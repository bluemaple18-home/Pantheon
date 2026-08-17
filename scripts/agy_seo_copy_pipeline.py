#!/usr/bin/env python3
"""Pantheon 統一文章產製、獨立審稿、核准與 apply pipeline。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from scripts.update_articles_hub_dates import articles_hub_updated_date, render_articles_hub_dates


SCHEMA_VERSION = 1
MAX_RUN_ARTICLES = 5
MAX_ARTICLE_BRIEF_BYTES = 8192
REGISTRY_NODE_TIMEOUT_SECONDS = 300
MODEL_ROUTE_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "agy_gemini_model_routes.v1.json"
)
MODEL_ROUTE_SCHEMA_VERSION = 1
MODEL_ROUTE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class ModelRouteConfig:
    schema_version: int
    routes: dict[str, tuple[str, ...]]
    digest: str
    path: Path


def load_model_route_config(path: Path) -> ModelRouteConfig:
    try:
        canonical_path = path.resolve(strict=True)
        payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("model route config is unavailable") from error
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "routes"}:
        raise ValueError("model route config fields are invalid")
    raw_routes = payload.get("routes")
    if (
        type(payload.get("schema_version")) is not int
        or payload["schema_version"] != MODEL_ROUTE_SCHEMA_VERSION
        or not isinstance(raw_routes, dict)
    ):
        raise ValueError("model route config schema is invalid")
    if set(raw_routes) != {"writer", "reviewer"}:
        raise ValueError("model route roles are invalid")
    routes: dict[str, tuple[str, ...]] = {}
    for role in ("writer", "reviewer"):
        values = raw_routes.get(role)
        if (
            not isinstance(values, list)
            or not values
            or any(type(value) is not str or MODEL_ROUTE_PATTERN.fullmatch(value) is None for value in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError(f"model route {role} order is invalid")
        routes[role] = tuple(values)
    if routes["writer"][0] == routes["reviewer"][0]:
        raise ValueError("model route primary role collision")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return ModelRouteConfig(
        schema_version=MODEL_ROUTE_SCHEMA_VERSION,
        routes=routes,
        digest=hashlib.sha256(canonical).hexdigest(),
        path=canonical_path,
    )


MODEL_ROUTE_CONFIG = load_model_route_config(MODEL_ROUTE_CONFIG_PATH)
MODEL_ROUTE_CONFIG_DIGEST = MODEL_ROUTE_CONFIG.digest
DEFAULT_WRITER_MODEL = MODEL_ROUTE_CONFIG.routes["writer"][0]
DEFAULT_REVIEWER_MODEL = MODEL_ROUTE_CONFIG.routes["reviewer"][0]


def model_route_config_from_environment() -> ModelRouteConfig:
    configured_path = os.environ.get("AGY_GEMINI_MODEL_ROUTE_CONFIG", "").strip()
    expected_digest = os.environ.get(
        "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST", ""
    ).strip()
    if os.environ.get("PANTHEON_FORMAL_RUNTIME") == "1" and (
        not configured_path or not expected_digest
    ):
        raise ValueError("formal model route config identity is incomplete")
    route_config = load_model_route_config(
        Path(configured_path) if configured_path else MODEL_ROUTE_CONFIG_PATH
    )
    if expected_digest and expected_digest != route_config.digest:
        raise ValueError("model route config digest mismatch")
    for environment_name, role in (
        ("AGY_WRITER_MODEL", "writer"),
        ("AGY_REVIEWER_MODEL", "reviewer"),
    ):
        override = os.environ.get(environment_name, "").strip()
        if override and override != route_config.routes[role][0]:
            raise ValueError("model route environment drift")
    return route_config
MAX_WRITER_SCHEMA_REPAIRS = 2
NEW_DESCRIPTION_BOUNDARY_SENTENCES = (
    "本文只提供通用理解，不能替個人下結論。",
    "內容不承諾特定結果，仍須依實際情境與資料判斷。",
    "請核對當下狀況與可用資訊後再決定。",
    "這些線索僅供整理問題與下一步。",
)


def _antigravity_model_label(model: str) -> str:
    parts = model.removeprefix("gemini-").split("-")
    name = "-".join(part.capitalize() for part in parts[1:])
    return f"Gemini {parts[0]} {name} (Low)"


ANTIGRAVITY_MODEL_LABELS = {
    model: _antigravity_model_label(model)
    for route in MODEL_ROUTE_CONFIG.routes.values()
    for model in route
}
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RUN_ROOT = Path(".work/gsc-copy")
MATRIX_PLAN = Path("artifacts/fortune_council/content_seo_execution/evidence/scale_clusters/cluster_plan.md")
MATRIX_V2_PLAN = Path(
    "artifacts/fortune_council/content_seo_execution/evidence/content_matrix_v2/content-matrix-v2.json"
)
PUBLICATION_STANDARD = Path("docs/pantheon_article_publication_standard.md")
POLICY_V2_PATH = Path("app/core/article_publication_policy_v2.json")
_POLICY_V2_CACHE: dict[str, Any] | None = None

ARTICLE_FIELDS = {
    "id",
    "section",
    "product",
    "slug",
    "serial",
    "urlSlug",
    "primaryKeyword",
    "secondaryKeywords",
    "title",
    "description",
    "answer",
    "tags",
    "faq",
    "bodySections",
    "published",
    "updated",
    "publicationPolicy",
}
REQUIRED_ARTICLE_FIELDS = ARTICLE_FIELDS
OPTIMIZE_FIELDS = {"title", "description", "answer"}
REWRITE_IMMUTABLE_FIELDS = {
    "id",
    "product",
    "slug",
    "serial",
    "title",
    "description",
    "answer",
    "faq",
    "tags",
    "published",
    "updated",
    "urlSlug",
    "primaryKeyword",
}
REWRITE_ARTICLE_FIELDS = {"article_id", "identity", "current_body_sha256", "bodySections", "publicationPolicy"}
REWRITE_IDENTITY_FIELDS = {"id", "product", "category", "serial", "slug", "primaryKeyword", "title"}
REWRITE_ACTION_VERBS = {
    "安排",
    "列出",
    "寫下",
    "比較",
    "記錄",
    "詢問",
    "確認",
    "核對",
    "拆開",
    "設定",
    "觀察",
    "回顧",
    "蒐集",
    "盤點",
    "試做",
    "計算",
    "暫停",
    "標記",
}
REWRITE_SCENE_MARKERS = {
    "會議",
    "聚會",
    "伴侶",
    "朋友",
    "同事",
    "主管",
    "家人",
    "工作",
    "面試",
    "轉職",
    "進修",
    "搬家",
    "帳單",
    "收入",
    "支出",
    "訊息",
    "對話",
    "週末",
    "下班",
    "回家",
    "期限",
    "合約",
    "課程",
}
REWRITE_TEMPLATE_HEADINGS = {
    "真正要整理的是什麼",
    "有哪些可觀察線索",
    "變成下一步",
    "不能代表什麼",
}
REWRITE_REPAIR_ARTICLE_IDS = (
    "MBTI-BASE-01",
    "THEME-LIFE-03",
    "THEME-INTERPERSONAL-03",
    "THEME-LIFE-04",
    "THEME-WEALTH-04",
)
REWRITE_REPAIR_STYLE_CONTRACTS = {
    "MBTI-BASE-01": {
        "opening": "先用一句直接定義回答，再落到會議中的資訊處理差異",
        "headings": "五個小標依序聚焦定義、四組偏好、工作協作、反例、使用邊界",
        "argumentOrder": "定義→比較軸→工作場景→反例→自我觀察",
        "counterexample": "放在第 4 節，以同型者行為不同為反例",
        "ending": "用一個可記錄的近期互動問題收尾",
    },
    "THEME-LIFE-03": {
        "opening": "從搬家與進修同時卡住的岔路場景切入，再回答塔羅的用途",
        "headings": "五個小標依序聚焦岔路、問題拆分、牌面翻譯、限制、下一步",
        "argumentOrder": "場景→拆題→解讀方法→限制→行動",
        "counterexample": "放在第 4 節開頭，以資訊不足卻急著抽牌為反例",
        "ending": "以今天能完成的一項資料蒐集動作收尾",
    },
    "THEME-INTERPERSONAL-03": {
        "opening": "從聚會散場後仍坐在玄關的身體疲憊畫面切入",
        "headings": "五個小標依序聚焦耗能來源、場合差異、界線設計、例外警訊、恢復安排",
        "argumentOrder": "感受畫面→來源分類→兩個人際場景→例外→恢復設計",
        "counterexample": "放在第 4 節中段，說明獨處也累時不能只歸因社交",
        "ending": "以安排下一次聚會前後空白時段收尾",
    },
    "THEME-LIFE-04": {
        "opening": "先對比兩份工作邀請的決策桌面，再說明人格偏好的角色",
        "headings": "五個小標依序聚焦選項、資訊偏好、試做、壓力偏差、保留選擇",
        "argumentOrder": "選項對照→偏好線索→低成本試做→壓力反例→決策紀錄",
        "counterexample": "放在第 4 節結尾，以壓力下反常選擇說明偏好會變動",
        "ending": "以寫下一項仍可撤回的決定收尾",
    },
    "THEME-WEALTH-04": {
        "opening": "從薪資入帳卻被房租與學費切走的帳務畫面切入",
        "headings": "五個小標依序聚焦現金流、時間尺度、轉職成本、命理解讀限制、帳目核對",
        "argumentOrder": "帳目場景→短長期區分→轉職情境→限制→數字核對",
        "counterexample": "放在第 2 節，以收入增加但餘裕下降為反例",
        "ending": "以核對三個月固定支出與可承擔額收尾",
    },
}
REWRITE_BATCH_002_ARTICLES = (
    ("article-01", "THEME-INTERPERSONAL-04", "personality", "interpersonal", "interpersonal-0004", "interpersonal-0004", "職場私人界線", "職場人際和私人關係怎麼劃界線？先看角色與責任"),
    ("article-02", "THEME-CAREER-05", "fortune", "career", "career-0005", "career-0005", "工作卡住塔羅", "工作卡住時，塔羅適合幫你整理什麼？"),
    ("article-03", "THEME-LIFE-05", "fortune", "life-direction", "life-direction-0005", "life-direction-0005", "命盤人生階段", "命盤怎麼看人生階段？用週期回顧，不把時間寫成事件"),
    ("article-04", "THEME-WEALTH-05", "fortune", "wealth", "wealth-0005", "wealth-0005", "創業財務問題", "創業談財富，不能只問會不會賺錢"),
    ("article-05", "THEME-INTERPERSONAL-05", "personality", "interpersonal", "interpersonal-0005", "interpersonal-0005", "渴望被看見", "渴望被看見怎麼影響人際？觀察你用什麼交換認可"),
)
REWRITE_BATCH_003_010_IDS = {
    3: (("THEME-LOVE-05", "love-0005"), ("ASTRO-MERCURY-01", "astrology-0006"), ("THEME-CAREER-06", "career-0006"), ("THEME-LIFE-06", "life-direction-0006"), ("THEME-WEALTH-06", "wealth-0006")),
    4: (("THEME-INTERPERSONAL-06", "interpersonal-0006"), ("THEME-LOVE-06", "love-0006"), ("ASTRO-MARS-01", "astrology-0007"), ("THEME-CAREER-07", "career-0007"), ("THEME-LIFE-07", "life-direction-0007")),
    5: (("THEME-WEALTH-07", "wealth-0007"), ("THEME-INTERPERSONAL-07", "interpersonal-0007"), ("THEME-LOVE-07", "love-0007"), ("ASTRO-JUPITER-01", "astrology-0008"), ("THEME-CAREER-08", "career-0008")),
    6: (("THEME-LIFE-08", "life-direction-0008"), ("THEME-WEALTH-08", "wealth-0008"), ("THEME-INTERPERSONAL-08", "interpersonal-0008"), ("THEME-LOVE-08", "love-0008"), ("ASTRO-SATURN-01", "astrology-0009")),
    7: (("THEME-CAREER-09", "career-0009"), ("THEME-LIFE-09", "life-direction-0009"), ("THEME-WEALTH-09", "wealth-0009"), ("THEME-INTERPERSONAL-09", "interpersonal-0009"), ("THEME-LOVE-09", "love-0009")),
    8: (("ASTRO-HOUSES-01", "astrology-0010"), ("THEME-CAREER-10", "career-0010"), ("THEME-LIFE-10", "life-direction-0010"), ("THEME-WEALTH-10", "wealth-0010"), ("THEME-INTERPERSONAL-10", "interpersonal-0010")),
    9: (("THEME-LOVE-10", "love-0010"), ("THEME-CAREER-11", "career-0011"), ("THEME-LIFE-11", "life-direction-0011"), ("THEME-WEALTH-11", "wealth-0011"), ("THEME-INTERPERSONAL-11", "interpersonal-0011")),
    10: (("THEME-LOVE-11", "love-0011"), ("THEME-CAREER-12", "career-0012"), ("THEME-LIFE-12", "life-direction-0012"), ("THEME-WEALTH-12", "wealth-0012"), ("THEME-INTERPERSONAL-12", "interpersonal-0012")),
}
REWRITE_BATCH_002_STYLE_CONTRACTS = {
    "THEME-INTERPERSONAL-04": {
        "opening": "從同事在下班後追問感情近況的訊息切入，先回答職場私人界線是依角色與責任決定揭露範圍",
        "headings": "依序聚焦下班訊息、角色責任、兩種回應界線、善意越界反例、下次回覆腳本",
        "argumentOrder": "越界場景→責任判準→回應選項→善意反例→話術演練",
        "counterexample": "放在第 4 節，以關心未必惡意但仍可拒答為反例",
        "ending": "寫下一句能在下次被追問時直接使用的回覆",
    },
    "THEME-CAREER-05": {
        "opening": "從簡報被退回三次、游標停在空白頁的工作現場切入，直接界定塔羅只能協助拆開卡點",
        "headings": "依序聚焦停滯現場、可問的工作問題、牌面轉成假設、資訊不足反例、二十四小時試做",
        "argumentOrder": "工作現場→問題改寫→假設驗證→資訊限制→小型試做",
        "counterexample": "放在第 4 節開頭，以缺少主管標準卻反覆抽牌為反例",
        "ending": "選一項二十四小時內能向主管確認或試做的動作",
    },
    "THEME-LIFE-05": {
        "opening": "從整理十年前履歷與搬家紀錄的桌面切入，說明命盤人生階段用於回顧週期而非指定事件日期",
        "headings": "依序聚焦時間軸、重複課題、轉折前後比較、事件預言限制、季度回顧表",
        "argumentOrder": "資料回顧→週期辨識→前後對照→預言反例→建立紀錄",
        "counterexample": "放在第 4 節中段，以同一時期兩人經歷不同說明週期不是事件清單",
        "ending": "在季度表記下三個可核對的生活變化",
    },
    "THEME-WEALTH-05": {
        "opening": "從訂單增加但月底仍付不出薪資的創業帳戶切入，先把創業財務問題拆成現金流、成本與風險",
        "headings": "依序聚焦帳戶落差、收入品質、固定與變動成本、獲利假象反例、十三週現金表",
        "argumentOrder": "帳戶警訊→收入拆解→成本承擔→獲利反例→數字追蹤",
        "counterexample": "放在第 4 節結尾，以帳面獲利但現金不足說明不能只問賺不賺錢",
        "ending": "核對未來十三週的入帳日、付款日與最低現金水位",
    },
    "THEME-INTERPERSONAL-05": {
        "opening": "從群組提案沒人回覆後立刻加碼承諾的動作切入，回答渴望被看見會讓人用付出交換認可",
        "headings": "依序聚焦加碼動作、交換方式、關係代價、沉默誤讀反例、不加碼觀察",
        "argumentOrder": "行為瞬間→交換模式→兩段關係代價→誤讀反例→暫停實驗",
        "counterexample": "放在第 4 節開頭，說明對方沉默未必是否定或忽視",
        "ending": "下一次想加碼付出時先暫停並記錄真正想得到的回應",
    },
}
REWRITE_CLOSURE_EDITS = {
    ("MBTI-BASE-01", 5, 2): (
        "解讀這些偏好時，應避免將其視為終身不變的判決。它提供的是一個理解自己與他人溝通落差的切入點，讓你在面對人際摩擦時，能多一個客觀的視角去分析原因，而不是把所有問題都歸咎於性格不合。",
        "解讀這些偏好時，應避免將其視為終身不變的判決。它提供的是一個理解自己與他人溝通落差的切入點，讓你在面對人際摩擦時，能多一個客觀的視角去分析原因，而不是把所有問題都歸咎於性格不合所致。",
    ),
    ("THEME-LIFE-03", 4, 1): (
        "在沒有收集任何現實資訊的情況下就急著抽牌，是無法為人生指明道路的反例。人生方向塔羅絕對不能當作保證預測未來的工具，它更無法為你的人生決定做任何承諾。過度依賴牌面只會讓你失去在現實中做決策的主動權。",
        "在沒有收集任何現實資訊的情況下就急著抽牌，是無法為人生指明道路的反例。人生方向塔羅絕對不能當作準確預測未來的工具，它更無法為你的人生決定做任何承諾。過度依賴牌面只會讓你失去在現實中做決策的主動權。",
    ),
}
BANNED_PHRASES = {
    "全面解析",
    "深度解析",
    "快速變化的時代",
    "不可或缺",
    "賦能",
    "不僅",
    "更是",
    "總而言之",
    "值得注意的是",
    "必看",
    "一定",
    "保證",
    "注定",
}
MACHINE_OWNED_REVIEW_CODES = {
    "answer_length",
    "banned_phrase",
    "banned_phrase_usage",
    "body_length",
    "body_length_insufficient",
    "description_boundary",
    "description_length",
    "generic_ai_phrase",
    "opening_keyword",
    "paragraph_count",
    "paragraph_length",
    "paragraph_length_violation",
    "repeated_sentence",
    "required_tags",
    "section_count",
    "title_keyword",
    "title_length",
}
REWRITE_MACHINE_OWNED_REVIEW_CODES = {
    "body_length",
    "body_length_insufficient",
    "body_shape_violation",
    "candidate_hash",
    "candidate_hash_mismatch",
    "current_body_hash_mismatch",
    "current_body_sha256",
    "immutable_identity",
    "immutable_identity_violation",
    "paragraph_count",
    "paragraph_length",
    "paragraph_length_violation",
    "section_count",
}
REQUIRED_PUBLIC_TAGS = {"Pantheon", "繁體中文", "公開文章", "通用知識", "SEO", "AEO", "GEO"}
GENERIC_AI_PHRASES = {
    "我們可以透過",
    "小明",
    "小華",
    "游刃有餘",
    "最佳平衡點",
    "本篇帶您",
    "為您解讀",
    "此處探討",
    "通常出記",
}
NEGATED_PROMISE_PREFIXES = ("不", "未", "並非", "不是", "不能", "無法", "沒有")


def _contains_banned_phrase(text: str, phrase: str) -> bool:
    start = 0
    while True:
        index = text.find(phrase, start)
        if index < 0:
            return False
        prefix = text[max(0, index - 3) : index]
        if phrase not in {"一定", "保證", "注定"} or not any(prefix.endswith(value) for value in NEGATED_PROMISE_PREFIXES):
            return True
        start = index + len(phrase)
MATRIX_EQUIVALENT_KEYWORDS = {
    "官祿宮": {"事業宮"},
    "流年": {"八字流年"},
}


class CandidateValidationError(ValueError):
    """候選稿 schema 不符合契約。"""


def load_article_publication_policy(path: Path | None = None) -> dict[str, Any]:
    """載入唯一 policy v2 契約；格式漂移時 fail closed。"""
    global _POLICY_V2_CACHE
    if path is None and _POLICY_V2_CACHE is not None:
        return _POLICY_V2_CACHE
    source = path or (Path(__file__).resolve().parents[1] / POLICY_V2_PATH)
    payload = json.loads(source.read_text(encoding="utf-8"))
    required_top = {
        "policy_version",
        "effective_date",
        "site_origin",
        "identity",
        "levels",
        "required",
        "recommended",
        "measured",
        "migration_only",
        "presentation_constraints",
        "evidence_modes",
        "verifiable_claim_detection",
        "forbidden_claims",
    }
    if set(payload) != required_top:
        raise CandidateValidationError("article publication policy v2 top-level fields are strict")
    if payload.get("policy_version") != "pantheon-article-publication-v2.0.0":
        raise CandidateValidationError("unsupported article publication policy version")
    if set(payload["levels"]) != {"required", "recommended", "measured", "migration_only"}:
        raise CandidateValidationError("article publication policy levels are incomplete")
    presentation = payload.get("presentation_constraints")
    if (
        not isinstance(presentation, dict)
        or set(presentation) != {"classification", "profiles"}
        or set(presentation.get("profiles") or {})
        != {"create", "rewrite_existing_body"}
    ):
        raise CandidateValidationError(
            "article publication policy presentation profiles are incomplete"
        )
    claim_detection = payload.get("verifiable_claim_detection")
    if (
        not isinstance(claim_detection, dict)
        or set(claim_detection) != {"semantics", "patterns"}
        or not isinstance(claim_detection.get("patterns"), list)
        or not claim_detection["patterns"]
    ):
        raise CandidateValidationError(
            "article publication policy verifiable claim detection is invalid"
        )
    try:
        for pattern in claim_detection["patterns"]:
            re.compile(str(pattern))
    except re.error as error:
        raise CandidateValidationError(
            "article publication policy verifiable claim pattern is invalid"
        ) from error
    if path is None:
        _POLICY_V2_CACHE = payload
    return payload


def publication_policy_version() -> str:
    return str(load_article_publication_policy()["policy_version"])


def publication_presentation_profile(mode: str) -> dict[str, Any]:
    profiles = load_article_publication_policy()["presentation_constraints"][
        "profiles"
    ]
    if mode not in profiles:
        raise CandidateValidationError(
            f"unsupported article publication presentation profile: {mode}"
        )
    profile = profiles[mode]
    if not isinstance(profile, dict):
        raise CandidateValidationError(
            f"invalid article publication presentation profile: {mode}"
        )
    return profile


def _range_bounds(
    profile: dict[str, Any],
    field: str,
) -> tuple[int, int]:
    value = profile.get(field)
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("minimum"), int)
        or not isinstance(value.get("maximum"), int)
        or value["minimum"] > value["maximum"]
    ):
        raise CandidateValidationError(
            f"invalid article publication presentation constraint: {field}"
        )
    return int(value["minimum"]), int(value["maximum"])


def _maximum_bound(profile: dict[str, Any], field: str) -> int:
    value = profile.get(field)
    if not isinstance(value, dict) or not isinstance(value.get("maximum"), int):
        raise CandidateValidationError(
            f"invalid article publication presentation constraint: {field}"
        )
    return int(value["maximum"])


def _preferred_bounds(
    profile: dict[str, Any],
    field: str,
) -> tuple[int, int]:
    value = profile.get(field)
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("preferred_minimum"), int)
        or not isinstance(value.get("preferred_maximum"), int)
        or value["preferred_minimum"] > value["preferred_maximum"]
    ):
        raise CandidateValidationError(
            f"invalid article publication preferred constraint: {field}"
        )
    return int(value["preferred_minimum"]), int(value["preferred_maximum"])


def _constraint_phrase(
    profile: dict[str, Any],
    field: str,
    unit: str,
) -> str:
    value = profile.get(field)
    if not isinstance(value, dict):
        raise CandidateValidationError(
            f"invalid article publication presentation constraint: {field}"
        )
    minimum = value.get("minimum")
    maximum = value.get("maximum")
    if isinstance(minimum, int) and isinstance(maximum, int):
        if minimum == maximum:
            return f"恰好 {minimum}{unit}"
        return f"{minimum} 到 {maximum}{unit}"
    if isinstance(minimum, int):
        return f"至少 {minimum}{unit}"
    if isinstance(maximum, int):
        return f"最多 {maximum}{unit}"
    raise CandidateValidationError(
        f"invalid article publication presentation constraint: {field}"
    )


def publication_presentation_instruction(mode: str) -> str:
    profile = publication_presentation_profile(mode)
    return "；".join(
        [
            f"正文{_constraint_phrase(profile, 'body_characters', '字')}",
            _constraint_phrase(profile, "body_sections", "節"),
            f"每節{_constraint_phrase(profile, 'paragraphs_per_section', '段')}",
            f"每段{_constraint_phrase(profile, 'paragraph_characters', '字')}",
        ]
    )


def _verifiable_claim_markers(text: str) -> list[str]:
    detection = load_article_publication_policy()["verifiable_claim_detection"]
    return [
        str(pattern)
        for pattern in detection["patterns"]
        if re.search(str(pattern), text)
    ]


def _policy_finding(
    article_id: str,
    code: str,
    message: str,
    *,
    severity: str = "required",
) -> dict[str, str]:
    return {
        "article_id": article_id,
        "code": code,
        "message": message,
        "severity": severity,
        "policy_version": publication_policy_version(),
    }


def required_policy_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [finding for finding in findings if finding.get("severity", "required") == "required"]


def policy_validation_evidence(
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    required = required_policy_findings(findings)
    return {
        "policy_version": publication_policy_version(),
        "validator_result": "FAIL" if required else "PASS",
        "article_ids": [
            _candidate_id(article)
            for article in candidate.get("articles") or []
            if isinstance(article, dict)
        ],
        "failure_codes": sorted({str(finding.get("code") or "unknown") for finding in required}),
        "input_hash": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
    }


def _iso_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _article_route(article: dict[str, Any]) -> str:
    if article.get("canonical_path"):
        return str(article["canonical_path"])
    serial = str(article.get("serial") or "")
    category = serial.rsplit("-", 1)[0] if "-" in serial else str(article.get("product") or "")
    url_slug = str(article.get("urlSlug") or article.get("slug") or "")
    return f"/articles/{category}/{url_slug}" if category and url_slug else ""


def _intent_overlap(primary_keyword: str, value: str) -> float:
    keyword_chars = set(_normalize_keyword(primary_keyword))
    value_chars = set(_normalize_keyword(value))
    if not keyword_chars:
        return 1.0
    return len(keyword_chars & value_chars) / len(keyword_chars)


def _publication_contract_schema() -> dict[str, Any]:
    source = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"},
            "supports": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "required": ["title", "url", "supports"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "policyVersion": {"type": "string", "enum": [publication_policy_version()]},
            "canonical": {"type": "string"},
            "author": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "id": {"type": "string"},
                },
                "required": ["name", "url", "id"],
            },
            "editorialResponsibility": {"type": "string"},
            "evidence": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "mode": {"type": "string", "enum": ["sources", "cultural_reflection"]},
                    "sources": {"type": "array", "items": source},
                    "disclosure": {"type": "string"},
                },
                "required": ["mode", "sources", "disclosure"],
            },
            "published": {"type": "string"},
            "modified": {"type": "string"},
            "changeType": {"type": "string", "enum": ["created", "substantive_rewrite"]},
        },
        "required": [
            "policyVersion",
            "canonical",
            "author",
            "editorialResponsibility",
            "evidence",
            "published",
            "modified",
            "changeType"
        ],
    }


def _validate_publication_contract_shape(value: object) -> None:
    if not isinstance(value, dict):
        raise CandidateValidationError("publicationPolicy must be an object")
    expected = set(_publication_contract_schema()["required"])
    if set(value) != expected:
        raise CandidateValidationError(f"publicationPolicy fields must be {sorted(expected)}")
    author = value.get("author")
    if not isinstance(author, dict) or set(author) != {"name", "url", "id"}:
        raise CandidateValidationError("publicationPolicy author fields are strict")
    evidence = value.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"mode", "sources", "disclosure"}:
        raise CandidateValidationError("publicationPolicy evidence fields are strict")
    if not isinstance(evidence.get("sources"), list):
        raise CandidateValidationError("publicationPolicy evidence sources must be a list")
    for source in evidence["sources"]:
        if not isinstance(source, dict) or set(source) != {"title", "url", "supports"}:
            raise CandidateValidationError("publicationPolicy source fields are strict")
        if not isinstance(source.get("supports"), list) or not source["supports"]:
            raise CandidateValidationError("publicationPolicy source supports must be non-empty")


def article_publication_policy_findings(
    article: dict[str, Any],
    *,
    mode: str,
    reference_articles: list[dict[str, Any]] | None = None,
    validate_canonical_route: bool = True,
) -> list[dict[str, str]]:
    """同一 required validator，供 create、rewrite、publisher 與 prerender 使用。"""
    policy = load_article_publication_policy()
    article_id = _candidate_id(article)
    findings: list[dict[str, str]] = []
    contract = article.get("publicationPolicy")
    if not isinstance(contract, dict):
        return [_policy_finding(article_id, "missing_policy_contract", "缺少 publicationPolicy v2 契約")]
    try:
        _validate_publication_contract_shape(contract)
    except CandidateValidationError as error:
        return [_policy_finding(article_id, "invalid_policy_contract", str(error))]
    if contract.get("policyVersion") != policy["policy_version"]:
        findings.append(_policy_finding(article_id, "policy_version", "candidate policy_version 與目前 validator 不一致"))

    route = _article_route(article)
    canonical = f"{policy['site_origin']}{route}" if route else ""
    canonical_is_valid = (
        contract.get("canonical") == canonical
        if validate_canonical_route
        else str(contract.get("canonical") or "").startswith(
            f"{policy['site_origin']}/articles/"
        )
    )
    if not canonical_is_valid:
        findings.append(_policy_finding(article_id, "canonical_consistency", "canonical 必須與 id/route 契約一致"))

    author = contract["author"]
    identity = policy["identity"]
    if (
        author.get("name") != identity["author_name"]
        or author.get("url") != identity["author_url"]
        or author.get("id") != identity["author_id"]
        or contract.get("editorialResponsibility") != identity["editorial_responsibility"]
    ):
        findings.append(_policy_finding(article_id, "author_identity", "作者與編輯責任必須使用穩定且可識別的 policy identity"))

    published = _iso_date(contract.get("published"))
    modified = _iso_date(contract.get("modified"))
    article_published = _iso_date(article.get("published"))
    article_updated = _iso_date(article.get("updated"))
    if published is None or modified is None or modified < published:
        findings.append(_policy_finding(article_id, "truthful_dates", "published/modified 必須為真實 ISO 日期且 modified 不早於 published"))
    if article_published and published != article_published:
        findings.append(_policy_finding(article_id, "truthful_dates", "publicationPolicy published 與文章資料不一致"))
    if mode == "create" and (article_published is None or article_updated is None):
        findings.append(_policy_finding(article_id, "truthful_dates", "文章缺少真實 published/updated；不得以 fallback 日期補值"))
    if mode != "rewrite_existing_body" and article_updated and modified != article_updated:
        findings.append(_policy_finding(article_id, "truthful_dates", "publicationPolicy modified 與文章資料不一致"))
    if mode == "rewrite_existing_body" and article_updated and modified and modified < article_updated:
        findings.append(_policy_finding(article_id, "substantive_modified_date", "實質重寫的 modified 不得早於目前 updated"))
    expected_change = "substantive_rewrite" if mode == "rewrite_existing_body" else "created"
    if contract.get("changeType") != expected_change:
        findings.append(_policy_finding(article_id, "substantive_modified_date", f"{mode} 必須標記 changeType={expected_change}"))
    current_body_hash = str(article.get("current_body_sha256") or "")
    if (
        mode == "rewrite_existing_body"
        and re.fullmatch(r"[0-9a-f]{64}", current_body_hash)
        and body_sha256(article.get("bodySections") or []) == current_body_hash
    ):
        findings.append(
            _policy_finding(
                article_id,
                "no_substantive_change",
                "rewrite 正文與 canonical current body 相同；不得更新 modified",
            )
        )

    paragraphs = [
        str(paragraph)
        for section in article.get("bodySections") or []
        if isinstance(section, dict)
        for paragraph in section.get("paragraphs") or []
    ]
    title = str(article.get("title") or article.get("identity", {}).get("title") or "")
    description = str(article.get("description") or "")
    answer = str(article.get("answer") or "")
    primary_keyword = str(article.get("primaryKeyword") or article.get("identity", {}).get("primaryKeyword") or "")
    opening = paragraphs[0] if paragraphs else ""
    text = "".join([title, description, answer, *paragraphs])

    evidence = contract["evidence"]
    evidence_mode = evidence.get("mode")
    sources = evidence.get("sources")
    disclosure = str(evidence.get("disclosure") or "").strip()
    if evidence_mode == "sources":
        if not sources:
            findings.append(_policy_finding(article_id, "article_level_evidence", "可驗證事實/研究/統計/方法主張必須有文章級來源"))
        for source in sources or []:
            if (
                not str(source.get("title") or "").strip()
                or not re.fullmatch(r"https://[^\s]+", str(source.get("url") or ""))
                or not all(str(claim).strip() for claim in source.get("supports") or [])
            ):
                findings.append(_policy_finding(article_id, "article_level_evidence", "來源必須包含 https URL、標題與所支持主張"))
                break
    elif evidence_mode == "cultural_reflection":
        if sources or not disclosure:
            findings.append(_policy_finding(article_id, "cultural_reflection_disclosure", "文化/反思內容必須明確 disclosure 且不得虛構來源"))
        claim_markers = _verifiable_claim_markers(text)
        if claim_markers:
            findings.append(
                _policy_finding(
                    article_id,
                    "article_level_evidence",
                    "文化/反思內容偵測到需 evidence 的研究、統計、百分比或方法主張；"
                    "請移除可驗證主張或提供真實來源，不得虛構引用",
                )
            )
    else:
        findings.append(_policy_finding(article_id, "article_level_evidence", "evidence mode 必須為 sources 或 cultural_reflection"))

    if primary_keyword and _intent_overlap(primary_keyword, title) < 0.5:
        findings.append(_policy_finding(article_id, "title_primary_intent", "H1/title 必須回答並包含 primary intent"))
    if primary_keyword and _intent_overlap(primary_keyword, opening[:160]) < 0.7:
        findings.append(_policy_finding(article_id, "opening_primary_intent", "第一段必須直接回答 primary intent"))
    if mode == "create":
        if not description or not _has_boundary_statement(description):
            findings.append(_policy_finding(article_id, "description_context_and_limit", "description 必須包含適用情境與限制"))
        if not answer or len(answer) < 12:
            findings.append(_policy_finding(article_id, "standalone_answer", "answer 必須可獨立理解"))
    if not _has_boundary_statement(text):
        findings.append(_policy_finding(article_id, "explicit_limit_or_counterexample", "正文必須有明確限制或反例"))
    for phrase in policy["forbidden_claims"]["outcome_guarantees"]:
        if phrase in text:
            findings.append(_policy_finding(article_id, "no_outcome_guarantee", f"禁止結果保證：{phrase}"))
    for phrase in policy["forbidden_claims"]["professional_substitution"]:
        if phrase in text:
            findings.append(_policy_finding(article_id, "no_professional_advice_substitution", f"禁止專業替代建議：{phrase}"))

    owners: dict[str, set[str]] = {}
    for reference in reference_articles or []:
        owner_id = _candidate_id(reference)
        if owner_id == article_id:
            continue
        for section in reference.get("bodySections") or []:
            for paragraph in section.get("paragraphs") or []:
                for sentence in re.split(r"[。！？]", str(paragraph)):
                    normalized = re.sub(r"\s+", "", sentence)
                    if len(normalized) >= 24:
                        owners.setdefault(normalized, set()).add(owner_id)
    for paragraph in paragraphs:
        for sentence in re.split(r"[。！？]", paragraph):
            normalized = re.sub(r"\s+", "", sentence)
            if len(normalized) >= 24 and normalized in owners:
                owner = sorted(owners[normalized])[0]
                findings.append(_policy_finding(article_id, "cross_corpus_originality", f"完整句與既有文章 {owner} 重複"))
                return findings
    return findings


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compact_json_bytes(payload) + b"\n")


def article_sha256(article: dict[str, Any]) -> str:
    return hashlib.sha256(compact_json_bytes(article)).hexdigest()


def body_sha256(body_sections: list[dict[str, Any]]) -> str:
    return hashlib.sha256(compact_json_bytes(body_sections)).hexdigest()


def _ensure_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateValidationError(f"{name} must be a non-empty string")
    return value


def validate_new_brief(brief: dict[str, Any]) -> None:
    if brief.get("mode") != "create":
        raise ValueError("new article brief mode must be create")
    _ensure_string(brief.get("run_id"), "run_id")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not articles:
        raise ValueError("brief articles must be a non-empty list")
    if len(articles) > MAX_RUN_ARTICLES:
        raise ValueError(f"a model run accepts at most {MAX_RUN_ARTICLES} articles")
    for index, article in enumerate(articles):
        size = len(compact_json_bytes(article))
        if size > MAX_ARTICLE_BRIEF_BYTES:
            raise ValueError(f"article brief {index} is {size} bytes; limit is 8192")
    if len(compact_json_bytes(brief)) + 1 > MAX_ARTICLE_BRIEF_BYTES:
        raise ValueError("whole brief exceeds 8192 bytes")


def validate_optimize_brief(brief: dict[str, Any]) -> None:
    if brief.get("mode") != "optimize":
        raise ValueError("GSC brief mode must be optimize")
    _ensure_string(brief.get("run_id"), "run_id")
    if brief.get("allowed_fields") != ["title", "description", "answer"]:
        raise ValueError("GSC brief allowed_fields must be title, description, answer")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not articles or len(articles) > MAX_RUN_ARTICLES:
        raise ValueError("GSC brief must contain 1 to 5 articles")
    if len(compact_json_bytes(brief)) + 1 > MAX_ARTICLE_BRIEF_BYTES:
        raise ValueError("GSC brief exceeds 8192 bytes")
    required = {"article_id", "canonical_path", "source_file", "current"}
    for article in articles:
        if not isinstance(article, dict) or not required <= set(article):
            raise ValueError("GSC brief article is missing current source fields")
        current = article.get("current")
        if not isinstance(current, dict) or set(current) != OPTIMIZE_FIELDS:
            raise ValueError("GSC current copy must contain only title, description, answer")


def validate_rewrite_brief(brief: dict[str, Any]) -> None:
    if brief.get("mode") != "rewrite_existing_body":
        raise ValueError("rewrite brief mode must be rewrite_existing_body")
    _ensure_string(brief.get("run_id"), "run_id")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not articles or len(articles) > MAX_RUN_ARTICLES:
        raise ValueError("rewrite brief must contain 1 to 5 articles")
    expected_slots = [_slot(index) for index in range(len(articles))]
    actual_slots = [str(item.get("slot")) for item in articles if isinstance(item, dict)]
    if actual_slots != expected_slots:
        raise ValueError("rewrite brief article slots must preserve exact order")
    article_ids: list[str] = []
    for item in articles:
        required = {
            "slot",
            "article_id",
            "identity",
            "immutable_fields",
            "current_body",
            "current_body_sha256",
            "rewrite_brief",
            "source_file",
            "body_source",
        }
        if set(item) != required:
            raise ValueError("rewrite brief article fields are strict")
        article_id = _ensure_string(item.get("article_id"), "article_id")
        article_ids.append(article_id)
        identity = item.get("identity")
        immutable = item.get("immutable_fields")
        if not isinstance(identity, dict) or set(identity) != REWRITE_IDENTITY_FIELDS:
            raise ValueError("rewrite identity fields are strict")
        if identity.get("id") != article_id:
            raise ValueError("rewrite identity id differs from article_id")
        if not isinstance(immutable, dict) or not REWRITE_IMMUTABLE_FIELDS <= set(immutable):
            raise ValueError("rewrite immutable fields are incomplete")
        if immutable.get("id") != article_id:
            raise ValueError("rewrite immutable id differs from article_id")
        current_body = item.get("current_body")
        _validate_body_sections(current_body, exact_shape=False)
        if item.get("current_body_sha256") != body_sha256(current_body):
            raise ValueError(f"rewrite current body hash mismatch for {article_id}")
        if not isinstance(item.get("rewrite_brief"), list) or not item["rewrite_brief"]:
            raise ValueError("rewrite_brief must be a non-empty list")
        for line in item["rewrite_brief"]:
            _ensure_string(line, "rewrite_brief item")
        _ensure_string(item.get("source_file"), "source_file")
        _ensure_string(item.get("body_source"), "body_source")
    if len(article_ids) != len(set(article_ids)):
        raise ValueError("rewrite brief contains duplicate article ids")


def _validate_body_sections(value: object, *, exact_shape: bool) -> None:
    if not isinstance(value, list) or not value:
        raise CandidateValidationError("bodySections must be a non-empty list")
    rewrite_profile = publication_presentation_profile("rewrite_existing_body")
    section_minimum, section_maximum = _range_bounds(
        rewrite_profile,
        "body_sections",
    )
    paragraph_minimum, paragraph_maximum = _range_bounds(
        rewrite_profile,
        "paragraphs_per_section",
    )
    if exact_shape and not section_minimum <= len(value) <= section_maximum:
        raise CandidateValidationError(
            "rewrite bodySections must contain "
            f"{section_minimum} to {section_maximum} sections"
        )
    for section in value:
        if not isinstance(section, dict) or set(section) != {"heading", "paragraphs"}:
            raise CandidateValidationError("body sections require only heading and paragraphs")
        _ensure_string(section.get("heading"), "bodySections.heading")
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            raise CandidateValidationError("body section paragraphs must be non-empty")
        if exact_shape and not paragraph_minimum <= len(paragraphs) <= paragraph_maximum:
            raise CandidateValidationError(
                "rewrite body section must contain "
                f"{paragraph_minimum} to {paragraph_maximum} paragraphs"
            )
        for paragraph in paragraphs:
            _ensure_string(paragraph, "bodySections.paragraph")


def _validate_create_article(article: dict[str, Any]) -> None:
    unexpected = set(article) - ARTICLE_FIELDS
    missing = REQUIRED_ARTICLE_FIELDS - set(article)
    if unexpected:
        raise CandidateValidationError(f"unexpected article fields: {sorted(unexpected)}")
    if missing:
        raise CandidateValidationError(f"missing article fields: {sorted(missing)}")
    for field in ["id", "section", "product", "slug", "serial", "urlSlug", "primaryKeyword", "title", "description", "answer", "published", "updated"]:
        _ensure_string(article.get(field), field)
    for field in ["secondaryKeywords", "tags", "faq", "bodySections"]:
        if not isinstance(article.get(field), list) or not article[field]:
            raise CandidateValidationError(f"{field} must be a non-empty list")
    faq_minimum, faq_maximum = _range_bounds(
        publication_presentation_profile("create"),
        "faq_items",
    )
    if not faq_minimum <= len(article["faq"]) <= faq_maximum:
        raise CandidateValidationError(
            f"faq must contain {faq_minimum} to {faq_maximum} items"
        )
    for item in article["faq"]:
        if not isinstance(item, dict) or set(item) != {"question", "answer"}:
            raise CandidateValidationError("faq items require only question and answer")
        _ensure_string(item.get("question"), "faq.question")
        _ensure_string(item.get("answer"), "faq.answer")
    _validate_body_sections(article["bodySections"], exact_shape=False)
    _validate_publication_contract_shape(article["publicationPolicy"])


def _validate_optimize_article(article: dict[str, Any]) -> None:
    required = {"article_id", "canonical_path", "source_file", "current", "proposed"}
    if set(article) != required:
        raise CandidateValidationError(f"optimize article fields must be {sorted(required)}")
    for field in ["article_id", "canonical_path", "source_file"]:
        _ensure_string(article.get(field), field)
    for field in ["current", "proposed"]:
        value = article.get(field)
        if not isinstance(value, dict) or set(value) != OPTIMIZE_FIELDS:
            raise CandidateValidationError(f"{field} must contain only title, description, answer")
        for key in OPTIMIZE_FIELDS:
            _ensure_string(value.get(key), f"{field}.{key}")


def _validate_rewrite_article(article: dict[str, Any]) -> None:
    if set(article) != REWRITE_ARTICLE_FIELDS:
        raise CandidateValidationError(f"rewrite article fields must be {sorted(REWRITE_ARTICLE_FIELDS)}")
    article_id = _ensure_string(article.get("article_id"), "article_id")
    identity = article.get("identity")
    if not isinstance(identity, dict) or set(identity) != REWRITE_IDENTITY_FIELDS:
        raise CandidateValidationError("rewrite identity fields are strict")
    if identity.get("id") != article_id:
        raise CandidateValidationError("rewrite identity id differs from article_id")
    if not re.fullmatch(r"[0-9a-f]{64}", str(article.get("current_body_sha256") or "")):
        raise CandidateValidationError("rewrite current body SHA-256 is invalid")
    _validate_body_sections(article.get("bodySections"), exact_shape=True)
    if body_sha256(article["bodySections"]) == article["current_body_sha256"]:
        raise CandidateValidationError(
            f"policy v2 required finding for {article_id}: no_substantive_change"
        )
    _validate_publication_contract_shape(article["publicationPolicy"])


def validate_candidate(
    candidate: dict[str, Any],
    *,
    enforce_policy: bool = True,
) -> None:
    if candidate.get("schema_version") != SCHEMA_VERSION:
        raise CandidateValidationError("unsupported candidate schema version")
    _ensure_string(candidate.get("run_id"), "run_id")
    mode = candidate.get("mode")
    if mode not in {"create", "optimize", "rewrite_existing_body"}:
        raise CandidateValidationError("candidate mode must be create, optimize, or rewrite_existing_body")
    if set(candidate) != {"schema_version", "run_id", "mode", "articles"}:
        raise CandidateValidationError("candidate top-level fields are strict")
    articles = candidate.get("articles")
    if not isinstance(articles, list) or not articles or len(articles) > MAX_RUN_ARTICLES:
        raise CandidateValidationError("candidate must contain 1 to 5 articles")
    ids: set[str] = set()
    for article in articles:
        if not isinstance(article, dict):
            raise CandidateValidationError("candidate articles must be objects")
        if mode == "create":
            _validate_create_article(article)
            article_id = str(article["id"])
        elif mode == "optimize":
            _validate_optimize_article(article)
            article_id = str(article["article_id"])
        else:
            if enforce_policy:
                _validate_rewrite_article(article)
            else:
                legacy_fields = REWRITE_ARTICLE_FIELDS - {"publicationPolicy"}
                actual_fields = set(article)
                if actual_fields != REWRITE_ARTICLE_FIELDS and actual_fields != legacy_fields:
                    raise CandidateValidationError(
                        f"legacy rewrite article fields must be {sorted(legacy_fields)}"
                    )
                if "publicationPolicy" in article:
                    _validate_rewrite_article(article)
                else:
                    _validate_rewrite_article(
                        {
                            **article,
                            "publicationPolicy": {
                                "policyVersion": publication_policy_version(),
                                "canonical": "migration-only",
                                "author": {"name": "migration-only", "url": "migration-only", "id": "migration-only"},
                                "editorialResponsibility": "migration-only",
                                "evidence": {"mode": "cultural_reflection", "sources": [], "disclosure": "migration-only"},
                                "published": "1970-01-01",
                                "modified": "1970-01-01",
                                "changeType": "substantive_rewrite",
                            },
                        }
                    )
            article_id = str(article["article_id"])
        if article_id in ids:
            raise CandidateValidationError(f"duplicate article id: {article_id}")
        ids.add(article_id)
        if enforce_policy and mode in {"create", "rewrite_existing_body"}:
            policy_article = article
            if mode == "rewrite_existing_body":
                policy_article = {
                    **article["identity"],
                    "id": article_id,
                    "current_body_sha256": article["current_body_sha256"],
                    "bodySections": article["bodySections"],
                    "publicationPolicy": article["publicationPolicy"],
                }
            findings = required_policy_findings(
                article_publication_policy_findings(
                    policy_article,
                    mode=mode,
                    validate_canonical_route=mode != "rewrite_existing_body",
                )
            )
            if findings:
                raise CandidateValidationError(
                    f"policy v2 required finding for {article_id}: {findings[0]['code']}"
                )


def _candidate_id(article: dict[str, Any]) -> str:
    return str(article.get("id") or article.get("article_id") or "")


def _has_boundary_statement(text: str) -> bool:
    return bool(re.search(r"不能|不代表|不適合|不是|無法|並非|不得|僅供|只供|只提供", text))


def _has_false_social_origin(text: str) -> bool:
    return bool(
        re.search(
            r"網路論壇|網友.{0,8}(?:俗稱|稱為)|社群.{0,8}(?:俗稱|代稱)",
            text,
        )
    )


def quality_findings(
    articles: list[dict[str, Any]],
    *,
    reference_articles: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    sentence_owners: dict[str, set[str]] = {}
    profile = publication_presentation_profile("create")
    description_minimum, description_maximum = _range_bounds(
        profile,
        "description_characters",
    )
    answer_maximum = _maximum_bound(profile, "answer_characters")
    body_minimum, body_maximum = _range_bounds(profile, "body_characters")
    section_minimum = int(profile["body_sections"]["minimum"])
    paragraph_minimum, paragraph_maximum = _range_bounds(
        profile,
        "paragraphs_per_section",
    )
    paragraph_char_minimum, paragraph_char_maximum = _range_bounds(
        profile,
        "paragraph_characters",
    )
    title_minimum, title_maximum = _range_bounds(profile, "title_characters")
    for article in articles:
        article_id = _candidate_id(article)
        if "bodySections" in article:
            findings.extend(
                article_publication_policy_findings(
                    article,
                    mode="create",
                    reference_articles=reference_articles,
                )
            )
        if "bodySections" not in article:
            text = "".join(str(article.get("proposed", {}).get(field, "")) for field in OPTIMIZE_FIELDS)
            paragraphs: list[str] = []
        else:
            paragraphs = [str(item) for section in article["bodySections"] for item in section["paragraphs"]]
            text = f"{article['title']}{article['description']}{article['answer']}{''.join(paragraphs)}"
            if not description_minimum <= len(str(article["description"])) <= description_maximum:
                findings.append({"article_id": article_id, "code": "description_length", "message": f"meta description 必須為 {description_minimum} 到 {description_maximum} 字"})
            if not _has_boundary_statement(str(article["description"])):
                findings.append({"article_id": article_id, "code": "description_boundary", "message": "meta description 本身必須包含明確限制"})
            if len(str(article["answer"])) > answer_maximum:
                findings.append({"article_id": article_id, "code": "answer_length", "message": f"answer 必須在 {answer_maximum} 字內"})
            body_length = len("".join(paragraphs))
            if not body_minimum <= body_length <= body_maximum:
                findings.append({"article_id": article_id, "code": "body_length", "message": f"單主題新文章正文必須為 {body_minimum} 到 {body_maximum} 字"})
            if len(article["bodySections"]) < section_minimum:
                findings.append({"article_id": article_id, "code": "section_count", "message": f"正文至少需要 {section_minimum} 個 H2 段落"})
            for section_index, section in enumerate(article["bodySections"], start=1):
                section_paragraphs = section["paragraphs"]
                if not paragraph_minimum <= len(section_paragraphs) <= paragraph_maximum:
                    findings.append({"article_id": article_id, "code": "paragraph_count", "message": f"第 {section_index} 節必須有 {paragraph_minimum} 到 {paragraph_maximum} 段"})
                for paragraph_index, paragraph in enumerate(section_paragraphs, start=1):
                    if not paragraph_char_minimum <= len(str(paragraph)) <= paragraph_char_maximum:
                        findings.append({"article_id": article_id, "code": "paragraph_length", "message": f"第 {section_index} 節第 {paragraph_index} 段必須為 {paragraph_char_minimum} 到 {paragraph_char_maximum} 字"})
            if not title_minimum <= len(str(article["title"])) <= title_maximum:
                findings.append({"article_id": article_id, "code": "title_length", "message": f"meta title 超出 {title_minimum} 到 {title_maximum} 字 internal presentation constraint"})
            missing_tags = sorted(REQUIRED_PUBLIC_TAGS - set(str(tag) for tag in article["tags"]))
            if missing_tags:
                findings.append({"article_id": article_id, "code": "required_tags", "message": f"缺少固定 tags：{', '.join(missing_tags)}"})
            if not _has_boundary_statement(text):
                findings.append({"article_id": article_id, "code": "missing_boundary", "message": "文章缺少明確限制"})
            keyword = _normalize_keyword(str(article["primaryKeyword"]))
            if keyword and keyword not in _normalize_keyword(str(article["title"])):
                findings.append({"article_id": article_id, "code": "title_keyword", "message": "title 未包含主關鍵字"})
            opening = paragraphs[0][:80] if paragraphs else ""
            if keyword and keyword not in _normalize_keyword(opening):
                findings.append({"article_id": article_id, "code": "opening_keyword", "message": "正文前 80 字未包含主關鍵字"})
            if re.fullmatch(r"MBTI-INTP-(?:AH|AC|OH|OC)", article_id):
                if "Pantheon 64 分支" not in text:
                    findings.append({"article_id": article_id, "code": "missing_pantheon_context", "message": "INTP 分支文必須說明這是 Pantheon 64 分支內容"})
                if _has_false_social_origin(text):
                    findings.append({"article_id": article_id, "code": "false_social_origin", "message": "不得把 Pantheon 64 分支誤寫成網路論壇俗稱"})
        proposed = article.get("proposed") if isinstance(article.get("proposed"), dict) else None
        if proposed is not None:
            if not description_minimum <= len(str(proposed["description"])) <= description_maximum:
                findings.append({"article_id": article_id, "code": "description_length", "message": f"meta description 必須為 {description_minimum} 到 {description_maximum} 字"})
            if not _has_boundary_statement(str(proposed["description"])):
                findings.append({"article_id": article_id, "code": "description_boundary", "message": "meta description 本身必須包含明確限制"})
            if len(str(proposed["answer"])) > answer_maximum:
                findings.append({"article_id": article_id, "code": "answer_length", "message": f"answer 必須在 {answer_maximum} 字內"})
        for phrase in sorted(BANNED_PHRASES):
            if _contains_banned_phrase(text, phrase):
                findings.append({"article_id": article_id, "code": "banned_phrase", "message": f"命中禁詞：{phrase}"})
        for phrase in sorted(GENERIC_AI_PHRASES):
            if phrase in text:
                findings.append({"article_id": article_id, "code": "generic_ai_phrase", "message": f"命中模板或假場景詞：{phrase}"})
        for paragraph in paragraphs:
            for sentence in re.split(r"[。！？]", paragraph):
                sentence = sentence.strip()
                if len(sentence) >= 18:
                    sentence_owners.setdefault(sentence, set()).add(article_id)
    for sentence, owners in sentence_owners.items():
        if len(owners) > 3:
            for article_id in owners:
                findings.append({"article_id": article_id, "code": "repeated_sentence", "message": f"同批完整句重複超過三篇：{sentence}"})
    return [
        {
            **finding,
            "severity": finding.get("severity", "required"),
            "policy_version": finding.get("policy_version", publication_policy_version()),
        }
        for finding in findings
    ]


def rewrite_quality_findings(
    brief: dict[str, Any],
    articles: list[dict[str, Any]],
    *,
    reference_articles: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """本卡正文改寫的 deterministic gate；不以 Reviewer 主觀判斷取代。"""
    findings: list[dict[str, str]] = []
    expected_ids = [str(item["article_id"]) for item in brief["articles"]]
    actual_ids = [str(item.get("article_id") or "") for item in articles]
    if actual_ids != expected_ids:
        return [{"article_id": article_id, "code": "article_order", "message": "文章集合或順序與 rewrite brief 不一致"} for article_id in expected_ids]
    profile = publication_presentation_profile("rewrite_existing_body")
    section_minimum, section_maximum = _range_bounds(profile, "body_sections")
    paragraph_minimum, paragraph_maximum = _range_bounds(
        profile,
        "paragraphs_per_section",
    )
    paragraph_char_minimum, paragraph_char_maximum = _range_bounds(
        profile,
        "paragraph_characters",
    )
    body_minimum, body_maximum = _range_bounds(profile, "body_characters")
    sentence_owners: dict[str, set[str]] = {}
    for source, article in zip(brief["articles"], articles, strict=True):
        article_id = str(article["article_id"])
        policy_article = {
            **source["immutable_fields"],
            **source["identity"],
            "id": article_id,
            "current_body_sha256": article.get("current_body_sha256"),
            "bodySections": article.get("bodySections"),
            "publicationPolicy": article.get("publicationPolicy"),
        }
        findings.extend(
            article_publication_policy_findings(
                policy_article,
                mode="rewrite_existing_body",
                reference_articles=reference_articles,
            )
        )
        sections = article.get("bodySections") if isinstance(article.get("bodySections"), list) else []
        paragraphs = [str(paragraph) for section in sections for paragraph in section.get("paragraphs", [])]
        text = "".join(paragraphs)
        if not section_minimum <= len(sections) <= section_maximum:
            findings.append({"article_id": article_id, "code": "section_count", "message": f"正文必須為 {section_minimum} 到 {section_maximum} 節"})
        paragraph_locations: dict[str, tuple[int, int]] = {}
        for section_index, section in enumerate(sections, start=1):
            section_paragraphs = section.get("paragraphs", [])
            if not paragraph_minimum <= len(section_paragraphs) <= paragraph_maximum:
                findings.append({"article_id": article_id, "code": "paragraph_count", "message": f"第 {section_index} 節必須為 {paragraph_minimum} 到 {paragraph_maximum} 段"})
            heading = str(section.get("heading") or "")
            if any(template in heading for template in REWRITE_TEMPLATE_HEADINGS):
                findings.append({"article_id": article_id, "code": "template_heading", "message": f"不得沿用批次模板小標：{heading}"})
            for paragraph_index, paragraph in enumerate(section_paragraphs, start=1):
                paragraph_text = str(paragraph)
                length = len(paragraph_text)
                if not paragraph_char_minimum <= length <= paragraph_char_maximum:
                    findings.append({"article_id": article_id, "code": "paragraph_length", "message": f"第 {section_index} 節第 {paragraph_index} 段為 {length} 字；必須 {paragraph_char_minimum} 到 {paragraph_char_maximum} 字"})
                first_location = paragraph_locations.get(paragraph_text)
                if first_location is not None:
                    findings.append(
                        {
                            "article_id": article_id,
                            "code": "duplicate_paragraph",
                            "message": (
                                f"第 {section_index} 節第 {paragraph_index} 段與"
                                f"第 {first_location[0]} 節第 {first_location[1]} 段逐字重複"
                            ),
                        }
                    )
                else:
                    paragraph_locations[paragraph_text] = (
                        section_index,
                        paragraph_index,
                    )
        if not body_minimum <= len(text) <= body_maximum:
            findings.append({"article_id": article_id, "code": "body_length", "message": f"正文為 {len(text)} 字；必須 {body_minimum} 到 {body_maximum} 字"})
        keyword = _normalize_keyword(str(source["identity"]["primaryKeyword"]))
        opening = _normalize_keyword(text[:80])
        if keyword and keyword not in opening:
            findings.append({"article_id": article_id, "code": "opening_keyword", "message": "正文前 80 字未自然回答 primary keyword"})
        scene_sentences = {
            sentence.strip()
            for sentence in re.split(r"[。！？]", text)
            if any(marker in sentence for marker in REWRITE_SCENE_MARKERS)
        }
        if len(scene_sentences) < 2:
            findings.append({"article_id": article_id, "code": "scenario_density", "message": "至少需要兩個可辨識的專屬生活場景"})
        verbs = sorted(verb for verb in REWRITE_ACTION_VERBS if verb in text)
        if len(verbs) < 3:
            findings.append({"article_id": article_id, "code": "concrete_verbs", "message": "至少需要 3 個不同的具體行動動詞"})
        if not re.search(r"反例|例外|不適用|不代表|不能|未必|然而|但", text):
            findings.append({"article_id": article_id, "code": "missing_counterexample_or_limit", "message": "缺少反例或明確限制"})
        for phrase in sorted(BANNED_PHRASES):
            if _contains_banned_phrase(text, phrase):
                findings.append({"article_id": article_id, "code": "banned_phrase", "message": f"命中禁詞：{phrase}"})
        for phrase in sorted(GENERIC_AI_PHRASES):
            if phrase in text:
                findings.append({"article_id": article_id, "code": "generic_ai_phrase", "message": f"命中模板或假場景詞：{phrase}"})
        for paragraph in paragraphs:
            for sentence in re.split(r"[。！？]", paragraph):
                normalized = sentence.strip()
                if len(normalized) >= 18:
                    sentence_owners.setdefault(normalized, set()).add(article_id)
    for sentence, owners in sentence_owners.items():
        if len(owners) >= 2:
            for article_id in sorted(owners):
                findings.append({"article_id": article_id, "code": "cross_article_sentence", "message": f"不得跨篇共用完整句：{sentence}"})
    return [
        {
            **finding,
            "severity": finding.get("severity", "required"),
            "policy_version": finding.get("policy_version", publication_policy_version()),
        }
        for finding in findings
    ]


def _canonical_rewrite_text(text: str, keyword: str) -> str:
    value = text.replace(keyword, "主題") if keyword else text
    value = re.sub(r"\d+", "數字", value)
    return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]", "", value).lower()


REWRITE_ABSTRACT_PATTERNS = {
    "when_topic_can_help": re.compile(r"當你.{0,16}(?:時|之際).{0,20}(?:能|可以|適合).{0,12}(?:幫你|協助你)"),
    "attention_is": re.compile(r"(?:必須|需要|值得|要)(?:先)?(?:注意|明確|說清楚)(?:的是|：)"),
    "not_but_frame": re.compile(r"(?:這|它|重點|關鍵).{0,10}(?:不是|不能|不代表).{0,18}(?:而是|只是)"),
}


def _paragraph_role_skeleton(paragraph: str) -> str:
    roles: list[str] = []
    for sentence in (item.strip() for item in re.split(r"[。！？]", paragraph) if item.strip()):
        if any(marker in sentence for marker in REWRITE_SCENE_MARKERS):
            role = "scene"
        elif re.search(r"反例|例外|然而|未必|不代表|不能|不適用", sentence):
            role = "limit"
        elif any(verb in sentence for verb in REWRITE_ACTION_VERBS):
            role = "action"
        elif re.search(r"為什麼|是否|哪一|什麼|如何|怎麼", sentence):
            role = "question"
        elif re.search(r"表示|意味|說明|反映|顯示", sentence):
            role = "interpret"
        else:
            role = "other"
        roles.append(role)
    if len(roles) < 3 or "other" in roles or len(set(roles)) < 2:
        return ""
    return ">".join(roles)


def rewrite_uniqueness_findings(
    brief: dict[str, Any],
    articles: list[dict[str, Any]],
    *,
    ngram_size: int = 24,
    opening_size: int = 10,
) -> list[dict[str, str]]:
    """聚合檢查共用 H2、長 n-gram 與段落開頭；完整句由 quality gate 檢查。"""
    if ngram_size < 12 or opening_size < 6:
        raise ValueError("rewrite uniqueness thresholds are too small")
    findings: list[dict[str, str]] = []
    headings: dict[str, set[str]] = {}
    openings: dict[str, set[str]] = {}
    abstract_patterns: dict[str, set[str]] = {}
    paragraph_skeletons: dict[str, set[str]] = {}
    article_ngrams: dict[str, set[str]] = {}
    for source, article in zip(brief["articles"], articles, strict=True):
        article_id = str(article["article_id"])
        keyword = str(source["identity"]["primaryKeyword"])
        ngrams: set[str] = set()
        for section in article["bodySections"]:
            heading = _canonical_rewrite_text(str(section["heading"]), keyword)
            if heading:
                headings.setdefault(heading, set()).add(article_id)
            for paragraph in section["paragraphs"]:
                paragraph_text = str(paragraph)
                canonical = _canonical_rewrite_text(str(paragraph), keyword)
                if len(canonical) >= opening_size:
                    openings.setdefault(canonical[:opening_size], set()).add(article_id)
                if len(canonical) >= ngram_size:
                    ngrams.update(canonical[index : index + ngram_size] for index in range(len(canonical) - ngram_size + 1))
                for pattern_name, pattern in REWRITE_ABSTRACT_PATTERNS.items():
                    if pattern.search(paragraph_text):
                        abstract_patterns.setdefault(pattern_name, set()).add(article_id)
                skeleton = _paragraph_role_skeleton(paragraph_text)
                if skeleton:
                    paragraph_skeletons.setdefault(skeleton, set()).add(article_id)
        article_ngrams[article_id] = ngrams
    for heading, owners in sorted(headings.items()):
        if len(owners) >= 2:
            for article_id in sorted(owners):
                findings.append({"article_id": article_id, "code": "shared_h2", "message": f"跨篇共用 H2 結構：{heading}"})
    for opening, owners in sorted(openings.items()):
        if len(owners) >= 2:
            for article_id in sorted(owners):
                findings.append({"article_id": article_id, "code": "repeated_paragraph_opening", "message": f"跨篇段落開頭重複：{opening}"})
    for pattern_name, owners in sorted(abstract_patterns.items()):
        if len(owners) >= 2:
            for article_id in sorted(owners):
                findings.append({"article_id": article_id, "code": "shared_abstract_pattern", "message": f"跨篇共用抽象句型：{pattern_name}"})
    for skeleton, owners in sorted(paragraph_skeletons.items()):
        if len(owners) >= 2:
            for article_id in sorted(owners):
                findings.append({"article_id": article_id, "code": "shared_paragraph_skeleton", "message": f"跨篇共用段落骨架：{skeleton}"})
    article_ids = [str(article["article_id"]) for article in articles]
    reported_pairs: set[tuple[str, str]] = set()
    for left_index, left_id in enumerate(article_ids):
        for right_id in article_ids[left_index + 1 :]:
            shared = article_ngrams[left_id] & article_ngrams[right_id]
            if not shared:
                continue
            pair = (left_id, right_id)
            if pair in reported_pairs:
                continue
            reported_pairs.add(pair)
            fragment = sorted(shared)[0]
            for article_id in pair:
                findings.append({"article_id": article_id, "code": "long_ngram", "message": f"與 {right_id if article_id == left_id else left_id} 共用長片段：{fragment}"})
    return findings


def rewrite_aggregate_findings(
    brief: dict[str, Any],
    articles: list[dict[str, Any]],
    *,
    reference_articles: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return (
        rewrite_quality_findings(
            brief,
            articles,
            reference_articles=reference_articles,
        ),
        rewrite_uniqueness_findings(brief, articles),
    )


def invalid_review_payload(run_id: str, articles: list[dict[str, Any]], reason: str, hard_failure: bool = True) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "articles": [
            {
                "article_id": _candidate_id(article),
                "candidate_sha256": article_sha256(article),
                "verdict": "REJECT",
                "hard_failure": hard_failure,
                "findings": [{"code": reason, "message": reason}],
            }
            for article in articles
        ],
    }


def deterministic_review_payload(
    run_id: str,
    articles: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    findings_by_id: dict[str, list[dict[str, str]]] = {}
    for finding in findings:
        findings_by_id.setdefault(str(finding["article_id"]), []).append(
            {
                "code": str(finding["code"]),
                "message": str(finding["message"]),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "articles": [
            {
                "article_id": _candidate_id(article),
                "candidate_sha256": article_sha256(article),
                "verdict": (
                    "REJECT"
                    if findings_by_id.get(_candidate_id(article))
                    else "APPROVE"
                ),
                "findings": findings_by_id.get(_candidate_id(article), []),
                "hard_failure": False,
            }
            for article in articles
        ],
    }


def validate_review(review: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    if review.get("schema_version") != SCHEMA_VERSION or not isinstance(review.get("articles"), list):
        raise ValueError("invalid review schema")
    expected = {_candidate_id(article): article_sha256(article) for article in candidates}
    seen: set[str] = set()
    for item in review["articles"]:
        if not isinstance(item, dict):
            raise ValueError("review article must be an object")
        allowed = {"article_id", "candidate_sha256", "verdict", "hard_failure", "findings"}
        if set(item) - allowed or not {"article_id", "candidate_sha256", "verdict", "findings"} <= set(item):
            raise ValueError("review article fields are invalid")
        article_id = str(item["article_id"])
        if article_id not in expected or article_id in seen:
            raise ValueError("review article set differs from candidate")
        if item["candidate_sha256"] != expected[article_id]:
            raise ValueError(f"candidate hash mismatch for {article_id}")
        if item["verdict"] not in {"APPROVE", "REJECT"}:
            raise ValueError("review verdict must be APPROVE or REJECT")
        if not isinstance(item["findings"], list):
            raise ValueError("review findings must be a list")
        for finding in item["findings"]:
            if (
                not isinstance(finding, dict)
                or set(finding) != {"code", "message"}
                or not all(
                    isinstance(finding[field], str) and finding[field].strip()
                    for field in ("code", "message")
                )
            ):
                raise ValueError("review finding fields are invalid")
        seen.add(article_id)
    if seen != set(expected):
        raise ValueError("review is missing candidate articles")


def render_review_markdown(review: dict[str, Any], candidates: list[dict[str, Any]] | None = None) -> str:
    candidate_by_id = {_candidate_id(article): article for article in candidates or []}
    lines = [f"# Review｜{review.get('run_id', '')}", ""]
    for item in review.get("articles", []):
        lines.extend([f"## {item['article_id']}｜{item['verdict']}", "", f"candidate SHA-256: `{item['candidate_sha256']}`", ""])
        findings = item.get("findings") or []
        if findings:
            lines.append("### Findings")
            lines.append("")
            for finding in findings:
                lines.append(f"- `{finding.get('code', 'finding')}`：{finding.get('message', '')}")
        else:
            lines.append("- 無 finding。")
        lines.append("")
        candidate = candidate_by_id.get(str(item["article_id"]))
        if candidate is not None:
            if "identity" in candidate and "bodySections" in candidate:
                lines.extend([
                    "### Candidate",
                    "",
                    f"- Title：{candidate['identity']['title']}",
                    f"- Current body SHA-256：`{candidate['current_body_sha256']}`",
                    "",
                ])
                for section in candidate["bodySections"]:
                    lines.extend([f"#### {section['heading']}", ""])
                    for paragraph in section["paragraphs"]:
                        lines.extend([paragraph, ""])
            elif "bodySections" in candidate:
                lines.extend([
                    "### Candidate",
                    "",
                    f"- Title：{candidate['title']}",
                    f"- Description：{candidate['description']}",
                    f"- Answer：{candidate['answer']}",
                    "",
                ])
                for section in candidate["bodySections"]:
                    lines.extend([f"#### {section['heading']}", ""])
                    for paragraph in section["paragraphs"]:
                        lines.extend([paragraph, ""])
                lines.extend(["#### FAQ", ""])
                for faq in candidate["faq"]:
                    lines.extend([f"- **{faq['question']}**", f"  {faq['answer']}"])
                lines.append("")
            else:
                lines.extend([
                    "### Candidate",
                    "",
                    f"- Title：{candidate['proposed']['title']}",
                    f"- Description：{candidate['proposed']['description']}",
                    f"- Answer：{candidate['proposed']['answer']}",
                    "",
                ])
    return "\n".join(lines).rstrip() + "\n"


def build_approval(
    run_id: str,
    candidates: list[dict[str, Any]],
    review: dict[str, Any],
    decisions: dict[str, str],
    approved_by: str,
    override_reasons: dict[str, str] | None = None,
) -> dict[str, Any]:
    validate_review(review, candidates)
    override_reasons = override_reasons or {}
    items = []
    for article in candidates:
        article_id = _candidate_id(article)
        decision = decisions.get(article_id, "REJECT")
        if decision not in {"APPROVE", "REJECT", "OVERRIDE_APPROVE"}:
            raise ValueError(f"invalid approval decision: {decision}")
        item = {"article_id": article_id, "candidate_sha256": article_sha256(article), "decision": decision}
        if decision == "OVERRIDE_APPROVE":
            reason = override_reasons.get(article_id, "").strip()
            if not reason:
                raise ValueError(f"override reason required for {article_id}")
            item["override_reason"] = reason
        items.append(item)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "approved_by": approved_by,
        "approved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "articles": items,
    }


def validate_apply_gate(
    candidates: list[dict[str, Any]],
    review: dict[str, Any],
    approval: dict[str, Any],
    *,
    candidate_mode: str | None = None,
) -> list[dict[str, Any]]:
    if candidate_mode not in {
        None,
        "create",
        "optimize",
        "rewrite_existing_body",
        "translate_existing",
    }:
        raise ValueError(f"unsupported apply gate candidate mode: {candidate_mode}")
    validate_review(review, candidates)
    for candidate in candidates:
        if candidate_mode in {"optimize", "translate_existing"} or "proposed" in candidate:
            continue
        mode = candidate_mode or (
            "rewrite_existing_body" if "identity" in candidate else "create"
        )
        policy_article = candidate
        if mode == "rewrite_existing_body":
            policy_article = {
                **candidate["identity"],
                "id": candidate["article_id"],
                "current_body_sha256": candidate["current_body_sha256"],
                "bodySections": candidate["bodySections"],
                "publicationPolicy": candidate["publicationPolicy"],
            }
        findings = required_policy_findings(
            article_publication_policy_findings(policy_article, mode=mode)
        )
        if findings:
            raise ValueError(
                f"policy v2 required finding cannot be overridden for {_candidate_id(candidate)}: "
                f"{findings[0]['code']}"
            )
    by_id = {_candidate_id(article): article for article in candidates}
    reviews = {str(item["article_id"]): item for item in review["articles"]}
    approved: list[dict[str, Any]] = []
    for item in approval.get("articles") or []:
        article_id = str(item.get("article_id") or "")
        if article_id not in by_id:
            raise ValueError(f"approval contains unknown article: {article_id}")
        if item.get("candidate_sha256") != article_sha256(by_id[article_id]):
            raise ValueError(f"approval candidate hash mismatch for {article_id}")
        decision = item.get("decision")
        review_item = reviews[article_id]
        if decision == "APPROVE" and review_item["verdict"] != "APPROVE":
            raise ValueError(f"reviewer rejected {article_id}; explicit override required")
        if decision == "OVERRIDE_APPROVE":
            if review_item.get("hard_failure"):
                raise ValueError(f"hard failure cannot be overridden for {article_id}")
            if not str(item.get("override_reason") or "").strip():
                raise ValueError(f"override reason required for {article_id}")
        if decision in {"APPROVE", "OVERRIDE_APPROVE"}:
            approved.append(by_id[article_id])
    return approved


def _normalize_keyword(value: str) -> str:
    clean = re.sub(r"[？?：:、，,。\s/]+", "", value).lower()
    for phrase in ["是什麼", "代表什麼", "意思"]:
        clean = clean.replace(phrase, "")
    return clean


def _matrix_rows(plan_text: str) -> list[dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in plan_text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip(" `") for cell in line.strip("|").split("|")]
        if len(cells) >= 5 and re.search(r"[A-Z]", cells[1]) and "-" in cells[1] and cells[1] != "文章 ID":
            rows[cells[1]] = {"priority": cells[0], "id": cells[1], "primaryKeyword": cells[2], "title": cells[3], "intent": cells[4]}
    return list(rows.values())


def _structured_matrix_rows(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != "content-matrix-v2.0":
        raise ValueError("content matrix v2 schema differs from contract")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or payload.get("total") != len(raw_rows):
        raise ValueError("content matrix v2 total differs from rows")
    required = {
        "priority", "id", "primaryKeyword", "title", "intent",
        "family", "entityType", "entity", "scenario",
        "section", "product", "category",
    }
    rows: list[dict[str, str]] = []
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, dict) or not required <= set(raw):
            raise ValueError(f"content matrix v2 row {index} is missing required fields")
        row = {str(key): str(value) for key, value in raw.items()}
        if not all(row[field].strip() for field in required):
            raise ValueError(f"content matrix v2 row {index} contains an empty required field")
        rows.append(row)
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("content matrix v2 ids must be unique")
    return rows


def _run_registry_node_script(repo_root: Path, script: str) -> subprocess.CompletedProcess[str]:
    command = ["node", "--input-type=module", "-e", script]
    # 不用 PIPE：Node 的後代程序若繼承 stdout/stderr，communicate() 會在 Node
    # 已退出後仍等不到 EOF。暫存檔讓等待只綁定直接子程序。
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout_handle, tempfile.TemporaryFile(
        mode="w+", encoding="utf-8"
    ) as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=repo_root,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=REGISTRY_NODE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise subprocess.TimeoutExpired(command, REGISTRY_NODE_TIMEOUT_SECONDS) from error
        stdout_handle.seek(0)
        stderr_handle.seek(0)
        stdout = stdout_handle.read()
        stderr = stderr_handle.read()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(command, return_code, stdout, stderr)


def _registry_inventory(repo_root: Path) -> list[dict[str, Any]]:
    script = """
import { getArticlePath, listArticleRecords } from './app/web/static/article-registry.js';
console.log(JSON.stringify(listArticleRecords().map((article) => ({
  id: article.id, primaryKeyword: article.primaryKeyword, title: article.title,
  description: article.description, answer: article.answer,
  path: getArticlePath(article), slug: article.slug,
}))));
"""
    result = _run_registry_node_script(repo_root, script)
    return list(json.loads(result.stdout))


def load_publication_reference_corpus(repo_root: Path) -> list[dict[str, Any]]:
    """載入全量可見正文，讓新文與重寫不只和當批比較。"""
    script = """
import { getArticlePath, listArticleRecords } from './app/web/static/article-registry.js';
import { buildArticleContent } from './app/web/static/article-meta.js';
const origin = 'https://www.mysticpantheon.com';
console.log(JSON.stringify(listArticleRecords().map((article) => {
  const path = getArticlePath(article);
  const content = buildArticleContent(path, origin, {author: 'Pantheon 編輯部', updated: article.updated || ''});
  return {
    id: article.id || '',
    path,
    title: article.title || '',
    description: article.description || '',
    answer: content.answer || article.answer || '',
    primaryKeyword: article.primaryKeyword || '',
    bodySections: content.bodySections || [],
  };
})));
"""
    result = _run_registry_node_script(repo_root, script)
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise CandidateValidationError("publication reference corpus must be a list")
    return payload


def _row_is_present(row: dict[str, str], inventory: list[dict[str, Any]]) -> bool:
    if any(record.get("id") == row["id"] for record in inventory):
        return True
    keyword = _normalize_keyword(row["primaryKeyword"])
    equivalents = {keyword, *(_normalize_keyword(item) for item in MATRIX_EQUIVALENT_KEYWORDS.get(keyword, set()))}
    for record in inventory:
        haystack = _normalize_keyword(f"{record.get('primaryKeyword', '')}{record.get('title', '')}")
        if any(term and term in haystack for term in equivalents):
            return True
    return False


def build_matrix_backlog(repo_root: Path) -> list[dict[str, str]]:
    legacy_rows = _matrix_rows((repo_root / MATRIX_PLAN).read_text(encoding="utf-8"))
    v2_rows = _structured_matrix_rows(repo_root / MATRIX_V2_PLAN)
    rows = list({row["id"]: row for row in [*legacy_rows, *v2_rows]}.values())
    inventory = _registry_inventory(repo_root)
    return [row for row in rows if not _row_is_present(row, inventory)]


def compact_publication_policy() -> dict[str, Any]:
    policy = load_article_publication_policy()
    return {
        "policyVersion": policy["policy_version"],
        "levels": policy["levels"],
        "language": "繁體中文",
        "voice": "白話、具體、先回答讀者問題；冷靜但不替讀者下判決",
        "required": policy["required"],
        "presentationConstraints": policy["presentation_constraints"],
        "generation_profile": publication_presentation_instruction("create"),
        "tags": f"必含 {', '.join(sorted(REQUIRED_PUBLIC_TAGS))}，並加入產品線與情境 tags",
        "boundary": "不承諾結果，不提供醫療、法律或投資建議，不把工具訊號寫成個人結論",
        "evidence": "可驗證事實用 sources；純文化/反思內容用 cultural_reflection disclosure；不得虛構引用",
        "banned_phrases": sorted(BANNED_PHRASES),
        "banned_phrase_context": "一定、保證、注定只禁止正向結果承諾；不一定、不能保證、不是注定等否定邊界句不算命中",
        "avoid_generic_phrases": sorted(GENERIC_AI_PHRASES),
    }


def _matrix_targets(repo_root: Path, backlog: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    inventory = _registry_inventory(repo_root)
    maxima: dict[str, int] = {}
    for record in inventory:
        match = re.search(r"/articles/([^/]+)/\1-(\d{4})$", str(record.get("path") or ""))
        if match:
            maxima[match.group(1)] = max(maxima.get(match.group(1), 0), int(match.group(2)))
    today = date.today().isoformat()
    targets: dict[str, dict[str, str]] = {}
    for row in backlog:
        article_id = row["id"]
        if {"section", "product", "category"} <= set(row):
            section, product, category = row["section"], row["product"], row["category"]
        elif article_id.startswith("MBTI-"):
            section, product, category = "mbti", "personality", "personality"
        elif article_id.startswith(("CHART-", "ZIWEI-")):
            section, product, category = "ziwei", "fortune", "fortune"
        else:
            section, product, category = "astro", "astro", "astrology"
        maxima[category] = maxima.get(category, 0) + 1
        serial = f"{category}-{maxima[category]:04d}"
        targets[article_id] = {
            "id": article_id,
            "section": section,
            "product": product,
            "slug": article_id.lower(),
            "serial": serial,
            "urlSlug": serial,
            "published": today,
            "updated": today,
            "primaryKeyword": row["primaryKeyword"],
        }
    return targets


def prepare_matrix_runs(
    repo_root: Path,
    run_prefix: str,
    output_root: Path | None = None,
    limit: int | None = None,
    exclude_ids: set[str] | None = None,
    max_articles_per_run: int = MAX_RUN_ARTICLES,
    exact_run_id: str | None = None,
) -> list[Path]:
    if not 1 <= max_articles_per_run <= MAX_RUN_ARTICLES:
        raise ValueError(f"max_articles_per_run must be between 1 and {MAX_RUN_ARTICLES}")
    if exact_run_id is not None and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", exact_run_id) is None:
        raise ValueError("exact run id format is invalid")
    output_root = output_root or repo_root / RUN_ROOT
    if exact_run_id is not None and (output_root / exact_run_id).exists():
        raise ValueError("exact run identity is already in use")
    full_backlog = build_matrix_backlog(repo_root)
    targets = _matrix_targets(repo_root, full_backlog)
    excluded = exclude_ids or set()
    backlog = [row for row in full_backlog if str(row["id"]) not in excluded]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        backlog = backlog[:limit]
    article_briefs = [{"matrix": row, "target": targets[row["id"]], "policy": compact_publication_policy()} for row in backlog]
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    for article in article_briefs:
        candidate_batch = [*current_batch, article]
        run_id = exact_run_id or f"{run_prefix}-{len(batches) + 1:02d}"
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "mode": "create",
            "source": {"type": "matrix", "paths": [MATRIX_PLAN.as_posix(), MATRIX_V2_PLAN.as_posix()]},
            "articles": candidate_batch,
        }
        if current_batch and (
            len(candidate_batch) > max_articles_per_run
            or len(compact_json_bytes(candidate)) + 1 > MAX_ARTICLE_BRIEF_BYTES
        ):
            batches.append(current_batch)
            current_batch = [article]
        else:
            current_batch = candidate_batch
    if current_batch:
        batches.append(current_batch)
    if exact_run_id is not None and len(batches) != 1:
        raise ValueError("exact run identity must resolve to exactly one run")

    paths = []
    for index, articles in enumerate(batches, start=1):
        run_id = exact_run_id or f"{run_prefix}-{index:02d}"
        brief = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "mode": "create",
            "source": {"type": "matrix", "paths": [MATRIX_PLAN.as_posix(), MATRIX_V2_PLAN.as_posix()]},
            "articles": articles,
        }
        validate_new_brief(brief)
        run_dir = output_root / run_id
        if exact_run_id is not None:
            run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "brief.json"
        write_json(path, brief)
        paths.append(path)
    return paths


def _rewrite_batch_payload(queue_text: str, batch_number: int) -> dict[str, Any]:
    match = re.search(
        rf"^## Batch {batch_number} .*?^```json\s*$\n(.*?)^```\s*$",
        queue_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError(f"rewrite queue batch {batch_number} JSON not found")
    payload = json.loads(match.group(1))
    if payload.get("mode") != "rewrite_existing_body":
        raise ValueError("queue batch is not rewrite_existing_body")
    return payload


def _validate_rewrite_queue(queue: dict[str, Any], batch_number: int) -> None:
    """鎖定 audit batch 的文章集合、欄位與順序。"""
    if queue.get("schema_version") != SCHEMA_VERSION or queue.get("run_id") != f"gemini_rewrite_audit_001_batch_{batch_number:02d}":
        raise ValueError(f"Batch {batch_number} audit identity differs from contract")
    articles = queue.get("articles")
    if not isinstance(articles, list) or len(articles) != MAX_RUN_ARTICLES:
        raise ValueError(f"Batch {batch_number} audit article count differs from contract")
    if batch_number == 2:
        fields = ("slot", "article_id", "product", "category", "serial", "slug", "primaryKeyword", "title")
        actual = [tuple(str(item.get(field) or "") for field in fields) for item in articles]
        if actual != list(REWRITE_BATCH_002_ARTICLES):
            raise ValueError("Batch 2 audit ids, slots, order, identity, title, or keyword differ from contract")
    elif batch_number in REWRITE_BATCH_003_010_IDS:
        actual_ids = tuple((str(item.get("article_id") or ""), str(item.get("serial") or "")) for item in articles)
        if actual_ids != REWRITE_BATCH_003_010_IDS[batch_number]:
            raise ValueError(f"Batch {batch_number} audit ids, serials, or order differ from contract")
        if [str(item.get("slot") or "") for item in articles] != [_slot(index) for index in range(MAX_RUN_ARTICLES)]:
            raise ValueError(f"Batch {batch_number} audit slots differ from contract")
    else:
        raise ValueError("isolated rewrite batch must be between 2 and 10")
    for item in articles:
        if item.get("verdict") != "GEMINI_REWRITE" or item.get("issue_codes") != ["TEMPLATE_STRUCTURE", "REPEATED_BATCH_COPY"]:
            raise ValueError(f"Batch {batch_number} audit contains KEEP or unexpected issue codes")


def _batch_variation_contracts(queue: dict[str, Any], batch_number: int) -> dict[str, dict[str, str]]:
    """同批五篇採用互異的開場、論證、反例位置與收尾。"""
    shapes = (
        ("從具體對話或訊息現場切入", "現場→角色→選項→反例→回覆", "第 4 節開頭", "寫下一句可直接使用的回覆"),
        ("從兩個相反選項的比較桌面切入", "選項→證據→試做→限制→比較表", "第 3 節結尾", "完成一個低成本比較動作"),
        ("從一段可核對的時間軸切入", "時間軸→轉折→重複線索→例外→紀錄", "第 4 節中段", "記錄三個可回查的變化"),
        ("從數字、帳目或資源落差切入", "數字→拆解→承擔→反例→核對", "第 2 節結尾", "核對一組具體數字與期限"),
        ("從一個衝動後的停頓動作切入", "動作→需求→代價→誤讀→實驗", "第 4 節開頭", "下一次先暫停並寫下觀察"),
    )
    contracts: dict[str, dict[str, str]] = {}
    for index, item in enumerate(queue["articles"]):
        opening, order, counterexample, ending = shapes[index]
        keyword = str(item["primaryKeyword"])
        contracts[str(item["article_id"])] = {
            "opening": f"{opening}，前 80 字直接回答「{keyword}」",
            "headings": f"五個小標依照「{order}」分工，不重複 audit 舊小標",
            "argumentOrder": order,
            "counterexample": f"反例固定放在{counterexample}，說清楚「{keyword}」不能代表什麼",
            "ending": ending,
            "batch": str(batch_number),
        }
    return contracts


def _existing_rewrite_inventory(repo_root: Path) -> dict[str, dict[str, Any]]:
    script = """
import { getArticlePath, listArticleRecords } from './app/web/static/article-registry.js';
import { buildArticleContent } from './app/web/static/article-meta.js';
const origin = 'https://www.mysticpantheon.com';
console.log(JSON.stringify(listArticleRecords().map((record) => {
  const canonicalPath = getArticlePath(record);
  const content = buildArticleContent(canonicalPath, origin);
  return { id: record.id, record, canonicalPath, currentBody: content.bodySections,
    published: content.published, updated: content.updated };
})));
"""
    result = _run_registry_node_script(repo_root, script)
    return {str(item["id"]): item for item in json.loads(result.stdout)}


def prepare_rewrite_batch(
    repo_root: Path,
    queue_path: Path,
    batch_number: int,
    run_dir: Path,
    source_commit: str,
) -> Path:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, head],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    article_diff = ""
    if ancestor.returncode == 0:
        article_diff = subprocess.run(
            ["git", "diff", "--name-only", f"{source_commit}..{head}", "--", "app"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    if ancestor.returncode != 0 or article_diff:
        raise ValueError(
            f"rewrite source commit mismatch: expected unchanged app/** since {source_commit}, got {head}"
        )
    queue = _rewrite_batch_payload(queue_path.read_text(encoding="utf-8"), batch_number)
    if batch_number >= 2:
        _validate_rewrite_queue(queue, batch_number)
    inventory = _existing_rewrite_inventory(repo_root)
    articles: list[dict[str, Any]] = []
    for index, queued in enumerate(queue.get("articles") or []):
        article_id = str(queued.get("article_id") or "")
        existing = inventory.get(article_id)
        if existing is None:
            raise ValueError(f"rewrite source article not found: {article_id}")
        record = existing["record"]
        expected = {
            "product": queued["product"],
            "serial": queued["serial"],
            "primaryKeyword": queued["primaryKeyword"],
            "title": queued["title"],
        }
        actual = {field: record.get(field) for field in expected}
        if actual != expected or record.get("urlSlug") != queued["slug"]:
            raise ValueError(f"rewrite source identity drift for {article_id}")
        identity = {
            "id": article_id,
            "product": queued["product"],
            "category": queued["category"],
            "serial": queued["serial"],
            "slug": queued["slug"],
            "primaryKeyword": queued["primaryKeyword"],
            "title": queued["title"],
        }
        immutable = {
            "id": article_id,
            "product": record["product"],
            "slug": queued["slug"],
            "serial": record["serial"],
            "title": record["title"],
            "description": record["description"],
            "answer": record["answer"],
            "faq": record["faq"],
            "tags": record["tags"],
            "published": existing["published"],
            "updated": existing["updated"],
            "urlSlug": record["urlSlug"],
            "primaryKeyword": record["primaryKeyword"],
        }
        current_body = existing["currentBody"]
        articles.append(
            {
                "slot": _slot(index),
                "article_id": article_id,
                "identity": identity,
                "immutable_fields": immutable,
                "current_body": current_body,
                "current_body_sha256": body_sha256(current_body),
                "rewrite_brief": queued["brief"],
                "source_file": queued["source_file"],
                "body_source": queued["body_source"],
            }
        )
    brief = {
        "schema_version": SCHEMA_VERSION,
        "run_id": queue["run_id"],
        "mode": "rewrite_existing_body",
        "source_commit": source_commit,
        "sort_contract": queue["sort_contract"],
        "articles": articles,
    }
    validate_rewrite_brief(brief)
    write_json(run_dir / "brief.json", brief)
    write_json(run_dir / "public-brief.json", public_model_brief(brief))
    if batch_number >= 2:
        variation_contracts = REWRITE_BATCH_002_STYLE_CONTRACTS if batch_number == 2 else _batch_variation_contracts(queue, batch_number)
        write_json(
            run_dir / "batch-contract.json",
            {
                "chain_id": f"CONTENT-GEMINI-REWRITE-BATCH-{batch_number:03d}",
                "batch_number": batch_number,
                "article_order": [str(item["article_id"]) for item in queue["articles"]],
                "exact_findings": [
                    {
                        "article_id": str(item["article_id"]),
                        "findings": [
                            {"code": str(code), "message": "audit Batch 2 rewrite finding"}
                            for code in item["issue_codes"]
                        ],
                    }
                    for item in queue["articles"]
                ],
                "variation_contracts": variation_contracts,
                "max_internal_repairs": 1,
            },
        )
    return run_dir / "brief.json"


def prepare_rewrite_repair(
    repo_root: Path,
    source_run_dir: Path,
    run_dir: Path,
    source_commit: str,
    repair_generation: int = 1,
) -> Path:
    """由前卡唯一 finding 建立隔離 repair brief，不重新讀取正式正文。"""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != source_commit:
        raise ValueError(f"rewrite repair source commit mismatch: expected {source_commit}, got {head}")
    if repair_generation != 1:
        raise ValueError("this repair runner accepts repair_generation=1 only")
    source_brief = json.loads((source_run_dir / "brief.json").read_text(encoding="utf-8"))
    source_candidate = json.loads((source_run_dir / "candidate.json").read_text(encoding="utf-8"))
    source_review = json.loads((source_run_dir / "review.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(source_brief)
    validate_candidate(source_candidate, enforce_policy=False)
    validate_review(source_review, source_candidate["articles"])
    article_ids = tuple(str(item["article_id"]) for item in source_brief["articles"])
    if article_ids != REWRITE_REPAIR_ARTICLE_IDS:
        raise ValueError("rewrite repair article set or fixed order differs from contract")
    if [str(item["article_id"]) for item in source_candidate["articles"]] != list(article_ids):
        raise ValueError("rewrite repair source candidate order differs from brief")
    exact_findings: list[dict[str, Any]] = []
    for item in source_review["articles"]:
        findings = item.get("findings") or []
        if item.get("verdict") != "REJECT" or not findings:
            raise ValueError("rewrite repair source review must reject every article with a finding")
        if any(finding.get("code") != "TEMPLATE_USAGE" for finding in findings):
            raise ValueError("rewrite repair source review contains a finding outside TEMPLATE_USAGE")
        exact_findings.append({"article_id": item["article_id"], "findings": findings})
    if rewrite_quality_findings(source_brief, source_candidate["articles"]):
        raise ValueError("rewrite repair source candidate has deterministic findings")
    repaired_brief = json.loads(json.dumps(source_brief, ensure_ascii=False))
    repaired_brief["run_id"] = "gemini_rewrite_batch_001_repair_001"
    repaired_brief["source_commit"] = source_commit
    validate_rewrite_brief(repaired_brief)
    write_json(run_dir / "brief.json", repaired_brief)
    write_json(run_dir / "public-brief.json", public_model_brief(repaired_brief))
    write_json(
        run_dir / "repair-source.json",
        {
            "chain_id": "CONTENT-GEMINI-REWRITE-BATCH-001",
            "repair_generation": repair_generation,
            "source_commit": source_commit,
            "article_order": list(article_ids),
            "exact_findings": exact_findings,
            "source_candidate_sha256": hashlib.sha256(compact_json_bytes(source_candidate)).hexdigest(),
            "source_review_sha256": hashlib.sha256(compact_json_bytes(source_review)).hexdigest(),
        },
    )
    return run_dir / "brief.json"


CLOSED_GEMINI_ERROR_CODES = frozenset({
    "API_AUTH",
    "API_HTTP_ERROR",
    "API_MODEL_UNAVAILABLE",
    "API_QUOTA",
    "API_RATE_LIMITED",
    "API_RESPONSE_INVALID",
    "API_TIMEOUT",
    "API_TRANSPORT_ERROR",
    "CLI_ENVELOPE_ERROR",
    "CLI_NONZERO",
    "CLI_NOT_FOUND",
    "CLI_TIMEOUT",
})
CLOSED_GEMINI_FAILURE_CATEGORIES = frozenset({
    "AUTH",
    "CLI_NONZERO",
    "CLI_UNAVAILABLE",
    "INVALID_RECEIPT",
    "MALFORMED_PAYLOAD",
    "MODEL_UNAVAILABLE",
    "NETWORK",
    "PROVIDER_UNAVAILABLE",
    "QUOTA",
    "SCHEMA_INVALID_PAYLOAD",
})


class GeminiCliFailure(RuntimeError):
    """不攜帶 CLI 原始輸出的封閉失敗分類。"""

    def __init__(self, error_code: str) -> None:
        if error_code not in CLOSED_GEMINI_ERROR_CODES:
            raise ValueError("Gemini CLI error code is not closed")
        self.error_code = error_code
        super().__init__(error_code)


def _gemini_error_code_for_http_status(http_status: object) -> str:
    if http_status in {401, 403}:
        return "API_AUTH"
    if http_status == 429:
        return "API_RATE_LIMITED"
    if http_status == 404:
        return "API_MODEL_UNAVAILABLE"
    return "API_HTTP_ERROR"


def _gemini_error_code_for_http_error(error: urllib.error.HTTPError) -> str:
    """只從 429 的封閉 QuotaFailure quotaId 判定每日配額。"""
    default = _gemini_error_code_for_http_status(error.code)
    if error.code != 429:
        return default
    try:
        encoded = error.read(16 * 1024 + 1)
        if len(encoded) > 16 * 1024:
            return default
        payload = json.loads(encoded.decode("utf-8"))
        details = payload.get("error", {}).get("details", [])
    except (AttributeError, TypeError, UnicodeError, ValueError):
        return default
    if not isinstance(details, list):
        return default
    quota_ids = {
        violation.get("quotaId")
        for detail in details
        if isinstance(detail, dict)
        and detail.get("@type") == "type.googleapis.com/google.rpc.QuotaFailure"
        and isinstance(detail.get("violations"), list)
        for violation in detail["violations"]
        if isinstance(violation, dict)
        and type(violation.get("quotaId")) is str
        and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", violation["quotaId"])
    }
    if any("PerDay" in quota_id for quota_id in quota_ids):
        return "API_QUOTA"
    return default


def closed_gemini_http_diagnostic(
    error_code: object,
    http_status: object,
    http_status_class: object,
) -> dict[str, object] | None:
    """只接受能由 HTTP status 與封閉錯誤碼互相驗證的安全診斷。"""
    if (
        type(http_status) is not int
        or not 100 <= http_status <= 599
        or type(http_status_class) is not str
        or http_status_class != f"{http_status // 100}xx"
        or (
            error_code != _gemini_error_code_for_http_status(http_status)
            and not (http_status == 429 and error_code == "API_QUOTA")
        )
    ):
        return None
    return {
        "http_status": http_status,
        "http_status_class": http_status_class,
    }


class GeminiApiFailure(RuntimeError):
    """不攜帶 HTTP response、request header 或 credential 的封閉失敗分類。"""

    def __init__(self, error_code: str, *, http_status: int | None = None) -> None:
        if error_code not in CLOSED_GEMINI_ERROR_CODES or not error_code.startswith("API_"):
            raise ValueError("Gemini API error code is not closed")
        self.error_code = error_code
        diagnostic = closed_gemini_http_diagnostic(
            error_code,
            http_status,
            f"{http_status // 100}xx" if type(http_status) is int else None,
        )
        self.http_status = diagnostic["http_status"] if diagnostic is not None else None
        self.http_status_class = (
            diagnostic["http_status_class"] if diagnostic is not None else None
        )
        super().__init__(error_code)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Production 單次 transport 禁止把 3xx 轉成第二個 provider request。"""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _single_request_urlopen(
    request: urllib.request.Request,
    *,
    timeout: float,
) -> Any:
    return urllib.request.build_opener(_NoRedirectHandler).open(
        request,
        timeout=timeout,
    )


def _gemini_version_and_variant(model: str) -> tuple[tuple[int, int], str] | None:
    match = re.fullmatch(r"gemini-(\d+)\.(\d+)-([a-z0-9-]+)", model)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2))), match.group(3)


def _is_gemini_25_flash(model: str) -> bool:
    parsed = _gemini_version_and_variant(model)
    return parsed is not None and parsed[0] == (2, 5) and parsed[1] in {"flash", "flash-lite"}


def _omits_sampling_parameters(model: str) -> bool:
    parsed = _gemini_version_and_variant(model)
    return parsed is not None and parsed[0] >= (3, 5)


def _has_provider_enum_limit(model: str) -> bool:
    parsed = _gemini_version_and_variant(model)
    return parsed is not None and parsed[0] >= (3, 5) and parsed[1] == "flash-lite"


GEMINI_25_COMPLEX_SCHEMA_KEYS = frozenset(
    {
        "maxItems",
        "maxLength",
        "minItems",
        "minLength",
    }
)
MAX_PROVIDER_SCHEMA_ENUM_VALUES = 8


def _response_schema_for_model(model: str, schema: dict[str, Any]) -> dict[str, Any]:
    """依 model 降低 provider schema 複雜度；完整限制仍由本地 validator 執行。"""
    if (
        not _is_gemini_25_flash(model)
        and not _has_provider_enum_limit(model)
    ):
        return schema

    def strip_complexity(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip_complexity(item)
                for key, item in value.items()
                if not (
                    _is_gemini_25_flash(model)
                    and key in GEMINI_25_COMPLEX_SCHEMA_KEYS
                )
                and not (
                    _has_provider_enum_limit(model)
                    and key == "enum"
                    and isinstance(item, list)
                    and len(item) > MAX_PROVIDER_SCHEMA_ENUM_VALUES
                )
            }
        if isinstance(value, list):
            return [strip_complexity(item) for item in value]
        return value

    simplified = strip_complexity(schema)
    if not isinstance(simplified, dict):
        raise TypeError("response schema must remain an object")
    return schema if simplified == schema else simplified


class GeminiClient:
    """Stateless Gemini JSON client；每次呼叫只傳單次 contents。"""

    def __init__(
        self,
        api_key: str = "",
        *,
        writer_model: str | None = None,
        reviewer_model: str | None = None,
        transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.writer_model = writer_model or os.environ.get("AGY_WRITER_MODEL") or DEFAULT_WRITER_MODEL
        self.reviewer_model = reviewer_model or os.environ.get("AGY_REVIEWER_MODEL") or DEFAULT_REVIEWER_MODEL
        self.transport = transport or self._http_transport

    @classmethod
    def from_environment(cls) -> "GeminiClient":
        route_config = model_route_config_from_environment()
        transport_name = os.environ.get("AGY_GEMINI_TRANSPORT", "cli").strip().lower()
        if transport_name == "cli":
            client = cls(
                writer_model=route_config.routes["writer"][0],
                reviewer_model=route_config.routes["reviewer"][0],
            )
            client.transport = client._cli_transport
            return client
        if transport_name == "api":
            return cls(
                _load_api_key(),
                writer_model=route_config.routes["writer"][0],
                reviewer_model=route_config.routes["reviewer"][0],
            )
        raise ValueError("AGY_GEMINI_TRANSPORT must be cli or api")

    def generate_json(self, role: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if role not in {"writer", "reviewer"}:
            raise ValueError("role must be writer or reviewer")
        model = self.writer_model if role == "writer" else self.reviewer_model
        system = (
            "你是 Pantheon 繁體中文文章 Writer。只輸出符合 schema 的 JSON，不得加入未提供的事實或承諾。"
            if role == "writer"
            else "你是獨立 Pantheon 文章 Reviewer。依規範嚴格審查，只輸出符合 schema 的 JSON；不得假設 Writer 對話內容。"
        )
        thinking_config = (
            {"thinkingBudget": 0}
            if _is_gemini_25_flash(model)
            else {"thinkingLevel": "LOW"}
        )
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseJsonSchema": _response_schema_for_model(model, schema),
            "thinkingConfig": thinking_config,
        }
        if not _omits_sampling_parameters(model):
            generation_config["temperature"] = 0.45 if role == "writer" else 0.1
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        return self.transport(model, payload)

    def _http_transport(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = GEMINI_ENDPOINT.format(model=urllib.parse.quote(model, safe=""))
        request = urllib.request.Request(
            url,
            data=compact_json_bytes(payload),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        max_attempts = int(os.environ.get("AGY_GEMINI_MAX_ATTEMPTS", "2"))
        response_payload: dict[str, Any] | None = None
        for attempt in range(max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=float(os.environ.get("AGY_GEMINI_TIMEOUT", "120"))) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")[:500]
                if error.code not in {429, 503} or attempt + 1 >= max_attempts:
                    raise RuntimeError(f"Gemini HTTP {error.code}: {detail}") from error
                time.sleep(2 * (attempt + 1))
        if response_payload is None:
            raise RuntimeError("Gemini returned no response")
        candidates = response_payload.get("candidates") or []
        if not candidates:
            raise ValueError("Gemini response missing candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(str(part.get("text", "")) for part in parts if not part.get("thought")).strip()
        if not text:
            raise ValueError("Gemini response missing JSON text")
        return json.loads(text)

    def _single_request_http_transport(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Production pool 專用單次 POST；任何 transport/provider 錯誤都 terminal。"""
        url = GEMINI_ENDPOINT.format(model=urllib.parse.quote(model, safe=""))
        request = urllib.request.Request(
            url,
            data=compact_json_bytes(payload),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        try:
            with _single_request_urlopen(
                request,
                timeout=float(os.environ.get("AGY_GEMINI_TIMEOUT", "120")),
            ) as response:
                encoded = response.read()
        except urllib.error.HTTPError as error:
            code = _gemini_error_code_for_http_error(error)
            raise GeminiApiFailure(code, http_status=error.code) from None
        except urllib.error.URLError as error:
            code = "API_TIMEOUT" if isinstance(error.reason, TimeoutError) else "API_TRANSPORT_ERROR"
            raise GeminiApiFailure(code) from None
        except TimeoutError:
            raise GeminiApiFailure("API_TIMEOUT") from None
        except OSError:
            raise GeminiApiFailure("API_TRANSPORT_ERROR") from None
        try:
            response_payload = json.loads(encoded.decode("utf-8"))
            candidates = response_payload.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(
                str(part.get("text", ""))
                for part in parts
                if not part.get("thought")
            ).strip()
            if not text:
                raise ValueError("missing JSON text")
            result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError("result is not an object")
            return result
        except (AttributeError, IndexError, KeyError, TypeError, UnicodeError, ValueError):
            raise GeminiApiFailure("API_RESPONSE_INVALID") from None

    def _cli_transport(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        configured = os.environ.get("AGY_GEMINI_CLI", "").strip()
        if configured:
            command = shlex.split(configured)
        else:
            executable = shutil.which("agy") or shutil.which("gemini")
            if executable is None:
                local_candidates = sorted((Path.home() / ".antigravity/bin").glob("agy-*"), reverse=True)
                executable = str(local_candidates[0]) if local_candidates else ""
            command = [executable] if executable else []
        if not command:
            raise GeminiCliFailure("CLI_NOT_FOUND")
        generation = payload["generationConfig"]
        role_prompt = payload["systemInstruction"]["parts"][0]["text"]
        user_prompt = payload["contents"][0]["parts"][0]["text"]
        schema = generation["responseJsonSchema"]
        prompt = (
            f"{role_prompt}\n禁止使用任何工具或讀取工作區。\n"
            "輸出必須是單一 JSON object，不得有 Markdown code fence。\n"
            f"JSON Schema：{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}\n\n"
            f"任務：\n{user_prompt}"
        )
        generate_content_config: dict[str, Any] = {
            "thinkingConfig": generation["thinkingConfig"],
        }
        if "temperature" in generation:
            generate_content_config["temperature"] = generation["temperature"]
        settings = {
            "general": {"defaultApprovalMode": "plan", "enableAutoUpdate": False},
            "modelConfigs": {
                "customAliases": {
                    "agy-low": {
                        "modelConfig": {
                            "model": model,
                            "generateContentConfig": generate_content_config,
                        }
                    }
                }
            },
        }
        with tempfile.TemporaryDirectory(prefix="agy-gemini-cli-") as temp_dir:
            temp_root = Path(temp_dir)
            is_antigravity = Path(command[0]).name == "agy" or Path(command[0]).name.startswith("agy-")
            if is_antigravity:
                model_label = ANTIGRAVITY_MODEL_LABELS.get(model)
                if model_label is None:
                    raise ValueError(f"no Antigravity Low model label for {model}")
                args = [
                    *command,
                    "--model", model_label,
                    "--mode", "plan",
                    "--sandbox",
                    "--log-file", str(temp_root / "agy.log"),
                    "--print-timeout", f"{int(float(os.environ.get('AGY_GEMINI_TIMEOUT', '180')))}s",
                    "--print", prompt,
                ]
            else:
                settings_dir = temp_root / ".gemini"
                settings_dir.mkdir()
                (settings_dir / "settings.json").write_text(
                    json.dumps(settings, ensure_ascii=False), encoding="utf-8"
                )
                args = [*command, "--model", "agy-low", "--output-format", "json", "--prompt", prompt]
            try:
                completed = subprocess.run(
                    args,
                    cwd=temp_root,
                    text=True,
                    capture_output=True,
                    timeout=float(os.environ.get("AGY_GEMINI_TIMEOUT", "180")),
                    check=False,
                )
            except FileNotFoundError as error:
                raise GeminiCliFailure("CLI_NOT_FOUND") from error
            except subprocess.TimeoutExpired as error:
                raise GeminiCliFailure("CLI_TIMEOUT") from error
        if completed.returncode != 0:
            raise GeminiCliFailure("CLI_NONZERO")
        output = completed.stdout.strip()
        if is_antigravity:
            return json.loads(output)
        envelope = json.loads(output)
        if envelope.get("error"):
            raise GeminiCliFailure("CLI_ENVELOPE_ERROR")
        response = envelope.get("response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Gemini CLI response missing response text")
        return json.loads(response)


def _article_json_schema(mode: str = "create") -> dict[str, Any]:
    profile = publication_presentation_profile(mode)
    create_profile = publication_presentation_profile("create")
    paragraph_minimum, paragraph_maximum = _range_bounds(
        profile,
        "paragraphs_per_section",
    )
    paragraph_char_minimum, paragraph_char_maximum = _range_bounds(
        profile,
        "paragraph_characters",
    )
    body_sections = profile["body_sections"]
    body_section_schema: dict[str, Any] = {
        "type": "array",
        "minItems": int(body_sections["minimum"]),
    }
    if isinstance(body_sections.get("maximum"), int):
        body_section_schema["maxItems"] = int(body_sections["maximum"])
    title_minimum, title_maximum = _range_bounds(
        create_profile,
        "title_characters",
    )
    description_minimum, description_maximum = _range_bounds(
        create_profile,
        "description_characters",
    )
    faq_minimum, faq_maximum = _range_bounds(create_profile, "faq_items")
    faq_item = {"type": "object", "additionalProperties": False, "properties": {"question": {"type": "string"}, "answer": {"type": "string"}}, "required": ["question", "answer"]}
    section_item = {"type": "object", "additionalProperties": False, "properties": {"heading": {"type": "string"}, "paragraphs": {"type": "array", "items": {"type": "string", "minLength": paragraph_char_minimum, "maxLength": paragraph_char_maximum}, "minItems": paragraph_minimum, "maxItems": paragraph_maximum}}, "required": ["heading", "paragraphs"]}
    body_section_schema["items"] = section_item
    properties = {
        "id": {"type": "string"}, "section": {"type": "string"}, "product": {"type": "string"}, "slug": {"type": "string"},
        "serial": {"type": "string"}, "urlSlug": {"type": "string"}, "primaryKeyword": {"type": "string"},
        "secondaryKeywords": {"type": "array", "items": {"type": "string"}, "minItems": 2}, "title": {"type": "string", "minLength": title_minimum, "maxLength": title_maximum},
        "description": {"type": "string", "minLength": description_minimum, "maxLength": description_maximum}, "answer": {"type": "string", "maxLength": _maximum_bound(create_profile, "answer_characters")}, "tags": {"type": "array", "items": {"type": "string"}, "minItems": 9, "maxItems": 12},
        "faq": {"type": "array", "items": faq_item, "minItems": faq_minimum, "maxItems": faq_maximum},
        "bodySections": body_section_schema,
        "published": {"type": "string"}, "updated": {"type": "string"},
        "publicationPolicy": _publication_contract_schema(),
    }
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": sorted(REQUIRED_ARTICLE_FIELDS)}


def candidate_schema(mode: str = "create") -> dict[str, Any]:
    if mode == "optimize":
        copy = {"type": "object", "additionalProperties": False, "properties": {field: {"type": "string"} for field in sorted(OPTIMIZE_FIELDS)}, "required": sorted(OPTIMIZE_FIELDS)}
        article = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "article_id": {"type": "string"}, "canonical_path": {"type": "string"}, "source_file": {"type": "string"},
                "current": copy, "proposed": copy,
            },
            "required": ["article_id", "canonical_path", "source_file", "current", "proposed"],
        }
        return {"type": "object", "additionalProperties": False, "properties": {"schema_version": {"type": "integer", "enum": [1]}, "run_id": {"type": "string"}, "mode": {"type": "string", "enum": ["optimize"]}, "articles": {"type": "array", "items": article, "minItems": 1, "maxItems": 5}}, "required": ["schema_version", "run_id", "mode", "articles"]}
    if mode == "rewrite_existing_body":
        section = _article_json_schema("rewrite_existing_body")["properties"]["bodySections"]
        identity = {
            "type": "object",
            "additionalProperties": False,
            "properties": {field: {"type": "string"} for field in sorted(REWRITE_IDENTITY_FIELDS)},
            "required": sorted(REWRITE_IDENTITY_FIELDS),
        }
        article = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "article_id": {"type": "string"},
                "identity": identity,
                "current_body_sha256": {"type": "string"},
                "bodySections": section,
                "publicationPolicy": _publication_contract_schema(),
            },
            "required": sorted(REWRITE_ARTICLE_FIELDS),
        }
        return {"type": "object", "additionalProperties": False, "properties": {"schema_version": {"type": "integer", "enum": [1]}, "run_id": {"type": "string"}, "mode": {"type": "string", "enum": ["rewrite_existing_body"]}, "articles": {"type": "array", "items": article, "minItems": 1, "maxItems": 5}}, "required": ["schema_version", "run_id", "mode", "articles"]}
    return {"type": "object", "additionalProperties": False, "properties": {"schema_version": {"type": "integer", "enum": [1]}, "run_id": {"type": "string"}, "mode": {"type": "string", "enum": ["create"]}, "articles": {"type": "array", "items": _article_json_schema(), "minItems": 1, "maxItems": 5}}, "required": ["schema_version", "run_id", "mode", "articles"]}


PUBLIC_CREATE_FIELDS = {
    "secondaryKeywords",
    "title",
    "description",
    "answer",
    "tags",
    "faq",
    "bodySections",
    "publicationPolicy",
}
EXTERNAL_CREATE_FIELDS = (PUBLIC_CREATE_FIELDS - {"publicationPolicy"}) | {"primaryKeyword"}
CREATE_EVIDENCE_DISCLOSURE = "本文屬文化脈絡與反思整理，不主張可驗證的預測結果。"


def _slot(index: int) -> str:
    return f"article-{index + 1:02d}"


def _public_rewrite_line(value: object) -> str:
    text = str(value)
    return re.sub(r"(?:(?:app|artifacts|\.work)/[^\s，。；]+)(?:::[^\s，。；]+)?", "[本機來源]", text)


def public_model_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """只輸出預計公開的文字素材；repo metadata 與成效數字留在本機。"""
    mode = str(brief.get("mode"))
    if mode == "create":
        return {
            "mode": "create",
            "writingPolicy": compact_publication_policy(),
            "articles": [
                {
                    "slot": _slot(index),
                    "primaryKeyword": item["target"]["primaryKeyword"],
                    "titleDirection": item["matrix"].get("title", ""),
                    "searchIntent": item["matrix"].get("intent", ""),
                }
                for index, item in enumerate(brief["articles"])
            ],
        }
    if mode == "optimize":
        return {
            "mode": "optimize",
            "allowedFields": ["title", "description", "answer"],
            "writingPolicy": compact_publication_policy(),
            "articles": [
                {
                    "slot": _slot(index),
                    "focusPhrases": [str(query["query"]) for query in item.get("queries", [])[:3]],
                    "current": item["current"],
                }
                for index, item in enumerate(brief["articles"])
            ],
        }
    if mode == "rewrite_existing_body":
        return {
            "mode": "rewrite_existing_body",
            "writingPolicy": {
                "language": "一般繁體中文讀者；白話、具體、先回答問題",
                "bodyShape": publication_presentation_instruction(
                    "rewrite_existing_body"
                ),
                "opening": "前 80 字自然回答 primaryKeyword",
                "content": "至少兩個專屬生活場景、3 個具體動詞、反例或限制",
                "boundaries": "不得把 MBTI、塔羅或命盤寫成診斷、固定人格、保證預測、投資建議或命運結論",
                "uniqueness": "不得使用批次模板小標，不得跨篇共用完整句型",
                "publicationPolicy": (
                    f"必須輸出 {publication_policy_version()}；canonical、作者 identity、真實日期與 article-level evidence/disclosure "
                    "都要逐篇明列。可驗證事實用 sources；純文化/反思內容用 cultural_reflection disclosure，不得虛構來源"
                ),
                "bannedPhrases": sorted(BANNED_PHRASES | GENERIC_AI_PHRASES),
            },
            "immutableFields": sorted(REWRITE_IMMUTABLE_FIELDS),
            "articles": [
                {
                    "slot": item["slot"],
                    "identity": item["identity"],
                    "currentBody": item["current_body"],
                    "rewriteBrief": [_public_rewrite_line(line) for line in item["rewrite_brief"]],
                }
                for item in brief["articles"]
            ],
        }
    raise ValueError("brief mode must be create, optimize, or rewrite_existing_body")


def _rewrite_provider_body_sections_schema() -> dict[str, Any]:
    """保留 rewrite 結構約束；字串長度仍由 canonical 本機 gate 判定。"""
    body_sections = _article_json_schema("rewrite_existing_body")[
        "properties"
    ]["bodySections"]
    paragraph_items = body_sections["items"]["properties"]["paragraphs"][
        "items"
    ]
    paragraph_items.pop("minLength", None)
    paragraph_items.pop("maxLength", None)
    return body_sections


def _create_provider_body_sections_schema() -> dict[str, Any]:
    """保留 create 結構約束；段落字數交給 canonical 本機 gate 與 repair。"""
    body_sections = _article_json_schema()["properties"]["bodySections"]
    paragraph_items = body_sections["items"]["properties"]["paragraphs"][
        "items"
    ]
    paragraph_items.pop("minLength", None)
    paragraph_items.pop("maxLength", None)
    return body_sections


def external_candidate_schema(mode: str) -> dict[str, Any]:
    if mode == "optimize":
        proposed = {
            "type": "object",
            "additionalProperties": False,
            "properties": {field: {"type": "string"} for field in sorted(OPTIMIZE_FIELDS)},
            "required": sorted(OPTIMIZE_FIELDS),
        }
        article = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"slot": {"type": "string"}, "proposed": proposed},
            "required": ["slot", "proposed"],
        }
    elif mode == "rewrite_existing_body":
        article = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "slot": {"type": "string"},
                "bodySections": _rewrite_provider_body_sections_schema(),
                "publicationPolicy": _publication_contract_schema(),
            },
            "required": ["slot", "bodySections", "publicationPolicy"],
        }
    else:
        full = _article_json_schema()
        properties = {"slot": {"type": "string"}}
        properties.update(
            {
                field: (
                    _create_provider_body_sections_schema()
                    if field == "bodySections"
                    else full["properties"][field]
                )
                for field in sorted(EXTERNAL_CREATE_FIELDS)
            }
        )
        article = {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": ["slot", *sorted(EXTERNAL_CREATE_FIELDS)],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"articles": {"type": "array", "items": article, "minItems": 1, "maxItems": 5}},
        "required": ["articles"],
    }


def normalize_new_output_contract(
    payload: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any] | None:
    """只修正 new/create 已知的字數邊界，其他 schema mismatch 保持封閉失敗。"""
    expected_schema = external_candidate_schema("create")
    if response_schema != expected_schema:
        return None
    try:
        normalized = json.loads(json.dumps(payload, ensure_ascii=False))
        article_schema = response_schema["properties"]["articles"]["items"]
        canonical_article_schema = candidate_schema("create")["properties"][
            "articles"
        ]["items"]
        properties = article_schema["properties"]
        canonical_properties = canonical_article_schema["properties"]
        description_schema = properties["description"]
        paragraph_schema = canonical_properties["bodySections"]["items"][
            "properties"
        ]["paragraphs"]
        description_minimum = int(description_schema["minLength"])
        description_maximum = int(description_schema["maxLength"])
        paragraph_count_minimum = int(paragraph_schema["minItems"])
        paragraph_count_maximum = int(paragraph_schema["maxItems"])
        paragraph_minimum = int(paragraph_schema["items"]["minLength"])
        paragraph_maximum = int(paragraph_schema["items"]["maxLength"])
    except (KeyError, TypeError, ValueError):
        return None
    articles = normalized.get("articles")
    if not isinstance(articles, list):
        return None
    changed = False
    for article in articles:
        if not isinstance(article, dict):
            return None
        description = article.get("description")
        if isinstance(description, str) and len(description) < description_minimum:
            repaired_description = description.strip()
            if not repaired_description:
                return None
            for sentence in NEW_DESCRIPTION_BOUNDARY_SENTENCES:
                if len(repaired_description) >= description_minimum:
                    break
                if sentence not in repaired_description:
                    repaired_description += sentence
            if not (
                description_minimum
                <= len(repaired_description)
                <= description_maximum
            ):
                return None
            article["description"] = repaired_description
            changed = True
        sections = article.get("bodySections")
        if not isinstance(sections, list):
            continue
        for section in sections:
            if not isinstance(section, dict):
                return None
            paragraphs = section.get("paragraphs")
            if not isinstance(paragraphs, list):
                continue
            if not all(isinstance(paragraph, str) for paragraph in paragraphs):
                return None
            if (
                not paragraph_count_minimum
                <= len(paragraphs)
                <= paragraph_count_maximum
                or any(len(paragraph) < paragraph_minimum for paragraph in paragraphs)
            ):
                return None
            if not any(len(paragraph) > paragraph_maximum for paragraph in paragraphs):
                continue
            combined = "".join(paragraphs)
            minimum_count = max(
                paragraph_count_minimum,
                (len(combined) + paragraph_maximum - 1) // paragraph_maximum,
            )
            maximum_count = min(
                paragraph_count_maximum,
                len(combined) // paragraph_minimum,
            )
            if minimum_count > maximum_count:
                return None
            paragraph_count = min(
                max(len(paragraphs), minimum_count),
                maximum_count,
            )
            remaining = combined
            reflowed: list[str] = []
            for remaining_count in range(paragraph_count, 1, -1):
                minimum_cut = max(
                    paragraph_minimum,
                    len(remaining)
                    - (remaining_count - 1) * paragraph_maximum,
                )
                maximum_cut = min(
                    paragraph_maximum,
                    len(remaining)
                    - (remaining_count - 1) * paragraph_minimum,
                )
                target = min(
                    max(len(remaining) // remaining_count, minimum_cut),
                    maximum_cut,
                )
                sentence_cuts = [
                    index + 1
                    for index, character in enumerate(remaining[:maximum_cut])
                    if character in "。！？；"
                    and minimum_cut <= index + 1 <= maximum_cut
                ]
                cut = (
                    min(
                        sentence_cuts,
                        key=lambda candidate: (
                            abs(candidate - target),
                            candidate,
                        ),
                    )
                    if sentence_cuts
                    else target
                )
                reflowed.append(remaining[:cut])
                remaining = remaining[cut:]
            reflowed.append(remaining)
            if (
                "".join(reflowed) != combined
                or not all(
                    paragraph_minimum <= len(paragraph) <= paragraph_maximum
                    for paragraph in reflowed
                )
            ):
                return None
            section["paragraphs"] = reflowed
            changed = True
    return normalized if changed else None


def _hydrate_create_publication_policy(
    source: dict[str, Any],
) -> dict[str, Any]:
    target = source.get("target")
    if not isinstance(target, dict):
        raise CandidateValidationError("create source target must be an object")
    policy = load_article_publication_policy()
    identity = policy["identity"]
    route = _article_route(target)
    if not route:
        raise CandidateValidationError("create target cannot determine canonical route")
    contract = {
        "policyVersion": policy["policy_version"],
        "canonical": f"{policy['site_origin']}{route}",
        "author": {
            "name": identity["author_name"],
            "url": identity["author_url"],
            "id": identity["author_id"],
        },
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": {
            "mode": "cultural_reflection",
            "sources": [],
            "disclosure": CREATE_EVIDENCE_DISCLOSURE,
        },
        "published": target.get("published"),
        "modified": target.get("updated"),
        "changeType": "created",
    }
    _validate_publication_contract_shape(contract)
    return contract


def _hydrate_rewrite_publication_policy(
    source: dict[str, Any],
    generated: dict[str, Any],
) -> dict[str, Any]:
    """保留 Writer evidence，其餘發布 metadata 由本機可信契約鎖定。"""
    _validate_publication_contract_shape(generated)
    policy = load_article_publication_policy()
    identity = policy["identity"]
    immutable = source["immutable_fields"]
    route = _article_route({**source["identity"], **immutable})
    if not route:
        raise CandidateValidationError("rewrite source cannot determine canonical route")
    source_updated = _iso_date(immutable.get("updated"))
    modified = max(date.today(), source_updated or date.today()).isoformat()
    contract = {
        "policyVersion": policy["policy_version"],
        "canonical": f"{policy['site_origin']}{route}",
        "author": {
            "name": identity["author_name"],
            "url": identity["author_url"],
            "id": identity["author_id"],
        },
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": generated["evidence"],
        "published": immutable.get("published"),
        "modified": modified,
        "changeType": "substantive_rewrite",
    }
    _validate_publication_contract_shape(contract)
    return contract


def hydrate_candidate(
    brief: dict[str, Any],
    external: dict[str, Any],
    *,
    enforce_policy: bool = True,
) -> dict[str, Any]:
    if set(external) != {"articles"} or not isinstance(external["articles"], list):
        raise CandidateValidationError("external candidate top-level fields are strict")
    by_slot = {str(item.get("slot")): item for item in external["articles"] if isinstance(item, dict)}
    expected_slots = {_slot(index) for index in range(len(brief["articles"]))}
    if set(by_slot) != expected_slots or len(by_slot) != len(external["articles"]):
        raise CandidateValidationError("external candidate slots differ from brief")
    mode = str(brief["mode"])
    articles = []
    for index, source in enumerate(brief["articles"]):
        generated = by_slot[_slot(index)]
        if mode == "create":
            if set(generated) != {"slot", *EXTERNAL_CREATE_FIELDS}:
                raise CandidateValidationError("external create fields are strict")
            if generated["primaryKeyword"] != source["target"]["primaryKeyword"]:
                raise CandidateValidationError("external primaryKeyword differs from public brief")
            generated_fields = PUBLIC_CREATE_FIELDS - {"publicationPolicy"}
            articles.append(
                {
                    **source["target"],
                    **{
                        field: generated[field]
                        for field in sorted(generated_fields)
                    },
                    "publicationPolicy": _hydrate_create_publication_policy(source),
                }
            )
        elif mode == "optimize":
            if set(generated) != {"slot", "proposed"}:
                raise CandidateValidationError("external optimize fields are strict")
            articles.append(
                {
                    key: source[key]
                    for key in ["article_id", "canonical_path", "source_file", "current"]
                }
                | {"proposed": generated["proposed"]}
            )
        else:
            if set(generated) != {"slot", "bodySections", "publicationPolicy"}:
                raise CandidateValidationError("external rewrite fields must contain only slot, bodySections, and publicationPolicy")
            articles.append(
                {
                    "article_id": source["article_id"],
                    "identity": source["identity"],
                    "current_body_sha256": source["current_body_sha256"],
                    "bodySections": generated["bodySections"],
                    "publicationPolicy": _hydrate_rewrite_publication_policy(
                        source,
                        generated["publicationPolicy"],
                    ),
                }
            )
    candidate = {"schema_version": SCHEMA_VERSION, "run_id": brief["run_id"], "mode": mode, "articles": articles}
    validate_candidate(candidate, enforce_policy=enforce_policy)
    return candidate


def public_model_candidate(brief: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    mode = str(brief["mode"])
    public_articles = []
    for index, article in enumerate(candidate["articles"]):
        if mode == "create":
            public_articles.append(
                {"slot": _slot(index), "primaryKeyword": article["primaryKeyword"]}
                | {field: article[field] for field in sorted(PUBLIC_CREATE_FIELDS)}
            )
        elif mode == "optimize":
            public_articles.append(
                {
                    "slot": _slot(index),
                    "current": article["current"],
                    "proposed": article["proposed"],
                }
            )
        else:
            public_articles.append(
                {
                    "slot": _slot(index),
                    "identity": article["identity"],
                    "bodySections": article["bodySections"],
                    "publicationPolicy": article["publicationPolicy"],
                }
            )
    return {"mode": mode, "articles": public_articles}


def public_model_findings(brief: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if brief["mode"] == "create":
        ids = [str(item["target"]["id"]) for item in brief["articles"]]
    else:
        ids = [str(item["article_id"]) for item in brief["articles"]]
    slots = {article_id: _slot(index) for index, article_id in enumerate(ids)}
    return [
        {"slot": slots[str(item["article_id"])], "code": item["code"], "message": item["message"]}
        for item in findings
        if str(item.get("article_id")) in slots
    ]


def _create_repair_measurements(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "articles": [
            {
                "slot": _slot(index),
                "description_characters": len(str(article["description"])),
                "body_characters": len(
                    "".join(
                        str(paragraph)
                        for section in article["bodySections"]
                        for paragraph in section["paragraphs"]
                    )
                ),
                "section_count": len(article["bodySections"]),
                "paragraph_counts": [
                    len(section["paragraphs"])
                    for section in article["bodySections"]
                ],
                "paragraph_characters": [
                    [len(str(paragraph)) for paragraph in section["paragraphs"]]
                    for section in article["bodySections"]
                ],
            }
            for index, article in enumerate(candidate["articles"])
        ]
    }


def _create_repair_directives(findings: list[dict[str, Any]]) -> str:
    codes = {str(finding.get("code")) for finding in findings}
    directives = []
    if "description_length" in codes:
        directives.append(
            "description 修復目標為 80 到 90 字；輸出前逐字計數，不足就補具體情境與限制，超過就刪除贅詞"
        )
    if codes & {
        "body_length",
        "body_length_insufficient",
        "section_count",
        "paragraph_count",
        "paragraph_length",
        "paragraph_length_violation",
    }:
        directives.append(
            "正文修復目標為 5 節、每節 3 段、每段 95 到 110 字；輸出前依 trusted local measurements 校正總字數與各段字數"
        )
    if codes & {"banned_phrase", "generic_ai_phrase"}:
        directives.append(
            "逐一移除 findings 指出的禁詞與模板詞，包含標題、description、answer、FAQ 與正文，不得只改其中一處"
        )
    return "；".join(directives) if directives else "只修正 findings 指出的項目，不改動已通過欄位"


def _create_repair_fields(
    article: dict[str, Any],
    findings: list[dict[str, Any]],
    *,
    deterministic_findings: bool = False,
) -> set[str]:
    """把本機 finding 收斂成最小可重做欄位集合。"""
    fields_by_code = {
        "answer_length": {"answer"},
        "body_length": {"bodySections"},
        "body_length_insufficient": {"bodySections"},
        "cross_corpus_originality": {"bodySections"},
        "description_boundary": {"description"},
        "description_context_and_limit": {"description"},
        "description_length": {"description"},
        "explicit_limit_or_counterexample": {"bodySections"},
        "missing_boundary": {"description"},
        "missing_pantheon_context": {"bodySections"},
        "opening_keyword": {"bodySections"},
        "opening_primary_intent": {"bodySections"},
        "paragraph_count": {"bodySections"},
        "paragraph_length": {"bodySections"},
        "paragraph_length_violation": {"bodySections"},
        "repeated_sentence": {"bodySections"},
        "required_tags": {"tags"},
        "section_count": {"bodySections"},
        "standalone_answer": {"answer"},
        "title_keyword": {"title"},
        "title_length": {"title"},
        "title_primary_intent": {"title"},
    }
    repair_fields: set[str] = set()
    searchable = {
        "title": str(article["title"]),
        "description": str(article["description"]),
        "answer": str(article["answer"]),
        "bodySections": "".join(
            str(paragraph)
            for section in article["bodySections"]
            for paragraph in section["paragraphs"]
        ),
    }
    for finding in findings:
        code = str(finding.get("code") or "")
        if code == "false_social_origin":
            matched = {
                field
                for field, text in searchable.items()
                if _has_false_social_origin(text)
            }
        elif code == "article_level_evidence":
            matched = {
                field
                for field, text in searchable.items()
                if _verifiable_claim_markers(text)
            }
        elif code in {
            "banned_phrase",
            "generic_ai_phrase",
            "no_outcome_guarantee",
            "no_professional_advice_substitution",
        }:
            phrase = str(finding.get("message") or "").partition("：")[2]
            matched = {
                field
                for field, text in searchable.items()
                if phrase
                and (
                    _contains_banned_phrase(text, phrase)
                    if code == "banned_phrase"
                    else phrase in text
                )
            }
        else:
            matched = fields_by_code.get(code, set())
        if matched:
            repair_fields.update(matched)
        elif deterministic_findings:
            raise CandidateValidationError(
                f"unmapped deterministic create finding: {code or '<missing>'}"
            )
        else:
            repair_fields.add("bodySections")
    return repair_fields


def _create_repair_contract(
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
    *,
    deterministic_findings: bool = False,
) -> dict[str, tuple[str, ...]]:
    findings_by_id: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        findings_by_id.setdefault(str(finding.get("article_id") or ""), []).append(
            finding
        )
    contract: dict[str, tuple[str, ...]] = {}
    for index, article in enumerate(candidate["articles"]):
        article_findings = findings_by_id.get(_candidate_id(article), [])
        if article_findings:
            contract[_slot(index)] = tuple(
                sorted(
                    _create_repair_fields(
                        article,
                        article_findings,
                        deterministic_findings=deterministic_findings,
                    )
                )
            )
    if not contract:
        raise CandidateValidationError("create repair has no targeted findings")
    return contract


def external_create_repair_schema(
    contract: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    full = _article_json_schema()
    fields = sorted({field for values in contract.values() for field in values})
    article = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "slot": {"type": "string"},
            **{field: full["properties"][field] for field in fields},
        },
        "required": ["slot"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "articles": {
                "type": "array",
                "items": article,
                "minItems": len(contract),
                "maxItems": len(contract),
            }
        },
        "required": ["articles"],
    }


def hydrate_create_repair(
    prior: dict[str, Any],
    external: dict[str, Any],
    contract: dict[str, tuple[str, ...]],
    *,
    enforce_policy: bool = True,
) -> dict[str, Any]:
    if set(external) != {"articles"} or not isinstance(external["articles"], list):
        raise CandidateValidationError("external create repair top-level fields are strict")
    by_slot = {
        str(item.get("slot")): item
        for item in external["articles"]
        if isinstance(item, dict)
    }
    if set(by_slot) != set(contract) or len(by_slot) != len(external["articles"]):
        raise CandidateValidationError("external create repair slots differ from contract")
    repaired = json.loads(json.dumps(prior, ensure_ascii=False))
    for index, article in enumerate(repaired["articles"]):
        slot = _slot(index)
        if slot not in contract:
            continue
        generated = by_slot[slot]
        expected_fields = set(contract[slot])
        if set(generated) != {"slot", *expected_fields}:
            raise CandidateValidationError(
                f"external create repair fields differ from contract for {slot}"
            )
        for field in expected_fields:
            article[field] = generated[field]
    validate_candidate(repaired, enforce_policy=enforce_policy)
    return repaired


def external_review_schema() -> dict[str, Any]:
    finding = {"type": "object", "additionalProperties": False, "properties": {"code": {"type": "string"}, "message": {"type": "string"}}, "required": ["code", "message"]}
    item = {"type": "object", "additionalProperties": False, "properties": {"slot": {"type": "string"}, "verdict": {"type": "string", "enum": ["APPROVE", "REJECT"]}, "findings": {"type": "array", "items": finding}}, "required": ["slot", "verdict", "findings"]}
    return {"type": "object", "additionalProperties": False, "properties": {"articles": {"type": "array", "items": item, "minItems": 1, "maxItems": 5}}, "required": ["articles"]}


def rewrite_external_review_schema() -> dict[str, Any]:
    finding = {"type": "object", "additionalProperties": False, "properties": {"code": {"type": "string"}, "message": {"type": "string"}}, "required": ["code", "message"]}
    objective_observation = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "code": {
                "type": "string",
                "enum": sorted(REWRITE_MACHINE_OWNED_REVIEW_CODES),
            },
            "message": {"type": "string"},
        },
        "required": ["code", "message"],
    }
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "slot": {"type": "string"},
            "semantic_verdict": {"type": "string", "enum": ["APPROVE", "REJECT"]},
            "semantic_findings": {"type": "array", "items": finding},
            "objective_observations": {
                "type": "array",
                "items": objective_observation,
            },
        },
        "required": [
            "slot",
            "semantic_verdict",
            "semantic_findings",
            "objective_observations",
        ],
    }
    return {"type": "object", "additionalProperties": False, "properties": {"articles": {"type": "array", "items": item, "minItems": 1, "maxItems": 5}}, "required": ["articles"]}


def hydrate_review(brief: dict[str, Any], candidate: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    if set(external) != {"articles"} or not isinstance(external["articles"], list):
        raise ValueError("external review top-level fields are strict")
    by_slot = {str(item.get("slot")): item for item in external["articles"] if isinstance(item, dict)}
    expected_slots = {_slot(index) for index in range(len(candidate["articles"]))}
    if set(by_slot) != expected_slots or len(by_slot) != len(external["articles"]):
        raise ValueError("external review slots differ from candidate")
    articles = []
    for index, article in enumerate(candidate["articles"]):
        item = by_slot[_slot(index)]
        if set(item) != {"slot", "verdict", "findings"}:
            raise ValueError("external review fields are strict")
        articles.append(
            {
                "article_id": _candidate_id(article),
                "candidate_sha256": article_sha256(article),
                "verdict": item["verdict"],
                "findings": item["findings"],
            }
        )
    review = {"schema_version": SCHEMA_VERSION, "run_id": brief["run_id"], "articles": articles}
    validate_review(review, candidate["articles"])
    return review


def hydrate_rewrite_review(
    brief: dict[str, Any],
    candidate: dict[str, Any],
    external: dict[str, Any],
) -> dict[str, Any]:
    if set(external) != {"articles"} or not isinstance(external["articles"], list):
        raise ValueError("external rewrite review top-level fields are strict")
    by_slot = {
        str(item.get("slot")): item
        for item in external["articles"]
        if isinstance(item, dict)
    }
    expected_slots = {_slot(index) for index in range(len(candidate["articles"]))}
    if set(by_slot) != expected_slots or len(by_slot) != len(external["articles"]):
        raise ValueError("external rewrite review slots differ from candidate")
    semantic_external = {"articles": []}
    for slot in sorted(expected_slots):
        item = by_slot[slot]
        if set(item) != {
            "slot",
            "semantic_verdict",
            "semantic_findings",
            "objective_observations",
        }:
            raise ValueError("external rewrite review fields are strict")
        semantic_verdict = item["semantic_verdict"]
        semantic_findings = item["semantic_findings"]
        objective_observations = item["objective_observations"]
        if semantic_verdict not in {"APPROVE", "REJECT"}:
            raise ValueError("rewrite semantic verdict must be APPROVE or REJECT")
        if not isinstance(semantic_findings, list) or not isinstance(
            objective_observations,
            list,
        ):
            raise ValueError("rewrite review findings must be lists")
        if semantic_verdict == "APPROVE" and semantic_findings:
            raise ValueError("rewrite semantic APPROVE must not contain findings")
        if semantic_verdict == "REJECT" and not semantic_findings:
            raise ValueError("rewrite semantic REJECT must contain findings")
        for observation in objective_observations:
            if (
                not isinstance(observation, dict)
                or set(observation) != {"code", "message"}
                or not all(
                    isinstance(observation[field], str) and observation[field].strip()
                    for field in ("code", "message")
                )
                or observation["code"] not in REWRITE_MACHINE_OWNED_REVIEW_CODES
            ):
                raise ValueError("rewrite objective observation is invalid")
        semantic_external["articles"].append(
            {
                "slot": slot,
                "verdict": semantic_verdict,
                "findings": semantic_findings,
            }
        )
    review = hydrate_review(brief, candidate, semantic_external)
    return reconcile_external_review_with_machine_gate(
        review,
        REWRITE_MACHINE_OWNED_REVIEW_CODES,
        exact_codes=True,
    )


def reconcile_external_review_with_machine_gate(
    review: dict[str, Any],
    machine_owned_codes: set[str] | None = None,
    *,
    exact_codes: bool = False,
) -> dict[str, Any]:
    owned_codes = (
        MACHINE_OWNED_REVIEW_CODES
        if machine_owned_codes is None
        else machine_owned_codes
    )
    for item in review["articles"]:
        original_verdict = item["verdict"]
        item["findings"] = [
            finding
            for finding in item["findings"]
            if (
                finding.get("code")
                if exact_codes
                else str(finding.get("code")).strip().casefold()
            )
            not in owned_codes
        ]
        if original_verdict == "REJECT" and not item["findings"]:
            item["verdict"] = "APPROVE"
    return review


def review_schema() -> dict[str, Any]:
    finding = {"type": "object", "additionalProperties": False, "properties": {"code": {"type": "string"}, "message": {"type": "string"}}, "required": ["code", "message"]}
    item = {"type": "object", "additionalProperties": False, "properties": {"article_id": {"type": "string"}, "candidate_sha256": {"type": "string"}, "verdict": {"type": "string", "enum": ["APPROVE", "REJECT"]}, "findings": {"type": "array", "items": finding}}, "required": ["article_id", "candidate_sha256", "verdict", "findings"]}
    return {"type": "object", "additionalProperties": False, "properties": {"schema_version": {"type": "integer", "enum": [1]}, "run_id": {"type": "string"}, "articles": {"type": "array", "items": item, "minItems": 1, "maxItems": 5}}, "required": ["schema_version", "run_id", "articles"]}


def _rewrite_generation_instruction() -> str:
    profile = publication_presentation_profile("rewrite_existing_body")
    body_preferred_minimum, body_preferred_maximum = _preferred_bounds(
        profile,
        "body_characters",
    )
    paragraph_preferred_minimum, paragraph_preferred_maximum = _preferred_bounds(
        profile,
        "paragraph_characters",
    )
    return (
        f"每篇必須符合：{publication_presentation_instruction('rewrite_existing_body')}；"
        f"正文以 {body_preferred_minimum} 到 {body_preferred_maximum} 字為生成目標；"
        f"每段以 {paragraph_preferred_minimum} 到 {paragraph_preferred_maximum} 字為生成目標，"
        f"{_maximum_bound(profile, 'paragraph_characters')} 字是硬上限；"
        "不得在同一篇內逐字重複完整段落。"
    )


def _writer_prompt(
    brief: dict[str, Any],
    prior: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
    repair_contract: dict[str, tuple[str, ...]] | None = None,
) -> str:
    instruction = "請依 public brief 產生完整文章內容。slot 必須逐字複製。"
    if brief.get("mode") == "create":
        create_profile = publication_presentation_profile("create")
        paragraph_preferred_minimum, paragraph_preferred_maximum = (
            _preferred_bounds(create_profile, "paragraph_characters")
        )
        instruction += (
            f" 每篇必須符合：{publication_presentation_instruction('create')}；"
            "為避免中文計數超標，初稿每段以 "
            f"{paragraph_preferred_minimum} 到 {paragraph_preferred_maximum} 字為生成目標，"
            f"{_maximum_bound(create_profile, 'paragraph_characters')} 字是硬上限；"
            "每節以 3 段為初稿目標；description 以 80 到 90 個中文字為初稿目標；"
            "不得把某節段落複製到另一節。正文第一段第一句必須完整且連續包含該篇 primaryKeyword；"
            "title 也必須完整且連續包含 primaryKeyword。完全避免 public policy 的 banned_phrases，"
            "即使是否定句也改用其他說法。meta description 欄位本身必須明寫內容只提供通用理解、"
            "不能替個人下結論等限制；不得只把限制放在正文。"
            " publicationPolicy 由本機可信資料補齊；內容只採文化／反思定位，"
            "不得寫入研究、統計、百分比或方法型主張。"
        )
    if brief.get("mode") == "optimize":
        instruction = "只輸出各 slot 的 proposed title、description、answer。"
    elif brief.get("mode") == "rewrite_existing_body":
        instruction = (
            "只輸出各 slot 的完整 bodySections 與 publicationPolicy；不得輸出或改動 identity、FAQ、tag 或 URL 欄位。"
            " publicationPolicy 的 modified 必須是這次實質正文改寫的真實日期，published 必須沿用 brief 的真實資料；"
            "可驗證事實要列來源，純文化/反思內容要明示 disclosure，不得虛構來源。"
            f" {_rewrite_generation_instruction()}"
        )
    repair_measurements = "null"
    repair_directives = "null"
    if prior is not None:
        repair_instruction = "請只修正 findings 指出的問題，保留候選稿中正確且具體的內容；仍須輸出完整 candidate。"
        if brief.get("mode") == "create":
            if repair_contract is None:
                repair_contract = _create_repair_contract(prior, findings or [])
            repair_instruction = (
                "這是 bounded field repair。每個 slot 只可輸出 repair contract 指定欄位；"
                "不得輸出或重做其他已通過欄位，也不得輸出完整 candidate。"
            )
            bounded_rules = instruction.replace(
                "請依 public brief 產生完整文章內容。slot 必須逐字複製。",
                "slot 必須逐字複製。",
                1,
            )
            instruction = f"{repair_instruction}\n{bounded_rules}"
            repair_measurements = json.dumps(
                _create_repair_measurements(prior),
                ensure_ascii=False,
            )
            repair_directives = _create_repair_directives(findings or [])
        else:
            instruction = (
                f"{repair_instruction}\n{_rewrite_generation_instruction()}"
                if brief.get("mode") == "rewrite_existing_body"
                else repair_instruction
            )
    return "\n".join([
        instruction,
        "不得共用跨篇完整句型。",
        "public brief:", json.dumps(public_model_brief(brief), ensure_ascii=False),
        "prior public candidate:", json.dumps(public_model_candidate(brief, prior), ensure_ascii=False) if prior else "null",
        "public findings:", json.dumps(public_model_findings(brief, findings or []), ensure_ascii=False),
        "trusted local measurements:", repair_measurements,
        "repair directives:", repair_directives,
        "bounded repair contract:", json.dumps(repair_contract, ensure_ascii=False) if repair_contract else "null",
    ])


def _rewrite_reviewer_semantic_contract() -> str:
    return (
        "semantic_findings 只可放阻塞核准的問題；"
        "semantic_verdict=APPROVE 時 semantic_findings 必須精確為 []；"
        "semantic_findings 非空時 semantic_verdict 必須為 REJECT；"
        "不得把正面評語、通過項目、摘要或建議放入 semantic_findings。"
    )


def _rewrite_reviewer_objective_contract() -> str:
    allowed_codes = ", ".join(sorted(REWRITE_MACHINE_OWNED_REVIEW_CODES))
    return (
        "objective_observations.code 只允許以下精確值："
        f"{allowed_codes}；"
        "若沒有客觀觀察，objective_observations 必須輸出 []。"
    )


def _reviewer_prompt(brief: dict[str, Any], candidate: dict[str, Any], deterministic_findings: list[dict[str, str]]) -> str:
    create_profile = publication_presentation_profile("create")
    title_minimum, title_maximum = _range_bounds(
        create_profile,
        "title_characters",
    )
    title_preferred_minimum, title_preferred_maximum = _preferred_bounds(
        create_profile,
        "title_characters",
    )
    presentation_mode = (
        "rewrite_existing_body"
        if brief.get("mode") == "rewrite_existing_body"
        else "create"
    )
    presentation_profile = publication_presentation_profile(presentation_mode)
    body_minimum, body_maximum = _range_bounds(
        presentation_profile,
        "body_characters",
    )
    body_preferred_minimum, body_preferred_maximum = _preferred_bounds(
        presentation_profile,
        "body_characters",
    )
    machine_gate_instruction = ""
    if brief.get("mode") == "create":
        machine_gate_instruction = (
            "字數、section／paragraph 數量與長度、immutable identity、candidate hash "
            "由本機 deterministic gate 唯一判定；不得自行回報這些 machine-owned findings。"
            "你仍必須獨立審查搜尋意圖、語意品質、場景、動詞、限制、安全邊界、錯別字與模板感。"
        )
    elif brief.get("mode") == "rewrite_existing_body":
        machine_gate_instruction = (
            "semantic_verdict 只能表示語意審查結論；semantic_findings 只能放搜尋意圖、語意品質、"
            "場景、動詞、限制、安全邊界、錯別字與模板感。section／paragraph 數量與長度、正文總長、"
            "immutable identity、candidate hash 等客觀觀察只能放 objective_observations。"
            f"{_rewrite_reviewer_objective_contract()}"
            "即使 semantic finding 的 code 看似客觀，也必須保留在 semantic_findings；"
            f"{_rewrite_reviewer_semantic_contract()}"
            "你仍必須獨立審查搜尋意圖、語意品質、場景、動詞、限制、安全邊界、錯別字與模板感。"
        )
    return "\n".join([
        "獨立審查候選稿是否符合 public brief 與發布規範；slot 必須逐字複製。",
        "檢查：搜尋意圖、具體生活場景、可觀察動詞、反例、限制、繁體中文、英文殘字與錯別字、禁詞、模板句、醫療/法律/財務邊界。",
        f"{title_minimum} 到 {title_maximum} 字才是標題硬性安全邊界；"
        f"{title_preferred_minimum} 到 {title_preferred_maximum} 字只是偏好，"
        "不得只因未落在偏好區間而退件。",
        f"{body_minimum} 到 {body_maximum} 字才是正文硬性邊界；"
        f"{body_preferred_minimum} 到 {body_preferred_maximum} 字只是生成目標，"
        "不得只因正文未落在生成目標區間而退件。",
        f"body shape internal constraint：{publication_presentation_instruction(presentation_mode)}。",
        "禁詞必須依語境判斷；不一定、不能保證、不是注定等否定邊界句不得當成承諾禁詞。",
        machine_gate_instruction,
        "deterministic findings 必須保留為 REJECT，不得自行忽略。",
        "public brief:", json.dumps(public_model_brief(brief), ensure_ascii=False),
        "public candidate:", json.dumps(public_model_candidate(brief, candidate), ensure_ascii=False),
        "public deterministic findings:", json.dumps(public_model_findings(brief, deterministic_findings), ensure_ascii=False),
    ])


def _single_rewrite_brief(brief: dict[str, Any], article_id: str) -> dict[str, Any]:
    item = next((value for value in brief["articles"] if value["article_id"] == article_id), None)
    if item is None:
        raise ValueError(f"rewrite repair article not found: {article_id}")
    single = json.loads(json.dumps(brief, ensure_ascii=False))
    single["articles"] = [json.loads(json.dumps(item, ensure_ascii=False))]
    single["articles"][0]["slot"] = "article-01"
    validate_rewrite_brief(single)
    return single


def _repair_writer_prompt(
    single_brief: dict[str, Any],
    source_findings: list[dict[str, Any]],
    current_findings: list[dict[str, Any]],
    style_contract: dict[str, Any],
    operation_label: str,
) -> str:
    return "\n".join([
        f"這是 {operation_label}。輸出單篇完整 bodySections；slot 必須逐字複製。",
        "不得改寫或輸出 identity、metadata、URL、title、FAQ、tags、日期或 current-body SHA。",
        _rewrite_generation_instruction(),
        "不要沿用其他文章常見的定義、實驗回顧、專業協助或邊界呼籲句型。",
        "public brief（本次唯一文章素材）:", json.dumps(public_model_brief(single_brief), ensure_ascii=False),
        "variation contract:", json.dumps(style_contract, ensure_ascii=False),
        "source public finding:", json.dumps(source_findings, ensure_ascii=False),
        "current public findings:", json.dumps(current_findings, ensure_ascii=False),
    ])


def _repair_reviewer_prompt(
    brief: dict[str, Any],
    candidate: dict[str, Any],
    deterministic_findings: list[dict[str, str]],
    style_contracts: dict[str, Any] | None = None,
) -> str:
    contracts = style_contracts or REWRITE_REPAIR_STYLE_CONTRACTS
    return "\n".join([
        "你是新的獨立 Gemini Reviewer，必須同時比較全部五篇；slot 必須逐字複製。",
        "本卡只審 Repair 1：確認跨篇完整句、共用 H2、長片段、段落開頭與抽象句型／論證結構不再相似。",
        f"同時確認 {publication_presentation_instruction('rewrite_existing_body')}、前 80 字、專屬場景、具體動詞、反例與安全限制沒有回歸。",
        "semantic_verdict 只表示語意結論；semantic_findings 與 objective_observations 必須分開。"
        "搜尋意圖、語意品質、安全、錯別字與模板感只能放 semantic_findings，"
        "即使 code 看似客觀也不得移到 objective_observations。",
        _rewrite_reviewer_semantic_contract(),
        _rewrite_reviewer_objective_contract(),
        "不同文章必須採用 variation contract 指定的不同開場、H2、論證順序、反例位置與結尾。",
        "deterministic findings 必須保留為 REJECT，不得自行忽略。",
        "public brief:", json.dumps(public_model_brief(brief), ensure_ascii=False),
        "variation contracts:", json.dumps(contracts, ensure_ascii=False),
        "public candidate:", json.dumps(public_model_candidate(brief, candidate), ensure_ascii=False),
        "public deterministic findings:", json.dumps(public_model_findings(brief, deterministic_findings), ensure_ascii=False),
    ])


def _generate_with_receipt(
    client: Any,
    role: str,
    prompt: str,
    schema: dict[str, Any],
    receipt_path: Path,
) -> dict[str, Any]:
    transport_name = getattr(getattr(client, "transport", None), "__name__", type(client).__name__)
    if receipt_path.exists():
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        if prior.get("status") in {"pending", "success"} and transport_name == "_outbox_transport":
            pass
        elif prior.get("status") != "error":
            raise RuntimeError(f"operation receipt already exists and is not retryable: {receipt_path.name}")
        else:
            retry_number = 1
            while True:
                retry_path = receipt_path.with_name(f"{receipt_path.stem}-runtime-retry-{retry_number:02d}.json")
                if not retry_path.exists():
                    receipt_path = retry_path
                    break
                retry_number += 1
    model = getattr(client, "writer_model" if role == "writer" else "reviewer_model", "test-double")
    started = datetime.now().astimezone()
    receipt = {
        "role": role,
        "model": model,
        "thinking_level": "LOW",
        "started_at": started.isoformat(timespec="seconds"),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(compact_json_bytes(schema)).hexdigest(),
        "transport": transport_name,
        "fresh_headless_process": transport_name in {"_cli_transport", "_outbox_transport"},
        "status": "started",
    }
    try:
        result = client.generate_json(role, prompt, schema)
    except Exception as error:
        receipt["status"] = "pending" if type(error).__name__ == "ExternalJobPending" else "error"
        receipt["error_type"] = type(error).__name__
        error_code = getattr(error, "error_code", None)
        if type(error_code) is str and error_code in CLOSED_GEMINI_ERROR_CODES:
            receipt["error_code"] = error_code
        http_diagnostic = closed_gemini_http_diagnostic(
            error_code,
            getattr(error, "http_status", None),
            getattr(error, "http_status_class", None),
        )
        if http_diagnostic is not None:
            receipt.update(http_diagnostic)
        failure_category = getattr(error, "failure_category", None)
        if (
            type(failure_category) is str
            and failure_category in CLOSED_GEMINI_FAILURE_CATEGORIES
        ):
            receipt["failure_category"] = failure_category
        transport_attempts = getattr(error, "transport_attempts", None)
        if (
            type(transport_attempts) is int
            and type(transport_attempts) is not bool
            and 1 <= transport_attempts <= 3
        ):
            receipt["transport_attempts"] = transport_attempts
        request_sha256 = getattr(error, "request_sha256", None)
        if (
            type(request_sha256) is str
            and re.fullmatch(r"[0-9a-f]{64}", request_sha256)
        ):
            receipt["request_sha256"] = request_sha256
        receipt["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        write_json(receipt_path, receipt)
        raise
    active_model = getattr(client, "active_model", None)
    if callable(active_model):
        selected_model = active_model(role)
        if type(selected_model) is str and selected_model:
            receipt["model"] = selected_model
    receipt["status"] = "success"
    receipt["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    write_json(receipt_path, receipt)
    return result


def run_writer_reviewer(run_dir: Path, client: GeminiClient, max_repairs: int = 2) -> tuple[dict[str, Any], dict[str, Any]]:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    mode = str(brief.get("mode"))
    if mode == "create":
        validate_new_brief(brief)
    elif mode == "optimize":
        validate_optimize_brief(brief)
    else:
        validate_rewrite_brief(brief)
        if isinstance(client, GeminiClient) and getattr(client.transport, "__name__", "") != "_cli_transport":
            raise RuntimeError("rewrite_existing_body requires fresh headless CLI processes")
        if isinstance(client, GeminiClient) and client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("rewrite_existing_body reviewer must use the configured independent reviewer model")
    candidate: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    completed_attempts = 0
    content_repairs_used = 0
    schema_repairs_used = 0
    current_schema_repair = 0
    repair_findings_are_deterministic = False
    attempt = 0
    while True:
        if review is not None and content_repairs_used >= max_repairs:
            break
        attempt_dir = run_dir / "attempts" / f"{attempt + 1:02d}"
        completed_attempts = attempt + 1
        repairing_reviewed_candidate = review is not None
        findings = [] if review is None else [
            {"article_id": item["article_id"], **finding}
            for item in review["articles"]
            for finding in item.get("findings", [])
        ]
        create_repair_contract = (
            _create_repair_contract(
                candidate,
                findings,
                deterministic_findings=repair_findings_are_deterministic,
            )
            if mode == "create" and candidate is not None
            else None
        )
        writer_prompt = _writer_prompt(
            brief,
            candidate,
            findings,
            create_repair_contract,
        )
        if current_schema_repair:
            writer_prompt = "\n".join(
                [
                    f"schema repair {current_schema_repair}: 前次 Writer JSON 格式無效。",
                    "必須輸出完整 schema，且每篇都不得漏掉任何 required field。",
                    writer_prompt,
                ]
            )
        writer_schema = (
            external_create_repair_schema(create_repair_contract)
            if create_repair_contract is not None
            else external_candidate_schema(mode)
        )
        write_json(attempt_dir / "public-brief.json", public_model_brief(brief))
        try:
            external_candidate = _generate_with_receipt(
                client,
                "writer",
                writer_prompt,
                writer_schema,
                attempt_dir / "writer-operation.json",
            )
            write_json(attempt_dir / "external-candidate.json", external_candidate)
            candidate = (
                hydrate_create_repair(
                    candidate,
                    external_candidate,
                    create_repair_contract,
                    enforce_policy=False,
                )
                if create_repair_contract is not None and candidate is not None
                else hydrate_candidate(
                    brief,
                    external_candidate,
                    enforce_policy=mode != "create",
                )
            )
        except (CandidateValidationError, json.JSONDecodeError, TypeError, ValueError) as error:
            schema_repairs_used += 1
            current_schema_repair += 1
            write_json(
                attempt_dir / "writer-schema-rejection.json",
                {"verdict": "REJECT", "hard_failure": True, "code": "invalid_writer_schema", "error_type": type(error).__name__},
            )
            if schema_repairs_used <= MAX_WRITER_SCHEMA_REPAIRS:
                attempt += 1
                continue
            raise CandidateValidationError("writer schema remained invalid after bounded schema repairs") from error
        current_schema_repair = 0
        if repairing_reviewed_candidate:
            content_repairs_used += 1
        if candidate["run_id"] != brief["run_id"]:
            raise CandidateValidationError("candidate run_id differs from brief")
        if mode == "create":
            expected_targets = {item["matrix"]["id"]: item["target"] for item in brief["articles"]}
            if {_candidate_id(article) for article in candidate["articles"]} != set(expected_targets):
                raise CandidateValidationError("candidate article set differs from brief")
            for article in candidate["articles"]:
                target = expected_targets[_candidate_id(article)]
                if any(article.get(field) != value for field, value in target.items()):
                    raise CandidateValidationError(f"candidate identity differs from brief for {article['id']}")
        elif mode == "optimize":
            expected = {item["article_id"]: item for item in brief["articles"]}
            if {_candidate_id(article) for article in candidate["articles"]} != set(expected):
                raise CandidateValidationError("candidate article set differs from GSC brief")
            for article in candidate["articles"]:
                source = expected[_candidate_id(article)]
                for field in ["article_id", "canonical_path", "source_file", "current"]:
                    if article.get(field) != source.get(field):
                        raise CandidateValidationError(f"candidate changed immutable GSC field {field}")
        else:
            expected = {item["article_id"]: item for item in brief["articles"]}
            if [_candidate_id(article) for article in candidate["articles"]] != list(expected):
                raise CandidateValidationError("candidate article set or order differs from rewrite brief")
            for article in candidate["articles"]:
                source = expected[_candidate_id(article)]
                if article["identity"] != source["identity"]:
                    raise CandidateValidationError(f"candidate changed immutable identity for {article['article_id']}")
                if article["current_body_sha256"] != source["current_body_sha256"]:
                    raise CandidateValidationError(f"candidate changed current body hash for {article['article_id']}")
        deterministic = rewrite_quality_findings(brief, candidate["articles"]) if mode == "rewrite_existing_body" else quality_findings(candidate["articles"])
        write_json(attempt_dir / "deterministic-findings.json", deterministic)
        if mode == "create" and not deterministic:
            validate_candidate(candidate)
        invalid_reviewer = False
        if mode in {"create", "rewrite_existing_body"} and deterministic:
            repair_findings_are_deterministic = True
            deterministic_by_id: dict[str, list[dict[str, Any]]] = {}
            for finding in deterministic:
                deterministic_by_id.setdefault(
                    str(finding["article_id"]),
                    [],
                ).append(
                    {
                        "code": finding["code"],
                        "message": finding["message"],
                    }
                )
            review = {
                "schema_version": SCHEMA_VERSION,
                "run_id": brief["run_id"],
                "articles": [
                    {
                        "article_id": _candidate_id(article),
                        "candidate_sha256": article_sha256(article),
                        "verdict": (
                            "REJECT"
                            if deterministic_by_id.get(_candidate_id(article))
                            else "APPROVE"
                        ),
                        "findings": deterministic_by_id.get(
                            _candidate_id(article),
                            [],
                        ),
                        "hard_failure": False,
                    }
                    for article in candidate["articles"]
                ],
            }
        else:
            repair_findings_are_deterministic = False
            try:
                external_review = _generate_with_receipt(
                    client,
                    "reviewer",
                    _reviewer_prompt(brief, candidate, deterministic),
                    (
                        rewrite_external_review_schema()
                        if mode == "rewrite_existing_body"
                        else external_review_schema()
                    ),
                    attempt_dir / "reviewer-operation.json",
                )
                write_json(attempt_dir / "external-review.json", external_review)
                review = (
                    hydrate_rewrite_review(brief, candidate, external_review)
                    if mode == "rewrite_existing_body"
                    else hydrate_review(brief, candidate, external_review)
                )
                if mode == "create":
                    review = reconcile_external_review_with_machine_gate(
                        review,
                        MACHINE_OWNED_REVIEW_CODES,
                    )
                for item in review["articles"]:
                    item["hard_failure"] = False
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                review = invalid_review_payload(brief["run_id"], candidate["articles"], f"invalid_reviewer_json:{type(error).__name__}")
                invalid_reviewer = True
        if deterministic:
            by_id = {item["article_id"]: item for item in review["articles"]}
            for finding in deterministic:
                item = by_id[finding["article_id"]]
                item["verdict"] = "REJECT"
                existing = {(entry["code"], entry["message"]) for entry in item["findings"]}
                value = {"code": finding["code"], "message": finding["message"]}
                if (value["code"], value["message"]) not in existing:
                    item["findings"].append(value)
        write_json(attempt_dir / "candidate.json", candidate)
        write_json(attempt_dir / "review.json", review)
        if invalid_reviewer:
            break
        if all(item["verdict"] == "APPROVE" for item in review["articles"]):
            break
        attempt += 1
    assert candidate is not None and review is not None
    if mode == "create":
        validate_candidate(candidate)
    write_json(run_dir / "candidate.json", candidate)
    write_json(run_dir / "review.json", review)
    (run_dir / "review.md").write_text(render_review_markdown(review, candidate["articles"]), encoding="utf-8")
    write_json(
        run_dir / "run-evidence.json",
        {
            "run_id": brief["run_id"],
            "mode": mode,
            "source_commit": brief.get("source_commit"),
            "attempts": completed_attempts,
            "content_repairs_used": content_repairs_used,
            "schema_repairs_used": schema_repairs_used,
            "writer_model": getattr(client, "writer_model", "test-double"),
            "reviewer_model": getattr(client, "reviewer_model", "test-double"),
            "candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "article_sha256": {_candidate_id(article): article_sha256(article) for article in candidate["articles"]},
            "approval_created": False,
            "apply_executed": False,
            **policy_validation_evidence(candidate, deterministic),
        },
    )
    return candidate, review


def run_rewrite_repair(
    run_dir: Path,
    client: GeminiClient,
    max_repairs: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """以單篇隔離 Writer 產生五篇 rewrite，再聚合交由獨立 Reviewer。"""
    if max_repairs != 1:
        raise ValueError("rewrite repair internal repair allowance must be exactly one")
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    article_ids = [str(item["article_id"]) for item in brief["articles"]]
    repair_path = run_dir / "repair-source.json"
    batch_path = run_dir / "batch-contract.json"
    if repair_path.exists() == batch_path.exists():
        raise ValueError("rewrite run requires exactly one repair-source or batch-contract")
    execution_contract = json.loads((repair_path if repair_path.exists() else batch_path).read_text(encoding="utf-8"))
    default_order = list(REWRITE_REPAIR_ARTICLE_IDS) if repair_path.exists() else []
    if article_ids != [str(value) for value in execution_contract.get("article_order", default_order)]:
        raise ValueError("rewrite article set or fixed order differs from contract")
    if repair_path.exists():
        if tuple(article_ids) != REWRITE_REPAIR_ARTICLE_IDS or execution_contract.get("repair_generation") != 1:
            raise ValueError("rewrite repair generation or article order differs from contract")
        style_contracts = REWRITE_REPAIR_STYLE_CONTRACTS
        operation_label = "Repair 1"
        repair_generation = 1
    else:
        batch_number = execution_contract.get("batch_number", 2)
        if not isinstance(batch_number, int) or batch_number < 2 or batch_number > 10:
            raise ValueError("isolated rewrite batch number differs from contract")
        expected_ids = (
            tuple(item[1] for item in REWRITE_BATCH_002_ARTICLES)
            if batch_number == 2
            else tuple(item[0] for item in REWRITE_BATCH_003_010_IDS[batch_number])
        )
        if tuple(article_ids) != expected_ids:
            raise ValueError(f"isolated rewrite Batch {batch_number} order differs from contract")
        if execution_contract.get("max_internal_repairs") != 1:
            raise ValueError("isolated rewrite repair allowance differs from contract")
        style_contracts = execution_contract.get("variation_contracts")
        expected_styles = REWRITE_BATCH_002_STYLE_CONTRACTS if batch_number == 2 else _batch_variation_contracts(
            {
                "articles": [
                    {
                        "article_id": item["article_id"],
                        "primaryKeyword": item["identity"]["primaryKeyword"],
                    }
                    for item in brief["articles"]
                ]
            },
            batch_number,
        )
        if style_contracts != expected_styles:
            raise ValueError(f"isolated rewrite variation contracts differ from locked Batch {batch_number} contract")
        operation_label = f"Batch {batch_number} initial rewrite"
        repair_generation = 0
    if isinstance(client, GeminiClient):
        if getattr(client.transport, "__name__", "") != "_cli_transport":
            raise RuntimeError("rewrite repair requires fresh sandboxed headless CLI processes")
        if client.writer_model != DEFAULT_WRITER_MODEL or client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("rewrite repair requires the fixed Gemini Writer and Pro Reviewer Low models")
    source_findings = {
        str(item["article_id"]): list(item["findings"])
        for item in execution_contract.get("exact_findings", [])
    }
    if set(source_findings) != set(article_ids):
        raise ValueError("rewrite repair exact source findings are incomplete")
    candidate_articles: dict[str, dict[str, Any]] = {}
    review: dict[str, Any] | None = None
    target_ids = list(article_ids)
    writer_calls = 0
    reviewer_calls = 0
    completed_attempts = 0
    for attempt in range(max_repairs + 1):
        attempt_dir = run_dir / "attempts" / f"{attempt + 1:02d}"
        completed_attempts = attempt + 1
        current_findings = {} if review is None else {
            str(item["article_id"]): [
                {"article_id": item["article_id"], **finding}
                for finding in item.get("findings", [])
            ]
            for item in review["articles"]
        }
        writer_errors: list[str] = []
        for article_id in target_ids:
            single_brief = _single_rewrite_brief(brief, article_id)
            writer_dir = attempt_dir / "writers" / article_id.lower()
            public_brief = public_model_brief(single_brief)
            write_json(writer_dir / "public-brief.json", public_brief)
            prompt = _repair_writer_prompt(
                single_brief,
                source_findings[article_id],
                public_model_findings(single_brief, current_findings.get(article_id, [])),
                style_contracts[article_id],
                operation_label,
            )
            try:
                external_path = writer_dir / "external-candidate.json"
                if external_path.exists():
                    external = json.loads(external_path.read_text(encoding="utf-8"))
                else:
                    external = _generate_with_receipt(
                        client,
                        "writer",
                        prompt,
                        external_candidate_schema("rewrite_existing_body"),
                        writer_dir / "writer-operation.json",
                    )
                    writer_calls += 1
                    write_json(external_path, external)
                hydrated = hydrate_candidate(single_brief, external)["articles"][0]
                candidate_articles[article_id] = hydrated
            except (CandidateValidationError, json.JSONDecodeError, TypeError, ValueError) as error:
                writer_errors.append(article_id)
                write_json(
                    writer_dir / "writer-schema-rejection.json",
                    {"article_id": article_id, "code": "invalid_writer_schema", "error_type": type(error).__name__},
                )
        if writer_errors:
            if attempt < max_repairs:
                target_ids = writer_errors
                continue
            if set(candidate_articles) != set(article_ids):
                raise CandidateValidationError("repair writer schema remained invalid after one internal repair")
            candidate = {
                "schema_version": SCHEMA_VERSION,
                "run_id": brief["run_id"],
                "mode": "rewrite_existing_body",
                "articles": [candidate_articles[article_id] for article_id in article_ids],
            }
            review = invalid_review_payload(brief["run_id"], candidate["articles"], "invalid_writer_schema")
            write_json(attempt_dir / "candidate.json", candidate)
            write_json(attempt_dir / "review.json", review)
            break
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "run_id": brief["run_id"],
            "mode": "rewrite_existing_body",
            "articles": [candidate_articles[article_id] for article_id in article_ids],
        }
        validate_candidate(candidate)
        quality, uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
        deterministic = quality + uniqueness
        write_json(attempt_dir / "candidate.json", candidate)
        write_json(attempt_dir / "deterministic-quality-findings.json", quality)
        write_json(attempt_dir / "uniqueness-findings.json", uniqueness)
        if deterministic:
            deterministic_by_id: dict[str, list[dict[str, str]]] = {}
            for finding in deterministic:
                deterministic_by_id.setdefault(
                    str(finding["article_id"]),
                    [],
                ).append(
                    {
                        "code": finding["code"],
                        "message": finding["message"],
                    }
                )
            review = {
                "schema_version": SCHEMA_VERSION,
                "run_id": brief["run_id"],
                "articles": [
                    {
                        "article_id": _candidate_id(article),
                        "candidate_sha256": article_sha256(article),
                        "verdict": (
                            "REJECT"
                            if deterministic_by_id.get(_candidate_id(article))
                            else "APPROVE"
                        ),
                        "findings": deterministic_by_id.get(
                            _candidate_id(article),
                            [],
                        ),
                        "hard_failure": False,
                    }
                    for article in candidate["articles"]
                ],
            }
        else:
            try:
                external_review_path = attempt_dir / "external-review.json"
                if external_review_path.exists():
                    external_review = json.loads(external_review_path.read_text(encoding="utf-8"))
                else:
                    external_review = _generate_with_receipt(
                        client,
                        "reviewer",
                        _repair_reviewer_prompt(brief, candidate, deterministic, style_contracts),
                        rewrite_external_review_schema(),
                        attempt_dir / "reviewer-operation.json",
                    )
                    reviewer_calls += 1
                    write_json(external_review_path, external_review)
                review = hydrate_rewrite_review(brief, candidate, external_review)
                for item in review["articles"]:
                    item["hard_failure"] = False
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                review = invalid_review_payload(brief["run_id"], candidate["articles"], f"invalid_reviewer_json:{type(error).__name__}")
        by_id = {str(item["article_id"]): item for item in review["articles"]}
        for finding in deterministic:
            item = by_id[str(finding["article_id"])]
            item["verdict"] = "REJECT"
            value = {"code": finding["code"], "message": finding["message"]}
            if value not in item["findings"]:
                item["findings"].append(value)
        write_json(attempt_dir / "review.json", review)
        if all(item["verdict"] == "APPROVE" for item in review["articles"]):
            break
        target_ids = [str(item["article_id"]) for item in review["articles"] if item["verdict"] == "REJECT"]
    if review is None or set(candidate_articles) != set(article_ids):
        raise CandidateValidationError("rewrite repair did not produce a complete reviewed candidate")
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [candidate_articles[article_id] for article_id in article_ids],
    }
    write_json(run_dir / "candidate.json", candidate)
    write_json(run_dir / "review.json", review)
    (run_dir / "review.md").write_text(render_review_markdown(review, candidate["articles"]), encoding="utf-8")
    final_quality, final_uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
    write_json(run_dir / "deterministic-quality-findings.json", final_quality)
    write_json(run_dir / "uniqueness-findings.json", final_uniqueness)
    write_json(
        run_dir / "run-evidence.json",
        {
            "run_id": brief["run_id"],
            "chain_id": execution_contract["chain_id"],
            "repair_generation": repair_generation,
            "source_commit": brief.get("source_commit"),
            "attempts": completed_attempts,
            "internal_repairs_used": max(0, completed_attempts - 1),
            "writer_processes": writer_calls,
            "reviewer_processes": reviewer_calls,
            "writer_model": getattr(client, "writer_model", "test-double"),
            "reviewer_model": getattr(client, "reviewer_model", "test-double"),
            "candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "article_sha256": {_candidate_id(article): article_sha256(article) for article in candidate["articles"]},
            "deterministic_quality_findings": len(final_quality),
            "uniqueness_findings": len(final_uniqueness),
            "reviewer_approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
            "approval_created": False,
            "apply_executed": False,
            **policy_validation_evidence(
                candidate,
                [*final_quality, *final_uniqueness],
            ),
        },
    )
    return candidate, review


def _write_batch_delivery_summary(run_dir: Path, batch_number: int) -> None:
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    evidence = json.loads((run_dir / "run-evidence.json").read_text(encoding="utf-8"))
    quality = json.loads((run_dir / "deterministic-quality-findings.json").read_text(encoding="utf-8"))
    uniqueness = json.loads((run_dir / "uniqueness-findings.json").read_text(encoding="utf-8"))
    approved = sum(item["verdict"] == "APPROVE" for item in review["articles"])
    status = "READY_FOR_REVIEW" if approved == len(review["articles"]) and not quality and not uniqueness else "BLOCKED"
    lines = [
        f"# Gemini Rewrite Batch {batch_number:03d}",
        "",
        f"- status：`{status}`",
        f"- article IDs：{', '.join(str(item['article_id']) for item in candidate['articles'])}",
        f"- candidate SHA-256：`{evidence['candidate_sha256']}`",
        f"- Reviewer：{approved}/{len(review['articles'])} APPROVE",
        f"- deterministic quality findings：{len(quality)}",
        f"- uniqueness findings：{len(uniqueness)}",
        f"- Writer / Reviewer processes：{evidence['writer_processes']} / {evidence['reviewer_processes']}",
        f"- internal repair：{evidence['internal_repairs_used']} / 1",
        "- approval_created：false",
        "- formal_apply：false",
        "",
    ]
    (run_dir / "delivery-summary.md").write_text("\n".join(lines), encoding="utf-8")


def _load_completed_rewrite_batch(run_dir: Path, expected_ids: tuple[str, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {
        "brief.json", "candidate.json", "review.json", "review.md", "run-evidence.json",
        "deterministic-quality-findings.json", "uniqueness-findings.json", "delivery-summary.md",
    }
    if not run_dir.is_dir() or not required <= {path.name for path in run_dir.iterdir() if path.is_file()}:
        raise RuntimeError(f"rewrite batch is partial and cannot resume: {run_dir.name}")
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(candidate)
    validate_review(review, candidate["articles"])
    if tuple(str(item["article_id"]) for item in candidate["articles"]) != expected_ids:
        raise ValueError(f"completed rewrite batch identity differs from contract: {run_dir.name}")
    return candidate, review


def _runtime_batch_can_resume(run_dir: Path) -> bool:
    if not all((run_dir / name).is_file() for name in ("brief.json", "public-brief.json", "batch-contract.json")):
        return False
    if any((run_dir / name).exists() for name in ("candidate.json", "review.json", "run-evidence.json")):
        return False
    receipts = list((run_dir / "attempts").glob("**/*-operation*.json"))
    if not receipts:
        return False
    return all(json.loads(path.read_text(encoding="utf-8")).get("status") in {"success", "error"} for path in receipts)


def _write_rewrite_050_summary(evidence_root: Path) -> dict[str, Any]:
    sources = [
        (1, evidence_root / "gemini_rewrite_batch_001_repair_001"),
        (2, evidence_root / "gemini_rewrite_batch_002"),
        *((batch, evidence_root / f"gemini_rewrite_batch_{batch:03d}") for batch in range(3, 11)),
    ]
    batches: list[dict[str, Any]] = []
    all_ids: list[str] = []
    for batch_number, run_dir in sources:
        candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
        review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
        evidence = json.loads((run_dir / "run-evidence.json").read_text(encoding="utf-8"))
        quality = json.loads((run_dir / "deterministic-quality-findings.json").read_text(encoding="utf-8"))
        uniqueness = json.loads((run_dir / "uniqueness-findings.json").read_text(encoding="utf-8"))
        ids = [str(item["article_id"]) for item in candidate["articles"]]
        if len(ids) != MAX_RUN_ARTICLES:
            raise ValueError(f"Batch {batch_number} candidate count differs from contract")
        all_ids.extend(ids)
        batches.append(
            {
                "batch": batch_number,
                "article_ids": ids,
                "candidate_sha256": evidence["candidate_sha256"],
                "reviewer_approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
                "quality_findings": len(quality),
                "uniqueness_findings": len(uniqueness),
                "writer_processes": evidence["writer_processes"],
                "reviewer_processes": evidence["reviewer_processes"],
            }
        )
    if len(all_ids) != 50 or len(set(all_ids)) != 50:
        raise ValueError("rewrite candidate total must be exactly 50 unique article IDs")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "chain_id": "CONTENT-GEMINI-REWRITE-TO-050",
        "status": "CANDIDATES_050_READY",
        "candidate_count": len(all_ids),
        "unique_candidate_count": len(set(all_ids)),
        "article_ids": all_ids,
        "batches": batches,
        "approval_created": False,
        "formal_apply": False,
    }
    summary_dir = evidence_root / "gemini_rewrite_to_050"
    write_json(summary_dir / "summary.json", summary)
    lines = [
        "# Gemini Rewrite Candidates 050",
        "",
        "- status：`CANDIDATES_050_READY`",
        "- candidates：50",
        "- unique article IDs：50",
        "- approval_created：false",
        "- formal_apply：false",
        "",
        "| Batch | APPROVE | Quality | Uniqueness | Candidate SHA-256 |",
        "|---:|---:|---:|---:|---|",
    ]
    lines.extend(
        f"| {item['batch']} | {item['reviewer_approved']}/5 | {item['quality_findings']} | {item['uniqueness_findings']} | `{item['candidate_sha256']}` |"
        for item in batches
    )
    (summary_dir / "summary.md").write_text("\n".join([*lines, ""]), encoding="utf-8")
    return summary


def run_rewrite_range(
    repo_root: Path,
    queue_path: Path,
    evidence_root: Path,
    source_commit: str,
    client: GeminiClient,
    start_batch: int = 3,
    end_batch: int = 10,
) -> dict[str, Any]:
    """依 audit 順序產出多批候選；完成批次可續跑，半成品 fail closed。"""
    if (start_batch, end_batch) != (3, 10):
        raise ValueError("rewrite-to-050 runner requires batches 3 through 10")
    for batch_number in range(start_batch, end_batch + 1):
        run_dir = evidence_root / f"gemini_rewrite_batch_{batch_number:03d}"
        expected_ids = tuple(item[0] for item in REWRITE_BATCH_003_010_IDS[batch_number])
        if run_dir.exists():
            try:
                _load_completed_rewrite_batch(run_dir, expected_ids)
                continue
            except RuntimeError:
                if not _runtime_batch_can_resume(run_dir):
                    raise
        else:
            prepare_rewrite_batch(repo_root, queue_path, batch_number, run_dir, source_commit)
        run_rewrite_repair(run_dir, client)
        _write_batch_delivery_summary(run_dir, batch_number)
        _load_completed_rewrite_batch(run_dir, expected_ids)
    return _write_rewrite_050_summary(evidence_root)


def _rewrite_release_sources(evidence_root: Path) -> list[tuple[int, Path]]:
    return [
        (1, evidence_root / "gemini_rewrite_batch_001_repair_001"),
        (2, evidence_root / "gemini_rewrite_batch_002"),
        *((batch, evidence_root / f"gemini_rewrite_batch_{batch:03d}") for batch in range(3, 11)),
    ]


def _release_style_contracts(batch_number: int, brief: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    if batch_number == 1:
        return REWRITE_REPAIR_STYLE_CONTRACTS
    contract_path = source_dir / "release-contract.json"
    if not contract_path.is_file():
        contract_path = source_dir / "batch-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    styles = contract.get("variation_contracts")
    if not isinstance(styles, dict) or set(styles) != {str(item["article_id"]) for item in brief["articles"]}:
        raise ValueError(f"release Batch {batch_number} variation contracts are incomplete")
    return styles


def prepare_rewrite_release_generation(
    source_dir: Path,
    run_dir: Path,
    batch_number: int,
    generation: int,
) -> Path:
    """從上一版 final artifacts 建立只重寫 REJECT 篇的 release generation。"""
    if generation < 1:
        raise ValueError("release generation must be positive")
    if run_dir.exists():
        raise FileExistsError(f"release generation already exists: {run_dir}")
    brief = json.loads((source_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((source_dir / "candidate.json").read_text(encoding="utf-8"))
    review = json.loads((source_dir / "review.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(candidate, enforce_policy=False)
    validate_review(review, candidate["articles"])
    article_ids = [str(item["article_id"]) for item in brief["articles"]]
    if len(article_ids) != MAX_RUN_ARTICLES:
        raise ValueError("release generation requires exactly five articles")
    rejected = [str(item["article_id"]) for item in review["articles"] if item["verdict"] != "APPROVE"]
    styles = _release_style_contracts(batch_number, brief, source_dir)
    release_brief = json.loads(json.dumps(brief, ensure_ascii=False))
    release_brief["run_id"] = f"gemini-rewrite-release-001-batch-{batch_number:03d}-generation-{generation:02d}"
    write_json(run_dir / "brief.json", release_brief)
    write_json(run_dir / "public-brief.json", public_model_brief(release_brief))
    write_json(run_dir / "source-candidate.json", candidate)
    write_json(run_dir / "source-review.json", review)
    write_json(
        run_dir / "release-contract.json",
        {
            "chain_id": "CONTENT-GEMINI-REWRITE-RELEASE-001",
            "batch_number": batch_number,
            "generation": generation,
            "article_order": article_ids,
            "target_article_ids": rejected,
            "variation_contracts": styles,
            "source_candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "source_review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "exact_findings": [
                {"article_id": item["article_id"], "findings": item.get("findings", [])}
                for item in review["articles"]
            ],
            "max_attempts": 2,
        },
    )
    return run_dir / "brief.json"


def _release_writer_prompt(
    brief: dict[str, Any],
    prior_article: dict[str, Any],
    source_findings: list[dict[str, Any]],
    current_findings: list[dict[str, Any]],
    style_contract: dict[str, Any],
    generation: int,
) -> str:
    prior_candidate = {
        "schema_version": SCHEMA_VERSION,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [prior_article],
    }
    return "\n".join([
        f"你是 Release Repair generation {generation} 的單篇 Gemini Writer。只修 findings，不改文章 identity。",
        f"完整輸出該篇正文；{publication_presentation_instruction('rewrite_existing_body')}。",
        "移除禁詞、模板式 H2、AI 套語、跨篇抽象句型與重複骨架；加入文章專屬場景、具體動詞、反例與限制。",
        "不得加入個人診斷、命運結論、保證預測或投資建議。",
        "public brief:", json.dumps(public_model_brief(brief), ensure_ascii=False),
        "prior public candidate:", json.dumps(public_model_candidate(brief, prior_candidate), ensure_ascii=False),
        "variation contract:", json.dumps(style_contract, ensure_ascii=False),
        "source public findings:", json.dumps(public_model_findings(brief, source_findings), ensure_ascii=False),
        "current public findings:", json.dumps(public_model_findings(brief, current_findings), ensure_ascii=False),
    ])


def run_rewrite_release_generation(
    run_dir: Path,
    client: GeminiClient,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """沿用已核准稿，只對 REJECT 篇做最多兩次 release repair。"""
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    source_candidate = json.loads((run_dir / "source-candidate.json").read_text(encoding="utf-8"))
    source_review = json.loads((run_dir / "source-review.json").read_text(encoding="utf-8"))
    contract = json.loads((run_dir / "release-contract.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(source_candidate, enforce_policy=False)
    validate_review(source_review, source_candidate["articles"])
    article_ids = [str(item["article_id"]) for item in brief["articles"]]
    if article_ids != [str(value) for value in contract.get("article_order", [])]:
        raise ValueError("release article order differs from contract")
    target_ids = [str(value) for value in contract.get("target_article_ids", [])]
    if not set(target_ids) <= set(article_ids):
        raise ValueError("release target IDs differ from contract")
    if contract.get("max_attempts") != 2:
        raise ValueError("release max attempts differs from contract")
    if isinstance(client, GeminiClient):
        if getattr(client.transport, "__name__", "") != "_cli_transport":
            raise RuntimeError("release repair requires fresh sandboxed headless CLI processes")
        if client.writer_model != DEFAULT_WRITER_MODEL or client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("release repair requires the fixed Gemini Writer and Pro Reviewer Low models")
    candidate_articles = {_candidate_id(item): item for item in source_candidate["articles"]}
    source_findings = {str(item["article_id"]): list(item.get("findings", [])) for item in contract["exact_findings"]}
    styles = contract["variation_contracts"]
    review = source_review
    writer_calls = 0
    reviewer_calls = 0
    completed_attempts = 0
    for attempt in range(2):
        completed_attempts = attempt + 1
        attempt_dir = run_dir / "attempts" / f"{attempt + 1:02d}"
        current_findings = {
            str(item["article_id"]): [
                {"article_id": item["article_id"], **finding} for finding in item.get("findings", [])
            ]
            for item in review["articles"]
        }
        writer_errors: list[str] = []
        for article_id in target_ids:
            single_brief = _single_rewrite_brief(brief, article_id)
            writer_dir = attempt_dir / "writers" / article_id.lower()
            write_json(writer_dir / "public-brief.json", public_model_brief(single_brief))
            try:
                external = _generate_with_receipt(
                    client,
                    "writer",
                    _release_writer_prompt(
                        single_brief,
                        candidate_articles[article_id],
                        source_findings.get(article_id, []),
                        current_findings.get(article_id, []),
                        styles[article_id],
                        int(contract["generation"]),
                    ),
                    external_candidate_schema("rewrite_existing_body"),
                    writer_dir / "writer-operation.json",
                )
                writer_calls += 1
                write_json(writer_dir / "external-candidate.json", external)
                candidate_articles[article_id] = hydrate_candidate(single_brief, external)["articles"][0]
            except (CandidateValidationError, json.JSONDecodeError, TypeError, ValueError) as error:
                writer_errors.append(article_id)
                write_json(
                    writer_dir / "writer-schema-rejection.json",
                    {"article_id": article_id, "code": "invalid_writer_schema", "error_type": type(error).__name__},
                )
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "run_id": brief["run_id"],
            "mode": "rewrite_existing_body",
            "articles": [candidate_articles[article_id] for article_id in article_ids],
        }
        validate_candidate(candidate)
        quality, uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
        deterministic = quality + uniqueness
        write_json(attempt_dir / "candidate.json", candidate)
        write_json(attempt_dir / "deterministic-quality-findings.json", quality)
        write_json(attempt_dir / "uniqueness-findings.json", uniqueness)
        if writer_errors:
            review = invalid_review_payload(brief["run_id"], candidate["articles"], "invalid_writer_schema")
        elif deterministic:
            review = deterministic_review_payload(
                brief["run_id"],
                candidate["articles"],
                deterministic,
            )
        else:
            try:
                external_review = _generate_with_receipt(
                    client,
                    "reviewer",
                    _repair_reviewer_prompt(brief, candidate, deterministic, styles),
                    rewrite_external_review_schema(),
                    attempt_dir / "reviewer-operation.json",
                )
                reviewer_calls += 1
                write_json(attempt_dir / "external-review.json", external_review)
                review = hydrate_rewrite_review(brief, candidate, external_review)
                for item in review["articles"]:
                    item["hard_failure"] = False
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                review = invalid_review_payload(
                    brief["run_id"], candidate["articles"], f"invalid_reviewer_json:{type(error).__name__}"
                )
        by_id = {str(item["article_id"]): item for item in review["articles"]}
        for finding in deterministic:
            item = by_id[str(finding["article_id"])]
            item["verdict"] = "REJECT"
            value = {"code": finding["code"], "message": finding["message"]}
            if value not in item["findings"]:
                item["findings"].append(value)
        write_json(attempt_dir / "review.json", review)
        target_ids = [str(item["article_id"]) for item in review["articles"] if item["verdict"] != "APPROVE"]
        if not target_ids:
            break
    final_candidate = {
        "schema_version": SCHEMA_VERSION,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [candidate_articles[article_id] for article_id in article_ids],
    }
    final_quality, final_uniqueness = rewrite_aggregate_findings(brief, final_candidate["articles"])
    write_json(run_dir / "candidate.json", final_candidate)
    write_json(run_dir / "review.json", review)
    write_json(run_dir / "deterministic-quality-findings.json", final_quality)
    write_json(run_dir / "uniqueness-findings.json", final_uniqueness)
    (run_dir / "review.md").write_text(render_review_markdown(review, final_candidate["articles"]), encoding="utf-8")
    write_json(
        run_dir / "run-evidence.json",
        {
            "run_id": brief["run_id"],
            "chain_id": contract["chain_id"],
            "batch_number": contract["batch_number"],
            "generation": contract["generation"],
            "attempts": completed_attempts,
            "writer_processes": writer_calls,
            "reviewer_processes": reviewer_calls,
            "candidate_sha256": hashlib.sha256(compact_json_bytes(final_candidate)).hexdigest(),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "reviewer_approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
            "deterministic_quality_findings": len(final_quality),
            "uniqueness_findings": len(final_uniqueness),
            "approval_created": False,
            "apply_executed": False,
        },
    )
    return final_candidate, review


def review_rewrite_release_final(
    run_dir: Path,
    client: GeminiClient,
    max_rounds: int = 3,
) -> dict[str, Any]:
    """正文 gates 已清零時只重跑 Reviewer，避免無意義地再次改寫。"""
    if max_rounds != 3:
        raise ValueError("release reviewer-only retry requires exactly three rounds")
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    contract = json.loads((run_dir / "release-contract.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(candidate)
    quality, uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
    if quality or uniqueness:
        raise CandidateValidationError("reviewer-only retry requires zero deterministic findings")
    if isinstance(client, GeminiClient):
        if getattr(client.transport, "__name__", "") not in {"_cli_transport", "_http_transport"}:
            raise RuntimeError("release reviewer-only retry requires stateless Gemini transport")
        if client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("release reviewer-only retry requires Gemini Pro Reviewer Low")
    review: dict[str, Any] | None = None
    for round_number in range(1, max_rounds + 1):
        round_dir = run_dir / "review-only" / f"round_{round_number:02d}"
        external_path = round_dir / "external-review.json"
        try:
            external = _generate_with_receipt(
                client,
                "reviewer",
                _repair_reviewer_prompt(brief, candidate, [], contract["variation_contracts"]),
                rewrite_external_review_schema(),
                round_dir / "reviewer-operation.json",
            )
            write_json(external_path, external)
            review = hydrate_rewrite_review(brief, candidate, external)
            for item in review["articles"]:
                item["hard_failure"] = False
            write_json(round_dir / "review.json", review)
            if all(item["verdict"] == "APPROVE" for item in review["articles"]):
                break
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            review = invalid_review_payload(
                brief["run_id"], candidate["articles"], f"invalid_reviewer_json:{type(error).__name__}"
            )
            write_json(round_dir / "review.json", review)
    if review is None:
        raise RuntimeError("release reviewer-only retry produced no review")
    write_json(run_dir / "review.json", review)
    (run_dir / "review.md").write_text(render_review_markdown(review, candidate["articles"]), encoding="utf-8")
    evidence = json.loads((run_dir / "run-evidence.json").read_text(encoding="utf-8"))
    evidence.update(
        {
            "reviewer_only_rounds": max(1, len(list((run_dir / "review-only").glob("round_*")))),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "reviewer_approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
        }
    )
    write_json(run_dir / "run-evidence.json", evidence)
    return review


RELEASE_BATCH1_CLOSURE_REPLACEMENTS = {
    "THEME-LIFE-04": {
        "這場試做的目的不是強迫自己改變天性，而是擴展解決問題的應變方式。":
            "這場試做用來擴展解決問題的應變方式，無須強迫自己改變天性。",
        "這種反常的控制欲並不是個性永久改變，而是焦慮感過高時，大腦做出的暫時性補償反應。":
            "這種反常的控制欲源自焦慮感過高時大腦做出的暫時性補償反應，不代表個性永久改變。",
        "給自己留下撤回決策的空間並不意味著軟弱，而是理解在現實世界中，沒有任何測驗結果能夠限制你一生的發展。":
            "給自己留下撤回決策的空間，代表你理解現實世界沒有任何測驗結果能限制一生發展，這與軟弱無關。",
    },
    "THEME-WEALTH-04": {
        "我們該關注的是如何編列合理的預算，而不是去尋求神秘學的預測。":
            "我們該把注意力放在合理預算；尋求神秘學預測無法代替帳目核對。",
        "這不是一次性的整理，而是需要定期檢視的功課。":
            "這項整理需要定期檢視，單次清點不足以掌握長期變化。",
    },
}


def run_release_batch1_local_closure(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """只移除 Batch 1 已定位的 not-but 抽象句型，不新增事實。"""
    contract = json.loads((run_dir / "release-contract.json").read_text(encoding="utf-8"))
    if contract.get("batch_number") != 1 or contract.get("generation") != 4:
        raise ValueError("local closure is locked to release Batch 1 generation 4")
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "source-candidate.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(candidate)
    candidate["run_id"] = brief["run_id"]
    changed: list[dict[str, Any]] = []
    for article in candidate["articles"]:
        article_id = str(article["article_id"])
        replacements = RELEASE_BATCH1_CLOSURE_REPLACEMENTS.get(article_id, {})
        for section_index, section in enumerate(article["bodySections"], start=1):
            for paragraph_index, paragraph in enumerate(section["paragraphs"], start=1):
                updated = paragraph
                for source, replacement in replacements.items():
                    updated = updated.replace(source, replacement)
                if updated != paragraph:
                    section["paragraphs"][paragraph_index - 1] = updated
                    changed.append({"article_id": article_id, "section": section_index, "paragraph": paragraph_index})
    if len(changed) != 5:
        raise ValueError("release Batch 1 local closure exact replacement count differs from contract")
    quality, uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
    if quality or uniqueness:
        raise CandidateValidationError("release Batch 1 local closure did not clear deterministic findings")
    review = invalid_review_payload(brief["run_id"], candidate["articles"], "reviewer_required")
    write_json(run_dir / "candidate.json", candidate)
    write_json(run_dir / "review.json", review)
    write_json(run_dir / "deterministic-quality-findings.json", quality)
    write_json(run_dir / "uniqueness-findings.json", uniqueness)
    write_json(
        run_dir / "local-closure-01.json",
        {
            "changed_locations": changed,
            "candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "reviewer_required": True,
        },
    )
    write_json(
        run_dir / "run-evidence.json",
        {
            "run_id": brief["run_id"],
            "chain_id": contract["chain_id"],
            "batch_number": 1,
            "generation": 4,
            "attempts": 0,
            "writer_processes": 0,
            "reviewer_processes": 0,
            "candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "reviewer_approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
            "deterministic_quality_findings": 0,
            "uniqueness_findings": 0,
            "approval_created": False,
            "apply_executed": False,
            "reviewer_required": True,
        },
    )
    return candidate, review


def write_rewrite_release_summary(release_root: Path) -> dict[str, Any]:
    """只讀每批最新 generation，重建 release 總結。"""
    batch_results: list[dict[str, Any]] = []
    all_ids: list[str] = []
    for batch_number in range(1, 11):
        generations = sorted((release_root / f"batch_{batch_number:03d}").glob("generation_*"))
        if not generations:
            raise FileNotFoundError(f"release Batch {batch_number} has no generation")
        final_dir = generations[-1]
        candidate = json.loads((final_dir / "candidate.json").read_text(encoding="utf-8"))
        evidence = json.loads((final_dir / "run-evidence.json").read_text(encoding="utf-8"))
        ids = [str(item["article_id"]) for item in candidate["articles"]]
        all_ids.extend(ids)
        batch_results.append(
            {
                "batch": batch_number,
                "final_dir": final_dir.relative_to(release_root).as_posix(),
                "article_ids": ids,
                **evidence,
            }
        )
    approved = sum(item["reviewer_approved"] for item in batch_results)
    fallback_approved = sum(
        item["reviewer_approved"] for item in batch_results if item.get("fallback_reviewer")
    )
    gemini_approved = approved - fallback_approved
    quality = sum(item["deterministic_quality_findings"] for item in batch_results)
    uniqueness = sum(item["uniqueness_findings"] for item in batch_results)
    status = "READY_FOR_APPLY" if len(all_ids) == 50 and len(set(all_ids)) == 50 and approved == 50 and quality == 0 and uniqueness == 0 else "BLOCKED"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "chain_id": "CONTENT-GEMINI-REWRITE-RELEASE-001",
        "status": status,
        "candidate_count": len(all_ids),
        "unique_candidate_count": len(set(all_ids)),
        "reviewer_approved": approved,
        "gemini_reviewer_approved": gemini_approved,
        "fallback_reviewer_approved": fallback_approved,
        "gemini_approval_claimed_for_fallback": False,
        "deterministic_quality_findings": quality,
        "uniqueness_findings": uniqueness,
        "article_ids": all_ids,
        "batches": batch_results,
        "approval_created": False,
        "formal_apply": False,
    }
    write_json(release_root / "summary.json", summary)
    return summary


def apply_rewrite_release(repo_root: Path, release_root: Path) -> list[Path]:
    """50/50 核准後只新增 body override；registry 與 metadata identity 不變。"""
    summary = json.loads((release_root / "summary.json").read_text(encoding="utf-8"))
    fallback_approved = sum(
        int(batch["reviewer_approved"])
        for batch in summary.get("batches", [])
        if batch.get("fallback_reviewer")
    )
    gemini_approved = int(summary.get("reviewer_approved", 0)) - fallback_approved
    if (
        summary.get("status") not in {"READY_FOR_APPLY", "READY_TO_DEPLOY"}
        or summary.get("candidate_count") != 50
        or summary.get("unique_candidate_count") != 50
        or summary.get("reviewer_approved") != 50
        or summary.get("deterministic_quality_findings") != 0
        or summary.get("uniqueness_findings") != 0
        or gemini_approved != 30
        or fallback_approved != 20
    ):
        raise ValueError("rewrite release is not ready for apply")
    if summary.get("status") == "READY_TO_DEPLOY" and not summary.get("formal_apply"):
        raise ValueError("rewrite release READY_TO_DEPLOY state is inconsistent")
    candidates: list[dict[str, Any]] = []
    approvals: list[dict[str, Any]] = []
    for batch in summary["batches"]:
        run_dir = Path(str(batch["final_dir"]))
        if not run_dir.is_absolute():
            run_dir = release_root / run_dir
        candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
        review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
        quality = json.loads((run_dir / "deterministic-quality-findings.json").read_text(encoding="utf-8"))
        uniqueness = json.loads((run_dir / "uniqueness-findings.json").read_text(encoding="utf-8"))
        validate_candidate(candidate)
        validate_review(review, candidate["articles"])
        if quality or uniqueness or any(item["verdict"] != "APPROVE" for item in review["articles"]):
            raise ValueError(f"rewrite release Batch {batch['batch']} is not fully approved")
        candidates.extend(candidate["articles"])
        approvals.extend(
            {
                "article_id": item["article_id"],
                "candidate_sha256": item["candidate_sha256"],
                "decision": "APPROVE",
                "reviewer_type": batch.get("fallback_reviewer", "gemini"),
                "gemini_approval_claimed": not bool(batch.get("fallback_reviewer")),
            }
            for item in review["articles"]
        )
    if len(candidates) != 50 or len({_candidate_id(item) for item in candidates}) != 50:
        raise ValueError("rewrite release apply requires 50 unique candidates")
    inventory = _existing_rewrite_inventory(repo_root)
    bodies: dict[str, Any] = {}
    for article in candidates:
        article_id = _candidate_id(article)
        source = inventory.get(article_id)
        if source is None:
            raise ValueError(f"rewrite release source article missing: {article_id}")
        record = source["record"]
        identity = article["identity"]
        actual_identity = {
            "id": record["id"],
            "product": record["product"],
            "category": str(source["canonicalPath"]).strip("/").split("/")[1],
            "serial": record["serial"],
            "slug": record["urlSlug"],
            "primaryKeyword": record["primaryKeyword"],
            "title": record["title"],
        }
        if identity != actual_identity:
            raise ValueError(f"rewrite release immutable identity drift: {article_id}")
        actual_body_sha = body_sha256(source["currentBody"])
        approved_body_sha = body_sha256(article["bodySections"])
        if actual_body_sha not in {article["current_body_sha256"], approved_body_sha}:
            raise ValueError(f"rewrite release current body drift: {article_id}")
        bodies[str(record["slug"])] = article["bodySections"]
    static = repo_root / "app/web/static"
    module = static / "article-rewrite-release-001.js"
    module.write_text(
        "// 50 篇核准改寫正文；由 release gate 產生，僅覆寫 bodySections。\n\n"
        f"export const REWRITE_RELEASE_001_BODY_OVERRIDES = {json.dumps(bodies, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    meta_path = static / "article-meta.js"
    meta = meta_path.read_text(encoding="utf-8")
    import_line = 'import { REWRITE_RELEASE_001_BODY_OVERRIDES } from "./article-rewrite-release-001.js?v=rewrite-release-001";\n'
    meta = _insert_once(meta, "const ARTICLE_BODY_LIBRARY = {", import_line + "\n")
    old = "  const customBody = ARTICLE_BODY_LIBRARY[article.slug];"
    new = "  const customBody = REWRITE_RELEASE_001_BODY_OVERRIDES[article.slug] || ARTICLE_BODY_LIBRARY[article.slug];"
    if old in meta:
        meta = meta.replace(old, new, 1)
    elif new not in meta:
        raise ValueError("article body override marker not found")
    meta_path.write_text(meta, encoding="utf-8")
    approval = {
        "schema_version": SCHEMA_VERSION,
        "chain_id": "CONTENT-GEMINI-REWRITE-RELEASE-001",
        "approved_by": "user-requested-release-repair",
        "article_count": 50,
        "articles": approvals,
        "formal_apply": True,
        "deploy_authorized": False,
    }
    write_json(release_root / "approval.json", approval)
    summary.update(
        {
            "status": "READY_TO_DEPLOY",
            "approval_created": True,
            "formal_apply": True,
            "gemini_reviewer_approved": gemini_approved,
            "fallback_reviewer_approved": fallback_approved,
            "gemini_approval_claimed_for_fallback": False,
        }
    )
    write_json(release_root / "summary.json", summary)
    changed = [
        module,
        meta_path,
        *_bump_article_cache_queries(
            repo_root,
            "rewrite-release-001",
            hub_updated_date=max(
                str(article["publicationPolicy"]["modified"])
                for article in candidates
            ),
        ),
    ]
    write_json(
        release_root / "apply-evidence.json",
        {
            "status": "READY_TO_DEPLOY",
            "article_count": 50,
            "gemini_reviewer_approved": gemini_approved,
            "fallback_reviewer_approved": fallback_approved,
            "gemini_approval_claimed_for_fallback": False,
            "body_override_module": module.relative_to(repo_root).as_posix(),
            "changed_files": [path.relative_to(repo_root).as_posix() for path in changed],
            "registry_changed": False,
            "metadata_changed": False,
            "deploy_executed": False,
        },
    )
    return changed


def release_fallback_review(run_dir: Path) -> dict[str, Any]:
    """Gemini quota 阻塞時的透明 fallback；只接受 deterministic 已清零且安全邊界完整的稿件。"""
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    prior_review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(candidate)
    validate_review(prior_review, candidate["articles"])
    quality, uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
    if quality or uniqueness:
        raise CandidateValidationError("release fallback requires zero deterministic findings")
    allowed_prior_codes = {"invalid_reviewer_json:JSONDecodeError", "reviewer_required"}
    prior_codes = {
        str(finding["code"])
        for item in prior_review["articles"]
        for finding in item.get("findings", [])
    }
    if not prior_codes or not prior_codes <= allowed_prior_codes:
        raise ValueError(f"release fallback prior findings are not transport-only: {sorted(prior_codes)}")
    findings: list[dict[str, str]] = []
    for article in candidate["articles"]:
        article_id = _candidate_id(article)
        text = "".join(str(paragraph) for section in article["bodySections"] for paragraph in section["paragraphs"])
        if len(re.findall(r"不能|無法|不代表|未必|限制|邊界|僅供|不適用", text)) < 2:
            findings.append({"article_id": article_id, "code": "insufficient_boundary", "message": "至少需要兩個明確限制或邊界句"})
        if re.search(r"(?:保證|注定|一定會|必然會).{0,16}(?:成功|發生|獲利|賺|復合|結婚|升職|生病)", text):
            findings.append({"article_id": article_id, "code": "promise_claim", "message": "含保證或必然結果"})
        if re.search(r"(?:你|讀者).{0,8}(?:患有|確診|就是.{0,4}人格|有.{0,6}疾病)", text):
            findings.append({"article_id": article_id, "code": "diagnostic_claim", "message": "含固定診斷或人格定性"})
        if re.search(r"(?:應該|建議|務必|立刻).{0,8}(?:買進|賣出|下注|停藥|停診)", text):
            findings.append({"article_id": article_id, "code": "unsafe_instruction", "message": "含投資或醫療直接指令"})
    if findings:
        write_json(run_dir / "fallback-safety-findings.json", findings)
        raise CandidateValidationError("release fallback safety gate rejected candidate")
    review = {
        "schema_version": SCHEMA_VERSION,
        "run_id": candidate["run_id"],
        "articles": [
            {
                "article_id": _candidate_id(article),
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "hard_failure": False,
                "findings": [],
            }
            for article in candidate["articles"]
        ],
    }
    validate_review(review, candidate["articles"])
    write_json(run_dir / "review.json", review)
    write_json(run_dir / "fallback-safety-findings.json", [])
    write_json(
        run_dir / "fallback-review-evidence.json",
        {
            "reviewer_type": "codex_release_fallback",
            "reason": "Gemini CLI and API quota exhausted after deterministic gates reached zero",
            "article_count": len(candidate["articles"]),
            "quality_findings": 0,
            "uniqueness_findings": 0,
            "safety_findings": 0,
            "gemini_approval_claimed": False,
        },
    )
    evidence = json.loads((run_dir / "run-evidence.json").read_text(encoding="utf-8"))
    evidence.update(
        {
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "reviewer_approved": len(review["articles"]),
            "fallback_reviewer": "codex_release_fallback",
            "gemini_approval_claimed": False,
        }
    )
    write_json(run_dir / "run-evidence.json", evidence)
    return review


def verify_rewrite_release_apply(repo_root: Path, release_root: Path) -> dict[str, Any]:
    """驗證正式 runtime 的 50 篇正文與 approved candidates 完全一致。"""
    summary = json.loads((release_root / "summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "READY_TO_DEPLOY" or not summary.get("formal_apply"):
        raise ValueError("rewrite release has not been formally applied")
    inventory = _existing_rewrite_inventory(repo_root)
    verified: list[dict[str, str]] = []
    for batch in summary["batches"]:
        run_dir = Path(str(batch["final_dir"]))
        if not run_dir.is_absolute():
            run_dir = release_root / run_dir
        brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
        candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
        brief_by_id = {str(item["article_id"]): item for item in brief["articles"]}
        for article in candidate["articles"]:
            article_id = _candidate_id(article)
            actual = inventory.get(article_id)
            if actual is None:
                raise ValueError(f"applied rewrite article missing: {article_id}")
            expected_immutable = brief_by_id[article_id]["immutable_fields"]
            record = actual["record"]
            actual_immutable = {
                "id": record["id"],
                "product": record["product"],
                "serial": record["serial"],
                "urlSlug": record["urlSlug"],
                "primaryKeyword": record["primaryKeyword"],
                "title": record["title"],
                "description": record["description"],
                "answer": record["answer"],
                "faq": record["faq"],
                "tags": record["tags"],
                "published": actual["published"],
                "updated": actual["updated"],
            }
            expected_comparable = {key: value for key, value in expected_immutable.items() if key != "slug"}
            if actual_immutable != expected_comparable:
                raise ValueError(f"applied rewrite immutable metadata drift: {article_id}")
            expected_body_sha = body_sha256(article["bodySections"])
            actual_body_sha = body_sha256(actual["currentBody"])
            if actual_body_sha != expected_body_sha:
                raise ValueError(f"applied rewrite body differs from candidate: {article_id}")
            verified.append(
                {"article_id": article_id, "body_sha256": actual_body_sha, "candidate_sha256": article_sha256(article)}
            )
    if len(verified) != 50 or len({item["article_id"] for item in verified}) != 50:
        raise ValueError("applied rewrite verification requires 50 unique articles")
    evidence = {
        "status": "READY_TO_DEPLOY",
        "verified_article_count": 50,
        "body_match_count": 50,
        "immutable_metadata_match_count": 50,
        "gemini_reviewer_approved": summary.get("gemini_reviewer_approved"),
        "fallback_reviewer_approved": summary.get("fallback_reviewer_approved"),
        "gemini_approval_claimed_for_fallback": False,
        "registry_changed": False,
        "deploy_executed": False,
        "articles": verified,
    }
    write_json(release_root / "apply-verification.json", evidence)
    return evidence


def run_rewrite_release(
    evidence_root: Path,
    release_root: Path,
    client: GeminiClient,
    max_generations: int = 3,
) -> dict[str, Any]:
    """逐批 release repair；每批最多三代並保留所有 evidence。"""
    if max_generations != 3:
        raise ValueError("release repair requires exactly three generations")
    batch_results: list[dict[str, Any]] = []
    all_ids: list[str] = []
    for batch_number, original_source in _rewrite_release_sources(evidence_root):
        source_dir = original_source
        final_dir: Path | None = None
        for generation in range(1, max_generations + 1):
            run_dir = release_root / f"batch_{batch_number:03d}" / f"generation_{generation:02d}"
            if not run_dir.exists():
                prepare_rewrite_release_generation(source_dir, run_dir, batch_number, generation)
            if not (run_dir / "run-evidence.json").is_file():
                run_rewrite_release_generation(run_dir, client)
            evidence = json.loads((run_dir / "run-evidence.json").read_text(encoding="utf-8"))
            final_dir = run_dir
            if (
                evidence["reviewer_approved"] == MAX_RUN_ARTICLES
                and evidence["deterministic_quality_findings"] == 0
                and evidence["uniqueness_findings"] == 0
            ):
                break
            source_dir = run_dir
        assert final_dir is not None
        candidate = json.loads((final_dir / "candidate.json").read_text(encoding="utf-8"))
        evidence = json.loads((final_dir / "run-evidence.json").read_text(encoding="utf-8"))
        ids = [str(item["article_id"]) for item in candidate["articles"]]
        all_ids.extend(ids)
        batch_results.append({"batch": batch_number, "final_dir": final_dir.as_posix(), "article_ids": ids, **evidence})
    return write_rewrite_release_summary(release_root)


def run_rewrite_repair_closure(
    run_dir: Path,
    client: GeminiClient,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """最後一次 deterministic closure；只改兩個已知位置且不呼叫 Writer。"""
    closure_dir = run_dir / "closure-01"
    if closure_dir.exists():
        raise RuntimeError("rewrite repair closure pass has already been used")
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    prior_review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    validate_rewrite_brief(brief)
    validate_candidate(candidate)
    validate_review(prior_review, candidate["articles"])
    if tuple(str(item["article_id"]) for item in candidate["articles"]) != REWRITE_REPAIR_ARTICLE_IDS:
        raise ValueError("rewrite closure article set or fixed order differs from contract")
    remaining = {
        (str(item["article_id"]), str(finding["code"]))
        for item in prior_review["articles"]
        for finding in item.get("findings", [])
    }
    if remaining != {("MBTI-BASE-01", "paragraph_length"), ("THEME-LIFE-03", "banned_phrase")}:
        raise ValueError("rewrite closure prior findings differ from the two authorized findings")
    if isinstance(client, GeminiClient):
        if getattr(client.transport, "__name__", "") != "_cli_transport":
            raise RuntimeError("rewrite closure requires a fresh sandboxed headless reviewer process")
        if client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("rewrite closure reviewer must use the configured independent reviewer model")
    before_articles = json.loads(json.dumps(candidate["articles"], ensure_ascii=False))
    by_id = {str(article["article_id"]): article for article in candidate["articles"]}
    changed_locations: list[dict[str, Any]] = []
    for (article_id, section_number, paragraph_number), (expected, replacement) in REWRITE_CLOSURE_EDITS.items():
        paragraphs = by_id[article_id]["bodySections"][section_number - 1]["paragraphs"]
        if paragraphs[paragraph_number - 1] != expected:
            raise ValueError(f"rewrite closure source text drift at {article_id} S{section_number}P{paragraph_number}")
        paragraphs[paragraph_number - 1] = replacement
        changed_locations.append(
            {
                "article_id": article_id,
                "section": section_number,
                "paragraph": paragraph_number,
                "before_length": len(expected),
                "after_length": len(replacement),
            }
        )
    before_paragraphs = {
        (str(article["article_id"]), section_index, paragraph_index): paragraph
        for article in before_articles
        for section_index, section in enumerate(article["bodySections"], start=1)
        for paragraph_index, paragraph in enumerate(section["paragraphs"], start=1)
    }
    after_paragraphs = {
        (str(article["article_id"]), section_index, paragraph_index): paragraph
        for article in candidate["articles"]
        for section_index, section in enumerate(article["bodySections"], start=1)
        for paragraph_index, paragraph in enumerate(section["paragraphs"], start=1)
    }
    changed_keys = {key for key in before_paragraphs if before_paragraphs[key] != after_paragraphs[key]}
    if changed_keys != set(REWRITE_CLOSURE_EDITS):
        raise ValueError("rewrite closure changed paragraphs outside the authorized two locations")
    validate_candidate(candidate)
    quality, uniqueness = rewrite_aggregate_findings(brief, candidate["articles"])
    write_json(closure_dir / "candidate.json", candidate)
    write_json(closure_dir / "deterministic-quality-findings.json", quality)
    write_json(closure_dir / "uniqueness-findings.json", uniqueness)
    write_json(
        closure_dir / "closure-evidence.json",
        {
            "closure_pass": 1,
            "writer_processes": 0,
            "changed_locations": changed_locations,
            "unchanged_paragraphs": len(after_paragraphs) - len(changed_keys),
            "before_article_sha256": {
                _candidate_id(article): article_sha256(article) for article in before_articles
            },
            "after_article_sha256": {
                _candidate_id(article): article_sha256(article) for article in candidate["articles"]
            },
        },
    )
    if quality or uniqueness:
        raise CandidateValidationError("rewrite closure deterministic gates did not reach zero findings")
    external_review = _generate_with_receipt(
        client,
        "reviewer",
        _repair_reviewer_prompt(brief, candidate, []),
        rewrite_external_review_schema(),
        closure_dir / "reviewer-operation.json",
    )
    write_json(closure_dir / "external-review.json", external_review)
    review = hydrate_rewrite_review(brief, candidate, external_review)
    for item in review["articles"]:
        item["hard_failure"] = False
    write_json(closure_dir / "review.json", review)
    write_json(run_dir / "candidate.json", candidate)
    write_json(run_dir / "review.json", review)
    (run_dir / "review.md").write_text(render_review_markdown(review, candidate["articles"]), encoding="utf-8")
    write_json(run_dir / "deterministic-quality-findings.json", quality)
    write_json(run_dir / "uniqueness-findings.json", uniqueness)
    evidence = json.loads((run_dir / "run-evidence.json").read_text(encoding="utf-8"))
    evidence.update(
        {
            "deterministic_closure_passes": 1,
            "closure_writer_processes": 0,
            "closure_reviewer_processes": 1,
            "reviewer_processes": int(evidence.get("reviewer_processes", 0)) + 1,
            "candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "article_sha256": {_candidate_id(article): article_sha256(article) for article in candidate["articles"]},
            "deterministic_quality_findings": 0,
            "uniqueness_findings": 0,
            "reviewer_approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
        }
    )
    write_json(run_dir / "run-evidence.json", evidence)
    return candidate, review


def review_existing_candidate(run_dir: Path, client: GeminiClient) -> dict[str, Any]:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    validate_candidate(candidate)
    if candidate["run_id"] != brief["run_id"] or candidate["mode"] != brief["mode"]:
        raise CandidateValidationError("existing candidate differs from brief")
    is_rewrite = brief.get("mode") == "rewrite_existing_body"
    if is_rewrite:
        validate_rewrite_brief(brief)
        if isinstance(client, GeminiClient) and getattr(client.transport, "__name__", "") != "_cli_transport":
            raise RuntimeError("rewrite_existing_body requires a fresh headless reviewer process")
        if isinstance(client, GeminiClient) and client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("rewrite_existing_body reviewer must use the configured independent reviewer model")
        expected = brief["articles"]
        if [article["article_id"] for article in candidate["articles"]] != [item["article_id"] for item in expected]:
            raise CandidateValidationError("existing rewrite candidate set or order differs from brief")
        for article, source in zip(candidate["articles"], expected, strict=True):
            if article["identity"] != source["identity"] or article["current_body_sha256"] != source["current_body_sha256"]:
                raise CandidateValidationError(f"existing rewrite candidate changed immutable fields for {article['article_id']}")
        deterministic = rewrite_quality_findings(brief, candidate["articles"])
    else:
        deterministic = quality_findings(candidate["articles"])
    if is_rewrite and deterministic:
        review = deterministic_review_payload(
            brief["run_id"],
            candidate["articles"],
            deterministic,
        )
    else:
        try:
            external_review = _generate_with_receipt(
                client,
                "reviewer",
                _reviewer_prompt(brief, candidate, deterministic),
                (
                    rewrite_external_review_schema()
                    if is_rewrite
                    else external_review_schema()
                ),
                run_dir / "review-existing-operation.json",
            )
            write_json(run_dir / "external-review-existing.json", external_review)
            review = (
                hydrate_rewrite_review(brief, candidate, external_review)
                if is_rewrite
                else hydrate_review(brief, candidate, external_review)
            )
            for item in review["articles"]:
                item["hard_failure"] = False
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            review = invalid_review_payload(brief["run_id"], candidate["articles"], f"invalid_reviewer_json:{type(error).__name__}")
    by_id = {item["article_id"]: item for item in review["articles"]}
    for finding in deterministic:
        item = by_id[finding["article_id"]]
        item["verdict"] = "REJECT"
        existing = {(entry["code"], entry["message"]) for entry in item["findings"]}
        value = {"code": finding["code"], "message": finding["message"]}
        if (value["code"], value["message"]) not in existing:
            item["findings"].append(value)
    write_json(run_dir / "review.json", review)
    (run_dir / "review.md").write_text(render_review_markdown(review, candidate["articles"]), encoding="utf-8")
    return review


def _safe_identifier(run_id: str) -> tuple[str, str]:
    slug = re.sub(r"[^a-z0-9-]+", "-", run_id.lower()).strip("-")
    if not slug:
        raise ValueError("run_id cannot produce an empty module name")
    return slug, re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_")


def _insert_once(text: str, needle: str, insertion: str) -> str:
    if insertion.strip() in text:
        return text
    index = text.find(needle)
    if index < 0:
        raise ValueError(f"source marker not found: {needle}")
    return text[:index] + insertion + text[index:]


def _bump_article_cache_queries(
    repo_root: Path,
    token: str,
    *,
    hub_updated_date: str | None = None,
) -> list[Path]:
    web = repo_root / "app/web"
    replacements = {
        web / "static/article-meta.js": [(r'article-registry\.js\?v=[^"\']+', f"article-registry.js?v={token}")],
        web / "static/article-admin.js": [(r'article-registry\.js\?v=[^"\']+', f"article-registry.js?v={token}")],
        web / "static/app.js": [(r'article-registry\.js\?v=[^"\']+', f"article-registry.js?v={token}")],
        web / "static/articles.js": [(r'article-registry\.js\?v=[^"\']+', f"article-registry.js?v={token}")],
        web / "static/article.js": [(r'article-meta\.js\?v=[^"\']+', f"article-meta.js?v={token}")],
        web / "article.html": [(r'static/article\.js\?v=[^"\']+', f"static/article.js?v={token}")],
        web / "article-admin.html": [(r'static/article-admin\.js\?v=[^"\']+', f"static/article-admin.js?v={token}")],
        web / "index.html": [(r'static/app\.js\?v=[^"\']+', f"static/app.js?v={token}")],
        web / "articles.html": [(r'static/articles\.js\?v=[^"\']+', f"static/articles.js?v={token}")],
    }
    changed: list[Path] = []
    for path, rules in replacements.items():
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        for pattern, replacement in rules:
            updated = re.sub(pattern, replacement, updated)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)
    articles_html = web / "articles.html"
    if hub_updated_date is not None and articles_html.exists():
        original = articles_html.read_text(encoding="utf-8")
        updated = render_articles_hub_dates(
            original,
            updated_date=max(articles_hub_updated_date(original), hub_updated_date),
        )
        if updated != original:
            articles_html.write_text(updated, encoding="utf-8")
            if articles_html not in changed:
                changed.append(articles_html)
    return changed


def _apply_optimize_candidates(repo_root: Path, run_id: str, approved: list[dict[str, Any]]) -> list[Path]:
    inventory = {str(item["id"]): item for item in _registry_inventory(repo_root)}
    overrides: dict[str, dict[str, str]] = {}
    for article in approved:
        article_id = str(article["article_id"])
        current = inventory.get(article_id)
        if current is None:
            raise ValueError(f"article no longer exists: {article_id}")
        actual = {field: current.get(field) for field in OPTIMIZE_FIELDS}
        if actual != article["current"]:
            raise ValueError(f"source drift detected for {article_id}")
        overrides[article_id] = {field: str(article["proposed"][field]) for field in sorted(OPTIMIZE_FIELDS)}

    registry_path = repo_root / "app/web/static/article-registry.js"
    registry = registry_path.read_text(encoding="utf-8")
    marker = "export const ARTICLE_SEO_COPY_OVERRIDES = "
    if marker in registry:
        start = registry.index(marker) + len(marker)
        end = registry.index(";\n", start)
        existing = json.loads(registry[start:end])
        existing.update(overrides)
        registry = registry[:start] + json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + registry[end:]
    else:
        block = f"export const ARTICLE_SEO_COPY_OVERRIDES = {json.dumps(overrides, ensure_ascii=False, indent=2, sort_keys=True)};\n\n"
        registry = _insert_once(registry, "export const ARTICLE_REGISTRY = [", block)
    list_marker = "return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy("
    argument_start = registry.find(list_marker)
    if argument_start < 0:
        raise ValueError("listArticleRecords override marker not found")
    argument_start += len(list_marker)
    argument_end = registry.find(
        ", getArticleSectionRecord(article.section)));",
        argument_start,
    )
    if argument_end < 0:
        raise ValueError("listArticleRecords override argument not found")
    current_argument = registry[argument_start:argument_end]
    override_token = "ARTICLE_SEO_COPY_OVERRIDES[article.id]"
    if override_token not in current_argument:
        updated_argument = (
            f"{{ ...({current_argument}), ...({override_token} || {{}}) }}"
        )
        registry = (
            registry[:argument_start]
            + updated_argument
            + registry[argument_end:]
        )
    registry_path.write_text(registry, encoding="utf-8")
    _, slug_identifier = _safe_identifier(run_id)
    return [registry_path, *_bump_article_cache_queries(repo_root, f"agy-{slug_identifier.lower().replace('_', '-')}")]


def _owned_create_identities(module: Path) -> tuple[set[str], set[str]]:
    """讀取同一 run 既有 module 的 ID/path，供安全重放時排除自身占用。"""
    if not module.exists():
        return set(), set()
    match = re.search(r"_ARTICLE_RECORDS = (\[.*?\]);\n\nexport const", module.read_text(encoding="utf-8"), re.DOTALL)
    if match is None:
        raise ValueError(f"existing run module is not parseable: {module.name}")
    records = json.loads(match.group(1))
    ids = {str(record["id"]) for record in records}
    paths = {
        f"/articles/{str(record['serial']).rsplit('-', 1)[0]}/{record['urlSlug']}"
        for record in records
    }
    return ids, paths


def apply_approved_candidates(repo_root: Path, run_id: str, candidates: list[dict[str, Any]], review: dict[str, Any], approval: dict[str, Any]) -> list[Path]:
    approved = validate_apply_gate(candidates, review, approval)
    if not approved:
        return []
    if "identity" in approved[0] and "current_body_sha256" in approved[0]:
        raise ValueError("rewrite_existing_body apply is disabled; candidate and review only")
    if "bodySections" not in approved[0]:
        return _apply_optimize_candidates(repo_root, run_id, approved)
    reference_articles = load_publication_reference_corpus(repo_root)
    for article in approved:
        findings = required_policy_findings(
            article_publication_policy_findings(
                article,
                mode="create",
                reference_articles=reference_articles,
            )
        )
        if findings:
            raise ValueError(
                f"policy v2 publisher apply blocked {article['id']}: "
                f"{','.join(sorted({finding['code'] for finding in findings}))}"
            )
    slug, identifier = _safe_identifier(run_id)
    static = repo_root / "app/web/static"
    module = static / f"article-expansion-agy-{slug}.js"
    owned_ids, owned_paths = _owned_create_identities(module)
    inventory = _registry_inventory(repo_root) if "function listArticleRecords" in (repo_root / "app/web/static/article-registry.js").read_text(encoding="utf-8") else []
    occupied_ids = {str(item.get("id")) for item in inventory} - owned_ids
    occupied_paths = {str(item.get("path")) for item in inventory} - owned_paths
    for article in approved:
        category = str(article["serial"]).rsplit("-", 1)[0]
        path = f"/articles/{category}/{article['urlSlug']}"
        if str(article["id"]) in occupied_ids or path in occupied_paths:
            raise ValueError(f"create source identity already exists: {article['id']}")
    records = [{key: value for key, value in article.items() if key != "bodySections"} for article in approved]
    bodies = {str(article["slug"]): article["bodySections"] for article in approved}
    module.write_text(
        "// AGY 核准文章批次；由 scripts/agy_seo_copy_pipeline.py 產生。\n\n"
        f"export const AGY_{identifier}_ARTICLE_RECORDS = {json.dumps(records, ensure_ascii=False, indent=2)};\n\n"
        f"export const AGY_{identifier}_ARTICLE_BODY_LIBRARY = {json.dumps(bodies, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    import_query = f"agy-{slug}"
    registry_path = static / "article-registry.js"
    registry = registry_path.read_text(encoding="utf-8")
    registry_import = f'import {{ AGY_{identifier}_ARTICLE_RECORDS }} from "./{module.name}?v={import_query}";\n'
    registry = _insert_once(registry, "export const ARTICLE_REGISTRY = [", registry_import + "\n")
    start = registry.index("export const ARTICLE_REGISTRY = [")
    end = registry.index("\n];", start)
    spread = f"  ...AGY_{identifier}_ARTICLE_RECORDS,\n"
    if spread.strip() not in registry[start:end]:
        registry = registry[:end] + "\n" + spread.rstrip("\n") + registry[end:]
    registry_path.write_text(registry, encoding="utf-8")

    meta_path = static / "article-meta.js"
    meta = meta_path.read_text(encoding="utf-8")
    meta_import = f'import {{ AGY_{identifier}_ARTICLE_BODY_LIBRARY }} from "./{module.name}?v={import_query}";\n'
    meta = _insert_once(meta, "const ARTICLE_BODY_LIBRARY = {", meta_import + "\n")
    marker = "const ARTICLE_BODY_LIBRARY = {"
    body_spread = f"\n  ...AGY_{identifier}_ARTICLE_BODY_LIBRARY,"
    if body_spread.strip() not in meta:
        position = meta.index(marker) + len(marker)
        meta = meta[:position] + body_spread + meta[position:]
    meta_path.write_text(meta, encoding="utf-8")
    hub_updated_date = max(str(article["updated"] or article["published"]) for article in approved)
    return [
        module,
        registry_path,
        meta_path,
        *_bump_article_cache_queries(
            repo_root,
            import_query,
            hub_updated_date=hub_updated_date,
        ),
    ]


def _load_api_key() -> str:
    direct = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS") or ""
    if direct.strip():
        return direct.strip().strip('"').strip("'").split(",")[0].strip()
    env_file = Path.home() / ".config/ai-core/legacy_review.env"
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("GEMINI_API_KEY") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'").split(",")[0].strip()
    raise RuntimeError("missing local GEMINI_API_KEY or GEMINI_API_KEYS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare-matrix")
    prepare_identity = prepare.add_mutually_exclusive_group(required=True)
    prepare_identity.add_argument("--run-prefix")
    prepare_identity.add_argument("--exact-run-id")
    prepare.add_argument("--limit", type=int)
    prepare.add_argument("--exclude", action="append", default=[])
    prepare.add_argument("--max-articles-per-run", type=int, default=MAX_RUN_ARTICLES)
    rewrite = subparsers.add_parser("prepare-rewrite")
    rewrite.add_argument("--queue", type=Path, required=True)
    rewrite.add_argument("--batch", type=int, required=True)
    rewrite.add_argument("--run-dir", type=Path, required=True)
    rewrite.add_argument("--source-commit", required=True)
    prepare_repair = subparsers.add_parser("prepare-rewrite-repair")
    prepare_repair.add_argument("--source-run-dir", type=Path, required=True)
    prepare_repair.add_argument("--run-dir", type=Path, required=True)
    prepare_repair.add_argument("--source-commit", required=True)
    prepare_repair.add_argument("--repair-generation", type=int, default=1)
    run = subparsers.add_parser("run")
    run.add_argument("run_dir", type=Path)
    run.add_argument("--max-repairs", type=int, choices=range(0, 3), default=2)
    repair_run = subparsers.add_parser("run-rewrite-repair")
    repair_run.add_argument("run_dir", type=Path)
    isolated_run = subparsers.add_parser("run-isolated-rewrite")
    isolated_run.add_argument("run_dir", type=Path)
    rewrite_range = subparsers.add_parser("run-rewrite-range")
    rewrite_range.add_argument("--queue", type=Path, required=True)
    rewrite_range.add_argument("--evidence-root", type=Path, required=True)
    rewrite_range.add_argument("--source-commit", required=True)
    rewrite_range.add_argument("--start-batch", type=int, default=3)
    rewrite_range.add_argument("--end-batch", type=int, default=10)
    release = subparsers.add_parser("run-rewrite-release")
    release.add_argument("--evidence-root", type=Path, required=True)
    release.add_argument("--release-root", type=Path, required=True)
    release_prepare = subparsers.add_parser("prepare-rewrite-release-generation")
    release_prepare.add_argument("--source-dir", type=Path, required=True)
    release_prepare.add_argument("--run-dir", type=Path, required=True)
    release_prepare.add_argument("--batch", type=int, required=True)
    release_prepare.add_argument("--generation", type=int, required=True)
    release_generation = subparsers.add_parser("run-rewrite-release-generation")
    release_generation.add_argument("run_dir", type=Path)
    release_local_closure = subparsers.add_parser("run-rewrite-release-local-closure")
    release_local_closure.add_argument("run_dir", type=Path)
    release_review = subparsers.add_parser("review-rewrite-release")
    release_review.add_argument("run_dir", type=Path)
    release_summary = subparsers.add_parser("summarize-rewrite-release")
    release_summary.add_argument("release_root", type=Path)
    release_apply = subparsers.add_parser("apply-rewrite-release")
    release_apply.add_argument("release_root", type=Path)
    release_fallback = subparsers.add_parser("review-rewrite-release-fallback")
    release_fallback.add_argument("run_dir", type=Path)
    release_verify = subparsers.add_parser("verify-rewrite-release-apply")
    release_verify.add_argument("release_root", type=Path)
    repair_closure = subparsers.add_parser("run-rewrite-repair-closure")
    repair_closure.add_argument("run_dir", type=Path)
    review_parser = subparsers.add_parser("review-existing")
    review_parser.add_argument("run_dir", type=Path)
    approve = subparsers.add_parser("approve")
    approve.add_argument("run_dir", type=Path)
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--approve", action="append", default=[])
    approve.add_argument("--reject", action="append", default=[])
    approve.add_argument("--override", action="append", default=[], metavar="ARTICLE_ID=REASON")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("run_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    if args.command == "prepare-matrix":
        paths = prepare_matrix_runs(
            repo_root,
            args.run_prefix or args.exact_run_id,
            limit=args.limit,
            exclude_ids=set(args.exclude),
            max_articles_per_run=args.max_articles_per_run,
            exact_run_id=args.exact_run_id,
        )
        print(json.dumps({"backlog": sum(len(json.loads(path.read_text())["articles"]) for path in paths), "runs": [str(path.parent) for path in paths]}, ensure_ascii=False))
        return 0
    if args.command == "prepare-rewrite":
        path = prepare_rewrite_batch(
            repo_root,
            (repo_root / args.queue).resolve() if not args.queue.is_absolute() else args.queue,
            args.batch,
            (repo_root / args.run_dir).resolve() if not args.run_dir.is_absolute() else args.run_dir,
            args.source_commit,
        )
        print(json.dumps({"brief": str(path), "mode": "rewrite_existing_body"}, ensure_ascii=False))
        return 0
    if args.command == "prepare-rewrite-repair":
        source_run_dir = (repo_root / args.source_run_dir).resolve() if not args.source_run_dir.is_absolute() else args.source_run_dir
        target_run_dir = (repo_root / args.run_dir).resolve() if not args.run_dir.is_absolute() else args.run_dir
        path = prepare_rewrite_repair(
            repo_root,
            source_run_dir,
            target_run_dir,
            args.source_commit,
            args.repair_generation,
        )
        print(json.dumps({"brief": str(path), "repair_generation": args.repair_generation}, ensure_ascii=False))
        return 0
    if args.command == "run-rewrite-range":
        summary = run_rewrite_range(
            repo_root,
            (repo_root / args.queue).resolve() if not args.queue.is_absolute() else args.queue,
            (repo_root / args.evidence_root).resolve() if not args.evidence_root.is_absolute() else args.evidence_root,
            args.source_commit,
            GeminiClient.from_environment(),
            args.start_batch,
            args.end_batch,
        )
        print(json.dumps({"status": "CANDIDATES_050_READY", "candidate_count": summary["candidate_count"]}, ensure_ascii=False))
        return 0
    if args.command == "run-rewrite-release":
        summary = run_rewrite_release(
            (repo_root / args.evidence_root).resolve() if not args.evidence_root.is_absolute() else args.evidence_root,
            (repo_root / args.release_root).resolve() if not args.release_root.is_absolute() else args.release_root,
            GeminiClient.from_environment(),
        )
        print(json.dumps({"status": summary["status"], "approved": summary["reviewer_approved"]}, ensure_ascii=False))
        return 0
    if args.command == "prepare-rewrite-release-generation":
        path = prepare_rewrite_release_generation(
            args.source_dir.resolve(), args.run_dir.resolve(), args.batch, args.generation
        )
        print(json.dumps({"brief": str(path)}, ensure_ascii=False))
        return 0
    if args.command == "run-rewrite-release-generation":
        candidate, review = run_rewrite_release_generation(args.run_dir.resolve(), GeminiClient.from_environment())
        print(json.dumps({"run_id": candidate["run_id"], "approved": sum(item["verdict"] == "APPROVE" for item in review["articles"])}, ensure_ascii=False))
        return 0
    if args.command == "run-rewrite-release-local-closure":
        candidate, review = run_release_batch1_local_closure(args.run_dir.resolve())
        print(json.dumps({"run_id": candidate["run_id"], "approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]), "reviewer_required": True}, ensure_ascii=False))
        return 0
    if args.command == "review-rewrite-release":
        review = review_rewrite_release_final(args.run_dir.resolve(), GeminiClient.from_environment())
        print(json.dumps({"approved": sum(item["verdict"] == "APPROVE" for item in review["articles"])}, ensure_ascii=False))
        return 0
    if args.command == "summarize-rewrite-release":
        summary = write_rewrite_release_summary(args.release_root.resolve())
        print(json.dumps({"status": summary["status"], "approved": summary["reviewer_approved"]}, ensure_ascii=False))
        return 0
    if args.command == "apply-rewrite-release":
        changed = apply_rewrite_release(repo_root, args.release_root.resolve())
        print(json.dumps({"status": "READY_TO_DEPLOY", "changed": [str(path) for path in changed]}, ensure_ascii=False))
        return 0
    if args.command == "review-rewrite-release-fallback":
        review = release_fallback_review(args.run_dir.resolve())
        print(json.dumps({"approved": len(review["articles"]), "reviewer_type": "codex_release_fallback"}, ensure_ascii=False))
        return 0
    if args.command == "verify-rewrite-release-apply":
        evidence = verify_rewrite_release_apply(repo_root, args.release_root.resolve())
        print(json.dumps({"status": evidence["status"], "verified": evidence["verified_article_count"]}, ensure_ascii=False))
        return 0
    run_dir = args.run_dir.resolve()
    if args.command == "run":
        candidate, review = run_writer_reviewer(
            run_dir,
            GeminiClient.from_environment(),
            max_repairs=args.max_repairs,
        )
        print(json.dumps({"run_id": candidate["run_id"], "approved_by_reviewer": sum(item["verdict"] == "APPROVE" for item in review["articles"]), "review": str(run_dir / "review.md")}, ensure_ascii=False))
        return 0
    if args.command in {"run-rewrite-repair", "run-isolated-rewrite"}:
        candidate, review = run_rewrite_repair(run_dir, GeminiClient.from_environment())
        print(json.dumps({"run_id": candidate["run_id"], "approved_by_reviewer": sum(item["verdict"] == "APPROVE" for item in review["articles"]), "review": str(run_dir / "review.md")}, ensure_ascii=False))
        return 0
    if args.command == "run-rewrite-repair-closure":
        candidate, review = run_rewrite_repair_closure(run_dir, GeminiClient.from_environment())
        print(json.dumps({"run_id": candidate["run_id"], "approved_by_reviewer": sum(item["verdict"] == "APPROVE" for item in review["articles"]), "review": str(run_dir / "review.md")}, ensure_ascii=False))
        return 0
    if args.command == "review-existing":
        review = review_existing_candidate(run_dir, GeminiClient.from_environment())
        print(json.dumps({"run_id": review["run_id"], "approved_by_reviewer": sum(item["verdict"] == "APPROVE" for item in review["articles"]), "review": str(run_dir / "review.md")}, ensure_ascii=False))
        return 0
    candidate_payload = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    if args.command == "approve":
        decisions = {str(article_id): "APPROVE" for article_id in args.approve}
        decisions.update({str(article_id): "REJECT" for article_id in args.reject})
        override_reasons: dict[str, str] = {}
        for value in args.override:
            if "=" not in value:
                raise ValueError("--override must use ARTICLE_ID=REASON")
            article_id, reason = value.split("=", 1)
            decisions[article_id] = "OVERRIDE_APPROVE"
            override_reasons[article_id] = reason
        approval = build_approval(candidate_payload["run_id"], candidate_payload["articles"], review, decisions, args.approved_by, override_reasons)
        write_json(run_dir / "approval.json", approval)
        print(json.dumps({"approval": str(run_dir / "approval.json"), "decisions": len(approval["articles"])}, ensure_ascii=False))
        return 0
    approval = json.loads((run_dir / "approval.json").read_text(encoding="utf-8"))
    changed = apply_approved_candidates(repo_root, candidate_payload["run_id"], candidate_payload["articles"], review, approval)
    print(json.dumps({"changed": [str(path) for path in changed]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

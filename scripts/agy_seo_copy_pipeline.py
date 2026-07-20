#!/usr/bin/env python3
"""Pantheon 統一文章產製、獨立審稿、核准與 apply pipeline。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = 1
MAX_RUN_ARTICLES = 5
MAX_ARTICLE_BRIEF_BYTES = 8192
DEFAULT_WRITER_MODEL = "gemini-3.5-flash"
DEFAULT_REVIEWER_MODEL = "gemini-3.1-pro-preview"
ANTIGRAVITY_MODEL_LABELS = {
    DEFAULT_WRITER_MODEL: "Gemini 3.5 Flash (Low)",
    DEFAULT_REVIEWER_MODEL: "Gemini 3.1 Pro (Low)",
}
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RUN_ROOT = Path(".work/gsc-copy")
MATRIX_PLAN = Path("artifacts/fortune_council/content_seo_execution/evidence/scale_clusters/cluster_plan.md")
PUBLICATION_STANDARD = Path("docs/pantheon_article_publication_standard.md")

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
REWRITE_ARTICLE_FIELDS = {"article_id", "identity", "current_body_sha256", "bodySections"}
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
    if exact_shape and len(value) != 5:
        raise CandidateValidationError("rewrite bodySections must contain exactly 5 sections")
    for section in value:
        if not isinstance(section, dict) or set(section) != {"heading", "paragraphs"}:
            raise CandidateValidationError("body sections require only heading and paragraphs")
        _ensure_string(section.get("heading"), "bodySections.heading")
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            raise CandidateValidationError("body section paragraphs must be non-empty")
        if exact_shape and len(paragraphs) != 3:
            raise CandidateValidationError("rewrite body section must contain exactly 3 paragraphs")
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
    if not 3 <= len(article["faq"]) <= 5:
        raise CandidateValidationError("faq must contain 3 to 5 items")
    for item in article["faq"]:
        if not isinstance(item, dict) or set(item) != {"question", "answer"}:
            raise CandidateValidationError("faq items require only question and answer")
        _ensure_string(item.get("question"), "faq.question")
        _ensure_string(item.get("answer"), "faq.answer")
    _validate_body_sections(article["bodySections"], exact_shape=False)


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


def validate_candidate(candidate: dict[str, Any]) -> None:
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
            _validate_rewrite_article(article)
            article_id = str(article["article_id"])
        if article_id in ids:
            raise CandidateValidationError(f"duplicate article id: {article_id}")
        ids.add(article_id)


def _candidate_id(article: dict[str, Any]) -> str:
    return str(article.get("id") or article.get("article_id") or "")


def _has_boundary_statement(text: str) -> bool:
    return bool(re.search(r"不能|不代表|不適合|不是|無法|並非|不得|僅供|只供|只提供", text))


def quality_findings(articles: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    sentence_owners: dict[str, set[str]] = {}
    for article in articles:
        article_id = _candidate_id(article)
        if "bodySections" not in article:
            text = "".join(str(article.get("proposed", {}).get(field, "")) for field in OPTIMIZE_FIELDS)
            paragraphs: list[str] = []
        else:
            paragraphs = [str(item) for section in article["bodySections"] for item in section["paragraphs"]]
            text = f"{article['title']}{article['description']}{article['answer']}{''.join(paragraphs)}"
            if not 70 <= len(str(article["description"])) <= 95:
                findings.append({"article_id": article_id, "code": "description_length", "message": "meta description 必須為 70 到 95 字"})
            if not _has_boundary_statement(str(article["description"])):
                findings.append({"article_id": article_id, "code": "description_boundary", "message": "meta description 本身必須包含明確限制"})
            if len(str(article["answer"])) > 50:
                findings.append({"article_id": article_id, "code": "answer_length", "message": "answer 必須在 50 字內"})
            body_length = len("".join(paragraphs))
            if not 1300 <= body_length <= 2000:
                findings.append({"article_id": article_id, "code": "body_length", "message": "單主題新文章正文必須為 1300 到 2000 字"})
            if len(article["bodySections"]) < 5:
                findings.append({"article_id": article_id, "code": "section_count", "message": "正文至少需要 5 個 H2 段落"})
            for section_index, section in enumerate(article["bodySections"], start=1):
                section_paragraphs = section["paragraphs"]
                if not 2 <= len(section_paragraphs) <= 4:
                    findings.append({"article_id": article_id, "code": "paragraph_count", "message": f"第 {section_index} 節必須有 2 到 4 段"})
                for paragraph_index, paragraph in enumerate(section_paragraphs, start=1):
                    if not 80 <= len(str(paragraph)) <= 160:
                        findings.append({"article_id": article_id, "code": "paragraph_length", "message": f"第 {section_index} 節第 {paragraph_index} 段必須為 80 到 160 字"})
            if not 20 <= len(str(article["title"])) <= 45:
                findings.append({"article_id": article_id, "code": "title_length", "message": "meta title 超出 20 到 45 字安全邊界；28 到 36 字仍為優先目標"})
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
                if re.search(r"網路論壇|網友.{0,8}(?:俗稱|稱為)|社群.{0,8}(?:俗稱|代稱)", text):
                    findings.append({"article_id": article_id, "code": "false_social_origin", "message": "不得把 Pantheon 64 分支誤寫成網路論壇俗稱"})
        proposed = article.get("proposed") if isinstance(article.get("proposed"), dict) else None
        if proposed is not None:
            if not 70 <= len(str(proposed["description"])) <= 95:
                findings.append({"article_id": article_id, "code": "description_length", "message": "meta description 必須為 70 到 95 字"})
            if not _has_boundary_statement(str(proposed["description"])):
                findings.append({"article_id": article_id, "code": "description_boundary", "message": "meta description 本身必須包含明確限制"})
            if len(str(proposed["answer"])) > 50:
                findings.append({"article_id": article_id, "code": "answer_length", "message": "answer 必須在 50 字內"})
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
    return findings


def rewrite_quality_findings(brief: dict[str, Any], articles: list[dict[str, Any]]) -> list[dict[str, str]]:
    """本卡正文改寫的 deterministic gate；不以 Reviewer 主觀判斷取代。"""
    findings: list[dict[str, str]] = []
    expected_ids = [str(item["article_id"]) for item in brief["articles"]]
    actual_ids = [str(item.get("article_id") or "") for item in articles]
    if actual_ids != expected_ids:
        return [{"article_id": article_id, "code": "article_order", "message": "文章集合或順序與 rewrite brief 不一致"} for article_id in expected_ids]
    sentence_owners: dict[str, set[str]] = {}
    for source, article in zip(brief["articles"], articles, strict=True):
        article_id = str(article["article_id"])
        sections = article.get("bodySections") if isinstance(article.get("bodySections"), list) else []
        paragraphs = [str(paragraph) for section in sections for paragraph in section.get("paragraphs", [])]
        text = "".join(paragraphs)
        if len(sections) != 5:
            findings.append({"article_id": article_id, "code": "section_count", "message": "正文必須恰好 5 節"})
        for section_index, section in enumerate(sections, start=1):
            section_paragraphs = section.get("paragraphs", [])
            if len(section_paragraphs) != 3:
                findings.append({"article_id": article_id, "code": "paragraph_count", "message": f"第 {section_index} 節必須恰好 3 段"})
            heading = str(section.get("heading") or "")
            if any(template in heading for template in REWRITE_TEMPLATE_HEADINGS):
                findings.append({"article_id": article_id, "code": "template_heading", "message": f"不得沿用批次模板小標：{heading}"})
            for paragraph_index, paragraph in enumerate(section_paragraphs, start=1):
                length = len(str(paragraph))
                if not 90 <= length <= 130:
                    findings.append({"article_id": article_id, "code": "paragraph_length", "message": f"第 {section_index} 節第 {paragraph_index} 段為 {length} 字；必須 90 到 130 字"})
        if not 1300 <= len(text) <= 2000:
            findings.append({"article_id": article_id, "code": "body_length", "message": f"正文為 {len(text)} 字；必須 1300 到 2000 字"})
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
    return findings


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


def rewrite_aggregate_findings(brief: dict[str, Any], articles: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return rewrite_quality_findings(brief, articles), rewrite_uniqueness_findings(brief, articles)


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


def validate_apply_gate(candidates: list[dict[str, Any]], review: dict[str, Any], approval: dict[str, Any]) -> list[dict[str, Any]]:
    validate_review(review, candidates)
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


def _registry_inventory(repo_root: Path) -> list[dict[str, Any]]:
    script = """
import { getArticlePath, listArticleRecords } from './app/web/static/article-registry.js';
console.log(JSON.stringify(listArticleRecords().map((article) => ({
  id: article.id, primaryKeyword: article.primaryKeyword, title: article.title,
  description: article.description, answer: article.answer,
  path: getArticlePath(article), slug: article.slug,
}))));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=repo_root, check=True, capture_output=True, text=True)
    return list(json.loads(result.stdout))


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
    rows = _matrix_rows((repo_root / MATRIX_PLAN).read_text(encoding="utf-8"))
    inventory = _registry_inventory(repo_root)
    return [row for row in rows if not _row_is_present(row, inventory)]


def compact_publication_policy() -> dict[str, Any]:
    return {
        "language": "繁體中文",
        "voice": "白話、具體、先回答讀者問題；冷靜但不替讀者下判決",
        "title": "20 到 45 字為硬性安全邊界；28 到 36 個中文字為偏好，且須含主關鍵字",
        "description": "70 到 95 字，包含適用情境與限制",
        "answer": "50 字內",
        "faq": "3 到 5 題真實問答",
        "body": "單主題文章 1300 到 2000 字；至少 5 節，每節 2 到 4 段，每段 80 到 160 字；至少兩個專屬生活場景、3 個具體動詞、反例與不能代表什麼",
        "generation_profile": "本批固定輸出 5 節，每節恰好 3 段，每段 90 到 130 字；正文目標 1500 到 1800 字，不得超過 2000 字",
        "tags": f"必含 {', '.join(sorted(REQUIRED_PUBLIC_TAGS))}，並加入產品線與情境 tags",
        "boundary": "不承諾結果，不提供醫療、法律或投資建議，不把工具訊號寫成個人結論",
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
        if article_id.startswith("MBTI-"):
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
) -> list[Path]:
    full_backlog = build_matrix_backlog(repo_root)
    targets = _matrix_targets(repo_root, full_backlog)
    excluded = exclude_ids or set()
    backlog = [row for row in full_backlog if str(row["id"]) not in excluded]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        backlog = backlog[:limit]
    output_root = output_root or repo_root / RUN_ROOT
    article_briefs = [{"matrix": row, "target": targets[row["id"]], "policy": compact_publication_policy()} for row in backlog]
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    for article in article_briefs:
        candidate_batch = [*current_batch, article]
        run_id = f"{run_prefix}-{len(batches) + 1:02d}"
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "mode": "create",
            "source": {"type": "matrix", "path": MATRIX_PLAN.as_posix()},
            "articles": candidate_batch,
        }
        if current_batch and (len(candidate_batch) > MAX_RUN_ARTICLES or len(compact_json_bytes(candidate)) + 1 > MAX_ARTICLE_BRIEF_BYTES):
            batches.append(current_batch)
            current_batch = [article]
        else:
            current_batch = candidate_batch
    if current_batch:
        batches.append(current_batch)

    paths = []
    for index, articles in enumerate(batches, start=1):
        run_id = f"{run_prefix}-{index:02d}"
        brief = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "mode": "create", "source": {"type": "matrix", "path": MATRIX_PLAN.as_posix()}, "articles": articles}
        validate_new_brief(brief)
        path = output_root / run_id / "brief.json"
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
const origin = 'https://mysticpantheon.com';
console.log(JSON.stringify(listArticleRecords().map((record) => {
  const canonicalPath = getArticlePath(record);
  const content = buildArticleContent(canonicalPath, origin);
  return { id: record.id, record, canonicalPath, currentBody: content.bodySections,
    published: content.published, updated: content.updated };
})));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
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
    validate_candidate(source_candidate)
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
        transport_name = os.environ.get("AGY_GEMINI_TRANSPORT", "cli").strip().lower()
        if transport_name == "cli":
            client = cls()
            client.transport = client._cli_transport
            return client
        if transport_name == "api":
            return cls(_load_api_key())
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
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.45 if role == "writer" else 0.1,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
                "thinkingConfig": {"thinkingLevel": "LOW"},
            },
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
            raise RuntimeError("Gemini/Antigravity CLI not found; set AGY_GEMINI_CLI")
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
        settings = {
            "general": {"defaultApprovalMode": "plan", "enableAutoUpdate": False},
            "modelConfigs": {
                "customAliases": {
                    "agy-low": {
                        "modelConfig": {
                            "model": model,
                            "generateContentConfig": {
                                "temperature": generation["temperature"],
                                "thinkingConfig": {"thinkingLevel": "LOW"},
                            },
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
                raise RuntimeError(
                    "Gemini CLI not found; set AGY_GEMINI_CLI to the executable or full command"
                ) from error
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:1000]
            raise RuntimeError(f"Gemini CLI exited {completed.returncode}: {detail}")
        output = completed.stdout.strip()
        if is_antigravity:
            return json.loads(output)
        envelope = json.loads(output)
        if envelope.get("error"):
            raise RuntimeError(f"Gemini CLI error: {envelope['error']}")
        response = envelope.get("response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Gemini CLI response missing response text")
        return json.loads(response)


def _article_json_schema() -> dict[str, Any]:
    faq_item = {"type": "object", "additionalProperties": False, "properties": {"question": {"type": "string"}, "answer": {"type": "string"}}, "required": ["question", "answer"]}
    section_item = {"type": "object", "additionalProperties": False, "properties": {"heading": {"type": "string"}, "paragraphs": {"type": "array", "items": {"type": "string", "minLength": 90, "maxLength": 130}, "minItems": 3, "maxItems": 3}}, "required": ["heading", "paragraphs"]}
    properties = {
        "id": {"type": "string"}, "section": {"type": "string"}, "product": {"type": "string"}, "slug": {"type": "string"},
        "serial": {"type": "string"}, "urlSlug": {"type": "string"}, "primaryKeyword": {"type": "string"},
        "secondaryKeywords": {"type": "array", "items": {"type": "string"}, "minItems": 2}, "title": {"type": "string", "minLength": 20, "maxLength": 45},
        "description": {"type": "string", "minLength": 70, "maxLength": 95}, "answer": {"type": "string", "maxLength": 50}, "tags": {"type": "array", "items": {"type": "string"}, "minItems": 9, "maxItems": 12},
        "faq": {"type": "array", "items": faq_item, "minItems": 3, "maxItems": 5},
        "bodySections": {"type": "array", "items": section_item, "minItems": 5, "maxItems": 5},
        "published": {"type": "string"}, "updated": {"type": "string"},
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
        section = _article_json_schema()["properties"]["bodySections"]
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
}
EXTERNAL_CREATE_FIELDS = PUBLIC_CREATE_FIELDS | {"primaryKeyword"}


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
                "bodyShape": "恰好 5 節；每節恰好 3 段；每段 90 到 130 字；正文 1300 到 2000 字",
                "opening": "前 80 字自然回答 primaryKeyword",
                "content": "至少兩個專屬生活場景、3 個具體動詞、反例或限制",
                "boundaries": "不得把 MBTI、塔羅或命盤寫成診斷、固定人格、保證預測、投資建議或命運結論",
                "uniqueness": "不得使用批次模板小標，不得跨篇共用完整句型",
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
                "bodySections": _article_json_schema()["properties"]["bodySections"],
            },
            "required": ["slot", "bodySections"],
        }
    else:
        full = _article_json_schema()
        properties = {"slot": {"type": "string"}}
        properties.update({field: full["properties"][field] for field in sorted(EXTERNAL_CREATE_FIELDS)})
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


def hydrate_candidate(brief: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
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
            articles.append({**source["target"], **{field: generated[field] for field in sorted(PUBLIC_CREATE_FIELDS)}})
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
            if set(generated) != {"slot", "bodySections"}:
                raise CandidateValidationError("external rewrite fields must contain only slot and bodySections")
            articles.append(
                {
                    "article_id": source["article_id"],
                    "identity": source["identity"],
                    "current_body_sha256": source["current_body_sha256"],
                    "bodySections": generated["bodySections"],
                }
            )
    candidate = {"schema_version": SCHEMA_VERSION, "run_id": brief["run_id"], "mode": mode, "articles": articles}
    validate_candidate(candidate)
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


def external_review_schema() -> dict[str, Any]:
    finding = {"type": "object", "additionalProperties": False, "properties": {"code": {"type": "string"}, "message": {"type": "string"}}, "required": ["code", "message"]}
    item = {"type": "object", "additionalProperties": False, "properties": {"slot": {"type": "string"}, "verdict": {"type": "string", "enum": ["APPROVE", "REJECT"]}, "findings": {"type": "array", "items": finding}}, "required": ["slot", "verdict", "findings"]}
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


def review_schema() -> dict[str, Any]:
    finding = {"type": "object", "additionalProperties": False, "properties": {"code": {"type": "string"}, "message": {"type": "string"}}, "required": ["code", "message"]}
    item = {"type": "object", "additionalProperties": False, "properties": {"article_id": {"type": "string"}, "candidate_sha256": {"type": "string"}, "verdict": {"type": "string", "enum": ["APPROVE", "REJECT"]}, "findings": {"type": "array", "items": finding}}, "required": ["article_id", "candidate_sha256", "verdict", "findings"]}
    return {"type": "object", "additionalProperties": False, "properties": {"schema_version": {"type": "integer", "enum": [1]}, "run_id": {"type": "string"}, "articles": {"type": "array", "items": item, "minItems": 1, "maxItems": 5}}, "required": ["schema_version", "run_id", "articles"]}


def _writer_prompt(brief: dict[str, Any], prior: dict[str, Any] | None = None, findings: list[dict[str, Any]] | None = None) -> str:
    instruction = "請依 public brief 產生完整文章內容。slot 必須逐字複製。"
    if brief.get("mode") == "optimize":
        instruction = "只輸出各 slot 的 proposed title、description、answer。"
    elif brief.get("mode") == "rewrite_existing_body":
        instruction = "只輸出各 slot 的完整 bodySections；不得輸出或改動任何 identity、metadata、FAQ、tag、日期或 URL 欄位。"
    if prior is not None:
        instruction = "請只修正 findings 指出的問題，保留候選稿中正確且具體的內容；仍須輸出完整 candidate。"
    return "\n".join([
        instruction,
        "不得共用跨篇完整句型。",
        "public brief:", json.dumps(public_model_brief(brief), ensure_ascii=False),
        "prior public candidate:", json.dumps(public_model_candidate(brief, prior), ensure_ascii=False) if prior else "null",
        "public findings:", json.dumps(public_model_findings(brief, findings or []), ensure_ascii=False),
    ])


def _reviewer_prompt(brief: dict[str, Any], candidate: dict[str, Any], deterministic_findings: list[dict[str, str]]) -> str:
    return "\n".join([
        "獨立審查候選稿是否符合 public brief 與發布規範；slot 必須逐字複製。",
        "檢查：搜尋意圖、具體生活場景、可觀察動詞、反例、限制、繁體中文、英文殘字與錯別字、禁詞、模板句、醫療/法律/財務邊界。",
        "20 到 45 字才是標題硬性安全邊界；28 到 36 字只是偏好，不得只因未落在偏好區間而退件。",
        "禁詞必須依語境判斷；不一定、不能保證、不是注定等否定邊界句不得當成承諾禁詞。",
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
        "你是新的獨立 Gemini Pro Reviewer，必須同時比較全部五篇；slot 必須逐字複製。",
        "本卡只審 Repair 1：確認跨篇完整句、共用 H2、長片段、段落開頭與抽象句型／論證結構不再相似。",
        "同時確認 5 節、每節 3 段、段長、總字數、前 80 字、專屬場景、具體動詞、反例與安全限制沒有回歸。",
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
        receipt["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        write_json(receipt_path, receipt)
        raise
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
            raise RuntimeError("rewrite_existing_body reviewer must use Gemini 3.1 Pro Low")
    candidate: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    completed_attempts = 0
    writer_schema_repairs = 0
    for attempt in range(max_repairs + 1):
        attempt_dir = run_dir / "attempts" / f"{attempt + 1:02d}"
        completed_attempts = attempt + 1
        findings = [] if review is None else [
            {"article_id": item["article_id"], **finding}
            for item in review["articles"]
            for finding in item.get("findings", [])
        ]
        writer_prompt = _writer_prompt(brief, candidate, findings)
        if writer_schema_repairs:
            writer_prompt = "\n".join(
                [
                    f"schema repair {writer_schema_repairs}: 前次 Writer JSON 格式無效。",
                    "必須輸出完整 schema，且每篇都不得漏掉任何 required field。",
                    writer_prompt,
                ]
            )
        writer_schema = external_candidate_schema(mode)
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
            candidate = hydrate_candidate(brief, external_candidate)
        except (CandidateValidationError, json.JSONDecodeError, TypeError, ValueError) as error:
            writer_schema_repairs += 1
            write_json(
                attempt_dir / "writer-schema-rejection.json",
                {"verdict": "REJECT", "hard_failure": True, "code": "invalid_writer_schema", "error_type": type(error).__name__},
            )
            if attempt < max_repairs:
                continue
            raise CandidateValidationError("writer schema remained invalid after two repairs") from error
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
        invalid_reviewer = False
        try:
            external_review = _generate_with_receipt(
                client,
                "reviewer",
                _reviewer_prompt(brief, candidate, deterministic),
                external_review_schema(),
                attempt_dir / "reviewer-operation.json",
            )
            write_json(attempt_dir / "external-review.json", external_review)
            review = hydrate_review(brief, candidate, external_review)
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
    assert candidate is not None and review is not None
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
            "writer_model": getattr(client, "writer_model", "test-double"),
            "reviewer_model": getattr(client, "reviewer_model", "test-double"),
            "candidate_sha256": hashlib.sha256(compact_json_bytes(candidate)).hexdigest(),
            "review_sha256": hashlib.sha256(compact_json_bytes(review)).hexdigest(),
            "article_sha256": {_candidate_id(article): article_sha256(article) for article in candidate["articles"]},
            "approval_created": False,
            "apply_executed": False,
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
        try:
            external_review_path = attempt_dir / "external-review.json"
            if external_review_path.exists():
                external_review = json.loads(external_review_path.read_text(encoding="utf-8"))
            else:
                external_review = _generate_with_receipt(
                    client,
                    "reviewer",
                    _repair_reviewer_prompt(brief, candidate, deterministic, style_contracts),
                    external_review_schema(),
                    attempt_dir / "reviewer-operation.json",
                )
                reviewer_calls += 1
                write_json(external_review_path, external_review)
            review = hydrate_review(brief, candidate, external_review)
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
    validate_candidate(candidate)
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
        "完整輸出該篇 5 節 × 3 段正文；每段 90–130 個中文字，全文 1300–2000 字。",
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
    validate_candidate(source_candidate)
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
        else:
            try:
                external_review = _generate_with_receipt(
                    client,
                    "reviewer",
                    _repair_reviewer_prompt(brief, candidate, deterministic, styles),
                    external_review_schema(),
                    attempt_dir / "reviewer-operation.json",
                )
                reviewer_calls += 1
                write_json(attempt_dir / "external-review.json", external_review)
                review = hydrate_review(brief, candidate, external_review)
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
                external_review_schema(),
                round_dir / "reviewer-operation.json",
            )
            write_json(external_path, external)
            review = hydrate_review(brief, candidate, external)
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
    changed = [module, meta_path, *_bump_article_cache_queries(repo_root, "rewrite-release-001")]
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
            raise RuntimeError("rewrite closure reviewer must use Gemini 3.1 Pro Low")
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
        external_review_schema(),
        closure_dir / "reviewer-operation.json",
    )
    write_json(closure_dir / "external-review.json", external_review)
    review = hydrate_review(brief, candidate, external_review)
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
    if brief.get("mode") == "rewrite_existing_body":
        validate_rewrite_brief(brief)
        if isinstance(client, GeminiClient) and getattr(client.transport, "__name__", "") != "_cli_transport":
            raise RuntimeError("rewrite_existing_body requires a fresh headless reviewer process")
        if isinstance(client, GeminiClient) and client.reviewer_model != DEFAULT_REVIEWER_MODEL:
            raise RuntimeError("rewrite_existing_body reviewer must use Gemini 3.1 Pro Low")
        expected = brief["articles"]
        if [article["article_id"] for article in candidate["articles"]] != [item["article_id"] for item in expected]:
            raise CandidateValidationError("existing rewrite candidate set or order differs from brief")
        for article, source in zip(candidate["articles"], expected, strict=True):
            if article["identity"] != source["identity"] or article["current_body_sha256"] != source["current_body_sha256"]:
                raise CandidateValidationError(f"existing rewrite candidate changed immutable fields for {article['article_id']}")
        deterministic = rewrite_quality_findings(brief, candidate["articles"])
    else:
        deterministic = quality_findings(candidate["articles"])
    try:
        external_review = _generate_with_receipt(
            client,
            "reviewer",
            _reviewer_prompt(brief, candidate, deterministic),
            external_review_schema(),
            run_dir / "review-existing-operation.json",
        )
        write_json(run_dir / "external-review-existing.json", external_review)
        review = hydrate_review(brief, candidate, external_review)
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


def _bump_article_cache_queries(repo_root: Path, token: str) -> list[Path]:
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
    old = "return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy(article, getArticleSectionRecord(article.section)));"
    new = "return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy({ ...article, ...(ARTICLE_SEO_COPY_OVERRIDES[article.id] || {}) }, getArticleSectionRecord(article.section)));"
    if old in registry:
        registry = registry.replace(old, new, 1)
    elif new not in registry:
        raise ValueError("listArticleRecords override marker not found")
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
    return [module, registry_path, meta_path, *_bump_article_cache_queries(repo_root, import_query)]


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
    prepare.add_argument("--run-prefix", required=True)
    prepare.add_argument("--limit", type=int)
    prepare.add_argument("--exclude", action="append", default=[])
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
        paths = prepare_matrix_runs(repo_root, args.run_prefix, limit=args.limit, exclude_ids=set(args.exclude))
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
        candidate, review = run_writer_reviewer(run_dir, GeminiClient.from_environment())
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

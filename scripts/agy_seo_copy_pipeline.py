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
    if head != source_commit:
        raise ValueError(f"rewrite source commit mismatch: expected {source_commit}, got {head}")
    queue = _rewrite_batch_payload(queue_path.read_text(encoding="utf-8"), batch_number)
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
            articles.append({**source["target"], **{field: generated[field] for field in PUBLIC_CREATE_FIELDS}})
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
                | {field: article[field] for field in PUBLIC_CREATE_FIELDS}
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


def _generate_with_receipt(
    client: Any,
    role: str,
    prompt: str,
    schema: dict[str, Any],
    receipt_path: Path,
) -> dict[str, Any]:
    model = getattr(client, "writer_model" if role == "writer" else "reviewer_model", "test-double")
    transport_name = getattr(getattr(client, "transport", None), "__name__", type(client).__name__)
    started = datetime.now().astimezone()
    receipt = {
        "role": role,
        "model": model,
        "thinking_level": "LOW",
        "started_at": started.isoformat(timespec="seconds"),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(compact_json_bytes(schema)).hexdigest(),
        "transport": transport_name,
        "fresh_headless_process": transport_name == "_cli_transport",
        "status": "started",
    }
    try:
        result = client.generate_json(role, prompt, schema)
    except Exception as error:
        receipt["status"] = "error"
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
    for attempt in range(max_repairs + 1):
        attempt_dir = run_dir / "attempts" / f"{attempt + 1:02d}"
        completed_attempts = attempt + 1
        findings = [] if review is None else [
            {"article_id": item["article_id"], **finding}
            for item in review["articles"]
            for finding in item.get("findings", [])
        ]
        writer_prompt = _writer_prompt(brief, candidate, findings)
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
    run = subparsers.add_parser("run")
    run.add_argument("run_dir", type=Path)
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
    run_dir = args.run_dir.resolve()
    if args.command == "run":
        candidate, review = run_writer_reviewer(run_dir, GeminiClient.from_environment())
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

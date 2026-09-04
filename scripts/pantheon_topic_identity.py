#!/usr/bin/env python3
"""既有內容矩陣的 deterministic topic identity 與唯讀去重 adapter。"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import scripts.agy_seo_copy_pipeline as pipeline


SITE_ORIGIN = "https://www.mysticpantheon.com"
MATRIX_DIMENSIONS = (
    "domain",
    "entity",
    "semantic_intent",
    "scenario",
    "relationship_context",
    "time_window",
    "template_family",
    "product_intent",
)
REQUIRED_IDENTITY_FIELDS = (
    "domain",
    "entity",
    "semantic_intent",
    "scenario",
    "template_family",
    "product_intent",
)


class TopicIdentityValidationError(ValueError):
    """Topic identity 必要維度缺失或與內容不一致。"""


def _normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[^\w\u3400-\u9fff]+", "", text)


def _normalize_slug(value: object) -> str:
    slug = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    return re.sub(r"[-_\s]+", "-", slug).strip("-/")


def _path(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    path = parsed.path if parsed.scheme or parsed.netloc else raw
    normalized = "/" + path.strip("/")
    return normalized if normalized != "/" else ""


def _record_identity(record: dict[str, Any]) -> str | None:
    value = record.get("topic_id") or record.get("id") or record.get("article_id")
    return str(value) if value else None


def _record_slugs(record: dict[str, Any]) -> set[str]:
    slugs = {
        _normalize_slug(record.get("slug")),
        _normalize_slug(record.get("urlSlug")),
    }
    for field in ("path", "route", "canonical"):
        route = _path(record.get(field))
        if route:
            slugs.add(_normalize_slug(route.rsplit("/", 1)[-1]))
    return slugs - {""}


def _entity(title: str) -> str:
    for token, value in (
        ("塔羅", "tarot"),
        ("人格", "personality"),
        ("mbti", "personality"),
        ("命盤", "birth-chart"),
        ("八字", "birth-chart"),
        ("紫微", "birth-chart"),
        ("星盤", "astrology"),
        ("星座", "astrology"),
        ("命書", "report"),
        ("報告", "report"),
    ):
        if token in title.lower():
            return value
    return "general"


def _time_window(text: str) -> str:
    for token, value in (
        ("年度", "annual"),
        ("長期", "long-term"),
        ("短期", "short-term"),
        ("現在", "current"),
        ("當下", "current"),
    ):
        if token in text:
            return value
    return "unspecified"


def build_topic_id(topic: dict[str, Any]) -> str:
    """只由語意維度建立穩定 identity，不納入來源 lineage 或 title。"""
    payload = [_normalize_text(topic.get(field)) for field in MATRIX_DIMENSIONS]
    missing = [
        field
        for field in REQUIRED_IDENTITY_FIELDS
        if not _normalize_text(topic.get(field))
    ]
    if missing:
        raise TopicIdentityValidationError(
            f"missing required identity dimensions: {', '.join(missing)}"
        )
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return f"topic-{digest}"


def _finish_topic(topic: dict[str, Any]) -> dict[str, Any]:
    topic["topic_id"] = build_topic_id(topic)
    topic["priority_score"] = 0
    topic["coverage_status"] = "AVAILABLE"
    topic["duplicate_of_topic_id"] = None
    topic["duplicate_reason"] = None
    return topic


def load_article_matrix_topics(path: Path) -> list[dict[str, Any]]:
    topics: list[dict[str, Any]] = []
    row = re.compile(
        r"^\|\s*([LCRWD]\d{2})\s*\|\s*\[([^]]+)]\((/topics/[^)]+)\)\s*\|\s*([^|]+)\|"
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        match = row.match(line)
        if not match:
            continue
        source_id, title, route, intent = (part.strip() for part in match.groups())
        parts = route.strip("/").split("/")
        domain, slug = parts[1], parts[-1]
        topics.append(
            _finish_topic(
                {
                    "source": "article_matrix",
                    "source_id": source_id,
                    "source_matrix_ref": f"article_matrix:{source_id}",
                    "domain": "fortune",
                    "entity": _entity(title),
                    "semantic_intent": intent,
                    "scenario": "relationship" if domain == "relationships" else domain,
                    "relationship_context": domain,
                    "time_window": _time_window(f"{title}{intent}"),
                    "template_family": "topic-question-guide",
                    "product_intent": (
                        "report" if _entity(title) == "report" else "reflection"
                    ),
                    "search_volume": "UNKNOWN",
                    "title": title,
                    "article_id": source_id,
                    "route": route,
                    "canonical": f"{SITE_ORIGIN}{route}",
                    "slug": slug,
                }
            )
        )
    return topics


def load_article_brief_topics(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    heading = re.compile(r"^###\s+([MTCPA]\d{2})：(.+)$", re.MULTILINE)
    matches = list(heading.finditer(text))
    topics: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : block_end]
        keyword_match = re.search(r"^主攻關鍵字：(.+)$", block, re.MULTILINE)
        if keyword_match is None:
            raise ValueError(f"brief {match.group(1)} 缺少主攻關鍵字")
        source_id, title = match.group(1), match.group(2).strip()
        intent = keyword_match.group(1).strip()
        prefix = source_id[0]
        domain = {
            "M": "personality",
            "T": "tarot",
            "C": "birth-chart",
            "A": "astrology",
            "P": "life-topic",
        }[prefix]
        topics.append(
            _finish_topic(
                {
                    "source": "article_briefs_first_30",
                    "source_id": source_id,
                    "source_matrix_ref": f"article_briefs_first_30:{source_id}",
                    "domain": "fortune",
                    "entity": _entity(f"{title}{intent}"),
                    "semantic_intent": intent,
                    "scenario": _normalize_text(intent),
                    "relationship_context": domain,
                    "time_window": _time_window(title),
                    "template_family": f"{domain}-brief",
                    "product_intent": "topic-report" if prefix == "P" else "education",
                    "search_volume": "UNKNOWN",
                    "title": title,
                    "article_id": "",
                    "route": "",
                    "canonical": "",
                    "slug": "",
                }
            )
        )
    return topics


def load_existing_corpus(repo_root: Path) -> list[dict[str, Any]]:
    return pipeline.load_publication_reference_corpus(repo_root)


def _result(
    status: str,
    level: str | None,
    match: dict[str, Any] | None,
) -> dict[str, str | None]:
    matched_identity = _record_identity(match or {})
    return {
        "status": status,
        "level": level,
        "matched_identity": matched_identity,
        "coverage_status": status,
        "duplicate_of_topic_id": matched_identity,
        "duplicate_reason": level,
    }


def classify_topic(
    topic: dict[str, Any],
    existing_articles: Iterable[dict[str, Any]],
    planned_topics: Iterable[dict[str, Any]] = (),
) -> dict[str, str | None]:
    existing = [*existing_articles]
    planned = [*planned_topics]
    candidate_topic_id = str(topic.get("topic_id") or "").strip()
    if not candidate_topic_id:
        raise TopicIdentityValidationError("topic_id is required")
    if candidate_topic_id != build_topic_id(topic):
        raise TopicIdentityValidationError("topic_id does not match identity dimensions")
    for record in planned:
        if candidate_topic_id and record.get("topic_id") == candidate_topic_id:
            return _result("COLLISION", "exact_identity", record)

    candidate_id = _normalize_text(topic.get("article_id"))
    candidate_paths = {_path(topic.get("route")), _path(topic.get("canonical"))} - {""}
    for record in [*existing, *planned]:
        record_id = _normalize_text(record.get("id") or record.get("article_id"))
        record_paths = {
            _path(record.get("path")),
            _path(record.get("route")),
            _path(record.get("canonical")),
            *(_path(path) for path in record.get("legacyPaths", [])),
        } - {""}
        if (candidate_id and candidate_id == record_id) or candidate_paths & record_paths:
            return _result("COLLISION", "article_identity", record)

    candidate_title = _normalize_text(topic.get("title"))
    candidate_slugs = _record_slugs(topic)
    for record in [*existing, *planned]:
        if (
            candidate_title
            and candidate_title == _normalize_text(record.get("title"))
        ) or candidate_slugs & _record_slugs(record):
            return _result("COLLISION", "normalized_title_slug", record)

    combination = tuple(_normalize_text(topic.get(field)) for field in MATRIX_DIMENSIONS)
    for record in planned:
        if all(combination) and combination == tuple(
            _normalize_text(record.get(field)) for field in MATRIX_DIMENSIONS
        ):
            return _result("COLLISION", "matrix_combination", record)

    candidate_intent = _normalize_text(
        topic.get("semantic_intent") or topic.get("primaryKeyword")
    )
    for record in [*existing, *planned]:
        record_intent = _normalize_text(
            record.get("semantic_intent") or record.get("primaryKeyword")
        )
        if candidate_intent and candidate_intent == record_intent:
            return _result("REVIEW_NEEDED", "same_intent_different_title", record)
    return _result("AVAILABLE", None, None)


def check_topic(
    repo_root: Path,
    topic: dict[str, Any],
    planned_topics: Iterable[dict[str, Any]] = (),
) -> dict[str, str | None]:
    return classify_topic(topic, load_existing_corpus(repo_root), planned_topics)

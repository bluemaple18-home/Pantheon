#!/usr/bin/env python3
"""以既有 Gemini Writer／Reviewer gate 產製並發布多語文章。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
from collections import Counter
import copy
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Callable
import unicodedata

from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
SUPPORTED_LOCALES = {"en", "ja", "ko"}
TRANSLATION_IDENTITY_LANES = {"i18n-new", "i18n-rewrite"}
TRANSLATION_BRIEF_FIELDS = frozenset({"schema_version", "run_id", "mode", "articles"})
LEGACY_REWRITE_TRANSLATION_LANE = "i18n-rewrite"
TRANSLATION_REPLACEMENT_REASONS = frozenset({
    "LOCALE_PLAN_VALIDATION",
    "NETWORK",
    "PROVIDER_UNAVAILABLE",
    "SCHEMA_INVALID_PAYLOAD",
})
LOCALE_LABELS = {"en": "English", "ja": "日本語", "ko": "한국어"}
LOCALE_EDITORIAL_CONTRACTS = {
    "en": {
        "voice": "Write as an original English web editor: direct, clear, calm, and useful. Use active voice and natural subject-verb order.",
        "syntax": "Lead with the answer, use short scannable headings, vary sentence length, and address the reader as 'you' only when it helps.",
        "search": "Derive the query phrasing from the current source facts. Use natural English question and noun-phrase patterns without keyword stuffing.",
        "avoid": "Do not preserve Chinese sentence order, parallelism, section boundaries, or repeated negative constructions. Avoid calques, generic AI polish, inflated adjectives, decorative metaphors, and formulaic conclusions.",
    },
    "ja": {
        "voice": "日本のWebメディア向けに、自然で落ち着いた「です・ます調」で書く。説明は丁寧にするが、回りくどくしない。",
        "syntax": "日本語として自然な主題提示と省略を使い、長い修飾語を分ける。見出しと段落は読者の疑問順に再構成する。",
        "search": "現在のsource factsから検索意図を導き、日本語で実際に入力される助詞省略や疑問形を自然に使う。キーワードを詰め込まない。",
        "avoid": "中国語の語順、対句、段落構成を写さない。「〜することができます」「〜において」「〜を提供します」などの翻訳調を連発しない。文体を混在させない。",
    },
    "ko": {
        "voice": "한국 웹 콘텐츠에 맞는 자연스럽고 신뢰감 있는 설명체로 쓴다. 설명은 합니다체를 기본으로 하고, 행동 제안에서만 자연스럽게 권유형을 쓴다.",
        "syntax": "핵심 답을 먼저 제시하고, 긴 관형절과 명사 나열을 줄인다. 한국어 독자의 질문 흐름에 따라 제목과 문단 순서를 새로 구성한다.",
        "search": "현재 source facts에서 검색 의도를 도출하고, 한국어 검색에서 자연스러운 명사구와 질문형을 문맥에 맞게 사용한다. 키워드를 나열하지 않는다.",
        "avoid": "중국어 어순, 대칭 문장, 원문의 문단 수를 복제하지 않는다. 번역투인 과도한 피동형, '제공합니다' 반복, 부자연스러운 한자어와 전각 문장부호를 피한다.",
    },
}
REBUILD_FINDING_CODES = {
    "AI_TEMPLATE_STYLE",
    "MIRRORED_STRUCTURE",
    "SOURCE_SYNTAX_TRANSFER",
    "NON_NATIVE_SEARCH_INTENT",
}
JA_BOUNDARY_REQUIRED_FIELDS = ("meta_description", "body")
JA_BOUNDARY_CATEGORY_LABELS = {
    "outcome_not_determined": "結果や個人の結末を断定しない",
    "contextual_or_general_interpretation": "一般的な解釈であり個人の結論を代行しない",
    "professional_advice_non_substitution": "財務、法律、投資などの専門助言に代わらない",
}
JA_BOUNDARY_TARGET_PATTERNS = {
    "outcome_not_determined": re.compile(
        r"(結果を(?:保証|断定)しない|結果を断定せず|結果を保証せず|結果を保証したり|"
        r"結果を保証することはでき|結果を保証(?:するもの)?では|"
        r"未来の結果を(?:完全に)?確定することはでき(?:ない|ず)|"
        r"断定(?:でき|し)ない|直接(?:示す|意味する)ものでは|"
        r"決めるわけでは|確定した答え|成功を約束|破産.*直接|"
        r"個人の結果を断定し|個人の結論や結果を断定し)"
    ),
    "contextual_or_general_interpretation": re.compile(
        r"(一般的な(?:理解|解釈|象徴解釈|文化的読み物)|文化的(?:な)?(?:内省|反省|読み物)|"
        r"整理する(?:ための)?(?:補助|手がかり)|象徴解釈として|"
        r"(?:個人の結論|個別の判断|本人に代わって判断)を?(?:代弁|代行)しない|"
        r"本人に代わって判断したりするものでは|重要な決定を代行)"
    ),
    "professional_advice_non_substitution": re.compile(
        r"(専門(?:的な)?(?:財務|法律|投資)?(?:助言|判断|指導)|専門家に確認|"
        r"専門家の(?:助言|判断)|投資.*法律.*助言|財務.*専門|"
        r"専門的な(?:財務|投資|法律).*(?:助言|代わるものでは))"
    ),
}
JA_BOUNDARY_SOURCE_CATEGORY_PATTERNS = {
    "outcome_not_determined": re.compile(
        r"(不能.*(?:下結論|斷定)|不能替(?:個人|對方)?下結論|不保證|"
        r"不代表.*承諾|不作.*預測承諾|不直接等於|無法.*確定|"
        r"請勿將其視為明牌|未來的走向仍取決於個人的具體行動|"
        r"不能承諾復合、成功或最終結果|不用來替你拿確定答案|"
        r"不能替你拿確定答案|不能替你預測必然結果|不能保證結果|"
        r"不能預先承諾結果|^不能$)"
    ),
    "contextual_or_general_interpretation": re.compile(
        r"(通用理解|一般理解|文化(?:與|和)?符號|文化反思|"
        r"文化性反思|不能替個人下結論|自行衡量適用性|"
        r"只用來輔助整理|文化與符號層面的反思|文化反思範疇|"
        r"不能取代完整情境|不能替任何人做重大決定|通用觀察|"
        r"通用描述.*個人|不能代替個人判斷)"
    ),
    "professional_advice_non_substitution": re.compile(
        r"(不構成.*(?:投資|法律).*建議|不作.*財務建議|"
        r"專業(?:財務)?(?:指導|建議)|投資或法律建議|"
        r"經濟決策仍須依賴個人審慎評估)"
    ),
}
JA_BOUNDARY_SOURCE_HEURISTIC_RE = re.compile(
    r"(不能|不得|不會|無法|不保證|限制|避免|禁止|不代表|不構成|"
    r"不作|請勿|自行衡量|通用理解|一般理解|文化反思|専門|助言|"
    r"指導|保証|断定|代弁|代行|約束|明牌|確定|診斷|診断|"
    r"停藥|停薬|醫療|医療)"
)
JA_BOUNDARY_NOT_A_BOUNDARY_REASONS = (
    ("ordinary_content_contrast", re.compile(r"(不能只|不只是|不是.*而是|不是固定|而非|不該成為|不再)")),
    ("ordinary_uncertainty_context", re.compile(r"不確定性")),
    ("ordinary_process_limit", re.compile(r"(先整理事實.*限制與可行選項|避免只憑一時感受做決定|使用限制)")),
)
JA_BOUNDARY_HIGH_RISK_UNRESOLVED_RE = re.compile(
    r"(醫療|医療|診斷|診断|停藥|停薬|專業(?:醫療|法律|投資|財務)?建議|"
    r"専門(?:的な)?(?:医療|法律|投資|財務)?助言)"
)
JA_BOUNDARY_CONSTRAINT_KEYS = {
    "outcome_not_determined": "outcome_not_determined",
    "contextual_or_general_interpretation": "general_interpretation_only",
    "professional_advice_non_substitution": "professional_advice_non_substitution",
}
TRANSLATABLE_FIELDS = {"title", "description", "answer", "tags", "faq", "bodySections"}
TRANSLATION_ARTICLE_FIELDS = {
    "article_id",
    "locale",
    "source_article_id",
    "source_path",
    "source_sha256",
    *TRANSLATABLE_FIELDS,
}
SourceLoader = Callable[[Path, str], dict[str, Any]]


class LocalePlanValidationError(ValueError):
    """標示 provider transport 成功後的 deterministic locale-plan 契約失敗。"""


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_json(payload: object) -> str:
    return compact_json_bytes(payload).decode("utf-8")


def _json_sha256(payload: object) -> str:
    return hashlib.sha256(compact_json_bytes(payload)).hexdigest()


def translation_identity_envelope(article_id: str, lane: str) -> dict[str, object]:
    if not article_id.strip() or lane not in TRANSLATION_IDENTITY_LANES:
        raise ValueError("translation identity envelope is invalid")
    identity = {
        "schema_version": SCHEMA_VERSION,
        "mode": "translate_existing",
        "lane": lane,
        "article_ids": [article_id],
    }
    return {**identity, "digest": _json_sha256(identity)}


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(compact_json_bytes(payload) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def source_sha256(source: dict[str, Any]) -> str:
    return hashlib.sha256(compact_json_bytes(source)).hexdigest()


def _non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _validate_sections(value: object, name: str) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    for section in value:
        if not isinstance(section, dict) or set(section) != {"heading", "paragraphs"}:
            raise ValueError(f"{name} sections require heading and paragraphs")
        _non_empty_string(section.get("heading"), f"{name}.heading")
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            raise ValueError(f"{name}.paragraphs must be a non-empty list")
        for paragraph in paragraphs:
            _non_empty_string(paragraph, f"{name}.paragraph")


def _validate_faq(value: object, name: str) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    for item in value:
        if not isinstance(item, dict) or set(item) != {"question", "answer"}:
            raise ValueError(f"{name} items require question and answer")
        _non_empty_string(item.get("question"), f"{name}.question")
        _non_empty_string(item.get("answer"), f"{name}.answer")


def _validate_source(source: object) -> dict[str, Any]:
    required = {
        "article_id",
        "canonical_path",
        "title",
        "description",
        "answer",
        "tags",
        "faq",
        "bodySections",
    }
    if not isinstance(source, dict) or set(source) != required:
        raise ValueError("translation source fields are strict")
    for field in ["article_id", "canonical_path", "title", "description", "answer"]:
        _non_empty_string(source.get(field), f"source.{field}")
    if not str(source["canonical_path"]).startswith("/articles/"):
        raise ValueError("source canonical path must be an article path")
    if not isinstance(source.get("tags"), list) or not source["tags"]:
        raise ValueError("source.tags must be a non-empty list")
    _validate_faq(source.get("faq"), "source.faq")
    _validate_sections(source.get("bodySections"), "source.bodySections")
    return source


def validate_translation_brief(brief: dict[str, Any]) -> None:
    if set(brief) != TRANSLATION_BRIEF_FIELDS:
        raise ValueError("translation brief fields are strict")
    if brief.get("schema_version") != SCHEMA_VERSION or brief.get("mode") != "translate_existing":
        raise ValueError("translation brief identity is invalid")
    _non_empty_string(brief.get("run_id"), "run_id")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not 1 <= len(articles) <= 5:
        raise ValueError("translation brief must contain 1 to 5 targets")
    translation_ids: set[str] = set()
    for item in articles:
        required = {
            "translation_id",
            "locale",
            "source_article_id",
            "source_path",
            "source_sha256",
            "source",
        }
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("translation brief target fields are strict")
        locale = str(item.get("locale") or "")
        if locale not in SUPPORTED_LOCALES:
            raise ValueError(f"unsupported locale: {locale}")
        source = _validate_source(item.get("source"))
        source_article_id = _non_empty_string(item.get("source_article_id"), "source_article_id")
        translation_id = _non_empty_string(item.get("translation_id"), "translation_id")
        if translation_id != f"{source_article_id}:{locale}":
            raise ValueError("translation id differs from article and locale")
        if translation_id in translation_ids:
            raise ValueError(f"duplicate translation id: {translation_id}")
        translation_ids.add(translation_id)
        if source["article_id"] != source_article_id or source["canonical_path"] != item.get("source_path"):
            raise ValueError("translation source identity differs from target")
        if item.get("source_sha256") != source_sha256(source):
            raise ValueError(f"translation source hash differs for {translation_id}")


def _registered_translation_state_path(run_dir: Path, run_id: str) -> Path | None:
    resolved_run_dir = run_dir.resolve()
    if resolved_run_dir.parent.name != "translation-runs":
        return None
    queue_root = resolved_run_dir.parent.parent
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    return queue_root / "runs" / f"{digest}.json"


def _legacy_rewrite_translation_article_id(brief: dict[str, Any]) -> str:
    articles = brief.get("articles")
    if not (
        isinstance(articles, list)
        and len(articles) == 1
        and isinstance(articles[0], dict)
    ):
        raise ValueError("legacy translation brief identity is invalid")
    return _non_empty_string(
        articles[0].get("source_article_id"),
        "source_article_id",
    )


def _validate_legacy_rewrite_translation_context(
    brief: dict[str, Any],
    run_dir: Path,
    trusted_state: dict[str, Any],
) -> None:
    brief_lane = brief.get("lane")
    if type(brief_lane) is not str or brief_lane != LEGACY_REWRITE_TRANSLATION_LANE:
        raise ValueError("legacy translation brief lane is invalid")
    resolved_run_dir = run_dir.resolve()
    run_id = _non_empty_string(brief.get("run_id"), "run_id")
    article_id = _legacy_rewrite_translation_article_id(brief)
    expected_envelope = translation_identity_envelope(
        article_id,
        LEGACY_REWRITE_TRANSLATION_LANE,
    )
    if (
        not isinstance(trusted_state, dict)
        or trusted_state.get("run_id") != run_id
        or trusted_state.get("run_dir") != str(resolved_run_dir)
        or trusted_state.get("status") not in {"active", "complete", "failed"}
        or trusted_state.get("lane") != LEGACY_REWRITE_TRANSLATION_LANE
        or trusted_state.get("identity_envelope") != expected_envelope
    ):
        raise ValueError("legacy translation brief lane context is invalid")


def _normalize_registered_translation_brief(
    brief: dict[str, Any],
    run_dir: Path,
    *,
    trusted_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    keys = set(brief)
    if keys == TRANSLATION_BRIEF_FIELDS:
        validate_translation_brief(brief)
        return brief
    if keys != TRANSLATION_BRIEF_FIELDS | {"lane"}:
        validate_translation_brief(brief)
        return brief
    run_id = _non_empty_string(brief.get("run_id"), "run_id")
    state = trusted_state
    if state is None:
        state_path = _registered_translation_state_path(run_dir, run_id)
        if state_path is None or not state_path.is_file():
            raise ValueError("legacy translation brief lane context is invalid")
        state = json.loads(state_path.read_text(encoding="utf-8"))
    _validate_legacy_rewrite_translation_context(brief, run_dir, state)
    normalized = {field: brief[field] for field in TRANSLATION_BRIEF_FIELDS}
    validate_translation_brief(normalized)
    return normalized


def _load_registered_translation_brief(run_dir: Path) -> dict[str, Any]:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    if not isinstance(brief, dict):
        raise ValueError("translation brief must be a JSON object")
    return _normalize_registered_translation_brief(brief, run_dir)


def validate_translation_candidate(brief: dict[str, Any], candidate: dict[str, Any]) -> None:
    validate_translation_brief(brief)
    if set(candidate) != {"schema_version", "run_id", "mode", "articles"}:
        raise ValueError("translation candidate fields are strict")
    if (
        candidate.get("schema_version") != SCHEMA_VERSION
        or candidate.get("run_id") != brief["run_id"]
        or candidate.get("mode") != "translate_existing"
    ):
        raise ValueError("translation candidate identity differs from brief")
    articles = candidate.get("articles")
    if not isinstance(articles, list) or len(articles) != len(brief["articles"]):
        raise ValueError("translation candidate target count differs from brief")
    expected = {str(item["translation_id"]): item for item in brief["articles"]}
    if [str(item.get("article_id")) for item in articles if isinstance(item, dict)] != list(expected):
        raise ValueError("translation candidate order differs from brief")
    for article in articles:
        if not isinstance(article, dict) or set(article) != TRANSLATION_ARTICLE_FIELDS:
            raise ValueError("translation article fields are strict")
        translation_id = str(article["article_id"])
        source = expected[translation_id]
        for candidate_field, source_field in [
            ("locale", "locale"),
            ("source_article_id", "source_article_id"),
            ("source_path", "source_path"),
            ("source_sha256", "source_sha256"),
        ]:
            if article[candidate_field] != source[source_field]:
                label = "source hash" if candidate_field == "source_sha256" else candidate_field
                raise ValueError(f"translation {label} differs for {translation_id}")
        for field in ["title", "description", "answer"]:
            _non_empty_string(article.get(field), field)
        if not isinstance(article.get("tags"), list) or not article["tags"]:
            raise ValueError("translation tags must be a non-empty list")
        _validate_faq(article.get("faq"), "translation.faq")
        _validate_sections(article.get("bodySections"), "translation.bodySections")


def _visible_text(article: dict[str, Any]) -> str:
    values = [str(article["title"]), str(article["description"]), str(article["answer"])]
    values.extend(str(tag) for tag in article["tags"])
    values.extend(str(item[key]) for item in article["faq"] for key in ["question", "answer"])
    values.extend(str(section["heading"]) for section in article["bodySections"])
    values.extend(str(paragraph) for section in article["bodySections"] for paragraph in section["paragraphs"])
    return "\n".join(values)


def _ja_body_text(article: dict[str, Any]) -> str:
    return "\n".join(
        str(paragraph)
        for section in article.get("bodySections", [])
        if isinstance(section, dict)
        for paragraph in section.get("paragraphs", [])
    )


def _ja_field_text(article: dict[str, Any], field: str) -> str:
    if field == "meta_description":
        return str(article.get("description") or "")
    if field == "body":
        return _ja_body_text(article)
    raise ValueError(f"unknown JA boundary field: {field}")


def _source_text_fields(source: dict[str, Any]) -> list[tuple[str, str]]:
    fields = [
        ("description", str(source["description"])),
        ("answer", str(source["answer"])),
    ]
    fields.extend(
        (f"faq[{index}].question", str(item["question"]))
        for index, item in enumerate(source["faq"])
    )
    fields.extend(
        (f"faq[{index}].answer", str(item["answer"]))
        for index, item in enumerate(source["faq"])
    )
    fields.extend(
        (
            f"bodySections[{section_index}].paragraphs[{paragraph_index}]",
            str(paragraph),
        )
        for section_index, section in enumerate(source["bodySections"])
        for paragraph_index, paragraph in enumerate(section["paragraphs"])
    )
    return fields


def _ja_source_candidate_clauses(text: str) -> list[str]:
    clauses = []
    for sentence in re.findall(r"[^。！？!?]+[。！？!?]?", text):
        for clause in re.split(r"[，,；;]", sentence):
            normalized = clause.strip(" \t\r\n。！？!?")
            if normalized:
                clauses.append(normalized)
    return clauses


def _ja_boundary_source_categories(text: str) -> list[str]:
    return [
        category
        for category, pattern in JA_BOUNDARY_SOURCE_CATEGORY_PATTERNS.items()
        if pattern.search(text)
    ]


def _ja_boundary_target_categories(text: str) -> set[str]:
    return {
        category
        for category, pattern in JA_BOUNDARY_TARGET_PATTERNS.items()
        if pattern.search(text)
    }


def _ja_boundary_not_a_boundary_reason(text: str) -> str | None:
    for reason_code, pattern in JA_BOUNDARY_NOT_A_BOUNDARY_REASONS:
        if pattern.search(text):
            return reason_code
    return None


def _ja_boundary_high_risk_unresolved(text: str) -> bool:
    return bool(JA_BOUNDARY_HIGH_RISK_UNRESOLVED_RE.search(text))


def _ja_exact_normalized_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\s、，,。！？!?；;：「」『』（）()\[\]]+", "", normalized)


def _ja_constraint_id(
    source_version_digest: str,
    category: str,
    constraint_key: str,
    equivalence_key: str,
) -> str:
    value = f"{source_version_digest}\0{category}\0{constraint_key}\0{equivalence_key}"
    return f"constraint-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _ja_source_span_id(
    source_version_digest: str,
    field_path: str,
    ordinal: int,
) -> str:
    value = f"{source_version_digest}\0{field_path}\0{ordinal}"
    return f"span-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _ja_protected_constraint_view(item: dict[str, Any]) -> dict[str, Any]:
    source_version_digest = str(item["source_sha256"])
    source = item["source"]
    dispositions = []
    constraints_by_id: dict[str, dict[str, Any]] = {}
    preserved_constraint_ids: set[str] = set()

    for field_path, text in _source_text_fields(source):
        for ordinal, source_text in enumerate(_ja_source_candidate_clauses(text), start=1):
            if not JA_BOUNDARY_SOURCE_HEURISTIC_RE.search(source_text):
                continue
            source_span_id = _ja_source_span_id(
                source_version_digest,
                field_path,
                ordinal,
            )
            base = {
                "source_span_id": source_span_id,
                "field_path": field_path,
                "ordinal": ordinal,
                "source_text": source_text,
                "source_digest": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                "provenance": "source",
            }
            categories = _ja_boundary_source_categories(source_text)
            if not categories:
                if _ja_boundary_high_risk_unresolved(source_text):
                    dispositions.append(
                        {
                            **base,
                            "disposition": "UNRESOLVED",
                            "reason_code": "high_risk_boundary_candidate",
                            "constraint_ids": [],
                        }
                    )
                    continue
                reason_code = _ja_boundary_not_a_boundary_reason(source_text)
                if reason_code is not None:
                    dispositions.append(
                        {
                            **base,
                            "disposition": "NOT_A_BOUNDARY",
                            "reason_code": reason_code,
                            "constraint_ids": [],
                        }
                    )
                else:
                    dispositions.append(
                        {
                            **base,
                            "disposition": "UNRESOLVED",
                            "reason_code": "unknown_boundary_candidate",
                            "constraint_ids": [],
                        }
                    )
                continue

            constraint_ids = []
            for category in categories:
                equivalence_key = _ja_exact_normalized_text(source_text)
                constraint_key = f"{JA_BOUNDARY_CONSTRAINT_KEYS[category]}:{equivalence_key}"
                constraint_id = _ja_constraint_id(
                    source_version_digest,
                    category,
                    constraint_key,
                    equivalence_key,
                )
                constraint_ids.append(constraint_id)
                constraint = constraints_by_id.setdefault(
                    constraint_id,
                    {
                        "constraint_id": constraint_id,
                        "constraint_key": constraint_key,
                        "equivalence_key": equivalence_key,
                        "category": category,
                        "category_label": JA_BOUNDARY_CATEGORY_LABELS[category],
                        "source_span_ids": [],
                        "source_texts": [],
                        "required_fields": list(JA_BOUNDARY_REQUIRED_FIELDS),
                        "provenance": "source",
                    },
                )
                if source_span_id not in constraint["source_span_ids"]:
                    constraint["source_span_ids"].append(source_span_id)
                    constraint["source_texts"].append(source_text)

            disposition = (
                "MERGED_DUPLICATE"
                if any(constraint_id in preserved_constraint_ids for constraint_id in constraint_ids)
                else "PRESERVED"
            )
            preserved_constraint_ids.update(constraint_ids)
            dispositions.append(
                {
                    **base,
                    "disposition": disposition,
                    "categories": categories,
                    "constraint_ids": constraint_ids,
                }
            )

    return {
        "protected_source": {
            "source_version_digest": source_version_digest,
            "boundary_candidate_dispositions": dispositions,
        },
        "protected_constraints": sorted(
            constraints_by_id.values(),
            key=lambda constraint: constraint["constraint_id"],
        ),
    }


def _ja_source_fact_projection(text: str, dispositions: list[dict[str, Any]]) -> str:
    protected_texts = {
        str(disposition["source_text"])
        for disposition in dispositions
        if disposition["disposition"] in {"PRESERVED", "MERGED_DUPLICATE"}
        and _ja_source_clause_is_pure_protected(str(disposition["source_text"]))
    }
    projected_sentences = []
    for sentence in re.findall(r"[^。！？!?]+[。！？!?]?", text):
        suffix = sentence[-1] if re.search(r"[。！？!?]$", sentence) else ""
        body = sentence[:-1] if suffix else sentence
        clauses = [
            clause.strip()
            for clause in re.split(r"[，,；;]", body)
            if clause.strip()
        ]
        kept = [
            clause
            for clause in clauses
            if clause.strip(" \t\r\n。！？!?") not in protected_texts
        ]
        if not kept:
            continue
        if kept[0].startswith(("旨在", "這點", "未來的走向")):
            projected_sentences.append(sentence.strip())
        else:
            projected_sentences.append("，".join(kept) + suffix)
    return "".join(projected_sentences).strip()


def _ja_source_clause_is_pure_protected(text: str) -> bool:
    if re.search(r"(而是|提醒我們檢視|映照|藉由|旨在|學習接受|提供了一種|具體問題)", text):
        return False
    return bool(
        re.search(
            r"(通用理解|一般理解|不能替|不代表|不作|不構成|"
            r"財務建議|投資或法律建議|專業財務指導|請讀者|請勿|"
            r"未來的走向仍取決於|任何預測工具|這點在解讀|"
            r"經濟決策仍須依賴|不能承諾|不用來替你拿確定答案)",
            text,
        )
    )


def _ja_boundary_contracts_for_brief(brief: dict[str, Any]) -> dict[str, Any]:
    validate_translation_brief(brief)
    articles = []
    for index, item in enumerate(brief["articles"]):
        if item["locale"] != "ja":
            continue
        view = _ja_protected_constraint_view(item)
        articles.append(
            {
                "slot": f"article-{index + 1:02d}",
                "article_id": item["translation_id"],
                "locale": "ja",
                "protected_constraints": view["protected_constraints"],
                "boundary_candidate_dispositions": view["protected_source"][
                    "boundary_candidate_dispositions"
                ],
            }
        )
    return {"articles": articles}


def _ja_repeated_boundary_locations(article: dict[str, Any]) -> list[str]:
    body = _ja_body_text(article)
    if _ja_repeated_boundary_span_evidence(body):
        return ["body"]
    return []


def _ja_repeated_boundary_span_evidence(text: str) -> list[str]:
    spans: dict[str, int] = {}
    for sentence in re.findall(r"[^。！？!?]+[。！？!?]?", text):
        if not _ja_boundary_target_categories(sentence):
            continue
        normalized = _ja_exact_normalized_text(sentence)
        if len(normalized) >= 24:
            spans[normalized] = spans.get(normalized, 0) + 1
        window_size = 24
        if len(normalized) >= window_size:
            for index in range(len(normalized) - window_size + 1):
                window = normalized[index:index + window_size]
                spans[window] = spans.get(window, 0) + 1
    return [
        span
        for span, count in spans.items()
        if count >= 3
    ]


def _ja_boundary_findings(
    brief: dict[str, Any],
    article: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    contract = next(
        (
            item
            for item in _ja_boundary_contracts_for_brief(brief)["articles"]
            if item["article_id"] == article.get("article_id")
        ),
        None,
    )
    if contract is None:
        return []

    unresolved = [
        item
        for item in contract["boundary_candidate_dispositions"]
        if item["disposition"] == "UNRESOLVED"
    ]
    if unresolved:
        return [
            {
                "article_id": str(article["article_id"]),
                "code": "UNRESOLVED_BOUNDARY_CANDIDATE",
                "message": "JA protected source constraint has unresolved boundary candidates",
                "source_span_ids": [item["source_span_id"] for item in unresolved],
                "reason_codes": [item["reason_code"] for item in unresolved],
            }
        ]

    repeated_locations = _ja_repeated_boundary_locations(article)
    if repeated_locations:
        return [
            {
                "article_id": str(article["article_id"]),
                "code": "BOUNDARY_BOILERPLATE_REPEATED",
                "message": (
                    "JA protected boundary meaning is present but repeated as boilerplate "
                    f"in {', '.join(repeated_locations)}"
                ),
                "repeated_locations": repeated_locations,
            }
        ]

    required_categories = sorted(
        {
            constraint["category"]
            for constraint in contract["protected_constraints"]
        }
    )
    present_by_field = {
        field: _ja_boundary_target_categories(_ja_field_text(article, field))
        for field in JA_BOUNDARY_REQUIRED_FIELDS
    }
    present_categories = sorted(_ja_boundary_target_categories(_visible_text(article)))
    missing_categories = [
        category
        for category in required_categories
        if category not in present_categories
    ]
    missing_fields = [
        field
        for field in JA_BOUNDARY_REQUIRED_FIELDS
        if any(category not in present_by_field[field] for category in required_categories)
    ]
    if not missing_categories and not missing_fields:
        return []
    return [
        {
            "article_id": str(article["article_id"]),
            "code": "BOUNDARY_MEANING_MISSING",
            "message": (
                "JA protected boundary meaning is missing from "
                f"{', '.join(missing_fields)}"
            ),
            "missing_fields": missing_fields,
            "missing_categories": missing_categories,
            "present_categories": present_categories,
            "reasons": [
                {
                    "category": category,
                    "reason": "omission",
                    "missing_fields": [
                        field
                        for field, categories in present_by_field.items()
                        if category not in categories
                    ],
                }
                for category in missing_categories
            ],
        }
    ]


def _matches_target_language(locale: str, text: str) -> bool:
    if locale == "en":
        latin = len(re.findall(r"[A-Za-z]", text))
        cjk = len(re.findall(r"[\u3400-\u9fff]", text))
        return latin >= 80 and cjk <= max(5, latin // 25)
    if locale == "ja":
        kana = len(re.findall(r"[\u3040-\u30ff]", text))
        hangul = len(re.findall(r"[\uac00-\ud7af]", text))
        return kana >= 20 and hangul == 0
    hangul = len(re.findall(r"[\uac00-\ud7af]", text))
    kana = len(re.findall(r"[\u3040-\u30ff]", text))
    return hangul >= 30 and kana == 0


def _metadata_matches_target_language(locale: str, text: str) -> bool:
    if locale == "en":
        return len(re.findall(r"[A-Za-z]", text)) >= 5 and not re.search(r"[\u3040-\u30ff\uac00-\ud7af]", text)
    if locale == "ja":
        return len(re.findall(r"[\u3040-\u30ff]", text)) >= 2 and not re.search(r"[\uac00-\ud7af]", text)
    return len(re.findall(r"[\uac00-\ud7af]", text)) >= 4 and not re.search(r"[\u3040-\u30ff]", text)


def _japanese_tag_matches_target_language(tag: str, source: dict[str, Any]) -> bool:
    normalized = tag.strip()
    if normalized in {str(source_tag).strip() for source_tag in source["tags"]}:
        return (
            normalized in _source_ascii_authorities(source)
            or _ascii_is_name_acronym_or_number(normalized)
        )
    if re.search(r"(?:人際|[與斷體國學關氣覺實應發讓對從將會這們裡麼戀])", normalized):
        return False
    return _plan_matches_target_language("ja", normalized)


def translation_findings(brief: dict[str, Any], articles: list[dict[str, Any]]) -> list[dict[str, str]]:
    expected = {str(item["translation_id"]): item for item in brief["articles"]}
    findings: list[dict[str, str]] = []
    for article in articles:
        translation_id = str(article.get("article_id") or "")
        source = expected.get(translation_id)
        if source is None:
            findings.append({"article_id": translation_id, "code": "unknown_target", "message": "翻譯目標不在 brief"})
            continue
        source_content = source["source"]
        if not 4 <= len(article["bodySections"]) <= 5:
            findings.append(
                {
                    "article_id": translation_id,
                    "code": "localized_structure",
                    "message": "母語重寫正文必須有 4–5 個依目標語言讀者重新規劃的 H2",
                }
            )
        source_shape = (
            len(source_content["bodySections"]),
            tuple(len(section["paragraphs"]) for section in source_content["bodySections"]),
        )
        localized_shape = (
            len(article["bodySections"]),
            tuple(len(section["paragraphs"]) for section in article["bodySections"]),
        )
        if localized_shape == source_shape:
            findings.append(
                {
                    "article_id": translation_id,
                    "code": "structural_mirroring",
                    "message": "文章沿用中文 H2 與段落骨架；必須依目標語言讀者的搜尋與閱讀順序重新編排",
                }
            )
        locale = str(article["locale"])
        if (
            not _matches_target_language(locale, _visible_text(article))
            or not _metadata_matches_target_language(locale, str(article["title"]))
            or not _metadata_matches_target_language(locale, str(article["description"]))
        ):
            findings.append({"article_id": translation_id, "code": "target_language", "message": "可見文字不是指定目標語言"})
        if locale == "ja" and any(
            not _japanese_tag_matches_target_language(str(tag), source_content)
            for tag in article["tags"]
        ):
            findings.append(
                {
                    "article_id": translation_id,
                    "code": "target_language_tags",
                    "message": "日文 metadata tags 含繁中殘留或沿用來源語言",
                }
            )
        if article["title"] == source_content["title"] or article["description"] == source_content["description"]:
            findings.append({"article_id": translation_id, "code": "untranslated_metadata", "message": "標題或描述仍與原文相同"})
        if locale == "ja":
            findings.extend(_ja_boundary_findings(brief, article, source_content))
    return findings


def load_source_article(repo_root: Path, article_id: str) -> dict[str, Any]:
    script = f"""
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
const article = listArticleRecords().find((item) => item.id === {json.dumps(article_id)});
if (!article) throw new Error("article not found");
const canonicalPath = getArticlePath(article);
const content = buildArticleContent(canonicalPath, "https://www.mysticpantheon.com");
console.log(JSON.stringify({{
  article_id: article.id,
  canonical_path: canonicalPath,
  title: content.title,
  description: content.description,
  answer: content.answer,
  tags: content.displayTags,
  faq: content.faq,
  bodySections: content.bodySections,
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return _validate_source(json.loads(result.stdout))


def prepare_translation_run(
    repo_root: Path,
    run_id: str,
    article_id: str,
    locales: list[str],
    output_root: Path,
    *,
    source_loader: SourceLoader = load_source_article,
) -> Path:
    if len(locales) != len(set(locales)) or not locales:
        raise ValueError("translation locales must be non-empty and unique")
    source = source_loader(repo_root, article_id)
    digest = source_sha256(source)
    brief = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"{article_id}:{locale}",
                "locale": locale,
                "source_article_id": article_id,
                "source_path": source["canonical_path"],
                "source_sha256": digest,
                "source": source,
            }
            for locale in locales
        ],
    }
    validate_translation_brief(brief)
    path = output_root / run_id / "brief.json"
    pipeline.write_json(path, brief)
    return path


def translation_run_id(source_run_id: str, article_id: str, locale: str) -> str:
    """回傳既有 queue contract 唯一且可重算的 translation run ID。"""
    if not source_run_id.strip() or not article_id.strip() or locale not in SUPPORTED_LOCALES:
        raise ValueError("translation run identity is invalid")
    identity = f"{source_run_id}\0{article_id}\0{locale}"
    return f"auto-i18n-{locale}-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"


def enqueue_article_translations(
    repo_root: Path,
    queue_root: Path,
    *,
    source_run_id: str,
    article_id: str,
    locales: list[str] | None = None,
    lane: str,
    source_loader: SourceLoader = load_source_article,
) -> list[dict[str, str]]:
    """為已發布新文或成功改寫舊文建立英、日、韓三個互不阻塞的翻譯 run。"""
    if not source_run_id.strip() or not article_id.strip():
        raise ValueError("source run id and article id must be non-empty")
    selected_locales = locales if locales is not None else ["en", "ja", "ko"]
    if (
        not selected_locales
        or len(selected_locales) != len(set(selected_locales))
        or any(locale not in SUPPORTED_LOCALES for locale in selected_locales)
    ):
        raise ValueError("translation locales must be non-empty, unique, and supported")
    identity_envelope = translation_identity_envelope(article_id, lane)
    queue_root = queue_root.resolve()
    records: list[dict[str, str]] = []
    for locale in selected_locales:
        run_id = translation_run_id(source_run_id, article_id, locale)
        run_dir = queue_root / "translation-runs" / run_id
        state_path = queue_root / "runs" / f"{hashlib.sha256(run_id.encode('utf-8')).hexdigest()[:24]}.json"
        resolved_run_dir = run_dir.resolve()
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("run_id") != run_id or state.get("run_dir") != str(resolved_run_dir):
                raise ValueError("translation run identity collision")
            brief_path = run_dir / "brief.json"
            if not brief_path.is_file():
                raise ValueError("registered translation run brief is missing")
            existing_brief = json.loads(brief_path.read_text(encoding="utf-8"))
            existing_brief = _normalize_registered_translation_brief(
                existing_brief,
                run_dir,
                trusted_state=state,
            )
            current_source = source_loader(repo_root, article_id)
            if existing_brief["articles"][0]["source_sha256"] != source_sha256(current_source):
                raise ValueError("registered translation run source drift")
            if (
                state.get("lane") != lane
                or state.get("identity_envelope") != identity_envelope
            ):
                raise ValueError("registered translation run identity envelope drift")
        else:
            prepare_translation_run(
                repo_root,
                run_id,
                article_id,
                [locale],
                queue_root / "translation-runs",
                source_loader=source_loader,
            )
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            _atomic_write_json(
                state_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_id,
                    "run_dir": str(resolved_run_dir),
                    "status": "active",
                    "lane": lane,
                    "identity_envelope": identity_envelope,
                    "registered_at": now,
                    "updated_at": now,
                },
            )
        records.append({"run_id": run_id, "locale": locale, "run_dir": str(resolved_run_dir)})
    return records


def enqueue_translation_replacement(
    repo_root: Path,
    queue_root: Path,
    *,
    terminal_state: dict[str, Any],
    recovery_reason: str,
    source_loader: SourceLoader = load_source_article,
) -> dict[str, str]:
    """為 eligible terminal translation run 建立一次、可重入的 replacement。"""
    if recovery_reason not in TRANSLATION_REPLACEMENT_REASONS:
        raise ValueError("translation replacement reason is not allowed")
    if terminal_state.get("status") != "failed":
        raise ValueError("translation replacement requires a failed terminal run")
    base_run_id = str(terminal_state.get("run_id") or "")
    if not base_run_id or base_run_id.endswith("-replacement-01"):
        raise ValueError("translation replacement lineage is exhausted")
    queue_root = queue_root.resolve()
    base_run_dir = (queue_root / "translation-runs" / base_run_id).resolve()
    if terminal_state.get("run_dir") != str(base_run_dir):
        raise ValueError("translation replacement base run identity differs")
    base_brief_path = base_run_dir / "brief.json"
    if not base_brief_path.is_file():
        raise ValueError("translation replacement base brief is missing")
    base_brief = json.loads(base_brief_path.read_text(encoding="utf-8"))
    base_brief = _normalize_registered_translation_brief(
        base_brief,
        base_run_dir,
        trusted_state=terminal_state,
    )
    if base_brief.get("run_id") != base_run_id:
        raise ValueError("translation replacement base brief identity differs")
    for article in base_brief["articles"]:
        current_source = source_loader(repo_root, str(article["source_article_id"]))
        if source_sha256(current_source) != article["source_sha256"]:
            raise ValueError("translation replacement source drift")

    replacement_run_id = f"{base_run_id}-replacement-01"
    replacement_run_dir = (
        queue_root / "translation-runs" / replacement_run_id
    ).resolve()
    replacement_state_path = (
        queue_root
        / "runs"
        / f"{hashlib.sha256(replacement_run_id.encode('utf-8')).hexdigest()[:24]}.json"
    )
    replacement_brief = {**base_brief, "run_id": replacement_run_id}
    validate_translation_brief(replacement_brief)
    replacement_brief_path = replacement_run_dir / "brief.json"
    if replacement_brief_path.exists():
        existing_brief = json.loads(
            replacement_brief_path.read_text(encoding="utf-8")
        )
        if existing_brief != replacement_brief:
            raise ValueError("translation replacement brief collision")
    else:
        _atomic_write_json(replacement_brief_path, replacement_brief)

    if replacement_state_path.exists():
        replacement_state = json.loads(
            replacement_state_path.read_text(encoding="utf-8")
        )
        expected_identity = {
            "run_id": replacement_run_id,
            "run_dir": str(replacement_run_dir),
            "replacement_of": base_run_id,
            "replacement_reason": recovery_reason,
        }
        if any(
            replacement_state.get(field) != value
            for field, value in expected_identity.items()
        ):
            raise ValueError("translation replacement state collision")
    else:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        replacement_state = {
            "schema_version": SCHEMA_VERSION,
            "run_id": replacement_run_id,
            "run_dir": str(replacement_run_dir),
            "status": "active",
            "registered_at": now,
            "updated_at": now,
            "replacement_of": base_run_id,
            "replacement_reason": recovery_reason,
        }
        _atomic_write_json(replacement_state_path, replacement_state)
    return {
        "run_id": replacement_run_id,
        "run_dir": str(replacement_run_dir),
        "state_path": str(replacement_state_path),
    }


def _source_fact_package(brief: dict[str, Any]) -> dict[str, Any]:
    """將來源結構攤平成可追溯 facts，避免 Writer 把來源 H2 當成 outline。"""
    validate_translation_brief(brief)
    articles = []
    safety_pattern = re.compile(
        r"(不能|不得|不會|無法|不保證|限制|避免|禁止|保証しない|できません|"
        r"보장하지|할 수 없|제한)"
    )
    for index, item in enumerate(brief["articles"]):
        source = item["source"]
        protected_view = (
            _ja_protected_constraint_view(item)
            if item["locale"] == "ja"
            else None
        )
        dispositions_by_field: dict[str, list[dict[str, Any]]] = {}
        if protected_view is not None:
            for disposition in protected_view["protected_source"][
                "boundary_candidate_dispositions"
            ]:
                dispositions_by_field.setdefault(
                    str(disposition["field_path"]),
                    [],
                ).append(disposition)
        if item["locale"] == "ja":
            texts = [
                (field_path, text)
                for field_path, text in _source_text_fields(source)
                if not field_path.endswith(".question")
            ]
        else:
            texts = [
                ("description", str(source["description"])),
                ("answer", str(source["answer"])),
                *[
                    (f"faq[{index}]", f"{faq['question']} {faq['answer']}")
                    for index, faq in enumerate(source["faq"])
                ],
                *[
                    (
                        f"bodySections[{section_index}].paragraphs[{paragraph_index}]",
                        str(paragraph),
                    )
                    for section_index, section in enumerate(source["bodySections"])
                    for paragraph_index, paragraph in enumerate(section["paragraphs"])
                ],
            ]
        facts = []
        seen: set[str] = set()
        for field_path, text in texts:
            normalized = text.strip()
            if item["locale"] == "ja":
                normalized = _ja_source_fact_projection(
                    normalized,
                    dispositions_by_field.get(field_path, []),
                )
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unresolved = any(
                disposition["disposition"] == "UNRESOLVED"
                for disposition in dispositions_by_field.get(field_path, [])
            )
            facts.append(
                {
                    "fact_id": f"fact-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:12]}",
                    "text": normalized,
                    "safety_boundary": (
                        unresolved
                        if item["locale"] == "ja"
                        else bool(safety_pattern.search(normalized))
                    ),
                }
            )
        facts.sort(key=lambda fact: fact["fact_id"])
        article = {
            "slot": f"article-{index + 1:02d}",
            "locale": item["locale"],
            "source_sha256": item["source_sha256"],
            "topic_cues": {
                "title": source["title"],
                "tags": source["tags"],
            },
            "facts": facts,
        }
        if protected_view is not None:
            article.update(protected_view)
        articles.append(article)
    return {"articles": articles}


def _uses_request_local_source_refs(
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
) -> bool:
    """JA continuation planning 不讓 provider-facing payload 承載 durable ids。"""
    return (
        prior_plan is not None
        and bool(brief.get("articles"))
        and all(str(item.get("locale")) == "ja" for item in brief["articles"])
    )


def _request_local_source_ref_maps(
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
) -> dict[str, dict[str, str]]:
    if not _uses_request_local_source_refs(brief, prior_plan):
        return {}
    maps: dict[str, dict[str, str]] = {}
    for article in _source_fact_package(brief)["articles"]:
        maps[str(article["slot"])] = {
            f"source_ref_{index + 1:02d}": str(fact["fact_id"])
            for index, fact in enumerate(article["facts"])
        }
    return maps


def _source_ref_maps_from_artifact(
    payload: object,
    *,
    generation: int,
) -> dict[str, dict[str, str]]:
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "generation", "articles"}
        or payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("generation") != generation
        or not isinstance(payload.get("articles"), list)
    ):
        raise ValueError("source ref map identity is invalid")
    maps: dict[str, dict[str, str]] = {}
    for article in payload["articles"]:
        if (
            not isinstance(article, dict)
            or set(article) != {"slot", "refs"}
            or not isinstance(article.get("slot"), str)
            or not isinstance(article.get("refs"), list)
        ):
            raise ValueError("source ref map article fields are strict")
        refs: dict[str, str] = {}
        for item in article["refs"]:
            if (
                not isinstance(item, dict)
                or set(item) != {"source_ref", "source_fact_id"}
                or not isinstance(item.get("source_ref"), str)
                or not isinstance(item.get("source_fact_id"), str)
                or not re.fullmatch(r"source_ref_\d{2}", item["source_ref"])
            ):
                raise ValueError("source ref map refs are strict")
            if item["source_ref"] in refs:
                raise ValueError("source ref map duplicate refs")
            refs[item["source_ref"]] = item["source_fact_id"]
        if article["slot"] in maps:
            raise ValueError("source ref map duplicate article slots")
        maps[article["slot"]] = refs
    return maps


def _source_ref_map_artifact(
    maps: dict[str, dict[str, str]],
    *,
    generation: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generation": generation,
        "articles": [
            {
                "slot": slot,
                "refs": [
                    {"source_ref": ref, "source_fact_id": fact_id}
                    for ref, fact_id in refs.items()
                ],
            }
            for slot, refs in maps.items()
        ],
    }


def _validate_source_ref_maps_against_current_package(
    brief: dict[str, Any],
    maps: dict[str, dict[str, str]],
) -> None:
    fact_articles = _source_fact_package(brief)["articles"]
    expected_slots = [str(article["slot"]) for article in fact_articles]
    if set(maps) != set(expected_slots):
        raise ValueError("source ref map slots differ from current source package")
    for article in fact_articles:
        slot = str(article["slot"])
        expected_refs = [
            f"source_ref_{index + 1:02d}"
            for index, _fact in enumerate(article["facts"])
        ]
        current_fact_ids = [str(fact["fact_id"]) for fact in article["facts"]]
        refs = maps[slot]
        if list(refs) != expected_refs:
            raise ValueError("source ref map refs differ from current source package")
        persisted_fact_ids = list(refs.values())
        if persisted_fact_ids != current_fact_ids:
            raise ValueError("source ref map current fact coverage differs")


def _load_or_create_source_ref_maps(
    path: Path,
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    *,
    generation: int,
    external_plan_path: Path,
) -> dict[str, dict[str, str]]:
    if not _uses_request_local_source_refs(brief, prior_plan):
        return {}
    if path.is_file():
        maps = _source_ref_maps_from_artifact(
            json.loads(path.read_text(encoding="utf-8")),
            generation=generation,
        )
        _validate_source_ref_maps_against_current_package(brief, maps)
        return maps
    if external_plan_path.is_file():
        raise ValueError("source ref map missing for persisted external locale plan")
    maps = _request_local_source_ref_maps(brief, prior_plan)
    _validate_source_ref_maps_against_current_package(brief, maps)
    _atomic_write_json(path, _source_ref_map_artifact(maps, generation=generation))
    return maps


def _stable_legacy_source_provenance(mappings: object) -> bool:
    if not isinstance(mappings, list) or not mappings:
        return False
    return all(
        isinstance(mapping, dict)
        and isinstance(mapping.get("source_span_id"), str)
        and isinstance(mapping.get("source_digest"), str)
        for mapping in mappings
    )


def _legacy_plan_authority(
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    source_ref_maps: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    if not source_ref_maps:
        return {}
    prior_by_slot = {
        str(item.get("slot")): item
        for item in (prior_plan or {}).get("articles", [])
        if isinstance(item, dict)
    }
    authority: dict[str, dict[str, Any]] = {}
    fact_articles = _source_fact_package(brief)["articles"]
    for article in fact_articles:
        slot = str(article["slot"])
        prior = prior_by_slot.get(slot, {})
        mappings = prior.get("coverage_mapping", [])
        legacy_ids = [
            str(mapping.get("source_fact_id"))
            for mapping in mappings
            if isinstance(mapping, dict) and mapping.get("source_fact_id") is not None
        ]
        current_ids = [str(fact["fact_id"]) for fact in article["facts"]]
        counts = Counter(legacy_ids)
        duplicate_count = sum(1 for count in counts.values() if count > 1)
        stale_count = sum(1 for fact_id in counts if fact_id not in current_ids)
        missing_count = sum(1 for fact_id in current_ids if fact_id not in counts)
        has_stable_provenance = _stable_legacy_source_provenance(mappings)
        invalidated = (
            (duplicate_count > 0 or stale_count > 0 or missing_count > 0)
            and not has_stable_provenance
        )
        outline = prior.get("ordered_h2_outline", [])
        section_hints = (
            [
                {
                    "h2_slot": f"h2-{index + 1}",
                    "title": str(heading),
                }
                for index, heading in enumerate(outline)
            ]
            if isinstance(outline, list)
            else []
        )
        payload: dict[str, Any] = {
            "slot": slot,
            "legacy_mapping_status": (
                "INVALIDATED"
                if invalidated
                else (
                    "RETAINED_SAME_DOMAIN"
                    if not stale_count and not missing_count and not duplicate_count
                    else "UNUSABLE_WITH_STABLE_PROVENANCE"
                )
            ),
            "legacy_id_counts": {
                "returned": len(legacy_ids),
                "stale": stale_count,
                "missing": missing_count,
                "duplicates": duplicate_count,
            },
            "stable_source_provenance": has_stable_provenance,
            "non_authoritative_hints": {
                "article_angle": str(prior.get("article_angle", "")),
                "sections": section_hints,
            },
        }
        if payload["legacy_mapping_status"] == "RETAINED_SAME_DOMAIN":
            fact_to_ref = {fact_id: ref for ref, fact_id in source_ref_maps[slot].items()}
            heading_slots = (
                {
                    str(heading): f"h2-{index + 1}"
                    for index, heading in enumerate(outline)
                }
                if isinstance(outline, list)
                else {}
            )
            payload["prior_ref_to_h2_slot"] = [
                {
                    "source_ref": fact_to_ref[str(mapping["source_fact_id"])],
                    "planned_h2_slot": heading_slots[str(mapping["planned_h2"])],
                }
                for mapping in mappings
                if isinstance(mapping, dict)
                and str(mapping.get("source_fact_id")) in fact_to_ref
                and str(mapping.get("planned_h2")) in heading_slots
            ]
        authority[slot] = payload
    return authority


def _strip_provider_identity(value: Any) -> Any:
    identity_keys = {
        "fact_id",
        "source_fact_id",
        "constraint_id",
        "constraint_ids",
        "source_span_id",
        "source_span_ids",
        "source_digest",
        "source_sha256",
        "source_version_digest",
        "digest",
    }
    if isinstance(value, dict):
        return {
            str(key): _strip_provider_identity(item)
            for key, item in value.items()
            if key not in identity_keys
        }
    if isinstance(value, list):
        return [_strip_provider_identity(item) for item in value]
    return value


def _source_fact_package_for_prompt(
    brief: dict[str, Any],
    source_ref_maps: dict[str, dict[str, str]],
) -> dict[str, Any]:
    package = copy.deepcopy(_source_fact_package(brief))
    if not source_ref_maps:
        return package
    for article in package["articles"]:
        slot = str(article["slot"])
        refs = source_ref_maps.get(slot)
        if not refs:
            continue
        fact_to_ref = {fact_id: ref for ref, fact_id in refs.items()}
        article["facts"] = [
            {
                "source_ref": fact_to_ref[str(fact["fact_id"])],
                "text": fact["text"],
            }
            for fact in article["facts"]
        ]
        sanitized = _strip_provider_identity(article)
        article.clear()
        article.update(sanitized)
    return package


def _locale_plan_for_prompt(
    plan_item: dict[str, Any],
    source_ref_map: dict[str, str] | None,
) -> dict[str, Any]:
    item = copy.deepcopy(plan_item)
    if not source_ref_map:
        return item
    fact_to_ref = {fact_id: ref for ref, fact_id in source_ref_map.items()}
    item.pop("source_sha256", None)
    item["coverage_mapping"] = [
        {
            "source_ref": fact_to_ref[str(mapping["source_fact_id"])],
            "planned_h2": mapping["planned_h2"],
            "coverage_note": mapping["coverage_note"],
            "safety_boundary": mapping["safety_boundary"],
        }
        for mapping in item.get("coverage_mapping", [])
        if str(mapping.get("source_fact_id")) in fact_to_ref
    ]
    return item


def _source_structure_to_avoid(brief: dict[str, Any]) -> dict[str, Any]:
    return {
        "articles": [
            {
                "slot": f"article-{index + 1:02d}",
                "source_h2_order": [
                    section["heading"]
                    for section in item["source"]["bodySections"]
                ],
                "source_section_count": len(item["source"]["bodySections"]),
                "source_paragraph_counts": [
                    len(section["paragraphs"])
                    for section in item["source"]["bodySections"]
                ],
            }
            for index, item in enumerate(brief["articles"])
        ]
    }


def _external_locale_plan_schema(
    brief: dict[str, Any],
    *,
    prior_plan: dict[str, Any] | None = None,
    source_ref_maps: dict[str, dict[str, str]] | None = None,
    include_provider_safety_boundary: bool = False,
) -> dict[str, Any]:
    validate_translation_brief(brief)
    fact_articles = _source_fact_package(brief)["articles"]
    fact_counts = [len(item["facts"]) for item in fact_articles]
    if source_ref_maps is None:
        source_ref_maps = _request_local_source_ref_maps(brief, prior_plan)
    source_refs = [
        ref
        for article in fact_articles
        for ref in source_ref_maps.get(str(article["slot"]), {})
    ]
    source_fact_ids = list(
        dict.fromkeys(
            str(fact["fact_id"])
            for item in fact_articles
            for fact in item["facts"]
        )
    )
    target_count = len(brief["articles"])
    coverage_identity_field = "source_ref" if source_ref_maps else "source_fact_id"
    coverage = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            coverage_identity_field: {
                "type": "string",
                "enum": source_refs if source_ref_maps else source_fact_ids,
            },
            "planned_h2_slot": {
                "type": "string",
                "enum": ["h2-1", "h2-2", "h2-3", "h2-4"],
            },
            "coverage_note": {"type": "string"},
        },
        "required": [
            coverage_identity_field,
            "planned_h2_slot",
            "coverage_note",
        ],
    }
    if include_provider_safety_boundary:
        coverage["properties"]["safety_boundary"] = {"type": "boolean"}
        coverage["required"].append("safety_boundary")
    item_properties = {
        "slot": {
            "type": "string",
            "enum": [
                f"article-{index + 1:02d}"
                for index in range(target_count)
            ],
        },
        "locale": {
            "type": "string",
            "enum": list(
                dict.fromkeys(
                    str(target["locale"])
                    for target in brief["articles"]
                )
            ),
        },
        "native_search_intent": {"type": "string"},
        "native_query_phrasings": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "article_angle": {"type": "string"},
        "ordered_h2_outline": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 4,
            "maxItems": 4,
        },
        "coverage_mapping": {
            "type": "array",
            "items": coverage,
            "minItems": min(fact_counts),
            "maxItems": max(fact_counts),
        },
        "source_structure_not_copied": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "rebuild_outline": {"type": "boolean"},
    }
    if not source_ref_maps:
        item_properties["source_sha256"] = {
            "type": "string",
            "enum": list(
                dict.fromkeys(
                    str(target["source_sha256"])
                    for target in brief["articles"]
                )
            ),
        }
    item_required = [
        "slot",
        "locale",
        "native_search_intent",
        "native_query_phrasings",
        "article_angle",
        "ordered_h2_outline",
        "coverage_mapping",
        "source_structure_not_copied",
        "rebuild_outline",
    ]
    if not source_ref_maps:
        item_required.insert(2, "source_sha256")
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": item_properties,
        "required": item_required,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "articles": {
                "type": "array",
                "items": item,
                "minItems": target_count,
                "maxItems": target_count,
            }
        },
        "required": ["articles"],
    }


def _normalized_outline(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(re.sub(r"\W+", "", str(item)).casefold() for item in value)


def _outline_topology(item: dict[str, Any]) -> tuple[frozenset[str], ...]:
    outline = item.get("ordered_h2_outline")
    mappings = item.get("coverage_mapping")
    if not isinstance(outline, list) or not isinstance(mappings, list):
        return ()
    return tuple(
        frozenset(
            str(mapping.get("source_fact_id"))
            for mapping in mappings
            if isinstance(mapping, dict) and mapping.get("planned_h2") == heading
        )
        for heading in outline
    )


def _ascii_is_name_acronym_or_number(text: str) -> bool:
    token_pattern = (
        r"(?:\d+(?:[.,]\d+)?%?|[A-Za-z0-9]+(?:[-+.][A-Za-z0-9]+)*%?)"
    )
    if re.fullmatch(rf"{token_pattern}(?: {token_pattern})*", text) is None:
        return False
    tokens = text.split(" ")

    def is_number(token: str) -> bool:
        return re.fullmatch(r"\d+(?:[.,]\d+)?%?", token) is not None

    def is_literal_authority(token: str) -> bool:
        return token in {"OpenAI", "API"}

    def is_model_code(token: str) -> bool:
        return (
            len(token) <= 24
            and re.fullmatch(r"[A-Za-z0-9]+(?:[-+][A-Za-z0-9]+)*", token)
            is not None
            and any(character.isalpha() for character in token)
            and any(character.isdigit() for character in token)
            and (
                any(character.isupper() for character in token)
                or "-" in token
                or "+" in token
            )
        )

    if len(tokens) == 1:
        return any(
            predicate(tokens[0])
            for predicate in (is_number, is_literal_authority, is_model_code)
        )
    if len(tokens) > 3:
        return False
    return (
        is_literal_authority(tokens[0])
        and is_model_code(tokens[1])
        and all(is_number(token) for token in tokens[2:])
    ) or (
        is_model_code(tokens[0])
        and all(is_number(token) for token in tokens[1:])
    )


def _source_ascii_authorities(source: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        re.findall(
            r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,15}(?![A-Za-z0-9])",
            _visible_text(source),
        )
    )


def _plan_matches_target_language(
    locale: str,
    text: str,
    *,
    source_ascii_authorities: frozenset[str] = frozenset(),
) -> bool:
    latin = len(re.findall(r"[A-Za-z]", text))
    han = len(re.findall(r"[\u3400-\u9fff]", text))
    kana = len(re.findall(r"[\u3040-\u30ff]", text))
    hangul = len(re.findall(r"[\uac00-\ud7af]", text))
    if locale == "en":
        return (
            (latin > 0 and latin >= 2 * (han + kana + hangul))
            or (latin == 0 and han + kana + hangul == 0 and bool(re.search(r"\d", text)))
        )
    ascii_tokens = re.findall(r"[A-Za-z0-9]+(?:[-+.][A-Za-z0-9]+)*%?", text)
    latin_authority = latin - sum(
        sum(character.isalpha() for character in token)
        for token in ascii_tokens
        if (
            _ascii_is_name_acronym_or_number(token)
            or token in source_ascii_authorities
        )
    )
    if locale == "ja":
        traditional_chinese = bool(
            re.search(r"[與斷體國學關氣覺實應發讓對從將會這們裡麼]", text)
        )
        if kana + han:
            return (
                not (traditional_chinese and kana == 0)
                and kana + han >= hangul
                and kana + han >= latin_authority
            )
        return _ascii_is_name_acronym_or_number(text)
    if hangul:
        return hangul >= han + kana and hangul >= latin_authority
    return _ascii_is_name_acronym_or_number(text)


def validate_locale_plan(
    brief: dict[str, Any],
    plan: object,
    *,
    prior_plan: dict[str, Any] | None = None,
) -> None:
    validate_translation_brief(brief)
    if not isinstance(plan, dict) or set(plan) != {
        "schema_version",
        "run_id",
        "generation",
        "articles",
    }:
        raise ValueError("locale plan fields are strict")
    if (
        plan.get("schema_version") != SCHEMA_VERSION
        or plan.get("run_id") != brief["run_id"]
        or type(plan.get("generation")) is not int
        or type(plan.get("generation")) is bool
        or plan["generation"] < 1
    ):
        raise ValueError("locale plan identity is invalid")
    articles = plan.get("articles")
    if not isinstance(articles, list) or len(articles) != len(brief["articles"]):
        raise ValueError("locale plan target count differs from brief")
    prior_by_slot = {
        str(item.get("slot")): item
        for item in (prior_plan or {}).get("articles", [])
        if isinstance(item, dict)
    }
    fact_package = _source_fact_package(brief)
    for index, target in enumerate(brief["articles"]):
        slot = f"article-{index + 1:02d}"
        item = articles[index]
        required = {
            "slot",
            "locale",
            "source_sha256",
            "native_search_intent",
            "native_query_phrasings",
            "article_angle",
            "ordered_h2_outline",
            "coverage_mapping",
            "source_structure_not_copied",
            "rebuild_outline",
        }
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError(f"locale plan article fields are strict for {slot}")
        if item["slot"] != slot or item["locale"] != target["locale"]:
            raise ValueError(f"locale plan locale identity differs for {slot}")
        if item["source_sha256"] != target["source_sha256"]:
            raise ValueError(f"locale plan source hash differs for {slot}")
        for field in ("native_search_intent", "article_angle"):
            _non_empty_string(item.get(field), f"locale plan {field}")
        queries = item.get("native_query_phrasings")
        if not isinstance(queries, list) or not queries:
            raise ValueError(f"locale plan query phrasing is empty for {slot}")
        for query in queries:
            _non_empty_string(query, "locale plan query phrasing")
        outline = item.get("ordered_h2_outline")
        if (
            not isinstance(outline, list)
            or len(outline) != 4
            or len(_normalized_outline(outline)) != len(set(_normalized_outline(outline)))
        ):
            raise ValueError(f"locale plan outline is invalid for {slot}")
        for heading in outline:
            _non_empty_string(heading, "locale plan heading")
        expected_facts = {
            str(fact["fact_id"]): fact
            for fact in fact_package["articles"][index]["facts"]
        }
        mappings = item.get("coverage_mapping")
        if not isinstance(mappings, list) or len(mappings) != len(expected_facts):
            raise ValueError(f"locale plan coverage mapping differs for {slot}")
        seen_fact_ids: set[str] = set()
        mapped_fact_ids: list[str] = []
        for mapping in mappings:
            if not isinstance(mapping, dict) or set(mapping) != {
                "source_fact_id",
                "planned_h2",
                "coverage_note",
                "safety_boundary",
            }:
                raise ValueError(f"locale plan coverage fields are strict for {slot}")
            fact_id = str(mapping["source_fact_id"])
            if fact_id not in expected_facts or fact_id in seen_fact_ids:
                raise ValueError(f"locale plan source fact coverage differs for {slot}")
            seen_fact_ids.add(fact_id)
            mapped_fact_ids.append(fact_id)
            if mapping["planned_h2"] not in outline:
                raise ValueError(f"locale plan coverage heading differs for {slot}")
            _non_empty_string(mapping["coverage_note"], "locale plan coverage note")
            if mapping["safety_boundary"] is not expected_facts[fact_id]["safety_boundary"]:
                raise ValueError(f"locale plan safety coverage differs for {slot}")
        if mapped_fact_ids != list(expected_facts):
            raise ValueError(f"locale plan coverage mapping order differs for {slot}")
        semantic_items = [
            ("native_search_intent", str(item["native_search_intent"])),
            *[
                (f"native_query_phrasings[{query_index}]", str(query))
                for query_index, query in enumerate(queries)
            ],
            ("article_angle", str(item["article_angle"])),
            *[
                (f"ordered_h2_outline[{heading_index}]", str(heading))
                for heading_index, heading in enumerate(outline)
            ],
            *[
                (f"coverage_note[{mapping_index}]", str(mapping["coverage_note"]))
                for mapping_index, mapping in enumerate(mappings)
            ],
        ]
        source_ascii_authorities = _source_ascii_authorities(target["source"])
        for field, value in semantic_items:
            if not _plan_matches_target_language(
                str(target["locale"]),
                value,
                source_ascii_authorities=source_ascii_authorities,
            ):
                raise ValueError(
                    f"locale plan native locale language differs for {slot}.{field}"
                )
        source_headings = [
            section["heading"]
            for section in target["source"]["bodySections"]
        ]
        if (
            not isinstance(item.get("source_structure_not_copied"), list)
            or set(item["source_structure_not_copied"]) != set(source_headings)
        ):
            raise ValueError(f"locale plan source structure blacklist differs for {slot}")
        if type(item.get("rebuild_outline")) is not bool:
            raise ValueError(f"locale plan rebuild flag is invalid for {slot}")
        prior = prior_by_slot.get(slot)
        if (
            item["rebuild_outline"]
            and prior is not None
            and _outline_topology(item)
            and _outline_topology(item) == _outline_topology(prior)
        ):
            raise ValueError(f"locale plan rebuild reused prior outline topology for {slot}")


def _canonicalize_external_coverage_mappings(
    expected_facts: list[dict[str, Any]],
    mappings: object,
    *,
    slot: str,
    source_ref_map: dict[str, str] | None = None,
    allow_provider_safety_boundary: bool = False,
) -> list[dict[str, Any]]:
    """驗證 fact 集合後，依 deterministic fact 順序注入本機 safety。"""
    if not isinstance(mappings, list) or len(mappings) != len(expected_facts):
        raise ValueError(f"external locale plan coverage differs for {slot}")
    expected_by_id = {
        str(fact["fact_id"]): fact
        for fact in expected_facts
    }
    mapped_by_id: dict[str, dict[str, Any]] = {}
    identity_field = "source_ref" if source_ref_map is not None else "source_fact_id"
    required = {
        identity_field,
        "planned_h2_slot",
        "coverage_note",
    }
    if allow_provider_safety_boundary:
        required.add("safety_boundary")
    for mapping in mappings:
        if not isinstance(mapping, dict) or set(mapping) != required:
            raise ValueError(
                f"external locale plan coverage fields are strict for {slot}"
            )
        if source_ref_map is not None:
            source_ref = str(mapping["source_ref"])
            if source_ref not in source_ref_map:
                raise ValueError(f"external locale plan source ref coverage differs for {slot}")
            fact_id = source_ref_map[source_ref]
        else:
            fact_id = str(mapping["source_fact_id"])
        if fact_id not in expected_by_id or fact_id in mapped_by_id:
            reason = "source ref" if source_ref_map is not None else "source fact"
            raise ValueError(f"external locale plan {reason} coverage differs for {slot}")
        hydrated = dict(mapping)
        if source_ref_map is not None:
            hydrated.pop("source_ref")
            hydrated["source_fact_id"] = fact_id
        hydrated["safety_boundary"] = expected_by_id[fact_id]["safety_boundary"]
        mapped_by_id[fact_id] = hydrated
    return [
        mapped_by_id[str(fact["fact_id"])]
        for fact in expected_facts
    ]


def _hydrate_locale_plan(
    brief: dict[str, Any],
    external: dict[str, Any],
    *,
    generation: int,
    rebuild_by_slot: dict[str, bool],
    prior_plan: dict[str, Any] | None = None,
    source_ref_maps: dict[str, dict[str, str]] | None = None,
    allow_provider_safety_boundary: bool = False,
) -> dict[str, Any]:
    if set(external) != {"articles"} or not isinstance(external["articles"], list):
        raise ValueError("external locale plan fields are strict")
    expected_slots = [
        f"article-{index + 1:02d}"
        for index in range(len(brief["articles"]))
    ]
    supplied_slots = [
        str(item.get("slot")) if isinstance(item, dict) else ""
        for item in external["articles"]
    ]
    if supplied_slots != expected_slots:
        raise ValueError("external locale plan slots differ from brief order")
    by_slot = {
        str(item.get("slot")): item
        for item in external["articles"]
        if isinstance(item, dict)
    }
    if set(by_slot) != set(expected_slots) or len(by_slot) != len(external["articles"]):
        raise ValueError("external locale plan slots differ from brief")
    fact_articles = _source_fact_package(brief)["articles"]
    if source_ref_maps is None:
        source_ref_maps = _request_local_source_ref_maps(brief, prior_plan)
    if source_ref_maps:
        _validate_source_ref_maps_against_current_package(brief, source_ref_maps)
    articles = []
    for index, slot in enumerate(expected_slots):
        external_item = by_slot[slot]
        external_required = {
            "slot",
            "locale",
            "native_search_intent",
            "native_query_phrasings",
            "article_angle",
            "ordered_h2_outline",
            "coverage_mapping",
            "source_structure_not_copied",
            "rebuild_outline",
        }
        if slot not in source_ref_maps:
            external_required.add("source_sha256")
        if not isinstance(external_item, dict) or set(external_item) != external_required:
            raise ValueError(f"external locale plan article fields are strict for {slot}")
        external_mappings = _canonicalize_external_coverage_mappings(
            fact_articles[index]["facts"],
            external_item.get("coverage_mapping"),
            slot=slot,
            source_ref_map=source_ref_maps.get(slot),
            allow_provider_safety_boundary=allow_provider_safety_boundary,
        )
        item_source_sha256 = (
            brief["articles"][index]["source_sha256"]
            if slot in source_ref_maps
            else external_item.get("source_sha256")
        )
        item = {
            **external_item,
            "source_sha256": item_source_sha256,
            "source_structure_not_copied": [
                section["heading"]
                for section in brief["articles"][index]["source"]["bodySections"]
            ],
            "rebuild_outline": rebuild_by_slot.get(slot, False),
            "coverage_mapping": [
                dict(mapping)
                for mapping in external_mappings
            ],
        }
        if type(external_item.get("rebuild_outline")) is not bool:
            raise ValueError(f"locale plan rebuild flag is invalid for {slot}")
        outline = item.get("ordered_h2_outline")
        if not isinstance(outline, list):
            raise ValueError(f"locale plan outline is invalid for {slot}")
        for mapping in item["coverage_mapping"]:
            if set(mapping) != {
                "source_fact_id",
                "planned_h2_slot",
                "coverage_note",
                "safety_boundary",
            }:
                raise ValueError(
                    f"external locale plan coverage fields are strict for {slot}"
                )
            heading_slot = mapping.pop("planned_h2_slot")
            heading_slots = {
                f"h2-{index + 1}": index
                for index in range(len(outline))
            }
            if type(heading_slot) is not str or heading_slot not in heading_slots:
                raise ValueError(f"locale plan coverage heading slot differs for {slot}")
            heading_index = heading_slots[heading_slot]
            mapping["planned_h2"] = outline[heading_index]
        articles.append(item)
    plan = {
        "schema_version": SCHEMA_VERSION,
        "run_id": brief["run_id"],
        "generation": generation,
        "articles": articles,
    }
    validate_locale_plan(brief, plan, prior_plan=prior_plan)
    return plan


def _rebuild_topology_constraints(
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    rebuild_by_slot: dict[str, bool],
    *,
    source_ref_maps: dict[str, dict[str, str]] | None = None,
    legacy_authority: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """把前代 fact-to-H2 topology 轉成模型可直接比較的 slot 契約。"""
    source_ref_maps = source_ref_maps or {}
    legacy_authority = legacy_authority or {}
    prior_by_slot = {
        str(item.get("slot")): item
        for item in (prior_plan or {}).get("articles", [])
        if isinstance(item, dict)
    }
    articles = []
    for index, _target in enumerate(brief["articles"]):
        slot = f"article-{index + 1:02d}"
        prior = prior_by_slot.get(slot, {})
        outline = prior.get("ordered_h2_outline", [])
        heading_slots = (
            {
                str(heading): f"h2-{heading_index + 1}"
                for heading_index, heading in enumerate(outline)
            }
            if isinstance(outline, list)
            else {}
        )
        if slot in source_ref_maps:
            retained = legacy_authority.get(slot, {}).get("prior_ref_to_h2_slot", [])
            articles.append(
                {
                    "slot": slot,
                    "rebuild_required": rebuild_by_slot.get(slot, False),
                    "legacy_mapping_status": legacy_authority.get(slot, {}).get(
                        "legacy_mapping_status",
                        "UNAVAILABLE",
                    ),
                    "prior_ref_to_h2_slot": retained,
                    "forbidden_prior_topology_signature": [
                        item["planned_h2_slot"]
                        for item in retained
                    ],
                }
            )
        else:
            prior_fact_to_h2_slot = [
                {
                    "source_fact_id": str(mapping["source_fact_id"]),
                    "planned_h2_slot": heading_slots[str(mapping["planned_h2"])],
                }
                for mapping in prior.get("coverage_mapping", [])
                if isinstance(mapping, dict)
                and "source_fact_id" in mapping
                and str(mapping.get("planned_h2")) in heading_slots
            ]
            articles.append(
                {
                    "slot": slot,
                    "rebuild_required": rebuild_by_slot.get(slot, False),
                    "prior_fact_to_h2_slot": prior_fact_to_h2_slot,
                    "forbidden_prior_topology_signature": [
                        item["planned_h2_slot"]
                        for item in prior_fact_to_h2_slot
                    ],
                }
            )
    return {"articles": articles}


def _plan_prompt(
    brief: dict[str, Any],
    *,
    generation: int,
    prior_plan: dict[str, Any] | None,
    findings: list[dict[str, str]],
    rebuild_by_slot: dict[str, bool],
    source_ref_maps: dict[str, dict[str, str]] | None = None,
) -> str:
    if source_ref_maps is None:
        source_ref_maps = _request_local_source_ref_maps(brief, prior_plan)
    legacy_authority = _legacy_plan_authority(brief, prior_plan, source_ref_maps)
    source_identity = "source_ref" if source_ref_maps else "source_fact_id"
    return "\n".join(
        [
            "你是 Pantheon 的目標語言內容規劃主編。只輸出 locale plan，不寫文章。",
            "topic、native search intent、query phrasing 與 H2 必須完全由本次 source fact package 產生，不得套用任何預設題材。",
            f"coverage_mapping 必須逐一覆蓋 source fact，且每筆只能輸出 {source_identity}、planned_h2_slot 與 coverage_note。",
            "不得輸出 schema 未列欄位；限制保留由 pipeline 的本機 source fact authority 在 hydrate 時處理。",
            "JA protected_constraints 是 boundary coverage authority；boundary source spans 只供 provenance trace，不得逐段重現為獨立 safety requirement。",
            "ordered_h2_outline 必須恰好有 4 個 H2；coverage_mapping.planned_h2_slot 必須使用 h2-1、h2-2、h2-3 或 h2-4，不得另寫或改寫 H2 文字。",
            "ordered_h2_outline 必須是目標語言的自然標題；h2-1、h2-2、h2-3、h2-4 只供 planned_h2_slot 定位，禁止把它們當成標題。",
            "source_structure_to_avoid 只用來辨識不能複製的來源 H2、section count、paragraph pattern；不得把它當 outline。",
            "rebuild_outline 由 pipeline 指定，不得自行改值。為 true 時，禁止沿用 prior plan 的 heading order、section topology 或同義詞替換版。",
            "rebuild topology constraints 中 rebuild_required=true 時，輸出的 planned_h2_slot 序列不得等於 forbidden_prior_topology_signature。",
            "JA continuation 使用本次 request-local source_ref；provider 不得輸出或抄寫任何本機 identity、span 或 hash 欄位。",
            "legacy mapping authority:",
            _canonical_json(legacy_authority),
            "rebuild contract:",
            _canonical_json(
                {
                    "required_when": "rebuild_outline=true",
                    "topology_definition": (
                        f"依 {source_identity} 順序排列的 "
                        "coverage_mapping.planned_h2_slot 序列"
                    ),
                    "prior_comparison": (
                        "將 prior plan coverage_mapping.planned_h2 對回 prior "
                        "ordered_h2_outline 的 h2-1 至 h2-4"
                    ),
                    "minimum_change": (
                        "至少一個有意義 fact 的 planned_h2_slot "
                        "必須與 prior plan 不同"
                    ),
                    "must_preserve": [
                        f"全部 {source_identity}",
                        "local safety authority",
                        "locale plan JSON schema",
                    ],
                    "insufficient_changes": [
                        "只換 H2 標題或同義詞",
                        "只改標題順序文字",
                        "只改 coverage_note",
                    ],
                }
            ),
            "rebuild topology constraints:",
            _canonical_json(
                _rebuild_topology_constraints(
                    brief,
                    prior_plan,
                    rebuild_by_slot,
                    source_ref_maps=source_ref_maps,
                    legacy_authority=legacy_authority,
                )
            ),
            "generation:",
            str(generation),
            "locale contracts:",
            _canonical_json(LOCALE_EDITORIAL_CONTRACTS),
            "source fact package:",
            _canonical_json(_source_fact_package_for_prompt(brief, source_ref_maps)),
            "source structure to avoid:",
            _canonical_json(_source_structure_to_avoid(brief)),
            "prior plan:",
            _canonical_json(
                {"articles": list(legacy_authority.values())}
                if source_ref_maps
                else prior_plan
            ),
            "findings:",
            _canonical_json(findings),
            "rebuild authority:",
            _canonical_json(rebuild_by_slot),
        ]
    )


def _article_prompt(
    brief: dict[str, Any],
    plan: dict[str, Any] | None,
    findings: list[dict[str, str]],
    source_ref_maps: dict[str, dict[str, str]] | None = None,
) -> str:
    try:
        validate_locale_plan(brief, plan)
    except (TypeError, ValueError) as error:
        raise ValueError(f"locale plan is required and must be valid: {error}") from error
    if source_ref_maps is None:
        source_ref_maps = (
            _request_local_source_ref_maps(brief, plan)
            if all(str(item.get("locale")) == "ja" for item in brief["articles"])
            else {}
        )
    fact_package_for_prompt = _source_fact_package_for_prompt(brief, source_ref_maps)
    public_input = {
        "articles": [
            {
                **fact_package,
                "editorial_contract": LOCALE_EDITORIAL_CONTRACTS[target["locale"]],
                "locale_plan": _locale_plan_for_prompt(
                    plan["articles"][index],
                    source_ref_maps.get(str(fact_package["slot"])),
                ),
            }
            for index, (target, fact_package) in enumerate(
                zip(brief["articles"], fact_package_for_prompt["articles"])
            )
        ]
    }
    return "\n".join(
        [
            "你是 Pantheon 的目標語言母語主編。這不是翻譯任務；slot 必須逐字複製。",
            "只依 source fact package、locale contract 與已驗證 locale plan 寫完整文章。",
            "所有可見欄位都必須以 article input.locale 指定的語言完整重寫；title、description、answer、tags、FAQ、H2 與 paragraphs 禁止保留來源語言文字，只有該 locale 慣用的專有名詞與識別符例外。",
            "tags 必須逐項以目標語言的自然搜尋用語重寫，不得複製或沿用來源語言 tag。",
            "寫作前先建立 source claim ledger：每一個定義、解釋、例子與結論都必須能由 source fact 明確支持；無法對應的句子直接刪除，不得用常識補完。",
            "ordered_h2_outline 是唯一 section authority；不得推回或模仿來源 H2、段落數、敘事順序。",
            "bodySections 的數量、順序與 heading 必須逐字對齊 ordered_h2_outline；h2-1 到 h2-4 只是 mapping slot，不是可輸出的標題。",
            "不得逐句對譯。可拆分、合併、重排 facts，但不能新增來源沒有的事實或承諾。",
            "JA protected_constraints 必須覆蓋其 required_fields；raw boundary source_text 只供 provenance trace，不得逐段複製成重複 boilerplate。",
            "JA field-by-field protected boundary checklist: meta_description 與 body 必須各自包含每個 protected_constraints category 的自然日文可辨識語意；outcome_not_determined 在每個 required field 都要明確表達結果／未來結果不可斷定或保證，例如「結果を断定しない」「結果を保証しない」「未来の結果を完全に確定することはできない」。不得用 FAQ、answer、tags、另一個 required field、contextual/general disclaimer 或 professional advice disclaimer 代替；也不得把同一句 disclaimer 逐段重複成 boilerplate。",
            "禁止用比喻、口號、華麗形容詞或抽象 AI 套話填補篇幅。",
            "只針對 findings 做 targeted repair，但不得接收或沿用前一版文章全文。",
            "article input:",
            json.dumps(public_input, ensure_ascii=False, sort_keys=True),
            "findings:",
            json.dumps(findings, ensure_ascii=False),
        ]
    )


def _writer_prompt(
    brief: dict[str, Any],
    plan: dict[str, Any],
    findings: list[dict[str, str]],
) -> str:
    """保留舊 helper 名稱；Writer authority 已改為 validated locale plan。"""
    return _article_prompt(brief, plan, findings)


def _external_candidate_schema() -> dict[str, Any]:
    faq = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"question": {"type": "string"}, "answer": {"type": "string"}},
        "required": ["question", "answer"],
    }
    section = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "heading": {"type": "string"},
            "paragraphs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "required": ["heading", "paragraphs"],
    }
    localized = {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "answer": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "faq": {"type": "array", "items": faq, "minItems": 1},
        "bodySections": {"type": "array", "items": section, "minItems": 4, "maxItems": 5},
    }
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"slot": {"type": "string"}, **localized},
        "required": ["slot", *sorted(localized)],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"articles": {"type": "array", "items": item, "minItems": 1, "maxItems": 5}},
        "required": ["articles"],
    }


def _public_brief(brief: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "translate_existing",
        "policy": {
            "purpose": "母語重寫／SEO 在地化，不是翻譯。原文只提供可用事實、觀點與安全邊界",
            "seo": "依目標語言的實際搜尋語序重做 title、description、answer、tags、H2 與 FAQ，不堆疊關鍵字",
            "tags": "tags 必須逐項以目標語言的自然搜尋用語重寫，不得複製或沿用來源語言 tag。",
            "safety": "不得新增原文沒有的承諾、診斷、法律、醫療、財務或命運結論",
            "coverage": "原文的重要資訊與限制都要覆蓋，但可改變順序、H2 數量、段落切分、FAQ 問法與例子擺放位置",
            "hard_reject": "逐句對譯、中文語序殘留、相同 H2／段落骨架、非母語搭配、AI 套話或搜尋用語不自然",
        },
        "articles": [
            {
                "slot": f"article-{index + 1:02d}",
                "locale": item["locale"],
                "language": LOCALE_LABELS[item["locale"]],
                "editorial_contract": LOCALE_EDITORIAL_CONTRACTS[item["locale"]],
                "source": item["source"],
            }
            for index, item in enumerate(brief["articles"])
        ],
    }


def _hydrate_candidate(brief: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    if set(external) != {"articles"} or not isinstance(external["articles"], list):
        raise ValueError("external translation candidate fields are strict")
    by_slot = {str(item.get("slot")): item for item in external["articles"] if isinstance(item, dict)}
    expected_slots = [f"article-{index + 1:02d}" for index in range(len(brief["articles"]))]
    if set(by_slot) != set(expected_slots) or len(by_slot) != len(external["articles"]):
        raise ValueError("external translation slots differ from brief")
    articles = []
    for index, source in enumerate(brief["articles"]):
        generated = by_slot[expected_slots[index]]
        if set(generated) != {"slot", *TRANSLATABLE_FIELDS}:
            raise ValueError("external translation article fields are strict")
        localized_fields = {field: generated[field] for field in sorted(TRANSLATABLE_FIELDS)}
        if source["locale"] == "ko":
            localized_fields = _normalize_korean_typography(localized_fields)
        articles.append(
            {
                "article_id": source["translation_id"],
                "locale": source["locale"],
                "source_article_id": source["source_article_id"],
                "source_path": source["source_path"],
                "source_sha256": source["source_sha256"],
                **localized_fields,
            }
        )
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "run_id": brief["run_id"],
        "mode": "translate_existing",
        "articles": articles,
    }
    validate_translation_candidate(brief, candidate)
    return candidate


def _normalize_korean_typography(value: Any) -> Any:
    """將韓文內容中不自然的全形西文標點轉為半形。"""
    if isinstance(value, str):
        return value.translate(str.maketrans({"？": "?", "！": "!", "：": ":", "；": ";"}))
    if isinstance(value, list):
        return [_normalize_korean_typography(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_korean_typography(item) for key, item in value.items()}
    return value


def _reviewer_prompt(
    brief: dict[str, Any],
    candidate: dict[str, Any],
    findings: list[dict[str, str]],
) -> str:
    public_candidate = {
        "articles": [
            {"slot": f"article-{index + 1:02d}", **{field: article[field] for field in sorted(TRANSLATABLE_FIELDS)}}
            for index, article in enumerate(candidate["articles"])
        ]
    }
    return "\n".join(
        [
            "你是獨立目標語言母語總編。逐篇比較原文與在地化稿，slot 必須逐字複製。",
            "檢查資訊覆蓋、母語語法、搜尋語序、文體一致、限制保留、無新增事實與無殘留繁中。",
            "只要命中 LITERAL_TRANSLATION、SOURCE_SYNTAX_TRANSFER、MIRRORED_STRUCTURE、NON_NATIVE_SEARCH_INTENT 或 AI_TEMPLATE_STYLE 任一項，就必須 REJECT。",
            "不要因為意思大致正確就放行；文章必須讀起來像直接以該語言採訪、規劃並寫成的原生內容。",
            "deterministic findings 必須判 REJECT，不得忽略。",
            "JA protected source constraints 與 deterministic findings 是 boundary authority；raw source_text 只供 trace，不是逐段複製要求。",
            "public brief:",
            json.dumps(_public_brief(brief), ensure_ascii=False),
            "public candidate:",
            json.dumps(public_candidate, ensure_ascii=False),
            "protected source constraint view:",
            json.dumps(_ja_boundary_contracts_for_brief(brief), ensure_ascii=False),
            "deterministic findings:",
            json.dumps(findings, ensure_ascii=False),
        ]
    )


def _load_or_generate_external(
    client: pipeline.GeminiClient,
    role: str,
    prompt: str,
    schema: dict[str, Any],
    receipt_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """讓同一 attempt 可從已成功的外部 operation 接續，不重生內容。"""
    if output_path.is_file():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{output_path.name} must contain a JSON object")
        return payload
    payload = pipeline._generate_with_receipt(client, role, prompt, schema, receipt_path)
    pipeline.write_json(output_path, payload)
    return payload


def _external_locale_plan_contains_provider_safety(payload: dict[str, Any]) -> bool:
    articles = payload.get("articles")
    if not isinstance(articles, list):
        return False
    for article in articles:
        if not isinstance(article, dict):
            continue
        mappings = article.get("coverage_mapping")
        if not isinstance(mappings, list):
            continue
        if any(isinstance(mapping, dict) and "safety_boundary" in mapping for mapping in mappings):
            return True
    return False


def _legacy_provider_safety_schema_sha256s(
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    source_ref_maps: dict[str, dict[str, str]],
) -> set[str]:
    legacy_schema = _external_locale_plan_schema(
        brief,
        prior_plan=prior_plan,
        source_ref_maps=source_ref_maps,
        include_provider_safety_boundary=True,
    )
    return {_json_sha256(legacy_schema)}


def _validate_legacy_provider_safety_receipt(
    receipt_path: Path,
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    source_ref_maps: dict[str, dict[str, str]],
) -> None:
    if not source_ref_maps:
        raise ValueError("legacy external locale plan safety requires source ref map")
    if not receipt_path.is_file():
        raise ValueError("legacy external locale plan safety requires planning receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_digests = _legacy_provider_safety_schema_sha256s(
        brief,
        prior_plan,
        source_ref_maps,
    )
    if (
        not isinstance(receipt, dict)
        or receipt.get("status") != "success"
        or receipt.get("role") != "writer"
        or receipt.get("schema_sha256") not in expected_digests
    ):
        raise ValueError("legacy external locale plan safety receipt schema drift")


def _load_or_generate_external_locale_plan(
    client: pipeline.GeminiClient,
    prompt: str,
    schema: dict[str, Any],
    receipt_path: Path,
    output_path: Path,
    *,
    brief: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    source_ref_maps: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], bool]:
    """讀取既有 plan 時，只有舊 schema receipt 可授權 provider safety 欄位。"""
    if output_path.is_file():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{output_path.name} must contain a JSON object")
        has_provider_safety = _external_locale_plan_contains_provider_safety(payload)
        if has_provider_safety:
            _validate_legacy_provider_safety_receipt(
                receipt_path,
                brief,
                prior_plan,
                source_ref_maps,
            )
        return payload, has_provider_safety
    payload = pipeline._generate_with_receipt(client, "writer", prompt, schema, receipt_path)
    pipeline.write_json(output_path, payload)
    return payload, False


def _write_locale_planning_result(
    path: Path,
    *,
    generation: int,
    transport_status: str,
    planning_contract_status: str,
    terminal_stage: str | None,
    terminal_reason: str | None,
) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generation": generation,
        "transport_status": transport_status,
        "planning_contract_status": planning_contract_status,
        "terminal_stage": terminal_stage,
        "terminal_reason": terminal_reason,
    }
    _atomic_write_json(path, payload)


def _continuation_lifecycle_path(run_dir: Path) -> Path:
    return run_dir / "continuation" / "generation-lifecycle.json"


def _committed_planning_artifact_status(
    generation_dir: Path,
) -> tuple[list[str], list[str]]:
    required = [
        "external-plan.json",
        "source-ref-map.json",
        "planning-result.json",
        "locale-plan.json",
        "plan-operation.json",
    ]
    present = [
        name
        for name in required
        if (generation_dir / name).is_file()
    ]
    missing = [
        name
        for name in required
        if not (generation_dir / name).is_file()
    ]
    return present, missing


def _partial_generation_decision_payload(
    brief: dict[str, Any],
    *,
    generation: int,
    generation_dir: Path,
    reason: str,
) -> dict[str, Any]:
    present, missing = _committed_planning_artifact_status(generation_dir)
    preserved = [
        name
        for name in ["external-plan.json", "plan-operation.json"]
        if (generation_dir / name).is_file()
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": "continuation-partial-generation-terminalization",
        "run_id": brief["run_id"],
        "generation": generation,
        "generation_name": f"{generation:02d}",
        "allocated": True,
        "committed": False,
        "resumable": False,
        "decision": "terminalize",
        "lifecycle_state": "abandoned",
        "terminal_stage": "PLANNING",
        "terminal_reason": reason,
        "source_package_sha256": _json_sha256(_source_fact_package(brief)),
        "committed_planning_artifacts_present": present,
        "committed_planning_artifacts_missing": missing,
        "preserved_audit_artifacts": preserved,
        "allowed_next_actions": [
            "explicit_deterministic_replan_after_authority_update",
            "explicit_next_generation_after_authority_update",
        ],
    }


def _write_if_same_or_missing(path: Path, payload: dict[str, Any]) -> None:
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError(f"{path.name} differs from continuation lifecycle contract")
        return
    _atomic_write_json(path, payload)


def _record_partial_generation_terminalization(
    brief: dict[str, Any],
    *,
    generation: int,
    generation_dir: Path,
    reason: str,
) -> None:
    if generation_dir.parent.name != "generations":
        return
    run_dir = generation_dir.parent.parent
    decision = _partial_generation_decision_payload(
        brief,
        generation=generation,
        generation_dir=generation_dir,
        reason=reason,
    )
    _write_if_same_or_missing(
        generation_dir / "partial-generation-decision.json",
        decision,
    )
    lifecycle_path = _continuation_lifecycle_path(run_dir)
    lifecycle = {
        "schema_version": SCHEMA_VERSION,
        "contract": "continuation-generation-lifecycle",
        "run_id": brief["run_id"],
        "source_package_sha256": decision["source_package_sha256"],
        "generations": {
            f"{generation:02d}": {
                "generation": generation,
                "allocated": True,
                "committed": False,
                "resumable": False,
                "decision": "terminalize",
                "lifecycle_state": "abandoned",
                "terminal_stage": "PLANNING",
                "terminal_reason": reason,
                "decision_artifact": (
                    f"generations/{generation:02d}/partial-generation-decision.json"
                ),
            }
        },
    }
    _write_if_same_or_missing(lifecycle_path, lifecycle)


def _authority_transition_path(run_dir: Path, generation: int) -> Path:
    return run_dir / "continuation" / f"authority-transition-{generation:02d}.json"


@contextmanager
def _continuation_run_lock(run_dir: Path) -> Any:
    continuation_dir = run_dir / "continuation"
    continuation_dir.mkdir(parents=True, exist_ok=True)
    with (continuation_dir / "continuation.lock").open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _validate_partial_generation_decision(
    run_dir: Path,
    brief: dict[str, Any],
    *,
    generation: int,
) -> dict[str, Any] | None:
    generation_dir = run_dir / "generations" / f"{generation:02d}"
    decision_path = generation_dir / "partial-generation-decision.json"
    if not decision_path.is_file():
        return None
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    lifecycle_path = _continuation_lifecycle_path(run_dir)
    lifecycle = (
        json.loads(lifecycle_path.read_text(encoding="utf-8"))
        if lifecycle_path.is_file()
        else None
    )
    expected_source_package = _json_sha256(_source_fact_package(brief))
    present, missing = _committed_planning_artifact_status(generation_dir)
    lifecycle_item = (
        lifecycle.get("generations", {}).get(f"{generation:02d}")
        if isinstance(lifecycle, dict)
        else None
    )
    if (
        not isinstance(decision, dict)
        or decision.get("schema_version") != SCHEMA_VERSION
        or decision.get("contract")
        != "continuation-partial-generation-terminalization"
        or decision.get("run_id") != brief["run_id"]
        or decision.get("generation") != generation
        or decision.get("generation_name") != f"{generation:02d}"
        or decision.get("allocated") is not True
        or decision.get("committed") is not False
        or decision.get("resumable") is not False
        or decision.get("decision") != "terminalize"
        or decision.get("lifecycle_state") != "abandoned"
        or decision.get("terminal_stage") != "PLANNING"
        or decision.get("source_package_sha256") != expected_source_package
        or decision.get("committed_planning_artifacts_present") != present
        or decision.get("committed_planning_artifacts_missing") != missing
        or "source-ref-map.json" not in missing
        or not isinstance(lifecycle_item, dict)
        or lifecycle_item.get("decision_artifact")
        != f"generations/{generation:02d}/partial-generation-decision.json"
        or lifecycle_item.get("committed") is not False
        or lifecycle_item.get("resumable") is not False
        or lifecycle_item.get("lifecycle_state") != "abandoned"
    ):
        raise ValueError("partial generation terminal decision is invalid")
    return decision


def _consume_partial_generation_terminalization(
    run_dir: Path,
    brief: dict[str, Any],
    state: dict[str, Any],
) -> bool:
    if state.get("status") != "active":
        return False
    abandoned = list(state.get("abandoned_generations", []))
    current_generation = int(state["next_generation"])
    if abandoned and abandoned[-1] == current_generation - 1:
        transition_path = _authority_transition_path(run_dir, abandoned[-1])
        if transition_path.is_file():
            json.loads(transition_path.read_text(encoding="utf-8"))
        return False
    decision = _validate_partial_generation_decision(
        run_dir,
        brief,
        generation=current_generation,
    )
    if decision is None:
        return False
    if current_generation in state.get("completed_generations", []):
        raise ValueError("partial generation decision conflicts with completed state")
    updated = {
        **state,
        "abandoned_generations": [*abandoned, current_generation],
        "next_generation": current_generation + 1,
    }
    transition = {
        "schema_version": SCHEMA_VERSION,
        "contract": "continuation-authority-transition",
        "run_id": brief["run_id"],
        "action": "advance_after_terminalized_partial",
        "generation": current_generation,
        "decision_artifact": (
            f"generations/{current_generation:02d}/partial-generation-decision.json"
        ),
        "from_next_generation": current_generation,
        "to_next_generation": current_generation + 1,
        "completed_generations": updated["completed_generations"],
        "abandoned_generations": updated["abandoned_generations"],
        "state_before_sha256": _json_sha256(state),
        "state_after_sha256": _json_sha256(updated),
        "terminal_reason": decision["terminal_reason"],
    }
    _write_if_same_or_missing(
        _authority_transition_path(run_dir, current_generation),
        transition,
    )
    _atomic_write_json(run_dir / "continuation" / "state.json", updated)
    return True


def _require_sha256_digest(value: object, label: str) -> str:
    digest = str(value)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"{label} is invalid")
    return digest


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> str | None:
    if not root.exists():
        return None
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        if path.is_symlink():
            digest.update(b"SYMLINK")
            digest.update(path.readlink().as_posix().encode("utf-8"))
        elif path.is_file():
            digest.update(b"FILE")
            digest.update(path.read_bytes())
        elif path.is_dir():
            digest.update(b"DIR")
    return digest.hexdigest()


def _bytes_sha256(value: bytes | None) -> str | None:
    return hashlib.sha256(value).hexdigest() if value is not None else None


def _validate_approved_stage_formal_identity(
    identity: dict[str, Any],
    result: dict[str, Any],
    review: dict[str, Any],
    run_id: str,
    article_sha256: str,
) -> None:
    job_id = str(identity.get("job_id") or "")
    request_sha256 = str(identity.get("request_sha256") or "")
    if (
        identity.get("schema_version") != SCHEMA_VERSION
        or identity.get("run_id") != run_id
        or identity.get("role") != "reviewer"
        or identity.get("lane") not in TRANSLATION_IDENTITY_LANES
        or re.fullmatch(r"[0-9a-f]{40}", job_id) is None
        or re.fullmatch(r"[0-9a-f]{64}", request_sha256) is None
        or not request_sha256.startswith(job_id)
        or result.get("exit_verdict") != "APPROVE_READY_FOR_STAGING"
        or result.get("findings") != []
        or result.get("review") != review
        or any(
            item.get("candidate_sha256") != article_sha256
            or item.get("verdict") != "APPROVE"
            or item.get("findings") != []
            for item in review.get("articles", [])
        )
    ):
        raise ValueError("formal review identity is invalid")


def _approved_stage_path(
    run_dir: Path,
    relative: str,
    *,
    must_exist: bool = True,
    directory: bool = False,
    create_root: bool = False,
) -> Path:
    run_root = run_dir.resolve(strict=True)
    stage_root = run_root / "editorial-staging"
    if stage_root.is_symlink():
        raise ValueError("approved edited stage root must not be a symlink")
    if create_root:
        stage_root.mkdir(exist_ok=True)
    if stage_root.exists() and (
        not stage_root.is_dir() or stage_root.resolve(strict=True).parent != run_root
    ):
        raise ValueError("approved edited stage root differs")
    part = Path(relative)
    if part.is_absolute() or not part.parts or ".." in part.parts:
        raise ValueError("approved edited stage path differs")
    target = stage_root / part
    if target.is_symlink():
        raise ValueError("approved edited stage path must not be a symlink")
    if not target.exists():
        if must_exist:
            raise ValueError("approved edited stage path is missing")
        return target
    expected = stage_root.resolve(strict=True).joinpath(*part.parts)
    resolved = target.resolve(strict=True)
    if resolved != expected or (directory and not resolved.is_dir()) or (not directory and not resolved.is_file()):
        raise ValueError("approved edited stage path differs")
    return resolved


@contextmanager
def _approved_stage_run_lock(run_dir: Path) -> Any:
    with (run_dir / ".approved-stage.lock").open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
def _approved_stage_terminal_owner(
    *, run_dir: Path, kind: str, queue_state: dict[str, Any],
    root_candidate: dict[str, Any], root_review: dict[str, Any],
    expected_root_candidate_sha256: str, expected_root_review_sha256: str,
    terminal_generation: int | None, expected_continuation_state_sha256: str | None,
    terminal_attempt: int | None, replacement_of: str | None,
    replacement_reason: str | None, expected_replacement_state_sha256: str | None,
) -> dict[str, Any]:
    common = {
        "kind": kind,
        "root_candidate_sha256": expected_root_candidate_sha256,
        "root_review_sha256": expected_root_review_sha256,
    }
    if kind == "continuation_generation":
        if any(value is not None for value in (
            terminal_attempt, replacement_of, replacement_reason, expected_replacement_state_sha256
        )):
            raise ValueError("approved stage terminal owner fields are mixed")
        if type(terminal_generation) is not int or type(terminal_generation) is bool or terminal_generation < 1:
            raise ValueError("approved edited stage terminal generation is invalid")
        continuation_path = run_dir / "continuation" / "state.json"
        expected_continuation = _require_sha256_digest(
            expected_continuation_state_sha256, "continuation stage lock"
        )
        continuation = json.loads(continuation_path.read_text(encoding="utf-8"))
        if (
            _file_sha256(continuation_path) != expected_continuation
            or continuation.get("status") != "complete"
            or continuation.get("next_generation") != terminal_generation + 1
            or continuation.get("terminal_candidate_sha256") != _json_sha256(root_candidate)
            or continuation.get("terminal_review_sha256") != _json_sha256(root_review)
            or (run_dir / "generations" / f"{terminal_generation + 1:02d}").exists()
        ):
            raise ValueError("terminal continuation state differs")
        generation_dir = run_dir / "generations" / f"{terminal_generation:02d}"
        if (
            _file_sha256(generation_dir / "candidate.json") != expected_root_candidate_sha256
            or _file_sha256(generation_dir / "review.json") != expected_root_review_sha256
            or not all(item["verdict"] == "REJECT" and item.get("hard_failure") is True
                       and item.get("findings") for item in root_review["articles"])
        ):
            raise ValueError("terminal generation audit differs from root audit")
        return {
            **common,
            "terminal_audit_tree_sha256": _tree_sha256(generation_dir),
            "terminal_generation": terminal_generation,
            "continuation_state_sha256": expected_continuation,
            "terminal_generation_candidate_sha256": expected_root_candidate_sha256,
            "terminal_generation_review_sha256": expected_root_review_sha256,
        }
    if kind != "replacement_attempt":
        raise ValueError("approved stage terminal owner kind is invalid")
    if terminal_generation is not None or expected_continuation_state_sha256 is not None:
        raise ValueError("approved stage terminal owner fields are mixed")
    if terminal_attempt != 3 or not replacement_of or not replacement_reason:
        raise ValueError("replacement attempt authority is invalid")
    replacement_state_sha256 = _require_sha256_digest(
        expected_replacement_state_sha256, "replacement state lock"
    )
    if (
        queue_state.get("replacement_of") != replacement_of
        or queue_state.get("replacement_reason") != replacement_reason
        or (run_dir / "continuation").exists()
        or (run_dir / "generations").exists()
    ):
        raise ValueError("replacement attempt lineage differs")
    attempts_root = run_dir / "attempts"
    attempt_dirs = sorted(path.name for path in attempts_root.iterdir() if path.is_dir())
    terminal_dir = attempts_root / "03"
    if (
        attempt_dirs != ["01", "02", "03"]
        or _file_sha256(terminal_dir / "candidate.json") != expected_root_candidate_sha256
        or _file_sha256(terminal_dir / "review.json") != expected_root_review_sha256
        or any(item.get("verdict") != "REJECT" or not item.get("findings")
               or item.get("hard_failure") is True for item in root_review["articles"])
    ):
        raise ValueError("replacement attempt terminal audit differs")
    return {
        **common,
        "terminal_audit_tree_sha256": _tree_sha256(attempts_root),
        "terminal_attempt": 3,
        "replacement_of": replacement_of,
        "replacement_reason": replacement_reason,
        "replacement_state_sha256": replacement_state_sha256,
        "terminal_attempt_candidate_sha256": expected_root_candidate_sha256,
        "terminal_attempt_review_sha256": expected_root_review_sha256,
    }
def _locale_replacement_plan(
    repo_root: Path, descriptor: dict[str, Any], article: dict[str, Any], run_id: str,
) -> tuple[Path, bytes]:
    keys = set("contract source_article_id locale old_run_id old_source_sha256 old_record_sha256 module_path module_export record_index module_before_sha256 module_after_sha256 manifest_path manifest_sha256 replacement_run_id replacement_source_sha256 approved_article_sha256 replacement_record_sha256".split())
    if not isinstance(descriptor, dict) or set(descriptor) != keys or descriptor.get("contract") != "approved-locale-existing-record-replacement":
        raise ValueError("public replacement descriptor is invalid")
    if descriptor.get("replacement_run_id") != run_id or descriptor.get("source_article_id") != article.get("source_article_id") or descriptor.get("locale") != article.get("locale") or descriptor.get("replacement_source_sha256") != article.get("source_sha256") or descriptor.get("approved_article_sha256") != pipeline.article_sha256(article):
        raise ValueError("public replacement identity differs")
    relative = Path(str(descriptor["module_path"])); manifest_relative = Path(str(descriptor["manifest_path"]))
    if relative.is_absolute() or ".." in relative.parts or relative.parts[:3] != ("app", "web", "static") or manifest_relative.as_posix() != "app/web/static/article-locales.js":
        raise ValueError("public replacement path differs")
    module = repo_root / relative; manifest = repo_root / manifest_relative
    for path in (module, manifest):
        if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != repo_root.resolve(strict=True).joinpath(*path.relative_to(repo_root).parts):
            raise ValueError("public replacement path is not canonical")
    before = module.read_bytes(); manifest_bytes = manifest.read_bytes()
    current_module_sha = hashlib.sha256(before).hexdigest()
    if current_module_sha not in {descriptor["module_before_sha256"], descriptor["module_after_sha256"]} or hashlib.sha256(manifest_bytes).hexdigest() != descriptor["manifest_sha256"]:
        raise ValueError("public replacement module or manifest drift")
    prefix = b"// AGY \xe6\xa0\xb8\xe5\x87\x86\xe5\xa4\x9a\xe8\xaa\x9e\xe6\x96\x87\xe7\xab\xa0\xef\xbc\x9b\xe7\x94\xb1 scripts/agy_multilingual_pipeline.py \xe7\x94\xa2\xe7\x94\x9f\xe3\x80\x82\n\n"
    pattern = re.compile(rb"export const ([A-Z][A-Z0-9_]*) = (\[.*\]);\n", re.DOTALL)
    match = pattern.fullmatch(before[len(prefix):]) if before.startswith(prefix) else None
    if match is None or match.group(1).decode() != descriptor["module_export"]:
        raise ValueError("public replacement module grammar differs")
    records = json.loads(match.group(2)); rendered = prefix + f"export const {descriptor['module_export']} = {json.dumps(records, ensure_ascii=False, indent=2)};\n".encode()
    if rendered != before or not isinstance(records, list):
        raise ValueError("public replacement module grammar differs")
    identity = (str(descriptor["source_article_id"]), str(descriptor["locale"])); index = descriptor["record_index"]
    matches = [i for i, item in enumerate(records) if (str(item.get("articleId")), str(item.get("locale"))) == identity]
    inventory = [item for item in _locale_inventory(repo_root) if (str(item.get("articleId")), str(item.get("locale"))) == identity]
    expected_inventory_run = descriptor["replacement_run_id"] if current_module_sha == descriptor["module_after_sha256"] else descriptor["old_run_id"]
    expected_inventory_source = descriptor["replacement_source_sha256"] if current_module_sha == descriptor["module_after_sha256"] else descriptor["old_source_sha256"]
    if matches != [index] or len(inventory) != 1 or inventory[0].get("runId") != expected_inventory_run or inventory[0].get("sourceSha256") != expected_inventory_source:
        raise ValueError("public replacement owner is ambiguous")
    old = records[index]
    replacement = {"runId": run_id, "articleId": article["source_article_id"], "locale": article["locale"], "sourcePath": article["source_path"], "sourceSha256": article["source_sha256"], **{field: article[field] for field in sorted(TRANSLATABLE_FIELDS)}}
    expected_current_record = descriptor["replacement_record_sha256"] if current_module_sha == descriptor["module_after_sha256"] else descriptor["old_record_sha256"]
    if hashlib.sha256(compact_json_bytes(old)).hexdigest() != expected_current_record or hashlib.sha256(compact_json_bytes(replacement)).hexdigest() != descriptor["replacement_record_sha256"]:
        raise ValueError("public replacement record drift")
    if current_module_sha == descriptor["module_after_sha256"]:
        return module, before
    records[index] = replacement
    after = prefix + f"export const {descriptor['module_export']} = {json.dumps(records, ensure_ascii=False, indent=2)};\n".encode()
    if hashlib.sha256(after).hexdigest() != descriptor["module_after_sha256"]:
        raise ValueError(f"public replacement after digest differs: {hashlib.sha256(after).hexdigest()}")
    return module, after
def plan_approved_edited_candidate_stage(
    *,
    repo_root: Path, run_dir: Path,
    approved_candidate_path: Path, approved_review_path: Path,
    formal_review_result_path: Path, queue_state_path: Path, publisher_ledger_path: Path,
    expected_run_id: str, terminal_owner_kind: str,
    expected_approved_article_sha256: str, expected_root_candidate_sha256: str,
    expected_root_review_sha256: str,
    expected_queue_state_sha256: str, expected_publisher_ledger_sha256: str,
    terminal_generation: int | None = None, expected_continuation_state_sha256: str | None = None,
    terminal_attempt: int | None = None, replacement_of: str | None = None,
    replacement_reason: str | None = None, expected_replacement_state_sha256: str | None = None,
    public_replacement: dict[str, Any] | None = None,
    expected_approved_candidate_sha256: str | None = None, expected_approved_review_sha256: str | None = None,
    expected_formal_review_result_sha256: str | None = None, expected_source_sha256: str | None = None,
    expected_actor_sha: str | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    required_hashes = (expected_approved_article_sha256, expected_root_candidate_sha256,
                       expected_root_review_sha256, expected_queue_state_sha256,
                       expected_publisher_ledger_sha256)
    optional_hashes = (expected_approved_candidate_sha256, expected_approved_review_sha256,
                       expected_formal_review_result_sha256, expected_source_sha256)
    for value in required_hashes:
        _require_sha256_digest(value, "stage lock")
    for value in optional_hashes:
        if value is not None:
            _require_sha256_digest(value, "optional stage lock")
    if expected_actor_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", expected_actor_sha):
        raise ValueError("actor hash is invalid")
    if expected_run_id.strip() != expected_run_id or not expected_run_id:
        raise ValueError("approved edited stage run id is invalid")
    formal_job_identity_path = formal_review_result_path.parent / "formal-request-identity.json"
    input_paths = (run_dir / "brief.json", run_dir / "candidate.json", run_dir / "review.json",
                   approved_candidate_path, approved_review_path, formal_review_result_path,
                   queue_state_path, publisher_ledger_path, formal_job_identity_path)
    (brief, root_candidate, root_review, approved_candidate, approved_review, formal_result,
     queue_state, publisher_ledger, formal_job_identity) = (
        json.loads(path.read_text(encoding="utf-8")) for path in input_paths
    )

    brief = _normalize_registered_translation_brief(brief, run_dir)
    validate_translation_candidate(brief, root_candidate)
    validate_translation_candidate(brief, approved_candidate)
    pipeline.validate_review(root_review, root_candidate["articles"])
    pipeline.validate_review(approved_review, approved_candidate["articles"])
    approved_article_sha256 = pipeline.article_sha256(approved_candidate["articles"][0])
    _validate_approved_stage_formal_identity(formal_job_identity, formal_result, approved_review,
                                             expected_run_id, approved_article_sha256)
    if any(item.get("run_id") != expected_run_id for item in
           (brief, root_candidate, root_review, approved_candidate, approved_review)):
        raise ValueError("approved edited stage run identity differs")
    if approved_article_sha256 != expected_approved_article_sha256:
        raise ValueError("approved article identity differs")
    if expected_source_sha256 is not None and brief["articles"][0]["source_sha256"] != expected_source_sha256:
        raise ValueError("source identity differs")
    current_paths = (run_dir / "candidate.json", run_dir / "review.json",
                     queue_state_path, publisher_ledger_path)
    current_expected = (expected_root_candidate_sha256, expected_root_review_sha256,
                        expected_queue_state_sha256, expected_publisher_ledger_sha256)
    approved_paths = (approved_candidate_path, approved_review_path, formal_review_result_path)
    approved_expected = (expected_approved_candidate_sha256, expected_approved_review_sha256,
                         expected_formal_review_result_sha256)
    if any(_file_sha256(path) != digest for path, digest in zip(current_paths, current_expected)):
        raise ValueError("current stage lock differs")
    approved_hashes = tuple(_file_sha256(path) for path in approved_paths)
    if any(expected is not None and actual != expected for actual, expected in zip(approved_hashes, approved_expected)):
        raise ValueError("approved input lock differs")
    if (queue_state.get("run_id") != expected_run_id or queue_state.get("status") != "complete"
            or queue_state.get("run_dir") != str(run_dir)):
        raise ValueError("queue state identity differs")
    if any(
        item.get("run_id") == expected_run_id
        for key in ("translation_published_runs", "translation_deferred_runs")
        for item in publisher_ledger.get(key, [])
        if isinstance(item, dict)
    ):
        raise ValueError("publisher ledger lifecycle is not stageable")
    terminal_owner = _approved_stage_terminal_owner(
        run_dir=run_dir, kind=terminal_owner_kind, queue_state=queue_state,
        root_candidate=root_candidate, root_review=root_review,
        expected_root_candidate_sha256=expected_root_candidate_sha256,
        expected_root_review_sha256=expected_root_review_sha256,
        terminal_generation=terminal_generation,
        expected_continuation_state_sha256=expected_continuation_state_sha256,
        terminal_attempt=terminal_attempt, replacement_of=replacement_of,
        replacement_reason=replacement_reason,
        expected_replacement_state_sha256=expected_replacement_state_sha256,
    )
    if terminal_owner_kind == "replacement_attempt":
        if public_replacement is None:
            raise ValueError("replacement stage requires public replacement descriptor")
        _locale_replacement_plan(repo_root, public_replacement, approved_candidate["articles"][0], expected_run_id)
    elif public_replacement is not None:
        raise ValueError("continuation stage rejects public replacement descriptor")

    try:
        actor_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        actor_sha = "0" * 40
    if re.fullmatch(r"[0-9a-f]{40}", actor_sha) is None:
        raise ValueError("actor identity is invalid")
    if expected_actor_sha is not None and actor_sha != expected_actor_sha:
        raise ValueError("actor identity differs")
    identity = {
        "schema_version": SCHEMA_VERSION, "contract": "approved-edited-candidate-stage",
        "run_id": expected_run_id, "terminal_owner": terminal_owner,
        **({"public_replacement": public_replacement} if public_replacement is not None else {}),
        "source_sha256": brief["articles"][0]["source_sha256"], "actor_sha": actor_sha,
        "approved_article_sha256": approved_article_sha256,
        "queue_state_sha256": expected_queue_state_sha256, "publisher_ledger_sha256": expected_publisher_ledger_sha256,
        "approved_candidate_file_sha256": approved_hashes[0], "approved_review_file_sha256": approved_hashes[1],
        "formal_review_result_sha256": approved_hashes[2], "formal_job_identity_sha256": _file_sha256(formal_job_identity_path),
        "formal_job_identity_content_sha256": _json_sha256(formal_job_identity),
        "formal_job_id": formal_job_identity["job_id"], "formal_request_sha256": formal_job_identity["request_sha256"],
    }
    operation_id = f"approved-edit-stage-{_json_sha256(identity)[:24]}"
    operation_dir = run_dir / "editorial-staging" / operation_id
    plan = {
        **identity, "status": "READY_TO_EXECUTE", "operation_id": operation_id,
        "operation_dir": str(operation_dir), "payload_path": str(operation_dir / "payload.json"),
        "receipt_path": str(operation_dir / "receipt.json"),
        "rollback_receipt_path": str(operation_dir / "rollback-receipt.json"),
        "current_seal_path": str(run_dir / "editorial-staging" / "current.json"), "provider_calls": 0,
    }
    plan = {**plan, "plan_digest": _json_sha256(plan)}
    current_path = _approved_stage_path(run_dir, "current.json", must_exist=False)
    if not current_path.exists():
        return plan
    current = json.loads(current_path.read_text(encoding="utf-8"))
    loaded = load_approved_edited_candidate_stage(run_dir)
    if loaded["plan_digest"] == plan["plan_digest"]:
        return {**plan, "status": "ALREADY_STAGED"}
    raise ValueError("approved edited stage current seal conflicts")


def apply_approved_edited_candidate_stage(
    *,
    repo_root: Path, run_dir: Path,
    approved_candidate_path: Path, approved_review_path: Path,
    formal_review_result_path: Path, queue_state_path: Path, publisher_ledger_path: Path,
    expected_run_id: str, terminal_owner_kind: str,
    expected_approved_article_sha256: str, expected_root_candidate_sha256: str,
    expected_root_review_sha256: str,
    expected_queue_state_sha256: str, expected_publisher_ledger_sha256: str, expected_plan_digest: str,
    terminal_generation: int | None = None, expected_continuation_state_sha256: str | None = None,
    terminal_attempt: int | None = None, replacement_of: str | None = None,
    replacement_reason: str | None = None, expected_replacement_state_sha256: str | None = None,
    public_replacement: dict[str, Any] | None = None,
    expected_approved_candidate_sha256: str | None = None, expected_approved_review_sha256: str | None = None,
    expected_formal_review_result_sha256: str | None = None, expected_source_sha256: str | None = None,
    expected_actor_sha: str | None = None,
) -> dict[str, Any]:
    inputs = dict(locals())
    expected_plan_digest = _require_sha256_digest(inputs.pop("expected_plan_digest"), "plan digest")
    stage_lock = _continuation_run_lock if terminal_owner_kind == "continuation_generation" else _approved_stage_run_lock
    with stage_lock(run_dir):
        plan = plan_approved_edited_candidate_stage(**inputs)
        if plan["plan_digest"] != expected_plan_digest:
            raise ValueError("approved edited stage plan digest differs")
        if plan["status"] == "ALREADY_STAGED":
            return plan
        run_dir = run_dir.resolve(strict=True)
        operation_dir = _approved_stage_path(run_dir, plan["operation_id"], must_exist=False,
                                             directory=True, create_root=True)
        current_path = _approved_stage_path(run_dir, "current.json", must_exist=False, create_root=True)
        prior_current = current_path.read_bytes() if current_path.is_file() else None
        payload = {
            "schema_version": SCHEMA_VERSION, "contract": "approved-edited-candidate-stage-payload",
            "operation_id": plan["operation_id"], "plan_digest": plan["plan_digest"],
            "candidate": json.loads(approved_candidate_path.read_text(encoding="utf-8")),
            "review": json.loads(approved_review_path.read_text(encoding="utf-8")),
            "formal_review_result": json.loads(formal_review_result_path.read_text(encoding="utf-8")),
            "formal_job_identity": json.loads((formal_review_result_path.parent / "formal-request-identity.json").read_text(encoding="utf-8")),
        }
        rollback_receipt = {
            "schema_version": SCHEMA_VERSION, "contract": "approved-edited-candidate-stage-rollback",
            "operation_id": plan["operation_id"], "plan_digest": plan["plan_digest"],
            "current_seal_path": str(current_path), "operation_dir": str(operation_dir),
            "prior_current_pointer_sha256": _bytes_sha256(prior_current),
            "prior_current_pointer_text": prior_current.decode("utf-8") if prior_current is not None else None,
        }
        receipt = {
            **plan, "status": "STAGED",
            "payload_sha256": hashlib.sha256(compact_json_bytes(payload) + b"\n").hexdigest(),
            "rollback_receipt_sha256": hashlib.sha256(compact_json_bytes(rollback_receipt) + b"\n").hexdigest(),
            "current_pointer_before_sha256": _bytes_sha256(prior_current),
            "created_paths": [str(operation_dir / name) for name in
                              ("payload.json", "receipt.json", "rollback-receipt.json")] + [str(current_path)],
        }
        if operation_dir.exists():
            loaded = _load_approved_edited_candidate_stage_record(run_dir, receipt, require_current=False)
            _atomic_write_json(current_path, receipt)
            return {**receipt, "recovered_current_pointer": True, "receipt_sha256": loaded["receipt_sha256"]}
        temporary_dir = Path(tempfile.mkdtemp(prefix=f".{plan['operation_id']}.", dir=operation_dir.parent))
        try:
            _atomic_write_json(temporary_dir / "payload.json", payload)
            _atomic_write_json(temporary_dir / "rollback-receipt.json", rollback_receipt)
            _atomic_write_json(temporary_dir / "receipt.json", receipt)
            os.replace(temporary_dir, operation_dir)
        finally:
            if temporary_dir.exists():
                shutil.rmtree(temporary_dir)
        _atomic_write_json(current_path, receipt)
        return receipt


def _load_approved_edited_candidate_stage_record(
    run_dir: Path,
    seal: dict[str, Any],
    *,
    require_current: bool,
) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    if not isinstance(seal, dict): raise ValueError("approved edited stage current seal is invalid")
    required = set("schema_version contract status operation_id operation_dir payload_path receipt_path rollback_receipt_path current_seal_path plan_digest payload_sha256 rollback_receipt_sha256 run_id provider_calls terminal_owner formal_job_identity_sha256 formal_job_identity_content_sha256 formal_job_id formal_request_sha256".split())
    if (set(seal) != required | set("actor_sha approved_article_sha256 approved_candidate_file_sha256 approved_review_file_sha256 created_paths current_pointer_before_sha256 formal_review_result_sha256 publisher_ledger_sha256 queue_state_sha256 source_sha256".split()) | ({"public_replacement"} if "public_replacement" in seal else set())
            or seal.get("schema_version") != SCHEMA_VERSION or seal.get("contract") != "approved-edited-candidate-stage"
            or seal.get("status") != "STAGED" or seal.get("provider_calls") != 0):
        raise ValueError("approved edited stage current seal is invalid")
    plan = {
        key: value
        for key, value in {**seal, "status": "READY_TO_EXECUTE"}.items()
        if key not in {"plan_digest", "payload_sha256", "rollback_receipt_sha256", "current_pointer_before_sha256", "created_paths"}
    }
    if _json_sha256(plan) != seal["plan_digest"]:
        raise ValueError("approved edited stage plan digest drift")
    operation_id = str(seal["operation_id"])
    if re.fullmatch(r"approved-edit-stage-[0-9a-f]{24}", operation_id) is None:
        raise ValueError("approved edited stage operation identity differs")
    operation_dir = _approved_stage_path(run_dir, operation_id, directory=True)
    payload_path = _approved_stage_path(run_dir, f"{operation_id}/payload.json")
    receipt_path = _approved_stage_path(run_dir, f"{operation_id}/receipt.json")
    rollback_path = _approved_stage_path(run_dir, f"{operation_id}/rollback-receipt.json")
    current_path = _approved_stage_path(run_dir, "current.json") if require_current else None
    expected_paths = {"operation_dir": operation_dir, "payload_path": payload_path,
                      "receipt_path": receipt_path, "rollback_receipt_path": rollback_path,
                      "current_seal_path": run_dir / "editorial-staging" / "current.json"}
    if any(Path(str(seal[key])) != path for key, path in expected_paths.items()):
        raise ValueError("approved edited stage paths differ")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt != seal or (current_path is not None and current_path.read_bytes() != receipt_path.read_bytes())
            or _file_sha256(payload_path) != seal["payload_sha256"]
            or _file_sha256(rollback_path) != seal["rollback_receipt_sha256"]):
        raise ValueError("approved edited stage record digest differs")
    candidate = payload.get("candidate")
    review = payload.get("review")
    formal_result = payload.get("formal_review_result")
    formal_job_identity = payload.get("formal_job_identity")
    brief = _load_registered_translation_brief(run_dir)
    if not all(isinstance(item, dict) for item in (candidate, review, formal_result, formal_job_identity)):
        raise ValueError("approved edited stage payload is invalid")
    validate_translation_candidate(brief, candidate)
    pipeline.validate_review(review, candidate["articles"])
    approved_article_sha256 = pipeline.article_sha256(candidate["articles"][0])
    _validate_approved_stage_formal_identity(formal_job_identity, formal_result, review,
                                             str(seal["run_id"]), approved_article_sha256)
    if (_json_sha256(formal_job_identity) != seal["formal_job_identity_content_sha256"]
            or formal_job_identity["job_id"] != seal["formal_job_id"]
            or formal_job_identity["request_sha256"] != seal["formal_request_sha256"]):
        raise ValueError("approved edited stage formal job identity differs")
    if approved_article_sha256 != seal["approved_article_sha256"]:
        raise ValueError("approved edited stage article digest differs")
    terminal_owner = seal.get("terminal_owner")
    common_owner_keys = set("kind root_candidate_sha256 root_review_sha256 terminal_audit_tree_sha256".split())
    continuation_keys = common_owner_keys | set("terminal_generation continuation_state_sha256 terminal_generation_candidate_sha256 terminal_generation_review_sha256".split())
    replacement_keys = common_owner_keys | set("terminal_attempt replacement_of replacement_reason replacement_state_sha256 terminal_attempt_candidate_sha256 terminal_attempt_review_sha256".split())
    if not isinstance(terminal_owner, dict):
        raise ValueError("approved edited stage terminal owner is invalid")
    kind = terminal_owner.get("kind")
    expected_owner_keys = continuation_keys if kind == "continuation_generation" else replacement_keys
    if kind not in {"continuation_generation", "replacement_attempt"} or set(terminal_owner) != expected_owner_keys:
        raise ValueError("approved edited stage terminal owner is invalid")
    if (kind == "replacement_attempt") != ("public_replacement" in seal):
        raise ValueError("approved edited stage public replacement owner differs")
    current_locks = [
        (run_dir / "candidate.json", terminal_owner["root_candidate_sha256"]),
        (run_dir / "review.json", terminal_owner["root_review_sha256"]),
    ]
    if kind == "continuation_generation":
        terminal_number = int(terminal_owner["terminal_generation"])
        audit_dir = run_dir / "generations" / f"{terminal_number:02d}"
        current_locks.extend((
            (run_dir / "continuation" / "state.json", terminal_owner["continuation_state_sha256"]),
            (audit_dir / "candidate.json", terminal_owner["terminal_generation_candidate_sha256"]),
            (audit_dir / "review.json", terminal_owner["terminal_generation_review_sha256"]),
        ))
    else:
        if terminal_owner.get("terminal_attempt") != 3:
            raise ValueError("approved edited stage terminal owner is invalid")
        audit_dir = run_dir / "attempts"
        terminal_dir = audit_dir / "03"
        current_locks.extend((
            (terminal_dir / "candidate.json", terminal_owner["terminal_attempt_candidate_sha256"]),
            (terminal_dir / "review.json", terminal_owner["terminal_attempt_review_sha256"]),
        ))
    if any(_file_sha256(path) != expected for path, expected in current_locks):
        raise ValueError("approved edited stage terminal audit drift")
    if _tree_sha256(audit_dir) != terminal_owner["terminal_audit_tree_sha256"]:
        raise ValueError("approved edited stage terminal audit tree drift")
    if brief.get("run_id") != seal["run_id"] or brief["articles"][0]["source_sha256"] != seal["source_sha256"]:
        raise ValueError("approved edited stage source identity differs")
    return {"seal": seal, "candidate": candidate, "review": review,
            "formal_review_result": formal_result, "plan_digest": seal["plan_digest"],
            "receipt_sha256": _file_sha256(receipt_path), "payload_sha256": seal["payload_sha256"]}


def load_approved_edited_candidate_stage(run_dir: Path) -> dict[str, Any]:
    current_path = _approved_stage_path(run_dir, "current.json")
    seal = json.loads(current_path.read_text(encoding="utf-8"))
    if not isinstance(seal, dict):
        raise ValueError("approved edited stage current seal is invalid")
    return _load_approved_edited_candidate_stage_record(run_dir, seal, require_current=True)


def rollback_approved_edited_candidate_stage(run_dir: Path, operation_id: str) -> dict[str, Any]:
    seal = json.loads(_approved_stage_path(run_dir, "current.json").read_text(encoding="utf-8"))
    stage_lock = _continuation_run_lock if seal.get("terminal_owner", {}).get("kind") == "continuation_generation" else _approved_stage_run_lock
    with stage_lock(run_dir):
        run_dir = run_dir.resolve(strict=True)
        loaded = load_approved_edited_candidate_stage(run_dir)
        current = loaded["seal"]
        if current is None or current.get("operation_id") != operation_id:
            raise ValueError("approved edited stage rollback target differs")
        current_path = _approved_stage_path(run_dir, "current.json")
        operation_dir = _approved_stage_path(run_dir, operation_id, directory=True)
        rollback_path = _approved_stage_path(run_dir, f"{operation_id}/rollback-receipt.json")
        rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
        if (
            rollback.get("operation_id") != operation_id
            or rollback.get("current_seal_path") != str(current_path)
            or rollback.get("operation_dir") != str(operation_dir)
            or rollback.get("plan_digest") != current.get("plan_digest")
        ):
            raise ValueError("approved edited stage rollback receipt differs")
        prior_text = rollback.get("prior_current_pointer_text")
        prior_bytes = prior_text.encode("utf-8") if isinstance(prior_text, str) else None
        if _bytes_sha256(prior_bytes) != rollback.get("prior_current_pointer_sha256"):
            raise ValueError("approved edited stage prior pointer digest differs")
        if prior_bytes is None:
            current_path.unlink()
        else:
            _atomic_write_bytes(current_path, prior_bytes)
        shutil.rmtree(operation_dir)
        return {"schema_version": SCHEMA_VERSION, "status": "ROLLED_BACK",
                "operation_id": operation_id, "restored_prior_current": prior_bytes is not None}


def _load_generation_authority_artifacts(
    run_dir: Path,
    brief: dict[str, Any],
    generation: int,
) -> dict[str, Any]:
    directory = run_dir / "generations" / f"{generation:02d}"
    names = {
        "candidate": "candidate.json",
        "review": "review.json",
        "locale_plan": "locale-plan.json",
        "source_ref_map": "source-ref-map.json",
        "deterministic_findings": "deterministic-findings.json",
    }
    paths = {name: directory / filename for name, filename in names.items()}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"terminal {missing[0].replace('_', ' ')} artifact is missing")
    artifacts = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    validate_translation_candidate(brief, artifacts["candidate"])
    pipeline.validate_review(artifacts["review"], artifacts["candidate"]["articles"])
    validate_locale_plan(brief, artifacts["locale_plan"])
    _validate_source_ref_maps_against_current_package(
        brief,
        _source_ref_maps_from_artifact(artifacts["source_ref_map"], generation=generation),
    )
    if not isinstance(artifacts["deterministic_findings"], list):
        raise ValueError("terminal deterministic findings artifact is invalid")
    return artifacts


def _review_finding_codes(review: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(article["article_id"]), str(finding["code"]))
        for article in review["articles"]
        for finding in article["findings"]
    }


def _validate_terminal_transition_receipt(
    receipt: object,
    expected: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ValueError("terminal authority transition identity differs")
    required = {"schema_version": SCHEMA_VERSION, "contract": "continuation-authority-transition", "action": "authorize_next_generation_after_reviewer_reject", **expected}
    if any(receipt.get(key) != value for key, value in required.items()):
        raise ValueError("terminal authority transition identity differs")
    for key in ("state_before_sha256", "state_after_sha256"):
        _require_sha256_digest(receipt.get(key), key)
    state_after = receipt.get("state_after")
    if not isinstance(state_after, dict) or _json_sha256(state_after) != receipt["state_after_sha256"]:
        raise ValueError("terminal authority transition identity differs")
    return receipt


def _authorize_next_generation_after_reviewer_reject_unlocked(
    run_dir: Path,
    *,
    expected_run_id: str,
    terminal_generation: int,
    expected_source_sha256: str,
    expected_locale_plan_sha256: str,
    expected_source_ref_map_sha256: str,
    expected_terminal_candidate_sha256: str,
    expected_terminal_review_sha256: str,
    authority_digest: str,
    execute: bool = False,
) -> dict[str, Any]:
    """正式授權 terminal Reviewer REJECT 後建立下一代，不直接產生內容。"""
    expected_source_sha256, expected_locale_plan_sha256, expected_source_ref_map_sha256, expected_terminal_candidate_sha256, expected_terminal_review_sha256, authority_digest = (
        _require_sha256_digest(value, label)
        for value, label in ((expected_source_sha256, "source hash"), (expected_locale_plan_sha256, "locale plan hash"), (expected_source_ref_map_sha256, "source ref map hash"), (expected_terminal_candidate_sha256, "terminal candidate hash"), (expected_terminal_review_sha256, "terminal review hash"), (authority_digest, "authority digest"))
    )
    brief = _load_registered_translation_brief(run_dir)
    expected = dict(run_id=expected_run_id, terminal_generation=terminal_generation, from_status="complete", to_status="active", to_next_generation=terminal_generation + 1, source_sha256=expected_source_sha256, locale_plan_sha256=expected_locale_plan_sha256, source_ref_map_sha256=expected_source_ref_map_sha256, terminal_candidate_sha256=expected_terminal_candidate_sha256, terminal_review_sha256=expected_terminal_review_sha256, authority_digest=authority_digest)
    transition_path = _authority_transition_path(run_dir, terminal_generation)
    if transition_path.is_file():
        transition = _validate_terminal_transition_receipt(
            json.loads(transition_path.read_text(encoding="utf-8")),
            expected,
        )
        state_path = run_dir / "continuation" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state_sha256 = _json_sha256(state)
        if execute and state_sha256 == transition["state_before_sha256"]:
            _atomic_write_json(state_path, transition["state_after"])
            return {**transition, "status": "AUTHORIZED", "execute": True}
        if state_sha256 == transition["state_after_sha256"]:
            return {**transition, "status": "ALREADY_AUTHORIZED", "execute": execute}
        raise ValueError("authorization already consumed/state progressed")
    if expected_run_id != brief["run_id"] or terminal_generation < 1:
        raise ValueError("terminal authority identity differs")
    if len(brief["articles"]) != 1:
        raise ValueError("terminal rejected next generation supports one article")
    if str(brief["articles"][0]["source_sha256"]) != expected_source_sha256:
        raise ValueError("source identity differs")
    if (run_dir / "continuation" / "root-update.json").exists():
        raise ValueError("root update residue is not supported")
    next_dir = run_dir / "generations" / f"{expected['to_next_generation']:02d}"
    if next_dir.exists():
        raise ValueError("authorization already consumed/state progressed")
    state_path = run_dir / "continuation" / "state.json"
    if not state_path.is_file():
        raise ValueError("continuation state is missing")
    root_candidate, root_review = (
        json.loads((run_dir / name).read_text(encoding="utf-8"))
        for name in ("candidate.json", "review.json")
    )
    validate_translation_candidate(brief, root_candidate)
    pipeline.validate_review(root_review, root_candidate["articles"])
    state = _load_or_create_continuation_state(
        run_dir,
        brief,
        root_review,
        max_repairs=2,
    )
    if any((state.get("status") != "complete", state.get("next_generation") != expected["to_next_generation"], state.get("completed_generations") not in ([], [terminal_generation]), state.get("terminal_candidate_sha256") != expected_terminal_candidate_sha256, state.get("terminal_review_sha256") != expected_terminal_review_sha256, _json_sha256(root_candidate) != expected_terminal_candidate_sha256, _json_sha256(root_review) != expected_terminal_review_sha256)):
        raise ValueError("terminal rejected state identity differs")
    terminal = _load_generation_authority_artifacts(run_dir, brief, terminal_generation)
    if any(
        _json_sha256(terminal[artifact]) != expected[key]
        for artifact, key in (
            ("candidate", "terminal_candidate_sha256"),
            ("review", "terminal_review_sha256"),
            ("locale_plan", "locale_plan_sha256"),
            ("source_ref_map", "source_ref_map_sha256"),
        )
    ):
        raise ValueError("terminal generation artifact identity differs")
    if (run_dir / "published.json").exists():
        raise ValueError("published residue is not supported")
    if not all(
        item["verdict"] == "REJECT"
        and item.get("hard_failure") is True
        and item.get("findings")
        for item in root_review["articles"]
    ):
        raise ValueError("terminal review must be rejected hard failure")
    deterministic_codes = {
        (str(item.get("article_id")), str(item.get("code")))
        for item in terminal["deterministic_findings"]
        if isinstance(item, dict)
    }
    if not deterministic_codes or not deterministic_codes <= _review_finding_codes(root_review):
        raise ValueError("deterministic hard failure is invalid")
    abandoned = list(state.get("abandoned_generations", []))
    required_budget = int(state["next_generation"]) - int(state["started_after_generation"]) - len(abandoned)
    updated_budget = max(int(state["semantic_budget"]), required_budget)
    if updated_budget > 3:
        raise ValueError("terminal rejected next generation exceeds semantic budget")
    updated = {
        **state,
        "operation_id": _continuation_operation_id(brief, expected_terminal_review_sha256, state["started_after_generation"]),
        "starting_review_sha256": expected_terminal_review_sha256,
        "terminal_candidate_sha256": None,
        "terminal_review_sha256": None,
        "semantic_budget": updated_budget,
        "status": "active",
    }
    transition = {**expected, "schema_version": SCHEMA_VERSION, "contract": "continuation-authority-transition", "action": "authorize_next_generation_after_reviewer_reject", "from_next_generation": state["next_generation"], "from_semantic_budget": state["semantic_budget"], "to_semantic_budget": updated["semantic_budget"], "from_operation_id": state["operation_id"], "to_operation_id": updated["operation_id"], "completed_generations": updated["completed_generations"], "abandoned_generations": updated["abandoned_generations"], "state_before_sha256": _json_sha256(state), "state_after_sha256": _json_sha256(updated), "state_after": updated}
    if not execute:
        return {**transition, "status": "READY_TO_EXECUTE", "execute": False}
    _write_if_same_or_missing(transition_path, transition)
    _atomic_write_json(run_dir / "continuation" / "state.json", updated)
    return {**transition, "status": "AUTHORIZED", "execute": True}


def authorize_next_generation_after_reviewer_reject(
    run_dir: Path,
    *,
    expected_run_id: str,
    terminal_generation: int,
    expected_source_sha256: str,
    expected_locale_plan_sha256: str,
    expected_source_ref_map_sha256: str,
    expected_terminal_candidate_sha256: str,
    expected_terminal_review_sha256: str,
    authority_digest: str,
    execute: bool = False,
) -> dict[str, Any]:
    context = _continuation_run_lock(run_dir) if execute else nullcontext()
    with context:
        return _authorize_next_generation_after_reviewer_reject_unlocked(
            run_dir,
            expected_run_id=expected_run_id,
            terminal_generation=terminal_generation,
            expected_source_sha256=expected_source_sha256,
            expected_locale_plan_sha256=expected_locale_plan_sha256,
            expected_source_ref_map_sha256=expected_source_ref_map_sha256,
            expected_terminal_candidate_sha256=expected_terminal_candidate_sha256,
            expected_terminal_review_sha256=expected_terminal_review_sha256,
            authority_digest=authority_digest,
            execute=execute,
        )


def _review_findings(review: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "article_id": str(item["article_id"]),
            "code": str(finding["code"]),
            "message": str(finding["message"]),
        }
        for item in review["articles"]
        for finding in item["findings"]
    ]


def _external_review_findings(
    brief: dict[str, Any],
    attempt_dir: Path,
) -> list[dict[str, str]]:
    path = attempt_dir / "external-review.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_slot = {
        str(item.get("slot")): item
        for item in payload.get("articles", [])
        if isinstance(item, dict)
    }
    findings = []
    for index, target in enumerate(brief["articles"]):
        item = by_slot.get(f"article-{index + 1:02d}", {})
        for finding in item.get("findings", []):
            if isinstance(finding, dict) and {"code", "message"} <= set(finding):
                findings.append(
                    {
                        "article_id": str(target["translation_id"]),
                        "code": str(finding["code"]),
                        "message": str(finding["message"]),
                    }
                )
    return findings


def _generation_directories(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and re.fullmatch(r"\d+", path.name)
        ),
        key=lambda path: int(path.name),
    )


def _finding_history(brief: dict[str, Any], roots: list[Path]) -> list[list[dict[str, str]]]:
    history = []
    for root in roots:
        for attempt_dir in _generation_directories(root):
            findings = _external_review_findings(brief, attempt_dir)
            if findings:
                history.append(findings)
    return history


def _rebuild_authority(
    brief: dict[str, Any],
    history: list[list[dict[str, str]]],
) -> dict[str, bool]:
    recent = []
    for findings in history[-2:]:
        current: dict[str, set[str]] = {}
        for finding in findings:
            current.setdefault(str(finding["article_id"]), set()).add(str(finding["code"]))
        recent.append(current)
    return {
        f"article-{index + 1:02d}": bool(
            (
                recent[0].get(str(target["translation_id"]), set())
                & recent[1].get(str(target["translation_id"]), set())
                if len(recent) == 2
                else set()
            )
            & REBUILD_FINDING_CODES
        )
        for index, target in enumerate(brief["articles"])
    }


def _last_locale_plan(
    roots: list[Path],
    *,
    before_generation: int,
) -> dict[str, Any] | None:
    paths = [
        attempt_dir / "locale-plan.json"
        for root in roots
        for attempt_dir in _generation_directories(root)
        if int(attempt_dir.name) < before_generation
        if (attempt_dir / "locale-plan.json").is_file()
    ]
    if not paths:
        return None
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def _candidate_outline_plan(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "articles": [
            {
                "slot": f"article-{index + 1:02d}",
                "ordered_h2_outline": [
                    section["heading"]
                    for section in article["bodySections"]
                ],
            }
            for index, article in enumerate(candidate["articles"])
        ]
    }


def _review_generated_candidate(
    brief: dict[str, Any],
    candidate: dict[str, Any],
    external_review: dict[str, Any],
    deterministic_findings: list[dict[str, str]],
) -> dict[str, Any]:
    review = pipeline.hydrate_review(brief, candidate, external_review)
    by_id = {str(item["article_id"]): item for item in review["articles"]}
    for finding in deterministic_findings:
        item = by_id[str(finding["article_id"])]
        item["verdict"] = "REJECT"
        normalized = {
            "code": finding["code"],
            "message": finding["message"],
        }
        if normalized not in item["findings"]:
            item["findings"].append(normalized)
        item["hard_failure"] = True
    return review


def _validate_candidate_matches_plan(
    candidate: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    for article, planned in zip(candidate["articles"], plan["articles"]):
        headings = [
            section["heading"]
            for section in article["bodySections"]
        ]
        if headings != planned["ordered_h2_outline"]:
            raise ValueError(
                f"article outline differs from locale plan for {planned['slot']}"
            )


def _candidate_plan_findings(
    candidate: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for article, planned in zip(candidate["articles"], plan["articles"]):
        planned_outline = planned["ordered_h2_outline"]
        headings = [
            section["heading"]
            for section in article["bodySections"]
        ]
        if any(
            re.fullmatch(r"h2-[1-4]", str(heading).strip(), re.IGNORECASE)
            for heading in planned_outline
        ):
            findings.append(
                {
                    "article_id": str(article["article_id"]),
                    "code": "LOCALE_PLAN_HEADING_PLACEHOLDER",
                    "message": (
                        "ordered_h2_outline 使用了保留的 h2 slot token，"
                        "必須改成目標語言的自然標題"
                    ),
                }
            )
        if headings != planned_outline:
            findings.append(
                {
                    "article_id": str(article["article_id"]),
                    "code": "LOCALE_PLAN_OUTLINE_MISMATCH",
                    "message": (
                        "bodySections 的數量、順序與 heading 必須逐字對齊"
                        "已驗證的 ordered_h2_outline"
                    ),
                }
            )
    return findings


def _run_locale_generation(
    brief: dict[str, Any],
    client: pipeline.GeminiClient,
    *,
    generation: int,
    generation_dir: Path,
    findings: list[dict[str, str]],
    history: list[list[dict[str, str]]],
    prior_plan: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    rebuild_by_slot = _rebuild_authority(brief, history)
    source_ref_path = generation_dir / "source-ref-map.json"
    external_plan_path = generation_dir / "external-plan.json"
    planning_result_path = generation_dir / "planning-result.json"
    try:
        source_ref_maps = _load_or_create_source_ref_maps(
            source_ref_path,
            brief,
            prior_plan,
            generation=generation,
            external_plan_path=external_plan_path,
        )
    except ValueError as error:
        terminal_reason = str(error)
        _write_locale_planning_result(
            planning_result_path,
            generation=generation,
            transport_status=(
                "EXTERNAL_PLAN_AVAILABLE"
                if external_plan_path.is_file()
                else "NOT_STARTED"
            ),
            planning_contract_status="PLANNING_CONTRACT_FAILURE",
            terminal_stage="PLANNING",
            terminal_reason=terminal_reason,
        )
        _record_partial_generation_terminalization(
            brief,
            generation=generation,
            generation_dir=generation_dir,
            reason=terminal_reason,
        )
        raise LocalePlanValidationError(
            f"deterministic locale plan failure: {error}"
        ) from error
    plan_prompt = _plan_prompt(
        brief,
        generation=generation,
        prior_plan=prior_plan,
        findings=findings,
        rebuild_by_slot=rebuild_by_slot,
        source_ref_maps=source_ref_maps,
    )
    plan_schema = _external_locale_plan_schema(
        brief,
        prior_plan=prior_plan,
        source_ref_maps=source_ref_maps,
    )
    try:
        external_plan, allow_provider_safety_boundary = (
            _load_or_generate_external_locale_plan(
                client,
                plan_prompt,
                plan_schema,
                generation_dir / "plan-operation.json",
                external_plan_path,
                brief=brief,
                prior_plan=prior_plan,
                source_ref_maps=source_ref_maps,
            )
        )
        plan = _hydrate_locale_plan(
            brief,
            external_plan,
            generation=generation,
            rebuild_by_slot=rebuild_by_slot,
            prior_plan=prior_plan,
            source_ref_maps=source_ref_maps,
            allow_provider_safety_boundary=allow_provider_safety_boundary,
        )
    except ValueError as error:
        _write_locale_planning_result(
            planning_result_path,
            generation=generation,
            transport_status="EXTERNAL_PLAN_AVAILABLE",
            planning_contract_status="PLANNING_CONTRACT_FAILURE",
            terminal_stage="PLANNING",
            terminal_reason=str(error),
        )
        raise LocalePlanValidationError(
            f"deterministic locale plan failure: {error}"
        ) from error
    if source_ref_maps:
        _validate_source_ref_maps_against_current_package(brief, source_ref_maps)
    _write_locale_planning_result(
        planning_result_path,
        generation=generation,
        transport_status="EXTERNAL_PLAN_AVAILABLE",
        planning_contract_status="PASS",
        terminal_stage=None,
        terminal_reason=None,
    )
    _atomic_write_json(generation_dir / "locale-plan.json", plan)
    external_candidate = _load_or_generate_external(
        client,
        "writer",
        _article_prompt(
            brief,
            plan,
            findings,
            source_ref_maps=source_ref_maps,
        ),
        _external_candidate_schema(),
        generation_dir / "article-operation.json",
        generation_dir / "external-candidate.json",
    )
    candidate = _hydrate_candidate(brief, external_candidate)
    deterministic = [
        *_candidate_plan_findings(candidate, plan),
        *translation_findings(brief, candidate["articles"]),
    ]
    _atomic_write_json(
        generation_dir / "deterministic-findings.json",
        deterministic,
    )
    external_review = _load_or_generate_external(
        client,
        "reviewer",
        _reviewer_prompt(brief, candidate, deterministic),
        pipeline.external_review_schema(),
        generation_dir / "reviewer-operation.json",
        generation_dir / "external-review.json",
    )
    review = _review_generated_candidate(
        brief,
        candidate,
        external_review,
        deterministic,
    )
    _atomic_write_json(generation_dir / "candidate.json", candidate)
    _atomic_write_json(generation_dir / "review.json", review)
    return candidate, review, plan


def _review_approved(review: dict[str, Any]) -> bool:
    return all(
        item["verdict"] == "APPROVE" and not item["findings"]
        for item in review["articles"]
    )


def _write_root_result(
    run_dir: Path,
    candidate: dict[str, Any],
    review: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
) -> None:
    if state is not None and state.get("status") == "complete":
        state["terminal_candidate_sha256"] = _json_sha256(candidate)
        state["terminal_review_sha256"] = _json_sha256(review)
    transaction_path = run_dir / "continuation" / "root-update.json"
    _atomic_write_json(
        transaction_path,
        {
            "schema_version": SCHEMA_VERSION,
            "candidate": candidate,
            "review": review,
            "state": state,
        },
    )
    _atomic_write_json(run_dir / "candidate.json", candidate)
    _atomic_write_json(run_dir / "review.json", review)
    if state is not None:
        _atomic_write_json(run_dir / "continuation" / "state.json", state)
    transaction_path.unlink()


def _recover_root_result(run_dir: Path) -> None:
    transaction_path = run_dir / "continuation" / "root-update.json"
    if not transaction_path.is_file():
        return
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    if (
        not isinstance(transaction, dict)
        or set(transaction) != {"schema_version", "candidate", "review", "state"}
        or transaction.get("schema_version") != SCHEMA_VERSION
        or not isinstance(transaction.get("candidate"), dict)
        or not isinstance(transaction.get("review"), dict)
        or (
            transaction.get("state") is not None
            and not isinstance(transaction.get("state"), dict)
        )
    ):
        raise ValueError("root update transaction is invalid")
    state = transaction["state"]
    if state is not None and state.get("status") == "complete" and (
        state.get("terminal_candidate_sha256")
        != _json_sha256(transaction["candidate"])
        or state.get("terminal_review_sha256")
        != _json_sha256(transaction["review"])
    ):
        raise ValueError("root update transaction terminal identity is invalid")
    _atomic_write_json(run_dir / "candidate.json", transaction["candidate"])
    _atomic_write_json(run_dir / "review.json", transaction["review"])
    if transaction["state"] is not None:
        _atomic_write_json(
            run_dir / "continuation" / "state.json",
            transaction["state"],
        )
    transaction_path.unlink()


def _run_fresh_writer_reviewer(
    run_dir: Path,
    client: pipeline.GeminiClient,
    *,
    max_repairs: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    brief = _load_registered_translation_brief(run_dir)
    history: list[list[dict[str, str]]] = []
    findings: list[dict[str, str]] = []
    prior_plan: dict[str, Any] | None = None
    candidate: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    for generation in range(1, max_repairs + 2):
        candidate, review, prior_plan = _run_locale_generation(
            brief,
            client,
            generation=generation,
            generation_dir=run_dir / "attempts" / f"{generation:02d}",
            findings=findings,
            history=history,
            prior_plan=prior_plan,
        )
        findings = _review_findings(review)
        history.append(findings)
        if _review_approved(review):
            break
    if candidate is None or review is None:
        raise RuntimeError("translation writer/reviewer produced no result")
    _write_root_result(run_dir, candidate, review)
    return candidate, review


def _continuation_operation_id(
    brief: dict[str, Any],
    starting_review_sha256: str,
    started_after_generation: int,
) -> str:
    identity = {
        "run_id": brief["run_id"],
        "source_sha256": [
            target["source_sha256"]
            for target in brief["articles"]
        ],
        "starting_review_sha256": starting_review_sha256,
        "started_after_generation": started_after_generation,
    }
    return hashlib.sha256(compact_json_bytes(identity)).hexdigest()


def _load_or_create_continuation_state(
    run_dir: Path,
    brief: dict[str, Any],
    review: dict[str, Any],
    *,
    max_repairs: int,
) -> dict[str, Any]:
    path = run_dir / "continuation" / "state.json"
    existing = _generation_directories(run_dir / "attempts")
    expected_attempt_names = [
        f"{generation:02d}"
        for generation in range(1, len(existing) + 1)
    ]
    if [attempt_dir.name for attempt_dir in existing] != expected_attempt_names:
        raise ValueError("attempt generation lineage must be contiguous from 01")
    started_after = len(existing)
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        starting_review_sha256 = hashlib.sha256(
            compact_json_bytes(review)
        ).hexdigest()
        state = {
            "schema_version": SCHEMA_VERSION,
            "operation_id": _continuation_operation_id(
                brief,
                starting_review_sha256,
                started_after,
            ),
            "run_id": brief["run_id"],
            "source_sha256": [
                target["source_sha256"]
                for target in brief["articles"]
            ],
            "starting_review_sha256": starting_review_sha256,
            "terminal_candidate_sha256": None,
            "terminal_review_sha256": None,
            "started_after_generation": started_after,
            "semantic_budget": max_repairs + 1,
            "next_generation": started_after + 1,
            "completed_generations": [],
            "abandoned_generations": [],
            "status": "active",
        }
        _atomic_write_json(path, state)
    required = {
        "schema_version",
        "operation_id",
        "run_id",
        "source_sha256",
        "starting_review_sha256",
        "terminal_candidate_sha256",
        "terminal_review_sha256",
        "started_after_generation",
        "semantic_budget",
        "next_generation",
        "completed_generations",
        "status",
    }
    state_keys = set(state) if isinstance(state, dict) else set()
    abandoned_generations = state.get("abandoned_generations", [])
    if (
        not isinstance(state, dict)
        or state_keys not in (required, {*required, "abandoned_generations"})
        or state.get("schema_version") != SCHEMA_VERSION
        or state.get("run_id") != brief["run_id"]
        or state.get("source_sha256")
        != [target["source_sha256"] for target in brief["articles"]]
        or not re.fullmatch(r"[0-9a-f]{64}", str(state.get("starting_review_sha256")))
        or state.get("operation_id")
        != _continuation_operation_id(
            brief,
            str(state.get("starting_review_sha256")),
            state.get("started_after_generation"),
        )
        or type(state.get("started_after_generation")) is not int
        or type(state.get("started_after_generation")) is bool
        or state["started_after_generation"] < 1
        or state["started_after_generation"] != started_after
        or type(state.get("semantic_budget")) is not int
        or type(state.get("semantic_budget")) is bool
        or not 1 <= state["semantic_budget"] <= 3
        or type(state.get("next_generation")) is not int
        or type(state.get("next_generation")) is bool
        or state["next_generation"] < state["started_after_generation"] + 1
        or not isinstance(state.get("completed_generations"), list)
        or not isinstance(abandoned_generations, list)
        or any(
            type(generation) is not int or type(generation) is bool
            for generation in [*state["completed_generations"], *abandoned_generations]
        )
        or sorted(set(state["completed_generations"])) != state["completed_generations"]
        or sorted(set(abandoned_generations)) != abandoned_generations
        or set(state["completed_generations"]) & set(abandoned_generations)
        or any(
            generation <= state["started_after_generation"]
            or generation >= state["next_generation"]
            for generation in [*state["completed_generations"], *abandoned_generations]
        )
        or state.get("status") not in {"active", "complete"}
        or (
            state.get("status") == "active"
            and (
                state.get("starting_review_sha256") != _json_sha256(review)
                or state.get("terminal_candidate_sha256") is not None
                or state.get("terminal_review_sha256") is not None
            )
        )
        or (
            state.get("status") == "complete"
            and (
                not re.fullmatch(
                    r"[0-9a-f]{64}",
                    str(state.get("terminal_candidate_sha256")),
                )
                or not re.fullmatch(
                    r"[0-9a-f]{64}",
                    str(state.get("terminal_review_sha256")),
                )
                or state.get("terminal_candidate_sha256")
                != _json_sha256(
                    json.loads(
                        (run_dir / "candidate.json").read_text(encoding="utf-8")
                    )
                )
                or state.get("terminal_review_sha256") != _json_sha256(review)
            )
        )
    ):
        raise ValueError("continuation state identity is invalid")
    occupied_generations = sorted(
        [*state["completed_generations"], *abandoned_generations]
    )
    expected_occupied = list(
        range(
            state["started_after_generation"] + 1,
            state["next_generation"],
        )
    )
    if (
        occupied_generations != expected_occupied
        or state["next_generation"]
        > (
            state["started_after_generation"]
            + state["semantic_budget"]
            + len(abandoned_generations)
            + 1
        )
    ):
        raise ValueError("continuation generation state is not contiguous")
    generation_dirs = _generation_directories(run_dir / "generations")
    occupied_names = [f"{generation:02d}" for generation in expected_occupied]
    allowed_names = [occupied_names]
    if state["status"] == "active":
        allowed_names.append(
            [*occupied_names, f"{state['next_generation']:02d}"]
        )
    if [generation_dir.name for generation_dir in generation_dirs] not in allowed_names:
        raise ValueError("continuation generation directories differ from state")
    if "abandoned_generations" not in state:
        state = {**state, "abandoned_generations": []}
    return state


def _validate_semantic_budget(max_repairs: int) -> None:
    if (
        type(max_repairs) is not int
        or type(max_repairs) is bool
        or not 0 <= max_repairs <= 2
    ):
        raise ValueError("translation semantic repair budget must be between 0 and 2")


def _continue_writer_reviewer_unlocked(
    run_dir: Path,
    client: pipeline.GeminiClient,
    *,
    max_repairs: int = 2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_semantic_budget(max_repairs)
    _recover_root_result(run_dir)
    brief = _load_registered_translation_brief(run_dir)
    root_candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    root_review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    validate_translation_candidate(brief, root_candidate)
    if root_review.get("run_id") != brief["run_id"]:
        raise ValueError("continuation review run identity differs from brief")
    pipeline.validate_review(root_review, root_candidate["articles"])
    state = _load_or_create_continuation_state(
        run_dir,
        brief,
        root_review,
        max_repairs=max_repairs,
    )
    if state["status"] == "complete":
        return root_candidate, root_review
    if _consume_partial_generation_terminalization(run_dir, brief, state):
        next_generation = int(state["next_generation"]) + 1
        raise LocalePlanValidationError(
            "partial generation terminalized; "
            f"retry continuation from generation {next_generation:02d}"
        )

    roots = [run_dir / "attempts", run_dir / "generations"]
    history = _finding_history(brief, [run_dir / "attempts"])
    history.append(_review_findings(root_review))
    history.extend(_finding_history(brief, [run_dir / "generations"]))
    findings = history[-1]
    prior_plan = _last_locale_plan(
        roots,
        before_generation=int(state["next_generation"]),
    ) or _candidate_outline_plan(root_candidate)
    candidate: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    final_generation = (
        int(state["started_after_generation"])
        + int(state["semantic_budget"])
        + len(state.get("abandoned_generations", []))
    )
    for generation in range(int(state["next_generation"]), final_generation + 1):
        candidate, review, prior_plan = _run_locale_generation(
            brief,
            client,
            generation=generation,
            generation_dir=run_dir / "generations" / f"{generation:02d}",
            findings=findings,
            history=history,
            prior_plan=prior_plan,
        )
        findings = _review_findings(review)
        history.append(findings)
        state["completed_generations"].append(generation)
        state["next_generation"] = generation + 1
        complete = _review_approved(review) or generation == final_generation
        if complete:
            state["status"] = "complete"
            _write_root_result(
                run_dir,
                candidate,
                review,
                state=state,
            )
            return candidate, review
        _atomic_write_json(run_dir / "continuation" / "state.json", state)
    raise RuntimeError("continuation semantic budget produced no result")


def continue_writer_reviewer(
    run_dir: Path,
    client: pipeline.GeminiClient,
    *,
    max_repairs: int = 2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with _continuation_run_lock(run_dir):
        return _continue_writer_reviewer_unlocked(
            run_dir,
            client,
            max_repairs=max_repairs,
        )


def run_writer_reviewer(
    run_dir: Path,
    client: pipeline.GeminiClient,
    *,
    max_repairs: int = 2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_semantic_budget(max_repairs)
    _recover_root_result(run_dir)
    state_path = run_dir / "continuation" / "state.json"
    review_path = run_dir / "review.json"
    candidate_path = run_dir / "candidate.json"
    has_legacy_attempts = bool(_generation_directories(run_dir / "attempts"))
    if state_path.is_file() or (
        has_legacy_attempts
        and candidate_path.is_file()
        and review_path.is_file()
        and not _review_approved(
            json.loads(review_path.read_text(encoding="utf-8"))
        )
    ):
        return continue_writer_reviewer(
            run_dir,
            client,
            max_repairs=max_repairs,
        )
    return _run_fresh_writer_reviewer(
        run_dir,
        client,
        max_repairs=max_repairs,
    )


def review_edited_candidate(
    run_dir: Path,
    client: pipeline.GeminiClient,
) -> dict[str, Any]:
    """讓母語編輯稿沿用 deterministic gate 與獨立 Reviewer。"""
    brief = _load_registered_translation_brief(run_dir)
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    validate_translation_candidate(brief, candidate)
    findings = translation_findings(brief, candidate["articles"])
    pipeline.write_json(run_dir / "editorial-review" / "deterministic-findings.json", findings)
    external_review = _load_or_generate_external(
        client,
        "reviewer",
        _reviewer_prompt(brief, candidate, findings),
        pipeline.external_review_schema(),
        run_dir / "editorial-review" / "reviewer-operation.json",
        run_dir / "editorial-review" / "external-review.json",
    )
    review = pipeline.hydrate_review(brief, candidate, external_review)
    by_id = {str(item["article_id"]): item for item in review["articles"]}
    for finding in findings:
        item = by_id[str(finding["article_id"])]
        normalized_finding = {"code": finding["code"], "message": finding["message"]}
        item["verdict"] = "REJECT"
        if normalized_finding not in item["findings"]:
            item["findings"].append(normalized_finding)
        item["hard_failure"] = True
    pipeline.write_json(run_dir / "review.json", review)
    return review


def _locale_inventory(repo_root: Path) -> list[dict[str, Any]]:
    manifest = repo_root / "app/web/static/article-locales.js"
    if not manifest.exists() or "listArticleLocaleRecords" not in manifest.read_text(encoding="utf-8"):
        return []
    script = """
import { listArticleLocaleRecords } from "./app/web/static/article-locales.js";
console.log(JSON.stringify(listArticleLocaleRecords()));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return list(json.loads(result.stdout))


def apply_approved_translations(
    repo_root: Path,
    run_id: str,
    brief: dict[str, Any],
    candidate: dict[str, Any],
    review: dict[str, Any],
    approval: dict[str, Any],
    *,
    source_loader: SourceLoader = load_source_article,
    public_replacement: dict[str, Any] | None = None,
) -> list[Path]:
    validate_translation_candidate(brief, candidate)
    deterministic = translation_findings(brief, candidate["articles"])
    if deterministic:
        raise ValueError(f"translation deterministic gate failed: {len(deterministic)}")
    approved = pipeline.validate_apply_gate(
        candidate["articles"],
        review,
        approval,
        candidate_mode=str(candidate["mode"]),
    )
    if not approved:
        return []
    for article in approved:
        current = source_loader(repo_root, str(article["source_article_id"]))
        if source_sha256(current) != article["source_sha256"]:
            raise ValueError(f"translation source drift for {article['article_id']}")

    if public_replacement is not None:
        if len(approved) != 1:
            raise ValueError("public replacement requires exactly one approved article")
        module, after = _locale_replacement_plan(
            repo_root, public_replacement, approved[0], run_id
        )
        if module.read_bytes() == after:
            return [module]
        _atomic_write_bytes(module, after)
        return [module]

    slug, identifier = pipeline._safe_identifier(run_id)
    static = repo_root / "app/web/static"
    module = static / f"article-locale-{slug}.js"
    owned = {
        (str(item.get("articleId")), str(item.get("locale")))
        for item in _locale_inventory(repo_root)
        if str(item.get("runId")) == run_id
    }
    occupied = {
        (str(item.get("articleId")), str(item.get("locale")))
        for item in _locale_inventory(repo_root)
    } - owned
    records = []
    for article in approved:
        identity = (str(article["source_article_id"]), str(article["locale"]))
        if identity in occupied:
            raise ValueError(f"translation already exists: {identity[0]}:{identity[1]}")
        records.append(
            {
                "runId": run_id,
                "articleId": article["source_article_id"],
                "locale": article["locale"],
                "sourcePath": article["source_path"],
                "sourceSha256": article["source_sha256"],
                **{field: article[field] for field in sorted(TRANSLATABLE_FIELDS)},
            }
        )
    module.write_text(
        "// AGY 核准多語文章；由 scripts/agy_multilingual_pipeline.py 產生。\n\n"
        f"export const {identifier}_ARTICLE_LOCALES = {json.dumps(records, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    manifest = static / "article-locales.js"
    text = manifest.read_text(encoding="utf-8")
    import_line = f'import {{ {identifier}_ARTICLE_LOCALES }} from "./{module.name}?v={slug}";\n'
    text = pipeline._insert_once(text, "export const ARTICLE_LOCALE_REGISTRY = [", import_line + "\n")
    start = text.index("export const ARTICLE_LOCALE_REGISTRY = [")
    end = text.index("\n];", start)
    spread = f"  ...{identifier}_ARTICLE_LOCALES,"
    if spread not in text[start:end]:
        text = text[:end] + "\n" + spread + text[end:]
    manifest.write_text(text, encoding="utf-8")
    return [module, manifest]


def approve_and_apply_translation_run(
    repo_root: Path,
    run_dir: Path,
    approver: str,
) -> list[Path]:
    """核准 Reviewer 全數通過的 run，並套用至 locale registry。"""
    brief = _load_registered_translation_brief(run_dir)
    candidate = json.loads((run_dir / "candidate.json").read_text(encoding="utf-8"))
    review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    validate_translation_candidate(brief, candidate)
    pipeline.validate_review(review, candidate["articles"])
    if any(
        item.get("verdict") != "APPROVE"
        or item.get("hard_failure") is True
        or item.get("findings")
        for item in review["articles"]
    ):
        raise ValueError("translation run is not cleanly approved")
    decisions = {str(article["article_id"]): "APPROVE" for article in candidate["articles"]}
    approval = pipeline.build_approval(
        str(candidate["run_id"]),
        candidate["articles"],
        review,
        decisions,
        approver,
    )
    pipeline.write_json(run_dir / "approval.json", approval)
    return apply_approved_translations(
        repo_root,
        str(candidate["run_id"]),
        brief,
        candidate,
        review,
        approval,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--article-id", required=True)
    prepare.add_argument("--locales", nargs="+", choices=sorted(SUPPORTED_LOCALES), default=sorted(SUPPORTED_LOCALES))
    prepare.add_argument("--output-root", type=Path, default=Path(".work/i18n-runs"))
    run = subparsers.add_parser("run")
    run.add_argument("--run-dir", type=Path, required=True)
    review = subparsers.add_parser("review")
    review.add_argument("--run-dir", type=Path, required=True)
    apply = subparsers.add_parser("apply")
    apply.add_argument("--run-dir", type=Path, required=True)
    apply.add_argument("--approver", required=True)
    authorize = subparsers.add_parser("authorize-next-generation-after-reviewer-reject")
    authorize.add_argument("--run-dir", type=Path, required=True)
    authorize.add_argument("--expected-run-id", required=True)
    authorize.add_argument("--terminal-generation", type=int, required=True)
    authorize.add_argument("--expected-source-sha256", required=True)
    authorize.add_argument("--expected-locale-plan-sha256", required=True)
    authorize.add_argument("--expected-source-ref-map-sha256", required=True)
    authorize.add_argument("--expected-terminal-candidate-sha256", required=True)
    authorize.add_argument("--expected-terminal-review-sha256", required=True)
    authorize.add_argument("--authority-digest", required=True)
    authorize.add_argument("--execute", action="store_true")
    stage = subparsers.add_parser("stage-approved-edited-candidate")
    for name in ("run-dir", "approved-candidate", "approved-review", "formal-review-result", "queue-state", "publisher-ledger"):
        stage.add_argument(f"--{name}", type=Path, required=True)
    stage.add_argument("--terminal-owner-kind", choices=("continuation_generation", "replacement_attempt"), required=True)
    stage.add_argument("--terminal-generation", type=int)
    stage.add_argument("--terminal-attempt", type=int)
    stage.add_argument("--replacement-of")
    stage.add_argument("--replacement-reason")
    stage.add_argument("--public-replacement", type=Path)
    for name in ("run-id", "approved-article-sha256", "root-candidate-sha256", "root-review-sha256", "queue-state-sha256", "publisher-ledger-sha256"):
        stage.add_argument(f"--expected-{name}", required=True)
    stage.add_argument("--expected-continuation-state-sha256")
    stage.add_argument("--expected-replacement-state-sha256")
    for name in ("approved-candidate-sha256", "approved-review-sha256", "formal-review-result-sha256", "source-sha256", "actor-sha"):
        stage.add_argument(f"--expected-{name}")
    stage.add_argument("--expected-plan-digest")
    stage.add_argument("--execute", action="store_true")
    return parser.parse_args()
def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    if args.command == "prepare":
        path = prepare_translation_run(
            repo_root,
            args.run_id,
            args.article_id,
            args.locales,
            (repo_root / args.output_root).resolve(),
        )
        print(path)
        return 0
    if args.command == "run":
        client = pipeline.GeminiClient.from_environment()
        candidate, review = run_writer_reviewer(args.run_dir.resolve(), client)
        print(
            json.dumps(
                {
                    "run_id": candidate["run_id"],
                    "approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
                    "total": len(review["articles"]),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "review":
        review = review_edited_candidate(args.run_dir.resolve(), pipeline.GeminiClient.from_environment())
        print(
            json.dumps(
                {
                    "run_id": review["run_id"],
                    "approved": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
                    "total": len(review["articles"]),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "authorize-next-generation-after-reviewer-reject":
        receipt = authorize_next_generation_after_reviewer_reject(
            args.run_dir.resolve(),
            expected_run_id=args.expected_run_id,
            terminal_generation=args.terminal_generation,
            expected_source_sha256=args.expected_source_sha256,
            expected_locale_plan_sha256=args.expected_locale_plan_sha256,
            expected_source_ref_map_sha256=args.expected_source_ref_map_sha256,
            expected_terminal_candidate_sha256=args.expected_terminal_candidate_sha256,
            expected_terminal_review_sha256=args.expected_terminal_review_sha256,
            authority_digest=args.authority_digest,
            execute=args.execute,
        )
        print(json.dumps(receipt, ensure_ascii=False))
        return 0
    if args.command == "stage-approved-edited-candidate":
        stage_kwargs = {
            "repo_root": repo_root,
            **{
                f"{name}_path": getattr(args, name).resolve()
                for name in ("approved_candidate", "approved_review", "formal_review_result", "queue_state", "publisher_ledger")
            },
            **{
                name: getattr(args, name)
                for name in (
                    "expected_run_id", "terminal_owner_kind", "terminal_generation", "terminal_attempt",
                    "replacement_of", "replacement_reason", "expected_approved_article_sha256",
                    "expected_root_candidate_sha256", "expected_root_review_sha256",
                    "expected_continuation_state_sha256", "expected_replacement_state_sha256",
                    "expected_queue_state_sha256", "expected_publisher_ledger_sha256", "expected_approved_candidate_sha256",
                    "expected_approved_review_sha256", "expected_formal_review_result_sha256", "expected_source_sha256", "expected_actor_sha",
                )
            },
            "run_dir": args.run_dir.resolve(),
            "public_replacement": json.loads(args.public_replacement.resolve().read_text(encoding="utf-8")) if args.public_replacement else None,
        }
        if args.execute:
            if not args.expected_plan_digest:
                raise SystemExit("--execute requires --expected-plan-digest")
            receipt = apply_approved_edited_candidate_stage(
                **stage_kwargs,
                expected_plan_digest=args.expected_plan_digest,
            )
        else:
            receipt = plan_approved_edited_candidate_stage(**stage_kwargs)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "apply":
        changed = approve_and_apply_translation_run(
            repo_root,
            args.run_dir.resolve(),
            args.approver,
        )
        print(
            json.dumps(
                {"changed": [str(path.relative_to(repo_root)) for path in changed]},
                ensure_ascii=False,
            )
        )
        return 0
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

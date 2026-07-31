#!/usr/bin/env python3
"""以既有 Gemini Writer／Reviewer gate 產製並發布多語文章。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Callable

from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
SUPPORTED_LOCALES = {"en", "ja", "ko"}
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


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(compact_json_bytes(payload) + b"\n")
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
    if set(brief) != {"schema_version", "run_id", "mode", "articles"}:
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
        if article["title"] == source_content["title"] or article["description"] == source_content["description"]:
            findings.append({"article_id": translation_id, "code": "untranslated_metadata", "message": "標題或描述仍與原文相同"})
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


def enqueue_article_translations(
    repo_root: Path,
    queue_root: Path,
    *,
    source_run_id: str,
    article_id: str,
    source_loader: SourceLoader = load_source_article,
) -> list[dict[str, str]]:
    """為已發布新文或成功改寫舊文建立英、日、韓三個互不阻塞的翻譯 run。"""
    if not source_run_id.strip() or not article_id.strip():
        raise ValueError("source run id and article id must be non-empty")
    queue_root = queue_root.resolve()
    records: list[dict[str, str]] = []
    for locale in ["en", "ja", "ko"]:
        identity = f"{source_run_id}\0{article_id}\0{locale}"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        run_id = f"auto-i18n-{locale}-{digest[:20]}"
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
            current_source = source_loader(repo_root, article_id)
            if existing_brief["articles"][0]["source_sha256"] != source_sha256(current_source):
                raise ValueError("registered translation run source drift")
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
    validate_translation_brief(base_brief)
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
        texts = [
            str(source["description"]),
            str(source["answer"]),
            *[
                f"{faq['question']} {faq['answer']}"
                for faq in source["faq"]
            ],
            *[
                str(paragraph)
                for section in source["bodySections"]
                for paragraph in section["paragraphs"]
            ],
        ]
        facts = []
        seen: set[str] = set()
        for text in texts:
            normalized = text.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            facts.append(
                {
                    "fact_id": f"fact-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:12]}",
                    "text": normalized,
                    "safety_boundary": bool(safety_pattern.search(normalized)),
                }
            )
        facts.sort(key=lambda fact: fact["fact_id"])
        articles.append(
            {
                "slot": f"article-{index + 1:02d}",
                "locale": item["locale"],
                "source_sha256": item["source_sha256"],
                "topic_cues": {
                    "title": source["title"],
                    "tags": source["tags"],
                },
                "facts": facts,
            }
        )
    return {"articles": articles}


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


def _external_locale_plan_schema(brief: dict[str, Any]) -> dict[str, Any]:
    validate_translation_brief(brief)
    fact_articles = _source_fact_package(brief)["articles"]
    fact_counts = [len(item["facts"]) for item in fact_articles]
    source_fact_ids = list(
        dict.fromkeys(
            str(fact["fact_id"])
            for item in fact_articles
            for fact in item["facts"]
        )
    )
    target_count = len(brief["articles"])
    coverage = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source_fact_id": {"type": "string", "enum": source_fact_ids},
            "planned_h2_slot": {
                "type": "string",
                "enum": ["h2-1", "h2-2", "h2-3", "h2-4"],
            },
            "coverage_note": {"type": "string"},
            "safety_boundary": {"type": "boolean"},
        },
        "required": [
            "source_fact_id",
            "planned_h2_slot",
            "coverage_note",
            "safety_boundary",
        ],
    }
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
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
            "source_sha256": {
                "type": "string",
                "enum": list(
                    dict.fromkeys(
                        str(target["source_sha256"])
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
        },
        "required": [
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
        ],
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
            and (
                _normalized_outline(item["ordered_h2_outline"])
                == _normalized_outline(prior.get("ordered_h2_outline"))
                or (
                    _outline_topology(item)
                    and _outline_topology(item) == _outline_topology(prior)
                )
            )
        ):
            raise ValueError(f"locale plan rebuild reused prior outline topology for {slot}")


def _canonicalize_external_coverage_mappings(
    expected_facts: list[dict[str, Any]],
    mappings: object,
    *,
    slot: str,
) -> list[dict[str, Any]]:
    """驗證 fact 集合與安全旗標後，依 deterministic fact 順序正規化。"""
    if not isinstance(mappings, list) or len(mappings) != len(expected_facts):
        raise ValueError(f"external locale plan coverage differs for {slot}")
    expected_by_id = {
        str(fact["fact_id"]): fact
        for fact in expected_facts
    }
    mapped_by_id: dict[str, dict[str, Any]] = {}
    required = {
        "source_fact_id",
        "planned_h2_slot",
        "coverage_note",
        "safety_boundary",
    }
    for mapping in mappings:
        if not isinstance(mapping, dict) or set(mapping) != required:
            raise ValueError(
                f"external locale plan coverage fields are strict for {slot}"
            )
        fact_id = str(mapping["source_fact_id"])
        if fact_id not in expected_by_id or fact_id in mapped_by_id:
            raise ValueError(f"external locale plan source fact coverage differs for {slot}")
        if (
            mapping["safety_boundary"]
            is not expected_by_id[fact_id]["safety_boundary"]
        ):
            raise ValueError(f"locale plan safety coverage differs for {slot}")
        mapped_by_id[fact_id] = dict(mapping)
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
    articles = []
    for index, slot in enumerate(expected_slots):
        external_item = by_slot[slot]
        external_mappings = _canonicalize_external_coverage_mappings(
            fact_articles[index]["facts"],
            external_item.get("coverage_mapping"),
            slot=slot,
        )
        item = {
            **external_item,
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


def _plan_prompt(
    brief: dict[str, Any],
    *,
    generation: int,
    prior_plan: dict[str, Any] | None,
    findings: list[dict[str, str]],
    rebuild_by_slot: dict[str, bool],
) -> str:
    return "\n".join(
        [
            "你是 Pantheon 的目標語言內容規劃主編。只輸出 locale plan，不寫文章。",
            "topic、native search intent、query phrasing 與 H2 必須完全由本次 source fact package 產生，不得套用任何預設題材。",
            "coverage_mapping 必須逐一覆蓋 source fact，並保留標記為 safety_boundary 的限制。",
            "ordered_h2_outline 必須恰好有 4 個 H2；coverage_mapping.planned_h2_slot 必須使用 h2-1、h2-2、h2-3 或 h2-4，不得另寫或改寫 H2 文字。",
            "ordered_h2_outline 必須是目標語言的自然標題；h2-1、h2-2、h2-3、h2-4 只供 planned_h2_slot 定位，禁止把它們當成標題。",
            "source_structure_to_avoid 只用來辨識不能複製的來源 H2、section count、paragraph pattern；不得把它當 outline。",
            "rebuild_outline 由 pipeline 指定，不得自行改值。為 true 時，禁止沿用 prior plan 的 heading order、section topology 或同義詞替換版。",
            "generation:",
            str(generation),
            "locale contracts:",
            _canonical_json(LOCALE_EDITORIAL_CONTRACTS),
            "source fact package:",
            _canonical_json(_source_fact_package(brief)),
            "source structure to avoid:",
            _canonical_json(_source_structure_to_avoid(brief)),
            "prior plan:",
            _canonical_json(prior_plan),
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
) -> str:
    try:
        validate_locale_plan(brief, plan)
    except (TypeError, ValueError) as error:
        raise ValueError(f"locale plan is required and must be valid: {error}") from error
    public_input = {
        "articles": [
            {
                **fact_package,
                "editorial_contract": LOCALE_EDITORIAL_CONTRACTS[target["locale"]],
                "locale_plan": plan["articles"][index],
            }
            for index, (target, fact_package) in enumerate(
                zip(brief["articles"], _source_fact_package(brief)["articles"])
            )
        ]
    }
    return "\n".join(
        [
            "你是 Pantheon 的目標語言母語主編。這不是翻譯任務；slot 必須逐字複製。",
            "只依 source fact package、locale contract 與已驗證 locale plan 寫完整文章。",
            "寫作前先建立 source claim ledger：每一個定義、解釋、例子與結論都必須能由 source fact 明確支持；無法對應的句子直接刪除，不得用常識補完。",
            "ordered_h2_outline 是唯一 section authority；不得推回或模仿來源 H2、段落數、敘事順序。",
            "bodySections 的數量、順序與 heading 必須逐字對齊 ordered_h2_outline；h2-1 到 h2-4 只是 mapping slot，不是可輸出的標題。",
            "不得逐句對譯。可拆分、合併、重排 facts，但不能新增來源沒有的事實或承諾。",
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
            "public brief:",
            json.dumps(_public_brief(brief), ensure_ascii=False),
            "public candidate:",
            json.dumps(public_candidate, ensure_ascii=False),
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
    external_plan = _load_or_generate_external(
        client,
        "writer",
        _plan_prompt(
            brief,
            generation=generation,
            prior_plan=prior_plan,
            findings=findings,
            rebuild_by_slot=rebuild_by_slot,
        ),
        _external_locale_plan_schema(brief),
        generation_dir / "plan-operation.json",
        generation_dir / "external-plan.json",
    )
    try:
        plan = _hydrate_locale_plan(
            brief,
            external_plan,
            generation=generation,
            rebuild_by_slot=rebuild_by_slot,
            prior_plan=prior_plan,
        )
    except ValueError as error:
        raise LocalePlanValidationError(
            f"deterministic locale plan failure: {error}"
        ) from error
    _atomic_write_json(generation_dir / "locale-plan.json", plan)
    external_candidate = _load_or_generate_external(
        client,
        "writer",
        _article_prompt(brief, plan, findings),
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
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    validate_translation_brief(brief)
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
    if (
        not isinstance(state, dict)
        or set(state) != required
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
    expected_completed = list(
        range(
            state["started_after_generation"] + 1,
            state["next_generation"],
        )
    )
    if (
        state["completed_generations"] != expected_completed
        or state["next_generation"]
        > state["started_after_generation"] + state["semantic_budget"] + 1
    ):
        raise ValueError("continuation generation state is not contiguous")
    generation_dirs = _generation_directories(run_dir / "generations")
    completed_names = [f"{generation:02d}" for generation in expected_completed]
    allowed_names = [completed_names]
    if state["status"] == "active":
        allowed_names.append(
            [*completed_names, f"{state['next_generation']:02d}"]
        )
    if [generation_dir.name for generation_dir in generation_dirs] not in allowed_names:
        raise ValueError("continuation generation directories differ from state")
    return state


def _validate_semantic_budget(max_repairs: int) -> None:
    if (
        type(max_repairs) is not int
        or type(max_repairs) is bool
        or not 0 <= max_repairs <= 2
    ):
        raise ValueError("translation semantic repair budget must be between 0 and 2")


def continue_writer_reviewer(
    run_dir: Path,
    client: pipeline.GeminiClient,
    *,
    max_repairs: int = 2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_semantic_budget(max_repairs)
    _recover_root_result(run_dir)
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    validate_translation_brief(brief)
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
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
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
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
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
    changed = approve_and_apply_translation_run(repo_root, args.run_dir.resolve(), args.approver)
    print(json.dumps({"changed": [str(path.relative_to(repo_root)) for path in changed]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

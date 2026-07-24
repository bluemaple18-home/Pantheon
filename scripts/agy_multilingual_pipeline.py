#!/usr/bin/env python3
"""以既有 Gemini Writer／Reviewer gate 產製並發布多語文章。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable

from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
SUPPORTED_LOCALES = {"en", "ja", "ko"}
LOCALE_LABELS = {"en": "English", "ja": "日本語", "ko": "한국어"}
LOCALE_EDITORIAL_CONTRACTS = {
    "en": {
        "audience": "Readers searching in English for a practical tarot card meanings guide.",
        "voice": "Write as an original English web editor: direct, clear, calm, and useful. Use active voice and natural subject-verb order.",
        "syntax": "Lead with the answer, use short scannable headings, vary sentence length, and address the reader as 'you' only when it helps.",
        "structure": (
            "Use exactly 4 H2 sections in this English-native order: "
            "(1) answer how tarot card meanings work, "
            "(2) give a short reading method using symbol, upright/reversed tone, and context, "
            "(3) explain why the same card reads differently in relationship and career questions, "
            "(4) state the limits and one practical next step. "
            "Recast source examples as natural English prose; never copy the source's three-item lists or clause order."
        ),
        "seo": "Use the phrases English readers would search for, such as tarot card meanings, upright and reversed meanings, and tarot reading, without keyword stuffing.",
        "avoid": "Do not preserve Chinese sentence order, parallelism, section boundaries, or repeated negative constructions. Avoid calques, generic AI polish, inflated adjectives, decorative metaphors, and formulaic conclusions.",
    },
    "ja": {
        "audience": "タロットカードの意味や正位置・逆位置を調べる日本語読者。",
        "voice": "日本のWebメディア向けに、自然で落ち着いた「です・ます調」で書く。説明は丁寧にするが、回りくどくしない。",
        "syntax": "日本語として自然な主題提示と省略を使い、長い修飾語を分ける。見出しと段落は読者の疑問順に再構成する。",
        "structure": "H2は4つに再構成する。最初に要点、次に正位置・逆位置の読み分け、質問別の読み方、最後に使い方の限界を置く。原文と同じ段落数にしない。",
        "seo": "「タロットカード 意味」「正位置 逆位置」「タロット 読み方」など、日本語で実際に入力される語順を自然に使う。",
        "avoid": "中国語の語順、対句、段落構成を写さない。「〜することができます」「〜において」「〜を提供します」などの翻訳調を連発しない。文体を混在させない。",
    },
    "ko": {
        "audience": "타로카드 뜻, 정방향·역방향, 타로 해석 방법을 찾는 한국어 독자.",
        "voice": "한국 웹 콘텐츠에 맞는 자연스럽고 신뢰감 있는 설명체로 쓴다. 설명은 합니다체를 기본으로 하고, 행동 제안에서만 자연스럽게 권유형을 쓴다.",
        "syntax": "핵심 답을 먼저 제시하고, 긴 관형절과 명사 나열을 줄인다. 한국어 독자의 질문 흐름에 따라 제목과 문단 순서를 새로 구성한다.",
        "structure": "한국 독자의 검색 흐름에 맞춰 H2를 4개 또는 5개로 다시 구성한다. 원문과 같은 섹션 수나 문단 수 패턴을 사용하지 않는다.",
        "seo": "「타로카드 뜻」「타로카드 해석」「정방향 역방향」처럼 한국어 검색에서 자연스러운 표현을 문맥에 맞게 사용한다.",
        "avoid": "중국어 어순, 대칭 문장, 원문의 문단 수를 복제하지 않는다. 번역투인 과도한 피동형, '제공합니다' 반복, 부자연스러운 한자어와 전각 문장부호를 피한다.",
    },
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


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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
const content = buildArticleContent(canonicalPath, "https://mysticpantheon.com");
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


def _writer_prompt(
    brief: dict[str, Any],
    prior: dict[str, Any] | None,
    findings: list[dict[str, str]],
) -> str:
    return "\n".join(
        [
            "你是 Pantheon 的目標語言母語主編。這不是翻譯任務，而是依 editorial_contract 從零重寫可公開文章；slot 必須逐字複製。",
            "寫作前先在內部建立 source claim ledger：每一個定義、解釋、例子與結論都必須能由 source 明確支持；無法對應的句子直接刪除，不得用常識補完。",
            "再按照該語言的語法、搜尋習慣與閱讀節奏重新設計標題、H2、段落與 FAQ。",
            "不得逐句對譯、不得沿用中文段落骨架。可拆分、合併、重排內容，但不能新增原文沒有的事實或承諾。",
            "禁止用比喻、口號、華麗形容詞或抽象 AI 套話填補篇幅；原文只有「正逆位語氣不同」時，不得自行發明正逆位能量、心理或象徵定義。",
            "若有 prior，只修正 findings，但仍輸出完整結果。",
            "public brief:",
            json.dumps(_public_brief(brief), ensure_ascii=False),
            "prior:",
            json.dumps(prior, ensure_ascii=False) if prior else "null",
            "findings:",
            json.dumps(findings, ensure_ascii=False),
        ]
    )


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


def run_writer_reviewer(
    run_dir: Path,
    client: pipeline.GeminiClient,
    *,
    max_repairs: int = 2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    validate_translation_brief(brief)
    candidate: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    findings: list[dict[str, str]] = []
    for attempt in range(max_repairs + 1):
        attempt_dir = run_dir / "attempts" / f"{attempt + 1:02d}"
        external = _load_or_generate_external(
            client,
            "writer",
            _writer_prompt(brief, candidate, findings),
            _external_candidate_schema(),
            attempt_dir / "writer-operation.json",
            attempt_dir / "external-candidate.json",
        )
        candidate = _hydrate_candidate(brief, external)
        findings = translation_findings(brief, candidate["articles"])
        pipeline.write_json(attempt_dir / "deterministic-findings.json", findings)
        external_review = _load_or_generate_external(
            client,
            "reviewer",
            _reviewer_prompt(brief, candidate, findings),
            pipeline.external_review_schema(),
            attempt_dir / "reviewer-operation.json",
            attempt_dir / "external-review.json",
        )
        review = pipeline.hydrate_review(brief, candidate, external_review)
        by_id = {str(item["article_id"]): item for item in review["articles"]}
        for finding in findings:
            item = by_id[str(finding["article_id"])]
            item["verdict"] = "REJECT"
            normalized_finding = {"code": finding["code"], "message": finding["message"]}
            if normalized_finding not in item["findings"]:
                item["findings"].append(normalized_finding)
            item["hard_failure"] = True
        if all(item["verdict"] == "APPROVE" and not item["findings"] for item in review["articles"]):
            break
        findings = [
            {"article_id": str(item["article_id"]), **finding}
            for item in review["articles"]
            for finding in item["findings"]
        ]
    if candidate is None or review is None:
        raise RuntimeError("translation writer/reviewer produced no result")
    pipeline.write_json(run_dir / "candidate.json", candidate)
    pipeline.write_json(run_dir / "review.json", review)
    return candidate, review


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
    approved = pipeline.validate_apply_gate(candidate["articles"], review, approval)
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

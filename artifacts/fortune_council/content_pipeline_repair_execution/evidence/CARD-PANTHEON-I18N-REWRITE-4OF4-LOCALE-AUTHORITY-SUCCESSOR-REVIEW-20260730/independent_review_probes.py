"""Locale-authority successor candidate 的獨立 adversarial Review probes。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from scripts import agy_multilingual_pipeline as multilingual


SPEC = importlib.util.spec_from_file_location(
    "locale_authority_candidate_tests",
    Path("tests/test_agy_multilingual_pipeline.py"),
)
assert SPEC is not None and SPEC.loader is not None
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)

SEMANTIC_FIELDS = (
    "native_search_intent",
    "native_query_phrasings",
    "article_angle",
    "ordered_h2_outline",
    "coverage_note",
)


def _replace_semantic_item(
    item: dict[str, object],
    field: str,
    text: str,
) -> None:
    if field in {"native_search_intent", "article_angle"}:
        item[field] = text
        return
    if field == "native_query_phrasings":
        queries = item[field]
        assert isinstance(queries, list)
        queries[0] = text
        return
    if field == "ordered_h2_outline":
        outline = item[field]
        mappings = item["coverage_mapping"]
        assert isinstance(outline, list) and isinstance(mappings, list)
        old_heading = outline[0]
        outline[0] = text
        for mapping in mappings:
            assert isinstance(mapping, dict)
            if mapping["planned_h2"] == old_heading:
                mapping["planned_h2"] = text
        return
    mappings = item["coverage_mapping"]
    assert isinstance(mappings, list) and isinstance(mappings[0], dict)
    mappings[0]["coverage_note"] = text


def _assert_semantic_item_rejected(locale: str, field: str, text: str) -> None:
    brief = FIXTURES.non_tarot_translation_brief(locale)
    external = FIXTURES.external_locale_plan(brief)
    item = external["articles"][0]
    _replace_semantic_item(item, field, text)

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize("field", SEMANTIC_FIELDS)
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("ordinary english words", id="lowercase"),
        pytest.param("Ordinary English Words", id="title-case"),
        pytest.param("SOURCE FACT CHECK", id="uppercase"),
        pytest.param("Zorple Quindle", id="unknown-words"),
        pytest.param(
            "OpenAI GPT-5 2026 2027",
            id="over-token-count",
        ),
        pytest.param(
            "MODEL-12345678901234567890",
            id="over-token-length",
        ),
        pytest.param("API OpenAI 2026", id="unlisted-topology"),
    ],
)
def test_each_semantic_item_rejects_ascii_sentences_and_out_of_bounds_literals(
    locale: str,
    field: str,
    text: str,
) -> None:
    _assert_semantic_item_rejected(locale, field, text)


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize("field", SEMANTIC_FIELDS)
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("@@OpenAI@@", id="leading-trailing-junk"),
        pytest.param("OpenAI???", id="trailing-punctuation"),
        pytest.param("OpenAI/GPT-5/2026", id="slash-separators"),
        pytest.param("OpenAI,GPT-5;2026", id="mixed-separators"),
    ],
)
def test_each_semantic_item_requires_full_ascii_value_consumption(
    locale: str,
    field: str,
    text: str,
) -> None:
    _assert_semantic_item_rejected(locale, field, text)


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize("field", SEMANTIC_FIELDS)
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Strategy", id="ordinary-title-case-word"),
        pytest.param("SOURCE", id="ordinary-uppercase-word"),
        pytest.param("Zorple", id="unknown-title-case-word"),
    ],
)
def test_each_semantic_item_rejects_single_ordinary_ascii_word(
    locale: str,
    field: str,
    text: str,
) -> None:
    _assert_semantic_item_rejected(locale, field, text)


@pytest.mark.parametrize(
    "text",
    [
        "@@OpenAI@@",
        "OpenAI???",
        "OpenAI/GPT-5/2026",
        "OpenAI,GPT-5;2026",
    ],
)
def test_ascii_literal_validator_rejects_unconsumed_characters(text: str) -> None:
    assert not multilingual._ascii_is_name_acronym_or_number(text)


@pytest.mark.parametrize(
    ("locale", "text"),
    [
        ("ja", "実践方法"),
        ("ja", "自然な日本語の説明"),
        ("ko", "자연스러운 한국어 설명"),
        ("ja", "OpenAIを使う"),
        ("ja", "APIを確認する"),
        ("ja", "GPT-5を比較する"),
        ("ja", "2026年の傾向"),
        ("ko", "OpenAI를 사용합니다"),
        ("ko", "API를 확인합니다"),
        ("ko", "GPT-5를 비교합니다"),
        ("ko", "2026년의 경향"),
        ("ja", "OpenAI"),
        ("ja", "API"),
        ("ja", "GPT-5"),
        ("ja", "2026"),
        ("ja", "OpenAI GPT-5 2026"),
        ("ko", "OpenAI"),
        ("ko", "API"),
        ("ko", "GPT-5"),
        ("ko", "2026"),
        ("ko", "OpenAI GPT-5 2026"),
    ],
)
def test_positive_locale_authority_controls(locale: str, text: str) -> None:
    assert multilingual._plan_matches_target_language(locale, text)


@pytest.mark.parametrize("locale", ["ja", "ko"])
def test_natural_locale_plan_positive_control(locale: str) -> None:
    brief = FIXTURES.non_tarot_translation_brief(locale)
    multilingual._hydrate_locale_plan(
        brief,
        FIXTURES.external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("How to compare useful methods", True),
        ("OpenAI GPT-5 2026", True),
        ("2026", True),
        ("実践方法", False),
        ("자연스러운 설명", False),
    ],
)
def test_english_locale_behavior_is_preserved(text: str, expected: bool) -> None:
    assert multilingual._plan_matches_target_language("en", text) is expected

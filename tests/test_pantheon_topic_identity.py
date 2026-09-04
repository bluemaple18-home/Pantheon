from __future__ import annotations

from pathlib import Path

import pytest

import scripts.pantheon_topic_identity as identity


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX = REPO_ROOT / "artifacts/fortune_council/content_seo_matrix/article_matrix.md"
BRIEFS = REPO_ROOT / "artifacts/fortune_council/content_seo_matrix/article_briefs_first_30.md"


def _topic(**overrides: str) -> dict[str, str]:
    topic = {
        "source": "test",
        "source_id": "T01",
        "source_matrix_ref": "test:T01",
        "domain": "fortune",
        "entity": "tarot",
        "semantic_intent": "感情塔羅怎麼問",
        "scenario": "love",
        "relationship_context": "partner",
        "time_window": "current",
        "template_family": "question-guide",
        "product_intent": "love-report",
        "search_volume": "UNKNOWN",
        "priority_score": 0,
        "coverage_status": "AVAILABLE",
        "duplicate_of_topic_id": None,
        "duplicate_reason": None,
        "title": "感情塔羅怎麼問？",
        "article_id": "LOVE-TAROT-QUESTIONS",
        "route": "/articles/tarot/love-tarot-questions",
        "canonical": "https://www.mysticpantheon.com/articles/tarot/love-tarot-questions",
        "slug": "love-tarot-questions",
    }
    topic.update(overrides)
    topic["topic_id"] = identity.build_topic_id(topic)
    return topic


def test_real_authority_files_convert_to_unique_topics() -> None:
    matrix_topics = identity.load_article_matrix_topics(MATRIX)
    brief_topics = identity.load_article_brief_topics(BRIEFS)

    assert len(matrix_topics) == 60
    assert len(brief_topics) == 30
    assert len({topic["topic_id"] for topic in matrix_topics}) == 60
    assert len({topic["topic_id"] for topic in brief_topics}) == 30
    assert len({topic["topic_id"] for topic in [*matrix_topics, *brief_topics]}) == 90
    assert matrix_topics[0]["source_id"] == "L01"
    assert brief_topics[0]["source_id"] == "M01"
    assert {topic["domain"] for topic in [*matrix_topics, *brief_topics]} == {"fortune"}
    assert all(topic["semantic_intent"] for topic in [*matrix_topics, *brief_topics])
    assert all(topic["source_matrix_ref"] for topic in [*matrix_topics, *brief_topics])
    assert {topic["search_volume"] for topic in [*matrix_topics, *brief_topics]} == {"UNKNOWN"}
    assert {topic["coverage_status"] for topic in [*matrix_topics, *brief_topics]} == {"AVAILABLE"}
    assert {topic["priority_score"] for topic in [*matrix_topics, *brief_topics]} == {0}
    assert {
        (topic["duplicate_of_topic_id"], topic["duplicate_reason"])
        for topic in [*matrix_topics, *brief_topics]
    } == {(None, None)}
    assert matrix_topics == identity.load_article_matrix_topics(MATRIX)
    assert brief_topics == identity.load_article_brief_topics(BRIEFS)


def test_topic_id_is_deterministic_and_not_title_only() -> None:
    first = _topic(title="共用標題")
    repeated = _topic(title="共用標題")
    different_identity = _topic(scenario="career", title="共用標題")

    assert first["topic_id"] == repeated["topic_id"]
    assert first["topic_id"] != different_identity["topic_id"]


def test_lineage_and_title_do_not_change_semantic_topic_identity() -> None:
    first = _topic()
    second = _topic(
        source="another_matrix",
        source_id="X99",
        source_matrix_ref="another_matrix:X99",
        title="不同標題但同一語意",
    )

    assert first["topic_id"] == second["topic_id"]
    assert identity.classify_topic(first, [], [second])["level"] == "exact_identity"


def test_exact_identity_is_a_collision() -> None:
    existing = _topic()
    result = identity.classify_topic(_topic(), existing_articles=[], planned_topics=[existing])

    assert result == {
        "status": "COLLISION",
        "level": "exact_identity",
        "matched_identity": existing["topic_id"],
        "coverage_status": "COLLISION",
        "duplicate_of_topic_id": existing["topic_id"],
        "duplicate_reason": "exact_identity",
    }


def test_article_id_route_and_canonical_collisions_are_hard_collisions() -> None:
    candidate = _topic()
    for existing in (
        {
            "id": candidate["article_id"],
            "path": "/articles/other/other",
            "title": "其他",
            "primaryKeyword": "其他",
        },
        {"id": "OTHER", "path": candidate["route"] + "/", "title": "其他", "primaryKeyword": "其他"},
        {"id": "OTHER", "canonical": candidate["canonical"] + "/", "title": "其他", "primaryKeyword": "其他"},
    ):
        result = identity.classify_topic(candidate, existing_articles=[existing])
        assert result["status"] == "COLLISION"
        assert result["level"] == "article_identity"


def test_normalized_title_or_slug_is_a_collision() -> None:
    candidate = _topic()
    title_match = {
        "id": "OTHER",
        "path": "/articles/other/unique",
        "title": "感情塔羅 怎麼問",
        "primaryKeyword": "其他",
    }
    slug_match = {
        "id": "OTHER",
        "path": "/articles/other/love_tarot_questions/",
        "title": "其他",
        "primaryKeyword": "其他",
    }

    assert identity.classify_topic(candidate, [title_match])["level"] == "normalized_title_slug"
    assert identity.classify_topic(candidate, [slug_match])["level"] == "normalized_title_slug"


def test_candidate_slug_collides_with_existing_current_url_slug() -> None:
    candidate = _topic(
        title="獨立 current slug 題目",
        semantic_intent="獨立 current slug 意圖",
        article_id="UNIQUE-CURRENT-SLUG",
        route="/articles/other/unique-current-route",
        canonical="https://www.mysticpantheon.com/articles/other/unique-current-canonical",
        slug="personality-0001",
    )
    existing = {
        "id": "MBTI-BASE-01",
        "path": "/articles/other/existing-current-path",
        "canonical": "https://www.mysticpantheon.com/articles/other/existing-current-canonical",
        "slug": "mbti-meaning",
        "urlSlug": "personality-0001",
        "title": "既有 current slug 題目",
        "primaryKeyword": "既有 current slug 意圖",
    }

    assert identity.classify_topic(candidate, [existing])["level"] == "normalized_title_slug"


def test_candidate_slug_collides_with_existing_legacy_slug() -> None:
    candidate = _topic(
        title="獨立 legacy slug 題目",
        semantic_intent="獨立 legacy slug 意圖",
        article_id="UNIQUE-LEGACY-SLUG",
        route="/articles/other/unique-legacy-route",
        canonical="https://www.mysticpantheon.com/articles/other/unique-legacy-canonical",
        slug="mbti-meaning",
    )
    existing = {
        "id": "MBTI-BASE-01",
        "path": "/articles/other/existing-legacy-path",
        "canonical": "https://www.mysticpantheon.com/articles/other/existing-legacy-canonical",
        "slug": "mbti-meaning",
        "urlSlug": "personality-0001",
        "title": "既有 legacy slug 題目",
        "primaryKeyword": "既有 legacy slug 意圖",
    }

    assert identity.classify_topic(candidate, [existing])["level"] == "normalized_title_slug"


def test_same_intent_with_different_title_needs_review() -> None:
    candidate = _topic()
    existing = {
        "id": "OTHER",
        "path": "/articles/other/unique",
        "title": "如何整理感情牌陣問題",
        "primaryKeyword": "感情塔羅 怎麼問？",
    }

    assert identity.classify_topic(candidate, [existing]) == {
        "status": "REVIEW_NEEDED",
        "level": "same_intent_different_title",
        "matched_identity": "OTHER",
        "coverage_status": "REVIEW_NEEDED",
        "duplicate_of_topic_id": "OTHER",
        "duplicate_reason": "same_intent_different_title",
    }


def test_same_matrix_combination_is_a_collision() -> None:
    candidate = _topic()
    existing = _topic(
        source_id="T99",
        title="另一個標題",
        article_id="OTHER",
        route="/articles/other/unique",
        canonical="https://www.mysticpantheon.com/articles/other/unique",
        slug="unique",
    )
    existing.pop("topic_id")

    result = identity.classify_topic(candidate, [], [existing])

    assert result["status"] == "COLLISION"
    assert result["level"] == "matrix_combination"


def test_distinct_topic_is_available_and_adapter_reuses_full_corpus_loader(monkeypatch) -> None:
    calls: list[Path] = []

    def fake_loader(repo_root: Path) -> list[dict[str, str]]:
        calls.append(repo_root)
        return [{"id": "OTHER", "path": "/articles/other/unique", "title": "其他", "primaryKeyword": "其他"}]

    monkeypatch.setattr(identity.pipeline, "load_publication_reference_corpus", fake_loader)
    candidate = _topic()

    first = identity.check_topic(REPO_ROOT, candidate)
    second = identity.check_topic(REPO_ROOT, candidate)

    assert first == {
        "status": "AVAILABLE",
        "level": None,
        "matched_identity": None,
        "coverage_status": "AVAILABLE",
        "duplicate_of_topic_id": None,
        "duplicate_reason": None,
    }
    assert second == first
    assert calls == [REPO_ROOT, REPO_ROOT]


def test_real_full_corpus_loader_is_accepted_by_adapter() -> None:
    articles = identity.load_existing_corpus(REPO_ROOT)

    assert articles
    assert all("id" in article and "path" in article and "title" in article for article in articles)


def test_real_legacy_slug_route_and_canonical_are_collisions() -> None:
    articles = identity.load_existing_corpus(REPO_ROOT)
    mbti = next(article for article in articles if article["id"] == "MBTI-BASE-01")

    assert mbti["slug"] == "mbti-meaning"
    assert mbti["urlSlug"] == "personality-0001"
    assert "/articles/personality/mbti-meaning" in mbti["legacyPaths"]

    cases = (
        (
            _topic(
                article_id="UNIQUE-ROUTE",
                title="獨立題目 route",
                semantic_intent="獨立意圖 route",
                route="/articles/personality/mbti-meaning",
                canonical="",
                slug="unique-route",
            ),
            "article_identity",
        ),
        (
            _topic(
                article_id="UNIQUE-CANONICAL",
                title="獨立題目 canonical",
                semantic_intent="獨立意圖 canonical",
                route="",
                canonical="https://www.mysticpantheon.com/articles/personality/mbti-meaning",
                slug="unique-canonical",
            ),
            "article_identity",
        ),
        (
            _topic(
                article_id="UNIQUE-SLUG",
                title="獨立題目 slug",
                semantic_intent="獨立意圖 slug",
                route="/articles/personality/unique-slug",
                canonical="",
                slug="mbti-meaning",
            ),
            "normalized_title_slug",
        ),
    )
    for candidate, expected_level in cases:
        result = identity.classify_topic(candidate, articles)
        assert (result["status"], result["level"]) == ("COLLISION", expected_level)


def test_invalid_or_stale_topic_identity_fails_closed() -> None:
    assert identity.REQUIRED_IDENTITY_FIELDS == (
        "domain",
        "entity",
        "semantic_intent",
        "scenario",
        "template_family",
        "product_intent",
    )
    with pytest.raises(identity.TopicIdentityValidationError, match="missing required identity dimensions"):
        identity.build_topic_id({})
    with pytest.raises(identity.TopicIdentityValidationError, match="topic_id is required"):
        identity.classify_topic({}, [])

    for field in identity.REQUIRED_IDENTITY_FIELDS:
        missing = _topic()
        missing.pop(field)
        with pytest.raises(identity.TopicIdentityValidationError, match=field):
            identity.build_topic_id(missing)

        whitespace = _topic()
        whitespace[field] = " \t"
        with pytest.raises(identity.TopicIdentityValidationError, match=field):
            identity.build_topic_id(whitespace)

    missing_dimension = _topic()
    missing_dimension.pop("entity")
    with pytest.raises(identity.TopicIdentityValidationError, match="entity"):
        identity.classify_topic(missing_dimension, [])

    whitespace_dimension = _topic()
    whitespace_dimension["entity"] = " \t"
    with pytest.raises(identity.TopicIdentityValidationError, match="entity"):
        identity.classify_topic(whitespace_dimension, [])

    missing_topic_id = _topic()
    missing_topic_id.pop("topic_id")
    with pytest.raises(identity.TopicIdentityValidationError, match="topic_id is required"):
        identity.classify_topic(missing_topic_id, [])

    whitespace_topic_id = _topic()
    whitespace_topic_id["topic_id"] = " \t"
    with pytest.raises(identity.TopicIdentityValidationError, match="topic_id is required"):
        identity.classify_topic(whitespace_topic_id, [])

    stale_topic_id = _topic()
    stale_topic_id["scenario"] = "career"
    with pytest.raises(identity.TopicIdentityValidationError, match="topic_id does not match"):
        identity.classify_topic(stale_topic_id, [])


def test_optional_identity_fields_may_be_missing_or_blank_and_remain_deterministic() -> None:
    for field in ("relationship_context", "time_window"):
        missing = _topic()
        missing.pop(field)
        missing_id = identity.build_topic_id(missing)
        assert missing_id == identity.build_topic_id(missing)

        blank = _topic()
        blank[field] = " \t"
        blank_id = identity.build_topic_id(blank)
        assert blank_id == identity.build_topic_id(blank)
        assert missing_id == blank_id

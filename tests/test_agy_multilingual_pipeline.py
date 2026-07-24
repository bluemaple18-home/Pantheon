from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import agy_multilingual_pipeline as multilingual
from scripts.agy_seo_copy_pipeline import article_sha256, build_approval


def source_article() -> dict[str, object]:
    return {
        "article_id": "TEST-001",
        "canonical_path": "/articles/tarot/tarot-0001",
        "title": "塔羅牌是什麼？",
        "description": "塔羅牌可協助整理問題，但不能替你預測必然結果。",
        "answer": "先看問題與情境，再閱讀牌義。",
        "tags": ["塔羅", "自我探索"],
        "faq": [
            {"question": "塔羅可以預測未來嗎？", "answer": "不能保證結果，只能提供觀察角度。"},
        ],
        "bodySections": [
            {
                "heading": "先釐清問題",
                "paragraphs": [
                    "閱讀塔羅牌前，先把問題、時間與可觀察事實分開。",
                    "單張牌不能取代完整情境，也不能替任何人做重大決定。",
                ],
            }
        ],
    }


def translation_brief(locale: str = "en") -> dict[str, object]:
    source = source_article()
    return {
        "schema_version": 1,
        "run_id": f"translate-test-{locale}",
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"TEST-001:{locale}",
                "locale": locale,
                "source_article_id": "TEST-001",
                "source_path": source["canonical_path"],
                "source_sha256": multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }


def translation_candidate(locale: str = "en") -> dict[str, object]:
    localized = {
        "en": {
            "title": "What Are Tarot Cards?",
            "description": "Tarot cards can help you organize a question and notice patterns, but they cannot guarantee a future outcome or replace a personal decision.",
            "answer": "Start with the question and context before interpreting a card.",
            "tags": ["Tarot", "Self-reflection"],
            "faq": [
                {
                    "question": "Can tarot predict the future?",
                    "answer": "No. It offers perspectives but cannot guarantee an outcome.",
                }
            ],
            "bodySections": [
                {
                    "heading": "Clarify the question first",
                    "paragraphs": [
                        "Before reading tarot cards, separate the question, time frame, and observable facts.",
                        "A single card cannot replace the full context or make an important decision for you.",
                    ],
                }
            ],
        },
        "ja": {
            "title": "タロットカードとは？",
            "description": "タロットは質問や状況を整理するための手がかりですが、未来の結果を保証したり、本人に代わって判断したりするものではありません。",
            "answer": "カードの意味より先に、質問と状況を整理しましょう。",
            "tags": ["タロット", "自己理解"],
            "faq": [
                {
                    "question": "タロットで未来を予測できますか？",
                    "answer": "結果を保証するものではなく、考える視点を提供します。",
                }
            ],
            "bodySections": [
                {
                    "heading": "最初に質問を整理する",
                    "paragraphs": [
                        "タロットを読む前に、質問、期間、確認できる事実を分けて整理します。",
                        "一枚のカードだけで状況全体を判断したり、重要な決定を代行したりすることはできません。",
                    ],
                }
            ],
        },
        "ko": {
            "title": "타로 카드는 무엇인가요?",
            "description": "타로 카드는 질문과 상황을 정리하는 데 도움을 줄 수 있지만 미래의 결과를 보장하거나 개인의 결정을 대신할 수는 없습니다.",
            "answer": "카드 뜻보다 먼저 질문과 상황을 정리하세요.",
            "tags": ["타로", "자기 이해"],
            "faq": [
                {
                    "question": "타로로 미래를 예측할 수 있나요?",
                    "answer": "결과를 보장하지 않으며 생각할 관점을 제공할 뿐입니다.",
                }
            ],
            "bodySections": [
                {
                    "heading": "먼저 질문을 분명히 하기",
                    "paragraphs": [
                        "타로를 읽기 전에 질문과 기간, 확인할 수 있는 사실을 나누어 정리하세요.",
                        "한 장의 카드가 전체 상황을 대신하거나 중요한 결정을 내려 줄 수는 없습니다.",
                    ],
                }
            ],
        },
    }[locale]
    localized["bodySections"].append(
        {
            "heading": {
                "en": "Use the reading as a prompt, not a verdict",
                "ja": "答えではなく、考える手がかりとして使う",
                "ko": "정답이 아니라 생각을 정리하는 도구로 사용합니다",
            }[locale],
            "paragraphs": [
                {
                    "en": "Use the reading to identify a question that you can verify or act on.",
                    "ja": "リーディングの後は、確認できる問いや実行できる一歩に戻りましょう。",
                    "ko": "리딩 후에는 확인할 수 있는 질문이나 실행 가능한 다음 단계로 돌아갑니다.",
                }[locale]
            ],
        }
    )
    localized["bodySections"].extend(
        [
            {
                "heading": {
                    "en": "Read the card in context",
                    "ja": "質問と状況を合わせて読む",
                    "ko": "질문과 상황을 함께 살핍니다",
                }[locale],
                "paragraphs": [
                    {
                        "en": "The same card can point to different concerns in a relationship or career reading.",
                        "ja": "同じカードでも、恋愛と仕事では注目する点が変わります。",
                        "ko": "같은 카드라도 연애와 직업 질문에서는 살펴볼 지점이 달라집니다.",
                    }[locale]
                ],
            },
            {
                "heading": {
                    "en": "Keep the limits clear",
                    "ja": "カードで決められないこと",
                    "ko": "카드가 결정할 수 없는 것",
                }[locale],
                "paragraphs": [
                    {
                        "en": "Tarot cannot guarantee an outcome or replace professional advice.",
                        "ja": "タロットは結果を保証せず、専門家の判断にも代わりません。",
                        "ko": "타로는 결과를 보장하거나 전문가의 판단을 대신하지 않습니다.",
                    }[locale]
                ],
            },
        ]
    )
    brief = translation_brief(locale)
    source = brief["articles"][0]
    return {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "translate_existing",
        "articles": [
            {
                "article_id": source["translation_id"],
                "locale": locale,
                "source_article_id": source["source_article_id"],
                "source_path": source["source_path"],
                "source_sha256": source["source_sha256"],
                **localized,
            }
        ],
    }


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_translation_contract_accepts_supported_locales(locale: str) -> None:
    brief = translation_brief(locale)
    candidate = translation_candidate(locale)

    multilingual.validate_translation_brief(brief)
    multilingual.validate_translation_candidate(brief, candidate)

    assert multilingual.translation_findings(brief, candidate["articles"]) == []


def test_translation_contract_rejects_source_hash_drift() -> None:
    brief = translation_brief()
    candidate = translation_candidate()
    candidate["articles"][0]["source_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="source hash"):
        multilingual.validate_translation_candidate(brief, candidate)


def test_translation_gate_rejects_wrong_language() -> None:
    brief = translation_brief("ko")
    candidate = translation_candidate("ko")
    candidate["articles"][0]["title"] = "This is not Korean"

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(item["code"] == "target_language" for item in findings)


def test_translation_gate_rejects_source_structure_mirroring() -> None:
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    candidate["articles"][0]["bodySections"] = [
        {
            "heading": "Clarify the question first",
            "paragraphs": [
                "Start by separating the question, time frame, and facts.",
                "A single card cannot replace the full context or make a decision for you.",
            ],
        }
    ]

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(item["code"] == "structural_mirroring" for item in findings)


def test_translation_gate_rejects_too_few_localized_sections() -> None:
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    candidate["articles"][0]["bodySections"] = candidate["articles"][0]["bodySections"][:3]

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(item["code"] == "localized_structure" for item in findings)


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_public_brief_includes_locale_specific_editorial_contract(locale: str) -> None:
    public = multilingual._public_brief(translation_brief(locale))
    target = public["articles"][0]

    assert target["editorial_contract"] == multilingual.LOCALE_EDITORIAL_CONTRACTS[locale]
    assert "不是翻譯" in public["policy"]["purpose"]
    assert "相同 H2／段落骨架" in public["policy"]["hard_reject"]


def test_writer_prompt_requires_source_claim_traceability_and_rejects_filler() -> None:
    prompt = multilingual._writer_prompt(translation_brief("en"), None, [])

    assert "source claim ledger" in prompt
    assert "不得用常識補完" in prompt
    assert "禁止用比喻、口號、華麗形容詞或抽象 AI 套話" in prompt


def test_korean_typography_normalizes_fullwidth_western_punctuation() -> None:
    value = {
        "title": "타로란 무엇인가요？",
        "faq": [{"question": "미래를 알 수 있나요？", "answer": "아니요！"}],
    }

    normalized = multilingual._normalize_korean_typography(value)

    assert normalized == {
        "title": "타로란 무엇인가요?",
        "faq": [{"question": "미래를 알 수 있나요?", "answer": "아니요!"}],
    }


def test_external_operation_resumes_from_saved_output_without_regeneration(tmp_path: Path) -> None:
    output = tmp_path / "external-candidate.json"
    output.write_text('{"articles":[]}', encoding="utf-8")

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("saved operation must not run again")

    payload = multilingual._load_or_generate_external(
        FailIfCalled(),
        "writer",
        "prompt",
        {"type": "object"},
        tmp_path / "writer-operation.json",
        output,
    )

    assert payload == {"articles": []}


def test_edited_candidate_uses_deterministic_gate_and_independent_reviewer(tmp_path: Path) -> None:
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    multilingual.pipeline.write_json(tmp_path / "candidate.json", candidate)

    class ReviewerClient:
        reviewer_model = "reviewer-test"

        def generate_json(self, role: str, _prompt: str, _schema: dict[str, object]) -> dict[str, object]:
            assert role == "reviewer"
            return {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}

    review = multilingual.review_edited_candidate(tmp_path, ReviewerClient())

    assert review["articles"][0]["verdict"] == "APPROVE"
    assert (tmp_path / "editorial-review" / "deterministic-findings.json").read_text() == "[]\n"
    assert (tmp_path / "review.json").is_file()


def test_apply_approved_translation_writes_run_module_and_manifest(tmp_path: Path) -> None:
    static = tmp_path / "app" / "web" / "static"
    static.mkdir(parents=True)
    manifest = static / "article-locales.js"
    manifest.write_text(
        "export const ARTICLE_LOCALE_REGISTRY = [\n];\n",
        encoding="utf-8",
    )
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    article = candidate["articles"][0]
    review = {
        "schema_version": 1,
        "run_id": candidate["run_id"],
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "hard_failure": False,
                "findings": [],
            }
        ],
    }
    approval = build_approval(
        str(candidate["run_id"]),
        candidate["articles"],
        review,
        {str(article["article_id"]): "APPROVE"},
        "test",
    )

    changed = multilingual.apply_approved_translations(
        tmp_path,
        str(candidate["run_id"]),
        brief,
        candidate,
        review,
        approval,
        source_loader=lambda _repo, _article_id: source_article(),
    )

    module = static / "article-locale-translate-test-en.js"
    assert module in changed
    assert module.exists()
    module_text = module.read_text(encoding="utf-8")
    assert '"locale": "en"' in module_text
    assert '"articleId": "TEST-001"' in module_text
    manifest_text = manifest.read_text(encoding="utf-8")
    assert 'from "./article-locale-translate-test-en.js?v=translate-test-en"' in manifest_text
    assert "...TRANSLATE_TEST_EN_ARTICLE_LOCALES" in manifest_text


def test_apply_translation_fails_closed_when_source_changed(tmp_path: Path) -> None:
    static = tmp_path / "app" / "web" / "static"
    static.mkdir(parents=True)
    (static / "article-locales.js").write_text("export const ARTICLE_LOCALE_REGISTRY = [\n];\n", encoding="utf-8")
    brief = translation_brief()
    candidate = translation_candidate()
    article = candidate["articles"][0]
    review = {
        "schema_version": 1,
        "run_id": candidate["run_id"],
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "hard_failure": False,
                "findings": [],
            }
        ],
    }
    approval = build_approval(
        str(candidate["run_id"]),
        candidate["articles"],
        review,
        {str(article["article_id"]): "APPROVE"},
        "test",
    )
    changed_source = source_article()
    changed_source["title"] = "原文後來改過"

    with pytest.raises(ValueError, match="source drift"):
        multilingual.apply_approved_translations(
            tmp_path,
            str(candidate["run_id"]),
            brief,
            candidate,
            review,
            approval,
            source_loader=lambda _repo, _article_id: changed_source,
        )

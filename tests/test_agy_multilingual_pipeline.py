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


def non_tarot_translation_brief(locale: str = "ko") -> dict[str, object]:
    source = {
        "article_id": "FORTUNE-0039",
        "canonical_path": "/articles/bazi/fortune-0039",
        "title": "八字用神是什麼？",
        "description": "用神是依命局失衡處選出的調整方向，不是固定五行，也不能只看單一字。",
        "answer": "先看整體強弱、寒燥與流通，再判斷哪個五行能改善失衡。",
        "tags": ["八字", "用神"],
        "faq": [
            {
                "question": "用神會永遠不變嗎？",
                "answer": "不能脫離完整命局與運勢條件，只用單一規則固定判斷。",
            }
        ],
        "bodySections": [
            {
                "heading": "先找出命局的失衡",
                "paragraphs": ["用神判斷先看日主強弱、寒燥與五行是否能流通。"],
            },
            {
                "heading": "再選擇能改善失衡的方向",
                "paragraphs": ["同一個五行在不同命局中可能有不同作用，不能套用固定答案。"],
            },
        ],
    }
    return {
        "schema_version": 1,
        "run_id": f"auto-i18n-{locale}-fortune-0039",
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"FORTUNE-0039:{locale}",
                "locale": locale,
                "source_article_id": "FORTUNE-0039",
                "source_path": source["canonical_path"],
                "source_sha256": multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }


def non_tarot_external_candidate(
    outline: list[str] | None = None,
) -> dict[str, object]:
    payload = {
        "articles": [
            {
                "slot": "article-01",
                "title": "사주에서 용신은 어떻게 찾나요?",
                "description": "용신은 명식 전체의 불균형을 살핀 뒤 조정 방향을 찾는 개념이며, 한 글자나 고정된 오행만으로 정할 수 없습니다.",
                "answer": "강약과 한난조습, 오행의 흐름을 함께 살핀 뒤 불균형을 줄이는 방향을 찾습니다.",
                "tags": ["사주", "용신"],
                "faq": [
                    {
                        "question": "용신은 항상 같나요?",
                        "answer": "전체 명식과 운의 조건을 벗어나 하나의 규칙으로 고정할 수 없습니다.",
                    }
                ],
                "bodySections": [
                    {
                        "heading": "용신이 답하려는 질문",
                        "paragraphs": ["용신은 명식에서 무엇이 과하거나 부족한지 살피는 출발점입니다."],
                    },
                    {
                        "heading": "강약과 계절을 함께 보는 이유",
                        "paragraphs": ["일간의 강약과 계절의 한난조습을 따로 떼어 판단하지 않습니다."],
                    },
                    {
                        "heading": "오행의 흐름으로 조정 방향 찾기",
                        "paragraphs": ["막힌 흐름을 이어 주거나 지나친 기운을 덜어 내는 방향을 비교합니다."],
                    },
                    {
                        "heading": "고정 공식으로 단정하지 않기",
                        "paragraphs": ["같은 오행도 명식과 운의 조건에 따라 역할이 달라질 수 있습니다."],
                    },
                ],
            }
        ]
    }
    if outline is not None:
        for section, heading in zip(
            payload["articles"][0]["bodySections"],
            outline,
        ):
            section["heading"] = heading
    return payload


def external_locale_plan(
    brief: dict[str, object],
    *,
    rebuild_outline: bool = False,
    outline: list[str] | None = None,
    coverage_shift: int = 0,
) -> dict[str, object]:
    fact_package = multilingual._source_fact_package(brief)
    target = fact_package["articles"][0]
    headings = outline or [
        "용신이 답하려는 질문",
        "강약과 계절을 함께 보는 이유",
        "오행의 흐름으로 조정 방향 찾기",
        "고정 공식으로 단정하지 않기",
    ]
    return {
        "articles": [
            {
                "slot": "article-01",
                "locale": brief["articles"][0]["locale"],
                "source_sha256": brief["articles"][0]["source_sha256"],
                "native_search_intent": "사주에서 용신을 판단하는 기준과 한계를 알고 싶다",
                "native_query_phrasings": ["사주 용신 찾는 법", "용신 판단 기준"],
                "article_angle": "고정 공식을 제시하지 않고 판단 순서와 한계를 설명한다",
                "ordered_h2_outline": headings,
                "coverage_mapping": [
                    {
                        "source_fact_id": fact["fact_id"],
                        "planned_h2": headings[
                            (index + coverage_shift) % len(headings)
                        ],
                        "coverage_note": "이 사실과 제한을 해당 절에서 설명한다",
                        "safety_boundary": fact["safety_boundary"],
                    }
                    for index, fact in enumerate(target["facts"])
                ],
                "source_structure_not_copied": [
                    section["heading"]
                    for section in brief["articles"][0]["source"]["bodySections"]
                ],
                "rebuild_outline": rebuild_outline,
            }
        ]
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


def test_translation_apply_gate_uses_translation_mode_without_bypassing_approval() -> None:
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

    approved = multilingual.pipeline.validate_apply_gate(
        candidate["articles"],
        review,
        approval,
        candidate_mode=str(candidate["mode"]),
    )

    assert approved == candidate["articles"]


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
    brief = translation_brief("en")
    plan = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )
    prompt = multilingual._article_prompt(brief, plan, [])

    assert "source claim ledger" in prompt
    assert "不得用常識補完" in prompt
    assert "禁止用比喻、口號、華麗形容詞或抽象 AI 套話" in prompt


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_locale_plan_and_article_prompts_are_topic_neutral(locale: str) -> None:
    brief = non_tarot_translation_brief(locale)
    external_plan = external_locale_plan(non_tarot_translation_brief())
    external_plan["articles"][0]["locale"] = locale
    external_plan["articles"][0]["source_sha256"] = brief["articles"][0]["source_sha256"]
    plan = multilingual._hydrate_locale_plan(
        brief,
        external_plan,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    serialized_contract = json.dumps(
        multilingual.LOCALE_EDITORIAL_CONTRACTS[locale],
        ensure_ascii=False,
    ).lower()
    plan_prompt = multilingual._plan_prompt(
        brief,
        generation=1,
        prior_plan=None,
        findings=[],
        rebuild_by_slot={"article-01": False},
    )
    article_prompt = multilingual._article_prompt(brief, plan, [])

    for forbidden in (
        "tarot",
        "タロット",
        "타로",
        "upright",
        "reversed",
        "正位置",
        "逆位置",
        "정방향",
        "역방향",
    ):
        assert forbidden not in serialized_contract
        assert forbidden not in plan_prompt.lower()
        assert forbidden not in article_prompt.lower()
    assert "用神" in plan_prompt
    assert "ordered_h2_outline" in article_prompt


def test_article_phase_rejects_missing_invalid_or_mismatched_plan() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    with pytest.raises(ValueError, match="locale plan"):
        multilingual._article_prompt(brief, None, [])

    invalid = json.loads(json.dumps(plan))
    del invalid["articles"][0]["coverage_mapping"]
    with pytest.raises(ValueError, match="locale plan"):
        multilingual._article_prompt(brief, invalid, [])

    mismatched = json.loads(json.dumps(plan))
    mismatched["articles"][0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source hash"):
        multilingual._article_prompt(brief, mismatched, [])


def test_invalid_generated_plan_fails_before_article_candidate(tmp_path: Path) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)

    class InvalidPlanClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            payload = external_locale_plan(brief)
            del payload["articles"][0]["coverage_mapping"]
            return payload

    with pytest.raises(ValueError, match="locale plan"):
        multilingual.run_writer_reviewer(
            tmp_path,
            InvalidPlanClient(),
            max_repairs=2,
        )

    assert not (tmp_path / "attempts/01/locale-plan.json").exists()
    assert not (tmp_path / "attempts/01/article-operation.json").exists()
    assert not (tmp_path / "candidate.json").exists()
    assert not (tmp_path / "review.json").exists()


def test_outline_rebuild_rejects_synonym_headings_with_same_fact_topology() -> None:
    brief = non_tarot_translation_brief()
    prior = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )
    synonym_only = external_locale_plan(
        brief,
        rebuild_outline=True,
        outline=[
            "용신이 해결하는 핵심 질문",
            "강약과 절기를 같이 확인하는 까닭",
            "오행 흐름에서 조정 방향 고르기",
            "하나의 공식으로 결론 내리지 않기",
        ],
    )

    with pytest.raises(ValueError, match="reused prior outline topology"):
        multilingual._hydrate_locale_plan(
            brief,
            synonym_only,
            generation=2,
            rebuild_by_slot={"article-01": True},
            prior_plan=prior,
        )


@pytest.mark.parametrize(
    "finding_code",
    [
        "AI_TEMPLATE_STYLE",
        "SOURCE_SYNTAX_TRANSFER",
        "NON_NATIVE_SEARCH_INTENT",
    ],
)
def test_repeated_native_finding_forces_new_outline_topology(
    tmp_path: Path,
    finding_code: str,
) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    plan_count = 0
    review_count = 0
    last_outline: list[str] | None = None

    class ScriptedClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal plan_count, review_count, last_outline
            if "native_search_intent" in json.dumps(schema):
                plan_count += 1
                if plan_count == 3:
                    payload = external_locale_plan(
                        brief,
                        rebuild_outline=True,
                        coverage_shift=1,
                        outline=[
                            "용신을 검색할 때 가장 먼저 묻는 것",
                            "명식 전체에서 불균형 확인하기",
                            "조정 후보를 비교하는 순서",
                            "단정 대신 조건을 남기는 이유",
                        ],
                    )
                else:
                    payload = external_locale_plan(brief)
                last_outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(last_outline)
            review_count += 1
            if review_count < 3:
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "verdict": "REJECT",
                                "findings": [
                                    {
                                        "code": finding_code,
                                        "message": "구조가 이전 세대와 같은 템플릿입니다",
                                    }
                                ],
                        }
                    ]
                }
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    multilingual.run_writer_reviewer(tmp_path, ScriptedClient(), max_repairs=2)

    first = json.loads((tmp_path / "attempts/01/locale-plan.json").read_text())
    third = json.loads((tmp_path / "attempts/03/locale-plan.json").read_text())
    assert first["articles"][0]["rebuild_outline"] is False
    assert third["articles"][0]["rebuild_outline"] is True
    assert (
        third["articles"][0]["ordered_h2_outline"]
        != first["articles"][0]["ordered_h2_outline"]
    )


def _write_rejected_deferred_lineage(run_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    brief = non_tarot_translation_brief()
    candidate = multilingual._hydrate_candidate(brief, non_tarot_external_candidate())
    review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": "FORTUNE-0039:ko",
                "candidate_sha256": article_sha256(candidate["articles"][0]),
                "verdict": "REJECT",
                "findings": [
                    {
                        "code": "AI_TEMPLATE_STYLE",
                        "message": "기존 구조를 반복합니다",
                    }
                ],
            }
        ],
    }
    multilingual.pipeline.write_json(run_dir / "brief.json", brief)
    multilingual.pipeline.write_json(run_dir / "candidate.json", candidate)
    multilingual.pipeline.write_json(run_dir / "review.json", review)
    for attempt in range(1, 4):
        attempt_dir = run_dir / "attempts" / f"{attempt:02d}"
        multilingual.pipeline.write_json(
            attempt_dir / "external-review.json",
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": [
                            {
                                "code": "AI_TEMPLATE_STYLE",
                                "message": f"generation {attempt} repeats the template",
                            }
                        ],
                    }
                ]
            },
        )
        (attempt_dir / "immutable-marker.txt").write_text(
            f"legacy-attempt-{attempt}\n",
            encoding="utf-8",
        )
    return candidate, review


def test_deferred_lineage_continuation_is_incremental_immutable_and_replayable(
    tmp_path: Path,
) -> None:
    old_candidate, _old_review = _write_rejected_deferred_lineage(tmp_path)
    legacy_bytes = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "attempts").rglob("*")
        if path.is_file()
    }
    calls: list[str] = []
    last_outline: list[str] | None = None

    class ApprovingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal last_outline
            calls.append(role)
            if "native_search_intent" in json.dumps(schema):
                payload = external_locale_plan(
                    non_tarot_translation_brief(),
                    rebuild_outline=True,
                    coverage_shift=1,
                    outline=[
                        "용신 검색 질문부터 정리하기",
                        "명식의 강약과 계절 확인하기",
                        "오행의 흐름으로 후보 비교하기",
                        "조건에 따라 결론을 제한하기",
                    ],
                )
                last_outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(last_outline)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    candidate, review = multilingual.continue_writer_reviewer(
        tmp_path,
        ApprovingClient(),
        max_repairs=2,
    )

    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["status"] == "complete"
    assert not (tmp_path / "continuation/root-update.json").exists()
    assert state["started_after_generation"] == 3
    assert state["completed_generations"] == [4]
    assert (tmp_path / "generations/04/locale-plan.json").is_file()
    assert candidate["run_id"] == old_candidate["run_id"]
    assert review["run_id"] == old_candidate["run_id"]
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert not (tmp_path / "approval.json").exists()
    assert not (tmp_path / "run-evidence.json").exists()
    assert legacy_bytes == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "attempts").rglob("*")
        if path.is_file()
    }

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("completed continuation must replay root artifacts")

    replayed_candidate, replayed_review = multilingual.continue_writer_reviewer(
        tmp_path,
        FailIfCalled(),
        max_repairs=2,
    )
    assert replayed_candidate == candidate
    assert replayed_review == review
    assert calls == ["writer", "writer", "reviewer"]


def test_pending_continuation_does_not_advance_or_overwrite_roots(tmp_path: Path) -> None:
    old_candidate, old_review = _write_rejected_deferred_lineage(tmp_path)
    prompts: list[str] = []

    class ExternalJobPending(RuntimeError):
        pass

    class PendingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def _outbox_transport(self) -> None:
            raise AssertionError

        transport = _outbox_transport

        def generate_json(
            self,
            _role: str,
            prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            prompts.append(prompt)
            raise ExternalJobPending("synthetic pending plan")

    client = PendingClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="synthetic pending plan"):
            multilingual.continue_writer_reviewer(tmp_path, client, max_repairs=2)

    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["status"] == "active"
    assert state["next_generation"] == 4
    assert state["completed_generations"] == []
    assert sorted(path.name for path in (tmp_path / "generations").iterdir()) == ["04"]
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review
    assert prompts[0] == prompts[1]
    for forbidden in ("approval.json", "apply.json", "publish.json", "run-evidence.json"):
        assert not (tmp_path / forbidden).exists()


def test_root_update_transaction_recovers_candidate_review_and_state_together(
    tmp_path: Path,
) -> None:
    _old_candidate, old_review = _write_rejected_deferred_lineage(tmp_path)
    brief = non_tarot_translation_brief()
    new_candidate = multilingual._hydrate_candidate(
        brief,
        non_tarot_external_candidate(),
    )
    new_review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": "FORTUNE-0039:ko",
                "candidate_sha256": article_sha256(new_candidate["articles"][0]),
                "verdict": "APPROVE",
                "findings": [],
            }
        ],
    }
    state = multilingual._load_or_create_continuation_state(
        tmp_path,
        brief,
        old_review,
        max_repairs=2,
    )
    state["status"] = "complete"
    multilingual.pipeline.write_json(
        tmp_path / "continuation/root-update.json",
        {
            "schema_version": 1,
            "candidate": new_candidate,
            "review": new_review,
            "state": state,
        },
    )
    multilingual.pipeline.write_json(
        tmp_path / "candidate.json",
        {"interrupted": True},
    )

    multilingual._recover_root_result(tmp_path)

    assert json.loads((tmp_path / "candidate.json").read_text()) == new_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == new_review
    assert json.loads((tmp_path / "continuation/state.json").read_text()) == state
    assert not (tmp_path / "continuation/root-update.json").exists()


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


def test_transport_failure_does_not_advance_translation_semantic_attempt(
    tmp_path: Path,
) -> None:
    brief = translation_brief("en")
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)

    class FailedTransportClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            failure = RuntimeError("closed synthetic transport failure")
            failure.failure_category = "NETWORK"  # type: ignore[attr-defined]
            failure.transport_attempts = 3  # type: ignore[attr-defined]
            failure.request_sha256 = "a" * 64  # type: ignore[attr-defined]
            raise failure

    with pytest.raises(RuntimeError, match="closed synthetic transport failure"):
        multilingual.run_writer_reviewer(
            tmp_path,
            FailedTransportClient(),
            max_repairs=2,
        )

    receipt = json.loads(
        (tmp_path / "attempts/01/plan-operation.json").read_text()
    )
    assert receipt["failure_category"] == "NETWORK"
    assert receipt["transport_attempts"] == 3
    assert receipt["request_sha256"] == "a" * 64
    assert not (tmp_path / "attempts/02").exists()
    for forbidden in ("candidate.json", "review.json", "approval.json", "run-evidence.json"):
        assert not (tmp_path / forbidden).exists()


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


def test_enqueue_article_translations_creates_three_independent_idempotent_runs(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"

    first = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    second = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        source_loader=lambda _repo, _article_id: source_article(),
    )

    assert first == second
    assert {item["locale"] for item in first} == {"en", "ja", "ko"}
    assert len(list((queue_root / "runs").glob("*.json"))) == 3
    for item in first:
        brief = json.loads((Path(item["run_dir"]) / "brief.json").read_text(encoding="utf-8"))
        assert brief["mode"] == "translate_existing"
        assert len(brief["articles"]) == 1
        assert brief["articles"][0]["locale"] == item["locale"]


def test_enqueue_article_translations_does_not_overwrite_registered_source(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    changed = source_article()
    changed["title"] = "來源文章已更新"

    with pytest.raises(ValueError, match="source drift"):
        multilingual.enqueue_article_translations(
            tmp_path,
            queue_root,
            source_run_id="source-run-001",
            article_id="TEST-001",
            source_loader=lambda _repo, _article_id: changed,
        )

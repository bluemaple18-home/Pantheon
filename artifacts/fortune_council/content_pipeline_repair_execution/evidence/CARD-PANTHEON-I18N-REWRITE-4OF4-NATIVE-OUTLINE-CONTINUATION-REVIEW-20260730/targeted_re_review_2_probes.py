"""Repair-2 candidate 的 final targeted re-review 獨立 probes。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from scripts import agy_gemini_outbox as outbox
from scripts import agy_multilingual_pipeline as multilingual


SPEC = importlib.util.spec_from_file_location(
    "repair_2_candidate_tests",
    Path("tests/test_agy_multilingual_pipeline.py"),
)
assert SPEC is not None and SPEC.loader is not None
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)


def test_later_plan_pending_replay_preserves_full_external_identity(
    tmp_path: Path,
) -> None:
    old_candidate, old_review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    brief = FIXTURES.non_tarot_translation_brief()
    queue_root = tmp_path / "synthetic-queue"
    plan_calls = 0
    last_outline: list[str] | None = None
    pending_prompts: list[str] = []
    pending_requests: list[dict[str, object]] = []

    class ExternalJobPending(RuntimeError):
        pass

    class PendingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def _outbox_transport(self) -> None:
            raise AssertionError("transport marker only")

        transport = _outbox_transport

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal plan_calls, last_outline
            if "native_search_intent" in json.dumps(schema):
                plan_calls += 1
                if plan_calls == 1:
                    payload = FIXTURES.external_locale_plan(
                        brief,
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
                request = outbox.create_external_request(
                    queue_root,
                    namespace="cycle3-plan",
                    role=role,
                    model=self.writer_model,
                    prompt=prompt,
                    response_schema=schema,
                )
                pending_prompts.append(prompt)
                pending_requests.append(request)
                pending = ExternalJobPending("synthetic later plan pending")
                pending.request_sha256 = request["request_sha256"]
                raise pending
            if role == "writer":
                return FIXTURES.non_tarot_external_candidate(last_outline)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": [
                            {
                                "code": "AI_TEMPLATE_STYLE",
                                "message": "still repeats the template",
                            }
                        ],
                    }
                ]
            }

    client = PendingClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="later plan pending"):
            multilingual.continue_writer_reviewer(
                tmp_path,
                client,
                max_repairs=2,
            )

    prompt_hashes = [
        hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        for prompt in pending_prompts
    ]
    assert len(pending_prompts) == 2
    assert pending_prompts[0].encode("utf-8") == pending_prompts[1].encode("utf-8")
    assert prompt_hashes[0] == prompt_hashes[1]
    assert pending_requests[0]["request_sha256"] == pending_requests[1]["request_sha256"]
    assert pending_requests[0]["job_id"] == pending_requests[1]["job_id"]
    assert len(list((queue_root / "outbox").glob("*.json"))) == 1
    receipt = json.loads(
        (tmp_path / "generations/05/plan-operation.json").read_text()
    )
    assert receipt["prompt_sha256"] == prompt_hashes[0]
    assert receipt["request_sha256"] == pending_requests[0]["request_sha256"]
    assert len(list((tmp_path / "generations/05").glob("plan-operation*.json"))) == 1
    assert not (tmp_path / "generations/05/external-plan.json").exists()
    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["completed_generations"] == [4]
    assert state["next_generation"] == 5
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review


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


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize(
    "field",
    [
        "native_search_intent",
        "native_query_phrasings",
        "article_angle",
        "ordered_h2_outline",
        "coverage_note",
    ],
)
def test_each_semantic_item_rejects_unambiguous_all_english(
    locale: str,
    field: str,
) -> None:
    brief = FIXTURES.non_tarot_translation_brief(locale)
    external = FIXTURES.external_locale_plan(brief)
    item = external["articles"][0]
    _replace_semantic_item(
        item,
        field,
        "READERS EVALUATE SOURCES CAREFULLY",
    )

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_valid_japanese_kanji_only_heading_is_not_rejected() -> None:
    brief = FIXTURES.non_tarot_translation_brief("ja")
    external = FIXTURES.external_locale_plan(brief)
    item = external["articles"][0]
    _replace_semantic_item(item, "ordered_h2_outline", "実践方法")

    multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )


def _reverse_dict_order(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _reverse_dict_order(value[key])
            for key in reversed(list(value))
        }
    if isinstance(value, list):
        return [_reverse_dict_order(item) for item in value]
    return value


def test_plan_prompt_structured_fragments_ignore_dict_insertion_order() -> None:
    brief = FIXTURES.non_tarot_translation_brief("ko")
    prior_plan = multilingual._hydrate_locale_plan(
        brief,
        FIXTURES.external_locale_plan(brief),
        generation=4,
        rebuild_by_slot={"article-01": False},
    )
    findings = [
        {
            "article_id": brief["articles"][0]["translation_id"],
            "code": "AI_TEMPLATE_STYLE",
            "message": "repeat",
        }
    ]
    rebuild = {"article-01": True}
    expected = multilingual._plan_prompt(
        brief,
        generation=5,
        prior_plan=prior_plan,
        findings=findings,
        rebuild_by_slot=rebuild,
    )
    actual = multilingual._plan_prompt(
        _reverse_dict_order(brief),
        generation=5,
        prior_plan=_reverse_dict_order(prior_plan),
        findings=_reverse_dict_order(findings),
        rebuild_by_slot=_reverse_dict_order(rebuild),
    )

    assert actual == expected

"""Repair-candidate-only probes for targeted re-review cycle 2."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from scripts import agy_multilingual_pipeline as multilingual


SPEC = importlib.util.spec_from_file_location(
    "repair_candidate_tests",
    Path("tests/test_agy_multilingual_pipeline.py"),
)
assert SPEC is not None and SPEC.loader is not None
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)


def test_locale_gate_rejects_wrong_language_outline_when_other_fields_are_native() -> None:
    brief = FIXTURES.non_tarot_translation_brief("ko")
    external = FIXTURES.external_locale_plan(brief)
    outline = [
        "What the useful element answers",
        "Check strength and season",
        "Compare the flow of elements",
        "Avoid a fixed conclusion",
    ]
    external["articles"][0]["ordered_h2_outline"] = outline
    for index, mapping in enumerate(external["articles"][0]["coverage_mapping"]):
        mapping["planned_h2"] = outline[index % len(outline)]

    with pytest.raises(ValueError, match="native|locale|language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_later_generation_plan_pending_replay_keeps_prompt_identity(
    tmp_path: Path,
) -> None:
    old_candidate, old_review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    brief = FIXTURES.non_tarot_translation_brief()
    plan_calls = 0
    last_outline: list[str] | None = None
    pending_prompts: list[str] = []

    class ExternalJobPending(RuntimeError):
        pass

    class LaterPlanPendingClient:
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
                pending_prompts.append(prompt)
                raise ExternalJobPending("synthetic later plan pending")
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

    client = LaterPlanPendingClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="later plan pending"):
            multilingual.continue_writer_reviewer(tmp_path, client, max_repairs=2)

    assert len(pending_prompts) == 2
    prompt_hashes = [
        hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        for prompt in pending_prompts
    ]
    assert pending_prompts[0] == pending_prompts[1], prompt_hashes
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review
    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["completed_generations"] == [4]
    assert state["next_generation"] == 5


def test_future_generation_directory_fails_closed(tmp_path: Path) -> None:
    _candidate, review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    brief = FIXTURES.non_tarot_translation_brief()
    multilingual._load_or_create_continuation_state(
        tmp_path,
        brief,
        review,
        max_repairs=2,
    )
    (tmp_path / "generations/09").mkdir(parents=True)

    with pytest.raises(ValueError, match="generation directories"):
        multilingual._load_or_create_continuation_state(
            tmp_path,
            brief,
            review,
            max_repairs=2,
        )

"""Candidate-only adversarial probes for the independent Review evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as pipeline


SPEC = importlib.util.spec_from_file_location(
    "native_outline_candidate_tests",
    Path("tests/test_agy_multilingual_pipeline.py"),
)
assert SPEC is not None and SPEC.loader is not None
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)


def _approved_review(
    brief: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": candidate["articles"][0]["article_id"],
                "candidate_sha256": pipeline.article_sha256(candidate["articles"][0]),
                "verdict": "APPROVE",
                "findings": [],
            }
        ],
    }


def test_requirement_rejects_cross_locale_plan() -> None:
    brief = FIXTURES.non_tarot_translation_brief("ko")
    external = FIXTURES.external_locale_plan(brief)
    item = external["articles"][0]
    item["native_search_intent"] = "How to choose a useful element in a birth chart"
    item["native_query_phrasings"] = ["how to find the useful element"]
    item["article_angle"] = "Explain the decision order and its limits"
    item["ordered_h2_outline"] = [
        "What the useful element answers",
        "Check strength and season",
        "Compare the flow of elements",
        "Avoid a fixed conclusion",
    ]
    for index, mapping in enumerate(item["coverage_mapping"]):
        mapping["planned_h2"] = item["ordered_h2_outline"][
            index % len(item["ordered_h2_outline"])
        ]
        mapping["coverage_note"] = "Cover this fact in the selected section"

    with pytest.raises(ValueError, match="native|locale|language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_requirement_rebuilds_repeated_mirrored_structure() -> None:
    brief = FIXTURES.non_tarot_translation_brief()
    article_id = brief["articles"][0]["translation_id"]
    history = [
        [{"article_id": article_id, "code": "MIRRORED_STRUCTURE", "message": "first"}],
        [{"article_id": article_id, "code": "MIRRORED_STRUCTURE", "message": "second"}],
    ]

    assert multilingual._rebuild_authority(brief, history)["article-01"] is True


def test_non_consecutive_or_cross_article_findings_do_not_rebuild() -> None:
    brief = {
        "articles": [
            {"translation_id": "article-a"},
            {"translation_id": "article-b"},
        ]
    }
    history = [
        [{"article_id": "article-a", "code": "AI_TEMPLATE_STYLE", "message": "a1"}],
        [{"article_id": "article-b", "code": "AI_TEMPLATE_STYLE", "message": "b2"}],
        [{"article_id": "article-a", "code": "AI_TEMPLATE_STYLE", "message": "a3"}],
    ]

    assert multilingual._rebuild_authority(brief, history) == {
        "article-01": False,
        "article-02": False,
    }


def test_requirement_first_continuation_uses_root_review_findings(
    tmp_path: Path,
) -> None:
    _candidate, review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    review["articles"][0]["findings"] = [
        {
            "code": "NON_NATIVE_SEARCH_INTENT",
            "message": "ROOT-REVIEW-AUTHORITY-MARKER",
        }
    ]
    pipeline.write_json(tmp_path / "review.json", review)
    prompts: list[str] = []

    class CaptureClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            prompts.append(prompt)
            raise RuntimeError("capture only")

    with pytest.raises(RuntimeError, match="capture only"):
        multilingual.continue_writer_reviewer(tmp_path, CaptureClient(), max_repairs=2)

    assert prompts
    assert "ROOT-REVIEW-AUTHORITY-MARKER" in prompts[0]


def test_requirement_complete_state_rejects_review_drift(tmp_path: Path) -> None:
    _candidate, review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    brief = FIXTURES.non_tarot_translation_brief()
    state = multilingual._load_or_create_continuation_state(
        tmp_path,
        brief,
        review,
        max_repairs=2,
    )
    state["status"] = "complete"
    pipeline.write_json(tmp_path / "continuation/state.json", state)
    drifted = copy.deepcopy(review)
    drifted["articles"][0]["findings"] = [
        {"code": "NON_NATIVE_SEARCH_INTENT", "message": "different review"}
    ]
    pipeline.write_json(tmp_path / "review.json", drifted)

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("complete replay must not call provider")

    with pytest.raises(ValueError, match="identity"):
        multilingual.continue_writer_reviewer(tmp_path, FailIfCalled(), max_repairs=2)


def test_requirement_attempt_number_gap_fails_closed(tmp_path: Path) -> None:
    _candidate, review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    shutil.rmtree(tmp_path / "attempts/02")
    brief = FIXTURES.non_tarot_translation_brief()

    with pytest.raises(ValueError, match="generation|contiguous|lineage"):
        multilingual._load_or_create_continuation_state(
            tmp_path,
            brief,
            review,
            max_repairs=2,
        )


def test_pending_rebuild_article_replay_keeps_identity_and_roots(
    tmp_path: Path,
) -> None:
    old_candidate, old_review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    brief = FIXTURES.non_tarot_translation_brief()
    calls: list[tuple[str, str]] = []

    class ExternalJobPending(RuntimeError):
        pass

    class PendingArticleClient:
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
            calls.append((role, prompt))
            if "native_search_intent" in json.dumps(schema):
                return FIXTURES.external_locale_plan(
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
            raise ExternalJobPending("synthetic pending article")

    client = PendingArticleClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="pending article"):
            multilingual.continue_writer_reviewer(tmp_path, client, max_repairs=2)

    article_prompts = [prompt for role, prompt in calls if role == "writer"][1:]
    assert len(calls) == 3
    assert article_prompts[0] == article_prompts[1]
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review


@pytest.mark.parametrize("failure_target", ["transaction", "candidate", "review", "state"])
def test_atomic_root_write_interruptions_recover_or_preserve_old_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_target: str,
) -> None:
    run_dir = tmp_path / failure_target
    old_candidate, old_review = FIXTURES._write_rejected_deferred_lineage(run_dir)
    brief = FIXTURES.non_tarot_translation_brief()
    new_candidate = copy.deepcopy(old_candidate)
    new_candidate["articles"][0]["title"] += " 수정"
    new_review = _approved_review(brief, new_candidate)
    state = multilingual._load_or_create_continuation_state(
        run_dir,
        brief,
        old_review,
        max_repairs=2,
    )
    state["status"] = "complete"
    targets = {
        "transaction": run_dir / "continuation/root-update.json",
        "candidate": run_dir / "candidate.json",
        "review": run_dir / "review.json",
        "state": run_dir / "continuation/state.json",
    }
    original_atomic = multilingual._atomic_write_json
    failed = False

    def interrupted(path: Path, payload: object) -> None:
        nonlocal failed
        if path == targets[failure_target] and not failed:
            failed = True
            raise OSError(f"synthetic {failure_target} interruption")
        original_atomic(path, payload)

    monkeypatch.setattr(multilingual, "_atomic_write_json", interrupted)
    with pytest.raises(OSError, match="synthetic"):
        multilingual._write_root_result(
            run_dir,
            new_candidate,
            new_review,
            state=state,
        )
    monkeypatch.setattr(multilingual, "_atomic_write_json", original_atomic)

    if failure_target == "transaction":
        assert json.loads((run_dir / "candidate.json").read_text()) == old_candidate
        assert json.loads((run_dir / "review.json").read_text()) == old_review
        return

    multilingual._recover_root_result(run_dir)
    assert json.loads((run_dir / "candidate.json").read_text()) == new_candidate
    assert json.loads((run_dir / "review.json").read_text()) == new_review
    assert json.loads((run_dir / "continuation/state.json").read_text()) == state
    assert not (run_dir / "continuation/root-update.json").exists()


def test_root_transaction_unlink_interruption_replays_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_candidate, old_review = FIXTURES._write_rejected_deferred_lineage(tmp_path)
    brief = FIXTURES.non_tarot_translation_brief()
    new_candidate = copy.deepcopy(old_candidate)
    new_candidate["articles"][0]["title"] += " 수정"
    new_review = _approved_review(brief, new_candidate)
    state = multilingual._load_or_create_continuation_state(
        tmp_path,
        brief,
        old_review,
        max_repairs=2,
    )
    state["status"] = "complete"
    transaction_path = tmp_path / "continuation/root-update.json"
    original_unlink = Path.unlink
    failed = False

    def interrupted_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal failed
        if path == transaction_path and not failed:
            failed = True
            raise OSError("synthetic unlink interruption")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", interrupted_unlink)
    with pytest.raises(OSError, match="unlink interruption"):
        multilingual._write_root_result(
            tmp_path,
            new_candidate,
            new_review,
            state=state,
        )
    monkeypatch.setattr(Path, "unlink", original_unlink)

    assert transaction_path.is_file()
    multilingual._recover_root_result(tmp_path)
    assert json.loads((tmp_path / "candidate.json").read_text()) == new_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == new_review
    assert json.loads((tmp_path / "continuation/state.json").read_text()) == state
    assert not transaction_path.exists()

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import scripts.agy_seo_copy_pipeline as pipeline
import scripts.pantheon_content_batch as batch
import scripts.pantheon_topic_identity as identity
import scripts.pantheon_topic_reservation as reservation


def _topic(index: int) -> dict[str, Any]:
    topic: dict[str, Any] = {
        "source": "test_inventory",
        "source_id": f"T{index:02d}",
        "source_matrix_ref": f"test_inventory:T{index:02d}",
        "domain": "fortune",
        "entity": "tarot",
        "semantic_intent": f"命理問題 {index}",
        "scenario": f"scenario-{index}",
        "relationship_context": "general",
        "time_window": "current",
        "template_family": "topic-question-guide",
        "product_intent": "reflection",
        "search_volume": "UNKNOWN",
        "priority_score": 0,
        "coverage_status": "AVAILABLE",
        "duplicate_of_topic_id": None,
        "duplicate_reason": None,
        "title": f"命理問題 {index} 怎麼看？",
        "article_id": "",
        "route": "",
        "canonical": "",
        "slug": "",
    }
    topic["topic_id"] = identity.build_topic_id(topic)
    return topic


def _plan(tmp_path: Path, count: int = 10) -> dict[str, Any]:
    return batch.build_batch_plan(
        tmp_path,
        topics=[_topic(index) for index in range(1, count + 1)],
        existing_articles=[],
        slot_ids=[f"slot-{index:02d}" for index in range(1, count + 1)],
        publication_date="2026-09-04",
    )


def _records(root: Path) -> dict[str, dict[str, Any]]:
    directory = root / "reservations"
    if not directory.exists():
        return {}
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    ]
    return {record["topic_id"]: record for record in records}


def _run_bytes(root: Path, run_id: str) -> bytes:
    return (root / run_id / "brief.json").read_bytes()


def _recompute_plan_integrity(plan: dict[str, Any]) -> None:
    digest_slots = []
    for slot in plan["slots"]:
        value = deepcopy(slot)
        value.pop("lineage", None)
        digest_slots.append(value)
    plan["batch_digest"] = batch._digest(
        {
            "schema_version": plan["schema_version"],
            "snapshot_digest": plan["snapshot_digest"],
            "slots": digest_slots,
        }
    )
    for slot in plan["slots"]:
        slot["lineage"] = {
            "snapshot_digest": plan["snapshot_digest"],
            "batch_digest": plan["batch_digest"],
            "topic_id": slot["topic_id"],
            "run_id": slot["run_id"],
            "slot_id": slot["slot_id"],
            "target_article_id": slot["target"]["article_id"],
            "target_route": slot["target"]["route"],
        }


@pytest.mark.parametrize("count", [4, 10])
def test_plan_is_unique_and_deterministic(tmp_path: Path, count: int) -> None:
    first = _plan(tmp_path, count)
    repeated = _plan(tmp_path, count)

    assert first == repeated
    assert batch.batch_plan_bytes(first) == batch.batch_plan_bytes(repeated)
    assert set(first["metrics"]) == set(batch.METRIC_BUCKETS)
    assert set(first["metrics"].values()) == {0}
    for field in ("topic_id", "run_id", "slot_id", "lane_id"):
        values = [slot[field] for slot in first["slots"]]
        assert len(values) == len(set(values)) == count
    for field in ("article_id", "route", "slug"):
        values = [slot["target"][field] for slot in first["slots"]]
        assert len(values) == len(set(values)) == count
    assert all(
        slot["lineage"]
        == {
            "snapshot_digest": first["snapshot_digest"],
            "batch_digest": first["batch_digest"],
            "topic_id": slot["topic_id"],
            "run_id": slot["run_id"],
            "slot_id": slot["slot_id"],
            "target_article_id": slot["target"]["article_id"],
            "target_route": slot["target"]["route"],
        }
        for slot in first["slots"]
    )


def test_checkpoint_four_is_prefix_of_same_ten_slot_plan(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    first_four = batch.checkpoint_slots(plan, 4)
    all_ten = batch.checkpoint_slots(plan, 10)

    assert first_four == all_ten[:4]
    assert all(
        slot["lineage"]["batch_digest"] == plan["batch_digest"]
        for slot in all_ten
    )


def test_non_available_and_target_collision_fail_closed(tmp_path: Path) -> None:
    topic = _topic(1)
    with pytest.raises(batch.BatchPlanError, match="REVIEW_NEEDED"):
        batch.build_batch_plan(
            tmp_path,
            topics=[topic],
            existing_articles=[
                {
                    "id": "OTHER",
                    "path": "/articles/other/unique",
                    "title": "其他",
                    "primaryKeyword": topic["semantic_intent"],
                }
            ],
            slot_ids=["slot-01"],
            topic_ids=[topic["topic_id"]],
            publication_date="2026-09-04",
        )

    clean = batch.build_batch_plan(
        tmp_path,
        topics=[topic],
        existing_articles=[],
        slot_ids=["slot-01"],
        topic_ids=[topic["topic_id"]],
        publication_date="2026-09-04",
    )
    with pytest.raises(batch.BatchPlanError, match="target.*COLLISION"):
        batch.build_batch_plan(
            tmp_path,
            topics=[topic],
            existing_articles=[
                {
                    "id": clean["slots"][0]["target"]["article_id"],
                    "path": "/articles/other/unique",
                    "title": "其他",
                    "primaryKeyword": "其他",
                }
            ],
            slot_ids=["slot-01"],
            topic_ids=[topic["topic_id"]],
            publication_date="2026-09-04",
        )


def test_serial_maxima_accepts_more_than_four_digits(tmp_path: Path) -> None:
    topic = _topic(1)
    plan = batch.build_batch_plan(
        tmp_path,
        topics=[topic],
        existing_articles=[
            {
                "id": "OLD",
                "path": "/articles/tarot/tarot-10000",
                "title": "其他",
                "primaryKeyword": "其他",
            }
        ],
        slot_ids=["slot-01"],
        topic_ids=[topic["topic_id"]],
        publication_date="2026-09-04",
    )

    assert plan["slots"][0]["target"]["route"] == "/articles/tarot/tarot-10001"


def test_four_then_ten_reuses_identity_and_only_adds_six(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    first = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    first_bytes = {
        slot["run_id"]: _run_bytes(output_root, slot["run_id"])
        for slot in first["slots"]
    }
    second = batch.prepare_checkpoint(plan, state_root, output_root, count=10)

    assert first["status"] == second["status"] == "READY"
    assert first["batch_digest"] == second["batch_digest"] == plan["batch_digest"]
    assert second["slots"][:4] == first["slots"]
    assert len(_records(state_root)) == 10
    assert {record["status"] for record in _records(state_root).values()} == {
        "RESERVED"
    }
    assert all(
        _run_bytes(output_root, run_id) == content
        for run_id, content in first_bytes.items()
    )
    for slot in second["slots"]:
        brief = json.loads(_run_bytes(output_root, slot["run_id"]))
        pipeline.validate_new_brief(brief)
        assert brief["source"]["topic_id"] == slot["topic_id"]


def test_checkpoint_ten_skips_published_first_four_and_only_prepares_six(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    first = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    first_bytes = {
        slot["run_id"]: _run_bytes(output_root, slot["run_id"])
        for slot in first["slots"]
    }
    for slot in first["slots"]:
        owner = {
            key: slot[key]
            for key in (
                "topic_id",
                "reservation_token",
                "lane_id",
                "run_id",
                "owner_generation",
            )
        }
        assert reservation.activate_topic_reservation(state_root, **owner)["ok"] is True
        assert reservation.schedule_topic_reservation(state_root, **owner)["ok"] is True
        assert reservation.publish_topic_reservation(state_root, **owner)["ok"] is True

    published_topic_ids = {slot["topic_id"] for slot in first["slots"]}

    def reject_published_reclaim(*args: Any, **kwargs: Any) -> dict[str, object]:
        assert kwargs["topic_id"] not in published_topic_ids
        return reservation.claim_topic_reservation(*args, **kwargs)

    second = batch.prepare_checkpoint(
        plan,
        state_root,
        output_root,
        count=10,
        completed_count=4,
        claim_topic=reject_published_reclaim,
    )

    assert second["status"] == "READY"
    assert second["checkpoint_count"] == 10
    assert second["metrics"]["attempted"] == 6
    assert [slot["slot_id"] for slot in second["slots"]] == [
        f"slot-{index:02d}" for index in range(5, 11)
    ]
    assert len(_records(state_root)) == 10
    assert {
        record["status"] for record in _records(state_root).values()
    } == {"PUBLISHED", "RESERVED"}
    assert all(
        _run_bytes(output_root, run_id) == content
        for run_id, content in first_bytes.items()
    )


def test_checkpoint_ten_rejects_completed_prefix_drift_before_new_claim(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    first = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    records_before = _records(state_root)
    (output_root / first["slots"][0]["run_id"] / "brief.json").write_text(
        "{}\n", encoding="utf-8"
    )

    def unexpected_claim(*args: Any, **kwargs: Any) -> dict[str, object]:
        raise AssertionError("completed-prefix validation must precede new claims")

    with pytest.raises(batch.BatchPlanError, match="completed checkpoint output mismatch"):
        batch.prepare_checkpoint(
            plan,
            state_root,
            output_root,
            count=10,
            completed_count=4,
            claim_topic=unexpected_claim,
        )

    assert _records(state_root) == records_before
    assert len(list(output_root.glob("*/brief.json"))) == 4


def test_claim_failure_isolated_to_one_slot(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    calls = 0

    def fail_third(*args: Any, **kwargs: Any) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 3:
            return {"ok": False, "result": "injected_failure", "reservation": None}
        return reservation.claim_topic_reservation(*args, **kwargs)

    receipt = batch.prepare_checkpoint(
        plan,
        tmp_path / "state",
        tmp_path / "runs",
        count=4,
        claim_topic=fail_third,
    )

    assert receipt["status"] == "PARTIAL"
    assert receipt["metrics"]["runtime_failure"] == 1
    assert receipt["metrics"]["duplicate_rejection"] == 0
    assert [slot["status"] for slot in receipt["slots"]] == [
        "PREPARED",
        "PREPARED",
        "RESERVATION_REJECTED",
        "PREPARED",
    ]
    assert set(_records(tmp_path / "state")) == {
        plan["slots"][index]["topic_id"] for index in (0, 1, 3)
    }


def test_failed_prepare_keeps_owned_reservation_for_retry(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    calls = 0

    def fail_first_write(path: Path, payload: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("write failure")
        pipeline.write_json(path, payload)

    failed = batch.prepare_checkpoint(
        plan,
        state_root,
        output_root,
        count=4,
        write_json=fail_first_write,
    )
    first_slot = plan["slots"][0]

    assert failed["slots"][0]["status"] == "PREPARE_FAILED"
    assert _records(state_root)[first_slot["topic_id"]]["status"] == "RESERVED"
    retried = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    assert retried["status"] == "READY"
    assert retried["slots"][0]["reservation_token"] == failed["slots"][0]["reservation_token"]


def test_foreign_reservation_is_preserved_without_blocking_other_slots(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    blocked = plan["slots"][1]
    foreign = reservation.claim_topic_reservation(
        tmp_path / "state",
        topic_id=blocked["topic_id"],
        reservation_token="foreign-token",
        lane_id="foreign-lane",
        run_id="foreign-run",
        semantic_exclusion_key=blocked["semantic_exclusion_key"],
        ttl_seconds=60,
    )
    assert foreign["ok"] is True

    receipt = batch.prepare_checkpoint(
        plan, tmp_path / "state", tmp_path / "runs", count=4
    )
    records = _records(tmp_path / "state")

    assert receipt["status"] == "PARTIAL"
    assert receipt["slots"][1]["status"] == "RESERVATION_REJECTED"
    assert receipt["slots"][1]["metric_bucket"] == "duplicate_rejection"
    assert receipt["metrics"]["duplicate_rejection"] == 1
    assert receipt["metrics"]["runtime_failure"] == 0
    assert records[blocked["topic_id"]]["reservation_token"] == "foreign-token"
    assert sum(slot["status"] == "PREPARED" for slot in receipt["slots"]) == 3


def test_replay_rechecks_owner_and_does_not_report_foreign_slot_prepared(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    first = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    stolen = first["slots"][0]
    released = reservation.release_topic_reservation(
        state_root,
        topic_id=stolen["topic_id"],
        reservation_token=stolen["reservation_token"],
        lane_id=stolen["lane_id"],
        run_id=stolen["run_id"],
        owner_generation=stolen["owner_generation"],
    )
    assert released["ok"] is True
    slot = plan["slots"][0]
    foreign = reservation.claim_topic_reservation(
        state_root,
        topic_id=slot["topic_id"],
        reservation_token="foreign-token",
        lane_id="foreign-lane",
        run_id="foreign-run",
        semantic_exclusion_key=slot["semantic_exclusion_key"],
        ttl_seconds=60,
    )
    assert foreign["ok"] is True

    replay = batch.prepare_checkpoint(plan, state_root, output_root, count=4)

    assert replay["status"] == "PARTIAL"
    assert replay["slots"][0]["status"] == "RESERVATION_REJECTED"
    assert _records(state_root)[slot["topic_id"]]["reservation_token"] == "foreign-token"


def test_post_commit_claim_exception_is_reconciled(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    raised: set[str] = set()

    def mutate_then_raise(*args: Any, **kwargs: Any) -> dict[str, object]:
        result = reservation.claim_topic_reservation(*args, **kwargs)
        topic_id = str(kwargs["topic_id"])
        if topic_id not in raised:
            raised.add(topic_id)
            raise OSError("post-commit failure")
        return result

    receipt = batch.prepare_checkpoint(
        plan,
        tmp_path / "state",
        tmp_path / "runs",
        count=4,
        claim_topic=mutate_then_raise,
    )

    assert receipt["status"] == "READY"
    assert len(raised) == 4


def test_non_io_claim_error_is_not_retried(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    calls = 0

    def programming_error(*args: Any, **kwargs: Any) -> dict[str, object]:
        nonlocal calls
        calls += 1
        raise TypeError("programming error")

    receipt = batch.prepare_checkpoint(
        plan,
        tmp_path / "state",
        tmp_path / "runs",
        count=4,
        claim_topic=programming_error,
    )

    assert calls == 4
    assert {slot["status"] for slot in receipt["slots"]} == {
        "RESERVATION_UNCERTAIN"
    }
    assert receipt["metrics"]["runtime_failure"] == 4


def test_unavailable_reservation_fails_closed_as_runtime(tmp_path: Path) -> None:
    plan = _plan(tmp_path)

    def unavailable(*args: Any, **kwargs: Any) -> dict[str, object]:
        return {"ok": False, "result": "unavailable", "reservation": None}

    receipt = batch.prepare_checkpoint(
        plan,
        tmp_path / "state",
        tmp_path / "runs",
        count=4,
        claim_topic=unavailable,
    )

    assert receipt["metrics"]["duplicate_rejection"] == 0
    assert receipt["metrics"]["runtime_failure"] == 4
    assert {slot["metric_bucket"] for slot in receipt["slots"]} == {
        "runtime_failure"
    }


def test_invalid_run_id_and_tampered_output_fail_closed(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    tampered = deepcopy(plan)
    tampered["slots"][0]["run_id"] = "../escape"
    with pytest.raises(batch.BatchPlanError, match="invalid run_id"):
        batch.prepare_checkpoint(
            tampered,
            tmp_path / "state-invalid",
            tmp_path / "runs-invalid",
            count=4,
        )

    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    first = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    (output_root / first["slots"][0]["run_id"] / "brief.json").write_text(
        "{}\n", encoding="utf-8"
    )
    replay = batch.prepare_checkpoint(plan, state_root, output_root, count=4)
    assert replay["status"] == "PARTIAL"
    assert replay["slots"][0]["status"] == "OUTPUT_CONFLICT"


def test_invalid_brief_shape_fails_before_any_reservation(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan["slots"][0]["topic"].pop("title")
    digest_slots = []
    for slot in plan["slots"]:
        value = deepcopy(slot)
        value.pop("lineage", None)
        digest_slots.append(value)
    plan["batch_digest"] = batch._digest(
        {
            "schema_version": plan["schema_version"],
            "snapshot_digest": plan["snapshot_digest"],
            "slots": digest_slots,
        }
    )
    for slot in plan["slots"]:
        slot["lineage"]["batch_digest"] = plan["batch_digest"]

    with pytest.raises(KeyError, match="title"):
        batch.prepare_checkpoint(
            plan, tmp_path / "state", tmp_path / "runs", count=4
        )

    assert _records(tmp_path / "state") == {}
    assert not (tmp_path / "runs").exists()


def test_cli_replays_one_frozen_plan_after_corpus_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus: list[dict[str, Any]] = []
    monkeypatch.setattr(
        batch, "load_canonical_topics", lambda repo_root: [_topic(index) for index in range(1, 11)]
    )
    monkeypatch.setattr(
        identity, "load_existing_corpus", lambda repo_root: deepcopy(corpus)
    )
    plan_path = tmp_path / "artifacts" / "batch-plan.json"
    state_root, output_root = tmp_path / "state", tmp_path / "runs"
    first_receipt, second_receipt = tmp_path / "a.json", tmp_path / "b.json"

    assert batch.main(
        [
            "create-plan",
            "--repo-root",
            str(tmp_path),
            "--plan-path",
            str(plan_path),
            "--publication-date",
            "2026-09-04",
        ]
    ) == 0
    frozen_bytes = plan_path.read_bytes()
    frozen_plan = json.loads(frozen_bytes)
    assert frozen_bytes == batch.batch_plan_bytes(frozen_plan)

    assert batch.main(
        [
            "prepare-checkpoint",
            "--plan-path",
            str(plan_path),
            "--plan-sha256",
            hashlib.sha256(frozen_bytes).hexdigest(),
            "--state-root",
            str(state_root),
            "--output-root",
            str(output_root),
            "--count",
            "4",
            "--receipt-path",
            str(first_receipt),
        ]
    ) == 0
    first = json.loads(first_receipt.read_bytes())
    first_bytes = {
        slot["run_id"]: _run_bytes(output_root, slot["run_id"])
        for slot in first["slots"]
    }
    for slot in first["slots"]:
        owner = {
            key: slot[key]
            for key in (
                "topic_id",
                "reservation_token",
                "lane_id",
                "run_id",
                "owner_generation",
            )
        }
        assert reservation.activate_topic_reservation(state_root, **owner)["ok"] is True
        assert reservation.schedule_topic_reservation(state_root, **owner)["ok"] is True
        assert reservation.publish_topic_reservation(state_root, **owner)["ok"] is True
    corpus.append(
        {
            "id": "OLD",
            "path": "/articles/tarot/tarot-0099",
            "title": "其他",
            "primaryKeyword": "其他",
        }
    )

    def unexpected_rebuild(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("prepare mode must not rebuild the plan")

    monkeypatch.setattr(batch, "build_checkpoint_plan", unexpected_rebuild)

    assert batch.main(
        [
            "prepare-checkpoint",
            "--plan-path",
            str(plan_path),
            "--plan-sha256",
            hashlib.sha256(frozen_bytes).hexdigest(),
            "--state-root",
            str(state_root),
            "--output-root",
            str(output_root),
            "--count",
            "10",
            "--completed-count",
            "4",
            "--receipt-path",
            str(second_receipt),
        ]
    ) == 0
    second = json.loads(second_receipt.read_bytes())

    assert plan_path.read_bytes() == frozen_bytes
    assert first["status"] == second["status"] == "READY"
    assert first["batch_digest"] == second["batch_digest"] == frozen_plan["batch_digest"]
    assert second["metrics"]["attempted"] == 6
    assert [slot["run_id"] for slot in second["slots"]] == [
        slot["run_id"] for slot in frozen_plan["slots"][4:]
    ]
    assert len(_records(state_root)) == 10
    assert {
        record["status"] for record in _records(state_root).values()
    } == {"PUBLISHED", "RESERVED"}
    assert all(
        _run_bytes(output_root, run_id) == content
        for run_id, content in first_bytes.items()
    )


def test_cli_create_plan_is_exactly_idempotent_and_refuses_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        batch, "load_canonical_topics", lambda repo_root: [_topic(index) for index in range(1, 11)]
    )
    monkeypatch.setattr(identity, "load_existing_corpus", lambda repo_root: [])
    plan_path = tmp_path / "batch-plan.json"

    common = ["create-plan", "--repo-root", str(tmp_path), "--plan-path", str(plan_path)]
    assert batch.main([*common, "--publication-date", "2026-09-04"]) == 0
    original = plan_path.read_bytes()
    assert batch.main([*common, "--publication-date", "2026-09-04"]) == 0
    assert plan_path.read_bytes() == original

    assert batch.main([*common, "--publication-date", "2026-09-05"]) != 0
    assert plan_path.read_bytes() == original


def test_cli_prepare_returns_nonzero_for_partial_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "batch-plan.json"
    plan_path.write_bytes(batch.batch_plan_bytes(_plan(tmp_path)))
    monkeypatch.setattr(
        batch,
        "prepare_checkpoint",
        lambda *args, **kwargs: {"schema_version": 1, "status": "PARTIAL"},
    )

    assert batch.main(
        [
            "prepare-checkpoint",
            "--plan-path",
            str(plan_path),
            "--plan-sha256",
            hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "--state-root",
            str(tmp_path / "state"),
            "--output-root",
            str(tmp_path / "runs"),
            "--count",
            "4",
        ]
    ) != 0


def test_cli_rejects_invalid_plan_artifacts_before_prepare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path)
    invalid_digest = deepcopy(plan)
    invalid_digest["batch_digest"] = "0" * 64
    for slot in invalid_digest["slots"]:
        slot["lineage"]["batch_digest"] = invalid_digest["batch_digest"]
    invalid_lineage = deepcopy(plan)
    invalid_lineage["slots"][-1]["lineage"]["run_id"] = "different-run"
    artifacts = {
        "noncanonical": json.dumps(plan, ensure_ascii=False, indent=2).encode("utf-8"),
        "digest": batch.batch_plan_bytes(invalid_digest),
        "lineage": batch.batch_plan_bytes(invalid_lineage),
    }

    def unexpected_prepare(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("prepare_checkpoint must not run")

    monkeypatch.setattr(batch, "prepare_checkpoint", unexpected_prepare)
    for name, content in artifacts.items():
        plan_path = tmp_path / f"{name}.json"
        plan_path.write_bytes(content)
        state_root, output_root = tmp_path / f"state-{name}", tmp_path / f"runs-{name}"
        assert batch.main(
            [
                "prepare-checkpoint",
                "--plan-path",
                str(plan_path),
                "--plan-sha256",
                hashlib.sha256(content).hexdigest(),
                "--state-root",
                str(state_root),
                "--output-root",
                str(output_root),
                "--count",
                "4",
            ]
        ) != 0
        assert not state_root.exists()
        assert not output_root.exists()


def test_cli_sha_pin_rejects_self_consistent_plan_replacement_before_b(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        batch, "load_canonical_topics", lambda repo_root: [_topic(index) for index in range(1, 11)]
    )
    monkeypatch.setattr(identity, "load_existing_corpus", lambda repo_root: [])
    plan_path = tmp_path / "batch-plan.json"
    state_root, output_root = tmp_path / "state", tmp_path / "runs"

    assert batch.main(
        [
            "create-plan",
            "--repo-root",
            str(tmp_path),
            "--plan-path",
            str(plan_path),
            "--publication-date",
            "2026-09-04",
        ]
    ) == 0
    original_sha = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert capsys.readouterr().out.strip() == original_sha
    common = [
        "prepare-checkpoint",
        "--plan-path",
        str(plan_path),
        "--plan-sha256",
        original_sha,
        "--state-root",
        str(state_root),
        "--output-root",
        str(output_root),
    ]
    assert batch.main([*common, "--count", "4"]) == 0
    records_before = _records(state_root)
    outputs_before = {
        slot["run_id"]: _run_bytes(output_root, slot["run_id"])
        for slot in json.loads(plan_path.read_bytes())["slots"][:4]
    }

    replacement = batch.build_checkpoint_plan(
        tmp_path,
        publication_date="2026-09-05",
    )
    replacement_bytes = batch.batch_plan_bytes(replacement)
    assert hashlib.sha256(replacement_bytes).hexdigest() != original_sha
    plan_path.write_bytes(replacement_bytes)

    assert batch.main([*common, "--count", "10"]) != 0
    assert _records(state_root) == records_before
    assert {path.name for path in output_root.iterdir()} == set(outputs_before)
    assert all(
        _run_bytes(output_root, run_id) == content
        for run_id, content in outputs_before.items()
    )


@pytest.mark.parametrize(
    "duplicate_identity",
    [
        "schema_version",
        "slot_id",
        "topic_id",
        "run_id",
        "lane_id",
        "semantic_exclusion_key",
        "target_article_id",
        "target_route",
    ],
)
def test_cli_rejects_self_consistent_invalid_or_duplicate_identity_before_mutation(
    tmp_path: Path,
    duplicate_identity: str,
) -> None:
    plan = _plan(tmp_path)
    first, second = plan["slots"][:2]
    if duplicate_identity == "schema_version":
        plan["schema_version"] = 2
    elif duplicate_identity.startswith("target_"):
        field = duplicate_identity.removeprefix("target_")
        second["target"][field] = first["target"][field]
    else:
        second[duplicate_identity] = first[duplicate_identity]
    _recompute_plan_integrity(plan)
    plan_path = tmp_path / f"{duplicate_identity}.json"
    plan_path.write_bytes(batch.batch_plan_bytes(plan))

    assert batch.main(
        [
            "prepare-checkpoint",
            "--plan-path",
            str(plan_path),
            "--plan-sha256",
            hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "--state-root",
            str(tmp_path / "state"),
            "--output-root",
            str(tmp_path / "runs"),
            "--count",
            "4",
        ]
    ) != 0
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("slot_index", range(4, 10))
def test_cli_checkpoint_four_rejects_malformed_tail_before_mutation(
    tmp_path: Path,
    slot_index: int,
) -> None:
    plan = _plan(tmp_path)
    plan["slots"][slot_index]["topic"]["title"] = "過長" * 5000
    _recompute_plan_integrity(plan)
    plan_path = tmp_path / f"malformed-slot-{slot_index + 1:02d}.json"
    plan_path.write_bytes(batch.batch_plan_bytes(plan))

    assert batch.main(
        [
            "prepare-checkpoint",
            "--plan-path",
            str(plan_path),
            "--plan-sha256",
            hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "--state-root",
            str(tmp_path / "state"),
            "--output-root",
            str(tmp_path / "runs"),
            "--count",
            "4",
        ]
    ) != 0
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / "runs").exists()

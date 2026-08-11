from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import agy_gemini_coordinator as coordinator
from scripts.agy_gemini_outbox import ExternalJobPending
from scripts.pantheon_content_capability_receipt import (
    CAPABILITIES,
    SCHEMA_VERSION,
    validate_capability_receipt,
)


EVIDENCE_PREFIX = (
    "artifacts/fortune_council/content_writer_vnext_execution/"
    "runtime_activation/ra_slice_002/sandbox/evidence"
)
RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": "c" * 64,
}


def _digest(index: int) -> str:
    return f"{index:064x}"


def _brief() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "ra-slice-002-synthetic-create-run",
        "mode": "create",
        "articles": [
            {
                "id": "RA-SLICE-002-SYNTHETIC",
                "title": "Synthetic local create run receipt",
            }
        ],
    }


def _paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    return (
        sandbox_root,
        sandbox_root / "runs",
        sandbox_root / "queue",
        sandbox_root / "evidence",
    )


def _full_receipt(envelope: dict[str, Any]) -> dict[str, Any]:
    steps = list(envelope["receipt_steps"])
    previous = steps[-1]["output_digest"]
    for ordinal, capability in enumerate(CAPABILITIES[2:], 3):
        output = _digest(ordinal)
        steps.append(
            {
                "capability": capability,
                "ordinal": ordinal,
                "entrypoint": f"tests.fixture:{capability}",
                "input_digest": previous,
                "output_digest": output,
                "execution_line_id": envelope["execution_line_id"],
                "correlation_id": envelope["correlation_id"],
                "actor_identity": envelope["actor_identity"],
                "runtime_identity_digest": envelope["runtime_identity_digest"],
                "positive_evidence": f"{EVIDENCE_PREFIX}/{ordinal:02d}-{capability}-pass.json",
                "negative_evidence": f"{EVIDENCE_PREFIX}/{ordinal:02d}-{capability}-blocked.json",
                "positive_outcome": "PASS",
                "negative_outcome": "BLOCKED",
            }
        )
        previous = output
    return {
        "schema_version": SCHEMA_VERSION,
        "execution_line_id": envelope["execution_line_id"],
        "correlation_id": envelope["correlation_id"],
        "actor_identity": envelope["actor_identity"],
        "runtime_identity_digest": envelope["runtime_identity_digest"],
        "mode": envelope["mode"],
        "canary_created": envelope["canary_created"],
        "production_mutation": envelope["production_mutation"],
        "steps": steps,
    }


def _assert_no_absolute_strings(value: object) -> None:
    if isinstance(value, dict):
        for nested in value.values():
            _assert_no_absolute_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_absolute_strings(nested)
    elif isinstance(value, str):
        assert not value.startswith("/")


def test_coordinator_preflight_emits_create_run_steps_from_official_boundaries(
    tmp_path: Path,
) -> None:
    sandbox_root, run_root, queue_root, evidence_root = _paths(tmp_path)
    events: list[tuple[str, object]] = []
    tick_calls = 0

    def local_tick(run_dir: Path, job_queue_root: Path) -> dict[str, object]:
        nonlocal tick_calls
        tick_calls += 1
        events.append(("tick", run_dir.name, job_queue_root == queue_root))
        if tick_calls == 1:
            raise ExternalJobPending("ra-slice-002-local-job")
        return {"status": "complete", "bounded": True}

    def local_process(queue: Path, **kwargs: object) -> dict[str, str]:
        events.append(("process", queue == queue_root, kwargs.get("exact_run_ids")))
        return {"status": "processed", "job_id": "ra-slice-002-local-job"}

    envelope = coordinator.coordinator_create_run_receipt_preflight(
        trusted_sandbox_root=sandbox_root,
        run_root=run_root,
        queue_root=queue_root,
        evidence_root=evidence_root,
        execution_line_id="exec-ra-slice-002",
        correlation_id="corr-ra-slice-002",
        actor_identity="actor-ra-slice-002",
        runtime_identity_digest=RUNTIME_RECEIPT["runtime_identity_digest"],
        runtime_receipt=RUNTIME_RECEIPT,
        brief=_brief(),
        lane="new",
        tick=local_tick,
        process=local_process,
    )

    assert envelope["mode"] == "synthetic-non-production"
    assert envelope["canary_created"] is False
    assert envelope["production_mutation"] is False
    assert envelope["created_run_id"] == "ra-slice-002-synthetic-create-run"
    assert [step["capability"] for step in envelope["receipt_steps"]] == ["create", "run"]
    assert [step["ordinal"] for step in envelope["receipt_steps"]] == [1, 2]
    assert envelope["receipt_steps"][1]["input_digest"] == envelope["receipt_steps"][0]["output_digest"]
    assert events == [
        ("tick", "ra-slice-002-synthetic-create-run", True),
        ("process", True, frozenset({"ra-slice-002-synthetic-create-run"})),
        ("tick", "ra-slice-002-synthetic-create-run", True),
    ]

    state = coordinator.read_run_state(run_root / _brief()["run_id"], queue_root)
    assert state["status"] == "complete"
    assert state["correlation_id"] == "corr-ra-slice-002"
    assert state["run_dir"] == str((run_root / _brief()["run_id"]).resolve())

    validated = validate_capability_receipt(_full_receipt(envelope))
    assert validated["status"] == "PASS"

    for artifact_name in ("positive-create.json", "positive-run.json"):
        artifact = json.loads((evidence_root / artifact_name).read_text(encoding="utf-8"))
        assert artifact["production_mutation"] is False
        assert artifact["correlation_id"] == "corr-ra-slice-002"
        assert artifact["runtime_identity_digest"] == RUNTIME_RECEIPT["runtime_identity_digest"]
        _assert_no_absolute_strings(artifact)


def test_coordinator_preflight_blocked_evidence_comes_from_rejected_calls(
    tmp_path: Path,
) -> None:
    sandbox_root, run_root, queue_root, evidence_root = _paths(tmp_path)

    coordinator.coordinator_create_run_receipt_preflight(
        trusted_sandbox_root=sandbox_root,
        run_root=run_root,
        queue_root=queue_root,
        evidence_root=evidence_root,
        execution_line_id="exec-ra-slice-002",
        correlation_id="corr-ra-slice-002",
        actor_identity="actor-ra-slice-002",
        runtime_identity_digest=RUNTIME_RECEIPT["runtime_identity_digest"],
        runtime_receipt=RUNTIME_RECEIPT,
        brief=_brief(),
        lane="new",
    )

    blocked_create = json.loads(
        (evidence_root / "blocked-create.json").read_text(encoding="utf-8")
    )
    blocked_run = json.loads(
        (evidence_root / "blocked-run.json").read_text(encoding="utf-8")
    )
    assert blocked_create["case"] == "missing-brief"
    assert blocked_create["reason"] == "brief is required"
    assert blocked_run["case"] == "run-boundary"
    assert "exact run ids not found" in blocked_run["reason"]


def test_coordinator_preflight_digest_is_stable_across_canonical_roots(
    tmp_path: Path,
) -> None:
    def run_preflight(root: Path) -> dict[str, Any]:
        sandbox_root = root / "sandbox"
        sandbox_root.mkdir(parents=True)
        return coordinator.coordinator_create_run_receipt_preflight(
            trusted_sandbox_root=sandbox_root,
            run_root=sandbox_root / "runs",
            queue_root=sandbox_root / "queue",
            evidence_root=sandbox_root / "evidence",
            execution_line_id="exec-ra-slice-002",
            correlation_id="corr-ra-slice-002",
            actor_identity="actor-ra-slice-002",
            runtime_identity_digest=RUNTIME_RECEIPT["runtime_identity_digest"],
            runtime_receipt=RUNTIME_RECEIPT,
            brief=_brief(),
            lane="new",
        )

    first = run_preflight(tmp_path / "first-root")
    second = run_preflight(tmp_path / "second-root")

    assert [step["output_digest"] for step in first["receipt_steps"]] == [
        step["output_digest"] for step in second["receipt_steps"]
    ]


def test_coordinator_preflight_propagates_unexpected_runtime_error(
    tmp_path: Path,
) -> None:
    sandbox_root, run_root, queue_root, evidence_root = _paths(tmp_path)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("ra-slice-002-local-job")

    def broken_process(*_args: object, **_kwargs: object) -> dict[str, str]:
        raise RuntimeError("injected unexpected runtime failure")

    with pytest.raises(RuntimeError, match="injected unexpected runtime failure"):
        coordinator.coordinator_create_run_receipt_preflight(
            trusted_sandbox_root=sandbox_root,
            run_root=run_root,
            queue_root=queue_root,
            evidence_root=evidence_root,
            execution_line_id="exec-ra-slice-002",
            correlation_id="corr-ra-slice-002",
            actor_identity="actor-ra-slice-002",
            runtime_identity_digest=RUNTIME_RECEIPT["runtime_identity_digest"],
            runtime_receipt=RUNTIME_RECEIPT,
            brief=_brief(),
            lane="new",
            tick=pending_tick,
            process=broken_process,
        )

    assert not (evidence_root / "blocked-run.json").exists()


def test_coordinator_preflight_evidence_ids_follow_caller_evidence_root(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    evidence_root = sandbox_root / "caller-approved" / "proofs"

    envelope = coordinator.coordinator_create_run_receipt_preflight(
        trusted_sandbox_root=sandbox_root,
        run_root=sandbox_root / "runs",
        queue_root=sandbox_root / "queue",
        evidence_root=evidence_root,
        execution_line_id="exec-ra-slice-002",
        correlation_id="corr-ra-slice-002",
        actor_identity="actor-ra-slice-002",
        runtime_identity_digest=RUNTIME_RECEIPT["runtime_identity_digest"],
        runtime_receipt=RUNTIME_RECEIPT,
        brief=_brief(),
        lane="new",
    )

    evidence_ids = {
        step[key]
        for step in envelope["receipt_steps"]
        for key in ("positive_evidence", "negative_evidence")
    }
    assert evidence_ids == {
        "caller-approved/proofs/positive-create.json",
        "caller-approved/proofs/blocked-create.json",
        "caller-approved/proofs/positive-run.json",
        "caller-approved/proofs/blocked-run.json",
    }
    for evidence_id in evidence_ids:
        assert not evidence_id.startswith(EVIDENCE_PREFIX)


@pytest.mark.parametrize(
    ("case", "overrides", "match"),
    [
        ("missing-brief", {"brief": None}, "brief"),
        ("too-many-articles", {"brief": {**_brief(), "articles": [{}, {}]}}, "brief"),
        ("blank-correlation", {"correlation_id": " "}, "correlation"),
        ("wrong-lane", {"lane": "rewrite"}, "lane"),
        ("runtime-missing-digest", {"runtime_receipt": {"status": "PASS"}}, "runtime identity"),
        (
            "runtime-digest-mismatch",
            {"runtime_identity_digest": "d" * 64},
            "runtime identity",
        ),
        (
            "caller-verdict",
            {"runtime_receipt": {**RUNTIME_RECEIPT, "valid": True}},
            "caller",
        ),
        (
            "extra-runtime-key",
            {"runtime_receipt": {**RUNTIME_RECEIPT, "extra": "nope"}},
            "runtime identity",
        ),
    ],
)
def test_coordinator_preflight_blocks_invalid_identity_before_queue_io(
    case: str,
    overrides: dict[str, object],
    match: str,
    tmp_path: Path,
) -> None:
    sandbox_root, run_root, queue_root, evidence_root = _paths(tmp_path)
    process_called = False

    def process_must_not_run(*_args: object, **_kwargs: object) -> dict[str, str]:
        nonlocal process_called
        process_called = True
        raise AssertionError(f"{case} must block before process")

    kwargs: dict[str, object] = {
        "trusted_sandbox_root": sandbox_root,
        "run_root": run_root,
        "queue_root": queue_root,
        "evidence_root": evidence_root,
        "execution_line_id": "exec-ra-slice-002",
        "correlation_id": "corr-ra-slice-002",
        "actor_identity": "actor-ra-slice-002",
        "runtime_identity_digest": RUNTIME_RECEIPT["runtime_identity_digest"],
        "runtime_receipt": RUNTIME_RECEIPT,
        "brief": _brief(),
        "lane": "new",
        "tick": lambda *_args: pytest.fail(f"{case} must block before tick"),
        "process": process_must_not_run,
    }
    kwargs.update(overrides)

    with pytest.raises(coordinator.CoordinatorReceiptBlocked, match=match):
        coordinator.coordinator_create_run_receipt_preflight(**kwargs)

    assert process_called is False
    assert not (queue_root / "runs").exists()
    artifact = json.loads((evidence_root / "blocked-create.json").read_text(encoding="utf-8"))
    assert artifact["outcome"] == "BLOCKED"
    assert artifact["reason"]
    assert artifact["case"] == case
    assert artifact["production_mutation"] is False
    _assert_no_absolute_strings(artifact)


@pytest.mark.parametrize("case", ["external-queue", "symlink-escape", "overlap"])
def test_coordinator_preflight_rejects_untrusted_roots_before_run_io(
    case: str,
    tmp_path: Path,
) -> None:
    sandbox_root, run_root, queue_root, evidence_root = _paths(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    if case == "external-queue":
        queue_root = external / "queue"
    elif case == "symlink-escape":
        queue_root.parent.mkdir(parents=True, exist_ok=True)
        queue_root.symlink_to(external, target_is_directory=True)
    elif case == "overlap":
        evidence_root = queue_root / "evidence"

    with pytest.raises(coordinator.CoordinatorReceiptBlocked, match="root|overlap"):
        coordinator.coordinator_create_run_receipt_preflight(
            trusted_sandbox_root=sandbox_root,
            run_root=run_root,
            queue_root=queue_root,
            evidence_root=evidence_root,
            execution_line_id="exec-ra-slice-002",
            correlation_id="corr-ra-slice-002",
            actor_identity="actor-ra-slice-002",
            runtime_identity_digest=RUNTIME_RECEIPT["runtime_identity_digest"],
            runtime_receipt=RUNTIME_RECEIPT,
            brief=_brief(),
            lane="new",
            tick=lambda *_args: pytest.fail(f"{case} must block before tick"),
            process=lambda *_args, **_kwargs: pytest.fail(
                f"{case} must block before process"
            ),
        )

    assert not (sandbox_root / "runs" / "ra-slice-002-synthetic-create-run").exists()
    assert not (queue_root / "runs").exists()

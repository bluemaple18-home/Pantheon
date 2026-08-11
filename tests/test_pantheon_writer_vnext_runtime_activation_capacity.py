from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.pantheon_writer_vnext_runtime_activation_capacity import (
    CapacityProofBlocked,
    DEFAULT_POLICY,
    GIB,
    MIB,
    run_capacity_negative_matrix,
    run_capacity_proof,
)


RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": "d" * 64,
}


def _brief() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "ra-slice-005-synthetic-create-run",
        "mode": "create",
        "articles": [{"id": "RA-SLICE-005-SYNTHETIC", "title": "Synthetic"}],
    }


def _fake_e2e_receipt(cycle: int) -> dict[str, object]:
    return {
        "status": "PASS",
        "mode": "synthetic-non-production",
        "canary_created": False,
        "production_mutation": False,
        "receipt": {
            "steps": [
                {
                    "ordinal": ordinal,
                    "capability": capability,
                    "execution_line_id": f"exec-ra-slice-005-cycle-{cycle}",
                    "correlation_id": f"corr-ra-slice-005-cycle-{cycle}",
                }
                for ordinal, capability in enumerate(
                    (
                        "create",
                        "run",
                        "select",
                        "publish",
                        "transaction",
                        "tag",
                        "push",
                    ),
                    1,
                )
            ],
        },
    }


def _tree_size(root: Path) -> tuple[int, int]:
    total_bytes = 0
    file_count = 0
    for directory, _directories, filenames in os.walk(root):
        for filename in filenames:
            path = Path(directory) / filename
            total_bytes += path.stat().st_size
            file_count += 1
    return total_bytes, file_count


def test_capacity_proof_runs_two_e2e_cycles_and_reclaims_only_cycle_roots(
    tmp_path: Path,
) -> None:
    calls: list[Path] = []
    sample_labels: list[str] = []

    def workload(**kwargs: object) -> dict[str, object]:
        cycle_root = Path(kwargs["trusted_sandbox_root"])
        calls.append(cycle_root)
        cycle_number = len(calls)
        (cycle_root / f"payload-{cycle_number}.txt").write_text(
            f"cycle:{cycle_number}\n",
            encoding="utf-8",
        )
        return _fake_e2e_receipt(cycle_number)

    def sampler(project_root: Path, label: str, _started: float) -> dict[str, object]:
        sample_labels.append(label)
        project_bytes, file_count = _tree_size(project_root)
        return {
            "label": label,
            "sampled_epoch": float(len(sample_labels)),
            "elapsed_seconds": float(len(sample_labels)),
            "host_total_bytes": 500 * GIB,
            "host_free_bytes": 250 * GIB,
            "project_bytes": project_bytes,
            "file_count": file_count,
            "process_rss_bytes": 64 * MIB,
            "swap_used_bytes": 0,
        }

    result = run_capacity_proof(
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=(tmp_path / "evidence").resolve(),
        runtime_receipt=RUNTIME_RECEIPT,
        actor_identity="actor-ra-slice-005",
        brief=_brief(),
        policy=DEFAULT_POLICY,
        sampler=sampler,
        workload=workload,
    )

    assert result["status"] == "PASS"
    assert result["canary_created"] is False
    assert result["production_mutation"] is False
    assert [cycle["cycle"] for cycle in result["cycles"]] == [1, 2]
    assert [cycle["capability_receipt_status"] for cycle in result["cycles"]] == [
        "PASS",
        "PASS",
    ]
    assert len(calls) == 2
    assert calls[0] != calls[1]
    assert all(not root.exists() for root in calls)
    assert all(cycle["cleanup"]["root_exists_after_cleanup"] is False for cycle in result["cycles"])
    assert all(cycle["cleanup"]["reclaimed_bytes"] > 0 for cycle in result["cycles"])
    assert sample_labels == [
        "cycle-1-before",
        "cycle-1-peak",
        "cycle-1-after-cleanup",
        "cycle-2-before",
        "cycle-2-peak",
        "cycle-2-after-cleanup",
    ]
    assert result["projections"]["host_free_after_projection_bytes"] > result[
        "projections"
    ]["host_reserve_bytes"]
    assert (tmp_path / "evidence" / "capacity-receipt.json").is_file()
    assert json.loads((tmp_path / "evidence" / "capacity-receipt.json").read_text())[
        "status"
    ] == "PASS"


def test_capacity_proof_blocks_over_budget_before_second_cycle(tmp_path: Path) -> None:
    calls: list[Path] = []
    policy = {**DEFAULT_POLICY, "max_bytes": 1}

    def workload(**kwargs: object) -> dict[str, object]:
        cycle_root = Path(kwargs["trusted_sandbox_root"])
        calls.append(cycle_root)
        (cycle_root / "too-large.txt").write_text("over-budget\n", encoding="utf-8")
        return _fake_e2e_receipt(len(calls))

    with pytest.raises(CapacityProofBlocked) as blocked:
        run_capacity_proof(
            capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
            evidence_root=(tmp_path / "evidence").resolve(),
            runtime_receipt=RUNTIME_RECEIPT,
            actor_identity="actor-ra-slice-005",
            brief=_brief(),
            policy=policy,
            workload=workload,
        )

    assert len(calls) == 1
    assert blocked.value.payload["status"] == "BLOCKED"
    assert blocked.value.payload["case"] == "project-bytes-over-budget"
    assert blocked.value.payload["next_cycle_started"] is False
    assert blocked.value.payload["external_cleanup_performed"] is False
    assert not (tmp_path / "evidence" / "capacity-receipt.json").exists()
    assert (tmp_path / "evidence" / "blocked-capacity.json").is_file()


def test_capacity_negative_matrix_covers_required_fail_closed_cases(
    tmp_path: Path,
) -> None:
    matrix = run_capacity_negative_matrix(evidence_root=(tmp_path / "evidence").resolve())
    cases = {case["case"]: case for case in matrix["cases"]}

    for case in [
        "max-bytes-too-low",
        "max-file-count-too-low",
        "host-free-below-reserve",
        "rss-growth-over-budget",
        "swap-growth-over-budget",
        "cleanup-root-still-exists",
        "unknown-write-path",
        "missing-required-measurement",
        "invalid-policy",
        "caller-supplied-verdict",
    ]:
        assert cases[case]["outcome"] == "BLOCKED"
        assert cases[case]["next_cycle_started"] is False
        assert cases[case]["external_cleanup_performed"] is False

    assert json.loads((tmp_path / "evidence" / "negative-matrix.json").read_text())[
        "cases"
    ] == matrix["cases"]


def test_capacity_policy_rejects_unbounded_values_and_caller_verdict(
    tmp_path: Path,
) -> None:
    for policy in (
        {**DEFAULT_POLICY, "max_bytes": -1},
        {**DEFAULT_POLICY, "sampling_interval_seconds": 301},
        {**DEFAULT_POLICY, "status": "PASS"},
        {**DEFAULT_POLICY, "ready": True},
    ):
        with pytest.raises(CapacityProofBlocked):
            run_capacity_proof(
                capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
                evidence_root=(tmp_path / "evidence").resolve(),
                runtime_receipt=RUNTIME_RECEIPT,
                actor_identity="actor-ra-slice-005",
                brief=_brief(),
                policy=policy,
                workload=lambda **_kwargs: _fake_e2e_receipt(1),
            )

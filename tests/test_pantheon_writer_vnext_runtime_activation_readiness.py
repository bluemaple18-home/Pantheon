from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.pantheon_writer_vnext_runtime_activation_readiness import (
    ReadinessPackagingBlocked,
    build_readiness_package,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RA_ROOT = (
    REPO_ROOT
    / "artifacts/fortune_council/content_writer_vnext_execution/runtime_activation"
)
RA004_ROOT = RA_ROOT / "ra_slice_004"
RA005_ROOT = RA_ROOT / "ra_slice_005"
AI_CORE_GATE = Path("/Users/mattkuo/ai-core/scripts/production_canary_readiness_gate.py")


def _source_args(tmp_path: Path) -> dict[str, object]:
    return {
        "capability_receipt_path": RA004_ROOT / "positive-receipt.json",
        "capability_evidence_root": RA004_ROOT / "sandbox/evidence",
        "capacity_receipt_path": RA005_ROOT / "capacity-receipt.json",
        "cycle_measurement_paths": [
            RA005_ROOT / "cycle-1-measurements.json",
            RA005_ROOT / "cycle-2-measurements.json",
        ],
        "capacity_negative_matrix_path": RA005_ROOT / "negative-matrix.json",
        "capacity_blocked_path": RA005_ROOT / "blocked-capacity.json",
        "output_package_root": tmp_path / "package",
    }


def _gate(receipt: Path) -> dict[str, object]:
    if not AI_CORE_GATE.is_file():
        pytest.skip("official ai-core readiness gate is unavailable")
    completed = subprocess.run(
        [sys.executable, str(AI_CORE_GATE), "--receipt", str(receipt)],
        check=False,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_builds_portable_package_that_official_gate_marks_ready(tmp_path: Path) -> None:
    result = build_readiness_package(**_source_args(tmp_path))
    package_root = Path(result["package_root"])
    receipt_path = package_root / "production-canary-capability-receipt.json"

    assert result["status"] == "PACKAGED"
    assert result["canary_created"] is False
    assert result["production_authorized"] is False
    assert receipt_path.is_file()
    assert _gate(receipt_path)["status"] == "READY"

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["canary_created"] is False
    assert receipt["production_authorized"] is False
    assert set(receipt["steps"]) == {
        "create",
        "run",
        "select",
        "publish",
        "transaction",
        "tag",
        "push",
    }

    evidence_artifacts: list[str] = []
    for step in receipt["steps"].values():
        evidence_artifacts.extend(
            [
                step["positive_evidence"]["artifact"],
                step["negative_evidence"]["artifact"],
            ]
        )
    assert len(evidence_artifacts) == 14
    assert len(set(evidence_artifacts)) == 14
    assert all(not Path(artifact).is_absolute() for artifact in evidence_artifacts)
    assert all((package_root / artifact).is_file() for artifact in evidence_artifacts)

    capacity = json.loads(
        (package_root / "capacity-proof-normalized.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(capacity, ensure_ascii=False)
    assert "/Users/" not in serialized
    assert capacity["status"] == "PASS"
    assert [cycle["cycle"] for cycle in capacity["cycles"]] == [1, 2]
    assert all(cycle["cleanup"]["reclaimed_bytes"] > 0 for cycle in capacity["cycles"])
    assert (
        capacity["projections"]["host_free_after_projection_bytes"]
        >= capacity["projections"]["host_reserve_bytes"]
    )


def test_blocks_identity_drift_before_thin_gate_can_authorize(tmp_path: Path) -> None:
    source = json.loads((RA004_ROOT / "positive-receipt.json").read_text(encoding="utf-8"))
    source["steps"][3]["actor_identity"] = "actor-ra-slice-004-drift"
    drifted = tmp_path / "drifted-capability-receipt.json"
    _write_json(drifted, source)

    args = _source_args(tmp_path)
    args["capability_receipt_path"] = drifted

    with pytest.raises(ReadinessPackagingBlocked) as blocked:
        build_readiness_package(**args)
    assert blocked.value.payload["case"] == "capability-receipt-invalid"
    assert blocked.value.payload["outcome"] == "BLOCKED"


def test_thin_gate_adversarial_red_is_saved_and_demonstrates_gap(
    tmp_path: Path,
) -> None:
    build_readiness_package(**_source_args(tmp_path))
    package_root = tmp_path / "package"
    adversarial_receipt = package_root / "adversarial-thin-gate-receipt.json"
    red = json.loads(
        (package_root / "thin-gate-adversarial-red.json").read_text(encoding="utf-8")
    )

    assert red["case"] == "thin-gate-identity-digest-provenance-gap"
    assert red["repo_packager_required_outcome"] == "BLOCKED"
    assert red["official_gate_observed_outcome"] == "READY"
    assert _gate(adversarial_receipt)["status"] == "READY"


def test_official_gate_blocked_fixture_and_packager_negative_matrix(
    tmp_path: Path,
) -> None:
    build_readiness_package(**_source_args(tmp_path))
    package_root = tmp_path / "package"

    blocked = _gate(package_root / "missing-step-receipt.json")
    assert blocked["status"] == "BLOCKED"

    matrix = json.loads((package_root / "negative-matrix.json").read_text(encoding="utf-8"))
    cases = {item["case"]: item for item in matrix["cases"]}
    for case in [
        "missing-capability-step",
        "identity-drift",
        "digest-discontinuity",
        "positive-evidence-missing",
        "positive-evidence-empty",
        "positive-evidence-outcome",
        "evidence-reuse",
        "capacity-not-pass",
        "capacity-missing-cycle",
        "capacity-missing-measurement",
        "capacity-cleanup-reclaim-missing",
        "capacity-stop-loss-not-blocked",
        "capacity-projection-below-reserve",
        "absolute-artifact-path",
        "symlink-escape",
    ]:
        assert cases[case]["outcome"] == "BLOCKED"


def test_blocks_capacity_projection_without_trusting_pass_status(tmp_path: Path) -> None:
    source = json.loads((RA005_ROOT / "capacity-receipt.json").read_text(encoding="utf-8"))
    source["status"] = "PASS"
    source["projections"]["host_free_after_projection_bytes"] = (
        source["projections"]["host_reserve_bytes"] - 1
    )
    invalid = tmp_path / "capacity-receipt.json"
    _write_json(invalid, source)

    args = _source_args(tmp_path)
    args["capacity_receipt_path"] = invalid

    with pytest.raises(ReadinessPackagingBlocked) as blocked:
        build_readiness_package(**args)
    assert blocked.value.payload["case"] == "capacity-projection-below-reserve"

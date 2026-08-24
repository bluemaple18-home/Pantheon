from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterator

import pytest

from scripts.pantheon_writer_vnext_runtime_activation_capacity import (
    CAPACITY_RECEIPT_MEDIA_TYPE,
    CYCLE_MEASUREMENT_MEDIA_TYPE,
    CapacityEvidenceArtifact,
    CapacityEvidenceBundle,
    CapacityProofBlocked,
    DEFAULT_POLICY,
    GIB,
    MIB,
    run_capacity_proof_evidence_bundle,
    run_capacity_negative_matrix,
    run_capacity_proof,
)
from scripts import pantheon_writer_vnext_runtime_activation_capacity as capacity_module


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


def _write_fixture_capacity_artifacts(evidence_root: Path) -> dict[str, object]:
    cycles = [
        {"cycle": 1, "execution_line_id": "exec-1"},
        {"cycle": 2, "execution_line_id": "exec-2"},
    ]
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "mode": "synthetic-non-production-capacity-proof",
        "cycles": cycles,
        "canary_created": False,
        "production_mutation": False,
    }
    evidence_root.mkdir(parents=True, exist_ok=True)
    for cycle in cycles:
        (evidence_root / f"cycle-{cycle['cycle']}-measurements.json").write_text(
            json.dumps(cycle, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (evidence_root / "capacity-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


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


def test_capacity_proof_evidence_bundle_exposes_exact_byte_artifacts(
    tmp_path: Path,
) -> None:
    calls: list[Path] = []

    def capacity_evaluator(**kwargs: object) -> dict[str, object]:
        evidence_root = Path(kwargs["evidence_root"])
        calls.append(evidence_root)
        return _write_fixture_capacity_artifacts(evidence_root)

    evidence_root = (tmp_path / "evidence").resolve()
    bundle = run_capacity_proof_evidence_bundle(
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=evidence_root,
        runtime_receipt=RUNTIME_RECEIPT,
        actor_identity="actor-ra-slice-005",
        brief=_brief(),
        policy=DEFAULT_POLICY,
        capacity_evaluator=capacity_evaluator,
    )

    assert calls == [evidence_root]
    assert bundle.evidence_root == evidence_root
    assert bundle.receipt == json.loads(
        (evidence_root / "capacity-receipt.json").read_text(encoding="utf-8")
    )
    assert bundle.capacity_receipt.logical_name == "capacity-receipt.json"
    assert bundle.capacity_receipt.media_type == CAPACITY_RECEIPT_MEDIA_TYPE
    assert bundle.capacity_receipt.path == evidence_root / "capacity-receipt.json"
    assert bundle.capacity_receipt.sha256 == hashlib.sha256(
        (evidence_root / "capacity-receipt.json").read_bytes()
    ).hexdigest()
    assert [artifact.logical_name for artifact in bundle.cycle_measurements] == [
        "cycle-1-measurements.json",
        "cycle-2-measurements.json",
    ]
    assert [artifact.media_type for artifact in bundle.cycle_measurements] == [
        CYCLE_MEASUREMENT_MEDIA_TYPE,
        CYCLE_MEASUREMENT_MEDIA_TYPE,
    ]
    assert [artifact.path for artifact in bundle.cycle_measurements] == [
        evidence_root / "cycle-1-measurements.json",
        evidence_root / "cycle-2-measurements.json",
    ]
    assert [artifact.sha256 for artifact in bundle.cycle_measurements] == [
        hashlib.sha256((evidence_root / "cycle-1-measurements.json").read_bytes()).hexdigest(),
        hashlib.sha256((evidence_root / "cycle-2-measurements.json").read_bytes()).hexdigest(),
    ]

    with pytest.raises(AttributeError):
        bundle.cycle_measurements.append(bundle.capacity_receipt)  # type: ignore[attr-defined]


def test_capacity_proof_evidence_bundle_receipt_is_deeply_immutable(
    tmp_path: Path,
) -> None:
    def capacity_evaluator(**kwargs: object) -> dict[str, object]:
        return _write_fixture_capacity_artifacts(Path(kwargs["evidence_root"]))

    evidence_root = (tmp_path / "evidence").resolve()
    bundle = run_capacity_proof_evidence_bundle(
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=evidence_root,
        runtime_receipt=RUNTIME_RECEIPT,
        actor_identity="actor-ra-slice-005",
        brief=_brief(),
        policy=DEFAULT_POLICY,
        capacity_evaluator=capacity_evaluator,
    )

    assert bundle.receipt == json.loads(
        (evidence_root / "capacity-receipt.json").read_text(encoding="utf-8")
    )
    with pytest.raises(TypeError):
        bundle.receipt["status"] = "BLOCKED"  # type: ignore[index]
    with pytest.raises(TypeError):
        bundle.receipt["cycles"][0]["execution_line_id"] = "drifted"  # type: ignore[index]
    with pytest.raises(AttributeError):
        bundle.receipt["cycles"].append({"cycle": 3})  # type: ignore[attr-defined]


def test_capacity_proof_evidence_bundle_calls_evaluator_once(tmp_path: Path) -> None:
    calls = 0

    def capacity_evaluator(**kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return _write_fixture_capacity_artifacts(Path(kwargs["evidence_root"]))

    run_capacity_proof_evidence_bundle(
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=(tmp_path / "evidence").resolve(),
        runtime_receipt=RUNTIME_RECEIPT,
        actor_identity="actor-ra-slice-005",
        brief=_brief(),
        policy=DEFAULT_POLICY,
        capacity_evaluator=capacity_evaluator,
    )

    assert calls == 1


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("missing-capacity-receipt", lambda root: (root / "capacity-receipt.json").unlink()),
        (
            "tampered-capacity-receipt",
            lambda root: (root / "capacity-receipt.json").write_text(
                json.dumps({"status": "PASS", "cycles": []}) + "\n",
                encoding="utf-8",
            ),
        ),
        (
            "cycle-mismatch",
            lambda root: (root / "cycle-2-measurements.json").write_text(
                json.dumps({"cycle": 2, "execution_line_id": "drifted"}) + "\n",
                encoding="utf-8",
            ),
        ),
        (
            "path-escape",
            lambda root: (root / "cycle-1-measurements.json").symlink_to(
                root.parent / "outside.json"
            ),
        ),
        ("non-regular-file", lambda root: (root / "cycle-2-measurements.json").unlink()),
    ],
)
def test_capacity_proof_evidence_bundle_fail_closed_on_artifact_drift(
    tmp_path: Path,
    case: str,
    mutate: object,
) -> None:
    def capacity_evaluator(**kwargs: object) -> dict[str, object]:
        evidence_root = Path(kwargs["evidence_root"])
        receipt = _write_fixture_capacity_artifacts(evidence_root)
        if case == "path-escape":
            (evidence_root.parent / "outside.json").write_text("{}", encoding="utf-8")
            (evidence_root / "cycle-1-measurements.json").unlink()
        elif case == "non-regular-file":
            (evidence_root / "cycle-2-measurements.json").unlink()
            (evidence_root / "cycle-2-measurements.json").mkdir()
            return receipt
        mutate(evidence_root)  # type: ignore[operator]
        return receipt

    with pytest.raises(CapacityProofBlocked) as blocked:
        run_capacity_proof_evidence_bundle(
            capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
            evidence_root=(tmp_path / "evidence").resolve(),
            runtime_receipt=RUNTIME_RECEIPT,
            actor_identity="actor-ra-slice-005",
            brief=_brief(),
            policy=DEFAULT_POLICY,
            capacity_evaluator=capacity_evaluator,
        )

    assert blocked.value.payload["status"] == "BLOCKED"


def test_capacity_proof_evidence_bundle_blocks_replacement_symlink_race(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"cycle": 1, "execution_line_id": "evil"}), encoding="utf-8")

    def capacity_evaluator(**kwargs: object) -> dict[str, object]:
        return _write_fixture_capacity_artifacts(Path(kwargs["evidence_root"]))

    replaced = False

    def replace_cycle_with_symlink(path: Path) -> None:
        nonlocal replaced
        if path.name != "cycle-1-measurements.json" or replaced:
            return
        replaced = True
        path.unlink()
        path.symlink_to(outside)

    with pytest.raises(CapacityProofBlocked) as blocked:
        run_capacity_proof_evidence_bundle(
            capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
            evidence_root=(tmp_path / "evidence").resolve(),
            runtime_receipt=RUNTIME_RECEIPT,
            actor_identity="actor-ra-slice-005",
            brief=_brief(),
            policy=DEFAULT_POLICY,
            capacity_evaluator=capacity_evaluator,
            artifact_before_open_hook=replace_cycle_with_symlink,
        )

    assert replaced is True
    assert blocked.value.payload["status"] == "BLOCKED"
    assert blocked.value.payload["case"] in {
        "capacity-artifact-identity-drift",
        "capacity-artifact-read-failed",
    }


def test_capacity_proof_blocks_over_budget_before_second_cycle(tmp_path: Path) -> None:
    calls: list[Path] = []
    samples: list[dict[str, object]] = []
    policy = {**DEFAULT_POLICY, "max_bytes": 1}

    def sampler(project_root: Path, label: str, _started: float) -> dict[str, object]:
        project_bytes, file_count = _tree_size(project_root)
        sample = {
            "label": label,
            "sampled_epoch": float(len(samples) + 1),
            "elapsed_seconds": float(len(samples) + 1),
            "host_total_bytes": 500 * GIB,
            "host_free_bytes": 250 * GIB,
            "project_bytes": project_bytes,
            "file_count": file_count,
            "process_rss_bytes": 64 * MIB,
            "swap_used_bytes": 0,
        }
        samples.append(sample)
        return sample

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
            sampler=sampler,
            workload=workload,
        )

    assert len(calls) == 1
    assert [sample["label"] for sample in samples] == ["cycle-1-before", "cycle-1-peak"]
    assert samples[0]["project_bytes"] == 0
    assert samples[0]["host_free_bytes"] > 50 * GIB
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


def _write_cli_inputs(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    inputs = {
        "runtime_receipt": root / "runtime-receipt.json",
        "brief": root / "brief.json",
        "policy": root / "policy.json",
    }
    inputs["runtime_receipt"].write_text(
        json.dumps(RUNTIME_RECEIPT) + "\n", encoding="utf-8"
    )
    inputs["brief"].write_text(json.dumps(_brief()) + "\n", encoding="utf-8")
    inputs["policy"].write_text(json.dumps(DEFAULT_POLICY) + "\n", encoding="utf-8")
    return inputs


@pytest.fixture
def cli_task_root() -> Iterator[Path]:
    root = Path(
        tempfile.mkdtemp(prefix="pantheon-v0387-", dir="/private/tmp")
    ).resolve()
    try:
        yield root
    finally:
        shutil.rmtree(root)


def test_bundle_cli_help_is_public() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/pantheon_writer_vnext_runtime_activation_capacity.py",
            "bundle",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--task-root" in result.stdout
    assert "--evidence-root" in result.stdout
    assert "--capacity-sandbox-root" in result.stdout


def test_bundle_cli_requires_explicit_task_root_before_bundle_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _write_cli_inputs(tmp_path / "inputs")
    called = False

    def unexpected_bundle(**_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("missing task root must be rejected before API call")

    monkeypatch.setattr(
        capacity_module,
        "run_capacity_proof_evidence_bundle",
        unexpected_bundle,
    )
    with pytest.raises(SystemExit) as raised:
        capacity_module.main(
            [
                "bundle",
                "--evidence-root",
                str((tmp_path / "evidence").resolve()),
                "--capacity-sandbox-root",
                str((tmp_path / "sandbox").resolve()),
                "--runtime-receipt",
                str(inputs["runtime_receipt"]),
                "--brief",
                str(inputs["brief"]),
                "--policy",
                str(inputs["policy"]),
                "--actor-identity",
                "actor-v0387",
            ]
        )
    assert raised.value.code == 2
    assert called is False


def test_bundle_cli_happy_path_calls_existing_bundle_and_prints_summary(
    tmp_path: Path,
    cli_task_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = _write_cli_inputs(tmp_path / "inputs")
    evidence_root = (cli_task_root / "evidence").resolve()
    sandbox_root = (cli_task_root / "sandbox").resolve()
    expected = CapacityEvidenceBundle(
        evidence_root=evidence_root,
        receipt={"status": "PASS", "cycles": [{"cycle": 1}, {"cycle": 2}]},
        capacity_receipt=CapacityEvidenceArtifact(
            logical_name="capacity-receipt.json",
            path=evidence_root / "capacity-receipt.json",
            sha256="a" * 64,
            media_type=CAPACITY_RECEIPT_MEDIA_TYPE,
            byte_length=1,
        ),
        cycle_measurements=(),
    )

    def fake_bundle(**kwargs: object) -> object:
        assert kwargs["capacity_sandbox_root"] == sandbox_root
        assert kwargs["evidence_root"] == evidence_root
        assert kwargs["runtime_receipt"] == RUNTIME_RECEIPT
        assert kwargs["actor_identity"] == "actor-v0387"
        return expected

    monkeypatch.setattr(capacity_module, "run_capacity_proof_evidence_bundle", fake_bundle)
    assert capacity_module.main(
        [
            "bundle",
            "--task-root",
            str(cli_task_root),
            "--evidence-root",
            str(evidence_root),
            "--capacity-sandbox-root",
            str(sandbox_root),
            "--runtime-receipt",
            str(inputs["runtime_receipt"]),
            "--brief",
            str(inputs["brief"]),
            "--policy",
            str(inputs["policy"]),
            "--actor-identity",
            "actor-v0387",
        ]
    ) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PASS"
    assert summary["cycle_count"] == 2


@pytest.mark.parametrize("bad_root", ["production", "runtime/manifest", "launchagents"])
def test_bundle_cli_rejects_production_root_before_bundle_call(
    tmp_path: Path,
    cli_task_root: Path,
    bad_root: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _write_cli_inputs(tmp_path / "inputs")
    called = False

    def unexpected_bundle(**_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("production root must be rejected before API call")

    monkeypatch.setattr(
        capacity_module,
        "run_capacity_proof_evidence_bundle",
        unexpected_bundle,
    )
    result = capacity_module.main(
        [
            "bundle",
            "--task-root",
            str(cli_task_root),
            "--evidence-root",
            str((tmp_path / bad_root / "evidence").resolve()),
            "--capacity-sandbox-root",
            str((cli_task_root / "sandbox").resolve()),
            "--runtime-receipt",
            str(inputs["runtime_receipt"]),
            "--brief",
            str(inputs["brief"]),
            "--policy",
            str(inputs["policy"]),
            "--actor-identity",
            "actor-v0387",
        ]
    )
    assert result != 0
    assert called is False


def test_bundle_cli_rejects_symlink_escape_before_bundle_call(
    tmp_path: Path,
    cli_task_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _write_cli_inputs(tmp_path / "inputs")
    outside = tmp_path / "outside"
    outside.mkdir()
    escaped = cli_task_root / "escaped"
    escaped.symlink_to(outside, target_is_directory=True)
    called = False

    def unexpected_bundle(**_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("symlink escape must be rejected before API call")

    monkeypatch.setattr(
        capacity_module,
        "run_capacity_proof_evidence_bundle",
        unexpected_bundle,
    )
    result = capacity_module.main(
        [
            "bundle",
            "--task-root",
            str(cli_task_root),
            "--evidence-root",
            str(escaped / "evidence"),
            "--capacity-sandbox-root",
            str(cli_task_root / "sandbox"),
            "--runtime-receipt",
            str(inputs["runtime_receipt"]),
            "--brief",
            str(inputs["brief"]),
            "--policy",
            str(inputs["policy"]),
            "--actor-identity",
            "actor-v0387",
        ]
    )
    assert result == 2
    assert called is False


@pytest.mark.parametrize(
    "policy",
    [
        {**DEFAULT_POLICY, "max_bytes": -1},
        {**DEFAULT_POLICY, "max_bytes": 0},
        {**DEFAULT_POLICY, "sampling_interval_seconds": 301},
        {key: value for key, value in DEFAULT_POLICY.items() if key != "max_bytes"},
    ],
)
def test_bundle_cli_rejects_invalid_or_unbounded_policy_before_bundle_call(
    tmp_path: Path,
    cli_task_root: Path,
    policy: dict[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _write_cli_inputs(tmp_path / "inputs")
    inputs["policy"].write_text(json.dumps(policy) + "\n", encoding="utf-8")
    called = False

    def unexpected_bundle(**_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("invalid policy must be rejected before API call")

    monkeypatch.setattr(
        capacity_module,
        "run_capacity_proof_evidence_bundle",
        unexpected_bundle,
    )
    result = capacity_module.main(
        [
            "bundle",
            "--task-root",
            str(cli_task_root),
            "--evidence-root",
            str(cli_task_root / "evidence"),
            "--capacity-sandbox-root",
            str(cli_task_root / "sandbox"),
            "--runtime-receipt",
            str(inputs["runtime_receipt"]),
            "--brief",
            str(inputs["brief"]),
            "--policy",
            str(inputs["policy"]),
            "--actor-identity",
            "actor-v0387",
        ]
    )
    assert result == 2
    assert called is False


def test_bundle_cli_rejects_missing_input_before_bundle_call(
    tmp_path: Path,
    cli_task_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _write_cli_inputs(tmp_path / "inputs")
    missing_receipt = inputs["runtime_receipt"].with_name("missing-runtime-receipt.json")
    called = False

    def unexpected_bundle(**_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("missing input must be rejected before API call")

    monkeypatch.setattr(
        capacity_module,
        "run_capacity_proof_evidence_bundle",
        unexpected_bundle,
    )
    result = capacity_module.main(
        [
            "bundle",
            "--task-root",
            str(cli_task_root),
            "--evidence-root",
            str(cli_task_root / "evidence"),
            "--capacity-sandbox-root",
            str(cli_task_root / "sandbox"),
            "--runtime-receipt",
            str(missing_receipt),
            "--brief",
            str(inputs["brief"]),
            "--policy",
            str(inputs["policy"]),
            "--actor-identity",
            "actor-v0387",
        ]
    )
    assert result == 2
    assert called is False

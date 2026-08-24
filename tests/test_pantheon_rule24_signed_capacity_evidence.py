from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import pantheon_rule24_dsse_attestation as rule24
from scripts import pantheon_rule24_signed_capacity_evidence as signed
from scripts.pantheon_writer_vnext_runtime_activation_capacity import DEFAULT_POLICY


PRODUCER_ID = "rule24-composition:test"
TARGET_NAME = "pantheon-rule24-composition-target"
TARGET_TYPE = "application/vnd.pantheon.rule24.target"
POLICY_NAME = "rule24-policy.json"
CORRELATION = "corr-rule24-composition"
CHALLENGE = "challenge-rule24-composition"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _openssl(*args: str) -> str:
    completed = subprocess.run(
        ["openssl", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _keypair(root: Path, name: str = "trusted") -> tuple[Path, Path, str]:
    private_key = root / f"{name}.private.pem"
    public_key = root / f"{name}.public.pem"
    _openssl("genpkey", "-algorithm", "ED25519", "-out", str(private_key))
    _openssl("pkey", "-in", str(private_key), "-pubout", "-out", str(public_key))
    fingerprint = rule24.public_key_fingerprint(public_key.resolve())
    return private_key.resolve(), public_key.resolve(), fingerprint


def _sample(label: str) -> dict[str, object]:
    return {
        "label": label,
        "sampled_epoch": 1.0,
        "elapsed_seconds": 1.0,
        "host_total_bytes": 500 * 1024**3,
        "host_free_bytes": 250 * 1024**3,
        "project_bytes": 16,
        "file_count": 1,
        "process_rss_bytes": 64 * 1024**2,
        "swap_used_bytes": 0,
    }


def _cycle(cycle: int) -> dict[str, object]:
    return {
        "cycle": cycle,
        "execution_line_id": f"exec-{cycle}",
        "correlation_id": f"corr-{cycle}",
        "root": f"/tmp/pantheon-cycle-{cycle}",
        "root_unique": True,
        "capability_receipt_status": "PASS",
        "seven_step_capabilities": [
            "create",
            "run",
            "select",
            "publish",
            "transaction",
            "tag",
            "push",
        ],
        "canary_created": False,
        "production_mutation": False,
        "before": _sample(f"cycle-{cycle}-before"),
        "peak": _sample(f"cycle-{cycle}-peak"),
        "after_cleanup": _sample(f"cycle-{cycle}-after-cleanup"),
        "growth_bytes_per_hour": 16,
        "peak_transaction_temp_bytes": 16,
        "cleanup": {
            "root_exists_after_cleanup": False,
            "elapsed_seconds": 0.1,
            "reclaimed_bytes": 16,
            "reclaimed_file_count": 1,
        },
    }


def _capacity_receipt(*, status: str = "PASS") -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": status,
        "mode": "synthetic-non-production-capacity-proof",
        "cycles": [_cycle(1), _cycle(2)],
        "policy": dict(DEFAULT_POLICY),
        "projections": {
            "measured_max_growth_bytes_per_hour": 16,
            "projected_growth_bytes_per_hour": 16,
            "hour_peak_bytes": 32,
            "day_peak_bytes": 400,
            "retention_peak_bytes": 400,
            "host_reserve_bytes": 50 * 1024**3,
            "host_free_after_projection_bytes": 200 * 1024**3,
        },
        "stop_loss_negative_result": "BLOCKED",
        "canary_created": False,
        "production_mutation": False,
    }


def _write_capacity_artifacts(evidence_root: Path, *, status: str = "PASS") -> dict[str, object]:
    receipt = _capacity_receipt(status=status)
    evidence_root.mkdir(parents=True, exist_ok=True)
    _write_json(evidence_root / "cycle-1-measurements.json", receipt["cycles"][0])
    _write_json(evidence_root / "cycle-2-measurements.json", receipt["cycles"][1])
    _write_json(evidence_root / "capacity-receipt.json", receipt)
    return receipt


def _fixture(tmp_path: Path) -> dict[str, object]:
    private_key, public_key, fingerprint = _keypair(tmp_path)
    target = tmp_path / "target.txt"
    policy = tmp_path / POLICY_NAME
    target.write_text("target-v1\n", encoding="utf-8")
    _write_json(policy, {"policy": "rule24", "threshold": 1})
    trust_policy = tmp_path / "trust-policy.json"
    _write_json(
        trust_policy,
        {
            "schema_version": 1,
            "producer_id": PRODUCER_ID,
            "pinned_public_key_fingerprint": fingerprint,
            "allowed_predicate_type": rule24.PREDICATE_TYPE,
            "threshold": 1,
        },
    )
    challenge = tmp_path / "challenge.json"
    replay_state = tmp_path / "external-replay"
    replay_state.mkdir()
    _write_json(
        challenge,
        {
            "schema_version": 1,
            "correlation": CORRELATION,
            "challenge": CHALLENGE,
            "expires_epoch": 4_102_444_800,
            "consumed": False,
        },
    )
    evidence_root = tmp_path / "evidence"
    _write_capacity_artifacts(evidence_root)
    return {
        "private_key": private_key,
        "public_key": public_key,
        "target": target.resolve(),
        "policy": policy.resolve(),
        "trust_policy": trust_policy.resolve(),
        "challenge": challenge.resolve(),
        "replay_state": replay_state.resolve(),
        "evidence_root": evidence_root.resolve(),
    }


def _cycle_inputs(evidence_root: Path) -> tuple[signed.CapacityArtifactInput, ...]:
    return (
        signed.CapacityArtifactInput(
            logical_name="cycle-1-measurements.json",
            media_type=signed.CYCLE_MEASUREMENT_MEDIA_TYPE,
            path=(evidence_root / "cycle-1-measurements.json").resolve(),
            raw_bytes=(evidence_root / "cycle-1-measurements.json").read_bytes(),
        ),
        signed.CapacityArtifactInput(
            logical_name="cycle-2-measurements.json",
            media_type=signed.CYCLE_MEASUREMENT_MEDIA_TYPE,
            path=(evidence_root / "cycle-2-measurements.json").resolve(),
            raw_bytes=(evidence_root / "cycle-2-measurements.json").read_bytes(),
        ),
    )


def _produce_with_existing_artifacts(fixture: dict[str, object]) -> dict[str, object]:
    evidence_root = Path(fixture["evidence_root"])
    return rule24.produce_rule24_attestation(
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=[
            rule24.ResourceInput(item.logical_name, item.media_type, item.path)
            for item in _cycle_inputs(evidence_root)
        ],
        correlation=CORRELATION,
        challenge=CHALLENGE,
        capacity_evidence_input=rule24.ResourceInput(
            rule24.CAPACITY_EVIDENCE_NAME,
            rule24.CAPACITY_EVIDENCE_MEDIA_TYPE,
            (evidence_root / "capacity-receipt.json").resolve(),
        ),
    )


def _verify(
    fixture: dict[str, object],
    envelope: dict[str, object],
    *,
    observer: object | None = None,
    cycles: tuple[signed.CapacityArtifactInput, ...] | None = None,
    capacity_bytes: bytes | None = None,
) -> dict[str, object]:
    evidence_root = Path(fixture["evidence_root"])
    return signed.verify_signed_capacity_evidence(
        envelope=envelope,
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        capacity_receipt_path=(evidence_root / "capacity-receipt.json").resolve(),
        capacity_receipt_bytes=(
            (evidence_root / "capacity-receipt.json").read_bytes()
            if capacity_bytes is None
            else capacity_bytes
        ),
        capacity_cycle_artifacts=_cycle_inputs(evidence_root) if cycles is None else cycles,
        expected_challenge_path=fixture["challenge"],
        replay_state_dir=fixture["replay_state"],
        verified_payload_observer=observer,
    )


def test_producer_runs_capacity_bundle_then_offline_verifier_reauth_domain_claims_and_releases(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    calls: list[Path] = []

    def capacity_evaluator(**kwargs: object) -> dict[str, object]:
        evidence_root = Path(kwargs["evidence_root"])
        calls.append(evidence_root)
        return _write_capacity_artifacts(evidence_root)

    produced = signed.produce_signed_capacity_evidence(
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=fixture["evidence_root"],
        runtime_receipt={"status": "PASS", "runtime_identity_digest": "d" * 64},
        actor_identity="actor-rule24-composition",
        brief={"schema_version": 1, "run_id": "rule24-composition"},
        capacity_policy=DEFAULT_POLICY,
        correlation=CORRELATION,
        challenge=CHALLENGE,
        capacity_evaluator=capacity_evaluator,
    )
    observed: list[bytes] = []
    verified = _verify(fixture, produced["envelope"], observer=observed.append)

    assert calls == [fixture["evidence_root"]]
    assert produced["status"] == "PASS"
    assert verified["status"] == "PASS"
    assert verified["mode"] == "verify-signed-capacity-evidence"
    assert verified["production_mutation"] is False
    assert verified["canary_created"] is False
    assert verified["authorization_granted"] is False
    assert observed == [base64.b64decode(produced["envelope"]["payload"])]
    assert len(list(Path(fixture["replay_state"]).glob("*.json"))) == 1


def test_producer_rejects_post_bundle_capacity_receipt_drift_without_signed_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    original_bundle = signed.run_capacity_proof_evidence_bundle

    def drift_after_bundle(**kwargs: object) -> object:
        bundle = original_bundle(**kwargs)
        receipt_path = bundle.capacity_receipt.path
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["policy"]["normal_growth_bytes_per_hour"] += 1
        _write_json(receipt_path, receipt)
        return bundle

    monkeypatch.setattr(signed, "run_capacity_proof_evidence_bundle", drift_after_bundle)

    result = signed.produce_signed_capacity_evidence(
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=fixture["evidence_root"],
        runtime_receipt={"status": "PASS", "runtime_identity_digest": "d" * 64},
        actor_identity="actor-rule24-composition",
        brief={"schema_version": 1, "run_id": "rule24-composition"},
        capacity_policy=DEFAULT_POLICY,
        correlation=CORRELATION,
        challenge=CHALLENGE,
        capacity_evaluator=lambda **kwargs: _write_capacity_artifacts(Path(kwargs["evidence_root"])),
    )

    assert result["status"] == "NO-GO"
    assert result["reason"] == "capacity_bundle_drift"
    assert "envelope" not in result
    assert "authenticated_statement_digest" not in result
    assert "capacity_artifacts" not in result
    assert result["authorization_granted"] is False


def test_producer_rejects_post_bundle_cycle_artifact_drift_without_signed_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    original_bundle = signed.run_capacity_proof_evidence_bundle

    def drift_after_bundle(**kwargs: object) -> object:
        bundle = original_bundle(**kwargs)
        receipt_path = bundle.capacity_receipt.path
        cycle_path = bundle.cycle_measurements[0].path
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["cycles"][0]["growth_bytes_per_hour"] += 1
        _write_json(cycle_path, receipt["cycles"][0])
        _write_json(receipt_path, receipt)
        return bundle

    monkeypatch.setattr(signed, "run_capacity_proof_evidence_bundle", drift_after_bundle)

    result = signed.produce_signed_capacity_evidence(
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        capacity_sandbox_root=(tmp_path / "capacity-sandbox").resolve(),
        evidence_root=fixture["evidence_root"],
        runtime_receipt={"status": "PASS", "runtime_identity_digest": "d" * 64},
        actor_identity="actor-rule24-composition",
        brief={"schema_version": 1, "run_id": "rule24-composition"},
        capacity_policy=DEFAULT_POLICY,
        correlation=CORRELATION,
        challenge=CHALLENGE,
        capacity_evaluator=lambda **kwargs: _write_capacity_artifacts(Path(kwargs["evidence_root"])),
    )

    assert result["status"] == "NO-GO"
    assert result["reason"] == "capacity_bundle_drift"
    assert "envelope" not in result
    assert "authenticated_statement_digest" not in result
    assert "capacity_artifacts" not in result
    assert result["authorization_granted"] is False


def test_signature_pass_cannot_wash_capacity_domain_failure_or_release_payload(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _write_capacity_artifacts(Path(fixture["evidence_root"]), status="BLOCKED")
    produced = _produce_with_existing_artifacts(fixture)
    observed: list[bytes] = []

    result = _verify(fixture, produced["envelope"], observer=observed.append)

    assert result == {
        "schema_version": 1,
        "status": "NO-GO",
        "reason": "capacity_status",
        "production_mutation": False,
        "canary_created": False,
        "authorization_granted": False,
    }
    assert observed == []
    assert list(Path(fixture["replay_state"]).iterdir()) == []


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda receipt: receipt.__setitem__("unexpected", True),
            "capacity_unknown_field",
        ),
        (
            lambda receipt: receipt["cycles"].append(_cycle(3)),
            "capacity_cycle_count",
        ),
        (
            lambda receipt: receipt["cycles"].__setitem__(0, _cycle(2)),
            "capacity_cycle_identity",
        ),
        (
            lambda receipt: receipt["cycles"][0].__setitem__("growth_bytes_per_hour", True),
            "capacity_numeric_contract",
        ),
        (
            lambda receipt: receipt.__setitem__("production_mutation", True),
            "capacity_production_boundary",
        ),
    ],
)
def test_capacity_domain_negative_matrix_fails_before_replay_claim(
    tmp_path: Path,
    mutate: object,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    receipt = _capacity_receipt()
    mutate(receipt)
    evidence_root = Path(fixture["evidence_root"])
    _write_json(evidence_root / "capacity-receipt.json", receipt)
    if reason not in {"capacity_cycle_count", "capacity_cycle_identity"}:
        _write_json(evidence_root / "cycle-1-measurements.json", _capacity_receipt()["cycles"][0])
        _write_json(evidence_root / "cycle-2-measurements.json", _capacity_receipt()["cycles"][1])
    produced = _produce_with_existing_artifacts(fixture)

    result = _verify(fixture, produced["envelope"])

    assert result["status"] == "NO-GO"
    assert result["reason"] == reason
    assert "authenticated_statement_digest" not in result
    assert list(Path(fixture["replay_state"]).iterdir()) == []


def test_exact_capacity_bytes_must_match_caller_owned_paths_before_auth_release(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    produced = _produce_with_existing_artifacts(fixture)
    observed: list[bytes] = []

    result = _verify(
        fixture,
        produced["envelope"],
        observer=observed.append,
        capacity_bytes=Path(fixture["evidence_root"], "capacity-receipt.json").read_bytes() + b"\n",
    )

    assert result["status"] == "NO-GO"
    assert result["reason"] == "capacity_receipt_bytes_mismatch"
    assert observed == []
    assert list(Path(fixture["replay_state"]).iterdir()) == []


def test_cycle_artifact_order_duplicate_and_path_tamper_fail_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    produced = _produce_with_existing_artifacts(fixture)
    first = _cycle_inputs(Path(fixture["evidence_root"]))[0]
    duplicate = (first, first)

    result = _verify(fixture, produced["envelope"], cycles=duplicate)

    assert result["status"] == "NO-GO"
    assert result["reason"] == "capacity_cycle_duplicate"
    assert list(Path(fixture["replay_state"]).iterdir()) == []


def test_commit_failure_does_not_release_observer_payload(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    produced = _produce_with_existing_artifacts(fixture)
    observed: list[bytes] = []

    first = _verify(fixture, produced["envelope"], observer=observed.append)
    second = _verify(fixture, produced["envelope"], observer=observed.append)

    assert first["status"] == "PASS"
    assert second["status"] == "NO-GO"
    assert second["reason"] == "challenge_replay"
    assert observed == [base64.b64decode(produced["envelope"]["payload"])]


def test_forged_prior_authenticated_object_cannot_authorize_claim_or_observer_release(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    produced = _produce_with_existing_artifacts(fixture)
    authenticated = rule24.authenticate_rule24_attestation(
        envelope=produced["envelope"],
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=[
            rule24.ResourceInput(item.logical_name, item.media_type, item.path)
            for item in _cycle_inputs(Path(fixture["evidence_root"]))
        ],
        expected_challenge_path=fixture["challenge"],
        capacity_evidence_bytes=Path(fixture["evidence_root"], "capacity-receipt.json").read_bytes(),
    )
    observed: list[bytes] = []

    result = _verify(fixture, authenticated, observer=observed.append)  # type: ignore[arg-type]

    assert result["status"] == "NO-GO"
    assert result["reason"] == "envelope_contract"
    assert observed == []
    assert list(Path(fixture["replay_state"]).iterdir()) == []


def test_cli_verify_emits_single_machine_readable_json_and_nonzero_no_go(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    produced = _produce_with_existing_artifacts(fixture)
    envelope_path = tmp_path / "envelope.json"
    _write_json(envelope_path, produced["envelope"])
    replay_in_repo = Path.cwd() / "artifacts"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/pantheon_rule24_signed_capacity_evidence.py",
            "verify",
            "--envelope",
            str(envelope_path.resolve()),
            "--trust-policy",
            str(fixture["trust_policy"]),
            "--pinned-public-key",
            str(fixture["public_key"]),
            "--target-path",
            str(fixture["target"]),
            "--target-name",
            TARGET_NAME,
            "--target-media-type",
            TARGET_TYPE,
            "--rule24-policy-path",
            str(fixture["policy"]),
            "--rule24-policy-name",
            POLICY_NAME,
            "--capacity-receipt",
            str(Path(fixture["evidence_root"], "capacity-receipt.json").resolve()),
            "--cycle-artifact",
            f"cycle-1-measurements.json:{signed.CYCLE_MEASUREMENT_MEDIA_TYPE}:{Path(fixture['evidence_root'], 'cycle-1-measurements.json').resolve()}",
            "--cycle-artifact",
            f"cycle-2-measurements.json:{signed.CYCLE_MEASUREMENT_MEDIA_TYPE}:{Path(fixture['evidence_root'], 'cycle-2-measurements.json').resolve()}",
            "--expected-challenge",
            str(fixture["challenge"]),
            "--replay-state-dir",
            str(replay_in_repo),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["status"] == "NO-GO"
    assert payload["reason"] == "replay_state_in_repo"
    assert completed.stdout.count("\n") == 1

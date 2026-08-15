from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from scripts import pantheon_gate_a_governance as governance


SOURCE_SHA = "a" * 40
PLAN_DIGEST = "b" * 64


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _authorization(repo_root: Path, *, evidence_root: str = "evidence/gate-a") -> dict[str, object]:
    argv = [
        "<runtime-python-executable>",
        "-m",
        "scripts.pantheon_content_runtime_promotion",
        "apply",
        "--source-repo",
        "<source-worktree>",
        "--source-sha",
        SOURCE_SHA,
        "--expected-origin",
        "git@example.invalid:pantheon.git",
        "--actor-root",
        "<runtime-root>/actor",
        "--expected-current-actor-sha",
        "c" * 40,
        "--manifest-path",
        "<runtime-root>/runtime-manifest.json",
        "--expected-current-manifest-digest",
        "d" * 64,
        "--private-stage-root",
        "<private-stage-root>",
        "--expected-current-stage-digest",
        "e" * 64,
        "--transaction-root",
        "<runtime-root>/backups/gate-a",
        "--queue-root",
        "<runtime-root>/queue",
        "--publisher-state-root",
        "<runtime-root>/state",
        "--log-root",
        "<runtime-root>/logs",
        "--target-identity",
        f"gate2-actor:{SOURCE_SHA}:activation-only",
        "--target-runtime-digest",
        "f" * 64,
        "--target-config-version",
        "formal-runtime-v2-gate2",
        "--target-generation",
        "g2-test",
        "--target-python-executable",
        "<runtime-python-executable>",
        "--authorization-digest",
        "1" * 64,
        "--capacity-receipt",
        "<repo-root>/capacity.json",
        "--capacity-receipt-digest",
        "2" * 64,
        "--correlation-id",
        "gate-a-test",
        "--expected-plan-digest",
        PLAN_DIGEST,
    ]
    argv_digest = sha256(
        json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    _write_json(
        repo_root / "artifacts/exact-apply-argv.json",
        {
            "schema_version": 1,
            "argv": argv,
            "canonical_argv_sha256": argv_digest,
            "expected_plan_digest": PLAN_DIGEST,
            "execution_status": "not_executed",
        },
    )
    return {
        "schema_version": 1,
        "authorization_id": "gate-a-001",
        "authorization_status": "AUTHORIZED",
        "authorization_expires_at": "2099-01-01T00:00:00Z",
        "authorization_revoked": False,
        "production_target": f"gate2-actor:{SOURCE_SHA}:activation-only",
        "source_sha": SOURCE_SHA,
        "plan_digest": PLAN_DIGEST,
        "exact_apply_argv_artifact": "artifacts/exact-apply-argv.json",
        "exact_apply_argv_digest": argv_digest,
        "mutation_scope": "runtime-promotion-apply-once",
        "rollback_contract": "rollback-bundle-retained-until-explicit-finalize",
        "evidence_root": evidence_root,
    }


def _authorization_state(
    authorization: dict[str, object],
    *,
    apply_calls: int = 0,
    last_outcome: str = "AUTHORIZED",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "authorization_id": authorization["authorization_id"],
        "immutable_tuple_digest": governance.immutable_tuple_digest(authorization),
        "apply_calls": apply_calls,
        "last_outcome": last_outcome,
    }


def test_valid_authorization_is_ready_before_mutation(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "READY"
    assert receipt["authorization_state"] == "UNCONSUMED"
    assert receipt["apply_calls"] == 0
    assert receipt["apply_call_budget"] == 1
    assert receipt["production_mutation"] == 0
    assert receipt["errors"] == []


def test_missing_evidence_root_blocks_before_mutation(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    del authorization["evidence_root"]

    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "missing_field:evidence_root" in receipt["errors"]
    assert receipt["apply_calls"] == 0


def test_evidence_root_path_traversal_blocks(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path, evidence_root="../outside")
    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "evidence_root_outside_repo" in receipt["errors"]


def test_existing_evidence_root_blocks_duplicate_write(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    (tmp_path / "evidence/gate-a").mkdir(parents=True)

    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "evidence_root_already_exists" in receipt["errors"]


def test_unchanged_tuple_and_zero_apply_calls_keeps_authority(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    state = _authorization_state(
        authorization,
        last_outcome="BLOCKED_BEFORE_MUTATION",
    )
    retry = _authorization(tmp_path, evidence_root="evidence/gate-a-retry")

    receipt = governance.validate_authorization(
        retry,
        tmp_path,
        authorization_state=state,
    )

    assert receipt["status"] == "READY"
    assert receipt["authorization_state"] == "UNCONSUMED_RETRY"
    assert receipt["immutable_tuple_digest"] == state["immutable_tuple_digest"]


def test_tuple_drift_requires_new_authorization(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    state = _authorization_state(authorization)
    drifted = deepcopy(authorization)
    drifted["mutation_scope"] = "different-production-write"

    receipt = governance.validate_authorization(
        drifted,
        tmp_path,
        authorization_state=state,
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert receipt["authorization_state"] == "REAUTHORIZATION_REQUIRED"
    assert "immutable_tuple_drift" in receipt["errors"]


def test_apply_calls_greater_than_zero_consumes_authority(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization, apply_calls=1),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert receipt["authorization_state"] == "CONSUMED"
    assert "authorization_consumed" in receipt["errors"]
    assert "authorization_state_outcome_counter_inconsistent" in receipt["errors"]


def test_terminal_outcome_with_zero_calls_stays_consumed_and_blocks(tmp_path: Path) -> None:
    for last_outcome in ("APPLIED", "ROLLED_BACK"):
        authorization = _authorization(
            tmp_path,
            evidence_root=f"evidence/gate-a-{last_outcome.lower()}",
        )
        receipt = governance.validate_authorization(
            authorization,
            tmp_path,
            authorization_state=_authorization_state(
                authorization,
                apply_calls=0,
                last_outcome=last_outcome,
            ),
        )

        assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
        assert receipt["authorization_state"] == "CONSUMED"
        assert "authorization_consumed" in receipt["errors"]
        assert "authorization_state_outcome_counter_inconsistent" in receipt["errors"]


def test_expired_or_revoked_authority_blocks(tmp_path: Path) -> None:
    expired = _authorization(tmp_path)
    expired["authorization_expires_at"] = "2000-01-01T00:00:00Z"
    revoked = _authorization(tmp_path, evidence_root="evidence/revoked")
    revoked["authorization_revoked"] = True

    expired_receipt = governance.validate_authorization(
        expired,
        tmp_path,
        authorization_state=_authorization_state(expired),
    )
    revoked_receipt = governance.validate_authorization(
        revoked,
        tmp_path,
        authorization_state=_authorization_state(revoked),
    )

    assert "authorization_expired" in expired_receipt["errors"]
    assert "authorization_revoked" in revoked_receipt["errors"]


def test_exact_argv_digest_drift_blocks(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    authorization["exact_apply_argv_digest"] = "0" * 64

    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "exact_apply_argv_digest_mismatch" in receipt["errors"]


def test_public_cli_emits_machine_readable_receipt(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    state_path = tmp_path / "authorization-state.json"
    authorization = _authorization(tmp_path)
    _write_json(authorization_path, authorization)
    _write_json(state_path, _authorization_state(authorization))

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.pantheon_gate_a_governance",
            "--repo-root",
            str(tmp_path),
            "--authorization",
            str(authorization_path),
            "--authorization-state",
            str(state_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "READY"


def test_public_cli_requires_durable_authorization_state(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    _write_json(authorization_path, _authorization(tmp_path))

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.pantheon_gate_a_governance",
            "--repo-root",
            str(tmp_path),
            "--authorization",
            str(authorization_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "--authorization-state" in completed.stderr


def test_duplicate_sensitive_flag_blocks_runtime_parser_override(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    artifact_path = tmp_path / str(authorization["exact_apply_argv_artifact"])
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["argv"].extend(["--source-sha", "f" * 40])
    artifact["canonical_argv_sha256"] = governance.canonical_argv_digest(artifact["argv"])
    authorization["exact_apply_argv_digest"] = artifact["canonical_argv_sha256"]
    _write_json(artifact_path, artifact)

    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "duplicate_sensitive_flag:--source-sha" in receipt["errors"]


def test_invalid_immutable_field_types_block(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    authorization["production_target"] = 123
    authorization["mutation_scope"] = []
    authorization["rollback_contract"] = {}

    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        authorization_state=_authorization_state(authorization),
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "production_target_invalid" in receipt["errors"]
    assert "mutation_scope_invalid" in receipt["errors"]
    assert "rollback_contract_invalid" in receipt["errors"]

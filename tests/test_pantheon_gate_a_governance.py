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
        "--source-sha",
        SOURCE_SHA,
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


def test_valid_authorization_is_ready_before_mutation(tmp_path: Path) -> None:
    receipt = governance.validate_authorization(_authorization(tmp_path), tmp_path)

    assert receipt["status"] == "READY"
    assert receipt["authorization_state"] == "UNCONSUMED"
    assert receipt["apply_calls"] == 0
    assert receipt["apply_call_budget"] == 1
    assert receipt["production_mutation"] == 0
    assert receipt["errors"] == []


def test_missing_evidence_root_blocks_before_mutation(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    del authorization["evidence_root"]

    receipt = governance.validate_authorization(authorization, tmp_path)

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "missing_field:evidence_root" in receipt["errors"]
    assert receipt["apply_calls"] == 0


def test_evidence_root_path_traversal_blocks(tmp_path: Path) -> None:
    receipt = governance.validate_authorization(
        _authorization(tmp_path, evidence_root="../outside"),
        tmp_path,
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "evidence_root_outside_repo" in receipt["errors"]


def test_existing_evidence_root_blocks_duplicate_write(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    (tmp_path / "evidence/gate-a").mkdir(parents=True)

    receipt = governance.validate_authorization(authorization, tmp_path)

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "evidence_root_already_exists" in receipt["errors"]


def test_unchanged_tuple_and_zero_apply_calls_keeps_authority(tmp_path: Path) -> None:
    first = governance.validate_authorization(_authorization(tmp_path), tmp_path)
    first["status"] = "BLOCKED_BEFORE_MUTATION"
    retry = _authorization(tmp_path, evidence_root="evidence/gate-a-retry")

    receipt = governance.validate_authorization(
        retry,
        tmp_path,
        previous_receipt=first,
    )

    assert receipt["status"] == "READY"
    assert receipt["authorization_state"] == "UNCONSUMED_RETRY"
    assert receipt["immutable_tuple_digest"] == first["immutable_tuple_digest"]


def test_tuple_drift_requires_new_authorization(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    previous = governance.validate_authorization(authorization, tmp_path)
    drifted = deepcopy(authorization)
    drifted["mutation_scope"] = "different-production-write"

    receipt = governance.validate_authorization(
        drifted,
        tmp_path,
        previous_receipt=previous,
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert receipt["authorization_state"] == "REAUTHORIZATION_REQUIRED"
    assert "immutable_tuple_drift" in receipt["errors"]


def test_apply_calls_greater_than_zero_consumes_authority(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    previous = governance.validate_authorization(authorization, tmp_path)
    previous["apply_calls"] = 1

    receipt = governance.validate_authorization(
        authorization,
        tmp_path,
        previous_receipt=previous,
    )

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert receipt["authorization_state"] == "CONSUMED"
    assert "authorization_consumed" in receipt["errors"]


def test_expired_or_revoked_authority_blocks(tmp_path: Path) -> None:
    expired = _authorization(tmp_path)
    expired["authorization_expires_at"] = "2000-01-01T00:00:00Z"
    revoked = _authorization(tmp_path, evidence_root="evidence/revoked")
    revoked["authorization_revoked"] = True

    expired_receipt = governance.validate_authorization(expired, tmp_path)
    revoked_receipt = governance.validate_authorization(revoked, tmp_path)

    assert "authorization_expired" in expired_receipt["errors"]
    assert "authorization_revoked" in revoked_receipt["errors"]


def test_exact_argv_digest_drift_blocks(tmp_path: Path) -> None:
    authorization = _authorization(tmp_path)
    authorization["exact_apply_argv_digest"] = "0" * 64

    receipt = governance.validate_authorization(authorization, tmp_path)

    assert receipt["status"] == "BLOCKED_BEFORE_MUTATION"
    assert "exact_apply_argv_digest_mismatch" in receipt["errors"]


def test_public_cli_emits_machine_readable_receipt(tmp_path: Path) -> None:
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

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "READY"

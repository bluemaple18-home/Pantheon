#!/usr/bin/env python3
"""在 Gate A thread dispatch 前驗證 schema 與 mutation authority。"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from typing import Any

from scripts import pantheon_content_runtime_promotion as promotion


SCHEMA_VERSION = 1
REQUIRED_FIELDS = (
    "schema_version",
    "authorization_id",
    "authorization_status",
    "authorization_expires_at",
    "authorization_revoked",
    "production_target",
    "source_sha",
    "plan_digest",
    "exact_apply_argv_artifact",
    "exact_apply_argv_digest",
    "mutation_scope",
    "rollback_contract",
    "evidence_root",
)
IMMUTABLE_FIELDS = (
    "production_target",
    "source_sha",
    "plan_digest",
    "exact_apply_argv_digest",
    "mutation_scope",
    "rollback_contract",
    "authorization_expires_at",
    "authorization_revoked",
)
SHA40 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
STRING_FIELDS = (
    "authorization_id",
    "production_target",
    "exact_apply_argv_artifact",
    "mutation_scope",
    "rollback_contract",
    "evidence_root",
)
SENSITIVE_FLAGS = ("--source-sha", "--expected-plan-digest")


def _json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return sha256(encoded).hexdigest()


def canonical_argv_digest(argv: list[object]) -> str:
    return _json_digest(argv)


def _repo_path(repo_root: Path, value: object, field: str) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None, f"{field}_outside_repo"
    root = repo_root.resolve()
    candidate = (root / value).resolve(strict=False)
    if not candidate.is_relative_to(root):
        return None, f"{field}_outside_repo"
    return candidate, None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    return payload


def immutable_tuple_digest(authorization: dict[str, object]) -> str:
    return _json_digest({field: authorization.get(field) for field in IMMUTABLE_FIELDS})


def validate_authorization(
    authorization: dict[str, object],
    repo_root: Path,
    *,
    authorization_state: dict[str, object],
    now: datetime | None = None,
) -> dict[str, object]:
    errors = [f"missing_field:{field}" for field in REQUIRED_FIELDS if field not in authorization]
    tuple_digest = immutable_tuple_digest(authorization)
    authority_status = "UNCONSUMED"
    apply_calls = 0

    if type(authorization.get("schema_version")) is not int or authorization.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_unsupported")
    if authorization.get("authorization_status") != "AUTHORIZED":
        errors.append("authorization_status_not_authorized")
    if type(authorization.get("authorization_revoked")) is not bool or authorization.get("authorization_revoked") is not False:
        errors.append("authorization_revoked")
    for field in STRING_FIELDS:
        if not isinstance(authorization.get(field), str) or not authorization.get(field):
            errors.append(f"{field}_invalid")
    if authorization.get("mutation_scope") != "runtime-promotion-apply-once":
        errors.append("mutation_scope_invalid")
    if authorization.get("rollback_contract") != "rollback-bundle-retained-until-explicit-finalize":
        errors.append("rollback_contract_invalid")
    if not SHA40.fullmatch(str(authorization.get("source_sha", ""))):
        errors.append("source_sha_invalid")
    for field in ("plan_digest", "exact_apply_argv_digest"):
        if not SHA256.fullmatch(str(authorization.get(field, ""))):
            errors.append(f"{field}_invalid")

    expires_at = authorization.get("authorization_expires_at")
    if not isinstance(expires_at, str):
        errors.append("authorization_expiry_invalid")
    else:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                raise ValueError
            if expiry <= (now or datetime.now(timezone.utc)):
                errors.append("authorization_expired")
        except ValueError:
            errors.append("authorization_expiry_invalid")

    evidence_root, path_error = _repo_path(
        repo_root,
        authorization.get("evidence_root"),
        "evidence_root",
    )
    if path_error:
        errors.append(path_error)
    elif evidence_root is not None and evidence_root.exists():
        errors.append("evidence_root_already_exists")

    argv_artifact, artifact_error = _repo_path(
        repo_root,
        authorization.get("exact_apply_argv_artifact"),
        "exact_apply_argv_artifact",
    )
    if artifact_error:
        errors.append(artifact_error)
    elif argv_artifact is None or not argv_artifact.is_file():
        errors.append("exact_apply_argv_artifact_missing")
    else:
        try:
            artifact = _load_json(argv_artifact)
            argv = artifact.get("argv")
            if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
                errors.append("exact_apply_argv_invalid")
            else:
                actual_digest = canonical_argv_digest(argv)
                if actual_digest != authorization.get("exact_apply_argv_digest"):
                    errors.append("exact_apply_argv_digest_mismatch")
                if artifact.get("canonical_argv_sha256") != actual_digest:
                    errors.append("exact_apply_argv_artifact_digest_mismatch")
                if len(argv) < 4 or argv[1:4] != [
                    "-m",
                    "scripts.pantheon_content_runtime_promotion",
                    "apply",
                ]:
                    errors.append("exact_apply_argv_not_apply")
                for flag in SENSITIVE_FLAGS:
                    if argv.count(flag) != 1:
                        errors.append(f"duplicate_sensitive_flag:{flag}")
                try:
                    with redirect_stderr(io.StringIO()):
                        parsed = promotion.parse_args(argv[3:])
                    if parsed.command != "apply":
                        errors.append("exact_apply_argv_not_apply")
                    if parsed.source_sha != authorization.get("source_sha"):
                        errors.append("source_sha_binding_mismatch")
                    if parsed.expected_plan_digest != authorization.get("plan_digest"):
                        errors.append("plan_digest_binding_mismatch")
                    if parsed.target_identity != authorization.get("production_target"):
                        errors.append("production_target_binding_mismatch")
                except SystemExit:
                    errors.append("exact_apply_argv_parse_failed")
                if artifact.get("expected_plan_digest") != authorization.get("plan_digest"):
                    errors.append("plan_artifact_digest_mismatch")
                if artifact.get("execution_status") != "not_executed":
                    errors.append("exact_apply_argv_already_executed")
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("exact_apply_argv_artifact_invalid")

    for field in (
        "schema_version",
        "authorization_id",
        "immutable_tuple_digest",
        "apply_calls",
        "last_outcome",
    ):
        if field not in authorization_state:
            errors.append(f"authorization_state_missing_field:{field}")
    if (
        type(authorization_state.get("schema_version")) is not int
        or authorization_state.get("schema_version") != SCHEMA_VERSION
    ):
        errors.append("authorization_state_schema_invalid")
    state_calls = authorization_state.get("apply_calls")
    calls_are_valid = type(state_calls) is int and state_calls >= 0
    if not calls_are_valid:
        errors.append("authorization_state_apply_calls_invalid")
    else:
        apply_calls = state_calls
        if apply_calls > 0:
            authority_status = "CONSUMED"
            errors.append("authorization_consumed")
    if authorization_state.get("authorization_id") != authorization.get("authorization_id"):
        authority_status = "REAUTHORIZATION_REQUIRED"
        errors.append("authorization_id_drift")
    state_tuple_digest = authorization_state.get("immutable_tuple_digest")
    if not isinstance(state_tuple_digest, str) or not SHA256.fullmatch(state_tuple_digest):
        errors.append("authorization_state_tuple_digest_invalid")
    if state_tuple_digest != tuple_digest:
        authority_status = "REAUTHORIZATION_REQUIRED"
        errors.append("immutable_tuple_drift")
    last_outcome = authorization_state.get("last_outcome")
    if last_outcome not in {
        "AUTHORIZED",
        "BLOCKED_BEFORE_MUTATION",
        "APPLIED",
        "ROLLED_BACK",
    }:
        errors.append("authorization_state_last_outcome_invalid")
    elif last_outcome in {"APPLIED", "ROLLED_BACK"}:
        authority_status = "CONSUMED"
        errors.append("authorization_consumed")
        if calls_are_valid and apply_calls != 1:
            errors.append("authorization_state_outcome_counter_inconsistent")
    elif calls_are_valid and apply_calls != 0:
        errors.append("authorization_state_outcome_counter_inconsistent")
    elif last_outcome == "BLOCKED_BEFORE_MUTATION":
        authority_status = "UNCONSUMED_RETRY"

    errors = list(dict.fromkeys(errors))
    status = "READY" if not errors else "BLOCKED_BEFORE_MUTATION"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "authorization_id": authorization.get("authorization_id"),
        "authorization_state": authority_status,
        "immutable_tuple_digest": tuple_digest,
        "evidence_root": authorization.get("evidence_root"),
        "apply_calls": apply_calls,
        "apply_call_budget": 1,
        "production_mutation": 0,
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--authorization-state", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        authorization = _load_json(args.authorization)
        authorization_state = _load_json(args.authorization_state)
        receipt = validate_authorization(
            authorization,
            args.repo_root,
            authorization_state=authorization_state,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "status": "BLOCKED_BEFORE_MUTATION",
            "authorization_state": "UNKNOWN",
            "apply_calls": 0,
            "apply_call_budget": 1,
            "production_mutation": 0,
            "errors": [f"input_invalid:{error}"],
        }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

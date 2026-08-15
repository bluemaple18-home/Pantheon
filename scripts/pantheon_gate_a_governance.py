#!/usr/bin/env python3
"""在 Gate A thread dispatch 前驗證 schema 與 mutation authority。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


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


def _json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return sha256(encoded).hexdigest()


def _repo_path(repo_root: Path, value: object, field: str) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None, f"{field}_outside_repo"
    root = repo_root.resolve()
    candidate = (root / value).resolve(strict=False)
    if not candidate.is_relative_to(root):
        return None, f"{field}_outside_repo"
    return candidate, None


def _argument(argv: list[object], flag: str) -> object | None:
    try:
        index = argv.index(flag)
    except ValueError:
        return None
    return argv[index + 1] if index + 1 < len(argv) else None


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
    previous_receipt: dict[str, object] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    errors = [f"missing_field:{field}" for field in REQUIRED_FIELDS if field not in authorization]
    tuple_digest = immutable_tuple_digest(authorization)
    authorization_state = "UNCONSUMED"
    apply_calls = 0

    if authorization.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_unsupported")
    if authorization.get("authorization_status") != "AUTHORIZED":
        errors.append("authorization_status_not_authorized")
    if authorization.get("authorization_revoked") is not False:
        errors.append("authorization_revoked")
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
                actual_digest = _json_digest(argv)
                if actual_digest != authorization.get("exact_apply_argv_digest"):
                    errors.append("exact_apply_argv_digest_mismatch")
                if artifact.get("canonical_argv_sha256") != actual_digest:
                    errors.append("exact_apply_argv_artifact_digest_mismatch")
                if len(argv) < 4 or argv[3] != "apply":
                    errors.append("exact_apply_argv_not_apply")
                if _argument(argv, "--source-sha") != authorization.get("source_sha"):
                    errors.append("source_sha_binding_mismatch")
                if _argument(argv, "--expected-plan-digest") != authorization.get("plan_digest"):
                    errors.append("plan_digest_binding_mismatch")
                if artifact.get("expected_plan_digest") != authorization.get("plan_digest"):
                    errors.append("plan_artifact_digest_mismatch")
                if artifact.get("execution_status") != "not_executed":
                    errors.append("exact_apply_argv_already_executed")
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("exact_apply_argv_artifact_invalid")

    if previous_receipt is not None:
        previous_calls = previous_receipt.get("apply_calls")
        if type(previous_calls) is not int or previous_calls < 0:
            errors.append("previous_apply_calls_invalid")
        else:
            apply_calls = previous_calls
            if apply_calls > 0:
                authorization_state = "CONSUMED"
                errors.append("authorization_consumed")
        if previous_receipt.get("authorization_id") != authorization.get("authorization_id"):
            authorization_state = "REAUTHORIZATION_REQUIRED"
            errors.append("authorization_id_drift")
        if previous_receipt.get("immutable_tuple_digest") != tuple_digest:
            authorization_state = "REAUTHORIZATION_REQUIRED"
            errors.append("immutable_tuple_drift")
        elif apply_calls == 0 and authorization_state == "UNCONSUMED":
            authorization_state = "UNCONSUMED_RETRY"

    errors = list(dict.fromkeys(errors))
    status = "READY" if not errors else "BLOCKED_BEFORE_MUTATION"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "authorization_id": authorization.get("authorization_id"),
        "authorization_state": authorization_state,
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
    parser.add_argument("--previous-receipt", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        authorization = _load_json(args.authorization)
        previous = _load_json(args.previous_receipt) if args.previous_receipt else None
        receipt = validate_authorization(
            authorization,
            args.repo_root,
            previous_receipt=previous,
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

#!/usr/bin/env python3
"""唯讀檢查 current runtime identity 與 new lane provider freshness。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--plist", type=Path, required=True)
    parser.add_argument("--run-state", type=Path, required=True)
    parser.add_argument("--writer-operation", type=Path, required=True)
    parser.add_argument("--attempt", type=Path, required=True)
    parser.add_argument("--inbox", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    plist = plistlib.loads(args.plist.read_bytes())
    environment = plist.get("EnvironmentVariables", {})
    if not isinstance(environment, dict):
        raise ValueError("plist EnvironmentVariables is invalid")
    state = load_json(args.run_state)
    writer = load_json(args.writer_operation)
    attempt = load_json(args.attempt)
    inbox = load_json(args.inbox)
    archive = load_json(args.archive)

    installed_matches_current = (
        environment.get("PANTHEON_RUNTIME_ACTOR_HEAD") == manifest.get("actor_head")
        and environment.get("PANTHEON_RUNTIME_MANIFEST_DIGEST")
        == manifest.get("manifest_digest")
        and environment.get("PANTHEON_RUNTIME_GENERATION") == manifest.get("generation")
    )
    job_id = state.get("last_job_id")
    request_sha = archive.get("request_sha256")
    stale_succeeded_provider_residue = (
        state.get("status") == "active"
        and writer.get("status") == "pending"
        and attempt.get("attempt_status") == "succeeded"
        and attempt.get("job_id") == job_id
        and inbox.get("job_id") == job_id
        and archive.get("job_id") == job_id
        and attempt.get("request_sha256") == request_sha
        and inbox.get("request_sha256") == request_sha
        and not args.candidate.exists()
        and not args.review.exists()
    )
    findings: list[str] = []
    if not installed_matches_current:
        findings.append("INSTALLED_SERVICE_IDENTITY_MISMATCH")
    if stale_succeeded_provider_residue:
        findings.append("STALE_SUCCEEDED_PROVIDER_RESIDUE")

    receipt = {
        "schema_version": 1,
        "operation": "read_only_plan_only_preflight",
        "status": "PASS" if not findings else "BLOCKED",
        "findings": findings,
        "checks": {
            "installed_service_identity_matches_current_manifest": installed_matches_current,
            "stale_succeeded_provider_residue_absent": not stale_succeeded_provider_residue,
        },
        "current_identity": {
            "actor_head": manifest.get("actor_head"),
            "manifest_digest": manifest.get("manifest_digest"),
            "generation": manifest.get("generation"),
        },
        "installed_identity": {
            "actor_head": environment.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
            "manifest_digest": environment.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
            "generation": environment.get("PANTHEON_RUNTIME_GENERATION"),
        },
        "run_identity": {
            "run_id": state.get("run_id"),
            "job_id": job_id,
            "run_status": state.get("status"),
            "writer_operation_status": writer.get("status"),
            "production_attempt_status": attempt.get("attempt_status"),
            "candidate_exists": args.candidate.exists(),
            "review_exists": args.review.exists(),
        },
        "digests": {
            "manifest_sha256": sha256(args.manifest),
            "plist_sha256": sha256(args.plist),
            "run_state_sha256": sha256(args.run_state),
            "writer_operation_sha256": sha256(args.writer_operation),
            "attempt_sha256": sha256(args.attempt),
            "inbox_sha256": sha256(args.inbox),
            "archive_sha256": sha256(args.archive),
        },
        "mutations": {
            "production": 0,
            "provider_calls": 0,
            "reviewer_calls": 0,
            "publisher_calls": 0,
            "git_writes": 0,
        },
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

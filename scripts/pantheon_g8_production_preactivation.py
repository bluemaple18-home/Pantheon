#!/usr/bin/env python3
"""G8 production preactivation reconciliation without production mutation."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_manifest as runtime_manifest


SCHEMA_VERSION = 1
READY_STATUS = "READY_FOR_PRODUCTION_AUTHORIZATION"
BLOCKED_STATUS = "BLOCKED"
AUTHORITY_READY = "PLANNED_FAST_FORWARD"
RUNTIME_READY = "OLD_LIVE_TO_NEW_STAGE_READY"
SELECTOR_READY = "CURRENT_EXACT_SELECTOR_READY"
MUTATION_DETECTED = "MUTATION_DETECTED"
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SERVICE_LABELS = runtime_manifest.SERVICE_LABELS
IDENTITY_FIELDS = (
    "identity",
    "manifest_digest",
    "runtime_identity_digest",
    "runtime_digest",
    "config_version",
    "generation",
    "actor_root",
    "queue_root",
    "publisher_state_root",
    "log_root",
    "actor_head",
    "python_executable",
    "uv_executable",
)


class ReconciliationBlocked(RuntimeError):
    def __init__(self, code: str, reason: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.details = details or {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReconciliationBlocked("INVALID_JSON", f"{path} is unreadable") from error
    if not isinstance(payload, dict):
        raise ReconciliationBlocked("INVALID_JSON", f"{path} must contain a JSON object")
    return payload


def _read_manifest_identity(path: Path, expected_digest: str) -> dict[str, Any]:
    manifest = _read_json(path)
    if manifest.get("manifest_digest") != expected_digest:
        raise ReconciliationBlocked("MANIFEST_DIGEST_MISMATCH", "runtime manifest digest mismatch")
    return manifest


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _require_sha1(value: str, field: str) -> str:
    if SHA1_PATTERN.fullmatch(value) is None:
        raise ReconciliationBlocked("INVALID_INPUT", f"{field} must be an exact git sha")
    return value


def _git_head(repo: Path) -> str:
    result = _run_git(repo, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise ReconciliationBlocked("GIT_UNAVAILABLE", "repo HEAD is unavailable", {"stderr": result.stderr.strip()})
    return _require_sha1(result.stdout.strip(), "HEAD")


def _git_common_dir(repo: Path) -> Path:
    result = _run_git(repo, "rev-parse", "--git-common-dir")
    if result.returncode != 0:
        raise ReconciliationBlocked("GIT_UNAVAILABLE", "git common dir is unavailable", {"stderr": result.stderr.strip()})
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (repo / path)


def _path_digest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "digest": None, "files": 0}
    if path.is_file():
        return {
            "exists": True,
            "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            "files": 1,
        }
    digest = hashlib.sha256()
    files = 0
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = child.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
        files += 1
    return {"exists": True, "digest": digest.hexdigest(), "files": files}


def _snapshot(args: argparse.Namespace) -> dict[str, Any]:
    git_common = _git_common_dir(args.repo_root)
    return {
        "queue_root": _path_digest(args.queue_root),
        "state_root": _path_digest(args.state_root),
        "transaction_root": _path_digest(args.transaction_root),
        "publisher_lock": _path_digest(args.state_root / "publisher.lock"),
        "git_refs": _path_digest(git_common / "refs"),
        "git_packed_refs": _path_digest(git_common / "packed-refs"),
        "live_root": _path_digest(args.live_root),
        "staged_root": _path_digest(args.staged_root),
        "manifest": _path_digest(args.manifest),
    }


def _changed_snapshot(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [name for name, before_value in before.items() if after.get(name) != before_value]


def _matches_allowlist(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def evaluate_authority(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    required = _require_sha1(args.required_source, "required_source")
    origin_main = _require_sha1(args.origin_main, "origin_main")
    head = _git_head(args.repo_root)
    if head != required:
        raise ReconciliationBlocked(
            "LOCAL_HEAD_MISMATCH",
            "local HEAD is not the required source",
            {"head": head, "required_source": required},
        )
    ancestor = _run_git(args.repo_root, "merge-base", "--is-ancestor", required, origin_main)
    if ancestor.returncode != 0:
        raise ReconciliationBlocked(
            "REMOTE_DIVERGED",
            "origin main is not a descendant of the required source",
            {"required_source": required, "origin_main": origin_main},
        )
    diff = _run_git(args.repo_root, "diff", "--name-only", f"{required}..{origin_main}")
    if diff.returncode != 0:
        raise ReconciliationBlocked("GIT_DIFF_FAILED", "source authority diff is unavailable", {"stderr": diff.stderr.strip()})
    changed_paths = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    forbidden = [path for path in changed_paths if not _matches_allowlist(path, args.allow_source_drift)]
    if forbidden:
        raise ReconciliationBlocked(
            "SOURCE_DRIFT",
            "origin main contains non-allowlisted source drift",
            {"changed_paths": changed_paths, "forbidden_paths": forbidden},
        )
    actor_head = _git_head(args.actor_root)
    manifest_actor_head = str(manifest.get("actor_head") or "")
    if actor_head != origin_main or manifest_actor_head != origin_main:
        raise ReconciliationBlocked(
            "ACTOR_MANIFEST_AUTHORITY_MISMATCH",
            "actor checkout and runtime manifest must both bind to origin main",
            {
                "actor_head": actor_head,
                "manifest_actor_head": manifest_actor_head,
                "origin_main": origin_main,
            },
        )
    return {
        "status": AUTHORITY_READY,
        "required_source": required,
        "origin_main": origin_main,
        "local_head": head,
        "actor_head": actor_head,
        "allowlisted_paths": changed_paths,
    }


def _load_receipts(root: Path) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for label in SERVICE_LABELS:
        path = root / f"{label}.json"
        receipt = _read_json(path)
        if receipt.get("label") != label or receipt.get("service_label") != label:
            raise ReconciliationBlocked(
                "RUNTIME_LABEL_MISMATCH",
                "runtime receipt label mismatch",
                {"path": str(path), "label": label},
            )
        receipts.append(receipt)
    return receipts


def _identity(receipt: dict[str, Any]) -> dict[str, Any]:
    return {field: receipt.get(field) for field in IDENTITY_FIELDS if field in receipt}


def _coherent_identity(receipts: list[dict[str, Any]], code: str) -> dict[str, Any]:
    identities = [_identity(receipt) for receipt in receipts]
    if not identities:
        raise ReconciliationBlocked(code, "runtime receipts are incomplete")
    first = identities[0]
    if any(identity != first for identity in identities[1:]):
        raise ReconciliationBlocked(code, "runtime receipts are mixed", {"identities": identities})
    missing = [field for field in ("identity", "manifest_digest", "runtime_identity_digest", "runtime_digest", "generation", "actor_head") if not first.get(field)]
    if missing:
        raise ReconciliationBlocked(code, "runtime identity is incomplete", {"missing": missing})
    return first


def evaluate_runtime(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    live_receipts = _load_receipts(args.live_root)
    staged_receipts = _load_receipts(args.staged_root)
    live_identity = _coherent_identity(live_receipts, "LIVE_RUNTIME_MIXED")
    runtime_manifest.validate_receipts(manifest, staged_receipts)
    staged_identity = _coherent_identity(staged_receipts, "STAGED_RUNTIME_MIXED")
    if staged_identity["actor_head"] != args.origin_main:
        raise ReconciliationBlocked(
            "STAGED_AUTHORITY_MISMATCH",
            "staged runtime does not bind to origin main",
            {"staged_actor_head": staged_identity["actor_head"], "origin_main": args.origin_main},
        )
    if live_identity == staged_identity:
        raise ReconciliationBlocked(
            "NO_PACTIVE_TRANSITION",
            "live and staged runtime identities are identical; expected old-live to new-stage transition",
        )
    exact_receipt = args.staged_root / "publisher-exact-run-id"
    staged_exact_run = exact_receipt.read_text(encoding="utf-8").strip() if exact_receipt.is_file() else ""
    if staged_exact_run != args.exact_run_id:
        raise ReconciliationBlocked(
            "STAGED_SELECTOR_MISMATCH",
            "staged publisher exact run id must match the requested selector",
            {"staged_exact_run_id": staged_exact_run, "exact_run_id": args.exact_run_id},
        )
    return {
        "status": RUNTIME_READY,
        "live_identity": live_identity,
        "staged_identity": staged_identity,
        "staged_exact_run_id": staged_exact_run,
    }


def _copy_snapshot_root(source: Path, target: Path) -> None:
    if source.exists():
        shutil.copytree(source, target)
    else:
        target.mkdir(parents=True)


def evaluate_selector(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pantheon-g8-selector-") as sandbox_name:
        sandbox = Path(sandbox_name)
        sandbox_queue = sandbox / "queue"
        sandbox_state = sandbox / "state"
        _copy_snapshot_root(args.queue_root, sandbox_queue)
        _copy_snapshot_root(args.state_root, sandbox_state)
        try:
            ready = publisher.collect_ready_runs(
                sandbox_queue,
                sandbox_state,
                limit=max(args.selector_limit, 2),
                repo_root=args.repo_root,
                exact_run_ids=[args.exact_run_id],
            )
        except publisher.PublishBlocked as error:
            raise ReconciliationBlocked(
                "SELECTOR_CARDINALITY",
                "exact selector must resolve to exactly one ready run",
                {
                    "exact_run_id": args.exact_run_id,
                    "collector_error": str(error),
                    "selector_isolation": "queue_state_snapshot",
                },
            ) from error
    if len(ready) != 1:
        raise ReconciliationBlocked(
            "SELECTOR_CARDINALITY",
            "exact selector must resolve to exactly one ready run",
            {
                "exact_run_id": args.exact_run_id,
                "count": len(ready),
                "selector_isolation": "queue_state_snapshot",
            },
        )
    state, candidate, review = ready[0]
    run_id = str(state.get("run_id") or "")
    candidate_run_id = str(candidate.get("run_id") or "")
    review_run_id = str(review.get("run_id") or "")
    if {run_id, candidate_run_id, review_run_id} != {args.exact_run_id}:
        raise ReconciliationBlocked(
            "SELECTOR_IDENTITY_DRIFT",
            "selector state, candidate, and review must bind to the exact run",
            {
                "state_run_id": run_id,
                "candidate_run_id": candidate_run_id,
                "review_run_id": review_run_id,
                "exact_run_id": args.exact_run_id,
            },
        )
    if state.get("status") != "complete" or candidate.get("mode") != "create":
        raise ReconciliationBlocked(
            "SELECTOR_NOT_READY",
            "selector run is not complete create mode",
            {"run_id": run_id, "state_status": state.get("status"), "candidate_mode": candidate.get("mode")},
        )
    return {
        "status": SELECTOR_READY,
        "exact_run_id": args.exact_run_id,
        "state_path": str(args.queue_root / "runs" / f"{args.exact_run_id}.json"),
        "selector_isolation": "queue_state_snapshot",
        "candidate_article_count": len(candidate.get("articles", [])),
    }


def reconcile(args: argparse.Namespace) -> dict[str, Any]:
    before = _snapshot(args)
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": READY_STATUS,
        "production_mutation": False,
        "card_id": args.card_id,
    }
    try:
        manifest_identity = _read_manifest_identity(args.manifest, args.expected_manifest_digest)
        result["authority"] = evaluate_authority(args, manifest_identity)
        manifest = runtime_manifest.load_manifest(args.manifest, args.expected_manifest_digest)
        result["runtime_transition"] = evaluate_runtime(args, manifest)
        result["selector"] = evaluate_selector(args)
    except (runtime_manifest.RuntimeManifestError, publisher.PublishBlocked, ReconciliationBlocked) as error:
        code = error.code if isinstance(error, ReconciliationBlocked) else type(error).__name__
        details = error.details if isinstance(error, ReconciliationBlocked) else {}
        result.update(
            {
                "status": BLOCKED_STATUS,
                "blocked_code": code,
                "reasons": [str(error)],
                "details": details,
            }
        )
    after = _snapshot(args)
    changed = _changed_snapshot(before, after)
    result["mutation_tripwire"] = {
        "status": "PASS" if not changed else MUTATION_DETECTED,
        "changed": changed,
        "before": before,
        "after": after,
    }
    if changed:
        result.update(
            {
                "status": BLOCKED_STATUS,
                "blocked_code": MUTATION_DETECTED,
                "production_mutation": True,
                "reasons": [f"protected roots changed: {', '.join(changed)}"],
            }
        )
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card-id", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--actor-root", type=Path, required=True)
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--transaction-root", type=Path, required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    parser.add_argument("--staged-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-digest", required=True)
    parser.add_argument("--required-source", required=True)
    parser.add_argument("--origin-main", required=True)
    parser.add_argument("--exact-run-id", required=True)
    parser.add_argument("--evidence-path", type=Path, required=True)
    parser.add_argument("--allow-source-drift", action="append", default=[])
    parser.add_argument("--selector-limit", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.allow_source_drift and args.required_source != args.origin_main:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": BLOCKED_STATUS,
            "blocked_code": "ALLOWLIST_REQUIRED",
            "reasons": ["planned fast-forward requires at least one explicit allowlist pattern"],
        }
    else:
        payload = reconcile(args)
    args.evidence_path.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("status") == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

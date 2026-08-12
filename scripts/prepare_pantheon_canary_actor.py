#!/usr/bin/env python3
"""準備單次 Pantheon Canary publisher actor 的 fail-closed 入口。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from scripts.agy_content_publisher import runtime_manifest_digest
from scripts.pantheon_content_runtime_manifest import build_manifest, write_manifest


SCHEMA_VERSION = 1
REGRESSION_ID = "REG-PANTHEON-CANARY-ACTOR-PROVISIONING-001"
EXACT_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CanaryActorError(RuntimeError):
    """Canary actor 準備契約未通過。"""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CanaryActorError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    ).returncode == 0


def _canonical_existing_dir(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise CanaryActorError(f"{label} must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CanaryActorError(f"{label} is missing") from error
    if path != resolved or path.is_symlink() or not resolved.is_dir():
        raise CanaryActorError(f"{label} must be a canonical directory")
    return resolved


def _canonical_target(path: Path, sandbox_root: Path, label: str) -> Path:
    if not path.is_absolute():
        raise CanaryActorError(f"{label} must be absolute")
    try:
        parent = path.parent.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CanaryActorError(f"{label} parent is missing") from error
    target = parent / path.name
    if target.exists():
        try:
            resolved = target.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise CanaryActorError(f"{label} is invalid") from error
        if resolved != target or target.is_symlink():
            raise CanaryActorError(f"{label} must not be a symlink alias")
    if target != sandbox_root and not target.is_relative_to(sandbox_root):
        raise CanaryActorError(f"{label} must stay inside sandbox root")
    return target


def _empty_or_missing_directory(path: Path, label: str) -> None:
    if not path.exists():
        return
    if not path.is_dir() or path.is_symlink():
        raise CanaryActorError(f"{label} must be a directory")
    if any(path.iterdir()):
        raise CanaryActorError(f"{label} must be empty")


def _empty_or_prepared_queue(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_dir() or path.is_symlink():
        raise CanaryActorError("queue root must be a directory")
    entries = list(path.iterdir())
    if not entries:
        return
    if len(entries) == 1 and entries[0].name == "runs" and entries[0].is_dir():
        if any(entries[0].iterdir()):
            raise CanaryActorError("queue root must be empty")
        return
    raise CanaryActorError("queue root must be empty")


def _python_executable(path: Path, sandbox_root: Path) -> Path:
    if not path.is_absolute():
        raise CanaryActorError("python executable must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CanaryActorError("python executable is missing") from error
    if path != resolved or path.is_symlink() or not resolved.is_file():
        raise CanaryActorError("python executable must use its canonical realpath")
    if not os.access(resolved, os.X_OK):
        raise CanaryActorError("python executable is not executable")
    if resolved.is_relative_to(sandbox_root):
        return resolved
    # A shared read-only Python outside the sandbox is allowed, but it is pinned
    # into the manifest so later provisioning can detect drift.
    return resolved


def _worktree_paths(repo_root: Path) -> set[Path]:
    output = _git(repo_root, "worktree", "list", "--porcelain")
    paths: set[Path] = set()
    for line in output.splitlines():
        if line.startswith("worktree "):
            paths.add(Path(line.removeprefix("worktree ")).resolve())
    return paths


def _validate_lineage(repo_root: Path, actor_sha: str, remote_ref: str) -> str:
    if SHA1_PATTERN.fullmatch(actor_sha) is None:
        raise CanaryActorError("actor source SHA must be a full 40-character SHA")
    _git(repo_root, "cat-file", "-e", f"{actor_sha}^{{commit}}")
    remote_sha = _git(repo_root, "rev-parse", remote_ref)
    if SHA1_PATTERN.fullmatch(remote_sha) is None:
        raise CanaryActorError("remote ref did not resolve to a full SHA")
    if not _git_ok(repo_root, "merge-base", "--is-ancestor", remote_sha, actor_sha):
        raise CanaryActorError("actor source is not a descendant of remote ref")
    return remote_sha


def _state_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _publisher_command(
    *,
    python: Path,
    actor_root: Path,
    queue_root: Path,
    state_root: Path,
    actor_sha: str,
    runtime_digest: str,
    exact_run_id: str,
) -> list[str]:
    return [
        str(python),
        "-m",
        "scripts.agy_content_publisher",
        "--repo-root",
        str(actor_root),
        "--queue-root",
        str(queue_root),
        "--state-root",
        str(state_root),
        "--max-runs",
        "1",
        "--exact-run-id",
        exact_run_id,
        "--include-rewrites",
        "--push",
        "--deployment-preflight",
        "--expected-repo-root",
        str(actor_root),
        "--expected-queue-root",
        str(queue_root),
        "--expected-state-root",
        str(state_root),
        "--expected-runtime-sha",
        actor_sha,
        "--expected-runtime-digest",
        runtime_digest,
        "--expected-push-mode",
        "push",
    ]


def _validate_publisher_plan(plan: dict[str, Any]) -> None:
    command = plan.get("publisher_command")
    if not isinstance(command, list) or any(type(item) is not str for item in command):
        raise CanaryActorError("publisher command is missing")
    if command.count("--exact-run-id") != 1:
        raise CanaryActorError("publisher plan must contain exactly one exact run selector")
    selector_index = command.index("--exact-run-id") + 1
    if selector_index >= len(command) or command[selector_index] != plan.get("exact_run_id"):
        raise CanaryActorError("publisher plan exact run selector drift")
    if command.count("--max-runs") != 1:
        raise CanaryActorError("publisher plan must contain exactly one max-runs")
    max_index = command.index("--max-runs") + 1
    if max_index >= len(command) or command[max_index] != "1":
        raise CanaryActorError("publisher plan must be bounded to one run")
    required_flags = {
        "--deployment-preflight",
        "--expected-runtime-sha",
        "--expected-runtime-digest",
        "--expected-repo-root",
        "--expected-queue-root",
        "--expected-state-root",
    }
    if not required_flags.issubset(set(command)):
        raise CanaryActorError("publisher plan deployment contract is incomplete")
    digest_index = command.index("--expected-runtime-digest") + 1
    if digest_index >= len(command) or command[digest_index] != plan.get("runtime_digest"):
        raise CanaryActorError("publisher plan runtime digest drift")
    sha_index = command.index("--expected-runtime-sha") + 1
    if sha_index >= len(command) or command[sha_index] != plan.get("actor_sha"):
        raise CanaryActorError("publisher plan actor SHA drift")


def build_plan(
    *,
    repo_root: Path,
    sandbox_root: Path,
    actor_root: Path,
    queue_root: Path,
    publisher_state_root: Path,
    log_root: Path,
    manifest_path: Path,
    python: Path,
    actor_sha: str,
    remote_ref: str,
    exact_run_id: str,
) -> dict[str, Any]:
    repo_root = _canonical_existing_dir(repo_root, "repo root")
    sandbox_root = _canonical_existing_dir(sandbox_root, "sandbox root")
    if actor_root.exists() and actor_root.resolve(strict=True) == repo_root:
        raise CanaryActorError("actor root must not be the current checkout")
    actor_root = _canonical_target(actor_root, sandbox_root, "actor root")
    queue_root = _canonical_target(queue_root, sandbox_root, "queue root")
    publisher_state_root = _canonical_target(
        publisher_state_root,
        sandbox_root,
        "publisher state root",
    )
    log_root = _canonical_target(log_root, sandbox_root, "log root")
    manifest_path = _canonical_target(manifest_path, sandbox_root, "manifest path")
    python = _python_executable(python, sandbox_root)
    if EXACT_RUN_ID_PATTERN.fullmatch(exact_run_id) is None:
        raise CanaryActorError("exact run id is invalid")
    if len({actor_root, queue_root, publisher_state_root, log_root}) != 4:
        raise CanaryActorError("runtime roots must be distinct")
    _empty_or_prepared_queue(queue_root)
    for label, path in (
        ("publisher state root", publisher_state_root),
        ("log root", log_root),
    ):
        _empty_or_missing_directory(path, label)
    current_root = Path(_git(repo_root, "rev-parse", "--show-toplevel")).resolve()
    if actor_root == current_root:
        raise CanaryActorError("actor root must not be the current checkout")
    registered_worktrees = _worktree_paths(repo_root)
    if actor_root.exists() and actor_root not in registered_worktrees:
        raise CanaryActorError("actor root already exists outside git worktree registry")
    if actor_root in registered_worktrees and (
        _git(actor_root, "rev-parse", "HEAD") != actor_sha
        or _git(actor_root, "status", "--porcelain") != ""
    ):
        raise CanaryActorError("actor root is an existing incompatible worktree")
    remote_sha = _validate_lineage(repo_root, actor_sha, remote_ref)
    runtime_digest = runtime_manifest_digest(repo_root)
    plan = {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "status": "ready",
        "mode": "read-only",
        "mutation_permitted": False,
        "repo_root": str(repo_root),
        "sandbox_root": str(sandbox_root),
        "actor_root": str(actor_root),
        "queue_root": str(queue_root),
        "publisher_state_root": str(publisher_state_root),
        "log_root": str(log_root),
        "runtime_manifest": str(manifest_path),
        "python_executable": str(python),
        "actor_sha": actor_sha,
        "remote_ref": remote_ref,
        "remote_sha": remote_sha,
        "runtime_digest": runtime_digest,
        "exact_run_id": exact_run_id,
        "max_runs": 1,
        "publisher_command": _publisher_command(
            python=python,
            actor_root=actor_root,
            queue_root=queue_root,
            state_root=publisher_state_root,
            actor_sha=actor_sha,
            runtime_digest=runtime_digest,
            exact_run_id=exact_run_id,
        ),
    }
    plan["plan_digest"] = _state_digest(plan)
    _validate_publisher_plan(plan)
    return plan


def prepare(plan: dict[str, Any]) -> dict[str, Any]:
    _validate_publisher_plan(plan)
    repo_root = Path(str(plan["repo_root"]))
    actor_root = Path(str(plan["actor_root"]))
    queue_root = Path(str(plan["queue_root"]))
    state_root = Path(str(plan["publisher_state_root"]))
    log_root = Path(str(plan["log_root"]))
    manifest_path = Path(str(plan["runtime_manifest"]))
    actor_sha = str(plan["actor_sha"])
    python = Path(str(plan["python_executable"]))
    if actor_root.exists():
        if _git(actor_root, "rev-parse", "HEAD") != actor_sha:
            raise CanaryActorError("actor root HEAD drift")
        if _git(actor_root, "status", "--porcelain") != "":
            raise CanaryActorError("actor root is dirty")
    else:
        _git(repo_root, "worktree", "add", "--detach", str(actor_root), actor_sha)
    for path, label in (
        (queue_root / "runs", "queue runs root"),
        (state_root, "publisher state root"),
        (log_root, "log root"),
    ):
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise CanaryActorError(f"{label} must not be a symlink")
    if any(state_root.iterdir()):
        raise CanaryActorError("publisher state root must stay empty")
    manifest = build_manifest(
        actor_root=actor_root,
        queue_root=queue_root,
        publisher_state_root=state_root,
        log_root=log_root,
        identity=f"canary-actor:{actor_sha}:{plan['exact_run_id']}",
        runtime_digest=str(plan["runtime_digest"]),
        config_version="formal-runtime-v2-canary",
        generation=f"canary-{actor_sha[:16]}",
        actor_head=actor_sha,
        python_executable=python,
    )
    write_manifest(manifest_path, manifest)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "prepared",
        "actor_root": str(actor_root),
        "actor_head": _git(actor_root, "rev-parse", "HEAD"),
        "actor_clean": _git(actor_root, "status", "--porcelain") == "",
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "publisher_plan": plan,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "preflight", "prepare"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--repo-root", type=Path, required=True)
        sub.add_argument("--sandbox-root", type=Path, required=True)
        sub.add_argument("--actor-root", type=Path, required=True)
        sub.add_argument("--queue-root", type=Path, required=True)
        sub.add_argument("--publisher-state-root", type=Path, required=True)
        sub.add_argument("--log-root", type=Path, required=True)
        sub.add_argument("--runtime-manifest", type=Path, required=True)
        sub.add_argument("--python", type=Path, required=True)
        sub.add_argument("--actor-sha", required=True)
        sub.add_argument("--remote-ref", default="origin/main")
        sub.add_argument("--exact-run-id", required=True)
        sub.add_argument("--receipt", type=Path)
    return parser.parse_args()


def _emit(payload: dict[str, Any], receipt: Path | None) -> None:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if receipt is not None:
        if not receipt.is_absolute():
            raise CanaryActorError("receipt path must be absolute")
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(body, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main() -> int:
    args = parse_args()
    try:
        plan = build_plan(
            repo_root=args.repo_root,
            sandbox_root=args.sandbox_root,
            actor_root=args.actor_root,
            queue_root=args.queue_root,
            publisher_state_root=args.publisher_state_root,
            log_root=args.log_root,
            manifest_path=args.runtime_manifest,
            python=args.python,
            actor_sha=args.actor_sha,
            remote_ref=args.remote_ref,
            exact_run_id=args.exact_run_id,
        )
        if args.command in {"plan", "preflight"}:
            _emit(plan, args.receipt)
            return 0
        result = prepare(plan)
        _emit(result, args.receipt)
        return 0
    except CanaryActorError as error:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "NO-GO",
            "error": str(error),
        }
        if getattr(args, "receipt", None) is not None:
            _emit(payload, args.receipt)
        else:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""以單一 fail-closed 入口 preflight 或 restore Pantheon publisher actor。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

from scripts.agy_content_publisher import runtime_manifest_digest


SCHEMA_VERSION = 1
REGRESSION_ID = "REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001"
DEPENDENCY_PATHS = ("pyproject.toml", "uv.lock")


class ActorRecoveryError(RuntimeError):
    """Actor recovery contract 未通過。"""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ActorRecoveryError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def dependency_digest(repo: Path) -> str:
    digest = hashlib.sha256()
    found = False
    for relative in DEPENDENCY_PATHS:
        path = repo / relative
        if not path.is_file():
            continue
        found = True
        body = path.read_bytes()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(body).digest())
    if not found:
        raise ActorRecoveryError("dependency manifest is missing")
    return digest.hexdigest()


def _canonical_target(target: Path, allow_root: Path) -> tuple[Path, Path]:
    if not target.is_absolute() or not allow_root.is_absolute():
        raise ActorRecoveryError("target and allowlist root must be absolute")
    root = allow_root.resolve(strict=True)
    parent = target.parent.resolve(strict=True)
    canonical = parent / target.name
    if canonical.parent != root or canonical == root:
        raise ActorRecoveryError("target is outside the actor allowlist")
    if target.exists() and (target.is_symlink() or target.resolve(strict=True) != canonical):
        raise ActorRecoveryError("target canonical realpath mismatch")
    if os.stat(parent).st_uid != os.getuid():
        raise ActorRecoveryError("target parent owner mismatch")
    return canonical, root


def _validate_source(
    source_repo: Path,
    source_sha: str,
    expected_origin: str,
    expected_runtime_digest: str,
    expected_dependency_digest: str,
) -> dict[str, str]:
    source = source_repo.resolve(strict=True)
    if os.stat(source).st_uid != os.getuid():
        raise ActorRecoveryError("source owner mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ActorRecoveryError("source SHA must be a full lowercase commit")
    if _git(source, "status", "--porcelain"):
        raise ActorRecoveryError("source worktree must be clean")
    if _git(source, "rev-parse", "HEAD") != source_sha:
        raise ActorRecoveryError("source SHA mismatch")
    if _git(source, "remote", "get-url", "origin") != expected_origin:
        raise ActorRecoveryError("source origin mismatch")
    actual_runtime = runtime_manifest_digest(source)
    if actual_runtime != expected_runtime_digest:
        raise ActorRecoveryError("runtime digest mismatch")
    actual_dependencies = dependency_digest(source)
    if actual_dependencies != expected_dependency_digest:
        raise ActorRecoveryError("dependency digest mismatch")
    return {
        "source_repo": str(source),
        "source_sha": source_sha,
        "origin": expected_origin,
        "runtime_digest": actual_runtime,
        "dependency_digest": actual_dependencies,
    }


def recover_actor(
    *,
    source_repo: Path,
    source_sha: str,
    target: Path,
    allow_root: Path,
    expected_origin: str,
    expected_runtime_digest: str,
    expected_dependency_digest: str,
    mode: str,
) -> dict[str, Any]:
    if mode not in {"preflight", "restore"}:
        raise ActorRecoveryError("mode must be preflight or restore")
    canonical_target, canonical_allow_root = _canonical_target(target, allow_root)
    source = _validate_source(
        source_repo,
        source_sha,
        expected_origin,
        expected_runtime_digest,
        expected_dependency_digest,
    )
    if canonical_target.exists():
        if os.stat(canonical_target).st_uid != os.getuid():
            raise ActorRecoveryError("target owner mismatch")
        if _git(canonical_target, "status", "--porcelain"):
            raise ActorRecoveryError("target worktree must be clean")
    target_current_sha: str | None = None
    if canonical_target.exists():
        target_current_sha = _git(canonical_target, "rev-parse", "HEAD")
        if _git(canonical_target, "remote", "get-url", "origin") != expected_origin:
            raise ActorRecoveryError("target origin mismatch")
        if target_current_sha != source_sha:
            merge_base = _git(source_repo, "merge-base", target_current_sha, source_sha)
            if merge_base != target_current_sha:
                raise ActorRecoveryError("target is not a fast-forward ancestor")
        else:
            if runtime_manifest_digest(canonical_target) != expected_runtime_digest:
                raise ActorRecoveryError("target runtime digest mismatch")
            if dependency_digest(canonical_target) != expected_dependency_digest:
                raise ActorRecoveryError("target dependency digest mismatch")
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "mode": mode,
        "target": str(canonical_target),
        "allow_root": str(canonical_allow_root),
        "owner_uid": os.getuid(),
        **source,
    }
    if mode == "preflight":
        return {
            "status": "READY_TO_RESTORE",
            "mutation_permitted": False,
            "target_current_sha": target_current_sha,
            **receipt,
        }

    stage = Path(tempfile.mkdtemp(prefix=f".{canonical_target.name}.restore-", dir=canonical_allow_root))
    backup = canonical_allow_root / f".{canonical_target.name}.rollback"
    if backup.exists():
        shutil.rmtree(stage)
        raise ActorRecoveryError("rollback target already exists")
    installed = False
    try:
        shutil.rmtree(stage)
        subprocess.run(
            ["git", "clone", "-q", "--no-checkout", str(source_repo.resolve()), str(stage)],
            check=True,
        )
        _git(stage, "checkout", "-q", "--detach", source_sha)
        _git(stage, "remote", "set-url", "origin", expected_origin)
        _validate_source(
            stage,
            source_sha,
            expected_origin,
            expected_runtime_digest,
            expected_dependency_digest,
        )
        if canonical_target.exists():
            os.replace(canonical_target, backup)
        os.replace(stage, canonical_target)
        installed = True
        if backup.exists():
            shutil.rmtree(backup)
    except Exception as error:
        if installed and canonical_target.exists():
            shutil.rmtree(canonical_target)
        if backup.exists():
            os.replace(backup, canonical_target)
        if isinstance(error, ActorRecoveryError):
            raise
        raise ActorRecoveryError(f"restore failed and was rolled back: {error}") from error
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"status": "RESTORED", "mutation_permitted": True, **receipt}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--allow-root", type=Path, required=True)
    parser.add_argument("--expected-origin", required=True)
    parser.add_argument("--expected-runtime-digest", required=True)
    parser.add_argument("--expected-dependency-digest", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", dest="mode", action="store_const", const="preflight")
    mode.add_argument("--restore", dest="mode", action="store_const", const="restore")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = recover_actor(
            source_repo=args.source_repo,
            source_sha=args.source_sha,
            target=args.target,
            allow_root=args.allow_root,
            expected_origin=args.expected_origin,
            expected_runtime_digest=args.expected_runtime_digest,
            expected_dependency_digest=args.expected_dependency_digest,
            mode=args.mode,
        )
    except ActorRecoveryError as error:
        print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
from scripts.pantheon_content_runtime_manifest import build_manifest, write_manifest


SCHEMA_VERSION = 1
REGRESSION_ID = "REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001"
DEPENDENCY_PATHS = ("pyproject.toml", "uv.lock")
PYTHON_REQUIRED_MODULES = (
    "scripts.agy_content_publisher",
    "scripts.agy_gemini_runner",
    "scripts.pantheon_content_capacity_guard",
)
NODE_CLI_RELATIVE = ".bin/agy-1.1.3"


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


def dependency_root_digest(root: Path, required_relative: str) -> str:
    canonical = root.resolve(strict=True)
    if not canonical.is_dir() or root != canonical or root.is_symlink():
        raise ActorRecoveryError("dependency root must use its canonical realpath")
    if os.stat(canonical).st_uid != os.getuid():
        raise ActorRecoveryError("dependency root owner mismatch")
    required = canonical / required_relative
    if not required.is_file() or not os.access(required, os.X_OK):
        raise ActorRecoveryError(f"dependency entrypoint is unavailable: {required_relative}")
    payload = {
        "root": str(canonical),
        "owner_uid": os.stat(canonical).st_uid,
        "entrypoint": required_relative,
        "entrypoint_realpath": str(required.resolve(strict=True)),
        "entrypoint_sha256": hashlib.sha256(required.read_bytes()).hexdigest(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _validated_dependency_roots(
    *,
    python_root: Path,
    node_root: Path,
    expected_python_digest: str,
    expected_node_digest: str,
) -> tuple[Path, Path]:
    canonical_python = python_root.resolve(strict=True)
    canonical_node = node_root.resolve(strict=True)
    if dependency_root_digest(canonical_python, "bin/python") != expected_python_digest:
        raise ActorRecoveryError("Python dependency root digest mismatch")
    if dependency_root_digest(canonical_node, NODE_CLI_RELATIVE) != expected_node_digest:
        raise ActorRecoveryError("Node dependency root digest mismatch")
    return canonical_python, canonical_node


def _run_checked(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ActorRecoveryError(f"runtime preflight failed: {detail}")


def _provision_and_preflight(
    *,
    actor: Path,
    python_root: Path,
    node_root: Path,
    source_sha: str,
    runtime_digest: str,
    runtime_root: Path,
) -> dict[str, str]:
    with (actor / ".git/info/exclude").open("a", encoding="utf-8") as stream:
        stream.write("\n.venv\nnode_modules\n")
    (actor / ".venv").symlink_to(python_root, target_is_directory=True)
    (actor / "node_modules").symlink_to(node_root, target_is_directory=True)
    python = actor / ".venv/bin/python"
    node_cli = actor / "node_modules" / NODE_CLI_RELATIVE
    env = os.environ.copy()
    queue = runtime_root / "queue"
    state = runtime_root / "publisher-state"
    logs = runtime_root / "logs"
    home = runtime_root / "home"
    for path in (queue / "runs", state, logs, home):
        path.mkdir(parents=True, exist_ok=True)
    manifest_path = runtime_root / "runtime-manifest.json"
    manifest = build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity=f"actor-recovery:{source_sha}:{runtime_digest}",
        runtime_digest=runtime_digest,
        config_version="formal-runtime-v2",
        generation=f"actor-recovery-{source_sha[:16]}",
    )
    write_manifest(manifest_path, manifest)
    env.update(
        {
            "PANTHEON_USER_HOME_DIR": str(home),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest[
                "manifest_digest"
            ],
            "PANTHEON_PYTHON_PATH": str(python),
            "AGY_GEMINI_CLI_PATH": str(node_cli),
            "PANTHEON_GSC_COPY_ROOT": str(runtime_root / "gsc-copy"),
        }
    )
    imports = ";".join(f"import {module}" for module in PYTHON_REQUIRED_MODULES)
    _run_checked([str(python), "-c", imports], cwd=actor, env=env)
    _run_checked([str(node_cli), "--version"], cwd=actor, env=env)
    installers = {
        "publisher": "scripts/install_agy_content_publisher_launchd.sh",
        "coordinator": "scripts/install_agy_gemini_coordinator_launchd.sh",
        "capacity": "scripts/install_pantheon_content_capacity_guard_launchd.sh",
    }
    for relative in installers.values():
        _run_checked(["/bin/bash", str(actor / relative), "--preflight"], cwd=actor, env=env)
    return {name: "PASS" for name in installers}


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
    python_dependency_root: Path,
    node_dependency_root: Path,
    expected_python_dependency_digest: str,
    expected_node_dependency_digest: str,
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
    python_root, node_root = _validated_dependency_roots(
        python_root=python_dependency_root,
        node_root=node_dependency_root,
        expected_python_digest=expected_python_dependency_digest,
        expected_node_digest=expected_node_dependency_digest,
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
    stage = Path(tempfile.mkdtemp(prefix=f".{canonical_target.name}.restore-", dir=canonical_allow_root))
    runtime_root = Path(
        tempfile.mkdtemp(prefix=f".{canonical_target.name}.preflight-", dir=canonical_allow_root)
    )
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
        installer_preflights = _provision_and_preflight(
            actor=stage,
            python_root=python_root,
            node_root=node_root,
            source_sha=source_sha,
            runtime_digest=expected_runtime_digest,
            runtime_root=runtime_root,
        )
        if mode == "preflight":
            return {
                "status": "READY_TO_RESTORE",
                "mutation_permitted": False,
                "target_current_sha": target_current_sha,
                "python_dependency_digest": expected_python_dependency_digest,
                "node_dependency_digest": expected_node_dependency_digest,
                "installer_preflights": installer_preflights,
                **receipt,
            }
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
        shutil.rmtree(runtime_root, ignore_errors=True)
    return {
        "status": "RESTORED",
        "mutation_permitted": True,
        "python_dependency_digest": expected_python_dependency_digest,
        "node_dependency_digest": expected_node_dependency_digest,
        "installer_preflights": installer_preflights,
        **receipt,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--allow-root", type=Path, required=True)
    parser.add_argument("--expected-origin", required=True)
    parser.add_argument("--expected-runtime-digest", required=True)
    parser.add_argument("--expected-dependency-digest", required=True)
    parser.add_argument("--python-dependency-root", type=Path, required=True)
    parser.add_argument("--node-dependency-root", type=Path, required=True)
    parser.add_argument("--expected-python-dependency-digest", required=True)
    parser.add_argument("--expected-node-dependency-digest", required=True)
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
            python_dependency_root=args.python_dependency_root,
            node_dependency_root=args.node_dependency_root,
            expected_python_dependency_digest=args.expected_python_dependency_digest,
            expected_node_dependency_digest=args.expected_node_dependency_digest,
            mode=args.mode,
        )
    except ActorRecoveryError as error:
        print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

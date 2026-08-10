from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_actor_recovery as recovery


REGRESSION_ID = "REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _source_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "origin.git"
    source = tmp_path / "source"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    _git(source, "config", "user.email", "synthetic@example.invalid")
    _git(source, "config", "user.name", "Synthetic Test")
    for relative in publisher.TRANSACTION_RUNTIME_PATHS:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture:{relative}\n", encoding="utf-8")
    (source / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    _git(source, "add", ".")
    _git(source, "commit", "-qm", "fixture")
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "-qu", "origin", "main")
    return source, remote, _git(source, "rev-parse", "HEAD")


def test_same_recovery_entrypoint_preflights_and_restores_exact_actor(
    tmp_path: Path,
) -> None:
    source, remote, source_sha = _source_repo(tmp_path)
    allow_root = tmp_path / "actors"
    allow_root.mkdir()
    target = allow_root / "publisher"
    expected_runtime = publisher.runtime_manifest_digest(source)
    expected_dependencies = recovery.dependency_digest(source)

    plan = recovery.recover_actor(
        source_repo=source,
        source_sha=source_sha,
        target=target,
        allow_root=allow_root,
        expected_origin=str(remote),
        expected_runtime_digest=expected_runtime,
        expected_dependency_digest=expected_dependencies,
        mode="preflight",
    )
    restored = recovery.recover_actor(
        source_repo=source,
        source_sha=source_sha,
        target=target,
        allow_root=allow_root,
        expected_origin=str(remote),
        expected_runtime_digest=expected_runtime,
        expected_dependency_digest=expected_dependencies,
        mode="restore",
    )

    assert plan["status"] == "READY_TO_RESTORE"
    assert plan["regression_id"] == REGRESSION_ID
    assert restored["status"] == "RESTORED"
    assert _git(target, "rev-parse", "HEAD") == source_sha
    assert _git(target, "status", "--porcelain") == ""
    assert _git(target, "remote", "get-url", "origin") == str(remote)


def test_recovery_fails_closed_outside_allowlist_and_on_dirty_source(
    tmp_path: Path,
) -> None:
    source, remote, source_sha = _source_repo(tmp_path)
    allow_root = tmp_path / "actors"
    allow_root.mkdir()
    expected_runtime = publisher.runtime_manifest_digest(source)
    expected_dependencies = recovery.dependency_digest(source)
    (source / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(recovery.ActorRecoveryError, match="allowlist"):
        recovery.recover_actor(
            source_repo=source,
            source_sha=source_sha,
            target=tmp_path / "outside",
            allow_root=allow_root,
            expected_origin=str(remote),
            expected_runtime_digest=expected_runtime,
            expected_dependency_digest=expected_dependencies,
            mode="preflight",
        )
    with pytest.raises(recovery.ActorRecoveryError, match="clean"):
        recovery.recover_actor(
            source_repo=source,
            source_sha=source_sha,
            target=allow_root / "publisher",
            allow_root=allow_root,
            expected_origin=str(remote),
            expected_runtime_digest=expected_runtime,
            expected_dependency_digest=expected_dependencies,
            mode="preflight",
        )

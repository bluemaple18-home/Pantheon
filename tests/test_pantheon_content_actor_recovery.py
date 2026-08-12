from __future__ import annotations

import subprocess
import shutil
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


def _repair_source_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = Path(__file__).resolve().parents[1]
    remote = tmp_path / "repair-origin.git"
    source = tmp_path / "repair-source"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "push", "-q", str(remote), "HEAD:refs/heads/main"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True,
    )
    subprocess.run(["git", "clone", "-q", str(remote), str(source)], check=True)
    _git(source, "config", "user.email", "synthetic@example.invalid")
    _git(source, "config", "user.name", "Synthetic Test")
    repair_paths = [
        "ops/launchd/com.pantheon.agy-content-publisher.plist.example",
        "ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example",
        "ops/launchd/com.pantheon.agy-gemini-lane.plist.example",
        "ops/launchd/com.pantheon.content-capacity-guard.plist.example",
        "scripts/install_agy_content_publisher_launchd.sh",
        "scripts/install_agy_gemini_coordinator_launchd.sh",
        "scripts/install_pantheon_content_capacity_guard_launchd.sh",
        "scripts/pantheon_content_actor_recovery.py",
        "scripts/pantheon_content_capability_adapter.py",
        "scripts/pantheon_content_capability_probe.py",
        "scripts/pantheon_content_runtime_manifest.py",
    ]
    for relative in repair_paths:
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / relative, destination)
    _git(source, "add", *repair_paths)
    _git(source, "commit", "-qm", "repair-2 fixture")
    _git(source, "push", "-q", "origin", "main")
    with (source / ".git/info/exclude").open("a", encoding="utf-8") as stream:
        stream.write("\n.venv\nnode_modules\n")
    (source / ".venv").symlink_to((repo / ".venv").resolve(), target_is_directory=True)
    node_root = tmp_path / "node-dependencies"
    cli = node_root / ".bin" / "agy-1.1.3"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli.chmod(0o700)
    (source / "node_modules").symlink_to(node_root, target_is_directory=True)
    return source, remote, _git(source, "rev-parse", "HEAD")


def test_same_recovery_entrypoint_preflights_and_restores_exact_actor(
    tmp_path: Path,
) -> None:
    source, remote, source_sha = _repair_source_repo(tmp_path)
    allow_root = tmp_path / "actors"
    allow_root.mkdir()
    target = allow_root / "publisher"
    expected_runtime = publisher.runtime_manifest_digest(source)
    expected_dependencies = recovery.dependency_digest(source)
    python_root = (source / ".venv").resolve()
    node_root = (source / "node_modules").resolve()
    python_digest = recovery.dependency_root_digest(python_root, "bin/python")
    node_digest = recovery.dependency_root_digest(node_root, recovery.NODE_CLI_RELATIVE)

    plan = recovery.recover_actor(
        source_repo=source,
        source_sha=source_sha,
        target=target,
        allow_root=allow_root,
        expected_origin=str(remote),
        expected_runtime_digest=expected_runtime,
        expected_dependency_digest=expected_dependencies,
        python_dependency_root=python_root,
        node_dependency_root=node_root,
        expected_python_dependency_digest=python_digest,
        expected_node_dependency_digest=node_digest,
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
        python_dependency_root=python_root,
        node_dependency_root=node_root,
        expected_python_dependency_digest=python_digest,
        expected_node_dependency_digest=node_digest,
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
            python_dependency_root=Path("/missing-python"),
            node_dependency_root=Path("/missing-node"),
            expected_python_dependency_digest="missing",
            expected_node_dependency_digest="missing",
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
            python_dependency_root=Path("/missing-python"),
            node_dependency_root=Path("/missing-node"),
            expected_python_dependency_digest="missing",
            expected_node_dependency_digest="missing",
            mode="preflight",
        )


def test_empty_target_restore_provisions_runtime_before_formal_preflights(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001 Repair-2。"""
    source, remote, source_sha = _repair_source_repo(tmp_path)
    allow_root = tmp_path / "actors"
    allow_root.mkdir()
    target = allow_root / "publisher"
    python_root = (source / ".venv").resolve()
    node_root = (source / "node_modules").resolve()

    restored = recovery.recover_actor(
        source_repo=source,
        source_sha=source_sha,
        target=target,
        allow_root=allow_root,
        expected_origin=str(remote),
        expected_runtime_digest=publisher.runtime_manifest_digest(source),
        expected_dependency_digest=recovery.dependency_digest(source),
        python_dependency_root=python_root,
        node_dependency_root=node_root,
        expected_python_dependency_digest=recovery.dependency_root_digest(
            python_root, "bin/python"
        ),
        expected_node_dependency_digest=recovery.dependency_root_digest(
            node_root, recovery.NODE_CLI_RELATIVE
        ),
        mode="restore",
    )

    assert restored["status"] == "RESTORED"
    assert (target / ".venv/bin/python").is_file()
    assert (target / "node_modules/.bin/agy-1.1.3").is_file()
    assert restored["installer_preflights"] == {
        "publisher": "PASS",
        "coordinator": "PASS",
        "capacity": "PASS",
    }


def test_failed_runtime_preflight_leaves_no_half_ready_actor(tmp_path: Path) -> None:
    """REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001 原子失敗。"""
    source, remote, source_sha = _repair_source_repo(tmp_path)
    allow_root = tmp_path / "actors"
    allow_root.mkdir()
    target = allow_root / "publisher"
    python_root = (source / ".venv").resolve()
    node_root = (source / "node_modules").resolve()
    cli = node_root / recovery.NODE_CLI_RELATIVE
    cli.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")

    with pytest.raises(recovery.ActorRecoveryError, match="runtime preflight failed"):
        recovery.recover_actor(
            source_repo=source,
            source_sha=source_sha,
            target=target,
            allow_root=allow_root,
            expected_origin=str(remote),
            expected_runtime_digest=publisher.runtime_manifest_digest(source),
            expected_dependency_digest=recovery.dependency_digest(source),
            python_dependency_root=python_root,
            node_dependency_root=node_root,
            expected_python_dependency_digest=recovery.dependency_root_digest(
                python_root, "bin/python"
            ),
            expected_node_dependency_digest=recovery.dependency_root_digest(
                node_root, recovery.NODE_CLI_RELATIVE
            ),
            mode="restore",
        )

    assert not target.exists()
    assert not list(allow_root.iterdir())

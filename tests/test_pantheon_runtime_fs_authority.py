from __future__ import annotations

from pathlib import Path

import pytest

from scripts import agy_content_publisher as publisher


def _tree_snapshot(root: Path) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                path.lstat().st_mode,
                path.lstat().st_size,
            )
            for path in root.rglob("*")
        )
    )


def test_formal_preflight_blocks_parent_swap_before_external_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    displaced_root = tmp_path / "displaced-sandbox"
    external_root = tmp_path / "external"
    external_root.mkdir()
    before_external = _tree_snapshot(external_root)
    original = publisher._require_sandbox_descendant
    validations = 0

    def swap_after_validation(
        trusted_root: Path,
        candidate: Path,
        label: str,
    ) -> Path:
        nonlocal validations
        result = original(trusted_root, candidate, label)
        validations += 1
        if validations == 2:
            sandbox_root.rename(displaced_root)
            sandbox_root.symlink_to(external_root, target_is_directory=True)
        return result

    monkeypatch.setattr(
        publisher,
        "_require_sandbox_descendant",
        swap_after_validation,
    )

    with pytest.raises(
        publisher.PublishBlocked,
        match="authority|identity|drift|escaped",
    ):
        publisher.formal_capability_preflight(
            "select",
            run_ids=["run-a"],
            correlation_id="parent-swap-red",
            trusted_sandbox_root=sandbox_root,
            queue_root=sandbox_root / "queue",
            state_root=sandbox_root / "publisher-state",
        )

    assert _tree_snapshot(external_root) == before_external
    assert not (external_root / "queue").exists()
    assert not (external_root / "publisher-state").exists()


def test_transaction_operation_trace_records_create_remove_when_snapshot_matches(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    queue_root.mkdir(parents=True)
    state_root.mkdir()
    git_root = sandbox_root / ".git"
    git_root.mkdir()
    (git_root / "agy-content-publisher.lifecycle.lock").touch()
    before_sandbox = _tree_snapshot(sandbox_root)

    result = publisher.formal_capability_preflight(
        "transaction",
        run_ids=["run-a"],
        correlation_id="transaction-trace",
        trusted_sandbox_root=sandbox_root,
        queue_root=queue_root,
        state_root=state_root,
    )

    assert _tree_snapshot(sandbox_root) == before_sandbox
    assert result["production_mutation"] is False
    assert result["sandbox_mutation"] is True
    assert not list(state_root.glob("transaction-*"))
    trace = result["operation_trace"]
    assert result["operation_trace_digest"]
    operations = [event["operation"] for event in trace]
    assert "filesystem-transaction-create" in operations
    assert "git-worktree-add" in operations
    assert "git-worktree-remove" in operations
    assert "filesystem-transaction-remove" in operations
    for event in trace:
        assert set(event) == {
            "operation",
            "relative_target",
            "anchor_identity",
            "pre_identity",
            "post_identity",
            "result",
            "correlation_id",
            "runtime_identity_digest",
        }
        assert event["correlation_id"] == "transaction-trace"
        assert len(event["runtime_identity_digest"]) == 64
        assert not event["relative_target"].startswith("/")
    create_event = next(
        event for event in trace if event["operation"] == "git-worktree-add"
    )
    remove_event = next(
        event for event in trace if event["operation"] == "filesystem-transaction-remove"
    )
    assert create_event["pre_identity"] is None
    assert create_event["post_identity"]["kind"] == "directory"
    assert remove_event["pre_identity"]["kind"] == "directory"
    assert remove_event["post_identity"] is None

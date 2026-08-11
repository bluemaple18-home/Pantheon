from __future__ import annotations

from pathlib import Path

import pytest

from scripts import agy_content_publisher as publisher
from scripts.pantheon_runtime_fs_authority import (
    FilesystemAuthorityError,
    TrustedSandboxDirectoryAuthority,
)


RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": "a" * 64,
}


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
            runtime_receipt=RUNTIME_RECEIPT,
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
        runtime_receipt=RUNTIME_RECEIPT,
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


def test_formal_transaction_blocks_late_parent_swap_before_git_lock_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    displaced_root = tmp_path / "displaced-sandbox"
    external_root = tmp_path / "external"
    external_root.mkdir()
    (external_root / "publisher-state").mkdir()
    before_external = _tree_snapshot(external_root)
    original = publisher._require_sandbox_descendant

    def swap_after_git_root_validation(
        trusted_root: Path,
        candidate: Path,
        label: str,
    ) -> Path:
        result = original(trusted_root, candidate, label)
        if label == "Git root":
            sandbox_root.rename(displaced_root)
            sandbox_root.symlink_to(external_root, target_is_directory=True)
        return result

    monkeypatch.setattr(
        publisher,
        "_require_sandbox_descendant",
        swap_after_git_root_validation,
    )

    with pytest.raises(
        publisher.PublishBlocked,
        match="authority|identity|drift|escaped",
    ):
        publisher.formal_capability_preflight(
            "transaction",
            run_ids=["run-a"],
            correlation_id="late-parent-swap-red",
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            runtime_receipt=RUNTIME_RECEIPT,
        )

    assert _tree_snapshot(external_root) == before_external
    assert not (external_root / ".git").exists()
    assert not (
        external_root / ".git" / "agy-content-publisher.lifecycle.lock"
    ).exists()


def test_formal_transaction_post_lock_cleanup_swap_preserves_external_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    (sandbox_root / ".git").mkdir()
    displaced_root = tmp_path / "displaced-sandbox"
    external_root = tmp_path / "external"
    external_stale = external_root / "publisher-state" / "transaction-escape"
    external_marker = external_stale / "repo" / "marker.txt"
    external_marker.parent.mkdir(parents=True)
    external_marker.write_text("external marker\n", encoding="utf-8")
    before_external = _tree_snapshot(external_root)
    original_record = publisher.OperationTraceRecorder.record_path_operation

    def swap_after_lock_open(
        self: publisher.OperationTraceRecorder,
        operation: str,
        target: Path,
        mutation: object,
    ) -> object:
        result = original_record(self, operation, target, mutation)
        if operation == "filesystem-lock-open":
            sandbox_root.rename(displaced_root)
            sandbox_root.symlink_to(external_root, target_is_directory=True)
        return result

    monkeypatch.setattr(
        publisher.OperationTraceRecorder,
        "record_path_operation",
        swap_after_lock_open,
    )

    with pytest.raises(
        publisher.PublishBlocked,
        match="authority|identity|drift|escaped|sandbox",
    ):
        publisher.formal_capability_preflight(
            "transaction",
            run_ids=["run-a"],
            correlation_id="post-lock-cleanup-swap-red",
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            runtime_receipt=RUNTIME_RECEIPT,
        )

    assert _tree_snapshot(external_root) == before_external
    assert external_marker.read_text(encoding="utf-8") == "external marker\n"


def test_formal_transaction_cleans_stale_worktree_with_authority_trace(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    stale_marker = state_root / "transaction-stale" / "repo" / "marker.txt"
    stale_marker.parent.mkdir(parents=True)
    stale_marker.write_text("stale\n", encoding="utf-8")
    queue_root.mkdir()
    (sandbox_root / ".git").mkdir()

    result = publisher.formal_capability_preflight(
        "transaction",
        run_ids=["run-a"],
        correlation_id="stale-cleanup-authority-green",
        trusted_sandbox_root=sandbox_root,
        queue_root=queue_root,
        state_root=state_root,
        runtime_receipt=RUNTIME_RECEIPT,
    )

    assert result["status"] == "PASS"
    assert not (state_root / "transaction-stale").exists()
    operations = [event["operation"] for event in result["operation_trace"]]
    assert "git-worktree-remove" in operations
    assert "filesystem-stale-transaction-remove" in operations
    for event in result["operation_trace"]:
        assert not event["relative_target"].startswith("/")


def test_authority_stale_cleanup_keeps_non_transaction_entry(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    state_root = sandbox_root / "publisher-state"
    marker = state_root / "cache-entry" / "repo" / "marker.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("keep\n", encoding="utf-8")

    with TrustedSandboxDirectoryAuthority(sandbox_root) as sandbox_authority:
        cleaned = publisher._cleanup_stale_transaction_worktrees(
            tmp_path,
            state_root,
            lambda _repo, _args, _input: "",
            sandbox_authority=sandbox_authority,
        )

    assert cleaned == []
    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_authority_stale_cleanup_rejects_transaction_symlink(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    state_root = sandbox_root / "publisher-state"
    target_root = tmp_path / "target"
    state_root.mkdir(parents=True)
    target_root.mkdir()
    (state_root / "transaction-link").symlink_to(
        target_root,
        target_is_directory=True,
    )

    with TrustedSandboxDirectoryAuthority(sandbox_root) as sandbox_authority:
        with pytest.raises(FilesystemAuthorityError, match="not a directory"):
            publisher._cleanup_stale_transaction_worktrees(
                tmp_path,
                state_root,
                lambda _repo, _args, _input: "",
                sandbox_authority=sandbox_authority,
            )

    assert (state_root / "transaction-link").is_symlink()
    assert target_root.exists()


def test_authority_stale_cleanup_removes_missing_repo_parent_idempotently(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    state_root = sandbox_root / "publisher-state"
    stale_parent = state_root / "transaction-empty"
    stale_parent.mkdir(parents=True)
    git_calls: list[list[str]] = []

    def git(_repo: Path, args: list[str], _input: str | None) -> str:
        git_calls.append(args)
        return ""

    with TrustedSandboxDirectoryAuthority(sandbox_root) as sandbox_authority:
        cleaned = publisher._cleanup_stale_transaction_worktrees(
            tmp_path,
            state_root,
            git,
            sandbox_authority=sandbox_authority,
        )

    assert cleaned == [stale_parent]
    assert not stale_parent.exists()
    assert ["worktree", "remove", "--force", str(stale_parent / "repo")] not in git_calls
    assert ["worktree", "prune"] in git_calls


def test_authority_stale_cleanup_exception_keeps_authority_usable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    state_root = sandbox_root / "publisher-state"
    stale_marker = state_root / "transaction-fail" / "repo" / "marker.txt"
    stale_marker.parent.mkdir(parents=True)
    stale_marker.write_text("stale\n", encoding="utf-8")
    original_remove_tree = TrustedSandboxDirectoryAuthority.remove_tree
    calls = 0

    def fail_parent_remove(
        self: TrustedSandboxDirectoryAuthority,
        relative: Path | str,
    ) -> None:
        nonlocal calls
        calls += 1
        if Path(relative).as_posix() == "publisher-state/transaction-fail":
            raise FilesystemAuthorityError("injected cleanup failure")
        original_remove_tree(self, relative)

    monkeypatch.setattr(
        TrustedSandboxDirectoryAuthority,
        "remove_tree",
        fail_parent_remove,
    )

    with TrustedSandboxDirectoryAuthority(sandbox_root) as sandbox_authority:
        with pytest.raises(FilesystemAuthorityError, match="injected"):
            publisher._cleanup_stale_transaction_worktrees(
                tmp_path,
                state_root,
                lambda _repo, _args, _input: "",
                sandbox_authority=sandbox_authority,
            )
        assert sandbox_authority.exists("publisher-state")

    assert calls >= 1


def test_formal_preflight_blocks_unverified_trace_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    monkeypatch.delenv("PANTHEON_RUNTIME_IDENTITY_DIGEST", raising=False)

    with pytest.raises(publisher.PublishBlocked, match="runtime identity"):
        publisher.formal_capability_preflight(
            "select",
            run_ids=["run-a"],
            correlation_id="missing-trace-identity",
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
        )

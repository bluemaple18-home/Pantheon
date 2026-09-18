"""正式 maintenance CLI：沿既有 runtime/deployment/reconciliation 接縫。"""
import json
import os
import sys
import fcntl

import pytest

from scripts import agy_content_publisher as publisher
from tests.test_publisher_reconciliation import release, accounts


@pytest.fixture
def cli(release, monkeypatch):
    f = release
    for name in tuple(os.environ):
        if name.startswith(("PANTHEON_", "AGY_")):
            monkeypatch.delenv(name)
    for name in publisher.TRANSACTION_RUNTIME_PATHS:
        path = f["repo"] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("隔離 actor runtime fixture\n")
    digest = publisher.runtime_manifest_digest(f["repo"])
    original_preflight = publisher.deployment_preflight
    checks = []

    def git(repo, args, value=None):
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return "b" * 40
        if args[:2] == ["merge-base", "b" * 40] and args[2] in {"a" * 40, "c" * 40}:
            return "b" * 40
        if (args[:3] == ["diff", "--name-only", "b" * 40]
            and args[3] in {"a" * 40, "c" * 40}
            and args[4:] == ["--", *publisher.TRANSACTION_RUNTIME_PATHS]):
            return ""
        return f["git"](repo, args, value)

    def preflight(*args, **kwargs):
        result = original_preflight(*args, **kwargs, git=git)
        checks.append(result)
        return result

    def forbidden(*_args, **_kwargs):
        pytest.fail("maintenance 不得進入發布、worktree、retry、prepare 或 log mutation")

    for name in ("publish_ready_runs", "publish_ready_rewrite_runs", "publish_ready_all",
                 "publish_exact_fresh_ja_translation_run", "prepare_exact_fresh_ja_translation_run",
                 "recover_exhausted_create_retries", "_isolated_transaction_worktree",
                 "_trim_configured_launchd_logs"):
        monkeypatch.setattr(publisher, name, forbidden)
    monkeypatch.setattr(publisher, "run_git", git)
    monkeypatch.setattr(publisher, "deployment_preflight", preflight)
    argv = ["publisher", "--reconcile-unresolved-push", "--repo-root", str(f["repo"]),
            "--queue-root", str(f["queue"]), "--state-root", str(f["state"]),
            "--expected-repo-root", str(f["repo"]), "--expected-queue-root", str(f["queue"]),
            "--expected-state-root", str(f["state"]), "--expected-runtime-sha", "b" * 40,
            "--expected-runtime-digest", digest, "--expected-push-mode", "no-push"]
    monkeypatch.setattr(sys, "argv", argv)
    return {**f, "argv": argv, "preflight_checks": checks}


def test_cli_real_entry_reconciles_then_idempotent_idle(cli, capsys):
    assert publisher.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PUSH_OUTCOME_RECONCILED"
    assert len(publisher._load_ledger(cli["state"])["rewrite_released_runs"]) == 1
    assert cli["evidence"].is_file()
    assert not publisher._unresolved_push_path(cli["state"]).exists()
    before = accounts(cli)
    assert publisher.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "idle"
    assert accounts(cli) == before
    assert len(cli["preflight_checks"]) == 2


def snapshot(f):
    paths = (publisher._ledger_path(f["state"]), f["evidence"], publisher._unresolved_push_path(f["state"]))
    return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in paths if p.exists()}


@pytest.mark.parametrize("extra", [
    ["--push"], ["--dry-run"], ["--rewrite-release"], ["--include-rewrites"],
    ["--new-only"], ["--legacy-report"], ["--deployment-preflight"],
    ["--manifest-authorized-deployment-preflight"], ["--skip-tests"], ["--skip-release-gate"],
    ["--recover-exhausted-create-run", "other"], ["--recover-exhausted-rewrite-run", "other"],
    ["--exact-run-id", "other"], ["--exact-fresh-ja-run-id", "other"],
    ["--prepare-exact-fresh-ja-source-run-id", "other"],
    ["--prepare-exact-fresh-ja-article-id", "other"],
    ["--runtime-manifest-authority", "/unused"], ["--expected-manifest-digest", "unused"],
    ["--expected-retry-error", "unused"], ["--expected-quarantine-reason", "unused"],
    ["--expected-recovery-digest", "unused"], ["--recovery-reason", "unused"],
])
def test_cli_rejects_mixed_modes_before_io(cli, extra):
    before = snapshot(cli)
    cli["argv"].extend(extra)
    with pytest.raises(SystemExit, match="cannot be combined"):
        publisher.main()
    assert snapshot(cli) == before
    assert cli["preflight_checks"] == []
    assert cli["calls"] == []


@pytest.mark.parametrize("missing", ["all", "--expected-runtime-digest", "--queue-root"])
def test_cli_requires_complete_deployment_contract(cli, missing):
    before = snapshot(cli)
    if missing == "all":
        del cli["argv"][cli["argv"].index("--expected-repo-root"):]
    else:
        index = cli["argv"].index(missing)
        del cli["argv"][index:index + 2]
    with pytest.raises(SystemExit, match="required|requires|all expected"):
        publisher.main()
    assert snapshot(cli) == before
    assert cli["preflight_checks"] == []


@pytest.mark.parametrize("field,value", [
    ("--expected-repo-root", "/wrong-actor"), ("--expected-queue-root", "/wrong-queue"),
    ("--expected-state-root", "/wrong-state"), ("--expected-runtime-sha", "a" * 40),
    ("--expected-runtime-digest", "a" * 64), ("--expected-push-mode", "push"),
])
def test_cli_deployment_identity_mismatch_blocks(cli, field, value):
    before = snapshot(cli)
    cli["argv"][cli["argv"].index(field) + 1] = value
    with pytest.raises(publisher.PublishBlocked, match="differs"):
        publisher.main()
    assert snapshot(cli) == before


@pytest.mark.parametrize("failure", ["main", "tag", "unobservable"])
def test_cli_remote_failure_keeps_control_and_accounts(cli, failure, monkeypatch):
    before = snapshot(cli)
    if failure == "unobservable":
        def unavailable(*args):
            raise OSError("隔離遠端不可觀測")
        monkeypatch.setattr(publisher, "run_git", unavailable)
    else:
        cli["refs"][failure] = "a" * 40
    with pytest.raises(publisher.PublishBlocked):
        publisher.main()
    assert snapshot(cli) == before


def test_cli_formal_runtime_rejection_precedes_reconciliation(cli, monkeypatch):
    before = snapshot(cli)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(cli["state"]))
    with pytest.raises(publisher.formal_runtime.RuntimeManifestError, match="environment is incomplete"):
        publisher.main()
    assert snapshot(cli) == before
    assert cli["preflight_checks"] == []
    assert cli["calls"] == []


@pytest.mark.parametrize("lock_kind", ["runtime", "publisher"])
def test_cli_existing_locks_block_recovery(cli, monkeypatch, lock_kind):
    before = snapshot(cli)
    if lock_kind == "runtime":
        monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
        monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(cli["state"]))
        path = cli["state"] / "runtime-work.lock"
    else:
        path = cli["state"] / "publisher.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises((publisher.PublishBlocked, publisher.formal_runtime.RuntimeWorkBusy)):
            publisher.main()
    assert snapshot(cli) == before


def test_cli_waits_for_existing_lifecycle_lock_before_remote_read(cli, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    reached = threading.Event()
    original_git = publisher.run_git
    def git(repo, args, value=None):
        if args == ["fetch", "origin", "main"]:
            reached.set()
        return original_git(repo, args, value)
    monkeypatch.setattr(publisher, "run_git", git)
    path = cli["repo"] / ".git/agy-content-publisher.lifecycle.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    before = snapshot(cli)
    with path.open("a+") as lock, ThreadPoolExecutor(max_workers=1) as pool:
        fcntl.flock(lock, fcntl.LOCK_EX)
        future = pool.submit(publisher.main)
        try:
            assert not reached.wait(0.1)
            assert not future.done()
            assert snapshot(cli) == before
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
        assert future.result(timeout=5) == 0


def test_cli_formal_lease_covers_identity_preflight_and_canonical_writes(cli, monkeypatch):
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(cli["state"]))
    seen = []

    def assert_lease():
        with (cli["state"] / "runtime-work.lock").open("a+") as probe:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def validated(label, **kwargs):
        assert_lease()
        assert kwargs["actor_root"] == cli["repo"]
        assert kwargs["queue_root"] == cli["queue"]
        assert kwargs["state_root"] == cli["state"]
        seen.append("identity")
        return {"status": "PASS", "actor_root": str(cli["repo"]), "actor_head": "b" * 40,
                "runtime_digest": publisher.runtime_manifest_digest(cli["repo"]), "manifest_digest": "a" * 64}

    original_preflight = publisher.deployment_preflight
    def preflight(*args, **kwargs):
        assert_lease()
        seen.append("preflight")
        return original_preflight(*args, **kwargs)

    original_write = publisher._atomic_write_json
    def write(path, value):
        assert_lease()
        seen.append("write")
        return original_write(path, value)

    monkeypatch.setattr(publisher.formal_runtime, "validate_runtime_tick", validated)
    monkeypatch.setattr(publisher, "deployment_preflight", preflight)
    monkeypatch.setattr(publisher, "_atomic_write_json", write)
    assert publisher.main() == 0
    assert seen == ["identity", "preflight", "identity", "write", "write"]
    with (cli["state"] / "runtime-work.lock").open("a+") as probe:
        fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_normal_publisher_startup_still_blocks_without_automatic_reconciliation(release, monkeypatch):
    before = snapshot(release)
    monkeypatch.setattr(publisher, "_reconcile_unresolved_push", lambda *a, **k: pytest.fail("不得startup自動補帳"))
    with pytest.raises(publisher.PublishBlocked, match="unresolved push"):
        publisher.publish_ready_rewrite_runs(release["repo"], release["queue"], release["state"],
                                             git=release["git"], push=False, run_tests=False)
    assert snapshot(release) == before

"""工作 lease：真 tmp flock；OS 服務與正式資料邊界全隔離。"""
from __future__ import annotations

from contextlib import contextmanager
import asyncio
import fcntl
import os
from pathlib import Path
import select
import subprocess
import sys

import pytest

from scripts import pantheon_content_runtime_manifest as runtime
from scripts import pantheon_runtime_activation as activation


def can_exclude(path: Path) -> bool:
    """獨立程序、獨立 open，避免同一 FD 的 flock 自己覆蓋自己。"""
    code = """
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(3)
finally:
    os.close(fd)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(path)], timeout=10, check=False,
        env={k: v for k, v in os.environ.items() if not k.startswith("PANTHEON_")},
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 3), result.stderr
    return result.returncode == 0


@contextmanager
def exclusive(path: Path):
    with path.open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


@pytest.fixture
def state(tmp_path: Path) -> Path:
    value = tmp_path / "state"
    value.mkdir()
    return value


def invoke(state: Path, operation):
    return activation.run_after_activation_token(
        state / "activation.token", {"publisher_state_root": str(state)},
        "com.pantheon.agy-gemini-new", queue_root=state, state_root=state,
        actor_root=state, log_root=state, operation=operation,
    )


def test_existing_callback_cannot_start_under_shutdown_exclusion(state, monkeypatch):
    monkeypatch.setattr(activation, "validate_service_before_io", lambda *a, **k: {})
    marker = state / "protected-write"
    with exclusive(state / "runtime-work.lock"):
        try:
            invoke(state, lambda: marker.write_text("started"))
        except (runtime.RuntimeManifestError, activation.RuntimeActivationError):
            pass
    assert not marker.exists(), "停機獨占期間仍開始 callback I/O"


def test_existing_validation_to_callback_gap_retains_exclusion(state, monkeypatch):
    observations = []
    def validated(*args, **kwargs):
        observations.append(can_exclude(state / "runtime-work.lock"))
        return {}
    monkeypatch.setattr(activation, "validate_service_before_io", validated)
    invoke(state, lambda: observations.append(can_exclude(state / "runtime-work.lock")))
    assert observations == [False, False], "token 驗證及開始工作之間沒有持續 lease"
    assert can_exclude(state / "runtime-work.lock")


def test_existing_wrapper_does_no_protected_io_under_exclusion(state, monkeypatch):
    marker = state / "readiness"
    payload = state / "payload"
    barrier = state / "activation.token"
    barrier.touch()
    manifest = {"queue_root": str(state), "publisher_state_root": str(state),
                "actor_root": str(state), "log_root": str(state)}
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    monkeypatch.setattr(runtime, "load_manifest", lambda *a: manifest)
    monkeypatch.setattr(runtime, "validate_runtime_tick", lambda *a, **k: {})
    monkeypatch.setattr(runtime, "validate_execution_python_identity", lambda *a: None)
    monkeypatch.setattr(runtime, "write_readiness_ack", lambda *a: marker.write_text("ack"))
    monkeypatch.setattr(runtime, "validate_barrier", lambda *a: {})
    monkeypatch.setattr(runtime.os, "execv", lambda *a: payload.write_text("exec"))
    monkeypatch.setattr(sys, "argv", ["manifest", "barrier-exec", "--barrier", str(barrier),
        "--manifest", str(state / "manifest.json"), "--expected-digest", "a" * 64,
        "--service-label", "com.pantheon.agy-gemini-new", "--ready-root", str(state),
        "--timeout", "1", "--", sys.executable, "-c", "pass"])
    with exclusive(state / "runtime-work.lock"):
        result = runtime.main()
    assert not marker.exists() and not payload.exists(), "wrapper readiness/exec 穿越停機排他"
    assert result == 75


def test_existing_capacity_guard_does_not_trim_under_exclusion(state, monkeypatch):
    from scripts import pantheon_content_capacity_guard as capacity
    marker = state / "trimmed"
    class ReachedTrim(Exception):
        pass
    def trim(path):
        marker.write_text("trim")
        raise ReachedTrim
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    monkeypatch.setattr(runtime, "validate_runtime_tick", lambda *a, **k: {})
    monkeypatch.setattr(capacity, "_trim_log", trim)
    with exclusive(state / "runtime-work.lock"):
        try:
            capacity.check_once(state, state, state, state / "capacity.json")
        except (ReachedTrim, runtime.RuntimeManifestError):
            pass
    assert not marker.exists(), "capacity guard 在停機獨占期間仍修改 log"


def start_python(code, *arguments):
    return subprocess.Popen(
        [sys.executable, "-c", code, *map(str, arguments)],
        cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={k: v for k, v in os.environ.items() if not k.startswith("PANTHEON_")},
    )


def line(process):
    assert select.select([process.stdout], [], [], 10)[0], "程序握手逾時"
    value = process.stdout.readline().strip()
    assert value, process.stderr.read() if process.poll() is not None else "握手為空"
    return value


def finish(process):
    if process.poll() is None:
        try:
            process.stdin.write("GO\n")
            process.stdin.flush()
        except BrokenPipeError:
            pass
    output, error = process.communicate(timeout=15)
    assert process.returncode == 0, error
    return output


HELPER = """
import sys
from pathlib import Path
from scripts import pantheon_runtime_activation as activation
from scripts import pantheon_content_runtime_manifest as runtime
state = Path(sys.argv[1])
activation.validate_service_before_io = lambda *a, **k: {}
def work():
    print('READY', flush=True)
    assert sys.stdin.readline().strip() == 'GO'
    print('DONE', flush=True)
activation.run_after_activation_token(state/'token', {'publisher_state_root':str(state)},
    'com.pantheon.agy-gemini-'+sys.argv[2], queue_root=state, state_root=state,
    actor_root=state, log_root=state, operation=work)
"""


def test_new_and_rewrite_work_can_overlap_but_shutdown_cannot(state):
    processes = []
    try:
        for lane in ("new", "rewrite"):
            process = start_python(HELPER, state, lane)
            processes.append(process)
            assert line(process) == "READY"
        assert not can_exclude(state / "runtime-work.lock")
        assert all(process.poll() is None for process in processes)
    finally:
        for process in processes:
            finish(process)
    assert can_exclude(state / "runtime-work.lock")


@pytest.mark.parametrize("outcome", [None, ValueError, KeyboardInterrupt, asyncio.CancelledError])
def test_callback_success_exception_and_cancellation_release(state, monkeypatch, outcome):
    monkeypatch.setattr(activation, "validate_service_before_io", lambda *a, **k: {})
    def work():
        assert not can_exclude(state / "runtime-work.lock")
        if outcome is not None:
            raise outcome("synthetic")
        return 17
    if outcome is None:
        assert invoke(state, work) == 17
    else:
        with pytest.raises(outcome):
            invoke(state, work)
    assert can_exclude(state / "runtime-work.lock")
    assert runtime.runtime_work_pass_fds() == ()


def test_invalid_token_never_calls_work_and_releases(state, monkeypatch):
    def invalid(*args, **kwargs):
        assert not can_exclude(state / "runtime-work.lock")
        raise activation.RuntimeActivationError("stale synthetic token")
    monkeypatch.setattr(activation, "validate_service_before_io", invalid)
    with pytest.raises(activation.RuntimeActivationError, match="stale synthetic"):
        invoke(state, lambda: pytest.fail("invalid token reached protected work"))
    assert can_exclude(state / "runtime-work.lock")


def test_nested_lease_release_does_not_release_outer_work(state):
    with runtime.runtime_work_lease(state):
        first = runtime.runtime_work_pass_fds()
        with runtime.runtime_work_lease(state):
            assert runtime.runtime_work_pass_fds() != first
        assert runtime.runtime_work_pass_fds() == first
        assert not can_exclude(state / "runtime-work.lock")
    assert can_exclude(state / "runtime-work.lock")


def test_symlink_lock_fails_before_callback(state, monkeypatch):
    target = state / "unrelated"
    target.write_text("untouched")
    (state / "runtime-work.lock").symlink_to(target)
    monkeypatch.setattr(activation, "validate_service_before_io", lambda *a, **k: {})
    with pytest.raises((OSError, runtime.RuntimeManifestError)):
        invoke(state, lambda: pytest.fail("symlink admitted work"))
    assert target.read_text() == "untouched"


@pytest.mark.parametrize("service", ["runner", "coordinator", "publisher", "capacity"])
def test_actual_service_entry_stops_before_validation_or_work(state, monkeypatch, service):
    from scripts import agy_gemini_runner as runner
    from scripts import agy_gemini_coordinator as coordinator
    from scripts import agy_content_publisher as publisher
    from scripts import pantheon_content_capacity_guard as capacity
    calls = {
        "runner": lambda: runner.process_once(state, lane="new"),
        "coordinator": lambda: coordinator.cycle_once(state, repo_root=state),
        "publisher": lambda: publisher.publish_ready_all(state, state, state),
        "capacity": lambda: capacity.check_once(state, state, state, state / "capacity.json"),
    }
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    monkeypatch.setattr(runtime, "validate_runtime_tick", lambda *a, **k: pytest.fail("已進入工作"))
    with exclusive(state / "runtime-work.lock"):
        if service == "runner":
            # Runner 原公開介面以 failed 字典回報；仍要求完全未進入工作。
            assert calls[service]() == {"status": "failed", "error_type": "RuntimeWorkBusy"}
        else:
            with pytest.raises(runtime.RuntimeWorkBusy):
                calls[service]()


@pytest.mark.parametrize("entry", [
    "publish_ready_runs", "publish_ready_rewrite_runs", "publish_ready_translation_runs",
])
def test_public_publish_entry_excluded_before_outer_journal(state, monkeypatch, entry):
    """呼叫原公開 decorated 入口；不用 unwrap，也不依賴 main/all 的外層鎖。"""
    from scripts import agy_content_publisher as publisher
    entered = []
    class ReachedJournal(Exception):
        pass
    def journal(*args, **kwargs):
        entered.append("journal")
        raise ReachedJournal("outer journal entered")
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    monkeypatch.setattr(publisher, "_validate_formal_runtime", lambda *a: {})
    monkeypatch.setattr(publisher, "MutationJournal", journal)
    with exclusive(state / "runtime-work.lock"):
        try:
            getattr(publisher, entry)(state, state, state)
        except (runtime.RuntimeWorkBusy, ReachedJournal):
            pass
    assert entered == [], "停機獨占時，公開入口仍进入外層 journal"


@pytest.mark.parametrize("entry", [
    "publish_ready_runs", "publish_ready_rewrite_runs", "publish_ready_translation_runs",
])
@pytest.mark.parametrize("outcome", ["return", "failure"])
def test_public_publish_outer_scope_holds_lease_through_cleanup(state, monkeypatch, entry, outcome):
    """原 recovery decorator／原函式入口；僅替換 journal 與業務副作用接點。"""
    from scripts import agy_content_publisher as publisher
    observations = []
    def observe(name):
        observations.append((name, can_exclude(state / "runtime-work.lock")))
    class Journal:
        mutation_started = True
        selected_run_ids = ["synthetic-run"]
        def __init__(self, *args):
            self.depth = 0
            observe("journal-init")
        @contextmanager
        def state_scope(self, *args, **kwargs):
            self.depth += 1
            observe("scope-enter")
            try:
                # 原函式的 busy 返回也必須跑完外層 flush/finally。
                yield self.depth == 1
            finally:
                observe("scope-exit")
                self.depth -= 1
        def acquire_writer(self):
            observe("recovery-writer")
        def flush_deferred(self):
            observe("flush")
        def recovery_run_ids(self, *args):
            observe("recovery-run-ids")
            return ["synthetic-run"]
    def normalized(*args):
        observe("function-entry")
        if outcome == "failure":
            raise ValueError("synthetic publish failure")
        return None
    def recover(*args, **kwargs):
        observe("recovery")
        return state / "synthetic-recovery.json"
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    monkeypatch.setattr(publisher, "_validate_formal_runtime", lambda *a: observe("validate"))
    monkeypatch.setattr(publisher, "MutationJournal", Journal)
    monkeypatch.setattr(publisher, "_assert_clean_origin_head", lambda *a: "a" * 40)
    monkeypatch.setattr(publisher, "_normalize_exact_run_ids", normalized)
    monkeypatch.setattr(publisher, "_owns_unresolved_push", lambda *a: False)
    monkeypatch.setattr(publisher, "_recover_failed_publish", recover)
    monkeypatch.setattr(publisher, "_record_retry_failure", lambda *a, **k: observe("retry-record"))
    result = getattr(publisher, entry)(state, state, state)
    assert result["status"] == ("failed_recovered" if outcome == "failure" else "busy")
    assert "flush" in [name for name, _ in observations]
    if outcome == "failure":
        assert {"recovery", "retry-record"} <= {name for name, _ in observations}
    assert observations[-1][0] == "scope-exit"
    assert not any(excluded for _, excluded in observations), observations
    assert can_exclude(state / "runtime-work.lock")


def test_public_translation_resume_holds_lease_until_outer_scope_exit(state, monkeypatch):
    """PUSH_PREPARED 分支在內層 function 之前返回，仍須持有 lease。"""
    import json
    from scripts import agy_content_publisher as publisher
    observations = []
    def observe(name):
        observations.append((name, can_exclude(state / "runtime-work.lock")))
    class Journal:
        def __init__(self, *args):
            observe("journal-init")
        @contextmanager
        def state_scope(self, *args, **kwargs):
            observe("scope-enter")
            try:
                yield True
            finally:
                observe("scope-exit")
    control = state / "synthetic-push.json"
    control.write_text(json.dumps({"status": "PUSH_PREPARED", "run_id": "synthetic-run"}))
    def resume(*args, **kwargs):
        observe("resume")
        return {"status": "resumed-synthetic"}
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    monkeypatch.setattr(publisher, "_validate_formal_runtime", lambda *a: observe("validate"))
    monkeypatch.setattr(publisher, "MutationJournal", Journal)
    monkeypatch.setattr(publisher, "_unresolved_push_path", lambda *a: control)
    monkeypatch.setattr(publisher, "_resume_prepared_translation", resume)
    result = publisher.publish_ready_translation_runs(state, state, state, exact_run_ids=["synthetic-run"])
    assert result == {"status": "resumed-synthetic"}
    assert [name for name, _ in observations][-2:] == ["resume", "scope-exit"]
    assert not any(excluded for _, excluded in observations), observations
    assert can_exclude(state / "runtime-work.lock")


WRAPPER = """
import os, sys
from pathlib import Path
from scripts import pantheon_content_runtime_manifest as runtime
state = Path(sys.argv[1])
mode = sys.argv[2]
os.environ['PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT'] = str(state)
manifest = {k:str(state) for k in ('queue_root','publisher_state_root','actor_root','log_root')}
manifest.update(manifest_digest='a'*64, generation='synthetic')
runtime.load_manifest = lambda *a: manifest
runtime.validate_runtime_tick = lambda *a, **k: {}
runtime.validate_execution_python_identity = lambda *a: None
def ready(*args):
    (state/'ack').write_text('ready')
    if mode == 'ack-error': raise OSError('synthetic readiness failure')
runtime.write_readiness_ack = ready
def validate(*args):
    if mode == 'token-error': raise runtime.RuntimeManifestError('stale token')
    return {}
runtime.validate_barrier = validate
if mode == 'exec-error':
    def error(*a): raise OSError('synthetic exec failure')
    runtime.os.execv = error
payload = '''import os,sys
from scripts import pantheon_content_runtime_manifest as r
assert r.runtime_work_pass_fds()
print("PAYLOAD_READY",flush=True)
assert sys.stdin.readline().strip()=="GO"
'''
sys.argv = ['manifest','barrier-exec','--barrier',str(state/'token'),
    '--manifest',str(state/'manifest.json'),'--expected-digest','a'*64,
    '--service-label','com.pantheon.agy-gemini-new','--ready-root',str(state),
    '--timeout','1',*(['--activation-only'] if mode=='activation-only' else []),
    '--',sys.executable,'-c',payload]
print('RETURN='+str(runtime.main()),flush=True)
"""


def test_actual_wrapper_exec_inherits_lease_through_payload_exit(state):
    (state / "token").touch()
    process = start_python(WRAPPER, state, "normal")
    try:
        assert line(process) == "PAYLOAD_READY"
        assert (state / "ack").exists()
        assert not can_exclude(state / "runtime-work.lock")
    finally:
        finish(process)
    assert can_exclude(state / "runtime-work.lock")


@pytest.mark.parametrize("mode,expected", [
    ("activation-only", 0), ("ack-error", 78), ("token-error", 78),
    ("exec-error", 78), ("missing-token", 75),
])
def test_wrapper_return_paths_release_lease(state, mode, expected):
    if mode != "missing-token":
        (state / "token").touch()
    process = start_python(WRAPPER, state, mode)
    output, error = process.communicate(timeout=10)
    assert process.returncode == 0, error
    assert f"RETURN={expected}" in output
    assert can_exclude(state / "runtime-work.lock")


def test_new_wrapper_process_under_exclusion_never_writes_ack(state):
    (state / "token").touch()
    with exclusive(state / "runtime-work.lock"):
        process = start_python(WRAPPER, state, "normal")
        output, error = process.communicate(timeout=10)
    assert process.returncode == 0, error
    assert "RETURN=75" in output and not (state / "ack").exists()


@pytest.mark.parametrize("fork_child", [False, True])
def test_publisher_real_caller_passes_lease_and_does_not_unlock_live_descendant(state, fork_child):
    """實際 _run_checked；子程序及 fork 後代均以 tmp FIFO 握手自然退出。"""
    target = r'''
import os, select, sys
from pathlib import Path
fd = int(sys.argv[1])
if sys.argv[3] == 'True':
    if os.fork(): os._exit(0)
    for stream in (0, 1, 2): os.close(stream)
assert os.fstat(fd).st_ino == os.stat(sys.argv[4]).st_ino
notice = os.open(Path(sys.argv[2])/'child-notice', os.O_WRONLY)
release = os.open(Path(sys.argv[2])/'child-release', os.O_RDONLY | os.O_NONBLOCK)
try:
    os.write(notice, b'READY')
    assert select.select([release], [], [], 10)[0]
    assert os.read(release, 1) == b'G'
    os.close(fd)
    os.write(notice, b'CLOSED')
finally:
    os.close(notice)
    os.close(release)
'''
    parent = """
import sys
from pathlib import Path
from scripts import pantheon_content_runtime_manifest as runtime
from scripts import agy_content_publisher as publisher
state=Path(sys.argv[1])
with runtime.runtime_work_lease(state):
    fd=runtime.runtime_work_pass_fds()[0]
    publisher._run_checked(Path.cwd(), [sys.executable,'-c',sys.argv[2],str(fd),
        sys.argv[3],sys.argv[4],str(state/'runtime-work.lock')])
print('CALLER_RETURNED',flush=True)
"""
    for name in ("child-notice", "child-release"):
        os.mkfifo(state / name, 0o600)
    notice = os.open(state / "child-notice", os.O_RDWR | os.O_NONBLOCK)
    release = os.open(state / "child-release", os.O_RDWR | os.O_NONBLOCK)
    def receive(size):
        data = b""
        while len(data) < size:
            assert select.select([notice], [], [], 10)[0], "FIFO 握手逾時"
            data += os.read(notice, size - len(data))
        return data
    process = start_python(parent, state, target, state, fork_child)
    ready = False
    try:
        assert receive(5) == b"READY"
        ready = True
        if fork_child:
            output, error = process.communicate(timeout=10)
            assert process.returncode == 0 and "CALLER_RETURNED" in output, error
        else:
            assert process.poll() is None
        assert not can_exclude(state / "runtime-work.lock"), "活後代被 parent close 提早解鎖"
    finally:
        os.write(release, b"G")
        if ready:
            assert receive(6) == b"CLOSED"
        os.close(notice)
        os.close(release)
        finish(process)
    assert can_exclude(state / "runtime-work.lock")


@pytest.mark.parametrize("explicit_env", [False, True])
@pytest.mark.parametrize("child_fails", [False, True])
def test_child_fd_declaration_matches_nested_lease_without_mutating_parent(state, monkeypatch, explicit_env, child_fails):
    """真子程序讀正式 helper；正常與失敗皆不修改父環境或 caller mapping。"""
    import json
    from types import MappingProxyType
    from scripts import agy_content_publisher as publisher

    key = "PANTHEON_RUNTIME_WORK_LEASE_FD"
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    with runtime.runtime_work_lease(state) as outer:
        monkeypatch.setenv(key, str(outer))
        original_env = dict(os.environ)
        supplied = MappingProxyType(dict(os.environ)) if explicit_env else None
        with runtime.runtime_work_lease(state) as inner:
            assert outer != inner
            leaf = """
import json, os, sys
from pathlib import Path
from scripts import pantheon_content_runtime_manifest as runtime
Path(sys.argv[1]).write_text(json.dumps({
    'declared': int(os.environ['PANTHEON_RUNTIME_WORK_LEASE_FD']),
    'discovered': runtime.runtime_work_pass_fds(),
}))
raise SystemExit(int(sys.argv[2]))
"""
            receipt = state / "child-fd.json"
            argv = [sys.executable, "-c", leaf, str(receipt), "7" if child_fails else "0"]
            if child_fails:
                with pytest.raises(subprocess.CalledProcessError) as caught:
                    publisher._run_checked(Path(__file__).resolve().parents[1], argv, env=supplied, timeout_seconds=10)
                assert caught.value.returncode == 7
            else:
                publisher._run_checked(Path(__file__).resolve().parents[1], argv, env=supplied, timeout_seconds=10)
            assert json.loads(receipt.read_text()) == {"declared": inner, "discovered": [inner]}
            assert dict(os.environ) == original_env
            if supplied is not None:
                assert dict(supplied) == original_env


def test_release_test_environment_stays_filtered_at_actual_subprocess_boundary(state, monkeypatch):
    """真正子程序不能重新收到 release test 已移除的 runtime 環境。"""
    import json
    from scripts import agy_content_publisher as publisher

    key = "PANTHEON_RUNTIME_WORK_LEASE_FD"
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state))
    with runtime.runtime_work_lease(state) as outer:
        monkeypatch.setenv(key, str(outer))
        original_env = dict(os.environ)
        filtered = publisher._release_test_child_env()
        expected = dict(filtered)
        with runtime.runtime_work_lease(state):
            fd = runtime.runtime_work_pass_fds()[0]
            leaf = """
import json, os, sys
from pathlib import Path
assert os.fstat(int(sys.argv[2])).st_ino == Path(sys.argv[3]).stat().st_ino
Path(sys.argv[1]).write_text(json.dumps([
    k for k in os.environ if k.startswith('PANTHEON_RUNTIME_') or k == 'PANTHEON_FORMAL_RUNTIME'
]))
"""
            receipt = state / "filtered-env.json"
            publisher._run_checked(Path(__file__).resolve().parents[1],
                [sys.executable, "-c", leaf, str(receipt), str(fd), str(state / "runtime-work.lock")],
                env=filtered, timeout_seconds=10)
            assert json.loads(receipt.read_text()) == []
            assert filtered == expected and dict(os.environ) == original_env


def test_parallel_child_fd_environments_remain_per_call(state, monkeypatch):
    """兩個執行緒各持共享 lease；交錯呼叫仍各自收到正確環境副本。"""
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from scripts import agy_content_publisher as publisher

    key = "PANTHEON_RUNTIME_WORK_LEASE_FD"
    monkeypatch.setenv(key, "777777")
    before = dict(os.environ)
    rendezvous = threading.Barrier(2)
    seen = []
    def child_boundary(args, **kwargs):
        rendezvous.wait(timeout=10)
        fd = kwargs["pass_fds"][0]
        assert int(kwargs["env"][key]) == fd
        assert os.fstat(fd).st_ino == (state / "runtime-work.lock").stat().st_ino
        seen.append(fd)
    monkeypatch.setattr(publisher.subprocess, "run", child_boundary)
    def call():
        with runtime.runtime_work_lease(state):
            publisher._run_checked(state, ["isolated-subprocess-boundary"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(call) for _ in range(2)]
        for future in futures:
            future.result(timeout=15)
    assert len(set(seen)) == 2 and dict(os.environ) == before

"""直接 child 的 lease lifetime、環境 binding 與 nested scope 回歸。"""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from scripts import pantheon_content_runtime_manifest as runtime

FD = "PANTHEON_RUNTIME_WORK_LEASE_FD"
STATE = "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"
FORMAL = "PANTHEON_FORMAL_RUNTIME"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    for key in (FD, STATE, FORMAL):
        monkeypatch.delenv(key, raising=False)


def test_nonformal_preserves_environment():
    assert runtime.runtime_work_child_transport() == {}
    env = {"ONLY": "value"}
    kwargs = runtime.runtime_work_child_transport(env)
    assert kwargs == {"env": env}
    assert kwargs["env"] is not env


def test_formal_without_lease_rejected(monkeypatch):
    monkeypatch.setenv(FORMAL, "1")
    with pytest.raises(runtime.RuntimeManifestError, match="requires work lease"):
        runtime.runtime_work_child_transport()


def test_nested_scope_rebinds_same_inode_without_global_mutation(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    with runtime.runtime_work_lease(root) as outer:
        monkeypatch.setenv(FD, str(outer))
        monkeypatch.setenv(STATE, str(root))
        original = dict(os.environ)
        with runtime.runtime_work_lease(root) as inner:
            env = {**os.environ, "CUSTOM": "kept"}
            kwargs = runtime.runtime_work_child_transport(env)
            assert kwargs["pass_fds"] == (inner,)
            assert kwargs["env"][FD] == str(inner)
            assert kwargs["env"][STATE] == str(root)
            assert kwargs["env"]["CUSTOM"] == "kept"
            assert env[FD] == str(outer)
            # 真 exec child 再經 inherited-only helper 傳給 grandchild。
            code = '''import json,os,subprocess,sys
from scripts import pantheon_content_runtime_manifest as r
k=r.runtime_work_child_transport()
child="import os; from pathlib import Path; f=os.fstat(int(os.environ['PANTHEON_RUNTIME_WORK_LEASE_FD'])); s=(Path(os.environ['PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT'])/'runtime-work.lock').stat(); assert (f.st_dev,f.st_ino)==(s.st_dev,s.st_ino); print('same-inode')"
print(subprocess.check_output([sys.executable,'-c',child],text=True,**k).strip())
'''
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True, **kwargs)
            assert result.stdout.strip() == "same-inode"
            assert dict(os.environ) == original
        assert runtime.runtime_work_child_transport()["pass_fds"] == (outer,)
    assert runtime._WORK_LEASE.get() is None
    assert runtime._WORK_LEASE_ROOT.get() is None


@pytest.mark.parametrize("kind", ["root", "fd", "closed", "invalid"])
def test_explicit_wrong_binding_rejected(tmp_path, kind):
    root = tmp_path.resolve()
    wrong = root / "wrong"; wrong.mkdir()
    with runtime.runtime_work_lease(root):
        env = {}
        with (wrong / "runtime-work.lock").open("w+") as other:
            if kind == "root": env[STATE] = str(wrong)
            elif kind == "fd": env[FD] = str(other.fileno())
            elif kind == "closed": env[FD] = "999999"
            else: env[FD] = "no-fd"
            with pytest.raises(runtime.RuntimeManifestError, match="binding differs"):
                runtime.runtime_work_child_transport(env)


@pytest.mark.parametrize("kind", ["replace", "symlink", "hardlink"])
def test_context_lease_identity_drift_rejected(tmp_path, kind):
    root = tmp_path.resolve(); lock = root / "runtime-work.lock"
    with runtime.runtime_work_lease(root):
        if kind == "hardlink": os.link(lock, root / "alias")
        else:
            lock.rename(root / "old")
            if kind == "replace": lock.touch()
            else: lock.symlink_to(root / "old")
        with pytest.raises(runtime.RuntimeManifestError, match="identity drift"):
            runtime.runtime_work_child_transport()


CHILD = '''import json,os,time
from pathlib import Path
p=Path(os.environ['PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT'])
try:
 f=os.fstat(int(os.environ.get('PANTHEON_RUNTIME_WORK_LEASE_FD','-1')));s=(p/'runtime-work.lock').stat()
 valid=(f.st_dev,f.st_ino)==(s.st_dev,s.st_ino)
except (OSError,ValueError):valid=False
(p/'ready').write_text(json.dumps({'pid':os.getpid(),'valid':valid,'pgid':os.getpgrp()}))
while not (p/'finish').exists():time.sleep(.01)
(p/'terminal').touch()
print('0'*40)
'''
PARENT = '''import sys
from pathlib import Path
from scripts import pantheon_content_runtime_manifest as r
from scripts import agy_gemini_coordinator as c, agy_gemini_runner as g
from scripts import pantheon_content_capacity_guard as cap, agy_seo_copy_pipeline as seo
@r.with_runtime_work_lease
def invoke():
 seam=sys.argv[1];root=Path.cwd()
 if seam=='coordinator':c._head_sha(root)
 elif seam=='runner':g._translation_source_git(root,'rev-parse','HEAD')
 elif seam=='capacity':cap._run(['git','rev-parse','HEAD'])
 elif seam=='manifest':r._git_output(root,'rev-parse','HEAD')
 elif seam=='detached-node':seo._run_registry_node_script(root,'unused')
invoke()
'''


def _wait(predicate):
    deadline = time.monotonic() + 10
    while not predicate():
        assert time.monotonic() < deadline, "合成 fixture handshake 逾時"
        time.sleep(.01)


def _exclusive(root):
    with (root / "runtime-work.lock").open("r+") as lease:
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


@pytest.mark.parametrize("seam", ["coordinator", "runner", "capacity", "manifest", "detached-node"])
def test_formal_direct_child_outlives_parent_and_releases_only_at_terminal(tmp_path, seam):
    root = tmp_path.resolve(); binary = root / "bin"; binary.mkdir()
    for name in ("git", "node"):
        executable = binary / name
        executable.write_text("#!" + str(Path(sys.executable).resolve()) + "\n" + CHILD)
        executable.chmod(0o700)
    env = {**os.environ, FORMAL: "1", STATE: str(root), "PATH": str(binary) + os.pathsep + os.environ["PATH"]}
    child = None
    with (root / "parent.log").open("w") as log:
        parent = subprocess.Popen([sys.executable, "-c", PARENT, seam], cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            _wait(lambda: (root / "ready").exists() or parent.poll() is not None)
            assert (root / "ready").exists(), (root / "parent.log").read_text()
            child = json.loads((root / "ready").read_text())
            parent.kill(); parent.wait(timeout=5)
            os.kill(child["pid"], 0)
            assert child["valid"], "child env FD 未綁同 inode"
            assert _exclusive(root) is False, "parent abrupt exit 不得釋放 child lease"
            if seam == "detached-node": assert child["pgid"] == child["pid"]
            (root / "finish").touch()
            _wait(lambda: (root / "terminal").exists())
            _wait(lambda: _exclusive(root))
        finally:
            if parent.poll() is None: parent.kill(); parent.wait(timeout=5)
            if child:
                try: os.kill(child["pid"], signal.SIGTERM)
                except ProcessLookupError: pass
            try: os.killpg(parent.pid, signal.SIGTERM)
            except ProcessLookupError: pass


def _formal_identity(root, label):
    actor = root / "actor"; actor.mkdir()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(actor), *args], text=True).strip()
    git("init", "--quiet")
    git("-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "--allow-empty", "-qm", "合成 actor")
    for name in ("queue", "state", "logs", "ready"):
        (root / name).mkdir()
    manifest = runtime.build_manifest(
        actor_root=actor, queue_root=root / "queue", publisher_state_root=root / "state",
        log_root=root / "logs", identity="synthetic-transport-startup", actor_head=git("rev-parse", "HEAD"),
        python_executable=Path(sys.executable).resolve(),
    )
    path = root / "manifest.json"; runtime.write_manifest(path, manifest)
    env = {**os.environ, FORMAL: "1", "PANTHEON_RUNTIME_MANIFEST": str(path), "PANTHEON_RUNTIME_SERVICE_LABEL": label}
    for field, key in {
        "manifest_digest": "MANIFEST_DIGEST", "identity": "IDENTITY", "runtime_identity_digest": "IDENTITY_DIGEST",
        "runtime_digest": "CODE_DIGEST", "config_version": "CONFIG_VERSION", "generation": "GENERATION",
        "actor_root": "ACTOR_ROOT", "queue_root": "QUEUE_ROOT", "publisher_state_root": "PUBLISHER_STATE_ROOT",
        "log_root": "LOG_ROOT", "actor_head": "ACTOR_HEAD", "python_executable": "PYTHON_EXECUTABLE",
    }.items(): env["PANTHEON_RUNTIME_" + key] = str(manifest[field])
    return manifest, path, env


def test_native_barrier_startup_actor_git_validation_has_lease(tmp_path):
    root = tmp_path.resolve(); label = runtime.SERVICE_LABELS[1]
    manifest, path, env = _formal_identity(root, label)
    for service in runtime.SERVICE_LABELS:
        runtime.write_readiness_ack(root / "ready", manifest, service)
    barrier = root / "barrier"; runtime.activate_barrier(barrier, root / "ready", manifest)
    output = root / "exec-child.json"
    code = "import os,json; from pathlib import Path; fd=int(os.environ['PANTHEON_RUNTIME_WORK_LEASE_FD']); p=Path(os.environ['PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT'])/'runtime-work.lock'; assert os.fstat(fd).st_ino==p.stat().st_ino; Path(" + repr(str(output)) + ").write_text(json.dumps({'lease':True}))"
    result = subprocess.run([
        sys.executable, "-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec",
        "--barrier", str(barrier), "--manifest", str(path), "--expected-digest", manifest["manifest_digest"],
        "--service-label", label, "--ready-root", str(root / "ready"), "--timeout", "1", "--", sys.executable, "-c", code,
    ], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output.read_text()) == {"lease": True}
    assert _exclusive(root / "state")


def test_formal_capacity_preflight_actor_git_validation_has_lease(tmp_path, monkeypatch):
    from scripts import pantheon_content_capacity_guard as guard
    root = tmp_path.resolve(); label = runtime.SERVICE_LABELS[-1]
    manifest, path, env = _formal_identity(root, label)
    for key, value in env.items(): monkeypatch.setenv(key, value)
    reached = []
    class SnapshotReached(Exception): pass
    def snapshot(*args, **kwargs):
        reached.append(runtime.runtime_work_child_transport()["pass_fds"])
        raise SnapshotReached
    monkeypatch.setattr(guard, "_snapshot", snapshot)
    # 沿 installer 的 formal env → preflight → validate_runtime_tick → 真 Git。
    with pytest.raises(SnapshotReached):
        guard.preflight(root / "queue", root / "state", root / "logs")
    assert reached and reached[0]
    assert _exclusive(root / "state")


def test_real_node_detached_transport_identity(tmp_path):
    from scripts import agy_seo_copy_pipeline as seo
    script = '''import fs from 'node:fs';
const fd=Number(process.env.PANTHEON_RUNTIME_WORK_LEASE_FD);
const held=fs.fstatSync(fd), current=fs.statSync(process.env.PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT+'/runtime-work.lock');
console.log(JSON.stringify({same:held.dev===current.dev && held.ino===current.ino}));'''
    with runtime.runtime_work_lease(tmp_path.resolve()):
        result = seo._run_registry_node_script(ROOT, script)
        assert json.loads(result.stdout) == {"same": True}


@pytest.mark.parametrize("symbol", ["registry_articles", "registry_topics"])
def test_prerender_formal_child_transport(tmp_path, monkeypatch, symbol):
    from scripts import prerender_article_shells as prerender
    monkeypatch.setenv(FORMAL, "1")
    monkeypatch.setenv(STATE, str(tmp_path.resolve()))
    observed = []
    def run(command, **kwargs):
        fd, = kwargs["pass_fds"]
        assert kwargs["env"][FD] == str(fd)
        assert os.fstat(fd).st_ino == (tmp_path / "runtime-work.lock").stat().st_ino
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, "[]", "")
    monkeypatch.setattr(prerender.subprocess, "run", run)
    with runtime.runtime_work_lease(tmp_path.resolve()):
        assert getattr(prerender, symbol)() == []
    assert len(observed) == 1


def test_inherited_closed_fd_rejected_as_contract_error(tmp_path, monkeypatch):
    monkeypatch.setenv(FD, "999999")
    monkeypatch.setenv(STATE, str(tmp_path.resolve()))
    with pytest.raises(runtime.RuntimeManifestError, match="descriptor is unavailable"):
        runtime.runtime_work_child_transport()

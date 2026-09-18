"""真公開 Publisher → registry helper → Node；資料與開始／完成握手隔離。"""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]


def exclude_now(state):
    descriptor = os.open(state / "runtime-work.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True
    finally:
        os.close(descriptor)


def write_script(state, name, body):
    path = state / name
    path.write_text(body)
    return path


WRAPPER = r"""
import os, sys
from pathlib import Path
from scripts import pantheon_content_runtime_manifest as runtime
state=Path(sys.argv[1])
os.environ['PANTHEON_FORMAL_RUNTIME']='1'
os.environ['PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT']=str(state)
manifest={k:str(state) for k in ('queue_root','publisher_state_root','actor_root','log_root')}
manifest.update(manifest_digest='a'*64,generation='independent-tmp')
runtime.load_manifest=lambda *a:manifest
runtime.validate_runtime_tick=lambda *a,**k:{}
runtime.validate_execution_python_identity=lambda *a:None
runtime.write_readiness_ack=lambda *a:(state/'readiness-ack').write_text('ready')
runtime.validate_barrier=lambda *a:{}
sys.argv=['manifest','barrier-exec','--barrier',str(state/'token'),'--manifest',str(state/'manifest.json'),
 '--expected-digest','a'*64,'--service-label','com.pantheon.agy-content-publisher',
 '--ready-root',str(state),'--timeout','5','--',sys.executable,*sys.argv[2:]]
raise SystemExit(runtime.main())
"""


def wait_file(path, timeout=12):
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() >= deadline:
            raise AssertionError(f'握手逾時：{path.name}')
        time.sleep(0.02)


def test_public_registry_cancel_keeps_node_protected(tmp_path):
    """取消 caller 後，尚未收到完成握手的真 Node 不得失去排他保護。"""
    state = tmp_path.resolve()
    static = state / 'app/web/static'
    static.mkdir(parents=True)
    (state / 'token').touch()
    (state / 'package.json').write_text('{"type":"module"}')
    (static / 'article-registry.js').write_text(r'''
import fs from 'node:fs';
const root=process.cwd();
let inherited=false;
try {
  const held=fs.fstatSync(Number(process.env.PANTHEON_RUNTIME_WORK_LEASE_FD));
  const expected=fs.statSync(root+'/runtime-work.lock');
  inherited=held.dev===expected.dev && held.ino===expected.ino;
} catch {}
fs.writeFileSync(root+'/node-ready.json',JSON.stringify({pid:process.pid,inherited}));
const deadline=Date.now()+30000;
while (!fs.existsSync(root+'/release-node') && Date.now()<deadline) {
  await new Promise(resolve=>setTimeout(resolve,20));
}
fs.writeFileSync(root+'/node-work-done','completed');
export function getArticlePath() { return '/articles/local/'; }
export function listArticleRecords() { return []; }
''')
    wrapper = write_script(state, 'wrapper.py', WRAPPER)
    payload = write_script(state, 'payload.py', r'''
import sys
from pathlib import Path
from scripts import agy_content_publisher as publisher
state=Path(sys.argv[1])
publisher._validate_formal_runtime=lambda *a:{}
publisher._repo_lock_path=lambda *a:state/'publisher-mutation.lock'
publisher._assert_clean_origin_head=lambda *a:'a'*40
class EndFixture(BaseException): pass
def registry_work(*args):
    publisher._public_article_count(state)
    raise EndFixture()
publisher._normalize_exact_run_ids=registry_work
try:
    publisher.publish_ready_runs(state,state,state)
except EndFixture:
    pass
''')
    env = {k:v for k,v in os.environ.items() if not k.startswith('PANTHEON_')}
    env['PYTHONPATH'] = str(REPO)
    caller = subprocess.Popen(
        [sys.executable, str(wrapper), str(state), str(payload), str(state)],
        cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    observation = {}
    try:
        wait_file(state / 'node-ready.json')
        observation.update(json.loads((state / 'node-ready.json').read_text()))
        assert not exclude_now(state), '取消前必須真的持有 lease'
        # 僅取消此測試以 Popen 建立且仍存活的 caller；不查詢或操作任何正式程序。
        caller.send_signal(signal.SIGINT)
        stdout, stderr = caller.communicate(timeout=12)
        observation.update(caller_exit=caller.returncode, caller_stderr=stderr,
                           caller_stdout=stdout, work_pending=not (state/'node-work-done').exists(),
                           exclusion_acquired=exclude_now(state))
        (state/'observation.json').write_text(json.dumps(observation,indent=2))
        assert 'KeyboardInterrupt' in stderr, observation
        assert observation['work_pending'], observation
        assert not observation['exclusion_acquired'], observation
        assert observation['inherited'], observation
    finally:
        (state/'release-node').touch()
        if caller.poll() is None:
            caller.communicate(timeout=35)
        if (state/'node-ready.json').exists():
            wait_file(state/'node-work-done',timeout=35)
            deadline = time.monotonic() + 12
            while not exclude_now(state):
                assert time.monotonic() < deadline, 'Node 完成後 lease 未釋放'
                time.sleep(0.02)

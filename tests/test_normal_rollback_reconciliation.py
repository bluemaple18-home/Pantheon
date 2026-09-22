"""正式 maintenance CLI：合成控制面、native lease/process，禁止轉送 launchd。"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time

import pytest
from scripts import pantheon_content_runtime_manifest as runtime

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'scripts/install_agy_gemini_coordinator_launchd.sh'
SOURCE_FILES = ['scripts/install_agy_gemini_coordinator_launchd.sh', 'scripts/pantheon_runtime_activation.py', 'scripts/pantheon_content_runtime_manifest.py']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ident(p):
    s = p.stat()
    return dict(device=s.st_dev, inode=s.st_ino, uid=s.st_uid, mode=s.st_mode & 0o777, nlink=s.st_nlink)


@pytest.fixture
def case(tmp_path):
    home = tmp_path / 'home'
    stage = home / 'Library/LaunchAgents/.pantheon-four-lane-stage'
    (stage / 'backups').mkdir(parents=True)
    roots = [tmp_path / n for n in ('actor', 'queue', 'state', 'logs')]
    for p in roots:
        p.mkdir()
    actor, queue, state, logs = roots
    subprocess.run(['git', 'init', '-q', str(actor)], check=True)
    subprocess.run(['git', '-C', str(actor), '-c', 'user.name=fixture', '-c', 'user.email=fixture@localhost', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
    head = subprocess.check_output(['git', '-C', str(actor), 'rev-parse', 'HEAD'], text=True).strip()
    manifest = runtime.build_manifest(actor_root=actor, queue_root=queue, publisher_state_root=state, log_root=logs, identity='synthetic-maintenance', actor_head=head, python_executable=Path(sys.executable).resolve())
    mp = tmp_path / 'manifest.json'
    runtime.write_manifest(mp, manifest)
    lock = state / 'runtime-work.lock'
    lock.touch(mode=0o600)
    (stage/'manifest-digest').write_text(manifest['manifest_digest'])
    (stage/'generation').write_text(manifest['generation'])
    failure = dict(status='ROLLBACK_FAILED', stage_identity={k:manifest[k] for k in ('manifest_digest','generation')})
    (stage/'failure-receipt.json').write_text(json.dumps(failure))
    (stage/'normal-rollback-drain.json').write_text(json.dumps(dict(status='UNKNOWN_OR_FAILED', error='original', processes={}, groups=[], seen_labels=[])))
    for label in runtime.SERVICE_LABELS:
        env_fields = {'manifest_digest':'MANIFEST_DIGEST','identity':'IDENTITY','runtime_identity_digest':'IDENTITY_DIGEST',
                      'runtime_digest':'CODE_DIGEST','config_version':'CONFIG_VERSION','generation':'GENERATION',
                      'actor_root':'ACTOR_ROOT','queue_root':'QUEUE_ROOT','publisher_state_root':'PUBLISHER_STATE_ROOT',
                      'log_root':'LOG_ROOT','actor_head':'ACTOR_HEAD','python_executable':'PYTHON_EXECUTABLE'}
        environment = {'PANTHEON_RUNTIME_'+suffix:manifest[field] for field,suffix in env_fields.items()}
        environment['PANTHEON_RUNTIME_SERVICE_LABEL']=label
        barrier=state/f"four-lane-activation-{manifest['generation']}.barrier"
        args=[str(Path(sys.executable).resolve()),'-m','scripts.pantheon_content_runtime_manifest','barrier-exec',
              '--barrier',str(barrier),'--expected-digest',manifest['manifest_digest'],'--manifest',str(mp),
              '--service-label',label,'--ready-root',str(stage/'readiness'/manifest['generation']),
              '--timeout','90','--activation-only','--',str(Path(sys.executable).resolve()),'-m','scripts.agy_content_publisher']
        base = dict(Label=label, RunAtLoad=True, StartInterval=300 if 'capacity' in label else 60,
                    ProgramArguments=args, WorkingDirectory=str(actor), EnvironmentVariables=environment)
        (stage/'backups'/f'{label}.plist').write_bytes(plistlib.dumps(base))
        (stage/'backups'/f'{label}.plist').chmod(0o600)
        base['ProgramArguments'].remove('--activation-only')
        (stage/f'{label}.plist').write_bytes(plistlib.dumps(base))
        live=stage.parent/f'{label}.plist'
        live.write_bytes((stage/f'{label}.plist').read_bytes()); live.chmod(0o600)
        (stage/f'{label}.previous_loaded').write_text('0')
    bindir=tmp_path/'bin'; bindir.mkdir()
    control=bindir/'launchctl'
    control.write_text('#!'+sys.executable+'\n'+'''import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
args=sys.argv[1:]
with (root/'calls').open('a') as f:f.write(' '.join(args)+'\\n')
mode=(root/'control-mode').read_text() if (root/'control-mode').exists() else ''
if args[0]=='print-disabled':
 from importlib import import_module
 labels=json.loads((root/'labels.json').read_text())
 print('{')
 if mode=='native-missing':labels=labels[1:]
 for index,label in enumerate(labels):
  value=('disabled' if mode in ('native-disabled','native-missing','native-duplicate') else
         'enabled' if mode=='native-enabled' else
         'unknown' if mode=='native-unknown' else
         'false' if mode=='disabled' else 'true')
  print('"'+label+'" => '+value)
  if mode=='native-duplicate' and index==0:print('"'+label+'" => '+value)
 print('}');sys.exit(0)
if args[0]=='print':sys.exit(2 if mode=='unknown' else 0 if mode=='loaded' else 113)
raise SystemExit('MUTATION FORBIDDEN: no native forwarding')
''')
    control.chmod(0o700)
    (tmp_path/'labels.json').write_text(json.dumps(list(runtime.SERVICE_LABELS)))
    binding=dict(schema_version=1, purpose='fixture', source_root=str(ROOT), source_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(), source_files={n:sha(ROOT/n) for n in SOURCE_FILES}, actor_root=str(actor), actor_head=head, manifest_path=str(mp), manifest_sha256=sha(mp), manifest_digest=manifest['manifest_digest'], stage_path=str(stage), stage_files={str(p.relative_to(stage)):sha(p) for p in stage.rglob('*') if p.is_file() and p.name!='normal-rollback-drain.json'}, drain_sha256=sha(stage/'normal-rollback-drain.json'), lease=ident(lock), control={'path':str(control),'sha256':sha(control),**ident(control)})
    bp=tmp_path/'binding.json'; bp.write_text(json.dumps(binding))
    env={**os.environ, 'PANTHEON_USER_HOME_DIR':str(home), 'PANTHEON_PYTHON_PATH':sys.executable, 'PATH':str(bindir)+':'+os.environ['PATH']}
    return dict(root=tmp_path, stage=stage, binding=binding, bp=bp, env=env, lock=lock, manifest=manifest)


def cli(c):
    result=subprocess.run(['/bin/bash',str(INSTALLER),'--reconcile-normal-rollback',str(c['bp'])],env=c['env'],cwd=ROOT,text=True,capture_output=True,timeout=30)
    with (c['root']/'cli-results.jsonl').open('a') as f:
        f.write(json.dumps({'code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})+'\n')
    return result


def snapshot(c):
    return {str(p): (p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ino) for p in c['stage'].parent.rglob('*') if p.is_file()}


def test_cli_accepts_native_disabled_readback(case):
    """正式 CLI 必須接受 macOS launchctl 的原生 disabled token。"""
    c=case
    (c['root']/'control-mode').write_text('native-disabled')
    result=cli(c)
    assert result.returncode==0,result.stderr
    assert (c['stage']/'normal-rollback-reconciliation.json').exists()


@pytest.mark.parametrize('mode', ['native-enabled','native-missing','native-duplicate','native-unknown'])
def test_cli_rejects_non_disabled_native_readback(case,mode):
    """enabled、缺列、重複列與未知 token 都必須 fail-closed。"""
    c=case
    (c['root']/'control-mode').write_text(mode)
    before=snapshot(c)
    result=cli(c)
    assert result.returncode!=0 and 'disabled identity drift' in result.stderr,result.stderr
    assert snapshot(c)==before


def save_binding(c):
    c['bp'].write_text(json.dumps(c['binding']))


@pytest.mark.parametrize('scenario', ['short-process','missing-cwd','mixed'])
def test_r1_native_churn_idle(case, scenario):
    c=case
    owned=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],cwd=c['manifest']['queue_root'],start_new_session=True)
    try:
        birth,ppid,pgid=_birth(owned.pid)
        drain=c['stage']/'normal-rollback-drain.json'
        drain.write_text(json.dumps(dict(status='UNKNOWN_OR_FAILED',error='original',
            processes={str(owned.pid):dict(birth=birth,ppid=ppid,pgid=pgid)},groups=[pgid],seen_labels=[])))
        c['binding']['drain_sha256']=sha(drain);save_binding(c)
    finally:
        owned.terminate();owned.wait(timeout=5)
    script="""import os,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1]);scenario=sys.argv[2];count=0;end=time.monotonic()+120
while time.monotonic()<end and not (root/'churn-stop').exists():
 commands=['/usr/bin/true','/bin/pwd']*4 if scenario=='mixed' else ['/usr/bin/true' if scenario=='short-process' else '/bin/pwd']
 children=[subprocess.Popen([command],stdout=subprocess.DEVNULL) for command in commands]
 assert all(child.wait()==0 for child in children)
 count+=len(children)
 (root/'churn-counter.tmp').write_text(str(count))
 os.replace(root/'churn-counter.tmp',root/'churn-counter')
 (root/'churn-ready').touch()
"""
    churn=subprocess.Popen([sys.executable,'-c',script,str(c['root']),scenario],cwd='/private/tmp')
    churn_receipt={'scenario':scenario,'pid':churn.pid,'samples':[],'cli_attempts':0}
    def sample(phase):
        item={'phase':phase,'monotonic':time.monotonic(),'completed_children':int((c['root']/'churn-counter').read_text()),'poll':churn.poll()}
        churn_receipt['samples'].append(item)
        assert item['poll'] is None,item
        return item['completed_children']
    if scenario in ('missing-cwd', 'mixed'):
        inject=c['root']/'missing-cwd';inject.mkdir()
        (inject/'sitecustomize.py').write_text('''import os,subprocess
from pathlib import Path
original=subprocess.run
def run(argv,*a,**kw):
 result=original(argv,*a,**kw)
 if argv[0]=='/usr/sbin/lsof' and result.returncode==0:
  lines=[];skip=False
  for line in result.stdout.splitlines():
   if line.startswith('p'):skip=line=='p'+os.environ['S3_UNRELATED_PID']
   if skip:Path(os.environ['S3_MISSING_HIT']).touch()
   else:lines.append(line)
  result.stdout='\\n'.join(lines)+'\\n'
 return result
subprocess.run=run
''')
        c['env'].update(PYTHONPATH=str(inject)+':'+str(ROOT),S3_UNRELATED_PID=str(churn.pid),S3_MISSING_HIT=str(c['root']/'missing-hit'))
    try:
        deadline=time.monotonic()+5
        while not (c['root']/'churn-ready').exists() and time.monotonic()<deadline:
            assert churn.poll() is None
            time.sleep(.01)
        assert (c['root']/'churn-ready').exists()
        churn_receipt['ready']=True
        before=(c['stage']/'failure-receipt.json').read_bytes()
        first_count=sample('before-reconcile')
        churn_receipt['cli_attempts']+=1
        result=cli(c)
        assert sample('after-reconcile')>first_count
        assert result.returncode==0,result.stderr
        assert (c['stage']/'failure-receipt.json').read_bytes()==before
        first=snapshot(c)
        second_count=sample('before-idle')
        churn_receipt['cli_attempts']+=1
        result=cli(c)
        assert sample('after-idle')>second_count
        assert result.returncode==0,result.stderr
        assert 'IDLE' in result.stdout
        assert snapshot(c)==first
        calls=(c['root']/'calls').read_text()
        assert 'bootout' not in calls and 'bootstrap' not in calls
        if scenario != 'short-process':assert (c['root']/'missing-hit').exists()
    finally:
        (c['root']/'churn-stop').touch()
        try:
            churn.wait(timeout=5)
        except subprocess.TimeoutExpired:
            churn.terminate();churn.wait(timeout=5)
        churn_receipt['cleanup_exit']=churn.returncode
        (c['root']/'churn-receipt.json').write_text(json.dumps(churn_receipt,indent=2))
    assert churn.returncode==0


def test_r2_r3_shared_child_busy_then_terminal(case):
    c=case
    code='import fcntl,os,sys,time; f=os.open(sys.argv[1],os.O_RDWR); fcntl.flock(f,fcntl.LOCK_SH); print("ready",flush=True); time.sleep(30)'
    child=subprocess.Popen([sys.executable,'-c',code,str(c['lock'])],stdout=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='ready'
        before=snapshot(c); result=cli(c)
        assert result.returncode!=0 and 'BUSY' in result.stderr,result.stderr
        assert snapshot(c)==before
        assert not (c['root']/'calls').exists()
    finally:
        child.terminate();child.wait(timeout=5)
    result=cli(c); assert result.returncode==0,result.stderr


@pytest.mark.parametrize('drift', ['source','actor','manifest','stage','failure','drain','lease','control','loaded','unknown','disabled'])
def test_r4_identity_zero_mutation(case, drift):
    c=case; b=c['binding'];stage=c['stage']
    expected=drift
    if drift=='source':b['source_head']='0'*40
    elif drift=='actor':b['actor_head']='0'*40
    elif drift=='manifest':b['manifest_sha256']='0'*64
    elif drift=='stage':(stage/'generation').write_text('wrong')
    elif drift=='failure':(stage/'failure-receipt.json').write_text('{}')
    elif drift=='drain':(stage/'normal-rollback-drain.json').write_text('{}')
    elif drift=='lease':b['lease']['inode']+=1
    elif drift=='control':b['control']['sha256']='0'*64
    else:(c['root']/'control-mode').write_text(drift)
    save_binding(c);before=snapshot(c);result=cli(c)
    assert result.returncode!=0,result.stdout
    assert expected.lower() in result.stderr.lower(),result.stderr
    assert snapshot(c)==before


@pytest.mark.parametrize('boundary', ['archive','journal','restore-before','restore-after','receipt-write','receipt-chmod','receipt-mv'])
def test_r5_fault_resume(case,boundary):
    c=case
    # sitecustomize 只在 fixture Python 注入，產品不提供 fault bypass。
    inject=c['root']/'inject';inject.mkdir()
    (inject/'sitecustomize.py').write_text('''import os,pathlib
root=pathlib.Path(os.environ['S3_FAULT_ROOT']);kind=os.environ['S3_FAULT']; orig_replace=os.replace;orig_chmod=os.chmod;orig_open=pathlib.Path.open
hit=root/'fault-hit'
def fail():
 hit.write_text(kind);raise OSError('S3 injected '+kind)
def replace(src,dst,*a,**k):
 name=str(dst)
 if kind=='archive' and name.endswith('normal-rollback-drain.original.json'):fail()
 if kind=='journal' and name.endswith('normal-rollback-drain.json'):fail()
 if kind=='restore-before' and name.endswith('.plist') and 'LaunchAgents/' in name and 'stage' not in name:fail()
 result=orig_replace(src,dst,*a,**k)
 if kind=='restore-after' and name.endswith('.plist') and 'LaunchAgents/' in name and 'stage' not in name:fail()
 return result
os.replace=replace
def chmod(p,*a,**k):
 if kind=='receipt-chmod' and 'normal-rollback-reconciliation.json.tmp' in str(p):fail()
 return orig_chmod(p,*a,**k)
os.chmod=chmod
def fopen(p,mode='r',*a,**k):
 if kind=='receipt-write' and 'normal-rollback-reconciliation.json.tmp' in str(p) and any(flag in mode for flag in ('w','x')):fail()
 return orig_open(p,mode,*a,**k)
pathlib.Path.open=fopen
if kind=='receipt-mv':
 def receipt_replace(src,dst,*a,**k):
  if str(dst).endswith('normal-rollback-reconciliation.json'):fail()
  return replace(src,dst,*a,**k)
 os.replace=receipt_replace
''')
    old_failure=(c['stage']/'failure-receipt.json').read_bytes();old_drain=(c['stage']/'normal-rollback-drain.json').read_bytes()
    c['env'].update(PYTHONPATH=str(inject)+':'+str(ROOT),S3_FAULT=boundary,S3_FAULT_ROOT=str(c['root']))
    result=cli(c)
    assert result.returncode!=0,result.stdout
    assert (c['root']/'fault-hit').read_text()==boundary
    restored={p:p.stat().st_mtime_ns for p in c['stage'].parent.glob('*.plist') if p.read_bytes()==(c['stage']/'backups'/p.name).read_bytes()}
    c['env'].pop('S3_FAULT');c['env'].pop('S3_FAULT_ROOT');c['env'].pop('PYTHONPATH')
    result=cli(c);assert result.returncode==0,result.stderr
    assert all(p.stat().st_mtime_ns==mtime for p,mtime in restored.items())
    assert (c['stage']/'failure-receipt.json').read_bytes()==old_failure
    assert (c['stage']/'normal-rollback-drain.original.json').read_bytes()==old_drain
    before=snapshot(c);result=cli(c);assert result.returncode==0,result.stderr
    assert snapshot(c)==before


def _birth(pid):
    """使用相同 Darwin ABI 取得 native PID birth；不偽造程序存活。"""
    import ast
    tree=ast.parse(INSTALLER.read_text().split("normal_activation_boundary() {",1)[1].split("<<'PY'\n",1)[1].split('\nPY\n}',1)[0])
    selected=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.ClassDef) and node.name=='Birth']
    ns={};exec(compile(ast.Module(body=selected,type_ignores=[]),str(INSTALLER),'exec'),ns)
    import ctypes
    value=ns['Birth']();lib=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
    assert lib.proc_pidinfo(pid,3,0,ctypes.byref(value),ctypes.sizeof(value))==ctypes.sizeof(value)
    return [value.sec,value.usec],value.ppid,value.pgid


@pytest.mark.parametrize('kind', ['nonlease-pgid','pid-reuse','birth-unknown'])
def test_r4_native_known_cohort(case,kind):
    c=case
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],cwd='/private/tmp',start_new_session=True)
    try:
        birth,ppid,pgid=_birth(child.pid)
        observed_birth=None if kind=='birth-unknown' else [birth[0],birth[1]+1] if kind=='pid-reuse' else birth
        record=dict(status='UNKNOWN_OR_FAILED',error='original',processes={str(child.pid):dict(birth=observed_birth,ppid=ppid,pgid=pgid)},groups=[pgid],seen_labels=[])
        drain=c['stage']/'normal-rollback-drain.json';drain.write_text(json.dumps(record))
        c['binding']['drain_sha256']=sha(drain);save_binding(c)
        before=snapshot(c);result=cli(c)
        assert result.returncode!=0,result.stdout
        assert ('not terminal' if kind=='nonlease-pgid' else 'PID reuse') in result.stderr,result.stderr
        assert snapshot(c)==before
    finally:
        child.terminate();child.wait(timeout=5)
    # 同一 binding/known cohort，真 terminal 後不需 full UID 收斂。
    result=cli(c);assert result.returncode==0,result.stderr


def test_r4_observer_unknown(case):
    c=case;inject=c['root']/'observer';inject.mkdir()
    (inject/'sitecustomize.py').write_text('''import subprocess
original=subprocess.run
def run(argv,*a,**kw):
 if argv[0]=='/usr/sbin/lsof':return subprocess.CompletedProcess(argv,1,'','permission denied fixture')
 return original(argv,*a,**kw)
subprocess.run=run
''')
    c['env']['PYTHONPATH']=str(inject)+':'+str(ROOT)
    before=snapshot(c);result=cli(c)
    assert result.returncode!=0 and 'runtime cwd observation UNKNOWN' in result.stderr,result.stderr
    assert snapshot(c)==before


def test_r4_backup_wrapper_guard(case):
    c=case;label=runtime.SERVICE_LABELS[0];p=c['stage']/'backups'/f'{label}.plist'
    payload=plistlib.loads(p.read_bytes());payload['ProgramArguments'][7]='0'*64
    p.write_bytes(plistlib.dumps(payload));c['binding']['stage_files'][f'backups/{label}.plist']=sha(p);save_binding(c)
    before=snapshot(c);result=cli(c)
    assert result.returncode!=0 and 'backup wrapper' in result.stderr,result.stderr
    assert snapshot(c)==before


def test_r4_lease_inode_drift_during_readback(case):
    c=case;inject=c['root']/'inode';inject.mkdir()
    (inject/'sitecustomize.py').write_text('''import os,subprocess
from pathlib import Path
original=subprocess.run
def run(argv,*a,**kw):
 result=original(argv,*a,**kw)
 if len(argv)>1 and argv[1]=='print-disabled':
  p=Path(os.environ['S3_LOCK']);p.unlink();p.touch(mode=0o600)
 return result
subprocess.run=run
''')
    c['env'].update(PYTHONPATH=str(inject)+':'+str(ROOT),S3_LOCK=str(c['lock']))
    before=snapshot(c);result=cli(c)
    assert result.returncode!=0 and 'lease identity drift' in result.stderr,result.stderr
    assert snapshot(c)==before


@pytest.mark.parametrize('boundary', ['archive','journal','restore','receipt'])
def test_r5_sigkill_after_atomic_publish(case,boundary):
    c=case;inject=c['root']/'crash';inject.mkdir()
    (inject/'sitecustomize.py').write_text('''import os,signal
from pathlib import Path
original=os.replace
kind=os.environ['S3_CRASH'];root=Path(os.environ['S3_ROOT'])
def replace(src,dst,*a,**kw):
 result=original(src,dst,*a,**kw);name=str(dst)
 hit=(kind=='archive' and name.endswith('normal-rollback-drain.original.json') or
      kind=='journal' and name.endswith('normal-rollback-drain.json') or
      kind=='restore' and name.endswith('.plist') and 'LaunchAgents/' in name and 'stage' not in name or
      kind=='receipt' and name.endswith('normal-rollback-reconciliation.json'))
 if hit:
  (root/'crash-hit').write_text(kind);os.kill(os.getpid(),signal.SIGKILL)
 return result
os.replace=replace
''')
    original=(c['stage']/'normal-rollback-drain.json').read_bytes()
    failure=(c['stage']/'failure-receipt.json').read_bytes()
    c['env'].update(PYTHONPATH=str(inject)+':'+str(ROOT),S3_CRASH=boundary,S3_ROOT=str(c['root']))
    result=cli(c);assert result.returncode!=0,result.stdout
    assert (c['root']/'crash-hit').read_text()==boundary
    restored={p:p.stat().st_ino for p in c['stage'].parent.glob('*.plist') if p.read_bytes()==(c['stage']/'backups'/p.name).read_bytes()}
    c['env'].pop('PYTHONPATH');c['env'].pop('S3_CRASH');c['env'].pop('S3_ROOT')
    result=cli(c);assert result.returncode==0,result.stderr
    assert all(p.stat().st_ino==ino for p,ino in restored.items())
    assert (c['stage']/'normal-rollback-drain.original.json').read_bytes()==original
    assert (c['stage']/'failure-receipt.json').read_bytes()==failure
    before=snapshot(c);result=cli(c);assert result.returncode==0,result.stderr
    assert snapshot(c)==before


def test_r5_control_child_retains_ex_after_parent_death(case):
    import signal
    c=case;control=Path(c['binding']['control']['path'])
    source=control.read_text().replace("args=sys.argv[1:]", """args=sys.argv[1:]
if (root/'pause-control').exists():
 import time
 (root/'control-ready').touch()
 time.sleep(30)
""")
    control.write_text(source);c['binding']['control']['sha256']=sha(control);save_binding(c)
    (c['root']/'pause-control').touch()
    before=snapshot(c)
    output=(c['root']/'killed-parent.log').open('w')
    parent=subprocess.Popen(['/bin/bash',str(INSTALLER),'--reconcile-normal-rollback',str(c['bp'])],env=c['env'],cwd=ROOT,stdout=output,stderr=output,start_new_session=True)
    try:
        deadline=time.monotonic()+5
        while not (c['root']/'control-ready').exists() and time.monotonic()<deadline:time.sleep(.01)
        assert (c['root']/'control-ready').exists()
        parent.kill();parent.wait(timeout=5)
        result=cli(c)
        assert result.returncode!=0 and 'BUSY' in result.stderr,result.stderr
        assert snapshot(c)==before
    finally:
        # 只 signal 此 fixture 自建 session/PGID。
        try:os.killpg(parent.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        parent.wait(timeout=5);output.close()
    (c['root']/'pause-control').unlink()
    import fcntl
    fd=os.open(c['lock'],os.O_RDWR)
    try:
        deadline=time.monotonic()+5
        while True:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                assert time.monotonic()<deadline
                time.sleep(.01)
    finally:os.close(fd)
    result=cli(c);assert result.returncode==0,result.stderr


def test_normal_unknown_boundary_remains_fail_closed(case):
    c=case
    source=INSTALLER.read_text()
    body='normal_activation_boundary() {'+source.split('normal_activation_boundary() {',1)[1].split('\nPY\n}',1)[0]+'\nPY\n}\n'
    import shlex
    settings=dict(PYTHON_BIN=sys.executable,STAGE_DIR=str(c['stage']),BARRIER_TIMEOUT_SECONDS='30',USER_ID=str(os.getuid()),RUNTIME_MANIFEST_FILE=c['binding']['manifest_path'])
    script='\n'.join(k+'='+shlex.quote(v) for k,v in settings.items())+'\n'+body+'normal_activation_boundary drain\n'
    result=subprocess.run(['/bin/bash'],input=script,text=True,capture_output=True,env=c['env'],cwd=ROOT)
    assert result.returncode!=0
    assert 'prior normal process evidence is unresolved' in result.stderr
    assert not (c['root']/'calls').exists()


@pytest.mark.parametrize('drift',['live','receipt','journal'])
def test_r4_completed_receipt_requires_actual_state(case,drift):
    c=case;result=cli(c);assert result.returncode==0,result.stderr
    if drift=='live':
        label=runtime.SERVICE_LABELS[0]
        (c['stage'].parent/f'{label}.plist').write_bytes((c['stage']/f'{label}.plist').read_bytes())
    elif drift=='receipt':(c['stage']/'normal-rollback-reconciliation.json').write_text('{}')
    else:(c['stage']/'normal-rollback-drain.json').write_bytes((c['stage']/'normal-rollback-drain.original.json').read_bytes())
    before=snapshot(c);result=cli(c)
    assert result.returncode!=0 and 'receipt' in result.stderr,result.stderr
    assert snapshot(c)==before


def test_r4_native_known_pgid_nonlease_descendant(case):
    import signal
    c=case
    code="import subprocess,sys,time; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print(child.pid,flush=True); time.sleep(.5)"
    parent=subprocess.Popen([sys.executable,'-c',code],cwd='/private/tmp',stdout=subprocess.PIPE,text=True,start_new_session=True)
    try:
        child_pid=int(parent.stdout.readline())
        birth,ppid,pgid=_birth(parent.pid)
        record=dict(status='UNKNOWN_OR_FAILED',error='original',processes={str(parent.pid):dict(birth=birth,ppid=ppid,pgid=pgid)},groups=[pgid],seen_labels=[])
        drain=c['stage']/'normal-rollback-drain.json';drain.write_text(json.dumps(record))
        c['binding']['drain_sha256']=sha(drain);save_binding(c)
        parent.wait(timeout=5)
        assert _birth(child_pid)[2]==pgid
        before=snapshot(c);result=cli(c)
        assert result.returncode!=0 and 'not terminal' in result.stderr,result.stderr
        assert snapshot(c)==before
    finally:
        try:os.killpg(parent.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        parent.wait(timeout=5)
    # 自建 descendant terminal 後才可恢復，同一 binding 不重寫原 evidence。
    deadline=time.monotonic()+5
    while True:
        try:os.kill(child_pid,0)
        except ProcessLookupError:break
        assert time.monotonic()<deadline
        time.sleep(.01)
    result=cli(c);assert result.returncode==0,result.stderr


def test_system_control_identity_is_read_only_and_root_specific(monkeypatch):
    """只讀系統 binary，不執行 native launchctl，也不放寬 evidence owner。"""
    from scripts import pantheon_runtime_activation as activation
    path=Path('/bin/launchctl')
    control={'path':str(path),'sha256':sha(path),**ident(path)}
    assert control['uid']==0 and os.getuid()!=0
    monkeypatch.setenv('PATH','/bin:/usr/bin')
    before=(path.stat().st_ino,path.stat().st_mtime_ns,sha(path))
    activation.maintenance_control_identity(control,'production')
    assert (path.stat().st_ino,path.stat().st_mtime_ns,sha(path))==before
    with pytest.raises(activation.RuntimeActivationError,match='file identity'):
        activation._exact_bytes(path)
    for field,value in [('uid',os.getuid()),('sha256','0'*64),('inode',control['inode']+1)]:
        with pytest.raises(activation.RuntimeActivationError,match='control identity'):
            activation.maintenance_control_identity({**control,field:value},'production')


@pytest.mark.parametrize('mode',['restore','finish'])
def test_direct_helper_requires_reconciled_archive_journal(case,mode):
    c=case
    if mode=='finish':
        for label in runtime.SERVICE_LABELS:
            (c['stage'].parent/f'{label}.plist').write_bytes((c['stage']/'backups'/f'{label}.plist').read_bytes())
    fd=os.open(c['lock'],os.O_RDWR)
    try:
        args=[sys.executable,'-m','scripts.pantheon_runtime_activation',mode,str(c['bp'])]
        if mode=='restore':args.append(runtime.SERVICE_LABELS[0])
        before=snapshot(c)
        result=subprocess.run(args,env={**c['env'],'PANTHEON_MAINTENANCE_LEASE_FD':str(fd)},pass_fds=(fd,),cwd=ROOT,text=True,capture_output=True)
        (c['root']/'direct-helper.json').write_text(json.dumps(dict(mode=mode,code=result.returncode,stdout=result.stdout,stderr=result.stderr)))
        assert result.returncode!=0,result.stdout
        assert 'reconciled archive/journal required' in result.stderr,result.stderr
        assert snapshot(c)==before
        assert not (c['root']/'calls').exists()
    finally:os.close(fd)


def test_previous_loaded_zero_contract(case):
    c=case;name=runtime.SERVICE_LABELS[0]+'.previous_loaded'
    (c['stage']/name).write_text('1')
    c['binding']['stage_files'][name]=sha(c['stage']/name);save_binding(c)
    before=snapshot(c);result=cli(c)
    assert result.returncode!=0 and 'previous_loaded must be 0' in result.stderr,result.stderr
    assert snapshot(c)==before
    assert not (c['root']/'calls').exists()


def test_nonfixture_prepare_has_no_new_g8_mapping_or_native_mutation(case,monkeypatch,capsys):
    """nonfixture 分支只讀真系統 binary；控制面 readback 全 mock，不呼叫 native。"""
    from scripts import pantheon_runtime_activation as activation
    c=case;path=Path('/bin/launchctl')
    c['binding'].update(purpose='production',control={'path':str(path),'sha256':sha(path),**ident(path)})
    save_binding(c)
    monkeypatch.setenv('PATH','/bin:/usr/bin')
    monkeypatch.setenv('PANTHEON_USER_HOME_DIR',c['env']['PANTHEON_USER_HOME_DIR'])
    # 即使外部帶著既有 release edge，也不可拿不存在的 maintenance mapping 阻擋。
    monkeypatch.setenv('PANTHEON_RELEASE_NEXT_EDGE','fixture-no-maintenance-edge')
    calls=[];original=subprocess.run
    def readonly(argv,*args,**kwargs):
        if argv[0] in ('/usr/bin/git','git'):return original(argv,*args,**kwargs)
        assert argv[0]=='/bin/launchctl',f'unexpected new gate/effector: {argv}'
        calls.append(argv)
        if argv[1]=='print-disabled':
            return subprocess.CompletedProcess(argv,0,'\n'.join('"'+label+'" => true' for label in runtime.SERVICE_LABELS),'')
        assert argv[1]=='print',f'native mutation forbidden: {argv}'
        return subprocess.CompletedProcess(argv,113,'','')
    monkeypatch.setattr(activation.subprocess,'run',readonly)
    fd=os.open(c['lock'],os.O_RDWR)
    try:
        monkeypatch.setenv('PANTHEON_MAINTENANCE_LEASE_FD',str(fd))
        monkeypatch.setattr(sys,'argv',['runtime_activation','prepare',str(c['bp'])])
        before=snapshot(c);control_before=(path.stat().st_ino,path.stat().st_mtime_ns,sha(path))
        assert activation._maintenance_main()==0
        assert 'STAGE_DIR=' in capsys.readouterr().out
        assert len(calls)==8 and {argv[1] for argv in calls}=={'print-disabled','print'}
        assert snapshot(c)==before
        assert (path.stat().st_ino,path.stat().st_mtime_ns,sha(path))==control_before
    finally:os.close(fd)

from unittest.mock import patch
"""真本機 Git＋真 readiness wrapper；launchd/ps 為受控 adapter，非正式部署證據。"""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import os
import plistlib
import subprocess
import sys
import time

import pytest

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_manifest as runtime
from scripts import pantheon_content_runtime_promotion as promotion
from scripts import pantheon_runtime_activation as activation

ROOT=Path(__file__).resolve().parents[1]
PAIR=('com.pantheon.agy-content-publisher','com.pantheon.content-capacity-guard')


def git(root,*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(root),*args],stderr=subprocess.PIPE,text=True).strip()


def commit(root,text):
    git(root,'add','.');git(root,'-c','user.name=Isolated Probe','-c','user.email=probe@localhost','commit','-qm',text)
    return git(root,'rev-parse','HEAD')


def write_private(path,data):
    path.write_bytes(data);path.chmod(0o600)


def plist_for(m,label,manifest_path,ready):
    fields=runtime.receipt_for_label(m,label)
    mapping={'service_label':'SERVICE_LABEL','identity':'IDENTITY','manifest_digest':'MANIFEST_DIGEST',
        'runtime_identity_digest':'IDENTITY_DIGEST','runtime_digest':'CODE_DIGEST','config_version':'CONFIG_VERSION',
        'generation':'GENERATION','actor_root':'ACTOR_ROOT','queue_root':'QUEUE_ROOT',
        'publisher_state_root':'PUBLISHER_STATE_ROOT','log_root':'LOG_ROOT','actor_head':'ACTOR_HEAD',
        'python_executable':'PYTHON_EXECUTABLE','uv_executable':'UV_EXECUTABLE'}
    env={'PANTHEON_RUNTIME_'+v:fields[k] for k,v in mapping.items() if k in fields}
    env.update(PANTHEON_FORMAL_RUNTIME='1',PANTHEON_RUNTIME_MANIFEST=str(manifest_path))
    barrier=Path(m['publisher_state_root'])/('four-lane-activation-'+m['generation']+'.barrier')
    inner=[m['python_executable'],'-m','scripts.agy_content_publisher' if label==PAIR[0] else 'scripts.pantheon_content_capacity_guard',
        '--repo-root',m['actor_root'],'--queue-root',m['queue_root'],'--state-root',m['publisher_state_root']]
    if label==PAIR[0]:
        inner+=['--max-runs','1','--include-rewrites','--continuous-tick','--push',
            '--expected-repo-root',m['actor_root'],'--expected-queue-root',m['queue_root'],
            '--expected-state-root',m['publisher_state_root'],'--expected-runtime-sha',m['actor_head'],
            '--expected-runtime-digest',m['runtime_digest'],'--expected-push-mode','push']
    else:
        inner=[m['python_executable'],'-m','scripts.pantheon_content_capacity_guard',
            '--queue-root',m['queue_root'],'--publisher-root',m['publisher_state_root'],
            '--log-root',m['log_root'],'--state-file',str(Path(m['queue_root'])/'capacity-guard-state.json'),'check']
    args=[m['python_executable'],'-m','scripts.pantheon_content_runtime_manifest','barrier-exec',
        '--barrier',str(barrier),'--expected-digest',m['manifest_digest'],'--manifest',str(manifest_path),
        '--service-label',label,'--ready-root',str(ready),'--timeout','180','--',*inner]
    return {'Label':label,'ProgramArguments':args,'EnvironmentVariables':env,'WorkingDirectory':m['actor_root'],
        'StartInterval':60 if label==PAIR[0] else 300,'RunAtLoad':True}


class HybridHost:
    """Git/manifest 使用原生 bounded runner；兩個 wrapper 為真，payload 是無副作用 sentinel。"""
    def __init__(self,request,root,mode):
        self.request=request;self.root=root;self.mode=mode;self.loaded={x:x in PAIR for x in runtime.SERVICE_LABELS}
        self.processes={};self.commands=[];self.push_under_ex=[];self.native=promotion._PublisherGuardCommands(request)
        self.injected=False
    def __call__(self,argv,*,timeout):
        self.commands.append(list(argv));self.native.deadline=time.monotonic()+timeout
        if argv[0] in ('/bin/launchctl','launchctl'):
            action=argv[1]
            if action=='print':
                label=argv[2].split('/',2)[2]
                if not self.loaded[label]:return subprocess.CompletedProcess(argv,113,'','isolated absent')
                p=self.processes.get(label);pid=f' pid = {p.pid}\n' if p and p.poll() is None else ''
                state='running' if pid else 'not running';exitcode=p.returncode if p and p.poll() is not None else 0
                text=f'{argv[2]} = {{\n path = {self.request.launch_agents_dir/(label+".plist")}\n state = {state}\n runs = 1\n last exit code = {exitcode}\n{pid}}}\n'
                return subprocess.CompletedProcess(argv,0,text,'')
            if action=='bootout':
                label=argv[2].split('/',2)[2];assert label in PAIR
                p=self.processes.get(label)
                if p and p.poll() is None:p.kill();p.wait(timeout=5)
                self.loaded[label]=False;return subprocess.CompletedProcess(argv,0,'','')
            if action=='bootstrap':
                d=plistlib.loads(Path(argv[3]).read_bytes());label=d['Label'];assert label in PAIR
                mark=self.root/(label+'.sentinel')
                args=d['ProgramArguments'];sep=args.index('--')
                # 真 wrapper 的標準正常路徑，最後 payload 換成有限 sentinel；不聲稱驗過文章/Guard business payload。
                payload=[d['EnvironmentVariables']['PANTHEON_RUNTIME_PYTHON_EXECUTABLE'],'-B','-c',
                    f'from pathlib import Path; Path({str(mark)!r}).write_text("done")']
                env={**os.environ,**d['EnvironmentVariables'],'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':d['WorkingDirectory']}
                p=subprocess.Popen(args[:sep+1]+payload,cwd=d['WorkingDirectory'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,start_new_session=True)
                self.processes[label]=p;self.loaded[label]=True
                return subprocess.CompletedProcess(argv,0,'','')
            raise AssertionError(argv)
        if Path(argv[0]).name=='ps':
            # 模擬 launchd 的 process table；真受控 wrapper 由 cleanup/wait 另核對終止，非全主機 lineage 證據。
            return subprocess.CompletedProcess(argv,0,'','')
        is_push=argv[0]=='/usr/bin/git' and 'push' in argv
        if is_push:self.push_under_ex.append(runtime._SHUTDOWN_LEASE.get() is not None)
        result=self.native(argv)
        if is_push and self.mode=='lost_ack' and not self.injected:
            self.injected=True;raise subprocess.TimeoutExpired(argv,timeout)
        return result
    def cleanup(self):
        for p in self.processes.values():
            if p.poll() is None:p.kill()
            p.wait(timeout=5)


@pytest.mark.parametrize('mode',['success','reject','lost_ack','publish_advance','publish_lightweight','publish_tag_wrong_commit','publish_no_ledger','publish_code_drift','publish_tag_missing','release_gap','cleanup_gap'])
def test_real_git_source_outcome_and_real_wrapper_pair(tmp_path,mode):
    started=time.time()
    source=tmp_path/'source';source.mkdir();bare=tmp_path/'remote.git'
    subprocess.run(['/usr/bin/git','init','--bare','--template=','--initial-branch=main',str(bare)],check=True,capture_output=True)
    git(source,'init','--template=','--initial-branch=main')
    (source/'epoch.txt').write_text('before');before=commit(source,'before')
    git(source,'remote','add','origin',str(bare));git(source,'push','origin','HEAD:refs/heads/main')
    old_actor=tmp_path/'old-actor';subprocess.run(['/usr/bin/git','clone','--no-local','--template=',str(source),str(old_actor)],check=True,capture_output=True)
    scripts=source/'scripts';scripts.mkdir();(scripts/'__init__.py').write_text('')
    for name in ['pantheon_content_runtime_manifest.py','pantheon_runtime_activation.py','pantheon_content_runtime_promotion.py']:
        (scripts/name).write_bytes((ROOT/'scripts'/name).read_bytes())
    (source/'epoch.txt').write_text('target');target=commit(source,'target')
    actor=tmp_path/'actor';subprocess.run(['/usr/bin/git','clone','--no-local','--template=',str(source),str(actor)],check=True,capture_output=True);git(actor,'remote','set-url','origin',str(bare))
    queue=tmp_path/'queue';state=tmp_path/'state';logs=tmp_path/'logs';launch=tmp_path/'launch';stage=tmp_path/'stage'
    for p in [queue,state,logs,launch,stage]:p.mkdir()
    (state/'runtime-work.lock').touch(mode=0o600)
    common=dict(queue_root=queue,publisher_state_root=state,log_root=logs,python_executable=Path(sys.executable).resolve(),uv_executable=Path('/usr/bin/true'))
    old=runtime.build_manifest(actor_root=old_actor,identity='synthetic-old',generation='old',actor_head=before,**common)
    new=runtime.build_manifest(actor_root=actor,identity='synthetic-target',generation='target',actor_head=target,activation_scope='publisher_guard',**common)
    old_path=tmp_path/'old.json';new_path=tmp_path/'new.json';runtime.write_manifest(old_path,old);runtime.write_manifest(new_path,new)
    ready=tmp_path/'ready';plists=[]
    for label in runtime.SERVICE_LABELS:
        write_private(launch/(label+'.plist'),plistlib.dumps({'Label':label,'previous':True}))
        if label in PAIR:
            path=stage/(label+'.plist');write_private(path,plistlib.dumps(plist_for(new,label,new_path,ready)));plists.append(path)
    five={p:p.read_bytes() for p in launch.iterdir() if p.stem not in PAIR};old_bytes=old_path.read_bytes()
    if mode=='reject':
        hook=bare/'hooks/pre-receive';hook.parent.mkdir(exist_ok=True);hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
    # 僅測既有 gate wiring 的 unit 資料；不冒充正式 Rule24 容量取證。
    capacity_path=tmp_path/'unit-capacity.json'
    capacity={'schema_version':1,'regression_id':'REG-PANTHEON-CAPACITY-WRITE-CYCLES-001',
        'status':'PASS','mode':'bounded-synthetic-dry-run','cycles':[{'rss_available':True,'swap_available':True}]*2,
        'reclamation':{'bytes_before':1,'bytes_after':0},'stop_loss':{'status':'STOPPED','triggered':True,'remaining_loaded':[],'cross_project_deletions':[]},
        'evidence_scope':'unit schema wiring only, not production capacity evidence'}
    write_private(capacity_path,json.dumps(capacity).encode())
    request=promotion.PublisherGuardRequest(source_repo=source,expected_remote=str(bare),remote_ref='refs/heads/main',
        before_sha=before,target_sha=target,old_manifest_path=old_path,new_manifest_path=new_path,staged_plists=tuple(plists),
        launch_agents_dir=launch,transaction_root=tmp_path/'txn',lock_budget_seconds=30,command_timeout_seconds=5,health_timeout_seconds=5,push_source=True,capacity_receipt_path=capacity_path,
        capacity_receipt_digest=hashlib.sha256(capacity_path.read_bytes()).hexdigest())
    host=HybridHost(request,tmp_path,mode)
    try:
        planned=promotion.plan_publisher_guard(request,runner=host);digest=planned['plan_digest']
        promotion.prepare_publisher_guard(request,expected_plan_digest=digest,runner=host)
        try:
            if mode=='cleanup_gap':
                with patch.object(runtime,'revoke_shutdown_readiness_permit',side_effect=OSError('post-barrier injected cleanup')):
                    result=promotion.apply_publisher_guard(request,expected_plan_digest=digest,runner=host)
            else:
                result=promotion.apply_publisher_guard(request,expected_plan_digest=digest,runner=host)
        except promotion.PromotionError as error:
            if mode not in {'reject','cleanup_gap'}:raise
            result={'status':'SOURCE_REJECTED','error':str(error)}
        actual=git(bare,'rev-parse','refs/heads/main')
        receipt=activation.load_action_receipt(promotion._pg_receipt_path(request))
        assert host.push_under_ex==[True]
        assert all(path.read_bytes()==data for path,data in five.items()) and old_path.read_bytes()==old_bytes
        assert all(not host.loaded[x] for x in runtime.SERVICE_LABELS if x not in PAIR)
        if mode=='reject':
            assert actual==before and not host.processes
            assert result['status'] not in {'POSTCHECK_PASSED','COMMITTED'}
        else:
            assert actual==target
            for p in host.processes.values():
                p.wait(timeout=5)
                assert p.returncode==0,p.stderr.read()
            assert all((tmp_path/(label+'.sentinel')).is_file() for label in PAIR)
            if mode.startswith('publish_'):
                release=tmp_path/'release'
                git(actor,'worktree','add','--detach',str(release),target)
                (release/'package.json').write_text(json.dumps({'version':'0.0.1'}))
                (release/'pyproject.toml').write_text('version = "0.0.1"\n')
                if mode=='publish_code_drift':
                    path=release/'scripts/pantheon_content_runtime_manifest.py'
                    path.write_bytes(path.read_bytes()+b'\n# isolated runtime drift\n')
                published=commit(release,'isolated publication proof')
                if mode=='publish_lightweight':
                    git(release,'tag','v0.0.1')
                else:
                    # 沿正式 Publisher 的 tag 命令，不自行用較弱 fixture 代替。
                    tag_args=publisher.release_git_plan('0.0.1')['tag']
                    if mode=='publish_tag_wrong_commit':tag_args=[*tag_args,target]
                    git(release,'-c','user.name=Isolated Probe','-c','user.email=probe@localhost',*tag_args)
                git(release,'push','--atomic','origin','HEAD:refs/heads/main','refs/tags/v0.0.1')
                if mode=='publish_tag_missing':git(bare,'update-ref','-d','refs/tags/v0.0.1')
                if mode!='publish_no_ledger':write_private(state/'ledger.json',json.dumps({'published_runs':[{'run_id':'isolated-release',
                    'commit_sha':published,'version':'0.0.1','article_ids':['ISOLATED']}]}).encode())
                actual=git(bare,'rev-parse','refs/heads/main')
            before_commands=len([x for x in host.commands if len(x)>1 and x[1] in ['bootstrap','bootout']])
            if mode=='release_gap':
                missing=activation.load_action_receipt(promotion._pg_receipt_path(request));missing['ex_releases']=[]
                promotion._pg_save(request,missing)
            if mode in {'publish_no_ledger','publish_code_drift','publish_tag_missing','publish_tag_wrong_commit'}:
                with pytest.raises(promotion.PromotionError,match='remote OLD/UNKNOWN'):
                    promotion.recover_publisher_guard(request,expected_plan_digest=digest,runner=host)
                result={'status':'EXPECTED_UNKNOWN'}
            else:
                result=promotion.recover_publisher_guard(request,expected_plan_digest=digest,runner=host)
                assert result['status']=='HEALTHY'
                if mode in {'publish_advance','publish_lightweight'}:
                    assert result['health']['remote']['status']=='PUBLISHED_DESCENDANT'
            assert len([x for x in host.commands if len(x)>1 and x[1] in ['bootstrap','bootout']])==before_commands
            assert runtime.validate_barrier(state/'four-lane-activation-target.barrier',new)['status']=='PASS'
        assert not runtime.shutdown_readiness_permit_path(state).exists()
        assert all(x['released'] for x in receipt.get('ex_releases',[]) if x['acquired'])
        # 在受管根回收前匯出真 Git/原生 wrapper 證據；不把 host adapter 或 sentinel 當正式驗收。
        if os.environ.get('TMP_ARTIFACT_ROOT'):
            evidence=Path(os.environ['TMP_ARTIFACT_ROOT'])/'evidence'
            evidence.mkdir(exist_ok=True)
            final_receipt=activation.load_action_receipt(promotion._pg_receipt_path(request))
            summary={'mode':mode,'started_epoch':started,'ended_epoch':time.time(),
                'before_sha':before,'target_sha':target,'remote_main_after':actual,
                'source_head':git(source,'rev-parse','HEAD'),'old_actor_head':git(old_actor,'rev-parse','HEAD'),
                'new_actor_head':git(actor,'rev-parse','HEAD'),'plan_digest':digest,
                'controller_sha256':hashlib.sha256((ROOT/'scripts/pantheon_content_runtime_promotion.py').read_bytes()).hexdigest(),
                'status':result['status'],'push_under_ex':host.push_under_ex,
                'five_bytes_preserved':True,'five_unloaded':True,'old_manifest_preserved':True,
                'permit_absent':True,'wrappers_started':list(host.processes),
                'release_tag_raw':git(bare,'ls-remote',str(bare),'refs/tags/v0.0.1','refs/tags/v0.0.1^{}') if mode.startswith('publish_') else None,
                'publication_commit_sha':published if mode.startswith('publish_') else None,
                'publication_proofs':result.get('health',{}).get('remote',{}).get('proofs',[]),
                'commands':host.commands,'limitations':['launchd/ps are injected host adapter',
                    'wrapper payload is harmless sentinel','capacity receipt is synthetic schema wiring',
                    'local bare Git only; not production deployment, business payload or formal readiness']}
            (evidence/(mode+'-git-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
            (evidence/(mode+'-controller-receipt.json')).write_text(json.dumps(final_receipt,indent=2)+'\n')
    finally:host.cleanup()

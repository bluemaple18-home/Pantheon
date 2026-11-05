"""兩服務 opt-in 不影響既有七服務契約；以原生 manifest/receipt 驗邊界。"""
from pathlib import Path
from types import SimpleNamespace
import json
import os
import plistlib
import subprocess
import sys

import pytest

from scripts import pantheon_content_runtime_manifest as runtime
from scripts import pantheon_content_capacity_guard as guard

PUB = 'com.pantheon.agy-content-publisher'
GUARD = 'com.pantheon.content-capacity-guard'
PAIR = (PUB, GUARD)


def manifest(tmp_path, scoped=True):
    roots = {name: tmp_path / name for name in ('actor', 'queue', 'state', 'logs')}
    for path in roots.values():
        path.mkdir(exist_ok=True)
    kwargs = {'activation_scope': 'publisher_guard'} if scoped else {}
    return runtime.build_manifest(actor_root=roots['actor'], queue_root=roots['queue'],
        publisher_state_root=roots['state'], log_root=roots['logs'], identity='synthetic-pubguard',
        generation='pubguard-scope-test', python_executable=Path(sys.executable).resolve(), **kwargs)


def normal_plist(m, label, path):
    mapping = {'identity':'IDENTITY','manifest_digest':'MANIFEST_DIGEST',
        'runtime_identity_digest':'IDENTITY_DIGEST','runtime_digest':'CODE_DIGEST',
        'config_version':'CONFIG_VERSION','generation':'GENERATION','actor_root':'ACTOR_ROOT',
        'queue_root':'QUEUE_ROOT','publisher_state_root':'PUBLISHER_STATE_ROOT','log_root':'LOG_ROOT',
        'python_executable':'PYTHON_EXECUTABLE'}
    env = {'PANTHEON_FORMAL_RUNTIME':'1', 'PANTHEON_RUNTIME_SERVICE_LABEL':label,
        'PANTHEON_RUNTIME_MANIFEST':str(Path(m['actor_root']).parent/'manifest.json')}
    env.update({'PANTHEON_RUNTIME_'+suffix:m[key] for key,suffix in mapping.items()})
    args = [m['python_executable'],'-m','scripts.pantheon_content_runtime_manifest','barrier-exec',
        '--barrier',str(Path(m['publisher_state_root'])/('four-lane-activation-'+m['generation']+'.barrier')),
        '--expected-digest',m['manifest_digest'],'--manifest',env['PANTHEON_RUNTIME_MANIFEST'],
        '--service-label',label,'--ready-root',str(path.parent/'ready'),'--timeout','30','--',
        m['python_executable'],'-m','scripts.agy_content_publisher' if label==PUB else 'scripts.pantheon_content_capacity_guard',
        '--max-runs','1']
    payload={'Label':label,'ProgramArguments':args,'WorkingDirectory':m['actor_root'],
        'RunAtLoad':True,'StartInterval':60 if label==PUB else 300,'EnvironmentVariables':env}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(payload));path.chmod(0o600)
    return path


def test_opt_in_pair_real_ack_barrier_and_inactive_refusal(tmp_path):
    m=manifest(tmp_path)
    assert m['service_labels']==list(runtime.SERVICE_LABELS)
    assert runtime.activation_service_labels(m)==PAIR
    ready=tmp_path/'ready';barrier=tmp_path/'barrier.json'
    for label in PAIR:
        runtime.write_readiness_ack(ready,m,label)
    runtime.activate_barrier(barrier,ready,m)
    assert runtime.validate_barrier(barrier,m)['status']=='PASS'
    assert json.loads(barrier.read_text())['service_labels']==list(PAIR)
    with pytest.raises(runtime.RuntimeManifestError):
        runtime.write_readiness_ack(ready,m,'com.pantheon.agy-gemini-new')
    assert not (ready/'com.pantheon.agy-gemini-new.json').exists()


def test_unscoped_manifest_still_requires_all_seven(tmp_path):
    m=manifest(tmp_path,False)
    receipts=[runtime.receipt_for_label(m,label) for label in PAIR]
    with pytest.raises(runtime.RuntimeManifestError,match='incomplete'):
        runtime.validate_receipts(m,receipts)
    assert runtime.activation_service_labels(m)==runtime.SERVICE_LABELS


def test_scope_is_bound_and_unknown_scope_rejected(tmp_path):
    m=manifest(tmp_path,False)
    digest=m['runtime_identity_digest'];m['activation_scope']='publisher_guard'
    assert runtime._runtime_identity_digest(m)!=digest
    path=tmp_path/'manifest.json';runtime.write_manifest(path,m)
    with pytest.raises(runtime.RuntimeManifestError,match='digest'):
        runtime.load_manifest(path)
    with pytest.raises(runtime.RuntimeManifestError):
        runtime.activation_service_labels({'activation_scope':'any-two'})


def test_scoped_guard_idle_and_stop_authority_only_publisher(tmp_path,monkeypatch):
    m=manifest(tmp_path)
    home=tmp_path/'home';home.mkdir();launch=home/'Library/LaunchAgents'
    for label in PAIR:
        normal_plist(m,label,launch/(label+'.plist'))
    mp=tmp_path/'manifest.json';runtime.write_manifest(mp,m)
    ready=tmp_path/'ready';barrier=Path(m['publisher_state_root'])/('four-lane-activation-'+m['generation']+'.barrier')
    for label in PAIR:
        runtime.write_readiness_ack(ready,m,label)
    runtime.activate_barrier(barrier,ready,m)
    monkeypatch.setattr(guard.pwd,'getpwuid',lambda uid:SimpleNamespace(pw_dir=str(home)))
    monkeypatch.setenv('PANTHEON_USER_HOME_DIR',str(home))
    monkeypatch.setenv('PANTHEON_RUNTIME_MANIFEST',str(mp))
    monkeypatch.setenv('PANTHEON_RUNTIME_MANIFEST_DIGEST',m['manifest_digest'])
    receipt={'status':'PASS',**runtime.receipt_for_label(m,GUARD)}
    assert guard._normal_scheduled_service_labels(receipt)==frozenset({PUB})
    context=guard._recovery_context(receipt)
    assert context['authorized'] is True
    assert set(context['plists'])=={PUB}
    monkeypatch.setattr(guard,'_disabled_service_labels',lambda runner:(frozenset(),None))
    def runner(args):
        assert args[:2]==['launchctl','print']
        if args[2].endswith('/'+PUB):
            text=f'{args[2]} = {{\n path = {launch/(PUB+".plist")}\n state = not running\n last exit code = 0\n}}\n'
            return subprocess.CompletedProcess(args,0,text,'')
        return subprocess.CompletedProcess(args,113,'','absent')
    snapshot=guard._service_rss_snapshot(runner,expected_inert_labels=frozenset(),expected_idle_labels=frozenset({PUB}))
    assert snapshot['available'] is True
    incident=guard._capture_recovery_incident(timestamp=1.0,reasons=['test'],recovery_context=context,runner=runner)
    assert incident['stop_targets']==[PUB]
    assert incident['owned_labels']==[PUB]

    # 既有 incident decoder 也須接受合法 Pub-only、拒絕把另五服務加入其 stop 集合。
    state_file=tmp_path/'guard-state.json'
    previous={'status':'STOPPING','recovery_incident':incident}
    guard._write_state(state_file,previous)
    loaded,error=guard._load_open_recovery_incident(previous,state_file)
    assert error is None and loaded['stop_targets']==[PUB]
    widened={**incident,'stop_targets':[PUB,'com.pantheon.agy-gemini-new'],
        'owned_labels':[PUB,'com.pantheon.agy-gemini-new']}
    invalid,error=guard._load_open_recovery_incident({'status':'STOPPING','recovery_incident':widened},state_file)
    assert invalid is None and error=='capacity_recovery_incident_invalid'

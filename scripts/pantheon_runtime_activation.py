#!/usr/bin/env python3
"""七服務 activation token 的薄驗證層。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from scripts import pantheon_content_runtime_manifest as formal_runtime


T = TypeVar("T")


class RuntimeActivationError(ValueError):
    """activation token 不完整、過期或 identity 不一致。"""


def publish_generation_token(
    token_path: Path,
    ready_root: Path,
    manifest: dict[str, Any],
    *,
    correlation_id: str,
) -> dict[str, Any]:
    """七個服務 ack 完整一致時，原子發布單一 generation token。"""
    if not correlation_id or correlation_id.strip() != correlation_id:
        raise RuntimeActivationError("activation correlation id is invalid")
    try:
        activation = formal_runtime.activate_barrier(token_path, ready_root, manifest)
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error
    return {
        **activation,
        "activation_token": str(token_path),
        "correlation_id": correlation_id,
    }


def validate_token_payload(
    token_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """驗證 token 與當前 manifest generation/identity 完全一致。"""
    if not token_path.is_absolute():
        raise RuntimeActivationError("activation token path is invalid")
    try:
        return formal_runtime.validate_barrier(token_path, manifest)
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error


def validate_service_before_io(
    token_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    *,
    queue_root: Path,
    state_root: Path,
    actor_root: Path,
    log_root: Path,
) -> dict[str, Any]:
    """在服務第一次 queue/state I/O 前重驗 token 與 runtime identity。"""
    token_receipt = validate_token_payload(token_path, manifest)
    try:
        runtime_receipt = formal_runtime.validate_runtime_tick(
            service_label,
            queue_root=queue_root,
            state_root=state_root,
            actor_root=actor_root,
            log_root=log_root,
        )
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error
    return {
        "status": "PASS",
        "activation": token_receipt,
        "runtime": runtime_receipt,
    }


def run_after_activation_token(
    token_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    *,
    queue_root: Path,
    state_root: Path,
    actor_root: Path,
    log_root: Path,
    operation: Callable[[], T],
) -> T:
    """共享 lease 涵蓋驗證到 callback 返回；非同步後代須另有繼承／等待證據。"""
    with formal_runtime.runtime_work_lease(state_root):
        validate_service_before_io(
            token_path,
            manifest,
            service_label,
            queue_root=queue_root,
            state_root=state_root,
            actor_root=actor_root,
            log_root=log_root,
        )
        return operation()


def validate_rollback_loaded_identities(
    expected: dict[str, dict[str, Any]],
    actual: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    try:
        return formal_runtime.validate_rollback_identities(expected, actual)
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error

# maintenance 沿 installer rollback；此處僅提供身分、lease 與原子發布原語。
import fcntl
import hashlib
import json
import os
import plistlib
import re
import shlex
import shutil
import stat
import subprocess
import sys

_MAINTENANCE_FILES = (
    'scripts/install_agy_gemini_coordinator_launchd.sh',
    'scripts/pantheon_runtime_activation.py',
    'scripts/pantheon_content_runtime_manifest.py',
)


def _exact_bytes(path: Path, *, expected_uid: int | None = None) -> bytes:
    owner = os.getuid() if expected_uid is None else expected_uid
    if path.resolve(strict=True) != path:
        raise RuntimeActivationError(f'noncanonical identity: {path}')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid != owner or before.st_nlink != 1:
            raise RuntimeActivationError(f'file identity: {path}')
        data = stream.read()
        after = os.fstat(stream.fileno())
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise RuntimeActivationError(f'file changed: {path}')
    if path.stat().st_ino != after.st_ino:
        raise RuntimeActivationError(f'file replaced: {path}')
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_identity(path: Path) -> dict[str, int]:
    value = path.lstat()
    return dict(device=value.st_dev, inode=value.st_ino, uid=value.st_uid,
                mode=stat.S_IMODE(value.st_mode), nlink=value.st_nlink)


def _require(value: bool, reason: str) -> None:
    if not value:
        raise RuntimeActivationError(reason)


def _head(root: Path) -> str:
    return subprocess.check_output(['/usr/bin/git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()


def maintenance_binding(binding_path: Path) -> tuple[dict, dict, str]:
    raw = _exact_bytes(binding_path)
    binding = json.loads(raw)
    _require(binding.get('schema_version') == 1, 'binding schema mismatch')
    token = _digest(raw)
    source = Path(__file__).resolve().parents[1]
    _require(binding['source_root'] == str(source) and _head(source) == binding['source_head'], 'source HEAD/root mismatch')
    _require(set(binding['source_files']) == set(_MAINTENANCE_FILES), 'source file set mismatch')
    for name, digest in binding['source_files'].items():
        _require(_digest(_exact_bytes(source / name)) == digest, f'source hash mismatch: {name}')
    mp = Path(binding['manifest_path'])
    _require(_digest(_exact_bytes(mp)) == binding['manifest_sha256'], 'manifest hash mismatch')
    manifest = formal_runtime.load_manifest(mp, binding['manifest_digest'])
    _require(manifest['actor_root'] == binding['actor_root'] and manifest.get('actor_head') == binding['actor_head']
             and _head(Path(binding['actor_root'])) == binding['actor_head'], 'actor HEAD/root mismatch')
    stage = Path(binding['stage_path'])
    expected_stage = Path(os.environ['PANTHEON_USER_HOME_DIR']) / 'Library/LaunchAgents/.pantheon-four-lane-stage'
    _require(stage == expected_stage and stage.resolve(strict=True) == stage, 'stage path mismatch')
    required = {'failure-receipt.json', 'manifest-digest', 'generation'}
    for label in formal_runtime.SERVICE_LABELS:
        required.update({f'{label}.plist', f'{label}.previous_loaded', f'backups/{label}.plist'})
    _require(required <= binding['stage_files'].keys(), 'stage binding incomplete')
    for name, digest in binding['stage_files'].items():
        _require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'stage binding path invalid')
        _require(_digest(_exact_bytes(stage / name)) == digest, f'stage {name} hash mismatch')
    _require((stage/'manifest-digest').read_text().strip() == manifest['manifest_digest']
             and (stage/'generation').read_text().strip() == manifest['generation'], 'stage manifest/generation mismatch')
    failure = json.loads(_exact_bytes(stage/'failure-receipt.json'))
    _require(failure.get('status') == 'ROLLBACK_FAILED' and failure.get('stage_identity') == {
        key: manifest[key] for key in ('manifest_digest', 'generation')}, 'failure identity mismatch')
    archive = stage/'normal-rollback-drain.original.json'
    original = _exact_bytes(archive if archive.exists() else stage/'normal-rollback-drain.json')
    _require(_digest(original) == binding['drain_sha256'], 'drain original hash mismatch')
    record = json.loads(original)
    _require(record.get('status') == 'UNKNOWN_OR_FAILED' and isinstance(record.get('processes'), dict)
             and isinstance(record.get('groups'), list), 'drain original status mismatch')
    actual = _exact_bytes(stage/'normal-rollback-drain.json')
    expected = maintenance_journal(original, token)
    _require(actual in (original, expected), 'drain journal binding mismatch')
    barrier = Path(manifest['publisher_state_root']) / f"four-lane-activation-{manifest['generation']}.barrier"
    _require(not os.path.lexists(barrier), 'fence current barrier present')
    previous = stage/'previous-barrier-path'
    if previous.exists():
        _require('previous-barrier-path' in binding['stage_files'], 'stage previous fence unbound')
        prior = Path(previous.read_text().strip())
        _require(prior.is_absolute() and not os.path.lexists(prior), 'fence previous barrier present')
    formal_runtime.aggregate_plist_preflight(manifest, [stage/'backups'/f'{label}.plist' for label in formal_runtime.SERVICE_LABELS], expected_activation_mode='activation-only')
    for label in formal_runtime.SERVICE_LABELS:
        _require((stage/f'{label}.previous_loaded').read_text().strip() == '0', 'stage previous_loaded must be 0')
        backup = _exact_bytes(stage/'backups'/f'{label}.plist')
        plist = plistlib.loads(backup)
        args = plist.get('ProgramArguments', [])
        _require(len(args) > 18 and args[1:4] == ['-m', 'scripts.pantheon_content_runtime_manifest', 'barrier-exec']
                 and args[4:12] == ['--barrier', str(barrier), '--expected-digest', manifest['manifest_digest'],
                    '--manifest', binding['manifest_path'], '--service-label', label]
                 and args[12] == '--ready-root' and args[14] == '--timeout'
                 and args[16:18] == ['--activation-only', '--'], 'stage backup wrapper identity mismatch')
        live = stage.parent/f'{label}.plist'
        _require(_exact_bytes(live) in (backup, _exact_bytes(stage/f'{label}.plist'))
                 and _file_identity(live)['mode'] == 0o600, f'live plist identity mismatch: {label}')
    result = stage/'normal-rollback-reconciliation.json'
    if result.exists():
        _require(_exact_bytes(result) == maintenance_result(binding, token), 'receipt identity mismatch')
        _require(archive.exists() and actual == expected, 'receipt drain readback drift')
        for label in formal_runtime.SERVICE_LABELS:
            _require(_exact_bytes(stage.parent/f'{label}.plist') == _exact_bytes(stage/'backups'/f'{label}.plist'),
                     'receipt live readback drift')
    maintenance_control_identity(binding['control'], binding['purpose'])
    cp = Path(binding['control']['path'])
    _require(binding['purpose'] in ('fixture', 'production'), 'binding purpose invalid')
    if binding['purpose'] == 'fixture':
        _require(cp != Path('/bin/launchctl') and cp != Path('/usr/bin/launchctl')
                 and manifest['identity'].startswith('synthetic-'), 'fixture cannot authorize production')
    return binding, manifest, token


def maintenance_control_identity(control: dict, purpose: str) -> None:
    """系統 controller 僅允許 canonical /bin/launchctl、root owner；evidence owner 不變。"""
    path = Path(control['path'])
    if purpose == 'production':
        _require(path == Path('/bin/launchctl') and control['uid'] == 0, 'control identity must be root /bin/launchctl')
        owner = 0
    else:
        _require(purpose == 'fixture' and path not in (Path('/bin/launchctl'), Path('/usr/bin/launchctl')),
                 'control identity fixture path invalid')
        owner = os.getuid()
    _require(shutil.which('launchctl') == str(path)
             and _digest(_exact_bytes(path, expected_uid=owner)) == control['sha256']
             and _file_identity(path) == {key: control[key] for key in _file_identity(path)},
             'control identity mismatch')


def maintenance_reconciled(binding: dict, token: str) -> None:
    """直接 helper 也不能越過原 UNKNOWN 的 archive/journal 邊界。"""
    stage = Path(binding['stage_path'])
    archive = stage/'normal-rollback-drain.original.json'
    _require(archive.exists(), 'reconciled archive/journal required')
    original = _exact_bytes(archive)
    _require(_digest(original) == binding['drain_sha256']
             and _exact_bytes(stage/'normal-rollback-drain.json') == maintenance_journal(original, token),
             'reconciled archive/journal required')


def maintenance_journal(original: bytes, token: str) -> bytes:
    value = json.loads(original)
    value.pop('deadline', None)
    value.pop('error', None)
    value.update(status='DRAINED', active=[], resample_required=False, reconciliation_binding=token, original_sha256=_digest(original))
    return (json.dumps(value, sort_keys=True) + '\n').encode()


def maintenance_result(binding: dict, token: str) -> bytes:
    return (json.dumps(dict(status='ROLLBACK_COMPLETE_FENCED', binding_sha256=token,
        original_sha256=binding['drain_sha256'], source_head=binding['source_head'], actor_head=binding['actor_head'],
        manifest_digest=binding['manifest_digest'], stage_path=binding['stage_path'],
        bootout='NOT_SENT', containment='PREREQUISITE_DISABLED_UNLOADED'), sort_keys=True)+'\n').encode()


def maintenance_lease(binding: dict, manifest: dict, fd: int) -> None:
    path = Path(manifest['publisher_state_root'])/'runtime-work.lock'
    formal_runtime._verify_work_lease(fd, path)
    _require(_file_identity(path) == binding['lease'], 'lease inode/control identity mismatch')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeActivationError('lease BUSY') from error
    formal_runtime._verify_work_lease(fd, path)


def maintenance_control(binding: dict, manifest: dict, fd: int) -> None:
    domain = f'gui/{os.getuid()}'
    def run(*args):
        maintenance_lease(binding, manifest, fd)
        reply = subprocess.run([binding['control']['path'], *args], capture_output=True, text=True, timeout=5, pass_fds=(fd,))
        maintenance_lease(binding, manifest, fd)
        return reply
    disabled = run('print-disabled', domain)
    _require(disabled.returncode == 0, 'disabled readback UNKNOWN')
    for label in formal_runtime.SERVICE_LABELS:
        marker = f'"{label}"'
        lines = [line for line in disabled.stdout.splitlines() if marker in line]
        _require(len(lines) == 1, f'disabled identity drift: {label}')
        match = re.fullmatch(
            r'\s*"' + re.escape(label) + r'"\s*=>\s*(true|false|enabled|disabled)\s*',
            lines[0],
        )
        _require(match is not None and match.group(1) in ('true', 'disabled'),
                 f'disabled identity drift: {label}')
        reply = run('print', f'{domain}/{label}')
        _require(reply.returncode in (3, 113), f'loaded/UNKNOWN service: {label}: {reply.returncode}')


def maintenance_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + f'.tmp.{os.getpid()}')
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def maintenance_publish_journal(binding: dict, token: str, fd: int, manifest: dict) -> None:
    stage = Path(binding['stage_path'])
    archive = stage/'normal-rollback-drain.original.json'
    path = stage/'normal-rollback-drain.json'
    original = _exact_bytes(archive if archive.exists() else path)
    _require(_digest(original) == binding['drain_sha256'], 'drain archive mismatch')
    maintenance_lease(binding, manifest, fd)
    if not archive.exists():
        maintenance_atomic(archive, original)
    desired = maintenance_journal(original, token)
    if _exact_bytes(path) != desired:
        maintenance_atomic(path, desired)
    maintenance_lease(binding, manifest, fd)


def _maintenance_main() -> int:
    mode, path, *arguments = sys.argv[1:]
    bp = Path(path)
    binding, manifest, token = maintenance_binding(bp)
    if mode in ('restore', 'finish'):
        maintenance_reconciled(binding, token)
    if mode == 'run':
        fd = os.open(Path(manifest['publisher_state_root'])/'runtime-work.lock', os.O_RDWR | os.O_NOFOLLOW)
        try:
            maintenance_lease(binding, manifest, fd)
            env = {**os.environ, 'PANTHEON_MAINTENANCE_LEASE_FD': str(fd)}
            child = subprocess.run(['/bin/bash', str(Path(binding['source_root'])/_MAINTENANCE_FILES[0]),
                '--reconcile-normal-rollback-held', str(bp)], env=env, pass_fds=(fd,))
            maintenance_lease(binding, manifest, fd)
            return child.returncode
        finally:
            # 不 LOCK_UN：控制 child 意外超過 parent lifetime 時仍持 exclusion。
            os.close(fd)
    fd = int(os.environ['PANTHEON_MAINTENANCE_LEASE_FD'])
    maintenance_lease(binding, manifest, fd)
    maintenance_control(binding, manifest, fd)
    stage = Path(binding['stage_path'])
    if mode == 'prepare':
        values = dict(STAGE_DIR=str(stage), RUNTIME_MANIFEST_FILE=binding['manifest_path'],
            ACTIVATION_BARRIER=str(Path(manifest['publisher_state_root'])/f"four-lane-activation-{manifest['generation']}.barrier"))
        for key, value in values.items():
            print(key+'='+shlex.quote(value))
        print('LABELS=('+' '.join(shlex.quote(x) for x in formal_runtime.SERVICE_LABELS)+')')
        print('TARGET_PLISTS=('+' '.join(shlex.quote(str(stage.parent/f'{x}.plist')) for x in formal_runtime.SERVICE_LABELS)+')')
    elif mode == 'restore':
        label, = arguments
        _require(label in formal_runtime.SERVICE_LABELS, 'restore label identity mismatch')
        target = stage.parent/f'{label}.plist'
        desired = _exact_bytes(stage/'backups'/f'{label}.plist')
        if _exact_bytes(target) != desired:
            maintenance_atomic(target, desired)
        maintenance_lease(binding, manifest, fd)
    elif mode == 'finish':
        for label in formal_runtime.SERVICE_LABELS:
            _require(_exact_bytes(stage.parent/f'{label}.plist') == _exact_bytes(stage/'backups'/f'{label}.plist'), 'restore readback mismatch')
        receipt = stage/'normal-rollback-reconciliation.json'
        desired = maintenance_result(binding, token)
        if receipt.exists():
            _require(_exact_bytes(receipt) == desired, 'receipt identity mismatch')
            print('IDLE')
        else:
            maintenance_atomic(receipt, desired)
            print('ROLLBACK_COMPLETE_FENCED')
    else:
        raise RuntimeActivationError('unknown maintenance helper')
    maintenance_lease(binding, manifest, fd)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(_maintenance_main())
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        raise SystemExit(1)

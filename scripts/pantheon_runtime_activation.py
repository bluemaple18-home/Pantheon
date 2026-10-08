#!/usr/bin/env python3
"""Pantheon 七服務 activation、程序排空與同 generation 復機控制接點。"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, TypeVar

from scripts import pantheon_content_runtime_manifest as formal_runtime


T = TypeVar("T")
CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]
ACTION_RECEIPT_SCHEMA_VERSION = 1
TERMINAL_SERVICE_STATES = frozenset({"waiting", "not running", "exited"})
LAUNCHCTL_OBJECT_START_PATTERN = re.compile(r"^[^{}]+ = \{$")
LAUNCHCTL_STATE_FIELD_PATTERN = re.compile(r"^state = ([^\r\n]+)$")
LAUNCHCTL_PATH_FIELD_PATTERN = re.compile(r"^path = ([^\r\n]+)$")
LAUNCHCTL_LAST_EXIT_CODE_FIELD_PATTERN = re.compile(r"^last exit code = (-?[0-9]+)$")
LAUNCHCTL_RUNS_FIELD_PATTERN = re.compile(r"^runs = ([0-9]+)$")
LAUNCHCTL_PID_FIELD_PATTERN = re.compile(r"^pid = ([1-9][0-9]*)$")
OWNED_ROOT_FIELDS = ("actor_root", "queue_root", "publisher_state_root", "log_root")


class RuntimeActivationError(ValueError):
    """activation、程序生命週期或 action receipt 無法被可靠證明。"""


class ProcessBirth(ctypes.Structure):
    """Darwin PROC_PIDTBSDINFO 的程序出生身分。"""

    _fields_ = [
        (name, ctypes.c_uint32)
        for name in (
            "flags",
            "status",
            "xstatus",
            "pid",
            "ppid",
            "uid",
            "gid",
            "ruid",
            "rgid",
            "svuid",
            "svgid",
            "reserved",
        )
    ]
    _fields_ += [("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32)]
    _fields_ += [
        (name, ctypes.c_uint32)
        for name in ("nfiles", "pgid", "jobc", "tdev", "tpgid")
    ]
    _fields_ += [
        ("nice", ctypes.c_int32),
        ("sec", ctypes.c_uint64),
        ("usec", ctypes.c_uint64),
    ]


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


def _maintenance_main(argv: Sequence[str] | None = None) -> int:
    mode, path, *arguments = sys.argv[1:] if argv is None else argv
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



def parse_launchctl_service_identity(
    output: str,
    *,
    expected_target: str,
) -> dict[str, list[Any]] | None:
    """只解析 launchctl root service object；nested coalition 欄位不得混入。"""
    depth = 0
    root_started = False
    root_closed = False
    fields: dict[str, list[Any]] = {
        "states": [],
        "paths": [],
        "last_exit_codes": [],
        "runs": [],
        "pids": [],
    }
    patterns: tuple[tuple[str, re.Pattern[str], Callable[[str], Any]], ...] = (
        ("states", LAUNCHCTL_STATE_FIELD_PATTERN, str),
        ("paths", LAUNCHCTL_PATH_FIELD_PATTERN, str),
        ("last_exit_codes", LAUNCHCTL_LAST_EXIT_CODE_FIELD_PATTERN, int),
        ("runs", LAUNCHCTL_RUNS_FIELD_PATTERN, int),
        ("pids", LAUNCHCTL_PID_FIELD_PATTERN, int),
    )
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        if not root_started:
            if raw_line != f"{expected_target} = {{":
                return None
            root_started = True
            depth = 1
            continue
        line = raw_line.strip()
        if root_closed:
            return None
        if line == "}":
            depth -= 1
            if depth < 0:
                return None
            if depth == 0:
                root_closed = True
            continue
        if LAUNCHCTL_OBJECT_START_PATTERN.fullmatch(line) is not None:
            depth += 1
            continue
        if "{" in line or "}" in line:
            return None
        if depth == 1:
            for field, pattern, converter in patterns:
                match = pattern.fullmatch(line)
                if match is not None:
                    fields[field].append(converter(match.group(1)))
    if not root_started or not root_closed or depth != 0:
        return None
    return fields


def observe_launchctl_service(
    label: str,
    plist_path: Path | None,
    *,
    runner: CommandRunner,
    domain: str | None = None,
) -> dict[str, Any]:
    """讀取單一 label 的 exact live identity；不可解析時回 UNKNOWN。"""
    selected_domain = domain or f"gui/{os.getuid()}"
    target = f"{selected_domain}/{label}"
    try:
        result = runner(["launchctl", "print", target])
    except OSError as error:
        return {
            "label": label,
            "target": target,
            "topology": "UNKNOWN",
            "returncode": None,
            "error": f"{type(error).__name__}: {error}",
            "identity": None,
        }
    if result.returncode in {3, 113}:
        return {
            "label": label,
            "target": target,
            "topology": "ABSENT",
            "returncode": result.returncode,
            "identity": None,
        }
    identity = (
        parse_launchctl_service_identity(result.stdout, expected_target=target)
        if result.returncode == 0
        else None
    )
    expected_path = None if plist_path is None else str(plist_path)
    valid = (
        identity is not None
        and len(identity["states"]) == 1
        and len(identity["paths"]) == 1
        and len(identity["runs"]) == 1
        and len(identity["last_exit_codes"]) <= 1
        and len(identity["pids"]) <= 1
        and (expected_path is None or identity["paths"] == [expected_path])
    )
    return {
        "label": label,
        "target": target,
        "topology": "LOADED" if valid else "UNKNOWN",
        "returncode": result.returncode,
        "identity": identity,
    }


def verify_services_absent(
    labels: Sequence[str],
    *,
    runner: CommandRunner,
    domain: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """逐 label 證明 launchd absence；任一 UNKNOWN/LOADED 即失敗。"""
    observations: dict[str, Any] = {}
    for label in labels:
        observation = observe_launchctl_service(
            label,
            None,
            runner=runner,
            domain=domain,
        )
        observations[label] = observation
        if observation["topology"] != "ABSENT":
            return False, observations
    return True, observations



def read_disabled_service_labels(
    labels: Sequence[str],
    *,
    runner: CommandRunner,
    domain: str | None = None,
) -> frozenset[str]:
    """精確解析 launchctl print-disabled；任何不完整輸出皆 UNKNOWN。"""
    selected_domain = domain or f"gui/{os.getuid()}"
    try:
        result = runner(["launchctl", "print-disabled", selected_domain])
    except OSError as error:
        raise RuntimeActivationError("launchctl print-disabled outcome is unknown") from error
    if result.returncode != 0:
        raise RuntimeActivationError(
            f"launchctl print-disabled failed: {result.returncode}"
        )
    rows = [line for line in result.stdout.splitlines() if line.strip()]
    if not rows or rows[0].strip() != "disabled services = {" or rows[-1].strip() != "}":
        raise RuntimeActivationError("launchctl print-disabled grammar is invalid")
    allowed = set(labels)
    disabled: set[str] = set()
    pattern = re.compile(r'^\s*"([^"]+)"\s*=>\s*(true|false|enabled|disabled),?\s*$')
    for line in rows[1:-1]:
        match = pattern.fullmatch(line)
        if match is None:
            raise RuntimeActivationError("launchctl print-disabled grammar is invalid")
        if match.group(2) in {"true", "disabled"} and match.group(1) in allowed:
            disabled.add(match.group(1))
    return frozenset(disabled)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _is_private_file(path: Path) -> bool:
    try:
        metadata = path.stat()
    except OSError:
        return False
    return (
        path.is_file()
        and not path.is_symlink()
        and path.resolve(strict=True) == path
        and metadata.st_uid == os.getuid()
        and metadata.st_nlink == 1
        and stat.S_IMODE(metadata.st_mode) == 0o600
    )


def capture_file_identity(
    path: Path,
    *,
    require_private: bool = True,
) -> dict[str, Any]:
    """以 no-follow FD 綁定 path、inode 與 bytes；authority 可要求 owner-private。"""
    if not path.is_absolute():
        raise RuntimeActivationError("authority file path is not absolute")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise RuntimeActivationError("authority file is unavailable") from error
    try:
        held = os.fstat(descriptor)
        current = path.lstat()
        if (
            not stat.S_ISREG(held.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or current.st_uid != os.getuid()
            or current.st_nlink != 1
            or (require_private and stat.S_IMODE(current.st_mode) != 0o600)
            or (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise RuntimeActivationError("authority file identity is invalid")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        current_after = path.lstat()
        if (
            (held.st_dev, held.st_ino, held.st_size, held.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or (after.st_dev, after.st_ino)
            != (current_after.st_dev, current_after.st_ino)
            or current_after.st_uid != os.getuid()
            or current_after.st_nlink != 1
            or (require_private and stat.S_IMODE(current_after.st_mode) != 0o600)
        ):
            raise RuntimeActivationError("authority file changed during read")
        return {
            "path": str(path),
            "device": after.st_dev,
            "inode": after.st_ino,
            "size": after.st_size,
            "mtime_ns": after.st_mtime_ns,
            "sha256": digest.hexdigest(),
        }
    finally:
        os.close(descriptor)


def valid_file_identity_record(value: object) -> bool:
    """驗證 action authority 使用的 immutable file identity schema。"""
    if not isinstance(value, dict):
        return False
    path = value.get("path")
    return (
        isinstance(path, str)
        and Path(path).is_absolute()
        and type(value.get("device")) is int
        and type(value.get("inode")) is int
        and type(value.get("size")) is int
        and type(value.get("mtime_ns")) is int
        and formal_runtime.SHA256_PATTERN.fullmatch(
            str(value.get("sha256", ""))
        )
        is not None
    )


def file_identity_matches(
    expected: object,
    *,
    require_private: bool = True,
) -> bool:
    """重新開啟 exact path，確認 path/inode/content/owner/mode 未漂移。"""
    if not valid_file_identity_record(expected):
        return False
    assert isinstance(expected, dict)
    try:
        return (
            capture_file_identity(
                Path(str(expected["path"])),
                require_private=require_private,
            )
            == expected
        )
    except RuntimeActivationError:
        return False


def _write_private_json(path: Path, payload: Mapping[str, Any]) -> None:
    """file fsync → replace → parent fsync → exact readback。"""
    if not path.is_absolute():
        raise RuntimeActivationError("action receipt path must be absolute")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        encoded = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise OSError("action receipt write made no progress")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
        _fsync_directory(path.parent)
        try:
            readback = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise OSError("action receipt readback failed") from error
        if readback != dict(payload) or not _is_private_file(path):
            raise OSError("action receipt durable readback mismatch")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def load_action_receipt(path: Path) -> dict[str, Any]:
    """讀取 private action receipt；不接受 symlink、寬鬆權限或非 object。"""
    if not path.is_absolute() or not _is_private_file(path):
        raise RuntimeActivationError("action receipt identity is invalid")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeActivationError("action receipt is unreadable") from error
    if not isinstance(payload, dict):
        raise RuntimeActivationError("action receipt must be an object")
    return payload


def _validate_owned_roots(owned_roots: Mapping[str, object]) -> tuple[str, ...]:
    if set(owned_roots) != set(OWNED_ROOT_FIELDS):
        raise RuntimeActivationError("runtime owned roots are incomplete")
    roots: list[str] = []
    for field in OWNED_ROOT_FIELDS:
        value = owned_roots[field]
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise RuntimeActivationError(f"runtime owned root is invalid: {field}")
        roots.append(str(Path(value).resolve(strict=True)))
    return tuple(roots)


def _load_boundary_record(path: Path, *, maintenance: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "processes": {},
            "groups": [],
            "seen_labels": [],
            "resample_required": False,
        }
    payload = json.loads(_exact_bytes(path)) if maintenance else load_action_receipt(path)
    if not isinstance(payload, dict):
        raise RuntimeActivationError("process boundary journal is invalid")
    if maintenance:
        # 僅 bound maintenance 接受 upstream 舊 journal 的缺省 metadata；不發布此投影。
        payload.setdefault("schema_version", 1)
        payload.setdefault("resample_required", False)
    if (
        payload.get("schema_version") != 1
        or not isinstance(payload.get("processes"), dict)
        or not isinstance(payload.get("groups"), list)
        or not isinstance(payload.get("seen_labels"), list)
        or not isinstance(payload.get("resample_required"), bool)
    ):
        raise RuntimeActivationError("process boundary journal is invalid")
    return payload


def _process_birth_identity(
    pid: int,
    row: Mapping[str, Any],
    record: dict[str, Any],
) -> list[int] | None:
    """以 libproc birth identity 關閉 PID reuse／ps→identity race。"""
    value = ProcessBirth()
    library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    library.proc_pidinfo.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    ctypes.set_errno(0)
    count = library.proc_pidinfo(
        pid,
        3,
        0,
        ctypes.byref(value),
        ctypes.sizeof(value),
    )
    error_number = ctypes.get_errno()
    previous = record["processes"].get(str(pid))
    if count != ctypes.sizeof(value):
        if error_number == errno.ESRCH:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                if not previous:
                    record["processes"][str(pid)] = {"birth": None, **dict(row)}
                record["resample_required"] = True
                return None
            except OSError as probe_error:
                raise RuntimeActivationError(
                    "process identity UNKNOWN: "
                    f"{pid}: bytes={count}, errno={error_number}, "
                    f"confirmation_errno={probe_error.errno}"
                ) from probe_error
            raise RuntimeActivationError(
                f"process identity UNKNOWN: {pid}: bytes={count}, "
                f"errno={error_number}, still_present=1"
            )
        raise RuntimeActivationError(
            f"process identity UNKNOWN: {pid}: bytes={count}, errno={error_number}"
        )
    birth = [int(value.sec), int(value.usec)]
    if value.pid != pid or not value.sec:
        raise RuntimeActivationError(f"process identity UNKNOWN: {pid}")
    if previous and previous.get("birth") != birth:
        raise RuntimeActivationError(f"PID reuse: {pid}")
    if not previous and (
        value.ppid != int(row["ppid"]) or value.pgid != int(row["pgid"])
    ):
        raise RuntimeActivationError(f"unobserved process ancestry UNKNOWN: {pid}")
    return birth


def run_process_boundary(
    *,
    journal_path: Path,
    timeout_seconds: float,
    domain: str,
    owned_roots: Mapping[str, object],
    mode: str,
    arguments: Sequence[str],
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """唯一 process identity／descendant／orphan boundary；UNKNOWN 一律 fail closed。"""
    if (
        not journal_path.is_absolute()
        or not 0 < timeout_seconds <= 300
        or not domain.startswith("gui/")
        or mode not in {"observe", "drain", "control", "absent", "reconcile"}
    ):
        raise RuntimeActivationError("process boundary arguments are invalid")
    roots = _validate_owned_roots(owned_roots)
    labels_or_control = [str(value) for value in arguments]
    if not labels_or_control:
        raise RuntimeActivationError("process boundary arguments are empty")
    maintenance = None
    if mode == "reconcile":
        try:
            binding_path = Path(os.environ["PANTHEON_MAINTENANCE_BINDING"])
            maintenance_fd = int(os.environ["PANTHEON_MAINTENANCE_LEASE_FD"])
        except (KeyError, ValueError) as error:
            raise RuntimeActivationError("maintenance binding/lease is required") from error
        binding, manifest, token = maintenance_binding(binding_path)
        _require(
            journal_path == Path(binding["stage_path"]) / "normal-rollback-drain.json"
            and domain == f"gui/{os.getuid()}"
            and labels_or_control == list(formal_runtime.SERVICE_LABELS)
            and roots == _validate_owned_roots({field: manifest[field] for field in OWNED_ROOT_FIELDS}),
            "maintenance observer binding mismatch",
        )
        maintenance_lease(binding, manifest, maintenance_fd)
        maintenance_control(binding, manifest, maintenance_fd)
        maintenance = (binding, manifest, token, maintenance_fd)
    record = _load_boundary_record(journal_path, maintenance=maintenance is not None)
    if record.get("status") == "UNKNOWN_OR_FAILED" and maintenance is None:
        raise RuntimeActivationError(
            "prior process evidence is unresolved: " + str(record.get("error", "unknown"))
        )
    now = time.monotonic()
    if mode == "drain" and "deadline" not in record:
        record["deadline"] = now + timeout_seconds
        _write_private_json(journal_path, record)
    deadline = now + timeout_seconds if maintenance else float(record.get("deadline", now + timeout_seconds))

    def save() -> None:
        # maintenance 保留原 UNKNOWN/archive bytes；唯一發布點是既有原語。
        if maintenance is None:
            _write_private_json(journal_path, record)

    def remaining() -> float:
        value = deadline - time.monotonic()
        if value <= 0:
            raise RuntimeActivationError("process drain deadline exceeded")
        return min(value, 5.0)

    def command(argv: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            if maintenance:
                binding, manifest, _token, fd = maintenance
                maintenance_lease(binding, manifest, fd)
            if runner is not None:
                result = runner(argv)
            else:
                result = subprocess.run(
                    argv, check=False, capture_output=True, text=True,
                    timeout=remaining(), pass_fds=(fd,) if maintenance else (),
                )
            if maintenance:
                maintenance_lease(binding, manifest, fd)
            return result
        except subprocess.TimeoutExpired as error:
            raise RuntimeActivationError(
                f"command outcome UNKNOWN: {argv[:2]}"
            ) from error

    def services() -> dict[str, tuple[int | None, str]]:
        result: dict[str, tuple[int | None, str]] = {}
        for label in labels_or_control:
            target = f"{domain}/{label}"
            reply = command(["launchctl", "print", target])
            if reply.returncode in {3, 113}:
                result[label] = (None, "ABSENT")
                continue
            if reply.returncode != 0:
                raise RuntimeActivationError(
                    f"service state UNKNOWN: {label}: {reply.returncode}"
                )
            identity = parse_launchctl_service_identity(
                reply.stdout,
                expected_target=target,
            )
            if (
                identity is None
                or len(identity["pids"]) > 1
                or len(identity["states"]) != 1
                or len(identity["runs"]) != 1
            ):
                raise RuntimeActivationError(
                    f"service process evidence UNKNOWN: {label}"
                )
            if identity["pids"]:
                result[label] = (int(identity["pids"][0]), identity["states"][0])
            elif (
                identity["states"][0] in TERMINAL_SERVICE_STATES
                or identity["states"][0] == "xpcproxy"
            ):
                result[label] = (None, identity["states"][0])
            else:
                raise RuntimeActivationError(f"service PID UNKNOWN: {label}")
        return result

    def pending_observation() -> list[int]:
        """未穩定的取樣只保留舊 lineage；不得提升新 birth／group 或宣稱無殘留。"""
        remaining()
        record.update(status="OBSERVED", resample_required=True, sampled_at=time.time())
        save()
        return list(record.get("active", []))

    def missing_known_pids_are_absent(rows: Mapping[int, Any]) -> bool:
        """ps 漏掉的 durable lineage 只能以既有 targeted birth／kill0 證明消失。"""
        observed = {**record, "processes": dict(record["processes"])}
        for known_pid, previous in record["processes"].items():
            if int(known_pid) not in rows:
                if _process_birth_identity(int(known_pid), previous, observed) is not None:
                    return False
        return True

    def observe() -> list[int]:
        remaining()
        first = services()
        reply = command(["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,command="])
        if reply.returncode != 0:
            raise RuntimeActivationError("process snapshot UNKNOWN")
        rows: dict[int, dict[str, Any]] = {}
        for line in reply.stdout.splitlines():
            fields = line.split(None, 4)
            if len(fields) != 5 or not all(value.isdigit() for value in fields[:3]):
                raise RuntimeActivationError("process snapshot grammar UNKNOWN")
            pid, parent, group = map(int, fields[:3])
            rows[pid] = {
                "ppid": parent,
                "pgid": group,
                "zombie": fields[3].startswith("Z"),
                "command": fields[4],
            }
        if maintenance:
            # 已 bound 的 known PID 即使漏於 ps，也須 targeted libproc／kill0 證明。
            _require(missing_known_pids_are_absent(rows), "maintenance cohort not terminal: known PID absent from snapshot but still present")
        excluded = {os.getpid()}
        parent = os.getpid()
        while parent in rows and rows[parent]["ppid"] not in excluded:
            parent = int(rows[parent]["ppid"])
            excluded.add(parent)
        diagnostic = {os.getpid()}
        while True:
            added = {
                pid for pid, row in rows.items() if row["ppid"] in diagnostic
            } - diagnostic
            if not added:
                break
            diagnostic |= added
        excluded |= diagnostic
        cwd = command(
            ["/usr/sbin/lsof", "-a", "-u", str(os.getuid()), "-d", "cwd", "-Fpn"]
        )
        if cwd.returncode != 0:
            raise RuntimeActivationError("runtime cwd observation UNKNOWN")
        selected: int | None = None
        for line in cwd.stdout.splitlines():
            if line.startswith("p") and line[1:].isdigit():
                selected = int(line[1:])
            elif line == "fcwd":
                continue
            elif line.startswith("n") and selected is not None:
                if selected in rows:
                    rows[selected]["cwd"] = line[1:]
            else:
                raise RuntimeActivationError("cwd observation grammar UNKNOWN")
        owned = {
            pid
            for pid, row in rows.items()
            if pid not in excluded
            and any(
                row.get("cwd") == root
                or str(row.get("cwd", "")).startswith(root + "/")
                or root + "/" in str(row["command"])
                for root in roots
            )
        }
        second = services()
        if first != second or any(
            state == "xpcproxy" for _pid, state in [*first.values(), *second.values()]
        ):
            return pending_observation()
        seeds = {
            pid for pid, _state in [*first.values(), *second.values()] if pid is not None
        }
        if seeds - rows.keys():
            raise RuntimeActivationError(
                "unobserved service PID missing from process snapshot"
            )
        if not maintenance and not missing_known_pids_are_absent(rows):
            return pending_observation()
        record["resample_required"] = False
        active = (
            owned
            | (seeds & rows.keys())
            | {int(pid) for pid in record["processes"] if int(pid) in rows}
        )
        tracked = {int(pid) for pid in record["processes"]}
        groups = {int(value) for value in record["groups"]}
        while True:
            previous = set(active)
            groups |= {int(rows[pid]["pgid"]) for pid in active}
            if any(group <= 1 or group == os.getpgrp() for group in groups):
                raise RuntimeActivationError("service process group ownership UNKNOWN")
            active |= {
                pid
                for pid, row in rows.items()
                if pid not in excluded
                and (
                    row["ppid"] in active
                    or row["ppid"] in tracked
                    or row["pgid"] in groups
                )
            }
            if previous == active:
                break
        alive: list[int] = []
        # 所有 birth 完成驗證前只暫存；消失或失敗不能污染持久 lineage。
        observation_record = {**record, "processes": dict(record["processes"])}
        for pid in active:
            row = rows[pid]
            birth = _process_birth_identity(pid, row, observation_record)
            if birth is None:
                if str(pid) not in record["processes"]:
                    raise RuntimeActivationError(
                        f"unobserved process birth missing from stable snapshot: {pid}"
                    )
                return pending_observation()
            previous = record["processes"].get(str(pid))
            if previous and previous.get("birth") != birth:
                raise RuntimeActivationError(f"PID reuse: {pid}")
            observation_record["processes"][str(pid)] = {"birth": birth, **row}
            if not row["zombie"]:
                alive.append(pid)
        remaining()
        record["processes"] = observation_record["processes"]
        for label, (pid, _state) in {**first, **second}.items():
            if (
                pid is not None
                and str(pid) in record["processes"]
                and label not in record["seen_labels"]
            ):
                record["seen_labels"].append(label)
        record.update(
            groups=sorted(groups),
            active=sorted(alive),
            sampled_at=time.time(),
        )
        save()
        return alive

    try:
        if maintenance:
            active = observe()
            _require(not active and not record["resample_required"], "maintenance cohort not terminal")
            binding, manifest, token, fd = maintenance
            current_binding, current_manifest, current_token = maintenance_binding(binding_path)
            _require(
                current_binding == binding and current_manifest == manifest and current_token == token,
                "maintenance binding changed during observation",
            )
            maintenance_control(binding, manifest, fd)
            remaining()
            maintenance_publish_journal(binding, token, fd, manifest)
            return {"status": "DRAINED", "active": [], "journal": str(journal_path)}
        if mode == "absent":
            result = command(["launchctl", "print", *labels_or_control])
            if result.returncode not in {3, 113}:
                raise RuntimeActivationError(
                    f"service absence UNKNOWN: {result.returncode}"
                )
            return {"status": "ABSENT", "returncode": result.returncode}
        if mode == "control":
            result = command(["launchctl", *labels_or_control])
            if result.returncode != 0:
                raise RuntimeActivationError(
                    f"launchctl control failed: {result.returncode}"
                )
            return {
                "status": "PASS",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        if mode == "observe":
            active = observe()
            return {
                "status": "OBSERVED",
                "active": active,
                "resample_required": bool(record["resample_required"]),
                "seen_labels": list(record["seen_labels"]),
                "journal": str(journal_path),
            }
        while True:
            active = observe()
            if not active and not record["resample_required"]:
                break
            time.sleep(min(0.1, remaining()))
        record["status"] = "DRAINED"
        save()
        return {
            "status": "DRAINED",
            "active": [],
            "seen_labels": list(record["seen_labels"]),
            "journal": str(journal_path),
        }
    except Exception as error:
        record.update(
            status="UNKNOWN_OR_FAILED",
            error=f"{type(error).__name__}: {error}",
            sampled_at=time.time(),
        )
        try:
            save()
        except Exception as write_error:
            raise RuntimeActivationError(
                f"{record['error']}; journal: {type(write_error).__name__}: {write_error}"
            ) from error
        if isinstance(error, RuntimeActivationError):
            raise
        raise RuntimeActivationError(str(error)) from error


def _validate_action_inputs(
    *,
    labels: Sequence[str],
    plist_paths: Mapping[str, Path],
    owned_roots: Mapping[str, object],
    state_root: Path,
    receipt_path: Path,
) -> tuple[list[str], dict[str, Path]]:
    selected = [str(label) for label in labels]
    if (
        not selected
        or len(selected) != len(set(selected))
        or any(label not in formal_runtime.SERVICE_LABELS for label in selected)
    ):
        raise RuntimeActivationError("capacity action labels are invalid")
    if not state_root.is_absolute() or state_root.resolve(strict=True) != state_root:
        raise RuntimeActivationError("capacity action state root is invalid")
    if not receipt_path.is_absolute():
        raise RuntimeActivationError("capacity action receipt path is invalid")
    _validate_owned_roots(owned_roots)
    normalized: dict[str, Path] = {}
    for label in selected:
        path = plist_paths.get(label)
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or not path.is_file()
            or path.resolve(strict=True) != path
            or path.is_symlink()
        ):
            raise RuntimeActivationError(f"capacity action plist is invalid: {label}")
        normalized[label] = path
    return selected, normalized


def _normalize_action_authority(
    authority: Mapping[str, Any],
    *,
    labels: Sequence[str],
    plist_paths: Mapping[str, Path],
    generation: str,
    manifest_digest: str,
    runtime_identity_digest: str,
) -> dict[str, Any]:
    """鎖定本次 mutation 可用的 immutable runtime authority。"""
    if (
        authority.get("schema_version") != 1
        or authority.get("generation") != generation
        or authority.get("manifest_digest") != manifest_digest
        or authority.get("runtime_identity_digest") != runtime_identity_digest
        or not valid_file_identity_record(authority.get("manifest_file"))
        or not valid_file_identity_record(authority.get("barrier"))
        or not isinstance(authority.get("plists"), Mapping)
    ):
        raise RuntimeActivationError("runtime action authority is invalid")
    raw_plists = authority["plists"]
    normalized_plists: dict[str, dict[str, Any]] = {}
    for label in labels:
        record = raw_plists.get(label)
        if (
            not valid_file_identity_record(record)
            or Path(str(record["path"])) != plist_paths[label]
        ):
            raise RuntimeActivationError(
                f"runtime action plist authority is invalid: {label}"
            )
        normalized_plists[label] = dict(record)
    return {
        "schema_version": 1,
        "generation": generation,
        "manifest_digest": manifest_digest,
        "runtime_identity_digest": runtime_identity_digest,
        "manifest_file": dict(authority["manifest_file"]),
        "barrier": dict(authority["barrier"]),
        "plists": normalized_plists,
    }


def _assert_static_authority(
    authority: Mapping[str, Any],
    *,
    labels: Sequence[str],
) -> None:
    """每個 launchctl side effect 緊鄰前後都重驗 exact runtime bytes。"""
    if not file_identity_matches(authority.get("manifest_file")):
        raise RuntimeActivationError("runtime authority drift: manifest_file")
    if not file_identity_matches(authority.get("barrier")):
        raise RuntimeActivationError("runtime authority drift: barrier")
    plists = authority.get("plists")
    if not isinstance(plists, Mapping):
        raise RuntimeActivationError("runtime authority drift: plists")
    for label in labels:
        if not file_identity_matches(plists.get(label)):
            raise RuntimeActivationError(f"runtime authority drift: plist:{label}")


def _same_launchctl_root_identity(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> bool:
    """process drain 後的 launchd root identity 必須保持 exact stable fields。"""
    if expected.get("topology") != "LOADED" or actual.get("topology") != "LOADED":
        return False
    return all(
        actual.get(field) == expected.get(field)
        for field in ("label", "target", "identity")
    )


def _action_identity(
    *,
    action: str,
    incident_id: str,
    generation: str,
    manifest_digest: str,
    runtime_identity_digest: str,
    labels: Sequence[str],
    owned_roots: Mapping[str, object],
    receipt_path: Path,
    domain: str,
) -> dict[str, Any]:
    if (
        not incident_id
        or incident_id.strip() != incident_id
        or formal_runtime.GENERATION_PATTERN.fullmatch(generation) is None
        or formal_runtime.SHA256_PATTERN.fullmatch(manifest_digest) is None
        or formal_runtime.SHA256_PATTERN.fullmatch(runtime_identity_digest) is None
    ):
        raise RuntimeActivationError("capacity action identity is invalid")
    return {
        "schema_version": ACTION_RECEIPT_SCHEMA_VERSION,
        "action": action,
        "incident_id": incident_id,
        "generation": generation,
        "manifest_digest": manifest_digest,
        "runtime_identity_digest": runtime_identity_digest,
        "labels": list(labels),
        "owned_roots": dict(owned_roots),
        "domain": domain,
        "receipt_path": str(receipt_path),
        "created_epoch": time.time(),
        "updated_epoch": time.time(),
    }


def _inherit_resume_process_lineage(
    resume_identity: Mapping[str, Any],
    stop_receipt: Mapping[str, Any],
    journal_path: Path,
    previous_stop: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """只從同 action scope 的 private resume receipt 衍生 lineage；UNKNOWN 不可換檔清除。"""
    if not file_identity_matches(resume_identity):
        raise RuntimeActivationError("prior resume action receipt identity drift")
    source_path = Path(str(resume_identity["path"]))
    prior = load_action_receipt(source_path)
    fields = ("incident_id", "generation", "manifest_digest", "runtime_identity_digest", "owned_roots", "domain")
    source_labels = prior.get("labels")
    attempted = prior.get("attempted_labels")
    selected = stop_receipt["labels"]
    if (
        prior.get("schema_version") != ACTION_RECEIPT_SCHEMA_VERSION
        or prior.get("action") != "capacity-resume"
        or prior.get("receipt_path") != str(source_path)
        or prior.get("status") not in {"STARTED", "PARTIAL", "STARTING"}
        or any(prior.get(field) != stop_receipt[field] for field in fields)
        or not isinstance(source_labels, list)
        or not all(isinstance(label, str) for label in source_labels)
        or len(source_labels) != len(set(source_labels))
        or not set(selected) <= set(source_labels)
        or not isinstance(attempted, list)
        or not all(isinstance(label, str) for label in attempted)
        or not set(attempted) <= set(selected)
    ):
        raise RuntimeActivationError("prior resume action scope mismatch")
    prior_authority = _normalize_action_authority(
        prior.get("authority", {}), labels=selected,
        plist_paths={label: Path(stop_receipt["authority"]["plists"][label]["path"]) for label in selected},
        generation=stop_receipt["generation"], manifest_digest=stop_receipt["manifest_digest"],
        runtime_identity_digest=stop_receipt["runtime_identity_digest"],
    )
    if prior_authority != stop_receipt["authority"]:
        raise RuntimeActivationError("prior resume action authority mismatch")
    source_journal = source_path.with_name(f".{source_path.name}.verification-processes.json")
    if prior.get("process_journal_path") != str(source_journal) or not source_journal.exists():
        raise RuntimeActivationError("prior resume process journal binding is invalid")
    source = _load_boundary_record(source_journal)
    target = _load_boundary_record(journal_path)
    for record in (source, target):
        if record.get("status") == "UNKNOWN_OR_FAILED":
            raise RuntimeActivationError("prior process evidence is unresolved: " + str(record.get("error", "unknown")))
        valid_processes = all(
            isinstance(pid, str) and pid.isdigit() and str(int(pid)) == pid and int(pid) > 1
            and isinstance(process, dict)
            and isinstance(process.get("birth"), list) and len(process["birth"]) == 2
            and all(type(value) is int for value in process["birth"])
            and process["birth"][0] > 0 and process["birth"][1] >= 0
            and type(process.get("ppid")) is int and process["ppid"] >= 0
            and type(process.get("pgid")) is int and process["pgid"] > 1
            for pid, process in record["processes"].items()
        )
        if (
            not valid_processes
            or not all(type(group) is int and group > 1 for group in record["groups"])
            or not all(isinstance(label, str) and label in source_labels for label in record["seen_labels"])
            or not all(type(pid) is int and str(pid) in record["processes"] for pid in record.get("active", []))
            or ("deadline" in record and (type(record["deadline"]) not in {int, float} or not math.isfinite(record["deadline"])))
        ):
            raise RuntimeActivationError("prior process lineage is invalid")
    if journal_path.exists():
        if (
            previous_stop is None or previous_stop.get("action") != "capacity-stop"
            or previous_stop.get("receipt_path") != stop_receipt["receipt_path"]
            or previous_stop.get("process_journal_path") != str(journal_path)
            or any(previous_stop.get(field) != stop_receipt[field] for field in (*fields, "labels", "authority"))
        ):
            raise RuntimeActivationError("prior stop process journal scope mismatch")
    merged = {**target, "processes": dict(target["processes"])}
    for pid, process in source["processes"].items():
        if pid in merged["processes"] and merged["processes"][pid].get("birth") != process.get("birth"):
            raise RuntimeActivationError(f"prior process lineage identity conflict: {pid}")
        merged["processes"][pid] = dict(process)
    merged.update(
        groups=sorted(set(source["groups"]) | set(target["groups"])),
        seen_labels=list(dict.fromkeys([*target["seen_labels"], *source["seen_labels"]])),
        active=sorted(set(source.get("active", [])) | set(target.get("active", []))),
        resample_required=source["resample_required"] or target["resample_required"],
    )
    deadlines = [record["deadline"] for record in (source, target) if "deadline" in record]
    if deadlines:
        merged["deadline"] = min(deadlines)
    if not file_identity_matches(resume_identity):
        raise RuntimeActivationError("prior resume action receipt identity drift")
    _write_private_json(journal_path, merged)
    return {"resume_action_receipt": dict(resume_identity), "process_journal_path": str(source_journal)}


def stop_capacity_services(
    labels: Sequence[str],
    *,
    plist_paths: Mapping[str, Path],
    authority: Mapping[str, Any],
    owned_roots: Mapping[str, object],
    state_root: Path,
    receipt_path: Path,
    incident_id: str,
    generation: str,
    manifest_digest: str,
    runtime_identity_digest: str,
    timeout_seconds: float,
    runner: CommandRunner,
    domain: str | None = None,
    allow_absent: bool = False,
    resume_action_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """canonical stop；復機後 rollback 須交付綁定的 resume receipt，延續原 lineage。"""
    formal_runtime.assert_runtime_shutdown_lease(state_root)
    selected, normalized = _validate_action_inputs(
        labels=labels,
        plist_paths=plist_paths,
        owned_roots=owned_roots,
        state_root=state_root,
        receipt_path=receipt_path,
    )
    action_authority = _normalize_action_authority(
        authority,
        labels=selected,
        plist_paths=normalized,
        generation=generation,
        manifest_digest=manifest_digest,
        runtime_identity_digest=runtime_identity_digest,
    )
    selected_domain = domain or f"gui/{os.getuid()}"
    receipt = {
        **_action_identity(
            action="capacity-stop",
            incident_id=incident_id,
            generation=generation,
            manifest_digest=manifest_digest,
            runtime_identity_digest=runtime_identity_digest,
            labels=selected,
            owned_roots=owned_roots,
            receipt_path=receipt_path,
            domain=selected_domain,
        ),
        "status": "PREPARED",
        "mutation_started": False,
        "pre_stop": {},
        "mutation_authority": {},
        "services": {},
        "process_drain": {},
        "stopped_labels": [],
        "already_absent_labels": [],
        "authority": action_authority,
    }
    journal_path = receipt_path.with_name(f".{receipt_path.name}.processes.json")
    previous_stop = load_action_receipt(receipt_path) if receipt_path.exists() else None
    if journal_path.exists():
        # 驗證前不可覆寫舊 action metadata，否則重試會把不屬本 scope 的 journal 洗成合法。
        bound_fields = ("schema_version", "action", "incident_id", "generation", "manifest_digest",
                        "runtime_identity_digest", "labels", "owned_roots", "domain", "receipt_path", "authority")
        if (
            previous_stop is None or previous_stop.get("process_journal_path") != str(journal_path)
            or any(previous_stop.get(field) != receipt[field] for field in bound_fields)
        ):
            raise RuntimeActivationError("prior stop process journal scope mismatch")
    receipt["process_journal_path"] = str(journal_path)
    _write_private_json(receipt_path, receipt)
    try:
        _assert_static_authority(action_authority, labels=selected)
        if resume_action_receipt is not None:
            receipt["prior_lineage"] = _inherit_resume_process_lineage(
                resume_action_receipt, receipt, journal_path, previous_stop,
            )
        for label in selected:
            observation = observe_launchctl_service(
                label,
                normalized[label],
                runner=runner,
                domain=selected_domain,
            )
            receipt["pre_stop"][label] = observation
            if observation["topology"] == "ABSENT" and allow_absent:
                continue
            if observation["topology"] != "LOADED":
                raise RuntimeActivationError(
                    f"capacity stop target identity changed before mutation: {label}"
                )
        receipt["status"] = "DRAINING"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        receipt["process_drain"]["before_bootout"] = run_process_boundary(
            journal_path=journal_path,
            timeout_seconds=timeout_seconds,
            domain=selected_domain,
            owned_roots=owned_roots,
            mode="drain",
            arguments=selected,
            runner=runner,
        )
        _assert_static_authority(action_authority, labels=selected)
        for label in selected:
            observation = observe_launchctl_service(
                label,
                normalized[label],
                runner=runner,
                domain=selected_domain,
            )
            if observation["topology"] == "ABSENT" and allow_absent:
                receipt["mutation_authority"][label] = observation
                continue
            if (
                observation["topology"] != "LOADED"
                or observation.get("identity", {}).get("pids") != []
            ):
                raise RuntimeActivationError(
                    f"capacity stop root identity is not quiescent: {label}"
                )
            receipt["mutation_authority"][label] = observation
        receipt["status"] = "STOPPING"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        for label in selected:
            formal_runtime.assert_runtime_shutdown_lease(state_root)
            _assert_static_authority(action_authority, labels=selected)
            current = observe_launchctl_service(
                label,
                normalized[label],
                runner=runner,
                domain=selected_domain,
            )
            expected = receipt["mutation_authority"][label]
            if expected["topology"] == "ABSENT":
                if current["topology"] != "ABSENT":
                    raise RuntimeActivationError(
                        f"capacity rollback absence identity changed: {label}"
                    )
                receipt["already_absent_labels"].append(label)
                receipt["services"][label] = {
                    "bootout_returncode": None,
                    "post_stop": current,
                    "already_absent": True,
                }
                receipt["stopped_labels"].append(label)
                receipt["updated_epoch"] = time.time()
                _write_private_json(receipt_path, receipt)
                continue
            if not _same_launchctl_root_identity(expected, current):
                raise RuntimeActivationError(
                    f"capacity stop root identity drift before mutation: {label}"
                )
            receipt["mutation_started"] = True
            receipt["updated_epoch"] = time.time()
            _write_private_json(receipt_path, receipt)
            target = f"{selected_domain}/{label}"
            try:
                bootout = runner(["launchctl", "bootout", target])
                bootout_returncode: int | None = bootout.returncode
            except OSError:
                bootout_returncode = None
            _assert_static_authority(action_authority, labels=selected)
            observation = observe_launchctl_service(
                label,
                None,
                runner=runner,
                domain=selected_domain,
            )
            receipt["services"][label] = {
                "bootout_returncode": bootout_returncode,
                "post_stop": observation,
            }
            if observation["topology"] != "ABSENT":
                raise RuntimeActivationError(
                    f"capacity stop absence is unproven: {label}"
                )
            if bootout_returncode != 0:
                raise RuntimeActivationError(
                    f"capacity stop mutation outcome is unproven: {label}"
                )
            receipt["stopped_labels"].append(label)
            receipt["updated_epoch"] = time.time()
            _write_private_json(receipt_path, receipt)
        _assert_static_authority(action_authority, labels=selected)
        receipt["process_drain"]["after_bootout"] = run_process_boundary(
            journal_path=journal_path,
            timeout_seconds=timeout_seconds,
            domain=selected_domain,
            owned_roots=owned_roots,
            mode="drain",
            arguments=selected,
            runner=runner,
        )
        receipt["status"] = "STOPPED"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        return receipt
    except Exception as error:
        receipt["status"] = (
            "UNKNOWN_OR_FAILED" if receipt["mutation_started"] else "BLOCKED"
        )
        receipt["error"] = f"{type(error).__name__}: {error}"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        if isinstance(error, RuntimeActivationError):
            raise
        raise RuntimeActivationError(str(error)) from error


def _required_success_runs(identity: Mapping[str, list[Any]]) -> int:
    """復機成功必須來自 bootstrap baseline 之後的新一次 launchd run。"""
    return int(identity["runs"][0]) + 1


def resume_capacity_services(
    labels: Sequence[str],
    *,
    plist_paths: Mapping[str, Path],
    authority: Mapping[str, Any],
    owned_roots: Mapping[str, object],
    state_root: Path,
    receipt_path: Path,
    incident_id: str,
    generation: str,
    manifest_digest: str,
    runtime_identity_digest: str,
    runner: CommandRunner,
    domain: str | None = None,
) -> dict[str, Any]:
    """canonical resume：exact absence preflight 後 bootstrap；不宣稱 workload success。"""
    formal_runtime.assert_runtime_shutdown_lease(state_root)
    selected, normalized = _validate_action_inputs(
        labels=labels,
        plist_paths=plist_paths,
        owned_roots=owned_roots,
        state_root=state_root,
        receipt_path=receipt_path,
    )
    action_authority = _normalize_action_authority(
        authority,
        labels=selected,
        plist_paths=normalized,
        generation=generation,
        manifest_digest=manifest_digest,
        runtime_identity_digest=runtime_identity_digest,
    )
    selected_domain = domain or f"gui/{os.getuid()}"
    receipt = {
        **_action_identity(
            action="capacity-resume",
            incident_id=incident_id,
            generation=generation,
            manifest_digest=manifest_digest,
            runtime_identity_digest=runtime_identity_digest,
            labels=selected,
            owned_roots=owned_roots,
            receipt_path=receipt_path,
            domain=selected_domain,
        ),
        "status": "PREPARED",
        "mutation_started": False,
        "pre_resume": {},
        "services": {},
        "attempted_labels": [],
        "started_labels": [],
        "authority": action_authority,
        "process_journal_path": str(
            receipt_path.with_name(f".{receipt_path.name}.verification-processes.json")
        ),
    }
    _write_private_json(receipt_path, receipt)
    try:
        _assert_static_authority(action_authority, labels=selected)
        for label in selected:
            observation = observe_launchctl_service(
                label,
                None,
                runner=runner,
                domain=selected_domain,
            )
            receipt["pre_resume"][label] = observation
            if observation["topology"] != "ABSENT":
                raise RuntimeActivationError(
                    f"capacity resume target is not absent: {label}"
                )
        disabled = read_disabled_service_labels(
            selected,
            runner=runner,
            domain=selected_domain,
        )
        if disabled:
            raise RuntimeActivationError("owned_service_manually_disabled")
        receipt["status"] = "STARTING"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        for label in selected:
            formal_runtime.assert_runtime_shutdown_lease(state_root)
            _assert_static_authority(action_authority, labels=selected)
            disabled = read_disabled_service_labels(
                selected,
                runner=runner,
                domain=selected_domain,
            )
            if label in disabled:
                receipt["status"] = "PARTIAL" if receipt["mutation_started"] else "BLOCKED"
                receipt["failed_label"] = label
                receipt["error"] = "owned_service_manually_disabled"
                receipt["updated_epoch"] = time.time()
                _write_private_json(receipt_path, receipt)
                return receipt
            current = observe_launchctl_service(
                label,
                None,
                runner=runner,
                domain=selected_domain,
            )
            if current["topology"] != "ABSENT":
                receipt["status"] = (
                    "PARTIAL" if receipt["mutation_started"] else "BLOCKED"
                )
                receipt["failed_label"] = label
                receipt["error"] = "pre_bootstrap_service_identity_changed"
                receipt["updated_epoch"] = time.time()
                _write_private_json(receipt_path, receipt)
                return receipt
            receipt["attempted_labels"].append(label)
            receipt["mutation_started"] = True
            receipt["updated_epoch"] = time.time()
            _write_private_json(receipt_path, receipt)
            try:
                bootstrap = runner(
                    ["launchctl", "bootstrap", selected_domain, str(normalized[label])]
                )
                bootstrap_returncode: int | None = bootstrap.returncode
            except OSError:
                bootstrap_returncode = None
            service = {
                "bootstrap_returncode": bootstrap_returncode,
                "post_bootstrap": None,
                "baseline_runs": None,
                "required_success_runs": None,
                "lineage_capture": None,
            }
            receipt["services"][label] = service
            _assert_static_authority(action_authority, labels=selected)
            observation = observe_launchctl_service(
                label,
                normalized[label],
                runner=runner,
                domain=selected_domain,
            )
            service["post_bootstrap"] = observation
            if bootstrap_returncode != 0 or observation["topology"] != "LOADED":
                receipt["status"] = "PARTIAL"
                receipt["failed_label"] = label
                receipt["error"] = "bootstrap_or_identity_failed"
                receipt["updated_epoch"] = time.time()
                _write_private_json(receipt_path, receipt)
                return receipt
            identity = observation["identity"]
            assert isinstance(identity, dict)
            service["baseline_runs"] = int(identity["runs"][0])
            service["required_success_runs"] = _required_success_runs(identity)
            service["lineage_capture"] = run_process_boundary(
                journal_path=Path(str(receipt["process_journal_path"])),
                timeout_seconds=30.0,
                domain=selected_domain,
                owned_roots=owned_roots,
                mode="observe",
                arguments=[label],
                runner=runner,
            )
            _assert_static_authority(action_authority, labels=selected)
            receipt["started_labels"].append(label)
            receipt["updated_epoch"] = time.time()
            _write_private_json(receipt_path, receipt)
        receipt["status"] = "STARTED"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        return receipt
    except Exception as error:
        receipt["status"] = (
            "PARTIAL" if receipt["mutation_started"] else "BLOCKED"
        )
        receipt["error"] = f"{type(error).__name__}: {error}"
        receipt["updated_epoch"] = time.time()
        _write_private_json(receipt_path, receipt)
        if receipt["mutation_started"]:
            return receipt
        if isinstance(error, RuntimeActivationError):
            raise
        raise RuntimeActivationError(str(error)) from error


def verify_capacity_resume_execution(
    resume_receipt: Mapping[str, Any],
    *,
    runner: CommandRunner,
    timeout_seconds: float,
) -> dict[str, Any]:
    """跨 tick 驗證每個 exact label 至少一次成功 terminal run 與無殘留程序。"""
    if (
        resume_receipt.get("schema_version") != ACTION_RECEIPT_SCHEMA_VERSION
        or resume_receipt.get("action") != "capacity-resume"
        or resume_receipt.get("status") != "STARTED"
        or not isinstance(resume_receipt.get("labels"), list)
        or not isinstance(resume_receipt.get("services"), dict)
        or not isinstance(resume_receipt.get("owned_roots"), dict)
        or not isinstance(resume_receipt.get("domain"), str)
        or not isinstance(resume_receipt.get("process_journal_path"), str)
    ):
        raise RuntimeActivationError("capacity resume receipt is invalid")
    labels = [str(label) for label in resume_receipt["labels"]]
    services: dict[str, Any] = {}
    overall = "PASS"
    for label in labels:
        service_plan = resume_receipt["services"].get(label)
        if not isinstance(service_plan, dict):
            raise RuntimeActivationError("capacity resume service plan is invalid")
        post_bootstrap = service_plan.get("post_bootstrap")
        if not isinstance(post_bootstrap, dict):
            raise RuntimeActivationError("capacity resume bootstrap evidence is invalid")
        bootstrap_identity = post_bootstrap.get("identity")
        if not isinstance(bootstrap_identity, dict):
            raise RuntimeActivationError("capacity resume bootstrap identity is invalid")
        paths = bootstrap_identity.get("paths")
        baseline_runs = service_plan.get("baseline_runs")
        required_runs = service_plan.get("required_success_runs")
        if (
            not isinstance(paths, list)
            or len(paths) != 1
            or type(baseline_runs) is not int
            or baseline_runs < 0
            or type(required_runs) is not int
            or required_runs != baseline_runs + 1
        ):
            raise RuntimeActivationError("capacity resume execution threshold is invalid")
        observation = observe_launchctl_service(
            label,
            Path(str(paths[0])),
            runner=runner,
            domain=str(resume_receipt["domain"]),
        )
        service_status = "PENDING"
        reason = "successful_terminal_run_not_observed"
        if observation["topology"] == "ABSENT":
            service_status = "FAILED"
            reason = "service_disappeared_after_resume"
        elif observation["topology"] == "UNKNOWN":
            service_status = "UNKNOWN"
            reason = "service_identity_unknown"
        else:
            identity = observation["identity"]
            assert isinstance(identity, dict)
            runs = int(identity["runs"][0])
            state = str(identity["states"][0])
            exit_codes = [int(value) for value in identity["last_exit_codes"]]
            pids = [int(value) for value in identity["pids"]]
            if (
                runs >= required_runs
                and state in TERMINAL_SERVICE_STATES
                and not pids
                and exit_codes == [0]
            ):
                service_status = "PASS"
                reason = None
            elif (
                runs >= required_runs
                and state in TERMINAL_SERVICE_STATES
                and not pids
                and exit_codes
                and exit_codes != [0]
            ):
                service_status = "FAILED"
                reason = f"service_exit_nonzero:{exit_codes[0]}"
        services[label] = {
            "status": service_status,
            "reason": reason,
            "required_success_runs": required_runs,
            "observation": observation,
        }
        if service_status == "UNKNOWN":
            overall = "UNKNOWN"
        elif service_status == "FAILED" and overall != "UNKNOWN":
            overall = "FAILED"
        elif service_status == "PENDING" and overall == "PASS":
            overall = "PENDING"
    process_observation: dict[str, Any] | None = None
    lineage_missing_labels: list[str] = []
    if overall in {"PASS", "PENDING"}:
        try:
            process_observation = run_process_boundary(
                journal_path=Path(str(resume_receipt["process_journal_path"])),
                timeout_seconds=timeout_seconds,
                domain=str(resume_receipt["domain"]),
                owned_roots=resume_receipt["owned_roots"],
                mode="observe",
                arguments=labels,
                runner=runner,
            )
        except RuntimeActivationError as error:
            overall = "UNKNOWN"
            process_observation = {
                "status": "UNKNOWN",
                "error": str(error),
            }
        else:
            seen_labels = process_observation.get("seen_labels")
            if not isinstance(seen_labels, list) or any(
                not isinstance(label, str) for label in seen_labels
            ):
                overall = "UNKNOWN"
                process_observation = {
                    **process_observation,
                    "status": "UNKNOWN",
                    "error": "process lineage journal is invalid",
                }
            else:
                lineage_missing_labels = [
                    label for label in labels if label not in seen_labels
                ]
            if overall != "UNKNOWN" and (
                process_observation.get("active")
                or process_observation.get("resample_required")
                or lineage_missing_labels
            ):
                overall = "PENDING"
    return {
        "status": overall,
        "services": services,
        "process_observation": process_observation,
        "lineage_missing_labels": lineage_missing_labels,
        "sampled_epoch": time.time(),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    boundary = subparsers.add_parser("process-boundary")
    boundary.add_argument("--journal", type=Path, required=True)
    boundary.add_argument("--timeout", type=float, required=True)
    boundary.add_argument("--domain", required=True)
    boundary.add_argument("--manifest", type=Path, required=True)
    boundary.add_argument(
        "mode",
        choices=("observe", "drain", "control", "absent", "reconcile"),
    )
    boundary.add_argument("arguments", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        selected = sys.argv[1:] if argv is None else list(argv)
        if selected and selected[0] in {"run", "prepare", "restore", "finish"}:
            return _maintenance_main(selected)
        args = parse_args(selected)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise RuntimeActivationError("runtime manifest must be an object")
        result = run_process_boundary(
            journal_path=args.journal,
            timeout_seconds=args.timeout,
            domain=args.domain,
            owned_roots={field: manifest.get(field) for field in OWNED_ROOT_FIELDS},
            mode=args.mode,
            arguments=args.arguments,
        )
        if args.mode == "control":
            sys.stdout.write(str(result.get("stdout", "")))
            sys.stderr.write(str(result.get("stderr", "")))
        return 0
    except (OSError, json.JSONDecodeError, RuntimeActivationError, formal_runtime.RuntimeManifestError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

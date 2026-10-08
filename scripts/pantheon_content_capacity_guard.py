#!/usr/bin/env python3
"""監控 Pantheon 自動產文寫入面，超限時停用六個內容服務。"""

from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager, nullcontext
import ctypes
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import plistlib
import pwd
import re
import resource
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

from scripts import pantheon_content_runtime_manifest as formal_runtime
from scripts import pantheon_runtime_activation as runtime_activation


GIB = 1024**3
MIB = 1024**2
MAX_BYTES = 4 * GIB
MAX_FILE_COUNT = 120_000
NORMAL_GROWTH_BYTES_PER_HOUR = 256 * MIB
RECOVERY_WINDOW_SECONDS = 3600
DEFAULT_PROJECTED_BYTES = GIB
HOST_RESERVE_MIN_BYTES = 20 * GIB
CANONICAL_HOST_CAPACITY_SENSOR = (
    Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    / "ai-core/scripts/host_capacity_sensor.py"
)
SERVICE_TRANSITION_RECHECKS = 20
SERVICE_TRANSITION_RECHECK_SECONDS = 0.25
LOG_MAX_BYTES = 32 * MIB
LOG_RETAIN_BYTES = 4 * MIB
MEMORY_STEP_BYTES = 128 * MIB
RECOVERY_HEALTHY_SAMPLES = 4
RECOVERY_SAMPLE_MIN_SECONDS = 240
RECOVERY_PROJECTED_RESTART_BYTES = DEFAULT_PROJECTED_BYTES
MAX_AUTOMATIC_RECOVERY_ATTEMPTS = 1
RECOVERY_SHUTDOWN_TIMEOUT_SECONDS = 30.0
RECOVERY_POST_RESUME_HEALTHY_SAMPLES = 1
RECOVERY_EXECUTION_TIMEOUT_SECONDS = 900
# 已觀測新文工作需約 29 分鐘；容納一次排程取樣與收尾，仍保留有界停損。
RECOVERY_ACTIVE_RUN_TIMEOUT_SECONDS = 45 * 60
RECOVERY_RSS_GROWTH_LIMIT_BYTES = 512 * MIB
RECOVERY_SWAP_GROWTH_LIMIT_BYTES = 128 * MIB
OPEN_RECOVERY_STATUSES = frozenset(
    {
        "STOPPING",
        "STOPPED",
        "STOP_FAILED",
        "RECOVERY_PENDING",
        "RECOVERY_IN_PROGRESS",
        "RECOVERY_VERIFYING",
        "ROLLBACK_IN_PROGRESS",
        "OPERATOR_REQUIRED",
    }
)
SERVICE_LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
)
CAPACITY_GUARD_LABEL = "com.pantheon.content-capacity-guard"
ACTIVATION_CORRELATION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
PUBLISHER_RESET_RECEIPT_NAME = "publisher-reset-receipt.json"
PUBLISHER_RESET_RECEIPT_SCHEMA_VERSION = 1
PUBLISHER_RESET_TRANSITION = "TE-TARGET-STAGED-TO-QUIESCED"
LAUNCHCTL_OBJECT_START_PATTERN = re.compile(r"^[^{}]+ = \{$")
LAUNCHCTL_STATE_FIELD_PATTERN = re.compile(r"^state = ([^\r\n]+)$")
LAUNCHCTL_PATH_FIELD_PATTERN = re.compile(r"^path = ([^\r\n]+)$")
LAUNCHCTL_LAST_EXIT_CODE_FIELD_PATTERN = re.compile(r"^last exit code = (-?[0-9]+)$")
LOG_NAMES = tuple(
    f"{stem}.{stream}.log"
    for stem in (
        "agy-content-publisher",
        "agy-gemini-coordinator",
        "agy-gemini-new",
        "agy-gemini-rewrite",
        "agy-gemini-i18n-new",
        "agy-gemini-i18n-rewrite",
        "pantheon-content-capacity-guard",
    )
    for stream in ("stdout", "stderr")
)
Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]
SwapFallback = Callable[[], tuple[int | None, str | None]]
CapacitySensor = Callable[[Path], dict[str, Any]]


def _verify_private_lock(fd: int, path: Path, *, field: str) -> None:
    held = os.fstat(fd)
    current = path.lstat()
    if (
        not stat.S_ISREG(current.st_mode)
        or current.st_uid != os.getuid()
        or current.st_nlink != 1
        or stat.S_IMODE(current.st_mode) != 0o600
        or (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino)
    ):
        raise formal_runtime.RuntimeManifestError(f"{field} identity drift")


@contextmanager
def _state_writer_lock(state_file: Path):
    """同一 state file 僅允許一個 Guard tick 寫入或派送 mutation。"""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_file.with_name(f".{state_file.name}.lock")
    descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    try:
        _verify_private_lock(
            descriptor,
            lock_path,
            field="capacity guard state writer lock",
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise formal_runtime.RuntimeWorkBusy(
                "capacity guard state writer is busy"
            ) from error
        _verify_private_lock(
            descriptor,
            lock_path,
            field="capacity guard state writer lock",
        )
        yield
    finally:
        os.close(descriptor)


def _sampling_lease(publisher_root: Path):
    """正式 runtime 的 read-only sampling 受 shared lease 保護。"""
    if os.environ.get("PANTHEON_FORMAL_RUNTIME") != "1":
        return nullcontext()
    return formal_runtime.runtime_work_lease(publisher_root.resolve(strict=True))


def _host_capacity_sample(path: Path) -> dict[str, Any]:
    """使用 ai-core canonical sensor；macOS 量測失敗時不得降級為 raw。"""
    sensor_path = CANONICAL_HOST_CAPACITY_SENSOR
    module_name = f"_pantheon_host_capacity_sensor_{hashlib.sha256(str(sensor_path).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, sensor_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical host capacity sensor unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        capacity = module.measure_host_capacity(path)
    except Exception as error:
        raise RuntimeError("canonical host capacity measurement failed") from error
    return {
        "disk_total_bytes": capacity.total_bytes,
        "disk_free_bytes": capacity.physical_available_bytes,
        "admission_available_bytes": capacity.admission_available_bytes,
        "capacity_source": capacity.source,
        "capacity_available": True,
        "capacity_error": None,
    }


def _measure_tree(root: Path) -> tuple[int, int]:
    """不跟隨 symlink，回傳登記路徑的 bytes 與檔案數。"""
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return 0, 0
    if not root.is_dir() or root.is_symlink():
        return root_stat.st_size, 1
    total_bytes = 0
    file_count = 0
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = os.scandir(directory)
        except FileNotFoundError:
            continue
        with entries:
            for entry in entries:
                try:
                    stat_result = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                else:
                    total_bytes += stat_result.st_size
                    file_count += 1
    return total_bytes, file_count


def _trim_log(path: Path) -> int:
    """超限時保留同 inode 的末段 bytes，回傳釋放量。"""
    try:
        before = path.lstat()
    except FileNotFoundError:
        return 0
    if path.is_symlink() or not path.is_file() or before.st_size <= LOG_MAX_BYTES:
        return 0
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise RuntimeError("capacity guard log changed during rotation")
        retain = min(LOG_RETAIN_BYTES, opened.st_size)
        os.lseek(descriptor, opened.st_size - retain, os.SEEK_SET)
        tail = os.read(descriptor, retain)
        os.lseek(descriptor, 0, os.SEEK_SET)
        written = 0
        while written < len(tail):
            written += os.write(descriptor, tail[written:])
        os.ftruncate(descriptor, len(tail))
        os.fsync(descriptor)
        return opened.st_size - len(tail)
    finally:
        os.close(descriptor)


def _disk_sample(path: Path) -> tuple[int, int]:
    sample = os.statvfs(path)
    return sample.f_blocks * sample.f_frsize, sample.f_bavail * sample.f_frsize


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, check=False, capture_output=True, text=True,
        **formal_runtime.runtime_work_child_transport(),
    )


def _activation_only_service_labels(runtime_receipt: dict[str, Any]) -> frozenset[str]:
    if runtime_receipt.get("status") != "PASS":
        return frozenset()
    try:
        home = Path(
            os.environ.get("PANTHEON_USER_HOME_DIR")
            or pwd.getpwuid(os.getuid()).pw_dir
        ).resolve(strict=True)
        for label in formal_runtime.SERVICE_LABELS:
            with (home / "Library" / "LaunchAgents" / f"{label}.plist").open("rb") as stream:
                payload = plistlib.load(stream)
            arguments = payload.get("ProgramArguments")
            separator = arguments.index("--") if isinstance(arguments, list) and "--" in arguments else -1
            if (
                payload.get("Label") != label
                or separator < 0
                or arguments[:separator].count("--activation-only") != 1
            ):
                return frozenset()
    except OSError:
        return frozenset()
    except plistlib.InvalidFileException:
        return frozenset()
    return frozenset(SERVICE_LABELS)


def _normal_scheduled_service_labels(
    runtime_receipt: dict[str, Any],
) -> frozenset[str]:
    """只信任 manifest-bound、owner/mode 正確的正式 interval job。"""
    if runtime_receipt.get("status") != "PASS":
        return frozenset()
    try:
        manifest = formal_runtime.load_manifest(
            Path(os.environ["PANTHEON_RUNTIME_MANIFEST"]),
            os.environ["PANTHEON_RUNTIME_MANIFEST_DIGEST"],
        )
        if runtime_receipt.get("config_version") != manifest["config_version"]:
            return frozenset()
        home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
        plist_paths = [
            home / "Library" / "LaunchAgents" / f"{label}.plist"
            for label in formal_runtime.SERVICE_LABELS
        ]
        formal_runtime.aggregate_plist_preflight(
            manifest,
            plist_paths,
            expected_activation_mode="normal",
        )
        for label, path in zip(formal_runtime.SERVICE_LABELS, plist_paths):
            with path.open("rb") as stream:
                payload = plistlib.load(stream)
            interval = payload.get("StartInterval")
            if (
                payload.get("Label") != label
                or payload.get("RunAtLoad") is not True
                or type(interval) is not int
                or interval <= 0
                or "KeepAlive" in payload
            ):
                return frozenset()
    except (
        KeyError,
        OSError,
        plistlib.InvalidFileException,
        formal_runtime.RuntimeManifestError,
    ):
        return frozenset()
    return frozenset(SERVICE_LABELS)


def _launchctl_top_level_identity(
    output: str,
    *,
    expected_target: str,
) -> dict[str, list[Any]] | None:
    """沿用 canonical parser，並維持 Guard 既有的 stable identity 契約。"""
    identity = runtime_activation.parse_launchctl_service_identity(
        output,
        expected_target=expected_target,
    )
    if identity is None:
        return None
    return {
        "states": identity["states"],
        "paths": identity["paths"],
        "last_exit_codes": identity["last_exit_codes"],
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_identity(path: Path) -> dict[str, Any]:
    try:
        return runtime_activation.capture_file_identity(path, require_private=False)
    except runtime_activation.RuntimeActivationError as error:
        raise OSError(str(error)) from error


def _same_file_identity(expected: object) -> bool:
    return runtime_activation.file_identity_matches(
        expected,
        require_private=False,
    )


def _valid_file_identity_record(value: object) -> bool:
    return runtime_activation.valid_file_identity_record(value)


def _snapshot_launchctl_identity(output: str, *, expected_path: Path) -> dict[str, Any]:
    if re.search(r"^\s*pid = [1-9][0-9]*\s*$", output, re.MULTILINE):
        raise formal_runtime.RuntimeManifestError("publisher reset proof has pid")
    target = f"gui/{os.getuid()}/{expected_path.stem}"
    identity = _launchctl_top_level_identity(output, expected_target=target)
    if identity is None:
        raise formal_runtime.RuntimeManifestError("publisher reset identity mismatch")
    states = identity["states"]
    paths = identity["paths"]
    if paths != [str(expected_path)] or states not in (["not running"], ["waiting"]):
        raise formal_runtime.RuntimeManifestError("publisher reset identity mismatch")
    return {
        "states": states,
        "paths": paths,
        "last_exit_codes": identity["last_exit_codes"],
    }


def _live_receipt_aggregate(
    live_receipt: dict[str, Any],
    live_arguments: list[Any],
) -> dict[str, Any]:
    return {
        "identity": live_receipt.get("identity"),
        "manifest_digest": live_receipt.get("manifest_digest"),
        "runtime_identity_digest": live_receipt.get("runtime_identity_digest"),
        "runtime_digest": live_receipt.get("runtime_digest"),
        "config_version": live_receipt.get("config_version"),
        "generation": live_receipt.get("generation"),
        "actor_root": live_receipt.get("actor_root"),
        "queue_root": live_receipt.get("queue_root"),
        "publisher_state_root": live_receipt.get("publisher_state_root"),
        "log_root": live_receipt.get("log_root"),
        "actor_head": live_receipt.get("actor_head"),
        "python_executable": live_receipt.get("python_executable"),
        "uv_executable": live_receipt.get("uv_executable"),
        "barrier": formal_runtime._single_argument_value(live_arguments, "--barrier"),
        "manifest_path": formal_runtime._single_argument_value(
            live_arguments, "--manifest"
        ),
    }


def _publisher_reset_old_live_identity(aggregate: dict[str, Any]) -> dict[str, Any]:
    return {
        field: aggregate.get(field)
        for field in (
            "identity",
            "manifest_digest",
            "runtime_identity_digest",
            "runtime_digest",
            "config_version",
            "generation",
            "actor_root",
            "queue_root",
            "publisher_state_root",
            "log_root",
            "actor_head",
            "python_executable",
            "uv_executable",
            "barrier",
        )
    }


def write_publisher_reset_receipt(
    *,
    receipt_path: Path,
    correlation_id: str,
    manifest_path: Path,
    expected_digest: str,
    launch_agents_dir: Path,
    proof_dir: Path,
) -> dict[str, Any]:
    if ACTIVATION_CORRELATION_PATTERN.fullmatch(correlation_id) is None:
        raise formal_runtime.RuntimeManifestError("publisher reset correlation mismatch")
    manifest = formal_runtime.load_manifest(manifest_path, expected_digest)
    launch_agents = launch_agents_dir.resolve(strict=True)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    if receipt_path != stage_dir / PUBLISHER_RESET_RECEIPT_NAME:
        raise formal_runtime.RuntimeManifestError("publisher reset receipt path mismatch")
    if proof_dir != stage_dir / "publisher-reset-backups":
        raise formal_runtime.RuntimeManifestError("publisher reset proof path mismatch")
    try:
        stage_manifest_digest = (stage_dir / "manifest-digest").read_text(
            encoding="utf-8"
        ).strip()
        stage_generation = (stage_dir / "generation").read_text(
            encoding="utf-8"
        ).strip()
        publisher_exact_run_id = (stage_dir / "publisher-exact-run-id").read_text(
            encoding="utf-8"
        ).strip()
        publisher_max_runs = (stage_dir / "publisher-max-runs").read_text(
            encoding="utf-8"
        ).strip()
    except OSError as error:
        raise formal_runtime.RuntimeManifestError("publisher reset stage mismatch") from error
    if (
        stage_manifest_digest != manifest["manifest_digest"]
        or stage_generation != manifest["generation"]
        or not publisher_exact_run_id
        or publisher_max_runs != "1"
    ):
        raise formal_runtime.RuntimeManifestError("publisher reset stage mismatch")

    publisher_label = "com.pantheon.agy-content-publisher"
    live_aggregate: dict[str, Any] | None = None
    publisher_proof: dict[str, Any] | None = None
    other_six: list[dict[str, Any]] = []
    for label in formal_runtime.SERVICE_LABELS:
        live_path = launch_agents / f"{label}.plist"
        live_receipt = formal_runtime.plist_receipt(
            live_path,
            expected_activation_mode="activation-only",
        )
        with live_path.open("rb") as stream:
            live_payload = plistlib.load(stream)
        live_arguments = live_payload.get("ProgramArguments")
        if not isinstance(live_arguments, list):
            raise formal_runtime.RuntimeManifestError("publisher reset live mismatch")
        aggregate = _publisher_reset_old_live_identity(
            _live_receipt_aggregate(live_receipt, live_arguments)
        )
        if live_aggregate is None:
            live_aggregate = aggregate
        elif aggregate != live_aggregate:
            drift_fields = sorted(
                field
                for field in set(live_aggregate) | set(aggregate)
                if live_aggregate.get(field) != aggregate.get(field)
            )
            raise formal_runtime.RuntimeManifestError(
                "publisher reset live aggregate mismatch:"
                f"{label}:{','.join(drift_fields)}"
            )

        pre_plist = proof_dir / f"{label}.plist"
        pre_identity = proof_dir / f"{label}.identity"
        post_identity = proof_dir / f"{label}.post_identity"
        current_sha256 = _file_sha256(live_path)
        pre_sha256 = _file_sha256(pre_plist)
        post_snapshot = _snapshot_launchctl_identity(
            post_identity.read_text(encoding="utf-8"),
            expected_path=live_path,
        )
        if label == publisher_label:
            previous_loaded = (
                proof_dir / f"{publisher_label}.previous_loaded"
            ).read_text(encoding="utf-8").strip()
            if previous_loaded not in {"0", "1"}:
                raise formal_runtime.RuntimeManifestError(
                    "publisher reset previous state mismatch"
                )
            publisher_proof = {
                "pre_plist_sha256": pre_sha256,
                "post_plist_sha256": current_sha256,
                "post_plist_receipt": live_receipt,
                "post_launchctl_identity": post_snapshot,
                "previous_loaded": previous_loaded == "1",
            }
            continue
        if pre_sha256 != current_sha256:
            raise formal_runtime.RuntimeManifestError(
                "publisher reset other-service drift"
            )
        pre_snapshot = _snapshot_launchctl_identity(
            pre_identity.read_text(encoding="utf-8"),
            expected_path=live_path,
        )
        other_six.append(
            {
                "label": label,
                "pre_plist_sha256": pre_sha256,
                "post_plist_sha256": current_sha256,
                "pre_launchctl_identity": pre_snapshot,
                "post_launchctl_identity": post_snapshot,
            }
        )
    if live_aggregate is None or publisher_proof is None:
        raise formal_runtime.RuntimeManifestError("publisher reset live proof missing")
    old_generation = str(live_aggregate.get("generation", ""))
    generation_relation = (
        "target_same_generation"
        if old_generation == manifest["generation"]
        else "target_newer_than_live"
    )
    payload = {
        "schema_version": PUBLISHER_RESET_RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "transition": PUBLISHER_RESET_TRANSITION,
        "correlation_id": correlation_id,
        "target": {
            "manifest_digest": manifest["manifest_digest"],
            "runtime_identity_digest": manifest["runtime_identity_digest"],
            "generation": manifest["generation"],
            "publisher_exact_run_id": publisher_exact_run_id,
        },
        "old_live": {
            **live_aggregate,
            "generation_relation": generation_relation,
        },
        "publisher": publisher_proof,
        "other_six": other_six,
    }
    _write_state(receipt_path, payload)
    return payload


def _load_publisher_reset_receipt(
    receipt_path: Path,
    *,
    stage_dir: Path,
) -> dict[str, Any]:
    expected_path = stage_dir / PUBLISHER_RESET_RECEIPT_NAME
    try:
        if receipt_path != expected_path or receipt_path.is_symlink():
            raise formal_runtime.RuntimeManifestError(
                "publisher reset receipt path mismatch"
            )
        receipt_stat = receipt_path.stat()
        if (
            not receipt_path.is_file()
            or receipt_stat.st_uid != os.getuid()
            or receipt_stat.st_mode & 0o777 != 0o600
        ):
            raise formal_runtime.RuntimeManifestError(
                "publisher reset receipt ownership mismatch"
            )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as error:
        raise formal_runtime.RuntimeManifestError(
            "publisher reset receipt is invalid"
        ) from error
    if not isinstance(payload, dict):
        raise formal_runtime.RuntimeManifestError("publisher reset receipt is invalid")
    return payload


def _validate_publisher_reset_provenance(
    *,
    receipt_path: Path | None,
    expected_correlation_id: str | None,
    stage_dir: Path,
    manifest: dict[str, Any],
    publisher_exact_run_id: str,
    live_aggregate: dict[str, Any],
    live_receipts: dict[str, dict[str, Any]],
    live_identities: dict[str, dict[str, list[Any]]],
    live_plist_sha256: dict[str, str],
) -> None:
    if (
        receipt_path is None
        or expected_correlation_id is None
        or ACTIVATION_CORRELATION_PATTERN.fullmatch(expected_correlation_id) is None
    ):
        raise formal_runtime.RuntimeManifestError("publisher reset provenance missing")
    payload = _load_publisher_reset_receipt(receipt_path, stage_dir=stage_dir)
    if (
        payload.get("schema_version") != PUBLISHER_RESET_RECEIPT_SCHEMA_VERSION
        or payload.get("status") != "PASS"
        or payload.get("transition") != PUBLISHER_RESET_TRANSITION
        or payload.get("correlation_id") != expected_correlation_id
        or payload.get("target")
        != {
            "manifest_digest": manifest["manifest_digest"],
            "runtime_identity_digest": manifest["runtime_identity_digest"],
            "generation": manifest["generation"],
            "publisher_exact_run_id": publisher_exact_run_id,
        }
    ):
        raise formal_runtime.RuntimeManifestError("publisher reset provenance mismatch")
    expected_old_live = {
        **_publisher_reset_old_live_identity(live_aggregate),
        "generation_relation": "target_newer_than_live",
    }
    if (
        payload.get("old_live") != expected_old_live
        or live_aggregate.get("generation") == manifest["generation"]
    ):
        raise formal_runtime.RuntimeManifestError("publisher reset generation mismatch")

    publisher_label = "com.pantheon.agy-content-publisher"
    publisher = payload.get("publisher")
    if not isinstance(publisher, dict) or (
        publisher.get("post_plist_sha256") != live_plist_sha256[publisher_label]
        or publisher.get("post_plist_receipt") != live_receipts[publisher_label]
        or publisher.get("post_launchctl_identity") != live_identities[publisher_label]
    ):
        raise formal_runtime.RuntimeManifestError("publisher reset Publisher proof mismatch")
    expected_labels = [
        label for label in formal_runtime.SERVICE_LABELS if label != publisher_label
    ]
    other_six = payload.get("other_six")
    if not isinstance(other_six, list) or [
        item.get("label") if isinstance(item, dict) else None for item in other_six
    ] != expected_labels:
        raise formal_runtime.RuntimeManifestError("publisher reset unchanged proof mismatch")
    for item in other_six:
        label = str(item["label"])
        if (
            item.get("pre_plist_sha256") != live_plist_sha256[label]
            or item.get("post_plist_sha256") != live_plist_sha256[label]
            or item.get("post_launchctl_identity") != live_identities[label]
            or not isinstance(item.get("pre_launchctl_identity"), dict)
            or item["pre_launchctl_identity"].get("paths")
            != [str(stage_dir.parent / f"{label}.plist")]
            or item["pre_launchctl_identity"].get("states")
            not in (["not running"], ["waiting"])
        ):
            raise formal_runtime.RuntimeManifestError(
                "publisher reset unchanged proof mismatch"
            )


def _service_rss_bytes(
    runner: Runner = _run,
    *,
    expected_inert_labels: frozenset[str] = frozenset(),
    expected_idle_labels: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    # 只重測已證實的程序拓樸變動；量測錯誤不能藉重試變成零。
    for attempt in range(3):
        result = _service_rss_snapshot(
            runner,
            expected_inert_labels=expected_inert_labels,
            expected_idle_labels=expected_idle_labels,
        )
        if result.get("error") != "service_topology_changed_during_rss":
            return result
        if attempt < 2:
            time.sleep(SERVICE_TRANSITION_RECHECK_SECONDS)
    return result


def _service_rss_snapshot(
    runner: Runner,
    *,
    expected_inert_labels: frozenset[str],
    expected_idle_labels: frozenset[str],
) -> dict[str, Any]:
    pids: list[str] = []
    loaded: list[dict[str, Any]] = []
    inert: list[dict[str, Any]] = []
    idle: list[dict[str, Any]] = []
    absent: list[dict[str, Any]] = []
    domain = f"gui/{os.getuid()}"
    for label in SERVICE_LABELS:
        target = f"{domain}/{label}"
        result = runner(["launchctl", "print", target])
        if result.returncode in {3, 113}:
            absent.append({"label": label, "returncode": result.returncode})
            continue
        if result.returncode != 0:
            return {
                "value": None,
                "available": False,
                "error": f"launchctl_print_failed:{label}:{result.returncode}",
                "identity": {"loaded_labels": loaded, "absent_labels": absent},
            }
        match = re.search(r"^\s*pid = ([1-9][0-9]*)\s*$", result.stdout, re.MULTILINE)
        if not match:
            identity = _launchctl_top_level_identity(
                result.stdout,
                expected_target=target,
            )
            if (
                label in expected_inert_labels
                and identity is not None
                and identity["states"] in (["not running"], ["waiting"])
            ):
                inert.append(
                    {
                        "label": label,
                        "topology": "INERT_LOADED",
                        "pid_required": False,
                        "measurement_required": False,
                        "expected_process_count": 0,
                        "resource_usage": "NOT_APPLICABLE",
                    }
                )
                continue
            expected_plist = str(
                Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
                / "Library"
                / "LaunchAgents"
                / f"{label}.plist"
            )
            if (
                label in expected_idle_labels
                and identity is not None
                and identity["states"] == ["not running"]
                and identity["paths"] == [expected_plist]
                # 已結束工作的退出碼不代表目前仍有程序占用記憶體。
                and len(identity["last_exit_codes"]) <= 1
            ):
                idle.append({"label": label, "topology": "loaded-but-idle"})
                continue
            if (
                label in expected_idle_labels
                and identity is not None
                and identity["states"] in (
                    ["running"],
                    ["waiting"],
                    ["spawn scheduled"],
                )
                and identity["paths"] == [expected_plist]
                and identity["last_exit_codes"] in ([], [0])
            ):
                for _attempt in range(SERVICE_TRANSITION_RECHECKS):
                    time.sleep(SERVICE_TRANSITION_RECHECK_SECONDS)
                    retry = runner(["launchctl", "print", target])
                    if retry.returncode != 0:
                        break
                    retry_identity = _launchctl_top_level_identity(
                        retry.stdout,
                        expected_target=target,
                    )
                    if (
                        retry_identity is None
                        or retry_identity["paths"] != [expected_plist]
                        or len(retry_identity["last_exit_codes"]) > 1
                    ):
                        break
                    match = re.search(
                        r"^\s*pid = ([1-9][0-9]*)\s*$",
                        retry.stdout,
                        re.MULTILINE,
                    )
                    if match:
                        break
                    if retry_identity["states"] == ["not running"]:
                        idle.append({"label": label, "topology": "loaded-but-idle"})
                        break
                    if retry_identity["last_exit_codes"] not in ([], [0]):
                        break
                    if retry_identity["states"] not in (
                        ["running"],
                        ["waiting"],
                        ["spawn scheduled"],
                    ):
                        break
                if idle and idle[-1]["label"] == label:
                    continue
            if match:
                pid = match.group(1)
                pids.append(pid)
                loaded.append({"label": label, "pid": int(pid)})
                continue
            return {
                "value": None,
                "available": False,
                "error": f"loaded_service_pid_missing:{label}",
                "identity": {
                    "loaded_labels": loaded,
                    "inert_labels": inert,
                    "idle_labels": idle,
                    "absent_labels": absent,
                },
            }
        pid = match.group(1)
        if label in expected_inert_labels:
            return {
                "value": None,
                "available": False,
                "error": f"inert_service_pid_present:{label}",
                "identity": {
                    "loaded_labels": loaded,
                    "inert_labels": inert,
                    "idle_labels": idle,
                    "absent_labels": absent,
                    "violation": {
                        "service": label,
                        "expected": "no-pid",
                        "actual": int(pid),
                    },
                },
            }
        pids.append(pid)
        loaded.append({"label": label, "pid": int(pid)})
    if not pids:
        return {
            "value": 0,
            "available": True,
            "error": None,
            "identity": {
                "loaded_labels": [],
                "inert_labels": inert,
                "idle_labels": idle,
                "absent_labels": absent,
            },
        }
    identity = {
        "loaded_labels": loaded,
        "inert_labels": inert,
        "idle_labels": idle,
        "absent_labels": absent,
    }

    def unavailable(error: str) -> dict[str, Any]:
        return {"value": None, "available": False, "error": error, "identity": identity}

    result = runner(["ps", "-o", "pid=,rss=", "-p", ",".join(pids)])
    if result.returncode not in (0, 1):
        return unavailable(f"ps_failed:{result.returncode}")
    values: dict[str, int] = {}
    for line in result.stdout.splitlines():
        match = re.fullmatch(r"\s*([1-9][0-9]*)\s+([0-9]+)\s*", line)
        if match is None or match[1] not in pids or match[1] in values:
            return unavailable("ps_parse_failed")
        values[match[1]] = int(match[2])
    if result.returncode == 1 and values:
        return unavailable("ps_failed:1")
    changed = False
    for item in loaded:
        label = item["label"]
        target = f"{domain}/{label}"
        current = runner(["launchctl", "print", target])
        if current.returncode in (3, 113) and label in expected_idle_labels:
            changed = True
            continue
        current_identity = _launchctl_top_level_identity(current.stdout, expected_target=target)
        expected_path = str(Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True) / "Library" / "LaunchAgents" / f"{label}.plist")
        if (
            current.returncode != 0
            or current_identity is None
            or current_identity["paths"] != [expected_path]
            or len(current_identity["states"]) != 1
            or len(current_identity["last_exit_codes"]) > 1
        ):
            return unavailable("service_identity_unknown_after_rss")
        current_pids = re.findall(r"^\s*pid = ([1-9][0-9]*)\s*$", current.stdout, re.MULTILINE)
        if current_pids == [str(item["pid"])]:
            if current_identity["states"] != ["running"]:
                return unavailable("service_identity_unknown_after_rss")
            continue
        if label not in expected_idle_labels or not (
            (not current_pids and current_identity["states"] == ["not running"])
            or (len(current_pids) == 1 and current_identity["states"] == ["running"])
        ):
            return unavailable("service_identity_unknown_after_rss")
        changed = True
    if changed:
        return unavailable("service_topology_changed_during_rss")
    if result.returncode != 0:
        return unavailable(f"ps_failed:{result.returncode}")
    if set(values) != set(pids):
        return unavailable("ps_parse_failed")
    return {
        "value": sum(values.values()) * 1024,
        "available": True,
        "error": None,
        "identity": {
            "loaded_labels": loaded,
            "inert_labels": inert,
            "idle_labels": idle,
            "absent_labels": absent,
        },
    }


class _DarwinSwapUsage(ctypes.Structure):
    _fields_ = (
        ("total", ctypes.c_uint64),
        ("available", ctypes.c_uint64),
        ("used", ctypes.c_uint64),
        ("page_size", ctypes.c_uint32),
        ("encrypted", ctypes.c_int),
    )


def _local_swap_used_bytes() -> tuple[int | None, str | None]:
    if sys.platform == "darwin":
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            sysctlbyname = libc.sysctlbyname
            sysctlbyname.argtypes = (
                ctypes.c_char_p,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_size_t),
                ctypes.c_void_p,
                ctypes.c_size_t,
            )
            sysctlbyname.restype = ctypes.c_int
            usage = _DarwinSwapUsage()
            expected_size = ctypes.sizeof(usage)
            actual_size = ctypes.c_size_t(expected_size)
            returncode = sysctlbyname(
                b"vm.swapusage",
                ctypes.byref(usage),
                ctypes.byref(actual_size),
                None,
                0,
            )
        except (AttributeError, OSError) as error:
            return None, f"sysctlbyname_unavailable:{type(error).__name__}"
        if returncode != 0:
            return None, f"sysctlbyname_failed:{ctypes.get_errno() or returncode}"
        if actual_size.value != expected_size:
            return None, "sysctlbyname_size_mismatch"
        if usage.used > usage.total:
            return None, "sysctlbyname_invalid_usage"
        return int(usage.used), None

    try:
        values = {
            line.split(":", 1)[0]: int(line.split()[1]) * 1024
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
            if line.startswith(("SwapTotal:", "SwapFree:"))
        }
    except (FileNotFoundError, OSError, ValueError, IndexError):
        values = {}
    if set(values) == {"SwapTotal", "SwapFree"}:
        used = values["SwapTotal"] - values["SwapFree"]
        if used >= 0:
            return used, None
    return None, "local_swap_telemetry_unavailable"


def _swap_used_bytes(
    runner: Runner = _run,
    *,
    fallback: SwapFallback = _local_swap_used_bytes,
) -> dict[str, Any]:
    result = runner(["sysctl", "-n", "vm.swapusage"])
    if result.returncode == 0:
        match = re.search(r"used = ([0-9.]+)([MG])", result.stdout)
        if match:
            factor = GIB if match.group(2) == "G" else MIB
            return {
                "value": int(float(match.group(1)) * factor),
                "available": True,
                "error": None,
            }
        return {"value": None, "available": False, "error": "swap_parse_failed"}
    value, fallback_error = fallback()
    if value is not None and fallback_error is None:
        return {
            "value": value,
            "available": True,
            "error": None,
        }
    return {
        "value": None,
        "available": False,
        "error": (
            f"swap_sources_failed:command:{result.returncode};"
            f"fallback:{fallback_error or 'invalid_result'}"
        ),
    }


def _read_state(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}, None
    except OSError as error:
        return {}, f"capacity_state_unreadable:{type(error).__name__}"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {}, f"capacity_state_malformed:{type(error).__name__}"
    if not isinstance(payload, dict):
        return {}, "capacity_state_not_object"
    return payload, None


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _preserve_invalid_state(path: Path) -> str | None:
    """覆寫 malformed state 前保存 exact bytes；保存失敗時維持原檔。"""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    digest = hashlib.sha256(raw).hexdigest()
    evidence = path.with_name(f".{path.name}.invalid-{digest[:20]}.raw")
    if evidence.exists():
        return str(evidence)
    descriptor = os.open(
        evidence,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("capacity guard invalid state evidence write failed")
            offset += written
        os.fsync(descriptor)
    except Exception:
        evidence.unlink(missing_ok=True)
        raise
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)
    return str(evidence)


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise OSError("capacity guard state write failed")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
        _fsync_directory(path.parent)
        try:
            readback = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise OSError("capacity guard state readback failed") from error
        if readback != payload or not _state_file_is_private(path):
            raise OSError("capacity guard state durable readback mismatch")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _state_file_is_private(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and not path.is_symlink()
        and metadata.st_uid == os.getuid()
        and metadata.st_nlink == 1
        and stat.S_IMODE(metadata.st_mode) == 0o600
    )


def _recovery_context(runtime_receipt: dict[str, Any]) -> dict[str, Any]:
    """只從目前正式 normal runtime 推導可自動恢復的 immutable identity。"""
    unavailable = {
        "authorized": False,
        "blocker": "formal_normal_recovery_context_unavailable",
    }
    if _normal_scheduled_service_labels(runtime_receipt) != frozenset(SERVICE_LABELS):
        return unavailable
    try:
        manifest_path = Path(os.environ["PANTHEON_RUNTIME_MANIFEST"])
        expected_digest = os.environ["PANTHEON_RUNTIME_MANIFEST_DIGEST"]
        manifest = formal_runtime.load_manifest(manifest_path, expected_digest)
        manifest_file = _file_identity(manifest_path)
        expected_guard = formal_runtime.receipt_for_label(manifest, CAPACITY_GUARD_LABEL)
        if any(runtime_receipt.get(field) != value for field, value in expected_guard.items()):
            return unavailable
        home = Path(
            os.environ.get("PANTHEON_USER_HOME_DIR")
            or pwd.getpwuid(os.getuid()).pw_dir
        ).resolve(strict=True)
        launch_agents = home / "Library" / "LaunchAgents"
        plist_paths = [
            launch_agents / f"{label}.plist" for label in formal_runtime.SERVICE_LABELS
        ]
        formal_runtime.aggregate_plist_preflight(
            manifest,
            plist_paths,
            expected_activation_mode="normal",
        )
        barrier = (
            Path(manifest["publisher_state_root"])
            / f"four-lane-activation-{manifest['generation']}.barrier"
        )
        formal_runtime.validate_barrier(barrier, manifest)
        barrier_identity = _file_identity(barrier)
        for label, path in zip(formal_runtime.SERVICE_LABELS, plist_paths):
            with path.open("rb") as stream:
                payload = plistlib.load(stream)
            arguments = payload.get("ProgramArguments")
            if not isinstance(arguments, list):
                return unavailable
            if (
                formal_runtime._single_argument_value(arguments, "--service-label")
                != label
                or Path(
                    formal_runtime._single_argument_value(arguments, "--manifest")
                )
                != manifest_path
                or formal_runtime._single_argument_value(
                    arguments, "--expected-digest"
                )
                != manifest["manifest_digest"]
                or Path(formal_runtime._single_argument_value(arguments, "--barrier"))
                != barrier
            ):
                return unavailable
        business_plists = {
            label: _file_identity(launch_agents / f"{label}.plist")
            for label in SERVICE_LABELS
        }
        if (
            not _same_file_identity(manifest_file)
            or not _same_file_identity(barrier_identity)
            or not all(_same_file_identity(item) for item in business_plists.values())
        ):
            return unavailable
    except (
        KeyError,
        OSError,
        plistlib.InvalidFileException,
        formal_runtime.RuntimeManifestError,
    ):
        return unavailable
    return {
        "authorized": True,
        "blocker": None,
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "barrier_path": str(barrier),
        "manifest_file": manifest_file,
        "barrier": barrier_identity,
        "owned_roots": {
            field: manifest[field]
            for field in ("actor_root", "queue_root", "publisher_state_root", "log_root")
        },
        "restart_projected_bytes": RECOVERY_PROJECTED_RESTART_BYTES,
        "plists": business_plists,
    }


def _disabled_service_labels(
    runner: Runner,
) -> tuple[frozenset[str] | None, str | None]:
    try:
        return (
            runtime_activation.read_disabled_service_labels(
                SERVICE_LABELS,
                runner=runner,
            ),
            None,
        )
    except runtime_activation.RuntimeActivationError as error:
        return None, f"launchctl_print_disabled_failed:{error}"


def _capture_recovery_incident(
    *,
    timestamp: float,
    reasons: list[str],
    recovery_context: dict[str, Any],
    runner: Runner,
) -> dict[str, Any]:
    context_authorized = recovery_context.get("authorized") is True
    automatic = context_authorized
    blocker = recovery_context.get("blocker") if not automatic else None
    disabled: frozenset[str] = frozenset()
    observations: dict[str, dict[str, Any]] = {}
    pre_stop_loaded_labels: list[str] = []
    stop_targets: list[str] = []
    plists = recovery_context.get("plists")
    disabled_known = False
    if context_authorized:
        disabled_result, disabled_error = _disabled_service_labels(runner)
        if disabled_result is None:
            automatic = False
            blocker = disabled_error
        else:
            disabled = disabled_result
            disabled_known = True
    if context_authorized and isinstance(plists, dict):
        domain = f"gui/{os.getuid()}"
        for label in SERVICE_LABELS:
            plist = plists.get(label)
            expected_path = (
                Path(str(plist.get("path"))) if isinstance(plist, dict) else None
            )
            target = f"{domain}/{label}"
            try:
                observed = runner(["launchctl", "print", target])
            except OSError:
                observations[label] = {
                    "topology": "UNKNOWN",
                    "returncode": None,
                }
                automatic = False
                blocker = f"pre_stop_service_identity_unknown:{label}"
                continue
            if observed.returncode in {3, 113}:
                observations[label] = {
                    "topology": "ABSENT",
                    "returncode": observed.returncode,
                    "manual_disabled": label in disabled,
                }
                continue
            identity = (
                _launchctl_top_level_identity(
                    observed.stdout,
                    expected_target=target,
                )
                if observed.returncode == 0
                else None
            )
            if (
                expected_path is None
                or identity is None
                or identity["paths"] != [str(expected_path)]
                or len(identity["states"]) != 1
                or identity["states"][0]
                not in {"running", "not running", "waiting", "spawn scheduled"}
                or identity["last_exit_codes"] not in ([], [0])
            ):
                observations[label] = {
                    "topology": "UNKNOWN",
                    "returncode": observed.returncode,
                }
                automatic = False
                blocker = f"pre_stop_service_identity_unknown:{label}"
                continue
            observations[label] = {
                "topology": "LOADED",
                "returncode": 0,
                "identity": identity,
                "manual_disabled": label in disabled if disabled_known else None,
            }
            pre_stop_loaded_labels.append(label)
            if disabled_known and label not in disabled:
                stop_targets.append(label)
    elif context_authorized:
        automatic = False
        blocker = "recovery_plist_identity_missing"
    owned_labels = list(stop_targets) if automatic else []
    identity_seed = {
        "sampled_epoch": timestamp,
        "reasons": reasons,
        "manifest_digest": recovery_context.get("manifest_digest"),
        "generation": recovery_context.get("generation"),
        "stop_targets": stop_targets,
    }
    incident_id = "capacity-" + hashlib.sha256(
        json.dumps(identity_seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]
    return {
        "schema_version": 2,
        "incident_id": incident_id,
        "status": "STOPPING",
        "started_epoch": timestamp,
        "updated_epoch": timestamp,
        "trigger_reasons": list(reasons),
        "automatic_recovery_authorized": automatic,
        "authorization_blocker": blocker,
        "manifest_digest": recovery_context.get("manifest_digest"),
        "runtime_identity_digest": recovery_context.get("runtime_identity_digest"),
        "generation": recovery_context.get("generation"),
        "barrier_path": recovery_context.get("barrier_path"),
        "manifest_file": recovery_context.get("manifest_file"),
        "barrier": recovery_context.get("barrier"),
        "owned_roots": recovery_context.get("owned_roots"),
        "restart_projected_bytes": recovery_context.get(
            "restart_projected_bytes", RECOVERY_PROJECTED_RESTART_BYTES
        ),
        "plists": plists if isinstance(plists, dict) else {},
        "pre_stop_services": observations,
        "pre_stop_loaded_labels": pre_stop_loaded_labels,
        "disabled_labels_before_stop": sorted(disabled),
        "stop_targets": stop_targets,
        "owned_labels": owned_labels,
        "stopped_by_guard": [],
        "stopped_services": [],
        "stop_verification": {},
        "healthy_samples": 0,
        "last_healthy_epoch": None,
        "attempts_started": 0,
        "max_attempts": MAX_AUTOMATIC_RECOVERY_ATTEMPTS,
        "attempted_labels": [],
        "started_labels": [],
        "rollback": None,
        "stop_action_receipt": None,
        "resume_action_receipt": None,
        "rollback_action_receipt": None,
        "execution_verification": None,
        "restart_baseline": None,
        "restart_samples": [],
        "post_resume_healthy_samples": 0,
        "last_post_resume_epoch": None,
        "verification_started_epoch": None,
        "active_run_first_seen_epoch": {},
        "active_run_last_seen_epoch": {},
        "lineage_pending_first_seen_epoch": None,
        "restart_measurement": None,
    }


def _load_open_recovery_incident(
    previous: dict[str, Any],
    state_file: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    candidate = previous.get("recovery_incident")
    previous_status = previous.get("status")
    if not previous and not state_file.exists():
        return None, None
    if previous_status not in {*OPEN_RECOVERY_STATUSES, "PASS"}:
        return None, "capacity_state_status_unknown"
    if not isinstance(candidate, dict):
        if previous_status in OPEN_RECOVERY_STATUSES:
            return None, "legacy_stop_without_owned_incident"
        if previous_status == "PASS":
            return None, None
        return None, "capacity_recovery_incident_missing"
    candidate = dict(candidate)
    candidate.setdefault("stop_action_receipt", None)
    candidate.setdefault("resume_action_receipt", None)
    candidate.setdefault("rollback_action_receipt", None)
    candidate.setdefault("execution_verification", None)
    candidate.setdefault("restart_baseline", None)
    candidate.setdefault("restart_samples", [])
    candidate.setdefault("post_resume_healthy_samples", 0)
    candidate.setdefault("last_post_resume_epoch", None)
    candidate.setdefault("verification_started_epoch", None)
    candidate.setdefault("active_run_first_seen_epoch", {})
    candidate.setdefault("active_run_last_seen_epoch", {})
    candidate.setdefault("lineage_pending_first_seen_epoch", None)
    incident_status = candidate.get("status")
    if incident_status == "RECOVERED":
        if previous_status != "PASS":
            return None, "capacity_state_status_mismatch"
    elif incident_status not in OPEN_RECOVERY_STATUSES:
        return None, "capacity_recovery_incident_unknown_status"
    elif previous_status != incident_status:
        return None, "capacity_state_status_mismatch"
    if not _state_file_is_private(state_file):
        return None, "capacity_state_identity_untrusted"
    owned = candidate.get("owned_labels")
    stop_targets = candidate.get("stop_targets")
    stopped_by_guard = candidate.get("stopped_by_guard")
    attempts = candidate.get("attempts_started")
    healthy_samples = candidate.get("healthy_samples")
    attempted_labels = candidate.get("attempted_labels")
    started_labels = candidate.get("started_labels")
    restart_samples = candidate.get("restart_samples")
    post_resume_healthy_samples = candidate.get("post_resume_healthy_samples")
    active_run_first_seen = candidate.get("active_run_first_seen_epoch")
    active_run_last_seen = candidate.get("active_run_last_seen_epoch")
    lineage_pending_first_seen = candidate.get("lineage_pending_first_seen_epoch")
    if (
        candidate.get("schema_version") != 2
        or not isinstance(candidate.get("incident_id"), str)
        or not isinstance(stop_targets, list)
        or len(stop_targets) != len(set(stop_targets))
        or any(label not in SERVICE_LABELS for label in stop_targets)
        or not isinstance(owned, list)
        or len(owned) != len(set(owned))
        or any(label not in SERVICE_LABELS for label in owned)
        or not set(owned).issubset(stop_targets)
        or not isinstance(stopped_by_guard, list)
        or len(stopped_by_guard) != len(set(stopped_by_guard))
        or any(label not in SERVICE_LABELS for label in stopped_by_guard)
        or not set(stopped_by_guard).issubset(stop_targets)
        or type(attempts) is not int
        or attempts < 0
        or attempts > MAX_AUTOMATIC_RECOVERY_ATTEMPTS
        or type(healthy_samples) is not int
        or healthy_samples < 0
        or not isinstance(attempted_labels, list)
        or any(label not in SERVICE_LABELS for label in attempted_labels)
        or not set(attempted_labels).issubset(owned)
        or not isinstance(started_labels, list)
        or any(label not in SERVICE_LABELS for label in started_labels)
        or not set(started_labels).issubset(attempted_labels)
        or not isinstance(restart_samples, list)
        or type(post_resume_healthy_samples) is not int
        or post_resume_healthy_samples < 0
        or not isinstance(active_run_first_seen, dict)
        or any(
            label not in SERVICE_LABELS
            or type(epoch) not in (int, float)
            or epoch < 0
            or epoch > 1_000_000_000_000
            or not math.isfinite(epoch)
            for label, epoch in active_run_first_seen.items()
        )
        or not isinstance(active_run_last_seen, dict)
        or any(
            label not in SERVICE_LABELS
            or type(epoch) not in (int, float)
            or epoch < 0
            or epoch > 1_000_000_000_000
            or not math.isfinite(epoch)
            for label, epoch in active_run_last_seen.items()
        )
        or not set(active_run_last_seen).issubset(active_run_first_seen)
        or any(
            active_run_last_seen[label] < active_run_first_seen[label]
            for label in active_run_last_seen
        )
        or (
            lineage_pending_first_seen is not None
            and (
                type(lineage_pending_first_seen) not in (int, float)
                or lineage_pending_first_seen < 0
                or lineage_pending_first_seen > 1_000_000_000_000
                or not math.isfinite(lineage_pending_first_seen)
            )
        )
        or candidate.get("max_attempts") != MAX_AUTOMATIC_RECOVERY_ATTEMPTS
    ):
        return None, "capacity_recovery_incident_invalid"
    if candidate.get("automatic_recovery_authorized") is True:
        plists = candidate.get("plists")
        barrier_path = candidate.get("barrier_path")
        barrier = candidate.get("barrier")
        manifest_file = candidate.get("manifest_file")
        owned_roots = candidate.get("owned_roots")
        if (
            formal_runtime.SHA256_PATTERN.fullmatch(
                str(candidate.get("manifest_digest", ""))
            )
            is None
            or formal_runtime.SHA256_PATTERN.fullmatch(
                str(candidate.get("runtime_identity_digest", ""))
            )
            is None
            or formal_runtime.GENERATION_PATTERN.fullmatch(
                str(candidate.get("generation", ""))
            )
            is None
            or not isinstance(barrier_path, str)
            or not Path(barrier_path).is_absolute()
            or not _valid_file_identity_record(barrier)
            or barrier.get("path") != barrier_path
            or not _valid_file_identity_record(manifest_file)
            or not isinstance(owned_roots, dict)
            or set(owned_roots)
            != {"actor_root", "queue_root", "publisher_state_root", "log_root"}
            or any(
                not isinstance(path, str) or not Path(path).is_absolute()
                for path in owned_roots.values()
            )
            or candidate.get("restart_projected_bytes")
            != RECOVERY_PROJECTED_RESTART_BYTES
            or not isinstance(plists, dict)
            or set(plists) != set(SERVICE_LABELS)
        ):
            return None, "capacity_recovery_incident_invalid"
        for label in SERVICE_LABELS:
            if not _valid_file_identity_record(plists.get(label)):
                return None, "capacity_recovery_incident_invalid"
    for field in (
        "stop_action_receipt",
        "resume_action_receipt",
        "rollback_action_receipt",
    ):
        value = candidate.get(field)
        if value is not None and not _valid_file_identity_record(value):
            return None, "capacity_recovery_incident_invalid"
    if incident_status == "RECOVERY_VERIFYING" and (
        not _valid_file_identity_record(candidate.get("resume_action_receipt"))
        or not isinstance(candidate.get("restart_baseline"), dict)
        or not candidate.get("started_labels")
        or type(candidate.get("verification_started_epoch")) not in (int, float)
        or candidate["verification_started_epoch"] < 0
        or candidate["verification_started_epoch"] > 1_000_000_000_000
        or not math.isfinite(candidate["verification_started_epoch"])
        or type(candidate.get("updated_epoch")) not in (int, float)
        or candidate["updated_epoch"] > 1_000_000_000_000
        or not math.isfinite(candidate["updated_epoch"])
        or candidate["updated_epoch"] < candidate["verification_started_epoch"]
        or any(
            epoch < candidate["verification_started_epoch"]
            or epoch > candidate["updated_epoch"]
            for epoch in active_run_first_seen.values()
        )
        or any(
            epoch < candidate["verification_started_epoch"]
            or epoch > candidate["updated_epoch"]
            for epoch in active_run_last_seen.values()
        )
        or (
            lineage_pending_first_seen is not None
            and (
                lineage_pending_first_seen < candidate["verification_started_epoch"]
                or lineage_pending_first_seen > candidate["updated_epoch"]
            )
        )
    ):
        return None, "capacity_recovery_incident_invalid"
    if incident_status == "RECOVERED":
        return None, None
    return dict(candidate), None


def _recovery_context_mismatch(
    incident: dict[str, Any],
    current: dict[str, Any],
) -> str | None:
    if incident.get("automatic_recovery_authorized") is not True:
        return str(incident.get("authorization_blocker") or "automatic_recovery_not_authorized")
    if current.get("authorized") is not True:
        return str(current.get("blocker") or "current_recovery_context_unavailable")
    for field in (
        "manifest_digest",
        "runtime_identity_digest",
        "generation",
        "barrier_path",
        "manifest_file",
        "barrier",
        "owned_roots",
        "restart_projected_bytes",
        "plists",
    ):
        if incident.get(field) != current.get(field):
            return f"recovery_context_drift:{field}"
    return None


def _verify_owned_services_absent(
    labels: list[str],
    runner: Runner,
) -> tuple[bool, dict[str, Any]]:
    """沿用 canonical lifecycle observer；Guard 不再自行解析 absence。"""
    return runtime_activation.verify_services_absent(
        labels,
        runner=runner,
    )


def _incident_plist_paths(
    incident: dict[str, Any],
    labels: list[str],
) -> dict[str, Path]:
    plists = incident.get("plists")
    if not isinstance(plists, dict):
        raise formal_runtime.RuntimeManifestError("recovery plist identity is missing")
    result: dict[str, Path] = {}
    for label in labels:
        record = plists.get(label)
        if not _valid_file_identity_record(record):
            raise formal_runtime.RuntimeManifestError("recovery plist identity is invalid")
        result[label] = Path(str(record["path"]))
    return result


def _recovery_action_receipt_path(
    state_file: Path,
    incident: dict[str, Any],
    action: str,
) -> Path:
    incident_id = str(incident.get("incident_id", ""))
    if (
        ACTIVATION_CORRELATION_PATTERN.fullmatch(incident_id) is None
        or action not in {"stop", "resume", "rollback"}
    ):
        raise formal_runtime.RuntimeManifestError("recovery action identity is invalid")
    return state_file.with_name(
        f".{state_file.name}.{incident_id}.{action}.json"
    )


def _runtime_action_kwargs(
    incident: dict[str, Any],
    labels: list[str],
) -> dict[str, Any]:
    owned_roots = incident.get("owned_roots")
    if not isinstance(owned_roots, dict):
        raise formal_runtime.RuntimeManifestError("recovery owned roots are missing")
    manifest_file = incident.get("manifest_file")
    barrier = incident.get("barrier")
    plists = incident.get("plists")
    if (
        not _valid_file_identity_record(manifest_file)
        or not _valid_file_identity_record(barrier)
        or not isinstance(plists, dict)
    ):
        raise formal_runtime.RuntimeManifestError("recovery action authority is missing")
    selected_plists: dict[str, dict[str, Any]] = {}
    for label in labels:
        record = plists.get(label)
        if not _valid_file_identity_record(record):
            raise formal_runtime.RuntimeManifestError(
                f"recovery action plist authority is missing: {label}"
            )
        selected_plists[label] = dict(record)
    return {
        "incident_id": str(incident["incident_id"]),
        "generation": str(incident["generation"]),
        "manifest_digest": str(incident["manifest_digest"]),
        "runtime_identity_digest": str(incident["runtime_identity_digest"]),
        "owned_roots": owned_roots,
        "authority": {
            "schema_version": 1,
            "generation": str(incident["generation"]),
            "manifest_digest": str(incident["manifest_digest"]),
            "runtime_identity_digest": str(incident["runtime_identity_digest"]),
            "manifest_file": dict(manifest_file),
            "barrier": dict(barrier),
            "plists": selected_plists,
        },
    }


def _snapshot(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    *,
    runner: Runner = _run,
    capacity_sensor: CapacitySensor | None = None,
    expected_inert_labels: frozenset[str] = frozenset(),
    expected_idle_labels: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    roots = (queue_root, publisher_root, log_root)
    measured = [_measure_tree(root) for root in roots]
    raw_total_disk, raw_free_disk = _disk_sample(queue_root)
    sensor = _host_capacity_sample if capacity_sensor is None else capacity_sensor
    try:
        capacity = sensor(queue_root)
    except RuntimeError as error:
        capacity = {
            "disk_total_bytes": raw_total_disk,
            "disk_free_bytes": raw_free_disk,
            "admission_available_bytes": None,
            "capacity_source": None,
            "capacity_available": False,
            "capacity_error": str(error),
        }
    if runner is _run:
        if expected_inert_labels or expected_idle_labels:
            rss = _service_rss_bytes(
                expected_inert_labels=expected_inert_labels,
                expected_idle_labels=expected_idle_labels,
            )
        else:
            rss = _service_rss_bytes()
        swap = _swap_used_bytes()
    else:
        if expected_inert_labels or expected_idle_labels:
            rss = _service_rss_bytes(
                runner,
                expected_inert_labels=expected_inert_labels,
                expected_idle_labels=expected_idle_labels,
            )
        else:
            rss = _service_rss_bytes(runner)
        swap = _swap_used_bytes(runner)
    return {
        "bytes": sum(item[0] for item in measured),
        "file_count": sum(item[1] for item in measured),
        "raw_disk_total_bytes": raw_total_disk,
        "raw_disk_free_bytes": raw_free_disk,
        **capacity,
        "rss_bytes": rss["value"],
        "rss_available": rss["available"],
        "rss_error": rss["error"],
        "rss_identity": rss["identity"],
        "swap_used_bytes": swap["value"],
        "swap_available": swap["available"],
        "swap_error": swap["error"],
    }


@formal_runtime.with_runtime_work_lease
def preflight(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    *,
    runner: Runner = _run,
    capacity_sensor: CapacitySensor | None = None,
) -> dict[str, Any]:
    projected_bytes = DEFAULT_PROJECTED_BYTES
    runtime_receipt = formal_runtime.validate_runtime_tick(
        "com.pantheon.content-capacity-guard",
        queue_root=queue_root.resolve(),
        state_root=publisher_root.resolve(),
        actor_root=Path(
            os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())
        ),
        log_root=log_root.resolve(),
        require_activation_token=False,
    )
    expected_inert_labels = _activation_only_service_labels(runtime_receipt)
    expected_idle_labels = _normal_scheduled_service_labels(runtime_receipt)
    snapshot_options: dict[str, Any] = {}
    if runner is not _run:
        snapshot_options["runner"] = runner
    if capacity_sensor is not None:
        snapshot_options["capacity_sensor"] = capacity_sensor
    if expected_inert_labels:
        snapshot_options["expected_inert_labels"] = expected_inert_labels
    if expected_idle_labels:
        snapshot_options["expected_idle_labels"] = expected_idle_labels
    sample = _snapshot(queue_root, publisher_root, log_root, **snapshot_options)
    reasons: list[str] = []
    reserve_bytes = max(
        HOST_RESERVE_MIN_BYTES,
        (sample["disk_total_bytes"] + 9) // 10,
    )
    admission_available = sample.get("admission_available_bytes")
    projected_admission_available = (
        int(admission_available) - projected_bytes
        if isinstance(admission_available, int) and not isinstance(admission_available, bool)
        else None
    )
    if sample.get("capacity_available") is not True or projected_admission_available is None:
        reasons.append("capacity_telemetry_unknown")
    elif projected_admission_available < reserve_bytes:
        reasons.append("projected_admission_below_reserve")
    if sample["bytes"] > MAX_BYTES:
        reasons.append("project_bytes_over_budget")
    if sample["file_count"] > MAX_FILE_COUNT:
        reasons.append("project_files_over_budget")
    telemetry_gaps = []
    if sample.get("rss_available") is not True:
        telemetry_gaps.append("rss_telemetry_unknown")
        rss_error = str(sample.get("rss_error") or "")
        topology_error = rss_error.startswith(
            (
                "loaded_service_pid_missing:",
                "inert_service_pid_present:",
            )
        )
        if topology_error:
            reasons.append("service_topology_invalid")
    if sample.get("swap_available") is not True:
        telemetry_gaps.append("swap_telemetry_unknown")
    process_policy = {
        "topology": "INERT_LOADED",
        "pid_required": False,
        "measurement_required": False,
        "expected_process_count": 0,
        "resource_usage": "NOT_APPLICABLE",
    } if expected_inert_labels else {
        "topology": "RSS_REQUIRED",
        "pid_required": True,
        "measurement_required": True,
    }
    return {
        "status": "PASS" if not reasons else "NO-GO",
        "reasons": reasons,
        "telemetry_gaps": telemetry_gaps,
        "projected_bytes": projected_bytes,
        "reserve_bytes": reserve_bytes,
        "projected_admission_available_bytes": projected_admission_available,
        "capacity_path": str(queue_root.resolve()),
        "process_policy": process_policy,
        **sample,
    }


def _validate_capacity_admission_receipt(receipt: object) -> None:
    """驗證 activation 使用的 receipt 確實包含本次容量 admission 證據。"""
    if not isinstance(receipt, dict):
        raise formal_runtime.RuntimeManifestError("preactivation receipt mismatch")
    integer_fields = (
        "disk_total_bytes",
        "disk_free_bytes",
        "raw_disk_total_bytes",
        "raw_disk_free_bytes",
        "admission_available_bytes",
        "projected_bytes",
        "reserve_bytes",
        "projected_admission_available_bytes",
    )
    values = {name: receipt.get(name) for name in integer_fields}
    if (
        receipt.get("status") != "PASS"
        or receipt.get("reasons") != []
        or receipt.get("capacity_available") is not True
        or receipt.get("capacity_error") is not None
        or receipt.get("capacity_source")
        != (
            "macos_foundation_important_usage"
            if sys.platform == "darwin"
            else "shutil.disk_usage"
        )
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in values.values()
        )
    ):
        raise formal_runtime.RuntimeManifestError("preactivation receipt mismatch")
    capacity_path = receipt.get("capacity_path")
    if not isinstance(capacity_path, str) or not capacity_path:
        raise formal_runtime.RuntimeManifestError("preactivation receipt mismatch")
    total = values["disk_total_bytes"]
    physical_available = values["disk_free_bytes"]
    raw_total = values["raw_disk_total_bytes"]
    raw_available = values["raw_disk_free_bytes"]
    admission = values["admission_available_bytes"]
    projected = values["projected_bytes"]
    reserve = values["reserve_bytes"]
    projected_available = values["projected_admission_available_bytes"]
    expected_reserve = max(HOST_RESERVE_MIN_BYTES, (total + 9) // 10)
    if (
        total <= 0
        or raw_total != total
        or raw_available > raw_total
        or physical_available > total
        or admission < physical_available
        or admission > total
        or projected != DEFAULT_PROJECTED_BYTES
        or reserve != expected_reserve
        or projected_available != admission - projected
        or projected_available < reserve
    ):
        raise formal_runtime.RuntimeManifestError("preactivation receipt mismatch")


def validate_preactivation_transition(
    *,
    preflight_receipt: Path,
    manifest_path: Path,
    expected_digest: str,
    barrier: Path,
    launch_agents_dir: Path,
    capacity_plist: Path,
    publisher_reset_receipt: Path | None = None,
    expected_reset_correlation_id: str | None = None,
    recovery_from_normal_stopped: bool = False,
    recovery_from_all_stopped: bool = False,
    recovery_from_activation_only_all_stopped: bool = False,
    recovery_from_publisher_canary_all_stopped: bool = False,
    runner: Runner = _run,
    capacity_sensor: CapacitySensor | None = None,
) -> dict[str, Any]:
    recovery_mode_count = sum(
        int(value)
        for value in (
            recovery_from_normal_stopped,
            recovery_from_all_stopped,
            recovery_from_activation_only_all_stopped,
            recovery_from_publisher_canary_all_stopped,
        )
    )
    if recovery_mode_count > 1:
        raise formal_runtime.RuntimeManifestError("preactivation recovery mode is ambiguous")
    recovery_from_stopped = recovery_mode_count == 1
    all_stopped_recovery = (
        recovery_from_all_stopped
        or recovery_from_activation_only_all_stopped
        or recovery_from_publisher_canary_all_stopped
    )
    publisher_label = "com.pantheon.agy-content-publisher"
    try:
        receipt = json.loads(preflight_receipt.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as error:
        raise formal_runtime.RuntimeManifestError("preactivation receipt is invalid") from error
    _validate_capacity_admission_receipt(receipt)
    manifest = formal_runtime.load_manifest(manifest_path, expected_digest)
    try:
        capacity_path = Path(receipt["capacity_path"]).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise formal_runtime.RuntimeManifestError(
            "preactivation capacity path mismatch"
        ) from error
    if capacity_path != Path(manifest["queue_root"]):
        raise formal_runtime.RuntimeManifestError("preactivation capacity path mismatch")
    sensor = _host_capacity_sample if capacity_sensor is None else capacity_sensor
    try:
        current_capacity = sensor(capacity_path)
    except Exception as error:
        raise formal_runtime.RuntimeManifestError(
            "preactivation capacity remeasurement failed"
        ) from error
    if (
        current_capacity.get("capacity_available") is not True
        or current_capacity.get("capacity_source") != receipt["capacity_source"]
        or current_capacity.get("disk_total_bytes") != receipt["disk_total_bytes"]
        or not isinstance(current_capacity.get("admission_available_bytes"), int)
        or current_capacity["admission_available_bytes"] - receipt["projected_bytes"]
        < receipt["reserve_bytes"]
    ):
        raise formal_runtime.RuntimeManifestError(
            "preactivation capacity remeasurement mismatch"
        )
    formal_runtime.validate_barrier(barrier, manifest)
    launch_agents = launch_agents_dir.resolve(strict=True)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    try:
        stage_manifest_digest = (stage_dir / "manifest-digest").read_text(
            encoding="utf-8"
        ).strip()
        stage_generation = (stage_dir / "generation").read_text(
            encoding="utf-8"
        ).strip()
        publisher_max_runs = (stage_dir / "publisher-max-runs").read_text(
            encoding="utf-8"
        ).strip()
    except OSError as error:
        raise formal_runtime.RuntimeManifestError("preactivation stage mismatch") from error
    try:
        publisher_exact_run_id = (stage_dir / "publisher-exact-run-id").read_text(
            encoding="utf-8"
        ).strip()
    except FileNotFoundError:
        publisher_exact_run_id = None
    except OSError as error:
        raise formal_runtime.RuntimeManifestError("preactivation stage mismatch") from error
    if (
        stage_manifest_digest != manifest["manifest_digest"]
        or stage_generation != manifest["generation"]
        or publisher_max_runs != "1"
    ):
        raise formal_runtime.RuntimeManifestError("preactivation stage mismatch")
    publisher_plist = stage_dir / "com.pantheon.agy-content-publisher.plist"
    if publisher_exact_run_id is None:
        formal_runtime.publisher_plist_preflight(
            manifest,
            publisher_plist,
            require_no_exact_run_id=True,
        )
    else:
        if not publisher_exact_run_id:
            raise formal_runtime.RuntimeManifestError("preactivation stage mismatch")
        formal_runtime.publisher_plist_preflight(
            manifest,
            publisher_plist,
            expected_exact_run_id=publisher_exact_run_id,
        )
    staged_plists = {
        **{label: stage_dir / f"{label}.plist" for label in SERVICE_LABELS},
        CAPACITY_GUARD_LABEL: capacity_plist,
    }
    for label, stage_plist in staged_plists.items():
        with stage_plist.open("rb") as stream:
            stage_payload = plistlib.load(stream)
        stage_arguments = stage_payload.get("ProgramArguments")
        if not isinstance(stage_arguments, list):
            raise formal_runtime.RuntimeManifestError("preactivation stage mismatch")
        stage_separator = (
            stage_arguments.index("--") if "--" in stage_arguments else len(stage_arguments)
        )
        if "--activation-only" in stage_arguments[:stage_separator] and any(
            field in stage_payload
            for field in ("StandardInPath", "StandardOutPath", "StandardErrorPath")
        ):
            raise formal_runtime.RuntimeManifestError("preactivation stage child io mismatch")
    for label in (*SERVICE_LABELS[1:], CAPACITY_GUARD_LABEL):
        stage_receipt = formal_runtime.plist_receipt(
            staged_plists[label],
            expected_activation_mode="normal",
        )
        expected_stage = formal_runtime.receipt_for_label(manifest, label)
        if any(stage_receipt.get(field) != value for field, value in expected_stage.items()):
            raise formal_runtime.RuntimeManifestError("preactivation stage mismatch")
    domain = f"gui/{os.getuid()}"
    loaded: list[dict[str, Any]] = []
    live_aggregate: dict[str, Any] | None = None
    live_receipts: dict[str, dict[str, Any]] = {}
    live_identities: dict[str, dict[str, list[Any]]] = {}
    live_plist_sha256: dict[str, str] = {}
    for label in formal_runtime.SERVICE_LABELS:
        plist_path = launch_agents / f"{label}.plist"
        if recovery_from_publisher_canary_all_stopped:
            expected_live_activation_mode = (
                "normal" if label == publisher_label else "activation-only"
            )
        elif recovery_from_activation_only_all_stopped:
            expected_live_activation_mode = "activation-only"
        else:
            expected_live_activation_mode = (
                "normal" if recovery_from_stopped else "activation-only"
            )
        live_receipt = formal_runtime.plist_receipt(
            plist_path,
            expected_activation_mode=expected_live_activation_mode,
        )
        with plist_path.open("rb") as stream:
            live_payload = plistlib.load(stream)
        live_arguments = live_payload.get("ProgramArguments")
        if not isinstance(live_arguments, list):
            raise formal_runtime.RuntimeManifestError("preactivation live plist mismatch")
        try:
            live_barrier = formal_runtime._single_argument_value(
                live_arguments,
                "--barrier",
            )
            live_expected_digest = formal_runtime._single_argument_value(
                live_arguments,
                "--expected-digest",
            )
            live_service_label = formal_runtime._single_argument_value(
                live_arguments,
                "--service-label",
            )
            live_manifest_path = formal_runtime._single_argument_value(
                live_arguments,
                "--manifest",
            )
        except formal_runtime.RuntimeManifestError as error:
            raise formal_runtime.RuntimeManifestError(
                "preactivation live plist mismatch"
            ) from error
        current_live_aggregate = _live_receipt_aggregate(
            live_receipt,
            live_arguments,
        )
        if live_aggregate is None:
            live_aggregate = current_live_aggregate
        elif current_live_aggregate != live_aggregate:
            raise formal_runtime.RuntimeManifestError("preactivation live aggregate mismatch")
        if (
            live_receipt.get("label") != label
            or live_receipt.get("service_label") != label
            or live_service_label != label
            or live_expected_digest != live_receipt.get("manifest_digest")
            or not str(live_barrier).endswith(
                f"/four-lane-activation-{live_receipt.get('generation')}.barrier"
            )
            or not str(live_receipt.get("identity", ""))
        ):
            raise formal_runtime.RuntimeManifestError("preactivation live plist mismatch")
        if recovery_from_publisher_canary_all_stopped:
            expected_live_receipt = formal_runtime.receipt_for_label(manifest, label)
            if any(
                live_receipt.get(field) != value
                for field, value in expected_live_receipt.items()
            ):
                raise formal_runtime.RuntimeManifestError(
                    "preactivation publisher-canary live target identity mismatch"
                )
            if (
                Path(str(live_barrier)) != barrier
                or Path(str(live_manifest_path)) != manifest_path
            ):
                raise formal_runtime.RuntimeManifestError(
                    "preactivation publisher-canary live target path mismatch"
                )
        target = f"{domain}/{label}"
        result = runner(["launchctl", "print", target])
        if result.returncode != 0:
            if (
                recovery_from_stopped
                and (
                    all_stopped_recovery
                    or label != CAPACITY_GUARD_LABEL
                )
                and result.returncode == 113
            ):
                live_receipts[label] = live_receipt
                live_plist_sha256[label] = _file_sha256(plist_path)
                loaded.append(
                    {
                        "label": label,
                        "topology": f"{expected_live_activation_mode}-absent",
                    }
                )
                continue
            raise formal_runtime.RuntimeManifestError("preactivation service is absent")
        if all_stopped_recovery:
            raise formal_runtime.RuntimeManifestError(
                "preactivation all-stopped recovery service is loaded"
            )
        if recovery_from_normal_stopped and label != CAPACITY_GUARD_LABEL:
            raise formal_runtime.RuntimeManifestError(
                "preactivation recovery business service is loaded"
            )
        if re.search(r"^\s*pid = [1-9][0-9]*\s*$", result.stdout, re.MULTILINE):
            raise formal_runtime.RuntimeManifestError("preactivation service has pid")
        identity = _launchctl_top_level_identity(result.stdout, expected_target=target)
        if (
            identity is None
            or identity["paths"] != [str(plist_path)]
            or identity["states"] not in (["not running"], ["waiting"])
            or identity["last_exit_codes"] not in (
                ([], [0]) if recovery_from_normal_stopped else ([], [0], [78])
            )
        ):
            raise formal_runtime.RuntimeManifestError("preactivation service mismatch")
        live_receipts[label] = live_receipt
        live_identities[label] = identity
        live_plist_sha256[label] = _file_sha256(plist_path)
        loaded.append(
            {
                "label": label,
                "topology": (
                    "normal-loaded-no-pid"
                    if recovery_from_normal_stopped
                    else "activation-only-loaded-no-pid"
                ),
            }
        )
    if live_aggregate is None:
        raise formal_runtime.RuntimeManifestError("preactivation live aggregate mismatch")
    if not recovery_from_normal_stopped and any(
        identity["last_exit_codes"] == [78] for identity in live_identities.values()
    ):
        _validate_publisher_reset_provenance(
            receipt_path=publisher_reset_receipt,
            expected_correlation_id=expected_reset_correlation_id,
            stage_dir=stage_dir,
            manifest=manifest,
            publisher_exact_run_id=publisher_exact_run_id,
            live_aggregate=live_aggregate,
            live_receipts=live_receipts,
            live_identities=live_identities,
            live_plist_sha256=live_plist_sha256,
        )
    return {
        "status": "PASS",
        "preactivation_transition": "accepted",
        "production_mutation": False,
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "recovery_from_normal_stopped": recovery_from_normal_stopped,
        "recovery_from_all_stopped": recovery_from_all_stopped,
        "recovery_from_activation_only_all_stopped": (
            recovery_from_activation_only_all_stopped
        ),
        "recovery_from_publisher_canary_all_stopped": (
            recovery_from_publisher_canary_all_stopped
        ),
        "loaded_labels": loaded,
    }


def _collect_capacity_tick(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    state_file: Path,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    with _sampling_lease(publisher_root):
        previous, state_error = _read_state(state_file)
        state_identity = (
            _file_identity(state_file)
            if state_error is None and state_file.exists()
            else None
        )
        runtime_error: str | None = None
        try:
            runtime_receipt = formal_runtime.validate_runtime_tick(
                "com.pantheon.content-capacity-guard",
                queue_root=queue_root.resolve(),
                state_root=publisher_root.resolve(),
                actor_root=Path(
                    os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())
                ),
                log_root=log_root.resolve(),
            )
        except (OSError, formal_runtime.RuntimeManifestError) as error:
            runtime_receipt = None
            runtime_error = f"runtime_identity_unavailable:{type(error).__name__}"
        reclaimed = (
            sum(_trim_log(log_root / name) for name in LOG_NAMES)
            if runtime_receipt is not None
            else 0
        )
        expected_inert_labels = (
            _activation_only_service_labels(runtime_receipt)
            if runtime_receipt is not None
            else []
        )
        expected_idle_labels = (
            _normal_scheduled_service_labels(runtime_receipt)
            if runtime_receipt is not None
            else []
        )
        snapshot_options: dict[str, Any] = {}
        if expected_inert_labels:
            snapshot_options["expected_inert_labels"] = expected_inert_labels
        if expected_idle_labels:
            snapshot_options["expected_idle_labels"] = expected_idle_labels
        current = _snapshot(queue_root, publisher_root, log_root, **snapshot_options)
        timestamp = time.time() if now is None else now
        previous_sampled_raw = previous.get("sampled_epoch", timestamp)
        if (
            state_error is None
            and "sampled_epoch" in previous
            and (
                type(previous_sampled_raw) not in (int, float)
                or not math.isfinite(previous_sampled_raw)
                or previous_sampled_raw < 0
                or previous_sampled_raw > timestamp
            )
        ):
            state_error = "capacity_state_sampled_epoch_invalid"
            previous_sampled_epoch = float(timestamp)
        else:
            previous_sampled_epoch = (
                float(previous_sampled_raw)
                if type(previous_sampled_raw) in (int, float)
                and math.isfinite(previous_sampled_raw)
                else float(timestamp)
            )
    stop_floor = max(
        HOST_RESERVE_MIN_BYTES,
        (current["disk_total_bytes"] + 9) // 10,
    )
    reasons: list[str] = []
    if current["bytes"] > MAX_BYTES:
        reasons.append("project_bytes_over_budget")
    if current["file_count"] > MAX_FILE_COUNT:
        reasons.append("project_files_over_budget")
    admission_available = current.get("admission_available_bytes")
    if current.get("capacity_available") is not True or not isinstance(
        admission_available, int
    ):
        reasons.append("capacity_telemetry_unknown")
    elif admission_available < stop_floor:
        reasons.append("admission_available_below_stop_floor")
    telemetry_gaps: list[str] = []
    if current.get("rss_available") is not True:
        telemetry_gaps.append("rss_telemetry_unknown")
    if current.get("swap_available") is not True:
        telemetry_gaps.append("swap_telemetry_unknown")

    elapsed = max(1.0, timestamp - previous_sampled_epoch)
    delta = current["bytes"] - int(previous.get("bytes", current["bytes"]))
    growth_per_hour = max(0, int(delta * 3600 / elapsed))
    projected = current["bytes"] + growth_per_hour * RECOVERY_WINDOW_SECONDS // 3600
    high_growth = (
        growth_per_hour > 2 * NORMAL_GROWTH_BYTES_PER_HOUR
        and (
            projected > MAX_BYTES
            or (
                isinstance(admission_available, int)
                and admission_available - growth_per_hour < stop_floor
            )
        )
    )
    high_growth_streak = int(previous.get("high_growth_streak", 0)) + 1 if high_growth else 0
    if high_growth_streak >= 2:
        reasons.append("growth_rate_would_cross_budget")

    increasing = delta > MIB
    growth_streak = int(previous.get("growth_streak", 0)) + 1 if increasing else 0
    if growth_streak >= 12:
        reasons.append("no_stabilization_within_recovery_window")

    current_rss = current.get("rss_bytes")
    current_swap = current.get("swap_used_bytes")
    previous_rss = previous.get("rss_bytes")
    previous_swap = previous.get("swap_used_bytes")
    rss_growth = (
        int(current_rss) - int(previous_rss)
        if current_rss is not None and previous_rss is not None
        else 0
    )
    swap_growth = (
        int(current_swap) - int(previous_swap)
        if current_swap is not None and previous_swap is not None
        else 0
    )
    memory_risk = rss_growth > MEMORY_STEP_BYTES and swap_growth > MEMORY_STEP_BYTES
    memory_streak = int(previous.get("memory_streak", 0)) + 1 if memory_risk else 0
    if memory_streak >= 2:
        reasons.append("rss_and_swap_growth")

    if state_error is None:
        incident, incident_error = _load_open_recovery_incident(previous, state_file)
    else:
        incident, incident_error = None, state_error
    return {
        "runtime_receipt": runtime_receipt,
        "runtime_error": runtime_error,
        "reclaimed": reclaimed,
        "snapshot_options": snapshot_options,
        "current": current,
        "timestamp": timestamp,
        "previous": previous,
        "previous_sampled_epoch": previous_sampled_epoch,
        "state_error": state_error,
        "state_identity": state_identity,
        "stop_floor": stop_floor,
        "reasons": reasons,
        "admission_available": admission_available,
        "telemetry_gaps": telemetry_gaps,
        "growth_per_hour": growth_per_hour,
        "high_growth_streak": high_growth_streak,
        "growth_streak": growth_streak,
        "memory_streak": memory_streak,
        "incident": incident,
        "incident_error": incident_error,
    }


def check_once(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    state_file: Path,
    *,
    now: float | None = None,
    stop_runner: Runner = _run,
) -> dict[str, Any]:
    with _state_writer_lock(state_file):
        return _check_once_state_locked(
            queue_root,
            publisher_root,
            log_root,
            state_file,
            now=now,
            stop_runner=stop_runner,
        )


def _check_once_state_locked(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    state_file: Path,
    *,
    now: float | None = None,
    stop_runner: Runner = _run,
) -> dict[str, Any]:
    tick = _collect_capacity_tick(
        queue_root,
        publisher_root,
        log_root,
        state_file,
        now=now,
    )
    runtime_receipt = tick["runtime_receipt"]
    runtime_error = tick["runtime_error"]
    reclaimed = tick["reclaimed"]
    current = tick["current"]
    timestamp = tick["timestamp"]
    previous = tick["previous"]
    previous_sampled_epoch = tick["previous_sampled_epoch"]
    state_error = tick["state_error"]
    state_identity = tick["state_identity"]
    stop_floor = tick["stop_floor"]
    reasons = tick["reasons"]
    admission_available = tick["admission_available"]
    telemetry_gaps = tick["telemetry_gaps"]
    growth_per_hour = tick["growth_per_hour"]
    high_growth_streak = tick["high_growth_streak"]
    growth_streak = tick["growth_streak"]
    memory_streak = tick["memory_streak"]
    incident = tick["incident"]
    incident_error = tick["incident_error"]

    def build_receipt(
        status: str,
        *,
        active_reasons: list[str] | None = None,
        recovery_incident: dict[str, Any] | None = None,
        stop_verification: dict[str, Any] | None = None,
        stopped_services: list[str] | None = None,
        sample: dict[str, Any] | None = None,
        reset_growth_baseline: bool = False,
    ) -> dict[str, Any]:
        selected_sample = current if sample is None else sample
        selected_incident = recovery_incident
        if stop_verification is None:
            stop_verification = (
                selected_incident.get("stop_verification", {})
                if isinstance(selected_incident, dict)
                else {}
            )
        if stopped_services is None:
            stopped_services = (
                list(selected_incident.get("stopped_services", []))
                if isinstance(selected_incident, dict)
                else []
            )
        payload: dict[str, Any] = {
            "schema_version": 2,
            "status": status,
            "sampled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sampled_epoch": timestamp,
            "reclaimed_log_bytes": reclaimed,
            "growth_bytes_per_hour": 0 if reset_growth_baseline else growth_per_hour,
            "high_growth_streak": 0 if reset_growth_baseline else high_growth_streak,
            "growth_streak": 0 if reset_growth_baseline else growth_streak,
            "memory_streak": 0 if reset_growth_baseline else memory_streak,
            "reasons": list(reasons if active_reasons is None else active_reasons),
            "telemetry_gaps": telemetry_gaps,
            "stop_floor_bytes": stop_floor,
            "recovery_projected_restart_bytes": RECOVERY_PROJECTED_RESTART_BYTES,
            "stopped_services": stopped_services,
            "stop_verification": stop_verification,
            **selected_sample,
        }
        if selected_incident is not None:
            payload["recovery_incident"] = selected_incident
        return payload

    def operator_required(
        blocker: str,
        candidate: dict[str, Any] | None = None,
        *,
        allow_unpersisted: bool = False,
    ) -> dict[str, Any]:
        blocked = dict(candidate or {})
        blocked["schema_version"] = 2
        blocked.setdefault(
            "incident_id",
            "capacity-operator-"
            + hashlib.sha256(f"{timestamp}:{blocker}".encode()).hexdigest()[:20],
        )
        blocked.setdefault("started_epoch", timestamp)
        blocked.setdefault("trigger_reasons", list(previous.get("reasons", [])))
        blocked.setdefault("stop_targets", [])
        blocked.setdefault("owned_labels", [])
        blocked.setdefault("stopped_by_guard", [])
        blocked.setdefault("stopped_services", list(previous.get("stopped_services", [])))
        blocked.setdefault("stop_verification", previous.get("stop_verification", {}))
        blocked.setdefault("healthy_samples", 0)
        blocked.setdefault("last_healthy_epoch", None)
        blocked.setdefault("attempts_started", 0)
        blocked.setdefault("max_attempts", MAX_AUTOMATIC_RECOVERY_ATTEMPTS)
        blocked.setdefault("attempted_labels", [])
        blocked.setdefault("started_labels", [])
        blocked.setdefault("rollback", None)
        blocked.setdefault("stop_action_receipt", None)
        blocked.setdefault("resume_action_receipt", None)
        blocked.setdefault("rollback_action_receipt", None)
        blocked.setdefault("execution_verification", None)
        blocked.setdefault("restart_baseline", None)
        blocked.setdefault("restart_samples", [])
        blocked.setdefault("post_resume_healthy_samples", 0)
        blocked.setdefault("last_post_resume_epoch", None)
        blocked.setdefault("verification_started_epoch", None)
        blocked.setdefault("restart_measurement", None)
        blocked["status"] = "OPERATOR_REQUIRED"
        blocked["updated_epoch"] = timestamp
        blocked["automatic_recovery_authorized"] = False
        blocked["authorization_blocker"] = blocker
        result = build_receipt(
            "OPERATOR_REQUIRED",
            active_reasons=[],
            recovery_incident=blocked,
        )
        try:
            _write_state(state_file, result)
            result["state_persisted"] = True
        except OSError:
            if not allow_unpersisted:
                raise
            result["state_persisted"] = False
        return result

    def fresh_recovery_authority(
        candidate: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        try:
            fresh_runtime = formal_runtime.validate_runtime_tick(
                CAPACITY_GUARD_LABEL,
                queue_root=queue_root.resolve(),
                state_root=publisher_root.resolve(),
                actor_root=Path(
                    os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())
                ),
                log_root=log_root.resolve(),
            )
        except formal_runtime.RuntimeManifestError as error:
            return None, f"runtime_identity_unavailable:{type(error).__name__}"
        fresh_context = _recovery_context(fresh_runtime)
        fresh_context.setdefault(
            "restart_projected_bytes", RECOVERY_PROJECTED_RESTART_BYTES
        )
        mismatch = _recovery_context_mismatch(candidate, fresh_context)
        if mismatch is not None:
            return fresh_context, mismatch
        disabled_labels, disabled_error = _disabled_service_labels(stop_runner)
        if disabled_labels is None:
            return fresh_context, str(disabled_error)
        disabled_owned = [
            label
            for label in candidate.get("owned_labels", [])
            if label in disabled_labels
        ]
        if disabled_owned:
            candidate["disabled_labels_at_recovery"] = disabled_owned
            return fresh_context, "owned_service_manually_disabled"
        return fresh_context, None

    def rollback_and_require_operator(
        candidate: dict[str, Any],
        failure: str,
    ) -> dict[str, Any]:
        candidate["status"] = "ROLLBACK_IN_PROGRESS"
        candidate["updated_epoch"] = timestamp
        candidate["recovery_failure"] = failure
        candidate["rollback"] = {
            "status": "ROLLBACK_IN_PROGRESS",
            "services": {},
        }
        _write_state(
            state_file,
            build_receipt(
                "ROLLBACK_IN_PROGRESS",
                active_reasons=[],
                recovery_incident=candidate,
            ),
        )
        labels = list(dict.fromkeys(candidate.get("attempted_labels", [])))
        if not labels:
            candidate["rollback"] = {
                "status": "ROLLBACK_COMPLETE",
                "stopped_labels": [],
                "launchd_absent": True,
                "reason": "no_attempted_service",
            }
            return operator_required(failure, candidate)
        try:
            receipt_path = _recovery_action_receipt_path(
                state_file,
                candidate,
                "rollback",
            )
            resume_identity = candidate.get("resume_action_receipt")
            if not _same_file_identity(resume_identity):
                raise runtime_activation.RuntimeActivationError("prior resume action receipt identity drift")
            rollback_receipt = runtime_activation.stop_capacity_services(
                labels,
                plist_paths=_incident_plist_paths(candidate, labels),
                state_root=publisher_root.resolve(strict=True),
                receipt_path=receipt_path,
                timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
                runner=stop_runner,
                allow_absent=True,
                resume_action_receipt=resume_identity,
                **_runtime_action_kwargs(candidate, labels),
            )
            candidate["rollback_action_receipt"] = _file_identity(receipt_path)
            candidate["rollback"] = {
                "status": "ROLLBACK_COMPLETE",
                "launchd_absent": True,
                "stopped_labels": list(rollback_receipt["stopped_labels"]),
                "services": rollback_receipt["services"],
                "process_drain": rollback_receipt["process_drain"],
            }
            return operator_required(failure, candidate)
        except (OSError, runtime_activation.RuntimeActivationError) as error:
            receipt_path = _recovery_action_receipt_path(
                state_file,
                candidate,
                "rollback",
            )
            if receipt_path.exists():
                try:
                    candidate["rollback_action_receipt"] = _file_identity(receipt_path)
                except OSError:
                    candidate["rollback_action_receipt"] = None
            candidate["rollback"] = {
                "status": "ROLLBACK_UNKNOWN",
                "services": {},
                "reason": f"{type(error).__name__}: {error}",
            }
            return operator_required(
                "partial_recovery_rollback_unknown",
                candidate,
            )

    def rollback_after_verification(
        candidate: dict[str, Any],
        failure: str,
    ) -> dict[str, Any]:
        try:
            with formal_runtime.runtime_shutdown_lease(
                publisher_root.resolve(strict=True),
                timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
            ):
                return rollback_and_require_operator(candidate, failure)
        except formal_runtime.RuntimeWorkBusy:
            candidate["recovery_failure"] = failure
            candidate["rollback"] = {
                "status": "ROLLBACK_UNKNOWN",
                "services": {},
                "reason": "runtime_shutdown_lease_unavailable",
            }
            return operator_required(
                "partial_recovery_rollback_unknown",
                candidate,
            )

    def update_restart_measurement(
        candidate: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        baseline = candidate.get("restart_baseline")
        if not isinstance(baseline, dict):
            raise formal_runtime.RuntimeManifestError("restart baseline is missing")
        rows = list(candidate.get("restart_samples", []))
        baseline_admission = baseline.get("admission_available_bytes")
        baseline_bytes = baseline.get("bytes")
        baseline_rss = baseline.get("rss_bytes")
        baseline_swap = baseline.get("swap_used_bytes")
        row = {
            "sample_index": len(rows),
            "sampled_epoch": timestamp,
            "admission_available_bytes": current.get("admission_available_bytes"),
            "admission_drop_bytes": (
                max(0, int(baseline_admission) - int(current["admission_available_bytes"]))
                if isinstance(baseline_admission, int)
                and isinstance(current.get("admission_available_bytes"), int)
                else None
            ),
            "project_growth_bytes": (
                max(0, int(current["bytes"]) - int(baseline_bytes))
                if isinstance(baseline_bytes, int)
                and isinstance(current.get("bytes"), int)
                else None
            ),
            "rss_growth_bytes": (
                max(0, int(current["rss_bytes"]) - int(baseline_rss))
                if isinstance(baseline_rss, int)
                and isinstance(current.get("rss_bytes"), int)
                else None
            ),
            "swap_growth_bytes": (
                max(0, int(current["swap_used_bytes"]) - int(baseline_swap))
                if isinstance(baseline_swap, int)
                and isinstance(current.get("swap_used_bytes"), int)
                else None
            ),
        }
        if not rows or rows[-1].get("sampled_epoch") != timestamp:
            rows.append(row)
        candidate["restart_samples"] = rows

        def high_water(field: str) -> int | None:
            values = [item.get(field) for item in rows]
            return (
                max(int(value) for value in values)
                if values and all(isinstance(value, int) for value in values)
                else None
            )

        max_admission_drop = high_water("admission_drop_bytes")
        max_project_growth = high_water("project_growth_bytes")
        max_rss_growth = high_water("rss_growth_bytes")
        max_swap_growth = high_water("swap_growth_bytes")
        measured_restart_bytes = (
            max(max_admission_drop, max_project_growth)
            if isinstance(max_admission_drop, int)
            and isinstance(max_project_growth, int)
            else None
        )
        measurement = {
            "pre_admission_available_bytes": baseline_admission,
            "post_admission_available_bytes": current.get(
                "admission_available_bytes"
            ),
            "admission_drop_bytes": max_admission_drop,
            "project_growth_bytes": max_project_growth,
            "measured_restart_bytes": measured_restart_bytes,
            "projected_restart_bytes": int(
                candidate.get(
                    "restart_projected_bytes",
                    RECOVERY_PROJECTED_RESTART_BYTES,
                )
            ),
            "pre_rss_bytes": baseline_rss,
            "post_rss_bytes": current.get("rss_bytes"),
            "rss_growth_bytes": max_rss_growth,
            "pre_swap_used_bytes": baseline_swap,
            "post_swap_used_bytes": current.get("swap_used_bytes"),
            "swap_growth_bytes": max_swap_growth,
            "stop_floor_bytes": stop_floor,
            "rss_growth_limit_bytes": RECOVERY_RSS_GROWTH_LIMIT_BYTES,
            "swap_growth_limit_bytes": RECOVERY_SWAP_GROWTH_LIMIT_BYTES,
            "sample_count": len(rows),
            "samples": rows,
        }
        candidate["restart_measurement"] = measurement
        post_safe = (
            current.get("capacity_available") is True
            and isinstance(current.get("admission_available_bytes"), int)
            and current["admission_available_bytes"] >= stop_floor
            and current.get("bytes", MAX_BYTES + 1) <= MAX_BYTES
            and current.get("file_count", MAX_FILE_COUNT + 1) <= MAX_FILE_COUNT
            and current.get("rss_available") is True
            and current.get("swap_available") is True
            and isinstance(measured_restart_bytes, int)
            and measured_restart_bytes
            <= int(candidate.get("restart_projected_bytes", RECOVERY_PROJECTED_RESTART_BYTES))
            and isinstance(max_rss_growth, int)
            and max_rss_growth <= RECOVERY_RSS_GROWTH_LIMIT_BYTES
            and isinstance(max_swap_growth, int)
            and max_swap_growth <= RECOVERY_SWAP_GROWTH_LIMIT_BYTES
        )
        return measurement, post_safe

    if runtime_error is not None and state_error is None:
        if incident is not None and incident.get("status") == "RECOVERY_VERIFYING":
            return rollback_after_verification(incident, runtime_error)
        raise formal_runtime.RuntimeManifestError(runtime_error)
    if state_error is not None:
        candidate = (
            previous.get("recovery_incident")
            if isinstance(previous.get("recovery_incident"), dict)
            else None
        )
        evidence = None
        if state_error.startswith(
            (
                "capacity_state_malformed",
                "capacity_state_not_object",
                "capacity_state_sampled_epoch_invalid",
            )
        ):
            evidence = _preserve_invalid_state(state_file)
        if evidence is not None:
            candidate = dict(candidate or {})
            candidate["invalid_state_evidence"] = evidence
        return operator_required(
            state_error,
            candidate,
            allow_unpersisted=True,
        )
    if incident_error is not None:
        candidate = (
            previous.get("recovery_incident")
            if isinstance(previous.get("recovery_incident"), dict)
            else None
        )
        return operator_required(incident_error, candidate)
    deferred_stop = (
        incident is not None
        and incident.get("status") == "STOPPING"
        and incident.get("stop_deferred_for_work") is True
        and incident.get("stop_action_receipt") is None
        and not incident.get("stopped_by_guard")
    )
    if deferred_stop:
        interrupted_action_path = _recovery_action_receipt_path(
            state_file, incident, "stop"
        )
        if interrupted_action_path.exists():
            try:
                interrupted_action = runtime_activation.load_action_receipt(
                    interrupted_action_path
                )
            except (OSError, runtime_activation.RuntimeActivationError):
                return operator_required("deferred_stop_action_interrupted", incident)
            prepared_retry = (
                interrupted_action.get("status") == "PREPARED"
                and interrupted_action.get("mutation_started") is False
                and interrupted_action.get("pre_stop") == {}
                and interrupted_action.get("process_drain") == {}
                and interrupted_action.get("services") == {}
                and interrupted_action.get("stopped_labels") == []
                and not interrupted_action_path.with_name(
                    f".{interrupted_action_path.name}.processes.json"
                ).exists()
            )
            if prepared_retry:
                if (
                    interrupted_action.get("action") != "capacity-stop"
                    or interrupted_action.get("incident_id") != incident["incident_id"]
                    or interrupted_action.get("labels") != incident["stop_targets"]
                    or interrupted_action.get("manifest_digest") != incident.get("manifest_digest")
                    or interrupted_action.get("runtime_identity_digest")
                    != incident.get("runtime_identity_digest")
                    or interrupted_action.get("generation") != incident.get("generation")
                    or interrupted_action.get("owned_roots") != incident.get("owned_roots")
                    or interrupted_action.get("receipt_path") != str(interrupted_action_path)
                ):
                    return operator_required("deferred_stop_action_interrupted", incident)
                incident["prepared_stop_retry_receipt"] = _file_identity(
                    interrupted_action_path
                )
            else:
                targets = list(incident["stop_targets"])
                if (
                    interrupted_action.get("action") != "capacity-stop"
                    or interrupted_action.get("incident_id") != incident["incident_id"]
                    or interrupted_action.get("status") != "STOPPED"
                    or interrupted_action.get("labels") != targets
                    or interrupted_action.get("stopped_labels") != targets
                    or interrupted_action.get("manifest_digest")
                    != incident.get("manifest_digest")
                    or interrupted_action.get("runtime_identity_digest")
                    != incident.get("runtime_identity_digest")
                    or interrupted_action.get("generation") != incident.get("generation")
                    or interrupted_action.get("owned_roots") != incident.get("owned_roots")
                    or interrupted_action.get("receipt_path")
                    != str(interrupted_action_path)
                    or not isinstance(interrupted_action.get("process_drain"), dict)
                ):
                    return operator_required("deferred_stop_action_interrupted", incident)
                try:
                    with formal_runtime.runtime_shutdown_lease(
                        publisher_root.resolve(strict=True),
                        timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
                    ):
                        current_context = _recovery_context(runtime_receipt)
                        if _recovery_context_mismatch(incident, current_context) is not None:
                            return operator_required("deferred_stop_authority_drift", incident)
                        all_absent, observations = _verify_owned_services_absent(
                            targets, stop_runner
                        )
                        if not all_absent:
                            incident["stop_reconciliation_observations"] = observations
                            return operator_required(
                                "deferred_stop_absence_unproven", incident
                            )
                        incident["stop_action_receipt"] = _file_identity(
                            interrupted_action_path
                        )
                        incident["stopped_by_guard"] = targets
                        incident["stopped_services"] = targets
                        incident["canonical_process_drain"] = interrupted_action[
                            "process_drain"
                        ]
                        incident["stop_verification"] = {
                            label: {"absent": True} for label in targets
                        }
                        incident["exclusive_quiescence"] = {
                            "status": "RUNTIME_WORK_LEASE_EXCLUSIVE",
                            "state_root": str(publisher_root.resolve(strict=True)),
                        }
                        incident["stop_deferred_for_work"] = False
                        incident["status"] = "STOPPED"
                        incident["updated_epoch"] = timestamp
                        receipt = build_receipt("STOPPED", recovery_incident=incident)
                        _write_state(state_file, receipt)
                        return receipt
                except formal_runtime.RuntimeWorkBusy:
                    receipt = build_receipt("STOPPING", recovery_incident=incident)
                    _write_state(state_file, receipt)
                    return receipt
    if incident is not None and incident.get("status") in {
        "OPERATOR_REQUIRED",
        "STOP_FAILED",
        "STOPPING",
        "RECOVERY_IN_PROGRESS",
        "ROLLBACK_IN_PROGRESS",
    } and not deferred_stop:
        return operator_required(
            str(
                incident.get("authorization_blocker")
                or (
                    "stop_verification_failed"
                    if incident.get("status") == "STOP_FAILED"
                    else "interrupted_recovery_transition"
                )
            ),
            incident,
        )

    if reasons or deferred_stop:
        if incident is not None and incident.get("status") == "RECOVERY_VERIFYING":
            with _sampling_lease(publisher_root):
                current_context = _recovery_context(runtime_receipt)
                current_context.setdefault(
                    "restart_projected_bytes",
                    RECOVERY_PROJECTED_RESTART_BYTES,
                )
                context_error = _recovery_context_mismatch(incident, current_context)
            if context_error is not None:
                return rollback_after_verification(incident, context_error)
            incident["capacity_regression_reasons"] = list(reasons)
            return rollback_after_verification(
                incident,
                "capacity_regressed_after_resume",
            )
        if incident is not None and not deferred_stop:
            tracked = list(
                incident.get("stopped_by_guard")
                or incident.get("stop_targets")
                or incident.get("owned_labels", [])
            )
            all_absent, observations = _verify_owned_services_absent(
                tracked,
                stop_runner,
            )
            if not all_absent:
                incident["capacity_regression_observations"] = observations
                return operator_required(
                    "guard_stopped_service_reappeared_during_capacity_regression",
                    incident,
                )
            incident["status"] = "STOPPED"
            incident["updated_epoch"] = timestamp
            incident["healthy_samples"] = 0
            incident["last_healthy_epoch"] = None
            incident["recovery_wait_reasons"] = []
            incident["trigger_reasons"] = list(
                dict.fromkeys([*incident.get("trigger_reasons", []), *reasons])
            )
            receipt = build_receipt("STOPPED", recovery_incident=incident)
            _write_state(state_file, receipt)
            return receipt

        with ExitStack() as stop_scope:
            try:
                stop_scope.enter_context(formal_runtime.runtime_shutdown_lease(
                    publisher_root.resolve(strict=True),
                    timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
                ))
            except formal_runtime.RuntimeWorkBusy:
                if incident is None:
                    recovery_context = _recovery_context(runtime_receipt)
                    incident = _capture_recovery_incident(
                        timestamp=timestamp,
                        reasons=reasons,
                        recovery_context=recovery_context,
                        runner=stop_runner,
                    )
                if (
                    os.environ.get("PANTHEON_FORMAL_RUNTIME") == "1"
                    and state_file != queue_root.resolve() / "capacity-guard-state.json"
                ):
                    return operator_required(
                        "deferred_stop_admission_path_unavailable", incident
                    )
                if not incident.get("stop_targets"):
                    return operator_required(
                        str(incident.get("authorization_blocker")
                            or "automatic_stop_authority_unavailable"),
                        incident,
                    )
                incident["stop_deferred_for_work"] = True
                incident["updated_epoch"] = timestamp
                receipt = build_receipt("STOPPING", recovery_incident=incident)
                _write_state(state_file, receipt)
                return receipt
            if state_identity is not None and not _same_file_identity(state_identity):
                return operator_required("capacity_state_changed_before_stop")
            if state_identity is None and state_file.exists():
                return operator_required("capacity_state_appeared_before_stop")
            fresh_runtime = formal_runtime.validate_runtime_tick(
                CAPACITY_GUARD_LABEL,
                queue_root=queue_root.resolve(),
                state_root=publisher_root.resolve(),
                actor_root=Path(
                    os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())
                ),
                log_root=log_root.resolve(),
            )
            recovery_context = _recovery_context(fresh_runtime)
            fresh_incident = _capture_recovery_incident(
                timestamp=timestamp,
                reasons=reasons,
                recovery_context=recovery_context,
                runner=stop_runner,
            )
            if deferred_stop:
                if (
                    _recovery_context_mismatch(incident, recovery_context) is not None
                    or fresh_incident["automatic_recovery_authorized"] is not True
                    or fresh_incident["stop_targets"] != incident["stop_targets"]
                    or fresh_incident["disabled_labels_before_stop"]
                    != incident["disabled_labels_before_stop"]
                    or fresh_incident["pre_stop_loaded_labels"]
                    != incident["pre_stop_loaded_labels"]
                ):
                    return operator_required("deferred_stop_authority_drift", incident)
                incident["pre_stop_services"] = fresh_incident["pre_stop_services"]
            else:
                incident = fresh_incident
            stop_targets = list(incident.get("stop_targets", []))
            if not stop_targets and incident.get("automatic_recovery_authorized") is not True:
                return operator_required(
                    str(
                        incident.get("authorization_blocker")
                        or "automatic_stop_authority_unavailable"
                    ),
                    incident,
                )
            _write_state(
                state_file,
                build_receipt(
                    "STOPPING",
                    recovery_incident=incident,
                    stop_verification={},
                    stopped_services=[],
                ),
            )
            if stop_targets:
                receipt_path = _recovery_action_receipt_path(
                    state_file,
                    incident,
                    "stop",
                )
                try:
                    stop_action = runtime_activation.stop_capacity_services(
                        stop_targets,
                        plist_paths=_incident_plist_paths(incident, stop_targets),
                        state_root=publisher_root.resolve(strict=True),
                        receipt_path=receipt_path,
                        timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
                        runner=stop_runner,
                        **_runtime_action_kwargs(incident, stop_targets),
                    )
                except (OSError, runtime_activation.RuntimeActivationError) as error:
                    if receipt_path.exists():
                        try:
                            incident["stop_action_receipt"] = _file_identity(receipt_path)
                            action = runtime_activation.load_action_receipt(receipt_path)
                            incident["stopped_by_guard"] = list(
                                action.get("stopped_labels", [])
                            )
                            incident["stopped_services"] = list(
                                action.get("stopped_labels", [])
                            )
                        except (OSError, runtime_activation.RuntimeActivationError):
                            incident["stop_action_receipt"] = None
                    incident["stop_failure"] = f"{type(error).__name__}: {error}"
                    return operator_required("capacity_stop_effector_failed", incident)
                incident["stop_action_receipt"] = _file_identity(receipt_path)
                stopped_by_guard = list(stop_action["stopped_labels"])
                stop_verification = {
                    label: {
                        "bootout_returncode": value.get("bootout_returncode"),
                        "verify_returncode": value.get("post_stop", {}).get(
                            "returncode"
                        ),
                        "absent": value.get("post_stop", {}).get("topology")
                        == "ABSENT",
                    }
                    for label, value in stop_action["services"].items()
                }
                incident["canonical_process_drain"] = stop_action["process_drain"]
            else:
                stopped_by_guard = []
                stop_verification = {}
            incident["updated_epoch"] = timestamp
            incident["stopped_by_guard"] = stopped_by_guard
            incident["stopped_services"] = stopped_by_guard
            incident["stop_verification"] = stop_verification
            incident["exclusive_quiescence"] = {
                "status": "RUNTIME_WORK_LEASE_EXCLUSIVE",
                "state_root": str(publisher_root.resolve(strict=True)),
            }
            incident["status"] = "STOPPED"
            incident["stop_deferred_for_work"] = False
            receipt = build_receipt(
                "STOPPED",
                recovery_incident=incident,
                stop_verification=stop_verification,
                stopped_services=stopped_by_guard,
            )
            _write_state(state_file, receipt)
            return receipt

    if incident is None:
        closed_incident = (
            previous.get("recovery_incident")
            if isinstance(previous.get("recovery_incident"), dict)
            and previous["recovery_incident"].get("status") == "RECOVERED"
            else None
        )
        receipt = build_receipt(
            "PASS",
            active_reasons=[],
            recovery_incident=closed_incident,
        )
        _write_state(state_file, receipt)
        return receipt

    with _sampling_lease(publisher_root):
        current_context = _recovery_context(runtime_receipt)
        current_context.setdefault(
            "restart_projected_bytes",
            RECOVERY_PROJECTED_RESTART_BYTES,
        )
        context_error = _recovery_context_mismatch(incident, current_context)
    if context_error is not None:
        if incident.get("status") == "RECOVERY_VERIFYING":
            return rollback_after_verification(incident, context_error)
        return operator_required(context_error, incident)

    if incident.get("status") == "RECOVERY_VERIFYING":
        _fresh_context, authority_error = fresh_recovery_authority(incident)
        if authority_error is not None:
            return rollback_after_verification(incident, authority_error)
        resume_identity = incident.get("resume_action_receipt")
        if not _same_file_identity(resume_identity):
            return rollback_after_verification(
                incident, "resume_action_receipt_identity_drift"
            )
        try:
            resume_action = runtime_activation.load_action_receipt(
                Path(str(resume_identity["path"]))
            )
            execution = runtime_activation.verify_capacity_resume_execution(
                resume_action,
                runner=stop_runner,
                timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
            )
            _measurement, post_safe = update_restart_measurement(incident)
        except (
            OSError,
            formal_runtime.RuntimeManifestError,
            runtime_activation.RuntimeActivationError,
        ) as error:
            incident["execution_verification"] = {
                "status": "UNKNOWN",
                "error": f"{type(error).__name__}: {error}",
            }
            return rollback_after_verification(
                incident,
                "resume_execution_verification_unknown",
            )
        incident["execution_verification"] = execution
        if not post_safe:
            return rollback_after_verification(
                incident,
                "restart_measurement_outside_reserve",
            )
        if execution["status"] in {"FAILED", "UNKNOWN"}:
            return rollback_after_verification(
                incident,
                "resume_execution_" + str(execution["status"]).lower(),
            )
        started_epoch = incident.get("verification_started_epoch")
        if execution["status"] == "PENDING" and isinstance(
            started_epoch, (int, float)
        ):
            active_since = dict(incident.get("active_run_first_seen_epoch") or {})
            active_last_seen = dict(incident.get("active_run_last_seen_epoch") or {})
            for label, service in execution["services"].items():
                if service["status"] != "PENDING":
                    active_since.pop(label, None)
                    active_last_seen.pop(label, None)
                    continue
                observation = service["observation"]
                identity = observation.get("identity")
                active = (
                    observation.get("topology") == "LOADED"
                    and isinstance(identity, dict)
                    and identity.get("states") == ["running"]
                    and bool(identity.get("pids"))
                    and isinstance(identity.get("runs"), list)
                    and len(identity["runs"]) == 1
                    and type(identity["runs"][0]) is int
                    # bootstrap 已記錄的同次執行仍可在釋放工作鎖後開始工作。
                    # 執行期限與後續 terminal 成功所需的 runs + 1 分開判斷。
                    and identity["runs"][0] >= service["required_success_runs"] - 1
                )
                if active:
                    active_since.setdefault(label, timestamp)
                    active_last_seen[label] = timestamp
                    if (
                        timestamp - float(active_since[label])
                        > RECOVERY_ACTIVE_RUN_TIMEOUT_SECONDS
                    ):
                        incident["active_run_first_seen_epoch"] = active_since
                        incident["active_run_last_seen_epoch"] = active_last_seen
                        return rollback_after_verification(
                            incident, "resume_active_run_timeout"
                        )
                elif label in active_last_seen:
                    # 已觀測到真實執行後，terminal → 下一次 StartInterval 的空窗
                    # 應從最後一次 active 觀測重新計時，不能沿用整次復機起點。
                    if (
                        timestamp - float(active_last_seen[label])
                        > RECOVERY_EXECUTION_TIMEOUT_SECONDS
                    ):
                        incident["active_run_first_seen_epoch"] = active_since
                        incident["active_run_last_seen_epoch"] = active_last_seen
                        return rollback_after_verification(
                            incident, "resume_execution_timeout"
                        )
                elif (
                    timestamp - float(started_epoch)
                    > RECOVERY_EXECUTION_TIMEOUT_SECONDS
                ):
                    incident["active_run_first_seen_epoch"] = active_since
                    incident["active_run_last_seen_epoch"] = active_last_seen
                    return rollback_after_verification(
                        incident, "resume_execution_timeout"
                    )
            incident["active_run_first_seen_epoch"] = active_since
            incident["active_run_last_seen_epoch"] = active_last_seen
            process_observation = execution.get("process_observation")
            lineage_pending = (
                all(service["status"] == "PASS" for service in execution["services"].values())
                and bool(execution["services"])
                and isinstance(process_observation, dict)
                and (
                    bool(process_observation.get("active"))
                    or bool(process_observation.get("resample_required"))
                    or bool(execution.get("lineage_missing_labels"))
                )
            )
            if lineage_pending:
                first_seen = incident.get("lineage_pending_first_seen_epoch")
                if first_seen is None:
                    first_seen = timestamp
                    incident["lineage_pending_first_seen_epoch"] = first_seen
                if timestamp - float(first_seen) > RECOVERY_EXECUTION_TIMEOUT_SECONDS:
                    return rollback_after_verification(
                        incident, "resume_lineage_timeout"
                    )
            else:
                incident["lineage_pending_first_seen_epoch"] = None
        elif execution["status"] == "PASS":
            incident["active_run_first_seen_epoch"] = {}
            incident["active_run_last_seen_epoch"] = {}
            incident["lineage_pending_first_seen_epoch"] = None
        sample_interval = timestamp - previous_sampled_epoch
        post_samples = int(incident.get("post_resume_healthy_samples", 0))
        if (
            execution["status"] == "PASS"
            and sample_interval >= RECOVERY_SAMPLE_MIN_SECONDS
        ):
            post_samples += 1
            incident["last_post_resume_epoch"] = timestamp
        incident["post_resume_healthy_samples"] = post_samples
        incident["updated_epoch"] = timestamp
        if (
            execution["status"] != "PASS"
            or post_samples < RECOVERY_POST_RESUME_HEALTHY_SAMPLES
        ):
            incident["status"] = "RECOVERY_VERIFYING"
            receipt = build_receipt(
                "RECOVERY_VERIFYING",
                active_reasons=[],
                recovery_incident=incident,
            )
            _write_state(state_file, receipt)
            return receipt
        _final_context, final_authority_error = fresh_recovery_authority(incident)
        if final_authority_error is not None:
            return rollback_after_verification(incident, final_authority_error)
        if not _same_file_identity(resume_identity):
            return rollback_after_verification(
                incident, "resume_action_receipt_identity_drift"
            )
        incident["status"] = "RECOVERED"
        incident["recovery_result"] = "AUTOMATIC_RECOVERY_COMPLETE"
        receipt = build_receipt(
            "PASS",
            active_reasons=[],
            recovery_incident=incident,
            sample=current,
            reset_growth_baseline=True,
        )
        _write_state(state_file, receipt)
        return receipt

    if int(incident.get("attempts_started", 0)) >= MAX_AUTOMATIC_RECOVERY_ATTEMPTS:
        return operator_required("automatic_recovery_attempt_limit_reached", incident)

    projected_restart_bytes = int(
        incident.get("restart_projected_bytes", RECOVERY_PROJECTED_RESTART_BYTES)
    )
    recovery_wait_reasons: list[str] = []
    if telemetry_gaps:
        recovery_wait_reasons.append("recovery_telemetry_incomplete")
    if (
        not isinstance(admission_available, int)
        or admission_available - projected_restart_bytes < stop_floor
    ):
        recovery_wait_reasons.append("restart_projection_below_reserve")
    sample_interval = timestamp - previous_sampled_epoch
    healthy_samples = int(incident.get("healthy_samples", 0))
    if recovery_wait_reasons:
        healthy_samples = 0
    elif sample_interval >= RECOVERY_SAMPLE_MIN_SECONDS:
        healthy_samples += 1
    incident["status"] = "RECOVERY_PENDING"
    incident["updated_epoch"] = timestamp
    incident["healthy_samples"] = healthy_samples
    incident["last_healthy_epoch"] = timestamp if not recovery_wait_reasons else None
    incident["recovery_wait_reasons"] = recovery_wait_reasons
    pending_receipt = build_receipt(
        "RECOVERY_PENDING",
        active_reasons=[],
        recovery_incident=incident,
    )
    _write_state(state_file, pending_receipt)
    if healthy_samples < RECOVERY_HEALTHY_SAMPLES:
        return pending_receipt

    owned_labels = list(incident.get("owned_labels", []))
    if not owned_labels:
        return operator_required("no_guard_owned_services", incident)

    pending_identity = _file_identity(state_file)
    with formal_runtime.runtime_shutdown_lease(
        publisher_root.resolve(strict=True),
        timeout_seconds=RECOVERY_SHUTDOWN_TIMEOUT_SECONDS,
    ):
        if not _same_file_identity(pending_identity):
            return operator_required("capacity_state_changed_before_recovery", incident)
        _fresh_context, authority_error = fresh_recovery_authority(incident)
        if authority_error is not None:
            return operator_required(authority_error, incident)
        all_owned_absent, absent_observations = _verify_owned_services_absent(
            owned_labels,
            stop_runner,
        )
        incident["pre_recovery_absence"] = absent_observations
        if not all_owned_absent:
            return operator_required("owned_service_not_absent_before_recovery", incident)
        for label in owned_labels:
            if not _same_file_identity(incident["plists"].get(label)):
                return operator_required("recovery_plist_identity_drift", incident)

        incident["status"] = "RECOVERY_IN_PROGRESS"
        incident["updated_epoch"] = timestamp
        incident["attempts_started"] = int(incident.get("attempts_started", 0)) + 1
        incident["attempted_labels"] = []
        incident["started_labels"] = []
        incident["activation_verification"] = {}
        incident["execution_verification"] = None
        incident["restart_baseline"] = dict(current)
        incident["restart_samples"] = []
        incident["post_resume_healthy_samples"] = 0
        incident["last_post_resume_epoch"] = None
        incident["verification_started_epoch"] = timestamp
        incident["active_run_first_seen_epoch"] = {}
        incident["active_run_last_seen_epoch"] = {}
        incident["lineage_pending_first_seen_epoch"] = None
        _write_state(
            state_file,
            build_receipt(
                "RECOVERY_IN_PROGRESS",
                active_reasons=[],
                recovery_incident=incident,
            ),
        )
        receipt_path = _recovery_action_receipt_path(
            state_file,
            incident,
            "resume",
        )
        resume_action: dict[str, Any] | None = None

        def merge_resume_action_evidence(action: dict[str, Any]) -> None:
            attempted = [
                label
                for label in action.get("attempted_labels", [])
                if label in owned_labels
            ]
            started = [
                label
                for label in action.get("started_labels", [])
                if label in attempted
            ]
            incident["attempted_labels"] = list(
                dict.fromkeys([*incident.get("attempted_labels", []), *attempted])
            )
            incident["started_labels"] = list(
                dict.fromkeys([*incident.get("started_labels", []), *started])
            )
            services = action.get("services")
            if isinstance(services, dict):
                incident["activation_verification"] = dict(services)

        try:
            resume_action = runtime_activation.resume_capacity_services(
                owned_labels,
                plist_paths=_incident_plist_paths(incident, owned_labels),
                state_root=publisher_root.resolve(strict=True),
                receipt_path=receipt_path,
                runner=stop_runner,
                **_runtime_action_kwargs(incident, owned_labels),
            )
            merge_resume_action_evidence(resume_action)
            incident["resume_action_receipt"] = _file_identity(receipt_path)
        except (OSError, runtime_activation.RuntimeActivationError) as error:
            if receipt_path.exists():
                try:
                    persisted_action = runtime_activation.load_action_receipt(receipt_path)
                    merge_resume_action_evidence(persisted_action)
                except (OSError, runtime_activation.RuntimeActivationError):
                    persisted_action = None
                try:
                    incident["resume_action_receipt"] = _file_identity(
                        receipt_path
                    )
                except OSError:
                    incident["resume_action_receipt"] = None
            observations: dict[str, Any] = {}
            possible_mutations = list(incident.get("attempted_labels", []))
            plist_paths = _incident_plist_paths(incident, owned_labels)
            for label in owned_labels:
                observation = runtime_activation.observe_launchctl_service(
                    label,
                    plist_paths[label],
                    runner=stop_runner,
                )
                observations[label] = observation
                if observation.get("topology") != "ABSENT":
                    possible_mutations.append(label)
            incident["resume_failure_observations"] = observations
            incident["attempted_labels"] = list(dict.fromkeys(possible_mutations))
            incident["resume_failure"] = f"{type(error).__name__}: {error}"
            if incident["attempted_labels"]:
                return rollback_and_require_operator(
                    incident,
                    "automatic_recovery_failed",
                )
            return operator_required("automatic_recovery_failed", incident)
        assert resume_action is not None
        if resume_action.get("status") != "STARTED":
            failure = str(resume_action.get("error") or "automatic_recovery_failed")
            if incident["attempted_labels"]:
                return rollback_and_require_operator(incident, failure)
            return operator_required(failure, incident)
        _fresh_context, post_authority_error = fresh_recovery_authority(incident)
        if post_authority_error is not None:
            return rollback_and_require_operator(incident, post_authority_error)
        incident["status"] = "RECOVERY_VERIFYING"
        incident["updated_epoch"] = timestamp
        receipt = build_receipt(
            "RECOVERY_VERIFYING",
            active_reasons=[],
            recovery_incident=incident,
        )
        _write_state(state_file, receipt)
        return receipt

def _exercise_sample(root: Path) -> dict[str, Any]:
    used_bytes, file_count = _measure_tree(root)
    total, free = _disk_sample(root)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss if sys.platform == "darwin" else rss * 1024)
    swap = _swap_used_bytes()
    return {
        "bytes": used_bytes,
        "file_count": file_count,
        "host_total": total,
        "host_free": free,
        "rss": rss_bytes,
        "rss_available": True,
        "swap": swap["value"],
        "swap_available": swap["available"],
        "swap_error": swap["error"],
    }


def run_bounded_exercise(
    exercise_root: Path,
    receipt_path: Path,
    *,
    cycle_bytes: int = MIB,
) -> dict[str, Any]:
    if not 1 <= cycle_bytes <= 8 * MIB:
        raise ValueError("cycle_bytes must be between 1 byte and 8 MiB")
    if exercise_root.exists():
        raise ValueError("exercise root must not already exist")
    exercise_root.mkdir(parents=True)
    cycles: list[dict[str, Any]] = []
    for number in (1, 2):
        before = _exercise_sample(exercise_root)
        started = time.monotonic()
        path = exercise_root / f"cycle-{number}.bin"
        path.write_bytes(bytes([number]) * cycle_bytes)
        after = _exercise_sample(exercise_root)
        cycles.append(
            {
                "cycle": number,
                "before_bytes": before["bytes"],
                "after_bytes": after["bytes"],
                "before_file_count": before["file_count"],
                "after_file_count": after["file_count"],
                "host_free_before": before["host_free"],
                "host_free_after": after["host_free"],
                "rss_before": before["rss"],
                "rss_after": after["rss"],
                "swap_before": before["swap"],
                "swap_after": after["swap"],
                "elapsed_seconds": max(time.monotonic() - started, 0.000001),
                "growth_bytes": after["bytes"] - before["bytes"],
                "rss_available": before["rss_available"] and after["rss_available"],
                "swap_available": before["swap_available"] and after["swap_available"],
            }
        )
    before_reclaim = _exercise_sample(exercise_root)
    (exercise_root / "cycle-1.bin").unlink()
    after_reclaim = _exercise_sample(exercise_root)
    simulated_loaded = set(SERVICE_LABELS)
    simulated_stop_outcomes = {
        label: {"loaded_before": True, "absent_after": True, "controller": "bounded-synthetic"}
        for label in SERVICE_LABELS
    }
    simulated_loaded.difference_update(SERVICE_LABELS)
    telemetry_available = all(
        cycle["rss_available"] and cycle["swap_available"] for cycle in cycles
    )
    receipt = {
        "schema_version": 1,
        "regression_id": "REG-PANTHEON-CAPACITY-WRITE-CYCLES-001",
        "status": "PASS" if telemetry_available else "NO-GO",
        "mode": "bounded-synthetic-dry-run",
        "production_mutation": False,
        "exercise_root": str(exercise_root),
        "cycles": cycles,
        "reclamation": {
            "bytes_before": before_reclaim["bytes"],
            "bytes_after": after_reclaim["bytes"],
            "allowlist": [str(exercise_root / "cycle-1.bin")],
        },
        "stop_loss": {
            "status": "STOPPED" if not simulated_loaded else "STOP_FAILED",
            "triggered": True,
            "registered_labels": list(SERVICE_LABELS),
            "outcomes": simulated_stop_outcomes,
            "remaining_loaded": sorted(simulated_loaded),
            "cross_project_deletions": [],
        },
    }
    _write_state(receipt_path, receipt)
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path)
    parser.add_argument("--publisher-root", type=Path)
    parser.add_argument("--log-root", type=Path)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--exercise-root", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--preflight-receipt", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expected-digest")
    parser.add_argument("--barrier", type=Path)
    parser.add_argument("--launch-agents-dir", type=Path)
    parser.add_argument("--capacity-plist", type=Path)
    parser.add_argument("--publisher-reset-receipt", type=Path)
    parser.add_argument("--expected-reset-correlation-id")
    parser.add_argument("--recovery-from-normal-stopped", action="store_true")
    parser.add_argument("--recovery-from-all-stopped", action="store_true")
    parser.add_argument(
        "--recovery-from-activation-only-all-stopped",
        action="store_true",
    )
    parser.add_argument(
        "--recovery-from-publisher-canary-all-stopped",
        action="store_true",
    )
    parser.add_argument("--reset-proof-dir", type=Path)
    parser.add_argument("--cycle-bytes", type=int, default=MIB)
    parser.add_argument(
        "command",
        choices=(
            "preflight",
            "check",
            "exercise",
            "preactivation-transition",
            "publisher-reset-receipt",
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "exercise":
        if args.exercise_root is None or args.receipt is None:
            raise SystemExit("exercise requires --exercise-root and --receipt")
        result = run_bounded_exercise(
            args.exercise_root, args.receipt, cycle_bytes=args.cycle_bytes
        )
    elif args.command == "publisher-reset-receipt":
        if None in (
            args.publisher_reset_receipt,
            args.expected_reset_correlation_id,
            args.manifest,
            args.expected_digest,
            args.launch_agents_dir,
            args.reset_proof_dir,
        ):
            raise SystemExit("publisher-reset-receipt requires reset proof inputs")
        result = write_publisher_reset_receipt(
            receipt_path=args.publisher_reset_receipt,
            correlation_id=args.expected_reset_correlation_id,
            manifest_path=args.manifest,
            expected_digest=args.expected_digest,
            launch_agents_dir=args.launch_agents_dir,
            proof_dir=args.reset_proof_dir,
        )
    elif args.command == "preactivation-transition":
        if None in (
            args.preflight_receipt,
            args.manifest,
            args.expected_digest,
            args.barrier,
            args.launch_agents_dir,
            args.capacity_plist,
        ):
            raise SystemExit("preactivation-transition requires transition inputs")
        try:
            result = validate_preactivation_transition(
                preflight_receipt=args.preflight_receipt,
                manifest_path=args.manifest,
                expected_digest=args.expected_digest,
                barrier=args.barrier,
                launch_agents_dir=args.launch_agents_dir,
                capacity_plist=args.capacity_plist,
                publisher_reset_receipt=args.publisher_reset_receipt,
                expected_reset_correlation_id=args.expected_reset_correlation_id,
                recovery_from_normal_stopped=args.recovery_from_normal_stopped,
                recovery_from_all_stopped=args.recovery_from_all_stopped,
                recovery_from_activation_only_all_stopped=(
                    args.recovery_from_activation_only_all_stopped
                ),
                recovery_from_publisher_canary_all_stopped=(
                    args.recovery_from_publisher_canary_all_stopped
                ),
            )
        except formal_runtime.RuntimeManifestError as error:
            print(
                json.dumps(
                    {
                        "status": "NO-GO",
                        "reasons": [str(error)],
                        "preactivation_transition": "rejected",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 1
    elif None in (args.queue_root, args.publisher_root, args.log_root, args.state_file):
        raise SystemExit("preflight/check require queue, publisher, log, and state paths")
    elif args.command == "preflight":
        result = preflight(args.queue_root, args.publisher_root, args.log_root)
    else:
        result = check_once(
            args.queue_root,
            args.publisher_root,
            args.log_root,
            args.state_file,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

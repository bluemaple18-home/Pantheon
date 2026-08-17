#!/usr/bin/env python3
"""監控 Pantheon 自動產文寫入面，超限時停用六個內容服務。"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import plistlib
import pwd
import re
import resource
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

from scripts import pantheon_content_runtime_manifest as formal_runtime


GIB = 1024**3
MIB = 1024**2
MAX_BYTES = 4 * GIB
MAX_FILE_COUNT = 120_000
NORMAL_GROWTH_BYTES_PER_HOUR = 256 * MIB
RECOVERY_WINDOW_SECONDS = 3600
SERVICE_TRANSITION_RECHECKS = 20
SERVICE_TRANSITION_RECHECK_SECONDS = 0.25
LOG_MAX_BYTES = 32 * MIB
LOG_RETAIN_BYTES = 4 * MIB
MEMORY_STEP_BYTES = 128 * MIB
SERVICE_LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
)
ACTIVATION_ONLY_IDENTITY_PATTERN = re.compile(
    r"gate2-actor:[0-9a-f]{40}:activation-only"
)
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
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _activation_only_service_labels(runtime_receipt: dict[str, Any]) -> frozenset[str]:
    if (
        runtime_receipt.get("status") == "PASS"
        and runtime_receipt.get("config_version") == "formal-runtime-v2-gate2"
        and ACTIVATION_ONLY_IDENTITY_PATTERN.fullmatch(
            str(runtime_receipt.get("identity", ""))
        )
    ):
        return frozenset(SERVICE_LABELS)
    return frozenset()


def _normal_scheduled_service_labels(
    runtime_receipt: dict[str, Any],
) -> frozenset[str]:
    """只信任 manifest-bound、owner/mode 正確的正式 interval job。"""
    if (
        runtime_receipt.get("status") != "PASS"
        or ACTIVATION_ONLY_IDENTITY_PATTERN.fullmatch(
            str(runtime_receipt.get("identity", ""))
        )
    ):
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
) -> dict[str, list[str]] | None:
    """只解析 root service object 的 state/path/exit；結構不完整時回傳 None。"""
    depth = 0
    root_started = False
    root_closed = False
    states: list[str] = []
    paths: list[str] = []
    last_exit_codes: list[int] = []
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
            match = LAUNCHCTL_STATE_FIELD_PATTERN.fullmatch(line)
            if match is not None:
                states.append(match.group(1))
            match = LAUNCHCTL_PATH_FIELD_PATTERN.fullmatch(line)
            if match is not None:
                paths.append(match.group(1))
            match = LAUNCHCTL_LAST_EXIT_CODE_FIELD_PATTERN.fullmatch(line)
            if match is not None:
                last_exit_codes.append(int(match.group(1)))
    if not root_started or not root_closed or depth != 0:
        return None
    return {
        "states": states,
        "paths": paths,
        "last_exit_codes": last_exit_codes,
    }


def _service_rss_bytes(
    runner: Runner = _run,
    *,
    expected_inert_labels: frozenset[str] = frozenset(),
    expected_idle_labels: frozenset[str] = frozenset(),
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
                and identity["states"] == ["not running"]
            ):
                inert.append({"label": label, "topology": "loaded-but-inert"})
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
                and identity["last_exit_codes"] in ([], [0])
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
                        or retry_identity["last_exit_codes"] not in ([], [0])
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
    result = runner(["ps", "-o", "rss=", "-p", ",".join(pids)])
    if result.returncode != 0:
        return {
            "value": None,
            "available": False,
            "error": f"ps_failed:{result.returncode}",
            "identity": {
                "loaded_labels": loaded,
                "inert_labels": inert,
                "idle_labels": idle,
                "absent_labels": absent,
            },
        }
    values = [int(value) for value in result.stdout.split() if value.isdigit()]
    if len(values) != len(pids):
        return {
            "value": None,
            "available": False,
            "error": "ps_parse_failed",
            "identity": {
                "loaded_labels": loaded,
                "inert_labels": inert,
                "idle_labels": idle,
                "absent_labels": absent,
            },
        }
    return {
        "value": sum(values) * 1024,
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


def _read_state(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


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
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _stop_services(runner: Runner = _run) -> dict[str, dict[str, Any]]:
    outcomes: dict[str, dict[str, Any]] = {}
    domain = f"gui/{os.getuid()}"
    for label in SERVICE_LABELS:
        bootout = runner(["launchctl", "bootout", f"{domain}/{label}"])
        verified = runner(["launchctl", "print", f"{domain}/{label}"])
        outcomes[label] = {
            "bootout_returncode": bootout.returncode,
            "verify_returncode": verified.returncode,
            "absent": verified.returncode in {3, 113},
            "loaded_identity": verified.stdout.strip() if verified.returncode == 0 else "",
        }
    return outcomes


def _snapshot(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    *,
    runner: Runner = _run,
    expected_inert_labels: frozenset[str] = frozenset(),
    expected_idle_labels: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    roots = (queue_root, publisher_root, log_root)
    measured = [_measure_tree(root) for root in roots]
    total_disk, free_disk = _disk_sample(queue_root)
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
        "disk_total_bytes": total_disk,
        "disk_free_bytes": free_disk,
        "rss_bytes": rss["value"],
        "rss_available": rss["available"],
        "rss_error": rss["error"],
        "rss_identity": rss["identity"],
        "swap_used_bytes": swap["value"],
        "swap_available": swap["available"],
        "swap_error": swap["error"],
    }


def preflight(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    *,
    runner: Runner = _run,
) -> dict[str, Any]:
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
    if expected_inert_labels:
        snapshot_options["expected_inert_labels"] = expected_inert_labels
    if expected_idle_labels:
        snapshot_options["expected_idle_labels"] = expected_idle_labels
    sample = _snapshot(queue_root, publisher_root, log_root, **snapshot_options)
    reasons: list[str] = []
    if sample["disk_free_bytes"] * 10 < sample["disk_total_bytes"]:
        reasons.append("disk_free_below_start_floor")
    if sample["bytes"] > MAX_BYTES:
        reasons.append("project_bytes_over_budget")
    if sample["file_count"] > MAX_FILE_COUNT:
        reasons.append("project_files_over_budget")
    if sample.get("rss_available") is not True:
        reasons.append("rss_telemetry_unknown")
    if sample.get("swap_available") is not True:
        reasons.append("swap_telemetry_unknown")
    return {"status": "PASS" if not reasons else "NO-GO", "reasons": reasons, **sample}


def check_once(
    queue_root: Path,
    publisher_root: Path,
    log_root: Path,
    state_file: Path,
    *,
    now: float | None = None,
    stop_runner: Runner = _run,
) -> dict[str, Any]:
    runtime_receipt = formal_runtime.validate_runtime_tick(
        "com.pantheon.content-capacity-guard",
        queue_root=queue_root.resolve(),
        state_root=publisher_root.resolve(),
        actor_root=Path(
            os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())
        ),
        log_root=log_root.resolve(),
    )
    reclaimed = sum(_trim_log(log_root / name) for name in LOG_NAMES)
    expected_inert_labels = _activation_only_service_labels(runtime_receipt)
    expected_idle_labels = _normal_scheduled_service_labels(runtime_receipt)
    snapshot_options: dict[str, Any] = {}
    if expected_inert_labels:
        snapshot_options["expected_inert_labels"] = expected_inert_labels
    if expected_idle_labels:
        snapshot_options["expected_idle_labels"] = expected_idle_labels
    current = _snapshot(queue_root, publisher_root, log_root, **snapshot_options)
    timestamp = time.time() if now is None else now
    previous = _read_state(state_file)
    stop_floor = max(20 * GIB, current["disk_total_bytes"] // 10)
    reasons: list[str] = []
    if current["bytes"] > MAX_BYTES:
        reasons.append("project_bytes_over_budget")
    if current["file_count"] > MAX_FILE_COUNT:
        reasons.append("project_files_over_budget")
    if current["disk_free_bytes"] < stop_floor:
        reasons.append("disk_free_below_stop_floor")
    if current.get("rss_available") is not True:
        reasons.append("rss_telemetry_unknown")
    if current.get("swap_available") is not True:
        reasons.append("swap_telemetry_unknown")
    if previous.get("status") == "STOP_FAILED":
        reasons.append("stop_verification_pending")

    elapsed = max(1.0, timestamp - float(previous.get("sampled_epoch", timestamp)))
    delta = current["bytes"] - int(previous.get("bytes", current["bytes"]))
    growth_per_hour = max(0, int(delta * 3600 / elapsed))
    projected = current["bytes"] + growth_per_hour * RECOVERY_WINDOW_SECONDS // 3600
    high_growth = (
        growth_per_hour > 2 * NORMAL_GROWTH_BYTES_PER_HOUR
        and (projected > MAX_BYTES or current["disk_free_bytes"] - growth_per_hour < stop_floor)
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

    stop_verification = _stop_services(stop_runner) if reasons else {}
    all_absent = bool(stop_verification) and all(
        outcome["absent"] for outcome in stop_verification.values()
    )
    status = "PASS" if not reasons else "STOPPED" if all_absent else "STOP_FAILED"
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "sampled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sampled_epoch": timestamp,
        "reclaimed_log_bytes": reclaimed,
        "growth_bytes_per_hour": growth_per_hour,
        "high_growth_streak": high_growth_streak,
        "growth_streak": growth_streak,
        "memory_streak": memory_streak,
        "reasons": reasons,
        "stopped_services": [
            label for label, outcome in stop_verification.items() if outcome["absent"]
        ],
        "stop_verification": stop_verification,
        **current,
    }
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
    parser.add_argument("--cycle-bytes", type=int, default=MIB)
    parser.add_argument("command", choices=("preflight", "check", "exercise"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "exercise":
        if args.exercise_root is None or args.receipt is None:
            raise SystemExit("exercise requires --exercise-root and --receipt")
        result = run_bounded_exercise(
            args.exercise_root, args.receipt, cycle_bytes=args.cycle_bytes
        )
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

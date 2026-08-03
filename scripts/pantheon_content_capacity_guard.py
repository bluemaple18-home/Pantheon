#!/usr/bin/env python3
"""監控 Pantheon 自動產文寫入面，超限時停用六個內容服務。"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Callable


GIB = 1024**3
MIB = 1024**2
MAX_BYTES = 4 * GIB
MAX_FILE_COUNT = 120_000
NORMAL_GROWTH_BYTES_PER_HOUR = 256 * MIB
RECOVERY_WINDOW_SECONDS = 3600
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
        with os.scandir(directory) as entries:
            for entry in entries:
                stat_result = entry.stat(follow_symlinks=False)
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


def _service_rss_bytes(runner: Runner = _run) -> int:
    pids: list[str] = []
    domain = f"gui/{os.getuid()}"
    for label in SERVICE_LABELS:
        result = runner(["launchctl", "print", f"{domain}/{label}"])
        if result.returncode != 0:
            continue
        match = re.search(r"^\s*pid = ([1-9][0-9]*)\s*$", result.stdout, re.MULTILINE)
        if match:
            pids.append(match.group(1))
    if not pids:
        return 0
    result = runner(["ps", "-o", "rss=", "-p", ",".join(pids)])
    if result.returncode != 0:
        return 0
    return sum(int(value) for value in result.stdout.split() if value.isdigit()) * 1024


def _swap_used_bytes(runner: Runner = _run) -> int:
    result = runner(["sysctl", "-n", "vm.swapusage"])
    if result.returncode != 0:
        return 0
    match = re.search(r"used = ([0-9.]+)([MG])", result.stdout)
    if not match:
        return 0
    factor = GIB if match.group(2) == "G" else MIB
    return int(float(match.group(1)) * factor)


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


def _stop_services(runner: Runner = _run) -> list[str]:
    stopped: list[str] = []
    domain = f"gui/{os.getuid()}"
    for label in SERVICE_LABELS:
        result = runner(["launchctl", "bootout", f"{domain}/{label}"])
        if result.returncode in {0, 3, 113}:
            stopped.append(label)
    return stopped


def _snapshot(queue_root: Path, publisher_root: Path, log_root: Path) -> dict[str, int]:
    roots = (queue_root, publisher_root, log_root)
    measured = [_measure_tree(root) for root in roots]
    total_disk, free_disk = _disk_sample(queue_root)
    return {
        "bytes": sum(item[0] for item in measured),
        "file_count": sum(item[1] for item in measured),
        "disk_total_bytes": total_disk,
        "disk_free_bytes": free_disk,
        "rss_bytes": _service_rss_bytes(),
        "swap_used_bytes": _swap_used_bytes(),
    }


def preflight(queue_root: Path, publisher_root: Path, log_root: Path) -> dict[str, Any]:
    sample = _snapshot(queue_root, publisher_root, log_root)
    start_floor = max(30 * GIB, sample["disk_total_bytes"] * 15 // 100)
    reasons: list[str] = []
    if sample["disk_free_bytes"] < start_floor:
        reasons.append("disk_free_below_start_floor")
    if sample["bytes"] > MAX_BYTES:
        reasons.append("project_bytes_over_budget")
    if sample["file_count"] > MAX_FILE_COUNT:
        reasons.append("project_files_over_budget")
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
    reclaimed = sum(_trim_log(log_root / name) for name in LOG_NAMES)
    current = _snapshot(queue_root, publisher_root, log_root)
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

    rss_growth = current["rss_bytes"] - int(previous.get("rss_bytes", current["rss_bytes"]))
    swap_growth = current["swap_used_bytes"] - int(previous.get("swap_used_bytes", current["swap_used_bytes"]))
    memory_risk = rss_growth > MEMORY_STEP_BYTES and swap_growth > MEMORY_STEP_BYTES
    memory_streak = int(previous.get("memory_streak", 0)) + 1 if memory_risk else 0
    if memory_streak >= 2:
        reasons.append("rss_and_swap_growth")

    stopped = _stop_services(stop_runner) if reasons else []
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": "STOPPED" if reasons else "PASS",
        "sampled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sampled_epoch": timestamp,
        "reclaimed_log_bytes": reclaimed,
        "growth_bytes_per_hour": growth_per_hour,
        "high_growth_streak": high_growth_streak,
        "growth_streak": growth_streak,
        "memory_streak": memory_streak,
        "reasons": reasons,
        "stopped_services": stopped,
        **current,
    }
    _write_state(state_file, receipt)
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--publisher-root", type=Path, required=True)
    parser.add_argument("--log-root", type=Path, required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("command", choices=("preflight", "check"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "preflight":
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

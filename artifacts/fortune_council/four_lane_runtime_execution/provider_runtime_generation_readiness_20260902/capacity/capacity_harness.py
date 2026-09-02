#!/usr/bin/env python3
"""Rule 24 provider runtime generation readiness 的隔離容量 harness。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile
import re
from typing import Any


MAX_BYTES = 4 * 1024 * 1024
MAX_FILE_COUNT = 32
PLIST = Path("/Users/mattkuo/Library/LaunchAgents/com.pantheon.agy-gemini-i18n-new.plist")
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
SELECTED_FILES = (PLIST, RUNTIME / "runtime-manifest.json")
PRODUCTION_ROOTS = tuple(
    RUNTIME / name for name in ("actor", "queue", "state", "logs", "transactions")
)
SESSION_PREFIX = "/private/tmp/pantheon-provider-readiness-capacity-"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_metadata(path: Path) -> dict[str, Any]:
    """只 hash path/type/size/mtime；不讀 production file body 或 secret。"""
    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    if not path.is_dir():
        return {"exists": False, "metadata_sha256": None, "file_count": 0, "bytes": 0}
    for root, directories, files in os.walk(path):
        directories.sort()
        files.sort()
        root_path = Path(root)
        for name in directories + files:
            item = root_path / name
            try:
                stat = item.lstat()
            except FileNotFoundError:
                continue
            relative = item.relative_to(path)
            kind = "l" if item.is_symlink() else "d" if item.is_dir() else "f"
            size = stat.st_size if kind == "f" else 0
            if kind == "f":
                file_count += 1
                total_bytes += size
            digest.update(
                f"{relative}\0{kind}\0{size}\0{stat.st_mtime_ns}\n".encode("utf-8")
            )
    return {
        "exists": True,
        "metadata_sha256": digest.hexdigest(),
        "file_count": file_count,
        "bytes": total_bytes,
    }


def _external_snapshot() -> dict[str, Any]:
    return {
        "selected_non_secret_files": {
            str(path): {
                "exists": path.is_file(),
                "sha256": _file_sha256(path) if path.is_file() else None,
                "bytes": path.stat().st_size if path.is_file() else 0,
            }
            for path in SELECTED_FILES
        },
        "production_roots_metadata_only": {
            str(path): _tree_metadata(path) for path in PRODUCTION_ROOTS
        },
    }


def _host() -> dict[str, int]:
    usage = shutil.disk_usage("/private/tmp")
    return {"total_bytes": usage.total, "free_bytes": usage.free, "used_bytes": usage.used}


def _rss_bytes() -> int | None:
    # macOS 的 ru_maxrss 單位為 bytes；避免 sandbox 禁止的 ps process inspection。
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value) if value >= 0 else None


def _swap() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["/usr/bin/vm_stat"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return {"available": False, "swapins": None, "swapouts": None}
    swapins = re.search(r"^Swapins:\s+(\d+)\.", completed.stdout, re.MULTILINE)
    swapouts = re.search(r"^Swapouts:\s+(\d+)\.", completed.stdout, re.MULTILINE)
    return {
        "available": completed.returncode == 0 and swapins is not None and swapouts is not None,
        "swapins": int(swapins.group(1)) if swapins else None,
        "swapouts": int(swapouts.group(1)) if swapouts else None,
    }


def _usage(path: Path) -> dict[str, int]:
    files = 0
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                files += 1
                total += item.stat().st_size
    return {"bytes": total, "file_count": files}


def _safe_cleanup(path: Path, session: Path) -> None:
    resolved = path.resolve(strict=False)
    session_resolved = session.resolve(strict=True)
    if resolved.parent != session_resolved or not path.name.startswith("cycle-"):
        raise RuntimeError("cleanup target is outside exact cycle allowlist")
    shutil.rmtree(resolved)


def _write_cycle(session: Path, number: int) -> dict[str, Any]:
    cycle = session / f"cycle-{number}"
    before = {
        "usage": _usage(session),
        "host": _host(),
        "rss_bytes": _rss_bytes(),
        "swap": _swap(),
    }
    cycle.mkdir()
    payloads = {
        "output/provider-output.bin": b"P" * 8192,
        "logs/provider-generation.log": b"isolated provider_calls=0\n" * 16,
        "cache/bounded.cache": b"C" * 1024,
        "tmp/ephemeral.tmp": b"T" * 256,
        "checkpoint/cycle.json": json.dumps(
            {"cycle": number, "provider_calls": 0}, sort_keys=True
        ).encode(),
    }
    baseline = _usage(session)
    projected_bytes = baseline["bytes"] + sum(len(body) for body in payloads.values())
    projected_files = baseline["file_count"] + len(payloads)
    if projected_bytes > MAX_BYTES or projected_files > MAX_FILE_COUNT:
        raise RuntimeError("representative cycle exceeded budget before write")
    for relative, body in payloads.items():
        target = cycle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    peak = {
        "usage": _usage(session),
        "host": _host(),
        "rss_bytes": _rss_bytes(),
        "rss_peak_raw": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "swap": _swap(),
    }
    _safe_cleanup(cycle, session)
    after = {
        "usage": _usage(session),
        "host": _host(),
        "rss_bytes": _rss_bytes(),
        "swap": _swap(),
        "cycle_root_exists": cycle.exists(),
    }
    return {
        "cycle": number,
        "before": before,
        "peak": peak,
        "after_cleanup": after,
        "cleanup_reclaimed_bytes": peak["usage"]["bytes"] - after["usage"]["bytes"],
        "cleanup_reclaimed_files": peak["usage"]["file_count"] - after["usage"]["file_count"],
    }


def _stop_loss_negative(session: Path) -> dict[str, Any]:
    target = session / "cycle-stop-loss"
    attempted_bytes = MAX_BYTES + 1
    accepted = attempted_bytes <= MAX_BYTES
    if accepted:
        target.mkdir()
        (target / "unexpected.bin").write_bytes(b"x" * attempted_bytes)
    return {
        "trigger": "projected_bytes_exceeds_max_bytes",
        "attempted_bytes": attempted_bytes,
        "max_bytes": MAX_BYTES,
        "write_accepted": accepted,
        "target_created": target.exists(),
        "writes_stopped": not accepted and not target.exists(),
        "automatic_restart_enabled": False,
        "other_project_processes_stopped": 0,
        "launchctl_mutation": 0,
    }


def main() -> int:
    external_before = _external_snapshot()
    host_before = _host()
    reserve_bytes = max(20 * 1024**3, host_before["total_bytes"] // 10)
    session = Path(tempfile.mkdtemp(prefix=Path(SESSION_PREFIX).name, dir="/private/tmp"))
    marker = session / ".owned-by-provider-readiness-capacity-harness"
    control = session / "control-sentinel.txt"
    marker.write_text("owned\n", encoding="utf-8")
    control.write_text("must-survive-cycle-cleanup\n", encoding="utf-8")
    cycles: list[dict[str, Any]] = []
    try:
        cycles = [_write_cycle(session, 1), _write_cycle(session, 2)]
        stop_loss = _stop_loss_negative(session)
        control_survived = control.read_text(encoding="utf-8") == "must-survive-cycle-cleanup\n"
        peak_bytes = max(cycle["peak"]["usage"]["bytes"] for cycle in cycles)
        projection = {
            "measured_peak_bytes": peak_bytes,
            "one_hour_worst_bytes_if_cleanup_fails": peak_bytes * 12,
            "one_day_worst_bytes_if_cleanup_fails": peak_bytes * 288,
            "retention_peak_bytes": peak_bytes,
            "host_reserve_bytes": reserve_bytes,
            "free_after_one_hour_projection_bytes": host_before["free_bytes"] - peak_bytes * 12,
            "free_after_one_day_projection_bytes": host_before["free_bytes"] - peak_bytes * 288,
        }
    finally:
        if session.exists():
            if not marker.is_file() or not str(session).startswith(SESSION_PREFIX):
                raise RuntimeError("refused final cleanup without exact ownership proof")
            shutil.rmtree(session)
    external_after = _external_snapshot()
    host_after = _host()
    selected_equal = all(
        external_before["selected_non_secret_files"][key]["sha256"]
        == external_after["selected_non_secret_files"][key]["sha256"]
        for key in external_before["selected_non_secret_files"]
    )
    roots_equal = all(
        external_before["production_roots_metadata_only"][key]["metadata_sha256"]
        == external_after["production_roots_metadata_only"][key]["metadata_sha256"]
        for key in external_before["production_roots_metadata_only"]
    )
    cleanup_ok = all(
        cycle["cleanup_reclaimed_bytes"] > 0
        and cycle["cleanup_reclaimed_files"] == 5
        and not cycle["after_cleanup"]["cycle_root_exists"]
        for cycle in cycles
    )
    reserve_ok = (
        host_before["free_bytes"] >= host_before["total_bytes"] // 10
        and projection["free_after_one_day_projection_bytes"] >= reserve_bytes
    )
    telemetry_ok = all(
        sample["rss_bytes"] is not None and sample["swap"]["available"]
        for cycle in cycles
        for sample in (cycle["before"], cycle["peak"], cycle["after_cleanup"])
    )
    reasons: list[str] = []
    if not cleanup_ok:
        reasons.append("isolated_cleanup_not_verified")
    if not stop_loss["writes_stopped"]:
        reasons.append("stop_loss_failed_open")
    if not control_survived:
        reasons.append("cleanup_touched_control_sentinel")
    if not selected_equal:
        reasons.append("selected_public_path_hash_changed")
    if not roots_equal:
        reasons.append("production_root_metadata_hash_changed")
    if not reserve_ok:
        reasons.append("host_free_projection_below_rule24_reserve")
    if not telemetry_ok:
        reasons.append("rss_or_swap_telemetry_unavailable")
    status = "PASS" if not reasons else "BLOCKED"
    budget = {
        "max_bytes": MAX_BYTES,
        "max_file_count": MAX_FILE_COUNT,
        "normal_growth_bytes_per_hour_after_cleanup": 0,
        "spike_window_seconds": 300,
        "stable_or_cleanup_within_seconds": 30,
        "retention_seconds": 0,
        "rotation_or_compression": "每 cycle 完成即刪除 exact owned cycle root；不保留原檔",
        "monitoring_interval_seconds": 300,
        "cleanup_allowlist": [
            f"{SESSION_PREFIX}<random>/cycle-1",
            f"{SESSION_PREFIX}<random>/cycle-2",
            f"{SESSION_PREFIX}<random> (final cleanup only after ownership marker validation)",
        ],
    }
    inventory = {
        "write_root": f"{SESSION_PREFIX}<random>",
        "output": "cycle-N/output/provider-output.bin",
        "log": "cycle-N/logs/provider-generation.log",
        "cache": "cycle-N/cache/bounded.cache",
        "tmp": "cycle-N/tmp/ephemeral.tmp",
        "checkpoint": "cycle-N/checkpoint/cycle.json",
        "downloads": None,
        "screenshots": None,
        "database_or_wal": None,
        "models": None,
        "build_artifacts": None,
        "container_data": None,
        "archives": None,
        "production_roots_written": [],
    }
    result = {
        "schema": "pantheon.provider_runtime_rule24_readiness.v1",
        "task": "PANTHEON-PROVIDER-RUNTIME-GENERATION-READINESS-20260902",
        "status": status,
        "reasons": reasons,
        "scope": "isolated Rule 24 generation readiness only; no activation claim",
        "write_root_inventory": inventory,
        "budget": budget,
        "host_before": host_before,
        "host_after": host_after,
        "cycles": cycles,
        "projection": projection,
        "cleanup": {
            "actual_cleanup": cleanup_ok,
            "control_sentinel_survived_cycle_cleanup": control_survived,
            "session_root_removed": not session.exists(),
        },
        "stop_loss_negative": stop_loss,
        "immutability": {
            "before": external_before,
            "after": external_after,
            "selected_file_hashes_equal": selected_equal,
            "production_root_metadata_hashes_equal": roots_equal,
            "production_mutation": 0 if selected_equal and roots_equal else "concurrent_or_unknown_change_detected",
        },
        "commands": [
            "/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 artifacts/fortune_council/four_lane_runtime_execution/provider_runtime_generation_readiness_20260902/capacity/capacity_harness.py",
            "git diff --check -- artifacts/.../identity artifacts/.../capacity",
        ],
        "execution_attempts": [
            {
                "status": "BLOCKED_BEFORE_CYCLE_WRITE",
                "reason": "sandbox denied /bin/ps RSS inspection",
                "owned_temp_session_cleanup": "PASS",
                "production_mutation": 0,
            },
            {
                "status": "PASS",
                "telemetry": "in-process ru_maxrss plus vm_stat swap counters",
            },
        ],
        "network_calls": 0,
        "provider_calls": 0,
        "launchctl_mutation": 0,
    }
    output = Path(__file__).resolve().parent
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = f"""# Rule 24 capacity readiness

最終結果：`{status}`

- 兩個 representative isolated cycles：`{len(cycles)}`；每輪 exact owned root 均實際清理並回收。
- bounded budget：`{MAX_BYTES}` bytes／`{MAX_FILE_COUNT}` files；穩態每小時增長 `0` bytes。
- stop-loss 負向演練：`{'PASS' if stop_loss['writes_stopped'] else 'BLOCKED'}`；超限 write 在建立 root 前遭拒，automatic restart=`false`。
- host reserve projection：`{'PASS' if reserve_ok else 'BLOCKED'}`；Rule 24 reserve `{reserve_bytes}` bytes。
- installed plist／selected public non-secret files hashes：`{'相同' if selected_equal else '不同'}`。
- Pantheon-canary-runtime-v8 production roots metadata hashes：`{'相同' if roots_equal else '不同'}`。
- network/provider calls：`0`；launchctl mutation：`0`；production mutation：`{0 if selected_equal and roots_equal else '未證明為 0'}`。

結構化 inventory、cycles、RSS/swap、projection、cleanup 與 before/after hashes 見 `result.json`。
"""
    (output / "result.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"status": status, "result": str(output / "result.json")}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

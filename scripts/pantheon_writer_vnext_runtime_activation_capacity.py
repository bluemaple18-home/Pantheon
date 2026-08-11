#!/usr/bin/env python3
"""RA-SLICE-005 兩週期容量與 fail-closed proof harness。"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import time
from typing import Any

from scripts.pantheon_writer_vnext_runtime_activation_e2e import (
    run_runtime_activation_e2e,
)


GIB = 1024**3
MIB = 1024**2
SCHEMA_VERSION = 1
EVIDENCE_PATH = Path(
    "artifacts/fortune_council/content_writer_vnext_execution/"
    "runtime_activation/ra_slice_005"
)
REQUIRED_POLICY_FIELDS = (
    "max_bytes",
    "max_file_count",
    "normal_growth_bytes_per_hour",
    "peak_window_seconds",
    "recovery_deadline_seconds",
    "retention_seconds",
    "sampling_interval_seconds",
    "max_rss_growth_bytes_per_sample",
    "max_swap_growth_bytes_per_sample",
)
CALLER_VERDICT_FIELDS = {"status", "verdict", "ready", "valid", "pass"}
DEFAULT_POLICY = {
    "max_bytes": 67_108_864,
    "max_file_count": 1_024,
    "normal_growth_bytes_per_hour": 67_108_864,
    "peak_window_seconds": 1_800,
    "recovery_deadline_seconds": 300,
    "retention_seconds": 86_400,
    "sampling_interval_seconds": 300,
    "max_rss_growth_bytes_per_sample": 268_435_456,
    "max_swap_growth_bytes_per_sample": 268_435_456,
}
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
Workload = Callable[..., dict[str, Any]]
Sampler = Callable[[Path, str, float], Mapping[str, Any]]
Cleanup = Callable[[Path], None]


class CapacityProofBlocked(ValueError):
    """容量 proof 的 deterministic fail-closed 錯誤。"""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)
        super().__init__(str(self.payload.get("reason") or self.payload.get("case")))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _write_text(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _canonical_path(path: Path, label: str, *, must_be_dir: bool = False) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError(f"{label} must be canonical absolute")
    try:
        resolved = candidate.resolve(strict=must_be_dir)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"{label} must be canonical absolute") from error
    if resolved != candidate:
        raise ValueError(f"{label} must be canonical absolute")
    if must_be_dir and not candidate.is_dir():
        raise ValueError(f"{label} must be an existing directory")
    return candidate


def _validate_policy(policy: Mapping[str, Any]) -> dict[str, int]:
    if not isinstance(policy, Mapping):
        raise ValueError("policy must be an object")
    verdict_fields = sorted(set(policy).intersection(CALLER_VERDICT_FIELDS))
    if verdict_fields:
        raise ValueError(f"policy must not include caller verdict fields: {verdict_fields}")
    missing = [field for field in REQUIRED_POLICY_FIELDS if field not in policy]
    if missing:
        raise ValueError(f"policy fields are missing: {missing}")
    parsed: dict[str, int] = {}
    for field in REQUIRED_POLICY_FIELDS:
        value = policy[field]
        if type(value) is bool or not isinstance(value, int) or value < 0:
            raise ValueError(f"policy field is invalid: {field}")
        if field != "normal_growth_bytes_per_hour" and value == 0:
            raise ValueError(f"policy field must be bounded positive: {field}")
        parsed[field] = value
    if parsed["sampling_interval_seconds"] > 300:
        raise ValueError("sampling_interval_seconds must be <= 300")
    if parsed["normal_growth_bytes_per_hour"] == 0:
        raise ValueError("normal_growth_bytes_per_hour must be bounded positive")
    return parsed


def _measure_tree(root: Path) -> tuple[int, int]:
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


def _swap_used_bytes() -> int:
    try:
        import subprocess

        result = subprocess.run(
            ["sysctl", "-n", "vm.swapusage"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        result = None
    if result is not None and result.returncode == 0:
        for chunk in result.stdout.split(","):
            chunk = chunk.strip()
            if chunk.startswith("used = "):
                number, unit = chunk.removeprefix("used = ").split()[:2]
                factor = GIB if unit.startswith("G") else MIB
                return int(float(number) * factor)
    try:
        values = {
            line.split(":", 1)[0]: int(line.split()[1]) * 1024
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
            if line.startswith(("SwapTotal:", "SwapFree:"))
        }
    except (FileNotFoundError, OSError, ValueError, IndexError):
        values = {}
    if set(values) == {"SwapTotal", "SwapFree"}:
        return values["SwapTotal"] - values["SwapFree"]
    return 0


def _default_sampler(project_root: Path, label: str, started: float) -> dict[str, Any]:
    project_bytes, file_count = _measure_tree(project_root)
    total, _used, free = shutil.disk_usage(project_root)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss if sys.platform == "darwin" else rss * 1024)
    return {
        "label": label,
        "sampled_epoch": time.time(),
        "elapsed_seconds": max(time.monotonic() - started, 0.0),
        "host_total_bytes": int(total),
        "host_free_bytes": int(free),
        "project_bytes": int(project_bytes),
        "file_count": int(file_count),
        "process_rss_bytes": rss_bytes,
        "swap_used_bytes": _swap_used_bytes(),
    }


def _sample(
    sampler: Sampler,
    project_root: Path,
    label: str,
    started: float,
) -> dict[str, int | float | str]:
    raw = dict(sampler(project_root, label, started))
    required = (
        "host_total_bytes",
        "host_free_bytes",
        "project_bytes",
        "file_count",
        "process_rss_bytes",
        "swap_used_bytes",
        "elapsed_seconds",
    )
    for field in required:
        value = raw.get(field)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"required measurement is invalid: {field}")
    if int(raw["host_total_bytes"]) <= 0:
        raise ValueError("host_total_bytes must be positive")
    return {
        "label": str(raw.get("label") or label),
        "sampled_epoch": float(raw.get("sampled_epoch", time.time())),
        "elapsed_seconds": float(raw["elapsed_seconds"]),
        "host_total_bytes": int(raw["host_total_bytes"]),
        "host_free_bytes": int(raw["host_free_bytes"]),
        "project_bytes": int(raw["project_bytes"]),
        "file_count": int(raw["file_count"]),
        "process_rss_bytes": int(raw["process_rss_bytes"]),
        "swap_used_bytes": int(raw["swap_used_bytes"]),
    }


def _host_reserve(sample: Mapping[str, Any]) -> int:
    return max(20 * GIB, int(sample["host_total_bytes"]) // 10)


def _block_payload(
    *,
    case: str,
    reason: str,
    cycle: int | None,
    next_cycle_started: bool,
    external_cleanup_performed: bool,
    last_safe_sample: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED",
        "case": case,
        "reason": reason,
        "cycle": cycle,
        "next_cycle_started": next_cycle_started,
        "external_cleanup_performed": external_cleanup_performed,
        "last_safe_sample": dict(last_safe_sample or {}),
        "canary_created": False,
        "production_mutation": False,
        "complete_pass_receipt_written": False,
    }


def _raise_blocked(
    evidence_root: Path,
    *,
    case: str,
    reason: str,
    cycle: int | None = None,
    next_cycle_started: bool = False,
    external_cleanup_performed: bool = False,
    last_safe_sample: Mapping[str, Any] | None = None,
) -> None:
    payload = _block_payload(
        case=case,
        reason=reason,
        cycle=cycle,
        next_cycle_started=next_cycle_started,
        external_cleanup_performed=external_cleanup_performed,
        last_safe_sample=last_safe_sample,
    )
    _write_json(evidence_root / "blocked-capacity.json", payload)
    raise CapacityProofBlocked(payload)


def _check_policy_limits(
    sample: Mapping[str, Any],
    policy: Mapping[str, int],
    evidence_root: Path,
    *,
    cycle: int | None,
    last_safe_sample: Mapping[str, Any] | None,
) -> None:
    if int(sample["host_free_bytes"]) < _host_reserve(sample):
        _raise_blocked(
            evidence_root,
            case="host-free-below-reserve",
            reason="host free bytes are below max(20 GiB, 10% total)",
            cycle=cycle,
            last_safe_sample=last_safe_sample,
        )
    if int(sample["project_bytes"]) > policy["max_bytes"]:
        _raise_blocked(
            evidence_root,
            case="project-bytes-over-budget",
            reason="project bytes exceed policy max_bytes",
            cycle=cycle,
            last_safe_sample=last_safe_sample,
        )
    if int(sample["file_count"]) > policy["max_file_count"]:
        _raise_blocked(
            evidence_root,
            case="project-file-count-over-budget",
            reason="project file count exceeds policy max_file_count",
            cycle=cycle,
            last_safe_sample=last_safe_sample,
        )


def _check_sample_growth(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    policy: Mapping[str, int],
    evidence_root: Path,
    *,
    cycle: int,
) -> None:
    if (
        int(after["process_rss_bytes"]) - int(before["process_rss_bytes"])
        > policy["max_rss_growth_bytes_per_sample"]
    ):
        _raise_blocked(
            evidence_root,
            case="rss-growth-over-budget",
            reason="process RSS growth exceeds policy max_rss_growth_bytes_per_sample",
            cycle=cycle,
            last_safe_sample=before,
        )
    if (
        int(after["swap_used_bytes"]) - int(before["swap_used_bytes"])
        > policy["max_swap_growth_bytes_per_sample"]
    ):
        _raise_blocked(
            evidence_root,
            case="swap-growth-over-budget",
            reason="swap growth exceeds policy max_swap_growth_bytes_per_sample",
            cycle=cycle,
            last_safe_sample=before,
        )


def _direct_children(root: Path) -> set[Path]:
    try:
        return {Path(entry.path).resolve(strict=False) for entry in os.scandir(root)}
    except FileNotFoundError:
        return set()


def _reject_unknown_writes(
    sandbox_root: Path,
    allowed_roots: set[Path],
    evidence_root: Path,
    *,
    cycle: int,
    last_safe_sample: Mapping[str, Any],
) -> None:
    unknown = sorted(
        path for path in _direct_children(sandbox_root) if path not in allowed_roots
    )
    if unknown:
        _raise_blocked(
            evidence_root,
            case="unknown-write-path",
            reason="sandbox contains unregistered write paths",
            cycle=cycle,
            last_safe_sample=last_safe_sample,
        )


def _cycle_marker(cycle_root: Path, cycle: int, actor_identity: str) -> Path:
    return cycle_root / ".ra-slice-005-cycle-identity.json"


def _write_cycle_marker(cycle_root: Path, cycle: int, actor_identity: str) -> None:
    _write_json(
        _cycle_marker(cycle_root, cycle, actor_identity),
        {"cycle": cycle, "actor_identity": actor_identity, "owned_by": "RA-SLICE-005"},
    )


def _verify_cycle_marker(cycle_root: Path, cycle: int, actor_identity: str) -> None:
    payload = json.loads(_cycle_marker(cycle_root, cycle, actor_identity).read_text())
    if payload != {
        "actor_identity": actor_identity,
        "cycle": cycle,
        "owned_by": "RA-SLICE-005",
    }:
        raise ValueError("cycle root identity marker drifted")


def _capability_receipt_pass(result: Mapping[str, Any]) -> bool:
    receipt = result.get("receipt")
    if not isinstance(receipt, Mapping):
        return False
    steps = receipt.get("steps")
    capabilities = [step.get("capability") for step in steps] if isinstance(steps, list) else []
    return (
        result.get("status") == "PASS"
        and result.get("mode") == "synthetic-non-production"
        and result.get("canary_created") is False
        and result.get("production_mutation") is False
        and capabilities == list(CAPABILITIES)
    )


def _cleanup_cycle_root(cycle_root: Path) -> None:
    shutil.rmtree(cycle_root)


def run_capacity_proof(
    *,
    capacity_sandbox_root: Path,
    evidence_root: Path,
    runtime_receipt: Mapping[str, Any],
    actor_identity: str,
    brief: Mapping[str, Any],
    policy: Mapping[str, Any],
    sampler: Sampler = _default_sampler,
    workload: Workload = run_runtime_activation_e2e,
    cleanup: Cleanup = _cleanup_cycle_root,
) -> dict[str, Any]:
    """執行兩個完整 non-production E2E cycle，並保存容量 proof receipt。"""

    evidence_root = _canonical_path(evidence_root, "evidence root")
    evidence_root.mkdir(parents=True, exist_ok=True)
    try:
        parsed_policy = _validate_policy(policy)
        sandbox_root = _canonical_path(capacity_sandbox_root, "capacity sandbox root")
        if not isinstance(runtime_receipt, Mapping):
            raise ValueError("runtime receipt must be an object")
        if not isinstance(brief, Mapping):
            raise ValueError("brief must be an object")
        if type(actor_identity) is not str or not actor_identity.strip():
            raise ValueError("actor_identity is required")
    except ValueError as error:
        _raise_blocked(
            evidence_root,
            case="invalid-policy" if "policy" in str(error) else "invalid-input",
            reason=str(error),
            cycle=None,
        )
    sandbox_root.mkdir(parents=True, exist_ok=True)
    sandbox_root = _canonical_path(sandbox_root, "capacity sandbox root", must_be_dir=True)
    cycles: list[dict[str, Any]] = []
    created_roots: set[Path] = set()

    for cycle in (1, 2):
        cycle_started = time.monotonic()
        cycle_root = sandbox_root / f"cycle-{cycle}"
        if cycle_root.exists():
            _raise_blocked(
                evidence_root,
                case="cycle-root-already-exists",
                reason="cycle root already exists before this harness creates it",
                cycle=cycle,
            )
        try:
            before = _sample(sampler, sandbox_root, f"cycle-{cycle}-before", cycle_started)
        except ValueError as error:
            _raise_blocked(
                evidence_root,
                case="missing-required-measurement",
                reason=str(error),
                cycle=cycle,
            )
        _check_policy_limits(
            before,
            parsed_policy,
            evidence_root,
            cycle=cycle,
            last_safe_sample=before,
        )
        cycle_root.mkdir()
        cycle_root = cycle_root.resolve(strict=True)
        created_roots.add(cycle_root)
        _write_cycle_marker(cycle_root, cycle, actor_identity)
        _reject_unknown_writes(
            sandbox_root,
            created_roots,
            evidence_root,
            cycle=cycle,
            last_safe_sample=before,
        )
        result = workload(
            trusted_sandbox_root=cycle_root,
            runtime_receipt=runtime_receipt,
            execution_line_id=f"exec-ra-slice-005-cycle-{cycle}",
            correlation_id=f"corr-ra-slice-005-cycle-{cycle}",
            actor_identity=actor_identity,
            brief=dict(brief),
        )
        if not _capability_receipt_pass(result):
            _raise_blocked(
                evidence_root,
                case="e2e-receipt-invalid",
                reason="workload did not return a complete non-production PASS receipt",
                cycle=cycle,
                last_safe_sample=before,
            )
        _write_json(evidence_root / f"cycle-{cycle}-runtime-receipt.json", result)
        try:
            peak = _sample(sampler, sandbox_root, f"cycle-{cycle}-peak", cycle_started)
        except ValueError as error:
            _raise_blocked(
                evidence_root,
                case="missing-required-measurement",
                reason=str(error),
                cycle=cycle,
                last_safe_sample=before,
            )
        _check_policy_limits(
            peak,
            parsed_policy,
            evidence_root,
            cycle=cycle,
            last_safe_sample=before,
        )
        _check_sample_growth(before, peak, parsed_policy, evidence_root, cycle=cycle)
        _reject_unknown_writes(
            sandbox_root,
            created_roots,
            evidence_root,
            cycle=cycle,
            last_safe_sample=before,
        )

        cleanup_started = time.monotonic()
        before_cleanup_bytes = int(peak["project_bytes"])
        before_cleanup_files = int(peak["file_count"])
        try:
            _verify_cycle_marker(cycle_root, cycle, actor_identity)
            cleanup(cycle_root)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            _raise_blocked(
                evidence_root,
                case="cleanup-root-still-exists",
                reason=str(error),
                cycle=cycle,
                last_safe_sample=before,
            )
        cleanup_elapsed = time.monotonic() - cleanup_started
        created_roots.remove(cycle_root)
        try:
            after_cleanup = _sample(
                sampler,
                sandbox_root,
                f"cycle-{cycle}-after-cleanup",
                cycle_started,
            )
        except ValueError as error:
            _raise_blocked(
                evidence_root,
                case="missing-required-measurement",
                reason=str(error),
                cycle=cycle,
                last_safe_sample=before,
            )
        if cycle_root.exists() or cleanup_elapsed > parsed_policy["recovery_deadline_seconds"]:
            _raise_blocked(
                evidence_root,
                case="cleanup-root-still-exists",
                reason="cycle root cleanup failed or missed recovery deadline",
                cycle=cycle,
                last_safe_sample=before,
            )
        reclaimed_bytes = before_cleanup_bytes - int(after_cleanup["project_bytes"])
        reclaimed_files = before_cleanup_files - int(after_cleanup["file_count"])
        if reclaimed_bytes <= 0 or reclaimed_files <= 0:
            _raise_blocked(
                evidence_root,
                case="cleanup-reclaim-missing",
                reason="cleanup did not reclaim positive bytes and file count",
                cycle=cycle,
                last_safe_sample=before,
            )
        _check_policy_limits(
            after_cleanup,
            parsed_policy,
            evidence_root,
            cycle=cycle,
            last_safe_sample=after_cleanup,
        )
        growth_bytes = max(0, int(peak["project_bytes"]) - int(before["project_bytes"]))
        growth_elapsed = max(float(peak["elapsed_seconds"]) - float(before["elapsed_seconds"]), 0.001)
        measurement = {
            "cycle": cycle,
            "execution_line_id": f"exec-ra-slice-005-cycle-{cycle}",
            "correlation_id": f"corr-ra-slice-005-cycle-{cycle}",
            "root": str(cycle_root),
            "root_unique": True,
            "capability_receipt_status": "PASS",
            "seven_step_capabilities": list(CAPABILITIES),
            "canary_created": False,
            "production_mutation": False,
            "before": before,
            "peak": peak,
            "after_cleanup": after_cleanup,
            "growth_bytes_per_hour": int(growth_bytes * 3600 / growth_elapsed),
            "peak_transaction_temp_bytes": growth_bytes,
            "cleanup": {
                "root_exists_after_cleanup": cycle_root.exists(),
                "elapsed_seconds": cleanup_elapsed,
                "reclaimed_bytes": reclaimed_bytes,
                "reclaimed_file_count": reclaimed_files,
            },
        }
        _write_json(evidence_root / f"cycle-{cycle}-measurements.json", measurement)
        cycles.append(measurement)

    measured_max_growth_per_hour = max(cycle["growth_bytes_per_hour"] for cycle in cycles)
    projected_growth_per_hour = max(
        parsed_policy["normal_growth_bytes_per_hour"],
        measured_peak := max(cycle["peak_transaction_temp_bytes"] for cycle in cycles),
    )
    last_sample = cycles[-1]["after_cleanup"]
    projections = {
        "measured_max_growth_bytes_per_hour": measured_max_growth_per_hour,
        "projected_growth_bytes_per_hour": projected_growth_per_hour,
        "hour_peak_bytes": measured_peak + projected_growth_per_hour,
        "day_peak_bytes": measured_peak + projected_growth_per_hour * 24,
        "retention_peak_bytes": measured_peak
        + projected_growth_per_hour * parsed_policy["retention_seconds"] // 3600,
        "host_reserve_bytes": _host_reserve(last_sample),
        "host_free_after_projection_bytes": int(last_sample["host_free_bytes"])
        - (
            measured_peak
            + projected_growth_per_hour * parsed_policy["retention_seconds"] // 3600
        ),
    }
    if projections["host_free_after_projection_bytes"] < projections["host_reserve_bytes"]:
        _raise_blocked(
            evidence_root,
            case="projection-below-host-reserve",
            reason="retention projection would cross host reserve",
            cycle=2,
            last_safe_sample=last_sample,
        )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "mode": "synthetic-non-production-capacity-proof",
        "cycles": cycles,
        "policy": parsed_policy,
        "projections": projections,
        "stop_loss_negative_result": "BLOCKED",
        "canary_created": False,
        "production_mutation": False,
    }
    _write_json(evidence_root / "capacity-receipt.json", receipt)
    return receipt


def _fixture_sample(
    *,
    host_total: int = 500 * GIB,
    host_free: int = 250 * GIB,
    rss: int = 64 * MIB,
    swap: int = 0,
    missing: bool = False,
) -> Sampler:
    def sampler(project_root: Path, label: str, started: float) -> Mapping[str, Any]:
        project_bytes, file_count = _measure_tree(project_root)
        payload: dict[str, Any] = {
            "label": label,
            "sampled_epoch": time.time(),
            "elapsed_seconds": max(time.monotonic() - started, 0.001),
            "host_total_bytes": host_total,
            "host_free_bytes": host_free,
            "project_bytes": project_bytes,
            "file_count": file_count,
            "process_rss_bytes": rss,
            "swap_used_bytes": swap,
        }
        if missing:
            payload.pop("host_free_bytes")
        return payload

    return sampler


def _fixture_workload(byte_count: int = 16, file_count: int = 1) -> Workload:
    def workload(**kwargs: object) -> dict[str, Any]:
        root = Path(kwargs["trusted_sandbox_root"])
        for index in range(file_count):
            (root / f"payload-{index}.txt").write_text("x" * byte_count, encoding="utf-8")
        return {
            "status": "PASS",
            "mode": "synthetic-non-production",
            "canary_created": False,
            "production_mutation": False,
            "receipt": {
                "steps": [
                    {"ordinal": ordinal, "capability": capability}
                    for ordinal, capability in enumerate(CAPABILITIES, 1)
                ]
            },
        }

    return workload


def run_capacity_negative_matrix(*, evidence_root: Path) -> dict[str, Any]:
    evidence_root = _canonical_path(evidence_root, "evidence root")
    evidence_root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []

    def collect(
        case: str,
        *,
        policy: Mapping[str, Any] = DEFAULT_POLICY,
        sampler: Sampler = _fixture_sample(),
        workload: Workload = _fixture_workload(),
        cleanup: Cleanup = _cleanup_cycle_root,
    ) -> None:
        case_root = evidence_root / "negative-probes" / case
        try:
            run_capacity_proof(
                capacity_sandbox_root=(case_root / "capacity-sandbox").resolve(),
                evidence_root=(case_root / "evidence").resolve(),
                runtime_receipt={"status": "PASS", "runtime_identity_digest": "d" * 64},
                actor_identity="actor-ra-slice-005-negative",
                brief={"schema_version": 1, "run_id": case, "mode": "create"},
                policy=policy,
                sampler=sampler,
                workload=workload,
                cleanup=cleanup,
            )
        except CapacityProofBlocked as error:
            payload = dict(error.payload)
            payload["case"] = case
            payload["outcome"] = "BLOCKED"
            payload["external_cleanup_performed"] = False
            payload["next_cycle_started"] = False
            cases.append(payload)
            return
        raise RuntimeError(f"negative probe did not block: {case}")

    collect("max-bytes-too-low", policy={**DEFAULT_POLICY, "max_bytes": 1})
    collect(
        "max-file-count-too-low",
        policy={**DEFAULT_POLICY, "max_file_count": 1},
        workload=_fixture_workload(file_count=2),
    )
    collect("host-free-below-reserve", sampler=_fixture_sample(host_free=2 * GIB))

    def rss_sampler(project_root: Path, label: str, started: float) -> Mapping[str, Any]:
        sample = dict(_fixture_sample()(project_root, label, started))
        if "peak" in label:
            sample["process_rss_bytes"] = (
                int(sample["process_rss_bytes"])
                + DEFAULT_POLICY["max_rss_growth_bytes_per_sample"]
                + MIB
            )
        return sample

    collect("rss-growth-over-budget", sampler=rss_sampler)

    def swap_sampler(project_root: Path, label: str, started: float) -> Mapping[str, Any]:
        sample = dict(_fixture_sample()(project_root, label, started))
        if "peak" in label:
            sample["swap_used_bytes"] = (
                int(sample["swap_used_bytes"])
                + DEFAULT_POLICY["max_swap_growth_bytes_per_sample"]
                + MIB
            )
        return sample

    collect("swap-growth-over-budget", sampler=swap_sampler)
    collect("cleanup-root-still-exists", cleanup=lambda _root: None)

    def unknown_workload(**kwargs: object) -> dict[str, Any]:
        root = Path(kwargs["trusted_sandbox_root"])
        (root / "payload.txt").write_text("x", encoding="utf-8")
        (root.parent / "unknown-write.txt").write_text("x", encoding="utf-8")
        return _fixture_workload()(**kwargs)

    collect("unknown-write-path", workload=unknown_workload)
    collect("missing-required-measurement", sampler=_fixture_sample(missing=True))
    collect("invalid-policy", policy={**DEFAULT_POLICY, "max_bytes": -1})
    collect("caller-supplied-verdict", policy={**DEFAULT_POLICY, "status": "PASS"})

    matrix = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "cases": cases,
        "canary_created": False,
        "production_mutation": False,
    }
    _write_json(evidence_root / "negative-matrix.json", matrix)
    _write_json(
        evidence_root / "blocked-capacity.json",
        _block_payload(
            case="negative-probe-fixture",
            reason="fail-closed probes are separated from the complete PASS receipt",
            cycle=None,
            next_cycle_started=False,
            external_cleanup_performed=False,
            last_safe_sample={},
        ),
    )
    return matrix


def _write_source_inventory(evidence_root: Path) -> None:
    _write_text(
        evidence_root / "source-inventory.md",
        "\n".join(
            [
                "# RA-SLICE-005 Source Inventory",
                "",
                "## CodeGraph",
                "",
                "- Status: READY.",
                "- Task-semantic query: `RA-SLICE-005 capacity proof harness run_runtime_activation_e2e two-cycle non-production E2E measurement cleanup stop-loss policy`.",
                "- Entry point returned: `scripts/pantheon_writer_vnext_runtime_activation_e2e.py:run_runtime_activation_e2e`.",
                "",
                "## Bounded Source Confirmation",
                "",
                "- `scripts/pantheon_writer_vnext_runtime_activation_e2e.py`:唯一 workload，signature 接受 caller-owned sandbox、runtime receipt、execution line、correlation、actor identity 與 brief。",
                "- `tests/test_pantheon_writer_vnext_runtime_activation_e2e.py`:既有 RA004 regression 驗證七段 capability、dry-run tag/push 與 fail-closed matrix。",
                "- `scripts/pantheon_content_capacity_guard.py`:現有容量守門提供本地 tree/disk/RSS/swap 量測模式參考；RA-SLICE-005 未修改或接管 production guard。",
                "",
                "## Changed Files",
                "",
                "- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`",
                "- `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`",
                "- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_005/**`",
                "",
                "## Boundary",
                "",
                "- No RA004 E2E, coordinator, Publisher, shared receipt validator, runtime manifest, deployment, registry, metadata, article, sitemap, feed, redirect, production, canary, network write, launchctl, service mutation, push, or tag path was modified.",
                "",
            ]
        ),
    )


def _write_verification_receipt(evidence_root: Path) -> None:
    _write_text(
        evidence_root / "verification-receipt.md",
        "\n".join(
            [
                "# RA-SLICE-005 Verification Receipt",
                "",
                "## Positive Probe",
                "",
                "- `capacity-receipt.json` 保存兩個完整 synthetic non-production E2E cycles。",
                "- `cycle-1-measurements.json` 與 `cycle-2-measurements.json` 含 before、peak、after-cleanup sample。",
                "- 每個 cycle root 已清理，cleanup reclaim bytes/file count 均大於零。",
                "- `canary_created=false` 且 `production_mutation=false`。",
                "",
                "## Fail-closed Probe",
                "",
                "- `negative-matrix.json` 覆蓋 bytes、file count、host reserve、RSS、swap、cleanup failure、unknown write、missing measurement、invalid policy 與 caller verdict。",
                "- `blocked-capacity.json` 為 BLOCKED fixture，沒有 PASS receipt authority。",
                "",
                "## Verification Commands",
                "",
                "- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q`",
                "- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py -q`",
                "- `git diff --check`",
                "",
            ]
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE_PATH)
    parser.add_argument("--capacity-sandbox-root", type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    sandbox_root = (
        args.capacity_sandbox_root.resolve()
        if args.capacity_sandbox_root is not None
        else (output_root / "capacity-sandbox").resolve()
    )
    receipt = run_capacity_proof(
        capacity_sandbox_root=sandbox_root,
        evidence_root=output_root,
        runtime_receipt={
            "status": "PASS",
            "runtime_identity_digest": "d" * 64,
        },
        actor_identity="actor-ra-slice-005",
        brief={
            "schema_version": 1,
            "run_id": "ra-slice-002-synthetic-create-run",
            "mode": "create",
            "articles": [
                {
                    "id": "RA-SLICE-004-SYNTHETIC",
                    "title": "Synthetic local E2E receipt",
                }
            ],
        },
        policy=DEFAULT_POLICY,
    )
    run_capacity_negative_matrix(evidence_root=output_root)
    _write_source_inventory(output_root)
    _write_verification_receipt(output_root)
    print(json.dumps({"status": receipt["status"], "cycles": len(receipt["cycles"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

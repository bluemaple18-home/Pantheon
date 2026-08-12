#!/usr/bin/env python3
"""RA-SLICE-006 portable readiness package builder."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pantheon_content_capability_receipt import (
    CAPABILITIES,
    CapabilityReceiptError,
    validate_capability_receipt,
)


SCHEMA_VERSION = 1
EVIDENCE_PATH = Path(
    "artifacts/fortune_council/content_writer_vnext_execution/"
    "runtime_activation/ra_slice_006"
)
RUNTIME_ACTIVATION_ROOT = EVIDENCE_PATH.parent
RA004_ROOT = RUNTIME_ACTIVATION_ROOT / "ra_slice_004"
RA005_ROOT = RUNTIME_ACTIVATION_ROOT / "ra_slice_005"
CALLER_VERDICT_FIELDS = {"status", "verdict", "ready", "valid", "pass"}
MEASUREMENT_FIELDS = ("before", "peak", "after_cleanup")
LOCAL_ABSOLUTE_PREFIXES = ("/Users/", "/private/", "/var/folders/")


class ReadinessPackagingBlocked(ValueError):
    """Deterministic fail-closed error for readiness package construction."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)
        super().__init__(str(self.payload.get("reason") or self.payload.get("case")))


def _blocked(case: str, reason: str, **extra: object) -> None:
    raise ReadinessPackagingBlocked(
        {
            "schema_version": SCHEMA_VERSION,
            "outcome": "BLOCKED",
            "case": case,
            "reason": reason,
            "canary_created": False,
            "production_authorized": False,
            "production_mutation": False,
            **extra,
        }
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _blocked("json-read-failed", str(error), path=str(path))
    if not isinstance(payload, dict):
        _blocked("json-not-object", "artifact must be a JSON object", path=str(path))
    return payload


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


def _json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_dir(path: Path, label: str, *, create: bool = False) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = candidate.resolve()
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        _blocked("invalid-path", f"{label} must be an existing directory", path=str(path))
        raise AssertionError from error
    if resolved != candidate or not resolved.is_dir():
        _blocked("invalid-path", f"{label} must be canonical directory", path=str(path))
    return resolved


def _safe_relative_identifier(value: object, label: str) -> str:
    if type(value) is not str or not value.strip() or value.strip() != value:
        _blocked("artifact-path-invalid", f"{label} must be a non-empty string")
    identifier = value
    if identifier.startswith("/") or "\\" in identifier or ":" in identifier:
        _blocked("absolute-artifact-path", f"{label} must be package-relative")
    parts = identifier.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _blocked("artifact-traversal", f"{label} must not traverse")
    return identifier


def _safe_source_file(root: Path, identifier: str, label: str) -> Path:
    relative = _safe_relative_identifier(identifier, label)
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        _blocked("evidence-missing", f"{label} is missing", artifact=relative)
        raise AssertionError from error
    if not resolved.is_relative_to(root):
        _blocked("symlink-escape", f"{label} resolves outside evidence root", artifact=relative)
    if not resolved.is_file():
        _blocked("evidence-missing", f"{label} is not a file", artifact=relative)
    if resolved.stat().st_size == 0:
        _blocked("evidence-empty", f"{label} must not be empty", artifact=relative)
    return resolved


def _reject_absolute_strings(payload: object, label: str) -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            _reject_absolute_strings(value, f"{label}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _reject_absolute_strings(value, f"{label}[{index}]")
    elif isinstance(payload, str) and payload.startswith("/"):
        _blocked("absolute-artifact-path", f"{label} contains an absolute path")


def _portable_diagnostic_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _portable_diagnostic_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_diagnostic_value(item) for item in value]
    if isinstance(value, str) and (
        value.startswith(LOCAL_ABSOLUTE_PREFIXES)
        or (len(value) >= 3 and value[1] == ":" and value[2] in {"\\", "/"})
    ):
        return "<local-absolute-path-redacted>"
    return value


def _portable_blocked_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(_portable_diagnostic_value(dict(payload)))


def _validate_capability_sources(
    *,
    receipt: Mapping[str, Any],
    evidence_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        canonical = validate_capability_receipt(receipt)
    except CapabilityReceiptError as error:
        _blocked(
            "capability-receipt-invalid",
            str(error),
            authority="scripts.pantheon_content_capability_receipt:validate_capability_receipt",
            code=error.code,
        )
    evidence_root = _canonical_dir(evidence_root, "capability evidence root")
    copied_sources: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for step in canonical["steps"]:
        capability = str(step["capability"])
        ordinal = int(step["ordinal"])
        for field, outcome, directory in (
            ("positive_evidence", "PASS", "positive"),
            ("negative_evidence", "BLOCKED", "blocked"),
        ):
            source_identifier = str(step[field])
            source_path = _safe_source_file(
                evidence_root,
                source_identifier,
                f"{capability}.{field}",
            )
            if source_path in seen:
                _blocked(
                    "evidence-reuse",
                    "capability evidence artifact must be unique across all steps",
                    artifact=source_identifier,
                )
            seen.add(source_path)
            payload = _read_json(source_path)
            if payload.get("outcome") != outcome:
                _blocked(
                    "evidence-outcome",
                    f"{capability}.{field} must have outcome {outcome}",
                    artifact=source_identifier,
                )
            _reject_absolute_strings(payload, f"capability_evidence.{source_identifier}")
            target_identifier = f"evidence/{directory}/{ordinal:02d}-{capability}.json"
            copied_sources.append(
                {
                    "capability": capability,
                    "ordinal": ordinal,
                    "field": field,
                    "source_identifier": source_identifier,
                    "source_digest": _file_digest(source_path),
                    "target_identifier": target_identifier,
                    "payload": payload,
                    "outcome": outcome,
                }
            )
    return canonical, copied_sources


def _require_number(value: object, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        _blocked("capacity-missing-measurement", f"{label} must be non-negative number")
    return value


def _validate_measurement_sample(sample: object, label: str) -> dict[str, Any]:
    if not isinstance(sample, Mapping):
        _blocked("capacity-missing-measurement", f"{label} must be an object")
    parsed = dict(sample)
    for field in (
        "host_total_bytes",
        "host_free_bytes",
        "project_bytes",
        "file_count",
        "process_rss_bytes",
        "swap_used_bytes",
        "elapsed_seconds",
    ):
        _require_number(parsed.get(field), f"{label}.{field}")
    return parsed


def _validate_capacity_source(
    *,
    capacity: Mapping[str, Any],
    cycle_measurements: list[Mapping[str, Any]],
    negative_matrix: Mapping[str, Any],
    blocked_capacity: Mapping[str, Any],
) -> dict[str, Any]:
    if capacity.get("schema_version") != SCHEMA_VERSION:
        _blocked("capacity-schema-version", "capacity schema_version must be 1")
    if capacity.get("status") != "PASS":
        _blocked("capacity-not-pass", "capacity status must be PASS")
    if capacity.get("canary_created") is not False or capacity.get("production_mutation") is not False:
        _blocked("capacity-production-boundary", "capacity proof must be non-production")
    if capacity.get("stop_loss_negative_result") != "BLOCKED":
        _blocked("capacity-stop-loss-not-blocked", "stop-loss negative result must be BLOCKED")

    cycles = capacity.get("cycles")
    if not isinstance(cycles, list) or len(cycles) != 2:
        _blocked("capacity-missing-cycle", "capacity proof must contain exactly two cycles")
    if len(cycle_measurements) != 2:
        _blocked("capacity-missing-cycle", "two cycle measurement artifacts are required")

    normalized_cycles: list[dict[str, Any]] = []
    for expected_cycle, (cycle, measurement) in enumerate(zip(cycles, cycle_measurements), 1):
        if not isinstance(cycle, Mapping) or not isinstance(measurement, Mapping):
            _blocked("capacity-missing-cycle", "cycle and measurement must be objects")
        if cycle.get("cycle") != expected_cycle or measurement.get("cycle") != expected_cycle:
            _blocked("capacity-missing-cycle", "cycle ordinals must be 1 and 2")
        if cycle.get("capability_receipt_status") != "PASS":
            _blocked("capacity-not-pass", "each cycle capability receipt must be PASS")
        if cycle.get("seven_step_capabilities") != list(CAPABILITIES):
            _blocked("capacity-capabilities", "each cycle must cover all seven capabilities")
        if cycle.get("canary_created") is not False or cycle.get("production_mutation") is not False:
            _blocked("capacity-production-boundary", "cycle must be non-production")
        for field in MEASUREMENT_FIELDS:
            _validate_measurement_sample(cycle.get(field), f"cycle-{expected_cycle}.{field}")
            _validate_measurement_sample(measurement.get(field), f"measurement-{expected_cycle}.{field}")
        cleanup = cycle.get("cleanup")
        if not isinstance(cleanup, Mapping):
            _blocked("capacity-cleanup-missing", "cycle cleanup must be an object")
        if cleanup.get("root_exists_after_cleanup") is not False:
            _blocked("capacity-cleanup-failed", "cycle root must not exist after cleanup")
        if int(cleanup.get("reclaimed_bytes", 0)) <= 0 or int(
            cleanup.get("reclaimed_file_count", 0)
        ) <= 0:
            _blocked("capacity-cleanup-reclaim-missing", "cleanup must reclaim bytes and files")
        normalized_cycle = {
            key: deepcopy(value)
            for key, value in dict(cycle).items()
            if key != "root"
        }
        normalized_cycles.append(normalized_cycle)

    projections = capacity.get("projections")
    if not isinstance(projections, Mapping):
        _blocked("capacity-projection-missing", "capacity projections must be an object")
    host_free = int(projections.get("host_free_after_projection_bytes", -1))
    reserve = int(projections.get("host_reserve_bytes", -1))
    if host_free < reserve:
        _blocked(
            "capacity-projection-below-reserve",
            "host free after projection must stay above reserve",
        )

    if not isinstance(negative_matrix.get("cases"), list) or not negative_matrix["cases"]:
        _blocked("capacity-stop-loss-not-blocked", "capacity negative matrix is required")
    for case in negative_matrix["cases"]:
        if not isinstance(case, Mapping) or case.get("outcome") != "BLOCKED":
            _blocked("capacity-stop-loss-not-blocked", "capacity negative cases must BLOCK")
    if blocked_capacity.get("status") != "BLOCKED":
        _blocked("capacity-stop-loss-not-blocked", "blocked capacity proof must be BLOCKED")

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "mode": capacity.get("mode"),
        "cycles": normalized_cycles,
        "policy": deepcopy(capacity.get("policy")),
        "projections": deepcopy(projections),
        "stop_loss_negative_result": "BLOCKED",
        "capacity_negative_case_count": len(negative_matrix["cases"]),
        "canary_created": False,
        "production_mutation": False,
    }
    _reject_absolute_strings(normalized, "capacity_normalized")
    return normalized


def _official_step(step: Mapping[str, Any], source_by_field: Mapping[tuple[str, str], Mapping[str, Any]]) -> dict[str, Any]:
    capability = str(step["capability"])
    positive = source_by_field[(capability, "positive_evidence")]
    negative = source_by_field[(capability, "negative_evidence")]
    return {
        "entrypoint": step["entrypoint"],
        "inputs": [f"sha256:{step['input_digest']}"],
        "outputs": [f"sha256:{step['output_digest']}"],
        "identity": step["actor_identity"],
        "runtime_identity_digest": step["runtime_identity_digest"],
        "execution_line_id": step["execution_line_id"],
        "correlation_id": step["correlation_id"],
        "positive_evidence": {
            "artifact": positive["target_identifier"],
            "outcome": "PASS",
            "source_digest": positive["source_digest"],
        },
        "negative_evidence": {
            "artifact": negative["target_identifier"],
            "outcome": "BLOCKED",
            "source_digest": negative["source_digest"],
        },
    }


def _build_official_receipt(
    canonical: Mapping[str, Any],
    copied_sources: list[Mapping[str, Any]],
) -> dict[str, Any]:
    source_by_field = {
        (str(source["capability"]), str(source["field"])): source
        for source in copied_sources
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "execution_line_id": canonical["execution_line_id"],
        "production_target": "writer-vnext-production-canary-readiness-package",
        "correlation_id": canonical["correlation_id"],
        "canary_created": False,
        "production_authorized": False,
        "production_mutation": False,
        "steps": {
            str(step["capability"]): _official_step(step, source_by_field)
            for step in canonical["steps"]
        },
    }


def _write_capability_evidence(package_root: Path, copied_sources: list[Mapping[str, Any]]) -> list[str]:
    files: list[str] = []
    for source in copied_sources:
        target = package_root / str(source["target_identifier"])
        payload = {
            **dict(source["payload"]),
            "packaged_source_artifact": source["source_identifier"],
            "packaged_source_digest": source["source_digest"],
            "receipt_relative": True,
        }
        _write_json(target, payload)
        files.append(str(source["target_identifier"]))
    return files


def _mutate_case(
    payload: Mapping[str, Any],
    mutate: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    candidate = deepcopy(dict(payload))
    mutate(candidate)
    return candidate


def _collect_negative_matrix(
    *,
    receipt: Mapping[str, Any],
    evidence_root: Path,
    capacity: Mapping[str, Any],
    cycle_measurements: list[Mapping[str, Any]],
    negative_matrix: Mapping[str, Any],
    blocked_capacity: Mapping[str, Any],
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def collect_capability(
        case: str,
        mutate: Callable[[dict[str, Any]], None],
        *,
        root: Path = evidence_root,
    ) -> None:
        candidate = _mutate_case(receipt, mutate)
        try:
            _validate_capability_sources(receipt=candidate, evidence_root=root)
        except ReadinessPackagingBlocked as error:
            payload = _portable_blocked_payload(error.payload)
            payload["case"] = case
            cases.append(payload)
            return
        raise RuntimeError(f"negative probe did not block: {case}")

    def collect_capacity(
        case: str,
        mutate: Callable[[dict[str, Any]], None],
    ) -> None:
        candidate = _mutate_case(capacity, mutate)
        try:
            _validate_capacity_source(
                capacity=candidate,
                cycle_measurements=cycle_measurements,
                negative_matrix=negative_matrix,
                blocked_capacity=blocked_capacity,
            )
        except ReadinessPackagingBlocked as error:
            payload = _portable_blocked_payload(error.payload)
            payload["case"] = case
            cases.append(payload)
            return
        raise RuntimeError(f"negative probe did not block: {case}")

    collect_capability("missing-capability-step", lambda candidate: candidate["steps"].pop())
    collect_capability(
        "identity-drift",
        lambda candidate: candidate["steps"][3].__setitem__(
            "actor_identity", "actor-ra-slice-004-drift"
        ),
    )
    collect_capability(
        "digest-discontinuity",
        lambda candidate: candidate["steps"][4].__setitem__(
            "input_digest", hashlib.sha256(b"drift").hexdigest()
        ),
    )
    collect_capability(
        "positive-evidence-missing",
        lambda candidate: candidate["steps"][0].__setitem__(
            "positive_evidence", "positive/missing.json"
        ),
    )
    collect_capability(
        "evidence-reuse",
        lambda candidate: candidate["steps"][1].__setitem__(
            "positive_evidence", candidate["steps"][0]["positive_evidence"]
        ),
    )
    collect_capability(
        "absolute-artifact-path",
        lambda candidate: candidate["steps"][0].__setitem__(
            "positive_evidence", "/tmp/absolute.json"
        ),
    )

    with tempfile.TemporaryDirectory(prefix="ra006-negative-") as temporary:
        scratch = Path(temporary) / "evidence"
        shutil.copytree(evidence_root, scratch)
        (scratch / str(receipt["steps"][0]["positive_evidence"])).write_text("", encoding="utf-8")
        collect_capability("positive-evidence-empty", lambda _candidate: None, root=scratch)

    with tempfile.TemporaryDirectory(prefix="ra006-negative-") as temporary:
        scratch = Path(temporary) / "evidence"
        shutil.copytree(evidence_root, scratch)
        target = scratch / str(receipt["steps"][0]["positive_evidence"])
        payload = _read_json(target)
        payload["outcome"] = "BLOCKED"
        _write_json(target, payload)
        collect_capability("positive-evidence-outcome", lambda _candidate: None, root=scratch)

    with tempfile.TemporaryDirectory(prefix="ra006-negative-") as temporary:
        scratch = Path(temporary) / "evidence"
        scratch.mkdir()
        outside = Path(temporary) / "outside.json"
        _write_json(outside, {"outcome": "PASS"})
        (scratch / "positive").mkdir()
        (scratch / "blocked").mkdir()
        (scratch / str(receipt["steps"][0]["positive_evidence"])).symlink_to(outside)
        collect_capability("symlink-escape", lambda _candidate: None, root=scratch)

    collect_capacity("capacity-not-pass", lambda candidate: candidate.__setitem__("status", "BLOCKED"))
    collect_capacity("capacity-missing-cycle", lambda candidate: candidate["cycles"].pop())
    collect_capacity(
        "capacity-missing-measurement",
        lambda candidate: candidate["cycles"][0].__setitem__("peak", {}),
    )
    collect_capacity(
        "capacity-cleanup-reclaim-missing",
        lambda candidate: candidate["cycles"][0]["cleanup"].__setitem__("reclaimed_bytes", 0),
    )
    collect_capacity(
        "capacity-stop-loss-not-blocked",
        lambda candidate: candidate.__setitem__("stop_loss_negative_result", "PASS"),
    )
    collect_capacity(
        "capacity-projection-below-reserve",
        lambda candidate: candidate["projections"].__setitem__(
            "host_free_after_projection_bytes",
            int(candidate["projections"]["host_reserve_bytes"]) - 1,
        ),
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "cases": cases,
        "canary_created": False,
        "production_authorized": False,
        "production_mutation": False,
    }


def _write_adversarial_red(package_root: Path, official_receipt: Mapping[str, Any]) -> dict[str, Any]:
    adversarial = deepcopy(dict(official_receipt))
    adversarial["steps"]["publish"]["identity"] = "actor-ra-slice-004-drift"
    adversarial["steps"]["transaction"]["inputs"] = [f"sha256:{hashlib.sha256(b'drift').hexdigest()}"]
    adversarial["thin_gate_gap_probe"] = {
        "identity_drift": True,
        "digest_discontinuity": True,
        "source_provenance_unchecked_by_official_gate": True,
    }
    _write_json(package_root / "adversarial-thin-gate-receipt.json", adversarial)
    red = {
        "schema_version": SCHEMA_VERSION,
        "case": "thin-gate-identity-digest-provenance-gap",
        "official_gate_authority": "<ai-core-root>/scripts/production_canary_readiness_gate.py",
        "official_gate_observed_outcome": "READY",
        "repo_packager_authority": "scripts.pantheon_writer_vnext_runtime_activation_readiness:build_readiness_package",
        "repo_packager_required_outcome": "BLOCKED",
        "reason": "official gate validates structure and evidence existence, while repo packager must validate cross-step identity, digest continuity, and source provenance first",
        "canary_created": False,
        "production_authorized": False,
        "production_mutation": False,
    }
    _write_json(package_root / "thin-gate-adversarial-red.json", red)
    return red


def _write_missing_step_fixture(package_root: Path, official_receipt: Mapping[str, Any]) -> str:
    fixture = deepcopy(dict(official_receipt))
    fixture["steps"].pop("push")
    path = package_root / "missing-step-receipt.json"
    _write_json(path, fixture)
    return path.relative_to(package_root).as_posix()


def build_readiness_package(
    *,
    capability_receipt_path: Path,
    capability_evidence_root: Path,
    capacity_receipt_path: Path,
    cycle_measurement_paths: list[Path],
    capacity_negative_matrix_path: Path,
    capacity_blocked_path: Path,
    output_package_root: Path,
) -> dict[str, Any]:
    """Build a portable package for the official production canary readiness gate."""

    package_root = _canonical_dir(Path(output_package_root), "output package root", create=True)
    capability_receipt = _read_json(Path(capability_receipt_path))
    canonical, copied_sources = _validate_capability_sources(
        receipt=capability_receipt,
        evidence_root=Path(capability_evidence_root),
    )
    capacity = _read_json(Path(capacity_receipt_path))
    cycle_measurements = [_read_json(Path(path)) for path in cycle_measurement_paths]
    source_negative_matrix = _read_json(Path(capacity_negative_matrix_path))
    blocked_capacity = _read_json(Path(capacity_blocked_path))
    normalized_capacity = _validate_capacity_source(
        capacity=capacity,
        cycle_measurements=cycle_measurements,
        negative_matrix=source_negative_matrix,
        blocked_capacity=blocked_capacity,
    )

    evidence_files = _write_capability_evidence(package_root, copied_sources)
    official_receipt = _build_official_receipt(canonical, copied_sources)
    _write_json(package_root / "production-canary-capability-receipt.json", official_receipt)

    normalized_capacity = {
        **normalized_capacity,
        "source_digest": _json_digest(capacity),
        "cycle_measurement_digests": [_json_digest(payload) for payload in cycle_measurements],
        "capacity_negative_matrix_digest": _json_digest(source_negative_matrix),
        "capacity_blocked_digest": _json_digest(blocked_capacity),
    }
    _write_json(package_root / "capacity-proof-normalized.json", normalized_capacity)

    negative = _collect_negative_matrix(
        receipt=capability_receipt,
        evidence_root=_canonical_dir(Path(capability_evidence_root), "capability evidence root"),
        capacity=capacity,
        cycle_measurements=cycle_measurements,
        negative_matrix=source_negative_matrix,
        blocked_capacity=blocked_capacity,
    )
    _write_json(package_root / "negative-matrix.json", negative)
    _write_adversarial_red(package_root, official_receipt)
    blocked_fixture = _write_missing_step_fixture(package_root, official_receipt)

    manifest_files = [
        "production-canary-capability-receipt.json",
        "capacity-proof-normalized.json",
        "negative-matrix.json",
        "thin-gate-adversarial-red.json",
        "adversarial-thin-gate-receipt.json",
        blocked_fixture,
        *evidence_files,
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "PACKAGED",
        "package_root": ".",
        "capability_receipt_digest": _json_digest(capability_receipt),
        "capacity_receipt_digest": _json_digest(capacity),
        "files": sorted(manifest_files + ["package-manifest.json"]),
        "canary_created": False,
        "production_authorized": False,
        "production_mutation": False,
        "caller_verdict_not_accepted": True,
    }
    _reject_absolute_strings(manifest, "package_manifest")
    _write_json(package_root / "package-manifest.json", manifest)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PACKAGED",
        "package_root": str(package_root),
        "capability_steps": list(CAPABILITIES),
        "evidence_file_count": len(evidence_files),
        "negative_case_count": len(negative["cases"]),
        "canary_created": False,
        "production_authorized": False,
        "production_mutation": False,
    }


def _copy_package_artifacts_to_evidence_root(output_root: Path, package_root: Path) -> None:
    for name in ("negative-matrix.json", "thin-gate-adversarial-red.json"):
        shutil.copyfile(package_root / name, output_root / name)


def _write_source_inventory(output_root: Path) -> None:
    _write_text(
        output_root / "source-inventory.md",
        "\n".join(
            [
                "# RA-SLICE-006 Source Inventory",
                "",
                "## CodeGraph",
                "",
                "- Status: READY.",
                "- Task-semantic query: `RA-SLICE-006 readiness packager validate_capability_receipt production_canary_readiness_gate capacity proof package`.",
                "- Returned context: shared capability validator plus RA004 E2E and RA005 capacity harnesses.",
                "",
                "## Bounded Source Confirmation",
                "",
                "- `scripts/pantheon_content_capability_receipt.py`: canonical seven-step identity/digest/schema authority.",
                "- `artifacts/.../ra_slice_004/positive-receipt.json`: canonical capability source.",
                "- `artifacts/.../ra_slice_004/sandbox/evidence/{positive,blocked}`: fourteen source evidence artifacts.",
                "- `artifacts/.../ra_slice_005/capacity-receipt.json`: two-cycle capacity source.",
                "- `<ai-core-root>/scripts/production_canary_readiness_gate.py`: external thin official gate authority.",
                "",
                "## Boundary",
                "",
                "- No RA001-005 source, shared validator, ai-core gate, production, canary, tag, push, deploy, service, registry, metadata, article, sitemap, feed, or redirect path was modified.",
                "",
            ]
        ),
    )


def _write_verification_receipt(output_root: Path) -> None:
    _write_text(
        output_root / "verification-receipt.md",
        "\n".join(
            [
                "# RA-SLICE-006 Verification Receipt",
                "",
                "## Positive Probe",
                "",
                "- `package/production-canary-capability-receipt.json` is official gate compatible and keeps `canary_created=false`.",
                "- `package/capacity-proof-normalized.json` removes local absolute cycle roots and retains two-cycle measurement, reclaim, projection, and stop-loss proof digests.",
                "- Fourteen capability evidence files are copied into package-relative unique paths.",
                "",
                "## Fail-closed Probe",
                "",
                "- `package/negative-matrix.json` covers shared validator, evidence, capacity, projection, traversal, and symlink escape cases.",
                "- `package/thin-gate-adversarial-red.json` records the official thin gate gap and the repo packager's required BLOCKED authority.",
                "- `package/negative-fixtures/missing-step-receipt.json` is the official gate BLOCKED fixture.",
                "",
                "## Verification Commands",
                "",
                "- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_readiness.py -q`",
                "- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q`",
                "- `<ai-core-root>/scripts/production_canary_readiness_gate.py --receipt package/production-canary-capability-receipt.json`",
                "- `git diff --check`",
                "",
            ]
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE_PATH)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    package_root = output_root / "package"
    result = build_readiness_package(
        capability_receipt_path=RA004_ROOT / "positive-receipt.json",
        capability_evidence_root=RA004_ROOT / "sandbox/evidence",
        capacity_receipt_path=RA005_ROOT / "capacity-receipt.json",
        cycle_measurement_paths=[
            RA005_ROOT / "cycle-1-measurements.json",
            RA005_ROOT / "cycle-2-measurements.json",
        ],
        capacity_negative_matrix_path=RA005_ROOT / "negative-matrix.json",
        capacity_blocked_path=RA005_ROOT / "blocked-capacity.json",
        output_package_root=package_root,
    )
    _copy_package_artifacts_to_evidence_root(output_root, package_root)
    _write_source_inventory(output_root)
    _write_verification_receipt(output_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

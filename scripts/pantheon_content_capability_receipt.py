#!/usr/bin/env python3
"""七段 capability receipt 的純本機 fail-closed schema authority。"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


SCHEMA_VERSION = 1
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
APF_004_READINESS_ROOT = Path(
    "artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness"
)
NON_PRODUCTION_MODES = frozenset(
    {
        "synthetic-non-production",
        "formal-runtime-production-dry-run",
    }
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "execution_line_id",
        "correlation_id",
        "actor_identity",
        "runtime_identity_digest",
        "mode",
        "canary_created",
        "production_mutation",
        "steps",
    }
)
_STEP_KEYS = frozenset(
    {
        "capability",
        "ordinal",
        "entrypoint",
        "input_digest",
        "output_digest",
        "execution_line_id",
        "correlation_id",
        "actor_identity",
        "runtime_identity_digest",
        "positive_evidence",
        "negative_evidence",
        "positive_outcome",
        "negative_outcome",
    }
)
_CALLER_VERDICT_KEYS = frozenset({"status", "verdict", "ready", "valid"})
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")


class CapabilityReceiptError(ValueError):
    """穩定錯誤型別；`code` 是 caller 可比對的 fail-closed reason。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise CapabilityReceiptError(code, message)


def _reject_non_finite(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("type", "receipt contains a non-finite JSON value")
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_non_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_non_finite(nested)


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("type", f"{label} must be an object")
    if any(type(key) is not str for key in value):
        _fail("type", f"{label} keys must be strings")
    return value


def _reject_unknown_keys(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    label: str,
) -> None:
    if _CALLER_VERDICT_KEYS.intersection(value):
        _fail("caller_verdict", f"{label} contains caller-supplied verdict")
    unknown = set(value) - allowed
    if unknown:
        _fail("unknown_key", f"{label} contains unknown keys")


def _identifier(value: object, field: str) -> str:
    if type(value) is not str:
        _fail("type", f"{field} must be a string")
    if not value or value.strip() != value:
        _fail("identifier", f"{field} must be a non-blank stable identifier")
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str:
        _fail("type", f"{field} must be a digest string")
    if _DIGEST_PATTERN.fullmatch(value) is None:
        _fail("digest_format", f"{field} must be a lowercase sha256 digest")
    return value


def _evidence_identifier(value: object, field: str) -> str:
    if type(value) is not str:
        _fail("type", f"{field} must be a string")
    identifier = value
    if not identifier or identifier.strip() != identifier:
        _fail("evidence_identifier", f"{field} must be a non-blank identifier")
    if (
        identifier.startswith("/")
        or "\\" in identifier
        or "//" in identifier
        or ":" in identifier
    ):
        _fail("evidence_identifier", f"{field} must be repo-relative")
    parts = identifier.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _fail("evidence_identifier", f"{field} must not traverse directories")
    return identifier


def _validate_top_level(receipt: Mapping[str, Any]) -> dict[str, str]:
    _reject_unknown_keys(receipt, _TOP_LEVEL_KEYS, "receipt")
    schema_version = receipt.get("schema_version")
    if type(schema_version) is not int:
        _fail("type", "schema_version must be an integer")
    if schema_version != SCHEMA_VERSION:
        _fail("schema_version", "receipt schema version is unsupported")
    identities = {
        "execution_line_id": _identifier(
            receipt.get("execution_line_id"), "execution_line_id"
        ),
        "correlation_id": _identifier(receipt.get("correlation_id"), "correlation_id"),
        "actor_identity": _identifier(receipt.get("actor_identity"), "actor_identity"),
        "runtime_identity_digest": _digest(
            receipt.get("runtime_identity_digest"), "runtime_identity_digest"
        ),
    }
    mode = _identifier(receipt.get("mode"), "mode")
    if mode not in NON_PRODUCTION_MODES:
        _fail("production_boundary", "receipt mode is not an allowed boundary")
    for field in ("canary_created", "production_mutation"):
        if receipt.get(field) is not False:
            _fail("production_boundary", f"{field} must be false")
    return identities


def _validate_step(
    step: Mapping[str, Any],
    ordinal: int,
    capability: str,
    identities: dict[str, str],
) -> dict[str, str]:
    _reject_unknown_keys(step, _STEP_KEYS, f"step {ordinal}")
    if type(step.get("ordinal")) is not int:
        _fail("type", "ordinal must be an integer")
    if step.get("capability") != capability or step.get("ordinal") != ordinal:
        _fail("step_sequence", "receipt steps must match the fixed sequence")
    _identifier(step.get("entrypoint"), "entrypoint")
    for field, expected in identities.items():
        actual = (
            _digest(step.get(field), field)
            if field.endswith("_digest")
            else _identifier(step.get(field), field)
        )
        if actual != expected:
            _fail("identity_mismatch", f"{field} drifted across receipt steps")
    positive_evidence = _evidence_identifier(
        step.get("positive_evidence"), "positive_evidence"
    )
    negative_evidence = _evidence_identifier(
        step.get("negative_evidence"), "negative_evidence"
    )
    if positive_evidence == negative_evidence:
        _fail("evidence_pair", "positive and fail-closed evidence must be distinct")
    if step.get("positive_outcome") != "PASS" or step.get("negative_outcome") != "BLOCKED":
        _fail("evidence_outcome", "evidence outcomes must be PASS and BLOCKED")
    return {
        "input_digest": _digest(step.get("input_digest"), "input_digest"),
        "output_digest": _digest(step.get("output_digest"), "output_digest"),
    }


def validate_capability_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """驗證七段 receipt，回傳 canonical copy；任何缺漏都 deterministic 拒絕。"""

    root = _require_mapping(receipt, "receipt")
    _reject_non_finite(root)
    identities = _validate_top_level(root)
    steps = root.get("steps")
    if not isinstance(steps, list):
        _fail("type", "steps must be a list")
    if len(steps) != len(CAPABILITIES):
        _fail("step_sequence", "receipt must contain exactly seven steps")
    previous_output: str | None = None
    for ordinal, (capability, raw_step) in enumerate(zip(CAPABILITIES, steps), 1):
        step = _require_mapping(raw_step, f"step {ordinal}")
        digests = _validate_step(step, ordinal, capability, identities)
        if previous_output is not None and digests["input_digest"] != previous_output:
            _fail("digest_continuity", "step input digest must match previous output")
        previous_output = digests["output_digest"]
    canonical = deepcopy(dict(root))
    canonical["status"] = "PASS"
    return canonical


def _compact_json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _run_official_gate(gate_path: Path, receipt_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(gate_path), "--receipt", str(receipt_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {
            "status": "BLOCKED",
            "failures": ["official gate output was not JSON"],
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    payload["returncode"] = completed.returncode
    return payload


def _resolve_ai_core_root(explicit: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    for variable in ("AI_CORE_ROOT", "AI_CORE_HOME"):
        raw = os.environ.get(variable)
        if raw:
            candidates.append(Path(raw))
    candidates.append(Path.home() / "ai-core")
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if (resolved / "scripts/production_canary_readiness_gate.py").is_file():
            return resolved
    return None


def _apf_004_runtime_receipt() -> dict[str, str]:
    return {
        "status": "PASS",
        "runtime_identity_digest": _compact_json_digest(
            {
                "card": "APF-004-READINESS",
                "mode": "synthetic-readiness",
                "entrypoints": [
                    "scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight",
                    "scripts.agy_content_publisher:formal_capability_preflight",
                ],
            }
        ),
    }


def _apf_004_brief() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "ra-slice-002-synthetic-create-run",
        "mode": "create",
        "articles": [
            {
                "id": "APF-004-READINESS-SYNTHETIC",
                "title": "APF-004 synthetic readiness receipt",
            }
        ],
    }


def _reset_generated_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _mirror_capability_artifacts(evidence_root: Path, capability_root: Path) -> None:
    for name in (
        "positive-receipt.json",
        "blocked-receipt.json",
        "negative-matrix.json",
        "source-inventory.md",
    ):
        shutil.copy2(evidence_root / name, capability_root / name)


def _portable_artifact_value(
    value: object,
    *,
    repo_root: Path,
    output_root: Path,
) -> object:
    if isinstance(value, Mapping):
        return {
            key: _portable_artifact_value(
                item,
                repo_root=repo_root,
                output_root=output_root,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _portable_artifact_value(item, repo_root=repo_root, output_root=output_root)
            for item in value
        ]
    if not isinstance(value, str):
        return value
    normalized = value
    for root, marker in (
        (output_root, "<apf-004-readiness-root>"),
        (repo_root, "<repo-root>"),
    ):
        prefix = root.as_posix()
        if normalized == prefix:
            return marker
        if normalized.startswith(prefix + "/"):
            return marker + normalized[len(prefix) :]
    if normalized.startswith("/"):
        return "<local-absolute-path-redacted>"
    return normalized


def _normalize_portable_artifacts(output_root: Path, *, repo_root: Path) -> None:
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            _write_json(
                path,
                _portable_artifact_value(
                    payload,
                    repo_root=repo_root,
                    output_root=output_root,
                ),
            )
        elif path.suffix in {".md", ".txt"}:
            body = path.read_text(encoding="utf-8")
            body = body.replace(repo_root.as_posix(), "<repo-root>")
            body = body.replace(output_root.as_posix(), "<apf-004-readiness-root>")
            _write_text(path, body)


def build_apf_004_readiness_candidate(
    *,
    output_root: Path = APF_004_READINESS_ROOT,
    ai_core_root: Path | None = None,
) -> dict[str, Any]:
    """產出 APF-004 專屬 synthetic readiness package；不建立 canary。"""

    from scripts.pantheon_writer_vnext_runtime_activation_capacity import (
        DEFAULT_POLICY,
        run_capacity_negative_matrix,
        run_capacity_proof,
    )
    from scripts.pantheon_writer_vnext_runtime_activation_e2e import (
        run_runtime_activation_e2e,
    )
    from scripts.pantheon_writer_vnext_runtime_activation_readiness import (
        build_readiness_package,
    )

    output_root = Path(output_root)
    if not output_root.is_absolute():
        output_root = output_root.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    output_root.mkdir(parents=True, exist_ok=True)
    capability_root = output_root / "capability"
    capacity_root = output_root / "capacity"
    package_root = output_root / "package"
    _reset_generated_directory(capability_root)
    _reset_generated_directory(capacity_root)
    _reset_generated_directory(package_root)

    capability_sandbox = (capability_root / "sandbox").resolve()
    capability_sandbox.mkdir()
    runtime_receipt = _apf_004_runtime_receipt()
    capability_result = run_runtime_activation_e2e(
        trusted_sandbox_root=capability_sandbox,
        runtime_receipt=runtime_receipt,
        execution_line_id="exec-apf-004-readiness",
        correlation_id="corr-apf-004-readiness",
        actor_identity="actor-apf-004-readiness",
        brief=_apf_004_brief(),
    )
    capability_evidence_root = Path(capability_result["evidence_root"])
    _normalize_portable_artifacts(capability_root, repo_root=repo_root)
    _mirror_capability_artifacts(capability_evidence_root, capability_root)

    capacity_result = run_capacity_proof(
        capacity_sandbox_root=(capacity_root / "capacity-sandbox").resolve(),
        evidence_root=capacity_root.resolve(),
        runtime_receipt=runtime_receipt,
        actor_identity="actor-apf-004-readiness",
        brief=_apf_004_brief(),
        policy=DEFAULT_POLICY,
    )
    capacity_negative = run_capacity_negative_matrix(evidence_root=capacity_root.resolve())
    _normalize_portable_artifacts(capacity_root, repo_root=repo_root)

    package_result = build_readiness_package(
        capability_receipt_path=capability_evidence_root / "positive-receipt.json",
        capability_evidence_root=capability_evidence_root,
        capacity_receipt_path=capacity_root / "capacity-receipt.json",
        cycle_measurement_paths=[
            capacity_root / "cycle-1-measurements.json",
            capacity_root / "cycle-2-measurements.json",
        ],
        capacity_negative_matrix_path=capacity_root / "negative-matrix.json",
        capacity_blocked_path=capacity_root / "blocked-capacity.json",
        output_package_root=package_root,
    )

    resolved_ai_core_root = _resolve_ai_core_root(ai_core_root)
    if resolved_ai_core_root is None:
        ready_gate = {
            "status": "BLOCKED",
            "failures": ["official ai-core readiness gate is unavailable"],
            "returncode": 127,
        }
        blocked_gate = dict(ready_gate)
    else:
        official_gate_path = (
            resolved_ai_core_root / "scripts/production_canary_readiness_gate.py"
        )
        ready_gate = _run_official_gate(
            official_gate_path,
            package_root / "production-canary-capability-receipt.json",
        )
        blocked_gate = _run_official_gate(
            official_gate_path,
            package_root / "missing-step-receipt.json",
        )
    _write_json(output_root / "official-gate-ready.json", ready_gate)
    _write_json(output_root / "official-gate-blocked.json", blocked_gate)
    _normalize_portable_artifacts(output_root, repo_root=repo_root)

    status = (
        "READY"
        if ready_gate.get("status") == "READY"
        and blocked_gate.get("status") == "BLOCKED"
        and capacity_result.get("status") == "PASS"
        and capability_result.get("status") == "PASS"
        else "BLOCKED"
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "card_id": "APF-004-READINESS",
        "execution_line_id": "exec-apf-004-readiness",
        "correlation_id": "corr-apf-004-readiness",
        "capabilities": list(CAPABILITIES),
        "capability_status": capability_result.get("status"),
        "capacity_status": capacity_result.get("status"),
        "capacity_cycles": len(capacity_result.get("cycles", [])),
        "capacity_negative_case_count": len(capacity_negative.get("cases", [])),
        "package_status": package_result.get("status"),
        "official_gate_status": ready_gate.get("status"),
        "official_blocked_fixture_status": blocked_gate.get("status"),
        "canary_created": False,
        "production_authorized": False,
        "production_mutation": False,
        "publish": False,
        "tag": False,
        "push": False,
        "deploy": False,
        "schedule": False,
        "production_activation": False,
        "artifacts": {
            "capability_receipt": "capability/positive-receipt.json",
            "capacity_receipt": "capacity/capacity-receipt.json",
            "official_receipt": "package/production-canary-capability-receipt.json",
            "official_gate_ready": "official-gate-ready.json",
            "official_gate_blocked": "official-gate-blocked.json",
        },
        "remediation_frontier": None
        if status == "READY"
        else "repair the first BLOCKED capability/capacity/gate artifact in APF-004 readiness output before requesting canary authorization",
    }
    _write_json(output_root / "readiness-summary.json", summary)
    _write_text(
        output_root / "verification-receipt.md",
        "\n".join(
            [
                "# APF-004 Readiness Verification Receipt",
                "",
                "## Boundary",
                "",
                "- Synthetic/readiness only; `canary_created=false`.",
                "- No publish, tag, push, deploy, schedule, production activation, or production authorization was performed.",
                "",
                "## Evidence",
                "",
                "- `capability/positive-receipt.json`: seven digest-continuous capability steps.",
                "- `capacity/capacity-receipt.json`: two synthetic capacity cycles, cleanup, projection, and stop-loss proof.",
                "- `package/production-canary-capability-receipt.json`: ai-core official readiness gate input.",
                "- `official-gate-ready.json`: official gate result for the package receipt.",
                "- `official-gate-blocked.json`: fail-closed result for the missing-step fixture.",
                "",
                "## Source Confirmation",
                "",
                "- CodeGraph query: `APF-004 readiness formal capability seam: formal_capability_preflight pantheon_content_capability_receipt create run select publish transaction tag push storage capacity readiness gate`.",
                "- Reused create/run seam: `scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight`.",
                "- Reused select/publish/transaction/tag/push seam: `scripts.agy_content_publisher:formal_capability_preflight`.",
                "- Reused receipt authority: `scripts.pantheon_content_capability_receipt:validate_capability_receipt`.",
                "",
            ]
        ),
    )
    return summary


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    apf = subparsers.add_parser(
        "apf-004-readiness",
        help="build the APF-004 synthetic production-canary readiness package",
    )
    apf.add_argument("--output-root", type=Path, default=APF_004_READINESS_ROOT)
    apf.add_argument("--ai-core-root", type=Path)
    args = parser.parse_args(argv)
    if args.command == "apf-004-readiness":
        result = build_apf_004_readiness_candidate(
            output_root=args.output_root,
            ai_core_root=args.ai_core_root,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "READY" else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))

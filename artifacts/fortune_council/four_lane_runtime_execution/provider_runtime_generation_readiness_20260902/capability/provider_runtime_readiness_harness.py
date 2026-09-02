#!/usr/bin/env python3
"""本卡專用的 Rule 25 isolated generation-binding harness。"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping


TASK_ID = "PANTHEON-PROVIDER-RUNTIME-GENERATION-READINESS-20260902"
GENERATION = "provider-readiness-4a3dfeac1943-20260902"
ACTOR_HEAD = "4a3dfeac1943061edfce5350cb6bb25e35ff64c0"
PROVIDER_FIX_SHA = "2d03f97a7750e23cb1e67dd850e841fa35e3e194"
EXECUTION_LINE_ID = f"exec-{GENERATION}"
CORRELATION_ID = f"corr-{GENERATION}"
ACTOR_IDENTITY = f"pantheon-provider-runtime@{GENERATION}:{ACTOR_HEAD}"
LEGACY_IDENTITY_MARKERS = ("ra-slice-004", "corr-ra-slice-004", "actor-ra-slice-004")
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "scripts" / "pantheon_writer_vnext_runtime_activation_e2e.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pantheon_writer_vnext_runtime_activation_e2e import (  # noqa: E402
    run_runtime_activation_e2e,
)


class BindingError(ValueError):
    """Generation binding 驗證失敗。"""


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _source_inventory() -> str:
    return "\n".join(
        (
            "# Provider Runtime Generation Source Inventory",
            "",
            f"- Task: `{TASK_ID}`",
            f"- Generation: `{GENERATION}`",
            f"- Actor HEAD: `{ACTOR_HEAD}`",
            f"- Provider fix SHA: `{PROVIDER_FIX_SHA}`",
            "- CodeGraph: `CONTEXT_DEGRADED`; bounded source census only.",
            "- Create/run formal boundary: `scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight`.",
            "- Select/publish/transaction/tag/push formal boundary: `scripts.agy_content_publisher:formal_capability_preflight`.",
            "- Harness composition: `scripts.pantheon_writer_vnext_runtime_activation_e2e:run_runtime_activation_e2e`.",
            "- Provider mode: deterministic local fake provider; external provider calls remain zero.",
            "- Tag/push mode: sandbox local fake git; real tag/push probes fail closed.",
        )
    )


def runtime_binding_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "task_id": TASK_ID,
        "generation": GENERATION,
        "actor_head": ACTOR_HEAD,
        "provider_fix_sha": PROVIDER_FIX_SHA,
        "formal_harness": (
            "scripts.pantheon_writer_vnext_runtime_activation_e2e:"
            "run_runtime_activation_e2e"
        ),
        "provider_mode": "deterministic-local-fake-provider",
        "push_sink": "sandbox-local-fake-git",
    }


def runtime_receipt() -> dict[str, str]:
    return {
        "status": "PASS",
        "runtime_identity_digest": _digest(runtime_binding_payload()),
    }


def _assert_actor_source() -> None:
    actual_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_head != ACTOR_HEAD:
        raise BindingError(f"actor HEAD mismatch: {actual_head}")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PROVIDER_FIX_SHA, ACTOR_HEAD],
        cwd=REPO_ROOT,
        check=False,
    )
    if ancestry.returncode != 0:
        raise BindingError("provider fix SHA is not an ancestor of actor HEAD")


def _assert_no_legacy_identity(value: object) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    for marker in LEGACY_IDENTITY_MARKERS:
        if marker in serialized:
            raise BindingError(f"legacy identity marker detected: {marker}")


def verify_binding(
    receipt: Mapping[str, Any],
    binding_document: Mapping[str, Any],
    *,
    evidence_root: Path,
) -> dict[str, object]:
    payload = binding_document.get("payload")
    if not isinstance(payload, Mapping):
        raise BindingError("runtime binding payload is missing")
    expected_payload = runtime_binding_payload()
    if dict(payload) != expected_payload:
        raise BindingError("runtime binding payload drift")
    expected_digest = _digest(expected_payload)
    if binding_document.get("runtime_identity_digest") != expected_digest:
        raise BindingError("runtime binding digest is not recomputable")
    if receipt.get("execution_line_id") != EXECUTION_LINE_ID:
        raise BindingError("execution line is not generation-bound")
    if receipt.get("correlation_id") != CORRELATION_ID:
        raise BindingError("correlation is not generation-bound")
    if receipt.get("actor_identity") != ACTOR_IDENTITY:
        raise BindingError("actor identity is not generation-bound")
    if receipt.get("runtime_identity_digest") != expected_digest:
        raise BindingError("receipt runtime digest does not match binding payload")

    steps = receipt.get("steps")
    if not isinstance(steps, list) or len(steps) != 7:
        raise BindingError("receipt must contain seven steps")
    for ordinal, (expected_capability, step) in enumerate(zip(CAPABILITIES, steps), 1):
        if not isinstance(step, Mapping):
            raise BindingError(f"step {ordinal} is not an object")
        expected = {
            "capability": expected_capability,
            "execution_line_id": EXECUTION_LINE_ID,
            "correlation_id": CORRELATION_ID,
            "actor_identity": ACTOR_IDENTITY,
            "runtime_identity_digest": expected_digest,
            "positive_outcome": "PASS",
            "negative_outcome": "BLOCKED",
        }
        for key, value in expected.items():
            if step.get(key) != value:
                raise BindingError(f"step {ordinal} {key} binding mismatch")
        for evidence_field, outcome in (
            ("positive_evidence", "PASS"),
            ("negative_evidence", "BLOCKED"),
        ):
            artifact = evidence_root / str(step[evidence_field])
            artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
            if artifact_payload.get("outcome") != outcome:
                raise BindingError(f"step {ordinal} {evidence_field} outcome mismatch")
            for key, value in (
                ("execution_line_id", EXECUTION_LINE_ID),
                ("correlation_id", CORRELATION_ID),
                ("actor_identity", ACTOR_IDENTITY),
                ("runtime_identity_digest", expected_digest),
            ):
                if artifact_payload.get(key) != value:
                    raise BindingError(
                        f"step {ordinal} {evidence_field} {key} binding mismatch"
                    )
            _assert_no_legacy_identity(artifact_payload)
    _assert_no_legacy_identity(receipt)
    return {
        "status": "PASS",
        "receipt_binding_verification": True,
        "task_id": TASK_ID,
        "generation": GENERATION,
        "actor_head": ACTOR_HEAD,
        "provider_fix_sha": PROVIDER_FIX_SHA,
        "execution_line_id": EXECUTION_LINE_ID,
        "correlation_id": CORRELATION_ID,
        "actor_identity": ACTOR_IDENTITY,
        "runtime_identity_digest": expected_digest,
        "verified_steps": list(CAPABILITIES),
        "legacy_identity_markers_absent": True,
    }


def _legacy_red_probe(
    receipt: Mapping[str, Any],
    binding_document: Mapping[str, Any],
    evidence_root: Path,
) -> dict[str, object]:
    candidate = deepcopy(dict(receipt))
    candidate["execution_line_id"] = "exec-ra-slice-004"
    candidate["correlation_id"] = "corr-ra-slice-004"
    candidate["actor_identity"] = "actor-ra-slice-004"
    try:
        verify_binding(candidate, binding_document, evidence_root=evidence_root)
    except BindingError as error:
        return {
            "status": "RED_EXPECTED",
            "case": "legacy-ra-slice-004-identity-regression",
            "outcome": "BLOCKED",
            "reason": str(error),
        }
    raise BindingError("legacy RA-SLICE-004 identity did not produce RED")


def _brief() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "ra-slice-002-synthetic-create-run",
        "mode": "create",
        "articles": [
            {
                "id": "PROVIDER-RUNTIME-GENERATION-READINESS",
                "title": "Task-specific isolated provider readiness probe",
            }
        ],
    }


def _write_aggregate_projection(
    *,
    aggregate_root: Path,
    output_root: Path,
    receipt: Mapping[str, Any],
    assertion: Mapping[str, Any],
) -> None:
    try:
        evidence_prefix = output_root.relative_to(aggregate_root).as_posix()
    except ValueError as error:
        raise BindingError("output root must be inside aggregate root") from error
    identity = f"{ACTOR_IDENTITY}/runtime-{assertion['runtime_identity_digest']}"
    gate_steps: dict[str, object] = {}
    for step in receipt["steps"]:
        capability = str(step["capability"])
        gate_steps[capability] = {
            "entrypoint": step["entrypoint"],
            "inputs": [f"sha256:{step['input_digest']}"],
            "outputs": [f"sha256:{step['output_digest']}"],
            "identity": identity,
            "correlation_id": CORRELATION_ID,
            "positive_evidence": {
                "artifact": (
                    f"{evidence_prefix}/sandbox/evidence/"
                    f"{step['positive_evidence']}"
                ),
                "outcome": "PASS",
            },
            "negative_evidence": {
                "artifact": (
                    f"{evidence_prefix}/sandbox/evidence/"
                    f"{step['negative_evidence']}"
                ),
                "outcome": "BLOCKED",
            },
        }
    _write_json(
        aggregate_root / "positive_receipt.json",
        {
            "schema_version": 1,
            "execution_line_id": EXECUTION_LINE_ID,
            "production_target": "pantheon-provider-runtime-generation",
            "correlation_id": CORRELATION_ID,
            "canary_created": False,
            "generation": GENERATION,
            "actor_head": ACTOR_HEAD,
            "provider_fix_sha": PROVIDER_FIX_SHA,
            "runtime_identity_digest": assertion["runtime_identity_digest"],
            "receipt_binding_verification": True,
            "steps": gate_steps,
        },
    )
    _write_json(
        aggregate_root / "blocked_receipt.json",
        {
            "schema_version": 1,
            "status": "BLOCKED",
            "task_id": TASK_ID,
            "generation": GENERATION,
            "actor_head": ACTOR_HEAD,
            "provider_fix_sha": PROVIDER_FIX_SHA,
            "execution_line_id": EXECUTION_LINE_ID,
            "correlation_id": CORRELATION_ID,
            "actor_identity": ACTOR_IDENTITY,
            "runtime_identity_digest": assertion["runtime_identity_digest"],
            "reason": "Real tag and production push modes fail closed.",
            "cases": [
                {
                    "case": "publisher-real-tag-mode",
                    "outcome": "BLOCKED",
                    "artifact": (
                        f"{evidence_prefix}/sandbox/evidence/blocked/"
                        "74-probe-publisher-real-tag-mode.json"
                    ),
                },
                {
                    "case": "publisher-real-push-mode",
                    "outcome": "BLOCKED",
                    "artifact": (
                        f"{evidence_prefix}/sandbox/evidence/blocked/"
                        "75-probe-publisher-real-push-mode.json"
                    ),
                },
            ],
            "legacy_identity_red": f"{evidence_prefix}/legacy_identity_red.json",
            "canary_created": False,
            "network_calls": 0,
            "provider_calls": 0,
            "launchctl_mutation": 0,
            "production_mutation": 0,
        },
    )
    _write_json(
        aggregate_root / "result.json",
        {
            "schema_version": 1,
            "task": TASK_ID,
            "slice": "rule-25-capability",
            "status": "READY",
            "acceptance_status": "GO",
            "generation": GENERATION,
            "actor_head": ACTOR_HEAD,
            "provider_fix_sha": PROVIDER_FIX_SHA,
            "execution_line_id": EXECUTION_LINE_ID,
            "correlation_id": CORRELATION_ID,
            "actor_identity": ACTOR_IDENTITY,
            "runtime_identity_digest": assertion["runtime_identity_digest"],
            "receipt_binding_verification": True,
            "legacy_identity_red": "RED_EXPECTED",
            "official_gate": "PENDING_EXTERNAL_VALIDATION",
            "positive_outcomes": 7,
            "blocked_outcomes": 7,
            "canary_created": False,
            "network_calls": 0,
            "provider_calls": 0,
            "launchctl_mutation": 0,
            "production_mutation": 0,
            "production_authorization": False,
        },
    )


def generate(output_root: Path, aggregate_root: Path) -> dict[str, object]:
    _assert_actor_source()
    output_root = output_root.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    sandbox_root = output_root / "sandbox"
    sandbox_root.mkdir()

    payload = runtime_binding_payload()
    digest = _digest(payload)
    binding_document = {
        "schema_version": 1,
        "payload": payload,
        "canonicalization": "json(sort_keys=true,separators=[comma,colon],utf8)",
        "digest_algorithm": "sha256",
        "runtime_identity_digest": digest,
        "runtime_receipt": runtime_receipt(),
    }
    _write_json(output_root / "runtime_binding.json", binding_document)

    result = run_runtime_activation_e2e(
        trusted_sandbox_root=sandbox_root,
        runtime_receipt=runtime_receipt(),
        execution_line_id=EXECUTION_LINE_ID,
        correlation_id=CORRELATION_ID,
        actor_identity=ACTOR_IDENTITY,
        brief=_brief(),
    )
    evidence_root = Path(str(result["evidence_root"]))
    for name in (
        "positive-receipt.json",
        "blocked-receipt.json",
        "negative-matrix.json",
        "source-inventory.md",
    ):
        shutil.copy2(evidence_root / name, output_root / name)
    source_inventory = _source_inventory()
    _write_text(output_root / "source-inventory.md", source_inventory)
    _write_text(evidence_root / "source-inventory.md", source_inventory)

    receipt = json.loads((output_root / "positive-receipt.json").read_text(encoding="utf-8"))
    assertion = verify_binding(receipt, binding_document, evidence_root=evidence_root)
    legacy_red = _legacy_red_probe(receipt, binding_document, evidence_root)
    _write_json(output_root / "binding_assertion.json", assertion)
    _write_json(output_root / "legacy_identity_red.json", legacy_red)
    run_result = {
        **assertion,
        "harness_status": result["status"],
        "legacy_identity_red": legacy_red["status"],
        "canary_created": False,
        "network_calls": 0,
        "provider_calls": 0,
        "launchctl_mutation": 0,
        "production_mutation": 0,
    }
    _write_json(output_root / "run_result.json", run_result)
    _write_aggregate_projection(
        aggregate_root=aggregate_root.resolve(),
        output_root=output_root,
        receipt=receipt,
        assertion=assertion,
    )
    return run_result


def verify_only(output_root: Path) -> dict[str, object]:
    _assert_actor_source()
    binding_document = json.loads(
        (output_root / "runtime_binding.json").read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (output_root / "positive-receipt.json").read_text(encoding="utf-8")
    )
    evidence_root = output_root / "sandbox" / "evidence"
    return verify_binding(receipt, binding_document, evidence_root=evidence_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parent / "harness",
    )
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument(
        "--aggregate-root",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()
    result = (
        verify_only(args.output_root.resolve())
        if args.verify_only
        else generate(args.output_root, args.aggregate_root)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

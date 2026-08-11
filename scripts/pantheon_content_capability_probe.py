#!/usr/bin/env python3
"""以正式 production entrypoint 產生同一 correlation 的 bounded capability chain。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from scripts import pantheon_content_runtime_manifest as runtime_manifest


SCHEMA_VERSION = 2
REGRESSION_ID = "REG-PANTHEON-READINESS-CORRELATED-CHAIN-001"
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
PRODUCTION_SOURCE_FILES = (
    "scripts/agy_gemini_coordinator.py",
    "scripts/agy_gemini_runner.py",
    "scripts/agy_gemini_outbox.py",
    "scripts/agy_content_publisher.py",
    "scripts/pantheon_content_capacity_guard.py",
    "scripts/pantheon_content_runtime_manifest.py",
    "scripts/pantheon_content_actor_recovery.py",
    "scripts/pantheon_content_capability_adapter.py",
    "scripts/pantheon_content_capability_probe.py",
    "scripts/install_agy_content_publisher_launchd.sh",
    "scripts/install_agy_gemini_coordinator_launchd.sh",
    "scripts/install_pantheon_content_capacity_guard_launchd.sh",
    "ops/launchd/com.pantheon.agy-content-publisher.plist.example",
    "ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example",
    "ops/launchd/com.pantheon.agy-gemini-lane.plist.example",
    "ops/launchd/com.pantheon.content-capacity-guard.plist.example",
)
ADAPTER_MODULE = "scripts.pantheon_content_capability_adapter"


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def production_source_digest(source_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in PRODUCTION_SOURCE_FILES:
        path = source_root / relative
        if not path.is_file():
            raise ValueError(f"production source is missing: {relative}")
        body = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(body)).encode("ascii"))
        digest.update(b"\0")
        digest.update(body)
        digest.update(b"\0")
    return digest.hexdigest()


def _head_sha(source_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source_root,
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("source root HEAD is unavailable")
    return value


def run_probe(
    *,
    evidence_root: Path,
    execution_id: str,
    correlation_id: str,
    parent_sha: str | None = None,
    source_tree_digest: str | None = None,
    source_root: Path | None = None,
    fail_step: str | None = None,
    adapter_command: list[str] | None = None,
) -> dict[str, Any]:
    if fail_step is not None and fail_step not in CAPABILITIES:
        raise ValueError("fail_step is not a registered capability")
    if not execution_id or not correlation_id:
        raise ValueError("execution and correlation are required")
    resolved_source = (source_root or Path.cwd()).resolve(strict=True)
    actual_parent_sha = _head_sha(resolved_source)
    actual_source_digest = production_source_digest(resolved_source)
    if parent_sha is not None and parent_sha != actual_parent_sha:
        raise ValueError("parent SHA differs from source root HEAD")
    if source_tree_digest is not None and source_tree_digest != actual_source_digest:
        raise ValueError("source tree digest differs from production modules")
    actor_identity = f"parent:{actual_parent_sha};tree:{actual_source_digest}"
    evidence_root = evidence_root.resolve()
    evidence_root.mkdir(parents=True, exist_ok=False)
    sandbox_root = (evidence_root / "runtime").resolve()
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    log_root = sandbox_root / "logs"
    for path in (sandbox_root, queue_root, state_root, log_root):
        path.mkdir(parents=True, exist_ok=True)
    generation = "probe-" + hashlib.sha256(execution_id.encode()).hexdigest()[:24]
    manifest = runtime_manifest.build_manifest(
        actor_root=resolved_source,
        queue_root=queue_root,
        publisher_state_root=state_root,
        log_root=log_root,
        identity=actor_identity,
        runtime_digest=actual_source_digest,
        config_version="formal-runtime-v2",
        generation=generation,
    )
    manifest_path = evidence_root / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    ready_root = evidence_root / "runtime-ready"
    activation_token = evidence_root / "activation.token"
    ready_root.mkdir()
    for service_label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready_root, manifest, service_label)
    activation_receipt = runtime_manifest.activate_barrier(
        activation_token,
        ready_root,
        manifest,
    )
    command_prefix = adapter_command or [sys.executable, "-m", ADAPTER_MODULE]
    initial = {
        "schema_version": SCHEMA_VERSION,
        "capability": None,
        "execution_id": execution_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "parent_sha": actual_parent_sha,
        "source_tree_digest": actual_source_digest,
        "runtime_manifest": str(manifest_path),
        "runtime_manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "sandbox_root": str(sandbox_root),
        "activation_token": str(activation_token),
        "activation": activation_receipt,
    }
    initial["output_digest"] = _digest(initial)
    previous_digest = initial["output_digest"]
    previous_artifact = evidence_root / "00-probe-input.json"
    _write_json(previous_artifact, initial)
    steps: list[dict[str, Any]] = []
    for ordinal, capability in enumerate(CAPABILITIES, 1):
        expected_input = previous_digest
        actual_input = (
            _digest({"corrupted": expected_input}) if capability == fail_step else expected_input
        )
        adapter_receipt = evidence_root / f"{ordinal:02d}-{capability}-adapter.json"
        command = [
            *command_prefix,
            "--capability",
            capability,
            "--input",
            str(previous_artifact),
            "--output",
            str(adapter_receipt),
            "--expected-input-digest",
            expected_input,
            "--actual-input-digest",
            actual_input,
            "--execution-id",
            execution_id,
            "--correlation-id",
            correlation_id,
            "--actor-identity",
            actor_identity,
        ]
        invoked = subprocess.run(
            command,
            cwd=resolved_source,
            check=False,
            capture_output=True,
            text=True,
        )
        adapter_payload: dict[str, Any] = {}
        if adapter_receipt.is_file():
            try:
                loaded = json.loads(adapter_receipt.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    adapter_payload = loaded
            except json.JSONDecodeError:
                adapter_payload = {}
        outcome = (
            "PASS"
            if invoked.returncode == 0
            and adapter_payload.get("entrypoint_outcome") == "PASS"
            and adapter_payload.get("input_digest") == actual_input
            and bool(adapter_payload.get("output_digest"))
            and adapter_payload.get("runtime_identity_digest")
            == manifest["runtime_identity_digest"]
            else "BLOCKED"
        )
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "runtime_identity_digest": manifest["runtime_identity_digest"],
            "capability": capability,
            "ordinal": ordinal,
            "input_digest": actual_input,
            "expected_input_digest": expected_input,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "entrypoint": f"{ADAPTER_MODULE}:{capability}",
            "production_entrypoints": adapter_payload.get(
                "production_entrypoints", []
            ),
            "entrypoint_outcome": outcome,
            "mode": "formal-runtime-production-dry-run",
            "return_code": invoked.returncode,
            "adapter_invocation": {
                "boundary": f"{ADAPTER_MODULE}:{capability}",
                "command": command,
                "returncode": invoked.returncode,
                "receipt": str(adapter_receipt),
            },
        }
        if outcome == "BLOCKED":
            event["error"] = (
                str(adapter_payload.get("error"))
                or invoked.stderr.strip()
                or invoked.stdout.strip()
                or "adapter_invocation_failed"
            )
            event["output_digest"] = ""
        else:
            event["output_digest"] = str(adapter_payload["output_digest"])
            previous_digest = event["output_digest"]
            previous_artifact = adapter_receipt
        artifact = evidence_root / f"{ordinal:02d}-{capability}.json"
        _write_json(artifact, event)
        steps.append({**event, "artifact": str(artifact)})
        if outcome == "BLOCKED":
            break
    status = "BLOCKED" if steps[-1]["entrypoint_outcome"] == "BLOCKED" else "PASS"
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "status": status,
        "execution_id": execution_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "mode": "formal-runtime-production-dry-run",
        "production_mutation": False,
        "steps": steps,
    }
    _write_json(evidence_root / "receipt.json", receipt)
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--parent-sha")
    parser.add_argument("--source-tree-digest")
    parser.add_argument("--fail-step", choices=CAPABILITIES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = run_probe(
        evidence_root=args.evidence_root,
        execution_id=args.execution_id,
        correlation_id=args.correlation_id,
        source_root=args.source_root,
        parent_sha=args.parent_sha,
        source_tree_digest=args.source_tree_digest,
        fail_step=args.fail_step,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

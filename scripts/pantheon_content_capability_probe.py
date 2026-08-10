#!/usr/bin/env python3
"""產生同一 execution/correlation 的 bounded capability chain 證據。"""

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


SCHEMA_VERSION = 1
REGRESSION_ID = "REG-PANTHEON-READINESS-CORRELATED-CHAIN-001"
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
PRODUCTION_ENTRYPOINTS = {
    "create": "scripts.agy_gemini_coordinator:register/cycle",
    "run": "scripts.agy_gemini_runner:process-once",
    "select": "scripts.agy_content_publisher:exact-run-selector",
    "publish": "scripts.agy_content_publisher:publish",
    "transaction": "scripts.agy_content_publisher:transaction",
    "tag": "scripts.agy_content_publisher:tag",
    "push": "scripts.agy_content_publisher:atomic-push",
}
ADAPTER_MODULE = "scripts.pantheon_content_capability_adapter"


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def run_probe(
    *,
    evidence_root: Path,
    execution_id: str,
    correlation_id: str,
    parent_sha: str,
    source_tree_digest: str,
    fail_step: str | None = None,
    adapter_command: list[str] | None = None,
) -> dict[str, Any]:
    if fail_step is not None and fail_step not in CAPABILITIES:
        raise ValueError("fail_step is not a registered capability")
    if not execution_id or not correlation_id:
        raise ValueError("execution and correlation are required")
    if not re.fullmatch(r"[0-9a-f]{40}", parent_sha):
        raise ValueError("parent SHA must be exact")
    if not re.fullmatch(r"[0-9a-f]{64}", source_tree_digest):
        raise ValueError("source tree digest must be exact")
    actor_identity = f"parent:{parent_sha};tree:{source_tree_digest}"
    evidence_root.mkdir(parents=True, exist_ok=False)
    command_prefix = adapter_command or [sys.executable, "-m", ADAPTER_MODULE]
    previous_digest = _digest(
        {
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "kind": "probe-input",
        }
    )
    previous_artifact = evidence_root / "00-probe-input.json"
    _write_json(
        previous_artifact,
        {
            "schema_version": SCHEMA_VERSION,
            "capability": None,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "output_digest": previous_digest,
        },
    )
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
        invoked = subprocess.run(command, check=False, capture_output=True, text=True)
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
            else "BLOCKED"
        )
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "capability": capability,
            "ordinal": ordinal,
            "input_digest": actual_input,
            "expected_input_digest": expected_input,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "entrypoint": f"{ADAPTER_MODULE}:{capability}",
            "production_entrypoint": PRODUCTION_ENTRYPOINTS[capability],
            "entrypoint_outcome": outcome,
            "mode": "bounded-production-dry-run-adapter",
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
        "mode": "bounded-production-dry-run-adapter",
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
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--source-tree-digest", required=True)
    parser.add_argument("--fail-step", choices=CAPABILITIES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = run_probe(
        evidence_root=args.evidence_root,
        execution_id=args.execution_id,
        correlation_id=args.correlation_id,
        parent_sha=args.parent_sha,
        source_tree_digest=args.source_tree_digest,
        fail_step=args.fail_step,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

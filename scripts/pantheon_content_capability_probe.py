#!/usr/bin/env python3
"""產生同一 execution/correlation 的 bounded capability chain 證據。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
REGRESSION_ID = "REG-PANTHEON-READINESS-CORRELATED-CHAIN-001"
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
ENTRYPOINTS = {
    "create": "scripts.agy_gemini_coordinator:register/cycle",
    "run": "scripts.agy_gemini_runner:process-once",
    "select": "scripts.agy_content_publisher:exact-run-selector",
    "publish": "scripts.agy_content_publisher:publish",
    "transaction": "scripts.agy_content_publisher:transaction",
    "tag": "scripts.agy_content_publisher:tag",
    "push": "scripts.agy_content_publisher:atomic-push",
}


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
    actor_identity: str,
    fail_step: str | None = None,
) -> dict[str, Any]:
    if fail_step is not None and fail_step not in CAPABILITIES:
        raise ValueError("fail_step is not a registered capability")
    if not execution_id or not correlation_id or not actor_identity:
        raise ValueError("execution, correlation, and actor identity are required")
    evidence_root.mkdir(parents=True, exist_ok=False)
    previous_digest = _digest(
        {
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "kind": "probe-input",
        }
    )
    steps: list[dict[str, Any]] = []
    for ordinal, capability in enumerate(CAPABILITIES, 1):
        expected_input = previous_digest
        actual_input = (
            _digest({"corrupted": expected_input}) if capability == fail_step else expected_input
        )
        outcome = "PASS" if actual_input == expected_input else "BLOCKED"
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
            "entrypoint": ENTRYPOINTS[capability],
            "entrypoint_outcome": outcome,
            "mode": "bounded-synthetic-dry-run",
        }
        if outcome == "BLOCKED":
            event["error"] = "input_digest_mismatch"
            event["output_digest"] = ""
        else:
            event["output_digest"] = _digest(event)
            previous_digest = event["output_digest"]
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
        "mode": "bounded-synthetic-dry-run",
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
    parser.add_argument("--actor-identity", required=True)
    parser.add_argument("--fail-step", choices=CAPABILITIES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = run_probe(
        evidence_root=args.evidence_root,
        execution_id=args.execution_id,
        correlation_id=args.correlation_id,
        actor_identity=args.actor_identity,
        fail_step=args.fail_step,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

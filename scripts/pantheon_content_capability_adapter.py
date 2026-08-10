#!/usr/bin/env python3
"""執行 production capability 的 bounded、無 mutation 正式 dry-run adapter。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
PREVIOUS = dict(zip(CAPABILITIES, (None, *CAPABILITIES[:-1])))


class AdapterBlocked(ValueError):
    """正式 dry-run adapter 拒絕不連續或不完整的 handoff。"""


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _transition(capability: str, source: dict[str, Any]) -> dict[str, Any]:
    previous = PREVIOUS[capability]
    if source.get("capability") != previous:
        raise AdapterBlocked("previous capability mismatch")
    run_id = str(source.get("run_id") or "")
    if capability == "create":
        run_id = f"probe-{str(source['correlation_id'])[:24]}"
    elif not run_id:
        raise AdapterBlocked("run identity is missing")
    transitions: dict[str, Callable[[], dict[str, Any]]] = {
        "create": lambda: {"run_id": run_id, "registration": "accepted"},
        "run": lambda: {"run_id": run_id, "runner": "completed"},
        "select": lambda: {"run_id": run_id, "selector": "exact"},
        "publish": lambda: {"run_id": run_id, "publish_preview": "accepted"},
        "transaction": lambda: {"run_id": run_id, "transaction_plan": "atomic"},
        "tag": lambda: {"run_id": run_id, "tag_plan": f"probe-{run_id}"},
        "push": lambda: {"run_id": run_id, "push_plan": "HEAD:main+tag"},
    }
    return transitions[capability]()


def invoke(
    *,
    capability: str,
    input_path: Path,
    output_path: Path,
    expected_input_digest: str,
    actual_input_digest: str,
    execution_id: str,
    correlation_id: str,
    actor_identity: str,
) -> dict[str, Any]:
    if capability not in CAPABILITIES:
        raise AdapterBlocked("capability is not registered")
    source = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise AdapterBlocked("adapter input must be an object")
    if actual_input_digest != expected_input_digest:
        raise AdapterBlocked("input digest mismatch")
    if source.get("output_digest") != actual_input_digest:
        raise AdapterBlocked("input artifact digest mismatch")
    for field, value in (
        ("execution_id", execution_id),
        ("correlation_id", correlation_id),
        ("actor_identity", actor_identity),
    ):
        if source.get(field) != value:
            raise AdapterBlocked(f"{field} mismatch")
    transition = _transition(capability, source)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "capability": capability,
        "execution_id": execution_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "input_digest": actual_input_digest,
        "expected_input_digest": expected_input_digest,
        "entrypoint_outcome": "PASS",
        "mode": "bounded-production-dry-run-adapter",
        "production_mutation": False,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        **transition,
    }
    payload["output_digest"] = _digest(payload)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", choices=CAPABILITIES, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-input-digest", required=True)
    parser.add_argument("--actual-input-digest", required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--actor-identity", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = invoke(
            capability=args.capability,
            input_path=args.input,
            output_path=args.output,
            expected_input_digest=args.expected_input_digest,
            actual_input_digest=args.actual_input_digest,
            execution_id=args.execution_id,
            correlation_id=args.correlation_id,
            actor_identity=args.actor_identity,
        )
    except (AdapterBlocked, OSError, json.JSONDecodeError, KeyError) as error:
        blocked = {
            "schema_version": 1,
            "capability": args.capability,
            "execution_id": args.execution_id,
            "correlation_id": args.correlation_id,
            "actor_identity": args.actor_identity,
            "input_digest": args.actual_input_digest,
            "expected_input_digest": args.expected_input_digest,
            "entrypoint_outcome": "BLOCKED",
            "output_digest": "",
            "error": str(error),
            "mode": "bounded-production-dry-run-adapter",
            "production_mutation": False,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        }
        args.output.write_text(
            json.dumps(blocked, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(blocked, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

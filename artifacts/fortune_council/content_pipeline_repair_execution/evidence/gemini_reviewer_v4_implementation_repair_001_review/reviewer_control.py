#!/usr/bin/env python3
"""Reviewer-owned：確認非法 ledger 仍 fail closed。"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from scripts import agy_gemini_v4_broker as broker


def _event(
    binding: broker.Binding,
    sequence: int,
    parent: str | None,
    event_type: str,
    **fields: object,
) -> dict[str, object]:
    return {
        "schema_version": 2,
        "sequence": sequence,
        "parent_sha256": parent,
        "event_type": event_type,
        "operation_id": binding.operation_id,
        "item_id": binding.item_id,
        "attempt_id": binding.attempt_id,
        **fields,
    }


def _write_ledger(path: Path, binding: broker.Binding) -> str:
    definitions = [
        ("OPERATION_CREATED", {}),
        ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
        ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 123}),
        ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
    ]
    frames: list[bytes] = []
    parent = None
    for sequence, (event_type, fields) in enumerate(definitions, 1):
        encoded = broker.canonical_json(
            _event(binding, sequence, parent, event_type, **fields)
        )
        frames.append(encoded + b"\n")
        parent = hashlib.sha256(encoded).hexdigest()
    path.write_bytes(b"".join(frames))
    assert parent is not None
    return parent


def run_control() -> dict[str, object]:
    binding = broker.Binding("operation-control", "item-control", "attempt-1")
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="gemini-v4-review-control-") as raw_root:
        root = Path(raw_root)
        for case in ("schema", "order", "frame", "chain"):
            path = root / f"{case}.jsonl"
            anchor = _write_ledger(path, binding)
            lines = path.read_text(encoding="utf-8").splitlines()
            if case == "schema":
                event = json.loads(lines[0])
                event["schema_version"] = 1
                lines[0] = broker.canonical_json(event).decode()
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            elif case == "order":
                lines[3], lines[4] = lines[4], lines[3]
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            elif case == "frame":
                path.write_bytes(path.read_bytes() + b'{"schema_version":')
            elif case == "chain":
                event = json.loads(lines[1])
                event["parent_sha256"] = "0" * 64
                lines[1] = broker.canonical_json(event).decode()
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            replay = broker.replay_ledger(path, binding, anchor)
            results[case] = {
                "status": replay.status,
                "process_count": replay.process_count,
                "complete": replay.complete,
                "automatic_resend_allowed": replay.automatic_resend_allowed,
                "errors": list(replay.errors),
            }

    passed = all(
        result["status"] == "INVALID"
        and result["process_count"] == "UNKNOWN"
        and result["complete"] is False
        and result["automatic_resend_allowed"] is False
        for result in results.values()
    )
    return {
        "control": "invalid_schema_order_frame_chain_fail_closed",
        "offline_synthetic_only": True,
        "results": results,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_control()
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

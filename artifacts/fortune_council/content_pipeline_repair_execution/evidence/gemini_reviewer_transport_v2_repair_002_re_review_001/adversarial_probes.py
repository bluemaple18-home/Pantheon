#!/usr/bin/env python3
"""Repair 2 re-review：驗證後續 retry 不得跳過最新 persisted pair。"""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from scripts import agy_seo_copy_pipeline as pipeline


class Client:
    def __init__(self) -> None:
        self.calls = 0

    def generate_json(self, *_args: object) -> dict[str, object]:
        self.calls += 1
        return {"verdict": "APPROVE", "hard_failure": False, "findings": []}


def terminal(client: Client, invocation_id: str, attempt_id: str) -> dict[str, object]:
    return {
        "schema_version": 2,
        "invocation_id": invocation_id,
        "item_id": "ITEM-A",
        "attempt_id": attempt_id,
        "request_sha256": pipeline._request_sha256(client, "reviewer", "prompt", {}),
        "candidate_sha256": "2" * 64,
        "started_at": "2026-07-21T10:00:00+08:00",
        "finished_at": "2026-07-21T10:00:01+08:00",
        "exit_status": 0,
        "stdout_sha256": "3" * 64,
        "stdout_bytes": 1,
        "error_category": None,
        "terminal_status": "process_succeeded",
        "argv_sha256": "4" * 64,
    }


def failed_gate(invocation_id: str, item_id: str = "ITEM-A") -> dict[str, object]:
    return {
        "schema_version": 2,
        "invocation_id": invocation_id,
        "item_id": item_id,
        "event_type": "reviewer_strict_gate",
        "status": "failed",
        "error_category": "ValueError",
    }


def main() -> int:
    client = Client()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        base = root / "terminal-receipt.json"
        pipeline.write_json(base, terminal(client, "invocation-01", "attempt-01"))
        pipeline.write_json(
            root / "strict-gate.invocation-01.event.json",
            failed_gate("invocation-01"),
        )
        pipeline.write_json(
            root / "terminal-receipt-runtime-retry-01.json",
            terminal(client, "invocation-02", "attempt-02"),
        )
        pipeline.write_json(
            root / "strict-gate.invocation-02.event.json",
            failed_gate("invocation-02", "ITEM-B"),
        )

        pipeline._generate_with_receipt(
            client,
            "reviewer",
            "prompt",
            {},
            base,
            binding={
                "invocation_id": "invocation-03",
                "item_id": "ITEM-A",
                "attempt_id": "attempt-03",
                "candidate_sha256": "2" * 64,
            },
        )

        assert client.calls == 1
        assert (root / "terminal-receipt-runtime-retry-02.json").is_file()
        print("REPRO P1-01 latest mismatched runtime-retry pair was skipped before client call")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Transport V2 Repair 1 的獨立離線 re-review probes。"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from scripts import agy_seo_copy_pipeline as pipeline


def repro_p2_quote_does_not_bind_claim() -> None:
    judgment = {
        "verdict": "REJECT",
        "hard_failure": True,
        "findings": [
            {
                "code": "TEMPLATE_USAGE",
                "severity": "HARD",
                "message": "另一篇文章使用重複模板，本篇本身沒有問題",
                "evidence_quote": "article-01",
            }
        ],
    }
    pipeline._validate_reviewer_judgment(
        judgment,
        accepted_codes={"TEMPLATE_USAGE"},
        target_candidate_text=json.dumps(
            {"slot": "article-01", "body": "A 本文完全獨立"}, ensure_ascii=False
        ),
        candidate_sha256="a" * 64,
        expected_candidate_sha256="a" * 64,
    )
    print("REPRO P2-01 B-only claim accepted with unrelated target-local quote")


def repro_p1_02_malformed_terminal_is_ignored() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        item = root / "item-a"
        pipeline.write_json(
            item / "terminal-receipt.json",
            {
                "schema_version": 2,
                "invocation_id": "invocation-01",
                "item_id": "ITEM-A",
                "attempt_id": "attempt-01",
                "request_sha256": "1" * 64,
                "candidate_sha256": "2" * 64,
            },
        )
        replay = pipeline.replay_reviewer_receipts(
            root,
            {
                "ITEM-A": {
                    "request_sha256": "1" * 64,
                    "candidate_sha256": "2" * 64,
                    "attempt_ids": {"attempt-01"},
                }
            },
        )
        assert replay["pending"] == 1 and replay["reviewer_invocations"] == 0
    print("REPRO P1-02 malformed persisted terminal silently normalized to pending")


def repro_p1_01_mismatched_gate_authorizes_retry() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        terminal = root / "terminal-receipt.json"
        pipeline.write_json(
            terminal,
            {
                "schema_version": 2,
                "invocation_id": "old-invocation",
                "item_id": "ITEM-A",
                "attempt_id": "attempt-01",
                "request_sha256": "1" * 64,
                "candidate_sha256": "2" * 64,
                "started_at": "2026-07-21T10:00:00+08:00",
                "finished_at": "2026-07-21T10:00:01+08:00",
                "exit_status": 0,
                "stdout_sha256": "3" * 64,
                "stdout_bytes": 1,
                "error_category": None,
                "terminal_status": "process_succeeded",
                "argv_sha256": "4" * 64,
            },
        )
        pipeline.write_json(
            root / "strict-gate.old-invocation.event.json",
            {
                "schema_version": 2,
                "invocation_id": "different-invocation",
                "item_id": "ITEM-B",
                "event_type": "reviewer_strict_gate",
                "status": "failed",
                "error_category": "ValueError",
            },
        )

        class Client:
            def __init__(self) -> None:
                self.calls = 0

            def generate_json(self, *_args: object) -> dict[str, object]:
                self.calls += 1
                return {"verdict": "APPROVE", "hard_failure": False, "findings": []}

        client = Client()
        pipeline._generate_with_receipt(
            client,
            "reviewer",
            "prompt",
            {},
            terminal,
            binding={
                "invocation_id": "new-invocation",
                "item_id": "ITEM-A",
                "attempt_id": "attempt-02",
                "candidate_sha256": "2" * 64,
            },
        )
        assert client.calls == 1
        assert (root / "terminal-receipt-runtime-retry-01.json").is_file()
    print("REPRO P1-01 mismatched gate binding authorizes a fresh retry")


def repro_p1_03_not_started_counts_as_external_process() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        item = root / "item-a"
        pipeline.write_json(
            item / "terminal-receipt.json",
            {
                "schema_version": 2,
                "invocation_id": "invocation-01",
                "item_id": "ITEM-A",
                "attempt_id": "attempt-01",
                "request_sha256": "1" * 64,
                "candidate_sha256": "2" * 64,
                "started_at": "2026-07-21T10:00:00+08:00",
                "finished_at": "2026-07-21T10:00:01+08:00",
                "exit_status": None,
                "stdout_sha256": None,
                "stdout_bytes": None,
                "error_category": "CLI_NOT_FOUND",
                "terminal_status": "process_not_started",
                "argv_sha256": "4" * 64,
            },
        )
        pipeline.write_json(
            item / "strict-gate.invocation-01.event.json",
            {
                "schema_version": 2,
                "invocation_id": "invocation-01",
                "item_id": "ITEM-A",
                "event_type": "reviewer_strict_gate",
                "status": "failed",
                "error_category": "CLI_NOT_FOUND",
            },
        )
        replay = pipeline.replay_reviewer_receipts(
            root,
            {
                "ITEM-A": {
                    "request_sha256": "1" * 64,
                    "candidate_sha256": "2" * 64,
                    "attempt_ids": {"attempt-01"},
                }
            },
        )
        assert replay["external_cli_process_invocations"] == 1
    print("REPRO P1-03 process_not_started counted as an external CLI process")


def main() -> None:
    repro_p2_quote_does_not_bind_claim()
    repro_p1_02_malformed_terminal_is_ignored()
    repro_p1_01_mismatched_gate_authorizes_retry()
    repro_p1_03_not_started_counts_as_external_process()


if __name__ == "__main__":
    main()

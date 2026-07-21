#!/usr/bin/env python3
"""Transport V2 Review 的離線 adversarial probes。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from scripts import agy_gemini_transport_probe as probe
from scripts import agy_seo_copy_pipeline as pipeline


CORPUS = Path(
    "artifacts/fortune_council/content_pipeline_repair_execution/evidence/"
    "gemini_reviewer_transport_v2_implementation_001/corpus.json"
)


def binding(item_id: str, attempt: int) -> probe.InvocationContext:
    return probe.new_invocation_context(
        item_id=item_id,
        article_identity=f"identity-{item_id}",
        attempt_id=f"attempt-{attempt:02d}",
        request_bytes=f"request-{item_id}-{attempt}".encode(),
        candidate_sha256=probe.sha256_bytes(f"candidate-{item_id}".encode()),
        invocation_id=f"invocation-{item_id}-{attempt:02d}",
        started_at="2026-07-21T10:00:00+08:00",
    )


def probe_invocation_local_fingerprints() -> None:
    configuration = probe.CONFIGURATIONS[1]
    success = probe.execute_review_invocation(
        binding("public-sanitized-review-approve-001", 1),
        configuration,
        lambda: subprocess.CompletedProcess(
            [], 0, probe.compact_bytes({"verdict": "APPROVE", "hard_failure": False, "findings": []}), b""
        ),
        finished_at=lambda: "2026-07-21T10:00:01+08:00",
    )
    failures = [
        probe.execute_review_invocation(
            binding("public-sanitized-review-approve-001", 2),
            configuration,
            lambda: subprocess.CompletedProcess([], 0, b'{"response":', b""),
            outer_parser=probe.parse_strict_outer_envelope,
            finished_at=lambda: "2026-07-21T10:00:02+08:00",
        ),
        probe.execute_review_invocation(
            binding("public-sanitized-review-approve-001", 3),
            configuration,
            lambda: subprocess.CompletedProcess([], 0, b'{"verdict":', b""),
            finished_at=lambda: "2026-07-21T10:00:03+08:00",
        ),
        probe.execute_review_invocation(
            binding("public-sanitized-review-approve-001", 4),
            configuration,
            lambda: (_ for _ in ()).throw(subprocess.TimeoutExpired([], 10)),
            finished_at=lambda: "2026-07-21T10:00:04+08:00",
        ),
        probe.execute_review_invocation(
            binding("public-sanitized-review-approve-001", 5),
            configuration,
            lambda: subprocess.CompletedProcess([], 9, b"current-nonzero", b"private"),
            finished_at=lambda: "2026-07-21T10:00:05+08:00",
        ),
    ]
    assert all(outcome.receipt.stdout_sha256 != success.receipt.stdout_sha256 for outcome in failures if outcome.receipt.stdout_sha256)
    assert failures[2].receipt.stdout_sha256 is None and failures[2].receipt.stdout_bytes is None
    print("PASS invocation-local fingerprints and timeout nulls")


def probe_cross_slot_contract() -> None:
    b_only_without_identity = {
        "verdict": "REJECT",
        "hard_failure": True,
        "findings": [
            {
                "code": "TEMPLATE_USAGE",
                "severity": "HARD",
                "message": "另一篇文章使用重複模板，本篇本身沒有問題",
            }
        ],
    }
    pipeline._validate_reviewer_judgment(
        b_only_without_identity,
        accepted_codes=set(pipeline.REVIEWER_POLICY_CODES),
        forbidden_identity_tokens={"ITEM-B"},
    )
    print("REPRO cross-slot global code/message accepted for A")


def probe_retry_after_strict_failure() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        receipt = Path(temporary) / "terminal-receipt.json"
        pipeline.write_json(
            receipt,
            {
                "schema_version": 2,
                "invocation_id": "old",
                "item_id": "ITEM-A",
                "attempt_id": "attempt-01",
                "candidate_sha256": "a" * 64,
                "terminal_status": "process_succeeded",
            },
        )

        class Client:
            reviewer_model = "test-reviewer"
            transport = pipeline.GeminiClient._cli_transport

        try:
            pipeline._generate_with_receipt(
                Client(),
                "reviewer",
                "prompt",
                {},
                receipt,
                binding={
                    "invocation_id": "new",
                    "item_id": "ITEM-A",
                    "attempt_id": "attempt-02",
                    "candidate_sha256": "a" * 64,
                },
            )
        except RuntimeError as error:
            assert "not retryable" in str(error)
            print("REPRO strict/schema/rubric failed item cannot resume after process_succeeded receipt")
            return
    raise AssertionError("resume unexpectedly proceeded")


def probe_replay_fail_open() -> None:
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
                "request_sha256": "wrong-request",
                "candidate_sha256": "wrong-candidate",
                "terminal_status": "unknown-status",
            },
        )
        pipeline.write_json(
            item / "strict-gate.invocation-01.event.json",
            {
                "invocation_id": "invocation-01",
                "item_id": "ITEM-A",
                "event_type": "wrong-event-type",
                "status": "succeeded",
            },
        )
        # 先寫 gate、後寫 terminal 的順序也不會被 replay 拒絕。
        terminal = item / "terminal-receipt.json"
        terminal_payload = json.loads(terminal.read_text(encoding="utf-8"))
        terminal.unlink()
        pipeline.write_json(
            item / "strict-gate.invocation-01.duplicate.event.json",
            {
                "invocation_id": "invocation-01",
                "item_id": "ITEM-A",
                "event_type": "reviewer_strict_gate",
                "status": "failed",
            },
        )
        pipeline.write_json(terminal, terminal_payload)
        replay = pipeline.replay_reviewer_receipts(root, {"ITEM-A"})
        assert replay["succeeded"] == 1
        assert pipeline.replay_reviewer_receipts(Path(temporary) / "missing", {"ITEM-A"})["pending"] == 1

        other = root / "item-b"
        pipeline.write_json(
            other / "terminal-receipt.json",
            {
                "schema_version": 2,
                "invocation_id": "invocation-01",
                "item_id": "ITEM-B",
                "attempt_id": "attempt-01",
                "terminal_status": "process_succeeded",
            },
        )
        try:
            pipeline.replay_reviewer_receipts(root, {"ITEM-A", "ITEM-B"})
        except ValueError as error:
            assert "duplicate terminal receipt" in str(error)
        else:
            raise AssertionError("duplicate invocation ID was accepted")
    report = json.loads(CORPUS.read_text(encoding="utf-8"))
    report["runs"][0]["terminal_receipt"]["candidate_sha256"] = "0" * 64
    report["runs"][0]["terminal_receipt"]["terminal_status"] = "unknown"
    report["runs"][0]["gate_event"]["status"] = "unknown"
    assert probe.replay_stored_report(report)["decision"] == "DELIVERED_CORPUS"
    print("REPRO replay accepts malformed binding/status/event and ignores duplicate gate")


def probe_failure_position_and_resume() -> None:
    item_ids = ["A", "B", "C"]
    for failed_index in range(3):
        outcomes: list[probe.InvocationOutcome] = []
        for index, item_id in enumerate(item_ids):
            configuration = probe.Configuration(
                f"item-{item_id}",
                probe.MODEL_LABELS["pro-low"],
                probe.MINIMAL_SCHEMA,
                True,
                {"case_id": item_id, "title": "一般提醒", "answer": "先確認資訊", "policy": {}},
                "APPROVE",
                frozenset(),
            )
            completed = (
                subprocess.CompletedProcess([], 7, b"", b"private")
                if index == failed_index
                else subprocess.CompletedProcess(
                    [], 0, probe.compact_bytes({"verdict": "APPROVE", "hard_failure": False, "findings": []}), b""
                )
            )
            outcomes.append(
                probe.execute_review_invocation(
                    binding(item_id, 1),
                    configuration,
                    lambda completed=completed: completed,
                    finished_at=lambda: "2026-07-21T10:00:01+08:00",
                )
            )
        replay = probe.replay_accounting(item_ids, outcomes)
        assert (replay["succeeded"], replay["failed"], replay["pending"]) == (2, 1, 0)
        assert probe.resume_item_ids(item_ids, outcomes) == [item_ids[failed_index]]
    print("PASS isolated replay for first/middle/last failure and failed-identity-only resume")


def probe_strict_parser_matrix() -> None:
    configuration = probe.CONFIGURATIONS[1]
    invalid_payloads = [
        b'{"verdict":"APPROVE","hard_failure":false,"findings":[],"nested":{"x":1,"x":2}}',
        b'{"verdict":"APPROVE","hard_failure":false,"findings":[]} trailing',
        b'```json\n{"verdict":"APPROVE","hard_failure":false,"findings":[]}\n```',
        b'{"verdict":"APPROVE","hard_failure":false,"findings":[],"unknown":1}',
        b'{"verdict":"APPROVE","hard_failure":"false","findings":[]}',
        b'{"verdict":"APPROVE","hard_failure":true,"findings":[]}',
        b'{"verdict":"REJECT","hard_failure":false,"findings":[]}',
        b'{"verdict":"REJECT","hard_failure":true,"findings":[]}',
        b'{"verdict":"APPROVE","hard_failure":false,"findings":[{"code":"X","severity":"HARD","message":"x"}]}',
        b'{"verdict":"REJECT","hard_failure":true,"findings":[{"code":"GUARANTEE_CLAIM","severity":"HARD","message":"   "}]}',
        b'{"verdict":"REJECT","hard_failure":true,"findings":[{"code":"GUARANTEE_CLAIM","severity":"HARD","message":"x"},{"code":"GUARANTEE_CLAIM","severity":"HARD","message":"y"}]}',
    ]
    for raw in invalid_payloads:
        result = probe.evaluate_output(raw, configuration)
        assert not (result["strict_parse"] and result["schema_valid"] and result["rubric_valid"])
    print("PASS strict parser/schema/rubric contradiction matrix")


def main() -> None:
    probe_invocation_local_fingerprints()
    probe_cross_slot_contract()
    probe_retry_after_strict_failure()
    probe_replay_fail_open()
    probe_failure_position_and_resume()
    probe_strict_parser_matrix()


if __name__ == "__main__":
    main()

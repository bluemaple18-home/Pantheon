from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from scripts import agy_gemini_outbox as outbox
from scripts import agy_gemini_transport_probe as probe


def valid_minimal() -> dict[str, object]:
    return {
        "verdict": "REJECT",
        "hard_failure": True,
        "findings": [
            {
                "code": "GUARANTEE_CLAIM",
                "severity": "HARD",
                "message": "保證",
                "evidence_quote": "官方研究",
            },
            {
                "code": "UNSUPPORTED_AUTHORITY",
                "severity": "HARD",
                "message": "權威",
                "evidence_quote": "保證今天投資獲利",
            },
        ],
    }


def binding(operation_id: str) -> probe.ReviewOperationBinding:
    return probe.ReviewOperationBinding(
        operation_id=operation_id,
        item_id="item-a",
        request_id="request-a",
        run_id="run-a",
        candidate_sha256="a" * 64,
    )


def completed() -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        ["offline"], 0, stdout=probe.compact_bytes(valid_minimal()), stderr=b""
    )


def swapped_quote_probe() -> bool:
    result = probe.evaluate_output(probe.compact_bytes(valid_minimal()), probe.CONFIGURATIONS[0])
    return bool(result["rubric_valid"])


def stored_request_binding_probe(root: Path) -> bool:
    client = outbox.OutboxGeminiClient(root, namespace="review")
    prompt = "public prompt"
    schema = {"type": "object"}
    expected = outbox.build_external_request(
        namespace="review",
        role="reviewer",
        model=client.reviewer_model,
        prompt=prompt,
        response_schema=schema,
    )
    wrong = dict(expected)
    wrong["request_sha256"] = "0" * 64
    outbox.atomic_write_json(root / "outbox" / f"{expected['job_id']}.json", wrong)
    outbox.atomic_write_json(
        root / "inbox" / f"{expected['job_id']}.json",
        {
            "schema_version": outbox.SCHEMA_VERSION,
            "job_id": expected["job_id"],
            "request_sha256": expected["request_sha256"],
            "model": expected["model"],
            "completed_at": "2026-07-21T00:00:00+08:00",
            "result": {"accepted": True},
        },
    )
    return client.consume_existing_json("reviewer", prompt, schema) == {"accepted": True}


def whole_triple_replacement_probe(root: Path) -> bool:
    probe.execute_single_shot_operation(root, binding("replace"), probe.CONFIGURATIONS[0], completed)
    manifest_path, terminal_path, gate_path = probe._operation_paths(root, "replace")
    manifest = json.loads(manifest_path.read_text())
    terminal = json.loads(terminal_path.read_text())
    gate = json.loads(gate_path.read_text())
    for record in (manifest, terminal, gate):
        record["item_id"] = "replacement-item"
        record["request_id"] = "replacement-request"
        record["candidate_sha256"] = "b" * 64
    terminal["parent_sha256"] = probe._record_sha256(manifest)
    gate["parent_sha256"] = probe._record_sha256(terminal)
    manifest_path.write_bytes(probe.compact_bytes(manifest) + b"\n")
    terminal_path.write_bytes(probe.compact_bytes(terminal) + b"\n")
    gate_path.write_bytes(probe.compact_bytes(gate) + b"\n")
    replay = probe.replay_operation_records(root)
    return replay["operations"][0]["item_id"] == "replacement-item"


def concurrent_prelaunch_create_probe(root: Path) -> tuple[bool, int]:
    original = probe._write_record_exclusive
    calls = 0

    def racing_write(path: Path, record: dict[str, object]) -> None:
        original(path, record)
        if path.name.startswith("manifest."):
            terminal = path.with_name(path.name.replace("manifest.", "terminal."))
            terminal.write_bytes(b"concurrent-writer\n")

    def launcher() -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        calls += 1
        return completed()

    probe._write_record_exclusive = racing_write
    raised = False
    try:
        probe.execute_single_shot_operation(root, binding("race"), probe.CONFIGURATIONS[0], launcher)
    except FileExistsError:
        raised = True
    finally:
        probe._write_record_exclusive = original
    return raised, calls


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        race_raised, race_calls = concurrent_prelaunch_create_probe(base / "race")
        report = {
            "swapped_existing_quotes_machine_accepted": swapped_quote_probe(),
            "wrong_stored_request_binding_consumed": stored_request_binding_probe(base / "outbox"),
            "self_consistent_whole_triple_replacement_replayed": whole_triple_replacement_probe(base / "replace"),
            "concurrent_terminal_created_before_launcher_return_raised": race_raised,
            "concurrent_terminal_case_launcher_calls": race_calls,
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

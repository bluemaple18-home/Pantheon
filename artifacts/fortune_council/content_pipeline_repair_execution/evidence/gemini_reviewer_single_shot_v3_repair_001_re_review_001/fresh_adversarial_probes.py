from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from scripts import agy_gemini_operations as operations
from scripts import agy_gemini_outbox as outbox
from scripts import agy_gemini_transport_probe as probe
from scripts import agy_seo_copy_pipeline as pipeline


def _completed(value: object | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        ["offline"], 0, stdout=operations.compact_bytes(value or {"ok": True}), stderr=b""
    )


def _binding(operation_id: str) -> operations.OperationBinding:
    return operations.OperationBinding(
        operation_id=operation_id,
        item_id=f"item-{operation_id}",
        request_id=f"request-{operation_id}",
        run_id="review-run",
        candidate_sha256="a" * 64,
    )


def production_cli_missing_probe(root: Path) -> dict[str, object]:
    client = pipeline.GeminiClient()
    client.transport = client._cli_transport
    prior = os.environ.get("AGY_GEMINI_CLI")
    os.environ["AGY_GEMINI_CLI"] = str(root / "missing-cli")
    error_type = None
    try:
        pipeline._generate_with_receipt(
            client,
            "writer",
            "public prompt",
            {"type": "object"},
            root / "writer-operation.json",
        )
    except Exception as error:  # expected offline CLI-not-found path
        error_type = type(error).__name__
    finally:
        if prior is None:
            os.environ.pop("AGY_GEMINI_CLI", None)
        else:
            os.environ["AGY_GEMINI_CLI"] = prior
    terminal = json.loads(next((root / "operation-records").glob("terminal.*.json")).read_text())
    return {
        "error_type": error_type,
        "process_started": terminal["process_started"],
        "terminal_status": terminal["terminal_status"],
        "failure_code": terminal["failure_code"],
    }


def strict_outbox_probe(root: Path) -> dict[str, bool]:
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

    def rejected() -> bool:
        try:
            client.consume_existing_json("reviewer", prompt, schema)
        except ValueError:
            return True
        return False

    results = {"zero": rejected()}
    outbox.atomic_write_json(root / "outbox" / f"{expected['job_id']}.json", expected)
    outbox.atomic_write_json(root / "archive" / f"{expected['job_id']}.json", expected)
    results["duplicate"] = rejected()
    (root / "archive" / f"{expected['job_id']}.json").unlink()
    (root / "outbox" / f"{expected['job_id']}.json").write_bytes(b'{"bad":')
    results["malformed"] = rejected()
    wrong = dict(expected)
    wrong["unknown"] = True
    outbox.atomic_write_json(root / "outbox" / f"{expected['job_id']}.json", wrong)
    results["unknown"] = rejected()
    wrong = dict(expected)
    wrong["request_sha256"] = "0" * 64
    outbox.atomic_write_json(root / "outbox" / f"{expected['job_id']}.json", wrong)
    results["mismatch"] = rejected()
    results["no_new_job"] = len(list((root / "outbox").glob("*.json"))) == 1
    return results


def anchored_replay_probe(root: Path) -> dict[str, bool]:
    first = operations.execute_single_shot_operation(
        root, _binding("first"), _completed, operations.json_evaluator
    )
    second = operations.execute_single_shot_operation(
        root, _binding("second"), _completed, operations.json_evaluator
    )
    single = operations.replay_operation_records(
        root, [first.commitment], allow_other_operations=True
    )
    strict_single = single["logical_operations"] == 1 and single["operations"][0]["operation_id"] == "first"

    manifest_path, terminal_path, gate_path = operations.operation_paths(root, "first")
    records = [json.loads(path.read_text()) for path in (manifest_path, terminal_path, gate_path)]
    for record in records:
        record["item_id"] = "replacement-item"
        record["request_id"] = "replacement-request"
        record["candidate_sha256"] = "b" * 64
    records[1]["parent_sha256"] = operations.record_sha256(records[0])
    records[2]["parent_sha256"] = operations.record_sha256(records[1])
    for path, record in zip((manifest_path, terminal_path, gate_path), records, strict=True):
        path.write_bytes(operations.compact_bytes(record) + b"\n")
    rejected = False
    try:
        operations.replay_operation_records(
            root, [first.commitment], allow_other_operations=True
        )
    except ValueError:
        rejected = True
    return {
        "single_response_mode_requires_commitment": strict_single,
        "whole_triple_replacement_rejected": rejected,
        "other_operation_does_not_authorize_target": second.commitment.operation_id != first.commitment.operation_id,
    }


def namespace_race_probes(root: Path) -> dict[str, object]:
    injected_pre = b"pre-launch-writer\n"
    pre_calls = 0

    def racing_writer(path: Path, record: dict[str, object]) -> None:
        operations.write_record_exclusive(path, record)
        if path.name.startswith("manifest."):
            path.with_name(path.name.replace("manifest.", "terminal.")).write_bytes(injected_pre)

    def pre_launcher() -> subprocess.CompletedProcess[bytes]:
        nonlocal pre_calls
        pre_calls += 1
        return _completed()

    try:
        operations.execute_single_shot_operation(
            root / "pre",
            _binding("pre"),
            pre_launcher,
            operations.json_evaluator,
            record_writer=racing_writer,
        )
    except operations.DuplicateOperationError:
        pass

    during_calls = 0
    injected_during = b"during-launch-writer\n"
    during_root = root / "during"

    def during_launcher() -> subprocess.CompletedProcess[bytes]:
        nonlocal during_calls
        during_calls += 1
        terminal = operations.operation_paths(during_root, "during")[1]
        terminal.write_bytes(injected_during)
        return _completed()

    during_error = None
    try:
        operations.execute_single_shot_operation(
            during_root, _binding("during"), during_launcher, operations.json_evaluator
        )
    except Exception as error:
        during_error = type(error).__name__
    return {
        "prelaunch_calls": pre_calls,
        "prelaunch_bytes_preserved": (root / "pre" / "terminal.pre.json").read_bytes() == injected_pre,
        "during_launch_calls": during_calls,
        "during_launch_error": during_error,
        "during_launch_bytes_preserved": (during_root / "terminal.during.json").read_bytes() == injected_during,
    }


def witness_probe() -> dict[str, bool]:
    valid = {
        "verdict": "REJECT",
        "hard_failure": True,
        "findings": [
            {"code": "GUARANTEE_CLAIM", "severity": "HARD", "message": "x", "evidence_quote": "保證今天投資獲利"},
            {"code": "UNSUPPORTED_AUTHORITY", "severity": "HARD", "message": "x", "evidence_quote": "官方研究證實"},
        ],
    }
    results: dict[str, bool] = {}
    results["valid"] = bool(probe.evaluate_output(probe.compact_bytes(valid), probe.CONFIGURATIONS[0])["rubric_valid"])
    swapped = json.loads(json.dumps(valid, ensure_ascii=False))
    swapped["findings"][0]["evidence_quote"] = "官方研究證實"
    swapped["findings"][1]["evidence_quote"] = "保證今天投資獲利"
    results["swapped_rejected"] = not bool(
        probe.evaluate_output(probe.compact_bytes(swapped), probe.CONFIGURATIONS[0])["rubric_valid"]
    )
    for name, quote in {
        "generic": "今天投資",
        "synthetic": "保證不存在結果",
        "structural": "官方研究",
        "other_item": "別篇保證獲利",
    }.items():
        altered = json.loads(json.dumps(valid, ensure_ascii=False))
        altered["findings"][0]["evidence_quote"] = quote
        results[f"{name}_rejected"] = not bool(
            probe.evaluate_output(probe.compact_bytes(altered), probe.CONFIGURATIONS[0])["rubric_valid"]
        )
    return results


def resume_probe() -> dict[str, bool]:
    history = [
        {"operation_id": "approved", "item_id": "done", "status": "APPROVED", "failure_code": None},
        *[
            {"operation_id": f"blocked-{index}", "item_id": "blocked", "status": "BLOCKED", "failure_code": "CLI_TIMEOUT"}
            for index in range(1, 4)
        ],
    ]
    planned = operations.plan_resume_operations(
        ["done", "blocked"],
        history,
        run_id="next-run",
        candidate_sha256_by_item={"done": "a" * 64, "blocked": "b" * 64},
    )
    return {"approved_not_resent": not planned, "no_fourth_same_blocker": not planned}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v3-re-review-") as temp:
        root = Path(temp)
        report = {
            "production_cli_missing": production_cli_missing_probe(root / "production-missing"),
            "strict_outbox": strict_outbox_probe(root / "outbox"),
            "anchored_replay": anchored_replay_probe(root / "replay"),
            "namespace_races": namespace_race_probes(root / "races"),
            "witness": witness_probe(),
            "resume": resume_probe(),
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

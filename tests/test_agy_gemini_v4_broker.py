from __future__ import annotations

import hashlib
import json
import stat
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_v4_broker as broker


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


def _write_target(path: Path, mode: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!{sys.executable}\n"
        "import hashlib,json,os,sys,time\n"
        "from pathlib import Path\n"
        "raw=sys.stdin.buffer.read()\n"
        "fds=[]\n"
        "for fd in range(64):\n"
        "    try: os.fstat(fd)\n"
        "    except OSError: continue\n"
        "    fds.append(fd)\n"
        "trace={'argv_count':len(sys.argv),'env_keys':sorted(os.environ),"
        "'fds':fds,'stdin_sha256':hashlib.sha256(raw).hexdigest()}\n"
        "Path(__file__).with_suffix('.trace').write_text("
        "json.dumps(trace,sort_keys=True,separators=(',',':')),encoding='utf-8')\n"
        f"mode={mode!r}\n"
        "if mode=='success': print(json.dumps({'ok':True},sort_keys=True))\n"
        "elif mode=='nonzero': print('non-json-output'); sys.exit(7)\n"
        "elif mode=='timeout': time.sleep(10)\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _run(tmp_path: Path, executable: Path, *, timeout_milliseconds: int = 1500) -> broker.BrokerResult:
    raw = "公開 synthetic request".encode()
    return broker.run_single_shot(
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
        executable=executable,
        raw_request=raw,
        response_schema=SCHEMA,
        timeout_milliseconds=timeout_milliseconds,
        ledger_path=tmp_path / "ledger.jsonl",
        anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
    )


def _event(binding: broker.Binding, sequence: int, parent: str | None, event_type: str, **fields: object) -> dict[str, object]:
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


def _ledger(path: Path, binding: broker.Binding, definitions: list[tuple[str, dict[str, object]]]) -> str:
    frames = []
    parent = None
    for sequence, (event_type, fields) in enumerate(definitions, 1):
        event = _event(binding, sequence, parent, event_type, **fields)
        encoded = broker.canonical_json(event)
        frames.append(encoded + b"\n")
        parent = hashlib.sha256(encoded).hexdigest()
    path.write_bytes(b"".join(frames))
    assert parent is not None
    return parent


def test_command_frame_is_length_prefixed_versioned_and_closed() -> None:
    command = broker.CommandFrame(
        schema_version=1,
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        executable_digest="a" * 64,
        request_sha256="b" * 64,
        request_bytes_length=12,
        timeout_milliseconds=1000,
    )
    encoded = broker.encode_frame(command.to_dict())
    assert int.from_bytes(encoded[:4], "big") == len(encoded) - 4
    assert broker.decode_command_frame(encoded) == command
    payload = command.to_dict() | {"raw_prompt": "forbidden"}
    with pytest.raises(broker.FrameError):
        broker.decode_command_frame(broker.encode_frame(payload))
    with pytest.raises(broker.FrameError):
        broker.decode_command_frame(encoded[:-1])


@pytest.mark.parametrize(
    ("name", "definitions", "status", "count"),
    (
        ("preflight", [("OPERATION_CREATED", {}), ("PREFLIGHT_REJECTED", {"outcome": "CLI_NOT_FOUND"})], "COMPLETE", 0),
        ("abort", [("OPERATION_CREATED", {}), ("BROKER_ATTEMPTED", {"broker_attempt": 1}), ("BROKER_ABORTED", {"outcome": "CRASH_BEFORE_FORK"})], "BLOCKED", 0),
        ("broker-window", [("OPERATION_CREATED", {}), ("BROKER_ATTEMPTED", {"broker_attempt": 1})], "AMBIGUOUS", "UNKNOWN"),
        ("fork-window", [("OPERATION_CREATED", {}), ("BROKER_ATTEMPTED", {"broker_attempt": 1}), ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1})], "AMBIGUOUS", "UNKNOWN"),
        ("exec-failure", [("OPERATION_CREATED", {}), ("BROKER_ATTEMPTED", {"broker_attempt": 1}), ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}), ("EXEC_FAILURE", {"outcome": "EXEC_FORMAT", "process_ordinal": 1})], "BLOCKED", 0),
        ("terminal-loss", [("OPERATION_CREATED", {}), ("BROKER_ATTEMPTED", {"broker_attempt": 1}), ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}), ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 123})], "BLOCKED", 1),
        ("success", [("OPERATION_CREATED", {}), ("BROKER_ATTEMPTED", {"broker_attempt": 1}), ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}), ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 123}), ("PROCESS_TERMINAL", {"outcome": "SUCCESS"})], "COMPLETE", 1),
    ),
)
def test_replay_legal_table(tmp_path: Path, name: str, definitions: list[tuple[str, dict[str, object]]], status: str, count: int | str) -> None:
    binding = broker.Binding("operation-001", "item-001", "attempt-1")
    path = tmp_path / f"{name}.jsonl"
    anchor = _ledger(path, binding, definitions)
    result = broker.replay_ledger(path, binding, anchor)
    assert (result.status, result.process_count) == (status, count)
    assert result.complete is (status == "COMPLETE")
    assert result.automatic_resend_allowed is False


@pytest.mark.parametrize("mutation", ("legacy", "pid", "order", "binding", "chain", "partial", "anchor-missing", "anchor-mismatch"))
def test_replay_rejects_schema_fsm_frame_binding_chain_and_anchor(tmp_path: Path, mutation: str) -> None:
    binding = broker.Binding("operation-001", "item-001", "attempt-1")
    definitions = [
        ("OPERATION_CREATED", {}),
        ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
        ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 123}),
        ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
    ]
    if mutation == "legacy":
        definitions[3] = ("PROCESS_STARTED", {"process_ordinal": 1, "pid": 123})
    elif mutation == "pid":
        definitions[3] = ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": True})
    elif mutation == "order":
        definitions[3], definitions[4] = definitions[4], definitions[3]
    path = tmp_path / "ledger.jsonl"
    anchor = _ledger(path, binding, definitions)
    expected = binding
    if mutation == "binding":
        expected = broker.Binding("wrong", "item-001", "attempt-1")
    elif mutation == "chain":
        lines = path.read_text().splitlines()
        altered = json.loads(lines[1])
        altered["parent_sha256"] = "0" * 64
        lines[1] = broker.canonical_json(altered).decode()
        path.write_text("\n".join(lines) + "\n")
    elif mutation == "partial":
        path.write_bytes(path.read_bytes() + b'{"schema_version":')
    external_anchor = anchor
    if mutation == "anchor-missing":
        external_anchor = None
    elif mutation == "anchor-mismatch":
        external_anchor = "0" * 64
    result = broker.replay_ledger(path, expected, external_anchor)
    assert (result.status, result.process_count, result.complete) == ("INVALID", "UNKNOWN", False)


def test_single_shot_success_is_one_process_bound_and_private(tmp_path: Path) -> None:
    target = _write_target(tmp_path / "fake-target", "success")
    result = _run(tmp_path, target)
    trace = json.loads(target.with_suffix(".trace").read_text())
    assert (result.replay_status, result.process_count, result.outcome) == ("COMPLETE", 1, "SUCCESS")
    assert result.caller_contract_satisfied is True
    assert result.result == {"ok": True}
    mutable_copy = result.result
    assert mutable_copy is not None
    mutable_copy["ok"] = False
    assert result.result == {"ok": True}
    assert result.receipt == broker.ExecutionReceipt(
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
    )
    assert trace["fds"] == [0, 1, 2]
    assert trace["argv_count"] == 1
    assert trace["stdin_sha256"] == hashlib.sha256("公開 synthetic request".encode()).hexdigest()
    assert not any("operation-001" in key or "ledger" in key.lower() or "anchor" in key.lower() for key in trace["env_keys"])
    events = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [event["event_type"] for event in events].count("EXEC_CONFIRMED") == 1


@pytest.mark.parametrize(
    ("mode", "expected_status", "expected_count", "expected_outcome"),
    (
        ("nonzero", "COMPLETE", 1, "CLI_NONZERO"),
        ("timeout", "COMPLETE", 1, "CLI_TIMEOUT"),
    ),
)
def test_single_shot_nonzero_and_timeout_are_one_without_caller_result(tmp_path: Path, mode: str, expected_status: str, expected_count: int, expected_outcome: str) -> None:
    target = _write_target(tmp_path / "fake-target", mode)
    result = _run(tmp_path, target, timeout_milliseconds=500 if mode == "timeout" else 1500)
    assert (result.replay_status, result.process_count, result.outcome) == (expected_status, expected_count, expected_outcome)
    assert result.caller_contract_satisfied is False
    assert result.result is None
    assert target.with_suffix(".trace").exists()
    events = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [event["event_type"] for event in events].count("EXEC_CONFIRMED") == 1


def test_single_shot_preflight_and_exec_failure_never_start_target(tmp_path: Path) -> None:
    missing = _run(tmp_path / "missing", tmp_path / "does-not-exist")
    invalid = tmp_path / "invalid-executable"
    invalid.write_text("not an executable format", encoding="utf-8")
    invalid.chmod(invalid.stat().st_mode | stat.S_IXUSR)
    failed = _run(tmp_path / "exec-failure", invalid)
    assert (missing.replay_status, missing.process_count, missing.outcome) == ("COMPLETE", 0, "CLI_NOT_FOUND")
    assert (failed.replay_status, failed.process_count, failed.outcome) == ("BLOCKED", 0, "EXEC_FORMAT")
    assert missing.result is failed.result is None
    assert not (tmp_path / "missing" / "does-not-exist.trace").exists()


def test_existing_operation_never_spawns_or_repairs_anchor(tmp_path: Path) -> None:
    target = _write_target(tmp_path / "fake-target", "success")
    first = _run(tmp_path, target)
    target.with_suffix(".trace").unlink()
    second = _run(tmp_path, target)
    assert first.process_count == second.process_count == 1
    assert second.result is None
    assert second.caller_contract_satisfied is False
    assert not target.with_suffix(".trace").exists()


def test_normalized_fake_trace_is_byte_identical(tmp_path: Path) -> None:
    traces = []
    for index in range(2):
        root = tmp_path / str(index)
        target = _write_target(root / "fake-target", "success")
        result = _run(root, target)
        traces.append(broker.canonical_json(result.normalized_trace()))
    assert traces[0] == traces[1]

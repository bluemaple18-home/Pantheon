from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

from scripts import agy_gemini_v4_broker as broker
from scripts import agy_gemini_outbox as outbox


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
        f"Path({str(path.with_suffix('.trace'))!r}).write_text("
        "json.dumps(trace,sort_keys=True,separators=(',',':')),encoding='utf-8')\n"
        f"mode={mode!r}\n"
        "if mode=='success': print(json.dumps({'ok':True},sort_keys=True))\n"
        "elif mode=='nonzero': print('non-json-output'); sys.exit(7)\n"
        "elif mode=='timeout': time.sleep(10)\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _run(
    tmp_path: Path,
    executable: Path,
    *,
    timeout_milliseconds: int = 1500,
    model: str = "synthetic-model",
    raw_request: bytes = "公開 synthetic request".encode(),
    target_profile: str | None = None,
) -> broker.BrokerResult:
    selected_profile = target_profile or (
        broker.ANTIGRAVITY_CLI_PROFILE if executable.name.startswith("agy") else broker.RAW_STDIN_PROFILE
    )
    expected_digest = broker._sha256(executable.read_bytes()) if executable.exists() else broker._sha256(b"")
    return broker.run_single_shot(
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model=model,
        executable=executable,
        target_profile=selected_profile,
        expected_executable_digest=expected_digest,
        raw_request=raw_request,
        response_schema=SCHEMA,
        timeout_milliseconds=timeout_milliseconds,
        ledger_path=tmp_path / "ledger.jsonl",
        anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
    )


def _write_fake_agy(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "raw=sys.stdin.buffer.read()\n"
        "fds=[]\n"
        "for fd in range(64):\n"
        "    try: os.fstat(fd)\n"
        "    except OSError: continue\n"
        "    fds.append(fd)\n"
        "trace={'argv':sys.argv[1:],'env':dict(os.environ),'fds':fds,'stdin_bytes':len(raw)}\n"
        f"Path({str(path.with_suffix('.trace'))!r}).write_text("
        "json.dumps(trace,sort_keys=True,separators=(',',':')),encoding='utf-8')\n"
        "print(json.dumps({'ok':True},sort_keys=True))\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


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
        schema_version=2,
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        executable_digest="a" * 64,
        request_sha256="b" * 64,
        request_bytes_length=12,
        timeout_milliseconds=1000,
        target_profile=broker.RAW_STDIN_PROFILE,
        model_label="synthetic-model",
        payload_class=broker.SYNTHETIC_TEST,
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
    ("model", "label"),
    (
        ("gemini-3.5-flash", "Gemini 3.5 Flash (Low)"),
        ("gemini-3.1-pro-preview", "Gemini 3.1 Pro (Low)"),
    ),
)
def test_agy_profile_uses_closed_argv_empty_stdin_and_allowlisted_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model: str, label: str
) -> None:
    target = _write_fake_agy(tmp_path / "agy-1.1.5")
    prompt = "公開且已清理的文章審查請求"
    monkeypatch.setenv("HOME", "/synthetic-home")
    monkeypatch.setenv("PATH", "/synthetic-path")
    monkeypatch.setenv("LANG", "zh_TW.UTF-8")
    monkeypatch.setenv("GEMINI_API_KEY", "must-not-cross-boundary")
    monkeypatch.setenv("UNRELATED_SENTINEL", "must-not-cross-boundary")

    result = _run(tmp_path, target, model=model, raw_request=prompt.encode())

    trace = json.loads(target.with_suffix(".trace").read_text())
    assert (result.replay_status, result.process_count, result.outcome) == ("COMPLETE", 1, "SUCCESS")
    assert trace["argv"][:6] == ["--model", label, "--mode", "plan", "--sandbox", "--log-file"]
    assert trace["argv"][-4:-2] == ["--print-timeout", "2s"]
    assert trace["argv"][-2:] == ["--print", prompt]
    assert trace["stdin_bytes"] == 0
    assert trace["fds"] == [0, 1, 2]
    assert set(trace["env"]) <= {
        "HOME", "LANG", "LC_ALL", "PATH", "TMPDIR", "__CF_USER_TEXT_ENCODING"
    }
    assert trace["env"]["HOME"] == "/synthetic-home"
    assert "GEMINI_API_KEY" not in trace["env"]
    assert "UNRELATED_SENTINEL" not in trace["env"]


@pytest.mark.parametrize(
    ("model", "prompt"),
    (
        ("unknown-model", "公開且已清理的請求"),
        ("gemini-3.5-flash", "/Users/example/private-draft.md"),
        ("gemini-3.5-flash", "GEMINI_API_KEY=forbidden"),
    ),
)
def test_agy_profile_rejects_unapproved_binding_before_creating_ledger(
    tmp_path: Path, model: str, prompt: str
) -> None:
    target = _write_fake_agy(tmp_path / "agy-1.1.5")

    with pytest.raises(ValueError):
        _run(tmp_path, target, model=model, raw_request=prompt.encode())

    assert not (tmp_path / "ledger.jsonl").exists()
    assert not target.with_suffix(".trace").exists()


def test_agy_profile_privacy_patterns_and_size_match_outbox_contract(tmp_path: Path) -> None:
    target = _write_fake_agy(tmp_path / "agy-1.1.5")
    assert tuple((item.pattern, item.flags) for item in broker.FORBIDDEN_PUBLIC_PROMPT_PATTERNS) == tuple(
        (item.pattern, item.flags) for item in outbox.FORBIDDEN_EXTERNAL_PATTERNS
    )
    assert broker.MAX_AGY_PROMPT_BYTES == outbox.MAX_PROMPT_BYTES

    for prompt in (b"", b"x" * (outbox.MAX_PROMPT_BYTES + 1)):
        with pytest.raises(ValueError):
            _run(tmp_path, target, model="gemini-3.5-flash", raw_request=prompt)

    assert not (tmp_path / "ledger.jsonl").exists()
    assert not target.with_suffix(".trace").exists()


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
        target_profile=broker.RAW_STDIN_PROFILE,
        executable_digest=broker._sha256(target.read_bytes()),
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


def test_single_shot_supervisor_launch_race_still_executes_verified_snapshot(tmp_path: Path) -> None:
    target = _write_target(tmp_path / "fake-target", "success")
    real_popen = subprocess.Popen
    broker_launches = 0

    def mutate_before_broker_exec(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
        nonlocal broker_launches
        broker_launches += 1
        if broker_launches == 1:
            _write_target(target, "nonzero")
        return real_popen(*args, **kwargs)

    with mock.patch.object(broker.subprocess, "Popen", side_effect=mutate_before_broker_exec):
        result = _run(tmp_path, target)

    events = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [event["event_type"] for event in events] == [
        "OPERATION_CREATED",
        "BROKER_ATTEMPTED",
        "FORK_ATTEMPTED",
        "EXEC_CONFIRMED",
        "PROCESS_TERMINAL",
    ]
    assert events[-1]["outcome"] == "SUCCESS"
    assert (result.replay_status, result.process_count) == ("COMPLETE", 1)
    assert result.caller_contract_satisfied is True
    assert result.result == {"ok": True}
    assert result.automatic_resend_allowed is False
    assert target.with_suffix(".trace").exists()


def test_single_shot_executes_verified_snapshot_when_source_path_changes_after_verification(
    tmp_path: Path,
) -> None:
    target = _write_target(tmp_path / "fake-target", "success")
    replacement = _write_target(tmp_path / "replacement", "nonzero")
    expected_digest = broker._sha256(target.read_bytes())
    backing_store = broker.FileAnchorStore(tmp_path / "anchors")

    class SwapAfterVerificationStore:
        def __init__(self) -> None:
            self.cas_count = 0

        def load(self, operation_id: str, attempt_id: str) -> str | None:
            return backing_store.load(operation_id, attempt_id)

        def compare_and_swap(
            self, operation_id: str, attempt_id: str, previous_anchor: str | None, next_anchor: str
        ) -> bool:
            self.cas_count += 1
            if self.cas_count == 3:
                replacement.replace(target)
            return backing_store.compare_and_swap(operation_id, attempt_id, previous_anchor, next_anchor)

    result = broker.run_single_shot(
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
        executable=target,
        target_profile=broker.RAW_STDIN_PROFILE,
        expected_executable_digest=expected_digest,
        raw_request=b"public synthetic request",
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=tmp_path / "ledger.jsonl",
        anchor_store=SwapAfterVerificationStore(),
    )

    assert (result.replay_status, result.outcome, result.result) == ("COMPLETE", "SUCCESS", {"ok": True})


def test_existing_operation_never_spawns_or_repairs_anchor(tmp_path: Path) -> None:
    target = _write_target(tmp_path / "fake-target", "success")
    first = _run(tmp_path, target)
    target.with_suffix(".trace").unlink()
    second = _run(tmp_path, target)
    assert first.process_count == second.process_count == 1
    assert second.result is None
    assert second.caller_contract_satisfied is False
    assert not target.with_suffix(".trace").exists()


def test_post_fork_anchor_failure_kills_and_reaps_target(tmp_path: Path) -> None:
    target = tmp_path / "agy-current"
    pid_path = tmp_path / "target.pid"
    target.write_text(
        f"#!{sys.executable}\n"
        "import os,sys,time\n"
        "from pathlib import Path\n"
        "log_path=Path(sys.argv[sys.argv.index('--log-file') + 1])\n"
        f"Path({str(pid_path)!r}).write_text(str(os.getpid()) + '\\n' + str(log_path.parent), encoding='utf-8')\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    expected_digest = broker._sha256(target.read_bytes())
    backing_store = broker.FileAnchorStore(tmp_path / "anchors")

    class RejectExecConfirmedStore:
        def __init__(self) -> None:
            self.cas_count = 0

        def load(self, operation_id: str, attempt_id: str) -> str | None:
            return backing_store.load(operation_id, attempt_id)

        def compare_and_swap(
            self, operation_id: str, attempt_id: str, previous_anchor: str | None, next_anchor: str
        ) -> bool:
            self.cas_count += 1
            if self.cas_count == 4:
                deadline = time.monotonic() + 2
                while not pid_path.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                return False
            return backing_store.compare_and_swap(operation_id, attempt_id, previous_anchor, next_anchor)

    result = broker.run_single_shot(
        operation_id="operation-001",
        item_id="item-001",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="gemini-3.5-flash",
        executable=target,
        target_profile=broker.ANTIGRAVITY_CLI_PROFILE,
        expected_executable_digest=expected_digest,
        raw_request="公開且已清理的請求".encode(),
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=tmp_path / "ledger.jsonl",
        anchor_store=RejectExecConfirmedStore(),
    )

    assert result.caller_contract_satisfied is False
    assert result.automatic_resend_allowed is False
    pid_text, temporary_path = pid_path.read_text(encoding="utf-8").splitlines()
    pid = int(pid_text)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert not Path(temporary_path).exists()


@pytest.mark.parametrize(
    ("target_profile", "expected_digest"),
    (("unknown-profile", "valid"), (broker.RAW_STDIN_PROFILE, "mismatch")),
)
def test_single_shot_rejects_unknown_profile_or_untrusted_executable_before_ledger(
    tmp_path: Path, target_profile: str, expected_digest: str
) -> None:
    target = _write_target(tmp_path / "fake-target", "success")
    digest = broker._sha256(target.read_bytes()) if expected_digest == "valid" else "0" * 64

    with pytest.raises(ValueError):
        broker.run_single_shot(
            operation_id="operation-001",
            item_id="item-001",
            attempt_id="attempt-1",
            request_sha256="a" * 64,
            model="synthetic-model",
            executable=target,
            target_profile=target_profile,
            expected_executable_digest=digest,
            raw_request=b"public synthetic request",
            response_schema=SCHEMA,
            timeout_milliseconds=1500,
            ledger_path=tmp_path / "ledger.jsonl",
            anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
        )

    assert not (tmp_path / "ledger.jsonl").exists()
    assert not target.with_suffix(".trace").exists()


def test_normalized_fake_trace_is_byte_identical(tmp_path: Path) -> None:
    traces = []
    target = _write_target(tmp_path / "fake-target", "success")
    for index in range(2):
        root = tmp_path / str(index)
        result = _run(root, target)
        traces.append(broker.canonical_json(result.normalized_trace()))
    assert traces[0] == traces[1]

from __future__ import annotations

import hashlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest
import scripts.agy_gemini_outbox as outbox
import scripts.agy_gemini_runner as runner
from scripts import agy_gemini_v4_broker as broker
from scripts.agy_gemini_v4_broker import BrokerResult, ExecutionReceipt

from scripts.agy_gemini_outbox import (
    ExternalJobPending,
    OutboxGeminiClient,
    consume_external_response,
    create_external_request,
    run_pipeline_tick,
)
from scripts.agy_gemini_runner import process_once


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


def _broker_result(
    status: str,
    receipt: ExecutionReceipt,
    *,
    result: dict[str, object] | None = None,
) -> BrokerResult:
    success = status == "COMPLETE" and result is not None
    count: int | str = 1 if status in {"COMPLETE", "BLOCKED"} else "UNKNOWN"
    return BrokerResult(
        replay_status=status,
        process_count=count,
        outcome="SUCCESS" if success else None,
        exit_status=0 if success else None,
        stdout_sha256="a" * 64 if success else None,
        stderr_sha256="b" * 64 if success else None,
        byte_count=1 if success else 0,
        final_anchor="c" * 64 if success else None,
        receipt=receipt,
        caller_contract_satisfied=success,
        result_json=json.dumps(result, sort_keys=True, separators=(",", ":")).encode() if result is not None else None,
        errors=() if success else ("SYNTHETIC_FAILURE",),
    )


def test_runner_module_entrypoint_and_launchd_template_are_runnable(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_runner",
            "--queue-root",
            str(tmp_path),
            "process-once",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    plist = plistlib.loads(
        (repo_root / "ops/launchd/com.pantheon.agy-gemini-runner.plist.example").read_bytes()
    )
    arguments = plist["ProgramArguments"]

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {"status": "idle"}
    assert arguments[1:3] == ["-m", "scripts.agy_gemini_runner"]
    assert not any(argument.endswith("agy_gemini_runner.py") for argument in arguments)


def test_outbox_request_is_sanitized_hashed_and_idempotent(tmp_path: Path) -> None:
    first = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="只根據公開 brief 產生 JSON。",
        response_schema=SCHEMA,
    )
    second = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="只根據公開 brief 產生 JSON。",
        response_schema=SCHEMA,
    )

    assert first == second
    assert len(first["job_id"]) == 40
    assert len(first["request_sha256"]) == 64
    assert first["thinking_level"] == "LOW"
    assert first["operation_level"] == "external_generation"
    assert json.loads((tmp_path / "outbox" / f"{first['job_id']}.json").read_text()) == first


@pytest.mark.parametrize(
    "private_value",
    [
        "/Users/example/private/article.md",
        ".work/gsc-copy/private/brief.json",
        "GEMINI_API_KEY=secret",
        "AIza" + "x" * 32,
        "-----BEGIN PRIVATE KEY-----",
    ],
)
def test_outbox_rejects_private_paths_and_credentials(tmp_path: Path, private_value: str) -> None:
    with pytest.raises(ValueError, match="external payload contains forbidden private data"):
        create_external_request(
            tmp_path,
            namespace="opaque-run-01",
            role="writer",
            model="gemini-test-writer",
            prompt=f"公開說明：{private_value}",
            response_schema=SCHEMA,
        )


def test_outbox_client_returns_pending_then_consumes_bound_response(tmp_path: Path) -> None:
    client = OutboxGeminiClient(
        tmp_path,
        namespace="opaque-run-01",
        writer_model="gemini-test-writer",
        reviewer_model="gemini-test-reviewer",
    )

    with pytest.raises(ExternalJobPending) as pending:
        client.generate_json("writer", "公開 prompt", SCHEMA)

    request = json.loads((tmp_path / "outbox" / f"{pending.value.job_id}.json").read_text())
    response = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": request["model"],
        "completed_at": "2026-07-18T12:00:00+08:00",
        "result": {"ok": True},
    }
    inbox = tmp_path / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir(parents=True)
    inbox.write_text(json.dumps(response), encoding="utf-8")

    assert client.generate_json("writer", "公開 prompt", SCHEMA) == {"ok": True}


def test_response_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    inbox = tmp_path / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir(parents=True)
    inbox.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "job_id": request["job_id"],
                "request_sha256": "0" * 64,
                "model": request["model"],
                "completed_at": "2026-07-18T12:00:00+08:00",
                "result": {"ok": True},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="response request hash mismatch"):
        consume_external_response(tmp_path, request)


def test_runner_processes_one_job_and_archives_request(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="審查公開 candidate",
        response_schema=SCHEMA,
    )
    calls: list[tuple[str, str]] = []

    def generate(role: str, model: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
        calls.append((role, model))
        assert prompt == "審查公開 candidate"
        assert schema == SCHEMA
        return {"ok": True}

    result = process_once(tmp_path, generate_json=generate)

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert calls == [("reviewer", "gemini-test-reviewer")]
    assert not (tmp_path / "outbox" / f"{request['job_id']}.json").exists()
    assert (tmp_path / "archive" / f"{request['job_id']}.json").exists()
    response = json.loads((tmp_path / "inbox" / f"{request['job_id']}.json").read_text())
    assert response["request_sha256"] == request["request_sha256"]
    assert response["result"] == {"ok": True}


def test_runner_flag_off_preserves_single_legacy_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-legacy",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 legacy prompt",
        response_schema=SCHEMA,
    )
    calls: list[str] = []

    def generate(_role: str, _model: str, prompt: str, _schema: dict[str, object]) -> dict[str, object]:
        calls.append(prompt)
        return {"ok": True}

    assert process_once(tmp_path, generate_json=generate)["status"] == "processed"
    assert calls == ["公開 legacy prompt"]
    assert json.loads((tmp_path / "inbox" / f"{request['job_id']}.json").read_text())["result"] == {"ok": True}


@pytest.mark.parametrize(
    ("role", "expected_role_instruction", "forbidden_role_instruction"),
    (
        (
            "writer",
            "你是 Pantheon 繁體中文文章 Writer。只輸出符合 schema 的 JSON，不得加入未提供的事實或承諾。",
            "你是獨立 Pantheon 文章 Reviewer。",
        ),
        (
            "reviewer",
            "你是獨立 Pantheon 文章 Reviewer。依規範嚴格審查，只輸出符合 schema 的 JSON；不得假設 Writer 對話內容。",
            "你是 Pantheon 繁體中文文章 Writer。",
        ),
    ),
)
def test_runner_flag_on_uses_only_broker_and_writes_bound_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    expected_role_instruction: str,
    forbidden_role_instruction: str,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", hashlib.sha256(executable.read_bytes()).hexdigest())
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-v4",
        role=role,
        model=f"gemini-test-{role}",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    legacy_calls: list[str] = []
    broker_calls: list[dict[str, object]] = []

    def fake_broker(**kwargs: object) -> BrokerResult:
        broker_calls.append(kwargs)
        return _broker_result(
            "COMPLETE",
            ExecutionReceipt(
                operation_id=request["job_id"],
                item_id=request["namespace"],
                attempt_id="attempt-1",
                request_sha256=request["request_sha256"],
                model=request["model"],
                target_profile="antigravity_cli_v1",
                executable_digest=hashlib.sha256(executable.read_bytes()).hexdigest(),
            ),
            result={"ok": True},
        )

    monkeypatch.setattr(runner, "run_single_shot", fake_broker)
    result = process_once(tmp_path, generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": False})
    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert legacy_calls == []
    assert len(broker_calls) == 1
    effective_prompt = broker_calls[0]["raw_request"].decode()
    canonical_schema = json.dumps(
        SCHEMA,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    expected_effective_prompt = (
        f"{expected_role_instruction}\n"
        "禁止使用任何工具或讀取工作區。\n"
        "輸出必須是單一 JSON object，不得有 Markdown code fence。\n"
        f"JSON Schema：{canonical_schema}\n\n"
        "任務：\n公開 V4 prompt"
    )
    assert effective_prompt == expected_effective_prompt
    assert forbidden_role_instruction not in effective_prompt
    assert hashlib.sha256(broker_calls[0]["raw_request"]).hexdigest() == hashlib.sha256(
        expected_effective_prompt.encode()
    ).hexdigest()
    assert len(broker_calls[0]["raw_request"]) == len(expected_effective_prompt.encode())
    assert broker_calls[0]["request_sha256"] == request["request_sha256"]


def test_maximum_valid_outbox_payload_fits_v4_effective_prompt_ceiling() -> None:
    empty_schema = {"description": "", "type": "object"}
    empty_schema_bytes = outbox._json_bytes(empty_schema)
    response_schema = {
        "description": "x" * (outbox.MAX_SCHEMA_BYTES - len(empty_schema_bytes)),
        "type": "object",
    }
    prompt = "x" * outbox.MAX_PROMPT_BYTES

    request = outbox.build_external_request(
        namespace="maximum-valid-v4-envelope",
        role="writer",
        model="gemini-3.5-flash",
        prompt=prompt,
        response_schema=response_schema,
    )
    effective_prompt = runner._render_v4_effective_prompt(
        request["role"],
        request["prompt"],
        request["response_schema"],
    )

    assert len(outbox._json_bytes(response_schema)) == outbox.MAX_SCHEMA_BYTES
    assert len(effective_prompt) <= broker.MAX_AGY_PROMPT_BYTES


def test_production_runner_explicitly_selects_closed_profile_for_unknown_basename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    monkeypatch.setenv("AGY_GEMINI_V4_PROFILE", "raw_stdin_v1")
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-explicit-profile",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    broker_calls: list[dict[str, object]] = []

    def fake_broker(**kwargs: object) -> BrokerResult:
        broker_calls.append(kwargs)
        receipt = ExecutionReceipt(
            request["job_id"],
            request["namespace"],
            "attempt-1",
            request["request_sha256"],
            request["model"],
            "antigravity_cli_v1",
            executable_digest,
        )
        return _broker_result("BLOCKED", receipt)

    monkeypatch.setattr(runner, "run_single_shot", fake_broker)

    assert process_once(tmp_path)["status"] == "failed"
    assert broker_calls[0]["target_profile"] == "antigravity_cli_v1"
    assert broker_calls[0]["expected_executable_digest"] == executable_digest
    failed = json.loads((tmp_path / "failed" / f"{request['job_id']}.json").read_text())
    assert failed["broker_diagnostic"]["result_validation"] == "NOT_EVALUATED"


def test_runner_flag_on_rejects_misbound_complete_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-misbound",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    wrong = ExecutionReceipt(
        "wrong-operation",
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: _broker_result("COMPLETE", wrong, result={"ok": True}))
    legacy_calls: list[str] = []
    result = process_once(tmp_path, generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": True})
    assert result["status"] == "failed"
    assert legacy_calls == []
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()


def test_runner_rejects_schema_valid_success_without_production_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-no-provenance",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    synthetic_receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "raw_stdin_v1",
        executable_digest,
    )
    monkeypatch.setattr(
        runner,
        "run_single_shot",
        lambda **_kwargs: _broker_result("COMPLETE", synthetic_receipt, result={"ok": True}),
    )

    result = process_once(tmp_path)

    assert result["status"] == "failed"
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()


def test_broker_preserves_schema_valid_pretty_json_for_stdout_digest_binding(
    tmp_path: Path,
) -> None:
    expected_stdout = json.dumps(
        {"ok": True},
        indent=2,
        sort_keys=True,
    ).encode() + b"\n"
    executable = tmp_path / "pretty-json-target"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "print(json.dumps({'ok': True}, indent=2, sort_keys=True))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()

    result = broker.run_single_shot(
        operation_id="operation-pretty-json",
        item_id="item-pretty-json",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
        executable=executable,
        target_profile=broker.RAW_STDIN_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request=b"public synthetic request",
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=tmp_path / "ledger.jsonl",
        anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
    )

    assert result.caller_contract_satisfied is True
    assert result.result == {"ok": True}
    assert result.result_json == expected_stdout
    assert result.byte_count == len(expected_stdout)
    assert result.stdout_sha256 == hashlib.sha256(expected_stdout).hexdigest()


@pytest.mark.parametrize(
    ("raw_output", "expected_diagnostic"),
    (
        (b"", "EMPTY"),
        (b"\xff", "UTF8_INVALID"),
        (b"```json\n{\"ok\":true}\n```\n", "MARKDOWN_FENCE"),
        (b"result: {\"ok\":true}", "WRAPPED_JSON"),
        (b"{\"ok\":", "PARSE_ERROR_AT_END"),
        (b"{\"ok\":nope}", "PARSE_ERROR_OTHER"),
    ),
)
def test_broker_classifies_json_invalid_without_retaining_output(
    tmp_path: Path,
    raw_output: bytes,
    expected_diagnostic: str,
) -> None:
    executable = tmp_path / f"json-invalid-{expected_diagnostic.lower()}"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"sys.stdout.buffer.write(bytes.fromhex({raw_output.hex()!r}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()

    result = broker.run_single_shot(
        operation_id=f"operation-{expected_diagnostic.lower()}",
        item_id="item-json-invalid",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
        executable=executable,
        target_profile=broker.RAW_STDIN_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request=b"public synthetic request",
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=tmp_path / f"{expected_diagnostic.lower()}.jsonl",
        anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
    )

    assert result.result_validation == "JSON_INVALID"
    assert result.json_diagnostic == expected_diagnostic
    assert result.result_json is None
    serialized = json.dumps(result.normalized_trace(), ensure_ascii=False)
    if raw_output:
        assert raw_output.hex() not in serialized
    assert "result:" not in serialized


@pytest.mark.parametrize(
    ("json_diagnostic", "expected"),
    (
        ("MARKDOWN_FENCE", "MARKDOWN_FENCE"),
        ("must-not-persist", None),
        ({"secret": "must-not-persist"}, None),
    ),
)
def test_runner_persists_only_closed_json_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    json_diagnostic: object,
    expected: str | None,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-json-diagnostic",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 JSON diagnostic synthetic request",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        broker.ANTIGRAVITY_CLI_PROFILE,
        executable_digest,
    )
    malformed = BrokerResult(
        replay_status="COMPLETE",
        process_count=1,
        outcome="SUCCESS",
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=(),
        result_validation="JSON_INVALID",
        json_diagnostic=json_diagnostic,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: malformed)

    result = process_once(tmp_path)

    assert result["status"] == "failed"
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text())
    expected_fields = {
        "outcome",
        "process_count",
        "replay_status",
        "result_validation",
    }
    if expected is None:
        assert "json_diagnostic" not in failed["broker_diagnostic"]
    else:
        assert failed["broker_diagnostic"]["json_diagnostic"] == expected
        expected_fields.add("json_diagnostic")
    assert set(failed["broker_diagnostic"]) == expected_fields
    assert "must-not-persist" not in failed_path.read_text()


@pytest.mark.parametrize("status", ("BLOCKED", "AMBIGUOUS", "INVALID"))
def test_runner_flag_on_fails_closed_without_legacy_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace=f"opaque-run-{status.lower()}",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: _broker_result(status, receipt))
    legacy_calls: list[str] = []
    result = process_once(tmp_path, generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": True})
    assert result["status"] == "failed"
    assert legacy_calls == []
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()
    assert (tmp_path / "failed" / f"{request['job_id']}.json").exists()
    assert (tmp_path / "archive" / f"{request['job_id']}.json").exists()


def test_concurrent_create_loser_returns_replayed_external_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    ledger_path = tmp_path / "ledger.jsonl"
    anchor_store = broker.FileAnchorStore(tmp_path / "anchors")
    binding = broker.Binding("operation-concurrent", "item-concurrent", "attempt-1")
    definitions = [
        ("OPERATION_CREATED", {}),
        ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
        ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4321}),
        ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
    ]
    frames = []
    parent = None
    for sequence, (event_type, fields) in enumerate(definitions, 1):
        event = {
            "schema_version": 2,
            "sequence": sequence,
            "parent_sha256": parent,
            "event_type": event_type,
            "operation_id": binding.operation_id,
            "item_id": binding.item_id,
            "attempt_id": binding.attempt_id,
            **fields,
        }
        encoded = broker.canonical_json(event)
        frames.append(encoded + b"\n")
        parent = hashlib.sha256(encoded).hexdigest()
    assert parent is not None
    real_open = broker.os.open

    def lose_create_race(path: object, flags: int, mode: int = 0o777) -> int:
        if Path(path) == ledger_path and flags & broker.os.O_EXCL:
            ledger_path.write_bytes(b"".join(frames))
            assert anchor_store.compare_and_swap(
                binding.operation_id,
                binding.attempt_id,
                None,
                parent,
            )
            raise FileExistsError
        return real_open(path, flags, mode)

    monkeypatch.setattr(broker.os, "open", lose_create_race)

    result = broker.run_single_shot(
        operation_id=binding.operation_id,
        item_id=binding.item_id,
        attempt_id=binding.attempt_id,
        request_sha256="a" * 64,
        model="gemini-3.5-flash",
        executable=executable,
        target_profile=broker.ANTIGRAVITY_CLI_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request="公開 concurrent duplicate synthetic request".encode(),
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=ledger_path,
        anchor_store=anchor_store,
    )

    assert (result.replay_status, result.process_count) == ("COMPLETE", 1)
    assert result.caller_contract_satisfied is False
    assert result.final_anchor == parent


def test_concurrent_create_loser_returns_invalid_when_race_anchor_is_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    ledger_path = tmp_path / "ledger.jsonl"
    anchor_store = broker.FileAnchorStore(tmp_path / "anchors")
    load_calls = 0
    target_spawns: list[list[str]] = []

    def load_race_anchor(_operation_id: str, _attempt_id: str) -> str | None:
        nonlocal load_calls
        load_calls += 1
        if load_calls == 1:
            return None
        raise broker.AnchorError("synthetic unreadable race anchor")

    def lose_create_race(_path: object, _flags: int, _mode: int = 0o777) -> int:
        raise FileExistsError

    def reject_spawn(command: list[str], **_kwargs: object) -> None:
        target_spawns.append(command)
        raise AssertionError("race loser must not spawn broker or target")

    monkeypatch.setattr(anchor_store, "load", load_race_anchor)
    monkeypatch.setattr(broker.os, "open", lose_create_race)
    monkeypatch.setattr(broker.subprocess, "Popen", reject_spawn)

    result = broker.run_single_shot(
        operation_id="operation-race-invalid",
        item_id="item-race-invalid",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="gemini-3.5-flash",
        executable=executable,
        target_profile=broker.ANTIGRAVITY_CLI_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request="公開 malformed race anchor synthetic request".encode(),
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=ledger_path,
        anchor_store=anchor_store,
    )

    assert (result.replay_status, result.process_count) == ("INVALID", "UNKNOWN")
    assert result.errors == ("EXTERNAL_ANCHOR_INVALID",)
    assert result.caller_contract_satisfied is False
    assert result.result_json is None
    assert result.final_anchor is None
    assert result.automatic_resend_allowed is False
    assert target_spawns == []
    assert load_calls == 2


def test_runner_flag_on_fails_closed_on_malformed_success_without_legacy_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-malformed",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 malformed-output synthetic request",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    malformed = BrokerResult(
        replay_status="COMPLETE",
        process_count=1,
        outcome="SUCCESS",
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=("MALFORMED_OUTPUT",),
        result_validation="SCHEMA_MISMATCH",
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: malformed)
    legacy_calls: list[str] = []

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": True},
    )

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "V4BrokerFailure",
    }
    assert legacy_calls == []
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()
    failed = json.loads((tmp_path / "failed" / f"{request['job_id']}.json").read_text())
    assert failed["broker_diagnostic"] == {
        "outcome": "SUCCESS",
        "process_count": 1,
        "replay_status": "COMPLETE",
        "result_validation": "SCHEMA_MISMATCH",
    }
    assert "prompt" not in failed
    assert "result" not in failed


def test_runner_persists_only_closed_schema_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    diagnostic_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ok": {"type": "boolean"},
            "items": {"type": "array", "items": {"type": "boolean"}},
            "a" * 65: {"type": "boolean"},
        },
        "required": ["ok"],
    }
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-schema-diagnostic",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 schema diagnostic synthetic request",
        response_schema=diagnostic_schema,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    malformed = BrokerResult(
        replay_status="COMPLETE",
        process_count=1,
        outcome="SUCCESS",
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=(),
        result_validation="SCHEMA_MISMATCH",
    )
    object.__setattr__(
        malformed,
        "schema_diagnostics",
        (
            broker.SchemaDiagnostic("type", ("ok",)),
            broker.SchemaDiagnostic("message", ("ok",)),
            broker.SchemaDiagnostic("enum", ("unknown-property",)),
            broker.SchemaDiagnostic("type", ({"secret": "must-not-persist"},)),
            broker.SchemaDiagnostic("type", ("ok", "too-deep")),
            broker.SchemaDiagnostic("type", ("items", 10**1000)),
            broker.SchemaDiagnostic("type", ("ok",) * 9),
            broker.SchemaDiagnostic("type", ("a" * 65,)),
        ),
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: malformed)

    result = process_once(tmp_path)

    assert result["status"] == "failed"
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text())
    assert failed["broker_diagnostic"]["schema_diagnostics"] == [
        {"keyword": "type", "path": ["ok"]},
    ]
    assert "must-not-persist" not in failed_path.read_text()
    assert "unknown-property" not in failed_path.read_text()
    assert "message" not in failed_path.read_text()


@pytest.mark.parametrize(
    ("replay_status", "process_count", "outcome", "result_validation"),
    (
        (
            {"secret": "must-not-persist"},
            ["must-not-persist"],
            {"secret": "must-not-persist"},
            {"secret": "must-not-persist"},
        ),
        (
            "must-not-persist",
            "must-not-persist",
            "must-not-persist",
            "must-not-persist",
        ),
    ),
)
def test_runner_closes_all_forged_broker_diagnostic_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replay_status: object,
    process_count: object,
    outcome: object,
    result_validation: object,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-forged-diagnostic",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 forged diagnostic synthetic request",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    secret_marker = "must-not-persist"
    forged = BrokerResult(
        replay_status=replay_status,  # type: ignore[arg-type]
        process_count=process_count,  # type: ignore[arg-type]
        outcome=outcome,  # type: ignore[arg-type]
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=("FORGED_DIAGNOSTIC",),
        result_validation=result_validation,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: forged)

    result = process_once(tmp_path)

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "V4BrokerFailure",
    }
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text())
    assert failed["broker_diagnostic"] == {
        "outcome": None,
        "process_count": "UNKNOWN",
        "replay_status": "INVALID",
        "result_validation": "NOT_EVALUATED",
    }
    assert secret_marker not in failed_path.read_text()


def test_runner_preserves_invalid_model_json_for_pipeline_rejection(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )

    result = process_once(tmp_path, generate_json=lambda *_args: {"wrong": True})

    assert result == {"status": "processed", "job_id": request["job_id"]}
    response = json.loads((tmp_path / "inbox" / f"{request['job_id']}.json").read_text())
    assert response["result"] == {"wrong": True}
    assert not (tmp_path / "failed" / f"{request['job_id']}.json").exists()


def test_runner_returns_idle_for_empty_outbox(tmp_path: Path) -> None:
    assert process_once(tmp_path, generate_json=lambda *_args: {"ok": True}) == {"status": "idle"}


def test_pipeline_tick_reserves_one_bounded_final_content_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(json.dumps({"run_id": "bounded-repair-run"}), encoding="utf-8")
    observed: list[int] = []

    def fake_run_writer_reviewer(_run_dir: Path, _client: object, max_repairs: int = 2):
        observed.append(max_repairs)
        return {"articles": []}, {"articles": []}

    monkeypatch.setattr(outbox.pipeline, "run_writer_reviewer", fake_run_writer_reviewer)

    result = run_pipeline_tick(run_dir, tmp_path / "queue")

    assert result["status"] == "complete"
    assert observed == [2]


def test_outbox_client_retries_json_decode_with_new_job_identity(tmp_path: Path) -> None:
    client = outbox.OutboxGeminiClient(tmp_path, namespace="retry-json")
    first = outbox.create_external_request(
        tmp_path,
        namespace="retry-json",
        role="writer",
        model=client.writer_model,
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{first['job_id']}.json",
        {"error_type": "JSONDecodeError"},
    )

    with pytest.raises(ExternalJobPending) as pending:
        client.generate_json("writer", "公開 prompt", SCHEMA)

    assert pending.value.job_id != first["job_id"]
    retry_request = json.loads((tmp_path / "outbox" / f"{pending.value.job_id}.json").read_text())
    assert retry_request["namespace"] == "retry-json-r1"
    assert retry_request["prompt_sha256"] == first["prompt_sha256"]


def test_outbox_client_stops_after_two_json_decode_retries(tmp_path: Path) -> None:
    client = outbox.OutboxGeminiClient(tmp_path, namespace="retry-stop")
    failed_job_ids: list[str] = []
    for retry_index in range(3):
        namespace = "retry-stop" if retry_index == 0 else f"retry-stop-r{retry_index}"
        request = outbox.create_external_request(
            tmp_path,
            namespace=namespace,
            role="reviewer",
            model=client.reviewer_model,
            prompt="公開 prompt",
            response_schema=SCHEMA,
        )
        failed_job_ids.append(request["job_id"])
        outbox.atomic_write_json(
            tmp_path / "failed" / f"{request['job_id']}.json",
            {"error_type": "JSONDecodeError"},
        )

    with pytest.raises(outbox.ExternalJobFailed) as failure:
        client.generate_json("reviewer", "公開 prompt", SCHEMA)

    assert failure.value.job_id == failed_job_ids[-1]
    assert failure.value.error_type == "JSONDecodeError"
    assert len(list((tmp_path / "outbox").glob("*.json"))) == 3


def test_pipeline_advances_writer_then_fresh_reviewer_across_ticks(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "optimize-01"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    brief = {
        "schema_version": 1,
        "run_id": "private-optimize-run-id",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-001",
                "canonical_path": "/articles/astrology/astrology-0001",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    proposed = {
        "title": "公開搜尋詞怎麼看？整理使用情境與限制",
        "description": "公開搜尋詞適合用來整理讀者真正想確認的情境、可觀察資訊與下一步選擇；本文只提供一般說明，不能替個人判斷，也不承諾任何特定結果，仍須回到實際資料與互動再決定。",
        "answer": "先確認具體情境與資料；這項說明不能替個人下結論。",
    }
    roles: list[str] = []

    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    writer_request_path = next((queue_root / "outbox").glob("*.json"))
    writer_request_text = writer_request_path.read_text(encoding="utf-8")
    assert "private-optimize-run-id" not in writer_request_text
    assert "app/web/static/article-registry.js" not in writer_request_text
    assert '"run_id"' not in writer_request_text

    def generate(role: str, _model: str, _prompt: str, _schema: dict[str, object]) -> dict[str, object]:
        roles.append(role)
        if role == "writer":
            return {"articles": [{"slot": "article-01", "proposed": proposed}]}
        return {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}

    assert process_once(queue_root, generate_json=generate)["status"] == "processed"
    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    assert process_once(queue_root, generate_json=generate)["status"] == "processed"

    result = run_pipeline_tick(run_dir, queue_root)

    assert result["status"] == "complete"
    assert roles == ["writer", "reviewer"]
    candidate = json.loads((run_dir / "candidate.json").read_text())
    review = json.loads((run_dir / "review.json").read_text())
    assert candidate["articles"][0]["proposed"] == proposed
    assert review["articles"][0]["verdict"] == "APPROVE"


def test_invalid_writer_schema_enqueues_a_distinct_retry_job(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "optimize-writer-schema-retry"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    brief = {
        "schema_version": 1,
        "run_id": "private-writer-schema-retry",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-RETRY-001",
                "canonical_path": "/articles/astrology/astrology-0001",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ExternalJobPending) as first_pending:
        run_pipeline_tick(run_dir, queue_root)
    process_once(queue_root, generate_json=lambda *_args: {"articles": [{"slot": "article-01"}]})

    with pytest.raises(ExternalJobPending) as retry_pending:
        run_pipeline_tick(run_dir, queue_root)

    assert retry_pending.value.job_id != first_pending.value.job_id
    retry = json.loads((queue_root / "outbox" / f"{retry_pending.value.job_id}.json").read_text())
    assert "schema repair 1" in retry["prompt"]


def test_invalid_reviewer_json_becomes_hard_rejection(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "optimize-invalid-review"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    brief = {
        "schema_version": 1,
        "run_id": "private-invalid-review-run",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-002",
                "canonical_path": "/articles/astrology/astrology-0002",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞二"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    proposed = {
        "title": "公開搜尋詞二怎麼看？整理情境與限制",
        "description": "公開搜尋詞二適合整理讀者想確認的情境、可觀察資料與下一步選擇；本文只提供一般說明，不能替個人判斷，也不承諾任何特定結果，仍須回到實際互動再決定。",
        "answer": "先確認具體資料；這項說明不能替個人下結論。",
    }

    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    process_once(
        queue_root,
        generate_json=lambda *_args: {"articles": [{"slot": "article-01", "proposed": proposed}]},
    )
    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    process_once(queue_root, generate_json=lambda *_args: {"wrong": True})

    result = run_pipeline_tick(run_dir, queue_root)
    review = json.loads((run_dir / "review.json").read_text())

    assert result["status"] == "complete"
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["hard_failure"] is True
    assert review["articles"][0]["findings"][0]["code"].startswith("invalid_reviewer_json:")

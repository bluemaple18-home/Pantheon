from __future__ import annotations

import hashlib
import io
import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

import pytest
import scripts.agy_gemini_outbox as outbox
import scripts.agy_gemini_runner as runner
import scripts.agy_seo_copy_pipeline as pipeline
from scripts import agy_gemini_v4_broker as broker
from scripts.agy_gemini_v4_broker import BrokerResult, ExecutionReceipt

from scripts.agy_gemini_outbox import (
    ExternalJobFailed,
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
NORMALIZED_TRACE_KEYS = frozenset(
    {
        "replay_status",
        "process_count",
        "outcome",
        "exit_status",
        "stdout_sha256",
        "stderr_sha256",
        "byte_count",
        "receipt",
        "caller_contract_satisfied",
        "result_validation",
        "result",
        "errors",
        "automatic_resend_allowed",
    }
)


def _assert_normalized_trace_schema(trace: dict[str, object]) -> None:
    assert frozenset(trace) == NORMALIZED_TRACE_KEYS, "normalized trace schema changed"


def _failure_receipt(
    request: dict[str, object],
    *,
    error_type: object,
    error_code: object = None,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "error_type": error_type,
        "completed_at": "2026-07-26T00:30:00+08:00",
    }
    if error_code is not None:
        receipt["error_code"] = error_code
    return receipt


def _deep_failure_json(marker: str, depth: int = 20_000) -> str:
    payload = "[" * depth + json.dumps(marker) + "]" * depth
    assert len(payload.encode("utf-8")) < outbox.MAX_FAILURE_RECEIPT_BYTES
    return payload


def _write_production_pool(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    credentials: dict[str, str] = {}
    slots: list[dict[str, str]] = []
    for index in range(3):
        slot_id = f"account-{index + 1}"
        credential = f"test-production-credential-slot-{index + 1}-value"
        credential_path = tmp_path / f"credential-{index + 1}"
        credential_path.write_text(credential + "\n", encoding="utf-8")
        credential_path.chmod(0o600)
        credentials[slot_id] = credential
        slots.append({"slot_id": slot_id, "credential_file": str(credential_path)})
    manifest = tmp_path / "production-pool.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": "pantheon-production-v1",
                "slots": list(reversed(slots)),
            }
        ),
        encoding="utf-8",
    )
    manifest.chmod(0o600)
    return manifest, credentials


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


def test_production_pool_selection_is_stable_and_distributed(tmp_path: Path) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    selections: dict[str, str] = {}
    try:
        for index in range(300):
            job_id = hashlib.sha256(f"job-{index}".encode()).hexdigest()[:40]
            source = runner._open_production_credential_source(manifest, job_id)
            selections[job_id] = source.slot_id
            os.close(source.descriptor)
        repeated = runner._open_production_credential_source(manifest, next(iter(selections)))
        assert repeated.slot_id == selections[next(iter(selections))]
        os.close(repeated.descriptor)
    finally:
        pass

    assert set(selections.values()) == {"account-1", "account-2", "account-3"}
    assert all(
        slot_id
        == sorted(("account-1", "account-2", "account-3"))[
            int.from_bytes(
                hashlib.sha256(f"pantheon-production-v1\0{job_id}".encode()).digest()[:8],
                "big",
            )
            % 3
        ]
        for job_id, slot_id in selections.items()
    )


@pytest.mark.parametrize("unsafe_target", ["manifest-mode", "manifest-symlink", "credential-mode", "credential-symlink"])
def test_production_pool_rejects_unsafe_files(
    tmp_path: Path,
    unsafe_target: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    selected_path = Path(payload["slots"][0]["credential_file"])
    if unsafe_target == "manifest-mode":
        manifest.chmod(0o644)
    elif unsafe_target == "manifest-symlink":
        target = tmp_path / "pool-target.json"
        manifest.replace(target)
        manifest.symlink_to(target)
    elif unsafe_target == "credential-mode":
        selected_path.chmod(0o644)
    else:
        target = selected_path.with_suffix(".target")
        selected_path.replace(target)
        selected_path.symlink_to(target)

    with pytest.raises(ValueError, match="production credential"):
        source = runner._open_production_credential_source(manifest, "a" * 40)
        os.close(source.descriptor)


@pytest.mark.parametrize("malformation", ["slot-count", "duplicate-slot", "relative-path", "extra-field"])
def test_production_pool_rejects_incompatible_schema(
    tmp_path: Path,
    malformation: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if malformation == "slot-count":
        payload["slots"].pop()
    elif malformation == "duplicate-slot":
        payload["slots"][1]["slot_id"] = payload["slots"][0]["slot_id"]
    elif malformation == "relative-path":
        payload["slots"][0]["credential_file"] = "relative-key-file"
    else:
        payload["unexpected"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    manifest.chmod(0o600)

    with pytest.raises(ValueError, match="production credential pool"):
        source = runner._open_production_credential_source(manifest, "b" * 40)
        os.close(source.descriptor)


def test_production_pool_uses_only_selected_slot_and_one_provider_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, credentials = _write_production_pool(tmp_path)
    request = create_external_request(
        tmp_path / "queue",
        namespace="production-pool-success",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    credential_paths = {
        Path(slot["credential_file"])
        for slot in json.loads(manifest.read_text(encoding="utf-8"))["slots"]
    }
    opened_credentials: list[Path] = []
    real_open = runner.os.open

    def tracked_open(path: object, flags: int, mode: int = 0o777) -> int:
        candidate = Path(path)
        if candidate in credential_paths:
            opened_credentials.append(candidate)
        return real_open(path, flags, mode)

    provider_calls: list[object] = []

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "{\"ok\":true}"}]}}]}
            ).encode()

    def fake_urlopen(provider_request: object, **_kwargs: object) -> FakeResponse:
        provider_calls.append(provider_request)
        return FakeResponse()

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner.os, "open", tracked_open)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", fake_urlopen)

    result = process_once(tmp_path / "queue")
    response_path = tmp_path / "queue" / "inbox" / f"{request['job_id']}.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    selected = response["credential_pool"]["slot_id"]

    assert result["status"] == "processed"
    assert result["credential_pool"] == response["credential_pool"]
    assert len(provider_calls) == 1
    manifest_slots = json.loads(manifest.read_text(encoding="utf-8"))["slots"]
    expected_path = next(
        Path(slot["credential_file"])
        for slot in manifest_slots
        if slot["slot_id"] == selected
    )
    assert opened_credentials == [expected_path]
    assert consume_external_response(tmp_path / "queue", request) == {"ok": True}
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (response_path, tmp_path / "queue" / "archive" / f"{request['job_id']}.json")
    )
    assert all(secret not in persisted for secret in credentials.values())
    assert all(str(path) not in persisted for path in credential_paths)


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("rate-limit", "API_RATE_LIMITED"),
        ("provider-nonzero", "API_HTTP_ERROR"),
        ("redirect", "API_HTTP_ERROR"),
        ("timeout", "API_TIMEOUT"),
        ("transport", "API_TRANSPORT_ERROR"),
    ],
)
def test_production_pool_failure_is_terminal_without_rotation_or_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_code: str,
) -> None:
    manifest, credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace="production-pool-rate-limit",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    calls = 0

    def fail_provider(provider_request: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise TimeoutError("private-timeout-detail")
        if failure == "transport":
            raise pipeline.urllib.error.URLError(OSError("private-transport-detail"))
        status = 429 if failure == "rate-limit" else 302 if failure == "redirect" else 503
        raise pipeline.urllib.error.HTTPError(
            getattr(provider_request, "full_url", "https://example.invalid"),
            status,
            "private-provider-detail",
            {},
            io.BytesIO(b"must-not-persist-provider-body"),
        )

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", fail_provider)
    result = process_once(queue_root)
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text(encoding="utf-8"))

    assert calls == 1
    assert result["status"] == "failed"
    assert result["error_type"] == "GeminiApiFailure"
    assert result["error_code"] == expected_code
    assert result["credential_pool"] == failed["credential_pool"]
    assert not (queue_root / "inbox" / f"{request['job_id']}.json").exists()
    assert (queue_root / "archive" / f"{request['job_id']}.json").exists()
    persisted = failed_path.read_text(encoding="utf-8")
    assert "provider-body" not in persisted
    assert "private-provider-detail" not in persisted
    assert "private-timeout-detail" not in persisted
    assert "private-transport-detail" not in persisted
    assert all(secret not in persisted for secret in credentials.values())
    with pytest.raises(ExternalJobFailed) as raised:
        consume_external_response(queue_root, request)
    assert raised.value.error_code == expected_code


def test_production_pool_flag_off_preserves_injected_cli_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="production-pool-flag-off",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    calls: list[tuple[str, str, str, dict[str, object]]] = []

    def fake_generate(role: str, model: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
        calls.append((role, model, prompt, schema))
        return {"ok": True}

    monkeypatch.delenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", raising=False)
    result = process_once(tmp_path, generate_json=fake_generate)

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert len(calls) == 1


def test_production_pool_receipt_rejects_unclosed_identity(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="production-pool-closed-receipt",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    inbox = tmp_path / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir()
    inbox.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "job_id": request["job_id"],
                "request_sha256": request["request_sha256"],
                "model": request["model"],
                "completed_at": "2026-07-26T01:00:00+08:00",
                "result": {"ok": True},
                "credential_pool": {
                    "pool_id": "pantheon-production-v1",
                    "slot_id": "account-1",
                    "manifest_sha256": "a" * 64,
                    "credential_file": "must-not-pass",
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="external response fields are strict"):
        consume_external_response(tmp_path, request)


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


def test_lane_client_consumes_existing_response_from_legacy_shared_queue(tmp_path: Path) -> None:
    legacy_root = tmp_path / "shared"
    lane_root = legacy_root / "lanes" / "new"
    request = create_external_request(
        legacy_root,
        namespace="opaque-lane-fallback",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    response = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": request["model"],
        "completed_at": "2026-07-25T20:00:00+08:00",
        "result": {"ok": True},
    }
    inbox = legacy_root / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir()
    inbox.write_text(json.dumps(response), encoding="utf-8")
    client = OutboxGeminiClient(
        lane_root,
        legacy_queue_root=legacy_root,
        namespace="opaque-lane-fallback",
        writer_model="gemini-test-writer",
    )

    assert client.generate_json("writer", "公開 prompt", SCHEMA) == {"ok": True}
    assert not list((lane_root / "outbox").glob("*.json"))


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


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("nonzero", "CLI_NONZERO"),
        ("timeout", "CLI_TIMEOUT"),
        ("not-found", "CLI_NOT_FOUND"),
        ("envelope", "CLI_ENVELOPE_ERROR"),
    ],
)
def test_runner_failure_receipt_persists_only_closed_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_code: str,
) -> None:
    private_detail = "/Users/example/private prompt GEMINI_API_KEY=must-not-persist raw stderr"
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-closed-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )

    def fake_run(args: list[str], **_kwargs: object) -> object:
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, timeout=1, stderr=private_detail)
        if failure == "not-found":
            raise FileNotFoundError(private_detail)
        if failure == "nonzero":
            return subprocess.CompletedProcess(args, 7, "", private_detail)
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps({"error": private_detail}),
            "",
        )

    monkeypatch.setenv("AGY_GEMINI_CLI", "/opt/tools/gemini")
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    result = process_once(tmp_path)
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text(encoding="utf-8"))

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "GeminiCliFailure",
        "error_code": expected_code,
    }
    assert failed["error_code"] == expected_code
    assert set(failed) == {
        "schema_version",
        "job_id",
        "request_sha256",
        "error_type",
        "error_code",
        "completed_at",
    }
    persisted = failed_path.read_text(encoding="utf-8")
    for forbidden in ("prompt", "response", "stdout", "stderr", "GEMINI_API_KEY", "/Users/"):
        assert forbidden not in persisted


def test_outbox_failure_preserves_closed_error_code(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-code-consumer",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "job_id": request["job_id"],
                "request_sha256": request["request_sha256"],
                "error_type": "GeminiCliFailure",
                "error_code": "CLI_TIMEOUT",
                "completed_at": "2026-07-25T23:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "GeminiCliFailure"
    assert raised.value.error_code == "CLI_TIMEOUT"


@pytest.mark.parametrize(
    "unsafe_error_type",
    [
        "PRIVATE_PATH_MARKER/CREDENTIAL_MARKER",
        "X" * 10_000,
        ["PRIVATE_PATH_MARKER"],
        {"credential": "CREDENTIAL_MARKER"},
        7,
        None,
    ],
)
def test_failure_consumer_closes_untrusted_error_type(
    tmp_path: Path,
    unsafe_error_type: object,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-invalid-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{request['job_id']}.json",
        _failure_receipt(request, error_type=unsafe_error_type),
    )

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert "PRIVATE_PATH_MARKER" not in str(raised.value)
    assert "CREDENTIAL_MARKER" not in str(raised.value)


@pytest.mark.parametrize(
    "malformation",
    [
        "job-id",
        "request-hash",
        "extra-field",
        "missing-field",
        "invalid-code",
        "invalid-broker",
        "unhashable-broker",
        "invalid-timestamp",
        "non-object",
    ],
)
def test_failure_consumer_rejects_misbound_or_malformed_receipt(
    tmp_path: Path,
    malformation: str,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-malformed-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    receipt: object = _failure_receipt(request, error_type="RuntimeError")
    assert isinstance(receipt, dict)
    if malformation == "job-id":
        receipt["job_id"] = "0" * 40
    elif malformation == "request-hash":
        receipt["request_sha256"] = "0" * 64
    elif malformation == "extra-field":
        receipt["message"] = "PRIVATE_PATH_MARKER"
    elif malformation == "missing-field":
        receipt.pop("completed_at")
    elif malformation == "invalid-code":
        receipt["error_type"] = "GeminiCliFailure"
        receipt["error_code"] = ["CLI_TIMEOUT"]
    elif malformation == "invalid-broker":
        receipt["error_type"] = "V4BrokerFailure"
        receipt["broker_diagnostic"] = {"message": "CREDENTIAL_MARKER"}
    elif malformation == "unhashable-broker":
        receipt["error_type"] = "V4BrokerFailure"
        receipt["broker_diagnostic"] = {
            "replay_status": ["PRIVATE_PATH_MARKER"],
            "process_count": {"credential": "CREDENTIAL_MARKER"},
            "outcome": [],
            "result_validation": {},
        }
    elif malformation == "invalid-timestamp":
        receipt["completed_at"] = "2026-99-99T99:99:99+08:00"
    else:
        receipt = ["PRIVATE_PATH_MARKER", "CREDENTIAL_MARKER"]
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{request['job_id']}.json",
        receipt,
    )

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert "PRIVATE_PATH_MARKER" not in str(raised.value)
    assert "CREDENTIAL_MARKER" not in str(raised.value)


def test_failure_consumer_closes_invalid_json_without_echoing_payload(
    tmp_path: Path,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-invalid-json-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text('{"error_type":"PRIVATE_PATH_MARKER"', encoding="utf-8")

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert "PRIVATE_PATH_MARKER" not in str(raised.value)


def test_failure_consumer_closes_deep_valid_json_recursion(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-deep-json-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker = "/Users/PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(_deep_failure_json(marker), encoding="utf-8")

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert marker not in str(raised.value)
    assert raised.value.__cause__ is None


def test_deep_failure_json_does_not_leak_to_cli_or_operation_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = create_external_request(
        queue_root,
        namespace="opaque-run-deep-json-cli",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker = "/Users/PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(_deep_failure_json(marker), encoding="utf-8")

    class ConsumerClient:
        writer_model = "gemini-test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            return consume_external_response(queue_root, request)

    operation_receipt = tmp_path / "writer-operation.json"
    with pytest.raises(outbox.ExternalJobFailed):
        pipeline._generate_with_receipt(
            ConsumerClient(),
            "writer",
            "public prompt",
            SCHEMA,
            operation_receipt,
        )
    assert marker not in operation_receipt.read_text(encoding="utf-8")

    monkeypatch.setattr(
        outbox,
        "run_pipeline_tick",
        lambda *_args: consume_external_response(queue_root, request),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["agy_gemini_outbox", "tick", str(run_dir), "--queue-root", str(queue_root)],
    )
    assert outbox.main() == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert marker not in combined
    assert "Traceback" not in combined
    assert str(tmp_path) not in combined
    assert json.loads(captured.out)["error_type"] == "InvalidFailureReceipt"


def test_invalid_failure_receipt_does_not_leak_to_cli_stdout_or_operation_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = create_external_request(
        queue_root,
        namespace="opaque-run-cli-invalid-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker = "PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    outbox.atomic_write_json(
        queue_root / "failed" / f"{request['job_id']}.json",
        _failure_receipt(request, error_type=marker),
    )

    class ConsumerClient:
        writer_model = "gemini-test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            return consume_external_response(queue_root, request)

    operation_receipt = tmp_path / "writer-operation.json"
    with pytest.raises(outbox.ExternalJobFailed) as raised:
        pipeline._generate_with_receipt(
            ConsumerClient(),
            "writer",
            "public prompt",
            SCHEMA,
            operation_receipt,
        )
    persisted = operation_receipt.read_text(encoding="utf-8")
    assert marker not in str(raised.value)
    assert marker not in persisted

    monkeypatch.setattr(
        outbox,
        "run_pipeline_tick",
        lambda *_args: consume_external_response(queue_root, request),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["agy_gemini_outbox", "tick", str(run_dir), "--queue-root", str(queue_root)],
    )
    assert outbox.main() == 1
    stdout = capsys.readouterr().out
    assert marker not in stdout
    assert json.loads(stdout)["error_type"] == "InvalidFailureReceipt"


def test_runner_requeues_stale_processing_job_after_interrupted_worker(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-stale-processing",
        role="writer",
        model="gemini-test-writer",
        prompt="產生公開 candidate",
        response_schema=SCHEMA,
    )
    outbox_path = tmp_path / "outbox" / f"{request['job_id']}.json"
    processing_path = tmp_path / "processing" / outbox_path.name
    processing_path.parent.mkdir()
    os.replace(outbox_path, processing_path)
    stale_time = time.time() - runner.STALE_PROCESSING_SECONDS - 1
    os.utime(processing_path, (stale_time, stale_time))

    result = process_once(tmp_path, generate_json=lambda *_args: {"ok": True})

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert not processing_path.exists()
    assert (tmp_path / "archive" / processing_path.name).exists()


def test_runner_does_not_requeue_fresh_processing_job(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-live-processing",
        role="writer",
        model="gemini-test-writer",
        prompt="產生公開 candidate",
        response_schema=SCHEMA,
    )
    outbox_path = tmp_path / "outbox" / f"{request['job_id']}.json"
    processing_path = tmp_path / "processing" / outbox_path.name
    processing_path.parent.mkdir()
    os.replace(outbox_path, processing_path)

    result = process_once(tmp_path, generate_json=lambda *_args: {"ok": True})

    assert result == {"status": "idle"}
    assert processing_path.exists()


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
    trace = result.normalized_trace()
    _assert_normalized_trace_schema(trace)
    assert trace == {
        "replay_status": "COMPLETE",
        "process_count": 1,
        "outcome": "SUCCESS",
        "exit_status": 0,
        "stdout_sha256": hashlib.sha256(raw_output).hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "byte_count": len(raw_output),
        "receipt": {
            "operation_id": f"operation-{expected_diagnostic.lower()}",
            "item_id": "item-json-invalid",
            "attempt_id": "attempt-1",
            "request_sha256": "a" * 64,
            "model": "synthetic-model",
            "target_profile": broker.RAW_STDIN_PROFILE,
            "executable_digest": executable_digest,
        },
        "caller_contract_satisfied": False,
        "result_validation": "JSON_INVALID",
        "result": None,
        "errors": [],
        "automatic_resend_allowed": False,
    }


def test_normalized_trace_schema_rejects_invalid_raw_stdout_bytes() -> None:
    trace = dict.fromkeys(NORMALIZED_TRACE_KEYS)
    trace["stdout_sha256"] = hashlib.sha256(b"\xff").hexdigest()
    _assert_normalized_trace_schema(trace)

    trace["raw_stdout"] = b"\xff"
    with pytest.raises(AssertionError, match="normalized trace schema changed"):
        _assert_normalized_trace_schema(trace)


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


def test_pipeline_tick_routes_translation_brief_to_multilingual_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(
        json.dumps({"run_id": "translate-en-001", "mode": "translate_existing"}),
        encoding="utf-8",
    )
    observed: list[int] = []

    def fake_run_writer_reviewer(_run_dir: Path, _client: object, max_repairs: int = 2):
        observed.append(max_repairs)
        return {"articles": []}, {"articles": []}

    monkeypatch.setattr(outbox.multilingual, "run_writer_reviewer", fake_run_writer_reviewer)
    monkeypatch.setattr(
        outbox.pipeline,
        "run_writer_reviewer",
        lambda *_args, **_kwargs: pytest.fail("translation must not use the create pipeline"),
    )

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
        _failure_receipt(first, error_type="JSONDecodeError"),
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
            _failure_receipt(request, error_type="JSONDecodeError"),
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

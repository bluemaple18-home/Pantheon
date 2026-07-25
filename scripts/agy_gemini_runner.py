#!/usr/bin/env python3
"""處理 sanitized Gemini outbox；本腳本由使用者自行啟用的 runner 執行。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Final

from scripts.agy_gemini_outbox import (
    SCHEMA_VERSION,
    atomic_write_json,
    validate_external_request,
)
from scripts.agy_seo_copy_pipeline import GeminiClient
from scripts.agy_gemini_v4_broker import (
    ANTIGRAVITY_CLI_PROFILE,
    CredentialSource,
    GEMINI_STRUCTURED_API_PROFILE,
    ExecutionReceipt,
    FileAnchorStore,
    V4BrokerFailure,
    RESULT_VALIDATION_STATES,
    SchemaDiagnostic,
    run_single_shot,
)
from scripts.agy_gemini_v4_structured_target import encode_target_request


GenerateJson = Callable[[str, str, str, dict[str, Any]], dict[str, Any]]
REPLAY_STATUS_STATES = frozenset({"COMPLETE", "BLOCKED", "AMBIGUOUS", "INVALID"})
PROCESS_COUNT_STATES = frozenset({0, 1, "UNKNOWN"})
OUTCOME_STATES = frozenset({
    "CLI_NOT_FOUND",
    "CRASH_BEFORE_FORK",
    "PERMISSION_DENIED",
    "EXEC_FORMAT",
    "EXEC_RACE",
    "SUCCESS",
    "CLI_NONZERO",
    "CLI_TIMEOUT",
})
JSON_DIAGNOSTIC_STATES = frozenset({
    "EMPTY",
    "UTF8_INVALID",
    "MARKDOWN_FENCE",
    "WRAPPED_JSON",
    "PARSE_ERROR_AT_END",
    "PARSE_ERROR_OTHER",
})
SCHEMA_DIAGNOSTIC_KEYWORDS = frozenset({
    "additionalProperties",
    "enum",
    "maximum",
    "maxItems",
    "maxLength",
    "minimum",
    "minItems",
    "minLength",
    "required",
    "schema",
    "type",
})
SAFE_SCHEMA_PATH_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
MAX_SCHEMA_DIAGNOSTICS = 3
MAX_SCHEMA_DIAGNOSTIC_DEPTH = 8
MAX_SCHEMA_ARRAY_INDEX = 1_048_576
MAX_CREDENTIAL_POOL_BYTES = 16 * 1024
MAX_CREDENTIAL_POOL_SLOTS = 16
SAFE_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
STRUCTURED_TARGET_DIAGNOSTICS = frozenset({
    "AUTH_FAILED",
    "CREDENTIAL_INVALID",
    "ENVELOPE_INVALID",
    "INTERNAL_ERROR",
    "OUTPUT_BLOCKED",
    "OUTPUT_INCOMPLETE",
    "OUTPUT_TRUNCATED",
    "PROVIDER_REJECTED",
    "PROVIDER_UNAVAILABLE",
    "RATE_LIMITED",
    "REQUEST_INVALID",
    "TRANSPORT_ERROR",
})
V4_ROLE_INSTRUCTIONS: Final = {
    "writer": "你是 Pantheon 繁體中文文章 Writer。只輸出符合 schema 的 JSON，不得加入未提供的事實或承諾。",
    "reviewer": "你是獨立 Pantheon 文章 Reviewer。依規範嚴格審查，只輸出符合 schema 的 JSON；不得假設 Writer 對話內容。",
}


def _cli_generate_json(role: str, model: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    client = GeminiClient(writer_model=model if role == "writer" else None, reviewer_model=model if role == "reviewer" else None)
    client.transport = client._cli_transport
    return client.generate_json(role, prompt, schema)


def _render_v4_effective_prompt(
    role: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> bytes:
    if role not in V4_ROLE_INSTRUCTIONS:
        raise ValueError("V4 role is not closed")
    canonical_schema = json.dumps(
        response_schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        f"{V4_ROLE_INSTRUCTIONS[role]}\n"
        "禁止使用任何工具或讀取工作區。\n"
        "輸出必須是單一 JSON object，不得有 Markdown code fence。\n"
        f"JSON Schema：{canonical_schema}\n\n"
        f"任務：\n{prompt}"
    ).encode("utf-8")


def _open_private_credential_file(path: Path) -> int:
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError("V4 credential file is unavailable") from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o077
        or not 20 <= before.st_size <= 512
    ):
        raise ValueError("V4 credential file must be owner-only regular file")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("V4 credential file cannot be opened") from error
    try:
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_uid != os.getuid()
            or after.st_mode & 0o077
            or not 20 <= after.st_size <= 512
        ):
            raise ValueError("V4 credential file changed during validation")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_private_credential_pool(path: Path) -> tuple[dict[str, Any], str]:
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError("V4 credential pool is unavailable") from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o077
        or not 2 <= before.st_size <= MAX_CREDENTIAL_POOL_BYTES
    ):
        raise ValueError("V4 credential pool must be owner-only regular file")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("V4 credential pool cannot be opened") from error
    try:
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_uid != os.getuid()
            or after.st_mode & 0o077
            or not 2 <= after.st_size <= MAX_CREDENTIAL_POOL_BYTES
        ):
            raise ValueError("V4 credential pool changed during validation")
        chunks = bytearray()
        while len(chunks) <= MAX_CREDENTIAL_POOL_BYTES:
            chunk = os.read(
                descriptor,
                min(
                    4096,
                    MAX_CREDENTIAL_POOL_BYTES + 1 - len(chunks),
                ),
            )
            if not chunk:
                break
            chunks.extend(chunk)
        encoded = bytes(chunks)
    finally:
        os.close(descriptor)
    if len(encoded) != after.st_size:
        raise ValueError("V4 credential pool size is invalid")
    try:
        payload = json.loads(
            encoded,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("V4 credential pool JSON is invalid") from error
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "pool_id",
        "slots",
    }:
        raise ValueError("V4 credential pool schema is invalid")
    pool_id = payload.get("pool_id")
    slots = payload.get("slots")
    if (
        payload.get("schema_version") != 1
        or type(pool_id) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(pool_id) is None
        or not isinstance(slots, list)
        or not 1 <= len(slots) <= MAX_CREDENTIAL_POOL_SLOTS
    ):
        raise ValueError("V4 credential pool schema is invalid")
    slot_ids: set[str] = set()
    credential_paths: set[str] = set()
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {
            "slot_id",
            "credential_file",
        }:
            raise ValueError("V4 credential pool slot is invalid")
        slot_id = slot.get("slot_id")
        credential_file = slot.get("credential_file")
        if (
            type(slot_id) is not str
            or SAFE_CREDENTIAL_ID.fullmatch(slot_id) is None
            or type(credential_file) is not str
            or not Path(credential_file).is_absolute()
            or slot_id in slot_ids
            or credential_file in credential_paths
        ):
            raise ValueError("V4 credential pool slot is invalid")
        slot_ids.add(slot_id)
        credential_paths.add(credential_file)
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return payload, hashlib.sha256(canonical).hexdigest()


def _open_credential_source(operation_id: str) -> CredentialSource:
    if SAFE_CREDENTIAL_ID.fullmatch(operation_id) is None:
        raise ValueError("V4 operation id is invalid")
    credential_file = os.environ.get("AGY_GEMINI_V4_CREDENTIAL_FILE")
    pool_file = os.environ.get("AGY_GEMINI_V4_CREDENTIAL_POOL_FILE")
    if bool(credential_file) == bool(pool_file):
        raise ValueError("V4 credential configuration is ambiguous")
    if credential_file:
        return CredentialSource(
            descriptor=_open_private_credential_file(Path(credential_file)),
            pool_id="single-key-v1",
            slot_id="single",
            pool_sha256=hashlib.sha256(b"single-key-v1").hexdigest(),
        )
    assert pool_file is not None
    payload, pool_sha256 = _read_private_credential_pool(Path(pool_file))
    slots = sorted(payload["slots"], key=lambda slot: slot["slot_id"])
    selection_digest = hashlib.sha256(
        f"{payload['pool_id']}\0{operation_id}".encode("utf-8")
    ).digest()
    selected = slots[int.from_bytes(selection_digest[:8], "big") % len(slots)]
    return CredentialSource(
        descriptor=_open_private_credential_file(
            Path(selected["credential_file"])
        ),
        pool_id=str(payload["pool_id"]),
        slot_id=str(selected["slot_id"]),
        pool_sha256=pool_sha256,
    )


def _receipt_matches(
    receipt: object,
    *,
    operation_id: str,
    item_id: str,
    attempt_id: str,
    request_sha256: str,
    model: str,
    target_profile: str,
    executable_digest: str,
) -> bool:
    if type(receipt) is not ExecutionReceipt:
        return False
    if (
        receipt.operation_id,
        receipt.item_id,
        receipt.attempt_id,
        receipt.request_sha256,
        receipt.model,
        receipt.target_profile,
        receipt.executable_digest,
    ) != (
        operation_id,
        item_id,
        attempt_id,
        request_sha256,
        model,
        target_profile,
        executable_digest,
    ):
        return False
    if target_profile != GEMINI_STRUCTURED_API_PROFILE:
        return (
            receipt.pool_id,
            receipt.slot_id,
            receipt.pool_sha256,
        ) == (None, None, None)
    return (
        type(receipt.pool_id) is str
        and SAFE_CREDENTIAL_ID.fullmatch(receipt.pool_id) is not None
        and type(receipt.slot_id) is str
        and SAFE_CREDENTIAL_ID.fullmatch(receipt.slot_id) is not None
        and type(receipt.pool_sha256) is str
        and re.fullmatch(r"[0-9a-f]{64}", receipt.pool_sha256) is not None
    )


def _claim_next(queue_root: Path) -> Path | None:
    outbox = queue_root / "outbox"
    processing = queue_root / "processing"
    processing.mkdir(parents=True, exist_ok=True)
    for source in sorted(outbox.glob("*.json")) if outbox.exists() else []:
        target = processing / source.name
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue
        return target
    return None


def _schema_path_is_closed(
    response_schema: object,
    path: tuple[str | int, ...],
) -> bool:
    current = response_schema
    for token in path:
        if not isinstance(current, dict):
            return False
        if type(token) is str:
            if SAFE_SCHEMA_PATH_TOKEN.fullmatch(token) is None or current.get("type") != "object":
                return False
            properties = current.get("properties")
            if not isinstance(properties, dict) or token not in properties:
                return False
            current = properties[token]
        elif type(token) is int:
            if (
                token < 0
                or token > MAX_SCHEMA_ARRAY_INDEX
                or current.get("type") != "array"
            ):
                return False
            current = current.get("items")
        else:
            return False
    return isinstance(current, dict)


def _closed_schema_diagnostics(
    broker_result: object,
    response_schema: object,
) -> list[dict[str, object]]:
    if getattr(broker_result, "result_validation", None) != "SCHEMA_MISMATCH":
        return []
    diagnostics = getattr(broker_result, "schema_diagnostics", None)
    if type(diagnostics) is not tuple:
        return []
    closed: list[dict[str, object]] = []
    for diagnostic in diagnostics:
        if len(closed) >= MAX_SCHEMA_DIAGNOSTICS or type(diagnostic) is not SchemaDiagnostic:
            break
        keyword = diagnostic.keyword
        path = diagnostic.path
        if (
            type(keyword) is not str
            or keyword not in SCHEMA_DIAGNOSTIC_KEYWORDS
            or type(path) is not tuple
            or len(path) > MAX_SCHEMA_DIAGNOSTIC_DEPTH
            or not _schema_path_is_closed(response_schema, path)
        ):
            continue
        closed.append({"keyword": keyword, "path": list(path)})
    return closed


def _closed_broker_diagnostic(
    broker_result: object,
    response_schema: object,
) -> dict[str, object]:
    replay_status = getattr(broker_result, "replay_status", None)
    if type(replay_status) is not str or replay_status not in REPLAY_STATUS_STATES:
        replay_status = "INVALID"

    process_count = getattr(broker_result, "process_count", None)
    if (
        type(process_count) not in {int, str}
        or type(process_count) is bool
        or process_count not in PROCESS_COUNT_STATES
    ):
        process_count = "UNKNOWN"

    outcome = getattr(broker_result, "outcome", None)
    if outcome is not None and (type(outcome) is not str or outcome not in OUTCOME_STATES):
        outcome = None

    result_validation = getattr(broker_result, "result_validation", None)
    if type(result_validation) is not str or result_validation not in RESULT_VALIDATION_STATES:
        result_validation = "NOT_EVALUATED"

    diagnostic: dict[str, object] = {
        "replay_status": replay_status,
        "process_count": process_count,
        "outcome": outcome,
        "result_validation": result_validation,
    }
    schema_diagnostics = _closed_schema_diagnostics(broker_result, response_schema)
    if schema_diagnostics:
        diagnostic["schema_diagnostics"] = schema_diagnostics
    json_diagnostic = getattr(broker_result, "json_diagnostic", None)
    if (
        result_validation == "JSON_INVALID"
        and type(json_diagnostic) is str
        and json_diagnostic in JSON_DIAGNOSTIC_STATES
    ):
        diagnostic["json_diagnostic"] = json_diagnostic
    target_diagnostic = getattr(broker_result, "target_diagnostic", None)
    receipt = getattr(broker_result, "receipt", None)
    if (
        outcome == "CLI_NONZERO"
        and getattr(receipt, "target_profile", None) == GEMINI_STRUCTURED_API_PROFILE
        and type(target_diagnostic) is str
        and target_diagnostic in STRUCTURED_TARGET_DIAGNOSTICS
    ):
        diagnostic["target_diagnostic"] = target_diagnostic
    return diagnostic


def process_once(queue_root: Path, *, generate_json: GenerateJson = _cli_generate_json) -> dict[str, str]:
    claimed = _claim_next(queue_root)
    if claimed is None:
        return {"status": "idle"}
    processing_path = claimed
    job_id = processing_path.stem
    archive_path = queue_root / "archive" / f"{job_id}.json"
    request: dict[str, Any] = {}
    broker_diagnostic: dict[str, object] | None = None
    try:
        request = json.loads(processing_path.read_text(encoding="utf-8"))
        validate_external_request(request)
        if request["job_id"] != job_id:
            raise ValueError("request job id differs from queue filename")
        if os.environ.get("AGY_GEMINI_V4_BROKER") == "1":
            executable = Path(os.environ["AGY_GEMINI_V4_EXECUTABLE"])
            expected_executable_digest = os.environ["AGY_GEMINI_V4_EXECUTABLE_SHA256"]
            ledger_path = queue_root / "v4" / "ledger" / f"{job_id}.jsonl"
            target_profile = os.environ.get(
                "AGY_GEMINI_V4_PROFILE",
                GEMINI_STRUCTURED_API_PROFILE,
            )
            credential_fd: int | None = None
            credential_fd_opener: Callable[[], int] | None = None
            credential_source_opener: Callable[[], CredentialSource] | None = None
            if target_profile == GEMINI_STRUCTURED_API_PROFILE:
                credential_source_opener = lambda: _open_credential_source(job_id)
                raw_request = encode_target_request(
                    str(request["role"]),
                    str(request["prompt"]),
                    request["response_schema"],
                )
            elif target_profile == ANTIGRAVITY_CLI_PROFILE:
                if not ledger_path.exists():
                    raise ValueError("legacy V4 profile is replay-only")
                raw_request = _render_v4_effective_prompt(
                    str(request["role"]),
                    str(request["prompt"]),
                    request["response_schema"],
                )
            else:
                raise ValueError("AGY_GEMINI_V4_PROFILE is not approved")
            try:
                broker_result = run_single_shot(
                    operation_id=job_id,
                    item_id=str(request["namespace"]),
                    attempt_id="attempt-1",
                    request_sha256=str(request["request_sha256"]),
                    model=str(request["model"]),
                    executable=executable,
                    target_profile=target_profile,
                    expected_executable_digest=expected_executable_digest,
                    raw_request=raw_request,
                    response_schema=request["response_schema"],
                    timeout_milliseconds=120_000,
                    ledger_path=ledger_path,
                    anchor_store=FileAnchorStore(queue_root / "v4" / "anchors"),
                    credential_fd=credential_fd,
                    credential_fd_opener=credential_fd_opener,
                    credential_source_opener=credential_source_opener,
                )
            finally:
                if credential_fd is not None:
                    os.close(credential_fd)
            if (
                not _receipt_matches(
                    broker_result.receipt,
                    operation_id=job_id,
                    item_id=str(request["namespace"]),
                    attempt_id="attempt-1",
                    request_sha256=str(request["request_sha256"]),
                    model=str(request["model"]),
                    target_profile=target_profile,
                    executable_digest=expected_executable_digest,
                )
                or not broker_result.caller_contract_satisfied
                or broker_result.result is None
            ):
                broker_diagnostic = _closed_broker_diagnostic(
                    broker_result,
                    request["response_schema"],
                )
                raise V4BrokerFailure(
                    f"V4 fail closed: {broker_diagnostic['replay_status']}/"
                    f"{broker_diagnostic['process_count']}"
                )
            result = broker_result.result
        else:
            result = generate_json(
                str(request["role"]),
                str(request["model"]),
                str(request["prompt"]),
                request["response_schema"],
            )
        atomic_write_json(
            queue_root / "inbox" / f"{job_id}.json",
            {
                "schema_version": SCHEMA_VERSION,
                "job_id": job_id,
                "request_sha256": request["request_sha256"],
                "model": request["model"],
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "result": result,
            },
        )
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        return {"status": "processed", "job_id": job_id}
    except Exception as error:
        failed_record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "request_sha256": request.get("request_sha256"),
            "error_type": type(error).__name__,
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        if isinstance(error, V4BrokerFailure) and broker_diagnostic is not None:
            failed_record["broker_diagnostic"] = broker_diagnostic
        atomic_write_json(queue_root / "failed" / f"{job_id}.json", failed_record)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        return {"status": "failed", "job_id": job_id, "error_type": type(error).__name__}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("process-once")
    drain = subparsers.add_parser("drain")
    drain.add_argument("--max-jobs", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue_root = args.queue_root.resolve()
    if args.command == "process-once":
        result = process_once(queue_root)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result["status"] == "failed" else 0
    results = []
    for _ in range(args.max_jobs):
        result = process_once(queue_root)
        results.append(result)
        if result["status"] in {"idle", "failed"}:
            break
    print(json.dumps({"results": results}, ensure_ascii=False))
    return 1 if any(item["status"] == "failed" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

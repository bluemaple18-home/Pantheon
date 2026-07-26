#!/usr/bin/env python3
"""處理 sanitized Gemini outbox；本腳本由使用者自行啟用的 runner 執行。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Final

from scripts.agy_gemini_outbox import (
    SCHEMA_VERSION,
    atomic_write_json,
    validate_external_request,
)
from scripts.agy_seo_copy_pipeline import CLOSED_GEMINI_ERROR_CODES, GeminiClient
from scripts.agy_gemini_v4_broker import (
    ANTIGRAVITY_CLI_PROFILE,
    ExecutionReceipt,
    FileAnchorStore,
    V4BrokerFailure,
    RESULT_VALIDATION_STATES,
    SchemaDiagnostic,
    run_single_shot,
)


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
    "maxItems",
    "maxLength",
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
STALE_PROCESSING_SECONDS = 10 * 60
MAX_CREDENTIAL_POOL_BYTES = 16 * 1024
SAFE_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SAFE_JOB_ID = re.compile(r"^[0-9a-f]{40}$")
V4_ROLE_INSTRUCTIONS: Final = {
    "writer": "你是 Pantheon 繁體中文文章 Writer。只輸出符合 schema 的 JSON，不得加入未提供的事實或承諾。",
    "reviewer": "你是獨立 Pantheon 文章 Reviewer。依規範嚴格審查，只輸出符合 schema 的 JSON；不得假設 Writer 對話內容。",
}


@dataclass(frozen=True)
class ProductionCredentialSource:
    descriptor: int
    pool_id: str
    slot_id: str
    manifest_sha256: str


def _private_file_stat(path: Path, *, minimum_size: int, maximum_size: int) -> os.stat_result:
    try:
        current = path.lstat()
    except OSError as error:
        raise ValueError("production credential file is unavailable") from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or current.st_uid != os.getuid()
        or current.st_mode & 0o077
        or not minimum_size <= current.st_size <= maximum_size
    ):
        raise ValueError("production credential file must be owner-only regular file")
    return current


def _open_private_file(path: Path, *, minimum_size: int, maximum_size: int) -> int:
    before = _private_file_stat(
        path,
        minimum_size=minimum_size,
        maximum_size=maximum_size,
    )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("production credential file cannot be opened") from error
    try:
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_uid != os.getuid()
            or after.st_mode & 0o077
            or not minimum_size <= after.st_size <= maximum_size
        ):
            raise ValueError("production credential file changed during validation")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_descriptor(descriptor: int, *, expected_size: int, maximum_size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) <= maximum_size:
        chunk = os.read(descriptor, min(4096, maximum_size + 1 - len(chunks)))
        if not chunk:
            break
        chunks.extend(chunk)
    encoded = bytes(chunks)
    if len(encoded) != expected_size:
        raise ValueError("production credential file size changed")
    return encoded


def _read_production_pool(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_absolute():
        raise ValueError("production credential pool path must be absolute")
    descriptor = _open_private_file(path, minimum_size=2, maximum_size=MAX_CREDENTIAL_POOL_BYTES)
    try:
        size = os.fstat(descriptor).st_size
        encoded = _read_descriptor(
            descriptor,
            expected_size=size,
            maximum_size=MAX_CREDENTIAL_POOL_BYTES,
        )
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(
            encoded,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("production credential pool JSON is invalid") from error
    if not isinstance(payload, dict) or set(payload) != {
        "pool_id",
        "schema_version",
        "slots",
    }:
        raise ValueError("production credential pool schema is invalid")
    pool_id = payload.get("pool_id")
    slots = payload.get("slots")
    if (
        type(payload.get("schema_version")) is not int
        or payload.get("schema_version") != 1
        or type(pool_id) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(pool_id) is None
        or not isinstance(slots, list)
        or len(slots) != 3
    ):
        raise ValueError("production credential pool schema is invalid")
    slot_ids: set[str] = set()
    credential_paths: set[str] = set()
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"credential_file", "slot_id"}:
            raise ValueError("production credential pool slot is invalid")
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
            raise ValueError("production credential pool slot is invalid")
        _private_file_stat(Path(credential_file), minimum_size=20, maximum_size=512)
        slot_ids.add(slot_id)
        credential_paths.add(credential_file)
    canonical_payload = {
        "pool_id": pool_id,
        "schema_version": payload["schema_version"],
        "slots": sorted(slots, key=lambda slot: slot["slot_id"]),
    }
    canonical = json.dumps(
        canonical_payload,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return payload, hashlib.sha256(canonical).hexdigest()


def _open_production_credential_source(
    manifest_path: Path,
    job_id: str,
) -> ProductionCredentialSource:
    if SAFE_JOB_ID.fullmatch(job_id) is None:
        raise ValueError("production credential job id is invalid")
    payload, manifest_sha256 = _read_production_pool(manifest_path)
    slots = sorted(payload["slots"], key=lambda slot: slot["slot_id"])
    digest = hashlib.sha256(f"{payload['pool_id']}\0{job_id}".encode("utf-8")).digest()
    selected = slots[int.from_bytes(digest[:8], "big") % len(slots)]
    return ProductionCredentialSource(
        descriptor=_open_private_file(
            Path(selected["credential_file"]),
            minimum_size=20,
            maximum_size=512,
        ),
        pool_id=str(payload["pool_id"]),
        slot_id=str(selected["slot_id"]),
        manifest_sha256=manifest_sha256,
    )


def _read_production_api_key(descriptor: int) -> str:
    size = os.fstat(descriptor).st_size
    encoded = _read_descriptor(descriptor, expected_size=size, maximum_size=512)
    try:
        api_key = encoded.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise ValueError("production credential value is invalid") from error
    if (
        not 20 <= len(api_key) <= 512
        or re.fullmatch(r"[A-Za-z0-9_-]+", api_key) is None
    ):
        raise ValueError("production credential value is invalid")
    return api_key


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


def _requeue_stale_processing(queue_root: Path) -> None:
    """回收 worker 中斷後遺留的 processing 工作。"""
    processing = queue_root / "processing"
    outbox = queue_root / "outbox"
    if not processing.exists():
        return
    cutoff = time.time() - STALE_PROCESSING_SECONDS
    for source in sorted(processing.glob("*.json")):
        try:
            if source.stat().st_mtime > cutoff:
                continue
        except FileNotFoundError:
            continue
        target = outbox / source.name
        if target.exists():
            continue
        outbox.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue


def _claim_next(queue_root: Path) -> Path | None:
    _requeue_stale_processing(queue_root)
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
    return diagnostic


def _closed_error_code(error: BaseException) -> str | None:
    error_code = getattr(error, "error_code", None)
    if type(error_code) is str and error_code in CLOSED_GEMINI_ERROR_CODES:
        return error_code
    return None


def process_once(queue_root: Path, *, generate_json: GenerateJson = _cli_generate_json) -> dict[str, Any]:
    claimed = _claim_next(queue_root)
    if claimed is None:
        return {"status": "idle"}
    processing_path = claimed
    job_id = processing_path.stem
    archive_path = queue_root / "archive" / f"{job_id}.json"
    request: dict[str, Any] = {}
    broker_diagnostic: dict[str, object] | None = None
    credential_pool: dict[str, str] | None = None
    try:
        request = json.loads(processing_path.read_text(encoding="utf-8"))
        validate_external_request(request)
        if request["job_id"] != job_id:
            raise ValueError("request job id differs from queue filename")
        if os.environ.get("AGY_GEMINI_V4_BROKER") == "1":
            executable = Path(os.environ["AGY_GEMINI_V4_EXECUTABLE"])
            expected_executable_digest = os.environ["AGY_GEMINI_V4_EXECUTABLE_SHA256"]
            broker_result = run_single_shot(
                operation_id=job_id,
                item_id=str(request["namespace"]),
                attempt_id="attempt-1",
                request_sha256=str(request["request_sha256"]),
                model=str(request["model"]),
                executable=executable,
                target_profile=ANTIGRAVITY_CLI_PROFILE,
                expected_executable_digest=expected_executable_digest,
                raw_request=_render_v4_effective_prompt(
                    str(request["role"]),
                    str(request["prompt"]),
                    request["response_schema"],
                ),
                response_schema=request["response_schema"],
                timeout_milliseconds=120_000,
                ledger_path=queue_root / "v4" / "ledger" / f"{job_id}.jsonl",
                anchor_store=FileAnchorStore(queue_root / "v4" / "anchors"),
            )
            expected_receipt = ExecutionReceipt(
                job_id,
                str(request["namespace"]),
                "attempt-1",
                str(request["request_sha256"]),
                str(request["model"]),
                ANTIGRAVITY_CLI_PROFILE,
                expected_executable_digest,
            )
            if (
                broker_result.receipt != expected_receipt
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
        elif pool_file := os.environ.get("AGY_GEMINI_CREDENTIAL_POOL_FILE", "").strip():
            source = _open_production_credential_source(Path(pool_file), job_id)
            credential_pool = {
                "pool_id": source.pool_id,
                "slot_id": source.slot_id,
                "manifest_sha256": source.manifest_sha256,
            }
            try:
                api_key = _read_production_api_key(source.descriptor)
            finally:
                os.close(source.descriptor)
            client = GeminiClient(
                api_key,
                writer_model=str(request["model"]) if request["role"] == "writer" else None,
                reviewer_model=str(request["model"]) if request["role"] == "reviewer" else None,
            )
            client.transport = client._single_request_http_transport
            result = client.generate_json(
                str(request["role"]),
                str(request["prompt"]),
                request["response_schema"],
            )
        else:
            result = generate_json(
                str(request["role"]),
                str(request["model"]),
                str(request["prompt"]),
                request["response_schema"],
            )
        response_record = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "request_sha256": request["request_sha256"],
            "model": request["model"],
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "result": result,
        }
        if credential_pool is not None:
            response_record["credential_pool"] = credential_pool
        atomic_write_json(queue_root / "inbox" / f"{job_id}.json", response_record)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        processed: dict[str, Any] = {"status": "processed", "job_id": job_id}
        if credential_pool is not None:
            processed["credential_pool"] = credential_pool
        return processed
    except Exception as error:
        failed_record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "request_sha256": request.get("request_sha256"),
            "error_type": type(error).__name__,
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        error_code = _closed_error_code(error)
        if error_code is not None:
            failed_record["error_code"] = error_code
        if isinstance(error, V4BrokerFailure) and broker_diagnostic is not None:
            failed_record["broker_diagnostic"] = broker_diagnostic
        if credential_pool is not None:
            failed_record["credential_pool"] = credential_pool
        atomic_write_json(queue_root / "failed" / f"{job_id}.json", failed_record)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        result = {"status": "failed", "job_id": job_id, "error_type": type(error).__name__}
        if error_code is not None:
            result["error_code"] = error_code
        if credential_pool is not None:
            result["credential_pool"] = credential_pool
        return result


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

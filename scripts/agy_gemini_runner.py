#!/usr/bin/env python3
"""處理 sanitized Gemini outbox；本腳本由使用者自行啟用的 runner 執行。"""

from __future__ import annotations

import argparse
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
            target_profile = os.environ.get(
                "AGY_GEMINI_V4_PROFILE",
                ANTIGRAVITY_CLI_PROFILE,
            )
            credential_fd: int | None = None
            if target_profile == GEMINI_STRUCTURED_API_PROFILE:
                credential_path = Path(os.environ["AGY_GEMINI_V4_CREDENTIAL_FILE"])
                credential_fd = _open_private_credential_file(credential_path)
                raw_request = encode_target_request(
                    str(request["role"]),
                    str(request["prompt"]),
                    request["response_schema"],
                )
            elif target_profile == ANTIGRAVITY_CLI_PROFILE:
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
                    ledger_path=queue_root / "v4" / "ledger" / f"{job_id}.jsonl",
                    anchor_store=FileAnchorStore(queue_root / "v4" / "anchors"),
                    credential_fd=credential_fd,
                )
            finally:
                if credential_fd is not None:
                    os.close(credential_fd)
            expected_receipt = ExecutionReceipt(
                job_id,
                str(request["namespace"]),
                "attempt-1",
                str(request["request_sha256"]),
                str(request["model"]),
                target_profile,
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

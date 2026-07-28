#!/usr/bin/env python3
"""以純公開 payload 串接 Pantheon pipeline 與外部 Gemini runner。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
OUTBOX_MAX_REPAIRS = 2
OUTBOX_MAX_TRANSPORT_RETRIES = 2
RETRYABLE_EXTERNAL_ERRORS = {"JSONDecodeError"}
CLOSED_EXTERNAL_ERROR_CODES = pipeline.CLOSED_GEMINI_ERROR_CODES
INVALID_FAILURE_RECEIPT = "InvalidFailureReceipt"
CLOSED_EXTERNAL_ERROR_TYPES = frozenset({
    "GeminiApiFailure",
    "GeminiCliFailure",
    INVALID_FAILURE_RECEIPT,
    "JSONDecodeError",
    "RuntimeError",
    "V4BrokerFailure",
    "ValueError",
})
FAILURE_RECEIPT_BASE_FIELDS = frozenset({
    "schema_version",
    "job_id",
    "request_sha256",
    "error_type",
    "completed_at",
})
FAILURE_RECEIPT_OPTIONAL_FIELDS = frozenset({
    "broker_diagnostic",
    "credential_pool",
    "error_code",
})
FAILURE_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}$"
)
BROKER_REPLAY_STATES = frozenset({"COMPLETE", "BLOCKED", "AMBIGUOUS", "INVALID"})
BROKER_PROCESS_COUNTS = frozenset({0, 1, "UNKNOWN"})
BROKER_OUTCOMES = frozenset({
    None,
    "CLI_NOT_FOUND",
    "CRASH_BEFORE_FORK",
    "PERMISSION_DENIED",
    "EXEC_FORMAT",
    "EXEC_RACE",
    "SUCCESS",
    "CLI_NONZERO",
    "CLI_TIMEOUT",
})
BROKER_RESULT_VALIDATIONS = frozenset({
    "NOT_EVALUATED",
    "JSON_INVALID",
    "NOT_OBJECT",
    "SCHEMA_MISMATCH",
    "VALID",
})
BROKER_JSON_DIAGNOSTICS = frozenset({
    "EMPTY",
    "UTF8_INVALID",
    "MARKDOWN_FENCE",
    "WRAPPED_JSON",
    "PARSE_ERROR_AT_END",
    "PARSE_ERROR_OTHER",
})
BROKER_SCHEMA_KEYWORDS = frozenset({
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
SAFE_DIAGNOSTIC_PATH_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
SAFE_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_PROMPT_BYTES = 256 * 1024
MAX_SCHEMA_BYTES = 64 * 1024
MAX_FAILURE_RECEIPT_BYTES = 64 * 1024
NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
FORBIDDEN_EXTERNAL_PATTERNS = (
    re.compile(r"/(?:Users|home|private|var|tmp)/"),
    re.compile(r"\.work/"),
    re.compile(r"GEMINI_API_KEY", re.IGNORECASE),
    re.compile(r"x-goog-api-key", re.IGNORECASE),
    re.compile(r"authorization\s*:\s*bearer", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?:ghp|github_pat)_[0-9A-Za-z_]{20,}"),
)


class ExternalJobPending(RuntimeError):
    """外部 runner 尚未回傳此 job。"""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"external job pending: {job_id}")


class ExternalJobFailed(RuntimeError):
    """外部 runner 已記錄失敗。"""

    def __init__(self, job_id: str, error_type: str, error_code: str | None = None) -> None:
        self.job_id = job_id
        self.error_type = (
            error_type
            if type(error_type) is str and error_type in CLOSED_EXTERNAL_ERROR_TYPES
            else INVALID_FAILURE_RECEIPT
        )
        self.error_code = (
            error_code
            if type(error_code) is str and error_code in CLOSED_EXTERNAL_ERROR_CODES
            else None
        )
        super().__init__(f"external job failed: {job_id} ({self.error_type})")


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_write_json(path: Path, payload: object) -> None:
    """同目錄暫存後原子替換，避免 runner 讀到半份 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(_json_bytes(payload) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def _assert_external_payload_is_public(prompt: str, response_schema: dict[str, Any]) -> None:
    prompt_bytes = prompt.encode("utf-8")
    schema_bytes = _json_bytes(response_schema)
    if len(prompt_bytes) > MAX_PROMPT_BYTES:
        raise ValueError("external prompt exceeds 256 KB")
    if len(schema_bytes) > MAX_SCHEMA_BYTES:
        raise ValueError("external schema exceeds 64 KB")
    serialized = prompt + "\n" + schema_bytes.decode("utf-8")
    if any(pattern.search(serialized) for pattern in FORBIDDEN_EXTERNAL_PATTERNS):
        raise ValueError("external payload contains forbidden private data")


def _request_core(
    *,
    namespace: str,
    role: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    if not NAMESPACE_PATTERN.fullmatch(namespace):
        raise ValueError("namespace must be opaque and path-free")
    if role not in {"writer", "reviewer"}:
        raise ValueError("role must be writer or reviewer")
    if not model.strip():
        raise ValueError("model must be non-empty")
    _assert_external_payload_is_public(prompt, response_schema)
    return {
        "schema_version": SCHEMA_VERSION,
        "namespace": namespace,
        "role": role,
        "model": model,
        "thinking_level": "LOW",
        "operation_level": "external_generation",
        "prompt": prompt,
        "response_schema": response_schema,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(_json_bytes(response_schema)).hexdigest(),
    }


def build_external_request(
    *,
    namespace: str,
    role: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    core = _request_core(
        namespace=namespace,
        role=role,
        model=model,
        prompt=prompt,
        response_schema=response_schema,
    )
    request_sha256 = hashlib.sha256(_json_bytes(core)).hexdigest()
    return {**core, "job_id": request_sha256[:40], "request_sha256": request_sha256}


def validate_external_request(request: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "namespace",
        "role",
        "model",
        "thinking_level",
        "operation_level",
        "prompt",
        "response_schema",
        "prompt_sha256",
        "schema_sha256",
        "job_id",
        "request_sha256",
    }
    if set(request) != required:
        raise ValueError("external request fields are strict")
    rebuilt = build_external_request(
        namespace=str(request["namespace"]),
        role=str(request["role"]),
        model=str(request["model"]),
        prompt=str(request["prompt"]),
        response_schema=request["response_schema"],
    )
    if request != rebuilt:
        raise ValueError("external request hash mismatch")


def create_external_request(
    queue_root: Path,
    *,
    namespace: str,
    role: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    request = build_external_request(
        namespace=namespace,
        role=role,
        model=model,
        prompt=prompt,
        response_schema=response_schema,
    )
    job_id = request["job_id"]
    known_paths = [
        queue_root / "outbox" / f"{job_id}.json",
        queue_root / "processing" / f"{job_id}.json",
        queue_root / "archive" / f"{job_id}.json",
    ]
    for path in known_paths:
        if not path.exists():
            continue
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != request:
            raise ValueError(f"external job collision: {job_id}")
        return request
    atomic_write_json(known_paths[0], request)
    return request


def _broker_diagnostic_is_closed(value: object) -> bool:
    if type(value) is not dict:
        return False
    required = {"replay_status", "process_count", "outcome", "result_validation"}
    optional = {"json_diagnostic", "schema_diagnostics"}
    if not required <= set(value) or not set(value) <= required | optional:
        return False
    replay_status = value.get("replay_status")
    process_count = value.get("process_count")
    outcome = value.get("outcome")
    result_validation = value.get("result_validation")
    if (
        type(replay_status) is not str
        or replay_status not in BROKER_REPLAY_STATES
        or type(process_count) not in {int, str}
        or type(process_count) is bool
        or process_count not in BROKER_PROCESS_COUNTS
        or (outcome is not None and type(outcome) is not str)
        or outcome not in BROKER_OUTCOMES
        or type(result_validation) is not str
        or result_validation not in BROKER_RESULT_VALIDATIONS
    ):
        return False
    if "json_diagnostic" in value:
        json_diagnostic = value.get("json_diagnostic")
        if type(json_diagnostic) is not str or json_diagnostic not in BROKER_JSON_DIAGNOSTICS:
            return False
    diagnostics = value.get("schema_diagnostics", [])
    if type(diagnostics) is not list or len(diagnostics) > 3:
        return False
    for diagnostic in diagnostics:
        if type(diagnostic) is not dict or set(diagnostic) != {"keyword", "path"}:
            return False
        keyword = diagnostic.get("keyword")
        if type(keyword) is not str or keyword not in BROKER_SCHEMA_KEYWORDS:
            return False
        path = diagnostic.get("path")
        if type(path) is not list or len(path) > 8:
            return False
        for token in path:
            if type(token) is str:
                if SAFE_DIAGNOSTIC_PATH_TOKEN.fullmatch(token) is None:
                    return False
            elif type(token) is int:
                if token < 0 or token > 1_048_576:
                    return False
            else:
                return False
    return True


def _credential_pool_identity_is_closed(value: object) -> bool:
    if type(value) is not dict or set(value) != {
        "manifest_sha256",
        "pool_id",
        "slot_id",
    }:
        return False
    return (
        type(value.get("pool_id")) is str
        and SAFE_CREDENTIAL_ID.fullmatch(value["pool_id"]) is not None
        and type(value.get("slot_id")) is str
        and SAFE_CREDENTIAL_ID.fullmatch(value["slot_id"]) is not None
        and type(value.get("manifest_sha256")) is str
        and SHA256_PATTERN.fullmatch(value["manifest_sha256"]) is not None
    )


def _failure_receipt_is_valid(
    failure: object,
    request: dict[str, Any],
) -> bool:
    if type(failure) is not dict:
        return False
    fields = set(failure)
    if (
        not FAILURE_RECEIPT_BASE_FIELDS <= fields
        or not fields <= FAILURE_RECEIPT_BASE_FIELDS | FAILURE_RECEIPT_OPTIONAL_FIELDS
        or type(failure.get("schema_version")) is not int
        or failure.get("schema_version") != SCHEMA_VERSION
        or failure.get("job_id") != request["job_id"]
        or failure.get("request_sha256") != request["request_sha256"]
        or type(failure.get("error_type")) is not str
        or failure.get("error_type") not in CLOSED_EXTERNAL_ERROR_TYPES
        or not _failure_timestamp_is_valid(failure.get("completed_at"))
    ):
        return False
    error_code = failure.get("error_code")
    if "error_code" in failure and (
        failure.get("error_type") not in {"GeminiApiFailure", "GeminiCliFailure"}
        or type(error_code) is not str
        or error_code not in CLOSED_EXTERNAL_ERROR_CODES
    ):
        return False
    broker_diagnostic = failure.get("broker_diagnostic")
    if ("broker_diagnostic" in failure) != (failure.get("error_type") == "V4BrokerFailure"):
        return False
    credential_pool = failure.get("credential_pool")
    return (
        ("broker_diagnostic" not in failure or _broker_diagnostic_is_closed(broker_diagnostic))
        and (
            "credential_pool" not in failure
            or _credential_pool_identity_is_closed(credential_pool)
        )
    )


def _failure_timestamp_is_valid(value: object) -> bool:
    if type(value) is not str or FAILURE_TIMESTAMP_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def consume_external_response(queue_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    validate_external_request(request)
    job_id = str(request["job_id"])
    failed_path = queue_root / "failed" / f"{job_id}.json"
    if failed_path.exists():
        try:
            if failed_path.stat().st_size > MAX_FAILURE_RECEIPT_BYTES:
                raise ValueError("failure receipt exceeds closed size")
            failure = json.loads(failed_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
            raise ExternalJobFailed(job_id, INVALID_FAILURE_RECEIPT) from None
        if not _failure_receipt_is_valid(failure, request):
            raise ExternalJobFailed(job_id, INVALID_FAILURE_RECEIPT)
        raise ExternalJobFailed(
            job_id,
            failure["error_type"],
            failure.get("error_code") if type(failure.get("error_code")) is str else None,
        )
    response_path = queue_root / "inbox" / f"{job_id}.json"
    if not response_path.exists():
        raise ExternalJobPending(job_id)
    response = json.loads(response_path.read_text(encoding="utf-8"))
    required = {"schema_version", "job_id", "request_sha256", "model", "completed_at", "result"}
    optional = {"credential_pool"}
    if (
        not required <= set(response)
        or not set(response) <= required | optional
        or response.get("schema_version") != SCHEMA_VERSION
        or (
            "credential_pool" in response
            and not _credential_pool_identity_is_closed(response["credential_pool"])
        )
    ):
        raise ValueError("external response fields are strict")
    if response["job_id"] != job_id:
        raise ValueError("response job id mismatch")
    if response["request_sha256"] != request["request_sha256"]:
        raise ValueError("response request hash mismatch")
    if response["model"] != request["model"]:
        raise ValueError("response model mismatch")
    return response["result"]


def _request_is_known(queue_root: Path, job_id: str) -> bool:
    return any(
        (queue_root / directory / f"{job_id}.json").exists()
        for directory in ("outbox", "processing", "archive", "inbox", "failed")
    )


def _model_from_environment(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


class OutboxGeminiClient:
    """只寫 sanitized request；不持有憑證，也不直接呼叫外部服務。"""

    def __init__(
        self,
        queue_root: Path,
        *,
        legacy_queue_root: Path | None = None,
        namespace: str,
        writer_model: str = pipeline.DEFAULT_WRITER_MODEL,
        reviewer_model: str = pipeline.DEFAULT_REVIEWER_MODEL,
    ) -> None:
        self.queue_root = queue_root
        self.legacy_queue_root = legacy_queue_root
        self.namespace = namespace
        self.writer_model = writer_model
        self.reviewer_model = reviewer_model
        self.transport = self._outbox_transport

    def _outbox_transport(self) -> None:
        raise RuntimeError("outbox transport is represented by generate_json")

    def generate_json(self, role: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        model = self.writer_model if role == "writer" else self.reviewer_model
        for retry_index in range(OUTBOX_MAX_TRANSPORT_RETRIES + 1):
            namespace = self.namespace if retry_index == 0 else f"{self.namespace}-r{retry_index}"
            expected = build_external_request(
                namespace=namespace,
                role=role,
                model=model,
                prompt=prompt,
                response_schema=schema,
            )
            request_root = self.queue_root
            if (
                self.legacy_queue_root is not None
                and _request_is_known(self.legacy_queue_root, str(expected["job_id"]))
            ):
                request_root = self.legacy_queue_root
            request = create_external_request(
                request_root,
                namespace=namespace,
                role=role,
                model=model,
                prompt=prompt,
                response_schema=schema,
            )
            try:
                return consume_external_response(request_root, request)
            except ExternalJobFailed as failed:
                if failed.error_type not in RETRYABLE_EXTERNAL_ERRORS or retry_index >= OUTBOX_MAX_TRANSPORT_RETRIES:
                    raise
        raise RuntimeError("unreachable external transport retry state")


def run_pipeline_tick(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    run_id = str(brief["run_id"])
    namespace = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    legacy_queue_root = queue_root.parent.parent if queue_root.parent.name == "lanes" else None
    client = OutboxGeminiClient(
        queue_root,
        legacy_queue_root=legacy_queue_root,
        namespace=namespace,
        writer_model=_model_from_environment(
            "AGY_WRITER_MODEL",
            pipeline.DEFAULT_WRITER_MODEL,
        ),
        reviewer_model=_model_from_environment(
            "AGY_REVIEWER_MODEL",
            pipeline.DEFAULT_REVIEWER_MODEL,
        ),
    )
    runner = multilingual.run_writer_reviewer if brief.get("mode") == "translate_existing" else pipeline.run_writer_reviewer
    candidate, review = runner(run_dir, client, max_repairs=OUTBOX_MAX_REPAIRS)
    return {
        "status": "complete",
        "run_id": run_id,
        "approved_by_reviewer": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
        "candidate": str(run_dir / "candidate.json"),
        "review": str(run_dir / "review.md"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    tick = subparsers.add_parser("tick")
    tick.add_argument("run_dir", type=Path)
    tick.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_pipeline_tick(args.run_dir.resolve(), args.queue_root.resolve())
    except ExternalJobPending as pending:
        print(json.dumps({"status": "pending", "job_id": pending.job_id}, ensure_ascii=False))
        return 75
    except ExternalJobFailed as failed:
        result = {"status": "failed", "job_id": failed.job_id, "error_type": failed.error_type}
        if failed.error_code is not None:
            result["error_code"] = failed.error_code
        print(json.dumps(result, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

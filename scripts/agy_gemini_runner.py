#!/usr/bin/env python3
"""處理 sanitized Gemini outbox；本腳本由使用者自行啟用的 runner 執行。"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Final

from scripts.agy_gemini_outbox import (
    SCHEMA_VERSION,
    atomic_write_json,
    classify_external_failure,
    validate_external_request,
)
from scripts.agy_gemini_allocator import (
    MAX_RATE_LIMIT_COOLDOWN_SECONDS,
    ProductionSlotAdmission,
    RATE_LIMIT_REASON,
    allocate_production_slot,
    production_slot_admission,
    record_production_rate_limit,
    validate_production_allocator_installation,
)
from scripts.agy_seo_copy_pipeline import (
    CLOSED_GEMINI_ERROR_CODES,
    GeminiClient,
    closed_gemini_http_diagnostic,
    normalize_new_output_contract,
)
from scripts.agy_gemini_v4_broker import (
    ANTIGRAVITY_CLI_PROFILE,
    ExecutionReceipt,
    FileAnchorStore,
    V4BrokerFailure,
    RESULT_VALIDATION_STATES,
    SchemaDiagnostic,
    _diagnose_json_schema,
    run_single_shot,
)
from scripts import pantheon_content_runtime_manifest as formal_runtime


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
MAX_PRODUCTION_ATTEMPT_BYTES = 4 * 1024
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 5 * 60
SAFE_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SAFE_ATTEMPT_JOB_ID = re.compile(r"^[0-9a-f]{40,64}$")
SAFE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRODUCTION_SLOT_IDS = ("account-1", "account-2", "account-3")
CONTENT_LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
EXACT_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PRODUCTION_ATTEMPT_STATES = frozenset({"started", "succeeded", "failed"})
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
    ordinal: int


def _normalize_exact_run_ids(
    run_ids: Iterable[str] | None,
) -> frozenset[str] | None:
    if run_ids is None:
        return None
    if isinstance(run_ids, str):
        raise ValueError("exact run ids must be a collection")
    values = tuple(run_ids)
    if not values:
        raise ValueError("exact run ids must not be empty")
    if any(
        type(run_id) is not str or EXACT_RUN_ID_PATTERN.fullmatch(run_id) is None
        for run_id in values
    ):
        raise ValueError("exact run id format is invalid")
    if len(values) != len(set(values)):
        raise ValueError("exact run ids must be unique")
    return frozenset(values)


class ProductionAttemptEvidenceError(ValueError):
    """Production at-most-once evidence 不可信時的封閉錯誤。"""


class ProductionAttemptReplay(RuntimeError):
    """同一 production job 已有可信 attempt evidence。"""


@dataclass
class ProductionAttemptEvidence:
    directory_descriptor: int
    marker_descriptor: int
    marker_path: Path
    job_id: str
    request_sha256: str
    attempt_status: str
    is_new: bool


def _private_file_stat(
    path: Path,
    *,
    minimum_size: int,
    maximum_size: int,
    label: str = "production credential file",
) -> os.stat_result:
    try:
        current = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or current.st_uid != os.getuid()
        or current.st_mode & 0o077
        or not minimum_size <= current.st_size <= maximum_size
    ):
        raise ValueError(f"{label} must be owner-only regular file")
    return current


def _open_private_file(
    path: Path,
    *,
    minimum_size: int,
    maximum_size: int,
    label: str = "production credential file",
) -> int:
    before = _private_file_stat(
        path,
        minimum_size=minimum_size,
        maximum_size=maximum_size,
        label=label,
    )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"{label} cannot be opened") from error
    try:
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_uid != os.getuid()
            or after.st_mode & 0o077
            or not minimum_size <= after.st_size <= maximum_size
        ):
            raise ValueError(f"{label} changed during validation")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_descriptor(
    descriptor: int,
    *,
    expected_size: int,
    maximum_size: int,
    label: str = "production credential file",
) -> bytes:
    chunks = bytearray()
    while len(chunks) <= maximum_size:
        chunk = os.read(descriptor, min(4096, maximum_size + 1 - len(chunks)))
        if not chunk:
            break
        chunks.extend(chunk)
    encoded = bytes(chunks)
    if len(encoded) != expected_size:
        raise ValueError(f"{label} size changed")
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
    if slot_ids != set(PRODUCTION_SLOT_IDS):
        raise ValueError("production credential pool slot ids are invalid")
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


def _allocate_production_credential_source(
    manifest_path: Path,
    state_path: Path,
) -> ProductionCredentialSource:
    if not state_path.is_absolute():
        raise ValueError("production allocator state path must be absolute")
    payload, manifest_sha256 = _read_production_pool(manifest_path)
    slots = sorted(payload["slots"], key=lambda slot: slot["slot_id"])
    ordinal, selected_slot = allocate_production_slot(
        state_path,
        pool_id=str(payload["pool_id"]),
        manifest_sha256=manifest_sha256,
    )
    selected = next(slot for slot in slots if slot["slot_id"] == selected_slot)
    return ProductionCredentialSource(
        descriptor=_open_private_file(
            Path(selected["credential_file"]),
            minimum_size=20,
            maximum_size=512,
        ),
        pool_id=str(payload["pool_id"]),
        slot_id=str(selected["slot_id"]),
        manifest_sha256=manifest_sha256,
        ordinal=ordinal,
    )


def _credential_from_admission(
    payload: dict[str, Any],
    manifest_sha256: str,
    admission: ProductionSlotAdmission,
) -> tuple[str, dict[str, str]]:
    slots = sorted(payload["slots"], key=lambda slot: slot["slot_id"])
    selected = next(slot for slot in slots if slot["slot_id"] == admission.slot_id)
    _ordinal, selected_slot = admission.commit()
    descriptor = _open_private_file(
        Path(selected["credential_file"]),
        minimum_size=20,
        maximum_size=512,
    )
    try:
        api_key = _read_production_api_key(descriptor)
    finally:
        os.close(descriptor)
    return api_key, {
        "pool_id": str(payload["pool_id"]),
        "slot_id": selected_slot,
        "manifest_sha256": manifest_sha256,
    }


def _production_cooldown_seconds() -> int:
    raw = os.environ.get(
        "AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS",
        str(DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS),
    )
    if re.fullmatch(r"[1-9][0-9]*", raw) is None:
        raise ValueError("production cooldown duration is invalid")
    seconds = int(raw)
    if seconds > MAX_RATE_LIMIT_COOLDOWN_SECONDS:
        raise ValueError("production cooldown duration is invalid")
    return seconds


def _new_only_enabled() -> bool:
    raw = os.environ.get("AGY_GEMINI_NEW_ONLY", "0")
    if raw not in {"0", "1"}:
        raise ValueError("AGY_GEMINI_NEW_ONLY must be 0 or 1")
    return raw == "1"


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


def validate_production_installation(
    manifest_path: Path,
    state_path: Path,
) -> None:
    """安裝前只驗 pool/state/lock 與 credential file metadata。"""
    payload, manifest_sha256 = _read_production_pool(manifest_path)
    validate_production_allocator_installation(
        state_path,
        pool_id=str(payload["pool_id"]),
        manifest_sha256=manifest_sha256,
    )


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


def _requeue_stale_processing(
    queue_root: Path,
    exact_namespaces: frozenset[str] | None = None,
) -> None:
    """回收 worker 中斷後遺留的 processing 工作。"""
    processing = queue_root / "processing"
    outbox = queue_root / "outbox"
    if not processing.exists():
        return
    cutoff = time.time() - STALE_PROCESSING_SECONDS
    for source in sorted(processing.glob("*.json")):
        if exact_namespaces is not None:
            try:
                selected_request = json.loads(source.read_text(encoding="utf-8"))
                validate_external_request(selected_request)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if str(selected_request["namespace"]) not in exact_namespaces:
                continue
        try:
            if source.stat().st_mtime > cutoff:
                continue
        except FileNotFoundError:
            continue
        attempt_marker = _production_attempt_marker(queue_root, source.stem)
        if attempt_marker.exists() or attempt_marker.is_symlink():
            request = json.loads(source.read_text(encoding="utf-8"))
            validate_external_request(request)
            if request["job_id"] != source.stem:
                raise ProductionAttemptEvidenceError(
                    "production attempt evidence identity mismatch"
                )
            attempt_evidence = _begin_production_attempt(queue_root, request)
            inbox_path = queue_root / "inbox" / source.name
            failed_path = queue_root / "failed" / source.name
            try:
                if not inbox_path.exists() and not failed_path.exists():
                    atomic_write_json(
                        failed_path,
                        {
                            "schema_version": SCHEMA_VERSION,
                            "job_id": source.stem,
                            "request_sha256": request.get("request_sha256"),
                            "error_type": "RuntimeError",
                            "completed_at": datetime.now().astimezone().isoformat(
                                timespec="seconds"
                            ),
                        },
                    )
                archive_path = queue_root / "archive" / source.name
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.replace(source, archive_path)
                except FileNotFoundError:
                    continue
                _finish_production_attempt(
                    attempt_evidence,
                    "succeeded" if inbox_path.exists() else "failed",
                )
            finally:
                _close_production_attempt(attempt_evidence)
            continue
        target = outbox / source.name
        if target.exists():
            continue
        outbox.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue


def _claim_next(
    queue_root: Path,
    exact_run_ids: Iterable[str] | None = None,
) -> Path | None:
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    exact_namespaces = (
        frozenset(
            hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
            for run_id in selected_run_ids
        )
        if selected_run_ids is not None
        else None
    )
    _requeue_stale_processing(queue_root, exact_namespaces)
    outbox = queue_root / "outbox"
    processing = queue_root / "processing"
    sources = list(outbox.glob("*.json")) if outbox.exists() else []
    if exact_namespaces is not None:
        selected_sources: list[Path] = []
        for source in sources:
            try:
                request = json.loads(source.read_text(encoding="utf-8"))
                validate_external_request(request)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if str(request["namespace"]) in exact_namespaces:
                selected_sources.append(source)
        sources = selected_sources
        if not sources:
            return None
    processing.mkdir(parents=True, exist_ok=True)

    def priority(source: Path) -> tuple[int, str]:
        try:
            request = json.loads(source.read_text(encoding="utf-8"))
            validate_external_request(request)
        except Exception:
            return 2, source.name
        return (0 if request["role"] == "reviewer" else 1), source.name

    for source in sorted(sources, key=priority):
        target = processing / source.name
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue
        return target
    return None


def _production_attempt_marker(queue_root: Path, job_id: str) -> Path:
    return queue_root / "production-attempts" / f"{job_id}.attempt"


def _attempt_payload(
    job_id: str,
    request_sha256: str,
    attempt_status: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "job_id": job_id,
        "request_sha256": request_sha256,
        "attempt_status": attempt_status,
    }


def _encode_attempt_payload(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _write_all(descriptor: int, encoded: bytes) -> None:
    offset = 0
    while offset < len(encoded):
        written = os.write(descriptor, encoded[offset:])
        if written <= 0:
            raise ProductionAttemptEvidenceError(
                "production attempt evidence write failed"
            )
        offset += written


def _assert_attempt_directory_identity(evidence: ProductionAttemptEvidence) -> None:
    try:
        current = evidence.marker_path.parent.lstat()
        opened = os.fstat(evidence.directory_descriptor)
    except OSError as error:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory changed"
        ) from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
        or opened.st_uid != os.getuid()
        or opened.st_mode & 0o022
    ):
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory changed"
        )


def _assert_attempt_marker_identity(evidence: ProductionAttemptEvidence) -> None:
    try:
        current = os.stat(
            evidence.marker_path.name,
            dir_fd=evidence.directory_descriptor,
            follow_symlinks=False,
        )
        opened = os.fstat(evidence.marker_descriptor)
    except OSError as error:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence changed"
        ) from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or not stat.S_ISREG(opened.st_mode)
        or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
        or opened.st_uid != os.getuid()
        or stat.S_IMODE(opened.st_mode) != 0o600
        or not 2 <= opened.st_size <= MAX_PRODUCTION_ATTEMPT_BYTES
    ):
        raise ProductionAttemptEvidenceError(
            "production attempt evidence changed"
        )
    _assert_attempt_directory_identity(evidence)


def _read_attempt_payload(evidence: ProductionAttemptEvidence) -> dict[str, object]:
    _assert_attempt_marker_identity(evidence)
    try:
        os.lseek(evidence.marker_descriptor, 0, os.SEEK_SET)
        expected_size = os.fstat(evidence.marker_descriptor).st_size
        encoded = os.read(
            evidence.marker_descriptor,
            MAX_PRODUCTION_ATTEMPT_BYTES + 1,
        )
    except OSError as error:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence cannot be read"
        ) from error
    if len(encoded) != expected_size or len(encoded) > MAX_PRODUCTION_ATTEMPT_BYTES:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence size changed"
        )
    try:
        payload = json.loads(
            encoded,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence JSON is invalid"
        ) from error
    if not isinstance(payload, dict) or set(payload) != {
        "attempt_status",
        "job_id",
        "request_sha256",
        "schema_version",
    }:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence schema is invalid"
        )
    if (
        type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
        or type(payload.get("job_id")) is not str
        or SAFE_ATTEMPT_JOB_ID.fullmatch(payload["job_id"]) is None
        or type(payload.get("request_sha256")) is not str
        or SAFE_SHA256.fullmatch(payload["request_sha256"]) is None
        or type(payload.get("attempt_status")) is not str
        or payload["attempt_status"] not in PRODUCTION_ATTEMPT_STATES
    ):
        raise ProductionAttemptEvidenceError(
            "production attempt evidence schema is invalid"
        )
    if (
        payload["job_id"] != evidence.job_id
        or payload["request_sha256"] != evidence.request_sha256
    ):
        raise ProductionAttemptEvidenceError(
            "production attempt evidence identity mismatch"
        )
    _assert_attempt_marker_identity(evidence)
    return payload


def _open_attempt_directory(marker_directory: Path) -> int:
    try:
        marker_directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    except OSError as error:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory cannot be created"
        ) from error
    try:
        before = marker_directory.lstat()
    except OSError as error:
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory is unavailable"
        ) from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISDIR(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o022
    ):
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory is unsafe"
        )
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(marker_directory, flags)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        after = os.fstat(descriptor)
        current = marker_directory.lstat()
    except OSError as error:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory cannot be opened"
        ) from error
    if (
        not stat.S_ISDIR(after.st_mode)
        or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        or (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino)
        or after.st_uid != os.getuid()
        or after.st_mode & 0o022
    ):
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
        raise ProductionAttemptEvidenceError(
            "production attempt evidence directory changed"
        )
    return descriptor


def _begin_production_attempt(
    queue_root: Path,
    request: dict[str, Any],
) -> ProductionAttemptEvidence:
    job_id = request.get("job_id")
    request_sha256 = request.get("request_sha256")
    if (
        type(job_id) is not str
        or SAFE_ATTEMPT_JOB_ID.fullmatch(job_id) is None
        or type(request_sha256) is not str
        or SAFE_SHA256.fullmatch(request_sha256) is None
    ):
        raise ProductionAttemptEvidenceError(
            "production attempt identity is invalid"
        )
    marker = _production_attempt_marker(queue_root, job_id)
    directory_descriptor = _open_attempt_directory(marker.parent)
    marker_descriptor = -1
    is_new = False
    try:
        flags = (
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            marker_descriptor = os.open(
                marker.name,
                flags,
                0o600,
                dir_fd=directory_descriptor,
            )
            is_new = True
        except FileExistsError:
            marker_descriptor = os.open(
                marker.name,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_descriptor,
            )
        evidence = ProductionAttemptEvidence(
            directory_descriptor=directory_descriptor,
            marker_descriptor=marker_descriptor,
            marker_path=marker,
            job_id=job_id,
            request_sha256=request_sha256,
            attempt_status="started",
            is_new=is_new,
        )
        if is_new:
            os.fchmod(marker_descriptor, 0o600)
            _write_all(
                marker_descriptor,
                _encode_attempt_payload(
                    _attempt_payload(job_id, request_sha256, "started")
                ),
            )
            os.fsync(marker_descriptor)
            os.fsync(directory_descriptor)
        payload = _read_attempt_payload(evidence)
        evidence.attempt_status = str(payload["attempt_status"])
        return evidence
    except Exception as error:
        if marker_descriptor >= 0:
            os.close(marker_descriptor)
        fcntl.flock(directory_descriptor, fcntl.LOCK_UN)
        os.close(directory_descriptor)
        if isinstance(error, ProductionAttemptEvidenceError):
            raise
        raise ProductionAttemptEvidenceError(
            "production attempt evidence cannot be opened"
        ) from error


def _finish_production_attempt(
    evidence: ProductionAttemptEvidence,
    attempt_status: str,
) -> None:
    if attempt_status not in {"succeeded", "failed"}:
        raise ProductionAttemptEvidenceError(
            "production attempt terminal status is invalid"
        )
    payload = _read_attempt_payload(evidence)
    current_status = str(payload["attempt_status"])
    if current_status in {"succeeded", "failed"}:
        evidence.attempt_status = current_status
        return
    temp_name = (
        f".{evidence.marker_path.name}.{os.getpid()}."
        f"{secrets.token_hex(8)}.tmp"
    )
    temp_descriptor = -1
    try:
        temp_descriptor = os.open(
            temp_name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=evidence.directory_descriptor,
        )
        os.fchmod(temp_descriptor, 0o600)
        _write_all(
            temp_descriptor,
            _encode_attempt_payload(
                _attempt_payload(
                    evidence.job_id,
                    evidence.request_sha256,
                    attempt_status,
                )
            ),
        )
        os.fsync(temp_descriptor)
        _assert_attempt_marker_identity(evidence)
        os.replace(
            temp_name,
            evidence.marker_path.name,
            src_dir_fd=evidence.directory_descriptor,
            dst_dir_fd=evidence.directory_descriptor,
        )
        os.fsync(evidence.directory_descriptor)
        os.close(evidence.marker_descriptor)
        evidence.marker_descriptor = os.open(
            evidence.marker_path.name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=evidence.directory_descriptor,
        )
        evidence.attempt_status = attempt_status
        committed = _read_attempt_payload(evidence)
        if committed["attempt_status"] != attempt_status:
            raise ProductionAttemptEvidenceError(
                "production attempt terminal evidence is invalid"
            )
    except Exception as error:
        if isinstance(error, ProductionAttemptEvidenceError):
            raise
        raise ProductionAttemptEvidenceError(
            "production attempt evidence cannot be finalized"
        ) from error
    finally:
        if temp_descriptor >= 0:
            try:
                os.close(temp_descriptor)
            except OSError:
                pass
        try:
            os.unlink(temp_name, dir_fd=evidence.directory_descriptor)
        except FileNotFoundError:
            pass


def _close_production_attempt(evidence: ProductionAttemptEvidence | None) -> None:
    if evidence is None:
        return
    try:
        os.close(evidence.marker_descriptor)
    except OSError:
        pass
    try:
        fcntl.flock(evidence.directory_descriptor, fcntl.LOCK_UN)
    finally:
        try:
            os.close(evidence.directory_descriptor)
        except OSError:
            pass


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


def process_once(
    queue_root: Path,
    *,
    generate_json: GenerateJson = _cli_generate_json,
    clock: Callable[[], float] | None = None,
    lane: str | None = None,
    exact_run_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    processing_path: Path | None = None
    archive_path: Path | None = None
    job_id = ""
    request: dict[str, Any] = {}
    broker_diagnostic: dict[str, object] | None = None
    credential_pool: dict[str, str] | None = None
    production_attempt_evidence: ProductionAttemptEvidence | None = None
    production_api_key: str | None = None
    production_state_path: Path | None = None
    production_manifest_sha256: str | None = None
    cooldown_seconds: int | None = None
    clock_function = clock or time.time
    try:
        service_label = (
            f"com.pantheon.agy-gemini-{lane}"
            if lane is not None
            else os.environ.get("PANTHEON_RUNTIME_SERVICE_LABEL", "")
        )
        formal_runtime.validate_runtime_tick(
            service_label,
            queue_root=queue_root.resolve(),
            state_root=Path(
                os.environ.get(
                    "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", Path.cwd()
                )
            ),
            actor_root=Path(
                os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())
            ),
            log_root=Path(
                os.environ.get("PANTHEON_RUNTIME_LOG_ROOT", Path.cwd())
            ),
        )
        if lane is not None and lane not in CONTENT_LANES:
            raise ValueError("unknown content lane")
        if _new_only_enabled() and lane != "new":
            return {
                "status": "disabled",
                "reason": "new_only",
                "lane": lane or "shared",
            }
        pool_file = os.environ.get("AGY_GEMINI_CREDENTIAL_POOL_FILE", "").strip()
        production_enabled = (
            os.environ.get("AGY_GEMINI_V4_BROKER") != "1"
            and bool(pool_file)
        )
        if production_enabled:
            state_file = os.environ.get(
                "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
                "",
            ).strip()
            if not state_file:
                raise ValueError("production allocator state path is required")
            production_state_path = Path(state_file)
            pool_payload, production_manifest_sha256 = _read_production_pool(
                Path(pool_file)
            )
            cooldown_seconds = _production_cooldown_seconds()
            with production_slot_admission(
                production_state_path,
                pool_id=str(pool_payload["pool_id"]),
                manifest_sha256=production_manifest_sha256,
                clock=clock_function,
            ) as admission:
                if not admission.allowed:
                    return {
                        "status": "cooldown",
                        "admission": admission.receipt,
                    }
                processing_path = _claim_next(queue_root, selected_run_ids)
                if processing_path is None:
                    return {"status": "idle"}
                job_id = processing_path.stem
                archive_path = queue_root / "archive" / f"{job_id}.json"
                request = json.loads(processing_path.read_text(encoding="utf-8"))
                validate_external_request(request)
                if request["job_id"] != job_id:
                    raise ValueError("request job id differs from queue filename")
                production_attempt_evidence = _begin_production_attempt(
                    queue_root,
                    request,
                )
                if not production_attempt_evidence.is_new:
                    raise ProductionAttemptReplay(
                        "production job already has attempt evidence"
                    )
                production_api_key, credential_pool = _credential_from_admission(
                    pool_payload,
                    production_manifest_sha256,
                    admission,
                )
        else:
            processing_path = _claim_next(queue_root, selected_run_ids)
            if processing_path is None:
                return {"status": "idle"}
            job_id = processing_path.stem
            archive_path = queue_root / "archive" / f"{job_id}.json"
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
                result_normalizer=normalize_new_output_contract,
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
        elif production_api_key is not None:
            _assert_attempt_marker_identity(production_attempt_evidence)
            _read_attempt_payload(production_attempt_evidence)
            client = GeminiClient(
                production_api_key,
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
        schema_diagnostics = _diagnose_json_schema(
            result,
            request["response_schema"],
        )
        if schema_diagnostics:
            normalized_result = normalize_new_output_contract(
                result,
                request["response_schema"],
            )
            if (
                normalized_result is not None
                and not _diagnose_json_schema(
                    normalized_result,
                    request["response_schema"],
                )
            ):
                result = normalized_result
                schema_diagnostics = ()
        if schema_diagnostics:
            broker_diagnostic = {
                "replay_status": "COMPLETE",
                "process_count": 1,
                "outcome": "SUCCESS",
                "result_validation": "SCHEMA_MISMATCH",
                "schema_diagnostics": [
                    {
                        "keyword": diagnostic.keyword,
                        "path": list(diagnostic.path),
                    }
                    for diagnostic in schema_diagnostics
                ],
            }
            raise V4BrokerFailure("provider payload failed response schema")
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
        assert archive_path is not None
        assert processing_path is not None
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        if production_attempt_evidence is not None:
            _finish_production_attempt(
                production_attempt_evidence,
                "succeeded",
            )
        processed: dict[str, Any] = {"status": "processed", "job_id": job_id}
        if credential_pool is not None:
            processed["credential_pool"] = credential_pool
        return processed
    except Exception as error:
        if processing_path is None:
            return {"status": "failed", "error_type": type(error).__name__}
        cooldown_receipt: dict[str, object] | None = None
        error_code = _closed_error_code(error)
        http_diagnostic = closed_gemini_http_diagnostic(
            error_code,
            getattr(error, "http_status", None),
            getattr(error, "http_status_class", None),
        )
        if (
            error_code == RATE_LIMIT_REASON
            and credential_pool is not None
            and production_state_path is not None
            and production_manifest_sha256 is not None
            and cooldown_seconds is not None
        ):
            try:
                cooldown_receipt = record_production_rate_limit(
                    production_state_path,
                    pool_id=credential_pool["pool_id"],
                    manifest_sha256=production_manifest_sha256,
                    slot_id=credential_pool["slot_id"],
                    cooldown_seconds=cooldown_seconds,
                    clock=clock_function,
                )
            except (OSError, ValueError):
                cooldown_receipt = None
        failed_record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job_id,
            "request_sha256": request.get("request_sha256"),
            "error_type": type(error).__name__,
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        if error_code is not None:
            failed_record["error_code"] = error_code
        if http_diagnostic is not None:
            failed_record.update(http_diagnostic)
        if isinstance(error, V4BrokerFailure) and broker_diagnostic is not None:
            failed_record["broker_diagnostic"] = broker_diagnostic
        if credential_pool is not None:
            failed_record["credential_pool"] = credential_pool
        failure_category = classify_external_failure(failed_record)
        failed_record["failure_category"] = failure_category
        inbox_path = queue_root / "inbox" / f"{job_id}.json"
        failed_path = queue_root / "failed" / f"{job_id}.json"
        if not inbox_path.exists() and not failed_path.exists():
            atomic_write_json(failed_path, failed_record)
        assert archive_path is not None
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        if processing_path.exists():
            os.replace(processing_path, archive_path)
        if (
            production_attempt_evidence is not None
            and not isinstance(error, ProductionAttemptEvidenceError)
        ):
            try:
                _finish_production_attempt(
                    production_attempt_evidence,
                    "succeeded" if inbox_path.exists() else "failed",
                )
            except ProductionAttemptEvidenceError as evidence_error:
                error = evidence_error
        result = {"status": "failed", "job_id": job_id, "error_type": type(error).__name__}
        if error_code is not None:
            result["error_code"] = error_code
        if http_diagnostic is not None:
            result.update(http_diagnostic)
        if credential_pool is not None:
            result["credential_pool"] = credential_pool
        if cooldown_receipt is not None:
            result["cooldown"] = cooldown_receipt
        return result
    finally:
        _close_production_attempt(production_attempt_evidence)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    parser.add_argument("--lane", choices=CONTENT_LANES)
    parser.add_argument("--exact-run-id", action="append")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("process-once")
    validate = subparsers.add_parser("validate-production-installation")
    validate.add_argument("--pool-file", type=Path, required=True)
    validate.add_argument("--state-file", type=Path, required=True)
    drain = subparsers.add_parser("drain")
    drain.add_argument("--max-jobs", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue_root = args.queue_root.resolve()
    if args.command == "validate-production-installation":
        try:
            validate_production_installation(args.pool_file, args.state_file)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        print('{"status":"valid"}')
        return 0
    if args.command == "process-once":
        result = process_once(
            queue_root,
            lane=args.lane,
            exact_run_ids=args.exact_run_id,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result["status"] == "failed" else 0
    results = []
    for _ in range(args.max_jobs):
        result = process_once(
            queue_root,
            lane=args.lane,
            exact_run_ids=args.exact_run_id,
        )
        results.append(result)
        if result["status"] in {"idle", "failed"}:
            break
    print(json.dumps({"results": results}, ensure_ascii=False))
    return 1 if any(item["status"] == "failed" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

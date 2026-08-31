#!/usr/bin/env python3
"""處理 sanitized Gemini outbox；本腳本由使用者自行啟用的 runner 執行。"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import fcntl
import hashlib
import json
import os
import plistlib
import re
import secrets
import stat
import subprocess
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
    QUOTA_REASON,
    RATE_LIMIT_REASON,
    allocate_production_slot,
    production_slot_admission,
    record_production_rate_limit,
    record_production_quota_exhausted,
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
    RAW_STDIN_PROFILE,
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
SAFE_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
SAFE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRODUCTION_SLOT_IDS = ("account-1", "account-2", "account-3")
CONTENT_LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
EXACT_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PRODUCTION_ATTEMPT_STATES = frozenset({"started", "succeeded", "failed"})
FORMAL_PRODUCTION_TRANSPORT_ENV = (
    "AGY_GEMINI_CREDENTIAL_POOL_FILE",
    "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
    "AGY_GEMINI_MODEL_ROUTE_CONFIG",
    "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST",
    "AGY_REVIEWER_MODEL",
    "AGY_WRITER_MODEL",
)
FORMAL_PRODUCTION_SECRET_ENV = frozenset({"AGY_GEMINI_CREDENTIAL_POOL_FILE"})
ACCEPTANCE_SEALED_REPLAY_MODE: Final = "acceptance_sealed_replay_v1"
ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE: Final = "acceptance_sealed_replay_bundle_v1"
ACCEPTANCE_SEALED_REPLAY_ATTEMPT_ID: Final = "sealed-replay-1"
ACCEPTANCE_SEALED_REPLAY_FIELDS: Final = frozenset({
    "schema_version",
    "mode",
    "authority_digest",
    "accepted_base_sha",
    "actor_sha",
    "lane",
    "run_id",
    "namespace",
    "job_id",
    "request_sha256",
    "role",
    "model",
    "schema_sha256",
    "executable_path",
    "executable_sha256",
    "live_provider_disabled",
    "production_allocator_disabled",
})
ACCEPTANCE_SEALED_REPLAY_SECRET_ENV: Final = frozenset({
    "AGY_GEMINI_API_KEY",
    "AGY_GEMINI_CREDENTIAL_POOL_FILE",
    "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
    "AGY_GEMINI_V4_BROKER",
    "AGY_GEMINI_V4_EXECUTABLE",
    "AGY_GEMINI_V4_EXECUTABLE_SHA256",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
})
ACCEPTANCE_SEALED_REPLAY_BUNDLE_FIELDS: Final = frozenset({
    "schema_version",
    "mode",
    "session_id",
    "bundle_digest",
    "accepted_base_sha",
    "actor_sha",
    "generation",
    "queue_root",
    "lane",
    "run_id",
    "namespace",
    "provider_call_budget",
    "entries",
})
ACCEPTANCE_SEALED_REPLAY_BUNDLE_ENTRY_FIELDS: Final = frozenset({
    "session_id",
    "entry_id",
    "job_id",
    "request_sha256",
    "namespace",
    "lane",
    "run_id",
    "role",
    "model",
    "schema_sha256",
    "sealed_result_sha256",
    "executable_path",
    "executable_sha256",
    "required",
})
OPERATOR_SAFE_CHILD_RESULT_KEYS = frozenset({
    "status",
    "reason",
    "service_label",
    "missing_env",
    "job_id",
    "error_type",
    "error_code",
    "failure_category",
    "http_status",
    "http_status_class",
    "lane",
})
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


@dataclass(frozen=True)
class AcceptanceSealedReplayEntry:
    session_id: str
    entry_id: str
    namespace: str
    job_id: str
    request_sha256: str
    lane: str
    run_id: str
    role: str
    model: str
    schema_sha256: str
    sealed_result_sha256: str
    executable_path: Path
    executable_sha256: str
    required: bool

    def validate_request(self, request: dict[str, Any]) -> None:
        validate_external_request(request)
        expected = {
            "namespace": self.namespace,
            "job_id": self.job_id,
            "request_sha256": self.request_sha256,
            "role": self.role,
            "model": self.model,
            "schema_sha256": self.schema_sha256,
        }
        for field, value in expected.items():
            if request.get(field) != value:
                raise ValueError(f"sealed replay request {field} mismatch")

    def validate_transport(
        self,
        role: str,
        model: str,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> None:
        if role != self.role:
            raise ValueError("sealed replay role mismatch")
        if model != self.model:
            raise ValueError("sealed replay model mismatch")
        schema_sha256 = hashlib.sha256(_canonical_json_bytes(response_schema)).hexdigest()
        if schema_sha256 != self.schema_sha256:
            raise ValueError("sealed replay schema mismatch")
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        request_core = {
            "schema_version": SCHEMA_VERSION,
            "namespace": self.namespace,
            "role": role,
            "model": model,
            "thinking_level": "LOW",
            "operation_level": "external_generation",
            "prompt": prompt,
            "response_schema": response_schema,
            "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256,
        }
        request_sha256 = hashlib.sha256(_canonical_json_bytes(request_core)).hexdigest()
        if request_sha256 != self.request_sha256:
            raise ValueError("sealed replay request hash mismatch")
        if _sha256_file(self.executable_path) != self.executable_sha256:
            raise ValueError("sealed replay executable changed")

    def validate_result(self, result: dict[str, Any]) -> None:
        result_sha256 = hashlib.sha256(_canonical_json_bytes(result)).hexdigest()
        if result_sha256 != self.sealed_result_sha256:
            raise ValueError("sealed replay result digest mismatch")


@dataclass(frozen=True)
class AcceptanceSealedReplayAuthority:
    accepted_base_sha: str
    actor_sha: str
    lane: str
    run_id: str
    authority_digest: str
    entry: AcceptanceSealedReplayEntry

    def validate_request(self, request: dict[str, Any]) -> None:
        self.entry.validate_request(request)

    def validate_transport(
        self,
        actor_root: Path,
        role: str,
        model: str,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> None:
        self.validate_actor(actor_root)
        self.entry.validate_transport(role, model, prompt, response_schema)

    def validate_actor(self, actor_root: Path) -> None:
        actual_head = _git_head(actor_root)
        if actual_head != self.actor_sha:
            raise ValueError("sealed replay actor head mismatch")
        _assert_git_ancestor(actor_root, self.accepted_base_sha, actual_head)

    @property
    def namespace(self) -> str:
        return self.entry.namespace

    @property
    def job_id(self) -> str:
        return self.entry.job_id

    @property
    def request_sha256(self) -> str:
        return self.entry.request_sha256

    @property
    def model(self) -> str:
        return self.entry.model

    @property
    def executable_path(self) -> Path:
        return self.entry.executable_path

    @property
    def executable_sha256(self) -> str:
        return self.entry.executable_sha256


@dataclass(frozen=True)
class AcceptanceSealedReplayBundle:
    session_id: str
    accepted_base_sha: str
    actor_sha: str
    generation: str
    queue_root: Path
    lane: str
    run_id: str
    namespace: str
    provider_call_budget: int
    entries: tuple[AcceptanceSealedReplayEntry, ...]
    bundle_digest: str
    expected_bundle_digest: str

    def validate_actor(self, actor_root: Path) -> None:
        actual_head = _git_head(actor_root)
        if actual_head != self.actor_sha:
            raise ValueError("sealed replay bundle actor head mismatch")
        _assert_git_ancestor(actor_root, self.accepted_base_sha, actual_head)

    def validate_runtime(self, actor_root: Path, queue_root: Path, lane: str, run_id: str) -> None:
        self.validate_actor(actor_root)
        if self.queue_root != queue_root.resolve():
            raise ValueError("sealed replay bundle queue root mismatch")
        if os.environ.get("PANTHEON_RUNTIME_GENERATION", "") != self.generation:
            raise ValueError("sealed replay bundle generation mismatch")
        if lane != self.lane:
            raise ValueError("sealed replay bundle lane mismatch")
        if run_id != self.run_id:
            raise ValueError("sealed replay bundle run id mismatch")

    def matching_entries(self, request: dict[str, Any]) -> tuple[AcceptanceSealedReplayEntry, ...]:
        return tuple(
            entry
            for entry in self.entries
            if (
                entry.session_id == self.session_id
                and entry.namespace == request.get("namespace")
                and entry.job_id == request.get("job_id")
                and entry.request_sha256 == request.get("request_sha256")
                and entry.lane == self.lane
                and entry.run_id == self.run_id
                and entry.role == request.get("role")
                and entry.model == request.get("model")
                and entry.schema_sha256 == request.get("schema_sha256")
            )
        )


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


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("sealed replay executable is unavailable")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_pinned_json_object(
    path: Path,
    *,
    expected_sha256: str,
    label: str,
    maximum_size: int,
) -> tuple[dict[str, Any], str]:
    if (
        not path.is_absolute()
        or str(path.resolve()) != str(path)
        or type(expected_sha256) is not str
        or SAFE_SHA256.fullmatch(expected_sha256) is None
    ):
        raise ValueError(f"{label} pinned identity is invalid")
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o022
        or not 2 <= before.st_size <= maximum_size
    ):
        raise ValueError(f"{label} must be owner-safe regular file")
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        after = os.fstat(descriptor)
        if (
            not stat.S_ISREG(after.st_mode)
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_uid != os.getuid()
            or after.st_mode & 0o022
            or after.st_size != before.st_size
            or not 2 <= after.st_size <= maximum_size
        ):
            raise ValueError(f"{label} changed during validation")
        encoded = _read_descriptor(
            descriptor,
            expected_size=after.st_size,
            maximum_size=maximum_size,
            label=label,
        )
    finally:
        os.close(descriptor)
    raw_sha256 = hashlib.sha256(encoded).hexdigest()
    if raw_sha256 != expected_sha256:
        raise ValueError(f"{label} expected digest mismatch")
    try:
        payload = json.loads(
            encoded,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"{label} JSON is invalid") from error
    if type(payload) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return payload, raw_sha256


def _git_head(actor_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(actor_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("sealed replay actor git head is unavailable") from error
    head = completed.stdout.strip()
    if SAFE_GIT_COMMIT.fullmatch(head) is None:
        raise ValueError("sealed replay actor git head is invalid")
    return head


def _assert_git_ancestor(actor_root: Path, ancestor: str, descendant: str) -> None:
    if (
        SAFE_GIT_COMMIT.fullmatch(ancestor) is None
        or SAFE_GIT_COMMIT.fullmatch(descendant) is None
    ):
        raise ValueError("sealed replay git ancestry identity is invalid")
    try:
        subprocess.run(
            ["git", "-C", str(actor_root), "merge-base", "--is-ancestor", ancestor, descendant],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("sealed replay accepted base is not actor ancestor") from error


def _load_json_object(path: Path, *, label: str, maximum_size: int = 16 * 1024) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is unavailable")
    encoded = path.read_bytes()
    if not 2 <= len(encoded) <= maximum_size:
        raise ValueError(f"{label} size is invalid")
    try:
        payload = json.loads(
            encoded,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"{label} JSON is invalid") from error
    if type(payload) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _expected_namespace_for_run_id(run_id: str) -> str:
    if EXACT_RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("sealed replay run id is invalid")
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]


def _load_acceptance_sealed_replay_entry(
    payload: dict[str, Any],
) -> AcceptanceSealedReplayEntry:
    if set(payload) != ACCEPTANCE_SEALED_REPLAY_BUNDLE_ENTRY_FIELDS:
        raise ValueError("sealed replay entry fields are strict")
    executable_path_value = payload.get("executable_path")
    if type(executable_path_value) is not str:
        raise ValueError("sealed replay executable path is invalid")
    executable_path = Path(executable_path_value)
    if not executable_path.is_absolute() or str(executable_path.resolve()) != executable_path_value:
        raise ValueError("sealed replay executable path must be canonical")
    executable_sha256 = payload.get("executable_sha256")
    if (
        type(payload.get("job_id")) is not str
        or SAFE_ATTEMPT_JOB_ID.fullmatch(payload["job_id"]) is None
        or type(payload.get("session_id")) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(payload["session_id"]) is None
        or type(payload.get("entry_id")) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(payload["entry_id"]) is None
        or type(payload.get("request_sha256")) is not str
        or SAFE_SHA256.fullmatch(payload["request_sha256"]) is None
        or type(payload.get("namespace")) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(payload["namespace"]) is None
        or payload.get("lane") not in CONTENT_LANES
        or type(payload.get("run_id")) is not str
        or EXACT_RUN_ID_PATTERN.fullmatch(payload["run_id"]) is None
        or payload.get("role") not in V4_ROLE_INSTRUCTIONS
        or type(payload.get("model")) is not str
        or not str(payload["model"])
        or type(payload.get("schema_sha256")) is not str
        or SAFE_SHA256.fullmatch(payload["schema_sha256"]) is None
        or type(payload.get("sealed_result_sha256")) is not str
        or SAFE_SHA256.fullmatch(payload["sealed_result_sha256"]) is None
        or type(executable_sha256) is not str
        or SAFE_SHA256.fullmatch(executable_sha256) is None
        or type(payload.get("required")) is not bool
    ):
        raise ValueError("sealed replay entry identity is invalid")
    if _sha256_file(executable_path) != executable_sha256:
        raise ValueError("sealed replay executable digest mismatch")
    return AcceptanceSealedReplayEntry(
        session_id=str(payload["session_id"]),
        entry_id=str(payload["entry_id"]),
        namespace=str(payload["namespace"]),
        job_id=str(payload["job_id"]),
        request_sha256=str(payload["request_sha256"]),
        lane=str(payload["lane"]),
        run_id=str(payload["run_id"]),
        role=str(payload["role"]),
        model=str(payload["model"]),
        schema_sha256=str(payload["schema_sha256"]),
        sealed_result_sha256=str(payload["sealed_result_sha256"]),
        executable_path=executable_path,
        executable_sha256=str(executable_sha256),
        required=bool(payload["required"]),
    )


def _load_acceptance_sealed_replay_authority(
    authority_path: Path,
    actor_root: Path,
) -> AcceptanceSealedReplayAuthority:
    authority = _load_json_object(authority_path, label="sealed replay authority")
    if set(authority) != ACCEPTANCE_SEALED_REPLAY_FIELDS:
        raise ValueError("sealed replay authority fields are strict")
    authority_digest = authority.get("authority_digest")
    body = {key: value for key, value in authority.items() if key != "authority_digest"}
    if (
        type(authority_digest) is not str
        or SAFE_SHA256.fullmatch(authority_digest) is None
        or hashlib.sha256(_canonical_json_bytes(body)).hexdigest() != authority_digest
    ):
        raise ValueError("sealed replay authority digest mismatch")
    entry = _load_acceptance_sealed_replay_entry(
        {
            "job_id": authority.get("job_id"),
            "request_sha256": authority.get("request_sha256"),
            "namespace": authority.get("namespace"),
            "role": authority.get("role"),
            "model": authority.get("model"),
            "schema_sha256": authority.get("schema_sha256"),
            "executable_path": authority.get("executable_path"),
            "executable_sha256": authority.get("executable_sha256"),
        }
    )
    if (
        type(authority.get("schema_version")) is not int
        or authority["schema_version"] != 1
        or authority.get("mode") != ACCEPTANCE_SEALED_REPLAY_MODE
        or type(authority.get("accepted_base_sha")) is not str
        or SAFE_GIT_COMMIT.fullmatch(authority["accepted_base_sha"]) is None
        or type(authority.get("actor_sha")) is not str
        or SAFE_GIT_COMMIT.fullmatch(authority["actor_sha"]) is None
        or authority.get("lane") not in CONTENT_LANES
        or type(authority.get("run_id")) is not str
        or EXACT_RUN_ID_PATTERN.fullmatch(authority["run_id"]) is None
        or authority.get("namespace") != _expected_namespace_for_run_id(authority["run_id"])
        or authority.get("live_provider_disabled") is not True
        or authority.get("production_allocator_disabled") is not True
    ):
        raise ValueError("sealed replay authority identity is invalid")
    authority_record = AcceptanceSealedReplayAuthority(
        accepted_base_sha=str(authority["accepted_base_sha"]),
        actor_sha=str(authority["actor_sha"]),
        lane=str(authority["lane"]),
        run_id=str(authority["run_id"]),
        authority_digest=str(authority_digest),
        entry=entry,
    )
    authority_record.validate_actor(actor_root)
    return authority_record


def _load_acceptance_sealed_replay_bundle(
    bundle_path: Path,
    expected_bundle_digest: str,
    actor_root: Path,
    queue_root: Path,
    lane: str,
    run_id: str,
) -> AcceptanceSealedReplayBundle:
    bundle, raw_bundle_digest = _read_pinned_json_object(
        bundle_path,
        expected_sha256=expected_bundle_digest,
        label="sealed replay bundle",
        maximum_size=256 * 1024,
    )
    if set(bundle) != ACCEPTANCE_SEALED_REPLAY_BUNDLE_FIELDS:
        raise ValueError("sealed replay bundle fields are strict")
    bundle_digest = bundle.get("bundle_digest")
    body = {key: value for key, value in bundle.items() if key != "bundle_digest"}
    if (
        type(bundle_digest) is not str
        or SAFE_SHA256.fullmatch(bundle_digest) is None
        or hashlib.sha256(_canonical_json_bytes(body)).hexdigest() != bundle_digest
    ):
        raise ValueError("sealed replay bundle digest mismatch")
    raw_entries = bundle.get("entries")
    if not isinstance(raw_entries, list) or not 1 <= len(raw_entries) <= 16:
        raise ValueError("sealed replay bundle entries are invalid")
    entries = tuple(
        _load_acceptance_sealed_replay_entry(entry)
        for entry in raw_entries
        if type(entry) is dict
    )
    if len(entries) != len(raw_entries):
        raise ValueError("sealed replay bundle entries are strict")
    session_id = bundle.get("session_id")
    entry_ids = [entry.entry_id for entry in entries]
    job_ids = [entry.job_id for entry in entries]
    request_sha256_values = [entry.request_sha256 for entry in entries]
    entry_keys = [
        (
            entry.session_id,
            entry.entry_id,
            entry.namespace,
            entry.job_id,
            entry.request_sha256,
            entry.lane,
            entry.run_id,
            entry.role,
            entry.model,
            entry.schema_sha256,
            entry.sealed_result_sha256,
        )
        for entry in entries
    ]
    if (
        len(entry_ids) != len(set(entry_ids))
        or
        len(job_ids) != len(set(job_ids))
        or len(request_sha256_values) != len(set(request_sha256_values))
        or len(entry_keys) != len(set(entry_keys))
    ):
        raise ValueError("sealed replay bundle entries are ambiguous")
    canonical_queue_root = queue_root.resolve()
    queue_root_value = bundle.get("queue_root")
    if (
        type(queue_root_value) is not str
        or not Path(queue_root_value).is_absolute()
        or Path(queue_root_value).resolve() != canonical_queue_root
        or queue_root_value != str(canonical_queue_root)
    ):
        raise ValueError("sealed replay bundle queue root mismatch")
    provider_call_budget = bundle.get("provider_call_budget")
    required_count = sum(1 for entry in entries if entry.required)
    if (
        type(bundle.get("schema_version")) is not int
        or bundle["schema_version"] != 1
        or bundle.get("mode") != ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE
        or type(session_id) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(session_id) is None
        or type(bundle.get("accepted_base_sha")) is not str
        or SAFE_GIT_COMMIT.fullmatch(bundle["accepted_base_sha"]) is None
        or type(bundle.get("actor_sha")) is not str
        or SAFE_GIT_COMMIT.fullmatch(bundle["actor_sha"]) is None
        or type(bundle.get("generation")) is not str
        or not str(bundle["generation"])
        or bundle.get("lane") not in CONTENT_LANES
        or type(bundle.get("run_id")) is not str
        or EXACT_RUN_ID_PATTERN.fullmatch(bundle["run_id"]) is None
        or bundle.get("namespace") != _expected_namespace_for_run_id(bundle["run_id"])
        or type(provider_call_budget) is not int
        or type(provider_call_budget) is bool
        or not required_count <= provider_call_budget <= len(entries)
        or any(
            entry.session_id != session_id
            or entry.namespace != bundle["namespace"]
            or entry.lane != bundle["lane"]
            or entry.run_id != bundle["run_id"]
            for entry in entries
        )
    ):
        raise ValueError("sealed replay bundle identity is invalid")
    authority = AcceptanceSealedReplayBundle(
        session_id=str(session_id),
        accepted_base_sha=str(bundle["accepted_base_sha"]),
        actor_sha=str(bundle["actor_sha"]),
        generation=str(bundle["generation"]),
        queue_root=canonical_queue_root,
        lane=str(bundle["lane"]),
        run_id=str(bundle["run_id"]),
        namespace=str(bundle["namespace"]),
        provider_call_budget=provider_call_budget,
        entries=entries,
        bundle_digest=str(bundle_digest),
        expected_bundle_digest=raw_bundle_digest,
    )
    authority.validate_runtime(actor_root, canonical_queue_root, lane, run_id)
    return authority


def _assert_acceptance_sealed_replay_environment(
    environment: dict[str, str] | os._Environ[str] = os.environ,
) -> None:
    present = sorted(
        name
        for name in ACCEPTANCE_SEALED_REPLAY_SECRET_ENV
        if str(environment.get(name, "")).strip()
    )
    if present:
        raise ValueError(
            "sealed replay forbids live provider or production allocator env: "
            + ",".join(present)
        )


def _load_single_pending_sealed_request(
    queue_root: Path,
    authority: AcceptanceSealedReplayAuthority,
) -> dict[str, Any]:
    outbox_path = queue_root / "outbox" / f"{authority.job_id}.json"
    if not outbox_path.exists():
        raise ValueError("sealed replay pending request is missing")
    candidates = [
        queue_root / "processing" / f"{authority.job_id}.json",
        queue_root / "archive" / f"{authority.job_id}.json",
        queue_root / "failed" / f"{authority.job_id}.json",
        queue_root / "inbox" / f"{authority.job_id}.json",
    ]
    if any(path.exists() for path in candidates):
        raise ValueError("sealed replay request location is not pending-only")
    request = _load_json_object(
        outbox_path,
        label="sealed replay pending request",
        maximum_size=512 * 1024,
    )
    authority.validate_request(request)
    if request["job_id"] != authority.job_id:
        raise ValueError("sealed replay request job id mismatch")
    return request


def _load_exact_pending_bundle_request(
    queue_root: Path,
    bundle: AcceptanceSealedReplayBundle,
) -> tuple[dict[str, Any], AcceptanceSealedReplayEntry]:
    outbox = queue_root / "outbox"
    if not outbox.exists():
        raise ValueError("sealed replay bundle has zero pending request")
    pending: list[dict[str, Any]] = []
    for path in sorted(outbox.glob("*.json")):
        request = _load_json_object(
            path,
            label="sealed replay bundle pending request",
            maximum_size=512 * 1024,
        )
        validate_external_request(request)
        if request.get("job_id") != path.stem:
            raise ValueError("sealed replay bundle pending job id mismatch")
        if request.get("namespace") == bundle.namespace:
            pending.append(request)
    if not pending:
        raise ValueError("sealed replay bundle has zero pending request")
    if len(pending) != 1:
        raise ValueError("sealed replay bundle has many pending requests")
    matches = bundle.matching_entries(pending[0])
    if not matches:
        raise ValueError("sealed replay bundle has unknown pending request")
    if len(matches) != 1:
        raise ValueError("sealed replay bundle has ambiguous pending entry")
    matches[0].validate_request(pending[0])
    if _trusted_bundle_entry_used(queue_root, matches[0]):
        raise ValueError("sealed replay bundle pending request was already used")
    return pending[0], matches[0]


def _trusted_bundle_entry_used(
    queue_root: Path,
    entry: AcceptanceSealedReplayEntry,
) -> bool:
    state = _classify_bundle_entry_delivery(queue_root, entry)
    if state["state"] == "DELIVERED":
        return True
    if state["state"] == "UNUSED":
        return False
    raise ValueError(f"sealed replay bundle usage evidence is incomplete: {state['reason']}")


def _sealed_bundle_attempt_id(entry: AcceptanceSealedReplayEntry) -> str:
    suffix = hashlib.sha256(
        f"{entry.session_id}:{entry.entry_id}".encode("utf-8")
    ).hexdigest()[:32]
    return f"sr2-{suffix}"


def _classify_bundle_entry_delivery(
    queue_root: Path,
    entry: AcceptanceSealedReplayEntry,
) -> dict[str, object]:
    archive_path = queue_root / "archive" / f"{entry.job_id}.json"
    inbox_path = queue_root / "inbox" / f"{entry.job_id}.json"
    ledger_path = queue_root / "v4" / "ledger" / f"{entry.job_id}.jsonl"
    anchor_path = (
        queue_root
        / "v4"
        / "anchors"
        / f"{entry.job_id}.{_sealed_bundle_attempt_id(entry)}.json"
    )
    processing_path = queue_root / "processing" / f"{entry.job_id}.json"
    failed_path = queue_root / "failed" / f"{entry.job_id}.json"
    existing = {
        "archive": archive_path.exists(),
        "inbox": inbox_path.exists(),
        "ledger": ledger_path.exists(),
        "anchor": anchor_path.exists(),
        "processing": processing_path.exists(),
        "failed": failed_path.exists(),
    }
    if not any(existing.values()):
        return {"state": "UNUSED", "reason": "no_delivery_evidence", "paths": existing}
    if existing["processing"] or existing["failed"]:
        return {"state": "INCOMPLETE", "reason": "active_or_failed_path_present", "paths": existing}
    if not (existing["archive"] and existing["inbox"] and existing["ledger"] and existing["anchor"]):
        return {"state": "INCOMPLETE", "reason": "partial_delivery_evidence", "paths": existing}
    archived_request = _load_json_object(
        archive_path,
        label="sealed replay bundle archived request",
        maximum_size=512 * 1024,
    )
    entry.validate_request(archived_request)
    response = _load_json_object(
        inbox_path,
        label="sealed replay bundle inbox response",
        maximum_size=512 * 1024,
    )
    if (
        response.get("schema_version") != SCHEMA_VERSION
        or response.get("job_id") != entry.job_id
        or response.get("request_sha256") != entry.request_sha256
        or response.get("model") != entry.model
        or type(response.get("result")) is not dict
    ):
        return {"state": "INCOMPLETE", "reason": "response_identity_mismatch", "paths": existing}
    result = response["result"]
    if hashlib.sha256(_canonical_json_bytes(result)).hexdigest() != entry.sealed_result_sha256:
        return {"state": "INCOMPLETE", "reason": "sealed_result_digest_mismatch", "paths": existing}
    if _diagnose_json_schema(result, archived_request["response_schema"]):
        return {"state": "INCOMPLETE", "reason": "response_schema_mismatch", "paths": existing}
    entry.validate_transport(
        str(archived_request["role"]),
        str(archived_request["model"]),
        str(archived_request["prompt"]),
        archived_request["response_schema"],
    )
    broker_result = run_single_shot(
        operation_id=entry.job_id,
        item_id=entry.namespace,
        attempt_id=_sealed_bundle_attempt_id(entry),
        request_sha256=entry.request_sha256,
        model=entry.model,
        executable=entry.executable_path,
        target_profile=RAW_STDIN_PROFILE,
        expected_executable_digest=entry.executable_sha256,
        raw_request=_render_v4_effective_prompt(
            str(archived_request["role"]),
            str(archived_request["prompt"]),
            archived_request["response_schema"],
        ),
        response_schema=archived_request["response_schema"],
        timeout_milliseconds=120_000,
        ledger_path=ledger_path,
        anchor_store=FileAnchorStore(queue_root / "v4" / "anchors"),
        result_normalizer=normalize_new_output_contract,
    )
    expected_receipt = ExecutionReceipt(
        entry.job_id,
        entry.namespace,
        _sealed_bundle_attempt_id(entry),
        entry.request_sha256,
        entry.model,
        RAW_STDIN_PROFILE,
        entry.executable_sha256,
    )
    if (
        broker_result.receipt != expected_receipt
        or broker_result.replay_status != "COMPLETE"
        or broker_result.process_count != 1
        or broker_result.errors
    ):
        return {
            "state": "INCOMPLETE",
            "reason": "broker_delivery_evidence_mismatch",
            "paths": existing,
            "broker_replay_status": broker_result.replay_status,
            "broker_process_count": broker_result.process_count,
        }
    return {"state": "DELIVERED", "reason": "trusted_delivery", "paths": existing}


def _trusted_bundle_usage_count(
    queue_root: Path,
    bundle: AcceptanceSealedReplayBundle,
) -> int:
    used = 0
    for entry in bundle.entries:
        if _trusted_bundle_entry_used(queue_root, entry):
            used += 1
    return used


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


def _is_formal_production_gemini_service(service_label: str) -> bool:
    return (
        service_label.startswith("com.pantheon.agy-gemini-")
        and service_label != "com.pantheon.agy-gemini-coordinator"
        and service_label.removeprefix("com.pantheon.agy-gemini-") in CONTENT_LANES
    )


def _formal_production_transport_block(
    service_label: str,
    environment: dict[str, str] | os._Environ[str] = os.environ,
) -> dict[str, Any] | None:
    if environment.get("PANTHEON_FORMAL_RUNTIME") != "1":
        return None
    if not _is_formal_production_gemini_service(service_label):
        return None
    missing = [
        name
        for name in FORMAL_PRODUCTION_TRANSPORT_ENV
        if not str(environment.get(name, "")).strip()
    ]
    if not missing:
        return None
    return {
        "status": "blocked",
        "reason": "formal_production_transport_env_missing",
        "service_label": service_label,
        "missing_env": missing,
    }


def _read_plist_environment(plist_path: Path, service_label: str) -> dict[str, str]:
    if not plist_path.is_absolute() or plist_path.is_symlink() or not plist_path.is_file():
        raise ValueError("formal operator plist is unavailable")
    payload = plistlib.loads(plist_path.read_bytes())
    if type(payload) is not dict or payload.get("Label") != service_label:
        raise ValueError("formal operator plist label mismatch")
    environment = payload.get("EnvironmentVariables")
    if type(environment) is not dict:
        raise ValueError("formal operator plist environment is missing")
    result: dict[str, str] = {}
    for key, value in environment.items():
        if type(key) is str and type(value) in {str, int, float, bool}:
            result[key] = str(value)
    return result


def _manifest_environment(
    manifest_path: Path,
    manifest: dict[str, Any],
    service_label: str,
) -> dict[str, str]:
    result = {
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": str(manifest["manifest_digest"]),
        "PANTHEON_RUNTIME_IDENTITY": str(manifest["identity"]),
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": str(manifest["runtime_identity_digest"]),
        "PANTHEON_RUNTIME_CODE_DIGEST": str(manifest["runtime_digest"]),
        "PANTHEON_RUNTIME_CONFIG_VERSION": str(manifest["config_version"]),
        "PANTHEON_RUNTIME_GENERATION": str(manifest["generation"]),
        "PANTHEON_RUNTIME_ACTOR_ROOT": str(manifest["actor_root"]),
        "PANTHEON_RUNTIME_QUEUE_ROOT": str(manifest["queue_root"]),
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": str(manifest["publisher_state_root"]),
        "PANTHEON_RUNTIME_LOG_ROOT": str(manifest["log_root"]),
        "PANTHEON_RUNTIME_SERVICE_LABEL": service_label,
    }
    if "python_executable" in manifest:
        result["PANTHEON_RUNTIME_PYTHON_EXECUTABLE"] = str(
            manifest["python_executable"]
        )
    if "uv_executable" in manifest:
        result["PANTHEON_RUNTIME_UV_EXECUTABLE"] = str(manifest["uv_executable"])
    if "actor_head" in manifest:
        result["PANTHEON_RUNTIME_ACTOR_HEAD"] = str(manifest["actor_head"])
    return result


def _file_identity_receipt(path_value: str) -> dict[str, Any]:
    receipt: dict[str, Any] = {"present": bool(path_value.strip())}
    if not path_value.strip():
        return receipt
    path = Path(path_value)
    receipt["absolute"] = path.is_absolute()
    if path.is_absolute() and path.is_file() and not path.is_symlink():
        payload = path.read_bytes()
        receipt["size"] = len(payload)
        receipt["sha256"] = hashlib.sha256(payload).hexdigest()
    return receipt


def _operator_env_receipt(environment: dict[str, str]) -> dict[str, Any]:
    receipt: dict[str, Any] = {}
    for name in FORMAL_PRODUCTION_TRANSPORT_ENV:
        value = environment.get(name, "")
        if name in FORMAL_PRODUCTION_SECRET_ENV or name.endswith("_FILE") or name.endswith("_CONFIG"):
            receipt[name] = _file_identity_receipt(value)
        else:
            encoded = value.encode("utf-8", errors="replace")
            receipt[name] = {
                "present": bool(value.strip()),
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }
    return receipt


def _stream_receipt(value: str) -> dict[str, Any]:
    encoded = value.encode("utf-8", errors="replace")
    return {
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "empty": not bool(value),
    }


def _safe_child_result_summary(stdout: str) -> tuple[str, dict[str, Any] | None]:
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        if not candidate.startswith("{") or not candidate.endswith("}"):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return "invalid_last_json_line", None
        if type(parsed) is not dict:
            return "last_json_line_not_object", None
        return (
            "parsed_last_json_line",
            {
                key: parsed[key]
                for key in sorted(OPERATOR_SAFE_CHILD_RESULT_KEYS)
                if key in parsed
            },
        )
    return "no_json_object_line", None


def operator_exact_process_once(
    *,
    manifest_path: Path,
    expected_digest: str,
    barrier: Path,
    service_label: str,
    ready_root: Path,
    plist: Path,
    exact_run_id: str,
    timeout: int,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """以 current manifest/barrier 與 plist env 執行單一正式 runner tick。"""
    if EXACT_RUN_ID_PATTERN.fullmatch(exact_run_id) is None:
        raise ValueError("formal operator exact run id is invalid")
    if not 1 <= timeout <= 300:
        raise ValueError("formal operator timeout is invalid")
    if not _is_formal_production_gemini_service(service_label):
        raise ValueError("formal operator service label is invalid")
    manifest = formal_runtime.load_manifest(manifest_path, expected_digest)
    lane = service_label.removeprefix("com.pantheon.agy-gemini-")
    python_executable = str(manifest.get("python_executable") or sys.executable)
    lane_queue_root = Path(str(manifest["queue_root"])) / "lanes" / lane
    child_command = [
        python_executable,
        "-m",
        "scripts.agy_gemini_runner",
        "--queue-root",
        str(lane_queue_root),
        "--lane",
        lane,
        "--exact-run-id",
        exact_run_id,
        "process-once",
    ]
    command = [
        python_executable,
        "-m",
        "scripts.pantheon_content_runtime_manifest",
        "barrier-exec",
        "--barrier",
        str(barrier),
        "--expected-digest",
        str(manifest["manifest_digest"]),
        "--manifest",
        str(manifest_path),
        "--service-label",
        service_label,
        "--ready-root",
        str(ready_root),
        "--timeout",
        str(timeout),
        "--",
        *child_command,
    ]
    environment = os.environ.copy()
    environment.update(_read_plist_environment(plist, service_label))
    environment.update(_manifest_environment(manifest_path, manifest, service_label))
    transport_block = _formal_production_transport_block(service_label, environment)
    if transport_block is not None:
        return {
            **transport_block,
            "env_receipt": _operator_env_receipt(environment),
        }
    completed = runner(
        command,
        cwd=str(manifest["actor_root"]),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    result: dict[str, Any] = {
        "status": "executed",
        "returncode": completed.returncode,
        "stdout_receipt": _stream_receipt(completed.stdout),
        "stderr_receipt": _stream_receipt(completed.stderr),
        "env_receipt": _operator_env_receipt(environment),
    }
    parse_status, child_summary = _safe_child_result_summary(completed.stdout)
    result["child_result_summary_parse"] = parse_status
    if child_summary is not None:
        result["child_result_summary"] = child_summary
    return result


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


def _peek_next_model(
    queue_root: Path,
    exact_run_ids: Iterable[str] | None = None,
) -> str | None:
    """不 claim 工作，只讀取與 `_claim_next` 相同優先序的下一個 model。"""
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
    sources = list(outbox.glob("*.json")) if outbox.exists() else []
    candidates: list[tuple[int, str, str]] = []
    for source in sources:
        try:
            request = json.loads(source.read_text(encoding="utf-8"))
            validate_external_request(request)
        except (OSError, json.JSONDecodeError, ValueError):
            if exact_namespaces is None:
                candidates.append((2, source.name, ""))
            continue
        if exact_namespaces is not None and str(request["namespace"]) not in exact_namespaces:
            continue
        candidates.append(
            (0 if request["role"] == "reviewer" else 1, source.name, str(request["model"]))
        )
    return min(candidates)[2] if candidates else None


def _restore_unattempted_claim(queue_root: Path, processing_path: Path) -> None:
    """Admission 拒絕時原子放回尚未建立 production attempt 的工作。"""
    target = queue_root / "outbox" / processing_path.name
    if target.exists() or not processing_path.exists():
        raise ValueError("unattempted production claim cannot be restored")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(processing_path, target)
    try:
        processing_path.parent.rmdir()
    except OSError:
        pass


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


def _process_once(
    queue_root: Path,
    *,
    generate_json: GenerateJson = _cli_generate_json,
    clock: Callable[[], float] | None = None,
    lane: str | None = None,
    exact_run_ids: Iterable[str] | None = None,
    acceptance_sealed_replay: bool = False,
    claimed_request_validator: Callable[[dict[str, Any]], None] | None = None,
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
        if acceptance_sealed_replay != (claimed_request_validator is not None):
            raise ValueError("sealed replay internal context is incomplete")
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
        transport_block = (
            None
            if acceptance_sealed_replay
            else _formal_production_transport_block(service_label)
        )
        if transport_block is not None:
            return transport_block
        pool_file = os.environ.get("AGY_GEMINI_CREDENTIAL_POOL_FILE", "").strip()
        production_enabled = (
            not acceptance_sealed_replay
            and claimed_request_validator is None
            and os.environ.get("AGY_GEMINI_V4_BROKER") != "1"
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
            selected_model = _peek_next_model(queue_root, selected_run_ids)
            if selected_model is None:
                return {"status": "idle"}
            if selected_model == "":
                processing_path = _claim_next(queue_root, selected_run_ids)
                if processing_path is None:
                    return {"status": "idle"}
                job_id = processing_path.stem
                archive_path = queue_root / "archive" / f"{job_id}.json"
                request = json.loads(processing_path.read_text(encoding="utf-8"))
                validate_external_request(request)
                raise ValueError("production request selection remained invalid")
            with production_slot_admission(
                production_state_path,
                pool_id=str(pool_payload["pool_id"]),
                manifest_sha256=production_manifest_sha256,
                model=selected_model,
                clock=clock_function,
            ) as admission:
                if not admission.allowed:
                    return {
                        "status": (
                            "quota_blocked"
                            if admission.receipt.get("reason") == QUOTA_REASON
                            else "cooldown"
                        ),
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
                if request["model"] != selected_model:
                    _restore_unattempted_claim(queue_root, processing_path)
                    processing_path = None
                    return {"status": "selection_changed"}
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
            if claimed_request_validator is not None:
                try:
                    claimed_request_validator(request)
                except Exception:
                    _restore_unattempted_claim(queue_root, processing_path)
                    processing_path = None
                    return {
                        "status": "rejected",
                        "reason": "claimed_request_validation_failed",
                    }

        if (
            os.environ.get("AGY_GEMINI_V4_BROKER") == "1"
            and not acceptance_sealed_replay
        ):
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
        quota_receipt: dict[str, object] | None = None
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
        if (
            error_code == QUOTA_REASON
            and credential_pool is not None
            and production_state_path is not None
            and production_manifest_sha256 is not None
            and type(request.get("model")) is str
        ):
            try:
                quota_receipt = record_production_quota_exhausted(
                    production_state_path,
                    pool_id=credential_pool["pool_id"],
                    manifest_sha256=production_manifest_sha256,
                    slot_id=credential_pool["slot_id"],
                    model=str(request["model"]),
                    clock=clock_function,
                )
            except (OSError, ValueError):
                quota_receipt = None
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
        if quota_receipt is not None:
            result["quota_block"] = quota_receipt
        return result
    finally:
        _close_production_attempt(production_attempt_evidence)


def process_once(
    queue_root: Path,
    *,
    generate_json: GenerateJson = _cli_generate_json,
    clock: Callable[[], float] | None = None,
    lane: str | None = None,
    exact_run_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    return _process_once(
        queue_root,
        generate_json=generate_json,
        clock=clock,
        lane=lane,
        exact_run_ids=exact_run_ids,
    )


def _sealed_replay_process_once_for_legacy_tests(
    *,
    queue_root: Path,
    lane: str,
    exact_run_id: str,
    authority_path: Path,
) -> dict[str, Any]:
    """Legacy single-job sealed replay support；不得作為 cohort authority。"""
    actor_root = Path(os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())).resolve()
    authority = _load_acceptance_sealed_replay_authority(authority_path, actor_root)
    if lane != authority.lane:
        raise ValueError("sealed replay lane mismatch")
    if exact_run_id != authority.run_id:
        raise ValueError("sealed replay exact run id mismatch")
    _assert_acceptance_sealed_replay_environment()
    _load_single_pending_sealed_request(queue_root, authority)

    def sealed_transport(
        role: str,
        model: str,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        authority.validate_transport(actor_root, role, model, prompt, response_schema)
        broker_result = run_single_shot(
            operation_id=authority.job_id,
            item_id=authority.namespace,
            attempt_id=ACCEPTANCE_SEALED_REPLAY_ATTEMPT_ID,
            request_sha256=authority.request_sha256,
            model=authority.model,
            executable=authority.executable_path,
            target_profile=RAW_STDIN_PROFILE,
            expected_executable_digest=authority.executable_sha256,
            raw_request=_render_v4_effective_prompt(role, prompt, response_schema),
            response_schema=response_schema,
            timeout_milliseconds=120_000,
            ledger_path=queue_root / "v4" / "ledger" / f"{authority.job_id}.jsonl",
            anchor_store=FileAnchorStore(queue_root / "v4" / "anchors"),
            result_normalizer=normalize_new_output_contract,
        )
        expected_receipt = ExecutionReceipt(
            authority.job_id,
            authority.namespace,
            ACCEPTANCE_SEALED_REPLAY_ATTEMPT_ID,
            authority.request_sha256,
            authority.model,
            RAW_STDIN_PROFILE,
            authority.executable_sha256,
        )
        if (
            broker_result.receipt != expected_receipt
            or not broker_result.caller_contract_satisfied
            or broker_result.result is None
        ):
            raise V4BrokerFailure("sealed replay broker failed closed")
        return broker_result.result

    result = _process_once(
        queue_root,
        generate_json=sealed_transport,
        lane=lane,
        exact_run_ids=[exact_run_id],
        acceptance_sealed_replay=True,
        claimed_request_validator=authority.validate_request,
    )
    if result.get("status") == "processed":
        result["sealed_replay"] = {
            "authority_digest": authority.authority_digest,
            "accepted_base_sha": authority.accepted_base_sha,
            "lane": authority.lane,
            "run_id": authority.run_id,
            "request_sha256": authority.request_sha256,
            "executable_sha256": authority.executable_sha256,
        }
    return result


def sealed_replay_bundle_process_once(
    *,
    queue_root: Path,
    lane: str,
    exact_run_id: str,
    bundle_path: Path,
    expected_bundle_digest: str,
) -> dict[str, Any]:
    """用 sealed bundle session 跑一次正式 runner queue consumption。"""
    actor_root = Path(os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())).resolve()
    queue_root = queue_root.resolve()
    bundle = _load_acceptance_sealed_replay_bundle(
        bundle_path,
        expected_bundle_digest,
        actor_root,
        queue_root,
        lane,
        exact_run_id,
    )
    _assert_acceptance_sealed_replay_environment()
    pending_request, entry = _load_exact_pending_bundle_request(queue_root, bundle)
    used_provider_calls = _trusted_bundle_usage_count(queue_root, bundle)
    if used_provider_calls >= bundle.provider_call_budget:
        raise ValueError("sealed replay bundle provider call budget exhausted")

    def sealed_transport(
        role: str,
        model: str,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        bundle.validate_runtime(actor_root, queue_root, lane, exact_run_id)
        entry.validate_transport(role, model, prompt, response_schema)
        broker_result = run_single_shot(
            operation_id=entry.job_id,
            item_id=entry.namespace,
            attempt_id=_sealed_bundle_attempt_id(entry),
            request_sha256=entry.request_sha256,
            model=entry.model,
            executable=entry.executable_path,
            target_profile=RAW_STDIN_PROFILE,
            expected_executable_digest=entry.executable_sha256,
            raw_request=_render_v4_effective_prompt(role, prompt, response_schema),
            response_schema=response_schema,
            timeout_milliseconds=120_000,
            ledger_path=queue_root / "v4" / "ledger" / f"{entry.job_id}.jsonl",
            anchor_store=FileAnchorStore(queue_root / "v4" / "anchors"),
            result_normalizer=normalize_new_output_contract,
        )
        expected_receipt = ExecutionReceipt(
            entry.job_id,
            entry.namespace,
            _sealed_bundle_attempt_id(entry),
            entry.request_sha256,
            entry.model,
            RAW_STDIN_PROFILE,
            entry.executable_sha256,
        )
        if (
            broker_result.receipt != expected_receipt
            or not broker_result.caller_contract_satisfied
            or broker_result.result is None
        ):
            raise V4BrokerFailure("sealed replay bundle broker failed closed")
        entry.validate_result(broker_result.result)
        return broker_result.result

    result = _process_once(
        queue_root,
        generate_json=sealed_transport,
        lane=lane,
        exact_run_ids=[exact_run_id],
        acceptance_sealed_replay=True,
        claimed_request_validator=entry.validate_request,
    )
    if result.get("status") == "processed":
        result["sealed_replay_bundle"] = {
            "bundle_digest": bundle.bundle_digest,
            "expected_bundle_digest": bundle.expected_bundle_digest,
            "session_id": bundle.session_id,
            "accepted_base_sha": bundle.accepted_base_sha,
            "actor_sha": bundle.actor_sha,
            "generation": bundle.generation,
            "queue_root": str(bundle.queue_root),
            "lane": bundle.lane,
            "run_id": bundle.run_id,
            "request_sha256": pending_request["request_sha256"],
            "job_id": entry.job_id,
            "entry_id": entry.entry_id,
            "used_provider_calls_before_tick": used_provider_calls,
            "provider_call_budget": bundle.provider_call_budget,
        }
    return result


def _bundle_namespace_job_ids(
    queue_root: Path,
    bundle: AcceptanceSealedReplayBundle,
) -> dict[str, list[str]]:
    known = {entry.job_id for entry in bundle.entries}
    known_attempts = {
        f"{entry.job_id}.{_sealed_bundle_attempt_id(entry)}" for entry in bundle.entries
    }
    unknown: dict[str, list[str]] = {}
    for directory in ("outbox", "processing", "inbox", "archive", "failed"):
        root = queue_root / directory
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                payload = _load_json_object(
                    path,
                    label="sealed replay bundle session state",
                    maximum_size=512 * 1024,
                )
            except ValueError:
                unknown.setdefault(directory, []).append(path.stem)
                continue
            job_id = payload.get("job_id", path.stem)
            if type(job_id) is not str or job_id not in known:
                unknown.setdefault(directory, []).append(path.stem)
    ledger_root = queue_root / "v4" / "ledger"
    if ledger_root.exists():
        for path in sorted(ledger_root.glob("*.jsonl")):
            if path.stem not in known:
                unknown.setdefault("v4/ledger", []).append(path.stem)
    anchor_root = queue_root / "v4" / "anchors"
    if anchor_root.exists():
        for path in sorted(anchor_root.glob("*.json")):
            if path.stem not in known_attempts:
                unknown.setdefault("v4/anchors", []).append(path.stem)
    return unknown


def sealed_replay_bundle_close(
    *,
    queue_root: Path,
    lane: str,
    exact_run_id: str,
    bundle_path: Path,
    expected_bundle_digest: str,
) -> dict[str, Any]:
    """只讀驗證 sealed bundle session 是否 exact-closeout；不寫 pipeline state。"""
    actor_root = Path(os.environ.get("PANTHEON_RUNTIME_ACTOR_ROOT", Path.cwd())).resolve()
    queue_root = queue_root.resolve()
    bundle = _load_acceptance_sealed_replay_bundle(
        bundle_path,
        expected_bundle_digest,
        actor_root,
        queue_root,
        lane,
        exact_run_id,
    )
    unknown = _bundle_namespace_job_ids(queue_root, bundle)
    if unknown:
        raise ValueError("sealed replay bundle session has unauthorized state")
    entry_states = {
        entry.entry_id: _classify_bundle_entry_delivery(queue_root, entry)
        for entry in bundle.entries
    }
    incomplete = [
        entry.entry_id
        for entry in bundle.entries
        if entry_states[entry.entry_id]["state"] == "INCOMPLETE"
    ]
    unused_required = [
        entry.entry_id
        for entry in bundle.entries
        if entry.required and entry_states[entry.entry_id]["state"] != "DELIVERED"
    ]
    if incomplete:
        raise ValueError("sealed replay bundle session has incomplete entries")
    if unused_required:
        raise ValueError("sealed replay bundle session has unused required entries")
    delivered = [
        entry.entry_id
        for entry in bundle.entries
        if entry_states[entry.entry_id]["state"] == "DELIVERED"
    ]
    return {
        "status": "closed",
        "sealed_replay_bundle_session": {
            "session_id": bundle.session_id,
            "bundle_digest": bundle.bundle_digest,
            "expected_bundle_digest": bundle.expected_bundle_digest,
            "lane": bundle.lane,
            "run_id": bundle.run_id,
            "required_entries": [
                entry.entry_id for entry in bundle.entries if entry.required
            ],
            "delivered_entries": delivered,
            "entry_states": entry_states,
        },
    }


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
    operator = subparsers.add_parser("operator-exact-process-once")
    operator.add_argument("--manifest", type=Path, required=True)
    operator.add_argument("--expected-digest", required=True)
    operator.add_argument("--barrier", type=Path, required=True)
    operator.add_argument("--service-label", required=True)
    operator.add_argument("--ready-root", type=Path, required=True)
    operator.add_argument("--plist", type=Path, required=True)
    operator.add_argument("--timeout", type=int, default=90)
    sealed_bundle = subparsers.add_parser("sealed-replay-bundle-process-once")
    sealed_bundle.add_argument("--bundle", type=Path, required=True)
    sealed_bundle.add_argument("--expected-bundle-digest", required=True)
    sealed_bundle_close = subparsers.add_parser("sealed-replay-bundle-close")
    sealed_bundle_close.add_argument("--bundle", type=Path, required=True)
    sealed_bundle_close.add_argument("--expected-bundle-digest", required=True)
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
    if args.command == "operator-exact-process-once":
        if not args.exact_run_id or len(args.exact_run_id) != 1:
            print(
                json.dumps(
                    {
                        "status": "rejected",
                        "error": "formal operator requires exactly one exact run id",
                    },
                    ensure_ascii=False,
                )
            )
            return 64
        try:
            result = operator_exact_process_once(
                manifest_path=args.manifest.resolve(),
                expected_digest=args.expected_digest,
                barrier=args.barrier.resolve(),
                service_label=args.service_label,
                ready_root=args.ready_root.resolve(),
                plist=args.plist.resolve(),
                exact_run_id=args.exact_run_id[0],
                timeout=args.timeout,
            )
        except (OSError, ValueError, formal_runtime.RuntimeManifestError) as error:
            print(
                json.dumps(
                    {"status": "rejected", "error": str(error)},
                    ensure_ascii=False,
                )
            )
            return 1
        print(json.dumps(result, ensure_ascii=False))
        if result["status"] in {"blocked", "rejected"}:
            return 1
        if result["status"] == "executed":
            returncode = result.get("returncode")
            if type(returncode) is int and returncode != 0:
                return returncode if 1 <= returncode <= 255 else 1
        return 0
    if args.command == "process-once":
        result = process_once(
            queue_root,
            lane=args.lane,
            exact_run_ids=args.exact_run_id,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result["status"] == "failed" else 0
    if args.command == "sealed-replay-bundle-process-once":
        if not args.lane or not args.exact_run_id or len(args.exact_run_id) != 1:
            print(
                json.dumps(
                    {
                        "status": "rejected",
                        "error": "sealed replay bundle requires one lane and one exact run id",
                    },
                    ensure_ascii=False,
                )
            )
            return 64
        try:
            result = sealed_replay_bundle_process_once(
                queue_root=queue_root,
                lane=args.lane,
                exact_run_id=args.exact_run_id[0],
                bundle_path=args.bundle,
                expected_bundle_digest=args.expected_bundle_digest,
            )
        except (OSError, ValueError, V4BrokerFailure) as error:
            print(
                json.dumps(
                    {"status": "rejected", "error": str(error)},
                    ensure_ascii=False,
                )
            )
            return 64
        print(json.dumps(result, ensure_ascii=False))
        if result["status"] == "rejected":
            return 64
        return 1 if result["status"] == "failed" else 0
    if args.command == "sealed-replay-bundle-close":
        if not args.lane or not args.exact_run_id or len(args.exact_run_id) != 1:
            print(
                json.dumps(
                    {
                        "status": "rejected",
                        "error": "sealed replay bundle close requires one lane and one exact run id",
                    },
                    ensure_ascii=False,
                )
            )
            return 64
        try:
            result = sealed_replay_bundle_close(
                queue_root=queue_root,
                lane=args.lane,
                exact_run_id=args.exact_run_id[0],
                bundle_path=args.bundle,
                expected_bundle_digest=args.expected_bundle_digest,
            )
        except (OSError, ValueError, V4BrokerFailure) as error:
            print(
                json.dumps(
                    {"status": "rejected", "error": str(error)},
                    ensure_ascii=False,
                )
            )
            return 64
        print(json.dumps(result, ensure_ascii=False))
        return 0
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

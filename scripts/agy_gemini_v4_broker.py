#!/usr/bin/env python3
"""Gemini V4 單次 broker；以 ledger replay 決定是否可交付 caller result。"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, Literal, NoReturn, Protocol


COMMAND_SCHEMA_VERSION: Final = 2
EVENT_SCHEMA_VERSION: Final = 2
MAX_FRAME_BYTES: Final = 64 * 1024
MAX_RESULT_BYTES: Final = 2 * 1024 * 1024
MAX_AGY_ENVELOPE_OVERHEAD_BYTES: Final = 64 * 1024
MAX_AGY_PROMPT_BYTES: Final = 384 * 1024
MAX_SCHEMA_DIAGNOSTICS: Final = 3
MAX_SCHEMA_DIAGNOSTIC_DEPTH: Final = 8
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
EVENT_TYPES: Final = {
    "OPERATION_CREATED",
    "PREFLIGHT_REJECTED",
    "BROKER_ATTEMPTED",
    "BROKER_ABORTED",
    "FORK_ATTEMPTED",
    "EXEC_FAILURE",
    "EXEC_CONFIRMED",
    "PROCESS_TERMINAL",
}
BASE_FIELDS: Final = {
    "schema_version",
    "sequence",
    "parent_sha256",
    "event_type",
    "operation_id",
    "item_id",
    "attempt_id",
}
EVENT_FIELDS: Final = {
    "OPERATION_CREATED": {},
    "PREFLIGHT_REJECTED": {"outcome": str},
    "BROKER_ATTEMPTED": {"broker_attempt": int},
    "BROKER_ABORTED": {"outcome": str},
    "FORK_ATTEMPTED": {"broker_attempt": int, "process_ordinal": int},
    "EXEC_FAILURE": {"outcome": str, "process_ordinal": int},
    "EXEC_CONFIRMED": {"process_ordinal": int, "pid": int},
    "PROCESS_TERMINAL": {"outcome": str},
}
LEGAL_REPLAY_STATES: Final = {
    ("OPERATION_CREATED", "PREFLIGHT_REJECTED"): ("COMPLETE", 0, ()),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "BROKER_ABORTED"): ("BLOCKED", 0, ()),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED", "EXEC_FAILURE"): ("BLOCKED", 0, ()),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED"): ("AMBIGUOUS", "UNKNOWN", ("BROKER_CRASH_WINDOW",)),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED"): (
        "AMBIGUOUS", "UNKNOWN", ("EXEC_CONFIRMATION_MISSING",)
    ),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED", "EXEC_CONFIRMED"): (
        "BLOCKED", 1, ("PROCESS_TERMINAL_MISSING",)
    ),
    (
        "OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED",
        "EXEC_CONFIRMED", "PROCESS_TERMINAL",
    ): ("COMPLETE", 1, ()),
}
CONTROL_FIELDS: Final = {
    "replay_status",
    "process_count",
    "outcome",
    "exit_status",
    "stdout_sha256",
    "stderr_sha256",
    "byte_count",
    "final_anchor",
    "target_diagnostic",
}
RAW_STDIN_PROFILE: Final = "raw_stdin_v1"
ANTIGRAVITY_CLI_PROFILE: Final = "antigravity_cli_v1"
GEMINI_STRUCTURED_API_PROFILE: Final = "gemini_structured_api_v1"
PUBLIC_SANITIZED: Final = "PUBLIC_SANITIZED"
PUBLIC_STRUCTURED: Final = "PUBLIC_STRUCTURED"
SYNTHETIC_TEST: Final = "SYNTHETIC_TEST"
RESULT_VALIDATION_STATES: Final = frozenset({
    "NOT_EVALUATED",
    "JSON_INVALID",
    "NOT_OBJECT",
    "SCHEMA_MISMATCH",
    "VALID",
})
SCHEMA_DIAGNOSTIC_KEYWORDS: Final = frozenset({
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
AGY_MODEL_LABELS: Final = {
    "gemini-3.5-flash": "Gemini 3.5 Flash (Low)",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro (Low)",
}
API_MODEL_LABELS: Final = {
    "gemini-3.5-flash": "gemini-3.5-flash",
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
}
TARGET_ENV_ALLOWLIST: Final = (
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "TMPDIR",
    "__CF_USER_TEXT_ENCODING",
)
STRUCTURED_TARGET_ENV_ALLOWLIST: Final = (
    "LANG",
    "LC_ALL",
    "PATH",
    "TMPDIR",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "__CF_USER_TEXT_ENCODING",
)
STRUCTURED_TARGET_DIAGNOSTICS: Final = frozenset(
    {
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
    }
)
FORBIDDEN_PUBLIC_PROMPT_PATTERNS: Final = (
    re.compile(r"/(?:Users|home|private|var|tmp)/"),
    re.compile(r"\.work/"),
    re.compile(r"GEMINI_API_KEY", re.IGNORECASE),
    re.compile(r"x-goog-api-key", re.IGNORECASE),
    re.compile(r"authorization\s*:\s*bearer", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?:ghp|github_pat)_[0-9A-Za-z_]{20,}"),
)


class FrameError(ValueError):
    """Wire frame 不完整或不符合 closed schema。"""


class AnchorError(RuntimeError):
    """External anchor 無法載入或 CAS 失敗。"""


class V4BrokerFailure(RuntimeError):
    """Runner 可記錄但不可 fallback 的 V4 fail-closed 結果。"""


ProcessCount = int | Literal["UNKNOWN"]
JsonDiagnostic = Literal[
    "EMPTY",
    "UTF8_INVALID",
    "MARKDOWN_FENCE",
    "WRAPPED_JSON",
    "PARSE_ERROR_AT_END",
    "PARSE_ERROR_OTHER",
]


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_nonfinite_constant(_constant: str) -> NoReturn:
    raise ValueError("non-finite JSON constant is invalid")


def _strict_json_loads(value: str | bytes | bytearray) -> Any:
    return json.loads(value, parse_constant=_reject_nonfinite_constant)


def _is_finite_json_number(value: object) -> bool:
    return type(value) is int or (
        type(value) is float and math.isfinite(value)
    )


def _is_valid_numeric_bound(value: object, schema_type: str) -> bool:
    if schema_type == "integer":
        return type(value) is int
    return _is_finite_json_number(value)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _valid_identifier(value: object) -> bool:
    return type(value) is str and IDENTIFIER.fullmatch(value) is not None


def _valid_sha256(value: object) -> bool:
    return type(value) is str and HEX_SHA256.fullmatch(value) is not None


def encode_frame(payload: object) -> bytes:
    encoded = canonical_json(payload)
    if not encoded or len(encoded) > MAX_FRAME_BYTES:
        raise FrameError("frame size is invalid")
    return len(encoded).to_bytes(4, "big") + encoded


def _decode_frame(encoded: bytes) -> object:
    if len(encoded) < 4:
        raise FrameError("frame header is truncated")
    length = int.from_bytes(encoded[:4], "big")
    if length < 1 or length > MAX_FRAME_BYTES or len(encoded) != length + 4:
        raise FrameError("frame length is invalid")
    try:
        return _strict_json_loads(encoded[4:])
    except (ValueError, UnicodeDecodeError) as error:
        raise FrameError("frame JSON is invalid") from error


def _read_exact_fd(descriptor: int, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        chunk = os.read(descriptor, length - len(chunks))
        if not chunk:
            raise FrameError("frame is truncated")
        chunks.extend(chunk)
    return bytes(chunks)


def _read_framed_fd(descriptor: int) -> bytes:
    header = _read_exact_fd(descriptor, 4)
    length = int.from_bytes(header, "big")
    if length < 1 or length > MAX_FRAME_BYTES:
        raise FrameError("frame length is invalid")
    return header + _read_exact_fd(descriptor, length)


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        offset += os.write(descriptor, payload[offset:])


@dataclass(frozen=True)
class Binding:
    operation_id: str
    item_id: str
    attempt_id: str

    def validate(self) -> None:
        if not all(_valid_identifier(value) for value in (self.operation_id, self.item_id, self.attempt_id)):
            raise ValueError("binding identifiers must be opaque and path-free")


@dataclass(frozen=True)
class CommandFrame:
    schema_version: int
    operation_id: str
    item_id: str
    attempt_id: str
    executable_digest: str
    request_sha256: str
    request_bytes_length: int
    timeout_milliseconds: int
    target_profile: str
    model_label: str
    payload_class: str

    def validate(self) -> None:
        Binding(self.operation_id, self.item_id, self.attempt_id).validate()
        if type(self.schema_version) is not int or self.schema_version != COMMAND_SCHEMA_VERSION:
            raise FrameError("command schema version is invalid")
        if not _valid_sha256(self.executable_digest) or not _valid_sha256(self.request_sha256):
            raise FrameError("command digest is invalid")
        if type(self.request_bytes_length) is not int or not 0 <= self.request_bytes_length <= MAX_RESULT_BYTES:
            raise FrameError("request length is invalid")
        if type(self.timeout_milliseconds) is not int or not 1 <= self.timeout_milliseconds <= 3_600_000:
            raise FrameError("timeout is invalid")
        if self.target_profile not in {
            RAW_STDIN_PROFILE,
            ANTIGRAVITY_CLI_PROFILE,
            GEMINI_STRUCTURED_API_PROFILE,
        }:
            raise FrameError("target profile is invalid")
        if type(self.model_label) is not str or not self.model_label:
            raise FrameError("model label is invalid")
        expected_payload_class = {
            RAW_STDIN_PROFILE: SYNTHETIC_TEST,
            ANTIGRAVITY_CLI_PROFILE: PUBLIC_SANITIZED,
            GEMINI_STRUCTURED_API_PROFILE: PUBLIC_STRUCTURED,
        }[self.target_profile]
        if self.payload_class != expected_payload_class:
            raise FrameError("payload class is invalid")
        if self.target_profile == ANTIGRAVITY_CLI_PROFILE and self.model_label not in AGY_MODEL_LABELS.values():
            raise FrameError("agy model label is invalid")
        if (
            self.target_profile == GEMINI_STRUCTURED_API_PROFILE
            and self.model_label not in API_MODEL_LABELS.values()
        ):
            raise FrameError("Gemini API model label is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "operation_id": self.operation_id,
            "item_id": self.item_id,
            "attempt_id": self.attempt_id,
            "executable_digest": self.executable_digest,
            "request_sha256": self.request_sha256,
            "request_bytes_length": self.request_bytes_length,
            "timeout_milliseconds": self.timeout_milliseconds,
            "target_profile": self.target_profile,
            "model_label": self.model_label,
            "payload_class": self.payload_class,
        }


def decode_command_frame(encoded: bytes) -> CommandFrame:
    payload = _decode_frame(encoded)
    if not isinstance(payload, dict) or set(payload) != set(CommandFrame.__dataclass_fields__):
        raise FrameError("command fields are not closed")
    try:
        command = CommandFrame(**payload)
    except TypeError as error:
        raise FrameError("command fields are invalid") from error
    command.validate()
    return command


@dataclass(frozen=True)
class ReplayResult:
    status: str
    process_count: ProcessCount
    complete: bool
    errors: tuple[str, ...]
    automatic_resend_allowed: bool = False


@dataclass(frozen=True)
class ExecutionReceipt:
    operation_id: str
    item_id: str
    attempt_id: str
    request_sha256: str
    model: str
    target_profile: str
    executable_digest: str


@dataclass(frozen=True)
class SchemaDiagnostic:
    keyword: str
    path: tuple[str | int, ...]


def _diagnose_json_invalid(
    raw: bytes,
    error: ValueError | UnicodeDecodeError,
) -> JsonDiagnostic:
    if not raw.strip():
        return "EMPTY"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "UTF8_INVALID"
    stripped = text.strip()
    if stripped.startswith("```") or stripped.endswith("```"):
        return "MARKDOWN_FENCE"
    first_object = text.find("{")
    last_object = text.rfind("}")
    if first_object >= 0 and last_object > first_object:
        try:
            embedded = _strict_json_loads(text[first_object:last_object + 1])
        except (ValueError, UnicodeDecodeError):
            pass
        else:
            if isinstance(embedded, dict):
                return "WRAPPED_JSON"
    if isinstance(error, json.JSONDecodeError) and error.pos >= len(text.rstrip()):
        return "PARSE_ERROR_AT_END"
    return "PARSE_ERROR_OTHER"


@dataclass(frozen=True)
class BrokerResult:
    replay_status: str
    process_count: ProcessCount
    outcome: str | None
    exit_status: int | None
    stdout_sha256: str | None
    stderr_sha256: str | None
    byte_count: int
    final_anchor: str | None
    receipt: ExecutionReceipt
    caller_contract_satisfied: bool
    result_json: bytes | None
    errors: tuple[str, ...]
    automatic_resend_allowed: bool = False
    result_validation: str = "NOT_EVALUATED"
    schema_diagnostics: tuple[SchemaDiagnostic, ...] = ()
    json_diagnostic: JsonDiagnostic | None = None
    target_diagnostic: str | None = None

    @property
    def result(self) -> dict[str, Any] | None:
        if self.result_json is None:
            return None
        decoded = _strict_json_loads(self.result_json)
        return decoded if isinstance(decoded, dict) else None

    def normalized_trace(self) -> dict[str, object]:
        return {
            "replay_status": self.replay_status,
            "process_count": self.process_count,
            "outcome": self.outcome,
            "exit_status": self.exit_status,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "byte_count": self.byte_count,
            "receipt": self.receipt.__dict__,
            "caller_contract_satisfied": self.caller_contract_satisfied,
            "result_validation": self.result_validation,
            "result": self.result,
            "errors": list(self.errors),
            "automatic_resend_allowed": self.automatic_resend_allowed,
        }

class AnchorStore(Protocol):
    def load(self, operation_id: str, attempt_id: str) -> str | None: ...

    def compare_and_swap(
        self, operation_id: str, attempt_id: str, previous_anchor: str | None, next_anchor: str
    ) -> bool: ...


class FileAnchorStore:
    """Coordinator-owned anchor store；ledger 不會自行讀寫這些檔案。"""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, operation_id: str, attempt_id: str) -> Path:
        Binding(operation_id, "anchor-item", attempt_id).validate()
        return self.root / f"{operation_id}.{attempt_id}.json"

    def load(self, operation_id: str, attempt_id: str) -> str | None:
        path = self._path(operation_id, attempt_id)
        if not path.exists():
            return None
        try:
            payload = _strict_json_loads(path.read_bytes())
        except (ValueError, UnicodeDecodeError, OSError) as error:
            raise AnchorError("anchor cannot be loaded") from error
        expected = {"schema_version", "operation_id", "attempt_id", "anchor"}
        if (
            not isinstance(payload, dict)
            or set(payload) != expected
            or payload.get("schema_version") != 1
            or payload.get("operation_id") != operation_id
            or payload.get("attempt_id") != attempt_id
            or not _valid_sha256(payload.get("anchor"))
        ):
            raise AnchorError("anchor schema or binding is invalid")
        return str(payload["anchor"])

    def compare_and_swap(
        self, operation_id: str, attempt_id: str, previous_anchor: str | None, next_anchor: str
    ) -> bool:
        if not _valid_sha256(next_anchor):
            raise AnchorError("next anchor is invalid")
        if self.load(operation_id, attempt_id) != previous_anchor:
            return False
        path = self._path(operation_id, attempt_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json({
            "schema_version": 1,
            "operation_id": operation_id,
            "attempt_id": attempt_id,
            "anchor": next_anchor,
        }) + b"\n"
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True


def _schema_errors(event: dict[str, object]) -> list[str]:
    kind = event.get("event_type")
    if kind not in EVENT_TYPES:
        return ["UNKNOWN_EVENT"]
    specific = EVENT_FIELDS[str(kind)]
    expected = BASE_FIELDS | set(specific)
    errors: list[str] = []
    if set(event) - expected:
        errors.append("UNKNOWN_FIELD")
    if expected - set(event):
        errors.append("MISSING_FIELD")
    if type(event.get("schema_version")) is not int or event.get("schema_version") != EVENT_SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION")
    if type(event.get("sequence")) is not int or int(event.get("sequence", 0)) < 1:
        errors.append("SEQUENCE_TYPE")
    for field in ("event_type", "operation_id", "item_id", "attempt_id"):
        if type(event.get(field)) is not str or not event.get(field):
            errors.append(f"{field.upper()}_TYPE")
    parent = event.get("parent_sha256")
    if parent is not None and not _valid_sha256(parent):
        errors.append("PARENT_TYPE")
    for field, expected_type in specific.items():
        if type(event.get(field)) is not expected_type:
            errors.append(f"{field.upper()}_TYPE")
    if kind == "EXEC_CONFIRMED" and type(event.get("pid")) is int and int(event["pid"]) <= 0:
        errors.append("PID_VALUE")
    if event.get("broker_attempt") not in {None, 1}:
        errors.append("BROKER_ATTEMPT_VALUE")
    if event.get("process_ordinal") not in {None, 1}:
        errors.append("PROCESS_ORDINAL")
    if kind == "PREFLIGHT_REJECTED" and event.get("outcome") != "CLI_NOT_FOUND":
        errors.append("PREFLIGHT_OUTCOME")
    if kind == "BROKER_ABORTED" and event.get("outcome") != "CRASH_BEFORE_FORK":
        errors.append("BROKER_ABORT_OUTCOME")
    if kind == "EXEC_FAILURE" and event.get("outcome") not in {"CLI_NOT_FOUND", "PERMISSION_DENIED", "EXEC_FORMAT", "EXEC_RACE"}:
        errors.append("EXEC_FAILURE_OUTCOME")
    if kind == "PROCESS_TERMINAL" and event.get("outcome") not in {"SUCCESS", "CLI_NONZERO", "CLI_TIMEOUT"}:
        errors.append("TERMINAL_OUTCOME")
    return errors


def replay_ledger(path: Path, expected: Binding, external_anchor: str | None) -> ReplayResult:
    expected.validate()
    raw = path.read_bytes() if path.exists() else b""
    errors: list[str] = []
    events: list[dict[str, object]] = []
    parent: str | None = None
    if raw and not raw.endswith(b"\n"):
        errors.append("PARTIAL_FRAME")
    for index, frame in enumerate(raw.splitlines(keepends=True), 1):
        if not frame.endswith(b"\n"):
            continue
        try:
            event = _strict_json_loads(frame)
        except (ValueError, UnicodeDecodeError):
            errors.append("INVALID_JSON")
            continue
        if not isinstance(event, dict):
            errors.append("INVALID_EVENT")
            continue
        errors.extend(_schema_errors(event))
        if event.get("sequence") != index:
            errors.append("SEQUENCE_GAP_OR_DUPLICATE")
        if event.get("parent_sha256") != parent:
            errors.append("HASH_CHAIN_MISMATCH")
        if (event.get("operation_id"), event.get("item_id"), event.get("attempt_id")) != (
            expected.operation_id, expected.item_id, expected.attempt_id
        ):
            errors.append("BINDING_MISMATCH")
        parent = _sha256(canonical_json(event))
        events.append(event)
    if raw and external_anchor is None:
        errors.append("EXTERNAL_ANCHOR_MISSING")
    elif external_anchor is not None and parent != external_anchor:
        errors.append("EXTERNAL_ANCHOR_MISMATCH")
    types = tuple(str(event.get("event_type")) for event in events)
    state = LEGAL_REPLAY_STATES.get(types)
    if state is None:
        status: str = "INVALID"
        count: ProcessCount = "UNKNOWN"
        errors.append("ILLEGAL_EVENT_ORDER")
    else:
        status, count, state_errors = state
        errors.extend(state_errors)
    validation_errors = set(errors) - {"BROKER_CRASH_WINDOW", "EXEC_CONFIRMATION_MISSING", "PROCESS_TERMINAL_MISSING"}
    if validation_errors:
        status, count = "INVALID", "UNKNOWN"
    return ReplayResult(status, count, status == "COMPLETE", tuple(sorted(set(errors))))


class _LedgerWriter:
    def __init__(self, descriptor: int, anchor_socket: socket.socket, binding: Binding) -> None:
        self.descriptor = descriptor
        self.anchor_socket = anchor_socket
        self.binding = binding
        self.sequence = 0
        self.anchor: str | None = None
        os.set_inheritable(descriptor, False)

    def append(self, event_type: str, **fields: object) -> None:
        self.sequence += 1
        event = {
            "schema_version": EVENT_SCHEMA_VERSION,
            "sequence": self.sequence,
            "parent_sha256": self.anchor,
            "event_type": event_type,
            "operation_id": self.binding.operation_id,
            "item_id": self.binding.item_id,
            "attempt_id": self.binding.attempt_id,
            **fields,
        }
        next_anchor = _sha256(canonical_json(event))
        _write_all(self.descriptor, canonical_json(event) + b"\n")
        os.fsync(self.descriptor)
        self.anchor_socket.sendall(encode_frame({"previous_anchor": self.anchor, "next_anchor": next_anchor}))
        response = _decode_frame(_recv_frame(self.anchor_socket))
        if response != {"ok": True}:
            raise AnchorError("coordinator rejected anchor CAS")
        self.anchor = next_anchor


def _recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        chunk = sock.recv(length - len(chunks))
        if not chunk:
            if not chunks:
                return b""
            raise FrameError("socket frame is truncated")
        chunks.extend(chunk)
    return bytes(chunks)


def _recv_frame(sock: socket.socket) -> bytes:
    header = _recv_exact(sock, 4)
    if not header:
        return b""
    length = int.from_bytes(header, "big")
    if length < 1 or length > MAX_FRAME_BYTES:
        raise FrameError("socket frame length is invalid")
    return header + _recv_exact(sock, length)


def _control(
    status: str, count: ProcessCount, outcome: str | None, exit_status: int | None,
    stdout: bytes, stderr: bytes, anchor: str | None, target_diagnostic: str | None = None,
) -> dict[str, object]:
    return {
        "replay_status": status,
        "process_count": count,
        "outcome": outcome,
        "exit_status": exit_status,
        "stdout_sha256": _sha256(stdout),
        "stderr_sha256": _sha256(stderr),
        "byte_count": len(stdout),
        "final_anchor": anchor,
        "target_diagnostic": target_diagnostic,
    }


def _structured_target_diagnostic(
    target_profile: str,
    outcome: str,
    stderr: bytes,
) -> str | None:
    if target_profile != GEMINI_STRUCTURED_API_PROFILE or outcome != "CLI_NONZERO":
        return None
    try:
        diagnostic = stderr.decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    if "\n" in diagnostic or diagnostic not in STRUCTURED_TARGET_DIAGNOSTICS:
        return None
    return diagnostic


def _exec_failure_outcome(error: OSError, executable_existed: bool) -> str:
    if error.errno == errno.ENOENT:
        return "EXEC_RACE" if executable_existed else "CLI_NOT_FOUND"
    if error.errno == errno.EACCES:
        return "PERMISSION_DENIED"
    return "EXEC_FORMAT"


def _emit_broker_result(anchor_socket: socket.socket, result_fd: int, control: dict[str, object], raw: bytes) -> None:
    anchor_socket.close()
    if raw:
        _write_all(result_fd, raw)
    os.close(result_fd)
    sys.stdout.buffer.write(encode_frame(control))
    sys.stdout.buffer.flush()


def _validate_public_prompt(raw_request: bytes) -> str:
    if not raw_request or len(raw_request) > MAX_AGY_PROMPT_BYTES:
        raise ValueError("agy prompt size is invalid")
    try:
        prompt = raw_request.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("agy prompt must be UTF-8 public text") from error
    if any(pattern.search(prompt) for pattern in FORBIDDEN_PUBLIC_PROMPT_PATTERNS):
        raise ValueError("agy prompt contains forbidden private data")
    return prompt


def _target_invocation(
    command: CommandFrame,
    executable: Path,
    raw_request: bytes,
    log_path: Path | None,
    credential_fd: int | None,
) -> tuple[list[str], bytes, dict[str, str], tuple[int, ...]]:
    if command.target_profile == RAW_STDIN_PROFILE:
        return [str(executable)], raw_request, {}, ()
    if command.target_profile == GEMINI_STRUCTURED_API_PROFILE:
        if credential_fd is None or credential_fd < 3:
            raise FrameError("structured target credential fd is required")
        timeout_seconds = (command.timeout_milliseconds + 999) // 1000
        environment = {
            key: os.environ[key]
            for key in STRUCTURED_TARGET_ENV_ALLOWLIST
            if key in os.environ
        }
        return (
            [
                str(executable),
                "--model",
                command.model_label,
                "--credential-fd",
                str(credential_fd),
                "--timeout-seconds",
                str(timeout_seconds),
            ],
            raw_request,
            environment,
            (credential_fd,),
        )
    if log_path is None:
        raise FrameError("agy log path is required")
    prompt = raw_request.decode("utf-8")
    timeout_seconds = (command.timeout_milliseconds + 999) // 1000
    arguments = [
        str(executable),
        "--model",
        command.model_label,
        "--mode",
        "plan",
        "--sandbox",
        "--log-file",
        str(log_path),
        "--print-timeout",
        f"{timeout_seconds}s",
        "--print",
        prompt,
    ]
    environment = {key: os.environ[key] for key in TARGET_ENV_ALLOWLIST if key in os.environ}
    return arguments, b"", environment, ()


def _write_executable_snapshot(directory: Path, executable_bytes: bytes) -> Path:
    snapshot = directory / "verified-target"
    descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o500)
    try:
        _write_all(descriptor, executable_bytes)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(directory, 0o500)
    return snapshot


def _broker_entry(
    command_fd: int,
    ledger_fd: int,
    anchor_fd: int,
    result_fd: int,
    executable: Path,
    credential_fd: int | None,
) -> int:
    anchor_socket = socket.socket(fileno=anchor_fd)
    try:
        command = decode_command_frame(_read_framed_fd(command_fd))
        os.close(command_fd)
        raw_request = sys.stdin.buffer.read(MAX_RESULT_BYTES + 1)
        if len(raw_request) != command.request_bytes_length or _sha256(raw_request) != command.request_sha256:
            raise FrameError("raw request binding is invalid")
        binding = Binding(command.operation_id, command.item_id, command.attempt_id)
        writer = _LedgerWriter(ledger_fd, anchor_socket, binding)
        writer.append("OPERATION_CREATED")
        if not executable.exists() or not os.access(executable, os.X_OK):
            writer.append("PREFLIGHT_REJECTED", outcome="CLI_NOT_FOUND")
            _emit_broker_result(anchor_socket, result_fd, _control("COMPLETE", 0, "CLI_NOT_FOUND", None, b"", b"", writer.anchor), b"")
            return 0
        writer.append("BROKER_ATTEMPTED", broker_attempt=1)
        try:
            digest = _sha256(executable.read_bytes())
        except OSError:
            writer.append("BROKER_ABORTED", outcome="CRASH_BEFORE_FORK")
            _emit_broker_result(
                anchor_socket,
                result_fd,
                _control("BLOCKED", 0, "CRASH_BEFORE_FORK", None, b"", b"", writer.anchor),
                b"",
            )
            return 0
        if digest != command.executable_digest:
            writer.append("BROKER_ABORTED", outcome="CRASH_BEFORE_FORK")
            _emit_broker_result(
                anchor_socket,
                result_fd,
                _control("BLOCKED", 0, "CRASH_BEFORE_FORK", None, b"", b"", writer.anchor),
                b"",
            )
            return 0
        writer.append("FORK_ATTEMPTED", broker_attempt=1, process_ordinal=1)
        existed = executable.exists()
        temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        target: subprocess.Popen[bytes] | None = None
        try:
            log_path: Path | None = None
            if command.target_profile == ANTIGRAVITY_CLI_PROFILE:
                temporary_directory = tempfile.TemporaryDirectory(prefix="agy-v4-")
                log_path = Path(temporary_directory.name) / "agy.log"
            arguments, target_input, target_environment, target_pass_fds = _target_invocation(
                command,
                executable,
                raw_request,
                log_path,
                credential_fd,
            )
            try:
                target = subprocess.Popen(
                    arguments,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    pass_fds=target_pass_fds,
                    env=target_environment,
                )
                if credential_fd is not None:
                    os.close(credential_fd)
                    credential_fd = None
            except OSError as error:
                outcome = _exec_failure_outcome(error, existed)
                writer.append("EXEC_FAILURE", outcome=outcome, process_ordinal=1)
                _emit_broker_result(
                    anchor_socket,
                    result_fd,
                    _control("BLOCKED", 0, outcome, None, b"", b"", writer.anchor),
                    b"",
                )
                return 0
            writer.append("EXEC_CONFIRMED", process_ordinal=1, pid=target.pid)
            try:
                stdout, stderr = target.communicate(
                    input=target_input, timeout=command.timeout_milliseconds / 1000
                )
                outcome = "SUCCESS" if target.returncode == 0 else "CLI_NONZERO"
                exit_status = target.returncode
            except subprocess.TimeoutExpired:
                target.kill()
                stdout, stderr = target.communicate()
                outcome = "CLI_TIMEOUT"
                exit_status = None
            if len(stdout) > MAX_RESULT_BYTES or len(stderr) > MAX_RESULT_BYTES:
                stdout, stderr, outcome, exit_status = b"", b"", "CLI_NONZERO", target.returncode
            writer.append("PROCESS_TERMINAL", outcome=outcome)
            target_diagnostic = _structured_target_diagnostic(
                command.target_profile,
                outcome,
                stderr,
            )
            _emit_broker_result(
                anchor_socket,
                result_fd,
                _control(
                    "COMPLETE",
                    1,
                    outcome,
                    exit_status,
                    stdout,
                    stderr,
                    writer.anchor,
                    target_diagnostic,
                ),
                stdout,
            )
            return 0
        finally:
            if target is not None:
                if target.poll() is None:
                    target.kill()
                target.wait()
                for pipe in (target.stdin, target.stdout, target.stderr):
                    if pipe is not None:
                        pipe.close()
            if temporary_directory is not None:
                temporary_directory.cleanup()
    except Exception:
        try:
            anchor_socket.close()
        finally:
            try:
                os.close(result_fd)
            except OSError:
                pass
        return 70
    finally:
        if credential_fd is not None:
            try:
                os.close(credential_fd)
            except OSError:
                pass
        try:
            os.close(ledger_fd)
        except OSError:
            pass


def _validate_control(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict) or set(payload) != CONTROL_FIELDS:
        raise FrameError("control fields are not closed")
    if payload["replay_status"] not in {"COMPLETE", "BLOCKED", "AMBIGUOUS", "INVALID"}:
        raise FrameError("control status is invalid")
    if payload["process_count"] not in {0, 1, "UNKNOWN"} or type(payload["process_count"]) is bool:
        raise FrameError("control process count is invalid")
    if type(payload["byte_count"]) is not int or int(payload["byte_count"]) < 0:
        raise FrameError("control byte count is invalid")
    for field in ("stdout_sha256", "stderr_sha256", "final_anchor"):
        if payload[field] is not None and not _valid_sha256(payload[field]):
            raise FrameError(f"control {field} is invalid")
    if payload["exit_status"] is not None and type(payload["exit_status"]) is not int:
        raise FrameError("control exit status is invalid")
    if payload["outcome"] is not None and type(payload["outcome"]) is not str:
        raise FrameError("control outcome is invalid")
    if (
        payload["target_diagnostic"] is not None
        and (
            type(payload["target_diagnostic"]) is not str
            or payload["target_diagnostic"] not in STRUCTURED_TARGET_DIAGNOSTICS
        )
    ):
        raise FrameError("control target diagnostic is invalid")
    if payload["target_diagnostic"] is not None and payload["outcome"] != "CLI_NONZERO":
        raise FrameError("control target diagnostic has invalid outcome")
    return payload


def _validate_json_schema(value: object, schema: object) -> bool:
    return not _diagnose_json_schema(value, schema)


def _diagnose_json_schema(
    value: object,
    schema: object,
    path: tuple[str | int, ...] = (),
) -> tuple[SchemaDiagnostic, ...]:
    diagnostics: list[SchemaDiagnostic] = []

    def add(keyword: str, diagnostic_path: tuple[str | int, ...]) -> None:
        if len(diagnostics) >= MAX_SCHEMA_DIAGNOSTICS:
            return
        if len(diagnostic_path) > MAX_SCHEMA_DIAGNOSTIC_DEPTH:
            keyword = "schema"
            diagnostic_path = diagnostic_path[:MAX_SCHEMA_DIAGNOSTIC_DEPTH]
        diagnostics.append(SchemaDiagnostic(keyword, diagnostic_path))

    if not isinstance(schema, dict) or type(schema.get("type")) is not str:
        add("schema", path)
        return tuple(diagnostics)
    expected_type = schema["type"]
    type_ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": type(value) is str,
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": _is_finite_json_number(value),
        "null": value is None,
    }.get(expected_type, False)
    enum = schema.get("enum")
    if "enum" in schema and not isinstance(enum, list):
        add("schema", path)
        return tuple(diagnostics)
    if not type_ok:
        add("type", path)
        return tuple(diagnostics)
    if enum is not None and value not in enum:
        add("enum", path)
        return tuple(diagnostics)
    if expected_type == "object":
        properties = schema.get("properties")
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list) or not all(type(item) is str for item in required):
            add("schema", path)
            return tuple(diagnostics)
        assert isinstance(value, dict)
        for key in required:
            if key not in value:
                add("required", path + (key,))
        if schema.get("additionalProperties") is False and not set(value) <= set(properties):
            add("additionalProperties", path)
        for key in sorted(value):
            if key not in properties or len(diagnostics) >= MAX_SCHEMA_DIAGNOSTICS:
                continue
            diagnostics.extend(
                _diagnose_json_schema(value[key], properties[key], path + (key,))[
                    : MAX_SCHEMA_DIAGNOSTICS - len(diagnostics)
                ]
            )
        return tuple(diagnostics)
    if expected_type == "array":
        assert isinstance(value, list)
        minimum, maximum = schema.get("minItems", 0), schema.get("maxItems", MAX_RESULT_BYTES)
        if type(minimum) is not int or type(maximum) is not int:
            add("schema", path)
            return tuple(diagnostics)
        if len(value) < minimum:
            add("minItems", path)
        if len(value) > maximum:
            add("maxItems", path)
            return tuple(diagnostics)
        for index, item in enumerate(value):
            if len(diagnostics) >= MAX_SCHEMA_DIAGNOSTICS:
                break
            diagnostics.extend(
                _diagnose_json_schema(item, schema.get("items"), path + (index,))[
                    : MAX_SCHEMA_DIAGNOSTICS - len(diagnostics)
                ]
            )
        return tuple(diagnostics)
    if expected_type == "string":
        assert isinstance(value, str)
        minimum, maximum = schema.get("minLength", 0), schema.get("maxLength", MAX_RESULT_BYTES)
        if type(minimum) is not int or type(maximum) is not int:
            add("schema", path)
            return tuple(diagnostics)
        if len(value) < minimum:
            add("minLength", path)
        if len(value) > maximum:
            add("maxLength", path)
    if expected_type in {"number", "integer"}:
        assert type(value) in {int, float}
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if (
            (
                "minimum" in schema
                and not _is_valid_numeric_bound(minimum, expected_type)
            )
            or (
                "maximum" in schema
                and not _is_valid_numeric_bound(maximum, expected_type)
            )
            or (
                minimum is not None
                and maximum is not None
                and minimum > maximum
            )
        ):
            add("schema", path)
            return tuple(diagnostics)
        if minimum is not None and value < minimum:
            add("minimum", path)
        if maximum is not None and value > maximum:
            add("maximum", path)
    return tuple(diagnostics)


def _failure_result(receipt: ExecutionReceipt, replay: ReplayResult, anchor: str | None) -> BrokerResult:
    return BrokerResult(
        replay.status, replay.process_count, None, None, None, None, 0, anchor,
        receipt, False, None, replay.errors,
    )


def run_single_shot(
    *,
    operation_id: str,
    item_id: str,
    attempt_id: str,
    request_sha256: str,
    model: str,
    executable: Path,
    target_profile: str,
    expected_executable_digest: str,
    raw_request: bytes,
    response_schema: dict[str, Any],
    timeout_milliseconds: int,
    ledger_path: Path,
    anchor_store: AnchorStore,
    credential_fd: int | None = None,
    credential_fd_opener: Callable[[], int] | None = None,
) -> BrokerResult:
    """執行恰一次 target；既有 ledger 一律只 replay，不補事件或重送。"""
    binding = Binding(operation_id, item_id, attempt_id)
    binding.validate()
    if not _valid_sha256(request_sha256) or type(model) is not str or not model:
        raise ValueError("receipt binding is invalid")
    if type(raw_request) is not bytes or len(raw_request) > MAX_RESULT_BYTES:
        raise ValueError("raw request is invalid")
    if not _valid_sha256(expected_executable_digest):
        raise ValueError("trusted executable digest is invalid")
    if target_profile == ANTIGRAVITY_CLI_PROFILE:
        try:
            model_label = AGY_MODEL_LABELS[model]
        except KeyError as error:
            raise ValueError("agy model is not approved") from error
        _validate_public_prompt(raw_request)
        target_profile = ANTIGRAVITY_CLI_PROFILE
        payload_class = PUBLIC_SANITIZED
        if credential_fd is not None or credential_fd_opener is not None:
            raise ValueError("agy profile must not receive credential fd")
    elif target_profile == GEMINI_STRUCTURED_API_PROFILE:
        try:
            model_label = API_MODEL_LABELS[model]
        except KeyError as error:
            raise ValueError("Gemini API model is not approved") from error
        _validate_public_prompt(raw_request)
        if credential_fd is not None and credential_fd_opener is not None:
            raise ValueError("structured target credential source is ambiguous")
        target_profile = GEMINI_STRUCTURED_API_PROFILE
        payload_class = PUBLIC_STRUCTURED
    elif target_profile == RAW_STDIN_PROFILE:
        model_label = model
        payload_class = SYNTHETIC_TEST
        if credential_fd is not None or credential_fd_opener is not None:
            raise ValueError("synthetic profile must not receive credential fd")
    else:
        raise ValueError("target profile is invalid")
    executable_bytes = executable.read_bytes() if executable.exists() and executable.is_file() else b""
    executable_digest = _sha256(executable_bytes)
    if executable_digest != expected_executable_digest:
        raise ValueError("trusted executable digest mismatch")
    receipt = ExecutionReceipt(
        operation_id,
        item_id,
        attempt_id,
        request_sha256,
        model,
        target_profile,
        executable_digest,
    )
    command = CommandFrame(
        COMMAND_SCHEMA_VERSION,
        operation_id,
        item_id,
        attempt_id,
        executable_digest,
        _sha256(raw_request),
        len(raw_request),
        timeout_milliseconds,
        target_profile,
        model_label,
        payload_class,
    )
    command.validate()
    try:
        existing_anchor = anchor_store.load(operation_id, attempt_id)
    except AnchorError:
        return _failure_result(receipt, ReplayResult("INVALID", "UNKNOWN", False, ("EXTERNAL_ANCHOR_INVALID",)), None)
    if ledger_path.exists():
        replay = replay_ledger(ledger_path, binding, existing_anchor)
        return _failure_result(receipt, replay, existing_anchor)
    if existing_anchor is not None:
        return _failure_result(receipt, ReplayResult("INVALID", "UNKNOWN", False, ("LEDGER_MISSING",)), existing_anchor)
    owns_credential_fd = False
    if target_profile == GEMINI_STRUCTURED_API_PROFILE:
        if credential_fd is None:
            if credential_fd_opener is None:
                raise ValueError("structured target credential fd is invalid")
            credential_fd = credential_fd_opener()
            owns_credential_fd = True
        if type(credential_fd) is not int or credential_fd < 3:
            if (
                owns_credential_fd
                and type(credential_fd) is int
                and credential_fd >= 3
            ):
                os.close(credential_fd)
            raise ValueError("structured target credential fd is invalid")
        try:
            os.fstat(credential_fd)
        except OSError as error:
            if owns_credential_fd:
                try:
                    os.close(credential_fd)
                except OSError:
                    pass
            raise ValueError("structured target credential fd is invalid") from error
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        if owns_credential_fd and credential_fd is not None:
            os.close(credential_fd)
        raise
    try:
        ledger_fd = os.open(ledger_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if owns_credential_fd and credential_fd is not None:
            os.close(credential_fd)
        try:
            replay_anchor = anchor_store.load(operation_id, attempt_id)
        except AnchorError:
            return _failure_result(
                receipt,
                ReplayResult("INVALID", "UNKNOWN", False, ("EXTERNAL_ANCHOR_INVALID",)),
                None,
            )
        replay = replay_ledger(ledger_path, binding, replay_anchor)
        return _failure_result(receipt, replay, replay_anchor)
    except Exception:
        if owns_credential_fd and credential_fd is not None:
            try:
                os.close(credential_fd)
            except OSError:
                pass
        raise
    command_read, command_write = os.pipe()
    result_read, result_write = os.pipe()
    anchor_parent, anchor_child = socket.socketpair()
    process: subprocess.Popen[bytes] | None = None
    snapshot_directory: tempfile.TemporaryDirectory[str] | None = None
    raw_result = b""
    control_bytes = b""
    try:
        broker_executable = executable
        if executable_bytes:
            snapshot_directory = tempfile.TemporaryDirectory(prefix="agy-v4-exec-")
            broker_executable = _write_executable_snapshot(Path(snapshot_directory.name), executable_bytes)
        broker_arguments = [
                sys.executable,
                "-m",
                "scripts.agy_gemini_v4_broker",
                "--broker",
                str(command_read),
                str(ledger_fd),
                str(anchor_child.fileno()),
                str(result_write),
                str(broker_executable),
            ]
        broker_pass_fds = [
            command_read,
            ledger_fd,
            anchor_child.fileno(),
            result_write,
        ]
        if credential_fd is not None:
            broker_arguments.extend(["--credential-fd", str(credential_fd)])
            broker_pass_fds.append(credential_fd)
        process = subprocess.Popen(
            broker_arguments,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=tuple(broker_pass_fds),
        )
        if owns_credential_fd and credential_fd is not None:
            os.close(credential_fd)
            credential_fd = None
            owns_credential_fd = False
        os.close(ledger_fd)
        ledger_fd = -1
        os.close(command_read)
        command_read = -1
        os.close(result_write)
        result_write = -1
        anchor_child.close()
        _write_all(command_write, encode_frame(command.to_dict()))
        os.close(command_write)
        command_write = -1
        assert process.stdin is not None
        process.stdin.write(raw_request)
        process.stdin.close()
        process.stdin = None
        while True:
            framed = _recv_frame(anchor_parent)
            if not framed:
                break
            request = _decode_frame(framed)
            ok = False
            if isinstance(request, dict) and set(request) == {"previous_anchor", "next_anchor"}:
                previous = request["previous_anchor"]
                next_anchor = request["next_anchor"]
                if (previous is None or _valid_sha256(previous)) and _valid_sha256(next_anchor):
                    try:
                        ok = anchor_store.compare_and_swap(operation_id, attempt_id, previous, str(next_anchor))
                    except AnchorError:
                        ok = False
            anchor_parent.sendall(encode_frame({"ok": ok}))
            if not ok:
                break
        anchor_parent.close()
        chunks = bytearray()
        while True:
            chunk = os.read(result_read, 64 * 1024)
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > MAX_RESULT_BYTES:
                break
        raw_result = bytes(chunks)
        stdout, _broker_stderr = process.communicate(timeout=timeout_milliseconds / 1000 + 5)
        control_bytes = stdout
    except (BrokenPipeError, OSError, FrameError, subprocess.TimeoutExpired):
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
    finally:
        for descriptor in (ledger_fd, command_read, command_write, result_read, result_write):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        for channel in (anchor_parent, anchor_child):
            try:
                channel.close()
            except OSError:
                pass
        if snapshot_directory is not None:
            os.chmod(snapshot_directory.name, 0o700)
            snapshot_directory.cleanup()
        if owns_credential_fd and credential_fd is not None:
            try:
                os.close(credential_fd)
            except OSError:
                pass
    try:
        final_anchor = anchor_store.load(operation_id, attempt_id)
    except AnchorError:
        final_anchor = None
    replay = replay_ledger(ledger_path, binding, final_anchor)
    if not control_bytes:
        return _failure_result(receipt, replay, final_anchor)
    try:
        control = _validate_control(_decode_frame(control_bytes))
    except FrameError:
        return _failure_result(receipt, ReplayResult("INVALID", "UNKNOWN", False, replay.errors + ("CONTROL_FRAME_INVALID",)), final_anchor)
    if (
        control["replay_status"] != replay.status
        or control["process_count"] != replay.process_count
        or control["final_anchor"] != final_anchor
        or control["byte_count"] != len(raw_result)
        or control["stdout_sha256"] != _sha256(raw_result)
    ):
        return _failure_result(receipt, ReplayResult("INVALID", "UNKNOWN", False, replay.errors + ("CONTROL_REPLAY_MISMATCH",)), final_anchor)
    parsed: dict[str, Any] | None = None
    caller_ok = False
    result_validation = "NOT_EVALUATED"
    schema_diagnostics: tuple[SchemaDiagnostic, ...] = ()
    json_diagnostic: JsonDiagnostic | None = None
    if replay.status == "COMPLETE" and replay.process_count == 1 and control["outcome"] == "SUCCESS":
        try:
            candidate = _strict_json_loads(raw_result)
        except (ValueError, UnicodeDecodeError) as error:
            result_validation = "JSON_INVALID"
            json_diagnostic = _diagnose_json_invalid(raw_result, error)
        else:
            if not isinstance(candidate, dict):
                result_validation = "NOT_OBJECT"
            else:
                schema_diagnostics = _diagnose_json_schema(candidate, response_schema)
                if schema_diagnostics:
                    result_validation = "SCHEMA_MISMATCH"
                else:
                    result_validation = "VALID"
                    parsed, caller_ok = candidate, True
    return BrokerResult(
        replay.status,
        replay.process_count,
        str(control["outcome"]) if control["outcome"] is not None else None,
        int(control["exit_status"]) if control["exit_status"] is not None else None,
        str(control["stdout_sha256"]),
        str(control["stderr_sha256"]),
        int(control["byte_count"]),
        final_anchor,
        receipt,
        caller_ok,
        raw_result if parsed is not None else None,
        replay.errors,
        result_validation=result_validation,
        schema_diagnostics=schema_diagnostics,
        json_diagnostic=json_diagnostic,
        target_diagnostic=(
            str(control["target_diagnostic"])
            if control["target_diagnostic"] is not None
            else None
        ),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", action="store_true")
    parser.add_argument("command_fd", type=int)
    parser.add_argument("ledger_fd", type=int)
    parser.add_argument("anchor_fd", type=int)
    parser.add_argument("result_fd", type=int)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--credential-fd", type=int)
    return parser.parse_args()


def main() -> int:
    arguments = _parse_args()
    if not arguments.broker:
        raise SystemExit("module mode is reserved for the broker supervisor")
    return _broker_entry(
        arguments.command_fd,
        arguments.ledger_fd,
        arguments.anchor_fd,
        arguments.result_fd,
        arguments.executable,
        arguments.credential_fd,
    )


if __name__ == "__main__":
    raise SystemExit(main())

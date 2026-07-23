#!/usr/bin/env python3
"""離線驗證 Gemini V4 canary bundle；不讀 prompt、不呼叫 production broker。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MODEL_LABELS = {
    "gemini-3.5-flash": "Gemini 3.5 Flash (Low)",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro (Low)",
}
BASE_EVENT_FIELDS = {
    "schema_version",
    "sequence",
    "parent_sha256",
    "event_type",
    "operation_id",
    "item_id",
    "attempt_id",
}
EVENT_FIELDS: dict[str, dict[str, type]] = {
    "OPERATION_CREATED": {},
    "BROKER_ATTEMPTED": {"broker_attempt": int},
    "FORK_ATTEMPTED": {"broker_attempt": int, "process_ordinal": int},
    "EXEC_CONFIRMED": {"process_ordinal": int, "pid": int},
    "PROCESS_TERMINAL": {"outcome": str},
}
EXPECTED_EVENT_ORDER = tuple(EVENT_FIELDS)
TOP_LEVEL_FIELDS = {
    "schema_version",
    "receipt",
    "command",
    "execution",
    "ledger",
    "control",
    "inbox",
    "result_schema",
    "executable_identity",
    "invocation_policy",
    "privacy",
}
RECEIPT_FIELDS = {
    "operation_id",
    "item_id",
    "attempt_id",
    "request_sha256",
    "model",
    "target_profile",
    "executable_digest",
}
COMMAND_FIELDS = {
    "schema_version",
    "operation_id",
    "item_id",
    "attempt_id",
    "executable_digest",
    "request_sha256",
    "request_bytes_length",
    "timeout_milliseconds",
    "target_profile",
    "model_label",
    "payload_class",
}
EXECUTION_FIELDS = {
    "replay_status",
    "process_count",
    "outcome",
    "exit_status",
    "stdout_sha256",
    "stderr_sha256",
    "byte_count",
    "final_anchor",
    "caller_contract_satisfied",
    "result",
    "errors",
    "automatic_resend_allowed",
}
CONTROL_FIELDS = {
    "replay_status",
    "process_count",
    "outcome",
    "exit_status",
    "stdout_sha256",
    "stderr_sha256",
    "byte_count",
    "final_anchor",
}
LEDGER_FIELDS = {"encoding", "canonical_frames", "ledger_sha256", "final_anchor"}
INBOX_FIELDS = {"schema_version", "job_id", "request_sha256", "model", "result"}
EXECUTABLE_FIELDS = {"tool", "cli_version", "sha256"}
POLICY_FIELDS = {
    "target_invocations",
    "fallback_invocations",
    "automatic_retry_invocations",
    "automatic_resend_allowed",
}
PRIVACY_FIELDS = {
    "prompt_saved",
    "credential_saved",
    "full_environment_saved",
    "cli_log_saved",
    "executable_path_saved",
}


class VerificationError(ValueError):
    """Bundle 不符合 closed evidence contract。"""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def require_closed(value: object, fields: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    assert isinstance(value, dict)
    require(set(value) == fields, f"{label} fields are not closed")
    return value


def require_sha(value: object, label: str) -> str:
    require(type(value) is str and HEX_SHA256.fullmatch(value) is not None, f"{label} is not SHA-256")
    return str(value)


def require_identifier(value: object, label: str) -> str:
    require(type(value) is str and IDENTIFIER.fullmatch(value) is not None, f"{label} is not opaque")
    return str(value)


def validate_schema(value: object, schema: object) -> bool:
    if not isinstance(schema, dict) or type(schema.get("type")) is not str:
        return False
    expected_type = schema["type"]
    type_ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": type(value) is str,
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) in {int, float},
        "null": value is None,
    }.get(expected_type, False)
    if not type_ok:
        return False
    enum = schema.get("enum")
    if "enum" in schema and (not isinstance(enum, list) or value not in enum):
        return False
    if expected_type == "object":
        assert isinstance(value, dict)
        properties = schema.get("properties")
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            return False
        if not all(type(field) is str for field in required) or not set(required) <= set(value):
            return False
        if schema.get("additionalProperties") is False and not set(value) <= set(properties):
            return False
        return all(field not in properties or validate_schema(item, properties[field]) for field, item in value.items())
    if expected_type == "array":
        assert isinstance(value, list)
        return all(validate_schema(item, schema.get("items")) for item in value)
    return True


def verify_bundle(bundle: object) -> dict[str, object]:
    root = require_closed(bundle, TOP_LEVEL_FIELDS, "bundle")
    require(root["schema_version"] == 1, "bundle schema version is invalid")
    receipt = require_closed(root["receipt"], RECEIPT_FIELDS, "receipt")
    command = require_closed(root["command"], COMMAND_FIELDS, "command")
    execution = require_closed(root["execution"], EXECUTION_FIELDS, "execution")
    ledger = require_closed(root["ledger"], LEDGER_FIELDS, "ledger")
    control = require_closed(root["control"], CONTROL_FIELDS, "control")
    inbox = require_closed(root["inbox"], INBOX_FIELDS, "inbox")
    executable = require_closed(root["executable_identity"], EXECUTABLE_FIELDS, "executable_identity")
    policy = require_closed(root["invocation_policy"], POLICY_FIELDS, "invocation_policy")
    privacy = require_closed(root["privacy"], PRIVACY_FIELDS, "privacy")

    operation_id = require_identifier(receipt["operation_id"], "receipt operation")
    item_id = require_identifier(receipt["item_id"], "receipt item")
    attempt_id = require_identifier(receipt["attempt_id"], "receipt attempt")
    request_sha256 = require_sha(receipt["request_sha256"], "receipt request")
    executable_sha256 = require_sha(receipt["executable_digest"], "receipt executable")
    require(receipt["target_profile"] == "antigravity_cli_v1", "receipt profile is invalid")
    require(receipt["model"] in MODEL_LABELS, "receipt model is not approved")

    require(command["schema_version"] == 2, "command schema version is invalid")
    for field in ("operation_id", "item_id", "attempt_id", "request_sha256", "target_profile"):
        require(command[field] == receipt[field], f"command/receipt {field} mismatch")
    require(command["executable_digest"] == executable_sha256, "command executable digest mismatch")
    require(command["model_label"] == MODEL_LABELS[receipt["model"]], "command model label mismatch")
    require(type(command["request_bytes_length"]) is int and command["request_bytes_length"] > 0, "request length is invalid")
    require(
        type(command["timeout_milliseconds"]) is int and 1 <= command["timeout_milliseconds"] <= 3_600_000,
        "timeout is invalid",
    )
    require(command["payload_class"] == "PUBLIC_SANITIZED", "payload class is invalid")

    require(executable["tool"] == "agy", "executable tool is invalid")
    require(executable["cli_version"] == "1.1.5", "agy CLI version is invalid")
    require(executable["sha256"] == executable_sha256, "executable identity digest mismatch")

    require(ledger["encoding"] == "canonical-jsonl-v1", "ledger encoding is invalid")
    frames = ledger["canonical_frames"]
    require(isinstance(frames, list) and len(frames) == 5, "ledger must contain five closed events")
    parent: str | None = None
    event_types: list[str] = []
    canonical_lines: list[bytes] = []
    for index, frame_value in enumerate(frames, 1):
        require(isinstance(frame_value, dict), f"ledger event {index} is invalid")
        assert isinstance(frame_value, dict)
        event_type = frame_value.get("event_type")
        require(event_type in EVENT_FIELDS, f"ledger event {index} type is invalid")
        specific = EVENT_FIELDS[str(event_type)]
        require(set(frame_value) == BASE_EVENT_FIELDS | set(specific), f"ledger event {index} fields are not closed")
        require(frame_value["schema_version"] == 2, f"ledger event {index} schema is invalid")
        require(frame_value["sequence"] == index, f"ledger event {index} sequence is invalid")
        require(frame_value["parent_sha256"] == parent, f"ledger event {index} chain is invalid")
        require(
            (frame_value["operation_id"], frame_value["item_id"], frame_value["attempt_id"])
            == (operation_id, item_id, attempt_id),
            f"ledger event {index} binding mismatch",
        )
        for field, expected_type in specific.items():
            require(type(frame_value[field]) is expected_type, f"ledger event {index} {field} type is invalid")
        if "broker_attempt" in frame_value:
            require(frame_value["broker_attempt"] == 1, "broker attempt is invalid")
        if "process_ordinal" in frame_value:
            require(frame_value["process_ordinal"] == 1, "process ordinal is invalid")
        if event_type == "EXEC_CONFIRMED":
            require(frame_value["pid"] > 0, "confirmed pid is invalid")
        if event_type == "PROCESS_TERMINAL":
            require(frame_value["outcome"] == "SUCCESS", "terminal outcome is not success")
        encoded = canonical_json(frame_value)
        canonical_lines.append(encoded + b"\n")
        parent = sha256(encoded)
        event_types.append(str(event_type))
    require(tuple(event_types) == EXPECTED_EVENT_ORDER, "ledger event order is invalid")
    assert parent is not None
    require_sha(ledger["ledger_sha256"], "ledger digest")
    require(ledger["ledger_sha256"] == sha256(b"".join(canonical_lines)), "ledger digest mismatch")
    require(ledger["final_anchor"] == parent, "ledger anchor mismatch")

    require(execution["replay_status"] == "COMPLETE", "execution replay is not complete")
    require(execution["process_count"] == 1, "execution process count is not one")
    require(execution["outcome"] == "SUCCESS", "execution outcome is not success")
    require(execution["exit_status"] == 0, "execution exit status is not zero")
    require_sha(execution["stdout_sha256"], "execution stdout")
    require_sha(execution["stderr_sha256"], "execution stderr")
    require(type(execution["byte_count"]) is int and execution["byte_count"] > 0, "execution byte count is invalid")
    require(execution["final_anchor"] == parent, "execution anchor mismatch")
    require(execution["caller_contract_satisfied"] is True, "caller contract is not satisfied")
    require(execution["errors"] == [], "execution contains errors")
    require(execution["automatic_resend_allowed"] is False, "automatic resend is enabled")
    require(validate_schema(execution["result"], root["result_schema"]), "execution result schema is invalid")

    for field in CONTROL_FIELDS:
        require(control[field] == execution[field], f"control/execution {field} mismatch")
    require(control["final_anchor"] == parent, "control anchor mismatch")

    require(inbox["schema_version"] == 1, "inbox schema version is invalid")
    require(inbox["job_id"] == operation_id, "inbox operation mismatch")
    require(inbox["request_sha256"] == request_sha256, "inbox request mismatch")
    require(inbox["model"] == receipt["model"], "inbox model mismatch")
    require(inbox["result"] == execution["result"], "inbox result mismatch")
    require(validate_schema(inbox["result"], root["result_schema"]), "inbox result schema is invalid")

    require(policy["target_invocations"] == 1, "target invocation count is invalid")
    require(policy["fallback_invocations"] == 0, "fallback was invoked")
    require(policy["automatic_retry_invocations"] == 0, "automatic retry was invoked")
    require(policy["automatic_resend_allowed"] is False, "policy permits automatic resend")
    require(all(value is False for value in privacy.values()), "privacy contract is invalid")

    return {
        "status": "PASS",
        "operation_id": operation_id,
        "item_id": item_id,
        "attempt_id": attempt_id,
        "request_sha256": request_sha256,
        "model": receipt["model"],
        "target_profile": receipt["target_profile"],
        "executable_sha256": executable_sha256,
        "ledger_sha256": ledger["ledger_sha256"],
        "final_anchor": parent,
        "event_types": event_types,
        "event_count": len(event_types),
        "process_count": 1,
        "result_schema_valid": True,
        "no_fallback": True,
        "automatic_resend_allowed": False,
    }


def mutation_matrix(bundle: object) -> dict[str, object]:
    require(isinstance(bundle, dict), "matrix input is invalid")
    cases: list[tuple[str, Any]] = [
        ("wrong_operation", lambda value: value["receipt"].__setitem__("operation_id", "operation-wrong")),
        ("wrong_item", lambda value: value["receipt"].__setitem__("item_id", "item-wrong")),
        ("wrong_attempt", lambda value: value["receipt"].__setitem__("attempt_id", "attempt-wrong")),
        ("wrong_request", lambda value: value["receipt"].__setitem__("request_sha256", "0" * 64)),
        ("wrong_model", lambda value: value["receipt"].__setitem__("model", "gemini-wrong")),
        ("wrong_profile", lambda value: value["receipt"].__setitem__("target_profile", "raw_stdin_v1")),
        ("wrong_digest", lambda value: value["receipt"].__setitem__("executable_digest", "0" * 64)),
        (
            "broken_chain",
            lambda value: value["ledger"]["canonical_frames"][2].__setitem__("parent_sha256", "0" * 64),
        ),
        ("partial_ledger", lambda value: value["ledger"]["canonical_frames"].pop()),
        (
            "duplicate_event",
            lambda value: value["ledger"]["canonical_frames"].insert(
                2, copy.deepcopy(value["ledger"]["canonical_frames"][1])
            ),
        ),
        ("wrong_anchor", lambda value: value["ledger"].__setitem__("final_anchor", "0" * 64)),
        (
            "wrong_result_schema",
            lambda value: value["execution"].__setitem__("result", {"ok": "not-a-boolean"}),
        ),
    ]
    results: list[dict[str, object]] = []
    for name, mutate in cases:
        candidate = copy.deepcopy(bundle)
        mutate(candidate)
        try:
            verify_bundle(candidate)
        except VerificationError as error:
            results.append({"scenario": name, "status": "PASS", "rejected": True, "error": str(error)})
        else:
            results.append({"scenario": name, "status": "FAIL", "rejected": False, "error": None})
    return {
        "schema_version": 1,
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "cases": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mutation-matrix", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        result = mutation_matrix(bundle) if args.mutation_matrix else verify_bundle(bundle)
        if args.mutation_matrix and result["status"] != "PASS":
            raise VerificationError("one or more mutations were accepted")
    except (OSError, json.JSONDecodeError, VerificationError) as error:
        result = {"status": "REJECTED", "error": str(error)}
        exit_code = 1
    else:
        exit_code = 0
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""七段 capability receipt 的純本機 fail-closed schema authority。"""

from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Mapping


SCHEMA_VERSION = 1
CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
NON_PRODUCTION_MODES = frozenset(
    {
        "synthetic-non-production",
        "formal-runtime-production-dry-run",
    }
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "execution_line_id",
        "correlation_id",
        "actor_identity",
        "runtime_identity_digest",
        "mode",
        "canary_created",
        "production_mutation",
        "steps",
    }
)
_STEP_KEYS = frozenset(
    {
        "capability",
        "ordinal",
        "entrypoint",
        "input_digest",
        "output_digest",
        "execution_line_id",
        "correlation_id",
        "actor_identity",
        "runtime_identity_digest",
        "positive_evidence",
        "negative_evidence",
        "positive_outcome",
        "negative_outcome",
    }
)
_CALLER_VERDICT_KEYS = frozenset({"status", "verdict", "ready", "valid"})
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")


class CapabilityReceiptError(ValueError):
    """穩定錯誤型別；`code` 是 caller 可比對的 fail-closed reason。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise CapabilityReceiptError(code, message)


def _reject_non_finite(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("type", "receipt contains a non-finite JSON value")
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_non_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_non_finite(nested)


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("type", f"{label} must be an object")
    if any(type(key) is not str for key in value):
        _fail("type", f"{label} keys must be strings")
    return value


def _reject_unknown_keys(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    label: str,
) -> None:
    if _CALLER_VERDICT_KEYS.intersection(value):
        _fail("caller_verdict", f"{label} contains caller-supplied verdict")
    unknown = set(value) - allowed
    if unknown:
        _fail("unknown_key", f"{label} contains unknown keys")


def _identifier(value: object, field: str) -> str:
    if type(value) is not str:
        _fail("type", f"{field} must be a string")
    if not value or value.strip() != value:
        _fail("identifier", f"{field} must be a non-blank stable identifier")
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str:
        _fail("type", f"{field} must be a digest string")
    if _DIGEST_PATTERN.fullmatch(value) is None:
        _fail("digest_format", f"{field} must be a lowercase sha256 digest")
    return value


def _evidence_identifier(value: object, field: str) -> str:
    if type(value) is not str:
        _fail("type", f"{field} must be a string")
    identifier = value
    if not identifier or identifier.strip() != identifier:
        _fail("evidence_identifier", f"{field} must be a non-blank identifier")
    if (
        identifier.startswith("/")
        or "\\" in identifier
        or "//" in identifier
        or ":" in identifier
    ):
        _fail("evidence_identifier", f"{field} must be repo-relative")
    parts = identifier.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _fail("evidence_identifier", f"{field} must not traverse directories")
    return identifier


def _validate_top_level(receipt: Mapping[str, Any]) -> dict[str, str]:
    _reject_unknown_keys(receipt, _TOP_LEVEL_KEYS, "receipt")
    schema_version = receipt.get("schema_version")
    if type(schema_version) is not int:
        _fail("type", "schema_version must be an integer")
    if schema_version != SCHEMA_VERSION:
        _fail("schema_version", "receipt schema version is unsupported")
    identities = {
        "execution_line_id": _identifier(
            receipt.get("execution_line_id"), "execution_line_id"
        ),
        "correlation_id": _identifier(receipt.get("correlation_id"), "correlation_id"),
        "actor_identity": _identifier(receipt.get("actor_identity"), "actor_identity"),
        "runtime_identity_digest": _digest(
            receipt.get("runtime_identity_digest"), "runtime_identity_digest"
        ),
    }
    mode = _identifier(receipt.get("mode"), "mode")
    if mode not in NON_PRODUCTION_MODES:
        _fail("production_boundary", "receipt mode is not an allowed boundary")
    for field in ("canary_created", "production_mutation"):
        if receipt.get(field) is not False:
            _fail("production_boundary", f"{field} must be false")
    return identities


def _validate_step(
    step: Mapping[str, Any],
    ordinal: int,
    capability: str,
    identities: dict[str, str],
) -> dict[str, str]:
    _reject_unknown_keys(step, _STEP_KEYS, f"step {ordinal}")
    if type(step.get("ordinal")) is not int:
        _fail("type", "ordinal must be an integer")
    if step.get("capability") != capability or step.get("ordinal") != ordinal:
        _fail("step_sequence", "receipt steps must match the fixed sequence")
    _identifier(step.get("entrypoint"), "entrypoint")
    for field, expected in identities.items():
        actual = (
            _digest(step.get(field), field)
            if field.endswith("_digest")
            else _identifier(step.get(field), field)
        )
        if actual != expected:
            _fail("identity_mismatch", f"{field} drifted across receipt steps")
    positive_evidence = _evidence_identifier(
        step.get("positive_evidence"), "positive_evidence"
    )
    negative_evidence = _evidence_identifier(
        step.get("negative_evidence"), "negative_evidence"
    )
    if positive_evidence == negative_evidence:
        _fail("evidence_pair", "positive and fail-closed evidence must be distinct")
    if step.get("positive_outcome") != "PASS" or step.get("negative_outcome") != "BLOCKED":
        _fail("evidence_outcome", "evidence outcomes must be PASS and BLOCKED")
    return {
        "input_digest": _digest(step.get("input_digest"), "input_digest"),
        "output_digest": _digest(step.get("output_digest"), "output_digest"),
    }


def validate_capability_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """驗證七段 receipt，回傳 canonical copy；任何缺漏都 deterministic 拒絕。"""

    root = _require_mapping(receipt, "receipt")
    _reject_non_finite(root)
    identities = _validate_top_level(root)
    steps = root.get("steps")
    if not isinstance(steps, list):
        _fail("type", "steps must be a list")
    if len(steps) != len(CAPABILITIES):
        _fail("step_sequence", "receipt must contain exactly seven steps")
    previous_output: str | None = None
    for ordinal, (capability, raw_step) in enumerate(zip(CAPABILITIES, steps), 1):
        step = _require_mapping(raw_step, f"step {ordinal}")
        digests = _validate_step(step, ordinal, capability, identities)
        if previous_output is not None and digests["input_digest"] != previous_output:
            _fail("digest_continuity", "step input digest must match previous output")
        previous_output = digests["output_digest"]
    canonical = deepcopy(dict(root))
    canonical["status"] = "PASS"
    return canonical

from __future__ import annotations

from copy import deepcopy
import math

import pytest

from scripts.pantheon_content_capability_receipt import (
    CAPABILITIES,
    CapabilityReceiptError,
    SCHEMA_VERSION,
    validate_capability_receipt,
)


def _digest(index: int) -> str:
    return f"{index:064x}"


def _valid_receipt() -> dict[str, object]:
    previous = _digest(0)
    steps: list[dict[str, object]] = []
    for ordinal, capability in enumerate(CAPABILITIES, 1):
        output = _digest(ordinal)
        steps.append(
            {
                "capability": capability,
                "ordinal": ordinal,
                "entrypoint": f"scripts.example:{capability}",
                "input_digest": previous,
                "output_digest": output,
                "execution_line_id": "exec-line-001",
                "correlation_id": "corr-001",
                "actor_identity": "actor-001",
                "runtime_identity_digest": _digest(99),
                "positive_evidence": f"runtime_activation/ra_slice_001/{ordinal:02d}-{capability}-pass.json",
                "negative_evidence": f"runtime_activation/ra_slice_001/{ordinal:02d}-{capability}-blocked.json",
                "positive_outcome": "PASS",
                "negative_outcome": "BLOCKED",
            }
        )
        previous = output
    return {
        "schema_version": SCHEMA_VERSION,
        "execution_line_id": "exec-line-001",
        "correlation_id": "corr-001",
        "actor_identity": "actor-001",
        "runtime_identity_digest": _digest(99),
        "mode": "synthetic-non-production",
        "canary_created": False,
        "production_mutation": False,
        "steps": steps,
    }


def _rejects(receipt: dict[str, object], code: str) -> None:
    with pytest.raises(CapabilityReceiptError) as error:
        validate_capability_receipt(receipt)
    assert error.value.code == code


def test_valid_receipt_returns_canonical_copy_without_mutating_input() -> None:
    receipt = _valid_receipt()
    original = deepcopy(receipt)

    validated = validate_capability_receipt(receipt)

    assert receipt == original
    assert validated is not receipt
    assert validated["schema_version"] == SCHEMA_VERSION
    assert validated["status"] == "PASS"
    assert [step["capability"] for step in validated["steps"]] == list(CAPABILITIES)
    assert validated["steps"] is not receipt["steps"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda receipt: receipt["steps"].pop(0),
        lambda receipt: receipt["steps"].append(dict(receipt["steps"][-1])),
        lambda receipt: receipt["steps"].__setitem__(1, dict(receipt["steps"][0])),
        lambda receipt: receipt["steps"].__setitem__(
            1,
            {
                **receipt["steps"][1],
                "capability": "run",
                "ordinal": 7,
            },
        ),
        lambda receipt: receipt["steps"].__setitem__(
            1,
            {
                **receipt["steps"][1],
                "capability": "publish",
            },
        ),
    ],
)
def test_step_count_order_uniqueness_and_ordinal_are_strict(mutate) -> None:
    receipt = _valid_receipt()
    mutate(receipt)

    _rejects(receipt, "step_sequence")


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("execution_line_id", "identity_mismatch"),
        ("correlation_id", "identity_mismatch"),
        ("actor_identity", "identity_mismatch"),
        ("runtime_identity_digest", "identity_mismatch"),
    ],
)
def test_step_identity_correlation_actor_and_runtime_drift_rejects(
    field: str,
    code: str,
) -> None:
    receipt = _valid_receipt()
    receipt["steps"][2][field] = "drift" if field != "runtime_identity_digest" else _digest(98)

    _rejects(receipt, code)


@pytest.mark.parametrize(
    ("step_index", "field", "value", "code"),
    [
        (1, "input_digest", _digest(40), "digest_continuity"),
        (2, "output_digest", "not-a-digest", "digest_format"),
        (3, "output_digest", "", "digest_format"),
    ],
)
def test_digest_continuity_and_format_are_recomputed(
    step_index: int,
    field: str,
    value: str,
    code: str,
) -> None:
    receipt = _valid_receipt()
    receipt["steps"][step_index][field] = value

    _rejects(receipt, code)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("positive_evidence", "", "evidence_identifier"),
        ("negative_evidence", "", "evidence_identifier"),
        ("positive_evidence", "/tmp/pass.json", "evidence_identifier"),
        ("negative_evidence", "../blocked.json", "evidence_identifier"),
        ("positive_evidence", "runtime_activation/../pass.json", "evidence_identifier"),
        ("negative_evidence", "runtime_activation\\..\\blocked.json", "evidence_identifier"),
        ("negative_evidence", "runtime_activation/ra_slice_001/01-create-pass.json", "evidence_pair"),
        ("positive_outcome", "BLOCKED", "evidence_outcome"),
        ("negative_outcome", "PASS", "evidence_outcome"),
    ],
)
def test_positive_and_fail_closed_evidence_contract_is_strict(
    field: str,
    value: str,
    code: str,
) -> None:
    receipt = _valid_receipt()
    receipt["steps"][0][field] = value

    _rejects(receipt, code)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("canary_created", True, "production_boundary"),
        ("production_mutation", True, "production_boundary"),
        ("mode", "production", "production_boundary"),
    ],
)
def test_production_boundary_is_non_authoritative_and_fail_closed(
    field: str,
    value: object,
    code: str,
) -> None:
    receipt = _valid_receipt()
    receipt[field] = value

    _rejects(receipt, code)


@pytest.mark.parametrize("field", ["status", "verdict", "ready", "valid"])
def test_caller_supplied_readiness_or_verdict_is_rejected(field: str) -> None:
    receipt = _valid_receipt()
    receipt[field] = "PASS"

    _rejects(receipt, "caller_verdict")


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda receipt: receipt.__setitem__("unexpected", True), "unknown_key"),
        (lambda receipt: receipt["steps"][0].__setitem__("unexpected", True), "unknown_key"),
        (lambda receipt: receipt.__setitem__("execution_line_id", " "), "identifier"),
        (lambda receipt: receipt["steps"][0].__setitem__("entrypoint", ""), "identifier"),
        (lambda receipt: receipt.__setitem__("steps", tuple(receipt["steps"])), "type"),
        (lambda receipt: receipt["steps"][0].__setitem__("ordinal", "1"), "type"),
        (lambda receipt: receipt["steps"][0].__setitem__("input_digest", math.inf), "type"),
    ],
)
def test_unknown_extra_keys_wrong_types_blank_and_non_finite_values_reject(
    mutate,
    code: str,
) -> None:
    receipt = _valid_receipt()
    mutate(receipt)

    _rejects(receipt, code)

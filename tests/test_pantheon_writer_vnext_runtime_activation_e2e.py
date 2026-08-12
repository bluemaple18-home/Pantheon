from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.agy_content_publisher import PublishBlocked
from scripts.pantheon_content_capability_receipt import (
    CAPABILITIES,
    validate_capability_receipt,
)
from scripts.pantheon_writer_vnext_runtime_activation_e2e import (
    RuntimeActivationE2EBlocked,
    run_runtime_activation_e2e,
)


RUNTIME_DIGEST = "d" * 64
RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": RUNTIME_DIGEST,
}


def _brief() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "ra-slice-002-synthetic-create-run",
        "mode": "create",
        "articles": [
            {
                "id": "RA-SLICE-004-SYNTHETIC",
                "title": "Synthetic local E2E receipt",
            }
        ],
    }


def _run(tmp_path: Path) -> dict[str, object]:
    sandbox_root = (tmp_path / "sandbox").resolve()
    sandbox_root.mkdir()
    return run_runtime_activation_e2e(
        trusted_sandbox_root=sandbox_root,
        runtime_receipt=RUNTIME_RECEIPT,
        execution_line_id="exec-ra-slice-004",
        correlation_id="corr-ra-slice-004",
        actor_identity="actor-ra-slice-004",
        brief=_brief(),
    )


def _artifact(result: dict[str, object], identifier: str) -> dict[str, object]:
    evidence_root = Path(str(result["evidence_root"]))
    return json.loads((evidence_root / identifier).read_text(encoding="utf-8"))


def test_runtime_activation_e2e_links_official_boundaries_and_writes_artifacts(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path)
    receipt = result["receipt"]

    assert result["mode"] == "synthetic-non-production"
    assert result["canary_created"] is False
    assert result["production_mutation"] is False
    assert result["created_run_id"] == "ra-slice-002-synthetic-create-run"
    assert [step["capability"] for step in receipt["steps"]] == list(CAPABILITIES)
    assert [step["ordinal"] for step in receipt["steps"]] == list(range(1, 8))
    assert receipt["mode"] == "synthetic-non-production"
    assert receipt["canary_created"] is False
    assert receipt["production_mutation"] is False
    assert validate_capability_receipt(receipt)["status"] == "PASS"

    expected_entrypoints = [
        "scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight",
        "scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight",
        *[
            "scripts.agy_content_publisher:formal_capability_preflight"
            for _ in range(5)
        ],
    ]
    assert [step["entrypoint"] for step in receipt["steps"]] == expected_entrypoints

    previous_output = None
    for step in receipt["steps"]:
        assert step["execution_line_id"] == "exec-ra-slice-004"
        assert step["correlation_id"] == "corr-ra-slice-004"
        assert step["actor_identity"] == "actor-ra-slice-004"
        assert step["runtime_identity_digest"] == RUNTIME_DIGEST
        if previous_output is not None:
            assert step["input_digest"] == previous_output
        previous_output = step["output_digest"]

        positive = str(step["positive_evidence"])
        negative = str(step["negative_evidence"])
        assert positive.startswith("positive/")
        assert negative.startswith("blocked/")
        assert positive != negative
        assert _artifact(result, positive)["outcome"] == "PASS"
        assert _artifact(result, negative)["outcome"] == "BLOCKED"

    positive_inventory = result["positive_artifact_inventory"]
    blocked_inventory = result["blocked_artifact_inventory"]
    assert len(positive_inventory) == 7
    assert len(blocked_inventory) >= 7
    assert not set(positive_inventory).intersection(blocked_inventory)


def test_runtime_activation_e2e_saves_fail_closed_matrix_and_blocked_receipt(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path)
    matrix = _artifact(result, "negative-matrix.json")
    blocked = _artifact(result, "blocked-receipt.json")

    cases = {str(item["case"]): item for item in matrix["cases"]}
    for case in [
        "identity-drift",
        "digest-discontinuity",
        "missing-step",
        "duplicate-step",
        "caller-supplied-verdict",
        "production-mutation",
        "publisher-runtime-drift",
        "publisher-caller-verdict",
        "publisher-overlapping-roots",
        "publisher-real-tag-mode",
        "publisher-real-push-mode",
        "publisher-empty-run-selection",
    ]:
        assert cases[case]["outcome"] == "BLOCKED"
    assert blocked["status"] == "BLOCKED"
    assert blocked["complete_pass_receipt_written"] is False
    assert blocked["production_mutation"] is False
    assert blocked["canary_created"] is False


def test_runtime_activation_e2e_rejects_untrusted_or_overlapping_roots(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeActivationE2EBlocked, match="canonical absolute"):
        run_runtime_activation_e2e(
            trusted_sandbox_root=Path("relative-sandbox"),
            runtime_receipt=RUNTIME_RECEIPT,
            execution_line_id="exec-ra-slice-004",
            correlation_id="corr-ra-slice-004",
            actor_identity="actor-ra-slice-004",
            brief=_brief(),
        )

    sandbox_root = (tmp_path / "sandbox").resolve()
    sandbox_root.mkdir()
    with pytest.raises(RuntimeActivationE2EBlocked, match="overlap"):
        run_runtime_activation_e2e(
            trusted_sandbox_root=sandbox_root,
            runtime_receipt=RUNTIME_RECEIPT,
            execution_line_id="exec-ra-slice-004",
            correlation_id="corr-ra-slice-004",
            actor_identity="actor-ra-slice-004",
            brief=_brief(),
            queue_root=sandbox_root / "shared",
            publisher_state_root=sandbox_root / "shared" / "state",
        )


def test_runtime_activation_e2e_stops_when_publisher_boundary_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import agy_content_publisher as publisher

    calls: list[str] = []
    original = publisher.formal_capability_preflight

    def blocking_preflight(capability: str, **kwargs: object) -> dict[str, object]:
        calls.append(capability)
        if capability == "transaction":
            raise PublishBlocked("injected transaction boundary block")
        return original(capability, **kwargs)

    monkeypatch.setattr(publisher, "formal_capability_preflight", blocking_preflight)

    sandbox_root = (tmp_path / "sandbox").resolve()
    sandbox_root.mkdir()
    with pytest.raises(RuntimeActivationE2EBlocked, match="transaction"):
        run_runtime_activation_e2e(
            trusted_sandbox_root=sandbox_root,
            runtime_receipt=RUNTIME_RECEIPT,
            execution_line_id="exec-ra-slice-004",
            correlation_id="corr-ra-slice-004",
            actor_identity="actor-ra-slice-004",
            brief=_brief(),
        )

    assert calls[-1] == "transaction"
    assert "tag" not in calls
    assert "push" not in calls
    evidence_root = sandbox_root / "evidence"
    assert (evidence_root / "blocked-receipt.json").is_file()
    assert not (evidence_root / "positive-receipt.json").exists()

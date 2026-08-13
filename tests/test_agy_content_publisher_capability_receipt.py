from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import agy_content_publisher as publisher
from scripts.pantheon_content_capability_receipt import (
    build_apf_004_readiness_candidate,
    CAPABILITIES,
    SCHEMA_VERSION,
    _resolve_ai_core_root,
    validate_capability_receipt,
)


RUNTIME_DIGEST = "b" * 64
RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": RUNTIME_DIGEST,
}
ENTRYPOINT = "scripts.agy_content_publisher:formal_capability_preflight"
EXECUTION_LINE_ID = "ra-slice-003-line"
CORRELATION_ID = "ra-slice-003-correlation"
ACTOR_IDENTITY = "publisher-actor-identity"


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sandbox(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    sandbox_root = (tmp_path / "sandbox").resolve()
    sandbox_root.mkdir()
    evidence_root = sandbox_root / "receipt-evidence"
    return sandbox_root, sandbox_root / "queue", sandbox_root / "publisher-state", evidence_root


def _context(
    *,
    evidence_root: Path,
    capability: str,
    input_digest: str,
    positive: bool = True,
    **extra: object,
) -> dict[str, object]:
    return {
        "execution_line_id": EXECUTION_LINE_ID,
        "correlation_id": CORRELATION_ID,
        "actor_identity": ACTOR_IDENTITY,
        "runtime_identity_digest": RUNTIME_DIGEST,
        "input_digest": input_digest,
        "evidence_root": str(evidence_root),
        "positive_evidence": f"positive-{capability}.json",
        "negative_evidence": f"blocked-{capability}.json",
        **extra,
    }


def _stub_boundaries(monkeypatch: pytest.MonkeyPatch, sandbox_root: Path) -> None:
    def fake_publish(
        _repo_root: Path,
        _queue_root: Path,
        _state_root: Path,
        **_kwargs: object,
    ) -> dict[str, object]:
        return {
            "status": "dry-run",
            "ready_runs": ["run-a"],
            "base_sha": "a" * 40,
        }

    @contextmanager
    def fake_transaction(*_args: object, **_kwargs: object):
        yield sandbox_root / "transaction"

    def fake_release(*_args: object, **_kwargs: object) -> str:
        return "c" * 40

    monkeypatch.setattr(publisher, "publish_ready_runs", fake_publish)
    monkeypatch.setattr(publisher, "_isolated_transaction_worktree", fake_transaction)
    monkeypatch.setattr(publisher, "_stage_commit_tag_push", fake_release)


def _call(
    capability: str,
    *,
    sandbox_root: Path,
    queue_root: Path,
    state_root: Path,
    receipt_context: dict[str, object],
    run_ids: list[str] | None = None,
    correlation_id: str = CORRELATION_ID,
    runtime_receipt: dict[str, object] | None = None,
) -> dict[str, Any]:
    return publisher.formal_capability_preflight(
        capability,
        run_ids=run_ids if run_ids is not None else ["run-a"],
        correlation_id=correlation_id,
        trusted_sandbox_root=sandbox_root,
        queue_root=queue_root,
        state_root=state_root,
        runtime_receipt=runtime_receipt if runtime_receipt is not None else RUNTIME_RECEIPT,
        receipt_context=receipt_context,
    )


def _synthetic_step(
    *,
    capability: str,
    ordinal: int,
    input_digest: str,
    output_digest: str,
) -> dict[str, object]:
    return {
        "capability": capability,
        "ordinal": ordinal,
        "entrypoint": f"scripts.synthetic:{capability}",
        "input_digest": input_digest,
        "output_digest": output_digest,
        "execution_line_id": EXECUTION_LINE_ID,
        "correlation_id": CORRELATION_ID,
        "actor_identity": ACTOR_IDENTITY,
        "runtime_identity_digest": RUNTIME_DIGEST,
        "positive_evidence": f"synthetic-positive-{capability}.json",
        "negative_evidence": f"synthetic-blocked-{capability}.json",
        "positive_outcome": "PASS",
        "negative_outcome": "BLOCKED",
    }


def _absolute_strings(payload: object) -> list[str]:
    values: list[str] = []
    if isinstance(payload, dict):
        for item in payload.values():
            values.extend(_absolute_strings(item))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_absolute_strings(item))
    elif isinstance(payload, str) and payload.startswith("/"):
        values.append(payload)
    return values


def test_formal_publisher_emits_shared_receipt_steps_and_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root, queue_root, state_root, evidence_root = _sandbox(tmp_path)
    _stub_boundaries(monkeypatch, sandbox_root)
    initial_digest = _digest({"fixture": "start"})
    create_output = _digest({"fixture": "create", "input": initial_digest})
    run_output = _digest({"fixture": "run", "input": create_output})
    previous_digest = run_output
    steps = [
        _synthetic_step(
            capability="create",
            ordinal=1,
            input_digest=initial_digest,
            output_digest=create_output,
        ),
        _synthetic_step(
            capability="run",
            ordinal=2,
            input_digest=create_output,
            output_digest=run_output,
        ),
    ]

    for capability in ("select", "publish", "transaction", "tag", "push"):
        result = _call(
            capability,
            sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            receipt_context=_context(
                evidence_root=evidence_root,
                capability=capability,
                input_digest=previous_digest,
            ),
        )
        step = result["receipt_step"]
        steps.append(step)
        assert step["capability"] == capability
        assert step["ordinal"] == CAPABILITIES.index(capability) + 1
        assert step["entrypoint"] == ENTRYPOINT
        assert step["input_digest"] == previous_digest
        assert step["runtime_identity_digest"] == RUNTIME_DIGEST
        assert result["production_mutation"] is False
        artifact = json.loads((evidence_root / f"positive-{capability}.json").read_text())
        assert artifact["capability"] == capability
        assert artifact["entrypoint"] == ENTRYPOINT
        assert artifact["outcome"] == "PASS"
        assert artifact["production_mutation"] is False
        assert artifact["input_digest"] == previous_digest
        assert artifact["output_digest"] == step["output_digest"]
        assert _absolute_strings(artifact) == []
        previous_digest = str(step["output_digest"])

    for capability, context_extra, call_kwargs in [
        ("select", {}, {"run_ids": []}),
        ("publish", {"runtime_identity_digest": "c" * 64}, {}),
        ("transaction", {}, {"state_root": queue_root / "nested-state"}),
        ("tag", {"tag_mode": "real-tag"}, {}),
        ("push", {"push_mode": "production"}, {}),
    ]:
        with pytest.raises(publisher.PublishBlocked):
            _call(
                capability,
                sandbox_root=sandbox_root,
                queue_root=queue_root,
                state_root=call_kwargs.pop("state_root", state_root),
                receipt_context=_context(
                    evidence_root=evidence_root,
                    capability=capability,
                    input_digest=run_output,
                    **context_extra,
                ),
                **call_kwargs,
            )
        blocked = json.loads((evidence_root / f"blocked-{capability}.json").read_text())
        assert blocked["capability"] == capability
        assert blocked["entrypoint"] == ENTRYPOINT
        assert blocked["outcome"] == "BLOCKED"
        assert blocked["production_mutation"] is False
        assert blocked["execution_line_id"] == EXECUTION_LINE_ID
        assert blocked["actor_identity"] == ACTOR_IDENTITY
        assert blocked["stable_reason"]

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "execution_line_id": EXECUTION_LINE_ID,
        "correlation_id": CORRELATION_ID,
        "actor_identity": ACTOR_IDENTITY,
        "runtime_identity_digest": RUNTIME_DIGEST,
        "mode": "formal-runtime-production-dry-run",
        "canary_created": False,
        "production_mutation": False,
        "steps": steps,
    }

    assert validate_capability_receipt(receipt)["status"] == "PASS"
    drifted = json.loads(json.dumps(receipt))
    drifted["steps"][3]["input_digest"] = _digest({"drift": True})
    with pytest.raises(Exception):
        validate_capability_receipt(drifted)


def test_formal_publisher_receipt_digest_is_stable_across_canonical_roots(
    tmp_path: Path,
) -> None:
    def call_in(root_name: str) -> dict[str, Any]:
        sandbox_root = (tmp_path / root_name / "sandbox").resolve()
        sandbox_root.mkdir(parents=True)
        evidence_root = sandbox_root / "receipt-evidence"
        return _call(
            "select",
            sandbox_root=sandbox_root,
            queue_root=sandbox_root / "queue",
            state_root=sandbox_root / "publisher-state",
            receipt_context=_context(
                evidence_root=evidence_root,
                capability="select",
                input_digest=_digest({"input": "select"}),
            ),
        )

    first = call_in("first-root")
    second = call_in("second-root")

    assert first["receipt_step"]["output_digest"] == second["receipt_step"]["output_digest"]


def test_formal_publisher_blocked_evidence_write_failure_is_observable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root, queue_root, state_root, evidence_root = _sandbox(tmp_path)

    def broken_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected evidence write failure")

    monkeypatch.setattr(publisher, "_write_receipt_evidence", broken_write)

    with pytest.raises(publisher.PublishBlocked, match="evidence") as captured:
        _call(
            "select",
            sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            receipt_context=_context(
                evidence_root=evidence_root,
                capability="select",
                input_digest=_digest({"input": "select"}),
            ),
            run_ids=[],
        )

    final_error = captured.value
    chain_messages: list[str] = []
    current: BaseException | None = final_error
    while current is not None:
        chain_messages.append(str(current))
        current = current.__cause__ or current.__context__
    assert "injected evidence write failure" in str(final_error)
    assert "exact run ids must not be empty" in str(final_error)
    assert any("injected evidence write failure" in message for message in chain_messages)
    assert any("exact run ids must not be empty" in message for message in chain_messages)


@pytest.mark.parametrize(
    "context_patch",
    [
        {"unexpected": True},
        {"status": "PASS"},
        {"positive_evidence": "/tmp/pass.json"},
        {"negative_evidence": "../blocked.json"},
        {"actor_identity": ""},
        {"input_digest": "not-a-digest"},
    ],
)
def test_receipt_context_rejects_caller_authority_and_unsafe_paths(
    context_patch: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root, queue_root, state_root, evidence_root = _sandbox(tmp_path)
    _stub_boundaries(monkeypatch, sandbox_root)
    context = _context(
        evidence_root=evidence_root,
        capability="select",
        input_digest=_digest({"input": "select"}),
    )
    context.update(context_patch)

    with pytest.raises(publisher.PublishBlocked):
        _call(
            "select",
            sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            receipt_context=context,
        )


def test_apf_004_readiness_builder_packages_capability_capacity_and_gate(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "ai-core/scripts/production_canary_readiness_gate.py"
    gate.parent.mkdir(parents=True)
    gate.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "receipt = sys.argv[-1]",
                "blocked = receipt.endswith('missing-step-receipt.json')",
                "print(json.dumps({'status': 'BLOCKED' if blocked else 'READY', 'failures': []}))",
                "raise SystemExit(1 if blocked else 0)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = build_apf_004_readiness_candidate(
        output_root=tmp_path / "apf_004_readiness",
        ai_core_root=tmp_path / "ai-core",
    )

    assert result["status"] == "READY"
    assert result["canary_created"] is False
    assert result["production_mutation"] is False
    assert result["publish"] is False
    assert result["tag"] is False
    assert result["push"] is False
    assert result["deploy"] is False
    assert result["schedule"] is False
    assert result["production_activation"] is False
    assert result["capabilities"] == list(CAPABILITIES)
    assert result["capacity_cycles"] == 2

    root = tmp_path / "apf_004_readiness"
    official = root / "package/production-canary-capability-receipt.json"
    capacity = root / "capacity/capacity-receipt.json"
    ready_gate = root / "official-gate-ready.json"
    blocked_gate = root / "official-gate-blocked.json"
    assert official.is_file()
    assert capacity.is_file()
    assert json.loads(ready_gate.read_text(encoding="utf-8"))["status"] == "READY"
    assert json.loads(blocked_gate.read_text(encoding="utf-8"))["status"] == "BLOCKED"

    official_payload = json.loads(official.read_text(encoding="utf-8"))
    assert official_payload["canary_created"] is False
    assert set(official_payload["steps"]) == set(CAPABILITIES)
    evidence = [
        step[field]["artifact"]
        for step in official_payload["steps"].values()
        for field in ("positive_evidence", "negative_evidence")
    ]
    assert len(evidence) == 14
    assert len(set(evidence)) == 14

    leaked = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and str(tmp_path) in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert leaked == []


def test_ai_core_root_discovery_fails_closed_without_machine_specific_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_CORE_ROOT", raising=False)
    monkeypatch.delenv("AI_CORE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))

    assert _resolve_ai_core_root(None) is None

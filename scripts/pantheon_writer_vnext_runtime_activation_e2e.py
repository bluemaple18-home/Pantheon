#!/usr/bin/env python3
"""Writer vNext runtime activation 的七段 synthetic non-production E2E harness。"""

from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable, Mapping

from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts.pantheon_content_capability_receipt import (
    CapabilityReceiptError,
    SCHEMA_VERSION,
    validate_capability_receipt,
)


MODE = "synthetic-non-production"
EVIDENCE_PATH = Path(
    "artifacts/fortune_council/content_writer_vnext_execution/"
    "runtime_activation/ra_slice_004"
)
PUBLISHER_ENTRYPOINT = "scripts.agy_content_publisher:formal_capability_preflight"


class RuntimeActivationE2EBlocked(ValueError):
    """七段 E2E harness 的 deterministic fail-closed 錯誤。"""


def _compact_json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_existing_directory(path: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise RuntimeActivationE2EBlocked(f"{label} must be canonical absolute")
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise RuntimeActivationE2EBlocked(f"{label} must be canonical absolute") from error
    if resolved != candidate or not resolved.is_dir():
        raise RuntimeActivationE2EBlocked(f"{label} must be canonical absolute")
    return resolved


def _strict_descendant(root: Path, candidate: Path, label: str) -> Path:
    path = Path(candidate)
    if not path.is_absolute():
        raise RuntimeActivationE2EBlocked(f"{label} must be absolute")
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise RuntimeActivationE2EBlocked(f"{label} is invalid") from error
    if resolved == root or not resolved.is_relative_to(root):
        raise RuntimeActivationE2EBlocked(f"{label} must be a strict sandbox descendant")
    return resolved


def _reject_overlapping_roots(roots: Mapping[str, Path]) -> None:
    items = list(roots.items())
    for index, (left_name, left) in enumerate(items):
        for right_name, right in items[index + 1 :]:
            if (
                left == right
                or left.is_relative_to(right)
                or right.is_relative_to(left)
            ):
                raise RuntimeActivationE2EBlocked(
                    f"{left_name} and {right_name} roots overlap"
                )


def _runtime_digest(runtime_receipt: Mapping[str, Any]) -> str:
    if not isinstance(runtime_receipt, Mapping):
        raise RuntimeActivationE2EBlocked("runtime receipt must be an object")
    if set(runtime_receipt) != {"status", "runtime_identity_digest"}:
        raise RuntimeActivationE2EBlocked("runtime receipt keys are strict")
    if runtime_receipt.get("status") != "PASS":
        raise RuntimeActivationE2EBlocked("runtime receipt must be PASS")
    digest = runtime_receipt.get("runtime_identity_digest")
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise RuntimeActivationE2EBlocked("runtime identity digest is invalid")
    return digest


def _identifier(value: str, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise RuntimeActivationE2EBlocked(f"{label} is required")
    return value


def _copy_step_evidence(
    *,
    sandbox_root: Path,
    evidence_root: Path,
    step: Mapping[str, Any],
) -> dict[str, Any]:
    copied = dict(step)
    capability = str(step["capability"])
    ordinal = int(step["ordinal"])
    for field, directory, outcome in (
        ("positive_evidence", "positive", "PASS"),
        ("negative_evidence", "blocked", "BLOCKED"),
    ):
        source_identifier = str(step[field])
        source_path = sandbox_root / source_identifier
        target_identifier = f"{directory}/{ordinal:02d}-{capability}.json"
        target_path = evidence_root / target_identifier
        payload = _read_json(source_path)
        if outcome == "BLOCKED" and payload.get("outcome") != "BLOCKED":
            payload = {
                **payload,
                "outcome": "BLOCKED",
                "stable_reason": payload.get("reason") or payload.get("case") or "blocked",
            }
        payload = {
            **payload,
            "source_evidence": source_identifier,
        }
        _write_json(target_path, payload)
        copied[field] = target_identifier
    return copied


def _publisher_context(
    *,
    evidence_root: Path,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
    input_digest: str,
    capability: str,
    ordinal: int,
    **extra: object,
) -> dict[str, object]:
    return {
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_identity_digest,
        "input_digest": input_digest,
        "evidence_root": str(evidence_root),
        "positive_evidence": f"positive/{ordinal:02d}-{capability}.json",
        "negative_evidence": f"blocked/{ordinal:02d}-{capability}.json",
        **extra,
    }


def _publisher_step_blocked_probe(
    *,
    sandbox_root: Path,
    queue_root: Path,
    publisher_state_root: Path,
    evidence_root: Path,
    run_id: str,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
    runtime_receipt: dict[str, Any],
    input_digest: str,
    capability: str,
    ordinal: int,
) -> None:
    context_extra: dict[str, object] = {}
    call_extra: dict[str, object] = {}
    if capability == "select":
        call_extra["run_ids"] = []
    elif capability == "publish":
        context_extra["runtime_identity_digest"] = "e" * 64
    elif capability == "transaction":
        call_extra["state_root"] = queue_root / "nested-state"
    elif capability == "tag":
        context_extra["tag_mode"] = "real-tag"
    elif capability == "push":
        context_extra["push_mode"] = "production"
    else:
        raise RuntimeActivationE2EBlocked(f"blocked probe capability is invalid: {capability}")
    context = _publisher_context(
        evidence_root=evidence_root,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_identity_digest,
        input_digest=input_digest,
        capability=capability,
        ordinal=ordinal,
    )
    context.update(context_extra)
    try:
        publisher.formal_capability_preflight(
            capability,
            run_ids=call_extra.get("run_ids", [run_id]),
            correlation_id=correlation_id,
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=call_extra.get("state_root", publisher_state_root),
            runtime_receipt=runtime_receipt,
            receipt_context=context,
        )
    except publisher.PublishBlocked:
        return
    raise RuntimeActivationE2EBlocked(
        f"publisher blocked probe did not block: {capability}"
    )


def _blocked_receipt_payload(
    *,
    case: str,
    reason: str,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED",
        "case": case,
        "reason": reason,
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_identity_digest,
        "mode": MODE,
        "canary_created": False,
        "production_mutation": False,
        "complete_pass_receipt_written": False,
    }


def _record_blocked_receipt(
    *,
    evidence_root: Path,
    case: str,
    reason: str,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
) -> None:
    _write_json(
        evidence_root / "blocked-receipt.json",
        _blocked_receipt_payload(
            case=case,
            reason=reason,
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
        ),
    )


def _receipt_rejection_cases(receipt: Mapping[str, Any]) -> list[dict[str, object]]:
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        (
            "identity-drift",
            lambda candidate: candidate["steps"][3].__setitem__(
                "actor_identity",
                "actor-ra-slice-004-drift",
            ),
        ),
        (
            "digest-discontinuity",
            lambda candidate: candidate["steps"][4].__setitem__(
                "input_digest",
                _compact_json_digest({"drift": True}),
            ),
        ),
        ("missing-step", lambda candidate: candidate["steps"].pop(5)),
        (
            "duplicate-step",
            lambda candidate: candidate["steps"].__setitem__(
                5,
                deepcopy(candidate["steps"][4]),
            ),
        ),
        (
            "caller-supplied-verdict",
            lambda candidate: candidate.__setitem__("status", "PASS"),
        ),
        (
            "production-mutation",
            lambda candidate: candidate.__setitem__("production_mutation", True),
        ),
    ]
    results: list[dict[str, object]] = []
    for case, mutate in cases:
        candidate = deepcopy(dict(receipt))
        mutate(candidate)
        try:
            validate_capability_receipt(candidate)
        except CapabilityReceiptError as error:
            results.append(
                {
                    "case": case,
                    "outcome": "BLOCKED",
                    "authority": "scripts.pantheon_content_capability_receipt:validate_capability_receipt",
                    "code": error.code,
                    "reason": str(error),
                }
            )
        else:
            raise RuntimeActivationE2EBlocked(f"negative probe did not block: {case}")
    return results


def _publisher_rejection_cases(
    *,
    sandbox_root: Path,
    queue_root: Path,
    publisher_state_root: Path,
    evidence_root: Path,
    run_id: str,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
    runtime_receipt: dict[str, Any],
    input_digest: str,
) -> list[dict[str, object]]:
    cases: list[tuple[str, str, dict[str, object], dict[str, object]]] = [
        (
            "publisher-runtime-drift",
            "publish",
            {"runtime_identity_digest": "e" * 64},
            {},
        ),
        ("publisher-caller-verdict", "select", {"status": "PASS"}, {}),
        (
            "publisher-overlapping-roots",
            "transaction",
            {},
            {"state_root": queue_root / "nested-state"},
        ),
        ("publisher-real-tag-mode", "tag", {"tag_mode": "real-tag"}, {}),
        ("publisher-real-push-mode", "push", {"push_mode": "production"}, {}),
        ("publisher-empty-run-selection", "select", {}, {"run_ids": []}),
    ]
    results: list[dict[str, object]] = []
    for index, (case, capability, context_extra, call_extra) in enumerate(cases, 1):
        context_extra_copy = dict(context_extra)
        context = _publisher_context(
            evidence_root=evidence_root,
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
            input_digest=input_digest,
            capability=f"probe-{case}",
            ordinal=70 + index,
        )
        context.update(context_extra_copy)
        try:
            publisher.formal_capability_preflight(
                capability,
                run_ids=call_extra.get("run_ids", [run_id]),
                correlation_id=correlation_id,
                trusted_sandbox_root=sandbox_root,
                queue_root=queue_root,
                state_root=call_extra.get("state_root", publisher_state_root),
                runtime_receipt=runtime_receipt,
                receipt_context=context,
            )
        except publisher.PublishBlocked as error:
            results.append(
                {
                    "case": case,
                    "outcome": "BLOCKED",
                    "authority": PUBLISHER_ENTRYPOINT,
                    "reason": str(error),
                    "negative_evidence": context["negative_evidence"],
                }
            )
        else:
            raise RuntimeActivationE2EBlocked(f"negative probe did not block: {case}")

    relative_probe = None
    try:
        _canonical_existing_directory(Path("relative-sandbox"), "trusted sandbox root")
    except RuntimeActivationE2EBlocked as error:
        relative_probe = str(error)
    if relative_probe is None:
        raise RuntimeActivationE2EBlocked("negative probe did not block: untrusted-root")
    results.append(
        {
            "case": "untrusted-root",
            "outcome": "BLOCKED",
            "authority": "scripts.pantheon_writer_vnext_runtime_activation_e2e:run_runtime_activation_e2e",
            "reason": relative_probe,
        }
    )

    symlink_path = sandbox_root / "escape-link"
    try:
        symlink_path.symlink_to(sandbox_root.parent)
        try:
            _strict_descendant(sandbox_root, symlink_path / "queue", "symlink probe")
        except RuntimeActivationE2EBlocked as error:
            results.append(
                {
                    "case": "symlink-escape",
                    "outcome": "BLOCKED",
                    "authority": "scripts.pantheon_writer_vnext_runtime_activation_e2e:run_runtime_activation_e2e",
                    "reason": str(error),
                }
            )
        else:
            raise RuntimeActivationE2EBlocked("negative probe did not block: symlink-escape")
    finally:
        try:
            symlink_path.unlink()
        except FileNotFoundError:
            pass

    return results


def _artifact_inventory(evidence_root: Path, directory: str) -> list[str]:
    root = evidence_root / directory
    if not root.exists():
        return []
    return sorted(
        path.relative_to(evidence_root).as_posix()
        for path in root.rglob("*.json")
        if path.is_file()
    )


def _write_source_inventory(evidence_root: Path) -> None:
    _write_text(
        evidence_root / "source-inventory.md",
        "\n".join(
            [
                "# RA-SLICE-004 Source Inventory",
                "",
                "## CodeGraph",
                "",
                "- Status: READY",
                "- Task-semantic query: `coordinator_create_run_receipt_preflight formal_capability_preflight validate_capability_receipt runtime activation e2e`",
                "- Entry points returned:",
                "  - `scripts/agy_gemini_coordinator.py:coordinator_create_run_receipt_preflight`",
                "  - `scripts/agy_content_publisher.py:formal_capability_preflight`",
                "  - `scripts/pantheon_content_capability_receipt.py:validate_capability_receipt`",
                "",
                "## Bounded Source Confirmation",
                "",
                "- `scripts/agy_gemini_coordinator.py`: official create/run preflight remains the source for ordinals 1-2.",
                "- `scripts/agy_content_publisher.py`: official Publisher preflight remains the source for ordinals 3-7.",
                "- `scripts/pantheon_content_capability_receipt.py`: shared `validate_capability_receipt` remains the only full seven-step schema authority.",
                "- `scripts/pantheon_runtime_fs_authority.py`: Publisher sandbox writes continue through `TrustedSandboxDirectoryAuthority` and operation trace checks.",
                "",
                "## Changed Files",
                "",
                "- `scripts/pantheon_writer_vnext_runtime_activation_e2e.py`",
                "- `tests/test_pantheon_writer_vnext_runtime_activation_e2e.py`",
                "- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_004/**`",
                "",
                "## Boundary",
                "",
                "- No coordinator, Publisher, shared validator, runtime manifest, capacity guard, deployment, registry, metadata, article, sitemap, feed, redirect, production transport, tag, push, publication, network write, launchctl, or service mutation was added.",
                "",
            ]
        ),
    )


def _write_text(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def run_runtime_activation_e2e(
    *,
    trusted_sandbox_root: Path,
    runtime_receipt: Mapping[str, Any],
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    brief: Mapping[str, Any],
    run_root: Path | None = None,
    queue_root: Path | None = None,
    publisher_state_root: Path | None = None,
) -> dict[str, Any]:
    """以既有官方入口組合七段 non-production capability receipt。"""

    sandbox_root = _canonical_existing_directory(
        trusted_sandbox_root,
        "trusted sandbox root",
    )
    runtime_receipt_copy = dict(runtime_receipt)
    runtime_identity_digest = _runtime_digest(runtime_receipt_copy)
    execution_line_id = _identifier(execution_line_id, "execution_line_id")
    correlation_id = _identifier(correlation_id, "correlation_id")
    actor_identity = _identifier(actor_identity, "actor_identity")
    if not isinstance(brief, Mapping):
        raise RuntimeActivationE2EBlocked("brief must be an object")

    resolved_run_root = _strict_descendant(
        sandbox_root,
        run_root or sandbox_root / "runs",
        "run root",
    )
    resolved_queue_root = _strict_descendant(
        sandbox_root,
        queue_root or sandbox_root / "queue",
        "queue root",
    )
    resolved_state_root = _strict_descendant(
        sandbox_root,
        publisher_state_root or sandbox_root / "publisher-state",
        "publisher state root",
    )
    evidence_root = _strict_descendant(
        sandbox_root,
        sandbox_root / "evidence",
        "evidence root",
    )
    official_coordinator_evidence = _strict_descendant(
        sandbox_root,
        evidence_root / "official" / "coordinator",
        "coordinator evidence root",
    )
    _reject_overlapping_roots(
        {
            "run": resolved_run_root,
            "queue": resolved_queue_root,
            "publisher_state": resolved_state_root,
            "coordinator_evidence": official_coordinator_evidence,
        }
    )

    envelope = coordinator.coordinator_create_run_receipt_preflight(
        trusted_sandbox_root=sandbox_root,
        run_root=resolved_run_root,
        queue_root=resolved_queue_root,
        evidence_root=official_coordinator_evidence,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_identity_digest,
        runtime_receipt=runtime_receipt_copy,
        brief=dict(brief),
        lane="new",
    )
    steps = [
        _copy_step_evidence(
            sandbox_root=sandbox_root,
            evidence_root=evidence_root,
            step=step,
        )
        for step in envelope["receipt_steps"]
    ]
    run_id = str(envelope["created_run_id"])
    previous_digest = str(steps[-1]["output_digest"])

    try:
        for ordinal, capability in enumerate(
            ("select", "publish", "transaction", "tag", "push"),
            3,
        ):
            context_extra: dict[str, object] = {}
            if capability == "tag":
                context_extra["tag_mode"] = "injected-git-dry-run"
            if capability == "push":
                context_extra["push_mode"] = "injected-git-dry-run"
            result = publisher.formal_capability_preflight(
                capability,
                run_ids=[run_id],
                correlation_id=correlation_id,
                trusted_sandbox_root=sandbox_root,
                queue_root=resolved_queue_root,
                state_root=resolved_state_root,
                runtime_receipt=runtime_receipt_copy,
                receipt_context=_publisher_context(
                    evidence_root=evidence_root,
                    execution_line_id=execution_line_id,
                    correlation_id=correlation_id,
                    actor_identity=actor_identity,
                    runtime_identity_digest=runtime_identity_digest,
                    input_digest=previous_digest,
                    capability=capability,
                    ordinal=ordinal,
                    **context_extra,
                ),
            )
            step = result["receipt_step"]
            _publisher_step_blocked_probe(
                sandbox_root=sandbox_root,
                queue_root=resolved_queue_root,
                publisher_state_root=resolved_state_root,
                evidence_root=evidence_root,
                run_id=run_id,
                execution_line_id=execution_line_id,
                correlation_id=correlation_id,
                actor_identity=actor_identity,
                runtime_identity_digest=runtime_identity_digest,
                runtime_receipt=runtime_receipt_copy,
                input_digest=previous_digest,
                capability=capability,
                ordinal=ordinal,
            )
            steps.append(step)
            previous_digest = str(step["output_digest"])
    except publisher.PublishBlocked as error:
        _record_blocked_receipt(
            evidence_root=evidence_root,
            case="publisher-boundary",
            reason=str(error),
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
        )
        raise RuntimeActivationE2EBlocked(str(error)) from error

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_identity_digest,
        "mode": MODE,
        "canary_created": False,
        "production_mutation": False,
        "steps": steps,
    }
    validate_capability_receipt(receipt)

    matrix_cases = [
        *_receipt_rejection_cases(receipt),
        *_publisher_rejection_cases(
            sandbox_root=sandbox_root,
            queue_root=resolved_queue_root,
            publisher_state_root=resolved_state_root,
            evidence_root=evidence_root,
            run_id=run_id,
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
            runtime_receipt=runtime_receipt_copy,
            input_digest=previous_digest,
        ),
    ]
    _write_json(evidence_root / "positive-receipt.json", receipt)
    _write_json(
        evidence_root / "blocked-receipt.json",
        _blocked_receipt_payload(
            case="negative-probe-fixture",
            reason="fail-closed probes are separated from the complete PASS receipt",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
        ),
    )
    _write_json(
        evidence_root / "negative-matrix.json",
        {
            "schema_version": SCHEMA_VERSION,
            "execution_line_id": execution_line_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "runtime_identity_digest": runtime_identity_digest,
            "mode": MODE,
            "canary_created": False,
            "production_mutation": False,
            "cases": matrix_cases,
        },
    )
    _write_source_inventory(evidence_root)
    positive_inventory = _artifact_inventory(evidence_root, "positive")
    blocked_inventory = _artifact_inventory(evidence_root, "blocked")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "mode": MODE,
        "canary_created": False,
        "production_mutation": False,
        "created_run_id": run_id,
        "evidence_root": str(evidence_root),
        "receipt": receipt,
        "positive_artifact_inventory": positive_inventory,
        "blocked_artifact_inventory": blocked_inventory,
        "negative_matrix": matrix_cases,
    }


def _default_brief() -> dict[str, object]:
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


def _default_runtime_receipt() -> dict[str, str]:
    return {
        "status": "PASS",
        "runtime_identity_digest": _compact_json_digest(
            {
                "card": "CARD-CONTENT-WRITER-VNEXT-RA-SLICE-004",
                "mode": MODE,
                "entrypoints": [
                    "scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight",
                    PUBLISHER_ENTRYPOINT,
                ],
            }
        ),
    }


def _mirror_cli_artifacts(evidence_root: Path, output_root: Path) -> None:
    for name in (
        "positive-receipt.json",
        "blocked-receipt.json",
        "negative-matrix.json",
        "source-inventory.md",
    ):
        shutil.copy2(evidence_root / name, output_root / name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=EVIDENCE_PATH,
        help="RA-SLICE-004 evidence output root",
    )
    args = parser.parse_args()
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    sandbox_root = (output_root / "sandbox").resolve()
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)
    sandbox_root.mkdir()
    result = run_runtime_activation_e2e(
        trusted_sandbox_root=sandbox_root,
        runtime_receipt=_default_runtime_receipt(),
        execution_line_id="exec-ra-slice-004",
        correlation_id="corr-ra-slice-004",
        actor_identity="actor-ra-slice-004",
        brief=_default_brief(),
    )
    _mirror_cli_artifacts(Path(result["evidence_root"]), output_root)
    _write_text(
        output_root / "verification-receipt.md",
        "\n".join(
            [
                "# RA-SLICE-004 Verification Receipt",
                "",
                "## Positive Probe",
                "",
                "- Seven official preflight steps produced one digest-continuous receipt.",
                "- `positive-receipt.json`: PASS by `validate_capability_receipt`.",
                "- `canary_created=false` and `production_mutation=false`.",
                "",
                "## Fail-closed Probe",
                "",
                "- `negative-matrix.json`: identity, digest, step, caller verdict, production boundary, Publisher drift, overlapping roots, dry-run mode, empty selection, untrusted root, and symlink escape probes BLOCKED.",
                "- `blocked-receipt.json`: fail-closed fixture remains separate from the PASS receipt.",
                "",
                "## Artifact Separation",
                "",
                "- Positive artifacts are under `sandbox/evidence/positive/`.",
                "- Blocked artifacts are under `sandbox/evidence/blocked/`.",
                "",
                "## Verification Commands",
                "",
                "- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py -q`",
                "- `uv run pytest tests/test_agy_gemini_coordinator_capability_receipt.py tests/test_agy_content_publisher_capability_receipt.py tests/test_pantheon_content_capability_receipt.py -q`",
                "- `git diff --check`",
                "",
            ]
        ),
    )
    print(json.dumps({"status": result["status"], "created_run_id": result["created_run_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""協調 Pantheon 私密 run、sanitized outbox 與使用者擁有的 Gemini runner。"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import urlsplit

from scripts import agy_content_publisher as publisher
from scripts import agy_editorial_contracts as editorial_contracts
from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as pipeline
from scripts import pantheon_content_runtime_manifest as formal_runtime
from scripts.agy_gemini_outbox import (
    ExternalJobFailed,
    ExternalJobPending,
    OUTBOX_MAX_TRANSPORT_RETRIES,
    SHA256_PATTERN,
    atomic_write_json,
    run_pipeline_tick,
    validate_external_request,
)
from scripts.agy_gemini_runner import process_once


MAX_BRIEF_BYTES = 12 * 1024
MAX_ACTIVE_RUNS_PER_CYCLE = 5
DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS = 2
DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE = 1
DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN = 5
DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE = 1
MAX_LEGACY_REWRITE_LINEAGE_RETRIES = 100
CONTENT_LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
OPERATOR_TERMINALIZATION_REASONS = frozenset({
    "UNSUPPORTED_MODEL_CANARY_ABORT",
})
JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EXACT_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
Tick = Callable[[Path, Path], dict[str, Any]]
Process = Callable[[Path], dict[str, str]]
EditorialFactory = Callable[[dict[str, Any]], dict[str, Any]]
EditorialWriter = Callable[[dict[str, Any]], dict[str, Any]]
EditorialReviewer = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
COORDINATOR_RECEIPT_RUN_ID = "ra-slice-002-synthetic-create-run"
COORDINATOR_RECEIPT_ALLOWED_RUNTIME_KEYS = frozenset(
    {
        "status",
        "runtime_identity_digest",
    }
)
COORDINATOR_RECEIPT_CALLER_VERDICT_KEYS = frozenset(
    {
        "valid",
        "ready",
        "verdict",
    }
)


class CoordinatorReceiptBlocked(ValueError):
    """Coordinator create/run receipt preflight 的穩定 fail-closed boundary。"""


def _validate_formal_runtime(
    queue_root: Path,
    actor_root: Path | None = None,
) -> dict[str, Any]:
    return formal_runtime.validate_runtime_tick(
        "com.pantheon.agy-gemini-coordinator",
        queue_root=queue_root.resolve(),
        state_root=Path(
            os.environ.get("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", Path.cwd())
        ),
        actor_root=(actor_root or Path.cwd()).resolve(),
        log_root=Path(os.environ.get("PANTHEON_RUNTIME_LOG_ROOT", Path.cwd())),
    )


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


def _coordinator_receipt_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _coordinator_receipt_evidence_identifier(
    sandbox_root: Path,
    evidence_root: Path,
    artifact_name: str,
) -> str:
    artifact_path = (evidence_root / artifact_name).resolve(strict=False)
    if not artifact_path.is_file():
        raise CoordinatorReceiptBlocked("evidence: artifact must exist")
    try:
        relative = artifact_path.relative_to(sandbox_root)
    except ValueError as error:
        raise CoordinatorReceiptBlocked(
            "evidence: artifact must stay under trusted sandbox root"
        ) from error
    return relative.as_posix()


def _coordinator_receipt_identifier(value: object, label: str, case: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise CoordinatorReceiptBlocked(f"{case}: {label} is required")
    return value


def _coordinator_receipt_blocked_artifact(
    evidence_root: Path | None,
    *,
    case: str,
    step: str,
    entrypoint: str,
    reason: str,
    execution_line_id: str | None = None,
    correlation_id: str | None = None,
    actor_identity: str | None = None,
    runtime_identity_digest: str | None = None,
) -> None:
    if evidence_root is None:
        return
    artifact = {
        "schema_version": 1,
        "case": case,
        "step": step,
        "entrypoint": entrypoint,
        "outcome": "BLOCKED",
        "reason": reason,
        "execution_line_id": execution_line_id or "unavailable",
        "correlation_id": correlation_id or "unavailable",
        "actor_identity": actor_identity or "unavailable",
        "runtime_identity_digest": runtime_identity_digest or "0" * 64,
        "production_mutation": False,
    }
    atomic_write_json(evidence_root / f"blocked-{step}.json", artifact)


def _coordinator_receipt_block(
    evidence_root: Path | None,
    *,
    case: str,
    step: str = "create",
    reason: str,
    execution_line_id: str | None = None,
    correlation_id: str | None = None,
    actor_identity: str | None = None,
    runtime_identity_digest: str | None = None,
) -> None:
    _coordinator_receipt_blocked_artifact(
        evidence_root,
        case=case,
        step=step,
        entrypoint="scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight",
        reason=reason,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_identity_digest,
    )
    raise CoordinatorReceiptBlocked(f"{case}: {reason}")


def _coordinator_receipt_create_blocked_probe(
    *,
    trusted_sandbox_root: Path,
    run_root: Path,
    queue_root: Path,
    evidence_root: Path,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
    runtime_receipt: Mapping[str, Any],
) -> None:
    try:
        coordinator_create_run_receipt_preflight(
            trusted_sandbox_root=trusted_sandbox_root,
            run_root=run_root,
            queue_root=queue_root,
            evidence_root=evidence_root,
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
            runtime_receipt=dict(runtime_receipt),
            brief=None,
            lane="new",
            tick=lambda *_args: {"status": "unreachable"},
            process=lambda *_args, **_kwargs: {"status": "unreachable"},
        )
    except CoordinatorReceiptBlocked:
        artifact_path = evidence_root / "blocked-create.json"
        if artifact_path.is_file():
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            if artifact.get("case") == "missing-brief":
                return
    _coordinator_receipt_block(
        evidence_root,
        case="missing-brief-probe-drift",
        reason="missing brief probe did not reject",
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_identity_digest,
    )


def _coordinator_receipt_run_blocked_probe(
    *,
    queue_root: Path,
    evidence_root: Path,
    repo_root: Path,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
) -> None:
    try:
        cycle_once(
            queue_root,
            repo_root=repo_root,
            exact_run_ids=["ra-slice-002-missing-negative-probe"],
        )
    except ValueError as error:
        reason = str(error)
        if reason.startswith("exact run ids not found:"):
            _coordinator_receipt_blocked_artifact(
                evidence_root,
                case="run-boundary",
                step="run",
                entrypoint="scripts.agy_gemini_coordinator:cycle_once",
                reason=reason,
                execution_line_id=execution_line_id,
                correlation_id=correlation_id,
                actor_identity=actor_identity,
                runtime_identity_digest=runtime_identity_digest,
            )
            return
        raise
    _coordinator_receipt_block(
        evidence_root,
        case="run-boundary-probe-drift",
        step="run",
        reason="missing exact run id probe did not reject",
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_identity_digest,
    )


def _coordinator_receipt_sandbox_root(path: Path) -> Path:
    root = Path(path)
    if not root.is_absolute():
        raise CoordinatorReceiptBlocked("sandbox-root: trusted sandbox root must be absolute")
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CoordinatorReceiptBlocked(
            "sandbox-root: trusted sandbox root is invalid"
        ) from error
    if resolved != root or not resolved.is_dir() or root.is_symlink():
        raise CoordinatorReceiptBlocked(
            "sandbox-root: trusted sandbox root must be canonical"
        )
    return resolved


def _coordinator_receipt_descendant(
    sandbox_root: Path,
    path: Path,
    label: str,
) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise CoordinatorReceiptBlocked(f"{label}: root must be absolute")
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise CoordinatorReceiptBlocked(f"{label}: root is invalid") from error
    if resolved == sandbox_root or not resolved.is_relative_to(sandbox_root):
        raise CoordinatorReceiptBlocked(
            f"{label}: root must be a strict trusted sandbox descendant"
        )
    return resolved


def _coordinator_receipt_validate_roots(
    *,
    trusted_sandbox_root: Path,
    run_root: Path,
    queue_root: Path,
    evidence_root: Path,
) -> tuple[Path, Path, Path, Path]:
    sandbox_root = _coordinator_receipt_sandbox_root(trusted_sandbox_root)
    resolved_run = _coordinator_receipt_descendant(sandbox_root, run_root, "run")
    resolved_queue = _coordinator_receipt_descendant(sandbox_root, queue_root, "queue")
    resolved_evidence = _coordinator_receipt_descendant(
        sandbox_root,
        evidence_root,
        "evidence",
    )
    pairs = (
        ("run", resolved_run, "queue", resolved_queue),
        ("run", resolved_run, "evidence", resolved_evidence),
        ("queue", resolved_queue, "evidence", resolved_evidence),
    )
    for left_label, left, right_label, right in pairs:
        if left == right or left.is_relative_to(right) or right.is_relative_to(left):
            raise CoordinatorReceiptBlocked(
                f"{left_label}/{right_label}: roots must not overlap"
            )
    return sandbox_root, resolved_run, resolved_queue, resolved_evidence


def _coordinator_receipt_runtime_digest(
    runtime_identity_digest: object,
    runtime_receipt: object,
    evidence_root: Path,
    *,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
) -> str:
    if not isinstance(runtime_receipt, Mapping):
        _coordinator_receipt_block(
            evidence_root,
            case="runtime-missing-digest",
            reason="runtime identity receipt is required",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
        )
    if COORDINATOR_RECEIPT_CALLER_VERDICT_KEYS.intersection(runtime_receipt):
        _coordinator_receipt_block(
            evidence_root,
            case="caller-verdict",
            reason="caller-supplied verdict is not accepted",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
        )
    if set(runtime_receipt) - COORDINATOR_RECEIPT_ALLOWED_RUNTIME_KEYS:
        _coordinator_receipt_block(
            evidence_root,
            case="extra-runtime-key",
            reason="runtime identity receipt contains unsupported keys",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
        )
    if runtime_receipt.get("status") != "PASS":
        _coordinator_receipt_block(
            evidence_root,
            case="runtime-missing-digest",
            reason="runtime identity receipt must be PASS",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
        )
    digest = runtime_receipt.get("runtime_identity_digest")
    if (
        type(digest) is not str
        or SHA256_PATTERN.fullmatch(digest) is None
        or digest != runtime_identity_digest
    ):
        _coordinator_receipt_block(
            evidence_root,
            case=(
                "runtime-digest-mismatch"
                if type(digest) is str
                and type(runtime_identity_digest) is str
                and SHA256_PATTERN.fullmatch(runtime_identity_digest) is not None
                else "runtime-missing-digest"
            ),
            reason="runtime identity digest is invalid",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=digest if type(digest) is str else None,
        )
    return digest


def _coordinator_receipt_brief(
    brief: object,
    evidence_root: Path,
    *,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
) -> dict[str, Any]:
    if not isinstance(brief, Mapping):
        _coordinator_receipt_block(
            evidence_root,
            case="missing-brief",
            reason="brief is required",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
        )
    articles = brief.get("articles")
    if (
        brief.get("schema_version") != 1
        or brief.get("run_id") != COORDINATOR_RECEIPT_RUN_ID
        or brief.get("mode") != "create"
        or not isinstance(articles, list)
        or len(articles) > 1
    ):
        _coordinator_receipt_block(
            evidence_root,
            case="too-many-articles",
            reason="brief must be the fixed synthetic create brief with at most one article",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
        )
    return dict(brief)


def _coordinator_receipt_step(
    *,
    capability: str,
    ordinal: int,
    input_digest: str,
    output_digest: str,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
    positive_evidence: str,
    negative_evidence: str,
) -> dict[str, Any]:
    return {
        "capability": capability,
        "ordinal": ordinal,
        "entrypoint": "scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight",
        "input_digest": input_digest,
        "output_digest": output_digest,
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_identity_digest,
        "positive_evidence": positive_evidence,
        "negative_evidence": negative_evidence,
        "positive_outcome": "PASS",
        "negative_outcome": "BLOCKED",
    }


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_only_enabled() -> bool:
    raw = os.environ.get("AGY_GEMINI_NEW_ONLY", "0")
    if raw not in {"0", "1"}:
        raise ValueError("AGY_GEMINI_NEW_ONLY must be 0 or 1")
    return raw == "1"


def _brief(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "brief.json"
    if not path.is_file():
        raise ValueError("run directory must contain brief.json")
    if path.stat().st_size > MAX_BRIEF_BYTES:
        raise ValueError("brief exceeds 12 KB")
    brief = json.loads(path.read_text(encoding="utf-8"))
    run_id = brief.get("run_id")
    articles = brief.get("articles")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("brief run_id must be non-empty")
    if not isinstance(articles, list) or len(articles) > 5:
        raise ValueError("brief articles must contain at most 5 items")
    return brief


def _state_path(run_id: str, queue_root: Path) -> Path:
    opaque_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    return queue_root / "runs" / f"{opaque_id}.json"


def _run_identity_lock_path(run_id: str, queue_root: Path) -> Path:
    opaque_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    return queue_root / "run-identity-locks" / f"{opaque_id}.lock"


@contextmanager
def _run_identity_lock(run_id: str, queue_root: Path) -> Iterator[None]:
    path = _run_identity_lock_path(run_id, queue_root.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _reservation_is_owned(
    state: object,
    *,
    run_id: str,
    run_dir: Path,
    correlation_id: str,
    reservation_token: str,
) -> bool:
    return (
        isinstance(state, dict)
        and state.get("status") == "reserved"
        and state.get("run_id") == run_id
        and state.get("run_dir") == str(run_dir.resolve())
        and state.get("correlation_id") == correlation_id
        and state.get("reservation_token") == reservation_token
    )


def _reservation_marker_path(path: Path, reservation_token: str, phase: str) -> Path:
    return path.with_name(f".{path.name}.{reservation_token}.{phase}")


def _write_json_exclusive(path: Path, payload: object) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise ValueError("reservation ownership mismatch") from error


def _reserve_run_identity(
    run_id: str,
    run_dir: Path,
    queue_root: Path,
    correlation_id: str,
    reservation_token: str,
) -> Path:
    path = _state_path(run_id, queue_root.resolve())
    reservation = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "reserved",
        "correlation_id": correlation_id,
        "reservation_token": reservation_token,
        "reserved_at": _now(),
    }
    with _run_identity_lock(run_id, queue_root):
        if run_dir.exists():
            raise ValueError("exact run identity is already in use")
        path.parent.mkdir(parents=True, exist_ok=True)
        if any(path.parent.glob(f".{path.name}.*.transition")) or any(
            path.parent.glob(f".{path.name}.*.cleanup")
        ):
            raise ValueError("exact run identity has a stale transaction")
        try:
            _write_json_exclusive(path, reservation)
        except ValueError as error:
            raise ValueError("exact run identity is already in use") from error
    return path


def _release_run_reservation(
    run_id: str,
    run_dir: Path,
    queue_root: Path,
    correlation_id: str,
    reservation_token: str,
) -> None:
    path = _state_path(run_id, queue_root.resolve())
    cleanup_path = _reservation_marker_path(path, reservation_token, "cleanup")
    with _run_identity_lock(run_id, queue_root):
        try:
            os.rename(path, cleanup_path)
        except FileNotFoundError:
            return
        try:
            state = json.loads(cleanup_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = None
        if not _reservation_is_owned(
            state,
            run_id=run_id,
            run_dir=run_dir,
            correlation_id=correlation_id,
            reservation_token=reservation_token,
        ):
            if not path.exists():
                os.rename(cleanup_path, path)
            return
        cleanup_path.unlink()


def _activate_run_reservation(
    run_id: str,
    staging_run_dir: Path,
    run_dir: Path,
    queue_root: Path,
    correlation_id: str,
    reservation_token: str,
) -> dict[str, Any]:
    state_path = _state_path(run_id, queue_root.resolve())
    transition_path = _reservation_marker_path(
        state_path,
        reservation_token,
        "transition",
    )
    with _run_identity_lock(run_id, queue_root):
        try:
            os.rename(state_path, transition_path)
        except FileNotFoundError as error:
            raise ValueError("reservation ownership mismatch") from error
        try:
            reservation = json.loads(transition_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            reservation = None
        if not _reservation_is_owned(
            reservation,
            run_id=run_id,
            run_dir=run_dir,
            correlation_id=correlation_id,
            reservation_token=reservation_token,
        ):
            if not state_path.exists():
                os.rename(transition_path, state_path)
            raise ValueError("reservation ownership mismatch")
        staging_identity = None
        published = False
        active_created = False
        try:
            brief = _brief(staging_run_dir)
            if brief.get("run_id") != run_id or staging_run_dir.name != run_id:
                raise ValueError("exact run identity closure failed")
            if run_dir.exists():
                raise ValueError("exact run identity is already in use")
            staging_identity = staging_run_dir.stat()
            os.rename(staging_run_dir, run_dir)
            published = True
            _cleanup_staging(staging_run_dir.parent)
            now = _now()
            state = {
                "schema_version": 1,
                "run_id": run_id,
                "run_dir": str(run_dir.resolve()),
                "status": "active",
                "correlation_id": correlation_id,
                "registered_at": now,
                "updated_at": now,
            }
            transition_path.unlink()
            _write_json_exclusive(state_path, state)
            active_created = True
            return state
        except BaseException:
            if published and not active_created and staging_identity is not None:
                try:
                    published_identity = run_dir.stat()
                except FileNotFoundError:
                    published_identity = None
                if (
                    published_identity is not None
                    and published_identity.st_dev == staging_identity.st_dev
                    and published_identity.st_ino == staging_identity.st_ino
                    and not staging_run_dir.exists()
                ):
                    staging_run_dir.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(run_dir, staging_run_dir)
            if transition_path.exists():
                transition_path.unlink()
            raise


def _cleanup_staging(staging_token_root: Path) -> None:
    if staging_token_root.exists():
        shutil.rmtree(staging_token_root)
    if staging_token_root.exists():
        raise ValueError("exact run staging cleanup failed")
    staging_root = staging_token_root.parent
    try:
        staging_root.rmdir()
    except OSError:
        pass


def _translation_replacement_decision_path(
    queue_root: Path,
    run_id: str,
) -> Path:
    opaque_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    return queue_root / "translation-replacement-decisions" / f"{opaque_id}.json"


def register_run(
    run_dir: Path,
    queue_root: Path,
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """將一個本機私密 run 登記為 active；不建立外部 request。"""
    _validate_formal_runtime(queue_root)
    resolved = run_dir.resolve()
    brief = _brief(resolved)
    path = _state_path(str(brief["run_id"]), queue_root.resolve())
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("run_dir") != str(resolved) or state.get("run_id") != brief["run_id"]:
            raise ValueError("registered run identity collision")
        return state
    now = _now()
    effective_correlation_id = correlation_id or secrets.token_hex(16)
    if not effective_correlation_id or effective_correlation_id.strip() != effective_correlation_id:
        raise ValueError("correlation id is required")
    state = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "run_dir": str(resolved),
        "status": "active",
        "correlation_id": effective_correlation_id,
        "registered_at": now,
        "updated_at": now,
    }
    atomic_write_json(path, state)
    return state


def read_run_state(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    _validate_formal_runtime(queue_root)
    brief = _brief(run_dir.resolve())
    path = _state_path(str(brief["run_id"]), queue_root.resolve())
    if not path.exists():
        raise ValueError("run is not registered")
    return json.loads(path.read_text(encoding="utf-8"))


def coordinator_create_run_receipt_preflight(
    *,
    trusted_sandbox_root: Path,
    run_root: Path,
    queue_root: Path,
    evidence_root: Path,
    execution_line_id: str,
    correlation_id: str,
    actor_identity: str,
    runtime_identity_digest: str,
    runtime_receipt: dict[str, Any] | None,
    brief: Mapping[str, Any] | None,
    lane: str = "new",
    tick: Tick | None = None,
    process: Callable[..., dict[str, str]] | None = None,
) -> dict[str, Any]:
    """在 trusted sandbox 內產生 coordinator create/run normalized receipt。"""

    try:
        (
            sandbox_root,
            resolved_run_root,
            resolved_queue_root,
            resolved_evidence_root,
        ) = _coordinator_receipt_validate_roots(
            trusted_sandbox_root=trusted_sandbox_root,
            run_root=run_root,
            queue_root=queue_root,
            evidence_root=evidence_root,
        )
    except CoordinatorReceiptBlocked:
        raise

    execution_line_id = _coordinator_receipt_identifier(
        execution_line_id,
        "execution_line_id",
        "execution-line",
    )
    if type(correlation_id) is not str or not correlation_id or correlation_id.strip() != correlation_id:
        _coordinator_receipt_block(
            resolved_evidence_root,
            case="blank-correlation",
            reason="correlation_id is required",
            execution_line_id=execution_line_id,
            correlation_id=None if type(correlation_id) is not str else correlation_id,
        )
    actor_identity = _coordinator_receipt_identifier(
        actor_identity,
        "actor_identity",
        "actor",
    )
    if lane != "new":
        _coordinator_receipt_block(
            resolved_evidence_root,
            case="wrong-lane",
            reason="lane must be the fixed synthetic new lane",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_identity_digest,
        )
    runtime_digest = _coordinator_receipt_runtime_digest(
        runtime_identity_digest,
        runtime_receipt,
        resolved_evidence_root,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
    )
    synthetic_brief = _coordinator_receipt_brief(
        brief,
        resolved_evidence_root,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_digest,
    )
    run_id = str(synthetic_brief["run_id"])
    run_dir = resolved_run_root / run_id
    create_input_digest = _coordinator_receipt_digest(
        {
            "brief": synthetic_brief,
            "execution_line_id": execution_line_id,
            "correlation_id": correlation_id,
            "actor_identity": actor_identity,
            "runtime_identity_digest": runtime_digest,
        }
    )
    atomic_write_json(run_dir / "brief.json", synthetic_brief)
    registered = register_run(
        run_dir,
        resolved_queue_root,
        correlation_id=correlation_id,
    )
    if (
        registered.get("run_id") != run_id
        or registered.get("run_dir") != str(run_dir.resolve())
        or registered.get("correlation_id") != correlation_id
    ):
        _coordinator_receipt_block(
            resolved_evidence_root,
            case="create-identity-drift",
            reason="registered run identity drifted",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_digest,
        )
    create_state_projection = {
        "schema_version": registered.get("schema_version"),
        "run_id": registered.get("run_id"),
        "run_dir_digest": _coordinator_receipt_digest(
            {"root": "run", "run_id": run_id}
        ),
        "status": registered.get("status"),
        "correlation_id": registered.get("correlation_id"),
    }
    create_output_digest = _coordinator_receipt_digest(create_state_projection)
    create_positive = {
        "schema_version": 1,
        "step": "create",
        "entrypoint": "scripts.agy_gemini_coordinator:register_run",
        "outcome": "PASS",
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_digest,
        "input_digest": create_input_digest,
        "output_digest": create_output_digest,
        "run_id": run_id,
        "state_digest": create_output_digest,
        "production_mutation": False,
    }
    atomic_write_json(resolved_evidence_root / "positive-create.json", create_positive)
    _coordinator_receipt_create_blocked_probe(
        trusted_sandbox_root=sandbox_root,
        run_root=resolved_run_root,
        queue_root=resolved_queue_root,
        evidence_root=resolved_evidence_root,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_digest,
        runtime_receipt=runtime_receipt,
    )

    tick_calls = 0

    def local_tick(local_run_dir: Path, job_queue_root: Path) -> dict[str, object]:
        nonlocal tick_calls
        tick_calls += 1
        if tick_calls == 1:
            raise ExternalJobPending("ra-slice-002-local-job")
        return {
            "status": "complete",
            "bounded": True,
            "job_queue": job_queue_root.name,
            "run_id": local_run_dir.name,
        }

    def local_process(
        _queue_root: Path,
        **_kwargs: object,
    ) -> dict[str, str]:
        return {"status": "processed", "job_id": "ra-slice-002-local-job"}

    try:
        summary = cycle_once(
            resolved_queue_root,
            tick=tick or local_tick,
            process=process or local_process,
            repo_root=resolved_run_root.parent,
            exact_run_ids=[run_id],
        )
    except ValueError as error:
        reason = str(error)
        if not reason.startswith("exact run ids not found:"):
            raise
        _coordinator_receipt_block(
            resolved_evidence_root,
            case="run-boundary",
            step="run",
            reason=f"coordinator run boundary rejected: {reason}",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_digest,
        )
    final_state = read_run_state(run_dir, resolved_queue_root)
    if final_state.get("correlation_id") != correlation_id:
        _coordinator_receipt_block(
            resolved_evidence_root,
            case="correlation-drift",
            step="run",
            reason="correlation drifted across create/run",
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_digest,
        )
    run_projection = {
        "summary": summary,
        "state": {
            "run_id": final_state.get("run_id"),
            "run_dir_digest": _coordinator_receipt_digest(
                {"root": "run", "run_id": run_id}
            ),
            "status": final_state.get("status"),
            "correlation_id": final_state.get("correlation_id"),
            "result": final_state.get("result"),
        },
    }
    run_output_digest = _coordinator_receipt_digest(run_projection)
    run_positive = {
        "schema_version": 1,
        "step": "run",
        "entrypoint": "scripts.agy_gemini_coordinator:cycle_once",
        "outcome": "PASS",
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_digest,
        "input_digest": create_output_digest,
        "output_digest": run_output_digest,
        "run_id": run_id,
        "summary_digest": _coordinator_receipt_digest(summary),
        "state_digest": _coordinator_receipt_digest(run_projection["state"]),
        "production_mutation": False,
    }
    atomic_write_json(resolved_evidence_root / "positive-run.json", run_positive)
    _coordinator_receipt_run_blocked_probe(
        queue_root=resolved_queue_root,
        evidence_root=resolved_evidence_root,
        repo_root=resolved_run_root.parent,
        execution_line_id=execution_line_id,
        correlation_id=correlation_id,
        actor_identity=actor_identity,
        runtime_identity_digest=runtime_digest,
    )
    negative_matrix = {
        "schema_version": 1,
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_digest,
        "production_mutation": False,
        "blocked_cases": [
            "missing-brief",
            "blank-correlation",
            "wrong-lane",
            "untrusted-root",
            "runtime-missing-digest",
            "runtime-digest-mismatch",
            "caller-verdict",
            "extra-runtime-key",
        ],
    }
    atomic_write_json(resolved_evidence_root / "negative-matrix.json", negative_matrix)
    receipt_steps = [
        _coordinator_receipt_step(
            capability="create",
            ordinal=1,
            input_digest=create_input_digest,
            output_digest=create_output_digest,
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_digest,
            positive_evidence=_coordinator_receipt_evidence_identifier(
                sandbox_root,
                resolved_evidence_root,
                "positive-create.json",
            ),
            negative_evidence=_coordinator_receipt_evidence_identifier(
                sandbox_root,
                resolved_evidence_root,
                "blocked-create.json",
            ),
        ),
        _coordinator_receipt_step(
            capability="run",
            ordinal=2,
            input_digest=create_output_digest,
            output_digest=run_output_digest,
            execution_line_id=execution_line_id,
            correlation_id=correlation_id,
            actor_identity=actor_identity,
            runtime_identity_digest=runtime_digest,
            positive_evidence=_coordinator_receipt_evidence_identifier(
                sandbox_root,
                resolved_evidence_root,
                "positive-run.json",
            ),
            negative_evidence=_coordinator_receipt_evidence_identifier(
                sandbox_root,
                resolved_evidence_root,
                "blocked-run.json",
            ),
        ),
    ]
    return {
        "schema_version": 1,
        "mode": "synthetic-non-production",
        "execution_line_id": execution_line_id,
        "correlation_id": correlation_id,
        "actor_identity": actor_identity,
        "runtime_identity_digest": runtime_digest,
        "canary_created": False,
        "production_mutation": False,
        "created_run_id": run_id,
        "receipt_steps": receipt_steps,
        "run_summary": summary,
    }


def terminalize_pending_job(
    run_dir: Path,
    queue_root: Path,
    *,
    job_queue_root: Path | None = None,
    lane: str,
    expected_run_id: str,
    job_id: str,
    request_sha256: str,
    model: str,
    role: str,
    transport_attempt: int,
    reason: str,
    execute: bool = False,
) -> dict[str, Any]:
    """預覽或終止一筆 identity 完全相符、仍未被 runner claim 的 outbox job。"""
    if JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ValueError("operator terminalization job id is invalid")
    if SHA256_PATTERN.fullmatch(request_sha256) is None:
        raise ValueError("operator terminalization request hash is invalid")
    if role not in {"writer", "reviewer"}:
        raise ValueError("operator terminalization role is invalid")
    if (
        type(transport_attempt) is not int
        or type(transport_attempt) is bool
        or not 0 <= transport_attempt <= OUTBOX_MAX_TRANSPORT_RETRIES
    ):
        raise ValueError("operator terminalization transport attempt is invalid")
    if reason not in OPERATOR_TERMINALIZATION_REASONS:
        raise ValueError("operator terminalization reason is not closed")

    if lane not in CONTENT_LANES:
        raise ValueError("operator terminalization lane is invalid")
    state_root = queue_root.resolve()
    job_root = (job_queue_root or state_root).resolve()
    if job_root != state_root and (
        job_root.parent != state_root / "lanes" or job_root.name != lane
    ):
        raise ValueError("operator terminalization job queue root does not match lane")
    resolved_run_dir = run_dir.resolve()
    brief = _brief(resolved_run_dir)
    if brief.get("run_id") != expected_run_id:
        raise ValueError("operator terminalization run id mismatch")
    state = read_run_state(resolved_run_dir, state_root)
    if (
        state.get("run_id") != expected_run_id
        or state.get("run_dir") != str(resolved_run_dir)
    ):
        raise ValueError("operator terminalization state identity mismatch")
    expected_identity = {
        "job_id": job_id,
        "request_sha256": request_sha256,
        "model": model,
        "role": role,
        "transport_attempt": transport_attempt,
    }
    decision_path = job_root / "operator-terminalizations" / f"{job_id}.json"
    state_receipt = {
        "decision": str(decision_path.relative_to(state_root)),
        **expected_identity,
        "lane": lane,
        "reason": reason,
    }
    operator_state_matches = (
        state.get("status") == "failed"
        and state.get("error_type") == "OperatorTerminalized"
        and state.get("last_job_id") == job_id
        and state.get("operator_terminalization") == state_receipt
    )

    outbox_path = job_root / "outbox" / f"{job_id}.json"
    claimed_path = job_root / "outbox" / f"{job_id}.json.terminalizing"
    processing_path = job_root / "processing" / f"{job_id}.json"
    archive_path = job_root / "archive" / f"{job_id}.json"
    resolved_paths = [
        ("outbox", outbox_path),
        ("terminalizing", claimed_path),
        ("processing", processing_path),
        ("archive", archive_path),
    ]
    locations = [(name, path) for name, path in resolved_paths if path.exists()]
    if len(locations) != 1:
        raise ValueError("operator terminalization request location is ambiguous")
    location, request_path = locations[0]
    if location == "processing":
        raise ValueError("operator terminalization job is already processing")
    if request_path.is_symlink() or not request_path.is_file():
        raise ValueError("operator terminalization requires regular request file")
    if (job_root / "inbox" / f"{job_id}.json").exists() or (
        job_root / "failed" / f"{job_id}.json"
    ).exists():
        raise ValueError("operator terminalization job already has a provider outcome")
    if (job_root / "production-attempts" / f"{job_id}.attempt").exists():
        raise ValueError("operator terminalization job already has production attempt evidence")

    request_bytes = request_path.read_bytes()
    request = json.loads(request_bytes)
    validate_external_request(request)
    actual_identity = {
        "job_id": request.get("job_id"),
        "request_sha256": request.get("request_sha256"),
        "model": request.get("model"),
        "role": request.get("role"),
        "transport_attempt": request.get("transport_attempt", 0),
    }
    if actual_identity != expected_identity:
        raise ValueError("operator terminalization request identity mismatch")
    request_file_sha256 = hashlib.sha256(request_bytes).hexdigest()

    decision: dict[str, Any] | None = None
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        required_decision = {
            "schema_version",
            "status",
            "action",
            "run_id",
            "lane",
            "job_id",
            "request_sha256",
            "model",
            "role",
            "transport_attempt",
            "reason",
            "request_file_sha256",
            "claimed_at",
            "from",
            "to",
        }
        allowed_decision = required_decision | {"terminalized_at"}
        if (
            type(decision) is not dict
            or not required_decision <= set(decision)
            or not set(decision) <= allowed_decision
            or decision.get("schema_version") != 1
            or decision.get("status") not in {"terminalizing", "terminalized"}
            or (decision.get("status") == "terminalized")
            != ("terminalized_at" in decision)
            or decision.get("action") != "terminalize_pending"
            or decision.get("run_id") != expected_run_id
            or decision.get("lane") != lane
            or any(decision.get(key) != value for key, value in expected_identity.items())
            or decision.get("reason") != reason
            or decision.get("request_file_sha256") != request_file_sha256
            or decision.get("from") != "outbox"
            or decision.get("to") != "archive"
        ):
            raise ValueError("operator terminalization decision identity mismatch")
        try:
            datetime.fromisoformat(str(decision["claimed_at"]))
            if "terminalized_at" in decision:
                datetime.fromisoformat(str(decision["terminalized_at"]))
        except ValueError:
            raise ValueError("operator terminalization decision timestamp is invalid") from None

    result = {
        "status": "dry_run",
        "action": "terminalize_pending",
        "run_id": expected_run_id,
        "lane": lane,
        **expected_identity,
        "reason": reason,
        "from": "outbox",
        "to": "archive",
    }
    if operator_state_matches:
        if location != "archive" or decision is None:
            raise ValueError("operator terminalization terminal state evidence is incomplete")
        if decision["status"] == "terminalized":
            return {
                **result,
                "status": "already_terminalized",
                "from": "archive",
                "decision": state_receipt["decision"],
            }
        if not execute:
            return {**result, "from": "archive"}
        decision = {**decision, "status": "terminalized", "terminalized_at": _now()}
        atomic_write_json(decision_path, decision)
        return {
            **result,
            "status": "terminalized",
            "from": "archive",
            "decision": state_receipt["decision"],
        }
    if state.get("status") != "active":
        raise ValueError("operator terminalization requires active run")
    if state.get("last_job_id") != job_id:
        raise ValueError("operator terminalization last job mismatch")
    if decision is not None and location == "outbox":
        raise ValueError("operator terminalization decision conflicts with pending outbox")
    if location == "archive" and decision is None:
        raise ValueError("operator terminalization archive lacks operator decision")
    if not execute:
        return {**result, "from": location}

    if location == "outbox":
        try:
            os.replace(outbox_path, claimed_path)
        except FileNotFoundError:
            if processing_path.exists():
                raise ValueError("operator terminalization job is already processing") from None
            raise ValueError("operator terminalization lost atomic claim") from None
        request_path = claimed_path
        location = "terminalizing"
    if decision is None:
        decision = {
            "schema_version": 1,
            "status": "terminalizing",
            "action": "terminalize_pending",
            "run_id": expected_run_id,
            "lane": lane,
            **expected_identity,
            "reason": reason,
            "request_file_sha256": request_file_sha256,
            "claimed_at": _now(),
            "from": "outbox",
            "to": "archive",
        }
        atomic_write_json(decision_path, decision)
    if location == "terminalizing":
        if archive_path.exists():
            raise ValueError("operator terminalization archive target already exists")
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(request_path, archive_path)

    state["status"] = "failed"
    state["last_job_id"] = job_id
    state["error_type"] = "OperatorTerminalized"
    state["operator_terminalization"] = state_receipt
    state.pop("error_code", None)
    state.pop("failure_category", None)
    state.pop("transport_attempts", None)
    state.pop("result", None)
    _write_state(state_root, state)
    if decision["status"] != "terminalized":
        decision = {**decision, "status": "terminalized", "terminalized_at": _now()}
        atomic_write_json(decision_path, decision)
    return {
        **result,
        "status": "terminalized",
        "decision": state_receipt["decision"],
    }


def _write_state(queue_root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    atomic_write_json(_state_path(str(state["run_id"]), queue_root), state)


def _advance(
    queue_root: Path,
    state: dict[str, Any],
    tick: Tick,
    *,
    job_queue_root: Path | None = None,
) -> str:
    try:
        result = tick(Path(str(state["run_dir"])), job_queue_root or queue_root)
    except ExternalJobPending as pending:
        state["status"] = "active"
        state["last_job_id"] = pending.job_id
        state.pop("error_type", None)
        state.pop("error_code", None)
        state.pop("failure_category", None)
        state.pop("transport_attempts", None)
        _write_state(queue_root, state)
        return "pending"
    except ExternalJobFailed as failed:
        state["status"] = "failed"
        state["last_job_id"] = failed.job_id
        state["error_type"] = failed.error_type
        if failed.error_code is not None:
            state["error_code"] = failed.error_code
        else:
            state.pop("error_code", None)
        if failed.failure_category != "INVALID_RECEIPT":
            state["failure_category"] = failed.failure_category
        else:
            state.pop("failure_category", None)
        state["transport_attempts"] = failed.transport_attempts
        _write_state(queue_root, state)
        return "failed"
    except Exception as error:
        state["status"] = "failed"
        state["error_type"] = type(error).__name__
        state.pop("error_code", None)
        state.pop("failure_category", None)
        state.pop("transport_attempts", None)
        _write_state(queue_root, state)
        return "failed"
    state["status"] = "complete"
    state["result"] = result
    state.pop("error_type", None)
    state.pop("error_code", None)
    state.pop("failure_category", None)
    state.pop("transport_attempts", None)
    _write_state(queue_root, state)
    return "complete"


def _active_states(queue_root: Path) -> list[dict[str, Any]]:
    states = []
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("status") == "active":
            states.append(state)
    return sorted(
        states,
        key=lambda state: (
            str(state.get("updated_at") or ""),
            str(state.get("registered_at") or ""),
            str(state.get("run_id") or ""),
        ),
    )


def _known_run_ids(queue_root: Path) -> frozenset[str]:
    run_ids: set[str] = set()
    runs_root = queue_root / "runs"
    for path in sorted(runs_root.glob("*.json")) if runs_root.exists() else []:
        state = json.loads(path.read_text(encoding="utf-8"))
        run_id = state.get("run_id")
        if isinstance(run_id, str) and run_id:
            run_ids.add(run_id)
    return frozenset(run_ids)


def _failed_states(queue_root: Path) -> list[dict[str, Any]]:
    states = []
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("status") == "failed":
            states.append(state)
    return sorted(
        states,
        key=lambda state: (
            str(state.get("updated_at") or ""),
            str(state.get("registered_at") or ""),
            str(state.get("run_id") or ""),
        ),
    )


def _lane_queue_root(queue_root: Path, lane: str) -> Path:
    if lane not in CONTENT_LANES:
        raise ValueError(f"unknown content lane: {lane}")
    return queue_root / "lanes" / lane


def _lane_for_state(state: dict[str, Any], legacy_article_ids: set[str]) -> str:
    brief = _read_run_brief_from_state(state)
    if not isinstance(brief, dict):
        raise ValueError("active run brief is unavailable")
    mode = brief.get("mode")
    if mode == "create":
        return "new"
    if mode == "rewrite_existing_body":
        return "rewrite"
    if mode != "translate_existing":
        raise ValueError(f"unsupported active run mode: {mode}")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not articles or not isinstance(articles[0], dict):
        raise ValueError("translation run has no source article")
    source_article_id = str(articles[0].get("source_article_id") or "")
    return "i18n-rewrite" if source_article_id in legacy_article_ids else "i18n-new"


def _select_lane_states(
    states: list[dict[str, Any]],
    legacy_article_ids: set[str],
) -> list[dict[str, Any]]:
    """每條 lane 固定推進最早註冊的 run，直到它進入終態。"""
    selected: dict[str, dict[str, Any]] = {}
    ordered_states = sorted(
        states,
        key=lambda state: (
            str(state.get("registered_at") or ""),
            str(state.get("run_id") or ""),
        ),
    )
    for state in ordered_states:
        lane = _lane_for_state(state, legacy_article_ids)
        selected.setdefault(lane, state)
        if len(selected) == len(CONTENT_LANES):
            break
    return [selected[lane] for lane in CONTENT_LANES if lane in selected]


def _lane_summary(
    queue_root: Path,
    states: list[dict[str, Any]],
    legacy_article_ids: set[str],
) -> dict[str, dict[str, int]]:
    counts = {lane: 0 for lane in CONTENT_LANES}
    for state in states:
        counts[_lane_for_state(state, legacy_article_ids)] += 1
    return {
        lane: {
            "active": counts[lane],
            "queued": len(list((_lane_queue_root(queue_root, lane) / "outbox").glob("*.json"))),
            "processing": len(list((_lane_queue_root(queue_root, lane) / "processing").glob("*.json"))),
        }
        for lane in CONTENT_LANES
    }


def _translation_replacement_reason(
    queue_root: Path,
    state: dict[str, Any],
) -> str | None:
    run_id = str(state.get("run_id") or "")
    if (
        state.get("status") != "failed"
        or not run_id
        or run_id.endswith("-replacement-01")
        or _state_path(f"{run_id}-replacement-01", queue_root).exists()
        or _translation_replacement_decision_path(queue_root, run_id).exists()
    ):
        return None
    if state.get("error_type") == "LocalePlanValidationError":
        return "LOCALE_PLAN_VALIDATION"
    category = state.get("failure_category")
    attempts = state.get("transport_attempts")
    if (
        category in {"NETWORK", "PROVIDER_UNAVAILABLE", "SCHEMA_INVALID_PAYLOAD"}
        and attempts == OUTBOX_MAX_TRANSPORT_RETRIES + 1
    ):
        return str(category)
    return None


def seed_failed_translation_replacements(
    repo_root: Path,
    queue_root: Path,
    *,
    legacy_article_ids: set[str],
) -> dict[str, Any]:
    """每條 i18n lane 最多補一個 terminal run replacement。"""
    root = queue_root.resolve()
    busy_lanes: set[str] = set()
    for state in _active_states(root):
        if not state.get("replacement_of"):
            continue
        try:
            lane = _lane_for_state(state, legacy_article_ids)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if lane in {"i18n-new", "i18n-rewrite"}:
            busy_lanes.add(lane)

    selected: dict[str, tuple[dict[str, Any], str]] = {}
    for state in _failed_states(root):
        reason = _translation_replacement_reason(root, state)
        if reason is None:
            continue
        try:
            lane = _lane_for_state(state, legacy_article_ids)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if (
            lane not in {"i18n-new", "i18n-rewrite"}
            or lane in busy_lanes
            or lane in selected
        ):
            continue
        selected[lane] = (state, reason)

    created_run_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for lane in ("i18n-new", "i18n-rewrite"):
        selected_item = selected.get(lane)
        if selected_item is None:
            continue
        state, reason = selected_item
        try:
            replacement = multilingual.enqueue_translation_replacement(
                repo_root,
                root,
                terminal_state=state,
                recovery_reason=reason,
            )
        except ValueError as error:
            closed_reason = (
                "SOURCE_DRIFT"
                if str(error) == "translation replacement source drift"
                else "INVALID_TERMINAL_STATE"
            )
            atomic_write_json(
                _translation_replacement_decision_path(root, str(state["run_id"])),
                {
                    "schema_version": 1,
                    "run_id": str(state["run_id"]),
                    "status": "skipped",
                    "reason": closed_reason,
                    "recorded_at": _now(),
                },
            )
            skipped.append({"run_id": str(state["run_id"]), "reason": closed_reason})
            continue
        created_run_ids.append(replacement["run_id"])
    summary: dict[str, Any] = {
        "status": "seeded" if created_run_ids else "idle",
        "created": len(created_run_ids),
        "created_run_ids": created_run_ids,
    }
    if skipped:
        summary["skipped"] = skipped
    return summary


def _migrate_pending_jobs(
    queue_root: Path,
    states: list[dict[str, Any]],
    legacy_article_ids: set[str],
) -> dict[str, int]:
    """把舊 shared outbox 的 pending job 原子搬到對應 lane。"""
    lane_by_namespace = {
        hashlib.sha256(str(state["run_id"]).encode("utf-8")).hexdigest()[:24]: _lane_for_state(
            state,
            legacy_article_ids,
        )
        for state in states
    }
    moved = {lane: 0 for lane in CONTENT_LANES}
    outbox = queue_root / "outbox"
    for source in sorted(outbox.glob("*.json")) if outbox.exists() else []:
        try:
            request = json.loads(source.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        namespace = re.sub(r"-r[0-9]+$", "", str(request.get("namespace") or ""))
        lane = lane_by_namespace.get(namespace)
        if lane is None:
            continue
        target = _lane_queue_root(queue_root, lane) / "outbox" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError(f"lane job collision: {source.name}")
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue
        moved[lane] += 1
    return moved


def _read_run_brief_from_state(state: dict[str, Any]) -> dict[str, Any] | None:
    run_dir = Path(str(state.get("run_dir") or ""))
    path = run_dir / "brief.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _article_ids_from_brief(brief: dict[str, Any] | None) -> set[str]:
    if not isinstance(brief, dict) or brief.get("mode") != "rewrite_existing_body":
        return set()
    articles = brief.get("articles")
    if not isinstance(articles, list):
        return set()
    return {str(article.get("article_id") or "") for article in articles if isinstance(article, dict) and article.get("article_id")}


def _create_article_ids_from_brief(brief: dict[str, Any] | None) -> set[str]:
    if not isinstance(brief, dict) or brief.get("mode") != "create":
        return set()
    articles = brief.get("articles")
    if not isinstance(articles, list):
        return set()
    article_ids: set[str] = set()
    for article in articles:
        if not isinstance(article, dict):
            continue
        target = article.get("target")
        if isinstance(target, dict) and target.get("id"):
            article_ids.add(str(target["id"]))
            continue
        if article.get("id"):
            article_ids.add(str(article["id"]))
    return article_ids


def _registered_article_ids_by_mode(queue_root: Path, mode: str) -> set[str]:
    article_ids: set[str] = set()
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        brief = _read_run_brief_from_state(state)
        if mode == "create":
            article_ids.update(_create_article_ids_from_brief(brief))
        elif mode == "rewrite_existing_body":
            article_ids.update(_article_ids_from_brief(brief))
    return article_ids


def _active_count_by_mode(queue_root: Path, mode: str) -> int:
    count = 0
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if state.get("status") != "active":
            continue
        brief = _read_run_brief_from_state(state)
        if isinstance(brief, dict) and brief.get("mode") == mode:
            count += 1
    return count


def _campaign_version_from_brief(brief: dict[str, Any] | None) -> str | None:
    if not isinstance(brief, dict):
        return None
    value = brief.get("campaign_version")
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or "\n" in normalized or "\r" in normalized:
        return None
    return normalized


def _registered_rewrite_article_ids_for_campaign(queue_root: Path, campaign_version: str) -> set[str]:
    article_ids: set[str] = set()
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        brief = _read_run_brief_from_state(state)
        if _campaign_version_from_brief(brief) == campaign_version:
            article_ids.update(_article_ids_from_brief(brief))
    return article_ids


def _registered_rewrite_article_ids(queue_root: Path) -> set[str]:
    return _registered_article_ids_by_mode(queue_root, "rewrite_existing_body")


def _campaign_work_id(
    source_kind: str,
    article_id: str,
    locale: str,
    campaign_version: str,
) -> str:
    """回傳可重跑的 campaign work identity，不配置或寫入任何 runtime state。"""
    if source_kind not in {"matrix", "legacy"}:
        raise ValueError("campaign source kind is invalid")
    if not article_id or not locale or not campaign_version:
        raise ValueError("campaign identity fields must be non-empty")
    canonical = json.dumps(
        {
            "article_id": article_id,
            "campaign_version": campaign_version,
            "locale": locale,
            "source_kind": source_kind,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"apf-work-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]}"


def _translation_identities_in_queue(queue_root: Path, campaign_version: str) -> set[tuple[str, str]]:
    identities: set[tuple[str, str]] = set()
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        state = json.loads(path.read_text(encoding="utf-8"))
        brief = _read_run_brief_from_state(state)
        if (
            not isinstance(brief, dict)
            or brief.get("mode") != "translate_existing"
            or _campaign_version_from_brief(brief) != campaign_version
        ):
            continue
        articles = brief.get("articles")
        if not isinstance(articles, list):
            continue
        for article in articles:
            if not isinstance(article, dict):
                continue
            article_id = str(article.get("source_article_id") or "")
            locale = str(article.get("locale") or "")
            if article_id and locale:
                identities.add((article_id, locale))
    return identities


def build_campaign_dry_run_workset(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    campaign_version: str,
    locales: Iterable[str] = ("en", "ja", "ko"),
) -> dict[str, Any]:
    """讀取既有來源與狀態，回傳四 lane 的純 dry-run campaign workset。"""
    if not isinstance(campaign_version, str):
        raise ValueError("campaign version and locales must be valid")
    campaign_version = campaign_version.strip()
    selected_locales = tuple(sorted(set(locales)))
    if (
        not campaign_version.strip()
        or "\n" in campaign_version
        or "\r" in campaign_version
        or not selected_locales
        or any(locale not in multilingual.SUPPORTED_LOCALES for locale in selected_locales)
    ):
        raise ValueError("campaign version and locales must be valid")
    root = queue_root.resolve()
    registered_new = _registered_article_ids_by_mode(root, "create")
    registered_rewrite = _registered_rewrite_article_ids_for_campaign(root, campaign_version)
    queued_translations = _translation_identities_in_queue(root, campaign_version)
    matrix_rows = sorted(
        pipeline.build_matrix_backlog(repo_root),
        key=lambda row: str(row.get("id") or ""),
    )
    legacy_records = publisher.legacy_article_records(repo_root)
    legacy_inventory = pipeline._existing_rewrite_inventory(repo_root)
    legacy_ids = {str(record.get("id") or "") for record in legacy_records}
    rewrite_backlog = publisher.summarize_legacy_rewrite_backlog(
        root,
        state_root.resolve(),
        allowed_article_ids=legacy_ids,
        legacy_records=legacy_records,
    )

    items: list[dict[str, str]] = []
    source_candidates: list[tuple[str, str, str]] = []
    excluded_new = 0
    for row in matrix_rows:
        article_id = str(row.get("id") or "")
        if not article_id or article_id in registered_new:
            excluded_new += 1
            continue
        source_candidates.append(("matrix", article_id, "new"))
        items.append(
            {
                "source_kind": "matrix",
                "article_id": article_id,
                "locale": "zh-TW",
                "campaign_version": campaign_version,
                "work_id": _campaign_work_id("matrix", article_id, "zh-TW", campaign_version),
                "lane": "new",
                "reason": "matrix_backlog_unpublished_and_unregistered",
            }
        )

    excluded_rewrite = 0
    for record in legacy_records:
        article_id = str(record.get("id") or "")
        if not article_id or article_id in registered_rewrite or article_id not in legacy_inventory:
            excluded_rewrite += 1
            continue
        source_candidates.append(("legacy", article_id, "rewrite"))
        items.append(
            {
                "source_kind": "legacy",
                "article_id": article_id,
                "locale": "zh-TW",
                "campaign_version": campaign_version,
                "work_id": _campaign_work_id("legacy", article_id, "zh-TW", campaign_version),
                "lane": "rewrite",
                "reason": "legacy_inventory_unregistered",
            }
        )

    excluded_i18n = 0
    for source_kind, article_id, source_lane in source_candidates:
        lane = "i18n-new" if source_lane == "new" else "i18n-rewrite"
        for locale in selected_locales:
            if (article_id, locale) in queued_translations:
                excluded_i18n += 1
                continue
            items.append(
                {
                    "source_kind": source_kind,
                    "article_id": article_id,
                    "locale": locale,
                    "campaign_version": campaign_version,
                    "work_id": _campaign_work_id(source_kind, article_id, locale, campaign_version),
                    "lane": lane,
                    "reason": "derived_from_source_publication_candidate",
                }
            )

    lane_order = {lane: index for index, lane in enumerate(CONTENT_LANES)}
    items.sort(key=lambda item: (lane_order[item["lane"]], item["source_kind"], item["article_id"], item["locale"], item["work_id"]))
    work_ids = [item["work_id"] for item in items]
    if len(work_ids) != len(set(work_ids)):
        raise ValueError("campaign work identities must be unique")
    return {
        "schema_version": 1,
        "campaign_version": campaign_version,
        "lanes": list(CONTENT_LANES),
        "items": items,
        "summary": {
            "counts": {lane: sum(item["lane"] == lane for item in items) for lane in CONTENT_LANES},
            "excluded": {
                "new_registered": excluded_new,
                "rewrite_registered_or_unavailable": excluded_rewrite,
                "i18n_existing_queue": excluded_i18n,
            },
            "rewrite_backlog": {
                key: rewrite_backlog.get(key, 0)
                for key in ("released", "active_or_incomplete", "unattempted")
            },
        },
    }


def _campaign_editorial_work_item(work_item: object) -> dict[str, str]:
    """驗證 APF workset 的可執行新文／重寫 item，不自行補值。"""
    required = {
        "source_kind", "article_id", "locale", "campaign_version", "work_id", "lane", "reason",
    }
    if not isinstance(work_item, dict) or set(work_item) != required:
        raise ValueError("campaign work item schema is invalid")
    item = {key: value for key, value in work_item.items() if isinstance(value, str)}
    if len(item) != len(required) or any(not value.strip() for value in item.values()):
        raise ValueError("campaign work item fields must be non-empty strings")
    expected_lane = {"matrix": "new", "legacy": "rewrite"}.get(item["source_kind"])
    if expected_lane != item["lane"] or item["locale"] != "zh-TW":
        raise ValueError("campaign work item is not a supported editorial lane")
    if item["work_id"] != _campaign_work_id(
        item["source_kind"], item["article_id"], item["locale"], item["campaign_version"]
    ):
        raise ValueError("campaign work identity differs from source contract")
    return item


def _editorial_candidate_id(candidate: dict[str, Any]) -> str:
    articles = candidate.get("articles")
    if not isinstance(articles, list) or len(articles) != 1 or not isinstance(articles[0], dict):
        raise ValueError("legacy candidate must contain exactly one article")
    value = articles[0].get("id", articles[0].get("article_id"))
    if not isinstance(value, str) or not value:
        raise ValueError("legacy candidate article identity is invalid")
    return value


def _read_editorial_artifact(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"editorial artifact is unreadable: {path.name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"editorial artifact is invalid: {path.name}")
    return value


def execute_campaign_editorial_work_item(
    work_item: object,
    run_dir: Path,
    *,
    brief_factory: EditorialFactory,
    writer: EditorialWriter,
    reviewer: EditorialReviewer,
) -> dict[str, Any]:
    """把單一 APF work item 推進至既有 Publisher 相容、無 side effect 的邊界。"""
    item = _campaign_editorial_work_item(work_item)
    root = run_dir / "editorial-vnext"
    root.mkdir(parents=True, exist_ok=True)
    brief_path = root / "article-brief-v2.json"
    candidate_path = root / "legacy-candidate.json"
    review_path = root / "legacy-review.json"
    manifest_path = root / "editorial-manifest-v1.json"

    if brief_path.exists():
        brief = editorial_contracts.validate_article_brief(_read_editorial_artifact(brief_path))
    else:
        brief = editorial_contracts.validate_article_brief(brief_factory(dict(item)))
        atomic_write_json(brief_path, brief)
    identity = brief.get("article_identity")
    if not isinstance(identity, dict) or identity.get("id") != item["article_id"]:
        raise ValueError("article brief identity differs from campaign work item")

    expected_mode = "create" if item["lane"] == "new" else "rewrite_existing_body"
    if candidate_path.exists():
        candidate = _read_editorial_artifact(candidate_path)
    else:
        candidate = writer(brief)
    pipeline.validate_candidate(candidate)
    if candidate.get("run_id") != brief["run_id"] or candidate.get("mode") != expected_mode:
        raise ValueError("legacy candidate run identity or mode differs from article brief")
    if _editorial_candidate_id(candidate) != item["article_id"]:
        raise ValueError("legacy candidate identity differs from campaign work item")
    if not candidate_path.exists():
        atomic_write_json(candidate_path, candidate)

    if review_path.exists():
        review = _read_editorial_artifact(review_path)
    else:
        review = reviewer(brief, candidate)
    pipeline.validate_review(review, candidate["articles"])
    if review.get("run_id") != brief["run_id"]:
        raise ValueError("legacy review run identity differs from article brief")
    if any(
        item.get("verdict") != "APPROVE" or item.get("hard_failure") is True or item.get("findings")
        for item in review["articles"]
    ):
        raise ValueError("reviewer reported blocking findings")
    if not review_path.exists():
        atomic_write_json(review_path, review)

    manifest = {
        "version": "EditorialManifestV1",
        "orchestration_mode": editorial_contracts.MANIFEST_ORCHESTRATION_MODE,
        "run_id": brief["run_id"],
        "article_identity": identity,
        "brief_sha256": editorial_contracts.artifact_sha256(brief),
        "selected_stages": [],
        "artifacts": {"brief": brief, "campaign_work": item, "legacy_review": review},
        "artifact_sha256": {
            "brief": editorial_contracts.artifact_sha256(brief),
            "campaign_work": editorial_contracts.artifact_sha256(item),
            "legacy_review": editorial_contracts.artifact_sha256(review),
        },
        "final_candidate_sha256": editorial_contracts.artifact_sha256(candidate),
        "legacy_candidate": candidate,
        "legacy_candidate_sha256": editorial_contracts.artifact_sha256(candidate),
    }
    report = editorial_contracts.validate_manifest(manifest)
    if report["blocking"]:
        raise ValueError("editorial manifest is blocked: " + editorial_contracts.stable_json_summary(report))
    atomic_write_json(manifest_path, manifest)
    return {
        "work_id": item["work_id"],
        "lane": item["lane"],
        "run_id": brief["run_id"],
        "run_dir": str(run_dir.resolve()),
        "article_identity": identity,
        "candidate": candidate,
        "review": review,
        "manifest": manifest,
        "candidate_sha256": editorial_contracts.artifact_sha256(candidate),
        "review_sha256": editorial_contracts.artifact_sha256(review),
    }


def execute_campaign_editorial_workset(
    workset: object,
    run_root: Path,
    *,
    brief_factory: EditorialFactory,
    writer: EditorialWriter,
    reviewer: EditorialReviewer,
    max_items: int = 2,
) -> dict[str, Any]:
    """一次 bounded 執行 APF workset 的 new 與 rewrite，拒絕不完整輸入。"""
    if (
        not isinstance(workset, dict)
        or set(workset) != {"schema_version", "campaign_version", "lanes", "items", "summary"}
        or workset.get("schema_version") != 1
        or not isinstance(workset.get("items"), list)
        or type(max_items) is not int
        or max_items != 2
    ):
        raise ValueError("campaign editorial workset is invalid")
    selected: dict[str, dict[str, str]] = {}
    for raw_item in workset["items"]:
        item = _campaign_editorial_work_item(raw_item)
        if item["lane"] not in {"new", "rewrite"}:
            continue
        if item["lane"] in selected:
            continue
        selected[item["lane"]] = item
    if set(selected) != {"new", "rewrite"}:
        raise ValueError("campaign editorial workset must contain one new and one rewrite item")
    results = [
        execute_campaign_editorial_work_item(
            selected[lane],
            run_root / selected[lane]["work_id"],
            brief_factory=brief_factory,
            writer=writer,
            reviewer=reviewer,
        )
        for lane in ("new", "rewrite")
    ]
    return {
        "campaign_version": workset["campaign_version"],
        "work_ids": [result["work_id"] for result in results],
        "runs": results,
    }


def _preflight_campaign_editorial_handoffs(
    campaign_result: object,
    *,
    rewrite_briefs: Mapping[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """完整驗證 APF 雙 lane handoff，不配置或寫入 runtime state。"""
    if not isinstance(campaign_result, dict) or not isinstance(campaign_result.get("runs"), list):
        raise ValueError("campaign editorial result is invalid")
    prepared: list[dict[str, Any]] = []
    by_lane: dict[str, dict[str, Any]] = {}
    for result in campaign_result["runs"]:
        if not isinstance(result, dict):
            raise ValueError("campaign editorial run is invalid")
        lane = result.get("lane")
        if lane not in {"new", "rewrite"} or lane in by_lane:
            raise ValueError("campaign editorial lanes must be unique new and rewrite")
        candidate = result.get("candidate")
        review = result.get("review")
        manifest = result.get("manifest")
        identity = result.get("article_identity")
        run_id = result.get("run_id")
        work_id = result.get("work_id")
        run_dir = result.get("run_dir")
        if not all(isinstance(value, str) and value for value in (run_id, work_id, run_dir)):
            raise ValueError("campaign editorial handoff identity is invalid")
        if not isinstance(candidate, dict) or not isinstance(review, dict) or not isinstance(manifest, dict):
            raise ValueError("campaign editorial handoff artifacts are invalid")
        report = editorial_contracts.validate_manifest(manifest)
        if report["blocking"]:
            raise ValueError("campaign editorial manifest is blocked: " + editorial_contracts.stable_json_summary(report))
        if (
            result.get("candidate_sha256") != editorial_contracts.artifact_sha256(candidate)
            or manifest.get("legacy_candidate") != candidate
            or manifest.get("legacy_candidate_sha256") != editorial_contracts.artifact_sha256(candidate)
        ):
            raise ValueError("campaign candidate SHA drift")
        legacy_review = manifest.get("artifacts", {}).get("legacy_review") if isinstance(manifest.get("artifacts"), dict) else None
        if result.get("review_sha256") != editorial_contracts.artifact_sha256(review) or legacy_review != review:
            raise ValueError("campaign review SHA drift")
        pipeline.validate_candidate(candidate)
        pipeline.validate_review(review, candidate["articles"])
        article = candidate["articles"][0]
        article_id = str(article.get("id") or article.get("article_id") or "")
        if not isinstance(identity, dict) or identity.get("id") != article_id:
            raise ValueError("campaign article identity drift")
        artifacts = manifest.get("artifacts")
        campaign_work = artifacts.get("campaign_work") if isinstance(artifacts, dict) else None
        try:
            manifest_work = _campaign_editorial_work_item(campaign_work)
        except ValueError as error:
            raise ValueError("campaign work identity drift") from error
        if (
            manifest_work["work_id"] != work_id
            or manifest_work["lane"] != lane
            or manifest_work["article_id"] != article_id
        ):
            raise ValueError("campaign work identity drift")
        expected_mode = "create" if lane == "new" else "rewrite_existing_body"
        if candidate.get("run_id") != run_id or candidate.get("mode") != expected_mode:
            raise ValueError("campaign candidate run identity drift")
        if lane == "rewrite":
            brief = rewrite_briefs.get(run_id)
            if not isinstance(brief, dict):
                raise ValueError("rewrite publisher brief is required")
            pipeline.validate_rewrite_brief(brief)
            if brief.get("run_id") != run_id or brief["articles"][0].get("article_id") != article_id:
                raise ValueError("rewrite publisher brief identity drift")
        else:
            brief = {"schema_version": 1, "run_id": run_id, "mode": "create", "articles": []}
        prepared.append(
            {
                "lane": lane,
                "run_id": run_id,
                "work_id": work_id,
                "article_id": article_id,
                "run_dir": run_dir,
                "brief": brief,
                "candidate": candidate,
                "review": review,
                "candidate_sha256": result["candidate_sha256"],
                "review_sha256": result["review_sha256"],
            }
        )
        by_lane[lane] = {"run_id": run_id, "article_id": article_id}
    if set(by_lane) != {"new", "rewrite"}:
        raise ValueError("campaign editorial result must contain new and rewrite")
    return prepared, by_lane


def replay_campaign_editorial_workset_through_publisher(
    campaign_result: object,
    queue_root: Path,
    state_root: Path,
    *,
    rewrite_briefs: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    """把已驗證 APF 結果重放至既有 Publisher collector，不發布。"""
    prepared, by_lane = _preflight_campaign_editorial_handoffs(
        campaign_result,
        rewrite_briefs=rewrite_briefs,
    )
    for item in prepared:
        handoff_dir = Path(str(item["run_dir"])) / "publisher-dry-run"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(handoff_dir / "brief.json", item["brief"])
        atomic_write_json(handoff_dir / "candidate.json", item["candidate"])
        atomic_write_json(handoff_dir / "review.json", item["review"])
        atomic_write_json(
            _state_path(str(item["run_id"]), queue_root.resolve()),
            {
                "schema_version": 1,
                "run_id": item["run_id"],
                "run_dir": str(handoff_dir.resolve()),
                "status": "complete",
                "result": {
                    "status": "complete",
                    "run_id": item["run_id"],
                    "candidate": str((handoff_dir / "candidate.json").resolve()),
                    "campaign_work_id": item["work_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "review_sha256": item["review_sha256"],
                },
            },
        )
    new_ready = publisher.collect_ready_runs(
        queue_root,
        state_root,
        exact_run_ids=[by_lane["new"]["run_id"]],
    )
    rewrite_ready = publisher.collect_ready_rewrite_runs(
        queue_root,
        state_root,
        allowed_article_ids={by_lane["rewrite"]["article_id"]},
        exact_run_ids=[by_lane["rewrite"]["run_id"]],
    )
    if [state["run_id"] for state, _candidate, _review in new_ready] != [by_lane["new"]["run_id"]]:
        raise ValueError("publisher rejected campaign new handoff")
    if [state["run_id"] for state, _candidate, _review, _brief in rewrite_ready] != [by_lane["rewrite"]["run_id"]]:
        raise ValueError("publisher rejected campaign rewrite handoff")
    return {
        "status": "dry-run",
        "published": 0,
        "new_run_id": by_lane["new"]["run_id"],
        "rewrite_run_id": by_lane["rewrite"]["run_id"],
    }


def _campaign_translation_source(item: Mapping[str, Any]) -> dict[str, Any]:
    """把已驗證 Publisher handoff 正規化為 multilingual source contract。"""
    article = item["candidate"]["articles"][0]
    if item["lane"] == "new":
        metadata = article
    else:
        metadata = item["brief"]["articles"][0]["immutable_fields"]
    policy = article.get("publicationPolicy")
    canonical = policy.get("canonical") if isinstance(policy, dict) else None
    path = urlsplit(str(canonical or "")).path
    source = {
        "article_id": item["article_id"],
        "canonical_path": path,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "answer": metadata.get("answer"),
        "tags": metadata.get("tags"),
        "faq": metadata.get("faq"),
        "bodySections": article.get("bodySections"),
    }
    return multilingual._validate_source(source)


def _campaign_translation_brief(
    item: Mapping[str, Any],
    source: dict[str, Any],
    locale: str,
) -> dict[str, Any]:
    run_id = multilingual.translation_run_id(
        str(item["run_id"]),
        str(item["article_id"]),
        locale,
    )
    brief = {
        "schema_version": multilingual.SCHEMA_VERSION,
        "run_id": run_id,
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"{item['article_id']}:{locale}",
                "locale": locale,
                "source_article_id": item["article_id"],
                "source_path": source["canonical_path"],
                "source_sha256": multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }
    multilingual.validate_translation_brief(brief)
    return brief


def _preflight_translation_registration(
    queue_root: Path,
    brief: dict[str, Any],
) -> tuple[dict[str, Any] | None, Path]:
    run_id = str(brief["run_id"])
    run_dir = (queue_root / "translation-runs" / run_id).resolve()
    state_path = _state_path(run_id, queue_root)
    if state_path.exists() != run_dir.exists():
        raise ValueError("translation registration is incomplete")
    if not state_path.exists():
        return None, run_dir
    state = _read_editorial_artifact(state_path)
    if (
        state.get("run_id") != run_id
        or state.get("run_dir") != str(run_dir)
        or state.get("status") not in {"active", "complete"}
    ):
        raise ValueError("translation run identity collision")
    existing_brief = _read_editorial_artifact(run_dir / "brief.json")
    multilingual.validate_translation_brief(existing_brief)
    if existing_brief != brief:
        raise ValueError("registered translation run source, locale, or identity drift")
    if state["status"] == "complete":
        candidate = _read_editorial_artifact(run_dir / "candidate.json")
        review = _read_editorial_artifact(run_dir / "review.json")
        multilingual.validate_translation_candidate(brief, candidate)
        pipeline.validate_review(review, candidate["articles"])
        result = state.get("result")
        if (
            not isinstance(result, dict)
            or result.get("candidate_sha256")
            != editorial_contracts.artifact_sha256(candidate)
            or result.get("review_sha256")
            != editorial_contracts.artifact_sha256(review)
        ):
            raise ValueError("registered translation candidate or review SHA drift")
    return state, run_dir


def _validate_staged_translation(
    brief: dict[str, Any],
    candidate: dict[str, Any],
    review: dict[str, Any],
) -> tuple[str, str]:
    multilingual.validate_translation_brief(brief)
    multilingual.validate_translation_candidate(brief, candidate)
    pipeline.validate_review(review, candidate["articles"])
    if review.get("run_id") != brief["run_id"]:
        raise ValueError("translation review identity drift")
    if any(
        item.get("verdict") != "APPROVE"
        or item.get("hard_failure") is True
        or item.get("findings")
        for item in review["articles"]
    ):
        raise ValueError("translation reviewer reported blocking findings")
    findings = multilingual.translation_findings(brief, candidate["articles"])
    if findings:
        raise ValueError("translation deterministic validation failed")
    return (
        editorial_contracts.artifact_sha256(candidate),
        editorial_contracts.artifact_sha256(review),
    )


@contextmanager
def _campaign_translation_source_snapshot(
    sources: Mapping[str, dict[str, Any]],
) -> Iterator[None]:
    """讓既有 Publisher collector 對 APF 尚未發布的 source snapshot 驗證。"""
    original = multilingual.load_source_article

    def load_snapshot(_repo_root: Path, article_id: str) -> dict[str, Any]:
        source = sources.get(article_id)
        if source is None:
            raise ValueError("campaign translation source is not registered")
        return source

    multilingual.load_source_article = load_snapshot
    try:
        yield
    finally:
        multilingual.load_source_article = original


def replay_campaign_editorial_workset_through_translation(
    repo_root: Path,
    campaign_result: object,
    queue_root: Path,
    state_root: Path,
    client: pipeline.GeminiClient,
    *,
    rewrite_briefs: Mapping[str, dict[str, Any]],
    locale: str = "ja",
    max_repairs: int = 2,
) -> dict[str, Any]:
    """把 APF new／rewrite 原子送入單一 locale translation dry-run。"""
    if locale not in multilingual.SUPPORTED_LOCALES:
        raise ValueError("campaign translation locale is unsupported")
    prepared, _by_lane = _preflight_campaign_editorial_handoffs(
        campaign_result,
        rewrite_briefs=rewrite_briefs,
    )
    sources = {
        str(item["article_id"]): _campaign_translation_source(item)
        for item in prepared
    }
    plans = []
    for item in prepared:
        source = sources[str(item["article_id"])]
        brief = _campaign_translation_brief(item, source, locale)
        state, run_dir = _preflight_translation_registration(queue_root, brief)
        plans.append(
            {
                "item": item,
                "brief": brief,
                "state": state,
                "run_dir": run_dir,
                "lane": "i18n-new" if item["lane"] == "new" else "i18n-rewrite",
            }
        )
    if {plan["lane"] for plan in plans} != {"i18n-new", "i18n-rewrite"}:
        raise ValueError("campaign translation must contain new and rewrite lanes")

    with tempfile.TemporaryDirectory(prefix="pantheon-apf-003-") as temporary:
        staging_root = Path(temporary)
        for plan in plans:
            staged_dir = staging_root / str(plan["brief"]["run_id"])
            if plan["state"] is None:
                atomic_write_json(staged_dir / "brief.json", plan["brief"])
            else:
                shutil.copytree(plan["run_dir"], staged_dir)
            if plan["state"] is not None and plan["state"]["status"] == "complete":
                candidate = _read_editorial_artifact(staged_dir / "candidate.json")
                review = _read_editorial_artifact(staged_dir / "review.json")
            else:
                candidate, review = multilingual.run_writer_reviewer(
                    staged_dir,
                    client,
                    max_repairs=max_repairs,
                )
            candidate_sha, review_sha = _validate_staged_translation(
                plan["brief"],
                candidate,
                review,
            )
            plan.update(
                {
                    "staged_dir": staged_dir,
                    "candidate_sha256": candidate_sha,
                    "review_sha256": review_sha,
                }
            )

        source_loader = lambda _root, article_id: sources[article_id]
        for plan in plans:
            item = plan["item"]
            records = multilingual.enqueue_article_translations(
                repo_root,
                queue_root,
                source_run_id=str(item["run_id"]),
                article_id=str(item["article_id"]),
                locales=[locale],
                source_loader=source_loader,
            )
            if [record["run_id"] for record in records] != [plan["brief"]["run_id"]]:
                raise ValueError("translation enqueue identity drift")
            if plan["state"] is not None and plan["state"]["status"] == "complete":
                continue
            shutil.copytree(plan["staged_dir"], plan["run_dir"], dirs_exist_ok=True)
            state = _read_editorial_artifact(_state_path(plan["brief"]["run_id"], queue_root))
            state.update(
                {
                    "status": "complete",
                    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "result": {
                        "status": "complete",
                        "run_id": plan["brief"]["run_id"],
                        "candidate": str((plan["run_dir"] / "candidate.json").resolve()),
                        "candidate_sha256": plan["candidate_sha256"],
                        "review_sha256": plan["review_sha256"],
                        "source_run_id": item["run_id"],
                        "source_article_id": item["article_id"],
                        "locale": locale,
                        "lane": plan["lane"],
                    },
                }
            )
            atomic_write_json(_state_path(plan["brief"]["run_id"], queue_root), state)

    run_ids = [str(plan["brief"]["run_id"]) for plan in plans]
    with _campaign_translation_source_snapshot(sources):
        ready = publisher.collect_ready_translation_runs(
            repo_root,
            queue_root,
            state_root,
            exact_run_ids=run_ids,
        )
    ready_by_id = {str(state["run_id"]): (brief, candidate, review) for state, brief, candidate, review in ready}
    if set(ready_by_id) != set(run_ids):
        raise ValueError("publisher rejected campaign translation handoff")
    return {
        "status": "dry-run",
        "published": 0,
        "locale": locale,
        "translation_runs": [
            {
                "lane": plan["lane"],
                "source_run_id": plan["item"]["run_id"],
                "source_article_id": plan["item"]["article_id"],
                "source_sha256": plan["brief"]["articles"][0]["source_sha256"],
                "translation_run_id": plan["brief"]["run_id"],
                "translation_article_id": plan["brief"]["articles"][0]["translation_id"],
                "translation_sha256": plan["candidate_sha256"],
                "review_sha256": plan["review_sha256"],
            }
            for plan in plans
        ],
    }


def _private_campaign_e2e_workset(workset: object, locale: str) -> dict[str, Any]:
    """驗證 CHECKPOINT-A 固定四 lane 私有 workset，先拒絕超量。"""
    if (
        not isinstance(workset, dict)
        or set(workset) != {"schema_version", "campaign_version", "lanes", "items", "summary"}
        or workset.get("schema_version") != 1
        or not isinstance(workset.get("items"), list)
        or workset.get("lanes") != list(CONTENT_LANES)
        or locale != "ja"
    ):
        raise ValueError("private campaign workset is invalid")
    items = workset["items"]
    editorial_count = sum(
        isinstance(item, dict) and item.get("lane") in {"new", "rewrite"}
        for item in items
    )
    translation_count = sum(
        isinstance(item, dict) and item.get("lane") in {"i18n-new", "i18n-rewrite"}
        for item in items
    )
    if editorial_count > 2:
        raise ValueError("private campaign capacity exceeds two editorial work items")
    if translation_count > 2:
        raise ValueError("private campaign capacity exceeds two translation work items")
    if len(items) != 4:
        raise ValueError("private campaign capacity requires exactly four work items")

    by_lane: dict[str, dict[str, str]] = {}
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise ValueError("private campaign work item is invalid")
        lane = raw_item.get("lane")
        if lane in {"new", "rewrite"}:
            item = _campaign_editorial_work_item(raw_item)
        elif lane in {"i18n-new", "i18n-rewrite"}:
            expected_source = "matrix" if lane == "i18n-new" else "legacy"
            expected_id = _campaign_work_id(
                expected_source,
                str(raw_item.get("article_id") or ""),
                locale,
                str(workset["campaign_version"]),
            )
            item = {key: value for key, value in raw_item.items() if isinstance(value, str)}
            if (
                len(item) != 7
                or set(item) != {"source_kind", "article_id", "locale", "campaign_version", "work_id", "lane", "reason"}
                or any(not value.strip() for value in item.values())
                or item["source_kind"] != expected_source
                or item["locale"] != locale
                or item["campaign_version"] != workset["campaign_version"]
                or item["work_id"] != expected_id
            ):
                raise ValueError("private campaign translation work item is invalid")
        else:
            raise ValueError("private campaign lane is invalid")
        if lane in by_lane:
            raise ValueError("private campaign lane is duplicated")
        by_lane[str(lane)] = item
    if set(by_lane) != set(CONTENT_LANES):
        raise ValueError("private campaign must contain four lanes")
    for editorial_lane, translation_lane in (("new", "i18n-new"), ("rewrite", "i18n-rewrite")):
        editorial = by_lane[editorial_lane]
        translation = by_lane[translation_lane]
        if editorial["article_id"] != translation["article_id"]:
            raise ValueError("private campaign translation source identity drift")
    return {
        "schema_version": 1,
        "campaign_version": workset["campaign_version"],
        "lanes": ["new", "rewrite"],
        "items": [by_lane["new"], by_lane["rewrite"]],
        "summary": workset["summary"],
    }


def _select_private_campaign_e2e_workset(workset: object, locale: str) -> dict[str, Any]:
    """從 APF-001 完整 workset 穩定挑選 CHECKPOINT-A 的四個 lane。"""
    if not isinstance(workset, dict) or not isinstance(workset.get("items"), list):
        raise ValueError("private campaign source workset is invalid")
    selected: dict[str, dict[str, Any]] = {}
    for lane in ("new", "rewrite"):
        candidates = [
            item
            for item in workset["items"]
            if isinstance(item, dict) and item.get("lane") == lane
        ]
        if not candidates:
            raise ValueError("private campaign source workset is missing editorial lane")
        selected[lane] = candidates[0]
        translation_lane = f"i18n-{lane}"
        translations = [
            item
            for item in workset["items"]
            if (
                isinstance(item, dict)
                and item.get("lane") == translation_lane
                and item.get("locale") == locale
                and item.get("article_id") == selected[lane].get("article_id")
            )
        ]
        if len(translations) != 1:
            raise ValueError("private campaign source workset has invalid translation selection")
        selected[translation_lane] = translations[0]
    return _private_campaign_e2e_workset(
        {**workset, "items": [selected[lane] for lane in CONTENT_LANES]},
        locale,
    )


def _rebase_private_campaign_state_paths(
    queue_root: Path,
    replacements: Iterable[tuple[Path, Path]],
) -> None:
    """只在私有 staging 與 receipt 間搬移時更新既有 run_dir 路徑。"""
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        state = _read_editorial_artifact(path)
        changed = False
        for container, key in ((state, "run_dir"), (state.get("result"), "candidate")):
            if not isinstance(container, dict) or not isinstance(container.get(key), str):
                continue
            value = container[key]
            for source, target in replacements:
                source_text = str(source.resolve())
                if value == source_text or value.startswith(source_text + os.sep):
                    container[key] = str(target.resolve()) + value[len(source_text):]
                    changed = True
                    break
        if changed:
            atomic_write_json(path, state)


def execute_private_campaign_e2e(
    repo_root: Path,
    run_root: Path,
    queue_root: Path,
    state_root: Path,
    client: pipeline.GeminiClient,
    *,
    campaign_version: str,
    brief_factory: EditorialFactory,
    writer: EditorialWriter,
    reviewer: EditorialReviewer,
    rewrite_brief_factory: Callable[[dict[str, Any]], dict[str, Any]],
    locale: str = "ja",
    max_repairs: int = 0,
) -> dict[str, Any]:
    """在可丟棄 staging 內串接四 lane，全部驗證後才保留私有 receipt。"""
    workset = build_campaign_dry_run_workset(
        repo_root,
        queue_root,
        state_root,
        campaign_version=campaign_version,
        locales=(locale,),
    )
    editorial_workset = _select_private_campaign_e2e_workset(workset, locale)
    with tempfile.TemporaryDirectory(prefix="pantheon-checkpoint-a-") as temporary:
        staging = Path(temporary)
        staged_runs = staging / "runs"
        staged_queue = staging / "queue"
        staged_state = staging / "publisher-state"
        for source, target in ((run_root, staged_runs), (queue_root, staged_queue), (state_root, staged_state)):
            if source.exists():
                shutil.copytree(source, target)
        _rebase_private_campaign_state_paths(
            staged_queue,
            ((run_root, staged_runs), (queue_root, staged_queue)),
        )
        editorial = execute_campaign_editorial_workset(
            editorial_workset,
            staged_runs,
            brief_factory=brief_factory,
            writer=writer,
            reviewer=reviewer,
        )
        rewrite_briefs = {
            str(run["run_id"]): rewrite_brief_factory(run["candidate"])
            for run in editorial["runs"]
            if run["lane"] == "rewrite"
        }
        publisher_receipt = replay_campaign_editorial_workset_through_publisher(
            editorial,
            staged_queue,
            staged_state,
            rewrite_briefs=rewrite_briefs,
        )
        translation_receipt = replay_campaign_editorial_workset_through_translation(
            repo_root,
            editorial,
            staged_queue,
            staged_state,
            client,
            rewrite_briefs=rewrite_briefs,
            locale=locale,
            max_repairs=max_repairs,
        )
        _rebase_private_campaign_state_paths(
            staged_queue,
            ((staged_runs, run_root), (staged_queue, queue_root)),
        )
        for source, target in ((staged_runs, run_root), (staged_queue, queue_root), (staged_state, state_root)):
            if source.exists():
                shutil.copytree(source, target, dirs_exist_ok=True)
    for run in editorial["runs"]:
        run["run_dir"] = str((run_root / str(run["work_id"])).resolve())
    return {
        "status": "dry-run",
        "published": 0,
        "campaign_version": editorial["campaign_version"],
        "lanes": list(CONTENT_LANES),
        "editorial_runs": editorial["runs"],
        "publisher": publisher_receipt,
        "translation": translation_receipt,
    }


APF_CREATE_RUN_ADAPTER_LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
APF_CREATE_RUN_ADAPTER_SOURCE_LANES = ("new", "rewrite")
APF_CREATE_RUN_ADAPTER_TRANSLATION_LANES = ("i18n-new", "i18n-rewrite")
APF_CREATE_RUN_ADAPTER_TUPLE_KEYS = frozenset(
    {"lane", "work_id", "article_id", "locale"}
)
APF_CREATE_RUN_ADAPTER_FORBIDDEN_CALLER_KEYS = frozenset(
    {"run_id", "status", "verdict", "ready"}
)


def _create_run_adapter_digest(payload: object) -> str:
    return _coordinator_receipt_digest(payload)


def _create_run_adapter_root(path: Path, label: str) -> Path:
    root = Path(path)
    if not root.is_absolute():
        raise ValueError(f"{label} root must be absolute")
    try:
        resolved = root.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"{label} root is invalid") from error
    if root.exists() and root.is_symlink():
        raise ValueError(f"{label} root must not be a symlink")
    return resolved


def _create_run_adapter_roots(
    *,
    run_root: Path,
    queue_root: Path,
    state_root: Path,
) -> tuple[Path, Path, Path]:
    roots = (
        ("run", _create_run_adapter_root(run_root, "run")),
        ("queue", _create_run_adapter_root(queue_root, "queue")),
        ("state", _create_run_adapter_root(state_root, "state")),
    )
    for left_index, (left_label, left) in enumerate(roots):
        for right_label, right in roots[left_index + 1 :]:
            if left == right or left.is_relative_to(right) or right.is_relative_to(left):
                raise ValueError(f"{left_label}/{right_label}: roots must not overlap")
    return roots[0][1], roots[1][1], roots[2][1]


def _create_run_adapter_required_string(value: object, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{label} is required")
    return value


def _create_run_adapter_sha(value: object, label: str) -> str:
    digest = _create_run_adapter_required_string(value, label)
    if SHA256_PATTERN.fullmatch(digest) is None:
        display = label.replace("_", " ")
        raise ValueError(f"{display} must be a sha256 digest")
    return digest


def _create_run_adapter_work_item(
    raw_item: object,
    *,
    campaign_version: str,
) -> dict[str, str]:
    if not isinstance(raw_item, dict):
        raise ValueError("create-run adapter work item is invalid")
    if APF_CREATE_RUN_ADAPTER_FORBIDDEN_CALLER_KEYS.intersection(raw_item):
        raise ValueError("caller-supplied run identity or status is not accepted")
    lane = raw_item.get("lane")
    if lane in APF_CREATE_RUN_ADAPTER_SOURCE_LANES:
        item = _campaign_editorial_work_item(raw_item)
    elif lane in APF_CREATE_RUN_ADAPTER_TRANSLATION_LANES:
        expected_source_kind = "matrix" if lane == "i18n-new" else "legacy"
        required = {
            "source_kind",
            "article_id",
            "locale",
            "campaign_version",
            "work_id",
            "lane",
            "reason",
        }
        if set(raw_item) != required:
            raise ValueError("create-run adapter translation work item is invalid")
        item = {
            key: _create_run_adapter_required_string(raw_item.get(key), key)
            for key in required
        }
        if (
            item["source_kind"] != expected_source_kind
            or item["campaign_version"] != campaign_version
            or item["locale"] == "zh-TW"
            or item["locale"] not in multilingual.SUPPORTED_LOCALES
            or item["work_id"]
            != _campaign_work_id(
                item["source_kind"],
                item["article_id"],
                item["locale"],
                campaign_version,
            )
        ):
            raise ValueError("create-run adapter translation work item is invalid")
    else:
        raise ValueError("create-run adapter lane is invalid")
    if item["campaign_version"] != campaign_version:
        raise ValueError("create-run adapter campaign version drift")
    return item


def _create_run_adapter_exact_tuples(
    exact_tuples: Iterable[Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    if isinstance(exact_tuples, (str, bytes)):
        raise ValueError("create-run adapter exact tuples must be a collection")
    by_lane: dict[str, dict[str, str]] = {}
    count = 0
    for raw_tuple in exact_tuples:
        count += 1
        if not isinstance(raw_tuple, Mapping):
            raise ValueError("create-run adapter exact tuple is invalid")
        if APF_CREATE_RUN_ADAPTER_FORBIDDEN_CALLER_KEYS.intersection(raw_tuple):
            raise ValueError("caller-supplied run identity or status is not accepted")
        if set(raw_tuple) != APF_CREATE_RUN_ADAPTER_TUPLE_KEYS:
            raise ValueError("create-run adapter exact tuple fields are strict")
        item = {
            key: _create_run_adapter_required_string(raw_tuple.get(key), key)
            for key in APF_CREATE_RUN_ADAPTER_TUPLE_KEYS
        }
        lane = item["lane"]
        if lane in by_lane:
            raise ValueError("create-run adapter lane is duplicated")
        by_lane[lane] = item
    if count != 4 or set(by_lane) != set(APF_CREATE_RUN_ADAPTER_LANES):
        raise ValueError("create-run adapter requires exactly four lanes")
    return by_lane


def _create_run_adapter_source_run_id(item: Mapping[str, str]) -> str:
    canonical = {
        "article_id": item["article_id"],
        "campaign_version": item["campaign_version"],
        "lane": item["lane"],
        "locale": item["locale"],
        "source_kind": item["source_kind"],
        "work_id": item["work_id"],
    }
    return (
        f"apf-create-run-{item['lane']}-"
        f"{_create_run_adapter_digest(canonical)[:24]}"
    )


def _create_run_adapter_plan(
    *,
    repo_root: Path,
    workset: Mapping[str, Any],
    exact_tuples: Iterable[Mapping[str, str]],
    run_root: Path,
    queue_root: Path,
    state_root: Path,
    campaign_version: str,
    workset_sha256: str,
    confirmed_payload_digest: str,
    activation_authorization_digest: str,
    runtime_identity_digest: str,
    actor_identity: str,
    correlation_id: str,
    max_runs: int,
) -> dict[str, Any]:
    campaign_version = _create_run_adapter_required_string(
        campaign_version,
        "campaign_version",
    )
    _create_run_adapter_sha(workset_sha256, "workset_sha256")
    confirmed_payload_digest = _create_run_adapter_sha(
        confirmed_payload_digest,
        "confirmed_payload_digest",
    )
    activation_authorization_digest = _create_run_adapter_sha(
        activation_authorization_digest,
        "activation_authorization_digest",
    )
    runtime_identity_digest = _create_run_adapter_sha(
        runtime_identity_digest,
        "runtime_identity_digest",
    )
    actor_identity = _create_run_adapter_required_string(
        actor_identity,
        "actor_identity",
    )
    correlation_id = _create_run_adapter_required_string(
        correlation_id,
        "correlation_id",
    )
    if max_runs != 1:
        raise ValueError("create-run adapter requires max_runs=1 downstream contract")
    resolved_repo = repo_root.resolve(strict=True)
    resolved_run_root, resolved_queue_root, resolved_state_root = (
        _create_run_adapter_roots(
            run_root=run_root,
            queue_root=queue_root,
            state_root=state_root,
        )
    )
    _validate_formal_runtime(resolved_queue_root, resolved_repo)
    if (
        not isinstance(workset, Mapping)
        or set(workset)
        != {"schema_version", "campaign_version", "lanes", "items", "summary"}
        or workset.get("schema_version") != 1
        or workset.get("lanes") != list(APF_CREATE_RUN_ADAPTER_LANES)
        or not isinstance(workset.get("items"), list)
    ):
        raise ValueError("create-run adapter workset is invalid")
    if workset.get("campaign_version") != campaign_version:
        raise ValueError("create-run adapter campaign version drift")
    if _create_run_adapter_digest(workset) != workset_sha256:
        raise ValueError("create-run adapter workset SHA drift")
    exact_by_lane = _create_run_adapter_exact_tuples(exact_tuples)
    by_lane: dict[str, dict[str, str]] = {}
    for raw_item in workset["items"]:
        item = _create_run_adapter_work_item(
            raw_item,
            campaign_version=campaign_version,
        )
        lane = item["lane"]
        if lane in by_lane:
            raise ValueError("create-run adapter lane is duplicated")
        by_lane[lane] = item
    if set(by_lane) != set(APF_CREATE_RUN_ADAPTER_LANES):
        raise ValueError("create-run adapter requires exactly four lanes")
    for lane, item in by_lane.items():
        exact = exact_by_lane[lane]
        if any(
            exact[key] != item[key]
            for key in ("lane", "work_id", "article_id", "locale")
        ):
            raise ValueError("create-run adapter exact work identity differs")
    translation_locale = by_lane["i18n-new"]["locale"]
    if by_lane["i18n-rewrite"]["locale"] != translation_locale:
        raise ValueError("create-run adapter translation locale drift")
    for source_lane, translation_lane in (
        ("new", "i18n-new"),
        ("rewrite", "i18n-rewrite"),
    ):
        source = by_lane[source_lane]
        translation = by_lane[translation_lane]
        if (
            source["source_kind"] != translation["source_kind"]
            or source["article_id"] != translation["article_id"]
            or source["locale"] != "zh-TW"
        ):
            raise ValueError("create-run adapter translation source pairing drift")

    new_run_id = _create_run_adapter_source_run_id(by_lane["new"])
    rewrite_run_id = _create_run_adapter_source_run_id(by_lane["rewrite"])
    run_records = [
        {
            "lane": "new",
            "run_id": new_run_id,
            "mode": "create",
            "work_id": by_lane["new"]["work_id"],
            "article_id": by_lane["new"]["article_id"],
            "locale": by_lane["new"]["locale"],
            "run_dir": str((resolved_run_root / new_run_id).resolve()),
            "stage": "source",
            "depends_on": [],
        },
        {
            "lane": "rewrite",
            "run_id": rewrite_run_id,
            "mode": "rewrite_existing_body",
            "work_id": by_lane["rewrite"]["work_id"],
            "article_id": by_lane["rewrite"]["article_id"],
            "locale": by_lane["rewrite"]["locale"],
            "run_dir": str((resolved_run_root / rewrite_run_id).resolve()),
            "stage": "source",
            "depends_on": [],
        },
    ]
    translation_records = [
        (
            "i18n-new",
            by_lane["i18n-new"],
            new_run_id,
        ),
        (
            "i18n-rewrite",
            by_lane["i18n-rewrite"],
            rewrite_run_id,
        ),
    ]
    for lane, item, source_run_id in translation_records:
        run_id = multilingual.translation_run_id(
            source_run_id,
            item["article_id"],
            item["locale"],
        )
        run_records.append(
            {
                "lane": lane,
                "run_id": run_id,
                "mode": "translate_existing",
                "work_id": item["work_id"],
                "article_id": item["article_id"],
                "locale": item["locale"],
                "run_dir": str(
                    (resolved_queue_root / "translation-runs" / run_id).resolve()
                ),
                "stage": "pending_dependency",
                "depends_on": [source_run_id],
            }
        )
    plan = {
        "schema_version": 1,
        "entrypoint": "scripts.agy_gemini_coordinator:create_campaign_run_adapter",
        "campaign_version": campaign_version,
        "workset_sha256": workset_sha256,
        "confirmed_payload_digest": confirmed_payload_digest,
        "activation_authorization_digest": activation_authorization_digest,
        "runtime_identity_digest": runtime_identity_digest,
        "actor_identity": actor_identity,
        "correlation_id": correlation_id,
        "downstream_contract": {"max_runs": max_runs},
        "roots": {
            "repo_root": str(resolved_repo),
            "run_root": str(resolved_run_root),
            "queue_root": str(resolved_queue_root),
            "state_root": str(resolved_state_root),
        },
        "runs": run_records,
    }
    plan["plan_digest"] = _create_run_adapter_digest(plan)
    plan["expected_write_set"] = _create_run_adapter_write_set(plan)
    return plan


def _create_run_adapter_new_brief(
    repo_root: Path,
    item: Mapping[str, str],
    run_id: str,
) -> dict[str, Any]:
    backlog = {
        str(row.get("id") or ""): row
        for row in pipeline.build_matrix_backlog(repo_root)
    }
    row = backlog.get(item["article_id"])
    if row is None:
        raise ValueError("create-run adapter new article is not in matrix backlog")
    target = pipeline._matrix_targets(repo_root, [row])[item["article_id"]]
    brief = {
        "schema_version": pipeline.SCHEMA_VERSION,
        "run_id": run_id,
        "mode": "create",
        "campaign_version": item["campaign_version"],
        "source": {
            "type": "matrix",
            "paths": [
                pipeline.MATRIX_PLAN.as_posix(),
                pipeline.MATRIX_V2_PLAN.as_posix(),
            ],
        },
        "articles": [
            {
                "matrix": row,
                "target": target,
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    pipeline.validate_new_brief(brief)
    return brief


def _create_run_adapter_rewrite_brief(
    repo_root: Path,
    item: Mapping[str, str],
    run_id: str,
) -> dict[str, Any]:
    records = {
        str(record.get("id") or ""): record
        for record in publisher.legacy_article_records(repo_root)
    }
    record = records.get(item["article_id"])
    inventory_item = pipeline._existing_rewrite_inventory(repo_root).get(
        item["article_id"]
    )
    if record is None or inventory_item is None:
        raise ValueError("create-run adapter rewrite article is not in legacy inventory")
    brief = {
        "schema_version": pipeline.SCHEMA_VERSION,
        "run_id": run_id,
        "mode": "rewrite_existing_body",
        "campaign_version": item["campaign_version"],
        "source_commit": _head_sha(repo_root),
        "sort_contract": "apf_004_exact_create_run_adapter",
        "articles": [_legacy_rewrite_article_brief(record, inventory_item)],
    }
    pipeline.validate_rewrite_brief(brief)
    return brief


def _create_run_adapter_source_briefs(
    plan: Mapping[str, Any],
    by_lane: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, Any]]:
    repo_root = Path(str(plan["roots"]["repo_root"]))
    run_by_lane = {
        str(record["lane"]): record
        for record in plan["runs"]
        if record["lane"] in APF_CREATE_RUN_ADAPTER_SOURCE_LANES
    }
    return {
        "new": _create_run_adapter_new_brief(
            repo_root,
            by_lane["new"],
            str(run_by_lane["new"]["run_id"]),
        ),
        "rewrite": _create_run_adapter_rewrite_brief(
            repo_root,
            by_lane["rewrite"],
            str(run_by_lane["rewrite"]["run_id"]),
        ),
    }


def _create_run_adapter_write_set(plan: Mapping[str, Any]) -> list[str]:
    queue_root = Path(str(plan["roots"]["queue_root"]))
    paths: list[Path] = []
    for record in plan["runs"]:
        run_id = str(record["run_id"])
        if record["lane"] in APF_CREATE_RUN_ADAPTER_SOURCE_LANES:
            paths.append(Path(str(record["run_dir"])) / "brief.json")
            paths.append(_state_path(run_id, queue_root))
        else:
            paths.append(_create_run_adapter_pending_path(queue_root, run_id))
    paths.append(_create_run_adapter_transaction_path(queue_root, str(plan["plan_digest"])))
    return [str(path.resolve(strict=False)) for path in paths]


def _create_run_adapter_pending_path(queue_root: Path, run_id: str) -> Path:
    opaque_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    return queue_root / "translation-pending-dependencies" / f"{opaque_id}.json"


def _create_run_adapter_transaction_path(queue_root: Path, plan_digest: str) -> Path:
    return queue_root / "apf-create-run-transactions" / f"{plan_digest}.json"


def _create_run_adapter_existing_json(path: Path, label: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} receipt is damaged") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} receipt is damaged")
    return value


def _create_run_adapter_preflight_apply(
    plan: Mapping[str, Any],
    source_briefs: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    queue_root = Path(str(plan["roots"]["queue_root"]))
    source_records = {
        str(record["lane"]): record
        for record in plan["runs"]
        if record["lane"] in APF_CREATE_RUN_ADAPTER_SOURCE_LANES
    }
    pending_payloads = _create_run_adapter_pending_payloads(plan)
    for lane, record in source_records.items():
        run_dir = Path(str(record["run_dir"]))
        brief_path = run_dir / "brief.json"
        existing_brief = _create_run_adapter_existing_json(brief_path, "run")
        if existing_brief is not None and existing_brief != source_briefs[lane]:
            raise ValueError("create-run adapter run identity collision")
        state_path = _state_path(str(record["run_id"]), queue_root)
        existing_state = _create_run_adapter_existing_json(state_path, "run state")
        if existing_state is not None and (
            existing_state.get("run_id") != record["run_id"]
            or existing_state.get("run_dir") != str(run_dir.resolve())
            or existing_state.get("status") not in {"active", "complete"}
        ):
            raise ValueError("create-run adapter run identity collision")
    for run_id, pending in pending_payloads.items():
        existing_pending = _create_run_adapter_existing_json(
            _create_run_adapter_pending_path(queue_root, run_id),
            "pending dependency",
        )
        if existing_pending is not None and existing_pending != pending:
            raise ValueError("create-run adapter pending dependency collision")
    transaction_path = _create_run_adapter_transaction_path(
        queue_root,
        str(plan["plan_digest"]),
    )
    existing_transaction = _create_run_adapter_existing_json(
        transaction_path,
        "transaction",
    )
    if existing_transaction is not None and (
        existing_transaction.get("schema_version") != 1
        or existing_transaction.get("plan_digest") != plan["plan_digest"]
        or existing_transaction.get("exact_run_ids") != [record["run_id"] for record in plan["runs"]]
    ):
        raise ValueError("create-run adapter transaction receipt is damaged")
    return pending_payloads


def _create_run_adapter_pending_payloads(
    plan: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for record in plan["runs"]:
        if record["lane"] not in APF_CREATE_RUN_ADAPTER_TRANSLATION_LANES:
            continue
        payload = {
            "schema_version": 1,
            "status": "pending_source_completion",
            "owner": "scripts.agy_gemini_coordinator:create_campaign_run_adapter",
            "plan_digest": plan["plan_digest"],
            "campaign_version": plan["campaign_version"],
            "lane": record["lane"],
            "run_id": record["run_id"],
            "work_id": record["work_id"],
            "source_article_id": record["article_id"],
            "locale": record["locale"],
            "depends_on": record["depends_on"],
            "source_completion_required": True,
        }
        payload["payload_digest"] = _create_run_adapter_digest(payload)
        payloads[str(record["run_id"])] = payload
    return payloads


def create_campaign_run_adapter(
    *,
    repo_root: Path,
    workset: Mapping[str, Any],
    exact_tuples: Iterable[Mapping[str, str]],
    run_root: Path,
    queue_root: Path,
    state_root: Path,
    campaign_version: str,
    workset_sha256: str,
    confirmed_payload_digest: str,
    activation_authorization_digest: str,
    runtime_identity_digest: str,
    actor_identity: str,
    correlation_id: str,
    plan_only: bool,
    max_runs: int = 1,
) -> dict[str, Any]:
    """將已確認四 lane APF tuple 轉為可重算且可 resume 的 create-run identity。"""
    plan = _create_run_adapter_plan(
        repo_root=repo_root,
        workset=workset,
        exact_tuples=exact_tuples,
        run_root=run_root,
        queue_root=queue_root,
        state_root=state_root,
        campaign_version=campaign_version,
        workset_sha256=workset_sha256,
        confirmed_payload_digest=confirmed_payload_digest,
        activation_authorization_digest=activation_authorization_digest,
        runtime_identity_digest=runtime_identity_digest,
        actor_identity=actor_identity,
        correlation_id=correlation_id,
        max_runs=max_runs,
    )
    by_lane = {
        str(item["lane"]): item
        for item in workset["items"]
        if isinstance(item, Mapping)
    }
    source_briefs = _create_run_adapter_source_briefs(plan, by_lane)
    result = {
        "schema_version": 1,
        "status": "planned" if plan_only else "applied",
        "entrypoint": plan["entrypoint"],
        "campaign_version": plan["campaign_version"],
        "plan_digest": plan["plan_digest"],
        "exact_run_ids": [record["run_id"] for record in plan["runs"]],
        "runs": plan["runs"],
        "dependency_graph": {
            record["run_id"]: record["depends_on"]
            for record in plan["runs"]
        },
        "expected_write_set": plan["expected_write_set"],
        "production_mutation": False,
    }
    if plan_only:
        return result
    queue_root_resolved = Path(str(plan["roots"]["queue_root"]))
    pending_payloads = _create_run_adapter_preflight_apply(plan, source_briefs)
    created_registered = 0
    created_pending = 0
    for record in plan["runs"]:
        if record["lane"] not in APF_CREATE_RUN_ADAPTER_SOURCE_LANES:
            continue
        lane = str(record["lane"])
        run_dir = Path(str(record["run_dir"]))
        state_path = _state_path(str(record["run_id"]), queue_root_resolved)
        state_existed = state_path.exists()
        brief_path = run_dir / "brief.json"
        if not brief_path.exists():
            atomic_write_json(brief_path, source_briefs[lane])
        register_run(
            run_dir,
            queue_root_resolved,
            correlation_id=str(plan["correlation_id"]),
        )
        if not state_existed:
            created_registered += 1
    for run_id, pending in pending_payloads.items():
        path = _create_run_adapter_pending_path(queue_root_resolved, run_id)
        if path.exists():
            continue
        atomic_write_json(path, pending)
        created_pending += 1
    transaction = {
        "schema_version": 1,
        "status": "applied",
        "plan_digest": plan["plan_digest"],
        "exact_run_ids": [record["run_id"] for record in plan["runs"]],
        "created": {
            "registered": created_registered,
            "pending_dependencies": created_pending,
        },
        "updated_at": _now(),
    }
    transaction_path = _create_run_adapter_transaction_path(
        queue_root_resolved,
        str(plan["plan_digest"]),
    )
    if not transaction_path.exists():
        atomic_write_json(transaction_path, transaction)
    return {
        **result,
        "created": {
            "registered": created_registered,
            "pending_dependencies": created_pending,
        },
        "transaction_receipt": str(transaction_path.resolve()),
    }


def _slug_part(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return slug[:80] or "article"


def _next_legacy_rewrite_run_id(run_root: Path, queue_root: Path, base_run_id: str) -> str:
    """保留歷史 run/state，為重新排程挑選第一個未使用的 lineage ID。"""
    retries = (
        f"{base_run_id}-retry-{index:02d}"
        for index in range(1, MAX_LEGACY_REWRITE_LINEAGE_RETRIES + 1)
    )
    candidates = [base_run_id, *retries]
    for candidate in candidates:
        if not (run_root / candidate).exists() and not _state_path(candidate, queue_root).exists():
            return candidate
    raise ValueError("legacy rewrite run lineage exhausted")


def _head_sha(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _next_new_matrix_run_prefix(run_root: Path, queue_root: Path) -> str:
    today = datetime.now().astimezone().strftime("%Y%m%d")
    stem = f"auto-new-v1-{today}"
    used: set[str] = set()
    if run_root.exists():
        used.update(path.name for path in run_root.iterdir() if path.is_dir())
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        run_id = str(state.get("run_id") or "")
        if run_id:
            used.add(run_id)
    index = 1
    while True:
        prefix = f"{stem}-{index:03d}"
        if not any(item == prefix or item.startswith(f"{prefix}-") for item in used):
            return prefix
        index += 1


def _seed_exact_new_matrix_run(
    repo_root: Path,
    queue_root: Path,
    run_root: Path,
    exact_run_id: str,
    max_articles_per_run: int,
) -> dict[str, Any]:
    if EXACT_RUN_ID_PATTERN.fullmatch(exact_run_id) is None:
        raise ValueError("exact run id format is invalid")
    run_dir = run_root / exact_run_id
    correlation_id = secrets.token_hex(16)
    reservation_token = secrets.token_hex(16)
    staging_token_root = run_root / ".exact-run-staging" / reservation_token
    staging_run_dir = staging_token_root / exact_run_id
    _reserve_run_identity(
        exact_run_id,
        run_dir,
        queue_root,
        correlation_id,
        reservation_token,
    )
    try:
        active_create_before = _active_count_by_mode(queue_root, "create")
        excluded_ids = _registered_article_ids_by_mode(queue_root, "create")
        paths = pipeline.prepare_matrix_runs(
            repo_root,
            exact_run_id,
            output_root=staging_token_root,
            limit=min(1, max_articles_per_run),
            exclude_ids=excluded_ids,
            max_articles_per_run=min(1, max_articles_per_run),
            exact_run_id=exact_run_id,
        )
        if paths != [staging_run_dir / "brief.json"]:
            raise ValueError("exact run identity could not be allocated")
        state = _activate_run_reservation(
            exact_run_id,
            staging_run_dir,
            run_dir,
            queue_root,
            correlation_id,
            reservation_token,
        )
        return {
            "status": "seeded",
            "created": 1,
            "created_run_ids": [str(state["run_id"])],
            "active_create_before": active_create_before,
        }
    except BaseException:
        try:
            _cleanup_staging(staging_token_root)
        finally:
            _release_run_reservation(
                exact_run_id,
                run_dir,
                queue_root,
                correlation_id,
                reservation_token,
            )
        raise


def seed_new_matrix_runs(
    repo_root: Path,
    queue_root: Path,
    run_root: Path,
    *,
    min_active_runs: int = DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS,
    max_new_runs: int = DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE,
    max_articles_per_run: int = DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN,
    exact_run_id: str | None = None,
) -> dict[str, Any]:
    """自動從內容矩陣挑未登記的新文，建立 create run 並交給 coordinator。"""
    if exact_run_id is not None:
        return _seed_exact_new_matrix_run(
            repo_root,
            queue_root,
            run_root,
            exact_run_id,
            max_articles_per_run,
        )
    if min_active_runs <= 0 or max_new_runs <= 0 or max_articles_per_run <= 0:
        return {"status": "disabled", "created": 0, "created_run_ids": []}
    active_create = _active_count_by_mode(queue_root, "create")
    if active_create >= min_active_runs:
        return {"status": "active_floor_met", "created": 0, "created_run_ids": [], "active_create": active_create}

    created: list[str] = []
    excluded_ids = _registered_article_ids_by_mode(queue_root, "create")
    for _ in range(min(1, max_new_runs, min_active_runs - active_create)):
        run_prefix = _next_new_matrix_run_prefix(run_root, queue_root)
        paths = pipeline.prepare_matrix_runs(
            repo_root,
            run_prefix,
            output_root=run_root,
            limit=min(1, max_articles_per_run),
            exclude_ids=excluded_ids,
            max_articles_per_run=min(1, max_articles_per_run),
        )
        if not paths:
            break
        for brief_path in paths[:1]:
            state = register_run(brief_path.parent, queue_root)
            created.append(str(state["run_id"]))
            brief = _brief(brief_path.parent)
            excluded_ids.update(_create_article_ids_from_brief(brief))
        if len(created) >= max_new_runs:
            break

    return {
        "status": "seeded" if created else "idle",
        "created": len(created),
        "created_run_ids": created,
        "active_create_before": active_create,
    }


def _legacy_rewrite_article_brief(
    record: dict[str, Any],
    inventory_item: dict[str, Any],
) -> dict[str, Any]:
    article_id = str(record["id"])
    source_record = inventory_item.get("record") if isinstance(inventory_item.get("record"), dict) else record
    current_body = inventory_item.get("currentBody")
    immutable_fields = {
        "id": article_id,
        "product": str(source_record.get("product") or source_record.get("articleCategory") or publisher._record_category(record)),
        "slug": str(source_record.get("slug") or ""),
        "serial": publisher._record_serial(record),
        "title": str(source_record.get("title") or record.get("title") or ""),
        "description": str(source_record.get("description") or record.get("description") or ""),
        "answer": str(source_record.get("answer") or record.get("answer") or ""),
        "faq": source_record.get("faq") if isinstance(source_record.get("faq"), list) else [],
        "tags": source_record.get("tags") if isinstance(source_record.get("tags"), list) else [],
        "published": str(inventory_item.get("published") or source_record.get("published") or ""),
        "updated": str(inventory_item.get("updated") or source_record.get("updated") or ""),
        "urlSlug": str(source_record.get("urlSlug") or source_record.get("slug") or record.get("slug") or ""),
        "primaryKeyword": str(source_record.get("primaryKeyword") or record.get("primaryKeyword") or ""),
    }
    return {
        "slot": "article-01",
        "article_id": article_id,
        "identity": {
            "id": article_id,
            "product": immutable_fields["product"],
            "category": publisher._record_category(record),
            "serial": immutable_fields["serial"],
            "slug": immutable_fields["urlSlug"],
            "primaryKeyword": immutable_fields["primaryKeyword"],
            "title": immutable_fields["title"],
        },
        "immutable_fields": immutable_fields,
        "current_body": current_body,
        "current_body_sha256": pipeline.body_sha256(current_body),
        "rewrite_brief": [
            "把正文改得更口語、貼近使用者情境；不要改標題、URL、FAQ、metadata 或文章定位。",
            "每節至少放入一個具體生活場景、可觀察動作或可直接套用的判斷句，避免模板句與空泛雞湯。",
            "保留原本搜尋意圖與主題邊界；不要承諾感情、工作、財富、健康或人生結果。",
        ],
        "source_file": "app/web/static/article-meta.js",
        "body_source": "buildArticleContent",
    }


def _compact_legacy_backlog(backlog: dict[str, Any]) -> dict[str, Any]:
    preview = backlog.get("unattempted_articles")
    return {
        "released": backlog.get("released", 0),
        "clean_approve": backlog.get("clean_approve", 0),
        "publish_ready": backlog.get("publish_ready", 0),
        "retry_deferred": backlog.get("retry_deferred", 0),
        "retry_exhausted": backlog.get("retry_exhausted", 0),
        "retry_invalid": backlog.get("retry_invalid", 0),
        "reject": backlog.get("reject", 0),
        "active_or_incomplete": backlog.get("active_or_incomplete", 0),
        "non_legacy": backlog.get("non_legacy", 0),
        "legacy_total": backlog.get("legacy_total", 0),
        "attempted": backlog.get("attempted", 0),
        "unattempted": backlog.get("unattempted", 0),
        "clean_approve_run_ids": backlog.get("clean_approve_run_ids", []),
        "publish_ready_run_ids": backlog.get("publish_ready_run_ids", []),
        "retry_deferred_run_ids": backlog.get("retry_deferred_run_ids", []),
        "retry_exhausted_run_ids": backlog.get("retry_exhausted_run_ids", []),
        "retry_invalid_run_ids": backlog.get("retry_invalid_run_ids", []),
        "reject_run_ids": backlog.get("reject_run_ids", []),
        "unattempted_preview": preview[:5] if isinstance(preview, list) else [],
        "repair_rejects_allowed": backlog.get("repair_rejects_allowed", False),
    }


def seed_legacy_rewrite_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    run_root: Path,
    *,
    max_new_runs: int = DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE,
    max_active_runs: int = MAX_ACTIVE_RUNS_PER_CYCLE,
    source_commit: str | None = None,
) -> dict[str, Any]:
    """自動挑最前面的未掃舊文，建立私密 rewrite run 並登記到 coordinator。"""
    if max_new_runs <= 0:
        return {"status": "disabled", "created": 0, "created_run_ids": []}

    active_count = _active_count_by_mode(queue_root, "rewrite_existing_body")
    if active_count >= max_active_runs:
        return {"status": "active_limit", "created": 0, "created_run_ids": [], "active": active_count}

    legacy_records = publisher.legacy_article_records(repo_root)
    allowed_article_ids = {str(record["id"]) for record in legacy_records}
    backlog = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
        legacy_records=legacy_records,
    )
    publish_ready = backlog.get("publish_ready", backlog["clean_approve"])
    if publish_ready > 0:
        return {"status": "publish_ready_first", "created": 0, "created_run_ids": [], "backlog": _compact_legacy_backlog(backlog)}
    if backlog.get("retry_deferred", 0) > 0 or backlog.get("retry_invalid", 0) > 0:
        return {"status": "rewrite_retry_blocked", "created": 0, "created_run_ids": [], "backlog": _compact_legacy_backlog(backlog)}
    if backlog["unattempted"] <= 0:
        status = "rewrite_retry_exhausted" if backlog.get("retry_exhausted", 0) > 0 else "idle"
        return {"status": status, "created": 0, "created_run_ids": [], "backlog": _compact_legacy_backlog(backlog)}

    registered_article_ids = _registered_rewrite_article_ids(queue_root)
    inventory = pipeline._existing_rewrite_inventory(repo_root)
    head = source_commit or _head_sha(repo_root)
    capacity = max(0, min(max_new_runs, max_active_runs - active_count))
    created: list[str] = []
    for record in legacy_records:
        if len(created) >= capacity:
            break
        article_id = str(record.get("id") or "")
        if not article_id or article_id in registered_article_ids:
            continue
        inventory_item = inventory.get(article_id)
        if not inventory_item:
            continue
        base_run_id = f"legacy-auto-sweep-v1-{publisher._record_serial(record)}-{_slug_part(article_id)}"
        run_id = _next_legacy_rewrite_run_id(run_root, queue_root, base_run_id)
        run_dir = run_root / run_id
        article_brief = _legacy_rewrite_article_brief(record, inventory_item)
        brief = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "rewrite_existing_body",
            "source_commit": head,
            "sort_contract": "legacy_auto_sweep_v1_oldest_unattempted_first",
            "articles": [article_brief],
        }
        pipeline.validate_rewrite_brief(brief)
        pipeline.write_json(run_dir / "brief.json", brief)
        pipeline.write_json(run_dir / "public-brief.json", pipeline.public_model_brief(brief))
        register_run(run_dir, queue_root)
        registered_article_ids.add(article_id)
        created.append(run_id)

    return {
        "status": "seeded" if created else "idle",
        "created": len(created),
        "created_run_ids": created,
        "backlog": _compact_legacy_backlog(backlog),
    }


def cycle_once(
    queue_root: Path,
    *,
    tick: Tick = run_pipeline_tick,
    process: Process = process_once,
    repo_root: Path | None = None,
    new_matrix_sweep: bool = False,
    new_matrix_run_root: Path | None = None,
    new_matrix_min_active_runs: int = DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS,
    new_matrix_max_new_runs_per_cycle: int = DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE,
    new_matrix_max_articles_per_run: int = DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN,
    legacy_sweep: bool = False,
    legacy_state_root: Path | None = None,
    legacy_run_root: Path | None = None,
    legacy_max_new_runs_per_cycle: int = DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE,
    lane_mode: bool = False,
    new_only: bool = False,
    exact_run_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """推進 run 狀態；lane mode 每輪讓四類內容各推進一個 run。"""
    _validate_formal_runtime(queue_root, repo_root)
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    if selected_run_ids is not None and (new_matrix_sweep or legacy_sweep):
        raise ValueError("exact run ids cannot be combined with automatic sweeps")
    root = queue_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "coordinator.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "active": 0, "complete": 0, "failed": 0, "runner": {"status": "idle"}}

        resolved_repo = (repo_root or Path.cwd()).resolve()
        new_matrix_summary: dict[str, Any] | None = None
        if new_matrix_sweep:
            new_matrix_summary = seed_new_matrix_runs(
                resolved_repo,
                root,
                (new_matrix_run_root or resolved_repo / ".work/gsc-copy").resolve(),
                min_active_runs=new_matrix_min_active_runs,
                max_new_runs=new_matrix_max_new_runs_per_cycle,
                max_articles_per_run=new_matrix_max_articles_per_run,
            )

        legacy_summary: dict[str, Any] | None = None
        if legacy_sweep:
            if new_only:
                legacy_summary = {
                    "status": "disabled_by_new_only",
                    "created": 0,
                    "created_run_ids": [],
                }
            else:
                legacy_summary = seed_legacy_rewrite_runs(
                    resolved_repo,
                    root,
                    (legacy_state_root or resolved_repo / ".work/content-publisher").resolve(),
                    (legacy_run_root or resolved_repo / ".work/gsc-copy").resolve(),
                    max_new_runs=legacy_max_new_runs_per_cycle,
                )

        legacy_article_ids = publisher.legacy_article_ids(resolved_repo) if lane_mode else set()
        translation_replacements = (
            seed_failed_translation_replacements(
                resolved_repo,
                root,
                legacy_article_ids=legacy_article_ids,
            )
            if lane_mode and not new_only and selected_run_ids is None
            else None
        )
        active_states = _active_states(root)
        migrated_jobs = (
            _migrate_pending_jobs(root, active_states, legacy_article_ids)
            if lane_mode and not new_only and selected_run_ids is None
            else None
        )
        if selected_run_ids is not None:
            missing = selected_run_ids - _known_run_ids(root)
            if missing:
                raise ValueError(
                    "exact run ids not found: " + ",".join(sorted(missing))
                )
            active_states = [
                state
                for state in active_states
                if str(state.get("run_id") or "") in selected_run_ids
            ]
        if new_only:
            states = [
                state
                for state in active_states
                if _lane_for_state(state, legacy_article_ids) == "new"
            ][:1]
        elif lane_mode:
            states = _select_lane_states(active_states, legacy_article_ids)
        else:
            states = active_states[:MAX_ACTIVE_RUNS_PER_CYCLE]
        pending = 0
        completed = 0
        failed = 0
        for state in states:
            lane = _lane_for_state(state, legacy_article_ids) if lane_mode else None
            outcome = _advance(
                root,
                state,
                tick,
                job_queue_root=_lane_queue_root(root, lane) if lane is not None else None,
            )
            pending += outcome == "pending"
            completed += outcome == "complete"
            failed += outcome == "failed"

        runner: dict[str, str] = {"status": "idle"}
        if pending and not new_only:
            try:
                if selected_run_ids is None:
                    runner = process(root)
                else:
                    runner = process(root, exact_run_ids=selected_run_ids)
            except json.JSONDecodeError:
                job_id = next(
                    (str(state["last_job_id"]) for state in states if state.get("last_job_id")),
                    "unknown",
                )
                runner = {"status": "failed", "job_id": job_id, "error_type": "JSONDecodeError"}
            if runner.get("status") == "failed":
                failed += 1
            elif runner.get("status") == "processed" and not lane_mode:
                retry_states = _active_states(root)
                if selected_run_ids is not None:
                    retry_states = [
                        state
                        for state in retry_states
                        if str(state.get("run_id") or "") in selected_run_ids
                    ]
                for state in retry_states[:MAX_ACTIVE_RUNS_PER_CYCLE]:
                    outcome = _advance(root, state, tick)
                    completed += outcome == "complete"
                    failed += outcome == "failed"

        remaining_states = _active_states(root)
        if selected_run_ids is not None:
            remaining_states = [
                state
                for state in remaining_states
                if str(state.get("run_id") or "") in selected_run_ids
            ]
        runnable_remaining = (
            [
                state
                for state in remaining_states
                if _lane_for_state(state, legacy_article_ids) == "new"
            ]
            if new_only
            else remaining_states
        )
        summary = {
            "status": "ok" if failed == 0 else "failed",
            "active": len(runnable_remaining),
            "complete": completed,
            "failed": failed,
            "runner": runner,
            "new_matrix_sweep": new_matrix_summary,
            "legacy_sweep": legacy_summary,
        }
        if lane_mode:
            lane_inventory = _lane_summary(
                root,
                remaining_states,
                legacy_article_ids,
            )
            summary["lanes"] = lane_inventory
            if translation_replacements and (
                translation_replacements.get("created", 0)
                or translation_replacements.get("skipped")
            ):
                summary["translation_replacements"] = translation_replacements
            summary["migrated_jobs"] = migrated_jobs
            if new_only:
                disabled_lanes = {
                    lane: lane_inventory[lane]
                    for lane in CONTENT_LANES
                    if lane != "new"
                }
                summary["runnable_active"] = len(runnable_remaining)
                summary["disabled_backlog"] = {
                    "active": sum(
                        inventory["active"]
                        for inventory in disabled_lanes.values()
                    ),
                    "queued": sum(
                        inventory["queued"]
                        for inventory in disabled_lanes.values()
                    ),
                    "processing": sum(
                        inventory["processing"]
                        for inventory in disabled_lanes.values()
                    ),
                    "lanes": disabled_lanes,
                }
        return summary


def resume_run(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    state = read_run_state(run_dir, queue_root)
    if state.get("error_type") == "LocalePlanValidationError":
        state.pop("last_job_id", None)
    state["status"] = "active"
    state.pop("error_type", None)
    state.pop("error_code", None)
    state.pop("result", None)
    _write_state(queue_root.resolve(), state)
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--new-matrix-run-root", type=Path, default=Path(".work/gsc-copy"))
    parser.add_argument("--new-matrix-sweep", action="store_true")
    parser.add_argument("--new-matrix-min-active-runs", type=int, default=DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS)
    parser.add_argument("--new-matrix-max-new-runs-per-cycle", type=int, default=DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE)
    parser.add_argument("--new-matrix-max-articles-per-run", type=int, default=DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN)
    parser.add_argument("--legacy-state-root", type=Path, default=Path(".work/content-publisher"))
    parser.add_argument("--legacy-run-root", type=Path, default=Path(".work/gsc-copy"))
    parser.add_argument("--legacy-sweep", action="store_true")
    parser.add_argument("--legacy-max-new-runs-per-cycle", type=int, default=DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE)
    parser.add_argument("--lane-mode", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("run_dir", type=Path)
    resume = subparsers.add_parser("resume")
    resume.add_argument("run_dir", type=Path)
    status = subparsers.add_parser("status")
    status.add_argument("run_dir", type=Path)
    terminalize = subparsers.add_parser("terminalize-pending")
    terminalize.add_argument("run_dir", type=Path)
    terminalize.add_argument("--job-queue-root", type=Path, required=True)
    terminalize.add_argument("--lane", choices=CONTENT_LANES, required=True)
    terminalize.add_argument("--run-id", required=True)
    terminalize.add_argument("--job-id", required=True)
    terminalize.add_argument("--request-sha256", required=True)
    terminalize.add_argument("--model", required=True)
    terminalize.add_argument("--role", choices=("writer", "reviewer"), required=True)
    terminalize.add_argument("--transport-attempt", type=int, required=True)
    terminalize.add_argument(
        "--reason",
        choices=sorted(OPERATOR_TERMINALIZATION_REASONS),
        required=True,
    )
    terminalize.add_argument("--execute", action="store_true")
    campaign = subparsers.add_parser("dry-run-campaign")
    campaign.add_argument("--campaign-version", required=True)
    campaign.add_argument("--state-root", type=Path, default=Path(".work/content-publisher"))
    campaign.add_argument("--locale", action="append", choices=sorted(multilingual.SUPPORTED_LOCALES))
    campaign.add_argument("--output", type=Path)
    cycle = subparsers.add_parser("cycle")
    cycle.add_argument("--exact-run-id", action="append")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue_root = args.queue_root.resolve()
    if args.command == "register":
        result = register_run(args.run_dir, queue_root)
    elif args.command == "resume":
        result = resume_run(args.run_dir, queue_root)
    elif args.command == "status":
        result = read_run_state(args.run_dir, queue_root)
    elif args.command == "terminalize-pending":
        try:
            result = terminalize_pending_job(
                args.run_dir,
                queue_root,
                job_queue_root=args.job_queue_root,
                lane=args.lane,
                expected_run_id=args.run_id,
                job_id=args.job_id,
                request_sha256=args.request_sha256,
                model=args.model,
                role=args.role,
                transport_attempt=args.transport_attempt,
                reason=args.reason,
                execute=args.execute,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            print(json.dumps({"status": "rejected", "error": str(error)}, ensure_ascii=False))
            return 1
    elif args.command == "dry-run-campaign":
        result = build_campaign_dry_run_workset(
            args.repo_root.resolve(),
            queue_root,
            args.state_root.resolve(),
            campaign_version=args.campaign_version,
            locales=args.locale or ("en", "ja", "ko"),
        )
        if args.output is not None:
            output = args.output.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    else:
        result = cycle_once(
            queue_root,
            repo_root=args.repo_root,
            new_matrix_sweep=args.new_matrix_sweep,
            new_matrix_run_root=args.new_matrix_run_root,
            new_matrix_min_active_runs=args.new_matrix_min_active_runs,
            new_matrix_max_new_runs_per_cycle=args.new_matrix_max_new_runs_per_cycle,
            new_matrix_max_articles_per_run=args.new_matrix_max_articles_per_run,
            legacy_sweep=args.legacy_sweep,
            legacy_state_root=args.legacy_state_root,
            legacy_run_root=args.legacy_run_root,
            legacy_max_new_runs_per_cycle=args.legacy_max_new_runs_per_cycle,
            lane_mode=args.lane_mode,
            new_only=_new_only_enabled(),
            exact_run_ids=args.exact_run_id,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

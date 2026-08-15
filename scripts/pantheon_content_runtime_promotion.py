#!/usr/bin/env python3
"""Pantheon runtime actor/manifest/stage aggregate promotion transaction."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

from scripts import pantheon_content_runtime_manifest as runtime_manifest


SCHEMA_VERSION = 1
REGRESSION_ID = "REG-PANTHEON-AGGREGATE-RUNTIME-PROMOTION-001"
ORDERED_STATES = [
    "PREPARED",
    "ACTOR_PROMOTED",
    "MANIFEST_WRITTEN",
    "STAGE_INSTALLED",
    "POSTCHECK_PASSED",
    "COMMITTED",
]
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class PromotionError(RuntimeError):
    """Promotion transaction failed closed."""


class PromotionCrashStop(RuntimeError):
    """Test seam used to stop after a durable state."""


@dataclass(frozen=True)
class PromotionRequest:
    source_repo: Path
    source_sha: str
    expected_origin: str
    actor_root: Path
    expected_current_actor_sha: str
    manifest_path: Path
    expected_current_manifest_digest: str
    private_stage_root: Path
    expected_current_stage_digest: str
    transaction_root: Path
    queue_root: Path
    publisher_state_root: Path
    log_root: Path
    target_identity: str
    target_runtime_digest: str
    target_config_version: str
    target_generation: str
    target_python_executable: Path
    authorization_digest: str
    capacity_receipt_path: Path
    capacity_receipt_digest: str
    correlation_id: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise PromotionError("capacity receipt is missing") from error


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(temporary_name)
    try:
        body = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
        os.write(descriptor, body)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PromotionError("transaction receipt is unreadable") from error
    if not isinstance(payload, dict):
        raise PromotionError("transaction receipt must be an object")
    return payload


def _read_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PromotionError(f"{label} is missing") from error
    except (OSError, json.JSONDecodeError) as error:
        raise PromotionError(f"{label} is invalid") from error
    if not isinstance(payload, dict):
        raise PromotionError(f"{label} must be an object")
    return payload


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise PromotionError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def tree_digest(root: Path) -> str:
    if not root.exists():
        return hashlib.sha256(b"missing").hexdigest()
    if not root.is_dir() or root.is_symlink():
        raise PromotionError("tree root must be a directory")
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def receipt_path(request: PromotionRequest) -> Path:
    return request.transaction_root / "promotion-receipt.json"


def rollback_bundle_path(request: PromotionRequest) -> Path:
    return request.transaction_root / "rollback-bundle"


def barrier_path(request: PromotionRequest) -> Path:
    return (
        request.publisher_state_root
        / f"four-lane-activation-{request.target_generation}.barrier"
    )


def _actor_backup_path(request: PromotionRequest) -> Path:
    return rollback_bundle_path(request) / "actor.previous"


def _manifest_backup_path(request: PromotionRequest) -> Path:
    return rollback_bundle_path(request) / "runtime-manifest.previous.json"


def _stage_backup_path(request: PromotionRequest) -> Path:
    return rollback_bundle_path(request) / "private-stage.previous"


def _barrier_backup_path(request: PromotionRequest) -> Path:
    return rollback_bundle_path(request) / "activation-barrier.previous"


def _canonical_existing_dir(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise PromotionError(f"{label} must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise PromotionError(f"{label} is missing") from error
    if resolved != path or path.is_symlink() or not resolved.is_dir():
        raise PromotionError(f"{label} must be a canonical directory")
    return resolved


def _canonical_file_parent(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise PromotionError(f"{label} must be absolute")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as error:
        raise PromotionError(f"{label} parent is missing") from error
    canonical = parent / path.name
    if path.exists() and (path.is_symlink() or path.resolve(strict=True) != canonical):
        raise PromotionError(f"{label} must use canonical realpath")
    return canonical


def _validate_request_shape(request: PromotionRequest) -> None:
    for field in (
        "source_sha",
        "expected_current_actor_sha",
    ):
        if SHA1_PATTERN.fullmatch(getattr(request, field)) is None:
            raise PromotionError(f"{field} must be exact git SHA")
    for field in (
        "expected_current_manifest_digest",
        "expected_current_stage_digest",
        "target_runtime_digest",
        "authorization_digest",
        "capacity_receipt_digest",
    ):
        if SHA256_PATTERN.fullmatch(getattr(request, field)) is None:
            raise PromotionError(f"{field} must be exact sha256")
    for field in ("target_generation", "correlation_id"):
        if SAFE_ID_PATTERN.fullmatch(getattr(request, field)) is None:
            raise PromotionError(f"{field} is invalid")
    if not request.expected_origin:
        raise PromotionError("expected origin is required")


def _validate_capacity_receipt(request: PromotionRequest) -> dict[str, Any]:
    if not request.capacity_receipt_path.is_absolute():
        raise PromotionError("capacity receipt path must be absolute")
    try:
        resolved = request.capacity_receipt_path.resolve(strict=True)
    except OSError as error:
        raise PromotionError("capacity receipt is missing") from error
    if (
        resolved != request.capacity_receipt_path
        or request.capacity_receipt_path.is_symlink()
        or not request.capacity_receipt_path.is_file()
    ):
        raise PromotionError("capacity receipt path must use canonical realpath")
    if file_sha256(request.capacity_receipt_path) != request.capacity_receipt_digest:
        raise PromotionError("capacity receipt digest mismatch")
    receipt = _read_json_file(request.capacity_receipt_path, "capacity receipt")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("regression_id") != "REG-PANTHEON-CAPACITY-WRITE-CYCLES-001"
        or receipt.get("status") != "PASS"
        or receipt.get("mode") != "bounded-synthetic-dry-run"
    ):
        raise PromotionError("capacity stop-loss is not PASS")
    cycles = receipt.get("cycles")
    if not isinstance(cycles, list) or len(cycles) < 2:
        raise PromotionError("capacity stop-loss is not PASS")
    if any(
        not isinstance(cycle, dict)
        or cycle.get("rss_available") is not True
        or cycle.get("swap_available") is not True
        for cycle in cycles
    ):
        raise PromotionError("capacity stop-loss is not PASS")
    reclamation = receipt.get("reclamation")
    if (
        not isinstance(reclamation, dict)
        or not isinstance(reclamation.get("bytes_before"), int)
        or not isinstance(reclamation.get("bytes_after"), int)
        or reclamation["bytes_after"] >= reclamation["bytes_before"]
    ):
        raise PromotionError("capacity stop-loss is not PASS")
    stop_loss = receipt.get("stop_loss")
    if (
        not isinstance(stop_loss, dict)
        or stop_loss.get("status") != "STOPPED"
        or stop_loss.get("triggered") is not True
        or stop_loss.get("remaining_loaded") != []
        or stop_loss.get("cross_project_deletions") != []
    ):
        raise PromotionError("capacity stop-loss is not PASS")
    return receipt


def _validate_path_boundaries(request: PromotionRequest) -> None:
    roots = [
        _canonical_existing_dir(request.source_repo, "source_repo"),
        _canonical_existing_dir(request.actor_root, "actor_root"),
        _canonical_existing_dir(request.queue_root, "queue_root"),
        _canonical_existing_dir(request.publisher_state_root, "publisher_state_root"),
        _canonical_existing_dir(request.log_root, "log_root"),
        _canonical_existing_dir(request.private_stage_root, "private_stage_root"),
    ]
    manifest = _canonical_file_parent(request.manifest_path, "manifest_path")
    if not request.transaction_root.is_absolute():
        raise PromotionError("transaction_root must be absolute")
    transaction_parent = request.transaction_root.parent.resolve(strict=True)
    transaction = transaction_parent / request.transaction_root.name
    for root in roots:
        if transaction == root or transaction.is_relative_to(root):
            raise PromotionError("transaction root overlaps managed runtime roots")
        if root == manifest.parent and root.name == manifest.name:
            raise PromotionError("manifest path overlaps a managed directory")


def _validate_git_identity(
    *,
    repo: Path,
    expected_sha: str,
    expected_origin: str,
    label: str,
) -> None:
    if _git(repo, "rev-parse", "HEAD") != expected_sha:
        raise PromotionError(f"{label} SHA drift")
    if _git(repo, "remote", "get-url", "origin") != expected_origin:
        raise PromotionError(f"{label} origin drift")
    if _git(repo, "status", "--porcelain"):
        raise PromotionError(f"{label} worktree is dirty")


def _target_manifest(request: PromotionRequest) -> dict[str, Any]:
    return runtime_manifest.build_manifest(
        actor_root=request.actor_root,
        queue_root=request.queue_root,
        publisher_state_root=request.publisher_state_root,
        log_root=request.log_root,
        identity=request.target_identity,
        runtime_digest=request.target_runtime_digest,
        config_version=request.target_config_version,
        generation=request.target_generation,
        actor_head=request.source_sha,
        python_executable=request.target_python_executable,
    )


def _plan_payload(request: PromotionRequest) -> dict[str, Any]:
    _validate_request_shape(request)
    _validate_path_boundaries(request)
    _validate_capacity_receipt(request)
    _validate_git_identity(
        repo=request.source_repo,
        expected_sha=request.source_sha,
        expected_origin=request.expected_origin,
        label="source",
    )
    _validate_git_identity(
        repo=request.actor_root,
        expected_sha=request.expected_current_actor_sha,
        expected_origin=request.expected_origin,
        label="actor",
    )
    current_manifest = runtime_manifest.load_manifest(
        request.manifest_path,
        request.expected_current_manifest_digest,
    )
    if current_manifest.get("actor_head") != request.expected_current_actor_sha:
        raise PromotionError("current manifest actor SHA drift")
    if tree_digest(request.private_stage_root) != request.expected_current_stage_digest:
        raise PromotionError("private stage digest drift")
    target_manifest = _target_manifest(request)
    write_set = [
        {"stage": "ACTOR_PROMOTED", "path": str(request.actor_root), "type": "actor"},
        {
            "stage": "MANIFEST_WRITTEN",
            "path": str(request.manifest_path),
            "type": "manifest",
            "digest": target_manifest["manifest_digest"],
        },
        {
            "stage": "STAGE_INSTALLED",
            "path": str(request.private_stage_root / "readiness" / request.target_generation),
            "type": "readiness_acknowledgements",
        },
        {
            "stage": "STAGE_INSTALLED",
            "path": str(barrier_path(request)),
            "type": "activation_barrier",
        },
    ]
    backup_set = [
        {"path": str(_actor_backup_path(request)), "source": str(request.actor_root)},
        {"path": str(_manifest_backup_path(request)), "source": str(request.manifest_path)},
        {"path": str(_stage_backup_path(request)), "source": str(request.private_stage_root)},
        {"path": str(_barrier_backup_path(request)), "source": str(barrier_path(request))},
    ]
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "status": "READY_TO_APPLY",
        "source_repo": str(request.source_repo),
        "target_actor_sha": request.source_sha,
        "expected_current_actor_sha": request.expected_current_actor_sha,
        "expected_origin": request.expected_origin,
        "actor_root": str(request.actor_root),
        "manifest_path": str(request.manifest_path),
        "target_manifest_digest": target_manifest["manifest_digest"],
        "private_stage_root": str(request.private_stage_root),
        "ordered_states": list(ORDERED_STATES),
        "write_set": write_set,
        "backup_set": backup_set,
        "rollback_order": ["STAGE_INSTALLED", "MANIFEST_WRITTEN", "ACTOR_PROMOTED"],
        "postchecks": [
            "actor_clean_head_origin",
            "manifest_digest_actor_head_generation",
            "private_stage_readiness_and_barrier",
            "queue_empty",
            "capacity_receipt_payload_stop_loss_pass",
        ],
        "authorization_digest": request.authorization_digest,
        "capacity_receipt_path": str(request.capacity_receipt_path),
        "capacity_receipt_digest": request.capacity_receipt_digest,
        "correlation_id": request.correlation_id,
    }
    plan["plan_digest"] = _json_digest(plan)
    return plan


def plan_promotion(request: PromotionRequest) -> dict[str, Any]:
    return _plan_payload(request)


def _new_receipt(
    request: PromotionRequest,
    plan: dict[str, Any],
    state: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "state": state,
        "plan_digest": plan["plan_digest"],
        "authorization_digest": request.authorization_digest,
        "capacity_receipt_digest": request.capacity_receipt_digest,
        "correlation_id": request.correlation_id,
        "target_manifest_digest": plan["target_manifest_digest"],
        "target_actor_sha": request.source_sha,
        "history": [{"state": state, "sampled_at": _utc_now()}],
    }


def _record_state(
    request: PromotionRequest,
    receipt: dict[str, Any],
    state: str,
    **extra: Any,
) -> None:
    receipt["state"] = state
    receipt["updated_at"] = _utc_now()
    receipt.update(extra)
    receipt.setdefault("history", []).append({"state": state, "sampled_at": _utc_now()})
    _write_json(receipt_path(request), receipt)


def load_receipt(request: PromotionRequest) -> dict[str, Any]:
    return _read_json(receipt_path(request))


def _ensure_no_existing_transaction(request: PromotionRequest) -> None:
    if receipt_path(request).exists():
        raise PromotionError("existing transaction requires status, rollback, or finalize")


def _prepare_rollback_bundle(request: PromotionRequest) -> None:
    bundle = rollback_bundle_path(request)
    if bundle.exists():
        raise PromotionError("rollback bundle already exists")
    bundle.mkdir(parents=True)
    if request.manifest_path.exists():
        _manifest_backup_path(request).write_bytes(request.manifest_path.read_bytes())
    if request.private_stage_root.exists():
        os.replace(request.private_stage_root, _stage_backup_path(request))
    if barrier_path(request).exists():
        os.replace(barrier_path(request), _barrier_backup_path(request))


def _promote_actor(request: PromotionRequest) -> None:
    stage = request.transaction_root / "actor.stage"
    if stage.exists():
        shutil.rmtree(stage)
    subprocess.run(
        ["git", "clone", "-q", "--no-checkout", str(request.source_repo), str(stage)],
        check=True,
    )
    _git(stage, "checkout", "-q", "--detach", request.source_sha)
    _git(stage, "remote", "set-url", "origin", request.expected_origin)
    _validate_git_identity(
        repo=stage,
        expected_sha=request.source_sha,
        expected_origin=request.expected_origin,
        label="staged actor",
    )
    os.replace(request.actor_root, _actor_backup_path(request))
    os.replace(stage, request.actor_root)


def _write_runtime_manifest(request: PromotionRequest) -> dict[str, Any]:
    manifest = _target_manifest(request)
    runtime_manifest.write_manifest(request.manifest_path, manifest)
    return manifest


def _install_private_stage(request: PromotionRequest, manifest: dict[str, Any]) -> None:
    ready_root = request.private_stage_root / "readiness" / request.target_generation
    ready_root.mkdir(parents=True)
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready_root, manifest, label)
    runtime_manifest.activate_barrier(barrier_path(request), ready_root, manifest)


def _postcheck(request: PromotionRequest, manifest: dict[str, Any]) -> None:
    _validate_git_identity(
        repo=request.actor_root,
        expected_sha=request.source_sha,
        expected_origin=request.expected_origin,
        label="promoted actor",
    )
    loaded = runtime_manifest.load_manifest(
        request.manifest_path,
        manifest["manifest_digest"],
        expected_python_executable=request.target_python_executable,
    )
    if (
        loaded.get("actor_head") != request.source_sha
        or loaded.get("generation") != request.target_generation
    ):
        raise PromotionError("target manifest postcheck failed")
    ready_root = request.private_stage_root / "readiness" / request.target_generation
    runtime_manifest.validate_barrier(barrier_path(request), manifest)
    if any(
        not (ready_root / f"{label}.json").is_file()
        for label in runtime_manifest.SERVICE_LABELS
    ):
        raise PromotionError("private stage readiness postcheck failed")
    _validate_capacity_receipt(request)
    for relative in ("runs", "gsc-copy"):
        root = request.queue_root / relative
        if not root.exists():
            continue
        if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
            raise PromotionError(f"queue residue present: {relative}")


def _restore_manifest(request: PromotionRequest) -> None:
    backup = _manifest_backup_path(request)
    if backup.exists():
        request.manifest_path.write_bytes(backup.read_bytes())
    else:
        request.manifest_path.unlink(missing_ok=True)


def _restore_stage(request: PromotionRequest) -> None:
    if request.private_stage_root.exists():
        shutil.rmtree(request.private_stage_root)
    if _stage_backup_path(request).exists():
        os.replace(_stage_backup_path(request), request.private_stage_root)
    barrier = barrier_path(request)
    barrier.unlink(missing_ok=True)
    if _barrier_backup_path(request).exists():
        os.replace(_barrier_backup_path(request), barrier)


def _restore_actor(request: PromotionRequest) -> None:
    backup = _actor_backup_path(request)
    if not backup.exists():
        return
    if request.actor_root.exists():
        shutil.rmtree(request.actor_root)
    os.replace(backup, request.actor_root)


def _rollback_from_state(request: PromotionRequest, state: str) -> None:
    _restore_stage(request)
    _restore_manifest(request)
    if state in {"ACTOR_PROMOTED", "MANIFEST_WRITTEN", "STAGE_INSTALLED", "POSTCHECK_PASSED"}:
        _restore_actor(request)


def _assert_receipt_matches(
    request: PromotionRequest,
    receipt: dict[str, Any],
    expected_plan_digest: str | None,
) -> None:
    if receipt.get("authorization_digest") != request.authorization_digest:
        raise PromotionError("authorization digest mismatch")
    if receipt.get("correlation_id") != request.correlation_id:
        raise PromotionError("correlation mismatch")
    if expected_plan_digest is not None and receipt.get("plan_digest") != expected_plan_digest:
        raise PromotionError("plan digest mismatch")


def apply_promotion(
    request: PromotionRequest,
    *,
    expected_plan_digest: str,
    failure_injection: str | None = None,
    stop_after_state: str | None = None,
) -> dict[str, Any]:
    _ensure_no_existing_transaction(request)
    plan = _plan_payload(request)
    if plan["plan_digest"] != expected_plan_digest:
        raise PromotionError("plan digest mismatch")
    request.transaction_root.mkdir(parents=True)
    receipt = _new_receipt(request, plan, "PREPARED")
    _write_json(receipt_path(request), receipt)
    state_before_rollback = "PREPARED"
    try:
        _prepare_rollback_bundle(request)
        if failure_injection == "actor":
            raise PromotionError("injected actor failure")
        _promote_actor(request)
        state_before_rollback = "ACTOR_PROMOTED"
        _record_state(request, receipt, "ACTOR_PROMOTED")
        if stop_after_state == "ACTOR_PROMOTED":
            raise PromotionCrashStop("stopped after ACTOR_PROMOTED")
        if failure_injection == "manifest":
            raise PromotionError("injected manifest failure")
        manifest = _write_runtime_manifest(request)
        state_before_rollback = "MANIFEST_WRITTEN"
        _record_state(request, receipt, "MANIFEST_WRITTEN")
        if stop_after_state == "MANIFEST_WRITTEN":
            raise PromotionCrashStop("stopped after MANIFEST_WRITTEN")
        if failure_injection == "stage":
            raise PromotionError("injected stage failure")
        _install_private_stage(request, manifest)
        state_before_rollback = "STAGE_INSTALLED"
        _record_state(request, receipt, "STAGE_INSTALLED")
        if stop_after_state == "STAGE_INSTALLED":
            raise PromotionCrashStop("stopped after STAGE_INSTALLED")
        if failure_injection == "postcheck":
            raise PromotionError("injected postcheck failure")
        _postcheck(request, manifest)
        _record_state(
            request,
            receipt,
            "POSTCHECK_PASSED",
            target_manifest_digest=manifest["manifest_digest"],
        )
        return {
            "status": "POSTCHECK_PASSED",
            "plan_digest": plan["plan_digest"],
            "target_manifest_digest": manifest["manifest_digest"],
            "rollback_bundle": str(rollback_bundle_path(request)),
        }
    except PromotionCrashStop:
        raise
    except Exception as error:
        _rollback_from_state(request, state_before_rollback)
        _record_state(
            request,
            receipt,
            "ROLLED_BACK",
            state_before_rollback=state_before_rollback,
            error=str(error),
            rollback_status="ROLLBACK_COMPLETE",
        )
        if isinstance(error, PromotionError):
            raise PromotionError(f"ROLLBACK_COMPLETE: {error}") from error
        raise PromotionError(f"ROLLBACK_COMPLETE: {error}") from error


def status_promotion(request: PromotionRequest) -> dict[str, Any]:
    path = receipt_path(request)
    if not path.exists():
        return {"status": "NOT_STARTED", "state": "NOT_STARTED"}
    receipt = _read_json(path)
    state = str(receipt.get("state", "UNKNOWN"))
    return {
        "status": "PASS",
        "state": state,
        "plan_digest": receipt.get("plan_digest"),
        "correlation_id": receipt.get("correlation_id"),
        "rollback_required": state
        in {"ACTOR_PROMOTED", "MANIFEST_WRITTEN", "STAGE_INSTALLED", "POSTCHECK_PASSED"},
        "audit_receipt_exists": path.exists(),
        "rollback_bundle_exists": rollback_bundle_path(request).exists(),
    }


def rollback_promotion(
    request: PromotionRequest,
    *,
    expected_plan_digest: str | None = None,
) -> dict[str, Any]:
    receipt = load_receipt(request)
    _assert_receipt_matches(request, receipt, expected_plan_digest)
    state = str(receipt.get("state", "UNKNOWN"))
    if state in {"COMMITTED", "ROLLED_BACK"}:
        raise PromotionError(f"transaction is already {state}")
    _rollback_from_state(request, state)
    _record_state(
        request,
        receipt,
        "ROLLED_BACK",
        state_before_rollback=state,
        rollback_status="ROLLBACK_COMPLETE",
    )
    return {"status": "ROLLED_BACK", "plan_digest": receipt["plan_digest"]}


def finalize_promotion(
    request: PromotionRequest,
    *,
    expected_plan_digest: str | None = None,
) -> dict[str, Any]:
    receipt = load_receipt(request)
    _assert_receipt_matches(request, receipt, expected_plan_digest)
    if receipt.get("state") != "POSTCHECK_PASSED":
        raise PromotionError("finalize requires POSTCHECK_PASSED")
    bundle = rollback_bundle_path(request)
    if not bundle.exists():
        raise PromotionError("rollback bundle is missing")
    shutil.rmtree(bundle)
    _record_state(request, receipt, "COMMITTED", rollback_bundle_finalized=True)
    return {"status": "COMMITTED", "plan_digest": receipt["plan_digest"]}


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--expected-origin", required=True)
    parser.add_argument("--actor-root", type=Path, required=True)
    parser.add_argument("--expected-current-actor-sha", required=True)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--expected-current-manifest-digest", required=True)
    parser.add_argument("--private-stage-root", type=Path, required=True)
    parser.add_argument("--expected-current-stage-digest", required=True)
    parser.add_argument("--transaction-root", type=Path, required=True)
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--publisher-state-root", type=Path, required=True)
    parser.add_argument("--log-root", type=Path, required=True)
    parser.add_argument("--target-identity", required=True)
    parser.add_argument("--target-runtime-digest", required=True)
    parser.add_argument("--target-config-version", required=True)
    parser.add_argument("--target-generation", required=True)
    parser.add_argument("--target-python-executable", type=Path, required=True)
    parser.add_argument("--authorization-digest", required=True)
    parser.add_argument("--capacity-receipt", type=Path, required=True)
    parser.add_argument("--capacity-receipt-digest", required=True)
    parser.add_argument("--correlation-id", required=True)


def _request_from_args(args: argparse.Namespace) -> PromotionRequest:
    return PromotionRequest(
        source_repo=args.source_repo,
        source_sha=args.source_sha,
        expected_origin=args.expected_origin,
        actor_root=args.actor_root,
        expected_current_actor_sha=args.expected_current_actor_sha,
        manifest_path=args.manifest_path,
        expected_current_manifest_digest=args.expected_current_manifest_digest,
        private_stage_root=args.private_stage_root,
        expected_current_stage_digest=args.expected_current_stage_digest,
        transaction_root=args.transaction_root,
        queue_root=args.queue_root,
        publisher_state_root=args.publisher_state_root,
        log_root=args.log_root,
        target_identity=args.target_identity,
        target_runtime_digest=args.target_runtime_digest,
        target_config_version=args.target_config_version,
        target_generation=args.target_generation,
        target_python_executable=args.target_python_executable,
        authorization_digest=args.authorization_digest,
        capacity_receipt_path=args.capacity_receipt,
        capacity_receipt_digest=args.capacity_receipt_digest,
        correlation_id=args.correlation_id,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply", "rollback", "finalize", "status"):
        command = subparsers.add_parser(name)
        _add_common_arguments(command)
        if name in {"rollback", "finalize"}:
            command.add_argument("--expected-plan-digest", required=True)
        if name == "apply":
            command.add_argument("--expected-plan-digest", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    request = _request_from_args(args)
    try:
        if args.command == "plan":
            result = plan_promotion(request)
        elif args.command == "apply":
            result = apply_promotion(
                request,
                expected_plan_digest=args.expected_plan_digest,
            )
        elif args.command == "rollback":
            result = rollback_promotion(
                request,
                expected_plan_digest=args.expected_plan_digest,
            )
        elif args.command == "finalize":
            result = finalize_promotion(
                request,
                expected_plan_digest=args.expected_plan_digest,
            )
        else:
            result = status_promotion(request)
    except (PromotionError, runtime_manifest.RuntimeManifestError) as error:
        print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

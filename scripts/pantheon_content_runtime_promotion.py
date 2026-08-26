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
PRESERVABLE_RUN_STATUSES = {"active", "complete", "failed"}
RUN_IDENTITY_SCHEMA_VERSION = 1


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
    preserved_run_ids: tuple[str, ...] = ()
    target_uv_executable: Path | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical_json_sha256(payload: object) -> str:
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _read_json_value_file(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PromotionError(f"{label} is missing") from error
    except (OSError, json.JSONDecodeError) as error:
        raise PromotionError(f"{label} is invalid") from error


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


def _canonical_queue_child_file(queue_root: Path, path: Path, label: str) -> Path:
    canonical_queue_root = _canonical_existing_dir(queue_root, "queue_root")
    if not path.is_absolute():
        raise PromotionError(f"{label} must be absolute")
    try:
        relative = path.relative_to(canonical_queue_root)
    except ValueError as error:
        raise PromotionError(f"{label} is invalid") from error
    if relative.parts == () or ".." in relative.parts:
        raise PromotionError(f"{label} is invalid")
    current = canonical_queue_root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise PromotionError(f"{label} is invalid")
        try:
            resolved = current.resolve(strict=True)
        except OSError as error:
            raise PromotionError(f"{label} is missing") from error
        if resolved != current or not resolved.is_dir():
            raise PromotionError(f"{label} is invalid")
    if path.is_symlink():
        raise PromotionError(f"{label} is invalid")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise PromotionError(f"{label} is missing") from error
    if resolved != path or not resolved.is_file():
        raise PromotionError(f"{label} is invalid")
    return path


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
    if (
        tuple(sorted(set(request.preserved_run_ids))) != request.preserved_run_ids
        or any(SAFE_ID_PATTERN.fullmatch(run_id) is None for run_id in request.preserved_run_ids)
    ):
        raise PromotionError("preserved run ids are invalid")


def _validated_run_identity_envelope_value(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "mode",
        "lane",
        "article_ids",
        "digest",
    }:
        raise PromotionError("preserved run identity envelope is missing or invalid")
    if value.get("schema_version") != RUN_IDENTITY_SCHEMA_VERSION:
        raise PromotionError("preserved run identity envelope is missing or invalid")
    mode = value.get("mode")
    lane = value.get("lane")
    valid_lanes = {
        "create": {"new"},
        "rewrite_existing_body": {"rewrite"},
        "translate_existing": {"i18n-new", "i18n-rewrite"},
    }
    if type(mode) is not str or type(lane) is not str or lane not in valid_lanes.get(mode, set()):
        raise PromotionError("preserved run identity envelope is missing or invalid")
    article_ids = value.get("article_ids")
    if (
        not isinstance(article_ids, list)
        or any(type(article_id) is not str or not article_id or article_id.strip() != article_id for article_id in article_ids)
        or article_ids != sorted(set(article_ids))
    ):
        raise PromotionError("preserved run identity envelope is missing or invalid")
    identity = {
        "schema_version": RUN_IDENTITY_SCHEMA_VERSION,
        "mode": mode,
        "lane": lane,
        "article_ids": article_ids,
    }
    digest = hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if value.get("digest") != digest:
        raise PromotionError("preserved run identity envelope digest mismatch")
    return {**identity, "digest": digest}


def _validate_run_identity_matches_brief(
    identity: dict[str, Any],
    brief: dict[str, Any],
    state_lane: object = None,
) -> None:
    mode = identity["mode"]
    lane = identity["lane"]
    article_ids = identity["article_ids"]
    if brief.get("mode") != mode:
        raise PromotionError("preserved run brief identity mismatch")
    observed_ids: list[str] = []
    articles = brief.get("articles")
    if not isinstance(articles, list):
        raise PromotionError("preserved run brief identity mismatch")
    for article in articles:
        if not isinstance(article, dict):
            raise PromotionError("preserved run brief identity mismatch")
        value_id: object = None
        if mode == "create":
            target = article.get("target")
            value_id = target.get("id") if isinstance(target, dict) else article.get("id")
        elif mode == "rewrite_existing_body":
            value_id = article.get("article_id")
        elif mode == "translate_existing":
            value_id = article.get("source_article_id")
        if type(value_id) is not str or not value_id or value_id.strip() != value_id:
            raise PromotionError("preserved run brief identity mismatch")
        observed_ids.append(value_id)
    if sorted(observed_ids) != article_ids or len(observed_ids) != len(set(observed_ids)):
        raise PromotionError("preserved run brief identity mismatch")
    brief_lane = brief.get("lane")
    expected_brief_lane = {
        "create": "new",
        "rewrite_existing_body": "rewrite",
    }.get(mode, brief_lane)
    if mode == "translate_existing" and type(brief_lane) is not str:
        expected_brief_lane = state_lane
    if expected_brief_lane != lane:
        raise PromotionError("preserved run brief identity mismatch")


def _validated_run_identity_envelope(
    value: object,
    brief: dict[str, Any],
    state_lane: object = None,
) -> dict[str, Any]:
    identity = _validated_run_identity_envelope_value(value)
    _validate_run_identity_matches_brief(identity, brief, state_lane)
    return identity


def _run_identity_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    mode = brief.get("mode")
    lane = brief.get("lane")
    if mode == "create":
        lane = "new"
    elif mode == "rewrite_existing_body":
        lane = "rewrite"
    articles = brief.get("articles")
    if type(mode) is not str or type(lane) is not str or not isinstance(articles, list):
        raise PromotionError("preserved run brief identity mismatch")
    article_ids: list[str] = []
    for article in articles:
        if not isinstance(article, dict):
            raise PromotionError("preserved run brief identity mismatch")
        value_id: object = None
        if mode == "create":
            target = article.get("target")
            value_id = target.get("id") if isinstance(target, dict) else article.get("id")
        elif mode == "rewrite_existing_body":
            value_id = article.get("article_id")
        elif mode == "translate_existing":
            value_id = article.get("source_article_id")
        else:
            raise PromotionError("preserved run brief identity mismatch")
        if type(value_id) is not str or not value_id or value_id.strip() != value_id:
            raise PromotionError("preserved run brief identity mismatch")
        article_ids.append(value_id)
    identity = _validated_run_identity_envelope_value(
        {
            "schema_version": RUN_IDENTITY_SCHEMA_VERSION,
            "mode": mode,
            "lane": lane,
            "article_ids": sorted(article_ids),
            "digest": hashlib.sha256(
                json.dumps(
                    {
                        "schema_version": RUN_IDENTITY_SCHEMA_VERSION,
                        "mode": mode,
                        "lane": lane,
                        "article_ids": sorted(article_ids),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
    )
    _validate_run_identity_matches_brief(identity, brief)
    return identity


def _validated_ledger_article_ids(value: object) -> list[str]:
    if (
        not isinstance(value, list)
        or any(
            type(article_id) is not str
            or not article_id
            or article_id.strip() != article_id
            for article_id in value
        )
        or value != sorted(set(value))
    ):
        raise PromotionError("publisher ledger identity mismatch")
    return value


def _publisher_ledger_evidence(
    request: PromotionRequest,
    run_id: str,
) -> dict[str, Any] | None:
    ledger_path = request.publisher_state_root / "ledger.json"
    if not ledger_path.exists():
        return None
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise PromotionError("publisher ledger is invalid")
    ledger = _read_json_file(ledger_path, "publisher ledger")
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise PromotionError("publisher ledger is invalid")
    ledger_keys = {
        "published_runs": ("create", "new", "published"),
        "rewrite_released_runs": ("rewrite_existing_body", "rewrite", "released"),
        "translation_published_runs": (
            "translate_existing",
            None,
            "published_translation",
        ),
        "superseded_runs": ("create", "new", "superseded_create"),
    }
    matched: list[dict[str, Any]] = []
    for key, (expected_mode, expected_lane, lifecycle) in ledger_keys.items():
        entries = ledger.get(key, [])
        if not isinstance(entries, list):
            raise PromotionError("publisher ledger is invalid")
        seen = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise PromotionError("publisher ledger is invalid")
            if entry.get("run_id") != run_id:
                continue
            seen += 1
            matched.append(
                {
                    "mode": expected_mode,
                    "lane": expected_lane,
                    "article_ids": _validated_ledger_article_ids(
                        entry.get("article_ids")
                    ),
                    "lifecycle": lifecycle,
                }
            )
        if seen > 1:
            raise PromotionError("publisher ledger identity mismatch")
    if len(matched) > 1:
        raise PromotionError("publisher ledger lifecycle conflict")
    if matched:
        return matched[0]
    return None


def _publisher_ledger_lifecycle(
    request: PromotionRequest,
    run_id: str,
    identity: dict[str, Any],
) -> str | None:
    evidence = _publisher_ledger_evidence(request, run_id)
    if evidence is None:
        return None
    if (
        identity["mode"] != evidence["mode"]
        or identity["article_ids"] != evidence["article_ids"]
    ):
        raise PromotionError("publisher ledger identity mismatch")
    return str(evidence["lifecycle"])


def _validated_ledger_history_identity(
    run_id: str,
    brief: dict[str, Any],
    ledger_evidence: dict[str, Any],
) -> dict[str, Any]:
    if brief.get("run_id") != run_id or brief.get("mode") != ledger_evidence["mode"]:
        raise PromotionError("publisher ledger identity mismatch")
    articles = brief.get("articles")
    if not isinstance(articles, list):
        raise PromotionError("publisher ledger identity mismatch")
    observed_ids: list[str] = []
    for article in articles:
        if not isinstance(article, dict):
            raise PromotionError("publisher ledger identity mismatch")
        value_id: object = None
        if ledger_evidence["mode"] == "create":
            target = article.get("target")
            value_id = target.get("id") if isinstance(target, dict) else article.get("id")
        elif ledger_evidence["mode"] == "rewrite_existing_body":
            value_id = article.get("article_id")
        elif ledger_evidence["mode"] == "translate_existing":
            value_id = article.get("source_article_id")
        if type(value_id) is not str or not value_id or value_id.strip() != value_id:
            raise PromotionError("publisher ledger identity mismatch")
        observed_ids.append(value_id)
    if (
        sorted(observed_ids) != ledger_evidence["article_ids"]
        or len(observed_ids) != len(set(observed_ids))
    ):
        raise PromotionError("publisher ledger identity mismatch")
    lane = brief.get("lane")
    if type(lane) is not str:
        lane = ledger_evidence["lane"]
    return {
        "mode": ledger_evidence["mode"],
        "lane": lane,
        "article_ids": list(ledger_evidence["article_ids"]),
    }


def _terminalized_dangling_active_identity(
    request: PromotionRequest,
    run_id: str,
    run_dir: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    if run_dir.resolve(strict=False) != run_dir or run_dir.exists() or run_dir.is_symlink():
        raise PromotionError("preserved run directory is invalid")
    binding = state.get("dangling_active_terminalization")
    if type(binding) is not dict or set(binding) != {
        "receipt",
        "reason",
        "before_digest",
    }:
        raise PromotionError("terminalization receipt is missing")
    receipt_relative = binding.get("receipt")
    reason = binding.get("reason")
    before_digest = binding.get("before_digest")
    expected_receipt = f"dangling-active-terminalizations/{run_id}.json"
    if (
        receipt_relative != expected_receipt
        or reason != "UNRECOVERABLE_RUN_DIR_MISSING"
        or type(before_digest) is not str
        or SHA256_PATTERN.fullmatch(before_digest) is None
    ):
        raise PromotionError("terminalization receipt identity mismatch")
    receipt_path = request.queue_root / expected_receipt
    receipt_path = _canonical_queue_child_file(
        request.queue_root,
        receipt_path,
        "terminalization receipt",
    )
    receipt = _read_json_file(receipt_path, "terminalization receipt")
    before = receipt.get("before")
    after = receipt.get("after")
    if type(before) is not dict or type(after) is not dict:
        raise PromotionError("terminalization receipt identity mismatch")
    if (
        receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("status") != "terminalized"
        or receipt.get("action") != "terminalize_dangling_active"
        or receipt.get("run_id") != run_id
        or receipt.get("run_dir") != str(run_dir)
        or receipt.get("reason") != reason
        or receipt.get("before_digest") != before_digest
        or receipt.get("after_digest") != _canonical_json_sha256(state)
        or receipt.get("after_digest") != _canonical_json_sha256(after)
        or _canonical_json_sha256(before) != before_digest
        or before.get("status") != "active"
        or before.get("run_id") != run_id
        or before.get("run_dir") != str(run_dir)
        or after != state
        or state.get("status") != "failed"
        or state.get("run_id") != run_id
        or state.get("run_dir") != str(run_dir)
        or state.get("error_type") != "DanglingActiveRunTerminalized"
        or state.get("dangling_active_terminalization")
        != {
            "receipt": expected_receipt,
            "reason": reason,
            "before_digest": before_digest,
        }
    ):
        raise PromotionError("terminalization receipt identity mismatch")
    return {
        "mode": "terminal_abandoned",
        "lane": "terminal-abandoned",
        "article_ids": [],
    }


def _candidate_durable_roots(
    request: PromotionRequest,
    identity: dict[str, Any],
) -> list[Path]:
    if identity["mode"] == "translate_existing":
        roots = [request.queue_root / "translation-runs"]
    else:
        roots = [request.queue_root / "gsc-copy", request.queue_root.parent / "gsc-copy"]
    deduped: list[Path] = []
    for root in roots:
        if root not in deduped:
            deduped.append(root)
    return deduped


def _canonical_durable_root_for_run(
    request: PromotionRequest,
    identity: dict[str, Any],
    canonical_run_dir: Path,
) -> Path:
    for root in _candidate_durable_roots(request, identity):
        if not root.exists():
            continue
        if root.is_symlink() or not root.is_dir():
            raise PromotionError("preserved durable run root is invalid")
        canonical_root = root.resolve(strict=True)
        if canonical_run_dir != canonical_root and canonical_run_dir.is_relative_to(canonical_root):
            return canonical_root
    raise PromotionError("preserved run directory is outside durable root")


def _queue_owned_durable_root_for_run(
    request: PromotionRequest,
    identity: dict[str, Any],
    canonical_run_dir: Path,
) -> Path:
    root = (
        request.queue_root / "translation-runs"
        if identity["mode"] == "translate_existing"
        else request.queue_root / "gsc-copy"
    )
    if root.is_symlink() or not root.is_dir():
        raise PromotionError("preserved durable run root is invalid")
    canonical_root = root.resolve(strict=True)
    if canonical_run_dir != canonical_root and canonical_run_dir.is_relative_to(canonical_root):
        return canonical_root
    raise PromotionError("preserved run directory is outside durable root")


def _preserved_lifecycle(
    *,
    request: PromotionRequest,
    run_id: str,
    status: str,
    identity: dict[str, Any],
    identity_source: str,
    canonical_run_dir: Path | None,
) -> dict[str, Any]:
    ledger_lifecycle = _publisher_ledger_lifecycle(request, run_id, identity)
    if ledger_lifecycle is not None and status != "complete":
        raise PromotionError("publisher ledger lifecycle conflict")
    if canonical_run_dir is None:
        lifecycle = (
            "terminal_abandoned"
            if identity["mode"] == "terminal_abandoned"
            else "terminal_failed_tombstone"
        )
        durable_root: Path | None = None
    else:
        durable_root = _canonical_durable_root_for_run(request, identity, canonical_run_dir)
        if ledger_lifecycle is not None:
            lifecycle = ledger_lifecycle
        elif identity["mode"] == "translate_existing":
            lifecycle = "durable_translation"
        elif status == "failed":
            lifecycle = "terminal_failed_artifact"
        elif identity["mode"] == "create" and status == "complete":
            lifecycle = "create_candidate"
        elif identity["mode"] == "rewrite_existing_body" and status == "complete":
            lifecycle = "rewrite_candidate"
        else:
            lifecycle = f"{status}_preserved"
    return {
        "mode": identity["mode"],
        "lane": identity["lane"],
        "article_ids": list(identity["article_ids"]),
        "identity_source": identity_source,
        "status": status,
        "lifecycle": lifecycle,
        "run_dir_exists": canonical_run_dir is not None,
        "durable_root": str(durable_root) if durable_root is not None else None,
        "operational_selection": lifecycle == "rewrite_candidate",
    }


def _gsc_copy_identity_snapshot(queue_root: Path) -> list[dict[str, Any]]:
    root = queue_root / "gsc-copy"
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        raise PromotionError("gsc-copy snapshot is invalid")
    snapshot: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise PromotionError("gsc-copy snapshot contains symlink")
        if path.is_dir():
            snapshot.append({"path": relative, "type": "dir"})
            continue
        if not path.is_file():
            raise PromotionError("gsc-copy snapshot contains unexpected residue")
        if path.suffix == ".json":
            _read_json_value_file(path, "gsc-copy JSON")
        snapshot.append(
            {
                "path": relative,
                "type": "file",
                "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return snapshot


def _queue_identity_snapshot(request: PromotionRequest) -> dict[str, Any]:
    runs_root = request.queue_root / "runs"
    if not request.preserved_run_ids:
        for relative in ("runs", "gsc-copy"):
            root = request.queue_root / relative
            if root.exists() and (
                root.is_symlink() or not root.is_dir() or any(root.iterdir())
            ):
                raise PromotionError(f"queue residue present: {relative}")
        return {"preserved_runs": [], "gsc_copy": []}
    if runs_root.is_symlink() or not runs_root.is_dir():
        raise PromotionError("preserved run registry is invalid")
    observed: set[str] = set()
    preserved_runs: list[dict[str, str]] = []
    preservation_classification: dict[str, dict[str, Any]] = {}
    for path in runs_root.iterdir():
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise PromotionError("preserved run registry contains unexpected residue")
        state = _read_json_file(path, "preserved run state")
        run_id = state.get("run_id")
        status = state.get("status")
        if (
            type(run_id) is not str
            or SAFE_ID_PATTERN.fullmatch(run_id) is None
            or status not in PRESERVABLE_RUN_STATUSES
        ):
            raise PromotionError("preserved run state is not preservable")
        if run_id in observed:
            raise PromotionError("preserved run registry contains duplicate identity")
        run_dir_value = state.get("run_dir")
        if type(run_dir_value) is not str:
            raise PromotionError("preserved run directory is invalid")
        run_dir = Path(run_dir_value)
        if not run_dir.is_absolute():
            raise PromotionError("preserved run directory is invalid")
        try:
            canonical_run_dir = run_dir.resolve(strict=True)
        except OSError as error:
            if status != "failed":
                raise PromotionError("preserved run directory is missing") from error
            canonical_run_dir = None
            if state.get("identity_envelope") is None:
                identity = _terminalized_dangling_active_identity(
                    request,
                    run_id,
                    run_dir,
                    state,
                )
                identity_source = "terminalization_receipt"
            else:
                identity = _validated_run_identity_envelope_value(
                    state.get("identity_envelope")
                )
                identity_source = "current_identity_envelope"
        else:
            if run_dir.is_symlink() or not run_dir.is_dir() or canonical_run_dir != run_dir:
                raise PromotionError("preserved run directory is outside durable root")
            brief_path = canonical_run_dir / "brief.json"
            if brief_path.is_symlink() or not brief_path.is_file():
                raise PromotionError("preserved run brief is missing")
            brief = _read_json_file(brief_path, "preserved run brief")
            if brief.get("run_id") != run_id:
                raise PromotionError("preserved run brief identity mismatch")
            brief_mode = brief.get("mode")
            if type(brief_mode) is not str:
                raise PromotionError("preserved run brief identity mismatch")
            _canonical_durable_root_for_run(request, {"mode": brief_mode}, canonical_run_dir)
            ledger_evidence = _publisher_ledger_evidence(request, run_id)
            if status == "complete" and ledger_evidence is not None:
                identity = _validated_ledger_history_identity(
                    run_id,
                    brief,
                    ledger_evidence,
                )
                identity_source = "publisher_ledger"
            elif status == "failed" and state.get("identity_envelope") is None:
                identity = _run_identity_from_brief(brief)
                _queue_owned_durable_root_for_run(request, identity, canonical_run_dir)
                identity_source = "terminal_brief_reconstruction"
            else:
                identity = _validated_run_identity_envelope(
                    state.get("identity_envelope"),
                    brief,
                    state.get("lane"),
                )
                identity_source = "current_identity_envelope"
            _canonical_durable_root_for_run(request, identity, canonical_run_dir)
        observed.add(run_id)
        preserved_runs.append(
            {
                "path": path.name,
                "run_id": run_id,
                "run_dir": str(canonical_run_dir) if canonical_run_dir is not None else str(run_dir),
                "run_tree_digest": (
                    tree_digest(canonical_run_dir)
                    if canonical_run_dir is not None
                    else hashlib.sha256(b"missing").hexdigest()
                ),
                "status": str(status),
            }
        )
        preservation_classification[run_id] = _preserved_lifecycle(
            request=request,
            run_id=run_id,
            status=str(status),
            identity=identity,
            identity_source=identity_source,
            canonical_run_dir=canonical_run_dir,
        )
    if observed != set(request.preserved_run_ids):
        raise PromotionError("preserved run identity mismatch")
    return {
        "preserved_runs": sorted(
            preserved_runs,
            key=lambda entry: (entry["run_id"], entry["path"]),
        ),
        "preservation_classification": dict(sorted(preservation_classification.items())),
        "gsc_copy": _gsc_copy_identity_snapshot(request.queue_root),
    }


def _validate_preserved_runs(request: PromotionRequest) -> None:
    _queue_identity_snapshot(request)


def _queue_snapshot_digest(queue_root: Path) -> str:
    if not queue_root.exists():
        return _json_digest({"root": "missing", "entries": []})
    if not queue_root.is_dir() or queue_root.is_symlink():
        raise PromotionError("queue snapshot root must be a directory")
    entries: list[dict[str, Any]] = [{"path": ".", "type": "dir"}]
    for path in sorted(
        queue_root.rglob("*"),
        key=lambda item: item.relative_to(queue_root).as_posix(),
    ):
        relative = path.relative_to(queue_root).as_posix()
        if path.is_symlink():
            raise PromotionError("queue snapshot contains symlink")
        if path.is_dir():
            entries.append({"path": relative, "type": "dir"})
            continue
        if not path.is_file():
            raise PromotionError("queue snapshot contains unexpected residue")
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise PromotionError("queue snapshot changed during read") from error
        entries.append({"path": relative, "type": "file", "digest": digest})
    return _json_digest({"root": "dir", "entries": entries})


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
    actor_root = roots[1]
    queue_root = roots[2]
    if queue_root == actor_root or queue_root.is_relative_to(actor_root):
        raise PromotionError("queue root is actor-local and cannot survive promotion")
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
    if request.target_uv_executable is None:
        raise PromotionError("target uv executable is required")
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
        uv_executable=request.target_uv_executable,
    )


def _plan_payload(request: PromotionRequest) -> dict[str, Any]:
    _validate_request_shape(request)
    _validate_path_boundaries(request)
    _validate_capacity_receipt(request)
    queue_identity_snapshot = _queue_identity_snapshot(request)
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
            "queue_preserved" if request.preserved_run_ids else "queue_empty",
            "capacity_receipt_payload_stop_loss_pass",
        ],
        "authorization_digest": request.authorization_digest,
        "capacity_receipt_path": str(request.capacity_receipt_path),
        "capacity_receipt_digest": request.capacity_receipt_digest,
        "correlation_id": request.correlation_id,
        "preserved_run_ids": list(request.preserved_run_ids),
        "queue_identity_snapshot": queue_identity_snapshot,
        "queue_snapshot_digest": _queue_snapshot_digest(request.queue_root),
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


def _postcheck(
    request: PromotionRequest,
    manifest: dict[str, Any],
    plan: dict[str, Any],
) -> None:
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
        expected_uv_executable=request.target_uv_executable,
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
    if _queue_identity_snapshot(request) != plan["queue_identity_snapshot"]:
        raise PromotionError("queue identity changed during promotion")
    if _queue_snapshot_digest(request.queue_root) != plan["queue_snapshot_digest"]:
        raise PromotionError("queue changed during promotion")


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
        _postcheck(request, manifest, plan)
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
    parser.add_argument("--target-uv-executable", type=Path, required=True)
    parser.add_argument("--authorization-digest", required=True)
    parser.add_argument("--capacity-receipt", type=Path, required=True)
    parser.add_argument("--capacity-receipt-digest", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--preserve-run-id", action="append", default=[])


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
        preserved_run_ids=tuple(args.preserve_run_id),
        target_uv_executable=args.target_uv_executable,
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

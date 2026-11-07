#!/usr/bin/env python3
"""Pantheon runtime actor/manifest/stage aggregate promotion transaction."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import plistlib
import fcntl
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
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
PROMOTION_GIT_TAG_POLICY = "DISABLED"


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


@dataclass(frozen=True)
class LedgerCollectionDescriptor:
    key: str
    mode: str
    lane: str | None
    lifecycle: str
    identity_field: str
    cardinality: str


LEDGER_COLLECTION_DESCRIPTORS = (
    LedgerCollectionDescriptor("published_runs", "create", "new", "published", "article_ids", "many"),
    LedgerCollectionDescriptor("rewrite_released_runs", "rewrite_existing_body", "rewrite", "released", "article_ids", "many"),
    LedgerCollectionDescriptor("translation_published_runs", "translate_existing", None, "published_translation", "article_id", "one"),
    LedgerCollectionDescriptor("superseded_runs", "create", "new", "superseded_create", "article_ids", "many"),
)


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
        remaining = memoryview(body)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("receipt write made no progress")
            remaining = remaining[written:]
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
        pass_fds=runtime_manifest.runtime_work_pass_fds(),
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


def _validated_ledger_article_id(value: object) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise PromotionError("publisher ledger identity mismatch")
    return value


def _validated_ledger_article_ids(value: object) -> tuple[str, ...]:
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
    return tuple(value)


def _canonical_ledger_article_ids(
    entry: dict[str, Any],
    descriptor: LedgerCollectionDescriptor,
) -> tuple[str, ...]:
    if descriptor.identity_field == "article_id" and descriptor.cardinality == "one":
        if "article_ids" in entry:
            raise PromotionError("publisher ledger identity mismatch")
        return (_validated_ledger_article_id(entry.get("article_id")),)
    if descriptor.identity_field == "article_ids" and descriptor.cardinality == "many":
        if "article_id" in entry:
            raise PromotionError("publisher ledger identity mismatch")
        return _validated_ledger_article_ids(entry.get("article_ids"))
    raise PromotionError("publisher ledger is invalid")


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
    matched: list[dict[str, Any]] = []
    for descriptor in LEDGER_COLLECTION_DESCRIPTORS:
        entries = ledger.get(descriptor.key, [])
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
                    "mode": descriptor.mode,
                    "lane": descriptor.lane,
                    "article_ids": list(
                        _canonical_ledger_article_ids(entry, descriptor)
                    ),
                    "lifecycle": descriptor.lifecycle,
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
    *,
    published_queue_input: bool = False,
) -> Path:
    roots = _candidate_durable_roots(request, identity)
    # 已發布 immutable input 由 complete registry＋matching Publisher ledger 擁有。
    # 原正式 register/publish 接受 queue-owned input，不要求位於 gsc-copy。
    if published_queue_input:
        roots.append(request.queue_root)
    for root in roots:
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
        durable_root = _canonical_durable_root_for_run(
            request, identity, canonical_run_dir,
            published_queue_input=(status == "complete" and ledger_lifecycle == "published"
                                   and identity_source == "publisher_ledger"),
        )
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
            ledger_evidence = _publisher_ledger_evidence(request, run_id)
            _canonical_durable_root_for_run(
                request, {"mode": brief_mode}, canonical_run_dir,
                published_queue_input=(status == "complete" and ledger_evidence is not None
                                       and ledger_evidence["lifecycle"] == "published"),
            )
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
            _canonical_durable_root_for_run(
                request, identity, canonical_run_dir,
                published_queue_input=(status == "complete" and ledger_evidence is not None
                                       and ledger_evidence["lifecycle"] == "published"
                                       and identity_source == "publisher_ledger"),
            )
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


def _plan_authority_payload(
    request: PromotionRequest,
    *,
    target_manifest: dict[str, Any],
    queue_identity_snapshot: dict[str, Any],
    queue_snapshot_digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "status": "READY_TO_APPLY",
        "source": {
            "sha": request.source_sha,
            "expected_origin": request.expected_origin,
        },
        "current_runtime": {
            "actor_sha": request.expected_current_actor_sha,
            "manifest_digest": request.expected_current_manifest_digest,
            "stage_digest": request.expected_current_stage_digest,
        },
        "target_runtime": {
            "identity": request.target_identity,
            "runtime_digest": request.target_runtime_digest,
            "config_version": request.target_config_version,
            "generation": request.target_generation,
            "manifest_digest": target_manifest["manifest_digest"],
            "python_executable": str(request.target_python_executable),
            "uv_executable": str(request.target_uv_executable),
        },
        "ordered_states": list(ORDERED_STATES),
        "write_set_authority": [
            {"stage": "ACTOR_PROMOTED", "type": "actor"},
            {
                "stage": "MANIFEST_WRITTEN",
                "type": "manifest",
                "digest": target_manifest["manifest_digest"],
            },
            {"stage": "STAGE_INSTALLED", "type": "readiness_acknowledgements"},
            {"stage": "STAGE_INSTALLED", "type": "activation_barrier"},
        ],
        "rollback_order": ["STAGE_INSTALLED", "MANIFEST_WRITTEN", "ACTOR_PROMOTED"],
        "postchecks": [
            "actor_clean_head_origin",
            "manifest_digest_actor_head_generation",
            "private_stage_readiness_and_barrier",
            "queue_preserved" if request.preserved_run_ids else "queue_empty",
            "capacity_receipt_payload_stop_loss_pass",
        ],
        "authorization_digest": request.authorization_digest,
        "capacity_receipt_digest": request.capacity_receipt_digest,
        "correlation_id": request.correlation_id,
        "preserved_run_ids": list(request.preserved_run_ids),
        "queue_identity_snapshot": queue_identity_snapshot,
        "queue_snapshot_digest": queue_snapshot_digest,
        "git_tag_policy": PROMOTION_GIT_TAG_POLICY,
    }


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
    postchecks = [
        "actor_clean_head_origin",
        "manifest_digest_actor_head_generation",
        "private_stage_readiness_and_barrier",
        "queue_preserved" if request.preserved_run_ids else "queue_empty",
        "capacity_receipt_payload_stop_loss_pass",
    ]
    queue_snapshot_digest = _queue_snapshot_digest(request.queue_root)
    plan_authority = _plan_authority_payload(
        request,
        target_manifest=target_manifest,
        queue_identity_snapshot=queue_identity_snapshot,
        queue_snapshot_digest=queue_snapshot_digest,
    )
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
        "postchecks": postchecks,
        "authorization_digest": request.authorization_digest,
        "capacity_receipt_path": str(request.capacity_receipt_path),
        "capacity_receipt_digest": request.capacity_receipt_digest,
        "correlation_id": request.correlation_id,
        "preserved_run_ids": list(request.preserved_run_ids),
        "queue_identity_snapshot": queue_identity_snapshot,
        "queue_snapshot_digest": queue_snapshot_digest,
        "git_tag_policy": PROMOTION_GIT_TAG_POLICY,
        "plan_authority": plan_authority,
    }
    plan["plan_digest"] = _json_digest(plan_authority)
    return plan


def plan_promotion(request: PromotionRequest) -> dict[str, Any]:
    return _plan_payload(request)


def _rollback_targets(request: PromotionRequest) -> dict[str, tuple[Path, Path]]:
    return {
        "stage": (request.private_stage_root, _stage_backup_path(request)),
        "barrier": (barrier_path(request), _barrier_backup_path(request)),
        "manifest": (request.manifest_path, _manifest_backup_path(request)),
        "actor": (request.actor_root, _actor_backup_path(request)),
    }


def _rollback_fingerprint(path: Path, name: str) -> dict[str, Any] | None:
    """比對原始 bytes/mode；rename 原件另綁 inode，manifest copy 綁內容。"""
    if path.is_symlink():
        raise PromotionError("rollback root is a symlink")
    if not path.exists():
        return None
    info = path.stat()
    kind = "directory" if path.is_dir() else "file"
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise PromotionError("rollback root type is invalid")
    entries = []
    for item in [path, *sorted(path.rglob("*"))] if path.is_dir() else [path]:
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            body = os.readlink(item)
        elif stat.S_ISREG(mode):
            body = hashlib.sha256(item.read_bytes()).hexdigest()
        elif stat.S_ISDIR(mode):
            body = None
        else:
            raise PromotionError("rollback tree entry type is invalid")
        entries.append([str(item.relative_to(path)), mode, body])
    result = {"kind": kind, "mode": stat.S_IMODE(info.st_mode), "digest": _json_digest({"entries": entries})}
    if name != "manifest":
        result.update(device=info.st_dev, inode=info.st_ino)
    return result


def _rollback_record(request: PromotionRequest) -> dict[str, Any]:
    originals = {
        name: {"path": str(path), "fingerprint": _rollback_fingerprint(path, name)}
        for name, (path, _backup) in _rollback_targets(request).items()
    }
    return {"originals": originals, "originals_digest": _json_digest(originals), "mutation_started": []}


def _mutation_intent(request: PromotionRequest, receipt: dict[str, Any], *names: str) -> None:
    """在可能部分成功的原件寫入前持久化 intent，不以 coarse state 猜副作用。"""
    receipt["rollback"]["mutation_started"].extend(names)
    _write_json(receipt_path(request), receipt)


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
        "rollback": _rollback_record(request),
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
        backup = _manifest_backup_path(request)
        backup.write_bytes(request.manifest_path.read_bytes())
        backup.chmod(stat.S_IMODE(request.manifest_path.stat().st_mode))
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
    descriptor, name = tempfile.mkstemp(dir=request.manifest_path.parent, prefix=".manifest-restore-")
    os.close(descriptor)
    temporary = Path(name)
    try:
        shutil.copy2(backup, temporary)
        os.replace(temporary, request.manifest_path)
    finally:
        temporary.unlink(missing_ok=True)


def _restore_stage(request: PromotionRequest, *, stage: bool = True, barrier: bool = True) -> None:
    if stage:
        if request.private_stage_root.exists():
            shutil.rmtree(request.private_stage_root)
        os.replace(_stage_backup_path(request), request.private_stage_root)
    if barrier:
        barrier_path(request).unlink(missing_ok=True)
        os.replace(_barrier_backup_path(request), barrier_path(request))


def _restore_actor(request: PromotionRequest) -> None:
    if request.actor_root.exists():
        shutil.rmtree(request.actor_root)
    os.replace(_actor_backup_path(request), request.actor_root)


def _rollback_from_state(
    request: PromotionRequest, state: str, *, original_error: Exception | None = None,
) -> None:
    receipt = load_receipt(request)
    _assert_receipt_matches(request, receipt, None)
    record = receipt.get("rollback")
    targets = _rollback_targets(request)
    if not isinstance(record, dict) or set(record) != {"originals", "originals_digest", "mutation_started"}:
        raise PromotionError("rollback record is missing or invalid")
    originals, started = record["originals"], record["mutation_started"]
    if (not isinstance(originals, dict) or set(originals) != set(targets)
            or _json_digest(originals) != record["originals_digest"]
            or not isinstance(started, list) or any(type(name) is not str or name not in targets for name in started)
            or len(started) != len(set(started))):
        raise PromotionError("rollback record integrity mismatch")
    actions = []
    # 完整驗證記錄與所有實體來源後才允許任何刪除或還原。
    for name, (path, backup) in targets.items():
        entry = originals[name]
        if not isinstance(entry, dict) or set(entry) != {"path", "fingerprint"} or entry["path"] != str(path):
            raise PromotionError("rollback recorded path mismatch")
        expected = entry["fingerprint"]
        keys = {"kind", "mode", "digest"} | ({"device", "inode"} if name != "manifest" else set())
        if expected is not None and (
            not isinstance(expected, dict) or set(expected) != keys
            or expected["kind"] != ("directory" if name in {"actor", "stage"} else "file")
            or type(expected["mode"]) is not int or not 0 <= expected["mode"] <= 0o7777
            or not isinstance(expected["digest"], str) or SHA256_PATTERN.fullmatch(expected["digest"]) is None
            or any(type(expected[key]) is not int or expected[key] < 0 for key in keys & {"device", "inode"})
        ):
            raise PromotionError("rollback original fingerprint is invalid")
        if name == "actor" and expected is None:
            raise PromotionError("rollback original actor is missing")
        if _rollback_fingerprint(path, name) == expected:
            continue
        if expected is None:
            if name not in started:
                raise PromotionError(f"rollback mutation was not recorded: {name}")
        elif _rollback_fingerprint(backup, name) != expected or (name == "manifest" and name not in started):
            raise PromotionError(f"rollback backup is incomplete or unowned: {name}")
        actions.append((name, expected))
    # 首次恢復副作用前持久標記；中止後禁止 finalize，仍可依實體證據重試。
    if original_error is not None:
        receipt.setdefault("error", str(original_error))
    _record_state(request, receipt, state, rollback_status="ROLLBACK_IN_PROGRESS",
                  state_before_rollback=state)
    errors = []
    for name, expected in actions:
        try:
            if expected is None:
                path = targets[name][0]
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)
            elif name == "manifest":
                _restore_manifest(request)
            elif name == "actor":
                _restore_actor(request)
            else:
                _restore_stage(request, stage=name == "stage", barrier=name == "barrier")
        except Exception as error:
            errors.append(f"{name}: {type(error).__name__}: {error}")
    for name, (path, _backup) in targets.items():
        try:
            if _rollback_fingerprint(path, name) != originals[name]["fingerprint"]:
                errors.append(f"{name}: restored identity/bytes mismatch")
        except Exception as error:
            errors.append(f"{name}: verification: {type(error).__name__}: {error}")
    if errors:
        raise PromotionError("; ".join(errors))


def _rollback_failed(
    request: PromotionRequest, receipt: dict[str, Any], state: str,
    original_error: Exception, restore_error: Exception,
) -> None:
    """即使寫 receipt 再次失敗，也保留原 promotion exception 與恢復錯誤。"""
    detail = f"{type(restore_error).__name__}: {restore_error}"
    try:
        _record_state(request, receipt, state, rollback_status="ROLLBACK_FAILED",
                      state_before_rollback=state, error=receipt.get("error", str(original_error)),
                      rollback_error=detail)
    except Exception as receipt_error:
        detail += f"; receipt: {type(receipt_error).__name__}: {receipt_error}"
    raise PromotionError(f"ROLLBACK_FAILED: {original_error}; restore: {detail}") from original_error


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
        _mutation_intent(request, receipt, "actor")
        _promote_actor(request)
        state_before_rollback = "ACTOR_PROMOTED"
        _record_state(request, receipt, "ACTOR_PROMOTED")
        if stop_after_state == "ACTOR_PROMOTED":
            raise PromotionCrashStop("stopped after ACTOR_PROMOTED")
        if failure_injection == "manifest":
            raise PromotionError("injected manifest failure")
        _mutation_intent(request, receipt, "manifest")
        manifest = _write_runtime_manifest(request)
        state_before_rollback = "MANIFEST_WRITTEN"
        _record_state(request, receipt, "MANIFEST_WRITTEN")
        if stop_after_state == "MANIFEST_WRITTEN":
            raise PromotionCrashStop("stopped after MANIFEST_WRITTEN")
        if failure_injection == "stage":
            raise PromotionError("injected stage failure")
        _mutation_intent(request, receipt, "stage", "barrier")
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
        try:
            _rollback_from_state(request, state_before_rollback, original_error=error)
            _record_state(
                request, receipt, "ROLLED_BACK", state_before_rollback=state_before_rollback,
                error=str(error), rollback_status="ROLLBACK_COMPLETE",
            )
        except Exception as restore_error:
            _rollback_failed(request, receipt, state_before_rollback, error, restore_error)
        raise PromotionError(f"ROLLBACK_COMPLETE: {error}") from error


def status_promotion(request: PromotionRequest) -> dict[str, Any]:
    path = receipt_path(request)
    if not path.exists():
        return {"status": "NOT_STARTED", "state": "NOT_STARTED"}
    receipt = _read_json(path)
    state = str(receipt.get("state", "UNKNOWN"))
    return {
        "status": "BLOCKED" if receipt.get("rollback_status") in {"ROLLBACK_FAILED", "ROLLBACK_IN_PROGRESS"} else "PASS",
        "state": state,
        "plan_digest": receipt.get("plan_digest"),
        "correlation_id": receipt.get("correlation_id"),
        "rollback_required": state
        in {"PREPARED", "ACTOR_PROMOTED", "MANIFEST_WRITTEN", "STAGE_INSTALLED", "POSTCHECK_PASSED"},
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
    try:
        _rollback_from_state(request, state)
        _record_state(
            request, receipt, "ROLLED_BACK", state_before_rollback=state,
            rollback_status="ROLLBACK_COMPLETE",
        )
    except Exception as error:
        _rollback_failed(request, receipt, state, error, error)
    return {"status": "ROLLED_BACK", "plan_digest": receipt["plan_digest"]}


def _finalize_directory_identity(path: Path) -> dict[str, Any]:
    _canonical_existing_dir(path, "finalize directory")
    info = path.stat()
    if info.st_uid != os.getuid():
        raise PromotionError("finalize directory owner mismatch")
    return {"path": str(path), "device": info.st_dev, "inode": info.st_ino}


def _sync_finalize_receipt(request: PromotionRequest) -> None:
    """只在 finalize 接點同步終態與目錄，不改其他 receipt writer 的語意。"""
    for path in (receipt_path(request), request.transaction_root):
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def finalize_promotion(
    request: PromotionRequest,
    *,
    expected_plan_digest: str | None = None,
) -> dict[str, Any]:
    receipt = load_receipt(request)
    _assert_receipt_matches(request, receipt, expected_plan_digest)
    if receipt.get("state") not in {"POSTCHECK_PASSED", "COMMITTED"}:
        raise PromotionError("finalize requires POSTCHECK_PASSED")
    if "rollback_status" in receipt:
        raise PromotionError("finalize is forbidden after rollback has started")
    if (receipt.get("target_actor_sha") != request.source_sha
            or receipt.get("target_manifest_digest") != _target_manifest(request)["manifest_digest"]):
        raise PromotionError("finalize target identity mismatch")
    transaction_identity = _finalize_directory_identity(request.transaction_root)
    path = receipt_path(request)
    if path.is_symlink() or not path.is_file():
        raise PromotionError("finalize receipt path identity mismatch")
    record = receipt.get("rollback", {})
    if not isinstance(record, dict):
        raise PromotionError("finalize rollback record is invalid")
    originals = record.get("originals", {})
    targets = _rollback_targets(request)
    if (not isinstance(originals, dict) or set(originals) != set(targets)
            or record.get("originals_digest") != _json_digest(originals)
            or any(not isinstance(originals[name], dict)
                   or originals[name].get("path") != str(target)
                   for name, (target, _) in targets.items())):
        raise PromotionError("finalize rollback path identity mismatch")
    bundle = rollback_bundle_path(request)
    history = receipt.get("history", [])
    if not isinstance(history, list) or any(not isinstance(entry, dict) for entry in history):
        raise PromotionError("finalize history is invalid")
    if receipt["state"] == "POSTCHECK_PASSED":
        if not bundle.exists():
            raise PromotionError("rollback bundle is missing")
        bundle_identity = _finalize_directory_identity(bundle)
        started = record.get("mutation_started")
        if (not history or history[-1].get("state") != "POSTCHECK_PASSED"
                or not isinstance(started, list) or any(not isinstance(name, str) for name in started)
                or len(started) != len(targets) or set(started) != set(targets)):
            raise PromotionError("finalize requires completed postcheck and owned bundle")
        expected_entries = set()
        for name, (_, backup) in targets.items():
            expected = originals[name].get("fingerprint")
            if _rollback_fingerprint(backup, name) != expected or (name == "actor" and expected is None):
                raise PromotionError("finalize rollback bundle is incomplete or unowned")
            if expected is not None:
                expected_entries.add(backup.name)
        if {entry.name for entry in bundle.iterdir()} != expected_entries:
            raise PromotionError("finalize rollback bundle contains unowned entries")
        # 沿用終態；此 receipt 同時保留驗收來源與 cleanup 的 inode authority。
        _record_state(request, receipt, "COMMITTED", rollback_bundle_finalized=False,
                      finalize={"transaction": transaction_identity, "bundle": bundle_identity})
    else:
        finalization = receipt.get("finalize")
        if (not isinstance(finalization, dict)
                or finalization.get("transaction") != transaction_identity
                or not isinstance(finalization.get("bundle"), dict)
                or finalization["bundle"].get("path") != str(bundle)
                or type(receipt.get("rollback_bundle_finalized")) is not bool
                or len(history) < 2
                or [entry.get("state") for entry in history[-2:]] != ["POSTCHECK_PASSED", "COMMITTED"]):
            raise PromotionError("finalize COMMITTED receipt lacks verified cleanup authority")
        if bundle.exists() or bundle.is_symlink():
            if (receipt["rollback_bundle_finalized"]
                    or _finalize_directory_identity(bundle) != finalization["bundle"]):
                raise PromotionError("finalize bundle path identity mismatch")
    # 包含 replace 後拋錯的重試：每次刪除前都重新確認 receipt 與 parent 已耐久。
    _sync_finalize_receipt(request)
    if bundle.exists():
        shutil.rmtree(bundle)
    if not receipt["rollback_bundle_finalized"]:
        receipt["rollback_bundle_finalized"] = True
        receipt["updated_at"] = _utc_now()
        _write_json(path, receipt)
        _sync_finalize_receipt(request)
    return {"status": "COMMITTED", "plan_digest": receipt["plan_digest"]}


# Publisher／Guard 交接只延伸既有 promotion 入口；不改七服務交易與回退語意。
@dataclass(frozen=True)
class PublisherGuardRequest:
    source_repo: Path
    expected_remote: str
    remote_ref: str
    before_sha: str
    target_sha: str
    old_manifest_path: Path
    new_manifest_path: Path
    staged_plists: tuple[Path, ...]
    launch_agents_dir: Path
    transaction_root: Path
    capacity_receipt_path: Path
    capacity_receipt_digest: str
    lock_budget_seconds: float = 60.0
    command_timeout_seconds: float = 5.0
    health_timeout_seconds: float = 30.0
    push_source: bool = False


PUBGUARD_LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.content-capacity-guard",
)


def _pg_activation():
    from scripts import pantheon_runtime_activation
    return pantheon_runtime_activation


def _pg_require(value: bool, reason: str) -> None:
    if not value:
        raise PromotionError(reason)


def _pg_receipt_path(request: PublisherGuardRequest) -> Path:
    return request.transaction_root / "publisher-guard-receipt.json"


def _pg_save(request: PublisherGuardRequest, receipt: dict[str, Any]) -> None:
    receipt["updated_at"] = _utc_now()
    _pg_activation()._write_private_json(_pg_receipt_path(request), receipt)


def _pg_event(request, receipt, action, **details):
    event = {"action": action, "intent_at": _utc_now(), "outcome": "INTENT", **details}
    receipt.setdefault("events", []).append(event)
    _pg_save(request, receipt)
    return event


def _pg_finish(request, receipt, event, **details):
    event.update(outcome="READBACK", finished_at=_utc_now(), **details)
    _pg_save(request, receipt)


class _PublisherGuardCommands:
    """每個控制子程序均獨立 process group；注入 runner 僅供離線 unit。"""
    def __init__(self, request, receipt=None, runner=None):
        self.request, self.receipt, self.runner = request, receipt, runner
        self.deadline = time.monotonic() + 300

    def __call__(self, argv):
        argv = list(map(str, argv))
        if argv[0] == "launchctl":
            argv[0] = "/bin/launchctl"
        timeout = min(self.request.command_timeout_seconds, self.deadline - time.monotonic())
        _pg_require(timeout > 0, "controller deadline exceeded")
        event = None
        if self.receipt is not None:
            event = _pg_event(self.request, self.receipt, "command", argv=argv,
                              child_terminal=False, group_terminal=False)
        process = None
        try:
            if self.runner is not None:
                result = self.runner(argv, timeout=timeout)
            else:
                # 不繼承 EX FD；git 不啟用 hook、prompt、pager 或自訂傳輸命令。
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("GIT_", "PANTHEON_RUNTIME_"))}
                environment.update(GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
                                   GIT_CONFIG_GLOBAL="/dev/null", GIT_OPTIONAL_LOCKS="0", LC_ALL="C",
                                   GIT_CONFIG_COUNT="3", GIT_CONFIG_KEY_0="core.hooksPath",
                                   GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
                                   GIT_CONFIG_VALUE_1="false", GIT_CONFIG_KEY_2="credential.helper",
                                   GIT_CONFIG_VALUE_2="")
                with tempfile.TemporaryFile(dir=self.request.transaction_root.parent) as stdout, \
                        tempfile.TemporaryFile(dir=self.request.transaction_root.parent) as stderr:
                    process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=environment,
                                               start_new_session=True, close_fds=True)
                    try:
                        if event is not None:
                            event.update(pid=process.pid, pgid=process.pid)
                            _pg_save(self.request, self.receipt)
                        code = process.wait(timeout=timeout)
                    finally:
                        # timeout、signal、正常退出有殘留後代皆須終止整組並取證。
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait(timeout=2)
                    stdout.seek(0)
                    stderr.seek(0)
                    # 實測完整 actor 的 ls-files 超過 1 MiB；metadata 仍限 4 MiB，其他命令維持原界限。
                    stdout_limit = (4 if argv[0] == "/usr/bin/git" and "ls-files" in argv else 1) * 1024 * 1024
                    output, diagnostics = stdout.read(stdout_limit + 1), stderr.read(65537)
                    _pg_require(len(output) <= stdout_limit and len(diagnostics) <= 65536,
                                "command output exceeded bound; observation UNKNOWN")
                    result = subprocess.CompletedProcess(argv, code,
                        output.decode(errors="replace"), diagnostics.decode(errors="replace"))
                terminal_deadline = time.monotonic() + 1
                while True:
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        break
                    _pg_require(time.monotonic() < terminal_deadline, "child process group terminal UNKNOWN")
                    time.sleep(0.01)
            if event is not None:
                _pg_finish(self.request, self.receipt, event, returncode=result.returncode,
                           stdout=result.stdout, stderr=result.stderr,
                           child_terminal=True, group_terminal=True,
                           unit_runner=self.runner is not None)
            return result
        except BaseException as error:
            if event is not None:
                terminal = self.runner is not None or (process is not None and process.poll() is not None)
                group_terminal = False
                if process is not None:
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        group_terminal = True
                event.update(outcome="UNKNOWN", error=f"{type(error).__name__}: {error}",
                             child_terminal=terminal,
                             group_terminal=group_terminal or self.runner is not None)
                _pg_save(self.request, self.receipt)
            raise


def _pg_git(commands, repo: Path, *args: str) -> str:
    result = commands(["/usr/bin/git", "-c", "core.hooksPath=/dev/null",
                       "-c", "core.fsmonitor=false", "-c", "credential.helper=",
                       "-C", str(repo), *args])
    _pg_require(result.returncode == 0, f"git readback failed: {args[0]}")
    return result.stdout.strip()


def _pg_load_manifest(path, commands, expected_digest=None):
    """沿既有 validate CLI；其 Git 後代也受同一 process group 與 deadline 約束。"""
    raw = _pg_activation().load_action_receipt(path)
    digest = expected_digest or raw.get("manifest_digest")
    _pg_require(isinstance(digest, str) and bool(SHA256_PATTERN.fullmatch(digest)), "manifest digest invalid")
    result = commands([str(Path(sys.executable).resolve()), "-B", str(Path(runtime_manifest.__file__).resolve()),
                       "validate", "--manifest", str(path), "--expected-digest", digest])
    _pg_require(result.returncode == 0, "bounded manifest validation failed")
    _pg_require(json.loads(result.stdout) == {"status": "PASS", **raw}, "manifest validation readback mismatch")
    return raw


def _pg_validate_push_source(request, commands):
    """推送只用 source 的已核准 origin；禁止隱含 push URL、tag 與 submodule 擴張。"""
    for options in (("--all",), ("--push", "--all")):
        _pg_require(_pg_git(commands, request.source_repo, "remote", "get-url", *options, "origin")
                    == request.expected_remote, "source effective push origin mismatch")
    _pg_require(_pg_git(commands, request.source_repo, "rev-parse", request.target_sha + "^{commit}")
                == request.target_sha, "source target commit unavailable")
    _pg_git(commands, request.source_repo, "merge-base", "--is-ancestor", request.before_sha, request.target_sha)


def _pg_push_source(request, receipt, commands):
    """既有 EX 內只送一次；先證明子程序終態，再以 remote readback 裁決。"""
    runtime_manifest.assert_runtime_shutdown_lease(Path(receipt["plan"]["state_root"]))
    _pg_require(request.push_source is True and not any(event["action"] == "source-push"
                for event in receipt["events"]), "source push already attempted or not opted in")
    _pg_validate_push_source(request, commands)
    intent = _pg_event(request, receipt, "source-push", source_repo=str(request.source_repo),
                       remote=request.expected_remote, ref=request.remote_ref,
                       before_sha=request.before_sha, target_sha=request.target_sha,
                       lease=receipt["lease"])
    error_text = None
    try:
        _pg_git(commands, request.source_repo, "-c", "push.followTags=false",
                "-c", "push.recurseSubmodules=no", "-c", "remote.origin.mirror=false",
                "push", "--atomic", "origin", f"{request.target_sha}:{request.remote_ref}")
    except Exception as error:
        error_text = f"{type(error).__name__}: {error}"
        receipt["errors"].append({"phase": "source-push", "error": error_text, "at": _utc_now()})
        intent["push_error"] = error_text
        _pg_save(request, receipt)
    # 包含 timeout／非零退出；無法證明 child/group terminal 就不讀 remote 或推進。
    _pg_resume_commands(request, receipt)
    intent["terminal_verified_at"] = _utc_now()
    _pg_save(request, receipt)
    remote = _pg_remote(request, commands)
    receipt["remote"] = remote
    _pg_finish(request, receipt, intent, remote=remote, push_error=error_text)
    _pg_require(remote["status"] == "TARGET", "source push remote OLD/UNKNOWN; no service mutation")
    return remote


def _pg_remote(request, commands) -> dict[str, Any]:
    """只能以實際 ls-remote 分辨 OLD／TARGET；其他結果保留 UNKNOWN。"""
    try:
        output = _pg_git(commands, request.source_repo, "ls-remote", "--refs",
                         request.expected_remote, request.remote_ref)
        rows = [line.split() for line in output.splitlines()]
        if len(rows) != 1 or len(rows[0]) != 2 or rows[0][1] != request.remote_ref:
            raise PromotionError("remote ref ambiguous")
        sha = rows[0][0]
        status = "TARGET" if sha == request.target_sha else "OLD" if sha == request.before_sha else "UNKNOWN"
        return {"status": status, "sha": sha}
    except Exception as error:
        return {"status": "UNKNOWN", "error": f"{type(error).__name__}: {error}"}


def _pg_observe(request, commands, labels):
    activation = _pg_activation()
    return {label: activation.observe_launchctl_service(label,
                request.launch_agents_dir / f"{label}.plist", runner=commands)
            for label in labels}


def _pg_check_five(request, commands, plan):
    labels = tuple(label for label in runtime_manifest.SERVICE_LABELS if label not in PUBGUARD_LABELS)
    observed = _pg_observe(request, commands, labels)
    for label in labels:
        _pg_require(observed[label]["topology"] == "ABSENT", f"inactive service not absent: {label}")
        path = request.launch_agents_dir / f"{label}.plist"
        _pg_require(_pg_activation().capture_file_identity(path) == plan["five_plists"][label],
                    f"inactive plist changed: {label}")
    return observed


def _pg_publisher_normal_contract(manifest, arguments):
    """鎖住現役自然 tick 語意；僅額外允許明確選用兩篇 NEW 批次。"""
    child = arguments[17:]
    _pg_require(child[:3] == [manifest["python_executable"], "-m", "scripts.agy_content_publisher"],
                "normal Publisher command mismatch")
    expected = {
        "--repo-root": manifest["actor_root"], "--queue-root": manifest["queue_root"],
        "--state-root": manifest["publisher_state_root"], "--max-runs": "1",
        "--expected-repo-root": manifest["actor_root"], "--expected-queue-root": manifest["queue_root"],
        "--expected-state-root": manifest["publisher_state_root"], "--expected-runtime-sha": manifest["actor_head"],
        "--expected-runtime-digest": manifest["runtime_digest"], "--expected-push-mode": "push",
    }
    switches = {"--continuous-tick", "--include-rewrites", "--push"}
    required = set(expected) | switches
    expected["--prefer-new-batch-size"] = "2"
    seen = set()
    index = 3
    while index < len(child):
        flag = child[index]
        _pg_require(flag not in seen and flag in (set(expected) | switches),
                    "normal Publisher flag forbidden or duplicated")
        seen.add(flag)
        index += 1
        if flag in expected:
            _pg_require(index < len(child) and child[index] == expected[flag],
                        f"normal Publisher identity mismatch: {flag}")
            index += 1
    _pg_require(seen - {"--prefer-new-batch-size"} == required, "normal Publisher flags incomplete")


def _pg_guard_normal_contract(manifest, arguments):
    """Guard 只准完整、無重複且 manifest-bound 的正常 check，不接受 preflight。"""
    child = arguments[17:]
    _pg_require(child[:3] == [manifest["python_executable"], "-m", "scripts.pantheon_content_capacity_guard"]
                and child[-1:] == ["check"], "normal Guard command mismatch")
    expected = {"--queue-root": manifest["queue_root"], "--publisher-root": manifest["publisher_state_root"],
                "--log-root": manifest["log_root"],
                "--state-file": str(Path(manifest["queue_root"]) / "capacity-guard-state.json")}
    tail = child[3:-1]
    _pg_require(len(tail) == 2 * len(expected), "normal Guard flags incomplete")
    seen = set()
    for index in range(0, len(tail), 2):
        flag = tail[index]
        _pg_require(flag in expected and flag not in seen and tail[index + 1] == expected[flag],
                    "normal Guard flag forbidden, duplicated or identity mismatch")
        seen.add(flag)
    _pg_require(seen == set(expected), "normal Guard flags incomplete")


def _pg_capacity_receipt_identity(request):
    """沿用原容量 validator；只補原位檔案身分封印，不新增容量格式或政策。"""
    _pg_require(isinstance(request.capacity_receipt_path, Path)
                and isinstance(request.capacity_receipt_digest, str)
                and bool(SHA256_PATTERN.fullmatch(request.capacity_receipt_digest)),
                "capacity receipt path/digest required")
    activation = _pg_activation()
    try:
        before = activation.capture_file_identity(request.capacity_receipt_path, require_private=False)
    except activation.RuntimeActivationError as error:
        raise PromotionError("capacity receipt missing or identity invalid") from error
    # 既有 validator 僅讀兩個同名欄位，直接沿用；不複製或放寬 cycles/reclaim/stop-loss 判斷。
    _validate_capacity_receipt(request)
    after = activation.capture_file_identity(request.capacity_receipt_path, require_private=False)
    _pg_require(before == after and after["sha256"] == request.capacity_receipt_digest,
                "capacity receipt identity drift")
    return after


def _pg_spec(request: PublisherGuardRequest, commands) -> dict[str, Any]:
    """所有封印均唯讀；不建立 txnroot、barrier 或 readiness。"""
    activation = _pg_activation()
    _pg_require(type(request.push_source) is bool, "push_source must be an explicit boolean")
    capacity_identity = _pg_capacity_receipt_identity(request)
    for sha in (request.before_sha, request.target_sha):
        _pg_require(bool(SHA1_PATTERN.fullmatch(sha)), "source SHA invalid")
    _pg_require(request.before_sha != request.target_sha, "source must advance")
    _pg_require(bool(re.fullmatch(r"refs/heads/[A-Za-z0-9][A-Za-z0-9/._-]*", request.remote_ref))
                and ".." not in request.remote_ref, "remote branch invalid")
    _pg_require(bool(request.expected_remote) and not request.expected_remote.startswith("-"), "remote invalid")
    _pg_require(5 <= request.lock_budget_seconds <= 240
                and 0 < request.command_timeout_seconds <= 10
                and 0 < request.health_timeout_seconds <= 120, "time budget invalid")
    for path in (request.source_repo, request.launch_agents_dir):
        _pg_require(path.is_absolute() and path.resolve(strict=True) == path and path.is_dir(),
                    "request root must be canonical")
    txn = request.transaction_root
    _pg_require(txn.is_absolute() and txn.resolve() == txn and txn.parent.is_dir(), "txnroot invalid")
    if txn.exists():
        _pg_require(txn.is_dir() and txn.stat().st_uid == os.getuid()
                    and stat.S_IMODE(txn.stat().st_mode) == 0o700, "txnroot must be private")
    for path in (request.old_manifest_path, request.new_manifest_path):
        activation.capture_file_identity(path)
    old = _pg_load_manifest(request.old_manifest_path, commands)
    new = _pg_load_manifest(request.new_manifest_path, commands)
    helper = getattr(runtime_manifest, "activation_service_labels", None)
    _pg_require(helper is not None and new.get("activation_scope") == "publisher_guard"
                and helper(new) == PUBGUARD_LABELS, "publisher_guard manifest support required")
    _pg_require(new["service_labels"] == list(runtime_manifest.SERVICE_LABELS), "registration set changed")
    for field in ("queue_root", "publisher_state_root", "log_root"):
        _pg_require(old[field] == new[field], f"shared {field} changed")
    actor = Path(new["actor_root"])
    old_actor = Path(old["actor_root"])
    roots = (actor, old_actor, request.source_repo)
    _pg_require(all(a != b and a not in b.parents and b not in a.parents
                    for i, a in enumerate(roots) for b in roots[i + 1:]), "sidecar actor must be separate")
    _pg_require((actor / ".git").is_dir() and not (actor / ".git").is_symlink(),
                "actor must have a self-contained git directory")
    common = Path(_pg_git(commands, actor, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    _pg_require(common == actor / ".git" and not (common / "objects/info/alternates").exists()
                and not (common / "commondir").exists(), "actor git depends on another checkout")
    _pg_require(_pg_git(commands, actor, "rev-parse", "HEAD") == request.target_sha
                and new.get("actor_head") == request.target_sha, "actor target SHA mismatch")
    _pg_require(not _pg_git(commands, actor, "status", "--porcelain", "--untracked-files=all"), "actor not clean")
    _pg_require(all(line.startswith("H ") for line in _pg_git(commands, actor, "ls-files", "-v").splitlines()),
                "actor index has hidden worktree changes")
    _pg_require(all(not line.startswith(("120000 ", "160000 "))
                    for line in _pg_git(commands, actor, "ls-files", "--stage").splitlines()),
                "actor tracked symlink/submodule is not self-contained")
    for module in (runtime_manifest, activation):
        _pg_require(file_sha256(actor / "scripts" / Path(module.__file__).name)
                    == file_sha256(Path(module.__file__)), "actor activation helper version mismatch")
    _pg_git(commands, actor, "fsck", "--full", "--no-reflogs")
    _pg_require(_pg_git(commands, request.source_repo, "config", "--get", "remote.origin.url")
                == request.expected_remote, "source origin mismatch")
    if request.push_source:
        _pg_validate_push_source(request, commands)
    _pg_git(commands, actor, "merge-base", "--is-ancestor", request.before_sha, request.target_sha)
    _pg_require(request.old_manifest_path != request.new_manifest_path
                and old["generation"] != new["generation"], "old manifest/generation must be preserved")
    state = Path(new["publisher_state_root"])
    barrier = state / f"four-lane-activation-{new['generation']}.barrier"
    _pg_require(len(request.staged_plists) == 2, "exactly two staged plists required")
    runtime_manifest.aggregate_plist_preflight(new, list(request.staged_plists), expected_activation_mode="normal")
    staged = {}
    ready_root = None
    for path in request.staged_plists:
        identity = activation.capture_file_identity(path)
        plist = plistlib.loads(path.read_bytes())
        label = plist["Label"]
        _pg_require(label in PUBGUARD_LABELS and label not in staged, "staged label invalid")
        _pg_require(type(plist.get("StartInterval")) is int
                    and plist["StartInterval"] == (60 if label == PUBGUARD_LABELS[0] else 300)
                    and "KeepAlive" not in plist and plist.get("RunAtLoad") is True, "normal schedule mismatch")
        args = plist.get("ProgramArguments", [])
        _pg_require(len(args) > 17 and args[1:4] == ["-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec"]
                    and args[4:12] == ["--barrier", str(barrier), "--expected-digest", new["manifest_digest"],
                                      "--manifest", str(request.new_manifest_path), "--service-label", label]
                    and args[12] == "--ready-root" and args[14] == "--timeout" and args[16] == "--",
                    "wrapper command mismatch")
        candidate = Path(args[13])
        _pg_require(candidate.is_absolute() and candidate.resolve() == candidate and candidate.parent.is_dir()
                    and float(args[15]) >= request.lock_budget_seconds + request.health_timeout_seconds + 5,
                    "wrapper readiness/deadline mismatch")
        _pg_require(ready_root is None or ready_root == candidate, "ready root mismatch")
        ready_root = candidate
        staged[label] = identity
        _pg_require(path != request.launch_agents_dir / f"{label}.plist", "staged plist overlaps destination")
        if label == PUBGUARD_LABELS[0]:
            runtime_manifest.publisher_plist_preflight(new, path, require_no_exact_run_id=True)
            _pg_publisher_normal_contract(new, args)
        else:
            _pg_guard_normal_contract(new, args)
    _pg_require(set(staged) == set(PUBGUARD_LABELS), "staged pair incomplete")
    # 交易輸出與保留輸入不得互為 ancestor；防止 receipt／barrier 覆寫舊 actor。
    protected = [old_actor, actor, request.source_repo, Path(new["queue_root"])]
    for output in (txn, ready_root, barrier, request.launch_agents_dir):
        _pg_require(all(output != root and root not in output.parents and output not in root.parents
                        for root in protected), "transaction output overlaps immutable/shared root")
    _pg_require(ready_root != state and ready_root != barrier and txn != ready_root
                and request.launch_agents_dir not in txn.parents and txn != request.launch_agents_dir
                and txn not in ready_root.parents and ready_root not in txn.parents,
                "transaction/readiness paths overlap")
    _pg_guard_clear(new)
    return {
        "kind": "publisher_guard", "schema_version": 1,
        "controller": activation.capture_file_identity(Path(__file__).resolve(), require_private=False),
        "helpers": {module.__name__: file_sha256(Path(module.__file__))
                    for module in (runtime_manifest, activation)},
        "request": {key: [str(item) for item in value] if key == "staged_plists" else str(value)
                    if isinstance(value, Path) else value for key, value in vars(request).items()},
        "capacity_receipt": capacity_identity,
        "old_manifest": activation.capture_file_identity(request.old_manifest_path),
        "manifest": activation.capture_file_identity(request.new_manifest_path),
        "manifest_digest": new["manifest_digest"], "actor_root": str(actor),
        "state_root": str(state), "ready_root": str(ready_root), "barrier": str(barrier),
        "shutdown_lease": activation.capture_file_identity(state / "runtime-work.lock"),
        "staged_plists": staged,
        "five_plists": {label: activation.capture_file_identity(request.launch_agents_dir / f"{label}.plist")
                        for label in runtime_manifest.SERVICE_LABELS if label not in PUBGUARD_LABELS},
    }


def _pg_guard_clear(manifest):
    """不接管 Guard 既有 stop/recovery；未知狀態只保留，不洗成 PASS。"""
    path = Path(manifest["queue_root"]) / "capacity-guard-state.json"
    if not path.exists() and not path.is_symlink():
        return {"status": "ABSENT"}
    current = _pg_activation().load_action_receipt(path)
    _pg_require(current.get("status") == "PASS" and current.get("recovery_incident") is None,
                "Guard stop/recovery lineage requires resolution before handoff")
    return {"identity": _pg_activation().capture_file_identity(path), "status": "PASS"}


def plan_publisher_guard(request: PublisherGuardRequest, *, runner=None) -> dict[str, Any]:
    """預設唯讀；封印實際入口、controller 與全部 staged authority。"""
    commands = _PublisherGuardCommands(request, runner=runner)
    plan = _pg_spec(request, commands)
    _pg_require(_pg_remote(request, commands)["status"] == "OLD", "prepare requires observed remote OLD")
    _pg_check_five(request, commands, plan)
    _pg_require(not Path(plan["barrier"]).exists() and not Path(plan["ready_root"]).exists(),
                "new generation readiness must not exist before prepare")
    _pg_require(not runtime_manifest.shutdown_readiness_permit_path(Path(plan["state_root"])).exists(),
                "existing readiness permit cannot be replaced")
    pair = _pg_observe(request, commands, PUBGUARD_LABELS)
    _pg_require(all(item["topology"] in {"LOADED", "ABSENT"} for item in pair.values()), "old pair identity UNKNOWN")
    plan["initial_services"] = pair
    plan["old_plists"] = {label: _pg_activation().capture_file_identity(
                            request.launch_agents_dir / f"{label}.plist") for label in PUBGUARD_LABELS}
    return {"status": "PLANNED", "plan_digest": _json_digest(plan), "plan": plan}


def prepare_publisher_guard(request: PublisherGuardRequest, *, expected_plan_digest: str, runner=None):
    """任何 source 推送前封存恢復資料及 explicit push_source；prepare 本身不推送。"""
    result = plan_publisher_guard(request, runner=runner)
    _pg_require(result["plan_digest"] == expected_plan_digest, "expected plan digest mismatch")
    _pg_require(not request.transaction_root.exists(), "transaction already exists; use recover")
    request.transaction_root.mkdir(mode=0o700)
    _pg_activation()._fsync_directory(request.transaction_root.parent)
    receipt = {**result, "status": "PREPARING", "events": [], "errors": [], "attempts": [],
               "remote": {"status": "OLD"}, "touched_labels": [], "permit": None, "lease": None}
    _pg_save(request, receipt)
    event = _pg_event(request, receipt, "prepare-recovery-material")
    # 恢復只向前；舊 bytes 仍留存作檢核，絕不自動還原舊 actor。
    for label, identity in result["plan"]["staged_plists"].items():
        destination = request.transaction_root / f"{label}.target.plist"
        _pg_activation().maintenance_atomic(destination, Path(identity["path"]).read_bytes())
        _pg_require(file_sha256(destination) == identity["sha256"], "recovery payload readback mismatch")
    _pg_finish(request, receipt, event, payloads_sealed=True)
    receipt["status"] = "PREPARED"
    _pg_save(request, receipt)
    return receipt


@contextmanager
def _pg_watchdog(seconds):
    """主執行緒 wall clock 界限同時涵蓋 EX 持有；例外後最多五秒收尾。"""
    _pg_require(threading.current_thread() is threading.main_thread(), "bounded controller requires main thread")
    _pg_require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), "existing alarm authority")
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM)}
    interrupted = False
    def interrupt(signum, frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            signal.setitimer(signal.ITIMER_REAL, 5)
        raise PromotionError(f"controller interrupted: {signal.Signals(signum).name}")
    for sig in previous:
        signal.signal(sig, interrupt)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def _pg_resume_commands(request, receipt):
    """crash 留下的 spawn 空窗不猜測；已記錄 group 只能證明消失。"""
    for event in receipt["events"]:
        if event["action"] != "command" or (event.get("child_terminal") and event.get("group_terminal")):
            continue
        pgid = event.get("pgid")
        _pg_require(type(pgid) is int and pgid > 1, "unbound command lineage UNKNOWN")
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            # 保留原 event 不覆寫；新證據追加到同一 receipt。
            event["terminal_revalidation"] = {"at": _utc_now(), "group_absent": True}
        else:
            raise PromotionError("prior child group lineage UNKNOWN")
    _pg_save(request, receipt)


def _pg_drain(request, receipt, commands, manifest, suffix, *, mode="drain"):
    # 原 journal 永遠保留；每次有界取樣繼承既有 birth/groups，不沿用過期 monotonic deadline。
    activation = _pg_activation()
    lineage = receipt.setdefault("boundaries", {})
    previous = lineage.get(suffix)
    journal = request.transaction_root / f"{suffix}.{len(receipt['attempts'])}.{len(receipt['events'])}.processes.json"
    event = _pg_event(request, receipt, "process-boundary", journal=str(journal), previous=previous, mode=mode)
    if previous is not None:
        previous_path = Path(previous)
        prior = activation.load_action_receipt(previous_path)
        _pg_require(prior.get("status") != "UNKNOWN_OR_FAILED", "prior process evidence unresolved")
        prior = {**prior, "prior_journal": activation.capture_file_identity(previous_path)}
        prior.pop("deadline", None)
        activation._write_private_json(journal, prior)
    lineage[suffix] = str(journal)
    _pg_save(request, receipt)
    result = _pg_activation().run_process_boundary(journal_path=journal,
        timeout_seconds=min(10, max(0.01, commands.deadline - time.monotonic())),
        domain=f"gui/{os.getuid()}", owned_roots={field: manifest[field] for field in runtime_manifest.PATH_FIELDS},
        mode=mode, arguments=PUBGUARD_LABELS, runner=commands)
    _pg_require(result.get("status") == ("DRAINED" if mode == "drain" else "OBSERVED")
                and not result.get("resample_required", False), "process lineage UNKNOWN")
    _pg_finish(request, receipt, event, result=result)


def _pg_revoke(request, receipt, state):
    path = runtime_manifest.shutdown_readiness_permit_path(state)
    if path.exists() or path.is_symlink():
        current = _pg_activation().load_action_receipt(path)
        recorded = receipt.get("permit")
        _pg_require(recorded is not None and current == recorded, "unknown permit lineage; preserve")
        event = _pg_event(request, receipt, "revoke-permit", nonce=recorded["nonce"])
        runtime_manifest.revoke_shutdown_readiness_permit(state)
        _pg_activation()._fsync_directory(state)
        _pg_require(not path.exists(), "permit revoke unproven")
        _pg_finish(request, receipt, event, absent=True)
    receipt["permit_revoked"] = True
    _pg_save(request, receipt)


def _pg_forward(request, receipt, commands, *, allow_source_push=False):
    plan = receipt["plan"]
    activation = _pg_activation()
    manifest = _pg_load_manifest(request.new_manifest_path, commands, plan["manifest_digest"])
    state = Path(plan["state_root"])
    commands.deadline = time.monotonic() + request.lock_budget_seconds
    event = _pg_event(request, receipt, "acquire-ex", budget_seconds=request.lock_budget_seconds)
    acquired = False
    try:
        with _pg_watchdog(request.lock_budget_seconds):
            with runtime_manifest.runtime_shutdown_lease(state,
                    timeout_seconds=min(5, request.lock_budget_seconds)) as fd:
                acquired = True
                lease = state / "runtime-work.lock"
                metadata = lease.stat()
                prior = receipt.get("lease")
                identity = {"device": metadata.st_dev, "inode": metadata.st_ino}
                expected_lease = {key: plan["shutdown_lease"][key] for key in ("device", "inode")}
                _pg_require(identity == expected_lease and (prior is None or prior == identity),
                            "shutdown lease lineage changed")
                receipt["lease"] = identity
                _pg_finish(request, receipt, event, lease=identity)
                try:
                    _pg_require(_pg_capacity_receipt_identity(request) == plan["capacity_receipt"],
                                "capacity receipt sealed identity drift")
                    _pg_revoke(request, receipt, state)
                    remote = _pg_remote(request, commands)
                    receipt["remote"] = remote
                    _pg_save(request, receipt)
                    _pg_check_five(request, commands, plan)
                    receipt.setdefault("guard_observations", []).append(_pg_guard_clear(manifest))
                    _pg_save(request, receipt)
                    if remote["status"] == "OLD" and allow_source_push:
                        remote = _pg_push_source(request, receipt, commands)
                    _pg_require(remote["status"] == "TARGET", "remote not TARGET; no control mutation")
                    # 舊 actor 與新 actor 都取樣；既有 lineage journal 按同一 manifest 保留。
                    old = _pg_load_manifest(request.old_manifest_path, commands)
                    # EX 已排除 protected payload；先記錄 wrapper/後代，再 bootout，最後證明終態。
                    # 不能先 drain 等待 barrier 的新 wrapper，否則會自我等待直到 timeout。
                    _pg_drain(request, receipt, commands, old, "old-cohort", mode="observe")
                    _pg_drain(request, receipt, commands, manifest, "new-cohort", mode="observe")
                    observations = _pg_observe(request, commands, PUBGUARD_LABELS)
                    receipt.setdefault("observations", []).append(observations)
                    _pg_save(request, receipt)
                    for label in PUBGUARD_LABELS:
                        current = observations[label]
                        _pg_require(current["topology"] != "UNKNOWN", f"service control UNKNOWN: {label}")
                        destination = request.launch_agents_dir / f"{label}.plist"
                        digest = file_sha256(destination)
                        _pg_require(digest in {plan["old_plists"][label]["sha256"], plan["staged_plists"][label]["sha256"]},
                                    "destination outside sealed old/target payload")
                        if current["topology"] == "LOADED":
                            latest = _pg_observe(request, commands, (label,))[label]
                            _pg_require(activation._same_launchctl_root_identity(current, latest),
                                        "service identity drift before bootout")
                            event = _pg_event(request, receipt, "bootout", label=label, before=current)
                            if label not in receipt["touched_labels"]:
                                receipt["touched_labels"].append(label)
                            _pg_save(request, receipt)
                            result = commands(["launchctl", "bootout", f"gui/{os.getuid()}/{label}"])
                            after = _pg_observe(request, commands, (label,))[label]
                            _pg_finish(request, receipt, event, after=after, returncode=result.returncode)
                            _pg_require(result.returncode == 0 and after["topology"] == "ABSENT", "bootout outcome UNKNOWN")
                    _pg_drain(request, receipt, commands, old, "old-cohort")
                    _pg_drain(request, receipt, commands, manifest, "new-cohort")
                    barrier = Path(plan["barrier"])
                    ready = Path(plan["ready_root"])
                    # generation 專有 ack 不清除；重試前驗證，絕不造假 wrapper ack。
                    if barrier.exists():
                        runtime_manifest.validate_barrier(barrier, manifest)
                    event = _pg_event(request, receipt, "create-permit")
                    permit = runtime_manifest.create_shutdown_readiness_permit(state, manifest,
                        barrier=barrier, ready_root=ready, labels=list(PUBGUARD_LABELS),
                        timeout_seconds=min(300, max(1, commands.deadline - time.monotonic())), owner_pid=os.getpid())
                    receipt["permit"] = permit
                    activation._fsync_directory(state)
                    receipt["permit_revoked"] = False
                    _pg_finish(request, receipt, event, permit=permit)
                    ack_baseline = {}
                    for label in PUBGUARD_LABELS:
                        ack = ready / f"{label}.json"
                        ack_baseline[label] = activation.capture_file_identity(ack) if ack.exists() else None
                    receipt.setdefault("ack_baselines", []).append(ack_baseline)
                    _pg_save(request, receipt)
                    for label in PUBGUARD_LABELS:
                        target = request.transaction_root / f"{label}.target.plist"
                        _pg_require(file_sha256(target) == plan["staged_plists"][label]["sha256"], "staged recovery bytes changed")
                        destination = request.launch_agents_dir / f"{label}.plist"
                        event = _pg_event(request, receipt, "install-plist", label=label, target_sha256=file_sha256(target))
                        if label not in receipt["touched_labels"]:
                            receipt["touched_labels"].append(label)
                        _pg_save(request, receipt)
                        activation.maintenance_atomic(destination, target.read_bytes())
                        _pg_require(file_sha256(destination) == file_sha256(target), "plist install readback mismatch")
                        _pg_finish(request, receipt, event, identity=activation.capture_file_identity(destination))
                        event = _pg_event(request, receipt, "bootstrap", label=label)
                        result = commands(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(destination)])
                        after = _pg_observe(request, commands, (label,))[label]
                        _pg_finish(request, receipt, event, after=after, returncode=result.returncode)
                        _pg_require(result.returncode == 0 and after["topology"] == "LOADED", "bootstrap outcome UNKNOWN")
                    while True:
                        try:
                            acks = [runtime_manifest._load_readiness_ack(ready / f"{label}.json", manifest, label)
                                    for label in PUBGUARD_LABELS]
                            fresh = {label: activation.capture_file_identity(ready / f"{label}.json")
                                     for label in PUBGUARD_LABELS}
                            _pg_require(all(fresh[label] != ack_baseline[label] for label in PUBGUARD_LABELS),
                                        "wrapper acknowledgement not refreshed")
                            break
                        except (OSError, runtime_manifest.RuntimeManifestError, PromotionError):
                            _pg_require(time.monotonic() < commands.deadline - 1, "wrapper readiness timeout")
                            time.sleep(0.05)
                    activation._fsync_directory(ready)
                    activation._fsync_directory(ready.parent)
                    event = _pg_event(request, receipt, "activate-barrier", acknowledgements=acks, ack_files=fresh)
                    result = runtime_manifest.activate_barrier(barrier, ready, manifest)
                    activation._fsync_directory(state)
                    runtime_manifest.validate_barrier(barrier, manifest)
                    _pg_finish(request, receipt, event, result=result)
                    receipt["status"] = "ACTIVATED_UNDER_EX"
                    _pg_save(request, receipt)
                except BaseException as work_error:
                    receipt["errors"].append({"phase": "forward", "error": f"{type(work_error).__name__}: {work_error}"})
                    _pg_save(request, receipt)
                    raise
                finally:
                    try:
                        _pg_revoke(request, receipt, state)
                    except BaseException as cleanup_error:
                        receipt["errors"].append({"phase": "permit-cleanup", "error": f"{type(cleanup_error).__name__}: {cleanup_error}"})
                        _pg_save(request, receipt)
                        raise
                    finally:
                        _pg_event(request, receipt, "release-ex", lease=receipt.get("lease"))
    finally:
        # with 已關閉 FD 才記 release；不在 EX 下宣稱正常 payload 健康。
        closed = False
        if acquired:
            try:
                os.fstat(fd)
            except OSError as error:
                closed = error.errno == 9
        receipt.setdefault("ex_releases", []).append({"at": _utc_now(), "acquired": acquired,
                                                       "released": closed, "fd_closed": closed})
        _pg_save(request, receipt)
        _pg_require(not acquired or closed, "EX release terminal UNKNOWN")


def _pg_handoff_published(receipt):
    """barrier 發布證據是單向交接界線；即使後續健康失敗，也不回頭 bootout。"""
    return os.path.lexists(receipt["plan"]["barrier"]) or any(
        event["action"] == "activate-barrier" and event.get("outcome") == "READBACK"
        and event.get("result", {}).get("manifest_digest") == receipt["plan"]["manifest_digest"]
        for event in receipt["events"])


def _pg_reconcile_published_cleanup(request, receipt, commands):
    """交接後只補 owned 控制面收尾；同 inode 重新取得 EX 證明舊 exclusion 已釋放。"""
    plan = receipt["plan"]
    state = Path(plan["state_root"])
    manifest = _pg_load_manifest(request.new_manifest_path, commands, plan["manifest_digest"])
    runtime_manifest.validate_barrier(Path(plan["barrier"]), manifest)
    permit = runtime_manifest.shutdown_readiness_permit_path(state)
    releases = receipt.get("ex_releases", [])
    if releases and releases[-1].get("fd_closed") is True and receipt.get("permit_revoked") is True and not os.path.lexists(permit):
        return
    event = _pg_event(request, receipt, "reconcile-published-cleanup")
    acquired = False
    try:
        with _pg_watchdog(min(10, request.lock_budget_seconds)):
            with runtime_manifest.runtime_shutdown_lease(state, timeout_seconds=min(5, request.lock_budget_seconds)) as fd:
                acquired = True
                info = (state / "runtime-work.lock").stat()
                _pg_require({"device": info.st_dev, "inode": info.st_ino}
                            == {key: plan["shutdown_lease"][key] for key in ("device", "inode")},
                            "published cleanup lease lineage changed")
                _pg_revoke(request, receipt, state)
                _pg_finish(request, receipt, event, prior_ex_proven_released=True, no_service_restart=True)
    finally:
        closed = False
        if acquired:
            try:
                os.fstat(fd)
            except OSError as error:
                closed = error.errno == 9
        receipt.setdefault("ex_releases", []).append({"at": _utc_now(), "acquired": acquired,
            "released": closed, "fd_closed": closed, "reconciled_published_cleanup": True})
        _pg_save(request, receipt)
        _pg_require(not acquired or closed, "published cleanup EX release UNKNOWN")


def _pg_release_tag_proof(request, commands, tag, commit):
    """保留 tag object 身分；annotated tag 以 peeled commit 驗帳，lightweight 維持相容。"""
    peeled_ref = tag + "^{}"
    text = _pg_git(commands, request.source_repo, "ls-remote", request.expected_remote, tag, peeled_ref)
    refs = {}
    for line in text.splitlines():
        row = line.split()
        _pg_require(len(row) == 2 and bool(SHA1_PATTERN.fullmatch(row[0]))
                    and row[1] in {tag, peeled_ref} and row[1] not in refs,
                    "publication remote tag proof invalid or ambiguous")
        refs[row[1]] = row[0]
    _pg_require(tag in refs, "publication remote tag proof missing")
    target = refs.get(peeled_ref, refs[tag])
    _pg_require(target == commit, "publication remote tag commit differs")
    return {"tag_ref": tag, "tag_object_sha": refs[tag], "tag_commit_sha": target,
            "tag_kind": "annotated" if peeled_ref in refs else "lightweight"}


def _pg_publication_ledger_snapshot(path: Path):
    """業務 ledger 可為0600／0644；JSON 與身分取自同一 no-follow FD。"""
    descriptor = None
    try:
        _pg_require(path.is_absolute() and path.resolve(strict=True) == path,
                    "publication ledger path must be canonical")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(descriptor)

        def fingerprint(metadata):
            return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_uid,
                    metadata.st_nlink, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)

        _pg_require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                    and before.st_nlink == 1 and stat.S_IMODE(before.st_mode) in {0o600, 0o644}
                    and fingerprint(before) == fingerprint(path.lstat()),
                    "publication ledger identity is invalid")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        data = b"".join(chunks)
        ledger = json.loads(data)
        _pg_require(isinstance(ledger, dict), "publication ledger must be an object")
        after = os.fstat(descriptor)
        _pg_require(fingerprint(before) == fingerprint(after) == fingerprint(path.lstat())
                    and path.resolve(strict=True) == path,
                    "publication ledger changed during read")
        identity = {"path": str(path), "device": after.st_dev, "inode": after.st_ino,
                    "size": after.st_size, "mtime_ns": after.st_mtime_ns,
                    "sha256": hashlib.sha256(data).hexdigest()}
        return identity, ledger
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PromotionError("publication ledger is unavailable or invalid") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _pg_published_remote(request, receipt, commands):
    """交接後接受有 ledger/tag/同版 runtime 證據的有界正常前進；push fence 仍只准精確 TARGET。"""
    remote = _pg_remote(request, commands)
    if remote["status"] in {"OLD", "TARGET"}:
        return remote
    try:
        observed = remote.get("sha", "")
        _pg_require(bool(SHA1_PATTERN.fullmatch(observed)), "remote SHA unavailable")
        from scripts import agy_content_publisher as publisher
        actor = Path(receipt["plan"]["actor_root"])
        state = Path(receipt["plan"]["state_root"])
        _pg_require(not os.path.lexists(state / "push-outcome-unresolved.json"), "publisher push unresolved")
        _pg_git(commands, actor, "merge-base", "--is-ancestor", request.target_sha, observed)
        paths = tuple(publisher.TRANSACTION_RUNTIME_PATHS) + (
            "scripts/pantheon_content_runtime_manifest.py", "scripts/pantheon_runtime_activation.py",
            "scripts/pantheon_content_runtime_promotion.py", "scripts/pantheon_content_capacity_guard.py")
        _pg_require(not _pg_git(commands, actor, "diff", "--name-only", request.target_sha, observed, "--", *paths),
                    "published descendant runtime drift")
        commits = _pg_git(commands, actor, "rev-list", "--first-parent", "--max-count=21", observed,
                          "^" + request.target_sha).splitlines()
        _pg_require(0 < len(commits) <= 20, "publication history exceeds bounded health sample")
        ledger_path = state / "ledger.json"
        identity, ledger = _pg_publication_ledger_snapshot(ledger_path)
        entries = []
        for key in ("published_runs", "rewrite_released_runs", "translation_published_runs"):
            records = ledger.get(key, [])
            _pg_require(isinstance(records, list), "publication ledger collection invalid")
            entries.extend(record for record in records if isinstance(record, dict))
        proofs = []
        for index, commit in enumerate(commits):
            parent = commits[index + 1] if index + 1 < len(commits) else request.target_sha
            _pg_require(_pg_git(commands, actor, "rev-list", "--parents", "-n", "1", commit).split()
                        == [commit, parent], "publication chain is not single-parent")
            records = [item for item in entries if item.get("commit_sha") == commit]
            versions = {item.get("version") for item in records}
            _pg_require(bool(records) and len(versions) == 1 and all(isinstance(item.get("run_id"), str)
                        and item["run_id"] for item in records), "publication ledger proof missing")
            version = next(iter(versions))
            _pg_require(isinstance(version, str) and bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)),
                        "publication version invalid")
            tag = "refs/tags/v" + version
            tag_proof = _pg_release_tag_proof(request, commands, tag, commit)
            _pg_require(json.loads(_pg_git(commands, actor, "show", commit + ":package.json")).get("version") == version,
                        "publication committed version differs")
            proofs.append({"commit_sha": commit, "version": version, "run_ids": [item["run_id"] for item in records],
                           **tag_proof})
        _pg_require(_pg_publication_ledger_snapshot(ledger_path)[0] == identity
                    and _pg_remote(request, commands).get("sha") == observed, "publication observation changed")
        return {"status": "PUBLISHED_DESCENDANT", "sha": observed, "ledger": identity, "proofs": proofs}
    except Exception as error:
        return {**remote, "status": "UNKNOWN", "publication_error": f"{type(error).__name__}: {error}"}


def _pg_health(request, receipt, commands):
    plan = receipt["plan"]
    state = Path(plan["state_root"])
    _pg_require(runtime_manifest._SHUTDOWN_LEASE.get() is None
                and os.environ.get("PANTHEON_RUNTIME_SHUTDOWN_LEASE_FD") is None,
                "postcheck cannot run under shutdown EX")
    _pg_require(receipt.get("ex_releases") and receipt["ex_releases"][-1].get("fd_closed") is True,
                "EX release terminal UNKNOWN")
    _pg_require(receipt.get("permit_revoked") is True
                and not runtime_manifest.shutdown_readiness_permit_path(state).exists(), "permit cleanup incomplete")
    commands.deadline = time.monotonic() + request.health_timeout_seconds
    with _pg_watchdog(request.health_timeout_seconds):
        observed = _pg_observe(request, commands, PUBGUARD_LABELS)
        pending = {}
        for label, item in observed.items():
            identity = item.get("identity") or {}
            _pg_require(item["topology"] == "LOADED", "health control UNKNOWN or service absent")
            _pg_require(_pg_activation().capture_file_identity(request.launch_agents_dir / f"{label}.plist")["sha256"]
                        == plan["staged_plists"][label]["sha256"], "normal plist readback mismatch")
            exits = identity.get("last_exit_codes", [])
            _pg_require(not exits or exits == [0], f"normal payload last exit nonzero: {label}")
            runs = identity.get("runs", [])
            pids = identity.get("pids", [])
            states = identity.get("states", [])
            _pg_require(len(runs) == 1 and runs[0] >= 0 and len(states) == 1,
                        "normal payload identity UNKNOWN")
            if len(pids) == 1 and pids[0] > 1 and states == ["running"]:
                pending[label] = "RUNNING_NATURAL_TICK"
            elif not pids and states[0] in _pg_activation().TERMINAL_SERVICE_STATES:
                if runs[0] < 1 or not exits:
                    pending[label] = "READY_PENDING_NATURAL_TICK"
            else:
                raise PromotionError(f"normal payload process state UNKNOWN: {label}")
        manifest = _pg_load_manifest(request.new_manifest_path, commands, plan["manifest_digest"])
        runtime_manifest.validate_barrier(Path(plan["barrier"]), manifest)
        five = _pg_check_five(request, commands, plan)
        receipt.setdefault("guard_observations", []).append(_pg_guard_clear(manifest))
        remote = _pg_published_remote(request, receipt, commands)
        _pg_require(remote["status"] in {"TARGET", "PUBLISHED_DESCENDANT"}, "remote health readback UNKNOWN")
        if "health" in receipt:
            receipt.setdefault("health_history", []).append(receipt["health"])
        receipt["health"] = {"services": observed, "five_services": five, "remote": remote,
                             "at": _utc_now(), "after_ex_release": True,
                             "pending_services": pending, "payload_completed": not pending,
                             "normal_natural_tick_completed": not pending}
        receipt["status"] = "POSTCHECK_PENDING" if pending else "HEALTHY"
        _pg_save(request, receipt)


def _pg_run_locked(request, *, expected_plan_digest, runner, recovering):
    activation = _pg_activation()
    receipt = activation.load_action_receipt(_pg_receipt_path(request))
    _pg_require(receipt.get("plan_digest") == expected_plan_digest
                and _json_digest(receipt["plan"]) == expected_plan_digest, "receipt plan digest mismatch")
    _pg_require(receipt["status"] != "PREPARING", "recovery materials not durably prepared")
    commands = _PublisherGuardCommands(request, receipt, runner)
    attempt = {"at": _utc_now(), "recovering": recovering, "outcome": "STARTED"}
    receipt["attempts"].append(attempt)
    _pg_save(request, receipt)
    try:
        with _pg_watchdog(300):
            # 靜態 authority 重驗；不以一次 plan 或舊 status 取代實測。
            static = _pg_spec(request, commands)
            sealed = {key: value for key, value in receipt["plan"].items()
                      if key not in {"old_plists", "initial_services"}}
            _pg_require(static == sealed, "sealed actor/manifest/controller/input drift")
            _pg_resume_commands(request, receipt)
            for label in PUBGUARD_LABELS:
                path = request.transaction_root / f"{label}.target.plist"
                _pg_require(file_sha256(path) == sealed["staged_plists"][label]["sha256"], "recovery payload missing")
            published = _pg_handoff_published(receipt)
            remote = (_pg_published_remote(request, receipt, commands) if published
                      else _pg_remote(request, commands))
            receipt["remote"] = remote
            _pg_save(request, receipt)
            allow_source_push = request.push_source and not recovering and not any(
                event["action"] == "source-push" for event in receipt["events"])
            _pg_require(remote["status"] in ({"TARGET", "PUBLISHED_DESCENDANT"} if published else {"TARGET"})
                        or (not published and remote["status"] == "OLD" and allow_source_push),
                        "remote OLD/UNKNOWN; no bootstrap or push")
        # 各 bounded 段獨立 timer；EX 上限含 acquire、可選的單次 push 及交接，另有五秒故障收尾。
        # barrier 一旦發布，apply/recover 永遠只 readback；running 或 pending 不可成為重啟理由。
        if not _pg_handoff_published(receipt):
            _pg_forward(request, receipt, commands, allow_source_push=allow_source_push)
        else:
            _pg_reconcile_published_cleanup(request, receipt, commands)
        _pg_health(request, receipt, commands)
        attempt["outcome"] = receipt["status"]
        _pg_save(request, receipt)
        return receipt
    except BaseException as error:
        receipt["status"] = "RECOVERY_REQUIRED"
        attempt.update(outcome="FAILED", error=f"{type(error).__name__}: {error}")
        receipt["errors"].append({"phase": "recover" if recovering else "apply", "error": attempt["error"], "at": _utc_now()})
        _pg_save(request, receipt)
        # 故障也要取得五服務 after 證據；取不到時保留 UNKNOWN 與原錯誤。
        try:
            commands.deadline = time.monotonic() + 5
            with _pg_watchdog(5):
                receipt["five_after_failure"] = {"status": "PASS", "observations":
                    _pg_check_five(request, commands, receipt["plan"])}
        except BaseException as readback_error:
            receipt["five_after_failure"] = {"status": "UNKNOWN", "error": f"{type(readback_error).__name__}: {readback_error}"}
            receipt["errors"].append({"phase": "five-after-failure", "error": receipt["five_after_failure"]["error"]})
        _pg_save(request, receipt)
        raise PromotionError(attempt["error"]) from error


def _pg_run(request, *, expected_plan_digest, runner, recovering):
    """只序列化本 receipt 的 writer；正式 runtime 排他仍由原 shutdown lease 負責。"""
    _pg_require(isinstance(expected_plan_digest, str) and bool(SHA256_PATTERN.fullmatch(expected_plan_digest)),
                "explicit expected plan digest required")
    prior = _pg_activation().load_action_receipt(_pg_receipt_path(request))
    _pg_require(prior.get("plan_digest") == expected_plan_digest
                and _json_digest(prior["plan"]) == expected_plan_digest,
                "receipt plan digest mismatch")
    request_payload = {key: [str(item) for item in value] if key == "staged_plists" else str(value)
                       if isinstance(value, Path) else value for key, value in vars(request).items()}
    _pg_require(prior["plan"]["request"] == request_payload, "sealed request mismatch")
    path = request.transaction_root / ".publisher-guard-controller.lock"
    _pg_require(request.transaction_root.resolve(strict=True) == request.transaction_root
                and stat.S_IMODE(request.transaction_root.stat().st_mode) == 0o700,
                "transaction directory identity changed")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        metadata = os.fstat(fd)
        _pg_require(metadata.st_uid == os.getuid() and stat.S_ISREG(metadata.st_mode)
                    and metadata.st_nlink == 1 and stat.S_IMODE(metadata.st_mode) == 0o600,
                    "controller writer lock invalid")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PromotionError("controller receipt writer busy") from error
        _pg_require((path.stat().st_dev, path.stat().st_ino) == (metadata.st_dev, metadata.st_ino),
                    "controller writer lock replaced")
        return _pg_run_locked(request, expected_plan_digest=expected_plan_digest, runner=runner, recovering=recovering)
    finally:
        os.close(fd)


def apply_publisher_guard(request: PublisherGuardRequest, *, expected_plan_digest: str, runner=None):
    """已 prepare 的交接；預設 target-only，僅 explicit opt-in 才在自持 EX 內送 source。"""
    return _pg_run(request, expected_plan_digest=expected_plan_digest, runner=runner, recovering=False)


def recover_publisher_guard(request: PublisherGuardRequest, *, expected_plan_digest: str, runner=None):
    """延續原 receipt、lineage 與錯誤；只重驗並 forward 到封存的新同版。"""
    return _pg_run(request, expected_plan_digest=expected_plan_digest, runner=runner, recovering=True)


def _pg_request_from_file(path):
    payload = _read_json(path)
    for field in ("source_repo", "old_manifest_path", "new_manifest_path", "launch_agents_dir", "transaction_root",
                  "capacity_receipt_path"):
        payload[field] = Path(payload[field])
    payload["staged_plists"] = tuple(Path(item) for item in payload["staged_plists"])
    return PublisherGuardRequest(**payload)


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
    for name in ("plan-publisher-guard", "prepare-publisher-guard", "apply-publisher-guard", "recover-publisher-guard"):
        command = subparsers.add_parser(name)
        command.add_argument("--request-json", type=Path, required=True)
        if name != "plan-publisher-guard":
            command.add_argument("--expected-plan-digest", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    if args.command.endswith("-publisher-guard"):
        try:
            request = _pg_request_from_file(args.request_json)
            functions = {"plan-publisher-guard": plan_publisher_guard,
                         "prepare-publisher-guard": prepare_publisher_guard,
                         "apply-publisher-guard": apply_publisher_guard,
                         "recover-publisher-guard": recover_publisher_guard}
            kwargs = {} if args.command == "plan-publisher-guard" else {"expected_plan_digest": args.expected_plan_digest}
            result = functions[args.command](request, **kwargs)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        except (Exception, KeyboardInterrupt) as error:
            print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
            return 1
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

#!/usr/bin/env python3
"""發布已通過 Gemini Reviewer 的文章 run。"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
import functools
import hashlib
from datetime import date, datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Callable

from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as pipeline
from scripts import pantheon_content_runtime_manifest as formal_runtime
from scripts.pantheon_runtime_fs_authority import (
    FilesystemAuthorityError,
    OperationTraceRecorder,
    TrustedSandboxDirectoryAuthority,
    summarize_operation_trace,
)


SCHEMA_VERSION = 1
RUNTIME_MANIFEST_SCHEMA_VERSION = 1
DEFAULT_MAX_RUNS = 3
PUBLISHER_ID = "agy-content-publisher"
LEGACY_ARTICLE_COUNT_CUTOFF = 353
LEGACY_CUTOFF_REASON = "articles present before automated Gemini publisher v0.3.1 / harness-new-*"
GitRunner = Callable[[Path, list[str], str | None], str]
TRANSACTION_RUNTIME_PATHS = (
    "app/core/article_publication_policy_v2.json",
    "scripts/agy_content_publisher.py",
    "scripts/agy_seo_copy_pipeline.py",
    "scripts/agy_multilingual_pipeline.py",
    "scripts/prerender_article_shells.py",
    "pnpm-lock.yaml",
    "uv.lock",
)
_TRANSACTION_RUNTIME_AUTHORITY: ContextVar[tuple[Path, Path] | None] = ContextVar(
    "publisher_transaction_runtime_authority",
    default=None,
)
PROJECT_PYTHON_COMMAND = [
    os.environ.get("PANTHEON_RUNTIME_UV_EXECUTABLE", "uv"),
    "run",
    "--frozen",
    "python",
]
TEST_COMMAND = [
    *PROJECT_PYTHON_COMMAND,
    "-m",
    "pytest",
    "tests/test_web.py",
    "tests/test_agy_seo_copy_pipeline.py",
    "tests/test_agy_multilingual_pipeline.py",
    "tests/test_release_record.py",
    "-q",
]
PREFLIGHT_TEST_COMMAND = [
    *PROJECT_PYTHON_COMMAND,
    "-m",
    "pytest",
    "tests/test_web.py::test_cloudflare_pages_wildcard_rewrite_uses_prerendered_product_hubs",
    "tests/test_web.py::test_tarot_hub_reading_guide_is_scanable",
    "tests/test_web.py::test_public_articles_follow_latest_publication_standard",
    "-q",
]
SUCCESS_STATUSES = {
    "PUBLISHED",
    "PUBLISHED_REWRITE",
    "PUBLISHED_TRANSLATION",
    "idle",
    "idle_rejects_only",
    "busy",
    "dry-run",
    "policy_rejected",
}
RETRY_DELAY_SECONDS = 300
MAX_RETRY_ATTEMPTS = 3
PRERENDER_TIMEOUT_SECONDS = 300
PUBLISHER_LOG_MAX_BYTES = 32 * 1024 * 1024
PUBLISHER_LOG_RETAIN_BYTES = 4 * 1024 * 1024
EXACT_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
RECEIPT_CAPABILITY_ORDINALS = {
    "select": 3,
    "publish": 4,
    "transaction": 5,
    "tag": 6,
    "push": 7,
}
RECEIPT_CONTEXT_KEYS = frozenset(
    {
        "execution_line_id",
        "correlation_id",
        "actor_identity",
        "runtime_identity_digest",
        "input_digest",
        "evidence_root",
        "positive_evidence",
        "negative_evidence",
        "push_mode",
        "tag_mode",
        "canary_created",
        "production_mutation",
    }
)
RECEIPT_CALLER_VERDICT_KEYS = frozenset({"status", "verdict", "ready", "valid"})
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


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


def release_git_plan(version: str) -> dict[str, list[str]]:
    """回傳正式 release 的 tag/push 命令；只建 plan，不執行 mutation。"""
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise PublishBlocked("release version is invalid")
    return {
        "tag": ["tag", "-a", f"v{version}", "-m", f"Pantheon content release v{version}"],
        "push": ["push", "--atomic", "origin", "HEAD:main", f"v{version}"],
    }


def _runtime_identity_digest_for_trace(runtime_receipt: dict[str, Any] | None) -> str:
    if not isinstance(runtime_receipt, dict) or runtime_receipt.get("status") != "PASS":
        raise PublishBlocked("publisher runtime identity receipt is required")
    digest = runtime_receipt.get("runtime_identity_digest")
    if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise PublishBlocked("publisher runtime identity receipt is invalid")
    return digest


def _compact_json_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _receipt_identifier(value: object, field: str) -> str:
    if type(value) is not str:
        raise PublishBlocked(f"publisher receipt {field} must be a string")
    if not value or value.strip() != value:
        raise PublishBlocked(f"publisher receipt {field} must be non-blank")
    return value


def _receipt_digest(value: object, field: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise PublishBlocked(f"publisher receipt {field} must be a sha256 digest")
    return value


def _receipt_evidence_identifier(value: object, field: str) -> str:
    identifier = _receipt_identifier(value, field)
    if (
        identifier.startswith("/")
        or "\\" in identifier
        or "//" in identifier
        or ":" in identifier
    ):
        raise PublishBlocked(f"publisher receipt {field} must be artifact-relative")
    parts = identifier.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PublishBlocked(f"publisher receipt {field} must not traverse")
    return identifier


def _publisher_receipt_context(
    raw_context: Mapping[str, Any] | None,
    *,
    sandbox_root: Path,
) -> dict[str, Any] | None:
    if raw_context is None:
        return None
    if not isinstance(raw_context, Mapping) or any(type(key) is not str for key in raw_context):
        raise PublishBlocked("publisher receipt context must be an object")
    evidence_root_value = raw_context.get("evidence_root")
    if type(evidence_root_value) is not str:
        raise PublishBlocked("publisher receipt evidence root must be a string")
    evidence_root = _require_sandbox_descendant(
        sandbox_root,
        Path(evidence_root_value),
        "receipt evidence root",
    )
    positive_evidence = _receipt_evidence_identifier(
        raw_context.get("positive_evidence"),
        "positive_evidence",
    )
    negative_evidence = _receipt_evidence_identifier(
        raw_context.get("negative_evidence"),
        "negative_evidence",
    )
    if positive_evidence == negative_evidence:
        raise PublishBlocked("publisher receipt evidence identifiers must be distinct")
    return {
        "execution_line_id": _receipt_identifier(
            raw_context.get("execution_line_id"),
            "execution_line_id",
        ),
        "correlation_id": raw_context.get("correlation_id"),
        "actor_identity": _receipt_identifier(
            raw_context.get("actor_identity"),
            "actor_identity",
        ),
        "runtime_identity_digest": raw_context.get("runtime_identity_digest"),
        "input_digest": _receipt_digest(raw_context.get("input_digest"), "input_digest"),
        "evidence_root": evidence_root,
        "positive_evidence": positive_evidence,
        "negative_evidence": negative_evidence,
        "raw_context": raw_context,
    }


def _validate_publisher_receipt_context_policy(
    receipt_context: dict[str, Any],
    *,
    capability: str,
    correlation_id: str,
    runtime_identity_digest: str,
) -> None:
    raw_context = receipt_context["raw_context"]
    if RECEIPT_CALLER_VERDICT_KEYS.intersection(raw_context):
        raise PublishBlocked("publisher receipt context contains caller verdict")
    unknown_keys = set(raw_context) - RECEIPT_CONTEXT_KEYS
    if unknown_keys:
        raise PublishBlocked("publisher receipt context contains unknown keys")
    context_correlation = raw_context.get("correlation_id")
    if context_correlation is not None and context_correlation != correlation_id:
        raise PublishBlocked("publisher receipt correlation identity drift")
    context_runtime_digest = raw_context.get("runtime_identity_digest")
    if (
        context_runtime_digest is not None
        and context_runtime_digest != runtime_identity_digest
    ):
        raise PublishBlocked("publisher receipt runtime identity drift")
    if raw_context.get("canary_created") not in {None, False}:
        raise PublishBlocked("publisher receipt canary authority is not allowed")
    if raw_context.get("production_mutation") not in {None, False}:
        raise PublishBlocked("publisher receipt production mutation is not allowed")
    if capability == "tag" and raw_context.get("tag_mode") not in {
        None,
        "injected-git-dry-run",
    }:
        raise PublishBlocked("publisher receipt tag mode must be dry-run")
    if capability == "push" and raw_context.get("push_mode") not in {
        None,
        "injected-git-dry-run",
    }:
        raise PublishBlocked("publisher receipt push mode must be dry-run")


def _write_receipt_evidence(
    *,
    sandbox_root: Path,
    receipt_context: dict[str, Any],
    identifier: str,
    payload: dict[str, Any],
) -> None:
    evidence_root = receipt_context["evidence_root"]
    evidence_path = evidence_root / identifier
    evidence_path = _require_sandbox_descendant(
        sandbox_root,
        evidence_path,
        "receipt evidence path",
    )
    relative = evidence_path.relative_to(sandbox_root)
    with TrustedSandboxDirectoryAuthority(sandbox_root) as sandbox_authority:
        fd = sandbox_authority.open_file(
            relative,
            flags=os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            mode=0o600,
        )
        try:
            os.write(
                fd,
                (
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    )
                    + "\n"
                ).encode("utf-8"),
            )
        finally:
            os.close(fd)


def _receipt_positive_payload(
    *,
    receipt_context: dict[str, Any],
    capability: str,
    correlation_id: str,
    runtime_identity_digest: str,
    boundary_result: dict[str, Any],
    output_digest: str,
) -> dict[str, Any]:
    sandbox_root = receipt_context["evidence_root"].parent

    def artifact_value(value: Any) -> Any:
        if isinstance(value, list):
            return [artifact_value(item) for item in value]
        if isinstance(value, dict):
            return {key: artifact_value(item) for key, item in value.items()}
        if isinstance(value, str) and value.startswith("/"):
            try:
                return Path(value).resolve(strict=False).relative_to(sandbox_root).as_posix()
            except ValueError:
                return "<outside-sandbox-path-redacted>"
        return value

    return {
        "schema_version": SCHEMA_VERSION,
        "capability": capability,
        "entrypoint": boundary_result["entrypoint"],
        "execution_line_id": receipt_context["execution_line_id"],
        "correlation_id": correlation_id,
        "actor_identity": receipt_context["actor_identity"],
        "runtime_identity_digest": runtime_identity_digest,
        "input_digest": receipt_context["input_digest"],
        "output_digest": output_digest,
        "outcome": "PASS",
        "stable_reason": "publisher_capability_passed",
        "operation_trace_digest": boundary_result["operation_trace_digest"],
        "production_mutation": False,
        "capability_boundary": {
            "boundary_status": boundary_result["boundary_status"],
            "called_entrypoints": boundary_result["called_entrypoints"],
            "git_trace": artifact_value(boundary_result["git_trace"]),
            "run_ids": boundary_result["run_ids"],
        },
    }


def _record_positive_receipt_step(
    *,
    sandbox_root: Path,
    receipt_context: dict[str, Any],
    capability: str,
    correlation_id: str,
    runtime_identity_digest: str,
    boundary_result: dict[str, Any],
) -> dict[str, Any]:
    trace_summary = summarize_operation_trace(boundary_result["operation_trace"])
    digest_material = {
        "capability": capability,
        "input_digest": receipt_context["input_digest"],
        "boundary_status": boundary_result["boundary_status"],
        "called_entrypoints": boundary_result["called_entrypoints"],
        "run_ids": boundary_result["run_ids"],
        "production_mutation": boundary_result["production_mutation"],
        "sandbox_mutation": boundary_result["sandbox_mutation"],
        "trace_summary": trace_summary,
    }
    output_digest = _compact_json_digest(digest_material)
    payload = _receipt_positive_payload(
        receipt_context=receipt_context,
        capability=capability,
        correlation_id=correlation_id,
        runtime_identity_digest=runtime_identity_digest,
        boundary_result=boundary_result,
        output_digest=output_digest,
    )
    _write_receipt_evidence(
        sandbox_root=sandbox_root,
        receipt_context=receipt_context,
        identifier=receipt_context["positive_evidence"],
        payload=payload,
    )
    return {
        "capability": capability,
        "ordinal": RECEIPT_CAPABILITY_ORDINALS[capability],
        "entrypoint": boundary_result["entrypoint"],
        "input_digest": receipt_context["input_digest"],
        "output_digest": output_digest,
        "execution_line_id": receipt_context["execution_line_id"],
        "correlation_id": correlation_id,
        "actor_identity": receipt_context["actor_identity"],
        "runtime_identity_digest": runtime_identity_digest,
        "positive_evidence": receipt_context["positive_evidence"],
        "negative_evidence": receipt_context["negative_evidence"],
        "positive_outcome": "PASS",
        "negative_outcome": "BLOCKED",
    }


def _record_blocked_receipt_evidence_or_fail(
    *,
    sandbox_root: Path,
    receipt_context: dict[str, Any] | None,
    capability: str,
    correlation_id: str,
    runtime_identity_digest: str | None,
    error: Exception,
) -> None:
    try:
        _record_blocked_receipt_evidence(
            sandbox_root=sandbox_root,
            receipt_context=receipt_context,
            capability=capability,
            correlation_id=correlation_id,
            runtime_identity_digest=runtime_identity_digest,
            error=error,
        )
    except Exception as write_error:
        write_error.__context__ = error
        raise PublishBlocked(
            "publisher blocked receipt evidence write failed: "
            f"{type(write_error).__name__}: {write_error}; "
            f"original blocked reason: {error}"
        ) from write_error


def _record_blocked_receipt_evidence(
    *,
    sandbox_root: Path,
    receipt_context: dict[str, Any] | None,
    capability: str,
    correlation_id: str,
    runtime_identity_digest: str | None,
    error: Exception,
) -> None:
    if receipt_context is None:
        return
    digest_material = {
        "capability": capability,
        "input_digest": receipt_context["input_digest"],
        "error_type": type(error).__name__,
        "stable_reason": str(error),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "capability": capability,
        "entrypoint": "scripts.agy_content_publisher:formal_capability_preflight",
        "execution_line_id": receipt_context["execution_line_id"],
        "correlation_id": correlation_id,
        "actor_identity": receipt_context["actor_identity"],
        "runtime_identity_digest": runtime_identity_digest or "",
        "input_digest": receipt_context["input_digest"],
        "output_digest": _compact_json_digest(digest_material),
        "outcome": "BLOCKED",
        "stable_reason": str(error),
        "error_type": type(error).__name__,
        "production_mutation": False,
    }
    _write_receipt_evidence(
        sandbox_root=sandbox_root,
        receipt_context=receipt_context,
        identifier=receipt_context["negative_evidence"],
        payload=payload,
    )


def _require_sandbox_descendant(
    sandbox_root: Path,
    candidate: Path,
    label: str,
) -> Path:
    if not candidate.is_absolute():
        raise PublishBlocked(f"publisher {label} must be absolute")
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise PublishBlocked(f"publisher {label} is invalid") from error
    if resolved == sandbox_root or not resolved.is_relative_to(sandbox_root):
        raise PublishBlocked(
            f"publisher {label} must be a strict sandbox descendant"
        )
    return resolved


def _formal_capability_dry_run_git(
    actor_root: Path,
    sandbox_root: Path,
    actor_sha: str,
    _repo_root: Path,
    args: list[str],
    _input_text: str | None = None,
    *,
    sandbox_authority: TrustedSandboxDirectoryAuthority | None = None,
) -> str:
    """只在 capability sandbox 模擬 Git I/O，禁止碰正式 repository。"""
    if args == ["rev-parse", "--git-common-dir"]:
        return str(
            _require_sandbox_descendant(
                sandbox_root,
                sandbox_root / ".git",
                "Git root",
            )
        )
    if args in (
        ["fetch", "origin", "main"],
        ["status", "--porcelain"],
        ["worktree", "prune"],
    ):
        return ""
    if args in (["rev-parse", "HEAD"], ["rev-parse", "origin/main"]):
        return actor_sha
    if args[:3] == ["worktree", "add", "--detach"] and len(args) == 5:
        transaction_root = _require_sandbox_descendant(
            sandbox_root,
            Path(args[3]),
            "transaction root",
        )
        transaction_relative = transaction_root.relative_to(sandbox_root)
        for relative in TRANSACTION_RUNTIME_PATHS:
            source = actor_root / relative
            target_relative = transaction_relative / relative
            if sandbox_authority is None:
                target = transaction_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            else:
                sandbox_authority.copy_file(source, target_relative)
        return ""
    if args[:3] == ["worktree", "remove", "--force"] and len(args) == 4:
        transaction_root = _require_sandbox_descendant(
            sandbox_root,
            Path(args[3]),
            "transaction root",
        )
        if sandbox_authority is None:
            shutil.rmtree(transaction_root, ignore_errors=True)
        else:
            sandbox_authority.remove_tree(transaction_root.relative_to(sandbox_root))
        return ""
    if args and args[0] in {"add", "commit", "tag", "push"}:
        return ""
    raise PublishBlocked(f"unsupported capability dry-run git command: {args}")


def formal_capability_preflight(
    capability: str,
    *,
    run_ids: Iterable[str],
    correlation_id: str,
    trusted_sandbox_root: Path | None = None,
    queue_root: Path | None = None,
    state_root: Path | None = None,
    runtime_receipt: dict[str, Any] | None = None,
    receipt_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """正式 publisher 的公開 bounded validation/transaction/tag/push dry-run 入口。"""
    normalized_receipt_context: dict[str, Any] | None = None
    runtime_identity_digest: str | None = None
    if trusted_sandbox_root is None or queue_root is None or state_root is None:
        raise PublishBlocked("publisher sandbox authority is required")
    if capability not in {"select", "publish", "transaction", "tag", "push"}:
        raise PublishBlocked("publisher capability is invalid")
    sandbox_root = Path(trusted_sandbox_root)
    operation_trace: OperationTraceRecorder | None = None
    try:
        if not correlation_id:
            raise PublishBlocked("publisher capability identity is incomplete")
        if not sandbox_root.is_absolute():
            raise PublishBlocked("publisher sandbox authority must be absolute")
        try:
            resolved_sandbox = sandbox_root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise PublishBlocked("publisher sandbox authority is invalid") from error
        if resolved_sandbox != sandbox_root or not resolved_sandbox.is_dir():
            raise PublishBlocked("publisher sandbox authority is not canonical")
        sandbox_root = resolved_sandbox
        runtime_identity_digest = _runtime_identity_digest_for_trace(runtime_receipt)
        normalized_receipt_context = _publisher_receipt_context(
            receipt_context,
            sandbox_root=sandbox_root,
        )
        if normalized_receipt_context is not None:
            _validate_publisher_receipt_context_policy(
                normalized_receipt_context,
                capability=capability,
                correlation_id=correlation_id,
                runtime_identity_digest=runtime_identity_digest,
            )
        try:
            selected = sorted(_normalize_exact_run_ids(run_ids) or ())
        except ValueError as error:
            raise PublishBlocked(str(error)) from error
        if not selected:
            raise PublishBlocked("publisher capability identity is incomplete")
        with TrustedSandboxDirectoryAuthority(sandbox_root) as sandbox_authority:
            operation_trace = OperationTraceRecorder(
                anchor_root=sandbox_root,
                anchor_identity=sandbox_authority.identity,
                correlation_id=correlation_id,
                runtime_identity_digest=runtime_identity_digest,
            )
            queue_root = _require_sandbox_descendant(
                sandbox_root,
                Path(queue_root),
                "queue root",
            )
            state_root = _require_sandbox_descendant(
                sandbox_root,
                Path(state_root),
                "publisher state root",
            )
            if (
                queue_root == state_root
                or queue_root.is_relative_to(state_root)
                or state_root.is_relative_to(queue_root)
            ):
                raise PublishBlocked("publisher queue and state roots must not overlap")
            queue_relative = queue_root.relative_to(sandbox_root)
            state_relative = state_root.relative_to(sandbox_root)
            mutation_before = (
                sandbox_authority.exists(queue_relative),
                sandbox_authority.exists(state_relative),
                sandbox_authority.exists(state_relative / "publisher.lock"),
                sandbox_authority.exists(".git"),
            )
            operation_trace.record_path_operation(
                "filesystem-mkdir",
                queue_root,
                lambda: sandbox_authority.makedirs(queue_relative),
            )
            operation_trace.record_path_operation(
                "filesystem-mkdir",
                state_root,
                lambda: sandbox_authority.makedirs(state_relative),
            )
            actor_root = Path(
                os.environ.get(
                    "PANTHEON_RUNTIME_ACTOR_ROOT",
                    Path(__file__).resolve().parents[1],
                )
            ).resolve()
            actor_sha = run_git(actor_root, ["rev-parse", "HEAD"], None)
            if re.fullmatch(r"[0-9a-f]{40}", actor_sha) is None:
                raise PublishBlocked("publisher actor runtime identity is invalid")
            git_trace: list[list[str]] = []

            def dry_run_git(
                repo_root: Path,
                args: list[str],
                input_text: str | None = None,
            ) -> str:
                git_trace.append(list(args))
                operation_name = ""
                operation_target: Path | None = None
                if args[:3] == ["worktree", "add", "--detach"] and len(args) == 5:
                    operation_name = "git-worktree-add"
                    operation_target = Path(args[3])
                elif args[:3] == ["worktree", "remove", "--force"] and len(args) == 4:
                    operation_name = "git-worktree-remove"
                    operation_target = Path(args[3])
                if operation_name and operation_target is not None:
                    return operation_trace.record_path_operation(
                        operation_name,
                        operation_target,
                        lambda: _formal_capability_dry_run_git(
                            actor_root,
                            sandbox_root,
                            actor_sha,
                            repo_root,
                            args,
                            input_text,
                            sandbox_authority=sandbox_authority,
                        ),
                    )
                return _formal_capability_dry_run_git(
                    actor_root,
                    sandbox_root,
                    actor_sha,
                    repo_root,
                    args,
                    input_text,
                    sandbox_authority=sandbox_authority,
                )

            called: list[Callable[..., object]] = [_normalize_exact_run_ids]
            boundary_status = "PASS"
            boundary_result: dict[str, Any] = {}
            if capability == "select":
                boundary_result["validation_mode"] = "exact-run-id"
            elif capability == "publish":
                publish_result = publish_ready_runs(
                    actor_root,
                    queue_root,
                    state_root,
                    dry_run=True,
                    push=False,
                    run_tests=False,
                    release_gate=False,
                    git=dry_run_git,
                    exact_run_ids=selected,
                    seed_translations=False,
                )
                boundary_status = str(publish_result.get("status") or "")
                if boundary_status not in {"dry-run", "idle"}:
                    raise PublishBlocked(
                        f"publisher dry-run returned unexpected status: {boundary_status or 'missing'}"
                    )
                base_sha = publish_result.get("base_sha")
                if (
                    type(base_sha) is not str
                    or re.fullmatch(r"[0-9a-f]{40}", base_sha) is None
                ):
                    raise PublishBlocked("publisher dry-run runtime identity is missing")
                if boundary_status == "dry-run":
                    ready_runs = publish_result.get("ready_runs")
                    if (
                        not isinstance(ready_runs, list)
                        or not ready_runs
                        or any(run_id not in selected for run_id in ready_runs)
                    ):
                        raise PublishBlocked("publisher dry-run run identity is invalid")
                called.append(publish_ready_runs)
                boundary_result["publisher_result"] = publish_result
            elif capability == "transaction":
                with _isolated_transaction_worktree(
                    actor_root,
                    state_root,
                    dry_run_git,
                    operation_trace=operation_trace,
                    sandbox_authority=sandbox_authority,
                    transaction_name=(
                        "transaction-"
                        + hashlib.sha256(
                            f"{correlation_id}:transaction:{actor_sha}".encode()
                        ).hexdigest()[:24]
                    ),
                ):
                    pass
                called.append(_isolated_transaction_worktree)
                boundary_result["transaction_mode"] = "injected-git-dry-run"
            else:
                commit_sha = _stage_commit_tag_push(
                    actor_root,
                    "0.0.0",
                    dry_run_git,
                    push=capability == "push",
                    release_gate=False,
                    checked_runner=lambda _repo_root, _args: None,
                )
                if re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None:
                    raise PublishBlocked("publisher release dry-run returned invalid commit sha")
                called.append(_stage_commit_tag_push)
                boundary_result["candidate_sha"] = commit_sha
                boundary_result["release_mode"] = "injected-git-dry-run"

            mutation_after = (
                sandbox_authority.exists(queue_relative),
                sandbox_authority.exists(state_relative),
                sandbox_authority.exists(state_relative / "publisher.lock"),
                sandbox_authority.exists(".git"),
            )
            trace_summary = summarize_operation_trace(operation_trace.events())
            production_mutation = trace_summary["production_mutation"]
            if production_mutation:
                raise PublishBlocked("publisher capability mutation escaped sandbox")
            operation_trace_events = operation_trace.events()
            result = {
                "status": "PASS",
                "boundary_status": boundary_status,
                "capability": capability,
                "run_ids": selected,
                "correlation_id": correlation_id,
                "production_mutation": production_mutation,
                "sandbox_mutation": (
                    mutation_before != mutation_after
                    or trace_summary["sandbox_mutation"]
                ),
                "operation_trace": operation_trace_events,
                "operation_trace_digest": operation_trace.digest(),
                "entrypoint": "scripts.agy_content_publisher:formal_capability_preflight",
                "called_entrypoints": [
                    f"{entrypoint.__module__}:{entrypoint.__name__}"
                    for entrypoint in called
                ],
                "git_trace": git_trace,
                **boundary_result,
            }
            if normalized_receipt_context is not None:
                result["receipt_step"] = _record_positive_receipt_step(
                    sandbox_root=sandbox_root,
                    receipt_context=normalized_receipt_context,
                    capability=capability,
                    correlation_id=correlation_id,
                    runtime_identity_digest=runtime_identity_digest,
                    boundary_result=result,
                )
            return result
    except FilesystemAuthorityError as error:
        blocked = PublishBlocked("publisher sandbox authority identity drift")
        _record_blocked_receipt_evidence_or_fail(
            sandbox_root=sandbox_root,
            receipt_context=normalized_receipt_context,
            capability=capability,
            correlation_id=correlation_id,
            runtime_identity_digest=runtime_identity_digest,
            error=blocked,
        )
        raise blocked from error
    except PublishBlocked as error:
        _record_blocked_receipt_evidence_or_fail(
            sandbox_root=sandbox_root,
            receipt_context=normalized_receipt_context,
            capability=capability,
            correlation_id=correlation_id,
            runtime_identity_digest=runtime_identity_digest,
            error=error,
        )
        raise
    if operation_trace is None:
        raise PublishBlocked("publisher operation trace is unavailable")


class PublishBlocked(ValueError):
    """發布 gate fail-closed。"""


class PolicyRejected(PublishBlocked):
    """Required policy finding；屬 terminal content state，不是 transport failure。"""

    def __init__(self, findings: list[dict[str, Any]]) -> None:
        self.findings = pipeline.required_policy_findings(findings)
        codes = sorted(
            {str(finding.get("code") or "unknown") for finding in self.findings}
        )
        super().__init__(
            "policy v2 required rejection: " + ",".join(codes or ["unknown"])
        )


class PrerenderTimeout(PublishBlocked):
    """預渲染子程序逾時；保留可重驗的最小診斷。"""

    def __init__(self, diagnostic: dict[str, object]) -> None:
        self.diagnostic = diagnostic
        super().__init__(
            "prerender subprocess timed out: "
            + json.dumps(diagnostic, sort_keys=True)
        )


class PushOutcomeUnknown(PublishBlocked):
    """遠端 atomic push 結果無法安全判定。"""


def _validate_formal_runtime(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
) -> dict[str, Any]:
    actor_root = repo_root.resolve()
    transaction_authority = _TRANSACTION_RUNTIME_AUTHORITY.get()
    if (
        transaction_authority is not None
        and actor_root == transaction_authority[1]
    ):
        _assert_transaction_runtime_matches(*transaction_authority)
        actor_root = transaction_authority[0]
    return formal_runtime.validate_runtime_tick(
        "com.pantheon.agy-content-publisher",
        queue_root=queue_root.resolve(),
        state_root=state_root.resolve(),
        actor_root=actor_root,
        log_root=Path(os.environ.get("PANTHEON_RUNTIME_LOG_ROOT", Path.cwd())),
    )


def runtime_manifest(repo_root: Path) -> dict[str, Any]:
    """以封閉 path set 建立 Publisher runtime bytes manifest。"""
    paths = sorted(TRANSACTION_RUNTIME_PATHS)
    if not paths or len(paths) != len(set(paths)):
        raise PublishBlocked("publisher runtime manifest paths are invalid")
    files: list[dict[str, Any]] = []
    for relative in paths:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise PublishBlocked("publisher runtime manifest path is invalid")
        path = repo_root / relative_path
        if not path.is_file():
            raise PublishBlocked(
                f"publisher runtime manifest path is missing: {relative}"
            )
        body = path.read_bytes()
        files.append(
            {
                "path": relative,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    return {
        "schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "files": files,
    }


def _runtime_manifest_digest(manifest: dict[str, Any]) -> str:
    encoded = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def runtime_manifest_digest(repo_root: Path) -> str:
    return _runtime_manifest_digest(runtime_manifest(repo_root))


class MutationJournal:
    """記錄 publisher write-set 的 pre/post image，避免 recovery 覆寫並行 bytes。"""

    def __init__(self, repo_root: Path, git: GitRunner) -> None:
        self.repo_root = repo_root
        self.git = git
        self.pre_images: dict[str, bytes | None] = {}
        self.expected_post_images: dict[str, bytes | None] = {}
        self.unattributed_paths: set[str] = set()
        self.selected_run_ids: list[str] = []
        self.mutation_started = False

    def _owned_files(self) -> set[str]:
        paths = set(_git_paths(self.repo_root, self.git, ["ls-files", "-co", "--exclude-standard", "-z"]))
        return {path for path in paths if _publisher_owned_path(path)}

    def _read(self, relative: str) -> bytes | None:
        path = self.repo_root / relative
        return path.read_bytes() if path.is_file() else None

    def begin(self) -> None:
        if self.mutation_started:
            return
        self.pre_images = {relative: self._read(relative) for relative in self._owned_files()}
        self.expected_post_images = dict(self.pre_images)
        self.mutation_started = True

    def checkpoint(self, post_images: dict[str, bytes | None] | list[str] | None = None) -> None:
        if not self.mutation_started:
            return
        if not isinstance(post_images, dict):
            paths = post_images or sorted(self._owned_files())
            for relative in paths:
                if _publisher_owned_path(relative):
                    self.pre_images.setdefault(relative, None)
                    self.unattributed_paths.add(relative)
            return
        for relative, post_image in post_images.items():
            if _publisher_owned_path(relative):
                self.pre_images.setdefault(relative, None)
                self.expected_post_images[relative] = post_image
                self.unattributed_paths.discard(relative)

    def capture(self, mutation: Callable[[], Any]) -> Any:
        """在單一 publisher helper 邊界內捕捉可歸因的 before/after image。"""
        if not self.mutation_started:
            return mutation()
        before_paths = self._owned_files() | set(self.pre_images)
        before = {relative: self._read(relative) for relative in before_paths}
        try:
            return mutation()
        finally:
            after_paths = self._owned_files() | set(before)
            after = {relative: self._read(relative) for relative in after_paths}
            self.checkpoint(
                {
                    relative: after.get(relative)
                    for relative in before_paths | after_paths
                    if before.get(relative) != after.get(relative)
                }
            )

    def select_runs(self, run_ids: list[str]) -> None:
        self.selected_run_ids = list(run_ids)

    def image_metadata(self) -> dict[str, dict[str, str | bool | None]]:
        relatives = sorted(set(self.pre_images) | set(self.expected_post_images))
        return {
            relative: {
                "pre_exists": self.pre_images.get(relative) is not None,
                "pre_sha256": _bytes_sha256(self.pre_images.get(relative)),
                "expected_post_exists": self.expected_post_images.get(relative) is not None,
                "expected_post_sha256": _bytes_sha256(self.expected_post_images.get(relative)),
                "attributed": relative not in self.unattributed_paths,
            }
            for relative in sorted(set(relatives) | self.unattributed_paths)
        }


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _trim_log_file(
    path: Path,
    *,
    max_bytes: int = PUBLISHER_LOG_MAX_BYTES,
    retain_bytes: int = PUBLISHER_LOG_RETAIN_BYTES,
) -> bool:
    """同 inode 保留 log 尾端，避免破壞 launchd 已開啟的輸出描述符。"""
    if max_bytes <= 0 or retain_bytes <= 0 or retain_bytes >= max_bytes:
        raise ValueError("log limits must satisfy 0 < retain_bytes < max_bytes")
    try:
        with path.open("r+b") as log:
            log.seek(0, os.SEEK_END)
            size = log.tell()
            if size <= max_bytes:
                return False
            log.seek(-min(size, retain_bytes), os.SEEK_END)
            tail = log.read()
            log.seek(0)
            log.write(tail)
            log.truncate()
    except FileNotFoundError:
        return False
    return True


def _trim_configured_launchd_logs() -> None:
    for variable in (
        "PANTHEON_PUBLISHER_STDOUT_LOG",
        "PANTHEON_PUBLISHER_STDERR_LOG",
    ):
        configured = os.environ.get(variable)
        if configured:
            _trim_log_file(Path(configured).expanduser())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    pipeline.write_json(path, payload)


def _bytes_sha256(value: bytes | None) -> str | None:
    return hashlib.sha256(value).hexdigest() if value is not None else None


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _repo_lock_path(
    repo_root: Path,
    git: GitRunner,
    operation_trace: OperationTraceRecorder | None = None,
    sandbox_authority: TrustedSandboxDirectoryAuthority | None = None,
) -> Path:
    try:
        common_dir = Path(git(repo_root, ["rev-parse", "--git-common-dir"], None))
        if not common_dir.is_absolute():
            common_dir = repo_root / common_dir
    except (OSError, subprocess.CalledProcessError):
        common_dir = repo_root / ".git"
    if operation_trace is None:
        common_dir.mkdir(parents=True, exist_ok=True)
    elif sandbox_authority is not None:
        try:
            relative_common_dir = common_dir.relative_to(sandbox_authority.root)
        except ValueError as error:
            raise FilesystemAuthorityError(
                "sandbox relative target escaped sandbox"
            ) from error
        operation_trace.record_path_operation(
            "filesystem-git-common-dir-mkdir",
            common_dir,
            lambda: sandbox_authority.makedirs(relative_common_dir),
        )
    else:
        operation_trace.record_path_operation(
            "filesystem-git-common-dir-mkdir",
            common_dir,
            lambda: common_dir.mkdir(parents=True, exist_ok=True),
        )
    return common_dir / "agy-content-publisher.transaction.lock"


def _retry_path(state_root: Path, phase: str, run_id: str) -> Path:
    safe_run_id = re.sub(r"[^A-Za-z0-9._-]+", "-", run_id).strip("-") or "unknown"
    return state_root / "retry" / phase / f"{safe_run_id}.json"


def _policy_rejection_path(state_root: Path, phase: str, run_id: str) -> Path:
    safe_run_id = re.sub(r"[^0-9A-Za-z._-]+", "-", run_id).strip("-") or "unknown"
    return state_root / "policy-rejections" / phase / f"{safe_run_id}.json"


def _record_policy_rejection(
    state_root: Path,
    phase: str,
    state: dict[str, Any],
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
) -> Path:
    """Policy rejection 是 terminal content state，不建立 transport retry。"""
    run_id = str(state.get("run_id") or candidate.get("run_id") or "unknown")
    article_ids = [
        str(article.get("id") or article.get("article_id") or "")
        for article in candidate.get("articles") or []
        if isinstance(article, dict)
    ]
    required = pipeline.required_policy_findings(findings)
    input_hash = hashlib.sha256(pipeline.compact_json_bytes(candidate)).hexdigest()
    path = _policy_rejection_path(state_root, phase, run_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "POLICY_REJECTED",
        "terminal": True,
        "retry_eligible": False,
        "policy_version": pipeline.publication_policy_version(),
        "validator_result": "FAIL",
        "run_id": run_id,
        "article_ids": article_ids,
        "failure_codes": sorted({str(item.get("code") or "unknown") for item in required}),
        "findings": required,
        "input_hash": input_hash,
        "recorded_at": _now(),
    }
    if path.is_file():
        existing = _read_json(path)
        if existing.get("input_hash") == input_hash:
            return path
    _atomic_write_json(path, payload)
    _record_quarantine(
        state_root,
        state,
        f"policy_v2_required:{','.join(payload['failure_codes'])}",
    )
    return path


def _record_runtime_policy_rejections(
    queue_root: Path,
    state_root: Path,
    phase: str,
    run_ids: list[str],
    error: PolicyRejected,
) -> list[Path]:
    """把 mutation 後的 prerender policy failure 綁回 candidate run。"""
    states: dict[str, dict[str, Any]] = {}
    for state_path in _run_files(queue_root):
        try:
            state = _read_json(state_path)
        except (OSError, json.JSONDecodeError):
            continue
        run_id = str(state.get("run_id") or "")
        if run_id in run_ids:
            states[run_id] = state
    recorded: list[Path] = []
    for run_id in run_ids:
        state = states.get(run_id)
        if state is None:
            raise PublishBlocked(
                f"policy rejection state missing for runtime run: {run_id}"
            ) from error
        run_dir = Path(str(state.get("run_dir") or ""))
        result = state.get("result") if isinstance(state.get("result"), dict) else {}
        candidate_path = Path(
            str(result.get("candidate") or run_dir / "candidate.json")
        )
        candidate = _read_json(candidate_path)
        article_ids = {
            str(article.get("id") or article.get("article_id") or "")
            for article in candidate.get("articles") or []
            if isinstance(article, dict)
        }
        findings = [
            finding
            for finding in error.findings
            if str(finding.get("article_id") or "") in article_ids
        ]
        if not findings:
            continue
        recorded.append(
            _record_policy_rejection(
                state_root,
                phase,
                state,
                candidate,
                findings,
            )
        )
    if not recorded:
        raise PublishBlocked(
            "runtime policy rejection did not match any selected candidate"
        ) from error
    return recorded


def _unresolved_push_path(state_root: Path) -> Path:
    return state_root / "push-outcome-unresolved.json"


def _assert_no_unresolved_push(state_root: Path) -> None:
    path = _unresolved_push_path(state_root)
    if path.is_file():
        raise PublishBlocked(f"unresolved push control record blocks publisher mutation: {path}")


def _reconcile_unresolved_push(repo_root: Path, state_root: Path, git: GitRunner) -> dict[str, Any]:
    """只在 remote、ledger 與 publish evidence 全部收斂後清除 push control。"""
    path = _unresolved_push_path(state_root)
    if not path.is_file():
        raise PublishBlocked("no unresolved push control record to reconcile")
    control = _read_json(path)
    candidate_sha = str(control.get("candidate_sha") or "")
    version = str(control.get("version") or "")
    phase = str(control.get("phase") or "")
    run_ids = [str(run_id) for run_id in control.get("run_ids", [])]
    if not candidate_sha or not version or phase not in {"create", "rewrite", "translation"} or not run_ids:
        raise PublishBlocked("unresolved push control record is invalid")

    git(repo_root, ["fetch", "origin", "main"], None)
    remote_main = git(repo_root, ["rev-parse", "origin/main"], None)
    remote_tags = git(
        repo_root,
        ["ls-remote", "origin", f"refs/tags/v{version}", f"refs/tags/v{version}^{{}}"],
        None,
    )
    reconcile_ref = f"refs/agy-publisher-reconcile/v{version}"
    remote_tag = ""
    if remote_tags.strip():
        try:
            git(repo_root, ["fetch", "--force", "origin", f"refs/tags/v{version}:{reconcile_ref}"], None)
            remote_tag = git(repo_root, ["rev-parse", f"{reconcile_ref}^{{}}"], None)
        finally:
            git(repo_root, ["update-ref", "-d", reconcile_ref], None)
    if remote_main != candidate_sha or remote_tag != candidate_sha:
        raise PublishBlocked("unresolved push remote refs have not converged")

    ledger_key = {
        "create": "published_runs",
        "rewrite": "rewrite_released_runs",
        "translation": "translation_published_runs",
    }[phase]
    ledger = _load_ledger(state_root)
    converged_runs = {
        str(item.get("run_id"))
        for item in ledger[ledger_key]
        if item.get("version") == version and item.get("commit_sha") == candidate_sha
    }
    if not set(run_ids).issubset(converged_runs):
        raise PublishBlocked("unresolved push ledger has not converged")

    evidence_path = Path(str(control.get("publish_evidence") or ""))
    if not evidence_path.is_file():
        raise PublishBlocked("unresolved push publish evidence has not converged")
    evidence = _read_json(evidence_path)
    expected_status = {
        "create": "PUBLISHED",
        "rewrite": "PUBLISHED_REWRITE",
        "translation": "PUBLISHED_TRANSLATION",
    }[phase]
    if (
        evidence.get("status") != expected_status
        or evidence.get("commit_sha") != candidate_sha
        or evidence.get("version") != version
        or not set(run_ids).issubset({str(run_id) for run_id in evidence.get("run_ids", [])})
    ):
        raise PublishBlocked("unresolved push publish evidence has not converged")

    path.unlink()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PUSH_OUTCOME_RECONCILED",
        "candidate_sha": candidate_sha,
        "version": version,
        "phase": phase,
        "run_ids": run_ids,
    }


def _retry_eligibility(state_root: Path, phase: str, run_id: str) -> str:
    path = _retry_path(state_root, phase, run_id)
    if not path.is_file():
        return "eligible"
    try:
        retry = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return "invalid"
    if not isinstance(retry, dict):
        return "invalid"
    try:
        attempts = int(retry.get("attempts", 0))
    except (TypeError, ValueError):
        return "invalid"
    if attempts >= MAX_RETRY_ATTEMPTS:
        return "exhausted"
    try:
        next_eligible = datetime.fromisoformat(str(retry["next_eligible_at"]))
        return (
            "eligible"
            if datetime.now().astimezone() >= next_eligible
            else "deferred"
        )
    except (KeyError, TypeError, ValueError):
        return "invalid"


def _retry_eligible(state_root: Path, phase: str, run_id: str) -> bool:
    return _retry_eligibility(state_root, phase, run_id) == "eligible"


def _record_retry_failure(
    state_root: Path,
    phase: str,
    run_ids: list[str],
    error: Exception,
    evidence_path: Path,
) -> None:
    for run_id in run_ids:
        path = _retry_path(state_root, phase, run_id)
        previous = _read_json(path) if path.is_file() else {}
        attempts = int(previous.get("attempts", 0)) + 1
        delay = RETRY_DELAY_SECONDS * (2 ** min(attempts - 1, 4))
        _atomic_write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "phase": phase,
                "run_id": run_id,
                "attempts": attempts,
                "max_attempts": MAX_RETRY_ATTEMPTS,
                "error_type": type(error).__name__,
                "error": str(error),
                "evidence": str(evidence_path),
                "last_attempt_at": _now(),
                "next_eligible_at": (datetime.now().astimezone() + timedelta(seconds=delay)).isoformat(timespec="seconds"),
                "eligibility": "exhausted" if attempts >= MAX_RETRY_ATTEMPTS else "deferred",
                "candidate_preserved": True,
                "recovery_count": int(previous.get("recovery_count", 0)),
                "last_recovery_id": previous.get("last_recovery_id"),
            },
        )


@contextmanager
def _retry_recovery_lock(
    state_root: Path,
    *,
    dry_run: bool,
) -> Iterator[None]:
    if dry_run:
        yield
        return
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PublishBlocked("publisher is busy") from error
        yield


def recover_exhausted_create_retries(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    run_ids: list[str],
    expected_error: str,
    reason: str,
    expected_recovery_digest: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """驗證並恢復指定 create run 的 retry budget，同時保存可稽核 receipt。"""
    normalized_run_ids = [run_id.strip() for run_id in run_ids if run_id.strip()]
    if not normalized_run_ids or len(normalized_run_ids) != len(set(normalized_run_ids)):
        raise PublishBlocked("retry recovery run ids are empty or duplicated")
    expected_error = expected_error.strip()
    reason = reason.strip()
    if not expected_error:
        raise PublishBlocked("retry recovery expected error is required")
    if len(reason) < 8 or len(reason) > 500:
        raise PublishBlocked("retry recovery reason length is invalid")

    with _retry_recovery_lock(state_root, dry_run=dry_run):
        _assert_no_unresolved_push(state_root)
        ledger = _load_ledger(state_root)
        published = {
            str(item.get("run_id")) for item in ledger["published_runs"]
        }
        quarantined = {
            str(item.get("run_id")) for item in ledger["quarantined_runs"]
        }
        reference_articles = pipeline.load_publication_reference_corpus(repo_root)
        states_by_run: dict[str, list[Path]] = {
            run_id: [] for run_id in normalized_run_ids
        }
        for state_path in _run_files(queue_root):
            try:
                run_id = str(_read_json(state_path).get("run_id") or "")
            except (OSError, json.JSONDecodeError):
                continue
            if run_id in states_by_run:
                states_by_run[run_id].append(state_path)

        validated: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        for run_id in normalized_run_ids:
            if run_id in published:
                raise PublishBlocked(f"retry recovery run already published: {run_id}")
            if run_id in quarantined:
                raise PublishBlocked(f"retry recovery run is quarantined: {run_id}")
            if _policy_rejection_path(state_root, "create", run_id).exists():
                raise PublishBlocked(
                    f"retry recovery run has terminal policy rejection: {run_id}"
                )
            state_paths = states_by_run[run_id]
            if len(state_paths) != 1:
                raise PublishBlocked(
                    f"retry recovery requires one queue state for {run_id}"
                )
            state, candidate, review = _load_completed_run(state_paths[0])
            if candidate.get("mode") != "create":
                raise PublishBlocked(
                    f"retry recovery only supports create mode: {run_id}"
                )
            if not _review_is_clean_approve(review):
                raise PublishBlocked(
                    f"retry recovery reviewer approval is not clean: {run_id}"
                )
            findings = (
                pipeline.quality_findings(
                    candidate["articles"],
                    reference_articles=reference_articles,
                )
                if reference_articles
                else pipeline.quality_findings(candidate["articles"])
            )
            if findings:
                raise PublishBlocked(
                    f"retry recovery candidate no longer passes policy: {run_id}"
                )

            retry_path = _retry_path(state_root, "create", run_id)
            if not retry_path.is_file():
                raise PublishBlocked(
                    f"retry recovery record is missing: {run_id}"
                )
            retry_bytes = retry_path.read_bytes()
            retry = json.loads(retry_bytes)
            if (
                retry.get("schema_version") != SCHEMA_VERSION
                or retry.get("phase") != "create"
                or retry.get("run_id") != run_id
            ):
                raise PublishBlocked(
                    f"retry recovery record contract is invalid: {run_id}"
                )
            if (
                retry.get("eligibility") != "exhausted"
                or int(retry.get("attempts", -1)) < MAX_RETRY_ATTEMPTS
                or int(retry.get("max_attempts", -1)) != MAX_RETRY_ATTEMPTS
            ):
                raise PublishBlocked(
                    f"retry recovery record is not exhausted: {run_id}"
                )
            if retry.get("candidate_preserved") is not True:
                raise PublishBlocked(
                    f"retry recovery candidate preservation is not proven: {run_id}"
                )
            if str(retry.get("error") or "") != expected_error:
                raise PublishBlocked(
                    f"retry error differs from operator expectation: {run_id}"
                )

            evidence_path = Path(str(retry.get("evidence") or "")).resolve()
            if (
                not evidence_path.is_relative_to(state_root.resolve())
                or not evidence_path.is_file()
            ):
                raise PublishBlocked(
                    f"retry recovery evidence path is invalid: {run_id}"
                )
            failure_bytes = evidence_path.read_bytes()
            failure = json.loads(failure_bytes)
            if (
                failure.get("status") != "FAILED_RECOVERED"
                or failure.get("phase") != "create"
                or failure.get("repo_recovered") is not True
                or failure.get("status_after_recovery") not in (None, [])
                or failure.get("concurrent_write_conflicts") not in (None, [])
            ):
                raise PublishBlocked(
                    f"retry failure evidence is not fully recovered: {run_id}"
                )
            if failure.get("retry_status") != "candidate_preserved":
                raise PublishBlocked(
                    f"retry candidate preservation is not proven: {run_id}"
                )
            if failure.get("error_type") != retry.get("error_type"):
                raise PublishBlocked(
                    f"retry failure type is not bound to record: {run_id}"
                )
            if run_id not in {
                str(item) for item in failure.get("run_ids", [])
            }:
                raise PublishBlocked(
                    f"retry failure evidence is not bound to run: {run_id}"
                )
            validated.append(
                {
                    "run_id": run_id,
                    "retry_path": retry_path,
                    "retry": retry,
                    "retry_bytes": retry_bytes,
                    "failure_evidence": evidence_path,
                    "failure_bytes": failure_bytes,
                    "state_path": state_paths[0],
                    "candidate_sha256": hashlib.sha256(
                        pipeline.compact_json_bytes(candidate)
                    ).hexdigest(),
                }
            )
            candidates.append(candidate)

        _assert_batch_unique(candidates)
        recovery_digest = hashlib.sha256(
            pipeline.compact_json_bytes(
                {
                    "expected_error": expected_error,
                    "reason": reason,
                    "runs": [
                        {
                            "run_id": item["run_id"],
                            "source_retry_sha256": _bytes_sha256(
                                item["retry_bytes"]
                            ),
                            "source_failure_sha256": _bytes_sha256(
                                item["failure_bytes"]
                            ),
                            "candidate_sha256": item["candidate_sha256"],
                        }
                        for item in validated
                    ],
                }
            )
        ).hexdigest()
        if dry_run:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "dry-run",
                "operation": "recover-exhausted-create-retries",
                "mutation_permitted": False,
                "recoverable_runs": normalized_run_ids,
                "expected_error": expected_error,
                "recovery_digest": recovery_digest,
            }
        if expected_recovery_digest != recovery_digest:
            raise PublishBlocked(
                "retry recovery state differs from approved dry-run"
            )

        for item in validated:
            run_id = str(item["run_id"])
            retry_path = Path(item["retry_path"])
            if (
                retry_path.read_bytes() != item["retry_bytes"]
                or Path(item["failure_evidence"]).read_bytes()
                != item["failure_bytes"]
            ):
                raise PublishBlocked(
                    f"retry recovery state changed before mutation: {run_id}"
                )
            _, current_candidate, _ = _load_completed_run(
                Path(item["state_path"])
            )
            if hashlib.sha256(
                pipeline.compact_json_bytes(current_candidate)
            ).hexdigest() != item["candidate_sha256"]:
                raise PublishBlocked(
                    f"retry recovery candidate changed before mutation: {run_id}"
                )

        recovered_runs: list[str] = []
        receipts: list[str] = []
        for item in validated:
            run_id = str(item["run_id"])
            retry_path = Path(item["retry_path"])
            retry = dict(item["retry"])
            source_retry_sha256 = _bytes_sha256(item["retry_bytes"])
            recovered_at = _now()
            recovery_id = hashlib.sha256(
                (
                    f"create:{run_id}:{source_retry_sha256}:"
                    f"{recovered_at}:{reason}"
                ).encode("utf-8")
            ).hexdigest()[:20]
            receipt_path = (
                state_root
                / "evidence"
                / "retry-recovery"
                / f"{recovery_id}-{retry_path.stem}.json"
            )
            receipt = {
                "schema_version": SCHEMA_VERSION,
                "status": "RECOVERY_AUTHORIZED",
                "operation": "recover-exhausted-create-retry",
                "recovery_id": recovery_id,
                "phase": "create",
                "run_id": run_id,
                "reason": reason,
                "expected_error": expected_error,
                "source_retry_sha256": source_retry_sha256,
                "source_failure_evidence": str(item["failure_evidence"]),
                "candidate_sha256": item["candidate_sha256"],
                "authorized_at": recovered_at,
            }
            _atomic_write_json(receipt_path, receipt)
            _atomic_write_json(
                retry_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "phase": "create",
                    "run_id": run_id,
                    "attempts": 0,
                    "max_attempts": MAX_RETRY_ATTEMPTS,
                    "error_type": "OperatorRecovery",
                    "error": reason,
                    "evidence": str(receipt_path),
                    "last_attempt_at": retry.get("last_attempt_at"),
                    "next_eligible_at": datetime.now()
                    .astimezone()
                    .isoformat(timespec="seconds"),
                    "eligibility": "recovered",
                    "candidate_preserved": True,
                    "recovered_from_retry_sha256": source_retry_sha256,
                    "recovery_count": int(retry.get("recovery_count", 0)) + 1,
                    "last_recovery_id": recovery_id,
                    "recovered_at": recovered_at,
                },
            )
            receipt["status"] = "RECOVERED"
            receipt["completed_at"] = _now()
            _atomic_write_json(receipt_path, receipt)
            recovered_runs.append(run_id)
            receipts.append(str(receipt_path))

        return {
            "schema_version": SCHEMA_VERSION,
            "status": "RECOVERED",
            "operation": "recover-exhausted-create-retries",
            "recovered_runs": recovered_runs,
            "receipts": receipts,
        }


def run_git(repo_root: Path, args: list[str], input_text: str | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        input=input_text,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_clean(repo_root: Path, git: GitRunner = run_git) -> bool:
    return git(repo_root, ["status", "--porcelain"], None) == ""


def deployment_preflight(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    expected_repo_root: Path,
    expected_queue_root: Path,
    expected_state_root: Path,
    expected_runtime_sha: str,
    expected_runtime_digest: str,
    push: bool,
    expected_push_mode: str,
    max_runs: int | None = None,
    expected_exact_run_ids: Iterable[str] | None = None,
    manifest_authority: dict[str, Any] | None = None,
    expected_manifest_digest: str | None = None,
    git: GitRunner = run_git,
) -> dict[str, Any]:
    """唯讀核對 publisher actor 與部署契約，不建立或搬動任何狀態。"""
    path_contract = (
        ("actor root", repo_root, expected_repo_root),
        ("queue root", queue_root, expected_queue_root),
        ("state root", state_root, expected_state_root),
    )
    for label, actual, expected in path_contract:
        if actual.resolve() != expected.resolve():
            raise PublishBlocked(f"publisher {label} differs from deployment contract")
    actual_push_mode = "push" if push else "no-push"
    if expected_push_mode not in {"push", "no-push"}:
        raise PublishBlocked("publisher expected push mode is invalid")
    if actual_push_mode != expected_push_mode:
        raise PublishBlocked(
            "publisher push mode differs from deployment contract"
        )
    selected_run_ids = _normalize_exact_run_ids(expected_exact_run_ids)
    if selected_run_ids is not None:
        if len(selected_run_ids) != 1:
            raise PublishBlocked("canary deployment requires one exact run id")
        if max_runs != 1:
            raise PublishBlocked("canary deployment requires --max-runs 1")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_runtime_sha):
        raise PublishBlocked("publisher expected runtime SHA is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_runtime_digest):
        raise PublishBlocked("publisher expected runtime digest is invalid")
    if not _repo_clean(repo_root, git):
        raise PublishBlocked("publisher actor worktree is not clean")
    local_sha = git(repo_root, ["rev-parse", "HEAD"], None)
    if local_sha != expected_runtime_sha:
        raise PublishBlocked(
            "publisher runtime SHA differs from deployment contract"
        )
    actual_runtime_digest = runtime_manifest_digest(repo_root)
    if actual_runtime_digest != expected_runtime_digest:
        raise PublishBlocked(
            "publisher runtime digest differs from deployment contract"
        )
    if (manifest_authority is None) != (expected_manifest_digest is None):
        raise PublishBlocked("publisher manifest authority contract is incomplete")
    origin_main_sha: str | None = None
    if manifest_authority is not None and expected_manifest_digest is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_digest):
            raise PublishBlocked("publisher expected manifest digest is invalid")
        authority_contract = {
            "actor_root": str(repo_root.resolve()),
            "actor_head": expected_runtime_sha,
            "runtime_digest": expected_runtime_digest,
            "manifest_digest": expected_manifest_digest,
        }
        if any(
            manifest_authority.get(field) != value
            for field, value in authority_contract.items()
        ):
            raise PublishBlocked(
                "publisher manifest authority differs from deployment contract"
            )
    else:
        origin_main_sha = git(repo_root, ["rev-parse", "origin/main"], None)
        if local_sha != origin_main_sha:
            merge_base = git(
                repo_root,
                ["merge-base", local_sha, origin_main_sha],
                None,
            )
            if merge_base != local_sha:
                raise PublishBlocked(
                    "origin/main is not a descendant of publisher runtime SHA"
                )
            runtime_drift = git(
                repo_root,
                [
                    "diff",
                    "--name-only",
                    local_sha,
                    origin_main_sha,
                    "--",
                    *TRANSACTION_RUNTIME_PATHS,
                ],
                None,
            ).splitlines()
            if runtime_drift:
                raise PublishBlocked(
                    "publisher runtime differs from origin/main: "
                    + ", ".join(runtime_drift)
                )
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "ready",
        "operation": "deployment-preflight",
        "mode": "read-only",
        "dry_run": True,
        "mutation_permitted": False,
        "actor": "matched",
        "queue": "matched",
        "state": "matched",
        "runtime_sha": local_sha,
        "runtime_manifest_schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "runtime_digest": actual_runtime_digest,
        "push_mode": actual_push_mode,
    }
    if manifest_authority is not None:
        result["authority_mode"] = "manifest"
        result["manifest_digest"] = expected_manifest_digest
    else:
        result["origin_main_sha"] = origin_main_sha
    if selected_run_ids is not None:
        result["exact_run_ids"] = sorted(selected_run_ids)
        result["max_runs"] = max_runs
    return result


def _assert_clean_origin_head(repo_root: Path, git: GitRunner = run_git) -> str:
    git(repo_root, ["fetch", "origin", "main"], None)
    if not _repo_clean(repo_root, git):
        raise PublishBlocked("repo worktree is not clean")
    local = git(repo_root, ["rev-parse", "HEAD"], None)
    remote = git(repo_root, ["rev-parse", "origin/main"], None)
    if local != remote:
        raise PublishBlocked(f"local HEAD differs from origin/main: {local[:12]} != {remote[:12]}")
    return local


def _assert_transaction_runtime_matches(repo_root: Path, transaction_root: Path) -> None:
    """避免 lagging actor 用舊 publisher runtime 操作較新的 origin/main。"""
    actor_manifest = runtime_manifest(repo_root)
    transaction_manifest = runtime_manifest(transaction_root)
    actor_digest = _runtime_manifest_digest(actor_manifest)
    transaction_digest = _runtime_manifest_digest(transaction_manifest)
    if actor_manifest != transaction_manifest or actor_digest != transaction_digest:
        raise PublishBlocked(
            "publisher actor runtime digest differs from origin/main; "
            "deploy actor before publishing"
        )


@contextmanager
def _transaction_lifecycle_lock(
    repo_root: Path,
    git: GitRunner = run_git,
    operation_trace: OperationTraceRecorder | None = None,
    sandbox_authority: TrustedSandboxDirectoryAuthority | None = None,
) -> Iterator[None]:
    """序列化 transaction 建立、回收與執行，讓 crash 後清理可判定安全。"""
    lock_path = _repo_lock_path(
        repo_root,
        git,
        operation_trace,
        sandbox_authority,
    ).with_name(
        "agy-content-publisher.lifecycle.lock"
    )
    if operation_trace is None:
        lock_context = lock_path.open("a+")
    elif sandbox_authority is not None:
        try:
            relative_lock_path = lock_path.relative_to(sandbox_authority.root)
        except ValueError as error:
            raise FilesystemAuthorityError(
                "sandbox relative target escaped sandbox"
            ) from error
        lock_context = operation_trace.record_path_operation(
            "filesystem-lock-open",
            lock_path,
            lambda: os.fdopen(
                sandbox_authority.open_file(
                    relative_lock_path,
                    flags=os.O_RDWR | os.O_CREAT,
                    mode=0o600,
                ),
                "a+",
            ),
        )
    else:
        lock_context = operation_trace.record_path_operation(
            "filesystem-lock-open",
            lock_path,
            lambda: lock_path.open("a+"),
        )
    with lock_context as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PublishBlocked("publisher transaction is busy") from error
        yield


def _cleanup_stale_transaction_worktrees(
    repo_root: Path,
    state_root: Path,
    git: GitRunner = run_git,
    *,
    operation_trace: OperationTraceRecorder | None = None,
    sandbox_authority: TrustedSandboxDirectoryAuthority | None = None,
) -> list[Path]:
    """只回收專用 state root 直屬的 transaction 暫存 worktree。"""
    if sandbox_authority is not None:
        return _cleanup_stale_transaction_worktrees_with_authority(
            repo_root,
            state_root,
            git,
            operation_trace=operation_trace,
            sandbox_authority=sandbox_authority,
        )
    cleaned: list[Path] = []
    for transaction_parent in sorted(state_root.iterdir()):
        if (
            not transaction_parent.is_dir()
            or transaction_parent.is_symlink()
            or re.fullmatch(r"transaction-[A-Za-z0-9_-]+", transaction_parent.name)
            is None
        ):
            continue
        transaction_root = transaction_parent / "repo"
        if transaction_root.exists():
            try:
                git(
                    repo_root,
                    ["worktree", "remove", "--force", str(transaction_root)],
                    None,
                )
            except Exception:
                shutil.rmtree(transaction_root, ignore_errors=True)
        shutil.rmtree(transaction_parent, ignore_errors=True)
        if transaction_parent.exists():
            raise PublishBlocked(
                f"stale transaction cleanup failed: {transaction_parent}"
            )
        cleaned.append(transaction_parent)
    if cleaned:
        git(repo_root, ["worktree", "prune"], None)
    return cleaned


def _cleanup_stale_transaction_worktrees_with_authority(
    repo_root: Path,
    state_root: Path,
    git: GitRunner,
    *,
    operation_trace: OperationTraceRecorder | None,
    sandbox_authority: TrustedSandboxDirectoryAuthority,
) -> list[Path]:
    """透過 held sandbox fd 清理 stale transaction，避免 post-lock parent swap。"""
    try:
        state_relative = state_root.relative_to(sandbox_authority.root)
    except ValueError as error:
        raise FilesystemAuthorityError(
            "sandbox relative target escaped sandbox"
        ) from error
    cleaned: list[Path] = []
    for transaction_name, entry_kind in sandbox_authority.list_directory_entries(
        state_relative
    ):
        if re.fullmatch(r"transaction-[A-Za-z0-9_-]+", transaction_name) is None:
            continue
        if entry_kind != "directory":
            raise FilesystemAuthorityError(
                "stale transaction cleanup target is not a directory"
            )
        transaction_relative = state_relative / transaction_name
        transaction_parent = state_root / transaction_name
        transaction_root = transaction_parent / "repo"
        transaction_root_relative = transaction_relative / "repo"
        if sandbox_authority.exists(transaction_root_relative):
            try:
                git(
                    repo_root,
                    ["worktree", "remove", "--force", str(transaction_root)],
                    None,
                )
            except Exception:
                if operation_trace is None:
                    sandbox_authority.remove_tree(transaction_root_relative)
                else:
                    operation_trace.record_path_operation(
                        "filesystem-stale-transaction-repo-remove",
                        transaction_root,
                        lambda: sandbox_authority.remove_tree(
                            transaction_root_relative
                        ),
                    )
        if operation_trace is None:
            sandbox_authority.remove_tree(transaction_relative)
        else:
            operation_trace.record_path_operation(
                "filesystem-stale-transaction-remove",
                transaction_parent,
                lambda: sandbox_authority.remove_tree(transaction_relative),
            )
        if sandbox_authority.exists(transaction_relative):
            raise PublishBlocked(
                f"stale transaction cleanup failed: {transaction_parent}"
            )
        cleaned.append(transaction_parent)
    if cleaned:
        git(repo_root, ["worktree", "prune"], None)
    return cleaned


@contextmanager
def _isolated_transaction_worktree(
    repo_root: Path,
    state_root: Path,
    git: GitRunner = run_git,
    *,
    operation_trace: OperationTraceRecorder | None = None,
    sandbox_authority: TrustedSandboxDirectoryAuthority | None = None,
    transaction_name: str | None = None,
) -> Iterator[Path]:
    """從最新 origin/main 建立單輪隔離 worktree，正式 actor 全程唯讀。"""
    if sandbox_authority is None:
        state_root.mkdir(parents=True, exist_ok=True)
    else:
        sandbox_authority.makedirs(state_root.relative_to(sandbox_authority.root))
    with _transaction_lifecycle_lock(
        repo_root,
        git,
        operation_trace,
        sandbox_authority,
    ):
        _cleanup_stale_transaction_worktrees(
            repo_root,
            state_root,
            git,
            operation_trace=operation_trace,
            sandbox_authority=sandbox_authority,
        )
        git(repo_root, ["fetch", "origin", "main"], None)
        if not _repo_clean(repo_root, git):
            raise PublishBlocked("publisher actor worktree is not clean")
        remote_sha = git(repo_root, ["rev-parse", "origin/main"], None)
        if transaction_name is None:
            transaction_parent = Path(
                tempfile.mkdtemp(prefix="transaction-", dir=state_root)
            )
        else:
            if not re.fullmatch(r"transaction-[0-9a-f]{24}", transaction_name):
                raise PublishBlocked("transaction operation identity is invalid")
            transaction_parent = state_root / transaction_name
            if transaction_parent.exists():
                if sandbox_authority is None:
                    shutil.rmtree(transaction_parent, ignore_errors=True)
                else:
                    sandbox_authority.remove_tree(
                        transaction_parent.relative_to(sandbox_authority.root)
                    )
            if operation_trace is None:
                transaction_parent.mkdir(mode=0o700)
            elif sandbox_authority is not None:
                operation_trace.record_path_operation(
                    "filesystem-transaction-create",
                    transaction_parent,
                    lambda: sandbox_authority.makedirs(
                        transaction_parent.relative_to(sandbox_authority.root)
                    ),
                )
            else:
                operation_trace.record_path_operation(
                    "filesystem-transaction-create",
                    transaction_parent,
                    lambda: transaction_parent.mkdir(mode=0o700),
                )
        transaction_root = transaction_parent / "repo"
        added = False
        try:
            git(
                repo_root,
                ["worktree", "add", "--detach", str(transaction_root), remote_sha],
                None,
            )
            added = True
            _assert_transaction_runtime_matches(repo_root, transaction_root)
            actor_venv = repo_root / ".venv"
            transaction_venv = transaction_root / ".venv"
            if (
                operation_trace is None
                and actor_venv.is_dir()
                and not transaction_venv.exists()
            ):
                transaction_venv.symlink_to(actor_venv, target_is_directory=True)
            actor_node_modules = repo_root / "node_modules"
            transaction_node_modules = transaction_root / "node_modules"
            if (
                operation_trace is None
                and actor_node_modules.is_dir()
                and not transaction_node_modules.exists()
            ):
                transaction_node_modules.mkdir()
                for dependency in actor_node_modules.iterdir():
                    (transaction_node_modules / dependency.name).symlink_to(
                        dependency,
                        target_is_directory=dependency.is_dir(),
                    )
            authority_token = _TRANSACTION_RUNTIME_AUTHORITY.set(
                (repo_root.resolve(strict=True), transaction_root.resolve(strict=True))
            )
            try:
                yield transaction_root
            finally:
                _TRANSACTION_RUNTIME_AUTHORITY.reset(authority_token)
        finally:
            if added:
                try:
                    git(
                        repo_root,
                        ["worktree", "remove", "--force", str(transaction_root)],
                        None,
                    )
                except Exception:
                    shutil.rmtree(transaction_root, ignore_errors=True)
                    git(repo_root, ["worktree", "prune"], None)
            if operation_trace is None:
                shutil.rmtree(transaction_parent, ignore_errors=True)
            elif sandbox_authority is not None:
                operation_trace.record_path_operation(
                    "filesystem-transaction-remove",
                    transaction_parent,
                    lambda: sandbox_authority.remove_tree(
                        transaction_parent.relative_to(sandbox_authority.root)
                    ),
                )
            else:
                operation_trace.record_path_operation(
                    "filesystem-transaction-remove",
                    transaction_parent,
                    lambda: shutil.rmtree(transaction_parent, ignore_errors=True),
                )


def _git_paths(repo_root: Path, git: GitRunner, args: list[str]) -> list[str]:
    return [path for path in git(repo_root, args, None).split("\0") if path]


def _publisher_owned_path(relative: str) -> bool:
    return relative.startswith("app/web/") or relative in {
        "CHANGELOG.md",
        "package.json",
        "pyproject.toml",
        "tests/test_web.py",
    }


def _recover_failed_publish(
    repo_root: Path,
    state_root: Path,
    *,
    base_sha: str,
    phase: str,
    run_ids: list[str],
    error: Exception,
    git: GitRunner,
    journal: MutationJournal | None = None,
) -> Path:
    """保存失敗證據，只還原從乾淨 base 產生的本輪 repo 變更。"""
    failed_head = git(repo_root, ["rev-parse", "HEAD"], None)
    nonce = datetime.now().astimezone().isoformat(timespec="microseconds")
    suffix = hashlib.sha256(f"{phase}:{base_sha}:{nonce}".encode("utf-8")).hexdigest()[:10]
    evidence_dir = state_root / "evidence" / f"failed-{phase}-{suffix}"
    evidence_dir.mkdir(parents=True, exist_ok=False)
    status_before = git(repo_root, ["status", "--porcelain"], None)
    failure_attempt = evidence_dir / "failure-attempt.json"
    _atomic_write_json(
        failure_attempt,
        {
            "schema_version": SCHEMA_VERSION,
            "status": "RECOVERY_PENDING",
            "phase": phase,
            "run_ids": run_ids,
            "base_sha": base_sha,
            "failed_head": failed_head,
            "error_type": type(error).__name__,
            "error": str(error),
            "return_code": error.returncode if isinstance(error, subprocess.CalledProcessError) else None,
            "status_before_recovery": status_before.splitlines(),
            "mutation_started": bool(journal and journal.mutation_started),
            "write_set": journal.image_metadata() if journal else {},
            "recorded_at": _now(),
        },
    )
    recovery_result = evidence_dir / "recovery-result.json"
    cleanup_steps: list[dict[str, Any]] = []

    def record_step(step: str, status: str, **details: Any) -> None:
        cleanup_steps.append({"step": step, "status": status, **details, "recorded_at": _now()})
        _atomic_write_json(
            recovery_result,
            {
                "schema_version": SCHEMA_VERSION,
                "phase": phase,
                "run_ids": run_ids,
                "base_sha": base_sha,
                "failed_head": failed_head,
                "steps": cleanup_steps,
            },
        )

    untracked: list[str] = []
    try:
        (evidence_dir / "working-tree.patch").write_text(
            git(repo_root, ["diff", "--binary", base_sha], None),
            encoding="utf-8",
        )
        untracked = _git_paths(repo_root, git, ["ls-files", "--others", "--exclude-standard", "-z"])
        for relative in untracked:
            source = repo_root / relative
            if not source.is_file():
                continue
            target = evidence_dir / "untracked" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    except Exception as cleanup_error:
        record_step("archive-copy", "failed", error_type=type(cleanup_error).__name__, error=str(cleanup_error))
        raise
    record_step("archive-copy", "complete", untracked=untracked)

    created_tags: list[str] = []
    try:
        if failed_head != base_sha:
            created_tags = [
                tag
                for tag in git(repo_root, ["tag", "--points-at", failed_head], None).splitlines()
                if re.fullmatch(r"v\d+\.\d+\.\d+", tag)
            ]
            git(
                repo_root,
                ["update-ref", "-m", f"rollback failed {phase} publish", "HEAD", base_sha, failed_head],
                None,
            )
    except Exception as cleanup_error:
        record_step("update-ref", "failed", error_type=type(cleanup_error).__name__, error=str(cleanup_error))
        raise
    record_step("update-ref", "complete", updated=failed_head != base_sha)

    changed_tracked = sorted(
        set(
            _git_paths(repo_root, git, ["diff", "--name-only", "-z", base_sha])
            + _git_paths(repo_root, git, ["diff", "--cached", "--name-only", "-z", base_sha])
        )
    )
    tracked = [relative for relative in changed_tracked if _publisher_owned_path(relative)]
    conflicts: list[str] = []
    restored: list[str] = []
    try:
        if journal and journal.mutation_started:
            for relative in sorted(
                set(journal.pre_images) | set(journal.expected_post_images) | journal.unattributed_paths
            ):
                current = journal._read(relative)
                if relative in journal.unattributed_paths:
                    conflicts.append(relative)
                    continue
                expected = journal.expected_post_images.get(relative)
                if current != expected:
                    conflicts.append(relative)
                    continue
                path = repo_root / relative
                pre_image = journal.pre_images.get(relative)
                if pre_image is None:
                    if path.is_file() or path.is_symlink():
                        path.unlink()
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(pre_image)
                restored.append(relative)
            if restored:
                git(repo_root, ["add", "-A"], None)
                git(repo_root, ["reset", "-q", base_sha], None)
        elif tracked:
            git(repo_root, ["restore", f"--source={base_sha}", "--staged", "--worktree", "--", *tracked], None)
            restored.extend(tracked)
    except Exception as cleanup_error:
        record_step("restore", "failed", error_type=type(cleanup_error).__name__, error=str(cleanup_error))
        raise
    record_step("restore", "conflict" if conflicts else "complete", restored=restored, conflicts=conflicts)

    removed_untracked: list[str] = []
    try:
        if not journal:
            for relative in _git_paths(repo_root, git, ["ls-files", "--others", "--exclude-standard", "-z"]):
                path = repo_root / relative
                if _publisher_owned_path(relative) and (path.is_file() or path.is_symlink()):
                    path.unlink()
                    removed_untracked.append(relative)
    except Exception as cleanup_error:
        record_step("unlink", "failed", error_type=type(cleanup_error).__name__, error=str(cleanup_error))
        raise
    record_step("unlink", "complete", removed=removed_untracked)
    try:
        for tag in created_tags:
            git(repo_root, ["tag", "-d", tag], None)
    except Exception as cleanup_error:
        record_step("tag-delete", "failed", error_type=type(cleanup_error).__name__, error=str(cleanup_error))
        raise
    record_step("tag-delete", "complete", removed=created_tags)

    status_after = git(repo_root, ["status", "--porcelain"], None)
    evidence_path = evidence_dir / "failure.json"
    try:
        _write_json(
            evidence_path,
            {
            "schema_version": SCHEMA_VERSION,
            "status": "FAILED_RECOVERED" if not status_after else "FAILED_RECOVERY_INCOMPLETE",
            "phase": phase,
            "run_ids": run_ids,
            "base_sha": base_sha,
            "failed_head": failed_head,
            "error_type": type(error).__name__,
            "return_code": error.returncode if isinstance(error, subprocess.CalledProcessError) else None,
            "status_before_recovery": status_before.splitlines(),
            "status_after_recovery": status_after.splitlines(),
            "untracked_files_preserved": untracked,
            "publisher_owned_paths_restored": restored,
            "concurrent_write_conflicts": conflicts,
            "unknown_tracked_paths_preserved": [
                relative for relative in changed_tracked if not _publisher_owned_path(relative)
            ],
            "removed_local_tags": created_tags,
            "repo_recovered": not status_after and not conflicts,
            "retry_status": "candidate_preserved",
            "recorded_at": _now(),
            },
        )
    except Exception as cleanup_error:
        record_step(
            "final-evidence-write",
            "failed",
            error_type=type(cleanup_error).__name__,
            error=str(cleanup_error),
            path=str(evidence_path),
        )
        raise
    record_step("final-evidence-write", "complete", path=str(evidence_path))
    if status_after or conflicts:
        raise PublishBlocked(f"{phase} publish recovery did not restore a clean repo; evidence: {evidence_path}") from error
    return evidence_path


def _recoverable_publish(phase: str, count_key: str) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
    def decorate(function: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
        @functools.wraps(function)
        def wrapped(
            repo_root: Path,
            queue_root: Path,
            state_root: Path,
            *args: Any,
            **kwargs: Any,
        ) -> dict[str, Any]:
            _validate_formal_runtime(repo_root, queue_root, state_root)
            git = kwargs.get("git", run_git)
            state_root.mkdir(parents=True, exist_ok=True)
            with _repo_lock_path(repo_root, git).open("a+") as lock:
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return {"schema_version": SCHEMA_VERSION, "status": "busy", count_key: 0}
                _assert_no_unresolved_push(state_root)
                base_sha = _assert_clean_origin_head(repo_root, git)
                journal = MutationJournal(repo_root, git)
                kwargs["_transaction_base_sha"] = base_sha
                kwargs["_mutation_journal"] = journal
                try:
                    _validate_formal_runtime(repo_root, queue_root, state_root)
                    return function(repo_root, queue_root, state_root, *args, **kwargs)
                except PushOutcomeUnknown:
                    raise
                except PolicyRejected as error:
                    if not journal.mutation_started:
                        raise
                    recovery_path = _recover_failed_publish(
                        repo_root,
                        state_root,
                        base_sha=base_sha,
                        phase=phase,
                        run_ids=journal.selected_run_ids,
                        error=error,
                        git=git,
                        journal=journal,
                    )
                    rejection_paths = _record_runtime_policy_rejections(
                        queue_root,
                        state_root,
                        phase,
                        journal.selected_run_ids,
                        error,
                    )
                    return {
                        "schema_version": SCHEMA_VERSION,
                        "status": "policy_rejected",
                        count_key: 0,
                        "base_sha": base_sha,
                        "policy_version": pipeline.publication_policy_version(),
                        "validator_result": "FAIL",
                        "failure_codes": sorted(
                            {
                                str(finding.get("code") or "unknown")
                                for finding in error.findings
                            }
                        ),
                        "retry_eligible": False,
                        "evidence": str(recovery_path),
                        "policy_rejection_evidence": [
                            str(path) for path in rejection_paths
                        ],
                    }
                except Exception as error:
                    if not journal.mutation_started:
                        raise
                    evidence_path = _recover_failed_publish(
                        repo_root,
                        state_root,
                        base_sha=base_sha,
                        phase=phase,
                        run_ids=journal.selected_run_ids,
                        error=error,
                        git=git,
                        journal=journal,
                    )
                    _record_retry_failure(
                        state_root,
                        phase,
                        journal.selected_run_ids,
                        error,
                        evidence_path,
                    )
                    return {
                        "schema_version": SCHEMA_VERSION,
                        "status": "failed_recovered",
                        count_key: 0,
                        "base_sha": base_sha,
                        "error_type": type(error).__name__,
                        "evidence": str(evidence_path),
                        "retry_status": "candidate_preserved_deferred",
                    }

        return wrapped

    return decorate


def _run_files(queue_root: Path) -> list[Path]:
    runs_dir = queue_root / "runs"
    if not runs_dir.exists():
        return []
    return sorted(runs_dir.glob("*.json"), key=lambda path: path.name)


def _fresh_first_run_files(queue_root: Path, state_root: Path, phase: str) -> list[Path]:
    """未失敗候選優先；已有 retry 記錄者排到 fresh queue 之後。"""

    def priority(path: Path) -> tuple[bool, str]:
        try:
            run_id = str(_read_json(path).get("run_id") or "")
        except (OSError, json.JSONDecodeError):
            run_id = ""
        return (bool(run_id and _retry_path(state_root, phase, run_id).is_file()), path.name)

    return sorted(_run_files(queue_root), key=priority)


def _selected_run_files(
    queue_root: Path,
    state_root: Path,
    phase: str,
    exact_run_ids: frozenset[str] | None,
) -> list[Path]:
    paths = _fresh_first_run_files(queue_root, state_root, phase)
    if exact_run_ids is None:
        return paths
    selected: list[Path] = []
    for path in paths:
        try:
            run_id = str(_read_json(path).get("run_id") or "")
        except (OSError, json.JSONDecodeError):
            continue
        if run_id in exact_run_ids:
            selected.append(path)
    return selected


def _ledger_path(state_root: Path) -> Path:
    return state_root / "ledger.json"


def _load_ledger(state_root: Path) -> dict[str, Any]:
    path = _ledger_path(state_root)
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "published_runs": [],
            "quarantined_runs": [],
            "rewrite_released_runs": [],
            "superseded_runs": [],
            "translation_published_runs": [],
            "translation_deferred_runs": [],
        }
    ledger = _read_json(path)
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise PublishBlocked("publisher ledger schema is invalid")
    ledger.setdefault("published_runs", [])
    ledger.setdefault("quarantined_runs", [])
    ledger.setdefault("rewrite_released_runs", [])
    ledger.setdefault("superseded_runs", [])
    ledger.setdefault("translation_published_runs", [])
    ledger.setdefault("translation_deferred_runs", [])
    return ledger


def _ledger_article_ids(entry: object, label: str) -> list[str]:
    if not isinstance(entry, dict):
        raise PublishBlocked(f"{label} ledger identity mismatch")
    article_ids = entry.get("article_ids")
    if (
        not isinstance(article_ids, list)
        or any(
            type(article_id) is not str
            or not article_id
            or article_id.strip() != article_id
            for article_id in article_ids
        )
        or article_ids != sorted(set(article_ids))
    ):
        raise PublishBlocked(f"{label} ledger identity mismatch")
    return list(article_ids)


def _ledger_run_lifecycle(
    ledger: dict[str, Any],
    *,
    run_id: str,
    article_ids: list[str],
) -> str | None:
    matched: list[tuple[str, str]] = []
    for key, lifecycle in (
        ("published_runs", "published"),
        ("superseded_runs", "superseded"),
    ):
        entries = ledger.get(key)
        if not isinstance(entries, list):
            raise PublishBlocked("publisher ledger schema is invalid")
        seen = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise PublishBlocked("publisher ledger schema is invalid")
            if entry.get("run_id") != run_id:
                continue
            seen += 1
            if _ledger_article_ids(entry, lifecycle) != article_ids:
                raise PublishBlocked(f"{lifecycle} ledger identity mismatch")
            matched.append((key, lifecycle))
        if seen > 1:
            raise PublishBlocked(f"{lifecycle} ledger identity mismatch")
    if len(matched) > 1:
        raise PublishBlocked("publisher ledger lifecycle conflict")
    return matched[0][1] if matched else None


def _record_translation_deferred(state_root: Path, run_id: str, reason: str) -> None:
    ledger = _load_ledger(state_root)
    existing = {(str(item.get("run_id")), str(item.get("reason"))) for item in ledger["translation_deferred_runs"]}
    if run_id and (run_id, reason) not in existing:
        ledger["translation_deferred_runs"].append({"run_id": run_id, "reason": reason, "recorded_at": _now()})
        _write_json(_ledger_path(state_root), ledger)


def _record_quarantine(state_root: Path, state: dict[str, Any], reason: str) -> None:
    ledger = _load_ledger(state_root)
    existing = {(str(item.get("run_id")), str(item.get("reason"))) for item in ledger["quarantined_runs"]}
    run_id = str(state.get("run_id") or "")
    if run_id and (run_id, reason) not in existing:
        ledger["quarantined_runs"].append({"run_id": run_id, "reason": reason, "recorded_at": _now()})
        _write_json(_ledger_path(state_root), ledger)


def _rewrite_quarantined_run_ids(ledger: dict[str, Any]) -> set[str]:
    return {
        str(item.get("run_id"))
        for item in ledger["quarantined_runs"]
        if str(item.get("reason")) != "publisher only supports create mode"
    }


def _load_completed_run(state_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = _read_json(state_path)
    if state.get("schema_version") != SCHEMA_VERSION or state.get("status") != "complete":
        raise PublishBlocked("run state is not complete")
    run_dir = Path(str(state.get("run_dir") or ""))
    result = state.get("result") if isinstance(state.get("result"), dict) else {}
    candidate_path = Path(str(result.get("candidate") or run_dir / "candidate.json"))
    review_path = run_dir / "review.json"
    if not candidate_path.is_file() or not review_path.is_file():
        raise PublishBlocked("candidate or review json is missing")
    candidate = _read_json(candidate_path)
    review = _read_json(review_path)
    if candidate.get("run_id") != state.get("run_id") or review.get("run_id") != state.get("run_id"):
        raise PublishBlocked("run id drift between state, candidate, and review")
    try:
        if candidate.get("mode") == "translate_existing":
            brief = _read_json(run_dir / "brief.json")
            multilingual.validate_translation_candidate(brief, candidate)
        else:
            pipeline.validate_candidate(candidate)
        pipeline.validate_review(review, candidate["articles"])
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise PublishBlocked(f"run payload validation failed: {type(error).__name__}") from error
    return state, candidate, review


def _record_invalid_candidate_policy_rejection(
    state_root: Path,
    phase: str,
    state_path: Path,
) -> Path | None:
    """只把已存在但不合 policy/schema 的 candidate 收斂為 terminal rejection。"""
    try:
        state = _read_json(state_path)
        if state.get("status") != "complete":
            return None
        run_dir = Path(str(state.get("run_dir") or ""))
        result = state.get("result") if isinstance(state.get("result"), dict) else {}
        candidate_path = Path(str(result.get("candidate") or run_dir / "candidate.json"))
        if not candidate_path.is_file():
            return None
        candidate = _read_json(candidate_path)
        pipeline.validate_candidate(candidate)
    except pipeline.CandidateValidationError as error:
        match = re.search(r": ([a-z0-9_]+)$", str(error))
        code = match.group(1) if match else "invalid_candidate_contract"
        finding = pipeline._policy_finding(
            str(candidate.get("run_id") or state.get("run_id") or ""),
            code,
            str(error),
        )
        return _record_policy_rejection(state_root, phase, state, candidate, [finding])
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return None


def _review_is_clean_approve(review: dict[str, Any]) -> bool:
    for item in review["articles"]:
        if item.get("verdict") != "APPROVE" or item.get("hard_failure") is True:
            return False
        if item.get("findings"):
            return False
    return True


def _article_path(article: dict[str, Any]) -> str:
    category = str(article["serial"]).rsplit("-", 1)[0]
    return f"/articles/{category}/{article['urlSlug']}"


def _assert_batch_unique(candidates: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    paths: set[str] = set()
    paragraph_owners: dict[str, str] = {}
    for candidate in candidates:
        for article in candidate["articles"]:
            article_id = str(article["id"])
            path = _article_path(article)
            if article_id in ids:
                raise PublishBlocked(f"duplicate article id in publish batch: {article_id}")
            if path in paths:
                raise PublishBlocked(f"duplicate article path in publish batch: {path}")
            ids.add(article_id)
            paths.add(path)
            for section in article["bodySections"]:
                for paragraph in section["paragraphs"]:
                    normalized = re.sub(r"\s+", "", str(paragraph))
                    if len(normalized) < 40:
                        continue
                    owner = paragraph_owners.get(normalized)
                    if owner and owner != article_id:
                        raise PublishBlocked(f"duplicate paragraph across batch: {owner} and {article_id}")
                    paragraph_owners[normalized] = article_id


def collect_ready_runs(
    queue_root: Path,
    state_root: Path,
    *,
    limit: int = DEFAULT_MAX_RUNS,
    repo_root: Path | None = None,
    exact_run_ids: Iterable[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    ledger = _load_ledger(state_root)
    quarantined = {str(item.get("run_id")) for item in ledger["quarantined_runs"]}
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    reference_articles = (
        pipeline.load_publication_reference_corpus(repo_root)
        if repo_root is not None
        else None
    )
    for state_path in _selected_run_files(
        queue_root, state_root, "create", selected_run_ids
    ):
        try:
            state, candidate, review = _load_completed_run(state_path)
        except PublishBlocked:
            _record_invalid_candidate_policy_rejection(state_root, "create", state_path)
            continue
        run_id = str(state["run_id"])
        if candidate.get("mode") == "translate_existing":
            continue
        if candidate.get("mode") != "create":
            _record_quarantine(state_root, state, "publisher only supports create mode")
            continue
        article_ids = sorted(str(article["id"]) for article in candidate["articles"])
        lifecycle = _ledger_run_lifecycle(ledger, run_id=run_id, article_ids=article_ids)
        if lifecycle in {"published", "superseded"} or run_id in quarantined:
            continue
        if not _retry_eligible(state_root, "create", run_id):
            continue
        if not _review_is_clean_approve(review):
            _record_quarantine(state_root, state, "reviewer did not cleanly approve every article")
            continue
        findings = (
            pipeline.quality_findings(
                candidate["articles"],
                reference_articles=reference_articles,
            )
            if reference_articles
            else pipeline.quality_findings(candidate["articles"])
        )
        if findings:
            _record_policy_rejection(state_root, "create", state, candidate, findings)
            continue
        ready.append((state, candidate, review))
        if len(ready) >= limit:
            break
    _assert_batch_unique([candidate for _, candidate, _ in ready])
    return ready


def collect_ready_translation_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    limit: int = DEFAULT_MAX_RUNS,
    exact_run_ids: Iterable[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """只收乾淨通過的單語 run；其餘保留並移入待修清單。"""
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    ledger = _load_ledger(state_root)
    published = {str(item.get("run_id")) for item in ledger["translation_published_runs"]}
    deferred = {str(item.get("run_id")) for item in ledger["translation_deferred_runs"]}
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for state_path in _selected_run_files(
        queue_root, state_root, "translation", selected_run_ids
    ):
        try:
            state = _read_json(state_path)
            run_id = str(state.get("run_id") or "")
            run_dir = Path(str(state.get("run_dir") or ""))
            brief_path = run_dir / "brief.json"
            if not run_id or not brief_path.is_file():
                continue
            brief = _read_json(brief_path)
        except (OSError, json.JSONDecodeError):
            continue
        if brief.get("mode") != "translate_existing" or run_id in published or run_id in deferred:
            continue
        if not _retry_eligible(state_root, "translation", run_id):
            continue
        if state.get("status") == "failed":
            _record_translation_deferred(state_root, run_id, f"run failed: {state.get('error_type') or 'unknown'}")
            continue
        if state.get("status") != "complete":
            continue
        try:
            result = state.get("result") if isinstance(state.get("result"), dict) else {}
            candidate_path = Path(str(result.get("candidate") or run_dir / "candidate.json"))
            candidate = _read_json(candidate_path)
            review = _read_json(run_dir / "review.json")
            if candidate.get("run_id") != run_id or review.get("run_id") != run_id:
                raise ValueError("translation run id drift")
            multilingual.validate_translation_candidate(brief, candidate)
            pipeline.validate_review(review, candidate["articles"])
        except (OSError, json.JSONDecodeError, ValueError) as error:
            _record_translation_deferred(state_root, run_id, f"invalid translation result: {type(error).__name__}")
            continue
        if not _review_is_clean_approve(review):
            _record_translation_deferred(state_root, run_id, "translation reviewer did not cleanly approve")
            continue
        findings = multilingual.translation_findings(brief, candidate["articles"])
        if findings:
            _record_translation_deferred(state_root, run_id, f"translation deterministic findings: {len(findings)}")
            continue
        source_current = True
        try:
            for target in brief["articles"]:
                current = multilingual.load_source_article(repo_root, str(target["source_article_id"]))
                if multilingual.source_sha256(current) != target["source_sha256"]:
                    source_current = False
                    break
        except (OSError, subprocess.CalledProcessError, ValueError):
            source_current = False
        if not source_current:
            _record_translation_deferred(state_root, run_id, "translation source drift")
            continue
        ready.append((state, brief, candidate, review))
        if len(ready) >= limit:
            break
    return ready


def _assert_exact_fresh_ja_translation_run(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    run_id: str | None,
) -> str:
    """驗證單一全新 JA／i18n-new run，避免 exact selector 退化成廣域掃描。"""
    if type(run_id) is not str or EXACT_RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise PublishBlocked("exact fresh JA selector must name exactly one valid run id")
    if "replacement" in run_id.lower():
        raise PublishBlocked("exact fresh JA selector rejects replacement lineage")
    state_paths = _selected_run_files(
        queue_root,
        state_root,
        "translation",
        frozenset({run_id}),
    )
    if not state_paths:
        raise PublishBlocked("exact fresh JA run id was not found")
    if len(state_paths) != 1:
        raise PublishBlocked("exact fresh JA selector matched multiple runs")
    try:
        state = _read_json(state_paths[0])
        if state.get("run_id") != run_id:
            raise PublishBlocked("exact fresh JA run state identity differs")
        if state.get("status") != "complete":
            raise PublishBlocked("exact fresh JA run is not complete")
        if any(state.get(key) for key in ("replacement_of", "replaces", "replaced_by")):
            raise PublishBlocked("exact fresh JA selector rejects replacement lineage")
        if _retry_path(state_root, "translation", run_id).exists():
            raise PublishBlocked("exact fresh JA selector rejects old retry run")
        run_dir = Path(str(state.get("run_dir") or ""))
        brief = _read_json(run_dir / "brief.json")
    except (OSError, json.JSONDecodeError) as error:
        raise PublishBlocked("exact fresh JA run metadata is unreadable") from error
    if brief.get("run_id") != run_id or brief.get("mode") != "translate_existing":
        raise PublishBlocked("exact fresh JA run is not a translation run")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not articles:
        raise PublishBlocked("exact fresh JA translation brief has no articles")
    if any(not isinstance(article, dict) or article.get("locale") != "ja" for article in articles):
        raise PublishBlocked("exact fresh JA selector must be JA only")
    legacy_ids = legacy_article_ids(repo_root)
    if any(str(article.get("source_article_id") or "") in legacy_ids for article in articles):
        raise PublishBlocked("exact fresh JA selector requires i18n-new, not i18n-rewrite")
    ledger = _load_ledger(state_root)
    recorded = {
        str(item.get("run_id") or "")
        for key in ("translation_published_runs", "translation_deferred_runs")
        for item in ledger[key]
    }
    if run_id in recorded:
        raise PublishBlocked("exact fresh JA selector rejects old terminal run")
    return run_id


def publish_exact_fresh_ja_translation_run(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    run_id: str | None,
    *,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
) -> dict[str, Any]:
    """僅將指定的新 JA／i18n-new run 交給既有 publisher transaction。"""
    selected_run_id = _assert_exact_fresh_ja_translation_run(
        repo_root,
        queue_root,
        state_root,
        run_id,
    )
    return publish_ready_translation_runs(
        repo_root,
        queue_root,
        state_root,
        max_runs=1,
        dry_run=dry_run,
        push=push,
        run_tests=run_tests,
        release_gate=release_gate,
        exact_run_ids=[selected_run_id],
    )


def prepare_exact_fresh_ja_translation_run(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    source_run_id: str | None,
    article_id: str | None,
) -> dict[str, str]:
    """以既有 queue contract 建立一個 fresh JA run，並回傳唯一可重算的 run ID。"""
    if type(source_run_id) is not str or EXACT_RUN_ID_PATTERN.fullmatch(source_run_id) is None:
        raise PublishBlocked("exact fresh JA source run id must be valid")
    if type(article_id) is not str or not article_id.strip():
        raise PublishBlocked("exact fresh JA article id must be non-empty")
    if "replacement" in source_run_id.lower():
        raise PublishBlocked("exact fresh JA selector rejects replacement lineage")
    if article_id in legacy_article_ids(repo_root):
        raise PublishBlocked("exact fresh JA selector requires i18n-new, not i18n-rewrite")
    run_id = multilingual.translation_run_id(source_run_id, article_id, "ja")
    if _selected_run_files(queue_root, state_root, "translation", frozenset({run_id})):
        raise PublishBlocked("exact fresh JA selector rejects existing run")
    records = multilingual.enqueue_article_translations(
        repo_root,
        queue_root,
        source_run_id=source_run_id,
        article_id=article_id,
        locales=["ja"],
    )
    if len(records) != 1 or records[0].get("locale") != "ja":
        raise PublishBlocked("exact fresh JA queue registration was not singular")
    record = records[0]
    if record.get("run_id") != run_id:
        raise PublishBlocked("exact fresh JA queue registration run id differs")
    return record


def _load_rewrite_brief(run_dir: Path, run_id: str) -> dict[str, Any]:
    brief_path = run_dir / "brief.json"
    if not brief_path.is_file():
        raise PublishBlocked(f"rewrite brief is missing for {run_id}")
    brief = _read_json(brief_path)
    if brief.get("run_id") != run_id:
        raise PublishBlocked(f"rewrite brief run id drift for {run_id}")
    pipeline.validate_rewrite_brief(brief)
    return brief


def _rewrite_findings_for_run(
    candidate: dict[str, Any],
    brief: dict[str, Any],
    *,
    reference_articles: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    if not reference_articles:
        quality, uniqueness = pipeline.rewrite_aggregate_findings(
            brief,
            candidate["articles"],
        )
    else:
        quality, uniqueness = pipeline.rewrite_aggregate_findings(
            brief,
            candidate["articles"],
            reference_articles=reference_articles,
        )
    return [*quality, *uniqueness]


def collect_ready_rewrite_runs(
    queue_root: Path,
    state_root: Path,
    *,
    limit: int = DEFAULT_MAX_RUNS,
    allowed_article_ids: set[str] | None = None,
    repo_root: Path | None = None,
    exact_run_ids: Iterable[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    ledger = _load_ledger(state_root)
    released = {str(item.get("run_id")) for item in ledger["rewrite_released_runs"]}
    quarantined = _rewrite_quarantined_run_ids(ledger)
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    seen_article_ids: set[str] = set()
    seen_body_hashes: dict[str, str] = {}
    reference_articles = (
        pipeline.load_publication_reference_corpus(repo_root)
        if repo_root is not None
        else None
    )
    for state_path in _selected_run_files(
        queue_root, state_root, "rewrite", selected_run_ids
    ):
        try:
            state, candidate, review = _load_completed_run(state_path)
        except PublishBlocked:
            _record_invalid_candidate_policy_rejection(state_root, "rewrite", state_path)
            continue
        run_id = str(state["run_id"])
        if run_id in released or run_id in quarantined or candidate.get("mode") != "rewrite_existing_body":
            continue
        if not _retry_eligible(state_root, "rewrite", run_id):
            continue
        candidate_article_ids = {str(article["article_id"]) for article in candidate["articles"]}
        if allowed_article_ids is not None and not candidate_article_ids <= allowed_article_ids:
            continue
        if not _review_is_clean_approve(review):
            continue
        run_dir = Path(str(state["run_dir"]))
        brief = _load_rewrite_brief(run_dir, run_id)
        findings = _rewrite_findings_for_run(
            candidate,
            brief,
            reference_articles=reference_articles,
        )
        if findings:
            _record_policy_rejection(state_root, "rewrite", state, candidate, findings)
            continue
        for article in candidate["articles"]:
            article_id = str(article["article_id"])
            if article_id in seen_article_ids:
                raise PublishBlocked(f"duplicate rewrite article id in release batch: {article_id}")
            body_hash = pipeline.body_sha256(article["bodySections"])
            owner = seen_body_hashes.get(body_hash)
            if owner:
                raise PublishBlocked(f"duplicate rewrite body across batch: {owner} and {article_id}")
            seen_article_ids.add(article_id)
            seen_body_hashes[body_hash] = article_id
        ready.append((state, candidate, review, brief))
        if len(ready) >= limit:
            break
    return ready


def _filter_rewrite_runs_with_current_sources(
    repo_root: Path,
    state_root: Path,
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]],
    *,
    quarantine: bool,
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    filtered: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for state, candidate, review, brief in ready:
        try:
            _assert_rewrite_source_matches(repo_root, [candidate])
        except PublishBlocked as exc:
            if quarantine:
                _record_quarantine(state_root, state, str(exc))
            continue
        filtered.append((state, candidate, review, brief))
    return filtered


def summarize_legacy_rewrite_backlog(
    queue_root: Path,
    state_root: Path,
    *,
    allowed_article_ids: set[str],
    legacy_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ledger = _load_ledger(state_root)
    released = {str(item.get("run_id")) for item in ledger["rewrite_released_runs"]}
    quarantined = _rewrite_quarantined_run_ids(ledger)
    summary = {
        "released": 0,
        "quarantined": 0,
        "clean_approve": 0,
        "publish_ready": 0,
        "retry_deferred": 0,
        "retry_exhausted": 0,
        "retry_invalid": 0,
        "reject": 0,
        "active_or_incomplete": 0,
        "non_legacy": 0,
        "legacy_total": len(legacy_records) if legacy_records is not None else len(allowed_article_ids),
        "attempted": 0,
        "unattempted": 0,
        "clean_approve_run_ids": [],
        "publish_ready_run_ids": [],
        "retry_deferred_run_ids": [],
        "retry_exhausted_run_ids": [],
        "retry_invalid_run_ids": [],
        "reject_run_ids": [],
        "unattempted_articles": [],
    }
    attempted_article_ids: set[str] = set()
    for state_path in _run_files(queue_root):
        try:
            raw_state = _read_json(state_path)
        except (OSError, json.JSONDecodeError):
            continue
        if raw_state.get("status") != "complete":
            run_id = str(raw_state.get("run_id") or "")
            run_dir = Path(str(raw_state.get("run_dir") or ""))
            try:
                brief = _load_rewrite_brief(run_dir, run_id)
            except (PublishBlocked, ValueError):
                continue
            brief_article_ids = {str(article["article_id"]) for article in brief["articles"]}
            if not brief_article_ids <= allowed_article_ids:
                summary["non_legacy"] += 1
                continue
            attempted_article_ids.update(brief_article_ids)
            summary["active_or_incomplete"] += 1
            continue
        try:
            state, candidate, review = _load_completed_run(state_path)
        except PublishBlocked:
            run_id = str(raw_state.get("run_id") or "")
            run_dir = Path(str(raw_state.get("run_dir") or ""))
            try:
                brief = _load_rewrite_brief(run_dir, run_id)
            except (PublishBlocked, ValueError):
                continue
            brief_article_ids = {str(article["article_id"]) for article in brief["articles"]}
            if not brief_article_ids <= allowed_article_ids:
                summary["non_legacy"] += 1
                continue
            attempted_article_ids.update(brief_article_ids)
            summary["active_or_incomplete"] += 1
            continue
        if candidate.get("mode") != "rewrite_existing_body":
            continue
        run_id = str(state["run_id"])
        candidate_article_ids = {str(article["article_id"]) for article in candidate["articles"]}
        if not candidate_article_ids <= allowed_article_ids:
            summary["non_legacy"] += 1
            continue
        attempted_article_ids.update(candidate_article_ids)
        if run_id in quarantined:
            summary["quarantined"] += 1
            continue
        if run_id in released:
            summary["released"] += 1
            continue
        run_dir = Path(str(state["run_dir"]))
        try:
            brief = _load_rewrite_brief(run_dir, run_id)
        except PublishBlocked:
            summary["active_or_incomplete"] += 1
            continue
        if _review_is_clean_approve(review) and not _rewrite_findings_for_run(candidate, brief):
            summary["clean_approve"] += 1
            summary["clean_approve_run_ids"].append(run_id)
            retry_eligibility = _retry_eligibility(
                state_root,
                "rewrite",
                run_id,
            )
            count_key = (
                "publish_ready"
                if retry_eligibility == "eligible"
                else f"retry_{retry_eligibility}"
            )
            summary[count_key] += 1
            summary[f"{count_key}_run_ids"].append(run_id)
        else:
            summary["reject"] += 1
            summary["reject_run_ids"].append(run_id)
    summary["attempted"] = len(attempted_article_ids)
    if legacy_records is not None:
        unattempted_records = [record for record in legacy_records if str(record.get("id") or "") not in attempted_article_ids]
        summary["unattempted"] = len(unattempted_records)
        summary["unattempted_articles"] = [_legacy_article_summary(record) for record in unattempted_records]
    else:
        summary["unattempted"] = max(0, len(allowed_article_ids) - len(attempted_article_ids))
    summary["repair_rejects_allowed"] = (
        summary["clean_approve"] == 0
        and summary["active_or_incomplete"] == 0
        and summary["unattempted"] == 0
        and summary["reject"] > 0
    )
    return summary


def _current_version(repo_root: Path) -> tuple[int, int, int]:
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"$', pyproject, flags=re.MULTILINE)
    if not match:
        raise PublishBlocked("pyproject version is missing")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _bump_patch_version(repo_root: Path) -> str:
    major, minor, patch = _current_version(repo_root)
    version = f"{major}.{minor}.{patch + 1}"
    pyproject = repo_root / "pyproject.toml"
    package = repo_root / "package.json"
    pyproject.write_text(
        re.sub(r'^version = "\d+\.\d+\.\d+"$', f'version = "{version}"', pyproject.read_text(encoding="utf-8"), flags=re.MULTILINE),
        encoding="utf-8",
    )
    package_payload = json.loads(package.read_text(encoding="utf-8"))
    package_payload["version"] = version
    package.write_text(json.dumps(package_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return version


def _public_article_count(repo_root: Path) -> int:
    return len(pipeline._registry_inventory(repo_root))


def _serial_sort_key(record: dict[str, Any]) -> tuple[str, int, str]:
    serial = _record_serial(record)
    match = re.fullmatch(r"(.+)-(\d+)", serial)
    if not match:
        return serial, 0, str(record.get("id") or "")
    return match.group(1), int(match.group(2)), str(record.get("id") or "")


def _record_serial(record: dict[str, Any]) -> str:
    if record.get("serial"):
        return str(record["serial"])
    path = str(record.get("path") or "")
    if path:
        return path.rstrip("/").rsplit("/", 1)[-1]
    return str(record.get("id") or "")


def _record_category(record: dict[str, Any]) -> str:
    if record.get("articleCategory") or record.get("product"):
        return str(record.get("articleCategory") or record.get("product"))
    path = str(record.get("path") or "")
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "articles":
        return parts[1]
    return "unknown"


def legacy_article_records(repo_root: Path) -> list[dict[str, Any]]:
    records = pipeline._registry_inventory(repo_root)
    if len(records) < LEGACY_ARTICLE_COUNT_CUTOFF:
        raise PublishBlocked(f"registry has fewer articles than legacy cutoff: {len(records)} < {LEGACY_ARTICLE_COUNT_CUTOFF}")
    return sorted(records[:LEGACY_ARTICLE_COUNT_CUTOFF], key=_serial_sort_key)


def legacy_article_ids(repo_root: Path) -> set[str]:
    return {str(record["id"]) for record in legacy_article_records(repo_root)}


def _legacy_article_summary(record: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(record.get("id") or ""),
        "serial": _record_serial(record),
        "category": _record_category(record),
        "path": str(record.get("path") or ""),
        "title": str(record.get("title") or ""),
    }


def legacy_serial_report(repo_root: Path) -> dict[str, Any]:
    records = legacy_article_records(repo_root)
    by_category: dict[str, list[str]] = {}
    for record in records:
        by_category.setdefault(_record_category(record), []).append(_record_serial(record))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "LEGACY_SERIAL_REPORT",
        "legacy_cutoff_count": LEGACY_ARTICLE_COUNT_CUTOFF,
        "legacy_cutoff_reason": LEGACY_CUTOFF_REASON,
        "legacy_article_count": len(records),
        "serials_by_category": {key: sorted(value, key=lambda serial: _serial_sort_key({"serial": serial, "id": serial})) for key, value in sorted(by_category.items())},
    }


def _prepend_changelog(repo_root: Path, *, version: str, article_count: int, run_ids: list[str], evidence_path: str) -> None:
    changelog = repo_root / "CHANGELOG.md"
    body = changelog.read_text(encoding="utf-8")
    today = date.today().isoformat()
    section = "\n".join(
        [
            f"## [{version}] - {today}",
            "",
            f"- Release tag：`v{version}`",
            f"- 公開文章總數：{article_count}",
            f"- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 {len(run_ids)} 個 run；run_id：{', '.join(run_ids)}。",
            "- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。",
            f"- 證據：`{evidence_path}`",
            "",
        ]
    )
    changelog.write_text(body.replace("\n## [", "\n" + section + "\n## [", 1), encoding="utf-8")


def _prepend_rewrite_changelog(repo_root: Path, *, version: str, article_count: int, run_ids: list[str], article_ids: list[str], evidence_path: str) -> None:
    changelog = repo_root / "CHANGELOG.md"
    body = changelog.read_text(encoding="utf-8")
    today = date.today().isoformat()
    section = "\n".join(
        [
            f"## [{version}] - {today}",
            "",
            f"- Release tag：`v{version}`",
            f"- 公開文章總數：{article_count}（舊文重寫，不新增 registry 條目）",
            f"- 發布範圍：套用 Gemini Reviewer APPROVE 且 deterministic gate 通過的舊文 body override {len(article_ids)} 篇；run_id：{', '.join(run_ids)}。",
            "- 驗證：publisher clean-origin gate、Reviewer hash gate、rewrite deterministic gate、source body drift gate、focused article pipeline tests 與 release record gate。",
            f"- 證據：`{evidence_path}`",
            "",
        ]
    )
    changelog.write_text(body.replace("\n## [", "\n" + section + "\n## [", 1), encoding="utf-8")


def _prepend_translation_changelog(
    repo_root: Path,
    *,
    version: str,
    article_count: int,
    run_ids: list[str],
    locales: list[str],
    evidence_path: str,
) -> None:
    changelog = repo_root / "CHANGELOG.md"
    body = changelog.read_text(encoding="utf-8")
    today = date.today().isoformat()
    section = "\n".join(
        [
            f"## [{version}] - {today}",
            "",
            f"- Release tag：`v{version}`",
            f"- 公開文章總數：{article_count}（新增多語版本，不新增繁中 registry 條目）",
            f"- 發布範圍：發布通過母語品質、Reviewer 與 deterministic gate 的多語文章 {len(run_ids)} 個 run；語系：{', '.join(locales)}；run_id：{', '.join(run_ids)}。",
            "- 驗證：publisher clean-origin gate、來源漂移 gate、多語 deterministic gate、focused multilingual pipeline tests 與 release record gate。",
            f"- 證據：`{evidence_path}`",
            "",
        ]
    )
    changelog.write_text(body.replace("\n## [", "\n" + section + "\n## [", 1), encoding="utf-8")


def _rewrite_release_article_ids(queue_root: Path, run_id: str) -> list[str]:
    """從保留的 rewrite candidate 回溯舊 release 的文章 ID。"""
    for state_path in _run_files(queue_root):
        try:
            state = _read_json(state_path)
            if str(state.get("run_id") or "") != run_id:
                continue
            run_dir = Path(str(state["run_dir"]))
            candidate = _read_json(run_dir / "candidate.json")
        except (OSError, KeyError, json.JSONDecodeError):
            continue
        return [
            str(article["article_id"])
            for article in candidate.get("articles", [])
            if str(article.get("article_id") or "").strip()
        ]
    return []


def _seed_pending_translations(repo_root: Path, queue_root: Path, state_root: Path) -> list[str]:
    """補建已發布新文與成功改寫舊文尚未登記的多語 run。"""
    ledger = _load_ledger(state_root)
    seeded_run_ids: list[str] = []
    changed = False
    for item in ledger["rewrite_released_runs"]:
        if item.get("translation_seed_status") == "seeded":
            continue
        if not item.get("article_ids"):
            article_ids = _rewrite_release_article_ids(queue_root, str(item.get("run_id") or ""))
            if not article_ids:
                continue
            item["article_ids"] = article_ids
            changed = True
        if item.get("translation_seed_status") != "pending":
            item["translation_seed_status"] = "pending"
            changed = True
    for item in [*ledger["published_runs"], *ledger["rewrite_released_runs"]]:
        if item.get("translation_seed_status") != "pending":
            continue
        translation_runs: list[dict[str, str]] = []
        for article_id in item.get("article_ids", []):
            translation_runs.extend(
                multilingual.enqueue_article_translations(
                    repo_root,
                    queue_root,
                    source_run_id=str(item["run_id"]),
                    article_id=str(article_id),
                )
            )
        item["translation_seed_status"] = "seeded"
        item["translation_seeded_at"] = _now()
        item["translation_run_ids"] = [run["run_id"] for run in translation_runs]
        seeded_run_ids.extend(item["translation_run_ids"])
        changed = True
    if changed:
        _write_json(_ledger_path(state_root), ledger)
    return seeded_run_ids


def _sync_web_test_release_fixture(repo_root: Path, *, cache_token: str, articles: list[dict[str, Any]]) -> Path:
    test_path = repo_root / "tests/test_web.py"
    text = test_path.read_text(encoding="utf-8")
    text = re.sub(r'ARTICLE_CACHE_TOKEN = "[^"]+"', f'ARTICLE_CACHE_TOKEN = "{cache_token}"', text, count=1)
    paths = [_article_path(article) for article in articles]
    marker = "DAILY_PUBLIC_ARTICLE_PATHS = [\n"
    start = text.index(marker) + len(marker)
    closing = re.search(r"^]\r?$", text[start:], flags=re.MULTILINE)
    if closing is None:
        raise PublishBlocked("DAILY_PUBLIC_ARTICLE_PATHS closing bracket not found")
    end = start + closing.start()
    block = text[start:end]
    for path in paths:
        line = f'    "{path}",\n'
        if line not in block:
            block += line
    text = text[:start] + block + text[end:]
    test_path.write_text(text, encoding="utf-8")
    return test_path


def _sync_web_test_cache_token(repo_root: Path, *, cache_token: str) -> Path:
    pipeline._bump_article_cache_queries(repo_root, cache_token)
    test_path = repo_root / "tests/test_web.py"
    text = test_path.read_text(encoding="utf-8")
    text = re.sub(r'ARTICLE_CACHE_TOKEN = "[^"]+"', f'ARTICLE_CACHE_TOKEN = "{cache_token}"', text, count=1)
    test_path.write_text(text, encoding="utf-8")
    return test_path


def _run_prerender(
    repo_root: Path,
    *,
    required_article_modes: dict[str, str] | None = None,
) -> None:
    command = [*PROJECT_PYTHON_COMMAND, "scripts/prerender_article_shells.py"]
    for article_id, mode in sorted((required_article_modes or {}).items()):
        command.extend(["--required-article-mode", f"{article_id}={mode}"])
    with tempfile.TemporaryDirectory(prefix="agy-prerender-policy-") as temp_dir:
        failure_path = Path(temp_dir) / "failure.json"
        command.extend(["--policy-failure-output", str(failure_path)])
        started_at = time.monotonic()
        try:
            _run_checked(
                repo_root,
                command,
                timeout_seconds=PRERENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            diagnostic = {
                "command": command,
                "cwd": str(repo_root),
                "elapsed_seconds": time.monotonic() - started_at,
                "timeout_seconds": PRERENDER_TIMEOUT_SECONDS,
                "process_outcome": "timed_out",
            }
            raise PrerenderTimeout(diagnostic) from error
        except subprocess.CalledProcessError as error:
            if not failure_path.is_file():
                raise
            payload = _read_json(failure_path)
            findings = [
                pipeline._policy_finding(
                    str(article_id),
                    str(code),
                    "prerender acceptance required policy finding",
                )
                for article_id in payload.get("article_ids") or []
                for code in payload.get("failure_codes") or []
            ]
            raise PolicyRejected(findings) from error


def _run_feed(repo_root: Path) -> None:
    _run_checked(repo_root, [*PROJECT_PYTHON_COMMAND, "scripts/generate_feed.py"])


def _run_checked(
    repo_root: Path,
    args: list[str],
    *,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> None:
    run_kwargs: dict[str, Any] = {
        "cwd": repo_root,
        "check": True,
        "timeout": timeout_seconds,
    }
    if env is not None:
        run_kwargs["env"] = env
    subprocess.run(args, **run_kwargs)


_RELEASE_TEST_ENV_PREFIXES = ("PANTHEON_RUNTIME_",)
_RELEASE_TEST_ENV_KEYS = {
    "PANTHEON_FORMAL_RUNTIME",
    "AGY_GEMINI_MODEL_ROUTE_CONFIG",
    "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST",
    "AGY_WRITER_MODEL",
    "AGY_REVIEWER_MODEL",
}


def _release_test_child_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key in _RELEASE_TEST_ENV_KEYS or any(
            key.startswith(prefix) for prefix in _RELEASE_TEST_ENV_PREFIXES
        ):
            env.pop(key, None)
    return env


def _run_release_tests(repo_root: Path) -> None:
    """先跑快速結構檢查，通過後才進完整 release gate。"""
    child_env = _release_test_child_env()
    _run_checked(repo_root, PREFLIGHT_TEST_COMMAND, env=child_env)
    _run_checked(repo_root, TEST_COMMAND, env=child_env)


def _stage_commit_tag_push(
    repo_root: Path,
    version: str,
    git: GitRunner = run_git,
    *,
    push: bool,
    release_gate: bool,
    message: str | None = None,
    extra_add_paths: list[str] | None = None,
    outcome_evidence_dir: Path | None = None,
    state_root: Path | None = None,
    phase: str | None = None,
    run_ids: list[str] | None = None,
    checked_runner: Callable[[Path, list[str]], None] | None = None,
) -> str:
    release_plan = release_git_plan(version)
    run_checked = checked_runner or _run_checked
    if push:
        run_checked(repo_root, [*PROJECT_PYTHON_COMMAND, "scripts/verify_host_canonical.py"])
    git(repo_root, ["add", "app/web", "tests/test_web.py", "pyproject.toml", "package.json", "CHANGELOG.md"], None)
    if extra_add_paths:
        git(repo_root, ["add", *extra_add_paths], None)
    git(repo_root, ["commit", "-m", message or f"chore(content): publish Gemini approved articles v{version}"], None)
    git(repo_root, release_plan["tag"], None)
    commit_sha = git(repo_root, ["rev-parse", "HEAD"], None)
    if release_gate:
        run_checked(
            repo_root,
            [
                *PROJECT_PYTHON_COMMAND,
                "scripts/check_release_record.py",
                "--base-ref",
                "origin/main",
                "--require-head-tag",
            ],
        )
    if push:
        try:
            git(repo_root, release_plan["push"], None)
        except Exception as push_error:
            git(repo_root, ["fetch", "origin", "main"], None)
            remote_main = git(repo_root, ["rev-parse", "origin/main"], None)
            remote_tags = git(
                repo_root,
                ["ls-remote", "origin", f"refs/tags/v{version}", f"refs/tags/v{version}^{{}}"],
                None,
            )
            tag_lines = [line.split() for line in remote_tags.splitlines() if line.strip()]
            remote_tag = ""
            reconcile_ref = f"refs/agy-publisher-reconcile/v{version}"
            if tag_lines:
                try:
                    git(
                        repo_root,
                        ["fetch", "--force", "origin", f"refs/tags/v{version}:{reconcile_ref}"],
                        None,
                    )
                    remote_tag = git(repo_root, ["rev-parse", f"{reconcile_ref}^{{}}"], None)
                finally:
                    git(repo_root, ["update-ref", "-d", reconcile_ref], None)
            if remote_main == commit_sha and remote_tag == commit_sha:
                return commit_sha
            if remote_main != commit_sha and not remote_tag:
                raise push_error
            evidence_dir = outcome_evidence_dir or repo_root / ".git"
            evidence_path = evidence_dir / "push-outcome-unknown.json"
            outcome = {
                "schema_version": SCHEMA_VERSION,
                "status": "PUSH_OUTCOME_UNKNOWN",
                "version": version,
                "candidate_sha": commit_sha,
                "remote_main": remote_main,
                "remote_tag": remote_tag or None,
                "remote_tag_lines": remote_tags.splitlines(),
                "error_type": type(push_error).__name__,
                "error": str(push_error),
                "recorded_at": _now(),
            }
            if state_root is not None:
                if phase not in {"create", "rewrite", "translation"} or not run_ids:
                    raise PublishBlocked("push control context is incomplete") from push_error
                evidence_name = {
                    "create": "publish-evidence.json",
                    "rewrite": "rewrite-evidence.json",
                    "translation": "translation-evidence.json",
                }[phase]
                _atomic_write_json(
                    _unresolved_push_path(state_root),
                    {
                        **outcome,
                        "phase": phase,
                        "run_ids": list(run_ids),
                        "outcome_evidence": str(evidence_path),
                        "publish_evidence": str(evidence_dir / evidence_name),
                    },
                )
            _atomic_write_json(evidence_path, outcome)
            raise PushOutcomeUnknown(f"atomic push outcome is inconsistent; evidence: {evidence_path}") from push_error
    return commit_sha


def _rewrite_identity_for_inventory_item(item: dict[str, Any]) -> dict[str, str]:
    record = item["record"]
    return {
        "id": str(record["id"]),
        "product": str(record["product"]),
        "category": str(record["articleCategory"]),
        "serial": str(record["serial"]),
        "slug": str(record["urlSlug"]),
        "primaryKeyword": str(record["primaryKeyword"]),
        "title": str(record["title"]),
    }


def _assert_rewrite_source_matches(
    repo_root: Path,
    candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    inventory = pipeline._existing_rewrite_inventory(repo_root)
    for candidate in candidates:
        for article in candidate["articles"]:
            article_id = str(article["article_id"])
            current = inventory.get(article_id)
            if current is None:
                raise PublishBlocked(f"rewrite source article no longer exists: {article_id}")
            record = current.get("record")
            if not isinstance(record, dict):
                raise PublishBlocked(f"rewrite source record is missing: {article_id}")
            body_slug = record.get("slug")
            if not isinstance(body_slug, str) or not body_slug.strip():
                raise PublishBlocked(f"rewrite source body slug is missing: {article_id}")
            if article["identity"] != _rewrite_identity_for_inventory_item(current):
                raise PublishBlocked(f"rewrite identity drift for {article_id}")
            actual_hash = pipeline.body_sha256(current["currentBody"])
            approved_hash = pipeline.body_sha256(article["bodySections"])
            if actual_hash not in {str(article["current_body_sha256"]), approved_hash}:
                raise PublishBlocked(f"rewrite body drift for {article_id}")
    return inventory


def _update_rewrite_body_override_lookup(meta_path: Path, export_name: str) -> None:
    text = meta_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(?m)^(\s*const customBody = )(.+?);$")
    match = pattern.search(text)
    if not match:
        raise PublishBlocked("article-meta customBody lookup marker not found")
    expression = match.group(2)
    token = f"{export_name}[article.slug]"
    if token in expression:
        return
    updated_expression = f"{token} || {expression}"
    text = text[: match.start(2)] + updated_expression + text[match.end(2) :]
    meta_path.write_text(text, encoding="utf-8")


def _update_rewrite_policy_override_lookup(registry_path: Path, export_name: str) -> None:
    text = registry_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(?m)^(\s*const customPolicy = )(.+?);$")
    match = pattern.search(text)
    if not match:
        raise PublishBlocked("article registry customPolicy lookup marker not found")
    expression = match.group(2)
    token = f"{export_name}[article.id]"
    if token in expression:
        return
    updated_expression = f"{token} || {expression}"
    text = text[: match.start(2)] + updated_expression + text[match.end(2) :]
    registry_path.write_text(text, encoding="utf-8")


def _next_rewrite_release_id(repo_root: Path, release_day: date | None = None) -> str:
    """配置當日尚未使用的 rewrite release ID，避免服務重啟後覆寫舊模組。"""
    day_token = (release_day or date.today()).strftime("%Y%m%d")
    pattern = re.compile(
        rf"^article-rewrite-agy-rewrite-{day_token}-(\d+)\.js$"
    )
    sequences = [
        int(match.group(1))
        for path in (repo_root / "app/web/static").glob(
            f"article-rewrite-agy-rewrite-{day_token}-*.js"
        )
        if (match := pattern.fullmatch(path.name))
    ]
    return f"agy-rewrite-{day_token}-{max(sequences, default=0) + 1:02d}"


def apply_rewrite_release(repo_root: Path, release_id: str, candidates: list[dict[str, Any]]) -> list[Path]:
    if not candidates:
        return []
    inventory = _assert_rewrite_source_matches(repo_root, candidates)
    reference_articles = pipeline.load_publication_reference_corpus(repo_root)
    for candidate in candidates:
        for article in candidate["articles"]:
            policy_article = {
                **article["identity"],
                "id": article["article_id"],
                "current_body_sha256": article["current_body_sha256"],
                "bodySections": article["bodySections"],
                "publicationPolicy": article["publicationPolicy"],
            }
            findings = pipeline.required_policy_findings(
                pipeline.article_publication_policy_findings(
                    policy_article,
                    mode="rewrite_existing_body",
                    reference_articles=reference_articles,
                )
            )
            if findings:
                raise PublishBlocked(
                    f"policy v2 rewrite apply blocked {article['article_id']}: "
                    f"{','.join(sorted({finding['code'] for finding in findings}))}"
                )
    file_slug, identifier = pipeline._safe_identifier(release_id)
    export_name = f"AGY_{identifier}_REWRITE_BODY_OVERRIDES"
    policy_export_name = f"AGY_{identifier}_REWRITE_POLICY_OVERRIDES"
    module = repo_root / "app/web/static" / f"article-rewrite-{file_slug}.js"
    if module.exists():
        raise PublishBlocked(f"rewrite release id already exists: {release_id}")
    bodies: dict[str, list[dict[str, Any]]] = {}
    policies: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        for article in candidate["articles"]:
            article_id = str(article["article_id"])
            slug = str(inventory[article_id]["record"]["slug"])
            if slug in bodies:
                raise PublishBlocked(f"duplicate rewrite slug in release batch: {slug}")
            bodies[slug] = article["bodySections"]
            policies[article_id] = {
                "updated": article["publicationPolicy"]["modified"],
                "publicationPolicy": article["publicationPolicy"],
            }
    module.write_text(
        f"export const {export_name} = {json.dumps(bodies, ensure_ascii=False, indent=2)};\n\n"
        f"export const {policy_export_name} = {json.dumps(policies, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    meta_path = repo_root / "app/web/static/article-meta.js"
    import_line = f'import {{ {export_name} }} from "./{module.name}?v={release_id}";\n'
    meta = meta_path.read_text(encoding="utf-8")
    meta = pipeline._insert_once(meta, "const ARTICLE_BODY_LIBRARY = {", import_line + "\n")
    meta_path.write_text(meta, encoding="utf-8")
    _update_rewrite_body_override_lookup(meta_path, export_name)
    registry_path = repo_root / "app/web/static/article-registry.js"
    registry_import = (
        f'import {{ {policy_export_name} }} from "./{module.name}?v={release_id}";\n'
    )
    registry = registry_path.read_text(encoding="utf-8")
    registry = pipeline._insert_once(
        registry,
        "export const ARTICLE_REGISTRY = [",
        registry_import + "\n",
    )
    registry_path.write_text(registry, encoding="utf-8")
    _update_rewrite_policy_override_lookup(registry_path, policy_export_name)
    changed = [module, meta_path, registry_path]
    hub_updated_date = max(
        str(article["publicationPolicy"]["modified"])
        for candidate in candidates
        for article in candidate["articles"]
    )
    changed.extend(
        pipeline._bump_article_cache_queries(
            repo_root,
            release_id,
            hub_updated_date=hub_updated_date,
        )
    )
    return changed


@_recoverable_publish("create", "published")
def publish_ready_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
    git: GitRunner = run_git,
    _transaction_base_sha: str | None = None,
    _mutation_journal: MutationJournal | None = None,
    exact_run_ids: Iterable[str] | None = None,
    seed_translations: bool = True,
) -> dict[str, Any]:
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "published": 0}
        base_sha = _transaction_base_sha or _assert_clean_origin_head(repo_root, git)
        recovered_translation_runs = (
            []
            if dry_run or selected_run_ids is not None or not seed_translations
            else _seed_pending_translations(repo_root, queue_root, state_root)
        )
        ready = collect_ready_runs(
            queue_root,
            state_root,
            limit=max_runs,
            repo_root=repo_root,
            exact_run_ids=selected_run_ids,
        )
        if not ready:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "idle",
                "published": 0,
                "base_sha": base_sha,
                "seeded_translation_runs": recovered_translation_runs,
            }
        run_ids = [str(state["run_id"]) for state, _, _ in ready]
        journal = _mutation_journal or MutationJournal(repo_root, git)
        journal.select_runs(run_ids)
        if dry_run:
            return {"schema_version": SCHEMA_VERSION, "status": "dry-run", "published": 0, "ready_runs": run_ids, "base_sha": base_sha}

        journal.begin()
        changed: list[str] = []
        approved_articles: list[dict[str, Any]] = []
        cache_token = ""
        for state, candidate, review in ready:
            decisions = {str(item["id"]): "APPROVE" for item in candidate["articles"]}
            approval = pipeline.build_approval(str(candidate["run_id"]), candidate["articles"], review, decisions, PUBLISHER_ID)
            run_dir = Path(str(state["run_dir"]))
            _write_json(run_dir / "approval.json", approval)
            applied_paths = journal.capture(
                lambda: pipeline.apply_approved_candidates(
                    repo_root,
                    str(candidate["run_id"]),
                    candidate["articles"],
                    review,
                    approval,
                )
            )
            changed.extend(str(path.relative_to(repo_root)) for path in applied_paths)
            approved_articles.extend(candidate["articles"])
            cache_token = f"agy-{pipeline._safe_identifier(str(candidate['run_id']))[0]}"

        version = journal.capture(lambda: _bump_patch_version(repo_root))
        evidence_dir = state_root / "evidence" / f"publish-{version}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_rel = evidence_dir.relative_to(repo_root).as_posix() if evidence_dir.is_relative_to(repo_root) else str(evidence_dir)
        article_count = _public_article_count(repo_root)
        fixture_path = journal.capture(
            lambda: _sync_web_test_release_fixture(
                repo_root,
                cache_token=cache_token,
                articles=approved_articles,
            )
        )
        changed.append(str(fixture_path.relative_to(repo_root)))
        journal.capture(
            lambda: _run_prerender(
                repo_root,
                required_article_modes={
                    str(article["id"]): "create"
                    for article in approved_articles
                },
            )
        )
        journal.capture(lambda: _run_feed(repo_root))
        journal.capture(
            lambda: _prepend_changelog(
                repo_root,
                version=version,
                article_count=article_count,
                run_ids=run_ids,
                evidence_path=evidence_rel,
            )
        )
        if run_tests:
            _run_release_tests(repo_root)
        commit_sha = _stage_commit_tag_push(
            repo_root,
            version,
            git,
            push=push,
            release_gate=release_gate,
            outcome_evidence_dir=evidence_dir,
            state_root=state_root,
            phase="create",
            run_ids=run_ids,
        )
        ledger = _load_ledger(state_root)
        articles_by_run = {
            str(state["run_id"]): [str(article["id"]) for article in candidate["articles"]]
            for state, candidate, _ in ready
        }
        for run_id in run_ids:
            ledger["published_runs"].append(
                {
                    "run_id": run_id,
                    "version": version,
                    "commit_sha": commit_sha,
                    "published_at": _now(),
                    "article_ids": articles_by_run[run_id],
                    "translation_seed_status": "pending",
                }
            )
        _write_json(_ledger_path(state_root), ledger)
        seeded_translation_runs = (
            []
            if selected_run_ids is not None or not seed_translations
            else [
                *recovered_translation_runs,
                *_seed_pending_translations(repo_root, queue_root, state_root),
            ]
        )
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "status": "PUBLISHED",
            "base_sha": base_sha,
            "commit_sha": commit_sha,
            "version": version,
            "run_ids": run_ids,
            "changed": sorted(set(changed)),
            "public_article_count": article_count,
            "seeded_translation_runs": seeded_translation_runs,
            "pushed": push,
            "policy_version": pipeline.publication_policy_version(),
            "validator_result": "PASS",
            "article_ids": sorted(
                str(article["id"])
                for candidate in [candidate for _, candidate, _ in ready]
                for article in candidate["articles"]
            ),
            "failure_codes": [],
            "input_hash": hashlib.sha256(
                pipeline.compact_json_bytes(
                    [candidate for _, candidate, _ in ready]
                )
            ).hexdigest(),
        }
        _write_json(evidence_dir / "publish-evidence.json", evidence)
        return evidence


@_recoverable_publish("rewrite", "rewritten")
def publish_ready_rewrite_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
    git: GitRunner = run_git,
    _transaction_base_sha: str | None = None,
    _mutation_journal: MutationJournal | None = None,
    exact_run_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "rewritten": 0}
        base_sha = _transaction_base_sha or _assert_clean_origin_head(repo_root, git)
        legacy_records = legacy_article_records(repo_root)
        allowed_article_ids = {str(record["id"]) for record in legacy_records}
        backlog_summary = summarize_legacy_rewrite_backlog(
            queue_root,
            state_root,
            allowed_article_ids=allowed_article_ids,
            legacy_records=legacy_records,
        )
        ready = collect_ready_rewrite_runs(
            queue_root,
            state_root,
            limit=max_runs,
            allowed_article_ids=allowed_article_ids,
            repo_root=repo_root,
            exact_run_ids=selected_run_ids,
        )
        ready = _filter_rewrite_runs_with_current_sources(repo_root, state_root, ready, quarantine=not dry_run)
        if not ready:
            backlog_summary = summarize_legacy_rewrite_backlog(
                queue_root,
                state_root,
                allowed_article_ids=allowed_article_ids,
                legacy_records=legacy_records,
            )
            status = "idle_rejects_only" if backlog_summary["repair_rejects_allowed"] else "idle"
            return {
                "schema_version": SCHEMA_VERSION,
                "status": status,
                "rewritten": 0,
                "base_sha": base_sha,
                "legacy_cutoff_count": LEGACY_ARTICLE_COUNT_CUTOFF,
                "legacy_rewrite_backlog": backlog_summary,
            }
        run_ids = [str(state["run_id"]) for state, _, _, _ in ready]
        candidates = [candidate for _, candidate, _, _ in ready]
        article_ids = [str(article["article_id"]) for candidate in candidates for article in candidate["articles"]]
        journal = _mutation_journal or MutationJournal(repo_root, git)
        journal.select_runs(run_ids)
        if dry_run:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "dry-run",
                "rewritten": 0,
                "ready_runs": run_ids,
                "article_ids": article_ids,
                "base_sha": base_sha,
                "legacy_cutoff_count": LEGACY_ARTICLE_COUNT_CUTOFF,
                "legacy_rewrite_backlog": backlog_summary,
            }

        journal.begin()
        release_id = _next_rewrite_release_id(repo_root)
        changed = [
            str(path.relative_to(repo_root))
            for path in journal.capture(lambda: apply_rewrite_release(repo_root, release_id, candidates))
        ]
        version = journal.capture(lambda: _bump_patch_version(repo_root))
        evidence_dir = state_root / "evidence" / f"rewrite-{version}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_rel = evidence_dir.relative_to(repo_root).as_posix() if evidence_dir.is_relative_to(repo_root) else str(evidence_dir)
        article_count = _public_article_count(repo_root)
        fixture_path = journal.capture(lambda: _sync_web_test_cache_token(repo_root, cache_token=release_id))
        changed.append(str(fixture_path.relative_to(repo_root)))
        journal.capture(
            lambda: _run_prerender(
                repo_root,
                required_article_modes={
                    article_id: "rewrite_existing_body"
                    for article_id in article_ids
                },
            )
        )
        journal.capture(lambda: _run_feed(repo_root))
        journal.capture(
            lambda: _prepend_rewrite_changelog(
                repo_root,
                version=version,
                article_count=article_count,
                run_ids=run_ids,
                article_ids=article_ids,
                evidence_path=evidence_rel,
            )
        )
        if run_tests:
            _run_release_tests(repo_root)
        commit_sha = _stage_commit_tag_push(
            repo_root,
            version,
            git,
            push=push,
            release_gate=release_gate,
            message=f"chore(content): publish Gemini rewrite release v{version}",
            extra_add_paths=["scripts/agy_content_publisher.py"],
            outcome_evidence_dir=evidence_dir,
            state_root=state_root,
            phase="rewrite",
            run_ids=run_ids,
        )
        ledger = _load_ledger(state_root)
        for run_id in run_ids:
            ledger["rewrite_released_runs"].append(
                {
                    "run_id": run_id,
                    "version": version,
                    "commit_sha": commit_sha,
                    "published_at": _now(),
                    "article_ids": [
                        str(article["article_id"])
                        for candidate in candidates
                        for article in candidate["articles"]
                        if str(candidate["run_id"]) == run_id
                    ],
                    "translation_seed_status": "pending",
                }
            )
        _write_json(_ledger_path(state_root), ledger)
        seeded_translation_runs = _seed_pending_translations(repo_root, queue_root, state_root)
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "status": "PUBLISHED_REWRITE",
            "base_sha": base_sha,
            "commit_sha": commit_sha,
            "version": version,
            "run_ids": run_ids,
            "article_ids": article_ids,
            "changed": sorted(set(changed)),
            "public_article_count": article_count,
            "legacy_cutoff_count": LEGACY_ARTICLE_COUNT_CUTOFF,
            "legacy_rewrite_backlog": backlog_summary,
            "seeded_translation_runs": seeded_translation_runs,
            "pushed": push,
            "policy_version": pipeline.publication_policy_version(),
            "validator_result": "PASS",
            "failure_codes": [],
            "input_hash": hashlib.sha256(
                pipeline.compact_json_bytes(candidates)
            ).hexdigest(),
        }
        _write_json(evidence_dir / "rewrite-evidence.json", evidence)
        return evidence


@_recoverable_publish("translation", "translated")
def publish_ready_translation_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
    git: GitRunner = run_git,
    _transaction_base_sha: str | None = None,
    _mutation_journal: MutationJournal | None = None,
    exact_run_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """發布所有已通過的單語 run；退件留待最後修復且不阻塞通過者。"""
    selected_run_ids = _normalize_exact_run_ids(exact_run_ids)
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "translated": 0}
        base_sha = _transaction_base_sha or _assert_clean_origin_head(repo_root, git)
        ready = collect_ready_translation_runs(
            repo_root,
            queue_root,
            state_root,
            limit=max_runs,
            exact_run_ids=selected_run_ids,
        )
        if not ready:
            ledger = _load_ledger(state_root)
            status = "idle_rejects_only" if ledger["translation_deferred_runs"] else "idle"
            return {"schema_version": SCHEMA_VERSION, "status": status, "translated": 0, "base_sha": base_sha}
        ready_run_ids = [str(state["run_id"]) for state, _, _, _ in ready]
        journal = _mutation_journal or MutationJournal(repo_root, git)
        journal.select_runs(ready_run_ids)
        if dry_run:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "dry-run",
                "translated": 0,
                "ready_runs": ready_run_ids,
                "base_sha": base_sha,
            }

        journal.begin()
        changed: list[str] = []
        published: list[tuple[str, str, str]] = []
        for state, _brief, candidate, _review in ready:
            run_id = str(state["run_id"])
            locale = str(candidate["articles"][0]["locale"])
            article_id = str(candidate["articles"][0]["source_article_id"])
            try:
                paths = journal.capture(
                    lambda: multilingual.approve_and_apply_translation_run(
                        repo_root,
                        Path(str(state["run_dir"])),
                        PUBLISHER_ID,
                    )
                )
            except ValueError as error:
                _record_translation_deferred(state_root, run_id, f"translation apply failed: {error}")
                continue
            changed.extend(str(path.relative_to(repo_root)) for path in paths)
            published.append((run_id, locale, article_id))
        if not published:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "idle_rejects_only",
                "translated": 0,
                "base_sha": base_sha,
            }

        run_ids = [item[0] for item in published]
        locales = [item[1] for item in published]
        article_ids = [item[2] for item in published]
        version = journal.capture(lambda: _bump_patch_version(repo_root))
        evidence_dir = state_root / "evidence" / f"translation-{version}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_rel = evidence_dir.relative_to(repo_root).as_posix() if evidence_dir.is_relative_to(repo_root) else str(evidence_dir)
        article_count = _public_article_count(repo_root)
        cache_token = f"agy-i18n-{version.replace('.', '-')}"
        changed.extend(
            str(path.relative_to(repo_root))
            for path in journal.capture(lambda: pipeline._bump_article_cache_queries(repo_root, cache_token))
        )
        fixture_path = journal.capture(lambda: _sync_web_test_cache_token(repo_root, cache_token=cache_token))
        changed.append(str(fixture_path.relative_to(repo_root)))
        journal.capture(lambda: _run_prerender(repo_root))
        journal.capture(lambda: _run_feed(repo_root))
        journal.capture(
            lambda: _prepend_translation_changelog(
                repo_root,
                version=version,
                article_count=article_count,
                run_ids=run_ids,
                locales=locales,
                evidence_path=evidence_rel,
            )
        )
        if run_tests:
            _run_release_tests(repo_root)
        commit_sha = _stage_commit_tag_push(
            repo_root,
            version,
            git,
            push=push,
            release_gate=release_gate,
            message=f"chore(content): publish multilingual release v{version}",
            outcome_evidence_dir=evidence_dir,
            state_root=state_root,
            phase="translation",
            run_ids=run_ids,
        )
        ledger = _load_ledger(state_root)
        for run_id, locale, article_id in published:
            ledger["translation_published_runs"].append(
                {
                    "run_id": run_id,
                    "locale": locale,
                    "article_id": article_id,
                    "version": version,
                    "commit_sha": commit_sha,
                    "published_at": _now(),
                }
            )
        _write_json(_ledger_path(state_root), ledger)
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "status": "PUBLISHED_TRANSLATION",
            "base_sha": base_sha,
            "commit_sha": commit_sha,
            "version": version,
            "run_ids": run_ids,
            "locales": locales,
            "article_ids": article_ids,
            "changed": sorted(set(changed)),
            "public_article_count": article_count,
            "pushed": push,
        }
        _write_json(evidence_dir / "translation-evidence.json", evidence)
        return evidence


def publish_ready_all(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    dry_run: bool = False,
    push: bool = False,
    run_tests: bool = True,
    release_gate: bool = True,
    git: GitRunner = run_git,
    exact_run_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """同一輪先處理新文、舊文，再發布已通過的多語版本。"""
    selector_kwargs = (
        {"exact_run_ids": exact_run_ids} if exact_run_ids is not None else {}
    )
    create_result = publish_ready_runs(
        repo_root,
        queue_root,
        state_root,
        max_runs=max_runs,
        dry_run=dry_run,
        push=push,
        run_tests=run_tests,
        release_gate=release_gate,
        git=git,
        **selector_kwargs,
    )
    rewrite_result = publish_ready_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        max_runs=max_runs,
        dry_run=dry_run,
        push=push,
        run_tests=run_tests,
        release_gate=release_gate,
        git=git,
        **selector_kwargs,
    )
    translation_result = publish_ready_translation_runs(
        repo_root,
        queue_root,
        state_root,
        max_runs=max_runs,
        dry_run=dry_run,
        push=push,
        run_tests=run_tests,
        release_gate=release_gate,
        git=git,
        **selector_kwargs,
    )
    create_ok = create_result.get("status") in SUCCESS_STATUSES
    rewrite_ok = rewrite_result.get("status") in SUCCESS_STATUSES
    translation_ok = translation_result.get("status") in SUCCESS_STATUSES
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if create_ok and rewrite_ok and translation_ok else "failed",
        "create": create_result,
        "rewrite": rewrite_result,
        "translation": translation_result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--queue-root", type=Path)
    parser.add_argument("--state-root", type=Path, default=Path(".work/content-publisher"))
    parser.add_argument("--max-runs", type=int, default=DEFAULT_MAX_RUNS)
    parser.add_argument("--exact-run-id", action="append")
    parser.add_argument("--exact-fresh-ja-run-id")
    parser.add_argument("--prepare-exact-fresh-ja-source-run-id")
    parser.add_argument("--prepare-exact-fresh-ja-article-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rewrite-release", action="store_true")
    parser.add_argument("--include-rewrites", action="store_true")
    parser.add_argument("--new-only", action="store_true")
    parser.add_argument("--legacy-report", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--deployment-preflight", action="store_true")
    parser.add_argument(
        "--manifest-authorized-deployment-preflight",
        action="store_true",
    )
    parser.add_argument("--runtime-manifest-authority", type=Path)
    parser.add_argument("--expected-manifest-digest")
    parser.add_argument(
        "--recover-exhausted-create-run",
        action="append",
        default=[],
    )
    parser.add_argument("--expected-retry-error")
    parser.add_argument("--expected-recovery-digest")
    parser.add_argument("--recovery-reason")
    parser.add_argument("--expected-repo-root", type=Path)
    parser.add_argument("--expected-queue-root", type=Path)
    parser.add_argument("--expected-state-root", type=Path)
    parser.add_argument("--expected-runtime-sha")
    parser.add_argument("--expected-runtime-digest")
    parser.add_argument(
        "--expected-push-mode",
        choices=("push", "no-push"),
    )
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-release-gate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    new_only = bool(getattr(args, "new_only", False))
    exact_run_ids = _normalize_exact_run_ids(
        getattr(args, "exact_run_id", None)
    )
    fresh_ja_run_id = getattr(args, "exact_fresh_ja_run_id", None)
    fresh_ja_prepare_values = (
        getattr(args, "prepare_exact_fresh_ja_source_run_id", None),
        getattr(args, "prepare_exact_fresh_ja_article_id", None),
    )
    fresh_ja_prepare = any(value is not None for value in fresh_ja_prepare_values)
    if fresh_ja_prepare and not all(value is not None for value in fresh_ja_prepare_values):
        raise SystemExit("exact fresh JA prepare requires source run and article ids")
    if fresh_ja_prepare and fresh_ja_run_id is not None:
        raise SystemExit("exact fresh JA prepare returns the deterministic run id; publish it in a later command")
    if fresh_ja_run_id is not None and exact_run_ids is not None:
        raise SystemExit("--exact-fresh-ja-run-id cannot be combined with --exact-run-id")
    selector_kwargs = (
        {"exact_run_ids": exact_run_ids} if exact_run_ids is not None else {}
    )
    repo_root = args.repo_root.resolve()
    if args.legacy_report:
        print(json.dumps(legacy_serial_report(repo_root), ensure_ascii=False))
        return 0
    if args.queue_root is None:
        raise SystemExit("--queue-root is required unless --legacy-report is set")
    if sum((args.rewrite_release, args.include_rewrites, new_only)) > 1:
        raise SystemExit("publisher release modes cannot be combined")
    if fresh_ja_run_id is not None and (
        args.rewrite_release
        or args.include_rewrites
        or new_only
        or args.skip_tests
        or args.skip_release_gate
    ):
        raise SystemExit("exact fresh JA release only supports the publisher transaction contract")
    if fresh_ja_prepare and (args.dry_run or args.push):
        raise SystemExit("exact fresh JA prepare only registers a local queue run")
    recovery_run_ids = list(
        getattr(args, "recover_exhausted_create_run", []) or []
    )
    if recovery_run_ids and (
        args.rewrite_release
        or args.include_rewrites
        or new_only
        or args.legacy_report
    ):
        raise SystemExit("retry recovery cannot be combined with release modes")
    if fresh_ja_run_id is not None:
        publisher_fn = None
    elif args.include_rewrites:
        publisher_fn = publish_ready_all
    elif args.rewrite_release:
        publisher_fn = publish_ready_rewrite_runs
    else:
        publisher_fn = publish_ready_runs
        if new_only:
            selector_kwargs["seed_translations"] = False
    queue_root = args.queue_root.resolve()
    state_root = (repo_root / args.state_root).resolve() if not args.state_root.is_absolute() else args.state_root.resolve()
    _validate_formal_runtime(repo_root, queue_root, state_root)
    _trim_configured_launchd_logs()
    contract_values = (
        getattr(args, "expected_repo_root", None),
        getattr(args, "expected_queue_root", None),
        getattr(args, "expected_state_root", None),
        getattr(args, "expected_runtime_sha", None),
        getattr(args, "expected_runtime_digest", None),
        getattr(args, "expected_push_mode", None),
    )
    if any(value is not None for value in contract_values) and not all(
        value is not None for value in contract_values
    ):
        raise SystemExit("deployment contract requires all expected values")
    if getattr(args, "deployment_preflight", False) and not all(
        value is not None for value in contract_values
    ):
        raise SystemExit("--deployment-preflight requires a complete deployment contract")
    manifest_authority_values = (
        getattr(args, "manifest_authorized_deployment_preflight", False),
        getattr(args, "runtime_manifest_authority", None),
        getattr(args, "expected_manifest_digest", None),
    )
    if any(bool(value) for value in manifest_authority_values) and not all(
        bool(value) for value in manifest_authority_values
    ):
        raise SystemExit("manifest-authorized preflight requires flag, path, and digest")
    if manifest_authority_values[0] and not getattr(args, "deployment_preflight", False):
        raise SystemExit("manifest authority is only valid for deployment preflight")
    manifest_authority = None
    if manifest_authority_values[0]:
        authority_path = manifest_authority_values[1]
        if (
            not authority_path.is_absolute()
            or authority_path.is_symlink()
            or not authority_path.is_file()
            or authority_path.resolve(strict=True) != authority_path
        ):
            raise SystemExit("runtime manifest authority path must be a canonical file")
        try:
            manifest_authority = formal_runtime.load_manifest(
                authority_path,
                str(manifest_authority_values[2]),
            )
        except formal_runtime.RuntimeManifestError as error:
            raise SystemExit(str(error)) from error
    if all(value is not None for value in contract_values):
        preflight = deployment_preflight(
            repo_root,
            queue_root,
            state_root,
            expected_repo_root=contract_values[0],
            expected_queue_root=contract_values[1],
            expected_state_root=contract_values[2],
            expected_runtime_sha=contract_values[3],
            expected_runtime_digest=contract_values[4],
            push=args.push,
            expected_push_mode=contract_values[5],
            max_runs=args.max_runs,
            expected_exact_run_ids=exact_run_ids,
            manifest_authority=manifest_authority,
            expected_manifest_digest=(
                str(manifest_authority_values[2])
                if manifest_authority is not None
                else None
            ),
        )
        if getattr(args, "deployment_preflight", False):
            print(json.dumps(preflight, ensure_ascii=False))
            return 0
    if recovery_run_ids:
        if not args.dry_run and not all(
            value is not None for value in contract_values
        ):
            raise SystemExit(
                "retry recovery requires a complete deployment contract"
            )
        expected_retry_error = str(
            getattr(args, "expected_retry_error", "") or ""
        )
        recovery_reason = str(getattr(args, "recovery_reason", "") or "")
        if not expected_retry_error or not recovery_reason:
            raise SystemExit(
                "retry recovery requires --expected-retry-error "
                "and --recovery-reason"
            )
        expected_recovery_digest = getattr(
            args,
            "expected_recovery_digest",
            None,
        )
        if not args.dry_run and not expected_recovery_digest:
            raise SystemExit(
                "retry recovery requires --expected-recovery-digest "
                "from a current dry-run"
            )
        result = recover_exhausted_create_retries(
            repo_root,
            queue_root,
            state_root,
            run_ids=recovery_run_ids,
            expected_error=expected_retry_error,
            reason=recovery_reason,
            expected_recovery_digest=expected_recovery_digest,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    state_root.mkdir(parents=True, exist_ok=True)
    if fresh_ja_prepare:
        result = prepare_exact_fresh_ja_translation_run(
            repo_root,
            queue_root,
            state_root,
            str(getattr(args, "prepare_exact_fresh_ja_source_run_id")),
            str(getattr(args, "prepare_exact_fresh_ja_article_id")),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if not args.dry_run:
        _validate_formal_runtime(repo_root, queue_root, state_root)
    with _isolated_transaction_worktree(repo_root, state_root) as transaction_root:
        if fresh_ja_run_id is not None:
            result = publish_exact_fresh_ja_translation_run(
                transaction_root,
                queue_root,
                state_root,
                fresh_ja_run_id,
                dry_run=args.dry_run,
                push=args.push,
            )
        else:
            result = publisher_fn(
                transaction_root,
                queue_root,
                state_root,
                max_runs=args.max_runs,
                dry_run=args.dry_run,
                push=args.push,
                run_tests=not args.skip_tests,
                release_gate=not args.skip_release_gate,
                **selector_kwargs,
            )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") in {*SUCCESS_STATUSES, "ok"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

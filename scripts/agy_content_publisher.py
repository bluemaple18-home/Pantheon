#!/usr/bin/env python3
"""發布已通過 Gemini Reviewer 的文章 run。"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
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
import sys
import tempfile
from typing import Any, Callable

from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
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
TEST_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "tests/test_web.py",
    "tests/test_agy_seo_copy_pipeline.py",
    "tests/test_agy_multilingual_pipeline.py",
    "tests/test_release_record.py",
    "-q",
]
PREFLIGHT_TEST_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "tests/test_web.py::test_cloudflare_pages_exact_rewrites_use_prerendered_product_hubs",
    "tests/test_web.py::test_tarot_hub_reading_guide_is_scanable",
    "tests/test_web.py::test_public_articles_follow_latest_publication_standard",
    "-q",
]
SUCCESS_STATUSES = {"PUBLISHED", "PUBLISHED_REWRITE", "PUBLISHED_TRANSLATION", "idle", "idle_rejects_only", "busy", "dry-run"}
RETRY_DELAY_SECONDS = 300
MAX_RETRY_ATTEMPTS = 3


class PublishBlocked(ValueError):
    """發布 gate fail-closed。"""


class PushOutcomeUnknown(PublishBlocked):
    """遠端 atomic push 結果無法安全判定。"""


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


def _repo_lock_path(repo_root: Path, git: GitRunner) -> Path:
    try:
        common_dir = Path(git(repo_root, ["rev-parse", "--git-common-dir"], None))
        if not common_dir.is_absolute():
            common_dir = repo_root / common_dir
    except (OSError, subprocess.CalledProcessError):
        common_dir = repo_root / ".git"
    common_dir.mkdir(parents=True, exist_ok=True)
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


def _retry_eligible(state_root: Path, phase: str, run_id: str) -> bool:
    path = _retry_path(state_root, phase, run_id)
    if not path.is_file():
        return True
    try:
        retry = _read_json(path)
        attempts = int(retry.get("attempts", 0))
        next_eligible = datetime.fromisoformat(str(retry["next_eligible_at"]))
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return False
    return attempts < MAX_RETRY_ATTEMPTS and datetime.now().astimezone() >= next_eligible


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
            },
        )


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
    mismatches: list[str] = []
    for relative in TRANSACTION_RUNTIME_PATHS:
        actor_path = repo_root / relative
        transaction_path = transaction_root / relative
        actor_bytes = actor_path.read_bytes() if actor_path.is_file() else None
        transaction_bytes = transaction_path.read_bytes() if transaction_path.is_file() else None
        if actor_bytes != transaction_bytes:
            mismatches.append(relative)
    if mismatches:
        raise PublishBlocked(
            "publisher actor runtime differs from origin/main; deploy actor before publishing: "
            + ", ".join(mismatches)
        )


@contextmanager
def _isolated_transaction_worktree(
    repo_root: Path,
    state_root: Path,
    git: GitRunner = run_git,
) -> Iterator[Path]:
    """從最新 origin/main 建立單輪隔離 worktree，正式 actor 全程唯讀。"""
    state_root.mkdir(parents=True, exist_ok=True)
    git(repo_root, ["fetch", "origin", "main"], None)
    if not _repo_clean(repo_root, git):
        raise PublishBlocked("publisher actor worktree is not clean")
    remote_sha = git(repo_root, ["rev-parse", "origin/main"], None)
    transaction_parent = Path(tempfile.mkdtemp(prefix="transaction-", dir=state_root))
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
        actor_node_modules = repo_root / "node_modules"
        transaction_node_modules = transaction_root / "node_modules"
        if actor_node_modules.is_dir() and not transaction_node_modules.exists():
            transaction_node_modules.mkdir()
            for dependency in actor_node_modules.iterdir():
                (transaction_node_modules / dependency.name).symlink_to(
                    dependency,
                    target_is_directory=dependency.is_dir(),
                )
        yield transaction_root
    finally:
        if added:
            try:
                git(repo_root, ["worktree", "remove", "--force", str(transaction_root)], None)
            except Exception:
                shutil.rmtree(transaction_root, ignore_errors=True)
                git(repo_root, ["worktree", "prune"], None)
        shutil.rmtree(transaction_parent, ignore_errors=True)


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
                    return function(repo_root, queue_root, state_root, *args, **kwargs)
                except PushOutcomeUnknown:
                    raise
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
            "translation_published_runs": [],
            "translation_deferred_runs": [],
        }
    ledger = _read_json(path)
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise PublishBlocked("publisher ledger schema is invalid")
    ledger.setdefault("published_runs", [])
    ledger.setdefault("quarantined_runs", [])
    ledger.setdefault("rewrite_released_runs", [])
    ledger.setdefault("translation_published_runs", [])
    ledger.setdefault("translation_deferred_runs", [])
    return ledger


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
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    ledger = _load_ledger(state_root)
    published = {str(item.get("run_id")) for item in ledger["published_runs"]}
    quarantined = {str(item.get("run_id")) for item in ledger["quarantined_runs"]}
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    reference_articles = (
        pipeline.load_publication_reference_corpus(repo_root)
        if repo_root is not None
        else None
    )
    for state_path in _fresh_first_run_files(queue_root, state_root, "create"):
        try:
            state, candidate, review = _load_completed_run(state_path)
        except PublishBlocked:
            _record_invalid_candidate_policy_rejection(state_root, "create", state_path)
            continue
        run_id = str(state["run_id"])
        if run_id in published or run_id in quarantined:
            continue
        if not _retry_eligible(state_root, "create", run_id):
            continue
        if candidate.get("mode") == "translate_existing":
            continue
        if candidate.get("mode") != "create":
            _record_quarantine(state_root, state, "publisher only supports create mode")
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
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """只收乾淨通過的單語 run；其餘保留並移入待修清單。"""
    ledger = _load_ledger(state_root)
    published = {str(item.get("run_id")) for item in ledger["translation_published_runs"]}
    deferred = {str(item.get("run_id")) for item in ledger["translation_deferred_runs"]}
    ready: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for state_path in _fresh_first_run_files(queue_root, state_root, "translation"):
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
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
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
    for state_path in _fresh_first_run_files(queue_root, state_root, "rewrite"):
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
        "reject": 0,
        "active_or_incomplete": 0,
        "non_legacy": 0,
        "legacy_total": len(legacy_records) if legacy_records is not None else len(allowed_article_ids),
        "attempted": 0,
        "unattempted": 0,
        "clean_approve_run_ids": [],
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
    end = text.index("]\n\nPUBLIC_ARTICLE_PATHS", start)
    block = text[start:end]
    for path in paths:
        line = f'    "{path}",\n'
        if line not in block:
            block += line
    text = text[:start] + block + text[end:]
    if (repo_root / "app/web/static/articles.js").exists():
        records = _hub_display_records(repo_root)
        category_list = _python_string_list([str(record["category"]) for record in records])
        path_list = _python_string_list([str(record["path"]) for record in records])
        pattern = re.compile(
            r'assert \[record\["category"\] for record in data\["records"\]\] == \[\n.*?\n    \]\n'
            r'    assert \[record\["path"\] for record in data\["records"\]\] == \[\n.*?\n    \]',
            flags=re.DOTALL,
        )
        replacement = (
            'assert [record["category"] for record in data["records"]] == [\n'
            f"{category_list}\n"
            "    ]\n"
            '    assert [record["path"] for record in data["records"]] == [\n'
            f"{path_list}\n"
            "    ]"
        )
        text, replaced = pattern.subn(replacement, text, count=1)
        if replaced != 1:
            raise PublishBlocked("test_web hub display fixture marker not found")
    test_path.write_text(text, encoding="utf-8")
    return test_path


def _sync_web_test_cache_token(repo_root: Path, *, cache_token: str) -> Path:
    pipeline._bump_article_cache_queries(repo_root, cache_token)
    test_path = repo_root / "tests/test_web.py"
    text = test_path.read_text(encoding="utf-8")
    text = re.sub(r'ARTICLE_CACHE_TOKEN = "[^"]+"', f'ARTICLE_CACHE_TOKEN = "{cache_token}"', text, count=1)
    test_path.write_text(text, encoding="utf-8")
    return test_path


def _python_string_list(values: list[str]) -> str:
    return "\n".join(f'        "{value}",' for value in values)


def _hub_display_records(repo_root: Path) -> list[dict[str, str]]:
    script = """
import { getArticlePath, listArticleRecords } from "./app/web/static/article-registry.js";
import { pickLatestArticles } from "./app/web/static/articles.js";
const selected = pickLatestArticles(listArticleRecords());
console.log(JSON.stringify(selected.map((article) => ({
  path: getArticlePath(article),
  category: article.articleCategory,
}))));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=repo_root, check=True, capture_output=True, text=True)
    return list(json.loads(result.stdout))


def _run_prerender(repo_root: Path, *, required_article_ids: list[str] | None = None) -> None:
    command = [sys.executable, "scripts/prerender_article_shells.py"]
    for article_id in required_article_ids or []:
        command.extend(["--required-article-id", article_id])
    _run_checked(repo_root, command)


def _run_feed(repo_root: Path) -> None:
    _run_checked(repo_root, [sys.executable, "scripts/generate_feed.py"])


def _run_checked(repo_root: Path, args: list[str]) -> None:
    subprocess.run(args, cwd=repo_root, check=True)


def _run_release_tests(repo_root: Path) -> None:
    """先跑快速結構檢查，通過後才進完整 release gate。"""
    _run_checked(repo_root, PREFLIGHT_TEST_COMMAND)
    _run_checked(repo_root, TEST_COMMAND)


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
) -> str:
    git(repo_root, ["add", "app/web", "tests/test_web.py", "pyproject.toml", "package.json", "CHANGELOG.md"], None)
    if extra_add_paths:
        git(repo_root, ["add", *extra_add_paths], None)
    git(repo_root, ["commit", "-m", message or f"chore(content): publish Gemini approved articles v{version}"], None)
    git(repo_root, ["tag", "-a", f"v{version}", "-m", f"Pantheon content release v{version}"], None)
    commit_sha = git(repo_root, ["rev-parse", "HEAD"], None)
    if release_gate:
        _run_checked(repo_root, [sys.executable, "scripts/check_release_record.py", "--base-ref", "origin/main", "--require-head-tag"])
    if push:
        try:
            git(repo_root, ["push", "--atomic", "origin", "HEAD:main", f"v{version}"], None)
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


def _assert_rewrite_source_matches(repo_root: Path, candidates: list[dict[str, Any]]) -> None:
    inventory = pipeline._existing_rewrite_inventory(repo_root)
    for candidate in candidates:
        for article in candidate["articles"]:
            article_id = str(article["article_id"])
            current = inventory.get(article_id)
            if current is None:
                raise PublishBlocked(f"rewrite source article no longer exists: {article_id}")
            if article["identity"] != _rewrite_identity_for_inventory_item(current):
                raise PublishBlocked(f"rewrite identity drift for {article_id}")
            actual_hash = pipeline.body_sha256(current["currentBody"])
            approved_hash = pipeline.body_sha256(article["bodySections"])
            if actual_hash not in {str(article["current_body_sha256"]), approved_hash}:
                raise PublishBlocked(f"rewrite body drift for {article_id}")


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
    marker = "return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy("
    start = text.find(marker)
    if start < 0:
        raise PublishBlocked("article registry listArticleRecords policy marker not found")
    argument_start = start + len(marker)
    argument_end = text.find(", getArticleSectionRecord(article.section)));", argument_start)
    if argument_end < 0:
        raise PublishBlocked("article registry listArticleRecords policy argument not found")
    token = f"{export_name}[article.id]"
    current = text[argument_start:argument_end]
    if token in current:
        return
    updated = f"{{ ...({current}), ...({token} || {{}}) }}"
    text = text[:argument_start] + updated + text[argument_end:]
    registry_path.write_text(text, encoding="utf-8")


def apply_rewrite_release(repo_root: Path, release_id: str, candidates: list[dict[str, Any]]) -> list[Path]:
    if not candidates:
        return []
    _assert_rewrite_source_matches(repo_root, candidates)
    reference_articles = pipeline.load_publication_reference_corpus(repo_root)
    for candidate in candidates:
        for article in candidate["articles"]:
            policy_article = {
                **article["identity"],
                "id": article["article_id"],
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
    bodies: dict[str, list[dict[str, Any]]] = {}
    policies: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        for article in candidate["articles"]:
            slug = str(article["identity"]["slug"])
            if slug in bodies:
                raise PublishBlocked(f"duplicate rewrite slug in release batch: {slug}")
            bodies[slug] = article["bodySections"]
            policies[str(article["article_id"])] = {
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
    changed.extend(pipeline._bump_article_cache_queries(repo_root, release_id))
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
) -> dict[str, Any]:
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "published": 0}
        base_sha = _transaction_base_sha or _assert_clean_origin_head(repo_root, git)
        recovered_translation_runs = [] if dry_run else _seed_pending_translations(repo_root, queue_root, state_root)
        ready = collect_ready_runs(
            queue_root,
            state_root,
            limit=max_runs,
            repo_root=repo_root,
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
                required_article_ids=[
                    str(article["id"])
                    for article in approved_articles
                ],
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
        seeded_translation_runs = [
            *recovered_translation_runs,
            *_seed_pending_translations(repo_root, queue_root, state_root),
        ]
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
) -> dict[str, Any]:
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
        release_id = f"agy-rewrite-{date.today().strftime('%Y%m%d')}-{len(run_ids):02d}"
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
                required_article_ids=article_ids,
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
) -> dict[str, Any]:
    """發布所有已通過的單語 run；退件留待最後修復且不阻塞通過者。"""
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "publisher.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"schema_version": SCHEMA_VERSION, "status": "busy", "translated": 0}
        base_sha = _transaction_base_sha or _assert_clean_origin_head(repo_root, git)
        ready = collect_ready_translation_runs(repo_root, queue_root, state_root, limit=max_runs)
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
) -> dict[str, Any]:
    """同一輪先處理新文、舊文，再發布已通過的多語版本。"""
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
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rewrite-release", action="store_true")
    parser.add_argument("--include-rewrites", action="store_true")
    parser.add_argument("--legacy-report", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-release-gate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    if args.legacy_report:
        print(json.dumps(legacy_serial_report(repo_root), ensure_ascii=False))
        return 0
    if args.queue_root is None:
        raise SystemExit("--queue-root is required unless --legacy-report is set")
    if args.rewrite_release and args.include_rewrites:
        raise SystemExit("--rewrite-release and --include-rewrites cannot be used together")
    if args.include_rewrites:
        publisher_fn = publish_ready_all
    elif args.rewrite_release:
        publisher_fn = publish_ready_rewrite_runs
    else:
        publisher_fn = publish_ready_runs
    queue_root = args.queue_root.resolve()
    state_root = (repo_root / args.state_root).resolve() if not args.state_root.is_absolute() else args.state_root.resolve()
    state_root.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        result = publisher_fn(
            repo_root,
            queue_root,
            state_root,
            max_runs=args.max_runs,
            dry_run=True,
            push=args.push,
            run_tests=not args.skip_tests,
            release_gate=not args.skip_release_gate,
        )
    else:
        with _isolated_transaction_worktree(repo_root, state_root) as transaction_root:
            result = publisher_fn(
                transaction_root,
                queue_root,
                state_root,
                max_runs=args.max_runs,
                dry_run=False,
                push=args.push,
                run_tests=not args.skip_tests,
                release_gate=not args.skip_release_gate,
            )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") in {*SUCCESS_STATUSES, "ok"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

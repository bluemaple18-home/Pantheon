#!/usr/bin/env python3
# 👉 [假設與目標確認] 目標：以隔離 staging 錄取既有 pipeline 的 sealed trace；邊界：不寫 runtime queue/state；驗收：R2 bundle 與 evidence 均可重算且 fail-closed。
"""只在 disposable staging 產生 sealed trace bundle，不是 runtime controller。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Literal

from scripts import agy_gemini_outbox as outbox
from scripts import agy_gemini_runner as runner
from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as editorial


LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_GIT = re.compile(r"^[0-9a-f]{40}$")
_RUN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
PREFLIGHT_TIMEOUT_MILLISECONDS = 5_000


class SealedTraceCompilerBlocked(RuntimeError):
    """sealed trace compiler 的穩定 fail-closed boundary。"""


@dataclass(frozen=True)
class SealedResponse:
    role: Literal["writer", "reviewer"]
    model: str
    payload: dict[str, Any]
    executable_path: Path
    executable_sha256: str


@dataclass(frozen=True)
class SealedTraceCompileRequest:
    kind: Literal["editorial", "translation"]
    source_run_dir: Path
    source_tree_digest: str
    staging_root: Path
    evidence_artifact_dir: Path
    accepted_base_sha: str
    actor_sha: str
    actor_root: Path
    generation: str
    lane_queue_root: Path
    lane: str
    run_id: str
    namespace: str
    session_id: str
    responses: tuple[SealedResponse, ...]
    max_repairs: int = 0


def _bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha(value: object) -> str:
    return hashlib.sha256(runner._canonical_json_bytes(value)).hexdigest()


def _path(path: Path, label: str, *, exists: bool = False) -> Path:
    if not path.is_absolute() or path != path.resolve(strict=False):
        raise SealedTraceCompilerBlocked(f"{label} must be canonical absolute")
    if exists and not path.exists():
        raise SealedTraceCompilerBlocked(f"{label} is missing")
    return path


def strict_source_tree_digest(root: Path) -> str:
    """以 owner-only regular-file snapshot 產生可重算的 source tree digest。"""
    root = _path(root, "source run", exists=True)
    if not root.is_dir() or root.is_symlink() or root.stat().st_uid != os.getuid():
        raise SealedTraceCompilerBlocked("source run is not a regular directory")
    rows: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or path.stat().st_uid != os.getuid():
            raise SealedTraceCompilerBlocked("source snapshot contains non-owner or non-regular file")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SealedTraceCompilerBlocked("source snapshot contains non-owner or non-regular file")
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    if not rows:
        raise SealedTraceCompilerBlocked("source snapshot is empty")
    return hashlib.sha256(_bytes(rows)).hexdigest()


def _safe_lane_queue_tree_snapshot(root: Path) -> str:
    """封存 lane queue 的安全樹狀快照，僅接受 owner-owned directory/regular file。"""
    root = _path(root, "lane queue root", exists=True)
    rows: list[tuple[str, str, int, int, int | None, str | None]] = []
    for path in (root, *sorted(root.rglob("*"))):
        relative = "." if path == root else path.relative_to(root).as_posix()
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if path.is_symlink() or metadata.st_uid != os.getuid():
            raise SealedTraceCompilerBlocked("lane queue snapshot is unsafe")
        if stat.S_ISDIR(metadata.st_mode):
            if mode & 0o022:
                raise SealedTraceCompilerBlocked("lane queue snapshot is unsafe")
            rows.append((relative, "directory", metadata.st_uid, mode, None, None))
        elif stat.S_ISREG(metadata.st_mode):
            if mode & 0o022:
                raise SealedTraceCompilerBlocked("lane queue snapshot is unsafe")
            payload = path.read_bytes()
            rows.append((relative, "regular", metadata.st_uid, mode, len(payload), hashlib.sha256(payload).hexdigest()))
        else:
            raise SealedTraceCompilerBlocked("lane queue snapshot is unsafe")
    return hashlib.sha256(_bytes(rows)).hexdigest()


def _git(request: SealedTraceCompileRequest) -> None:
    module_root = Path(__file__).resolve().parents[1]
    actor = _path(request.actor_root, "actor root", exists=True)
    if actor != module_root or not _GIT.fullmatch(request.actor_sha) or not _GIT.fullmatch(request.accepted_base_sha):
        raise SealedTraceCompilerBlocked("actor authority is invalid")
    try:
        head = subprocess.run(["git", "-C", str(actor), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        clean = subprocess.run(["git", "-C", str(actor), "status", "--porcelain=v1", "--untracked-files=all"], check=True, capture_output=True, text=True).stdout
        subprocess.run(["git", "-C", str(actor), "merge-base", "--is-ancestor", request.accepted_base_sha, request.actor_sha], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SealedTraceCompilerBlocked("actor git authority is invalid") from error
    if head != request.actor_sha or clean:
        raise SealedTraceCompilerBlocked("actor head or worktree is dirty")


class RecordingSealedClient:
    """把 sealed payload 回傳給原 pipeline，並錄取其實際 request。"""
    def __init__(self, responses: Sequence[SealedResponse], namespace: str) -> None:
        self.responses = tuple(responses)
        self.namespace = namespace
        self.index = 0
        self.records: list[tuple[dict[str, Any], SealedResponse]] = []
        writers = [item.model for item in self.responses if item.role == "writer"]
        reviewers = [item.model for item in self.responses if item.role == "reviewer"]
        if not writers:
            raise SealedTraceCompilerBlocked("sealed trace requires writer payload")
        self.writer_model = writers[0]
        self.reviewer_model = reviewers[0] if reviewers else "sealed-reviewer-unavailable"

    def generate_json(self, role: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if self.index >= len(self.responses):
            raise SealedTraceCompilerBlocked("sealed response payloads are exhausted")
        response = self.responses[self.index]
        self.index += 1
        expected_model = self.writer_model if role == "writer" else self.reviewer_model
        if response.role != role or response.model != expected_model:
            raise SealedTraceCompilerBlocked("sealed response role or model drift")
        request = outbox.build_external_request(namespace=self.namespace, role=role, model=expected_model, prompt=prompt, response_schema=schema)
        self.records.append((request, response))
        return response.payload

    def assert_consumed(self) -> None:
        if self.index != len(self.responses):
            raise SealedTraceCompilerBlocked("sealed response payloads remain unused")


def _write_all(descriptor: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        written = os.write(descriptor, value[offset:])
        if written <= 0:
            raise OSError("evidence write did not advance")
        offset += written


def _publish_artifact(path: Path, bundle: bytes, receipt: bytes) -> None:
    """先 fsync 完整 artifact dir，再以單一 rename 發布，拒絕半份 evidence。"""
    if path.exists() or not path.parent.is_dir():
        raise SealedTraceCompilerBlocked("evidence destination already exists or parent is missing")
    parent_mode = path.parent.stat().st_mode
    if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid() or parent_mode & 0o077:
        raise SealedTraceCompilerBlocked("evidence parent permission is unsafe")
    claim = path.parent / f".{path.name}.claim"
    claim_fd = -1
    temporary = Path(tempfile.mkdtemp(dir=path.parent, prefix=f".{path.name}."))
    published = False
    try:
        claim_fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.fsync(claim_fd)
        os.chmod(temporary, 0o700)
        for name, value in (("bundle.json", bundle), ("compile-receipt.json", receipt)):
            target = temporary / name
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                _write_all(descriptor, value)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        directory_fd = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if path.exists() or claim_fd < 0:
            raise FileExistsError(path)
        os.rename(temporary, path)
        published = True
        parent_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except FileExistsError as error:
        raise SealedTraceCompilerBlocked("evidence destination race") from error
    except Exception:
        if published:
            quarantine_root = Path(tempfile.mkdtemp(dir=path.parent, prefix=f".{path.name}.failed-"))
            os.chmod(quarantine_root, 0o700)
            try:
                os.rename(path, quarantine_root / path.name)
            except OSError:
                raise SealedTraceCompilerBlocked("published artifact cannot be quarantined")
            try:
                shutil.rmtree(quarantine_root)
            except OSError:
                pass
            cleanup_fd = -1
            try:
                cleanup_fd = os.open(path.parent, os.O_RDONLY)
                os.fsync(cleanup_fd)
            except OSError:
                pass
            finally:
                if cleanup_fd >= 0:
                    os.close(cleanup_fd)
        raise
    finally:
        if claim_fd >= 0:
            os.close(claim_fd)
            claim.unlink(missing_ok=True)
        if temporary.exists():
            shutil.rmtree(temporary)


def _preflight_sealed_executable_records(
    stage: Path,
    records: Sequence[tuple[dict[str, Any], SealedResponse]],
) -> None:
    """以 Runner 同一 RAW_STDIN broker contract 實際綁定每筆 sealed result。"""
    evidence = stage / "sealed-executable-preflight"
    for ordinal, (external, response) in enumerate(records, 1):
        operation_id = hashlib.sha256(
            _bytes(
                {
                    "request": external["request_sha256"],
                    "result": _sha(response.payload),
                    "ordinal": ordinal,
                }
            )
        ).hexdigest()[:40]
        item_id = hashlib.sha256(
            _bytes({"job_id": external["job_id"], "ordinal": ordinal})
        ).hexdigest()[:24]
        attempt_id = f"trace-{ordinal:02d}"
        try:
            result = runner.run_single_shot(
                operation_id=operation_id,
                item_id=item_id,
                attempt_id=attempt_id,
                request_sha256=external["request_sha256"],
                model=external["model"],
                executable=response.executable_path,
                target_profile=runner.RAW_STDIN_PROFILE,
                expected_executable_digest=response.executable_sha256,
                raw_request=runner._render_v4_effective_prompt(
                    external["role"], external["prompt"], external["response_schema"]
                ),
                response_schema=external["response_schema"],
                timeout_milliseconds=PREFLIGHT_TIMEOUT_MILLISECONDS,
                ledger_path=evidence / "ledger" / f"{operation_id}.jsonl",
                anchor_store=runner.FileAnchorStore(evidence / "anchors"),
                result_normalizer=runner.normalize_new_output_contract,
            )
        except (OSError, ValueError) as error:
            raise SealedTraceCompilerBlocked("sealed executable preflight is invalid") from error
        if (
            result.replay_status != "COMPLETE"
            or result.process_count != 1
            or not result.caller_contract_satisfied
            or result.errors
            or result.result is None
            or result.result != response.payload
            or _sha(result.result) != _sha(response.payload)
        ):
            raise SealedTraceCompilerBlocked("sealed executable result binding failed")


def compile_sealed_trace(request: SealedTraceCompileRequest) -> dict[str, Any]:
    """重用既有 Writer/Reviewer loop，僅輸出 lane-local R2 evidence。"""
    if request.kind not in {"editorial", "translation"} or request.lane not in LANES or not _RUN.fullmatch(request.run_id) or not _TOKEN.fullmatch(request.session_id) or not _TOKEN.fullmatch(request.generation) or type(request.max_repairs) is not int or not 0 <= request.max_repairs <= 2:
        raise SealedTraceCompilerBlocked("sealed trace identity is invalid")
    if request.kind == "editorial" and request.lane not in {"new", "rewrite"} or request.kind == "translation" and request.lane not in {"i18n-new", "i18n-rewrite"}:
        raise SealedTraceCompilerBlocked("sealed trace kind/lane pairing is invalid")
    if request.namespace != hashlib.sha256(request.run_id.encode()).hexdigest()[:24] or not 1 <= len(request.responses) <= 16 or not _SHA.fullmatch(request.source_tree_digest):
        raise SealedTraceCompilerBlocked("sealed trace namespace or response count is invalid")
    source = _path(request.source_run_dir, "source run", exists=True)
    stage_root = _path(request.staging_root, "staging root")
    evidence = _path(request.evidence_artifact_dir, "evidence artifact")
    queue = _path(request.lane_queue_root, "lane queue root")
    if not queue.is_dir() or queue.is_symlink() or queue.stat().st_uid != os.getuid():
        raise SealedTraceCompilerBlocked("lane queue root is unsafe")
    protected_roots = (source, queue, request.actor_root)
    if evidence.parent != stage_root or evidence.exists() or any(left == right or left.is_relative_to(right) or right.is_relative_to(left) for index, left in enumerate(protected_roots) for right in protected_roots[index + 1:]) or any(root.is_relative_to(stage_root) or stage_root.is_relative_to(root) for root in (source, queue, request.actor_root)):
        raise SealedTraceCompilerBlocked("sealed trace roots overlap")
    for root, label in ((stage_root, "staging"), (evidence.parent, "evidence parent")):
        mode = root.stat().st_mode if root.exists() else 0
        if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid() or mode & 0o077 or mode & 0o700 != 0o700:
            raise SealedTraceCompilerBlocked(f"{label} root permission is unsafe")
    if any((source / item).exists() for item in ("candidate.json", "review.json", "attempts")):
        raise SealedTraceCompilerBlocked("source contains resumable artifacts")
    _git(request)
    if strict_source_tree_digest(source) != request.source_tree_digest:
        raise SealedTraceCompilerBlocked("source tree digest drift before trace")
    queue_snapshot = _safe_lane_queue_tree_snapshot(queue)
    for response in request.responses:
        executable = _path(response.executable_path, "sealed executable", exists=True)
        if response.role not in {"writer", "reviewer"} or not response.model or not _SHA.fullmatch(response.executable_sha256) or executable.is_symlink() or not executable.is_file() or executable.stat().st_uid != os.getuid() or executable.stat().st_mode & 0o022 or not os.access(executable, os.X_OK) or hashlib.sha256(executable.read_bytes()).hexdigest() != response.executable_sha256:
            raise SealedTraceCompilerBlocked("sealed response is invalid")
    stage = stage_root / f"trace-{request.run_id}"
    if stage.exists() or evidence.exists():
        raise SealedTraceCompilerBlocked("staging or evidence destination exists")
    if not stage_root.is_dir():
        raise SealedTraceCompilerBlocked("staging root is missing")
    shutil.copytree(source, stage, symlinks=False)
    if strict_source_tree_digest(stage) != request.source_tree_digest:
        raise SealedTraceCompilerBlocked("staging snapshot drift before pipeline")
    client = RecordingSealedClient(request.responses, request.namespace)
    if request.kind == "editorial":
        editorial.run_writer_reviewer(stage, client, max_repairs=request.max_repairs)
    else:
        multilingual.run_writer_reviewer(stage, client, max_repairs=request.max_repairs)
    client.assert_consumed()
    if strict_source_tree_digest(source) != request.source_tree_digest:
        raise SealedTraceCompilerBlocked("source tree digest drift after trace")
    _preflight_sealed_executable_records(stage, client.records)
    _git(request)
    if strict_source_tree_digest(source) != request.source_tree_digest:
        raise SealedTraceCompilerBlocked("source tree digest drift after preflight")
    if _safe_lane_queue_tree_snapshot(queue) != queue_snapshot:
        raise SealedTraceCompilerBlocked("lane queue tree drift after preflight")
    entries = [{"session_id": request.session_id, "entry_id": f"entry-{index:02d}", "job_id": external["job_id"], "request_sha256": external["request_sha256"], "namespace": request.namespace, "lane": request.lane, "run_id": request.run_id, "role": external["role"], "model": external["model"], "schema_sha256": external["schema_sha256"], "sealed_result_sha256": _sha(response.payload), "executable_path": str(response.executable_path), "executable_sha256": response.executable_sha256, "required": True} for index, (external, response) in enumerate(client.records, 1)]
    body = {"schema_version": 1, "mode": runner.ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE, "session_id": request.session_id, "accepted_base_sha": request.accepted_base_sha, "actor_sha": request.actor_sha, "generation": request.generation, "queue_root": str(queue), "lane": request.lane, "run_id": request.run_id, "namespace": request.namespace, "provider_call_budget": len(entries), "entries": entries}
    bundle = {**body, "bundle_digest": _sha(body)}
    raw = _bytes(bundle)
    receipt = {
        "schema_version": 1,
        "status": "SEALED_TRACE_COMPILED",
        "source_tree_digest": request.source_tree_digest,
        "raw_bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "bundle_path": str(evidence / "bundle.json"),
        "preflight_evidence_dir": str(stage / "sealed-executable-preflight"),
        "preflight_entry_count": len(entries),
    }
    _publish_artifact(evidence, raw, _bytes(receipt))
    return {**receipt, "bundle": bundle, "entries": len(entries), "runtime_queue_written": False}

#!/usr/bin/env python3
# 👉 [假設與目標確認] 目標：在 disposable staging 走既有 Writer/Reviewer，編譯 lane-local sealed bundle；邊界：不改任何 runtime owner 且不寫 runtime queue/state；驗收：trace 與 R2 loader 完整對齊。
"""Slice C-A：將既有 pipeline trace 編譯為 immutable lane-local sealed bundle。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Literal

from scripts import agy_gemini_outbox as outbox
from scripts import agy_gemini_runner as runner
from scripts import agy_multilingual_pipeline as multilingual
from scripts import agy_seo_copy_pipeline as editorial


CONTENT_LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
MAX_BUNDLE_ENTRIES = 16
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_GENERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TraceCompilerBlocked(RuntimeError):
    """C-A immutable trace contract 不成立時的封閉錯誤。"""


@dataclass(frozen=True)
class SealedResponse:
    role: Literal["writer", "reviewer"]
    model: str
    payload: dict[str, Any]
    executable_path: Path
    executable_sha256: str
    required: bool = True


@dataclass(frozen=True)
class TraceCompileRequest:
    kind: Literal["editorial", "translation"]
    source_run_dir: Path
    staging_root: Path
    evidence_bundle_path: Path
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


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(runner._canonical_json_bytes(payload)).hexdigest()


def _canonical_path(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise TraceCompilerBlocked(f"{label} must be absolute")
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise TraceCompilerBlocked(f"{label} is invalid") from error
    if resolved != path:
        raise TraceCompilerBlocked(f"{label} must be canonical")
    return resolved


def _require(value: object, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise TraceCompilerBlocked(f"{label} is invalid")
    return value


def _namespace_for_run(run_id: str) -> str:
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]


def _validate_request(request: TraceCompileRequest) -> tuple[Path, Path, Path]:
    _require(request.accepted_base_sha, _GIT_SHA, "accepted base sha")
    _require(request.actor_sha, _GIT_SHA, "actor sha")
    _require(request.run_id, _RUN_ID, "run id")
    _require(request.session_id, _TOKEN, "session id")
    if request.kind not in {"editorial", "translation"}:
        raise TraceCompilerBlocked("trace compiler kind is invalid")
    if request.lane not in CONTENT_LANES or _GENERATION.fullmatch(request.generation) is None:
        raise TraceCompilerBlocked("lane or generation is invalid")
    if request.kind == "editorial" and request.lane not in {"new", "rewrite"}:
        raise TraceCompilerBlocked("editorial trace lane is invalid")
    if request.kind == "translation" and request.lane not in {"i18n-new", "i18n-rewrite"}:
        raise TraceCompilerBlocked("translation trace lane is invalid")
    if request.namespace != _namespace_for_run(request.run_id):
        raise TraceCompilerBlocked("namespace must be exact run namespace")
    if not 1 <= len(request.responses) <= MAX_BUNDLE_ENTRIES:
        raise TraceCompilerBlocked("sealed response count is outside R2 bound")
    source = _canonical_path(request.source_run_dir, "source run dir")
    staging_root = _canonical_path(request.staging_root, "staging root")
    evidence = _canonical_path(request.evidence_bundle_path, "evidence bundle path")
    queue = _canonical_path(request.lane_queue_root, "lane queue root")
    actor_root = _canonical_path(request.actor_root, "actor root")
    if not source.is_dir() or not (source / "brief.json").is_file():
        raise TraceCompilerBlocked("source run must contain brief.json")
    if source.is_relative_to(queue) or staging_root.is_relative_to(queue) or evidence.is_relative_to(queue):
        raise TraceCompilerBlocked("compiler paths must not be inside runtime queue")
    if evidence.parent != staging_root:
        raise TraceCompilerBlocked("evidence bundle must be an explicit staging-root child")
    if source.is_relative_to(staging_root) or staging_root.is_relative_to(source) or actor_root.is_relative_to(queue) or queue.is_relative_to(actor_root):
        raise TraceCompilerBlocked("source, staging, actor, and queue roots must not overlap")
    if any((source / name).exists() for name in ("candidate.json", "review.json", "attempts")):
        raise TraceCompilerBlocked("source run must not contain resumable result artifacts")
    try:
        actual_actor = subprocess.run(
            ["git", "-C", str(actor_root), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(actor_root), "merge-base", "--is-ancestor", request.accepted_base_sha, request.actor_sha],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise TraceCompilerBlocked("actor root git authority is invalid") from error
    if actual_actor != request.actor_sha:
        raise TraceCompilerBlocked("actor head differs from actor sha")
    for response in request.responses:
        if response.role not in {"writer", "reviewer"} or not response.model:
            raise TraceCompilerBlocked("sealed response role or model is invalid")
        _require(response.executable_sha256, _SHA256, "sealed executable sha")
        executable = _canonical_path(response.executable_path, "sealed executable path")
        if executable.is_symlink() or not executable.is_file():
            raise TraceCompilerBlocked("sealed executable is unavailable")
        if hashlib.sha256(executable.read_bytes()).hexdigest() != response.executable_sha256:
            raise TraceCompilerBlocked("sealed executable digest mismatch")
    return source, staging_root, evidence


class RecordingSealedClient:
    """以 caller sealed payload 回放 production flow，並精確記錄其 external request identity。"""

    def __init__(self, responses: Sequence[SealedResponse]) -> None:
        self._responses = tuple(responses)
        self._index = 0
        self.records: list[tuple[dict[str, Any], SealedResponse]] = []
        try:
            self.writer_model = next(item.model for item in self._responses if item.role == "writer")
        except StopIteration as error:
            raise TraceCompilerBlocked("sealed responses must include writer") from error
        self.reviewer_model = next(
            (item.model for item in self._responses if item.role == "reviewer"),
            "sealed-reviewer-unavailable",
        )

    def generate_json(self, role: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if self._index >= len(self._responses):
            raise TraceCompilerBlocked("sealed response payloads are exhausted")
        response = self._responses[self._index]
        self._index += 1
        if response.role != role:
            raise TraceCompilerBlocked("sealed response role order drift")
        selected_model = self.writer_model if role == "writer" else self.reviewer_model
        if response.model != selected_model:
            raise TraceCompilerBlocked("sealed response model drift")
        request = outbox.build_external_request(
            namespace=self._namespace,
            role=role,
            model=selected_model,
            prompt=prompt,
            response_schema=schema,
        )
        self.records.append((request, response))
        return response.payload

    def bind_namespace(self, namespace: str) -> None:
        self._namespace = namespace

    def assert_consumed(self) -> None:
        if self._index != len(self._responses):
            raise TraceCompilerBlocked("sealed response payloads remain unused")


def compile_lane_trace(request: TraceCompileRequest) -> dict[str, Any]:
    """僅在 staging copy 執行既有 production loop，輸出不可變 sealed bundle。"""
    source, staging_root, evidence = _validate_request(request)
    stage = staging_root / f"trace-{request.run_id}"
    if stage.exists() or evidence.exists():
        raise TraceCompilerBlocked("staging trace or evidence bundle already exists")
    stage.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, stage)
    client = RecordingSealedClient(request.responses)
    client.bind_namespace(request.namespace)
    try:
        if request.kind == "editorial":
            editorial.run_writer_reviewer(stage, client, max_repairs=request.max_repairs)
        else:
            multilingual.run_writer_reviewer(stage, client, max_repairs=request.max_repairs)
        client.assert_consumed()
    except Exception:
        # 失敗 staging 供 audit 保留；不得 fallback 或觸及 runtime root。
        raise
    entries = []
    for index, (external_request, response) in enumerate(client.records, start=1):
        entries.append(
            {
                "session_id": request.session_id,
                "entry_id": f"entry-{index:02d}",
                "job_id": external_request["job_id"],
                "request_sha256": external_request["request_sha256"],
                "namespace": request.namespace,
                "lane": request.lane,
                "run_id": request.run_id,
                "role": external_request["role"],
                "model": external_request["model"],
                "schema_sha256": external_request["schema_sha256"],
                "sealed_result_sha256": _digest(response.payload),
                "executable_path": str(response.executable_path),
                "executable_sha256": response.executable_sha256,
                "required": response.required,
            }
        )
    bundle_body = {
        "schema_version": 1,
        "mode": "acceptance_sealed_replay_bundle_v1",
        "session_id": request.session_id,
        "accepted_base_sha": request.accepted_base_sha,
        "actor_sha": request.actor_sha,
        "generation": request.generation,
        "queue_root": str(request.lane_queue_root),
        "lane": request.lane,
        "run_id": request.run_id,
        "namespace": request.namespace,
        "provider_call_budget": sum(1 for item in entries if item["required"]),
        "entries": entries,
    }
    bundle = {**bundle_body, "bundle_digest": _digest(bundle_body)}
    evidence.write_bytes(_canonical_json(bundle))
    return {
        "status": "C_A_TRACE_COMPILED",
        "staging_run_dir": str(stage),
        "bundle_path": str(evidence),
        "expected_bundle_digest": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        "bundle": bundle,
        "trace_entries": len(entries),
        "runtime_queue_written": False,
        "runtime_must_validate": {
            "executable_sha256": True,
            "sealed_result_sha256": True,
            "request_schema_role_model": True,
        },
    }

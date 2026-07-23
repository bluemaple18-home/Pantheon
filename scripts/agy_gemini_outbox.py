#!/usr/bin/env python3
"""以純公開 payload 串接 Pantheon pipeline 與外部 Gemini runner。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA_VERSION = 1
OUTBOX_MAX_REPAIRS = 2
OUTBOX_MAX_TRANSPORT_RETRIES = 2
RETRYABLE_EXTERNAL_ERRORS = {"JSONDecodeError"}
MAX_PROMPT_BYTES = 256 * 1024
MAX_SCHEMA_BYTES = 64 * 1024
NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
FORBIDDEN_EXTERNAL_PATTERNS = (
    re.compile(r"/(?:Users|home|private|var|tmp)/"),
    re.compile(r"\.work/"),
    re.compile(r"GEMINI_API_KEY", re.IGNORECASE),
    re.compile(r"x-goog-api-key", re.IGNORECASE),
    re.compile(r"authorization\s*:\s*bearer", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?:ghp|github_pat)_[0-9A-Za-z_]{20,}"),
)


class ExternalJobPending(RuntimeError):
    """外部 runner 尚未回傳此 job。"""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"external job pending: {job_id}")


class ExternalJobFailed(RuntimeError):
    """外部 runner 已記錄失敗。"""

    def __init__(self, job_id: str, error_type: str) -> None:
        self.job_id = job_id
        self.error_type = error_type
        super().__init__(f"external job failed: {job_id} ({error_type})")


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_write_json(path: Path, payload: object) -> None:
    """同目錄暫存後原子替換，避免 runner 讀到半份 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(_json_bytes(payload) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def _assert_external_payload_is_public(prompt: str, response_schema: dict[str, Any]) -> None:
    prompt_bytes = prompt.encode("utf-8")
    schema_bytes = _json_bytes(response_schema)
    if len(prompt_bytes) > MAX_PROMPT_BYTES:
        raise ValueError("external prompt exceeds 256 KB")
    if len(schema_bytes) > MAX_SCHEMA_BYTES:
        raise ValueError("external schema exceeds 64 KB")
    serialized = prompt + "\n" + schema_bytes.decode("utf-8")
    if any(pattern.search(serialized) for pattern in FORBIDDEN_EXTERNAL_PATTERNS):
        raise ValueError("external payload contains forbidden private data")


def _request_core(
    *,
    namespace: str,
    role: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    if not NAMESPACE_PATTERN.fullmatch(namespace):
        raise ValueError("namespace must be opaque and path-free")
    if role not in {"writer", "reviewer"}:
        raise ValueError("role must be writer or reviewer")
    if not model.strip():
        raise ValueError("model must be non-empty")
    _assert_external_payload_is_public(prompt, response_schema)
    return {
        "schema_version": SCHEMA_VERSION,
        "namespace": namespace,
        "role": role,
        "model": model,
        "thinking_level": "LOW",
        "operation_level": "external_generation",
        "prompt": prompt,
        "response_schema": response_schema,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(_json_bytes(response_schema)).hexdigest(),
    }


def build_external_request(
    *,
    namespace: str,
    role: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    core = _request_core(
        namespace=namespace,
        role=role,
        model=model,
        prompt=prompt,
        response_schema=response_schema,
    )
    request_sha256 = hashlib.sha256(_json_bytes(core)).hexdigest()
    return {**core, "job_id": request_sha256[:40], "request_sha256": request_sha256}


def validate_external_request(request: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "namespace",
        "role",
        "model",
        "thinking_level",
        "operation_level",
        "prompt",
        "response_schema",
        "prompt_sha256",
        "schema_sha256",
        "job_id",
        "request_sha256",
    }
    if set(request) != required:
        raise ValueError("external request fields are strict")
    rebuilt = build_external_request(
        namespace=str(request["namespace"]),
        role=str(request["role"]),
        model=str(request["model"]),
        prompt=str(request["prompt"]),
        response_schema=request["response_schema"],
    )
    if request != rebuilt:
        raise ValueError("external request hash mismatch")


def create_external_request(
    queue_root: Path,
    *,
    namespace: str,
    role: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    request = build_external_request(
        namespace=namespace,
        role=role,
        model=model,
        prompt=prompt,
        response_schema=response_schema,
    )
    job_id = request["job_id"]
    known_paths = [
        queue_root / "outbox" / f"{job_id}.json",
        queue_root / "processing" / f"{job_id}.json",
        queue_root / "archive" / f"{job_id}.json",
    ]
    for path in known_paths:
        if not path.exists():
            continue
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != request:
            raise ValueError(f"external job collision: {job_id}")
        return request
    atomic_write_json(known_paths[0], request)
    return request


def consume_external_response(queue_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    validate_external_request(request)
    job_id = str(request["job_id"])
    failed_path = queue_root / "failed" / f"{job_id}.json"
    if failed_path.exists():
        failure = json.loads(failed_path.read_text(encoding="utf-8"))
        raise ExternalJobFailed(job_id, str(failure.get("error_type", "unknown")))
    response_path = queue_root / "inbox" / f"{job_id}.json"
    if not response_path.exists():
        raise ExternalJobPending(job_id)
    response = json.loads(response_path.read_text(encoding="utf-8"))
    required = {"schema_version", "job_id", "request_sha256", "model", "completed_at", "result"}
    if set(response) != required or response.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("external response fields are strict")
    if response["job_id"] != job_id:
        raise ValueError("response job id mismatch")
    if response["request_sha256"] != request["request_sha256"]:
        raise ValueError("response request hash mismatch")
    if response["model"] != request["model"]:
        raise ValueError("response model mismatch")
    return response["result"]


class OutboxGeminiClient:
    """只寫 sanitized request；不持有憑證，也不直接呼叫外部服務。"""

    def __init__(
        self,
        queue_root: Path,
        *,
        namespace: str,
        writer_model: str = pipeline.DEFAULT_WRITER_MODEL,
        reviewer_model: str = pipeline.DEFAULT_REVIEWER_MODEL,
    ) -> None:
        self.queue_root = queue_root
        self.namespace = namespace
        self.writer_model = writer_model
        self.reviewer_model = reviewer_model
        self.transport = self._outbox_transport

    def _outbox_transport(self) -> None:
        raise RuntimeError("outbox transport is represented by generate_json")

    def generate_json(self, role: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        model = self.writer_model if role == "writer" else self.reviewer_model
        for retry_index in range(OUTBOX_MAX_TRANSPORT_RETRIES + 1):
            namespace = self.namespace if retry_index == 0 else f"{self.namespace}-r{retry_index}"
            request = create_external_request(
                self.queue_root,
                namespace=namespace,
                role=role,
                model=model,
                prompt=prompt,
                response_schema=schema,
            )
            try:
                return consume_external_response(self.queue_root, request)
            except ExternalJobFailed as failed:
                if failed.error_type not in RETRYABLE_EXTERNAL_ERRORS or retry_index >= OUTBOX_MAX_TRANSPORT_RETRIES:
                    raise
        raise RuntimeError("unreachable external transport retry state")


def run_pipeline_tick(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    run_id = str(brief["run_id"])
    namespace = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    client = OutboxGeminiClient(queue_root, namespace=namespace)
    candidate, review = pipeline.run_writer_reviewer(run_dir, client, max_repairs=OUTBOX_MAX_REPAIRS)
    return {
        "status": "complete",
        "run_id": run_id,
        "approved_by_reviewer": sum(item["verdict"] == "APPROVE" for item in review["articles"]),
        "candidate": str(run_dir / "candidate.json"),
        "review": str(run_dir / "review.md"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    tick = subparsers.add_parser("tick")
    tick.add_argument("run_dir", type=Path)
    tick.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_pipeline_tick(args.run_dir.resolve(), args.queue_root.resolve())
    except ExternalJobPending as pending:
        print(json.dumps({"status": "pending", "job_id": pending.job_id}, ensure_ascii=False))
        return 75
    except ExternalJobFailed as failed:
        print(json.dumps({"status": "failed", "job_id": failed.job_id, "error_type": failed.error_type}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""處理 sanitized Gemini outbox；本腳本由使用者自行啟用的 runner 執行。"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from scripts.agy_gemini_outbox import (
    SCHEMA_VERSION,
    atomic_write_json,
    validate_external_request,
)
from scripts.agy_seo_copy_pipeline import GeminiClient


GenerateJson = Callable[[str, str, str, dict[str, Any]], dict[str, Any]]


def _cli_generate_json(role: str, model: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    client = GeminiClient(writer_model=model if role == "writer" else None, reviewer_model=model if role == "reviewer" else None)
    client.transport = client._cli_transport
    return client.generate_json(role, prompt, schema)


def _claim_next(queue_root: Path) -> Path | None:
    outbox = queue_root / "outbox"
    processing = queue_root / "processing"
    processing.mkdir(parents=True, exist_ok=True)
    for source in sorted(outbox.glob("*.json")) if outbox.exists() else []:
        target = processing / source.name
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue
        return target
    return None


def process_once(queue_root: Path, *, generate_json: GenerateJson = _cli_generate_json) -> dict[str, str]:
    claimed = _claim_next(queue_root)
    if claimed is None:
        return {"status": "idle"}
    processing_path = claimed
    job_id = processing_path.stem
    archive_path = queue_root / "archive" / f"{job_id}.json"
    request: dict[str, Any] = {}
    try:
        request = json.loads(processing_path.read_text(encoding="utf-8"))
        validate_external_request(request)
        if request["job_id"] != job_id:
            raise ValueError("request job id differs from queue filename")
        result = generate_json(
            str(request["role"]),
            str(request["model"]),
            str(request["prompt"]),
            request["response_schema"],
        )
        atomic_write_json(
            queue_root / "inbox" / f"{job_id}.json",
            {
                "schema_version": SCHEMA_VERSION,
                "job_id": job_id,
                "request_sha256": request["request_sha256"],
                "model": request["model"],
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "result": result,
            },
        )
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        return {"status": "processed", "job_id": job_id}
    except Exception as error:
        atomic_write_json(
            queue_root / "failed" / f"{job_id}.json",
            {
                "schema_version": SCHEMA_VERSION,
                "job_id": job_id,
                "request_sha256": request.get("request_sha256"),
                "error_type": type(error).__name__,
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
        )
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(processing_path, archive_path)
        return {"status": "failed", "job_id": job_id, "error_type": type(error).__name__}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("process-once")
    drain = subparsers.add_parser("drain")
    drain.add_argument("--max-jobs", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue_root = args.queue_root.resolve()
    if args.command == "process-once":
        result = process_once(queue_root)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result["status"] == "failed" else 0
    results = []
    for _ in range(args.max_jobs):
        result = process_once(queue_root)
        results.append(result)
        if result["status"] in {"idle", "failed"}:
            break
    print(json.dumps({"results": results}, ensure_ascii=False))
    return 1 if any(item["status"] == "failed" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

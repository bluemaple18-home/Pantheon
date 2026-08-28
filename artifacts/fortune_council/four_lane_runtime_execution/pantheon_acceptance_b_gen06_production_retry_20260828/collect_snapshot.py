#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path("/Users/mattkuo/Documents/Pantheon")
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
QUEUE = RUNTIME / "queue"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
REGISTRY = QUEUE / "runs/f46cda9eaa9ded446bf8e6c6.json"
RUN_DIR = QUEUE / "translation-runs" / RUN_ID
GEN06 = RUN_DIR / "generations/06"
GEN07 = RUN_DIR / "generations/07"
LANE = QUEUE / "lanes/i18n-new"
JOB_ID = "735ffd07d47e4b25d49f85f137d9dd238d8e9967"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> object | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(args: list[str], cwd: Path) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def file_record(path: Path) -> dict[str, object]:
    record: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }
    if path.is_file():
        record["bytes"] = path.stat().st_size
        record["sha256"] = sha256(path)
    return record


def tree_records(root: Path) -> list[dict[str, object]]:
    if not root.exists():
        return []
    records: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        records.append(
            {
                "relative_path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return records


def lane_job_records() -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for child, suffix in {
        "outbox": ".json",
        "processing": ".json",
        "inbox": ".json",
        "archive": ".json",
        "failed": ".json",
        "production-attempts": ".attempt",
    }.items():
        records[child] = file_record(LANE / child / f"{JOB_ID}{suffix}")
    records["outbox_terminalizing"] = file_record(LANE / "outbox" / f"{JOB_ID}.json.terminalizing")
    return records


def lane_inventory() -> dict[str, object]:
    inventory: dict[str, object] = {}
    for child in ("outbox", "processing", "inbox", "archive", "failed", "production-attempts"):
        root = LANE / child
        if not root.exists():
            inventory[child] = []
            continue
        inventory[child] = sorted(path.name for path in root.iterdir() if path.is_file())
    return inventory


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: collect_snapshot.py LABEL OUTPUT", file=sys.stderr)
        return 64
    label = sys.argv[1]
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)

    registry = load_json(REGISTRY)
    manifest = load_json(RUNTIME / "runtime-manifest.json")
    outbox_request = load_json(LANE / "outbox" / f"{JOB_ID}.json")
    inbox_response = load_json(LANE / "inbox" / f"{JOB_ID}.json")
    archive_request = load_json(LANE / "archive" / f"{JOB_ID}.json")
    attempt = load_json(LANE / "production-attempts" / f"{JOB_ID}.attempt")

    payload = {
        "label": label,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repo_head": git_output(["rev-parse", "HEAD"], REPO),
        "repo_status_porcelain": git_output(["status", "--porcelain=v1"], REPO),
        "actor_head": git_output(["rev-parse", "HEAD"], RUNTIME / "actor"),
        "actor_status_porcelain": git_output(["status", "--porcelain=v1"], RUNTIME / "actor"),
        "manifest": {
            "path": str(RUNTIME / "runtime-manifest.json"),
            "sha256": sha256(RUNTIME / "runtime-manifest.json"),
            "actor_head": manifest.get("actor_head") if isinstance(manifest, dict) else None,
            "manifest_digest": manifest.get("manifest_digest") if isinstance(manifest, dict) else None,
            "identity": manifest.get("identity") if isinstance(manifest, dict) else None,
            "generation": manifest.get("generation") if isinstance(manifest, dict) else None,
        },
        "registry": {
            "file": file_record(REGISTRY),
            "status": registry.get("status") if isinstance(registry, dict) else None,
            "lane": registry.get("lane") if isinstance(registry, dict) else None,
            "last_job_id": registry.get("last_job_id") if isinstance(registry, dict) else None,
            "error_type": registry.get("error_type") if isinstance(registry, dict) else None,
            "result_status": (
                registry.get("result", {}).get("status")
                if isinstance(registry, dict) and isinstance(registry.get("result"), dict)
                else None
            ),
        },
        "gen06": {
            "root": str(GEN06),
            "exists": GEN06.exists(),
            "files": tree_records(GEN06),
        },
        "gen07": {
            "root": str(GEN07),
            "exists": GEN07.exists(),
            "files": tree_records(GEN07),
        },
        "lane_job": lane_job_records(),
        "lane_inventory": lane_inventory(),
        "job_identity": {
            "outbox_role": outbox_request.get("role") if isinstance(outbox_request, dict) else None,
            "outbox_run_id": outbox_request.get("run_id") if isinstance(outbox_request, dict) else None,
            "outbox_request_sha256": outbox_request.get("request_sha256") if isinstance(outbox_request, dict) else None,
            "outbox_prompt_sha256": outbox_request.get("prompt_sha256") if isinstance(outbox_request, dict) else None,
            "outbox_schema_sha256": outbox_request.get("schema_sha256") if isinstance(outbox_request, dict) else None,
            "inbox_request_sha256": inbox_response.get("request_sha256") if isinstance(inbox_response, dict) else None,
            "archive_request_sha256": archive_request.get("request_sha256") if isinstance(archive_request, dict) else None,
            "attempt_request_sha256": attempt.get("request_sha256") if isinstance(attempt, dict) else None,
        },
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

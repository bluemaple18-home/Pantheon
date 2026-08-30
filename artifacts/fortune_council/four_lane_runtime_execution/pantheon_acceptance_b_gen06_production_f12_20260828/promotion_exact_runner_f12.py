#!/usr/bin/env python3
"""Run exact f12 runtime promotion commands and save bounded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
SOURCE_REPO = Path("/private/tmp/pantheon-gen06-production-f12-source-20260828")
EVIDENCE_DIR = MAIN_REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_production_f12_20260828"
PYTHON = MAIN_REPO / ".venv/bin/python"
TARGET_SHA = "f12f24315d30a8d030cf2e9d99a310c711eeeb0e"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
MANIFEST_PATH = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json")
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue")
PUBLISHER_STATE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state")
LOG_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/logs")
TRANSACTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/pantheon-gen06-production-f12-20260828")
EXPECTED_CURRENT_ACTOR_SHA = "99507c67e27d9e6f3af4e33c3ab0727682ed82bd"
EXPECTED_CURRENT_MANIFEST_DIGEST = "f3f0185bb35cdfe8da3602689d441ae46386682542c0be1a3364f97c10b4e4e0"
EXPECTED_CURRENT_STAGE_DIGEST = "3431336fd5c32b8ab85ce1deed083ba3aeade4cd4a4b1433752cdc8619946c85"
TARGET_IDENTITY = "gate2-actor:f12f24315d30a8d030cf2e9d99a310c711eeeb0e:gen06-production-f12-20260828"
TARGET_RUNTIME_DIGEST = "f346d0086ded5dd97505c27deb3f6cab92915d665fc82950b7f717701e3dd671"
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
TARGET_GENERATION = "g61-f12f2431-gen06-production-f12-20260828"
TARGET_PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
TARGET_UV = Path("/Users/mattkuo/.local/bin/uv")
CAPACITY_RECEIPT = EVIDENCE_DIR / "rule24-capacity-pre-f12.json"
CORRELATION_ID = "pantheon-gen06-production-f12-20260828"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_stdout(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def preserved_run_ids() -> list[str]:
    return sorted({json.loads(path.read_text(encoding="utf-8"))["run_id"] for path in (QUEUE_ROOT / "runs").glob("*.json")})


def common_args() -> list[str]:
    run_ids = preserved_run_ids()
    write_json(EVIDENCE_DIR / "preserved-run-ids-f12.json", run_ids)
    args = [
        str(PYTHON), "-m", "scripts.pantheon_content_runtime_promotion",
        "--source-repo", str(SOURCE_REPO), "--source-sha", TARGET_SHA, "--expected-origin", EXPECTED_ORIGIN,
        "--actor-root", str(ACTOR_ROOT), "--expected-current-actor-sha", EXPECTED_CURRENT_ACTOR_SHA,
        "--manifest-path", str(MANIFEST_PATH), "--expected-current-manifest-digest", EXPECTED_CURRENT_MANIFEST_DIGEST,
        "--private-stage-root", str(PRIVATE_STAGE_ROOT), "--expected-current-stage-digest", EXPECTED_CURRENT_STAGE_DIGEST,
        "--transaction-root", str(TRANSACTION_ROOT), "--queue-root", str(QUEUE_ROOT),
        "--publisher-state-root", str(PUBLISHER_STATE_ROOT), "--log-root", str(LOG_ROOT),
        "--target-identity", TARGET_IDENTITY, "--target-runtime-digest", TARGET_RUNTIME_DIGEST,
        "--target-config-version", TARGET_CONFIG_VERSION, "--target-generation", TARGET_GENERATION,
        "--target-python-executable", str(TARGET_PYTHON), "--target-uv-executable", str(TARGET_UV),
        "--authorization-digest", sha256_file(EVIDENCE_DIR / "authorization-payload-f12.json"),
        "--capacity-receipt", str(CAPACITY_RECEIPT), "--capacity-receipt-digest", sha256_file(CAPACITY_RECEIPT),
        "--correlation-id", CORRELATION_ID,
    ]
    for run_id in run_ids:
        args.extend(["--preserve-run-id", run_id])
    return args


def run(args: list[str], label: str) -> int:
    write_json(EVIDENCE_DIR / f"{label}-command.json", args)
    completed = subprocess.run(args, cwd=str(SOURCE_REPO), capture_output=True, text=True, check=False)
    (EVIDENCE_DIR / f"{label}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE_DIR / f"{label}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE_DIR / f"{label}.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
    if completed.stdout.strip().startswith("{"):
        try:
            write_json(EVIDENCE_DIR / f"{label}.stdout.json", json.loads(completed.stdout))
        except json.JSONDecodeError:
            pass
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["plan", "apply", "finalize", "status", "rollback"])
    parser.add_argument("--expected-plan-digest")
    args = parser.parse_args()
    write_json(EVIDENCE_DIR / f"{args.command}-source-identity-f12.json", {
        "source_head": git_stdout(SOURCE_REPO, "rev-parse", "HEAD"),
        "source_origin": git_stdout(SOURCE_REPO, "remote", "get-url", "origin"),
        "source_status": git_stdout(SOURCE_REPO, "status", "--porcelain"),
        "actor_head_before": git_stdout(ACTOR_ROOT, "rev-parse", "HEAD"),
        "authorization_digest": sha256_file(EVIDENCE_DIR / "authorization-payload-f12.json"),
        "capacity_receipt_digest": sha256_file(CAPACITY_RECEIPT),
    })
    if TRANSACTION_ROOT.exists() and args.command == "plan":
        raise SystemExit("transaction root already exists before plan")
    command = common_args()
    command.insert(3, args.command)
    if args.command in {"apply", "finalize", "rollback"}:
        if not args.expected_plan_digest:
            raise SystemExit("--expected-plan-digest is required")
        command.extend(["--expected-plan-digest", args.expected_plan_digest])
    return run(command, f"promotion-{args.command}-f12")


if __name__ == "__main__":
    raise SystemExit(main())

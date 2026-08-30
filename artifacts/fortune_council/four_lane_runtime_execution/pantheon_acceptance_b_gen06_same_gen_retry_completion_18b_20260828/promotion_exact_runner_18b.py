#!/usr/bin/env python3
"""Run exact 18b runtime promotion commands and save bounded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
SOURCE_REPO = Path("/private/tmp/pantheon-gen06-samegen-retry-18b-source-20260828-a")
EVIDENCE_DIR = MAIN_REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_completion_18b_20260828"
PYTHON = MAIN_REPO / ".venv/bin/python"
TARGET_SHA = "18b121fa335ab74621fb8da03d1a6b2a02916c88"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
MANIFEST_PATH = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json")
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue")
PUBLISHER_STATE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state")
LOG_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/logs")
TRANSACTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/pantheon-gen06-samegen-retry-18b-20260828")
EXPECTED_CURRENT_ACTOR_SHA = "ff41cb1c113fc78c9026662186d7bb4c47204a49"
EXPECTED_CURRENT_MANIFEST_DIGEST = "bf6b6be8cec1133281bcc24dd52d40302f7619565720bf231a8967982b027b20"
EXPECTED_CURRENT_STAGE_DIGEST = "c1bcd9398ff31e71ca0406c8feb006f0bc53cdca1259144f125a36ed81ec8b45"
TARGET_IDENTITY = "gate2-actor:18b121fa335ab74621fb8da03d1a6b2a02916c88:gen06-samegen-retry-18b-20260828"
TARGET_RUNTIME_DIGEST = "f346d0086ded5dd97505c27deb3f6cab92915d665fc82950b7f717701e3dd671"
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
TARGET_GENERATION = "g63-18b121fa-gen06-samegen-retry-20260828"
TARGET_PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
TARGET_UV = Path("/Users/mattkuo/.local/bin/uv")
CAPACITY_RECEIPT = EVIDENCE_DIR / "rule24-capacity-pre-18b.json"
CORRELATION_ID = "pantheon-gen06-samegen-retry-18b-20260828"


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
    write_json(EVIDENCE_DIR / "preserved-run-ids-18b.json", run_ids)
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
        "--authorization-digest", sha256_file(EVIDENCE_DIR / "authorization-payload-18b.json"),
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
    write_json(EVIDENCE_DIR / f"{args.command}-source-identity-18b.json", {
        "source_head": git_stdout(SOURCE_REPO, "rev-parse", "HEAD"),
        "source_origin": git_stdout(SOURCE_REPO, "remote", "get-url", "origin"),
        "source_status": git_stdout(SOURCE_REPO, "status", "--porcelain"),
        "actor_head_before": git_stdout(ACTOR_ROOT, "rev-parse", "HEAD"),
        "authorization_digest": sha256_file(EVIDENCE_DIR / "authorization-payload-18b.json"),
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
    return run(command, f"promotion-{args.command}-18b")


if __name__ == "__main__":
    raise SystemExit(main())

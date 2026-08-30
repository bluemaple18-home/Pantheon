#!/usr/bin/env python3
"""Run exact 995 runtime promotion commands and save bounded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
SOURCE_REPO = Path("/private/tmp/pantheon-gen06-attempt-995-source-20260828")
EVIDENCE_DIR = MAIN_REPO / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "pantheon_acceptance_b_gen06_production_attempt_995_20260828"
)
PYTHON = MAIN_REPO / ".venv/bin/python"
TARGET_SHA = "99507c67e27d9e6f3af4e33c3ab0727682ed82bd"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
MANIFEST_PATH = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json")
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue")
PUBLISHER_STATE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state")
LOG_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/logs")
EXPECTED_CURRENT_ACTOR_SHA = "ac1faef520c9b79f9bb70265735d07a6ca826b7d"
EXPECTED_CURRENT_MANIFEST_DIGEST = "5edb5d5f0b1d8eebc2fbe0855127f83fc9022fea9175c082505e807a29225bfe"
EXPECTED_CURRENT_STAGE_DIGEST = "914a85d7ceaebc039b54f888353ba6a5f13d1052fd1308d526ed0c5b0871b3f9"
TARGET_IDENTITY = "gate2-actor:99507c67e27d9e6f3af4e33c3ab0727682ed82bd:gen06-boundary-meaning-production-attempt-20260828"
TARGET_RUNTIME_DIGEST = "94567c23baedc97e300fc31b7c419496eee3140de3cacf2a63a42820d626d041"
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
TARGET_GENERATION = "g60-99507c67-gen06-boundary-meaning-production-attempt-20260828"
TARGET_PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
TARGET_UV = Path("/Users/mattkuo/.local/bin/uv")
CAPACITY_RECEIPT = EVIDENCE_DIR / "rule24-capacity-pre-995.json"
CAPACITY_RECEIPT_DIGEST = "a183f5bb098562138037a1c7bbee5b4482874f7535a588b2030797a857b9ff68"
AUTHORIZATION_PAYLOAD = EVIDENCE_DIR / "authorization-payload-995.json"
CORRELATION_ID = "pantheon-gen06-production-attempt-995-20260828"
TRANSACTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/pantheon-gen06-production-attempt-995-20260828")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], *, label: str) -> int:
    write_json(EVIDENCE_DIR / f"{label}-command.json", args)
    completed = subprocess.run(
        args,
        cwd=str(SOURCE_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    (EVIDENCE_DIR / f"{label}.stdout.txt").write_text(
        completed.stdout,
        encoding="utf-8",
    )
    (EVIDENCE_DIR / f"{label}.stderr.txt").write_text(
        completed.stderr,
        encoding="utf-8",
    )
    (EVIDENCE_DIR / f"{label}.returncode.txt").write_text(
        str(completed.returncode) + "\n",
        encoding="utf-8",
    )
    if completed.stdout.strip().startswith("{"):
        try:
            write_json(
                EVIDENCE_DIR / f"{label}.stdout.json",
                json.loads(completed.stdout),
            )
        except json.JSONDecodeError:
            pass
    return completed.returncode


def git_stdout(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def preserved_run_ids() -> list[str]:
    run_ids: list[str] = []
    for path in sorted((QUEUE_ROOT / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_id = payload.get("run_id")
        if isinstance(run_id, str) and run_id:
            run_ids.append(run_id)
    return sorted(set(run_ids))


def common_args() -> list[str]:
    authorization_digest = sha256_file(AUTHORIZATION_PAYLOAD)
    run_ids = preserved_run_ids()
    write_json(EVIDENCE_DIR / "preserved-run-ids-995.json", run_ids)
    args = [
        str(PYTHON),
        "-m",
        "scripts.pantheon_content_runtime_promotion",
        "--source-repo",
        str(SOURCE_REPO),
        "--source-sha",
        TARGET_SHA,
        "--expected-origin",
        EXPECTED_ORIGIN,
        "--actor-root",
        str(ACTOR_ROOT),
        "--expected-current-actor-sha",
        EXPECTED_CURRENT_ACTOR_SHA,
        "--manifest-path",
        str(MANIFEST_PATH),
        "--expected-current-manifest-digest",
        EXPECTED_CURRENT_MANIFEST_DIGEST,
        "--private-stage-root",
        str(PRIVATE_STAGE_ROOT),
        "--expected-current-stage-digest",
        EXPECTED_CURRENT_STAGE_DIGEST,
        "--transaction-root",
        str(TRANSACTION_ROOT),
        "--queue-root",
        str(QUEUE_ROOT),
        "--publisher-state-root",
        str(PUBLISHER_STATE_ROOT),
        "--log-root",
        str(LOG_ROOT),
        "--target-identity",
        TARGET_IDENTITY,
        "--target-runtime-digest",
        TARGET_RUNTIME_DIGEST,
        "--target-config-version",
        TARGET_CONFIG_VERSION,
        "--target-generation",
        TARGET_GENERATION,
        "--target-python-executable",
        str(TARGET_PYTHON),
        "--target-uv-executable",
        str(TARGET_UV),
        "--authorization-digest",
        authorization_digest,
        "--capacity-receipt",
        str(CAPACITY_RECEIPT),
        "--capacity-receipt-digest",
        CAPACITY_RECEIPT_DIGEST,
        "--correlation-id",
        CORRELATION_ID,
    ]
    for run_id in run_ids:
        args.extend(["--preserve-run-id", run_id])
    return args


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["plan", "apply", "finalize", "status", "rollback"],
    )
    parser.add_argument("--expected-plan-digest")
    args = parser.parse_args()
    source_identity = {
        "source_head": git_stdout(SOURCE_REPO, "rev-parse", "HEAD"),
        "source_origin": git_stdout(SOURCE_REPO, "remote", "get-url", "origin"),
        "source_status": git_stdout(SOURCE_REPO, "status", "--porcelain"),
        "actor_head_before": git_stdout(ACTOR_ROOT, "rev-parse", "HEAD"),
        "authorization_digest": sha256_file(AUTHORIZATION_PAYLOAD),
        "capacity_receipt_digest": sha256_file(CAPACITY_RECEIPT),
    }
    write_json(
        EVIDENCE_DIR / f"{args.command}-source-identity-995.json",
        source_identity,
    )
    if TRANSACTION_ROOT.exists() and args.command == "plan":
        raise SystemExit("transaction root already exists before plan")
    command = common_args()
    command.insert(3, args.command)
    if args.command in {"apply", "finalize", "rollback"}:
        if not args.expected_plan_digest:
            raise SystemExit("--expected-plan-digest is required")
        command.extend(["--expected-plan-digest", args.expected_plan_digest])
    return run(command, label=f"promotion-{args.command}-995")


if __name__ == "__main__":
    raise SystemExit(main())

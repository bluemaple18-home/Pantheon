#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO = Path("/Users/mattkuo/Documents/Pantheon")
SOURCE_REPO = Path("/private/tmp/pantheon-gen06-final-publish-source-5704-20260829")
EVIDENCE = REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_final_publish_acceptance_20260829"
PYTHON = REPO / ".venv/bin/python"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
TARGET_SHA = "5704fa6077aa4187619fddc08d9c29cad2f2dabf"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
PRODUCTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = PRODUCTION_ROOT / "actor"
MANIFEST_PATH = PRODUCTION_ROOT / "runtime-manifest.json"
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = PRODUCTION_ROOT / "queue"
QUEUE_STATE = QUEUE_ROOT / "runs/f46cda9eaa9ded446bf8e6c6.json"
PUBLISHER_STATE_ROOT = PRODUCTION_ROOT / "state"
LOG_ROOT = PRODUCTION_ROOT / "logs"
TRANSACTION_ROOT = PRODUCTION_ROOT / "transactions/pantheon-gen06-final-publish-runtime-digest-correction-5704-20260829"
TARGET_IDENTITY = f"gate2-actor:{TARGET_SHA}:gen06-final-publish-runtime-digest-correction-20260829"
TARGET_GENERATION = "g66-5704fa60-gen06-final-publish-runtime-digest-correction-20260829"
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
CAPACITY_RECEIPT = EVIDENCE / "rule24-capacity-pre.json"
AUTHORIZATION_PAYLOAD = EVIDENCE / "authorization-payload-5704.json"

sys.path.insert(0, str(REPO))

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_promotion as promotion


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_stdout(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def current_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def target_runtime_digest() -> str:
    return publisher.runtime_manifest_digest(SOURCE_REPO)


def preserved_run_ids() -> list[str]:
    run_ids: list[str] = []
    for path in sorted((QUEUE_ROOT / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_id = payload.get("run_id")
        if isinstance(run_id, str) and run_id:
            run_ids.append(run_id)
    return sorted(set(run_ids))


def write_authorization() -> None:
    payload = {
        "schema_version": 1,
        "authorized_by": "Owner prompt",
        "operation": "pantheon-gen06-final-publish-acceptance",
        "correction": "OPERATOR_HELPER_DIGEST_DERIVATION_ERROR",
        "target_sha": TARGET_SHA,
        "expected_initial_origin_main": "831c536043d85a6cafe813c08a4f06921f0dd0e2",
        "run_id": RUN_ID,
        "allowed_mutations": [
            "push exact target sha to origin/main once",
            "formal runtime promotion",
            "formal approved edited candidate staging",
            "formal publisher transaction/tag/push/deploy",
        ],
        "forbidden_mutations": [
            "force push",
            "source edits",
            "test edits",
            "manual production state edits",
            "provider calls",
            "coordinator calls",
            "Gen07 creation",
        ],
    }
    write_json(AUTHORIZATION_PAYLOAD, payload)


def common_promotion_args() -> list[str]:
    write_authorization()
    manifest = current_manifest()
    run_ids = preserved_run_ids()
    write_json(EVIDENCE / "preserved-run-ids-5704-correction.json", run_ids)
    runtime_digest = target_runtime_digest()
    write_json(
        EVIDENCE / "promotion-input-summary-5704-correction.json",
        {
            "actor_head": git_stdout(ACTOR_ROOT, "rev-parse", "HEAD"),
            "actor_status": git_stdout(ACTOR_ROOT, "status", "--porcelain"),
            "current_manifest_digest": manifest["manifest_digest"],
            "current_stage_digest": promotion.tree_digest(PRIVATE_STAGE_ROOT),
            "target_runtime_digest": runtime_digest,
            "target_identity": TARGET_IDENTITY,
            "target_generation": TARGET_GENERATION,
            "preserved_run_ids": run_ids,
            "capacity_receipt_digest": sha256_file(CAPACITY_RECEIPT),
            "authorization_digest": sha256_file(AUTHORIZATION_PAYLOAD),
        },
    )
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
        git_stdout(ACTOR_ROOT, "rev-parse", "HEAD"),
        "--manifest-path",
        str(MANIFEST_PATH),
        "--expected-current-manifest-digest",
        manifest["manifest_digest"],
        "--private-stage-root",
        str(PRIVATE_STAGE_ROOT),
        "--expected-current-stage-digest",
        promotion.tree_digest(PRIVATE_STAGE_ROOT),
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
        runtime_digest,
        "--target-config-version",
        TARGET_CONFIG_VERSION,
        "--target-generation",
        TARGET_GENERATION,
        "--target-python-executable",
        manifest["python_executable"],
        "--target-uv-executable",
        manifest["uv_executable"],
        "--authorization-digest",
        sha256_file(AUTHORIZATION_PAYLOAD),
        "--capacity-receipt",
        str(CAPACITY_RECEIPT),
        "--capacity-receipt-digest",
        sha256_file(CAPACITY_RECEIPT),
        "--correlation-id",
        "pantheon-gen06-final-publish-runtime-digest-correction-5704-20260829",
    ]
    for run_id in run_ids:
        args.extend(["--preserve-run-id", run_id])
    return args


def run_promotion(command: str, expected_plan_digest: str | None) -> int:
    args = common_promotion_args()
    args.insert(3, command)
    if command in {"apply", "finalize", "rollback"}:
        if not expected_plan_digest:
            raise SystemExit("--expected-plan-digest is required")
        args.extend(["--expected-plan-digest", expected_plan_digest])
    label = f"promotion-{command}-5704-correction"
    write_json(EVIDENCE / f"{label}-command.json", args)
    completed = subprocess.run(args, cwd=str(SOURCE_REPO), capture_output=True, text=True, check=False)
    (EVIDENCE / f"{label}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE / f"{label}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE / f"{label}.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
    if completed.stdout.strip().startswith("{"):
        write_json(EVIDENCE / f"{label}.stdout.json", json.loads(completed.stdout))
    return completed.returncode


def snapshot(label: str) -> None:
    run_dir = QUEUE_ROOT / "translation-runs" / RUN_ID
    payload = {
        "label": label,
        "repo_head": git_stdout(REPO, "rev-parse", "HEAD"),
        "repo_status_tracked": git_stdout(REPO, "status", "--short", "--untracked-files=no"),
        "actor_head": git_stdout(ACTOR_ROOT, "rev-parse", "HEAD"),
        "actor_status": git_stdout(ACTOR_ROOT, "status", "--porcelain"),
        "manifest": current_manifest(),
        "private_stage_digest": promotion.tree_digest(PRIVATE_STAGE_ROOT),
        "run_dir": str(run_dir),
        "run_candidate_sha256": sha256_file(run_dir / "candidate.json"),
        "run_review_sha256": sha256_file(run_dir / "review.json"),
        "continuation_state_sha256": sha256_file(run_dir / "continuation/state.json"),
        "gen06_candidate_sha256": sha256_file(run_dir / "generations/06/candidate.json") if (run_dir / "generations/06/candidate.json").exists() else None,
        "gen06_review_sha256": sha256_file(run_dir / "generations/06/review.json") if (run_dir / "generations/06/review.json").exists() else None,
        "gen07_exists": (run_dir / "generations/07").exists(),
        "queue_state_path": str(QUEUE_STATE),
        "queue_state_sha256": sha256_file(QUEUE_STATE),
        "publisher_ledger_sha256": sha256_file(PUBLISHER_STATE_ROOT / "ledger.json"),
    }
    write_json(EVIDENCE / f"{label}-snapshot.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["snapshot", "promotion"])
    parser.add_argument("--label")
    parser.add_argument("--promotion-command", choices=["plan", "apply", "finalize", "status", "rollback"])
    parser.add_argument("--expected-plan-digest")
    args = parser.parse_args()
    if args.command == "snapshot":
        if not args.label:
            raise SystemExit("--label is required")
        snapshot(args.label)
        return 0
    if not args.promotion_command:
        raise SystemExit("--promotion-command is required")
    return run_promotion(args.promotion_command, args.expected_plan_digest)


if __name__ == "__main__":
    raise SystemExit(main())

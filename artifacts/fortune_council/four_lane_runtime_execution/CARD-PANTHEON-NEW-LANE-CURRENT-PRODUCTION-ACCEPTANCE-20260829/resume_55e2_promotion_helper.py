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
SOURCE_REPO = Path("/private/tmp/pantheon-new-lane-55e2-source-20260829")
EVIDENCE = REPO / "artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829"
PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
CURRENT_SHA = "dfcb3c77f9404fc9ff0707cb944ad08f50a4abef"
CURRENT_MANIFEST_DIGEST = "4eaefa54b176ca8b159a05872655066304cfa8de15fe4dbcb2c67c94cf1e0de6"
TARGET_SHA = "55e2a78de92a6d7929da531ffc3e0dab049df142"
TARGET_RUNTIME_DIGEST = "db960fb0118ac8deda7de3d1b2b7e55358ea670458dd6d08773a56110ed8faba"
PRODUCTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = PRODUCTION_ROOT / "actor"
MANIFEST_PATH = PRODUCTION_ROOT / "runtime-manifest.json"
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = PRODUCTION_ROOT / "queue"
STATE_ROOT = PRODUCTION_ROOT / "state"
LOG_ROOT = PRODUCTION_ROOT / "logs"
TRANSACTION_ROOT = PRODUCTION_ROOT / "transactions/pantheon-new-lane-current-acceptance-55e2-20260829"
TARGET_IDENTITY = f"gate2-actor:{TARGET_SHA}:new-lane-current-acceptance-20260829"
TARGET_GENERATION = "g69-55e2a78d-new-lane-current-acceptance-20260829"
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
CAPACITY_RECEIPT = EVIDENCE / "resume-55e2-rule24-host-telemetry.json"
AUTHORIZATION_PAYLOAD = EVIDENCE / "resume-55e2-authorization-payload.json"
SERVICE_LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.content-capacity-guard",
)

sys.path.insert(0, str(SOURCE_REPO))
from scripts import agy_content_publisher as publisher  # noqa: E402
from scripts import pantheon_content_runtime_promotion as promotion  # noqa: E402


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_stdout(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def assert_services_stopped() -> dict[str, int]:
    outcomes: dict[str, int] = {}
    for label in SERVICE_LABELS:
        completed = subprocess.run(
            ["launchctl", "print", f"gui/501/{label}"],
            check=False,
            capture_output=True,
            text=True,
        )
        outcomes[label] = completed.returncode
        if completed.returncode == 0:
            raise SystemExit(f"service unexpectedly loaded: {label}")
    return outcomes


def preserved_run_ids() -> list[str]:
    values: set[str] = set()
    for path in sorted((QUEUE_ROOT / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_id = payload.get("run_id")
        if isinstance(run_id, str) and run_id:
            values.add(run_id)
    return sorted(values)


def authorization() -> str:
    payload = {
        "schema_version": 1,
        "authorized_by": "Owner four-lane production continuation",
        "operation": "new-lane-current-production-acceptance-55e2",
        "target_sha": TARGET_SHA,
        "parent_sha": CURRENT_SHA,
        "allowed_mutations": [
            "formal runtime promotion dfcb to 55e2",
            "exact stale succeeded writer terminalization once",
            "formal current runtime install and aggregate activation",
            "one fresh new run writer reviewer publisher release deploy",
        ],
        "forbidden_mutations": [
            "source repair",
            "manual plist edits",
            "rewrite or i18n lane execution",
            "second provider or publisher execute",
        ],
    }
    write_json(AUTHORIZATION_PAYLOAD, payload)
    return sha256_file(AUTHORIZATION_PAYLOAD)


def build_args(command: str, expected_plan_digest: str | None) -> list[str]:
    services = assert_services_stopped()
    if git_stdout(SOURCE_REPO, "rev-parse", "HEAD") != TARGET_SHA:
        raise SystemExit("target source SHA drift")
    if git_stdout(SOURCE_REPO, "status", "--porcelain"):
        raise SystemExit("target source is dirty")
    if git_stdout(SOURCE_REPO, "remote", "get-url", "origin") != EXPECTED_ORIGIN:
        raise SystemExit("target source origin drift")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actor_head = git_stdout(ACTOR_ROOT, "rev-parse", "HEAD")
    if command in {"plan", "apply"}:
        if actor_head != CURRENT_SHA or manifest.get("manifest_digest") != CURRENT_MANIFEST_DIGEST:
            raise SystemExit("current actor or manifest drift")
    if publisher.runtime_manifest_digest(SOURCE_REPO) != TARGET_RUNTIME_DIGEST:
        raise SystemExit("target runtime digest drift")
    run_ids = preserved_run_ids()
    write_json(EVIDENCE / "resume-55e2-preserved-run-ids.json", run_ids)
    auth_digest = authorization()
    write_json(
        EVIDENCE / f"resume-55e2-{command}-input.json",
        {
            "source_head": TARGET_SHA,
            "actor_head": actor_head,
            "manifest_digest": manifest.get("manifest_digest"),
            "target_runtime_digest": TARGET_RUNTIME_DIGEST,
            "target_identity": TARGET_IDENTITY,
            "target_generation": TARGET_GENERATION,
            "capacity_receipt_sha256": sha256_file(CAPACITY_RECEIPT),
            "authorization_sha256": auth_digest,
            "services_stopped_returncodes": services,
            "preserved_run_count": len(run_ids),
        },
    )
    args = [
        str(PYTHON), "-m", "scripts.pantheon_content_runtime_promotion", command,
        "--source-repo", str(SOURCE_REPO),
        "--source-sha", TARGET_SHA,
        "--expected-origin", EXPECTED_ORIGIN,
        "--actor-root", str(ACTOR_ROOT),
        "--expected-current-actor-sha", CURRENT_SHA,
        "--manifest-path", str(MANIFEST_PATH),
        "--expected-current-manifest-digest", CURRENT_MANIFEST_DIGEST,
        "--private-stage-root", str(PRIVATE_STAGE_ROOT),
        "--expected-current-stage-digest", promotion.tree_digest(PRIVATE_STAGE_ROOT),
        "--transaction-root", str(TRANSACTION_ROOT),
        "--queue-root", str(QUEUE_ROOT),
        "--publisher-state-root", str(STATE_ROOT),
        "--log-root", str(LOG_ROOT),
        "--target-identity", TARGET_IDENTITY,
        "--target-runtime-digest", TARGET_RUNTIME_DIGEST,
        "--target-config-version", TARGET_CONFIG_VERSION,
        "--target-generation", TARGET_GENERATION,
        "--target-python-executable", str(PYTHON),
        "--target-uv-executable", str(manifest["uv_executable"]),
        "--authorization-digest", auth_digest,
        "--capacity-receipt", str(CAPACITY_RECEIPT),
        "--capacity-receipt-digest", sha256_file(CAPACITY_RECEIPT),
        "--correlation-id", "pantheon-new-lane-current-acceptance-55e2-20260829",
    ]
    for run_id in run_ids:
        args.extend(["--preserve-run-id", run_id])
    if command in {"apply", "finalize", "rollback"}:
        if not expected_plan_digest:
            raise SystemExit("expected plan digest required")
        args.extend(["--expected-plan-digest", expected_plan_digest])
    return args


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "apply", "finalize", "status"))
    parser.add_argument("--expected-plan-digest")
    args = parser.parse_args()
    command = build_args(args.command, args.expected_plan_digest)
    write_json(EVIDENCE / f"resume-55e2-promotion-{args.command}-command.json", command)
    completed = subprocess.run(command, cwd=str(SOURCE_REPO), check=False, capture_output=True, text=True)
    (EVIDENCE / f"resume-55e2-promotion-{args.command}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE / f"resume-55e2-promotion-{args.command}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE / f"resume-55e2-promotion-{args.command}.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
    if completed.stdout.strip().startswith("{"):
        write_json(EVIDENCE / f"resume-55e2-promotion-{args.command}.stdout.json", json.loads(completed.stdout))
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

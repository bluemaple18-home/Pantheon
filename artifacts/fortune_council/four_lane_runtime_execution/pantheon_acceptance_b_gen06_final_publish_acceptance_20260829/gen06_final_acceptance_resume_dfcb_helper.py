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
SOURCE_REPO = Path("/private/tmp/pantheon-gen06-final-publish-source-dfcb-20260829")
EVIDENCE = REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_final_publish_acceptance_20260829"
PYTHON = REPO / ".venv/bin/python"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
TARGET_SHA = "dfcb3c77f9404fc9ff0707cb944ad08f50a4abef"
EXPECTED_CURRENT_ACTOR_SHA = "1e46c46426cf1662c1089cbf33dcf2ee54d437c4"
EXPECTED_CURRENT_MANIFEST_DIGEST = "71ac7256575fa7c17e32cf00aafd357acb8e0f3719a1b58e121203578a111e20"
EXPECTED_TARGET_RUNTIME_DIGEST = "db960fb0118ac8deda7de3d1b2b7e55358ea670458dd6d08773a56110ed8faba"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
PRODUCTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = PRODUCTION_ROOT / "actor"
MANIFEST_PATH = PRODUCTION_ROOT / "runtime-manifest.json"
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = PRODUCTION_ROOT / "queue"
QUEUE_STATE = QUEUE_ROOT / "runs/f46cda9eaa9ded446bf8e6c6.json"
PUBLISHER_STATE_ROOT = PRODUCTION_ROOT / "state"
LOG_ROOT = PRODUCTION_ROOT / "logs"
TRANSACTION_ROOT = PRODUCTION_ROOT / "transactions/pantheon-gen06-final-publish-release-namespace-dfcb-20260829"
TARGET_IDENTITY = f"gate2-actor:{TARGET_SHA}:gen06-final-publish-release-namespace-20260829"
TARGET_GENERATION = "g68-dfcb3c77-gen06-final-publish-release-namespace-20260829"
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
CAPACITY_RECEIPT = EVIDENCE / "resume-dfcb-rule24-capacity-pre-host-telemetry.json"
AUTHORIZATION_PAYLOAD = EVIDENCE / "resume-dfcb-authorization-payload.json"
READINESS_ROOT = EVIDENCE / "resume-dfcb-rule24-host-readiness"

sys.path.insert(0, str(SOURCE_REPO))

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
    digest = publisher.runtime_manifest_digest(SOURCE_REPO)
    if digest != EXPECTED_TARGET_RUNTIME_DIGEST:
        raise SystemExit(f"target runtime digest drift: {digest}")
    return digest


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
        "operation": "pantheon-gen06-final-publish-acceptance-resume-after-release-namespace-repair",
        "target_sha": TARGET_SHA,
        "parent_sha": EXPECTED_CURRENT_ACTOR_SHA,
        "run_id": RUN_ID,
        "allowed_mutations": [
            "formal runtime promotion from 1e46 to dfcb",
            "formal publisher transaction/tag/push/deploy through normal retry seam",
        ],
        "forbidden_mutations": [
            "force push",
            "source edits",
            "test edits",
            "manual production state edits",
            "provider calls",
            "coordinator calls",
            "Gen07 creation",
            "stage execute replay",
            "exact-fresh selector",
        ],
    }
    write_json(AUTHORIZATION_PAYLOAD, payload)


def common_promotion_args(command: str) -> list[str]:
    write_authorization()
    source_head = git_stdout(SOURCE_REPO, "rev-parse", "HEAD")
    if source_head != TARGET_SHA:
        raise SystemExit(f"source sha drift: {source_head}")
    if git_stdout(SOURCE_REPO, "status", "--porcelain"):
        raise SystemExit("source repo dirty")
    if git_stdout(SOURCE_REPO, "remote", "get-url", "origin") != EXPECTED_ORIGIN:
        raise SystemExit("source origin drift")
    manifest = current_manifest()
    actor_head = git_stdout(ACTOR_ROOT, "rev-parse", "HEAD")
    if command in {"plan", "apply"} and manifest.get("manifest_digest") != EXPECTED_CURRENT_MANIFEST_DIGEST:
        raise SystemExit(f"current manifest digest drift: {manifest.get('manifest_digest')}")
    if command in {"plan", "apply"} and actor_head != EXPECTED_CURRENT_ACTOR_SHA:
        raise SystemExit(f"current actor sha drift: {actor_head}")
    run_ids = preserved_run_ids()
    runtime_digest = target_runtime_digest()
    write_json(EVIDENCE / "resume-dfcb-preserved-run-ids.json", run_ids)
    write_json(
        EVIDENCE / "resume-dfcb-promotion-input-summary.json",
        {
            "actor_head": actor_head,
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
        EXPECTED_CURRENT_ACTOR_SHA,
        "--manifest-path",
        str(MANIFEST_PATH),
        "--expected-current-manifest-digest",
        EXPECTED_CURRENT_MANIFEST_DIGEST,
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
        "pantheon-gen06-final-publish-release-namespace-dfcb-20260829",
    ]
    for run_id in run_ids:
        args.extend(["--preserve-run-id", run_id])
    return args


def run_promotion(command: str, expected_plan_digest: str | None) -> int:
    args = common_promotion_args(command)
    args.insert(3, command)
    if command in {"apply", "finalize", "rollback"}:
        if not expected_plan_digest:
            raise SystemExit("--expected-plan-digest is required")
        args.extend(["--expected-plan-digest", expected_plan_digest])
    label = f"resume-dfcb-promotion-{command}"
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
        "stage_current_sha256": sha256_file(run_dir / "editorial-staging/current.json"),
        "run_candidate_sha256": sha256_file(run_dir / "candidate.json"),
        "run_review_sha256": sha256_file(run_dir / "review.json"),
        "continuation_state_sha256": sha256_file(run_dir / "continuation/state.json"),
        "gen06_candidate_sha256": sha256_file(run_dir / "generations/06/candidate.json") if (run_dir / "generations/06/candidate.json").exists() else None,
        "gen06_review_sha256": sha256_file(run_dir / "generations/06/review.json") if (run_dir / "generations/06/review.json").exists() else None,
        "gen07_exists": (run_dir / "generations/07").exists(),
        "queue_state_sha256": sha256_file(QUEUE_STATE),
        "publisher_ledger_sha256": sha256_file(PUBLISHER_STATE_ROOT / "ledger.json"),
    }
    write_json(EVIDENCE / f"{label}-snapshot.json", payload)


def normalized_rule24() -> None:
    receipt = json.loads(CAPACITY_RECEIPT.read_text(encoding="utf-8"))
    readiness_summary = json.loads((READINESS_ROOT / "readiness-summary.json").read_text(encoding="utf-8"))
    capacity_proof = json.loads((READINESS_ROOT / "package/capacity-proof-normalized.json").read_text(encoding="utf-8"))
    capacity_receipt = json.loads((READINESS_ROOT / "capacity/capacity-receipt.json").read_text(encoding="utf-8"))
    machine = json.loads(
        (
            REPO
            / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_rule24_capacity_blocker_triage_20260829/machine-receipt.json"
        ).read_text(encoding="utf-8")
    )
    total = int(machine["host"]["total_bytes"])
    free = int(receipt["cycles"][-1]["host_free_after"])
    ten_percent = int(total * 0.10)
    twenty_gib = 20 * 1024 * 1024 * 1024
    reserve = max(ten_percent, twenty_gib)
    retention_peak = int(machine["normalized_capacity_proof"]["projection"]["retention_peak_bytes"])
    projected_free = free - retention_peak
    payload = {
        "schema_version": 1,
        "status": "PASS"
        if receipt.get("status") == "PASS"
        and readiness_summary.get("status") == "READY"
        and projected_free > reserve
        else "NO-GO",
        "source": {
            "host_telemetry_receipt": CAPACITY_RECEIPT.relative_to(EVIDENCE).as_posix(),
            "host_telemetry_receipt_sha256": sha256_file(CAPACITY_RECEIPT),
            "readiness_summary": READINESS_ROOT.relative_to(EVIDENCE).as_posix() + "/readiness-summary.json",
            "readiness_summary_sha256": sha256_file(READINESS_ROOT / "readiness-summary.json"),
            "official_gate_ready": READINESS_ROOT.relative_to(EVIDENCE).as_posix() + "/official-gate-ready.json",
            "official_gate_ready_sha256": sha256_file(READINESS_ROOT / "official-gate-ready.json"),
            "packaged_capacity_proof": READINESS_ROOT.relative_to(EVIDENCE).as_posix() + "/package/capacity-proof-normalized.json",
            "packaged_capacity_proof_sha256": sha256_file(READINESS_ROOT / "package/capacity-proof-normalized.json"),
            "machine_triage_receipt_sha256": sha256_file(
                REPO
                / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_rule24_capacity_blocker_triage_20260829/machine-receipt.json"
            ),
        },
        "official_gate": {
            "readiness_status": readiness_summary.get("status"),
            "capacity_status": readiness_summary.get("capacity_status"),
            "official_gate_status": readiness_summary.get("official_gate_status"),
            "official_blocked_fixture_status": readiness_summary.get("official_blocked_fixture_status"),
            "production_mutation": readiness_summary.get("production_mutation"),
            "canary_created": readiness_summary.get("canary_created"),
        },
        "host_reserve": {
            "filesystem": machine["host"]["filesystem"],
            "total_bytes": total,
            "free_bytes": free,
            "ten_percent_bytes": ten_percent,
            "twenty_gib_bytes": twenty_gib,
            "required_reserve_bytes": reserve,
            "margin_bytes": free - reserve,
            "shortfall_bytes": max(reserve - free, 0),
        },
        "policy": capacity_proof.get("policy") or capacity_receipt.get("policy"),
        "projection": {
            "retention_peak_bytes": retention_peak,
            "projected_free_after_retention_peak_bytes": projected_free,
            "required_reserve_bytes": reserve,
            "projected_margin_after_retention_peak_bytes": projected_free - reserve,
            "projected_shortfall_bytes": max(reserve - projected_free, 0),
        },
        "cycles": [
            {
                "cycle": cycle["cycle"],
                "before_bytes": cycle["before_bytes"],
                "after_bytes": cycle["after_bytes"],
                "growth_bytes": cycle["growth_bytes"],
                "host_free_before": cycle["host_free_before"],
                "host_free_after": cycle["host_free_after"],
                "rss_before": cycle["rss_before"],
                "rss_after": cycle["rss_after"],
                "swap_before": cycle["swap_before"],
                "swap_after": cycle["swap_after"],
                "rss_available": cycle["rss_available"],
                "swap_available": cycle["swap_available"],
            }
            for cycle in receipt["cycles"]
        ],
        "reclamation": receipt["reclamation"],
        "stop_loss": receipt["stop_loss"],
        "production_mutation": False,
        "launch_agent_stop_start": False,
        "reclaim_existing_files": False,
    }
    write_json(EVIDENCE / "resume-dfcb-rule24-normalized-proof.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["snapshot", "promotion", "normalized-rule24"])
    parser.add_argument("--label")
    parser.add_argument("--promotion-command", choices=["plan", "apply", "finalize", "status"])
    parser.add_argument("--expected-plan-digest")
    args = parser.parse_args()
    if args.command == "snapshot":
        if not args.label:
            raise SystemExit("--label is required")
        snapshot(args.label)
        return 0
    if args.command == "normalized-rule24":
        normalized_rule24()
        return 0
    if not args.promotion_command:
        raise SystemExit("--promotion-command is required")
    return run_promotion(args.promotion_command, args.expected_plan_digest)


if __name__ == "__main__":
    raise SystemExit(main())

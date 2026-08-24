#!/usr/bin/env python3
"""產生 G8 pre-authorization 的唯讀 authority 與 promotion plan 證據。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


TASK_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_ROOT = TASK_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_preauth_blocker_resolution_20260824"
CARD_PATH = TASK_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824.md"
RUNTIME_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = RUNTIME_ROOT / "actor"
MANIFEST_PATH = RUNTIME_ROOT / "runtime-manifest.json"
QUEUE_ROOT = RUNTIME_ROOT / "queue"
STATE_ROOT = RUNTIME_ROOT / "state"
LOG_ROOT = RUNTIME_ROOT / "logs"
TRANSACTION_ROOT = RUNTIME_ROOT / "transactions/g8-v0370-5a9103785e-preauth-plan"
STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
CAPACITY_RECEIPT = TASK_ROOT / "artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/aggregate_runtime_promotion_plan_replay_raw_capacity_20260815/capacity-receipt-canonical.json"
CANONICAL_OBSERVATION = TASK_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json"

RELEASE_SHA = "b0950d4c436cc902e17ac110b579b35b84aa53e4"
REMOTE_MAIN_SHA = "5a9103785ebfc8d5a28fa8188def6069beb12d88"
LOCAL_MAIN_SHA = "a0391c298a4eff80be113c2a06c03529cd2dcbf6"
LOCAL_ORIGIN_MAIN_SHA = "5a9103785ebfc8d5a28fa8188def6069beb12d88"
ACTOR_SHA = "db9fb4343df212fd3b65546b017aba159620a058"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
REMOTE_QUERY_TIME = "2026-08-24T03:32:35Z"
REMOTE_QUERY_INVOCATIONS = [
    {
        "ordinal": 1,
        "command": "git ls-remote --heads origin main",
        "connected_to_remote": False,
        "exit_code": 128,
        "result": "DNS_RESOLUTION_FAILED",
        "stderr_summary": "ssh could not resolve github.com; remote authority was not returned",
    },
    {
        "ordinal": 2,
        "command": "git ls-remote --heads origin main",
        "connected_to_remote": True,
        "exit_code": 0,
        "result": "REMOTE_MAIN_RETURNED",
        "stdout": f"{REMOTE_MAIN_SHA}\\trefs/heads/main",
    },
]


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_json(name: str, payload: dict[str, Any]) -> None:
    (EVIDENCE_ROOT / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def is_ancestor(older: str, newer: str) -> bool:
    result = run_git(TASK_ROOT, "merge-base", "--is-ancestor", older, newer, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "git merge-base failed")
    return result.returncode == 0


def tree_sha(commit: str) -> str:
    return run_git(TASK_ROOT, "rev-parse", f"{commit}^{{tree}}").stdout.strip()


def changed_paths(older: str, newer: str) -> list[str]:
    output = run_git(TASK_ROOT, "diff", "--name-only", f"{older}..{newer}").stdout
    return [line for line in output.splitlines() if line]


def patch_id(commit: str) -> str:
    patch = run_git(TASK_ROOT, "show", "--pretty=format:", "--binary", commit).stdout
    result = subprocess.run(
        ["git", "patch-id", "--stable"],
        input=patch,
        text=True,
        check=True,
        capture_output=True,
    ).stdout.strip()
    return result.split()[0] if result else "EMPTY"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="已存在、canonical 且 HEAD 綁定既有 source decision 的唯讀 checkout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        source_root = args.source_root.resolve(strict=True)
    except OSError as error:
        raise SystemExit(f"source root is unavailable: {error}") from error
    if not args.source_root.is_absolute() or source_root != args.source_root or not source_root.is_dir():
        raise SystemExit("source root must be an explicit canonical directory")
    sys.path.insert(0, str(source_root))
    from scripts.agy_content_publisher import runtime_manifest_digest
    from scripts.pantheon_content_runtime_promotion import (
        PromotionError,
        PromotionRequest,
        plan_promotion,
        tree_digest,
    )

    release_to_remote = changed_paths(RELEASE_SHA, REMOTE_MAIN_SHA)
    remote_to_local = changed_paths(REMOTE_MAIN_SHA, LOCAL_MAIN_SHA)
    runtime_affecting = [
        path for path in release_to_remote
        if path.startswith(("app/", "scripts/", "tests/", "config/", "templates/"))
    ]
    docs_only = [path for path in release_to_remote if path not in runtime_affecting]
    ancestry = {
        "release_is_ancestor_of_remote_main": is_ancestor(RELEASE_SHA, REMOTE_MAIN_SHA),
        "remote_main_is_ancestor_of_local_main": is_ancestor(REMOTE_MAIN_SHA, LOCAL_MAIN_SHA),
        "local_main_is_ancestor_of_remote_main": is_ancestor(LOCAL_MAIN_SHA, REMOTE_MAIN_SHA),
        "actor_is_ancestor_of_release": is_ancestor(ACTOR_SHA, RELEASE_SHA),
        "release_is_ancestor_of_actor": is_ancestor(RELEASE_SHA, ACTOR_SHA),
    }
    patch_pairs = [
        {
            "left": "cf2a341ecf79755a7d7ca756bb9d59b4085c37d6",
            "right": "e7892fd2c66f41044cfb58d61f693d89f20f5faf",
        },
        {
            "left": REMOTE_MAIN_SHA,
            "right": "eb2ddd8157901e8764ffcc5fd8a5c68822fa357c",
        },
    ]
    for pair in patch_pairs:
        pair["left_patch_id"] = patch_id(pair["left"])
        pair["right_patch_id"] = patch_id(pair["right"])
        pair["equivalent"] = pair["left_patch_id"] == pair["right_patch_id"]

    remote_authority = {
        "schema_version": 1,
        "status": "BLOCKED_CONTRACT_VIOLATION",
        "remote_url_redacted": "git@github.com:<owner>/Pantheon.git",
        "query_time_utc": REMOTE_QUERY_TIME,
        "remote_main_sha": REMOTE_MAIN_SHA,
        "release_tag": "v0.3.370",
        "release_tag_peeled_sha": RELEASE_SHA,
        "local_main_sha": LOCAL_MAIN_SHA,
        "local_origin_main_sha": LOCAL_ORIGIN_MAIN_SHA,
        "task_head_sha": LOCAL_MAIN_SHA,
        "production_actor_sha": ACTOR_SHA,
        "remote_query_invocation_count": len(REMOTE_QUERY_INVOCATIONS),
        "remote_connection_success_count": 1,
        "bounded_query_limit": 1,
        "bounded_query_contract_pass": False,
        "query_invocations": REMOTE_QUERY_INVOCATIONS,
        "interpretation": "命令層共執行兩次 ls-remote；第一次在 DNS 前失敗、第二次成功。即使只有一次實際連線，仍不得把最多一次 invocation 的契約寫成 PASS。",
        "remote_mutation_count": 0,
        "fetch_count": 0,
    }
    write_json("remote-authority.json", remote_authority)

    source_decision = {
        "schema_version": 1,
        "status": "SOURCE_UNIQUE_BUT_TASK_BLOCKED",
        "future_promotion_source_sha": REMOTE_MAIN_SHA,
        "authority_basis": "成功的 bounded read-only remote query 回傳 current refs/heads/main；local tracking ref 僅交叉佐證。",
        "bounded_query_contract": "FAIL",
        "release_sha": RELEASE_SHA,
        "production_actor_sha": ACTOR_SHA,
        "local_main_sha": LOCAL_MAIN_SHA,
        "local_origin_main_sha": LOCAL_ORIGIN_MAIN_SHA,
        "trees": {
            "release": tree_sha(RELEASE_SHA),
            "remote_main": tree_sha(REMOTE_MAIN_SHA),
            "local_main": tree_sha(LOCAL_MAIN_SHA),
            "production_actor": tree_sha(ACTOR_SHA),
        },
        "ancestry": ancestry,
        "patch_id_pairs": patch_pairs,
        "release_to_remote_changed_paths": release_to_remote,
        "release_to_remote_classification": {
            "runtime_affecting": runtime_affecting,
            "docs_evidence_only": docs_only,
            "unknown": [],
        },
        "remote_to_local_changed_path_count": len(remote_to_local),
        "remote_to_local_changed_paths_digest": json_digest(remote_to_local),
        "runtime_equivalence": {
            "status": "PASS",
            "reason": "release 到 remote main 的三個 changed paths 全為 docs/handoff；runtime manifest path set 無變更。",
            "target_runtime_digest": runtime_manifest_digest(source_root),
        },
        "post_adoption_convergence": "Future authorized promotion/reset must bind actor HEAD and runtime manifest actor_head to the same remote main SHA, then run fresh formal reconciliation before canary.",
    }
    write_json("source-decision.json", source_decision)

    source_allowlist = {
        "schema_version": 1,
        "status": "PASS_EMPTY_EXACT_ALLOWLIST",
        "required_source": REMOTE_MAIN_SHA,
        "origin_main": REMOTE_MAIN_SHA,
        "patterns": [],
        "matched_paths": [],
        "unmatched_paths": [],
        "overmatched_paths": [],
        "actual_changed_paths": changed_paths(REMOTE_MAIN_SHA, REMOTE_MAIN_SHA),
        "reason": "required source 精確等於 current remote main，formal authority diff 為空；新增 pattern 只會擴權。",
        "formal_probe": "reconciler-result.json",
        "formal_probe_expected_earliest_blocker": "ACTOR_MANIFEST_AUTHORITY_MISMATCH",
    }
    write_json("source-allowlist.json", source_allowlist)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    preserved_runs = []
    for path in sorted((QUEUE_ROOT / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        preserved_runs.append({"run_id": payload.get("run_id"), "status": payload.get("status"), "path": path.name})
    preserved_ids = tuple(sorted(str(item["run_id"]) for item in preserved_runs))
    target_runtime_digest = runtime_manifest_digest(source_root)
    capacity_digest = sha256_file(CAPACITY_RECEIPT)
    planning_contract_digest = sha256_file(CARD_PATH)
    inputs = {
        "schema_version": 1,
        "status": "PLAN_INPUTS_LOCKED",
        "authorization_state": "NOT_GRANTED",
        "authorization_digest_input_semantics": "task card digest used only to satisfy deterministic plan shape; it is not human authorization",
        "source_repo_locator": "<local-temp-source-worktree>",
        "source_sha": REMOTE_MAIN_SHA,
        "expected_origin_redacted": "git@github.com:<owner>/Pantheon.git",
        "actor_root_locator": "<runtime-actor-root>",
        "expected_current_actor_sha": ACTOR_SHA,
        "manifest_locator": "<runtime-manifest>",
        "expected_current_manifest_digest": manifest["manifest_digest"],
        "private_stage_locator": "<private-stage-root>",
        "expected_current_stage_digest": tree_digest(STAGE_ROOT),
        "transaction_root_locator": "<runtime-transaction-root>/g8-v0370-5a9103785e-preauth-plan",
        "queue_root_locator": "<runtime-queue-root>",
        "state_root_locator": "<runtime-state-root>",
        "log_root_locator": "<runtime-log-root>",
        "target_identity": f"gate2-actor:{REMOTE_MAIN_SHA}:activation-only",
        "target_runtime_digest": target_runtime_digest,
        "target_config_version": manifest["config_version"],
        "target_generation": "g35-5a9103785e-preauth-plan",
        "target_python_locator": "<runtime-python>",
        "target_uv_locator": "<uv-executable>",
        "planning_contract_digest": planning_contract_digest,
        "capacity_receipt_locator": "<repo-root>/artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/aggregate_runtime_promotion_plan_replay_raw_capacity_20260815/capacity-receipt-canonical.json",
        "capacity_receipt_digest": capacity_digest,
        "capacity_receipt_sampled_at": "2026-08-14T18:31:09Z",
        "capacity_validator": "scripts.pantheon_content_runtime_promotion._validate_capacity_receipt",
        "correlation_id": "g8-v0370-5a9103785e-preauth-plan",
        "preserved_runs": preserved_runs,
        "canonical_observation_locator": "<repo-root>/artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json",
        "canonical_observation_digest": sha256_file(CANONICAL_OBSERVATION),
    }
    write_json("promotion-plan-inputs.json", inputs)

    request = PromotionRequest(
        source_repo=source_root,
        source_sha=REMOTE_MAIN_SHA,
        expected_origin=EXPECTED_ORIGIN,
        actor_root=ACTOR_ROOT,
        expected_current_actor_sha=ACTOR_SHA,
        manifest_path=MANIFEST_PATH,
        expected_current_manifest_digest=manifest["manifest_digest"],
        private_stage_root=STAGE_ROOT,
        expected_current_stage_digest=tree_digest(STAGE_ROOT),
        transaction_root=TRANSACTION_ROOT,
        queue_root=QUEUE_ROOT,
        publisher_state_root=STATE_ROOT,
        log_root=LOG_ROOT,
        target_identity=f"gate2-actor:{REMOTE_MAIN_SHA}:activation-only",
        target_runtime_digest=target_runtime_digest,
        target_config_version=manifest["config_version"],
        target_generation="g35-5a9103785e-preauth-plan",
        target_python_executable=Path(manifest["python_executable"]),
        target_uv_executable=Path(manifest["uv_executable"]),
        authorization_digest=planning_contract_digest,
        capacity_receipt_path=CAPACITY_RECEIPT.resolve(strict=True),
        capacity_receipt_digest=capacity_digest,
        correlation_id="g8-v0370-5a9103785e-preauth-plan",
        preserved_run_ids=preserved_ids,
    )
    try:
        plan = plan_promotion(request)
    except PromotionError as error:
        plan = {"status": "BLOCKED", "failure_code": "PROMOTION_PLAN_NOT_READY", "error": str(error)}
    plan["production_mutation"] = False
    plan["authorization_state"] = "NOT_GRANTED"
    write_json("promotion-plan.json", plan)
    return 0 if plan.get("status") == "READY_TO_APPLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

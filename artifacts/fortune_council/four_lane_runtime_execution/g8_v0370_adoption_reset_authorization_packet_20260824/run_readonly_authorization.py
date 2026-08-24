#!/usr/bin/env python3
"""以既有 plan_promotion 產生 G8 adoption/reset 唯讀授權證據。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_ROOT = Path(__file__).resolve().parent
CARD_PATH = REPO_ROOT / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "CARD-PANTHEON-G8-V0370-ADOPTION-RESET-AUTHORIZATION-PACKET-20260824.md"
)
PREAUTH_ROOT = REPO_ROOT / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "g8_v0370_preauth_blocker_resolution_20260824"
)
CAPACITY_RECEIPT = REPO_ROOT / (
    "artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/"
    "aggregate_runtime_promotion_plan_replay_raw_capacity_20260815/"
    "capacity-receipt-canonical.json"
)
RUNTIME_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = RUNTIME_ROOT / "actor"
MANIFEST_PATH = RUNTIME_ROOT / "runtime-manifest.json"
QUEUE_ROOT = RUNTIME_ROOT / "queue"
STATE_ROOT = RUNTIME_ROOT / "state"
LOG_ROOT = RUNTIME_ROOT / "logs"
TRANSACTION_ROOT = RUNTIME_ROOT / "transactions/g8-v0370-5a9103785e-adoption-auth-20260824"
STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")

SOURCE_SHA = "5a9103785ebfc8d5a28fa8188def6069beb12d88"
EXPECTED_ACTOR_SHA = "db9fb4343df212fd3b65546b017aba159620a058"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
TARGET_RUNTIME_DIGEST = "5554e075b0a6dcf97dd1cf431544c3456677b5d81174dcb8d660566dd82d5c92"
CORRELATION_ID = "g8-v0370-5a9103785e-adoption-auth-20260824"
TARGET_GENERATION = "g35-5a9103785e-adoption-auth-20260824"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name: str, payload: dict[str, Any]) -> None:
    (EVIDENCE_ROOT / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.pantheon_content_runtime_promotion import (
        PromotionError,
        PromotionRequest,
        plan_promotion,
        tree_digest,
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    preserved_runs: list[dict[str, str]] = []
    for path in sorted((QUEUE_ROOT / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        preserved_runs.append(
            {
                "path": path.name,
                "run_id": str(payload.get("run_id")),
                "status": str(payload.get("status")),
            }
        )
    preserved_ids = tuple(sorted(item["run_id"] for item in preserved_runs))
    authorization_digest = sha256_file(CARD_PATH)
    capacity_digest = sha256_file(CAPACITY_RECEIPT)
    source_checkout = Path(
        "/private/tmp/pantheon-g8-v0370-source-5a910-20260824"
    )
    source_checkout_available = source_checkout.is_dir()
    selected_source = source_checkout if source_checkout_available else REPO_ROOT

    inputs = {
        "schema_version": 1,
        "status": "CURRENT_INPUTS_LOCKED",
        "operation_level": "read_only",
        "production_mutation_authorized": False,
        "authorization_state": "NOT_GRANTED",
        "authorization_digest_semantics": (
            "卡片 digest 只固定 deterministic plan shape，不是人工 production 授權"
        ),
        "authorization_digest": authorization_digest,
        "source_sha": SOURCE_SHA,
        "source_checkout": str(selected_source),
        "canonical_target_source_checkout_available": source_checkout_available,
        "fallback_source_checkout_semantics": (
            "只用既有 activated worktree 呼叫正式 plan，預期由 source HEAD mismatch fail closed；"
            "不得建立 worktree、branch/ref 或修改 origin 來繞過缺口"
        ),
        "expected_origin_redacted": "git@github.com:<owner>/Pantheon.git",
        "actor_root": str(ACTOR_ROOT),
        "expected_current_actor_sha": EXPECTED_ACTOR_SHA,
        "manifest_path": str(MANIFEST_PATH),
        "expected_current_manifest_digest": manifest["manifest_digest"],
        "private_stage_root": str(STAGE_ROOT),
        "expected_current_stage_digest": tree_digest(STAGE_ROOT),
        "transaction_root": str(TRANSACTION_ROOT),
        "queue_root": str(QUEUE_ROOT),
        "publisher_state_root": str(STATE_ROOT),
        "log_root": str(LOG_ROOT),
        "target_identity": f"gate2-actor:{SOURCE_SHA}:activation-only",
        "target_runtime_digest": TARGET_RUNTIME_DIGEST,
        "target_config_version": manifest["config_version"],
        "target_generation": TARGET_GENERATION,
        "target_python_executable": manifest["python_executable"],
        "target_uv_executable": manifest["uv_executable"],
        "capacity_receipt_path": str(CAPACITY_RECEIPT),
        "capacity_receipt_digest": capacity_digest,
        "correlation_id": CORRELATION_ID,
        "preserved_runs": preserved_runs,
        "remote_query_invocation_count": 0,
        "remote_git_mutation_count": 0,
    }
    write_json("current-plan-inputs.json", inputs)

    request = PromotionRequest(
        source_repo=selected_source,
        source_sha=SOURCE_SHA,
        expected_origin=EXPECTED_ORIGIN,
        actor_root=ACTOR_ROOT,
        expected_current_actor_sha=EXPECTED_ACTOR_SHA,
        manifest_path=MANIFEST_PATH,
        expected_current_manifest_digest=manifest["manifest_digest"],
        private_stage_root=STAGE_ROOT,
        expected_current_stage_digest=inputs["expected_current_stage_digest"],
        transaction_root=TRANSACTION_ROOT,
        queue_root=QUEUE_ROOT,
        publisher_state_root=STATE_ROOT,
        log_root=LOG_ROOT,
        target_identity=inputs["target_identity"],
        target_runtime_digest=TARGET_RUNTIME_DIGEST,
        target_config_version=manifest["config_version"],
        target_generation=TARGET_GENERATION,
        target_python_executable=Path(manifest["python_executable"]),
        target_uv_executable=Path(manifest["uv_executable"]),
        authorization_digest=authorization_digest,
        capacity_receipt_path=CAPACITY_RECEIPT,
        capacity_receipt_digest=capacity_digest,
        correlation_id=CORRELATION_ID,
        preserved_run_ids=preserved_ids,
    )

    results: list[dict[str, Any]] = []
    for ordinal in (1, 2):
        try:
            result = plan_promotion(request)
        except PromotionError as error:
            result = {
                "schema_version": 1,
                "status": "BLOCKED",
                "failure_code": "CURRENT_PLAN_NOT_REPRODUCIBLE",
                "error": str(error),
            }
        result.update(
            {
                "run_ordinal": ordinal,
                "production_mutation": False,
                "authorization_state": "NOT_GRANTED",
                "forbidden_entrypoints_invoked": [],
            }
        )
        write_json(f"current-plan-run-{ordinal}.json", result)
        results.append(result)

    normalized = [
        {key: value for key, value in result.items() if key != "run_ordinal"}
        for result in results
    ]
    deterministic = normalized[0] == normalized[1]
    ready = deterministic and all(result.get("status") == "READY_TO_APPLY" for result in results)
    write_json(
        "current-plan-determinism.json",
        {
            "schema_version": 1,
            "status": "PASS" if deterministic else "FAIL",
            "deterministic": deterministic,
            "plan_ready_to_apply": ready,
            "run_statuses": [result.get("status") for result in results],
            "errors": [result.get("error") for result in results],
            "blocking_condition": None if ready else "CANONICAL_TARGET_SOURCE_CHECKOUT_UNAVAILABLE",
            "production_mutation": False,
            "remote_query_invocation_count": 0,
        },
    )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

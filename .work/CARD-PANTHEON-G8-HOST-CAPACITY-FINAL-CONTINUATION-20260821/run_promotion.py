#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

from scripts.agy_content_publisher import runtime_manifest_digest
from scripts.pantheon_content_runtime_promotion import (
    PromotionRequest,
    apply_promotion,
    finalize_promotion,
    plan_promotion,
    tree_digest,
)


CARD_ID = "CARD-PANTHEON-G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821"
WORK_ROOT = Path(".work") / CARD_ID
SOURCE_REPO = Path("/private/tmp/pantheon-g8-final-source-4c16-continuation-20260821")
SOURCE_SHA = "4c16a2f4ab81865ba854cff6cf79a82dfe700c71"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
CURRENT_ACTOR_SHA = "b1719c0d6243c7ec6372889405a846ccd1b666ed"
MANIFEST_PATH = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json")
CURRENT_MANIFEST_DIGEST = "d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf"
PRIVATE_STAGE_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue")
PUBLISHER_STATE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state")
LOG_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/logs")
TRANSACTION_ROOT = Path(
    "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/"
    "g8-host-capacity-final-continuation-20260821"
)
PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
UV = Path("/Users/mattkuo/.local/bin/uv")
EXACT_RUN_ID = "auto-i18n-en-614aa4dc3542ab2c5637"
CAPACITY_RECEIPT = (
    Path.cwd()
    / WORK_ROOT
    / "capacity-receipt.json"
)
CORRELATION_ID = "G8-HOST-CAPACITY-FINAL-CONTINUATION-20260821"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserved_run_ids() -> tuple[str, ...]:
    ids: list[str] = []
    for path in QUEUE_ROOT.joinpath("runs").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_id = payload.get("run_id")
        if not isinstance(run_id, str):
            raise RuntimeError(f"run_id missing from {path}")
        ids.append(run_id)
    return tuple(sorted(ids))


def build_request() -> PromotionRequest:
    capacity_digest = sha256_file(CAPACITY_RECEIPT)
    target_runtime_digest = runtime_manifest_digest(SOURCE_REPO)
    authorization_digest = hashlib.sha256(
        "\n".join(
            (
                CARD_ID,
                SOURCE_SHA,
                CURRENT_ACTOR_SHA,
                EXACT_RUN_ID,
                capacity_digest,
            )
        ).encode("utf-8")
    ).hexdigest()
    return PromotionRequest(
        source_repo=SOURCE_REPO,
        source_sha=SOURCE_SHA,
        expected_origin=EXPECTED_ORIGIN,
        actor_root=ACTOR_ROOT,
        expected_current_actor_sha=CURRENT_ACTOR_SHA,
        manifest_path=MANIFEST_PATH,
        expected_current_manifest_digest=CURRENT_MANIFEST_DIGEST,
        private_stage_root=PRIVATE_STAGE_ROOT,
        expected_current_stage_digest=tree_digest(PRIVATE_STAGE_ROOT),
        transaction_root=TRANSACTION_ROOT,
        queue_root=QUEUE_ROOT,
        publisher_state_root=PUBLISHER_STATE_ROOT,
        log_root=LOG_ROOT,
        target_identity=f"gate2-actor:{SOURCE_SHA}:activation-only",
        target_runtime_digest=target_runtime_digest,
        target_config_version="formal-runtime-v3-model-route-v1",
        target_generation="g31-4c16a2f4-20260821T180000Z",
        target_python_executable=PYTHON,
        target_uv_executable=UV,
        authorization_digest=authorization_digest,
        capacity_receipt_path=CAPACITY_RECEIPT.resolve(strict=True),
        capacity_receipt_digest=capacity_digest,
        correlation_id=CORRELATION_ID,
        preserved_run_ids=preserved_run_ids(),
    )


def request_receipt(request: PromotionRequest) -> dict:
    return {
        "schema_version": 1,
        "card_id": CARD_ID,
        "source_repo": str(request.source_repo),
        "source_sha": request.source_sha,
        "expected_current_actor_sha": request.expected_current_actor_sha,
        "expected_current_manifest_digest": request.expected_current_manifest_digest,
        "expected_current_stage_digest": request.expected_current_stage_digest,
        "transaction_root": str(request.transaction_root),
        "target_identity": request.target_identity,
        "target_runtime_digest": request.target_runtime_digest,
        "target_config_version": request.target_config_version,
        "target_generation": request.target_generation,
        "target_python_executable": str(request.target_python_executable),
        "target_uv_executable": str(request.target_uv_executable),
        "capacity_receipt": str(request.capacity_receipt_path),
        "capacity_receipt_digest": request.capacity_receipt_digest,
        "authorization_digest": request.authorization_digest,
        "correlation_id": request.correlation_id,
        "preserved_run_count": len(request.preserved_run_ids),
        "authorized_exact_run_present": EXACT_RUN_ID in request.preserved_run_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("plan", "apply-finalize"))
    args = parser.parse_args()
    request = build_request()
    write_json(WORK_ROOT / "promotion-request.json", request_receipt(request))
    if args.phase == "plan":
        result = plan_promotion(request)
        compact = {
            "schema_version": 1,
            "status": result["status"],
            "plan_digest": result["plan_digest"],
            "target_manifest_digest": result["target_manifest_digest"],
            "target_actor_sha": result["target_actor_sha"],
            "target_generation": request.target_generation,
            "queue_snapshot_digest": result["queue_snapshot_digest"],
            "preserved_run_count": len(request.preserved_run_ids),
            "capacity_receipt_digest": request.capacity_receipt_digest,
        }
        write_json(WORK_ROOT / "promotion-plan-result.json", compact)
        print(json.dumps(compact, sort_keys=True))
        return 0 if compact["status"] == "READY_TO_APPLY" else 1
    plan_path = WORK_ROOT / "promotion-plan-result.json"
    plan_digest = json.loads(plan_path.read_text(encoding="utf-8"))["plan_digest"]
    apply_result = apply_promotion(request, expected_plan_digest=plan_digest)
    write_json(WORK_ROOT / "promotion-apply-result.json", apply_result)
    final_result = finalize_promotion(request, expected_plan_digest=plan_digest)
    write_json(WORK_ROOT / "promotion-finalize-result.json", final_result)
    print(json.dumps({"apply": apply_result, "finalize": final_result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

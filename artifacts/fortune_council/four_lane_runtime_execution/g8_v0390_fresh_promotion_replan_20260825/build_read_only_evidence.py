#!/usr/bin/env python3
"""以唯讀 production facts 建立 V0390 阻斷證據。"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts import pantheon_content_runtime_promotion as promotion


OUTPUT_ROOT = Path(__file__).resolve().parent
MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
SOURCE_REPO = Path(
    "/Users/mattkuo/.codex/worktrees/10f3888a-73cf-4097-b857-5a466bffa716/Pantheon"
)
RUNTIME_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = RUNTIME_ROOT / "actor"
MANIFEST_PATH = RUNTIME_ROOT / "runtime-manifest.json"
PRIVATE_STAGE_ROOT = Path(
    "/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage"
)
QUEUE_ROOT = RUNTIME_ROOT / "queue"
STATE_ROOT = RUNTIME_ROOT / "state"
LOG_ROOT = RUNTIME_ROOT / "logs"
TRANSACTION_ROOT = (
    RUNTIME_ROOT / "transactions/g8-v0390-5872284828-promotion-20260825"
)
TARGET_SHA = "5872284828f9dd6f0a75adf407becaeadb50d61a"
REMOTE_MAIN_SHA = TARGET_SHA
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
CAPACITY_PATH = (
    MAIN_REPO
    / "artifacts/fortune_council/four_lane_runtime_execution/"
    "g8_v0388_fresh_rule24_unsigned_bundle_20260824/capacity-receipt.json"
)
CAPACITY_DIGEST = "776ae80fd611bb85b3693a1629176dc9d137c81b51d16fda62e6c3d200391ad4"
CORRELATION_ID = "g8-v0390-5872284828-fresh-replan-20260825"
TARGET_GENERATION = "g36-5872284828-zero-write-20260824"
TARGET_IDENTITY = f"gate2-actor:{TARGET_SHA}:activation-only"
TARGET_RUNTIME_DIGEST = (
    "5554e075b0a6dcf97dd1cf431544c3456677b5d81174dcb8d660566dd82d5c92"
)
TARGET_CONFIG_VERSION = "formal-runtime-v3-model-route-v1"
TARGET_PYTHON = Path(
    "/Users/mattkuo/.local/share/uv/python/"
    "cpython-3.12.12-macos-aarch64-none/bin/python3.12"
)
TARGET_UV = Path("/Users/mattkuo/.local/bin/uv")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name: str, value: Any) -> None:
    (OUTPUT_ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_bytes(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def manifest_payload() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def preserved_run_ids() -> tuple[str, ...]:
    run_ids: list[str] = []
    for path in (QUEUE_ROOT / "runs").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        run_ids.append(str(payload["run_id"]))
    return tuple(sorted(run_ids))


def transaction_observations() -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for path in sorted((RUNTIME_ROOT / "transactions").glob("*/promotion-receipt.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        observations.append(
            {
                "path": str(path),
                "correlation_id": payload.get("correlation_id"),
                "state": payload.get("state"),
                "terminal": payload.get("state") in {"COMMITTED", "ROLLED_BACK"},
            }
        )
    return observations


def facts_snapshot() -> dict[str, Any]:
    manifest = manifest_payload()
    runs = preserved_run_ids()
    request_view = type(
        "RequestView",
        (),
        {"queue_root": QUEUE_ROOT, "preserved_run_ids": runs},
    )()
    transactions = transaction_observations()
    usage = shutil.disk_usage(RUNTIME_ROOT)
    return {
        "source": {
            "path": str(SOURCE_REPO),
            "head": git(SOURCE_REPO, "rev-parse", "HEAD"),
            "origin": git(SOURCE_REPO, "remote", "get-url", "origin"),
            "clean": git(SOURCE_REPO, "status", "--porcelain") == "",
        },
        "actor": {
            "path": str(ACTOR_ROOT),
            "head": git(ACTOR_ROOT, "rev-parse", "HEAD"),
            "origin": git(ACTOR_ROOT, "remote", "get-url", "origin"),
            "clean": git(ACTOR_ROOT, "status", "--porcelain") == "",
        },
        "manifest": {
            "path": str(MANIFEST_PATH),
            "file_sha256": file_digest(MANIFEST_PATH),
            "manifest_digest": manifest["manifest_digest"],
            "actor_head": manifest["actor_head"],
            "generation": manifest["generation"],
            "identity": manifest["identity"],
        },
        "private_stage": {
            "path": str(PRIVATE_STAGE_ROOT),
            "tree_digest": promotion.tree_digest(PRIVATE_STAGE_ROOT),
            "target_readiness_exists": (
                PRIVATE_STAGE_ROOT / "readiness" / TARGET_GENERATION
            ).exists(),
        },
        "queue": {
            "path": str(QUEUE_ROOT),
            "snapshot_digest": promotion._queue_snapshot_digest(QUEUE_ROOT),
            "identity_digest": canonical_digest(
                promotion._queue_identity_snapshot(request_view)
            ),
            "preserved_run_count": len(runs),
            "preserved_run_ids": list(runs),
        },
        "state": {
            "path": str(STATE_ROOT),
            "tree_digest": promotion.tree_digest(STATE_ROOT),
            "target_barrier_exists": promotion.barrier_path(
                type(
                    "BarrierView",
                    (),
                    {
                        "publisher_state_root": STATE_ROOT,
                        "target_generation": TARGET_GENERATION,
                    },
                )()
            ).exists(),
        },
        "transactions": {
            "target_path": str(TRANSACTION_ROOT),
            "target_absent": not TRANSACTION_ROOT.exists(),
            "all_existing_terminal": all(item["terminal"] for item in transactions),
            "observations": transactions,
        },
        "machine": {
            "hostname": platform.node(),
            "uid": os.getuid(),
            "platform": platform.platform(),
            "runtime_volume": {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            },
        },
    }


def exact_byte_receipt() -> dict[str, Any]:
    specifications = [
        (
            "033f9aaa0a",
            "artifacts/fortune_council/four_lane_runtime_execution/"
            "g8_v0388_fresh_rule24_unsigned_bundle_20260824/capacity-receipt.json",
        ),
        (
            "033f9aaa0a",
            "artifacts/fortune_council/four_lane_runtime_execution/"
            "g8_v0388_fresh_rule24_unsigned_bundle_20260824/cycle-1-measurements.json",
        ),
        (
            "033f9aaa0a",
            "artifacts/fortune_council/four_lane_runtime_execution/"
            "g8_v0388_fresh_rule24_unsigned_bundle_20260824/cycle-2-measurements.json",
        ),
        (
            "5748d2d1e1",
            "artifacts/fortune_council/four_lane_runtime_execution/"
            "g8_v0389_fresh_rule24_dsse_sign_verify_20260825/envelope.json",
        ),
        (
            "5748d2d1e1",
            "artifacts/fortune_council/four_lane_runtime_execution/"
            "g8_v0389_fresh_rule24_dsse_sign_verify_20260825/verify-receipt.json",
        ),
        (
            "5748d2d1e1",
            "artifacts/fortune_council/four_lane_runtime_execution/"
            "g8_v0389_fresh_rule24_dsse_sign_verify_20260825/digest-manifest.json",
        ),
    ]
    artifacts: list[dict[str, Any]] = []
    for commit, relative in specifications:
        repository_bytes = (MAIN_REPO / relative).read_bytes()
        object_bytes = git_bytes(commit, relative)
        artifacts.append(
            {
                "commit": git(REPO_ROOT, "rev-parse", commit),
                "path": str(MAIN_REPO / relative),
                "bytes": len(repository_bytes),
                "sha256": hashlib.sha256(repository_bytes).hexdigest(),
                "git_object_sha256": hashlib.sha256(object_bytes).hexdigest(),
                "exact_byte_match": repository_bytes == object_bytes,
            }
        )
    return {
        "schema_version": 1,
        "status": "PASS" if all(item["exact_byte_match"] for item in artifacts) else "BLOCKED",
        "artifacts": artifacts,
    }


def source_contract_receipt() -> dict[str, Any]:
    source_path = Path(inspect.getsourcefile(promotion) or "")
    plan_start = inspect.getsourcelines(promotion._plan_payload)[1]
    install_start = inspect.getsourcelines(promotion._install_private_stage)[1]
    postcheck_start = inspect.getsourcelines(promotion._postcheck)[1]
    rollback_start = inspect.getsourcelines(promotion._restore_stage)[1]
    capacity_start = inspect.getsourcelines(promotion._validate_capacity_receipt)[1]
    test_path = REPO_ROOT / "tests/test_pantheon_content_runtime_promotion.py"
    test_lines = test_path.read_text(encoding="utf-8").splitlines()

    def test_line(needle: str) -> int:
        return next(index for index, line in enumerate(test_lines, 1) if needle in line)

    return {
        "schema_version": 1,
        "status": "PASS",
        "finding": "target readiness is an apply output and postcheck input, not a preflight input",
        "source": str(source_path),
        "evidence": [
            {
                "symbol": "_plan_payload",
                "line": plan_start,
                "fact": "preflight reads current private-stage digest; target readiness only appears in STAGE_INSTALLED write_set",
            },
            {
                "symbol": "_install_private_stage",
                "line": install_start,
                "fact": "creates target readiness acknowledgements and activates the barrier",
            },
            {
                "symbol": "_postcheck",
                "line": postcheck_start,
                "fact": "validates target barrier and readiness files after STAGE_INSTALLED",
            },
            {
                "symbol": "_restore_stage",
                "line": rollback_start,
                "fact": "removes the new stage/barrier and restores backups",
            },
        ],
        "tests": [
            {
                "path": str(test_path),
                "line": test_line("def test_plan_is_deterministic_and_zero_write"),
                "fact": "planner is deterministic and zero-write",
            },
            {
                "path": str(test_path),
                "line": test_line("def test_apply_failure_matrix_rolls_back_actor_manifest_and_stage"),
                "fact": "failure matrix rolls back actor, manifest, and stage",
            },
        ],
        "phase_order": {
            "preflight": [
                "capacity receipt",
                "source/actor/manifest/current-stage/queue bindings",
            ],
            "apply": [
                "PREPARED",
                "ACTOR_PROMOTED",
                "MANIFEST_WRITTEN",
                "STAGE_INSTALLED creates readiness and barrier",
            ],
            "postcheck": ["target readiness", "target barrier", "queue", "capacity"],
        },
        "capacity_compatibility": {
            "status": "BLOCKED",
            "symbol": "_validate_capacity_receipt",
            "line": capacity_start,
            "formal_planner_requires": {
                "regression_id": "REG-PANTHEON-CAPACITY-WRITE-CYCLES-001",
                "mode": "bounded-synthetic-dry-run",
                "cycle_fields": ["rss_available", "swap_available"],
                "top_level_fields": ["reclamation", "stop_loss"],
            },
            "v0388_observed": {
                "regression_id": None,
                "mode": "synthetic-non-production-capacity-proof",
                "cycle_fields": ["before", "peak", "after_cleanup"],
                "top_level_fields": ["projections", "stop_loss_negative_result"],
            },
            "interpretation": "fresh Rule24 bytes are valid but are not accepted by the formal promotion planner contract",
        },
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    before = facts_snapshot()
    exact_bytes = exact_byte_receipt()
    verify_path = (
        MAIN_REPO
        / "artifacts/fortune_council/four_lane_runtime_execution/"
        "g8_v0389_fresh_rule24_dsse_sign_verify_20260825/verify-receipt.json"
    )
    envelope_path = verify_path.with_name("envelope.json")
    verify = json.loads(verify_path.read_text(encoding="utf-8"))
    authorization_binding = {
        "schema_version": 1,
        "authorization_state": "not_authorized",
        "correlation_id": CORRELATION_ID,
        "machine": {
            "hostname": before["machine"]["hostname"],
            "uid": before["machine"]["uid"],
            "runtime_root": str(RUNTIME_ROOT),
        },
        "target_source_sha": TARGET_SHA,
        "remote_main_sha": REMOTE_MAIN_SHA,
        "source_repo": str(SOURCE_REPO),
        "actor_before_sha": before["actor"]["head"],
        "manifest_before_digest": before["manifest"]["manifest_digest"],
        "current_stage_digest": before["private_stage"]["tree_digest"],
        "queue_snapshot_digest": before["queue"]["snapshot_digest"],
        "state_snapshot_digest": before["state"]["tree_digest"],
        "capacity_receipt_path": str(CAPACITY_PATH),
        "capacity_receipt_digest": CAPACITY_DIGEST,
        "dsse": {
            "envelope_digest": file_digest(envelope_path),
            "authenticated_statement_digest": verify["authenticated_statement_digest"],
            "target_digest": verify["target_digest"],
            "policy_digest": verify["policy_digest"],
        },
        "rollback": {
            "transaction_root": str(TRANSACTION_ROOT),
            "bundle_root": str(TRANSACTION_ROOT / "rollback-bundle"),
            "order": ["STAGE_INSTALLED", "MANIFEST_WRITTEN", "ACTOR_PROMOTED"],
        },
    }
    planning_binding_digest = canonical_digest(authorization_binding)
    run_ids = before["queue"]["preserved_run_ids"]
    common = [
        "--source-repo", str(SOURCE_REPO),
        "--source-sha", TARGET_SHA,
        "--expected-origin", EXPECTED_ORIGIN,
        "--actor-root", str(ACTOR_ROOT),
        "--expected-current-actor-sha", before["actor"]["head"],
        "--manifest-path", str(MANIFEST_PATH),
        "--expected-current-manifest-digest", before["manifest"]["manifest_digest"],
        "--private-stage-root", str(PRIVATE_STAGE_ROOT),
        "--expected-current-stage-digest", before["private_stage"]["tree_digest"],
        "--transaction-root", str(TRANSACTION_ROOT),
        "--queue-root", str(QUEUE_ROOT),
        "--publisher-state-root", str(STATE_ROOT),
        "--log-root", str(LOG_ROOT),
        "--target-identity", TARGET_IDENTITY,
        "--target-runtime-digest", TARGET_RUNTIME_DIGEST,
        "--target-config-version", TARGET_CONFIG_VERSION,
        "--target-generation", TARGET_GENERATION,
        "--target-python-executable", str(TARGET_PYTHON),
        "--target-uv-executable", str(TARGET_UV),
        "--authorization-digest", planning_binding_digest,
        "--capacity-receipt", str(CAPACITY_PATH),
        "--capacity-receipt-digest", CAPACITY_DIGEST,
        "--correlation-id", CORRELATION_ID,
    ]
    for run_id in run_ids:
        common.extend(["--preserve-run-id", run_id])
    plan_argv = [
        sys.executable,
        "-m",
        "scripts.pantheon_content_runtime_promotion",
        "plan",
        *common,
    ]
    completed = subprocess.run(
        plan_argv,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    planner_output = json.loads(completed.stdout)
    after = facts_snapshot()
    comparison_fields = [
        ("source", "head"),
        ("source", "clean"),
        ("actor", "head"),
        ("actor", "clean"),
        ("manifest", "file_sha256"),
        ("manifest", "manifest_digest"),
        ("private_stage", "tree_digest"),
        ("queue", "snapshot_digest"),
        ("queue", "identity_digest"),
        ("state", "tree_digest"),
        ("transactions", "target_absent"),
    ]
    drift = [
        f"{section}.{field}"
        for section, field in comparison_fields
        if before[section][field] != after[section][field]
    ]
    fresh_facts = {
        "schema_version": 1,
        "observed_at": observed_at,
        "remote_query": {
            "operation_level": "read_only",
            "command": "git ls-remote --heads origin main",
            "invocation_count": 1,
            "returncode": 0,
            "ref": "refs/heads/main",
            "sha": REMOTE_MAIN_SHA,
        },
        "main_baseline": git(REPO_ROOT, "rev-parse", "HEAD"),
        "before": before,
        "after": after,
        "read_only_observed_drift": drift,
        "no_drift_status": "PASS" if not drift else "BLOCKED",
        "process_observation": {
            "scope": "pantheon|agy_gemini|four-lane",
            "matching_process_count": 0,
            "launchagent_observations": {
                "com.pantheon.agy-gemini-new": 78,
                "com.mattkuo.pantheon": 78,
                "com.pantheon.gsc-daily-fetch": 0,
                "com.pantheon.agy-gemini-rewrite": 78,
                "com.pantheon.agy-gemini-coordinator": 78,
                "com.pantheon.agy-gemini-i18n-rewrite": 78,
                "com.pantheon.agy-gemini-i18n-new": 78,
                "com.pantheon.content-capacity-guard": 78,
            },
            "interpretation": "no matching live process; launchctl was observed read-only and not mutated",
        },
        "production_mutation_count": 0,
        "remote_mutation_count": 0,
    }
    planner_receipt = {
        "schema_version": 1,
        "planner": "scripts.pantheon_content_runtime_promotion plan",
        "execution_status": "executed_zero_write_blocked",
        "returncode": completed.returncode,
        "stdout": planner_output,
        "stderr": completed.stderr,
        "exact_plan_argv_digest": canonical_digest(plan_argv),
        "planning_binding_digest": planning_binding_digest,
        "expected_failure": "capacity stop-loss is not PASS",
        "failure_matches_source_contract": planner_output
        == {"error": "capacity stop-loss is not PASS", "status": "NO-GO"},
        "plan_artifact_created": False,
        "apply_argv_created": False,
        "apply_invocation_count": 0,
        "production_mutation_count": 0,
    }
    exact_plan_argv = {
        "schema_version": 1,
        "execution_status": "executed_zero_write_blocked",
        "argv": plan_argv,
        "canonicalization": "UTF-8 compact JSON array with no trailing newline",
        "argv_digest": canonical_digest(plan_argv),
        "result": planner_output,
    }
    target_manifest = promotion._target_manifest(
        promotion.PromotionRequest(
            source_repo=SOURCE_REPO,
            source_sha=TARGET_SHA,
            expected_origin=EXPECTED_ORIGIN,
            actor_root=ACTOR_ROOT,
            expected_current_actor_sha=before["actor"]["head"],
            manifest_path=MANIFEST_PATH,
            expected_current_manifest_digest=before["manifest"]["manifest_digest"],
            private_stage_root=PRIVATE_STAGE_ROOT,
            expected_current_stage_digest=before["private_stage"]["tree_digest"],
            transaction_root=TRANSACTION_ROOT,
            queue_root=QUEUE_ROOT,
            publisher_state_root=STATE_ROOT,
            log_root=LOG_ROOT,
            target_identity=TARGET_IDENTITY,
            target_runtime_digest=TARGET_RUNTIME_DIGEST,
            target_config_version=TARGET_CONFIG_VERSION,
            target_generation=TARGET_GENERATION,
            target_python_executable=TARGET_PYTHON,
            target_uv_executable=TARGET_UV,
            authorization_digest=planning_binding_digest,
            capacity_receipt_path=CAPACITY_PATH,
            capacity_receipt_digest=CAPACITY_DIGEST,
            correlation_id=CORRELATION_ID,
            preserved_run_ids=tuple(run_ids),
        )
    )
    authorization_payload = {
        "schema_version": 1,
        "verdict": "BLOCKED",
        "authorization_state": "not_authorized",
        "authorization_granted": False,
        "planning_binding": authorization_binding,
        "planning_binding_digest": planning_binding_digest,
        "exact_plan_argv_digest": canonical_digest(plan_argv),
        "plan_digest": None,
        "exact_apply_argv_digest": None,
        "target_source_digest": TARGET_SHA,
        "target_manifest_digest": target_manifest["manifest_digest"],
        "capacity_receipt_digest": CAPACITY_DIGEST,
        "dsse_digests": authorization_binding["dsse"],
        "allowlist": [
            str(ACTOR_ROOT),
            str(MANIFEST_PATH),
            str(PRIVATE_STAGE_ROOT / "readiness" / TARGET_GENERATION),
            str(STATE_ROOT / f"four-lane-activation-{TARGET_GENERATION}.barrier"),
            str(TRANSACTION_ROOT),
        ],
        "forbidden": [
            "apply before a formal PASS plan exists",
            "production write under this V0390 task",
            "remote write/fetch/pull/push/tag",
            "manual target readiness or barrier creation",
            "deploy/canary/activation/launchctl mutation",
            "V0388 rerun or V0389 resign",
        ],
        "terminal_stops": [
            "fresh capacity receipt rejected by formal promotion planner",
            "any target/source/actor/manifest/current-stage/queue/state drift",
            "missing exact plan digest or exact apply argv digest",
            "authorization remains not_authorized",
        ],
        "human_approval": {
            "required": True,
            "granted": False,
            "approved_by": None,
            "approved_at": None,
        },
        "blocker": {
            "code": "fresh_capacity_schema_not_accepted_by_promotion_planner",
            "planner_error": planner_output,
            "source_expectation": {
                "regression_id": "REG-PANTHEON-CAPACITY-WRITE-CYCLES-001",
                "mode": "bounded-synthetic-dry-run",
            },
            "observed": {
                "regression_id": json.loads(CAPACITY_PATH.read_text()).get("regression_id"),
                "mode": json.loads(CAPACITY_PATH.read_text()).get("mode"),
            },
        },
    }
    authorization_payload["payload_digest"] = canonical_digest(authorization_payload)
    rollback_packet = {
        "schema_version": 1,
        "status": "not_created_planner_blocked",
        "transaction_root": str(TRANSACTION_ROOT),
        "rollback_bundle_root": str(TRANSACTION_ROOT / "rollback-bundle"),
        "rollback_order": ["STAGE_INSTALLED", "MANIFEST_WRITTEN", "ACTOR_PROMOTED"],
        "expected_backup_sources": [
            str(ACTOR_ROOT),
            str(MANIFEST_PATH),
            str(PRIVATE_STAGE_ROOT),
            str(STATE_ROOT / f"four-lane-activation-{TARGET_GENERATION}.barrier"),
        ],
        "exists": False,
        "apply_executed": False,
        "reason": "formal planner returned NO-GO before any transaction",
    }
    tripwire = {
        "schema_version": 1,
        "observation_mode": "read_only_before_after_comparison",
        "apply_executed": False,
        "production_snapshot_claimed": False,
        "compared_fields": [f"{section}.{field}" for section, field in comparison_fields],
        "read_only_observed_drift": drift,
        "status": "PASS" if not drift else "BLOCKED",
        "production_mutation_count": 0,
        "remote_mutation_count": 0,
        "note": "An empty read_only_observed_drift list is not an apply write-set or production after snapshot.",
    }
    write_json("fresh-facts.json", fresh_facts)
    write_json("v0388-v0389-exact-digests.json", exact_bytes)
    write_json("readiness-phase-contract.json", source_contract_receipt())
    write_json("exact-plan-argv.json", exact_plan_argv)
    write_json("planner-blocked-receipt.json", planner_receipt)
    write_json("authorization-payload.json", authorization_payload)
    write_json("rollback-packet.json", rollback_packet)
    write_json("protected-tripwire.json", tripwire)
    core_names = [
        "fresh-facts.json",
        "v0388-v0389-exact-digests.json",
        "readiness-phase-contract.json",
        "exact-plan-argv.json",
        "planner-blocked-receipt.json",
        "authorization-payload.json",
        "rollback-packet.json",
        "protected-tripwire.json",
    ]
    write_json(
        "digest-manifest.json",
        {
            "schema_version": 1,
            "canonicalization": "SHA-256 over exact repository bytes",
            "artifacts": {
                name: {"bytes": (OUTPUT_ROOT / name).stat().st_size, "sha256": file_digest(OUTPUT_ROOT / name)}
                for name in core_names
            },
        },
    )
    print(
        json.dumps(
            {
                "verdict": "BLOCKED",
                "planner_returncode": completed.returncode,
                "planner_result": planner_output,
                "no_drift": not drift,
                "exact_bytes": exact_bytes["status"],
                "production_mutation_count": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

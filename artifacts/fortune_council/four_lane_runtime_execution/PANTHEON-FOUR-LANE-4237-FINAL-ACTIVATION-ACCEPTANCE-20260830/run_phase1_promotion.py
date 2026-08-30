#!/usr/bin/env python3
"""以 exact 54ad source 執行單一 fresh runtime promotion transaction。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


SOURCE = Path("/private/tmp/pantheon-empty-continuation-4237")
TASK = Path("/Users/mattkuo/Documents/Pantheon")
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR = RUNTIME / "actor"
MANIFEST = RUNTIME / "runtime-manifest.json"
STAGE = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
QUEUE = RUNTIME / "queue"
STATE = RUNTIME / "state"
LOGS = RUNTIME / "logs"
EVIDENCE = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830"
TARGET_SHA = "54ad8654675dbf729367a25a5093a52b379b2538"
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
CAPACITY = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-E01-G75-EN-REPLACEMENT-ACCEPTANCE-20260830/rule24-e01-host-readable-output.json"
SUPERSESSION = EVIDENCE / "authorized-base-supersession.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def command_receipt(argv: list[str], *, cwd: Path) -> dict:
    result = subprocess.run(argv, cwd=cwd, env={**os.environ, "PYTHONPATH": str(cwd)}, text=True, capture_output=True, check=False)
    parsed = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "argv": argv,
        "cwd": str(cwd),
        "actor_sha": TARGET_SHA,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result": parsed,
    }


def write(name: str, payload: dict) -> None:
    (EVIDENCE / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    sys.path.insert(0, str(SOURCE))
    from scripts.agy_content_publisher import runtime_manifest_digest
    from scripts.pantheon_content_runtime_promotion import tree_digest

    current = json.loads(MANIFEST.read_text(encoding="utf-8"))
    match = re.fullmatch(r"g(\d+)-.*", current["generation"])
    if not match:
        raise RuntimeError("current generation is invalid")
    generation_number = int(match.group(1)) + 1
    target_generation = f"g{generation_number}-54ad8654-empty-continuation-authority-20260830"
    correlation = "pantheon-four-lane-54ad-final-activation-20260830"
    transaction = RUNTIME / "transactions" / correlation
    preserved: list[str] = []
    for path in sorted((QUEUE / "runs").glob("*.json")):
        run_id = json.loads(path.read_text(encoding="utf-8")).get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("registry run identity is invalid")
        preserved.append(run_id)
    preserved = sorted(set(preserved))
    common = [
        "--source-repo", str(SOURCE),
        "--source-sha", TARGET_SHA,
        "--expected-origin", EXPECTED_ORIGIN,
        "--actor-root", str(ACTOR),
        "--expected-current-actor-sha", current["actor_head"],
        "--manifest-path", str(MANIFEST),
        "--expected-current-manifest-digest", current["manifest_digest"],
        "--private-stage-root", str(STAGE),
        "--expected-current-stage-digest", tree_digest(STAGE),
        "--transaction-root", str(transaction),
        "--queue-root", str(QUEUE),
        "--publisher-state-root", str(STATE),
        "--log-root", str(LOGS),
        "--target-identity", f"gate2-actor:{TARGET_SHA}:final-four-lane-activation-20260830",
        "--target-runtime-digest", runtime_manifest_digest(SOURCE),
        "--target-config-version", current["config_version"],
        "--target-generation", target_generation,
        "--target-python-executable", current["python_executable"],
        "--target-uv-executable", current["uv_executable"],
        "--authorization-digest", sha(SUPERSESSION),
        "--capacity-receipt", str(CAPACITY),
        "--capacity-receipt-digest", sha(CAPACITY),
        "--correlation-id", correlation,
    ]
    for run_id in preserved:
        common.extend(["--preserve-run-id", run_id])
    python = current["python_executable"]
    base = [python, "-B", "-m", "scripts.pantheon_content_runtime_promotion"]
    plan = command_receipt([*base, "plan", *common], cwd=SOURCE)
    write("phase-1-promotion-plan.json", plan)
    if plan["returncode"] != 0 or not isinstance(plan["result"], dict) or plan["result"].get("status") != "READY_TO_APPLY":
        print(json.dumps({"status": "BLOCKED", "phase": "plan", "result": plan["result"], "stderr": plan["stderr"]}, sort_keys=True))
        return 1
    plan_digest = plan["result"]["plan_digest"]
    apply = command_receipt([*base, "apply", *common, "--expected-plan-digest", plan_digest], cwd=SOURCE)
    write("phase-1-promotion-apply.json", apply)
    if apply["returncode"] != 0 or not isinstance(apply["result"], dict) or apply["result"].get("status") != "POSTCHECK_PASSED":
        print(json.dumps({"status": "BLOCKED", "phase": "apply", "result": apply["result"], "stderr": apply["stderr"]}, sort_keys=True))
        return 1
    finalize = command_receipt([*base, "finalize", *common, "--expected-plan-digest", plan_digest], cwd=SOURCE)
    write("phase-1-promotion-finalize.json", finalize)
    if finalize["returncode"] != 0 or not isinstance(finalize["result"], dict) or finalize["result"].get("status") != "COMMITTED":
        print(json.dumps({"status": "BLOCKED", "phase": "finalize", "result": finalize["result"], "stderr": finalize["stderr"]}, sort_keys=True))
        return 1
    status = command_receipt([*base, "status", *common], cwd=SOURCE)
    write("phase-1-promotion-status.json", status)
    new_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ok = (
        status["returncode"] == 0
        and isinstance(status["result"], dict)
        and status["result"].get("status") == "PASS"
        and status["result"].get("state") == "COMMITTED"
        and new_manifest.get("actor_head") == TARGET_SHA
        and new_manifest.get("generation") == target_generation
        and git(ACTOR, "rev-parse", "HEAD") == TARGET_SHA
        and git(ACTOR, "status", "--porcelain") == ""
    )
    summary = {
        "status": "PASS" if ok else "BLOCKED",
        "target_sha": TARGET_SHA,
        "generation": target_generation,
        "manifest_digest": new_manifest.get("manifest_digest"),
        "runtime_digest": new_manifest.get("runtime_digest"),
        "plan_digest": plan_digest,
        "preserved_run_count": len(preserved),
        "transaction": str(transaction),
    }
    write("phase-1-promotion-summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

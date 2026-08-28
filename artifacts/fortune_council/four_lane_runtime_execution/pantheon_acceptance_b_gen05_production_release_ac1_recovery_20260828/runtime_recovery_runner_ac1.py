#!/usr/bin/env python3
"""Run exact ac1 recovery/operator steps and save bounded evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


EVIDENCE_DIR = Path(
    "/Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/"
    "four_lane_runtime_execution/"
    "pantheon_acceptance_b_gen05_production_release_ac1_recovery_20260828"
)
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
PYTHON = "/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12"
MANIFEST = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json"
MANIFEST_DIGEST = "5edb5d5f0b1d8eebc2fbe0855127f83fc9022fea9175c082505e807a29225bfe"
GENERATION = "g59-ac1faef5-gen05-entrypoint-recovery-20260828"
QUEUE_ROOT = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue"
STATE_ROOT = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state"
RUN_ROOT = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs"
RUN_DIR = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
JOB_ID = "61a83c341d39c882d5eed8ea23b7f805a89085e3"
REQUEST_SHA256 = "61a83c341d39c882d5eed8ea23b7f805a89085e326700281a54dbc6b45f8e62b"
NAMESPACE = "f46cda9eaa9ded446bf8e6c6"
AUTHORITY_DIGEST = "d44a30713092c1721cffa1974661508a2a2d10367e7a736d77d8841e2053ce2c"
LEGACY_CORRELATION = f"legacy-null-correlation:{RUN_ID}"
I18N_NEW_PLIST = "/Users/mattkuo/Library/LaunchAgents/com.pantheon.agy-gemini-i18n-new.plist"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def capture(command: list[str], label: str, *, cwd: Path = ACTOR_ROOT) -> int:
    write_json(EVIDENCE_DIR / f"{label}-command.json", command)
    completed = subprocess.run(
        command,
        cwd=str(cwd),
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
            write_json(EVIDENCE_DIR / f"{label}.stdout.json", json.loads(completed.stdout))
        except json.JSONDecodeError:
            pass
    return completed.returncode


def barrier_prefix(service_label: str) -> list[str]:
    return [
        PYTHON,
        "-m",
        "scripts.pantheon_content_runtime_manifest",
        "barrier-exec",
        "--barrier",
        f"{STATE_ROOT}/four-lane-activation-{GENERATION}.barrier",
        "--expected-digest",
        MANIFEST_DIGEST,
        "--manifest",
        MANIFEST,
        "--service-label",
        service_label,
        "--ready-root",
        f"/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/{GENERATION}",
        "--timeout",
        "30",
        "--",
    ]


def replace_command(*, execute: bool) -> list[str]:
    command = [
        *barrier_prefix("com.pantheon.agy-gemini-coordinator"),
        PYTHON,
        "-m",
        "scripts.agy_gemini_coordinator",
        "--queue-root",
        QUEUE_ROOT,
        "--repo-root",
        str(ACTOR_ROOT),
        "--legacy-state-root",
        STATE_ROOT,
        "--legacy-run-root",
        RUN_ROOT,
        "replace-failed-external-job",
        RUN_DIR,
        "--job-queue-root",
        f"{QUEUE_ROOT}/lanes/i18n-new",
        "--lane",
        "i18n-new",
        "--run-id",
        RUN_ID,
        "--job-id",
        JOB_ID,
        "--request-sha256",
        REQUEST_SHA256,
        "--namespace",
        NAMESPACE,
        "--correlation-id",
        LEGACY_CORRELATION,
        "--failure-category",
        "INVALID_RECEIPT",
        "--error-code",
        "NO_ERROR_CODE",
        "--authority-digest",
        AUTHORITY_DIGEST,
    ]
    command.append("--execute" if execute else "--plan-only")
    return command


def coordinator_cycle_command() -> list[str]:
    return [
        *barrier_prefix("com.pantheon.agy-gemini-coordinator"),
        PYTHON,
        "-m",
        "scripts.agy_gemini_coordinator",
        "--queue-root",
        QUEUE_ROOT,
        "--repo-root",
        str(ACTOR_ROOT),
        "--legacy-state-root",
        STATE_ROOT,
        "--legacy-run-root",
        RUN_ROOT,
        "--lane-mode",
        "cycle",
        "--exact-run-id",
        RUN_ID,
    ]


def operator_i18n_new_command() -> list[str]:
    return [
        PYTHON,
        "-m",
        "scripts.agy_gemini_runner",
        "--exact-run-id",
        RUN_ID,
        "operator-exact-process-once",
        "--manifest",
        MANIFEST,
        "--expected-digest",
        MANIFEST_DIGEST,
        "--barrier",
        f"{STATE_ROOT}/four-lane-activation-{GENERATION}.barrier",
        "--service-label",
        "com.pantheon.agy-gemini-i18n-new",
        "--ready-root",
        f"/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/{GENERATION}",
        "--plist",
        I18N_NEW_PLIST,
        "--timeout",
        "30",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "step",
        choices=["replace-plan", "replace-execute", "coordinator-cycle", "operator-i18n-new"],
    )
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if args.step == "replace-plan":
        return capture(replace_command(execute=False), args.label)
    if args.step == "replace-execute":
        return capture(replace_command(execute=True), args.label)
    if args.step == "coordinator-cycle":
        return capture(coordinator_cycle_command(), args.label)
    return capture(operator_i18n_new_command(), args.label)


if __name__ == "__main__":
    raise SystemExit(main())

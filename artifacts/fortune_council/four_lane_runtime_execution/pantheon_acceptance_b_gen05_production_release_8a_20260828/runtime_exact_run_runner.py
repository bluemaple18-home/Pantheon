#!/usr/bin/env python3
"""Run the exact production coordinator cycle through the promoted barrier."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
EVIDENCE_DIR = MAIN_REPO / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "pantheon_acceptance_b_gen05_production_release_8a_20260828"
)
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
PYTHON = "/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12"
MANIFEST = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json"
MANIFEST_DIGEST = "3012fdc78422dbfe1534b1eb1d353decb72ab0bd430e8e17f86a8fe6c4c586f0"
GENERATION = "g56-8a50395f-gen05-dangling-registry-guard-release-20260828"
QUEUE_ROOT = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue"
STATE_ROOT = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state"
RUN_ROOT = "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    command = [
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
        "com.pantheon.agy-gemini-coordinator",
        "--ready-root",
        f"/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/{GENERATION}",
        "--timeout",
        "30",
        "--",
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
    write_json(EVIDENCE_DIR / "exact-run-command.json", command)
    completed = subprocess.run(command, cwd=str(ACTOR_ROOT), capture_output=True, text=True, check=False)
    (EVIDENCE_DIR / "exact-run.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE_DIR / "exact-run.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE_DIR / "exact-run.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
    if completed.stdout.strip().startswith("{"):
        try:
            write_json(EVIDENCE_DIR / "exact-run.stdout.json", json.loads(completed.stdout))
        except json.JSONDecodeError:
            pass
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

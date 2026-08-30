#!/usr/bin/env python3
"""Run exact 18b runtime retry/cycle commands and save bounded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
EVIDENCE_DIR = MAIN_REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_completion_18b_20260828"
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
QUEUE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue")
MANIFEST = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json")
BARRIER = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/four-lane-activation-g63-18b121fa-gen06-samegen-retry-20260828.barrier")
READY_ROOT = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/g63-18b121fa-gen06-samegen-retry-20260828")
MANIFEST_DIGEST = "61c67eaf7f8e06b93005e47cb52427b6307dbe0c2b303ae7d48aec1357b982b3"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(sha(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def command_for(kind: str) -> list[str]:
    preflight = json.loads((EVIDENCE_DIR / "retry-preflight-18b.json").read_text())
    run_dir = Path(preflight["run_dir"])
    digests = preflight["gen06_artifacts"]
    child = [
        str(PYTHON), "-m", "scripts.agy_gemini_coordinator", "--queue-root", str(QUEUE_ROOT),
        "retry-same-generation-locale-plan", str(run_dir), "--run-id", RUN_ID, "--generation", "6",
        "--expected-registry-digest", preflight["registry_digest"], "--expected-job-id", preflight["last_job_id"],
        "--expected-attempt-digest", digests["attempt"]["sha256"], "--expected-archive-digest", digests["archive"]["sha256"],
        "--expected-inbox-digest", digests["inbox"]["sha256"], "--expected-external-plan-digest", digests["external_plan"]["sha256"],
        "--expected-plan-operation-digest", digests["plan_operation"]["sha256"], "--expected-planning-result-digest", digests["planning_result"]["sha256"],
        "--expected-source-ref-map-digest", digests["source_ref_map"]["sha256"],
    ]
    if kind == "retry-execute":
        child.append("--execute")
    if kind == "cycle":
        child = [str(PYTHON), "-m", "scripts.agy_gemini_coordinator", "--queue-root", str(QUEUE_ROOT), "--repo-root", str(ACTOR_ROOT), "--lane-mode", "cycle", "--exact-run-id", RUN_ID]
    return [
        str(PYTHON), "-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec",
        "--barrier", str(BARRIER), "--expected-digest", MANIFEST_DIGEST, "--manifest", str(MANIFEST),
        "--service-label", "com.pantheon.agy-gemini-coordinator", "--ready-root", str(READY_ROOT), "--timeout", "30",
        "--", *child,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["retry-plan", "retry-execute", "cycle"])
    args = parser.parse_args()
    preflight = json.loads((EVIDENCE_DIR / "retry-preflight-18b.json").read_text())
    run_dir = Path(preflight["run_dir"])
    before = {"registry": sha(Path(preflight["state_path"])), "gen06_tree": tree_digest(run_dir / "generations/06")}
    command = command_for(args.kind)
    write_json(EVIDENCE_DIR / f"{args.kind}-command.json", command)
    completed = subprocess.run(command, cwd=str(ACTOR_ROOT), capture_output=True, text=True, check=False)
    (EVIDENCE_DIR / f"{args.kind}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE_DIR / f"{args.kind}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE_DIR / f"{args.kind}.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
    after = {"registry": sha(Path(preflight["state_path"])), "gen06_tree": tree_digest(run_dir / "generations/06")}
    write_json(EVIDENCE_DIR / f"{args.kind}-mutation-receipt.json", {"before": before, "after": after, "zero_write": before == after, "returncode": completed.returncode})
    if completed.stdout.strip().startswith("{"):
        try:
            write_json(EVIDENCE_DIR / f"{args.kind}.stdout.json", json.loads(completed.stdout))
        except json.JSONDecodeError:
            pass
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

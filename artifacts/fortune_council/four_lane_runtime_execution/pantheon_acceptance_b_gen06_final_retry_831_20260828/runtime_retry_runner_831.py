#!/usr/bin/env python3
"""Run exact 831 same-generation retry/cycle commands and save bounded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MAIN_REPO = Path("/Users/mattkuo/Documents/Pantheon")
EVIDENCE_DIR = MAIN_REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_final_retry_831_20260828"
ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
MANIFEST = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json")
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() and path.is_file() else None


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update((sha(path) or "").encode())
        digest.update(b"\0")
    return digest.hexdigest()


def snapshot(preflight: dict[str, object]) -> dict[str, object]:
    run_dir = Path(str(preflight["run_dir"]))
    queue_root = Path(str(preflight["queue_root"]))
    job = str(preflight["expected_job_id"])
    lane = queue_root / "lanes" / "i18n-new"
    paths = {
        "registry": Path(str(preflight["state_path"])),
        "external_plan": run_dir / "generations/06/external-plan.json",
        "plan_operation": run_dir / "generations/06/plan-operation.json",
        "planning_result": run_dir / "generations/06/planning-result.json",
        "source_ref_map": run_dir / "generations/06/source-ref-map.json",
        "archive": lane / "archive" / f"{job}.json",
        "inbox": lane / "inbox" / f"{job}.json",
        "attempt": lane / "production-attempts" / f"{job}.attempt",
    }
    return {
        "hashes": {key: sha(path) for key, path in paths.items()},
        "gen06_tree": tree_digest(run_dir / "generations/06"),
        "gen07_exists": (run_dir / "generations/07").exists(),
        "outbox": sorted(path.name for path in (lane / "outbox").glob("*.json")),
        "inbox_job_exists": paths["inbox"].exists(),
        "archive_job_exists": paths["archive"].exists(),
        "attempt_job_exists": paths["attempt"].exists(),
    }


def command_for(kind: str, preflight: dict[str, object]) -> list[str]:
    queue_root = str(preflight["queue_root"])
    run_dir = str(preflight["run_dir"])
    digests = preflight["gen06_artifacts"]
    child = [
        str(PYTHON), "-m", "scripts.agy_gemini_coordinator", "--queue-root", queue_root,
        "retry-same-generation-locale-plan", run_dir, "--run-id", RUN_ID, "--generation", "6",
        "--expected-registry-digest", str(preflight["registry_digest"]),
        "--expected-job-id", str(preflight["expected_job_id"]),
        "--expected-attempt-digest", digests["attempt"]["sha256"],
        "--expected-archive-digest", digests["archive"]["sha256"],
        "--expected-inbox-digest", digests["inbox"]["sha256"],
        "--expected-external-plan-digest", digests["external_plan"]["sha256"],
        "--expected-plan-operation-digest", digests["plan_operation"]["sha256"],
        "--expected-planning-result-digest", digests["planning_result"]["sha256"],
        "--expected-source-ref-map-digest", digests["source_ref_map"]["sha256"],
    ]
    if kind == "retry-execute":
        child.append("--execute")
    if kind == "cycle":
        child = [str(PYTHON), "-m", "scripts.agy_gemini_coordinator", "--queue-root", queue_root, "--repo-root", str(ACTOR_ROOT), "--lane-mode", "cycle", "--exact-run-id", RUN_ID]
    return [
        str(PYTHON), "-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec",
        "--barrier", str(preflight["barrier"]), "--expected-digest", str(preflight["manifest_digest"]),
        "--manifest", str(MANIFEST), "--service-label", "com.pantheon.agy-gemini-coordinator",
        "--ready-root", str(preflight["ready_root"]), "--timeout", "30",
        "--", *child,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["retry-plan", "retry-execute", "cycle"])
    args = parser.parse_args()
    preflight = json.loads((EVIDENCE_DIR / "retry-preflight-831.json").read_text())
    before = snapshot(preflight)
    command = command_for(args.kind, preflight)
    write_json(EVIDENCE_DIR / f"{args.kind}-command.json", command)
    completed = subprocess.run(command, cwd=str(ACTOR_ROOT), capture_output=True, text=True, check=False)
    (EVIDENCE_DIR / f"{args.kind}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE_DIR / f"{args.kind}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE_DIR / f"{args.kind}.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
    after = snapshot(preflight)
    write_json(EVIDENCE_DIR / f"{args.kind}-mutation-receipt.json", {"before": before, "after": after, "zero_write": before == after, "returncode": completed.returncode})
    if completed.stdout.strip().startswith("{"):
        try:
            write_json(EVIDENCE_DIR / f"{args.kind}.stdout.json", json.loads(completed.stdout))
        except json.JSONDecodeError:
            pass
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

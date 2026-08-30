#!/usr/bin/env python3
"""蒐集 4237 四線最終驗收的唯讀 Phase 0 authority snapshot。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
from typing import Any


SOURCE = Path("/private/tmp/pantheon-empty-continuation-4237")
TASK = Path("/Users/mattkuo/Documents/Pantheon")
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR = RUNTIME / "actor"
QUEUE = RUNTIME / "queue"
STATE = RUNTIME / "state"
MANIFEST = RUNTIME / "runtime-manifest.json"
STAGE = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
LIVE = Path("/Users/mattkuo/Library/LaunchAgents")
EVIDENCE = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830"
RUN_ID = "auto-i18n-en-aa637e1bf05d3ad21429-replacement-01"
RUN_DIR = QUEUE / "translation-runs" / RUN_ID
CANDIDATE = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830/candidate-repaired.json"
FORMAL = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-FORMAL-REREVIEW-20260830/formal-review-result.json"
FORMAL_REVIEW = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-FORMAL-REREVIEW-20260830/isolated-formal-runtime/translation-runs/auto-i18n-en-aa637e1bf05d3ad21429-replacement-01/review.json"
TARGET_SHA = "54ad8654675dbf729367a25a5093a52b379b2538"
REMOTE_HEAD = TARGET_SHA
LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.content-capacity-guard",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*argv: str, cwd: Path | None = None) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "argv": list(argv),
        "cwd": str(cwd) if cwd else None,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def git(repo: Path, *argv: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *argv], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def tree(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink()):
            files.append({
                "path": path.relative_to(root).as_posix(),
                "sha256": sha(path),
                "bytes": path.stat().st_size,
            })
    digest = hashlib.sha256()
    for item in files:
        digest.update(item["path"].encode())
        digest.update(b"\0")
        digest.update(item["sha256"].encode())
        digest.update(b"\0")
    return {
        "root": str(root),
        "file_count": len(files),
        "bytes": sum(item["bytes"] for item in files),
        "digest": digest.hexdigest(),
        "files": files,
    }


def queue_surface() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite"):
        result[lane] = {}
        for box in ("outbox", "processing", "inbox"):
            root = QUEUE / "lanes" / lane / box
            result[lane][box] = tree(root)
    return result


def services() -> dict[str, Any]:
    result: dict[str, Any] = {}
    uid = os.getuid()
    for label in LABELS:
        live = LIVE / f"{label}.plist"
        staged = STAGE / f"{label}.plist"
        launch = run("launchctl", "print", f"gui/{uid}/{label}")
        item: dict[str, Any] = {
            "loaded": launch["returncode"] == 0,
            "launchctl_returncode": launch["returncode"],
            "live_plist": str(live),
            "live_exists": live.is_file(),
            "live_sha256": sha(live) if live.is_file() else None,
            "staged_plist": str(staged),
            "staged_exists": staged.is_file(),
            "staged_sha256": sha(staged) if staged.is_file() else None,
        }
        if live.is_file():
            payload = plistlib.loads(live.read_bytes())
            item["live_label"] = payload.get("Label")
            item["live_program_arguments"] = payload.get("ProgramArguments")
            env = payload.get("EnvironmentVariables") or {}
            item["live_runtime_identity"] = {
                key: env.get(key)
                for key in (
                    "PANTHEON_RUNTIME_ACTOR_HEAD",
                    "PANTHEON_RUNTIME_ACTOR_ROOT",
                    "PANTHEON_RUNTIME_MANIFEST_DIGEST",
                    "PANTHEON_RUNTIME_GENERATION",
                    "PANTHEON_RUNTIME_CODE_DIGEST",
                )
            }
        result[label] = item
    return result


def registry_summary() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted((QUEUE / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.append({
            "path": path.name,
            "sha256": sha(path),
            "run_id": payload.get("run_id"),
            "status": payload.get("status"),
            "lane": payload.get("lane"),
            "mode": payload.get("mode"),
        })
    target = [item for item in records if item["run_id"] == RUN_ID]
    return {"count": len(records), "target_matches": target, "records": records}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    barrier = STATE / f"four-lane-activation-{manifest['generation']}.barrier"
    disk = shutil.disk_usage(RUNTIME)
    candidate_payload = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    formal_payload = json.loads(FORMAL.read_text(encoding="utf-8"))
    stage_files = tree(STAGE)
    snapshot = {
        "schema_version": 1,
        "status": "PASS",
        "authorized_target": TARGET_SHA,
        "remote_origin_main": REMOTE_HEAD,
        "source": {
            "root": str(SOURCE.resolve(strict=True)),
            "head": git(SOURCE, "rev-parse", "HEAD"),
            "status_porcelain": git(SOURCE, "status", "--porcelain"),
            "origin": git(SOURCE, "remote", "get-url", "origin"),
        },
        "current_runtime": {
            "actor_root": str(ACTOR.resolve(strict=True)),
            "actor_head": git(ACTOR, "rev-parse", "HEAD"),
            "actor_status_porcelain": git(ACTOR, "status", "--porcelain"),
            "manifest": manifest,
            "manifest_sha256": sha(MANIFEST),
            "barrier_path": str(barrier),
            "barrier_sha256": sha(barrier),
            "barrier": json.loads(barrier.read_text(encoding="utf-8")),
            "stage": stage_files,
        },
        "services": services(),
        "queue_surface": queue_surface(),
        "registry": registry_summary(),
        "replacement": {
            "run_id": RUN_ID,
            "run_tree": tree(RUN_DIR),
            "attempt_directories": sorted(path.name for path in (RUN_DIR / "attempts").iterdir() if path.is_dir()),
            "generation_root_exists": (RUN_DIR / "generations").exists(),
            "continuation_root_exists": (RUN_DIR / "continuation").exists(),
            "root_candidate_sha256": sha(RUN_DIR / "candidate.json"),
            "root_review_sha256": sha(RUN_DIR / "review.json"),
            "attempt03_candidate_sha256": sha(RUN_DIR / "attempts/03/candidate.json"),
            "attempt03_review_sha256": sha(RUN_DIR / "attempts/03/review.json"),
            "repaired_candidate_file": str(CANDIDATE),
            "repaired_candidate_file_sha256": sha(CANDIDATE),
            "repaired_article_id": candidate_payload["articles"][0]["article_id"],
            "formal_result_file": str(FORMAL),
            "formal_result_sha256": sha(FORMAL),
            "formal_review_sha256": sha(FORMAL_REVIEW),
            "formal_verdict": formal_payload.get("exit_verdict"),
            "formal_findings": formal_payload.get("findings"),
        },
        "publisher": {
            "ledger_path": str(STATE / "ledger.json"),
            "ledger_sha256": sha(STATE / "ledger.json"),
            "push_prepared_matches": [
                {"path": str(path), "sha256": sha(path)}
                for path in sorted(STATE.rglob("*"))
                if path.is_file() and "unresolved" in path.name.lower() and RUN_ID in path.read_text(encoding="utf-8", errors="ignore")
            ],
        },
        "public_content": tree(SOURCE / "app/web/static"),
        "host": {
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_free": disk.free,
            "reserve_required": max(20 * 1024**3, disk.total // 10),
            "swap": run("sysctl", "vm.swapusage"),
            "vm_stat": run("vm_stat"),
        },
    }
    if (
        snapshot["source"]["head"] != TARGET_SHA
        or snapshot["source"]["status_porcelain"] != ""
        or REMOTE_HEAD != TARGET_SHA
        or snapshot["current_runtime"]["actor_status_porcelain"] != ""
        or snapshot["replacement"]["attempt_directories"] != ["01", "02", "03"]
        or snapshot["replacement"]["generation_root_exists"]
        or (
            snapshot["replacement"]["continuation_root_exists"]
            and any((RUN_DIR / "continuation").iterdir())
        )
        or snapshot["replacement"]["repaired_candidate_file_sha256"] != "26dd6ccf15a37a165f2ec11f9dd0220db26b9cdbc7fc8b2641b50b551e6731d1"
        or snapshot["replacement"]["formal_verdict"] != "APPROVE_READY_FOR_STAGING"
        or snapshot["replacement"]["formal_findings"] != []
        # g75 promotion preserved 136 runs；其後唯一 exact replacement 新增一筆，
        # 因此本卡 immutable baseline 必須為 137，而不是沿用 promotion 前計數。
        or snapshot["registry"]["count"] != 137
        or len(snapshot["registry"]["target_matches"]) != 1
        or any(snapshot["queue_surface"][lane][box]["file_count"] for lane in snapshot["queue_surface"] for box in ("outbox", "processing"))
        or snapshot["publisher"]["push_prepared_matches"]
        or disk.free < snapshot["host"]["reserve_required"]
    ):
        snapshot["status"] = "BLOCKED"
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    output = EVIDENCE / "phase-0-current-authority-snapshot.json"
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    protected = {
        "schema_version": 1,
        "snapshot_phase": "before",
        "queue": tree(QUEUE),
        "state": tree(STATE),
        "runtime_manifest": {"path": str(MANIFEST), "sha256": sha(MANIFEST), "bytes": MANIFEST.stat().st_size},
        "stage": stage_files,
        "live_plists": {
            label: ({"sha256": sha(LIVE / f"{label}.plist"), "bytes": (LIVE / f"{label}.plist").stat().st_size} if (LIVE / f"{label}.plist").is_file() else None)
            for label in LABELS
        },
        "production_static": tree(SOURCE / "app/web/static"),
    }
    (EVIDENCE / "protected-bytes-before.json").write_text(
        json.dumps(protected, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": snapshot["status"], "output": str(output), "registry_count": snapshot["registry"]["count"], "loaded_services": sum(1 for item in snapshot["services"].values() if item["loaded"]), "queue_active": sum(snapshot["queue_surface"][lane][box]["file_count"] for lane in snapshot["queue_surface"] for box in ("outbox", "processing")), "manifest_digest": manifest["manifest_digest"]}, sort_keys=True))
    return 0 if snapshot["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

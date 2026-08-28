#!/usr/bin/env python3
"""重現 formal-approved edited candidate 無正式 production staging 入口。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_seo_copy_pipeline as pipeline


RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
EXPECTED_ARTICLE_SHA256 = "a64d8a33b0b70933134452491c10058e820dd93d5c748d3cc220bbfc25da7b9c"
EXPECTED_ROOT_CANDIDATE_SHA256 = "09aa9ea8187a5884dd255d8d51020c32bbad4a1747c6c6f86b50973e3630ecee"
EXPECTED_ROOT_REVIEW_SHA256 = "4176d9306c5e49e5ab4bbd3860ed5eb2669c9490a506d20c4d7ef7e321bce3c9"
EXPECTED_CONTINUATION_STATE_SHA256 = "9b0b90943928d255454cab496dba502701e046446579a193820ac0205145818b"
EXPECTED_QUEUE_STATE_SHA256 = "397afcc959e1b8383541241fd3aed231e6b2545d6173b60155d8b8ed61d150ca"
EXPECTED_PUBLISHER_LEDGER_SHA256 = "0fc223530e1f8af7d0b495e28e4a336471a2349ceabd93074459827cbe93d8f9"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(root: Path) -> str | None:
    if not root.exists():
        return None
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        if path.is_symlink():
            digest.update(b"SYMLINK")
            digest.update(path.readlink().as_posix().encode("utf-8"))
        elif path.is_file():
            digest.update(b"FILE")
            digest.update(path.read_bytes())
        elif path.is_dir():
            digest.update(b"DIR")
    return digest.hexdigest()


def snapshot(repo_root: Path, production_root: Path, run_dir: Path) -> dict[str, object]:
    queue_state = production_root / "queue/runs/f46cda9eaa9ded446bf8e6c6.json"
    publisher_ledger = production_root / "state/ledger.json"
    return {
        "production_root_sha256": tree_sha256(production_root),
        "run_dir_sha256": tree_sha256(run_dir),
        "queue_state_sha256": file_sha256(queue_state),
        "publisher_ledger_sha256": file_sha256(publisher_ledger),
        "repo_public_content_sha256": tree_sha256(repo_root / "app/web"),
        "gen07_exists": (run_dir / "generations/07").exists(),
    }


def main() -> int:
    repo_root = REPO_ROOT
    production_root = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
    run_dir = production_root / "queue/translation-runs" / RUN_ID
    candidate_path = (
        repo_root
        / "artifacts/fortune_council/four_lane_runtime_execution"
        / "pantheon_acceptance_b_gen06_ja_content_repair_20260828/candidate-repaired.json"
    )
    formal_review_path = (
        repo_root
        / "artifacts/fortune_council/four_lane_runtime_execution"
        / "pantheon_acceptance_b_gen06_ja_formal_rereview_20260828/formal-review-result.json"
    )
    approved_review_path = (
        repo_root
        / "artifacts/fortune_council/four_lane_runtime_execution"
        / "pantheon_acceptance_b_gen06_ja_formal_rereview_20260828/isolated-formal-runtime"
        / "translation-runs"
        / RUN_ID
        / "review.json"
    )
    queue_state_path = production_root / "queue/runs/f46cda9eaa9ded446bf8e6c6.json"
    publisher_ledger_path = production_root / "state/ledger.json"
    continuation_path = run_dir / "continuation/state.json"

    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    formal = json.loads(formal_review_path.read_text(encoding="utf-8"))
    approved_review = json.loads(approved_review_path.read_text(encoding="utf-8"))
    production_review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    continuation = json.loads(continuation_path.read_text(encoding="utf-8"))
    queue_state = json.loads(queue_state_path.read_text(encoding="utf-8"))

    identity_checks = {
        "candidate_run_id_exact": candidate.get("run_id") == RUN_ID,
        "approved_article_sha_exact": pipeline.article_sha256(candidate["articles"][0])
        == EXPECTED_ARTICLE_SHA256,
        "formal_verdict_approved": formal.get("exit_verdict") == "APPROVE_READY_FOR_STAGING",
        "formal_findings_empty": formal.get("findings") == [],
        "formal_review_binds_candidate": formal["review"]["articles"][0].get("candidate_sha256")
        == EXPECTED_ARTICLE_SHA256,
        "approved_review_binds_candidate": approved_review["articles"][0].get("candidate_sha256")
        == EXPECTED_ARTICLE_SHA256,
        "approved_review_is_clean": all(
            item.get("verdict") == "APPROVE" and not item.get("findings")
            for item in approved_review["articles"]
        ),
        "production_root_candidate_exact": file_sha256(run_dir / "candidate.json")
        == EXPECTED_ROOT_CANDIDATE_SHA256,
        "production_root_review_exact": file_sha256(run_dir / "review.json")
        == EXPECTED_ROOT_REVIEW_SHA256,
        "production_review_terminal_reject": all(
            item.get("verdict") == "REJECT"
            and item.get("hard_failure") is True
            and bool(item.get("findings"))
            for item in production_review["articles"]
        ),
        "continuation_terminal_complete": continuation.get("status") == "complete"
        and continuation.get("next_generation") == 7,
        "continuation_state_exact": file_sha256(continuation_path)
        == EXPECTED_CONTINUATION_STATE_SHA256,
        "queue_state_complete": queue_state.get("status") == "complete"
        and queue_state.get("run_id") == RUN_ID,
        "queue_state_exact": file_sha256(queue_state_path) == EXPECTED_QUEUE_STATE_SHA256,
        "publisher_ledger_exact": file_sha256(publisher_ledger_path)
        == EXPECTED_PUBLISHER_LEDGER_SHA256,
        "gen07_absent": not (run_dir / "generations/07").exists(),
    }
    if not all(identity_checks.values()):
        print(
            json.dumps(
                {
                    "status": "INVALID_FIXTURE",
                    "identity_checks": identity_checks,
                    "provider_calls": 0,
                    "coordinator_calls": 0,
                    "publish_calls": 0,
                    "tag_calls": 0,
                    "push_calls": 0,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 3

    before = snapshot(repo_root, production_root, run_dir)
    command = [
        sys.executable,
        "-m",
        "scripts.agy_multilingual_pipeline",
        "--repo-root",
        str(repo_root),
        "stage-approved-edited-candidate",
        "--run-dir",
        str(run_dir),
        "--approved-candidate",
        str(candidate_path),
        "--approved-review",
        str(approved_review_path),
        "--formal-review-result",
        str(formal_review_path),
        "--queue-state",
        str(queue_state_path),
        "--publisher-ledger",
        str(publisher_ledger_path),
        "--expected-run-id",
        RUN_ID,
        "--terminal-generation",
        "6",
        "--expected-approved-article-sha256",
        EXPECTED_ARTICLE_SHA256,
        "--expected-root-candidate-sha256",
        EXPECTED_ROOT_CANDIDATE_SHA256,
        "--expected-root-review-sha256",
        EXPECTED_ROOT_REVIEW_SHA256,
        "--expected-continuation-state-sha256",
        EXPECTED_CONTINUATION_STATE_SHA256,
        "--expected-queue-state-sha256",
        EXPECTED_QUEUE_STATE_SHA256,
        "--expected-publisher-ledger-sha256",
        EXPECTED_PUBLISHER_LEDGER_SHA256,
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True)
    after = snapshot(repo_root, production_root, run_dir)
    no_mutation = before == after
    missing_command = (
        completed.returncode == 2
        and "invalid choice: 'stage-approved-edited-candidate'" in completed.stderr
    )
    payload = {
        "schema_version": 1,
        "status": "RED_MISSING_FORMAL_STAGING_SEAM" if missing_command else "GREEN",
        "run_id": RUN_ID,
        "identity_checks": identity_checks,
        "command": command,
        "returncode": completed.returncode,
        "stderr": completed.stderr,
        "before": before,
        "after": after,
        "production_bytes_before_equal_after": no_mutation,
        "provider_calls": 0,
        "coordinator_calls": 0,
        "publish_calls": 0,
        "tag_calls": 0,
        "push_calls": 0,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if not no_mutation:
        return 4
    return 1 if missing_command else completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

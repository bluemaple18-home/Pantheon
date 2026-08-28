#!/usr/bin/env python3
"""Collect read-only evidence for Gen06 JA production staging decision."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO = Path("/Users/mattkuo/Documents/Pantheon")
PRODUCTION = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
RUN_DIR = PRODUCTION / "queue" / "translation-runs" / RUN_ID
APPROVED_CANDIDATE = REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_content_repair_20260828/candidate-repaired.json"
FORMAL_REVIEW = REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_formal_rereview_20260828/formal-review-result.json"
ISOLATED_REVIEW = REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_formal_rereview_20260828/isolated-formal-runtime/translation-runs/auto-i18n-ja-1414b75a404721e95e74/review.json"
EVIDENCE = REPO / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_production_staging_20260828"
EXPECTED_ARTICLE_SHA = "a64d8a33b0b70933134452491c10058e820dd93d5c748d3cc220bbfc25da7b9c"
EXPECTED_ACTOR = "831c536043d85a6cafe813c08a4f06921f0dd0e2"
FORMAL_JOB = "e6c4542483f0b1100a19a5fb7af8c0597600462f"
PRIVATE_STAGE = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return {"path": str(path), "exists": False, "sha256": None, "size": None}
    return {"path": str(path), "exists": True, "sha256": sha256_bytes(data), "size": len(data)}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def tree_digest(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"path": str(root), "exists": False, "file_count": 0, "sha256": None}
    records: list[dict[str, Any]] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                records.append({"path": str(path.relative_to(root)), "symlink": os.readlink(path)})
                continue
            try:
                records.append(
                    {
                        "path": str(path.relative_to(root)),
                        "sha256": sha256_bytes(path.read_bytes()),
                        "size": path.stat().st_size,
                    }
                )
            except FileNotFoundError:
                continue
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "path": str(root),
        "exists": True,
        "file_count": len(records),
        "sha256": sha256_bytes(payload),
    }


def git_output(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "args": ["git", *args],
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def article_sha(article: dict[str, Any]) -> str:
    return sha256_bytes(
        json.dumps(article, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )


def candidate_summary(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    articles = payload.get("articles") or []
    return {
        "file": file_record(path),
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "mode": payload.get("mode"),
        "article_count": len(articles),
        "articles": [
            {
                "article_id": item.get("article_id"),
                "source_article_id": item.get("source_article_id"),
                "locale": item.get("locale"),
                "source_path": item.get("source_path"),
                "source_sha256": item.get("source_sha256"),
                "article_sha256": article_sha(item),
            }
            for item in articles
        ],
    }


def review_summary(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    articles = payload.get("articles") or []
    return {
        "file": file_record(path),
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "articles": [
            {
                "article_id": item.get("article_id"),
                "candidate_sha256": item.get("candidate_sha256"),
                "verdict": item.get("verdict"),
                "hard_failure": item.get("hard_failure"),
                "findings": item.get("findings"),
            }
            for item in articles
        ],
    }


def formal_summary() -> dict[str, Any]:
    formal = load_json(FORMAL_REVIEW)
    review = formal.get("review") or {}
    article_reviews = review.get("articles") or []
    approved = candidate_summary(APPROVED_CANDIDATE)
    return {
        "formal_review_file": file_record(FORMAL_REVIEW),
        "isolated_review_file": file_record(ISOLATED_REVIEW),
        "exit_verdict": formal.get("exit_verdict"),
        "findings": formal.get("findings"),
        "formal_job": FORMAL_JOB,
        "review_run_id": review.get("run_id"),
        "review_articles": article_reviews,
        "approved_candidate": approved,
        "expected_article_sha": EXPECTED_ARTICLE_SHA,
        "article_sha_matches_expected": bool(
            approved["articles"]
            and approved["articles"][0]["article_sha256"] == EXPECTED_ARTICLE_SHA
        ),
        "review_sha_matches_candidate": bool(
            article_reviews
            and approved["articles"]
            and article_reviews[0].get("candidate_sha256") == approved["articles"][0]["article_sha256"]
        ),
    }


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    run_files = [
        RUN_DIR / "brief.json",
        RUN_DIR / "candidate.json",
        RUN_DIR / "review.json",
        RUN_DIR / "continuation" / "state.json",
        RUN_DIR / "continuation" / "generation-lifecycle.json",
        RUN_DIR / "generations" / "06" / "candidate.json",
        RUN_DIR / "generations" / "06" / "review.json",
    ]
    output = {
        "schema_version": 1,
        "label": label,
        "production_root": str(PRODUCTION),
        "run_id": RUN_ID,
        "actor_authority": {
            "expected": EXPECTED_ACTOR,
            "runtime_manifest": file_record(PRODUCTION / "runtime-manifest.json"),
        },
        "formal_approval_binding": formal_summary(),
        "production_files": {str(path): file_record(path) for path in run_files},
        "production_candidate": candidate_summary(RUN_DIR / "candidate.json"),
        "production_review": review_summary(RUN_DIR / "review.json"),
        "production_gen06_review": review_summary(RUN_DIR / "generations" / "06" / "review.json"),
        "tree_digests": {
            "run_dir": tree_digest(RUN_DIR),
            "continuation": tree_digest(RUN_DIR / "continuation"),
            "gen06": tree_digest(RUN_DIR / "generations" / "06"),
            "gen07": tree_digest(RUN_DIR / "generations" / "07"),
            "lane_i18n_new": tree_digest(PRODUCTION / "queue" / "lanes" / "i18n-new"),
            "publisher_state": tree_digest(PRODUCTION / "state"),
            "private_stage": tree_digest(PRIVATE_STAGE),
            "repo_public_content": tree_digest(REPO / "app" / "web"),
        },
        "gen07_absent": not (RUN_DIR / "generations" / "07").exists(),
        "git": {
            "status_short": git_output(["status", "--short"]),
            "tag_contains_expected_article_sha": git_output(["tag", "--list", f"*{EXPECTED_ARTICLE_SHA[:12]}*"]),
        },
        "seam_search_decision": {
            "formal_staging_seam_found": False,
            "blocker": "BLOCKED_NO_FORMAL_STAGING_SEAM",
            "mutation_count": 0,
            "evaluated_existing_entrypoints": [
                {
                    "entrypoint": "scripts.agy_multilingual_pipeline approve_and_apply_translation_run/apply",
                    "decision": "reject_for_this_card",
                    "reason": "applies approved translation directly into repo locale registry and approval.json; no production-run staging receipt, expected-current SHA lock, or publish-boundary separation for edited candidate replacement.",
                },
                {
                    "entrypoint": "scripts.agy_content_publisher publish_ready_translation_runs",
                    "decision": "reject_for_this_card",
                    "reason": "publisher path applies, bumps version, prerenders/feed, writes changelog, and enters commit/tag/push-capable release boundary; not a staging-only seam.",
                },
                {
                    "entrypoint": "scripts.agy_gemini_coordinator replay_campaign_editorial_workset_through_translation",
                    "decision": "reject_for_this_card",
                    "reason": "campaign dry-run/replay helper stages in a temporary directory and copies only during campaign replay; not a standalone approved edited candidate staging command for an existing production run.",
                },
                {
                    "entrypoint": "scripts.pantheon_content_runtime_promotion",
                    "decision": "reject_for_this_card",
                    "reason": "promotes actor/runtime manifest/private launchd stage; it preserves run queues but does not stage candidate/review replacements.",
                },
            ],
        },
        "external_tool_gate": {
            "tool_service": "local filesystem and local Python only",
            "operation_level": "read_only/dry_run",
            "connection_status": "not_applicable",
            "schema_checked": "repo entrypoints and JSON artifacts inspected",
            "confirmation_required": "already received for production staging only; no external write authorized",
            "execution_status": "no provider call, no remote write",
        },
        "evidence_dir": str(EVIDENCE),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

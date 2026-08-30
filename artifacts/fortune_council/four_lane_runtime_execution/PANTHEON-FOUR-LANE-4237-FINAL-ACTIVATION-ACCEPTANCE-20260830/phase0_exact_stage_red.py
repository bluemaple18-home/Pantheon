#!/usr/bin/env python3
"""以 production-shaped bytes 證明 replacement attempt 被空 continuation 目錄擋下。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


SOURCE = Path(os.environ.get("PANTHEON_ACCEPTANCE_SOURCE", "/private/tmp/pantheon-approved-locale-replacement-e01"))
TASK = Path("/Users/mattkuo/Documents/Pantheon")
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
QUEUE = RUNTIME / "queue"
STATE = RUNTIME / "state"
RUN_ID = "auto-i18n-en-aa637e1bf05d3ad21429-replacement-01"
RUN_DIR = QUEUE / "translation-runs" / RUN_ID
EVIDENCE = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830"
APPROVED_ROOT = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-FORMAL-REREVIEW-20260830"
CANDIDATE = TASK / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830/candidate-repaired.json"
APPROVED_REVIEW = APPROVED_ROOT / "isolated-formal-runtime/translation-runs/auto-i18n-en-aa637e1bf05d3ad21429-replacement-01/review.json"
FORMAL_RESULT = APPROVED_ROOT / "formal-review-result.json"
QUEUE_STATE = QUEUE / "runs/1bf0bbc61ff8d10e808f6923.json"
LEDGER = STATE / "ledger.json"
MODULE_REL = Path("app/web/static/article-locale-codex-emergency-i18n-20260726-astro-base-03.js")
MANIFEST_REL = Path("app/web/static/article-locales.js")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    sys.path.insert(0, str(SOURCE))
    from scripts import agy_multilingual_pipeline as multilingual

    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    article = candidate["articles"][0]
    module = SOURCE / MODULE_REL
    before = module.read_bytes()
    prefix = "// AGY 核准多語文章；由 scripts/agy_multilingual_pipeline.py 產生。\n\n"
    match = re.fullmatch(r"export const ([A-Z][A-Z0-9_]*) = (\[.*\]);\n", before.decode()[len(prefix):], re.DOTALL)
    assert match is not None
    export = match.group(1)
    records = json.loads(match.group(2))
    matches = [index for index, item in enumerate(records) if item.get("articleId") == "ASTRO-BASE-03" and item.get("locale") == "en"]
    assert matches == [0]
    index = matches[0]
    old = records[index]
    replacement = {
        "runId": RUN_ID,
        "articleId": article["source_article_id"],
        "locale": article["locale"],
        "sourcePath": article["source_path"],
        "sourceSha256": article["source_sha256"],
        **{field: article[field] for field in sorted(multilingual.TRANSLATABLE_FIELDS)},
    }
    after_records = list(records)
    after_records[index] = replacement
    after = (prefix + f"export const {export} = {json.dumps(after_records, ensure_ascii=False, indent=2)};\n").encode()
    descriptor = {
        "contract": "approved-locale-existing-record-replacement",
        "source_article_id": article["source_article_id"],
        "locale": article["locale"],
        "old_run_id": old["runId"],
        "old_source_sha256": old["sourceSha256"],
        "old_record_sha256": hashlib.sha256(multilingual.compact_json_bytes(old)).hexdigest(),
        "module_path": MODULE_REL.as_posix(),
        "module_export": export,
        "record_index": index,
        "module_before_sha256": hashlib.sha256(before).hexdigest(),
        "module_after_sha256": hashlib.sha256(after).hexdigest(),
        "manifest_path": MANIFEST_REL.as_posix(),
        "manifest_sha256": sha(SOURCE / MANIFEST_REL),
        "replacement_run_id": RUN_ID,
        "replacement_source_sha256": article["source_sha256"],
        "approved_article_sha256": multilingual.pipeline.article_sha256(article),
        "replacement_record_sha256": hashlib.sha256(multilingual.compact_json_bytes(replacement)).hexdigest(),
    }
    descriptor_path = EVIDENCE / "phase-3-public-replacement-descriptor.json"
    descriptor_path.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = [
        str(SOURCE / ".venv/bin/python"), "-m", "scripts.agy_multilingual_pipeline", "--repo-root", str(SOURCE),
        "stage-approved-edited-candidate",
        "--run-dir", str(RUN_DIR),
        "--approved-candidate", str(CANDIDATE),
        "--approved-review", str(APPROVED_REVIEW),
        "--formal-review-result", str(FORMAL_RESULT),
        "--queue-state", str(QUEUE_STATE),
        "--publisher-ledger", str(LEDGER),
        "--terminal-owner-kind", "replacement_attempt",
        "--terminal-attempt", "3",
        "--replacement-of", "auto-i18n-en-aa637e1bf05d3ad21429",
        "--replacement-reason", "LOCALE_PLAN_VALIDATION",
        "--public-replacement", str(descriptor_path),
        "--expected-run-id", RUN_ID,
        "--expected-approved-article-sha256", descriptor["approved_article_sha256"],
        "--expected-root-candidate-sha256", sha(RUN_DIR / "candidate.json"),
        "--expected-root-review-sha256", sha(RUN_DIR / "review.json"),
        "--expected-queue-state-sha256", sha(QUEUE_STATE),
        "--expected-publisher-ledger-sha256", sha(LEDGER),
        "--expected-replacement-state-sha256", sha(QUEUE_STATE),
        "--expected-approved-candidate-sha256", sha(CANDIDATE),
        "--expected-approved-review-sha256", sha(APPROVED_REVIEW),
        "--expected-formal-review-result-sha256", sha(FORMAL_RESULT),
        "--expected-source-sha256", article["source_sha256"],
        "--expected-actor-sha", os.environ.get("PANTHEON_ACCEPTANCE_SHA", "4237d7c28274ea3373079f1504c3e22d400f0648"),
    ]
    protected = {
        "run_tree": multilingual._tree_sha256(RUN_DIR),
        "queue_state": sha(QUEUE_STATE),
        "ledger": sha(LEDGER),
        "module": sha(module),
        "manifest": sha(SOURCE / MANIFEST_REL),
    }
    completed = subprocess.run(command, cwd=SOURCE, text=True, capture_output=True, check=False)
    after_protected = {
        "run_tree": multilingual._tree_sha256(RUN_DIR),
        "queue_state": sha(QUEUE_STATE),
        "ledger": sha(LEDGER),
        "module": sha(module),
        "manifest": sha(SOURCE / MANIFEST_REL),
    }
    expected_status = os.environ.get("PANTHEON_EXPECTED_STAGE_STATUS", "RED")
    observed_status = (
        "RED_CONFIRMED"
        if completed.returncode != 0 and "replacement attempt lineage differs" in completed.stderr and protected == after_protected
        else "GREEN_CONFIRMED"
        if completed.returncode == 0 and protected == after_protected
        else "UNEXPECTED"
    )
    receipt = {
        "schema_version": 1,
        "status": observed_status,
        "argv": command,
        "cwd": str(SOURCE),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "continuation_exists": (RUN_DIR / "continuation").exists(),
        "continuation_entries": sorted(path.name for path in (RUN_DIR / "continuation").iterdir()),
        "continuation_is_empty": not any((RUN_DIR / "continuation").iterdir()),
        "attempt_directories": sorted(path.name for path in (RUN_DIR / "attempts").iterdir() if path.is_dir()),
        "protected_before": protected,
        "protected_after": after_protected,
        "production_mutation": protected != after_protected,
        "provider_writer_reviewer_publisher_calls": 0,
        "descriptor_sha256": sha(descriptor_path),
    }
    output = EVIDENCE / ("phase-0-exact-stage-green.json" if expected_status == "GREEN" else "phase-0-exact-stage-red.json")
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "returncode": completed.returncode, "stderr": completed.stderr.strip(), "production_mutation": receipt["production_mutation"]}, sort_keys=True))
    return 0 if receipt["status"] == f"{expected_status}_CONFIRMED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

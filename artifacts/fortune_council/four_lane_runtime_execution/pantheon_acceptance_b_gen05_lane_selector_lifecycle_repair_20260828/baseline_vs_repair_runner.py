#!/usr/bin/env python3
"""read-only baseline classification runner for the eight full-file failures."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_DIR = Path(__file__).resolve().parent
BASELINE_ROOT = Path("/private/tmp/pantheon-gen05-lane-selector-baseline-8a-20260828")
BASELINE_SHA = "8a50395f67d22343fec4b0a8a5f41c8f40ac360e"
NODEIDS = [
    "tests/test_agy_gemini_coordinator.py::test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain",
    "tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_composes_four_lanes_without_publishing",
    "tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_resumes_seeded_partial_state_without_repeating_completed_work",
    "tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[source_sha]",
    "tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[translation_sha]",
    "tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[locale]",
    "tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[article_identity]",
    "tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[review_identity]",
]


def _run(label: str, cwd: Path) -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", *NODEIDS, "-q"]
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=900,
    )
    stdout_path = EVIDENCE_DIR / f"{label}-eight-nodeids.stdout.txt"
    stderr_path = EVIDENCE_DIR / f"{label}-eight-nodeids.stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    stdout = completed.stdout
    stderr = completed.stderr
    return {
        "label": label,
        "cwd": str(cwd),
        "command": command,
        "returncode": completed.returncode,
        "stdout_path": str(stdout_path.relative_to(REPO_ROOT)),
        "stderr_path": str(stderr_path.relative_to(REPO_ROOT)),
        "summary_line": next(
            (
                line.strip()
                for line in reversed(stdout.splitlines())
                if "failed" in line and ("passed" in line or "warnings" in line)
            ),
            "",
        ),
        "locale_plan_validation_error_count": (
            stdout.count("LocalePlanValidationError")
            + stderr.count("LocalePlanValidationError")
        ),
        "strict_coverage_error_count": (
            stdout.count("external locale plan coverage fields are strict for article-01")
            + stderr.count("external locale plan coverage fields are strict for article-01")
        ),
    }


def main() -> int:
    if not BASELINE_ROOT.is_dir():
        raise SystemExit(f"baseline root missing: {BASELINE_ROOT}")
    baseline = _run("baseline-8a", BASELINE_ROOT)
    current = _run("current-repair", REPO_ROOT)
    same_failure_shape = (
        baseline["returncode"] == current["returncode"] == 1
        and baseline["locale_plan_validation_error_count"]
        == current["locale_plan_validation_error_count"]
        and baseline["strict_coverage_error_count"]
        == current["strict_coverage_error_count"]
        and baseline["strict_coverage_error_count"] > 0
    )
    receipt = {
        "schema_version": 1,
        "status": "CLASSIFIED",
        "classification": "PRE_EXISTING" if same_failure_shape else "REPAIR_REGRESSION_OR_CHANGED",
        "baseline_sha": BASELINE_SHA,
        "baseline_root": str(BASELINE_ROOT),
        "current_root": str(REPO_ROOT),
        "nodeids": NODEIDS,
        "baseline": baseline,
        "current": current,
        "same_failure_shape": same_failure_shape,
        "production_mutation": False,
        "provider_calls": 0,
    }
    output = EVIDENCE_DIR / "baseline-vs-repair-eight-nodeids-receipt.json"
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if same_failure_shape else 1


if __name__ == "__main__":
    raise SystemExit(main())

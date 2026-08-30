#!/usr/bin/env python3
"""Provider=0 reproduction for terminal complete+REJECT continuation seam."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path.cwd()))

from scripts import agy_multilingual_pipeline as multilingual


SOURCE_RUN = Path(
    "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/"
    "auto-i18n-ja-1414b75a404721e95e74"
)
TMP_RUN = Path("/private/tmp/pantheon-gen06-terminal-rejected-rca-copy-20260828")
OUT = Path(
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "pantheon_acceptance_b_gen06_terminal_continuation_and_capacity_rca_20260828/"
    "terminal-rejected-gen06-reproduction.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FailIfCalled:
    writer_model = "writer-test"
    reviewer_model = "reviewer-test"

    def generate_json(self, *_args: object) -> dict[str, object]:
        raise AssertionError("provider must not be called by terminal replay")


def main() -> int:
    if TMP_RUN.exists():
        shutil.rmtree(TMP_RUN)
    shutil.copytree(SOURCE_RUN, TMP_RUN)
    before = sorted(str(path.relative_to(TMP_RUN)) for path in TMP_RUN.rglob("*") if path.is_file())
    state_before = json.loads((TMP_RUN / "continuation/state.json").read_text())
    candidate, review = multilingual.continue_writer_reviewer(
        TMP_RUN,
        FailIfCalled(),
        max_repairs=2,
    )
    after = sorted(str(path.relative_to(TMP_RUN)) for path in TMP_RUN.rglob("*") if path.is_file())
    receipt = {
        "status": "REPRODUCED_NO_FORMAL_GEN06_SEAM",
        "source_run": str(SOURCE_RUN),
        "tmp_run": str(TMP_RUN),
        "state_before": state_before,
        "state_after": json.loads((TMP_RUN / "continuation/state.json").read_text()),
        "provider_called": False,
        "returned_review_verdicts": [article.get("verdict") for article in review.get("articles", [])],
        "returned_candidate_sha256": multilingual._json_sha256(candidate),
        "returned_review_sha256": multilingual._json_sha256(review),
        "gen06_exists_after": (TMP_RUN / "generations/06").exists(),
        "file_list_changed": before != after,
        "red_capable": not (TMP_RUN / "generations/06").exists()
        and not before != after
        and state_before.get("status") == "complete"
        and state_before.get("next_generation") == 6,
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"path": str(OUT), "sha256": sha256(OUT), "red_capable": receipt["red_capable"]}, ensure_ascii=False))
    return 0 if receipt["red_capable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

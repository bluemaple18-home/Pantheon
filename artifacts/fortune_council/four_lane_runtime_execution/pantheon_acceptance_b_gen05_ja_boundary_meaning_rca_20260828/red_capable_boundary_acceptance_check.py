#!/usr/bin/env python3
"""RED-capable check: current gen05 candidate must satisfy JA boundary contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

from scripts import agy_multilingual_pipeline as multilingual


RUN_ROOT = Path(
    "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/"
    "auto-i18n-ja-1414b75a404721e95e74"
)


def main() -> int:
    brief = json.loads((RUN_ROOT / "brief.json").read_text())
    candidate = json.loads((RUN_ROOT / "generations/05/candidate.json").read_text())
    findings = multilingual.translation_findings(brief, candidate["articles"])
    boundary = [item for item in findings if item.get("code") == "BOUNDARY_MEANING_MISSING"]
    if boundary:
        raise AssertionError(json.dumps(boundary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

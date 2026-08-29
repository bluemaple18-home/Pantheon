#!/usr/bin/env python3
"""比較既有 broad-suite failure node 與正規化錯誤，不掩蓋新增回歸。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
COMMAND = (
    ".venv/bin/python -m pytest -q "
    "tests/test_pantheon_content_capacity_guard.py "
    "tests/test_pantheon_content_runtime_manifest.py "
    "tests/test_agy_gemini_coordinator.py"
)


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def summarize(path: Path) -> dict[str, object]:
    body = path.read_bytes()
    text = body.decode("utf-8")
    nodes = sorted(
        line.removeprefix("FAILED ")
        for line in text.splitlines()
        if line.startswith("FAILED ")
    )
    errors = []
    for line in text.splitlines():
        if not line.startswith("E   "):
            continue
        normalized = re.sub(r"0x[0-9a-fA-F]+", "0x<ADDR>", line)
        normalized = re.sub(r"pytest-\d+", "pytest-<N>", normalized)
        errors.append(normalized)
    encoded_errors = json.dumps(errors, sort_keys=True, separators=(",", ":")).encode()
    return {
        "path": path.name,
        "bytes": len(body),
        "sha256": sha256(body),
        "failure_count": len(nodes),
        "failure_nodes": nodes,
        "normalized_error_lines_count": len(errors),
        "normalized_error_lines_sha256": sha256(encoded_errors),
    }


def main() -> int:
    baseline = summarize(ROOT / "broad-baseline.txt")
    candidate = summarize(ROOT / "broad-candidate.txt")
    identical = (
        baseline["failure_nodes"] == candidate["failure_nodes"]
        and baseline["normalized_error_lines_sha256"]
        == candidate["normalized_error_lines_sha256"]
    )
    receipt = {
        "schema_version": 1,
        "command": COMMAND,
        "command_sha256": sha256(COMMAND.encode()),
        "parent": "bde44589f3785aae738bb7d7b1626270ba5505d0",
        "baseline": baseline,
        "candidate": candidate,
        "baseline_identical": identical,
    }
    (ROOT / "broad-baseline-candidate.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())

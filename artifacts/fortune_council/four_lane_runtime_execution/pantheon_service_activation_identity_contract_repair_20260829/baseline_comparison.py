#!/usr/bin/env python3
"""在 candidate 與 detached parent 執行相同 pytest selection並比較失敗集合。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


TEST_ARGS = (
    "-m",
    "pytest",
    "-q",
    "tests/test_agy_gemini_coordinator.py",
    "tests/test_agy_gemini_coordinator_capability_receipt.py",
    "tests/test_pantheon_g8_production_preactivation.py",
    "tests/test_pantheon_runtime_activation.py",
)
FAILURE_LINE = re.compile(r"^FAILED (?P<node>\S+?)(?: - (?P<message>.*))?$", re.MULTILINE)
PYTEST_TMP = re.compile(r"/private/var/folders/[^\s'\"]+/pytest-of-[^/\s]+/pytest-\d+")
ADDRESS = re.compile(r"0x[0-9a-fA-F]+")
DURATION = re.compile(r"in \d+(?:\.\d+)?s")
SUMMARY = re.compile(r"(?P<failed>\d+) failed, (?P<passed>\d+) passed")
FAILURE_SECTION = re.compile(
    r"^_+ (?P<header>.+?) _+\n(?P<body>.*?)"
    r"(?=^_+ .+? _+\n|^=+ short test summary info =+)",
    re.MULTILINE | re.DOTALL,
)


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def normalize(value: str, roots: tuple[Path, Path]) -> str:
    normalized = value
    for root in roots:
        normalized = normalized.replace(str(root), "<WORKTREE>")
    normalized = PYTEST_TMP.sub("<PYTEST_TMP>", normalized)
    normalized = ADDRESS.sub("<ADDRESS>", normalized)
    return DURATION.sub("in <SECONDS>s", normalized)


def analyze(label: str, evidence: Path, roots: tuple[Path, Path], returncode: int) -> dict[str, object]:
    stdout_path = evidence / f"{label}_broad_pytest.stdout.txt"
    stderr_path = evidence / f"{label}_broad_pytest.stderr.txt"
    stdout_bytes = stdout_path.read_bytes()
    stderr_bytes = stderr_path.read_bytes()
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    nodes = [match.group("node") for match in FAILURE_LINE.finditer(stdout + "\n" + stderr)]
    sections = list(FAILURE_SECTION.finditer(stdout))
    failures: dict[str, str] = {}
    for node in nodes:
        leaf = node.rsplit("::", 1)[-1]
        function = leaf.split("[", 1)[0]
        parameter = leaf[len(function) :].strip("[]")
        matching = [
            section
            for section in sections
            if function in section.group("header")
            and (not parameter or parameter in section.group("header"))
        ]
        error_lines = (
            [line[4:] for line in matching[0].group("body").splitlines() if line.startswith("E   ")]
            if matching
            else []
        )
        detail = "\n".join(error_lines) if error_lines else (
            matching[0].group("body") if matching else leaf
        )
        failures[node] = digest(normalize(detail, roots))
    summary = SUMMARY.search(stdout)
    normalized_output = normalize(stdout + "\n<STDERR>\n" + stderr, roots)
    return {
        "returncode": returncode,
        "stdout_sha256": digest(stdout_bytes),
        "stderr_sha256": digest(stderr_bytes),
        "normalized_output_sha256": digest(normalized_output),
        "failure_count": len(failures),
        "passed_count": int(summary.group("passed")) if summary else None,
        "failure_nodes": sorted(failures),
        "normalized_error_digest_by_node": dict(sorted(failures.items())),
    }


def run_selection(
    label: str,
    root: Path,
    command: list[str],
    evidence: Path,
    roots: tuple[Path, Path],
) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=root,
        env=os.environ.copy(),
        check=False,
        capture_output=True,
    )
    (evidence / f"{label}_broad_pytest.stdout.txt").write_bytes(completed.stdout)
    (evidence / f"{label}_broad_pytest.stderr.txt").write_bytes(completed.stderr)
    return analyze(label, evidence, roots, completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--compare-existing", action="store_true")
    parser.add_argument("--candidate-only", action="store_true")
    args = parser.parse_args()
    candidate = args.candidate.resolve(strict=True)
    baseline = args.baseline.resolve(strict=True)
    evidence = args.evidence.resolve(strict=True)
    command = [sys.executable, *TEST_ARGS]
    roots = (candidate, baseline)
    previous_receipt = json.loads(
        (evidence / "baseline_identical.json").read_text(encoding="utf-8")
    ) if args.candidate_only else None
    if args.candidate_only:
        candidate_result = run_selection("candidate", candidate, command, evidence, roots)
        baseline_result = previous_receipt["baseline"]
    elif args.compare_existing:
        candidate_result = analyze("candidate", evidence, roots, 1)
        baseline_result = analyze("baseline", evidence, roots, 1)
    else:
        candidate_result = run_selection("candidate", candidate, command, evidence, roots)
        baseline_result = run_selection("baseline", baseline, command, evidence, roots)
    parent_sha = previous_receipt["parent_sha"] if previous_receipt else subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=baseline,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    environment_contract = {
        name: os.environ.get(name)
        for name in ("LANG", "LC_ALL", "PYTHONHASHSEED", "PYTEST_ADDOPTS", "TZ")
    }
    comparable = (
        candidate_result["returncode"] == baseline_result["returncode"] == 1
        and candidate_result["passed_count"] == baseline_result["passed_count"] == 442
        and candidate_result["failure_count"] == baseline_result["failure_count"] == 8
        and candidate_result["failure_nodes"] == baseline_result["failure_nodes"]
        and candidate_result["normalized_error_digest_by_node"]
        == baseline_result["normalized_error_digest_by_node"]
    )
    receipt = {
        "schema_version": 1,
        "status": "BASELINE_IDENTICAL" if comparable else "BASELINE_DIFFERENT",
        "identical": comparable,
        "parent_sha": parent_sha,
        "command": command,
        "command_sha256": digest(json.dumps(command, separators=(",", ":"))),
        "environment_contract": environment_contract,
        "environment_contract_sha256": digest(
            json.dumps(environment_contract, sort_keys=True, separators=(",", ":"))
        ),
        "candidate": candidate_result,
        "baseline": baseline_result,
        "production_live_mutations": 0,
    }
    (evidence / "baseline_identical.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if comparable else 1


if __name__ == "__main__":
    raise SystemExit(main())

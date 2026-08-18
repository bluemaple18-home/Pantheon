#!/usr/bin/env python3
"""Review repro: stale publisher-exact-run-id receipt is ignored by activation."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    fixture_path = repo_root / "tests" / "test_agy_gemini_coordinator.py"
    spec = importlib.util.spec_from_file_location(
        "review_test_agy_gemini_coordinator",
        fixture_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load coordinator fixture")
    fixture = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(repo_root))
    sys.modules[spec.name] = fixture
    spec.loader.exec_module(fixture)
    with tempfile.TemporaryDirectory(
        prefix="publisher-only-review-",
        dir="/private/tmp",
    ) as tmp:
        tmp_path = Path(tmp)
        (
            env,
            fake_home,
            mutation_log,
            _manifest,
            _barrier,
            _loaded,
            _live_payloads,
        ) = fixture._prepare_publisher_only_activation_fixture(
            tmp_path,
            exact_run_id=None,
        )
        stage_dir = fake_home / "Library" / "LaunchAgents" / ".pantheon-four-lane-stage"
        (stage_dir / "publisher-exact-run-id").write_text(
            "stale-run-from-previous-stage\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                "/bin/bash",
                str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
                "--activate-publisher-only",
            ],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        result = {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "mutation_log_exists": mutation_log.exists(),
            "mutations": (
                mutation_log.read_text(encoding="utf-8").splitlines()
                if mutation_log.exists()
                else []
            ),
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if completed.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

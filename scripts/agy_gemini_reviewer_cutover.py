"""產生只切換 reviewer model 的 coordinator launchd plist。"""

from __future__ import annotations

import argparse
import copy
import json
import plistlib
import re
from pathlib import Path
from typing import Any


COORDINATOR_LABEL = "com.pantheon.agy-gemini-coordinator"
MODEL_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")


def render_reviewer_cutover(
    source: Path,
    output: Path,
    reviewer_model: str,
) -> dict[str, str | None]:
    """複製既有 coordinator plist，並且只替換 reviewer model。"""

    if not MODEL_IDENTIFIER.fullmatch(reviewer_model):
        raise ValueError("reviewer model must be a non-empty safe model identifier")

    original: dict[str, Any] = plistlib.loads(source.read_bytes())
    if original.get("Label") != COORDINATOR_LABEL:
        raise ValueError("source must be the Pantheon Gemini coordinator plist")
    environment = original.get("EnvironmentVariables")
    if type(environment) is not dict:
        raise ValueError("coordinator plist must contain EnvironmentVariables")

    rendered = copy.deepcopy(original)
    rendered_environment = rendered["EnvironmentVariables"]
    previous_reviewer_model = rendered_environment.get("AGY_REVIEWER_MODEL")
    writer_model = rendered_environment.get("AGY_WRITER_MODEL")
    rendered_environment["AGY_REVIEWER_MODEL"] = reviewer_model

    expected = copy.deepcopy(original)
    expected["EnvironmentVariables"]["AGY_REVIEWER_MODEL"] = reviewer_model
    if rendered != expected:
        raise RuntimeError("reviewer cutover changed fields outside AGY_REVIEWER_MODEL")

    output.write_bytes(plistlib.dumps(rendered, sort_keys=False))
    return {
        "label": COORDINATOR_LABEL,
        "previous_reviewer_model": previous_reviewer_model,
        "reviewer_model": reviewer_model,
        "writer_model": writer_model,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer-model", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = render_reviewer_cutover(
        args.source,
        args.output,
        args.reviewer_model,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

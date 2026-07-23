#!/usr/bin/env python3
"""對 canary verifier 執行 deterministic result-schema tamper controls。"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path


WEAKENED_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "properties": {},
    "required": [],
}


def load_verifier(path: Path):
    spec = importlib.util.spec_from_file_location("repair_canary_verifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("canary verifier cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(verifier, bundle: object, *, coherent: bool) -> dict[str, object]:
    candidate = copy.deepcopy(bundle)
    candidate["result_schema"] = copy.deepcopy(WEAKENED_SCHEMA)
    if coherent:
        candidate["execution"]["result"] = {"unexpected": "accepted"}
        candidate["inbox"]["result"] = {"unexpected": "accepted"}
    try:
        verifier.verify_bundle(candidate)
    except verifier.VerificationError as error:
        return {"accepted": False, "error": str(error)}
    return {"accepted": True, "error": None}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verifier", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verifier = load_verifier(args.verifier)
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    output = {
        "wrong_result_schema": run_case(verifier, bundle, coherent=False),
        "coherent_weakened_schema": run_case(verifier, bundle, coherent=True),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

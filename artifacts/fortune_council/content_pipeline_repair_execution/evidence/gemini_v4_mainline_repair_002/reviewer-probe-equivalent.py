#!/usr/bin/env python3
"""等價重跑 canonical Reviewer 的 Gemini V4 canary 獨立 probe。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path


EXPECTED_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ok": {"type": "boolean"},
        "transport": {"type": "string", "enum": ["agy-v4-mainline-repair-canary"]},
    },
    "required": ["ok", "transport"],
}


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_verifier(path: Path):
    spec = importlib.util.spec_from_file_location("repair_canary_verifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("canary verifier cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    result = verifier.verify_bundle(bundle)
    frames = bundle["ledger"]["canonical_frames"]
    raw_ledger = b"".join(canonical_json(frame) + b"\n" for frame in frames)
    canonical_result = canonical_json(bundle["execution"]["result"])
    result_encodings = (canonical_result, canonical_result + b"\n")
    matrix = verifier.mutation_matrix(bundle)

    weakened = copy.deepcopy(bundle)
    weakened["result_schema"] = {
        "type": "object",
        "additionalProperties": True,
        "properties": {},
        "required": [],
    }
    weakened["execution"]["result"] = {"unexpected": "accepted"}
    weakened["inbox"]["result"] = {"unexpected": "accepted"}
    try:
        verifier.verify_bundle(weakened)
    except verifier.VerificationError as error:
        weakened_schema = {"accepted": False, "error": str(error)}
    else:
        weakened_schema = {"accepted": True, "error": None}

    output = {
        "offline_verifier_status": result["status"],
        "ledger_sha256_recomputed": sha256(raw_ledger),
        "ledger_sha256_matches": sha256(raw_ledger) == bundle["ledger"]["ledger_sha256"],
        "final_anchor_recomputed": sha256(canonical_json(frames[-1])),
        "final_anchor_matches": (
            sha256(canonical_json(frames[-1])) == bundle["ledger"]["final_anchor"]
        ),
        "operation_id_matches_request_prefix": (
            bundle["receipt"]["operation_id"] == bundle["receipt"]["request_sha256"][:40]
        ),
        "result_byte_count_matches": any(
            len(encoded) == bundle["execution"]["byte_count"] for encoded in result_encodings
        ),
        "result_stdout_sha256_matches": any(
            sha256(encoded) == bundle["execution"]["stdout_sha256"] for encoded in result_encodings
        ),
        "expected_result_schema_matches": bundle["result_schema"] == EXPECTED_SCHEMA,
        "mutation_controls_rejected": sum(
            case["rejected"] is True and case["status"] == "PASS" for case in matrix["cases"]
        ),
        "mutation_controls_total": len(matrix["cases"]),
        "weakened_schema_coherent_tamper": weakened_schema,
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

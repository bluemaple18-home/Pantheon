from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_editorial_contracts as contracts


def brief() -> dict[str, Any]:
    return {
        "version": "ArticleBriefV2",
        "run_id": "writer-vnext-review-002",
        "article_identity": {"id": "REVIEW-002", "canonical_path": "/review-002/"},
        "reader_question": "如何確認 Writer vNext contract 沒有接受模糊 sequence？",
        "target_reader": "審查 Writer vNext contract 的 reviewer",
        "search_intent": "verification",
        "thesis": "boolean sequence 必須 fail closed，真正 integer sequence 必須維持可用。",
        "reader_outcome": "reviewer 能獨立判定 Repair-1 是否關閉 P1。",
        "scope": "public API manifest validation",
        "anti_goals": ["不修改 production", "不啟動服務"],
        "evidence_policy": "in-process-public-api",
        "risk_class": "medium",
    }


def stage(sequence: object) -> dict[str, Any]:
    return {
        "stage_type": "content_plan_v1",
        "sequence": sequence,
        "required_inputs": ["ArticleBriefV2"],
        "expected_output": "content_plan",
        "blocking_policy": "blocking-v1",
    }


def content_plan() -> dict[str, Any]:
    return {
        "version": "ContentPlanV1",
        "sections": [{"purpose": "確認 sequence 型別", "supports_thesis": True}],
    }


def manifest(sequence: object) -> dict[str, Any]:
    base_brief = brief()
    artifacts = {"brief": base_brief, "content_plan": content_plan()}
    return {
        "version": "EditorialManifestV1",
        "run_id": base_brief["run_id"],
        "article_identity": base_brief["article_identity"],
        "brief_sha256": contracts.artifact_sha256(base_brief),
        "selected_stages": [stage(sequence)],
        "artifacts": artifacts,
        "artifact_sha256": {name: contracts.artifact_sha256(value) for name, value in artifacts.items()},
        "final_candidate_sha256": "a" * 64,
    }


def evaluate(name: str, sequence: object, expected_valid: bool, expected_findings: list[str]) -> dict[str, Any]:
    report = contracts.validate_manifest(manifest(sequence))
    return {
        "name": name,
        "sequence_repr": repr(sequence),
        "expected_valid": expected_valid,
        "actual_valid": report["valid"],
        "expected_findings": expected_findings,
        "actual_findings": report["findings"],
        "passed": report["valid"] is expected_valid and report["findings"] == expected_findings,
    }


def main() -> int:
    cases = [
        evaluate("sequence_true_blocks", True, False, ["schema_version_unsupported"]),
        evaluate("sequence_false_blocks", False, False, ["schema_version_unsupported"]),
        evaluate("sequence_integer_accepts", 1, True, []),
    ]
    output = {
        "summary": {
            "total_cases": len(cases),
            "passed_cases": sum(1 for case in cases if case["passed"]),
            "failed_cases": [case["name"] for case in cases if not case["passed"]],
        },
        "cases": cases,
    }
    output_path = Path(__file__).with_name("sequence_public_probe_results.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if output["summary"]["passed_cases"] == output["summary"]["total_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_editorial_contracts as contracts
from scripts.agy_seo_copy_pipeline import validate_candidate


FINAL_SHA = "a" * 64
BLIND_INPUT_SHA = "b" * 64


def brief() -> dict[str, Any]:
    return {
        "version": "ArticleBriefV2",
        "run_id": "writer-vnext-public-review-001",
        "article_identity": {"id": "PUBLIC-REVIEW-001", "canonical_path": "/public-review-001/"},
        "reader_question": "這份內容如何幫我做下一步判斷？",
        "target_reader": "需要快速理解選項差異的讀者",
        "search_intent": "informational",
        "thesis": "先分開可驗證事實、產品說明與主觀建議，才能做出可追溯的內容決策。",
        "reader_outcome": "讀者能列出下一步要查證與採取的動作。",
        "scope": "公開內容的決策輔助",
        "anti_goals": ["不保證個人結果", "不替代專業判斷"],
        "evidence_policy": "cite-verifiable-and-high-risk-claims",
        "risk_class": "medium",
    }


def stage(stage_type: str, sequence: int, *, policy: str = "blocking-v1") -> dict[str, Any]:
    return {
        "stage_type": stage_type,
        "sequence": sequence,
        "required_inputs": ["ArticleBriefV2"],
        "expected_output": contracts.STAGE_ARTIFACTS.get(stage_type, "unknown"),
        "blocking_policy": policy,
    }


def content_plan(count: int) -> dict[str, Any]:
    return {
        "version": "ContentPlanV1",
        "sections": [{"purpose": f"回答第 {index + 1} 個讀者任務", "supports_thesis": index % 2 == 0} for index in range(count)],
    }


def claims(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"version": "ClaimClassificationV1", "claims": items}


def blind_read(*, thesis_match: bool = True, candidate_sha: str = FINAL_SHA) -> dict[str, Any]:
    return {
        "version": "BlindReadResultV1",
        "candidate_sha256": candidate_sha,
        "blind_input_sha256": BLIND_INPUT_SHA,
        "summary_one_sentence": "讀者能理解主張，也知道要先查證哪些資訊。",
        "thesis_match": thesis_match,
        "confusing_sections": ["第二節可以更短"],
        "low_information_sections": ["第五節資訊量偏低"],
        "reader_questions": ["下一步要看哪個證據？"],
    }


def legacy_candidate() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": "legacy-public-review-001",
        "mode": "optimize",
        "articles": [
            {
                "article_id": "PUBLIC-REVIEW-001",
                "canonical_path": "/public-review-001/",
                "source_file": "content/public-review-001.md",
                "current": {"title": "原標題", "description": "原描述", "answer": "原答案"},
                "proposed": {"title": "新標題", "description": "新描述", "answer": "新答案"},
            }
        ],
    }


def manifest(
    selected: list[dict[str, Any]] | None = None,
    artifacts: dict[str, Any] | None = None,
    *,
    final_sha: str = FINAL_SHA,
) -> dict[str, Any]:
    base_brief = brief()
    artifacts = artifacts or {"brief": base_brief}
    return {
        "version": "EditorialManifestV1",
        "run_id": base_brief["run_id"],
        "article_identity": base_brief["article_identity"],
        "brief_sha256": contracts.artifact_sha256(base_brief),
        "selected_stages": selected or [],
        "artifacts": artifacts,
        "artifact_sha256": {name: contracts.artifact_sha256(value) for name, value in artifacts.items()},
        "final_candidate_sha256": final_sha,
    }


def evaluate(name: str, payload: dict[str, Any], expected_valid: bool, expected_findings: list[str]) -> dict[str, Any]:
    report = contracts.validate_manifest(payload)
    actual_findings = report["findings"]
    passed = report["valid"] is expected_valid and actual_findings == expected_findings
    return {
        "name": name,
        "passed": passed,
        "expected_valid": expected_valid,
        "actual_valid": report["valid"],
        "expected_findings": expected_findings,
        "actual_findings": actual_findings,
        "stable_summary": contracts.stable_json_summary(report),
    }


def build_cases() -> list[tuple[str, dict[str, Any], bool, list[str]]]:
    all_claim_types = claims(
        [
            {"type": "verifiable_fact", "text": "公開資料顯示 A", "evidence": {"url": "https://example.invalid/a"}},
            {"type": "interpretation", "text": "這代表讀者可能需要比較"},
            {"type": "product_explanation", "text": "工具會拆分輸入與輸出"},
            {"type": "subjective_guidance", "text": "可依情境調整下一步"},
            {"type": "common_knowledge", "text": "閱讀前先確認目標通常有幫助"},
        ]
    )
    full_artifacts = {
        "brief": brief(),
        "content_plan": content_plan(3),
        "claim_classification": all_claim_types,
        "blind_read": blind_read(),
    }
    cases: list[tuple[str, dict[str, Any], bool, list[str]]] = [
        ("core_only_without_optional_artifacts", manifest(), True, []),
        (
            "reordered_all_stages_three_sections",
            manifest(
                [stage("blind_read_v1", 30), stage("content_plan_v1", 10), stage("claim_classification_v1", 20)],
                full_artifacts,
            ),
            True,
            [],
        ),
    ]
    for count in (0, 3, 7):
        cases.append(
            (
                f"content_plan_{count}_sections",
                manifest([stage("content_plan_v1", 1)], {"brief": brief(), "content_plan": content_plan(count)}),
                True,
                [],
            )
        )
    cases.extend(
        [
            (
                "all_claim_types_without_nonfact_citations",
                manifest([stage("claim_classification_v1", 1)], {"brief": brief(), "claim_classification": all_claim_types}),
                True,
                [],
            ),
            (
                "verifiable_fact_without_evidence_fails",
                manifest(
                    [stage("claim_classification_v1", 1)],
                    {"brief": brief(), "claim_classification": claims([{"type": "verifiable_fact", "text": "A"}])},
                ),
                False,
                ["verifiable_fact_evidence_missing"],
            ),
            (
                "high_risk_without_evidence_fails",
                manifest(
                    [stage("claim_classification_v1", 1)],
                    {"brief": brief(), "claim_classification": claims([{"type": "interpretation", "text": "A", "risk_class": "high"}])},
                ),
                False,
                ["unverified_high_risk_claim"],
            ),
            (
                "unsupported_claim_type_fails",
                manifest(
                    [stage("claim_classification_v1", 1)],
                    {"brief": brief(), "claim_classification": claims([{"type": "freeform", "text": "A"}])},
                ),
                False,
                ["claim_type_unsupported"],
            ),
            (
                "blind_evidence_lists_do_not_block",
                manifest([stage("blind_read_v1", 1)], {"brief": brief(), "blind_read": blind_read()}),
                True,
                [],
            ),
            (
                "blind_thesis_mismatch_blocks",
                manifest([stage("blind_read_v1", 1)], {"brief": brief(), "blind_read": blind_read(thesis_match=False)}),
                False,
                ["blind_thesis_mismatch"],
            ),
            (
                "blind_candidate_sha_mismatch_fails",
                manifest([stage("blind_read_v1", 1)], {"brief": brief(), "blind_read": blind_read(candidate_sha="c" * 64)}),
                False,
                ["artifact_sha_mismatch"],
            ),
        ]
    )
    missing_core = manifest()
    missing_core["artifacts"] = {}
    missing_core["artifact_sha256"] = {}
    unsupported_version = manifest()
    unsupported_version["version"] = "EditorialManifestV0"
    hash_mismatch = manifest()
    hash_mismatch["artifact_sha256"]["brief"] = "0" * 64
    identity_mismatch = manifest()
    identity_mismatch["article_identity"] = {"id": "OTHER", "canonical_path": "/other/"}
    cases.extend(
        [
            ("missing_core_fails_closed", missing_core, False, ["missing_required_artifact"]),
            ("unsupported_manifest_version_fails_closed", unsupported_version, False, ["schema_version_unsupported"]),
            ("artifact_sha_mismatch_fails_closed", hash_mismatch, False, ["artifact_sha_mismatch"]),
            ("article_identity_mismatch_fails_closed", identity_mismatch, False, ["article_identity_mismatch"]),
            (
                "selected_artifact_missing_fails_closed",
                manifest([stage("content_plan_v1", 1)]),
                False,
                ["selected_stage_artifact_missing"],
            ),
        ]
    )
    free_action_stage = stage("content_plan_v1", 1)
    free_action_stage["retry"] = {"max_attempts": 3}
    duplicate_stage = [stage("content_plan_v1", 1), stage("content_plan_v1", 2)]
    duplicate_stage_artifacts = {"brief": brief(), "content_plan": content_plan(1)}
    duplicate_sequence = [stage("content_plan_v1", 1), stage("claim_classification_v1", 1)]
    duplicate_sequence_artifacts = {"brief": brief(), "content_plan": content_plan(1), "claim_classification": claims([])}
    wrong_output = stage("content_plan_v1", 1)
    wrong_output["expected_output"] = "claim_classification"
    invalid_policy = stage("content_plan_v1", 1, policy="publish-v1")
    boolean_sequence = stage("content_plan_v1", True)
    cases.extend(
        [
            ("free_action_in_stage_declaration_fails_closed", manifest([free_action_stage]), False, ["schema_version_unsupported"]),
            ("duplicate_stage_id_fails_closed", manifest(duplicate_stage, duplicate_stage_artifacts), False, ["schema_version_unsupported"]),
            ("duplicate_sequence_fails_closed", manifest(duplicate_sequence, duplicate_sequence_artifacts), False, ["schema_version_unsupported"]),
            ("artifact_mapping_collision_fails_closed", manifest([wrong_output]), False, ["schema_version_unsupported"]),
            ("publication_policy_rejected", manifest([invalid_policy]), False, ["schema_version_unsupported"]),
            (
                "boolean_sequence_ambiguity_fails_closed",
                manifest([boolean_sequence], {"brief": brief(), "content_plan": content_plan(1)}),
                False,
                ["schema_version_unsupported"],
            ),
        ]
    )
    legacy = legacy_candidate()
    validate_candidate(legacy)
    legacy_manifest = manifest()
    legacy_manifest["legacy_candidate"] = legacy
    legacy_manifest["legacy_candidate_sha256"] = contracts.artifact_sha256(legacy)
    tampered_legacy = deepcopy(legacy_manifest)
    tampered_legacy["legacy_candidate_sha256"] = "0" * 64
    invalid_legacy = deepcopy(legacy_manifest)
    invalid_legacy["legacy_candidate"] = {**legacy, "mode": "bad-mode"}
    cases.extend(
        [
            ("legacy_candidate_boundary_valid", legacy_manifest, True, []),
            ("legacy_candidate_hash_tamper_fails_closed", tampered_legacy, False, ["publisher_candidate_incompatible"]),
            ("legacy_candidate_schema_invalid_fails_closed", invalid_legacy, False, ["publisher_candidate_incompatible"]),
        ]
    )
    return cases


def main() -> int:
    cases = [evaluate(name, payload, valid, findings) for name, payload, valid, findings in build_cases()]
    legacy = legacy_candidate()
    before = deepcopy(legacy)
    legacy_manifest = manifest()
    legacy_manifest["legacy_candidate"] = legacy
    legacy_manifest["legacy_candidate_sha256"] = contracts.artifact_sha256(legacy)
    contracts.validate_manifest(legacy_manifest)
    mutation_check = {
        "name": "legacy_candidate_not_mutated_by_vnext_validation",
        "passed": legacy == before,
        "before_sha256": contracts.artifact_sha256(before),
        "after_sha256": contracts.artifact_sha256(legacy),
    }
    output = {
        "summary": {
            "total_cases": len(cases) + 1,
            "passed_cases": sum(1 for case in cases if case["passed"]) + int(mutation_check["passed"]),
            "failed_cases": [case["name"] for case in cases if not case["passed"]],
            "mutation_check_passed": mutation_check["passed"],
        },
        "cases": cases,
        "legacy_mutation_check": mutation_check,
    }
    output_path = Path(__file__).with_name("public_reproducer_results.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if output["summary"]["passed_cases"] == output["summary"]["total_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

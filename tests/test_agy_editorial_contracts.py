from __future__ import annotations

from copy import deepcopy

from scripts import agy_editorial_contracts as contracts
from scripts.agy_seo_copy_pipeline import validate_candidate


def _brief() -> dict[str, object]:
    return {
        "version": "ArticleBriefV2",
        "run_id": "writer-vnext-test-001",
        "article_identity": {"id": "TEST-001", "canonical_path": "/test-001/"},
        "reader_question": "這個概念在實際選擇中怎麼用？",
        "target_reader": "正在比較選項的讀者",
        "search_intent": "informational",
        "thesis": "先區分可驗證事實與個人解讀，才能做出較穩健的選擇。",
        "reader_outcome": "讀者能列出下一步要查證的資訊。",
        "scope": "一般資訊整理",
        "anti_goals": ["不替讀者做個人決定"],
        "evidence_policy": "cite-verifiable-claims",
        "risk_class": "medium",
    }


def _stage(stage_type: str, sequence: int) -> dict[str, object]:
    return {
        "stage_type": stage_type,
        "sequence": sequence,
        "required_inputs": ["ArticleBriefV2"],
        "expected_output": contracts.STAGE_ARTIFACTS[stage_type],
        "blocking_policy": "blocking-v1",
    }


def _manifest(selected: list[dict[str, object]] | None = None, artifacts: dict[str, object] | None = None) -> dict[str, object]:
    brief = _brief()
    artifacts = artifacts or {"brief": brief}
    return {
        "version": "EditorialManifestV1",
        "run_id": brief["run_id"],
        "article_identity": brief["article_identity"],
        "brief_sha256": contracts.artifact_sha256(brief),
        "selected_stages": selected or [],
        "artifacts": artifacts,
        "artifact_sha256": {name: contracts.artifact_sha256(value) for name, value in artifacts.items()},
        "final_candidate_sha256": "a" * 64,
    }


def test_core_only_and_unselected_artifacts_are_valid() -> None:
    report = contracts.validate_manifest(_manifest())
    assert report == {"blocking": False, "findings": [], "valid": True}


def test_optional_stages_are_independent_reorderable_and_content_plan_is_unbounded() -> None:
    for count in (0, 3, 7):
        plan = {
            "version": "ContentPlanV1",
            "sections": [{"purpose": f"目的 {index}", "supports_thesis": True} for index in range(count)],
        }
        claims = {"version": "ClaimClassificationV1", "claims": []}
        blind = {
            "version": "BlindReadResultV1",
            "candidate_sha256": "a" * 64,
            "blind_input_sha256": "b" * 64,
            "summary_one_sentence": "讀者能理解中心主張。",
            "thesis_match": True,
            "confusing_sections": ["可再說明"],
            "low_information_sections": [],
            "reader_questions": ["下一步怎麼做？"],
        }
        artifacts = {"brief": _brief(), "content_plan": plan, "claim_classification": claims, "blind_read": blind}
        selected = [_stage("blind_read_v1", 30), _stage("content_plan_v1", 10), _stage("claim_classification_v1", 20)]
        assert contracts.validate_manifest(_manifest(selected, artifacts))["valid"] is True


def test_selected_stage_sequence_rejects_booleans() -> None:
    for value in (True, False):
        report = contracts.validate_manifest(_manifest([_stage("content_plan_v1", value)]))
        assert "schema_version_unsupported" in report["findings"]


def test_fail_closed_for_core_hash_selected_stage_claim_and_blind_thesis() -> None:
    missing_thesis = _manifest()
    missing_thesis["artifacts"] = {"brief": {key: value for key, value in _brief().items() if key != "thesis"}}
    missing_thesis["artifact_sha256"] = {"brief": contracts.artifact_sha256(missing_thesis["artifacts"]["brief"])}
    assert "missing_thesis" in contracts.validate_manifest(missing_thesis)["findings"]

    selected = [_stage("claim_classification_v1", 1)]
    assert "selected_stage_artifact_missing" in contracts.validate_manifest(_manifest(selected))["findings"]

    claims = {"version": "ClaimClassificationV1", "claims": [{"type": "verifiable_fact", "text": "可驗證的說法"}]}
    report = contracts.validate_manifest(_manifest(selected, {"brief": _brief(), "claim_classification": claims}))
    assert "verifiable_fact_evidence_missing" in report["findings"]

    blind = {
        "version": "BlindReadResultV1", "candidate_sha256": "a" * 64, "blind_input_sha256": "b" * 64,
        "summary_one_sentence": "摘要", "thesis_match": False, "confusing_sections": [], "low_information_sections": [], "reader_questions": [],
    }
    report = contracts.validate_manifest(_manifest([_stage("blind_read_v1", 1)], {"brief": _brief(), "blind_read": blind}))
    assert report["findings"] == ["blind_thesis_mismatch"]


def test_hash_mismatch_and_nonblocking_subjective_blind_evidence() -> None:
    manifest = _manifest()
    manifest["artifact_sha256"]["brief"] = "0" * 64
    assert contracts.validate_manifest(manifest)["findings"] == ["artifact_sha_mismatch"]

    claims = {"version": "ClaimClassificationV1", "claims": [{"type": "subjective_guidance", "text": "可依情境自行調整"}]}
    assert contracts.validate_manifest(_manifest([_stage("claim_classification_v1", 1)], {"brief": _brief(), "claim_classification": claims}))["valid"] is True


def test_legacy_candidate_uses_existing_publisher_validation_boundary() -> None:
    candidate = {
        "schema_version": 1,
        "run_id": "legacy-001",
        "mode": "optimize",
        "articles": [{
            "article_id": "TEST-001", "canonical_path": "/test-001/", "source_file": "content/test.md",
            "current": {"title": "原標題", "description": "原描述", "answer": "原答案"},
            "proposed": {"title": "新標題", "description": "新描述", "answer": "新答案"},
        }],
    }
    validate_candidate(candidate)
    manifest = _manifest()
    manifest["legacy_candidate"] = candidate
    manifest["legacy_candidate_sha256"] = contracts.artifact_sha256(candidate)
    assert contracts.validate_manifest(manifest)["valid"] is True
    tampered = deepcopy(manifest)
    tampered["legacy_candidate_sha256"] = "0" * 64
    assert tampered and contracts.validate_manifest(tampered)["findings"] == ["publisher_candidate_incompatible"]

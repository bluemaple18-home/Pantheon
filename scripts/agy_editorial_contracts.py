"""Writer vNext 的純宣告式 editorial artifact contract。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.agy_seo_copy_pipeline import CandidateValidationError, validate_candidate

STAGE_ARTIFACTS = {
    "content_plan_v1": "content_plan",
    "claim_classification_v1": "claim_classification",
    "blind_read_v1": "blind_read",
}
MANIFEST_REQUIRED_FIELDS = {
    "version",
    "orchestration_mode",
    "run_id",
    "article_identity",
    "brief_sha256",
    "selected_stages",
    "artifacts",
    "artifact_sha256",
    "final_candidate_sha256",
}
MANIFEST_OPTIONAL_FIELDS = {"legacy_candidate", "legacy_candidate_sha256"}
MANIFEST_ORCHESTRATION_MODE = "writer_vnext_opt_in_v1"
CLAIM_TYPES = {"verifiable_fact", "interpretation", "product_explanation", "subjective_guidance", "common_knowledge"}
FINDING_CODES = {
    "missing_required_artifact", "schema_version_unsupported", "artifact_sha_mismatch", "article_identity_mismatch",
    "missing_reader_question", "missing_thesis", "selected_stage_artifact_missing", "content_plan_purpose_missing",
    "content_plan_supports_thesis_invalid", "claim_type_unsupported", "verifiable_fact_evidence_missing",
    "unverified_high_risk_claim", "blind_thesis_mismatch", "publisher_candidate_incompatible",
}


def artifact_sha256(payload: object) -> str:
    """回傳穩定 JSON artifact hash。"""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def stable_json_summary(report: dict[str, object]) -> str:
    """輸出供 manifest trace 使用的穩定 JSON。"""
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _add(findings: set[str], code: str) -> None:
    if code not in FINDING_CODES:
        raise ValueError(f"unknown finding code: {code}")
    findings.add(code)


def _validate_brief(brief: object, findings: set[str]) -> dict[str, Any] | None:
    if not isinstance(brief, dict):
        _add(findings, "missing_required_artifact")
        return None
    required = {"version", "run_id", "article_identity", "reader_question", "target_reader", "search_intent", "thesis", "reader_outcome", "scope", "anti_goals", "evidence_policy", "risk_class"}
    if set(brief) != required or brief.get("version") != "ArticleBriefV2":
        _add(findings, "schema_version_unsupported")
    for name in required - {"article_identity", "anti_goals"}:
        if not _string(brief.get(name)):
            _add(findings, "missing_thesis" if name == "thesis" else "missing_reader_question" if name == "reader_question" else "missing_required_artifact")
    identity = brief.get("article_identity")
    if not isinstance(identity, dict) or not _string(identity.get("id")):
        _add(findings, "article_identity_mismatch")
    if not isinstance(brief.get("anti_goals"), list):
        _add(findings, "missing_required_artifact")
    return brief


def validate_article_brief(brief: object) -> dict[str, Any]:
    """驗證 Writer vNext 的 ArticleBriefV2，缺欄位時 fail closed。"""
    findings: set[str] = set()
    result = _validate_brief(brief, findings)
    if findings or result is None:
        raise ValueError(stable_json_summary({"findings": sorted(findings)}))
    return result


def _validate_selected(selected: object, findings: set[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(selected, list):
        _add(findings, "missing_required_artifact")
        return {}
    result: dict[str, dict[str, Any]] = {}
    sequences: set[int] = set()
    for item in selected:
        if not isinstance(item, dict) or set(item) != {"stage_type", "sequence", "required_inputs", "expected_output", "blocking_policy"}:
            _add(findings, "schema_version_unsupported")
            continue
        stage_type = item.get("stage_type")
        if stage_type not in STAGE_ARTIFACTS or stage_type in result or type(item.get("sequence")) is not int or item["sequence"] in sequences:
            _add(findings, "schema_version_unsupported")
            continue
        if item.get("expected_output") != STAGE_ARTIFACTS[stage_type] or item.get("blocking_policy") not in {"blocking-v1", "evidence-only-v1"} or not isinstance(item.get("required_inputs"), list):
            _add(findings, "schema_version_unsupported")
            continue
        sequences.add(item["sequence"])
        result[stage_type] = item
    return result


def _validate_content_plan(value: object, findings: set[str]) -> None:
    if not isinstance(value, dict) or value.get("version") != "ContentPlanV1" or not isinstance(value.get("sections"), list):
        _add(findings, "schema_version_unsupported")
        return
    for section in value["sections"]:
        if not isinstance(section, dict) or not _string(section.get("purpose")):
            _add(findings, "content_plan_purpose_missing")
        if not isinstance(section.get("supports_thesis") if isinstance(section, dict) else None, bool):
            _add(findings, "content_plan_supports_thesis_invalid")


def _validate_claims(value: object, findings: set[str]) -> None:
    if not isinstance(value, dict) or value.get("version") != "ClaimClassificationV1" or not isinstance(value.get("claims"), list):
        _add(findings, "schema_version_unsupported")
        return
    for claim in value["claims"]:
        if not isinstance(claim, dict) or claim.get("type") not in CLAIM_TYPES:
            _add(findings, "claim_type_unsupported")
            continue
        evidence = claim.get("evidence") or claim.get("source")
        high_risk = claim.get("risk_class") == "high"
        if high_risk and not evidence:
            _add(findings, "unverified_high_risk_claim")
        if claim["type"] == "verifiable_fact" and not evidence:
            _add(findings, "verifiable_fact_evidence_missing")


def _validate_blind(value: object, final_sha: object, findings: set[str]) -> None:
    required = {"version", "candidate_sha256", "blind_input_sha256", "summary_one_sentence", "thesis_match", "confusing_sections", "low_information_sections", "reader_questions"}
    if not isinstance(value, dict) or set(value) != required or value.get("version") != "BlindReadResultV1":
        _add(findings, "schema_version_unsupported")
        return
    if value.get("candidate_sha256") != final_sha or not _sha(value.get("blind_input_sha256")):
        _add(findings, "artifact_sha_mismatch")
    if not _string(value.get("summary_one_sentence")) or not isinstance(value.get("thesis_match"), bool) or any(not isinstance(value.get(name), list) for name in ("confusing_sections", "low_information_sections", "reader_questions")):
        _add(findings, "schema_version_unsupported")
    if value.get("thesis_match") is False:
        _add(findings, "blind_thesis_mismatch")


def validate_manifest(manifest: object) -> dict[str, object]:
    """驗證 manifest；所有資料問題以可重現 finding 回傳，絕不補值。"""
    findings: set[str] = set()
    if not isinstance(manifest, dict):
        raise TypeError("EditorialManifestV1 must be an object")
    fields = set(manifest)
    has_legacy_candidate = "legacy_candidate" in manifest
    has_legacy_sha = "legacy_candidate_sha256" in manifest
    if (
        not MANIFEST_REQUIRED_FIELDS <= fields
        or bool(fields - MANIFEST_REQUIRED_FIELDS - MANIFEST_OPTIONAL_FIELDS)
        or manifest.get("version") != "EditorialManifestV1"
        or manifest.get("orchestration_mode") != MANIFEST_ORCHESTRATION_MODE
        or has_legacy_candidate != has_legacy_sha
    ):
        _add(findings, "schema_version_unsupported")
    artifacts = manifest.get("artifacts")
    hashes = manifest.get("artifact_sha256")
    if not isinstance(artifacts, dict) or not isinstance(hashes, dict):
        _add(findings, "missing_required_artifact")
        artifacts, hashes = {}, {}
    brief = _validate_brief(artifacts.get("brief"), findings)
    if brief is not None:
        if manifest.get("run_id") != brief.get("run_id") or manifest.get("article_identity") != brief.get("article_identity"):
            _add(findings, "article_identity_mismatch")
        if manifest.get("brief_sha256") != artifact_sha256(brief):
            _add(findings, "artifact_sha_mismatch")
    for name, value in artifacts.items():
        if hashes.get(name) != artifact_sha256(value):
            _add(findings, "artifact_sha_mismatch")
    selected = _validate_selected(manifest.get("selected_stages"), findings)
    if not _sha(manifest.get("final_candidate_sha256")):
        _add(findings, "artifact_sha_mismatch")
    for stage_type, stage in selected.items():
        name = STAGE_ARTIFACTS[stage_type]
        if name not in artifacts:
            _add(findings, "selected_stage_artifact_missing")
        elif stage_type == "content_plan_v1":
            _validate_content_plan(artifacts[name], findings)
        elif stage_type == "claim_classification_v1":
            _validate_claims(artifacts[name], findings)
        else:
            _validate_blind(artifacts[name], manifest.get("final_candidate_sha256"), findings)
    if has_legacy_candidate and has_legacy_sha:
        legacy = manifest.get("legacy_candidate")
        try:
            validate_candidate(legacy)
        except (CandidateValidationError, ValueError, TypeError):
            _add(findings, "publisher_candidate_incompatible")
        if manifest.get("legacy_candidate_sha256") != artifact_sha256(legacy):
            _add(findings, "publisher_candidate_incompatible")
    return {"blocking": bool(findings), "findings": sorted(findings), "valid": not findings}

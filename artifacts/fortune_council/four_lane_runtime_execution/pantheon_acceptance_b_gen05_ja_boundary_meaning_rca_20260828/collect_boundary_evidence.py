#!/usr/bin/env python3
"""Read-only RCA collector for gen05 JA boundary meaning rejection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path.cwd()))

from scripts import agy_multilingual_pipeline as multilingual


RUN_ROOT = Path(
    "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/"
    "auto-i18n-ja-1414b75a404721e95e74"
)
LANE_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/lanes/i18n-new")
FIXTURE_ROOT = Path("tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract")
OUT = Path(
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "pantheon_acceptance_b_gen05_ja_boundary_meaning_rca_20260828/"
    "boundary-rca-evidence.json"
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_categories(article: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "meta_description": sorted(
            multilingual._ja_boundary_target_categories(
                multilingual._ja_field_text(article, "meta_description")
            )
        ),
        "body": sorted(
            multilingual._ja_boundary_target_categories(
                multilingual._ja_field_text(article, "body")
            )
        ),
        "visible": sorted(multilingual._ja_boundary_target_categories(multilingual._visible_text(article))),
    }


def candidate_summary(base: Path, rel: str, brief: dict[str, Any]) -> dict[str, Any]:
    path = base / rel / "candidate.json"
    if not path.exists():
        return {"rel": rel, "exists": False}
    candidate = load_json(path)
    article = candidate["articles"][0]
    return {
        "rel": rel,
        "exists": True,
        "sha256": sha256(path),
        "article_id": article.get("article_id"),
        "title": article.get("title"),
        "description": article.get("description"),
        "category_presence": target_categories(article),
        "translation_findings": multilingual.translation_findings(brief, candidate["articles"]),
        "external_review": load_json(base / rel / "external-review.json")
        if (base / rel / "external-review.json").exists()
        else None,
        "deterministic_findings_file": load_json(base / rel / "deterministic-findings.json")
        if (base / rel / "deterministic-findings.json").exists()
        else None,
    }


def locale_plan_summary(base: Path, rel: str) -> dict[str, Any]:
    path = base / rel / "locale-plan.json"
    if not path.exists():
        return {"rel": rel, "exists": False}
    plan = load_json(path)
    article = plan["articles"][0]
    mappings = article.get("coverage_mapping", [])
    return {
        "rel": rel,
        "exists": True,
        "sha256": sha256(path),
        "native_search_intent": article.get("native_search_intent"),
        "outline": article.get("ordered_h2_outline"),
        "coverage_count": len(mappings),
        "coverage_slots": sorted({item.get("planned_h2_slot") or item.get("planned_h2") for item in mappings}),
        "contains_safety_boundary_field": any("safety_boundary" in item for item in mappings),
    }


def prompt_summary(prompt_sha256: str) -> list[dict[str, Any]]:
    found = []
    for path in sorted(LANE_ROOT.rglob("*.json")):
        try:
            payload = load_json(path)
        except Exception:
            continue
        if payload.get("prompt_sha256") != prompt_sha256:
            continue
        prompt = str(payload.get("prompt") or "")
        protected_index = prompt.find("JA protected_constraints")
        input_index = prompt.find("article input:")
        findings_index = prompt.find("findings:")
        excerpt_start = max(0, protected_index - 160) if protected_index >= 0 else 0
        excerpt_end = min(len(prompt), excerpt_start + 1200)
        found.append(
            {
                "queue_rel": str(path.relative_to(LANE_ROOT)),
                "job_id": payload.get("job_id"),
                "role": payload.get("role"),
                "prompt_sha256": prompt_sha256,
                "prompt_length": len(prompt),
                "has_protected_constraints": "protected_constraints" in prompt,
                "has_required_fields": "required_fields" in prompt,
                "has_outcome_not_determined": "outcome_not_determined" in prompt,
                "has_findings_section": findings_index >= 0,
                "excerpt": prompt[excerpt_start:excerpt_end],
                "article_input_offset": input_index,
                "findings_offset": findings_index,
            }
        )
    return found


def fixture_summary(name: str) -> dict[str, Any]:
    brief = load_json(FIXTURE_ROOT / "brief.json")
    path = FIXTURE_ROOT / name
    candidate = load_json(path)
    article = candidate["articles"][0]
    return {
        "name": name,
        "sha256": sha256(path),
        "description": article.get("description"),
        "category_presence": target_categories(article),
        "translation_findings": multilingual.translation_findings(brief, candidate["articles"]),
    }


def main() -> int:
    brief = load_json(RUN_ROOT / "brief.json")
    source_package = multilingual._source_fact_package(brief)
    boundary_contract = multilingual._ja_boundary_contracts_for_brief(brief)
    operations = {
        "gen05_plan": load_json(RUN_ROOT / "generations/05/plan-operation.json"),
        "gen05_article": load_json(RUN_ROOT / "generations/05/article-operation.json"),
        "gen05_reviewer": load_json(RUN_ROOT / "generations/05/reviewer-operation.json"),
    }
    evidence = {
        "run_root": str(RUN_ROOT),
        "target_run": RUN_ROOT.name,
        "brief_sha256": sha256(RUN_ROOT / "brief.json"),
        "source_package_sha256": hashlib.sha256(
            multilingual.compact_json_bytes(source_package)
        ).hexdigest(),
        "protected_constraint_categories": sorted(
            {
                constraint["category"]
                for article in boundary_contract["articles"]
                for constraint in article["protected_constraints"]
            }
        ),
        "protected_constraint_required_fields": sorted(
            {
                field
                for article in boundary_contract["articles"]
                for constraint in article["protected_constraints"]
                for field in constraint["required_fields"]
            }
        ),
        "protected_constraint_counts_by_category": {
            category: sum(
                1
                for article in boundary_contract["articles"]
                for constraint in article["protected_constraints"]
                if constraint["category"] == category
            )
            for category in sorted(
                {
                    constraint["category"]
                    for article in boundary_contract["articles"]
                    for constraint in article["protected_constraints"]
                }
            )
        },
        "continuation_state": load_json(RUN_ROOT / "continuation/state.json"),
        "generation_lifecycle": load_json(RUN_ROOT / "continuation/generation-lifecycle.json"),
        "generation_04_planning_result": load_json(RUN_ROOT / "generations/04/planning-result.json"),
        "generation_04_partial_decision": load_json(RUN_ROOT / "generations/04/partial-generation-decision.json"),
        "candidate_summaries": [
            candidate_summary(RUN_ROOT, rel, brief)
            for rel in ["attempts/01", "attempts/02", "attempts/03", "generations/05"]
        ],
        "locale_plan_summaries": [
            locale_plan_summary(RUN_ROOT, rel)
            for rel in ["attempts/01", "attempts/02", "attempts/03", "generations/04", "generations/05"]
        ],
        "operation_summaries": operations,
        "prompt_summaries": {
            key: prompt_summary(str(operation["prompt_sha256"]))
            for key, operation in operations.items()
        },
        "nearest_successful_fixture_contract": fixture_summary("corrected_test_only_candidate.json"),
        "negative_fixture_contracts": [
            fixture_summary("candidate_02.json"),
            fixture_summary("candidate_03.json"),
        ],
    }
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": "WROTE", "path": str(OUT), "sha256": sha256(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

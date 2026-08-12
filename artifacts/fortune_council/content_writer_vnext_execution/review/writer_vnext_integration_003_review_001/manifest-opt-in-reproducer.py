from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from scripts.agy_editorial_contracts import artifact_sha256, validate_manifest


def brief() -> dict[str, object]:
    return {
        "version": "ArticleBriefV2",
        "run_id": "run-1",
        "article_identity": {"id": "article-1"},
        "reader_question": "q",
        "target_reader": "reader",
        "search_intent": "intent",
        "thesis": "thesis",
        "reader_outcome": "outcome",
        "scope": "scope",
        "anti_goals": [],
        "evidence_policy": "policy",
        "risk_class": "low",
    }


def manifest_base() -> dict[str, object]:
    item = brief()
    return {
        "version": "EditorialManifestV1",
        "run_id": "run-1",
        "article_identity": {"id": "article-1"},
        "brief_sha256": artifact_sha256(item),
        "selected_stages": [],
        "artifacts": {"brief": item},
        "artifact_sha256": {"brief": artifact_sha256(item)},
        "final_candidate_sha256": "0" * 64,
    }


base = manifest_base()
cases = {
    "missing_orchestration_mode": dict(base),
    "wrong_orchestration_mode": {**base, "orchestration_mode": "legacy_shadow_ab"},
    "extra_free_state": {**base, "projection_state": "complete"},
    "expected_opt_in": {**base, "orchestration_mode": "writer_vnext_opt_in_v1"},
}

print(json.dumps({name: validate_manifest(payload) for name, payload in cases.items()}, ensure_ascii=False, sort_keys=True))

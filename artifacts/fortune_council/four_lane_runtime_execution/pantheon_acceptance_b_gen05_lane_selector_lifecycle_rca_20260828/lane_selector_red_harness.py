#!/usr/bin/env python3
"""provider=0 RCA harness：重現 gen05 active run 未被 lane selector 選中的狀態。"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_gemini_coordinator as coordinator


RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
ARTICLE_ID = "V2-TAROT-DEATH-MONEY"
LOCALE = "ja"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _brief(run_id: str = RUN_ID, *, lane: str | None = None) -> dict[str, Any]:
    brief: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"{ARTICLE_ID}:{LOCALE}",
                "locale": LOCALE,
                "source_article_id": ARTICLE_ID,
                "source_path": "/articles/tarot-death-money",
                "source_sha256": "a" * 64,
                "source": {
                    "article_id": ARTICLE_ID,
                    "canonical_path": "/articles/tarot-death-money",
                    "title": "placeholder",
                    "description": "placeholder",
                    "answer": "placeholder",
                    "tags": ["tarot"],
                    "faq": [{"question": "q", "answer": "a"}],
                    "bodySections": [
                        {"heading": "h1", "paragraphs": ["p"]},
                        {"heading": "h2", "paragraphs": ["p"]},
                        {"heading": "h3", "paragraphs": ["p"]},
                        {"heading": "h4", "paragraphs": ["p"]},
                    ],
                },
            }
        ],
    }
    if lane is not None:
        brief["lane"] = lane
    return brief


def _state(
    run_dir: Path,
    *,
    lane: str = "i18n-new",
    include_mode: bool,
    include_routing_schema: bool,
    envelope_lane: str = "i18n-new",
) -> dict[str, Any]:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    state: dict[str, Any] = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "run_dir": str(run_dir.resolve()),
        "status": "active",
        "registered_at": now,
        "updated_at": now,
        "lane": lane,
        "identity_envelope": coordinator._build_identity_envelope(
            "translate_existing",
            envelope_lane,
            [ARTICLE_ID],
        ),
    }
    if include_mode:
        state["mode"] = "translate_existing"
    if include_routing_schema:
        state["routing_schema_version"] = coordinator.ROUTING_SCHEMA_VERSION
    return state


def _run_case(
    root: Path,
    name: str,
    *,
    state: dict[str, Any],
    brief: dict[str, Any],
) -> dict[str, Any]:
    queue_root = root / name / "queue"
    repo_root = root / name / "repo"
    run_dir = queue_root / "translation-runs" / RUN_ID
    repo_root.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", brief)
    state = {**state, "run_dir": str(run_dir.resolve())}
    state_path = coordinator._state_path(RUN_ID, queue_root)
    coordinator.atomic_write_json(state_path, state)

    calls = {"tick": 0, "process": 0}

    def tick(_run_dir: Path, _job_queue_root: Path) -> dict[str, object]:
        calls["tick"] += 1
        return {"status": "synthetic-complete", "provider_calls": 0}

    def process(_root: Path, *args: object, **kwargs: object) -> dict[str, str]:
        calls["process"] += 1
        return {"status": "processed"}

    before_state = json.loads(state_path.read_text(encoding="utf-8"))
    integrity_block = coordinator._active_run_integrity_block(
        [copy.deepcopy(before_state)],
        exact_run_ids=frozenset({RUN_ID}),
    )
    lane_selector_result = coordinator._lane_for_state_or_none(
        copy.deepcopy(before_state),
        set(),
    )
    summary = coordinator.cycle_once(
        queue_root,
        tick=tick,
        process=process,
        repo_root=repo_root,
        lane_mode=True,
        exact_run_ids=[RUN_ID],
    )
    after_state = json.loads(state_path.read_text(encoding="utf-8"))
    return {
        "case": name,
        "input_state_keys": sorted(before_state),
        "integrity_block": integrity_block,
        "lane_selector_result": lane_selector_result,
        "summary": summary,
        "calls": calls,
        "state_after": after_state,
    }


def main() -> int:
    evidence_dir = Path(__file__).resolve().parent
    output = evidence_dir / "lane-selector-red-harness-result.json"
    fixture_root = Path(tempfile.mkdtemp(prefix="pantheon-gen05-lane-selector-rca-"))
    try:
        coordinator._validate_formal_runtime = lambda *_args, **_kwargs: {
            "status": "PASS",
            "provider_calls": 0,
            "harness": "provider-zero",
        }
        coordinator.publisher.legacy_article_ids = lambda _repo: set()

        production_shape = _run_case(
            fixture_root,
            "production_partial_legacy_state",
            state=_state(
                fixture_root / "unused",
                include_mode=False,
                include_routing_schema=False,
            ),
            brief=_brief(),
        )
        schema_complete = _run_case(
            fixture_root,
            "schema_complete_counterfactual",
            state=_state(
                fixture_root / "unused",
                include_mode=True,
                include_routing_schema=True,
            ),
            brief=_brief(),
        )
        lane_drift_negative = _run_case(
            fixture_root,
            "lane_drift_negative",
            state=_state(
                fixture_root / "unused",
                lane="i18n-rewrite",
                envelope_lane="i18n-new",
                include_mode=False,
                include_routing_schema=False,
            ),
            brief=_brief(),
        )
        symptom_reproduced = (
            production_shape["integrity_block"] is None
            and production_shape["lane_selector_result"] is None
            and production_shape["summary"].get("status") == "ok"
            and production_shape["summary"].get("active") == 1
            and production_shape["summary"].get("complete") == 0
            and production_shape["summary"].get("runner", {}).get("status") == "idle"
            and production_shape["calls"] == {"tick": 0, "process": 0}
        )
        counterfactual_advances = (
            schema_complete["summary"].get("status") == "ok"
            and schema_complete["summary"].get("complete") == 1
            and schema_complete["calls"] == {"tick": 1, "process": 0}
        )
        negative_blocks = (
            lane_drift_negative["summary"].get("status") == "blocked"
            and lane_drift_negative["summary"].get("reason")
            == "active run registry is dangling"
            and lane_drift_negative["calls"] == {"tick": 0, "process": 0}
        )
        result = {
            "schema_version": 1,
            "status": "RED" if symptom_reproduced else "HARNESS_INVALID",
            "provider_calls": 0,
            "fixture_root": str(fixture_root),
            "target_run": RUN_ID,
            "symptom": "exact_run_active_1_selected_0_runner_idle",
            "symptom_reproduced": symptom_reproduced,
            "counterfactual_schema_complete_advances": counterfactual_advances,
            "fail_closed_negative_blocks": negative_blocks,
            "cases": {
                "production_partial_legacy_state": production_shape,
                "schema_complete_counterfactual": schema_complete,
                "lane_drift_negative": lane_drift_negative,
            },
        }
        _write_json(output, result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1 if symptom_reproduced else 2
    finally:
        shutil.rmtree(fixture_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

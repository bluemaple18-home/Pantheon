#!/usr/bin/env python3
"""從唯讀 runtime snapshot 建立日韓翻譯失敗分類與離線 replay。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_multilingual_pipeline as multilingual  # noqa: E402


SAMPLE_SIZES = {"ja": 20, "ko": 20, "en": 10}
TERMINAL_STATUSES = {"complete", "failed"}
TARGET_REVIEWER_CODES = {"SOURCE_SYNTAX_TRANSFER", "NON_NATIVE_SEARCH_INTENT"}
DASHES = "-‐‑‒–—―"


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return payload


def _codes(payload: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(finding["code"])
            for article in payload.get("articles", [])
            if isinstance(article, dict)
            for finding in article.get("findings", [])
            if isinstance(finding, dict) and str(finding.get("code") or "").strip()
        }
    )


def _latest_attempt_file(run_dir: Path, name: str) -> Path | None:
    paths = [
        attempt / name
        for attempt in multilingual._generation_directories(run_dir / "attempts")
        if (attempt / name).is_file()
    ]
    return paths[-1] if paths else None


def _source_class_lookup(ledger: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for key, source_class in (
        ("published_runs", "i18n-new"),
        ("rewrite_released_runs", "i18n-rewrite"),
    ):
        for record in ledger.get(key, []):
            if not isinstance(record, dict):
                continue
            for run_id in record.get("translation_run_ids", []):
                run_id = str(run_id)
                prior = lookup.setdefault(run_id, source_class)
                if prior != source_class:
                    raise ValueError(f"translation source class collision: {run_id}")
    return lookup


def _base_run_id(run_id: str) -> str:
    return run_id.split("-replacement-", 1)[0]


def _source_derived_authority_false_negative(
    brief: dict[str, Any],
    external: dict[str, Any],
    message: str,
) -> dict[str, Any] | None:
    match = re.fullmatch(
        r"locale plan native locale language differs for article-(\d+)\.(.+)",
        message,
    )
    if match is None:
        return None
    article_index = int(match.group(1)) - 1
    field = match.group(2)
    if not field.startswith("coverage_note["):
        return None
    note_match = re.fullmatch(r"coverage_note\[(\d+)\]", field)
    if note_match is None:
        return None
    target = brief["articles"][article_index]
    external_item = external["articles"][article_index]
    expected_facts = multilingual._source_fact_package(brief)["articles"][article_index]["facts"]
    mappings = multilingual._canonicalize_external_coverage_mappings(
        expected_facts,
        external_item.get("coverage_mapping"),
        slot=f"article-{article_index + 1:02d}",
    )
    value = str(mappings[int(note_match.group(1))]["coverage_note"])
    source_text = multilingual._visible_text(target["source"])
    source_normalized = re.sub(r"[^A-Za-z0-9]", "", source_text).casefold()
    authority_pattern = re.compile(
        rf"[A-Za-z][A-Za-z0-9]*(?:(?:[{re.escape(DASHES)}]|\s)+[A-Za-z0-9]+)+"
    )
    authorities: list[str] = []

    def remove_if_source_derived(span_match: re.Match[str]) -> str:
        span = span_match.group(0)
        normalized = re.sub(r"[^A-Za-z0-9]", "", span).casefold()
        if len(normalized) >= 8 and normalized in source_normalized:
            authorities.append(span)
            return ""
        return span

    remainder = authority_pattern.sub(remove_if_source_derived, value)
    if not authorities or re.search(r"[A-Za-z]", remainder):
        return None
    locale = str(target["locale"])
    if not multilingual._plan_matches_target_language(locale, remainder):
        return None
    return {
        "reason_code": "SOURCE_PROPER_NAME_DASH_NORMALIZATION",
        "field": field,
        "source_derived_authorities": authorities,
        "value_sha256": _sha256_bytes(value.encode("utf-8")),
    }


def _failed_plan_replay(run_dir: Path, brief: dict[str, Any]) -> dict[str, Any]:
    attempts = multilingual._generation_directories(run_dir / "attempts")
    failed_attempts = [
        attempt
        for attempt in attempts
        if (attempt / "external-plan.json").is_file()
        and not (attempt / "locale-plan.json").is_file()
    ]
    if not failed_attempts:
        raise ValueError(f"saved external plan missing for {brief['run_id']}")
    attempt = failed_attempts[-1]
    generation = int(attempt.name)
    prior_plan = multilingual._last_locale_plan(
        [run_dir / "attempts"],
        before_generation=generation,
    )
    history = []
    for prior_attempt in attempts:
        if int(prior_attempt.name) >= generation:
            break
        findings = multilingual._external_review_findings(brief, prior_attempt)
        if findings:
            history.append(findings)
    rebuild_by_slot = multilingual._rebuild_authority(brief, history)
    response_path = attempt / "external-plan.json"
    response_bytes = response_path.read_bytes()
    external = json.loads(response_bytes)
    replay: dict[str, Any] = {
        "run_id": str(brief["run_id"]),
        "generation": generation,
        "response_sha256": _sha256_bytes(response_bytes),
        "rebuild_by_slot": rebuild_by_slot,
        "result": "unexpected-pass",
        "error_type": None,
        "error_message": None,
        "false_negative": False,
        "false_negative_context": None,
    }
    try:
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=generation,
            rebuild_by_slot=rebuild_by_slot,
            prior_plan=prior_plan,
        )
    except ValueError as error:
        message = str(error)
        false_negative = _source_derived_authority_false_negative(
            brief,
            external,
            message,
        )
        replay.update(
            {
                "result": "rejected",
                "error_type": type(error).__name__,
                "error_message": message,
                "false_negative": false_negative is not None,
                "false_negative_context": false_negative,
            }
        )
    return replay


def _control_replays(entries: list[tuple[dict[str, Any], Path]]) -> list[dict[str, Any]]:
    selected: tuple[dict[str, Any], Path, Path] | None = None
    for state, run_dir in entries:
        for attempt in multilingual._generation_directories(run_dir / "attempts"):
            response_path = attempt / "external-plan.json"
            if response_path.is_file() and (attempt / "locale-plan.json").is_file():
                selected = (state, run_dir, attempt)
                break
        if selected is not None:
            break
    if selected is None:
        raise ValueError("no successful saved locale-plan response for controls")
    state, run_dir, attempt = selected
    brief = _read_json(run_dir / "brief.json")
    original = _read_json(attempt / "external-plan.json")
    generation = int(attempt.name)
    response_sha256 = _sha256_bytes((attempt / "external-plan.json").read_bytes())

    cases: list[tuple[str, dict[str, Any], bool]] = [
        ("positive_original", copy.deepcopy(original), True),
    ]
    shuffled = copy.deepcopy(original)
    shuffled["articles"][0]["coverage_mapping"].reverse()
    cases.append(("positive_fact_order_canonicalization", shuffled, True))
    missing = copy.deepcopy(original)
    missing["articles"][0]["coverage_mapping"].pop()
    cases.append(("negative_missing_fact", missing, False))
    duplicate = copy.deepcopy(original)
    duplicate["articles"][0]["coverage_mapping"][0] = copy.deepcopy(
        duplicate["articles"][0]["coverage_mapping"][1]
    )
    cases.append(("negative_duplicate_fact", duplicate, False))
    safety = copy.deepcopy(original)
    safety["articles"][0]["coverage_mapping"][0]["safety_boundary"] = not safety[
        "articles"
    ][0]["coverage_mapping"][0]["safety_boundary"]
    cases.append(("negative_wrong_safety_flag", safety, False))
    heading_slot = copy.deepcopy(original)
    heading_slot["articles"][0]["coverage_mapping"][0]["planned_h2_slot"] = "h2-5"
    cases.append(("negative_illegal_h2_slot", heading_slot, False))

    results = []
    for name, payload, expected_pass in cases:
        passed = True
        error_message = None
        try:
            multilingual._hydrate_locale_plan(
                brief,
                payload,
                generation=generation,
                rebuild_by_slot={"article-01": False},
                prior_plan=None,
            )
        except ValueError as error:
            passed = False
            error_message = str(error)
        results.append(
            {
                "case": name,
                "source_run_id": str(state["run_id"]),
                "source_response_sha256": response_sha256,
                "expected": "pass" if expected_pass else "reject",
                "actual": "pass" if passed else "reject",
                "matched_expectation": passed is expected_pass,
                "error_message": error_message,
            }
        )
    return results


def _write_json(path: Path, payload: object) -> None:
    path.write_bytes(_json_bytes(payload) + b"\n")


def _baseline_markdown(
    snapshot_at: str,
    taxonomy: dict[str, Any],
    replay: dict[str, Any],
) -> str:
    locale_counts = Counter(item["locale"] for item in taxonomy["runs"])
    stage_counts = Counter(item["primary_stage"] for item in taxonomy["runs"])
    outcome_counts = Counter(item["outcome_code"] for item in taxonomy["runs"])
    target_code_counts = Counter(
        code
        for item in taxonomy["runs"]
        for code in item["reviewer_codes"]
        if code in TARGET_REVIEWER_CODES
    )
    false_negatives = [item for item in replay["replays"] if item["false_negative"]]
    lines = [
        "---",
        "id: SLICE-JKQ-OBS-001",
        "status: OBSERVATION_COMPLETE",
        "type: evidence",
        "---",
        "",
        "# 日韓翻譯品質基線",
        "",
        f"- snapshot_at: `{snapshot_at}`",
        f"- sample: `ja={locale_counts['ja']}, ko={locale_counts['ko']}, en={locale_counts['en']}`",
        f"- primary_stage: `{json.dumps(dict(sorted(stage_counts.items())), ensure_ascii=False)}`",
        f"- unknown_or_generic: `{taxonomy['summary']['unknown_or_generic']}`",
        "- runtime sources: local-only 唯讀 queue snapshot 與 Publisher ledger；提交檔不保存絕對路徑或完整文章內容。",
        "",
        "## Harness contract",
        "",
        "```text",
        "harness: yes",
        "pattern: Classify and Act",
        "scope: 20 ja + 20 ko + 10 en terminal translation runs",
        "output_schema: locale/source_class/primary_stage/outcome/error/reviewer_codes/repair_route/evidence_digest",
        "stop_condition: 50 mutually-exclusive rows; unknown_or_generic=0; replay controls match expectations",
        "safety_boundary: read-only runtime; no provider call; output only in card evidence allowlist",
        "```",
        "",
        "## 分類摘要",
        "",
        f"- outcome_code: `{json.dumps(dict(sorted(outcome_counts.items())), ensure_ascii=False)}`",
        f"- target reviewer codes: `{json.dumps(dict(sorted(target_code_counts.items())), ensure_ascii=False)}`",
        f"- saved plan replays: `{len(replay['replays'])}`",
        f"- proven false-negative: `{len(false_negatives)}`",
        f"- negative controls preserved: `{all(item['matched_expectation'] for item in replay['controls'])}`",
        "",
        "## Observation checkpoint",
        "",
        "保存 response 顯示一個可重現的 locale-plan false-negative：來源中的 `Rider–Waite–Smith`",
        "在 plan response 以 ASCII hyphen 寫成 `Rider-Waite-Smith`，後接自然日文時仍被語言 gate 拒絕。",
        "其餘 plan rejection 為 safety flag 不一致、來源語言殘留或 rebuild topology 重用；不得放寬。",
        "Reviewer 主因另由固定 fixture 建立 RED 後才能修改 writer prompt。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--publisher-ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    queue_root = args.queue_root.resolve()
    ledger_path = args.publisher_ledger.resolve()
    output_dir = args.output_dir.resolve()
    if not (queue_root / "runs").is_dir() or not ledger_path.is_file():
        raise SystemExit("required read-only runtime snapshot is missing")
    if REPO_ROOT not in output_dir.parents:
        raise SystemExit("output directory must remain inside the repository")
    output_dir.mkdir(parents=True, exist_ok=True)

    ledger_bytes = ledger_path.read_bytes()
    ledger = json.loads(ledger_bytes)
    source_classes = _source_class_lookup(ledger)
    published = {
        str(item.get("run_id")): item
        for item in ledger.get("translation_published_runs", [])
        if isinstance(item, dict)
    }
    deferred: dict[str, list[str]] = {}
    for item in ledger.get("translation_deferred_runs", []):
        if isinstance(item, dict):
            deferred.setdefault(str(item.get("run_id")), []).append(str(item.get("reason")))

    states = []
    state_bytes: dict[Path, bytes] = {}
    for state_path in sorted((queue_root / "runs").glob("*.json")):
        raw = state_path.read_bytes()
        state = json.loads(raw)
        run_id = str(state.get("run_id") or "")
        if run_id.startswith("auto-i18n-") and state.get("status") in TERMINAL_STATUSES:
            states.append((str(state.get("updated_at") or ""), run_id, state, state_path))
            state_bytes[state_path] = raw

    selected = []
    for locale, count in SAMPLE_SIZES.items():
        locale_rows = sorted(
            (row for row in states if row[1].split("-")[2] == locale),
            reverse=True,
        )[:count]
        if len(locale_rows) != count:
            raise ValueError(f"terminal sample is incomplete for {locale}: {len(locale_rows)}")
        selected.extend(locale_rows)
    snapshot_at = max(row[0] for row in selected)

    taxonomy_rows = []
    replay_rows = []
    control_sources: list[tuple[dict[str, Any], Path]] = []
    for locale in SAMPLE_SIZES:
        locale_rows = sorted(
            (row for row in selected if row[1].split("-")[2] == locale),
            reverse=True,
        )
        for ordinal, (updated_at, run_id, state, state_path) in enumerate(locale_rows, 1):
            run_dir = Path(str(state["run_dir"])).resolve()
            try:
                run_relative = run_dir.relative_to(queue_root)
            except ValueError as error:
                raise ValueError(f"run escaped queue root: {run_id}") from error
            brief = _read_json(run_dir / "brief.json")
            source_class = source_classes.get(_base_run_id(run_id))
            if source_class is None:
                raise ValueError(f"source class is unknown: {run_id}")

            review_path = run_dir / "review.json"
            review = _read_json(review_path) if review_path.is_file() else {}
            reviewer_codes = _codes(review)
            deterministic_path = _latest_attempt_file(run_dir, "deterministic-findings.json")
            deterministic_codes = []
            if deterministic_path is not None:
                deterministic_payload = json.loads(deterministic_path.read_text(encoding="utf-8"))
                deterministic_codes = sorted(
                    {
                        str(item.get("code"))
                        for item in deterministic_payload
                        if isinstance(item, dict) and str(item.get("code") or "").strip()
                    }
                )

            replay = None
            if state["status"] == "failed":
                error_type = str(state.get("error_type") or "")
                if error_type == "LocalePlanValidationError":
                    replay = _failed_plan_replay(run_dir, brief)
                    replay_rows.append(replay)
                    primary_stage = "plan"
                    outcome_code = "plan_contract_rejected"
                    exact_context = replay["error_message"]
                    if replay["false_negative"]:
                        repair_route = "locale-plan-contract"
                    else:
                        repair_route = "not-applicable-quality-rejection"
                else:
                    plan_response = _latest_attempt_file(run_dir, "external-plan.json")
                    candidate_response = _latest_attempt_file(run_dir, "external-candidate.json")
                    review_response = _latest_attempt_file(run_dir, "external-review.json")
                    if plan_response is None:
                        primary_stage = "plan"
                    elif candidate_response is None:
                        primary_stage = "candidate"
                    elif review_response is None:
                        primary_stage = "reviewer"
                    else:
                        primary_stage = "publisher"
                    outcome_code = f"{primary_stage}_transport_{error_type or 'untyped'}"
                    exact_context = str(state.get("error_code") or state.get("failure_category") or error_type)
                    repair_route = "not-applicable-transport"
            elif reviewer_codes:
                primary_stage = "reviewer"
                outcome_code = "reviewer_rejected"
                exact_context = ",".join(reviewer_codes)
                repair_route = (
                    "native-search-prompt"
                    if TARGET_REVIEWER_CODES.intersection(reviewer_codes)
                    else "not-applicable-reviewer-quality"
                )
            else:
                primary_stage = "publisher"
                if run_id in published:
                    outcome_code = "publisher_published"
                    exact_context = str(published[run_id].get("version") or "published")
                    repair_route = "none-already-published"
                elif run_id in deferred:
                    outcome_code = "publisher_deferred"
                    exact_context = deferred[run_id][-1]
                    repair_route = "publisher-followup"
                elif (run_dir / "approval.json").is_file():
                    outcome_code = "publisher_approval_without_ledger"
                    exact_context = "approval.json exists but Publisher ledger has no release row"
                    repair_route = "publisher-reconciliation"
                else:
                    outcome_code = "publisher_ready"
                    exact_context = "clean review; no approval or release ledger row"
                    repair_route = "publisher-followup"

            taxonomy_rows.append(
                {
                    "sample_ordinal": ordinal,
                    "run_id": run_id,
                    "locale": locale,
                    "source_class": source_class,
                    "terminal_status": str(state["status"]),
                    "updated_at": updated_at,
                    "primary_stage": primary_stage,
                    "outcome_code": outcome_code,
                    "error_type": str(state.get("error_type") or "") or None,
                    "exact_context": exact_context,
                    "reviewer_codes": reviewer_codes,
                    "deterministic_codes": deterministic_codes,
                    "repair_route": repair_route,
                    "reparable_by_card": repair_route in {
                        "locale-plan-contract",
                        "native-search-prompt",
                    },
                    "state_evidence": {
                        "path": str(state_path.relative_to(queue_root)),
                        "sha256": _sha256_bytes(state_bytes[state_path]),
                    },
                    "run_evidence": {
                        "path": str(run_relative),
                        "brief_sha256": _sha256_bytes((run_dir / "brief.json").read_bytes()),
                        "review_sha256": (
                            _sha256_bytes(review_path.read_bytes()) if review_path.is_file() else None
                        ),
                    },
                    "saved_plan_response_sha256": (
                        replay["response_sha256"] if replay is not None else None
                    ),
                }
            )
            control_sources.append((state, run_dir))

    if any(state_path.read_bytes() != raw for state_path, raw in state_bytes.items()):
        raise ValueError("selected terminal state changed during collection")

    controls = _control_replays(control_sources)
    unknown_or_generic = sum(
        1
        for item in taxonomy_rows
        if item["primary_stage"] not in {"plan", "candidate", "reviewer", "publisher"}
        or "unknown" in item["outcome_code"]
        or "generic" in item["outcome_code"]
    )
    if len(taxonomy_rows) != 50 or unknown_or_generic or not all(
        item["matched_expectation"] for item in controls
    ):
        raise ValueError("OBS-001 recompute gate failed")

    taxonomy = {
        "schema_version": 1,
        "card_id": "CARD-PANTHEON-JA-KO-TRANSLATION-QUALITY-PASS-RATE-REPAIR-20260803",
        "slice": "SLICE-JKQ-OBS-001",
        "snapshot_at": snapshot_at,
        "source_receipts": {
            "queue_root": "<production-root>/.work/gemini-runner (local-only read)",
            "publisher_ledger": "<publisher-root>/.work/content-publisher/ledger.json (local-only read)",
            "publisher_ledger_sha256": _sha256_bytes(ledger_bytes),
        },
        "selection": {
            "statuses": sorted(TERMINAL_STATUSES),
            "ordering": "updated_at descending per locale",
            "sample_sizes": SAMPLE_SIZES,
        },
        "summary": {
            "total": len(taxonomy_rows),
            "by_primary_stage": dict(
                sorted(Counter(item["primary_stage"] for item in taxonomy_rows).items())
            ),
            "by_outcome_code": dict(
                sorted(Counter(item["outcome_code"] for item in taxonomy_rows).items())
            ),
            "unknown_or_generic": unknown_or_generic,
        },
        "runs": taxonomy_rows,
    }
    replay = {
        "schema_version": 1,
        "slice": "SLICE-JKQ-OBS-001",
        "snapshot_at": snapshot_at,
        "summary": {
            "saved_response_replays": len(replay_rows),
            "false_negatives": sum(item["false_negative"] for item in replay_rows),
            "controls": len(controls),
            "control_mismatches": sum(not item["matched_expectation"] for item in controls),
        },
        "replays": replay_rows,
        "controls": controls,
    }
    _write_json(output_dir / "failure-taxonomy.json", taxonomy)
    _write_json(output_dir / "saved-response-replay.json", replay)
    (output_dir / "baseline.md").write_text(
        _baseline_markdown(snapshot_at, taxonomy, replay),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "snapshot_at": snapshot_at,
                "taxonomy_rows": len(taxonomy_rows),
                "unknown_or_generic": unknown_or_generic,
                "saved_response_replays": len(replay_rows),
                "false_negatives": replay["summary"]["false_negatives"],
                "control_mismatches": replay["summary"]["control_mismatches"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

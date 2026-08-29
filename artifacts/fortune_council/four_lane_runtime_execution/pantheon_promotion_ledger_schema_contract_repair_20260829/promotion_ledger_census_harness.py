#!/usr/bin/env python3
"""Read-only promotion ledger compatibility census.

This harness stores only identity/schema/hash evidence. It does not copy
production registry, queue, brief, candidate, review, or ledger payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import pantheon_content_runtime_promotion as promotion  # noqa: E402


TARGET_RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
TARGET_ARTICLE_ID = "V2-TAROT-DEATH-MONEY"
TARGET_VERSION = "0.3.374"
MANIFEST_SNAPSHOT = (
    REPO_ROOT
    / "artifacts/fortune_council/four_lane_runtime_execution/"
    "g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/"
    "raw-current/runtime/runtime-manifest.json"
)


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_fingerprint(path: Path, label: str) -> dict[str, Any]:
    stat = path.stat()
    return {
        "label": label,
        "exists": path.exists(),
        "is_file": path.is_file(),
        "mode": oct(stat.st_mode & 0o777),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "sha256": sha256_bytes(path.read_bytes()),
    }


def registry_fingerprint(runs_root: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(runs_root.glob("*.json")):
        stat = path.stat()
        entries.append(
            {
                "name": path.name,
                "mode": oct(stat.st_mode & 0o777),
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "sha256": sha256_bytes(path.read_bytes()),
            }
        )
    return {
        "label": "live_queue_runs_registry",
        "file_count": len(entries),
        "tree_digest": sha256_bytes(canonical_json_bytes(entries)),
        "entries": entries,
    }


def descriptor_by_key() -> dict[str, promotion.LedgerCollectionDescriptor]:
    return {descriptor.key: descriptor for descriptor in promotion.LEDGER_COLLECTION_DESCRIPTORS}


def valid_list_identity(value: Any) -> tuple[bool, tuple[str, ...] | None]:
    if (
        not isinstance(value, list)
        or any(type(item) is not str or not item or item.strip() != item for item in value)
        or value != sorted(set(value))
    ):
        return False, None
    return True, tuple(value)


def brief_identity(brief: dict[str, Any]) -> dict[str, Any]:
    mode = brief.get("mode")
    lane = brief.get("lane")
    articles = brief.get("articles")
    if mode == "create":
        lane = "new"
    elif mode == "rewrite_existing_body":
        lane = "rewrite"
    if type(mode) is not str or type(lane) is not str or not isinstance(articles, list):
        return {"valid": False, "mode": mode, "lane": lane, "article_ids": []}
    ids = []
    for article in articles:
        if not isinstance(article, dict):
            return {"valid": False, "mode": mode, "lane": lane, "article_ids": []}
        if mode == "create":
            target = article.get("target")
            value = target.get("id") if isinstance(target, dict) else article.get("id")
        elif mode == "rewrite_existing_body":
            value = article.get("article_id")
        elif mode == "translate_existing":
            value = article.get("source_article_id")
        else:
            return {"valid": False, "mode": mode, "lane": lane, "article_ids": []}
        if type(value) is not str or not value or value.strip() != value:
            return {"valid": False, "mode": mode, "lane": lane, "article_ids": []}
        ids.append(value)
    return {
        "valid": len(ids) == len(set(ids)),
        "mode": mode,
        "lane": lane,
        "article_ids": sorted(ids),
    }


def registry_identity(state: dict[str, Any]) -> dict[str, Any]:
    envelope = state.get("identity_envelope")
    if isinstance(envelope, dict):
        valid, article_ids = valid_list_identity(envelope.get("article_ids"))
        return {
            "source": "identity_envelope",
            "valid": valid,
            "mode": envelope.get("mode"),
            "lane": envelope.get("lane"),
            "article_ids": list(article_ids or ()),
        }
    run_dir = state.get("run_dir")
    if type(run_dir) is not str:
        return {"source": "missing", "valid": False, "mode": None, "lane": None, "article_ids": []}
    brief_path = Path(run_dir) / "brief.json"
    if not brief_path.is_file() or brief_path.is_symlink():
        return {"source": "brief_missing", "valid": False, "mode": None, "lane": None, "article_ids": []}
    identity = brief_identity(read_json(brief_path))
    return {"source": "brief", **identity}


def collect_ledger_matches(ledger: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    descriptors = descriptor_by_key()
    matches = []
    for key, descriptor in descriptors.items():
        entries = ledger.get(key, [])
        if not isinstance(entries, list):
            raise RuntimeError(f"ledger collection is not a list: {key}")
        for entry in entries:
            if isinstance(entry, dict) and entry.get("run_id") == run_id:
                after_ok = True
                after_ids: tuple[str, ...] | None
                try:
                    after_ids = promotion._canonical_ledger_article_ids(entry, descriptor)
                except promotion.PromotionError:
                    after_ok = False
                    after_ids = None
                before_ok, before_ids = valid_list_identity(entry.get("article_ids"))
                matches.append(
                    {
                        "collection": key,
                        "identity_field": descriptor.identity_field,
                        "cardinality": descriptor.cardinality,
                        "lifecycle": descriptor.lifecycle,
                        "version": entry.get("version"),
                        "has_article_id": "article_id" in entry,
                        "has_article_ids": "article_ids" in entry,
                        "before_ok": before_ok,
                        "before_article_ids": list(before_ids or ()),
                        "after_ok": after_ok,
                        "after_article_ids": list(after_ids or ()),
                    }
                )
    return matches


def classify_row(row: dict[str, Any]) -> str:
    matches = row["ledger_matches"]
    if len(matches) > 1:
        return "malformed_fail_closed"
    if not row["registry_identity"]["valid"]:
        return "malformed_fail_closed"
    if not matches:
        return "unchanged_pass"
    match = matches[0]
    registry_ids = row["registry_identity"]["article_ids"]
    after_matches = match["after_ok"] and match["after_article_ids"] == registry_ids
    before_matches = match["before_ok"] and match["before_article_ids"] == registry_ids
    if before_matches and after_matches:
        return "unchanged_pass"
    if not before_matches and after_matches:
        return "measured_mismatch_red_to_green"
    return "malformed_fail_closed"


def malformed_matrix() -> list[dict[str, Any]]:
    descriptor = descriptor_by_key()["translation_published_runs"]
    cases = [
        ("translation_singular_ok", {"run_id": "r", "article_id": "A"}, True),
        ("translation_list_rejected", {"run_id": "r", "article_ids": ["A"]}, False),
        ("translation_both_rejected", {"run_id": "r", "article_id": "A", "article_ids": ["A"]}, False),
        ("translation_missing_rejected", {"run_id": "r"}, False),
        ("translation_wrong_type_rejected", {"run_id": "r", "article_id": ["A"]}, False),
        ("translation_blank_rejected", {"run_id": "r", "article_id": " A"}, False),
    ]
    list_descriptor = descriptor_by_key()["published_runs"]
    cases.extend(
        [
            ("list_identity_ok", {"run_id": "r", "article_ids": ["A", "B"]}, True, list_descriptor),
            ("list_duplicate_rejected", {"run_id": "r", "article_ids": ["A", "A"]}, False, list_descriptor),
            ("list_both_rejected", {"run_id": "r", "article_id": "A", "article_ids": ["A"]}, False, list_descriptor),
        ]
    )
    rows = []
    for case in cases:
        name, entry, expected_ok, *override = case
        selected = override[0] if override else descriptor
        try:
            ids = promotion._canonical_ledger_article_ids(entry, selected)
            ok = True
        except promotion.PromotionError:
            ids = ()
            ok = False
        rows.append(
            {
                "case": name,
                "expected_ok": expected_ok,
                "actual_ok": ok,
                "canonical_article_ids": list(ids),
                "classification": "pass" if ok == expected_ok else "unexpected",
            }
        )
    return rows


def run_census() -> dict[str, Any]:
    manifest = read_json(MANIFEST_SNAPSHOT)
    queue_root = Path(manifest["queue_root"])
    ledger_path = Path(manifest["publisher_state_root"]) / "ledger.json"
    runs_root = queue_root / "runs"
    before = {
        "manifest_snapshot": file_fingerprint(MANIFEST_SNAPSHOT, "current_runtime_manifest_snapshot"),
        "publisher_ledger": file_fingerprint(ledger_path, "live_publisher_ledger"),
        "registry": registry_fingerprint(runs_root),
    }
    ledger = read_json(ledger_path)
    rows = []
    for state_path in sorted(runs_root.glob("*.json")):
        state = read_json(state_path)
        run_id = state.get("run_id")
        if type(run_id) is not str:
            raise RuntimeError(f"registry state missing run_id: {state_path.name}")
        row = {
            "registry_file": state_path.name,
            "registry_file_sha256": sha256_bytes(state_path.read_bytes()),
            "run_id": run_id,
            "status": state.get("status"),
            "run_dir_kind": "absolute" if Path(str(state.get("run_dir", ""))).is_absolute() else "invalid",
            "registry_identity": registry_identity(state),
            "ledger_matches": collect_ledger_matches(ledger, run_id),
        }
        row["classification"] = classify_row(row)
        rows.append(row)
    after = {
        "manifest_snapshot": file_fingerprint(MANIFEST_SNAPSHOT, "current_runtime_manifest_snapshot"),
        "publisher_ledger": file_fingerprint(ledger_path, "live_publisher_ledger"),
        "registry": registry_fingerprint(runs_root),
    }
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    transitions = [row for row in rows if row["classification"] == "measured_mismatch_red_to_green"]
    malformed = malformed_matrix()
    ok = (
        len(rows) == 136
        and len(transitions) == 1
        and transitions[0]["run_id"] == TARGET_RUN_ID
        and transitions[0]["ledger_matches"][0]["version"] == TARGET_VERSION
        and transitions[0]["ledger_matches"][0]["after_article_ids"] == [TARGET_ARTICLE_ID]
        and all(row["classification"] == "pass" for row in malformed)
        and before == after
    )
    return {
        "schema_version": 1,
        "status": "PASS" if ok else "FAIL",
        "input_sources": {
            "runtime_manifest_snapshot": {
                "source_id": "artifact:raw-current/runtime/runtime-manifest.json",
                "sha256": before["manifest_snapshot"]["sha256"],
            },
            "queue_runs_registry": {
                "source_id": "runtime_manifest.queue_root/runs",
                "file_count": before["registry"]["file_count"],
                "tree_digest": before["registry"]["tree_digest"],
            },
            "publisher_ledger": {
                "source_id": "runtime_manifest.publisher_state_root/ledger.json",
                "sha256": before["publisher_ledger"]["sha256"],
            },
        },
        "candidate_descriptor_digest": sha256_bytes(
            canonical_json_bytes(
                [descriptor.__dict__ for descriptor in promotion.LEDGER_COLLECTION_DESCRIPTORS]
            )
        ),
        "counts": counts,
        "transition_run_ids": [row["run_id"] for row in transitions],
        "pre_read_fingerprints": before,
        "post_read_fingerprints": after,
        "production_immutability": {
            "pre_post_fingerprints_identical": before == after,
            "transaction_calls": 0,
            "provider_calls": 0,
            "publisher_calls": 0,
            "live_mutation_calls": 0,
        },
        "matrix": rows,
        "malformed_matrix": malformed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_census()
    args.output.write_bytes(canonical_json_bytes(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

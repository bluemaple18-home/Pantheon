#!/usr/bin/env python3
"""Canonical topic 到 NEW exact-run brief 的本機批次 bridge。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import scripts.agy_seo_copy_pipeline as pipeline
import scripts.pantheon_topic_identity as identity
import scripts.pantheon_topic_reservation as reservation


TOPIC_MATRIX = Path("artifacts/fortune_council/content_seo_matrix/article_matrix.md")
TOPIC_BRIEFS = Path(
    "artifacts/fortune_council/content_seo_matrix/article_briefs_first_30.md"
)
METRIC_BUCKETS = (
    "attempted",
    "publish_success",
    "writer_or_reviewer_rejection",
    "duplicate_rejection",
    "policy_rejection",
    "runtime_failure",
)
CHECKPOINT_COUNTS = {4, 10}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
TOPIC_ID_PATTERN = re.compile(r"topic-[0-9a-f]{20}")


class BatchPlanError(ValueError):
    """批次計畫無法安全建立。"""


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def batch_plan_bytes(plan: dict[str, Any]) -> bytes:
    """回傳可固定 SHA 的 canonical plan bytes。"""
    return _canonical_bytes(plan)


def load_canonical_topics(repo_root: Path) -> list[dict[str, Any]]:
    """由 P0-FAST-02 的兩個 canonical artifacts 載入固定順序題庫。"""
    topics = [
        *identity.load_article_matrix_topics(repo_root / TOPIC_MATRIX),
        *identity.load_article_brief_topics(repo_root / TOPIC_BRIEFS),
    ]
    topic_ids = [str(topic.get("topic_id") or "") for topic in topics]
    if not topics or "" in topic_ids or len(topic_ids) != len(set(topic_ids)):
        raise BatchPlanError("canonical topic inventory is empty or duplicated")
    return topics


def _category(topic: dict[str, Any]) -> tuple[str, str, str]:
    entity = str(topic.get("entity") or "").strip().lower()
    context = str(topic.get("relationship_context") or "").strip().lower()
    if entity == "tarot" or context == "tarot":
        return "tarot", "tarot", "tarot"
    if entity == "personality" or context == "personality":
        return "mbti", "personality", "personality"
    if entity == "astrology" or context == "astrology":
        return "astro", "astro", "astrology"
    return "ziwei", "fortune", "fortune"


def _serial_maxima(existing_articles: Iterable[dict[str, Any]]) -> dict[str, int]:
    maxima: dict[str, int] = {}
    for record in existing_articles:
        path = str(record.get("path") or record.get("route") or "")
        match = re.search(r"/articles/([^/]+)/\1-(\d{4,})$", path)
        if match:
            category, serial = match.groups()
            maxima[category] = max(maxima.get(category, 0), int(serial))
    return maxima


def _target(
    topic: dict[str, Any],
    maxima: dict[str, int],
    publication_date: str,
) -> dict[str, str]:
    section, product, category = _category(topic)
    maxima[category] = maxima.get(category, 0) + 1
    serial = f"{category}-{maxima[category]:04d}"
    topic_suffix = str(topic["topic_id"]).removeprefix("topic-")[:12].upper()
    article_id = f"P0-{category.upper()}-{topic_suffix}"
    route = f"/articles/{category}/{serial}"
    return {
        "id": article_id,
        "article_id": article_id,
        "section": section,
        "product": product,
        "category": category,
        "slug": article_id.lower(),
        "serial": serial,
        "urlSlug": serial,
        "route": route,
        "canonical": f"{identity.SITE_ORIGIN}{route}",
        "published": publication_date,
        "updated": publication_date,
        "primaryKeyword": str(topic.get("semantic_intent") or "").strip(),
    }


def _semantic_key(topic: dict[str, Any]) -> str:
    intent = " ".join(str(topic.get("semantic_intent") or "").lower().split())
    return f"intent-{hashlib.sha256(intent.encode('utf-8')).hexdigest()[:20]}"


def _select_topics(
    topics: list[dict[str, Any]],
    corpus: list[dict[str, Any]],
    count: int,
    topic_ids: list[str] | None,
) -> list[dict[str, Any]]:
    by_id = {str(topic.get("topic_id") or ""): topic for topic in topics}
    if "" in by_id or len(by_id) != len(topics):
        raise BatchPlanError("topic inventory contains missing or duplicate topic_id")
    if topic_ids is not None:
        if len(topic_ids) != count or len(set(topic_ids)) != count:
            raise BatchPlanError("topic_ids must be unique and match slot count")
        try:
            candidates = [by_id[topic_id] for topic_id in topic_ids]
        except KeyError as error:
            raise BatchPlanError(f"unknown topic_id: {error.args[0]}") from error
    else:
        candidates = topics

    selected: list[dict[str, Any]] = []
    for topic in candidates:
        admission = identity.classify_topic(topic, corpus, selected)
        if admission["status"] == "AVAILABLE":
            selected.append(deepcopy(topic))
            if len(selected) == count:
                return selected
        elif topic_ids is not None:
            raise BatchPlanError(
                f"topic {topic['topic_id']} is {admission['status']}: "
                f"{admission['level']}"
            )
    raise BatchPlanError(f"only {len(selected)} AVAILABLE topics for {count} slots")


def build_batch_plan(
    repo_root: Path,
    *,
    topics: list[dict[str, Any]],
    slot_ids: list[str],
    publication_date: str,
    existing_articles: list[dict[str, Any]] | None = None,
    topic_ids: list[str] | None = None,
) -> dict[str, Any]:
    """建立 deterministic、無副作用的批次計畫。"""
    if not slot_ids or len(set(slot_ids)) != len(slot_ids):
        raise BatchPlanError("slot_ids must be non-empty and unique")
    if any(RUN_ID_PATTERN.fullmatch(slot_id) is None for slot_id in slot_ids):
        raise BatchPlanError("slot_id format is invalid")
    try:
        date.fromisoformat(publication_date)
    except ValueError as error:
        raise BatchPlanError("publication_date must be ISO-8601") from error

    corpus = (
        deepcopy(existing_articles)
        if existing_articles is not None
        else identity.load_existing_corpus(repo_root)
    )
    selected = _select_topics(topics, corpus, len(slot_ids), topic_ids)
    snapshot_digest = _digest(
        {
            "inventory": topics,
            "existing_articles": corpus,
            "slot_ids": slot_ids,
            "topic_ids": [topic["topic_id"] for topic in selected],
            "publication_date": publication_date,
        }
    )
    maxima = _serial_maxima(corpus)
    planned_targets: list[dict[str, Any]] = []
    slots: list[dict[str, Any]] = []
    for index, (slot_id, topic) in enumerate(zip(slot_ids, selected, strict=True), 1):
        target = _target(topic, maxima, publication_date)
        target_topic = {
            **deepcopy(topic),
            "article_id": target["article_id"],
            "route": target["route"],
            "canonical": target["canonical"],
            "slug": target["urlSlug"],
        }
        admission = identity.classify_topic(target_topic, corpus, planned_targets)
        if admission["status"] != "AVAILABLE":
            raise BatchPlanError(
                f"target for {topic['topic_id']} is {admission['status']}: "
                f"{admission['level']}"
            )
        planned_targets.append(target_topic)
        slots.append(
            {
                "slot_id": slot_id,
                "lane_id": f"new:{slot_id}",
                "runtime_lane": "new",
                "topic_id": topic["topic_id"],
                "run_id": (
                    f"content-{snapshot_digest[:10]}-{index:02d}-"
                    f"{str(topic['topic_id'])[-8:]}"
                ),
                "semantic_exclusion_key": _semantic_key(topic),
                "topic": topic,
                "target": target,
            }
        )
    digest_payload = {
        "schema_version": 1,
        "snapshot_digest": snapshot_digest,
        "slots": slots,
    }
    batch_digest = _digest(digest_payload)
    for slot in slots:
        slot["lineage"] = {
            "snapshot_digest": snapshot_digest,
            "batch_digest": batch_digest,
            "topic_id": slot["topic_id"],
            "run_id": slot["run_id"],
            "slot_id": slot["slot_id"],
            "target_article_id": slot["target"]["article_id"],
            "target_route": slot["target"]["route"],
        }
    return {
        **digest_payload,
        "batch_digest": batch_digest,
        "metrics": {bucket: 0 for bucket in METRIC_BUCKETS},
    }


def build_checkpoint_plan(
    repo_root: Path,
    *,
    publication_date: str,
    topic_ids: list[str] | None = None,
) -> dict[str, Any]:
    """建立唯一一份 10-slot plan；Checkpoint A 固定取前四槽。"""
    return build_batch_plan(
        repo_root,
        topics=load_canonical_topics(repo_root),
        existing_articles=None,
        slot_ids=[f"slot-{index:02d}" for index in range(1, 11)],
        topic_ids=topic_ids,
        publication_date=publication_date,
    )


def checkpoint_slots(plan: dict[str, Any], count: int) -> list[dict[str, Any]]:
    if count not in CHECKPOINT_COUNTS or len(plan.get("slots") or []) < count:
        raise BatchPlanError("checkpoint count must be 4 or 10")
    return plan["slots"][:count]


def _brief(plan: dict[str, Any], slot: dict[str, Any]) -> dict[str, Any]:
    topic, target = slot["topic"], slot["target"]
    writer_target = {
        field: target[field]
        for field in (
            "id",
            "section",
            "product",
            "slug",
            "serial",
            "urlSlug",
            "published",
            "updated",
            "primaryKeyword",
        )
    }
    return {
        "schema_version": pipeline.SCHEMA_VERSION,
        "run_id": slot["run_id"],
        "mode": "create",
        "source": {
            "type": "canonical_topic_batch",
            **slot["lineage"],
            "lane_id": slot["lane_id"],
            "source_matrix_ref": topic.get("source_matrix_ref"),
        },
        "articles": [
            {
                "matrix": {
                    "id": writer_target["id"],
                    "primaryKeyword": writer_target["primaryKeyword"],
                    "title": topic["title"],
                    "intent": topic["semantic_intent"],
                    "topic_id": slot["topic_id"],
                    "source_matrix_ref": topic.get("source_matrix_ref"),
                },
                "target": writer_target,
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }


def _validate_plan(plan: dict[str, Any], count: int) -> list[dict[str, Any]]:
    slots = checkpoint_slots(plan, count)
    for slot in slots:
        if RUN_ID_PATTERN.fullmatch(str(slot.get("run_id") or "")) is None:
            raise BatchPlanError("plan contains invalid run_id")
        if TOPIC_ID_PATTERN.fullmatch(str(slot.get("topic_id") or "")) is None:
            raise BatchPlanError("plan contains invalid topic_id")
        expected_lineage = {
            "snapshot_digest": plan.get("snapshot_digest"),
            "batch_digest": plan.get("batch_digest"),
            "topic_id": slot.get("topic_id"),
            "run_id": slot.get("run_id"),
            "slot_id": slot.get("slot_id"),
            "target_article_id": slot.get("target", {}).get("article_id"),
            "target_route": slot.get("target", {}).get("route"),
        }
        if slot.get("lineage") != expected_lineage:
            raise BatchPlanError("plan lineage mismatch")
    digest_slots = []
    for slot in plan["slots"]:
        value = deepcopy(slot)
        value.pop("lineage", None)
        digest_slots.append(value)
    expected_digest = _digest(
        {
            "schema_version": plan.get("schema_version"),
            "snapshot_digest": plan.get("snapshot_digest"),
            "slots": digest_slots,
        }
    )
    if plan.get("batch_digest") != expected_digest:
        raise BatchPlanError("batch plan digest mismatch")
    return slots


def _claim(
    state_root: Path,
    plan: dict[str, Any],
    slot: dict[str, Any],
    ttl_seconds: float,
    claim_topic: Callable[..., dict[str, object]],
) -> tuple[dict[str, object], str]:
    token = f"batch-{plan['batch_digest'][:20]}-{slot['slot_id']}"
    arguments = {
        "topic_id": slot["topic_id"],
        "reservation_token": token,
        "lane_id": slot["lane_id"],
        "run_id": slot["run_id"],
        "semantic_exclusion_key": slot["semantic_exclusion_key"],
        "ttl_seconds": ttl_seconds,
    }
    try:
        result = claim_topic(state_root, **arguments)
    except OSError:
        result = claim_topic(state_root, **arguments)
    return result, token


def _output_matches(run_dir: Path, brief: dict[str, Any]) -> bool:
    try:
        return (
            run_dir.is_dir()
            and {path.name for path in run_dir.iterdir()} == {"brief.json"}
            and (run_dir / "brief.json").read_bytes() == _canonical_bytes(brief)
        )
    except OSError:
        return False


def _prepare_slot(
    plan: dict[str, Any],
    slot: dict[str, Any],
    state_root: Path,
    output_root: Path,
    ttl_seconds: float,
    claim_topic: Callable[..., dict[str, object]],
    write_json: Callable[[Path, object], None],
) -> dict[str, Any]:
    base = {key: slot[key] for key in ("slot_id", "topic_id", "lane_id", "run_id")}
    try:
        claim, token = _claim(state_root, plan, slot, ttl_seconds, claim_topic)
    except Exception as error:
        return {**base, "status": "RESERVATION_UNCERTAIN", "error": type(error).__name__}
    if not claim.get("ok") or not isinstance(claim.get("reservation"), dict):
        return {
            **base,
            "status": "RESERVATION_REJECTED",
            "error": str(claim.get("result") or "missing_owner_record"),
        }
    generation = int(claim["reservation"]["owner_generation"])
    brief = _brief(plan, slot)
    pipeline.validate_new_brief(brief)
    run_dir = output_root / slot["run_id"]
    if run_dir.exists():
        return {
            **base,
            "status": "PREPARED" if _output_matches(run_dir, brief) else "OUTPUT_CONFLICT",
            "reservation_token": token,
            "owner_generation": generation,
            "brief_path": f"{slot['run_id']}/brief.json",
        }

    staging: Path | None = None
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(prefix=f".{slot['run_id']}.staging-", dir=output_root)
        )
        write_json(staging / "brief.json", brief)
        staging.replace(run_dir)
        staging = None
        status, error = "PREPARED", None
    except Exception as prepare_error:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        if _output_matches(run_dir, brief):
            status, error = "PREPARED", None
        else:
            status, error = "PREPARE_FAILED", type(prepare_error).__name__
    result = {
        **base,
        "status": status,
        "reservation_token": token,
        "owner_generation": generation,
        "brief_path": f"{slot['run_id']}/brief.json",
    }
    if error:
        result["error"] = error
    return result


def prepare_checkpoint(
    plan: dict[str, Any],
    state_root: Path,
    output_root: Path,
    *,
    count: int,
    ttl_seconds: float = 3600,
    claim_topic: Callable[..., dict[str, object]] = reservation.claim_topic_reservation,
    write_json: Callable[[Path, object], None] = pipeline.write_json,
) -> dict[str, Any]:
    """逐槽準備 checkpoint；單槽失敗不回滾其他槽。"""
    slots = _validate_plan(plan, count)
    for slot in slots:
        pipeline.validate_new_brief(_brief(plan, slot))
    results = [
        _prepare_slot(
            plan,
            slot,
            Path(state_root),
            Path(output_root),
            ttl_seconds,
            claim_topic,
            write_json,
        )
        for slot in slots
    ]
    metrics = {bucket: 0 for bucket in METRIC_BUCKETS}
    metrics["attempted"] = count
    for result in results:
        if result["status"] == "PREPARED":
            continue
        bucket = (
            "duplicate_rejection"
            if result["status"] == "RESERVATION_REJECTED"
            and result.get("error") == "already_reserved"
            else "runtime_failure"
        )
        result["metric_bucket"] = bucket
        metrics[bucket] += 1
    failed = sum(
        metrics[bucket] for bucket in METRIC_BUCKETS if bucket != "attempted"
    )
    return {
        "schema_version": 1,
        "status": "READY" if failed == 0 else "PARTIAL",
        "snapshot_digest": plan["snapshot_digest"],
        "batch_digest": plan["batch_digest"],
        "checkpoint_count": count,
        "metrics": metrics,
        "slots": results,
    }


def _validate_frozen_plan(plan: object) -> dict[str, Any]:
    if not isinstance(plan, dict) or not isinstance(plan.get("slots"), list):
        raise BatchPlanError("batch plan artifact must be a JSON object")
    if len(plan["slots"]) != 10:
        raise BatchPlanError("batch plan artifact must contain exactly 10 slots")
    _validate_plan(plan, 10)
    return plan


def _persist_batch_plan(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(content)
    except FileExistsError as error:
        if path.read_bytes() != content:
            raise BatchPlanError("existing batch plan differs; refusing overwrite") from error


def _load_frozen_plan(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        plan = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BatchPlanError("batch plan artifact is not valid JSON") from error
    if not isinstance(plan, dict) or raw != batch_plan_bytes(plan):
        raise BatchPlanError("batch plan artifact is not canonical")
    return _validate_frozen_plan(plan)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    create = subparsers.add_parser("create-plan")
    create.add_argument("--repo-root", type=Path, required=True)
    create.add_argument("--plan-path", type=Path, required=True)
    create.add_argument("--publication-date", required=True)
    create.add_argument("--topic-id", action="append", default=[])

    prepare = subparsers.add_parser("prepare-checkpoint")
    prepare.add_argument("--plan-path", type=Path, required=True)
    prepare.add_argument("--state-root", type=Path, required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument("--count", type=int, choices=sorted(CHECKPOINT_COUNTS), required=True)
    prepare.add_argument("--receipt-path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.mode == "create-plan":
            plan = build_checkpoint_plan(
                args.repo_root,
                publication_date=args.publication_date,
                topic_ids=args.topic_id or None,
            )
            _validate_frozen_plan(plan)
            _persist_batch_plan(args.plan_path, batch_plan_bytes(plan))
            return 0

        plan = _load_frozen_plan(args.plan_path)
        receipt = prepare_checkpoint(
            plan,
            args.state_root,
            args.output_root,
            count=args.count,
        )
        if args.receipt_path is not None:
            pipeline.write_json(args.receipt_path, receipt)
        return 0 if receipt["status"] == "READY" else 2
    except (BatchPlanError, KeyError, OSError, TypeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


__all__ = [
    "BatchPlanError",
    "CHECKPOINT_COUNTS",
    "METRIC_BUCKETS",
    "batch_plan_bytes",
    "build_batch_plan",
    "build_checkpoint_plan",
    "checkpoint_slots",
    "load_canonical_topics",
    "main",
    "prepare_checkpoint",
]


if __name__ == "__main__":
    raise SystemExit(main())

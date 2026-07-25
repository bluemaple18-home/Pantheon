#!/usr/bin/env python3
"""協調 Pantheon 私密 run、sanitized outbox 與使用者擁有的 Gemini runner。"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from scripts import agy_content_publisher as publisher
from scripts import agy_seo_copy_pipeline as pipeline
from scripts.agy_gemini_outbox import (
    ExternalJobFailed,
    ExternalJobPending,
    atomic_write_json,
    run_pipeline_tick,
)
from scripts.agy_gemini_runner import process_once


MAX_BRIEF_BYTES = 12 * 1024
MAX_ACTIVE_RUNS_PER_CYCLE = 5
DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS = 2
DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE = 1
DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN = 5
DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE = 1
CONTENT_LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
Tick = Callable[[Path, Path], dict[str, Any]]
Process = Callable[[Path], dict[str, str]]


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _brief(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "brief.json"
    if not path.is_file():
        raise ValueError("run directory must contain brief.json")
    if path.stat().st_size > MAX_BRIEF_BYTES:
        raise ValueError("brief exceeds 12 KB")
    brief = json.loads(path.read_text(encoding="utf-8"))
    run_id = brief.get("run_id")
    articles = brief.get("articles")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("brief run_id must be non-empty")
    if not isinstance(articles, list) or len(articles) > 5:
        raise ValueError("brief articles must contain at most 5 items")
    return brief


def _state_path(run_id: str, queue_root: Path) -> Path:
    opaque_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    return queue_root / "runs" / f"{opaque_id}.json"


def register_run(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    """將一個本機私密 run 登記為 active；不建立外部 request。"""
    resolved = run_dir.resolve()
    brief = _brief(resolved)
    path = _state_path(str(brief["run_id"]), queue_root.resolve())
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("run_dir") != str(resolved) or state.get("run_id") != brief["run_id"]:
            raise ValueError("registered run identity collision")
        return state
    now = _now()
    state = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "run_dir": str(resolved),
        "status": "active",
        "registered_at": now,
        "updated_at": now,
    }
    atomic_write_json(path, state)
    return state


def read_run_state(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    brief = _brief(run_dir.resolve())
    path = _state_path(str(brief["run_id"]), queue_root.resolve())
    if not path.exists():
        raise ValueError("run is not registered")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(queue_root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = _now()
    atomic_write_json(_state_path(str(state["run_id"]), queue_root), state)


def _advance(
    queue_root: Path,
    state: dict[str, Any],
    tick: Tick,
    *,
    job_queue_root: Path | None = None,
) -> str:
    try:
        result = tick(Path(str(state["run_dir"])), job_queue_root or queue_root)
    except ExternalJobPending as pending:
        state["status"] = "active"
        state["last_job_id"] = pending.job_id
        _write_state(queue_root, state)
        return "pending"
    except ExternalJobFailed as failed:
        state["status"] = "failed"
        state["last_job_id"] = failed.job_id
        state["error_type"] = failed.error_type
        _write_state(queue_root, state)
        return "failed"
    except Exception as error:
        state["status"] = "failed"
        state["error_type"] = type(error).__name__
        _write_state(queue_root, state)
        return "failed"
    state["status"] = "complete"
    state["result"] = result
    state.pop("error_type", None)
    _write_state(queue_root, state)
    return "complete"


def _active_states(queue_root: Path) -> list[dict[str, Any]]:
    states = []
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("status") == "active":
            states.append(state)
    return sorted(
        states,
        key=lambda state: (
            str(state.get("updated_at") or ""),
            str(state.get("registered_at") or ""),
            str(state.get("run_id") or ""),
        ),
    )


def _lane_queue_root(queue_root: Path, lane: str) -> Path:
    if lane not in CONTENT_LANES:
        raise ValueError(f"unknown content lane: {lane}")
    return queue_root / "lanes" / lane


def _lane_for_state(state: dict[str, Any], legacy_article_ids: set[str]) -> str:
    brief = _read_run_brief_from_state(state)
    if not isinstance(brief, dict):
        raise ValueError("active run brief is unavailable")
    mode = brief.get("mode")
    if mode == "create":
        return "new"
    if mode == "rewrite_existing_body":
        return "rewrite"
    if mode != "translate_existing":
        raise ValueError(f"unsupported active run mode: {mode}")
    articles = brief.get("articles")
    if not isinstance(articles, list) or not articles or not isinstance(articles[0], dict):
        raise ValueError("translation run has no source article")
    source_article_id = str(articles[0].get("source_article_id") or "")
    return "i18n-rewrite" if source_article_id in legacy_article_ids else "i18n-new"


def _select_lane_states(
    states: list[dict[str, Any]],
    legacy_article_ids: set[str],
) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for state in states:
        lane = _lane_for_state(state, legacy_article_ids)
        selected.setdefault(lane, state)
        if len(selected) == len(CONTENT_LANES):
            break
    return [selected[lane] for lane in CONTENT_LANES if lane in selected]


def _lane_summary(
    queue_root: Path,
    states: list[dict[str, Any]],
    legacy_article_ids: set[str],
) -> dict[str, dict[str, int]]:
    counts = {lane: 0 for lane in CONTENT_LANES}
    for state in states:
        counts[_lane_for_state(state, legacy_article_ids)] += 1
    return {
        lane: {
            "active": counts[lane],
            "queued": len(list((_lane_queue_root(queue_root, lane) / "outbox").glob("*.json"))),
            "processing": len(list((_lane_queue_root(queue_root, lane) / "processing").glob("*.json"))),
        }
        for lane in CONTENT_LANES
    }


def _migrate_pending_jobs(
    queue_root: Path,
    states: list[dict[str, Any]],
    legacy_article_ids: set[str],
) -> dict[str, int]:
    """把舊 shared outbox 的 pending job 原子搬到對應 lane。"""
    lane_by_namespace = {
        hashlib.sha256(str(state["run_id"]).encode("utf-8")).hexdigest()[:24]: _lane_for_state(
            state,
            legacy_article_ids,
        )
        for state in states
    }
    moved = {lane: 0 for lane in CONTENT_LANES}
    outbox = queue_root / "outbox"
    for source in sorted(outbox.glob("*.json")) if outbox.exists() else []:
        try:
            request = json.loads(source.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        namespace = re.sub(r"-r[0-9]+$", "", str(request.get("namespace") or ""))
        lane = lane_by_namespace.get(namespace)
        if lane is None:
            continue
        target = _lane_queue_root(queue_root, lane) / "outbox" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError(f"lane job collision: {source.name}")
        try:
            os.replace(source, target)
        except FileNotFoundError:
            continue
        moved[lane] += 1
    return moved


def _read_run_brief_from_state(state: dict[str, Any]) -> dict[str, Any] | None:
    run_dir = Path(str(state.get("run_dir") or ""))
    path = run_dir / "brief.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _article_ids_from_brief(brief: dict[str, Any] | None) -> set[str]:
    if not isinstance(brief, dict) or brief.get("mode") != "rewrite_existing_body":
        return set()
    articles = brief.get("articles")
    if not isinstance(articles, list):
        return set()
    return {str(article.get("article_id") or "") for article in articles if isinstance(article, dict) and article.get("article_id")}


def _create_article_ids_from_brief(brief: dict[str, Any] | None) -> set[str]:
    if not isinstance(brief, dict) or brief.get("mode") != "create":
        return set()
    articles = brief.get("articles")
    if not isinstance(articles, list):
        return set()
    article_ids: set[str] = set()
    for article in articles:
        if not isinstance(article, dict):
            continue
        target = article.get("target")
        if isinstance(target, dict) and target.get("id"):
            article_ids.add(str(target["id"]))
            continue
        if article.get("id"):
            article_ids.add(str(article["id"]))
    return article_ids


def _registered_article_ids_by_mode(queue_root: Path, mode: str) -> set[str]:
    article_ids: set[str] = set()
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        brief = _read_run_brief_from_state(state)
        if mode == "create":
            article_ids.update(_create_article_ids_from_brief(brief))
        elif mode == "rewrite_existing_body":
            article_ids.update(_article_ids_from_brief(brief))
    return article_ids


def _active_count_by_mode(queue_root: Path, mode: str) -> int:
    count = 0
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if state.get("status") != "active":
            continue
        brief = _read_run_brief_from_state(state)
        if isinstance(brief, dict) and brief.get("mode") == mode:
            count += 1
    return count


def _registered_rewrite_article_ids(queue_root: Path) -> set[str]:
    return _registered_article_ids_by_mode(queue_root, "rewrite_existing_body")


def _slug_part(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return slug[:80] or "article"


def _head_sha(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _next_new_matrix_run_prefix(run_root: Path, queue_root: Path) -> str:
    today = datetime.now().astimezone().strftime("%Y%m%d")
    stem = f"auto-new-v1-{today}"
    used: set[str] = set()
    if run_root.exists():
        used.update(path.name for path in run_root.iterdir() if path.is_dir())
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        run_id = str(state.get("run_id") or "")
        if run_id:
            used.add(run_id)
    index = 1
    while True:
        prefix = f"{stem}-{index:03d}"
        if not any(item == prefix or item.startswith(f"{prefix}-") for item in used):
            return prefix
        index += 1


def seed_new_matrix_runs(
    repo_root: Path,
    queue_root: Path,
    run_root: Path,
    *,
    min_active_runs: int = DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS,
    max_new_runs: int = DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE,
    max_articles_per_run: int = DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN,
) -> dict[str, Any]:
    """自動從內容矩陣挑未登記的新文，建立 create run 並交給 coordinator。"""
    if min_active_runs <= 0 or max_new_runs <= 0:
        return {"status": "disabled", "created": 0, "created_run_ids": []}
    active_create = _active_count_by_mode(queue_root, "create")
    if active_create >= min_active_runs:
        return {"status": "active_floor_met", "created": 0, "created_run_ids": [], "active_create": active_create}

    created: list[str] = []
    excluded_ids = _registered_article_ids_by_mode(queue_root, "create")
    for _ in range(min(max_new_runs, min_active_runs - active_create)):
        run_prefix = _next_new_matrix_run_prefix(run_root, queue_root)
        paths = pipeline.prepare_matrix_runs(
            repo_root,
            run_prefix,
            output_root=run_root,
            limit=max_articles_per_run,
            exclude_ids=excluded_ids,
            max_articles_per_run=max_articles_per_run,
        )
        if not paths:
            break
        for brief_path in paths:
            state = register_run(brief_path.parent, queue_root)
            created.append(str(state["run_id"]))
            brief = _brief(brief_path.parent)
            excluded_ids.update(_create_article_ids_from_brief(brief))
        if len(created) >= max_new_runs:
            break

    return {
        "status": "seeded" if created else "idle",
        "created": len(created),
        "created_run_ids": created,
        "active_create_before": active_create,
    }


def _legacy_rewrite_article_brief(
    record: dict[str, Any],
    inventory_item: dict[str, Any],
) -> dict[str, Any]:
    article_id = str(record["id"])
    source_record = inventory_item.get("record") if isinstance(inventory_item.get("record"), dict) else record
    current_body = inventory_item.get("currentBody")
    immutable_fields = {
        "id": article_id,
        "product": str(source_record.get("product") or source_record.get("articleCategory") or publisher._record_category(record)),
        "slug": str(source_record.get("slug") or ""),
        "serial": publisher._record_serial(record),
        "title": str(source_record.get("title") or record.get("title") or ""),
        "description": str(source_record.get("description") or record.get("description") or ""),
        "answer": str(source_record.get("answer") or record.get("answer") or ""),
        "faq": source_record.get("faq") if isinstance(source_record.get("faq"), list) else [],
        "tags": source_record.get("tags") if isinstance(source_record.get("tags"), list) else [],
        "published": str(inventory_item.get("published") or source_record.get("published") or ""),
        "updated": str(inventory_item.get("updated") or source_record.get("updated") or ""),
        "urlSlug": str(source_record.get("urlSlug") or source_record.get("slug") or record.get("slug") or ""),
        "primaryKeyword": str(source_record.get("primaryKeyword") or record.get("primaryKeyword") or ""),
    }
    return {
        "slot": "article-01",
        "article_id": article_id,
        "identity": {
            "id": article_id,
            "product": immutable_fields["product"],
            "category": publisher._record_category(record),
            "serial": immutable_fields["serial"],
            "slug": immutable_fields["slug"],
            "primaryKeyword": immutable_fields["primaryKeyword"],
            "title": immutable_fields["title"],
        },
        "immutable_fields": immutable_fields,
        "current_body": current_body,
        "current_body_sha256": pipeline.body_sha256(current_body),
        "rewrite_brief": [
            "把正文改得更口語、貼近使用者情境；不要改標題、URL、FAQ、metadata 或文章定位。",
            "每節至少放入一個具體生活場景、可觀察動作或可直接套用的判斷句，避免模板句與空泛雞湯。",
            "保留原本搜尋意圖與主題邊界；不要承諾感情、工作、財富、健康或人生結果。",
        ],
        "source_file": "app/web/static/article-meta.js",
        "body_source": "buildArticleContent",
    }


def _compact_legacy_backlog(backlog: dict[str, Any]) -> dict[str, Any]:
    preview = backlog.get("unattempted_articles")
    return {
        "released": backlog.get("released", 0),
        "clean_approve": backlog.get("clean_approve", 0),
        "reject": backlog.get("reject", 0),
        "active_or_incomplete": backlog.get("active_or_incomplete", 0),
        "non_legacy": backlog.get("non_legacy", 0),
        "legacy_total": backlog.get("legacy_total", 0),
        "attempted": backlog.get("attempted", 0),
        "unattempted": backlog.get("unattempted", 0),
        "clean_approve_run_ids": backlog.get("clean_approve_run_ids", []),
        "reject_run_ids": backlog.get("reject_run_ids", []),
        "unattempted_preview": preview[:5] if isinstance(preview, list) else [],
        "repair_rejects_allowed": backlog.get("repair_rejects_allowed", False),
    }


def seed_legacy_rewrite_runs(
    repo_root: Path,
    queue_root: Path,
    state_root: Path,
    run_root: Path,
    *,
    max_new_runs: int = DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE,
    max_active_runs: int = MAX_ACTIVE_RUNS_PER_CYCLE,
    source_commit: str | None = None,
) -> dict[str, Any]:
    """自動挑最前面的未掃舊文，建立私密 rewrite run 並登記到 coordinator。"""
    if max_new_runs <= 0:
        return {"status": "disabled", "created": 0, "created_run_ids": []}

    active_count = len(_active_states(queue_root))
    if active_count >= max_active_runs:
        return {"status": "active_limit", "created": 0, "created_run_ids": [], "active": active_count}

    legacy_records = publisher.legacy_article_records(repo_root)
    allowed_article_ids = {str(record["id"]) for record in legacy_records}
    backlog = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
        legacy_records=legacy_records,
    )
    if backlog["clean_approve"] > 0:
        return {"status": "publish_ready_first", "created": 0, "created_run_ids": [], "backlog": _compact_legacy_backlog(backlog)}
    if backlog["unattempted"] <= 0:
        return {"status": "idle", "created": 0, "created_run_ids": [], "backlog": _compact_legacy_backlog(backlog)}

    registered_article_ids = _registered_rewrite_article_ids(queue_root)
    inventory = pipeline._existing_rewrite_inventory(repo_root)
    head = source_commit or _head_sha(repo_root)
    capacity = max(0, min(max_new_runs, max_active_runs - active_count))
    created: list[str] = []
    for record in legacy_records:
        if len(created) >= capacity:
            break
        article_id = str(record.get("id") or "")
        if not article_id or article_id in registered_article_ids:
            continue
        inventory_item = inventory.get(article_id)
        if not inventory_item:
            continue
        run_id = f"legacy-auto-sweep-v1-{publisher._record_serial(record)}-{_slug_part(article_id)}"
        run_dir = run_root / run_id
        article_brief = _legacy_rewrite_article_brief(record, inventory_item)
        brief = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "rewrite_existing_body",
            "source_commit": head,
            "sort_contract": "legacy_auto_sweep_v1_oldest_unattempted_first",
            "articles": [article_brief],
        }
        pipeline.validate_rewrite_brief(brief)
        pipeline.write_json(run_dir / "brief.json", brief)
        pipeline.write_json(run_dir / "public-brief.json", pipeline.public_model_brief(brief))
        register_run(run_dir, queue_root)
        registered_article_ids.add(article_id)
        created.append(run_id)

    return {
        "status": "seeded" if created else "idle",
        "created": len(created),
        "created_run_ids": created,
        "backlog": _compact_legacy_backlog(backlog),
    }


def cycle_once(
    queue_root: Path,
    *,
    tick: Tick = run_pipeline_tick,
    process: Process = process_once,
    repo_root: Path | None = None,
    new_matrix_sweep: bool = False,
    new_matrix_run_root: Path | None = None,
    new_matrix_min_active_runs: int = DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS,
    new_matrix_max_new_runs_per_cycle: int = DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE,
    new_matrix_max_articles_per_run: int = DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN,
    legacy_sweep: bool = False,
    legacy_state_root: Path | None = None,
    legacy_run_root: Path | None = None,
    legacy_max_new_runs_per_cycle: int = DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE,
    lane_mode: bool = False,
) -> dict[str, Any]:
    """推進 run 狀態；lane mode 每輪讓四類內容各推進一個 run。"""
    root = queue_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "coordinator.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "active": 0, "complete": 0, "failed": 0, "runner": {"status": "idle"}}

        resolved_repo = (repo_root or Path.cwd()).resolve()
        new_matrix_summary: dict[str, Any] | None = None
        if new_matrix_sweep:
            new_matrix_summary = seed_new_matrix_runs(
                resolved_repo,
                root,
                (new_matrix_run_root or resolved_repo / ".work/gsc-copy").resolve(),
                min_active_runs=new_matrix_min_active_runs,
                max_new_runs=new_matrix_max_new_runs_per_cycle,
                max_articles_per_run=new_matrix_max_articles_per_run,
            )

        legacy_summary: dict[str, Any] | None = None
        if legacy_sweep:
            legacy_summary = seed_legacy_rewrite_runs(
                resolved_repo,
                root,
                (legacy_state_root or resolved_repo / ".work/content-publisher").resolve(),
                (legacy_run_root or resolved_repo / ".work/gsc-copy").resolve(),
                max_new_runs=legacy_max_new_runs_per_cycle,
            )

        active_states = _active_states(root)
        legacy_article_ids = publisher.legacy_article_ids(resolved_repo) if lane_mode else set()
        migrated_jobs = (
            _migrate_pending_jobs(root, active_states, legacy_article_ids)
            if lane_mode
            else None
        )
        states = (
            _select_lane_states(active_states, legacy_article_ids)
            if lane_mode
            else active_states[:MAX_ACTIVE_RUNS_PER_CYCLE]
        )
        pending = 0
        completed = 0
        failed = 0
        for state in states:
            lane = _lane_for_state(state, legacy_article_ids) if lane_mode else None
            outcome = _advance(
                root,
                state,
                tick,
                job_queue_root=_lane_queue_root(root, lane) if lane is not None else None,
            )
            pending += outcome == "pending"
            completed += outcome == "complete"
            failed += outcome == "failed"

        runner: dict[str, str] = {"status": "idle"}
        if pending:
            try:
                runner = process(root)
            except json.JSONDecodeError:
                job_id = next(
                    (str(state["last_job_id"]) for state in states if state.get("last_job_id")),
                    "unknown",
                )
                runner = {"status": "failed", "job_id": job_id, "error_type": "JSONDecodeError"}
            if runner.get("status") == "failed":
                failed += 1
            elif runner.get("status") == "processed" and not lane_mode:
                for state in _active_states(root)[:MAX_ACTIVE_RUNS_PER_CYCLE]:
                    outcome = _advance(root, state, tick)
                    completed += outcome == "complete"
                    failed += outcome == "failed"

        remaining = len(_active_states(root))
        summary = {
            "status": "ok" if failed == 0 else "failed",
            "active": remaining,
            "complete": completed,
            "failed": failed,
            "runner": runner,
            "new_matrix_sweep": new_matrix_summary,
            "legacy_sweep": legacy_summary,
        }
        if lane_mode:
            summary["lanes"] = _lane_summary(root, _active_states(root), legacy_article_ids)
            summary["migrated_jobs"] = migrated_jobs
        return summary


def resume_run(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    state = read_run_state(run_dir, queue_root)
    state["status"] = "active"
    state.pop("error_type", None)
    state.pop("result", None)
    _write_state(queue_root.resolve(), state)
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, default=Path(".work/gemini-runner"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--new-matrix-run-root", type=Path, default=Path(".work/gsc-copy"))
    parser.add_argument("--new-matrix-sweep", action="store_true")
    parser.add_argument("--new-matrix-min-active-runs", type=int, default=DEFAULT_NEW_MATRIX_MIN_ACTIVE_RUNS)
    parser.add_argument("--new-matrix-max-new-runs-per-cycle", type=int, default=DEFAULT_NEW_MATRIX_MAX_NEW_RUNS_PER_CYCLE)
    parser.add_argument("--new-matrix-max-articles-per-run", type=int, default=DEFAULT_NEW_MATRIX_MAX_ARTICLES_PER_RUN)
    parser.add_argument("--legacy-state-root", type=Path, default=Path(".work/content-publisher"))
    parser.add_argument("--legacy-run-root", type=Path, default=Path(".work/gsc-copy"))
    parser.add_argument("--legacy-sweep", action="store_true")
    parser.add_argument("--legacy-max-new-runs-per-cycle", type=int, default=DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE)
    parser.add_argument("--lane-mode", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("run_dir", type=Path)
    resume = subparsers.add_parser("resume")
    resume.add_argument("run_dir", type=Path)
    status = subparsers.add_parser("status")
    status.add_argument("run_dir", type=Path)
    subparsers.add_parser("cycle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue_root = args.queue_root.resolve()
    if args.command == "register":
        result = register_run(args.run_dir, queue_root)
    elif args.command == "resume":
        result = resume_run(args.run_dir, queue_root)
    elif args.command == "status":
        result = read_run_state(args.run_dir, queue_root)
    else:
        result = cycle_once(
            queue_root,
            repo_root=args.repo_root,
            new_matrix_sweep=args.new_matrix_sweep,
            new_matrix_run_root=args.new_matrix_run_root,
            new_matrix_min_active_runs=args.new_matrix_min_active_runs,
            new_matrix_max_new_runs_per_cycle=args.new_matrix_max_new_runs_per_cycle,
            new_matrix_max_articles_per_run=args.new_matrix_max_articles_per_run,
            legacy_sweep=args.legacy_sweep,
            legacy_state_root=args.legacy_state_root,
            legacy_run_root=args.legacy_run_root,
            legacy_max_new_runs_per_cycle=args.legacy_max_new_runs_per_cycle,
            lane_mode=args.lane_mode,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

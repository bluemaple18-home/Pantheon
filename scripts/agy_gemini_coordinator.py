#!/usr/bin/env python3
"""協調 Pantheon 私密 run、sanitized outbox 與使用者擁有的 Gemini runner。"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
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
DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE = 1
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


def _advance(queue_root: Path, state: dict[str, Any], tick: Tick) -> str:
    try:
        result = tick(Path(str(state["run_dir"])), queue_root)
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
    return states[:MAX_ACTIVE_RUNS_PER_CYCLE]


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


def _registered_rewrite_article_ids(queue_root: Path) -> set[str]:
    article_ids: set[str] = set()
    for path in sorted((queue_root / "runs").glob("*.json")) if (queue_root / "runs").exists() else []:
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        article_ids.update(_article_ids_from_brief(_read_run_brief_from_state(state)))
    return article_ids


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
    legacy_sweep: bool = False,
    legacy_state_root: Path | None = None,
    legacy_run_root: Path | None = None,
    legacy_max_new_runs_per_cycle: int = DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE,
) -> dict[str, Any]:
    """每輪最多執行一個外部 job；完成後再 tick 一次寫入下一個狀態。"""
    root = queue_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "coordinator.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "active": 0, "complete": 0, "failed": 0, "runner": {"status": "idle"}}

        legacy_summary: dict[str, Any] | None = None
        if legacy_sweep:
            resolved_repo = (repo_root or Path.cwd()).resolve()
            legacy_summary = seed_legacy_rewrite_runs(
                resolved_repo,
                root,
                (legacy_state_root or resolved_repo / ".work/content-publisher").resolve(),
                (legacy_run_root or resolved_repo / ".work/gsc-copy").resolve(),
                max_new_runs=legacy_max_new_runs_per_cycle,
            )

        states = _active_states(root)
        pending = 0
        completed = 0
        failed = 0
        for state in states:
            outcome = _advance(root, state, tick)
            pending += outcome == "pending"
            completed += outcome == "complete"
            failed += outcome == "failed"

        runner: dict[str, str] = {"status": "idle"}
        if pending:
            runner = process(root)
            if runner.get("status") == "failed":
                failed += 1
            elif runner.get("status") == "processed":
                for state in _active_states(root):
                    outcome = _advance(root, state, tick)
                    completed += outcome == "complete"
                    failed += outcome == "failed"

        remaining = len(_active_states(root))
        return {
            "status": "ok" if failed == 0 else "failed",
            "active": remaining,
            "complete": completed,
            "failed": failed,
            "runner": runner,
            "legacy_sweep": legacy_summary,
        }


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
    parser.add_argument("--legacy-state-root", type=Path, default=Path(".work/content-publisher"))
    parser.add_argument("--legacy-run-root", type=Path, default=Path(".work/gsc-copy"))
    parser.add_argument("--legacy-sweep", action="store_true")
    parser.add_argument("--legacy-max-new-runs-per-cycle", type=int, default=DEFAULT_LEGACY_MAX_NEW_RUNS_PER_CYCLE)
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
            legacy_sweep=args.legacy_sweep,
            legacy_state_root=args.legacy_state_root,
            legacy_run_root=args.legacy_run_root,
            legacy_max_new_runs_per_cycle=args.legacy_max_new_runs_per_cycle,
        )
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

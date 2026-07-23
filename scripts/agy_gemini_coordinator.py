#!/usr/bin/env python3
"""協調 Pantheon 私密 run、sanitized outbox 與使用者擁有的 Gemini runner。"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from scripts.agy_gemini_outbox import (
    ExternalJobFailed,
    ExternalJobPending,
    atomic_write_json,
    run_pipeline_tick,
)
from scripts.agy_gemini_runner import process_once


MAX_BRIEF_BYTES = 12 * 1024
MAX_ACTIVE_RUNS_PER_CYCLE = 5
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


def cycle_once(
    queue_root: Path,
    *,
    tick: Tick = run_pipeline_tick,
    process: Process = process_once,
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
        result = cycle_once(queue_root)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Gemini V4 常駐 shadow health check；與正式產文 queue 完全隔離。"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Final

from scripts.agy_gemini_outbox import (
    atomic_write_json,
    build_external_request,
    create_external_request,
)
from scripts.agy_gemini_runner import process_once
from scripts.agy_gemini_v4_broker import (
    Binding,
    FileAnchorStore,
    replay_ledger,
)


BUCKET_SECONDS: Final = 21_600
BUCKET_HOURS: Final = 6
MODEL: Final = "gemini-3.5-flash"
ROLE: Final = "reviewer"
NAMESPACE_PREFIX: Final = "gemini-v4-shadow-"
PROMPT: Final = (
    "這是公開的 Gemini V4 transport shadow health check。"
    "請只回傳符合 schema 的結果。"
)
EXPECTED_RESULT: Final = {
    "status": "PASS",
    "transport": "gemini-v4-quota-shadow",
}
RESPONSE_SCHEMA: Final = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["PASS"]},
        "transport": {
            "type": "string",
            "enum": ["gemini-v4-quota-shadow"],
        },
    },
    "required": ["status", "transport"],
    "additionalProperties": False,
}
Process = Callable[[Path], dict[str, str]]


def _now() -> datetime:
    return datetime.now(UTC)


def bucket_key(now: datetime) -> str:
    """將時間收斂到固定六小時UTC bucket；一天恰四個bucket。"""
    if now.tzinfo is None:
        raise ValueError("shadow time must be timezone-aware")
    current = now.astimezone(UTC)
    start = current.replace(
        hour=(current.hour // BUCKET_HOURS) * BUCKET_HOURS,
        minute=0,
        second=0,
        microsecond=0,
    )
    return start.strftime("%Y%m%dT%H%M%SZ")


def build_shadow_request(bucket: str) -> dict[str, Any]:
    if (
        len(bucket) != 16
        or not bucket.endswith("Z")
        or not bucket[:8].isdigit()
        or bucket[8] != "T"
        or not bucket[9:15].isdigit()
    ):
        raise ValueError("shadow bucket is invalid")
    return build_external_request(
        namespace=f"{NAMESPACE_PREFIX}{bucket}",
        role=ROLE,
        model=MODEL,
        prompt=PROMPT,
        response_schema=RESPONSE_SCHEMA,
    )


def _create_shadow_request(queue_root: Path, bucket: str) -> dict[str, Any]:
    request = build_shadow_request(bucket)
    created = create_external_request(
        queue_root,
        namespace=str(request["namespace"]),
        role=ROLE,
        model=MODEL,
        prompt=PROMPT,
        response_schema=RESPONSE_SCHEMA,
    )
    if created != request:
        raise ValueError("shadow request binding is invalid")
    return created


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _ledger_events(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    if not path.is_file():
        return [], None
    try:
        raw = path.read_bytes()
        events = [json.loads(line) for line in raw.splitlines()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [], None
    if not all(isinstance(event, dict) for event in events):
        return [], None
    return events, hashlib.sha256(raw).hexdigest()


def _collect_observation(
    queue_root: Path,
    request: dict[str, Any],
    process_result: dict[str, str],
    observed_at: str,
) -> dict[str, Any]:
    job_id = str(request["job_id"])
    bucket = str(request["namespace"]).removeprefix(NAMESPACE_PREFIX)
    ledger_path = queue_root / "v4" / "ledger" / f"{job_id}.jsonl"
    events, ledger_sha256 = _ledger_events(ledger_path)
    selected = [
        event
        for event in events
        if event.get("event_type") == "CREDENTIAL_SELECTED"
    ]
    terminal = [
        event
        for event in events
        if event.get("event_type") == "PROCESS_TERMINAL"
    ]
    anchor_store = FileAnchorStore(queue_root / "v4" / "anchors")
    try:
        anchor = anchor_store.load(job_id, "attempt-1")
        replay = replay_ledger(
            ledger_path,
            Binding(job_id, str(request["namespace"]), "attempt-1"),
            anchor,
        )
    except Exception:
        anchor = None
        replay = None
    inbox = _read_json(queue_root / "inbox" / f"{job_id}.json")
    failed = _read_json(queue_root / "failed" / f"{job_id}.json")
    result = inbox.get("result") if inbox is not None else None
    valid = (
        replay is not None
        and replay.status == "COMPLETE"
        and replay.process_count == 1
        and not replay.errors
        and len(selected) == 1
        and len(terminal) == 1
        and terminal[0].get("outcome") == "SUCCESS"
        and result == EXPECTED_RESULT
        and failed is None
    )
    observation: dict[str, Any] = {
        "schema_version": 1,
        "bucket": bucket,
        "job_id": job_id,
        "observed_at": observed_at,
        "status": "PASS" if valid else "FAIL",
        "runner_status": process_result.get("status"),
        "replay_status": replay.status if replay is not None else "INVALID",
        "process_count": replay.process_count if replay is not None else "UNKNOWN",
        "outcome": terminal[0].get("outcome") if len(terminal) == 1 else None,
        "result_validation": "VALID" if result == EXPECTED_RESULT else "INVALID",
        "credential_selected_count": len(selected),
        "pool_id": selected[0].get("pool_id") if len(selected) == 1 else None,
        "slot_id": selected[0].get("slot_id") if len(selected) == 1 else None,
        "pool_sha256": (
            selected[0].get("pool_sha256") if len(selected) == 1 else None
        ),
        "ledger_sha256": ledger_sha256,
        "final_anchor": anchor,
        "automatic_resend_allowed": False,
    }
    if failed is not None and type(failed.get("error_type")) is str:
        observation["error_type"] = failed["error_type"]
    return observation


def run_once(
    state_root: Path,
    *,
    now: datetime | None = None,
    process: Process = process_once,
) -> dict[str, Any]:
    """執行目前bucket；既有observation或durable job只讀取，不重新送出。"""
    root = state_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "DISABLED").exists():
        return {"status": "DISABLED"}
    lock_path = root / "shadow.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "BUSY"}
        current = now or _now()
        bucket = bucket_key(current)
        observation_path = root / "observations" / f"{bucket}.json"
        existing = _read_json(observation_path)
        if existing is not None:
            return existing | {"cached": True}
        queue_root = root / "buckets" / bucket
        request = _create_shadow_request(queue_root, bucket)
        process_result = process(queue_root)
        observation = _collect_observation(
            queue_root,
            request,
            process_result,
            current.astimezone(UTC).isoformat(timespec="seconds"),
        )
        atomic_write_json(observation_path, observation)
        atomic_write_json(root / "latest.json", observation)
        return observation


def read_status(state_root: Path) -> dict[str, Any]:
    latest = _read_json(state_root.resolve() / "latest.json")
    return latest if latest is not None else {"status": "NEVER_RUN"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once")
    subparsers.add_parser("status")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = (
        run_once(args.state_root)
        if args.command == "run-once"
        else read_status(args.state_root)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if result.get("status") == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

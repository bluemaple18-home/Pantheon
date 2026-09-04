#!/usr/bin/env python3
"""Writer 前的本機 topic reservation primitive。"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


_ACTIVE_STATUSES = {"RESERVED", "IN_PROGRESS", "SCHEDULED"}
_ALL_STATUSES = {*_ACTIVE_STATUSES, "PUBLISHED", "EXPIRED_OR_RELEASED"}
_RECORD_FIELDS = {
    "topic_id",
    "semantic_exclusion_key",
    "reservation_token",
    "lane_id",
    "run_id",
    "reserved_at",
    "expires_at",
    "owner_generation",
    "status",
}


def _clock() -> float:
    return time.time()


def _result(
    ok: bool,
    result: str,
    record: dict[str, Any] | None = None,
) -> dict[str, object]:
    return {
        "ok": ok,
        "result": result,
        "reservation": dict(record) if record is not None else None,
    }


def _valid_text(value: object) -> bool:
    return type(value) is str and bool(value) and value.strip() == value


def _valid_root(value: object) -> bool:
    return isinstance(value, (str, os.PathLike)) and bool(os.fspath(value))


def _valid_claim(
    state_root: object,
    *,
    topic_id: object,
    reservation_token: object,
    lane_id: object,
    run_id: object,
    semantic_exclusion_key: object,
    ttl_seconds: object,
) -> bool:
    return (
        _valid_root(state_root)
        and _valid_text(topic_id)
        and _valid_text(reservation_token)
        and _valid_text(lane_id)
        and _valid_text(run_id)
        and (
            semantic_exclusion_key is None
            or _valid_text(semantic_exclusion_key)
        )
        and type(ttl_seconds) in {int, float}
        and math.isfinite(ttl_seconds)
        and ttl_seconds > 0
    )


def _valid_owner(
    state_root: object,
    *,
    topic_id: object,
    reservation_token: object,
    lane_id: object,
    run_id: object,
    owner_generation: object,
) -> bool:
    return (
        _valid_root(state_root)
        and _valid_text(topic_id)
        and _valid_text(reservation_token)
        and _valid_text(lane_id)
        and _valid_text(run_id)
        and type(owner_generation) is int
        and owner_generation > 0
    )


def _resolved_root(state_root: str | os.PathLike[str]) -> Path:
    return Path(state_root).resolve()


def _reservation_path(state_root: Path, topic_id: str) -> Path:
    opaque_id = hashlib.sha256(topic_id.encode("utf-8")).hexdigest()[:24]
    return state_root / "reservations" / f"{opaque_id}.json"


@contextmanager
def _state_lock(state_root: Path) -> Iterator[None]:
    state_root.mkdir(parents=True, exist_ok=True)
    path = state_root / ".topic-reservation.lock"
    with path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _record_is_valid(record: object) -> bool:
    if type(record) is not dict or set(record) != _RECORD_FIELDS:
        return False
    semantic_key = record.get("semantic_exclusion_key")
    return (
        _valid_text(record.get("topic_id"))
        and _valid_text(record.get("reservation_token"))
        and _valid_text(record.get("lane_id"))
        and _valid_text(record.get("run_id"))
        and (semantic_key is None or _valid_text(semantic_key))
        and type(record.get("reserved_at")) in {int, float}
        and math.isfinite(record["reserved_at"])
        and type(record.get("expires_at")) in {int, float}
        and math.isfinite(record["expires_at"])
        and record["expires_at"] > record["reserved_at"]
        and type(record.get("owner_generation")) is int
        and record["owner_generation"] > 0
        and record.get("status") in _ALL_STATUSES
    )


def _load_records(state_root: Path) -> list[dict[str, Any]] | None:
    directory = state_root / "reservations"
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    topics: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not _record_is_valid(record):
            return None
        topic_id = record["topic_id"]
        if path != _reservation_path(state_root, topic_id) or topic_id in topics:
            return None
        topics.add(topic_id)
        records.append(record)
    return records


def _atomic_write_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(
                record,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _blocks_claim(record: dict[str, Any], now: float) -> bool:
    return record["status"] == "PUBLISHED" or (
        record["status"] in _ACTIVE_STATUSES and now < record["expires_at"]
    )


def claim_topic_reservation(
    state_root: str | os.PathLike[str],
    *,
    topic_id: str,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    ttl_seconds: float,
    semantic_exclusion_key: str | None = None,
) -> dict[str, object]:
    """原子 claim topic；正常競爭以明確 result 回傳。"""
    if not _valid_claim(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        semantic_exclusion_key=semantic_exclusion_key,
        ttl_seconds=ttl_seconds,
    ):
        return _result(False, "invalid")
    root = _resolved_root(state_root)
    with _state_lock(root):
        now = _clock()
        records = _load_records(root)
        if records is None:
            return _result(False, "unavailable")
        previous: dict[str, Any] | None = None
        for record in records:
            if record["topic_id"] == topic_id:
                previous = record
                if (
                    record["status"] in _ACTIVE_STATUSES
                    and now < record["expires_at"]
                    and record["reservation_token"] == reservation_token
                    and record["lane_id"] == lane_id
                    and record["run_id"] == run_id
                    and record["semantic_exclusion_key"] == semantic_exclusion_key
                ):
                    return _result(True, "claimed", record)
                if _blocks_claim(record, now):
                    result = (
                        "unavailable"
                        if record["status"] == "PUBLISHED"
                        else "already_reserved"
                    )
                    return _result(False, result)
            if (
                semantic_exclusion_key is not None
                and record["semantic_exclusion_key"] == semantic_exclusion_key
                and _blocks_claim(record, now)
            ):
                return _result(False, "unavailable")
        generation = 1 if previous is None else previous["owner_generation"] + 1
        record = {
            "topic_id": topic_id,
            "semantic_exclusion_key": semantic_exclusion_key,
            "reservation_token": reservation_token,
            "lane_id": lane_id,
            "run_id": run_id,
            "reserved_at": now,
            "expires_at": now + float(ttl_seconds),
            "owner_generation": generation,
            "status": "RESERVED",
        }
        _atomic_write_record(_reservation_path(root, topic_id), record)
        return _result(True, "claimed", record)


def _is_owner(
    record: dict[str, Any],
    *,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    owner_generation: int,
) -> bool:
    return (
        record["reservation_token"] == reservation_token
        and record["lane_id"] == lane_id
        and record["run_id"] == run_id
        and record["owner_generation"] == owner_generation
    )


def _transition(
    state_root: str | os.PathLike[str],
    *,
    topic_id: str,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    owner_generation: int,
    expected_statuses: set[str],
    next_status: str,
    success_result: str,
    release: bool = False,
) -> dict[str, object]:
    if not _valid_owner(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        owner_generation=owner_generation,
    ):
        return _result(False, "invalid")
    root = _resolved_root(state_root)
    with _state_lock(root):
        now = _clock()
        records = _load_records(root)
        if records is None:
            return _result(False, "unavailable")
        record = next(
            (candidate for candidate in records if candidate["topic_id"] == topic_id),
            None,
        )
        if record is None:
            return _result(False, "unavailable")
        if not _is_owner(
            record,
            reservation_token=reservation_token,
            lane_id=lane_id,
            run_id=run_id,
            owner_generation=owner_generation,
        ):
            return _result(False, "foreign_owner")
        if record["status"] == next_status:
            if record["status"] in _ACTIVE_STATUSES and now >= record["expires_at"]:
                return _result(False, "expired")
            return _result(True, success_result, record)
        if record["status"] not in expected_statuses:
            return _result(False, "unavailable")
        if not release and now >= record["expires_at"]:
            return _result(False, "expired")
        semantic_key = record["semantic_exclusion_key"]
        if next_status != "EXPIRED_OR_RELEASED" and semantic_key is not None:
            for candidate in records:
                if (
                    candidate["topic_id"] != topic_id
                    and candidate["semantic_exclusion_key"] == semantic_key
                    and _blocks_claim(candidate, now)
                ):
                    return _result(False, "unavailable")
        updated = {**record, "status": next_status}
        _atomic_write_record(_reservation_path(root, topic_id), updated)
        return _result(True, success_result, updated)


def activate_topic_reservation(
    state_root: str | os.PathLike[str],
    *,
    topic_id: str,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    owner_generation: int,
) -> dict[str, object]:
    """由 reservation owner 將 RESERVED 轉為 IN_PROGRESS。"""
    return _transition(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        owner_generation=owner_generation,
        expected_statuses={"RESERVED"},
        next_status="IN_PROGRESS",
        success_result="activated",
    )


def schedule_topic_reservation(
    state_root: str | os.PathLike[str],
    *,
    topic_id: str,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    owner_generation: int,
) -> dict[str, object]:
    """由 reservation owner 將 IN_PROGRESS 轉為 SCHEDULED。"""
    return _transition(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        owner_generation=owner_generation,
        expected_statuses={"IN_PROGRESS"},
        next_status="SCHEDULED",
        success_result="scheduled",
    )


def publish_topic_reservation(
    state_root: str | os.PathLike[str],
    *,
    topic_id: str,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    owner_generation: int,
) -> dict[str, object]:
    """由 reservation owner 將 SCHEDULED 轉為永久 PUBLISHED。"""
    return _transition(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        owner_generation=owner_generation,
        expected_statuses={"SCHEDULED"},
        next_status="PUBLISHED",
        success_result="published",
    )


def release_topic_reservation(
    state_root: str | os.PathLike[str],
    *,
    topic_id: str,
    reservation_token: str,
    lane_id: str,
    run_id: str,
    owner_generation: int,
) -> dict[str, object]:
    """由 owner 明確釋放未 publish 的 reservation。"""
    return _transition(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        owner_generation=owner_generation,
        expected_statuses=set(_ACTIVE_STATUSES),
        next_status="EXPIRED_OR_RELEASED",
        success_result="released",
        release=True,
    )


__all__ = [
    "activate_topic_reservation",
    "claim_topic_reservation",
    "publish_topic_reservation",
    "release_topic_reservation",
    "schedule_topic_reservation",
]

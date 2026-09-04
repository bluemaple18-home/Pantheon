from __future__ import annotations

import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier
from typing import Callable, Iterator

import pytest

import scripts.pantheon_topic_reservation as reservation


def _claim(
    state_root: Path,
    *,
    topic_id: str = "topic-a",
    reservation_token: str = "token-a",
    lane_id: str = "lane-a",
    run_id: str = "run-a",
    semantic_exclusion_key: str | None = None,
    ttl_seconds: float = 60,
) -> dict[str, object]:
    return reservation.claim_topic_reservation(
        state_root,
        topic_id=topic_id,
        reservation_token=reservation_token,
        lane_id=lane_id,
        run_id=run_id,
        semantic_exclusion_key=semantic_exclusion_key,
        ttl_seconds=ttl_seconds,
    )


def _record_path(state_root: Path, topic_id: str) -> Path:
    paths = list((state_root / "reservations").glob("*.json"))
    for path in paths:
        if json.loads(path.read_text(encoding="utf-8"))["topic_id"] == topic_id:
            return path
    raise AssertionError(f"missing reservation for {topic_id}")


def _owner(result: dict[str, object]) -> dict[str, object]:
    record = result["reservation"]
    assert isinstance(record, dict)
    return {
        "topic_id": record["topic_id"],
        "reservation_token": record["reservation_token"],
        "lane_id": record["lane_id"],
        "run_id": record["run_id"],
        "owner_generation": record["owner_generation"],
    }


def _fail_next_directory_fsync(monkeypatch: pytest.MonkeyPatch) -> None:
    original_fsync = reservation.os.fsync
    failed = False

    def fail_after_directory_fsync(descriptor: int) -> None:
        nonlocal failed
        original_fsync(descriptor)
        if not failed and stat.S_ISDIR(os.fstat(descriptor).st_mode):
            failed = True
            raise OSError("injected directory fsync failure")

    monkeypatch.setattr(reservation.os, "fsync", fail_after_directory_fsync)


def test_four_concurrent_same_topic_claimants_have_one_winner(tmp_path: Path) -> None:
    barrier = Barrier(4)

    def contend(index: int) -> dict[str, object]:
        barrier.wait()
        return _claim(
            tmp_path,
            reservation_token=f"token-{index}",
            lane_id=f"lane-{index}",
            run_id=f"run-{index}",
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(contend, range(4)))

    assert [result["result"] for result in results].count("claimed") == 1
    assert [result["result"] for result in results].count("already_reserved") == 3
    assert len(list((tmp_path / "reservations").glob("*.json"))) == 1


def test_four_concurrent_cluster_claimants_have_one_winner(tmp_path: Path) -> None:
    barrier = Barrier(4)

    def contend(index: int) -> dict[str, object]:
        barrier.wait()
        return _claim(
            tmp_path,
            topic_id=f"topic-{index}",
            reservation_token=f"token-{index}",
            lane_id=f"lane-{index}",
            run_id=f"run-{index}",
            semantic_exclusion_key="cluster-a",
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(contend, range(4)))

    assert [result["result"] for result in results].count("claimed") == 1
    assert [result["result"] for result in results].count("unavailable") == 3


def test_claim_timestamps_use_time_after_lock_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    original_lock = reservation._state_lock

    @contextmanager
    def advance_after_acquisition(state_root: Path) -> Iterator[None]:
        with original_lock(state_root):
            now[0] = 200.0
            yield

    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    monkeypatch.setattr(reservation, "_state_lock", advance_after_acquisition)

    claimed = _claim(tmp_path, ttl_seconds=10)

    assert claimed["result"] == "claimed"
    assert claimed["reservation"]["reserved_at"] == 200.0  # type: ignore[index]
    assert claimed["reservation"]["expires_at"] == 210.0  # type: ignore[index]


def test_claim_replay_after_directory_fsync_failure_returns_original_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    _fail_next_directory_fsync(monkeypatch)

    with pytest.raises(OSError, match="directory fsync"):
        _claim(tmp_path, semantic_exclusion_key="cluster-a", ttl_seconds=10)

    path = _record_path(tmp_path, "topic-a")
    committed = json.loads(path.read_text(encoding="utf-8"))
    committed_bytes = path.read_bytes()
    assert committed["status"] == "RESERVED"
    assert committed["reservation_token"] == "token-a"
    assert committed["owner_generation"] == 1
    assert committed["reserved_at"] == 100.0
    assert committed["expires_at"] == 110.0

    now[0] = 105.0
    assert _claim(
        tmp_path,
        semantic_exclusion_key="cluster-a",
        ttl_seconds=999,
    ) == {"ok": True, "result": "claimed", "reservation": committed}
    assert path.read_bytes() == committed_bytes


def test_activate_replay_after_directory_fsync_failure_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claimed = _claim(tmp_path)
    owner = _owner(claimed)
    path = _record_path(tmp_path, "topic-a")
    _fail_next_directory_fsync(monkeypatch)

    with pytest.raises(OSError, match="directory fsync"):
        reservation.activate_topic_reservation(tmp_path, **owner)

    committed = json.loads(path.read_text(encoding="utf-8"))
    committed_bytes = path.read_bytes()
    assert committed["status"] == "IN_PROGRESS"
    assert reservation.activate_topic_reservation(tmp_path, **owner) == {
        "ok": True,
        "result": "activated",
        "reservation": committed,
    }
    assert path.read_bytes() == committed_bytes


@pytest.mark.parametrize("target_status", ["IN_PROGRESS", "SCHEDULED"])
def test_expired_active_target_replay_fails_closed_without_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_status: str,
) -> None:
    now = [100.0]
    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    owner = _owner(_claim(tmp_path, ttl_seconds=10))
    operation = reservation.activate_topic_reservation
    if target_status == "SCHEDULED":
        assert operation(tmp_path, **owner)["result"] == "activated"
        operation = reservation.schedule_topic_reservation
    assert operation(tmp_path, **owner)["ok"] is True

    path = _record_path(tmp_path, "topic-a")
    active_bytes = path.read_bytes()
    now[0] = 111.0
    assert operation(tmp_path, **owner) == {
        "ok": False,
        "result": "expired",
        "reservation": None,
    }
    assert path.read_bytes() == active_bytes


def test_publish_replay_is_idempotent_but_remains_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    claimed = _claim(tmp_path, semantic_exclusion_key="cluster-a", ttl_seconds=10)
    owner = _owner(claimed)
    path = _record_path(tmp_path, "topic-a")
    assert reservation.activate_topic_reservation(tmp_path, **owner)["ok"] is True
    assert reservation.schedule_topic_reservation(tmp_path, **owner)["ok"] is True
    assert reservation.publish_topic_reservation(tmp_path, **owner)["ok"] is True

    published = json.loads(path.read_text(encoding="utf-8"))
    published_bytes = path.read_bytes()
    now[0] = 10_000.0
    assert reservation.publish_topic_reservation(tmp_path, **owner) == {
        "ok": True,
        "result": "published",
        "reservation": published,
    }
    assert reservation.release_topic_reservation(tmp_path, **owner)["ok"] is False
    assert _claim(
        tmp_path,
        reservation_token="token-b",
        lane_id="lane-b",
        run_id="run-b",
        semantic_exclusion_key="cluster-a",
    )["ok"] is False
    assert path.read_bytes() == published_bytes


def test_pre_replace_failure_leaves_no_reservation_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_before_replace(source: object, destination: object) -> None:
        raise OSError("injected pre-replace failure")

    monkeypatch.setattr(reservation.os, "replace", fail_before_replace)

    with pytest.raises(OSError, match="pre-replace"):
        _claim(tmp_path)

    assert list((tmp_path / "reservations").glob("*.json")) == []


def test_transition_expiry_is_checked_after_lock_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    claimed = _claim(tmp_path, ttl_seconds=10)
    owner = _owner(claimed)
    path = _record_path(tmp_path, "topic-a")
    before = path.read_bytes()
    original_lock = reservation._state_lock

    @contextmanager
    def advance_after_acquisition(state_root: Path) -> Iterator[None]:
        with original_lock(state_root):
            now[0] = 111.0
            yield

    monkeypatch.setattr(reservation, "_state_lock", advance_after_acquisition)

    assert reservation.activate_topic_reservation(tmp_path, **owner) == {
        "ok": False,
        "result": "expired",
        "reservation": None,
    }
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("first_key", "second_key"),
    [
        ("cluster-a", None),
        (None, "cluster-a"),
        ("cluster-a", "cluster-b"),
    ],
)
def test_topic_identity_is_always_exclusive_across_optional_key_combinations(
    tmp_path: Path,
    first_key: str | None,
    second_key: str | None,
) -> None:
    assert _claim(tmp_path, semantic_exclusion_key=first_key)["result"] == "claimed"

    contender = _claim(
        tmp_path,
        lane_id="lane-b",
        run_id="run-b",
        semantic_exclusion_key=second_key,
    )

    assert contender == {"ok": False, "result": "already_reserved", "reservation": None}


def test_owner_only_lifecycle_and_published_is_permanently_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    claimed = _claim(tmp_path, semantic_exclusion_key="cluster-a", ttl_seconds=10)
    owner = _owner(claimed)
    path = _record_path(tmp_path, "topic-a")

    operations: tuple[Callable[..., dict[str, object]], ...] = (
        reservation.activate_topic_reservation,
        reservation.schedule_topic_reservation,
        reservation.publish_topic_reservation,
        reservation.release_topic_reservation,
    )
    for operation in operations:
        before = path.read_bytes()
        foreign = operation(tmp_path, **{**owner, "reservation_token": "foreign"})
        assert foreign == {"ok": False, "result": "foreign_owner", "reservation": None}
        assert path.read_bytes() == before

    assert reservation.activate_topic_reservation(tmp_path, **owner)["result"] == "activated"
    assert reservation.schedule_topic_reservation(tmp_path, **owner)["result"] == "scheduled"
    assert reservation.publish_topic_reservation(tmp_path, **owner)["result"] == "published"

    published_bytes = path.read_bytes()
    now[0] = 10_000.0
    assert reservation.release_topic_reservation(tmp_path, **owner) == {
        "ok": False,
        "result": "unavailable",
        "reservation": None,
    }
    assert _claim(tmp_path, lane_id="lane-b", run_id="run-b")["result"] == "unavailable"
    assert (
        _claim(
            tmp_path,
            topic_id="topic-b",
            lane_id="lane-b",
            run_id="run-b",
            semantic_exclusion_key="cluster-a",
        )["result"]
        == "unavailable"
    )
    assert path.read_bytes() == published_bytes


def test_expiry_allows_safe_topic_and_cluster_takeover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr(reservation, "_clock", lambda: now[0])
    first = _claim(tmp_path, semantic_exclusion_key="cluster-a", ttl_seconds=10)
    first_owner = _owner(first)

    now[0] = 111.0
    replacement = _claim(
        tmp_path,
        lane_id="lane-b",
        run_id="run-b",
        semantic_exclusion_key="cluster-b",
    )
    assert replacement["result"] == "claimed"
    assert replacement["reservation"]["owner_generation"] == 2  # type: ignore[index]

    replacement_path = _record_path(tmp_path, "topic-a")
    before = replacement_path.read_bytes()
    assert reservation.activate_topic_reservation(tmp_path, **first_owner)["result"] == "foreign_owner"
    assert replacement_path.read_bytes() == before

    cluster_root = tmp_path / "cluster"
    _claim(
        cluster_root,
        topic_id="topic-a",
        semantic_exclusion_key="cluster-a",
        ttl_seconds=10,
    )
    now[0] = 122.0
    assert (
        _claim(
            cluster_root,
            topic_id="topic-b",
            lane_id="lane-b",
            run_id="run-b",
            semantic_exclusion_key="cluster-a",
        )["result"]
        == "claimed"
    )


def test_release_rerun_invalid_and_crash_shaped_files_are_deterministic(
    tmp_path: Path,
) -> None:
    claimed = _claim(tmp_path)
    owner = _owner(claimed)
    path = _record_path(tmp_path, "topic-a")

    invalid_before = path.read_bytes()
    assert reservation.activate_topic_reservation(
        tmp_path,
        **{**owner, "lane_id": ""},
    ) == {"ok": False, "result": "invalid", "reservation": None}
    assert path.read_bytes() == invalid_before

    assert reservation.release_topic_reservation(tmp_path, **owner)["result"] == "released"
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "EXPIRED_OR_RELEASED"
    released_bytes = path.read_bytes()
    assert reservation.release_topic_reservation(tmp_path, **owner)["result"] == "released"
    assert path.read_bytes() == released_bytes

    crash_file = path.with_name(f".{path.name}.crash.tmp")
    crash_file.write_text("partial", encoding="utf-8")
    reclaimed = _claim(tmp_path, lane_id="lane-b", run_id="run-b")
    assert reclaimed["result"] == "claimed"
    assert reclaimed["reservation"]["owner_generation"] == 2  # type: ignore[index]
    assert crash_file.read_text(encoding="utf-8") == "partial"

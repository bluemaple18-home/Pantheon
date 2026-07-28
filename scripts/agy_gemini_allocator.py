#!/usr/bin/env python3
"""Production Gemini credential pool 的 durable strict round-robin allocator。"""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator


MAX_ALLOCATOR_STATE_BYTES = 4 * 1024
MAX_ALLOCATION_ORDINAL = (1 << 63) - 1
MAX_TIMESTAMP_MILLISECONDS = (1 << 63) - 1
MAX_RATE_LIMIT_COOLDOWN_SECONDS = 60 * 60
SAFE_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SAFE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRODUCTION_SLOT_IDS = ("account-1", "account-2", "account-3")
RATE_LIMIT_REASON = "API_RATE_LIMITED"


@dataclass(frozen=True)
class _Cooldown:
    slot_id: str
    cooldown_started_ms: int
    cooldown_until_ms: int

    def state_payload(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "cooldown_started_ms": self.cooldown_started_ms,
            "cooldown_until_ms": self.cooldown_until_ms,
            "reason": RATE_LIMIT_REASON,
        }

    def receipt_payload(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "cooldown_started_ms": self.cooldown_started_ms,
            "cooldown_until_ms": self.cooldown_until_ms,
        }


@dataclass(frozen=True)
class _AllocatorState:
    last_ordinal: int
    last_slot_id: str | None
    cooldowns: tuple[_Cooldown, ...]
    state_identity: tuple[int, int] | None
    expected_lock_identity: tuple[int, int] | None


def _open_allocator_directory(path: Path) -> int:
    label = "production allocator state directory"
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISDIR(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o022
    ):
        raise ValueError(f"{label} is unsafe")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"{label} cannot be opened") from error
    after = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(after.st_mode)
        or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        or after.st_uid != os.getuid()
        or after.st_mode & 0o022
    ):
        os.close(descriptor)
        raise ValueError(f"{label} changed during validation")
    return descriptor


def _assert_path_identity(path: Path, descriptor: int, *, label: str) -> tuple[int, int]:
    try:
        current = path.lstat()
        opened = os.fstat(descriptor)
    except OSError as error:
        raise ValueError(f"{label} changed during allocation") from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
    ):
        raise ValueError(f"{label} changed during allocation")
    return opened.st_dev, opened.st_ino


def _assert_directory_identity(path: Path, descriptor: int) -> None:
    try:
        current = path.lstat()
        opened = os.fstat(descriptor)
    except OSError as error:
        raise ValueError(
            "production allocator state directory changed during allocation"
        ) from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
    ):
        raise ValueError(
            "production allocator state directory changed during allocation"
        )


def _private_state_stat(path: Path, *, minimum_size: int) -> os.stat_result:
    try:
        current = path.lstat()
    except OSError as error:
        raise ValueError("production allocator state file is unavailable") from error
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or current.st_uid != os.getuid()
        or current.st_mode & 0o077
        or not minimum_size <= current.st_size <= MAX_ALLOCATOR_STATE_BYTES
    ):
        raise ValueError(
            "production allocator state file must be owner-only regular file"
        )
    return current


def _open_private_state(path: Path) -> int:
    before = _private_state_stat(path, minimum_size=2)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("production allocator state file cannot be opened") from error
    after = os.fstat(descriptor)
    if (
        not stat.S_ISREG(after.st_mode)
        or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        or after.st_uid != os.getuid()
        or after.st_mode & 0o077
        or not 2 <= after.st_size <= MAX_ALLOCATOR_STATE_BYTES
    ):
        os.close(descriptor)
        raise ValueError("production allocator state file changed during validation")
    return descriptor


def _open_allocator_lock(path: Path) -> int:
    label = "production allocator lock file"
    flags = (
        os.O_RDWR
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        before = path.lstat()
    except FileNotFoundError:
        try:
            descriptor = os.open(
                path,
                flags | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            try:
                before = path.lstat()
            except OSError as error:
                raise ValueError(f"{label} changed during creation") from error
        except OSError as error:
            raise ValueError(f"{label} cannot be created") from error
        else:
            after = os.fstat(descriptor)
            if (
                not stat.S_ISREG(after.st_mode)
                or after.st_uid != os.getuid()
                or after.st_mode & 0o077
                or after.st_size != 0
            ):
                os.close(descriptor)
                raise ValueError(f"{label} must be owner-only regular file")
            return descriptor
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o077
        or before.st_size != 0
    ):
        raise ValueError(f"{label} must be owner-only regular file")
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"{label} cannot be opened") from error
    after = os.fstat(descriptor)
    if (
        not stat.S_ISREG(after.st_mode)
        or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        or after.st_uid != os.getuid()
        or after.st_mode & 0o077
        or after.st_size != 0
    ):
        os.close(descriptor)
        raise ValueError(f"{label} changed during validation")
    return descriptor


def _open_existing_allocator_lock(path: Path) -> int:
    label = "production allocator lock file"
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable") from error
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.getuid()
        or before.st_mode & 0o077
        or before.st_size != 0
    ):
        raise ValueError(f"{label} must be owner-only regular file")
    flags = (
        os.O_RDWR
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"{label} cannot be opened") from error
    after = os.fstat(descriptor)
    if (
        not stat.S_ISREG(after.st_mode)
        or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        or after.st_uid != os.getuid()
        or after.st_mode & 0o077
        or after.st_size != 0
    ):
        os.close(descriptor)
        raise ValueError(f"{label} changed during validation")
    return descriptor


def _read_state(
    path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
) -> _AllocatorState:
    try:
        path.lstat()
    except FileNotFoundError:
        return _AllocatorState(0, None, (), None, None)
    except OSError as error:
        raise ValueError("production allocator state file is unavailable") from error
    descriptor = _open_private_state(path)
    try:
        current = os.fstat(descriptor)
        encoded = os.read(descriptor, MAX_ALLOCATOR_STATE_BYTES + 1)
        if (
            len(encoded) != current.st_size
            or len(encoded) > MAX_ALLOCATOR_STATE_BYTES
        ):
            raise ValueError("production allocator state file size changed")
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(
            encoded,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite JSON constant")
            ),
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("production allocator state JSON is invalid") from error
    common_keys = {
        "last_ordinal",
        "lock_device",
        "lock_inode",
        "manifest_sha256",
        "pool_id",
        "schema_version",
    }
    if not isinstance(payload, dict):
        raise ValueError("production allocator state schema is invalid")
    schema_version = payload.get("schema_version")
    if schema_version == 1:
        if set(payload) != common_keys:
            raise ValueError("production allocator state schema is invalid")
    elif schema_version == 2:
        if set(payload) != common_keys | {"cooldowns", "last_slot_id"}:
            raise ValueError("production allocator state schema is invalid")
    else:
        raise ValueError("production allocator state schema is invalid")
    last_ordinal = payload.get("last_ordinal")
    lock_device = payload.get("lock_device")
    lock_inode = payload.get("lock_inode")
    if (
        type(schema_version) is not int
        or type(payload.get("pool_id")) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(payload["pool_id"]) is None
        or type(payload.get("manifest_sha256")) is not str
        or SAFE_SHA256.fullmatch(payload["manifest_sha256"]) is None
        or type(last_ordinal) is not int
        or not 1 <= last_ordinal <= MAX_ALLOCATION_ORDINAL
        or type(lock_device) is not int
        or lock_device < 0
        or type(lock_inode) is not int
        or lock_inode <= 0
    ):
        raise ValueError("production allocator state schema is invalid")
    if payload["pool_id"] != pool_id:
        raise ValueError("production allocator state pool mismatch")
    if payload["manifest_sha256"] != manifest_sha256:
        raise ValueError("production allocator state manifest mismatch")
    last_slot_id = PRODUCTION_SLOT_IDS[(last_ordinal - 1) % len(PRODUCTION_SLOT_IDS)]
    cooldowns: tuple[_Cooldown, ...] = ()
    if schema_version == 2:
        if (
            type(payload.get("last_slot_id")) is not str
            or payload["last_slot_id"] not in PRODUCTION_SLOT_IDS
            or not isinstance(payload.get("cooldowns"), list)
            or len(payload["cooldowns"]) > len(PRODUCTION_SLOT_IDS)
        ):
            raise ValueError("production allocator state schema is invalid")
        last_slot_id = payload["last_slot_id"]
        parsed: list[_Cooldown] = []
        seen_slots: set[str] = set()
        for item in payload["cooldowns"]:
            if not isinstance(item, dict) or set(item) != {
                "cooldown_started_ms",
                "cooldown_until_ms",
                "reason",
                "slot_id",
            }:
                raise ValueError("production allocator state schema is invalid")
            slot_id = item.get("slot_id")
            started_ms = item.get("cooldown_started_ms")
            until_ms = item.get("cooldown_until_ms")
            if (
                type(slot_id) is not str
                or slot_id not in PRODUCTION_SLOT_IDS
                or slot_id in seen_slots
                or type(started_ms) is not int
                or type(until_ms) is not int
                or not 0 <= started_ms < until_ms <= MAX_TIMESTAMP_MILLISECONDS
                or until_ms - started_ms > MAX_RATE_LIMIT_COOLDOWN_SECONDS * 1000
                or item.get("reason") != RATE_LIMIT_REASON
            ):
                raise ValueError("production allocator state schema is invalid")
            parsed.append(_Cooldown(slot_id, started_ms, until_ms))
            seen_slots.add(slot_id)
        cooldowns = tuple(
            sorted(parsed, key=lambda item: PRODUCTION_SLOT_IDS.index(item.slot_id))
        )
    return _AllocatorState(
        last_ordinal,
        last_slot_id,
        cooldowns,
        (current.st_dev, current.st_ino),
        (lock_device, lock_inode),
    )


def _commit_state(
    path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
    ordinal: int,
    last_slot_id: str,
    cooldowns: tuple[_Cooldown, ...],
    previous_identity: tuple[int, int] | None,
    lock_identity: tuple[int, int],
) -> None:
    encoded = (
        json.dumps(
            {
                "schema_version": 2,
                "pool_id": pool_id,
                "manifest_sha256": manifest_sha256,
                "last_ordinal": ordinal,
                "last_slot_id": last_slot_id,
                "cooldowns": [cooldown.state_payload() for cooldown in cooldowns],
                "lock_device": lock_identity[0],
                "lock_inode": lock_identity[1],
            },
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    try:
        parent = path.parent
        parent_stat = parent.stat()
    except OSError as error:
        raise ValueError("production allocator state directory is unavailable") from error
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise ValueError("production allocator state directory is invalid")
    descriptor, temp_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{path.name}.",
    )
    temp_path = Path(temp_name)
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise ValueError("production allocator state temp write failed")
            offset += written
        os.fsync(descriptor)
        temp_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(temp_stat.st_mode)
            or temp_stat.st_uid != os.getuid()
            or temp_stat.st_mode & 0o077
        ):
            raise ValueError(
                "production allocator state temp file must be owner-only regular file"
            )
        try:
            current = path.lstat()
        except FileNotFoundError:
            if previous_identity is not None:
                raise ValueError(
                    "production allocator state file changed during allocation"
                )
        except OSError as error:
            raise ValueError(
                "production allocator state file changed during allocation"
            ) from error
        else:
            _private_state_stat(path, minimum_size=2)
            if previous_identity is None or (
                current.st_dev,
                current.st_ino,
            ) != previous_identity:
                raise ValueError(
                    "production allocator state file changed during allocation"
                )
        os.replace(temp_path, path)
        directory_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        directory_flags |= getattr(os, "O_DIRECTORY", 0)
        directory_descriptor = os.open(parent, directory_flags)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        os.close(descriptor)
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


class ProductionAdmissionDenied(RuntimeError):
    """所有匿名 production slot cooling 時的封閉 admission 結果。"""

    def __init__(self, receipt: dict[str, object]) -> None:
        super().__init__("production provider admission is cooling")
        self.receipt = receipt


def _clock_milliseconds(clock: Callable[[], float] | None) -> int:
    value = (clock or time.time)()
    if (
        type(value) not in {int, float}
        or value < 0
        or value * 1000 > MAX_TIMESTAMP_MILLISECONDS
    ):
        raise ValueError("production allocator clock is invalid")
    return int(value * 1000)


@dataclass
class ProductionSlotAdmission:
    state_path: Path
    pool_id: str
    manifest_sha256: str
    now_ms: int
    slot_id: str | None
    cooldowns: tuple[_Cooldown, ...]
    state: _AllocatorState
    directory_descriptor: int
    lock_path: Path
    lock_descriptor: int
    lock_identity: tuple[int, int]
    committed: bool = False

    @property
    def allowed(self) -> bool:
        return self.slot_id is not None

    @property
    def receipt(self) -> dict[str, object]:
        if self.allowed:
            return {"slot_id": str(self.slot_id)}
        return {
            "reason": RATE_LIMIT_REASON,
            "cooldowns": [
                cooldown.receipt_payload() for cooldown in self.cooldowns
            ],
        }

    def commit(self) -> tuple[int, str]:
        if not self.allowed:
            raise ProductionAdmissionDenied(self.receipt)
        if self.committed:
            raise ValueError("production provider admission is already committed")
        if self.state.last_ordinal >= MAX_ALLOCATION_ORDINAL:
            raise ValueError("production allocator ordinal is exhausted")
        ordinal = self.state.last_ordinal + 1
        selected_slot = str(self.slot_id)
        _commit_state(
            self.state_path,
            pool_id=self.pool_id,
            manifest_sha256=self.manifest_sha256,
            ordinal=ordinal,
            last_slot_id=selected_slot,
            cooldowns=self.cooldowns,
            previous_identity=self.state.state_identity,
            lock_identity=self.lock_identity,
        )
        _assert_path_identity(
            self.lock_path,
            self.lock_descriptor,
            label="production allocator lock file",
        )
        _assert_directory_identity(
            self.state_path.parent,
            self.directory_descriptor,
        )
        self.committed = True
        return ordinal, selected_slot

    def record_rate_limit(
        self,
        slot_id: str,
        cooldown_seconds: int,
    ) -> dict[str, object]:
        if slot_id not in PRODUCTION_SLOT_IDS:
            raise ValueError("production cooldown slot is invalid")
        if (
            type(cooldown_seconds) is not int
            or not 1 <= cooldown_seconds <= MAX_RATE_LIMIT_COOLDOWN_SECONDS
            or self.now_ms + cooldown_seconds * 1000 > MAX_TIMESTAMP_MILLISECONDS
        ):
            raise ValueError("production cooldown duration is invalid")
        if self.committed:
            raise ValueError("production provider admission is already committed")
        if self.state.last_ordinal < 1 or self.state.last_slot_id is None:
            raise ValueError("production cooldown requires a committed attempt")
        cooldown = _Cooldown(
            slot_id,
            self.now_ms,
            self.now_ms + cooldown_seconds * 1000,
        )
        retained = tuple(item for item in self.cooldowns if item.slot_id != slot_id)
        updated = tuple(
            sorted(
                (*retained, cooldown),
                key=lambda item: PRODUCTION_SLOT_IDS.index(item.slot_id),
            )
        )
        _commit_state(
            self.state_path,
            pool_id=self.pool_id,
            manifest_sha256=self.manifest_sha256,
            ordinal=self.state.last_ordinal,
            last_slot_id=self.state.last_slot_id,
            cooldowns=updated,
            previous_identity=self.state.state_identity,
            lock_identity=self.lock_identity,
        )
        _assert_path_identity(
            self.lock_path,
            self.lock_descriptor,
            label="production allocator lock file",
        )
        _assert_directory_identity(
            self.state_path.parent,
            self.directory_descriptor,
        )
        self.committed = True
        receipt = cooldown.receipt_payload()
        receipt["reason"] = RATE_LIMIT_REASON
        return receipt


@contextmanager
def production_slot_admission(
    state_path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
    clock: Callable[[], float] | None = None,
) -> Iterator[ProductionSlotAdmission]:
    """鎖住 durable state，先判 eligibility，再由 caller 決定是否 commit ordinal。"""
    if not state_path.is_absolute():
        raise ValueError("production allocator state path must be absolute")
    now_ms = _clock_milliseconds(clock)
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    directory_descriptor = _open_allocator_directory(state_path.parent)
    try:
        fcntl.flock(directory_descriptor, fcntl.LOCK_EX)
        lock_descriptor = _open_allocator_lock(lock_path)
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
            lock_identity = _assert_path_identity(
                lock_path,
                lock_descriptor,
                label="production allocator lock file",
            )
            state = _read_state(
                state_path,
                pool_id=pool_id,
                manifest_sha256=manifest_sha256,
            )
            if (
                state.expected_lock_identity is not None
                and state.expected_lock_identity != lock_identity
            ):
                raise ValueError(
                    "production allocator lock file changed during allocation"
                )
            active_cooldowns = tuple(
                cooldown
                for cooldown in state.cooldowns
                if cooldown.cooldown_until_ms > now_ms
            )
            cooling_slots = {cooldown.slot_id for cooldown in active_cooldowns}
            start = (
                0
                if state.last_slot_id is None
                else (PRODUCTION_SLOT_IDS.index(state.last_slot_id) + 1)
                % len(PRODUCTION_SLOT_IDS)
            )
            selected_slot = next(
                (
                    PRODUCTION_SLOT_IDS[(start + offset) % len(PRODUCTION_SLOT_IDS)]
                    for offset in range(len(PRODUCTION_SLOT_IDS))
                    if PRODUCTION_SLOT_IDS[(start + offset) % len(PRODUCTION_SLOT_IDS)]
                    not in cooling_slots
                ),
                None,
            )
            admission = ProductionSlotAdmission(
                state_path=state_path,
                pool_id=pool_id,
                manifest_sha256=manifest_sha256,
                now_ms=now_ms,
                slot_id=selected_slot,
                cooldowns=active_cooldowns,
                state=state,
                directory_descriptor=directory_descriptor,
                lock_path=lock_path,
                lock_descriptor=lock_descriptor,
                lock_identity=lock_identity,
            )
            yield admission
            _assert_path_identity(
                lock_path,
                lock_descriptor,
                label="production allocator lock file",
            )
            _assert_directory_identity(state_path.parent, directory_descriptor)
        finally:
            fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
            os.close(lock_descriptor)
    finally:
        fcntl.flock(directory_descriptor, fcntl.LOCK_UN)
        os.close(directory_descriptor)


def allocate_production_slot(
    state_path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
    clock: Callable[[], float] | None = None,
) -> tuple[int, str]:
    """Durable commit 下一個 eligible slot 的 ordinal。"""
    with production_slot_admission(
        state_path,
        pool_id=pool_id,
        manifest_sha256=manifest_sha256,
        clock=clock,
    ) as admission:
        return admission.commit()


def record_production_rate_limit(
    state_path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
    slot_id: str,
    cooldown_seconds: int,
    clock: Callable[[], float] | None = None,
) -> dict[str, object]:
    """只以 closed API_RATE_LIMITED reason 寫入匿名 slot cooldown。"""
    with production_slot_admission(
        state_path,
        pool_id=pool_id,
        manifest_sha256=manifest_sha256,
        clock=clock,
    ) as admission:
        return admission.record_rate_limit(slot_id, cooldown_seconds)


def validate_production_allocator_installation(
    state_path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
) -> None:
    """只驗 allocator metadata 與 identity，不建立 state/lock。"""
    if not state_path.is_absolute():
        raise ValueError("production allocator state path must be absolute")
    directory_descriptor = _open_allocator_directory(state_path.parent)
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    state_exists = state_path.exists() or state_path.is_symlink()
    lock_exists = lock_path.exists() or lock_path.is_symlink()
    try:
        if state_exists and not lock_exists:
            raise ValueError("production allocator lock file is unavailable")
        if not lock_exists:
            return
        lock_descriptor = _open_existing_allocator_lock(lock_path)
        try:
            lock_identity = _assert_path_identity(
                lock_path,
                lock_descriptor,
                label="production allocator lock file",
            )
            if state_exists:
                state = _read_state(
                    state_path,
                    pool_id=pool_id,
                    manifest_sha256=manifest_sha256,
                )
                if state.expected_lock_identity != lock_identity:
                    raise ValueError(
                        "production allocator lock file changed during allocation"
                    )
            _assert_directory_identity(state_path.parent, directory_descriptor)
        finally:
            os.close(lock_descriptor)
    finally:
        os.close(directory_descriptor)

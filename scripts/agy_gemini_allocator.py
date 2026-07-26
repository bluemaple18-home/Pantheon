#!/usr/bin/env python3
"""Production Gemini credential pool 的 durable strict round-robin allocator。"""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import tempfile
from pathlib import Path


MAX_ALLOCATOR_STATE_BYTES = 4 * 1024
MAX_ALLOCATION_ORDINAL = (1 << 63) - 1
SAFE_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SAFE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PRODUCTION_SLOT_IDS = ("account-1", "account-2", "account-3")


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
) -> tuple[int, tuple[int, int] | None, tuple[int, int] | None]:
    try:
        path.lstat()
    except FileNotFoundError:
        return 0, None, None
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
    if not isinstance(payload, dict) or set(payload) != {
        "last_ordinal",
        "lock_device",
        "lock_inode",
        "manifest_sha256",
        "pool_id",
        "schema_version",
    }:
        raise ValueError("production allocator state schema is invalid")
    last_ordinal = payload.get("last_ordinal")
    lock_device = payload.get("lock_device")
    lock_inode = payload.get("lock_inode")
    if (
        type(payload.get("schema_version")) is not int
        or payload.get("schema_version") != 1
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
    return (
        last_ordinal,
        (current.st_dev, current.st_ino),
        (lock_device, lock_inode),
    )


def _commit_state(
    path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
    ordinal: int,
    previous_identity: tuple[int, int] | None,
    lock_identity: tuple[int, int],
) -> None:
    encoded = (
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": pool_id,
                "manifest_sha256": manifest_sha256,
                "last_ordinal": ordinal,
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


def allocate_production_slot(
    state_path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
) -> tuple[int, str]:
    """Durable commit 下一個 ordinal，並回傳固定三槽中的 selected slot。"""
    if not state_path.is_absolute():
        raise ValueError("production allocator state path must be absolute")
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
            last_ordinal, previous_identity, expected_lock_identity = _read_state(
                state_path,
                pool_id=pool_id,
                manifest_sha256=manifest_sha256,
            )
            if (
                expected_lock_identity is not None
                and expected_lock_identity != lock_identity
            ):
                raise ValueError(
                    "production allocator lock file changed during allocation"
                )
            if last_ordinal >= MAX_ALLOCATION_ORDINAL:
                raise ValueError("production allocator ordinal is exhausted")
            ordinal = last_ordinal + 1
            _commit_state(
                state_path,
                pool_id=pool_id,
                manifest_sha256=manifest_sha256,
                ordinal=ordinal,
                previous_identity=previous_identity,
                lock_identity=lock_identity,
            )
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
    return ordinal, PRODUCTION_SLOT_IDS[(ordinal - 1) % len(PRODUCTION_SLOT_IDS)]


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
                _last_ordinal, _state_identity, expected_lock_identity = _read_state(
                    state_path,
                    pool_id=pool_id,
                    manifest_sha256=manifest_sha256,
                )
                if expected_lock_identity != lock_identity:
                    raise ValueError(
                        "production allocator lock file changed during allocation"
                    )
            _assert_directory_identity(state_path.parent, directory_descriptor)
        finally:
            os.close(lock_descriptor)
    finally:
        os.close(directory_descriptor)

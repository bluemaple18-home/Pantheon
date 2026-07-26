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


def _read_state(
    path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
) -> tuple[int, tuple[int, int] | None]:
    try:
        path.lstat()
    except FileNotFoundError:
        return 0, None
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
        "manifest_sha256",
        "pool_id",
        "schema_version",
    }:
        raise ValueError("production allocator state schema is invalid")
    last_ordinal = payload.get("last_ordinal")
    if (
        type(payload.get("schema_version")) is not int
        or payload.get("schema_version") != 1
        or type(payload.get("pool_id")) is not str
        or SAFE_CREDENTIAL_ID.fullmatch(payload["pool_id"]) is None
        or type(payload.get("manifest_sha256")) is not str
        or SAFE_SHA256.fullmatch(payload["manifest_sha256"]) is None
        or type(last_ordinal) is not int
        or not 1 <= last_ordinal <= MAX_ALLOCATION_ORDINAL
    ):
        raise ValueError("production allocator state schema is invalid")
    if payload["pool_id"] != pool_id:
        raise ValueError("production allocator state pool mismatch")
    if payload["manifest_sha256"] != manifest_sha256:
        raise ValueError("production allocator state manifest mismatch")
    return last_ordinal, (current.st_dev, current.st_ino)


def _commit_state(
    path: Path,
    *,
    pool_id: str,
    manifest_sha256: str,
    ordinal: int,
    previous_identity: tuple[int, int] | None,
) -> None:
    encoded = (
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": pool_id,
                "manifest_sha256": manifest_sha256,
                "last_ordinal": ordinal,
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
    lock_descriptor = _open_allocator_lock(lock_path)
    try:
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
        last_ordinal, previous_identity = _read_state(
            state_path,
            pool_id=pool_id,
            manifest_sha256=manifest_sha256,
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
        )
    finally:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        os.close(lock_descriptor)
    return ordinal, PRODUCTION_SLOT_IDS[(ordinal - 1) % len(PRODUCTION_SLOT_IDS)]

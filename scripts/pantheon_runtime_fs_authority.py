#!/usr/bin/env python3
"""以可信 directory fd 執行 sandbox 相對 filesystem I/O。"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import errno
import os
from pathlib import Path
import stat
from typing import Any, Callable


class FilesystemAuthorityError(ValueError):
    """filesystem authority 驗證失敗，呼叫端必須 fail-closed。"""


@dataclass(frozen=True)
class DirectoryIdentity:
    """固定 directory 的 device/inode identity。"""

    device: int
    inode: int

    @classmethod
    def from_stat(cls, stat_result: os.stat_result) -> DirectoryIdentity:
        return cls(device=stat_result.st_dev, inode=stat_result.st_ino)

    def as_dict(self) -> dict[str, int]:
        return {"device": self.device, "inode": self.inode}


def path_identity(path: Path) -> dict[str, int | str] | None:
    try:
        result = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISDIR(result.st_mode):
        kind = "directory"
    elif stat.S_ISREG(result.st_mode):
        kind = "file"
    elif stat.S_ISLNK(result.st_mode):
        kind = "symlink"
    else:
        kind = "other"
    return {
        "device": result.st_dev,
        "inode": result.st_ino,
        "mode": stat.S_IMODE(result.st_mode),
        "kind": kind,
    }


class OperationTraceRecorder:
    """由實際允許的 filesystem/Git operation 產生 mutation trace。"""

    def __init__(
        self,
        *,
        anchor_root: Path,
        anchor_identity: DirectoryIdentity,
        correlation_id: str,
        runtime_identity_digest: str,
    ) -> None:
        self.anchor_root = Path(anchor_root)
        self.anchor_identity = anchor_identity
        self.correlation_id = correlation_id
        self.runtime_identity_digest = runtime_identity_digest
        self._events: list[dict[str, Any]] = []

    def record_path_operation(
        self,
        operation: str,
        target: Path,
        mutation: Callable[[], Any],
    ) -> Any:
        relative_target = self._relative_target(target)
        pre_identity = path_identity(target)
        try:
            result = mutation()
        except Exception:
            post_identity = path_identity(target)
            self._append_event(
                operation,
                relative_target,
                pre_identity,
                post_identity,
                "BLOCKED",
            )
            raise
        post_identity = path_identity(target)
        self._append_event(
            operation,
            relative_target,
            pre_identity,
            post_identity,
            "PASS",
        )
        return result

    def events(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps(self._events, sort_keys=True))

    def digest(self) -> str:
        encoded = json.dumps(
            self._events,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _append_event(
        self,
        operation: str,
        relative_target: str,
        pre_identity: dict[str, int | str] | None,
        post_identity: dict[str, int | str] | None,
        result: str,
    ) -> None:
        self._events.append(
            {
                "operation": operation,
                "relative_target": relative_target,
                "anchor_identity": self.anchor_identity.as_dict(),
                "pre_identity": pre_identity,
                "post_identity": post_identity,
                "result": result,
                "correlation_id": self.correlation_id,
                "runtime_identity_digest": self.runtime_identity_digest,
            }
        )

    def _relative_target(self, target: Path) -> str:
        path = Path(target)
        if not path.is_absolute():
            path = self.anchor_root / path
        try:
            relative = path.relative_to(self.anchor_root)
        except ValueError as error:
            raise FilesystemAuthorityError(
                "operation trace target escaped sandbox"
            ) from error
        if not relative.parts:
            raise FilesystemAuthorityError("operation trace target is anchor")
        if any(part in {"", ".", ".."} for part in relative.parts):
            raise FilesystemAuthorityError(
                "operation trace target has unsafe component"
            )
        return relative.as_posix()


def summarize_operation_trace(events: list[dict[str, Any]]) -> dict[str, bool]:
    sandbox_mutation = False
    production_mutation = False
    for event in events:
        relative_target = event.get("relative_target")
        if (
            type(relative_target) is not str
            or not relative_target
            or relative_target.startswith("/")
            or any(part in {"", ".", ".."} for part in relative_target.split("/"))
        ):
            production_mutation = True
        if (
            event.get("result") == "PASS"
            and event.get("pre_identity") != event.get("post_identity")
        ):
            sandbox_mutation = True
    return {
        "sandbox_mutation": sandbox_mutation,
        "production_mutation": production_mutation,
    }


class TrustedSandboxDirectoryAuthority:
    """持有 sandbox root fd，後續 I/O 只接受相對 component。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._fd: int | None = None
        flags = os.O_RDONLY
        flags |= getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            self._fd = os.open(self.root, flags)
            fd_stat = os.fstat(self._fd)
        except OSError as error:
            self.close()
            raise FilesystemAuthorityError("sandbox authority cannot be opened") from error
        if not stat.S_ISDIR(fd_stat.st_mode):
            self.close()
            raise FilesystemAuthorityError("sandbox authority is not a directory")
        self.identity = DirectoryIdentity.from_stat(fd_stat)
        self.assert_current()

    def __enter__(self) -> TrustedSandboxDirectoryAuthority:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._fd is None:
            return
        os.close(self._fd)
        self._fd = None

    @property
    def fd(self) -> int:
        if self._fd is None:
            raise FilesystemAuthorityError("sandbox authority is closed")
        return self._fd

    def assert_current(self) -> None:
        try:
            path_stat = os.lstat(self.root)
            fd_stat = os.fstat(self.fd)
        except OSError as error:
            raise FilesystemAuthorityError("sandbox authority identity is unreadable") from error
        if stat.S_ISLNK(path_stat.st_mode):
            raise FilesystemAuthorityError("sandbox authority path became symlink")
        path_identity = DirectoryIdentity.from_stat(path_stat)
        fd_identity = DirectoryIdentity.from_stat(fd_stat)
        if path_identity != self.identity or fd_identity != self.identity:
            raise FilesystemAuthorityError("sandbox authority identity drift")

    def exists(self, relative: os.PathLike[str] | str) -> bool:
        parts = self._relative_parts(relative)
        self.assert_current()
        parent_fd = os.dup(self.fd)
        try:
            for index, segment in enumerate(parts):
                is_leaf = index == len(parts) - 1
                if is_leaf:
                    try:
                        target_stat = os.stat(
                            segment,
                            dir_fd=parent_fd,
                            follow_symlinks=False,
                        )
                    except FileNotFoundError:
                        return False
                    except OSError as error:
                        raise FilesystemAuthorityError(
                            "sandbox relative target is unreadable"
                        ) from error
                    if stat.S_ISLNK(target_stat.st_mode):
                        raise FilesystemAuthorityError(
                            "sandbox relative component is a symlink"
                        )
                    return True
                try:
                    child_fd = self._open_directory_at(parent_fd, segment)
                except FileNotFoundError:
                    return False
                os.close(parent_fd)
                parent_fd = child_fd
            return True
        finally:
            os.close(parent_fd)
            self.assert_current()

    def makedirs(
        self,
        relative: os.PathLike[str] | str,
        *,
        mode: int = 0o700,
    ) -> None:
        parts = self._relative_parts(relative)
        self.assert_current()
        parent_fd = os.dup(self.fd)
        try:
            for segment in parts:
                try:
                    os.mkdir(segment, mode=mode, dir_fd=parent_fd)
                except FileExistsError:
                    pass
                except OSError as error:
                    raise FilesystemAuthorityError(
                        "sandbox relative directory cannot be created"
                    ) from error
                child_fd = self._open_directory_at(parent_fd, segment)
                os.close(parent_fd)
                parent_fd = child_fd
        finally:
            os.close(parent_fd)
            self.assert_current()

    def _open_directory_at(self, parent_fd: int, segment: str) -> int:
        flags = os.O_RDONLY
        flags |= getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            child_fd = os.open(segment, flags, dir_fd=parent_fd)
        except FileNotFoundError:
            raise
        except NotADirectoryError as error:
            raise FilesystemAuthorityError(
                "sandbox relative parent is not a directory"
            ) from error
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise FilesystemAuthorityError(
                    "sandbox relative component is a symlink"
                ) from error
            raise FilesystemAuthorityError(
                "sandbox relative directory cannot be opened"
            ) from error
        child_stat = os.fstat(child_fd)
        if not stat.S_ISDIR(child_stat.st_mode):
            os.close(child_fd)
            raise FilesystemAuthorityError(
                "sandbox relative component is not a directory"
            )
        return child_fd

    @staticmethod
    def _relative_parts(relative: os.PathLike[str] | str) -> tuple[str, ...]:
        raw = os.fspath(relative)
        path = Path(raw)
        parts = path.parts
        if path.is_absolute() or not parts:
            raise FilesystemAuthorityError("sandbox target must be relative")
        if any(part in {"", ".", ".."} for part in parts):
            raise FilesystemAuthorityError("sandbox target has unsafe component")
        return tuple(parts)

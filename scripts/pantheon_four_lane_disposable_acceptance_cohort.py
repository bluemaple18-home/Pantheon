#!/usr/bin/env python3
"""渲染並驗證一次性、可完全 teardown 的四軌 acceptance cohort。"""
from __future__ import annotations

from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import plistlib
import pwd
import re
import stat
import subprocess
import time
from typing import Any, Callable, Iterable, Mapping

from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import pantheon_content_runtime_manifest as runtime

LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")
PUBLISHER = "com.pantheon.agy-content-publisher"
COORDINATOR = "com.pantheon.agy-gemini-coordinator"
CAPACITY = "com.pantheon.content-capacity-guard"
SERVICE_LABELS = runtime.SERVICE_LABELS
PRODUCTION_ROOT_KEYS = frozenset(("queue", "ledger", "publisher", "public"))
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ACCEPTED_PARENT_SHA = "836d5f0d1d62b58ad886aa37863c15ce41d233ec"
SOURCE_LANES = ("new", "rewrite")
TRANSLATION_LANES = ("i18n-new", "i18n-rewrite")
LAUNCHCTL = "/bin/launchctl"


def _os_uid_home() -> Path:
    """以 OS account database 為 HOME authority，不信任 caller environment。"""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


PRODUCTION_LAUNCH_PLIST_ROOT = _os_uid_home() / "Library/LaunchAgents"
PRODUCTION_ARTICLE_REGISTRY_RELATIVE_PATH = Path("app/web/static/article-registry.js")
READINESS_TIMEOUT_SECONDS = max(7, len(SERVICE_LABELS))
TEARDOWN_ATTEMPTS = 3
PLAN_FIELDS = {
    "schema_version", "accepted_parent_sha", "actor_sha", "session_id",
    "session_nonce_digest", "generation", "manifest_path", "manifest_digest",
    "runtime_identity_digest", "service_labels", "plist_paths", "ready_root",
    "barrier", "lock", "evidence_root", "consumed_marker", "roots",
    "exact_runs", "publisher_activation_run_id", "dependency_graph", "c_b_materializations",
    "bundle_closeouts", "phase_schedule", "publisher_plan_only",
    "budgets", "teardown", "production_fingerprint_contract",
}


class AcceptanceBlocked(ValueError):
    """disposable acceptance 契約不成立。"""


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


@dataclass
class RetainedDirectory:
    """單一 run_once 內 retained directory fd 與首次 identity。"""

    path: Path
    descriptor: int
    device: int
    inode: int
    parent: RetainedDirectory | None = None
    entry_name: str | None = None

    @classmethod
    def open_absolute(cls, path: Path, label: str) -> RetainedDirectory:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
            info = os.fstat(descriptor)
        except OSError as error:
            raise AcceptanceBlocked(f"{label} authority cannot be opened") from error
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            os.close(descriptor)
            raise AcceptanceBlocked(f"{label} authority is not owner-safe")
        value = cls(path, descriptor, info.st_dev, info.st_ino)
        value.verify(label)
        return value

    def open_directory(self, name: str, label: str) -> RetainedDirectory:
        self.verify(label)
        if not name or "/" in name or name in {".", ".."}:
            raise AcceptanceBlocked(f"{label} authority name differs")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(name, flags, dir_fd=self.descriptor)
            info = os.fstat(descriptor)
        except OSError as error:
            raise AcceptanceBlocked(f"{label} authority cannot be opened") from error
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            os.close(descriptor)
            raise AcceptanceBlocked(f"{label} authority is not owner-safe")
        value = RetainedDirectory(self.path / name, descriptor, info.st_dev, info.st_ino, self, name)
        value.verify(label)
        return value

    def verify(self, label: str) -> None:
        try:
            current = os.fstat(self.descriptor)
            visible = (
                os.stat(self.entry_name, dir_fd=self.parent.descriptor, follow_symlinks=False)
                if self.parent is not None and self.entry_name is not None
                else os.lstat(self.path)
            )
        except OSError as error:
            raise AcceptanceBlocked(f"{label} authority drift") from error
        if (
            not stat.S_ISDIR(current.st_mode)
            or not stat.S_ISDIR(visible.st_mode)
            or _identity(current) != (self.device, self.inode)
            or _identity(visible) != (self.device, self.inode)
        ):
            raise AcceptanceBlocked(f"{label} authority drift")
        if self.parent is not None:
            self.parent.verify(label)

    def close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1


@dataclass
class RetainedFile:
    """只從 pinned parent fd 開啟，後續 digest/read-back 不重開 path。"""

    parent: RetainedDirectory
    name: str
    path: Path
    descriptor: int
    device: int
    inode: int
    digest: str
    immutable: bool

    @classmethod
    def open(cls, parent: RetainedDirectory, name: str, label: str, *, writable: bool = False) -> RetainedFile:
        parent.verify(label)
        flags = (os.O_RDWR if writable else os.O_RDONLY) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(name, flags, dir_fd=parent.descriptor)
            info = os.fstat(descriptor)
        except OSError as error:
            raise AcceptanceBlocked(f"{label} authority cannot be opened") from error
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            os.close(descriptor)
            raise AcceptanceBlocked(f"{label} authority is not owner-safe")
        return cls.adopt(parent, name, descriptor, label, immutable=not writable)

    @classmethod
    def adopt(
        cls,
        parent: RetainedDirectory,
        name: str,
        descriptor: int,
        label: str,
        *,
        immutable: bool,
    ) -> RetainedFile:
        """直接接管 create fd，禁止 create→close→path reopen。"""
        try:
            info = os.fstat(descriptor)
        except OSError as error:
            os.close(descriptor)
            raise AcceptanceBlocked(f"{label} authority cannot be adopted") from error
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            os.close(descriptor)
            raise AcceptanceBlocked(f"{label} authority is not owner-safe")
        digest = hashlib.sha256(_read_descriptor(descriptor)).hexdigest()
        value = cls(parent, name, parent.path / name, descriptor, info.st_dev, info.st_ino, digest, immutable)
        value.verify(label)
        return value

    def verify(self, label: str) -> None:
        self.parent.verify(label)
        try:
            visible = os.stat(self.name, dir_fd=self.parent.descriptor, follow_symlinks=False)
            current = os.fstat(self.descriptor)
        except OSError as error:
            raise AcceptanceBlocked(f"{label} authority drift") from error
        if (
            not stat.S_ISREG(visible.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or _identity(visible) != (self.device, self.inode)
            or _identity(current) != (self.device, self.inode)
        ):
            raise AcceptanceBlocked(f"{label} authority drift")
        if self.immutable and hashlib.sha256(_read_descriptor(self.descriptor)).hexdigest() != self.digest:
            raise AcceptanceBlocked(f"{label} pinned digest drift")

    def read(self, label: str) -> bytes:
        self.verify(label)
        return _read_descriptor(self.descriptor)

    def content_digest(self, label: str) -> str:
        self.verify(label)
        return hashlib.sha256(_read_descriptor(self.descriptor)).hexdigest()

    def close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1


@dataclass
class LoadedAuthority:
    label: str
    artifact: RetainedFile
    kind: str
    attempts: list[str] = field(default_factory=list)


class ContinuousAuthority:
    """run_once 唯一 transient authority aggregate；不跨執行持久化。"""

    def __init__(self, rendered: Mapping[str, Any]) -> None:
        self.rendered = rendered
        self.directories: list[RetainedDirectory] = []
        self.files: list[RetainedFile] = []
        self.loaded: dict[str, LoadedAuthority] = {}
        self.drift_evidence: list[dict[str, Any]] = []
        root = self._directory_absolute(Path(rendered["acceptance_root"]), "acceptance root")
        self.acceptance_root = root
        self.plists = self._directory(root, "plists", "plist parent")
        self.generation = self._directory(self.plists, str(rendered["session_plan"]["generation"]), "plist generation")
        self.baseline: dict[str, RetainedFile] = {}
        self.baseline_outputs: dict[str, tuple[RetainedFile, RetainedFile]] = {}
        expected = {f"{label}.plist" for label in SERVICE_LABELS}
        if {Path(path).name for path in rendered["plist_paths"]} != expected:
            raise AcceptanceBlocked("baseline plist set differs")
        for label in SERVICE_LABELS:
            self.baseline[label] = self._file(self.generation, f"{label}.plist", "baseline plist")
            self.baseline_outputs[label] = (
                self._create_empty(self.generation, f"{label}.stdout.json", "baseline stdout"),
                self._create_empty(self.generation, f"{label}.stderr.log", "baseline stderr"),
            )
        try:
            os.mkdir("steps", 0o700, dir_fd=self.generation.descriptor)
        except OSError as error:
            raise AcceptanceBlocked("step authority cannot be created") from error
        self.steps = self._directory(self.generation, "steps", "step directory")
        self.production_home = self._directory_absolute(_os_uid_home(), "production uid home")
        self.production_library = self._directory(self.production_home, "Library", "production Library")
        self.production_launch_agents = self._directory(self.production_library, "LaunchAgents", "production LaunchAgents")
        if self.production_launch_agents.path != PRODUCTION_LAUNCH_PLIST_ROOT:
            raise AcceptanceBlocked("production LaunchAgents authority differs")
        self.production_plists = {
            label: self._file(self.production_launch_agents, f"{label}.plist", "production launch plist")
            for label in SERVICE_LABELS
        }

    def __enter__(self) -> ContinuousAuthority:
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        for item in reversed(self.files):
            item.close()
        for item in reversed(self.directories):
            item.close()

    def _directory_absolute(self, path: Path, label: str) -> RetainedDirectory:
        value = RetainedDirectory.open_absolute(path, label)
        self.directories.append(value)
        return value

    def _directory(self, parent: RetainedDirectory, name: str, label: str) -> RetainedDirectory:
        value = parent.open_directory(name, label)
        self.directories.append(value)
        return value

    def _file(self, parent: RetainedDirectory, name: str, label: str, *, writable: bool = False) -> RetainedFile:
        value = RetainedFile.open(parent, name, label, writable=writable)
        self.files.append(value)
        return value

    def _create_empty(self, parent: RetainedDirectory, name: str, label: str) -> RetainedFile:
        parent.verify(label)
        descriptor = -1
        try:
            descriptor = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent.descriptor)
            os.fsync(descriptor)
        except OSError as error:
            if descriptor >= 0:
                os.close(descriptor)
            raise AcceptanceBlocked(f"{label} authority cannot be created") from error
        value = RetainedFile.adopt(parent, name, descriptor, label, immutable=False)
        self.files.append(value)
        return value

    def verify_baseline(self) -> None:
        self.generation.verify("plist generation")
        for label in SERVICE_LABELS:
            self.baseline[label].verify("baseline plist")
            for output in self.baseline_outputs[label]:
                output.verify("baseline output")

    def create_step(self, index: int, label: str, command: list[str]) -> tuple[RetainedFile, RetainedFile, RetainedFile]:
        self.verify_baseline()
        stem = f"{index:02d}-{label}"
        stdout = self._create_empty(self.steps, f"{stem}.stdout.json", "step stdout")
        stderr = self._create_empty(self.steps, f"{stem}.stderr.log", "step stderr")
        payload = {
            "Label": label,
            "ProgramArguments": [
                *_prefix(str(self.rendered["manifest"].get("python_executable") or os.sys.executable), self.rendered["manifest"], label, Path(self.rendered["barrier"]), Path(self.rendered["ready_root"]), False),
                "--",
                *command,
            ],
            "EnvironmentVariables": _env(self.rendered["manifest"], label, Path(self.rendered["barrier"])),
            "WorkingDirectory": str(self.rendered["manifest"]["actor_root"]),
            "RunAtLoad": False,
            "StandardOutPath": str(stdout.path),
            "StandardErrorPath": str(stderr.path),
        }
        data = plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)
        name = f"{stem}.plist"
        descriptor = -1
        try:
            descriptor = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=self.steps.descriptor)
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view):]
            os.fsync(descriptor)
        except OSError as error:
            if descriptor >= 0:
                os.close(descriptor)
            raise AcceptanceBlocked("step plist authority cannot be created") from error
        plist = RetainedFile.adopt(self.steps, name, descriptor, "step plist", immutable=True)
        self.files.append(plist)
        return plist, stdout, stderr

    def claim_loaded(self, label: str, artifact: RetainedFile, kind: str) -> None:
        """bootstrap 0 後的不可失敗 ownership transition；禁止任何 verify。"""
        self.loaded[label] = LoadedAuthority(label, artifact, kind)

    def _record_drift(self, owned: LoadedAuthority, message: str) -> dict[str, Any]:
        for evidence in self.drift_evidence:
            if evidence["label"] == owned.label and evidence["device"] == owned.artifact.device and evidence["inode"] == owned.artifact.inode:
                evidence["message"] = message
                return evidence
        evidence = {
            "label": owned.label,
            "kind": owned.kind,
            "device": owned.artifact.device,
            "inode": owned.artifact.inode,
            "captured_digest": owned.artifact.digest,
            "message": message,
            "teardown_attempts": [],
            "terminal_not_found": False,
        }
        self.drift_evidence.append(evidence)
        return evidence

    def release(self, label: str, *, attempts: int) -> dict[str, Any] | None:
        owned = self.loaded.get(label)
        if owned is None:
            return None
        manifest = self.rendered["manifest"]
        command = [LAUNCHCTL, "bootout", f"gui/{os.getuid()}/{label}"]
        for _index in range(attempts):
            drift = ""
            drift_evidence: dict[str, Any] | None = None
            try:
                owned.artifact.verify(f"{owned.kind} plist")
            except AcceptanceBlocked as error:
                drift = f"authority:{error};"
                drift_evidence = self._record_drift(owned, str(error))
            completed = _run_process(command)
            try:
                owned.artifact.verify(f"{owned.kind} plist")
            except AcceptanceBlocked as error:
                drift = f"{drift}post-bootout-authority:{error};"
                drift_evidence = self._record_drift(owned, str(error))
            if completed.returncode != 0:
                owned.attempts.append(f"{drift}bootout:{completed.returncode}:{completed.stderr.strip()}")
                if drift_evidence is not None:
                    drift_evidence["teardown_attempts"] = list(owned.attempts)
                continue
            printed = _run_process([LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"])
            try:
                owned.artifact.verify(f"{owned.kind} plist")
            except AcceptanceBlocked as error:
                drift = f"{drift}post-print-authority:{error};"
                drift_evidence = self._record_drift(owned, str(error))
            if printed.returncode == 113:
                owned.attempts.append(f"{drift}bootout:0;print:113")
                if drift_evidence is not None:
                    drift_evidence["teardown_attempts"] = list(owned.attempts)
                    drift_evidence["terminal_not_found"] = True
                receipt = _bootout_expectation(label, owned.artifact.path, manifest, owned.artifact.digest)
                del self.loaded[label]
                return receipt
            owned.attempts.append(f"{drift}bootout:0;print:{printed.returncode}:{printed.stdout.strip()}:{printed.stderr.strip()}")
            if drift_evidence is not None:
                drift_evidence["teardown_attempts"] = list(owned.attempts)
        return None

    def loaded_evidence(self) -> str:
        return ";".join(
            f"{label}[dev={item.artifact.device},ino={item.artifact.inode}]:{'|'.join(item.attempts)}"
            for label, item in sorted(self.loaded.items())
        )

    def cleanup_generation(self) -> bool:
        if self.loaded:
            return False
        try:
            self.verify_baseline()
            self.steps.verify("step directory")
            generation_name = str(self.rendered["session_plan"]["generation"])
            quarantine = f".continuous-cleanup-{os.urandom(16).hex()}"
            os.rename(generation_name, quarantine, src_dir_fd=self.plists.descriptor, dst_dir_fd=self.plists.descriptor)
            visible = os.stat(quarantine, dir_fd=self.plists.descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(visible.st_mode) or _identity(visible) != (self.generation.device, self.generation.inode):
                if not os.path.lexists(self.plists.path / generation_name):
                    os.rename(quarantine, generation_name, src_dir_fd=self.plists.descriptor, dst_dir_fd=self.plists.descriptor)
                return False
            self.generation.entry_name = quarantine
            self.generation.path = self.plists.path / quarantine
            for name in os.listdir(self.steps.descriptor):
                os.unlink(name, dir_fd=self.steps.descriptor)
            os.rmdir("steps", dir_fd=self.generation.descriptor)
            for label in SERVICE_LABELS:
                for name in (f"{label}.stdout.json", f"{label}.stderr.log", f"{label}.plist"):
                    os.unlink(name, dir_fd=self.generation.descriptor)
            os.rmdir(quarantine, dir_fd=self.plists.descriptor)
            return not os.path.lexists(self.plists.path / generation_name)
        except OSError:
            return False


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_dir(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        raise AcceptanceBlocked(f"{label} must be an absolute canonical directory")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise AcceptanceBlocked(f"{label} must use canonical realpath")
    mode = stat.S_IMODE(path.stat().st_mode)
    if path.stat().st_uid != os.getuid() or mode & 0o022:
        raise AcceptanceBlocked(f"{label} is not owner-safe")
    return resolved


def _canonical_file(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
        raise AcceptanceBlocked(f"{label} must be an absolute canonical regular file")
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o022:
        raise AcceptanceBlocked(f"{label} is not owner-safe")
    return path


def _descendant(path: Path, root: Path, label: str) -> Path:
    resolved = _canonical_dir(path, label)
    if resolved == root or not resolved.is_relative_to(root):
        raise AcceptanceBlocked(f"{label} must be a strict acceptance descendant")
    return resolved


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _write_plist(path: Path, payload: dict[str, Any]) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        data = plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        view = memoryview(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            + b"\n"
        )
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _tree_digest(root: Path) -> str:
    """非 follow lstat snapshot；涵蓋空目錄、metadata 與 symlink target。"""
    root = _canonical_dir(root, "production root")
    rows: list[dict[str, Any]] = []
    for path in [root, *sorted(root.rglob("*"))]:
        info = os.lstat(path)
        mode = stat.S_IFMT(info.st_mode)
        kind = "dir" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "symlink" if stat.S_ISLNK(info.st_mode) else "other"
        if kind == "other":
            raise AcceptanceBlocked("production fingerprint contains unsupported entry")
        row: dict[str, Any] = {"path": "." if path == root else str(path.relative_to(root)), "type": kind, "uid": info.st_uid, "gid": info.st_gid, "mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns, "size": info.st_size}
        if kind == "file": row["sha256"] = _sha(path)
        if kind == "symlink": row["target"] = os.readlink(path)
        rows.append(row)
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _bundle_required_entries(
    bundle: Path,
    *,
    expected_bundle_digest: str | None = None,
    queue_root: Path | None = None,
    lane: str | None = None,
    run_id: str | None = None,
    generation: str | None = None,
) -> list[str]:
    try:
        payload = json.loads(bundle.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AcceptanceBlocked("sealed bundle authority is invalid") from error
    if expected_bundle_digest is not None and _sha(bundle) != expected_bundle_digest:
        raise AcceptanceBlocked("sealed bundle authority digest differs")
    if not isinstance(payload, dict) or set(payload) != runner.ACCEPTANCE_SEALED_REPLAY_BUNDLE_FIELDS:
        raise AcceptanceBlocked("sealed bundle authority schema differs")
    body = {key: value for key, value in payload.items() if key != "bundle_digest"}
    if payload.get("bundle_digest") != _stable_digest(body):
        raise AcceptanceBlocked("sealed bundle authority digest differs")
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise AcceptanceBlocked("sealed bundle required entries differ")
    try:
        entries = [
            runner._load_acceptance_sealed_replay_entry(entry)
            for entry in raw_entries
            if isinstance(entry, dict)
        ]
    except ValueError as error:
        raise AcceptanceBlocked("sealed bundle authority entry differs") from error
    if len(entries) != len(raw_entries):
        raise AcceptanceBlocked("sealed bundle authority entry differs")
    required_entries = [entry.entry_id for entry in entries if entry.required]
    entry_keys = [
        (
            entry.session_id,
            entry.entry_id,
            entry.namespace,
            entry.job_id,
            entry.request_sha256,
            entry.lane,
            entry.run_id,
            entry.role,
            entry.model,
            entry.schema_sha256,
            entry.sealed_result_sha256,
        )
        for entry in entries
    ]
    expected_queue = str(queue_root.resolve()) if queue_root is not None else None
    if (
        payload.get("schema_version") != 1
        or payload.get("mode") != runner.ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE
        or (queue_root is not None and payload.get("queue_root") != expected_queue)
        or (lane is not None and payload.get("lane") != lane)
        or (run_id is not None and payload.get("run_id") != run_id)
        or (generation is not None and payload.get("generation") != generation)
        or (
            isinstance(payload.get("run_id"), str)
            and payload.get("namespace") != runner._expected_namespace_for_run_id(str(payload["run_id"]))
        )
        or len(entry_keys) != len(set(entry_keys))
        or len(required_entries) != len(set(required_entries))
        or not required_entries
        or any(
            entry.session_id != payload.get("session_id")
            or entry.namespace != payload.get("namespace")
            or entry.lane != payload.get("lane")
            or entry.run_id != payload.get("run_id")
            for entry in entries
        )
    ):
        raise AcceptanceBlocked("sealed bundle required entries differ")
    provider_budget = payload.get("provider_call_budget")
    if (
        type(provider_budget) is not int
        or type(provider_budget) is bool
        or not len(required_entries) <= provider_budget <= len(entries)
    ):
        raise AcceptanceBlocked("sealed bundle required entries differ")
    return required_entries


def _bundle_authority_digest(bundle: Path) -> str:
    try:
        payload = json.loads(bundle.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AcceptanceBlocked("sealed bundle authority is invalid") from error
    digest = payload.get("bundle_digest") if isinstance(payload, dict) else None
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        raise AcceptanceBlocked("sealed bundle authority digest differs")
    body = {key: value for key, value in payload.items() if key != "bundle_digest"}
    if digest != _stable_digest(body):
        raise AcceptanceBlocked("sealed bundle authority digest differs")
    return digest


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _validate_service_state(state: Mapping[str, Any]) -> dict[str, Any]:
    required = {"runtime_manifest_identity", "production_launch_plists", "loaded_service_snapshot", "registry"}
    if set(state) != required:
        raise AcceptanceBlocked("production service state schema differs")
    manifest_identity = state["runtime_manifest_identity"]
    production_plists = state["production_launch_plists"]
    loaded = state["loaded_service_snapshot"]
    registry = state["registry"]
    if (
        not isinstance(manifest_identity, Mapping)
        or set(manifest_identity) != {"manifest_path", "manifest_digest", "runtime_identity_digest", "generation"}
        or not all(isinstance(manifest_identity[key], str) for key in manifest_identity)
        or SHA256_PATTERN.fullmatch(str(manifest_identity["manifest_digest"])) is None
        or SHA256_PATTERN.fullmatch(str(manifest_identity["runtime_identity_digest"])) is None
        or not isinstance(production_plists, list)
        or len(production_plists) != len(SERVICE_LABELS)
        or {
            item.get("label") for item in production_plists if isinstance(item, Mapping)
        } != set(SERVICE_LABELS)
        or any(
            not isinstance(item, Mapping)
            or set(item) != {"label", "plist_path", "plist_digest"}
            or not isinstance(item["label"], str)
            or not isinstance(item["plist_path"], str)
            or not isinstance(item["plist_digest"], str)
            or SHA256_PATTERN.fullmatch(item["plist_digest"]) is None
            for item in production_plists
        )
        or any(Path(str(item["plist_path"])).is_absolute() is False for item in production_plists)
        or not isinstance(loaded, list)
        or any(not isinstance(item, str) for item in loaded)
        or not isinstance(registry, Mapping)
        or set(registry) != {"identity", "count", "digest"}
        or not isinstance(registry["identity"], str)
        or not isinstance(registry["count"], int)
        or not isinstance(registry["digest"], str)
        or SHA256_PATTERN.fullmatch(registry["digest"]) is None
    ):
        raise AcceptanceBlocked("production service state is invalid")
    if set(loaded) & set(SERVICE_LABELS):
        raise AcceptanceBlocked("production loaded acceptance labels present")
    return {
        "runtime_manifest_identity": dict(manifest_identity),
        "production_launch_plists": sorted(
            [dict(item) for item in production_plists],
            key=lambda item: str(item["label"]),
        ),
        "loaded_service_snapshot": sorted(loaded),
        "registry": dict(registry),
    }


def production_fingerprint(
    paths: Mapping[str, Path],
    service_state: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(paths) != PRODUCTION_ROOT_KEYS:
        raise AcceptanceBlocked("production root keys differ")
    roots = {
        name: {
            "canonical_path": str(_canonical_dir(Path(value), f"production {name}")),
            "tree_digest": _tree_digest(Path(value)),
        }
        for name, value in sorted(paths.items())
    }
    identities_digest = hashlib.sha256(json.dumps(roots, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    state = service_state()
    if not isinstance(state, Mapping): raise AcceptanceBlocked("production service state is invalid")
    service_snapshot = _validate_service_state(state)
    state_digest = _stable_digest(service_snapshot)
    return {
        "root_identities": roots,
        "root_identities_digest": identities_digest,
        "filesystem_digest": identities_digest,
        "runtime_manifest_identity": service_snapshot["runtime_manifest_identity"],
        "runtime_manifest_identity_digest": _stable_digest(service_snapshot["runtime_manifest_identity"]),
        "production_launch_plists": service_snapshot["production_launch_plists"],
        "production_launch_plists_digest": _stable_digest(service_snapshot["production_launch_plists"]),
        "loaded_service_snapshot": service_snapshot["loaded_service_snapshot"],
        "registry": service_snapshot["registry"],
        "service_state_digest": state_digest,
    }


def _env(manifest: Mapping[str, Any], label: str, barrier: Path) -> dict[str, str]:
    fields = {"PANTHEON_RUNTIME_MANIFEST": "manifest_path", "PANTHEON_RUNTIME_MANIFEST_DIGEST": "manifest_digest", "PANTHEON_RUNTIME_IDENTITY": "identity", "PANTHEON_RUNTIME_IDENTITY_DIGEST": "runtime_identity_digest", "PANTHEON_RUNTIME_CODE_DIGEST": "runtime_digest", "PANTHEON_RUNTIME_CONFIG_VERSION": "config_version", "PANTHEON_RUNTIME_GENERATION": "generation", "PANTHEON_RUNTIME_ACTOR_ROOT": "actor_root", "PANTHEON_RUNTIME_QUEUE_ROOT": "queue_root", "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": "publisher_state_root", "PANTHEON_RUNTIME_LOG_ROOT": "log_root"}
    result = {key: str(manifest[value]) for key, value in fields.items()}
    result.update({"PANTHEON_FORMAL_RUNTIME": "1", "PANTHEON_RUNTIME_SERVICE_LABEL": label, "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(barrier)})
    for key in ("actor_head", "python_executable", "uv_executable"):
        if key in manifest: result["PANTHEON_RUNTIME_" + key.upper()] = str(manifest[key])
    return result


def _prefix(python: str, manifest: Mapping[str, Any], label: str, barrier: Path, ready: Path, activation_only: bool) -> list[str]:
    value = [python, "-m", "scripts.pantheon_content_runtime_manifest", "barrier-exec", "--barrier", str(barrier), "--expected-digest", str(manifest["manifest_digest"]), "--manifest", str(manifest["manifest_path"]), "--service-label", label, "--ready-root", str(ready), "--timeout", "1"]
    return [*value, *( ["--activation-only"] if activation_only else [])]


def _binding(value: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    required = {"lane", "run_id", "bundle", "bundle_digest", "actor_digest", "generation", "identity_digest"}
    cb_optional = {"pending_receipt", "pending_digest", "c_b_plan_digest"}
    optional = {*cb_optional, "required_entries"}
    if not required.issubset(value) or set(value) - required - optional: raise AcceptanceBlocked("lane binding fields differ")
    lane, run_id = str(value["lane"]), str(value["run_id"])
    bundle = _canonical_file(Path(str(value["bundle"])), "sealed bundle")
    if lane not in LANES or not run_id or _sha(bundle) != str(value["bundle_digest"]): raise AcceptanceBlocked("sealed lane binding differs")
    if (str(value["actor_digest"]), str(value["generation"]), str(value["identity_digest"])) != (str(manifest["runtime_digest"]), str(manifest["generation"]), str(manifest["runtime_identity_digest"])): raise AcceptanceBlocked("sealed binding identity differs")
    required_entries = _bundle_required_entries(
        bundle,
        expected_bundle_digest=str(value["bundle_digest"]),
        queue_root=Path(str(manifest["queue_root"])) / "lanes" / lane,
        lane=lane,
        run_id=run_id,
        generation=str(manifest["generation"]),
    )
    if "required_entries" in value and value["required_entries"] != required_entries:
        raise AcceptanceBlocked("sealed bundle required entries differ")
    parsed = {
        "lane": lane,
        "run_id": run_id,
        "bundle": str(bundle),
        "bundle_digest": str(value["bundle_digest"]),
        "sealed_bundle_authority_digest": _bundle_authority_digest(bundle),
        "required_entries": required_entries,
    }
    if lane in TRANSLATION_LANES:
        if not cb_optional.issubset(value):
            raise AcceptanceBlocked("C-B external pins differ")
        pending = _canonical_file(Path(str(value["pending_receipt"])), "C-B pending receipt")
        if _sha(pending) != str(value["pending_digest"]) or SHA256_PATTERN.fullmatch(str(value["c_b_plan_digest"])) is None:
            raise AcceptanceBlocked("C-B external pins differ")
        parsed.update({"pending_receipt": str(pending), "pending_digest": str(value["pending_digest"]), "c_b_plan_digest": str(value["c_b_plan_digest"])})
    elif cb_optional & set(value):
        raise AcceptanceBlocked("C-B external pins differ")
    return parsed


def _validate_children(paths: list[Path], bindings: list[dict[str, Any]], manifest: Mapping[str, Any], publisher_run_id: str) -> None:
    by_label = {path.stem: plistlib.loads(path.read_bytes())["ProgramArguments"] for path in paths}
    child = lambda arguments: arguments[arguments.index("--") + 1 :]
    values = lambda arguments, flag: [arguments[index + 1] for index, value in enumerate(arguments[:-1]) if value == flag]
    coordinator = child(by_label[COORDINATOR])
    source_run_ids = [item["run_id"] for item in bindings if item["lane"] in SOURCE_LANES]
    if values(coordinator, "--exact-run-id") != source_run_ids or coordinator.count("--lane-mode") != 1 or coordinator.count("--external-workers-only") != 1 or coordinator.count("cycle") != 1 or any(flag in coordinator for flag in ("--new-matrix-sweep", "--legacy-sweep")): raise AcceptanceBlocked("coordinator child exact contract differs")
    for item in bindings:
        runner_child = child(by_label[f"com.pantheon.agy-gemini-{item['lane']}"])
        expected_root = str(Path(manifest["queue_root"]) / "lanes" / item["lane"])
        if runner_child.count("--exact-run-id") != 1 or "sealed-replay-bundle-process-once" not in runner_child or "process-once" in runner_child or "operator-exact-process-once" in runner_child or expected_root not in runner_child or item["run_id"] not in runner_child or item["bundle"] not in runner_child or item["bundle_digest"] not in runner_child: raise AcceptanceBlocked("runner child exact contract differs")
    publisher = child(by_label[PUBLISHER])
    if values(publisher, "--max-runs") != ["1"] or values(publisher, "--exact-run-id") != [publisher_run_id] or "--dry-run" not in publisher or "--push" in publisher: raise AcceptanceBlocked("publisher child exact contract differs")
    capacity = child(by_label[CAPACITY])
    if capacity[-1] != "preflight" or str(manifest["queue_root"]) not in capacity or str(manifest["publisher_state_root"]) not in capacity: raise AcceptanceBlocked("capacity child exact contract differs")


def _session_plan(
    *, path: Path, expected_digest: str, root: Path, manifest: Mapping[str, Any],
    bindings: list[dict[str, Any]], publisher_run_id: str, productions: Mapping[str, Path],
) -> tuple[dict[str, Any], str]:
    plan_path = _canonical_file(path, "acceptance session plan")
    if not plan_path.is_relative_to(root) or SHA256_PATTERN.fullmatch(expected_digest) is None:
        raise AcceptanceBlocked("acceptance session plan authority is invalid")
    actual_digest = _sha(plan_path)
    if actual_digest != expected_digest:
        raise AcceptanceBlocked("acceptance session plan digest differs")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AcceptanceBlocked("acceptance session plan is invalid") from error
    required = PLAN_FIELDS
    if not isinstance(plan, dict) or set(plan) != required or plan.get("schema_version") != 1:
        raise AcceptanceBlocked("acceptance session plan fields differ")
    nonce = plan.get("session_nonce_digest")
    if not isinstance(nonce, str) or SHA256_PATTERN.fullmatch(nonce) is None:
        raise AcceptanceBlocked("acceptance session nonce differs")
    generation = f"acceptance-{nonce[:32]}"
    if plan.get("generation") != generation or plan.get("session_id") != f"four-lane-acceptance-{nonce[:32]}":
        raise AcceptanceBlocked("acceptance session generation differs")
    generation = str(plan["generation"])
    expected_roots = {
        "acceptance_root": str(root), "actor_root": str(manifest["actor_root"]),
        "queue_root": str(manifest["queue_root"]), "publisher_state_root": str(manifest["publisher_state_root"]),
        "log_root": str(manifest["log_root"]),
        **{f"production_{name}": str(value) for name, value in productions.items()},
    }
    expected_paths = {
        "plist_paths": [str(root / "plists" / generation / f"{label}.plist") for label in SERVICE_LABELS],
        "ready_root": str(root / "readiness" / generation),
        "barrier": str(root / "barriers" / f"{generation}.json"),
        "lock": str(root / "locks" / f"{generation}.lock"),
        "evidence_root": str(root / "evidence" / generation),
        "consumed_marker": str(root / "consumed" / f"{generation}.json"),
    }
    expected_runs = [
        {
            "lane": item["lane"],
            "run_id": item["run_id"],
            "bundle_path": item["bundle"],
            "bundle_digest": item["bundle_digest"],
            "required_entries": item["required_entries"],
        }
        for item in bindings
    ]
    run_by_lane = {item["lane"]: item for item in bindings}
    expected_graph = [
        {"source_lane": "new", "translation_lane": "i18n-new"},
        {"source_lane": "rewrite", "translation_lane": "i18n-rewrite"},
    ]
    expected_cb = [
        {
            "source_run_id": run_by_lane[source]["run_id"],
            "target_run_id": run_by_lane[target]["run_id"],
            "pending_receipt": run_by_lane[target]["pending_receipt"],
            "pending_digest": run_by_lane[target]["pending_digest"],
            "plan_digest": run_by_lane[target]["c_b_plan_digest"],
        }
        for source, target in (("new", "i18n-new"), ("rewrite", "i18n-rewrite"))
    ]
    expected_publishers = [
        {"lane": item["lane"], "run_id": item["run_id"], "max_runs": 1, "selector_cardinality": 1, "dry_run": True, "push": False, "public_mutation": False}
        for item in expected_runs
    ]
    if plan.get("actor_sha") != manifest.get("actor_head") or plan.get("accepted_parent_sha") != ACCEPTED_PARENT_SHA or plan.get("publisher_activation_run_id") != publisher_run_id or plan.get("manifest_path") != str(manifest["manifest_path"]) or plan.get("manifest_digest") != manifest["manifest_digest"] or plan.get("runtime_identity_digest") != manifest["runtime_identity_digest"] or plan.get("generation") != manifest["generation"] or plan.get("service_labels") != list(SERVICE_LABELS) or plan.get("exact_runs") != expected_runs or plan.get("roots") != expected_roots or any(plan.get(key) != value for key, value in expected_paths.items()):
        raise AcceptanceBlocked("acceptance session plan binding differs")
    if plan.get("dependency_graph") != expected_graph or plan.get("c_b_materializations") != expected_cb or plan.get("bundle_closeouts") != expected_runs or plan.get("publisher_plan_only") != expected_publishers:
        raise AcceptanceBlocked("acceptance session plan workload differs")
    _validate_phase_schedule(plan["phase_schedule"], bindings)
    if plan.get("budgets") != {"provider_production_calls": 0, "public_mutation": 0, "production_queue_mutation": 0, "production_ledger_mutation": 0, "production_publisher_state_mutation": 0, "tag_push_deploy": 0}:
        raise AcceptanceBlocked("acceptance session plan budgets differ")
    teardown = plan.get("teardown")
    if not isinstance(teardown, Mapping) or teardown.get("initial_loaded_acceptance_labels") != 0 or teardown.get("final_absent_acceptance_labels") != 7 or sorted(teardown.get("allowed_residue", [])) != ["consumed_marker", "evidence_receipt"] or teardown.get("forbidden_residue") != ["plists", "readiness", "barrier", "lock"]:
        raise AcceptanceBlocked("acceptance session plan teardown differs")
    if plan.get("production_fingerprint_contract") != ["root_identities", "runtime_manifest_identity", "production_launch_plists", "loaded_service_snapshot", "registry"]:
        raise AcceptanceBlocked("acceptance session plan fingerprint contract differs")
    return plan, actual_digest


def _validate_phase_schedule(schedule: Any, bindings: list[dict[str, Any]]) -> None:
    if not isinstance(schedule, list):
        raise AcceptanceBlocked("acceptance schedule differs")
    by_lane = {item["lane"]: item for item in bindings}
    expected: list[dict[str, Any]] = []

    def phase_steps(phase: str, lanes: tuple[str, ...]) -> None:
        run_ids = [by_lane[lane]["run_id"] for lane in lanes]
        max_entries = max(len(by_lane[lane]["required_entries"]) for lane in lanes)
        for entry_index in range(max_entries):
            expected.append({"phase": phase, "action": "coordinator-cycle", "lanes": list(lanes), "run_ids": run_ids, "round": entry_index + 1})
            expected.extend({"phase": phase, "action": "runner-process-once", "lane": lane, "run_id": by_lane[lane]["run_id"], "entry_id": by_lane[lane]["required_entries"][entry_index]} for lane in lanes if entry_index < len(by_lane[lane]["required_entries"]))
        expected.append({"phase": phase, "action": "coordinator-cycle", "lanes": list(lanes), "run_ids": run_ids, "terminal": True})

    phase_steps("source", SOURCE_LANES)
    expected.extend({
        "phase": "materialization",
        "action": "c-b-materialize",
        "source_lane": source,
        "source_run_id": by_lane[source]["run_id"],
        "target_lane": target,
        "target_run_id": by_lane[target]["run_id"],
    } for source, target in (("new", "i18n-new"), ("rewrite", "i18n-rewrite")))
    phase_steps("translation", TRANSLATION_LANES)
    expected.extend({"phase": "bundle-close", "action": "bundle-close", "lane": lane, "run_id": by_lane[lane]["run_id"]} for lane in LANES)
    expected.extend({"phase": "publisher", "action": "publisher-plan-only", "lane": lane, "run_id": by_lane[lane]["run_id"]} for lane in LANES)
    expected.append({"phase": "closeout", "action": "queue-drain", "pending": 0, "processing": 0})
    if schedule != expected:
        raise AcceptanceBlocked("acceptance schedule differs")


def render_plists(*, manifest_path: Path, expected_manifest_digest: str, acceptance_root: Path, bindings: list[Mapping[str, Any]], publisher_run_id: str, production_paths: Mapping[str, Path], session_plan_path: Path, expected_session_plan_digest: str) -> dict[str, Any]:
    root = _canonical_dir(acceptance_root, "acceptance root")
    if set(production_paths) != PRODUCTION_ROOT_KEYS:
        raise AcceptanceBlocked("production root keys differ")
    manifest_file = _canonical_file(manifest_path, "disposable manifest")
    if not manifest_file.is_relative_to(root):
        raise AcceptanceBlocked("disposable manifest must be an acceptance descendant")
    manifest = {**runtime.load_manifest(manifest_path, expected_manifest_digest), "manifest_path": str(manifest_path)}
    owned = {name: _descendant(Path(manifest[field]), root, name) for name, field in (("queue", "queue_root"), ("state", "publisher_state_root"), ("logs", "log_root"))}
    productions = {name: _canonical_dir(Path(value), f"production {name}") for name, value in production_paths.items()}
    if any(_overlap(root, production) or any(_overlap(owned_path, production) for owned_path in owned.values()) for production in productions.values()) or any(_overlap(left, right) for index, left in enumerate(productions.values()) for right in list(productions.values())[index + 1 :]): raise AcceptanceBlocked("acceptance or production roots overlap")
    parsed = [_binding(item, manifest) for item in bindings]
    if {item["lane"] for item in parsed} != set(LANES) or len({item["run_id"] for item in parsed}) != 4 or len({item["bundle"] for item in parsed}) != 4 or not publisher_run_id: raise AcceptanceBlocked("acceptance exact bindings differ")
    plan, plan_digest = _session_plan(path=session_plan_path, expected_digest=expected_session_plan_digest, root=root, manifest=manifest, bindings=parsed, publisher_run_id=publisher_run_id, productions=productions)
    generation = str(plan["generation"])
    plist_parent, readiness_parent, barrier_parent, lock_parent, evidence_parent, consumed_parent = (root / "plists", root / "readiness", root / "barriers", root / "locks", root / "evidence", root / "consumed")
    for path, label in ((plist_parent, "plist parent"), (readiness_parent, "readiness parent"), (barrier_parent, "barrier parent"), (lock_parent, "lock parent"), (evidence_parent, "evidence parent"), (consumed_parent, "consumed parent")):
        _descendant(path, root, label)
    final, staging = plist_parent / generation, root / f".plists-staging.{generation}"
    ready, barrier, lock, evidence, consumed = readiness_parent / generation, barrier_parent / f"{generation}.json", lock_parent / f"{generation}.lock", evidence_parent / generation, consumed_parent / f"{generation}.json"
    if any(path.exists() for path in (final, staging, ready, barrier, lock, evidence, consumed)):
        raise AcceptanceBlocked("acceptance residue exists before render")
    _write_json_exclusive(consumed, {
        "schema_version": 1,
        "session_id": plan["session_id"],
        "generation": generation,
        "session_nonce_digest": plan["session_nonce_digest"],
        "session_plan_digest": plan_digest,
    })
    _fsync_directory(consumed_parent)
    staging.mkdir(mode=0o700)
    python = str(manifest.get("python_executable") or os.sys.executable)
    source_bindings = [item for item in parsed if item["lane"] in SOURCE_LANES]
    children: dict[str, list[str]] = {COORDINATOR: [python,"-m","scripts.agy_gemini_coordinator","--queue-root",str(manifest["queue_root"]),"--repo-root",str(manifest["actor_root"]),"--lane-mode","cycle",*(token for item in source_bindings for token in ("--exact-run-id",item["run_id"])),"--external-workers-only"], PUBLISHER: [python,"-m","scripts.agy_content_publisher","--repo-root",str(manifest["actor_root"]),"--queue-root",str(manifest["queue_root"]),"--state-root",str(manifest["publisher_state_root"]),"--max-runs","1","--exact-run-id",publisher_run_id,"--dry-run"], CAPACITY: [python,"-m","scripts.pantheon_content_capacity_guard","--queue-root",str(manifest["queue_root"]),"--publisher-root",str(manifest["publisher_state_root"]),"--log-root",str(manifest["log_root"]),"preflight"]}
    for item in parsed: children[f"com.pantheon.agy-gemini-{item['lane']}"] = [python,"-m","scripts.agy_gemini_runner","--queue-root",str(Path(manifest["queue_root"])/"lanes"/item["lane"]),"--lane",item["lane"],"--exact-run-id",item["run_id"],"sealed-replay-bundle-process-once","--bundle",item["bundle"],"--expected-bundle-digest",item["bundle_digest"]]
    paths: list[Path] = []
    try:
        for label in SERVICE_LABELS:
            activation_only = True
            path = staging / f"{label}.plist"
            final_path = final / f"{label}.plist"
            _write_plist(path, {"Label": label, "ProgramArguments": [*_prefix(python,manifest,label,barrier,ready,activation_only),"--",*children[label]], "EnvironmentVariables": _env(manifest,label,barrier), "WorkingDirectory": str(manifest["actor_root"]), "RunAtLoad": False, "StandardOutPath": str(final_path.with_suffix(".stdout.json")), "StandardErrorPath": str(final_path.with_suffix(".stderr.log"))})
            paths.append(path)
        receipts = [runtime.plist_receipt(path, expected_activation_mode="activation-only") for path in paths]
        runtime.validate_receipts(manifest, [{key:value for key,value in item.items() if key != "plist_realpath"} for item in receipts])
        runtime.publisher_plist_receipt(staging / f"{PUBLISHER}.plist", expected_activation_mode="activation-only")
        _validate_children(paths, parsed, manifest, publisher_run_id)
        _fsync_directory(staging)
        os.replace(staging, final)
        _fsync_directory(root)
    except Exception:
        with suppress(FileNotFoundError):
            for path in staging.iterdir(): path.unlink()
            staging.rmdir()
        raise
    return {"manifest":manifest,"acceptance_root":root,"plist_paths":[final/path.name for path in paths],"ready_root":ready,"evidence_root":evidence,"barrier":barrier,"lock":lock,"consumed_marker":consumed,"bindings":parsed,"production_paths":productions,"session_plan":plan,"session_plan_path":Path(session_plan_path),"session_plan_digest":plan_digest,"publisher_run_id":publisher_run_id}


def _consumed_marker(rendered: Mapping[str, Any], plan: Mapping[str, Any]) -> None:
    marker = _canonical_file(Path(rendered["consumed_marker"]), "consumed generation marker")
    if marker != Path(str(plan["consumed_marker"])):
        raise AcceptanceBlocked("consumed generation marker authority differs")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "session_id": plan["session_id"],
        "generation": plan["generation"],
        "session_nonce_digest": plan["session_nonce_digest"],
        "session_plan_digest": rendered["session_plan_digest"],
    }
    if payload != expected:
        raise AcceptanceBlocked("consumed generation marker differs")


def _revalidate_rendered_plan(rendered: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    root = _canonical_dir(Path(rendered["acceptance_root"]), "acceptance root")
    plan, plan_digest = _session_plan(path=Path(rendered["session_plan_path"]), expected_digest=str(rendered["session_plan_digest"]), root=root, manifest=rendered["manifest"], bindings=rendered["bindings"], publisher_run_id=str(rendered["publisher_run_id"]), productions=rendered["production_paths"])
    if plan != rendered["session_plan"] or plan_digest != rendered["session_plan_digest"]:
        raise AcceptanceBlocked("acceptance session plan revalidation differs")
    return plan, plan_digest


def _expect(receipt: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> dict[str, Any]:
    if (
        not isinstance(receipt, Mapping)
        or set(receipt) != set(expected)
        or any(receipt.get(key) != value for key, value in expected.items())
    ):
        raise AcceptanceBlocked(f"{label} receipt differs")
    return dict(receipt)


def _run_process(command: list[str]) -> subprocess.CompletedProcess[str]:
    if command[:1] == [LAUNCHCTL]:
        return subprocess.CompletedProcess(
            command,
            78,
            "",
            "real launchctl execution is not authorized for disposable acceptance\n",
        )
    return subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )


@contextmanager
def _formal_env(rendered: Mapping[str, Any], service_label: str):
    manifest = rendered["manifest"]
    previous = os.environ.copy()
    os.environ.update(_env(manifest, service_label, Path(rendered["barrier"])))
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def _stdout_json(completed: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    if completed.returncode != 0:
        raise AcceptanceBlocked(f"{label} owner command failed")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AcceptanceBlocked(f"{label} owner stdout is not json") from error
    if not isinstance(payload, dict):
        raise AcceptanceBlocked(f"{label} owner stdout is not an object")
    if payload.get("status") == "rejected":
        raise AcceptanceBlocked(f"{label} owner command rejected")
    return payload


def _process_owner_receipt(
    rendered: Mapping[str, Any],
    *,
    service_label: str,
    command: list[str],
    owner: str,
    key: str,
    label: str,
) -> dict[str, Any]:
    with _formal_env(rendered, service_label):
        native = _stdout_json(_run_process(command), label)
    return {"owner": owner, "command": command, key: native}


def _launchctl_completed(command: list[str], expected_returncode: int, label: str) -> subprocess.CompletedProcess[str]:
    completed = _run_process(command)
    if completed.returncode != expected_returncode:
        raise AcceptanceBlocked(f"{label} receipt differs")
    return completed


def _launchctl_print_absent(label: str, phase: str, plist_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    command = [LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"]
    _launchctl_completed(command, 113, "launchctl print")
    return _expect(
        {**_print_not_found_expectation(label, phase, plist_path, manifest), "command": command},
        _print_not_found_expectation(label, phase, plist_path, manifest),
        "launchctl print",
    )


def _launchctl_launch(label: str, plist_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    bootstrap = [LAUNCHCTL, "bootstrap", f"gui/{os.getuid()}", str(plist_path)]
    _launchctl_completed(bootstrap, 0, "launchctl bootstrap")
    try:
        loaded_print = [LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"]
        loaded = _launchctl_completed(loaded_print, 0, "launchctl loaded print")
        if label not in loaded.stdout:
            raise AcceptanceBlocked("launchctl loaded identity differs")
        kickstart = [LAUNCHCTL, "kickstart", "-k", f"gui/{os.getuid()}/{label}"]
        _launchctl_completed(kickstart, 0, "launchctl kickstart")
    except Exception:
        with suppress(Exception):
            _launchctl_bootout(label, plist_path, manifest)
        raise
    receipt = {
        **_launch_expectation(label, plist_path, manifest),
        "command": bootstrap,
        "loaded_identity": {
            "label": label,
            "plist_path": str(plist_path),
            "plist_digest": _sha(plist_path),
            "actor_root": str(manifest["actor_root"]),
            "manifest_digest": str(manifest["manifest_digest"]),
            "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
            "generation": str(manifest["generation"]),
        },
        "kickstart": {"command": kickstart, "returncode": 0, "label": label},
    }
    return _expect(receipt, _launch_expectation(label, plist_path, manifest), "launchctl bootstrap")


def _launchctl_bootout(label: str, plist_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    command = [LAUNCHCTL, "bootout", f"gui/{os.getuid()}/{label}"]
    _launchctl_completed(command, 0, "launchctl bootout")
    return _expect(
        {**_bootout_expectation(label, plist_path, manifest), "command": command},
        _bootout_expectation(label, plist_path, manifest),
        "bootout",
    )


def _launch_retained(
    authority: ContinuousAuthority,
    label: str,
    artifact: RetainedFile,
    kind: str,
) -> dict[str, Any]:
    """bootstrap 0 的同一控制點立即轉移 teardown ownership。"""
    artifact.verify(f"{kind} plist")
    manifest = authority.rendered["manifest"]
    bootstrap = [LAUNCHCTL, "bootstrap", f"gui/{os.getuid()}", str(artifact.path)]
    completed = _run_process(bootstrap)
    if completed.returncode != 0:
        raise AcceptanceBlocked("launchctl bootstrap receipt differs")
    authority.claim_loaded(label, artifact, kind)
    artifact.verify(f"{kind} plist")
    loaded_command = [LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"]
    loaded = _run_process(loaded_command)
    if loaded.returncode != 0 or label not in loaded.stdout:
        raise AcceptanceBlocked("launchctl loaded identity differs")
    artifact.verify(f"{kind} plist")
    kickstart = [LAUNCHCTL, "kickstart", "-k", f"gui/{os.getuid()}/{label}"]
    kicked = _run_process(kickstart)
    if kicked.returncode != 0:
        raise AcceptanceBlocked("launchctl kickstart receipt differs")
    artifact.verify(f"{kind} plist")
    return _launch_expectation(label, artifact.path, manifest, artifact.digest)


def _production_file(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise AcceptanceBlocked(f"{label} is not available")
    return path.resolve(strict=True)


def _plist_receipt_from_bytes(body: bytes, path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload = plistlib.loads(body)
    except plistlib.InvalidFileException as error:
        raise AcceptanceBlocked("production launch plist is invalid") from error
    environment = payload.get("EnvironmentVariables")
    if not isinstance(environment, dict):
        raise AcceptanceBlocked("production launch plist is invalid")
    receipt = {
        "label": payload.get("Label"),
        "service_label": environment.get("PANTHEON_RUNTIME_SERVICE_LABEL"),
        "identity": environment.get("PANTHEON_RUNTIME_IDENTITY"),
        "manifest_digest": environment.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
        "runtime_identity_digest": environment.get("PANTHEON_RUNTIME_IDENTITY_DIGEST"),
        "runtime_digest": environment.get("PANTHEON_RUNTIME_CODE_DIGEST"),
        "config_version": environment.get("PANTHEON_RUNTIME_CONFIG_VERSION"),
        "generation": environment.get("PANTHEON_RUNTIME_GENERATION"),
        "actor_root": environment.get("PANTHEON_RUNTIME_ACTOR_ROOT"),
        "queue_root": environment.get("PANTHEON_RUNTIME_QUEUE_ROOT"),
        "publisher_state_root": environment.get("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"),
        "log_root": environment.get("PANTHEON_RUNTIME_LOG_ROOT"),
        "plist_realpath": str(path),
    }
    for field, key in (("actor_head", "PANTHEON_RUNTIME_ACTOR_HEAD"), ("python_executable", "PANTHEON_RUNTIME_PYTHON_EXECUTABLE"), ("uv_executable", "PANTHEON_RUNTIME_UV_EXECUTABLE")):
        if key in environment:
            receipt[field] = environment[key]
    return payload, receipt


def _production_service_state(authority: ContinuousAuthority | None = None) -> dict[str, Any]:
    owned = authority
    if owned is None:
        rendered = {"acceptance_root": Path.cwd()}  # direct callers use the narrow production aggregate below
        home = RetainedDirectory.open_absolute(_os_uid_home(), "production uid home")
        directories = [home]
        files: list[RetainedFile] = []
        try:
            library = home.open_directory("Library", "production Library")
            directories.append(library)
            launch_agents = library.open_directory("LaunchAgents", "production LaunchAgents")
            directories.append(launch_agents)
            if launch_agents.path != PRODUCTION_LAUNCH_PLIST_ROOT:
                raise AcceptanceBlocked("production LaunchAgents authority differs")
            production_plists = {label: RetainedFile.open(launch_agents, f"{label}.plist", "production launch plist") for label in SERVICE_LABELS}
            files.extend(production_plists.values())
            return _production_service_state_from_retained(production_plists)
        finally:
            for item in reversed(files): item.close()
            for item in reversed(directories): item.close()
    return _production_service_state_from_retained(owned.production_plists)


def _production_service_state_from_retained(plist_files: Mapping[str, RetainedFile]) -> dict[str, Any]:
    manifest_identities: set[tuple[str, str]] = set()
    plist_receipts: list[dict[str, Any]] = []
    production_plists: list[dict[str, str]] = []
    for label in SERVICE_LABELS:
        retained = plist_files[label]
        body = retained.read("production launch plist")
        payload, receipt = _plist_receipt_from_bytes(body, retained.path)
        environment = payload.get("EnvironmentVariables")
        if not isinstance(environment, dict):
            raise AcceptanceBlocked("production launch plist is invalid")
        manifest_identities.add(
            (
                str(environment.get("PANTHEON_RUNTIME_MANIFEST", "")),
                str(environment.get("PANTHEON_RUNTIME_MANIFEST_DIGEST", "")),
            )
        )
        if receipt.get("label") != label:
            raise AcceptanceBlocked("production launch plist is invalid")
        plist_receipts.append(receipt)
        production_plists.append(
            {
                "label": label,
                "plist_path": str(retained.path),
                "plist_digest": hashlib.sha256(body).hexdigest(),
            }
        )
    if len(manifest_identities) != 1:
        raise AcceptanceBlocked("production runtime manifest identity differs")
    manifest_name, expected_manifest_digest = manifest_identities.pop()
    if not manifest_name or SHA256_PATTERN.fullmatch(expected_manifest_digest) is None:
        raise AcceptanceBlocked("production runtime manifest is invalid")
    manifest_path = _production_file(Path(manifest_name), "production runtime manifest")
    try:
        manifest = runtime.load_manifest(manifest_path, expected_manifest_digest)
        runtime.validate_receipts(manifest, plist_receipts)
    except runtime.RuntimeManifestError as error:
        raise AcceptanceBlocked("production runtime manifest is invalid") from error
    registry_path = _production_file(
        Path(str(manifest["actor_root"])) / PRODUCTION_ARTICLE_REGISTRY_RELATIVE_PATH,
        "production article registry",
    )
    registry_body = registry_path.read_bytes()
    registry = {
        "identity": str(registry_path),
        "count": registry_body.count(b"publicationPolicy"),
        "digest": hashlib.sha256(registry_body).hexdigest(),
    }
    loaded: list[str] = []
    for label in SERVICE_LABELS:
        completed = _run_process([LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"])
        if completed.returncode == 113:
            continue
        if completed.returncode == 0 and label in completed.stdout:
            loaded.append(label)
            continue
        raise AcceptanceBlocked("production service state is invalid")
    return {
        "runtime_manifest_identity": {
            "manifest_path": str(manifest_path),
            "manifest_digest": _sha(manifest_path),
            "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
            "generation": str(manifest["generation"]),
        },
        "production_launch_plists": production_plists,
        "loaded_service_snapshot": sorted(loaded),
        "registry": registry,
    }


def _launch_side_effect_proven(receipt: Mapping[str, Any], label: str, plist_path: Path, manifest: Mapping[str, Any]) -> bool:
    loaded = receipt.get("loaded_identity") if isinstance(receipt, Mapping) else None
    return (
        isinstance(receipt, Mapping)
        and receipt.get("phase") == "bootstrap"
        and receipt.get("returncode") == 0
        and receipt.get("label") == label
        and receipt.get("plist_path") == str(plist_path)
        and receipt.get("plist_digest") == _sha(plist_path)
        and isinstance(loaded, Mapping)
        and loaded.get("label") == label
        and loaded.get("plist_path") == str(plist_path)
        and loaded.get("plist_digest") == _sha(plist_path)
        and loaded.get("actor_root") == str(manifest["actor_root"])
        and loaded.get("manifest_digest") == str(manifest["manifest_digest"])
        and loaded.get("runtime_identity_digest") == str(manifest["runtime_identity_digest"])
        and loaded.get("generation") == str(manifest["generation"])
    )


def _launch_expectation(label: str, plist_path: Path, manifest: Mapping[str, Any], plist_digest: str | None = None) -> dict[str, Any]:
    digest = plist_digest if plist_digest is not None else _sha(plist_path)
    return {
        "schema_version": 1,
        "status": "bootstrapped",
        "phase": "bootstrap",
        "command": [LAUNCHCTL, "bootstrap", f"gui/{os.getuid()}", str(plist_path)],
        "returncode": 0,
        "label": label,
        "plist_path": str(plist_path),
        "plist_digest": digest,
        "actor_root": str(manifest["actor_root"]),
        "manifest_digest": str(manifest["manifest_digest"]),
        "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
        "generation": str(manifest["generation"]),
        "loaded_identity": {
            "label": label,
            "plist_path": str(plist_path),
            "plist_digest": digest,
            "actor_root": str(manifest["actor_root"]),
            "manifest_digest": str(manifest["manifest_digest"]),
            "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
            "generation": str(manifest["generation"]),
        },
        "kickstart": {
            "command": [LAUNCHCTL, "kickstart", "-k", f"gui/{os.getuid()}/{label}"],
            "returncode": 0,
            "label": label,
        },
    }


def _bootout_expectation(label: str, plist_path: Path, manifest: Mapping[str, Any], plist_digest: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "booted_out",
        "phase": "bootout",
        "command": [LAUNCHCTL, "bootout", f"gui/{os.getuid()}/{label}"],
        "returncode": 0,
        "label": label,
        "plist_path": str(plist_path),
        "plist_digest": plist_digest if plist_digest is not None else _sha(plist_path),
        "actor_root": str(manifest["actor_root"]),
        "manifest_digest": str(manifest["manifest_digest"]),
        "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
        "generation": str(manifest["generation"]),
    }


def _print_not_found_expectation(label: str, phase: str, plist_path: Path, manifest: Mapping[str, Any], plist_digest: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "not_found",
        "phase": phase,
        "command": [LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"],
        "returncode": 113,
        "label": label,
        "plist_path": str(plist_path),
        "plist_digest": plist_digest if plist_digest is not None else _sha(plist_path),
        "actor_root": str(manifest["actor_root"]),
        "manifest_digest": str(manifest["manifest_digest"]),
        "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
        "generation": str(manifest["generation"]),
    }


def _coordinator_command(manifest: Mapping[str, Any], run_ids: list[str]) -> list[str]:
    python = str(manifest.get("python_executable") or os.sys.executable)
    return [python, "-m", "scripts.agy_gemini_coordinator", "--queue-root", str(manifest["queue_root"]), "--repo-root", str(manifest["actor_root"]), "--lane-mode", "cycle", *(token for run_id in run_ids for token in ("--exact-run-id", run_id)), "--external-workers-only"]


def _runner_command(manifest: Mapping[str, Any], binding: Mapping[str, str]) -> list[str]:
    python = str(manifest.get("python_executable") or os.sys.executable)
    return [python, "-m", "scripts.agy_gemini_runner", "--queue-root", str(Path(str(manifest["queue_root"])) / "lanes" / str(binding["lane"])), "--lane", str(binding["lane"]), "--exact-run-id", str(binding["run_id"]), "sealed-replay-bundle-process-once", "--bundle", str(binding["bundle"]), "--expected-bundle-digest", str(binding["bundle_digest"])]


def _publisher_owner_for_lane(lane: str) -> tuple[str, str, set[str]]:
    if lane == "new":
        return (
            "publish_ready_runs",
            "published",
            {
                "schema_version",
                "status",
                "published",
                "ready_runs",
                "base_sha",
                "release_plan",
            },
        )
    if lane == "rewrite":
        return (
            "publish_ready_rewrite_runs",
            "rewritten",
            {
                "schema_version",
                "status",
                "rewritten",
                "ready_runs",
                "article_ids",
                "base_sha",
                "legacy_cutoff_count",
                "legacy_rewrite_backlog",
                "release_plan",
            },
        )
    if lane in TRANSLATION_LANES:
        return (
            "publish_ready_translation_runs",
            "translated",
            {
                "schema_version",
                "status",
                "translated",
                "ready_runs",
                "base_sha",
                "release_plan",
                "replacement_plans",
            },
        )
    raise AcceptanceBlocked("publisher lane differs")


def _publisher_command(manifest: Mapping[str, Any], run_id: str, lane: str = "new") -> list[str]:
    owner_function, _count_field, _fields = _publisher_owner_for_lane(lane)
    return [
        f"scripts.agy_content_publisher:{owner_function}",
        "--repo-root",
        str(manifest["actor_root"]),
        "--queue-root",
        str(manifest["queue_root"]),
        "--state-root",
        str(manifest["publisher_state_root"]),
        "--max-runs",
        "1",
        "--exact-run-id",
        run_id,
        "--dry-run",
    ]


def _materializer_command(manifest: Mapping[str, Any], step: Mapping[str, Any], pins: Mapping[str, Any]) -> list[str]:
    python = str(manifest.get("python_executable") or os.sys.executable)
    return [
        python, "-m", "scripts.agy_gemini_coordinator",
        "--queue-root", str(manifest["queue_root"]),
        "--repo-root", str(manifest["actor_root"]),
        "materialize-translation-pending",
        "--source-run-id", str(step["source_run_id"]),
        "--pending-receipt", str(pins["pending_receipt"]),
        "--expected-target-run-id", str(step["target_run_id"]),
        "--expected-pending-digest", str(pins["pending_digest"]),
        "--expected-plan-digest", str(pins["plan_digest"]),
    ]


def _owner_receipt(receipt: Mapping[str, Any], *, owner: str, command: list[str], key: str, label: str) -> Mapping[str, Any]:
    if (
        not isinstance(receipt, Mapping)
        or receipt.get("owner") != owner
        or receipt.get("command") != command
        or not isinstance(receipt.get(key), Mapping)
    ):
        raise AcceptanceBlocked(f"{label} receipt differs")
    return receipt[key]


def _expect_coordinator_receipt(receipt: Mapping[str, Any], step: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    command = _coordinator_command(manifest, list(step["run_ids"]))
    native = _owner_receipt(receipt, owner="scripts.agy_gemini_coordinator:cycle_once", command=command, key="cycle_once", label="coordinator")
    terminal = bool(step.get("terminal", False))
    if (
        native.get("status") != "ok"
        or native.get("runner") != {"status": "external_workers_only"}
        or native.get("failed") != 0
        or native.get("new_matrix_sweep") is not None
        or native.get("legacy_sweep") is not None
        or (terminal and (native.get("active") != 0 or native.get("complete") != len(step["run_ids"])))
    ):
        raise AcceptanceBlocked("coordinator receipt differs")
    owner_readback: list[dict[str, Any]] = []
    if terminal:
        queue_root = Path(str(manifest["queue_root"]))
        for run_id, lane in zip(step["run_ids"], step["lanes"], strict=True):
            state_path = coordinator._state_path(str(run_id), queue_root)
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise AcceptanceBlocked("coordinator owner read-back differs") from error
            if (
                not isinstance(state, dict)
                or state.get("run_id") != run_id
                or state.get("lane") != lane
                or state.get("status") != "complete"
            ):
                raise AcceptanceBlocked("coordinator owner read-back differs")
            owner_readback.append(
                {
                    "run_id": run_id,
                    "lane": lane,
                    "status": "complete",
                    "state_path": str(state_path),
                    "state_digest": _sha(state_path),
                }
            )
    result = {"status": "terminal" if terminal else "ok", "action": "coordinator-cycle", "phase": step["phase"], "lanes": step["lanes"], "run_ids": step["run_ids"], "terminal": terminal, "command": command, "owner": receipt["owner"], "owner_receipt": dict(native), "owner_readback": owner_readback}
    if terminal:
        result["terminal_run_ids"] = step["run_ids"]
    return result


def _expect_runner_receipt(receipt: Mapping[str, Any], step: Mapping[str, Any], manifest: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    command = _runner_command(manifest, binding)
    native = _owner_receipt(receipt, owner="scripts.agy_gemini_runner:sealed_replay_bundle_process_once", command=command, key="sealed_replay_bundle_process_once", label="runner")
    bundle = native.get("sealed_replay_bundle")
    if (
        native.get("status") != "processed"
        or not isinstance(bundle, Mapping)
        or bundle.get("lane") != step["lane"]
        or bundle.get("run_id") != step["run_id"]
        or bundle.get("entry_id") != step["entry_id"]
        or bundle.get("bundle_digest") != binding["sealed_bundle_authority_digest"]
        or bundle.get("expected_bundle_digest") != binding["bundle_digest"]
    ):
        raise AcceptanceBlocked("runner receipt differs")
    loaded = runner._load_acceptance_sealed_replay_bundle(
        Path(str(binding["bundle"])),
        str(binding["bundle_digest"]),
        Path(str(manifest["actor_root"])),
        Path(str(manifest["queue_root"])) / "lanes" / str(binding["lane"]),
        str(binding["lane"]),
        str(binding["run_id"]),
    ).with_activation_token_digest(str(bundle["activation_token_digest"]))
    entry = next(
        (candidate for candidate in loaded.entries if candidate.entry_id == step["entry_id"]),
        None,
    )
    if entry is None:
        raise AcceptanceBlocked("runner owner provenance read-back differs")
    readback = runner._classify_bundle_entry_delivery(
        Path(str(manifest["queue_root"])) / "lanes" / str(binding["lane"]),
        loaded,
        entry,
    )
    paths = readback.get("paths") if isinstance(readback, Mapping) else None
    if (
        readback.get("state") != "DELIVERED"
        or not isinstance(paths, Mapping)
        or paths.get("ledger") is not True
        or paths.get("anchor") is not True
    ):
        raise AcceptanceBlocked("runner owner provenance read-back differs")
    return {"status": "processed", "action": "runner-process-once", "lane": step["lane"], "run_id": step["run_id"], "entry_id": step["entry_id"], "command": command, "owner": receipt["owner"], "owner_receipt": dict(native), "owner_readback": dict(readback)}


def _expect_materialization_receipt(receipt: Mapping[str, Any], step: Mapping[str, Any], manifest: Mapping[str, Any], pins: Mapping[str, Any]) -> dict[str, Any]:
    command = _materializer_command(manifest, step, pins)
    native = _owner_receipt(receipt, owner="scripts.agy_gemini_coordinator:materialize_translation_pending_dependency", command=command, key="materialize_translation_pending_dependency", label="c-b materialization")
    status = native.get("status")
    expected_queue_mutation = True if status == "materialized" else False
    if (
        set(native) != {
            "status",
            "run_id",
            "source_run_id",
            "lane",
            "pending_digest_before",
            "pending_digest_after",
            "plan_digest",
            "brief_sha256",
            "registration_identity_digest",
            "queue_mutation",
            "public_mutation",
        }
        or status not in {"materialized", "already_materialized"}
        or native.get("run_id") != step["target_run_id"]
        or native.get("source_run_id") != step["source_run_id"]
        or native.get("lane") != step["target_lane"]
        or native.get("pending_digest_before") != pins["pending_digest"]
        or not isinstance(native.get("pending_digest_after"), str)
        or SHA256_PATTERN.fullmatch(str(native["pending_digest_after"])) is None
        or native.get("plan_digest") != pins["plan_digest"]
        or not isinstance(native.get("brief_sha256"), str)
        or SHA256_PATTERN.fullmatch(str(native["brief_sha256"])) is None
        or not isinstance(native.get("registration_identity_digest"), str)
        or SHA256_PATTERN.fullmatch(str(native["registration_identity_digest"])) is None
        or native.get("queue_mutation") is not expected_queue_mutation
        or native.get("public_mutation") is not False
    ):
        raise AcceptanceBlocked("c-b materialization receipt differs")
    current = json.loads(Path(str(pins["pending_receipt"])).read_text(encoding="utf-8"))
    _pending, materialized = coordinator._translation_pending_payload(
        current,
        expected_source_run_id=str(step["source_run_id"]),
    )
    if (
        materialized is None
        or materialized.get("pending_digest_after") != native["pending_digest_after"]
        or materialized.get("brief_sha256") != native["brief_sha256"]
        or materialized.get("registration_identity_digest") != native["registration_identity_digest"]
    ):
        raise AcceptanceBlocked("c-b materialization owner read-back differs")
    return {"status": "materialized", "action": "c-b-materialize", "source_run_id": step["source_run_id"], "target_run_id": step["target_run_id"], "pending_receipt": pins["pending_receipt"], "pending_digest": pins["pending_digest"], "plan_digest": pins["plan_digest"], "command": command, "owner": receipt["owner"], "owner_receipt": dict(native), "owner_readback": dict(materialized)}


def _expect_bundle_close_receipt(receipt: Mapping[str, Any], step: Mapping[str, Any], manifest: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    command = [*_runner_command(manifest, binding)[:-5], "sealed-replay-bundle-close", "--bundle", str(binding["bundle"]), "--expected-bundle-digest", str(binding["bundle_digest"])]
    native = _owner_receipt(receipt, owner="scripts.agy_gemini_runner:sealed_replay_bundle_close", command=command, key="sealed_replay_bundle_close", label="bundle closeout")
    session = native.get("sealed_replay_bundle_session")
    if (
        native.get("status") != "closed"
        or not isinstance(session, Mapping)
        or session.get("lane") != step["lane"]
        or session.get("run_id") != step["run_id"]
        or session.get("bundle_digest") != binding["sealed_bundle_authority_digest"]
        or session.get("expected_bundle_digest") != binding["bundle_digest"]
        or session.get("required_entries") != binding["required_entries"]
        or session.get("delivered_entries") != binding["required_entries"]
    ):
        raise AcceptanceBlocked("bundle closeout receipt differs")
    return {"status": "closed", "action": "bundle-close", "lane": step["lane"], "run_id": step["run_id"], "bundle_digest": binding["bundle_digest"], "required_entries": binding["required_entries"], "delivered_entries": binding["required_entries"], "command": command, "owner": receipt["owner"], "owner_receipt": dict(native)}


def _expect_publisher_receipt(receipt: Mapping[str, Any], step: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    owner_function, count_field, expected_fields = _publisher_owner_for_lane(str(step["lane"]))
    command = _publisher_command(manifest, str(step["run_id"]), str(step["lane"]))
    native = _owner_receipt(receipt, owner=f"scripts.agy_content_publisher:{owner_function}", command=command, key=owner_function, label="publisher plan-only")
    if (
        set(native) != expected_fields
        or native.get("schema_version") != publisher.SCHEMA_VERSION
        or native.get("status") != "dry-run"
        or native.get(count_field) != 0
        or native.get("ready_runs") != [step["run_id"]]
        or not isinstance(native.get("base_sha"), str)
        or re.fullmatch(r"[0-9a-f]{40}", str(native["base_sha"])) is None
        or not isinstance(native.get("release_plan"), Mapping)
    ):
        raise AcceptanceBlocked("publisher plan-only receipt differs")
    if "--dry-run" not in command or "--push" in command:
        raise AcceptanceBlocked("publisher plan-only receipt differs")
    if str(step["lane"]) == "rewrite" and (
        not isinstance(native.get("article_ids"), list)
        or not isinstance(native.get("legacy_rewrite_backlog"), Mapping)
    ):
        raise AcceptanceBlocked("publisher plan-only receipt differs")
    if str(step["lane"]) in TRANSLATION_LANES and not isinstance(native.get("replacement_plans"), list):
        raise AcceptanceBlocked("publisher plan-only receipt differs")
    return {"status": "dry-run", "action": "publisher-plan-only", "lane": step["lane"], "run_id": step["run_id"], "selector_cardinality": 1, "max_runs": 1, "command": command, "owner": receipt["owner"], "owner_receipt": dict(native)}


def _queue_drain_readback(rendered: Mapping[str, Any]) -> dict[str, Any]:
    queue_root = Path(str(rendered["manifest"]["queue_root"]))
    pending = 0
    processing = 0
    failed = 0
    for lane in LANES:
        lane_root = queue_root / "lanes" / lane
        pending += len(list((lane_root / "outbox").glob("*.json"))) if (lane_root / "outbox").exists() else 0
        processing += len(list((lane_root / "processing").glob("*.json"))) if (lane_root / "processing").exists() else 0
        failed += len(list((lane_root / "failed").glob("*.json"))) if (lane_root / "failed").exists() else 0
    if failed:
        raise AcceptanceBlocked("queue drain owner read-back differs")
    return _expect(
        {"status": "drained", "pending": pending, "processing": processing},
        {"status": "drained", "pending": 0, "processing": 0},
        "queue drain",
    )


def _publisher_owner_receipt(rendered: Mapping[str, Any], step: Mapping[str, Any]) -> dict[str, Any]:
    lane = str(step["lane"])
    owner_function, _count_field, _fields = _publisher_owner_for_lane(lane)
    command = _publisher_command(rendered["manifest"], str(step["run_id"]), lane)
    functions = {
        "new": publisher.publish_ready_runs,
        "rewrite": publisher.publish_ready_rewrite_runs,
        "i18n-new": publisher.publish_ready_translation_runs,
        "i18n-rewrite": publisher.publish_ready_translation_runs,
    }
    with _formal_env(rendered, PUBLISHER):
        native = functions[lane](
            Path(str(rendered["manifest"]["actor_root"])),
            Path(str(rendered["manifest"]["queue_root"])),
            Path(str(rendered["manifest"]["publisher_state_root"])),
            max_runs=1,
            dry_run=True,
            push=False,
            exact_run_ids=[str(step["run_id"])],
            _transaction_base_sha=str(rendered["session_plan"]["actor_sha"]),
        )
    return {"owner": f"scripts.agy_content_publisher:{owner_function}", "command": command, owner_function: native}


def _step_service_label(step: Mapping[str, Any]) -> str:
    if step["action"] in {"coordinator-cycle", "c-b-materialize"}:
        return COORDINATOR
    if step["action"] in {"runner-process-once", "bundle-close"}:
        return f"com.pantheon.agy-gemini-{step['lane']}"
    raise AcceptanceBlocked("acceptance schedule action differs")


def _step_child_command(rendered: Mapping[str, Any], step: Mapping[str, Any]) -> list[str]:
    manifest = rendered["manifest"]
    by_lane = {item["lane"]: item for item in rendered["bindings"]}
    cb_by_target = {item["target_run_id"]: item for item in rendered["session_plan"]["c_b_materializations"]}
    action = step["action"]
    if action == "coordinator-cycle": return _coordinator_command(manifest, list(step["run_ids"]))
    if action == "runner-process-once": return _runner_command(manifest, by_lane[step["lane"]])
    if action == "c-b-materialize": return _materializer_command(manifest, step, cb_by_target[step["target_run_id"]])
    if action == "bundle-close":
        binding = by_lane[step["lane"]]
        return [*_runner_command(manifest, binding)[:-5], "sealed-replay-bundle-close", "--bundle", str(binding["bundle"]), "--expected-bundle-digest", str(binding["bundle_digest"])]
    raise AcceptanceBlocked("acceptance schedule action differs")


def _wait_json(retained: RetainedFile, label: str, monotonic: Callable[[], float], sleep: Callable[[float], None]) -> dict[str, Any]:
    deadline = monotonic() + READINESS_TIMEOUT_SECONDS
    last: Exception | None = None
    while True:
        try:
            payload = json.loads(retained.read(label).decode())
            if isinstance(payload, dict) and payload.get("status") != "rejected":
                return payload
            last = AcceptanceBlocked(f"{label} owner stdout read-back differs")
        except (UnicodeDecodeError, json.JSONDecodeError, OSError) as error:
            last = error
        if monotonic() >= deadline:
            raise AcceptanceBlocked(f"{label} owner stdout read-back timeout") from last
        sleep(0.01)


def _validate_step_stdout(rendered: Mapping[str, Any], step: Mapping[str, Any], command: list[str], native: dict[str, Any]) -> dict[str, Any]:
    manifest = rendered["manifest"]
    by_lane = {item["lane"]: item for item in rendered["bindings"]}
    cb_by_target = {item["target_run_id"]: item for item in rendered["session_plan"]["c_b_materializations"]}
    action = step["action"]
    if action == "coordinator-cycle": return _expect_coordinator_receipt({"owner":"scripts.agy_gemini_coordinator:cycle_once","command":command,"cycle_once":native}, step, manifest)
    if action == "runner-process-once":
        binding = by_lane[step["lane"]]
        return _expect_runner_receipt({"owner":"scripts.agy_gemini_runner:sealed_replay_bundle_process_once","command":command,"sealed_replay_bundle_process_once":native}, step, manifest, binding)
    if action == "c-b-materialize":
        pins = cb_by_target[step["target_run_id"]]
        return _expect_materialization_receipt({"owner":"scripts.agy_gemini_coordinator:materialize_translation_pending_dependency","command":command,"materialize_translation_pending_dependency":native}, step, manifest, pins)
    if action == "bundle-close":
        binding = by_lane[step["lane"]]
        return _expect_bundle_close_receipt({"owner":"scripts.agy_gemini_runner:sealed_replay_bundle_close","command":command,"sealed_replay_bundle_close":native}, step, manifest, binding)
    raise AcceptanceBlocked("acceptance schedule action differs")


def _execute_schedule(rendered: Mapping[str, Any]) -> list[dict[str, Any]]:
    raise AcceptanceBlocked("direct workload schedule is disabled; launchd step ownership required")


def _read_back_schedule(authority: ContinuousAuthority, monotonic: Callable[[], float], sleep: Callable[[float], None]) -> list[dict[str, Any]]:
    rendered = authority.rendered
    receipts: list[dict[str, Any]] = []
    for index, step in enumerate(rendered["session_plan"]["phase_schedule"]):
        authority.verify_baseline()
        _revalidate_rendered_plan(rendered)
        if step["action"] == "publisher-plan-only":
            receipts.append(_expect_publisher_receipt(_publisher_owner_receipt(rendered, step), step, rendered["manifest"]))
            continue
        if step["action"] == "queue-drain":
            receipts.append(_queue_drain_readback(rendered))
            continue
        label = _step_service_label(step)
        command = _step_child_command(rendered, step)
        plist, stdout, stderr = authority.create_step(index, label, command)
        _launchctl_print_absent(label, "step-preflight-print", plist.path, rendered["manifest"])
        launch = _launch_retained(authority, label, plist, "step")
        native = _wait_json(stdout, "step stdout", monotonic, sleep)
        stdout.verify("step stdout")
        stderr.verify("step stderr")
        receipt = _validate_step_stdout(rendered, step, command, native)
        drift_count = len(authority.drift_evidence)
        bootout = authority.release(label, attempts=TEARDOWN_ATTEMPTS)
        if bootout is None:
            raise AcceptanceBlocked("step bootout terminal proof failed")
        if len(authority.drift_evidence) != drift_count:
            raise AcceptanceBlocked("step teardown authority drift")
        receipt["launchd_invocation"] = {"service_label":label,"plist_path":str(plist.path),"plist_digest":plist.digest,"launch":launch,"bootout":bootout}
        receipts.append(receipt)
    return receipts


def _print_retained_absent(label: str, phase: str, artifact: RetainedFile, manifest: Mapping[str, Any], *, verify_artifact: bool = True) -> dict[str, Any]:
    if verify_artifact:
        artifact.verify("launch plist")
    command = [LAUNCHCTL, "print", f"gui/{os.getuid()}/{label}"]
    completed = _run_process(command)
    if completed.returncode != 113:
        raise AcceptanceBlocked("launchctl print receipt differs")
    return _print_not_found_expectation(label, phase, artifact.path, manifest, artifact.digest)


def _baseline_completion(
    authority: ContinuousAuthority,
    label: str,
    barrier_stat: os.stat_result,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    stdout, stderr = authority.baseline_outputs[label]
    native = _wait_json(stdout, "baseline activation stdout", monotonic, sleep)
    expected = {"status":"PASS","activation_only":True,"service_label":label,"manifest_digest":authority.rendered["manifest"]["manifest_digest"],"generation":authority.rendered["manifest"]["generation"]}
    if native != expected or stderr.read("baseline activation stderr") != b"":
        raise AcceptanceBlocked("baseline activation completion differs")
    info = os.fstat(stdout.descriptor)
    if info.st_mtime_ns <= barrier_stat.st_mtime_ns:
        raise AcceptanceBlocked("baseline activation completion predates barrier")
    return {"label":label,"stdout_path":str(stdout.path),"stdout_digest":stdout.content_digest("baseline activation stdout"),**expected}


def run_once(
    rendered: Mapping[str, Any],
    *,
    monotonic: Callable[[],float]=time.monotonic,
    sleep: Callable[[float],None]=time.sleep,
) -> dict[str, Any]:
    root = _canonical_dir(Path(rendered["acceptance_root"]), "acceptance root")
    plan, plan_digest = _revalidate_rendered_plan(rendered)
    generation = str(plan["generation"])
    ready, barrier, lock, evidence = Path(rendered["ready_root"]), Path(rendered["barrier"]), Path(rendered["lock"]), Path(rendered["evidence_root"])
    if ready != root / "readiness" / generation or barrier != root / "barriers" / f"{generation}.json" or lock != root / "locks" / f"{generation}.lock" or evidence != root / "evidence" / generation:
        raise AcceptanceBlocked("acceptance session authority differs")
    _consumed_marker(rendered, plan)
    if ready.exists() or barrier.exists() or lock.exists() or evidence.exists():
        raise AcceptanceBlocked("acceptance generation residue exists before launch")
    primary: Exception | None = None
    result: dict[str, Any] | None = None
    unknown: list[str] = []
    with ContinuousAuthority(rendered) as authority:
        preflight_prints = [_print_retained_absent(label, "preflight-print", authority.baseline[label], rendered["manifest"]) for label in SERVICE_LABELS]
        before = production_fingerprint(rendered["production_paths"], lambda: _production_service_state(authority))
        os.close(os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600))
        launch_receipts: list[dict[str, Any]] = []
        bootouts: list[dict[str, Any]] = []
        try:
            for label in SERVICE_LABELS:
                authority.verify_baseline()
                _revalidate_rendered_plan(rendered)
                launch_receipts.append(_launch_retained(authority, label, authority.baseline[label], "baseline"))
            deadline = monotonic() + READINESS_TIMEOUT_SECONDS
            while any(not (ready/f"{label}.json").is_file() for label in SERVICE_LABELS):
                authority.verify_baseline()
                if monotonic() >= deadline: raise AcceptanceBlocked("readiness timeout")
                sleep(0.01)
            if {path.name for path in ready.iterdir()} != {f"{label}.json" for label in SERVICE_LABELS}:
                raise AcceptanceBlocked("readiness acknowledgement set differs")
            authority.verify_baseline()
            activation = runtime.activate_barrier(barrier,ready,dict(rendered["manifest"]))
            barrier_stat = barrier.stat()
            baseline_completions = [_baseline_completion(authority, label, barrier_stat, monotonic, sleep) for label in SERVICE_LABELS]
            for label in reversed(SERVICE_LABELS):
                receipt = authority.release(label, attempts=TEARDOWN_ATTEMPTS)
                if receipt is None: raise AcceptanceBlocked("baseline bootout terminal proof failed")
                bootouts.append(receipt)
            workload_receipts = _read_back_schedule(authority, monotonic, sleep)
            result={"status":"PASS","activation_token_digest":runtime.validate_barrier(barrier,dict(rendered["manifest"]))["activation_token_digest"],"ack_digests":[item["ack_digest"] for item in activation["acknowledgements"]],"baseline_activation_completions":baseline_completions,"preflight_prints":preflight_prints,"launchctl_receipts":launch_receipts,"workload_receipts":workload_receipts,"launched":list(SERVICE_LABELS),"bootouts":bootouts,"final_prints":[]}
        except Exception as error:
            primary = error
        for label in list(reversed(tuple(authority.loaded))):
            authority.release(label, attempts=TEARDOWN_ATTEMPTS)
        if authority.loaded:
            raise AcceptanceBlocked("acceptance bootout proof failed: " + authority.loaded_evidence()) from primary
        final_prints = [_print_retained_absent(label, "final-print", authority.baseline[label], rendered["manifest"], verify_artifact=False) for label in SERVICE_LABELS]
        if result is not None: result["final_prints"].extend(final_prints)
        known_ready={f"{label}.json" for label in SERVICE_LABELS}
        unknown=[] if not ready.exists() else [path.name for path in ready.iterdir() if path.name not in known_ready]
        if primary is None and not authority.drift_evidence:
            for name in known_ready:
                with suppress(FileNotFoundError): (ready/name).unlink()
            if ready.exists() and not unknown:
                with suppress(OSError): ready.rmdir()
            for path in (barrier,lock):
                with suppress(FileNotFoundError): path.unlink()
            if not authority.cleanup_generation(): unknown.append("plists")
        after=production_fingerprint(rendered["production_paths"],lambda: _production_service_state(authority))
        if authority.drift_evidence:
            raise AcceptanceBlocked("acceptance authority drift evidence: " + json.dumps(authority.drift_evidence, sort_keys=True)) from primary
        if primary is not None:
            raise primary
        if not result or len(result["bootouts"])!=7 or len(result["final_prints"])!=7 or unknown or before!=after or evidence.exists():
            raise AcceptanceBlocked("acceptance teardown or fingerprint proof failed")
    _revalidate_rendered_plan(rendered)
    receipt={**result,"session_id":plan["session_id"],"session_nonce_digest":plan["session_nonce_digest"],"session_plan_path":str(rendered["session_plan_path"]),"session_plan_digest":plan_digest,"actor_sha":plan["actor_sha"],"exact_runs":plan["exact_runs"],"publisher_activation_run_id":plan["publisher_activation_run_id"],"publisher_plan_only":plan["publisher_plan_only"],"service_labels":list(SERVICE_LABELS),"before_fingerprint":before,"after_fingerprint":after,"production_root_identities":before["root_identities"],"production_root_identities_digest":before["root_identities_digest"],"teardown_terminal":True,"residue_free":True,"manifest_digest":rendered["manifest"]["manifest_digest"],"generation":rendered["manifest"]["generation"],"runtime_identity_digest":rendered["manifest"]["runtime_identity_digest"]}
    evidence.mkdir(mode=0o700)
    output=evidence/"one-shot-session-receipt.json"
    _write_json_exclusive(output, receipt)
    _fsync_directory(evidence)
    return receipt

#!/usr/bin/env python3
"""建立並驗證 Pantheon 四軌共用 runtime identity manifest。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any


SCHEMA_VERSION = 2
REGRESSION_ID = "REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001"
SERVICE_LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.content-capacity-guard",
)
PATH_FIELDS = ("actor_root", "queue_root", "publisher_state_root", "log_root")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
GENERATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class RuntimeManifestError(ValueError):
    """共用 runtime manifest 不完整或 identity 漂移。"""


def _canonical_directory(path: Path, field: str) -> str:
    if not path.is_absolute():
        raise RuntimeManifestError(f"{field} must be absolute")
    if not path.exists() or not path.is_dir():
        raise RuntimeManifestError(f"{field} is missing")
    resolved = path.resolve(strict=True)
    if path != resolved:
        raise RuntimeManifestError(f"{field} must use its canonical realpath")
    if path.is_symlink():
        raise RuntimeManifestError(f"{field} must not be a symlink alias")
    return str(resolved)


def _canonical_executable(path: Path, field: str) -> str:
    if not path.is_absolute():
        raise RuntimeManifestError(f"{field} must be absolute")
    if not path.exists() or not path.is_file():
        raise RuntimeManifestError(f"{field} is missing")
    resolved = path.resolve(strict=True)
    if path != resolved:
        raise RuntimeManifestError(f"{field} must use its canonical realpath")
    if path.is_symlink() or not os.access(resolved, os.X_OK):
        raise RuntimeManifestError(f"{field} must be an executable regular file")
    return str(resolved)


def _resolve_executable_reference(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeManifestError(f"{field} is missing")
    path = Path(value)
    if not path.is_absolute():
        raise RuntimeManifestError(f"{field} must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise RuntimeManifestError(f"{field} is missing") from error
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise RuntimeManifestError(f"{field} must be an executable regular file")
    return str(resolved)


def _git_output(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RuntimeManifestError("actor git validation failed") from error
    if completed.returncode != 0:
        raise RuntimeManifestError("actor git command failed")
    return completed.stdout.strip()


def _validate_actor_head(actor_root: Path, expected_head: str) -> None:
    try:
        toplevel = Path(
            _git_output(actor_root, "rev-parse", "--show-toplevel")
        ).resolve(strict=True)
    except RuntimeManifestError as error:
        if str(error) == "actor git validation failed":
            raise
        raise RuntimeManifestError("actor root must be a git worktree") from error
    if toplevel != actor_root:
        raise RuntimeManifestError("actor root must be a git worktree")
    actual_head = _git_output(actor_root, "rev-parse", "HEAD")
    if actual_head != expected_head:
        raise RuntimeManifestError("runtime actor head drift")
    if _git_output(actor_root, "status", "--porcelain") != "":
        raise RuntimeManifestError("runtime actor worktree is dirty")


def _manifest_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _runtime_identity_digest(payload: dict[str, Any]) -> str:
    identity = {
        "schema_version": payload["schema_version"],
        "identity": payload["identity"],
        "runtime_digest": payload["runtime_digest"],
        "config_version": payload["config_version"],
        "generation": payload["generation"],
        **{field: payload[field] for field in PATH_FIELDS},
    }
    for field in ("actor_head", "python_executable"):
        if field in payload:
            identity[field] = payload[field]
    return _manifest_digest(identity)


def build_manifest(
    *,
    actor_root: Path,
    queue_root: Path,
    publisher_state_root: Path,
    log_root: Path,
    identity: str,
    runtime_digest: str | None = None,
    config_version: str = "runtime-v2",
    generation: str = "legacy-generation",
    actor_head: str | None = None,
    python_executable: Path | None = None,
) -> dict[str, Any]:
    if not identity or identity.strip() != identity:
        raise RuntimeManifestError("identity is required")
    effective_runtime_digest = runtime_digest or hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()
    if SHA256_PATTERN.fullmatch(effective_runtime_digest) is None:
        raise RuntimeManifestError("runtime digest must be exact sha256")
    if not config_version or config_version.strip() != config_version:
        raise RuntimeManifestError("config version is required")
    if GENERATION_PATTERN.fullmatch(generation) is None:
        raise RuntimeManifestError("generation is invalid")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "identity": identity,
        "runtime_digest": effective_runtime_digest,
        "config_version": config_version,
        "generation": generation,
        "owner_uid": os.stat(actor_root).st_uid,
        "actor_root": _canonical_directory(actor_root, "actor_root"),
        "queue_root": _canonical_directory(queue_root, "queue_root"),
        "publisher_state_root": _canonical_directory(
            publisher_state_root, "publisher_state_root"
        ),
        "log_root": _canonical_directory(log_root, "log_root"),
        "service_labels": list(SERVICE_LABELS),
    }
    if actor_head is not None:
        if SHA1_PATTERN.fullmatch(actor_head) is None:
            raise RuntimeManifestError("actor head must be exact git sha")
        payload["actor_head"] = actor_head
    if python_executable is not None:
        payload["python_executable"] = _canonical_executable(
            python_executable,
            "python_executable",
        )
    payload["runtime_identity_digest"] = _runtime_identity_digest(payload)
    payload["manifest_digest"] = _manifest_digest(payload)
    return payload


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        body = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
        os.write(descriptor, body)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def load_manifest(
    path: Path,
    expected_digest: str | None = None,
    *,
    expected_python_executable: Path | None = None,
) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as error:
        raise RuntimeManifestError("runtime manifest is unavailable") from error
    if not isinstance(payload, dict):
        raise RuntimeManifestError("runtime manifest must be an object")
    digest = str(payload.pop("manifest_digest", ""))
    if payload.get("schema_version") != SCHEMA_VERSION or digest != _manifest_digest(payload):
        raise RuntimeManifestError("runtime manifest digest mismatch")
    if expected_digest is not None and digest != expected_digest:
        raise RuntimeManifestError("runtime manifest expected digest mismatch")
    payload["manifest_digest"] = digest
    for field in PATH_FIELDS:
        if _canonical_directory(Path(str(payload.get(field, ""))), field) != payload[field]:
            raise RuntimeManifestError(f"{field} identity mismatch")
    if payload.get("service_labels") != list(SERVICE_LABELS):
        raise RuntimeManifestError("service label allowlist mismatch")
    if SHA256_PATTERN.fullmatch(str(payload.get("runtime_digest", ""))) is None:
        raise RuntimeManifestError("runtime digest is invalid")
    if GENERATION_PATTERN.fullmatch(str(payload.get("generation", ""))) is None:
        raise RuntimeManifestError("runtime generation is invalid")
    actor_root = Path(str(payload["actor_root"]))
    if "actor_head" in payload:
        actor_head = str(payload["actor_head"])
        if SHA1_PATTERN.fullmatch(actor_head) is None:
            raise RuntimeManifestError("runtime actor head is invalid")
        _validate_actor_head(actor_root, actor_head)
    if "python_executable" in payload:
        if _canonical_executable(
            Path(str(payload["python_executable"])),
            "python_executable",
        ) != payload["python_executable"]:
            raise RuntimeManifestError("runtime python executable mismatch")
    if expected_python_executable is not None and "python_executable" in payload:
        expected_python = _canonical_executable(
            expected_python_executable,
            "expected_python_executable",
        )
        if payload["python_executable"] != expected_python:
            raise RuntimeManifestError("runtime python executable drift")
    identity_digest = str(payload.get("runtime_identity_digest", ""))
    if identity_digest != _runtime_identity_digest(payload):
        raise RuntimeManifestError("runtime identity digest mismatch")
    return payload


def receipt_for_label(manifest: dict[str, Any], label: str) -> dict[str, Any]:
    if label not in SERVICE_LABELS:
        raise RuntimeManifestError("service label is not registered")
    receipt = {
        "label": label,
        "service_label": label,
        "identity": manifest["identity"],
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "runtime_digest": manifest["runtime_digest"],
        "config_version": manifest["config_version"],
        "generation": manifest["generation"],
        **{field: manifest[field] for field in PATH_FIELDS},
    }
    for field in ("actor_head", "python_executable"):
        if field in manifest:
            receipt[field] = manifest[field]
    return receipt


def validate_receipts(
    manifest: dict[str, Any], receipts: list[dict[str, Any]]
) -> dict[str, Any]:
    seen: set[str] = set()
    for receipt in receipts:
        label = str(receipt.get("label", ""))
        if label not in SERVICE_LABELS or label in seen:
            raise RuntimeManifestError("receipt label is missing, duplicated, or unregistered")
        seen.add(label)
        expected = receipt_for_label(manifest, label)
        for field, value in expected.items():
            if receipt.get(field) != value:
                raise RuntimeManifestError(f"{label} {field} mismatch")
    if seen != set(SERVICE_LABELS):
        raise RuntimeManifestError("runtime receipts are incomplete")
    return {"status": "PASS", "manifest_digest": manifest["manifest_digest"]}


def plist_receipt(
    path: Path,
    *,
    expected_activation_mode: str = "normal",
) -> dict[str, Any]:
    if expected_activation_mode not in {"normal", "activation-only"}:
        raise RuntimeManifestError("unsupported activation mode")
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RuntimeManifestError("plist must be an absolute regular file")
    canonical = path.resolve(strict=True)
    if canonical != path or os.stat(canonical).st_uid != os.getuid():
        raise RuntimeManifestError("plist canonical realpath or owner mismatch")
    if stat.S_IMODE(os.stat(canonical).st_mode) != 0o600:
        raise RuntimeManifestError("plist mode must be 0600")
    try:
        with canonical.open("rb") as stream:
            payload = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException) as error:
        raise RuntimeManifestError("plist is unreadable") from error
    environment = payload.get("EnvironmentVariables")
    if not isinstance(environment, dict):
        raise RuntimeManifestError("plist runtime environment is missing")
    receipt = {
        "label": payload.get("Label"),
        "service_label": environment.get("PANTHEON_RUNTIME_SERVICE_LABEL"),
        "identity": environment.get("PANTHEON_RUNTIME_IDENTITY"),
        "manifest_digest": environment.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
        "runtime_identity_digest": environment.get(
            "PANTHEON_RUNTIME_IDENTITY_DIGEST"
        ),
        "runtime_digest": environment.get("PANTHEON_RUNTIME_CODE_DIGEST"),
        "config_version": environment.get("PANTHEON_RUNTIME_CONFIG_VERSION"),
        "generation": environment.get("PANTHEON_RUNTIME_GENERATION"),
        "actor_root": environment.get("PANTHEON_RUNTIME_ACTOR_ROOT"),
        "queue_root": environment.get("PANTHEON_RUNTIME_QUEUE_ROOT"),
        "publisher_state_root": environment.get("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"),
        "log_root": environment.get("PANTHEON_RUNTIME_LOG_ROOT"),
        "plist_realpath": str(canonical),
    }
    optional_environment_fields = {
        "actor_head": "PANTHEON_RUNTIME_ACTOR_HEAD",
        "python_executable": "PANTHEON_RUNTIME_PYTHON_EXECUTABLE",
    }
    for field, environment_name in optional_environment_fields.items():
        if environment_name in environment:
            receipt[field] = environment[environment_name]
    arguments = payload.get("ProgramArguments")
    activation_only_argument = False
    if isinstance(arguments, list):
        try:
            child_separator_index = arguments.index("--")
        except ValueError:
            child_separator_index = len(arguments)
        activation_only_argument = "--activation-only" in arguments[:child_separator_index]
    if expected_activation_mode == "normal" and activation_only_argument:
        raise RuntimeManifestError("plist activation mode mismatch")
    if expected_activation_mode == "activation-only" and not activation_only_argument:
        raise RuntimeManifestError("plist activation mode mismatch")
    receipt["activation_mode"] = (
        "activation-only" if activation_only_argument else "normal"
    )
    if "python_executable" in receipt:
        if not isinstance(arguments, list) or len(arguments) <= 17:
            raise RuntimeManifestError("plist python_executable arguments are incomplete")
        separator_index = 16
        if len(arguments) > 17 and arguments[16] == "--activation-only":
            separator_index = 17
        if arguments[1:4] != [
            "-m",
            "scripts.pantheon_content_runtime_manifest",
            "barrier-exec",
        ] or len(arguments) <= separator_index + 1 or arguments[separator_index] != "--":
            raise RuntimeManifestError("plist barrier-exec arguments are invalid")
        outer_python = _resolve_executable_reference(
            arguments[0],
            "plist python_executable",
        )
        child_python = _resolve_executable_reference(
            arguments[separator_index + 1],
            "plist python_executable",
        )
        expected_python = _resolve_executable_reference(
            receipt["python_executable"],
            "plist python_executable",
        )
        if outer_python != expected_python or child_python != expected_python:
            raise RuntimeManifestError("plist python_executable mismatch")
        receipt["program_python_executable"] = outer_python
        receipt["barrier_child_python_executable"] = child_python
    if payload.get("WorkingDirectory") != receipt["actor_root"]:
        raise RuntimeManifestError("plist working directory actor mismatch")
    return receipt


def aggregate_plist_preflight(
    manifest: dict[str, Any],
    plist_paths: list[Path],
    *,
    expected_activation_mode: str = "normal",
) -> dict[str, Any]:
    receipts = [
        plist_receipt(path, expected_activation_mode=expected_activation_mode)
        for path in plist_paths
    ]
    result = validate_receipts(
        manifest,
        [{key: value for key, value in receipt.items() if key != "plist_realpath"} for receipt in receipts],
    )
    return {**result, "receipts": receipts}


def validate_runtime_tick(
    service_label: str,
    *,
    queue_root: Path,
    state_root: Path,
    actor_root: Path | None = None,
    log_root: Path | None = None,
    require_activation_token: bool = True,
) -> dict[str, Any]:
    """正式服務每次 tick 在任何 queue/state I/O 前驗證 runtime identity。"""
    if os.environ.get("PANTHEON_FORMAL_RUNTIME") != "1":
        return {"status": "SKIPPED", "service_label": service_label}
    manifest_path = Path(os.environ.get("PANTHEON_RUNTIME_MANIFEST", ""))
    expected_digest = os.environ.get("PANTHEON_RUNTIME_MANIFEST_DIGEST", "")
    expected_generation = os.environ.get("PANTHEON_RUNTIME_GENERATION", "")
    expected_identity_digest = os.environ.get(
        "PANTHEON_RUNTIME_IDENTITY_DIGEST", ""
    )
    configured_label = os.environ.get("PANTHEON_RUNTIME_SERVICE_LABEL", "")
    if (
        not manifest_path.is_absolute()
        or SHA256_PATTERN.fullmatch(expected_digest) is None
        or GENERATION_PATTERN.fullmatch(expected_generation) is None
        or SHA256_PATTERN.fullmatch(expected_identity_digest) is None
        or configured_label != service_label
    ):
        raise RuntimeManifestError("formal runtime environment is incomplete")
    manifest = load_manifest(manifest_path, expected_digest)
    expected_environment = {
        "PANTHEON_RUNTIME_SERVICE_LABEL": service_label,
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest["publisher_state_root"],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
    }
    for field, environment_name in (
        ("actor_head", "PANTHEON_RUNTIME_ACTOR_HEAD"),
        ("python_executable", "PANTHEON_RUNTIME_PYTHON_EXECUTABLE"),
    ):
        if field in manifest:
            expected_environment[environment_name] = manifest[field]
    if any(os.environ.get(key) != value for key, value in expected_environment.items()):
        raise RuntimeManifestError("formal runtime generation or identity mismatch")
    if service_label not in SERVICE_LABELS:
        raise RuntimeManifestError("formal runtime service label is unregistered")
    expected_queue = Path(manifest["queue_root"])
    if service_label.startswith("com.pantheon.agy-gemini-") and service_label != SERVICE_LABELS[1]:
        lane = service_label.removeprefix("com.pantheon.agy-gemini-")
        expected_queue = expected_queue / "lanes" / lane
    expected_paths = {
        "queue_root": expected_queue,
        "publisher_state_root": Path(manifest["publisher_state_root"]),
    }
    actual_paths = {
        "queue_root": queue_root,
        "publisher_state_root": state_root,
    }
    if actor_root is not None:
        expected_paths["actor_root"] = Path(manifest["actor_root"])
        actual_paths["actor_root"] = actor_root
    if log_root is not None:
        expected_paths["log_root"] = Path(manifest["log_root"])
        actual_paths["log_root"] = log_root
    for field, expected in expected_paths.items():
        actual = actual_paths[field]
        if actual.resolve() != expected.resolve():
            raise RuntimeManifestError(f"formal runtime {field} mismatch")
    activation_token = os.environ.get("PANTHEON_RUNTIME_ACTIVATION_TOKEN", "")
    if not activation_token:
        if not require_activation_token:
            return {"status": "PASS", **receipt_for_label(manifest, service_label)}
        raise RuntimeManifestError("formal runtime activation token is required")
    token_path = Path(activation_token)
    if not token_path.is_absolute():
        raise RuntimeManifestError("formal runtime activation token is invalid")
    from scripts import pantheon_runtime_activation

    try:
        pantheon_runtime_activation.validate_token_payload(
            token_path,
            manifest,
        )
    except pantheon_runtime_activation.RuntimeActivationError as error:
        raise RuntimeManifestError(str(error)) from error
    return {"status": "PASS", **receipt_for_label(manifest, service_label)}


def _read_private_json(path: Path, message: str) -> dict[str, Any]:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RuntimeManifestError(message)
    try:
        if path.resolve(strict=True) != path:
            raise RuntimeManifestError(message)
        metadata = os.stat(path)
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RuntimeManifestError(message)
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeManifestError(message) from error
    if not isinstance(payload, dict):
        raise RuntimeManifestError(message)
    return payload


def write_readiness_ack(
    ready_root: Path,
    manifest: dict[str, Any],
    service_label: str,
) -> dict[str, Any]:
    receipt = receipt_for_label(manifest, service_label)
    acknowledgement = {
        "schema_version": SCHEMA_VERSION,
        "service_label": service_label,
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "owner_uid": os.getuid(),
    }
    acknowledgement["ack_digest"] = _manifest_digest(acknowledgement)
    write_manifest(ready_root / f"{service_label}.json", acknowledgement)
    return {**receipt, **acknowledgement}


def _load_readiness_ack(
    path: Path,
    manifest: dict[str, Any],
    service_label: str,
) -> dict[str, Any]:
    acknowledgement = _read_private_json(path, "readiness acknowledgement is invalid")
    digest = str(acknowledgement.pop("ack_digest", ""))
    expected = {
        "schema_version": SCHEMA_VERSION,
        "service_label": service_label,
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "owner_uid": os.getuid(),
    }
    if acknowledgement != expected or digest != _manifest_digest(expected):
        raise RuntimeManifestError("readiness acknowledgement identity mismatch")
    return {**acknowledgement, "ack_digest": digest}


def activate_barrier(
    barrier_path: Path,
    ready_root: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if any(
        not (ready_root / f"{label}.json").is_file() for label in SERVICE_LABELS
    ):
        raise RuntimeManifestError("readiness acknowledgements are incomplete")
    acknowledgements = [
        _load_readiness_ack(
            ready_root / f"{label}.json",
            manifest,
            label,
        )
        for label in SERVICE_LABELS
    ]
    if len(acknowledgements) != len(SERVICE_LABELS):
        raise RuntimeManifestError("readiness acknowledgements are incomplete")
    barrier = {
        "schema_version": SCHEMA_VERSION,
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "owner_uid": os.getuid(),
        "service_labels": list(SERVICE_LABELS),
        "ack_digests": [item["ack_digest"] for item in acknowledgements],
    }
    write_manifest(barrier_path, barrier)
    return {
        "status": "PASS",
        "barrier": str(barrier_path),
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "acknowledgements": acknowledgements,
    }


def validate_barrier(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    payload = _read_private_json(path, "activation barrier is invalid")
    expected = {
        "schema_version": SCHEMA_VERSION,
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "owner_uid": os.getuid(),
        "service_labels": list(SERVICE_LABELS),
    }
    if any(payload.get(field) != value for field, value in expected.items()):
        raise RuntimeManifestError("activation barrier identity mismatch")
    digests = payload.get("ack_digests")
    if not isinstance(digests, list) or len(digests) != len(SERVICE_LABELS) or any(
        SHA256_PATTERN.fullmatch(str(value)) is None for value in digests
    ):
        raise RuntimeManifestError("activation barrier acknowledgements are incomplete")
    return {
        "status": "PASS",
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
    }


def validate_execution_python_identity(
    manifest: dict[str, Any], command: list[str]
) -> None:
    if "python_executable" not in manifest:
        return
    expected = str(manifest["python_executable"])
    runtime_python = _resolve_executable_reference(
        sys.executable,
        "runtime python_executable",
    )
    child_python = _resolve_executable_reference(
        command[0] if command else "",
        "child python_executable",
    )
    if runtime_python != expected or child_python != expected:
        raise RuntimeManifestError("runtime python_executable drift")


def validate_rollback_identities(
    expected: dict[str, dict[str, Any]],
    actual: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if set(expected) != set(SERVICE_LABELS) or set(actual) != set(SERVICE_LABELS):
        raise RuntimeManifestError("ROLLBACK_FAILED: service identity set mismatch")
    for label in SERVICE_LABELS:
        expected_identity = expected[label]
        actual_identity = actual[label]
        if actual_identity != expected_identity:
            raise RuntimeManifestError(f"ROLLBACK_FAILED: {label} identity mismatch")
        if type(actual_identity.get("loaded")) is not bool or any(
            SHA256_PATTERN.fullmatch(str(actual_identity.get(field, ""))) is None
            for field in ("config_digest", "control_identity_digest")
        ):
            raise RuntimeManifestError(f"ROLLBACK_FAILED: {label} identity invalid")
    return {"status": "PASS", "services": list(SERVICE_LABELS)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--actor-root", type=Path, required=True)
    create.add_argument("--queue-root", type=Path, required=True)
    create.add_argument("--publisher-state-root", type=Path, required=True)
    create.add_argument("--log-root", type=Path, required=True)
    create.add_argument("--identity", required=True)
    create.add_argument("--runtime-digest", required=True)
    create.add_argument("--config-version", required=True)
    create.add_argument("--generation", required=True)
    create.add_argument("--actor-head", required=True)
    create.add_argument("--python-executable", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    field = subparsers.add_parser("field")
    field.add_argument("--manifest", type=Path, required=True)
    field.add_argument("--expected-digest", required=True)
    field.add_argument(
        "--name",
        choices=(
            *PATH_FIELDS,
            "identity",
            "manifest_digest",
            "runtime_identity_digest",
            "runtime_digest",
            "config_version",
            "generation",
            "actor_head",
            "python_executable",
        ),
        required=True,
    )
    field.add_argument("--optional", action="store_true")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--expected-digest", required=True)
    validate.add_argument("--expected-python-executable", type=Path)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--manifest", type=Path, required=True)
    aggregate.add_argument("--expected-digest", required=True)
    aggregate.add_argument(
        "--activation-mode",
        choices=["normal", "activation-only"],
        default="normal",
    )
    aggregate.add_argument("--plist", type=Path, action="append", required=True)
    barrier = subparsers.add_parser("barrier-exec")
    barrier.add_argument("--barrier", type=Path, required=True)
    barrier.add_argument("--expected-digest", required=True)
    barrier.add_argument("--manifest", type=Path)
    barrier.add_argument("--service-label", choices=SERVICE_LABELS)
    barrier.add_argument("--ready-root", type=Path)
    barrier.add_argument("--timeout", type=int, default=90)
    barrier.add_argument("--activation-only", action="store_true")
    barrier.add_argument("remainder", nargs=argparse.REMAINDER)
    barrier_validate = subparsers.add_parser("barrier-validate")
    barrier_validate.add_argument("--barrier", type=Path, required=True)
    barrier_validate.add_argument("--manifest", type=Path, required=True)
    barrier_validate.add_argument("--expected-digest", required=True)
    activate = subparsers.add_parser("barrier-activate")
    activate.add_argument("--manifest", type=Path, required=True)
    activate.add_argument("--expected-digest", required=True)
    activate.add_argument("--ready-root", type=Path, required=True)
    activate.add_argument("--barrier", type=Path, required=True)
    activate.add_argument("--timeout", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "barrier-activate":
        try:
            manifest = load_manifest(args.manifest, args.expected_digest)
            if not 1 <= args.timeout <= 300:
                raise RuntimeManifestError("activation timeout is invalid")
            deadline = time.monotonic() + args.timeout
            while any(
                not (args.ready_root / f"{label}.json").is_file()
                for label in SERVICE_LABELS
            ):
                if time.monotonic() >= deadline:
                    raise RuntimeManifestError("readiness acknowledgements are incomplete")
                time.sleep(0.2)
            print(
                json.dumps(
                    activate_barrier(args.barrier, args.ready_root, manifest),
                    sort_keys=True,
                )
            )
            return 0
        except RuntimeManifestError as error:
            print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
            return 1
    if args.command == "barrier-validate":
        try:
            manifest = load_manifest(args.manifest, args.expected_digest)
            result = validate_barrier(args.barrier, manifest)
            print(json.dumps(result, sort_keys=True))
            return 0
        except RuntimeManifestError as error:
            print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
            return 1
    if args.command == "barrier-exec":
        command = list(args.remainder)
        if command[:1] == ["--"]:
            command = command[1:]
        if (
            not command
            or not args.barrier.is_absolute()
            or not 1 <= args.timeout <= 300
        ):
            return 64
        if args.manifest is None or args.service_label is None or args.ready_root is None:
            return 78
        if not args.ready_root.is_absolute():
            return 64
        try:
            manifest = load_manifest(args.manifest, args.expected_digest)
            validate_runtime_tick(
                args.service_label,
                queue_root=(
                    Path(manifest["queue_root"])
                    / "lanes"
                    / args.service_label.removeprefix("com.pantheon.agy-gemini-")
                    if args.service_label.startswith("com.pantheon.agy-gemini-")
                    and args.service_label != "com.pantheon.agy-gemini-coordinator"
                    else Path(manifest["queue_root"])
                ),
                state_root=Path(manifest["publisher_state_root"]),
                actor_root=Path(manifest["actor_root"]),
                log_root=Path(manifest["log_root"]),
                require_activation_token=False,
            )
            validate_execution_python_identity(manifest, command)
            write_readiness_ack(args.ready_root, manifest, args.service_label)
        except RuntimeManifestError:
            return 78
        deadline = time.monotonic() + args.timeout
        while not args.barrier.exists():
            if time.monotonic() >= deadline:
                return 75
            time.sleep(0.2)
        try:
            validate_barrier(args.barrier, manifest)
            validate_execution_python_identity(manifest, command)
        except RuntimeManifestError:
            return 78
        os.environ["PANTHEON_RUNTIME_ACTIVATION_TOKEN"] = str(args.barrier)
        if args.activation_only:
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "activation_only": True,
                        "service_label": args.service_label,
                        "manifest_digest": manifest["manifest_digest"],
                        "generation": manifest["generation"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        os.execv(command[0], command)
        return 70
    try:
        if args.command == "create":
            manifest = build_manifest(
                actor_root=args.actor_root,
                queue_root=args.queue_root,
                publisher_state_root=args.publisher_state_root,
                log_root=args.log_root,
                identity=args.identity,
                runtime_digest=args.runtime_digest,
                config_version=args.config_version,
                generation=args.generation,
                actor_head=args.actor_head,
                python_executable=args.python_executable,
            )
            write_manifest(args.output, manifest)
            print(json.dumps(manifest, sort_keys=True))
        else:
            manifest = load_manifest(
                args.manifest,
                args.expected_digest,
                expected_python_executable=(
                    args.expected_python_executable
                    if args.command == "validate"
                    else None
                ),
            )
            if args.command == "field":
                if args.name not in manifest:
                    if args.optional and args.name in (
                        "actor_head",
                        "python_executable",
                    ):
                        return 0
                    raise RuntimeManifestError(f"{args.name} is missing")
                print(manifest[args.name])
            elif args.command == "aggregate":
                print(
                    json.dumps(
                        aggregate_plist_preflight(
                            manifest,
                            args.plist,
                            expected_activation_mode=args.activation_mode,
                        ),
                        sort_keys=True,
                    )
                )
            else:
                print(json.dumps({"status": "PASS", **manifest}, sort_keys=True))
    except RuntimeManifestError as error:
        print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

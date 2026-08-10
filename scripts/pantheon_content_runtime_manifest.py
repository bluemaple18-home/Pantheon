#!/usr/bin/env python3
"""建立並驗證 Pantheon 四軌共用 runtime identity manifest。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import stat
import tempfile
import time
from typing import Any


SCHEMA_VERSION = 1
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


def _manifest_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_manifest(
    *,
    actor_root: Path,
    queue_root: Path,
    publisher_state_root: Path,
    log_root: Path,
    identity: str,
) -> dict[str, Any]:
    if not identity or identity.strip() != identity:
        raise RuntimeManifestError("identity is required")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "regression_id": REGRESSION_ID,
        "identity": identity,
        "owner_uid": os.stat(actor_root).st_uid,
        "actor_root": _canonical_directory(actor_root, "actor_root"),
        "queue_root": _canonical_directory(queue_root, "queue_root"),
        "publisher_state_root": _canonical_directory(
            publisher_state_root, "publisher_state_root"
        ),
        "log_root": _canonical_directory(log_root, "log_root"),
        "service_labels": list(SERVICE_LABELS),
    }
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


def load_manifest(path: Path, expected_digest: str | None = None) -> dict[str, Any]:
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
    return payload


def receipt_for_label(manifest: dict[str, Any], label: str) -> dict[str, Any]:
    if label not in SERVICE_LABELS:
        raise RuntimeManifestError("service label is not registered")
    return {
        "label": label,
        "identity": manifest["identity"],
        "manifest_digest": manifest["manifest_digest"],
        **{field: manifest[field] for field in PATH_FIELDS},
    }


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


def plist_receipt(path: Path) -> dict[str, Any]:
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
        "identity": environment.get("PANTHEON_RUNTIME_IDENTITY"),
        "manifest_digest": environment.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
        "actor_root": environment.get("PANTHEON_RUNTIME_ACTOR_ROOT"),
        "queue_root": environment.get("PANTHEON_RUNTIME_QUEUE_ROOT"),
        "publisher_state_root": environment.get("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"),
        "log_root": environment.get("PANTHEON_RUNTIME_LOG_ROOT"),
        "plist_realpath": str(canonical),
    }
    if payload.get("WorkingDirectory") != receipt["actor_root"]:
        raise RuntimeManifestError("plist working directory actor mismatch")
    return receipt


def aggregate_plist_preflight(
    manifest: dict[str, Any], plist_paths: list[Path]
) -> dict[str, Any]:
    receipts = [plist_receipt(path) for path in plist_paths]
    result = validate_receipts(
        manifest,
        [{key: value for key, value in receipt.items() if key != "plist_realpath"} for receipt in receipts],
    )
    return {**result, "receipts": receipts}


def _barrier_is_valid(path: Path, expected_digest: str) -> bool:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        return False
    try:
        if path.resolve(strict=True) != path:
            return False
        metadata = os.stat(path)
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            return False
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload == {
        "schema_version": 1,
        "manifest_digest": expected_digest,
        "owner_uid": os.getuid(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--actor-root", type=Path, required=True)
    create.add_argument("--queue-root", type=Path, required=True)
    create.add_argument("--publisher-state-root", type=Path, required=True)
    create.add_argument("--log-root", type=Path, required=True)
    create.add_argument("--identity", required=True)
    create.add_argument("--output", type=Path, required=True)
    field = subparsers.add_parser("field")
    field.add_argument("--manifest", type=Path, required=True)
    field.add_argument("--expected-digest", required=True)
    field.add_argument("--name", choices=(*PATH_FIELDS, "identity", "manifest_digest"), required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--expected-digest", required=True)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--manifest", type=Path, required=True)
    aggregate.add_argument("--expected-digest", required=True)
    aggregate.add_argument("--plist", type=Path, action="append", required=True)
    barrier = subparsers.add_parser("barrier-exec")
    barrier.add_argument("--barrier", type=Path, required=True)
    barrier.add_argument("--expected-digest", required=True)
    barrier.add_argument("--timeout", type=int, default=90)
    barrier.add_argument("remainder", nargs=argparse.REMAINDER)
    barrier_validate = subparsers.add_parser("barrier-validate")
    barrier_validate.add_argument("--barrier", type=Path, required=True)
    barrier_validate.add_argument("--expected-digest", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "barrier-validate":
        if _barrier_is_valid(args.barrier, args.expected_digest):
            print(json.dumps({"status": "PASS"}, sort_keys=True))
            return 0
        print(json.dumps({"status": "NO-GO", "error": "barrier identity mismatch"}, sort_keys=True))
        return 1
    if args.command == "barrier-exec":
        command = list(args.remainder)
        if command[:1] == ["--"]:
            command = command[1:]
        if not command or not args.barrier.is_absolute() or not 1 <= args.timeout <= 300:
            return 64
        deadline = time.monotonic() + args.timeout
        while not args.barrier.exists():
            if time.monotonic() >= deadline:
                return 75
            time.sleep(0.2)
        if not _barrier_is_valid(args.barrier, args.expected_digest):
            return 78
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
            )
            write_manifest(args.output, manifest)
            print(json.dumps(manifest, sort_keys=True))
        else:
            manifest = load_manifest(args.manifest, args.expected_digest)
            if args.command == "field":
                print(manifest[args.name])
            elif args.command == "aggregate":
                print(json.dumps(aggregate_plist_preflight(manifest, args.plist), sort_keys=True))
            else:
                print(json.dumps({"status": "PASS", **manifest}, sort_keys=True))
    except RuntimeManifestError as error:
        print(json.dumps({"status": "NO-GO", "error": str(error)}, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

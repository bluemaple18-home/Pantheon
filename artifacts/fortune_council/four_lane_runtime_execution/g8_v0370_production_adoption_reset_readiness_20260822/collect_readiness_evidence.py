#!/usr/bin/env python3
"""Collect read-only G8 v0.3.370 adoption/reset readiness evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys


RUNTIME_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
LAUNCH_ROOT = Path("/Users/mattkuo/Library/LaunchAgents")
STAGE_ROOT = LAUNCH_ROOT / ".pantheon-four-lane-stage"
LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.content-capacity-guard",
)
EXACT_FILES = (
    "actor-head.txt",
    "actor-status.txt",
    "actor-remotes.txt",
    "actor-git-refs.txt",
    "task-head.txt",
    "task-git-refs.txt",
    "release-tag-peeled.txt",
    "manifest.sha256",
    "manifest-identity.json",
    "queue-tree.sha256",
    "state-tree.sha256",
    "transaction-tree.sha256",
    "publisher-lock.sha256",
    "live-plists.sha256",
    "stage-tree.sha256",
    "barrier-paths.txt",
    "barriers.sha256",
)
LAUNCH_FIELDS = ("path", "state", "pid", "last exit code")


def run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tree_manifest(root: Path, output: Path) -> None:
    if not root.exists():
        write_text(output, f"ABSENT\t{root}\n")
        return
    if root.is_file():
        write_text(output, f"{file_digest(root)}  {root}\n")
        return
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(f"{file_digest(path)}  {path}")
    write_text(output, "\n".join(rows) + ("\n" if rows else ""))


def git_output(repo: Path, args: list[str], output: Path) -> None:
    result = run(["git", "-C", str(repo), *args])
    write_text(output, result.stdout)


def launchctl_print(label: str) -> str:
    return run(["launchctl", "print", f"gui/{os.getuid()}/{label}"]).stdout


def launch_identity_text(text: str) -> dict[str, str | bool | None]:
    result: dict[str, str | bool | None] = {}
    for field in LAUNCH_FIELDS:
        match = re.search(rf"^\s*{re.escape(field)} = (.+)$", text, flags=re.MULTILINE)
        result[field] = match.group(1).strip() if match else None
    lowered = text.lower()
    result["loaded"] = "service not found" not in lowered and "could not find service" not in lowered
    return result


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_plist(path: Path) -> dict:
    with path.open("rb") as stream:
        return plistlib.load(stream)


def plist_mode(plist: dict) -> str:
    return "activation-only" if "--activation-only" in plist.get("ProgramArguments", []) else "normal"


def plist_summary(path: Path) -> dict:
    if not path.is_file():
        return {"present": False, "path": str(path)}
    plist = read_plist(path)
    env = plist.get("EnvironmentVariables", {})
    return {
        "present": True,
        "path": str(path),
        "digest": file_digest(path),
        "activation_mode": plist_mode(plist),
        "RunAtLoad": bool(plist.get("RunAtLoad")),
        "StartInterval": plist.get("StartInterval"),
        "KeepAlive": plist.get("KeepAlive"),
        "identity": env.get("PANTHEON_RUNTIME_IDENTITY"),
        "generation": env.get("PANTHEON_RUNTIME_GENERATION"),
        "manifest_digest": env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
        "runtime_identity_digest": env.get("PANTHEON_RUNTIME_IDENTITY_DIGEST"),
        "actor_head": env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
        "service_label": env.get("PANTHEON_RUNTIME_SERVICE_LABEL"),
    }


def snapshot(args: argparse.Namespace) -> None:
    root = args.evidence_root / args.name
    root.mkdir(parents=True, exist_ok=True)
    actor_root = RUNTIME_ROOT / "actor"
    manifest = RUNTIME_ROOT / "runtime-manifest.json"
    state_root = RUNTIME_ROOT / "state"
    write_text(root / "timestamp.txt", dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z") + "\n")
    git_output(actor_root, ["rev-parse", "HEAD"], root / "actor-head.txt")
    git_output(actor_root, ["status", "--porcelain=v1", "--untracked-files=all"], root / "actor-status.txt")
    git_output(actor_root, ["remote", "-v"], root / "actor-remotes.txt")
    git_output(actor_root, ["show-ref"], root / "actor-git-refs.txt")
    git_output(args.repo_root, ["rev-parse", "HEAD"], root / "task-head.txt")
    git_output(args.repo_root, ["status", "--porcelain=v1", "--untracked-files=all"], root / "task-status.txt")
    git_output(args.repo_root, ["show-ref"], root / "task-git-refs.txt")
    git_output(args.repo_root, ["rev-parse", "v0.3.370^{}"], root / "release-tag-peeled.txt")
    tree_manifest(manifest, root / "manifest.sha256")
    tree_manifest(RUNTIME_ROOT / "queue", root / "queue-tree.sha256")
    tree_manifest(state_root, root / "state-tree.sha256")
    tree_manifest(RUNTIME_ROOT / "transactions", root / "transaction-tree.sha256")
    tree_manifest(state_root / "publisher.lock", root / "publisher-lock.sha256")
    tree_manifest(STAGE_ROOT, root / "stage-tree.sha256")
    live_rows = []
    launch_dir = root / "launchctl"
    launch_dir.mkdir(parents=True, exist_ok=True)
    for label in LABELS:
        plist = LAUNCH_ROOT / f"{label}.plist"
        live_rows.append(f"{file_digest(plist)}  {plist}" if plist.is_file() else f"ABSENT\t{plist}")
        write_text(launch_dir / f"{label}.txt", launchctl_print(label))
    write_text(root / "live-plists.sha256", "\n".join(live_rows) + "\n")
    manifest_payload = read_json(manifest)
    identity_keys = (
        "schema_version",
        "identity",
        "manifest_digest",
        "runtime_identity_digest",
        "runtime_digest",
        "config_version",
        "generation",
        "actor_root",
        "queue_root",
        "publisher_state_root",
        "log_root",
        "actor_head",
        "python_executable",
        "uv_executable",
    )
    write_text(
        root / "manifest-identity.json",
        json.dumps({key: manifest_payload.get(key) for key in identity_keys}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    barriers = sorted(state_root.glob("four-lane-activation-*.barrier"))
    write_text(root / "barrier-paths.txt", "".join(f"{path}\n" for path in barriers))
    write_text(root / "barriers.sha256", "".join(f"{file_digest(path)}  {path}\n" for path in barriers))
    snapshot_rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "snapshot-digest.txt"):
        snapshot_rows.append(f"{file_digest(path)}  {path}")
    write_text(root / "snapshot-digest.txt", "\n".join(snapshot_rows) + "\n")


def collect_observation(args: argparse.Namespace) -> None:
    manifest = read_json(RUNTIME_ROOT / "runtime-manifest.json")
    live = {}
    stage = {}
    launch = {}
    for label in LABELS:
        live[label] = plist_summary(LAUNCH_ROOT / f"{label}.plist")
        stage[label] = plist_summary(STAGE_ROOT / f"{label}.plist")
        launch[label] = launch_identity_text(launchctl_print(label))
    controls = {}
    for name in ("generation", "manifest-digest", "publisher-exact-run-id", "publisher-max-runs"):
        path = STAGE_ROOT / name
        controls[name] = path.read_text(encoding="utf-8").strip() if path.is_file() else None
    payload = {
        "schema_version": 1,
        "card_id": "CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822",
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "production_mutation": False,
        "runtime_root": str(RUNTIME_ROOT),
        "launch_root": str(LAUNCH_ROOT),
        "stage_root": str(STAGE_ROOT),
        "release": {
            "required_base_sha": "eb2ddd8157901e8764ffcc5fd8a5c68822fa357c",
            "peeled_v0.3.370": run(["git", "-C", str(args.repo_root), "rev-parse", "v0.3.370^{}"]).stdout.strip(),
        },
        "manifest": manifest,
        "stage_controls": controls,
        "publisher_reset_success_receipt_present": (STAGE_ROOT / "publisher-reset-receipt.json").is_file(),
        "publisher_reset_failure_receipt_present": (STAGE_ROOT / "failure-receipt.json").is_file(),
        "publisher_reset_backup_dir_present": (STAGE_ROOT / "publisher-reset-backups").is_dir(),
        "failure_receipt": read_json(STAGE_ROOT / "failure-receipt.json") if (STAGE_ROOT / "failure-receipt.json").is_file() else None,
        "live_plists": live,
        "stage_plists": stage,
        "launchctl": launch,
    }
    write_text(args.evidence_root / "release-observation.json", json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    identity = {
        "current_actor_head": manifest.get("actor_head"),
        "current_generation": manifest.get("generation"),
        "current_manifest_digest": manifest.get("manifest_digest"),
        "current_runtime_identity_digest": manifest.get("runtime_identity_digest"),
        "current_identity": manifest.get("identity"),
        "target_stage_generation": controls.get("generation"),
        "target_stage_manifest_digest": controls.get("manifest-digest"),
        "publisher_exact_run_id": controls.get("publisher-exact-run-id"),
        "publisher_max_runs": controls.get("publisher-max-runs"),
        "publisher_reset_success_receipt_present": payload["publisher_reset_success_receipt_present"],
        "failure_receipt_status": (payload["failure_receipt"] or {}).get("status"),
        "failure_receipt_phase": ((payload["failure_receipt"] or {}).get("exit_reason") or {}).get("phase"),
    }
    write_text(args.evidence_root / "production-identity.json", json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def compare(args: argparse.Namespace) -> int:
    root = args.evidence_root
    before = root / "before"
    after = root / "after"
    comparisons = []
    for name in EXACT_FILES:
        left = file_digest(before / name)
        right = file_digest(after / name)
        comparisons.append({"surface": name, "before": left, "after": right, "unchanged": left == right})
    for path in sorted((before / "launchctl").glob("*.txt")):
        left = launch_identity_text(path.read_text(encoding="utf-8", errors="replace"))
        right = launch_identity_text((after / "launchctl" / path.name).read_text(encoding="utf-8", errors="replace"))
        comparisons.append({"surface": f"launchctl/{path.name}", "before": left, "after": right, "unchanged": left == right})
    changed = [item["surface"] for item in comparisons if not item["unchanged"]]
    payload = {
        "status": "PASS" if not changed else "MUTATION_DETECTED",
        "production_mutation": bool(changed),
        "changed": changed,
        "launchctl_volatile_fields_ignored": ["runs"],
        "comparisons": comparisons,
    }
    write_text(root / "mutation-tripwire.json", json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if not changed else 1


def digest_evidence(args: argparse.Namespace) -> None:
    rows = []
    for path in sorted(item for item in args.evidence_root.rglob("*") if item.is_file()):
        if path.name == "evidence-digests.sha256":
            continue
        rows.append(f"{file_digest(path)}  {path}")
    write_text(args.evidence_root / "evidence-digests.sha256", "\n".join(rows) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("snapshot", "observe", "compare", "digest"))
    parser.add_argument("--name", choices=("before", "after"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "snapshot":
        if args.name is None:
            parser.error("--name is required for snapshot")
        snapshot(args)
    elif args.action == "observe":
        collect_observation(args)
    elif args.action == "compare":
        return compare(args)
    elif args.action == "digest":
        digest_evidence(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

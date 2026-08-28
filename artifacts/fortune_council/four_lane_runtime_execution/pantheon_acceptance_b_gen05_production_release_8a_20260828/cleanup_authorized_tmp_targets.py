#!/usr/bin/env python3
"""Delete only the owner-authorized Pantheon /private/tmp cleanup targets."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


REPO_ROOT = Path("/Users/mattkuo/Documents/Pantheon")
RECEIPT_PATH = REPO_ROOT / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "pantheon_acceptance_b_gen05_production_release_8a_20260828/"
    "authorized-tmp-cleanup-receipt.json"
)
CURRENT_HEAD = "8a50395f67d22343fec4b0a8a5f41c8f40ac360e"

TARGETS = [
    {
        "path": "/private/tmp/pantheon-acceptance-b-plan-2ce-source-a",
        "kind": "repo",
        "expected_head_prefix": "2ce431ec41f5187531d88b52dfa91cef0373d8b5",
    },
    {
        "path": "/private/tmp/pantheon-promotion-source-6766-20260827-git",
        "kind": "repo",
        "expected_head_prefix": "6766fff999de7af09efc227230e69efd25795108",
    },
    {
        "path": "/private/tmp/pantheon-promotion-source-e3a2-20260827",
        "kind": "repo",
        "expected_head_prefix": "e3a2bbd1",
    },
    {
        "path": "/private/tmp/pantheon-v0395-promotion-source-799d770b",
        "kind": "repo",
        "expected_head_prefix": "a419c9a6",
    },
    {
        "path": "/private/tmp/pantheon-promotion-f7822c99.MJS44t",
        "kind": "repo",
        "expected_head_prefix": "f7822c99",
    },
    {
        "path": "/private/tmp/pantheon-promotion-e5c0743f.pcIP6z",
        "kind": "repo",
        "expected_head_prefix": "e5c0743f",
    },
    {
        "path": "/private/tmp/pantheon-rereview-f453.tar",
        "kind": "file",
    },
    {
        "path": "/private/tmp/pantheon-gen05-clean-head-20260828.tar",
        "kind": "file",
    },
]


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_size(path: Path) -> tuple[int, int]:
    if path.is_file():
        return path.stat().st_size, 1
    total = 0
    count = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            candidate = Path(root) / name
            try:
                total += candidate.lstat().st_size
                count += 1
            except FileNotFoundError:
                continue
    return total, count


def worktree_paths() -> set[str]:
    result = run_git(["worktree", "list", "--porcelain"], REPO_ROOT)
    paths: set[str] = set()
    if result.returncode != 0:
        return paths
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            paths.add(line.removeprefix("worktree "))
    return paths


def validate_repo(path: Path, expected_prefix: str) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    if not (path / ".git").exists():
        checks["repo"] = "missing .git"
        return checks
    head = run_git(["rev-parse", "HEAD"], path)
    checks["head_returncode"] = head.returncode
    checks["head"] = head.stdout.strip()
    checks["head_matches_expected"] = checks["head"].startswith(expected_prefix)
    status = run_git(["status", "--short"], path)
    checks["status_returncode"] = status.returncode
    checks["status_stdout"] = status.stdout
    checks["clean"] = status.returncode == 0 and status.stdout == ""
    ancestor = run_git(["merge-base", "--is-ancestor", checks["head"], CURRENT_HEAD], REPO_ROOT)
    checks["ancestor_of_current_head"] = ancestor.returncode == 0
    return checks


def main() -> int:
    before = shutil.disk_usage("/private/tmp")._asdict()
    registered_worktrees = worktree_paths()
    results: list[dict[str, Any]] = []
    reclaimed = 0
    deleted_count = 0

    for target in TARGETS:
        path = Path(target["path"])
        item: dict[str, Any] = {
            "path": str(path),
            "kind": target["kind"],
            "validated": False,
            "deleted": False,
            "skip_reason": "",
        }
        try:
            if not path.exists():
                item["skip_reason"] = "missing"
                results.append(item)
                continue
            if path.is_symlink() or path.resolve(strict=True) != path:
                item["skip_reason"] = "symlink_or_noncanonical"
                results.append(item)
                continue
            if str(path) in registered_worktrees:
                item["skip_reason"] = "registered_git_worktree"
                results.append(item)
                continue
            size_bytes, file_count = tree_size(path)
            item["size_bytes_before"] = size_bytes
            item["file_count_before"] = file_count
            if target["kind"] == "repo":
                checks = validate_repo(path, str(target["expected_head_prefix"]))
                item["repo_checks"] = checks
                if not (
                    checks.get("head_returncode") == 0
                    and checks.get("head_matches_expected") is True
                    and checks.get("clean") is True
                    and checks.get("ancestor_of_current_head") is True
                ):
                    item["skip_reason"] = "repo_validation_failed"
                    results.append(item)
                    continue
            elif target["kind"] == "file":
                stat_result = path.lstat()
                if not path.is_file():
                    item["skip_reason"] = "not_regular_file"
                    results.append(item)
                    continue
                item["sha256_before"] = sha256_file(path)
                item["mode_before"] = oct(stat_result.st_mode & 0o777)
            else:
                item["skip_reason"] = "unknown_kind"
                results.append(item)
                continue
            item["validated"] = True
            if target["kind"] == "repo":
                shutil.rmtree(path)
            else:
                path.unlink()
            item["deleted"] = not path.exists()
            if item["deleted"]:
                reclaimed += size_bytes
                deleted_count += 1
            else:
                item["skip_reason"] = "delete_did_not_remove_path"
            results.append(item)
        except Exception as error:  # fail closed per-target.
            item["skip_reason"] = f"exception:{type(error).__name__}:{error}"
            results.append(item)

    after = shutil.disk_usage("/private/tmp")._asdict()
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "scope": "owner_authorized_exact_private_tmp_pantheon_targets",
        "current_head": CURRENT_HEAD,
        "before": before,
        "after": after,
        "reclaimed_bytes_by_size_accounting": reclaimed,
        "host_free_delta_bytes": after["free"] - before["free"],
        "deleted_count": deleted_count,
        "targets": results,
        "unrecoverable_but_reconstructible": True,
        "expanded_allowlist": False,
        "used_globs": False,
    }
    if any(item["skip_reason"].startswith("exception:") for item in results):
        receipt["status"] = "PARTIAL"
    RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

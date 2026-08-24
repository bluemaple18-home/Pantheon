#!/usr/bin/env python3
"""比較唯讀任務前後的 protected surfaces，另列 task-owned evidence 變更。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
EXACT_PROTECTED = (
    "actor-git-refs.txt",
    "actor-head.txt",
    "actor-remotes.txt",
    "actor-status.txt",
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
ALLOWED_PREFIXES = (
    "artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PREAUTH-BLOCKER-RESOLUTION-20260824-RESULT.md",
    "artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_preauth_blocker_resolution_20260824/",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def launch_identity(path: Path) -> dict[str, str | bool | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    result: dict[str, str | bool | None] = {}
    for field in LAUNCH_FIELDS:
        match = re.search(rf"^\s*{re.escape(field)} = (.+)$", text, flags=re.MULTILINE)
        result[field] = match.group(1).strip() if match else None
    lowered = text.lower()
    result["loaded"] = "service not found" not in lowered and "could not find service" not in lowered
    return result


def status_paths(path: Path) -> list[str]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(line[3:])
    return rows


def allowed(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def main() -> int:
    before = ROOT / "before"
    after = ROOT / "after"
    comparisons = []
    for name in EXACT_PROTECTED:
        left = digest(before / name)
        right = digest(after / name)
        comparisons.append(
            {"surface": name, "before": left, "after": right, "unchanged": left == right}
        )
    for path in sorted((before / "launchctl").glob("*.txt")):
        left = launch_identity(path)
        right = launch_identity(after / "launchctl" / path.name)
        comparisons.append(
            {
                "surface": f"launchctl/{path.name}",
                "before": left,
                "after": right,
                "unchanged": left == right,
            }
        )
    changed = [item["surface"] for item in comparisons if not item["unchanged"]]
    before_status = status_paths(before / "task-status.txt")
    after_status = status_paths(after / "task-status.txt")
    status_delta = sorted(set(before_status).symmetric_difference(after_status))
    disallowed_status_delta = [path for path in status_delta if not allowed(path)]
    payload = {
        "schema_version": 1,
        "status": "PASS" if not changed and not disallowed_status_delta else "MUTATION_DETECTED",
        "production_mutation": bool(changed),
        "git_ref_mutation": any(name in changed for name in ("task-git-refs.txt", "actor-git-refs.txt")),
        "changed_protected_surfaces": changed,
        "comparisons": comparisons,
        "launchctl_volatile_fields_ignored": ["runs"],
        "task_worktree_status": {
            "before": before_status,
            "after": after_status,
            "delta": status_delta,
            "disallowed_delta": disallowed_status_delta,
            "allowed_ownership_only": not disallowed_status_delta,
        },
        "remote_mutation_count": 0,
        "fetch_count": 0,
        "remote_query_invocation_count": 2,
        "bounded_remote_query_contract_pass": False,
    }
    (ROOT / "mutation-tripwire.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

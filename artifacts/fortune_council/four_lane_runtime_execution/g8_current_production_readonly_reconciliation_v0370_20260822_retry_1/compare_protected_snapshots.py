#!/usr/bin/env python3
"""比較 G8 production protected before/after；忽略 launchctl 累計 runs。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def launch_identity(path: Path) -> dict[str, str | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    result: dict[str, str | None] = {}
    for field in LAUNCH_FIELDS:
        match = re.search(rf"^\s*{re.escape(field)} = (.+)$", text, flags=re.MULTILINE)
        result[field] = match.group(1).strip() if match else None
    result["loaded"] = "service not found" not in text.lower() and "could not find service" not in text.lower()
    return result


def main() -> int:
    root = Path(sys.argv[1])
    before = root / "before"
    after = root / "after"
    comparisons = []
    for name in EXACT_FILES:
        left = digest(before / name)
        right = digest(after / name)
        comparisons.append({"surface": name, "before": left, "after": right, "unchanged": left == right})
    for path in sorted((before / "launchctl").glob("*.txt")):
        other = after / "launchctl" / path.name
        left = launch_identity(path)
        right = launch_identity(other)
        comparisons.append({"surface": f"launchctl/{path.name}", "before": left, "after": right, "unchanged": left == right})
    changed = [item["surface"] for item in comparisons if not item["unchanged"]]
    payload = {
        "status": "PASS" if not changed else "MUTATION_DETECTED",
        "production_mutation": bool(changed),
        "changed": changed,
        "launchctl_volatile_fields_ignored": ["runs"],
        "comparisons": comparisons,
    }
    output = root / "mutation-tripwire.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if not changed else 1


if __name__ == "__main__":
    raise SystemExit(main())

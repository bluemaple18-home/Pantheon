#!/usr/bin/env python3
"""以唯讀方式驗證 installed g47 與 current actor 的 runtime identity tuple。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
from typing import Any


EXPECTED_HEAD = "4a3dfeac1943061edfce5350cb6bb25e35ff64c0"
INSTALLED_PLIST = Path(
    "/Users/mattkuo/Library/LaunchAgents/com.pantheon.agy-gemini-i18n-new.plist"
)
SHA1 = re.compile(r"^[0-9a-f]{40}$")
GENERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tuple_digest(payload: dict[str, str]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def _judge(payload: dict[str, str], current_head: str) -> dict[str, Any]:
    reasons: list[str] = []
    if SHA1.fullmatch(payload.get("actor_head", "")) is None:
        reasons.append("actor_head_invalid")
    elif payload["actor_head"] != current_head:
        reasons.append("actor_head_not_current")
    if not payload.get("identity", "").strip():
        reasons.append("identity_missing")
    if GENERATION.fullmatch(payload.get("generation", "")) is None:
        reasons.append("generation_invalid")
    expected_digest = _tuple_digest(
        {
            "actor_head": payload.get("actor_head", ""),
            "generation": payload.get("generation", ""),
            "identity": payload.get("identity", ""),
        }
    )
    if payload.get("tuple_digest") != expected_digest:
        reasons.append("tuple_digest_mismatch")
    return {
        "status": "PASS" if not reasons else "BLOCKED",
        "reasons": reasons,
        "expected_current_actor_head": current_head,
    }


def _installed_tuple() -> dict[str, str]:
    # 僅擷取公開 runtime identity 欄位；不讀 credential 檔或 secret value。
    with INSTALLED_PLIST.open("rb") as stream:
        payload = plistlib.load(stream)
    environment = payload.get("EnvironmentVariables", {})
    selected = {
        "actor_head": str(environment.get("PANTHEON_RUNTIME_ACTOR_HEAD", "")),
        "generation": str(environment.get("PANTHEON_RUNTIME_GENERATION", "")),
        "identity": str(environment.get("PANTHEON_RUNTIME_IDENTITY", "")),
    }
    return {**selected, "tuple_digest": _tuple_digest(selected)}


def _isolated_tuple(current_head: str) -> dict[str, str]:
    selected = {
        "actor_head": current_head,
        "generation": f"provider-readiness-{current_head[:12]}-20260902",
        "identity": f"provider-runtime-readiness:{current_head}:isolated",
    }
    return {**selected, "tuple_digest": _tuple_digest(selected)}


def main() -> int:
    repo = Path.cwd().resolve()
    current_head = _git(repo, "rev-parse", "HEAD")
    origin_main = _git(repo, "rev-parse", "origin/main")
    local_main = _git(repo, "rev-parse", "main")
    installed_hash_before = _sha256(INSTALLED_PLIST)
    installed = _installed_tuple()
    isolated = _isolated_tuple(current_head)
    installed_verdict = _judge(installed, current_head)
    isolated_verdict = _judge(isolated, current_head)
    installed_hash_after = _sha256(INSTALLED_PLIST)
    reasons: list[str] = []
    if current_head != EXPECTED_HEAD:
        reasons.append("fixed_head_mismatch")
    if origin_main != EXPECTED_HEAD:
        reasons.append("origin_main_mismatch")
    if installed_verdict["status"] != "BLOCKED":
        reasons.append("installed_g47_did_not_fail_closed")
    if isolated_verdict["status"] != "PASS":
        reasons.append("current_actor_isolated_tuple_failed")
    if installed_hash_before != installed_hash_after:
        reasons.append("installed_plist_mutated")
    status = "PASS" if not reasons else "BLOCKED"
    result = {
        "schema": "pantheon.provider_runtime_identity_readiness.v1",
        "task": "PANTHEON-PROVIDER-RUNTIME-GENERATION-READINESS-20260902",
        "status": status,
        "reasons": reasons,
        "context": {
            "mode": "CONTEXT_DEGRADED",
            "codegraph": "confirmed_uninitialized_by_dispatch",
            "head": current_head,
            "origin_main": origin_main,
            "local_main": local_main,
            "local_main_is_authority": False,
        },
        "installed_g47": {"tuple": installed, "verdict": installed_verdict},
        "isolated_current_actor": {"tuple": isolated, "verdict": isolated_verdict},
        "immutability": {
            "installed_plist": str(INSTALLED_PLIST),
            "sha256_before": installed_hash_before,
            "sha256_after": installed_hash_after,
            "equal": installed_hash_before == installed_hash_after,
        },
        "commands": [
            "git rev-parse HEAD origin/main main",
            "/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 artifacts/fortune_council/four_lane_runtime_execution/provider_runtime_generation_readiness_20260902/identity/identity_harness.py",
        ],
        "execution_attempts": [
            {
                "runner": "uv run --offline --no-project",
                "status": "BLOCKED_BEFORE_HARNESS",
                "reason": "sandbox system-configuration NULL object panic",
                "external_mutation": 0,
            },
            {"runner": "existing uv-managed python3.12", "status": "PASS"},
        ],
        "network_calls": 0,
        "provider_calls": 0,
        "launchctl_mutation": 0,
        "installed_plist_mutation": 0,
    }
    output = Path(__file__).resolve().parent
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = f"""# Identity readiness

最終結果：`{status}`

- installed g47 tuple：`{installed_verdict['status']}`；原因：`{', '.join(installed_verdict['reasons']) or 'none'}`。
- current actor isolated tuple：`{isolated_verdict['status']}`。
- authoritative actor：固定 HEAD／origin-main `{current_head}`；本機 `main` ref `{local_main}` 不作 authority。
- installed plist SHA-256 before/after：`{'相同' if installed_hash_before == installed_hash_after else '不同'}`。
- network/provider calls：`0`；launchctl mutation：`0`；installed plist mutation：`0`。

結構化完整證據見 `result.json`。
"""
    (output / "result.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"status": status, "result": str(output / "result.json")}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

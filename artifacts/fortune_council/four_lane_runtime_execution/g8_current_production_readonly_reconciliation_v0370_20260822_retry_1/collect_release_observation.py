#!/usr/bin/env python3
"""從當下 plist 與 launchctl 唯讀建立 G8 normalized observation。"""

from __future__ import annotations

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
PUBLISHER = LABELS[0]
CAPACITY = LABELS[-1]


def read_plist(path: Path) -> dict:
    with path.open("rb") as stream:
        return plistlib.load(stream)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def launchctl_identity(label: str) -> dict:
    result = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout
    def value(pattern: str) -> str | None:
        match = re.search(pattern, output, flags=re.MULTILINE)
        return match.group(1).strip() if match else None
    return {
        "loaded": result.returncode == 0,
        "returncode": result.returncode,
        "path": value(r"^\s*path = (.+)$"),
        "state": value(r"^\s*state = (.+)$"),
        "pid": value(r"^\s*pid = (.+)$"),
        "runs": value(r"^\s*runs = (.+)$"),
        "last_exit_status": value(r"^\s*last exit code = (.+)$"),
    }


def activation_mode(plist: dict) -> str:
    return "activation-only" if "--activation-only" in plist.get("ProgramArguments", []) else "normal"


def interval(plist: dict) -> str:
    value = plist.get("StartInterval")
    return "absent" if value is None else str(value)


def keep_alive(plist: dict) -> str:
    return "absent" if plist.get("KeepAlive") is None else str(plist["KeepAlive"]).lower()


def live_item(label: str) -> dict:
    path = LAUNCH_ROOT / f"{label}.plist"
    plist = read_plist(path)
    launch = launchctl_identity(label)
    mode = activation_mode(plist)
    env = plist.get("EnvironmentVariables", {})
    return {
        "service": label,
        "scope": "live",
        "activation_mode": mode,
        "plist_present": "live",
        "loaded_expected": "loaded" if launch["loaded"] else "not_loaded",
        "pid_policy": "INERT_LOADED" if mode == "activation-only" else "NO_PID",
        "RunAtLoad": str(bool(plist.get("RunAtLoad"))).lower(),
        "StartInterval": interval(plist),
        "KeepAlive": keep_alive(plist),
        "stage_policy": "not_applicable",
        "child_policy": "forbidden",
        "generation_relation": "old_live",
        "path": str(path),
        "plist_digest": sha256(path),
        "identity": env.get("PANTHEON_RUNTIME_IDENTITY"),
        "generation": env.get("PANTHEON_RUNTIME_GENERATION"),
        "manifest_digest": env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
        "runtime_identity_digest": env.get("PANTHEON_RUNTIME_IDENTITY_DIGEST"),
        "runtime_digest": env.get("PANTHEON_RUNTIME_CODE_DIGEST"),
        "config_version": env.get("PANTHEON_RUNTIME_CONFIG_VERSION"),
        "actor_root": env.get("PANTHEON_RUNTIME_ACTOR_ROOT"),
        "queue_root": env.get("PANTHEON_RUNTIME_QUEUE_ROOT"),
        "publisher_state_root": env.get("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"),
        "log_root": env.get("PANTHEON_RUNTIME_LOG_ROOT"),
        "actor_head": env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
        "python_executable": env.get("PANTHEON_RUNTIME_PYTHON_EXECUTABLE"),
        "uv_executable": env.get("PANTHEON_RUNTIME_UV_EXECUTABLE"),
        "launchctl": launch,
    }


def stage_item(label: str, target_generation: str) -> dict:
    path = STAGE_ROOT / f"{label}.plist"
    if not path.is_file():
        return {
            "service": label,
            "scope": "target_stage",
            "activation_mode": "not_present",
            "plist_present": "absent",
            "loaded_expected": "not_required",
            "pid_policy": "NOT_APPLICABLE",
            "RunAtLoad": "not_applicable",
            "StartInterval": "not_applicable",
            "KeepAlive": "not_applicable",
            "stage_policy": "target_absent",
            "child_policy": "not_applicable",
            "generation_relation": "target_newer_than_live",
            "path": str(path),
            "generation": target_generation,
        }
    plist = read_plist(path)
    return {
        "service": label,
        "scope": "target_stage",
        "activation_mode": activation_mode(plist),
        "plist_present": "stage",
        "loaded_expected": "not_loaded",
        "pid_policy": "NOT_APPLICABLE",
        "RunAtLoad": str(bool(plist.get("RunAtLoad"))).lower(),
        "StartInterval": interval(plist),
        "KeepAlive": keep_alive(plist),
        "stage_policy": "target_publisher_exact_run" if label == PUBLISHER else "target_six_plist",
        "child_policy": "forbidden",
        "generation_relation": "target_newer_than_live",
        "path": str(path),
        "plist_digest": sha256(path),
        "generation": plist.get("EnvironmentVariables", {}).get("PANTHEON_RUNTIME_GENERATION"),
        "manifest_digest": plist.get("EnvironmentVariables", {}).get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
        "runtime_identity_digest": plist.get("EnvironmentVariables", {}).get("PANTHEON_RUNTIME_IDENTITY_DIGEST"),
    }


def main() -> int:
    output = Path(sys.argv[1])
    receipt_root = Path(sys.argv[2])
    manifest = json.loads((RUNTIME_ROOT / "runtime-manifest.json").read_text(encoding="utf-8"))
    services = [live_item(label) for label in LABELS]
    services.extend(stage_item(label, manifest["generation"]) for label in LABELS)
    payload = {
        "schema_version": 1,
        "contract_id": "PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821",
        "edge_map_id": "PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821",
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "evidence_scopes": ["current"],
        "expected_state_id": "ST-TARGET-STAGED",
        "desired_target_state": "ST-QUIESCED-TARGET-STAGED",
        "current_receipts": ["RR-TARGET-STAGE", "RR-PUBLISHER-EXACT-STAGE"],
        "receipt_note": "current stage receipts存在；未把 historical terminal／live AO evidence升格為current receipt",
        "manifest": manifest,
        "stage_controls": {
            name: (STAGE_ROOT / name).read_text(encoding="utf-8").strip()
            for name in ("generation", "manifest-digest", "publisher-exact-run-id", "publisher-max-runs")
        },
        "publisher_reset_success_receipt_present": (STAGE_ROOT / "publisher-reset-receipt.json").is_file(),
        "failure_receipt_present": (STAGE_ROOT / "failure-receipt.json").is_file(),
        "services": services,
        "production_mutation": False,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_root.mkdir(parents=True, exist_ok=True)
    for item in services[: len(LABELS)]:
        receipt = {
            key: item.get(key)
            for key in (
                "identity", "manifest_digest", "runtime_identity_digest", "runtime_digest",
                "config_version", "generation", "actor_root", "queue_root",
                "publisher_state_root", "log_root", "actor_head", "python_executable",
                "uv_executable",
            )
        }
        receipt.update({"label": item["service"], "service_label": item["service"]})
        (receipt_root / f"{item['service']}.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

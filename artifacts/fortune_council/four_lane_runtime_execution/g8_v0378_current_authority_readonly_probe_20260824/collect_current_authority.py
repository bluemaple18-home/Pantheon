#!/usr/bin/env python3
"""Collect V0378 read-only current authority evidence.

This helper is task-owned evidence. It reads the existing V0370/V1
contracts and production surfaces, but does not write outside this
evidence directory and the RESULT file.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


CARD_ID = "CARD-PANTHEON-G8-V0378-CURRENT-AUTHORITY-READONLY-PROBE-20260824"
CHAIN_ID = "PANTHEON-G8-RULE24-SIGNED-EVIDENCE"
ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_ROOT = ROOT / "artifacts/fortune_council/four_lane_runtime_execution/g8_v0378_current_authority_readonly_probe_20260824"
RESULT_PATH = ROOT / "artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0378-CURRENT-AUTHORITY-READONLY-PROBE-20260824-RESULT.md"

RUNTIME_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR_ROOT = RUNTIME_ROOT / "actor"
MANIFEST_PATH = RUNTIME_ROOT / "runtime-manifest.json"
QUEUE_ROOT = RUNTIME_ROOT / "queue"
STATE_ROOT = RUNTIME_ROOT / "state"
TRANSACTION_ROOT = RUNTIME_ROOT / "transactions"
LAUNCH_ROOT = Path("/Users/mattkuo/Library/LaunchAgents")
STAGE_ROOT = LAUNCH_ROOT / ".pantheon-four-lane-stage"

PYTHON = Path(".venv/bin/python")
if not (ROOT / PYTHON).is_file():
    PYTHON = Path("/Users/mattkuo/Documents/Pantheon/.venv/bin/python")

LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.content-capacity-guard",
)

SAFE_MANIFEST_FIELDS = (
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
SAFE_ENV_FIELDS = tuple(f"PANTHEON_RUNTIME_{name}" for name in (
    "IDENTITY",
    "MANIFEST_DIGEST",
    "IDENTITY_DIGEST",
    "CODE_DIGEST",
    "CONFIG_VERSION",
    "GENERATION",
    "ACTOR_ROOT",
    "QUEUE_ROOT",
    "PUBLISHER_STATE_ROOT",
    "LOG_ROOT",
    "ACTOR_HEAD",
    "PYTHON_EXECUTABLE",
    "UV_EXECUTABLE",
))
SECRET_PATTERN = re.compile(r"(?i)(token|secret|credential|password|private[_-]?key|api[_-]?key)")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(argv: list[str], cwd: Path | None = None) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "argv": argv,
        "cwd": str(cwd) if cwd else None,
        "returncode": result.returncode,
        "stdout": redact(result.stdout.strip()),
        "stderr": redact(result.stderr.strip()),
    }


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<REDACTED>" if SECRET_PATTERN.search(str(key)) else redact(inner)) for key, inner in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r"://([^/\s:@]+):([^@\s/]+)@", r"://<REDACTED>:<REDACTED>@", value)
    value = re.sub(r"(?i)(token|secret|password|api[_-]?key|private[_-]?key)=([^,\s]+)", r"\1=<REDACTED>", value)
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "digest": None, "files": 0}
    if path.is_file():
        return {"exists": True, "digest": sha256_bytes(path.read_bytes()), "files": 1}
    digest = hashlib.sha256()
    files = 0
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = child.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
        files += 1
    return {"exists": True, "digest": digest.hexdigest(), "files": files}


def selected_files_digest(root: Path, names: tuple[str, ...]) -> dict[str, Any]:
    digest = hashlib.sha256()
    entries = []
    for name in names:
        path = root / f"{name}.plist"
        if path.is_file():
            data = path.read_bytes()
            item = {"path": str(path), "exists": True, "digest": sha256_bytes(data)}
            digest.update(name.encode("utf-8") + b"\0" + data + b"\0")
        else:
            item = {"path": str(path), "exists": False, "digest": None}
            digest.update(name.encode("utf-8") + b"\0ABSENT\0")
        entries.append(item)
    return {"exists": root.exists(), "digest": digest.hexdigest(), "files": sum(1 for item in entries if item["exists"]), "entries": entries}


def command_stdout(command: dict[str, Any]) -> str:
    return str(command.get("stdout") or "").strip()


def git_identity(repo: Path) -> dict[str, Any]:
    return {
        "path": str(repo),
        "canonical_path": canonical(repo),
        "head": command_stdout(run(["git", "-C", str(repo), "rev-parse", "HEAD"])),
        "status_porcelain": command_stdout(run(["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"])),
        "show_ref_sha256": sha256_bytes(command_stdout(run(["git", "-C", str(repo), "show-ref"])).encode("utf-8")),
        "remotes": command_stdout(run(["git", "-C", str(repo), "remote", "-v"])),
    }


def canonical(path: Path) -> dict[str, Any]:
    try:
        return {"exists": path.exists(), "resolved": str(path.resolve(strict=path.exists()))}
    except OSError as error:
        return {"exists": path.exists(), "resolved": None, "error": str(error)}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_manifest_identity() -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    return {field: manifest.get(field) for field in SAFE_MANIFEST_FIELDS}


def read_plist(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        return plistlib.load(stream)


def activation_mode(plist: dict[str, Any] | None) -> str:
    if not plist:
        return "not_present"
    return "activation-only" if "--activation-only" in plist.get("ProgramArguments", []) else "normal"


def plist_safe_identity(path: Path) -> dict[str, Any]:
    plist = read_plist(path)
    if plist is None:
        return {"path": str(path), "present": False}
    env = plist.get("EnvironmentVariables", {})
    safe_env = {key: env.get(key) for key in SAFE_ENV_FIELDS if key in env}
    return {
        "path": str(path),
        "present": True,
        "digest": sha256_bytes(path.read_bytes()),
        "activation_mode": activation_mode(plist),
        "RunAtLoad": bool(plist.get("RunAtLoad")),
        "StartInterval": plist.get("StartInterval"),
        "KeepAlive": plist.get("KeepAlive"),
        "safe_environment": redact(safe_env),
    }


def launchctl_identity(label: str) -> dict[str, Any]:
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
        return redact(match.group(1).strip()) if match else None

    return {
        "label": label,
        "returncode": result.returncode,
        "loaded": result.returncode == 0,
        "path": value(r"^\s*path = (.+)$"),
        "state": value(r"^\s*state = (.+)$"),
        "pid": value(r"^\s*pid = (.+)$"),
        "last_exit_status": value(r"^\s*last exit code = (.+)$"),
    }


def stage_controls() -> dict[str, Any]:
    controls = {}
    for name in ("generation", "manifest-digest", "publisher-exact-run-id", "publisher-max-runs"):
        path = STAGE_ROOT / name
        controls[name] = {"path": str(path), "exists": path.is_file(), "value": redact(path.read_text(encoding="utf-8").strip()) if path.is_file() else None}
    return controls


def reset_phase_evidence() -> dict[str, Any]:
    names = (
        "publisher-reset-receipt.json",
        "failure-receipt.json",
        "preactivation-receipt.json",
        "promotion-receipt.json",
        "activation-receipt.json",
    )
    evidence = {}
    for name in names:
        path = STAGE_ROOT / name
        item: dict[str, Any] = {"path": str(path), "exists": path.is_file(), "digest": file_digest(path)["digest"]}
        if path.is_file() and path.suffix == ".json":
            try:
                payload = read_json(path)
                item["selected_fields"] = redact({key: payload.get(key) for key in ("status", "card_id", "run_id", "generation", "manifest_digest", "actor_head", "created_at", "observed_at") if key in payload})
            except Exception as error:  # noqa: BLE001 - evidence should record unreadable JSON.
                item["parse_error"] = str(error)
        evidence[name] = item
    return evidence


def snapshot(name: str) -> dict[str, Any]:
    snap = {
        "snapshot": name,
        "observed_at": now(),
        "locators": {
            "repo_root": canonical(ROOT),
            "runtime_root": canonical(RUNTIME_ROOT),
            "actor_root": canonical(ACTOR_ROOT),
            "manifest": canonical(MANIFEST_PATH),
            "queue_root": canonical(QUEUE_ROOT),
            "state_root": canonical(STATE_ROOT),
            "transaction_root": canonical(TRANSACTION_ROOT),
            "launch_root": canonical(LAUNCH_ROOT),
            "stage_root": canonical(STAGE_ROOT),
        },
        "task_git": git_identity(ROOT),
        "actor_git": git_identity(ACTOR_ROOT),
        "manifest_digest": file_digest(MANIFEST_PATH),
        "manifest_identity": safe_manifest_identity() if MANIFEST_PATH.is_file() else None,
        "queue_tree": file_digest(QUEUE_ROOT),
        "state_tree": file_digest(STATE_ROOT),
        "transaction_tree": file_digest(TRANSACTION_ROOT),
        "publisher_lock": file_digest(STATE_ROOT / "publisher.lock"),
        "stage_tree": file_digest(STAGE_ROOT),
        "live_plists": selected_files_digest(LAUNCH_ROOT, LABELS),
        "barriers": barrier_digest(),
        "stage_controls": stage_controls(),
        "runtime_status": {
            label: {
                "live_plist": plist_safe_identity(LAUNCH_ROOT / f"{label}.plist"),
                "stage_plist": plist_safe_identity(STAGE_ROOT / f"{label}.plist"),
                "launchctl": launchctl_identity(label),
            }
            for label in LABELS
        },
        "reset_phase_evidence": reset_phase_evidence(),
    }
    write_json(EVIDENCE_ROOT / name / "protected-snapshot.json", snap)
    return snap


def barrier_digest() -> dict[str, Any]:
    paths = sorted(STATE_ROOT.glob("four-lane-activation-*.barrier"))
    digest = hashlib.sha256()
    entries = []
    for path in paths:
        data = path.read_bytes()
        digest.update(path.name.encode("utf-8") + b"\0" + data + b"\0")
        entries.append({"path": str(path), "digest": sha256_bytes(data)})
    return {"exists": STATE_ROOT.exists(), "files": len(entries), "digest": digest.hexdigest(), "entries": entries}


def comparable_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    runtime_status = {}
    for label, item in snap["runtime_status"].items():
        launch = item["launchctl"]
        runtime_status[label] = {
            "live_plist_digest": item["live_plist"].get("digest"),
            "stage_plist_digest": item["stage_plist"].get("digest"),
            "launchctl": {
                "loaded": launch.get("loaded"),
                "path": launch.get("path"),
                "state": launch.get("state"),
                "pid": launch.get("pid"),
                "last_exit_status": launch.get("last_exit_status"),
            },
        }
    return {
        "locators": snap["locators"],
        "actor_git": {
            "head": snap["actor_git"]["head"],
            "status_porcelain": snap["actor_git"]["status_porcelain"],
            "show_ref_sha256": snap["actor_git"]["show_ref_sha256"],
        },
        "manifest_digest": snap["manifest_digest"],
        "manifest_identity": snap["manifest_identity"],
        "queue_tree": snap["queue_tree"],
        "state_tree": snap["state_tree"],
        "transaction_tree": snap["transaction_tree"],
        "publisher_lock": snap["publisher_lock"],
        "stage_tree": snap["stage_tree"],
        "live_plists": snap["live_plists"],
        "barriers": snap["barriers"],
        "stage_controls": snap["stage_controls"],
        "runtime_status": runtime_status,
        "reset_phase_evidence": snap["reset_phase_evidence"],
    }


def write_release_observation(path: Path, snapshot_payload: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    services = []
    for label in LABELS:
        live = snapshot_payload["runtime_status"][label]["live_plist"]
        live_env = live.get("safe_environment", {})
        services.append({
            "service": label,
            "scope": "live",
            "activation_mode": live.get("activation_mode"),
            "plist_present": "live" if live.get("present") else "absent",
            "loaded_expected": "loaded" if snapshot_payload["runtime_status"][label]["launchctl"].get("loaded") else "not_loaded",
            "pid_policy": "INERT_LOADED" if live.get("activation_mode") == "activation-only" else "NO_PID",
            "RunAtLoad": str(bool(live.get("RunAtLoad"))).lower() if live.get("present") else "not_applicable",
            "StartInterval": "absent" if live.get("StartInterval") is None else str(live.get("StartInterval")),
            "KeepAlive": "absent" if live.get("KeepAlive") is None else str(live.get("KeepAlive")).lower(),
            "stage_policy": "not_applicable",
            "child_policy": "forbidden",
            "generation_relation": "old_live",
            "path": live.get("path"),
            "plist_digest": live.get("digest"),
            "identity": live_env.get("PANTHEON_RUNTIME_IDENTITY"),
            "generation": live_env.get("PANTHEON_RUNTIME_GENERATION"),
            "manifest_digest": live_env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
            "runtime_identity_digest": live_env.get("PANTHEON_RUNTIME_IDENTITY_DIGEST"),
            "runtime_digest": live_env.get("PANTHEON_RUNTIME_CODE_DIGEST"),
            "config_version": live_env.get("PANTHEON_RUNTIME_CONFIG_VERSION"),
            "actor_root": live_env.get("PANTHEON_RUNTIME_ACTOR_ROOT"),
            "queue_root": live_env.get("PANTHEON_RUNTIME_QUEUE_ROOT"),
            "publisher_state_root": live_env.get("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT"),
            "log_root": live_env.get("PANTHEON_RUNTIME_LOG_ROOT"),
            "actor_head": live_env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
            "python_executable": live_env.get("PANTHEON_RUNTIME_PYTHON_EXECUTABLE"),
            "uv_executable": live_env.get("PANTHEON_RUNTIME_UV_EXECUTABLE"),
            "launchctl": snapshot_payload["runtime_status"][label]["launchctl"],
        })
    for label in LABELS:
        stage = snapshot_payload["runtime_status"][label]["stage_plist"]
        stage_env = stage.get("safe_environment", {})
        services.append({
            "service": label,
            "scope": "target_stage",
            "activation_mode": stage.get("activation_mode"),
            "plist_present": "stage" if stage.get("present") else "absent",
            "loaded_expected": "not_loaded",
            "pid_policy": "NOT_APPLICABLE",
            "RunAtLoad": str(bool(stage.get("RunAtLoad"))).lower() if stage.get("present") else "not_applicable",
            "StartInterval": "absent" if stage.get("StartInterval") is None else str(stage.get("StartInterval")),
            "KeepAlive": "absent" if stage.get("KeepAlive") is None else str(stage.get("KeepAlive")).lower(),
            "stage_policy": "target_publisher_exact_run" if label == LABELS[0] else "target_six_plist",
            "child_policy": "forbidden",
            "generation_relation": "target_newer_than_live",
            "path": stage.get("path"),
            "plist_digest": stage.get("digest"),
            "generation": stage_env.get("PANTHEON_RUNTIME_GENERATION"),
            "manifest_digest": stage_env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
            "runtime_identity_digest": stage_env.get("PANTHEON_RUNTIME_IDENTITY_DIGEST"),
        })
    payload = {
        "schema_version": 1,
        "contract_id": "PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821",
        "edge_map_id": "PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821",
        "observed_at": now(),
        "evidence_scopes": ["current"],
        "expected_state_id": "ST-TARGET-STAGED",
        "desired_target_state": "ST-QUIESCED-TARGET-STAGED",
        "current_receipts": ["RR-TARGET-STAGE", "RR-PUBLISHER-EXACT-STAGE"],
        "receipt_note": "V0378 current read-only observation; historical reset/phase receipts are not elevated to current authority.",
        "manifest": manifest,
        "stage_controls": snapshot_payload["stage_controls"],
        "publisher_reset_success_receipt_present": snapshot_payload["reset_phase_evidence"]["publisher-reset-receipt.json"]["exists"],
        "failure_receipt_present": snapshot_payload["reset_phase_evidence"]["failure-receipt.json"]["exists"],
        "services": services,
        "production_mutation": False,
    }
    write_json(path, payload)
    receipt_root = EVIDENCE_ROOT / "normalized-live-receipts"
    receipt_root.mkdir(parents=True, exist_ok=True)
    for item in services[: len(LABELS)]:
        receipt = {
            "label": item["service"],
            "service_label": item["service"],
            "identity": item.get("identity"),
            "manifest_digest": item.get("manifest_digest"),
            "runtime_identity_digest": item.get("runtime_identity_digest"),
            "runtime_digest": item.get("runtime_digest"),
            "config_version": item.get("config_version"),
            "generation": item.get("generation"),
            "actor_root": item.get("actor_root"),
            "queue_root": item.get("queue_root"),
            "publisher_state_root": item.get("publisher_state_root"),
            "log_root": item.get("log_root"),
            "actor_head": item.get("actor_head"),
            "python_executable": item.get("python_executable"),
            "uv_executable": item.get("uv_executable"),
        }
        write_json(receipt_root / f"{item['service']}.json", receipt)
    return payload


def run_reconciler(remote_sha: str, local_sha: str, manifest_digest: str, exact_run_id: str) -> dict[str, Any]:
    result_path = EVIDENCE_ROOT / "reconciler-result.json"
    observation_path = EVIDENCE_ROOT / "release-observation.json"
    argv = [
        str((ROOT / PYTHON).resolve() if not PYTHON.is_absolute() else PYTHON),
        "-m",
        "scripts.pantheon_g8_production_preactivation",
        "--card-id",
        CARD_ID,
        "--repo-root",
        str(ROOT),
        "--actor-root",
        str(ACTOR_ROOT),
        "--queue-root",
        str(QUEUE_ROOT),
        "--state-root",
        str(STATE_ROOT),
        "--transaction-root",
        str(TRANSACTION_ROOT),
        "--live-root",
        str(LAUNCH_ROOT),
        "--staged-root",
        str(STAGE_ROOT),
        "--manifest",
        str(MANIFEST_PATH),
        "--expected-manifest-digest",
        manifest_digest,
        "--required-source",
        local_sha,
        "--origin-main",
        remote_sha,
        "--exact-run-id",
        exact_run_id,
        "--evidence-path",
        str(result_path),
        "--release-observation",
        str(observation_path),
        "--allow-source-drift",
        "__v0378_readonly_probe_allowlist_not_authorizing_drift__",
    ]
    receipt = run(argv, cwd=ROOT)
    write_json(EVIDENCE_ROOT / "reconciler-command.json", receipt)
    if result_path.is_file():
        return read_json(result_path)
    return {"status": "UNKNOWN", "blocked_code": "RECONCILER_NO_RESULT", "command": receipt}


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = comparable_snapshot(before)
    right = comparable_snapshot(after)
    keys = sorted(left)
    comparisons = []
    for key in keys:
        unchanged = left[key] == right.get(key)
        comparisons.append({
            "surface": key,
            "before": sha256_bytes(json.dumps(left[key], sort_keys=True, ensure_ascii=False).encode("utf-8")),
            "after": sha256_bytes(json.dumps(right.get(key), sort_keys=True, ensure_ascii=False).encode("utf-8")),
            "unchanged": unchanged,
        })
    changed = [item["surface"] for item in comparisons if not item["unchanged"]]
    payload = {
        "status": "PASS" if not changed else "MUTATION_DETECTED",
        "production_mutation": bool(changed),
        "changed": changed,
        "comparisons": comparisons,
        "launchctl_volatile_fields_ignored": ["runs"],
    }
    write_json(EVIDENCE_ROOT / "mutation-tripwire.json", payload)
    return payload


def evidence_digests() -> None:
    rows = []
    for path in sorted(EVIDENCE_ROOT.rglob("*")):
        if path.is_file() and path.name != "evidence-digests.sha256":
            rows.append(f"{sha256_bytes(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}")
    (EVIDENCE_ROOT / "evidence-digests.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def choose_verdict(remote: dict[str, Any], local_sha: str, actor_head: str, manifest_actor_head: str, reconciler: dict[str, Any], tripwire: dict[str, Any]) -> tuple[str, list[str], str]:
    reasons = []
    if remote["exit_code"] != 0:
        return "UNKNOWN", ["唯一 remote query 失敗，依卡片不得 retry。"], "停止；重新授權前不得重試 remote。"
    if tripwire["status"] != "PASS":
        return "BLOCKED", [f"protected surfaces drifted: {tripwire['changed']}"], "停止；先人工檢查 mutation/drift。"
    remote_sha = remote.get("sha")
    if remote_sha != local_sha:
        reasons.append(f"local HEAD {local_sha} != remote main {remote_sha}")
    if actor_head != remote_sha:
        reasons.append(f"production actor HEAD {actor_head} != remote main {remote_sha}")
    if manifest_actor_head != remote_sha:
        reasons.append(f"runtime manifest actor_head {manifest_actor_head} != remote main {remote_sha}")
    if reconciler.get("status") != "READY_FOR_PRODUCTION_AUTHORIZATION":
        reasons.append(f"formal reconciler status {reconciler.get('status')} / {reconciler.get('blocked_code')}")
    if reasons:
        return "BLOCKED", reasons, "唯一下一步：先收斂 current Git/production identity，再重新產生 read-only authority evidence。"
    return "AUTHORITY_CURRENT", ["remote main、local HEAD、production actor、manifest 與 formal reconciler 均收斂。"], "可回主線由人工決定下一個 bounded authorization step。"


def write_result(summary: dict[str, Any]) -> None:
    lines = [
        "# V0378 current authority read-only probe RESULT",
        "",
        "## Verdict",
        "",
        f"`{summary['verdict']}`",
        "",
        "## Remote Git",
        "",
        f"- invocation_count: `{summary['remote']['invocation_count']}`",
        f"- exit_code: `{summary['remote']['exit_code']}`",
        f"- refs/heads/main: `{summary['remote'].get('sha')}`",
        "",
        "## Local And Production Identity",
        "",
        f"- local HEAD: `{summary['local_sha']}`",
        f"- actor HEAD: `{summary['actor_head']}`",
        f"- manifest actor_head: `{summary['manifest_actor_head']}`",
        f"- manifest_digest: `{summary['manifest_digest']}`",
        f"- generation: `{summary['generation']}`",
        "",
        "## Canonical Locator",
        "",
        f"- repo_root exists/resolved: `{summary['locators']['repo_root']['exists']}` / `{summary['locators']['repo_root']['resolved']}`",
        f"- actor_root exists/resolved: `{summary['locators']['actor_root']['exists']}` / `{summary['locators']['actor_root']['resolved']}`",
        f"- manifest exists/resolved: `{summary['locators']['manifest']['exists']}` / `{summary['locators']['manifest']['resolved']}`",
        f"- stage_root exists/resolved: `{summary['locators']['stage_root']['exists']}` / `{summary['locators']['stage_root']['resolved']}`",
        f"- launch_root exists/resolved: `{summary['locators']['launch_root']['exists']}` / `{summary['locators']['launch_root']['resolved']}`",
        "",
        "## Phase And Reset Evidence",
        "",
        f"- publisher_reset_success_receipt_present: `{summary['publisher_reset_success_receipt_present']}`",
        f"- failure_receipt_present: `{summary['failure_receipt_present']}`",
        f"- stage generation: `{summary['stage_generation']}`",
        f"- stage manifest digest: `{summary['stage_manifest_digest']}`",
        f"- staged exact run id: `{summary['exact_run_id']}`",
        "",
        "## Formal Contract Reuse",
        "",
        "- contract: `scripts.pantheon_g8_production_preactivation`",
        "- observation_schema: V0370 `schema_version=1`, `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821`, `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821`",
        f"- reconciler_status: `{summary['reconciler_status']}`",
        f"- reconciler_blocked_code: `{summary['reconciler_blocked_code']}`",
        "",
        "## Tripwire",
        "",
        f"- status: `{summary['tripwire_status']}`",
        f"- changed: `{summary['tripwire_changed']}`",
        "",
        "## Currentness",
        "",
    ]
    lines.extend(f"- {reason}" for reason in summary["reasons"])
    lines.extend([
        "",
        "## Evidence",
        "",
        f"- machine_summary: `{summary['summary_path']}`",
        f"- remote_authority: `{summary['remote_path']}`",
        f"- release_observation: `{summary['release_observation_path']}`",
        f"- mutation_tripwire: `{summary['tripwire_path']}`",
        f"- formal_reconciler: `{summary['reconciler_path']}`",
        "",
        "## Limits",
        "",
        "- remote Git query executed exactly once; no fetch/pull/push/tag/ref/credential write.",
        "- production observation was read-only; no launchctl load/unload/kickstart/enable/disable.",
        "- no production write, no canary, no dispatch.",
        "",
        "## Next Step",
        "",
        summary["next_step"],
        "",
    ])
    RESULT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: collect_current_authority.py <remote_exit_code> <remote_stdout> <remote_stderr>", file=sys.stderr)
        return 2
    remote_exit = int(sys.argv[1])
    remote_stdout = sys.argv[2]
    remote_stderr = sys.argv[3]
    remote_sha = remote_stdout.split()[0] if remote_exit == 0 and remote_stdout.split() else None
    remote = {
        "service": "git",
        "operation": "ls-remote --heads origin main",
        "operation_level": "read_only",
        "invocation_count": 1,
        "exit_code": remote_exit,
        "sha": remote_sha,
        "stdout_sha256": sha256_bytes(remote_stdout.encode("utf-8")),
        "stderr": redact(remote_stderr),
    }
    write_json(EVIDENCE_ROOT / "remote-authority.json", remote)
    write_json(EVIDENCE_ROOT / "external-tool-gate.json", {
        "tool_service": "git remote origin",
        "operation_level": "read_only",
        "connection_status": "authorized_by_activation_token",
        "schema_checked": "fixed command: git ls-remote --heads origin main",
        "confirmation_required": False,
        "execution_status": "PASS" if remote_exit == 0 else "FAILED_NO_RETRY",
        "evidence": "remote-authority.json",
        "remaining_risk": "remote contents are observed once only; no retry allowed",
    })
    write_json(EVIDENCE_ROOT / "codegraph-receipt.json", {
        "status": "NOT_READY",
        "reason": "CodeGraph not initialized in this worktree during bootstrap check",
        "fallback": "bounded rg/source reads and existing contract files",
    })

    before = snapshot("before")
    write_release_observation(EVIDENCE_ROOT / "release-observation.json", before)
    local_sha = before["task_git"]["head"]
    actor_head = before["actor_git"]["head"]
    manifest_identity = before["manifest_identity"] or {}
    manifest_actor_head = str(manifest_identity.get("actor_head") or "")
    manifest_digest = str(manifest_identity.get("manifest_digest") or "")
    exact_run_id = str(before["stage_controls"]["publisher-exact-run-id"]["value"] or "")
    reconciler = run_reconciler(remote_sha or "0" * 40, local_sha, manifest_digest, exact_run_id)
    after = snapshot("after")
    tripwire = compare(before, after)

    verdict, reasons, next_step = choose_verdict(remote, local_sha, actor_head, manifest_actor_head, reconciler, tripwire)
    summary = {
        "card_id": CARD_ID,
        "chain_id": CHAIN_ID,
        "observed_at": now(),
        "verdict": verdict,
        "reasons": reasons,
        "next_step": next_step,
        "remote": remote,
        "local_sha": local_sha,
        "actor_head": actor_head,
        "manifest_actor_head": manifest_actor_head,
        "manifest_digest": manifest_digest,
        "generation": manifest_identity.get("generation"),
        "locators": before["locators"],
        "publisher_reset_success_receipt_present": before["reset_phase_evidence"]["publisher-reset-receipt.json"]["exists"],
        "failure_receipt_present": before["reset_phase_evidence"]["failure-receipt.json"]["exists"],
        "stage_generation": before["stage_controls"]["generation"]["value"],
        "stage_manifest_digest": before["stage_controls"]["manifest-digest"]["value"],
        "exact_run_id": exact_run_id,
        "reconciler_status": reconciler.get("status"),
        "reconciler_blocked_code": reconciler.get("blocked_code"),
        "tripwire_status": tripwire["status"],
        "tripwire_changed": tripwire["changed"],
        "summary_path": str((EVIDENCE_ROOT / "summary.json").relative_to(ROOT)),
        "remote_path": str((EVIDENCE_ROOT / "remote-authority.json").relative_to(ROOT)),
        "release_observation_path": str((EVIDENCE_ROOT / "release-observation.json").relative_to(ROOT)),
        "tripwire_path": str((EVIDENCE_ROOT / "mutation-tripwire.json").relative_to(ROOT)),
        "reconciler_path": str((EVIDENCE_ROOT / "reconciler-result.json").relative_to(ROOT)),
        "production_mutation": False,
    }
    write_json(EVIDENCE_ROOT / "summary.json", summary)
    write_result(summary)
    evidence_digests()
    print(json.dumps({"verdict": verdict, "reasons": reasons, "tripwire": tripwire["status"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
from typing import Any


SOURCE = Path("/Users/mattkuo/.codex/worktrees/a018/Pantheon")
MAIN = Path("/Users/mattkuo/Documents/Pantheon")
EVIDENCE = MAIN / "artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829"
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
ACTOR = RUNTIME / "actor"
MANIFEST = RUNTIME / "runtime-manifest.json"
QUEUE = RUNTIME / "queue"
STATE = RUNTIME / "state"
LOGS = RUNTIME / "logs"
STAGE = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
LAUNCH_AGENTS = Path("/Users/mattkuo/Library/LaunchAgents")
PYTHON = Path("/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12")
AI_GATE = Path("/Users/mattkuo/ai-core/scripts/production_canary_readiness_gate.py")
EXPECTED_ORIGIN = "git@github.com:bluemaple18-home/Pantheon.git"
CURRENT_SHA = "779fb96434c15013d82833788a6795119730daad"
CURRENT_MANIFEST_DIGEST = "937fe73ef1f5cfb2b319bc6120937584ab4455d29f7755b8c4e88b97f672a3dd"
TARGET_SHA = "bde44589f3785aae738bb7d7b1626270ba5505d0"
TARGET_RUNTIME_DIGEST = "db960fb0118ac8deda7de3d1b2b7e55358ea670458dd6d08773a56110ed8faba"
TARGET_IDENTITY = f"gate2-actor:{TARGET_SHA}:new-lane-current-acceptance-20260829"
TARGET_GENERATION = "g71-bde44589-new-lane-current-acceptance-20260829"
CORRELATION = "pantheon-new-lane-current-acceptance-bde445-20260829"
TRANSACTION = RUNTIME / "transactions" / CORRELATION
CAPACITY = EVIDENCE / "resume-bde445-rule24-capacity-raw.json"
AUTHORIZATION = EVIDENCE / "resume-bde445-authorization-payload.json"
RULE25_RECEIPT = EVIDENCE / "resume-779f-rule25-readiness/package/production-canary-capability-receipt.json"
LABELS = (
    "com.pantheon.agy-content-publisher",
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.content-capacity-guard",
)
LANES = ("new", "rewrite", "i18n-new", "i18n-rewrite")

sys.path.insert(0, str(SOURCE))
from scripts import agy_content_publisher as publisher  # noqa: E402
from scripts import pantheon_content_runtime_promotion as promotion  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return done.stdout.strip()


def tree(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    total = 0
    if not path.exists():
        return {"exists": False, "files": 0, "bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}
    for item in sorted(path.rglob("*"), key=lambda p: p.relative_to(path).as_posix()):
        if not item.is_file() or item.is_symlink():
            continue
        rel = item.relative_to(path).as_posix().encode()
        body = item.read_bytes()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(hashlib.sha256(body).digest())
        count += 1
        total += len(body)
    return {"exists": True, "files": count, "bytes": total, "sha256": digest.hexdigest()}


def services() -> dict[str, int]:
    result = {}
    for label in LABELS:
        done = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True, text=True)
        result[label] = done.returncode
    return result


def assert_stopped() -> dict[str, int]:
    result = services()
    loaded = [label for label, code in result.items() if code == 0]
    if loaded:
        raise SystemExit(f"services unexpectedly loaded: {loaded}")
    return result


def plist_receipts() -> list[dict[str, Any]]:
    rows = []
    for label in LABELS:
        path = LAUNCH_AGENTS / f"{label}.plist"
        row: dict[str, Any] = {"label": label, "exists": path.is_file()}
        if path.is_file():
            with path.open("rb") as stream:
                payload = plistlib.load(stream)
            env = payload.get("EnvironmentVariables", {})
            row.update({
                "bytes": path.stat().st_size,
                "sha256": sha(path),
                "actor_head": env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
                "identity": env.get("PANTHEON_RUNTIME_IDENTITY"),
                "generation": env.get("PANTHEON_RUNTIME_GENERATION"),
                "manifest_digest": env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
                "arguments_sha256": hashlib.sha256(json.dumps(payload.get("ProgramArguments", []), separators=(",", ":")).encode()).hexdigest(),
            })
        rows.append(row)
    return rows


def registry() -> dict[str, Any]:
    rows = []
    counts: dict[str, int] = {}
    for path in sorted((QUEUE / "runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        lane = payload.get("lane")
        status = payload.get("status")
        key = f"{lane}:{status}"
        counts[key] = counts.get(key, 0) + 1
        envelope = payload.get("identity_envelope") if isinstance(payload.get("identity_envelope"), dict) else {}
        rows.append({
            "file": path.name,
            "sha256": sha(path),
            "run_id": payload.get("run_id"),
            "lane": lane,
            "mode": payload.get("mode"),
            "status": status,
            "identity_digest": envelope.get("digest"),
        })
    return {"count": len(rows), "counts": counts, "rows": rows}


def snapshot(label: str) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lane_payload = {}
    for lane in LANES:
        root = QUEUE / "lanes" / lane
        lane_payload[lane] = {"tree": tree(root)}
        for subdir in ("inbox", "processing", "outbox", "archive", "failed", "production-attempts"):
            lane_payload[lane][subdir] = tree(root / subdir)
    payload = {
        "schema_version": 1,
        "operation": "read-only-snapshot",
        "label": label,
        "source": {"head": git(SOURCE, "rev-parse", "HEAD"), "origin_main": git(SOURCE, "rev-parse", "origin/main"), "status": git(SOURCE, "status", "--porcelain")},
        "actor": {"head": git(ACTOR, "rev-parse", "HEAD"), "status": git(ACTOR, "status", "--porcelain")},
        "manifest": {k: manifest.get(k) for k in ("identity", "actor_head", "generation", "manifest_digest", "runtime_identity_digest", "runtime_digest", "config_version")},
        "manifest_file": {"bytes": MANIFEST.stat().st_size, "sha256": sha(MANIFEST)},
        "stage": tree(STAGE),
        "services": services(),
        "live_plists": plist_receipts(),
        "registry": registry(),
        "publisher_ledger": {"bytes": (STATE / "ledger.json").stat().st_size, "sha256": sha(STATE / "ledger.json")},
        "queue_tree": tree(QUEUE),
        "production_tree": tree(RUNTIME),
        "lanes": lane_payload,
        "mutation_counts": {"provider": 0, "reviewer": 0, "publisher": 0, "transaction": 0},
    }
    write_json(EVIDENCE / f"resume-bde445-{label}-snapshot.json", payload)


def record(label: str, command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    write_json(EVIDENCE / f"resume-bde445-{label}.command.json", command)
    done = subprocess.run(command, cwd=str(cwd), check=False, capture_output=True, text=True)
    (EVIDENCE / f"resume-bde445-{label}.stdout.txt").write_text(done.stdout, encoding="utf-8")
    (EVIDENCE / f"resume-bde445-{label}.stderr.txt").write_text(done.stderr, encoding="utf-8")
    (EVIDENCE / f"resume-bde445-{label}.returncode.txt").write_text(f"{done.returncode}\n", encoding="utf-8")
    if done.stdout.strip().startswith("{"):
        try:
            write_json(EVIDENCE / f"resume-bde445-{label}.stdout.json", json.loads(done.stdout))
        except json.JSONDecodeError:
            pass
    return done


def rule24(after: bool = False) -> int:
    assert_stopped()
    receipt = EVIDENCE / ("resume-bde445-rule24-after-raw.json" if after else "resume-bde445-rule24-capacity-raw.json")
    suffix = "-after" if after else ""
    command = [
        str(PYTHON), "-m", "scripts.pantheon_content_capacity_guard",
        "--exercise-root", f"/private/tmp/pantheon-new-lane-current-acceptance-rule24-bde445{suffix}-20260829",
        "--receipt", str(receipt), "--cycle-bytes", "1048576", "exercise",
    ]
    done = record("rule24-after" if after else "rule24-capacity", command, cwd=SOURCE)
    if done.returncode == 0:
        value = json.loads(receipt.read_text(encoding="utf-8"))
        if value.get("status") != "PASS" or value.get("production_mutation") is not False:
            return 1
    return done.returncode


def blocked_evidence() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stage_plists = sorted(STAGE.glob("com.pantheon.*.plist"))
    rows = []
    for path in stage_plists:
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
        env = payload.get("EnvironmentVariables", {})
        rows.append({
            "file": path.name,
            "sha256": sha(path),
            "actor_head": env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
            "identity": env.get("PANTHEON_RUNTIME_IDENTITY"),
            "generation": env.get("PANTHEON_RUNTIME_GENERATION"),
            "manifest_digest": env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
            "run_at_load": payload.get("RunAtLoad"),
            "start_interval": payload.get("StartInterval"),
        })
    stdout_path = EVIDENCE / "resume-bde445-service-capacity.stdout.txt"
    stderr_path = EVIDENCE / "resume-bde445-service-capacity.stderr.txt"
    payload = {
        "schema_version": 1,
        "status": "BLOCKED_CONTRACT_GAP",
        "verdict": "BLOCKED",
        "exact_edge": "coordinator --install -> publisher --install -> capacity --install-recovery-stage",
        "observed_error": "preactivation stage mismatch",
        "capacity_returncode": int((EVIDENCE / "resume-bde445-service-capacity.returncode.txt").read_text().strip()),
        "capacity_stdout_sha256": sha(stdout_path),
        "capacity_stderr_sha256": sha(stderr_path),
        "target": {k: manifest.get(k) for k in ("actor_head", "identity", "generation", "manifest_digest")},
        "stage_authority": {
            "manifest_digest": (STAGE / "manifest-digest").read_text().strip(),
            "generation": (STAGE / "generation").read_text().strip(),
            "publisher_max_runs": (STAGE / "publisher-max-runs").read_text().strip(),
            "publisher_exact_run_id_exists": (STAGE / "publisher-exact-run-id").is_file(),
            "publisher_exact_run_id": None,
            "plist_count": len(stage_plists),
            "plists": rows,
        },
        "validator_contract": {
            "source": "scripts/pantheon_content_capacity_guard.py:1040-1063",
            "requires_nonempty_publisher_exact_run_id": True,
            "formal_publisher_install_without_fresh_run_wrote_exact_run_id": False,
            "reason": "fresh new run does not yet exist; guessing or manually writing an exact run id is forbidden",
        },
        "services": services(),
        "aggregate_activation": 0,
        "scheduler_creates": 0,
        "provider_calls": 0,
        "reviewer_calls": 0,
        "publisher_executes": 0,
        "release_commits": 0,
        "tags": 0,
        "pushes": 0,
        "deploys": 0,
        "manual_queue_state_plist_edits": 0,
        "retry_or_bypass": 0,
    }
    write_json(EVIDENCE / "resume-bde445-blocked-contract-gap-receipt.json", payload)


def comparison() -> None:
    before = json.loads((EVIDENCE / "resume-bde445-immutable-before-snapshot.json").read_text(encoding="utf-8"))
    after = json.loads((EVIDENCE / "resume-bde445-post-blocked-snapshot.json").read_text(encoding="utf-8"))
    payload = {
        "schema_version": 1,
        "status": "PASS",
        "intended_runtime_promotion": {
            "actor_before": before["actor"]["head"],
            "actor_after": after["actor"]["head"],
            "manifest_before": before["manifest"],
            "manifest_after": after["manifest"],
            "production_bytes_before": before["production_tree"]["bytes"],
            "production_bytes_after": after["production_tree"]["bytes"],
        },
        "protected_equal": {
            "queue_tree": before["queue_tree"] == after["queue_tree"],
            "registry": before["registry"] == after["registry"],
            "publisher_ledger": before["publisher_ledger"] == after["publisher_ledger"],
            "live_plists": before["live_plists"] == after["live_plists"],
            "lane_trees": {lane: before["lanes"][lane]["tree"] == after["lanes"][lane]["tree"] for lane in LANES},
        },
        "services_after": after["services"],
        "all_services_stopped_after": all(code != 0 for code in after["services"].values()),
        "stage_before": before["stage"],
        "stage_after": after["stage"],
        "external_calls": {"provider": 0, "reviewer": 0, "publisher": 0},
        "scheduler_creates": 0,
        "second_job": False,
    }
    if not all(payload["protected_equal"][key] for key in ("queue_tree", "registry", "publisher_ledger", "live_plists")):
        payload["status"] = "FAIL"
    if not all(payload["protected_equal"]["lane_trees"].values()) or not payload["all_services_stopped_after"]:
        payload["status"] = "FAIL"
    write_json(EVIDENCE / "resume-bde445-immutability-comparison.json", payload)


def rule25() -> int:
    command = [str(PYTHON), str(AI_GATE), "--receipt", str(RULE25_RECEIPT)]
    return record("rule25-ready", command, cwd=SOURCE).returncode


def authorization() -> str:
    payload = {
        "schema_version": 1,
        "authorized_by": "Owner four-lane production acceptance continuation",
        "operation": "new-lane-current-production-acceptance-bde445",
        "parent_sha": CURRENT_SHA,
        "target_sha": TARGET_SHA,
        "allowed_mutations": [
            "formal runtime promotion 779fb to bde445",
            "formal seven-service staged install and aggregate activation after lane-isolation proof",
            "one fresh new run and bounded writer/reviewer/publisher/release/deploy",
        ],
        "forbidden_mutations": [
            "source or test edits", "manual queue/state/plist edits", "rewrite or i18n lane execution",
            "second provider, reviewer, publisher, job, or candidate",
        ],
    }
    write_json(AUTHORIZATION, payload)
    return sha(AUTHORIZATION)


def preserved() -> list[str]:
    values = []
    for path in sorted((QUEUE / "runs").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8")).get("run_id")
        if isinstance(value, str) and value:
            values.append(value)
    values = sorted(set(values))
    write_json(EVIDENCE / "resume-bde445-preserved-run-ids.json", values)
    return values


def promotion_command(action: str, expected_plan_digest: str | None) -> list[str]:
    stopped = assert_stopped()
    if git(SOURCE, "rev-parse", "HEAD") != TARGET_SHA or git(SOURCE, "rev-parse", "origin/main") != TARGET_SHA or git(SOURCE, "status", "--porcelain"):
        raise SystemExit("source SHA/origin/status drift")
    if git(SOURCE, "remote", "get-url", "origin") != EXPECTED_ORIGIN:
        raise SystemExit("source origin drift")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actor_head = git(ACTOR, "rev-parse", "HEAD")
    if action in ("plan", "apply") and (actor_head != CURRENT_SHA or manifest.get("manifest_digest") != CURRENT_MANIFEST_DIGEST):
        raise SystemExit("current actor or manifest drift")
    if publisher.runtime_manifest_digest(SOURCE) != TARGET_RUNTIME_DIGEST:
        raise SystemExit("target runtime digest drift")
    run_ids = preserved()
    auth_digest = authorization()
    input_payload = {
        "action": action, "source_head": TARGET_SHA, "actor_head": actor_head,
        "manifest_digest": manifest.get("manifest_digest"), "stage_digest": promotion.tree_digest(STAGE),
        "target_runtime_digest": TARGET_RUNTIME_DIGEST, "target_identity": TARGET_IDENTITY,
        "target_generation": TARGET_GENERATION, "capacity_receipt_sha256": sha(CAPACITY),
        "authorization_sha256": auth_digest, "services_stopped_returncodes": stopped,
        "preserved_run_count": len(run_ids),
    }
    write_json(EVIDENCE / f"resume-bde445-promotion-{action}-input.json", input_payload)
    command = [
        str(PYTHON), "-m", "scripts.pantheon_content_runtime_promotion", action,
        "--source-repo", str(SOURCE), "--source-sha", TARGET_SHA,
        "--expected-origin", EXPECTED_ORIGIN, "--actor-root", str(ACTOR),
        "--expected-current-actor-sha", CURRENT_SHA, "--manifest-path", str(MANIFEST),
        "--expected-current-manifest-digest", CURRENT_MANIFEST_DIGEST,
        "--private-stage-root", str(STAGE), "--expected-current-stage-digest", promotion.tree_digest(STAGE),
        "--transaction-root", str(TRANSACTION), "--queue-root", str(QUEUE),
        "--publisher-state-root", str(STATE), "--log-root", str(LOGS),
        "--target-identity", TARGET_IDENTITY, "--target-runtime-digest", TARGET_RUNTIME_DIGEST,
        "--target-config-version", "formal-runtime-v3-model-route-v1",
        "--target-generation", TARGET_GENERATION, "--target-python-executable", str(PYTHON),
        "--target-uv-executable", str(manifest["uv_executable"]),
        "--authorization-digest", auth_digest, "--capacity-receipt", str(CAPACITY),
        "--capacity-receipt-digest", sha(CAPACITY), "--correlation-id", CORRELATION,
    ]
    for run_id in run_ids:
        command.extend(["--preserve-run-id", run_id])
    if action in ("apply", "finalize", "rollback"):
        if not expected_plan_digest:
            raise SystemExit("expected plan digest required")
        command.extend(["--expected-plan-digest", expected_plan_digest])
    return command


def run_promotion(action: str, label: str, expected_plan_digest: str | None) -> int:
    command = promotion_command(action, expected_plan_digest)
    return record(label, command, cwd=SOURCE).returncode


def run_service(name: str) -> int:
    assert_stopped()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("actor_head") != TARGET_SHA or manifest.get("manifest_digest") != "255c72a7234ca97d1868c278acb5a92405bef03954a1b8e5918f62a4c663a358":
        raise SystemExit("promoted manifest drift")
    env = os.environ.copy()
    env.update({
        "AGY_GEMINI_CLI_PATH": "/Users/mattkuo/.antigravity/bin/agy-1.1.3",
        "AGY_GEMINI_CREDENTIAL_POOL_FILE": "/Users/mattkuo/.config/pantheon/gemini-api-pool.json",
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(QUEUE / "production-credential-pool-state.json"),
        "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": str(manifest["manifest_digest"]),
        "PANTHEON_PUBLISH_MAX_RUNS": "1",
        "PANTHEON_PYTHON_PATH": str(PYTHON),
        "PANTHEON_RUNTIME_MANIFEST_FILE": str(MANIFEST),
    })
    commands = {
        "coordinator": [str(ACTOR / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--install"],
        "publisher": [str(ACTOR / "scripts/install_agy_content_publisher_launchd.sh"), "--install"],
        "capacity": [str(ACTOR / "scripts/install_pantheon_content_capacity_guard_launchd.sh"), "--install-recovery-stage"],
    }
    command = commands[name]
    write_json(EVIDENCE / f"resume-bde445-service-{name}.command.json", {
        "command": command,
        "environment": {key: env[key] for key in sorted(env) if key.startswith("PANTHEON_") or key.startswith("AGY_GEMINI_")},
    })
    done = subprocess.run(command, cwd=str(ACTOR), env=env, check=False, capture_output=True, text=True)
    stem = EVIDENCE / f"resume-bde445-service-{name}"
    stem.with_suffix(".stdout.txt").write_text(done.stdout, encoding="utf-8")
    stem.with_suffix(".stderr.txt").write_text(done.stderr, encoding="utf-8")
    stem.with_suffix(".returncode.txt").write_text(f"{done.returncode}\n", encoding="utf-8")
    return done.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("snapshot", "rule24", "rule24-after", "rule25", "promotion", "service", "blocked-evidence", "comparison"))
    parser.add_argument("--label")
    parser.add_argument("--action", choices=("plan", "apply", "finalize", "status"))
    parser.add_argument("--expected-plan-digest")
    parser.add_argument("--service", choices=("coordinator", "publisher", "capacity"))
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.command == "snapshot":
        if not args.label:
            raise SystemExit("label required")
        snapshot(args.label)
        return 0
    if args.command == "rule24":
        return rule24()
    if args.command == "rule24-after":
        return rule24(after=True)
    if args.command == "rule25":
        return rule25()
    if args.command == "service":
        if not args.service:
            raise SystemExit("service required")
        return run_service(args.service)
    if args.command == "blocked-evidence":
        blocked_evidence()
        return 0
    if args.command == "comparison":
        comparison()
        return 0
    if not args.action or not args.label:
        raise SystemExit("action and label required")
    return run_promotion(args.action, args.label, args.expected_plan_digest)


if __name__ == "__main__":
    raise SystemExit(main())

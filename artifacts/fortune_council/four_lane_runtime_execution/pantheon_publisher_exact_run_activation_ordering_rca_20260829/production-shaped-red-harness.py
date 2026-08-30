#!/usr/bin/env python3
"""唯讀 RCA：在隔離 root 重播 fresh-run 與 historical exact-run activation ordering。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile


REPO = Path("/Users/mattkuo/.codex/worktrees/a018/Pantheon")
MAIN = Path("/Users/mattkuo/Documents/Pantheon")
PRODUCTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
LIVE_PLISTS = Path("/Users/mattkuo/Library/LaunchAgents")
LIVE_STAGE = LIVE_PLISTS / ".pantheon-four-lane-stage"
HEAD = "bde44589f3785aae738bb7d7b1626270ba5505d0"
IDENTITY = f"gate2-actor:{HEAD}:new-lane-current-acceptance-20260829"
GENERATION = "g71-bde44589-new-lane-current-acceptance-20260829"
HISTORICAL_EXACT_RUN_ID = "auto-i18n-en-614aa4dc3542ab2c5637"
HISTORICAL_RUN_RECEIPT = MAIN / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/"
    "raw-current/runtime/parent-run.json"
)
RULE24_RECEIPT = MAIN / (
    "artifacts/fortune_council/four_lane_runtime_execution/"
    "CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829/"
    "resume-bde445-rule24-after-raw.json"
)
LABELS = (
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.agy-content-publisher",
    "com.pantheon.content-capacity-guard",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_path(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "files": 0, "sha256": None}
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    total = 0
    for item in files:
        body = item.read_bytes()
        relative = item.name if path.is_file() else item.relative_to(path).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(body)
        total += len(body)
    return {"exists": True, "bytes": total, "files": len(files), "sha256": digest.hexdigest()}


def production_snapshot() -> dict[str, object]:
    return {
        "runtime_manifest": snapshot_path(PRODUCTION_ROOT / "runtime-manifest.json"),
        "queue": snapshot_path(PRODUCTION_ROOT / "queue"),
        "publisher_state": snapshot_path(PRODUCTION_ROOT / "state"),
        "transactions": snapshot_path(PRODUCTION_ROOT / "transactions"),
        "live_stage": snapshot_path(LIVE_STAGE),
        "live_plists": {
            label: snapshot_path(LIVE_PLISTS / f"{label}.plist") for label in LABELS
        },
    }


def write_fake_launchctl(path: Path, launch_agents: Path) -> None:
    capacity = "com.pantheon.content-capacity-guard"
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" != \"print\" ]; then exit 97; fi\n"
        "label=${2##*/}\n"
        f"if [ \"$label\" != \"{capacity}\" ]; then exit 113; fi\n"
        "printf '%s = {\\n' \"$2\"\n"
        f"printf '\\tpath = %s\\n' '{launch_agents}/{capacity}.plist'\n"
        "printf '%s\\n' '\tstate = waiting'\n"
        "printf '%s\\n' '\tlast exit code = 0'\n"
        "printf '%s\\n' '}'\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def command(env: dict[str, str], script: str, action: str) -> dict[str, object]:
    completed = subprocess.run(
        ["bash", str(REPO / "scripts" / script), action],
        cwd=REPO,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    combined = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    first_line = completed.stdout.splitlines()[0] if completed.stdout.splitlines() else ""
    try:
        transition = json.loads(first_line)
    except json.JSONDecodeError:
        transition = {}
    normalized_output: object = transition or combined
    if isinstance(normalized_output, dict):
        normalized_output = {
            key: value
            for key, value in normalized_output.items()
            if key not in {"manifest_digest", "runtime_identity_digest"}
        }
    normalized_encoded = json.dumps(
        normalized_output, sort_keys=True, separators=(",", ":")
    ).encode()
    reasons = transition.get("reasons") if isinstance(transition, dict) else None
    if reasons == ["preactivation stage mismatch"]:
        category = "preactivation_stage_mismatch"
        edge = "validate_preactivation_transition:publisher-exact-run-id"
    elif completed.returncode == 0:
        category = "PASS"
        edge = None
    else:
        category = "unexpected_failure"
        edge = None
    return {
        "installer": script,
        "action": action,
        "returncode": completed.returncode,
        "category": category,
        "exact_edge": edge,
        "output_semantic_sha256": hashlib.sha256(normalized_encoded).hexdigest(),
    }


def staged_topology(home: Path) -> dict[str, object]:
    stage = home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    plists = sorted(stage.glob("*.plist"))
    tuples = []
    for path in plists:
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
        env = payload.get("EnvironmentVariables", {})
        tuples.append(
            (
                env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
                env.get("PANTHEON_RUNTIME_GENERATION"),
                env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
            )
        )
    exact = stage / "publisher-exact-run-id"
    return {
        "plist_count": len(plists),
        "labels": [path.stem for path in plists],
        "cohort_tuple_count": len(set(tuples)),
        "manifest_digest_present": (stage / "manifest-digest").is_file(),
        "generation_present": (stage / "generation").is_file(),
        "publisher_max_runs": (stage / "publisher-max-runs").read_text().strip()
        if (stage / "publisher-max-runs").is_file()
        else None,
        "publisher_exact_run_id_present": exact.is_file(),
        "publisher_exact_run_id": exact.read_text().strip() if exact.is_file() else None,
    }


def prepare(root: Path, exact_run_id: str | None) -> tuple[Path, dict[str, str]]:
    sys.path.insert(0, str(REPO))
    from scripts.agy_content_publisher import runtime_manifest_digest
    from scripts.pantheon_content_runtime_manifest import build_manifest, write_manifest

    home = root / "home"
    queue = root / "queue"
    state = root / "state"
    logs = root / "logs"
    fake_bin = root / "bin"
    launch_agents = home / "Library/LaunchAgents"
    for path in (queue / "runs", state, logs, fake_bin, launch_agents):
        path.mkdir(parents=True, exist_ok=True)
    for label in LABELS:
        destination = launch_agents / f"{label}.plist"
        shutil.copy2(LIVE_PLISTS / f"{label}.plist", destination)
        destination.chmod(0o600)
    write_fake_launchctl(fake_bin / "launchctl", launch_agents)

    real_python = Path(sys.executable).resolve()
    python_path = root / "python-rule24-replay"
    python_path.write_text(
        "#!/usr/bin/env python3\n"
        "import os,sys\n"
        "args=sys.argv[1:]\n"
        "if len(args)>=3 and args[0:2]==['-m','scripts.pantheon_content_capacity_guard'] "
        "and args[-1]=='preflight':\n"
        " print(open(os.environ['PANTHEON_RCA_RULE24_RECEIPT'], encoding='utf-8').read(), end='')\n"
        " raise SystemExit(0)\n"
        "os.execv(os.environ['PANTHEON_RCA_REAL_PYTHON'], "
        "[os.environ['PANTHEON_RCA_REAL_PYTHON'], *args])\n",
        encoding="utf-8",
    )
    python_path.chmod(0o700)
    uv_path = Path("/Users/mattkuo/.local/bin/uv").resolve()
    manifest = build_manifest(
        actor_root=REPO,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity=IDENTITY,
        runtime_digest=runtime_manifest_digest(REPO),
        config_version="formal-runtime-v3-model-route-v1",
        generation=GENERATION,
        actor_head=HEAD,
        python_executable=python_path,
        uv_executable=uv_path,
    )
    manifest_path = root / "runtime-manifest.json"
    write_manifest(manifest_path, manifest)
    ready = state / "ready" / GENERATION
    barrier = state / f"four-lane-activation-{GENERATION}.barrier"
    for label in LABELS:
        from scripts.pantheon_content_runtime_manifest import write_readiness_ack

        write_readiness_ack(ready, manifest, label)
    from scripts.pantheon_content_runtime_manifest import activate_barrier

    activate_barrier(barrier, ready, manifest)
    fake_cli = root / "agy-1.1.3"
    fake_cli.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    fake_cli.chmod(0o700)
    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "TMPDIR": str(root),
            "PANTHEON_USER_HOME_DIR": str(home),
            "PANTHEON_PYTHON_PATH": str(python_path),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": str(manifest["manifest_digest"]),
            "PANTHEON_PUBLISH_MAX_RUNS": "1",
            "AGY_GEMINI_CLI_PATH": str(fake_cli),
            "PANTHEON_RCA_REAL_PYTHON": str(real_python),
            "PANTHEON_RCA_RULE24_RECEIPT": str(RULE24_RECEIPT),
        }
    )
    if exact_run_id is not None:
        env["PANTHEON_PUBLISH_EXACT_RUN_ID"] = exact_run_id
    else:
        env.pop("PANTHEON_PUBLISH_EXACT_RUN_ID", None)
    return home, env


def replay(exact_run_id: str | None) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="pantheon-exact-run-ordering-rca-") as raw:
        home, env = prepare(Path(raw).resolve(), exact_run_id)
        steps = []
        for script, action in (
            ("install_agy_gemini_coordinator_launchd.sh", "--install"),
            ("install_agy_content_publisher_launchd.sh", "--install"),
            ("install_pantheon_content_capacity_guard_launchd.sh", "--install-recovery-stage"),
        ):
            result = command(env, script, action)
            steps.append(result)
            if result["returncode"] != 0:
                break
        return {
            "selector": exact_run_id,
            "steps": steps,
            "stage": staged_topology(home),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip() != HEAD:
        raise SystemExit("actor HEAD drift")
    if subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain"], text=True).strip():
        raise SystemExit("actor worktree dirty")
    historical = json.loads(HISTORICAL_RUN_RECEIPT.read_text(encoding="utf-8"))
    if historical.get("run_id") != HISTORICAL_EXACT_RUN_ID or historical.get("status") != "complete":
        raise SystemExit("historical exact-run evidence drift")

    before = production_snapshot()
    fresh_without_future_run = replay(None)
    historical_existing_run = replay(HISTORICAL_EXACT_RUN_ID)
    after = production_snapshot()
    receipt = {
        "schema_version": 1,
        "actor_head": HEAD,
        "production_shaped_identity": IDENTITY,
        "generation": GENERATION,
        "formal_order": ["coordinator --install", "publisher --install", "capacity --install-recovery-stage"],
        "fresh_without_future_run": fresh_without_future_run,
        "historical_existing_run": historical_existing_run,
        "historical_run_evidence": {
            "run_id": HISTORICAL_EXACT_RUN_ID,
            "status": historical["status"],
            "receipt_sha256": sha256(HISTORICAL_RUN_RECEIPT),
            "receipt_bytes": HISTORICAL_RUN_RECEIPT.stat().st_size,
        },
        "rule24_receipt": {
            "status": json.loads(RULE24_RECEIPT.read_text(encoding="utf-8"))["status"],
            "sha256": sha256(RULE24_RECEIPT),
            "bytes": RULE24_RECEIPT.stat().st_size,
            "projection": "byte-exact stdout replay; no field projection",
        },
        "external_calls": {"provider": 0, "reviewer": 0, "publisher": 0, "scheduler": 0, "activation": 0},
        "production_before": before,
        "production_after": after,
        "production_bytes_unchanged": before == after,
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["canonical_digest_without_self"] = hashlib.sha256(canonical).hexdigest()
    body = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(body)
    else:
        args.output.write_text(body, encoding="utf-8")
    fresh_red = (
        fresh_without_future_run["steps"][-1]["category"] == "preactivation_stage_mismatch"
        and fresh_without_future_run["stage"]["publisher_exact_run_id_present"] is False
    )
    historical_green = (
        historical_existing_run["steps"][-1]["returncode"] == 0
        and historical_existing_run["stage"]["plist_count"] == 7
    )
    return 0 if fresh_red and historical_green and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())

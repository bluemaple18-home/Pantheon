#!/usr/bin/env python3
"""唯讀 RCA：在隔離 HOME/root 重播正式 installer 的 identity 順序契約。"""

from __future__ import annotations

import hashlib
import json
import os
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile


REPO = Path("/Users/mattkuo/.codex/worktrees/a018/Pantheon")
PRODUCTION_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
RULE24_RECEIPT = Path(
    "/Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/"
    "four_lane_runtime_execution/CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-"
    "ACCEPTANCE-20260829/resume-779f-rule24-promotion-capacity-raw.json"
)
LIVE_STAGE = Path("/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage")
LIVE_PLISTS = Path("/Users/mattkuo/Library/LaunchAgents")
HEAD = "779fb96434c15013d82833788a6795119730daad"
IDENTITY = f"gate2-actor:{HEAD}:new-lane-current-acceptance-20260829"
GENERATION = "g70-779fb964-new-lane-current-acceptance-20260829"
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
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_path(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "digest": None, "files": 0}
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
    return {"exists": True, "bytes": total, "digest": digest.hexdigest(), "files": len(files)}


def production_snapshot() -> dict[str, object]:
    plist_receipts = {}
    for label in LABELS:
        path = LIVE_PLISTS / f"{label}.plist"
        plist_receipts[label] = snapshot_path(path)
    return {
        "runtime_manifest": snapshot_path(PRODUCTION_ROOT / "runtime-manifest.json"),
        "promotion_receipt": snapshot_path(
            PRODUCTION_ROOT
            / "transactions/pantheon-new-lane-current-acceptance-779f-20260829/promotion-receipt.json"
        ),
        "registry": snapshot_path(PRODUCTION_ROOT / "queue/runs"),
        "publisher_ledger": snapshot_path(PRODUCTION_ROOT / "state/ledger.json"),
        "live_stage": snapshot_path(LIVE_STAGE),
        "live_plists": plist_receipts,
    }


def command(env: dict[str, str], script: str, action: str) -> dict[str, object]:
    proc = subprocess.run(
        ["bash", str(REPO / "scripts" / script), action],
        cwd=REPO,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    combined = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    if "preactivation manifest mismatch" in combined:
        edge = "validate_preactivation_transition:ACTIVATION_ONLY_IDENTITY_PATTERN"
        error = "preactivation manifest mismatch"
    elif proc.returncode == 0:
        edge = None
        error = None
    else:
        edge = "unrelated_fixture_or_preflight_failure"
        error = combined[-1200:]
    return {
        "action": action,
        "returncode": proc.returncode,
        "exact_edge": edge,
        "error": error,
    }


def staged_topology(home: Path) -> dict[str, object]:
    stage = home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    plists = sorted(p.stem for p in stage.glob("*.plist")) if stage.exists() else []
    identities: dict[str, str | None] = {}
    for path in sorted(stage.glob("*.plist")):
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
        identities[path.stem] = payload.get("EnvironmentVariables", {}).get("PANTHEON_RUNTIME_IDENTITY")
    return {
        "labels": plists,
        "count": len(plists),
        "identity_values": sorted(set(identities.values())),
        "manifest_digest_present": (stage / "manifest-digest").exists(),
        "generation_present": (stage / "generation").exists(),
        "publisher_max_runs_present": (stage / "publisher-max-runs").exists(),
    }


def prepare(root: Path) -> tuple[Path, dict[str, str]]:
    sys.path.insert(0, str(REPO))
    from scripts.agy_content_publisher import runtime_manifest_digest
    from scripts.pantheon_content_runtime_manifest import build_manifest, write_manifest

    home = root / "home"
    queue = root / "queue"
    state = root / "state"
    logs = root / "logs"
    for path in (home, queue / "runs", state, logs):
        path.mkdir(parents=True, exist_ok=True)
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
    fake_cli = root / "agy-1.1.3"
    fake_cli.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    fake_cli.chmod(0o700)
    env = dict(os.environ)
    env.update(
        {
            "PANTHEON_USER_HOME_DIR": str(home),
            "PANTHEON_PYTHON_PATH": str(python_path),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
            "PANTHEON_PUBLISH_MAX_RUNS": "1",
            "AGY_GEMINI_CLI_PATH": str(fake_cli),
            "PANTHEON_RCA_REAL_PYTHON": str(real_python),
            "PANTHEON_RCA_RULE24_RECEIPT": str(RULE24_RECEIPT),
        }
    )
    return home, env


def replay(order: tuple[tuple[str, str], ...]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="pantheon-identity-rca-") as raw:
        home, env = prepare(Path(raw).resolve())
        steps = []
        for script, action in order:
            result = command(env, script, action)
            steps.append({"installer": script, **result})
            if result["returncode"] != 0:
                break
        return {
            "order": [{"installer": script, "action": action} for script, action in order],
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
    before = production_snapshot()
    bypass_capacity_first = replay(
        (
            ("install_pantheon_content_capacity_guard_launchd.sh", "--install-recovery-stage"),
            ("install_agy_content_publisher_launchd.sh", "--install"),
            ("install_agy_gemini_coordinator_launchd.sh", "--install"),
        )
    )
    canonical_transition = replay(
        (
            ("install_agy_gemini_coordinator_launchd.sh", "--install"),
            ("install_agy_content_publisher_launchd.sh", "--install"),
            ("install_pantheon_content_capacity_guard_launchd.sh", "--install-recovery-stage"),
        )
    )
    publisher_first = replay(
        (
            ("install_agy_content_publisher_launchd.sh", "--install"),
            ("install_pantheon_content_capacity_guard_launchd.sh", "--install-recovery-stage"),
            ("install_agy_gemini_coordinator_launchd.sh", "--install"),
        )
    )
    after = production_snapshot()
    receipt = {
        "schema_version": 1,
        "actor_head": HEAD,
        "production_shaped_identity": IDENTITY,
        "generation": GENERATION,
        "rule24_receipt": {
            "sha256": sha256(RULE24_RECEIPT),
            "bytes": RULE24_RECEIPT.stat().st_size,
            "projection": "byte-exact stdout replay; no field projection",
        },
        "provider_calls": 0,
        "reviewer_calls": 0,
        "publisher_calls": 0,
        "activation_calls": 0,
        "diagnostic_capacity_first_bypass": bypass_capacity_first,
        "canonical_transition": canonical_transition,
        "publisher_first": publisher_first,
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
    expected_red = all(
        case["steps"][-1]["returncode"] != 0
        and case["steps"][-1]["error"] == "preactivation manifest mismatch"
        for case in (canonical_transition, publisher_first)
    )
    return 0 if before == after and expected_red else 1


if __name__ == "__main__":
    raise SystemExit(main())

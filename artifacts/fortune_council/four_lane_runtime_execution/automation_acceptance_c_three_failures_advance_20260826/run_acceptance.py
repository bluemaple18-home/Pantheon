#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_seo_copy_pipeline as pipeline
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts.agy_gemini_runner import process_once
from scripts.agy_seo_copy_pipeline import GeminiApiFailure


CARD_ID = "CARD-PANTHEON-AUTOMATION-ACCEPTANCE-C-THREE-FAILURES-ADVANCE-20260826"
DISPATCH_KEY = "v1:2a5865ab4eb192d645f4127ef8dbcd4d42ead56923c6677bccc94f48c3a35b85"
ACTIVATION_TOKEN = "act-v1:ce43d63a03a74ad9b06a9c23b1b164fd46123071efc316b6ce17b2d71ad58da0"
SOURCE_SHA = "cd9bd2f54b47433b176efb31a79f9a2bd6d38c6c"
RUNTIME_ACTOR = "6477ab815e8aecca7d1e8e1588e6e5eba0fab001"
RUNTIME_GENERATION = "g47-6477ab81-activation-only-20260826"
PRODUCTION_QUEUE = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue")
PRODUCTION_STATE = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state")
PRODUCTION_ACTOR_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor")
EVIDENCE_ROOT = Path(__file__).resolve().parent


def compact_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def directory_digest(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "root": str(root), "file_count": 0, "digest": None}
    entries: list[str] = []
    total_bytes = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file() and not item.is_symlink()):
        data = path.read_bytes()
        total_bytes += len(data)
        entries.append(f"{path.relative_to(root).as_posix()}\0{sha256_bytes(data)}\0{len(data)}")
    digest = sha256_bytes("\n".join(entries).encode("utf-8"))
    return {
        "exists": True,
        "root": str(root),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "digest": digest,
    }


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def service_snapshot() -> dict[str, Any]:
    uid = os.getuid()
    services: dict[str, Any] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        target = f"gui/{uid}/{label}"
        completed = subprocess.run(
            ["launchctl", "print", target],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (completed.stdout + completed.stderr).strip()
        stopped = completed.returncode != 0 and "Could not find service" in output
        services[label] = {
            "target": target,
            "returncode": completed.returncode,
            "state": "STOPPED" if stopped else "LOADED",
            "output_sha256": sha256_bytes(output.encode("utf-8")),
        }
    return {
        "status": "STOPPED" if all(item["state"] == "STOPPED" for item in services.values()) else "LOADED",
        "services": services,
    }


def install_formal_environment(manifest_path: Path, barrier: Path, manifest: dict[str, Any]) -> dict[str, str | None]:
    keys = [
        "PANTHEON_FORMAL_RUNTIME",
        "PANTHEON_RUNTIME_MANIFEST",
        "PANTHEON_RUNTIME_MANIFEST_DIGEST",
        "PANTHEON_RUNTIME_GENERATION",
        "PANTHEON_RUNTIME_IDENTITY",
        "PANTHEON_RUNTIME_IDENTITY_DIGEST",
        "PANTHEON_RUNTIME_CODE_DIGEST",
        "PANTHEON_RUNTIME_CONFIG_VERSION",
        "PANTHEON_RUNTIME_ACTOR_ROOT",
        "PANTHEON_RUNTIME_ACTOR_HEAD",
        "PANTHEON_RUNTIME_QUEUE_ROOT",
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT",
        "PANTHEON_RUNTIME_LOG_ROOT",
        "PANTHEON_RUNTIME_PYTHON_EXECUTABLE",
        "PANTHEON_RUNTIME_UV_EXECUTABLE",
        "PANTHEON_RUNTIME_ACTIVATION_TOKEN",
        "PANTHEON_RUNTIME_SERVICE_LABEL",
        "AGY_GEMINI_V4_BROKER",
        "AGY_GEMINI_CREDENTIAL_POOL_FILE",
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
        "AGY_GEMINI_MODEL_ROUTE_CONFIG",
        "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST",
        "AGY_WRITER_MODEL",
        "AGY_REVIEWER_MODEL",
    ]
    previous = {key: os.environ.get(key) for key in keys}
    os.environ.update(
        {
            "PANTHEON_FORMAL_RUNTIME": "1",
            "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
            "PANTHEON_RUNTIME_MANIFEST_DIGEST": str(manifest["manifest_digest"]),
            "PANTHEON_RUNTIME_GENERATION": str(manifest["generation"]),
            "PANTHEON_RUNTIME_IDENTITY": str(manifest["identity"]),
            "PANTHEON_RUNTIME_IDENTITY_DIGEST": str(manifest["runtime_identity_digest"]),
            "PANTHEON_RUNTIME_CODE_DIGEST": str(manifest["runtime_digest"]),
            "PANTHEON_RUNTIME_CONFIG_VERSION": str(manifest["config_version"]),
            "PANTHEON_RUNTIME_ACTOR_ROOT": str(manifest["actor_root"]),
            "PANTHEON_RUNTIME_ACTOR_HEAD": str(manifest["actor_head"]),
            "PANTHEON_RUNTIME_QUEUE_ROOT": str(manifest["queue_root"]),
            "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": str(manifest["publisher_state_root"]),
            "PANTHEON_RUNTIME_LOG_ROOT": str(manifest["log_root"]),
            "PANTHEON_RUNTIME_PYTHON_EXECUTABLE": str(manifest["python_executable"]),
            "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(barrier),
            "PANTHEON_RUNTIME_SERVICE_LABEL": "com.pantheon.agy-gemini-coordinator",
            "AGY_GEMINI_MODEL_ROUTE_CONFIG": str(pipeline.MODEL_ROUTE_CONFIG_PATH),
            "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST": pipeline.MODEL_ROUTE_CONFIG_DIGEST,
        }
    )
    if "uv_executable" in manifest:
        os.environ["PANTHEON_RUNTIME_UV_EXECUTABLE"] = str(manifest["uv_executable"])
    for key in ("AGY_GEMINI_V4_BROKER", "AGY_GEMINI_CREDENTIAL_POOL_FILE", "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"):
        os.environ.pop(key, None)
    return previous


def restore_environment(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def run_brief(run_id: str, article_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "create",
        "source_commit": SOURCE_SHA,
        "articles": [
            {
                "matrix": {
                    "id": article_id,
                    "title": f"Synthetic title direction for {article_id}",
                    "intent": "bounded isolated acceptance",
                    "primaryKeyword": f"{article_id} acceptance keyword",
                },
                "target": {
                    "id": article_id,
                    "section": "astro",
                    "product": "astro",
                    "slug": article_id.lower(),
                    "serial": article_id.lower(),
                    "urlSlug": article_id.lower(),
                    "published": "2026-08-26",
                    "updated": "2026-08-26",
                    "primaryKeyword": f"{article_id} acceptance keyword",
                },
                "policy": {"schema_version": 1, "disclosure": "synthetic non-public acceptance"},
            }
        ],
    }


def write_run_dir(run_root: Path, run_id: str, article_id: str) -> Path:
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True)
    write_json(run_dir / "brief.json", run_brief(run_id, article_id))
    return run_dir


def request_for_job(queue_root: Path, job_id: str) -> dict[str, Any]:
    for folder in ("outbox", "processing", "archive"):
        path = queue_root / folder / f"{job_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise RuntimeError(f"request not found: {job_id}")


def failed_receipt(queue_root: Path, job_id: str) -> dict[str, Any] | None:
    path = queue_root / "failed" / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fail_generate_json(_role: str, _model: str, _prompt: str, _schema: dict[str, Any]) -> dict[str, Any]:
    raise GeminiApiFailure("API_TIMEOUT")


def observed_tick(run_dir: Path, queue_root: Path) -> dict[str, Any]:
    try:
        return coordinator.run_pipeline_tick(run_dir, queue_root)
    except Exception as error:
        write_json(
            EVIDENCE_ROOT / "tick-error.json",
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "run_id": run_dir.name,
            },
        )
        raise


def run_acceptance() -> dict[str, Any]:
    initial_status = git_output("status", "--short")
    initial_head = git_output("rev-parse", "HEAD")
    initial_services = service_snapshot()
    production_before = {
        "queue": directory_digest(PRODUCTION_QUEUE),
        "state": directory_digest(PRODUCTION_STATE),
    }
    tmp_root = Path(tempfile.mkdtemp(prefix="pantheon-automation-acceptance-c-", dir="/private/tmp")).resolve()
    cleanup: dict[str, Any] = {"tmp_root": str(tmp_root), "removed": False}
    previous_env: dict[str, str | None] | None = None
    previous_cwd: str | None = None
    machine: dict[str, Any] = {}
    try:
        actor_root = PRODUCTION_ACTOR_ROOT.resolve()
        queue_root = tmp_root / "queue"
        state_root = tmp_root / "state"
        log_root = tmp_root / "logs"
        run_root = tmp_root / "runs"
        ready_root = tmp_root / "ready"
        for path in (queue_root, state_root, log_root, run_root, ready_root):
            path.mkdir(parents=True)
        runtime_digest = sha256_bytes(f"{RUNTIME_ACTOR}:{CARD_ID}".encode("utf-8"))
        manifest = runtime_manifest.build_manifest(
            actor_root=actor_root,
            queue_root=queue_root,
            publisher_state_root=state_root,
            log_root=log_root,
            identity=f"acceptance-c:{RUNTIME_ACTOR}",
            runtime_digest=runtime_digest,
            config_version="acceptance-c-three-failures",
            generation=RUNTIME_GENERATION,
            actor_head=RUNTIME_ACTOR,
            python_executable=Path(sys.executable).resolve(),
        )
        manifest_path = tmp_root / "manifest.json"
        barrier = tmp_root / "activation.barrier"
        runtime_manifest.write_manifest(manifest_path, manifest)
        for label in runtime_manifest.SERVICE_LABELS:
            runtime_manifest.write_readiness_ack(ready_root, manifest, label)
        activation = runtime_manifest.activate_barrier(barrier, ready_root, manifest)
        previous_env = install_formal_environment(manifest_path, barrier, manifest)
        previous_cwd = os.getcwd()
        os.chdir(actor_root)
        runtime_pass = runtime_manifest.validate_runtime_tick(
            "com.pantheon.agy-gemini-coordinator",
            queue_root=queue_root,
            state_root=state_root,
            actor_root=actor_root,
            log_root=log_root,
        )

        fail_run_id = "acceptance-c-fail-three-20260826"
        next_run_id = "acceptance-c-next-identity-20260826"
        fail_run = write_run_dir(run_root, fail_run_id, "ACCEPTANCE-C-F")
        next_run = write_run_dir(run_root, next_run_id, "ACCEPTANCE-C-N")
        fail_state = coordinator.register_run(fail_run, queue_root, correlation_id="acceptance-c-f")
        next_state = coordinator.register_run(next_run, queue_root, correlation_id="acceptance-c-n")

        attempts: list[dict[str, Any]] = []
        for ordinal in range(1, 4):
            before_jobs = sorted(path.stem for path in (queue_root / "archive").glob("*.json")) if (queue_root / "archive").exists() else []
            summary = coordinator.cycle_once(
                queue_root,
                repo_root=actor_root,
                exact_run_ids=[fail_run_id],
                tick=observed_tick,
                process=lambda root, **_kwargs: process_once(root, generate_json=fail_generate_json, exact_run_ids=[fail_run_id]),
            )
            current = coordinator.read_run_state(fail_run, queue_root)
            if "last_job_id" not in current:
                raise RuntimeError(
                    "fail run did not enter external job pending: "
                    + compact_json({"summary": summary, "state": current})
                )
            job_id = str(current["last_job_id"])
            request = request_for_job(queue_root, job_id)
            failure = failed_receipt(queue_root, job_id)
            after_jobs = sorted(path.stem for path in (queue_root / "archive").glob("*.json")) if (queue_root / "archive").exists() else []
            attempts.append(
                {
                    "ordinal": ordinal,
                    "summary": summary,
                    "state_status": current["status"],
                    "job_id": job_id,
                    "transport_attempt": request.get("transport_attempt", 0),
                    "request_sha256": request["request_sha256"],
                    "failure_category": None if failure is None else failure.get("failure_category"),
                    "error_type": None if failure is None else failure.get("error_type"),
                    "error_code": None if failure is None else failure.get("error_code"),
                    "new_archived_jobs": sorted(set(after_jobs) - set(before_jobs)),
                }
            )

        terminal_summary = coordinator.cycle_once(
            queue_root,
            repo_root=actor_root,
            exact_run_ids=[fail_run_id],
            tick=observed_tick,
            process=lambda _root, **_kwargs: {"status": "idle"},
        )
        fail_terminal_state = coordinator.read_run_state(fail_run, queue_root)
        fourth_probe = coordinator.cycle_once(
            queue_root,
            repo_root=actor_root,
            exact_run_ids=[fail_run_id],
            tick=observed_tick,
            process=lambda _root, **_kwargs: {"status": "idle"},
        )
        before_next_state = coordinator.read_run_state(next_run, queue_root)
        next_summary = coordinator.cycle_once(
            queue_root,
            repo_root=actor_root,
            exact_run_ids=[next_run_id],
            tick=observed_tick,
            process=lambda _root, **_kwargs: {"status": "idle"},
        )
        after_next_state = coordinator.read_run_state(next_run, queue_root)
        next_request = request_for_job(queue_root, str(after_next_state["last_job_id"]))

        queue_snapshot_before_cleanup = {
            "runs": sorted(path.name for path in (queue_root / "runs").glob("*.json")),
            "outbox": sorted(path.name for path in (queue_root / "outbox").glob("*.json")) if (queue_root / "outbox").exists() else [],
            "archive": sorted(path.name for path in (queue_root / "archive").glob("*.json")) if (queue_root / "archive").exists() else [],
            "failed": sorted(path.name for path in (queue_root / "failed").glob("*.json")) if (queue_root / "failed").exists() else [],
        }
        machine = {
            "card_id": CARD_ID,
            "dispatch_key": DISPATCH_KEY,
            "activation_token": ACTIVATION_TOKEN,
            "source_sha": SOURCE_SHA,
            "cwd": str(REPO_ROOT),
            "head": initial_head,
            "initial_clean": initial_status == "",
            "service_state_before": initial_services,
            "production_before": production_before,
            "formal_runtime": {
                "actor": RUNTIME_ACTOR,
                "generation": RUNTIME_GENERATION,
                "manifest_digest": manifest["manifest_digest"],
                "runtime_identity_digest": manifest["runtime_identity_digest"],
                "activation_status": activation["status"],
                "runtime_tick_status": runtime_pass["status"],
                "task_queue_root": str(queue_root),
                "task_state_root": str(state_root),
                "task_log_root": str(log_root),
            },
            "registered": {
                "fail": fail_state,
                "next": next_state,
                "identities_different": fail_run_id != next_run_id,
            },
            "attempts": attempts,
            "terminal": {
                "summary": terminal_summary,
                "state": fail_terminal_state,
                "attempts_exactly_three": fail_terminal_state.get("transport_attempts") == 3,
                "terminal_manual_status": fail_terminal_state.get("status") == "failed",
                "failure_category": fail_terminal_state.get("failure_category"),
                "error_code": fail_terminal_state.get("error_code"),
            },
            "fourth_probe": {
                "summary": fourth_probe,
                "not_selected": fourth_probe.get("active") == 0 and fourth_probe.get("runner", {}).get("status") == "idle",
            },
            "advance": {
                "before_next_state": before_next_state,
                "summary": next_summary,
                "after_next_state": after_next_state,
                "next_request": {
                    "job_id": next_request["job_id"],
                    "namespace": next_request["namespace"],
                    "transport_attempt": next_request.get("transport_attempt", 0),
                    "request_sha256": next_request["request_sha256"],
                },
                "identity_different": fail_run_id != next_run_id,
                "entered_execution": after_next_state.get("status") == "active" and bool(after_next_state.get("last_job_id")),
            },
            "queue_snapshot_before_cleanup": queue_snapshot_before_cleanup,
            "zero_external_api": {
                "v4_broker": os.environ.get("AGY_GEMINI_V4_BROKER"),
                "credential_pool_file": os.environ.get("AGY_GEMINI_CREDENTIAL_POOL_FILE"),
                "fake_generate_json_calls": 3,
                "publisher_invoked": False,
                "writer_reviewer_api_invoked": False,
                "git_push_invoked": False,
                "tag_invoked": False,
                "public_url_invoked": False,
            },
        }
    finally:
        if previous_cwd is not None:
            os.chdir(previous_cwd)
        if previous_env is not None:
            restore_environment(previous_env)
        if tmp_root.exists() and tmp_root.name.startswith("pantheon-automation-acceptance-c-"):
            shutil.rmtree(tmp_root)
            cleanup["removed"] = not tmp_root.exists()
    production_after = {
        "queue": directory_digest(PRODUCTION_QUEUE),
        "state": directory_digest(PRODUCTION_STATE),
    }
    final_status = git_output("status", "--short")
    final_services = service_snapshot()
    machine["cleanup"] = cleanup
    machine["production_after"] = production_after
    machine["production_unchanged"] = production_before == production_after
    machine["service_state_after"] = final_services
    machine["final_clean"] = final_status == ""
    machine["status"] = (
        "DELIVERED_CANDIDATE"
        if machine["terminal"]["attempts_exactly_three"]
        and machine["terminal"]["terminal_manual_status"]
        and machine["fourth_probe"]["not_selected"]
        and machine["advance"]["identity_different"]
        and machine["advance"]["entered_execution"]
        and machine["production_unchanged"]
        and final_services["status"] == "STOPPED"
        and cleanup["removed"]
        else "BLOCKED"
    )
    write_json(EVIDENCE_ROOT / "machine-summary.json", machine)
    return machine


if __name__ == "__main__":
    result = run_acceptance()
    print(json.dumps({"status": result["status"], "evidence": str(EVIDENCE_ROOT / "machine-summary.json")}, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result["status"] == "DELIVERED_CANDIDATE" else 1)

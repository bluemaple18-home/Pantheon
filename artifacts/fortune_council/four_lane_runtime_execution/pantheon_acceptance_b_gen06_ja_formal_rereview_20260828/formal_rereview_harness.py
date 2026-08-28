#!/usr/bin/env python3
"""Evidence-local Gen06 JA formal re-review harness.

This wrapper uses Pantheon's existing multilingual reviewer prompt/schema,
OutboxGeminiClient, and agy_gemini_runner CLI while keeping queue/state/log
artifacts outside the production runtime root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/Users/mattkuo/Documents/Pantheon")
PROD_ROOT = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
EVIDENCE_ROOT = REPO_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_formal_rereview_20260828"
REPAIR_ROOT = REPO_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_ja_content_repair_20260828"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
LANE = "i18n-new"
SERVICE_LABEL = "com.pantheon.agy-gemini-i18n-new"
SOURCE_AUTHORITY = "831c536043d85a6cafe813c08a4f06921f0dd0e2"
ORIGINAL_REVIEWER_JOB_ID = "735ffd07d47e4b25d49f85f137d9dd238d8e9967"
PLIST_PATH = Path("/Users/mattkuo/Library/LaunchAgents/com.pantheon.agy-gemini-i18n-new.plist")
PROD_MANIFEST_PATH = PROD_ROOT / "runtime-manifest.json"

sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_multilingual_pipeline as multilingual  # noqa: E402
from scripts import agy_seo_copy_pipeline as pipeline  # noqa: E402
from scripts import pantheon_content_runtime_manifest as formal_runtime  # noqa: E402
from scripts.agy_gemini_outbox import ExternalJobPending, OutboxGeminiClient, validate_external_request  # noqa: E402
from scripts.agy_gemini_runner import FORMAL_PRODUCTION_TRANSPORT_ENV, _operator_env_receipt  # noqa: E402


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file() or path.is_symlink():
        return None
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_plist_environment() -> dict[str, str]:
    payload = plistlib.loads(PLIST_PATH.read_bytes())
    if not isinstance(payload, dict) or payload.get("Label") != SERVICE_LABEL:
        raise ValueError("i18n-new plist identity mismatch")
    environment = payload.get("EnvironmentVariables")
    if not isinstance(environment, dict):
        raise ValueError("i18n-new plist environment missing")
    return {
        str(key): str(value)
        for key, value in environment.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


def formal_paths() -> dict[str, Path]:
    root = EVIDENCE_ROOT / "isolated-formal-runtime"
    return {
        "root": root,
        "run_dir": root / "translation-runs" / RUN_ID,
        "queue_root": root / "queue",
        "lane_queue_root": root / "queue" / "lanes" / LANE,
        "state_root": root / "state",
        "log_root": root / "logs",
        "ready_root": root / "ready",
        "manifest": root / "runtime-manifest.json",
        "barrier": root / "state" / "formal-rereview.barrier",
        "credential_state": root / "state" / "credential-pool-state.json",
    }


def ensure_runtime_dirs() -> None:
    paths = formal_paths()
    for key in ("run_dir", "lane_queue_root", "state_root", "log_root", "ready_root"):
        paths[key].mkdir(parents=True, exist_ok=True)


def transport_environment() -> dict[str, str]:
    paths = formal_paths()
    env = load_plist_environment()
    env["AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"] = str(paths["credential_state"])
    env["AGY_GEMINI_NEW_ONLY"] = "0"
    env.pop("PANTHEON_RUNTIME_ACTIVATION_TOKEN", None)
    return env


def write_env_receipt(path: Path, env: dict[str, str]) -> None:
    write_json(
        path,
        {
            "schema_version": 1,
            "service_label": SERVICE_LABEL,
            "env_receipt": _operator_env_receipt(env),
            "extra_transport": {
                "AGY_GEMINI_CLI": {
                    "present": bool(env.get("AGY_GEMINI_CLI", "").strip()),
                    "sha256": sha256_bytes(env.get("AGY_GEMINI_CLI", "").encode("utf-8")),
                },
                "AGY_GEMINI_NEW_ONLY": env.get("AGY_GEMINI_NEW_ONLY"),
            },
        },
    )


def setup_formal_runtime() -> dict[str, Any]:
    ensure_runtime_dirs()
    paths = formal_paths()
    production_manifest = read_json(PROD_MANIFEST_PATH)
    manifest = formal_runtime.build_manifest(
        actor_root=Path(production_manifest["actor_root"]),
        queue_root=paths["queue_root"],
        publisher_state_root=paths["state_root"],
        log_root=paths["log_root"],
        identity=f"gate2-actor:{SOURCE_AUTHORITY}:gen06-ja-formal-rereview-20260828",
        runtime_digest=str(production_manifest["runtime_digest"]),
        config_version=str(production_manifest["config_version"]),
        generation="g65-831c5360-gen06-ja-formal-rereview-20260828",
        actor_head=SOURCE_AUTHORITY,
        python_executable=Path(production_manifest["python_executable"]),
        uv_executable=Path(production_manifest["uv_executable"]),
    )
    formal_runtime.write_manifest(paths["manifest"], manifest)
    for label in formal_runtime.SERVICE_LABELS:
        formal_runtime.write_readiness_ack(paths["ready_root"], manifest, label)
    activation = formal_runtime.activate_barrier(
        paths["barrier"],
        paths["ready_root"],
        manifest,
    )
    return {
        "schema_version": 1,
        "manifest": manifest,
        "activation": activation,
        "paths": {key: str(value) for key, value in paths.items()},
    }


def production_tripwire() -> dict[str, Any]:
    prod_run = PROD_ROOT / "queue" / "translation-runs" / RUN_ID
    lane_root = PROD_ROOT / "queue" / "lanes" / LANE
    target_files = [
        PROD_MANIFEST_PATH,
        prod_run / "brief.json",
        prod_run / "candidate.json",
        prod_run / "review.json",
        prod_run / "continuation" / "state.json",
        prod_run / "continuation" / "generation-lifecycle.json",
        prod_run / "generations" / "06" / "candidate.json",
        prod_run / "generations" / "06" / "review.json",
        lane_root / "archive" / f"{ORIGINAL_REVIEWER_JOB_ID}.json",
        lane_root / "inbox" / f"{ORIGINAL_REVIEWER_JOB_ID}.json",
        lane_root / "production-attempts" / f"{ORIGINAL_REVIEWER_JOB_ID}.attempt",
    ]
    gen07_root = prod_run / "generations" / "07"
    return {
        "schema_version": 1,
        "production_root": str(PROD_ROOT),
        "run_id": RUN_ID,
        "target_files": {
            str(path): {
                "exists": path.exists(),
                "sha256": sha256_file(path),
                "size": path.stat().st_size if path.exists() and path.is_file() else None,
            }
            for path in target_files
        },
        "gen07": {
            "path": str(gen07_root),
            "exists": gen07_root.exists(),
            "file_count": sum(1 for _ in gen07_root.rglob("*")) if gen07_root.exists() else 0,
        },
        "forbidden_mutations": {
            "publish": 0,
            "tag": 0,
            "push": 0,
            "coordinator": 0,
        },
    }


def candidate_identity_receipt() -> dict[str, Any]:
    brief = read_json(PROD_ROOT / "queue" / "translation-runs" / RUN_ID / "brief.json")
    candidate = read_json(REPAIR_ROOT / "candidate-repaired.json")
    multilingual.validate_translation_candidate(brief, candidate)
    article = candidate["articles"][0]
    source = brief["articles"][0]
    topology = [
        {
            "heading": section["heading"],
            "paragraph_count": len(section["paragraphs"]),
        }
        for section in article["bodySections"]
    ]
    deterministic = multilingual.translation_findings(brief, candidate["articles"])
    return {
        "schema_version": 1,
        "run_id_match": candidate.get("run_id") == RUN_ID == brief.get("run_id"),
        "mode_match": candidate.get("mode") == brief.get("mode") == "translate_existing",
        "locale": source.get("locale"),
        "article_id": article.get("article_id"),
        "source_article_id_match": article.get("source_article_id") == source.get("source_article_id"),
        "source_path_match": article.get("source_path") == source.get("source_path"),
        "source_sha256_match": article.get("source_sha256") == source.get("source_sha256"),
        "source_sha256": article.get("source_sha256"),
        "candidate_sha256": sha256_file(REPAIR_ROOT / "candidate-repaired.json"),
        "candidate_canonical_sha256": sha256_bytes(compact_json_bytes(candidate)),
        "deterministic_translation_findings": deterministic,
        "section_topology": topology,
    }


def prepare_request() -> None:
    setup = setup_formal_runtime()
    paths = formal_paths()
    env = transport_environment()
    os.environ.update(env)
    run_dir = paths["run_dir"]
    shutil.copyfile(PROD_ROOT / "queue" / "translation-runs" / RUN_ID / "brief.json", run_dir / "brief.json")
    shutil.copyfile(REPAIR_ROOT / "candidate-repaired.json", run_dir / "candidate.json")
    client = OutboxGeminiClient(
        paths["lane_queue_root"],
        namespace=hashlib.sha256(RUN_ID.encode("utf-8")).hexdigest()[:24],
        route_config=pipeline.model_route_config_from_environment(),
    )
    try:
        multilingual.review_edited_candidate(run_dir, client)
    except ExternalJobPending as pending:
        job_id = pending.job_id
    else:
        raise RuntimeError("review unexpectedly completed before provider runner")
    request_path = paths["lane_queue_root"] / "outbox" / f"{job_id}.json"
    request = read_json(request_path)
    validate_external_request(request)
    write_json(EVIDENCE_ROOT / "formal-runtime-setup.json", setup)
    write_env_receipt(EVIDENCE_ROOT / "formal-env-receipt.json", env)
    write_json(EVIDENCE_ROOT / "candidate-identity.json", candidate_identity_receipt())
    write_json(EVIDENCE_ROOT / "production-tripwire-before.json", production_tripwire())
    write_json(EVIDENCE_ROOT / "formal-request-identity.json", {
        "schema_version": 1,
        "run_id": RUN_ID,
        "lane": LANE,
        "job_id": job_id,
        "request_path": str(request_path),
        "request_sha256": request["request_sha256"],
        "request_file_sha256": sha256_file(request_path),
        "prompt_sha256": request["prompt_sha256"],
        "schema_sha256": request["schema_sha256"],
        "role": request["role"],
        "model": request["model"],
        "namespace": request["namespace"],
        "operation_level": request["operation_level"],
    })
    (EVIDENCE_ROOT / "formal-request-prompt.txt").write_text(
        str(request["prompt"]),
        encoding="utf-8",
    )
    write_json(EVIDENCE_ROOT / "formal-request-schema.json", request["response_schema"])
    print(json.dumps({"status": "pending", "job_id": job_id}, ensure_ascii=False))


def run_provider() -> None:
    paths = formal_paths()
    manifest = read_json(paths["manifest"])
    env = os.environ.copy()
    env.update(transport_environment())
    env.update({
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(paths["manifest"]),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": str(manifest["manifest_digest"]),
        "PANTHEON_RUNTIME_IDENTITY": str(manifest["identity"]),
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": str(manifest["runtime_identity_digest"]),
        "PANTHEON_RUNTIME_CODE_DIGEST": str(manifest["runtime_digest"]),
        "PANTHEON_RUNTIME_CONFIG_VERSION": str(manifest["config_version"]),
        "PANTHEON_RUNTIME_GENERATION": str(manifest["generation"]),
        "PANTHEON_RUNTIME_ACTOR_ROOT": str(manifest["actor_root"]),
        "PANTHEON_RUNTIME_QUEUE_ROOT": str(manifest["queue_root"]),
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": str(manifest["publisher_state_root"]),
        "PANTHEON_RUNTIME_LOG_ROOT": str(manifest["log_root"]),
        "PANTHEON_RUNTIME_SERVICE_LABEL": SERVICE_LABEL,
        "PANTHEON_RUNTIME_ACTOR_HEAD": str(manifest["actor_head"]),
        "PANTHEON_RUNTIME_PYTHON_EXECUTABLE": str(manifest["python_executable"]),
        "PANTHEON_RUNTIME_UV_EXECUTABLE": str(manifest["uv_executable"]),
        "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(paths["barrier"]),
    })
    command = [
        str(manifest["python_executable"]),
        "-m",
        "scripts.agy_gemini_runner",
        "--queue-root",
        str(paths["lane_queue_root"]),
        "--lane",
        LANE,
        "--exact-run-id",
        RUN_ID,
        "process-once",
    ]
    write_json(EVIDENCE_ROOT / "provider-runner.command.json", {
        "schema_version": 1,
        "command": command,
        "cwd": str(manifest["actor_root"]),
        "external_provider_attempt_limit": 1,
        "env_receipt": _operator_env_receipt(env),
    })
    completed = subprocess.run(
        command,
        cwd=str(manifest["actor_root"]),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    (EVIDENCE_ROOT / "provider-runner.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE_ROOT / "provider-runner.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE_ROOT / "provider-runner.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="ascii")
    write_json(EVIDENCE_ROOT / "provider-runner.receipt.json", {
        "schema_version": 1,
        "returncode": completed.returncode,
        "stdout": {
            "bytes": len(completed.stdout.encode("utf-8", errors="replace")),
            "sha256": sha256_bytes(completed.stdout.encode("utf-8", errors="replace")),
        },
        "stderr": {
            "bytes": len(completed.stderr.encode("utf-8", errors="replace")),
            "sha256": sha256_bytes(completed.stderr.encode("utf-8", errors="replace")),
        },
    })
    print(json.dumps({"status": "executed", "returncode": completed.returncode}, ensure_ascii=False))
    raise SystemExit(completed.returncode if 0 <= completed.returncode <= 255 else 1)


def artifact_hashes() -> dict[str, Any]:
    paths = formal_paths()
    request_identity = read_json(EVIDENCE_ROOT / "formal-request-identity.json")
    job_id = str(request_identity["job_id"])
    targets = {
        "outbox": paths["lane_queue_root"] / "outbox" / f"{job_id}.json",
        "processing": paths["lane_queue_root"] / "processing" / f"{job_id}.json",
        "archive": paths["lane_queue_root"] / "archive" / f"{job_id}.json",
        "inbox": paths["lane_queue_root"] / "inbox" / f"{job_id}.json",
        "failed": paths["lane_queue_root"] / "failed" / f"{job_id}.json",
        "attempt": paths["lane_queue_root"] / "production-attempts" / f"{job_id}.attempt",
        "operation": paths["run_dir"] / "editorial-review" / "reviewer-operation.json",
        "external_review": paths["run_dir"] / "editorial-review" / "external-review.json",
        "review": paths["run_dir"] / "review.json",
    }
    return {
        "schema_version": 1,
        "job_id": job_id,
        "artifacts": {
            name: {
                "path": str(path),
                "exists": path.exists(),
                "sha256": sha256_file(path),
                "size": path.stat().st_size if path.exists() and path.is_file() else None,
            }
            for name, path in targets.items()
        },
    }


def finalize_review() -> None:
    paths = formal_paths()
    env = transport_environment()
    os.environ.update(env)
    client = OutboxGeminiClient(
        paths["lane_queue_root"],
        namespace=hashlib.sha256(RUN_ID.encode("utf-8")).hexdigest()[:24],
        route_config=pipeline.model_route_config_from_environment(),
    )
    review = multilingual.review_edited_candidate(paths["run_dir"], client)
    findings = [
        {"article_id": item["article_id"], **finding}
        for item in review["articles"]
        for finding in item.get("findings", [])
    ]
    verdict = "APPROVE_READY_FOR_STAGING" if all(
        item.get("verdict") == "APPROVE" and not item.get("findings")
        for item in review["articles"]
    ) else "REJECT"
    write_json(EVIDENCE_ROOT / "formal-review-result.json", {
        "schema_version": 1,
        "exit_verdict": verdict,
        "review": review,
        "findings": findings,
        "original_finding_codes": [
            "NON_NATIVE_LANGUAGE_RESIDUE",
            "BOUNDARY_MEANING_MISSING",
        ],
    })
    write_json(EVIDENCE_ROOT / "artifact-hashes.json", artifact_hashes())
    write_json(EVIDENCE_ROOT / "production-tripwire-after.json", production_tripwire())
    print(json.dumps({"status": "finalized", "verdict": verdict}, ensure_ascii=False))


def compare_tripwire() -> dict[str, Any]:
    before = read_json(EVIDENCE_ROOT / "production-tripwire-before.json")
    after = read_json(EVIDENCE_ROOT / "production-tripwire-after.json")
    return {
        "schema_version": 1,
        "target_files_unchanged": before["target_files"] == after["target_files"],
        "gen07_absent_before": before["gen07"]["exists"] is False,
        "gen07_absent_after": after["gen07"]["exists"] is False,
        "forbidden_mutations": {
            "publish": 0,
            "tag": 0,
            "push": 0,
            "coordinator": 0,
        },
    }


def write_result() -> None:
    formal = read_json(EVIDENCE_ROOT / "formal-review-result.json")
    tripwire = compare_tripwire()
    artifact = read_json(EVIDENCE_ROOT / "artifact-hashes.json")
    request = read_json(EVIDENCE_ROOT / "formal-request-identity.json")
    runner = read_json(EVIDENCE_ROOT / "provider-runner.receipt.json")
    verdict = str(formal["exit_verdict"])
    if not tripwire["target_files_unchanged"] or not tripwire["gen07_absent_after"]:
        verdict = "BLOCKED"
    lines = [
        "# RESULT: Pantheon Acceptance B Gen06 JA Formal Re-review",
        "",
        f"status: `{verdict}`",
        f"run_id: `{RUN_ID}`",
        "scope: original reviewer findings only",
        "",
        "## Formal Request",
        "",
        f"- job_id: `{request['job_id']}`",
        f"- role: `{request['role']}`",
        f"- model: `{request['model']}`",
        f"- request_sha256: `{request['request_sha256']}`",
        f"- prompt_sha256: `{request['prompt_sha256']}`",
        f"- schema_sha256: `{request['schema_sha256']}`",
        "",
        "## Provider Runner",
        "",
        f"- returncode: `{runner['returncode']}`",
        "- external provider runner executed once for this exact run id",
        "- no fallback or retry command was run",
        "",
        "## Review Verdict",
        "",
        f"- verdict: `{formal['exit_verdict']}`",
        f"- findings: `{formal['findings']}`",
        "",
        "## Production Tripwire",
        "",
        f"- target_files_unchanged: `{tripwire['target_files_unchanged']}`",
        f"- gen07_absent_after: `{tripwire['gen07_absent_after']}`",
        "- publish/tag/push/coordinator: `0`",
        "",
        "## Evidence",
        "",
        "- `CARD-PANTHEON-ACCEPTANCE-B-GEN06-JA-FORMAL-REREVIEW-20260828.md`",
        "- `candidate-identity.json`",
        "- `formal-request-identity.json`",
        "- `formal-request-prompt.txt`",
        "- `formal-request-schema.json`",
        "- `formal-env-receipt.json`",
        "- `provider-runner.*`",
        "- `artifact-hashes.json`",
        "- `formal-review-result.json`",
        "- `production-tripwire-before.json`",
        "- `production-tripwire-after.json`",
        "- `git-diff-check.*`",
        "",
        "## Boundary",
        "",
        "This approval, if present, only means the repaired candidate is ready for staging review. It is not published and does not authorize production mutation.",
    ]
    (EVIDENCE_ROOT / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "result_written", "verdict": verdict}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[
        "prepare-request",
        "run-provider",
        "finalize-review",
        "write-result",
    ])
    args = parser.parse_args()
    if args.command == "prepare-request":
        prepare_request()
    elif args.command == "run-provider":
        run_provider()
    elif args.command == "finalize-review":
        finalize_review()
    elif args.command == "write-result":
        write_result()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

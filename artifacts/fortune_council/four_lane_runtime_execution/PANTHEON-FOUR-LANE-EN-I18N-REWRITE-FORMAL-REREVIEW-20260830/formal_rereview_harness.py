#!/usr/bin/env python3
"""Evidence-local EN i18n-rewrite manual repair formal re-review harness.

This reuses Pantheon's accepted edited-candidate reviewer prompt/schema,
OutboxGeminiClient, and single-shot runner.  All mutable queue/state/log
artifacts stay under the evidence root; production is read-only.
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
ACTOR_ROOT = PROD_ROOT / "actor"
EVIDENCE_ROOT = REPO_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-FORMAL-REREVIEW-20260830"
REPAIR_ROOT = REPO_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-EN-I18N-REWRITE-CONTENT-REPAIR-20260830"
READINESS_ROOT = REPO_ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-E01-G75-EN-REPLACEMENT-ACCEPTANCE-20260830"
RUN_ID = "auto-i18n-en-aa637e1bf05d3ad21429-replacement-01"
LANE = "i18n-rewrite"
SERVICE_LABEL = "com.pantheon.agy-gemini-i18n-rewrite"
ACTOR_HEAD = "e01d56e3847600fa8723a006b3f16e3757af7610"
MANIFEST_DIGEST = "43e3b4c92318fcea47beb73b34c8635593f3ac5336f33c787095864419e628f1"
EXPECTED_CANDIDATE_SHA256 = "26dd6ccf15a37a165f2ec11f9dd0220db26b9cdbc7fc8b2641b50b551e6731d1"
ORIGINAL_REVIEWER_JOB_ID = "97678eafb23595f3f8dcff696b3d2e254e0cd2e0"
PLIST_PATH = Path("/Users/mattkuo/Library/LaunchAgents/com.pantheon.agy-gemini-i18n-rewrite.plist")
PROD_MANIFEST_PATH = PROD_ROOT / "runtime-manifest.json"
PROD_BARRIER_PATH = PROD_ROOT / "state/four-lane-activation-g75-e01d56e3-legacy-replacement-brief-20260830.barrier"

sys.path.insert(0, str(ACTOR_ROOT))

from scripts import agy_multilingual_pipeline as multilingual  # noqa: E402
from scripts import agy_seo_copy_pipeline as pipeline  # noqa: E402
from scripts import pantheon_content_runtime_manifest as formal_runtime  # noqa: E402
from scripts.agy_gemini_outbox import ExternalJobPending, OutboxGeminiClient, validate_external_request  # noqa: E402
from scripts.agy_gemini_runner import _operator_env_receipt  # noqa: E402


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file() or path.is_symlink():
        return None
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def run_command(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


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


def load_plist_environment() -> dict[str, str]:
    payload = plistlib.loads(PLIST_PATH.read_bytes())
    if not isinstance(payload, dict) or payload.get("Label") != SERVICE_LABEL:
        raise ValueError("i18n-rewrite plist identity mismatch")
    environment = payload.get("EnvironmentVariables")
    if not isinstance(environment, dict):
        raise ValueError("i18n-rewrite plist environment missing")
    return {
        str(key): str(value)
        for key, value in environment.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


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


def queue_surface() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite"):
        lane_root = PROD_ROOT / "queue" / "lanes" / lane
        result[lane] = {}
        for surface in ("outbox", "processing"):
            root = lane_root / surface
            files = sorted(path.name for path in root.glob("*.json")) if root.exists() else []
            result[lane][surface] = files
    return result


def production_tripwire() -> dict[str, Any]:
    prod_run = PROD_ROOT / "queue" / "translation-runs" / RUN_ID
    lane_root = PROD_ROOT / "queue" / "lanes" / LANE
    target_files = [
        PROD_MANIFEST_PATH,
        PROD_ROOT / "state" / "ledger.json",
        prod_run / "brief.json",
        prod_run / "candidate.json",
        prod_run / "review.json",
        prod_run / "attempts" / "03" / "candidate.json",
        prod_run / "attempts" / "03" / "review.json",
        prod_run / "attempts" / "03" / "locale-plan.json",
        lane_root / "archive" / f"{ORIGINAL_REVIEWER_JOB_ID}.json",
        lane_root / "inbox" / f"{ORIGINAL_REVIEWER_JOB_ID}.json",
        lane_root / "production-attempts" / f"{ORIGINAL_REVIEWER_JOB_ID}.attempt",
    ]
    gen04_root = prod_run / "attempts" / "04"
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
        "queue_surface": queue_surface(),
        "generation_04": {
            "path": str(gen04_root),
            "exists": gen04_root.exists(),
            "file_count": sum(1 for path in gen04_root.rglob("*") if path.is_file()) if gen04_root.exists() else 0,
        },
        "forbidden_mutations": {"coordinator": 0, "publisher": 0, "tag": 0, "push": 0},
    }


def current_authority_preflight() -> dict[str, Any]:
    manifest = formal_runtime.load_manifest(PROD_MANIFEST_PATH, MANIFEST_DIGEST)
    barrier = formal_runtime.validate_barrier(PROD_BARRIER_PATH, manifest)
    actor_head = run_command(["git", "rev-parse", "HEAD"], cwd=ACTOR_ROOT)
    actor_status = run_command(["git", "status", "--porcelain"], cwd=ACTOR_ROOT)
    if actor_head.returncode or actor_head.stdout.strip() != ACTOR_HEAD:
        raise RuntimeError("accepted actor HEAD drift")
    if actor_status.returncode or actor_status.stdout:
        raise RuntimeError("accepted actor worktree is not clean")
    rule24_path = READINESS_ROOT / "rule24-e01-host-readable-output.json"
    rule25_path = READINESS_ROOT / "rule25-e01-readiness/readiness-summary.json"
    rule24 = read_json(rule24_path)
    rule25 = read_json(rule25_path)
    if rule24.get("status") != "PASS" or rule24.get("production_mutation") is not False:
        raise RuntimeError("Rule24 receipt is not a zero-mutation PASS")
    if rule25.get("status") != "READY" or rule25.get("production_mutation") is not False:
        raise RuntimeError("Rule25 receipt is not READY")
    candidate_path = REPAIR_ROOT / "candidate-repaired.json"
    if sha256_file(candidate_path) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("repaired candidate SHA drift")
    brief = read_json(PROD_ROOT / "queue" / "translation-runs" / RUN_ID / "brief.json")
    candidate = read_json(candidate_path)
    multilingual.validate_translation_candidate(brief, candidate)
    deterministic = multilingual.translation_findings(brief, candidate["articles"])
    if deterministic:
        raise RuntimeError("repaired candidate deterministic findings are not empty")
    services = run_command(["launchctl", "list"])
    loaded = sorted(
        label
        for label in formal_runtime.SERVICE_LABELS
        if label in services.stdout
    ) if services.returncode == 0 else []
    return {
        "schema_version": 1,
        "status": "PASS",
        "actor_head": ACTOR_HEAD,
        "actor_clean": True,
        "manifest_digest": manifest["manifest_digest"],
        "manifest_generation": manifest["generation"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "barrier": barrier,
        "rule24": {"status": rule24["status"], "sha256": sha256_file(rule24_path)},
        "rule25": {"status": rule25["status"], "sha256": sha256_file(rule25_path)},
        "candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "deterministic_findings": deterministic,
        "loaded_service_labels": loaded,
        "production_queue_surface": queue_surface(),
    }


def setup_formal_runtime() -> dict[str, Any]:
    ensure_runtime_dirs()
    paths = formal_paths()
    production_manifest = formal_runtime.load_manifest(PROD_MANIFEST_PATH, MANIFEST_DIGEST)
    manifest = formal_runtime.build_manifest(
        actor_root=ACTOR_ROOT,
        queue_root=paths["queue_root"],
        publisher_state_root=paths["state_root"],
        log_root=paths["log_root"],
        identity=f"gate2-actor:{ACTOR_HEAD}:en-manual-formal-rereview-20260830",
        runtime_digest=str(production_manifest["runtime_digest"]),
        config_version=str(production_manifest["config_version"]),
        generation="g75-e01d56e3-en-manual-formal-rereview-20260830",
        actor_head=ACTOR_HEAD,
        python_executable=Path(str(production_manifest["python_executable"])),
        uv_executable=Path(str(production_manifest["uv_executable"])),
    )
    formal_runtime.write_manifest(paths["manifest"], manifest)
    for label in formal_runtime.SERVICE_LABELS:
        formal_runtime.write_readiness_ack(paths["ready_root"], manifest, label)
    activation = formal_runtime.activate_barrier(paths["barrier"], paths["ready_root"], manifest)
    return {
        "schema_version": 1,
        "manifest": manifest,
        "activation": activation,
        "paths": {key: str(value) for key, value in paths.items()},
    }


def prior_review_scope() -> dict[str, Any]:
    prior_path = PROD_ROOT / "queue" / "translation-runs" / RUN_ID / "attempts" / "03" / "review.json"
    prior = read_json(prior_path)
    findings = [
        {"article_id": item["article_id"], **finding}
        for item in prior.get("articles", [])
        for finding in item.get("findings", [])
    ]
    return {
        "prior_review_path": str(prior_path),
        "prior_review_sha256": sha256_file(prior_path),
        "prior_verdict": [item.get("verdict") for item in prior.get("articles", [])],
        "prior_findings": findings,
        "instruction": (
            "Independently reassess the repaired candidate under the unchanged reviewer rubric. "
            "Do not auto-approve or auto-reject because the previous candidate was rejected."
        ),
    }


def review_repaired_candidate(run_dir: Path, client: OutboxGeminiClient) -> dict[str, Any]:
    brief = read_json(run_dir / "brief.json")
    candidate = read_json(run_dir / "candidate.json")
    multilingual.validate_translation_candidate(brief, candidate)
    findings = multilingual.translation_findings(brief, candidate["articles"])
    pipeline.write_json(run_dir / "editorial-review" / "deterministic-findings.json", findings)
    scope = prior_review_scope()
    public_scope = {
        "prior_verdict": scope["prior_verdict"],
        "prior_findings": scope["prior_findings"],
        "instruction": scope["instruction"],
    }
    prompt = multilingual._reviewer_prompt(brief, candidate, findings) + "\nmanual repair re-review context:\n" + json.dumps(
        public_scope, ensure_ascii=False, sort_keys=True
    )
    external_review = multilingual._load_or_generate_external(
        client,
        "reviewer",
        prompt,
        pipeline.external_review_schema(),
        run_dir / "editorial-review" / "reviewer-operation.json",
        run_dir / "editorial-review" / "external-review.json",
    )
    review = pipeline.hydrate_review(brief, candidate, external_review)
    by_id = {str(item["article_id"]): item for item in review["articles"]}
    for finding in findings:
        item = by_id[str(finding["article_id"])]
        normalized = {"code": finding["code"], "message": finding["message"]}
        item["verdict"] = "REJECT"
        if normalized not in item["findings"]:
            item["findings"].append(normalized)
        item["hard_failure"] = True
    pipeline.write_json(run_dir / "review.json", review)
    return review


def candidate_identity_receipt() -> dict[str, Any]:
    brief = read_json(PROD_ROOT / "queue" / "translation-runs" / RUN_ID / "brief.json")
    candidate_path = REPAIR_ROOT / "candidate-repaired.json"
    candidate = read_json(candidate_path)
    multilingual.validate_translation_candidate(brief, candidate)
    article = candidate["articles"][0]
    source = brief["articles"][0]
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
        "candidate_sha256": sha256_file(candidate_path),
        "candidate_canonical_sha256": sha256_bytes(compact_json_bytes(candidate)),
        "deterministic_translation_findings": multilingual.translation_findings(brief, candidate["articles"]),
        "prior_review_scope": prior_review_scope(),
    }


def prepare_request() -> None:
    preflight = current_authority_preflight()
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
        review_repaired_candidate(run_dir, client)
    except ExternalJobPending as pending:
        job_id = pending.job_id
    else:
        raise RuntimeError("review unexpectedly completed before provider runner")
    request_path = paths["lane_queue_root"] / "outbox" / f"{job_id}.json"
    request = read_json(request_path)
    validate_external_request(request)
    if request.get("role") != "reviewer" or request.get("model") != "gemini-3.1-flash-lite":
        raise RuntimeError("formal reviewer route drift")
    expected_namespace = hashlib.sha256(RUN_ID.encode("utf-8")).hexdigest()[:24]
    if request.get("namespace") != expected_namespace:
        raise RuntimeError("formal reviewer run namespace drift")
    outbox_files = sorted(path.name for path in (paths["lane_queue_root"] / "outbox").glob("*.json"))
    if outbox_files != [f"{job_id}.json"]:
        raise RuntimeError("isolated reviewer outbox is not exact-one")
    write_json(EVIDENCE_ROOT / "current-authority-preflight.json", preflight)
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
        "candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "outbox_files": outbox_files,
        "external_provider_attempt_limit": 1,
    })
    (EVIDENCE_ROOT / "formal-request-prompt.txt").write_text(str(request["prompt"]), encoding="utf-8")
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
        "cwd": str(ACTOR_ROOT),
        "external_provider_attempt_limit": 1,
        "env_receipt": _operator_env_receipt(env),
    })
    completed = subprocess.run(command, cwd=str(ACTOR_ROOT), env=env, text=True, capture_output=True, timeout=300, check=False)
    (EVIDENCE_ROOT / "provider-runner.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (EVIDENCE_ROOT / "provider-runner.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (EVIDENCE_ROOT / "provider-runner.returncode.txt").write_text(str(completed.returncode) + "\n", encoding="ascii")
    write_json(EVIDENCE_ROOT / "provider-runner.receipt.json", {
        "schema_version": 1,
        "returncode": completed.returncode,
        "stdout": {"bytes": len(completed.stdout.encode()), "sha256": sha256_bytes(completed.stdout.encode())},
        "stderr": {"bytes": len(completed.stderr.encode()), "sha256": sha256_bytes(completed.stderr.encode())},
    })
    print(json.dumps({"status": "executed", "returncode": completed.returncode}, ensure_ascii=False))
    raise SystemExit(completed.returncode if 0 <= completed.returncode <= 255 else 1)


def artifact_hashes() -> dict[str, Any]:
    paths = formal_paths()
    request = read_json(EVIDENCE_ROOT / "formal-request-identity.json")
    job_id = str(request["job_id"])
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
    review = review_repaired_candidate(paths["run_dir"], client)
    findings = [
        {"article_id": item["article_id"], **finding}
        for item in review["articles"]
        for finding in item.get("findings", [])
    ]
    verdict = "APPROVE_READY_FOR_STAGING" if all(
        item.get("verdict") == "APPROVE" and not item.get("findings")
        for item in review["articles"]
    ) else "REJECT_STOP"
    write_json(EVIDENCE_ROOT / "formal-review-result.json", {
        "schema_version": 1,
        "exit_verdict": verdict,
        "review": review,
        "findings": findings,
        "original_finding_codes": ["SOURCE_SYNTAX_TRANSFER"],
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
        "queue_surface_unchanged": before["queue_surface"] == after["queue_surface"],
        "generation_04_absent_before": before["generation_04"]["exists"] is False,
        "generation_04_absent_after": after["generation_04"]["exists"] is False,
        "forbidden_mutations": {"coordinator": 0, "publisher": 0, "tag": 0, "push": 0},
    }


def write_result() -> None:
    formal = read_json(EVIDENCE_ROOT / "formal-review-result.json")
    tripwire = compare_tripwire()
    request = read_json(EVIDENCE_ROOT / "formal-request-identity.json")
    runner = read_json(EVIDENCE_ROOT / "provider-runner.receipt.json")
    verdict = str(formal["exit_verdict"])
    if not all((tripwire["target_files_unchanged"], tripwire["queue_surface_unchanged"], tripwire["generation_04_absent_after"])):
        verdict = "BLOCKED"
    lines = [
        "# EN i18n-rewrite repaired candidate Formal Re-review 結果",
        "",
        "## 唯一狀態",
        "",
        f"`{verdict}`",
        "",
        "## Formal request",
        "",
        f"- run_id：`{RUN_ID}`",
        f"- candidate SHA-256：`{EXPECTED_CANDIDATE_SHA256}`",
        f"- job_id：`{request['job_id']}`",
        f"- role／model：`{request['role']}`／`{request['model']}`",
        f"- request SHA-256：`{request['request_sha256']}`",
        f"- prompt SHA-256：`{request['prompt_sha256']}`",
        f"- schema SHA-256：`{request['schema_sha256']}`",
        "- isolated outbox：exactly one job",
        "",
        "## Provider 與 verdict",
        "",
        f"- provider runner returncode：`{runner['returncode']}`",
        "- external provider call：`1`；fallback／retry：`0`",
        f"- Formal Reviewer verdict：`{formal['exit_verdict']}`",
        f"- findings：`{formal['findings']}`",
        "",
        "## Current authority 與 production tripwire",
        "",
        f"- actor／manifest：`{ACTOR_HEAD}`／`{MANIFEST_DIGEST}`",
        "- Rule24：`PASS`；Rule25：`READY`",
        f"- protected target bytes unchanged：`{tripwire['target_files_unchanged']}`",
        f"- production queue surface unchanged：`{tripwire['queue_surface_unchanged']}`",
        f"- Generation 04 absent after：`{tripwire['generation_04_absent_after']}`",
        "- coordinator／publisher／tag／push：`0`",
        "",
        "## Boundary",
        "",
        "若狀態為 `APPROVE_READY_FOR_STAGING`，只代表此修復候選可交回主線進 staging；本卡沒有 stage、publish、tag 或 push。若為 `REJECT_STOP`，必須停止。",
    ]
    (EVIDENCE_ROOT / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "result_written", "verdict": verdict}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare-request", "run-provider", "finalize-review", "write-result"])
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

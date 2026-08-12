from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.agy_gemini_outbox import create_external_request
from scripts.agy_gemini_runner import process_once
from scripts import pantheon_content_runtime_manifest as runtime_manifest


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


def test_runner_exact_run_ids_claims_only_matching_namespace(tmp_path: Path) -> None:
    old_request = create_external_request(
        tmp_path,
        namespace=hashlib.sha256(b"old-active-run").hexdigest()[:24],
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="舊 run",
        response_schema=SCHEMA,
    )
    target_request = create_external_request(
        tmp_path,
        namespace=hashlib.sha256(b"target-ko-run").hexdigest()[:24],
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: {"ok": True},
        exact_run_ids=["target-ko-run"],
    )

    assert result["status"] == "processed"
    assert result["job_id"] == target_request["job_id"]
    assert (tmp_path / "outbox" / f"{old_request['job_id']}.json").is_file()
    assert not (tmp_path / "processing" / f"{old_request['job_id']}.json").exists()


def test_runner_exact_run_ids_missing_target_does_not_claim_fallback(
    tmp_path: Path,
) -> None:
    old_request = create_external_request(
        tmp_path,
        namespace=hashlib.sha256(b"old-active-run").hexdigest()[:24],
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="舊 run",
        response_schema=SCHEMA,
    )

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: pytest.fail("missing target must not call provider"),
        exact_run_ids=["missing-target-run"],
    )

    assert result == {"status": "idle"}
    assert (tmp_path / "outbox" / f"{old_request['job_id']}.json").is_file()
    assert not (tmp_path / "processing").exists()


def test_formal_lane_rejects_manifest_drift_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    lane_root = queue / "lanes" / "new"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, lane_root, state, logs):
        path.mkdir(parents=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-lane",
        runtime_digest="2" * 64,
        generation="generation-lane",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST", str(manifest_path))
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST_DIGEST", manifest["manifest_digest"])
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", manifest["generation"])
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_IDENTITY_DIGEST", manifest["runtime_identity_digest"]
    )
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_SERVICE_LABEL", "com.pantheon.agy-gemini-new"
    )
    manifest_path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")

    result = process_once(
        lane_root,
        lane="new",
        generate_json=lambda *_args: pytest.fail("provider must not run"),
    )

    assert result["status"] == "failed"
    assert result["error_type"] == "RuntimeManifestError"
    assert not (lane_root / "processing").exists()

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import subprocess
import sys
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


def _set_formal_runner_env(
    monkeypatch: pytest.MonkeyPatch,
    manifest_path: Path,
    manifest: dict[str, object],
    service_label: str,
    activation_token: Path | None = None,
) -> None:
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST", str(manifest_path))
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST_DIGEST", str(manifest["manifest_digest"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_IDENTITY", str(manifest["identity"]))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_IDENTITY_DIGEST",
        str(manifest["runtime_identity_digest"]),
    )
    monkeypatch.setenv("PANTHEON_RUNTIME_CODE_DIGEST", str(manifest["runtime_digest"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_CONFIG_VERSION", str(manifest["config_version"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", str(manifest["generation"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_ACTOR_ROOT", str(manifest["actor_root"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(manifest["queue_root"]))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT",
        str(manifest["publisher_state_root"]),
    )
    monkeypatch.setenv("PANTHEON_RUNTIME_LOG_ROOT", str(manifest["log_root"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_SERVICE_LABEL", service_label)
    if activation_token is not None:
        monkeypatch.setenv("PANTHEON_RUNTIME_ACTIVATION_TOKEN", str(activation_token))


def _activate_formal_runtime(
    ready_root: Path,
    barrier: Path,
    manifest: dict[str, object],
) -> None:
    ready_root.mkdir(parents=True)
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready_root, manifest, label)
    runtime_manifest.activate_barrier(barrier, ready_root, manifest)


def test_formal_production_lane_missing_transport_env_blocks_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    lane_root = queue / "lanes" / "i18n-new"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, lane_root, state, logs):
        path.mkdir(parents=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-lane-missing-transport",
        runtime_digest="3" * 64,
        generation="generation-lane-transport",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    barrier = tmp_path / "activation.barrier"
    _activate_formal_runtime(tmp_path / "ready", barrier, manifest)
    _set_formal_runner_env(
        monkeypatch,
        manifest_path,
        manifest,
        "com.pantheon.agy-gemini-i18n-new",
        activation_token=barrier,
    )
    request = create_external_request(
        lane_root,
        namespace=hashlib.sha256(b"target-run").hexdigest()[:24],
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    before = {
        str(path.relative_to(lane_root)): path.read_bytes()
        for path in sorted(lane_root.rglob("*"))
        if path.is_file()
    }

    result = process_once(
        lane_root,
        lane="i18n-new",
        exact_run_ids=["target-run"],
        generate_json=lambda *_args: pytest.fail("provider must not run"),
    )

    assert result == {
        "status": "blocked",
        "reason": "formal_production_transport_env_missing",
        "service_label": "com.pantheon.agy-gemini-i18n-new",
        "missing_env": [
            "AGY_GEMINI_CREDENTIAL_POOL_FILE",
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
            "AGY_GEMINI_MODEL_ROUTE_CONFIG",
            "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST",
            "AGY_REVIEWER_MODEL",
            "AGY_WRITER_MODEL",
        ],
    }
    after = {
        str(path.relative_to(lane_root)): path.read_bytes()
        for path in sorted(lane_root.rglob("*"))
        if path.is_file()
    }
    assert after == before
    assert (lane_root / "outbox" / f"{request['job_id']}.json").is_file()
    assert not (lane_root / "processing").exists()
    assert not (lane_root / "archive").exists()
    assert not (lane_root / "failed").exists()
    assert not (lane_root / "production-attempts").exists()


def test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import agy_gemini_runner as runner

    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    barrier = state / "four-lane-activation-current.barrier"
    pool = tmp_path / "pool.json"
    route = tmp_path / "route.json"
    for path in (actor, queue, state, logs, ready):
        path.mkdir(parents=True)
    pool.write_text("{}", encoding="utf-8")
    route.write_text("{}", encoding="utf-8")
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-current",
        runtime_digest="4" * 64,
        generation="generation-current",
        python_executable=Path(sys.executable).resolve(),
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    plist_path = tmp_path / "com.pantheon.agy-gemini-i18n-new.plist"
    plist_path.write_bytes(
        plistlib.dumps(
            {
                "Label": "com.pantheon.agy-gemini-i18n-new",
                "EnvironmentVariables": {
                    "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
                    "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(queue / "pool-state.json"),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG": str(route),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST": "5" * 64,
                    "AGY_WRITER_MODEL": "writer-model",
                    "AGY_REVIEWER_MODEL": "reviewer-model",
                    "PANTHEON_RUNTIME_GENERATION": "stale-generation",
                },
                "ProgramArguments": ["stale-python", "-m", "stale.module"],
            }
        )
    )
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        return subprocess.CompletedProcess(command, 0, '{"status":"idle"}\n', "")

    result = runner.operator_exact_process_once(
        manifest_path=manifest_path,
        expected_digest=str(manifest["manifest_digest"]),
        barrier=barrier,
        service_label="com.pantheon.agy-gemini-i18n-new",
        ready_root=ready,
        plist=plist_path,
        exact_run_id="target-run",
        timeout=30,
        runner=fake_run,
    )

    command = captured["command"]
    env = captured["env"]
    assert result["status"] == "executed"
    assert result["returncode"] == 0
    assert command[:4] == [
        str(Path(sys.executable).resolve()),
        "-m",
        "scripts.pantheon_content_runtime_manifest",
        "barrier-exec",
    ]
    assert "--expected-digest" in command
    assert command[command.index("--expected-digest") + 1] == manifest["manifest_digest"]
    assert "stale-python" not in command
    assert env["AGY_GEMINI_CREDENTIAL_POOL_FILE"] == str(pool)
    assert env["PANTHEON_RUNTIME_GENERATION"] == manifest["generation"]
    assert env["PANTHEON_RUNTIME_QUEUE_ROOT"] == str(queue)
    assert env["PANTHEON_RUNTIME_SERVICE_LABEL"] == "com.pantheon.agy-gemini-i18n-new"
    assert result["env_receipt"]["AGY_GEMINI_CREDENTIAL_POOL_FILE"]["present"] is True
    assert "value" not in result["env_receipt"]["AGY_GEMINI_CREDENTIAL_POOL_FILE"]


def test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import agy_gemini_runner as runner

    def fake_operator_exact_process_once(**_kwargs: object) -> dict[str, object]:
        return {
            "status": "executed",
            "returncode": 42,
            "stdout_receipt": {"bytes": 61, "sha256": "6" * 64, "empty": False},
            "stderr_receipt": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(), "empty": True},
            "env_receipt": {},
            "child_result_summary": {"status": "failed", "error_type": "ValueError"},
        }

    monkeypatch.setattr(
        runner,
        "operator_exact_process_once",
        fake_operator_exact_process_once,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agy_gemini_runner.py",
            "--queue-root",
            str(tmp_path / "unused-queue"),
            "--exact-run-id",
            "target-run",
            "operator-exact-process-once",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--expected-digest",
            "7" * 64,
            "--barrier",
            str(tmp_path / "barrier"),
            "--service-label",
            "com.pantheon.agy-gemini-i18n-new",
            "--ready-root",
            str(tmp_path / "ready"),
            "--plist",
            str(tmp_path / "service.plist"),
        ],
    )

    exit_code = runner.main()

    printed = capsys.readouterr().out
    payload = json.loads(printed)
    assert exit_code == 42
    assert payload["status"] == "executed"
    assert payload["returncode"] == 42
    assert payload["child_result_summary"] == {
        "status": "failed",
        "error_type": "ValueError",
    }
    assert "stdout" not in payload
    assert "stderr" not in payload
    assert "raw-secret" not in printed


def test_operator_exact_process_summarizes_last_json_line_without_raw_output(
    tmp_path: Path,
) -> None:
    from scripts import agy_gemini_runner as runner

    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    barrier = state / "four-lane-activation-current.barrier"
    pool = tmp_path / "pool.json"
    route = tmp_path / "route.json"
    for path in (actor, queue, state, logs, ready):
        path.mkdir(parents=True)
    pool.write_text("{}", encoding="utf-8")
    route.write_text("{}", encoding="utf-8")
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-current-multiline",
        runtime_digest="8" * 64,
        generation="generation-current-multiline",
        python_executable=Path(sys.executable).resolve(),
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    plist_path = tmp_path / "com.pantheon.agy-gemini-i18n-new.plist"
    plist_path.write_bytes(
        plistlib.dumps(
            {
                "Label": "com.pantheon.agy-gemini-i18n-new",
                "EnvironmentVariables": {
                    "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
                    "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(queue / "pool-state.json"),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG": str(route),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST": "9" * 64,
                    "AGY_WRITER_MODEL": "writer-model",
                    "AGY_REVIEWER_MODEL": "reviewer-model",
                },
                "ProgramArguments": ["stale-python", "-m", "stale.module"],
            }
        )
    )

    def fake_run(
        command: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            42,
            'banner raw-secret\n{"status":"failed","error_type":"ValueError","secret":"raw-secret"}\n',
            "stderr raw-secret",
        )

    result = runner.operator_exact_process_once(
        manifest_path=manifest_path,
        expected_digest=str(manifest["manifest_digest"]),
        barrier=barrier,
        service_label="com.pantheon.agy-gemini-i18n-new",
        ready_root=ready,
        plist=plist_path,
        exact_run_id="target-run",
        timeout=30,
        runner=fake_run,
    )
    encoded = json.dumps(result, ensure_ascii=False)

    assert result["status"] == "executed"
    assert result["returncode"] == 42
    assert result["child_result_summary_parse"] == "parsed_last_json_line"
    assert result["child_result_summary"] == {
        "status": "failed",
        "error_type": "ValueError",
    }
    assert "stdout" not in result
    assert "stderr" not in result
    assert "raw-secret" not in encoded

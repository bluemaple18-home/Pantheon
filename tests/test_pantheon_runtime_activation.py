from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest

from scripts import pantheon_content_runtime_manifest as runtime
from scripts import agy_gemini_coordinator as coordinator
from scripts import pantheon_runtime_activation as activation


def _runtime_roots(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    for path in (actor, queue, state, logs, ready):
        path.mkdir()
    return actor, queue, state, logs, ready


def _manifest(
    actor: Path,
    queue: Path,
    state: Path,
    logs: Path,
    *,
    generation: str,
    digest_seed: str,
) -> dict[str, Any]:
    return runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="activation-test",
        runtime_digest=digest_seed * 64,
        config_version="runtime-v2",
        generation=generation,
        uv_executable=Path(sys.executable).resolve(strict=True),
    )


def _install_environment(
    monkeypatch: pytest.MonkeyPatch,
    manifest_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    token_path: Path,
) -> None:
    values = {
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": service_label,
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest["publisher_state_root"],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
        "PANTHEON_RUNTIME_UV_EXECUTABLE": manifest["uv_executable"],
        "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(token_path),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_activation_token_requires_complete_seven_service_acknowledgements(
    tmp_path: Path,
) -> None:
    actor, queue, state, logs, ready = _runtime_roots(tmp_path)
    manifest = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-six-of-seven",
        digest_seed="a",
    )
    token_path = tmp_path / "activation.token"
    for label in runtime.SERVICE_LABELS[:-1]:
        runtime.write_readiness_ack(ready, manifest, label)
    calls: list[str] = []

    with pytest.raises(activation.RuntimeActivationError, match="incomplete"):
        activation.publish_generation_token(
            token_path,
            ready,
            manifest,
            correlation_id="activation-6-of-7",
        )
    with pytest.raises(activation.RuntimeActivationError):
        activation.run_after_activation_token(
            token_path,
            manifest,
            runtime.SERVICE_LABELS[0],
            queue_root=queue,
            state_root=state,
            actor_root=actor,
            log_root=logs,
            operation=lambda: calls.append("io"),
        )

    assert not token_path.exists()
    assert calls == []


def test_activation_token_rejects_ack_identity_mismatch(
    tmp_path: Path,
) -> None:
    actor, queue, state, logs, ready = _runtime_roots(tmp_path)
    manifest = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-match",
        digest_seed="b",
    )
    other = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-mismatch",
        digest_seed="c",
    )
    token_path = tmp_path / "activation.token"
    for label in runtime.SERVICE_LABELS[:-1]:
        runtime.write_readiness_ack(ready, manifest, label)
    runtime.write_readiness_ack(ready, other, runtime.SERVICE_LABELS[-1])

    with pytest.raises(activation.RuntimeActivationError, match="mismatch"):
        activation.publish_generation_token(
            token_path,
            ready,
            manifest,
            correlation_id="activation-mismatch",
        )

    assert not token_path.exists()


def test_activation_token_allows_seven_matching_services_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor, queue, state, logs, ready = _runtime_roots(tmp_path)
    manifest = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-seven-of-seven",
        digest_seed="d",
    )
    manifest_path = tmp_path / "manifest.json"
    token_path = tmp_path / "activation.token"
    runtime.write_manifest(manifest_path, manifest)
    for label in runtime.SERVICE_LABELS:
        runtime.write_readiness_ack(ready, manifest, label)
    published = activation.publish_generation_token(
        token_path,
        ready,
        manifest,
        correlation_id="activation-7-of-7",
    )
    service_label = runtime.SERVICE_LABELS[0]
    _install_environment(monkeypatch, manifest_path, manifest, service_label, token_path)
    marker = queue / "first-io"

    result = activation.run_after_activation_token(
        token_path,
        manifest,
        service_label,
        queue_root=queue,
        state_root=state,
        actor_root=actor,
        log_root=logs,
        operation=lambda: marker.write_text("ok", encoding="utf-8"),
    )

    assert published["status"] == "PASS"
    assert result == 2
    assert marker.read_text(encoding="utf-8") == "ok"


def test_stale_activation_token_fails_before_queue_state_io(
    tmp_path: Path,
) -> None:
    actor, queue, state, logs, ready = _runtime_roots(tmp_path)
    manifest = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-current",
        digest_seed="e",
    )
    stale_manifest = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-stale",
        digest_seed="f",
    )
    token_path = tmp_path / "activation.token"
    for label in runtime.SERVICE_LABELS:
        runtime.write_readiness_ack(ready, manifest, label)
    activation.publish_generation_token(
        token_path,
        ready,
        manifest,
        correlation_id="activation-stale",
    )
    calls: list[str] = []

    with pytest.raises(activation.RuntimeActivationError, match="mismatch"):
        activation.run_after_activation_token(
            token_path,
            stale_manifest,
            runtime.SERVICE_LABELS[0],
            queue_root=queue,
            state_root=state,
            actor_root=actor,
            log_root=logs,
            operation=lambda: calls.append("io"),
        )

    assert calls == []


def test_formal_coordinator_requires_activation_token_before_queue_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor, queue, state, logs, ready = _runtime_roots(tmp_path)
    manifest = _manifest(
        actor,
        queue,
        state,
        logs,
        generation="generation-missing-token",
        digest_seed="1",
    )
    manifest_path = tmp_path / "manifest.json"
    token_path = tmp_path / "activation.token"
    runtime.write_manifest(manifest_path, manifest)
    for label in runtime.SERVICE_LABELS:
        runtime.write_readiness_ack(ready, manifest, label)
    _install_environment(
        monkeypatch,
        manifest_path,
        manifest,
        "com.pantheon.agy-gemini-coordinator",
        token_path,
    )
    monkeypatch.delenv("PANTHEON_RUNTIME_ACTIVATION_TOKEN")
    monkeypatch.chdir(actor)
    run_dir = tmp_path / "private-run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(
        '{"schema_version":1,"run_id":"missing-token-run","mode":"create","articles":[]}\n',
        encoding="utf-8",
    )

    with pytest.raises(runtime.RuntimeManifestError, match="activation token"):
        coordinator.register_run(run_dir, queue)

    assert not (queue / "runs").exists()


def test_rollback_drift_reports_failed_without_using_config_text() -> None:
    expected = {
        label: {
            "loaded": True,
            "config_digest": f"{index:064x}",
            "control_identity_digest": f"{index + 20:064x}",
        }
        for index, label in enumerate(runtime.SERVICE_LABELS, 1)
    }
    actual = {label: dict(identity) for label, identity in expected.items()}
    actual[runtime.SERVICE_LABELS[-1]]["loaded"] = False

    with pytest.raises(activation.RuntimeActivationError, match="ROLLBACK_FAILED"):
        activation.validate_rollback_loaded_identities(expected, actual)

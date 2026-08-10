from __future__ import annotations

from pathlib import Path
import json
import os
import plistlib
import subprocess
import sys

import pytest

from scripts import pantheon_content_runtime_manifest as runtime


REGRESSION_ID = "REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001"


def test_runtime_manifest_canonicalizes_one_shared_cross_actor_contract(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = actor / ".work" / "content-publisher"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir(parents=True, exist_ok=True)

    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="synthetic-operator:501",
    )
    receipts = [runtime.receipt_for_label(manifest, label) for label in runtime.SERVICE_LABELS]

    assert runtime.validate_receipts(manifest, receipts)["status"] == "PASS"
    assert manifest["regression_id"] == REGRESSION_ID


def test_runtime_manifest_rejects_alias_and_cross_installer_drift(tmp_path: Path) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    alias = tmp_path / "queue-alias"
    alias.symlink_to(queue, target_is_directory=True)

    with pytest.raises(runtime.RuntimeManifestError, match="canonical"):
        runtime.build_manifest(
            actor_root=actor,
            queue_root=alias,
            publisher_state_root=state,
            log_root=logs,
            identity="synthetic-operator:501",
        )

    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="synthetic-operator:501",
    )
    receipt = runtime.receipt_for_label(manifest, runtime.SERVICE_LABELS[0])
    receipt["queue_root"] = str(tmp_path / "other-queue")
    with pytest.raises(runtime.RuntimeManifestError, match="queue_root"):
        runtime.validate_receipts(manifest, [receipt])


def test_all_formal_installers_and_plists_consume_shared_manifest_identity() -> None:
    repo = Path(__file__).resolve().parents[1]
    installers = [
        repo / "scripts/install_agy_content_publisher_launchd.sh",
        repo / "scripts/install_agy_gemini_coordinator_launchd.sh",
        repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh",
    ]
    plists = [
        repo / "ops/launchd/com.pantheon.agy-content-publisher.plist.example",
        repo / "ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example",
        repo / "ops/launchd/com.pantheon.agy-gemini-lane.plist.example",
        repo / "ops/launchd/com.pantheon.content-capacity-guard.plist.example",
    ]

    for installer in installers:
        body = installer.read_text(encoding="utf-8")
        assert "PANTHEON_RUNTIME_MANIFEST_FILE" in body
        assert "scripts.pantheon_content_runtime_manifest field" in body
        assert "PANTHEON_RUNTIME_MANIFEST_DIGEST" in body
        assert "PANTHEON_RUNTIME_IDENTITY" in body
        assert "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST" in body
    assert "scripts.pantheon_content_runtime_manifest aggregate" in installers[1].read_text(
        encoding="utf-8"
    )
    assert "launchctl bootstrap" not in installers[0].read_text(encoding="utf-8")
    assert "launchctl bootstrap" not in installers[2].read_text(encoding="utf-8")
    for plist in plists:
        body = plist.read_text(encoding="utf-8")
        assert "PANTHEON_RUNTIME_MANIFEST_DIGEST" in body
        assert "PANTHEON_RUNTIME_IDENTITY" in body


def test_aggregate_gate_rejects_mixed_manifest_plists(tmp_path: Path) -> None:
    """REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001 Repair-2。"""
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest_a = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="repair-2-a",
    )
    manifest_b = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="repair-2-b",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime.write_manifest(manifest_path, manifest_a)
    plists: list[Path] = []
    for label in runtime.SERVICE_LABELS:
        path = tmp_path / f"{label}.plist"
        with path.open("wb") as stream:
            plistlib.dump(
                {
                    "Label": label,
                    "WorkingDirectory": str(actor),
                    "EnvironmentVariables": {
                        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest_a[
                            "manifest_digest"
                        ],
                        "PANTHEON_RUNTIME_IDENTITY": manifest_a["identity"],
                        "PANTHEON_RUNTIME_SERVICE_LABEL": label,
                        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest_a[
                            "runtime_identity_digest"
                        ],
                        "PANTHEON_RUNTIME_CODE_DIGEST": manifest_a[
                            "runtime_digest"
                        ],
                        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest_a[
                            "config_version"
                        ],
                        "PANTHEON_RUNTIME_GENERATION": manifest_a["generation"],
                        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest_a["actor_root"],
                        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest_a["queue_root"],
                        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest_a[
                            "publisher_state_root"
                        ],
                        "PANTHEON_RUNTIME_LOG_ROOT": manifest_a["log_root"],
                    },
                },
                stream,
            )
        path.chmod(0o600)
        plists.append(path)

    command = [
        sys.executable,
        "-m",
        "scripts.pantheon_content_runtime_manifest",
        "aggregate",
        "--manifest",
        str(manifest_path),
        "--expected-digest",
        manifest_a["manifest_digest"],
        *sum((["--plist", str(path)] for path in plists), []),
    ]
    positive = subprocess.run(command, check=False, capture_output=True, text=True)
    with plists[-1].open("rb") as stream:
        mixed = plistlib.load(stream)
    mixed["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST_DIGEST"] = manifest_b[
        "manifest_digest"
    ]
    with plists[-1].open("wb") as stream:
        plistlib.dump(mixed, stream)
    negative = subprocess.run(command, check=False, capture_output=True, text=True)

    assert positive.returncode == 0, positive.stderr
    assert negative.returncode != 0
    assert "mismatch" in negative.stdout


def test_stale_or_malformed_activation_barrier_fails_closed(tmp_path: Path) -> None:
    """REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001 barrier identity。"""
    barrier = tmp_path / "activation.barrier"
    barrier.write_text("stale\n", encoding="utf-8")
    barrier.chmod(0o600)
    command = [
        sys.executable,
        "-m",
        "scripts.pantheon_content_runtime_manifest",
        "barrier-exec",
        "--barrier",
        str(barrier),
        "--expected-digest",
        "a" * 64,
        "--timeout",
        "1",
        "--",
        "/usr/bin/true",
    ]

    completed = subprocess.run(command, check=False)

    assert completed.returncode == 78


def test_runtime_identity_contract_contains_generation_and_runtime_digest(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()

    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-runtime:test",
        runtime_digest="a" * 64,
        config_version="runtime-v2",
        generation="generation-001",
    )

    assert manifest["schema_version"] == 2
    assert manifest["runtime_digest"] == "a" * 64
    assert manifest["config_version"] == "runtime-v2"
    assert manifest["generation"] == "generation-001"
    assert len(manifest["runtime_identity_digest"]) == 64
    receipt = runtime.receipt_for_label(manifest, runtime.SERVICE_LABELS[0])
    assert receipt["service_label"] == runtime.SERVICE_LABELS[0]
    assert receipt["runtime_identity_digest"] == manifest["runtime_identity_digest"]


def test_seven_service_barrier_requires_complete_matching_acknowledgements(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    barrier = tmp_path / "activation.barrier"
    for path in (actor, queue, state, logs, ready):
        path.mkdir()
    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-runtime:test",
        runtime_digest="b" * 64,
        config_version="runtime-v2",
        generation="generation-002",
    )
    for label in runtime.SERVICE_LABELS[:-1]:
        runtime.write_readiness_ack(ready, manifest, label)

    with pytest.raises(runtime.RuntimeManifestError, match="incomplete"):
        runtime.activate_barrier(barrier, ready, manifest)
    assert not barrier.exists()

    runtime.write_readiness_ack(ready, manifest, runtime.SERVICE_LABELS[-1])
    activation = runtime.activate_barrier(barrier, ready, manifest)

    assert activation["status"] == "PASS"
    assert runtime.validate_barrier(barrier, manifest)["status"] == "PASS"
    assert len(activation["acknowledgements"]) == 7


def test_runtime_tick_rejects_drift_before_queue_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-runtime:test",
        runtime_digest="c" * 64,
        config_version="runtime-v2",
        generation="generation-003",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime.write_manifest(manifest_path, manifest)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST", str(manifest_path))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_MANIFEST_DIGEST", manifest["manifest_digest"]
    )
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", manifest["generation"])
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_IDENTITY_DIGEST",
        manifest["runtime_identity_digest"],
    )
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_SERVICE_LABEL", runtime.SERVICE_LABELS[1]
    )
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["generation"] = "generation-stale"
    manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
    marker = queue / "must-not-exist"

    with pytest.raises(runtime.RuntimeManifestError):
        runtime.validate_runtime_tick(
            runtime.SERVICE_LABELS[1],
            queue_root=queue,
            state_root=state,
            actor_root=actor,
            log_root=logs,
        )

    assert not marker.exists()


def test_rollback_identity_requires_saved_actual_control_plane_match() -> None:
    expected = {
        label: {
            "loaded": True,
            "config_digest": f"{ordinal:064x}",
            "control_identity_digest": f"{ordinal + 10:064x}",
        }
        for ordinal, label in enumerate(runtime.SERVICE_LABELS, 1)
    }
    actual = json.loads(json.dumps(expected))

    assert runtime.validate_rollback_identities(expected, actual)["status"] == "PASS"

    actual[runtime.SERVICE_LABELS[-1]]["control_identity_digest"] = "f" * 64
    with pytest.raises(runtime.RuntimeManifestError, match="ROLLBACK_FAILED"):
        runtime.validate_rollback_identities(expected, actual)


@pytest.mark.parametrize("service_label", runtime.SERVICE_LABELS)
def test_each_service_identity_mismatch_fails_before_first_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_label: str,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="seven-service-matrix",
        runtime_digest="d" * 64,
        config_version="runtime-v2",
        generation="generation-matrix",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime.write_manifest(manifest_path, manifest)
    environment = {
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
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("PANTHEON_RUNTIME_CONFIG_VERSION", "stale-config")
    lane = service_label.removeprefix("com.pantheon.agy-gemini-")
    service_queue = (
        queue / "lanes" / lane
        if service_label.startswith("com.pantheon.agy-gemini-")
        and service_label != "com.pantheon.agy-gemini-coordinator"
        else queue
    )
    marker = queue / "must-not-exist"

    with pytest.raises(runtime.RuntimeManifestError, match="identity mismatch"):
        runtime.validate_runtime_tick(
            service_label,
            queue_root=service_queue,
            state_root=state,
            actor_root=actor,
            log_root=logs,
        )

    assert not marker.exists()


def test_early_service_acknowledges_but_cannot_run_before_barrier(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    for path in (actor, queue, state, logs, ready):
        path.mkdir()
    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="early-service",
        runtime_digest="e" * 64,
        config_version="runtime-v2",
        generation="generation-early",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime.write_manifest(manifest_path, manifest)
    label = runtime.SERVICE_LABELS[1]
    marker = queue / "early-mutation"
    environment = os.environ.copy()
    environment.update(
        {
            "PANTHEON_FORMAL_RUNTIME": "1",
            "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
            "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
            "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
            "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
            "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
            "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
            "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
            "PANTHEON_RUNTIME_SERVICE_LABEL": label,
            "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
            "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
            "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest["publisher_state_root"],
            "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.pantheon_content_runtime_manifest",
            "barrier-exec",
            "--barrier",
            str(tmp_path / "missing.barrier"),
            "--expected-digest",
            manifest["manifest_digest"],
            "--manifest",
            str(manifest_path),
            "--service-label",
            label,
            "--ready-root",
            str(ready),
            "--timeout",
            "1",
            "--",
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('bad')",
        ],
        check=False,
        env=environment,
    )

    assert completed.returncode == 78
    assert not (ready / f"{label}.json").exists()
    assert not marker.exists()

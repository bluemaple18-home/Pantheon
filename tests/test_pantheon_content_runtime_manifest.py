from __future__ import annotations

from pathlib import Path

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
    receipts = [
        {
            "label": label,
            "actor_root": str(actor.resolve()),
            "queue_root": str(queue.resolve()),
            "publisher_state_root": str(state.resolve()),
            "log_root": str(logs.resolve()),
            "identity": "synthetic-operator:501",
            "manifest_digest": manifest["manifest_digest"],
        }
        for label in runtime.SERVICE_LABELS
    ]

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
    for plist in plists:
        body = plist.read_text(encoding="utf-8")
        assert "PANTHEON_RUNTIME_MANIFEST_DIGEST" in body
        assert "PANTHEON_RUNTIME_IDENTITY" in body

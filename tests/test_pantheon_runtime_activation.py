from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import json
import os
import subprocess
import sys
from typing import Any

import pytest

from scripts import pantheon_content_runtime_manifest as runtime
from scripts import agy_gemini_coordinator as coordinator
from scripts import pantheon_runtime_activation as activation


def test_print_disabled_accepts_observed_macos_output() -> None:
    """使用 QA 主機原始輸出，foreign 停用項目不得阻擋 Pantheon。"""
    stdout = (Path(__file__).parent / "fixtures/launchctl_print_disabled_macos.txt").read_text()
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout, "")

    assert activation.read_disabled_service_labels(
        runtime.SERVICE_LABELS, runner=runner, domain="gui/502"
    ) == frozenset()
    assert commands == [["launchctl", "print-disabled", "gui/502"]]


@pytest.mark.parametrize("stdout", [
    'disabled services = {\n"foreign" => unknown\n}\n',
    'disabled services = {\n"foreign" => disabled\n',
    'disabled services = {\n"foreign" => enabled garbage\n}\n',
])
def test_print_disabled_rejects_unknown_or_incomplete_output(stdout: str) -> None:
    """foreign 項目亦須完整解析；未知或截斷不能當成允許復機。"""
    with pytest.raises(activation.RuntimeActivationError, match="grammar is invalid"):
        activation.read_disabled_service_labels(
            runtime.SERVICE_LABELS,
            runner=lambda command: subprocess.CompletedProcess(command, 0, stdout, ""),
            domain="gui/502",
        )


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



def _launchctl_identity(
    target: str,
    plist: Path,
    *,
    state: str,
    runs: int,
    exit_code: int | None,
    pid: int | None = None,
) -> str:
    rows = [
        f"{target} = {{",
        f"\tpath = {plist}",
        f"\tstate = {state}",
        f"\truns = {runs}",
    ]
    if exit_code is not None:
        rows.append(f"\tlast exit code = {exit_code}")
    if pid is not None:
        rows.append(f"\tpid = {pid}")
    rows.append("}")
    return "\n".join(rows) + "\n"


def _action_authority(
    tmp_path: Path,
    *,
    labels: list[str],
    plists: dict[str, Path],
    generation: str,
    manifest_digest: str,
    runtime_identity_digest: str,
) -> dict[str, Any]:
    manifest_file = tmp_path / f"{generation}.manifest.json"
    barrier = tmp_path / f"{generation}.barrier"
    manifest_file.write_text("{}\n", encoding="utf-8")
    barrier.write_text("synthetic barrier\n", encoding="utf-8")
    manifest_file.chmod(0o600)
    barrier.chmod(0o600)
    return {
        "schema_version": 1,
        "generation": generation,
        "manifest_digest": manifest_digest,
        "runtime_identity_digest": runtime_identity_digest,
        "manifest_file": activation.capture_file_identity(manifest_file),
        "barrier": activation.capture_file_identity(barrier),
        "plists": {
            label: activation.capture_file_identity(plists[label]) for label in labels
        },
    }


def test_capacity_stop_drains_tracked_child_before_bootout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    logs = tmp_path / "logs"
    launch_agents = tmp_path / "LaunchAgents"
    for path in (state_root, actor, queue, logs, launch_agents):
        path.mkdir()
    label = runtime.SERVICE_LABELS[0]
    plist = launch_agents / f"{label}.plist"
    plist.write_text("synthetic\n", encoding="utf-8")
    plist.chmod(0o600)
    receipt_path = state_root / "capacity-stop.json"
    loaded = True
    process_round = 0
    events: list[str] = []

    monkeypatch.setattr(
        activation,
        "_process_birth_identity",
        lambda pid, _row, _record: [1, pid],
    )
    monkeypatch.setattr(activation.os, "getpgrp", lambda: 50000)

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, process_round
        if command[:2] == ["launchctl", "print"]:
            target = command[-1]
            if not loaded:
                return subprocess.CompletedProcess(command, 113, "", "")
            if process_round == 0:
                body = _launchctl_identity(
                    target,
                    plist,
                    state="running",
                    runs=1,
                    exit_code=None,
                    pid=100,
                )
            else:
                body = _launchctl_identity(
                    target,
                    plist,
                    state="waiting",
                    runs=1,
                    exit_code=0,
                )
            return subprocess.CompletedProcess(command, 0, body, "")
        if command[:2] == ["/bin/ps", "-axo"]:
            if process_round == 0:
                process_round = 1
                events.append("child-observed")
                stdout = (
                    f"100 1 9001 S {actor}/service.py\n"
                    f"101 100 9001 S {actor}/child.py\n"
                )
            else:
                events.append("child-drained")
                stdout = ""
            return subprocess.CompletedProcess(command, 0, stdout, "")
        if command[:2] == ["/usr/sbin/lsof", "-a"]:
            stdout = (
                f"p100\nfcwd\nn{actor}\n"
                f"p101\nfcwd\nn{actor}\n"
                if process_round == 1
                else ""
            )
            return subprocess.CompletedProcess(command, 0, stdout, "")
        if command[:2] == ["launchctl", "bootout"]:
            events.append("bootout")
            loaded = False
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(command)

    roots = {
        "actor_root": str(actor),
        "queue_root": str(queue),
        "publisher_state_root": str(state_root),
        "log_root": str(logs),
    }
    authority = _action_authority(
        tmp_path,
        labels=[label],
        plists={label: plist},
        generation="capacity-stop-generation",
        manifest_digest="a" * 64,
        runtime_identity_digest="b" * 64,
    )
    with runtime.runtime_shutdown_lease(state_root):
        result = activation.stop_capacity_services(
            [label],
            plist_paths={label: plist},
            authority=authority,
            owned_roots=roots,
            state_root=state_root,
            receipt_path=receipt_path,
            incident_id="capacity-stop-test",
            generation="capacity-stop-generation",
            manifest_digest="a" * 64,
            runtime_identity_digest="b" * 64,
            timeout_seconds=5,
            runner=fake_runner,
        )

    assert result["status"] == "STOPPED"
    assert events.index("child-drained") < events.index("bootout")
    assert activation.load_action_receipt(receipt_path)["status"] == "STOPPED"


@pytest.mark.parametrize("override", ["enabled", "disabled", "false", "true"])
def test_capacity_resume_requires_later_successful_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: str,
) -> None:
    state_root = tmp_path / "state"
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    logs = tmp_path / "logs"
    launch_agents = tmp_path / "LaunchAgents"
    for path in (state_root, actor, queue, logs, launch_agents):
        path.mkdir()
    label = runtime.SERVICE_LABELS[0]
    plist = launch_agents / f"{label}.plist"
    plist.write_text("synthetic\n", encoding="utf-8")
    plist.chmod(0o600)
    receipt_path = state_root / "capacity-resume.json"
    loaded = False
    runs = 0
    exit_code: int | None = None

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, runs, exit_code
        if command[:2] == ["launchctl", "print-disabled"]:
            return subprocess.CompletedProcess(
                command,
                0,
                f'disabled services = {{\n"foreign" => disabled\n"{label}" => {override}\n}}\n',
                "",
            )
        if command[:2] == ["launchctl", "print"]:
            if not loaded:
                return subprocess.CompletedProcess(command, 113, "", "")
            return subprocess.CompletedProcess(
                command,
                0,
                _launchctl_identity(
                    command[-1],
                    plist,
                    state="waiting",
                    runs=runs,
                    exit_code=exit_code,
                ),
                "",
            )
        if command[:2] == ["launchctl", "bootstrap"]:
            loaded = True
            runs = 1
            exit_code = 0
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(command)

    roots = {
        "actor_root": str(actor),
        "queue_root": str(queue),
        "publisher_state_root": str(state_root),
        "log_root": str(logs),
    }
    authority = _action_authority(
        tmp_path,
        labels=[label],
        plists={label: plist},
        generation="capacity-resume-generation",
        manifest_digest="c" * 64,
        runtime_identity_digest="d" * 64,
    )
    monkeypatch.setattr(
        activation,
        "run_process_boundary",
        lambda **kwargs: {
            "status": "OBSERVED",
            "active": [],
            "resample_required": False,
            "seen_labels": list(kwargs["arguments"]),
            "journal": str(kwargs["journal_path"]),
        },
    )
    rejection = (
        pytest.raises(activation.RuntimeActivationError, match="owned_service_manually_disabled")
        if override in {"disabled", "true"} else nullcontext()
    )
    with runtime.runtime_shutdown_lease(state_root), rejection:
        started = activation.resume_capacity_services(
            [label],
            plist_paths={label: plist},
            authority=authority,
            owned_roots=roots,
            state_root=state_root,
            receipt_path=receipt_path,
            incident_id="capacity-resume-test",
            generation="capacity-resume-generation",
            manifest_digest="c" * 64,
            runtime_identity_digest="d" * 64,
            runner=fake_runner,
        )

    if override in {"disabled", "true"}:
        blocked = activation.load_action_receipt(receipt_path)
        assert blocked["status"] == "BLOCKED"
        assert blocked["error"] == "RuntimeActivationError: owned_service_manually_disabled"
        assert blocked["attempted_labels"] == []
        assert not loaded
        assert activation.load_action_receipt(receipt_path)["status"] == "BLOCKED"
        return

    assert started["status"] == "STARTED"
    assert started["services"][label]["baseline_runs"] == 1
    assert started["services"][label]["required_success_runs"] == 2
    pending = activation.verify_capacity_resume_execution(
        started,
        runner=fake_runner,
        timeout_seconds=5,
    )
    assert pending["status"] == "PENDING"

    runs = 2
    exit_code = 0
    monkeypatch.setattr(
        activation,
        "run_process_boundary",
        lambda **_kwargs: {
            "status": "OBSERVED",
            "active": [],
            "resample_required": False,
            "seen_labels": [label],
        },
    )
    verified = activation.verify_capacity_resume_execution(
        started,
        runner=fake_runner,
        timeout_seconds=5,
    )
    assert verified["status"] == "PASS"


def test_capacity_resume_tracks_detached_child_before_terminal_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    logs = tmp_path / "logs"
    launch_agents = tmp_path / "LaunchAgents"
    for path in (state_root, actor, queue, logs, launch_agents):
        path.mkdir()
    label = runtime.SERVICE_LABELS[0]
    plist = launch_agents / f"{label}.plist"
    plist.write_text("synthetic\n", encoding="utf-8")
    plist.chmod(0o600)
    receipt_path = state_root / "capacity-resume-detached-child.json"
    loaded = False
    terminal = False

    monkeypatch.setattr(
        activation,
        "_process_birth_identity",
        lambda pid, _row, _record: None if terminal and pid == 100 else [1, pid],
    )
    monkeypatch.setattr(activation.os, "getpgrp", lambda: 50000)

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        if command[:2] == ["launchctl", "print-disabled"]:
            return subprocess.CompletedProcess(
                command,
                0,
                "disabled services = {\n}\n",
                "",
            )
        if command[:2] == ["launchctl", "bootstrap"]:
            loaded = True
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:2] == ["launchctl", "print"]:
            if not loaded:
                return subprocess.CompletedProcess(command, 113, "", "")
            return subprocess.CompletedProcess(
                command,
                0,
                _launchctl_identity(
                    command[-1],
                    plist,
                    state="waiting" if terminal else "running",
                    runs=2 if terminal else 1,
                    exit_code=0 if terminal else None,
                    pid=None if terminal else 100,
                ),
                "",
            )
        if command[:2] == ["/bin/ps", "-axo"]:
            stdout = (
                "101 1 101 S /bin/sleep 300\n"
                if terminal
                else (
                    f"100 1 9001 S {actor}/service.py\n"
                    f"101 100 9001 S {actor}/child.py\n"
                )
            )
            return subprocess.CompletedProcess(command, 0, stdout, "")
        if command[:2] == ["/usr/sbin/lsof", "-a"]:
            stdout = (
                "p101\nfcwd\nn/\n"
                if terminal
                else (
                    f"p100\nfcwd\nn{actor}\n"
                    f"p101\nfcwd\nn{actor}\n"
                )
            )
            return subprocess.CompletedProcess(command, 0, stdout, "")
        raise AssertionError(command)

    roots = {
        "actor_root": str(actor),
        "queue_root": str(queue),
        "publisher_state_root": str(state_root),
        "log_root": str(logs),
    }
    authority = _action_authority(
        tmp_path,
        labels=[label],
        plists={label: plist},
        generation="capacity-resume-detached-child-generation",
        manifest_digest="1" * 64,
        runtime_identity_digest="2" * 64,
    )
    with runtime.runtime_shutdown_lease(state_root):
        started = activation.resume_capacity_services(
            [label],
            plist_paths={label: plist},
            authority=authority,
            owned_roots=roots,
            state_root=state_root,
            receipt_path=receipt_path,
            incident_id="capacity-resume-detached-child-test",
            generation="capacity-resume-detached-child-generation",
            manifest_digest="1" * 64,
            runtime_identity_digest="2" * 64,
            runner=fake_runner,
        )

    terminal = True
    verified = activation.verify_capacity_resume_execution(
        started,
        runner=fake_runner,
        timeout_seconds=5,
    )

    assert verified["status"] == "PENDING"
    assert verified["process_observation"]["active"] == [101]


def test_capacity_resume_surfaces_first_real_run_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    logs = tmp_path / "logs"
    launch_agents = tmp_path / "LaunchAgents"
    for path in (state_root, actor, queue, logs, launch_agents):
        path.mkdir()
    label = runtime.SERVICE_LABELS[0]
    plist = launch_agents / f"{label}.plist"
    plist.write_text("synthetic\n", encoding="utf-8")
    plist.chmod(0o600)
    loaded = False
    runs = 0
    exit_code: int | None = None

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, runs, exit_code
        if command[:2] == ["launchctl", "print-disabled"]:
            return subprocess.CompletedProcess(
                command,
                0,
                "disabled services = {\n}\n",
                "",
            )
        if command[:2] == ["launchctl", "print"]:
            if not loaded:
                return subprocess.CompletedProcess(command, 113, "", "")
            return subprocess.CompletedProcess(
                command,
                0,
                _launchctl_identity(
                    command[-1],
                    plist,
                    state="waiting",
                    runs=runs,
                    exit_code=exit_code,
                ),
                "",
            )
        if command[:2] == ["launchctl", "bootstrap"]:
            loaded = True
            runs = 1
            exit_code = 75
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(command)

    roots = {
        "actor_root": str(actor),
        "queue_root": str(queue),
        "publisher_state_root": str(state_root),
        "log_root": str(logs),
    }
    receipt_path = state_root / "capacity-resume-failed.json"
    authority = _action_authority(
        tmp_path,
        labels=[label],
        plists={label: plist},
        generation="capacity-resume-failed-generation",
        manifest_digest="e" * 64,
        runtime_identity_digest="f" * 64,
    )
    monkeypatch.setattr(
        activation,
        "run_process_boundary",
        lambda **kwargs: {
            "status": "OBSERVED",
            "active": [],
            "resample_required": False,
            "seen_labels": list(kwargs["arguments"]),
            "journal": str(kwargs["journal_path"]),
        },
    )
    with runtime.runtime_shutdown_lease(state_root):
        started = activation.resume_capacity_services(
            [label],
            plist_paths={label: plist},
            authority=authority,
            owned_roots=roots,
            state_root=state_root,
            receipt_path=receipt_path,
            incident_id="capacity-resume-failed-test",
            generation="capacity-resume-failed-generation",
            manifest_digest="e" * 64,
            runtime_identity_digest="f" * 64,
            runner=fake_runner,
        )
    runs = 2
    exit_code = 78
    monkeypatch.setattr(
        activation,
        "run_process_boundary",
        lambda **_kwargs: pytest.fail("failed service must be rejected before process proof"),
    )

    verified = activation.verify_capacity_resume_execution(
        started,
        runner=fake_runner,
        timeout_seconds=5,
    )

    assert verified["status"] == "FAILED"
    assert verified["services"][label]["reason"] == "service_exit_nonzero:78"


@pytest.fixture
def boundary_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """逐條核對唯讀 runner 回覆；禁止真實主機指令、birth 與 signal。"""
    actor, queue, state, logs, _ready = _runtime_roots(tmp_path)
    label = runtime.SERVICE_LABELS[0]
    journal = state / "boundary.json"
    calls: list[list[str]] = []
    births: list[int] = []
    snapshot_pids: set[int] = set()
    clock = [0.0]
    original_birth = activation._process_birth_identity

    def forbidden(*_args, **_kwargs):
        pytest.fail("離線測試不得存取真實主機")

    def birth(pid, _row, _record):
        births.append(pid)
        # 合成已知程序在本輪 ps 消失時，提供明確的 targeted absence 回覆。
        return [1, pid] if pid in snapshot_pids else None

    monkeypatch.setattr(activation.subprocess, "run", forbidden)
    monkeypatch.setattr(activation.os, "kill", forbidden)
    monkeypatch.setattr(activation.os, "getpid", lambda: 50000)
    monkeypatch.setattr(activation.os, "getpgrp", lambda: 50000)
    monkeypatch.setattr(activation, "_process_birth_identity", birth)
    monkeypatch.setattr(activation.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(activation.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    def prepare(samples, *, prior=None, real_birth=False):
        if real_birth:
            monkeypatch.setattr(activation, "_process_birth_identity", original_birth)
        if prior is not None:
            journal.write_text(json.dumps(prior), encoding="utf-8")
            journal.chmod(0o600)
        replies = []
        for first, second, ps, cwd in samples:
            for index, (service_state, pid) in enumerate((first, second)):
                command = ["launchctl", "print", f"gui/502/{label}"]
                body = "" if service_state == "ABSENT" else _launchctl_identity(
                    command[-1], state / f"{label}.plist", state=service_state,
                    runs=2, exit_code=0, pid=pid,
                )
                replies.append((command, 113 if service_state == "ABSENT" else 0, body))
                if index == 0:
                    replies.extend([
                        (["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,command="], 0, ps),
                        (["/usr/sbin/lsof", "-a", "-u", str(os.getuid()), "-d", "cwd", "-Fpn"], 0, cwd),
                    ])

        def runner(command):
            assert replies, f"非預期指令：{command}"
            expected, code, body = replies.pop(0)
            assert command == expected
            if command[:2] == ["/bin/ps", "-axo"]:
                snapshot_pids.clear()
                snapshot_pids.update(int(line.split()[0]) for line in body.splitlines() if line.split()[0].isdigit())
            calls.append(command)
            return subprocess.CompletedProcess(command, code, body, "")

        options = dict(
            journal_path=journal, timeout_seconds=1, domain="gui/502",
            owned_roots=dict(actor_root=str(actor), queue_root=str(queue),
                             publisher_state_root=str(state), log_root=str(logs)),
            arguments=[label], runner=runner,
        )
        return options, replies

    return prepare, journal, calls, births, clock


def test_boundary_new_pid_missing_snapshot_is_pending(boundary_replay) -> None:
    """重現 verify 新 PID67277 的 missing seed；應 pending 而非 latch UNKNOWN。"""
    prepare, journal, calls, births, _clock = boundary_replay
    options, replies = prepare([(("waiting", None), ("running", 67277), "", "")])
    result = activation.run_process_boundary(mode="observe", **options)
    saved = activation.load_action_receipt(journal)
    assert result["status"] == "OBSERVED" and result["resample_required"]
    assert saved["processes"] == {} and saved["groups"] == [] and saved["seen_labels"] == []
    assert saved.get("status") != "UNKNOWN_OR_FAILED"
    assert births == [] and len(calls) == 4 and replies == []


def _boundary_lineage() -> dict[str, Any]:
    """已驗證的舊 orphan，即使此次取樣不可用也不能丟棄。"""
    return dict(
        schema_version=1,
        processes={"100": {"birth": [1, 100], "ppid": 1, "pgid": 9001,
                           "zombie": False, "command": "/bin/sleep 300"}},
        groups=[9001], seen_labels=[runtime.SERVICE_LABELS[0]],
        resample_required=False, active=[100],
    )


@pytest.mark.parametrize("first,second,ps", [
    (("waiting", None), ("running", 67277), ""),
    (("waiting", None), ("running", 67334), ""),
    (("running", 67277), ("waiting", None), ""),
    (("running", 67277), ("ABSENT", None), ""),
    (("ABSENT", None), ("running", 67277), ""),
    (("running", 100), ("running", 101), "100 1 9001 S /bin/sleep 300\n"),
    (("xpcproxy", 100), ("running", 100), "100 1 0 S /usr/libexec/xpcproxy\n"),
    (("running", 100), ("xpcproxy", 100), "100 1 9001 S /bin/sleep 300\n"),
    (("xpcproxy", 100), ("xpcproxy", 100), "100 1 0 S /usr/libexec/xpcproxy\n"),
    (("xpcproxy", None), ("xpcproxy", None), ""),
    (("waiting", None), ("exited", None), ""),
])
def test_boundary_pending_preserves_trusted_lineage(boundary_replay, first, second, ps) -> None:
    """PID／state 變動或初始化只能要求重取樣，不能採納當輪 group 或 birth。"""
    prepare, journal, _calls, births, _clock = boundary_replay
    prior = _boundary_lineage()
    prior["status"] = "DRAINED"
    options, replies = prepare([(first, second, ps, "")], prior=prior)
    result = activation.run_process_boundary(mode="observe", **options)
    saved = activation.load_action_receipt(journal)
    assert result["resample_required"] and result["active"] == [100]
    for field in ("processes", "groups", "seen_labels"):
        assert saved[field] == prior[field]
    assert saved["status"] == "OBSERVED"
    assert births == [] and replies == []


def test_boundary_stable_resample_validates_and_keeps_old_orphan(boundary_replay) -> None:
    """pending 後的穩定快照才取得新 lineage；舊 orphan 仍須驗證且不得 false drain。"""
    prepare, journal, _calls, births, _clock = boundary_replay
    options, _replies = prepare([
        (("waiting", None), ("running", 67277), "", ""),
        (("running", 67277), ("running", 67277),
         "100 1 100 S /bin/sleep 300\n67277 1 9002 S /bin/sleep 300\n", ""),
        (("waiting", None), ("waiting", None), "100 1 100 S /bin/sleep 300\n", ""),
        (("ABSENT", None), ("ABSENT", None), "", ""),
    ], prior=_boundary_lineage())
    assert activation.run_process_boundary(mode="observe", **options)["resample_required"]
    stable = activation.run_process_boundary(mode="observe", **options)
    assert not stable["resample_required"] and stable["active"] == [100, 67277]
    saved = activation.load_action_receipt(journal)
    assert set(saved["processes"]) == {"100", "67277"}
    assert saved["groups"] == [100, 9001, 9002]
    assert sorted(births) == [100, 67277]
    orphan = activation.run_process_boundary(mode="observe", **options)
    assert orphan["active"] == [100] and not orphan["resample_required"]
    drained = activation.run_process_boundary(mode="drain", **options)
    assert drained["status"] == "DRAINED"
    saved = activation.load_action_receipt(journal)
    assert set(saved["processes"]) == {"100", "67277"} and saved["groups"] == [100, 9001, 9002]


def _boundary_resume_receipt(options: dict[str, Any]) -> dict[str, Any]:
    """僅提供 verify 入口必要的先前 bootstrap 契約，未啟動 runtime。"""
    label = options["arguments"][0]
    plist = Path(options["owned_roots"]["publisher_state_root"]) / f"{label}.plist"
    return dict(
        schema_version=activation.ACTION_RECEIPT_SCHEMA_VERSION,
        action="capacity-resume", status="STARTED", labels=[label],
        domain=options["domain"], owned_roots=options["owned_roots"],
        process_journal_path=str(options["journal_path"]),
        services={label: dict(baseline_runs=1, required_success_runs=2,
                             post_bootstrap={"identity": {"paths": [str(plist)]}})},
    )


@pytest.mark.parametrize("prior", [None, _boundary_lineage()])
def test_boundary_pending_cannot_verify_pass(boundary_replay, prior) -> None:
    """服務已達 terminal success 且已看過 lineage，當輪 pending 仍不得 PASS。"""
    prepare, journal, _calls, births, _clock = boundary_replay
    options, replies = prepare([
        (("waiting", None), ("waiting", None), "", ""),
        (("xpcproxy", None), ("xpcproxy", None), "", ""),
    ], prior=prior)
    # verify 先讀一次服務，其後才是完整的 boundary 快照。
    replies.pop(1)
    replies.pop(1)
    replies.pop(1)
    result = activation.verify_capacity_resume_execution(
        _boundary_resume_receipt(options), runner=options["runner"], timeout_seconds=1,
    )
    assert result["services"][options["arguments"][0]]["status"] == "PASS"
    assert result["status"] == "PENDING" and result["process_observation"]["resample_required"]
    assert activation.load_action_receipt(journal).get("status") != "UNKNOWN_OR_FAILED"
    assert births == [] and replies == []


def test_boundary_drain_resamples_until_stable_absence(boundary_replay) -> None:
    """pending 的空 active 不能結束 drain；新 PID 穩定驗證且消失後才 DRAINED。"""
    prepare, journal, calls, births, clock = boundary_replay
    options, replies = prepare([
        (("waiting", None), ("running", 67334), "", ""),
        (("running", 67334), ("running", 67334), "67334 1 9001 S /bin/sleep 300\n", ""),
        (("ABSENT", None), ("ABSENT", None), "", ""),
    ])
    result = activation.run_process_boundary(mode="drain", **options)
    assert result["status"] == "DRAINED" and len(calls) == 12 and replies == []
    saved = activation.load_action_receipt(journal)
    assert saved["processes"]["67334"]["birth"] == [1, 67334] and saved["groups"] == [9001]
    assert saved["seen_labels"] == options["arguments"] and births == [67334, 67334]
    assert saved["deadline"] == 1 and clock[0] == pytest.approx(0.2)


@pytest.mark.parametrize("first,second", [
    (("waiting", None), ("running", 67334)),
    (("xpcproxy", 67334), ("xpcproxy", 67334)),
    (("xpcproxy", 67334), ("running", 67334)),
    (("xpcproxy", None), ("xpcproxy", None)),
])
def test_boundary_persistent_pending_uses_original_deadline(boundary_replay, first, second) -> None:
    """沿用先前 drain 的總 deadline；每次重取樣不得延展逾時。"""
    prepare, journal, calls, births, clock = boundary_replay
    prior = {**_boundary_lineage(), "deadline": 0.25}
    options, replies = prepare([(first, second, "", "")] * 3, prior=prior)
    with pytest.raises(activation.RuntimeActivationError, match="deadline exceeded"):
        activation.run_process_boundary(mode="drain", **options)
    saved = activation.load_action_receipt(journal)
    assert saved["status"] == "UNKNOWN_OR_FAILED" and saved["deadline"] == 0.25
    assert saved["resample_required"] and saved["processes"] == prior["processes"]
    assert saved["groups"] == prior["groups"] and saved["seen_labels"] == prior["seen_labels"]
    assert births == [] and len(calls) == 12 and replies == [] and clock[0] == 0.25


@pytest.mark.parametrize("ps,error", [
    ("", "unobserved service PID missing"),
    ("101 1 0 S /bin/sleep 300\n", "group ownership UNKNOWN"),
    ("101 1 1 S /bin/sleep 300\n", "group ownership UNKNOWN"),
    ("101 1 50000 S /bin/sleep 300\n", "group ownership UNKNOWN"),
    ("50000 1 50000 S /bin/controller\n101 50000 50000 S /bin/sleep 300\n", "group ownership UNKNOWN"),
    ("malformed ps", "snapshot grammar UNKNOWN"),
])
def test_boundary_stable_missing_and_foreign_groups_fail_closed(boundary_replay, ps, error) -> None:
    """穩定快照仍保留 missing／system／controller group 與格式錯誤 guard。"""
    prepare, journal, _calls, births, _clock = boundary_replay
    options, _replies = prepare([(("running", 101), ("running", 101), ps, "")])
    with pytest.raises(activation.RuntimeActivationError, match=error):
        activation.run_process_boundary(mode="observe", **options)
    saved = activation.load_action_receipt(journal)
    assert saved["status"] == "UNKNOWN_OR_FAILED"
    assert saved["processes"] == {} and saved["groups"] == [] and births == []


@pytest.mark.parametrize("failure", ["lsof_exit", "lsof_grammar", "service_grammar", "unknown_pid"])
def test_boundary_pending_cannot_mask_unknown_observations(boundary_replay, failure) -> None:
    """PID 競態不能把不完整的 service／cwd 證據包成合法 pending。"""
    prepare, journal, _calls, births, _clock = boundary_replay
    options, replies = prepare([(("waiting", None), ("running", 101), "", "")])
    index = 2 if failure.startswith("lsof") else 0
    command, _code, body = replies[index]
    if failure == "lsof_exit":
        replies[index] = (command, 1, "")
    elif failure == "lsof_grammar":
        replies[index] = (command, 0, "garbage")
    elif failure == "service_grammar":
        replies[index] = (command, 0, body.replace("state = waiting", "state = waiting\n\tstate = running"))
    else:
        replies[index] = (command, 0, body.replace("state = waiting", "state = unexpected"))
    with pytest.raises(activation.RuntimeActivationError, match="UNKNOWN"):
        activation.run_process_boundary(mode="observe", **options)
    assert activation.load_action_receipt(journal)["status"] == "UNKNOWN_OR_FAILED" and births == []


def _boundary_libproc(monkeypatch: pytest.MonkeyPatch, identities: dict[int, Any]) -> list[int]:
    """以合成 libproc tuple 驗證正式 birth helper，沒有真實 native 呼叫。"""
    queried: list[int] = []

    class Query:
        def __call__(self, pid, _flavor, _arg, buffer, size):
            queried.append(pid)
            identity = identities[pid]
            if identity is None:
                activation.ctypes.set_errno(activation.errno.ESRCH)
                return 0
            parent, group, sec, usec = identity
            value = activation.ctypes.cast(buffer, activation.ctypes.POINTER(activation.ProcessBirth)).contents
            value.pid, value.ppid, value.pgid = pid, parent, group
            value.sec, value.usec = sec, usec
            activation.ctypes.set_errno(0)
            return size

    library = type("Libproc", (), {"proc_pidinfo": Query()})()
    monkeypatch.setattr(activation.ctypes, "CDLL", lambda *_args, **_kwargs: library)
    return queried


@pytest.mark.parametrize("fault", ["foreign_group", "foreign_parent", "invalid_birth", "pid_reuse"])
def test_boundary_stable_birth_and_pid_reuse_fail_closed(
    boundary_replay, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    """穩定後走正式 libproc helper；group／parent／birth 與舊 PID identity 仍拒絕。"""
    prepare, journal, _calls, _births, _clock = boundary_replay
    identities = {
        "foreign_group": (1, 9002, 1, 101),
        "foreign_parent": (2, 9001, 1, 101),
        "invalid_birth": (1, 9001, 0, 101),
        "pid_reuse": (1, 9001, 2, 101),
    }
    queried = _boundary_libproc(monkeypatch, {101: identities[fault]})
    prior = None
    if fault == "pid_reuse":
        prior = _boundary_lineage()
        prior["processes"] = {"101": {"birth": [1, 101], "ppid": 1, "pgid": 9001}}
        prior["active"] = [101]
    options, _replies = prepare([
        (("running", 101), ("running", 101), "101 1 9001 S /bin/sleep 300\n", ""),
    ], prior=prior, real_birth=True)
    expected = "PID reuse" if fault == "pid_reuse" else "identity UNKNOWN|ancestry UNKNOWN"
    with pytest.raises(activation.RuntimeActivationError, match=expected):
        activation.run_process_boundary(mode="observe", **options)
    saved = activation.load_action_receipt(journal)
    assert saved["status"] == "UNKNOWN_OR_FAILED" and queried == [101]
    assert saved["processes"] == (prior["processes"] if prior else {})
    assert saved["groups"] == (prior["groups"] if prior else [])


@pytest.mark.parametrize("tracked", [False, True])
def test_boundary_birth_disappearance_never_promotes_unverified_lineage(
    boundary_replay, monkeypatch: pytest.MonkeyPatch, tracked: bool,
) -> None:
    """birth 中途消失：有舊 lineage 才能 pending；新程序無身分則 fail closed。"""
    prepare, journal, _calls, _births, _clock = boundary_replay
    prior = _boundary_lineage() if tracked else None

    def vanished(pid, row, record):
        # 模擬正式 helper 的確認消失與暫存行為，不能把 birth=None 寫回 trusted journal。
        record["processes"][str(pid)] = {"birth": None, **row}
        record["resample_required"] = True
        return None

    monkeypatch.setattr(activation, "_process_birth_identity", vanished)
    options, _replies = prepare([
        (("running", 100), ("running", 100), "100 1 9002 S /bin/sleep 300\n", ""),
    ], prior=prior)
    if tracked:
        result = activation.run_process_boundary(mode="observe", **options)
        assert result["resample_required"] and result["active"] == [100]
    else:
        with pytest.raises(activation.RuntimeActivationError, match="birth missing"):
            activation.run_process_boundary(mode="observe", **options)
    saved = activation.load_action_receipt(journal)
    assert saved["processes"] == (prior["processes"] if prior else {})
    assert saved["groups"] == (prior["groups"] if prior else [])
    assert saved["seen_labels"] == (prior["seen_labels"] if prior else [])


def test_capacity_stop_pending_deadline_blocks_bootout(boundary_replay, tmp_path: Path) -> None:
    """ROOT stop 入口的 before_bootout 必須穩定；持續 pending 逾時前後都零 mutation。"""
    prepare, _journal, calls, births, _clock = boundary_replay
    options, replies = prepare([
        (("waiting", None), ("waiting", None), "", ""),
        *[(("waiting", None), ("running", 67334), "", "")] * 3,
    ])
    replies.pop(1)
    replies.pop(1)
    replies.pop(1)
    state_root = Path(options["owned_roots"]["publisher_state_root"])
    label = options["arguments"][0]
    plist = state_root / f"{label}.plist"
    plist.write_text("synthetic\n", encoding="utf-8")
    plist.chmod(0o600)
    authority = _action_authority(
        tmp_path, labels=[label], plists={label: plist}, generation="pending-stop",
        manifest_digest="e" * 64, runtime_identity_digest="f" * 64,
    )
    with runtime.runtime_shutdown_lease(state_root), pytest.raises(
        activation.RuntimeActivationError, match="deadline exceeded",
    ):
        activation.stop_capacity_services(
            [label], plist_paths={label: plist}, authority=authority,
            owned_roots=options["owned_roots"], state_root=state_root,
            receipt_path=state_root / "pending-stop.json", incident_id="pending-stop",
            generation="pending-stop", manifest_digest="e" * 64, runtime_identity_digest="f" * 64,
            timeout_seconds=0.25, runner=options["runner"], domain="gui/502",
        )
    result = activation.load_action_receipt(state_root / "pending-stop.json")
    assert result["status"] == "BLOCKED" and not result["mutation_started"]
    assert result["stopped_labels"] == [] and "deadline exceeded" in result["error"]
    assert not any(command[:2] == ["launchctl", "bootout"] for command in calls)
    assert births == [] and replies == []


def test_boundary_initializing_pid_becomes_stable_running_with_verified_birth(
    boundary_replay, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同 PID 初始化穩定後才採納有效 birth／group，最後 terminal 才能 verify PASS。"""
    prepare, journal, _calls, _births, _clock = boundary_replay
    queried = _boundary_libproc(monkeypatch, {100: (1, 9001, 1, 100)})
    options, replies = prepare([
        (("xpcproxy", 100), ("xpcproxy", 100), "100 1 0 S /usr/libexec/xpcproxy\n", ""),
        (("running", 100), ("running", 100), "100 1 9001 S /bin/sleep 300\n", ""),
        (("waiting", None), ("waiting", None), "", ""),
        (("waiting", None), ("waiting", None), "", ""),
    ], real_birth=True)
    assert activation.run_process_boundary(mode="observe", **options)["resample_required"]
    assert queried == [] and activation.load_action_receipt(journal)["groups"] == []
    stable = activation.run_process_boundary(mode="observe", **options)
    assert stable["active"] == [100] and not stable["resample_required"]
    assert queried == [100]
    saved = activation.load_action_receipt(journal)
    assert saved["groups"] == [9001] and saved["processes"]["100"]["birth"] == [1, 100]
    gone = _boundary_libproc(monkeypatch, {100: None})
    monkeypatch.setattr(activation.os, "kill", lambda _pid, _signal: (_ for _ in ()).throw(ProcessLookupError(activation.errno.ESRCH, "gone")))
    replies.pop(1)
    replies.pop(1)
    replies.pop(1)
    result = activation.verify_capacity_resume_execution(
        _boundary_resume_receipt(options), runner=options["runner"], timeout_seconds=1,
    )
    assert result["status"] == "PASS" and result["process_observation"]["active"] == []
    assert not result["process_observation"]["resample_required"] and replies == []
    assert gone == [100]


@pytest.fixture
def maintenance_boundary(boundary_replay, monkeypatch: pytest.MonkeyPatch):
    """綁定合成 maintenance authority；所有 publish 必須保留原 UNKNOWN bytes 到發布原語。"""
    prepare, journal, _calls, births, clock = boundary_replay
    events = []

    def setup(samples, *, processes=None, real_birth=False):
        prior = dict(status="UNKNOWN_OR_FAILED", error="original", deadline=-1,
                     processes=processes or {}, groups=[], seen_labels=[])
        options, replies = prepare(samples, prior=prior, real_birth=real_birth)
        target = journal.parent / "normal-rollback-drain.json"
        journal.rename(target)
        options["journal_path"] = target
        options["domain"] = f"gui/{os.getuid()}"
        original = target.read_bytes()
        binding_path = journal.parent / "binding.json"
        binding = dict(stage_path=str(journal.parent))
        manifest = dict(options["owned_roots"])
        monkeypatch.setenv("PANTHEON_MAINTENANCE_BINDING", str(binding_path))
        monkeypatch.setenv("PANTHEON_MAINTENANCE_LEASE_FD", "99")
        options["arguments"] = list(runtime.SERVICE_LABELS)
        # 每輪 services 的七個 exact label 都有對應 runner 回覆。
        expanded = []
        for command, code, body in replies:
            if command[:2] == ["launchctl", "print"]:
                for label in runtime.SERVICE_LABELS:
                    old_target = command[-1]
                    target_name = f"{options['domain']}/{label}"
                    expanded.append((["launchctl", "print", target_name], code, body.replace(old_target, target_name)))
            else:
                expanded.append((command, code, body))
        replies[:] = expanded

        def bound(path):
            assert path == binding_path
            events.append("binding")
            return binding, manifest, "bound-token"

        def lease(actual_binding, actual_manifest, fd):
            assert actual_binding == binding and actual_manifest == manifest and fd == 99
            events.append("lease")

        def control(actual_binding, actual_manifest, fd):
            lease(actual_binding, actual_manifest, fd)
            events.append("control")

        def publish(actual_binding, token, fd, actual_manifest):
            assert target.read_bytes() == original
            assert token == "bound-token"
            lease(actual_binding, actual_manifest, fd)
            events.append("publish")

        monkeypatch.setattr(activation, "maintenance_binding", bound)
        monkeypatch.setattr(activation, "maintenance_lease", lease)
        monkeypatch.setattr(activation, "maintenance_control", control)
        monkeypatch.setattr(activation, "maintenance_publish_journal", publish)
        return options, replies, original

    return setup, events, births, clock


def test_maintenance_reconcile_uses_canonical_quiescent_observer(maintenance_boundary) -> None:
    """只有 bound 且全七 label／程序靜止才發布；不先覆寫未知 journal。"""
    setup, events, births, _clock = maintenance_boundary
    options, replies, original = setup([(("ABSENT", None), ("ABSENT", None), "", "")])
    result = activation.run_process_boundary(mode="reconcile", **options)
    assert result["status"] == "DRAINED" and not replies and not births
    assert events.count("binding") >= 2 and events.count("control") >= 2
    assert events.count("publish") == 1 and events[-1] == "publish"
    assert options["journal_path"].read_bytes() == original


@pytest.mark.parametrize("first,second,ps", [
    (("waiting", None), ("running", 100), ""),
    (("xpcproxy", 100), ("running", 100), "100 1 0 S /usr/libexec/xpcproxy\n"),
    (("xpcproxy", None), ("xpcproxy", None), ""),
    (("running", 100), ("running", 100), "100 1 9001 S /bin/sleep 300\n"),
])
def test_maintenance_pending_or_active_never_publishes(
    maintenance_boundary, first, second, ps,
) -> None:
    """maintenance 的不穩定／初始化／active 證據不准一般 save 或發布 reconciled journal。"""
    setup, events, _births, _clock = maintenance_boundary
    options, _replies, original = setup([(first, second, ps, "")])
    with pytest.raises(activation.RuntimeActivationError, match="not terminal"):
        activation.run_process_boundary(mode="reconcile", **options)
    assert "publish" not in events and options["journal_path"].read_bytes() == original


@pytest.mark.parametrize("proof", ["gone", "live", "pid_reuse", "unknown_birth", "still_present", "permission"])
def test_maintenance_known_pid_missing_ps_requires_targeted_birth_and_kill0(
    maintenance_boundary, monkeypatch: pytest.MonkeyPatch, proof: str,
) -> None:
    """ps 漏已知 PID 時仍查正式 libproc seam；只有 ESRCH＋kill0 absence 可發布。"""
    setup, events, _births, _clock = maintenance_boundary
    previous = dict(birth=None if proof == "unknown_birth" else [1, 100], ppid=1, pgid=9001)
    identity = None if proof in {"gone", "still_present", "permission"} else (1, 9001, 2 if proof == "pid_reuse" else 1, 100)
    queried = _boundary_libproc(monkeypatch, {100: identity})
    probes = []

    def kill0(pid, signal):
        assert pid == 100 and signal == 0
        probes.append((pid, signal))
        if proof == "gone":
            raise ProcessLookupError(activation.errno.ESRCH, "gone")
        if proof == "permission":
            raise PermissionError(activation.errno.EPERM, "denied")

    monkeypatch.setattr(activation.os, "kill", kill0)
    options, _replies, original = setup(
        [(("ABSENT", None), ("ABSENT", None), "", "")],
        processes={"100": previous}, real_birth=True,
    )
    if proof == "gone":
        assert activation.run_process_boundary(mode="reconcile", **options)["status"] == "DRAINED"
        assert events.count("publish") == 1 and probes == [(100, 0)]
    else:
        with pytest.raises(activation.RuntimeActivationError, match="not terminal|PID reuse|identity UNKNOWN"):
            activation.run_process_boundary(mode="reconcile", **options)
        assert "publish" not in events
    assert queried == [100] and options["journal_path"].read_bytes() == original


@pytest.mark.parametrize("gate", ["binding", "lease", "control_before", "control_after", "binding_after"])
def test_maintenance_authority_drift_never_saves_or_publishes(
    maintenance_boundary, monkeypatch: pytest.MonkeyPatch, gate: str,
) -> None:
    """綁定／lease／fence 前後 gate 失敗都保持原 UNKNOWN，不能繞過發布原語。"""
    setup, events, _births, _clock = maintenance_boundary
    options, _replies, original = setup([(("ABSENT", None), ("ABSENT", None), "", "")])
    function = "maintenance_binding" if gate.startswith("binding") else "maintenance_lease" if gate == "lease" else "maintenance_control"
    original_gate = getattr(activation, function)
    calls = []

    def drift(*args):
        calls.append(args)
        if len(calls) == (2 if gate.endswith("after") else 1):
            raise activation.RuntimeActivationError("injected authority drift")
        return original_gate(*args)

    monkeypatch.setattr(activation, function, drift)
    with pytest.raises(activation.RuntimeActivationError, match="authority drift"):
        activation.run_process_boundary(mode="reconcile", **options)
    assert "publish" not in events and options["journal_path"].read_bytes() == original


@pytest.mark.parametrize("mode", ["observe", "drain", "control", "absent"])
def test_ordinary_unknown_journal_cannot_use_maintenance_bypass(boundary_replay, mode: str) -> None:
    """普通四模式一律先拒絕已 latch 的 UNKNOWN，不能送出任何 runner 指令。"""
    prepare, journal, calls, _births, _clock = boundary_replay
    prior = {**_boundary_lineage(), "status": "UNKNOWN_OR_FAILED", "error": "original"}
    options, _replies = prepare([], prior=prior)
    original = journal.read_bytes()
    with pytest.raises(activation.RuntimeActivationError, match="prior process evidence is unresolved"):
        activation.run_process_boundary(mode=mode, **options)
    assert calls == [] and journal.read_bytes() == original


def test_maintenance_cli_dispatch_preserves_upstream_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    """既有 run／prepare／restore／finish CLI 仍映射原 maintenance 原語。"""
    seen = []
    monkeypatch.setattr(activation, "_maintenance_main", lambda argv: seen.append(argv) or 0)
    for mode in ("run", "prepare", "restore", "finish"):
        assert activation.main([mode, "/synthetic/binding.json"]) == 0
    assert [arguments[0] for arguments in seen] == ["run", "prepare", "restore", "finish"]


@pytest.mark.parametrize("drift", ["journal", "domain", "labels", "roots", "binding_after"])
def test_maintenance_exact_observer_binding_rejects_drift(
    maintenance_boundary, monkeypatch: pytest.MonkeyPatch, drift: str,
) -> None:
    """不可把已 bound 的 maintenance authority 套用到另一 journal／domain／labels／roots。"""
    setup, events, _births, _clock = maintenance_boundary
    options, _replies, original = setup([(("ABSENT", None), ("ABSENT", None), "", "")])
    journal = options["journal_path"]
    if drift == "journal":
        options["journal_path"] = journal.with_name("unbound.json")
    elif drift == "domain":
        options["domain"] = "gui/99999"
    elif drift == "labels":
        options["arguments"] = options["arguments"][:-1]
    elif drift == "roots":
        options["owned_roots"]["queue_root"] = options["owned_roots"]["actor_root"]
    else:
        bound = activation.maintenance_binding
        calls = []

        def changed(path):
            calls.append(path)
            binding, manifest, token = bound(path)
            return binding, manifest, token if len(calls) == 1 else "changed-token"

        monkeypatch.setattr(activation, "maintenance_binding", changed)
    with pytest.raises(activation.RuntimeActivationError, match="binding mismatch|binding changed"):
        activation.run_process_boundary(mode="reconcile", **options)
    assert "publish" not in events and journal.read_bytes() == original


def test_verify_trusted_running_seed_missing_ps_never_passes(boundary_replay) -> None:
    """F2：先 terminal PASS、後穩定 running 的已知 seed 缺 ps，不能沿用舊 seen_labels PASS。"""
    prepare, journal, _calls, _births, _clock = boundary_replay
    prior = {**_boundary_lineage(), "active": []}
    options, replies = prepare([
        (("waiting", None), ("waiting", None), "", ""),
        (("running", 100), ("running", 100), "", ""),
    ], prior=prior)
    for _ in range(3):
        replies.pop(1)
    result = activation.verify_capacity_resume_execution(
        _boundary_resume_receipt(options), runner=options["runner"], timeout_seconds=1,
    )
    assert result["services"][options["arguments"][0]]["status"] == "PASS"
    assert result["status"] in {"PENDING", "UNKNOWN"}, "stable missing trusted seed 不得 false PASS"
    saved = activation.load_action_receipt(journal)
    assert saved["processes"] == prior["processes"] and saved["groups"] == prior["groups"]


@pytest.mark.parametrize("mode", ["observe", "drain"])
@pytest.mark.parametrize("proof", ["gone", "live", "pid_reuse", "still_present", "permission"])
def test_tracked_orphan_missing_ps_requires_targeted_absence(
    boundary_replay, monkeypatch: pytest.MonkeyPatch, mode: str, proof: str,
) -> None:
    """舊 orphan 缺 ps 也不能單靠空 rows 消失；正式 birth／kill0 證明決定 pending／拒絕。"""
    prepare, journal, _calls, _births, clock = boundary_replay
    prior = {**_boundary_lineage(), "active": []}
    identity = None if proof in {"gone", "still_present", "permission"} else (1, 9001, 2 if proof == "pid_reuse" else 1, 100)
    queried = _boundary_libproc(monkeypatch, {100: identity})
    probes = []

    def kill0(pid, signal):
        assert (pid, signal) == (100, 0)
        probes.append((pid, signal))
        if proof == "gone":
            raise ProcessLookupError(activation.errno.ESRCH, "gone")
        if proof == "permission":
            raise PermissionError(activation.errno.EPERM, "denied")

    monkeypatch.setattr(activation.os, "kill", kill0)
    sample = (("waiting", None), ("waiting", None), "", "")
    options, _replies = prepare([sample] * (3 if mode == "drain" and proof == "live" else 1), prior=prior, real_birth=True)
    options["timeout_seconds"] = 0.25
    if proof == "gone" or (proof == "live" and mode == "observe"):
        result = activation.run_process_boundary(mode=mode, **options)
        if proof == "live":
            assert result["resample_required"] and result["status"] == "OBSERVED"
        else:
            assert result["status"] == ("DRAINED" if mode == "drain" else "OBSERVED")
            assert probes == [(100, 0)]
    else:
        with pytest.raises(activation.RuntimeActivationError, match="PID reuse|identity UNKNOWN|deadline exceeded"):
            activation.run_process_boundary(mode=mode, **options)
    assert queried and set(queried) == {100}
    saved = activation.load_action_receipt(journal)
    assert saved["processes"] == prior["processes"] and saved["groups"] == prior["groups"]
    assert saved["seen_labels"] == prior["seen_labels"]
    if mode == "drain" and proof == "live":
        assert saved["deadline"] == clock[0] == 0.25 and len(queried) == 3


@pytest.fixture
def prior_resume_stop(boundary_replay, tmp_path: Path):
    """建立同 scope 的 private resume receipt 與 derived trusted journal，走真 stop API。"""
    prepare, _journal, calls, births, clock = boundary_replay

    def setup(samples, *, lineage=None):
        options, replies = prepare(samples)
        label = options["arguments"][0]
        state = Path(options["owned_roots"]["publisher_state_root"])
        plist = state / f"{label}.plist"
        plist.write_text("synthetic\n", encoding="utf-8")
        plist.chmod(0o600)
        authority = _action_authority(tmp_path, labels=[label], plists={label: plist},
                                      generation="prior-safe", manifest_digest="e" * 64, runtime_identity_digest="f" * 64)
        source = state / "resume.json"
        journal = source.with_name(f".{source.name}.verification-processes.json")
        receipt = activation._action_identity(
            action="capacity-resume", incident_id="prior-safe", generation="prior-safe",
            manifest_digest="e" * 64, runtime_identity_digest="f" * 64, labels=[label],
            owned_roots=options["owned_roots"], receipt_path=source, domain=options["domain"],
        )
        receipt.update(status="STARTED", attempted_labels=[label], started_labels=[label],
                       authority=authority, process_journal_path=str(journal))
        activation._write_private_json(source, receipt)
        activation._write_private_json(journal, _boundary_lineage() if lineage is None else lineage)
        stop = dict(labels=[label], plist_paths={label: plist}, authority=authority,
                    owned_roots=options["owned_roots"], state_root=state, receipt_path=state / "rollback.json",
                    incident_id="prior-safe", generation="prior-safe", manifest_digest="e" * 64,
                    runtime_identity_digest="f" * 64, timeout_seconds=0.25, runner=options["runner"],
                    domain=options["domain"], allow_absent=True,
                    resume_action_receipt=activation.capture_file_identity(source))
        return stop, source, journal, replies

    return setup, calls, births, clock


def test_stop_inherits_old_foreign_orphan_and_does_not_bootout(prior_resume_stop) -> None:
    """F1 直接 stop：orphan 離 roots 後仍有可信 birth，延續 source journal 並在總期限拒絕。"""
    setup, calls, births, clock = prior_resume_stop
    sample = (("waiting", None), ("waiting", None), "100 1 9001 S /bin/sleep 300\n", "p100\nfcwd\nn/\n")
    stop, _source, journal, replies = setup([sample] * 4)
    for _ in range(3):
        replies.pop(1)
    original = journal.read_bytes()
    with runtime.runtime_shutdown_lease(stop["state_root"]), pytest.raises(activation.RuntimeActivationError, match="deadline exceeded"):
        activation.stop_capacity_services(**stop)
    failed = activation.load_action_receipt(stop["receipt_path"])
    assert failed["status"] == "BLOCKED" and not failed["mutation_started"]
    assert failed["prior_lineage"]["resume_action_receipt"] == stop["resume_action_receipt"]
    target = stop["receipt_path"].with_name(f".{stop['receipt_path'].name}.processes.json")
    lineage = activation.load_action_receipt(target)
    assert lineage["processes"]["100"]["birth"] == [1, 100]
    assert lineage["groups"] == [9001] and lineage["seen_labels"] == stop["labels"]
    assert clock[0] == 0.25 and births == [100, 100, 100]
    assert not any(command[:2] == ["launchctl", "bootout"] for command in calls)
    assert journal.read_bytes() == original


@pytest.mark.parametrize("merge_existing", [False, True])
def test_stop_prior_lineage_gone_can_finish_without_dropping_records(prior_resume_stop, merge_existing: bool) -> None:
    """已證明 terminal 才成功；合併 source／既有 scoped target，保留所有 birth／groups／最早期限。"""
    setup, calls, births, _clock = prior_resume_stop
    waiting = (("waiting", None), ("waiting", None), "", "")
    absent = (("ABSENT", None), ("ABSENT", None), "", "")
    stop, source, journal, replies = setup([waiting, waiting, waiting, absent, absent])
    source_lineage = activation.load_action_receipt(journal)
    source_lineage["deadline"] = 0.2
    activation._write_private_json(journal, source_lineage)
    target = stop["receipt_path"].with_name(f".{stop['receipt_path'].name}.processes.json")
    if merge_existing:
        destination = {**_boundary_lineage(), "processes": {"200": dict(birth=[1, 200], ppid=1, pgid=9200)},
                       "groups": [9200], "active": [200], "deadline": 0.1}
        activation._write_private_json(target, destination)
        previous = {**activation.load_action_receipt(source), "action": "capacity-stop",
                    "receipt_path": str(stop["receipt_path"]), "process_journal_path": str(target)}
        activation._write_private_json(stop["receipt_path"], previous)
    original = journal.read_bytes()
    before = list(replies)
    bootout = (["launchctl", "bootout", f"{stop['domain']}/{stop['labels'][0]}"], 0, "")
    replies[:] = [before[0], *before[4:8], before[8], before[11], bootout, before[12], *before[16:20]]
    with runtime.runtime_shutdown_lease(stop["state_root"]):
        result = activation.stop_capacity_services(**stop)
    assert result["status"] == "STOPPED" and result["mutation_started"]
    assert result["process_drain"]["before_bootout"]["status"] == "DRAINED"
    assert result["process_drain"]["after_bootout"]["status"] == "DRAINED"
    saved = activation.load_action_receipt(target)
    assert set(saved["processes"]) == ({"100", "200"} if merge_existing else {"100"})
    assert saved["processes"]["100"]["birth"] == [1, 100]
    assert saved["groups"] == ([9001, 9200] if merge_existing else [9001])
    assert saved["deadline"] == (0.1 if merge_existing else 0.2)
    assert saved["seen_labels"] == stop["labels"] and journal.read_bytes() == original
    assert len([command for command in calls if command[:2] == ["launchctl", "bootout"]]) == 1
    assert 100 in births and not replies


@pytest.mark.parametrize("unbound", [False, True])
def test_stop_different_scope_cannot_be_laundered_by_retry(prior_resume_stop, unbound: bool) -> None:
    """拒絕 scope 前不准覆寫舊 action metadata；再次同名呼叫也不能抹掉原 responsibility。"""
    setup, calls, _births, _clock = prior_resume_stop
    stop, source, _journal, _replies = setup([])
    target = stop["receipt_path"].with_name(f".{stop['receipt_path'].name}.processes.json")
    activation._write_private_json(target, _boundary_lineage())
    previous = {**activation.load_action_receipt(source), "action": "capacity-stop", "incident_id": "other-incident",
                "receipt_path": str(stop["receipt_path"]), "process_journal_path": str(target)}
    if not unbound:
        activation._write_private_json(stop["receipt_path"], previous)
    original = stop["receipt_path"].read_bytes() if stop["receipt_path"].exists() else None
    original_journal = target.read_bytes()
    with runtime.runtime_shutdown_lease(stop["state_root"]):
        for _ in range(2):
            with pytest.raises(activation.RuntimeActivationError, match="journal scope mismatch"):
                activation.stop_capacity_services(**stop)
            assert target.read_bytes() == original_journal
            if original is None:
                assert not stop["receipt_path"].exists()
            else:
                assert stop["receipt_path"].read_bytes() == original
    assert calls == []


def test_stop_conflicting_trusted_births_cannot_merge(prior_resume_stop) -> None:
    """同 PID 的兩份可信 lineage birth 不一致時，不能盲選其中一份。"""
    setup, calls, _births, _clock = prior_resume_stop
    stop, source, _journal, _replies = setup([])
    target = stop["receipt_path"].with_name(f".{stop['receipt_path'].name}.processes.json")
    different = _boundary_lineage()
    different["processes"]["100"]["birth"] = [2, 100]
    activation._write_private_json(target, different)
    previous = {**activation.load_action_receipt(source), "action": "capacity-stop",
                "receipt_path": str(stop["receipt_path"]), "process_journal_path": str(target)}
    activation._write_private_json(stop["receipt_path"], previous)
    original = target.read_bytes()
    with runtime.runtime_shutdown_lease(stop["state_root"]), pytest.raises(activation.RuntimeActivationError, match="lineage identity conflict"):
        activation.stop_capacity_services(**stop)
    assert calls == [] and target.read_bytes() == original


@pytest.mark.parametrize("drift", [
    "incident_id", "generation", "manifest_digest", "runtime_identity_digest", "owned_roots", "domain",
    "action", "labels", "attempted_labels", "authority", "process_journal_path", "receipt_path",
    "receipt_bytes", "receipt_mode", "journal_symlink", "source_unknown", "target_unknown", "source_missing",
    "birth_unknown", "groups_invalid", "deadline_invalid",
])
def test_stop_rejects_unbound_or_unresolved_prior_lineage(prior_resume_stop, drift: str) -> None:
    """scope／Owner／derived path／UNKNOWN／不可信 birth 失敗不能轉空 journal 或送出 bootout。"""
    setup, calls, _births, _clock = prior_resume_stop
    stop, source, journal, _replies = setup([])
    receipt = activation.load_action_receipt(source)
    lineage = activation.load_action_receipt(journal)
    if drift in {"incident_id", "generation", "manifest_digest", "runtime_identity_digest", "domain", "action", "receipt_path", "process_journal_path"}:
        receipt[drift] = "other-scope"
    elif drift == "owned_roots":
        receipt["owned_roots"]["queue_root"] = receipt["owned_roots"]["actor_root"]
    elif drift in {"labels", "attempted_labels"}:
        receipt[drift] = [runtime.SERVICE_LABELS[1]]
    elif drift == "authority":
        receipt["authority"]["barrier"]["sha256"] = "0" * 64
    elif drift == "receipt_bytes":
        source.write_text("drift\n")
    elif drift == "receipt_mode":
        source.chmod(0o644)
    elif drift == "journal_symlink":
        original_path = journal.with_name("foreign.json")
        journal.rename(original_path)
        journal.symlink_to(original_path)
    elif drift == "source_missing":
        journal.unlink()
    elif drift == "source_unknown":
        lineage.update(status="UNKNOWN_OR_FAILED", error="original unresolved")
    elif drift == "target_unknown":
        destination = stop["receipt_path"].with_name(f".{stop['receipt_path'].name}.processes.json")
        activation._write_private_json(destination, {**lineage, "status": "UNKNOWN_OR_FAILED", "error": "original unresolved"})
        previous = {**receipt, "action": "capacity-stop", "receipt_path": str(stop["receipt_path"]),
                    "process_journal_path": str(destination)}
        activation._write_private_json(stop["receipt_path"], previous)
    elif drift == "birth_unknown":
        lineage["processes"]["100"]["birth"] = None
    elif drift == "groups_invalid":
        lineage["groups"] = [1]
    elif drift == "deadline_invalid":
        lineage["deadline"] = float("nan")
    if drift not in {"receipt_bytes", "receipt_mode"}:
        activation._write_private_json(source, receipt)
        stop["resume_action_receipt"] = activation.capture_file_identity(source)
    if drift in {"source_unknown", "birth_unknown", "groups_invalid", "deadline_invalid"}:
        if drift == "deadline_invalid":
            journal.write_text(json.dumps(lineage), encoding="utf-8")
        else:
            activation._write_private_json(journal, lineage)
    original_source = source.read_bytes()
    original_journal = journal.read_bytes() if journal.exists() else None
    with runtime.runtime_shutdown_lease(stop["state_root"]), pytest.raises(activation.RuntimeActivationError):
        activation.stop_capacity_services(**stop)
    assert calls == [] and source.read_bytes() == original_source
    if journal.exists():
        assert journal.read_bytes() == original_journal
    failed = activation.load_action_receipt(stop["receipt_path"])
    assert failed["status"] == "BLOCKED" and not failed["mutation_started"]

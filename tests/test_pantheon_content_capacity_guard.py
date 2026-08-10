from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from scripts import pantheon_content_capacity_guard as guard
from scripts import pantheon_content_runtime_manifest as runtime_manifest


def _completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, "")


def _available_snapshot(bytes_used: int = 100 * guard.MIB) -> dict[str, object]:
    return {
        "bytes": bytes_used,
        "file_count": 100,
        "disk_total_bytes": 200 * guard.GIB,
        "disk_free_bytes": 100 * guard.GIB,
        "rss_bytes": 0,
        "rss_available": True,
        "rss_error": None,
        "rss_identity": {"loaded_labels": [], "absent_labels": list(guard.SERVICE_LABELS)},
        "swap_used_bytes": 0,
        "swap_available": True,
        "swap_error": None,
    }


def test_log_rotation_keeps_inode_and_tail(tmp_path: Path) -> None:
    path = tmp_path / guard.LOG_NAMES[0]
    body = b"a" * guard.LOG_MAX_BYTES + b"final-tail"
    path.write_bytes(body)
    inode = path.stat().st_ino

    reclaimed = guard._trim_log(path)

    assert reclaimed == len(body) - guard.LOG_RETAIN_BYTES
    assert path.stat().st_ino == inode
    assert path.stat().st_size == guard.LOG_RETAIN_BYTES
    assert path.read_bytes().endswith(b"final-tail")


def test_measure_tree_ignores_directory_that_disappears_during_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    stable = tmp_path / "stable.json"
    stable.write_bytes(b"stable")
    disappearing = tmp_path / "transaction" / "repo" / "batch"
    disappearing.mkdir(parents=True)
    (disappearing / "candidate.json").write_bytes(b"candidate")
    real_scandir = os.scandir

    def disappearing_scandir(path: str | os.PathLike[str]):
        if Path(path) == disappearing:
            (disappearing / "candidate.json").unlink()
            disappearing.rmdir()
        return real_scandir(path)

    monkeypatch.setattr(guard.os, "scandir", disappearing_scandir)

    assert guard._measure_tree(tmp_path) == (len(b"stable"), 1)


def test_preflight_rejects_low_disk_without_mutation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 19 * guard.GIB))
    monkeypatch.setattr(
        guard,
        "_service_rss_bytes",
        lambda: {
            "value": 0,
            "available": True,
            "error": None,
            "identity": {"loaded_labels": [], "absent_labels": list(guard.SERVICE_LABELS)},
        },
    )
    monkeypatch.setattr(
        guard, "_swap_used_bytes", lambda: {"value": 0, "available": True, "error": None}
    )

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "NO-GO"
    assert result["reasons"] == ["disk_free_below_start_floor"]


def test_preflight_accepts_free_space_above_ten_percent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 25 * guard.GIB))
    monkeypatch.setattr(
        guard,
        "_service_rss_bytes",
        lambda: {
            "value": 0,
            "available": True,
            "error": None,
            "identity": {"loaded_labels": [], "absent_labels": list(guard.SERVICE_LABELS)},
        },
    )
    monkeypatch.setattr(
        guard, "_swap_used_bytes", lambda: {"value": 0, "available": True, "error": None}
    )

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "PASS"
    assert result["reasons"] == []


def test_preflight_accepts_exactly_ten_percent_free(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 20 * guard.GIB))
    monkeypatch.setattr(
        guard,
        "_service_rss_bytes",
        lambda: {
            "value": 0,
            "available": True,
            "error": None,
            "identity": {"loaded_labels": [], "absent_labels": list(guard.SERVICE_LABELS)},
        },
    )
    monkeypatch.setattr(
        guard, "_swap_used_bytes", lambda: {"value": 0, "available": True, "error": None}
    )

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "PASS"


def test_check_over_budget_stops_only_registered_services(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "queue"
    publisher = tmp_path / "publisher"
    logs = tmp_path / "logs"
    for root in (queue, publisher, logs):
        root.mkdir()
    state = queue / "capacity-state.json"
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_roots: {**_available_snapshot(guard.MAX_BYTES + 1), "file_count": 1},
    )
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return _completed(113 if command[1] == "print" else 0)

    result = guard.check_once(queue, publisher, logs, state, now=1000, stop_runner=runner)

    assert result["status"] == "STOPPED"
    assert result["reasons"] == ["project_bytes_over_budget"]
    assert [
        command[-1].split("/")[-1] for command in commands if command[1] == "bootout"
    ] == list(guard.SERVICE_LABELS)
    assert json.loads(state.read_text())["status"] == "STOPPED"


def test_check_within_budget_records_pass_without_bootout(tmp_path: Path, monkeypatch) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_roots: _available_snapshot(),
    )

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("healthy sample must not call launchctl bootout")

    result = guard.check_once(*roots, roots[0] / "state.json", now=1000, stop_runner=forbidden)

    assert result["status"] == "PASS"
    assert result["growth_bytes_per_hour"] == 0


def test_two_high_growth_cycles_trigger_bounded_stop_loss(
    tmp_path: Path,
    monkeypatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    samples = iter(
        [
            512 * guard.MIB,
            1536 * guard.MIB,
            2560 * guard.MIB,
        ]
    )

    def snapshot(*_roots: Path) -> dict[str, object]:
        return _available_snapshot(next(samples))

    monkeypatch.setattr(guard, "_snapshot", snapshot)
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return _completed(113 if command[1] == "print" else 0)

    state = roots[0] / "state.json"
    baseline = guard.check_once(*roots, state, now=1000, stop_runner=runner)
    first = guard.check_once(*roots, state, now=1300, stop_runner=runner)
    second = guard.check_once(*roots, state, now=1600, stop_runner=runner)

    assert baseline["status"] == "PASS"
    assert first["status"] == "PASS"
    assert first["high_growth_streak"] == 1
    assert second["status"] == "STOPPED"
    assert second["reasons"] == ["growth_rate_would_cross_budget"]
    assert [
        command[-1].split("/")[-1] for command in commands if command[1] == "bootout"
    ] == list(guard.SERVICE_LABELS)


def test_launchd_template_and_installer_keep_five_minute_fail_closed_contract() -> None:
    repo = Path(__file__).resolve().parents[1]
    template = (repo / "ops/launchd/com.pantheon.content-capacity-guard.plist.example").read_text()
    installer = (repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh").read_text()

    assert "<integer>300</integer>" in template
    assert "scripts.pantheon_content_capacity_guard" in template
    assert "preflight" in installer
    assert 'USER_HOME_DIR="${PANTHEON_USER_HOME_DIR:-}"' in installer
    assert 'launchctl bootstrap "gui/${USER_ID}"' in installer
    assert os.access(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh", os.X_OK)


def test_capacity_installer_preflight_has_no_target_or_control_plane_mutation(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    queue_root = tmp_path / "queue"
    publisher_root = tmp_path / "publisher"
    log_root = tmp_path / "logs"
    state_file = queue_root / "capacity-state.json"
    mutation_log = tmp_path / "launchctl-mutations.log"
    fake_bin.mkdir()
    queue_root.mkdir()
    publisher_root.mkdir()
    log_root.mkdir()
    manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=queue_root,
        publisher_state_root=publisher_root,
        log_root=log_root,
        identity="synthetic-capacity:501",
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 113; fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    sysctl = fake_bin / "sysctl"
    sysctl.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'total = 0.00M  used = 0.00M  free = 0.00M'\n",
        encoding="utf-8",
    )
    sysctl.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PANTHEON_CAPACITY_GUARD_STATE_FILE": str(state_file),
            "PANTHEON_USER_HOME_DIR": str(fake_home),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "TMPDIR": str(tmp_path),
        }
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--preflight",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert '"status": "PASS"' in completed.stdout
    assert list(publisher_root.iterdir()) == []
    assert list(log_root.iterdir()) == []
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_unknown_rss_or_swap_telemetry_is_no_go(tmp_path: Path, monkeypatch) -> None:
    """REG-PANTHEON-CAPACITY-UNKNOWN-METRICS-NO-GO-001。"""
    sample = _available_snapshot()
    sample.update({"rss_bytes": None, "rss_available": False, "rss_error": "ps_failed"})
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "NO-GO"
    assert "rss_telemetry_unknown" in result["reasons"]


def test_stop_loss_is_stopped_only_after_every_registered_identity_is_absent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """REG-PANTHEON-CAPACITY-STOP-VERIFICATION-001。"""
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    sample = _available_snapshot(guard.MAX_BYTES + 1)
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)
    failed_label = guard.SERVICE_LABELS[2]

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        label = command[-1].split("/")[-1]
        if command[1] == "bootout":
            return _completed(5 if label == failed_label else 0)
        if label == failed_label:
            return _completed(0, "pid = 4242\n")
        return _completed(113)

    result = guard.check_once(*roots, roots[0] / "state.json", stop_runner=runner)

    assert result["status"] == "STOP_FAILED"
    assert result["stop_verification"][failed_label]["absent"] is False
    assert result["stop_verification"][failed_label]["bootout_returncode"] == 5
    assert set(result["stop_verification"]) == set(guard.SERVICE_LABELS)


def test_bounded_runner_records_two_write_cycles_reclamation_and_stop_loss(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-CAPACITY-WRITE-CYCLES-001。"""
    receipt_path = tmp_path / "capacity-exercise.json"
    receipt = guard.run_bounded_exercise(
        tmp_path / "exercise",
        receipt_path,
        cycle_bytes=4096,
    )

    assert receipt["status"] == "PASS"
    assert len(receipt["cycles"]) == 2
    for cycle in receipt["cycles"]:
        assert {
            "before_bytes",
            "after_bytes",
            "before_file_count",
            "after_file_count",
            "host_free_before",
            "host_free_after",
            "rss_before",
            "rss_after",
            "swap_before",
            "swap_after",
            "elapsed_seconds",
            "growth_bytes",
        } <= cycle.keys()
    assert receipt["reclamation"]["bytes_after"] < receipt["reclamation"]["bytes_before"]
    assert receipt["stop_loss"]["status"] == "STOPPED"
    assert receipt["stop_loss"]["cross_project_deletions"] == []
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt

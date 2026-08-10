from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from scripts import pantheon_content_capacity_guard as guard


def _completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, "")


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
    monkeypatch.setattr(guard, "_service_rss_bytes", lambda: 0)
    monkeypatch.setattr(guard, "_swap_used_bytes", lambda: 0)

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "NO-GO"
    assert result["reasons"] == ["disk_free_below_start_floor"]


def test_preflight_accepts_free_space_above_ten_percent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 25 * guard.GIB))
    monkeypatch.setattr(guard, "_service_rss_bytes", lambda: 0)
    monkeypatch.setattr(guard, "_swap_used_bytes", lambda: 0)

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "PASS"
    assert result["reasons"] == []


def test_preflight_accepts_exactly_ten_percent_free(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 20 * guard.GIB))
    monkeypatch.setattr(guard, "_service_rss_bytes", lambda: 0)
    monkeypatch.setattr(guard, "_swap_used_bytes", lambda: 0)

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
        lambda *_roots: {
            "bytes": guard.MAX_BYTES + 1,
            "file_count": 1,
            "disk_total_bytes": 200 * guard.GIB,
            "disk_free_bytes": 100 * guard.GIB,
            "rss_bytes": 0,
            "swap_used_bytes": 0,
        },
    )
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return _completed()

    result = guard.check_once(queue, publisher, logs, state, now=1000, stop_runner=runner)

    assert result["status"] == "STOPPED"
    assert result["reasons"] == ["project_bytes_over_budget"]
    assert [command[-1].split("/")[-1] for command in commands] == list(guard.SERVICE_LABELS)
    assert json.loads(state.read_text())["status"] == "STOPPED"


def test_check_within_budget_records_pass_without_bootout(tmp_path: Path, monkeypatch) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_roots: {
            "bytes": 100 * guard.MIB,
            "file_count": 100,
            "disk_total_bytes": 200 * guard.GIB,
            "disk_free_bytes": 100 * guard.GIB,
            "rss_bytes": 0,
            "swap_used_bytes": 0,
        },
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

    def snapshot(*_roots: Path) -> dict[str, int]:
        return {
            "bytes": next(samples),
            "file_count": 100,
            "disk_total_bytes": 200 * guard.GIB,
            "disk_free_bytes": 100 * guard.GIB,
            "rss_bytes": 0,
            "swap_used_bytes": 0,
        }

    monkeypatch.setattr(guard, "_snapshot", snapshot)
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return _completed()

    state = roots[0] / "state.json"
    baseline = guard.check_once(*roots, state, now=1000, stop_runner=runner)
    first = guard.check_once(*roots, state, now=1300, stop_runner=runner)
    second = guard.check_once(*roots, state, now=1600, stop_runner=runner)

    assert baseline["status"] == "PASS"
    assert first["status"] == "PASS"
    assert first["high_growth_streak"] == 1
    assert second["status"] == "STOPPED"
    assert second["reasons"] == ["growth_rate_would_cross_budget"]
    assert [command[-1].split("/")[-1] for command in commands] == list(
        guard.SERVICE_LABELS
    )


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
    log_root = fake_home / "Library" / "Logs" / "Pantheon"
    state_file = queue_root / "capacity-state.json"
    mutation_log = tmp_path / "launchctl-mutations.log"
    fake_bin.mkdir()
    queue_root.mkdir()
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 1; fi\n"
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
    assert not publisher_root.exists()
    assert not log_root.exists()
    assert not fake_home.exists()
    assert not mutation_log.exists()

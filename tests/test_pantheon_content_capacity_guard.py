from __future__ import annotations

import json
import os
import plistlib
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import pantheon_content_capacity_guard as guard
from scripts import pantheon_content_runtime_manifest as runtime_manifest


ANONYMIZED_INERT_LAUNCHCTL_FIXTURE = """<target> = {
\tactive count = 0
\tstate = not running

\tresource coalition = {
\t\tID = 100
\t\ttype = resource
\t\tstate = active
\t\tactive count = 1
\t}

\tjetsam coalition = {
\t\tID = 101
\t\ttype = jetsam
\t\tstate = active
\t\tactive count = 1
\t}
}
"""


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


def test_formal_capacity_guard_rejects_manifest_drift_before_state_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "publisher-state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-capacity",
        runtime_digest="4" * 64,
        generation="generation-capacity",
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
        "PANTHEON_RUNTIME_SERVICE_LABEL", "com.pantheon.content-capacity-guard"
    )
    manifest_path.write_text("{}\n", encoding="utf-8")
    state_file = tmp_path / "capacity-state.json"

    with pytest.raises(runtime_manifest.RuntimeManifestError):
        guard.check_once(queue, state, logs, state_file)

    assert not state_file.exists()


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
    assert 'launchctl bootstrap "gui/${USER_ID}"' not in installer
    assert ".pantheon-four-lane-stage" in installer
    assert "optional_manifest_field actor_head" in installer
    assert "optional_manifest_field python_executable" in installer
    assert "PANTHEON_RUNTIME_ACTOR_HEAD" in installer
    assert "PANTHEON_RUNTIME_PYTHON_EXECUTABLE" in installer
    assert 'PYTHON_BIN="${PYTHON_REALPATH}"' in installer
    assert '--expected-python-executable "${PYTHON_BIN}"' in installer
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
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest[
                "manifest_digest"
            ],
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


def test_hardened_capacity_installer_uses_canonical_python_in_staged_plist(
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
    python_target = Path(sys.executable).resolve(strict=True)
    python_link = tmp_path / "python-link"
    for path in (fake_bin, queue_root, publisher_root, log_root):
        path.mkdir()
    python_link.symlink_to(python_target)
    (fake_bin / "dscl").write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    (fake_bin / "dscl").chmod(0o700)
    (fake_bin / "launchctl").write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 113; fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "launchctl").chmod(0o700)
    (fake_bin / "sysctl").write_text(
        "#!/bin/sh\nprintf '%s\\n' 'total = 0.00M  used = 0.00M  free = 0.00M'\n",
        encoding="utf-8",
    )
    (fake_bin / "sysctl").chmod(0o700)
    manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=queue_root,
        publisher_state_root=publisher_root,
        log_root=log_root,
        identity="synthetic-capacity:python",
        python_executable=python_target,
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PANTHEON_CAPACITY_GUARD_STATE_FILE": str(state_file),
            "PANTHEON_USER_HOME_DIR": str(fake_home),
            "PANTHEON_PYTHON_PATH": str(python_link),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest[
                "manifest_digest"
            ],
            "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "TMPDIR": str(tmp_path),
        }
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert not mutation_log.exists()
    staged = (
        fake_home
        / "Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    )
    payload = plistlib.loads(staged.read_bytes())
    assert payload["ProgramArguments"][0] == str(python_target)
    assert payload["ProgramArguments"][17] == str(python_target)
    assert payload["EnvironmentVariables"]["PANTHEON_RUNTIME_PYTHON_EXECUTABLE"] == str(
        python_target
    )


def test_hardened_capacity_installer_rejects_python_drift_before_stage_mutation(
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
    drift_python = tmp_path / "python-drift"
    for path in (fake_bin, queue_root, publisher_root, log_root):
        path.mkdir()
    drift_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    drift_python.chmod(0o755)
    (fake_bin / "dscl").write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    (fake_bin / "dscl").chmod(0o700)
    (fake_bin / "launchctl").write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 113; fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "launchctl").chmod(0o700)
    (fake_bin / "sysctl").write_text(
        "#!/bin/sh\nprintf '%s\\n' 'total = 0.00M  used = 0.00M  free = 0.00M'\n",
        encoding="utf-8",
    )
    (fake_bin / "sysctl").chmod(0o700)
    manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=queue_root,
        publisher_state_root=publisher_root,
        log_root=log_root,
        identity="synthetic-capacity:python-drift",
        python_executable=drift_python,
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PANTHEON_CAPACITY_GUARD_STATE_FILE": str(state_file),
            "PANTHEON_USER_HOME_DIR": str(fake_home),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest[
                "manifest_digest"
            ],
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

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert list(publisher_root.iterdir()) == []
    assert list(log_root.iterdir()) == []
    assert not mutation_log.exists()


def test_unknown_rss_or_swap_telemetry_is_no_go(tmp_path: Path, monkeypatch) -> None:
    """REG-PANTHEON-CAPACITY-UNKNOWN-METRICS-NO-GO-001。"""
    sample = _available_snapshot()
    sample.update({"rss_bytes": None, "rss_available": False, "rss_error": "ps_failed"})
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "NO-GO"
    assert "rss_telemetry_unknown" in result["reasons"]


def test_swap_telemetry_uses_primary_source_without_fallback() -> None:
    fallback_calls = 0

    def fallback() -> tuple[int | None, str | None]:
        nonlocal fallback_calls
        fallback_calls += 1
        return 17, None

    result = guard._swap_used_bytes(
        lambda _command: _completed(
            0,
            "total = 1024.00M  used = 12.50M  free = 1011.50M\n",
        ),
        fallback=fallback,
    )

    assert result == {
        "value": int(12.5 * guard.MIB),
        "available": True,
        "error": None,
    }
    assert fallback_calls == 0


def test_swap_telemetry_uses_native_fallback_after_primary_command_failure() -> None:
    result = guard._swap_used_bytes(
        lambda _command: _completed(1),
        fallback=lambda: (23 * guard.MIB, None),
    )

    assert result == {
        "value": 23 * guard.MIB,
        "available": True,
        "error": None,
    }


def test_swap_telemetry_is_no_go_when_primary_and_fallback_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    swap = guard._swap_used_bytes(
        lambda _command: _completed(1),
        fallback=lambda: (None, "sysctlbyname_failed:1"),
    )
    sample = _available_snapshot()
    sample.update(
        {
            "swap_used_bytes": swap["value"],
            "swap_available": swap["available"],
            "swap_error": swap["error"],
        }
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert swap == {
        "value": None,
        "available": False,
        "error": "swap_sources_failed:command:1;fallback:sysctlbyname_failed:1",
    }
    assert result["status"] == "NO-GO"
    assert result["reasons"] == ["swap_telemetry_unknown"]


def test_swap_telemetry_parse_error_fails_closed_without_fallback() -> None:
    fallback_calls = 0

    def fallback() -> tuple[int | None, str | None]:
        nonlocal fallback_calls
        fallback_calls += 1
        return 0, None

    result = guard._swap_used_bytes(
        lambda _command: _completed(0, "used = not-a-number\n"),
        fallback=fallback,
    )

    assert result == {
        "value": None,
        "available": False,
        "error": "swap_parse_failed",
    }
    assert fallback_calls == 0


@pytest.mark.parametrize(
    ("total", "used", "expected"),
    [
        (64 * guard.MIB, 8 * guard.MIB, (8 * guard.MIB, None)),
        (8 * guard.MIB, 64 * guard.MIB, (None, "sysctlbyname_invalid_usage")),
    ],
)
def test_darwin_native_swap_fallback_validates_usage_bounds(
    monkeypatch: pytest.MonkeyPatch,
    total: int,
    used: int,
    expected: tuple[int | None, str | None],
) -> None:
    class FakeSysctlByName:
        argtypes = None
        restype = None

        def __call__(self, _name, output, _size, _new, _new_size) -> int:
            output._obj.total = total
            output._obj.available = total - min(total, used)
            output._obj.used = used
            return 0

    class FakeLibc:
        sysctlbyname = FakeSysctlByName()

    monkeypatch.setattr(guard.sys, "platform", "darwin")
    monkeypatch.setattr(guard.ctypes, "CDLL", lambda *_args, **_kwargs: FakeLibc())

    assert guard._local_swap_used_bytes() == expected


def test_preflight_allows_formal_activation_only_service_without_pid_but_rejects_normal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REG-PANTHEON-CAPACITY-LOADED-INERT-NO-PID-001。"""
    identity = {"value": f"gate2-actor:{'a' * 40}:activation-only"}

    def exact_fixture(target: str) -> str:
        return ANONYMIZED_INERT_LAUNCHCTL_FIXTURE.replace("<target>", target, 1)

    launch_output = {"build": exact_fixture}
    monkeypatch.setattr(
        guard.formal_runtime,
        "validate_runtime_tick",
        lambda *_args, **_kwargs: {
            "status": "PASS",
            "identity": identity["value"],
            "config_version": "formal-runtime-v2-gate2",
        },
    )
    monkeypatch.setattr(
        guard,
        "_disk_sample",
        lambda _path: (200 * guard.GIB, 100 * guard.GIB),
    )

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[:2] == ["launchctl", "print"]:
            label = command[-1].rsplit("/", 1)[-1]
            if label == "com.pantheon.agy-content-publisher":
                return _completed(0, launch_output["build"](command[-1]))
            return _completed(113)
        if command == ["sysctl", "-n", "vm.swapusage"]:
            return _completed(0, "total = 0.00M  used = 0.00M  free = 0.00M\n")
        raise AssertionError(f"unexpected command: {command}")

    inert = guard.preflight(
        tmp_path,
        tmp_path / "publisher",
        tmp_path / "logs",
        runner=runner,
    )

    assert inert["status"] == "PASS"
    assert inert["rss_available"] is True
    assert inert["rss_identity"]["inert_labels"] == [
        {
            "label": "com.pantheon.agy-content-publisher",
            "topology": "loaded-but-inert",
        }
    ]

    invalid_outputs = {
        "duplicate_top_level": lambda target: exact_fixture(target).replace(
            "\tstate = not running\n", "\tstate = running\n\tstate = not running\n", 1
        ),
        "running": lambda target: exact_fixture(target).replace(
            "\tstate = not running\n", "\tstate = running\n", 1
        ),
        "waiting": lambda target: exact_fixture(target).replace(
            "\tstate = not running\n", "\tstate = waiting\n", 1
        ),
        "missing": lambda target: exact_fixture(target).replace(
            "\tstate = not running\n", "", 1
        ),
        "unbalanced": lambda target: exact_fixture(target).rsplit("}", 1)[0],
        "wrong_root": lambda _target: exact_fixture("garbage-root"),
        "prefix_spoof": lambda target: exact_fixture(f"spoof-{target}"),
        "suffix_spoof": lambda target: exact_fixture(f"{target}-spoof"),
        "leading_whitespace_root": lambda target: " " + exact_fixture(target),
        "trailing_whitespace_root": lambda target: exact_fixture(target).replace(
            f"{target} = {{\n", f"{target} = {{ \n", 1
        ),
        "other_label": lambda target: exact_fixture(
            f"{target.rsplit('/', 1)[0]}/com.pantheon.other"
        ),
        "multiple_roots": lambda target: exact_fixture(target) + exact_fixture(target),
        "garbage_prefix": lambda target: "garbage\n" + exact_fixture(target),
        "garbage_suffix": lambda target: exact_fixture(target) + "garbage\n",
    }
    for case, invalid_output in invalid_outputs.items():
        launch_output["build"] = invalid_output
        invalid = guard.preflight(
            tmp_path,
            tmp_path / "publisher",
            tmp_path / "logs",
            runner=runner,
        )

        assert invalid["status"] == "NO-GO", case
        assert invalid["rss_error"] == (
            "loaded_service_pid_missing:com.pantheon.agy-content-publisher"
        )

    identity["value"] = f"gate2-actor:{'a' * 40}:normal"
    launch_output["build"] = exact_fixture
    normal = guard.preflight(
        tmp_path,
        tmp_path / "publisher",
        tmp_path / "logs",
        runner=runner,
    )

    assert normal["status"] == "NO-GO"
    assert normal["rss_error"] == (
        "loaded_service_pid_missing:com.pantheon.agy-content-publisher"
    )
    assert "rss_telemetry_unknown" in normal["reasons"]


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
    monkeypatch,
) -> None:
    """REG-PANTHEON-CAPACITY-WRITE-CYCLES-001。"""
    monkeypatch.setattr(
        guard,
        "_swap_used_bytes",
        lambda: {"value": 0, "available": True, "error": None},
    )
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

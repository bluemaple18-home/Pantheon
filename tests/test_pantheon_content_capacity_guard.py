from __future__ import annotations

import hashlib
import json
import os
import fcntl
import plistlib
from contextlib import contextmanager
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import pantheon_content_capacity_guard as guard
from scripts import pantheon_content_runtime_manifest as runtime_manifest

_CANONICAL_PROCESS_BOUNDARY = guard.runtime_activation.run_process_boundary


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


def test_publisher_reset_snapshot_uses_top_level_launchctl_identity(tmp_path: Path) -> None:
    expected_path = (
        tmp_path
        / "Library"
        / "LaunchAgents"
        / "com.pantheon.agy-content-publisher.plist"
    )
    target = f"gui/{os.getuid()}/{expected_path.stem}"
    output = f"""{target} = {{
\tpath = {expected_path}
\tstate = not running

\tresource coalition = {{
\t\tstate = active
\t}}
}}
"""

    identity = guard._snapshot_launchctl_identity(output, expected_path=expected_path)

    assert identity == {
        "states": ["not running"],
        "paths": [str(expected_path)],
        "last_exit_codes": [],
    }


def _completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, "")


def _launchctl_loaded_identity(
    target: str,
    plist_path: Path,
    *,
    state: str = "waiting",
    runs: int = 1,
    exit_code: int | None = 0,
    pid: int | None = None,
) -> str:
    rows = [
        f"{target} = {{",
        f"\tpath = {plist_path}",
        f"\tstate = {state}",
        f"\truns = {runs}",
    ]
    if exit_code is not None:
        rows.append(f"\tlast exit code = {exit_code}")
    if pid is not None:
        rows.append(f"\tpid = {pid}")
    rows.append("}")
    return "\n".join(rows) + "\n"


def _available_snapshot(bytes_used: int = 100 * guard.MIB) -> dict[str, object]:
    return {
        "bytes": bytes_used,
        "file_count": 100,
        "disk_total_bytes": 200 * guard.GIB,
        "disk_free_bytes": 100 * guard.GIB,
        "admission_available_bytes": 100 * guard.GIB,
        "capacity_source": "test_important_usage",
        "capacity_available": True,
        "capacity_error": None,
        "rss_bytes": 0,
        "rss_available": True,
        "rss_error": None,
        "rss_identity": {"loaded_labels": [], "absent_labels": list(guard.SERVICE_LABELS)},
        "swap_used_bytes": 0,
        "swap_available": True,
        "swap_error": None,
    }


def _host_capacity(total_gib: int, available_gib: int) -> dict[str, object]:
    return {
        "disk_total_bytes": total_gib * guard.GIB,
        "disk_free_bytes": available_gib * guard.GIB,
        "admission_available_bytes": available_gib * guard.GIB,
        "capacity_source": "test_important_usage",
        "capacity_available": True,
        "capacity_error": None,
    }


def _passing_preflight_receipt(capacity_path: str = "/") -> dict[str, object]:
    total = 200 * guard.GIB
    admission = 100 * guard.GIB
    projected = guard.DEFAULT_PROJECTED_BYTES
    reserve = max(guard.HOST_RESERVE_MIN_BYTES, (total + 9) // 10)
    return {
        "status": "PASS",
        "reasons": [],
        "capacity_available": True,
        "capacity_error": None,
        "capacity_source": "macos_foundation_important_usage",
        "disk_total_bytes": total,
        "disk_free_bytes": 80 * guard.GIB,
        "raw_disk_total_bytes": total,
        "raw_disk_free_bytes": 80 * guard.GIB,
        "admission_available_bytes": admission,
        "projected_bytes": projected,
        "reserve_bytes": reserve,
        "projected_admission_available_bytes": admission - projected,
        "capacity_path": capacity_path,
    }


def _seed_pending_capacity_recovery(
    tmp_path: Path,
    *,
    owned_labels: tuple[str, ...],
) -> tuple[list[Path], Path, dict[str, Path], dict[str, object]]:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    launch_agents = tmp_path / "LaunchAgents"
    launch_agents.mkdir()
    plists = {
        label: launch_agents / f"{label}.plist" for label in guard.SERVICE_LABELS
    }
    for path in plists.values():
        path.write_text("synthetic\n", encoding="utf-8")
        path.chmod(0o600)
    manifest_file = tmp_path / "runtime-manifest.json"
    manifest_file.write_text("{}\n", encoding="utf-8")
    manifest_file.chmod(0o600)
    barrier = tmp_path / "activation.barrier"
    barrier.write_text("synthetic barrier\n", encoding="utf-8")
    barrier.chmod(0o600)
    context: dict[str, object] = {
        "authorized": True,
        "blocker": None,
        "manifest_digest": "a" * 64,
        "runtime_identity_digest": "b" * 64,
        "generation": "capacity-resume-test",
        "barrier_path": str(barrier),
        "manifest_file": guard._file_identity(manifest_file),
        "barrier": guard._file_identity(barrier),
        "owned_roots": {
            "actor_root": str(tmp_path),
            "queue_root": str(roots[0]),
            "publisher_state_root": str(roots[1]),
            "log_root": str(roots[2]),
        },
        "restart_projected_bytes": guard.RECOVERY_PROJECTED_RESTART_BYTES,
        "plists": {
            label: guard._file_identity(path)
            for label, path in plists.items()
        },
    }
    incident = {
        "schema_version": 2,
        "incident_id": "capacity-seeded-test",
        "status": "RECOVERY_PENDING",
        "started_epoch": 1000,
        "updated_epoch": 1900,
        "trigger_reasons": ["admission_available_below_stop_floor"],
        "automatic_recovery_authorized": True,
        "authorization_blocker": None,
        "manifest_digest": context["manifest_digest"],
        "runtime_identity_digest": context["runtime_identity_digest"],
        "generation": context["generation"],
        "barrier_path": context["barrier_path"],
        "manifest_file": context["manifest_file"],
        "barrier": context["barrier"],
        "owned_roots": context["owned_roots"],
        "restart_projected_bytes": context["restart_projected_bytes"],
        "plists": context["plists"],
        "pre_stop_services": {},
        "disabled_labels_before_stop": [],
        "stop_targets": list(owned_labels),
        "owned_labels": list(owned_labels),
        "stopped_by_guard": list(owned_labels),
        "stopped_services": list(owned_labels),
        "stop_verification": {
            label: {"absent": True} for label in owned_labels
        },
        "healthy_samples": 3,
        "last_healthy_epoch": 1900,
        "attempts_started": 0,
        "max_attempts": guard.MAX_AUTOMATIC_RECOVERY_ATTEMPTS,
        "attempted_labels": [],
        "started_labels": [],
        "rollback": None,
        "restart_measurement": None,
    }
    state = roots[0] / "state.json"
    state.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "status": "RECOVERY_PENDING",
                "sampled_epoch": 1900,
                "growth_bytes_per_hour": 0,
                "high_growth_streak": 0,
                "growth_streak": 0,
                "memory_streak": 0,
                "reasons": [],
                "telemetry_gaps": [],
                "recovery_incident": incident,
                **_available_snapshot(),
            }
        ),
        encoding="utf-8",
    )
    state.chmod(0o600)
    return roots, state, plists, context


def _make_recovery_context(
    tmp_path: Path,
    roots: list[Path],
    *,
    generation: str,
) -> tuple[dict[str, Path], dict[str, object]]:
    launch_agents = tmp_path / f"LaunchAgents-{generation}"
    launch_agents.mkdir()
    plists = {
        label: launch_agents / f"{label}.plist" for label in guard.SERVICE_LABELS
    }
    for path in plists.values():
        path.write_text("synthetic\n", encoding="utf-8")
        path.chmod(0o600)
    manifest_file = tmp_path / f"runtime-manifest-{generation}.json"
    manifest_file.write_text("{}\n", encoding="utf-8")
    manifest_file.chmod(0o600)
    barrier = tmp_path / f"activation-{generation}.barrier"
    barrier.write_text("synthetic barrier\n", encoding="utf-8")
    barrier.chmod(0o600)
    context: dict[str, object] = {
        "authorized": True,
        "blocker": None,
        "manifest_digest": "a" * 64,
        "runtime_identity_digest": "b" * 64,
        "generation": generation,
        "barrier_path": str(barrier),
        "manifest_file": guard._file_identity(manifest_file),
        "barrier": guard._file_identity(barrier),
        "owned_roots": {
            "actor_root": str(tmp_path),
            "queue_root": str(roots[0]),
            "publisher_state_root": str(roots[1]),
            "log_root": str(roots[2]),
        },
        "restart_projected_bytes": guard.RECOVERY_PROJECTED_RESTART_BYTES,
        "plists": {
            label: guard._file_identity(path)
            for label, path in plists.items()
        },
    }
    return plists, context


@pytest.fixture(autouse=True)
def _stable_canonical_capacity_sensor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        guard,
        "_host_capacity_sample",
        lambda _path: {
            **_host_capacity(200, 100),
            "capacity_source": "macos_foundation_important_usage",
        },
    )


@pytest.fixture(autouse=True)
def _quiescent_canonical_process_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard 測試只驗 policy/orchestration；程序樹故障矩陣由 activation 測試負責。"""

    def boundary(**kwargs: object) -> dict[str, object]:
        mode = kwargs.get("mode")
        journal = str(kwargs.get("journal_path"))
        # Policy fixture 也須交付正式持久 journal；不能讓跨 action 測試依賴不存在的檔案。
        path = Path(journal)
        record = guard.runtime_activation._load_boundary_record(path)
        record.update(active=[], resample_required=False, status="DRAINED" if mode == "drain" else "OBSERVED")
        record["seen_labels"] = list(dict.fromkeys([*record["seen_labels"], *kwargs.get("arguments", [])]))
        guard.runtime_activation._write_private_json(path, record)
        if mode == "drain":
            return {"status": "DRAINED", "active": [], "journal": journal}
        if mode == "observe":
            return {
                "status": "OBSERVED",
                "active": [],
                "resample_required": False,
                "seen_labels": list(kwargs.get("arguments", [])),
                "journal": journal,
            }
        raise AssertionError(f"unexpected process-boundary mode: {mode}")

    monkeypatch.setattr(guard.runtime_activation, "run_process_boundary", boundary)


def _force_safe_child_disk_capacity(env: dict[str, str], tmp_path: Path) -> None:
    """讓 installer subprocess 的容量測試不受開發機當下剩餘磁碟影響。"""
    support_dir = tmp_path / "python-test-support"
    support_dir.mkdir(exist_ok=True)
    (support_dir / "sitecustomize.py").write_text(
        "import os\n"
        "import json\n"
        "import subprocess\n"
        "_real_statvfs = os.statvfs\n"
        "def _safe_statvfs(path):\n"
        "    sample = _real_statvfs(path)\n"
        "    values = list(sample)\n"
        "    minimum_available = max(1, (int(sample.f_blocks) + 4) // 5)\n"
        "    if int(sample.f_bavail) >= minimum_available:\n"
        "        return sample\n"
        "    values[3] = max(int(sample.f_bfree), minimum_available)\n"
        "    values[4] = minimum_available\n"
        "    return os.statvfs_result(values)\n"
        "os.statvfs = _safe_statvfs\n"
        "_real_run = subprocess.run\n"
        "def _safe_run(command, *args, **kwargs):\n"
        "    if isinstance(command, list) and command[:3] == ['/usr/bin/osascript', '-l', 'JavaScript']:\n"
        "        disk = os.statvfs(command[-1])\n"
        "        total = int(disk.f_blocks) * int(disk.f_frsize)\n"
        "        physical = int(disk.f_bavail) * int(disk.f_frsize)\n"
        "        admission = min(total, max(physical, 100 * 1024**3))\n"
        "        payload = json.dumps({'total_bytes': total, 'physical_available_bytes': physical, 'admission_available_bytes': admission})\n"
        "        return subprocess.CompletedProcess(command, 0, payload, '')\n"
        "    return _real_run(command, *args, **kwargs)\n"
        "subprocess.run = _safe_run\n",
        encoding="utf-8",
    )
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{support_dir}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(support_dir)
    )


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
    monkeypatch.setattr(guard, "_host_capacity_sample", lambda _path: _host_capacity(200, 19))
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
    assert result["reasons"] == ["projected_admission_below_reserve"]


def test_preflight_accepts_free_space_above_ten_percent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 25 * guard.GIB))
    monkeypatch.setattr(guard, "_host_capacity_sample", lambda _path: _host_capacity(200, 25))
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
        "_host_capacity_sample",
        lambda _path: {
            **_host_capacity(200, 20),
            "disk_free_bytes": 20 * guard.GIB + guard.DEFAULT_PROJECTED_BYTES,
            "admission_available_bytes": 20 * guard.GIB + guard.DEFAULT_PROJECTED_BYTES,
        },
    )
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


def test_preflight_uses_important_usage_and_does_not_deny_on_unknown_swap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """raw 偏低與 swap 無法觀測，不得取代 projected admission 判斷。"""
    sample = _available_snapshot()
    sample.update(
        {
            "disk_total_bytes": 200 * guard.GIB,
            "disk_free_bytes": 19 * guard.GIB,
            "capacity_source": "macos_foundation_important_usage",
            "admission_available_bytes": 30 * guard.GIB,
            "capacity_available": True,
            "swap_used_bytes": None,
            "swap_available": False,
            "swap_error": "sandbox_denied",
        }
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)

    result = guard.preflight(
        tmp_path,
        tmp_path / "publisher",
        tmp_path / "logs",
    )

    assert result["status"] == "PASS"
    assert result["reasons"] == []
    assert result["projected_admission_available_bytes"] == 29 * guard.GIB
    assert result["telemetry_gaps"] == ["swap_telemetry_unknown"]


def test_host_capacity_sample_loads_canonical_ai_core_sensor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sensor = tmp_path / "ai-core/scripts/host_capacity_sensor.py"
    sensor.parent.mkdir(parents=True)
    sensor.write_text(
        "from types import SimpleNamespace\n"
        "def measure_host_capacity(path):\n"
        "    return SimpleNamespace(total_bytes=200, physical_available_bytes=19, "
        "admission_available_bytes=30, source='macos_foundation_important_usage')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(guard, "CANONICAL_HOST_CAPACITY_SENSOR", sensor)

    assert _REAL_HOST_CAPACITY_SAMPLE(tmp_path) == {
        "disk_total_bytes": 200,
        "disk_free_bytes": 19,
        "admission_available_bytes": 30,
        "capacity_source": "macos_foundation_important_usage",
        "capacity_available": True,
        "capacity_error": None,
    }


def test_preflight_fails_closed_when_canonical_capacity_sensor_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        guard,
        "_host_capacity_sample",
        lambda _path: (_ for _ in ()).throw(RuntimeError("sensor unavailable")),
    )
    monkeypatch.setattr(guard, "_disk_sample", lambda _path: (200 * guard.GIB, 100 * guard.GIB))
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
    assert result["reasons"] == ["capacity_telemetry_unknown"]
    assert result["capacity_available"] is False


def test_preflight_reserve_rounds_ten_percent_up(tmp_path: Path, monkeypatch) -> None:
    sample = _available_snapshot()
    total_bytes = 300 * guard.GIB + 1
    sample.update(
        {
            "disk_total_bytes": total_bytes,
            "admission_available_bytes": 31 * guard.GIB,
        }
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)

    result = guard.preflight(
        tmp_path,
        tmp_path / "publisher",
        tmp_path / "logs",
    )

    assert result["reserve_bytes"] == (total_bytes + 9) // 10


@pytest.mark.parametrize(
    "mutation",
    (
        lambda receipt: receipt.clear(),
        lambda receipt: receipt.update({"capacity_source": "raw_statvfs"}),
        lambda receipt: receipt.update({"capacity_source": "shutil.disk_usage"}),
        lambda receipt: receipt.update({"raw_disk_total_bytes": 1}),
        lambda receipt: receipt.update({"disk_free_bytes": 101 * guard.GIB}),
        lambda receipt: receipt.update({"projected_bytes": 0}),
        lambda receipt: receipt.update({"projected_admission_available_bytes": 1}),
        lambda receipt: receipt.update({"reserve_bytes": 1}),
        lambda receipt: receipt.pop("raw_disk_free_bytes"),
    ),
)
def test_preactivation_rejects_incomplete_or_tampered_capacity_receipt(mutation) -> None:
    receipt = _passing_preflight_receipt()
    mutation(receipt)

    with pytest.raises(runtime_manifest.RuntimeManifestError, match="receipt mismatch"):
        guard._validate_capacity_admission_receipt(receipt)


def test_check_over_budget_stops_only_registered_services(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "queue"
    publisher = tmp_path / "publisher"
    logs = tmp_path / "logs"
    for root in (queue, publisher, logs):
        root.mkdir()
    roots = [queue, publisher, logs]
    plists, context = _make_recovery_context(
        tmp_path,
        roots,
        generation="over-budget-stop",
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    state = queue / "capacity-state.json"
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_roots: {**_available_snapshot(guard.MAX_BYTES + 1), "file_count": 1},
    )
    commands: list[list[str]] = []
    loaded = set(guard.SERVICE_LABELS)

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        label = command[-1].split("/")[-1]
        if action == "bootout":
            loaded.discard(label)
            return _completed()
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(queue, publisher, logs, state, now=1000, stop_runner=runner)

    assert result["status"] == "STOPPED"
    assert result["reasons"] == ["project_bytes_over_budget"]
    assert [
        command[-1].split("/")[-1] for command in commands if command[1] == "bootout"
    ] == list(guard.SERVICE_LABELS)
    assert json.loads(state.read_text())["status"] == "STOPPED"


def test_plist_replacement_between_bootouts_blocks_second_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = tmp_path / "queue"
    publisher = tmp_path / "publisher"
    logs = tmp_path / "logs"
    for root in (queue, publisher, logs):
        root.mkdir()
    roots = [queue, publisher, logs]
    plists, context = _make_recovery_context(
        tmp_path,
        roots,
        generation="bootout-authority-drift",
    )
    labels = guard.SERVICE_LABELS[:2]
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_roots: {**_available_snapshot(guard.MAX_BYTES + 1), "file_count": 1},
    )
    loaded = set(labels)
    bootouts: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        label = command[-1].split("/")[-1]
        if action == "bootout":
            bootouts.append(label)
            loaded.discard(label)
            if label == labels[0]:
                replacement = plists[labels[1]].with_suffix(".replacement")
                replacement.write_text("replaced bytes\n", encoding="utf-8")
                replacement.chmod(0o600)
                os.replace(replacement, plists[labels[1]])
            return _completed()
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(
        queue,
        publisher,
        logs,
        queue / "capacity-state.json",
        now=1000,
        stop_runner=runner,
    )

    assert result["status"] == "OPERATOR_REQUIRED"
    assert bootouts == [labels[0]]
    assert labels[1] in loaded
    assert result["recovery_incident"]["status"] != "STOPPED"


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


def test_capacity_guard_persists_owned_stop_before_mutation_and_recovers_after_four_samples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    state = roots[0] / "state.json"
    launch_agents = tmp_path / "LaunchAgents"
    launch_agents.mkdir()
    plists = {
        label: launch_agents / f"{label}.plist" for label in guard.SERVICE_LABELS
    }
    for path in plists.values():
        path.write_text("synthetic\n", encoding="utf-8")
        path.chmod(0o600)
    runtime_receipt = {
        "status": "PASS",
        "manifest_digest": "a" * 64,
        "runtime_identity_digest": "b" * 64,
        "generation": "capacity-resume-test",
        "config_version": "formal-runtime-v3-model-route-v1",
    }
    manifest_file = tmp_path / "runtime-manifest.json"
    manifest_file.write_text("{}\n", encoding="utf-8")
    manifest_file.chmod(0o600)
    barrier = tmp_path / "activation.barrier"
    barrier.write_text("synthetic barrier\n", encoding="utf-8")
    barrier.chmod(0o600)
    recovery_context = {
        "authorized": True,
        "blocker": None,
        "manifest_digest": runtime_receipt["manifest_digest"],
        "runtime_identity_digest": runtime_receipt["runtime_identity_digest"],
        "generation": runtime_receipt["generation"],
        "barrier_path": str(barrier),
        "manifest_file": guard._file_identity(manifest_file),
        "barrier": guard._file_identity(barrier),
        "owned_roots": {
            "actor_root": str(tmp_path),
            "queue_root": str(roots[0]),
            "publisher_state_root": str(roots[1]),
            "log_root": str(roots[2]),
        },
        "restart_projected_bytes": guard.RECOVERY_PROJECTED_RESTART_BYTES,
        "plists": {
            label: guard._file_identity(path)
            for label, path in plists.items()
        },
    }
    sample = _available_snapshot()
    sample["disk_free_bytes"] = 19 * guard.GIB
    sample["admission_available_bytes"] = 19 * guard.GIB
    loaded = set(guard.SERVICE_LABELS)
    runs_by_label = {label: 1 for label in guard.SERVICE_LABELS}
    commands: list[list[str]] = []
    state_seen_before_first_bootout: list[dict[str, object]] = []
    state_seen_before_first_bootstrap: list[dict[str, object]] = []

    monkeypatch.setattr(
        guard.formal_runtime,
        "validate_runtime_tick",
        lambda *_args, **_kwargs: dict(runtime_receipt),
    )
    monkeypatch.setattr(
        guard,
        "_normal_scheduled_service_labels",
        lambda _receipt: frozenset(guard.SERVICE_LABELS),
    )
    monkeypatch.setattr(
        guard,
        "_activation_only_service_labels",
        lambda _receipt: frozenset(),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: dict(sample))
    monkeypatch.setattr(
        guard,
        "_recovery_context",
        lambda _receipt: dict(recovery_context),
        raising=False,
    )

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[1] == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if command[1] == "bootout":
            if not state_seen_before_first_bootout:
                state_seen_before_first_bootout.append(json.loads(state.read_text()))
            loaded.discard(command[-1].rsplit("/", 1)[-1])
            return _completed()
        if command[1] == "bootstrap":
            if not state_seen_before_first_bootstrap:
                state_seen_before_first_bootstrap.append(json.loads(state.read_text()))
            label = Path(command[-1]).stem
            loaded.add(label)
            runs_by_label[label] = 1
            return _completed()
        assert command[1] == "print", command
        label = command[-1].rsplit("/", 1)[-1]
        if label not in loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(
                command[-1],
                plists[label],
                runs=runs_by_label[label],
            ),
        )

    stopped = guard.check_once(*roots, state, now=1000, stop_runner=runner)

    assert stopped["status"] == "STOPPED"
    assert stopped["recovery_incident"]["status"] == "STOPPED"
    assert stopped["recovery_incident"]["owned_labels"] == list(guard.SERVICE_LABELS)
    assert state_seen_before_first_bootout[0]["status"] == "STOPPING"
    assert state_seen_before_first_bootout[0]["recovery_incident"]["status"] == "STOPPING"

    sample["disk_free_bytes"] = 100 * guard.GIB
    sample["admission_available_bytes"] = 100 * guard.GIB
    for index in range(1, 4):
        pending = guard.check_once(
            *roots,
            state,
            now=1000 + index * 300,
            stop_runner=runner,
        )
        assert pending["status"] == "RECOVERY_PENDING"
        assert pending["recovery_incident"]["healthy_samples"] == index
        assert loaded == set()

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert started["status"] == "RECOVERY_VERIFYING"
    assert started["recovery_incident"]["status"] == "RECOVERY_VERIFYING"
    assert started["recovery_incident"]["attempts_started"] == 1
    assert loaded == set(guard.SERVICE_LABELS)
    runs_by_label.update({label: 2 for label in guard.SERVICE_LABELS})
    recovered = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert recovered["status"] == "PASS"
    assert recovered["recovery_incident"]["status"] == "RECOVERED"
    assert state_seen_before_first_bootstrap[0]["status"] == "RECOVERY_IN_PROGRESS"
    assert (
        state_seen_before_first_bootstrap[0]["recovery_incident"]["attempts_started"]
        == 1
    )
    assert [command[1] for command in commands].count("bootstrap") == len(
        guard.SERVICE_LABELS
    )
    measurement = recovered["recovery_incident"]["restart_measurement"]
    assert {
        key: measurement[key]
        for key in (
            "pre_admission_available_bytes",
            "post_admission_available_bytes",
            "admission_drop_bytes",
            "project_growth_bytes",
            "measured_restart_bytes",
            "projected_restart_bytes",
            "pre_rss_bytes",
            "post_rss_bytes",
            "rss_growth_bytes",
            "pre_swap_used_bytes",
            "post_swap_used_bytes",
            "swap_growth_bytes",
            "stop_floor_bytes",
        )
    } == {
        "pre_admission_available_bytes": 100 * guard.GIB,
        "post_admission_available_bytes": 100 * guard.GIB,
        "admission_drop_bytes": 0,
        "project_growth_bytes": 0,
        "measured_restart_bytes": 0,
        "projected_restart_bytes": guard.RECOVERY_PROJECTED_RESTART_BYTES,
        "pre_rss_bytes": 0,
        "post_rss_bytes": 0,
        "rss_growth_bytes": 0,
        "pre_swap_used_bytes": 0,
        "post_swap_used_bytes": 0,
        "swap_growth_bytes": 0,
        "stop_floor_bytes": 20 * guard.GIB,
    }
    assert measurement["sample_count"] == guard.RECOVERY_POST_RESUME_HEALTHY_SAMPLES
    assert measurement["rss_growth_limit_bytes"] == guard.RECOVERY_RSS_GROWTH_LIMIT_BYTES
    assert measurement["swap_growth_limit_bytes"] == guard.RECOVERY_SWAP_GROWTH_LIMIT_BYTES
    assert len(measurement["samples"]) == guard.RECOVERY_POST_RESUME_HEALTHY_SAMPLES
    bootstrap_count = [command[1] for command in commands].count("bootstrap")
    retained = guard.check_once(*roots, state, now=2800, stop_runner=runner)
    assert retained["status"] == "PASS"
    assert retained["recovery_incident"]["status"] == "RECOVERED"
    assert [command[1] for command in commands].count("bootstrap") == bootstrap_count


def test_capacity_recovery_respects_manual_disable_before_bootstrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert command[1] == "print-disabled"
        return _completed(
            0,
            f'disabled services = {{\n\t"{label}" => true\n}}\n',
        )

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "owned_service_manually_disabled"
    )
    assert result["recovery_incident"]["disabled_labels_at_recovery"] == [label]
    assert all(command[1] != "bootstrap" for command in commands)


def test_capacity_stop_owns_only_loaded_services_not_already_disabled_or_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    state = roots[0] / "state.json"
    launch_agents = tmp_path / "LaunchAgents"
    launch_agents.mkdir()
    plists = {
        label: launch_agents / f"{label}.plist" for label in guard.SERVICE_LABELS
    }
    for path in plists.values():
        path.write_text("synthetic\n", encoding="utf-8")
        path.chmod(0o600)
    manifest_file = tmp_path / "runtime-manifest.json"
    manifest_file.write_text("{}\n", encoding="utf-8")
    manifest_file.chmod(0o600)
    barrier = tmp_path / "activation.barrier"
    barrier.write_text("synthetic barrier\n", encoding="utf-8")
    barrier.chmod(0o600)
    disabled_label = guard.SERVICE_LABELS[0]
    absent_label = guard.SERVICE_LABELS[1]
    loaded = set(guard.SERVICE_LABELS) - {absent_label}
    context = {
        "authorized": True,
        "blocker": None,
        "manifest_digest": "a" * 64,
        "runtime_identity_digest": "b" * 64,
        "generation": "capacity-stop-ownership-test",
        "barrier_path": str(barrier),
        "manifest_file": guard._file_identity(manifest_file),
        "barrier": guard._file_identity(barrier),
        "owned_roots": {
            "actor_root": str(tmp_path),
            "queue_root": str(roots[0]),
            "publisher_state_root": str(roots[1]),
            "log_root": str(roots[2]),
        },
        "restart_projected_bytes": guard.RECOVERY_PROJECTED_RESTART_BYTES,
        "plists": {
            label: guard._file_identity(path)
            for label, path in plists.items()
        },
    }
    sample = _available_snapshot()
    sample["disk_free_bytes"] = 19 * guard.GIB
    sample["admission_available_bytes"] = 19 * guard.GIB
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: dict(sample))
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        action = command[1]
        if action == "print-disabled":
            return _completed(
                0,
                f'disabled services = {{\n\t"{disabled_label}" => true\n}}\n',
            )
        if action == "bootout":
            loaded.discard(command[-1].rsplit("/", 1)[-1])
            return _completed()
        assert action == "print", command
        label = command[-1].rsplit("/", 1)[-1]
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, state, now=1000, stop_runner=runner)

    incident = result["recovery_incident"]
    assert result["status"] == "STOPPED"
    assert set(incident["pre_stop_loaded_labels"]) == set(guard.SERVICE_LABELS) - {
        absent_label
    }
    assert set(incident["owned_labels"]) == set(guard.SERVICE_LABELS) - {
        disabled_label,
        absent_label,
    }
    assert incident["disabled_labels_before_stop"] == [disabled_label]
    assert incident["pre_stop_services"][absent_label]["topology"] == "ABSENT"
    assert [
        command[-1].rsplit("/", 1)[-1]
        for command in commands
        if command[1] == "bootout"
    ] == [
        label
        for label in guard.SERVICE_LABELS
        if label not in {disabled_label, absent_label}
    ]


def test_malformed_capacity_state_is_preserved_and_blocks_all_launchctl_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    state = roots[0] / "state.json"
    original = b'{"status":"RECOVERY_PENDING"'
    state.write_bytes(original)
    state.chmod(0o600)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: _available_snapshot(guard.MAX_BYTES + 1),
    )
    calls: list[list[str]] = []

    def forbidden(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        raise AssertionError("malformed state 不得觸發 launchctl")

    result = guard.check_once(*roots, state, now=1000, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"].startswith("capacity_state_malformed:")
    evidence = Path(incident["invalid_state_evidence"])
    assert evidence.read_bytes() == original
    assert json.loads(state.read_text())["status"] == "OPERATOR_REQUIRED"
    assert calls == []


@pytest.mark.parametrize("sampled_epoch", ["broken", 5000])
def test_invalid_capacity_state_sampled_epoch_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sampled_epoch: object,
) -> None:
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    payload = json.loads(state.read_text())
    payload["sampled_epoch"] = sampled_epoch
    state.write_text(json.dumps(payload), encoding="utf-8")
    state.chmod(0o600)
    original = state.read_bytes()
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    calls: list[list[str]] = []

    def forbidden(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        raise AssertionError("invalid sampled_epoch 不得觸發 launchctl mutation")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "capacity_state_sampled_epoch_invalid"
    evidence = Path(incident["invalid_state_evidence"])
    assert evidence.read_bytes() == original
    assert calls == []


def test_capacity_state_status_mismatch_fails_closed_before_unhealthy_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, _context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    payload = json.loads(state.read_text())
    payload["status"] = "PASS"
    state.write_text(json.dumps(payload), encoding="utf-8")
    state.chmod(0o600)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: _available_snapshot(guard.MAX_BYTES + 1),
    )

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("status mismatch 不得觸發 launchctl")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "capacity_state_status_mismatch"
    )


def test_operator_required_remains_terminal_even_when_capacity_is_unhealthy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, _context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    payload = json.loads(state.read_text())
    payload["status"] = "OPERATOR_REQUIRED"
    payload["recovery_incident"]["status"] = "OPERATOR_REQUIRED"
    payload["recovery_incident"]["automatic_recovery_authorized"] = False
    payload["recovery_incident"]["authorization_blocker"] = "manual_handoff"
    state.write_text(json.dumps(payload), encoding="utf-8")
    state.chmod(0o600)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: _available_snapshot(guard.MAX_BYTES + 1),
    )

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("operator-owned state 不得再次 mutation")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["recovery_incident"]["authorization_blocker"] == "manual_handoff"


def test_unknown_recovery_incident_status_fails_closed_before_launchctl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, _context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    payload = json.loads(state.read_text())
    payload["recovery_incident"]["status"] = "UNKNOWN_TRANSITION"
    state.write_text(json.dumps(payload), encoding="utf-8")
    state.chmod(0o600)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: _available_snapshot(guard.MAX_BYTES + 1),
    )

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("unknown incident status 不得觸發 launchctl")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "capacity_recovery_incident_unknown_status"
    )


def test_unreadable_capacity_state_path_stays_unmodified_and_unpersisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    state = roots[0] / "state.json"
    state.mkdir()
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: _available_snapshot(guard.MAX_BYTES + 1),
    )

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("unreadable state 不得觸發 launchctl")

    result = guard.check_once(*roots, state, now=1000, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["state_persisted"] is False
    assert result["recovery_incident"]["authorization_blocker"].startswith(
        "capacity_state_unreadable:"
    )
    assert state.is_dir()


def test_existing_shared_runtime_lease_blocks_recovery_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    commands: list[list[str]] = []

    def forbidden(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        raise AssertionError("shared lease contention 不得觸發 launchctl")

    with runtime_manifest.runtime_work_lease(roots[1]):
        with pytest.raises(runtime_manifest.RuntimeManifestError, match="cannot upgrade"):
            guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert commands == []
    persisted = json.loads(state.read_text())
    assert persisted["status"] == "RECOVERY_PENDING"
    assert persisted["recovery_incident"]["healthy_samples"] == 4


def test_second_capacity_guard_cannot_enter_while_state_writer_lock_is_held(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    state = roots[0] / "state.json"
    lock_path = state.with_name(f".{state.name}.lock")
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: pytest.fail("第二個 guard 不得開始 sampling"),
    )
    try:
        with pytest.raises(runtime_manifest.RuntimeWorkBusy, match="state writer is busy"):
            guard.check_once(*roots, state, now=1000)
    finally:
        os.close(descriptor)


def test_parent_directory_fsync_failure_stops_before_first_bootout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    plists, context = _make_recovery_context(
        tmp_path,
        roots,
        generation="directory-fsync-failure",
    )
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: _available_snapshot(guard.MAX_BYTES + 1),
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    monkeypatch.setattr(
        guard,
        "_fsync_directory",
        lambda _path: (_ for _ in ()).throw(OSError("synthetic directory fsync")),
    )
    loaded = set(guard.SERVICE_LABELS)
    mutations: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action in {"bootout", "bootstrap"}:
            mutations.append(command)
            return _completed()
        assert action == "print", command
        label = command[-1].rsplit("/", 1)[-1]
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    with pytest.raises(OSError, match="synthetic directory fsync"):
        guard.check_once(*roots, roots[0] / "state.json", now=1000, stop_runner=runner)

    assert mutations == []


def test_same_path_plist_replacement_blocks_before_bootstrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    replacement = plists[label].with_suffix(".replacement")
    replacement.write_bytes(plists[label].read_bytes())
    replacement.chmod(0o600)
    os.replace(replacement, plists[label])
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    commands: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[1] == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        assert command[1] == "print", command
        return _completed(113)

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "recovery_plist_identity_drift"
    )
    assert all(command[1] != "bootstrap" for command in commands)


def test_same_path_barrier_replacement_is_context_drift_before_launchctl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    barrier_path = Path(str(context["barrier_path"]))
    replacement = barrier_path.with_suffix(".replacement")
    replacement.write_bytes(barrier_path.read_bytes())
    replacement.chmod(0o600)
    os.replace(replacement, barrier_path)
    current_context = dict(context)
    current_context["barrier"] = guard._file_identity(barrier_path)
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(
        guard,
        "_recovery_context",
        lambda _receipt: dict(current_context),
    )

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("barrier drift 不得觸發 launchctl")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "recovery_context_drift:barrier"
    )


def test_delayed_service_crash_inside_stabilization_window_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    service = {"state": "spawn scheduled", "runs": 1, "exit_code": 75}

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(
                command[-1],
                plists[label],
                state=str(service["state"]),
                runs=int(service["runs"]),
                exit_code=int(service["exit_code"]),
            ),
        )

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"

    service.update(state="not running", runs=2, exit_code=78)
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "resume_execution_failed"
    assert incident["recovery_failure"] == "resume_execution_failed"
    assert incident["execution_verification"]["services"][label]["reason"] == (
        "service_exit_nonzero:78"
    )
    assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert incident["rollback"]["launchd_absent"] is True
    assert loaded is False


def test_capacity_recovery_no_run_timeout_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(
                command[-1],
                plists[label],
                state="waiting",
                runs=1,
                exit_code=0,
            ),
        )

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"

    result = guard.check_once(
        *roots,
        state,
        now=2200 + guard.RECOVERY_EXECUTION_TIMEOUT_SECONDS + 1,
        stop_runner=runner,
    )

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "resume_execution_timeout"
    assert incident["recovery_failure"] == "resume_execution_timeout"
    assert incident["execution_verification"]["services"][label]["reason"] == (
        "successful_terminal_run_not_observed"
    )
    assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert incident["rollback"]["launchd_absent"] is True
    assert loaded is False


def test_busy_work_persists_stop_intent_then_stops_after_quiescence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, seeded_state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,),
    )
    seeded_state.unlink()
    state = roots[0] / "capacity-guard-state.json"
    sample = _available_snapshot()
    sample["admission_available_bytes"] = 19 * guard.GIB
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: dict(sample))
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    monkeypatch.setattr(
        guard.formal_runtime, "validate_runtime_tick",
        lambda *_args, **_kwargs: {"status": "PASS"},
    )
    monkeypatch.setattr(
        guard, "_normal_scheduled_service_labels",
        lambda _receipt: frozenset(guard.SERVICE_LABELS),
    )
    loaded = True
    bootouts: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootout":
            bootouts.append(command)
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded or not command[-1].endswith(label):
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    lock_path = roots[1] / "runtime-work.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    monkeypatch.setattr(guard, "RECOVERY_SHUTDOWN_TIMEOUT_SECONDS", 0)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        pending = guard.check_once(*roots, state, now=1000, stop_runner=runner)
    finally:
        os.close(descriptor)
    assert pending["status"] == "STOPPING"
    assert pending["recovery_incident"]["stop_deferred_for_work"] is True
    assert json.loads(state.read_text())["status"] == "STOPPING"
    assert bootouts == []
    pending_payload = json.loads(state.read_text())
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(roots[0]))
    monkeypatch.setenv("PANTHEON_RUNTIME_SERVICE_LABEL", label)
    with pytest.raises(runtime_manifest.RuntimeWorkBusy, match="capacity stop is unresolved"):
        with runtime_manifest.runtime_work_lease(roots[1]):
            pytest.fail("待停機時不得啟動新工作")
    monkeypatch.delenv("PANTHEON_FORMAL_RUNTIME")

    monkeypatch.setattr(guard, "RECOVERY_SHUTDOWN_TIMEOUT_SECONDS", 30.0)
    real_stop = guard.runtime_activation.stop_capacity_services

    def interrupt_before_effect(*_args, **_kwargs):
        raise KeyboardInterrupt("simulated crash before canonical action")

    monkeypatch.setattr(
        guard.runtime_activation, "stop_capacity_services", interrupt_before_effect
    )
    with pytest.raises(KeyboardInterrupt, match="simulated crash"):
        guard.check_once(*roots, state, now=1300, stop_runner=runner)
    persisted = json.loads(state.read_text())
    assert persisted["status"] == "STOPPING"
    assert persisted["recovery_incident"]["stop_deferred_for_work"] is True
    assert bootouts == []
    monkeypatch.setattr(guard.runtime_activation, "stop_capacity_services", real_stop)
    incident = pending_payload["recovery_incident"]
    prepared_path = guard._recovery_action_receipt_path(state, incident, "stop")
    prepared_path.write_text(
        json.dumps({
            "action": "capacity-stop",
            "incident_id": incident["incident_id"],
            "status": "PREPARED",
            "mutation_started": False,
            "pre_stop": {},
            "process_drain": {},
            "services": {},
            "stopped_labels": [],
            "labels": incident["stop_targets"],
            "manifest_digest": incident["manifest_digest"],
            "runtime_identity_digest": incident["runtime_identity_digest"],
            "generation": incident["generation"],
            "owned_roots": incident["owned_roots"],
            "receipt_path": str(prepared_path),
        }),
        encoding="utf-8",
    )
    prepared_path.chmod(0o600)

    stopped = guard.check_once(*roots, state, now=1600, stop_runner=runner)
    assert stopped["status"] == "STOPPED"
    assert stopped["recovery_incident"]["stop_deferred_for_work"] is False
    assert stopped["recovery_incident"]["stop_action_receipt"] is not None
    assert len(bootouts) == 1

    state.write_text(json.dumps(pending_payload), encoding="utf-8")
    state.chmod(0o600)
    reconciled = guard.check_once(*roots, state, now=1900, stop_runner=runner)
    assert reconciled["status"] == "STOPPED"
    assert reconciled["recovery_incident"]["stop_action_receipt"] is not None
    assert len(bootouts) == 1

    action_path = Path(stopped["recovery_incident"]["stop_action_receipt"]["path"])
    interrupted_action = json.loads(action_path.read_text())
    interrupted_action["status"] = "DRAINING"
    action_path.write_text(json.dumps(interrupted_action), encoding="utf-8")
    action_path.chmod(0o600)
    state.write_text(json.dumps(pending_payload), encoding="utf-8")
    state.chmod(0o600)
    blocked = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert blocked["status"] == "OPERATOR_REQUIRED"
    assert blocked["recovery_incident"]["authorization_blocker"] == (
        "deferred_stop_action_interrupted"
    )
    assert len(bootouts) == 1
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    with pytest.raises(runtime_manifest.RuntimeWorkBusy, match="capacity stop is unresolved"):
        with runtime_manifest.runtime_work_lease(roots[1]):
            pytest.fail("operator handoff不得放行新工作")


@pytest.mark.parametrize("expire", [False, True])
@pytest.mark.parametrize("active_runs", [1, 2])
def test_capacity_recovery_running_job_survives_no_start_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expire: bool,
    active_runs: int,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    running = True
    runs = 1
    bootouts: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            bootouts.append(command)
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(
                command[-1], plists[label],
                state="running" if running else "not running",
                runs=runs, exit_code=0, pid=4321 if running else None,
            ),
        )

    assert guard.check_once(*roots, state, now=2200, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"
    runs = active_runs
    real_boundary = guard.runtime_activation.run_process_boundary

    def boundary(*args, **kwargs):
        if kwargs.get("mode") == "observe":
            return {
                "status": "PASS",
                "active": [{"pid": 4321, "label": label}] if running else [],
                "resample_required": False,
                "seen_labels": [label],
            }
        return real_boundary(*args, **kwargs)

    monkeypatch.setattr(guard.runtime_activation, "run_process_boundary", boundary)
    for tick in (2500, 3101, 3900):
        result = guard.check_once(*roots, state, now=tick, stop_runner=runner)
        assert result["status"] == "RECOVERY_VERIFYING", result["recovery_incident"]
        assert bootouts == []
    if expire:
        result = guard.check_once(
            *roots, state,
            now=2500 + guard.RECOVERY_ACTIVE_RUN_TIMEOUT_SECONDS + 1,
            stop_runner=runner,
        )
        assert result["status"] == "OPERATOR_REQUIRED"
        assert result["recovery_incident"]["recovery_failure"] == (
            "resume_active_run_timeout"
        )
        assert bootouts == []
        return
    running = False
    runs = 2
    result = guard.check_once(*roots, state, now=4200, stop_runner=runner)
    assert result["status"] == "PASS"


@pytest.mark.parametrize("expire_gap", [False, True])
def test_capacity_recovery_restart_gap_after_long_run_does_not_use_no_start_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expire_gap: bool,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    running = True
    runs = 1
    bootouts: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            bootouts.append(command)
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(
                command[-1], plists[label],
                state="running" if running else "not running",
                runs=runs, exit_code=0, pid=4321 if running else None,
            ),
        )

    assert guard.check_once(*roots, state, now=2200, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"
    real_boundary = guard.runtime_activation.run_process_boundary

    def boundary(*args, **kwargs):
        if kwargs.get("mode") == "observe":
            return {
                "status": "PASS",
                "active": [{"pid": 4321, "label": label}] if running else [],
                "resample_required": False,
                "seen_labels": [label],
            }
        return real_boundary(*args, **kwargs)

    monkeypatch.setattr(guard.runtime_activation, "run_process_boundary", boundary)
    assert guard.check_once(*roots, state, now=2500, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"
    assert guard.check_once(*roots, state, now=3900, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"

    # 第一次長任務已正常結束，但 launchd 尚未進入下一次 StartInterval run。
    running = False
    gap = guard.check_once(*roots, state, now=3950, stop_runner=runner)
    assert gap["status"] == "RECOVERY_VERIFYING"
    assert bootouts == []
    assert gap["recovery_incident"]["active_run_last_seen_epoch"][label] == 3900

    if expire_gap:
        expired = guard.check_once(
            *roots, state,
            now=3900 + guard.RECOVERY_EXECUTION_TIMEOUT_SECONDS + 1,
            stop_runner=runner,
        )
        assert expired["status"] == "OPERATOR_REQUIRED"
        assert expired["recovery_incident"]["recovery_failure"] == (
            "resume_execution_timeout"
        )
        return

    running = True
    runs = 2
    assert guard.check_once(*roots, state, now=4010, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"
    running = False
    done = guard.check_once(*roots, state, now=4310, stop_runner=runner)
    assert done["status"] == "PASS"
    assert done["recovery_incident"]["active_run_first_seen_epoch"] == {}
    assert done["recovery_incident"]["active_run_last_seen_epoch"] == {}


def test_capacity_recovery_detached_lineage_has_bounded_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    runs = 1

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0, _launchctl_loaded_identity(command[-1], plists[label], runs=runs)
        )

    assert guard.check_once(*roots, state, now=2200, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"
    runs = 2
    monkeypatch.setattr(
        guard.runtime_activation,
        "verify_capacity_resume_execution",
        lambda *_args, **_kwargs: {
            "status": "PENDING",
            "services": {label: {"status": "PASS"}},
            "process_observation": {"active": [{"pid": 4321}]},
            "lineage_missing_labels": [],
        },
    )
    first = guard.check_once(*roots, state, now=2500, stop_runner=runner)
    assert first["status"] == "RECOVERY_VERIFYING"
    assert first["recovery_incident"]["lineage_pending_first_seen_epoch"] == 2500
    expired = guard.check_once(
        *roots, state,
        now=2500 + guard.RECOVERY_EXECUTION_TIMEOUT_SECONDS + 1,
        stop_runner=runner,
    )
    assert expired["status"] == "OPERATOR_REQUIRED"
    assert expired["recovery_incident"]["recovery_failure"] == (
        "resume_lineage_timeout"
    )


@pytest.mark.parametrize(
    "corruption",
    ["missing_start", "future_lineage", "future_active", "future_active_last_seen"],
)
def test_capacity_recovery_missing_verification_start_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            raise AssertionError("invalid verification state不得自行停服務")
        assert action == "print", command
        return (
            _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))
            if loaded else _completed(113)
        )

    assert guard.check_once(*roots, state, now=2200, stop_runner=runner)["status"] == "RECOVERY_VERIFYING"
    payload = json.loads(state.read_text())
    if corruption == "missing_start":
        payload["recovery_incident"].pop("verification_started_epoch")
    elif corruption == "future_lineage":
        payload["recovery_incident"]["lineage_pending_first_seen_epoch"] = 1_000_000_000_000
    elif corruption == "future_active":
        payload["recovery_incident"]["active_run_first_seen_epoch"] = {
            label: 1_000_000_000_000
        }
    else:
        payload["recovery_incident"]["active_run_first_seen_epoch"] = {label: 2200}
        payload["recovery_incident"]["active_run_last_seen_epoch"] = {
            label: 1_000_000_000_000
        }
    state.write_text(json.dumps(payload), encoding="utf-8")
    state.chmod(0o600)
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)
    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["recovery_incident"]["authorization_blocker"] == (
        "capacity_recovery_incident_invalid"
    )


def test_delayed_rss_peak_inside_stabilization_window_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    snapshots = [_available_snapshot() for _ in range(2)]
    snapshots[-1]["rss_bytes"] = guard.RECOVERY_RSS_GROWTH_LIMIT_BYTES + 1
    samples = iter(snapshots)
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: dict(next(samples)))
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    runs = 1

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, runs
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(command[-1], plists[label], runs=runs),
        )

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    runs = 2
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "restart_measurement_outside_reserve"
    assert incident["recovery_failure"] == "restart_measurement_outside_reserve"
    assert incident["restart_measurement"]["rss_growth_bytes"] == (
        guard.RECOVERY_RSS_GROWTH_LIMIT_BYTES + 1
    )
    assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert incident["rollback"]["launchd_absent"] is True


@pytest.mark.parametrize(
    ("peak_kind", "measurement_field"),
    (
        ("admission", "admission_drop_bytes"),
        ("project", "project_growth_bytes"),
        ("swap", "swap_growth_bytes"),
    ),
)
def test_delayed_restart_peak_gates_each_resource_dimension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    peak_kind: str,
    measurement_field: str,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    snapshots = [_available_snapshot() for _ in range(2)]
    if peak_kind == "admission":
        snapshots[-1]["admission_available_bytes"] = (
            int(snapshots[0]["admission_available_bytes"])
            - guard.RECOVERY_PROJECTED_RESTART_BYTES
            - 1
        )
    elif peak_kind == "project":
        snapshots[-1]["bytes"] = (
            int(snapshots[0]["bytes"])
            + guard.RECOVERY_PROJECTED_RESTART_BYTES
            + 1
        )
    else:
        snapshots[-1]["swap_used_bytes"] = (
            guard.RECOVERY_SWAP_GROWTH_LIMIT_BYTES + 1
        )
    samples = iter(snapshots)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: dict(next(samples)),
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    runs = 1

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, runs
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(command[-1], plists[label], runs=runs),
        )

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    runs = 2
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["recovery_failure"] == "restart_measurement_outside_reserve"
    assert incident["restart_measurement"][measurement_field] > 0
    if peak_kind in {"admission", "project"}:
        assert (
            incident["restart_measurement"][measurement_field]
            > guard.RECOVERY_PROJECTED_RESTART_BYTES
        )
    else:
        assert (
            incident["restart_measurement"][measurement_field]
            > guard.RECOVERY_SWAP_GROWTH_LIMIT_BYTES
        )
    assert incident["authorization_blocker"] == "restart_measurement_outside_reserve"
    assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert loaded is False


def test_failed_stabilization_without_exclusive_rollback_lease_stays_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    snapshots = [_available_snapshot() for _ in range(2)]
    snapshots[-1]["rss_bytes"] = guard.RECOVERY_RSS_GROWTH_LIMIT_BYTES + 1
    samples = iter(snapshots)
    monkeypatch.setattr(
        guard,
        "_snapshot",
        lambda *_args, **_kwargs: dict(next(samples)),
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    real_shutdown_lease = guard.formal_runtime.runtime_shutdown_lease
    lease_calls = 0

    @contextmanager
    def staged_shutdown_lease(*args, **kwargs):
        nonlocal lease_calls
        lease_calls += 1
        if lease_calls == 2:
            raise runtime_manifest.RuntimeWorkBusy("synthetic inherited child lease")
        with real_shutdown_lease(*args, **kwargs) as descriptor:
            yield descriptor

    monkeypatch.setattr(
        guard.formal_runtime,
        "runtime_shutdown_lease",
        staged_shutdown_lease,
    )
    loaded = False
    runs = 1
    bootouts: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, runs
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            bootouts.append(command)
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(command[-1], plists[label], runs=runs),
        )

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    assert lease_calls == 1
    runs = 2
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert lease_calls == 2
    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "partial_recovery_rollback_unknown"
    assert incident["rollback"] == {
        "status": "ROLLBACK_UNKNOWN",
        "services": {},
        "reason": "runtime_shutdown_lease_unavailable",
    }
    assert loaded is True
    assert bootouts == []


def test_manual_disable_before_second_bootstrap_rolls_back_first_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels = guard.SERVICE_LABELS[:2]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=labels,
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded: set[str] = set()
    disabled_checks = 0
    bootstrapped: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal disabled_checks
        action = command[1]
        if action == "print-disabled":
            disabled_checks += 1
            if disabled_checks >= 4:
                return _completed(
                    0,
                    f'disabled services = {{\n\t"{labels[1]}" => true\n}}\n',
                )
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            label = Path(command[-1]).stem
            bootstrapped.append(label)
            loaded.add(label)
            return _completed()
        label = command[-1].rsplit("/", 1)[-1]
        if action == "bootout":
            loaded.discard(label)
            return _completed()
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "owned_service_manually_disabled"
    assert incident["recovery_failure"] == "owned_service_manually_disabled"
    assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert incident["rollback"]["launchd_absent"] is True
    assert bootstrapped == [labels[0]]
    assert loaded == set()


def test_post_bootstrap_unknown_rolls_back_attempted_loaded_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    unknown_once = False
    bootouts: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded, unknown_once
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            unknown_once = True
            return _completed()
        if action == "bootout":
            bootouts.append(command[-1].rsplit("/", 1)[-1])
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        if unknown_once:
            unknown_once = False
            return _completed(0, "malformed launchctl output\n")
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["attempted_labels"] == [label]
    assert incident["started_labels"] == []
    # bootstrap 後尚未 capture lineage 的 UNKNOWN，不得藉新 rollback journal 宣稱完成。
    assert incident["rollback"]["status"] == "ROLLBACK_UNKNOWN"
    assert "journal binding is invalid" in incident["rollback"]["reason"]
    assert "launchd_absent" not in incident["rollback"]
    assert bootouts == []
    assert loaded is True


def test_no_guard_owned_service_never_claims_recovered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=()
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[1] == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        raise AssertionError("沒有 Guard ownership 不得執行 launchctl mutation")

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["recovery_incident"]["authorization_blocker"] == "no_guard_owned_services"
    assert result["recovery_incident"].get("recovery_result") != "AUTOMATIC_RECOVERY_COMPLETE"


def test_receipt_drift_after_bootstrap_rolls_back_live_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,)
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    bootouts: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            bootouts.append(command[-1].rsplit("/", 1)[-1])
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    receipt_identity = started["recovery_incident"]["resume_action_receipt"]
    Path(str(receipt_identity["path"])).write_text("drift\n", encoding="utf-8")

    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["recovery_incident"]["recovery_failure"] == "resume_action_receipt_identity_drift"
    assert result["recovery_incident"]["rollback"]["status"] == "ROLLBACK_UNKNOWN"
    assert "resume action receipt identity drift" in result["recovery_incident"]["rollback"]["reason"]
    assert bootouts == []
    assert loaded is True


@pytest.mark.parametrize(
    "fault", ["runtime_validation", "post_execution_context", "barrier_file_drift"]
)
def test_verification_authority_failure_never_claims_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path, owned_labels=(label,)
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    drift = False
    original_validate = guard.formal_runtime.validate_runtime_tick

    def validate_runtime(*args, **kwargs):
        if drift and fault == "runtime_validation":
            raise guard.formal_runtime.RuntimeManifestError("synthetic runtime drift")
        return original_validate(*args, **kwargs)

    def recovery_context(_receipt):
        result = dict(context)
        if drift and fault == "post_execution_context":
            result["generation"] = "replacement-generation"
        if drift and fault == "barrier_file_drift":
            result["barrier"] = guard._file_identity(Path(str(context["barrier_path"])))
        return result

    def execution_proof(*args, **kwargs):
        nonlocal drift
        drift = True
        return {"status": "PASS", "services": {}}

    monkeypatch.setattr(guard.formal_runtime, "validate_runtime_tick", validate_runtime)
    monkeypatch.setattr(guard, "_recovery_context", recovery_context)
    monkeypatch.setattr(
        guard.runtime_activation, "verify_capacity_resume_execution", execution_proof
    )
    loaded = False
    bootouts: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            bootouts.append(command[-1].rsplit("/", 1)[-1])
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    if fault == "runtime_validation":
        drift = True
    if fault == "barrier_file_drift":
        Path(str(context["barrier_path"])).write_text("replacement\n", encoding="utf-8")
        drift = True
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    if fault == "barrier_file_drift":
        assert result["recovery_incident"]["rollback"]["status"] == "ROLLBACK_UNKNOWN"
        assert bootouts == []
        assert loaded is True
    else:
        assert result["recovery_incident"]["rollback"]["status"] == "ROLLBACK_COMPLETE"
        assert bootouts == [label]
        assert loaded is False


def test_post_bootstrap_unknown_never_claims_rollback_complete_when_live_is_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    bootouts: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            bootouts.append(command[-1].rsplit("/", 1)[-1])
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(0, "malformed launchctl output\n")

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "partial_recovery_rollback_unknown"
    assert incident["rollback"]["status"] == "ROLLBACK_UNKNOWN"
    assert "launchd_absent" not in incident["rollback"]
    assert bootouts == []
    assert loaded is True


def test_resume_receipt_identity_failure_rolls_back_mutated_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    real_file_identity = guard._file_identity
    failed = False

    def failing_file_identity(path: Path) -> dict[str, object]:
        nonlocal failed
        if path.name.endswith(".resume.json") and not failed:
            failed = True
            raise OSError("synthetic resume receipt identity failure")
        return real_file_identity(path)

    monkeypatch.setattr(guard, "_file_identity", failing_file_identity)

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert failed is True
    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["attempted_labels"] == [label]
    assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert incident["rollback"]["launchd_absent"] is True
    assert loaded is False


def test_plist_replacement_between_bootstraps_blocks_second_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels = guard.SERVICE_LABELS[:2]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=labels,
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded: set[str] = set()
    bootstrapped: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            label = Path(command[-1]).stem
            bootstrapped.append(label)
            loaded.add(label)
            if label == labels[0]:
                replacement = plists[labels[1]].with_suffix(".replacement")
                replacement.write_text("replaced bytes\n", encoding="utf-8")
                replacement.chmod(0o600)
                os.replace(replacement, plists[labels[1]])
            return _completed()
        label = command[-1].rsplit("/", 1)[-1]
        if action == "bootout":
            loaded.discard(label)
            return _completed()
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert bootstrapped == [labels[0]]
    assert loaded == {labels[0]}
    assert result["recovery_incident"]["rollback"]["status"] == "ROLLBACK_UNKNOWN"
    assert "launchd_absent" not in result["recovery_incident"]["rollback"]


def test_capacity_recovery_waits_when_restart_projection_would_cross_reserve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    sample = _available_snapshot()
    sample["disk_free_bytes"] = 20 * guard.GIB + guard.RECOVERY_PROJECTED_RESTART_BYTES // 2
    sample["admission_available_bytes"] = sample["disk_free_bytes"]
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: dict(sample))
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("insufficient restart reserve must not call launchctl")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "RECOVERY_PENDING"
    assert result["recovery_incident"]["healthy_samples"] == 0
    assert result["recovery_incident"]["recovery_wait_reasons"] == [
        "restart_projection_below_reserve"
    ]


def test_capacity_recovery_resets_consecutive_health_when_capacity_falls_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    sample = _available_snapshot()
    sample["disk_free_bytes"] = 19 * guard.GIB
    sample["admission_available_bytes"] = 19 * guard.GIB
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: dict(sample))
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        assert command[1] in {"bootout", "print"}
        return _completed(113 if command[1] == "print" else 0)

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "STOPPED"
    assert result["recovery_incident"]["healthy_samples"] == 0
    assert result["recovery_incident"]["last_healthy_epoch"] is None


def test_capacity_recovery_blocks_runtime_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots, state, _plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(guard.SERVICE_LABELS[0],),
    )
    drift = dict(context)
    drift["generation"] = "capacity-resume-drift"
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(drift))

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("runtime identity drift must not call launchctl")

    result = guard.check_once(*roots, state, now=2200, stop_runner=forbidden)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "recovery_context_drift:generation"
    )


@pytest.mark.parametrize("rollback_unknown", [False, True])
def test_capacity_recovery_partial_bootstrap_rolls_back_and_requires_operator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rollback_unknown: bool,
) -> None:
    labels = guard.SERVICE_LABELS[:2]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=labels,
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded: set[str] = set()
    commands: list[list[str]] = []
    rollback_state_seen: list[dict[str, object]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            label = Path(command[-1]).stem
            if label == labels[1]:
                return _completed(5)
            loaded.add(label)
            return _completed()
        if action == "bootout":
            if not rollback_state_seen:
                rollback_state_seen.append(json.loads(state.read_text()))
            label = command[-1].rsplit("/", 1)[-1]
            if not (rollback_unknown and label == labels[0]):
                loaded.discard(label)
            return _completed(5 if rollback_unknown and label == labels[0] else 0)
        assert action == "print", command
        label = command[-1].rsplit("/", 1)[-1]
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, state, now=2200, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["recovery_incident"]["attempts_started"] == 1
    incident = result["recovery_incident"]
    assert incident["recovery_failure"] == "bootstrap_or_identity_failed"
    if rollback_unknown:
        assert incident["authorization_blocker"] == "partial_recovery_rollback_unknown"
        assert incident["rollback"]["status"] == "ROLLBACK_UNKNOWN"
        assert "launchd_absent" not in incident["rollback"]
    else:
        assert incident["authorization_blocker"] == "bootstrap_or_identity_failed"
        assert incident["rollback"]["status"] == "ROLLBACK_COMPLETE"
        assert incident["rollback"]["launchd_absent"] is True
    assert [command[1] for command in commands].count("bootstrap") == 2
    assert loaded == ({labels[0]} if rollback_unknown else set())
    assert rollback_state_seen[0]["status"] == "ROLLBACK_IN_PROGRESS"
    assert (
        rollback_state_seen[0]["recovery_incident"]["rollback"]["status"]
        == "ROLLBACK_IN_PROGRESS"
    )


def test_capacity_recovery_rejects_loaded_service_with_failed_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(
        tmp_path,
        owned_labels=(label,),
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    loaded = False
    service = {"state": "spawn scheduled", "runs": 1, "exit_code": 75}

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        if action == "bootstrap":
            loaded = True
            return _completed()
        if action == "bootout":
            loaded = False
            return _completed()
        assert action == "print", command
        if not loaded:
            return _completed(113)
        return _completed(
            0,
            _launchctl_loaded_identity(
                command[-1],
                plists[label],
                state=str(service["state"]),
                runs=int(service["runs"]),
                exit_code=int(service["exit_code"]),
            ),
        )

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    service.update(state="not running", runs=2, exit_code=78)
    result = guard.check_once(*roots, state, now=2500, stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["recovery_incident"]["rollback"]["status"] == "ROLLBACK_COMPLETE"
    assert result["recovery_incident"]["rollback"]["launchd_absent"] is True
    assert result["recovery_incident"]["authorization_blocker"] == "resume_execution_failed"
    assert result["recovery_incident"]["recovery_failure"] == "resume_execution_failed"
    assert loaded is False


def test_check_uses_current_memory_as_baseline_after_unknown_previous_sample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    state = roots[0] / "state.json"
    state.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "STOPPED",
                "sampled_epoch": 900,
                "bytes": 100 * guard.MIB,
                "rss_bytes": None,
                "swap_used_bytes": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: _available_snapshot())

    def forbidden(_command: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("recovered telemetry baseline must not stop services")

    result = guard.check_once(
        *roots,
        state,
        now=1000,
        stop_runner=forbidden,
    )

    assert result["status"] == "OPERATOR_REQUIRED"
    assert (
        result["recovery_incident"]["authorization_blocker"]
        == "legacy_stop_without_owned_incident"
    )
    assert result["memory_streak"] == 0
    assert result["rss_bytes"] == 0
    assert result["swap_used_bytes"] == 0


def test_two_high_growth_cycles_trigger_bounded_stop_loss(
    tmp_path: Path,
    monkeypatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    plists, context = _make_recovery_context(
        tmp_path,
        roots,
        generation="high-growth-stop",
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
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
    loaded = set(guard.SERVICE_LABELS)

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        label = command[-1].split("/")[-1]
        if action == "bootout":
            loaded.discard(label)
            return _completed()
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

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
    actor_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=queue_root,
        publisher_state_root=publisher_root,
        log_root=log_root,
        identity=f"gate2-actor:{actor_head}:activation-only",
        runtime_digest="b" * 64,
        config_version="formal-runtime-v2-gate2",
        generation="g2-capacity-preflight",
        python_executable=Path(sys.executable).resolve(strict=True),
        uv_executable=Path(sys.executable).resolve(strict=True),
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
    _force_safe_child_disk_capacity(env, tmp_path)

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

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
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
        uv_executable=python_target,
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
    _force_safe_child_disk_capacity(env, tmp_path)

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


def _write_capacity_transition_barrier(
    root: Path,
    manifest: dict[str, object],
) -> Path:
    ready = root / "ready" / str(manifest["generation"])
    barrier = root / f"four-lane-activation-{manifest['generation']}.barrier"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready, manifest, label)
    runtime_manifest.activate_barrier(barrier, ready, manifest)
    return barrier


def _write_activation_only_live_plists(
    launch_agents: Path,
    *,
    manifest: dict[str, object],
    manifest_path: Path,
    barrier: Path,
    python: Path,
) -> None:
    ready_root = launch_agents / ".pantheon-four-lane-stage/readiness" / str(
        manifest["generation"]
    )
    launch_agents.mkdir(parents=True, exist_ok=True)
    environment_fields = {
        "PANTHEON_RUNTIME_SERVICE_LABEL": "service_label",
        "PANTHEON_RUNTIME_IDENTITY": "identity",
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": "manifest_digest",
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": "runtime_identity_digest",
        "PANTHEON_RUNTIME_CODE_DIGEST": "runtime_digest",
        "PANTHEON_RUNTIME_CONFIG_VERSION": "config_version",
        "PANTHEON_RUNTIME_GENERATION": "generation",
        "PANTHEON_RUNTIME_ACTOR_ROOT": "actor_root",
        "PANTHEON_RUNTIME_QUEUE_ROOT": "queue_root",
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": "publisher_state_root",
        "PANTHEON_RUNTIME_LOG_ROOT": "log_root",
        "PANTHEON_RUNTIME_ACTOR_HEAD": "actor_head",
        "PANTHEON_RUNTIME_PYTHON_EXECUTABLE": "python_executable",
        "PANTHEON_RUNTIME_UV_EXECUTABLE": "uv_executable",
    }
    for label in runtime_manifest.SERVICE_LABELS:
        receipt = runtime_manifest.receipt_for_label(manifest, label)
        payload = {
            "Label": label,
            "ProgramArguments": [
                str(python),
                "-m",
                "scripts.pantheon_content_runtime_manifest",
                "barrier-exec",
                "--barrier",
                str(barrier),
                "--expected-digest",
                str(manifest["manifest_digest"]),
                "--manifest",
                str(manifest_path),
                "--service-label",
                label,
                "--ready-root",
                str(ready_root),
                "--timeout",
                "90",
                "--activation-only",
                "--",
                str(python),
                "-m",
                "scripts.agy_content_publisher",
            ],
            "WorkingDirectory": receipt["actor_root"],
            "RunAtLoad": True,
            "EnvironmentVariables": {
                name: receipt[field]
                for name, field in environment_fields.items()
                if field in receipt
            },
        }
        path = launch_agents / f"{label}.plist"
        with path.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
        path.chmod(0o600)


def _write_normal_stage_plists(
    stage_dir: Path,
    *,
    manifest: dict[str, object],
    manifest_path: Path,
    barrier: Path,
    python: Path,
    exact_run_id: str | None,
) -> None:
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "manifest-digest").write_text(
        str(manifest["manifest_digest"]) + "\n",
        encoding="utf-8",
    )
    (stage_dir / "generation").write_text(
        str(manifest["generation"]) + "\n",
        encoding="utf-8",
    )
    (stage_dir / "publisher-max-runs").write_text("1\n", encoding="utf-8")
    exact_run_path = stage_dir / "publisher-exact-run-id"
    if exact_run_id is None:
        exact_run_path.unlink(missing_ok=True)
    else:
        exact_run_path.write_text(exact_run_id + "\n", encoding="utf-8")
    _write_activation_only_live_plists(
        stage_dir,
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=python,
    )
    for plist_path in stage_dir.glob("*.plist"):
        payload = plistlib.loads(plist_path.read_bytes())
        payload["ProgramArguments"].remove("--activation-only")
        if payload["Label"] == "com.pantheon.agy-content-publisher":
            payload["ProgramArguments"].extend(
                [
                    "--repo-root",
                    str(manifest["actor_root"]),
                    "--queue-root",
                    str(manifest["queue_root"]),
                    "--state-root",
                    str(manifest["publisher_state_root"]),
                    "--max-runs",
                    "1",
                ]
            )
            if exact_run_id is not None:
                payload["ProgramArguments"].extend(
                    ["--exact-run-id", exact_run_id]
                )
        with plist_path.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
    (stage_dir / "com.pantheon.content-capacity-guard.plist").unlink()


def _write_capacity_transition_launchctl(
    path: Path,
    *,
    launch_agents: Path,
    mutation_log: Path,
    observed_launch_agents: Path | None = None,
    unknown_service: bool = False,
    include_pid: bool = False,
    last_exit_code: int | None = 0,
    absent_labels: tuple[str, ...] = (),
) -> None:
    observed_launch_agents = observed_launch_agents or launch_agents
    root_line = (
        "printf 'gui/%s/com.pantheon.unknown = {\\n' \"$(id -u)\""
        if unknown_service
        else "printf '%s = {\\n' \"$2\""
    )
    pid_line = "  printf '%s\\n' '\tpid = 4242'\n" if include_pid else ""
    exit_line = (
        f"  printf '%s\\n' '\tlast exit code = {last_exit_code}'\n"
        if last_exit_code is not None
        else ""
    )
    absent_case = ""
    if absent_labels:
        absent_case = (
            "  case \"$label\" in\n"
            f"    {'|'.join(absent_labels)}) exit 113 ;;\n"
            "  esac\n"
        )
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  label=${2##*/}\n"
        f"{absent_case}"
        f"  plist='{launch_agents}/'$label'.plist'\n"
        f"  observed_plist='{observed_launch_agents}/'$label'.plist'\n"
        "  [ -f \"$plist\" ] || exit 113\n"
        f"  {root_line}\n"
        "  printf '\\tpath = %s\\n' \"$observed_plist\"\n"
        f"{pid_line}"
        "  printf '%s\\n' '\tstate = waiting'\n"
        f"{exit_line}"
        "  printf '%s\\n' '}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def _make_live_plists_normal(launch_agents: Path) -> None:
    for label in runtime_manifest.SERVICE_LABELS:
        path = launch_agents / f"{label}.plist"
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
        payload["ProgramArguments"].remove("--activation-only")
        with path.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)


def _make_live_plists_publisher_canary_mixed(
    launch_agents: Path,
    *,
    manifest: dict[str, object],
    manifest_path: Path,
) -> None:
    """模擬 Publisher-only canary 後：Publisher normal，其餘 target plist activation-only。"""
    python = Path(sys.executable).resolve(strict=True)
    barrier = Path(str(manifest["publisher_state_root"])) / (
        f"four-lane-activation-{manifest['generation']}.barrier"
    )
    _write_activation_only_live_plists(
        launch_agents,
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=python,
    )
    publisher = "com.pantheon.agy-content-publisher"
    staged_publisher = launch_agents / ".pantheon-four-lane-stage" / f"{publisher}.plist"
    shutil.copy2(staged_publisher, launch_agents / f"{publisher}.plist")


def _publisher_canary_transition_direct_fixture(
    tmp_path: Path,
) -> tuple[
    Path,
    dict[str, object],
    Path,
    Path,
    Path,
]:
    _repo, _env, fake_home, _mutation_log, manifest, manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_publisher_canary_mixed(
        launch_agents,
        manifest=manifest,
        manifest_path=manifest_path,
    )
    barrier = Path(str(manifest["publisher_state_root"])) / (
        f"four-lane-activation-{manifest['generation']}.barrier"
    )
    candidate_dir = tmp_path / "capacity-candidate"
    _write_activation_only_live_plists(
        candidate_dir,
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=Path(sys.executable).resolve(strict=True),
    )
    capacity_plist = tmp_path / "candidate-capacity.plist"
    capacity_payload = plistlib.loads(
        (candidate_dir / "com.pantheon.content-capacity-guard.plist").read_bytes()
    )
    capacity_payload["ProgramArguments"].remove("--activation-only")
    capacity_plist.write_bytes(plistlib.dumps(capacity_payload, sort_keys=True))
    capacity_plist.chmod(0o600)
    preflight_receipt = tmp_path / "preflight-pass.json"
    preflight_receipt.write_text(
        json.dumps(_passing_preflight_receipt(str(manifest["queue_root"]))),
        encoding="utf-8",
    )
    return launch_agents, manifest, manifest_path, barrier, capacity_plist


def _capacity_transition_installer_env(
    tmp_path: Path,
    *,
    config_version: str = "formal-runtime-v2-gate2",
    identity_suffix: str = "activation-only",
    include_actor_head: bool = False,
) -> tuple[dict[str, str], Path, Path, dict[str, object], Path]:
    repo = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    queue_root = tmp_path / "queue"
    publisher_root = tmp_path / "publisher"
    log_root = tmp_path / "logs"
    python = Path(sys.executable).resolve(strict=True)
    for path in (fake_bin, queue_root, publisher_root, log_root):
        path.mkdir(parents=True)
    actor_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=queue_root,
        publisher_state_root=publisher_root,
        log_root=log_root,
        identity=f"gate2-actor:{actor_head}:{identity_suffix}",
        runtime_digest="c" * 64,
        config_version=config_version,
        generation="g2-capacity-transition",
        python_executable=python,
        uv_executable=python,
        actor_head=actor_head if include_actor_head else None,
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    barrier = _write_capacity_transition_barrier(publisher_root, manifest)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _write_activation_only_live_plists(
        launch_agents,
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=python,
    )
    _write_normal_stage_plists(
        launch_agents / ".pantheon-four-lane-stage",
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=python,
        exact_run_id="capacity-transition-run",
    )
    mutation_log = tmp_path / "launchctl-mutations.log"
    _write_capacity_transition_launchctl(
        fake_bin / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
    )
    (fake_bin / "sysctl").write_text(
        "#!/bin/sh\nprintf '%s\\n' 'total = 0.00M  used = 0.00M  free = 0.00M'\n",
        encoding="utf-8",
    )
    (fake_bin / "sysctl").chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PANTHEON_CAPACITY_GUARD_STATE_FILE": str(queue_root / "capacity-state.json"),
            "PANTHEON_USER_HOME_DIR": str(fake_home),
            "PANTHEON_PYTHON_PATH": str(python),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": str(
                manifest["manifest_digest"]
            ),
            "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "TMPDIR": str(tmp_path),
        }
    )
    _force_safe_child_disk_capacity(env, tmp_path)
    return env, fake_home, mutation_log, manifest, manifest_path


def _g5_capacity_transition_fixture(
    tmp_path: Path,
    *,
    identity_suffix: str = "activation-only",
    include_actor_head: bool = False,
    exact_run_id: str | None = "auto-i18n-en-614aa4dc3542ab2c5637",
) -> tuple[Path, dict[str, str], Path, Path, dict[str, object], Path]:
    repo = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, manifest, manifest_path = (
        _capacity_transition_installer_env(
            tmp_path,
            config_version="formal-runtime-v3-model-route-v1",
            identity_suffix=identity_suffix,
            include_actor_head=include_actor_head,
        )
    )
    python = Path(sys.executable).resolve(strict=True)
    old_manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=Path(str(manifest["queue_root"])),
        publisher_state_root=Path(str(manifest["publisher_state_root"])),
        log_root=Path(str(manifest["log_root"])),
        identity=f"gate2-actor:{'8' * 40}:activation-only",
        runtime_digest="8" * 64,
        config_version="formal-runtime-v2-gate2",
        generation="g8-previous-activation-only",
        python_executable=python,
        uv_executable=python,
    )
    old_manifest_path = tmp_path / "old-runtime-manifest.json"
    runtime_manifest.write_manifest(old_manifest_path, old_manifest)
    old_barrier = _write_capacity_transition_barrier(
        Path(str(old_manifest["publisher_state_root"])),
        old_manifest,
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _write_activation_only_live_plists(
        launch_agents,
        manifest=old_manifest,
        manifest_path=old_manifest_path,
        barrier=old_barrier,
        python=python,
    )
    new_barrier = Path(str(manifest["publisher_state_root"])) / (
        f"four-lane-activation-{manifest['generation']}.barrier"
    )
    _write_normal_stage_plists(
        launch_agents / ".pantheon-four-lane-stage",
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=new_barrier,
        python=python,
        exact_run_id=exact_run_id,
    )
    return repo, env, fake_home, mutation_log, manifest, manifest_path


def _write_capacity_publisher_reset_receipt(
    launch_agents: Path,
    *,
    target_manifest: dict[str, object],
    correlation_id: str,
    last_exit_code: int = 78,
) -> Path:
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    live_aggregate: dict[str, object] | None = None
    live_receipts: dict[str, dict[str, object]] = {}
    live_sha256: dict[str, str] = {}
    identities: dict[str, dict[str, list[object]]] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        live_path = launch_agents / f"{label}.plist"
        live_receipt = runtime_manifest.plist_receipt(
            live_path,
            expected_activation_mode="activation-only",
        )
        with live_path.open("rb") as stream:
            arguments = plistlib.load(stream)["ProgramArguments"]
        aggregate = guard._publisher_reset_old_live_identity(
            guard._live_receipt_aggregate(live_receipt, arguments)
        )
        if live_aggregate is None:
            live_aggregate = aggregate
        else:
            assert aggregate == live_aggregate
        live_receipts[label] = live_receipt
        live_sha256[label] = guard._file_sha256(live_path)
        identities[label] = {
            "states": ["waiting"],
            "paths": [str(live_path)],
            "last_exit_codes": [last_exit_code],
        }
    assert live_aggregate is not None
    publisher_label = "com.pantheon.agy-content-publisher"
    other_six = []
    for label in runtime_manifest.SERVICE_LABELS:
        if label == publisher_label:
            continue
        other_six.append(
            {
                "label": label,
                "pre_plist_sha256": live_sha256[label],
                "post_plist_sha256": live_sha256[label],
                "pre_launchctl_identity": identities[label],
                "post_launchctl_identity": identities[label],
            }
        )
    payload = {
        "schema_version": guard.PUBLISHER_RESET_RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "transition": guard.PUBLISHER_RESET_TRANSITION,
        "correlation_id": correlation_id,
        "target": {
            "manifest_digest": target_manifest["manifest_digest"],
            "runtime_identity_digest": target_manifest["runtime_identity_digest"],
            "generation": target_manifest["generation"],
            "publisher_exact_run_id": (
                stage_dir / "publisher-exact-run-id"
            ).read_text(encoding="utf-8").strip(),
        },
        "old_live": {
            **live_aggregate,
            "generation_relation": (
                "target_same_generation"
                if live_aggregate["generation"] == target_manifest["generation"]
                else "target_newer_than_live"
            ),
        },
        "publisher": {
            "pre_plist_sha256": live_sha256[publisher_label],
            "post_plist_sha256": live_sha256[publisher_label],
            "post_plist_receipt": live_receipts[publisher_label],
            "post_launchctl_identity": identities[publisher_label],
            "previous_loaded": True,
        },
        "other_six": other_six,
    }
    receipt_path = stage_dir / guard.PUBLISHER_RESET_RECEIPT_NAME
    receipt_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    receipt_path.chmod(0o600)
    return receipt_path


def test_capacity_installer_accepts_g5_promoted_manifest_with_staged_six_plists(
    tmp_path: Path,
) -> None:
    """G5：new promoted v3 manifest + old live no-PID + staged six exact plists。"""
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "preactivation_transition" in completed.stdout
    staged_capacity = (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    )
    assert staged_capacity.is_file()
    assert not mutation_log.exists()


def test_capacity_installer_recovery_stages_after_guard_stopped_normal_services(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    business_labels = guard.SERVICE_LABELS
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=business_labels,
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert '"recovery_from_normal_stopped": true' in completed.stdout
    assert (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).is_file()
    assert not mutation_log.exists()


def test_capacity_installer_all_stopped_recovery_stages_after_promotion(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=tuple(runtime_manifest.SERVICE_LABELS),
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-all-stopped-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert '"recovery_from_all_stopped": true' in completed.stdout
    assert (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).is_file()
    assert not mutation_log.exists()


def test_capacity_installer_activation_only_all_stopped_recovery_stages_after_pause(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=tuple(runtime_manifest.SERVICE_LABELS),
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-activation-only-all-stopped-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert '"recovery_from_activation_only_all_stopped": true' in completed.stdout
    assert not mutation_log.exists()


def test_capacity_installer_activation_only_all_stopped_recovery_rejects_normal_plists(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, _mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=tmp_path / "mutations.log",
        absent_labels=tuple(runtime_manifest.SERVICE_LABELS),
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-activation-only-all-stopped-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "plist activation mode mismatch" in completed.stdout


def test_capacity_installer_all_stopped_recovery_rejects_publisher_canary_mixed_mode(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(runtime_manifest.RuntimeManifestError, match="activation mode mismatch"):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_accepts_exact_mixed_mode(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    preflight_receipt = tmp_path / "preflight-pass.json"

    receipt = guard.validate_preactivation_transition(
        preflight_receipt=preflight_receipt,
        manifest_path=manifest_path,
        expected_digest=str(manifest["manifest_digest"]),
        barrier=barrier,
        launch_agents_dir=launch_agents,
        capacity_plist=capacity_plist,
        recovery_from_publisher_canary_all_stopped=True,
        runner=lambda _command: _completed(113, ""),
    )

    assert receipt["status"] == "PASS"
    assert receipt["recovery_from_publisher_canary_all_stopped"] is True
    topology = {row["label"]: row["topology"] for row in receipt["loaded_labels"]}
    assert topology["com.pantheon.agy-content-publisher"] == "normal-absent"
    assert topology["com.pantheon.agy-gemini-new"] == "activation-only-absent"


def test_preactivation_remeasures_capacity_and_rejects_stale_safe_receipt(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="capacity remeasurement mismatch",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
            capacity_sensor=lambda _path: {
                **_host_capacity(200, 19),
                "capacity_source": "macos_foundation_important_usage",
            },
        )


def test_preactivation_rejects_capacity_path_outside_signed_manifest_queue(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    preflight_receipt = tmp_path / "preflight-pass.json"
    payload = json.loads(preflight_receipt.read_text(encoding="utf-8"))
    foreign_root = tmp_path / "foreign-volume"
    foreign_root.mkdir()
    payload["capacity_path"] = str(foreign_root)
    preflight_receipt.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="capacity path mismatch",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_rejects_wrong_mixed_mode(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    wrong_label = "com.pantheon.agy-gemini-new"
    wrong_path = launch_agents / f"{wrong_label}.plist"
    payload = plistlib.loads(wrong_path.read_bytes())
    payload["ProgramArguments"].remove("--activation-only")
    wrong_path.write_bytes(plistlib.dumps(payload, sort_keys=True))
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(runtime_manifest.RuntimeManifestError, match="activation mode mismatch"):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_rejects_stale_target_identity(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    for label in runtime_manifest.SERVICE_LABELS:
        plist_path = launch_agents / f"{label}.plist"
        payload = plistlib.loads(plist_path.read_bytes())
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_IDENTITY"] = "stale-canary-target"
        plist_path.write_bytes(plistlib.dumps(payload, sort_keys=True))
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="publisher-canary live target identity mismatch",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_rejects_stale_barrier_path(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    stale_barrier = tmp_path / "stale" / barrier.name
    for label in runtime_manifest.SERVICE_LABELS:
        plist_path = launch_agents / f"{label}.plist"
        payload = plistlib.loads(plist_path.read_bytes())
        arguments = payload["ProgramArguments"]
        barrier_index = arguments.index("--barrier") + 1
        arguments[barrier_index] = str(stale_barrier)
        plist_path.write_bytes(plistlib.dumps(payload, sort_keys=True))
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="publisher-canary live target path mismatch",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_rejects_stale_manifest_path(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    stale_manifest = tmp_path / "stale-runtime-manifest.json"
    for label in runtime_manifest.SERVICE_LABELS:
        plist_path = launch_agents / f"{label}.plist"
        payload = plistlib.loads(plist_path.read_bytes())
        arguments = payload["ProgramArguments"]
        manifest_index = arguments.index("--manifest") + 1
        arguments[manifest_index] = str(stale_manifest)
        plist_path.write_bytes(plistlib.dumps(payload, sort_keys=True))
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="publisher-canary live target path mismatch",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(113, ""),
        )


def test_capacity_installer_rejects_ambiguous_recovery_modes() -> None:
    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="preactivation recovery mode is ambiguous",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=Path("/unused/preflight.json"),
            manifest_path=Path("/unused/manifest.json"),
            expected_digest="0" * 64,
            barrier=Path("/unused/barrier.json"),
            launch_agents_dir=Path("/unused/LaunchAgents"),
            capacity_plist=Path("/unused/capacity.plist"),
            recovery_from_all_stopped=True,
            recovery_from_publisher_canary_all_stopped=True,
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_rejects_unknown_launchctl_state(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    preflight_receipt = tmp_path / "preflight-pass.json"

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="preactivation service is absent",
    ):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=lambda _command: _completed(3, ""),
        )


def test_capacity_installer_publisher_canary_all_stopped_recovery_rejects_loaded_service(
    tmp_path: Path,
) -> None:
    launch_agents, manifest, manifest_path, barrier, capacity_plist = (
        _publisher_canary_transition_direct_fixture(tmp_path)
    )
    loaded_label = "com.pantheon.agy-content-publisher"
    preflight_receipt = tmp_path / "preflight-pass.json"

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        label = command[-1].rsplit("/", 1)[-1]
        if label != loaded_label:
            return _completed(113, "")
        return _completed(
            0,
            (
                f"{command[-1]} = {{\n"
                f"\tpath = {launch_agents / f'{label}.plist'}\n"
                "\tstate = waiting\n"
                "\tlast exit code = 0\n"
                "}\n"
            ),
        )

    with pytest.raises(runtime_manifest.RuntimeManifestError, match="all-stopped recovery service is loaded"):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            recovery_from_publisher_canary_all_stopped=True,
            runner=runner,
        )


def test_capacity_installer_accepts_publisher_canary_recovery_action_name(
    tmp_path: Path,
) -> None:
    repo, env, _fake_home, _mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-publisher-canary-all-stopped-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 2
    assert "用法：" not in completed.stderr


def test_capacity_installer_all_stopped_recovery_rejects_loaded_capacity_guard(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=guard.SERVICE_LABELS,
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-all-stopped-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert '"status": "NO-GO"' in completed.stdout
    assert not (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).exists()


def test_capacity_installer_all_stopped_recovery_never_bypasses_empty_stage(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    shutil.rmtree(stage_dir)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=tuple(runtime_manifest.SERVICE_LABELS),
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-all-stopped-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert '"status": "NO-GO"' in completed.stdout
    assert not (
        stage_dir / "com.pantheon.content-capacity-guard.plist"
    ).exists()
    assert not mutation_log.exists()


def test_capacity_installer_normal_stopped_recovery_still_rejects_absent_capacity_guard(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=tuple(runtime_manifest.SERVICE_LABELS),
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert '"status": "NO-GO"' in completed.stdout
    assert not (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).exists()


def test_capacity_installer_recovery_accepts_operation_identity_with_actor_head(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(
            tmp_path,
            identity_suffix="new-lane-current-acceptance-20260829",
            include_actor_head=True,
        )
    )
    fake_git = tmp_path / "bin" / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        f"case \"$*\" in\n"
        f"  *'rev-parse --show-toplevel') printf '%s\\n' '{repo}' ;;\n"
        f"  *'rev-parse HEAD') printf '%s\\n' '{_manifest['actor_head']}' ;;\n"
        "  *'status --porcelain') exit 0 ;;\n"
        "  *) exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o700)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=guard.SERVICE_LABELS,
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert '"recovery_from_normal_stopped": true' in completed.stdout
    assert not mutation_log.exists()


def test_capacity_installer_recovery_accepts_absent_future_run_selector(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, manifest, _manifest_path = (
        _g5_capacity_transition_fixture(
            tmp_path,
            identity_suffix="new-lane-current-acceptance-20260829",
            include_actor_head=True,
            exact_run_id=None,
        )
    )
    fake_git = tmp_path / "bin" / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        f"case \"$*\" in\n"
        f"  *'rev-parse --show-toplevel') printf '%s\\n' '{repo}' ;;\n"
        f"  *'rev-parse HEAD') printf '%s\\n' '{manifest['actor_head']}' ;;\n"
        "  *'status --porcelain') exit 0 ;;\n"
        "  *) exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o700)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    _make_live_plists_normal(launch_agents)
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=guard.SERVICE_LABELS,
    )

    assert not (stage_dir / "publisher-exact-run-id").exists()
    publisher_receipt = runtime_manifest.publisher_plist_preflight(
        manifest,
        stage_dir / "com.pantheon.agy-content-publisher.plist",
        require_no_exact_run_id=True,
    )
    assert publisher_receipt["exact_run_id"] == ""

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert (
        stage_dir / "com.pantheon.content-capacity-guard.plist"
    ).is_file()
    assert not mutation_log.exists()


def test_capacity_installer_recovery_rejects_loaded_business_service(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _make_live_plists_normal(launch_agents)
    business_labels = guard.SERVICE_LABELS[1:]
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        absent_labels=business_labels,
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh"),
            "--install-recovery-stage",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert '"status": "NO-GO"' in completed.stdout
    assert not (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).exists()


def test_capacity_installer_accepts_g6_old_live_model_route_identity(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, manifest, manifest_path = (
        _capacity_transition_installer_env(
            tmp_path,
            config_version="formal-runtime-v3-model-route-v1",
        )
    )
    python = Path(sys.executable).resolve(strict=True)
    old_manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=Path(str(manifest["queue_root"])),
        publisher_state_root=Path(str(manifest["publisher_state_root"])),
        log_root=Path(str(manifest["log_root"])),
        identity=f"{'b74646' + '0' * 34}:four-lane-model-route-v1",
        runtime_digest="6" * 64,
        config_version="formal-runtime-v3-model-route-v1",
        generation="g8-previous-model-route",
        python_executable=python,
        uv_executable=python,
    )
    old_manifest_path = tmp_path / "g6-old-runtime-manifest.json"
    runtime_manifest.write_manifest(old_manifest_path, old_manifest)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _write_activation_only_live_plists(
        launch_agents,
        manifest=old_manifest,
        manifest_path=old_manifest_path,
        barrier=Path(str(old_manifest["publisher_state_root"]))
        / f"four-lane-activation-{old_manifest['generation']}.barrier",
        python=python,
    )
    _write_normal_stage_plists(
        launch_agents / ".pantheon-four-lane-stage",
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=Path(str(manifest["publisher_state_root"]))
        / f"four-lane-activation-{manifest['generation']}.barrier",
        python=python,
        exact_run_id="auto-i18n-en-614aa4dc3542ab2c5637",
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "preactivation_transition" in completed.stdout
    assert (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).is_file()
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "case",
    [
        "stage_manifest_digest",
        "publisher_exact_receipt_missing",
        "publisher_exact_plist_missing",
        "publisher_exact_receipt_wrong",
        "publisher_exact_receipt_empty",
        "publisher_exact_both_malformed",
        "staged_lane_digest",
        "staged_activation_only_child_io",
    ],
)
def test_capacity_installer_rejects_g5_preactivation_stage_drift(
    tmp_path: Path,
    case: str,
) -> None:
    repo, env, fake_home, mutation_log, _manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    if case == "stage_manifest_digest":
        (stage_dir / "manifest-digest").write_text("0" * 64 + "\n", encoding="utf-8")
    elif case == "publisher_exact_receipt_missing":
        (stage_dir / "publisher-exact-run-id").unlink()
    elif case == "publisher_exact_receipt_wrong":
        (stage_dir / "publisher-exact-run-id").write_text(
            "wrong-exact-run\n",
            encoding="utf-8",
        )
    elif case == "publisher_exact_receipt_empty":
        (stage_dir / "publisher-exact-run-id").write_text("\n", encoding="utf-8")
    elif case in {"publisher_exact_plist_missing", "publisher_exact_both_malformed"}:
        publisher_plist = stage_dir / "com.pantheon.agy-content-publisher.plist"
        payload = plistlib.loads(publisher_plist.read_bytes())
        arguments = payload["ProgramArguments"]
        exact_index = arguments.index("--exact-run-id")
        if case == "publisher_exact_plist_missing":
            del arguments[exact_index : exact_index + 2]
        else:
            arguments[exact_index + 1] = "malformed selector"
            (stage_dir / "publisher-exact-run-id").write_text(
                "malformed selector\n",
                encoding="utf-8",
            )
        with publisher_plist.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
    elif case == "staged_lane_digest":
        lane_plist = stage_dir / "com.pantheon.agy-gemini-new.plist"
        payload = plistlib.loads(lane_plist.read_bytes())
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST_DIGEST"] = "0" * 64
        with lane_plist.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
    elif case == "staged_activation_only_child_io":
        lane_plist = stage_dir / "com.pantheon.agy-gemini-new.plist"
        payload = plistlib.loads(lane_plist.read_bytes())
        payload["ProgramArguments"].insert(payload["ProgramArguments"].index("--"), "--activation-only")
        payload["StandardOutPath"] = str(tmp_path / "child-io.log")
        with lane_plist.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0, case
    assert not (
        stage_dir / "com.pantheon.content-capacity-guard.plist"
    ).exists()
    assert not mutation_log.exists()


def test_capacity_installer_rejects_one_live_plist_coherent_old_runtime_drift(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    python = Path(sys.executable).resolve(strict=True)
    drift_manifest = runtime_manifest.build_manifest(
        actor_root=repo,
        queue_root=Path(str(manifest["queue_root"])),
        publisher_state_root=Path(str(manifest["publisher_state_root"])),
        log_root=Path(str(manifest["log_root"])),
        identity=f"gate2-actor:{'7' * 40}:activation-only",
        runtime_digest="7" * 64,
        config_version="formal-runtime-v2-gate2",
        generation="g8-previous-activation-only",
        python_executable=python,
        uv_executable=python,
    )
    drift_manifest_path = tmp_path / "drift-runtime-manifest.json"
    runtime_manifest.write_manifest(drift_manifest_path, drift_manifest)
    drift_barrier = (
        Path(str(drift_manifest["publisher_state_root"]))
        / "drift"
        / f"four-lane-activation-{drift_manifest['generation']}.barrier"
    )
    _write_activation_only_live_plists(
        launch_agents / "drift",
        manifest=drift_manifest,
        manifest_path=drift_manifest_path,
        barrier=drift_barrier,
        python=python,
    )
    drift_payload = plistlib.loads(
        (launch_agents / "drift/com.pantheon.agy-content-publisher.plist").read_bytes()
    )
    with (launch_agents / "com.pantheon.agy-content-publisher.plist").open("wb") as stream:
        plistlib.dump(drift_payload, stream, sort_keys=True)

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).exists()
    assert not mutation_log.exists()


def test_capacity_installer_rejects_transition_live_pid_even_when_preflight_passes(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _manifest_path = (
        _capacity_transition_installer_env(
            tmp_path,
            config_version="formal-runtime-v3-model-route-v1",
        )
    )
    fake_bin = tmp_path / "bin"
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _write_capacity_transition_launchctl(
        fake_bin / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        include_pid=True,
    )
    (fake_bin / "ps").write_text(
        "#!/bin/sh\nprintf '%s\\n' 1 1 1 1 1 1\n",
        encoding="utf-8",
    )
    (fake_bin / "ps").chmod(0o700)

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    ).exists()
    assert not mutation_log.exists()


def test_preactivation_transition_rejects_capacity_candidate_plist_drift(
    tmp_path: Path,
) -> None:
    _repo, _env, fake_home, _mutation_log, manifest, manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    python = Path(sys.executable).resolve(strict=True)
    barrier = Path(str(manifest["publisher_state_root"])) / (
        f"four-lane-activation-{manifest['generation']}.barrier"
    )
    candidate_dir = tmp_path / "capacity-candidate"
    _write_activation_only_live_plists(
        candidate_dir,
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=python,
    )
    capacity_plist = tmp_path / "candidate-capacity.plist"
    payload = plistlib.loads(
        (candidate_dir / "com.pantheon.content-capacity-guard.plist").read_bytes()
    )
    payload["ProgramArguments"].remove("--activation-only")
    payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST_DIGEST"] = "0" * 64
    with capacity_plist.open("wb") as stream:
        plistlib.dump(payload, stream, sort_keys=True)
    capacity_plist.chmod(0o600)
    preflight_receipt = tmp_path / "preflight.json"
    preflight_receipt.write_text(
        json.dumps(
            {
                "status": "NO-GO",
                "reasons": ["rss_telemetry_unknown"],
                "rss_available": False,
                "rss_error": "loaded_service_pid_missing:com.pantheon.agy-content-publisher",
            }
        ),
        encoding="utf-8",
    )

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        label = command[-1].rsplit("/", 1)[-1]
        return _completed(
            0,
            (
                f"{command[-1]} = {{\n"
                f"\tpath = {launch_agents / f'{label}.plist'}\n"
                "\tstate = waiting\n"
                "\tlast exit code = 78\n"
                "}\n"
            ),
        )

    with pytest.raises(runtime_manifest.RuntimeManifestError):
        guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            runner=runner,
        )


def test_capacity_installer_stages_during_manifest_bound_preactivation_transition(
    tmp_path: Path,
) -> None:
    """RED：promoted manifest + live activation-only no-PID 只能完成純 staging。"""
    repo = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _manifest_path = (
        _capacity_transition_installer_env(tmp_path)
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "preactivation_transition" in completed.stdout
    staged = (
        fake_home
        / "Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    )
    assert staged.is_file()
    assert not mutation_log.exists()


@pytest.mark.skipif(
    Path("/var").resolve() == Path("/var"),
    reason="macOS /var → /private/var canonical alias is required",
)
def test_capacity_installer_canonicalizes_var_tmp_plist_for_preactivation_transition(
    tmp_path: Path,
) -> None:
    """REG-TEMP-PLIST-CANONICAL-PATH-001：public installer 必須接受 /var temp alias。"""
    repo = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _manifest_path = (
        _capacity_transition_installer_env(tmp_path)
    )
    private_tmp = tmp_path.resolve(strict=True)
    alias_tmp = Path("/var") / private_tmp.relative_to("/private/var")

    assert alias_tmp.samefile(private_tmp)
    assert alias_tmp != alias_tmp.resolve(strict=True)
    env["TMPDIR"] = str(alias_tmp)

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "preactivation_transition" in completed.stdout
    staged = (
        fake_home
        / "Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    )
    assert staged.is_file()
    assert not mutation_log.exists()
    assert not list(alias_tmp.glob("pantheon-content-capacity-guard.*"))


def test_preactivation_transition_enforces_activation_only_exit_78_boundary(
    tmp_path: Path,
) -> None:
    _repo, _env, fake_home, mutation_log, manifest, manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    python = Path(sys.executable).resolve(strict=True)
    barrier = Path(str(manifest["publisher_state_root"])) / (
        f"four-lane-activation-{manifest['generation']}.barrier"
    )
    candidate_dir = tmp_path / "capacity-candidate"
    _write_activation_only_live_plists(
        candidate_dir,
        manifest=manifest,
        manifest_path=manifest_path,
        barrier=barrier,
        python=python,
    )
    capacity_plist = candidate_dir / "com.pantheon.content-capacity-guard.plist"
    payload = plistlib.loads(capacity_plist.read_bytes())
    payload["ProgramArguments"].remove("--activation-only")
    with capacity_plist.open("wb") as stream:
        plistlib.dump(payload, stream, sort_keys=True)
    preflight_receipt = tmp_path / "preflight.json"
    preflight_receipt.write_text(
        json.dumps(_passing_preflight_receipt(str(manifest["queue_root"]))),
        encoding="utf-8",
    )
    fake_launchctl = tmp_path / "bin" / "launchctl"

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(fake_launchctl), *command[1:]],
            check=False,
            capture_output=True,
            text=True,
        )

    for last_exit_code in (None, 0, 78):
        _write_capacity_transition_launchctl(
            fake_launchctl,
            launch_agents=launch_agents,
            mutation_log=mutation_log,
            last_exit_code=last_exit_code,
        )
        reset_inputs: dict[str, object] = {}
        if last_exit_code == 78:
            correlation_id = "g8-exit78-valid-current"
            reset_inputs = {
                "publisher_reset_receipt": _write_capacity_publisher_reset_receipt(
                    launch_agents,
                    target_manifest=manifest,
                    correlation_id=correlation_id,
                ),
                "expected_reset_correlation_id": correlation_id,
            }
        result = guard.validate_preactivation_transition(
            preflight_receipt=preflight_receipt,
            manifest_path=manifest_path,
            expected_digest=str(manifest["manifest_digest"]),
            barrier=barrier,
            launch_agents_dir=launch_agents,
            capacity_plist=capacity_plist,
            runner=runner,
            **reset_inputs,
        )

        assert result["status"] == "PASS", last_exit_code

    invalid_cases = [
        ("other_nonzero", None, False, 1, "preactivation service mismatch"),
        ("pid", None, True, 78, "preactivation service has pid"),
        (
            "path_drift",
            tmp_path / "wrong-launch-agents",
            False,
            78,
            "preactivation service mismatch",
        ),
    ]
    for case, observed_path, include_pid, last_exit_code, expected_error in invalid_cases:
        _write_capacity_transition_launchctl(
            fake_launchctl,
            launch_agents=launch_agents,
            mutation_log=mutation_log,
            observed_launch_agents=observed_path,
            include_pid=include_pid,
            last_exit_code=last_exit_code,
        )
        with pytest.raises(runtime_manifest.RuntimeManifestError) as error:
            guard.validate_preactivation_transition(
                preflight_receipt=preflight_receipt,
                manifest_path=manifest_path,
                expected_digest=str(manifest["manifest_digest"]),
                barrier=barrier,
                launch_agents_dir=launch_agents,
                capacity_plist=capacity_plist,
                runner=runner,
            )
        assert str(error.value) == expected_error, case
    assert not mutation_log.exists()


def test_capacity_installer_accepts_exit_78_with_current_reset_provenance(
    tmp_path: Path,
) -> None:
    repo, env, fake_home, mutation_log, manifest, _manifest_path = (
        _g5_capacity_transition_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    correlation_id = "g8-exit78-installer-current"
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = correlation_id
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        last_exit_code=78,
    )
    _write_capacity_publisher_reset_receipt(
        launch_agents,
        target_manifest=manifest,
        correlation_id=correlation_id,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "preactivation_transition" in completed.stdout
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "case",
    [
        "same_generation",
        "missing_receipt",
        "stale_receipt",
        "correlation_drift",
        "publisher_identity_drift",
        "other_six_drift",
    ],
)
def test_capacity_installer_rejects_exit_78_provenance_failures(
    tmp_path: Path,
    case: str,
) -> None:
    if case == "same_generation":
        repo = Path(__file__).resolve().parents[1]
        env, fake_home, mutation_log, manifest, _manifest_path = (
            _capacity_transition_installer_env(tmp_path)
        )
    else:
        repo, env, fake_home, mutation_log, manifest, _manifest_path = (
            _g5_capacity_transition_fixture(tmp_path)
        )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    correlation_id = f"g8-exit78-{case}"
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = correlation_id
    _write_capacity_transition_launchctl(
        tmp_path / "bin" / "launchctl",
        launch_agents=launch_agents,
        mutation_log=mutation_log,
        last_exit_code=78,
    )
    if case != "missing_receipt":
        receipt_path = _write_capacity_publisher_reset_receipt(
            launch_agents,
            target_manifest=manifest,
            correlation_id=correlation_id,
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if case == "stale_receipt":
            receipt["target"]["generation"] = "stale-target-generation"
        elif case == "correlation_drift":
            env["PANTHEON_ACTIVATION_CORRELATION_ID"] = correlation_id + "-drift"
        elif case == "publisher_identity_drift":
            receipt["publisher"]["post_launchctl_identity"]["paths"] = [
                str(tmp_path / "wrong-publisher.plist")
            ]
        elif case == "other_six_drift":
            receipt["other_six"][0]["post_plist_sha256"] = "0" * 64
        receipt_path.write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        receipt_path.chmod(0o600)

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0, case
    assert "preactivation_transition" in completed.stdout
    staged_capacity = (
        launch_agents
        / ".pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    )
    assert not staged_capacity.exists()
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "case",
    [
        "stale_barrier",
        "wrong_generation_digest",
        "normal_live_plist",
        "malformed_live_plist",
        "missing_identity",
        "unknown_service",
    ],
)
def test_capacity_installer_rejects_unsafe_preactivation_transition_cases(
    tmp_path: Path,
    case: str,
) -> None:
    repo = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, manifest, manifest_path = (
        _capacity_transition_installer_env(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_plist = launch_agents / "com.pantheon.agy-content-publisher.plist"
    if case == "stale_barrier":
        stale_barrier = Path(manifest["publisher_state_root"]) / (
            f"four-lane-activation-{manifest['generation']}.barrier"
        )
        runtime_manifest.write_manifest(stale_barrier, {
            "schema_version": runtime_manifest.SCHEMA_VERSION,
            "service_labels": list(runtime_manifest.SERVICE_LABELS),
            "owner_uid": os.getuid(),
            "generation": "stale-capacity-transition",
            "manifest_digest": str(manifest["manifest_digest"]),
            "runtime_identity_digest": str(manifest["runtime_identity_digest"]),
            "ack_digests": ["0" * 64 for _label in runtime_manifest.SERVICE_LABELS],
        })
    elif case == "wrong_generation_digest":
        payload = plistlib.loads(publisher_plist.read_bytes())
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_GENERATION"] = (
            "wrong-capacity-transition"
        )
        with publisher_plist.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
    elif case == "normal_live_plist":
        payload = plistlib.loads(publisher_plist.read_bytes())
        payload["ProgramArguments"].remove("--activation-only")
        with publisher_plist.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
    elif case == "malformed_live_plist":
        publisher_plist.write_text("not a plist\n", encoding="utf-8")
    elif case == "missing_identity":
        payload = plistlib.loads(publisher_plist.read_bytes())
        del payload["EnvironmentVariables"]["PANTHEON_RUNTIME_IDENTITY"]
        with publisher_plist.open("wb") as stream:
            plistlib.dump(payload, stream, sort_keys=True)
    elif case == "unknown_service":
        _write_capacity_transition_launchctl(
            tmp_path / "bin" / "launchctl",
            launch_agents=launch_agents,
            mutation_log=mutation_log,
            unknown_service=True,
        )
    assert manifest_path.is_file()

    completed = subprocess.run(
        ["/bin/bash", str(repo / "scripts/install_pantheon_content_capacity_guard_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0, case
    staged = (
        fake_home
        / "Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.content-capacity-guard.plist"
    )
    assert not staged.exists()
    assert not mutation_log.exists()


def test_unknown_rss_telemetry_is_recorded_without_denying_disk_admission(
    tmp_path: Path, monkeypatch
) -> None:
    sample = _available_snapshot()
    sample.update({"rss_bytes": None, "rss_available": False, "rss_error": "ps_failed"})
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)

    result = guard.preflight(tmp_path, tmp_path / "publisher", tmp_path / "logs")

    assert result["status"] == "PASS"
    assert result["reasons"] == []
    assert result["telemetry_gaps"] == ["rss_telemetry_unknown"]


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


def test_swap_telemetry_gap_does_not_deny_disk_admission(
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
    assert result["status"] == "PASS"
    assert result["reasons"] == []
    assert result["telemetry_gaps"] == ["swap_telemetry_unknown"]


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
    monkeypatch.setenv("PANTHEON_USER_HOME_DIR", str(tmp_path / "home"))
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
            "config_version": "formal-runtime-v3-model-route-v1",
        },
    )
    monkeypatch.setattr(
        guard,
        "_disk_sample",
        lambda _path: (200 * guard.GIB, 100 * guard.GIB),
    )
    monkeypatch.setattr(guard, "_host_capacity_sample", lambda _path: _host_capacity(200, 100))
    activation_labels = {
        "value": frozenset({"com.pantheon.agy-content-publisher"})
    }
    monkeypatch.setattr(
        guard,
        "_activation_only_service_labels",
        lambda _receipt: activation_labels["value"],
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
            "topology": "INERT_LOADED",
            "pid_required": False,
            "measurement_required": False,
            "expected_process_count": 0,
            "resource_usage": "NOT_APPLICABLE",
        }
    ]

    invalid_outputs = {
        "duplicate_top_level": lambda target: exact_fixture(target).replace(
            "\tstate = not running\n", "\tstate = running\n\tstate = not running\n", 1
        ),
        "running": lambda target: exact_fixture(target).replace(
            "\tstate = not running\n", "\tstate = running\n", 1
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
        assert invalid["reasons"] == ["service_topology_invalid"]

    identity["value"] = f"gate2-actor:{'a' * 40}:normal"
    activation_labels["value"] = frozenset()
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
    assert "service_topology_invalid" in normal["reasons"]

    monkeypatch.setattr(
        guard,
        "_normal_scheduled_service_labels",
        lambda _receipt: frozenset(guard.SERVICE_LABELS),
    )
    live_plist = (
        Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
        / "Library"
        / "LaunchAgents"
        / "com.pantheon.agy-content-publisher.plist"
    )
    launch_output["build"] = lambda target: exact_fixture(target).replace(
        "\tstate = not running\n",
        f"\tpath = {live_plist}\n\tstate = not running\n",
        1,
    )
    scheduled_idle = guard.preflight(
        tmp_path,
        tmp_path / "publisher",
        tmp_path / "logs",
        runner=runner,
    )

    assert scheduled_idle["status"] == "PASS"
    assert scheduled_idle["rss_available"] is True
    assert scheduled_idle["rss_identity"]["idle_labels"] == [
        {
            "label": "com.pantheon.agy-content-publisher",
            "topology": "loaded-but-idle",
        }
    ]


def test_inert_loaded_pid_is_violation() -> None:
    label = "com.pantheon.agy-gemini-coordinator"
    target = f"gui/{os.getuid()}/{label}"

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["launchctl", "print", target]:
            return _completed(
                0,
                ANONYMIZED_INERT_LAUNCHCTL_FIXTURE.replace("<target>", target, 1).replace(
                    "\tstate = not running\n",
                    "\tstate = running\n\tpid = 4242\n",
                    1,
                ),
            )
        if command[:2] == ["launchctl", "print"]:
            return _completed(113)
        raise AssertionError(f"unexpected command: {command}")

    result = guard._service_rss_bytes(
        runner,
        expected_inert_labels=frozenset({label}),
    )

    assert result["available"] is False
    assert result["error"] == f"inert_service_pid_present:{label}"
    assert result["identity"]["violation"] == {
        "service": label,
        "expected": "no-pid",
        "actual": 4242,
    }


@pytest.mark.parametrize(
    "transition_state", ["running", "waiting", "spawn scheduled"]
)
def test_normal_scheduled_service_rechecks_transient_state_without_pid(
    monkeypatch: pytest.MonkeyPatch,
    transition_state: str,
) -> None:
    label = "com.pantheon.agy-gemini-new"
    target = f"gui/{os.getuid()}/{label}"
    live_plist = (
        Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
        / "Library"
        / "LaunchAgents"
        / f"{label}.plist"
    )
    calls = 0

    def identity(state: str, *, last_exit_code: int = 0) -> str:
        return ANONYMIZED_INERT_LAUNCHCTL_FIXTURE.replace(
            "<target>", target, 1
        ).replace(
            "\tstate = not running\n",
            (
                f"\tpath = {live_plist}\n"
                f"\tstate = {state}\n"
                f"\tlast exit code = {last_exit_code}\n"
            ),
            1,
        )

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        if command == ["launchctl", "print", target]:
            calls += 1
            return _completed(
                0,
                identity(transition_state if calls < 4 else "not running"),
            )
        if command[:2] == ["launchctl", "print"]:
            return _completed(113)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(guard.time, "sleep", lambda _seconds: None)
    result = guard._service_rss_bytes(
        runner,
        expected_idle_labels=frozenset({label}),
    )

    assert result["available"] is True
    assert result["error"] is None
    assert result["identity"]["idle_labels"] == [
        {"label": label, "topology": "loaded-but-idle"}
    ]
    assert calls == 4


@pytest.mark.parametrize("last_exit_code", [0, 1, 78, -15])
@pytest.mark.parametrize("transient_first", [False, True])
def test_normal_failed_job_settles_to_zero_rss(
    monkeypatch: pytest.MonkeyPatch,
    last_exit_code: int,
    transient_first: bool,
) -> None:
    label = "com.pantheon.agy-gemini-i18n-rewrite"
    target = f"gui/{os.getuid()}/{label}"
    plist = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True) / "Library" / "LaunchAgents" / f"{label}.plist"
    calls = 0

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        if command == ["launchctl", "print", target]:
            calls += 1
            transient = transient_first and calls == 1
            state = "running" if transient else "not running"
            code = 0 if transient else last_exit_code
            return _completed(0, f"{target} = {{\n\tpath = {plist}\n\tstate = {state}\n\tlast exit code = {code}\n}}\n")
        if command[:2] == ["launchctl", "print"]:
            return _completed(113)
        raise AssertionError(command)

    monkeypatch.setattr(guard.time, "sleep", lambda _seconds: None)
    result = guard._service_rss_bytes(runner, expected_idle_labels=frozenset({label}))
    assert result["available"] is True
    assert result["value"] == 0
    assert result["identity"]["idle_labels"] == [{"label": label, "topology": "loaded-but-idle"}]
    assert calls == (2 if transient_first else 1)


@pytest.mark.parametrize("invalid", ["path", "target", "duplicate_exit", "untrusted_label"])
def test_normal_failed_job_requires_unambiguous_trusted_identity(invalid: str) -> None:
    label = "com.pantheon.agy-gemini-i18n-rewrite"
    target = f"gui/{os.getuid()}/{label}"
    plist = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True) / "Library" / "LaunchAgents" / f"{label}.plist"
    path = str(plist) + (".wrong" if invalid == "path" else "")
    output_target = target + (".wrong" if invalid == "target" else "")
    extra = "\tlast exit code = 1\n" if invalid == "duplicate_exit" else ""
    output = f"{output_target} = {{\n\tpath = {path}\n\tstate = not running\n\tlast exit code = 1\n{extra}}}\n"

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["launchctl", "print", target]:
            return _completed(0, output)
        if command[:2] == ["launchctl", "print"]:
            return _completed(113)
        raise AssertionError(command)

    expected = frozenset() if invalid == "untrusted_label" else frozenset({label})
    result = guard._service_rss_bytes(runner, expected_idle_labels=expected)
    assert result["available"] is False
    assert result["value"] is None


@pytest.mark.parametrize("last_exit_code", [0, 1, 78])
def test_normal_scheduled_service_persistent_pid_gap_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    last_exit_code: int,
) -> None:
    label = "com.pantheon.agy-gemini-new"
    target = f"gui/{os.getuid()}/{label}"
    live_plist = (
        Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
        / "Library"
        / "LaunchAgents"
        / f"{label}.plist"
    )
    output = ANONYMIZED_INERT_LAUNCHCTL_FIXTURE.replace(
        "<target>", target, 1
    ).replace(
        "\tstate = not running\n",
        (
            f"\tpath = {live_plist}\n"
            "\tstate = running\n"
            f"\tlast exit code = {last_exit_code}\n"
        ),
        1,
    )
    calls = 0

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        if command == ["launchctl", "print", target]:
            calls += 1
            return _completed(0, output)
        if command[:2] == ["launchctl", "print"]:
            return _completed(113)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(guard.time, "sleep", lambda _seconds: None)
    result = guard._service_rss_bytes(
        runner,
        expected_idle_labels=frozenset({label}),
    )

    assert result["available"] is False
    assert result["error"] == f"loaded_service_pid_missing:{label}"
    assert calls == (1 if last_exit_code else guard.SERVICE_TRANSITION_RECHECKS + 1)


def test_activation_only_service_labels_does_not_infer_mode_from_opaque_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PANTHEON_USER_HOME_DIR", str(tmp_path / "missing-home"))

    labels = guard._activation_only_service_labels(
        {
            "status": "PASS",
            "identity": f"gate2-actor:{'a' * 40}:activation-only",
        }
    )

    assert labels == frozenset()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("RunAtLoad", False),
        ("StartInterval", 0),
        ("StartInterval", True),
        ("KeepAlive", False),
    ],
)
def test_normal_scheduled_service_labels_requires_manifest_bound_interval_plists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    home = tmp_path / "home"
    launch_agents = home / "Library" / "LaunchAgents"
    for path in (actor, queue, state, logs, launch_agents):
        path.mkdir(parents=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity=f"gate2-actor:{'a' * 40}:activation-only",
        runtime_digest="b" * 64,
        config_version="formal-runtime-v3-model-route-v1",
        generation="g2-scheduled-idle-test",
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    payloads: dict[str, dict[str, object]] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        receipt = runtime_manifest.receipt_for_label(manifest, label)
        payload: dict[str, object] = {
            "Label": label,
            "ProgramArguments": [],
            "WorkingDirectory": receipt["actor_root"],
            "RunAtLoad": True,
            "StartInterval": 60,
            "EnvironmentVariables": {
                "PANTHEON_RUNTIME_SERVICE_LABEL": receipt["service_label"],
                "PANTHEON_RUNTIME_IDENTITY": receipt["identity"],
                "PANTHEON_RUNTIME_MANIFEST_DIGEST": receipt["manifest_digest"],
                "PANTHEON_RUNTIME_IDENTITY_DIGEST": receipt[
                    "runtime_identity_digest"
                ],
                "PANTHEON_RUNTIME_CODE_DIGEST": receipt["runtime_digest"],
                "PANTHEON_RUNTIME_CONFIG_VERSION": receipt["config_version"],
                "PANTHEON_RUNTIME_GENERATION": receipt["generation"],
                "PANTHEON_RUNTIME_ACTOR_ROOT": receipt["actor_root"],
                "PANTHEON_RUNTIME_QUEUE_ROOT": receipt["queue_root"],
                "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": receipt[
                    "publisher_state_root"
                ],
                "PANTHEON_RUNTIME_LOG_ROOT": receipt["log_root"],
            },
        }
        payloads[label] = payload
        path = launch_agents / f"{label}.plist"
        path.write_bytes(plistlib.dumps(payload))
        path.chmod(0o600)
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST", str(manifest_path))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_MANIFEST_DIGEST", manifest["manifest_digest"]
    )
    monkeypatch.setattr(
        guard.pwd,
        "getpwuid",
        lambda _uid: SimpleNamespace(pw_dir=str(home)),
    )
    runtime_receipt = {
        "status": "PASS",
        "config_version": "formal-runtime-v3-model-route-v1",
        "identity": manifest["identity"],
    }

    assert guard._activation_only_service_labels(runtime_receipt) == frozenset()
    assert guard._normal_scheduled_service_labels(runtime_receipt) == frozenset(
        guard.SERVICE_LABELS
    )

    for label, payload in payloads.items():
        payload["ProgramArguments"] = [
            sys.executable,
            "-m",
            "scripts.pantheon_content_runtime_manifest",
            "barrier-exec",
            "--activation-only",
            "--",
            sys.executable,
        ]
        payload["StandardOutPath"] = str(logs / f"{label}.stdout.log")
        payload["StandardErrorPath"] = str(logs / f"{label}.stderr.log")
        target = launch_agents / f"{label}.plist"
        target.write_bytes(plistlib.dumps(payload))
        target.chmod(0o600)
    assert guard._activation_only_service_labels(runtime_receipt) == frozenset(
        guard.SERVICE_LABELS
    )

    for label, payload in payloads.items():
        payload["ProgramArguments"] = []
        payload.pop("StandardOutPath")
        payload.pop("StandardErrorPath")
        target = launch_agents / f"{label}.plist"
        target.write_bytes(plistlib.dumps(payload))
        target.chmod(0o600)

    runtime_receipt["config_version"] = "unexpected-runtime"
    assert guard._normal_scheduled_service_labels(runtime_receipt) == frozenset()
    runtime_receipt["config_version"] = manifest["config_version"]

    target_label = guard.SERVICE_LABELS[0]
    payloads[target_label][field] = value
    target = launch_agents / f"{target_label}.plist"
    target.write_bytes(plistlib.dumps(payloads[target_label]))
    target.chmod(0o600)

    assert guard._normal_scheduled_service_labels(runtime_receipt) == frozenset()


def test_stop_loss_is_stopped_only_after_every_registered_identity_is_absent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """REG-PANTHEON-CAPACITY-STOP-VERIFICATION-001。"""
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    plists, context = _make_recovery_context(
        tmp_path,
        roots,
        generation="stop-verification",
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    sample = _available_snapshot(guard.MAX_BYTES + 1)
    monkeypatch.setattr(guard, "_snapshot", lambda *_roots: sample)
    failed_label = guard.SERVICE_LABELS[2]
    loaded = set(guard.SERVICE_LABELS)

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        label = command[-1].split("/")[-1]
        if action == "bootout":
            if label == failed_label:
                return _completed(5)
            loaded.discard(label)
            return _completed()
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, roots[0] / "state.json", stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "capacity_stop_effector_failed"
    assert incident["stopped_by_guard"] == list(guard.SERVICE_LABELS[:2])
    receipt_identity = incident["stop_action_receipt"]
    action = guard.runtime_activation.load_action_receipt(
        Path(str(receipt_identity["path"]))
    )
    assert action["status"] == "UNKNOWN_OR_FAILED"
    assert action["services"][failed_label]["bootout_returncode"] == 5
    assert action["services"][failed_label]["post_stop"]["topology"] == "LOADED"


def test_failed_bootout_that_becomes_absent_does_not_grant_recovery_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = [tmp_path / name for name in ("queue", "publisher", "logs")]
    for root in roots:
        root.mkdir()
    plists, context = _make_recovery_context(
        tmp_path, roots, generation="bootout-unknown"
    )
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    monkeypatch.setattr(
        guard, "_snapshot", lambda *_roots: _available_snapshot(guard.MAX_BYTES + 1)
    )
    loaded = set(guard.SERVICE_LABELS)
    bootouts: list[str] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        action = command[1]
        if action == "print-disabled":
            return _completed(0, "disabled services = {\n}\n")
        label = command[-1].rsplit("/", 1)[-1]
        if action == "bootout":
            bootouts.append(label)
            loaded.discard(label)
            return _completed(5)
        assert action == "print", command
        if label not in loaded:
            return _completed(113)
        return _completed(0, _launchctl_loaded_identity(command[-1], plists[label]))

    result = guard.check_once(*roots, roots[0] / "state.json", stop_runner=runner)

    assert result["status"] == "OPERATOR_REQUIRED"
    incident = result["recovery_incident"]
    assert incident["authorization_blocker"] == "capacity_stop_effector_failed"
    assert incident["stopped_by_guard"] == []
    assert bootouts == [guard.SERVICE_LABELS[0]]


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


@pytest.mark.parametrize("change", ["exit", "replace", "absent", "stable", "churn", "malformed", "missing", "wrong-path", "contradictory-state"])
def test_rss_reconciles_only_proven_process_lifecycle(monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    label = "com.pantheon.agy-content-publisher"
    target = f"gui/{os.getuid()}/{label}"
    plist = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve() / "Library/LaunchAgents" / f"{label}.plist"
    pid = 100
    ps_calls = 0
    exited = False

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal pid, ps_calls, exited
        if command[:2] == ["launchctl", "print"]:
            if command[-1] != target or (exited and change == "absent"):
                return _completed(113)
            state = "not running" if exited or (ps_calls and change == "contradictory-state") else "running"
            pid_line = "" if exited else f"\tpid = {pid}\n"
            path = str(plist) + (".wrong" if ps_calls and change == "wrong-path" else "")
            return _completed(0, f"{target} = {{\n\tpath = {path}\n\tstate = {state}\n{pid_line}\tlast exit code = 1\n}}\n")
        assert command[:3] == ["ps", "-o", "pid=,rss="]
        ps_calls += 1
        old_pid = pid
        if change in ("exit", "absent"):
            exited = True
            return _completed(1, "")
        if change == "churn" or (change == "replace" and ps_calls == 1):
            pid += 1
        if change == "malformed":
            return _completed(0, f"{pid} invalid\n")
        if change == "missing":
            return _completed(0, "")
        return _completed(0, f"{old_pid} 42\n")

    monkeypatch.setattr(guard.time, "sleep", lambda _seconds: None)
    result = guard._service_rss_bytes(runner, expected_idle_labels=frozenset({label}))
    success = change in ("exit", "replace", "absent", "stable")
    assert result["available"] is success
    if success:
        assert result["value"] == (0 if change in ("exit", "absent") else 42 * 1024)
    else:
        assert result["value"] is None
    assert ps_calls == (3 if change == "churn" else 2 if change == "replace" else 1)
_REAL_HOST_CAPACITY_SAMPLE = guard._host_capacity_sample


def test_real_guard_rollback_retains_trusted_orphan_until_quiescent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F1：真 guard→verify→stop seam，舊 orphan 離開 roots 後仍存活就不得 bootout／完成。"""
    activation = guard.runtime_activation
    label = guard.SERVICE_LABELS[0]
    roots, state, plists, context = _seed_pending_capacity_recovery(tmp_path, owned_labels=(label,))
    monkeypatch.setattr(guard, "_snapshot", lambda *_args, **_kwargs: _available_snapshot())
    monkeypatch.setattr(guard, "_recovery_context", lambda _receipt: dict(context))
    monkeypatch.setattr(activation, "run_process_boundary", _CANONICAL_PROCESS_BOUNDARY)
    loaded = [False]
    orphan = [False]
    calls = []
    births = []
    clock = [0.0]
    monkeypatch.setattr(activation.os, "getpid", lambda: 50000)
    monkeypatch.setattr(activation.os, "getpgrp", lambda: 50000)
    monkeypatch.setattr(activation.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(activation.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    def birth(pid, _row, _record):
        births.append(pid)
        return None if pid == 123 and orphan[0] else [1, pid]

    def forbidden(*_args, **_kwargs):
        pytest.fail("真 guard seam 測試禁止 native I/O")

    monkeypatch.setattr(activation, "_process_birth_identity", birth)
    monkeypatch.setattr(activation.subprocess, "run", forbidden)
    monkeypatch.setattr(activation.os, "kill", forbidden)
    monkeypatch.setattr(activation.ctypes, "CDLL", forbidden)

    def runner(command):
        calls.append(command)
        if command[:2] == ["launchctl", "print-disabled"]:
            return _completed(0, "disabled services = {\n}\n")
        if command[:2] == ["launchctl", "bootstrap"]:
            loaded[0] = True
            return _completed()
        if command[:2] == ["launchctl", "bootout"]:
            loaded[0] = False
            return _completed()
        if command[:2] == ["launchctl", "print"]:
            if not loaded[0]:
                return _completed(113)
            return _completed(0, _launchctl_loaded_identity(
                command[-1], plists[label], state="waiting" if orphan[0] else "running",
                runs=2 if orphan[0] else 1, pid=None if orphan[0] else 123,
            ))
        if command[0] == "/bin/ps":
            body = "100 1 100 S /bin/sleep 300\n" if orphan[0] else f"123 1 9001 S {tmp_path}/actor/job\n100 123 100 S /bin/sleep 300\n"
            return _completed(0, body)
        if command[0] == "/usr/sbin/lsof":
            return _completed(0, "p100\nfcwd\nn/\n")
        raise AssertionError(command)

    started = guard.check_once(*roots, state, now=2200, stop_runner=runner)
    assert started["status"] == "RECOVERY_VERIFYING"
    orphan[0] = True
    pending = guard.check_once(*roots, state, now=2500, stop_runner=runner)
    assert pending["recovery_incident"]["execution_verification"]["process_observation"]["active"] == [100]
    expired = guard.check_once(*roots, state, now=2500 + guard.RECOVERY_EXECUTION_TIMEOUT_SECONDS + 1, stop_runner=runner)
    incident = expired["recovery_incident"]
    assert incident["rollback"]["status"] == "ROLLBACK_UNKNOWN", "存活可信 orphan 不得被新的空 journal 抹掉"
    assert not any(command[:2] == ["launchctl", "bootout"] for command in calls)
    assert loaded[0] and 100 in births
    resume_identity = incident["resume_action_receipt"]
    stopped = activation.load_action_receipt(Path(incident["rollback_action_receipt"]["path"]))
    assert stopped["status"] == "BLOCKED" and not stopped["mutation_started"]
    assert stopped["prior_lineage"]["resume_action_receipt"] == resume_identity
    target = activation.load_action_receipt(Path(stopped["process_journal_path"]))
    assert target["status"] == "UNKNOWN_OR_FAILED" and "deadline exceeded" in target["error"]
    assert target["processes"]["100"]["birth"] == [1, 100] and target["groups"] == [100, 9001]
    assert clock[0] == guard.RECOVERY_SHUTDOWN_TIMEOUT_SECONDS

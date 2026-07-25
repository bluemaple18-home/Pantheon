from __future__ import annotations

import json
import hashlib
import plistlib
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts import agy_gemini_v4_shadow as shadow


def test_shadow_bucket_is_deterministic_and_limited_to_four_per_day() -> None:
    start = datetime(2026, 7, 25, tzinfo=UTC)
    buckets = {
        shadow.bucket_key(start + timedelta(minutes=minute))
        for minute in range(24 * 60)
    }

    assert buckets == {
        "20260725T000000Z",
        "20260725T060000Z",
        "20260725T120000Z",
        "20260725T180000Z",
    }


def test_shadow_request_is_public_fixed_and_closed() -> None:
    request = shadow.build_shadow_request("20260725T180000Z")

    assert request["namespace"] == "gemini-v4-shadow-20260725T180000Z"
    assert request["role"] == "reviewer"
    assert request["model"] == "gemini-3.5-flash"
    assert set(request["response_schema"]) == {
        "type",
        "properties",
        "required",
        "additionalProperties",
    }
    assert request["response_schema"]["additionalProperties"] is False
    serialized = json.dumps(request, ensure_ascii=False)
    assert "/Users/" not in serialized
    assert "GEMINI_API_KEY" not in serialized
    assert "文章" not in request["prompt"]


def test_run_once_persists_observation_and_deduplicates_bucket(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[str] = []

    def process(queue_root: Path) -> dict[str, str]:
        request_path = next((queue_root / "outbox").glob("*.json"))
        calls.append(request_path.stem)
        return {"status": "processed", "job_id": request_path.stem}

    monkeypatch.setattr(
        shadow,
        "_collect_observation",
        lambda _root, request, _result, observed_at: {
            "schema_version": 1,
            "bucket": "20260725T180000Z",
            "job_id": request["job_id"],
            "observed_at": observed_at,
            "status": "PASS",
            "slot_id": "account-2",
            "replay_status": "COMPLETE",
            "process_count": 1,
            "outcome": "SUCCESS",
            "automatic_resend_allowed": False,
        },
    )
    now = datetime(2026, 7, 25, 19, 30, tzinfo=UTC)

    first = shadow.run_once(tmp_path, now=now, process=process)
    second = shadow.run_once(tmp_path, now=now, process=process)

    assert first["status"] == "PASS"
    assert second == first | {"cached": True}
    assert len(calls) == 1
    assert json.loads((tmp_path / "latest.json").read_text())["job_id"] == calls[0]


def test_failed_bucket_is_terminal_and_not_retried(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = 0

    def process(queue_root: Path) -> dict[str, str]:
        nonlocal calls
        calls += 1
        request_path = next((queue_root / "outbox").glob("*.json"))
        return {
            "status": "failed",
            "job_id": request_path.stem,
            "error_type": "V4BrokerFailure",
        }

    monkeypatch.setattr(
        shadow,
        "_collect_observation",
        lambda _root, request, _result, observed_at: {
            "schema_version": 1,
            "bucket": "20260725T120000Z",
            "job_id": request["job_id"],
            "observed_at": observed_at,
            "status": "FAIL",
            "error_type": "V4BrokerFailure",
            "automatic_resend_allowed": False,
        },
    )
    now = datetime(2026, 7, 25, 12, 1, tzinfo=UTC)

    assert shadow.run_once(tmp_path, now=now, process=process)["status"] == "FAIL"
    assert shadow.run_once(tmp_path, now=now, process=process)["cached"] is True
    assert calls == 1


def test_shadow_integration_uses_one_pool_slot_and_one_target_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "structured-target"
    trace = tmp_path / "target.trace"
    target.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "from pathlib import Path\n"
        "raw=sys.stdin.buffer.read()\n"
        "fd=int(sys.argv[sys.argv.index('--credential-fd')+1])\n"
        "assert os.read(fd,512)\n"
        f"with Path({str(trace)!r}).open('a',encoding='utf-8') as handle:"
        " handle.write('call\\n')\n"
        "print(json.dumps({'status':'PASS','transport':'gemini-v4-quota-shadow'}))\n",
        encoding="utf-8",
    )
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    slots = []
    for index in range(1, 4):
        credential = tmp_path / f"credential-{index}"
        credential.write_text(f"synthetic-key-{index}-with-safe-length\n", encoding="utf-8")
        credential.chmod(stat.S_IRUSR | stat.S_IWUSR)
        slots.append(
            {
                "slot_id": f"account-{index}",
                "credential_file": str(credential),
            }
        )
    manifest = tmp_path / "pool.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": "shadow-test-pool",
                "slots": slots,
            }
        ),
        encoding="utf-8",
    )
    manifest.chmod(stat.S_IRUSR | stat.S_IWUSR)
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(target))
    monkeypatch.setenv(
        "AGY_GEMINI_V4_EXECUTABLE_SHA256",
        hashlib.sha256(target.read_bytes()).hexdigest(),
    )
    now = datetime(2026, 7, 25, 19, 30, tzinfo=UTC)

    first = shadow.run_once(tmp_path / "state", now=now)
    second = shadow.run_once(tmp_path / "state", now=now)

    assert first["status"] == "PASS"
    assert first["credential_selected_count"] == 1
    assert first["slot_id"] in {"account-1", "account-2", "account-3"}
    assert first["process_count"] == 1
    assert first["automatic_resend_allowed"] is False
    assert second["cached"] is True
    assert trace.read_text().splitlines() == ["call"]


def test_launchd_template_is_independent_and_runs_every_six_hours() -> None:
    path = Path("ops/launchd/com.pantheon.agy-gemini-v4-shadow.plist.example")
    payload = plistlib.loads(path.read_bytes())

    assert payload["Label"] == "com.pantheon.agy-gemini-v4-shadow"
    assert payload["StartInterval"] == 21_600
    assert payload["ProgramArguments"][2] == "scripts.agy_gemini_v4_shadow"
    assert "scripts.agy_gemini_coordinator" not in payload["ProgramArguments"]
    assert payload["EnvironmentVariables"]["AGY_GEMINI_V4_BROKER"] == "1"
    installer = Path(
        "scripts/install_agy_gemini_v4_shadow_launchd.sh"
    ).read_text()
    assert "install|check)" in installer
    assert "launchctl bootout" in installer
    assert "uninstall)" in installer

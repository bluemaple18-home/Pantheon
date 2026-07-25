from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path

from scripts import agy_gemini_coordinator as coordinator
from scripts.agy_gemini_coordinator import cycle_once, read_run_state, register_run, seed_legacy_rewrite_runs, seed_new_matrix_runs
from scripts.agy_gemini_outbox import ExternalJobPending, create_external_request


def _write_brief(run_dir: Path, run_id: str = "private-run-001") -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"schema_version": 1, "run_id": run_id, "mode": "create", "articles": []}),
        encoding="utf-8",
    )


def test_register_run_is_idempotent_and_keeps_private_path_local(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "run-001"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir)

    first = register_run(run_dir, queue_root)
    second = register_run(run_dir, queue_root)

    assert first == second
    assert first["status"] == "active"
    assert first["run_dir"] == str(run_dir.resolve())
    assert len(list((queue_root / "runs").glob("*.json"))) == 1


def test_register_run_rejects_more_than_five_articles(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "run-oversized"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"run_id": "too-many", "articles": [{"slot": index} for index in range(6)]}),
        encoding="utf-8",
    )

    try:
        register_run(run_dir, tmp_path / "queue")
    except ValueError as error:
        assert str(error) == "brief articles must contain at most 5 items"
    else:
        raise AssertionError("six-article run must be rejected")


def test_register_run_accepts_private_rewrite_brief_above_eight_kb(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "rewrite-above-eight-kb"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "run_id": "rewrite-above-eight-kb",
                "mode": "rewrite_existing_body",
                "articles": [{"current_body": "字" * 3000}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = register_run(run_dir, tmp_path / "queue")

    assert state["status"] == "active"


def test_cycle_processes_one_external_job_then_completes_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-001"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir)
    register_run(run_dir, queue_root)
    tick_calls = 0
    process_calls = 0

    def fake_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        nonlocal tick_calls
        tick_calls += 1
        if tick_calls == 1:
            raise ExternalJobPending("public-job-001")
        return {"status": "complete", "approved_by_reviewer": 2}

    def fake_process(_queue_root: Path) -> dict[str, str]:
        nonlocal process_calls
        process_calls += 1
        return {"status": "processed", "job_id": "public-job-001"}

    summary = cycle_once(queue_root, tick=fake_tick, process=fake_process)
    state = read_run_state(run_dir, queue_root)

    assert summary["runner"] == {"status": "processed", "job_id": "public-job-001"}
    assert summary["complete"] == 1
    assert tick_calls == 2
    assert process_calls == 1
    assert state["status"] == "complete"
    assert state["result"]["approved_by_reviewer"] == 2


def test_cycle_advances_oldest_active_runs_instead_of_state_filename_order(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    expected = [f"run-{index:03d}" for index in range(5)]
    for index in range(8):
        run_id = f"run-{index:03d}"
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)
        state_path = coordinator._state_path(run_id, queue_root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["updated_at"] = f"2026-07-25T10:{index:02d}:00+08:00"
        state_path.write_text(json.dumps(state), encoding="utf-8")

    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    cycle_once(queue_root, tick=pending_tick, process=lambda _root: {"status": "idle"})

    assert advanced == expected


def test_lane_mode_advances_one_run_per_content_lane(tmp_path: Path, monkeypatch) -> None:
    queue_root = tmp_path / "queue"
    briefs = {
        "new-run": {"mode": "create", "articles": []},
        "rewrite-run": {
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": "LEGACY-001"}],
        },
        "i18n-new-run": {
            "mode": "translate_existing",
            "articles": [{"source_article_id": "V2-NEW-001", "locale": "en"}],
        },
        "i18n-rewrite-run": {
            "mode": "translate_existing",
            "articles": [{"source_article_id": "LEGACY-001", "locale": "ja"}],
        },
    }
    for run_id, payload in briefs.items():
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **payload}),
            encoding="utf-8",
        )
        register_run(run_dir, queue_root)
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: {"LEGACY-001"})
    routed: dict[str, str] = {}

    def pending_tick(run_dir: Path, job_queue_root: Path) -> dict[str, object]:
        routed[run_dir.name] = str(job_queue_root.relative_to(queue_root))
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=tmp_path,
        lane_mode=True,
    )

    assert routed == {
        "new-run": "lanes/new",
        "rewrite-run": "lanes/rewrite",
        "i18n-new-run": "lanes/i18n-new",
        "i18n-rewrite-run": "lanes/i18n-rewrite",
    }
    assert summary["lanes"] == {
        "new": {"active": 1, "queued": 0, "processing": 0},
        "rewrite": {"active": 1, "queued": 0, "processing": 0},
        "i18n-new": {"active": 1, "queued": 0, "processing": 0},
        "i18n-rewrite": {"active": 1, "queued": 0, "processing": 0},
    }


def test_lane_mode_migrates_shared_pending_jobs_by_run_namespace(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "new-run"
    _write_brief(run_dir, "new-run")
    state = register_run(run_dir, queue_root)
    namespace = coordinator._state_path(str(state["run_id"]), queue_root).stem
    request = create_external_request(
        queue_root,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="公開新文 prompt",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    )

    result = coordinator._migrate_pending_jobs(queue_root, [state], set())

    assert result == {"new": 1, "rewrite": 0, "i18n-new": 0, "i18n-rewrite": 0}
    assert not (queue_root / "outbox" / f"{request['job_id']}.json").exists()
    assert (queue_root / "lanes/new/outbox" / f"{request['job_id']}.json").exists()


def test_cycle_marks_run_failed_without_retrying_external_job(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-001"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir)
    register_run(run_dir, queue_root)

    def fail_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ValueError("invalid candidate")

    summary = cycle_once(queue_root, tick=fail_tick, process=lambda _root: {"status": "idle"})
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["status"] == "failed"
    assert state["error_type"] == "ValueError"
    assert "invalid candidate" not in state


def test_cycle_isolates_runner_malformed_json_and_keeps_run_retryable(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-malformed-json"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-malformed-json")
    register_run(run_dir, queue_root)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("public-job-malformed")

    def malformed_runner(_queue_root: Path) -> dict[str, str]:
        raise json.JSONDecodeError("unterminated response", '{"result":', 10)

    summary = cycle_once(queue_root, tick=pending_tick, process=malformed_runner)
    state = read_run_state(run_dir, queue_root)

    assert summary["status"] == "failed"
    assert summary["runner"] == {
        "status": "failed",
        "job_id": "public-job-malformed",
        "error_type": "JSONDecodeError",
    }
    assert state["status"] == "active"
    assert state["last_job_id"] == "public-job-malformed"


def test_seed_legacy_rewrite_runs_registers_oldest_unattempted_article(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    first_record = {
        "id": "LEGACY-001",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-001",
        "slug": "legacy-one",
        "urlSlug": "legacy-one",
        "primaryKeyword": "塔羅舊文一",
        "title": "塔羅舊文一",
        "description": "描述一",
        "answer": "答案一",
        "faq": [{"question": "問一", "answer": "答一"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-001",
    }
    second_record = {
        **first_record,
        "id": "LEGACY-002",
        "serial": "tarot-002",
        "slug": "legacy-two",
        "urlSlug": "legacy-two",
        "primaryKeyword": "塔羅舊文二",
        "title": "塔羅舊文二",
        "path": "articles/tarot/tarot-002",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    inventory = {
        "LEGACY-001": {"id": "LEGACY-001", "record": first_record, "canonicalPath": "/articles/tarot/tarot-001", "currentBody": current_body, "published": "2026-01-01", "updated": "2026-01-01"},
        "LEGACY-002": {"id": "LEGACY-002", "record": second_record, "canonicalPath": "/articles/tarot/tarot-002", "currentBody": current_body, "published": "2026-01-01", "updated": "2026-01-01"},
    }

    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [first_record, second_record])
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: inventory)

    summary = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=1,
        source_commit="a" * 40,
    )

    assert summary["status"] == "seeded"
    assert summary["created"] == 1
    assert summary["created_run_ids"] == ["legacy-auto-sweep-v1-tarot-001-legacy-001"]
    brief = json.loads((run_root / "legacy-auto-sweep-v1-tarot-001-legacy-001" / "brief.json").read_text(encoding="utf-8"))
    assert brief["mode"] == "rewrite_existing_body"
    assert brief["articles"][0]["article_id"] == "LEGACY-001"
    assert brief["articles"][0]["identity"]["serial"] == "tarot-001"
    assert len(list((queue_root / "runs").glob("*.json"))) == 1


def test_seed_legacy_rewrite_runs_ignores_non_rewrite_active_runs_for_capacity(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    record = {
        "id": "LEGACY-003",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-003",
        "slug": "legacy-three",
        "urlSlug": "legacy-three",
        "primaryKeyword": "塔羅舊文三",
        "title": "塔羅舊文三",
        "description": "描述三",
        "answer": "答案三",
        "faq": [{"question": "問三", "answer": "答三"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-003",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    active_briefs = {
        "create-active": {"mode": "create", "articles": []},
        "translate-active": {
            "mode": "translate_existing",
            "articles": [{"source_article_id": "V2-NEW-001", "locale": "en"}],
        },
        "rewrite-active": {
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": "LEGACY-OTHER"}],
        },
    }
    for run_id, payload in active_briefs.items():
        active_run_dir = tmp_path / "active-runs" / run_id
        active_run_dir.mkdir(parents=True)
        (active_run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **payload}),
            encoding="utf-8",
        )
        register_run(active_run_dir, queue_root)

    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(
        coordinator.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "LEGACY-003": {
                "id": "LEGACY-003",
                "record": record,
                "canonicalPath": "/articles/tarot/tarot-003",
                "currentBody": current_body,
                "published": "2026-01-01",
                "updated": "2026-01-01",
            }
        },
    )

    summary = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=2,
        max_active_runs=2,
        source_commit="c" * 40,
    )

    assert summary["status"] == "seeded"
    assert summary["created"] == 1
    assert summary["created_run_ids"] == ["legacy-auto-sweep-v1-tarot-003-legacy-003"]


def test_cycle_legacy_sweep_does_not_require_manual_register(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    record = {
        "id": "LEGACY-010",
        "product": "mbti",
        "articleCategory": "mbti",
        "serial": "mbti-010",
        "slug": "legacy-ten",
        "urlSlug": "legacy-ten",
        "primaryKeyword": "人格舊文十",
        "title": "人格舊文十",
        "description": "描述十",
        "answer": "答案十",
        "faq": [{"question": "問十", "answer": "答十"}],
        "tags": ["人格"],
        "path": "articles/mbti/mbti-010",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(
        coordinator.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "LEGACY-010": {
                "id": "LEGACY-010",
                "record": record,
                "canonicalPath": "/articles/mbti/mbti-010",
                "currentBody": current_body,
                "published": "2026-01-01",
                "updated": "2026-01-01",
            }
        },
    )
    monkeypatch.setattr(coordinator, "_head_sha", lambda _repo: "b" * 40)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("public-job-legacy-010")

    summary = cycle_once(
        tmp_path / "queue",
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=repo_root,
        legacy_sweep=True,
        legacy_state_root=tmp_path / "state",
        legacy_run_root=tmp_path / "private-runs",
    )

    assert summary["legacy_sweep"]["status"] == "seeded"
    assert summary["legacy_sweep"]["created_run_ids"] == ["legacy-auto-sweep-v1-mbti-010-legacy-010"]
    assert summary["active"] == 1
    assert summary["runner"] == {"status": "idle"}


def test_seed_new_matrix_runs_registers_prepared_create_run(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    calls: list[dict[str, object]] = []

    def fake_prepare_matrix_runs(
        _repo_root: Path,
        run_prefix: str,
        *,
        output_root: Path,
        limit: int,
        exclude_ids: set[str],
        max_articles_per_run: int,
    ) -> list[Path]:
        calls.append(
            {
                "run_prefix": run_prefix,
                "limit": limit,
                "exclude_ids": sorted(exclude_ids),
                "max_articles_per_run": max_articles_per_run,
            }
        )
        paths: list[Path] = []
        for index, article_id in enumerate(["V2-ZODIAC-ARIES-LOVE", "V2-ZODIAC-ARIES-WORK"], start=1):
            run_dir = output_root / f"{run_prefix}-{index:02d}"
            run_dir.mkdir(parents=True)
            brief = {
                "schema_version": 1,
                "run_id": f"{run_prefix}-{index:02d}",
                "mode": "create",
                "articles": [{"target": {"id": article_id}}],
            }
            path = run_dir / "brief.json"
            path.write_text(json.dumps(brief), encoding="utf-8")
            paths.append(path)
        return paths

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fake_prepare_matrix_runs)

    summary = seed_new_matrix_runs(
        repo_root,
        queue_root,
        run_root,
        min_active_runs=1,
        max_new_runs=1,
        max_articles_per_run=5,
    )

    assert summary["status"] == "seeded"
    assert summary["created"] == 2
    assert summary["created_run_ids"][0].startswith("auto-new-v1-")
    assert summary["created_run_ids"][1].startswith("auto-new-v1-")
    assert calls[0]["limit"] == 5
    assert calls[0]["exclude_ids"] == []
    assert len(list((queue_root / "runs").glob("*.json"))) == 2


def test_cycle_new_matrix_sweep_does_not_require_manual_register(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    def fake_prepare_matrix_runs(
        _repo_root: Path,
        run_prefix: str,
        *,
        output_root: Path,
        limit: int,
        exclude_ids: set[str],
        max_articles_per_run: int,
    ) -> list[Path]:
        run_dir = output_root / f"{run_prefix}-01"
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": f"{run_prefix}-01",
                    "mode": "create",
                    "articles": [{"target": {"id": "V2-MBTI-INTJ-WORK"}}],
                }
            ),
            encoding="utf-8",
        )
        return [run_dir / "brief.json"]

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fake_prepare_matrix_runs)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("public-job-new-001")

    summary = cycle_once(
        tmp_path / "queue",
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=repo_root,
        new_matrix_sweep=True,
        new_matrix_run_root=tmp_path / "private-runs",
        new_matrix_min_active_runs=1,
        new_matrix_max_new_runs_per_cycle=1,
    )

    assert summary["new_matrix_sweep"]["status"] == "seeded"
    assert summary["new_matrix_sweep"]["created"] == 1
    assert summary["active"] == 1
    assert summary["runner"] == {"status": "idle"}


def test_launchd_template_runs_coordinator_and_installer_is_valid_shell(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    installer = (repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh").read_text(encoding="utf-8")
    plist = plistlib.loads(
        (repo_root / "ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example").read_bytes()
    )
    lane_plist = plistlib.loads(
        (repo_root / "ops/launchd/com.pantheon.agy-gemini-lane.plist.example").read_bytes()
    )
    arguments = plist["ProgramArguments"]

    assert arguments[1:3] == ["-m", "scripts.agy_gemini_coordinator"]
    assert "--lane-mode" in arguments
    assert "--new-matrix-sweep" in arguments
    assert "--new-matrix-run-root" in arguments
    assert "--legacy-sweep" in arguments
    assert "--legacy-state-root" in arguments
    assert "--legacy-run-root" in arguments
    assert arguments[-1] == "cycle"
    assert plist["RunAtLoad"] is True
    assert lane_plist["ProgramArguments"][1:3] == ["-m", "scripts.agy_gemini_runner"]
    assert lane_plist["ProgramArguments"][-1] == "process-once"
    assert "for LANE in new rewrite i18n-new i18n-rewrite" in installer
    assert 'LANE_LABEL="com.pantheon.agy-gemini-${LANE}"' in installer
    assert 'LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-' in installer
    assert "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" in installer
    completed = subprocess.run(
        ["bash", "-n", "scripts/install_agy_gemini_coordinator_launchd.sh"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    smoke = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_coordinator",
            "--queue-root",
            str(tmp_path / "queue"),
            "cycle",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert smoke.returncode == 0
    assert json.loads(smoke.stdout)["runner"] == {"status": "idle"}

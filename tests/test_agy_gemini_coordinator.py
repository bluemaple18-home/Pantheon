from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts.agy_gemini_coordinator import cycle_once, read_run_state, register_run, seed_legacy_rewrite_runs, seed_new_matrix_runs
from scripts.agy_gemini_outbox import ExternalJobPending, consume_external_response, create_external_request


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


def test_lane_mode_continues_oldest_registered_run_until_terminal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_root = tmp_path / "queue"
    for index, run_id in enumerate(("i18n-oldest", "i18n-next")):
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "mode": "translate_existing",
                    "articles": [{"source_article_id": f"V2-NEW-{index + 1:03d}", "locale": "en"}],
                }
            ),
            encoding="utf-8",
        )
        register_run(run_dir, queue_root)
        state_path = coordinator._state_path(run_id, queue_root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["registered_at"] = f"2026-07-25T10:0{index}:00+08:00"
        state["updated_at"] = state["registered_at"]
        state_path.write_text(json.dumps(state), encoding="utf-8")

    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: set())
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    for _ in range(2):
        cycle_once(
            queue_root,
            tick=pending_tick,
            process=lambda _root: {"status": "idle"},
            repo_root=tmp_path,
            lane_mode=True,
        )

    assert advanced == ["i18n-oldest", "i18n-oldest"]


def test_new_only_cycle_advances_one_new_and_skips_non_new_lanes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_root = tmp_path / "queue"
    briefs = {
        "new-run-1": {"mode": "create", "articles": []},
        "new-run-2": {"mode": "create", "articles": []},
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
    disabled_job = queue_root / "lanes" / "rewrite" / "outbox" / "stale-rewrite.json"
    disabled_job.parent.mkdir(parents=True)
    disabled_job.write_text('{"status":"pending"}\n', encoding="utf-8")
    disabled_job_before = disabled_job.read_bytes()
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: {"LEGACY-001"})
    monkeypatch.setattr(
        coordinator,
        "seed_legacy_rewrite_runs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("new-only must not seed rewrite")
        ),
    )
    advanced: list[str] = []
    process_calls: list[Path] = []

    def pending_tick(run_dir: Path, _job_queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda root: process_calls.append(root) or {"status": "processed"},
        repo_root=tmp_path,
        legacy_sweep=True,
        lane_mode=True,
        new_only=True,
    )

    assert advanced == ["new-run-1"]
    assert process_calls == []
    assert summary["runner"] == {"status": "idle"}
    assert summary["active"] == 2
    assert summary["runnable_active"] == 2
    assert summary["disabled_backlog"] == {
        "active": 3,
        "queued": 1,
        "processing": 0,
        "lanes": {
            "rewrite": {"active": 1, "queued": 1, "processing": 0},
            "i18n-new": {"active": 1, "queued": 0, "processing": 0},
            "i18n-rewrite": {"active": 1, "queued": 0, "processing": 0},
        },
    }
    assert disabled_job.read_bytes() == disabled_job_before
    assert summary["legacy_sweep"] == {
        "status": "disabled_by_new_only",
        "created": 0,
        "created_run_ids": [],
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


def test_cycle_preserves_closed_code_and_failed_run_does_not_block_next(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    first_run = tmp_path / "runs" / "run-001"
    second_run = tmp_path / "runs" / "run-002"
    _write_brief(first_run, "run-001")
    _write_brief(second_run, "run-002")
    register_run(first_run, queue_root)
    register_run(second_run, queue_root)

    def mixed_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        if run_dir == first_run.resolve():
            raise coordinator.ExternalJobFailed(
                "public-job-failed",
                "RuntimeError",
                "CLI_NONZERO",
            )
        return {"status": "complete", "run_id": "run-002"}

    summary = cycle_once(
        queue_root,
        tick=mixed_tick,
        process=lambda _root: {"status": "idle"},
    )
    first_state = read_run_state(first_run, queue_root)
    second_state = read_run_state(second_run, queue_root)

    assert summary["failed"] == 1
    assert summary["complete"] == 1
    assert first_state["status"] == "failed"
    assert first_state["error_code"] == "CLI_NONZERO"
    assert second_state["status"] == "complete"


def test_cycle_closes_untrusted_failure_receipt_error_type(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "run-invalid-failure"
    _write_brief(run_dir, "run-invalid-failure")
    register_run(run_dir, queue_root)
    request = create_external_request(
        queue_root,
        namespace="opaque-coordinator-invalid-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema={"type": "object"},
    )
    marker = "PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    coordinator.atomic_write_json(
        queue_root / "failed" / f"{request['job_id']}.json",
        {
            "schema_version": 1,
            "job_id": request["job_id"],
            "request_sha256": request["request_sha256"],
            "error_type": marker,
            "completed_at": "2026-07-26T00:30:00+08:00",
        },
    )

    summary = cycle_once(
        queue_root,
        tick=lambda *_args: consume_external_response(queue_root, request),
        process=lambda _root: {"status": "idle"},
    )
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["error_type"] == "InvalidFailureReceipt"
    assert marker not in json.dumps(state)


def test_cycle_closes_deep_failure_json_without_state_leak(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "run-deep-failure"
    _write_brief(run_dir, "run-deep-failure")
    register_run(run_dir, queue_root)
    request = create_external_request(
        queue_root,
        namespace="opaque-coordinator-deep-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema={"type": "object"},
    )
    marker = "/Users/PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    depth = 20_000
    payload = "[" * depth + json.dumps(marker) + "]" * depth
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(payload, encoding="utf-8")

    summary = cycle_once(
        queue_root,
        tick=lambda *_args: consume_external_response(queue_root, request),
        process=lambda _root: {"status": "idle"},
    )
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["error_type"] == "InvalidFailureReceipt"
    serialized = json.dumps(state)
    assert marker not in serialized
    assert "RecursionError" not in serialized


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


def test_seed_new_matrix_runs_registers_only_one_run_and_article_per_cycle(
    tmp_path: Path,
    monkeypatch,
) -> None:
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
        article_ids = [
            "V2-ZODIAC-ARIES-LOVE",
            "V2-ZODIAC-ARIES-WORK",
            "V2-ZODIAC-ARIES-MONEY",
            "V2-ZODIAC-ARIES-HEALTH",
            "V2-ZODIAC-ARIES-GROWTH",
        ]
        for index, article_id in enumerate(article_ids, start=1):
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
    assert summary["created"] == 1
    assert summary["created_run_ids"][0].startswith("auto-new-v1-")
    assert calls[0]["limit"] == 1
    assert calls[0]["max_articles_per_run"] == 1
    assert calls[0]["exclude_ids"] == []
    assert len(list((queue_root / "runs").glob("*.json"))) == 1
    state_path = next((queue_root / "runs").glob("*.json"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    brief = json.loads((Path(state["run_dir"]) / "brief.json").read_text(encoding="utf-8"))
    assert len(brief["articles"]) == 1


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
    assert "--lane" in lane_plist["ProgramArguments"]
    assert lane_plist["ProgramArguments"][-1] == "process-once"
    assert plist["EnvironmentVariables"]["AGY_GEMINI_NEW_ONLY"] == "0"
    assert lane_plist["EnvironmentVariables"]["AGY_GEMINI_NEW_ONLY"] == "0"
    assert (
        lane_plist["EnvironmentVariables"]["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"]
        == "300"
    )
    assert (
        plist["EnvironmentVariables"]["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"]
        == "300"
    )
    assert "for LANE in new rewrite i18n-new i18n-rewrite" in installer
    assert 'LANE_LABEL="com.pantheon.agy-gemini-${LANE}"' in installer
    assert 'LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-' in installer
    assert "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" in installer
    assert 'PRODUCTION_POOL_FILE="${AGY_GEMINI_CREDENTIAL_POOL_FILE:-}"' in installer
    assert 'WRITER_MODEL="${AGY_WRITER_MODEL:-}"' in installer
    assert 'REVIEWER_MODEL="${AGY_REVIEWER_MODEL:-}"' in installer
    assert 'NEW_ONLY="${AGY_GEMINI_NEW_ONLY:-0}"' in installer
    assert (
        'RATE_LIMIT_COOLDOWN_SECONDS="${AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS:-300}"'
        in installer
    )
    assert (
        'PRODUCTION_STATE_FILE="${AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE:-'
        in installer
    )
    assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in lane_plist["EnvironmentVariables"]
    assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in plist["EnvironmentVariables"]
    assert "AGY_WRITER_MODEL" not in plist["EnvironmentVariables"]
    assert "AGY_REVIEWER_MODEL" not in plist["EnvironmentVariables"]
    assert "AGY_WRITER_MODEL" not in lane_plist["EnvironmentVariables"]
    assert "AGY_REVIEWER_MODEL" not in lane_plist["EnvironmentVariables"]
    assert (
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"
        not in lane_plist["EnvironmentVariables"]
    )
    assert (
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"
        not in plist["EnvironmentVariables"]
    )
    assert "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_FILE string" in installer
    assert (
        "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE string"
        in installer
    )
    assert "Add :EnvironmentVariables:AGY_WRITER_MODEL string" in installer
    assert "Add :EnvironmentVariables:AGY_REVIEWER_MODEL string" in installer
    assert "for LANE in new rewrite i18n-new i18n-rewrite" in installer
    preflight_end = installer.index(
        'if launchctl print "gui/${USER_ID}/com.pantheon.agy-gemini-runner"'
    )
    first_plist_write = installer.index('cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"')
    first_control_write = installer.index('launchctl bootout "gui/${USER_ID}"')
    assert "PRODUCTION_STATE_FILE" in installer[:preflight_end]
    assert preflight_end < first_plist_write < first_control_write
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


def test_installer_rejects_relative_production_pool_before_install_side_effects(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir()
    pool_file = tmp_path / "relative-production-pool.json"
    pool_file.write_text("{}\n", encoding="utf-8")
    pool_file.chmod(0o600)
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n", encoding="utf-8")
    dscl.chmod(0o700)
    launchctl_log = tmp_path / "launchctl.log"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{launchctl_log}'\nexit 1\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": pool_file.name,
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "absolute path" in completed.stderr
    assert not fake_home.exists()
    assert not launchctl_log.exists()


def test_installer_rejects_relative_allocator_state_before_install_side_effects(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir()
    pool_file, _manifest_sha256 = _write_installer_pool(tmp_path)
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    launchctl_log = tmp_path / "launchctl.log"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{launchctl_log}'\nexit 1\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool_file),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": "relative-state.json",
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "state path" in completed.stderr
    assert not fake_home.exists()
    assert not launchctl_log.exists()


def _write_installer_pool(tmp_path: Path) -> tuple[Path, str]:
    slots = []
    for index, slot_id in enumerate(("account-1", "account-2", "account-3"), 1):
        credential = tmp_path / f"credential-{index}"
        credential.write_text(
            f"synthetic-installer-credential-{index}-value\n",
            encoding="utf-8",
        )
        credential.chmod(0o600)
        slots.append({"slot_id": slot_id, "credential_file": str(credential)})
    payload = {
        "schema_version": 1,
        "pool_id": "pantheon-production-v1",
        "slots": slots,
    }
    pool = tmp_path / "production-pool.json"
    pool.write_text(json.dumps(payload), encoding="utf-8")
    pool.chmod(0o600)
    _payload, manifest_sha256 = runner._read_production_pool(pool)
    return pool, manifest_sha256


def _write_installer_state(
    path: Path,
    manifest_sha256: str,
    *,
    pool_id: str = "pantheon-production-v1",
) -> Path:
    lock = path.with_name(f"{path.name}.lock")
    lock.touch(mode=0o600)
    lock_stat = lock.stat()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": pool_id,
                "manifest_sha256": manifest_sha256,
                "last_ordinal": 1,
                "lock_device": lock_stat.st_dev,
                "lock_inode": lock_stat.st_ino,
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return lock


def _installer_test_env(
    tmp_path: Path,
    *,
    pool: Path,
    state: Path,
    fail_plutil_call: int | None = None,
) -> tuple[dict[str, str], Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir(exist_ok=True)
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    mutation_log = tmp_path / "launchctl-mutations.log"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 1; fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    if fail_plutil_call is not None:
        counter = tmp_path / "plutil-count"
        plutil = fake_bin / "plutil"
        plutil.write_text(
            "#!/bin/sh\n"
            f"count=$(cat '{counter}' 2>/dev/null || printf 0)\n"
            "count=$((count + 1))\n"
            f"printf '%s' \"$count\" > '{counter}'\n"
            f"if [ \"$count\" -eq {fail_plutil_call} ]; then exit 1; fi\n"
            "exec /usr/bin/plutil \"$@\"\n",
            encoding="utf-8",
        )
        plutil.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state),
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )
    return env, fake_home, mutation_log


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("AGY_GEMINI_NEW_ONLY", "true"),
        ("AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", "0"),
        ("AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", "3601"),
    ],
)
def test_installer_rejects_invalid_admission_config_before_side_effects(
    tmp_path: Path,
    variable: str,
    value: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )
    env[variable] = value

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "failure_class",
    [
        "pool-corrupt",
        "state-corrupt",
        "pool-mismatch",
        "lock-nonempty",
        "state-parent-unsafe",
    ],
)
def test_installer_metadata_failure_has_zero_target_or_control_side_effects(
    tmp_path: Path,
    failure_class: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, manifest_sha256 = _write_installer_pool(tmp_path)
    state_parent = tmp_path / "state"
    state_parent.mkdir(mode=0o700)
    state = state_parent / "round-robin-state.json"
    lock = _write_installer_state(state, manifest_sha256)
    if failure_class == "pool-corrupt":
        pool.write_text("{broken\n", encoding="utf-8")
    elif failure_class == "state-corrupt":
        state.write_text("{broken\n", encoding="utf-8")
    elif failure_class == "pool-mismatch":
        _write_installer_state(state, manifest_sha256, pool_id="other-pool")
    elif failure_class == "lock-nonempty":
        lock.write_text("unexpected", encoding="utf-8")
    else:
        state.unlink()
        lock.unlink()
        state_parent.chmod(0o777)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


@pytest.mark.parametrize("fail_plutil_call", [1, 2, 3, 4, 5])
def test_installer_builds_and_lints_every_plist_before_any_mutation(
    tmp_path: Path,
    fail_plutil_call: int,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
        fail_plutil_call=fail_plutil_call,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "model_overrides",
    [
        {},
        {
            "AGY_WRITER_MODEL": "gemini-explicit-writer",
            "AGY_REVIEWER_MODEL": "gemini-explicit-reviewer",
        },
    ],
)
def test_installer_injects_one_shared_allocator_contract_into_coordinator_and_all_lanes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_overrides: dict[str, str],
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir()
    pool_file, _manifest_sha256 = _write_installer_pool(tmp_path)
    state_file = tmp_path / "round-robin-state.json"
    gsc_copy_root = tmp_path / "existing-gsc-copy"
    publisher_root = tmp_path / "existing-content-publisher"
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
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
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool_file),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state_file),
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "AGY_GEMINI_NEW_ONLY": "0",
            "AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": "600",
            "PANTHEON_GSC_COPY_ROOT": str(gsc_copy_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )
    env.update(model_overrides)

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    coordinator_plist = plistlib.loads(
        (
            fake_home
            / "Library"
            / "LaunchAgents"
            / "com.pantheon.agy-gemini-coordinator.plist"
        ).read_bytes()
    )
    coordinator_arguments = coordinator_plist["ProgramArguments"]
    coordinator_variables = coordinator_plist["EnvironmentVariables"]
    assert coordinator_arguments[8] == str(gsc_copy_root)
    assert coordinator_arguments[11] == str(publisher_root)
    assert coordinator_arguments[13] == str(gsc_copy_root)
    shared_contract = {
        "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool_file),
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state_file),
        "AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": "600",
    }
    assert coordinator_variables["AGY_GEMINI_NEW_ONLY"] == "0"
    assert {
        key: coordinator_variables[key]
        for key in shared_contract
    } == shared_contract
    if model_overrides:
        assert coordinator_variables["AGY_WRITER_MODEL"] == "gemini-explicit-writer"
        assert coordinator_variables["AGY_REVIEWER_MODEL"] == "gemini-explicit-reviewer"
    else:
        assert "AGY_WRITER_MODEL" not in coordinator_variables
        assert "AGY_REVIEWER_MODEL" not in coordinator_variables
    for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite"):
        installed = plistlib.loads(
            (
                fake_home
                / "Library"
                / "LaunchAgents"
                / f"com.pantheon.agy-gemini-{lane}.plist"
            ).read_bytes()
        )
        variables = installed["EnvironmentVariables"]
        arguments = installed["ProgramArguments"]
        assert arguments[arguments.index("--lane") + 1] == lane
        assert {key: variables[key] for key in shared_contract} == shared_contract
        assert variables["AGY_GEMINI_NEW_ONLY"] == "0"
        assert "AGY_WRITER_MODEL" not in variables
        assert "AGY_REVIEWER_MODEL" not in variables

    for key, value in coordinator_variables.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _root: set())
    queue_root = tmp_path / "canary-off-queue"
    run_dir = tmp_path / "canary-off-run"
    _write_brief(run_dir, "canary-off-root-run")
    register_run(run_dir, queue_root)
    observed: list[tuple[Path, dict[str, str]]] = []

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("canary-off-root-job")

    def observe_root_runner(root: Path) -> dict[str, str]:
        observed.append(
            (
                root,
                {key: os.environ[key] for key in shared_contract},
            )
        )
        return {"status": "idle"}

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=observe_root_runner,
        repo_root=tmp_path,
        lane_mode=True,
        new_only=False,
    )

    assert summary["runner"] == {"status": "idle"}
    assert observed == [(queue_root.resolve(), shared_contract)]


def test_installer_pool_opt_out_preserves_compatibility_without_pool_requirements(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )
    env.pop("AGY_GEMINI_CREDENTIAL_POOL_FILE")
    env.pop("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE")

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert mutation_log.exists()
    installed_paths = [
        fake_home / "Library/LaunchAgents/com.pantheon.agy-gemini-coordinator.plist",
        *[
            fake_home / f"Library/LaunchAgents/com.pantheon.agy-gemini-{lane}.plist"
            for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite")
        ],
    ]
    assert len(installed_paths) == 5
    for path in installed_paths:
        variables = plistlib.loads(path.read_bytes())["EnvironmentVariables"]
        assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in variables
        assert "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE" not in variables
        assert variables["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"] == "300"

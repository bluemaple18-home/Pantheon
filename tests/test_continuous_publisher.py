from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from scripts import agy_content_publisher as publisher


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, queue, state_root = (tmp_path / name for name in ("repo", "queue", "state"))
    for path in (repo, queue / "runs", state_root):
        path.mkdir(parents=True)
    runs = {}
    for lane in publisher.CONTINUOUS_LANES:
        run_id = f"test-{lane}"
        run_dir = queue / lane / run_id
        run_dir.mkdir(parents=True)
        mode = {"new": "create", "rewrite": "rewrite_existing_body"}.get(lane, "translate_existing")
        article = {"id": run_id, "article_id": run_id, "locale": "ja"}
        candidate = {"run_id": run_id, "mode": mode, "articles": [article]}
        (run_dir / "candidate.json").write_text(json.dumps(candidate))
        run_state = {"run_id": run_id, "lane": lane, "run_dir": str(run_dir),
                     "result": {"candidate": str(run_dir / "candidate.json")}}
        (queue / "runs" / f"{run_id}.json").write_text(json.dumps(run_state))
        runs[lane] = (run_state, candidate)

    def unpublished(lane: str) -> bool:
        ledger = publisher._load_ledger(state_root)
        return not any(
            item.get("run_id") == runs[lane][0]["run_id"]
            for bucket in ("published_runs", "rewrite_released_runs", "translation_published_runs")
            for item in ledger[bucket]
        )

    def create(*_args, **_kwargs):
        run_state, candidate = runs["new"]
        return [(run_state, candidate, {})] if unpublished("new") else []

    def rewrite(*_args, **_kwargs):
        run_state, candidate = runs["rewrite"]
        return [(run_state, candidate, {}, {})] if unpublished("rewrite") else []

    def translation(*_args, lane=None, **_kwargs):
        run_state, candidate = runs[lane]
        return [(run_state, {}, candidate, {})] if unpublished(lane) else []

    monkeypatch.setattr(publisher, "collect_ready_runs", create)
    monkeypatch.setattr(publisher, "collect_ready_rewrite_runs", rewrite)
    monkeypatch.setattr(publisher, "collect_ready_translation_runs", translation)
    monkeypatch.setattr(publisher, "legacy_article_records", lambda *_: [{"id": "legacy"}])
    monkeypatch.setattr(publisher, "_filter_rewrite_runs_with_current_sources",
                        lambda _repo, _state, ready, **_kwargs: ready)
    calls = []
    behavior = {"status": "success"}

    def publish(_repo, _queue, _state_root, *, exact_run_ids, **kwargs):
        run_id = exact_run_ids[0]
        lane = next(lane for lane, pair in runs.items() if pair[0]["run_id"] == run_id)
        calls.append((lane, run_id, kwargs))
        phase = "create" if lane == "new" else "rewrite" if lane == "rewrite" else "translation"
        if behavior["status"] != "success":
            return {phase: {"status": behavior["status"]}}
        artifact = repo / "publications" / run_id
        artifact.parent.mkdir(exist_ok=True)
        artifact.write_text(run_id)
        ledger = publisher._load_ledger(state_root)
        bucket = {"create": "published_runs", "rewrite": "rewrite_released_runs",
                  "translation": "translation_published_runs"}[phase]
        commit = str(len(calls)).zfill(40)
        ledger[bucket].append({
            "run_id": run_id, "published_at": "2026-10-25T12:00:00+08:00",
            "version": f"0.3.{len(calls)}", "commit_sha": commit,
        })
        publisher._atomic_write_json(publisher._ledger_path(state_root), ledger)
        status = {"create": "PUBLISHED", "rewrite": "PUBLISHED_REWRITE",
                  "translation": "PUBLISHED_TRANSLATION"}[phase]
        return {phase: {"status": status, "pushed": True,
                        "run_ids": [run_id], "commit_sha": commit}}

    monkeypatch.setattr(publisher, "publish_ready_all", publish)
    monkeypatch.setattr(publisher, "_assert_no_unresolved_push", lambda *_: None)
    monkeypatch.setattr(publisher, "_repo_lock_path", lambda *_: repo / "publisher.lock")
    monkeypatch.setattr(publisher, "CONTINUOUS_TIMEZONE", publisher.ZoneInfo("Asia/Taipei"))
    return repo, queue, state_root, runs, calls, behavior


def _tick(fixture):
    repo, queue, state_root, *_ = fixture
    return publisher.publish_continuous_tick.__wrapped__(
        repo, queue, state_root, max_runs=1, push=True,
    )


def test_continuous_four_ticks_apply_one_distinct_article_each(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    repo, _queue, state_root, _runs, calls, _behavior = fixture
    results = [_tick(fixture) for _ in range(4)]
    assert [result["lane"] for result in results] == list(publisher.CONTINUOUS_LANES)
    assert [result["daily_articles"] for result in results] == [1, 2, 3, 4]
    assert len(list((repo / "publications").iterdir())) == 4
    assert all(path.read_text() == path.name for path in (repo / "publications").iterdir())
    assert len(calls) == 4
    assert publisher._continuous_daily_usage(_queue, state_root, "2026-10-25")[0] == 4


@pytest.mark.parametrize("failure", ["failed_recovered", "policy_rejected", "unexpected_error"])
def test_continuous_repeated_lane_failure_does_not_starve_other_lanes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    repo, queue, _state_root, runs, calls, behavior = fixture
    original_publish = publisher.publish_ready_all

    def fail_translation(*args, exact_run_ids, **kwargs):
        lane = next(lane for lane, pair in runs.items()
                    if pair[0]["run_id"] == exact_run_ids[0])
        behavior["status"] = failure if lane == "i18n-new" else "success"
        result = original_publish(*args, exact_run_ids=exact_run_ids, **kwargs)
        if lane == "i18n-new" and failure == "unexpected_error":
            raise RuntimeError("injected publication failure")
        return result

    monkeypatch.setattr(publisher, "publish_ready_all", fail_translation)
    for index in range(12):
        try:
            result = _tick(fixture)
            lane = result["lane"]
        except RuntimeError as error:
            assert failure == "unexpected_error"
            assert str(error) == "injected publication failure"
            lane = calls[-1][0]
            assert lane == "i18n-new"
        # 每輪提供另一筆可選候選；本測試不裁決失敗 run 的重試權限。
        run_id = f"next-{index}-{lane}"
        run_dir = queue / lane / run_id
        run_dir.mkdir()
        run_state, candidate = runs[lane]
        candidate = {**candidate, "run_id": run_id,
                     "articles": [{"id": run_id, "article_id": run_id, "locale": "ja"}]}
        run_state = {**run_state, "run_id": run_id, "run_dir": str(run_dir),
                     "result": {"candidate": str(run_dir / "candidate.json")}}
        (run_dir / "candidate.json").write_text(json.dumps(candidate))
        (queue / "runs" / f"{run_id}.json").write_text(json.dumps(run_state))
        runs[lane] = run_state, candidate

    assert [call[0] for call in calls] == list(publisher.CONTINUOUS_LANES) * 3
    assert len(list((repo / "publications").iterdir())) == 9


def test_continuous_all_lanes_fail_once_per_tick_without_busy_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    fixture[5]["status"] = "policy_rejected"
    for index in range(12):
        assert _tick(fixture)["status"] == "policy_rejected"
        assert len(fixture[4]) == index + 1
    assert [call[0] for call in fixture[4]] == list(publisher.CONTINUOUS_LANES) * 3
    assert not (fixture[0] / "publications").exists()
    assert publisher._continuous_daily_usage(fixture[1], fixture[2], "2026-10-25")[0] == 0


def test_continuous_collector_exception_preserves_turn_for_next_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)

    def broken_collector(*_args, **_kwargs):
        raise RuntimeError("injected collector failure")

    monkeypatch.setattr(publisher, "collect_ready_runs", broken_collector)
    with pytest.raises(RuntimeError, match="injected collector failure"):
        _tick(fixture)
    assert fixture[4] == []
    saved = json.loads((fixture[2] / "continuous-publisher-attempt.json").read_text())
    assert saved["last_attempted_lane"] == "new"
    assert _tick(fixture)["lane"] == "i18n-new"


def test_continuous_invalid_attempt_state_blocks_without_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    cursor = fixture[2] / "continuous-publisher-attempt.json"
    cursor.write_text('{"last_attempted_lane":"bad"}')
    before = cursor.read_bytes()
    with pytest.raises(publisher.PublishBlocked, match="attempt state is invalid"):
        _tick(fixture)
    assert cursor.read_bytes() == before
    assert fixture[4] == []


def test_continuous_dry_run_does_not_advance_saved_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    _tick(fixture)
    cursor = fixture[2] / "continuous-publisher-attempt.json"
    before = cursor.read_bytes()
    fixture[5]["status"] = "dry-run"
    result = publisher.publish_continuous_tick.__wrapped__(
        fixture[0], fixture[1], fixture[2], max_runs=1, dry_run=True,
    )
    assert result["lane"] == "i18n-new"
    assert cursor.read_bytes() == before


def test_continuous_skips_empty_lane_without_empty_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(publisher, "collect_ready_translation_runs",
                        lambda *_args, lane=None, **_kwargs: [] if lane == "i18n-new" else
                        [(fixture[3][lane][0], {}, fixture[3][lane][1], {})])
    assert _tick(fixture)["lane"] == "new"
    assert _tick(fixture)["lane"] == "rewrite"


def test_continuous_all_quarantined_lanes_skip_without_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, queue, state_root = (tmp_path / name for name in ("repo", "queue", "state"))
    for path in (repo, queue / "runs", state_root):
        path.mkdir(parents=True)
    ids = {lane: f"quarantined-{lane}" for lane in ("rewrite", "i18n-new", "i18n-rewrite")}
    publisher._atomic_write_json(publisher._ledger_path(state_root), {
        **publisher._load_ledger(state_root),
        "quarantined_runs": [
            {"run_id": run_id, "reason": "publisher only supports create mode"}
            for run_id in ids.values()
        ],
    })
    paths = {}
    for lane, run_id in ids.items():
        run_dir = queue / lane / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text("{}")
        path = queue / "runs" / f"{run_id}.json"
        path.write_text(json.dumps({"run_id": run_id, "lane": lane, "run_dir": str(run_dir)}))
        paths[lane] = path

    monkeypatch.setattr(publisher, "collect_ready_runs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(publisher, "legacy_article_records", lambda *_args: [{"id": "SOURCE-01"}])
    monkeypatch.setattr(publisher.pipeline, "load_publication_reference_corpus", lambda *_args: [])
    monkeypatch.setattr(publisher, "_selected_run_files", lambda _queue, _state, phase, _ids: (
        [paths["rewrite"]] if phase == "rewrite" else [paths["i18n-new"], paths["i18n-rewrite"]]
    ))
    monkeypatch.setattr(publisher, "_load_completed_run", lambda _path: (
        {"run_id": ids["rewrite"], "run_dir": str(queue / "rewrite" / ids["rewrite"])},
        {"run_id": ids["rewrite"], "mode": "rewrite_existing_body", "articles": [
            {"article_id": "SOURCE-01", "bodySections": []},
        ]},
        {"run_id": ids["rewrite"], "verdict": "APPROVE"},
    ))
    monkeypatch.setattr(publisher, "_retry_eligible", lambda *_args: True)
    monkeypatch.setattr(publisher, "_review_is_clean_approve", lambda *_args: True)
    monkeypatch.setattr(publisher, "_load_rewrite_brief", lambda *_args: {})
    monkeypatch.setattr(publisher, "_rewrite_findings_for_run", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(publisher.pipeline, "body_sha256", lambda *_args: "body-hash")
    monkeypatch.setattr(publisher, "_filter_rewrite_runs_with_current_sources", lambda _repo, _state, ready, **_kwargs: ready)
    monkeypatch.setattr(publisher.multilingual, "read_translation_brief_payload", lambda *_args: {"mode": "translate_existing"})
    monkeypatch.setattr(publisher, "_assert_no_unresolved_push", lambda *_args: None)
    monkeypatch.setattr(publisher, "_repo_lock_path", lambda *_args: repo / "publisher.lock")
    monkeypatch.setattr(publisher, "publish_ready_all", lambda *_args, **_kwargs: (
        _ for _ in ()
    ).throw(AssertionError("隔離稿不得進入交易")))

    result = publisher.publish_continuous_tick.__wrapped__(
        repo, queue, state_root, max_runs=1, dry_run=True,
    )
    assert result["status"] == "idle"
    assert not (repo / "publications").exists()


@pytest.mark.parametrize("status", ["busy", "failed_recovered"])
def test_continuous_does_not_try_next_run_after_non_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    fixture[5]["status"] = status
    result = _tick(fixture)
    assert result["status"] == status
    assert len(fixture[4]) == 1
    assert not (fixture[0] / "publications").exists()


def test_continuous_daily_limit_blocks_and_uses_operator_alert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    _repo, queue, state_root, runs, _calls, _behavior = fixture
    ledger = publisher._load_ledger(state_root)
    for index in range(300):
        run_id = f"published-{index:03d}"
        run_dir = queue / "new" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "candidate.json").write_text(json.dumps({
            "run_id": run_id, "mode": "create", "articles": [{"id": run_id}],
        }))
        (queue / "runs" / f"{run_id}.json").write_text(json.dumps({
            "run_id": run_id, "lane": "new", "run_dir": str(run_dir),
        }))
        ledger["published_runs"].append({
            "run_id": run_id, "published_at": "2026-10-25T12:00:00+08:00",
            "version": f"0.3.{index + 1}", "commit_sha": f"{index:040x}",
        })
    publisher._atomic_write_json(publisher._ledger_path(state_root), ledger)
    assert publisher._continuous_daily_usage(queue, state_root, "2026-10-25") == (300, "new")
    alerts = []
    result = publisher.publish_continuous_tick.__wrapped__(
        fixture[0], fixture[1], fixture[2], max_runs=1, push=True,
        alert_sender=lambda message: alerts.append(message) or
        {"status": "PLATFORM_ACCEPTED", "platform_message_id": "discord-300"},
    )
    assert result["status"] == "OPERATOR_REQUIRED"
    assert result["operator_alert"]["platform_message_id"] == "discord-300"
    assert "發布日上限" in alerts[0]
    assert fixture[4] == []
    assert _tick(fixture)["status"] == "OPERATOR_REQUIRED"


def test_pages_maintenance_failure_stops_before_article_and_sends_alert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(publisher, "_pages_deploy_tick", lambda *_a, **_k: {
        "status": "OPERATOR_REQUIRED", "reason": "pages_public_verification_timeout"})
    alerts = []
    result = publisher.publish_continuous_tick.__wrapped__(
        fixture[0], fixture[1], fixture[2], push=True, pages_enabled=True,
        alert_sender=lambda message: alerts.append(message) or {
            "status": "PLATFORM_ACCEPTED", "platform_message_id": "pages-timeout"},
    )
    assert result["status"] == "OPERATOR_REQUIRED"
    assert fixture[4] == []
    assert len(alerts) == 1 and "公開正文驗證" in alerts[0]


def test_pages_wait_does_not_wait_for_interval_or_stop_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(publisher, "_pages_deploy_tick", lambda *_a, **_k: {"status": "INTERVAL_WAIT"})
    result = publisher.publish_continuous_tick.__wrapped__(
        fixture[0], fixture[1], fixture[2], push=True, pages_enabled=True,
    )
    assert result["status"] == "PUBLISHED"
    assert len(fixture[4]) == 1
    assert result["deployment"] == {"status": "INTERVAL_WAIT"}


def test_continuous_busy_tick_applies_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    repo, _queue, state_root, _runs, calls, _behavior = fixture
    journal = publisher.MutationJournal(repo, publisher.run_git)
    with journal.state_scope(state_root) as admitted:
        assert admitted
        assert _tick(fixture)["status"] == "busy"
    assert calls == []
    assert not (repo / "publications").exists()
    assert not (state_root / "continuous-publisher-attempt.json").exists()


def test_continuous_reconstructs_actual_article_count_from_saved_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path, monkeypatch)
    repo, queue, state_root, runs, _calls, _behavior = fixture
    run_state, candidate = runs["new"]
    candidate["articles"].append({"id": "second"})
    (Path(run_state["run_dir"]) / "candidate.json").write_text(json.dumps(candidate))
    ledger = publisher._load_ledger(state_root)
    ledger["published_runs"].append({
        "run_id": run_state["run_id"], "published_at": "2026-10-25T12:00:00+08:00",
        "version": "0.3.1", "commit_sha": "a" * 40,
    })
    publisher._atomic_write_json(publisher._ledger_path(state_root), ledger)
    assert publisher._continuous_daily_usage(queue, state_root, "2026-10-25") == (2, "new")


@pytest.mark.parametrize("arguments", [
    ["--continuous-tick", "--max-runs", "1", "--push"],
    ["--continuous-tick", "--include-rewrites", "--max-runs", "2", "--push"],
    ["--continuous-tick", "--include-rewrites", "--max-runs", "1"],
])
def test_continuous_cli_rejects_unbounded_or_non_push_mode(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["publisher", *arguments])
    with pytest.raises(SystemExit, match="continuous tick"):
        publisher.main.__wrapped__()

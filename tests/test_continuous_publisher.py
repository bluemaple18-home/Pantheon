from __future__ import annotations

import json
from datetime import datetime as RealDatetime
from pathlib import Path
import sys

import pytest

from scripts import agy_content_publisher as publisher


@pytest.fixture(autouse=True)
def _fixed_fixture_day(monkeypatch):
    """既有樣本的日期固定在10/25；僅替換本測試模組使用的時鐘。"""
    class FixtureDatetime(RealDatetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 10, 25, 12, tzinfo=publisher.CONTINUOUS_TIMEZONE)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
    monkeypatch.setattr(publisher, 'datetime', FixtureDatetime)


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


def _batch_fixture(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path, monkeypatch)
    repo, queue, state_root, runs, _calls, behavior = fixture
    run_id = 'test-new-second'
    directory = queue / 'new' / run_id
    directory.mkdir()
    candidate = {'run_id': run_id, 'mode': 'create', 'articles': [{'id': run_id}]}
    (directory / 'candidate.json').write_text(json.dumps(candidate))
    state = {'run_id': run_id, 'lane': 'new', 'run_dir': str(directory),
             'result': {'candidate': str(directory / 'candidate.json')}}
    (queue / 'runs' / (run_id + '.json')).write_text(json.dumps(state))
    original = publisher.collect_ready_runs
    batch_calls = []

    def collect(*args, limit=1, **kwargs):
        ready = original(*args, limit=limit, **kwargs)
        if limit == 2 and ready and behavior.get('enough', True):
            return [*ready, (state, candidate, {})]
        return ready

    def publish(*args, **kwargs):
        batch_calls.append(kwargs)
        if behavior.get('batch_error'):
            raise publisher.PublishBlocked('候選在批次准入時漂移')
        if behavior.get('batch_failure'):
            return {'status': 'FAILED_RECOVERED', 'published': 0}
        ids = [runs['new'][0]['run_id'], run_id]
        commit = 'b' * 40
        ledger = publisher._load_ledger(state_root)
        for rid in ids:
            ledger['published_runs'].append({'run_id': rid, 'article_ids': [rid],
                'published_at': '2026-10-25T12:00:00+08:00', 'version': '0.3.0', 'commit_sha': commit})
        publisher._atomic_write_json(publisher._ledger_path(state_root), ledger)
        return {'status': 'PUBLISHED', 'pushed': True, 'run_ids': ids,
                'article_ids': ids, 'commit_sha': commit, 'version': '0.3.0'}

    monkeypatch.setattr(publisher, 'collect_ready_runs', collect)
    monkeypatch.setattr(publisher, 'publish_ready_runs', publish)
    return fixture, batch_calls, publish


def _preferred_tick(fixture, **kwargs):
    repo, queue, state_root, *_ = fixture
    return publisher.publish_continuous_tick.__wrapped__(repo, queue, state_root,
        max_runs=1, push=True, prefer_new_batch_size=2, **kwargs)


def test_preferred_new_batch_publishes_two_then_yields_to_next_lane(tmp_path, monkeypatch):
    fixture, calls, _ = _batch_fixture(tmp_path, monkeypatch)
    first = _preferred_tick(fixture)
    assert first['status'] == 'PUBLISHED' and first['daily_articles'] == 2
    assert len(first['run_ids']) == 2 and fixture[4] == []
    assert len(calls) == 1 and calls[0]['max_runs'] == 2
    assert calls[0]['batch_day'] == '2026-10-25'
    assert calls[0]['run_tests'] and calls[0]['release_gate'] and calls[0]['push']
    assert _preferred_tick(fixture)['lane'] == 'i18n-new'
    assert len(calls) == 1


def test_batch_preference_off_still_publishes_only_one(tmp_path, monkeypatch):
    fixture, calls, _ = _batch_fixture(tmp_path, monkeypatch)
    assert _tick(fixture)['daily_articles'] == 1
    assert calls == [] and len(fixture[4]) == 1


@pytest.mark.parametrize('reason', ['insufficient', 'quota_one'])
def test_preferred_batch_falls_back_only_before_attempt(tmp_path, monkeypatch, reason):
    fixture, calls, _ = _batch_fixture(tmp_path, monkeypatch)
    if reason == 'insufficient':
        fixture[5]['enough'] = False
    else:
        monkeypatch.setattr(publisher, 'CONTINUOUS_DAILY_MAX_ARTICLES', 1)
    result = _preferred_tick(fixture)
    assert result['daily_articles'] == 1
    assert calls == [] and len(fixture[4]) == 1


@pytest.mark.parametrize('reason', ['batch_failure', 'batch_error'])
def test_failed_preferred_batch_never_republishes_single_in_same_tick(tmp_path, monkeypatch, reason):
    fixture, calls, _ = _batch_fixture(tmp_path, monkeypatch)
    fixture[5][reason] = True
    if reason == 'batch_error':
        with pytest.raises(publisher.PublishBlocked, match='漂移'):
            _preferred_tick(fixture)
    else:
        assert _preferred_tick(fixture)['status'] == 'FAILED_RECOVERED'
    assert len(calls) == 1 and fixture[4] == []
    assert _preferred_tick(fixture)['lane'] == 'i18n-new'


@pytest.mark.parametrize('corruption', ['missing_owner', 'duplicate_run', 'wrong_commit', 'wrong_article', 'wrong_version', 'swapped_owners'])
def test_preferred_batch_readback_checks_both_exact_owners(tmp_path, monkeypatch, corruption):
    fixture, _calls, publish = _batch_fixture(tmp_path, monkeypatch)
    def corrupt(*args, **kwargs):
        result = publish(*args, **kwargs)
        if corruption == 'duplicate_run':
            result['run_ids'] = result['run_ids'][:1] * 2
        else:
            ledger = publisher._load_ledger(fixture[2])
            if corruption == 'missing_owner':
                ledger['published_runs'].pop()
            elif corruption == 'wrong_commit':
                ledger['published_runs'][1]['commit_sha'] = 'c' * 40
            elif corruption == 'wrong_article':
                ledger['published_runs'][1]['article_ids'] = ['wrong']
            elif corruption == 'swapped_owners':
                left, right = ledger['published_runs']
                left['article_ids'], right['article_ids'] = right['article_ids'], left['article_ids']
            else:
                ledger['published_runs'][1]['version'] = '0.3.98'
            publisher._atomic_write_json(publisher._ledger_path(fixture[2]), ledger)
        return result
    monkeypatch.setattr(publisher, 'publish_ready_runs', corrupt)
    result = _preferred_tick(fixture)
    assert result['status'] == 'OPERATOR_REQUIRED'
    assert (fixture[2] / 'continuous-publisher-stop.json').exists()
    assert fixture[4] == []


def test_preferred_batch_joins_actual_owner_without_zipping_sorted_article_ids(tmp_path, monkeypatch):
    fixture, _calls, publish = _batch_fixture(tmp_path, monkeypatch)
    def reordered(*args, **kwargs):
        result = publish(*args, **kwargs)
        result['run_ids'] = list(reversed(result['run_ids']))
        result['article_ids'] = sorted(result['article_ids'])
        return result
    monkeypatch.setattr(publisher, 'publish_ready_runs', reordered)
    assert _preferred_tick(fixture)['status'] == 'PUBLISHED'


def test_preferred_batch_readback_ignores_unrelated_invalid_state(tmp_path, monkeypatch):
    fixture, _calls, _publish = _batch_fixture(tmp_path, monkeypatch)
    (fixture[1] / 'runs' / 'unrelated.json').write_text('{invalid')
    assert _preferred_tick(fixture)['status'] == 'PUBLISHED'


def test_preferred_batch_readback_uses_completed_runs_not_peek_reservation(tmp_path, monkeypatch):
    fixture, _calls, publish = _batch_fixture(tmp_path, monkeypatch)
    def reselected(*args, **kwargs):
        result = publish(*args, **kwargs)
        ledger = publisher._load_ledger(fixture[2])
        actual_ids = []
        for entry in ledger['published_runs']:
            rid = entry['run_id'] + '-reselected'
            directory = fixture[1] / 'new' / rid
            directory.mkdir()
            (directory / 'candidate.json').write_text(json.dumps({'run_id': rid, 'articles': [{'id': entry['article_ids'][0]}]}))
            (fixture[1] / 'runs' / (rid + '.json')).write_text(json.dumps({'run_id': rid, 'lane': 'new', 'run_dir': str(directory)}))
            entry['run_id'] = rid
            actual_ids.append(rid)
        publisher._atomic_write_json(publisher._ledger_path(fixture[2]), ledger)
        result['run_ids'] = actual_ids
        return result
    monkeypatch.setattr(publisher, 'publish_ready_runs', reselected)
    result = _preferred_tick(fixture)
    assert result['status'] == 'PUBLISHED'
    assert all(rid.endswith('-reselected') for rid in result['run_ids'])


@pytest.mark.parametrize('name,value', [('run_tests', False), ('release_gate', False), ('dry_run', True), ('pages_enabled', True)])
def test_preferred_batch_rejects_weakened_gates(tmp_path, monkeypatch, name, value):
    fixture, calls, _ = _batch_fixture(tmp_path, monkeypatch)
    with pytest.raises(publisher.PublishBlocked):
        _preferred_tick(fixture, **{name: value})
    assert calls == [] and fixture[4] == []


def test_preferred_batch_retains_stop_and_unknown_push_locks(tmp_path, monkeypatch):
    fixture, calls, _ = _batch_fixture(tmp_path, monkeypatch)
    def unknown(*_):
        raise publisher.PublishBlocked('unknown push')
    monkeypatch.setattr(publisher, '_assert_no_unresolved_push', unknown)
    with pytest.raises(publisher.PublishBlocked, match='unknown push'):
        _preferred_tick(fixture)
    assert calls == [] and fixture[4] == []
    monkeypatch.setattr(publisher, '_continuous_preexisting_stop', lambda *_: {'status': 'OPERATOR_REQUIRED'})
    assert _preferred_tick(fixture)['status'] == 'OPERATOR_REQUIRED'
    assert calls == []


@pytest.mark.parametrize('argv', [
    ['--prefer-new-batch-size', '1'], ['--prefer-new-batch-size', '10'],
    ['--prefer-new-batch-size', '02'],
    ['--prefer-new-batch-size'],
    ['--prefer-new-batch-size', '2', '--prefer-new-batch-size=2'],
])
def test_preferred_batch_parser_rejects_invalid_or_repeated_flag(monkeypatch, argv):
    monkeypatch.setattr(sys, 'argv', ['publisher', *argv])
    with pytest.raises(SystemExit):
        publisher.parse_args()


@pytest.mark.parametrize('extra', [[], ['--continuous-tick', '--include-rewrites', '--push', '--skip-tests'],
    ['--continuous-tick', '--include-rewrites', '--push', '--pages-deploy'],
    ['--continuous-tick', '--include-rewrites', '--push', '--deployment-preflight']])
def test_preferred_batch_cli_requires_full_continuous_contract(monkeypatch, extra):
    monkeypatch.setattr(sys, 'argv', ['publisher', '--max-runs', '1', '--prefer-new-batch-size', '2', *extra])
    with pytest.raises(SystemExit):
        publisher.main.__wrapped__()


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

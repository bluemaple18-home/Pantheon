from __future__ import annotations

import hashlib
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts.agy_gemini_coordinator import build_campaign_dry_run_workset, cycle_once, read_run_state, register_run, seed_legacy_rewrite_runs, seed_new_matrix_runs
from scripts.agy_gemini_outbox import ExternalJobPending, consume_external_response, create_external_request


def _article_brief_v2(run_id: str, article_id: str) -> dict[str, object]:
    return {
        "version": "ArticleBriefV2", "run_id": run_id,
        "article_identity": {"id": article_id, "canonical_path": f"/{article_id.lower()}/"},
        "reader_question": "這個概念應如何用在選擇上？", "target_reader": "正在比較選項的讀者",
        "search_intent": "informational", "thesis": "先查證事實，再判斷適用性。",
        "reader_outcome": "讀者能列出下一步。", "scope": "一般資訊整理",
        "anti_goals": ["不替讀者決定"], "evidence_policy": "cite-verifiable-claims", "risk_class": "medium",
    }


def _campaign_item(source_kind: str, article_id: str, campaign_version: str = "apf-002-v1") -> dict[str, str]:
    lane = "new" if source_kind == "matrix" else "rewrite"
    return {
        "source_kind": source_kind, "article_id": article_id, "locale": "zh-TW",
        "campaign_version": campaign_version,
        "work_id": coordinator._campaign_work_id(source_kind, article_id, "zh-TW", campaign_version),
        "lane": lane, "reason": "fixture",
    }


def _publication_policy(*, canonical: str, change_type: str) -> dict[str, object]:
    identity = coordinator.pipeline.load_article_publication_policy()["identity"]
    return {
        "policyVersion": coordinator.pipeline.publication_policy_version(),
        "canonical": canonical,
        "author": {"name": identity["author_name"], "url": identity["author_url"], "id": identity["author_id"]},
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": {"mode": "cultural_reflection", "sources": [], "disclosure": "本文屬文化脈絡與反思整理，不主張可驗證的預測結果。"},
        "published": "2026-07-23", "modified": "2026-07-23", "changeType": change_type,
    }


def _long_paragraph(seed: str) -> str:
    return (seed + "再核對一項具體資料，避免把通用描述當成個人結論。" * 8)[:108]


def _valid_campaign_candidate(brief: dict[str, object]) -> dict[str, object]:
    article_id = str(brief["article_identity"]["id"])
    run_id = str(brief["run_id"])
    keyword = "測試關鍵字" if article_id.startswith("NEW") else "舊文測試"
    paragraphs = [_long_paragraph(f"{keyword}在第{index + 1}個工作場景中，不能代替個人判斷，先整理事實、限制與可行選項。") for index in range(15)]
    if article_id.startswith("NEW"):
        article = {
            "id": article_id, "section": "mbti", "product": "personality", "slug": article_id.lower(),
            "serial": "personality-9999", "urlSlug": f"{article_id.lower()}-9999", "primaryKeyword": "測試關鍵字",
            "secondaryKeywords": ["具體場景", "通用觀察"], "title": "測試關鍵字是什麼？用生活場景理解限制與選擇",
            "description": "測試關鍵字適合整理具體情境、可觀察行動與使用限制；本文只提供通用理解，不替個人下結論，也不承諾任何結果，仍需回到現況判斷與實際資料再做選擇。",
            "answer": "測試關鍵字提供通用觀察，不能替個人下結論。", "tags": ["AEO", "GEO", "Pantheon", "SEO", "公開文章", "繁體中文", "通用知識", "人格", "自我理解"],
            "published": "2026-07-23", "updated": "2026-07-23",
            "faq": [{"question": "能直接判定結果嗎？", "answer": "不能，仍要回到實際情境與行動。"}, {"question": "應該先看什麼？", "answer": "先分開記錄事實、推測與期待。"}, {"question": "什麼時候不適用？", "answer": "需要專業判斷時不應只靠這篇文章。"}],
            "bodySections": [{"heading": f"測試關鍵字的觀察角度 {index + 1}", "paragraphs": paragraphs[index * 3 : index * 3 + 3]} for index in range(5)],
            "publicationPolicy": _publication_policy(canonical=f"https://www.mysticpantheon.com/articles/personality/{article_id.lower()}-9999", change_type="created"),
        }
        return {"schema_version": 1, "run_id": run_id, "mode": "create", "articles": [article]}
    body_sections = [{"heading": f"具體判讀角度 {index + 1}", "paragraphs": paragraphs[index * 3 : index * 3 + 3]} for index in range(5)]
    article = {
        "article_id": article_id,
        "identity": {"id": article_id, "product": "astrology", "category": "astrology", "serial": "astrology-0001", "slug": article_id.lower(), "primaryKeyword": "舊文測試", "title": "舊文測試標題"},
        "current_body_sha256": coordinator.pipeline.body_sha256([{"heading": "舊內容", "paragraphs": [_long_paragraph("舊文原始內容。")] }]),
        "bodySections": body_sections,
        "publicationPolicy": _publication_policy(canonical=f"https://www.mysticpantheon.com/articles/astrology/{article_id.lower()}", change_type="substantive_rewrite"),
    }
    return {"schema_version": 1, "run_id": run_id, "mode": "rewrite_existing_body", "articles": [article]}


def _clean_review(brief: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    article = candidate["articles"][0]
    article_id = str(article.get("id", article.get("article_id")))
    return {"schema_version": 1, "run_id": brief["run_id"], "articles": [{"article_id": article_id, "candidate_sha256": coordinator.pipeline.article_sha256(article), "verdict": "APPROVE", "hard_failure": False, "findings": []}]}


def test_campaign_editorial_workset_executes_new_and_rewrite_with_real_contracts(tmp_path: Path) -> None:
    calls = {"brief": 0, "writer": 0, "reviewer": 0}
    workset = {"schema_version": 1, "campaign_version": "apf-002-v1", "lanes": ["new", "rewrite"], "items": [_campaign_item("matrix", "NEW-001"), _campaign_item("legacy", "LEGACY-001")], "summary": {}}

    def make_brief(item: dict[str, object]) -> dict[str, object]:
        calls["brief"] += 1
        return _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"]))

    def write_candidate(brief: dict[str, object]) -> dict[str, object]:
        calls["writer"] += 1
        return _valid_campaign_candidate(brief)

    def write_review(brief: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
        calls["reviewer"] += 1
        return _clean_review(brief, candidate)

    first = coordinator.execute_campaign_editorial_workset(workset, tmp_path / "runs", brief_factory=make_brief, writer=write_candidate, reviewer=write_review)
    second = coordinator.execute_campaign_editorial_workset(workset, tmp_path / "runs", brief_factory=make_brief, writer=write_candidate, reviewer=write_review)

    assert first["work_ids"] == second["work_ids"] == [item["work_id"] for item in workset["items"]]
    assert calls == {"brief": 2, "writer": 2, "reviewer": 2}


def test_campaign_editorial_work_item_validates_before_persisting_and_retries(tmp_path: Path) -> None:
    item = _campaign_item("matrix", "NEW-001")
    attempts = 0

    def writer(brief: dict[str, object]) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        return {"schema_version": 1} if attempts == 1 else _valid_campaign_candidate(brief)

    with pytest.raises(ValueError):
        coordinator.execute_campaign_editorial_work_item(item, tmp_path / "run", brief_factory=lambda _item: _article_brief_v2("new-run-001", "NEW-001"), writer=writer, reviewer=_clean_review)
    assert not (tmp_path / "run" / "editorial-vnext" / "legacy-candidate.json").exists()
    coordinator.execute_campaign_editorial_work_item(item, tmp_path / "run", brief_factory=lambda _item: _article_brief_v2("new-run-001", "NEW-001"), writer=writer, reviewer=_clean_review)
    assert attempts == 2


def test_campaign_editorial_work_item_fails_closed_for_blocking_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _campaign_item("legacy", "LEGACY-001")
    brief = _article_brief_v2("rewrite-run-001", "LEGACY-001")
    candidate = {"schema_version": 1, "run_id": "rewrite-run-001", "mode": "rewrite_existing_body", "articles": [{"article_id": "LEGACY-001"}]}
    review = {"schema_version": 1, "run_id": "rewrite-run-001", "articles": [{"article_id": "LEGACY-001", "candidate_sha256": "a", "verdict": "REJECT", "findings": [{"code": "blocked", "message": "fixture"}]}]}
    monkeypatch.setattr(coordinator.pipeline, "validate_candidate", lambda _value: None)
    monkeypatch.setattr(coordinator.pipeline, "validate_review", lambda _value, _articles: None)

    with pytest.raises(ValueError, match="blocking findings"):
        coordinator.execute_campaign_editorial_work_item(item, tmp_path / "run", brief_factory=lambda _item: brief, writer=lambda _brief: candidate, reviewer=lambda _brief, _candidate: review)


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


def test_formal_coordinator_rejects_manifest_drift_before_lock_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-coordinator",
        runtime_digest="1" * 64,
        generation="generation-coordinator",
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
        "PANTHEON_RUNTIME_SERVICE_LABEL",
        "com.pantheon.agy-gemini-coordinator",
    )
    manifest_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(runtime_manifest.RuntimeManifestError):
        cycle_once(queue, repo_root=actor)

    assert not (queue / "coordinator.lock").exists()


def test_resume_locale_plan_validation_failure_starts_fresh_attempt(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "private-runs" / "run-locale-plan-failed"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-locale-plan-failed")
    state = register_run(run_dir, queue_root)
    state.update(
        {
            "status": "failed",
            "last_job_id": "terminal-locale-plan-job",
            "error_type": "LocalePlanValidationError",
        }
    )
    coordinator._write_state(queue_root, state)

    resumed = coordinator.resume_run(run_dir, queue_root)

    assert resumed["status"] == "active"
    assert "last_job_id" not in resumed
    assert "error_type" not in resumed


def test_resume_other_failure_preserves_existing_job_lineage(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "run-provider-failed"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-provider-failed")
    state = register_run(run_dir, queue_root)
    state.update(
        {
            "status": "failed",
            "last_job_id": "terminal-provider-job",
            "error_type": "V4BrokerFailure",
        }
    )
    coordinator._write_state(queue_root, state)

    resumed = coordinator.resume_run(run_dir, queue_root)

    assert resumed["status"] == "active"
    assert resumed["last_job_id"] == "terminal-provider-job"
    assert "error_type" not in resumed


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


def test_cycle_exact_run_ids_never_advances_unlisted_active_run(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    for run_id in ("old-active-run", "target-ja-run"):
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)

    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root, **_kwargs: {"status": "idle"},
        exact_run_ids=["target-ja-run"],
    )

    assert advanced == ["target-ja-run"]
    assert summary["active"] == 1
    assert read_run_state(tmp_path / "runs" / "old-active-run", queue_root)["status"] == "active"


def test_cycle_exact_run_ids_processed_runner_keeps_unlisted_run_unchanged(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    for index, run_id in enumerate(("old-active-run", "target-ja-run")):
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)
        state_path = coordinator._state_path(run_id, queue_root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["updated_at"] = f"2026-08-05T10:0{index}:00+08:00"
        state_path.write_text(json.dumps(state), encoding="utf-8")

    unlisted_state_path = coordinator._state_path("old-active-run", queue_root)
    unlisted_state_before = unlisted_state_path.read_bytes()
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root, **_kwargs: {
            "status": "processed",
            "job_id": "job-target-ja-run",
        },
        exact_run_ids=["target-ja-run"],
    )

    assert advanced == ["target-ja-run", "target-ja-run"]
    assert unlisted_state_path.read_bytes() == unlisted_state_before
    assert summary["runner"] == {
        "status": "processed",
        "job_id": "job-target-ja-run",
    }


def test_cycle_exact_run_ids_reject_duplicates_before_advancing(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "target-ja-run"
    _write_brief(run_dir, run_dir.name)
    register_run(run_dir, queue_root)

    with pytest.raises(ValueError, match="exact run ids must be unique"):
        cycle_once(
            queue_root,
            tick=lambda *_args: pytest.fail("duplicate selector must not advance"),
            exact_run_ids=[run_dir.name, run_dir.name],
        )


def test_cycle_exact_run_ids_continue_after_one_selected_run_is_terminal(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    for run_id in ("target-ja-run", "target-ko-run"):
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)
    completed_path = coordinator._state_path("target-ja-run", queue_root)
    completed = json.loads(completed_path.read_text(encoding="utf-8"))
    completed["status"] = "complete"
    completed_path.write_text(json.dumps(completed), encoding="utf-8")
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root, **_kwargs: {"status": "idle"},
        exact_run_ids=["target-ja-run", "target-ko-run"],
    )

    assert advanced == ["target-ko-run"]


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


def test_seed_failed_translation_replacements_is_bounded_per_i18n_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    failed_states = []
    for run_id, article_id in [
        ("i18n-new-base", "NEW-001"),
        ("i18n-new-later", "NEW-002"),
        ("i18n-rewrite-base", "LEGACY-001"),
        ("i18n-rewrite-later", "LEGACY-002"),
    ]:
        run_dir = queue_root / "translation-runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "mode": "translate_existing",
                    "articles": [{"source_article_id": article_id}],
                }
            ),
            encoding="utf-8",
        )
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "status": "failed",
            "error_type": "LocalePlanValidationError",
            "registered_at": f"2026-07-31T10:0{len(failed_states)}:00+08:00",
            "updated_at": f"2026-07-31T10:0{len(failed_states)}:00+08:00",
        }
        coordinator.atomic_write_json(
            coordinator._state_path(run_id, queue_root),
            state,
        )
        failed_states.append(state)

    calls: list[tuple[str, str]] = []

    def fake_enqueue(
        _repo_root: Path,
        selected_queue_root: Path,
        *,
        terminal_state: dict[str, object],
        recovery_reason: str,
    ) -> dict[str, str]:
        base_run_id = str(terminal_state["run_id"])
        replacement_run_id = f"{base_run_id}-replacement-01"
        calls.append((base_run_id, recovery_reason))
        replacement_run_dir = (
            selected_queue_root / "translation-runs" / replacement_run_id
        ).resolve()
        replacement_run_dir.mkdir(parents=True)
        base_brief = json.loads(
            (Path(str(terminal_state["run_dir"])) / "brief.json").read_text()
        )
        (replacement_run_dir / "brief.json").write_text(
            json.dumps({**base_brief, "run_id": replacement_run_id}),
            encoding="utf-8",
        )
        coordinator.atomic_write_json(
            coordinator._state_path(replacement_run_id, selected_queue_root),
            {
                "schema_version": 1,
                "run_id": replacement_run_id,
                "run_dir": str(replacement_run_dir),
                "status": "active",
                "replacement_of": base_run_id,
                "replacement_reason": recovery_reason,
            },
        )
        return {
            "run_id": replacement_run_id,
            "run_dir": str(replacement_run_dir),
            "state_path": str(
                coordinator._state_path(replacement_run_id, selected_queue_root)
            ),
        }

    monkeypatch.setattr(
        coordinator.multilingual,
        "enqueue_translation_replacement",
        fake_enqueue,
    )

    first = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids={"LEGACY-001", "LEGACY-002"},
    )
    second = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids={"LEGACY-001", "LEGACY-002"},
    )

    assert first == {
        "status": "seeded",
        "created": 2,
        "created_run_ids": [
            "i18n-new-base-replacement-01",
            "i18n-rewrite-base-replacement-01",
        ],
    }
    assert second == {
        "status": "idle",
        "created": 0,
        "created_run_ids": [],
    }
    assert calls == [
        ("i18n-new-base", "LOCALE_PLAN_VALIDATION"),
        ("i18n-rewrite-base", "LOCALE_PLAN_VALIDATION"),
    ]


def test_lane_cycle_reports_bounded_translation_replacement_seeding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    calls = 0

    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_ids",
        lambda _repo_root: {"LEGACY-001"},
    )

    def fake_seed(
        selected_repo_root: Path,
        selected_queue_root: Path,
        *,
        legacy_article_ids: set[str],
    ) -> dict[str, object]:
        nonlocal calls
        calls += 1
        assert selected_repo_root == repo_root.resolve()
        assert selected_queue_root == queue_root.resolve()
        assert legacy_article_ids == {"LEGACY-001"}
        return {
            "status": "seeded",
            "created": 1,
            "created_run_ids": ["i18n-new-base-replacement-01"],
        }

    monkeypatch.setattr(
        coordinator,
        "seed_failed_translation_replacements",
        fake_seed,
    )

    summary = cycle_once(
        queue_root,
        repo_root=repo_root,
        lane_mode=True,
        tick=lambda *_args: {"status": "complete"},
        process=lambda _root: {"status": "idle"},
    )

    assert calls == 1
    assert summary["translation_replacements"] == {
        "status": "seeded",
        "created": 1,
        "created_run_ids": ["i18n-new-base-replacement-01"],
    }


def test_failed_translation_replacement_skip_is_persisted_without_log_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_id = "i18n-new-source-drift"
    run_dir = queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "mode": "translate_existing",
                "articles": [{"source_article_id": "NEW-001"}],
            }
        ),
        encoding="utf-8",
    )
    coordinator.atomic_write_json(
        coordinator._state_path(run_id, queue_root),
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "status": "failed",
            "error_type": "LocalePlanValidationError",
            "registered_at": "2026-07-31T10:00:00+08:00",
            "updated_at": "2026-07-31T10:00:00+08:00",
        },
    )
    calls = 0

    def fail_source_drift(*_args: object, **_kwargs: object) -> dict[str, str]:
        nonlocal calls
        calls += 1
        raise ValueError("translation replacement source drift")

    monkeypatch.setattr(
        coordinator.multilingual,
        "enqueue_translation_replacement",
        fail_source_drift,
    )

    first = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids=set(),
    )
    second = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids=set(),
    )

    assert first == {
        "status": "idle",
        "created": 0,
        "created_run_ids": [],
        "skipped": [{"run_id": run_id, "reason": "SOURCE_DRIFT"}],
    }
    assert second == {
        "status": "idle",
        "created": 0,
        "created_run_ids": [],
    }
    assert calls == 1
    decision = json.loads(
        coordinator._translation_replacement_decision_path(
            queue_root,
            run_id,
        ).read_text()
    )
    assert decision["run_id"] == run_id
    assert decision["status"] == "skipped"
    assert decision["reason"] == "SOURCE_DRIFT"


@pytest.mark.parametrize(
    ("error_type", "failure_category", "transport_attempts", "expected"),
    [
        ("LocalePlanValidationError", None, None, "LOCALE_PLAN_VALIDATION"),
        ("GeminiApiFailure", "NETWORK", 3, "NETWORK"),
        ("V4BrokerFailure", "SCHEMA_INVALID_PAYLOAD", 3, "SCHEMA_INVALID_PAYLOAD"),
        ("GeminiApiFailure", "PROVIDER_UNAVAILABLE", 3, "PROVIDER_UNAVAILABLE"),
        ("GeminiApiFailure", "NETWORK", 2, None),
        ("GeminiApiFailure", "AUTH", 3, None),
        ("GeminiApiFailure", "QUOTA", 3, None),
        ("CandidateValidationError", None, None, None),
    ],
)
def test_translation_replacement_reason_is_closed_and_requires_exhaustion(
    tmp_path: Path,
    error_type: str,
    failure_category: str | None,
    transport_attempts: int | None,
    expected: str | None,
) -> None:
    state: dict[str, object] = {
        "status": "failed",
        "run_id": "translation-base",
        "error_type": error_type,
    }
    if failure_category is not None:
        state["failure_category"] = failure_category
    if transport_attempts is not None:
        state["transport_attempts"] = transport_attempts

    assert coordinator._translation_replacement_reason(tmp_path, state) == expected


def test_cycle_persists_closed_external_failure_recovery_metadata(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "runs" / "run-network-exhausted"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-network-exhausted")
    register_run(run_dir, queue_root)

    def fail_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise coordinator.ExternalJobFailed(
            "public-job-network-exhausted",
            "GeminiApiFailure",
            "API_TIMEOUT",
            failure_category="NETWORK",
            transport_attempt=2,
        )

    summary = cycle_once(
        queue_root,
        tick=fail_tick,
        process=lambda _root: {"status": "idle"},
    )
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["status"] == "failed"
    assert state["failure_category"] == "NETWORK"
    assert state["transport_attempts"] == 3


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


def test_campaign_dry_run_workset_is_stable_and_side_effect_free(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    repo_root.mkdir()
    records = [
        {"id": "LEGACY-001", "serial": "tarot-001", "path": "articles/tarot/tarot-001"},
        {"id": "LEGACY-002", "serial": "tarot-002", "path": "articles/tarot/tarot-002"},
    ]
    inventory = {record["id"]: {"id": record["id"], "record": record} for record in records}
    monkeypatch.setattr(
        coordinator.pipeline,
        "build_matrix_backlog",
        lambda _repo: [
            {"id": "NEW-001", "primaryKeyword": "新主題一"},
            {"id": "NEW-002", "primaryKeyword": "新主題二"},
        ],
    )
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: records)
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: inventory)
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: {"unattempted": 1, "active_or_incomplete": 1, "released": 0},
    )

    new_run = tmp_path / "new-run"
    rewrite_run = tmp_path / "rewrite-run"
    translation_run = tmp_path / "translation-run"
    for run_dir, run_id, brief in (
        (new_run, "new-run", {"mode": "create", "articles": [{"target": {"id": "NEW-002"}}]}),
        (rewrite_run, "rewrite-run", {"mode": "rewrite_existing_body", "articles": [{"article_id": "LEGACY-002"}]}),
        (translation_run, "translation-run", {"mode": "translate_existing", "articles": [{"source_article_id": "NEW-001", "locale": "en"}]}),
    ):
        run_dir.mkdir()
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **brief}),
            encoding="utf-8",
        )
        state_path = queue_root / "runs" / f"{run_id}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "status": "active"}), encoding="utf-8")

    before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    first = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="apf-001-v1")
    second = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="apf-001-v1")
    next_campaign = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="apf-001-v2")
    after = {str(path.relative_to(tmp_path)): path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}

    assert json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(second, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert after == before
    assert [item["lane"] for item in first["items"]] == [
        "new",
        "rewrite",
        "rewrite",
        "i18n-new",
        "i18n-new",
        "i18n-new",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
    ]
    assert {(item["article_id"], item["locale"]) for item in first["items"]} == {
        ("NEW-001", "zh-TW"),
        ("LEGACY-001", "zh-TW"),
        ("LEGACY-002", "zh-TW"),
        ("NEW-001", "en"),
        ("NEW-001", "ja"),
        ("NEW-001", "ko"),
        ("LEGACY-001", "en"),
        ("LEGACY-001", "ja"),
        ("LEGACY-001", "ko"),
        ("LEGACY-002", "en"),
        ("LEGACY-002", "ja"),
        ("LEGACY-002", "ko"),
    }
    assert len({item["work_id"] for item in first["items"]}) == len(first["items"])
    assert all({"source_kind", "article_id", "locale", "campaign_version", "work_id", "lane", "reason"} <= set(item) for item in first["items"])
    assert {item["work_id"] for item in first["items"]}.isdisjoint({item["work_id"] for item in next_campaign["items"]})


def test_campaign_dry_run_dedupes_rewrite_and_translation_by_campaign_version(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    repo_root.mkdir()
    record = {"id": "LEGACY-001", "serial": "tarot-001", "path": "articles/tarot/tarot-001"}
    monkeypatch.setattr(coordinator.pipeline, "build_matrix_backlog", lambda _repo: [])
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: {"LEGACY-001": {"id": "LEGACY-001", "record": record}})
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: {"unattempted": 1, "active_or_incomplete": 0, "released": 0},
    )

    def register_campaign_run(run_id: str, brief: dict[str, object]) -> None:
        run_dir = tmp_path / run_id
        run_dir.mkdir()
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **brief}),
            encoding="utf-8",
        )
        state_path = queue_root / "runs" / f"{run_id}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "status": "completed"}), encoding="utf-8")

    register_campaign_run(
        "old-rewrite",
        {"mode": "rewrite_existing_body", "campaign_version": "rewrite-v0", "articles": [{"article_id": "LEGACY-001"}]},
    )
    register_campaign_run(
        "old-translation",
        {"mode": "translate_existing", "campaign_version": "rewrite-v0", "articles": [{"source_article_id": "LEGACY-001", "locale": "en"}]},
    )

    first = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version=" rewrite-v1 ", locales=("en", "ja"))
    assert first["campaign_version"] == "rewrite-v1"
    assert [(item["lane"], item["locale"]) for item in first["items"]] == [("rewrite", "zh-TW"), ("i18n-rewrite", "en"), ("i18n-rewrite", "ja")]

    register_campaign_run(
        "same-rewrite",
        {"mode": "rewrite_existing_body", "campaign_version": "rewrite-v1", "articles": [{"article_id": "LEGACY-001"}]},
    )
    register_campaign_run(
        "same-translation",
        {"mode": "translate_existing", "campaign_version": "rewrite-v1", "articles": [{"source_article_id": "LEGACY-001", "locale": "ja"}]},
    )
    same_campaign = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="rewrite-v1", locales=("en", "ja"))
    assert same_campaign["items"] == []

    next_campaign = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="rewrite-v2", locales=("en", "ja"))
    assert [(item["lane"], item["locale"]) for item in next_campaign["items"]] == [("rewrite", "zh-TW"), ("i18n-rewrite", "en"), ("i18n-rewrite", "ja")]
    with pytest.raises(ValueError, match="campaign version"):
        build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="rewrite-v1\nnext")


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
        "slug": "yongshen-meaning",
        "urlSlug": "fortune-0039",
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
    assert brief["articles"][0]["identity"]["slug"] == "fortune-0039"
    assert brief["articles"][0]["immutable_fields"]["slug"] == "yongshen-meaning"
    assert len(list((queue_root / "runs").glob("*.json"))) == 1


def test_seed_legacy_rewrite_runs_preserves_orphan_state_and_uses_retry_lineage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    record = {
        "id": "LEGACY-001",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-001",
        "slug": "yongshen-meaning",
        "urlSlug": "fortune-0039",
        "primaryKeyword": "塔羅舊文一",
        "title": "塔羅舊文一",
        "description": "描述一",
        "answer": "答案一",
        "faq": [{"question": "問一", "answer": "答一"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-001",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    inventory = {
        "LEGACY-001": {
            "id": "LEGACY-001",
            "record": record,
            "canonicalPath": "/articles/tarot/tarot-001",
            "currentBody": current_body,
            "published": "2026-01-01",
            "updated": "2026-01-01",
        }
    }
    base_run_id = "legacy-auto-sweep-v1-tarot-001-legacy-001"
    orphan_state_path = coordinator._state_path(base_run_id, queue_root)
    orphan_state_path.parent.mkdir(parents=True)
    orphan_state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": base_run_id,
                "run_dir": str(tmp_path / "removed-worktree" / base_run_id),
                "status": "active",
            }
        ),
        encoding="utf-8",
    )
    orphan_state_before = orphan_state_path.read_bytes()
    preserved_base_run_dir = run_root / base_run_id
    preserved_base_run_dir.mkdir(parents=True)
    preserved_marker = preserved_base_run_dir / "preserve.txt"
    preserved_marker.write_text("failed historical seed", encoding="utf-8")

    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: inventory)

    summary = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=1,
        source_commit="a" * 40,
    )

    retry_run_id = f"{base_run_id}-retry-01"
    assert summary["status"] == "seeded"
    assert summary["created_run_ids"] == [retry_run_id]
    assert orphan_state_path.read_bytes() == orphan_state_before
    assert preserved_marker.read_text(encoding="utf-8") == "failed historical seed"
    retry_brief = json.loads((run_root / retry_run_id / "brief.json").read_text(encoding="utf-8"))
    assert retry_brief["run_id"] == retry_run_id
    assert read_run_state(run_root / retry_run_id, queue_root)["run_id"] == retry_run_id


def test_next_legacy_rewrite_run_id_skips_existing_retry_directory(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    base_run_id = "legacy-auto-sweep-v1-tarot-001-legacy-001"
    base_state_path = coordinator._state_path(base_run_id, queue_root)
    base_state_path.parent.mkdir(parents=True)
    base_state_path.write_text("{}", encoding="utf-8")
    retry_dir = run_root / f"{base_run_id}-retry-01"
    retry_dir.mkdir(parents=True)
    marker = retry_dir / "preserve.txt"
    marker.write_text("historical", encoding="utf-8")

    selected = coordinator._next_legacy_rewrite_run_id(run_root, queue_root, base_run_id)

    assert selected == f"{base_run_id}-retry-02"
    assert marker.read_text(encoding="utf-8") == "historical"


def test_seed_legacy_rewrite_runs_advances_past_exhausted_clean_approvals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    current_body = [
        {
            "heading": "現況",
            "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"],
        }
    ]
    records: list[dict[str, object]] = []
    inventory: dict[str, dict[str, object]] = {}
    completed: dict[str, tuple[dict[str, object], dict[str, object], dict[str, object]]] = {}
    retry_before: dict[Path, bytes] = {}
    for index in range(1, 7):
        article_id = f"LEGACY-{index:03d}"
        serial = f"tarot-{index:03d}"
        record = {
            "id": article_id,
            "product": "tarot",
            "articleCategory": "tarot",
            "serial": serial,
            "slug": f"legacy-{index:03d}",
            "urlSlug": f"legacy-{index:03d}",
            "primaryKeyword": f"塔羅舊文{index}",
            "title": f"塔羅舊文{index}",
            "description": f"描述{index}",
            "answer": f"答案{index}",
            "faq": [{"question": f"問{index}", "answer": f"答{index}"}],
            "tags": ["塔羅"],
            "path": f"articles/tarot/{serial}",
        }
        records.append(record)
        inventory[article_id] = {
            "id": article_id,
            "record": record,
            "canonicalPath": f"/articles/tarot/{serial}",
            "currentBody": current_body,
            "published": "2026-01-01",
            "updated": "2026-01-01",
        }
        if index == 6:
            continue
        run_id = f"rewrite-approved-{index}"
        run_dir = tmp_path / "completed-runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "mode": "rewrite_existing_body",
                    "articles": [{"article_id": article_id}],
                }
            ),
            encoding="utf-8",
        )
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "complete",
        }
        candidate = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": article_id}],
        }
        review = {
            "schema_version": 1,
            "run_id": run_id,
            "articles": [
                {
                    "article_id": article_id,
                    "verdict": "APPROVE",
                    "hard_failure": False,
                    "findings": [],
                }
            ],
        }
        completed[run_id] = (state, candidate, review)
        state_path = queue_root / "runs" / f"{run_id}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        retry_path = coordinator.publisher._retry_path(state_root, "rewrite", run_id)
        retry_path.parent.mkdir(parents=True, exist_ok=True)
        retry_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "phase": "rewrite",
                    "run_id": run_id,
                    "attempts": coordinator.publisher.MAX_RETRY_ATTEMPTS,
                    "max_attempts": coordinator.publisher.MAX_RETRY_ATTEMPTS,
                    "next_eligible_at": "2026-07-30T12:20:00+08:00",
                    "eligibility": "exhausted",
                    "candidate_preserved": True,
                }
            ),
            encoding="utf-8",
        )
        retry_before[retry_path] = retry_path.read_bytes()

    monkeypatch.setattr(
        coordinator.publisher,
        "_load_completed_run",
        lambda path: completed[json.loads(path.read_text(encoding="utf-8"))["run_id"]],
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "_load_rewrite_brief",
        lambda run_dir, _run_id: json.loads(
            (run_dir / "brief.json").read_text(encoding="utf-8")
        ),
    )
    monkeypatch.setattr(
        coordinator.publisher.pipeline,
        "rewrite_aggregate_findings",
        lambda *_args, **_kwargs: ([], []),
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_records",
        lambda _repo: records,
    )
    monkeypatch.setattr(
        coordinator.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: inventory,
    )

    allowed_article_ids = {str(record["id"]) for record in records}
    backlog = coordinator.publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
        legacy_records=records,
    )
    ready = coordinator.publisher.collect_ready_rewrite_runs(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
    )
    result = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=1,
        source_commit="a" * 40,
    )

    assert backlog["clean_approve"] == 5
    assert ready == []
    assert result["status"] == "seeded"
    assert backlog["publish_ready"] == 0
    assert backlog["retry_exhausted"] == 5
    assert result["created_run_ids"] == [
        "legacy-auto-sweep-v1-tarot-006-legacy-006"
    ]
    assert len(list((queue_root / "runs").glob("*.json"))) == 6
    assert {
        path: path.read_bytes() for path in retry_before
    } == retry_before


@pytest.mark.parametrize("blocked_field", ["retry_deferred", "retry_invalid"])
def test_seed_legacy_rewrite_runs_surfaces_non_idle_retry_blocker(
    tmp_path: Path,
    monkeypatch,
    blocked_field: str,
) -> None:
    backlog = {
        "released": 0,
        "clean_approve": 1,
        "publish_ready": 0,
        "retry_deferred": 0,
        "retry_exhausted": 0,
        "retry_invalid": 0,
        "reject": 0,
        "active_or_incomplete": 0,
        "non_legacy": 0,
        "legacy_total": 2,
        "attempted": 1,
        "unattempted": 1,
        "clean_approve_run_ids": ["rewrite-blocked"],
        "unattempted_articles": [],
    }
    backlog[blocked_field] = 1
    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_records",
        lambda _repo: [{"id": "LEGACY-001"}],
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: backlog,
    )

    result = seed_legacy_rewrite_runs(
        tmp_path,
        tmp_path / "queue",
        tmp_path / "state",
        tmp_path / "private-runs",
        source_commit="a" * 40,
    )

    assert result["status"] == "rewrite_retry_blocked"
    assert result["created"] == 0
    assert result["backlog"][blocked_field] == 1
    assert not (tmp_path / "private-runs").exists()


def test_seed_legacy_rewrite_runs_surfaces_exhausted_terminal_when_inventory_is_done(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_records",
        lambda _repo: [{"id": "LEGACY-001"}],
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: {
            "clean_approve": 1,
            "publish_ready": 0,
            "retry_exhausted": 1,
            "unattempted": 0,
        },
    )

    result = seed_legacy_rewrite_runs(
        tmp_path,
        tmp_path / "queue",
        tmp_path / "state",
        tmp_path / "private-runs",
        source_commit="a" * 40,
    )

    assert result["status"] == "rewrite_retry_exhausted"
    assert result["created"] == 0
    assert result["backlog"]["retry_exhausted"] == 1


def test_terminalize_pending_cli_defaults_to_dry_run_without_mutation(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-terminalization"
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        run_id,
    )
    before = _file_snapshot(queue_root)

    completed = _operator_cli(run_dir, queue_root, request)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "status": "dry_run",
        "action": "terminalize_pending",
        "run_id": run_id,
        "lane": "i18n-rewrite",
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": "gemini-3.5-flash",
        "role": "writer",
        "transport_attempt": 1,
        "reason": "UNSUPPORTED_MODEL_CANARY_ABORT",
        "from": "outbox",
        "to": "archive",
    }
    assert _file_snapshot(queue_root) == before
    assert not list((queue_root / "archive").glob("*.json"))
    assert not list((queue_root / "operator-terminalizations").glob("*.json"))


def test_terminalize_pending_cli_supports_split_state_and_job_queue_roots(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-split-root"
    run_dir = tmp_path / "runs" / run_id
    state_root = tmp_path / "queue"
    job_root = state_root / "lanes" / "i18n-rewrite"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, state_root)
    request = create_external_request(
        job_root,
        namespace="operator-split-root",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator split root",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        transport_attempt=1,
    )

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending(str(request["job_id"]))

    assert coordinator._advance(
        state_root,
        state,
        pending_tick,
        job_queue_root=job_root,
    ) == "pending"
    before_state = coordinator._state_path(run_id, state_root).read_bytes()
    before_request = (
        job_root / "outbox" / f"{request['job_id']}.json"
    ).read_bytes()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_coordinator",
            "--queue-root",
            str(state_root),
            "terminalize-pending",
            str(run_dir),
            "--job-queue-root",
            str(job_root),
            "--lane",
            "i18n-rewrite",
            "--run-id",
            run_id,
            "--job-id",
            str(request["job_id"]),
            "--request-sha256",
            str(request["request_sha256"]),
            "--model",
            str(request["model"]),
            "--role",
            str(request["role"]),
            "--transport-attempt",
            "1",
            "--reason",
            "UNSUPPORTED_MODEL_CANARY_ABORT",
        ],
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["lane"] == "i18n-rewrite"
    assert coordinator._state_path(run_id, state_root).read_bytes() == before_state
    assert (
        job_root / "outbox" / f"{request['job_id']}.json"
    ).read_bytes() == before_request


def test_terminalize_pending_execute_writes_state_and_evidence_to_split_roots(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-split-execute"
    run_dir = tmp_path / "runs" / run_id
    state_root = tmp_path / "queue"
    job_root = state_root / "lanes" / "i18n-rewrite"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, state_root)
    request = create_external_request(
        job_root,
        namespace="operator-split-execute",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator split execute",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        transport_attempt=1,
    )

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending(str(request["job_id"]))

    assert coordinator._advance(
        state_root,
        state,
        pending_tick,
        job_queue_root=job_root,
    ) == "pending"
    result = coordinator.terminalize_pending_job(
        run_dir,
        state_root,
        job_queue_root=job_root,
        lane="i18n-rewrite",
        expected_run_id=run_id,
        job_id=str(request["job_id"]),
        request_sha256=str(request["request_sha256"]),
        model=str(request["model"]),
        role=str(request["role"]),
        transport_attempt=1,
        reason="UNSUPPORTED_MODEL_CANARY_ABORT",
        execute=True,
    )

    assert result["status"] == "terminalized"
    assert (job_root / "archive" / f"{request['job_id']}.json").is_file()
    assert (
        job_root / "operator-terminalizations" / f"{request['job_id']}.json"
    ).is_file()
    terminal_state = read_run_state(run_dir, state_root)
    assert terminal_state["status"] == "failed"
    assert terminal_state["operator_terminalization"]["lane"] == "i18n-rewrite"
    assert terminal_state["operator_terminalization"]["decision"] == (
        f"lanes/i18n-rewrite/operator-terminalizations/{request['job_id']}.json"
    )


def test_terminalize_pending_execute_preserves_request_and_marks_run_terminal(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-execute"
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        run_id,
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    request_bytes = outbox_path.read_bytes()

    result = _operator_terminalize(run_dir, queue_root, request)

    assert result["status"] == "terminalized"
    assert not outbox_path.exists()
    archive_path = queue_root / "archive" / f"{request['job_id']}.json"
    assert archive_path.read_bytes() == request_bytes
    decision = json.loads(
        (queue_root / "operator-terminalizations" / f"{request['job_id']}.json").read_text()
    )
    assert decision["status"] == "terminalized"
    assert decision["request_file_sha256"] == hashlib.sha256(request_bytes).hexdigest()
    assert decision["reason"] == "UNSUPPORTED_MODEL_CANARY_ABORT"
    terminal_state = read_run_state(run_dir, queue_root)
    assert terminal_state["status"] == "failed"
    assert terminal_state["error_type"] == "OperatorTerminalized"
    assert terminal_state["last_job_id"] == request["job_id"]
    assert terminal_state["operator_terminalization"] == {
        "decision": f"operator-terminalizations/{request['job_id']}.json",
        "job_id": request["job_id"],
        "lane": "i18n-rewrite",
        "model": "gemini-3.5-flash",
        "reason": "UNSUPPORTED_MODEL_CANARY_ABORT",
        "request_sha256": request["request_sha256"],
        "role": "writer",
        "transport_attempt": 1,
    }
    assert not (queue_root / "failed" / f"{request['job_id']}.json").exists()
    assert not (queue_root / "inbox" / f"{request['job_id']}.json").exists()


def test_terminalize_pending_cli_execute_wires_public_command(tmp_path: Path) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-cli-execute",
    )

    completed = _operator_cli(run_dir, queue_root, request, execute=True)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "terminalized"
    assert read_run_state(run_dir, queue_root)["status"] == "failed"


def _operator_pending_fixture(
    tmp_path: Path,
    run_id: str,
) -> tuple[Path, Path, dict[str, object]]:
    run_dir = tmp_path / "runs" / run_id
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, queue_root)
    request = create_external_request(
        queue_root,
        namespace="operator-fixture",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator fixture",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        transport_attempt=1,
    )

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending(str(request["job_id"]))

    assert coordinator._advance(queue_root, state, pending_tick) == "pending"
    return run_dir, queue_root, request


def _operator_terminalize(
    run_dir: Path,
    queue_root: Path,
    request: dict[str, object],
    **overrides: object,
) -> dict[str, object]:
    arguments: dict[str, object] = {
        "job_queue_root": queue_root,
        "lane": "i18n-rewrite",
        "expected_run_id": json.loads((run_dir / "brief.json").read_text())["run_id"],
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": request["model"],
        "role": request["role"],
        "transport_attempt": request.get("transport_attempt", 0),
        "reason": "UNSUPPORTED_MODEL_CANARY_ABORT",
        "execute": True,
    }
    arguments.update(overrides)
    return coordinator.terminalize_pending_job(
        run_dir,
        queue_root,
        **arguments,
    )


def _operator_cli(
    run_dir: Path,
    queue_root: Path,
    request: dict[str, object],
    *,
    execute: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "scripts.agy_gemini_coordinator",
        "--queue-root",
        str(queue_root),
        "terminalize-pending",
        str(run_dir),
        "--job-queue-root",
        str(queue_root),
        "--lane",
        "i18n-rewrite",
        "--run-id",
        str(json.loads((run_dir / "brief.json").read_text())["run_id"]),
        "--job-id",
        str(request["job_id"]),
        "--request-sha256",
        str(request["request_sha256"]),
        "--model",
        str(request["model"]),
        "--role",
        str(request["role"]),
        "--transport-attempt",
        str(request.get("transport_attempt", 0)),
        "--reason",
        "UNSUPPORTED_MODEL_CANARY_ABORT",
    ]
    if execute:
        command.append("--execute")
    return subprocess.run(
        command,
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_terminalize_pending_execute_is_byte_idempotent(tmp_path: Path) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-idempotent",
    )
    first = _operator_terminalize(run_dir, queue_root, request)
    after_first = _file_snapshot(queue_root)

    second = _operator_terminalize(run_dir, queue_root, request)

    assert first["status"] == "terminalized"
    assert second["status"] == "already_terminalized"
    assert _file_snapshot(queue_root) == after_first


@pytest.mark.parametrize(
    ("override", "value"),
    [
        ("expected_run_id", "different-run"),
        ("job_id", "0" * 40),
        ("request_sha256", "0" * 64),
        ("model", "gemini-2.5-flash-lite"),
        ("role", "reviewer"),
        ("transport_attempt", 2),
        ("reason", "UNBOUNDED_OPERATOR_REASON"),
    ],
)
def test_terminalize_pending_rejects_identity_mismatch_without_mutation(
    tmp_path: Path,
    override: str,
    value: object,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        f"synthetic-operator-mismatch-{override}",
    )
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError):
        _operator_terminalize(
            run_dir,
            queue_root,
            request,
            **{override: value},
        )

    assert _file_snapshot(queue_root) == before


def test_terminalize_pending_rejects_processing_job_without_operator_write(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-processing",
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    processing_path = queue_root / "processing" / outbox_path.name
    processing_path.parent.mkdir(parents=True)
    os.replace(outbox_path, processing_path)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="already processing"):
        _operator_terminalize(run_dir, queue_root, request)

    assert _file_snapshot(queue_root) == before
    assert not list((queue_root / "operator-terminalizations").glob("*.json"))


def test_terminalize_pending_recovers_after_state_write_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "synthetic-operator-recovery"
    run_dir, queue_root, request = _operator_pending_fixture(tmp_path, run_id)
    state_path = coordinator._state_path(run_id, queue_root)
    original_atomic_write = coordinator.atomic_write_json
    interrupted = False

    def interrupt_state_write(path: Path, payload: object) -> None:
        nonlocal interrupted
        if path == state_path and isinstance(payload, dict) and payload.get("status") == "failed":
            interrupted = True
            raise OSError("synthetic state write interruption")
        original_atomic_write(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", interrupt_state_write)
    with pytest.raises(OSError, match="synthetic state write interruption"):
        _operator_terminalize(run_dir, queue_root, request)
    assert interrupted is True
    assert read_run_state(run_dir, queue_root)["status"] == "active"
    assert (
        queue_root / "archive" / f"{request['job_id']}.json"
    ).is_file()
    decision_path = queue_root / "operator-terminalizations" / f"{request['job_id']}.json"
    assert json.loads(decision_path.read_text())["status"] == "terminalizing"

    monkeypatch.setattr(coordinator, "atomic_write_json", original_atomic_write)
    recovered = _operator_terminalize(run_dir, queue_root, request)

    assert recovered["status"] == "terminalized"
    assert read_run_state(run_dir, queue_root)["status"] == "failed"
    assert json.loads(decision_path.read_text())["status"] == "terminalized"


def test_terminalize_pending_rejects_existing_production_attempt_evidence(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-attempted",
    )
    attempt_path = queue_root / "production-attempts" / f"{request['job_id']}.attempt"
    attempt_path.parent.mkdir(parents=True)
    attempt_path.write_text("existing-attempt-evidence\n", encoding="utf-8")
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="production attempt evidence"):
        _operator_terminalize(run_dir, queue_root, request)

    assert _file_snapshot(queue_root) == before


def test_terminalize_pending_rejects_symlink_request(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-symlink",
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    preserved_path = tmp_path / "preserved-request.json"
    os.replace(outbox_path, preserved_path)
    outbox_path.symlink_to(preserved_path)
    state_before = coordinator._state_path(
        "synthetic-operator-symlink",
        queue_root,
    ).read_bytes()
    request_before = preserved_path.read_bytes()

    with pytest.raises(ValueError, match="regular request file"):
        _operator_terminalize(run_dir, queue_root, request)

    assert outbox_path.is_symlink()
    assert preserved_path.read_bytes() == request_before
    assert coordinator._state_path(
        "synthetic-operator-symlink",
        queue_root,
    ).read_bytes() == state_before
    assert not list((queue_root / "operator-terminalizations").glob("*.json"))


def test_terminalize_pending_rejects_corrupt_decision_schema_version(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-decision-version",
    )
    _operator_terminalize(run_dir, queue_root, request)
    decision_path = queue_root / "operator-terminalizations" / f"{request['job_id']}.json"
    decision = json.loads(decision_path.read_text())
    decision["schema_version"] = 2
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    state_before = read_run_state(run_dir, queue_root)

    with pytest.raises(ValueError, match="decision identity mismatch"):
        _operator_terminalize(run_dir, queue_root, request)

    assert read_run_state(run_dir, queue_root) == state_before
    assert not (tmp_path / "private-runs").exists()


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


def _prepare_exact_brief_stub(
    _repo_root: Path,
    _run_prefix: str,
    *,
    output_root: Path,
    exact_run_id: str,
    **_kwargs,
) -> list[Path]:
    run_dir = output_root / exact_run_id
    _write_brief(run_dir, exact_run_id)
    return [run_dir / "brief.json"]


def test_seed_new_matrix_runs_reserves_exact_replacement_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    repo_root.mkdir()
    monkeypatch.setattr(
        coordinator.pipeline,
        "build_matrix_backlog",
        lambda _repo: [{"id": "V2-MBTI-INTJ-WORK", "primaryKeyword": "INTJ 工作"}],
    )
    monkeypatch.setattr(
        coordinator.pipeline,
        "_matrix_targets",
        lambda _repo, _backlog: {
            "V2-MBTI-INTJ-WORK": {
                "id": "V2-MBTI-INTJ-WORK",
                "section": "mbti",
                "product": "mbti",
                "slug": "v2-mbti-intj-work",
                "serial": "mbti-0001",
                "urlSlug": "mbti-0001",
                "published": "2026-08-12",
                "updated": "2026-08-12",
                "primaryKeyword": "INTJ 工作",
            }
        },
    )
    monkeypatch.setattr(coordinator.pipeline, "compact_publication_policy", lambda: {})

    summary = seed_new_matrix_runs(
        repo_root,
        queue_root,
        run_root,
        exact_run_id=exact_run_id,
    )

    assert summary["created_run_ids"] == [exact_run_id]
    brief_path = run_root / exact_run_id / "brief.json"
    assert json.loads(brief_path.read_text(encoding="utf-8"))["run_id"] == exact_run_id
    state = json.loads(coordinator._state_path(exact_run_id, queue_root).read_text(encoding="utf-8"))
    assert state["status"] == "active"
    assert state["correlation_id"]
    assert "reservation_token" not in state
    assert not (run_root / ".exact-run-staging").exists()


@pytest.mark.parametrize("collision_source", ["run_root", "queue"])
def test_seed_new_matrix_runs_rejects_exact_identity_collision_before_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision_source: str,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    repo_root.mkdir()
    if collision_source == "run_root":
        (run_root / exact_run_id).mkdir(parents=True)
    else:
        state_path = coordinator._state_path(exact_run_id, queue_root)
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({"run_id": exact_run_id, "status": "complete"}), encoding="utf-8")
    prepare_calls = 0

    def fail_if_prepared(*_args, **_kwargs) -> list[Path]:
        nonlocal prepare_calls
        prepare_calls += 1
        return []

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fail_if_prepared)

    with pytest.raises(ValueError, match="exact run identity is already in use"):
        seed_new_matrix_runs(repo_root, queue_root, run_root, exact_run_id=exact_run_id)

    assert prepare_calls == 0
    assert not (run_root / exact_run_id / "brief.json").exists()


def test_seed_new_matrix_runs_rejects_unclosed_exact_identity_before_register(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", lambda *_args, **_kwargs: [])

    with pytest.raises(ValueError, match="exact run identity could not be allocated"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id="auto-new-v1-20260812-001-02",
        )

    assert not coordinator._state_path("auto-new-v1-20260812-001-02", queue_root).exists()


def test_seed_new_matrix_runs_cleans_owned_reservation_after_prepare_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    repo_root.mkdir()

    def fail_prepare(*_args, **_kwargs) -> list[Path]:
        raise RuntimeError("prepare failed")

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fail_prepare)

    with pytest.raises(RuntimeError, match="prepare failed"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert not coordinator._state_path(exact_run_id, queue_root).exists()
    assert not (run_root / exact_run_id / "brief.json").exists()
    assert not (queue_root / "outbox").exists()


def test_activate_run_reservation_rejects_ownership_mismatch(
    tmp_path: Path,
) -> None:
    run_id = "auto-new-v1-20260812-001-02"
    run_root = tmp_path / "private-runs"
    run_dir = run_root / run_id
    staging_run_dir = run_root / ".exact-run-staging" / "owned-token" / run_id
    queue_root = tmp_path / "queue"
    _write_brief(staging_run_dir, run_id)
    state_path = coordinator._reserve_run_identity(
        run_id,
        run_dir,
        queue_root,
        "owned-correlation",
        "owned-token",
    )
    reservation = json.loads(state_path.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="reservation ownership mismatch"):
        coordinator._activate_run_reservation(
            run_id,
            staging_run_dir,
            run_dir,
            queue_root,
            "owned-correlation",
            "foreign-token",
        )

    assert json.loads(state_path.read_text(encoding="utf-8")) == reservation
    assert not run_dir.exists()


def test_seed_new_matrix_runs_rejects_foreign_state_inserted_after_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    run_dir = run_root / exact_run_id
    state_path = coordinator._state_path(exact_run_id, queue_root)
    repo_root.mkdir()
    foreign_state = {
        "schema_version": 1,
        "run_id": exact_run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "complete",
        "correlation_id": "other",
    }
    foreign_bytes = json.dumps(foreign_state, indent=2).encode("utf-8") + b"\n"

    staging_paths: list[Path] = []

    def prepare_then_replace_reservation(*_args, **kwargs) -> list[Path]:
        staging_run_dir = Path(kwargs["output_root"]) / exact_run_id
        staging_paths.append(staging_run_dir)
        _write_brief(staging_run_dir, exact_run_id)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_bytes(foreign_bytes)
        return [staging_run_dir / "brief.json"]

    monkeypatch.setattr(
        coordinator.pipeline,
        "prepare_matrix_runs",
        prepare_then_replace_reservation,
    )

    with pytest.raises(ValueError, match="reservation ownership mismatch"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert state_path.read_bytes() == foreign_bytes
    assert not (run_root / exact_run_id / "brief.json").exists()
    assert staging_paths and all(not path.exists() for path in staging_paths)
    assert not (run_root / ".exact-run-staging").exists()
    assert not (queue_root / "outbox").exists()


def test_exact_run_cleanup_does_not_unlink_foreign_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    state_path = coordinator._state_path(exact_run_id, queue_root)
    repo_root.mkdir()
    foreign_bytes = b'{"run_id":"foreign","status":"complete"}\n'
    original_rename = coordinator.os.rename

    def interleave_cleanup(source, target) -> None:
        if str(target).endswith(".cleanup"):
            state_path.write_bytes(foreign_bytes)
        original_rename(source, target)

    monkeypatch.setattr(coordinator.os, "rename", interleave_cleanup)
    monkeypatch.setattr(
        coordinator.pipeline,
        "prepare_matrix_runs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("prepare failed")),
    )

    with pytest.raises(RuntimeError, match="prepare failed"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert state_path.read_bytes() == foreign_bytes
    assert not (run_root / exact_run_id).exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_activation_does_not_replace_interleaved_foreign_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    state_path = coordinator._state_path(exact_run_id, queue_root)
    repo_root.mkdir()
    foreign_bytes = b'{"run_id":"foreign","status":"complete"}\n'
    original_write = coordinator._write_json_exclusive

    def interleave_activation(path: Path, payload: object) -> None:
        if isinstance(payload, dict) and payload.get("status") == "active":
            path.write_bytes(foreign_bytes)
        original_write(path, payload)

    monkeypatch.setattr(coordinator, "_write_json_exclusive", interleave_activation)
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", _prepare_exact_brief_stub)

    with pytest.raises(ValueError, match="reservation ownership mismatch"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert state_path.read_bytes() == foreign_bytes
    assert not (run_root / exact_run_id).exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_publish_failure_cleans_only_owned_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    run_dir = run_root / exact_run_id
    repo_root.mkdir()
    original_rename = coordinator.os.rename

    def fail_publish(source, target) -> None:
        if Path(target) == run_dir:
            raise OSError("publish failed")
        original_rename(source, target)

    monkeypatch.setattr(coordinator.os, "rename", fail_publish)
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", _prepare_exact_brief_stub)

    with pytest.raises(OSError, match="publish failed"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert not coordinator._state_path(exact_run_id, queue_root).exists()
    assert not run_dir.exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_foreign_directory_is_preserved_before_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    run_dir = run_root / exact_run_id
    sentinel = run_dir / "foreign.bin"
    repo_root.mkdir()
    original_activate = coordinator._activate_run_reservation

    def insert_foreign_directory(*args, **kwargs) -> dict[str, object]:
        run_dir.mkdir(parents=True)
        sentinel.write_bytes(b"foreign-directory-bytes")
        return original_activate(*args, **kwargs)

    monkeypatch.setattr(coordinator, "_activate_run_reservation", insert_foreign_directory)
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", _prepare_exact_brief_stub)

    with pytest.raises(ValueError, match="exact run identity is already in use"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert sentinel.read_bytes() == b"foreign-directory-bytes"
    assert not coordinator._state_path(exact_run_id, queue_root).exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_stale_transition_fails_closed_before_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    state_path = coordinator._state_path(exact_run_id, queue_root)
    stale = state_path.with_name(f".{state_path.name}.stale.transition")
    repo_root.mkdir()
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale-token")
    prepare_calls = 0

    def count_prepare(*_args, **_kwargs) -> list[Path]:
        nonlocal prepare_calls
        prepare_calls += 1
        return []

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", count_prepare)

    with pytest.raises(ValueError, match="stale transaction"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert prepare_calls == 0
    assert stale.read_bytes() == b"stale-token"


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

    assert arguments[1:3] == ["-m", "scripts.pantheon_content_runtime_manifest"]
    assert arguments[3:5] == ["barrier-exec", "--barrier"]
    separator = arguments.index("--")
    assert arguments[separator + 2 : separator + 4] == [
        "-m",
        "scripts.agy_gemini_coordinator",
    ]
    assert "--lane-mode" in arguments
    assert "--new-matrix-sweep" in arguments
    assert "--new-matrix-run-root" in arguments
    assert "--legacy-sweep" in arguments
    assert "--legacy-state-root" in arguments
    assert "--legacy-run-root" in arguments
    assert arguments[-1] == "cycle"
    assert plist["RunAtLoad"] is True
    assert lane_plist["ProgramArguments"][1:3] == [
        "-m",
        "scripts.pantheon_content_runtime_manifest",
    ]
    lane_arguments = lane_plist["ProgramArguments"]
    lane_separator = lane_arguments.index("--")
    assert lane_arguments[lane_separator + 2 : lane_separator + 4] == [
        "-m",
        "scripts.agy_gemini_runner",
    ]
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
    assert 'USER_HOME_DIR="${PANTHEON_USER_HOME_DIR:-}"' in installer
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
    assert "optional_manifest_field actor_head" in installer
    assert "optional_manifest_field python_executable" in installer
    assert 'PYTHON_BIN="${PYTHON_REALPATH}"' in installer
    assert '--expected-python-executable "${PYTHON_BIN}"' in installer
    assert 'add_hardened_runtime_identity "${TEMP_PLIST}"' in installer
    assert 'add_hardened_runtime_identity "${LANE_TEMP_PLIST}"' in installer
    assert "for LANE in new rewrite i18n-new i18n-rewrite" in installer
    preflight_end = installer.index(
        'if launchctl print "gui/${USER_ID}/com.pantheon.agy-gemini-runner"'
    )
    first_plist_write = installer.index('cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"')
    first_control_write = installer.index('launchctl bootout "gui/${USER_ID}/${LABEL}"')
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


def _write_installer_runtime_manifest(
    tmp_path: Path,
    *,
    publisher_root: Path | None = None,
    python_executable: Path | None = None,
) -> tuple[Path, Path, Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = tmp_path / "runtime-queue"
    state_root = publisher_root or tmp_path / "runtime-publisher-state"
    log_root = tmp_path / "runtime-logs"
    for path in (queue_root, state_root, log_root):
        path.mkdir(parents=True, exist_ok=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=repo_root,
        queue_root=queue_root,
        publisher_state_root=state_root,
        log_root=log_root,
        identity="synthetic-installer:501",
        python_executable=python_executable,
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    return manifest_path, queue_root, state_root, log_root


def _installer_test_env(
    tmp_path: Path,
    *,
    pool: Path,
    state: Path,
    fail_plutil_call: int | None = None,
    python_executable: Path | None = None,
    python_path: Path | None = None,
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
    manifest_path, queue_root, publisher_root, _log_root = _write_installer_runtime_manifest(
        tmp_path,
        python_executable=python_executable,
    )
    manifest_digest = runtime_manifest.load_manifest(manifest_path)["manifest_digest"]
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state),
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": str(python_path or sys.executable),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest_digest,
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )
    return env, fake_home, mutation_log


def _write_aggregate_stage_plist(
    path: Path,
    *,
    label: str,
    manifest: dict[str, object],
    manifest_digest: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        plistlib.dump(
            {
                "Label": label,
                "WorkingDirectory": manifest["actor_root"],
                "EnvironmentVariables": {
                    "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest_digest
                    or manifest["manifest_digest"],
                    "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
                    "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
                    "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
                    "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest[
                        "publisher_state_root"
                    ],
                    "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
                },
            },
            stream,
        )
    path.chmod(0o600)


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


def test_installer_preflight_builds_all_lane_plists_without_control_plane_mutation(
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

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--preflight",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "四條 lane runner preflight 通過" in completed.stdout
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_four_lane_recovery_coordinator_rejects_new_only_before_mutation(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-FOUR-LANE-REJECT-NEW-ONLY-001。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["AGY_GEMINI_NEW_ONLY"] = "1"

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--preflight"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "四軌 recovery 禁止 new-only" in completed.stderr
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_four_lane_installer_separates_stage_and_activation_with_rollback() -> None:
    """REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001。"""
    repo_root = Path(__file__).resolve().parents[1]
    installer = (repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh").read_text(
        encoding="utf-8"
    )

    assert 'ACTION}" == "--install"' in installer
    assert '"--activate"' in installer
    assert "ACTIVATION_BARRIER" in installer
    assert "rollback_activation" in installer
    assert "previous_loaded" in installer
    install_section = installer.split('if [[ "${ACTION}" == "--install" ]]', 1)[1]
    assert install_section.index("exit 0") < install_section.index("launchctl bootstrap")


def test_aggregate_activation_rejects_mixed_installer_manifest_before_mutation(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001 aggregate caller。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    _write_aggregate_stage_plist(
        stage_dir / "com.pantheon.agy-content-publisher.plist",
        label="com.pantheon.agy-content-publisher",
        manifest=manifest,
    )
    _write_aggregate_stage_plist(
        stage_dir / "com.pantheon.content-capacity-guard.plist",
        label="com.pantheon.content-capacity-guard",
        manifest=manifest,
        manifest_digest="0" * 64,
    )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert "mismatch" in activated.stdout
    assert not mutation_log.exists()
    assert not (fake_home / "Library/LaunchAgents/com.pantheon.agy-gemini-coordinator.plist").exists()


@pytest.mark.parametrize(
    ("rollback_fail_at", "expected_rollback_status"),
    [(0, "ROLLBACK_COMPLETE"), (4, "ROLLBACK_FAILED")],
)
def test_four_lane_activation_failure_restores_previous_plists_and_loaded_state(
    tmp_path: Path,
    rollback_fail_at: int,
    expected_rollback_status: str,
) -> None:
    """REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001 動態 rollback。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True)
    labels = [
        "com.pantheon.agy-gemini-coordinator",
        "com.pantheon.agy-gemini-new",
        "com.pantheon.agy-gemini-rewrite",
        "com.pantheon.agy-gemini-i18n-new",
        "com.pantheon.agy-gemini-i18n-rewrite",
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    ]
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    previous_payload = {
        "Label": "com.pantheon.agy-gemini-coordinator",
        "ProgramArguments": [
            "python",
            "-m",
            "runtime",
            "barrier-exec",
            "--barrier",
            str(barrier),
        ],
        "EnvironmentVariables": {
            "PANTHEON_RUNTIME_MANIFEST": env["PANTHEON_RUNTIME_MANIFEST_FILE"],
            "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        },
    }
    previous = plistlib.dumps(previous_payload)
    for label in labels:
        (launch_agents / f"{label}.plist").write_bytes(previous)
    ready = tmp_path / "previous-ready"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready, manifest, label)
    runtime_manifest.activate_barrier(barrier, ready, manifest)
    launchctl = tmp_path / "bin" / "launchctl"
    bootstrap_count = tmp_path / "bootstrap-count"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    for label in labels:
        (loaded / label).touch()
    launchctl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'pid = 4242'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        f"  count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
        "  count=$((count + 1))\n"
        f"  printf '%s' \"$count\" > '{bootstrap_count}'\n"
        f"  if [ \"$count\" -eq 3 ] || [ \"$count\" -eq {rollback_fail_at} ]; then exit 1; fi\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  touch '{loaded}/'$label\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--install"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    for label in labels[-2:]:
        with (stage_dir / f"{label}.plist").open("wb") as stream:
            plistlib.dump(
                {
                    "Label": label,
                    "WorkingDirectory": manifest["actor_root"],
                    "EnvironmentVariables": {
                        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest[
                            "manifest_digest"
                        ],
                        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
                        "PANTHEON_RUNTIME_SERVICE_LABEL": label,
                        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest[
                            "runtime_identity_digest"
                        ],
                        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
                        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
                        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
                        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
                        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
                        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest[
                            "publisher_state_root"
                        ],
                        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
                    },
                },
                stream,
            )
        (stage_dir / f"{label}.plist").chmod(0o600)
    for label in labels:
        assert (launch_agents / f"{label}.plist").read_bytes() == previous
        assert (stage_dir / f"{label}.plist").is_file()
    activated = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--activate"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    for label in labels:
        assert (launch_agents / f"{label}.plist").read_bytes() == previous
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"
    failure_receipt = launch_agents / ".pantheon-four-lane-stage" / "failure-receipt.json"
    assert json.loads(failure_receipt.read_text(encoding="utf-8"))["status"] == expected_rollback_status
    mutations = mutation_log.read_text(encoding="utf-8")
    assert mutations.count("bootout") >= 2
    assert mutations.count("bootstrap") >= len(labels)


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
    manifest_path, queue_root, _state_root, _log_root = _write_installer_runtime_manifest(
        tmp_path,
        publisher_root=publisher_root,
    )
    manifest_digest = runtime_manifest.load_manifest(manifest_path)["manifest_digest"]
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
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest_digest,
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
            / ".pantheon-four-lane-stage"
            / "com.pantheon.agy-gemini-coordinator.plist"
        ).read_bytes()
    )
    coordinator_arguments = coordinator_plist["ProgramArguments"]
    coordinator_variables = coordinator_plist["EnvironmentVariables"]
    assert coordinator_arguments[coordinator_arguments.index("--new-matrix-run-root") + 1] == str(gsc_copy_root)
    assert coordinator_arguments[coordinator_arguments.index("--legacy-state-root") + 1] == str(publisher_root)
    assert coordinator_arguments[coordinator_arguments.index("--legacy-run-root") + 1] == str(gsc_copy_root)
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
                / ".pantheon-four-lane-stage"
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
    monkeypatch.delenv("PANTHEON_FORMAL_RUNTIME")
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


def test_hardened_installer_uses_canonical_python_for_coordinator_and_lanes(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    python_target = Path(sys.executable).resolve(strict=True)
    python_link = tmp_path / "python-link"
    python_link.symlink_to(python_target)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
        python_executable=python_target,
        python_path=python_link,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert not mutation_log.exists()
    stage = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    staged_labels = [
        "com.pantheon.agy-gemini-coordinator",
        "com.pantheon.agy-gemini-new",
        "com.pantheon.agy-gemini-rewrite",
        "com.pantheon.agy-gemini-i18n-new",
        "com.pantheon.agy-gemini-i18n-rewrite",
    ]
    for label in staged_labels:
        payload = plistlib.loads((stage / f"{label}.plist").read_bytes())
        arguments = payload["ProgramArguments"]
        variables = payload["EnvironmentVariables"]
        assert arguments[0] == str(python_target)
        assert arguments[17] == str(python_target)
        assert variables["PANTHEON_RUNTIME_PYTHON_EXECUTABLE"] == str(python_target)


def test_hardened_installer_rejects_python_drift_before_stage_or_control_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    drift_python = tmp_path / "python-drift"
    drift_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    drift_python.chmod(0o755)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
        python_executable=drift_python,
        python_path=Path(sys.executable),
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
    assert not mutation_log.exists()
    installed_paths = [
        fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.agy-gemini-coordinator.plist",
        *[
            fake_home / f"Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.agy-gemini-{lane}.plist"
            for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite")
        ],
    ]
    assert len(installed_paths) == 5
    for path in installed_paths:
        variables = plistlib.loads(path.read_bytes())["EnvironmentVariables"]
        assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in variables
        assert "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE" not in variables
        assert variables["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"] == "300"

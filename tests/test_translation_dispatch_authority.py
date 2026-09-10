"""翻譯 dispatch 對既有 run/source authority 的離線驗證。"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import agy_gemini_runner as runner
from scripts.agy_gemini_outbox import create_external_request


def test_unregistered_translation_is_rejected_before_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue = tmp_path / "queue"
    lane_queue = queue / "lanes" / "i18n-rewrite"
    monkeypatch.delenv("PANTHEON_FORMAL_RUNTIME", raising=False)
    monkeypatch.delenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", raising=False)
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(queue))
    request = create_external_request(
        lane_queue,
        namespace=hashlib.sha256(b"translation-missing-registry").hexdigest()[:24],
        role="reviewer",
        model="fake-model",
        prompt="離線驗證",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False},
    )
    calls = []

    def fake_provider(*args: object) -> dict[str, bool]:
        calls.append(args)
        return {"ok": True}

    result = runner.process_once(lane_queue, lane="i18n-rewrite", generate_json=fake_provider)
    assert calls == []
    assert result["status"] == "failed"
    assert result["job_id"] == request["job_id"]
    assert not (lane_queue / "inbox" / f"{request['job_id']}.json").exists()


def _registered_job(tmp_path, monkeypatch):
    import copy
    import json
    from scripts import agy_multilingual_pipeline as multilingual
    from scripts import agy_seo_copy_pipeline as pipeline
    from tests.test_agy_multilingual_pipeline import source_article

    source = source_article()
    policy = pipeline.load_article_publication_policy()
    identity = policy["identity"]
    source["publication_policy"] = {
        "contract_version": 1,
        "global_policy": copy.deepcopy(policy),
        "article_policy": {
            "policyVersion": policy["policy_version"],
            "canonical": policy["site_origin"] + source["canonical_path"],
            "author": {"name": identity["author_name"], "url": identity["author_url"], "id": identity["author_id"]},
            "editorialResponsibility": identity["editorial_responsibility"],
            "evidence": {"mode": "cultural_reflection", "sources": [], "disclosure": "文化反思用途，無法保證結果。"},
            "published": "2026-09-08", "modified": "2026-09-08", "changeType": "created",
        },
    }
    queue = tmp_path / "queue"
    lane = "i18n-rewrite"
    run_id = "translate-dispatch-authority-ja"
    namespace = hashlib.sha256(run_id.encode()).hexdigest()[:24]
    run_dir = queue / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    brief = {"schema_version": 1, "mode": "translate_existing", "run_id": run_id,
             "articles": [{"translation_id": "TEST-001:ja", "locale": "ja", "source_article_id": "TEST-001",
                           "source_path": source["canonical_path"], "source": source,
                           "source_sha256": multilingual.source_sha256(source)}]}
    state = {"schema_version": 1, "run_id": run_id, "run_dir": str(run_dir), "status": "active", "lane": lane,
             "identity_envelope": multilingual.translation_identity_envelope("TEST-001", lane)}
    state_path = queue / "runs" / f"{namespace}.json"
    state_path.parent.mkdir()
    state_path.write_text(json.dumps(state))
    (run_dir / "brief.json").write_text(json.dumps(brief))
    for name in ("AGY_GEMINI_CREDENTIAL_POOL_FILE", "AGY_GEMINI_V4_BROKER", "PANTHEON_RUNTIME_SERVICE_LABEL", "AGY_GEMINI_NEW_ONLY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "0")
    monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(queue))
    monkeypatch.setattr(multilingual, "load_source_article", lambda *_args: copy.deepcopy(source))
    request = create_external_request(queue / "lanes" / lane, namespace=namespace, role="reviewer", model="fake-model",
                                      prompt="離線新契約", response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False})
    return queue / "lanes" / lane, request, source, brief, state, state_path, run_dir


@pytest.mark.parametrize("explicit_lane", [None, "i18n-rewrite"])
def test_current_registered_contract_reaches_fake_provider(tmp_path, monkeypatch, explicit_lane):
    lane_queue, request, *_ = _registered_job(tmp_path, monkeypatch)
    calls = []
    result = runner.process_once(lane_queue, lane=explicit_lane, generate_json=lambda *args: calls.append(args) or {"ok": True})
    assert result["status"] == "processed", result
    assert len(calls) == 1
    assert (lane_queue / "archive" / f"{request['job_id']}.json").is_file()


@pytest.mark.parametrize("mutation", ["body", "disclosure", "global", "legacy", "status", "lane", "run_id", "run_dir", "identity", "last_job", "missing_brief", "symlink_brief", "brief_hash", "explicit_lane"])
def test_invalid_registered_contract_never_consumes_admission(tmp_path, monkeypatch, mutation):
    import json
    from scripts import agy_multilingual_pipeline as multilingual
    lane_queue, request, source, brief, state, state_path, run_dir = _registered_job(tmp_path, monkeypatch)
    if mutation == "body":
        source["bodySections"][0]["paragraphs"].append("新增不可省略的限制。")
    elif mutation == "disclosure":
        source["publication_policy"]["article_policy"]["evidence"]["disclosure"] += "僅供文化反思。"
    elif mutation == "global":
        source["publication_policy"]["global_policy"]["levels"]["required"] += "更新規則。"
    elif mutation == "legacy":
        del brief["articles"][0]["source"]["publication_policy"]
        brief["articles"][0]["source_sha256"] = multilingual.source_sha256(source)
    elif mutation in {"status", "lane", "run_id", "run_dir", "last_job"}:
        state[{"last_job": "last_job_id"}.get(mutation, mutation)] = "mismatch"
    elif mutation == "identity":
        state["identity_envelope"]["article_ids"] = ["OTHER"]
    elif mutation == "brief_hash":
        brief["articles"][0]["source_sha256"] = "0" * 64
    state_path.write_text(json.dumps(state))
    # 改當前來源時保持封存 brief 不變；其餘 case 寫入受測的失配。
    if mutation not in {"body", "disclosure", "global"}:
        (run_dir / "brief.json").write_text(json.dumps(brief))
    if mutation in {"missing_brief", "symlink_brief"}:
        (run_dir / "brief.json").unlink()
        if mutation == "symlink_brief":
            other = tmp_path / "other.json"
            other.write_text(json.dumps(brief))
            (run_dir / "brief.json").symlink_to(other)
    calls = []
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(tmp_path / "must-not-read.json"))
    monkeypatch.setattr(runner, "_read_production_pool", lambda *_args: calls.append("pool") or pytest.fail("authority 必須先於 admission"))
    result = runner.process_once(lane_queue, lane="new" if mutation == "explicit_lane" else None,
                                 generate_json=lambda *_args: calls.append("provider") or {"ok": True})
    assert result["status"] == "failed", result
    assert calls == []
    assert (lane_queue / "failed" / f"{request['job_id']}.json").exists()
    assert not (lane_queue / "outbox" / f"{request['job_id']}.json").exists()
    assert not list((lane_queue / "inbox").glob("*.json"))


@pytest.mark.parametrize("transport", ["injected", "direct", "broker"])
@pytest.mark.parametrize("drift", [False, True])
def test_all_transports_obey_authority_before_attempt(tmp_path, monkeypatch, transport, drift):
    from tests.test_agy_gemini_outbox import _write_production_pool, _broker_result
    from scripts.agy_gemini_v4_broker import ExecutionReceipt
    lane_queue, request, source, *_ = _registered_job(tmp_path, monkeypatch)
    calls = []
    allocator = tmp_path / "allocator.json"
    if transport in {"direct", "broker"}:
        manifest, _ = _write_production_pool(tmp_path)
        monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
        monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(allocator))
        monkeypatch.setenv("AGY_GEMINI_DAILY_PROVIDER_ADMISSION_CAP", "1200")
    if transport == "direct":
        class Client:
            def __init__(self, *_args, **_kwargs):
                pass
            def _single_request_http_transport(self, *_args, **_kwargs):
                pytest.fail("不得呼叫 HTTP")
            def generate_json(self, *_args):
                calls.append("direct")
                return {"ok": True}
        monkeypatch.setattr(runner, "GeminiClient", Client)
    if transport == "broker":
        monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
        monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(tmp_path / "fake-executable"))
        monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", "a" * 64)
        def fake_broker(**kwargs):
            calls.append("broker")
            receipt = ExecutionReceipt(request["job_id"], request["namespace"], "attempt-1", request["request_sha256"], request["model"], "antigravity_cli_v1", "a" * 64)
            return _broker_result("COMPLETE", receipt, result={"ok": True})
        monkeypatch.setattr(runner, "run_single_shot", fake_broker)
    if drift:
        source["publication_policy"]["article_policy"]["evidence"]["disclosure"] += "新增限制。"
    result = runner.process_once(lane_queue, generate_json=lambda *_args: calls.append("injected") or {"ok": True})
    if drift:
        assert result["status"] == "failed", result
        assert calls == []
        assert not allocator.exists()
        assert not list(lane_queue.rglob("*.attempt.json"))
    else:
        assert result["status"] == "processed", result
        assert calls == [transport]


def test_source_change_during_claim_is_rechecked(tmp_path, monkeypatch):
    lane_queue, _request, source, *_ = _registered_job(tmp_path, monkeypatch)
    original = runner._claim_next
    def claim_then_drift(*args):
        claimed = original(*args)
        source["description"] += "新的限制條件。"
        return claimed
    monkeypatch.setattr(runner, "_claim_next", claim_then_drift)
    calls = []
    result = runner.process_once(lane_queue, generate_json=lambda *_args: calls.append(True) or {"ok": True})
    assert result["status"] == "failed", result
    assert calls == []


@pytest.mark.parametrize("with_root_env", [True, False])
def test_registered_translation_cannot_bypass_via_shared_queue(tmp_path, monkeypatch, with_root_env):
    import json
    lane_queue, request, _source, _brief, state, state_path, _run_dir = _registered_job(tmp_path, monkeypatch)
    root = lane_queue.parent.parent
    if not with_root_env:
        monkeypatch.delenv("PANTHEON_RUNTIME_QUEUE_ROOT")
    shared = create_external_request(root, namespace=request["namespace"], role="reviewer", model="fake-model",
                                     prompt="shared queue 不能繞過翻譯身份", response_schema=request["response_schema"])
    state["last_job_id"] = shared["job_id"]
    state_path.write_text(json.dumps(state))
    calls = []
    result = runner.process_once(root, generate_json=lambda *_args: calls.append(True) or {"ok": True})
    assert result["status"] == "failed"
    assert calls == []
    assert (root / "failed" / f"{shared['job_id']}.json").exists()


@pytest.mark.parametrize("internal_runner", [False, True])
def test_coordinator_handoff_preserves_new_job_until_registry_updated(tmp_path, monkeypatch, internal_runner):
    import fcntl
    import json
    from scripts import agy_gemini_coordinator as coordinator
    from scripts import agy_gemini_outbox as outbox
    lane_queue, old, _source, _brief, state, state_path, _run_dir = _registered_job(tmp_path, monkeypatch)
    root = lane_queue.parent.parent
    state["last_job_id"] = old["job_id"]
    state_path.write_text(json.dumps(state))
    (lane_queue / "archive").mkdir()
    (lane_queue / "outbox" / f"{old['job_id']}.json").rename(lane_queue / "archive" / f"{old['job_id']}.json")
    calls, observations = [], []
    original = outbox.create_external_request
    def emit_then_race(*args, **kwargs):
        request = original(*args, **kwargs)
        result = runner.process_once(lane_queue, generate_json=lambda *_args: calls.append(True) or {"ok": True})
        assert result == {"status": "busy", "reason": "coordinator_handoff"}
        assert (lane_queue / "outbox" / f"{request['job_id']}.json").exists()
        assert not (lane_queue / "failed" / f"{request['job_id']}.json").exists()
        observations.append(request)
        return request
    monkeypatch.setattr(outbox, "create_external_request", emit_then_race)
    client = outbox.OutboxGeminiClient(lane_queue, namespace=old["namespace"], writer_model="fake-writer", reviewer_model="fake-reviewer")
    def tick(*_args):
        return client.generate_json("writer", "合法下一階段", old["response_schema"])
    with (root / "coordinator.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert coordinator._advance(root, state, tick, job_queue_root=lane_queue) == "pending"
        assert len(observations) == 1 and calls == []
        if internal_runner:
            result = runner.process_once(lane_queue, _coordinator_lock_fd=lock.fileno(), generate_json=lambda *_args: calls.append(True) or {"ok": True})
            assert result["status"] == "processed", result
            with (root / "coordinator.lock").open() as other:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not internal_runner:
        result = runner.process_once(lane_queue, generate_json=lambda *_args: calls.append(True) or {"ok": True})
        assert result["status"] == "processed", result
    assert calls == [True]


def test_coordinator_lock_released_even_if_attempt_cleanup_fails(tmp_path, monkeypatch):
    import fcntl
    lane_queue, *_ = _registered_job(tmp_path, monkeypatch)
    def failed_cleanup(_evidence):
        raise OSError("離線清理故障")
    monkeypatch.setattr(runner, "_close_production_attempt", failed_cleanup)
    with pytest.raises(OSError, match="離線清理故障"):
        runner.process_once(lane_queue, generate_json=lambda *_args: {"ok": True})
    with (lane_queue.parent.parent / "coordinator.lock").open() as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

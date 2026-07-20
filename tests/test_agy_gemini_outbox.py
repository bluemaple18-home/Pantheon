from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest
import scripts.agy_gemini_outbox as outbox

from scripts.agy_gemini_outbox import (
    ExternalJobPending,
    OutboxGeminiClient,
    consume_external_response,
    create_external_request,
    run_pipeline_tick,
)
from scripts.agy_gemini_runner import process_once


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


def test_runner_module_entrypoint_and_launchd_template_are_runnable(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_runner",
            "--queue-root",
            str(tmp_path),
            "process-once",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    plist = plistlib.loads(
        (repo_root / "ops/launchd/com.pantheon.agy-gemini-runner.plist.example").read_bytes()
    )
    arguments = plist["ProgramArguments"]

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {"status": "idle"}
    assert arguments[1:3] == ["-m", "scripts.agy_gemini_runner"]
    assert not any(argument.endswith("agy_gemini_runner.py") for argument in arguments)


def test_outbox_request_is_sanitized_hashed_and_idempotent(tmp_path: Path) -> None:
    first = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="只根據公開 brief 產生 JSON。",
        response_schema=SCHEMA,
    )
    second = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="只根據公開 brief 產生 JSON。",
        response_schema=SCHEMA,
    )

    assert first == second
    assert len(first["job_id"]) == 40
    assert len(first["request_sha256"]) == 64
    assert first["thinking_level"] == "LOW"
    assert first["operation_level"] == "external_generation"
    assert json.loads((tmp_path / "outbox" / f"{first['job_id']}.json").read_text()) == first


@pytest.mark.parametrize(
    "private_value",
    [
        "/Users/example/private/article.md",
        ".work/gsc-copy/private/brief.json",
        "GEMINI_API_KEY=secret",
        "AIza" + "x" * 32,
        "-----BEGIN PRIVATE KEY-----",
    ],
)
def test_outbox_rejects_private_paths_and_credentials(tmp_path: Path, private_value: str) -> None:
    with pytest.raises(ValueError, match="external payload contains forbidden private data"):
        create_external_request(
            tmp_path,
            namespace="opaque-run-01",
            role="writer",
            model="gemini-test-writer",
            prompt=f"公開說明：{private_value}",
            response_schema=SCHEMA,
        )


def test_outbox_client_returns_pending_then_consumes_bound_response(tmp_path: Path) -> None:
    client = OutboxGeminiClient(
        tmp_path,
        namespace="opaque-run-01",
        writer_model="gemini-test-writer",
        reviewer_model="gemini-test-reviewer",
    )

    with pytest.raises(ExternalJobPending) as pending:
        client.generate_json("writer", "公開 prompt", SCHEMA)

    request = json.loads((tmp_path / "outbox" / f"{pending.value.job_id}.json").read_text())
    response = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": request["model"],
        "completed_at": "2026-07-18T12:00:00+08:00",
        "result": {"ok": True},
    }
    inbox = tmp_path / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir(parents=True)
    inbox.write_text(json.dumps(response), encoding="utf-8")

    assert client.generate_json("writer", "公開 prompt", SCHEMA) == {"ok": True}


def test_response_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    inbox = tmp_path / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir(parents=True)
    inbox.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "job_id": request["job_id"],
                "request_sha256": "0" * 64,
                "model": request["model"],
                "completed_at": "2026-07-18T12:00:00+08:00",
                "result": {"ok": True},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="response request hash mismatch"):
        consume_external_response(tmp_path, request)


def test_runner_processes_one_job_and_archives_request(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="審查公開 candidate",
        response_schema=SCHEMA,
    )
    calls: list[tuple[str, str]] = []

    def generate(role: str, model: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
        calls.append((role, model))
        assert prompt == "審查公開 candidate"
        assert schema == SCHEMA
        return {"ok": True}

    result = process_once(tmp_path, generate_json=generate)

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert calls == [("reviewer", "gemini-test-reviewer")]
    assert not (tmp_path / "outbox" / f"{request['job_id']}.json").exists()
    assert (tmp_path / "archive" / f"{request['job_id']}.json").exists()
    response = json.loads((tmp_path / "inbox" / f"{request['job_id']}.json").read_text())
    assert response["request_sha256"] == request["request_sha256"]
    assert response["result"] == {"ok": True}


def test_runner_preserves_invalid_model_json_for_pipeline_rejection(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )

    result = process_once(tmp_path, generate_json=lambda *_args: {"wrong": True})

    assert result == {"status": "processed", "job_id": request["job_id"]}
    response = json.loads((tmp_path / "inbox" / f"{request['job_id']}.json").read_text())
    assert response["result"] == {"wrong": True}
    assert not (tmp_path / "failed" / f"{request['job_id']}.json").exists()


def test_runner_returns_idle_for_empty_outbox(tmp_path: Path) -> None:
    assert process_once(tmp_path, generate_json=lambda *_args: {"ok": True}) == {"status": "idle"}


def test_pipeline_tick_reserves_one_bounded_final_content_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(json.dumps({"run_id": "bounded-repair-run"}), encoding="utf-8")
    observed: list[int] = []

    def fake_run_writer_reviewer(_run_dir: Path, _client: object, max_repairs: int = 2):
        observed.append(max_repairs)
        return {"articles": []}, {"articles": []}

    monkeypatch.setattr(outbox.pipeline, "run_writer_reviewer", fake_run_writer_reviewer)

    result = run_pipeline_tick(run_dir, tmp_path / "queue")

    assert result["status"] == "complete"
    assert observed == [3]


def test_pipeline_advances_writer_then_fresh_reviewer_across_ticks(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "optimize-01"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    brief = {
        "schema_version": 1,
        "run_id": "private-optimize-run-id",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-001",
                "canonical_path": "/articles/astrology/astrology-0001",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    proposed = {
        "title": "公開搜尋詞怎麼看？整理使用情境與限制",
        "description": "公開搜尋詞適合用來整理讀者真正想確認的情境、可觀察資訊與下一步選擇；本文只提供一般說明，不能替個人判斷，也不承諾任何特定結果，仍須回到實際資料與互動再決定。",
        "answer": "先確認具體情境與資料；這項說明不能替個人下結論。",
    }
    roles: list[str] = []

    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    writer_request_path = next((queue_root / "outbox").glob("*.json"))
    writer_request_text = writer_request_path.read_text(encoding="utf-8")
    assert "private-optimize-run-id" not in writer_request_text
    assert "app/web/static/article-registry.js" not in writer_request_text
    assert '"run_id"' not in writer_request_text

    def generate(role: str, _model: str, _prompt: str, _schema: dict[str, object]) -> dict[str, object]:
        roles.append(role)
        if role == "writer":
            return {"articles": [{"slot": "article-01", "proposed": proposed}]}
        return {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}

    assert process_once(queue_root, generate_json=generate)["status"] == "processed"
    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    assert process_once(queue_root, generate_json=generate)["status"] == "processed"

    result = run_pipeline_tick(run_dir, queue_root)

    assert result["status"] == "complete"
    assert roles == ["writer", "reviewer"]
    candidate = json.loads((run_dir / "candidate.json").read_text())
    review = json.loads((run_dir / "review.json").read_text())
    assert candidate["articles"][0]["proposed"] == proposed
    assert review["articles"][0]["verdict"] == "APPROVE"


def test_invalid_writer_schema_enqueues_a_distinct_retry_job(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "optimize-writer-schema-retry"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    brief = {
        "schema_version": 1,
        "run_id": "private-writer-schema-retry",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-RETRY-001",
                "canonical_path": "/articles/astrology/astrology-0001",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ExternalJobPending) as first_pending:
        run_pipeline_tick(run_dir, queue_root)
    process_once(queue_root, generate_json=lambda *_args: {"articles": [{"slot": "article-01"}]})

    with pytest.raises(ExternalJobPending) as retry_pending:
        run_pipeline_tick(run_dir, queue_root)

    assert retry_pending.value.job_id != first_pending.value.job_id
    retry = json.loads((queue_root / "outbox" / f"{retry_pending.value.job_id}.json").read_text())
    assert "schema repair 1" in retry["prompt"]


def test_invalid_reviewer_json_becomes_hard_rejection(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "optimize-invalid-review"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    brief = {
        "schema_version": 1,
        "run_id": "private-invalid-review-run",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-002",
                "canonical_path": "/articles/astrology/astrology-0002",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞二"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    proposed = {
        "title": "公開搜尋詞二怎麼看？整理情境與限制",
        "description": "公開搜尋詞二適合整理讀者想確認的情境、可觀察資料與下一步選擇；本文只提供一般說明，不能替個人判斷，也不承諾任何特定結果，仍須回到實際互動再決定。",
        "answer": "先確認具體資料；這項說明不能替個人下結論。",
    }

    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    process_once(
        queue_root,
        generate_json=lambda *_args: {"articles": [{"slot": "article-01", "proposed": proposed}]},
    )
    with pytest.raises(ExternalJobPending):
        run_pipeline_tick(run_dir, queue_root)
    process_once(queue_root, generate_json=lambda *_args: {"wrong": True})

    result = run_pipeline_tick(run_dir, queue_root)
    review = json.loads((run_dir / "review.json").read_text())

    assert result["status"] == "complete"
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["hard_failure"] is True
    assert review["articles"][0]["findings"][0]["code"].startswith("invalid_reviewer_json:")

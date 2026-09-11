from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_outbox as outbox
from scripts import agy_seo_copy_pipeline as pipeline
from scripts.agy_gemini_outbox import (
    create_external_request,
    consume_external_response,
)

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.append(str(TESTS_DIR))

from test_agy_seo_copy_pipeline import (  # noqa: E402
    make_deterministic_green_create_article,
    make_external_create_article,
    make_rewrite_brief,
    make_rewrite_publication_policy,
    make_rewrite_sections,
)


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _namespace(run_id: str) -> str:
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]


def _authority_digest(label: str = "repair1-authority") -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _write_route_config(path: Path, *, writer_model: str) -> pipeline.ModelRouteConfig:
    coordinator.atomic_write_json(
        path,
        {
            "schema_version": 1,
            "routes": {
                "writer": [writer_model],
                "reviewer": ["gemini-3.1-flash-lite"],
            },
        },
    )
    return pipeline.load_model_route_config(path)


def _use_route(
    monkeypatch: pytest.MonkeyPatch,
    route: pipeline.ModelRouteConfig,
) -> None:
    monkeypatch.setenv("AGY_GEMINI_MODEL_ROUTE_CONFIG", str(route.path))
    monkeypatch.setenv("AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST", route.digest)
    monkeypatch.setenv("AGY_WRITER_MODEL", route.routes["writer"][0])
    monkeypatch.setenv("AGY_REVIEWER_MODEL", route.routes["reviewer"][0])


def _use_source_lite_route(monkeypatch: pytest.MonkeyPatch) -> pipeline.ModelRouteConfig:
    route = pipeline.load_model_route_config(pipeline.MODEL_ROUTE_CONFIG_PATH)
    assert route.routes == {
        "writer": ("gemini-3.5-flash-lite",),
        "reviewer": ("gemini-3.1-flash-lite",),
    }
    _use_route(monkeypatch, route)
    return route


def _disable_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coordinator.formal_runtime,
        "validate_runtime_tick",
        lambda *args, **kwargs: {"status": "valid"},
    )


def _pending_writer_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    lane: str,
) -> tuple[Path, Path, Path, dict[str, object], str]:
    _disable_runtime(monkeypatch)
    queue_root = tmp_path / "queue"
    job_root = queue_root / "lanes" / lane
    run_id = (
        "auto-new-v1-20260910-002-01"
        if lane == "new"
        else "legacy-auto-sweep-v1-astrology-0010-astro-houses-01"
    )
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    if lane == "new":
        brief = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "create",
            "articles": [{"target": {"id": "V2-TAROT-TEMPERANCE-RELATIONSHIPS"}}],
        }
    else:
        brief = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": "ASTRO-HOUSES-01"}],
        }
    coordinator.atomic_write_json(run_dir / "brief.json", brief)
    correlation_id = hashlib.sha256(f"{lane}:correlation".encode("utf-8")).hexdigest()[:32]
    state = coordinator.register_run(run_dir, queue_root, correlation_id=correlation_id)
    request = create_external_request(
        job_root,
        namespace=_namespace(run_id),
        role="writer",
        model="gemini-3.5-flash",
        prompt=f"{lane} same writer prompt",
        response_schema=SCHEMA,
    )
    state["last_job_id"] = request["job_id"]
    coordinator._write_state(queue_root, state)
    return run_dir, queue_root, job_root, request, correlation_id


def _native_brief_and_writer_result(lane: str) -> tuple[dict[str, object], dict[str, object]]:
    if lane == "new":
        target = make_deterministic_green_create_article(
            "V2-TAROT-TEMPERANCE-RELATIONSHIPS"
        )
        brief = {
            "schema_version": 1,
            "run_id": "auto-new-v1-20260910-002-01",
            "mode": "create",
            "articles": [
                {
                    "matrix": {
                        "id": target["id"],
                        "title": target["title"],
                        "intent": "公開搜尋意圖",
                    },
                    "target": target,
                }
            ],
        }
        return brief, {"articles": [make_external_create_article(target)]}
    if lane != "rewrite":
        raise ValueError("native writer lite test lane is invalid")
    brief = make_rewrite_brief("ASTRO-HOUSES-01")
    brief["run_id"] = "legacy-auto-sweep-v1-astrology-0010-astro-houses-01"
    source = brief["articles"][0]
    return brief, {
        "articles": [
            {
                "slot": source["slot"],
                "bodySections": make_rewrite_sections(
                    str(source["identity"]["primaryKeyword"]),
                    "Lite",
                ),
                "publicationPolicy": make_rewrite_publication_policy(source),
            }
        ]
    }


def _native_pending_writer_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    lane: str,
) -> tuple[Path, Path, Path, dict[str, object], str, dict[str, object]]:
    _disable_runtime(monkeypatch)
    flash_route = _write_route_config(tmp_path / "flash-routes.json", writer_model="gemini-3.5-flash")
    _use_route(monkeypatch, flash_route)
    queue_root = tmp_path / "queue"
    job_root = queue_root / "lanes" / lane
    brief, writer_result = _native_brief_and_writer_result(lane)
    run_id = str(brief["run_id"])
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    coordinator.atomic_write_json(run_dir / "brief.json", brief)
    correlation_id = hashlib.sha256(f"{lane}:native-correlation".encode("utf-8")).hexdigest()[:32]
    state = coordinator.register_run(run_dir, queue_root, correlation_id=correlation_id)

    status = coordinator._advance(
        queue_root,
        state,
        outbox.run_pipeline_tick,
        job_queue_root=job_root,
    )
    pending = coordinator.read_run_state(run_dir, queue_root)
    request_path = job_root / "outbox" / f"{pending['last_job_id']}.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))

    assert status == "pending"
    assert request["role"] == "writer"
    assert request["model"] == "gemini-3.5-flash"
    assert request["namespace"] == _namespace(run_id)
    return run_dir, queue_root, job_root, request, correlation_id, writer_result


def _repair(
    run_dir: Path,
    queue_root: Path,
    job_root: Path,
    request: dict[str, object],
    correlation_id: str,
    *,
    lane: str,
    execute: bool = True,
) -> dict[str, object]:
    run_id = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))["run_id"]
    return coordinator.replace_failed_external_job(
        run_dir,
        queue_root,
        job_queue_root=job_root,
        lane=lane,
        expected_run_id=run_id,
        source_job_id=str(request["job_id"]),
        request_sha256=str(request["request_sha256"]),
        namespace=str(request["namespace"]),
        correlation_id=correlation_id,
        authority_digest=_authority_digest(),
        pending_writer_lite_retry=True,
        execute=execute,
        plan_only=not execute,
    )


@pytest.mark.parametrize("lane", ["new", "rewrite"])
def test_pending_writer_lite_retry_dry_run_is_side_effect_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lane: str,
) -> None:
    run_dir, queue_root, job_root, request, correlation_id = _pending_writer_fixture(
        tmp_path,
        monkeypatch,
        lane=lane,
    )
    before = _file_snapshot(queue_root)

    result = _repair(
        run_dir,
        queue_root,
        job_root,
        request,
        correlation_id,
        lane=lane,
        execute=False,
    )

    assert result["status"] == "plan_only"
    assert result["action"] == "pending_writer_lite_retry"
    assert result["source_model"] == "gemini-3.5-flash"
    assert result["model"] == "gemini-3.5-flash-lite"
    assert _file_snapshot(queue_root) == before


@pytest.mark.parametrize("lane", ["new", "rewrite"])
def test_pending_writer_lite_retry_replaces_same_run_and_consumes_lite_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lane: str,
) -> None:
    run_dir, queue_root, job_root, request, correlation_id = _pending_writer_fixture(
        tmp_path,
        monkeypatch,
        lane=lane,
    )
    brief_before = (run_dir / "brief.json").read_bytes()

    result = _repair(run_dir, queue_root, job_root, request, correlation_id, lane=lane)
    after_first = _file_snapshot(queue_root)
    replay = _repair(run_dir, queue_root, job_root, request, correlation_id, lane=lane)

    replacement_job_id = str(result["replacement_job_id"])
    replacement_path = job_root / "outbox" / f"{replacement_job_id}.json"
    replacement = json.loads(replacement_path.read_text(encoding="utf-8"))
    state = coordinator.read_run_state(run_dir, queue_root)

    assert result["status"] == "replacement_created"
    assert replay["status"] == "already_replaced"
    assert _file_snapshot(queue_root) == after_first
    assert (run_dir / "brief.json").read_bytes() == brief_before
    assert (job_root / "archive" / f"{request['job_id']}.json").is_file()
    assert not (job_root / "outbox" / f"{request['job_id']}.json").exists()
    assert replacement["model"] == "gemini-3.5-flash-lite"
    assert replacement["role"] == "writer"
    assert replacement["namespace"] == request["namespace"]
    assert replacement["prompt"] == request["prompt"]
    assert replacement["response_schema"] == request["response_schema"]
    assert replacement["job_id"] != request["job_id"]
    assert replacement["request_sha256"] != request["request_sha256"]
    assert state["status"] == "active"
    assert state["run_id"] == json.loads(brief_before)["run_id"]
    assert state["run_dir"] == str(run_dir.resolve())
    assert state["correlation_id"] == correlation_id
    assert state["last_job_id"] == replacement_job_id
    assert state["failed_external_job_replacement"]["source_job_id"] == request["job_id"]
    assert state["failed_external_job_replacement"]["replacement_job_id"] == replacement_job_id

    coordinator.atomic_write_json(
        job_root / "inbox" / f"{replacement_job_id}.json",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": replacement["request_sha256"],
            "model": "gemini-3.5-flash-lite",
            "completed_at": "2026-09-10T12:30:00+08:00",
            "result": {"ok": True},
        },
    )

    def consume_retry(local_run_dir: Path, local_job_root: Path) -> dict[str, object]:
        assert local_run_dir == run_dir
        assert local_job_root == job_root
        return {
            "status": "complete",
            "external_result": consume_external_response(local_job_root, replacement),
        }

    summary = coordinator.cycle_once(
        queue_root,
        tick=consume_retry,
        process=lambda *_args, **_kwargs: pytest.fail("replacement result is already available"),
        exact_run_ids=[json.loads(brief_before)["run_id"]],
        lane_mode=True,
    )
    completed = coordinator.read_run_state(run_dir, queue_root)

    assert summary["complete"] == 1
    assert summary["failed"] == 0
    assert completed["status"] == "complete"
    assert completed["result"]["external_result"] == {"ok": True}


@pytest.mark.parametrize("lane", ["new", "rewrite"])
def test_pending_writer_lite_retry_continues_native_tick_to_reviewer_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lane: str,
) -> None:
    run_dir, queue_root, job_root, request, correlation_id, writer_result = (
        _native_pending_writer_fixture(tmp_path, monkeypatch, lane=lane)
    )
    brief_before = (run_dir / "brief.json").read_bytes()
    _use_source_lite_route(monkeypatch)

    result = _repair(run_dir, queue_root, job_root, request, correlation_id, lane=lane)
    replacement_job_id = str(result["replacement_job_id"])
    replacement_path = job_root / "outbox" / f"{replacement_job_id}.json"
    replacement = json.loads(replacement_path.read_text(encoding="utf-8"))

    coordinator.atomic_write_json(
        job_root / "inbox" / f"{replacement_job_id}.json",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": replacement["request_sha256"],
            "model": "gemini-3.5-flash-lite",
            "completed_at": "2026-09-10T12:40:00+08:00",
            "result": writer_result,
        },
    )

    state = coordinator.read_run_state(run_dir, queue_root)
    status = coordinator._advance(
        queue_root,
        state,
        outbox.run_pipeline_tick,
        job_queue_root=job_root,
    )
    pending = coordinator.read_run_state(run_dir, queue_root)
    reviewer_path = job_root / "outbox" / f"{pending['last_job_id']}.json"
    reviewer_request = json.loads(reviewer_path.read_text(encoding="utf-8"))
    external_candidate = json.loads(
        (run_dir / "attempts" / "01" / "external-candidate.json").read_text(
            encoding="utf-8"
        )
    )
    writer_operation = json.loads(
        (run_dir / "attempts" / "01" / "writer-operation.json").read_text(
            encoding="utf-8"
        )
    )
    reviewer_operation = json.loads(
        (run_dir / "attempts" / "01" / "reviewer-operation.json").read_text(
            encoding="utf-8"
        )
    )

    assert status == "pending"
    assert pending["status"] == "active"
    assert pending["run_id"] == json.loads(brief_before)["run_id"]
    assert pending["correlation_id"] == correlation_id
    assert (run_dir / "brief.json").read_bytes() == brief_before
    assert (job_root / "archive" / f"{request['job_id']}.json").is_file()
    assert not (job_root / "outbox" / f"{request['job_id']}.json").exists()
    assert replacement["role"] == "writer"
    assert replacement["model"] == "gemini-3.5-flash-lite"
    assert replacement["namespace"] == request["namespace"]
    assert replacement["prompt"] == request["prompt"]
    assert replacement["response_schema"] == request["response_schema"]
    assert writer_operation["role"] == "writer"
    assert writer_operation["model"] == "gemini-3.5-flash-lite"
    assert writer_operation["status"] == "success"
    assert external_candidate == writer_result
    assert not (run_dir / "candidate.json").exists()
    assert reviewer_operation["role"] == "reviewer"
    assert reviewer_operation["model"] == "gemini-3.1-flash-lite"
    assert reviewer_operation["status"] == "pending"
    assert reviewer_request["role"] == "reviewer"
    assert reviewer_request["model"] == "gemini-3.1-flash-lite"
    assert reviewer_request["namespace"] == request["namespace"]
    assert pending["last_job_id"] == reviewer_request["job_id"]
    assert pending["failed_external_job_replacement"]["replacement_job_id"] == replacement_job_id


@pytest.mark.parametrize(
    ("case", "mutate", "match"),
    [
        (
            "processing",
            lambda _queue_root, job_root, request: (
                (job_root / "processing").mkdir(parents=True, exist_ok=True),
                (job_root / "outbox" / f"{request['job_id']}.json").replace(
                    job_root / "processing" / f"{request['job_id']}.json"
                ),
            ),
            "claimed source job",
        ),
        (
            "success",
            lambda _queue_root, job_root, request: coordinator.atomic_write_json(
                job_root / "inbox" / f"{request['job_id']}.json",
                {
                    "schema_version": 1,
                    "job_id": request["job_id"],
                    "request_sha256": request["request_sha256"],
                    "model": request["model"],
                    "completed_at": "2026-09-10T12:31:00+08:00",
                    "result": {"ok": True},
                },
            ),
            "source provider outcome",
        ),
        (
            "attempt",
            lambda _queue_root, job_root, request: coordinator.atomic_write_json(
                job_root / "production-attempts" / f"{request['job_id']}.attempt",
                {
                    "schema_version": 1,
                    "job_id": request["job_id"],
                    "request_sha256": request["request_sha256"],
                    "attempt_status": "started",
                },
            ),
            "production attempt evidence",
        ),
    ],
)
def test_pending_writer_lite_retry_rejects_unsafe_source_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    mutate,
    match: str,
) -> None:
    run_dir, queue_root, job_root, request, correlation_id = _pending_writer_fixture(
        tmp_path,
        monkeypatch,
        lane="new",
    )
    mutate(queue_root, job_root, request)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match=match):
        _repair(run_dir, queue_root, job_root, request, correlation_id, lane="new")

    assert _file_snapshot(queue_root) == before

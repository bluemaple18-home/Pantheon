from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

import pytest

from scripts import agy_gemini_runner as runner
from scripts import agy_seo_copy_pipeline as editorial
from scripts import pantheon_four_lane_acceptance_controller as controller
from tests.test_agy_multilingual_pipeline import (
    external_locale_plan,
    non_tarot_external_candidate,
    non_tarot_translation_brief,
)
from tests.test_agy_seo_copy_pipeline import (
    make_article,
    make_deterministic_green_create_article,
    make_external_create_article,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _parent_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD^"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _sealed_executable(tmp_path: Path) -> tuple[Path, str]:
    executable = (tmp_path / "sealed-client").resolve()
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return executable, _sha(executable)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _request(
    tmp_path: Path,
    *,
    kind: str,
    source: Path,
    responses: tuple[controller.SealedResponse, ...],
    lane: str = "new",
    run_id: str = "shadow-new-001",
) -> controller.TraceCompileRequest:
    stage_root = (tmp_path / "staging").resolve()
    queue_root = (tmp_path / "runtime-queue" / "lanes" / lane).resolve()
    return controller.TraceCompileRequest(
        kind=kind,  # type: ignore[arg-type]
        source_run_dir=source.resolve(),
        staging_root=stage_root,
        evidence_bundle_path=(stage_root / "bundle.json").resolve(),
        accepted_base_sha=_head(),
        actor_sha=_head(),
        actor_root=Path.cwd(),
        generation="acceptance-gen-01",
        lane_queue_root=queue_root,
        lane=lane,
        run_id=run_id,
        namespace=hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24],
        session_id="session-ca-001",
        responses=responses,
        max_repairs=0,
    )


def _editorial_source_and_responses(tmp_path: Path) -> tuple[Path, tuple[controller.SealedResponse, ...]]:
    source = tmp_path / "editorial-source"
    target = make_deterministic_green_create_article("TRACE-CREATE-001")
    brief = {
        "schema_version": 1,
        "run_id": "shadow-new-001",
        "mode": "create",
        "articles": [{"matrix": {"id": target["id"], "title": target["title"], "intent": "trace"}, "target": target}],
    }
    _write_json(source / "brief.json", brief)
    writer = {"articles": [make_external_create_article(target)]}
    candidate = editorial.hydrate_candidate(brief, writer)
    reviewer = {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}
    executable, digest = _sealed_executable(tmp_path)
    return source, (
        controller.SealedResponse("writer", "writer-test", writer, executable, digest),
        controller.SealedResponse("reviewer", "reviewer-test", reviewer, executable, digest),
    )


def _translation_source_and_responses(tmp_path: Path) -> tuple[Path, tuple[controller.SealedResponse, ...]]:
    source = tmp_path / "translation-source"
    brief = non_tarot_translation_brief("ko")
    brief["run_id"] = "shadow-i18n-new-001"
    _write_json(source / "brief.json", brief)
    plan = external_locale_plan(brief)
    outline = plan["articles"][0]["ordered_h2_outline"]
    candidate = non_tarot_external_candidate(outline)
    reviewer = {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}
    executable, digest = _sealed_executable(tmp_path)
    return source, (
        controller.SealedResponse("writer", "writer-test", plan, executable, digest),
        controller.SealedResponse("writer", "writer-test", candidate, executable, digest),
        controller.SealedResponse("reviewer", "reviewer-test", reviewer, executable, digest),
    )


def _assert_r2_loadable(result: dict[str, object], request: controller.TraceCompileRequest) -> None:
    bundle_path = Path(str(result["bundle_path"]))
    previous = os.environ.get("PANTHEON_RUNTIME_GENERATION")
    os.environ["PANTHEON_RUNTIME_GENERATION"] = request.generation
    try:
        bundle = runner._load_acceptance_sealed_replay_bundle(
            bundle_path,
            str(result["expected_bundle_digest"]),
            Path.cwd(),
            request.lane_queue_root,
            request.lane,
            request.run_id,
        )
    finally:
        if previous is None:
            os.environ.pop("PANTHEON_RUNTIME_GENERATION", None)
        else:
            os.environ["PANTHEON_RUNTIME_GENERATION"] = previous
    assert bundle.lane == request.lane
    assert bundle.run_id == request.run_id
    for entry, response in zip(bundle.entries, request.responses, strict=True):
        entry.validate_result(response.payload)


def test_editorial_trace_compiles_through_production_loop_and_r2_loader(tmp_path: Path) -> None:
    source, responses = _editorial_source_and_responses(tmp_path)
    request = _request(tmp_path, kind="editorial", source=source, responses=responses)

    result = controller.compile_lane_trace(request)

    assert result["trace_entries"] == 2
    assert [item["role"] for item in result["bundle"]["entries"]] == ["writer", "reviewer"]  # type: ignore[index]
    _assert_r2_loadable(result, request)
    assert not request.lane_queue_root.exists()


def test_translation_trace_compiles_through_production_loop_and_r2_loader(tmp_path: Path) -> None:
    source, responses = _translation_source_and_responses(tmp_path)
    request = _request(
        tmp_path,
        kind="translation",
        source=source,
        responses=responses,
        lane="i18n-new",
        run_id="shadow-i18n-new-001",
    )

    result = controller.compile_lane_trace(request)

    assert result["trace_entries"] == 3
    assert [item["role"] for item in result["bundle"]["entries"]] == ["writer", "writer", "reviewer"]  # type: ignore[index]
    _assert_r2_loadable(result, request)
    assert not request.lane_queue_root.exists()


def test_writer_payload_changes_reviewer_request_identity(tmp_path: Path) -> None:
    source, responses = _editorial_source_and_responses(tmp_path)
    first = _request(tmp_path, kind="editorial", source=source, responses=responses)
    first_result = controller.compile_lane_trace(first)
    changed_writer = json.loads(json.dumps(responses[0].payload, ensure_ascii=False))
    changed_writer["articles"][0]["answer"] = "這是不同的封存 Writer 回應，仍然不能替讀者下結論。"
    second_responses = (
        controller.SealedResponse("writer", "writer-test", changed_writer, responses[0].executable_path, responses[0].executable_sha256),
        responses[1],
    )
    second = _request(tmp_path / "second", kind="editorial", source=source, responses=second_responses)
    second_brief = json.loads((source / "brief.json").read_text(encoding="utf-8"))
    second_brief["articles"][0]["target"]["answer"] = changed_writer["articles"][0]["answer"]
    _write_json(second.source_run_dir / "brief.json", second_brief)

    second_result = controller.compile_lane_trace(second)

    first_reviewer = first_result["bundle"]["entries"][1]["request_sha256"]  # type: ignore[index]
    second_reviewer = second_result["bundle"]["entries"][1]["request_sha256"]  # type: ignore[index]
    assert first_reviewer != second_reviewer


def test_deterministic_finding_omits_reviewer_and_trace_records_only_writer(tmp_path: Path) -> None:
    source = tmp_path / "deterministic-source"
    target = make_article("TRACE-DETERMINISTIC-001")
    brief = {
        "schema_version": 1,
        "run_id": "shadow-new-001",
        "mode": "create",
        "articles": [{"matrix": {"id": target["id"], "title": target["title"], "intent": "trace"}, "target": target}],
    }
    _write_json(source / "brief.json", brief)
    executable, digest = _sealed_executable(tmp_path)
    writer = {"articles": [make_external_create_article(target)]}
    request = _request(
        tmp_path,
        kind="editorial",
        source=source,
        responses=(controller.SealedResponse("writer", "writer-test", writer, executable, digest),),
    )

    result = controller.compile_lane_trace(request)

    assert [item["role"] for item in result["bundle"]["entries"]] == ["writer"]  # type: ignore[index]
    _assert_r2_loadable(result, request)


def test_translation_second_writer_model_drift_fails_closed(tmp_path: Path) -> None:
    source, responses = _translation_source_and_responses(tmp_path)
    drifted = (
        responses[0],
        controller.SealedResponse("writer", "writer-drift", responses[1].payload, responses[1].executable_path, responses[1].executable_sha256),
        responses[2],
    )
    request = _request(
        tmp_path,
        kind="translation",
        source=source,
        responses=drifted,
        lane="i18n-new",
        run_id="shadow-i18n-new-001",
    )

    with pytest.raises(controller.TraceCompilerBlocked, match="model drift"):
        controller.compile_lane_trace(request)
    assert not request.lane_queue_root.exists()


@pytest.mark.parametrize("mutation", ["exhausted", "wrong-role", "too-many", "bad-actor", "noncanonical-root"])
def test_trace_compiler_fails_closed_before_runtime_queue_write(tmp_path: Path, mutation: str) -> None:
    source, responses = _editorial_source_and_responses(tmp_path)
    request = _request(tmp_path, kind="editorial", source=source, responses=responses)
    if mutation == "exhausted":
        request = _request(tmp_path, kind="editorial", source=source, responses=responses[:1])
    elif mutation == "wrong-role":
        request = _request(tmp_path, kind="editorial", source=source, responses=(responses[1], responses[0]))
    elif mutation == "too-many":
        request = _request(tmp_path, kind="editorial", source=source, responses=responses * 9)
    elif mutation == "bad-actor":
        request = controller.TraceCompileRequest(
            **{**request.__dict__, "accepted_base_sha": _parent_head(), "actor_sha": _parent_head()}
        )
    else:
        request = controller.TraceCompileRequest(**{**request.__dict__, "staging_root": Path("relative")})

    with pytest.raises(controller.TraceCompilerBlocked):
        controller.compile_lane_trace(request)
    assert not request.lane_queue_root.exists()

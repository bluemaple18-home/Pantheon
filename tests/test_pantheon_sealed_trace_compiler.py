from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
from dataclasses import replace

import pytest

from scripts import agy_gemini_runner as runner
from scripts import agy_seo_copy_pipeline as editorial
from scripts import pantheon_sealed_trace_compiler as compiler
from tests.test_agy_multilingual_pipeline import (
    external_locale_plan,
    non_tarot_external_candidate,
    non_tarot_translation_brief,
)
from tests.test_agy_seo_copy_pipeline import (
    make_deterministic_green_create_article,
    make_external_create_article,
    make_rewrite_brief,
    make_rewrite_publication_policy,
    make_rewrite_sections,
)


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _request(tmp_path: Path, responses: tuple[compiler.SealedResponse, ...]) -> compiler.SealedTraceCompileRequest:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = (tmp_path / "source").resolve()
    target = make_deterministic_green_create_article("SEALED-TRACE-001")
    brief = {"schema_version": 1, "run_id": "sealed-trace-001", "mode": "create", "articles": [{"matrix": {"id": target["id"], "title": target["title"], "intent": "trace"}, "target": target}]}
    source.mkdir()
    source.chmod(0o700)
    (source / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    stage = (tmp_path / "evidence").resolve()
    stage.mkdir(mode=0o700)
    queue = (tmp_path / "queue" / "lanes" / "new").resolve()
    queue.mkdir(parents=True)
    return compiler.SealedTraceCompileRequest("editorial", source, compiler.strict_source_tree_digest(source), stage, stage / "bundle", _head(), _head(), Path(compiler.__file__).resolve().parents[1], "sealed-gen-01", queue, "new", "sealed-trace-001", hashlib.sha256(b"sealed-trace-001").hexdigest()[:24], "sealed-session-01", responses)


def _responses(tmp_path: Path) -> tuple[compiler.SealedResponse, ...]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    executable = (tmp_path / "sealed-client").resolve()
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    target = make_deterministic_green_create_article("SEALED-TRACE-001")
    writer = {"articles": [make_external_create_article(target)]}
    reviewer = {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}
    return (compiler.SealedResponse("writer", "writer-test", writer, executable, digest), compiler.SealedResponse("reviewer", "reviewer-test", reviewer, executable, digest))


def test_compiles_actual_editorial_trace_and_r2_loader_without_queue_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = _responses(tmp_path)
    request = _request(tmp_path, responses)
    monkeypatch.setattr(compiler, "_git", lambda _request: None)

    result = compiler.compile_sealed_trace(request)

    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", request.generation)
    bundle = runner._load_acceptance_sealed_replay_bundle(request.evidence_artifact_dir / "bundle.json", str(result["raw_bundle_sha256"]), request.actor_root, request.lane_queue_root, request.lane, request.run_id)
    assert bundle.provider_call_budget == len(bundle.entries) == 2
    assert all(entry.required for entry in bundle.entries)
    for entry, response in zip(bundle.entries, responses, strict=True):
        entry.validate_result(response.payload)
    artifact = request.evidence_artifact_dir
    receipt = json.loads((artifact / "compile-receipt.json").read_text(encoding="utf-8"))
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o700
    assert all(stat.S_IMODE((artifact / name).stat().st_mode) == 0o600 for name in ("bundle.json", "compile-receipt.json"))
    assert receipt["raw_bundle_sha256"] == result["raw_bundle_sha256"]
    assert receipt["source_tree_digest"] == request.source_tree_digest
    assert not list(request.lane_queue_root.rglob("*"))


@pytest.mark.parametrize("mutation", ["exhausted", "unused", "role", "race"])
def test_red_cases_leave_runtime_queue_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    responses = _responses(tmp_path)
    if mutation == "exhausted":
        responses = responses[:1]
    elif mutation == "unused":
        responses = responses + responses[:1]
    elif mutation == "role":
        responses = (responses[1], responses[0])
    request = _request(tmp_path, responses)
    if mutation == "race":
        request.evidence_artifact_dir.mkdir()
    monkeypatch.setattr(compiler, "_git", lambda _request: None)
    with pytest.raises(compiler.SealedTraceCompilerBlocked):
        compiler.compile_sealed_trace(request)
    assert not list(request.lane_queue_root.rglob("*"))


@pytest.mark.parametrize("mutation", ["dirty", "head", "base"])
def test_git_authority_rejects_dirty_head_and_base_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    actor = tmp_path / "actor"
    actor.mkdir()
    subprocess.run(["git", "init", "-q", str(actor)], check=True)
    subprocess.run(["git", "-C", str(actor), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(actor), "config", "user.name", "Test"], check=True)
    (actor / "marker").write_text("ok", encoding="utf-8")
    (actor / "scripts").mkdir()
    (actor / "scripts" / "compiler-marker.py").write_text("# marker\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(actor), "add", "marker", "scripts/compiler-marker.py"], check=True)
    subprocess.run(["git", "-C", str(actor), "commit", "-qm", "base"], check=True)
    base = subprocess.run(["git", "-C", str(actor), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(actor), "checkout", "-qb", "side"], check=True)
    (actor / "side").write_text("side", encoding="utf-8")
    subprocess.run(["git", "-C", str(actor), "add", "side"], check=True)
    subprocess.run(["git", "-C", str(actor), "commit", "-qm", "side"], check=True)
    side = subprocess.run(["git", "-C", str(actor), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(actor), "checkout", "-q", "-"], check=True)
    (actor / "next").write_text("next", encoding="utf-8")
    subprocess.run(["git", "-C", str(actor), "add", "next"], check=True)
    subprocess.run(["git", "-C", str(actor), "commit", "-qm", "next"], check=True)
    head = subprocess.run(["git", "-C", str(actor), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    request_root = tmp_path / "request"
    request_root.mkdir()
    request = _request(request_root, _responses(request_root))
    request = compiler.SealedTraceCompileRequest(**{**request.__dict__, "actor_root": actor.resolve(), "actor_sha": head, "accepted_base_sha": head})
    monkeypatch.setattr(compiler, "__file__", str(actor / "scripts" / "compiler-marker.py"))
    if mutation == "dirty":
        (actor / "untracked").write_text("x", encoding="utf-8")
    elif mutation == "head":
        request = compiler.SealedTraceCompileRequest(**{**request.__dict__, "actor_sha": base, "accepted_base_sha": base})
    else:
        request = compiler.SealedTraceCompileRequest(**{**request.__dict__, "accepted_base_sha": side})
    with pytest.raises(compiler.SealedTraceCompilerBlocked):
        compiler._git(request)


def test_true_publish_claim_race_has_one_complete_artifact_and_no_overwrite(tmp_path: Path) -> None:
    parent = (tmp_path / "evidence").resolve()
    parent.mkdir(mode=0o700)
    destination = parent / "artifact"
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def publish() -> None:
        barrier.wait()
        try:
            compiler._publish_artifact(destination, b'{"bundle":1}', b'{"receipt":1}')
            outcomes.append("published")
        except compiler.SealedTraceCompilerBlocked:
            outcomes.append("blocked")

    first = threading.Thread(target=publish)
    second = threading.Thread(target=publish)
    first.start()
    second.start()
    first.join()
    second.join()

    assert sorted(outcomes) == ["blocked", "published"]
    assert (destination / "bundle.json").read_bytes() == b'{"bundle":1}'
    assert (destination / "compile-receipt.json").read_bytes() == b'{"receipt":1}'
    assert not (parent / ".artifact.claim").exists()


def test_source_digest_pre_and_post_drift_leave_no_artifact_or_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pre = _request(tmp_path / "pre", _responses(tmp_path / "pre"))
    monkeypatch.setattr(compiler, "_git", lambda _request: None)
    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="before trace"):
        compiler.compile_sealed_trace(replace(pre, source_tree_digest="0" * 64))
    assert not pre.evidence_artifact_dir.exists()
    assert not list(pre.lane_queue_root.rglob("*"))

    post = _request(tmp_path / "post", _responses(tmp_path / "post"))
    original = compiler.editorial.run_writer_reviewer

    def mutate_source_after_production_loop(*args: object, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        result = original(*args, **kwargs)
        (post.source_run_dir / "brief.json").write_text("{\"drift\":true}", encoding="utf-8")
        return result

    monkeypatch.setattr(compiler.editorial, "run_writer_reviewer", mutate_source_after_production_loop)
    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="after trace"):
        compiler.compile_sealed_trace(post)
    assert not post.evidence_artifact_dir.exists()
    assert not list(post.lane_queue_root.rglob("*"))


@pytest.mark.parametrize("mutation", ["generation", "repairs", "source_symlink", "unsafe_evidence", "executable_digest"])
def test_preflight_boundary_rejections_precede_staging_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    request = _request(tmp_path, _responses(tmp_path))
    monkeypatch.setattr(compiler, "_git", lambda _request: None)
    if mutation == "generation":
        request = replace(request, generation="invalid generation")
    elif mutation == "repairs":
        request = replace(request, max_repairs=3)
    elif mutation == "source_symlink":
        source_target = tmp_path / "source-target"
        source_target.mkdir()
        (source_target / "brief.json").write_text("{}", encoding="utf-8")
        (request.source_run_dir / "brief.json").unlink()
        request.source_run_dir.rmdir()
        request.source_run_dir.symlink_to(source_target, target_is_directory=True)
    elif mutation == "unsafe_evidence":
        request.staging_root.chmod(0o755)
    else:
        request = replace(request, responses=(replace(request.responses[0], executable_sha256="0" * 64), *request.responses[1:]))

    with pytest.raises(compiler.SealedTraceCompilerBlocked):
        compiler.compile_sealed_trace(request)
    assert not (request.staging_root / f"trace-{request.run_id}").exists()
    assert not request.evidence_artifact_dir.exists()
    assert not list(request.lane_queue_root.rglob("*"))


def test_source_tree_digest_rejects_owner_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path, _responses(tmp_path))
    owner = request.source_run_dir.stat().st_uid
    monkeypatch.setattr(compiler.os, "getuid", lambda: owner + 1)

    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="regular directory"):
        compiler.strict_source_tree_digest(request.source_run_dir)


def test_compiles_actual_translation_trace_and_validates_r2_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "translation"
    root.mkdir()
    responses_base = _responses(root)
    brief = non_tarot_translation_brief("ko")
    source = (root / "source").resolve()
    source.mkdir(mode=0o700)
    (source / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    stage = (root / "evidence").resolve()
    stage.mkdir(mode=0o700)
    queue = (root / "queue" / "lanes" / "i18n-new").resolve()
    queue.mkdir(parents=True)
    executable = responses_base[0].executable_path
    digest = responses_base[0].executable_sha256
    plan = external_locale_plan(brief)
    candidate = non_tarot_external_candidate(plan["articles"][0]["ordered_h2_outline"])
    responses = (
        compiler.SealedResponse("writer", "writer-test", plan, executable, digest),
        compiler.SealedResponse("writer", "writer-test", candidate, executable, digest),
        compiler.SealedResponse("reviewer", "reviewer-test", {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}, executable, digest),
    )
    request = compiler.SealedTraceCompileRequest("translation", source, compiler.strict_source_tree_digest(source), stage, stage / "bundle", _head(), _head(), Path(compiler.__file__).resolve().parents[1], "sealed-gen-02", queue, "i18n-new", str(brief["run_id"]), hashlib.sha256(str(brief["run_id"]).encode()).hexdigest()[:24], "sealed-session-02", responses)
    monkeypatch.setattr(compiler, "_git", lambda _request: None)

    result = compiler.compile_sealed_trace(request)

    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", request.generation)
    bundle = runner._load_acceptance_sealed_replay_bundle(request.evidence_artifact_dir / "bundle.json", result["raw_bundle_sha256"], request.actor_root, queue, request.lane, request.run_id)
    assert bundle.provider_call_budget == len(bundle.entries) == 3
    for entry, response in zip(bundle.entries, responses, strict=True):
        entry.validate_result(response.payload)
    assert not list(queue.rglob("*"))


def test_deterministic_rejection_records_writer_only_required_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path, _responses(tmp_path))
    source_brief = make_rewrite_brief("SEALED-REWRITE-001")
    (request.source_run_dir / "brief.json").write_text(json.dumps(source_brief, ensure_ascii=False), encoding="utf-8")
    response = request.responses[0]
    writer_payload = {"articles": [{"slot": "article-01", "bodySections": make_rewrite_sections(), "publicationPolicy": make_rewrite_publication_policy(source_brief["articles"][0])}]}
    request = replace(request, lane="rewrite", run_id=str(source_brief["run_id"]), namespace=hashlib.sha256(str(source_brief["run_id"]).encode()).hexdigest()[:24], source_tree_digest=compiler.strict_source_tree_digest(request.source_run_dir), responses=(compiler.SealedResponse("writer", "writer-test", writer_payload, response.executable_path, response.executable_sha256),), max_repairs=0)
    finding = {"article_id": str(source_brief["articles"][0]["article_id"]), "code": "forced", "message": "deterministic"}
    monkeypatch.setattr(compiler, "_git", lambda _request: None)
    monkeypatch.setattr(compiler.editorial, "rewrite_quality_findings", lambda *_args: [finding])

    result = compiler.compile_sealed_trace(request)

    assert result["entries"] == 1
    assert result["bundle"]["provider_call_budget"] == 1
    assert result["bundle"]["entries"][0]["role"] == "writer"
    assert result["bundle"]["entries"][0]["required"] is True

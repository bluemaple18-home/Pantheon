from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
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
    target = make_deterministic_green_create_article("SEALED-TRACE-001")
    writer = {"articles": [make_external_create_article(target)]}
    reviewer = {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}
    return (
        _response(tmp_path, "writer", "writer", writer),
        _response(tmp_path, "reviewer", "reviewer", reviewer),
    )


def _response(
    tmp_path: Path,
    name: str,
    role: str,
    payload: dict[str, object],
) -> compiler.SealedResponse:
    """產生只接受 RAW_STDIN 並輸出單一封存 payload 的測試 executable。"""
    executable = (tmp_path / f"sealed-client-{name}").resolve()
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    role_marker = runner.V4_ROLE_INSTRUCTIONS[role].encode("utf-8")
    executable.write_text(
        "#!/usr/bin/python3\n"
        "# -*- coding: utf-8 -*-\n"
        "import sys\n"
        f"raw = sys.stdin.buffer.read()\n"
        f"if not raw or {role_marker!r} not in raw:\n"
        "    raise SystemExit(23)\n"
        f"print({rendered!r})\n",
        encoding="utf-8",
    )
    executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return compiler.SealedResponse(
        role, f"{role}-test", payload, executable, hashlib.sha256(executable.read_bytes()).hexdigest()
    )


def _program_response(
    tmp_path: Path,
    name: str,
    role: str,
    payload: dict[str, object],
    program: str,
) -> compiler.SealedResponse:
    executable = (tmp_path / f"sealed-program-{name}").resolve()
    executable.write_text(
        "#!/usr/bin/python3\n# -*- coding: utf-8 -*-\n" + program,
        encoding="utf-8",
    )
    executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return compiler.SealedResponse(
        role, f"{role}-test", payload, executable, hashlib.sha256(executable.read_bytes()).hexdigest()
    )


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
    assert receipt["preflight_entry_count"] == 2
    assert Path(receipt["preflight_evidence_dir"]).is_relative_to(request.staging_root)
    assert len(list((Path(receipt["preflight_evidence_dir"]) / "ledger").glob("*.jsonl"))) == 2
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
    plan = external_locale_plan(brief)
    candidate = non_tarot_external_candidate(plan["articles"][0]["ordered_h2_outline"])
    responses = (
        _response(root, "translation-plan", "writer", plan),
        _response(root, "translation-candidate", "writer", candidate),
        _response(root, "translation-review", "reviewer", {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}),
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
    writer_payload = {"articles": [{"slot": "article-01", "bodySections": make_rewrite_sections(), "publicationPolicy": make_rewrite_publication_policy(source_brief["articles"][0])}]}
    response = _response(tmp_path, "rewrite-writer", "writer", writer_payload)
    request = replace(request, lane="rewrite", run_id=str(source_brief["run_id"]), namespace=hashlib.sha256(str(source_brief["run_id"]).encode()).hexdigest()[:24], source_tree_digest=compiler.strict_source_tree_digest(request.source_run_dir), responses=(response,), max_repairs=0)
    finding = {"article_id": str(source_brief["articles"][0]["article_id"]), "code": "forced", "message": "deterministic"}
    monkeypatch.setattr(compiler, "_git", lambda _request: None)
    monkeypatch.setattr(compiler.editorial, "rewrite_quality_findings", lambda *_args: [finding])

    result = compiler.compile_sealed_trace(request)

    assert result["entries"] == 1
    assert result["bundle"]["provider_call_budget"] == 1
    assert result["bundle"]["entries"][0]["role"] == "writer"
    assert result["bundle"]["entries"][0]["required"] is True


@pytest.mark.parametrize("drift", ["source", "queue"])
def test_post_preflight_authority_barrier_rejects_source_or_queue_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    original, reviewer = _responses(tmp_path)
    request = _request(tmp_path, (original, reviewer))
    target = request.source_run_dir / "brief.json" if drift == "source" else request.lane_queue_root / "preflight-drift.json"
    payload = json.dumps(original.payload, ensure_ascii=False, separators=(",", ":"))
    program = (
        "import sys\n"
        "raw = sys.stdin.buffer.read()\n"
        f"if {runner.V4_ROLE_INSTRUCTIONS['writer'].encode('utf-8')!r} not in raw: raise SystemExit(23)\n"
        f"open({str(target)!r}, 'w', encoding='utf-8').write('preflight-drift')\n"
        f"print({payload!r})\n"
    )
    mutating = _program_response(tmp_path, f"mutate-{drift}", "writer", original.payload, program)
    request = replace(request, responses=(mutating, reviewer))
    monkeypatch.setattr(compiler, "_git", lambda _request: None)

    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="after preflight"):
        compiler.compile_sealed_trace(request)

    assert not request.evidence_artifact_dir.exists()
    if drift == "source":
        assert not list(request.lane_queue_root.rglob("*"))
    else:
        assert target.exists()
        target.unlink()
        assert not list(request.lane_queue_root.rglob("*"))


def test_post_preflight_actor_barrier_is_reinvoked_before_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path, _responses(tmp_path))
    calls: list[str] = []

    def verify_actor(_request: compiler.SealedTraceCompileRequest) -> None:
        calls.append("verified")

    monkeypatch.setattr(compiler, "_git", verify_actor)

    compiler.compile_sealed_trace(request)

    assert calls == ["verified", "verified"]


def test_post_preflight_actor_barrier_rejects_executable_dirty_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = tmp_path / "actor"
    actor.mkdir()
    subprocess.run(["git", "init", "-q", str(actor)], check=True)
    subprocess.run(["git", "-C", str(actor), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(actor), "config", "user.name", "Test"], check=True)
    (actor / "scripts").mkdir()
    marker = actor / "scripts" / "compiler-marker.py"
    marker.write_text("# marker\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(actor), "add", "scripts/compiler-marker.py"], check=True)
    subprocess.run(["git", "-C", str(actor), "commit", "-qm", "base"], check=True)
    actor_sha = subprocess.run(
        ["git", "-C", str(actor), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    original, reviewer = _responses(tmp_path / "request")
    request = _request(tmp_path / "request", (original, reviewer))
    payload = json.dumps(original.payload, ensure_ascii=False, separators=(",", ":"))
    program = (
        "import sys\n"
        "raw = sys.stdin.buffer.read()\n"
        f"if {runner.V4_ROLE_INSTRUCTIONS['writer'].encode('utf-8')!r} not in raw: raise SystemExit(23)\n"
        f"open({str(actor / 'untracked')!r}, 'w', encoding='utf-8').write('dirty')\n"
        f"print({payload!r})\n"
    )
    mutating = _program_response(tmp_path / "request", "dirty-actor", "writer", original.payload, program)
    request = replace(request, actor_root=actor.resolve(), actor_sha=actor_sha, accepted_base_sha=actor_sha, responses=(mutating, reviewer))
    monkeypatch.setattr(compiler, "__file__", str(marker))

    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="actor head or worktree is dirty"):
        compiler.compile_sealed_trace(request)

    assert not request.evidence_artifact_dir.exists()
    assert not list(request.lane_queue_root.rglob("*"))


@pytest.mark.parametrize("kind", ["exit_zero", "invalid_json", "multiple_json", "schema_invalid", "nonzero"])
def test_executable_preflight_rejects_bad_output_before_artifact_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    original = _responses(tmp_path)[0]
    if kind == "exit_zero":
        program = "import sys\nsys.stdin.buffer.read()\n"
    elif kind == "invalid_json":
        program = "import sys\nsys.stdin.buffer.read()\nprint('not-json')\n"
    elif kind == "multiple_json":
        program = "import sys\nsys.stdin.buffer.read()\nprint('{}{}')\n"
    elif kind == "schema_invalid":
        program = "import sys\nsys.stdin.buffer.read()\nprint('{\\\"articles\\\":[]}')\n"
    else:
        program = "import sys\nsys.stdin.buffer.read()\nraise SystemExit(7)\n"
    rejected = _program_response(tmp_path, kind, "writer", original.payload, program)
    request = _request(tmp_path, (rejected, _responses(tmp_path)[1]))
    monkeypatch.setattr(compiler, "_git", lambda _request: None)

    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="sealed executable result binding"):
        compiler.compile_sealed_trace(request)

    assert not request.evidence_artifact_dir.exists()
    assert not list(request.lane_queue_root.rglob("*"))


def test_executable_preflight_rejects_valid_payload_mismatch_before_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original, reviewer = _responses(tmp_path)
    actual = json.loads(json.dumps(original.payload, ensure_ascii=False))
    actual["articles"][0]["answer"] = "另一份同樣合法但不同的答案。"
    program = (
        "import sys\n"
        "raw = sys.stdin.buffer.read()\n"
        f"if {runner.V4_ROLE_INSTRUCTIONS['writer'].encode('utf-8')!r} not in raw: raise SystemExit(23)\n"
        f"print({json.dumps(actual, ensure_ascii=False, separators=(',', ':'))!r})\n"
    )
    mismatch = _program_response(tmp_path, "mismatch", "writer", original.payload, program)
    request = _request(tmp_path, (mismatch, reviewer))
    monkeypatch.setattr(compiler, "_git", lambda _request: None)

    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="sealed executable result binding"):
        compiler.compile_sealed_trace(request)

    assert not request.evidence_artifact_dir.exists()
    assert not list(request.lane_queue_root.rglob("*"))


def test_executable_preflight_rejects_timeout_and_digest_drift_before_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original, reviewer = _responses(tmp_path)
    timeout = _program_response(
        tmp_path,
        "timeout",
        "writer",
        original.payload,
        "import sys, time\nsys.stdin.buffer.read()\ntime.sleep(0.1)\nprint('{}')\n",
    )
    request = _request(tmp_path, (timeout, reviewer))
    monkeypatch.setattr(compiler, "_git", lambda _request: None)
    monkeypatch.setattr(compiler, "PREFLIGHT_TIMEOUT_MILLISECONDS", 1)
    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="sealed executable result binding"):
        compiler.compile_sealed_trace(request)
    assert not request.evidence_artifact_dir.exists()

    original, reviewer = _responses(tmp_path / "digest")
    drift = _request(tmp_path / "digest", (original, reviewer))
    pipeline = compiler.editorial.run_writer_reviewer

    def mutate_executable(*args: object, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        result = pipeline(*args, **kwargs)
        original.executable_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        original.executable_path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        return result

    monkeypatch.setattr(compiler.editorial, "run_writer_reviewer", mutate_executable)
    monkeypatch.setattr(compiler, "PREFLIGHT_TIMEOUT_MILLISECONDS", 5_000)
    with pytest.raises(compiler.SealedTraceCompilerBlocked, match="preflight is invalid"):
        compiler.compile_sealed_trace(drift)
    assert not drift.evidence_artifact_dir.exists()
    assert not list(drift.lane_queue_root.rglob("*"))


def test_preflight_unique_bindings_allow_same_executable_for_two_records(tmp_path: Path) -> None:
    payload = {"value": "sealed"}
    response = _program_response(
        tmp_path,
        "shared",
        "writer",
        payload,
        "import sys\n"
        "raw = sys.stdin.buffer.read()\n"
        f"if {runner.V4_ROLE_INSTRUCTIONS['writer'].encode('utf-8')!r} not in raw: raise SystemExit(23)\n"
        "print('{\\\"value\\\":\\\"sealed\\\"}')\n",
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }
    first = compiler.outbox.build_external_request(
        namespace="sealed-ns", role="writer", model="writer-test", prompt="same", response_schema=schema
    )
    second = compiler.outbox.build_external_request(
        namespace="sealed-ns", role="writer", model="writer-test", prompt="same", response_schema=schema
    )
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)

    compiler._preflight_sealed_executable_records(stage, ((first, response), (second, response)))

    ledgers = sorted((stage / "sealed-executable-preflight" / "ledger").glob("*.jsonl"))
    assert len(ledgers) == 2
    operation_ids = {json.loads(path.read_text(encoding="utf-8").splitlines()[0])["operation_id"] for path in ledgers}
    assert len(operation_ids) == 2


@pytest.mark.parametrize("failure_at", ["directory", "parent"])
def test_publish_fsync_failure_closes_fds_and_cleans_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_at: str
) -> None:
    parent = tmp_path / "evidence"
    parent.mkdir(mode=0o700)
    destination = parent / "artifact"
    real_fsync = os.fsync
    real_close = os.close
    closed: list[int] = []
    fsync_calls: list[int] = []

    def fail_fsync(descriptor: int) -> None:
        fsync_calls.append(descriptor)
        target_call = 4 if failure_at == "directory" else 5
        if len(fsync_calls) == target_call:
            raise OSError("injected fsync failure")
        real_fsync(descriptor)

    def track_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    monkeypatch.setattr(compiler.os, "fsync", fail_fsync)
    monkeypatch.setattr(compiler.os, "close", track_close)
    with pytest.raises(OSError, match="injected fsync failure"):
        compiler._publish_artifact(destination, b'{"bundle":1}', b'{"receipt":1}')

    failed_call = 3 if failure_at == "directory" else 4
    assert fsync_calls[failed_call] in closed
    assert not (parent / ".artifact.claim").exists()
    assert not list(parent.glob(".artifact.*"))
    assert not destination.exists()


def test_parent_fsync_failure_quarantines_noncanonical_artifact_when_removal_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "evidence"
    parent.mkdir(mode=0o700)
    destination = parent / "artifact"
    real_fsync = os.fsync
    real_close = os.close
    real_rmtree = shutil.rmtree
    closed: list[int] = []
    fsync_calls: list[int] = []
    quarantines: list[Path] = []

    def fail_parent_fsync(descriptor: int) -> None:
        fsync_calls.append(descriptor)
        if len(fsync_calls) == 5:
            raise OSError("injected parent fsync failure")
        real_fsync(descriptor)

    def track_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    def leave_quarantine(path: str | Path, *args: object, **kwargs: object) -> None:
        candidate = Path(path)
        if candidate.parent == parent and candidate.name.startswith(".artifact.failed-"):
            quarantines.append(candidate)
            raise OSError("injected quarantine removal failure")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(compiler.os, "fsync", fail_parent_fsync)
    monkeypatch.setattr(compiler.os, "close", track_close)
    monkeypatch.setattr(compiler.shutil, "rmtree", leave_quarantine)
    with pytest.raises(OSError, match="injected parent fsync failure"):
        compiler._publish_artifact(destination, b'{"bundle":1}', b'{"receipt":1}')

    assert fsync_calls[4] in closed
    assert not destination.exists()
    assert not (parent / ".artifact.claim").exists()
    assert quarantines and (quarantines[0] / "artifact" / "bundle.json").is_file()
    real_rmtree(quarantines[0])
    assert not list(parent.glob(".artifact.failed-*"))

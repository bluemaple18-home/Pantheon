from __future__ import annotations

import hashlib
import inspect
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.agy_gemini_outbox import build_external_request, create_external_request
from scripts.agy_gemini_runner import (
    ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE,
    ACCEPTANCE_SEALED_REPLAY_MODE,
    process_once,
)
from scripts import pantheon_content_runtime_manifest as runtime_manifest


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


ACCEPTED_BASE_SHA = "b13bc765e9f694b3d9eeefc65335a5410cf5d898"


def _repo_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _namespace_for_run_id(run_id: str) -> str:
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_json(payload: dict[str, object]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _write_sealed_executable(tmp_path: Path, result: dict[str, object] | None = None) -> Path:
    payload = json.dumps(result or {"ok": True}, ensure_ascii=False, sort_keys=True)
    executable = tmp_path / "sealed-provider.py"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        f"print({payload!r})\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return executable


def _write_sealed_authority(
    tmp_path: Path,
    request: dict[str, object],
    executable: Path,
    *,
    lane: str = "new",
    run_id: str = "target-run",
    overrides: dict[str, object] | None = None,
) -> Path:
    executable_sha256 = hashlib.sha256(executable.read_bytes()).hexdigest()
    body: dict[str, object] = {
        "schema_version": 1,
        "mode": ACCEPTANCE_SEALED_REPLAY_MODE,
        "accepted_base_sha": ACCEPTED_BASE_SHA,
        "actor_sha": _repo_head(),
        "lane": lane,
        "run_id": run_id,
        "namespace": _namespace_for_run_id(run_id),
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "role": request["role"],
        "model": request["model"],
        "schema_sha256": request["schema_sha256"],
        "executable_path": str(executable.resolve()),
        "executable_sha256": executable_sha256,
        "live_provider_disabled": True,
        "production_allocator_disabled": True,
    }
    if overrides:
        body.update(overrides)
    authority = {
        **body,
        "authority_digest": hashlib.sha256(_canonical_json_bytes(body)).hexdigest(),
    }
    authority_path = tmp_path / "sealed-authority.json"
    authority_path.write_text(
        json.dumps(authority, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return authority_path


def _bundle_entry(
    request: dict[str, object],
    executable: Path,
    *,
    session_id: str = "session-r2",
    entry_id: str | None = None,
    lane: str = "new",
    run_id: str = "target-run",
    result: dict[str, object] | None = None,
    required: bool = True,
) -> dict[str, object]:
    return {
        "session_id": session_id,
        "entry_id": entry_id or str(request["role"]),
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "namespace": request["namespace"],
        "lane": lane,
        "run_id": run_id,
        "role": request["role"],
        "model": request["model"],
        "schema_sha256": request["schema_sha256"],
        "sealed_result_sha256": _sha256_json(result or {"ok": True}),
        "executable_path": str(executable.resolve()),
        "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "required": required,
    }


def _write_sealed_bundle(
    tmp_path: Path,
    queue: Path,
    entries: list[dict[str, object]],
    *,
    lane: str = "new",
    run_id: str = "target-run",
    generation: str = "generation-r2",
    session_id: str = "session-r2",
    provider_call_budget: int | None = None,
    overrides: dict[str, object] | None = None,
) -> Path:
    body: dict[str, object] = {
        "schema_version": 1,
        "mode": ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE,
        "session_id": session_id,
        "accepted_base_sha": ACCEPTED_BASE_SHA,
        "actor_sha": _repo_head(),
        "generation": generation,
        "queue_root": str(queue.resolve()),
        "lane": lane,
        "run_id": run_id,
        "namespace": _namespace_for_run_id(run_id),
        "provider_call_budget": provider_call_budget or len(entries),
        "entries": entries,
    }
    if overrides:
        body.update(overrides)
    bundle = {
        **body,
        "bundle_digest": hashlib.sha256(_canonical_json_bytes(body)).hexdigest(),
    }
    bundle_path = tmp_path / "sealed-bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return bundle_path


def _run_sealed_bundle_cli(
    capsys: pytest.CaptureFixture[str],
    queue: Path,
    bundle_path: Path,
    *,
    lane: str = "new",
    run_id: str = "target-run",
    expected_bundle_digest: str | None = None,
) -> tuple[int, dict[str, object]]:
    from scripts import agy_gemini_runner as runner

    old_argv = sys.argv
    try:
        sys.argv = [
            "agy_gemini_runner.py",
            "--queue-root",
            str(queue),
            "--lane",
            lane,
            "--exact-run-id",
            run_id,
            "sealed-replay-bundle-process-once",
            "--bundle",
            str(bundle_path),
            "--expected-bundle-digest",
            expected_bundle_digest or hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
        ]
        exit_code = runner.main()
    finally:
        sys.argv = old_argv
    return exit_code, json.loads(capsys.readouterr().out)


def _run_sealed_bundle_close_cli(
    capsys: pytest.CaptureFixture[str],
    queue: Path,
    bundle_path: Path,
    *,
    lane: str = "new",
    run_id: str = "target-run",
    expected_bundle_digest: str | None = None,
) -> tuple[int, dict[str, object]]:
    from scripts import agy_gemini_runner as runner

    old_argv = sys.argv
    try:
        sys.argv = [
            "agy_gemini_runner.py",
            "--queue-root",
            str(queue),
            "--lane",
            lane,
            "--exact-run-id",
            run_id,
            "sealed-replay-bundle-close",
            "--bundle",
            str(bundle_path),
            "--expected-bundle-digest",
            expected_bundle_digest or hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
        ]
        exit_code = runner.main()
    finally:
        sys.argv = old_argv
    return exit_code, json.loads(capsys.readouterr().out)


def _queue_snapshot(queue: Path) -> dict[str, bytes]:
    if not queue.exists():
        return {}
    return {
        str(path.relative_to(queue)): path.read_bytes()
        for path in sorted(queue.rglob("*"))
        if path.is_file()
    }


def test_sealed_bundle_cli_processes_writer_then_reviewer_with_one_bundle(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    namespace = _namespace_for_run_id("target-run")
    writer_request = create_external_request(
        queue,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="writer tick",
        response_schema=SCHEMA,
    )
    reviewer_request = build_external_request(
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="reviewer tick",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(writer_request, executable), _bundle_entry(reviewer_request, executable)],
    )

    first_exit, first_payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)
    create_external_request(
        queue,
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="reviewer tick",
        response_schema=SCHEMA,
    )
    second_exit, second_payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)
    close_exit, close_payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert first_exit == 0
    assert second_exit == 0
    assert close_exit == 0
    assert first_payload["status"] == "processed"
    assert second_payload["status"] == "processed"
    assert close_payload["status"] == "closed"
    assert first_payload["job_id"] == writer_request["job_id"]
    assert second_payload["job_id"] == reviewer_request["job_id"]
    assert first_payload["sealed_replay_bundle"]["session_id"] == "session-r2"
    assert first_payload["sealed_replay_bundle"]["used_provider_calls_before_tick"] == 0
    assert second_payload["sealed_replay_bundle"]["used_provider_calls_before_tick"] == 1
    assert first_payload["sealed_replay_bundle"]["bundle_digest"] == second_payload["sealed_replay_bundle"]["bundle_digest"]
    assert close_payload["sealed_replay_bundle_session"]["delivered_entries"] == [
        "writer",
        "reviewer",
    ]
    assert (queue / "inbox" / f"{writer_request['job_id']}.json").is_file()
    assert (queue / "archive" / f"{writer_request['job_id']}.json").is_file()
    assert (queue / "inbox" / f"{reviewer_request['job_id']}.json").is_file()
    assert (queue / "archive" / f"{reviewer_request['job_id']}.json").is_file()
    assert not (queue / "failed").exists()
    assert not (queue / "production-attempts").exists()


def test_single_job_authority_cannot_authorize_bundle_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    authority_path = _write_sealed_authority(tmp_path, request, executable)
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, authority_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "bundle fields are strict" in payload["error"]
    assert _queue_snapshot(queue) == before


@pytest.mark.parametrize(
    ("case", "bundle_overrides", "entry_overrides", "pending", "expected_error"),
    [
        ("unknown", {}, {"request_sha256": "f" * 64}, "one", "unknown pending request"),
        ("zero", {}, {}, "zero", "zero pending request"),
        ("many", {}, {}, "many", "many pending requests"),
        ("duplicate", {}, "duplicate-entry", "one", "entries are ambiguous"),
        ("wrong_actor", {"actor_sha": "1" * 40}, {}, "one", "actor head mismatch"),
        ("non_ancestor", {"accepted_base_sha": "0" * 40}, {}, "one", "accepted base is not actor ancestor"),
        ("wrong_generation", {"generation": "generation-other"}, {}, "one", "generation mismatch"),
        ("wrong_root", {"queue_root": "/tmp/not-the-queue-root"}, {}, "one", "queue root mismatch"),
        ("wrong_executable", {}, {"executable_sha256": "d" * 64}, "one", "executable digest mismatch"),
        ("missing_session", {}, {"__delete__": "session_id"}, "one", "entry fields are strict"),
        ("missing_entry", {}, {"__delete__": "entry_id"}, "one", "entry fields are strict"),
        ("missing_result", {}, {"__delete__": "sealed_result_sha256"}, "one", "entry fields are strict"),
        ("missing_required", {}, {"__delete__": "required"}, "one", "entry fields are strict"),
        ("wrong_lane", {}, {"lane": "rewrite"}, "one", "identity is invalid"),
        ("wrong_run", {}, {"run_id": "other-run"}, "one", "identity is invalid"),
    ],
)
def test_sealed_bundle_rejects_invalid_authority_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    bundle_overrides: dict[str, object],
    entry_overrides: dict[str, object] | str,
    pending: str,
    expected_error: str,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    namespace = _namespace_for_run_id("target-run")
    if pending == "zero":
        request = build_external_request(
            namespace=namespace,
            role="writer",
            model="gemini-test-writer",
            prompt=f"目標 run {case}",
            response_schema=SCHEMA,
        )
    else:
        request = create_external_request(
            queue,
            namespace=namespace,
            role="writer",
            model="gemini-test-writer",
            prompt=f"目標 run {case}",
            response_schema=SCHEMA,
        )
    if pending == "many":
        create_external_request(
            queue,
            namespace=namespace,
            role="reviewer",
            model="gemini-test-reviewer",
            prompt=f"review run {case}",
            response_schema=SCHEMA,
        )
    executable = _write_sealed_executable(tmp_path)
    entry = _bundle_entry(request, executable)
    if isinstance(entry_overrides, dict):
        if "__delete__" in entry_overrides:
            entry.pop(str(entry_overrides["__delete__"]))
            entry_overrides = {
                key: value
                for key, value in entry_overrides.items()
                if key != "__delete__"
            }
        entry.update(entry_overrides)
        entries = [entry]
    else:
        entries = [entry, dict(entry)]
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        entries,
        overrides=bundle_overrides,
    )
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert expected_error in payload["error"]
    assert _queue_snapshot(queue) == before
    assert not (queue / "processing").exists()
    assert not (queue / "inbox").exists()
    assert not (queue / "archive").exists()
    assert not (queue / "failed").exists()


@pytest.mark.parametrize(
    ("case", "path_mode", "expected_digest", "expected_error"),
    [
        ("digest_mismatch", "normal", "0" * 64, "expected digest mismatch"),
        ("symlink", "symlink", None, "pinned identity is invalid"),
        ("noncanonical", "noncanonical", None, "pinned identity is invalid"),
    ],
)
def test_sealed_bundle_rejects_unpinned_or_swapped_bundle_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    path_mode: str,
    expected_digest: str | None,
    expected_error: str,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt=f"目標 run {case}",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    selected_path = bundle_path
    if path_mode == "symlink":
        selected_path = tmp_path / "bundle-link.json"
        selected_path.symlink_to(bundle_path)
    elif path_mode == "noncanonical":
        (tmp_path / "sub").mkdir()
        selected_path = Path(f"{tmp_path}/sub/../{bundle_path.name}")
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(
        capsys,
        queue,
        selected_path,
        expected_bundle_digest=expected_digest,
    )

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert expected_error in payload["error"]
    assert _queue_snapshot(queue) == before


def test_sealed_bundle_rejects_bundle_swap_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    expected_digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["provider_call_budget"] = 2
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(
        capsys,
        queue,
        bundle_path,
        expected_bundle_digest=expected_digest,
    )

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "expected digest mismatch" in payload["error"]
    assert _queue_snapshot(queue) == before


def test_sealed_bundle_provider_budget_rejects_before_second_tick_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    namespace = _namespace_for_run_id("target-run")
    writer_request = create_external_request(
        queue,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="writer tick",
        response_schema=SCHEMA,
    )
    reviewer_request = build_external_request(
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="reviewer tick",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [
            _bundle_entry(writer_request, executable),
            _bundle_entry(reviewer_request, executable, required=False),
        ],
        provider_call_budget=1,
    )
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    create_external_request(
        queue,
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="reviewer tick",
        response_schema=SCHEMA,
    )
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "provider call budget exhausted" in payload["error"]
    assert _queue_snapshot(queue) == before
    assert not (queue / "processing" / f"{reviewer_request['job_id']}.json").exists()


def test_sealed_bundle_rejects_budget_below_required_count_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    namespace = _namespace_for_run_id("target-run")
    writer_request = create_external_request(
        queue,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="writer tick",
        response_schema=SCHEMA,
    )
    reviewer_request = build_external_request(
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="reviewer tick",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(writer_request, executable), _bundle_entry(reviewer_request, executable)],
        provider_call_budget=1,
    )
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "bundle identity is invalid" in payload["error"]
    assert _queue_snapshot(queue) == before


def test_sealed_bundle_result_digest_mismatch_fails_without_inbox(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path, {"ok": False})
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(request, executable, result={"ok": True})],
    )

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["job_id"] == request["job_id"]
    assert payload["error_type"] == "ValueError"
    assert (queue / "archive" / f"{request['job_id']}.json").is_file()
    assert (queue / "failed" / f"{request['job_id']}.json").is_file()
    assert not (queue / "inbox" / f"{request['job_id']}.json").exists()


def test_sealed_bundle_rejects_replayed_used_entry_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    namespace = _namespace_for_run_id("target-run")
    writer_request = create_external_request(
        queue,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="writer tick",
        response_schema=SCHEMA,
    )
    reviewer_request = build_external_request(
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="reviewer tick",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(writer_request, executable), _bundle_entry(reviewer_request, executable)],
        provider_call_budget=2,
    )
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    archived_writer = queue / "archive" / f"{writer_request['job_id']}.json"
    replayed_writer = queue / "outbox" / f"{writer_request['job_id']}.json"
    replayed_writer.write_bytes(archived_writer.read_bytes())
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "prior delivery evidence" in payload["error"]
    assert _queue_snapshot(queue) == before


def test_sealed_bundle_rejects_cross_session_reuse_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="writer tick",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(request, executable, session_id="session-a")],
        session_id="session-a",
    )
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    replayed = queue / "outbox" / f"{request['job_id']}.json"
    replayed.write_bytes((queue / "archive" / f"{request['job_id']}.json").read_bytes())
    other_session_bundle = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(request, executable, session_id="session-b")],
        session_id="session-b",
    )
    before = _queue_snapshot(queue)

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, other_session_bundle)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "prior delivery evidence" in payload["error"]
    assert _queue_snapshot(queue) == before


def test_sealed_bundle_close_rejects_rebound_entry_authority_after_delivery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="writer tick",
        response_schema=SCHEMA,
    )
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    executable_a = _write_sealed_executable(tmp_path / "a")
    bundle_a = _write_sealed_bundle(
        tmp_path,
        queue,
        [_bundle_entry(request, executable_a, session_id="session-a", entry_id="writer")],
        session_id="session-a",
    )
    assert _run_sealed_bundle_cli(capsys, queue, bundle_a)[0] == 0
    executable_b = _write_sealed_executable(tmp_path / "b", {"ok": False})
    bundle_b = _write_sealed_bundle(
        tmp_path,
        queue,
        [
            _bundle_entry(
                request,
                executable_b,
                session_id="session-a",
                entry_id="writer",
                result={"ok": False},
            )
        ],
        session_id="session-a",
    )

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_b)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "unauthorized state" in payload["error"]


def test_sealed_bundle_forbids_live_provider_env_before_queue_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    before = _queue_snapshot(queue)
    monkeypatch.setenv("GEMINI_API_KEY", "present-but-forbidden")

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "forbids live provider" in payload["error"]
    assert _queue_snapshot(queue) == before


def test_sealed_bundle_claim_time_rejection_returns_nonzero_and_restores_outbox(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import agy_gemini_runner as runner

    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    calls = 0
    original_validate_request = runner.AcceptanceSealedReplayEntry.validate_request

    def reject_after_preflight(
        entry: object,
        selected_request: dict[str, object],
    ) -> None:
        nonlocal calls
        calls += 1
        original_validate_request(entry, selected_request)
        if calls == 2:
            raise ValueError("sealed replay bundle claim-time drift")

    monkeypatch.setattr(
        runner.AcceptanceSealedReplayEntry,
        "validate_request",
        reject_after_preflight,
    )

    exit_code, payload = _run_sealed_bundle_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload == {
        "status": "rejected",
        "reason": "claimed_request_validation_failed",
    }
    assert calls == 2
    assert (queue / "outbox" / f"{request['job_id']}.json").is_file()
    assert not (queue / "processing" / f"{request['job_id']}.json").exists()
    assert not (queue / "inbox").exists()
    assert not (queue / "archive").exists()
    assert not (queue / "failed").exists()


def test_sealed_bundle_close_rejects_unused_required_entry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = build_external_request(
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "unused required entries" in payload["error"]


def test_sealed_bundle_close_rejects_unauthorized_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = build_external_request(
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    create_external_request(
        queue,
        namespace=_namespace_for_run_id("other-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="unauthorized",
        response_schema=SCHEMA,
    )

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "unauthorized state" in payload["error"]


@pytest.mark.parametrize(
    ("case", "relative_path"),
    [
        ("unknown_ledger", "v4/ledger/unknown-job.jsonl"),
        ("unknown_anchor", "v4/anchors/unknown-job.sr2-unknown.json"),
    ],
)
def test_sealed_bundle_close_rejects_unknown_v4_delivery_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    relative_path: str,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt=f"目標 run {case}",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    unknown_path = queue / relative_path
    unknown_path.parent.mkdir(parents=True, exist_ok=True)
    unknown_path.write_text("forensic stray evidence\n", encoding="utf-8")

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "unauthorized state" in payload["error"]


def test_sealed_bundle_close_rejects_delivered_entry_replayed_in_outbox(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    (queue / "outbox" / f"{request['job_id']}.json").write_bytes(
        (queue / "archive" / f"{request['job_id']}.json").read_bytes()
    )

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "incomplete entries" in payload["error"]


def test_sealed_bundle_close_rejects_optional_entry_pending_in_outbox(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    namespace = _namespace_for_run_id("target-run")
    required = create_external_request(
        queue,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="required",
        response_schema=SCHEMA,
    )
    optional = build_external_request(
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="optional",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(
        tmp_path,
        queue,
        [
            _bundle_entry(required, executable, entry_id="required"),
            _bundle_entry(optional, executable, entry_id="optional", required=False),
        ],
    )
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    create_external_request(
        queue,
        namespace=namespace,
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="optional",
        response_schema=SCHEMA,
    )

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "incomplete entries" in payload["error"]


@pytest.mark.parametrize(
    ("case", "remove_directory"),
    [
        ("missing_archive", "archive"),
        ("missing_inbox", "inbox"),
        ("missing_ledger", "v4/ledger"),
        ("missing_anchor", "v4/anchors"),
    ],
)
def test_sealed_bundle_close_rejects_partial_crash_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    remove_directory: str,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", "generation-r2")
    queue = tmp_path / "queue"
    request = create_external_request(
        queue,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt=f"目標 run {case}",
        response_schema=SCHEMA,
    )
    executable = _write_sealed_executable(tmp_path)
    bundle_path = _write_sealed_bundle(tmp_path, queue, [_bundle_entry(request, executable)])
    assert _run_sealed_bundle_cli(capsys, queue, bundle_path)[0] == 0
    root = queue
    for part in remove_directory.split("/"):
        root = root / part
    for path in root.glob("*.json*"):
        path.unlink()

    exit_code, payload = _run_sealed_bundle_close_cli(capsys, queue, bundle_path)

    assert exit_code == 64
    assert payload["status"] == "rejected"
    assert "incomplete entries" in payload["error"] or "unused required entries" in payload["error"]


def test_single_job_sealed_replay_cli_is_not_a_formal_command() -> None:
    from scripts import agy_gemini_runner as runner

    old_argv = sys.argv
    try:
        sys.argv = ["agy_gemini_runner.py", "sealed-replay-process-once"]
        with pytest.raises(SystemExit):
            runner.parse_args()
    finally:
        sys.argv = old_argv


def test_process_once_public_signature_does_not_expose_sealed_bypass() -> None:
    signature = inspect.signature(process_once)

    assert "acceptance_sealed_replay" not in signature.parameters
    assert "claimed_request_validator" not in signature.parameters


def test_public_process_once_fixture_cannot_skip_formal_transport_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    lane_root = queue / "lanes" / "rewrite"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, lane_root, state, logs):
        path.mkdir(parents=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-public-api",
        runtime_digest="a" * 64,
        generation="generation-public-api",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    barrier = tmp_path / "activation.barrier"
    _activate_formal_runtime(tmp_path / "ready", barrier, manifest)
    _set_formal_runner_env(
        monkeypatch,
        manifest_path,
        manifest,
        "com.pantheon.agy-gemini-rewrite",
        activation_token=barrier,
    )
    create_external_request(
        lane_root,
        namespace=_namespace_for_run_id("target-run"),
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    before = _queue_snapshot(lane_root)

    result = process_once(
        lane_root,
        lane="rewrite",
        exact_run_ids=["target-run"],
        generate_json=lambda *_args: {"ok": True},
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "formal_production_transport_env_missing"
    assert _queue_snapshot(lane_root) == before


def test_runner_exact_run_ids_claims_only_matching_namespace(tmp_path: Path) -> None:
    old_request = create_external_request(
        tmp_path,
        namespace=hashlib.sha256(b"old-active-run").hexdigest()[:24],
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="舊 run",
        response_schema=SCHEMA,
    )
    target_request = create_external_request(
        tmp_path,
        namespace=hashlib.sha256(b"target-ko-run").hexdigest()[:24],
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: {"ok": True},
        exact_run_ids=["target-ko-run"],
    )

    assert result["status"] == "processed"
    assert result["job_id"] == target_request["job_id"]
    assert (tmp_path / "outbox" / f"{old_request['job_id']}.json").is_file()
    assert not (tmp_path / "processing" / f"{old_request['job_id']}.json").exists()


def test_runner_exact_run_ids_missing_target_does_not_claim_fallback(
    tmp_path: Path,
) -> None:
    old_request = create_external_request(
        tmp_path,
        namespace=hashlib.sha256(b"old-active-run").hexdigest()[:24],
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="舊 run",
        response_schema=SCHEMA,
    )

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: pytest.fail("missing target must not call provider"),
        exact_run_ids=["missing-target-run"],
    )

    assert result == {"status": "idle"}
    assert (tmp_path / "outbox" / f"{old_request['job_id']}.json").is_file()
    assert not (tmp_path / "processing").exists()


def test_formal_lane_rejects_manifest_drift_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    lane_root = queue / "lanes" / "new"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, lane_root, state, logs):
        path.mkdir(parents=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-lane",
        runtime_digest="2" * 64,
        generation="generation-lane",
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
        "PANTHEON_RUNTIME_SERVICE_LABEL", "com.pantheon.agy-gemini-new"
    )
    manifest_path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")

    result = process_once(
        lane_root,
        lane="new",
        generate_json=lambda *_args: pytest.fail("provider must not run"),
    )

    assert result["status"] == "failed"
    assert result["error_type"] == "RuntimeManifestError"
    assert not (lane_root / "processing").exists()


def _set_formal_runner_env(
    monkeypatch: pytest.MonkeyPatch,
    manifest_path: Path,
    manifest: dict[str, object],
    service_label: str,
    activation_token: Path | None = None,
) -> None:
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST", str(manifest_path))
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST_DIGEST", str(manifest["manifest_digest"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_IDENTITY", str(manifest["identity"]))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_IDENTITY_DIGEST",
        str(manifest["runtime_identity_digest"]),
    )
    monkeypatch.setenv("PANTHEON_RUNTIME_CODE_DIGEST", str(manifest["runtime_digest"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_CONFIG_VERSION", str(manifest["config_version"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", str(manifest["generation"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_ACTOR_ROOT", str(manifest["actor_root"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(manifest["queue_root"]))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT",
        str(manifest["publisher_state_root"]),
    )
    monkeypatch.setenv("PANTHEON_RUNTIME_LOG_ROOT", str(manifest["log_root"]))
    monkeypatch.setenv("PANTHEON_RUNTIME_SERVICE_LABEL", service_label)
    if activation_token is not None:
        monkeypatch.setenv("PANTHEON_RUNTIME_ACTIVATION_TOKEN", str(activation_token))


def _activate_formal_runtime(
    ready_root: Path,
    barrier: Path,
    manifest: dict[str, object],
) -> None:
    ready_root.mkdir(parents=True)
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready_root, manifest, label)
    runtime_manifest.activate_barrier(barrier, ready_root, manifest)


def test_formal_production_lane_missing_transport_env_blocks_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    lane_root = queue / "lanes" / "i18n-new"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, lane_root, state, logs):
        path.mkdir(parents=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-lane-missing-transport",
        runtime_digest="3" * 64,
        generation="generation-lane-transport",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    barrier = tmp_path / "activation.barrier"
    _activate_formal_runtime(tmp_path / "ready", barrier, manifest)
    _set_formal_runner_env(
        monkeypatch,
        manifest_path,
        manifest,
        "com.pantheon.agy-gemini-i18n-new",
        activation_token=barrier,
    )
    request = create_external_request(
        lane_root,
        namespace=hashlib.sha256(b"target-run").hexdigest()[:24],
        role="writer",
        model="gemini-test-writer",
        prompt="目標 run",
        response_schema=SCHEMA,
    )
    before = {
        str(path.relative_to(lane_root)): path.read_bytes()
        for path in sorted(lane_root.rglob("*"))
        if path.is_file()
    }

    result = process_once(
        lane_root,
        lane="i18n-new",
        exact_run_ids=["target-run"],
        generate_json=lambda *_args: pytest.fail("provider must not run"),
    )

    assert result == {
        "status": "blocked",
        "reason": "formal_production_transport_env_missing",
        "service_label": "com.pantheon.agy-gemini-i18n-new",
        "missing_env": [
            "AGY_GEMINI_CREDENTIAL_POOL_FILE",
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
            "AGY_GEMINI_MODEL_ROUTE_CONFIG",
            "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST",
            "AGY_REVIEWER_MODEL",
            "AGY_WRITER_MODEL",
        ],
    }
    after = {
        str(path.relative_to(lane_root)): path.read_bytes()
        for path in sorted(lane_root.rglob("*"))
        if path.is_file()
    }
    assert after == before
    assert (lane_root / "outbox" / f"{request['job_id']}.json").is_file()
    assert not (lane_root / "processing").exists()
    assert not (lane_root / "archive").exists()
    assert not (lane_root / "failed").exists()
    assert not (lane_root / "production-attempts").exists()


def test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import agy_gemini_runner as runner

    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    barrier = state / "four-lane-activation-current.barrier"
    pool = tmp_path / "pool.json"
    route = tmp_path / "route.json"
    for path in (actor, queue, state, logs, ready):
        path.mkdir(parents=True)
    pool.write_text("{}", encoding="utf-8")
    route.write_text("{}", encoding="utf-8")
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-current",
        runtime_digest="4" * 64,
        generation="generation-current",
        python_executable=Path(sys.executable).resolve(),
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    plist_path = tmp_path / "com.pantheon.agy-gemini-i18n-new.plist"
    plist_path.write_bytes(
        plistlib.dumps(
            {
                "Label": "com.pantheon.agy-gemini-i18n-new",
                "EnvironmentVariables": {
                    "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
                    "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(queue / "pool-state.json"),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG": str(route),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST": "5" * 64,
                    "AGY_WRITER_MODEL": "writer-model",
                    "AGY_REVIEWER_MODEL": "reviewer-model",
                    "PANTHEON_RUNTIME_GENERATION": "stale-generation",
                },
                "ProgramArguments": ["stale-python", "-m", "stale.module"],
            }
        )
    )
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        return subprocess.CompletedProcess(command, 0, '{"status":"idle"}\n', "")

    result = runner.operator_exact_process_once(
        manifest_path=manifest_path,
        expected_digest=str(manifest["manifest_digest"]),
        barrier=barrier,
        service_label="com.pantheon.agy-gemini-i18n-new",
        ready_root=ready,
        plist=plist_path,
        exact_run_id="target-run",
        timeout=30,
        runner=fake_run,
    )

    command = captured["command"]
    env = captured["env"]
    assert result["status"] == "executed"
    assert result["returncode"] == 0
    assert command[:4] == [
        str(Path(sys.executable).resolve()),
        "-m",
        "scripts.pantheon_content_runtime_manifest",
        "barrier-exec",
    ]
    assert "--expected-digest" in command
    assert command[command.index("--expected-digest") + 1] == manifest["manifest_digest"]
    assert "stale-python" not in command
    assert env["AGY_GEMINI_CREDENTIAL_POOL_FILE"] == str(pool)
    assert env["PANTHEON_RUNTIME_GENERATION"] == manifest["generation"]
    assert env["PANTHEON_RUNTIME_QUEUE_ROOT"] == str(queue)
    assert env["PANTHEON_RUNTIME_SERVICE_LABEL"] == "com.pantheon.agy-gemini-i18n-new"
    assert result["env_receipt"]["AGY_GEMINI_CREDENTIAL_POOL_FILE"]["present"] is True
    assert "value" not in result["env_receipt"]["AGY_GEMINI_CREDENTIAL_POOL_FILE"]


def test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts import agy_gemini_runner as runner

    def fake_operator_exact_process_once(**_kwargs: object) -> dict[str, object]:
        return {
            "status": "executed",
            "returncode": 42,
            "stdout_receipt": {"bytes": 61, "sha256": "6" * 64, "empty": False},
            "stderr_receipt": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(), "empty": True},
            "env_receipt": {},
            "child_result_summary": {"status": "failed", "error_type": "ValueError"},
        }

    monkeypatch.setattr(
        runner,
        "operator_exact_process_once",
        fake_operator_exact_process_once,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agy_gemini_runner.py",
            "--queue-root",
            str(tmp_path / "unused-queue"),
            "--exact-run-id",
            "target-run",
            "operator-exact-process-once",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--expected-digest",
            "7" * 64,
            "--barrier",
            str(tmp_path / "barrier"),
            "--service-label",
            "com.pantheon.agy-gemini-i18n-new",
            "--ready-root",
            str(tmp_path / "ready"),
            "--plist",
            str(tmp_path / "service.plist"),
        ],
    )

    exit_code = runner.main()

    printed = capsys.readouterr().out
    payload = json.loads(printed)
    assert exit_code == 42
    assert payload["status"] == "executed"
    assert payload["returncode"] == 42
    assert payload["child_result_summary"] == {
        "status": "failed",
        "error_type": "ValueError",
    }
    assert "stdout" not in payload
    assert "stderr" not in payload
    assert "raw-secret" not in printed


def test_operator_exact_process_summarizes_last_json_line_without_raw_output(
    tmp_path: Path,
) -> None:
    from scripts import agy_gemini_runner as runner

    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    ready = tmp_path / "ready"
    barrier = state / "four-lane-activation-current.barrier"
    pool = tmp_path / "pool.json"
    route = tmp_path / "route.json"
    for path in (actor, queue, state, logs, ready):
        path.mkdir(parents=True)
    pool.write_text("{}", encoding="utf-8")
    route.write_text("{}", encoding="utf-8")
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-current-multiline",
        runtime_digest="8" * 64,
        generation="generation-current-multiline",
        python_executable=Path(sys.executable).resolve(),
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    plist_path = tmp_path / "com.pantheon.agy-gemini-i18n-new.plist"
    plist_path.write_bytes(
        plistlib.dumps(
            {
                "Label": "com.pantheon.agy-gemini-i18n-new",
                "EnvironmentVariables": {
                    "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
                    "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(queue / "pool-state.json"),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG": str(route),
                    "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST": "9" * 64,
                    "AGY_WRITER_MODEL": "writer-model",
                    "AGY_REVIEWER_MODEL": "reviewer-model",
                },
                "ProgramArguments": ["stale-python", "-m", "stale.module"],
            }
        )
    )

    def fake_run(
        command: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            42,
            'banner raw-secret\n{"status":"failed","error_type":"ValueError","secret":"raw-secret"}\n',
            "stderr raw-secret",
        )

    result = runner.operator_exact_process_once(
        manifest_path=manifest_path,
        expected_digest=str(manifest["manifest_digest"]),
        barrier=barrier,
        service_label="com.pantheon.agy-gemini-i18n-new",
        ready_root=ready,
        plist=plist_path,
        exact_run_id="target-run",
        timeout=30,
        runner=fake_run,
    )
    encoded = json.dumps(result, ensure_ascii=False)

    assert result["status"] == "executed"
    assert result["returncode"] == 42
    assert result["child_result_summary_parse"] == "parsed_last_json_line"
    assert result["child_result_summary"] == {
        "status": "failed",
        "error_type": "ValueError",
    }
    assert "stdout" not in result
    assert "stderr" not in result
    assert "raw-secret" not in encoded

from __future__ import annotations

import hashlib
import io
import json
import os
import plistlib
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest
import scripts.agy_gemini_allocator as allocator
import scripts.agy_gemini_outbox as outbox
import scripts.agy_gemini_runner as runner
import scripts.agy_seo_copy_pipeline as pipeline
from scripts import agy_gemini_v4_broker as broker
from scripts.agy_gemini_v4_broker import BrokerResult, ExecutionReceipt

from scripts.agy_gemini_outbox import (
    ExternalJobFailed,
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
NORMALIZED_TRACE_KEYS = frozenset(
    {
        "replay_status",
        "process_count",
        "outcome",
        "exit_status",
        "stdout_sha256",
        "stderr_sha256",
        "byte_count",
        "receipt",
        "caller_contract_satisfied",
        "result_validation",
        "result",
        "errors",
        "automatic_resend_allowed",
    }
)


def _assert_normalized_trace_schema(trace: dict[str, object]) -> None:
    assert frozenset(trace) == NORMALIZED_TRACE_KEYS, "normalized trace schema changed"


def _failure_receipt(
    request: dict[str, object],
    *,
    error_type: object,
    error_code: object = None,
    credential_slot_id: str | None = None,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "error_type": error_type,
        "completed_at": "2026-07-26T00:30:00+08:00",
    }
    if error_code is not None:
        receipt["error_code"] = error_code
    if credential_slot_id is not None:
        receipt["credential_pool"] = {
            "pool_id": "pantheon-production-v1",
            "slot_id": credential_slot_id,
            "manifest_sha256": "a" * 64,
        }
    return receipt


def _deep_failure_json(marker: str, depth: int = 20_000) -> str:
    payload = "[" * depth + json.dumps(marker) + "]" * depth
    assert len(payload.encode("utf-8")) < outbox.MAX_FAILURE_RECEIPT_BYTES
    return payload


def _write_production_pool(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    credentials: dict[str, str] = {}
    slots: list[dict[str, str]] = []
    for index in range(3):
        slot_id = f"account-{index + 1}"
        credential = f"test-production-credential-slot-{index + 1}-value"
        credential_path = tmp_path / f"credential-{index + 1}"
        credential_path.write_text(credential + "\n", encoding="utf-8")
        credential_path.chmod(0o600)
        credentials[slot_id] = credential
        slots.append({"slot_id": slot_id, "credential_file": str(credential_path)})
    manifest = tmp_path / "production-pool.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": "pantheon-production-v1",
                "slots": list(reversed(slots)),
            }
        ),
        encoding="utf-8",
    )
    manifest.chmod(0o600)
    return manifest, credentials


def _write_allocator_state(
    path: Path,
    *,
    pool_id: str = "pantheon-production-v1",
    manifest_sha256: str,
    last_ordinal: int,
) -> None:
    lock_path = path.with_name(f"{path.name}.lock")
    if not lock_path.exists():
        lock_path.touch(mode=0o600)
    lock_stat = lock_path.stat()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": pool_id,
                "manifest_sha256": manifest_sha256,
                "last_ordinal": last_ordinal,
                "lock_device": lock_stat.st_dev,
                "lock_inode": lock_stat.st_ino,
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)


def _broker_result(
    status: str,
    receipt: ExecutionReceipt,
    *,
    result: dict[str, object] | None = None,
) -> BrokerResult:
    success = status == "COMPLETE" and result is not None
    count: int | str = 1 if status in {"COMPLETE", "BLOCKED"} else "UNKNOWN"
    return BrokerResult(
        replay_status=status,
        process_count=count,
        outcome="SUCCESS" if success else None,
        exit_status=0 if success else None,
        stdout_sha256="a" * 64 if success else None,
        stderr_sha256="b" * 64 if success else None,
        byte_count=1 if success else 0,
        final_anchor="c" * 64 if success else None,
        receipt=receipt,
        caller_contract_satisfied=success,
        result_json=json.dumps(result, sort_keys=True, separators=(",", ":")).encode() if result is not None else None,
        errors=() if success else ("SYNTHETIC_FAILURE",),
    )


def _new_output_contract_fixture() -> dict[str, object]:
    def sized_text(seed: str, size: int) -> str:
        return (seed + "逐項核對情境、資料與可調整限制。" * size)[:size]

    bounded_paragraph = sized_text(
        "測試關鍵字先整理可觀察情境，再核對手邊資料與限制。",
        159,
    ) + "。"
    assert len(bounded_paragraph) == 160
    return {
        "articles": [
            {
                "slot": "article-01",
                "primaryKeyword": "測試關鍵字",
                "secondaryKeywords": ["觀察情境", "資料限制"],
                "title": sized_text("測試關鍵字如何整理日常觀察", 28),
                "description": sized_text("測試關鍵字可協助整理現況與下一步", 69),
                "answer": "先核對具體情境與可用資料，再決定下一步。",
                "tags": [f"測試標籤{index}" for index in range(1, 10)],
                "faq": [
                    {
                        "question": f"測試問題 {index}？",
                        "answer": "先核對實際情境與資料限制。",
                    }
                    for index in range(1, 4)
                ],
                "bodySections": [
                    {
                        "heading": f"測試關鍵字的觀察面向 {section}",
                        "paragraphs": [
                            (
                                bounded_paragraph + "RAW_PROVIDER_TAIL"
                                if section == 1 and paragraph == 1
                                else sized_text(
                                    f"第 {section} 節第 {paragraph} 段先整理具體線索。",
                                    100,
                                )
                            )
                            for paragraph in range(1, 3)
                        ],
                    }
                    for section in range(1, 6)
                ],
            }
        ]
    }


def _rewrite_length_cases() -> list[dict[str, object]]:
    path = (
        Path(__file__).parent
        / "fixtures"
        / "agy_rewrite_schema_conformance"
        / "length_cases.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["cases"]


def _rewrite_length_mismatch_fixture(
    case: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    current_body = [
        {
            "heading": "舊正文",
            "paragraphs": ["舊正文只作為 synthetic hash 輸入。"],
        }
    ]
    identity = {
        "id": "REWRITE-SCHEMA-001",
        "product": "personality",
        "category": "personality",
        "serial": "personality-0001",
        "slug": "rewrite-schema-001",
        "primaryKeyword": "測試關鍵字",
        "title": "測試關鍵字的既有標題",
    }
    immutable_fields = {
        "id": identity["id"],
        "product": identity["product"],
        "slug": identity["slug"],
        "serial": identity["serial"],
        "title": identity["title"],
        "description": "既有描述",
        "answer": "既有答案",
        "faq": [{"question": "既有問題", "answer": "既有回答"}],
        "tags": ["既有標籤"],
        "published": "2026-07-01",
        "updated": "2026-07-02",
        "urlSlug": identity["slug"],
        "primaryKeyword": identity["primaryKeyword"],
    }
    policy = pipeline.load_article_publication_policy()
    publication_policy = {
        "policyVersion": policy["policy_version"],
        "canonical": (
            f"{policy['site_origin']}/articles/{identity['category']}/"
            f"{identity['slug']}"
        ),
        "author": {
            "name": policy["identity"]["author_name"],
            "url": policy["identity"]["author_url"],
            "id": policy["identity"]["author_id"],
        },
        "editorialResponsibility": policy["identity"][
            "editorial_responsibility"
        ],
        "evidence": {
            "mode": "cultural_reflection",
            "sources": [],
            "disclosure": "本文屬文化脈絡與反思整理，不主張可驗證的預測結果。",
        },
        "published": "2026-07-01",
        "modified": "2026-08-01",
        "changeType": "substantive_rewrite",
    }

    def paragraph(section: int, item: int, length: int) -> str:
        seed = (
            f"測試關鍵字先核對第{section}節第{item}段的具體情境，"
            "記錄資料、比較選項並詢問限制；這不代表能替個人下結論。"
        )
        return (seed + "再核對一項可觀察細節。" * length)[:length]

    canonical_paragraph_schema = pipeline.candidate_schema(
        "rewrite_existing_body"
    )["properties"]["articles"]["items"]["properties"]["bodySections"][
        "items"
    ]["properties"]["paragraphs"]["items"]
    target_length = (
        int(canonical_paragraph_schema[str(case["keyword"])])
        + int(case["delta"])
    )
    body_sections = [
        {
            "heading": f"第 {section} 個觀察面向",
            "paragraphs": [
                paragraph(
                    section,
                    item,
                    (
                        target_length
                        if section - 1 == int(case["section_index"])
                        and item - 1 == int(case["paragraph_index"])
                        else 100
                    ),
                )
                for item in range(1, 4)
            ],
        }
        for section in range(1, 6)
    ]
    brief = {
        "schema_version": 1,
        "run_id": "rewrite-schema-conformance-red",
        "mode": "rewrite_existing_body",
        "source_commit": "0" * 40,
        "sort_contract": "fixed",
        "articles": [
            {
                "slot": "article-01",
                "article_id": identity["id"],
                "identity": identity,
                "immutable_fields": immutable_fields,
                "current_body": current_body,
                "current_body_sha256": pipeline.body_sha256(current_body),
                "rewrite_brief": ["先回答搜尋問題", "加入生活場景"],
                "source_file": "synthetic/article-registry.js",
                "body_source": "synthetic/article-body.js",
            }
        ],
    }
    external = {
        "articles": [
            {
                "slot": "article-01",
                "bodySections": body_sections,
                "publicationPolicy": publication_policy,
            }
        ]
    }
    return brief, external


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


def test_production_pool_strict_round_robin_is_exact_for_six_allocations(
    tmp_path: Path,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    sources = [
        runner._allocate_production_credential_source(manifest, state)
        for _index in range(6)
    ]
    try:
        assert [source.slot_id for source in sources] == [
            "account-1",
            "account-2",
            "account-3",
            "account-1",
            "account-2",
            "account-3",
        ]
        assert [source.ordinal for source in sources] == [1, 2, 3, 4, 5, 6]
    finally:
        for source in sources:
            os.close(source.descriptor)
    assert json.loads(state.read_text(encoding="utf-8"))["last_ordinal"] == 6
    assert stat.S_IMODE(state.stat().st_mode) == 0o600


def test_production_pool_four_process_stress_has_no_ordinal_gap_or_duplicate(
    tmp_path: Path,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    worker = (
        "import json,os,sys;"
        "from pathlib import Path;"
        "from scripts.agy_gemini_runner import _allocate_production_credential_source as a;"
        "rows=[];"
        "\nfor _ in range(int(sys.argv[3])):"
        "\n s=a(Path(sys.argv[1]),Path(sys.argv[2]));"
        "\n rows.append([s.ordinal,s.slot_id]);os.close(s.descriptor)"
        "\nprint(json.dumps(rows))"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", worker, str(manifest), str(state), "75"],
            cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _index in range(4)
    ]
    rows: list[list[object]] = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=60)
        assert process.returncode == 0, stderr
        rows.extend(json.loads(stdout))

    ordinals = sorted(int(row[0]) for row in rows)
    slots = [str(row[1]) for row in rows]
    assert ordinals == list(range(1, 301))
    assert {slot: slots.count(slot) for slot in set(slots)} == {
        "account-1": 100,
        "account-2": 100,
        "account-3": 100,
    }


def test_allocator_lock_path_replacement_cannot_create_parallel_critical_section(
    tmp_path: Path,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    committed = tmp_path / "committed"
    release = tmp_path / "release"
    repo_root = Path(__file__).resolve().parents[1]
    worker_a = (
        "import pathlib,sys,time;"
        "from scripts import agy_gemini_allocator as a;"
        "state=pathlib.Path(sys.argv[1]);"
        "committed=pathlib.Path(sys.argv[4]);release=pathlib.Path(sys.argv[5]);"
        "original=a._commit_state;"
        "\ndef wrapped(*args,**kwargs):"
        "\n original(*args,**kwargs);committed.touch()"
        "\n while not release.exists(): time.sleep(0.01)"
        "\na._commit_state=wrapped"
        "\ntry:"
        "\n print(a.allocate_production_slot(state,pool_id=sys.argv[2],manifest_sha256=sys.argv[3]))"
        "\nexcept Exception as error:"
        "\n print(type(error).__name__,str(error));raise SystemExit(17)"
    )
    worker_b = (
        "import pathlib,sys;"
        "from scripts.agy_gemini_allocator import allocate_production_slot;"
        "\ntry:"
        "\n print(allocate_production_slot(pathlib.Path(sys.argv[1]),pool_id=sys.argv[2],manifest_sha256=sys.argv[3]))"
        "\nexcept Exception as error:"
        "\n print(type(error).__name__,str(error));raise SystemExit(19)"
    )
    first = subprocess.Popen(
        [
            sys.executable,
            "-c",
            worker_a,
            str(state),
            str(payload["pool_id"]),
            manifest_sha256,
            str(committed),
            str(release),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while not committed.exists() and first.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert committed.exists(), first.communicate(timeout=1)

    lock_path = state.with_name(f"{state.name}.lock")
    lock_path.unlink()
    lock_path.touch(mode=0o600)
    second = subprocess.Popen(
        [
            sys.executable,
            "-c",
            worker_b,
            str(state),
            str(payload["pool_id"]),
            manifest_sha256,
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(0.1)
    assert second.poll() is None
    release.touch()
    first_stdout, first_stderr = first.communicate(timeout=5)
    second_stdout, second_stderr = second.communicate(timeout=5)

    assert second.returncode == 19, second_stdout + second_stderr
    assert "lock file changed" in second_stdout
    assert first.returncode == 17, first_stdout + first_stderr
    assert "lock file changed" in first_stdout


def test_allocator_rebinds_same_lock_inode_after_device_id_changes(
    tmp_path: Path,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    assert allocator.allocate_production_slot(
        state,
        pool_id=str(payload["pool_id"]),
        manifest_sha256=manifest_sha256,
    ) == (1, "account-1")

    state_payload = json.loads(state.read_text(encoding="utf-8"))
    current_device = int(state_payload["lock_device"])
    state_payload["lock_device"] = current_device + 1
    state.write_text(
        json.dumps(state_payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    state.chmod(0o600)

    allocator.validate_production_allocator_installation(
        state,
        pool_id=str(payload["pool_id"]),
        manifest_sha256=manifest_sha256,
    )
    assert allocator.allocate_production_slot(
        state,
        pool_id=str(payload["pool_id"]),
        manifest_sha256=manifest_sha256,
    ) == (2, "account-2")
    rebound = json.loads(state.read_text(encoding="utf-8"))
    assert rebound["lock_device"] == current_device


def test_production_pool_commit_survives_worker_crash_before_provider(
    tmp_path: Path,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    worker = (
        "import os,sys;"
        "from pathlib import Path;"
        "from scripts.agy_gemini_runner import _allocate_production_credential_source as a;"
        "s=a(Path(sys.argv[1]),Path(sys.argv[2]));os.close(s.descriptor);os._exit(23)"
    )
    crashed = subprocess.run(
        [sys.executable, "-c", worker, str(manifest), str(state)],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )
    assert crashed.returncode == 23

    source = runner._allocate_production_credential_source(manifest, state)
    try:
        assert (source.ordinal, source.slot_id) == (2, "account-2")
    finally:
        os.close(source.descriptor)


def test_production_pool_rejects_relative_manifest_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[Path] = []

    def reject_open(
        path: Path,
        *,
        minimum_size: int,
        maximum_size: int,
    ) -> int:
        del minimum_size, maximum_size
        opened.append(path)
        raise AssertionError("relative manifest must be rejected before file open")

    monkeypatch.setattr(runner, "_open_private_file", reject_open)

    with pytest.raises(ValueError, match="absolute"):
        runner._allocate_production_credential_source(
            Path("relative-production-pool.json"),
            tmp_path / "round-robin-state.json",
        )

    create_external_request(
        tmp_path,
        namespace="production-pool-relative-manifest",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    monkeypatch.setenv(
        "AGY_GEMINI_CREDENTIAL_POOL_FILE",
        "relative-production-pool.json",
    )
    monkeypatch.setenv(
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
        str(tmp_path / "round-robin-state.json"),
    )
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    result = process_once(tmp_path)

    assert result["status"] == "failed"
    assert result["error_type"] == "ValueError"
    assert opened == []


def test_production_pool_rejects_boolean_schema_version(tmp_path: Path) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["schema_version"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    manifest.chmod(0o600)

    with pytest.raises(ValueError, match="production credential pool schema"):
        source = runner._allocate_production_credential_source(
            manifest,
            tmp_path / "round-robin-state.json",
        )
        os.close(source.descriptor)


def test_production_pool_digest_is_stable_for_permuted_slots(tmp_path: Path) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    permuted_manifest = tmp_path / "production-pool-permuted.json"
    permuted_payload = {**payload, "slots": list(reversed(payload["slots"]))}
    permuted_manifest.write_text(json.dumps(permuted_payload), encoding="utf-8")
    permuted_manifest.chmod(0o600)

    original = runner._allocate_production_credential_source(
        manifest,
        tmp_path / "original-state.json",
    )
    for slot in payload["slots"]:
        Path(slot["credential_file"]).write_text(
            "replacement-production-credential-value\n",
            encoding="utf-8",
        )
    permuted = runner._allocate_production_credential_source(
        permuted_manifest,
        tmp_path / "permuted-state.json",
    )
    try:
        assert original.manifest_sha256 == permuted.manifest_sha256
        assert original.slot_id == permuted.slot_id == "account-1"
    finally:
        os.close(original.descriptor)
        os.close(permuted.descriptor)


@pytest.mark.parametrize("unsafe_target", ["manifest-mode", "manifest-symlink", "credential-mode", "credential-symlink"])
def test_production_pool_rejects_unsafe_files(
    tmp_path: Path,
    unsafe_target: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    selected_path = Path(
        next(
            slot["credential_file"]
            for slot in payload["slots"]
            if slot["slot_id"] == "account-1"
        )
    )
    if unsafe_target == "manifest-mode":
        manifest.chmod(0o644)
    elif unsafe_target == "manifest-symlink":
        target = tmp_path / "pool-target.json"
        manifest.replace(target)
        manifest.symlink_to(target)
    elif unsafe_target == "credential-mode":
        selected_path.chmod(0o644)
    else:
        target = selected_path.with_suffix(".target")
        selected_path.replace(target)
        selected_path.symlink_to(target)

    with pytest.raises(ValueError, match="production credential"):
        source = runner._allocate_production_credential_source(
            manifest,
            tmp_path / "round-robin-state.json",
        )
        os.close(source.descriptor)


@pytest.mark.parametrize("malformation", ["slot-count", "duplicate-slot", "relative-path", "extra-field"])
def test_production_pool_rejects_incompatible_schema(
    tmp_path: Path,
    malformation: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if malformation == "slot-count":
        payload["slots"].pop()
    elif malformation == "duplicate-slot":
        payload["slots"][1]["slot_id"] = payload["slots"][0]["slot_id"]
    elif malformation == "relative-path":
        payload["slots"][0]["credential_file"] = "relative-key-file"
    else:
        payload["unexpected"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    manifest.chmod(0o600)

    with pytest.raises(ValueError, match="production credential pool"):
        source = runner._allocate_production_credential_source(
            manifest,
            tmp_path / "round-robin-state.json",
        )
        os.close(source.descriptor)


@pytest.mark.parametrize(
    "malformation",
    [
        "corrupt",
        "truncated",
        "symlink",
        "wrong-mode",
        "non-regular",
        "pool-mismatch",
        "manifest-mismatch",
        "extra-field",
        "cooldown-extra-field",
        "cooldown-raw-reason",
        "cooldown-unbounded",
        "cooldown-duplicate",
    ],
)
def test_production_pool_state_fails_closed_before_credential_or_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    malformation: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    _payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    _write_allocator_state(
        state,
        manifest_sha256=manifest_sha256,
        last_ordinal=1,
    )
    if malformation.startswith("cooldown-"):
        allocator.record_production_rate_limit(
            state,
            pool_id="pantheon-production-v1",
            manifest_sha256=manifest_sha256,
            slot_id="account-1",
            cooldown_seconds=60,
            clock=lambda: 4_000.0,
        )
    if malformation == "corrupt":
        state.write_text("{not-json}\n", encoding="utf-8")
    elif malformation == "truncated":
        state.write_text('{"schema_version":1', encoding="utf-8")
    elif malformation == "symlink":
        target = tmp_path / "state-target.json"
        state.replace(target)
        state.symlink_to(target)
    elif malformation == "wrong-mode":
        state.chmod(0o644)
    elif malformation == "non-regular":
        state.unlink()
        state.mkdir()
    elif malformation == "pool-mismatch":
        _write_allocator_state(
            state,
            pool_id="other-production-pool",
            manifest_sha256=manifest_sha256,
            last_ordinal=1,
        )
    elif malformation == "manifest-mismatch":
        _write_allocator_state(
            state,
            manifest_sha256="0" * 64,
            last_ordinal=1,
        )
    elif malformation == "cooldown-extra-field":
        payload = json.loads(state.read_text(encoding="utf-8"))
        payload["cooldowns"][0]["raw"] = "must-not-be-accepted"
        state.write_text(json.dumps(payload), encoding="utf-8")
    elif malformation == "cooldown-raw-reason":
        payload = json.loads(state.read_text(encoding="utf-8"))
        payload["cooldowns"][0]["reason"] = "private provider detail"
        state.write_text(json.dumps(payload), encoding="utf-8")
    elif malformation == "cooldown-unbounded":
        payload = json.loads(state.read_text(encoding="utf-8"))
        payload["cooldowns"][0]["cooldown_until_ms"] += (
            allocator.MAX_RATE_LIMIT_COOLDOWN_SECONDS * 1000
        )
        state.write_text(json.dumps(payload), encoding="utf-8")
    elif malformation == "cooldown-duplicate":
        payload = json.loads(state.read_text(encoding="utf-8"))
        payload["cooldowns"].append(dict(payload["cooldowns"][0]))
        state.write_text(json.dumps(payload), encoding="utf-8")
    else:
        payload = json.loads(state.read_text(encoding="utf-8"))
        payload["unexpected"] = True
        state.write_text(json.dumps(payload), encoding="utf-8")
        state.chmod(0o600)

    credential_read = False
    provider_called = False

    def reject_credential(_descriptor: int) -> str:
        nonlocal credential_read
        credential_read = True
        raise AssertionError("credential value must not be read")

    def reject_provider(*_args: object, **_kwargs: object) -> object:
        nonlocal provider_called
        provider_called = True
        raise AssertionError("provider must not be called")

    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace=f"state-safety-{malformation}",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner, "_read_production_api_key", reject_credential)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", reject_provider)

    result = process_once(queue_root)

    assert result["status"] == "failed"
    assert result["error_type"] == "ValueError"
    assert "credential_pool" not in result
    assert credential_read is False
    assert provider_called is False
    assert (queue_root / "outbox" / f"{request['job_id']}.json").exists()
    assert not list((queue_root / "processing").glob("*.json"))
    assert not (queue_root / "archive").exists()
    assert not (queue_root / "failed").exists()


def test_production_malformed_request_terminalizes_without_credential_or_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    queue_root = tmp_path / "queue"
    malformed = queue_root / "outbox" / f"{'b' * 40}.json"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("{not-json}\n", encoding="utf-8")
    credential_reads = 0
    provider_calls = 0

    def reject_credential(_descriptor: int) -> str:
        nonlocal credential_reads
        credential_reads += 1
        raise AssertionError("credential must not be read")

    def reject_provider(*_args: object, **_kwargs: object) -> object:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("provider must not be called")

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner, "_read_production_api_key", reject_credential)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", reject_provider)

    result = process_once(queue_root)

    assert result["status"] == "failed"
    assert result["error_type"] == "JSONDecodeError"
    assert credential_reads == 0
    assert provider_calls == 0
    assert not state.exists()
    assert not malformed.exists()
    assert (queue_root / "archive" / malformed.name).exists()
    assert (queue_root / "failed" / malformed.name).exists()


def test_production_pool_rejects_relative_state_before_credential_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    credential_opened = False
    real_open = allocator.os.open
    credential_paths = {
        Path(slot["credential_file"])
        for slot in json.loads(manifest.read_text(encoding="utf-8"))["slots"]
    }

    def tracked_open(path: object, flags: int, mode: int = 0o777) -> int:
        nonlocal credential_opened
        if Path(path) in credential_paths:
            credential_opened = True
        return real_open(path, flags, mode)

    monkeypatch.setattr(runner.os, "open", tracked_open)
    with pytest.raises(ValueError, match="state path must be absolute"):
        runner._allocate_production_credential_source(
            manifest,
            Path("relative-state.json"),
        )
    assert credential_opened is False


def test_production_pool_state_detects_open_time_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    _payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    _write_allocator_state(
        state,
        manifest_sha256=manifest_sha256,
        last_ordinal=1,
    )
    replacement = tmp_path / "replacement-state.json"
    _write_allocator_state(
        replacement,
        manifest_sha256=manifest_sha256,
        last_ordinal=99,
    )
    real_open = runner.os.open
    replaced = False

    def racing_open(path: object, flags: int, mode: int = 0o777) -> int:
        nonlocal replaced
        if Path(path) == state and not replaced:
            replaced = True
            os.replace(replacement, state)
        return real_open(path, flags, mode)

    monkeypatch.setattr(allocator.os, "open", racing_open)
    with pytest.raises(ValueError, match="state file changed"):
        runner._allocate_production_credential_source(manifest, state)


def test_production_pool_state_rejects_wrong_owner_before_credential_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    _write_allocator_state(
        state,
        manifest_sha256=manifest_sha256,
        last_ordinal=1,
    )
    monkeypatch.setattr(
        runner,
        "_read_production_pool",
        lambda _path: (payload, manifest_sha256),
    )
    monkeypatch.setattr(
        allocator,
        "_open_allocator_lock",
        lambda path: os.open(path, os.O_RDWR),
    )
    monkeypatch.setattr(
        allocator,
        "_open_allocator_directory",
        lambda path: os.open(path, os.O_RDONLY),
    )
    real_uid = os.getuid()
    monkeypatch.setattr(allocator.os, "getuid", lambda: real_uid + 1)

    with pytest.raises(ValueError, match="state file must be owner-only"):
        runner._allocate_production_credential_source(manifest, state)


def test_production_pool_uses_only_selected_slot_and_one_provider_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, credentials = _write_production_pool(tmp_path)
    pool_payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    assert allocator.allocate_production_slot(
        state,
        pool_id=str(pool_payload["pool_id"]),
        manifest_sha256=manifest_sha256,
        clock=lambda: 7_000.0,
    ) == (1, "account-1")
    allocator.record_production_rate_limit(
        state,
        pool_id=str(pool_payload["pool_id"]),
        manifest_sha256=manifest_sha256,
        slot_id="account-1",
        cooldown_seconds=60,
        clock=lambda: 7_000.0,
    )
    request = create_external_request(
        tmp_path / "queue",
        namespace="production-pool-success",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    credential_paths = {
        Path(slot["credential_file"])
        for slot in json.loads(manifest.read_text(encoding="utf-8"))["slots"]
    }
    opened_credentials: list[Path] = []
    real_open = runner.os.open

    def tracked_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        **kwargs: object,
    ) -> int:
        candidate = Path(path)
        if candidate in credential_paths:
            opened_credentials.append(candidate)
        return real_open(path, flags, mode, **kwargs)

    provider_calls: list[object] = []

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "{\"ok\":true}"}]}}]}
            ).encode()

    def fake_urlopen(provider_request: object, **_kwargs: object) -> FakeResponse:
        provider_calls.append(provider_request)
        return FakeResponse()

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv(
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
        str(state),
    )
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    provider_constructions = 0
    real_gemini_client = runner.GeminiClient

    def assert_allocator_lock_is_free() -> None:
        lock_descriptor = os.open(
            state.with_name(f"{state.name}.lock"),
            os.O_RDWR,
        )
        try:
            allocator.fcntl.flock(
                lock_descriptor,
                allocator.fcntl.LOCK_EX | allocator.fcntl.LOCK_NB,
            )
            allocator.fcntl.flock(lock_descriptor, allocator.fcntl.LOCK_UN)
        finally:
            os.close(lock_descriptor)

    class LockCheckingGeminiClient(real_gemini_client):
        def __init__(self, *args: object, **kwargs: object) -> None:
            nonlocal provider_constructions
            assert_allocator_lock_is_free()
            provider_constructions += 1
            super().__init__(*args, **kwargs)

    original_fake_urlopen = fake_urlopen

    def lock_checking_urlopen(
        provider_request: object,
        **kwargs: object,
    ) -> FakeResponse:
        assert_allocator_lock_is_free()
        return original_fake_urlopen(provider_request, **kwargs)

    monkeypatch.setattr(runner.os, "open", tracked_open)
    monkeypatch.setattr(runner, "GeminiClient", LockCheckingGeminiClient)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", lock_checking_urlopen)

    result = process_once(tmp_path / "queue", clock=lambda: 7_001.0)
    response_path = tmp_path / "queue" / "inbox" / f"{request['job_id']}.json"
    response = json.loads(response_path.read_text(encoding="utf-8"))
    selected = response["credential_pool"]["slot_id"]

    assert result["status"] == "processed"
    assert result["credential_pool"] == response["credential_pool"]
    assert set(response["credential_pool"]) == {
        "pool_id",
        "slot_id",
        "manifest_sha256",
    }
    assert provider_constructions == 1
    assert len(provider_calls) == 1
    assert selected == "account-2"
    manifest_slots = json.loads(manifest.read_text(encoding="utf-8"))["slots"]
    expected_path = next(
        Path(slot["credential_file"])
        for slot in manifest_slots
        if slot["slot_id"] == selected
    )
    assert opened_credentials == [expected_path]
    assert consume_external_response(tmp_path / "queue", request) == {"ok": True}
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (response_path, tmp_path / "queue" / "archive" / f"{request['job_id']}.json")
    )
    assert all(secret not in persisted for secret in credentials.values())
    assert all(str(path) not in persisted for path in credential_paths)
    assert str(tmp_path / "round-robin-state.json") not in persisted
    assert "last_ordinal" not in persisted


def test_production_normalizes_new_output_with_one_credential_slot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    pool_payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    assert allocator.allocate_production_slot(
        state,
        pool_id=str(pool_payload["pool_id"]),
        manifest_sha256=manifest_sha256,
        clock=lambda: 8_000.0,
    ) == (1, "account-1")
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace="production-new-output-normalization",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 new lane prompt",
        response_schema=pipeline.external_candidate_schema("create"),
    )
    provider_constructions = 0
    provider_calls = 0

    class OneShotGeminiClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            nonlocal provider_constructions
            provider_constructions += 1

        def _single_request_http_transport(self, *_args: object) -> None:
            raise AssertionError("test double transport must not be called directly")

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal provider_calls
            provider_calls += 1
            return _new_output_contract_fixture()

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner, "GeminiClient", OneShotGeminiClient)

    result = process_once(queue_root, clock=lambda: 8_001.0, lane="new")

    response = json.loads(
        (queue_root / "inbox" / f"{request['job_id']}.json").read_text()
    )
    assert result["status"] == "processed"
    assert result["credential_pool"]["slot_id"] == "account-2"
    assert response["credential_pool"] == result["credential_pool"]
    assert provider_constructions == 1
    assert provider_calls == 1
    assert not list((queue_root / "failed").glob("*.json"))


def test_production_pool_commit_failure_precedes_credential_and_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, credentials = _write_production_pool(tmp_path)
    credential_paths = {
        Path(slot["credential_file"])
        for slot in json.loads(manifest.read_text(encoding="utf-8"))["slots"]
    }
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace="production-pool-commit-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    state = tmp_path / "round-robin-state.json"
    raw_error = (
        f"private-commit-error::{next(iter(credential_paths))}::"
        f"{credentials['account-1']}"
    )
    credential_opens = 0
    credential_reads = 0
    provider_constructions = 0
    provider_calls = 0
    real_open_private_file = runner._open_private_file
    real_read_production_api_key = runner._read_production_api_key

    def tracked_open_private_file(path: Path, **kwargs: object) -> int:
        nonlocal credential_opens
        if path in credential_paths:
            credential_opens += 1
        return real_open_private_file(path, **kwargs)

    def tracked_read_production_api_key(descriptor: int) -> str:
        nonlocal credential_reads
        credential_reads += 1
        return real_read_production_api_key(descriptor)

    def fail_commit(*_args: object, **_kwargs: object) -> None:
        raise OSError(raw_error)

    class ForbiddenProvider:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            nonlocal provider_constructions
            provider_constructions += 1

        def generate_json(self, *_args: object, **_kwargs: object) -> dict[str, bool]:
            nonlocal provider_calls
            provider_calls += 1
            return {"ok": True}

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner, "_open_private_file", tracked_open_private_file)
    monkeypatch.setattr(runner, "_read_production_api_key", tracked_read_production_api_key)
    monkeypatch.setattr(allocator, "_commit_state", fail_commit)
    monkeypatch.setattr(runner, "GeminiClient", ForbiddenProvider)

    result = process_once(queue_root)

    failed_paths = list((queue_root / "failed").glob("*.json"))
    archive_paths = list((queue_root / "archive").glob("*.json"))
    attempt_paths = list((queue_root / "production-attempts").glob("*.attempt"))
    failed = json.loads(failed_paths[0].read_text(encoding="utf-8"))
    attempt = json.loads(attempt_paths[0].read_text(encoding="utf-8"))
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (*failed_paths, *archive_paths, *attempt_paths)
    )

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "OSError",
    }
    assert credential_opens == 0
    assert credential_reads == 0
    assert provider_constructions == 0
    assert provider_calls == 0
    assert not state.exists()
    assert failed_paths == [queue_root / "failed" / f"{request['job_id']}.json"]
    assert archive_paths == [queue_root / "archive" / f"{request['job_id']}.json"]
    assert attempt_paths == [
        queue_root / "production-attempts" / f"{request['job_id']}.attempt"
    ]
    assert failed["error_type"] == "OSError"
    assert "credential_pool" not in failed
    assert attempt["attempt_status"] == "failed"
    assert not (queue_root / "inbox" / f"{request['job_id']}.json").exists()
    assert raw_error not in persisted
    assert all(secret not in persisted for secret in credentials.values())
    assert all(str(path) not in persisted for path in credential_paths)


@pytest.mark.parametrize(
    ("failure", "http_status", "expected_code", "expected_category"),
    [
        ("bad-request", 400, "API_HTTP_ERROR", "PROVIDER_UNAVAILABLE"),
        ("auth", 401, "API_AUTH", "AUTH"),
        ("forbidden", 403, "API_AUTH", "AUTH"),
        ("model-unavailable", 404, "API_MODEL_UNAVAILABLE", "MODEL_UNAVAILABLE"),
        ("rate-limit", 429, "API_RATE_LIMITED", "QUOTA"),
        ("provider-internal", 500, "API_HTTP_ERROR", "PROVIDER_UNAVAILABLE"),
        ("provider-unavailable", 503, "API_HTTP_ERROR", "PROVIDER_UNAVAILABLE"),
        ("redirect", 302, "API_HTTP_ERROR", "PROVIDER_UNAVAILABLE"),
        ("timeout", None, "API_TIMEOUT", "NETWORK"),
        ("transport", None, "API_TRANSPORT_ERROR", "NETWORK"),
    ],
)
def test_production_pool_failure_is_terminal_without_rotation_or_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    http_status: int | None,
    expected_code: str,
    expected_category: str,
) -> None:
    manifest, credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace="production-pool-rate-limit",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    calls = 0

    def fail_provider(provider_request: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise TimeoutError("private-timeout-detail")
        if failure == "transport":
            raise pipeline.urllib.error.URLError(OSError("private-transport-detail"))
        assert http_status is not None
        raise pipeline.urllib.error.HTTPError(
            getattr(provider_request, "full_url", "https://example.invalid"),
            http_status,
            "private-provider-detail",
            {},
            io.BytesIO(b"must-not-persist-provider-body"),
        )

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    state = tmp_path / "round-robin-state.json"
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", fail_provider)
    result = process_once(queue_root)
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text(encoding="utf-8"))

    assert calls == 1
    assert result["status"] == "failed"
    assert result["error_type"] == "GeminiApiFailure"
    assert result["error_code"] == expected_code
    assert failed["failure_category"] == expected_category
    if http_status is None:
        assert "http_status" not in result
        assert "http_status_class" not in result
        assert "http_status" not in failed
        assert "http_status_class" not in failed
    else:
        expected_status_class = f"{http_status // 100}xx"
        assert result["http_status"] == http_status
        assert result["http_status_class"] == expected_status_class
        assert failed["http_status"] == http_status
        assert failed["http_status_class"] == expected_status_class
    assert result["credential_pool"] == failed["credential_pool"]
    assert not (queue_root / "inbox" / f"{request['job_id']}.json").exists()
    assert (queue_root / "archive" / f"{request['job_id']}.json").exists()
    persisted = failed_path.read_text(encoding="utf-8")
    assert "provider-body" not in persisted
    assert "private-provider-detail" not in persisted
    assert "private-timeout-detail" not in persisted
    assert "private-transport-detail" not in persisted
    assert all(secret not in persisted for secret in credentials.values())
    allocator_payload = json.loads(state.read_text(encoding="utf-8"))
    assert allocator_payload["last_ordinal"] == 1
    if failure == "rate-limit":
        assert allocator_payload["cooldowns"] == [
            {
                "slot_id": "account-1",
                "cooldown_started_ms": result["cooldown"]["cooldown_started_ms"],
                "cooldown_until_ms": result["cooldown"]["cooldown_until_ms"],
                "reason": "API_RATE_LIMITED",
            }
        ]
    else:
        assert allocator_payload["cooldowns"] == []
    next_source = runner._allocate_production_credential_source(manifest, state)
    try:
        assert (next_source.ordinal, next_source.slot_id) == (2, "account-2")
    finally:
        os.close(next_source.descriptor)
    with pytest.raises(ExternalJobFailed) as raised:
        consume_external_response(queue_root, request)
    assert raised.value.error_code == expected_code
    assert raised.value.http_status == http_status
    assert raised.value.http_status_class == (
        f"{http_status // 100}xx" if http_status is not None else None
    )


def test_all_slots_cooling_denies_two_lanes_before_claim_or_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    for expected_slot in allocator.PRODUCTION_SLOT_IDS:
        ordinal, selected_slot = allocator.allocate_production_slot(
            state,
            pool_id=str(payload["pool_id"]),
            manifest_sha256=manifest_sha256,
            clock=lambda: 3_000.0,
        )
        assert ordinal >= 1
        assert selected_slot == expected_slot
        allocator.record_production_rate_limit(
            state,
            pool_id=str(payload["pool_id"]),
            manifest_sha256=manifest_sha256,
            slot_id=expected_slot,
            cooldown_seconds=60,
            clock=lambda: 3_000.0,
        )

    lane_roots = [tmp_path / "lanes" / "new", tmp_path / "lanes" / "rewrite"]
    requests = [
        create_external_request(
            lane_root,
            namespace=f"cooling-{lane_root.name}",
            role="writer",
            model="gemini-test-writer",
            prompt="公開 prompt",
            response_schema=SCHEMA,
        )
        for lane_root in lane_roots
    ]
    state_before = state.read_bytes()
    provider_calls = 0
    credential_reads = 0

    def reject_provider(*_args: object, **_kwargs: object) -> object:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("provider must not be called while all slots cool")

    def reject_credential(_descriptor: int) -> str:
        nonlocal credential_reads
        credential_reads += 1
        raise AssertionError("credential must not be read while all slots cool")

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", reject_provider)
    monkeypatch.setattr(runner, "_read_production_api_key", reject_credential)

    results = [
        process_once(lane_root, clock=lambda: 3_001.0)
        for lane_root in lane_roots
    ]

    assert all(result["status"] == "cooldown" for result in results)
    assert all(result["admission"]["reason"] == "API_RATE_LIMITED" for result in results)
    assert provider_calls == 0
    assert credential_reads == 0
    assert state.read_bytes() == state_before
    for lane_root, request in zip(lane_roots, requests, strict=True):
        assert (lane_root / "outbox" / f"{request['job_id']}.json").exists()
        assert not (lane_root / "processing").exists()
        assert not (lane_root / "archive").exists()
        assert not (lane_root / "inbox").exists()
        assert not (lane_root / "failed").exists()
        assert not (lane_root / "production-attempts").exists()


def test_all_slots_quota_blocked_preserves_primary_and_allows_fallback_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    state = tmp_path / "round-robin-state.json"
    primary = pipeline.DEFAULT_WRITER_MODEL
    fallback = pipeline.DEFAULT_WRITER_FALLBACK_MODEL
    quota_body = json.dumps(
        {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
                            }
                        ],
                    }
                ]
            }
        }
    ).encode()

    def quota_provider(provider_request: object, **_kwargs: object) -> object:
        raise pipeline.urllib.error.HTTPError(
            getattr(provider_request, "full_url", "https://example.invalid"),
            429,
            "private-provider-detail",
            {},
            io.BytesIO(quota_body),
        )

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", quota_provider)

    results = []
    for attempt, slot_id in enumerate(allocator.PRODUCTION_SLOT_IDS):
        create_external_request(
            queue_root,
            namespace="quota-model-routing",
            role="writer",
            model=primary,
            prompt="公開 prompt",
            response_schema=SCHEMA,
            transport_attempt=attempt,
        )
        results.append(process_once(queue_root, clock=lambda: 1_786_910_400.0))

    assert [result["error_code"] for result in results] == ["API_QUOTA"] * 3
    assert [result["credential_pool"]["slot_id"] for result in results] == list(
        allocator.PRODUCTION_SLOT_IDS
    )
    blocked = create_external_request(
        queue_root,
        namespace="quota-primary-blocked",
        role="writer",
        model=primary,
        prompt="公開 primary blocked",
        response_schema=SCHEMA,
    )
    blocked_result = process_once(queue_root, clock=lambda: 1_786_910_401.0)
    assert blocked_result["status"] == "quota_blocked"
    assert blocked_result["admission"]["reason"] == "API_QUOTA"
    assert (queue_root / "outbox" / f"{blocked['job_id']}.json").exists()
    assert not list((queue_root / "processing").glob("*.json"))

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "{\"ok\":true}"}]}}]}
            ).encode()

    monkeypatch.setattr(
        pipeline,
        "_single_request_urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    (queue_root / "outbox" / f"{blocked['job_id']}.json").unlink()
    fallback_request = create_external_request(
        queue_root,
        namespace="quota-fallback-allowed",
        role="writer",
        model=fallback,
        prompt="公開 fallback allowed",
        response_schema=SCHEMA,
    )
    fallback_result = process_once(queue_root, clock=lambda: 1_786_910_401.0)

    assert fallback_result["status"] == "processed"
    response = json.loads(
        (queue_root / "inbox" / f"{fallback_request['job_id']}.json").read_text()
    )
    assert response["model"] == fallback


def test_cooling_admission_64_process_competition_has_zero_side_effects(
    tmp_path: Path,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    for expected_slot in allocator.PRODUCTION_SLOT_IDS:
        _ordinal, selected_slot = allocator.allocate_production_slot(
            state,
            pool_id=str(payload["pool_id"]),
            manifest_sha256=manifest_sha256,
            clock=lambda: 5_000.0,
        )
        assert selected_slot == expected_slot
        allocator.record_production_rate_limit(
            state,
            pool_id=str(payload["pool_id"]),
            manifest_sha256=manifest_sha256,
            slot_id=expected_slot,
            cooldown_seconds=60,
            clock=lambda: 5_000.0,
        )
    lane_roots = [tmp_path / "lanes" / "new", tmp_path / "lanes" / "rewrite"]
    requests = [
        create_external_request(
            lane_root,
            namespace=f"competition-{lane_root.name}",
            role="writer",
            model="gemini-test-writer",
            prompt="公開 prompt",
            response_schema=SCHEMA,
        )
        for lane_root in lane_roots
    ]
    state_before = state.read_bytes()
    repo_root = Path(__file__).resolve().parents[1]
    worker = (
        "import json,pathlib,sys;"
        "from scripts import agy_gemini_runner as r;"
        "from scripts import agy_seo_copy_pipeline as p;"
        "\ndef blocked(*args,**kwargs): raise AssertionError('forbidden external call')"
        "\nr._read_production_api_key=blocked;p._single_request_urlopen=blocked"
        "\nroots=[pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2])]"
        "\nrows=[]"
        "\nfor index in range(8):"
        "\n rows.append(r.process_once(roots[index % 2],clock=lambda:5001.0)['status'])"
        "\nprint(json.dumps(rows))"
    )
    environment = os.environ.copy()
    environment["AGY_GEMINI_CREDENTIAL_POOL_FILE"] = str(manifest)
    environment["AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"] = str(state)
    environment.pop("AGY_GEMINI_V4_BROKER", None)
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                worker,
                str(lane_roots[index % 2]),
                str(lane_roots[(index + 1) % 2]),
            ],
            cwd=repo_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(8)
    ]
    rows: list[str] = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stdout + stderr
        rows.extend(json.loads(stdout))

    assert len(rows) == 64
    assert set(rows) == {"cooldown"}
    assert state.read_bytes() == state_before
    for lane_root, request in zip(lane_roots, requests, strict=True):
        assert (lane_root / "outbox" / f"{request['job_id']}.json").exists()
        assert not (lane_root / "processing").exists()
        assert not (lane_root / "archive").exists()
        assert not (lane_root / "inbox").exists()
        assert not (lane_root / "failed").exists()
        assert not (lane_root / "production-attempts").exists()


def test_production_pool_flag_off_preserves_injected_cli_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="production-pool-flag-off",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    calls: list[tuple[str, str, str, dict[str, object]]] = []

    def fake_generate(role: str, model: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
        calls.append((role, model, prompt, schema))
        return {"ok": True}

    monkeypatch.delenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", raising=False)
    monkeypatch.delenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", raising=False)
    result = process_once(tmp_path, generate_json=fake_generate)

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert len(calls) == 1


def test_production_pool_receipt_rejects_unclosed_identity(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="production-pool-closed-receipt",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    inbox = tmp_path / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir()
    inbox.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "job_id": request["job_id"],
                "request_sha256": request["request_sha256"],
                "model": request["model"],
                "completed_at": "2026-07-26T01:00:00+08:00",
                "result": {"ok": True},
                "credential_pool": {
                    "pool_id": "pantheon-production-v1",
                    "slot_id": "account-1",
                    "manifest_sha256": "a" * 64,
                    "credential_file": "must-not-pass",
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="external response fields are strict"):
        consume_external_response(tmp_path, request)


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


def test_lane_client_consumes_existing_response_from_legacy_shared_queue(tmp_path: Path) -> None:
    legacy_root = tmp_path / "shared"
    lane_root = legacy_root / "lanes" / "new"
    request = create_external_request(
        legacy_root,
        namespace="opaque-lane-fallback",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    response = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": request["model"],
        "completed_at": "2026-07-25T20:00:00+08:00",
        "result": {"ok": True},
    }
    inbox = legacy_root / "inbox" / f"{request['job_id']}.json"
    inbox.parent.mkdir()
    inbox.write_text(json.dumps(response), encoding="utf-8")
    client = OutboxGeminiClient(
        lane_root,
        legacy_queue_root=legacy_root,
        namespace="opaque-lane-fallback",
        writer_model="gemini-test-writer",
    )

    assert client.generate_json("writer", "公開 prompt", SCHEMA) == {"ok": True}
    assert not list((lane_root / "outbox").glob("*.json"))


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


def test_runner_claims_reviewer_before_fresh_writers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.delenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", raising=False)
    reviewer = create_external_request(
        tmp_path,
        namespace="opaque-review-ready",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="審查已完成的 writer candidate",
        response_schema=SCHEMA,
    )
    lower_writer = None
    for index in range(64):
        writer = create_external_request(
            tmp_path,
            namespace=f"opaque-fresh-writer-{index:02d}",
            role="writer",
            model="gemini-test-writer",
            prompt=f"fresh writer {index:02d}",
            response_schema=SCHEMA,
        )
        if writer["job_id"] < reviewer["job_id"]:
            lower_writer = writer
            break
    assert lower_writer is not None, "fixture must include a writer filename before reviewer"

    roles: list[str] = []
    result = process_once(
        tmp_path,
        generate_json=lambda role, _model, _prompt, _schema: roles.append(role) or {"ok": True},
    )

    assert result["job_id"] == reviewer["job_id"]
    assert roles == ["reviewer"]


def test_new_only_runner_gates_non_new_lane_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rewrite_root = tmp_path / "lanes" / "rewrite"
    new_root = tmp_path / "lanes" / "new"
    rewrite_request = create_external_request(
        rewrite_root,
        namespace="new-only-rewrite",
        role="writer",
        model="gemini-test-writer",
        prompt="rewrite must wait",
        response_schema=SCHEMA,
    )
    new_request = create_external_request(
        new_root,
        namespace="new-only-new",
        role="writer",
        model="gemini-test-writer",
        prompt="new may proceed",
        response_schema=SCHEMA,
    )
    calls: list[str] = []
    monkeypatch.setenv("AGY_GEMINI_NEW_ONLY", "1")
    monkeypatch.delenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", raising=False)
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)

    blocked = process_once(
        rewrite_root,
        lane="rewrite",
        generate_json=lambda role, *_args: calls.append(role) or {"ok": True},
    )
    processed = process_once(
        new_root,
        lane="new",
        generate_json=lambda role, *_args: calls.append(role) or {"ok": True},
    )

    assert blocked == {"status": "disabled", "reason": "new_only", "lane": "rewrite"}
    assert processed["status"] == "processed"
    assert processed["job_id"] == new_request["job_id"]
    assert calls == ["writer"]
    assert (rewrite_root / "outbox" / f"{rewrite_request['job_id']}.json").exists()
    assert not (rewrite_root / "processing").exists()
    assert not (rewrite_root / "archive").exists()

    monkeypatch.setenv("AGY_GEMINI_NEW_ONLY", "0")
    resumed = process_once(
        rewrite_root,
        lane="rewrite",
        generate_json=lambda role, *_args: calls.append(role) or {"ok": True},
    )
    assert resumed["status"] == "processed"
    assert resumed["job_id"] == rewrite_request["job_id"]


def test_cooldown_expiry_releases_one_new_and_keeps_rewrite_queued(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    payload, manifest_sha256 = runner._read_production_pool(manifest)
    state = tmp_path / "round-robin-state.json"
    for expected_slot in allocator.PRODUCTION_SLOT_IDS:
        _ordinal, selected_slot = allocator.allocate_production_slot(
            state,
            pool_id=str(payload["pool_id"]),
            manifest_sha256=manifest_sha256,
            clock=lambda: 6_000.0,
        )
        assert selected_slot == expected_slot
        allocator.record_production_rate_limit(
            state,
            pool_id=str(payload["pool_id"]),
            manifest_sha256=manifest_sha256,
            slot_id=expected_slot,
            cooldown_seconds=60,
            clock=lambda: 6_000.0,
        )
    new_root = tmp_path / "lanes" / "new"
    rewrite_root = tmp_path / "lanes" / "rewrite"
    new_request = create_external_request(
        new_root,
        namespace="expiry-new",
        role="writer",
        model="gemini-test-writer",
        prompt="new after expiry",
        response_schema=SCHEMA,
    )
    rewrite_request = create_external_request(
        rewrite_root,
        namespace="expiry-rewrite",
        role="writer",
        model="gemini-test-writer",
        prompt="rewrite remains paused",
        response_schema=SCHEMA,
    )
    provider_calls = 0

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}'

    def fake_provider(*_args: object, **_kwargs: object) -> FakeResponse:
        nonlocal provider_calls
        provider_calls += 1
        return FakeResponse()

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.setenv("AGY_GEMINI_NEW_ONLY", "1")
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", fake_provider)

    released = process_once(new_root, lane="new", clock=lambda: 6_060.0)
    blocked = process_once(rewrite_root, lane="rewrite", clock=lambda: 6_060.0)

    assert released["status"] == "processed"
    assert released["job_id"] == new_request["job_id"]
    assert released["credential_pool"]["slot_id"] == "account-1"
    assert blocked == {"status": "disabled", "reason": "new_only", "lane": "rewrite"}
    assert provider_calls == 1
    assert json.loads(state.read_text(encoding="utf-8"))["last_ordinal"] == 4
    assert (rewrite_root / "outbox" / f"{rewrite_request['job_id']}.json").exists()
    assert not (rewrite_root / "processing").exists()
    assert not (rewrite_root / "archive").exists()


@pytest.mark.parametrize(
    ("failure", "expected_code", "expected_category"),
    [
        ("nonzero", "CLI_NONZERO", "CLI_NONZERO"),
        ("timeout", "CLI_TIMEOUT", "NETWORK"),
        ("not-found", "CLI_NOT_FOUND", "CLI_UNAVAILABLE"),
        ("envelope", "CLI_ENVELOPE_ERROR", "MALFORMED_PAYLOAD"),
    ],
)
def test_runner_failure_receipt_persists_only_closed_error_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_code: str,
    expected_category: str,
) -> None:
    private_detail = "/Users/example/private prompt GEMINI_API_KEY=must-not-persist raw stderr"
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-closed-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )

    def fake_run(args: list[str], **_kwargs: object) -> object:
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, timeout=1, stderr=private_detail)
        if failure == "not-found":
            raise FileNotFoundError(private_detail)
        if failure == "nonzero":
            return subprocess.CompletedProcess(args, 7, "", private_detail)
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps({"error": private_detail}),
            "",
        )

    monkeypatch.setenv("AGY_GEMINI_CLI", "/opt/tools/gemini")
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    result = process_once(tmp_path)
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text(encoding="utf-8"))

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "GeminiCliFailure",
        "error_code": expected_code,
    }
    assert failed["error_code"] == expected_code
    assert failed["failure_category"] == expected_category
    assert set(failed) == {
        "schema_version",
        "job_id",
        "request_sha256",
        "error_type",
        "error_code",
        "failure_category",
        "completed_at",
    }
    persisted = failed_path.read_text(encoding="utf-8")
    for forbidden in ("prompt", "response", "stdout", "stderr", "GEMINI_API_KEY", "/Users/"):
        assert forbidden not in persisted


def test_outbox_failure_preserves_closed_error_code(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-code-consumer",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "job_id": request["job_id"],
                "request_sha256": request["request_sha256"],
                "error_type": "GeminiCliFailure",
                "error_code": "CLI_TIMEOUT",
                "completed_at": "2026-07-25T23:00:00+08:00",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "GeminiCliFailure"
    assert raised.value.error_code == "CLI_TIMEOUT"


@pytest.mark.parametrize(
    "unsafe_error_type",
    [
        "PRIVATE_PATH_MARKER/CREDENTIAL_MARKER",
        "X" * 10_000,
        ["PRIVATE_PATH_MARKER"],
        {"credential": "CREDENTIAL_MARKER"},
        7,
        None,
    ],
)
def test_failure_consumer_closes_untrusted_error_type(
    tmp_path: Path,
    unsafe_error_type: object,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-invalid-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{request['job_id']}.json",
        _failure_receipt(request, error_type=unsafe_error_type),
    )

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert "PRIVATE_PATH_MARKER" not in str(raised.value)
    assert "CREDENTIAL_MARKER" not in str(raised.value)


@pytest.mark.parametrize(
    "malformation",
    [
        "job-id",
        "request-hash",
        "extra-field",
        "missing-field",
        "invalid-code",
        "invalid-broker",
        "unhashable-broker",
        "http-status-only",
        "http-class-only",
        "invalid-http-status",
        "mismatched-http-class",
        "mismatched-http-code",
        "http-diagnostic-on-cli",
        "invalid-timestamp",
        "non-object",
    ],
)
def test_failure_consumer_rejects_misbound_or_malformed_receipt(
    tmp_path: Path,
    malformation: str,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-malformed-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    receipt: object = _failure_receipt(request, error_type="RuntimeError")
    assert isinstance(receipt, dict)
    if malformation == "job-id":
        receipt["job_id"] = "0" * 40
    elif malformation == "request-hash":
        receipt["request_sha256"] = "0" * 64
    elif malformation == "extra-field":
        receipt["message"] = "PRIVATE_PATH_MARKER"
    elif malformation == "missing-field":
        receipt.pop("completed_at")
    elif malformation == "invalid-code":
        receipt["error_type"] = "GeminiCliFailure"
        receipt["error_code"] = ["CLI_TIMEOUT"]
    elif malformation == "invalid-broker":
        receipt["error_type"] = "V4BrokerFailure"
        receipt["broker_diagnostic"] = {"message": "CREDENTIAL_MARKER"}
    elif malformation == "unhashable-broker":
        receipt["error_type"] = "V4BrokerFailure"
        receipt["broker_diagnostic"] = {
            "replay_status": ["PRIVATE_PATH_MARKER"],
            "process_count": {"credential": "CREDENTIAL_MARKER"},
            "outcome": [],
            "result_validation": {},
        }
    elif malformation == "http-status-only":
        receipt.update(
            error_type="GeminiApiFailure",
            error_code="API_HTTP_ERROR",
            http_status=503,
        )
    elif malformation == "http-class-only":
        receipt.update(
            error_type="GeminiApiFailure",
            error_code="API_HTTP_ERROR",
            http_status_class="5xx",
        )
    elif malformation == "invalid-http-status":
        receipt.update(
            error_type="GeminiApiFailure",
            error_code="API_HTTP_ERROR",
            http_status=True,
            http_status_class="5xx",
        )
    elif malformation == "mismatched-http-class":
        receipt.update(
            error_type="GeminiApiFailure",
            error_code="API_HTTP_ERROR",
            http_status=503,
            http_status_class="4xx",
        )
    elif malformation == "mismatched-http-code":
        receipt.update(
            error_type="GeminiApiFailure",
            error_code="API_AUTH",
            http_status=503,
            http_status_class="5xx",
        )
    elif malformation == "http-diagnostic-on-cli":
        receipt.update(
            error_type="GeminiCliFailure",
            error_code="CLI_NONZERO",
            http_status=503,
            http_status_class="5xx",
        )
    elif malformation == "invalid-timestamp":
        receipt["completed_at"] = "2026-99-99T99:99:99+08:00"
    else:
        receipt = ["PRIVATE_PATH_MARKER", "CREDENTIAL_MARKER"]
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{request['job_id']}.json",
        receipt,
    )

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert "PRIVATE_PATH_MARKER" not in str(raised.value)
    assert "CREDENTIAL_MARKER" not in str(raised.value)


def test_failure_consumer_closes_invalid_json_without_echoing_payload(
    tmp_path: Path,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-invalid-json-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text('{"error_type":"PRIVATE_PATH_MARKER"', encoding="utf-8")

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert "PRIVATE_PATH_MARKER" not in str(raised.value)


def test_failure_consumer_closes_deep_valid_json_recursion(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-deep-json-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker = "/Users/PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(_deep_failure_json(marker), encoding="utf-8")

    with pytest.raises(outbox.ExternalJobFailed) as raised:
        consume_external_response(tmp_path, request)

    assert raised.value.error_type == "InvalidFailureReceipt"
    assert marker not in str(raised.value)
    assert raised.value.__cause__ is None


def test_deep_failure_json_does_not_leak_to_cli_or_operation_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = create_external_request(
        queue_root,
        namespace="opaque-run-deep-json-cli",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker = "/Users/PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(_deep_failure_json(marker), encoding="utf-8")

    class ConsumerClient:
        writer_model = "gemini-test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            return consume_external_response(queue_root, request)

    operation_receipt = tmp_path / "writer-operation.json"
    with pytest.raises(outbox.ExternalJobFailed):
        pipeline._generate_with_receipt(
            ConsumerClient(),
            "writer",
            "public prompt",
            SCHEMA,
            operation_receipt,
        )
    assert marker not in operation_receipt.read_text(encoding="utf-8")

    monkeypatch.setattr(
        outbox,
        "run_pipeline_tick",
        lambda *_args: consume_external_response(queue_root, request),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["agy_gemini_outbox", "tick", str(run_dir), "--queue-root", str(queue_root)],
    )
    assert outbox.main() == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert marker not in combined
    assert "Traceback" not in combined
    assert str(tmp_path) not in combined
    assert json.loads(captured.out)["error_type"] == "InvalidFailureReceipt"


def test_invalid_failure_receipt_does_not_leak_to_cli_stdout_or_operation_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = create_external_request(
        queue_root,
        namespace="opaque-run-cli-invalid-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker = "PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    outbox.atomic_write_json(
        queue_root / "failed" / f"{request['job_id']}.json",
        _failure_receipt(request, error_type=marker),
    )

    class ConsumerClient:
        writer_model = "gemini-test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            return consume_external_response(queue_root, request)

    operation_receipt = tmp_path / "writer-operation.json"
    with pytest.raises(outbox.ExternalJobFailed) as raised:
        pipeline._generate_with_receipt(
            ConsumerClient(),
            "writer",
            "public prompt",
            SCHEMA,
            operation_receipt,
        )
    persisted = operation_receipt.read_text(encoding="utf-8")
    assert marker not in str(raised.value)
    assert marker not in persisted

    monkeypatch.setattr(
        outbox,
        "run_pipeline_tick",
        lambda *_args: consume_external_response(queue_root, request),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["agy_gemini_outbox", "tick", str(run_dir), "--queue-root", str(queue_root)],
    )
    assert outbox.main() == 1
    stdout = capsys.readouterr().out
    assert marker not in stdout
    assert json.loads(stdout)["error_type"] == "InvalidFailureReceipt"


def test_runner_requeues_stale_processing_job_after_interrupted_worker(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-stale-processing",
        role="writer",
        model="gemini-test-writer",
        prompt="產生公開 candidate",
        response_schema=SCHEMA,
    )
    outbox_path = tmp_path / "outbox" / f"{request['job_id']}.json"
    processing_path = tmp_path / "processing" / outbox_path.name
    processing_path.parent.mkdir()
    os.replace(outbox_path, processing_path)
    stale_time = time.time() - runner.STALE_PROCESSING_SECONDS - 1
    os.utime(processing_path, (stale_time, stale_time))

    result = process_once(tmp_path, generate_json=lambda *_args: {"ok": True})

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert not processing_path.exists()
    assert (tmp_path / "archive" / processing_path.name).exists()


@pytest.mark.parametrize(
    "crash_point",
    ["before-provider", "during-provider", "after-response"],
)
def test_production_pool_stale_recovery_never_retries_consumed_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_point: str,
) -> None:
    class SimulatedCrash(BaseException):
        pass

    manifest, _credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace=f"production-stale-{crash_point}",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    state = tmp_path / "round-robin-state.json"
    provider_calls = 0
    crash_enabled = True

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}'

    def provider(*_args: object, **_kwargs: object) -> FakeResponse:
        nonlocal provider_calls
        provider_calls += 1
        if crash_enabled and crash_point == "during-provider":
            raise SimulatedCrash
        return FakeResponse()

    real_read_api_key = runner._read_production_api_key
    real_atomic_write = runner.atomic_write_json

    def read_api_key(descriptor: int) -> str:
        if crash_enabled and crash_point == "before-provider":
            raise SimulatedCrash
        return real_read_api_key(descriptor)

    def atomic_write(path: Path, payload: dict[str, object]) -> None:
        real_atomic_write(path, payload)
        if (
            crash_enabled
            and crash_point == "after-response"
            and path.parent.name == "inbox"
        ):
            raise SimulatedCrash

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner, "_read_production_api_key", read_api_key)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", provider)
    monkeypatch.setattr(runner, "atomic_write_json", atomic_write)

    with pytest.raises(SimulatedCrash):
        process_once(queue_root)

    processing_path = queue_root / "processing" / f"{request['job_id']}.json"
    stale_time = time.time() - runner.STALE_PROCESSING_SECONDS - 1
    os.utime(processing_path, (stale_time, stale_time))
    calls_after_crash = provider_calls

    crash_enabled = False
    monkeypatch.setattr(runner, "_read_production_api_key", real_read_api_key)
    monkeypatch.setattr(runner, "atomic_write_json", real_atomic_write)
    result = process_once(queue_root)

    assert result == {"status": "idle"}
    assert provider_calls == calls_after_crash
    assert not (queue_root / "outbox" / processing_path.name).exists()
    assert not processing_path.exists()
    assert (queue_root / "archive" / processing_path.name).exists()
    if crash_point == "after-response":
        assert (queue_root / "inbox" / processing_path.name).exists()
        assert not (queue_root / "failed" / processing_path.name).exists()
    else:
        failed = json.loads(
            (queue_root / "failed" / processing_path.name).read_text(encoding="utf-8")
        )
        assert failed["error_type"] == "RuntimeError"
    attempt_marker = (
        queue_root / "production-attempts" / f"{request['job_id']}.attempt"
    )
    assert attempt_marker.exists()
    attempt_record = json.loads(attempt_marker.read_text(encoding="utf-8"))
    assert attempt_record["attempt_status"] == (
        "succeeded" if crash_point == "after-response" else "failed"
    )


@pytest.mark.parametrize("provider_outcome", ["success", "failure"])
def test_production_attempt_evidence_blocks_terminal_same_job_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_outcome: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace=f"production-replay-{provider_outcome}",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    state = tmp_path / "round-robin-state.json"
    provider_calls = 0

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}'

    def provider(provider_request: object, **_kwargs: object) -> FakeResponse:
        nonlocal provider_calls
        provider_calls += 1
        if provider_outcome == "failure":
            raise pipeline.urllib.error.HTTPError(
                getattr(provider_request, "full_url", "https://example.invalid"),
                429,
                "private-provider-detail",
                {},
                io.BytesIO(b"private-provider-body"),
            )
        return FakeResponse()

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", provider)

    first = process_once(queue_root)
    marker = queue_root / "production-attempts" / f"{request['job_id']}.attempt"
    first_record = json.loads(marker.read_text(encoding="utf-8"))
    assert first_record["attempt_status"] == (
        "succeeded" if provider_outcome == "success" else "failed"
    )
    assert provider_calls == 1

    archive = queue_root / "archive" / f"{request['job_id']}.json"
    replay = queue_root / "outbox" / archive.name
    replay.parent.mkdir(parents=True, exist_ok=True)
    replay.write_bytes(archive.read_bytes())
    second = process_once(queue_root)

    assert first["status"] == (
        "processed" if provider_outcome == "success" else "failed"
    )
    assert second["status"] == "failed"
    assert second["error_type"] == "ProductionAttemptReplay"
    assert provider_calls == 1
    assert json.loads(marker.read_text(encoding="utf-8")) == first_record
    if provider_outcome == "success":
        assert (queue_root / "inbox" / archive.name).exists()
        assert not (queue_root / "failed" / archive.name).exists()
    else:
        assert (queue_root / "failed" / archive.name).exists()


@pytest.mark.parametrize(
    "unsafe_kind",
    [
        "directory-symlink",
        "directory-writable",
        "marker-symlink",
        "marker-wrong-mode",
        "marker-corrupt",
        "marker-unknown-key",
        "marker-job-mismatch",
        "marker-request-mismatch",
    ],
)
def test_production_attempt_evidence_rejects_unsafe_metadata_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_kind: str,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace=f"production-marker-{unsafe_kind}",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    marker_directory = queue_root / "production-attempts"
    real_directory = tmp_path / "real-production-attempts"
    if unsafe_kind == "directory-symlink":
        real_directory.mkdir(mode=0o700)
        marker_directory.symlink_to(real_directory, target_is_directory=True)
    else:
        marker_directory.mkdir(mode=0o700)
    marker = marker_directory / f"{request['job_id']}.attempt"
    if unsafe_kind == "directory-writable":
        marker_directory.chmod(0o777)
    elif unsafe_kind == "marker-symlink":
        target = tmp_path / "attempt-target"
        target.write_text("{}\n", encoding="utf-8")
        marker.symlink_to(target)
    elif unsafe_kind.startswith("marker-"):
        payload: dict[str, object] = {
            "schema_version": 1,
            "job_id": request["job_id"],
            "request_sha256": request["request_sha256"],
            "attempt_status": "started",
        }
        if unsafe_kind == "marker-corrupt":
            marker.write_text("{\n", encoding="utf-8")
        else:
            if unsafe_kind == "marker-unknown-key":
                payload["unknown"] = True
            elif unsafe_kind == "marker-job-mismatch":
                payload["job_id"] = "0" * 64
            elif unsafe_kind == "marker-request-mismatch":
                payload["request_sha256"] = "0" * 64
            marker.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        marker.chmod(0o644 if unsafe_kind == "marker-wrong-mode" else 0o600)

    provider_calls = 0

    def provider(*_args: object, **_kwargs: object) -> object:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("unsafe marker metadata reached provider")

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv(
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE",
        str(tmp_path / "round-robin-state.json"),
    )
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", provider)

    result = process_once(queue_root)

    assert result["status"] == "failed"
    assert provider_calls == 0
    assert not (tmp_path / "round-robin-state.json").exists()


def test_production_attempt_marker_replacement_fails_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _credentials = _write_production_pool(tmp_path)
    queue_root = tmp_path / "queue"
    request = create_external_request(
        queue_root,
        namespace="production-marker-replacement",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    state = tmp_path / "round-robin-state.json"
    provider_calls = 0
    real_read_api_key = runner._read_production_api_key

    def replace_marker(descriptor: int) -> str:
        api_key = real_read_api_key(descriptor)
        marker = (
            queue_root / "production-attempts" / f"{request['job_id']}.attempt"
        )
        marker.unlink()
        marker.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "job_id": request["job_id"],
                    "request_sha256": request["request_sha256"],
                    "attempt_status": "started",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        marker.chmod(0o600)
        return api_key

    def provider(*_args: object, **_kwargs: object) -> object:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("replaced marker reached provider")

    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_FILE", str(manifest))
    monkeypatch.setenv("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE", str(state))
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    monkeypatch.setattr(runner, "_read_production_api_key", replace_marker)
    monkeypatch.setattr(pipeline, "_single_request_urlopen", provider)

    result = process_once(queue_root)

    assert result["status"] == "failed"
    assert result["error_type"] == "ProductionAttemptEvidenceError"
    assert provider_calls == 0


def test_runner_does_not_requeue_fresh_processing_job(tmp_path: Path) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-live-processing",
        role="writer",
        model="gemini-test-writer",
        prompt="產生公開 candidate",
        response_schema=SCHEMA,
    )
    outbox_path = tmp_path / "outbox" / f"{request['job_id']}.json"
    processing_path = tmp_path / "processing" / outbox_path.name
    processing_path.parent.mkdir()
    os.replace(outbox_path, processing_path)

    result = process_once(tmp_path, generate_json=lambda *_args: {"ok": True})

    assert result == {"status": "idle"}
    assert processing_path.exists()


def test_runner_flag_off_preserves_single_legacy_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGY_GEMINI_V4_BROKER", raising=False)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-legacy",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 legacy prompt",
        response_schema=SCHEMA,
    )
    calls: list[str] = []

    def generate(_role: str, _model: str, prompt: str, _schema: dict[str, object]) -> dict[str, object]:
        calls.append(prompt)
        return {"ok": True}

    assert process_once(tmp_path, generate_json=generate)["status"] == "processed"
    assert calls == ["公開 legacy prompt"]
    assert json.loads((tmp_path / "inbox" / f"{request['job_id']}.json").read_text())["result"] == {"ok": True}


@pytest.mark.parametrize(
    ("role", "expected_role_instruction", "forbidden_role_instruction"),
    (
        (
            "writer",
            "你是 Pantheon 繁體中文文章 Writer。只輸出符合 schema 的 JSON，不得加入未提供的事實或承諾。",
            "你是獨立 Pantheon 文章 Reviewer。",
        ),
        (
            "reviewer",
            "你是獨立 Pantheon 文章 Reviewer。依規範嚴格審查，只輸出符合 schema 的 JSON；不得假設 Writer 對話內容。",
            "你是 Pantheon 繁體中文文章 Writer。",
        ),
    ),
)
def test_runner_flag_on_uses_only_broker_and_writes_bound_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    expected_role_instruction: str,
    forbidden_role_instruction: str,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", hashlib.sha256(executable.read_bytes()).hexdigest())
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-v4",
        role=role,
        model=f"gemini-test-{role}",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    legacy_calls: list[str] = []
    broker_calls: list[dict[str, object]] = []

    def fake_broker(**kwargs: object) -> BrokerResult:
        broker_calls.append(kwargs)
        return _broker_result(
            "COMPLETE",
            ExecutionReceipt(
                operation_id=request["job_id"],
                item_id=request["namespace"],
                attempt_id="attempt-1",
                request_sha256=request["request_sha256"],
                model=request["model"],
                target_profile="antigravity_cli_v1",
                executable_digest=hashlib.sha256(executable.read_bytes()).hexdigest(),
            ),
            result={"ok": True},
        )

    monkeypatch.setattr(runner, "run_single_shot", fake_broker)
    result = process_once(tmp_path, generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": False})
    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert legacy_calls == []
    assert len(broker_calls) == 1
    effective_prompt = broker_calls[0]["raw_request"].decode()
    canonical_schema = json.dumps(
        SCHEMA,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    expected_effective_prompt = (
        f"{expected_role_instruction}\n"
        "禁止使用任何工具或讀取工作區。\n"
        "輸出必須是單一 JSON object，不得有 Markdown code fence。\n"
        f"JSON Schema：{canonical_schema}\n\n"
        "任務：\n公開 V4 prompt"
    )
    assert effective_prompt == expected_effective_prompt
    assert forbidden_role_instruction not in effective_prompt
    assert hashlib.sha256(broker_calls[0]["raw_request"]).hexdigest() == hashlib.sha256(
        expected_effective_prompt.encode()
    ).hexdigest()
    assert len(broker_calls[0]["raw_request"]) == len(expected_effective_prompt.encode())
    assert broker_calls[0]["request_sha256"] == request["request_sha256"]


def test_maximum_valid_outbox_payload_fits_v4_effective_prompt_ceiling() -> None:
    empty_schema = {"description": "", "type": "object"}
    empty_schema_bytes = outbox._json_bytes(empty_schema)
    response_schema = {
        "description": "x" * (outbox.MAX_SCHEMA_BYTES - len(empty_schema_bytes)),
        "type": "object",
    }
    prompt = "x" * outbox.MAX_PROMPT_BYTES

    request = outbox.build_external_request(
        namespace="maximum-valid-v4-envelope",
        role="writer",
        model="gemini-3.5-flash",
        prompt=prompt,
        response_schema=response_schema,
    )
    effective_prompt = runner._render_v4_effective_prompt(
        request["role"],
        request["prompt"],
        request["response_schema"],
    )

    assert len(outbox._json_bytes(response_schema)) == outbox.MAX_SCHEMA_BYTES
    assert len(effective_prompt) <= broker.MAX_AGY_PROMPT_BYTES


def test_production_runner_explicitly_selects_closed_profile_for_unknown_basename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    monkeypatch.setenv("AGY_GEMINI_V4_PROFILE", "raw_stdin_v1")
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-explicit-profile",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    broker_calls: list[dict[str, object]] = []

    def fake_broker(**kwargs: object) -> BrokerResult:
        broker_calls.append(kwargs)
        receipt = ExecutionReceipt(
            request["job_id"],
            request["namespace"],
            "attempt-1",
            request["request_sha256"],
            request["model"],
            "antigravity_cli_v1",
            executable_digest,
        )
        return _broker_result("BLOCKED", receipt)

    monkeypatch.setattr(runner, "run_single_shot", fake_broker)

    assert process_once(tmp_path)["status"] == "failed"
    assert broker_calls[0]["target_profile"] == "antigravity_cli_v1"
    assert broker_calls[0]["expected_executable_digest"] == executable_digest
    failed = json.loads((tmp_path / "failed" / f"{request['job_id']}.json").read_text())
    assert failed["broker_diagnostic"]["result_validation"] == "NOT_EVALUATED"


def test_runner_flag_on_rejects_misbound_complete_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-misbound",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    wrong = ExecutionReceipt(
        "wrong-operation",
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: _broker_result("COMPLETE", wrong, result={"ok": True}))
    legacy_calls: list[str] = []
    result = process_once(tmp_path, generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": True})
    assert result["status"] == "failed"
    assert legacy_calls == []
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()


def test_runner_rejects_schema_valid_success_without_production_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-no-provenance",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    synthetic_receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "raw_stdin_v1",
        executable_digest,
    )
    monkeypatch.setattr(
        runner,
        "run_single_shot",
        lambda **_kwargs: _broker_result("COMPLETE", synthetic_receipt, result={"ok": True}),
    )

    result = process_once(tmp_path)

    assert result["status"] == "failed"
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()


def test_broker_preserves_schema_valid_pretty_json_for_stdout_digest_binding(
    tmp_path: Path,
) -> None:
    expected_stdout = json.dumps(
        {"ok": True},
        indent=2,
        sort_keys=True,
    ).encode() + b"\n"
    executable = tmp_path / "pretty-json-target"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "print(json.dumps({'ok': True}, indent=2, sort_keys=True))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()

    result = broker.run_single_shot(
        operation_id="operation-pretty-json",
        item_id="item-pretty-json",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
        executable=executable,
        target_profile=broker.RAW_STDIN_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request=b"public synthetic request",
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=tmp_path / "ledger.jsonl",
        anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
    )

    assert result.caller_contract_satisfied is True
    assert result.result == {"ok": True}
    assert result.result_json == expected_stdout
    assert result.byte_count == len(expected_stdout)
    assert result.stdout_sha256 == hashlib.sha256(expected_stdout).hexdigest()


@pytest.mark.parametrize(
    ("raw_output", "expected_diagnostic"),
    (
        (b"", "EMPTY"),
        (b"\xff", "UTF8_INVALID"),
        (b"```json\n{\"ok\":true}\n```\n", "MARKDOWN_FENCE"),
        (b"result: {\"ok\":true}", "WRAPPED_JSON"),
        (b"{\"ok\":", "PARSE_ERROR_AT_END"),
        (b"{\"ok\":nope}", "PARSE_ERROR_OTHER"),
    ),
)
def test_broker_classifies_json_invalid_without_retaining_output(
    tmp_path: Path,
    raw_output: bytes,
    expected_diagnostic: str,
) -> None:
    executable = tmp_path / f"json-invalid-{expected_diagnostic.lower()}"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"sys.stdout.buffer.write(bytes.fromhex({raw_output.hex()!r}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()

    result = broker.run_single_shot(
        operation_id=f"operation-{expected_diagnostic.lower()}",
        item_id="item-json-invalid",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="synthetic-model",
        executable=executable,
        target_profile=broker.RAW_STDIN_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request=b"public synthetic request",
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=tmp_path / f"{expected_diagnostic.lower()}.jsonl",
        anchor_store=broker.FileAnchorStore(tmp_path / "anchors"),
    )

    assert result.result_validation == "JSON_INVALID"
    assert result.json_diagnostic == expected_diagnostic
    assert result.result_json is None
    trace = result.normalized_trace()
    _assert_normalized_trace_schema(trace)
    assert trace == {
        "replay_status": "COMPLETE",
        "process_count": 1,
        "outcome": "SUCCESS",
        "exit_status": 0,
        "stdout_sha256": hashlib.sha256(raw_output).hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "byte_count": len(raw_output),
        "receipt": {
            "operation_id": f"operation-{expected_diagnostic.lower()}",
            "item_id": "item-json-invalid",
            "attempt_id": "attempt-1",
            "request_sha256": "a" * 64,
            "model": "synthetic-model",
            "target_profile": broker.RAW_STDIN_PROFILE,
            "executable_digest": executable_digest,
        },
        "caller_contract_satisfied": False,
        "result_validation": "JSON_INVALID",
        "result": None,
        "errors": [],
        "automatic_resend_allowed": False,
    }


def test_normalized_trace_schema_rejects_invalid_raw_stdout_bytes() -> None:
    trace = dict.fromkeys(NORMALIZED_TRACE_KEYS)
    trace["stdout_sha256"] = hashlib.sha256(b"\xff").hexdigest()
    _assert_normalized_trace_schema(trace)

    trace["raw_stdout"] = b"\xff"
    with pytest.raises(AssertionError, match="normalized trace schema changed"):
        _assert_normalized_trace_schema(trace)


@pytest.mark.parametrize(
    ("json_diagnostic", "expected"),
    (
        ("MARKDOWN_FENCE", "MARKDOWN_FENCE"),
        ("must-not-persist", None),
        ({"secret": "must-not-persist"}, None),
    ),
)
def test_runner_persists_only_closed_json_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    json_diagnostic: object,
    expected: str | None,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-json-diagnostic",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 JSON diagnostic synthetic request",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        broker.ANTIGRAVITY_CLI_PROFILE,
        executable_digest,
    )
    malformed = BrokerResult(
        replay_status="COMPLETE",
        process_count=1,
        outcome="SUCCESS",
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=(),
        result_validation="JSON_INVALID",
        json_diagnostic=json_diagnostic,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: malformed)

    result = process_once(tmp_path)

    assert result["status"] == "failed"
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text())
    expected_fields = {
        "outcome",
        "process_count",
        "replay_status",
        "result_validation",
    }
    if expected is None:
        assert "json_diagnostic" not in failed["broker_diagnostic"]
    else:
        assert failed["broker_diagnostic"]["json_diagnostic"] == expected
        expected_fields.add("json_diagnostic")
    assert set(failed["broker_diagnostic"]) == expected_fields
    assert "must-not-persist" not in failed_path.read_text()


@pytest.mark.parametrize("status", ("BLOCKED", "AMBIGUOUS", "INVALID"))
def test_runner_flag_on_fails_closed_without_legacy_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace=f"opaque-run-{status.lower()}",
        role="reviewer",
        model="gemini-test-reviewer",
        prompt="公開 V4 prompt",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: _broker_result(status, receipt))
    legacy_calls: list[str] = []
    result = process_once(tmp_path, generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": True})
    assert result["status"] == "failed"
    assert legacy_calls == []
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()
    assert (tmp_path / "failed" / f"{request['job_id']}.json").exists()
    assert (tmp_path / "archive" / f"{request['job_id']}.json").exists()


def test_concurrent_create_loser_returns_replayed_external_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    ledger_path = tmp_path / "ledger.jsonl"
    anchor_store = broker.FileAnchorStore(tmp_path / "anchors")
    binding = broker.Binding("operation-concurrent", "item-concurrent", "attempt-1")
    definitions = [
        ("OPERATION_CREATED", {}),
        ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
        ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4321}),
        ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
    ]
    frames = []
    parent = None
    for sequence, (event_type, fields) in enumerate(definitions, 1):
        event = {
            "schema_version": 2,
            "sequence": sequence,
            "parent_sha256": parent,
            "event_type": event_type,
            "operation_id": binding.operation_id,
            "item_id": binding.item_id,
            "attempt_id": binding.attempt_id,
            **fields,
        }
        encoded = broker.canonical_json(event)
        frames.append(encoded + b"\n")
        parent = hashlib.sha256(encoded).hexdigest()
    assert parent is not None
    real_open = broker.os.open

    def lose_create_race(path: object, flags: int, mode: int = 0o777) -> int:
        if Path(path) == ledger_path and flags & broker.os.O_EXCL:
            ledger_path.write_bytes(b"".join(frames))
            assert anchor_store.compare_and_swap(
                binding.operation_id,
                binding.attempt_id,
                None,
                parent,
            )
            raise FileExistsError
        return real_open(path, flags, mode)

    monkeypatch.setattr(broker.os, "open", lose_create_race)

    result = broker.run_single_shot(
        operation_id=binding.operation_id,
        item_id=binding.item_id,
        attempt_id=binding.attempt_id,
        request_sha256="a" * 64,
        model="gemini-3.5-flash",
        executable=executable,
        target_profile=broker.ANTIGRAVITY_CLI_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request="公開 concurrent duplicate synthetic request".encode(),
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=ledger_path,
        anchor_store=anchor_store,
    )

    assert (result.replay_status, result.process_count) == ("COMPLETE", 1)
    assert result.caller_contract_satisfied is False
    assert result.final_anchor == parent


def test_concurrent_create_loser_returns_invalid_when_race_anchor_is_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    ledger_path = tmp_path / "ledger.jsonl"
    anchor_store = broker.FileAnchorStore(tmp_path / "anchors")
    load_calls = 0
    target_spawns: list[list[str]] = []

    def load_race_anchor(_operation_id: str, _attempt_id: str) -> str | None:
        nonlocal load_calls
        load_calls += 1
        if load_calls == 1:
            return None
        raise broker.AnchorError("synthetic unreadable race anchor")

    def lose_create_race(_path: object, _flags: int, _mode: int = 0o777) -> int:
        raise FileExistsError

    def reject_spawn(command: list[str], **_kwargs: object) -> None:
        target_spawns.append(command)
        raise AssertionError("race loser must not spawn broker or target")

    monkeypatch.setattr(anchor_store, "load", load_race_anchor)
    monkeypatch.setattr(broker.os, "open", lose_create_race)
    monkeypatch.setattr(broker.subprocess, "Popen", reject_spawn)

    result = broker.run_single_shot(
        operation_id="operation-race-invalid",
        item_id="item-race-invalid",
        attempt_id="attempt-1",
        request_sha256="a" * 64,
        model="gemini-3.5-flash",
        executable=executable,
        target_profile=broker.ANTIGRAVITY_CLI_PROFILE,
        expected_executable_digest=executable_digest,
        raw_request="公開 malformed race anchor synthetic request".encode(),
        response_schema=SCHEMA,
        timeout_milliseconds=1500,
        ledger_path=ledger_path,
        anchor_store=anchor_store,
    )

    assert (result.replay_status, result.process_count) == ("INVALID", "UNKNOWN")
    assert result.errors == ("EXTERNAL_ANCHOR_INVALID",)
    assert result.caller_contract_satisfied is False
    assert result.result_json is None
    assert result.final_anchor is None
    assert result.automatic_resend_allowed is False
    assert target_spawns == []
    assert load_calls == 2


def test_runner_flag_on_fails_closed_on_malformed_success_without_legacy_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-malformed",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 malformed-output synthetic request",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    malformed = BrokerResult(
        replay_status="COMPLETE",
        process_count=1,
        outcome="SUCCESS",
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=("MALFORMED_OUTPUT",),
        result_validation="SCHEMA_MISMATCH",
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: malformed)
    legacy_calls: list[str] = []

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: legacy_calls.append("legacy") or {"ok": True},
    )

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "V4BrokerFailure",
    }
    assert legacy_calls == []
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()
    failed = json.loads((tmp_path / "failed" / f"{request['job_id']}.json").read_text())
    assert failed["broker_diagnostic"] == {
        "outcome": "SUCCESS",
        "process_count": 1,
        "replay_status": "COMPLETE",
        "result_validation": "SCHEMA_MISMATCH",
    }
    assert "prompt" not in failed
    assert "result" not in failed


def test_runner_persists_only_closed_schema_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    diagnostic_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ok": {"type": "boolean"},
            "items": {"type": "array", "items": {"type": "boolean"}},
            "a" * 65: {"type": "boolean"},
        },
        "required": ["ok"],
    }
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-schema-diagnostic",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 schema diagnostic synthetic request",
        response_schema=diagnostic_schema,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    malformed = BrokerResult(
        replay_status="COMPLETE",
        process_count=1,
        outcome="SUCCESS",
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=(),
        result_validation="SCHEMA_MISMATCH",
    )
    object.__setattr__(
        malformed,
        "schema_diagnostics",
        (
            broker.SchemaDiagnostic("type", ("ok",)),
            broker.SchemaDiagnostic("message", ("ok",)),
            broker.SchemaDiagnostic("enum", ("unknown-property",)),
            broker.SchemaDiagnostic("type", ({"secret": "must-not-persist"},)),
            broker.SchemaDiagnostic("type", ("ok", "too-deep")),
            broker.SchemaDiagnostic("type", ("items", 10**1000)),
            broker.SchemaDiagnostic("type", ("ok",) * 9),
            broker.SchemaDiagnostic("type", ("a" * 65,)),
        ),
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: malformed)

    result = process_once(tmp_path)

    assert result["status"] == "failed"
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text())
    assert failed["broker_diagnostic"]["schema_diagnostics"] == [
        {"keyword": "type", "path": ["ok"]},
    ]
    assert "must-not-persist" not in failed_path.read_text()
    assert "unknown-property" not in failed_path.read_text()
    assert "message" not in failed_path.read_text()


@pytest.mark.parametrize(
    ("replay_status", "process_count", "outcome", "result_validation"),
    (
        (
            {"secret": "must-not-persist"},
            ["must-not-persist"],
            {"secret": "must-not-persist"},
            {"secret": "must-not-persist"},
        ),
        (
            "must-not-persist",
            "must-not-persist",
            "must-not-persist",
            "must-not-persist",
        ),
    ),
)
def test_runner_closes_all_forged_broker_diagnostic_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replay_status: object,
    process_count: object,
    outcome: object,
    result_validation: object,
) -> None:
    executable = tmp_path / "agy-current"
    executable.write_bytes(b"trusted agy fixture")
    executable_digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE", str(executable))
    monkeypatch.setenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", executable_digest)
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-forged-diagnostic",
        role="reviewer",
        model="gemini-3.5-flash",
        prompt="公開 forged diagnostic synthetic request",
        response_schema=SCHEMA,
    )
    receipt = ExecutionReceipt(
        request["job_id"],
        request["namespace"],
        "attempt-1",
        request["request_sha256"],
        request["model"],
        "antigravity_cli_v1",
        executable_digest,
    )
    secret_marker = "must-not-persist"
    forged = BrokerResult(
        replay_status=replay_status,  # type: ignore[arg-type]
        process_count=process_count,  # type: ignore[arg-type]
        outcome=outcome,  # type: ignore[arg-type]
        exit_status=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        byte_count=8,
        final_anchor="c" * 64,
        receipt=receipt,
        caller_contract_satisfied=False,
        result_json=None,
        errors=("FORGED_DIAGNOSTIC",),
        result_validation=result_validation,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(runner, "run_single_shot", lambda **_kwargs: forged)

    result = process_once(tmp_path)

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "V4BrokerFailure",
    }
    failed_path = tmp_path / "failed" / f"{request['job_id']}.json"
    failed = json.loads(failed_path.read_text())
    assert failed["broker_diagnostic"] == {
        "outcome": None,
        "process_count": "UNKNOWN",
        "replay_status": "INVALID",
        "result_validation": "NOT_EVALUATED",
    }
    assert secret_marker not in failed_path.read_text()


def test_runner_classifies_schema_invalid_payload_before_inbox_side_effect(
    tmp_path: Path,
) -> None:
    request = create_external_request(
        tmp_path,
        namespace="opaque-run-01",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )

    result = process_once(tmp_path, generate_json=lambda *_args: {"wrong": True})

    assert result == {
        "status": "failed",
        "job_id": request["job_id"],
        "error_type": "V4BrokerFailure",
    }
    assert not (tmp_path / "inbox" / f"{request['job_id']}.json").exists()
    failed = json.loads(
        (tmp_path / "failed" / f"{request['job_id']}.json").read_text()
    )
    assert failed["request_sha256"] == request["request_sha256"]
    assert failed["failure_category"] == "SCHEMA_INVALID_PAYLOAD"
    assert failed["broker_diagnostic"]["result_validation"] == "SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "case",
    _rewrite_length_cases(),
    ids=lambda case: str(case["id"]),
)
def test_rewrite_provider_length_mismatch_reaches_local_quality_gate(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    brief, external = _rewrite_length_mismatch_fixture(case)
    response_schema = pipeline.external_candidate_schema(
        "rewrite_existing_body"
    )
    canonical_schema = pipeline.candidate_schema("rewrite_existing_body")
    request = create_external_request(
        tmp_path,
        namespace="rewrite-schema-conformance-red",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 rewrite synthetic prompt",
        response_schema=response_schema,
    )

    result = process_once(
        tmp_path,
        generate_json=lambda *_args: external,
        lane="rewrite",
    )

    assert result == {"status": "processed", "job_id": request["job_id"]}
    provider_result = consume_external_response(tmp_path, request)
    assert provider_result == external
    candidate = pipeline.hydrate_candidate(brief, provider_result)
    findings = pipeline.rewrite_quality_findings(
        brief,
        candidate["articles"],
    )
    assert any(finding["code"] == "paragraph_length" for finding in findings)
    diagnostics = broker._diagnose_json_schema(candidate, canonical_schema)
    assert [(diagnostic.keyword, diagnostic.path) for diagnostic in diagnostics] == [
        (
            case["keyword"],
            (
                "articles",
                0,
                "bodySections",
                case["section_index"],
                "paragraphs",
                case["paragraph_index"],
            ),
        )
    ]


def test_runner_normalizes_new_description_and_paragraph_bounds_without_retry(
    tmp_path: Path,
) -> None:
    response_schema = pipeline.external_candidate_schema("create")
    request = create_external_request(
        tmp_path,
        namespace="new-output-contract-normalization",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 new lane prompt",
        response_schema=response_schema,
    )
    provider_calls = 0

    provider_payload = _new_output_contract_fixture()
    original_paragraph_text = "".join(
        provider_payload["articles"][0]["bodySections"][0]["paragraphs"]
    )

    def successful_provider(
        _role: str,
        _model: str,
        _prompt: str,
        _schema: dict[str, object],
    ) -> dict[str, object]:
        nonlocal provider_calls
        provider_calls += 1
        return provider_payload

    result = process_once(tmp_path, generate_json=successful_provider, lane="new")

    assert result == {"status": "processed", "job_id": request["job_id"]}
    assert provider_calls == 1
    assert not list((tmp_path / "failed").glob("*.json"))
    external = consume_external_response(tmp_path, request)
    article = external["articles"][0]
    assert 70 <= len(article["description"]) <= 95
    normalized_paragraphs = article["bodySections"][0]["paragraphs"]
    assert 2 <= len(normalized_paragraphs) <= 4
    assert all(80 <= len(paragraph) <= 160 for paragraph in normalized_paragraphs)
    assert "".join(normalized_paragraphs) == original_paragraph_text
    assert broker._diagnose_json_schema(external, response_schema) == ()

    target = {
        "id": "NEW-OUTPUT-01",
        "section": "astrology",
        "product": "astrology",
        "slug": "new-output-01",
        "serial": "astrology-0001",
        "urlSlug": "new-output-01",
        "primaryKeyword": "測試關鍵字",
        "published": "2026-07-31",
        "updated": "2026-07-31",
    }
    candidate = pipeline.hydrate_candidate(
        {
            "schema_version": 1,
            "run_id": "new-output-contract-normalization",
            "mode": "create",
            "articles": [{"target": target}],
        },
        external,
        enforce_policy=False,
    )
    pipeline.validate_candidate(candidate, enforce_policy=False)
    assert candidate["articles"][0]["description"] == article["description"]
    assert process_once(
        tmp_path,
        generate_json=lambda *_args: pytest.fail("archived job must not replay"),
        lane="new",
    ) == {"status": "idle"}
    assert provider_calls == 1


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
    assert observed == [2]


def test_pipeline_tick_honors_explicit_model_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(
        json.dumps({"run_id": "model-override-run"}),
        encoding="utf-8",
    )
    observed: list[tuple[str, str]] = []

    def fake_run_writer_reviewer(
        _run_dir: Path,
        client: OutboxGeminiClient,
        max_repairs: int = 2,
    ) -> tuple[dict[str, object], dict[str, object]]:
        observed.append((client.writer_model, client.reviewer_model))
        return {"articles": []}, {"articles": []}

    monkeypatch.setenv("AGY_WRITER_MODEL", "gemini-explicit-writer")
    monkeypatch.setenv("AGY_REVIEWER_MODEL", "gemini-explicit-reviewer")
    monkeypatch.setattr(outbox.pipeline, "run_writer_reviewer", fake_run_writer_reviewer)

    result = run_pipeline_tick(run_dir, tmp_path / "queue")

    assert result["status"] == "complete"
    assert observed == [("gemini-explicit-writer", "gemini-explicit-reviewer")]


def test_pipeline_tick_routes_translation_brief_to_multilingual_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(
        json.dumps({"run_id": "translate-en-001", "mode": "translate_existing"}),
        encoding="utf-8",
    )
    observed: list[int] = []

    def fake_run_writer_reviewer(_run_dir: Path, _client: object, max_repairs: int = 2):
        observed.append(max_repairs)
        return {"articles": []}, {"articles": []}

    monkeypatch.setattr(outbox.multilingual, "run_writer_reviewer", fake_run_writer_reviewer)
    monkeypatch.setattr(
        outbox.pipeline,
        "run_writer_reviewer",
        lambda *_args, **_kwargs: pytest.fail("translation must not use the create pipeline"),
    )

    result = run_pipeline_tick(run_dir, tmp_path / "queue")

    assert result["status"] == "complete"
    assert observed == [2]


def test_translation_continuation_pending_reuses_plan_request_identity(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    queue_root = tmp_path / "queue"
    source = {
        "article_id": "FORTUNE-0039",
        "canonical_path": "/articles/bazi/fortune-0039",
        "title": "八字用神是什麼？",
        "description": "用神要從完整命局判斷，不能只套單一五行。",
        "answer": "先看強弱、寒燥與五行流通，再找改善失衡的方向。",
        "tags": ["八字", "用神"],
        "faq": [
            {
                "question": "用神能固定嗎？",
                "answer": "不能脫離完整命局與運勢條件固定判斷。",
            }
        ],
        "bodySections": [
            {
                "heading": "先看整體失衡",
                "paragraphs": ["強弱、寒燥與五行流通必須一起判斷。"],
            },
            {
                "heading": "再找調整方向",
                "paragraphs": ["同一五行在不同命局中可能有不同作用。"],
            },
        ],
    }
    brief = {
        "schema_version": 1,
        "run_id": "auto-i18n-ko-149a513358e0e81cadcd",
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": "FORTUNE-0039:ko",
                "locale": "ko",
                "source_article_id": "FORTUNE-0039",
                "source_path": source["canonical_path"],
                "source_sha256": outbox.multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }
    external_candidate = {
        "articles": [
            {
                "slot": "article-01",
                "title": "사주 용신은 어떻게 찾나요?",
                "description": "용신은 명식 전체의 불균형을 살핀 뒤 정하며 하나의 오행만으로 고정할 수 없습니다.",
                "answer": "강약과 계절, 오행의 흐름을 함께 살펴 조정 방향을 찾습니다.",
                "tags": ["사주", "용신"],
                "faq": [
                    {
                        "question": "용신은 항상 같나요?",
                        "answer": "명식과 운의 조건을 벗어나 고정할 수 없습니다.",
                    }
                ],
                "bodySections": [
                    {"heading": "용신이 답하는 질문", "paragraphs": ["먼저 명식의 불균형을 확인합니다."]},
                    {"heading": "강약과 계절 확인", "paragraphs": ["두 조건을 함께 살핍니다."]},
                    {"heading": "오행 흐름 비교", "paragraphs": ["조정 후보를 비교합니다."]},
                    {"heading": "고정 결론 피하기", "paragraphs": ["조건에 따라 역할이 달라집니다."]},
                ],
            }
        ]
    }
    candidate = outbox.multilingual._hydrate_candidate(brief, external_candidate)
    review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": "FORTUNE-0039:ko",
                "candidate_sha256": pipeline.article_sha256(candidate["articles"][0]),
                "verdict": "REJECT",
                "findings": [
                    {
                        "code": "NON_NATIVE_SEARCH_INTENT",
                        "message": "검색 의도가 자연스럽지 않습니다",
                    }
                ],
            }
        ],
    }
    pipeline.write_json(run_dir / "brief.json", brief)
    pipeline.write_json(run_dir / "candidate.json", candidate)
    pipeline.write_json(run_dir / "review.json", review)
    for attempt in range(1, 4):
        pipeline.write_json(
            run_dir / "attempts" / f"{attempt:02d}" / "external-review.json",
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": review["articles"][0]["findings"],
                    }
                ]
            },
        )
    original_candidate = (run_dir / "candidate.json").read_bytes()
    original_review = (run_dir / "review.json").read_bytes()

    pending_ids = []
    for _replay in range(2):
        with pytest.raises(ExternalJobPending) as pending:
            run_pipeline_tick(run_dir, queue_root)
        pending_ids.append(pending.value.job_id)

    queued = list((queue_root / "outbox").glob("*.json"))
    state = json.loads((run_dir / "continuation/state.json").read_text())
    assert pending_ids[0] == pending_ids[1]
    assert len(queued) == 1
    assert state["next_generation"] == 4
    assert state["completed_generations"] == []
    assert sorted(path.name for path in (run_dir / "generations").iterdir()) == ["04"]
    assert (run_dir / "candidate.json").read_bytes() == original_candidate
    assert (run_dir / "review.json").read_bytes() == original_review
    for forbidden in ("approval.json", "apply.json", "publish.json", "run-evidence.json"):
        assert not (run_dir / forbidden).exists()


def test_outbox_client_retry_keeps_logical_request_identity(tmp_path: Path) -> None:
    client = outbox.OutboxGeminiClient(tmp_path, namespace="retry-json")
    first = outbox.create_external_request(
        tmp_path,
        namespace="retry-json",
        role="writer",
        model=client.writer_model,
        prompt="公開 prompt",
        response_schema=SCHEMA,
    )
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{first['job_id']}.json",
        _failure_receipt(first, error_type="JSONDecodeError"),
    )

    with pytest.raises(ExternalJobPending) as pending:
        client.generate_json("writer", "公開 prompt", SCHEMA)

    assert pending.value.job_id != first["job_id"]
    retry_request = json.loads((tmp_path / "outbox" / f"{pending.value.job_id}.json").read_text())
    assert retry_request["namespace"] == "retry-json"
    assert retry_request["request_sha256"] == first["request_sha256"]
    assert retry_request["transport_attempt"] == 1
    assert retry_request["prompt_sha256"] == first["prompt_sha256"]


def test_create_external_request_recognizes_operator_terminalizing_claim(
    tmp_path: Path,
) -> None:
    request = outbox.create_external_request(
        tmp_path,
        namespace="operator-claim",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator claim",
        response_schema=SCHEMA,
        transport_attempt=1,
    )
    outbox_path = tmp_path / "outbox" / f"{request['job_id']}.json"
    claimed_path = tmp_path / "outbox" / f"{request['job_id']}.json.terminalizing"
    os.replace(outbox_path, claimed_path)
    claimed_bytes = claimed_path.read_bytes()

    replay = outbox.create_external_request(
        tmp_path,
        namespace="operator-claim",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator claim",
        response_schema=SCHEMA,
        transport_attempt=1,
    )

    assert replay == request
    assert claimed_path.read_bytes() == claimed_bytes
    assert not outbox_path.exists()


def test_outbox_client_stops_after_two_json_decode_retries(tmp_path: Path) -> None:
    client = outbox.OutboxGeminiClient(tmp_path, namespace="retry-stop")
    failed_job_ids: list[str] = []
    logical_request_ids: set[str] = set()
    for retry_index in range(3):
        request = outbox.create_external_request(
            tmp_path,
            namespace="retry-stop",
            role="reviewer",
            model=client.reviewer_model,
            prompt="公開 prompt",
            response_schema=SCHEMA,
            transport_attempt=retry_index,
        )
        failed_job_ids.append(request["job_id"])
        logical_request_ids.add(str(request["request_sha256"]))
        outbox.atomic_write_json(
            tmp_path / "failed" / f"{request['job_id']}.json",
            _failure_receipt(request, error_type="JSONDecodeError"),
        )

    with pytest.raises(outbox.ExternalJobFailed) as failure:
        client.generate_json("reviewer", "公開 prompt", SCHEMA)

    assert failure.value.job_id == failed_job_ids[-1]
    assert failure.value.error_type == "JSONDecodeError"
    assert failure.value.failure_category == "MALFORMED_PAYLOAD"
    assert failure.value.transport_attempts == 3
    assert failure.value.request_sha256 in logical_request_ids
    assert len(logical_request_ids) == 1
    assert len(list((tmp_path / "outbox").glob("*.json"))) == 3


@pytest.mark.parametrize(
    ("error_type", "error_code", "broker_diagnostic", "expected_category"),
    [
        ("GeminiCliFailure", "CLI_NONZERO", None, "CLI_NONZERO"),
        ("GeminiApiFailure", "API_TRANSPORT_ERROR", None, "NETWORK"),
        ("JSONDecodeError", None, None, "MALFORMED_PAYLOAD"),
        (
            "V4BrokerFailure",
            None,
            {
                "replay_status": "COMPLETE",
                "process_count": 1,
                "outcome": "SUCCESS",
                "result_validation": "SCHEMA_MISMATCH",
                "schema_diagnostics": [{"keyword": "required", "path": []}],
            },
            "SCHEMA_INVALID_PAYLOAD",
        ),
        ("GeminiApiFailure", "API_HTTP_ERROR", None, "PROVIDER_UNAVAILABLE"),
        ("GeminiApiFailure", "API_RATE_LIMITED", None, "QUOTA"),
    ],
)
def test_transport_failure_retry_allowlist_preserves_logical_request_identity(
    tmp_path: Path,
    error_type: str,
    error_code: str | None,
    broker_diagnostic: dict[str, object] | None,
    expected_category: str,
) -> None:
    client = outbox.OutboxGeminiClient(tmp_path, namespace="closed-taxonomy")
    first = outbox.create_external_request(
        tmp_path,
        namespace="closed-taxonomy",
        role="writer",
        model=client.writer_model,
        prompt="公開 synthetic transport taxonomy",
        response_schema=SCHEMA,
    )
    receipt = _failure_receipt(
        first,
        error_type=error_type,
        error_code=error_code,
    )
    if broker_diagnostic is not None:
        receipt["broker_diagnostic"] = broker_diagnostic
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{first['job_id']}.json",
        receipt,
    )

    with pytest.raises(ExternalJobPending) as pending:
        client.generate_json(
            "writer",
            "公開 synthetic transport taxonomy",
            SCHEMA,
        )

    retry = json.loads(
        (tmp_path / "outbox" / f"{pending.value.job_id}.json").read_text()
    )
    assert retry["request_sha256"] == first["request_sha256"]
    assert retry["transport_attempt"] == 1
    assert retry["job_id"] != first["job_id"]
    assert len(list((tmp_path / "outbox").glob("*.json"))) == 2
    assert len(list((tmp_path / "failed").glob("*.json"))) == 1
    classified = outbox.classify_external_failure(receipt)
    assert classified == expected_category


@pytest.mark.parametrize(
    ("error_type", "error_code", "expected_category"),
    [
        ("GeminiApiFailure", "API_AUTH", "AUTH"),
        ("GeminiApiFailure", "API_MODEL_UNAVAILABLE", "MODEL_UNAVAILABLE"),
        ("GeminiCliFailure", "CLI_NOT_FOUND", "CLI_UNAVAILABLE"),
    ],
)
def test_transport_failure_terminal_categories_do_not_enqueue_retry(
    tmp_path: Path,
    error_type: str,
    error_code: str,
    expected_category: str,
) -> None:
    client = outbox.OutboxGeminiClient(tmp_path, namespace="terminal-taxonomy")
    first = outbox.create_external_request(
        tmp_path,
        namespace="terminal-taxonomy",
        role="writer",
        model=client.writer_model,
        prompt="公開 synthetic terminal transport taxonomy",
        response_schema=SCHEMA,
    )
    receipt = _failure_receipt(
        first,
        error_type=error_type,
        error_code=error_code,
    )
    outbox.atomic_write_json(
        tmp_path / "failed" / f"{first['job_id']}.json",
        receipt,
    )

    with pytest.raises(ExternalJobFailed) as failure:
        client.generate_json(
            "writer",
            "公開 synthetic terminal transport taxonomy",
            SCHEMA,
        )

    assert failure.value.job_id == first["job_id"]
    assert failure.value.request_sha256 == first["request_sha256"]
    assert failure.value.failure_category == expected_category
    assert failure.value.transport_attempts == 1
    assert len(list((tmp_path / "outbox").glob("*.json"))) == 1
    assert len(list((tmp_path / "failed").glob("*.json"))) == 1
    assert not list((tmp_path / "completed").glob("*.json"))
    classified = outbox.classify_external_failure(receipt)
    assert classified == expected_category


def test_quota_exhaustion_uses_three_primary_attempts_then_distinct_fallback(
    tmp_path: Path,
) -> None:
    namespace = "quota-aware-routing"
    prompt = "公開 quota-aware routing"
    client = outbox.OutboxGeminiClient(tmp_path, namespace=namespace)
    for attempt, slot_id in enumerate(allocator.PRODUCTION_SLOT_IDS):
        request = outbox.create_external_request(
            tmp_path,
            namespace=namespace,
            role="writer",
            model=pipeline.DEFAULT_WRITER_MODEL,
            prompt=prompt,
            response_schema=SCHEMA,
            transport_attempt=attempt,
        )
        outbox.atomic_write_json(
            tmp_path / "failed" / f"{request['job_id']}.json",
            _failure_receipt(
                request,
                error_type="GeminiApiFailure",
                error_code="API_QUOTA",
                credential_slot_id=slot_id,
            ),
        )
    fallback = outbox.create_external_request(
        tmp_path,
        namespace=namespace,
        role="writer",
        model=pipeline.DEFAULT_WRITER_FALLBACK_MODEL,
        prompt=prompt,
        response_schema=SCHEMA,
    )
    outbox.atomic_write_json(
        tmp_path / "inbox" / f"{fallback['job_id']}.json",
        {
            "schema_version": 1,
            "job_id": fallback["job_id"],
            "request_sha256": fallback["request_sha256"],
            "model": fallback["model"],
            "completed_at": "2026-08-17T12:00:00+08:00",
            "result": {"ok": True},
        },
    )

    assert client.generate_json("writer", prompt, SCHEMA) == {"ok": True}
    assert client._active_models == {
        "writer": pipeline.DEFAULT_WRITER_FALLBACK_MODEL,
        "reviewer": pipeline.DEFAULT_REVIEWER_MODEL,
    }
    routing = json.loads(
        (
            tmp_path
            / "model-routing"
            / f"{namespace}-writer.json"
        ).read_text(encoding="utf-8")
    )
    assert routing == {
        "schema_version": 1,
        "namespace": namespace,
        "role": "writer",
        "primary_model": pipeline.DEFAULT_WRITER_MODEL,
        "selected_model": pipeline.DEFAULT_WRITER_FALLBACK_MODEL,
        "reason": "API_QUOTA",
        "exhausted_slot_ids": list(allocator.PRODUCTION_SLOT_IDS),
    }


@pytest.mark.parametrize("error_code", ["API_RATE_LIMITED", "API_HTTP_ERROR"])
def test_transient_exhaustion_does_not_downgrade_model(
    tmp_path: Path,
    error_code: str,
) -> None:
    namespace = "rate-limit-no-downgrade"
    prompt = "公開 transient rate limit"
    client = outbox.OutboxGeminiClient(tmp_path, namespace=namespace)
    last_request: dict[str, object] | None = None
    for attempt in range(3):
        request = outbox.create_external_request(
            tmp_path,
            namespace=namespace,
            role="writer",
            model=pipeline.DEFAULT_WRITER_MODEL,
            prompt=prompt,
            response_schema=SCHEMA,
            transport_attempt=attempt,
        )
        last_request = request
        outbox.atomic_write_json(
            tmp_path / "failed" / f"{request['job_id']}.json",
            _failure_receipt(
                request,
                error_type="GeminiApiFailure",
                error_code=error_code,
            ),
        )

    with pytest.raises(ExternalJobFailed) as raised:
        client.generate_json("writer", prompt, SCHEMA)

    assert last_request is not None
    assert raised.value.job_id == last_request["job_id"]
    assert not (tmp_path / "model-routing").exists()
    assert all(
        json.loads(path.read_text())["model"] == pipeline.DEFAULT_WRITER_MODEL
        for path in (tmp_path / "outbox").glob("*.json")
    )


def test_reviewer_fails_closed_when_only_fallback_matches_active_writer(
    tmp_path: Path,
) -> None:
    namespace = "independent-reviewer-route"
    prompt = "公開 independent reviewer route"
    client = outbox.OutboxGeminiClient(tmp_path, namespace=namespace)
    client._active_models["writer"] = pipeline.DEFAULT_WRITER_FALLBACK_MODEL
    last_request: dict[str, object] | None = None
    for attempt in range(3):
        request = outbox.create_external_request(
            tmp_path,
            namespace=namespace,
            role="reviewer",
            model=pipeline.DEFAULT_REVIEWER_MODEL,
            prompt=prompt,
            response_schema=SCHEMA,
            transport_attempt=attempt,
        )
        last_request = request
        outbox.atomic_write_json(
            tmp_path / "failed" / f"{request['job_id']}.json",
            _failure_receipt(
                request,
                error_type="GeminiApiFailure",
                error_code="API_QUOTA",
            ),
        )

    with pytest.raises(ExternalJobFailed) as raised:
        client.generate_json("reviewer", prompt, SCHEMA)

    assert last_request is not None
    assert raised.value.job_id == last_request["job_id"]
    assert all(
        json.loads(path.read_text())["model"] == pipeline.DEFAULT_REVIEWER_MODEL
        for path in (tmp_path / "outbox").glob("*.json")
    )


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


def test_invalid_writer_schema_uses_transport_budget_without_semantic_repair(
    tmp_path: Path,
) -> None:
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
    first_request = json.loads(
        (queue_root / "outbox" / f"{first_pending.value.job_id}.json").read_text()
    )
    process_once(
        queue_root,
        generate_json=lambda *_args: {"articles": [{"slot": "article-01"}]},
    )
    failed = json.loads(
        (
            queue_root
            / "failed"
            / f"{first_request['job_id']}.json"
        ).read_text()
    )
    assert failed["failure_category"] == "SCHEMA_INVALID_PAYLOAD"

    with pytest.raises(ExternalJobPending) as retry_pending:
        run_pipeline_tick(run_dir, queue_root)

    assert retry_pending.value.job_id != first_pending.value.job_id
    retry = json.loads((queue_root / "outbox" / f"{retry_pending.value.job_id}.json").read_text())
    assert retry["namespace"] == first_request["namespace"]
    assert retry["request_sha256"] == first_request["request_sha256"]
    assert retry["prompt"] == first_request["prompt"]
    assert retry["transport_attempt"] == 1
    assert not (run_dir / "attempts" / "02").exists()
    for forbidden in ("candidate.json", "review.json", "approval.json", "run-evidence.json"):
        assert not (run_dir / forbidden).exists()


def test_invalid_reviewer_schema_exhausts_transport_without_semantic_repair(
    tmp_path: Path,
) -> None:
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
    for _transport_retry in range(outbox.OUTBOX_MAX_TRANSPORT_RETRIES):
        with pytest.raises(ExternalJobPending):
            run_pipeline_tick(run_dir, queue_root)
        process_once(queue_root, generate_json=lambda *_args: {"wrong": True})

    with pytest.raises(ExternalJobFailed) as exhausted:
        run_pipeline_tick(run_dir, queue_root)

    assert exhausted.value.failure_category == "SCHEMA_INVALID_PAYLOAD"
    assert exhausted.value.transport_attempts == 3
    assert not (run_dir / "attempts/02").exists()
    for forbidden in ("candidate.json", "review.json", "approval.json", "run-evidence.json"):
        assert not (run_dir / forbidden).exists()

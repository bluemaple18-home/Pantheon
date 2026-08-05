from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.agy_gemini_outbox import create_external_request
from scripts.agy_gemini_runner import process_once


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


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

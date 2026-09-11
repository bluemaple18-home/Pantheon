from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import agy_gemini_outbox as outbox
from scripts import agy_gemini_runner as runner
from scripts import agy_seo_copy_pipeline as pipeline


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


def test_default_model_route_is_formal_writer_lite(monkeypatch: pytest.MonkeyPatch) -> None:
    route = pipeline.load_model_route_config(pipeline.MODEL_ROUTE_CONFIG_PATH)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("AGY_GEMINI_MODEL_ROUTE_CONFIG", str(route.path))
    monkeypatch.setenv("AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST", route.digest)
    monkeypatch.setenv("AGY_WRITER_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("AGY_REVIEWER_MODEL", "gemini-3.1-flash-lite")

    actual = pipeline.model_route_config_from_environment()
    capability = pipeline.validate_gemini_api_model_capabilities(actual)

    assert actual.routes == {
        "writer": ("gemini-3.5-flash-lite",),
        "reviewer": ("gemini-3.1-flash-lite",),
    }
    assert capability == {
        "status": "PASS",
        "transport": "api",
        "writer_model": "gemini-3.5-flash-lite",
        "reviewer_model": "gemini-3.1-flash-lite",
    }


def test_installer_refuses_staging_when_manifest_actor_differs_from_repo() -> None:
    installer = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "install_agy_gemini_coordinator_launchd.sh"
    ).read_text(encoding="utf-8")

    guard = 'if [[ "${ACTOR_ROOT}" != "${REPO_ROOT}" ]]; then'
    route_stage = 'install -m 600 "${MODEL_ROUTE_CONFIG_PATH}" "${STAGED_MODEL_ROUTE_CONFIG}"'

    assert guard in installer
    assert route_stage in installer
    assert installer.index(guard) < installer.index(route_stage)
    assert "runtime manifest actor root 與 coordinator installer 不一致。" in installer


def test_exact_run_selector_can_continue_lite_without_claiming_old_flash(
    tmp_path: Path,
) -> None:
    old_run_id = "legacy-flash-run"
    target_run_id = "target-lite-run"
    old = outbox.create_external_request(
        tmp_path,
        namespace=hashlib.sha256(old_run_id.encode("utf-8")).hexdigest()[:24],
        role="writer",
        model="gemini-3.5-flash",
        prompt="old request",
        response_schema=SCHEMA,
    )
    target = outbox.create_external_request(
        tmp_path,
        namespace=hashlib.sha256(target_run_id.encode("utf-8")).hexdigest()[:24],
        role="writer",
        model="gemini-3.5-flash-lite",
        prompt="target request",
        response_schema=SCHEMA,
    )

    assert runner._peek_next_model(tmp_path, exact_run_ids=[target_run_id]) == (
        "gemini-3.5-flash-lite",
        target["job_id"],
    )

    result = runner.process_once(
        tmp_path,
        generate_json=lambda *_args: {"ok": True},
        exact_run_ids=[target_run_id],
    )

    assert result["status"] == "processed"
    assert result["job_id"] == target["job_id"]
    assert (tmp_path / "archive" / f"{target['job_id']}.json").is_file()
    assert (tmp_path / "outbox" / f"{old['job_id']}.json").is_file()
    assert not (tmp_path / "processing" / f"{old['job_id']}.json").exists()


def test_exact_run_selector_does_not_make_unselected_flash_a_fallback(
    tmp_path: Path,
) -> None:
    old_run_id = "legacy-flash-run"
    old = outbox.create_external_request(
        tmp_path,
        namespace=hashlib.sha256(old_run_id.encode("utf-8")).hexdigest()[:24],
        role="writer",
        model="gemini-3.5-flash",
        prompt="old request",
        response_schema=SCHEMA,
    )

    assert runner._peek_next_model(tmp_path, exact_run_ids=["missing-lite-run"]) is None
    result = runner.process_once(
        tmp_path,
        generate_json=lambda *_args: pytest.fail("unselected request must not run"),
        exact_run_ids=["missing-lite-run"],
    )

    assert result == {"status": "idle"}
    assert (tmp_path / "outbox" / f"{old['job_id']}.json").is_file()
    assert not (tmp_path / "processing").exists()


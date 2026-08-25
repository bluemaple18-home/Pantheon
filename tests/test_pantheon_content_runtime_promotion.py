from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from scripts import pantheon_content_runtime_manifest as runtime
from scripts import pantheon_content_runtime_promotion as promotion


AUTHORIZATION_DIGEST = "a" * 64
REGRESSION_ID = "REG-PANTHEON-AGGREGATE-RUNTIME-PROMOTION-001"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_commit(repo: Path, name: str, body: str) -> str:
    (repo / "runtime.txt").write_text(body, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", name)
    return _git(repo, "rev-parse", "HEAD")


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(encoded)
    return promotion.file_sha256(path)


def _identity_envelope(
    article_ids: list[str] | None = None,
    *,
    mode: str = "create",
    lane: str = "new",
) -> dict[str, object]:
    identity = {
        "schema_version": 1,
        "mode": mode,
        "lane": lane,
        "article_ids": sorted(article_ids or []),
    }
    digest = hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {**identity, "digest": digest}


def _preserved_brief(run_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "create",
        "articles": [],
    }


def _write_capacity_receipt(path: Path, *, status: str = "PASS") -> str:
    payload = {
        "schema_version": 1,
        "regression_id": "REG-PANTHEON-CAPACITY-WRITE-CYCLES-001",
        "status": status,
        "mode": "bounded-synthetic-dry-run",
        "cycles": [
            {
                "before_bytes": 0,
                "after_bytes": 4096,
                "before_file_count": 0,
                "after_file_count": 1,
                "host_free_before": 100000000000,
                "host_free_after": 99999995904,
                "rss_before": 1000,
                "rss_after": 1000,
                "swap_before": 0,
                "swap_after": 0,
                "elapsed_seconds": 0.1,
                "growth_bytes": 4096,
                "rss_available": True,
                "swap_available": True,
            },
            {
                "before_bytes": 4096,
                "after_bytes": 8192,
                "before_file_count": 1,
                "after_file_count": 2,
                "host_free_before": 99999995904,
                "host_free_after": 99999991808,
                "rss_before": 1000,
                "rss_after": 1000,
                "swap_before": 0,
                "swap_after": 0,
                "elapsed_seconds": 0.1,
                "growth_bytes": 4096,
                "rss_available": True,
                "swap_available": True,
            },
        ],
        "reclamation": {
            "bytes_before": 8192,
            "bytes_after": 4096,
            "allowlist": ["<exercise-root>/cycle-1.bin"],
        },
        "stop_loss": {
            "status": "STOPPED" if status == "PASS" else "STOP_FAILED",
            "triggered": True,
            "registered_labels": [
                "com.pantheon.agy-content-publisher",
                "com.pantheon.agy-gemini-coordinator",
                "com.pantheon.agy-gemini-new",
                "com.pantheon.agy-gemini-rewrite",
                "com.pantheon.agy-gemini-i18n-new",
                "com.pantheon.agy-gemini-i18n-rewrite",
            ],
            "outcomes": {},
            "remaining_loaded": [],
            "cross_project_deletions": [],
        },
    }
    return _write_json(path, payload)


def _runtime_fixture(tmp_path: Path) -> tuple[promotion.PromotionRequest, dict[str, str]]:
    remote = tmp_path / "origin.git"
    source = tmp_path / "source"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    _git(source, "config", "user.email", "promotion@example.invalid")
    _git(source, "config", "user.name", "Pantheon Promotion")
    old_sha = _write_commit(source, "old", "old\n")
    _write_commit(source, "new", "new\n")
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "-qu", "origin", "main")
    new_sha = _git(source, "rev-parse", "HEAD")

    actor = tmp_path / "actor"
    subprocess.run(["git", "clone", "-q", str(remote), str(actor)], check=True)
    _git(actor, "checkout", "-q", "--detach", old_sha)
    _git(actor, "remote", "set-url", "origin", str(remote))

    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    stage = tmp_path / "private-stage"
    for path in (queue / "runs", state, logs, stage):
        path.mkdir(parents=True)
    (stage / "previous.txt").write_text("previous-stage\n", encoding="utf-8")

    current_manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity=f"gate2-actor:{old_sha}:activation-only",
        runtime_digest="1" * 64,
        config_version="formal-runtime-v2-gate2",
        generation=f"g2-{old_sha[:10]}",
        actor_head=old_sha,
        python_executable=Path(sys.executable).resolve(strict=True),
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime.write_manifest(manifest_path, current_manifest)
    capacity_receipt_path = tmp_path / "capacity-receipt.json"
    capacity_receipt_digest = _write_capacity_receipt(capacity_receipt_path)

    request = promotion.PromotionRequest(
        source_repo=source,
        source_sha=new_sha,
        expected_origin=str(remote),
        actor_root=actor,
        expected_current_actor_sha=old_sha,
        manifest_path=manifest_path,
        expected_current_manifest_digest=current_manifest["manifest_digest"],
        private_stage_root=stage,
        expected_current_stage_digest=promotion.tree_digest(stage),
        transaction_root=tmp_path / "promotion-tx",
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        target_identity=f"gate2-actor:{new_sha}:activation-only",
        target_runtime_digest="2" * 64,
        target_config_version="formal-runtime-v2-gate2",
        target_generation=f"g2-{new_sha[:10]}",
        target_python_executable=Path(sys.executable).resolve(strict=True),
        authorization_digest=AUTHORIZATION_DIGEST,
        capacity_receipt_path=capacity_receipt_path,
        capacity_receipt_digest=capacity_receipt_digest,
        correlation_id=f"apf004-runtime-promotion-{new_sha[:10]}",
        target_uv_executable=Path(sys.executable).resolve(strict=True),
    )
    return request, {"old_sha": old_sha, "new_sha": new_sha}


def _snapshot(request: promotion.PromotionRequest) -> dict[str, object]:
    return {
        "actor_head": _git(request.actor_root, "rev-parse", "HEAD"),
        "manifest": json.loads(request.manifest_path.read_text(encoding="utf-8")),
        "stage_digest": promotion.tree_digest(request.private_stage_root),
        "barrier_exists": promotion.barrier_path(request).exists(),
    }


def _planned_digest(request: promotion.PromotionRequest) -> str:
    return str(promotion.plan_promotion(request)["plan_digest"])


def test_plan_is_deterministic_and_zero_write(tmp_path: Path) -> None:
    request, identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)

    first = promotion.plan_promotion(request)
    second = promotion.plan_promotion(request)

    assert first == second
    assert first["status"] == "READY_TO_APPLY"
    assert first["regression_id"] == REGRESSION_ID
    assert first["plan_digest"] == second["plan_digest"]
    assert first["ordered_states"] == [
        "PREPARED",
        "ACTOR_PROMOTED",
        "MANIFEST_WRITTEN",
        "STAGE_INSTALLED",
        "POSTCHECK_PASSED",
        "COMMITTED",
    ]
    assert first["target_actor_sha"] == identities["new_sha"]
    assert [item["stage"] for item in first["write_set"]] == [
        "ACTOR_PROMOTED",
        "MANIFEST_WRITTEN",
        "STAGE_INSTALLED",
        "STAGE_INSTALLED",
    ]
    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_apply_success_keeps_rollback_bundle_until_finalize(tmp_path: Path) -> None:
    request, identities = _runtime_fixture(tmp_path)

    applied = promotion.apply_promotion(
        request,
        expected_plan_digest=_planned_digest(request),
    )

    assert applied["status"] == "POSTCHECK_PASSED"
    assert _git(request.actor_root, "rev-parse", "HEAD") == identities["new_sha"]
    assert runtime.load_manifest(
        request.manifest_path,
        applied["target_manifest_digest"],
        expected_python_executable=request.target_python_executable,
    )["actor_head"] == identities["new_sha"]
    assert promotion.barrier_path(request).exists()
    assert promotion.rollback_bundle_path(request).exists()

    finalized = promotion.finalize_promotion(
        request,
        expected_plan_digest=applied["plan_digest"],
    )

    assert finalized["status"] == "COMMITTED"
    assert not promotion.rollback_bundle_path(request).exists()
    status = promotion.status_promotion(request)
    assert status["state"] == "COMMITTED"
    assert status["audit_receipt_exists"] is True


def test_apply_preserves_exact_active_run_queue(tmp_path: Path) -> None:
    request, identities = _runtime_fixture(tmp_path)
    run_id = "apf-create-run-new-preserved"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", _preserved_brief(run_id))
    (run_dir / "draft.md").write_text("durable draft\n", encoding="utf-8")
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
            "identity_envelope": _identity_envelope(),
        },
    )
    (request.queue_root / "outbox").mkdir()
    _write_json(
        request.queue_root / "outbox" / "retry.json",
        {"schema_version": 1, "job_id": "fresh-retry-job"},
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before_queue = promotion.tree_digest(request.queue_root)
    before_run = promotion.tree_digest(run_dir)

    plan = promotion.plan_promotion(request)
    applied = promotion.apply_promotion(
        request,
        expected_plan_digest=plan["plan_digest"],
    )

    assert applied["status"] == "POSTCHECK_PASSED"
    assert plan["preserved_run_ids"] == [run_id]
    assert plan["postchecks"][3] == "queue_preserved"
    assert plan["queue_identity_snapshot"]["preserved_runs"] == [
        {
            "path": "state.json",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "run_tree_digest": before_run,
            "status": "active",
        }
    ]
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert promotion.tree_digest(run_dir) == before_run
    assert _git(request.actor_root, "rev-parse", "HEAD") == identities["new_sha"]


def test_plan_rejects_dangling_preserved_run_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "dangling-active-run"
    (request.queue_root / "gsc-copy").mkdir()
    missing_run_dir = request.queue_root / "gsc-copy" / run_id
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(missing_run_dir),
            "status": "active",
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="run directory is missing"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_preserved_run_outside_durable_root_before_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "actor-local-active-run"
    (request.queue_root / "gsc-copy").mkdir()
    run_dir = tmp_path / "actor-local-gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", _preserved_brief(run_id))
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="outside durable root"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_actor_local_queue_root_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    actor_local_queue = request.actor_root / ".work" / "formal-queue"
    (request.actor_root / ".git" / "info" / "exclude").write_text(
        ".work/\n",
        encoding="utf-8",
    )
    actor_local_queue.parent.mkdir(parents=True)
    request.queue_root.replace(actor_local_queue)
    run_id = "actor-local-active-run"
    run_dir = actor_local_queue / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "create",
            "articles": [{"target": {"id": "V2-MBTI-INTJ-WORK"}}],
        },
    )
    _write_json(
        actor_local_queue / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
        },
    )
    current = json.loads(request.manifest_path.read_text(encoding="utf-8"))
    manifest = runtime.build_manifest(
        actor_root=request.actor_root,
        queue_root=actor_local_queue,
        publisher_state_root=request.publisher_state_root,
        log_root=request.log_root,
        identity=str(current["identity"]),
        runtime_digest=str(current["runtime_digest"]),
        config_version=str(current["config_version"]),
        generation=str(current["generation"]),
        actor_head=str(current["actor_head"]),
        python_executable=Path(str(current["python_executable"])),
        uv_executable=request.target_uv_executable,
    )
    runtime.write_manifest(request.manifest_path, manifest)
    request = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "queue_root": actor_local_queue,
            "expected_current_manifest_digest": manifest["manifest_digest"],
            "preserved_run_ids": (run_id,),
        }
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="actor-local"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_preserved_run_brief_identity_mismatch_before_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "registered-active-run"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        {"schema_version": 1, "run_id": "drifted-active-run"},
    )
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="brief identity mismatch"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_preserved_article_envelope_drift_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "registered-article-drift"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "create",
            "articles": [{"target": {"id": "V2-MBTI-ENFP-LOVE"}}],
        },
    )
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
            "identity_envelope": _identity_envelope(["V2-MBTI-INTJ-WORK"]),
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="brief identity mismatch"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_missing_identity_envelope_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-missing-envelope"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", _preserved_brief(run_id))
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="identity envelope"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_preserves_exact_complete_run_queue(tmp_path: Path) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "completed-reviewer-run"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", _preserved_brief(run_id))
    _write_json(
        request.queue_root / "runs" / "completed.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "complete",
            "identity_envelope": _identity_envelope(),
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )

    plan = promotion.plan_promotion(request)

    assert plan["status"] == "READY_TO_APPLY"
    assert plan["preserved_run_ids"] == [run_id]


def test_plan_preserves_exact_failed_run_and_gsc_copy_queue(tmp_path: Path) -> None:
    request, identities = _runtime_fixture(tmp_path)
    run_id = "failed-reviewer-run"
    gsc_copy_run = request.queue_root / "gsc-copy" / run_id
    gsc_copy_run.mkdir(parents=True)
    _write_json(
        gsc_copy_run / "brief.json",
        _preserved_brief(run_id),
    )
    _write_json(
        gsc_copy_run / "candidate.json",
        {"schema_version": 1, "run_id": run_id, "status": "needs-review"},
    )
    (gsc_copy_run / "review.md").write_text("review stays private\n", encoding="utf-8")
    _write_json(
        request.queue_root / "runs" / "failed.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(gsc_copy_run),
            "status": "failed",
            "identity_envelope": _identity_envelope(),
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before_queue = promotion.tree_digest(request.queue_root)

    first = promotion.plan_promotion(request)
    second = promotion.plan_promotion(request)
    applied = promotion.apply_promotion(
        request,
        expected_plan_digest=first["plan_digest"],
    )

    assert first == second
    assert first["status"] == "READY_TO_APPLY"
    assert first["preserved_run_ids"] == [run_id]
    assert first["queue_identity_snapshot"]["preserved_runs"] == [
        {
            "path": "failed.json",
            "run_id": run_id,
            "run_dir": str(gsc_copy_run),
            "run_tree_digest": promotion.tree_digest(gsc_copy_run),
            "status": "failed",
        }
    ]
    assert {
        entry["path"]
        for entry in first["queue_identity_snapshot"]["gsc_copy"]
        if entry["type"] == "file"
    } == {
        f"{run_id}/brief.json",
        f"{run_id}/candidate.json",
        f"{run_id}/review.md",
    }
    assert applied["status"] == "POSTCHECK_PASSED"
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert _git(request.actor_root, "rev-parse", "HEAD") == identities["new_sha"]


def test_preserved_failed_run_requires_identity_snapshot(tmp_path: Path) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    (request.queue_root / "gsc-copy").mkdir()
    _write_json(
        request.queue_root / "runs" / "failed.json",
        {"schema_version": 1, "status": "failed"},
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": ("failed-reviewer-run",)}
    )

    with pytest.raises(promotion.PromotionError, match="not preservable"):
        promotion.plan_promotion(request)


def test_preserved_run_contract_rejects_unexpected_run(tmp_path: Path) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_dir = request.queue_root / "gsc-copy" / "unexpected-run"
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        _preserved_brief("unexpected-run"),
    )
    _write_json(
        request.queue_root / "runs" / "state.json",
        {
            "schema_version": 1,
            "run_id": "unexpected-run",
            "run_dir": str(run_dir),
            "status": "active",
            "identity_envelope": _identity_envelope(),
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": ("expected-run",)}
    )

    with pytest.raises(promotion.PromotionError, match="identity mismatch"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()


def test_preserved_run_contract_rejects_duplicate_identity(tmp_path: Path) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "preserved-run"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", _preserved_brief(run_id))
    for name in ("one.json", "two.json"):
        _write_json(
            request.queue_root / "runs" / name,
            {
                "schema_version": 1,
                "run_id": run_id,
                "run_dir": str(run_dir),
                "status": "active",
                "identity_envelope": _identity_envelope(),
            },
        )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )

    with pytest.raises(promotion.PromotionError, match="duplicate identity"):
        promotion.plan_promotion(request)


def test_queue_snapshot_rejects_nested_symlink(tmp_path: Path) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    (request.queue_root / "linked-state").symlink_to(request.publisher_state_root)

    with pytest.raises(promotion.PromotionError, match="queue snapshot contains symlink"):
        promotion.plan_promotion(request)


def test_plan_rejects_gsc_copy_only_residue_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    gsc_copy = request.queue_root / "gsc-copy"
    gsc_copy.mkdir()
    (gsc_copy / "residue.json").write_text("{}", encoding="utf-8")

    with pytest.raises(promotion.PromotionError, match="queue residue"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_gsc_copy_invalid_json_fails_closed_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    run_id = "failed-reviewer-run"
    gsc_copy_run = request.queue_root / "gsc-copy" / run_id
    gsc_copy_run.mkdir(parents=True)
    _write_json(
        gsc_copy_run / "brief.json",
        _preserved_brief(run_id),
    )
    (gsc_copy_run / "candidate.json").write_text("{invalid", encoding="utf-8")
    _write_json(
        request.queue_root / "runs" / "failed.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(gsc_copy_run),
            "status": "failed",
            "identity_envelope": _identity_envelope(),
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )

    with pytest.raises(promotion.PromotionError, match="gsc-copy JSON is invalid"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_gsc_copy_plan_apply_drift_rolls_back_without_rewriting_existing_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    run_id = "failed-reviewer-run"
    gsc_copy_run = request.queue_root / "gsc-copy" / run_id
    gsc_copy_run.mkdir(parents=True)
    _write_json(
        gsc_copy_run / "brief.json",
        _preserved_brief(run_id),
    )
    _write_json(
        gsc_copy_run / "candidate.json",
        {"schema_version": 1, "run_id": run_id, "status": "needs-review"},
    )
    _write_json(
        request.queue_root / "runs" / "failed.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(gsc_copy_run),
            "status": "failed",
            "identity_envelope": _identity_envelope(),
        },
    )
    original_candidate = (gsc_copy_run / "candidate.json").read_bytes()
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    plan = promotion.plan_promotion(request)
    real_install_private_stage = promotion._install_private_stage

    def drift_gsc_copy(
        promoted_request: promotion.PromotionRequest,
        manifest: dict[str, Any],
    ) -> None:
        real_install_private_stage(promoted_request, manifest)
        _write_json(
            gsc_copy_run / "drift.json",
            {"schema_version": 1, "run_id": run_id, "status": "unexpected-drift"},
        )

    monkeypatch.setattr(promotion, "_install_private_stage", drift_gsc_copy)

    with pytest.raises(promotion.PromotionError, match="ROLLBACK_COMPLETE"):
        promotion.apply_promotion(
            request,
            expected_plan_digest=plan["plan_digest"],
        )

    receipt = promotion.load_receipt(request)
    assert receipt["state"] == "ROLLED_BACK"
    assert receipt["state_before_rollback"] == "STAGE_INSTALLED"
    assert (gsc_copy_run / "candidate.json").read_bytes() == original_candidate
    assert (gsc_copy_run / "drift.json").is_file()
    assert _snapshot(request) == before


def test_queue_empty_directory_drift_rolls_back_without_rewriting_existing_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    anchor = request.queue_root / "anchor.txt"
    anchor.write_text("existing queue bytes\n", encoding="utf-8")
    original_anchor = anchor.read_bytes()
    plan = promotion.plan_promotion(request)
    real_install_private_stage = promotion._install_private_stage

    def drift_empty_queue_directory(
        promoted_request: promotion.PromotionRequest,
        manifest: dict[str, Any],
    ) -> None:
        real_install_private_stage(promoted_request, manifest)
        (promoted_request.queue_root / "outbox" / "empty-drift").mkdir(parents=True)

    monkeypatch.setattr(promotion, "_install_private_stage", drift_empty_queue_directory)

    with pytest.raises(promotion.PromotionError, match="ROLLBACK_COMPLETE"):
        promotion.apply_promotion(
            request,
            expected_plan_digest=plan["plan_digest"],
        )

    receipt = promotion.load_receipt(request)
    assert receipt["state"] == "ROLLED_BACK"
    assert receipt["state_before_rollback"] == "STAGE_INSTALLED"
    assert anchor.read_bytes() == original_anchor
    assert (request.queue_root / "outbox" / "empty-drift").is_dir()
    assert _snapshot(request) == before


def test_gsc_copy_root_existence_drift_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    plan = promotion.plan_promotion(request)
    real_install_private_stage = promotion._install_private_stage

    def drift_empty_gsc_copy_root(
        promoted_request: promotion.PromotionRequest,
        manifest: dict[str, Any],
    ) -> None:
        real_install_private_stage(promoted_request, manifest)
        (promoted_request.queue_root / "gsc-copy").mkdir()

    monkeypatch.setattr(promotion, "_install_private_stage", drift_empty_gsc_copy_root)

    with pytest.raises(promotion.PromotionError, match="ROLLBACK_COMPLETE"):
        promotion.apply_promotion(
            request,
            expected_plan_digest=plan["plan_digest"],
        )

    receipt = promotion.load_receipt(request)
    assert receipt["state"] == "ROLLED_BACK"
    assert receipt["state_before_rollback"] == "STAGE_INSTALLED"
    assert (request.queue_root / "gsc-copy").is_dir()
    assert _snapshot(request) == before


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "capacity receipt is missing"),
        ("failed", "capacity stop-loss is not PASS"),
        ("digest", "capacity receipt digest mismatch"),
    ],
)
def test_capacity_receipt_contract_fails_closed_before_runtime_mutation(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    if mutation == "missing":
        request.capacity_receipt_path.unlink()
    elif mutation == "failed":
        digest = _write_capacity_receipt(request.capacity_receipt_path, status="NO-GO")
        request = promotion.PromotionRequest(
            **{**request.__dict__, "capacity_receipt_digest": digest}
        )
    else:
        request = promotion.PromotionRequest(
            **{**request.__dict__, "capacity_receipt_digest": "f" * 64}
        )

    with pytest.raises(promotion.PromotionError, match=message):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


@pytest.mark.parametrize(
    ("failure", "expected_state"),
    [
        ("actor", "PREPARED"),
        ("manifest", "ACTOR_PROMOTED"),
        ("stage", "MANIFEST_WRITTEN"),
        ("postcheck", "STAGE_INSTALLED"),
    ],
)
def test_apply_failure_matrix_rolls_back_actor_manifest_and_stage(
    tmp_path: Path,
    failure: str,
    expected_state: str,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="ROLLBACK_COMPLETE"):
        promotion.apply_promotion(
            request,
            expected_plan_digest=_planned_digest(request),
            failure_injection=failure,
        )

    receipt = promotion.load_receipt(request)
    assert receipt["state_before_rollback"] == expected_state
    assert receipt["state"] == "ROLLED_BACK"
    assert _snapshot(request) == before


def test_crash_recovery_status_and_explicit_rollback(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionCrashStop):
        promotion.apply_promotion(
            request,
            expected_plan_digest=_planned_digest(request),
            stop_after_state="ACTOR_PROMOTED",
        )

    status = promotion.status_promotion(request)
    assert status["state"] == "ACTOR_PROMOTED"
    assert status["rollback_required"] is True
    with pytest.raises(promotion.PromotionError, match="existing transaction"):
        promotion.apply_promotion(
            request,
            expected_plan_digest=status["plan_digest"],
        )

    rolled_back = promotion.rollback_promotion(
        request,
        expected_plan_digest=status["plan_digest"],
    )

    assert rolled_back["status"] == "ROLLED_BACK"
    assert _snapshot(request) == before


def test_authorization_drift_fails_finalize_and_rollback_closed(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    applied = promotion.apply_promotion(
        request,
        expected_plan_digest=_planned_digest(request),
    )
    drifted = promotion.PromotionRequest(
        **{**request.__dict__, "authorization_digest": "c" * 64}
    )

    with pytest.raises(promotion.PromotionError, match="authorization"):
        promotion.finalize_promotion(drifted, expected_plan_digest=applied["plan_digest"])
    with pytest.raises(promotion.PromotionError, match="authorization"):
        promotion.rollback_promotion(drifted, expected_plan_digest=applied["plan_digest"])


def test_apply_requires_expected_plan_digest_before_transaction(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)

    with pytest.raises(TypeError, match="expected_plan_digest"):
        promotion.apply_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_apply_rejects_plan_digest_mismatch_before_transaction(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="plan digest mismatch"):
        promotion.apply_promotion(
            request,
            expected_plan_digest="0" * 64,
        )

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_cli_apply_help_requires_expected_plan_digest() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.pantheon_content_runtime_promotion",
            "apply",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--expected-plan-digest" in completed.stdout


def test_cli_help_exposes_public_transaction_commands() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.pantheon_content_runtime_promotion", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    for command in ("plan", "apply", "rollback", "finalize", "status"):
        assert command in completed.stdout

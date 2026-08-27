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


def _preserved_brief(
    run_id: str,
    *,
    mode: str = "create",
    lane: str | None = None,
    article_ids: list[str] | None = None,
) -> dict[str, object]:
    articles: list[dict[str, object]] = []
    for article_id in article_ids or []:
        if mode == "create":
            articles.append({"target": {"id": article_id}})
        elif mode == "rewrite_existing_body":
            articles.append({"article_id": article_id})
        elif mode == "translate_existing":
            articles.append({"source_article_id": article_id})
    brief: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": mode,
        "articles": articles,
    }
    if lane is not None:
        brief["lane"] = lane
    return brief


def _write_preserved_state(
    request: promotion.PromotionRequest,
    name: str,
    *,
    run_id: str,
    run_dir: Path,
    status: str,
    identity_envelope: dict[str, object],
) -> None:
    _write_json(
        request.queue_root / "runs" / name,
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": status,
            "identity_envelope": identity_envelope,
        },
    )


def _canonical_json_sha256(payload: object) -> str:
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _terminalization_receipt_path(
    request: promotion.PromotionRequest,
    run_id: str,
) -> Path:
    return request.queue_root / "dangling-active-terminalizations" / f"{run_id}.json"


def _write_dangling_active_terminalization(
    request: promotion.PromotionRequest,
    *,
    run_id: str,
    run_dir: Path,
    receipt_patch: dict[str, object] | None = None,
    state_patch: dict[str, object] | None = None,
    write_receipt: bool = True,
) -> tuple[Path, Path]:
    receipt_relative = f"dangling-active-terminalizations/{run_id}.json"
    before_state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "active",
    }
    before_digest = _canonical_json_sha256(before_state)
    after_state = {
        **before_state,
        "status": "failed",
        "error_type": "DanglingActiveRunTerminalized",
        "dangling_active_terminalization": {
            "receipt": receipt_relative,
            "reason": "UNRECOVERABLE_RUN_DIR_MISSING",
            "before_digest": before_digest,
        },
        "terminalized_at": "2026-08-26T00:00:00+00:00",
    }
    if state_patch:
        after_state.update(state_patch)
    after_digest = _canonical_json_sha256(after_state)
    receipt = {
        "schema_version": 1,
        "status": "terminalized",
        "action": "terminalize_dangling_active",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "reason": "UNRECOVERABLE_RUN_DIR_MISSING",
        "before_digest": before_digest,
        "after_digest": after_digest,
        "before": before_state,
        "after": after_state,
        "terminalized_at": "2026-08-26T00:00:00+00:00",
    }
    if receipt_patch:
        receipt.update(receipt_patch)
    state_path = request.queue_root / "runs" / f"{run_id}.json"
    _write_json(state_path, after_state)
    receipt_path = _terminalization_receipt_path(request, run_id)
    if write_receipt:
        receipt_path.parent.mkdir(parents=True)
        _write_json(receipt_path, receipt)
    return state_path, receipt_path


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


def test_plan_authority_digest_ignores_runtime_locator_paths(tmp_path: Path) -> None:
    request, identities = _runtime_fixture(tmp_path)
    alt_source = tmp_path / "alternate" / "source"
    subprocess.run(
        ["git", "clone", "-q", request.expected_origin, str(alt_source)],
        check=True,
    )
    _git(alt_source, "checkout", "-q", "--detach", identities["new_sha"])
    _git(alt_source, "remote", "set-url", "origin", request.expected_origin)
    alt_capacity = tmp_path / "alternate" / "capacity" / "capacity-receipt.json"
    alt_capacity.parent.mkdir(parents=True)
    alt_capacity.write_bytes(request.capacity_receipt_path.read_bytes())
    relocated = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "source_repo": alt_source,
            "capacity_receipt_path": alt_capacity,
            "transaction_root": tmp_path / "alternate" / "promotion-tx",
        }
    )

    original = promotion.plan_promotion(request)
    replayed = promotion.plan_promotion(relocated)

    assert original["source_repo"] != replayed["source_repo"]
    assert original["capacity_receipt_path"] != replayed["capacity_receipt_path"]
    assert original["plan_authority"] == replayed["plan_authority"]
    assert original["plan_digest"] == replayed["plan_digest"]
    assert original["plan_digest"] == promotion._json_digest(original["plan_authority"])


def test_plan_authority_digest_changes_when_stable_authority_changes(
    tmp_path: Path,
) -> None:
    request, identities = _runtime_fixture(tmp_path)
    baseline = promotion.plan_promotion(request)
    old_source = tmp_path / "old-source"
    subprocess.run(
        ["git", "clone", "-q", request.expected_origin, str(old_source)],
        check=True,
    )
    _git(old_source, "checkout", "-q", "--detach", identities["old_sha"])
    _git(old_source, "remote", "set-url", "origin", request.expected_origin)
    old_source_request = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "source_repo": old_source,
            "source_sha": identities["old_sha"],
            "target_identity": f"gate2-actor:{identities['old_sha']}:activation-only",
            "target_generation": f"g2-{identities['old_sha'][:10]}",
            "transaction_root": tmp_path / "old-source-tx",
        }
    )
    old_source_plan = promotion.plan_promotion(old_source_request)
    capacity_payload = json.loads(
        request.capacity_receipt_path.read_text(encoding="utf-8")
    )
    capacity_payload["authority_probe"] = "changed"
    changed_capacity = tmp_path / "changed-capacity-receipt.json"
    changed_capacity_digest = _write_json(changed_capacity, capacity_payload)
    capacity_request = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "capacity_receipt_path": changed_capacity,
            "capacity_receipt_digest": changed_capacity_digest,
            "transaction_root": tmp_path / "capacity-authority-tx",
        }
    )
    capacity_plan = promotion.plan_promotion(capacity_request)
    stage_probe = request.private_stage_root / "authority-probe.txt"
    stage_probe.write_text("stage authority changed\n", encoding="utf-8")
    stage_request = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "expected_current_stage_digest": promotion.tree_digest(
                request.private_stage_root
            ),
            "transaction_root": tmp_path / "stage-authority-tx",
        }
    )

    assert old_source_plan["plan_digest"] != baseline["plan_digest"]
    assert promotion.plan_promotion(stage_request)["plan_digest"] != baseline[
        "plan_digest"
    ]
    assert capacity_plan["plan_digest"] != baseline["plan_digest"]


def test_apply_revalidates_source_locator_when_plan_digest_is_stable(
    tmp_path: Path,
) -> None:
    request, identities = _runtime_fixture(tmp_path)
    before = _snapshot(request)
    plan = promotion.plan_promotion(request)
    wrong_source = tmp_path / "wrong-source"
    subprocess.run(
        ["git", "clone", "-q", request.expected_origin, str(wrong_source)],
        check=True,
    )
    _git(wrong_source, "checkout", "-q", "--detach", identities["old_sha"])
    _git(wrong_source, "remote", "set-url", "origin", request.expected_origin)
    wrong_locator = promotion.PromotionRequest(
        **{**request.__dict__, "source_repo": wrong_source}
    )

    with pytest.raises(promotion.PromotionError, match="source SHA drift"):
        promotion.apply_promotion(
            wrong_locator,
            expected_plan_digest=plan["plan_digest"],
        )

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


def test_plan_reconstructs_failed_legacy_identity_from_queue_owned_brief(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-failed-translation-run"
    run_dir = request.queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        _preserved_brief(
            run_id,
            mode="translate_existing",
            lane="i18n-new",
            article_ids=["SOURCE-ARTICLE-001"],
        ),
    )
    _write_json(
        request.queue_root / "runs" / "failed-legacy.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "failed",
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before_queue = promotion.tree_digest(request.queue_root)
    before = _snapshot(request)

    plan = promotion.plan_promotion(request)

    classification = plan["queue_identity_snapshot"]["preservation_classification"]
    assert plan["status"] == "READY_TO_APPLY"
    assert classification[run_id]["mode"] == "translate_existing"
    assert classification[run_id]["lane"] == "i18n-new"
    assert classification[run_id]["article_ids"] == ["SOURCE-ARTICLE-001"]
    assert classification[run_id]["identity_source"] == "terminal_brief_reconstruction"
    assert classification[run_id]["durable_root"] == str(
        request.queue_root / "translation-runs"
    )
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_keeps_active_legacy_missing_envelope_failed_closed(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-active-translation-run"
    run_dir = request.queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        _preserved_brief(
            run_id,
            mode="translate_existing",
            lane="i18n-new",
            article_ids=["SOURCE-ARTICLE-001"],
        ),
    )
    _write_json(
        request.queue_root / "runs" / "active-legacy.json",
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


def test_plan_accepts_legacy_translation_brief_missing_lane_with_matching_state_lane(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "auto-i18n-ja-4a9da72316d5d368eeb5"
    run_dir = request.queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        _preserved_brief(
            run_id,
            mode="translate_existing",
            article_ids=["ASTRO-BASE-01"],
        ),
    )
    _write_json(
        request.queue_root / "runs" / "legacy-translation.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "failed",
            "lane": "i18n-rewrite",
            "identity_envelope": _identity_envelope(
                ["ASTRO-BASE-01"],
                mode="translate_existing",
                lane="i18n-rewrite",
            ),
        },
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before_queue = promotion.tree_digest(request.queue_root)
    before = _snapshot(request)

    plan = promotion.plan_promotion(request)

    classification = plan["queue_identity_snapshot"]["preservation_classification"]
    assert plan["status"] == "READY_TO_APPLY"
    assert classification[run_id]["mode"] == "translate_existing"
    assert classification[run_id]["lane"] == "i18n-rewrite"
    assert classification[run_id]["article_ids"] == ["ASTRO-BASE-01"]
    assert classification[run_id]["identity_source"] == "current_identity_envelope"
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


@pytest.mark.parametrize("state_lane", [None, "i18n-new"])
def test_plan_rejects_legacy_translation_brief_missing_lane_without_matching_state_lane(
    tmp_path: Path,
    state_lane: str | None,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "auto-i18n-ja-4a9da72316d5d368eeb5"
    run_dir = request.queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        _preserved_brief(
            run_id,
            mode="translate_existing",
            article_ids=["ASTRO-BASE-01"],
        ),
    )
    state: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "failed",
        "identity_envelope": _identity_envelope(
            ["ASTRO-BASE-01"],
            mode="translate_existing",
            lane="i18n-rewrite",
        ),
    }
    if state_lane is not None:
        state["lane"] = state_lane
    _write_json(request.queue_root / "runs" / "legacy-translation.json", state)
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="brief identity mismatch"):
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


def test_plan_allows_ledger_terminal_history_without_execution_schema(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)

    active_id = "active-operational-run"
    active_dir = request.queue_root / "gsc-copy" / active_id
    active_dir.mkdir(parents=True)
    _write_json(active_dir / "brief.json", _preserved_brief(active_id))
    _write_preserved_state(
        request,
        "a-active.json",
        run_id=active_id,
        run_dir=active_dir,
        status="active",
        identity_envelope=_identity_envelope(),
    )

    published_id = "legacy-published-history"
    published_dir = request.queue_root / "gsc-copy" / published_id
    published_dir.mkdir(parents=True)
    _write_json(
        published_dir / "brief.json",
        _preserved_brief(published_id, article_ids=["PUBLISHED-HISTORY-001"]),
    )
    _write_json(
        request.queue_root / "runs" / "b-published.json",
        {
            "schema_version": 1,
            "run_id": published_id,
            "run_dir": str(published_dir),
            "status": "complete",
        },
    )

    superseded_id = "legacy-superseded-history"
    superseded_dir = request.queue_root.parent / "gsc-copy" / superseded_id
    superseded_dir.mkdir(parents=True)
    _write_json(
        superseded_dir / "brief.json",
        _preserved_brief(superseded_id, article_ids=["SUPERSEDED-HISTORY-001"]),
    )
    _write_json(
        request.queue_root / "runs" / "c-superseded.json",
        {
            "schema_version": 1,
            "run_id": superseded_id,
            "run_dir": str(superseded_dir),
            "status": "complete",
        },
    )

    released_id = "legacy-released-history"
    released_dir = request.queue_root.parent / "gsc-copy" / released_id
    released_dir.mkdir(parents=True)
    _write_json(
        released_dir / "brief.json",
        _preserved_brief(
            released_id,
            mode="rewrite_existing_body",
            article_ids=["RELEASED-HISTORY-001"],
        ),
    )
    _write_json(
        request.queue_root / "runs" / "d-released.json",
        {
            "schema_version": 1,
            "run_id": released_id,
            "run_dir": str(released_dir),
            "status": "complete",
        },
    )

    translation_id = "legacy-translation-history"
    translation_dir = request.queue_root / "translation-runs" / translation_id
    translation_dir.mkdir(parents=True)
    _write_json(
        translation_dir / "brief.json",
        _preserved_brief(
            translation_id,
            mode="translate_existing",
            lane="i18n-new",
            article_ids=["TRANSLATED-SOURCE-001"],
        ),
    )
    _write_json(
        request.queue_root / "runs" / "e-translation.json",
        {
            "schema_version": 1,
            "run_id": translation_id,
            "run_dir": str(translation_dir),
            "status": "complete",
        },
    )

    _write_json(
        request.publisher_state_root / "ledger.json",
        {
            "schema_version": 1,
            "published_runs": [
                {
                    "run_id": published_id,
                    "article_ids": ["PUBLISHED-HISTORY-001"],
                    "published_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "rewrite_released_runs": [
                {
                    "run_id": released_id,
                    "article_ids": ["RELEASED-HISTORY-001"],
                    "published_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "superseded_runs": [
                {
                    "run_id": superseded_id,
                    "article_ids": ["SUPERSEDED-HISTORY-001"],
                    "recorded_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "translation_published_runs": [
                {
                    "run_id": translation_id,
                    "article_ids": ["TRANSLATED-SOURCE-001"],
                    "published_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "quarantined_runs": [],
            "translation_deferred_runs": [],
        },
    )
    request = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "preserved_run_ids": tuple(
                sorted(
                    [
                        active_id,
                        published_id,
                        released_id,
                        superseded_id,
                        translation_id,
                    ]
                )
            ),
        }
    )
    before_queue = promotion.tree_digest(request.queue_root)
    before_ledger = promotion.file_sha256(request.publisher_state_root / "ledger.json")

    plan = promotion.plan_promotion(request)

    classification = plan["queue_identity_snapshot"]["preservation_classification"]
    assert plan["status"] == "READY_TO_APPLY"
    assert classification[published_id]["lifecycle"] == "published"
    assert classification[superseded_id]["lifecycle"] == "superseded_create"
    assert classification[released_id]["lifecycle"] == "released"
    assert classification[translation_id]["lifecycle"] == "published_translation"
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert promotion.file_sha256(request.publisher_state_root / "ledger.json") == before_ledger
    assert not request.transaction_root.exists()


def test_plan_allows_terminalized_dangling_active_history_without_execution_schema(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-terminalized-dangling-active"
    missing_run_dir = tmp_path / "retired-runtime" / "gsc-copy" / run_id
    _state_path, receipt_path = _write_dangling_active_terminalization(
        request,
        run_id=run_id,
        run_dir=missing_run_dir,
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before_queue = promotion.tree_digest(request.queue_root)
    before_receipt = promotion.file_sha256(receipt_path)

    plan = promotion.plan_promotion(request)

    classification = plan["queue_identity_snapshot"]["preservation_classification"]
    assert plan["status"] == "READY_TO_APPLY"
    assert classification[run_id]["lifecycle"] == "terminal_abandoned"
    assert classification[run_id]["mode"] == "terminal_abandoned"
    assert classification[run_id]["run_dir_exists"] is False
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert promotion.file_sha256(receipt_path) == before_receipt
    assert not request.transaction_root.exists()


@pytest.mark.parametrize(
    ("fixture_patch", "message"),
    [
        ({"write_receipt": False}, "terminalization receipt is missing"),
        (
            {"receipt_patch": {"run_id": "other-terminalized-run"}},
            "terminalization receipt identity mismatch",
        ),
        (
            {"receipt_patch": {"run_dir": "/tmp/other-missing-run"}},
            "terminalization receipt identity mismatch",
        ),
        (
            {"receipt_patch": {"before_digest": "b" * 64}},
            "terminalization receipt identity mismatch",
        ),
        (
            {"receipt_patch": {"after_digest": "c" * 64}},
            "terminalization receipt identity mismatch",
        ),
        (
            {
                "state_patch": {
                    "dangling_active_terminalization": {
                        "receipt": "../escape.json",
                        "reason": "UNRECOVERABLE_RUN_DIR_MISSING",
                        "before_digest": "d" * 64,
                    }
                }
            },
            "terminalization receipt identity mismatch",
        ),
    ],
)
def test_plan_rejects_invalid_terminalization_receipt_before_runtime_mutation(
    tmp_path: Path,
    fixture_patch: dict[str, object],
    message: str,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-terminalized-dangling-active"
    missing_run_dir = tmp_path / "retired-runtime" / "gsc-copy" / run_id
    _write_dangling_active_terminalization(
        request,
        run_id=run_id,
        run_dir=missing_run_dir,
        **fixture_patch,
    )
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match=message):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_symlinked_terminalization_receipt_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-terminalized-dangling-active"
    missing_run_dir = tmp_path / "retired-runtime" / "gsc-copy" / run_id
    _state_path, receipt_path = _write_dangling_active_terminalization(
        request,
        run_id=run_id,
        run_dir=missing_run_dir,
    )
    receipt_payload = receipt_path.read_text(encoding="utf-8")
    receipt_path.unlink()
    target = tmp_path / "receipt-target.json"
    target.write_text(receipt_payload, encoding="utf-8")
    receipt_path.symlink_to(target)
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match="terminalization receipt is invalid"):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_symlinked_terminalization_receipt_parent_before_runtime_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "legacy-terminalized-dangling-active"
    missing_run_dir = tmp_path / "retired-runtime" / "gsc-copy" / run_id
    _state_path, receipt_path = _write_dangling_active_terminalization(
        request,
        run_id=run_id,
        run_dir=missing_run_dir,
    )
    receipt_payload = receipt_path.read_text(encoding="utf-8")
    receipt_dir = receipt_path.parent
    receipt_path.unlink()
    receipt_dir.rmdir()
    external_dir = tmp_path / "external-terminalizations"
    external_dir.mkdir()
    (external_dir / f"{run_id}.json").write_text(receipt_payload, encoding="utf-8")
    receipt_dir.symlink_to(external_dir, target_is_directory=True)
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)
    receipt_reads: list[Path] = []
    original_read_json_file = promotion._read_json_file

    def tracking_read_json_file(path: Path, label: str) -> dict[str, Any]:
        if path == receipt_path:
            receipt_reads.append(path)
        return original_read_json_file(path, label)

    monkeypatch.setattr(promotion, "_read_json_file", tracking_read_json_file)

    with pytest.raises(promotion.PromotionError, match="terminalization receipt is invalid"):
        promotion.plan_promotion(request)

    assert receipt_reads == []
    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


def test_plan_rejects_unpublished_complete_candidate_without_identity_envelope(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "complete-unpublished-candidate"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "brief.json", _preserved_brief(run_id))
    _write_json(
        request.queue_root / "runs" / "candidate.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "complete",
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


def test_plan_classifies_preserved_lifecycle_contract_before_runtime_mutation(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)

    translation_id = "a-durable-translation-run"
    translation_dir = request.queue_root / "translation-runs" / translation_id
    translation_dir.mkdir(parents=True)
    _write_json(
        translation_dir / "brief.json",
        _preserved_brief(
            translation_id,
            mode="translate_existing",
            lane="i18n-new",
            article_ids=["V2-SOURCE-001"],
        ),
    )
    _write_preserved_state(
        request,
        "a-translation.json",
        run_id=translation_id,
        run_dir=translation_dir,
        status="complete",
        identity_envelope=_identity_envelope(
            ["V2-SOURCE-001"],
            mode="translate_existing",
            lane="i18n-new",
        ),
    )

    tombstone_id = "b-terminal-failed-tombstone"
    missing_tombstone_dir = tmp_path / "retired-runtime" / "gsc-copy" / tombstone_id
    _write_preserved_state(
        request,
        "b-tombstone.json",
        run_id=tombstone_id,
        run_dir=missing_tombstone_dir,
        status="failed",
        identity_envelope=_identity_envelope(["FAILED-001"]),
    )

    superseded_id = "c-superseded-create"
    superseded_dir = request.queue_root.parent / "gsc-copy" / superseded_id
    superseded_dir.mkdir(parents=True)
    _write_json(
        superseded_dir / "brief.json",
        _preserved_brief(superseded_id, article_ids=["SUPERSEDED-001"]),
    )
    _write_preserved_state(
        request,
        "c-superseded.json",
        run_id=superseded_id,
        run_dir=superseded_dir,
        status="complete",
        identity_envelope=_identity_envelope(["SUPERSEDED-001"]),
    )

    published_id = "d-published-create"
    published_dir = request.queue_root / "gsc-copy" / published_id
    published_dir.mkdir(parents=True)
    _write_json(
        published_dir / "brief.json",
        _preserved_brief(published_id, article_ids=["PUBLISHED-001"]),
    )
    _write_preserved_state(
        request,
        "d-published.json",
        run_id=published_id,
        run_dir=published_dir,
        status="complete",
        identity_envelope=_identity_envelope(["PUBLISHED-001"]),
    )

    released_id = "e-released-rewrite"
    released_dir = request.queue_root.parent / "gsc-copy" / released_id
    released_dir.mkdir(parents=True)
    _write_json(
        released_dir / "brief.json",
        _preserved_brief(
            released_id,
            mode="rewrite_existing_body",
            lane="rewrite",
            article_ids=["ASTRO-BASE-01"],
        ),
    )
    _write_preserved_state(
        request,
        "e-released.json",
        run_id=released_id,
        run_dir=released_dir,
        status="complete",
        identity_envelope=_identity_envelope(
            ["ASTRO-BASE-01"],
            mode="rewrite_existing_body",
            lane="rewrite",
        ),
    )
    _write_json(
        request.publisher_state_root / "ledger.json",
        {
            "schema_version": 1,
            "published_runs": [
                {
                    "run_id": published_id,
                    "article_ids": ["PUBLISHED-001"],
                    "published_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "rewrite_released_runs": [
                {
                    "run_id": released_id,
                    "article_ids": ["ASTRO-BASE-01"],
                    "published_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "superseded_runs": [
                {
                    "run_id": superseded_id,
                    "article_ids": ["SUPERSEDED-001"],
                    "recorded_at": "2026-08-26T00:00:00+00:00",
                }
            ],
            "translation_published_runs": [],
            "quarantined_runs": [],
            "translation_deferred_runs": [],
        },
    )
    request = promotion.PromotionRequest(
        **{
            **request.__dict__,
            "preserved_run_ids": tuple(
                sorted(
                    [
                        translation_id,
                        tombstone_id,
                        superseded_id,
                        published_id,
                        released_id,
                    ]
                )
            ),
        }
    )
    before = _snapshot(request)

    plan = promotion.plan_promotion(request)

    classification = plan["queue_identity_snapshot"]["preservation_classification"]
    assert classification[translation_id]["lifecycle"] == "durable_translation"
    assert classification[translation_id]["durable_root"] == str(request.queue_root / "translation-runs")
    assert classification[tombstone_id]["lifecycle"] == "terminal_failed_tombstone"
    assert classification[tombstone_id]["run_dir_exists"] is False
    assert classification[superseded_id]["lifecycle"] == "superseded_create"
    assert classification[superseded_id]["mode"] == "create"
    assert classification[published_id]["lifecycle"] == "published"
    assert classification[released_id]["lifecycle"] == "released"
    assert all(item["operational_selection"] is False for item in classification.values())
    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


@pytest.mark.parametrize(
    ("ledger_patch", "message"),
    [
        (
            {"published_runs": [{"run_id": "published-create", "article_ids": "PUBLISHED-001"}]},
            "publisher ledger identity mismatch",
        ),
        (
            {
                "published_runs": [{"run_id": "published-create", "article_ids": ["PUBLISHED-001"]}],
                "superseded_runs": [{"run_id": "published-create", "article_ids": ["PUBLISHED-001"]}],
            },
            "publisher ledger lifecycle conflict",
        ),
        (
            {"superseded_runs": [{"run_id": "published-create", "article_ids": ["OTHER-001"]}]},
            "publisher ledger identity mismatch",
        ),
    ],
)
def test_plan_rejects_invalid_lifecycle_ledger_before_runtime_mutation(
    tmp_path: Path,
    ledger_patch: dict[str, object],
    message: str,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "published-create"
    run_dir = request.queue_root / "gsc-copy" / run_id
    run_dir.mkdir(parents=True)
    _write_json(
        run_dir / "brief.json",
        _preserved_brief(run_id, article_ids=["PUBLISHED-001"]),
    )
    _write_preserved_state(
        request,
        "published.json",
        run_id=run_id,
        run_dir=run_dir,
        status="complete",
        identity_envelope=_identity_envelope(["PUBLISHED-001"]),
    )
    ledger = {
        "schema_version": 1,
        "published_runs": [],
        "rewrite_released_runs": [],
        "translation_published_runs": [],
        "superseded_runs": [],
        "quarantined_runs": [],
        "translation_deferred_runs": [],
    }
    ledger.update(ledger_patch)
    _write_json(request.publisher_state_root / "ledger.json", ledger)
    request = promotion.PromotionRequest(
        **{**request.__dict__, "preserved_run_ids": (run_id,)}
    )
    before = _snapshot(request)

    with pytest.raises(promotion.PromotionError, match=message):
        promotion.plan_promotion(request)

    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


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


def test_plan_accepts_gsc_copy_json_array_without_rewriting_bytes(
    tmp_path: Path,
) -> None:
    request, _identities = _runtime_fixture(tmp_path)
    run_id = "failed-reviewer-run"
    gsc_copy_run = request.queue_root / "gsc-copy" / run_id
    review_dir = gsc_copy_run / "editorial-review"
    review_dir.mkdir(parents=True)
    _write_json(
        gsc_copy_run / "brief.json",
        _preserved_brief(run_id),
    )
    findings_path = review_dir / "deterministic-findings.json"
    findings_path.write_text("[]\n", encoding="utf-8")
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
    before = _snapshot(request)
    before_findings = findings_path.read_bytes()

    plan = promotion.plan_promotion(request)

    assert plan["status"] == "READY_TO_APPLY"
    assert {
        entry["path"]
        for entry in plan["queue_identity_snapshot"]["gsc_copy"]
        if entry["type"] == "file"
    } == {
        f"{run_id}/brief.json",
        f"{run_id}/editorial-review/deterministic-findings.json",
    }
    assert findings_path.read_bytes() == before_findings
    assert promotion.tree_digest(request.queue_root) == before_queue
    assert not request.transaction_root.exists()
    assert _snapshot(request) == before


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
        ("noncanonical", "capacity receipt path must use canonical realpath"),
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
    elif mutation == "noncanonical":
        link = tmp_path / "capacity-receipt-link.json"
        link.symlink_to(request.capacity_receipt_path)
        request = promotion.PromotionRequest(
            **{**request.__dict__, "capacity_receipt_path": link}
        )
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

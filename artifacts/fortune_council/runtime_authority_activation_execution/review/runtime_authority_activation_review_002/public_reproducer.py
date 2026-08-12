#!/usr/bin/env python3
"""Public reproducers for Runtime Authority Activation Repair-1 re-review."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable

from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import pantheon_content_runtime_manifest as runtime
from scripts import pantheon_runtime_activation as activation


RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": "a" * 64,
}


def tree_snapshot(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        stat_result = path.lstat()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "mode": stat_result.st_mode,
                "size": stat_result.st_size,
                "symlink": str(path.readlink()) if path.is_symlink() else None,
            }
        )
    return entries


def build_manifest(tmp_path: Path, *, generation: str) -> tuple[Path, dict[str, Any], Path, Path, Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical_tmp = tmp_path.resolve(strict=True)
    actor = canonical_tmp / "actor"
    queue = canonical_tmp / "queue"
    state = canonical_tmp / "state"
    logs = canonical_tmp / "logs"
    ready = canonical_tmp / "ready"
    for path in (actor, queue, state, logs, ready):
        path.mkdir(parents=True, exist_ok=True)
    manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity=f"review-002:{generation}",
        runtime_digest=("a" * 64),
        config_version="review-002",
        generation=generation,
    )
    manifest_path = canonical_tmp / "manifest.json"
    runtime.write_manifest(manifest_path, manifest)
    return manifest_path, manifest, actor, queue, state, logs, ready


def with_env(values: dict[str, str], action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        return action()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def formal_env(
    manifest_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    *,
    token_path: Path | None,
) -> dict[str, str]:
    values = {
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": service_label,
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest["publisher_state_root"],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
    }
    if token_path is not None:
        values["PANTHEON_RUNTIME_ACTIVATION_TOKEN"] = str(token_path)
    return values


def missing_token_reproducer(tmp_path: Path) -> dict[str, Any]:
    manifest_path, manifest, actor, queue, _state, _logs, ready = build_manifest(
        tmp_path / "missing-token",
        generation="generation-missing-token",
    )
    for label in runtime.SERVICE_LABELS:
        runtime.write_readiness_ack(ready, manifest, label)
    run_dir = tmp_path / "missing-token-run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(
        '{"schema_version":1,"run_id":"missing-token-run","mode":"create","articles":[]}\n',
        encoding="utf-8",
    )
    before = tree_snapshot(queue)

    def action() -> dict[str, Any]:
        previous_cwd = Path.cwd()
        try:
            os.chdir(actor)
            coordinator.register_run(run_dir, queue)
            status = "UNEXPECTED_PASS"
            error = None
        except Exception as exc:  # public reproducer records the fail-closed class.
            status = "BLOCKED"
            error = f"{type(exc).__name__}: {exc}"
        finally:
            os.chdir(previous_cwd)
        after = tree_snapshot(queue)
        return {
            "status": status,
            "error": error,
            "io_count": len(after) - len(before),
            "queue_before": before,
            "queue_after": after,
        }

    return with_env(
        formal_env(
            manifest_path,
            manifest,
            "com.pantheon.agy-gemini-coordinator",
            token_path=None,
        ),
        action,
    )


def six_of_seven_reproducer(tmp_path: Path) -> dict[str, Any]:
    _manifest_path, manifest, actor, queue, state, logs, ready = build_manifest(
        tmp_path / "six-of-seven",
        generation="generation-six-of-seven",
    )
    token_path = tmp_path / "six-of-seven" / "activation.token"
    for label in runtime.SERVICE_LABELS[:-1]:
        runtime.write_readiness_ack(ready, manifest, label)
    calls: list[str] = []
    before = tree_snapshot(queue)
    publish_error = None
    operation_error = None
    try:
        activation.publish_generation_token(
            token_path,
            ready,
            manifest,
            correlation_id="review-002-six-of-seven",
        )
    except Exception as exc:
        publish_error = f"{type(exc).__name__}: {exc}"
    try:
        activation.run_after_activation_token(
            token_path,
            manifest,
            runtime.SERVICE_LABELS[0],
            queue_root=queue,
            state_root=state,
            actor_root=actor,
            log_root=logs,
            operation=lambda: calls.append("io"),
        )
    except Exception as exc:
        operation_error = f"{type(exc).__name__}: {exc}"
    after = tree_snapshot(queue)
    return {
        "status": "BLOCKED" if publish_error and operation_error and not calls else "UNEXPECTED_PASS",
        "publish_error": publish_error,
        "operation_error": operation_error,
        "io_count": len(calls) + len(after) - len(before),
        "token_exists": token_path.exists(),
        "queue_before": before,
        "queue_after": after,
    }


def stale_token_reproducer(tmp_path: Path) -> dict[str, Any]:
    _manifest_path, manifest, actor, queue, state, logs, ready = build_manifest(
        tmp_path / "stale-token",
        generation="generation-current",
    )
    stale_manifest = runtime.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="review-002:stale",
        runtime_digest=("b" * 64),
        config_version="review-002",
        generation="generation-stale",
    )
    token_path = tmp_path / "stale-token" / "activation.token"
    for label in runtime.SERVICE_LABELS:
        runtime.write_readiness_ack(ready, manifest, label)
    activation.publish_generation_token(
        token_path,
        ready,
        manifest,
        correlation_id="review-002-stale",
    )
    calls: list[str] = []
    before = tree_snapshot(queue)
    try:
        activation.run_after_activation_token(
            token_path,
            stale_manifest,
            runtime.SERVICE_LABELS[0],
            queue_root=queue,
            state_root=state,
            actor_root=actor,
            log_root=logs,
            operation=lambda: calls.append("io"),
        )
        status = "UNEXPECTED_PASS"
        error = None
    except Exception as exc:
        status = "BLOCKED"
        error = f"{type(exc).__name__}: {exc}"
    after = tree_snapshot(queue)
    return {
        "status": status,
        "error": error,
        "io_count": len(calls) + len(after) - len(before),
        "queue_before": before,
        "queue_after": after,
    }


def late_parent_swap_reproducer(tmp_path: Path) -> dict[str, Any]:
    case_root = tmp_path / "late-swap"
    case_root.mkdir(parents=True, exist_ok=True)
    case_root = case_root.resolve(strict=True)
    sandbox_root = case_root / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    displaced_root = case_root / "displaced-sandbox"
    external_root = case_root / "external"
    external_root.mkdir()
    (external_root / "publisher-state").mkdir()
    before = tree_snapshot(external_root)
    original = publisher._require_sandbox_descendant

    def swap_after_git_root_validation(
        trusted_root: Path,
        candidate: Path,
        label: str,
    ) -> Path:
        result = original(trusted_root, candidate, label)
        if label == "Git root":
            sandbox_root.rename(displaced_root)
            sandbox_root.symlink_to(external_root, target_is_directory=True)
        return result

    publisher._require_sandbox_descendant = swap_after_git_root_validation
    try:
        try:
            publisher.formal_capability_preflight(
                "transaction",
                run_ids=["run-a"],
                correlation_id="review-002-late-swap",
                trusted_sandbox_root=sandbox_root,
                queue_root=queue_root,
                state_root=state_root,
                runtime_receipt=RUNTIME_RECEIPT,
            )
            status = "UNEXPECTED_PASS"
            error = None
        except Exception as exc:
            status = "BLOCKED"
            error = f"{type(exc).__name__}: {exc}"
    finally:
        publisher._require_sandbox_descendant = original
    after = tree_snapshot(external_root)
    return {
        "status": status,
        "error": error,
        "external_tree_identical": after == before,
        "external_before": before,
        "external_after": after,
        "external_git_exists": (external_root / ".git").exists(),
        "external_lock_exists": (
            external_root / ".git" / "agy-content-publisher.lifecycle.lock"
        ).exists(),
    }


def post_lock_cleanup_swap_reproducer(tmp_path: Path) -> dict[str, Any]:
    case_root = tmp_path / "post-lock-cleanup-swap"
    case_root.mkdir(parents=True, exist_ok=True)
    case_root = case_root.resolve(strict=True)
    sandbox_root = case_root / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    displaced_root = case_root / "displaced-sandbox"
    external_root = case_root / "external"
    external_state = external_root / "publisher-state"
    external_stale = external_state / "transaction-escape"
    (external_stale / "repo").mkdir(parents=True)
    (external_stale / "repo" / "marker.txt").write_text("do-not-touch\n", encoding="utf-8")
    before = tree_snapshot(external_root)
    original_flock = publisher.fcntl.flock
    swapped = False

    def swap_after_lock_open(file_descriptor: int, flags: int) -> Any:
        nonlocal swapped
        if not swapped:
            swapped = True
            sandbox_root.rename(displaced_root)
            sandbox_root.symlink_to(external_root, target_is_directory=True)
        return original_flock(file_descriptor, flags)

    publisher.fcntl.flock = swap_after_lock_open
    try:
        try:
            publisher.formal_capability_preflight(
                "transaction",
                run_ids=["run-a"],
                correlation_id="review-002-post-lock-cleanup-swap",
                trusted_sandbox_root=sandbox_root,
                queue_root=queue_root,
                state_root=state_root,
                runtime_receipt=RUNTIME_RECEIPT,
            )
            status = "UNEXPECTED_PASS"
            error = None
        except Exception as exc:
            status = "BLOCKED"
            error = f"{type(exc).__name__}: {exc}"
    finally:
        publisher.fcntl.flock = original_flock
    after = tree_snapshot(external_root)
    return {
        "status": status,
        "error": error,
        "swapped": swapped,
        "external_tree_identical": after == before,
        "external_before": before,
        "external_after": after,
        "external_stale_exists": external_stale.exists(),
        "external_marker_exists": (external_stale / "repo" / "marker.txt").exists(),
    }


def unverified_identity_reproducer(tmp_path: Path) -> dict[str, Any]:
    case_root = tmp_path / "unverified-identity"
    case_root.mkdir(parents=True, exist_ok=True)
    case_root = case_root.resolve(strict=True)
    sandbox_root = case_root / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    before = tree_snapshot(sandbox_root)
    os.environ.pop("PANTHEON_RUNTIME_IDENTITY_DIGEST", None)
    try:
        publisher.formal_capability_preflight(
            "select",
            run_ids=["run-a"],
            correlation_id="review-002-unverified",
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
        )
        status = "UNEXPECTED_PASS"
        error = None
    except Exception as exc:
        status = "BLOCKED"
        error = f"{type(exc).__name__}: {exc}"
    after = tree_snapshot(sandbox_root)
    return {
        "status": status,
        "error": error,
        "io_count": len(after) - len(before),
        "tree_before": before,
        "tree_after": after,
    }


def verified_trace_reproducer(tmp_path: Path) -> dict[str, Any]:
    case_root = tmp_path / "verified-trace"
    case_root.mkdir(parents=True, exist_ok=True)
    case_root = case_root.resolve(strict=True)
    sandbox_root = case_root / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    for path in (queue_root, state_root):
        path.mkdir(parents=True)
    result = publisher.formal_capability_preflight(
        "transaction",
        run_ids=["run-a"],
        correlation_id="review-002-verified-trace",
        trusted_sandbox_root=sandbox_root,
        queue_root=queue_root,
        state_root=state_root,
        runtime_receipt=RUNTIME_RECEIPT,
    )
    digests = sorted(
        {
            event["runtime_identity_digest"]
            for event in result.get("operation_trace", [])
        }
    )
    return {
        "status": result["status"],
        "production_mutation": result["production_mutation"],
        "sandbox_mutation": result["sandbox_mutation"],
        "trace_digests": digests,
        "expected_digest": RUNTIME_RECEIPT["runtime_identity_digest"],
        "trace_uses_verified_digest": digests == [RUNTIME_RECEIPT["runtime_identity_digest"]],
    }


def run_all() -> dict[str, Any]:
    tmp_root = Path(tempfile.mkdtemp(prefix="pantheon-review-002-"))
    try:
        return {
            "missing_token": missing_token_reproducer(tmp_root),
            "six_of_seven": six_of_seven_reproducer(tmp_root),
            "stale_token": stale_token_reproducer(tmp_root),
            "late_parent_swap": late_parent_swap_reproducer(tmp_root),
            "post_lock_cleanup_swap": post_lock_cleanup_swap_reproducer(tmp_root),
            "unverified_identity": unverified_identity_reproducer(tmp_root),
            "verified_trace": verified_trace_reproducer(tmp_root),
        }
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def main() -> int:
    output = Path(os.environ.get("REPRODUCER_OUTPUT", "reproducer_output.json"))
    payload = run_all()
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

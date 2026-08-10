from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import subprocess

import pytest

from scripts import pantheon_content_capability_probe as probe
from scripts import pantheon_content_capability_adapter as adapter
from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_manifest as runtime_manifest


REGRESSION_ID = "REG-PANTHEON-READINESS-CORRELATED-CHAIN-001"
SOURCE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_RECEIPT = {
    "status": "PASS",
    "runtime_identity_digest": "b" * 64,
}


def _source_identity() -> tuple[str, str]:
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=SOURCE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return parent, probe.production_source_digest(SOURCE_ROOT)


def _tree_snapshot(root: Path) -> tuple[tuple[str, int, int, str | None], ...]:
    entries: list[tuple[str, int, int, str | None]] = []
    for path in root.rglob("*"):
        stat_result = path.lstat()
        entries.append(
            (
                path.relative_to(root).as_posix(),
                stat_result.st_mode,
                stat_result.st_size,
                str(path.readlink()) if path.is_symlink() else None,
            )
        )
    return tuple(sorted(entries))


def test_environment_roots_cannot_self_authorize_publisher_sandbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external_queue = tmp_path / "external-queue"
    external_state = tmp_path / "external-state"
    monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(external_queue))
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT",
        str(external_state),
    )
    before = _tree_snapshot(tmp_path)

    with pytest.raises(publisher.PublishBlocked, match="sandbox authority"):
        publisher.formal_capability_preflight(
            "publish",
            run_ids=["run-a"],
            correlation_id="correlation-a",
        )

    assert _tree_snapshot(tmp_path) == before
    assert not external_queue.exists()
    assert not external_state.exists()


@pytest.mark.parametrize(
    "case",
    [
        "external-queue",
        "external-state",
        "queue-symlink-escape",
        "state-symlink-escape",
        "sandbox-self",
        "sandbox-parent",
        "overlapping-roots",
    ],
)
def test_publisher_preflight_rejects_untrusted_roots_before_io(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    outside = tmp_path / "outside"
    if case == "external-queue":
        queue_root = tmp_path / "external-queue"
    elif case == "external-state":
        state_root = tmp_path / "external-state"
    elif case == "queue-symlink-escape":
        outside.mkdir()
        queue_root.symlink_to(outside, target_is_directory=True)
    elif case == "state-symlink-escape":
        outside.mkdir()
        state_root.symlink_to(outside, target_is_directory=True)
    elif case == "sandbox-self":
        queue_root = sandbox_root
    elif case == "sandbox-parent":
        queue_root = tmp_path
    elif case == "overlapping-roots":
        state_root = queue_root / "state"
    before = _tree_snapshot(tmp_path)
    events: list[str] = []

    def fail_if_called(*_args: object, **_kwargs: object) -> object:
        events.append("io")
        raise AssertionError("I/O must not start for an untrusted root")

    monkeypatch.setattr(publisher, "run_git", fail_if_called)

    with pytest.raises(publisher.PublishBlocked, match="root|overlap"):
        publisher.formal_capability_preflight(
            "publish",
            run_ids=["run-a"],
            correlation_id="correlation-a",
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            runtime_receipt=RUNTIME_RECEIPT,
        )

    assert events == []
    assert _tree_snapshot(tmp_path) == before


@pytest.mark.parametrize("external_field", ["queue_root", "publisher_state_root"])
def test_adapter_contract_blocks_external_runtime_roots_without_mutation(
    external_field: str,
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    log_root = sandbox_root / "logs"
    external_root = tmp_path / "external"
    for path in (sandbox_root, queue_root, state_root, log_root, external_root):
        path.mkdir(parents=True, exist_ok=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=SOURCE_ROOT,
        queue_root=external_root if external_field == "queue_root" else queue_root,
        publisher_state_root=(
            external_root
            if external_field == "publisher_state_root"
            else state_root
        ),
        log_root=log_root,
        identity="external-root-rejection",
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    ready_root = tmp_path / "ready"
    token_path = tmp_path / "activation.token"
    ready_root.mkdir()
    for service_label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready_root, manifest, service_label)
    runtime_manifest.activate_barrier(token_path, ready_root, manifest)
    source = {
        "runtime_manifest": str(manifest_path),
        "runtime_manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "sandbox_root": str(sandbox_root),
        "activation_token": str(token_path),
    }
    before = _tree_snapshot(tmp_path)

    with pytest.raises(adapter.AdapterBlocked, match="root"):
        adapter._load_contract(source)

    assert _tree_snapshot(tmp_path) == before
    assert external_root.is_dir()


def test_adapter_contract_requires_activation_token_before_create_io(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"
    log_root = sandbox_root / "logs"
    for path in (sandbox_root, queue_root, state_root, log_root):
        path.mkdir(parents=True, exist_ok=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=SOURCE_ROOT,
        queue_root=queue_root,
        publisher_state_root=state_root,
        log_root=log_root,
        identity="missing-adapter-token",
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    source = {
        "schema_version": 2,
        "capability": None,
        "execution_id": "missing-adapter-token",
        "correlation_id": "missing-adapter-token",
        "actor_identity": "missing-adapter-token",
        "runtime_manifest": str(manifest_path),
        "runtime_manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "generation": manifest["generation"],
        "sandbox_root": str(sandbox_root),
    }
    before = _tree_snapshot(sandbox_root)

    with pytest.raises(adapter.AdapterBlocked, match="activation token"):
        adapter._production_transition("create", source)

    assert _tree_snapshot(sandbox_root) == before
    assert not list((queue_root / "runs").glob("*.json"))


def test_dry_run_git_blocks_transaction_materialization_outside_sandbox(
    tmp_path: Path,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    external_transaction = tmp_path / "external" / "repo"
    before = _tree_snapshot(tmp_path)

    with pytest.raises(publisher.PublishBlocked, match="transaction root"):
        publisher._formal_capability_dry_run_git(
            SOURCE_ROOT,
            sandbox_root,
            "a" * 40,
            SOURCE_ROOT,
            [
                "worktree",
                "add",
                "--detach",
                str(external_transaction),
                "a" * 40,
            ],
        )

    assert _tree_snapshot(tmp_path) == before
    assert not external_transaction.exists()


def test_publisher_preflight_invokes_formal_publish_transaction_and_release_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, object]] = []
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    queue_root = sandbox_root / "queue"
    state_root = sandbox_root / "publisher-state"

    def fake_publish(
        repo_root: Path,
        queue_root: Path,
        state_root: Path,
        **kwargs: object,
    ) -> dict[str, object]:
        events.append(
            (
                "publish",
                {
                    "repo_root": repo_root,
                    "queue_root": queue_root,
                    "state_root": state_root,
                    **kwargs,
                },
            )
        )
        return {
            "status": "dry-run",
            "ready_runs": ["run-a"],
            "base_sha": "b" * 40,
        }

    @contextmanager
    def fake_transaction(
        repo_root: Path,
        state_root: Path,
        git: publisher.GitRunner,
        **kwargs: object,
    ):
        events.append(
            (
                "transaction",
                {"repo_root": repo_root, "state_root": state_root, "git": git, **kwargs},
            )
        )
        yield sandbox_root / "transaction"

    def fake_release(
        repo_root: Path,
        version: str,
        git: publisher.GitRunner,
        **kwargs: object,
    ) -> str:
        events.append(
            (
                "push" if kwargs["push"] else "tag",
                {"repo_root": repo_root, "version": version, "git": git, **kwargs},
            )
        )
        return "a" * 40

    monkeypatch.setattr(publisher, "publish_ready_runs", fake_publish)
    monkeypatch.setattr(publisher, "_isolated_transaction_worktree", fake_transaction)
    monkeypatch.setattr(publisher, "_stage_commit_tag_push", fake_release)

    results = [
        publisher.formal_capability_preflight(
            capability,
            run_ids=["run-a"],
            correlation_id="correlation-a",
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            runtime_receipt=RUNTIME_RECEIPT,
        )
        for capability in ("publish", "transaction", "tag", "push")
    ]

    assert [event[0] for event in events] == [
        "publish",
        "transaction",
        "tag",
        "push",
    ]
    publish_call = events[0][1]
    assert isinstance(publish_call, dict)
    assert publish_call["dry_run"] is True
    assert publish_call["exact_run_ids"] == ["run-a"]
    assert publish_call["seed_translations"] is False
    transaction_call = events[1][1]
    tag_call = events[2][1]
    push_call = events[3][1]
    assert isinstance(transaction_call, dict)
    assert isinstance(tag_call, dict)
    assert isinstance(push_call, dict)
    assert callable(transaction_call["git"])
    assert tag_call["version"] == push_call["version"] == "0.0.0"
    assert tag_call["push"] is False
    assert push_call["push"] is True
    assert tag_call["release_gate"] is push_call["release_gate"] is False
    assert callable(tag_call["checked_runner"])
    assert callable(push_call["checked_runner"])
    assert all(result["status"] == "PASS" for result in results)
    assert [result["boundary_status"] for result in results] == [
        "dry-run",
        "PASS",
        "PASS",
        "PASS",
    ]


def test_publisher_preflight_blocks_publish_return_without_runtime_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()
    monkeypatch.setattr(
        publisher,
        "publish_ready_runs",
        lambda *_args, **_kwargs: {"status": "idle", "published": 0},
    )

    with pytest.raises(publisher.PublishBlocked, match="runtime identity"):
        publisher.formal_capability_preflight(
            "publish",
            run_ids=["run-a"],
            correlation_id="correlation-a",
            trusted_sandbox_root=sandbox_root,
            queue_root=sandbox_root / "queue",
            state_root=sandbox_root / "publisher-state",
            runtime_receipt=RUNTIME_RECEIPT,
        )


@pytest.mark.parametrize(
    ("capability", "boundary_name"),
    [
        ("publish", "publish_ready_runs"),
        ("transaction", "_isolated_transaction_worktree"),
        ("tag", "_stage_commit_tag_push"),
        ("push", "_stage_commit_tag_push"),
    ],
)
def test_publisher_preflight_propagates_formal_boundary_rejection(
    capability: str,
    boundary_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir()

    @contextmanager
    def rejected_transaction(*_args: object, **_kwargs: object):
        events.append("transaction")
        raise publisher.PublishBlocked("formal boundary rejected")
        yield

    def rejected_boundary(*_args: object, **_kwargs: object) -> object:
        events.append(capability)
        raise publisher.PublishBlocked("formal boundary rejected")

    monkeypatch.setattr(
        publisher,
        boundary_name,
        rejected_transaction
        if capability == "transaction"
        else rejected_boundary,
    )

    with pytest.raises(publisher.PublishBlocked, match="formal boundary rejected"):
        publisher.formal_capability_preflight(
            capability,
            run_ids=["run-a"],
            correlation_id="correlation-a",
            trusted_sandbox_root=sandbox_root,
            queue_root=sandbox_root / "queue",
            state_root=sandbox_root / "publisher-state",
            runtime_receipt=RUNTIME_RECEIPT,
        )

    assert events == [capability]


def test_one_formal_probe_emits_machine_correlated_positive_chain(tmp_path: Path) -> None:
    parent_sha, source_digest = _source_identity()
    source_status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=SOURCE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    receipt = probe.run_probe(
        evidence_root=tmp_path / "positive",
        execution_id="synthetic-execution-001",
        correlation_id="synthetic-correlation-001",
        source_root=SOURCE_ROOT,
        parent_sha=parent_sha,
        source_tree_digest=source_digest,
    )

    assert receipt["status"] == "PASS"
    assert receipt["regression_id"] == REGRESSION_ID
    assert [step["capability"] for step in receipt["steps"]] == list(probe.CAPABILITIES)
    for previous, current in zip(receipt["steps"], receipt["steps"][1:]):
        assert current["input_digest"] == previous["output_digest"]
    for step in receipt["steps"]:
        artifact = json.loads(Path(step["artifact"]).read_text(encoding="utf-8"))
        assert artifact["execution_id"] == receipt["execution_id"]
        assert artifact["correlation_id"] == receipt["correlation_id"]
        assert artifact["entrypoint_outcome"] == "PASS"
        assert artifact["production_entrypoints"]
        assert artifact["return_code"] == 0
        assert artifact["runtime_identity_digest"] == receipt["runtime_identity_digest"]
        assert artifact["adapter_invocation"]["returncode"] == 0
        assert Path(artifact["adapter_invocation"]["receipt"]).is_file()
        assert artifact["adapter_invocation"]["boundary"].endswith(
            f":{artifact['capability']}"
        )
        if artifact["capability"] in {"select", "publish", "transaction", "tag", "push"}:
            adapter_artifact = json.loads(
                Path(artifact["adapter_invocation"]["receipt"]).read_text(
                    encoding="utf-8"
                )
            )
            publisher_result = adapter_artifact["publisher_result"]
            assert publisher_result["production_mutation"] is False
            assert isinstance(publisher_result["sandbox_mutation"], bool)
            assert (
                adapter_artifact["production_mutation"]
                is publisher_result["production_mutation"]
            )
            assert (
                adapter_artifact["sandbox_mutation"]
                is publisher_result["sandbox_mutation"]
            )
    assert probe.production_source_digest(SOURCE_ROOT) == source_digest
    assert subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=SOURCE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == source_status


def test_same_formal_probe_boundary_blocks_corrupted_handoff(tmp_path: Path) -> None:
    parent_sha, source_digest = _source_identity()
    receipt = probe.run_probe(
        evidence_root=tmp_path / "negative",
        execution_id="synthetic-execution-002",
        correlation_id="synthetic-correlation-002",
        source_root=SOURCE_ROOT,
        parent_sha=parent_sha,
        source_tree_digest=source_digest,
        fail_step="publish",
    )

    assert receipt["status"] == "BLOCKED"
    blocked = receipt["steps"][-1]
    assert blocked["capability"] == "publish"
    assert blocked["entrypoint_outcome"] == "BLOCKED"
    assert blocked["error"] == "input digest mismatch"
    assert not {"transaction", "tag", "push"}.intersection(
        step["capability"] for step in receipt["steps"]
    )


def test_replacing_formal_adapter_with_failing_implementation_blocks_chain(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-READINESS-CORRELATED-CHAIN-001 Repair-2。"""
    failing = tmp_path / "always-fail"
    failing.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
    failing.chmod(0o700)

    parent_sha, source_digest = _source_identity()
    receipt = probe.run_probe(
        evidence_root=tmp_path / "adapter-failure",
        execution_id="repair-2-failing-adapter",
        correlation_id="repair-2-failing-adapter",
        source_root=SOURCE_ROOT,
        parent_sha=parent_sha,
        source_tree_digest=source_digest,
        adapter_command=[str(failing)],
    )

    assert receipt["status"] == "BLOCKED"
    assert len(receipt["steps"]) == 1
    assert receipt["steps"][0]["adapter_invocation"]["returncode"] == 9
    assert receipt["steps"][0]["entrypoint_outcome"] == "BLOCKED"


def test_probe_rejects_caller_digest_that_does_not_match_production_sources(
    tmp_path: Path,
) -> None:
    parent_sha, _source_digest = _source_identity()

    with pytest.raises(ValueError, match="source tree digest differs"):
        probe.run_probe(
            evidence_root=tmp_path / "digest-mismatch",
            execution_id="source-digest-mismatch",
            correlation_id="source-digest-mismatch",
            source_root=SOURCE_ROOT,
            parent_sha=parent_sha,
            source_tree_digest="f" * 64,
        )

    assert not (tmp_path / "digest-mismatch").exists()


@pytest.mark.parametrize("capability", probe.CAPABILITIES)
def test_thin_adapter_never_converts_production_boundary_failure_to_pass(
    tmp_path: Path,
    capability: str,
) -> None:
    source = {
        "schema_version": 2,
        "capability": adapter.PREVIOUS[capability],
        "execution_id": "boundary-failure",
        "correlation_id": "boundary-failure",
        "actor_identity": "boundary-failure",
    }
    source["output_digest"] = adapter._digest(source)
    input_path = tmp_path / f"{capability}-input.json"
    output_path = tmp_path / f"{capability}-output.json"
    input_path.write_text(json.dumps(source), encoding="utf-8")

    def fail_boundary(_capability: str, _source: dict[str, object]) -> dict[str, object]:
        raise adapter.AdapterBlocked("production boundary failed")

    with pytest.raises(adapter.AdapterBlocked, match="production boundary failed"):
        adapter.invoke(
            capability=capability,
            input_path=input_path,
            output_path=output_path,
            expected_input_digest=source["output_digest"],
            actual_input_digest=source["output_digest"],
            execution_id="boundary-failure",
            correlation_id="boundary-failure",
            actor_identity="boundary-failure",
            transition=fail_boundary,
        )

    assert not output_path.exists()

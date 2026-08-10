from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import subprocess

import pytest

from scripts import pantheon_content_capability_probe as probe
from scripts import pantheon_content_capability_adapter as adapter
from scripts import agy_content_publisher as publisher


REGRESSION_ID = "REG-PANTHEON-READINESS-CORRELATED-CHAIN-001"
SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _source_identity() -> tuple[str, str]:
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=SOURCE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return parent, probe.production_source_digest(SOURCE_ROOT)


def test_publisher_preflight_invokes_formal_publish_transaction_and_release_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, object]] = []

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
    ):
        events.append(
            (
                "transaction",
                {"repo_root": repo_root, "state_root": state_root, "git": git},
            )
        )
        yield tmp_path / "transaction"

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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

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

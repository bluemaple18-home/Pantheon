from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts import pantheon_content_capability_probe as probe
from scripts import pantheon_content_capability_adapter as adapter


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


def test_one_formal_probe_emits_machine_correlated_positive_chain(tmp_path: Path) -> None:
    parent_sha, source_digest = _source_identity()
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

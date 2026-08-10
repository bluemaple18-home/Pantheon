from __future__ import annotations

import json
from pathlib import Path

from scripts import pantheon_content_capability_probe as probe


REGRESSION_ID = "REG-PANTHEON-READINESS-CORRELATED-CHAIN-001"


def test_one_formal_probe_emits_machine_correlated_positive_chain(tmp_path: Path) -> None:
    receipt = probe.run_probe(
        evidence_root=tmp_path / "positive",
        execution_id="synthetic-execution-001",
        correlation_id="synthetic-correlation-001",
        parent_sha="a" * 40,
        source_tree_digest="b" * 64,
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
        assert artifact["adapter_invocation"]["returncode"] == 0
        assert Path(artifact["adapter_invocation"]["receipt"]).is_file()
        assert artifact["adapter_invocation"]["boundary"].endswith(
            f":{artifact['capability']}"
        )


def test_same_formal_probe_boundary_blocks_corrupted_handoff(tmp_path: Path) -> None:
    receipt = probe.run_probe(
        evidence_root=tmp_path / "negative",
        execution_id="synthetic-execution-002",
        correlation_id="synthetic-correlation-002",
        parent_sha="a" * 40,
        source_tree_digest="b" * 64,
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

    receipt = probe.run_probe(
        evidence_root=tmp_path / "adapter-failure",
        execution_id="repair-2-failing-adapter",
        correlation_id="repair-2-failing-adapter",
        parent_sha="a" * 40,
        source_tree_digest="b" * 64,
        adapter_command=[str(failing)],
    )

    assert receipt["status"] == "BLOCKED"
    assert len(receipt["steps"]) == 1
    assert receipt["steps"][0]["adapter_invocation"]["returncode"] == 9
    assert receipt["steps"][0]["entrypoint_outcome"] == "BLOCKED"

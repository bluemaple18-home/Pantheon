from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_v4_architecture_probe as probe


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def matrix() -> dict[str, object]:
    return probe.build_matrix()


def _cell(matrix: dict[str, object], scenario: str, option: str = "B") -> dict[str, str]:
    return next(row for row in matrix["matrix"] if row["scenario"] == scenario)[option]


def test_real_broker_separates_preflight_exec_and_confirmed_processes(tmp_path: Path) -> None:
    preflight = probe._run_broker(tmp_path / "preflight", "preflight_missing")
    exec_race = probe._run_broker(tmp_path / "race", "exec_race", race_unlink=True)
    assert preflight["status"] == "COMPLETE"
    assert preflight["gemini_process_count"] == 0
    assert exec_race["status"] == "BLOCKED"
    assert exec_race["gemini_process_count"] == 0
    assert exec_race["outcome"] == "EXEC_RACE"
    assert (tmp_path / "preflight/ledger.jsonl").read_bytes() != (tmp_path / "race/ledger.jsonl").read_bytes()

    for mode, outcome in (("success", "SUCCESS"), ("nonzero", "CLI_NONZERO"), ("timeout", "CLI_TIMEOUT")):
        result = probe._run_broker(tmp_path / mode, mode)
        assert result["status"] == "COMPLETE"
        assert result["gemini_process_count"] == 1
        assert result["outcome"] == outcome
        assert result["actual_target_marker"] is True
        assert result["automatic_resend_allowed"] is False


def test_broker_crash_windows_are_zero_only_with_evidence_or_unknown(tmp_path: Path) -> None:
    durable_zero = probe._run_broker(tmp_path / "zero", "success", crash="before_fork_durable")
    before_exec = probe._run_broker(tmp_path / "before-exec", "success", crash="before_exec")
    orphan = probe._run_broker(tmp_path / "orphan", "success", crash="after_exec_before_event")
    assert (durable_zero["status"], durable_zero["gemini_process_count"]) == ("BLOCKED", 0)
    assert (before_exec["status"], before_exec["gemini_process_count"]) == ("AMBIGUOUS", "UNKNOWN")
    assert before_exec["actual_target_marker"] is False
    assert (orphan["status"], orphan["gemini_process_count"]) == ("AMBIGUOUS", "UNKNOWN")
    assert orphan["actual_target_marker"] is True
    assert before_exec["automatic_resend_allowed"] is False
    assert orphan["automatic_resend_allowed"] is False


def test_target_fd_table_and_negative_policies_are_observed_by_real_broker(matrix: dict[str, object]) -> None:
    fd = matrix["runtime_evidence"]["option_b_inherited_fd"]
    assert fd["broker_received_fd"] is True
    assert fd["target_fd_table"] == [0, 1, 2]
    assert fd["gemini_child_fd_closed"] is True
    assert fd["token_file_present"] is False
    assert fd["negative_wrong_close_fds_detected"] is True
    assert fd["negative_wrong_pass_fds_detected"] is True
    assert fd["negative_extra_fd_detected"] is True


def test_strict_replay_rejects_illegal_schema_order_binding_and_frames(tmp_path: Path) -> None:
    binding = probe.Binding("op", "item", "attempt-1")
    valid = probe.Ledger(tmp_path / "valid.jsonl", binding)
    valid.append("OPERATION_CREATED")
    valid.append("BROKER_ATTEMPTED", broker_attempt=1)
    valid.append("FORK_ATTEMPTED", broker_attempt=1, process_ordinal=1)
    valid.append("EXEC_CONFIRMED", process_ordinal=1, pid=123)
    valid.append("PROCESS_TERMINAL", outcome="SUCCESS")
    assert probe.replay(valid.path, binding, valid.anchor)["status"] == "COMPLETE"

    terminal_first = probe.Ledger(tmp_path / "terminal-first.jsonl", binding)
    terminal_first.append("OPERATION_CREATED")
    terminal_first.append("BROKER_ATTEMPTED", broker_attempt=1)
    terminal_first.append("PROCESS_TERMINAL", outcome="SUCCESS")
    terminal_first.append("PROCESS_STARTED", process_ordinal=1)
    duplicate = probe.Ledger(tmp_path / "duplicate.jsonl", binding)
    duplicate.append("OPERATION_CREATED")
    duplicate.append("OPERATION_CREATED")
    bad_ordinal = probe.Ledger(tmp_path / "ordinal.jsonl", binding)
    bad_ordinal.append("OPERATION_CREATED")
    bad_ordinal.append("BROKER_ATTEMPTED", broker_attempt=1)
    bad_ordinal.append("PROCESS_STARTED", process_ordinal=99)
    bad_ordinal.append("PROCESS_TERMINAL", outcome="NOT_ALLOWED")
    unknown_field = probe.Ledger(tmp_path / "unknown.jsonl", binding)
    unknown_field.append("OPERATION_CREATED", surprise=True)
    truncated = tmp_path / "truncated.jsonl"
    truncated.write_bytes(valid.path.read_bytes() + b'{"event_type":')
    for path, anchor in (
        (terminal_first.path, terminal_first.anchor),
        (duplicate.path, duplicate.anchor),
        (bad_ordinal.path, bad_ordinal.anchor),
        (unknown_field.path, unknown_field.anchor),
        (truncated, valid.anchor),
    ):
        result = probe.replay(path, binding, anchor)
        assert result["status"] == "INVALID"
        assert result["gemini_process_count"] == "UNKNOWN"
    assert probe.replay(valid.path, probe.Binding("other", "item", "attempt-1"), valid.anchor)["status"] == "INVALID"


def test_current_v2_replay_contract_covers_terminal_loss_legacy_aliases_and_pid_domain(tmp_path: Path) -> None:
    binding = probe.Binding("op-contract", "item-contract", "attempt-1")

    def replay_events(name: str, events: list[tuple[str, dict[str, object]]]) -> dict[str, object]:
        ledger = probe.Ledger(tmp_path / f"{name}.jsonl", binding)
        for event_type, fields in events:
            ledger.append(event_type, **fields)
        return probe.replay(ledger.path, binding, ledger.anchor)

    prefix = [
        ("OPERATION_CREATED", {}),
        ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
    ]
    terminal_loss = replay_events(
        "terminal-loss",
        prefix + [("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4321})],
    )
    assert terminal_loss == {
        "status": "BLOCKED",
        "complete": False,
        "errors": ["PROCESS_TERMINAL_MISSING"],
        "logical_operations": 1,
        "broker_attempts": 1,
        "gemini_process_count": 1,
        "gemini_process_starts": 1,
        "provider_internal_calls": "UNKNOWN",
        "automatic_resend_allowed": False,
    }

    legacy_zero = replay_events(
        "legacy-zero",
        [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("PROCESS_NOT_STARTED", {"outcome": "CLI_NOT_FOUND"}),
        ],
    )
    legacy_one = replay_events(
        "legacy-one",
        [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("PROCESS_STARTED", {"process_ordinal": 1, "pid": 4321}),
            ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
        ],
    )
    assert legacy_zero["status"] == legacy_one["status"] == "INVALID"
    assert legacy_zero["complete"] is legacy_one["complete"] is False

    for index, pid in enumerate((None, 0, -1, True, "4321")):
        fields = {"process_ordinal": 1}
        if pid is not None:
            fields["pid"] = pid
        result = replay_events(
            f"bad-pid-{index}",
            prefix
            + [
                ("EXEC_CONFIRMED", fields),
                ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
            ],
        )
        assert result["status"] == "INVALID"
        assert result["gemini_process_count"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("corrupt_path", "corrupt_result"),
    (
        ("legal-blocked-one.jsonl", {"status": "INVALID", "gemini_process_count": "UNKNOWN"}),
        ("legacy-not-started.jsonl", {"status": "COMPLETE", "gemini_process_count": 0}),
        ("pid-0.jsonl", {"status": "COMPLETE", "gemini_process_count": 1}),
    ),
)
def test_strict_replay_matrix_uses_full_contract_and_real_negative_controls(
    matrix: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    corrupt_path: str,
    corrupt_result: dict[str, object],
) -> None:
    integrity = matrix["runtime_evidence"]["integrity_and_anchor"]
    assert integrity["legal_state_table_valid"] is True
    assert integrity["terminal_loss_classified"] is True
    assert integrity["legacy_aliases_rejected"] is True
    assert integrity["pid_domain_rejected"] is True
    assert integrity["illegal_order_detected"] is True
    assert integrity["partial_detected"] is True
    assert integrity["wrong_binding_detected"] is True
    assert integrity["chain_mismatch_detected"] is True
    assert matrix["runtime_evidence"]["observables"]["strict_replay"] is True

    original_replay = probe.replay

    def corrupt_required_control(path: Path, expected: probe.Binding, external_anchor: str | None) -> dict[str, object]:
        result = original_replay(path, expected, external_anchor)
        if path.name == corrupt_path:
            return {**result, **corrupt_result}
        return result

    monkeypatch.setattr(probe, "replay", corrupt_required_control)
    degraded = probe.build_matrix()
    assert degraded["runtime_evidence"]["observables"]["strict_replay"] is False
    assert _cell(degraded, "illegal_or_partial_replay")["status"] == "UNSUPPORTED"


def test_external_anchor_boundary_never_claims_same_domain_full_replacement_detected(matrix: dict[str, object]) -> None:
    integrity = matrix["runtime_evidence"]["integrity_and_anchor"]
    assert integrity["same_trust_domain_full_replacement"] == "OUT_OF_SCOPE"
    assert integrity["old_anchor_detects_replacement"] is True
    assert integrity["ledger_does_not_self_prove_anchor"] is True
    assert _cell(matrix, "same_uid_full_replacement")["status"] == "OUT_OF_SCOPE"


def test_matrix_cells_are_runtime_linked_and_negative_control_downgrades(matrix: dict[str, object]) -> None:
    for row in matrix["matrix"]:
        for option in ("A", "B", "C"):
            cell = row[option]
            assert cell["status"] in probe.STATUSES
            assert cell["observable"] == cell["observable_id"]
            assert cell["predicate"]
    assert _cell(matrix, "target_fd_isolation")["status"] == "PREVENTED"
    mutated = probe.build_matrix({"fd_policy_correct": False})
    assert _cell(mutated, "target_fd_isolation")["status"] == "UNSUPPORTED"
    assert _cell(mutated, "fd_negative_controls")["status"] == "UNSUPPORTED"


def test_cli_is_byte_identical_private_and_candidate_is_review_only() -> None:
    command = [sys.executable, "scripts/agy_gemini_v4_architecture_probe.py"]
    first = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, check=True, text=True)
    second = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, check=True, text=True)
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload["candidate_status"] == "READY_FOR_REVIEW"
    assert payload["provider_internal_calls"] == "UNKNOWN"
    forbidden = (
        "/" + "Users" + "/",
        "/" + "private" + "/",
        "owner-token",
        "API" + "_KEY",
        "stdout_raw",
        "stderr_raw",
        "[" + "DBG" + "-",
    )
    assert not any(value in first.stdout for value in forbidden)

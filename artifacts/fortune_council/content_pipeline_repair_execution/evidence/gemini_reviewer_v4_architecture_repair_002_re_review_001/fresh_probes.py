from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agy_gemini_v4_architecture_probe as candidate


def _write_events(
    root: Path,
    name: str,
    binding: candidate.Binding,
    events: list[tuple[str, dict[str, object]]],
) -> dict[str, object]:
    ledger = candidate.Ledger(root / f"{name}.jsonl", binding)
    for event_type, fields in events:
        ledger.append(event_type, **fields)
    return candidate.replay(ledger.path, binding, ledger.anchor)


def _cell(matrix: dict[str, object]) -> str:
    row = next(
        item for item in matrix["matrix"]
        if item["scenario"] == "illegal_or_partial_replay"
    )
    return row["B"]["status"]


def replay_contract(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    binding = candidate.Binding("review-op", "review-item", "attempt-1")
    prefix = [
        ("OPERATION_CREATED", {}),
        ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
    ]
    terminal_loss = _write_events(
        root, "terminal-loss", binding,
        prefix + [("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4321})],
    )
    legacy = {
        "PROCESS_NOT_STARTED": _write_events(
            root, "legacy-not-started", binding,
            [
                ("OPERATION_CREATED", {}),
                ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
                ("PROCESS_NOT_STARTED", {"outcome": "CLI_NOT_FOUND"}),
            ],
        ),
        "PROCESS_STARTED": _write_events(
            root, "legacy-started", binding,
            [
                ("OPERATION_CREATED", {}),
                ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
                ("PROCESS_STARTED", {"process_ordinal": 1, "pid": 4321}),
                ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
            ],
        ),
    }
    invalid_pids: list[tuple[str, object]] = [
        ("missing", None),
        ("zero", 0),
        ("negative", -1),
        ("bool", True),
        ("string", "4321"),
    ]
    pid_results: dict[str, dict[str, object]] = {}
    for name, pid in invalid_pids:
        fields: dict[str, object] = {"process_ordinal": 1}
        if name != "missing":
            fields["pid"] = pid
        pid_results[name] = _write_events(
            root, f"pid-{name}", binding,
            prefix + [
                ("EXEC_CONFIRMED", fields),
                ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
            ],
        )
    positive = _write_events(
        root, "pid-positive", binding,
        prefix + [
            ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4321}),
            ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
        ],
    )
    return {
        "terminal_loss": terminal_loss,
        "terminal_loss_contract_pass": terminal_loss == {
            "status": "BLOCKED",
            "complete": False,
            "errors": ["PROCESS_TERMINAL_MISSING"],
            "logical_operations": 1,
            "broker_attempts": 1,
            "gemini_process_count": 1,
            "gemini_process_starts": 1,
            "provider_internal_calls": "UNKNOWN",
            "automatic_resend_allowed": False,
        },
        "legacy": legacy,
        "legacy_contract_pass": all(
            result["status"] == "INVALID"
            and result["gemini_process_count"] == "UNKNOWN"
            and result["complete"] is False
            for result in legacy.values()
        ),
        "invalid_pid": pid_results,
        "invalid_pid_contract_pass": all(
            result["status"] == "INVALID"
            and result["gemini_process_count"] == "UNKNOWN"
            and result["complete"] is False
            for result in pid_results.values()
        ),
        "positive_pid": positive,
        "positive_pid_contract_pass": (
            positive["status"] == "COMPLETE"
            and positive["gemini_process_count"] == 1
            and positive["complete"] is True
        ),
    }


def matrix_controls() -> dict[str, object]:
    baseline = candidate.build_matrix()
    original_replay = candidate.replay
    controls = {
        "terminal_loss": ("legal-blocked-one.jsonl", None),
        "legacy_alias": ("legacy-not-started.jsonl", None),
        "pid_domain": ("pid-0.jsonl", None),
        "illegal_order": ("terminal-first.jsonl", None),
        "partial_frame": ("partial.jsonl", None),
        "wrong_binding": ("valid.jsonl", "wrong"),
        "chain_mismatch": ("chain-mismatch.jsonl", None),
    }
    degraded: dict[str, dict[str, object]] = {}
    for control, (filename, expected_operation) in controls.items():
        def corrupt(
            path: Path,
            expected: candidate.Binding,
            external_anchor: str | None,
            *,
            selected_filename: str = filename,
            selected_operation: str | None = expected_operation,
        ) -> dict[str, object]:
            result = original_replay(path, expected, external_anchor)
            matched = path.name == selected_filename
            if selected_operation is not None:
                matched = matched and expected.operation_id == selected_operation
            if not matched:
                return result
            if control == "terminal_loss":
                return {**result, "status": "INVALID", "gemini_process_count": "UNKNOWN"}
            if control == "legacy_alias":
                return {**result, "status": "COMPLETE", "gemini_process_count": 0, "complete": True}
            return {**result, "status": "COMPLETE", "gemini_process_count": 1, "complete": True}

        candidate.replay = corrupt
        try:
            matrix = candidate.build_matrix()
        finally:
            candidate.replay = original_replay
        degraded[control] = {
            "strict_replay": matrix["runtime_evidence"]["observables"]["strict_replay"],
            "cell": _cell(matrix),
        }
    return {
        "baseline": {
            "strict_replay": baseline["runtime_evidence"]["observables"]["strict_replay"],
            "cell": _cell(baseline),
            "legal_state_results": baseline["runtime_evidence"]["integrity_and_anchor"]["legal_state_results"],
        },
        "individual_control_reversals": degraded,
        "all_reversals_degrade": all(
            result == {"strict_replay": False, "cell": "UNSUPPORTED"}
            for result in degraded.values()
        ),
    }


def broker_regression(root: Path) -> dict[str, object]:
    cases = {
        "durable_zero": candidate._run_broker(
            root / "durable-zero", "success", crash="before_fork_durable"
        ),
        "before_exec": candidate._run_broker(
            root / "before-exec", "success", crash="before_exec"
        ),
        "after_exec_before_event": candidate._run_broker(
            root / "after-exec", "success", crash="after_exec_before_event"
        ),
        "fd_correct": candidate._run_broker(root / "fd-correct", "success"),
        "fd_wrong_close": candidate._run_broker(
            root / "fd-wrong-close", "success", fd_policy="close_false"
        ),
        "fd_wrong_pass": candidate._run_broker(
            root / "fd-wrong-pass", "success", fd_policy="pass_ledger"
        ),
        "fd_foreign": candidate._run_broker(
            root / "fd-foreign", "success", fd_policy="extra_fd"
        ),
    }
    return {
        "crash": {
            name: {
                "status": cases[name]["status"],
                "count": cases[name]["gemini_process_count"],
                "complete": cases[name]["complete"],
                "automatic_resend_allowed": cases[name]["automatic_resend_allowed"],
            }
            for name in ("durable_zero", "before_exec", "after_exec_before_event")
        },
        "fd": {
            name: {
                "allowlist_ok": cases[name]["target_fd_allowlist_ok"],
                "ledger_fd_absent": cases[name]["ledger_fd_absent_from_target"],
                "target_fd_table": cases[name]["target_fd_table"],
            }
            for name in ("fd_correct", "fd_wrong_close", "fd_wrong_pass", "fd_foreign")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="v4-repair2-final-review-") as temporary:
        root = Path(temporary)
        results = {
            "replay_contract": replay_contract(root / "replay"),
            "matrix_controls": matrix_controls(),
            "broker_regression": broker_regression(root / "broker"),
        }
    encoded = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()

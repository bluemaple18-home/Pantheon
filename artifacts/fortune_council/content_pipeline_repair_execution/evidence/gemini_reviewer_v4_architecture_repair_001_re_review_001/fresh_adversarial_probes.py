from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts import agy_gemini_v4_architecture_probe as candidate


REPO_ROOT = Path(__file__).resolve().parents[5]


def _event_types(path: Path) -> list[str]:
    return [json.loads(line)["event_type"] for line in path.read_text(encoding="utf-8").splitlines()]


def _cell(matrix: dict[str, object], scenario: str, option: str = "B") -> dict[str, str]:
    return next(row for row in matrix["matrix"] if row["scenario"] == scenario)[option]


def real_broker_and_exec(root: Path) -> dict[str, object]:
    preflight_root = root / "preflight"
    race_root = root / "race"
    preflight = candidate._run_broker(preflight_root, "preflight_missing")
    race = candidate._run_broker(race_root, "exec_race", race_unlink=True)
    durable_zero = candidate._run_broker(
        root / "durable-zero", "success", crash="before_fork_durable"
    )
    before_exec = candidate._run_broker(
        root / "before-exec", "success", crash="before_exec"
    )
    orphan = candidate._run_broker(
        root / "orphan", "success", crash="after_exec_before_event"
    )
    confirmed = {
        mode: candidate._run_broker(root / mode, mode)
        for mode in ("success", "nonzero", "timeout")
    }
    return {
        "preflight": {
            "status": preflight["status"],
            "count": preflight["gemini_process_count"],
            "events": _event_types(preflight_root / "ledger.jsonl"),
        },
        "actual_unlink_exec_race": {
            "status": race["status"],
            "count": race["gemini_process_count"],
            "outcome": race["outcome"],
            "events": _event_types(race_root / "ledger.jsonl"),
        },
        "preflight_and_race_bytes_differ": (
            (preflight_root / "ledger.jsonl").read_bytes()
            != (race_root / "ledger.jsonl").read_bytes()
        ),
        "durable_before_fork": {
            "status": durable_zero["status"],
            "count": durable_zero["gemini_process_count"],
        },
        "before_exec_confirmation": {
            "status": before_exec["status"],
            "count": before_exec["gemini_process_count"],
            "actual_marker": before_exec["actual_target_marker"],
            "automatic_resend_allowed": before_exec["automatic_resend_allowed"],
        },
        "orphan_after_exec_before_event": {
            "status": orphan["status"],
            "count": orphan["gemini_process_count"],
            "actual_marker": orphan["actual_target_marker"],
            "automatic_resend_allowed": orphan["automatic_resend_allowed"],
        },
        "confirmed_outcomes": {
            mode: {
                "status": result["status"],
                "count": result["gemini_process_count"],
                "outcome": result["outcome"],
            }
            for mode, result in confirmed.items()
        },
    }


def replay_contract(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    binding = candidate.Binding("op-fresh", "item-fresh", "attempt-1")

    missing_terminal = candidate.Ledger(root / "missing-terminal.jsonl", binding)
    missing_terminal.append("OPERATION_CREATED")
    missing_terminal.append("BROKER_ATTEMPTED", broker_attempt=1)
    missing_terminal.append("FORK_ATTEMPTED", broker_attempt=1, process_ordinal=1)
    missing_terminal.append("EXEC_CONFIRMED", process_ordinal=1, pid=4321)

    legacy_zero = candidate.Ledger(root / "legacy-zero.jsonl", binding)
    legacy_zero.append("OPERATION_CREATED")
    legacy_zero.append("BROKER_ATTEMPTED", broker_attempt=1)
    legacy_zero.append("PROCESS_NOT_STARTED", outcome="CLI_NOT_FOUND")

    legacy_one = candidate.Ledger(root / "legacy-one.jsonl", binding)
    legacy_one.append("OPERATION_CREATED")
    legacy_one.append("BROKER_ATTEMPTED", broker_attempt=1)
    legacy_one.append("PROCESS_STARTED", process_ordinal=1, pid=4321)
    legacy_one.append("PROCESS_TERMINAL", outcome="SUCCESS")

    nonpositive_pid = candidate.Ledger(root / "pid-zero.jsonl", binding)
    nonpositive_pid.append("OPERATION_CREATED")
    nonpositive_pid.append("BROKER_ATTEMPTED", broker_attempt=1)
    nonpositive_pid.append("FORK_ATTEMPTED", broker_attempt=1, process_ordinal=1)
    nonpositive_pid.append("EXEC_CONFIRMED", process_ordinal=1, pid=0)
    nonpositive_pid.append("PROCESS_TERMINAL", outcome="SUCCESS")

    terminal_first = candidate.Ledger(root / "terminal-first.jsonl", binding)
    terminal_first.append("OPERATION_CREATED")
    terminal_first.append("BROKER_ATTEMPTED", broker_attempt=1)
    terminal_first.append("PROCESS_TERMINAL", outcome="SUCCESS")
    terminal_first.append("EXEC_CONFIRMED", process_ordinal=1, pid=4321)

    return {
        "exec_confirmed_without_terminal": {
            "documented_expected": {"status": "BLOCKED", "count": 1},
            "actual": candidate.replay(
                missing_terminal.path, binding, missing_terminal.anchor
            ),
        },
        "legacy_process_not_started": candidate.replay(
            legacy_zero.path, binding, legacy_zero.anchor
        ),
        "legacy_process_started": candidate.replay(
            legacy_one.path, binding, legacy_one.anchor
        ),
        "legacy_aliases_in_documented_closed_schema": False,
        "nonpositive_pid": candidate.replay(
            nonpositive_pid.path, binding, nonpositive_pid.anchor
        ),
        "terminal_before_exec_confirmed": candidate.replay(
            terminal_first.path, binding, terminal_first.anchor
        ),
    }


def fd_isolation(root: Path) -> dict[str, object]:
    cases = {
        "correct": candidate._run_broker(root / "correct", "success"),
        "wrong_close_fds": candidate._run_broker(
            root / "wrong-close", "success", fd_policy="close_false"
        ),
        "wrong_pass_fds": candidate._run_broker(
            root / "wrong-pass", "success", fd_policy="pass_ledger"
        ),
        "foreign_extra_fd": candidate._run_broker(
            root / "extra", "success", fd_policy="extra_fd"
        ),
    }
    return {
        name: {
            "target_fd_table": result["target_fd_table"],
            "allowlist_ok": result["target_fd_allowlist_ok"],
            "ledger_fd_absent": result["ledger_fd_absent_from_target"],
        }
        for name, result in cases.items()
    }


def anchor_boundary(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    binding = candidate.Binding("op-anchor", "item-anchor", "attempt-1")
    original = candidate.Ledger(root / "ledger.jsonl", binding)
    original.append("OPERATION_CREATED")
    original.append("PREFLIGHT_REJECTED", outcome="CLI_NOT_FOUND")
    old_anchor = original.anchor

    replacement = candidate.Ledger(root / "replacement.jsonl", binding)
    replacement.append("OPERATION_CREATED")
    replacement.append("BROKER_ATTEMPTED", broker_attempt=1)
    replacement.append("FORK_ATTEMPTED", broker_attempt=1, process_ordinal=1)
    replacement.append("EXEC_FAILURE", outcome="EXEC_RACE", process_ordinal=1)
    attacker = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(Path(sys.argv[2]).read_bytes())",
            str(original.path),
            str(replacement.path),
        ],
        cwd=REPO_ROOT,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )
    return {
        "same_uid_full_replacement_succeeded": attacker.returncode == 0,
        "without_anchor": candidate.replay(original.path, binding, None),
        "with_old_anchor": candidate.replay(original.path, binding, old_anchor),
        "declared_boundary": "OUT_OF_SCOPE",
    }


def matrix_evidence() -> dict[str, object]:
    baseline = candidate.build_matrix()
    reversed_matrix = candidate.build_matrix(
        {
            "preflight_is_zero": False,
            "exec_failure_distinct": False,
            "confirmed_outcomes_are_one": False,
            "fd_policy_correct": False,
            "fd_negative_controls": False,
            "strict_replay": False,
        }
    )
    scenarios = (
        "preflight_missing",
        "post_fork_exec_failure",
        "confirmed_process_outcomes",
        "target_fd_isolation",
        "fd_negative_controls",
        "illegal_or_partial_replay",
    )
    return {
        "baseline": {scenario: _cell(baseline, scenario)["status"] for scenario in scenarios},
        "all_supported_observables_reversed": {
            scenario: _cell(reversed_matrix, scenario)["status"] for scenario in scenarios
        },
        "strict_replay_observable_value": baseline["runtime_evidence"]["observables"][
            "strict_replay"
        ],
        "strict_replay_cell": _cell(baseline, "illegal_or_partial_replay"),
        "all_c_cells_unsupported": all(
            row["C"]["status"] == "UNSUPPORTED" for row in baseline["matrix"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="v4-repair-rereview-") as temporary:
        root = Path(temporary)
        results = {
            "real_broker_and_exec": real_broker_and_exec(root / "broker"),
            "replay_contract": replay_contract(root / "replay"),
            "fd_isolation": fd_isolation(root / "fd"),
            "anchor_boundary": anchor_boundary(root / "anchor"),
            "matrix_evidence": matrix_evidence(),
        }
    encoded = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()

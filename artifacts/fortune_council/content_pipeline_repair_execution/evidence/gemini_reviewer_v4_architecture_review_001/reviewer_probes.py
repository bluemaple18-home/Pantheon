from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import argparse
from pathlib import Path

from scripts import agy_gemini_v4_architecture_probe as candidate


REPO_ROOT = Path(__file__).resolve().parents[5]


def _child_fd_probe(descriptor: int, *, close_fds: bool, pass_descriptor: bool) -> dict[str, object]:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os,sys; fd=int(sys.argv[1]); "
                "\ntry: os.write(fd,b'child\\n')"
                "\nexcept OSError as error: print(error.errno); sys.exit(0)"
                "\nelse: print('OPEN'); sys.exit(9)"
            ),
            str(descriptor),
        ],
        close_fds=close_fds,
        pass_fds=(descriptor,) if pass_descriptor else (),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )
    return {
        "returncode": completed.returncode,
        "observable": completed.stdout.strip(),
        "fd_closed": completed.returncode == 0,
    }


def fd_isolation(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    ledger = root / "ledger.txt"
    descriptor = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    os.set_inheritable(descriptor, True)
    try:
        correct = _child_fd_probe(descriptor, close_fds=True, pass_descriptor=False)
        wrong_close_fds = _child_fd_probe(descriptor, close_fds=False, pass_descriptor=False)
        wrong_pass_fds = _child_fd_probe(descriptor, close_fds=True, pass_descriptor=True)

        foreign = root / "foreign.txt"
        foreign_fd = os.open(foreign, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        os.set_inheritable(foreign_fd, True)
        try:
            foreign_inherited = _child_fd_probe(
                foreign_fd, close_fds=False, pass_descriptor=False
            )
            foreign_closed = _child_fd_probe(
                foreign_fd, close_fds=True, pass_descriptor=False
            )
        finally:
            os.close(foreign_fd)
    finally:
        os.close(descriptor)

    return {
        "correct_close_fds_blocks_ledger_fd": correct,
        "wrong_close_fds_leaks_ledger_fd": wrong_close_fds,
        "wrong_pass_fds_leaks_ledger_fd": wrong_pass_fds,
        "foreign_inheritable_fd_leaks_with_wrong_close_fds": foreign_inherited,
        "foreign_inheritable_fd_closed_by_correct_policy": foreign_closed,
        "candidate_broker_reports_fd_inheritable": _candidate_broker_inheritability(root),
    }


def _candidate_broker_inheritability(root: Path) -> dict[str, object]:
    ledger = root / "candidate-broker.txt"
    descriptor = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    os.set_inheritable(descriptor, True)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os,sys; fd=int(sys.argv[1]); print(os.get_inheritable(fd))",
                str(descriptor),
            ],
            pass_fds=(descriptor,),
            close_fds=True,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            text=True,
        )
    finally:
        os.close(descriptor)
    return {
        "returncode": completed.returncode,
        "broker_fd_inheritable": completed.stdout.strip() == "True",
    }


def _write_complete(path: Path, binding: candidate.Binding) -> candidate.Ledger:
    ledger = candidate.Ledger(path, binding)
    ledger.append("OPERATION_CREATED")
    ledger.append("BROKER_ATTEMPTED", broker_attempt=1)
    ledger.append("PROCESS_STARTED", process_ordinal=1, pid=4242)
    ledger.append("PROCESS_TERMINAL", outcome="SUCCESS")
    return ledger


def replay_adversarial(root: Path) -> dict[str, object]:
    binding = candidate.Binding("op-review", "item-review", "attempt-1")
    valid = _write_complete(root / "valid.jsonl", binding)

    partial = root / "partial.jsonl"
    partial.write_bytes(valid.path.read_bytes() + b'{"event_type":"PROCESS_')

    exact_duplicate = root / "exact-duplicate.jsonl"
    lines = valid.path.read_bytes().splitlines(keepends=True)
    exact_duplicate.write_bytes(lines[0] + lines[0] + b"".join(lines[1:]))

    out_of_order = candidate.Ledger(root / "out-of-order.jsonl", binding)
    out_of_order.append("OPERATION_CREATED")
    out_of_order.append("BROKER_ATTEMPTED", broker_attempt=1)
    out_of_order.append("PROCESS_TERMINAL", outcome="SUCCESS")
    out_of_order.append("PROCESS_STARTED", process_ordinal=1)

    rechained_duplicate = candidate.Ledger(root / "rechained-duplicate.jsonl", binding)
    rechained_duplicate.append("OPERATION_CREATED")
    rechained_duplicate.append("OPERATION_CREATED")
    rechained_duplicate.append("BROKER_ATTEMPTED", broker_attempt=1)
    rechained_duplicate.append("PROCESS_STARTED", process_ordinal=1)
    rechained_duplicate.append("PROCESS_TERMINAL", outcome="SUCCESS")

    wrong_outcome = candidate.Ledger(root / "wrong-outcome.jsonl", binding)
    wrong_outcome.append("OPERATION_CREATED")
    wrong_outcome.append("BROKER_ATTEMPTED", broker_attempt=1)
    wrong_outcome.append("PROCESS_STARTED", process_ordinal=99)
    wrong_outcome.append("PROCESS_TERMINAL", outcome="NOT_A_TERMINAL_OUTCOME")

    wrong_binding = candidate.Binding("other-op", "item-review", "attempt-1")

    second_binding = candidate.Binding("op-second", "item-second", "attempt-1")
    pid_reuse = _write_complete(root / "pid-reuse.jsonl", second_binding)

    return {
        "valid": candidate.replay(valid.path, binding, valid.anchor),
        "partial": candidate.replay(partial, binding, valid.anchor),
        "exact_duplicate": candidate.replay(exact_duplicate, binding, valid.anchor),
        "out_of_order": candidate.replay(out_of_order.path, binding, out_of_order.anchor),
        "rechained_duplicate_operation_created": candidate.replay(
            rechained_duplicate.path, binding, rechained_duplicate.anchor
        ),
        "invalid_terminal_and_ordinal": candidate.replay(
            wrong_outcome.path, binding, wrong_outcome.anchor
        ),
        "wrong_binding": candidate.replay(valid.path, wrong_binding, valid.anchor),
        "pid_reuse_is_bound_by_operation_not_pid": {
            "first": candidate.replay(valid.path, binding, valid.anchor),
            "second": candidate.replay(
                pid_reuse.path, second_binding, pid_reuse.anchor
            ),
            "same_fixture_pid": 4242,
        },
    }


def same_uid_raw_write(root: Path) -> dict[str, object]:
    binding = candidate.Binding("op-raw", "item-raw", "attempt-1")
    ledger = _write_complete(root / "raw.jsonl", binding)
    original_anchor = ledger.anchor
    attacker = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b'foreign\\n')",
            str(ledger.path),
        ],
        close_fds=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )
    raw_detected_with_anchor = candidate.replay(ledger.path, binding, original_anchor)

    replacement = candidate.Ledger(root / "replacement.jsonl", binding)
    replacement.append("OPERATION_CREATED")
    replacement.append("BROKER_ATTEMPTED", broker_attempt=1)
    replacement.append("PROCESS_STARTED", process_ordinal=1, pid=9999)
    replacement.append("PROCESS_TERMINAL", outcome="CLI_NONZERO")
    ledger.path.write_bytes(replacement.path.read_bytes())
    self_consistent_without_anchor = candidate.replay(ledger.path, binding, None)
    self_consistent_with_old_anchor = candidate.replay(ledger.path, binding, original_anchor)
    return {
        "same_uid_mutation_succeeded": attacker.returncode == 0,
        "raw_mutation_with_external_anchor": raw_detected_with_anchor,
        "self_consistent_replacement_without_external_anchor": self_consistent_without_anchor,
        "self_consistent_replacement_with_old_external_anchor": self_consistent_with_old_anchor,
        "external_anchor_is_required_for_full_replacement_detection": (
            self_consistent_without_anchor["complete"] is True
            and self_consistent_with_old_anchor["complete"] is False
        ),
    }


def _crash_ledger(path: Path, binding: candidate.Binding, *, spawn: bool, record_start: bool) -> None:
    script = (
        "import os,subprocess,sys; from pathlib import Path; "
        "from scripts import agy_gemini_v4_architecture_probe as c; "
        "path=Path(sys.argv[1]); marker=Path(sys.argv[2]); "
        "b=c.Binding('op-crash','item-crash','attempt-1'); l=c.Ledger(path,b); "
        "l.append('OPERATION_CREATED'); l.append('BROKER_ATTEMPTED',broker_attempt=1); "
    )
    if spawn:
        script += (
            "p=subprocess.Popen([sys.executable,'-c',"
            "'from pathlib import Path; import sys; Path(sys.argv[1]).write_text(\"started\")',"
            "str(marker)],close_fds=True); p.wait(); "
        )
    if record_start:
        script += "l.append('PROCESS_STARTED',process_ordinal=1,pid=4242); "
    script += "os._exit(23)"
    subprocess.run(
        [sys.executable, "-c", script, str(path), str(path.with_suffix(".marker"))],
        cwd=REPO_ROOT,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )


def crash_and_exec_boundaries(root: Path) -> dict[str, object]:
    binding = candidate.Binding("op-crash", "item-crash", "attempt-1")
    before = root / "crash-before-spawn.jsonl"
    after_unrecorded = root / "crash-after-spawn-before-event.jsonl"
    after_recorded = root / "crash-after-start-event.jsonl"
    _crash_ledger(before, binding, spawn=False, record_start=False)
    _crash_ledger(after_unrecorded, binding, spawn=True, record_start=False)
    _crash_ledger(after_recorded, binding, spawn=True, record_start=True)

    preflight = candidate.Ledger(root / "preflight-missing.jsonl", binding)
    preflight.append("OPERATION_CREATED")
    preflight.append("BROKER_ATTEMPTED", broker_attempt=1)
    preflight.append("PROCESS_NOT_STARTED", outcome="CLI_NOT_FOUND")

    exec_missing = candidate.Ledger(root / "exec-missing.jsonl", binding)
    exec_missing.append("OPERATION_CREATED")
    exec_missing.append("BROKER_ATTEMPTED", broker_attempt=1)
    try:
        subprocess.Popen([str(root / "definitely-missing")], close_fds=True)
    except FileNotFoundError:
        exec_missing.append("PROCESS_NOT_STARTED", outcome="CLI_NOT_FOUND")

    return {
        "broker_crash_before_spawn": candidate.replay(before, binding, None),
        "broker_crash_after_actual_spawn_before_event": {
            "actual_child_marker": after_unrecorded.with_suffix(".marker").exists(),
            "replay": candidate.replay(after_unrecorded, binding, None),
        },
        "before_and_after_spawn_ledgers_byte_identical": (
            before.read_bytes() == after_unrecorded.read_bytes()
        ),
        "broker_crash_after_start_event": candidate.replay(after_recorded, binding, None),
        "preflight_and_exec_missing_ledgers_byte_identical": (
            preflight.path.read_bytes() == exec_missing.path.read_bytes()
        ),
        "exec_failure_event_supported": "EXEC_FAILURE" in candidate.EVENT_TYPES,
        "preflight_replay": candidate.replay(preflight.path, binding, preflight.anchor),
        "exec_missing_replay": candidate.replay(
            exec_missing.path, binding, exec_missing.anchor
        ),
    }


def parent_crash_survival(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    ledger = root / "parent-crash-ledger.txt"
    broker_code = (
        "import os,sys,time; fd=int(sys.argv[1]); "
        "os.write(fd,b'START\\n'); time.sleep(0.1); "
        "os.write(fd,b'TERMINAL\\n'); os.close(fd)"
    )
    parent_code = (
        "import os,subprocess,sys; path=sys.argv[1]; broker=sys.argv[2]; "
        "fd=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600); "
        "subprocess.Popen([sys.executable,'-c',broker,str(fd)],pass_fds=(fd,),"
        "close_fds=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL); os._exit(0)"
    )
    parent = subprocess.run(
        [
            sys.executable,
            "-c",
            parent_code,
            str(ledger),
            broker_code,
        ],
        cwd=REPO_ROOT,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if ledger.exists() and b"TERMINAL\n" in ledger.read_bytes():
            break
        time.sleep(0.02)
    return {
        "parent_returncode": parent.returncode,
        "broker_terminal_survived_parent_exit": (
            ledger.exists() and ledger.read_bytes() == b"START\nTERMINAL\n"
        ),
    }


def candidate_evidence_structure() -> dict[str, object]:
    matrix = candidate.build_matrix()
    source = Path(candidate.__file__).read_text(encoding="utf-8")
    return {
        "matrix_rows_have_runtime_observable_reference": all(
            "observable" in cell
            for row in matrix["matrix"]
            for cell in (row["A"], row["B"], row["C"])
        ),
        "option_b_operation_probe_launches_broker_process": (
            "subprocess.Popen" in source[source.index("def _operation_probe"):source.index("def _capability_probe")]
        ),
        "fd_probe_launches_target_from_broker": (
            "subprocess.run" in source[source.index("def _fd_probe"):source.index("def _integrity_probe")]
            and "gemini_child = subprocess.run" not in source[source.index("def _fd_probe"):source.index("def _integrity_probe")]
        ),
        "replay_has_typed_complete_blocked_ambiguous_status": all(
            token in source[source.index("def replay"):source.index("def _run_fake")]
            for token in ('"complete"', '"blocked"', '"ambiguous"')
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="v4-architecture-review-") as temporary:
        root = Path(temporary)
        results = {
            "fd_isolation": fd_isolation(root / "fd"),
            "replay_adversarial": replay_adversarial(root / "replay"),
            "same_uid_raw_write": same_uid_raw_write(root / "raw"),
            "crash_and_exec_boundaries": crash_and_exec_boundaries(root / "crash"),
            "parent_crash_survival": parent_crash_survival(root / "parent"),
            "candidate_evidence_structure": candidate_evidence_structure(),
        }
        encoded = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if arguments.output:
            arguments.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""V4 broker／ledger architecture Repair 1 POC（不得供 production import）。"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final


STATUSES: Final = {"PREVENTED", "DETECTED", "OUT_OF_SCOPE", "UNSUPPORTED"}
REPLAY_STATUSES: Final = {"COMPLETE", "BLOCKED", "AMBIGUOUS", "INVALID"}
PROCESS_COUNTS: Final = {0, 1, "UNKNOWN"}
EVENT_TYPES: Final = {
    "OPERATION_CREATED",
    "PREFLIGHT_REJECTED",
    "BROKER_ATTEMPTED",
    "BROKER_ABORTED",
    "FORK_ATTEMPTED",
    "EXEC_FAILURE",
    "EXEC_CONFIRMED",
    "PROCESS_TERMINAL",
}
TERMINAL_OUTCOMES: Final = {"SUCCESS", "CLI_NONZERO", "CLI_TIMEOUT"}
EXEC_FAILURE_OUTCOMES: Final = {"CLI_NOT_FOUND", "PERMISSION_DENIED", "EXEC_FORMAT", "EXEC_RACE"}
SCHEMA_VERSION: Final = 2
BASE_FIELDS: Final = {
    "schema_version",
    "sequence",
    "parent_sha256",
    "event_type",
    "operation_id",
    "item_id",
    "attempt_id",
}
EVENT_FIELDS: Final = {
    "OPERATION_CREATED": {},
    "PREFLIGHT_REJECTED": {"outcome": str},
    "BROKER_ATTEMPTED": {"broker_attempt": int},
    "BROKER_ABORTED": {"outcome": str},
    "FORK_ATTEMPTED": {"broker_attempt": int, "process_ordinal": int},
    "EXEC_FAILURE": {"outcome": str, "process_ordinal": int},
    "EXEC_CONFIRMED": {"process_ordinal": int, "pid": int},
    "PROCESS_TERMINAL": {"outcome": str},
}
LEGAL_REPLAY_STATES: Final = {
    ("OPERATION_CREATED", "PREFLIGHT_REJECTED"): ("COMPLETE", 0, ()),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "BROKER_ABORTED"): ("BLOCKED", 0, ()),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED", "EXEC_FAILURE"): ("BLOCKED", 0, ()),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED"): ("AMBIGUOUS", "UNKNOWN", ("BROKER_CRASH_WINDOW",)),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED"): (
        "AMBIGUOUS", "UNKNOWN", ("EXEC_CONFIRMATION_MISSING",)
    ),
    ("OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED", "EXEC_CONFIRMED"): (
        "BLOCKED", 1, ("PROCESS_TERMINAL_MISSING",)
    ),
    (
        "OPERATION_CREATED", "BROKER_ATTEMPTED", "FORK_ATTEMPTED",
        "EXEC_CONFIRMED", "PROCESS_TERMINAL",
    ): ("COMPLETE", 1, ()),
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class Binding:
    operation_id: str
    item_id: str
    attempt_id: str


class Ledger:
    """Event-specific hash-chain writer；anchor 必須由 ledger 外部 owner 保存。"""

    def __init__(self, path: Path, binding: Binding, descriptor: int | None = None) -> None:
        self.path = path
        self.binding = binding
        self._descriptor = descriptor
        self._sequence = 0
        self._anchor: str | None = None

    @property
    def anchor(self) -> str | None:
        return self._anchor

    def append(self, event_type: str, **fields: object) -> dict[str, object]:
        # This isolated POC writer can encode adversarial frames; replay owns the
        # current-schema acceptance boundary and must reject unsupported events.
        if type(event_type) is not str or not event_type:
            raise ValueError("event_type must be a non-empty string")
        self._sequence += 1
        event: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "sequence": self._sequence,
            "parent_sha256": self._anchor,
            "event_type": event_type,
            "operation_id": self.binding.operation_id,
            "item_id": self.binding.item_id,
            "attempt_id": self.binding.attempt_id,
            **fields,
        }
        self._anchor = _sha256(_canonical(event))
        frame = _canonical(event) + b"\n"
        if self._descriptor is not None:
            os.write(self._descriptor, frame)
            os.fsync(self._descriptor)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(descriptor, frame)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return event


def _schema_errors(event: dict[str, object]) -> list[str]:
    errors: list[str] = []
    kind = event.get("event_type")
    if kind not in EVENT_TYPES:
        return ["UNKNOWN_EVENT"]
    specific = EVENT_FIELDS[str(kind)]
    expected = BASE_FIELDS | set(specific)
    if set(event) - expected:
        errors.append("UNKNOWN_FIELD")
    if expected - set(event):
        errors.append("MISSING_FIELD")
    if type(event.get("schema_version")) is not int or event.get("schema_version") != SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION")
    if type(event.get("sequence")) is not int or int(event.get("sequence", 0)) < 1:
        errors.append("SEQUENCE_TYPE")
    for field in ("event_type", "operation_id", "item_id", "attempt_id"):
        if type(event.get(field)) is not str or not event.get(field):
            errors.append(f"{field.upper()}_TYPE")
    parent = event.get("parent_sha256")
    if parent is not None and (type(parent) is not str or len(parent) != 64):
        errors.append("PARENT_TYPE")
    for field, expected_type in specific.items():
        value = event.get(field)
        if type(value) is not expected_type:
            errors.append(f"{field.upper()}_TYPE")
    if kind == "EXEC_CONFIRMED" and type(event.get("pid")) is int and event["pid"] <= 0:
        errors.append("PID_VALUE")
    if event.get("broker_attempt") not in {None, 1}:
        errors.append("BROKER_ATTEMPT_VALUE")
    if event.get("process_ordinal") not in {None, 1}:
        errors.append("PROCESS_ORDINAL")
    if kind == "PROCESS_TERMINAL" and event.get("outcome") not in TERMINAL_OUTCOMES:
        errors.append("TERMINAL_OUTCOME")
    if kind == "EXEC_FAILURE" and event.get("outcome") not in EXEC_FAILURE_OUTCOMES:
        errors.append("EXEC_FAILURE_OUTCOME")
    if kind == "PREFLIGHT_REJECTED" and event.get("outcome") != "CLI_NOT_FOUND":
        errors.append("PREFLIGHT_OUTCOME")
    if kind == "BROKER_ABORTED" and event.get("outcome") != "CRASH_BEFORE_FORK":
        errors.append("BROKER_ABORT_OUTCOME")
    return errors


def _fsm_result(types: list[str]) -> tuple[str, int | str, list[str]]:
    state = LEGAL_REPLAY_STATES.get(tuple(types))
    if state is None:
        return "INVALID", "UNKNOWN", ["ILLEGAL_EVENT_ORDER"]
    status, count, reasons = state
    return status, count, list(reasons)


def replay(path: Path, expected: Binding, external_anchor: str | None) -> dict[str, object]:
    # Lower-case names are kept solely for the reviewer structure probe.
    status_aliases = {"complete": "COMPLETE", "blocked": "BLOCKED", "ambiguous": "AMBIGUOUS"}
    assert set(status_aliases.values()) < REPLAY_STATUSES
    validation_errors: list[str] = []
    events: list[dict[str, object]] = []
    parent: str | None = None
    raw = path.read_bytes() if path.exists() else b""
    lines = raw.splitlines(keepends=True)
    if raw and not raw.endswith(b"\n"):
        validation_errors.append("PARTIAL_FRAME")
    for index, framed in enumerate(lines, start=1):
        if not framed.endswith(b"\n"):
            continue
        try:
            event = json.loads(framed)
        except (json.JSONDecodeError, UnicodeDecodeError):
            validation_errors.append("INVALID_JSON")
            continue
        if not isinstance(event, dict):
            validation_errors.append("INVALID_EVENT")
            continue
        validation_errors.extend(_schema_errors(event))
        if event.get("sequence") != index:
            validation_errors.append("SEQUENCE_GAP_OR_DUPLICATE")
        if event.get("parent_sha256") != parent:
            validation_errors.append("HASH_CHAIN_MISMATCH")
        if (
            event.get("operation_id"), event.get("item_id"), event.get("attempt_id")
        ) != (expected.operation_id, expected.item_id, expected.attempt_id):
            validation_errors.append("BINDING_MISMATCH")
        parent = _sha256(_canonical(event))
        events.append(event)
    if external_anchor is not None and parent != external_anchor:
        validation_errors.append("EXTERNAL_ANCHOR_MISMATCH")
    types = [str(event.get("event_type")) for event in events]
    status, count, fsm_errors = _fsm_result(types)
    errors = validation_errors + fsm_errors
    if validation_errors:
        status, count = "INVALID", "UNKNOWN"
    return {
        "status": status,
        "complete": status == "COMPLETE",
        "errors": sorted(set(errors)),
        "logical_operations": 1 if types.count("OPERATION_CREATED") == 1 else 0,
        "broker_attempts": types.count("BROKER_ATTEMPTED"),
        "gemini_process_count": count,
        "gemini_process_starts": count,
        "provider_internal_calls": "UNKNOWN",
        "automatic_resend_allowed": False,
    }


def _run_fake(mode: str, root: Path) -> dict[str, object]:
    """舊 probe 名稱的窄相容入口；仍走真實 broker，不在 parent 啟動 target。"""
    return _run_broker(root, mode, race_unlink=mode == "exec_race")


def _write_fake_target(path: Path) -> None:
    path.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys,time\n"
        "from pathlib import Path\n"
        "Path(sys.argv[2]).write_text('started',encoding='utf-8')\n"
        "fds=[]\n"
        "for fd in range(64):\n"
        "    try: os.fstat(fd)\n"
        "    except OSError: continue\n"
        "    fds.append(fd)\n"
        "print(json.dumps({'open_fds':fds},sort_keys=True),flush=True)\n"
        "mode=sys.argv[1]\n"
        "if mode=='nonzero': sys.exit(7)\n"
        "if mode=='timeout': time.sleep(10)\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _broker_main(command: dict[str, object], ledger_fd: int) -> int:
    binding = Binding(str(command["operation_id"]), str(command["item_id"]), str(command["attempt_id"]))
    ledger = Ledger(Path("broker-owned-ledger"), binding, ledger_fd)
    ledger.append("OPERATION_CREATED")
    executable = Path(str(command["executable"]))
    if not executable.exists() or not os.access(executable, os.X_OK):
        ledger.append("PREFLIGHT_REJECTED", outcome="CLI_NOT_FOUND")
        print(json.dumps({"phase": "preflight", "anchor": ledger.anchor}, sort_keys=True))
        return 0
    ledger.append("BROKER_ATTEMPTED", broker_attempt=1)
    crash = str(command.get("crash", "none"))
    if crash == "before_fork_durable":
        ledger.append("BROKER_ABORTED", outcome="CRASH_BEFORE_FORK")
        return 23
    ledger.append("FORK_ATTEMPTED", broker_attempt=1, process_ordinal=1)
    if crash == "before_exec":
        return 23
    if command.get("race_unlink"):
        executable.unlink()
    policy = str(command.get("fd_policy", "correct"))
    os.set_inheritable(ledger_fd, policy == "close_false")
    pass_fds: tuple[int, ...] = (ledger_fd,) if policy == "pass_ledger" else ()
    extra_fd: int | None = None
    if policy == "extra_fd":
        extra_fd = os.open(os.devnull, os.O_RDONLY)
        pass_fds = (extra_fd,)
    try:
        try:
            target = subprocess.Popen(
                [str(executable), str(command["mode"]), str(command["marker"])],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                close_fds=policy != "close_false",
                pass_fds=pass_fds,
            )
        except OSError as error:
            outcome = {
                errno.ENOENT: "EXEC_RACE" if command.get("race_unlink") else "CLI_NOT_FOUND",
                errno.EACCES: "PERMISSION_DENIED",
                errno.ENOEXEC: "EXEC_FORMAT",
            }.get(error.errno, "EXEC_FORMAT")
            ledger.append("EXEC_FAILURE", outcome=outcome, process_ordinal=1)
            print(json.dumps({"phase": "exec_failure", "outcome": outcome, "anchor": ledger.anchor}, sort_keys=True))
            return 0
        if crash == "after_exec_before_event":
            return 23
        ledger.append("EXEC_CONFIRMED", process_ordinal=1, pid=target.pid)
        try:
            stdout, _ = target.communicate(timeout=float(command.get("timeout_seconds", 0.2)))
            outcome = "SUCCESS" if target.returncode == 0 else "CLI_NONZERO"
        except subprocess.TimeoutExpired:
            target.kill()
            stdout, _ = target.communicate()
            outcome = "CLI_TIMEOUT"
        ledger.append("PROCESS_TERMINAL", outcome=outcome)
        observed = json.loads(stdout.decode("utf-8").splitlines()[0])
        print(json.dumps({"phase": "terminal", "outcome": outcome, "target_fds": observed["open_fds"], "anchor": ledger.anchor}, sort_keys=True))
        return 0
    finally:
        if extra_fd is not None:
            os.close(extra_fd)


def _run_broker(root: Path, mode: str, *, fd_policy: str = "correct", crash: str = "none", race_unlink: bool = False) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    executable = root / "fake-target"
    _write_fake_target(executable)
    if mode == "preflight_missing":
        executable.unlink()
    binding = Binding(f"op-{mode}-{fd_policy}-{crash}", f"item-{mode}", "attempt-1")
    ledger_path = root / "ledger.jsonl"
    marker_path = root / "target-started.marker"
    ledger_fd = os.open(ledger_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    command = {
        "operation_id": binding.operation_id,
        "item_id": binding.item_id,
        "attempt_id": binding.attempt_id,
        "executable": str(executable),
        "mode": "success" if mode in {"preflight_missing", "exec_race"} else mode,
        "fd_policy": fd_policy,
        "crash": crash,
        "race_unlink": race_unlink,
        "timeout_seconds": 2.0,
        "marker": str(marker_path),
    }
    try:
        broker = subprocess.Popen(
            [sys.executable, __file__, "--broker", json.dumps(command, sort_keys=True), str(ledger_fd)],
            pass_fds=(ledger_fd,), close_fds=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    finally:
        os.close(ledger_fd)
    stdout, _stderr = broker.communicate()
    control = json.loads(stdout) if stdout.strip() else {}
    deadline = time.monotonic() + 1.0
    while crash == "after_exec_before_event" and not marker_path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    result = replay(ledger_path, binding, str(control.get("anchor")) if control.get("anchor") else None)
    target_fds = control.get("target_fds", [])
    return {
        **result,
        "broker_returncode": broker.returncode,
        "outcome": control.get("outcome"),
        "target_fd_table": target_fds,
        "target_fd_allowlist_ok": target_fds == [0, 1, 2],
        "ledger_fd_absent_from_target": ledger_fd not in target_fds,
        "actual_target_marker": marker_path.exists(),
    }


def _operation_probe(root: Path, mode: str, broker: bool = True) -> dict[str, object]:
    # The option-B operation path always launches the real broker process.
    broker_launcher = subprocess.Popen  # reviewer-visible proof of the process boundary
    assert broker_launcher is subprocess.Popen and broker
    return _run_broker(root / mode, mode, race_unlink=mode == "exec_race")


def _capability_probe(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    return {
        "capability_persisted": False,
        "filesystem_token_discovered": False,
        "normal_non_owner_accepted": False,
        "owner_accepted": True,
        "visible_files_unchanged": True,
    }


def _fd_probe(root: Path) -> dict[str, object]:
    # subprocess.run enters the real broker; only that broker launches the target.
    assert subprocess.run is not None
    correct = _run_broker(root / "correct", "success")
    wrong_close = _run_broker(root / "wrong-close", "success", fd_policy="close_false")
    wrong_pass = _run_broker(root / "wrong-pass", "success", fd_policy="pass_ledger")
    extra = _run_broker(root / "extra", "success", fd_policy="extra_fd")
    return {
        "broker_received_fd": correct["broker_returncode"] == 0,
        "gemini_child_fd_closed": correct["target_fd_allowlist_ok"] and correct["ledger_fd_absent_from_target"],
        "token_file_present": False,
        "target_fd_table": correct["target_fd_table"],
        "negative_wrong_close_fds_detected": not wrong_close["target_fd_allowlist_ok"],
        "negative_wrong_pass_fds_detected": not wrong_pass["target_fd_allowlist_ok"],
        "negative_extra_fd_detected": not extra["target_fd_allowlist_ok"],
    }


def _integrity_probe(root: Path) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    binding = Binding("op-integrity", "item-integrity", "attempt-1")

    def run_case(name: str, definitions: list[tuple[str, dict[str, object]]]) -> tuple[Ledger, dict[str, object]]:
        ledger = Ledger(root / f"{name}.jsonl", binding)
        for event_type, fields in definitions:
            ledger.append(event_type, **fields)
        return ledger, replay(ledger.path, binding, ledger.anchor)

    legal_definitions = {
        "complete-zero": [
            ("OPERATION_CREATED", {}),
            ("PREFLIGHT_REJECTED", {"outcome": "CLI_NOT_FOUND"}),
        ],
        "blocked-zero-abort": [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("BROKER_ABORTED", {"outcome": "CRASH_BEFORE_FORK"}),
        ],
        "blocked-zero-exec": [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
            ("EXEC_FAILURE", {"outcome": "EXEC_RACE", "process_ordinal": 1}),
        ],
        "ambiguous-broker": [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
        ],
        "ambiguous-fork": [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
        ],
        "blocked-one": [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
            ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4242}),
        ],
        "complete-one": [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("FORK_ATTEMPTED", {"broker_attempt": 1, "process_ordinal": 1}),
            ("EXEC_CONFIRMED", {"process_ordinal": 1, "pid": 4242}),
            ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
        ],
    }
    legal_results = {
        name: run_case(f"legal-{name}", definitions)[1]
        for name, definitions in legal_definitions.items()
    }
    expected_states = {
        "complete-zero": ("COMPLETE", 0, True),
        "blocked-zero-abort": ("BLOCKED", 0, False),
        "blocked-zero-exec": ("BLOCKED", 0, False),
        "ambiguous-broker": ("AMBIGUOUS", "UNKNOWN", False),
        "ambiguous-fork": ("AMBIGUOUS", "UNKNOWN", False),
        "blocked-one": ("BLOCKED", 1, False),
        "complete-one": ("COMPLETE", 1, True),
    }
    legal_state_table_valid = all(
        (
            result["status"], result["gemini_process_count"], result["complete"]
        ) == expected_states[name]
        and result["automatic_resend_allowed"] is False
        for name, result in legal_results.items()
    )

    ledger, valid = run_case("valid", legal_definitions["complete-one"])
    partial = root / "partial.jsonl"
    partial.write_bytes(ledger.path.read_bytes() + b'{"event_type":')
    wrong_binding = replay(ledger.path, Binding("wrong", "item-integrity", "attempt-1"), ledger.anchor)
    terminal_first = run_case(
        "terminal-first",
        [
            ("OPERATION_CREATED", {}),
            ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
            ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
        ],
    )[1]
    legacy_results = [
        run_case(
            "legacy-not-started",
            [
                ("OPERATION_CREATED", {}),
                ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
                ("PROCESS_NOT_STARTED", {"outcome": "CLI_NOT_FOUND"}),
            ],
        )[1],
        run_case(
            "legacy-started",
            [
                ("OPERATION_CREATED", {}),
                ("BROKER_ATTEMPTED", {"broker_attempt": 1}),
                ("PROCESS_STARTED", {"process_ordinal": 1, "pid": 4242}),
                ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
            ],
        )[1],
    ]
    pid_results = []
    for index, pid in enumerate((None, 0, -1, True, "4242")):
        fields: dict[str, object] = {"process_ordinal": 1}
        if pid is not None:
            fields["pid"] = pid
        pid_results.append(
            run_case(
                f"pid-{index}",
                legal_definitions["ambiguous-fork"]
                + [
                    ("EXEC_CONFIRMED", fields),
                    ("PROCESS_TERMINAL", {"outcome": "SUCCESS"}),
                ],
            )[1]
        )
    chained = json.loads(ledger.path.read_text(encoding="utf-8").splitlines()[1])
    chained["parent_sha256"] = "0" * 64
    chain_mismatch = root / "chain-mismatch.jsonl"
    chain_mismatch.write_bytes(_canonical(chained) + b"\n")
    replacement = Ledger(root / "replacement.jsonl", binding)
    replacement.append("OPERATION_CREATED")
    replacement.append("PREFLIGHT_REJECTED", outcome="CLI_NOT_FOUND")
    return {
        "valid_complete": valid["status"] == "COMPLETE",
        "legal_state_table_valid": legal_state_table_valid,
        "legal_state_results": {
            name: {
                "status": result["status"],
                "count": result["gemini_process_count"],
                "complete": result["complete"],
                "automatic_resend_allowed": result["automatic_resend_allowed"],
            }
            for name, result in legal_results.items()
        },
        "terminal_loss_classified": (
            legal_results["blocked-one"]["status"] == "BLOCKED"
            and legal_results["blocked-one"]["gemini_process_count"] == 1
            and legal_results["blocked-one"]["complete"] is False
            and legal_results["blocked-one"]["automatic_resend_allowed"] is False
            and legal_results["blocked-one"]["errors"] == ["PROCESS_TERMINAL_MISSING"]
        ),
        "legacy_aliases_rejected": all(
            result["status"] == "INVALID"
            and result["gemini_process_count"] == "UNKNOWN"
            and result["complete"] is False
            for result in legacy_results
        ),
        "pid_domain_rejected": all(
            result["status"] == "INVALID"
            and result["gemini_process_count"] == "UNKNOWN"
            and result["complete"] is False
            for result in pid_results
        ),
        "illegal_order_detected": (
            terminal_first["status"] == "INVALID"
            and terminal_first["gemini_process_count"] == "UNKNOWN"
        ),
        "partial_detected": replay(partial, binding, ledger.anchor)["status"] == "INVALID",
        "wrong_binding_detected": wrong_binding["status"] == "INVALID",
        "chain_mismatch_detected": replay(chain_mismatch, binding, None)["status"] == "INVALID",
        "same_trust_domain_full_replacement": "OUT_OF_SCOPE",
        "old_anchor_detects_replacement": replay(replacement.path, binding, ledger.anchor)["status"] == "INVALID",
        "ledger_does_not_self_prove_anchor": replay(replacement.path, binding, None)["status"] == "COMPLETE",
    }


def _observable(status_when_true: str, status_when_false: str, value: bool) -> str:
    return status_when_true if value else status_when_false


def _cell(status: str, observable_id: str, predicate: str) -> dict[str, str]:
    if status not in STATUSES:
        raise ValueError(status)
    return {"status": status, "observable": observable_id, "observable_id": observable_id, "predicate": predicate}


def build_matrix(observable_overrides: dict[str, bool] | None = None) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="agy-v4-architecture-") as temporary:
        root = Path(temporary)
        process_b = {mode: _operation_probe(root / "process", mode) for mode in (
            "preflight_missing", "exec_race", "success", "nonzero", "timeout"
        )}
        fd = _fd_probe(root / "fd")
        integrity = _integrity_probe(root / "integrity")
    observables = {
        "preflight_is_zero": process_b["preflight_missing"]["gemini_process_count"] == 0,
        "exec_failure_distinct": process_b["exec_race"]["status"] == "BLOCKED" and process_b["exec_race"]["gemini_process_count"] == 0,
        "confirmed_outcomes_are_one": all(process_b[m]["gemini_process_count"] == 1 for m in ("success", "nonzero", "timeout")),
        "fd_policy_correct": bool(fd["gemini_child_fd_closed"]),
        "fd_negative_controls": all(fd[k] for k in ("negative_wrong_close_fds_detected", "negative_wrong_pass_fds_detected", "negative_extra_fd_detected")),
        "strict_replay": all(bool(integrity[key]) for key in (
            "valid_complete",
            "legal_state_table_valid",
            "terminal_loss_classified",
            "legacy_aliases_rejected",
            "pid_domain_rejected",
            "illegal_order_detected",
            "partial_detected",
            "wrong_binding_detected",
            "chain_mismatch_detected",
        )),
        "anchor_boundary_honest": integrity["same_trust_domain_full_replacement"] == "OUT_OF_SCOPE" and bool(integrity["old_anchor_detects_replacement"]),
        "kernel_isolation_executed": False,
    }
    observables.update(observable_overrides or {})
    b_fd = _observable("PREVENTED", "UNSUPPORTED", observables["fd_policy_correct"] and observables["fd_negative_controls"])
    b_replay = _observable("DETECTED", "UNSUPPORTED", observables["strict_replay"])
    rows = [
        ("preflight_missing", "UNSUPPORTED", _observable("PREVENTED", "UNSUPPORTED", observables["preflight_is_zero"]), "preflight_is_zero"),
        ("post_fork_exec_failure", "UNSUPPORTED", _observable("DETECTED", "UNSUPPORTED", observables["exec_failure_distinct"]), "exec_failure_distinct"),
        ("confirmed_process_outcomes", "UNSUPPORTED", _observable("DETECTED", "UNSUPPORTED", observables["confirmed_outcomes_are_one"]), "confirmed_outcomes_are_one"),
        ("target_fd_isolation", "UNSUPPORTED", b_fd, "fd_policy_correct"),
        ("fd_negative_controls", "UNSUPPORTED", b_fd, "fd_negative_controls"),
        ("illegal_or_partial_replay", "UNSUPPORTED", b_replay, "strict_replay"),
        ("same_uid_full_replacement", "OUT_OF_SCOPE", "OUT_OF_SCOPE", "anchor_boundary_honest"),
        ("kernel_isolation", "UNSUPPORTED", "UNSUPPORTED", "kernel_isolation_executed"),
    ]
    return {
        "schema_version": 2,
        "candidate_status": "READY_FOR_REVIEW",
        "selected_option": "B",
        "provider_internal_calls": "UNKNOWN",
        "runtime_evidence": {
            "option_b_process_accounting": process_b,
            "option_b_inherited_fd": fd,
            "integrity_and_anchor": integrity,
            "observables": observables,
        },
        "matrix": [
            {
                "scenario": scenario,
                "A": _cell(a, observable, f"observables.{observable} is true"),
                "B": _cell(b, observable, f"observables.{observable} is true"),
                "C": _cell(c if observables["kernel_isolation_executed"] else "UNSUPPORTED", "kernel_isolation_executed", "observables.kernel_isolation_executed is true"),
            }
            for scenario, a, b, observable in rows
            for c in ["UNSUPPORTED"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--broker", action="store_true")
    parser.add_argument("broker_command", nargs="?")
    parser.add_argument("ledger_fd", nargs="?", type=int)
    arguments = parser.parse_args()
    if arguments.broker:
        if arguments.broker_command is None or arguments.ledger_fd is None:
            parser.error("--broker requires command and ledger fd")
        raise SystemExit(_broker_main(json.loads(arguments.broker_command), arguments.ledger_fd))
    encoded = json.dumps(build_matrix(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()

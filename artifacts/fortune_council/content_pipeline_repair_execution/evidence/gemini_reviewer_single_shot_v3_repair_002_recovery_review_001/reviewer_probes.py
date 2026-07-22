from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts import agy_gemini_operations as operations


REPO_ROOT = Path(__file__).resolve().parents[5]


def binding(operation_id: str) -> operations.OperationBinding:
    return operations.OperationBinding(
        operation_id=operation_id,
        item_id=f"item-{operation_id}",
        request_id=f"request-{operation_id}",
        run_id="recovery-review",
        candidate_sha256="f" * 64,
    )


def same_user_token_discovery_and_writer_bypass(root: Path) -> dict[str, object]:
    operation_id = "same-user-token"
    claim = operations.claim_operation_namespace(root, binding(operation_id))
    manifest_path, terminal_path, _gate_path = operations.operation_paths(root, operation_id)
    old_manifest = manifest_path.read_bytes()
    target_popen_spawns = 0

    attacker = (
        "import json,sys; from pathlib import Path; "
        "from scripts import agy_gemini_operations as o; "
        "root=Path(sys.argv[1]); op=sys.argv[2]; "
        "token=(root / ('claim.'+op) / 'owner-token').read_text().strip(); "
        "terminal=o.operation_paths(root, op)[1]; "
        "o.write_record_exclusive(terminal, {'foreign':True}, owner_token=token); "
        "print(json.dumps({'token_read':bool(token),'record_written':terminal.exists()}))"
    )

    def launcher(authorize_process_start, mark_process_started):
        nonlocal target_popen_spawns
        authorize_process_start()
        attack = subprocess.run(
            [sys.executable, "-c", attacker, str(root), operation_id],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        target = subprocess.Popen(
            ["/usr/bin/true"],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        target_popen_spawns += 1
        mark_process_started()
        stdout, stderr = target.communicate(timeout=5)
        completed = subprocess.CompletedProcess(
            ["/usr/bin/true"], target.returncode, stdout, stderr
        )
        return attack, completed

    attack_result: subprocess.CompletedProcess[str] | None = None
    completion_error: BaseException | None = None

    def wrapped_launcher(authorize_process_start, mark_process_started):
        nonlocal attack_result
        attack_result, completed = launcher(authorize_process_start, mark_process_started)
        return completed

    try:
        operations.complete_claimed_operation(
            claim,
            wrapped_launcher,
            operations.json_evaluator,
            require_process_start_witness=True,
        )
    except BaseException as error:
        completion_error = error

    foreign_bytes = terminal_path.read_bytes() if terminal_path.exists() else b""
    attacker_payload = (
        json.loads(attack_result.stdout)
        if attack_result is not None and attack_result.returncode == 0
        else None
    )
    return {
        "attacker_started_without_token_argument": True,
        "attacker_returncode": None if attack_result is None else attack_result.returncode,
        "attacker_payload": attacker_payload,
        "target_popen_spawns": target_popen_spawns,
        "completion_error": None if completion_error is None else type(completion_error).__name__,
        "foreign_record_persisted": foreign_bytes == operations.compact_bytes({"foreign": True}) + b"\n",
        "old_manifest_bytes_unchanged": manifest_path.read_bytes() == old_manifest,
    }


def raw_callback_entry_vs_target_spawn(root: Path) -> dict[str, object]:
    operation_id = "raw-callback"
    claim = operations.claim_operation_namespace(root, binding(operation_id))
    _manifest_path, terminal_path, _gate_path = operations.operation_paths(root, operation_id)
    injected = b"raw-callback-entry\n"
    callback_entries = 0
    target_popen_spawns = 0

    def launcher(authorize_process_start, mark_process_started):
        nonlocal callback_entries, target_popen_spawns
        callback_entries += 1
        terminal_path.write_bytes(injected)
        authorize_process_start()
        target = subprocess.Popen(
            ["/usr/bin/true"],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        target_popen_spawns += 1
        mark_process_started()
        stdout, stderr = target.communicate(timeout=5)
        return subprocess.CompletedProcess(["/usr/bin/true"], target.returncode, stdout, stderr)

    completion_error: BaseException | None = None
    try:
        operations.complete_claimed_operation(
            claim,
            launcher,
            operations.json_evaluator,
            require_process_start_witness=True,
        )
    except BaseException as error:
        completion_error = error
    return {
        "callback_entries": callback_entries,
        "target_popen_spawns": target_popen_spawns,
        "raw_bytes_unchanged": terminal_path.read_bytes() == injected,
        "completion_error": None if completion_error is None else type(completion_error).__name__,
    }


def application_non_owner_rejected_before_spawn(root: Path) -> dict[str, object]:
    operation_id = "no-token-api"
    claim = operations.claim_operation_namespace(root, binding(operation_id))
    manifest_path, terminal_path, _gate_path = operations.operation_paths(root, operation_id)
    old_manifest = manifest_path.read_bytes()
    callback_entries = 0
    target_popen_spawns = 0

    def launcher(authorize_process_start, mark_process_started):
        nonlocal callback_entries, target_popen_spawns
        callback_entries += 1
        operations.write_record_exclusive(terminal_path, {"foreign": True})
        authorize_process_start()
        target = subprocess.Popen(["/usr/bin/true"])
        target_popen_spawns += 1
        mark_process_started()
        stdout, stderr = target.communicate(timeout=5)
        return subprocess.CompletedProcess(["/usr/bin/true"], target.returncode, stdout, stderr)

    outcome = operations.complete_claimed_operation(
        claim,
        launcher,
        operations.json_evaluator,
        require_process_start_witness=True,
    )
    return {
        "callback_entries": callback_entries,
        "target_popen_spawns": target_popen_spawns,
        "old_manifest_bytes_unchanged": manifest_path.read_bytes() == old_manifest,
        "process_started": outcome.terminal["process_started"],
        "terminal_status": outcome.terminal["terminal_status"],
        "failure_code": outcome.terminal["failure_code"],
        "gate_status": outcome.gate["status"],
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v3-recovery-review-") as temp:
        root = Path(temp)
        result = {
            "application_non_owner_rejected_before_spawn": application_non_owner_rejected_before_spawn(
                root / "api-denial"
            ),
            "same_user_token_discovery_and_writer_bypass": same_user_token_discovery_and_writer_bypass(
                root / "same-user"
            ),
            "raw_callback_entry_vs_target_spawn": raw_callback_entry_vs_target_spawn(
                root / "raw-callback"
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

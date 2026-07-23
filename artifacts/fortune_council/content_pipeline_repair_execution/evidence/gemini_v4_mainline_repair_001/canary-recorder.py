#!/usr/bin/env python3
"""執行單次 Gemini V4 canary並保存 privacy-safe、可離線重算的 evidence bundle。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts import agy_gemini_v4_broker as broker


RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ok": {"type": "boolean"},
        "transport": {"type": "string", "enum": ["agy-v4-mainline-repair-canary"]},
    },
    "required": ["ok", "transport"],
}
CANARY_ITEM_ID = "gemini-v4-mainline-repair-canary"
CANARY_ATTEMPT_ID = "attempt-1"
SYNTHETIC_EXECUTABLE = b"""#!/bin/sh
printf '%s' '{"ok":true,"transport":"agy-v4-mainline-repair-canary"}'
"""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_frames(ledger_path: Path) -> tuple[list[dict[str, object]], bytes]:
    raw = ledger_path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise RuntimeError("canary ledger is absent or partial")
    frames: list[dict[str, object]] = []
    for line in raw.splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("canary ledger frame is not an object")
        frames.append(value)
    canonical = b"".join(canonical_json(frame) + b"\n" for frame in frames)
    if canonical != raw:
        raise RuntimeError("canary ledger is not canonical JSONL")
    return frames, raw


def make_bundle(
    *,
    result: broker.BrokerResult,
    command: broker.CommandFrame,
    ledger_path: Path,
    cli_version: str,
) -> dict[str, object]:
    frames, raw_ledger = load_frames(ledger_path)
    parsed_result = result.result
    if parsed_result is None:
        raise RuntimeError("canary did not produce a caller result")
    receipt = dict(result.receipt.__dict__)
    control = {
        "replay_status": result.replay_status,
        "process_count": result.process_count,
        "outcome": result.outcome,
        "exit_status": result.exit_status,
        "stdout_sha256": result.stdout_sha256,
        "stderr_sha256": result.stderr_sha256,
        "byte_count": result.byte_count,
        "final_anchor": result.final_anchor,
    }
    return {
        "schema_version": 1,
        "receipt": receipt,
        "command": command.to_dict(),
        "execution": {
            **control,
            "caller_contract_satisfied": result.caller_contract_satisfied,
            "result": parsed_result,
            "errors": list(result.errors),
            "automatic_resend_allowed": result.automatic_resend_allowed,
        },
        "ledger": {
            "encoding": "canonical-jsonl-v1",
            "canonical_frames": frames,
            "ledger_sha256": sha256(raw_ledger),
            "final_anchor": result.final_anchor,
        },
        "control": control,
        "inbox": {
            "schema_version": 1,
            "job_id": result.receipt.operation_id,
            "request_sha256": result.receipt.request_sha256,
            "model": result.receipt.model,
            "result": parsed_result,
        },
        "result_schema": RESULT_SCHEMA,
        "executable_identity": {
            "tool": "agy",
            "cli_version": cli_version,
            "sha256": result.receipt.executable_digest,
        },
        "invocation_policy": {
            "target_invocations": sum(frame.get("event_type") == "EXEC_CONFIRMED" for frame in frames),
            "fallback_invocations": 0,
            "automatic_retry_invocations": 0,
            "automatic_resend_allowed": result.automatic_resend_allowed,
        },
        "privacy": {
            "prompt_saved": False,
            "credential_saved": False,
            "full_environment_saved": False,
            "cli_log_saved": False,
            "executable_path_saved": False,
        },
    }


def record(
    *,
    executable: Path,
    expected_executable_digest: str,
    cli_version: str,
    model: str,
    prompt: bytes,
    output: Path,
) -> None:
    executable_bytes = executable.read_bytes()
    executable_digest = sha256(executable_bytes)
    if executable_digest != expected_executable_digest:
        raise RuntimeError("executable digest differs from the authorized identity")
    request_sha256 = sha256(prompt)
    operation_id = request_sha256[:40]
    model_label = broker.AGY_MODEL_LABELS[model]
    command = broker.CommandFrame(
        broker.COMMAND_SCHEMA_VERSION,
        operation_id,
        CANARY_ITEM_ID,
        CANARY_ATTEMPT_ID,
        executable_digest,
        request_sha256,
        len(prompt),
        120_000,
        broker.ANTIGRAVITY_CLI_PROFILE,
        model_label,
        broker.PUBLIC_SANITIZED,
    )
    command.validate()
    with tempfile.TemporaryDirectory(prefix="gemini-v4-canary-recorder-") as directory:
        run_root = Path(directory)
        result = broker.run_single_shot(
            operation_id=operation_id,
            item_id=CANARY_ITEM_ID,
            attempt_id=CANARY_ATTEMPT_ID,
            request_sha256=request_sha256,
            model=model,
            executable=executable,
            target_profile=broker.ANTIGRAVITY_CLI_PROFILE,
            expected_executable_digest=executable_digest,
            raw_request=prompt,
            response_schema=RESULT_SCHEMA,
            timeout_milliseconds=120_000,
            ledger_path=run_root / "ledger.jsonl",
            anchor_store=broker.FileAnchorStore(run_root / "anchors"),
        )
        if (
            result.replay_status != "COMPLETE"
            or result.process_count != 1
            or not result.caller_contract_satisfied
            or result.result is None
            or result.automatic_resend_allowed
        ):
            raise RuntimeError(
                f"canary failed closed: {result.replay_status}/{result.process_count}/{','.join(result.errors)}"
            )
        atomic_write_json(
            output,
            make_bundle(result=result, command=command, ledger_path=run_root / "ledger.jsonl", cli_version=cli_version),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--executable", type=Path)
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--expected-executable-sha256")
    parser.add_argument("--cli-version", default="1.1.5")
    parser.add_argument("--model", choices=sorted(broker.AGY_MODEL_LABELS), default="gemini-3.5-flash")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.synthetic and args.expected_executable_sha256 is None:
        print("--expected-executable-sha256 is required with --executable", file=sys.stderr)
        return 2
    prompt = sys.stdin.buffer.read(broker.MAX_AGY_PROMPT_BYTES + 1)
    if not prompt:
        print("canary prompt is required on stdin", file=sys.stderr)
        return 2
    try:
        if args.synthetic:
            with tempfile.TemporaryDirectory(prefix="gemini-v4-synthetic-agy-") as directory:
                executable = Path(directory) / "agy"
                executable.write_bytes(SYNTHETIC_EXECUTABLE)
                executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
                record(
                    executable=executable,
                    expected_executable_digest=sha256(SYNTHETIC_EXECUTABLE),
                    cli_version=args.cli_version,
                    model=args.model,
                    prompt=prompt,
                    output=args.output,
                )
        else:
            assert args.executable is not None
            record(
                executable=args.executable,
                expected_executable_digest=args.expected_executable_sha256,
                cli_version=args.cli_version,
                model=args.model,
                prompt=prompt,
                output=args.output,
            )
    except (KeyError, OSError, ValueError, RuntimeError) as error:
        print(f"canary recorder rejected execution: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "RECORDED", "output": args.output.name}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

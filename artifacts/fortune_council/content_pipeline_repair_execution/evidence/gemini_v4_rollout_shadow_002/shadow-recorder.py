#!/usr/bin/env python3
"""記錄單次 Gemini V4 Shadow-002，輸出不含 raw stdout 的 evidence bundle。"""

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


MODEL = "gemini-3.5-flash"
MODEL_LABEL = "Gemini 3.5 Flash (Low)"
ITEM_ID = "gemini-v4-rollout-shadow-canary-002"
ATTEMPT_ID = "shadow-002-attempt-1"
UPSTREAM_MAIN_SHA = "1dd80978dc4c6facbb588aa8869bec8362e606a3"
OUTPUT_BINDING_REPAIR_SHA = "4e04e82506c4a1c2a3846640f9504fca972ae9fd"
OUTPUT_BINDING_REVIEW_SHA = "1dd80978dc4c6facbb588aa8869bec8362e606a3"
PREVIOUS_BLOCKED_ROLLOUT_SHA = "90559641a9460c26eb7c168ebbb78ce4be2a51fa"
ENCODINGS = (
    "canonical-json-v1",
    "canonical-json-newline-v1",
    "sorted-indent2-json-newline-v1",
)
RESULT = {
    "ok": True,
    "transport": "agy-v4-rollout-shadow-canary-002",
}
RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ok": {"type": "boolean", "enum": [True]},
        "transport": {
            "type": "string",
            "enum": ["agy-v4-rollout-shadow-canary-002"],
        },
    },
    "required": ["ok", "transport"],
}


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def encode_result(value: object, encoding: str) -> bytes:
    if encoding == "canonical-json-v1":
        return canonical_json(value)
    if encoding == "canonical-json-newline-v1":
        return canonical_json(value) + b"\n"
    if encoding == "sorted-indent2-json-newline-v1":
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8")
            + b"\n"
        )
    raise ValueError("unknown stdout encoding")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_frames(ledger_path: Path) -> tuple[list[dict[str, object]], bytes]:
    raw = ledger_path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise RuntimeError("shadow ledger is absent or partial")
    frames: list[dict[str, object]] = []
    for line in raw.splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("shadow ledger frame is not an object")
        frames.append(value)
    canonical = b"".join(canonical_json(frame) + b"\n" for frame in frames)
    if canonical != raw:
        raise RuntimeError("shadow ledger is not canonical JSONL")
    return frames, raw


def detect_encoding(result: object, raw_result: bytes | None) -> str:
    if raw_result is None:
        raise RuntimeError("broker did not preserve the verified stdout bytes")
    matches = [
        encoding
        for encoding in ENCODINGS
        if encode_result(result, encoding) == raw_result
    ]
    if len(matches) != 1:
        raise RuntimeError("stdout does not match one precommitted encoding")
    return matches[0]


def make_bundle(
    *,
    result: broker.BrokerResult,
    command: broker.CommandFrame,
    ledger_path: Path,
    evidence_kind: str,
    cli_version: str,
) -> dict[str, object]:
    frames, raw_ledger = load_frames(ledger_path)
    parsed_result = result.result
    if parsed_result is None:
        raise RuntimeError("shadow did not produce a caller result")
    output_encoding = detect_encoding(parsed_result, result.result_json)
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
        "evidence_kind": evidence_kind,
        "rollout_identity": {
            "upstream_main_sha": UPSTREAM_MAIN_SHA,
            "output_binding_repair_sha": OUTPUT_BINDING_REPAIR_SHA,
            "output_binding_review_sha": OUTPUT_BINDING_REVIEW_SHA,
            "output_binding_review_verdict": "GO",
            "previous_blocked_rollout_sha": PREVIOUS_BLOCKED_ROLLOUT_SHA,
            "chain_id": "CONTENT-GEMINI-V4-ROLLOUT-002",
        },
        "receipt": dict(result.receipt.__dict__),
        "command": command.to_dict(),
        "execution": {
            **control,
            "caller_contract_satisfied": result.caller_contract_satisfied,
            "result": parsed_result,
            "output_encoding": output_encoding,
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
            "kind": evidence_kind,
            "tool": "agy" if evidence_kind == "production" else "synthetic-agy",
            "cli_version": cli_version,
            "sha256": result.receipt.executable_digest,
        },
        "invocation_policy": {
            "target_invocations": sum(
                frame.get("event_type") == "EXEC_CONFIRMED" for frame in frames
            ),
            "fallback_invocations": 0,
            "automatic_retry_invocations": 0,
            "automatic_resend_allowed": result.automatic_resend_allowed,
        },
        "privacy": {
            "raw_stdout_saved": False,
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
    prompt: bytes,
    output: Path,
    evidence_kind: str,
) -> None:
    executable_digest = sha256(executable.read_bytes())
    if executable_digest != expected_executable_digest:
        raise RuntimeError("executable digest differs from the authorized identity")
    if evidence_kind == "production" and cli_version != "1.1.5":
        raise RuntimeError("CLI version differs from the authorized identity")
    request_sha256 = sha256(prompt)
    operation_id = request_sha256[:40]
    command = broker.CommandFrame(
        broker.COMMAND_SCHEMA_VERSION,
        operation_id,
        ITEM_ID,
        ATTEMPT_ID,
        executable_digest,
        request_sha256,
        len(prompt),
        120_000,
        broker.ANTIGRAVITY_CLI_PROFILE,
        MODEL_LABEL,
        broker.PUBLIC_SANITIZED,
    )
    command.validate()
    with tempfile.TemporaryDirectory(prefix="gemini-v4-shadow-002-recorder-") as directory:
        run_root = Path(directory)
        result = broker.run_single_shot(
            operation_id=operation_id,
            item_id=ITEM_ID,
            attempt_id=ATTEMPT_ID,
            request_sha256=request_sha256,
            model=MODEL,
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
            or result.result != RESULT
            or result.automatic_resend_allowed
        ):
            raise RuntimeError(
                "shadow failed closed: "
                f"{result.replay_status}/{result.process_count}/"
                f"{','.join(result.errors)}"
            )
        atomic_write_json(
            output,
            make_bundle(
                result=result,
                command=command,
                ledger_path=run_root / "ledger.jsonl",
                evidence_kind=evidence_kind,
                cli_version=cli_version,
            ),
        )


def synthetic_executable(encoding: str) -> bytes:
    encoded = encode_result(RESULT, encoding)
    return (
        b"#!/usr/bin/env python3\n"
        b"import sys\n"
        b"arguments = sys.argv[1:]\n"
        b"if arguments[:2] != ['--model', 'Gemini 3.5 Flash (Low)']:\n"
        b"    raise SystemExit(31)\n"
        b"if '--print' not in arguments or not arguments[arguments.index('--print') + 1]:\n"
        b"    raise SystemExit(32)\n"
        b"if sys.stdin.buffer.read():\n"
        b"    raise SystemExit(33)\n"
        + f"sys.stdout.buffer.write({encoded!r})\n".encode("utf-8")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--executable", type=Path)
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--expected-executable-sha256")
    parser.add_argument("--cli-version", default="1.1.5")
    parser.add_argument(
        "--synthetic-encoding",
        choices=ENCODINGS,
        default=ENCODINGS[0],
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.synthetic and args.expected_executable_sha256 is None:
        print(
            "--expected-executable-sha256 is required with --executable",
            file=sys.stderr,
        )
        return 2
    prompt = sys.stdin.buffer.read(broker.MAX_AGY_PROMPT_BYTES + 1)
    if not prompt:
        print("shadow prompt is required on stdin", file=sys.stderr)
        return 2
    try:
        if args.synthetic:
            fixture = synthetic_executable(args.synthetic_encoding)
            with tempfile.TemporaryDirectory(
                prefix="gemini-v4-shadow-002-synthetic-agy-"
            ) as directory:
                executable = Path(directory) / "agy"
                executable.write_bytes(fixture)
                executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
                record(
                    executable=executable,
                    expected_executable_digest=sha256(fixture),
                    cli_version="1.1.5-contract",
                    prompt=prompt,
                    output=args.output,
                    evidence_kind="synthetic",
                )
        else:
            assert args.executable is not None
            record(
                executable=args.executable,
                expected_executable_digest=args.expected_executable_sha256,
                cli_version=args.cli_version,
                prompt=prompt,
                output=args.output,
                evidence_kind="production",
            )
    except (KeyError, OSError, ValueError, RuntimeError) as error:
        print(f"shadow recorder rejected execution: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "RECORDED", "output": args.output.name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

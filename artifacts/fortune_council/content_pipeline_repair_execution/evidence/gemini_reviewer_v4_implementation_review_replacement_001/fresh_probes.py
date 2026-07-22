#!/usr/bin/env python3
"""以 production run_single_shot 重現 executable digest pre-fork race。"""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from scripts import agy_gemini_v4_broker as broker


def _target_source(marker: Path, revision: str) -> str:
    return (
        f"#!{sys.executable}\n"
        "from pathlib import Path\n"
        f"marker = Path({str(marker)!r})\n"
        "count = int(marker.read_text()) if marker.exists() else 0\n"
        "marker.write_text(str(count + 1))\n"
        f"print({json.dumps({'ok': True, 'revision': revision})!r})\n"
    )


def run_probe() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="gemini-v4-review-race-") as raw_root:
        root = Path(raw_root)
        executable = root / "fake-target"
        marker = root / "target-launch-count"
        executable.write_text(_target_source(marker, "precheck"), encoding="utf-8")
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

        real_popen = subprocess.Popen
        broker_launches = 0

        def mutate_before_broker_exec(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
            nonlocal broker_launches
            broker_launches += 1
            if broker_launches == 1:
                executable.write_text(_target_source(marker, "raced"), encoding="utf-8")
                executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            return real_popen(*args, **kwargs)

        ledger_path = root / "ledger.jsonl"
        anchor_store = broker.FileAnchorStore(root / "anchors")
        with mock.patch.object(broker.subprocess, "Popen", side_effect=mutate_before_broker_exec):
            result = broker.run_single_shot(
                operation_id="operation-digest-race",
                item_id="item-review",
                attempt_id="attempt-1",
                request_sha256="a" * 64,
                model="synthetic-review-model",
                executable=executable,
                raw_request=b"synthetic offline request",
                response_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                },
                timeout_milliseconds=1_000,
                ledger_path=ledger_path,
                anchor_store=anchor_store,
            )

        events = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
        anchor = anchor_store.load("operation-digest-race", "attempt-1")
        replay = broker.replay_ledger(
            ledger_path,
            broker.Binding("operation-digest-race", "item-review", "attempt-1"),
            anchor,
        )
        launch_count = int(marker.read_text()) if marker.exists() else 0
        observed = {
            "ledger_event_types": [event["event_type"] for event in events],
            "ledger_event_count": len(events),
            "anchor_present": anchor is not None,
            "target_launch_count": launch_count,
            "run_result": {
                "replay_status": result.replay_status,
                "process_count": result.process_count,
                "complete": result.replay_status == "COMPLETE",
                "automatic_resend_allowed": result.automatic_resend_allowed,
                "errors": list(result.errors),
            },
            "fresh_replay": {
                "status": replay.status,
                "process_count": replay.process_count,
                "complete": replay.complete,
                "automatic_resend_allowed": replay.automatic_resend_allowed,
                "errors": list(replay.errors),
            },
        }
        reproduced = (
            observed["ledger_event_types"] == ["OPERATION_CREATED"]
            and launch_count == 0
            and result.replay_status == "INVALID"
            and result.process_count == "UNKNOWN"
            and replay.status == "INVALID"
            and replay.process_count == "UNKNOWN"
        )
        return {
            "probe": "production_run_single_shot_executable_digest_race_after_operation_created",
            "offline_synthetic_only": True,
            "observed": observed,
            "required": {
                "ledger_event_types": [
                    "OPERATION_CREATED",
                    "BROKER_ATTEMPTED",
                    "BROKER_ABORTED",
                ],
                "broker_aborted_outcome": "CRASH_BEFORE_FORK",
                "target_launch_count": 0,
                "replay_status": "BLOCKED",
                "process_count": 0,
            },
            "counterexample_reproduced": reproduced,
            "verdict": "NO_GO" if reproduced else "CONTINUE_REVIEW",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_probe()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["counterexample_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

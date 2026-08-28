#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: run_and_record.py NAME OUTDIR -- COMMAND...", file=sys.stderr)
        return 64
    name = sys.argv[1]
    outdir = Path(sys.argv[2])
    if sys.argv[3] != "--" or len(sys.argv) == 4:
        print("missing command separator", file=sys.stderr)
        return 64
    command = sys.argv[4:]
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{name}.command.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    finished = datetime.now(timezone.utc).isoformat()
    (outdir / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (outdir / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (outdir / f"{name}.returncode.txt").write_text(f"{completed.returncode}\n", encoding="utf-8")
    receipt = {
        "name": name,
        "command": command,
        "started_at": started,
        "finished_at": finished,
        "returncode": completed.returncode,
        "stdout_bytes": len(completed.stdout.encode("utf-8")),
        "stderr_bytes": len(completed.stderr.encode("utf-8")),
    }
    (outdir / f"{name}.receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

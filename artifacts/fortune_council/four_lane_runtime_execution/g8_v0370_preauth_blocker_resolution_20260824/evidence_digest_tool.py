#!/usr/bin/env python3
"""以 evidence root 相對路徑寫入或驗證可攜式 sha256 manifest。"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "evidence-digests.sha256"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file() and path != MANIFEST
    )


def write_manifest() -> None:
    rows = [
        f"{file_digest(path)}  {path.relative_to(ROOT).as_posix()}"
        for path in evidence_files()
    ]
    MANIFEST.write_text("\n".join(rows) + "\n", encoding="utf-8")


def verify_manifest() -> None:
    observed: set[str] = set()
    for line_number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        digest, separator, relative = line.partition("  ")
        pure = PurePosixPath(relative)
        if (
            separator != "  "
            or len(digest) != 64
            or not relative
            or pure.is_absolute()
            or ".." in pure.parts
        ):
            raise SystemExit(f"invalid manifest row: {line_number}")
        path = ROOT.joinpath(*pure.parts)
        if not path.is_file() or file_digest(path) != digest:
            raise SystemExit(f"digest mismatch: {relative}")
        observed.add(relative)
    expected = {path.relative_to(ROOT).as_posix() for path in evidence_files()}
    if observed != expected:
        raise SystemExit("manifest file set mismatch")
    print(f"evidence_digest_verification=PASS files={len(observed)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("write", "verify"))
    args = parser.parse_args()
    if args.action == "write":
        write_manifest()
    else:
        verify_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

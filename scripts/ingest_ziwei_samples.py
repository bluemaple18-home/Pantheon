from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Iterable


def iter_json_records(source: Path) -> Iterable[dict]:
    for path in sorted(source.rglob("*")):
        if path.suffix not in {".json", ".jsonl"}:
            continue
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        yield json.loads(line)
        else:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list):
                yield from payload
            else:
                yield payload


def ingest(source: Path, db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ziwei_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT,
                payload TEXT NOT NULL
            )
            """
        )
        count = 0
        for record in iter_json_records(source):
            source_key = str(record.get("id") or record.get("key") or "")
            connection.execute(
                "INSERT INTO ziwei_samples (source_key, payload) VALUES (?, ?)",
                (source_key, json.dumps(record, ensure_ascii=False)),
            )
            count += 1
        connection.commit()
        return count
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ziwei-doushu sample JSON into SQLite.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args()
    count = ingest(args.source, args.db)
    print(f"ingested={count} db={args.db}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""依每日 URL inspection snapshot 驗證發布後索引狀態。"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit


FLAT_REQUIRED_FIELDS = (
    "url",
    "verdict",
    "coverage_state",
    "indexing_state",
    "robots_txt_state",
    "page_fetch_state",
    "user_canonical",
    "google_canonical",
)
GSC_INDEX_FIELDS = (
    "verdict",
    "coverageState",
    "indexingState",
    "robotsTxtState",
    "pageFetchState",
    "userCanonical",
    "googleCanonical",
)
FAIL_CATEGORIES = {
    "overdue_discovered",
    "overdue_unknown",
    "blocked_by_noindex",
    "blocked_by_robots",
    "fetch_failed",
    "canonical_split",
}


class SnapshotContractError(ValueError):
    """Snapshot 格式不符合輸入契約。"""


def parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise SnapshotContractError(f"{field} 必須是 ISO 日期字串")
    try:
        if field.endswith(".published_at"):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotContractError(f"{field} 不是有效 ISO 日期：{value}") from exc


def normalized_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def canonical_url(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    parsed = urlsplit(str(value).strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def contains_any(value: Any, needles: tuple[str, ...]) -> bool:
    text = normalized_text(value)
    return any(needle in text for needle in needles)


def published_date(
    row: dict[str, Any],
    index: int,
    collection: str,
    published_dates: dict[str, Any],
) -> date:
    if "published_date" in row:
        return parse_date(
            row["published_date"],
            f"{collection}[{index}].published_date",
        )
    if "published_at" in row:
        return parse_date(row["published_at"], f"{collection}[{index}].published_at")
    if row["url"] in published_dates:
        return parse_date(
            published_dates[row["url"]],
            f"published_dates[{row['url']!r}]",
        )
    raise SnapshotContractError(
        f"{collection}[{index}] 缺少發布日；請提供 record 的 published_date/"
        "published_at 或 --published-dates URL mapping"
    )


def validate_flat_row(row: Any, index: int) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise SnapshotContractError(f"urls[{index}] 必須是物件")
    missing = [field for field in FLAT_REQUIRED_FIELDS if field not in row]
    if missing:
        raise SnapshotContractError(f"urls[{index}] 缺少欄位：{', '.join(missing)}")
    if not isinstance(row["url"], str) or not row["url"].strip():
        raise SnapshotContractError(f"urls[{index}].url 必須是非空字串")
    return row


def normalize_gsc_record(record: Any, index: int) -> dict[str, Any]:
    path = f"records[{index}]"
    if not isinstance(record, dict):
        raise SnapshotContractError(f"{path} 必須是物件")
    if not isinstance(record.get("url"), str) or not record["url"].strip():
        raise SnapshotContractError(f"{path}.url 必須是非空字串")
    inspection = record.get("inspection")
    if not isinstance(inspection, dict):
        raise SnapshotContractError(f"{path}.inspection 必須是物件")
    if "available" not in inspection or not isinstance(inspection["available"], bool):
        raise SnapshotContractError(f"{path}.inspection.available 必須是布林值")

    index_data = inspection.get("index")
    if inspection["available"]:
        if not isinstance(index_data, dict):
            raise SnapshotContractError(f"{path}.inspection.index 必須是物件")
        missing = [field for field in GSC_INDEX_FIELDS if field not in index_data]
        if missing:
            raise SnapshotContractError(
                f"{path}.inspection.index 缺少欄位：{', '.join(missing)}"
            )
    elif not isinstance(index_data, dict):
        index_data = {}

    row = {
        "url": record["url"],
        "verdict": index_data.get("verdict"),
        "coverage_state": index_data.get("coverageState"),
        "indexing_state": index_data.get("indexingState"),
        "robots_txt_state": index_data.get("robotsTxtState"),
        "page_fetch_state": index_data.get("pageFetchState"),
        "user_canonical": index_data.get("userCanonical"),
        "google_canonical": index_data.get("googleCanonical"),
    }
    for field in ("published_date", "published_at"):
        if field in record:
            row[field] = record[field]
    return row


def snapshot_rows(snapshot: Any) -> tuple[date, str, list[dict[str, Any]]]:
    if not isinstance(snapshot, dict):
        raise SnapshotContractError("snapshot 根節點必須是物件")
    if "observation_date" in snapshot or "records" in snapshot:
        if "observation_date" not in snapshot:
            raise SnapshotContractError("snapshot 缺少 observation_date")
        if not isinstance(snapshot.get("records"), list):
            raise SnapshotContractError("snapshot.records 必須是陣列")
        observation_date = parse_date(snapshot["observation_date"], "observation_date")
        return (
            observation_date,
            "records",
            [
                normalize_gsc_record(record, index)
                for index, record in enumerate(snapshot["records"])
            ],
        )

    if "inspection_date" not in snapshot:
        raise SnapshotContractError("snapshot 缺少 observation_date 或 inspection_date")
    if not isinstance(snapshot.get("urls"), list):
        raise SnapshotContractError("snapshot.urls 必須是陣列")
    inspection_date = parse_date(snapshot["inspection_date"], "inspection_date")
    return (
        inspection_date,
        "urls",
        [validate_flat_row(row, index) for index, row in enumerate(snapshot["urls"])],
    )


def classify(row: dict[str, Any], age_days: int, observation_days: int) -> str:
    if contains_any(
        row["indexing_state"],
        (
            "noindex",
            "blocked by meta tag",
            "blocked by http header",
            "excluded by 'noindex'",
            "excluded by noindex",
        ),
    ):
        return "blocked_by_noindex"
    robots_blocked = contains_any(
        row["robots_txt_state"],
        ("blocked", "disallowed", "not allowed", "robots.txt unavailable"),
    ) or contains_any(row["page_fetch_state"], ("blocked robots txt", "blocked by robots"))
    if robots_blocked:
        return "blocked_by_robots"
    if contains_any(
        row["page_fetch_state"],
        ("failed", "error", "unreachable", "not found", "server error"),
    ):
        return "fetch_failed"

    user_canonical = canonical_url(row["user_canonical"])
    google_canonical = canonical_url(row["google_canonical"])
    if user_canonical and google_canonical and user_canonical != google_canonical:
        return "canonical_split"

    verdict = normalized_text(row["verdict"])
    coverage = normalized_text(row["coverage_state"])
    if verdict == "pass":
        return "indexed"
    if age_days <= observation_days:
        return "new_under_observation"
    if "discovered" in coverage:
        return "overdue_discovered"
    return "overdue_unknown"


def evaluate_snapshot(
    snapshot: Any,
    observation_days: int,
    published_dates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if observation_days < 0:
        raise SnapshotContractError("observation_days 不得小於 0")
    if published_dates is None:
        published_dates = {}
    if not isinstance(published_dates, dict):
        raise SnapshotContractError("published dates 必須是 URL→ISO date JSON 物件")

    inspection_date, collection, rows = snapshot_rows(snapshot)
    results: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        publication_date = published_date(row, index, collection, published_dates)
        age_days = (inspection_date - publication_date).days
        if age_days < 0:
            raise SnapshotContractError(
                f"{collection}[{index}] 的發布日晚於 observation/inspection date"
            )
        category = classify(row, age_days, observation_days)
        results.append(
            {
                "url": row["url"],
                "published_date": publication_date.isoformat(),
                "age_days": age_days,
                "category": category,
                "severity": "fail"
                if category in FAIL_CATEGORIES
                else ("warning" if category == "new_under_observation" else "pass"),
            }
        )

    counts = Counter(result["category"] for result in results)
    failed = any(result["severity"] == "fail" for result in results)
    warnings = sum(result["severity"] == "warning" for result in results)
    return {
        "status": "FAIL" if failed else ("WARNING" if warnings else "PASS"),
        "inspection_date": inspection_date.isoformat(),
        "observation_days": observation_days,
        "total": len(results),
        "counts": dict(sorted(counts.items())),
        "results": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="每日 URL inspection snapshot JSON")
    parser.add_argument(
        "--observation-days",
        type=int,
        default=7,
        help="索引觀察天數（預設：7）",
    )
    parser.add_argument(
        "--published-dates",
        type=Path,
        help="URL→ISO date 的 JSON mapping；record 未帶發布日時必填",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="僅輸出 machine-readable JSON",
    )
    return parser.parse_args(argv)


def load_snapshot(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotContractError(f"找不到 snapshot：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotContractError(f"snapshot 不是有效 JSON：{exc.msg}") from exc


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        published_dates = load_snapshot(args.published_dates) if args.published_dates else {}
        report = evaluate_snapshot(
            load_snapshot(args.snapshot),
            args.observation_days,
            published_dates,
        )
    except (SnapshotContractError, OSError) as exc:
        error = {"status": "ERROR", "error": str(exc)}
        if args.json:
            print(json.dumps(error, ensure_ascii=False, sort_keys=True))
        else:
            print(f"seo publish gate: ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"seo publish gate: {report['status']} "
            f"({report['total']} URLs, observation={report['observation_days']} days)"
        )
        for result in report["results"]:
            print(
                f"- [{result['severity'].upper()}] {result['category']}: "
                f"{result['url']} (age={result['age_days']} days)"
            )
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""抓取 Pantheon 每日 finalized GSC page/query 快照。"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.gsc_client import DEFAULT_MAX_ROWS, GscReadonlyClient, access_token
from scripts.gsc_opportunity_brief import choose_single_property


def visible_row_totals(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    return {
        "rows": len(rows),
        "pages": len({str(row.get("keys", [""])[0]) for row in rows if row.get("keys")}),
        "queries": len(
            {
                str(row["keys"][1])
                for row in rows
                if isinstance(row.get("keys"), list) and len(row["keys"]) > 1
            }
        ),
        "clicks": sum(float(row.get("clicks") or 0) for row in rows),
        "impressions": sum(float(row.get("impressions") or 0) for row in rows),
    }


def build_snapshot(
    *,
    property_url: str,
    start_date: str,
    end_date: str,
    rows: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    page_count: int,
    fetched_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "google_search_console",
        "property": property_url,
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ["page", "query"],
        "page_filter": {"operator": "contains", "expression": "/articles/"},
        "data_state": "final",
        "fetched_at": fetched_at,
        "pagination": {"pages": page_count, "complete": not warnings},
        "visible_row_totals": visible_row_totals(rows),
        "warnings": warnings,
        "rows": rows,
    }


def snapshot_path(output_root: Path, property_url: str, start_date: str, end_date: str) -> Path:
    property_slug = property_url.removeprefix("sc-domain:").replace("/", "_").replace(":", "_")
    filename = f"{start_date}.json" if start_date == end_date else f"{start_date}_{end_date}.json"
    return output_root / property_slug / filename


def write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    finalized_day = date.today() - timedelta(days=3)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default=finalized_day.isoformat())
    parser.add_argument("--end-date", default=finalized_day.isoformat())
    parser.add_argument("--property")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--output-root", type=Path, default=Path(".work/gsc-data/daily"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.start_date > args.end_date:
        raise SystemExit("--start-date 不得晚於 --end-date")

    client = GscReadonlyClient(access_token())
    properties = client.list_properties()
    property_url = args.property or choose_single_property(properties)
    accessible = {str(item.get("siteUrl") or "") for item in properties}
    if property_url not in accessible:
        raise SystemExit(f"指定的 GSC property 無法存取：{property_url}")

    output = snapshot_path(args.output_root, property_url, args.start_date, args.end_date)
    if output.exists() and not args.force:
        print(json.dumps({"status": "already_exists", "output": str(output)}, ensure_ascii=False))
        return 0

    rows, warnings, page_count = client.query_all(
        property_url,
        args.start_date,
        args.end_date,
        max_rows=args.max_rows,
    )
    if not rows:
        warnings.append(
            {
                "reason_code": "NO_ROWS",
                "stage": "gsc_query",
                "record": property_url,
                "impact_count": 0,
            }
        )
    snapshot = build_snapshot(
        property_url=property_url,
        start_date=args.start_date,
        end_date=args.end_date,
        rows=rows,
        warnings=warnings,
        page_count=page_count,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    write_snapshot(output, snapshot)
    print(
        json.dumps(
            {
                "status": "ok" if not warnings else "partial",
                "property": property_url,
                "dates": [args.start_date, args.end_date],
                "rows": len(rows),
                "warnings": len(warnings),
                "output": str(output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not warnings else 2


if __name__ == "__main__":
    raise SystemExit(main())

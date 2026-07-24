#!/usr/bin/env python3
"""建立 Pantheon GSC SEO copy 優化 brief；只讀取 Search Console。"""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.parse
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from scripts.gsc_client import GscReadonlyClient, access_token


MAX_GSC_PAGES = 5
MAX_BRIEF_BYTES = 8192


class BriefSizeError(ValueError):
    """brief 超過允許大小。"""


def compact_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_bounded_json(path: Path, payload: object, max_bytes: int = MAX_BRIEF_BYTES) -> None:
    data = compact_json_bytes(payload)
    file_size = len(data) + 1
    if file_size > max_bytes:
        raise BriefSizeError(f"brief is {file_size} bytes; limit is {max_bytes}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data + b"\n")


def choose_single_property(entries: list[dict[str, Any]]) -> str:
    urls = [str(item.get("siteUrl") or "") for item in entries if item.get("siteUrl")]
    if len(urls) != 1:
        raise ValueError(f"expected exactly one accessible GSC property, found {len(urls)}")
    return urls[0]


def select_opportunities(
    rows: list[dict[str, Any]],
    *,
    min_impressions: int,
    max_ctr: float,
    min_position: float = 4.0,
    max_position: float = 20.0,
    max_pages: int = MAX_GSC_PAGES,
) -> list[dict[str, Any]]:
    """把 page/query rows 聚合成頁面機會，依可改善點擊數排序。"""
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"clicks": 0.0, "impressions": 0.0, "position_weight": 0.0, "queries": []}
    )
    for row in rows:
        keys = row.get("keys") or []
        if not keys:
            continue
        page = str(keys[0])
        query = str(keys[1]) if len(keys) > 1 else ""
        impressions = float(row.get("impressions") or 0)
        clicks = float(row.get("clicks") or 0)
        position = float(row.get("position") or 0)
        bucket = grouped[page]
        bucket["clicks"] += clicks
        bucket["impressions"] += impressions
        bucket["position_weight"] += position * impressions
        if query:
            bucket["queries"].append({"query": query, "impressions": int(impressions), "clicks": int(clicks)})

    opportunities = []
    for page, bucket in grouped.items():
        impressions = float(bucket["impressions"])
        if impressions <= 0:
            continue
        clicks = float(bucket["clicks"])
        ctr = clicks / impressions
        position = float(bucket["position_weight"]) / impressions
        if impressions < min_impressions or ctr > max_ctr or not min_position <= position <= max_position:
            continue
        queries = sorted(bucket["queries"], key=lambda item: (-item["impressions"], item["query"]))[:3]
        opportunities.append(
            {
                "page": page,
                "clicks": int(clicks),
                "impressions": int(impressions),
                "ctr": round(ctr, 6),
                "position": round(position, 2),
                "opportunity_score": round(impressions * (max_ctr - ctr), 2),
                "queries": queries,
            }
        )
    limit = min(max_pages, MAX_GSC_PAGES)
    return sorted(opportunities, key=lambda item: (-item["opportunity_score"], -item["impressions"], item["page"]))[:limit]


def load_article_inventory(repo_root: Path) -> list[dict[str, Any]]:
    script = """
import { getArticlePath, listArticleRecords } from './app/web/static/article-registry.js';
console.log(JSON.stringify(listArticleRecords().map((article) => ({
  id: article.id,
  path: getArticlePath(article),
  slug: article.slug,
  title: article.title,
  description: article.description,
  answer: article.answer,
}))));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return list(json.loads(result.stdout))


def find_source_file(repo_root: Path, article: dict[str, Any]) -> str:
    candidates = [repo_root / "app/web/static/article-registry.js", *sorted((repo_root / "app/web/static").glob("article-expansion-*.js"))]
    needles = [f'"{article["id"]}"', f'"{article["slug"]}"']
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            return path.relative_to(repo_root).as_posix()
    return "app/web/static/article-registry.js"


def attach_current_content(repo_root: Path, selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory = load_article_inventory(repo_root)
    by_path = {str(item["path"]).rstrip("/"): item for item in inventory}
    attached = []
    for opportunity in selected:
        parsed = urllib.parse.urlsplit(str(opportunity["page"]))
        article = by_path.get(parsed.path.rstrip("/"))
        if not article:
            continue
        attached.append(
            {
                **opportunity,
                "article_id": article["id"],
                "canonical_path": article["path"],
                "source_file": find_source_file(repo_root, article),
                "current": {
                    "title": article["title"],
                    "description": article["description"],
                    "answer": article["answer"],
                },
            }
        )
    return attached


def build_brief(
    repo_root: Path,
    run_id: str,
    property_url: str,
    start_date: str,
    end_date: str,
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "optimize",
        "scope": "seo_copy_only",
        "source": {"type": "gsc", "property": property_url, "start_date": start_date, "end_date": end_date},
        "allowed_fields": ["title", "description", "answer"],
        "articles": attach_current_content(repo_root, selected),
    }


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start-date", default=(today - timedelta(days=30)).isoformat())
    parser.add_argument("--end-date", default=(today - timedelta(days=3)).isoformat())
    parser.add_argument("--min-impressions", type=int, default=100)
    parser.add_argument("--max-ctr", type=float, default=0.03)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    client = GscReadonlyClient(access_token())
    property_url = choose_single_property(client.list_properties())
    rows = client.query(property_url, args.start_date, args.end_date)
    selected = select_opportunities(rows, min_impressions=args.min_impressions, max_ctr=args.max_ctr)
    brief = build_brief(repo_root, args.run_id, property_url, args.start_date, args.end_date, selected)
    output = args.output or repo_root / ".work" / "gsc-copy" / args.run_id / "brief.json"
    write_bounded_json(output, brief)
    print(json.dumps({"run_id": args.run_id, "property": property_url, "selected": len(brief["articles"]), "brief": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

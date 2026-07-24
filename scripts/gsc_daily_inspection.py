#!/usr/bin/env python3
"""每日記錄 Pantheon URL 索引狀態與 Breadcrumb URL 變化。"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

from scripts.gsc_client import GscReadonlyClient, access_token
from scripts.gsc_daily_fetch import write_snapshot
from scripts.gsc_opportunity_brief import choose_single_property


DEFAULT_SITEMAP_URL = "https://mysticpantheon.com/sitemap.xml"
DEFAULT_MAX_URLS = 1_900
DEFAULT_INSPECTION_INTERVAL = 0.12
DEFAULT_WORKERS = 8
USER_AGENT = "Pantheon-GSC-Monitor/1.0 (+https://mysticpantheon.com)"
INDEX_FIELDS = (
    "verdict",
    "coverageState",
    "robotsTxtState",
    "indexingState",
    "lastCrawlTime",
    "pageFetchState",
    "googleCanonical",
    "userCanonical",
    "crawledAs",
)


class JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._inside_json_ld = False
        self._chunks: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        values = {key.lower(): (value or "") for key, value in attrs}
        if values.get("type", "").lower() == "application/ld+json":
            self._inside_json_ld = True
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._inside_json_ld:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._inside_json_ld:
            self.scripts.append("".join(self._chunks))
            self._inside_json_ld = False
            self._chunks = []


def _request_bytes(
    url: str,
    *,
    timeout: float = 20.0,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _same_origin(url: str, expected_host: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme == "https" and parsed.hostname == expected_host


def sitemap_urls_from_bytes(payload: bytes) -> tuple[str, list[str]]:
    root = ET.fromstring(payload)
    kind = root.tag.rsplit("}", 1)[-1]
    urls = [
        str(item.text or "").strip()
        for item in root.iter()
        if item.tag.rsplit("}", 1)[-1] == "loc" and str(item.text or "").strip()
    ]
    if kind not in {"urlset", "sitemapindex"}:
        raise ValueError(f"不支援的 Sitemap root：{kind}")
    return kind, urls


def load_sitemap_urls(
    sitemap_url: str,
    *,
    max_urls: int = DEFAULT_MAX_URLS,
    request_bytes: Callable[[str], bytes] = _request_bytes,
) -> list[str]:
    parsed = urllib.parse.urlsplit(sitemap_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Sitemap URL 必須是 HTTPS")
    expected_host = parsed.hostname
    pending = [sitemap_url]
    seen_sitemaps: set[str] = set()
    page_urls: set[str] = set()

    while pending:
        current = pending.pop(0)
        if current in seen_sitemaps:
            continue
        if not _same_origin(current, expected_host):
            raise ValueError(f"Sitemap index 含跨網域 URL：{current}")
        seen_sitemaps.add(current)
        kind, urls = sitemap_urls_from_bytes(request_bytes(current))
        if kind == "sitemapindex":
            pending.extend(urls)
            continue
        for url in urls:
            if not _same_origin(url, expected_host):
                raise ValueError(f"Sitemap 含跨網域頁面：{url}")
            page_urls.add(url)
            if len(page_urls) > max_urls:
                raise ValueError(f"Sitemap URL 超過安全上限 {max_urls}")
    return sorted(page_urls)


def _jsonld_nodes(value: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            nodes.extend(_jsonld_nodes(item))
    elif isinstance(value, dict):
        nodes.append(value)
        if "@graph" in value:
            nodes.extend(_jsonld_nodes(value["@graph"]))
    return nodes


def _is_breadcrumb(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    return node_type == "BreadcrumbList" or (
        isinstance(node_type, list) and "BreadcrumbList" in node_type
    )


def _item_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("@id") or value.get("url") or "")
    return ""


def extract_declared_breadcrumbs(html: str) -> tuple[list[dict[str, Any]], list[str]]:
    parser = JsonLdParser()
    parser.feed(html)
    breadcrumbs: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw in enumerate(parser.scripts):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            errors.append(f"jsonld[{index}]")
            continue
        for node in _jsonld_nodes(payload):
            if not _is_breadcrumb(node):
                continue
            items = node.get("itemListElement")
            if not isinstance(items, list):
                continue
            normalized = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                normalized.append(
                    {
                        "position": item.get("position"),
                        "name": str(item.get("name") or ""),
                        "url": _item_url(item.get("item")),
                    }
                )
            breadcrumbs.append(
                {
                    "items": sorted(
                        normalized,
                        key=lambda item: (
                            item["position"] if isinstance(item["position"], int) else 9_999,
                            item["name"],
                        ),
                    )
                }
            )
    return breadcrumbs, errors


def normalize_inspection(result: dict[str, Any]) -> dict[str, Any]:
    index_result = result.get("indexStatusResult")
    index_status = index_result if isinstance(index_result, dict) else {}
    rich_result = result.get("richResultsResult")
    rich_status = rich_result if isinstance(rich_result, dict) else {}
    detected_items = rich_status.get("detectedItems")
    detected = detected_items if isinstance(detected_items, list) else []
    breadcrumb_items = []
    for group in detected:
        if not isinstance(group, dict) or str(group.get("richResultType") or "").casefold() not in {
            "breadcrumb",
            "breadcrumbs",
            "導覽標記",
        }:
            continue
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            breadcrumb_items.append(
                {
                    "name": str(item.get("name") or ""),
                    "issues": [
                        {
                            "severity": str(issue.get("severity") or ""),
                            "message": str(issue.get("issueMessage") or ""),
                        }
                        for issue in item.get("issues") or []
                        if isinstance(issue, dict)
                    ],
                }
            )
    return {
        "available": True,
        "inspection_result_link": str(result.get("inspectionResultLink") or ""),
        "index": {field: index_status.get(field) for field in INDEX_FIELDS},
        "gsc_breadcrumb": {
            "detected": bool(breadcrumb_items),
            "verdict": rich_status.get("verdict"),
            "items": breadcrumb_items,
        },
    }


def _index_bucket(record: dict[str, Any]) -> str:
    inspection = record.get("inspection")
    if not isinstance(inspection, dict) or inspection.get("available") is not True:
        return "unknown"
    index_status = inspection.get("index")
    verdict = index_status.get("verdict") if isinstance(index_status, dict) else None
    if verdict == "PASS":
        return "indexed"
    if verdict in {"NEUTRAL", "FAIL"}:
        return "not_indexed"
    return "unknown"


def classify_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {
        "indexed_gsc_breadcrumb": [],
        "indexed_declared_not_recognized": [],
        "indexed_no_declared_breadcrumb": [],
        "not_indexed_declared_breadcrumb": [],
        "not_indexed_no_declared_breadcrumb": [],
        "unknown": [],
    }
    non_indexed_reasons: dict[str, int] = {}
    diagnosis_queue = []
    for record in records:
        url = str(record.get("url") or "")
        index_bucket = _index_bucket(record)
        inspection = record.get("inspection") if isinstance(record.get("inspection"), dict) else {}
        gsc_breadcrumb = inspection.get("gsc_breadcrumb")
        gsc_detected = bool(
            isinstance(gsc_breadcrumb, dict) and gsc_breadcrumb.get("detected") is True
        )
        declared = record.get("declared_breadcrumb")
        declared_present = bool(isinstance(declared, dict) and declared.get("present") is True)

        if index_bucket == "unknown":
            group = "unknown"
        elif index_bucket == "indexed" and gsc_detected:
            group = "indexed_gsc_breadcrumb"
        elif index_bucket == "indexed" and declared_present:
            group = "indexed_declared_not_recognized"
        elif index_bucket == "indexed":
            group = "indexed_no_declared_breadcrumb"
        elif declared_present:
            group = "not_indexed_declared_breadcrumb"
        else:
            group = "not_indexed_no_declared_breadcrumb"
        groups[group].append(url)

        index_status = inspection.get("index") if isinstance(inspection.get("index"), dict) else {}
        if index_bucket == "not_indexed":
            reason = str(index_status.get("coverageState") or "UNKNOWN_COVERAGE")
            non_indexed_reasons[reason] = non_indexed_reasons.get(reason, 0) + 1
        if group in {
            "indexed_declared_not_recognized",
            "not_indexed_declared_breadcrumb",
            "not_indexed_no_declared_breadcrumb",
            "unknown",
        }:
            diagnosis_queue.append(
                {
                    "url": url,
                    "group": group,
                    "coverage_state": index_status.get("coverageState"),
                    "page_fetch_state": index_status.get("pageFetchState"),
                    "indexing_state": index_status.get("indexingState"),
                    "robots_txt_state": index_status.get("robotsTxtState"),
                    "google_canonical": index_status.get("googleCanonical"),
                    "user_canonical": index_status.get("userCanonical"),
                }
            )
    for urls in groups.values():
        urls.sort()
    return {
        "counts": {name: len(urls) for name, urls in groups.items()},
        "groups": groups,
        "non_indexed_reason_counts": dict(sorted(non_indexed_reasons.items())),
        "diagnosis_queue": diagnosis_queue,
    }


def compare_classifications(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, dict[str, list[str]]]:
    previous_groups = {}
    if previous is not None:
        classification = previous.get("classification")
        if isinstance(classification, dict) and isinstance(classification.get("groups"), dict):
            previous_groups = classification["groups"]
    current_groups = current["groups"]
    changes = {}
    for name, urls in current_groups.items():
        before = set(previous_groups.get(name) or [])
        after = set(urls)
        changes[name] = {
            "entered": sorted(after - before),
            "left": sorted(before - after),
        }
    return changes


def _breadcrumb_url_chains(record: dict[str, Any]) -> list[list[str]]:
    declared = record.get("declared_breadcrumb")
    if not isinstance(declared, dict):
        return []
    breadcrumbs = declared.get("breadcrumbs")
    if not isinstance(breadcrumbs, list):
        return []
    return [
        [str(item.get("url") or "") for item in breadcrumb.get("items") or [] if isinstance(item, dict)]
        for breadcrumb in breadcrumbs
        if isinstance(breadcrumb, dict)
    ]


def compare_snapshots(
    previous: dict[str, Any] | None,
    current_records: list[dict[str, Any]],
) -> dict[str, Any]:
    if previous is None:
        return {
            "baseline": True,
            "previous_observation_date": None,
            "urls_added": [],
            "urls_removed": [],
            "index_changes": [],
            "breadcrumb_url_changes": [],
        }
    previous_records = {
        str(record.get("url") or ""): record
        for record in previous.get("records") or []
        if isinstance(record, dict) and record.get("url")
    }
    current_by_url = {str(record["url"]): record for record in current_records}
    previous_urls = set(previous_records)
    current_urls = set(current_by_url)
    index_changes = []
    breadcrumb_changes = []
    for url in sorted(previous_urls & current_urls):
        before_index = ((previous_records[url].get("inspection") or {}).get("index") or {})
        after_index = ((current_by_url[url].get("inspection") or {}).get("index") or {})
        changed_fields = {
            field: {"before": before_index.get(field), "after": after_index.get(field)}
            for field in INDEX_FIELDS
            if before_index.get(field) != after_index.get(field)
        }
        if changed_fields:
            index_changes.append({"url": url, "fields": changed_fields})
        before_chain = _breadcrumb_url_chains(previous_records[url])
        after_chain = _breadcrumb_url_chains(current_by_url[url])
        if before_chain != after_chain:
            breadcrumb_changes.append({"url": url, "before": before_chain, "after": after_chain})
    return {
        "baseline": False,
        "previous_observation_date": previous.get("observation_date"),
        "urls_added": sorted(current_urls - previous_urls),
        "urls_removed": sorted(previous_urls - current_urls),
        "index_changes": index_changes,
        "breadcrumb_url_changes": breadcrumb_changes,
    }


def _previous_snapshot(output_root: Path, observation_date: str) -> dict[str, Any] | None:
    candidates = sorted(path for path in output_root.glob("*.json") if path.stem < observation_date)
    if not candidates:
        return None
    payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def inspect_records(
    urls: list[str],
    *,
    property_url: str,
    client: GscReadonlyClient,
    inspection_interval: float,
    workers: int = DEFAULT_WORKERS,
    request_bytes: Callable[[str], bytes] = _request_bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not 1 <= workers <= 16:
        raise ValueError("workers 必須介於 1 與 16")

    def inspect_one(url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        record: dict[str, Any] = {"url": url}
        record_warnings = []
        inspection_error: Exception | None = None
        for attempt in range(2):
            try:
                record["inspection"] = normalize_inspection(client.inspect_url(property_url, url))
                inspection_error = None
                break
            except Exception as error:
                inspection_error = error
                if attempt == 0:
                    time.sleep(0.5)
        if inspection_error is not None:  # 保留失敗 URL，避免靜默消失。
            record["inspection"] = {"available": False}
            record_warnings.append(
                {
                    "record": url,
                    "reason_code": "URL_INSPECTION_FAILED",
                    "stage": "gsc_url_inspection",
                    "impact_count": 1,
                    "detail": str(inspection_error)[:300],
                }
            )
        try:
            html = request_bytes(url).decode("utf-8", errors="replace")
            breadcrumbs, parse_errors = extract_declared_breadcrumbs(html)
            record["declared_breadcrumb"] = {
                "available": True,
                "present": bool(breadcrumbs),
                "breadcrumbs": breadcrumbs,
            }
            if parse_errors:
                record_warnings.append(
                    {
                        "record": url,
                        "reason_code": "JSONLD_PARSE_FAILED",
                        "stage": "live_breadcrumb_parse",
                        "impact_count": len(parse_errors),
                        "detail": ",".join(parse_errors),
                    }
                )
        except Exception as error:  # 保留 GSC 結果並標示 live HTML 不可用。
            record["declared_breadcrumb"] = {"available": False, "present": None, "breadcrumbs": []}
            record_warnings.append(
                {
                    "record": url,
                    "reason_code": "LIVE_PAGE_FETCH_FAILED",
                    "stage": "live_breadcrumb_fetch",
                    "impact_count": 1,
                    "detail": str(error)[:300],
                }
            )
        return record, record_warnings

    futures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for index, url in enumerate(urls):
            futures.append(executor.submit(inspect_one, url))
            if inspection_interval > 0 and index < len(urls) - 1:
                time.sleep(inspection_interval)
        results = [future.result() for future in futures]
    records = [record for record, _warnings in results]
    warnings = [warning for _record, record_warnings in results for warning in record_warnings]
    return records, warnings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation-date", default=date.today().isoformat())
    parser.add_argument("--property")
    parser.add_argument("--sitemap-url", default=DEFAULT_SITEMAP_URL)
    parser.add_argument("--max-urls", type=int, default=DEFAULT_MAX_URLS)
    parser.add_argument("--inspection-interval", type=float, default=DEFAULT_INSPECTION_INTERVAL)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--output-root", type=Path, default=Path(".work/gsc-data/url-inspection"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output_root / f"{args.observation_date}.json"
    if output.exists() and not args.force:
        print(json.dumps({"status": "already_exists", "output": str(output)}, ensure_ascii=False))
        return 0

    client = GscReadonlyClient(access_token())
    properties = client.list_properties()
    property_url = args.property or choose_single_property(properties)
    accessible = {str(item.get("siteUrl") or "") for item in properties}
    if property_url not in accessible:
        raise SystemExit(f"指定的 GSC property 無法存取：{property_url}")

    urls = load_sitemap_urls(args.sitemap_url, max_urls=args.max_urls)
    if not urls:
        raise SystemExit("Sitemap 沒有 URL，停止建立空快照")
    records, warnings = inspect_records(
        urls,
        property_url=property_url,
        client=client,
        inspection_interval=args.inspection_interval,
        workers=args.workers,
    )
    previous = _previous_snapshot(args.output_root, args.observation_date)
    changes = compare_snapshots(previous, records)
    classification = classify_records(records)
    changes["classification_changes"] = compare_classifications(previous, classification)
    snapshot = {
        "schema_version": 1,
        "source": {
            "url_inventory": args.sitemap_url,
            "index_status": "google_search_console_url_inspection",
            "declared_breadcrumb": "live_html_jsonld",
        },
        "property": property_url,
        "observation_date": args.observation_date,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "url_count": len(urls),
        "complete": not warnings,
        "warnings": warnings,
        "classification": classification,
        "changes": changes,
        "records": records,
    }
    write_snapshot(output, snapshot)
    status = "ok" if not warnings else "partial"
    print(
        json.dumps(
            {
                "status": status,
                "property": property_url,
                "observation_date": args.observation_date,
                "urls": len(urls),
                "warnings": len(warnings),
                "changes": {
                    "baseline": changes["baseline"],
                    "urls_added": len(changes["urls_added"]),
                    "urls_removed": len(changes["urls_removed"]),
                    "index_changes": len(changes["index_changes"]),
                    "breadcrumb_url_changes": len(changes["breadcrumb_url_changes"]),
                },
                "classification_counts": classification["counts"],
                "output": str(output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not warnings else 2


if __name__ == "__main__":
    raise SystemExit(main())

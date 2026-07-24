#!/usr/bin/env python3
"""稽核 Pantheon 五個歷史索引異常 URL 的現行技術狀態。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


TARGET_HISTORY = {
    "/articles/career/career-0001": {
        "signal": "discovered_never_crawled",
        "observed": "GSC 顯示已發現但從未檢索；沒有已知的舊 repository 缺陷。",
    },
    "/articles/personality/personality-0017": {
        "signal": "historical_noindex",
        "observed": "GSC 保存 7/12 舊 noindex／X-Robots 狀態；目前需以新抓取覆核。",
    },
    "/articles/tarot/tarot-0048": {
        "signal": "historical_noindex",
        "observed": "GSC 保存 7/12 舊 noindex／X-Robots 狀態；目前需以新抓取覆核。",
    },
    "/articles/tarot/tarot-0009": {
        "signal": "historical_canonical",
        "observed": "GSC 保存 7/11 舊 alternate canonical；目前需以新抓取覆核。",
    },
    "/articles": {
        "signal": "historical_google_canonical",
        "observed": "Google 曾選首頁為 canonical；目前需以新抓取覆核。",
    },
}

CLASS_CURRENT_BUG = "目前仍有 bug"
CLASS_WAITING = "目前已修復等待重抓"
CLASS_MORE_EVIDENCE = "需要更多證據"


@dataclass(frozen=True)
class ResponseSnapshot:
    status: int
    headers: dict[str, str]
    body: str
    final_url: str = ""


class PageParser(HTMLParser):
    """只擷取索引診斷需要的 rendered HTML 欄位。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = ""
        self.canonical = ""
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.jsonld: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag in {"title", "h1"}:
            self._capture = tag
            self._buffer = []
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._capture = "jsonld"
            self._buffer = []
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href", "").strip()
        elif tag == "meta":
            key = (values.get("name") or values.get("property") or "").lower()
            if key:
                self.meta[key] = values.get("content", "").strip()
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"].strip())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture == tag:
            value = "".join(self._buffer).strip()
            if tag == "title":
                self.title = value
            elif tag == "h1" and not self.h1:
                self.h1 = value
            self._capture = None
            self._buffer = []
        elif tag == "script" and self._capture == "jsonld":
            self.jsonld.append("".join(self._buffer).strip())
            self._capture = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)


def normalize_path(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return path


def robots_has_noindex(value: str) -> bool:
    tokens = {
        token.rsplit(":", 1)[-1].strip().lower()
        for group in value.split(";")
        for token in group.split(",")
        if token.strip()
    }
    return "noindex" in tokens or "none" in tokens


def jsonld_urls(documents: Iterable[str]) -> set[str]:
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"url", "mainEntityOfPage"} and isinstance(child, str):
                    found.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for document in documents:
        try:
            walk(json.loads(document))
        except json.JSONDecodeError:
            continue
    return found


def parse_page(body: str) -> PageParser:
    parser = PageParser()
    parser.feed(body)
    return parser


def canonical_path_matches(canonical: str, target_path: str) -> bool:
    if not canonical:
        return False
    parsed = urlparse(canonical)
    return not parsed.query and not parsed.fragment and normalize_path(canonical) == target_path


def audit_snapshots(
    responses: dict[str, ResponseSnapshot],
    *,
    discovery_complete: bool,
) -> dict[str, Any]:
    parsed_pages = {
        normalize_path(path): parse_page(response.body)
        for path, response in responses.items()
        if response.body
    }
    inbound: dict[str, list[str]] = {path: [] for path in TARGET_HISTORY}
    for source_path, page in parsed_pages.items():
        for href in page.links:
            linked_path = normalize_path(href)
            if linked_path in inbound and linked_path != source_path:
                inbound[linked_path].append(source_path)

    findings: dict[str, Any] = {}
    for target_path, history in TARGET_HISTORY.items():
        response = responses.get(target_path)
        page = parsed_pages.get(target_path)
        issues: list[str] = []
        if response is None:
            issues.append("missing_response")
        elif response.status != 200:
            issues.append(f"status_{response.status}")
        if response is not None and robots_has_noindex(response.headers.get("x-robots-tag", "")):
            issues.append("x_robots_noindex")
        if page is None:
            issues.append("missing_html")
        else:
            if robots_has_noindex(page.meta.get("robots", "")):
                issues.append("meta_robots_noindex")
            if not page.canonical:
                issues.append("missing_canonical")
            elif not canonical_path_matches(page.canonical, target_path):
                issues.append("canonical_mismatch")
            if not page.title:
                issues.append("missing_title")
            if not page.meta.get("description"):
                issues.append("missing_description")
            if not page.h1:
                issues.append("missing_h1")
            og_url = page.meta.get("og:url", "")
            if not og_url:
                issues.append("missing_og_url")
            elif normalize_path(og_url) != target_path:
                issues.append("og_url_mismatch")
            if target_path not in {normalize_path(url) for url in jsonld_urls(page.jsonld)}:
                issues.append("jsonld_url_missing_or_mismatch")
        all_sources = sorted(set(inbound[target_path]))
        if discovery_complete and not all_sources:
            issues.append("no_internal_inbound_link")

        if issues:
            classification = CLASS_CURRENT_BUG
            next_step = "修正列出的現行 repository／服務輸出問題後重新執行 audit。"
        elif not discovery_complete:
            classification = CLASS_MORE_EVIDENCE
            next_step = "補齊 sitemap HTML discovery 掃描後再判斷；目前不得由缺少 inbound link 推論 repository bug。"
        elif history["signal"] == "discovered_never_crawled":
            classification = CLASS_MORE_EVIDENCE
            next_step = "保留現行頁面不變；由 GSC URL Inspection 的 live test／後續抓取紀錄確認 Googlebot 行為。"
        else:
            classification = CLASS_WAITING
            next_step = "保留現行頁面不變；等待 Google 重新抓取並覆寫歷史狀態。"

        findings[target_path] = {
            "classification": classification,
            "current_issues": issues,
            "status": response.status if response else None,
            "x_robots_tag": response.headers.get("x-robots-tag", "") if response else "",
            "meta_robots": page.meta.get("robots", "") if page else "",
            "canonical": page.canonical if page else "",
            "title": page.title if page else "",
            "description": page.meta.get("description", "") if page else "",
            "h1": page.h1 if page else "",
            "og_url": page.meta.get("og:url", "") if page else "",
            "jsonld_has_target_url": (
                target_path in {normalize_path(url) for url in jsonld_urls(page.jsonld)}
                if page
                else False
            ),
            "inbound_source_count": len(all_sources),
            "inbound_sources": all_sources[:20],
            "history": history["observed"],
            "next_step": next_step,
        }

    return {
        "discovery_complete": discovery_complete,
        "classification_counts": {
            label: sum(item["classification"] == label for item in findings.values())
            for label in (CLASS_CURRENT_BUG, CLASS_WAITING, CLASS_MORE_EVIDENCE)
        },
        "findings": findings,
    }


def fixture_responses(path: Path) -> tuple[dict[str, ResponseSnapshot], bool]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    responses = {
        normalize_path(key): ResponseSnapshot(
            status=int(value["status"]),
            headers={str(k).lower(): str(v) for k, v in value.get("headers", {}).items()},
            body=str(value.get("body", "")),
            final_url=str(value.get("final_url", "")),
        )
        for key, value in payload["responses"].items()
    }
    return responses, bool(payload.get("discovery_complete", False))


def fetch(url: str, timeout: float) -> ResponseSnapshot:
    request = Request(url, headers={"User-Agent": "PantheonIndexAnomalyAudit/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return ResponseSnapshot(
                status=response.status,
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace"),
                final_url=response.url,
            )
    except Exception as exc:  # URL 錯誤也必須成為可追溯 audit 輸出。
        return ResponseSnapshot(status=0, headers={}, body="", final_url=f"ERROR: {exc}")


def sitemap_paths(snapshot: ResponseSnapshot) -> list[str]:
    if snapshot.status != 200:
        return []
    try:
        root = ET.fromstring(snapshot.body)
    except ET.ParseError:
        return []
    paths: list[str] = []
    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            paths.append(normalize_path(element.text.strip()))
    return sorted(set(paths))


def base_url_responses(
    base_url: str,
    *,
    timeout: float,
    max_discovery_pages: int,
    workers: int,
) -> tuple[dict[str, ResponseSnapshot], bool]:
    base_url = base_url.rstrip("/")
    sitemap = fetch(f"{base_url}/sitemap.xml", timeout)
    discovered = sitemap_paths(sitemap)
    discovery_complete = bool(discovered) and len(discovered) <= max_discovery_pages
    source_paths = discovered[:max_discovery_pages]
    paths = sorted(set(TARGET_HISTORY) | set(source_paths))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        snapshots = executor.map(
            lambda path: fetch(urljoin(f"{base_url}/", path.lstrip("/")), timeout),
            paths,
        )
        responses = dict(zip(paths, snapshots, strict=True))
    if any(responses[path].status != 200 for path in source_paths):
        discovery_complete = False
    return responses, discovery_complete


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", type=Path, help="JSON response snapshot fixture")
    source.add_argument("--base-url", help="要稽核的網站 origin，例如 http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=10.0, help="單一 HTTP request timeout 秒數")
    parser.add_argument("--max-discovery-pages", type=int, default=500, help="sitemap HTML 掃描上限")
    parser.add_argument("--workers", type=int, default=8, help="base URL 同時抓取數")
    parser.add_argument("--pretty", action="store_true", help="縮排 JSON 輸出")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fixture:
        responses, discovery_complete = fixture_responses(args.fixture)
        source = {"fixture": str(args.fixture)}
    else:
        responses, discovery_complete = base_url_responses(
            args.base_url,
            timeout=args.timeout,
            max_discovery_pages=args.max_discovery_pages,
            workers=args.workers,
        )
        source = {"base_url": args.base_url}
    report = {"source": source, **audit_snapshots(responses, discovery_complete=discovery_complete)}
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    return 1 if report["classification_counts"][CLASS_CURRENT_BUG] else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""唯讀驗證 public HTTP 回應本身是否含完整 locale 文章 DOM。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from html.parser import HTMLParser
from urllib.request import Request, urlopen


class ProbeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.in_h1 = False
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.canonical: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "h1" and not self.h1_parts:
            self.in_h1 = True
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_h1:
            self.h1_parts.append(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--h1", required=True)
    parser.add_argument("--sentinel", required=True)
    args = parser.parse_args()

    request = Request(args.url, headers={"User-Agent": "Pantheon-readonly-RCA/1"})
    with urlopen(request, timeout=30) as response:
        status = response.status
        body = response.read()
        headers = dict(response.headers.items())
    text = body.decode("utf-8", errors="replace")
    dom = ProbeParser()
    dom.feed(text)
    actual = {
        "status": status,
        "canonical": dom.canonical,
        "title": "".join(dom.title_parts).strip(),
        "h1": "".join(dom.h1_parts).strip(),
        "sentinel_present": args.sentinel in text,
    }
    expected = {
        "status": 200,
        "canonical": args.canonical,
        "title": args.title,
        "h1": args.h1,
        "sentinel_present": True,
    }
    checks = {key: actual[key] == value for key, value in expected.items()}
    payload = {
        "schema_version": 1,
        "probe_layer": "raw_http_response_dom",
        "url": args.url,
        "actual": actual,
        "expected": expected,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "RED",
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "response_headers": {
            key.lower(): value
            for key, value in headers.items()
            if key.lower() in {"date", "server", "cf-cache-status", "cf-ray", "cache-control"}
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

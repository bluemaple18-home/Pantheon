from __future__ import annotations

import json

from scripts.gsc_daily_inspection import (
    classify_records,
    compare_classifications,
    compare_snapshots,
    extract_declared_breadcrumbs,
    inspect_records,
    load_sitemap_urls,
    normalize_inspection,
    sitemap_urls_from_bytes,
)


def test_sitemap_urlset_and_index_are_same_origin_and_unique() -> None:
    index = b"""<?xml version="1.0"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://mysticpantheon.com/a.xml</loc></sitemap>
      <sitemap><loc>https://mysticpantheon.com/b.xml</loc></sitemap>
    </sitemapindex>"""
    child_a = b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://mysticpantheon.com/articles/a</loc></url>
    </urlset>"""
    child_b = b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://mysticpantheon.com/articles/a</loc></url>
      <url><loc>https://mysticpantheon.com/articles/b</loc></url>
    </urlset>"""
    fixtures = {
        "https://mysticpantheon.com/sitemap.xml": index,
        "https://mysticpantheon.com/a.xml": child_a,
        "https://mysticpantheon.com/b.xml": child_b,
    }
    assert sitemap_urls_from_bytes(index)[0] == "sitemapindex"
    assert load_sitemap_urls(
        "https://mysticpantheon.com/sitemap.xml",
        request_bytes=fixtures.__getitem__,
    ) == [
        "https://mysticpantheon.com/articles/a",
        "https://mysticpantheon.com/articles/b",
    ]


def test_extracts_breadcrumb_urls_from_jsonld_graph() -> None:
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "文章",
                        "item": {"@id": "https://mysticpantheon.com/articles/a"},
                    },
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "首頁",
                        "item": "https://mysticpantheon.com/",
                    },
                ],
            }
        ],
    }
    html = f'<script type="application/ld+json">{json.dumps(payload, ensure_ascii=False)}</script>'
    breadcrumbs, errors = extract_declared_breadcrumbs(html)
    assert errors == []
    assert breadcrumbs == [
        {
            "items": [
                {"position": 1, "name": "首頁", "url": "https://mysticpantheon.com/"},
                {"position": 2, "name": "文章", "url": "https://mysticpantheon.com/articles/a"},
            ]
        }
    ]


def test_normalizes_index_and_gsc_breadcrumb_result() -> None:
    normalized = normalize_inspection(
        {
            "inspectionResultLink": "https://search.google.com/search-console/inspect",
            "indexStatusResult": {
                "verdict": "PASS",
                "coverageState": "Submitted and indexed",
                "indexingState": "INDEXING_ALLOWED",
                "pageFetchState": "SUCCESSFUL",
                "lastCrawlTime": "2026-07-24T00:00:00Z",
            },
            "richResultsResult": {
                "verdict": "PASS",
                "detectedItems": [
                    {
                        "richResultType": "Breadcrumbs",
                        "items": [{"name": "Unnamed item", "issues": []}],
                    }
                ],
            },
        }
    )
    assert normalized["index"]["verdict"] == "PASS"
    assert normalized["index"]["coverageState"] == "Submitted and indexed"
    assert normalized["gsc_breadcrumb"] == {
        "detected": True,
        "verdict": "PASS",
        "items": [{"name": "Unnamed item", "issues": []}],
    }


def test_normalizes_localized_gsc_breadcrumb_type() -> None:
    normalized = normalize_inspection(
        {
            "richResultsResult": {
                "verdict": "PASS",
                "detectedItems": [{"richResultType": "導覽標記", "items": [{"name": "未命名的項目"}]}],
            }
        }
    )
    assert normalized["gsc_breadcrumb"]["detected"] is True


def test_compares_index_and_breadcrumb_url_changes() -> None:
    previous = {
        "observation_date": "2026-07-23",
        "records": [
            {
                "url": "https://mysticpantheon.com/a",
                "inspection": {"index": {"verdict": "NEUTRAL"}},
                "declared_breadcrumb": {
                    "breadcrumbs": [{"items": [{"url": "https://mysticpantheon.com/old"}]}]
                },
            },
            {"url": "https://mysticpantheon.com/removed"},
        ],
    }
    current = [
        {
            "url": "https://mysticpantheon.com/a",
            "inspection": {"index": {"verdict": "PASS"}},
            "declared_breadcrumb": {
                "breadcrumbs": [{"items": [{"url": "https://mysticpantheon.com/new"}]}]
            },
        },
        {"url": "https://mysticpantheon.com/added"},
    ]
    changes = compare_snapshots(previous, current)
    assert changes["baseline"] is False
    assert changes["urls_added"] == ["https://mysticpantheon.com/added"]
    assert changes["urls_removed"] == ["https://mysticpantheon.com/removed"]
    assert changes["index_changes"][0]["fields"]["verdict"] == {
        "before": "NEUTRAL",
        "after": "PASS",
    }
    assert changes["breadcrumb_url_changes"][0] == {
        "url": "https://mysticpantheon.com/a",
        "before": [["https://mysticpantheon.com/old"]],
        "after": [["https://mysticpantheon.com/new"]],
    }


def test_inspection_keeps_failed_url_with_structured_warning() -> None:
    class FakeClient:
        def inspect_url(self, _property_url: str, inspection_url: str) -> dict:
            if inspection_url.endswith("/bad"):
                raise RuntimeError("inspection failed")
            return {"indexStatusResult": {"verdict": "PASS"}}

    html = b"""<script type="application/ld+json">
    {"@type":"BreadcrumbList","itemListElement":[{"position":1,"name":"Home","item":"https://mysticpantheon.com/"}]}
    </script>"""
    records, warnings = inspect_records(
        ["https://mysticpantheon.com/good", "https://mysticpantheon.com/bad"],
        property_url="sc-domain:mysticpantheon.com",
        client=FakeClient(),  # type: ignore[arg-type]
        inspection_interval=0,
        workers=2,
        request_bytes=lambda _url: html,
    )
    assert [record["url"] for record in records] == [
        "https://mysticpantheon.com/good",
        "https://mysticpantheon.com/bad",
    ]
    assert records[1]["inspection"] == {"available": False}
    assert records[0]["inspection"]["available"] is True
    assert warnings[0]["reason_code"] == "URL_INSPECTION_FAILED"
    assert warnings[0]["record"] == "https://mysticpantheon.com/bad"


def test_classifies_index_and_breadcrumb_research_groups() -> None:
    records = [
        {
            "url": "https://mysticpantheon.com/indexed-breadcrumb",
            "inspection": {
                "available": True,
                "index": {"verdict": "PASS", "coverageState": "Submitted and indexed"},
                "gsc_breadcrumb": {"detected": True},
            },
            "declared_breadcrumb": {"present": True},
        },
        {
            "url": "https://mysticpantheon.com/indexed-gap",
            "inspection": {
                "available": True,
                "index": {"verdict": "PASS"},
                "gsc_breadcrumb": {"detected": False},
            },
            "declared_breadcrumb": {"present": True},
        },
        {
            "url": "https://mysticpantheon.com/not-indexed",
            "inspection": {
                "available": True,
                "index": {"verdict": "NEUTRAL", "coverageState": "Crawled - currently not indexed"},
                "gsc_breadcrumb": {"detected": False},
            },
            "declared_breadcrumb": {"present": True},
        },
        {
            "url": "https://mysticpantheon.com/unknown",
            "inspection": {"available": False},
            "declared_breadcrumb": {"present": False},
        },
    ]
    classification = classify_records(records)
    assert classification["counts"]["indexed_gsc_breadcrumb"] == 1
    assert classification["counts"]["indexed_declared_not_recognized"] == 1
    assert classification["counts"]["not_indexed_declared_breadcrumb"] == 1
    assert classification["counts"]["unknown"] == 1
    assert classification["non_indexed_reason_counts"] == {
        "Crawled - currently not indexed": 1
    }
    assert len(classification["diagnosis_queue"]) == 3

    changes = compare_classifications(
        {"classification": {"groups": {"unknown": ["https://mysticpantheon.com/unknown"]}}},
        classification,
    )
    assert changes["unknown"]["entered"] == []
    assert changes["unknown"]["left"] == []
    assert changes["indexed_gsc_breadcrumb"]["entered"] == [
        "https://mysticpantheon.com/indexed-breadcrumb"
    ]

from scripts.competitor_seo_tool import (
    FeedItem,
    annotate_endpoint,
    endpoint_label,
    remap_feed_item_links_for_audit,
)


def endpoint_info(body: str, content_type: str = "text/plain", status: int = 200) -> dict[str, object]:
    return {
        "status": status,
        "content_type": content_type,
        "bytes": len(body.encode()),
        "body": body,
    }


def test_llms_txt_rejects_html_fallback() -> None:
    body = "<!doctype html><html><head><title>Pantheon</title></head><body><div id=\"root\"></div></body></html>"

    assert endpoint_label(endpoint_info(body, "text/html; charset=utf-8"), "llms_txt") == "fallback_html"


def test_llms_txt_rejects_feed_or_xml_fallback() -> None:
    body = "<?xml version=\"1.0\"?><rss><channel><title>Pantheon feed</title></channel></rss>"

    assert endpoint_label(endpoint_info(body, "application/rss+xml"), "llms_txt") == "invalid_content"


def test_llms_txt_accepts_markdown_site_summary() -> None:
    body = """# Pantheon

Summary: Pantheon publishes astrology and tarot articles for readers and AI crawlers.
URL: https://mysticpantheon.com/articles
"""

    assert endpoint_label(endpoint_info(body, "text/markdown"), "llms_txt") == "present"


def test_ai_txt_requires_policy_context() -> None:
    body = """# Pantheon

Summary: Pantheon has astrology and tarot pages.
URL: https://mysticpantheon.com/articles
"""

    assert endpoint_label(endpoint_info(body, "text/markdown"), "ai_txt") == "invalid_content"


def test_ai_txt_accepts_usage_and_citation_policy() -> None:
    body = """# AI Usage Policy

Allowed: AI crawlers may cite Pantheon pages with attribution.
Citation: https://mysticpantheon.com/articles
"""

    assert endpoint_label(endpoint_info(body, "text/markdown"), "ai_txt") == "present"


def test_endpoint_annotation_records_label_and_validation() -> None:
    info = annotate_endpoint("ai_txt", {"status": 404, "error": "HTTP Error 404: Not Found"})

    assert info["label"] == "missing"
    assert info["validation"] == "http_404"


def test_local_audit_remaps_feed_links_to_local_base() -> None:
    items = [
        FeedItem(
            title="塔羅牌意思",
            link="https://mysticpantheon.com/articles/tarot/tarot-0001",
            pub_date="Fri, 10 Jul 2026 00:00:00 +0800",
            categories=["塔羅"],
            description="",
            content_text="",
            headings=[],
            paragraph_count=0,
            char_count=0,
        )
    ]

    remapped = remap_feed_item_links_for_audit("http://127.0.0.1:8799", items)
    unchanged = remap_feed_item_links_for_audit("https://mysticpantheon.com", items)

    assert remapped[0].link == "http://127.0.0.1:8799/articles/tarot/tarot-0001"
    assert unchanged[0].link == "https://mysticpantheon.com/articles/tarot/tarot-0001"

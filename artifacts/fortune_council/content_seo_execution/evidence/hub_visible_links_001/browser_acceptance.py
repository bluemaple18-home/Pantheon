from __future__ import annotations

import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:9878"
EVIDENCE_DIR = Path(__file__).resolve().parent
FILE_URL = (Path(__file__).resolve().parents[4] / "app" / "web" / "article.html").as_uri()
CACHE_QUERY = "article-hub-visible-links-20260713-1"
SERIAL_RE = re.compile(r"[a-z]+-\d{4}", re.I)

CASES = [
    {
        "name": "product_desktop",
        "path": "/articles/tarot",
        "selector": "[data-hub-visible-links]:not([hidden])",
        "title": "分類文章",
        "viewport": {"width": 1440, "height": 1100},
        "min_links": 6,
    },
    {
        "name": "product_mobile",
        "path": "/articles/tarot",
        "selector": "[data-hub-visible-links]:not([hidden])",
        "title": "分類文章",
        "viewport": {"width": 390, "height": 1100},
        "min_links": 6,
    },
    {
        "name": "topic_desktop",
        "path": "/topics/tarot",
        "selector": "[data-topic-visible-links]:not([hidden])",
        "title": "相關文章",
        "viewport": {"width": 1440, "height": 1100},
        "min_links": 6,
    },
    {
        "name": "topic_mobile",
        "path": "/topics/tarot",
        "selector": "[data-topic-visible-links]:not([hidden])",
        "title": "相關文章",
        "viewport": {"width": 390, "height": 1100},
        "min_links": 6,
    },
]


def audit_case(page, case: dict) -> dict:
    console_messages: list[dict] = []
    page_errors: list[str] = []
    request_failed: list[str] = []
    bad_responses: list[dict] = []

    page.on("console", lambda message: console_messages.append({"type": message.type, "text": message.text}))
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("requestfailed", lambda request: request_failed.append(f"{request.method} {request.url} {request.failure}"))
    page.on(
        "response",
        lambda response: bad_responses.append({"status": response.status, "url": response.url})
        if response.status >= 400
        else None,
    )

    response = page.goto(f"{BASE_URL}{case['path']}", wait_until="networkidle")
    page.wait_for_selector(case["selector"], state="visible", timeout=5000)
    module = page.locator(case["selector"])
    links = module.locator("a")
    first_link = links.first
    first_link.focus()
    screenshot = EVIDENCE_DIR / f"{case['name']}.png"
    page.screenshot(path=str(screenshot), full_page=True)

    labels = links.evaluate_all("(items) => items.map((item) => item.textContent.trim())")
    hrefs = links.evaluate_all("(items) => items.map((item) => item.getAttribute('href'))")
    kinds = module.locator("span").evaluate_all("(items) => items.map((item) => item.textContent.trim())")
    layout = page.evaluate(
        """(selector) => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          activeHref: document.activeElement?.getAttribute("href") || "",
          moduleRect: document.querySelector(selector).getBoundingClientRect().toJSON(),
        })""",
        case["selector"],
    )
    script_src = page.locator('script[src*="/static/article.js"]').first.get_attribute("src") or ""
    style_href = page.locator('link[href*="/static/styles.css"]').first.get_attribute("href") or ""
    heading = module.locator("h2").first.text_content().strip()

    record = {
        "name": case["name"],
        "url": f"{BASE_URL}{case['path']}",
        "status": response.status if response else None,
        "heading": heading,
        "link_count": len(labels),
        "duplicate_href_count": len(hrefs) - len(set(hrefs)),
        "has_click_here": "點這裡" in labels,
        "has_serial_label": any(SERIAL_RE.search(label) for label in labels),
        "has_serial_kind": any(SERIAL_RE.search(kind) for kind in kinds),
        "active_href": layout["activeHref"],
        "horizontal_overflow": layout["scrollWidth"] > layout["clientWidth"],
        "script_src": script_src,
        "style_href": style_href,
        "screenshot": str(screenshot),
        "console_messages": console_messages,
        "page_errors": page_errors,
        "request_failed": request_failed,
        "bad_responses": bad_responses,
        "traceback_text_count": page.locator("text=Traceback").count(),
    }

    assert record["status"] == 200, record
    assert record["heading"] == case["title"], record
    assert case["min_links"] <= record["link_count"] <= 12, record
    assert record["duplicate_href_count"] == 0, record
    assert not record["has_click_here"], record
    assert not record["has_serial_label"], record
    assert not record["has_serial_kind"], record
    assert record["active_href"].startswith("/articles/"), record
    assert not record["horizontal_overflow"], record
    assert CACHE_QUERY in record["script_src"], record
    assert CACHE_QUERY in record["style_href"], record
    assert not record["page_errors"], record
    assert not record["request_failed"], record
    assert not record["bad_responses"], record
    assert record["traceback_text_count"] == 0, record
    return record


def audit_file_preview(page) -> dict:
    console_messages: list[dict] = []
    page_errors: list[str] = []
    request_failed: list[str] = []
    bad_responses: list[dict] = []
    page.on("console", lambda message: console_messages.append({"type": message.type, "text": message.text}))
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("requestfailed", lambda request: request_failed.append(f"{request.method} {request.url} {request.failure}"))
    page.on(
        "response",
        lambda response: bad_responses.append({"status": response.status, "url": response.url})
        if response.status >= 400
        else None,
    )

    response = page.goto(FILE_URL, wait_until="networkidle")
    page.wait_for_function("document.querySelectorAll('link[rel=stylesheet]').length > 0")
    page.wait_for_function("document.querySelector('img.ui-brand-mark img')?.complete")
    screenshot = EVIDENCE_DIR / "file_preview.png"
    page.screenshot(path=str(screenshot), full_page=True)
    record = {
        "name": "file_preview",
        "url": FILE_URL,
        "status": response.status if response else None,
        "heading": page.locator("[data-article-title]").text_content().strip(),
        "stylesheet_count": page.locator('link[rel="stylesheet"]').count(),
        "stylesheet_loaded_count": page.evaluate("Array.from(document.styleSheets).filter((sheet) => sheet.href).length"),
        "brand_image_width": page.locator(".ui-brand-mark img").evaluate("(image) => image.naturalWidth"),
        "script_src": page.locator('script[src*="article.js"]').first.get_attribute("src") or "",
        "style_href": page.locator('link[href*="styles.css"]').first.get_attribute("href") or "",
        "screenshot": str(screenshot),
        "console_messages": console_messages,
        "page_errors": page_errors,
        "request_failed": request_failed,
        "bad_responses": bad_responses,
    }
    assert record["status"] == 200, record
    assert record["heading"] == "最新文章", record
    assert record["stylesheet_count"] == 1, record
    assert record["stylesheet_loaded_count"] == 1, record
    assert record["brand_image_width"] > 0, record
    assert record["script_src"].startswith("file://"), record
    assert record["style_href"].startswith("file://"), record
    assert not record["page_errors"], record
    assert not record["request_failed"], record
    assert not record["bad_responses"], record
    return record


def main() -> None:
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for case in ([] if os.environ.get("FILE_ONLY") else CASES):
            context = browser.new_context(viewport=case["viewport"])
            page = context.new_page()
            try:
                results.append(audit_case(page, case))
            finally:
                context.close()
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        try:
            results.append(audit_file_preview(page))
        finally:
            context.close()
        browser.close()

    (EVIDENCE_DIR / "browser_acceptance.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

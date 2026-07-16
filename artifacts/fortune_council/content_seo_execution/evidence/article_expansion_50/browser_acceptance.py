from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:9878"
EVIDENCE_DIR = Path(__file__).resolve().parent
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ARTICLE_PATHS = [
    "/articles/love/love-0005",
    "/articles/career/career-0012",
    "/articles/interpersonal/interpersonal-0012",
    "/articles/wealth/wealth-0012",
    "/articles/life-direction/life-direction-0012",
    "/articles/astrology/astrology-0010",
]


def collect_page(page, path: str, expect_article: bool = True) -> dict:
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    bad_responses: list[dict] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on("requestfailed", lambda request: request_failures.append(f"{request.method} {request.url}"))
    page.on(
        "response",
        lambda response: bad_responses.append({"status": response.status, "url": response.url})
        if response.status >= 400
        else None,
    )
    response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    page.wait_for_selector("[data-article-title]", state="visible", timeout=5000)
    result = {
        "path": path,
        "status": response.status if response else None,
        "title": page.locator("[data-article-title]").text_content().strip(),
        "section_count": page.locator("[data-article-body] section").count(),
        "updated": page.locator("[data-article-updated]").text_content().strip(),
        "script_src": page.locator('script[src*="article.js"]').first.get_attribute("src") or "",
        "traceback_count": page.locator("text=Traceback").count(),
        "console_errors": console_errors,
        "page_errors": page_errors,
        "request_failures": request_failures,
        "bad_responses": bad_responses,
    }
    if expect_article:
        assert result["section_count"] == 4, result
        assert result["updated"] == "2026-07-16", result
    assert result["status"] == 200, result
    assert "article-expansion-20260716-1" in result["script_src"], result
    assert result["traceback_count"] == 0, result
    assert not console_errors and not page_errors and not request_failures and not bad_responses, result
    return result


def main() -> None:
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME_PATH)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        for path in ARTICLE_PATHS:
            results.append(collect_page(context.new_page(), path))

        hub = context.new_page()
        hub_result = collect_page(hub, "/articles/tarot", expect_article=False)
        hub_hrefs = hub.locator("[data-hub-visible-links] a").evaluate_all(
            "elements => elements.map((element) => element.getAttribute('href'))"
        )
        hub_result["visible_hrefs"] = hub_hrefs
        assert "/articles/tarot/tarot-0080" in hub_hrefs, hub_result
        assert "/articles/love/love-0012" in hub_hrefs, hub_result
        results.append(hub_result)

        topic = context.new_page()
        topic_result = collect_page(topic, "/topics/wealth", expect_article=False)
        topic_result["visible_link_count"] = topic.locator("[data-topic-visible-links] a").count()
        assert topic_result["visible_link_count"] >= 10, topic_result
        results.append(topic_result)

        screenshot = EVIDENCE_DIR / "wealth_topic_desktop.png"
        topic.screenshot(path=str(screenshot), full_page=True)
        browser.close()

    (EVIDENCE_DIR / "browser_acceptance.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

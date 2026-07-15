import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8891"
CHROMIUM_EXECUTABLE = (
    "/Users/mattkuo/ai-core/.tools/cache/ms-playwright/chromium-1228/chrome-mac-arm64/"
    "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
)
EVIDENCE_DIR = Path("artifacts/fortune_council/content_rewrite_execution/evidence/review/browser")

TARGETS = [
    {"id": "TAROT-CUPS-KING", "path": "/articles/tarot/tarot-0057", "keyword": "聖杯國王"},
    {"id": "MBTI-BASE-04", "path": "/articles/personality/personality-0004", "keyword": "MBTI 準嗎"},
    {"id": "THEME-LOVE-03", "path": "/articles/love/love-0003", "keyword": "復合前要想清楚什麼"},
    {"id": "ASTRO-BASE-01", "path": "/articles/astrology/astrology-0001", "keyword": "星盤是什麼"},
]

VIEWPORTS = [
    {"name": "desktop", "width": 1440, "height": 1100},
    {"name": "mobile", "width": 390, "height": 844, "is_mobile": True},
]


def text(page, selector):
    value = page.locator(selector).first.text_content(timeout=5000)
    return " ".join((value or "").split())


def count(page, selector):
    return page.locator(selector).count()


def run():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_EXECUTABLE, headless=True)
        for viewport in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": viewport["width"], "height": viewport["height"]},
                is_mobile=viewport.get("is_mobile", False),
                device_scale_factor=2 if viewport.get("is_mobile") else 1,
                locale="zh-TW",
            )
            for target in TARGETS:
                page = context.new_page()
                console_messages = []
                page_errors = []
                request_failures = []
                http_errors = []
                page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text}))
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                page.on(
                    "requestfailed",
                    lambda request: request_failures.append(
                        {
                            "url": request.url,
                            "method": request.method,
                            "failure": request.failure,
                        }
                    ),
                )
                page.on(
                    "response",
                    lambda response: http_errors.append({"url": response.url, "status": response.status})
                    if response.status >= 400 else None,
                )

                url = f"{BASE_URL}{target['path']}"
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_selector("[data-article-title]", timeout=10000)
                page.wait_for_function(
                    "([keyword]) => document.querySelector('[data-article-title]')?.textContent?.includes(keyword)",
                    arg=[target["keyword"]],
                    timeout=10000,
                )

                screenshot_path = EVIDENCE_DIR / f"{target['id']}-{viewport['name']}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)

                jsonld_types = page.locator('script[type="application/ld+json"]').evaluate_all(
                    """nodes => nodes.map((node) => {
                      try { return JSON.parse(node.textContent)['@type']; }
                      catch (error) { return 'parse-error'; }
                    })"""
                )
                anchors = page.locator("main a[href]").evaluate_all(
                    "nodes => nodes.map((node) => node.getAttribute('href'))"
                )

                result = {
                    "target": target["id"],
                    "viewport": viewport["name"],
                    "url": url,
                    "title": text(page, "[data-article-title]"),
                    "answer": text(page, "[data-answer-text]"),
                    "updated": page.locator("[data-article-updated]").first.get_attribute("datetime"),
                    "canonical": page.locator("link[rel='canonical']").first.get_attribute("href"),
                    "bodyHeadings": count(page, "[data-article-body] h2"),
                    "bodyParagraphs": count(page, "[data-article-body] p"),
                    "faqItems": count(page, "[data-article-faq] details"),
                    "relatedLinks": count(page, "[data-article-related] a[href]"),
                    "navigationLinks": count(page, "[data-article-navigation] a[href]"),
                    "mainInternalLinks": len([href for href in anchors if href and href.startswith("/")]),
                    "jsonLdTypes": jsonld_types,
                    "screenshot": str(screenshot_path),
                    "consoleErrors": [msg for msg in console_messages if msg["type"] == "error"],
                    "pageErrors": page_errors,
                    "requestFailures": request_failures,
                    "httpErrors": http_errors,
                }
                blocking_http_errors = [
                    item for item in http_errors
                    if not item["url"].endswith("/favicon.ico")
                ]
                blocking_console_errors = [
                    msg for msg in result["consoleErrors"]
                    if "Failed to load resource" not in msg["text"]
                ]
                result["status"] = "PASS" if (
                    target["keyword"] in result["title"]
                    and result["answer"]
                    and result["updated"]
                    and result["canonical"].endswith(target["path"])
                    and result["bodyHeadings"] >= 3
                    and result["bodyParagraphs"] >= 6
                    and result["faqItems"] == 5
                    and result["relatedLinks"] >= 3
                    and "Article" in result["jsonLdTypes"]
                    and "FAQPage" in result["jsonLdTypes"]
                    and "BreadcrumbList" in result["jsonLdTypes"]
                    and not blocking_console_errors
                    and not result["pageErrors"]
                    and not blocking_http_errors
                ) else "FAIL"
                results.append(result)
                page.close()
            context.close()
        browser.close()

    payload = {
        "baseUrl": BASE_URL,
        "chromiumExecutable": CHROMIUM_EXECUTABLE,
        "results": results,
        "summary": {
            "pass": sum(1 for row in results if row["status"] == "PASS"),
            "fail": sum(1 for row in results if row["status"] != "PASS"),
        },
    }
    output_path = EVIDENCE_DIR / "browser_acceptance.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["summary"]["fail"]:
        raise SystemExit(1)


if __name__ == "__main__":
    run()

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:9878"
EVIDENCE_DIR = Path(__file__).resolve().parent
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CASES = [
    {
        "name": "pentacles_ten_desktop",
        "path": "/articles/tarot/tarot-0077",
        "title": "錢幣十意思：牌面、正位、逆位、感情與工作怎麼看",
        "viewport": {"width": 1440, "height": 1100},
    },
    {
        "name": "pentacles_queen_mobile",
        "path": "/articles/tarot/tarot-0080",
        "title": "錢幣皇后意思：牌面、正位、逆位、感情與工作怎麼看",
        "viewport": {"width": 390, "height": 844},
    },
]


def audit_case(page, case: dict) -> dict:
    console_messages: list[dict] = []
    page_errors: list[str] = []
    request_failed: list[str] = []
    bad_responses: list[dict] = []

    # 驗收 listener 必須在導覽前完成註冊。
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
    page.wait_for_selector("[data-article-body] section", state="visible", timeout=5000)
    screenshot = EVIDENCE_DIR / f"{case['name']}.png"
    page.screenshot(path=str(screenshot), full_page=True)

    layout = page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bodyLength: [...document.querySelector('[data-article-body]').innerText.replace(/\\s/g, '')].length,
          overflowElements: [...document.querySelectorAll('body *')]
            .filter((element) => {
              const style = getComputedStyle(element);
              const rect = element.getBoundingClientRect();
              return style.display !== 'none' && style.visibility !== 'hidden'
                && rect.width > 0 && (rect.right > window.innerWidth + 1 || rect.left < -1);
            })
            .slice(0, 12)
            .map((element) => {
              const rect = element.getBoundingClientRect();
              return {
                tag: element.tagName,
                className: element.className || '',
                text: (element.textContent || '').trim().slice(0, 80),
                left: Math.round(rect.left),
                right: Math.round(rect.right),
                width: Math.round(rect.width),
              };
            }),
        })"""
    )
    headings = page.locator("[data-article-body] h2").all_text_contents()
    record = {
        "name": case["name"],
        "url": f"{BASE_URL}{case['path']}",
        "status": response.status if response else None,
        "title": page.locator("[data-article-title]").text_content().strip(),
        "body_section_count": len(headings),
        "body_length": layout["bodyLength"],
        "has_card_face_heading": any("牌面" in heading for heading in headings),
        "faq_count": page.locator("[data-article-faq] details").count(),
        "updated": page.locator("[data-article-updated]").text_content().strip(),
        "horizontal_overflow": layout["scrollWidth"] > layout["clientWidth"],
        "overflow_elements": layout["overflowElements"],
        "script_src": page.locator('script[src*="article.js"]').first.get_attribute("src") or "",
        "style_href": page.locator('link[href*="styles.css"]').first.get_attribute("href") or "",
        "traceback_text_count": page.locator("text=Traceback").count(),
        "console_messages": console_messages,
        "page_errors": page_errors,
        "request_failed": request_failed,
        "bad_responses": bad_responses,
        "screenshot": str(screenshot),
    }

    assert record["status"] == 200, record
    assert record["title"] == case["title"], record
    assert record["body_section_count"] == 6, record
    assert record["body_length"] >= 1300, record
    assert record["has_card_face_heading"], record
    assert 3 <= record["faq_count"] <= 5, record
    assert record["updated"] == "2026-07-16", record
    assert not record["horizontal_overflow"], record
    assert "article-content-20260716-1" in record["script_src"], record
    assert record["traceback_text_count"] == 0, record
    assert not [item for item in record["console_messages"] if item["type"] in {"error", "warning"}], record
    assert not record["page_errors"], record
    assert not record["request_failed"], record
    assert not record["bad_responses"], record
    return record


def main() -> None:
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME_PATH)
        for case in CASES:
            context = browser.new_context(viewport=case["viewport"])
            page = context.new_page()
            try:
                results.append(audit_case(page, case))
            finally:
                context.close()
        browser.close()

    (EVIDENCE_DIR / "browser_acceptance.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

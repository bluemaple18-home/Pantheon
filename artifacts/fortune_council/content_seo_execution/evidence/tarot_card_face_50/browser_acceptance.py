from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:9878"
EVIDENCE_DIR = Path(__file__).resolve().parent
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CASES = {
    "major_fool": "/articles/tarot/tarot-0003",
    "wands_three": "/articles/tarot/tarot-0033",
    "cups_ace": "/articles/tarot/tarot-0045",
}


def audit(page, name: str, path: str) -> dict:
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
    page.wait_for_selector("[data-article-body] section", state="visible", timeout=5000)
    headings = page.locator("[data-article-body] h2").all_text_contents()
    body_length = page.evaluate(
        "() => [...document.querySelector('[data-article-body]').innerText.replace(/\\s/g, '')].length"
    )
    screenshot = EVIDENCE_DIR / f"{name}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    result = {
        "name": name,
        "path": path,
        "status": response.status if response else None,
        "title": page.locator("[data-article-title]").text_content().strip(),
        "section_count": len(headings),
        "card_face_heading_count": sum("牌面" in heading for heading in headings),
        "body_length": body_length,
        "updated": page.locator("[data-article-updated]").text_content().strip(),
        "script_src": page.locator('script[src*="article.js"]').first.get_attribute("src") or "",
        "console_errors": console_errors,
        "page_errors": page_errors,
        "request_failures": request_failures,
        "bad_responses": bad_responses,
        "traceback_count": page.locator("text=Traceback").count(),
        "screenshot": str(screenshot.relative_to(Path.cwd())),
    }
    assert result["status"] == 200, result
    assert result["section_count"] >= 5, result
    assert result["card_face_heading_count"] >= 1, result
    assert result["body_length"] >= 800, result
    assert result["updated"] == "2026-07-16", result
    assert "tarot-card-face-20260716-1" in result["script_src"], result
    assert result["traceback_count"] == 0, result
    assert not console_errors and not page_errors and not request_failures and not bad_responses, result
    return result


def main() -> None:
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME_PATH)
        for name, path in CASES.items():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                results.append(audit(context.new_page(), name, path))
            finally:
                context.close()
        browser.close()
    (EVIDENCE_DIR / "browser_acceptance.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

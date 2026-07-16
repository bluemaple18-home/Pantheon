import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8878"
EVIDENCE_DIR = Path(__file__).resolve().parent
ARTICLE_PATHS = [
    "/articles/personality/personality-0037",
    "/articles/personality/personality-0052",
    "/articles/astrology/astrology-0028",
    "/articles/astrology/astrology-0044",
    "/articles/fortune/fortune-0027",
    "/articles/fortune/fortune-0043",
]
EXPECTED_LATEST = [
    "/articles/personality/personality-0052",
    "/articles/tarot/tarot-0080",
    "/articles/fortune/fortune-0043",
    "/articles/astrology/astrology-0044",
]


def attach_listeners(page, evidence):
    page.on("console", lambda message: evidence["console"].append({"type": message.type, "text": message.text, "location": message.location}))
    page.on("pageerror", lambda error: evidence["pageErrors"].append(str(error)))
    page.on("requestfailed", lambda request: evidence["requestFailures"].append({"url": request.url, "failure": request.failure}))
    page.on("response", lambda response: evidence["httpErrors"].append({"url": response.url, "status": response.status}) if response.status >= 400 else None)


def main():
    evidence = {
        "baseUrl": BASE_URL,
        "console": [],
        "pageErrors": [],
        "requestFailures": [],
        "httpErrors": [],
        "tracebacks": [],
        "latest": [],
        "articles": [],
        "mobile": {},
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        attach_listeners(page, evidence)
        page.goto(f"{BASE_URL}/articles", wait_until="networkidle")
        page.wait_for_selector("[data-home-articles] a")
        evidence["tracebacks"].extend(page.locator("text=Traceback").all_text_contents())
        evidence["latest"] = page.locator("[data-home-articles] a").evaluate_all(
            "nodes => nodes.map(node => new URL(node.href).pathname)"
        )
        page.screenshot(path=str(EVIDENCE_DIR / "latest-articles.png"), full_page=True)

        for path in ARTICLE_PATHS:
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            page.wait_for_function("document.querySelector('[data-article-body]')?.children.length === 4")
            evidence["tracebacks"].extend(page.locator("text=Traceback").all_text_contents())
            evidence["articles"].append({
                "path": path,
                "title": page.locator("[data-article-title]").inner_text().strip(),
                "updated": page.locator("[data-article-updated]").inner_text().strip(),
                "sectionCount": page.locator("[data-article-body] > section").count(),
                "faqCount": page.locator("[data-article-faq] details").count(),
            })

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        attach_listeners(mobile, evidence)
        mobile.goto(f"{BASE_URL}/articles", wait_until="networkidle")
        mobile.wait_for_selector("[data-home-articles] a")
        evidence["mobile"] = {
            "latestCount": mobile.locator("[data-home-articles] a").count(),
            "scrollWidth": mobile.evaluate("document.documentElement.scrollWidth"),
            "clientWidth": mobile.evaluate("document.documentElement.clientWidth"),
        }
        mobile.screenshot(path=str(EVIDENCE_DIR / "latest-articles-mobile.png"), full_page=True)
        browser.close()

    evidence["checks"] = {
        "latestFirstFour": evidence["latest"][:4] == EXPECTED_LATEST,
        "articlesValid": all(
            item["title"] and item["updated"] == "2026-07-16" and item["sectionCount"] == 4 and 3 <= item["faqCount"] <= 5
            for item in evidence["articles"]
        ),
        "mobileNoHorizontalOverflow": evidence["mobile"]["scrollWidth"] <= evidence["mobile"]["clientWidth"],
        "noTraceback": not evidence["tracebacks"],
        "noRelevantConsoleErrors": not [
            item for item in evidence["console"]
            if item["type"] == "error" and not item.get("location", {}).get("url", "").endswith("/favicon.ico")
        ],
        "noPageErrors": not evidence["pageErrors"],
        "noRequestFailures": not evidence["requestFailures"],
        "noHttpErrors": not evidence["httpErrors"],
    }
    evidence["go"] = all(evidence["checks"].values())
    (EVIDENCE_DIR / "browser-acceptance.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(json.dumps(evidence, ensure_ascii=False))
    raise SystemExit(0 if evidence["go"] else 1)


if __name__ == "__main__":
    main()

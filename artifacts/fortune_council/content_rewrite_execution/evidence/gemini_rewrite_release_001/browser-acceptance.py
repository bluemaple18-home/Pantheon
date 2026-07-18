"""50 篇文章 release 的代表性瀏覽器驗收。"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8878"
ROUTES = [
    "/articles/personality/personality-0001",
    "/articles/love/love-0005",
    "/articles/astrology/astrology-0007",
    "/articles/wealth/wealth-0012",
    "/articles/interpersonal/interpersonal-0010",
]
EVIDENCE_ROOT = Path(__file__).resolve().parent / "browser"


def main() -> int:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        for index, route in enumerate(ROUTES, start=1):
            page = context.new_page()
            console: list[dict[str, str]] = []
            page_errors: list[str] = []
            request_failures: list[dict[str, str]] = []
            abnormal_responses: list[dict[str, object]] = []

            # 必須在 goto 前掛上所有 evidence hooks。
            page.on("console", lambda message: console.append({"type": message.type, "text": message.text}))
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "requestfailed",
                lambda request: request_failures.append(
                    {"url": request.url, "error": request.failure or "unknown request failure"}
                ),
            )
            page.on(
                "response",
                lambda response: abnormal_responses.append({"url": response.url, "status": response.status})
                if response.status >= 400
                else None,
            )

            response = page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
            body_text = page.locator("body").inner_text()
            article_body = page.locator("[data-article-body]").inner_text()
            headings = page.locator("[data-article-body] h2").all_inner_texts()
            title = page.locator("h1").first.inner_text()
            visible_traceback = any(
                marker in body_text
                for marker in ("Traceback (most recent call last)", "Internal Server Error", "Application error")
            )
            screenshot = EVIDENCE_ROOT / f"{index:02d}-{route.rsplit('/', 1)[-1]}.png"
            page.screenshot(path=screenshot.as_posix(), full_page=True)
            console_errors = [item for item in console if item["type"] == "error"]
            passed = bool(
                response
                and response.status == 200
                and title.strip()
                and len(article_body) >= 650
                and len(headings) >= 3
                and not visible_traceback
                and not console_errors
                and not page_errors
                and not request_failures
                and not abnormal_responses
            )
            results.append(
                {
                    "route": route,
                    "http_status": response.status if response else None,
                    "title": title,
                    "body_characters": len(article_body),
                    "h2_count": len(headings),
                    "headings": headings,
                    "visible_traceback": visible_traceback,
                    "console": console,
                    "console_errors": console_errors,
                    "page_errors": page_errors,
                    "request_failures": request_failures,
                    "abnormal_responses": abnormal_responses,
                    "screenshot": screenshot.relative_to(Path(__file__).resolve().parent).as_posix(),
                    "status": "PASS" if passed else "FAIL",
                }
            )
            page.close()
        context.close()
        browser.close()

    evidence = {
        "card_id": "CARD-CONTENT-GEMINI-REWRITE-RELEASE-001",
        "type": "browser-acceptance",
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "scope": "五個類別的代表性 release 文章頁",
        "excluded": "部署、遠端正式環境與其餘 45 頁逐頁視覺檢查",
        "hooks_registered_before_navigation": True,
        "root_question": "50 篇改寫套用後，代表頁是否可在瀏覽器正常載入與閱讀？",
        "blocker": None,
        "fork": "READY_TO_DEPLOY" if all(item["status"] == "PASS" for item in results) else "BLOCKED",
        "results": results,
        "deploy_executed": False,
    }
    (EVIDENCE_ROOT / "browser-acceptance.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": evidence["status"], "pages": len(results)}, ensure_ascii=False))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

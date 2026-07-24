#!/usr/bin/env python3
"""驗證 Pantheon 的 Playwright Chromium runtime 與基本瀏覽器能力。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback
from typing import MutableMapping
from urllib.parse import quote


def configure_playwright_browsers_path(
    environ: MutableMapping[str, str] | None = None,
    *,
    home: Path | None = None,
) -> str | None:
    """在 import Playwright 前解析 ai-core 共用 browser cache。"""

    environ = os.environ if environ is None else environ
    configured = environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if configured:
        return configured

    home = Path.home() if home is None else home
    candidates = []
    if environ.get("AI_CORE_CACHE_DIR"):
        candidates.append(Path(environ["AI_CORE_CACHE_DIR"]) / "ms-playwright")
    if environ.get("AI_CORE_DIR"):
        candidates.append(Path(environ["AI_CORE_DIR"]) / ".tools/cache/ms-playwright")
    candidates.append(home / "ai-core/.tools/cache/ms-playwright")

    for candidate in candidates:
        if candidate.is_dir():
            resolved = str(candidate.resolve())
            environ["PLAYWRIGHT_BROWSERS_PATH"] = resolved
            return resolved
    return None


configure_playwright_browsers_path()

from playwright.sync_api import sync_playwright  # noqa: E402


DEFAULT_HTML = """<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>Pantheon Chromium Runtime</title></head>
<body>
  <main id="runtime-check">ready</main>
  <script>document.documentElement.dataset.runtimeReady = "true";</script>
</body>
</html>
"""
DEFAULT_URL = f"data:text/html;charset=utf-8,{quote(DEFAULT_HTML)}"


def evaluate_evidence(evidence: dict[str, object]) -> str:
    """依可觀察證據判定 browser acceptance 結果。"""

    console_errors = [
        item
        for item in evidence["console"]
        if isinstance(item, dict) and item.get("type") == "error"
    ]
    failed = any(
        (
            evidence["traceback"],
            console_errors,
            evidence["pageerror"],
            evidence["requestfailed"],
            evidence["http_errors"],
            not evidence["javascript_ready"],
        )
    )
    return "FAIL" if failed else "PASS"


def run_check(url: str, screenshot: Path) -> dict[str, object]:
    """啟動 Chromium、掛上證據 hooks、開頁、執行 JavaScript 並截圖。"""

    evidence: dict[str, object] = {
        "traceback": [],
        "console": [],
        "pageerror": [],
        "requestfailed": [],
        "http_errors": [],
        "javascript_ready": False,
    }
    screenshot.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            executable_path = playwright.chromium.executable_path
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})

            # 驗收協議：所有 listener 必須在 goto 前註冊。
            page.on(
                "console",
                lambda message: evidence["console"].append(
                    {"type": message.type, "text": message.text}
                ),
            )
            page.on(
                "pageerror",
                lambda error: evidence["pageerror"].append(str(error)),
            )
            page.on(
                "requestfailed",
                lambda request: evidence["requestfailed"].append(
                    {"url": request.url, "failure": request.failure}
                ),
            )
            page.on(
                "response",
                lambda response: evidence["http_errors"].append(
                    {"url": response.url, "status": response.status}
                )
                if response.status >= 400
                else None,
            )

            page.goto(url, wait_until="load", timeout=30_000)
            evidence["javascript_ready"] = page.evaluate(
                "() => document.readyState === 'complete'"
            )
            evidence["title"] = page.title()
            page.screenshot(path=str(screenshot), full_page=True)
            evidence["browser_version"] = browser.version
            evidence["executable_path"] = executable_path
            browser.close()
    except Exception:  # noqa: BLE001 - 健康檢查必須保存完整啟動證據。
        evidence["traceback"] = traceback.format_exc().splitlines()

    evidence["url"] = url
    evidence["screenshot"] = str(screenshot.resolve())
    evidence["status"] = evaluate_evidence(evidence)
    return evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="要驗收的頁面 URL")
    parser.add_argument(
        "--screenshot",
        type=Path,
        default=Path(".work/browser-acceptance/chromium-runtime.png"),
        help="驗收截圖輸出位置",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence = run_check(args.url, args.screenshot)
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

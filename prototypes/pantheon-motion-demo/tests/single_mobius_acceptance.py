from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_motion_img2threejs" / "evidence"
BASE_URL = "http://127.0.0.1:5173/?studio=1&capture=1&prototype=single-mobius"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME) if CHROME.exists() else None,
        )
        context = browser.new_context(
            viewport={"width": 720, "height": 864},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text)
                if message.type in {"error", "warning"}
                else None
            ),
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: request_failures.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )

        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function("Boolean(window.__PANTHEON_STUDIO__)")

        captures: dict[str, str] = {}
        for view in ("front", "orbit", "side"):
            page.evaluate(
                """(view) => {
                  window.__PANTHEON_STUDIO__.setView(view);
                  window.__PANTHEON_STUDIO__.setTime(0);
                }""",
                view,
            )
            output = EVIDENCE / f"single-mobius-{view}.png"
            page.screenshot(path=str(output), omit_background=True)
            captures[view] = str(output.relative_to(ROOT))

        runtime = page.evaluate(
            """() => {
              const studio = window.__PANTHEON_STUDIO__;
              const runtime = studio.orb.userData.sculptRuntime;
              return {
                nodes: Object.keys(runtime.nodes),
                meshes: Object.keys(runtime.meshes),
                pivots: Object.keys(runtime.bandPivots),
                calls: studio.renderer.info.render.calls,
                triangles: studio.renderer.info.render.triangles,
              };
            }"""
        )
        result = {
            "httpStatus": response.status if response else None,
            "runtime": runtime,
            "captures": captures,
            "consoleErrors": console_errors,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
        }
        output_json = EVIDENCE / "single-mobius-browser-evidence.json"
        output_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        browser.close()

    assert result["httpStatus"] == 200, result
    assert result["runtime"]["pivots"] == ["mobius"], result
    assert result["runtime"]["triangles"] < 100_000, result
    assert not console_errors, result
    assert not page_errors, result
    assert not request_failures, result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

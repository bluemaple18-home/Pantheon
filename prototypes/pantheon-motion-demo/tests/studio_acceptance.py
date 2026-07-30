from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_motion_img2threejs" / "evidence"
BASE_URL = "http://127.0.0.1:5173/?studio=1&capture=1"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console: list[dict[str, str]] = []
    page_errors: list[str] = []
    request_failures: list[dict[str, str]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME) if CHROME.exists() else None,
        )
        context = browser.new_context(
            viewport={"width": 720, "height": 864},
            device_scale_factor=1,
            reduced_motion="no-preference",
        )
        page = context.new_page()

        # Evidence hooks must be registered before navigation.
        page.on(
            "console",
            lambda message: console.append(
                {"type": message.type, "text": message.text}
            ),
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: request_failures.append(
                {
                    "url": request.url,
                    "error": request.failure or "unknown request failure",
                }
            ),
        )

        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function("Boolean(window.__PANTHEON_STUDIO__)")
        page.evaluate("window.__PANTHEON_STUDIO__.setTime(0)")

        runtime = page.evaluate(
            """() => {
              const studio = window.__PANTHEON_STUDIO__;
              const runtime = studio.orb.userData.sculptRuntime;
              const canvas = studio.renderer.domElement;
              return {
                responseCanvas: {
                  width: canvas.width,
                  height: canvas.height,
                  dataUrlLength: canvas.toDataURL("image/png").length,
                },
                renderInfo: {
                  calls: studio.renderer.info.render.calls,
                  triangles: studio.renderer.info.render.triangles,
                  lines: studio.renderer.info.render.lines,
                  geometries: studio.renderer.info.memory.geometries,
                },
                nodeNames: Object.keys(runtime.nodes),
                meshNames: Object.keys(runtime.meshes),
                socketNames: Object.keys(runtime.sockets),
                bandPivotNames: Object.keys(runtime.bandPivots),
                loopSeconds: studio.loopSeconds,
              };
            }"""
        )

        captures = {}
        for view, time_value in (("front", 0), ("orbit", 4.5), ("side", 8.25)):
            page.evaluate(
                """([view, timeValue]) => {
                  window.__PANTHEON_STUDIO__.setView(view);
                  window.__PANTHEON_STUDIO__.setTime(timeValue);
                }""",
                [view, time_value],
            )
            output = EVIDENCE / f"render-{view}.png"
            page.screenshot(path=str(output), omit_background=True)
            captures[view] = str(output.relative_to(ROOT))

        page.evaluate(
            """() => {
              window.__PANTHEON_STUDIO__.setView("front");
              window.__PANTHEON_STUDIO__.setTime(0);
              window.__PANTHEON_STUDIO__.setMaterialMode("blockout");
            }"""
        )
        blockout_output = EVIDENCE / "render-blockout.png"
        page.screenshot(path=str(blockout_output), omit_background=True)
        captures["blockout"] = str(blockout_output.relative_to(ROOT))
        page.evaluate('window.__PANTHEON_STUDIO__.setMaterialMode("reference")')

        result = {
            "url": BASE_URL,
            "httpStatus": response.status if response else None,
            "runtime": runtime,
            "captures": captures,
            "traceback": [],
            "console": console,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
        }
        (EVIDENCE / "studio-browser-evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        browser.close()

    assert result["httpStatus"] == 200, result
    assert result["runtime"]["responseCanvas"] == {
        "width": 720,
        "height": 864,
        "dataUrlLength": result["runtime"]["responseCanvas"]["dataUrlLength"],
    }
    assert result["runtime"]["responseCanvas"]["dataUrlLength"] > 50_000, result
    assert result["runtime"]["renderInfo"]["calls"] <= 48, result
    assert result["runtime"]["renderInfo"]["triangles"] <= 180_000, result
    assert result["runtime"]["bandPivotNames"] == [
        "gold",
        "teal",
        "rose",
        "navy",
        "bronze",
    ], result
    assert not page_errors, result
    assert not request_failures, result
    assert not [
        item for item in console if item["type"] in {"error", "warning"}
    ], result

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

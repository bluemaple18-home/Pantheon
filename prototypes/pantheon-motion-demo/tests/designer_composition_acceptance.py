from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = (
    ROOT
    / "artifacts"
    / "pantheon_designer_composition_b2_1"
    / "after"
)
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-designer-composition&capture=1"
)
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
VIEWS = [
    "front",
    "back",
    "left",
    "right",
    "top",
    "bottom",
    "front-left",
    "front-right",
]


def attach_evidence_hooks(
    page: Page,
    console: list[dict[str, str]],
    page_errors: list[str],
    request_failures: list[str],
) -> None:
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
            f"{request.method} {request.url}: {request.failure}"
        ),
    )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console: list[dict[str, str]] = []
    page_errors: list[str] = []
    request_failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME) if CHROME.exists() else None,
        )
        context = browser.new_context(
            viewport={"width": 1120, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()
        attach_evidence_hooks(
            page,
            console,
            page_errors,
            request_failures,
        )
        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_DESIGNER__?.curves)"
        )
        canvas = page.locator("canvas")
        previews: dict[str, str] = {}
        for view in VIEWS:
            page.evaluate(
                "(view) => window.__PANTHEON_DESIGNER__.setView(view)",
                view,
            )
            path = EVIDENCE / f"{view}.png"
            canvas.screenshot(path=str(path))
            previews[view] = str(path.relative_to(ROOT))

        page.evaluate(
            "() => window.__PANTHEON_DESIGNER__.setView('front')"
        )
        page.evaluate(
            "() => window.__PANTHEON_DESIGNER__.setMonochrome(true)"
        )
        monochrome_path = EVIDENCE / "front-monochrome.png"
        canvas.screenshot(path=str(monochrome_path))
        page.evaluate(
            "() => window.__PANTHEON_DESIGNER__.setMonochrome(false)"
        )

        debug_previews: dict[str, str] = {}
        for mode, filename in [
            ("reference-sphere", "debug-reference-sphere.png"),
            ("shell-weight", "debug-shell-weight.png"),
            ("density-grid", "debug-nine-grid-density.png"),
        ]:
            page.evaluate(
                "(mode) => "
                "window.__PANTHEON_DESIGNER__."
                "setCompositionDebugMode(mode)",
                mode,
            )
            path = EVIDENCE / filename
            canvas.screenshot(path=str(path))
            debug_previews[mode] = str(path.relative_to(ROOT))
        page.evaluate(
            "() => window.__PANTHEON_DESIGNER__."
            "setCompositionDebugMode('none')"
        )

        solo_previews: dict[str, str] = {}
        for curve_id in [
            "constellation",
            "tarot",
            "mbti",
            "human-design",
            "ziwei-bazi",
        ]:
            page.evaluate(
                "(id) => window.__PANTHEON_DESIGNER__.setSoloTrack(id)",
                curve_id,
            )
            path = EVIDENCE / f"solo-{curve_id}.png"
            canvas.screenshot(path=str(path))
            solo_previews[curve_id] = str(path.relative_to(ROOT))
        page.evaluate(
            "() => window.__PANTHEON_DESIGNER__.setSoloTrack(null)"
        )

        runtime = page.evaluate(
            """() => {
              const root = window.__PANTHEON_DESIGNER__.curves;
              const runtime = root.userData.compositionRuntime;
              return {
                rootName: root.name,
                rootChildren: root.children.map(child => child.name),
                trackNames: runtime.trackGroup.children.map(
                  child => child.name
                ),
                trackCount: runtime.trackGroup.children.length,
                coreName: runtime.core.name,
                metrics: runtime.metrics,
                monochrome: runtime.getMonochrome(),
                renderCalls:
                  window.__PANTHEON_DESIGNER__.renderer.info.render.calls,
              };
            }"""
        )
        browser.close()

    failures: list[str] = []
    if not response or response.status != 200:
        failures.append("HTTP status is not 200")
    if page_errors:
        failures.append(f"page errors: {page_errors}")
    if request_failures:
        failures.append(f"request failures: {request_failures}")
    if runtime["trackCount"] != 5:
        failures.append("formal composition does not contain five tracks")
    forbidden = ("Inner", "Occlusion", "Aperture", "Ribbon", "Mobius")
    all_names = runtime["rootChildren"] + runtime["trackNames"]
    if any(any(term in name for term in forbidden) for name in all_names):
        failures.append("forbidden formal mesh found")
    if runtime["coreName"] != "CoreTimeSphere":
        failures.append("time core is missing")
    metrics = runtime["metrics"]
    for metric in metrics["curveMetrics"]:
        if metric["shellCoverage"] < 0.65:
            failures.append(
                f"{metric['id']}: shell coverage below 65%"
            )
        if metric["minRadius"] < 0.48:
            failures.append(
                f"{metric['id']}: radius below 0.48"
            )
        if metric["maxRadius"] > 1.04:
            failures.append(
                f"{metric['id']}: radius above 1.04"
            )
    if metrics["centroidLength"] > 0.06:
        failures.append("curve centroid is outside 0.06")
    if metrics["extent"]["ratio"] > 1.12:
        failures.append("extent ratio is above 1.12")
    if metrics["nineGridDensity"][4] <= 0:
        failures.append("nine-grid center cell is empty")
    if metrics["nineGridMaxToMean"] > 2.2:
        failures.append("nine-grid density exceeds 2.2x mean")

    result = {
        "url": BASE_URL,
        "httpStatus": response.status if response else None,
        "console": console,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "runtime": runtime,
        "previews": {
            **previews,
            "frontMonochrome": str(monochrome_path.relative_to(ROOT)),
            "debug": debug_previews,
            "solo": solo_previews,
        },
        "acceptance": {
            "fiveTracksOnly": runtime["trackCount"] == 5,
            "hasTimeCore": runtime["coreName"] == "CoreTimeSphere",
            "noForbiddenFormalMeshes": not any(
                any(term in name for term in forbidden)
                for name in all_names
            ),
            "extentRatioWithinTarget":
                runtime["metrics"]["extent"]["ratio"] <= 1.12,
            "centroidWithinTarget":
                runtime["metrics"]["centroidLength"] <= 0.06,
            "shellCoverageMinimumPass": all(
                metric["shellCoverage"] >= 0.65
                for metric in runtime["metrics"]["curveMetrics"]
            ),
            "radiusRangePass": all(
                metric["minRadius"] >= 0.48
                and metric["maxRadius"] <= 1.04
                for metric in runtime["metrics"]["curveMetrics"]
            ),
            "nineGridDensityPass":
                runtime["metrics"]["nineGridDensity"][4] > 0
                and runtime["metrics"]["nineGridMaxToMean"] <= 2.2,
            "failures": failures,
        },
    }
    (EVIDENCE / "browser-evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["runtime"]["metrics"], indent=2))
    print(json.dumps(result["acceptance"], ensure_ascii=False, indent=2))
    if failures:
        raise AssertionError("; ".join(failures))


if __name__ == "__main__":
    main()

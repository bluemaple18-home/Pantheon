from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_designer_curves_b0"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-designer-b0&capture=1"
)
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CURVES = [
    "constellation",
    "tarot",
    "mbti",
    "human-design",
    "ziwei-bazi",
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
        previews: dict[str, dict[str, str]] = {}
        for curve_id in CURVES:
            curve_dir = EVIDENCE / curve_id
            curve_dir.mkdir(parents=True, exist_ok=True)
            page.evaluate(
                "(id) => window.__PANTHEON_DESIGNER__.setSoloCurve(id)",
                curve_id,
            )
            previews[curve_id] = {}
            for mode, filename in [
                ("line", "white-line.png"),
                ("control-points", "control-points.png"),
                ("curvature", "curvature-heatmap.png"),
            ]:
                page.evaluate(
                    "(mode) => window.__PANTHEON_DESIGNER__.setDebugMode(mode)",
                    mode,
                )
                target = curve_dir / filename
                canvas.screenshot(path=str(target))
                previews[curve_id][mode] = str(target.relative_to(ROOT))

        runtime = page.evaluate(
            """() => ({
              metrics: window.__PANTHEON_DESIGNER__.getMetrics(),
              configs: window.__PANTHEON_DESIGNER__.getConfigs(),
              rootName: window.__PANTHEON_DESIGNER__.curves.name,
              rootChildren:
                window.__PANTHEON_DESIGNER__.curves.children.map(
                  child => child.name
                ),
              sceneMeshes:
                window.__PANTHEON_DESIGNER__.scene.children.map(
                  child => child.name
                ),
              exportedJSON: window.__PANTHEON_DESIGNER__.exportJSON(),
              renderCalls:
                window.__PANTHEON_DESIGNER__.renderer.info.render.calls,
            })"""
        )
        browser.close()

    metrics = runtime["metrics"]
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    validation_failures: list[str] = []
    if not response or response.status != 200:
        validation_failures.append("HTTP status is not 200")
    if page_errors:
        validation_failures.append(f"page errors: {page_errors}")
    if request_failures:
        validation_failures.append(
            f"request failures: {request_failures}"
        )
    if len(runtime["configs"]) != 5:
        validation_failures.append("curve config count is not five")
    if len(runtime["rootChildren"]) != 5:
        validation_failures.append("rendered curve group count is not five")
    for metric in metrics:
        if not 8 <= metric["controlPointCount"] <= 12:
            validation_failures.append(
                f"{metric['id']}: control point count outside 8..12"
            )
        if not metric["closed"] or metric["seamDistance"] >= 1e-6:
            validation_failures.append(f"{metric['id']}: seam is not closed")
        if metric["hasSelfIntersection"]:
            validation_failures.append(
                f"{metric['id']}: self intersection detected"
            )
        if metric["hasSmallLoop"]:
            validation_failures.append(f"{metric['id']}: small loop detected")
        if metric["minimumBendingRadiusRatio"] < 0.18:
            validation_failures.append(
                f"{metric['id']}: minimum bending radius ratio "
                f"{metric['minimumBendingRadiusRatio']:.4f} < 0.18"
            )

    exported = json.loads(runtime.pop("exportedJSON"))
    (EVIDENCE / "exported-designer-curves.json").write_text(
        json.dumps(exported, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = {
        "url": BASE_URL,
        "httpStatus": response.status if response else None,
        "console": console,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "runtime": runtime,
        "previews": previews,
        "acceptance": {
            "fiveSoloCurvesOnly": len(runtime["rootChildren"]) == 5,
            "allControlPointCountsWithinRange": all(
                8 <= metric["controlPointCount"] <= 12
                for metric in metrics
            ),
            "allClosed": all(metric["closed"] for metric in metrics),
            "noSelfIntersections": all(
                not metric["hasSelfIntersection"] for metric in metrics
            ),
            "noSmallLoops": all(
                not metric["hasSmallLoop"] for metric in metrics
            ),
            "minimumBendingRadiusPass": all(
                metric["minimumBendingRadiusRatio"] >= 0.18
                for metric in metrics
            ),
            "noInnerSphereOrCoreInScene": all(
                "Sphere" not in name and "Core" not in name
                for name in runtime["sceneMeshes"]
            ),
            "validationFailures": validation_failures,
        },
    }
    (EVIDENCE / "browser-evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["acceptance"], ensure_ascii=False, indent=2))
    if validation_failures:
        raise AssertionError("; ".join(validation_failures))


if __name__ == "__main__":
    main()

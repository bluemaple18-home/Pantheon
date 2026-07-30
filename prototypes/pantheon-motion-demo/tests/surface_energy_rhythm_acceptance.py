from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "pantheon_surface_energy_rhythm"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits&capture=1"
    "&geometryVersion=v1.1&freezeOrbit=1"
)


def attach_hooks(
    page: Page,
    console_errors: list[str],
    page_errors: list[str],
    request_failures: list[str],
) -> None:
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text)
            if message.type == "error"
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


def snapshot(page: Page) -> dict:
    return page.evaluate(
        "() => window.__PANTHEON_STAR_ORBITS__.interaction"
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        attach_hooks(page, console_errors, page_errors, request_failures)
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        visual_delta = page.evaluate(
            """async () => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setOrbitMotionPaused(true);
              studio.setDebugDisplay({
                validationMode: "material-v3",
                showCore: false
              });
              const source = studio.renderer.domElement;
              const sample = document.createElement("canvas");
              sample.width = 180;
              sample.height = 180;
              const context = sample.getContext("2d", {
                willReadFrequently: true
              });
              const read = () => {
                context.drawImage(source, 0, 0, 180, 180);
                return context.getImageData(0, 0, 180, 180).data.slice();
              };
              const before = read();
              await new Promise((resolve) => setTimeout(resolve, 2400));
              const after = read();
              let totalDelta = 0;
              let changedPixels = 0;
              const pixelCount = before.length / 4;
              for (let index = 0; index < before.length; index += 4) {
                const delta =
                  Math.abs(before[index] - after[index]) +
                  Math.abs(before[index + 1] - after[index + 1]) +
                  Math.abs(before[index + 2] - after[index + 2]);
                totalDelta += delta / 3;
                if (delta >= 12) changedPixels += 1;
              }
              studio.setDebugDisplay({ showCore: true });
              return {
                meanRgbDelta: totalDelta / pixelCount,
                changedPixelRatio: changedPixels / pixelCount
              };
            }"""
        )
        before = snapshot(page)
        geometry_before = page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.geometryLock"
        )
        page.wait_for_timeout(1200)
        after = snapshot(page)
        geometry_after = page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.geometryLock"
        )
        page.locator("[data-pantheon-star-orbits] canvas").screenshot(
            path=str(OUTPUT / "desktop.png")
        )

        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__"
            ".setReducedMotionPreview(true)"
        )
        reduced = snapshot(page)
        browser.close()

    before_visuals = before["visuals"]
    after_visuals = after["visuals"]
    phases_before = {
        theme: visual["energyPhase"]
        for theme, visual in before_visuals.items()
    }
    phases_after = {
        theme: visual["energyPhase"]
        for theme, visual in after_visuals.items()
    }
    checks = {
        "geometry_unchanged": geometry_before == geometry_after,
        "five_distinct_cycles": (
            len(
                {
                    visual["energyCycleSeconds"]
                    for visual in after_visuals.values()
                }
            )
            == 5
        ),
        "flow_speed_is_visibly_faster": (
            min(
                visual["energyCycleSeconds"]
                for visual in after_visuals.values()
            )
            <= 12
            and max(
                visual["energyCycleSeconds"]
                for visual in after_visuals.values()
            )
            <= 20
        ),
        "all_phases_move": all(
            phases_before[theme] != phases_after[theme]
            for theme in phases_before
        ),
        "normal_view_light_is_visibly_moving": (
            visual_delta["meanRgbDelta"] >= 0.02
            and visual_delta["changedPixelRatio"] >= 0.001
        ),
        "moving_light_stays_local_to_symbols": (
            visual_delta["changedPixelRatio"] <= 0.02
        ),
        "surface_energy_is_bounded": all(
            1 <= visual["energyPulseCount"] <= 2
            and 0.3 <= visual["flowIntensity"] <= 0.48
            for visual in after_visuals.values()
        ),
        "reduced_motion_disables_flow": all(
            visual["energyPulseCount"] == 0
            and visual["flowIntensity"] == 0
            for visual in reduced["visuals"].values()
        ),
        "marks_stay_fixed": (
            after["surfaceMarks"]["fixedToBandUv"]
            and not after["surfaceMarks"]["independentMotion"]
            and after["surfaceMarks"]["marksRemainFixedWhileLightMoves"]
            and not after["surfaceMarks"]["wholeTextureTranslation"]
        ),
        "marks_visible_on_both_sides_before_lighting": (
            after["surfaceMarks"]["idleVisible"]
            and after["surfaceMarks"]["idleMarkOpacity"] >= 0.4
            and after["surfaceMarks"]["renderedSurfaces"]
            == ["top", "bottom"]
            and after["surfaceMarks"]["samePatternOnBothSurfaces"]
        ),
        "lighting_enhances_existing_marks": (
            after["surfaceMarks"]["illuminatedUsesSameMarks"]
            and after["surfaceMarks"]["illuminationAddsToIdleBaseline"]
        ),
        "idle_marks_have_strong_relief": (
            after["surfaceMarks"]["reliefNormalStrength"] >= 0.75
            and after["surfaceMarks"]["contactShadow"]
            and after["surfaceMarks"]["bevelHighlight"]
        ),
        "no_forbidden_effects": not any(
            after["effects"]["forbiddenEffects"].values()
        ),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "checks": checks,
        "phasesBefore": phases_before,
        "phasesAfter": phases_after,
        "surfaceEnergy": after["effects"]["surfaceEnergy"],
        "visualDelta": visual_delta,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
    }
    (OUTPUT / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

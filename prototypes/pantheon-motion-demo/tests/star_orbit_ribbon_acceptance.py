from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_star_orbits" / "final_lock"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits&capture=1&view=front"
)
VIEWS = {
    "front": "front",
    "side": "right",
    "back": "back",
    "front-left": "front-left",
    "front-right": "front-right",
    "top": "top",
}


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


def read_runtime(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const root = studio.orbits;
          const visibleGroups = root.children
            .filter(child => child.visible)
            .map(child => child.name);
          const core = root.getObjectByName("SelfCore");
          return {
            configs: studio.configs,
            metrics: studio.metrics,
            ribbonMetrics: studio.ribbonMetrics,
            geometryLock: studio.geometryLock,
            visibleGroups,
            coreRadius: core.userData.radius,
            corePosition: core.position.toArray(),
            renderCalls: studio.renderer.info.render.calls,
          };
        }"""
    )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        attach_hooks(
            page,
            console_errors,
            page_errors,
            request_failures,
        )
        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        canvas = page.locator("[data-pantheon-star-orbits] canvas")
        initial = read_runtime(page)

        for output_name, view in VIEWS.items():
            page.evaluate(
                "(value) => window.__PANTHEON_STAR_ORBITS__.setView(value)",
                view,
            )
            canvas.screenshot(
                path=str(EVIDENCE / f"locked-{output_name}.png")
            )

        page.evaluate(
            """() => {
              window.__PANTHEON_STAR_ORBITS__.setPresentationMode(
                "narrow-ribbon"
              );
              window.__PANTHEON_STAR_ORBITS__.setView("front");
            }"""
        )
        narrow_front = read_runtime(page)
        canvas.screenshot(path=str(EVIDENCE / "narrow-ribbon-front.png"))
        for output_name, view in (
            ("front-left", "front-left"),
            ("side", "right"),
            ("top", "top"),
        ):
            page.evaluate(
                "(value) => window.__PANTHEON_STAR_ORBITS__.setView(value)",
                view,
            )
            canvas.screenshot(
                path=str(
                    EVIDENCE / f"narrow-ribbon-{output_name}.png"
                )
            )

        page.evaluate(
            """() => {
              window.__PANTHEON_STAR_ORBITS__.setPresentationMode(
                "mobius-frame"
              );
              window.__PANTHEON_STAR_ORBITS__.setView("front");
            }"""
        )
        mobius_front = read_runtime(page)
        canvas.screenshot(path=str(EVIDENCE / "mobius-frame-front.png"))
        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front-left')"
        )
        canvas.screenshot(
            path=str(EVIDENCE / "mobius-frame-front-left.png")
        )

        page.get_by_role("button", name="Centerline").click()
        page.get_by_role("button", name="Narrow Ribbon").click()
        page.get_by_label("Ribbon width control").fill("0.017")
        adjusted_ribbon = read_runtime(page)
        page.get_by_label("Ribbon width control").fill("0.018")
        restored_ribbon = read_runtime(page)
        page.get_by_role("button", name="Centerline").click()
        final = read_runtime(page)
        page.screenshot(
            path=str(EVIDENCE / "locked-desktop-ui.png"),
            full_page=True,
        )

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        attach_hooks(
            mobile,
            console_errors,
            page_errors,
            request_failures,
        )
        mobile.goto(BASE_URL, wait_until="networkidle")
        mobile.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        mobile.evaluate(
            """() => {
              window.__PANTHEON_STAR_ORBITS__.setPresentationMode(
                "narrow-ribbon"
              );
              window.__PANTHEON_STAR_ORBITS__.setView("front-left");
            }"""
        )
        mobile.locator(
            "[data-pantheon-star-orbits] canvas"
        ).screenshot(path=str(EVIDENCE / "narrow-ribbon-mobile.png"))
        mobile.screenshot(
            path=str(EVIDENCE / "locked-mobile-ui.png"),
            full_page=True,
        )
        browser.close()

    ribbon = initial["ribbonMetrics"]
    lock = initial["geometryLock"]
    regular_frames = ribbon["regular"]
    mobius_frames = ribbon["mobius"]
    checks = {
        "http_ok": response is not None and response.ok,
        "geometry_locked": (
            lock["locked"]
            and lock["signature"] == lock["currentSignature"]
            and lock["orbitCount"] == 5
            and all(
                position == [0, 0, 0]
                for position in lock["positions"].values()
            )
        ),
        "final_pose_selected": (
            initial["configs"][0]["inclination"] == 32
            and initial["configs"][0]["azimuth"] == 58
            and initial["configs"][0]["roll"] == -31
            and initial["configs"][2]["azimuth"] == 335
            and initial["configs"][2]["roll"] == 49.6
            and initial["configs"][4]["roll"] == 172.2
            and all(config["scale"] == 1 for config in initial["configs"])
        ),
        "self_core_locked": (
            initial["coreRadius"] == 0.14
            and initial["corePosition"] == [0, 0, 0]
        ),
        "narrow_prototype_contract": (
            ribbon["width"] == 0.018
            and ribbon["thickness"] == 0.003
            and ribbon["width"] < 0.03
        ),
        "regular_frames_stable": all(
            frame["minimumAdjacentFrameDot"] > 0.999
            and frame["seamAlignment"] > 0.999
            and frame["frameFlipCount"] == 0
            and frame["maxOrthonormalError"] < 1e-9
            and frame["degenerateTriangleCount"] == 0
            for frame in regular_frames
        ),
        "mobius_frames_stable": all(
            frame["minimumAdjacentFrameDot"] > 0.999
            and frame["seamAlignment"] > 0.999
            and frame["frameFlipCount"] == 0
            and frame["maxOrthonormalError"] < 1e-9
            and frame["degenerateTriangleCount"] == 0
            for frame in mobius_frames
        ),
        "no_shell_penetration": (
            ribbon["minimumShellClearance"] > 0
            and not ribbon["hasShellPenetration"]
        ),
        "presentation_modes_work": (
            "NarrowRibbonPrototype" in narrow_front["visibleGroups"]
            and "MobiusFramePrototype" in mobius_front["visibleGroups"]
            and "StarOrbitTracks" in final["visibleGroups"]
        ),
        "width_control_rebuilds": (
            adjusted_ribbon["ribbonMetrics"]["width"] == 0.017
            and restored_ribbon["ribbonMetrics"]["width"] == 0.018
        ),
        "lock_survives_prototypes": (
            initial["geometryLock"]["signature"]
            == final["geometryLock"]["currentSignature"]
        ),
        "renders_geometry": initial["renderCalls"] > 0,
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "runtime": initial,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "evidence": [
            str(path.relative_to(ROOT))
            for path in sorted(EVIDENCE.glob("*.png"))
        ],
    }
    (EVIDENCE / "ribbon-acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

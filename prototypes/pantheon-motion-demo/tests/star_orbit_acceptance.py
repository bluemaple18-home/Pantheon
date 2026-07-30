from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_star_orbits"
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
          const trackGroup = studio.orbits.getObjectByName("StarOrbitTracks");
          const core = studio.orbits.getObjectByName("SelfCore");
          return {
            rootName: studio.orbits.name,
            childNames: trackGroup.children.map(child => child.name),
            childRoles: trackGroup.children.map(
              child => child.userData.geometryRole
            ),
            core: {
              name: core.name,
              position: core.position.toArray(),
              radius: core.userData.radius,
              role: core.userData.geometryRole,
              color: `#${core.material.color.getHexString()}`,
            },
            configs: studio.configs,
            metrics: studio.metrics,
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
        desktop = browser.new_page(viewport={"width": 1280, "height": 900})
        attach_hooks(
            desktop,
            console_errors,
            page_errors,
            request_failures,
        )
        response = desktop.goto(BASE_URL, wait_until="networkidle")
        desktop.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        canvas = desktop.locator("[data-pantheon-star-orbits] canvas")
        initial = read_runtime(desktop)

        for output_name, view_name in VIEWS.items():
            desktop.evaluate(
                "(view) => window.__PANTHEON_STAR_ORBITS__.setView(view)",
                view_name,
            )
            canvas.screenshot(
                path=str(EVIDENCE / f"{output_name}.png")
            )

        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
        )
        canvas.screenshot(path=str(EVIDENCE / "self-core.png"))
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(true)"
        )
        canvas.screenshot(path=str(EVIDENCE / "monochrome.png"))
        monochrome = read_runtime(desktop)
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(false)"
        )

        original_inclination = initial["configs"][0]["inclination"]
        desktop.get_by_label("Constellation Inclination").fill("61")
        adjusted = read_runtime(desktop)
        desktop.get_by_role(
            "button", name="Reset Orbit Angles"
        ).click()
        reset = read_runtime(desktop)
        desktop.get_by_role(
            "button", name="Export Orbit Config"
        ).click()
        export_value = desktop.locator("textarea").input_value()
        desktop.screenshot(
            path=str(EVIDENCE / "desktop-ui.png"),
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
        mobile.screenshot(
            path=str(EVIDENCE / "mobile-ui.png"),
            full_page=True,
        )
        mobile_canvas = mobile.locator(
            "[data-pantheon-star-orbits] canvas"
        ).bounding_box()
        browser.close()

    metrics = initial["metrics"]
    configs = initial["configs"]
    checks = {
        "http_ok": response is not None and response.ok,
        "exactly_five_orbits": metrics["orbitCount"] == 5,
        "only_orbit_tracks": (
            len(initial["childNames"]) == 5
            and all(
                name.startswith("StarOrbit.")
                for name in initial["childNames"]
            )
            and all(
                role == "orbit" for role in initial["childRoles"]
            )
        ),
        "shared_center": metrics["commonCenter"] == [0, 0, 0],
        "self_core_contract": (
            initial["core"]["position"] == [0, 0, 0]
            and 0.14 <= initial["core"]["radius"] <= 0.17
            and initial["core"]["role"] == "self-core"
            and initial["core"]["color"] == "#c9a24f"
        ),
        "monochrome_mode": monochrome["core"]["color"] == "#f5f5f2",
        "never_crosses_center": metrics["minRadius"] > 0.7,
        "stays_inside_sphere": metrics["maxRadius"] <= 1,
        "closed_and_smooth": all(
            orbit["closureDistance"] < 1e-9
            and orbit["seamTangentDot"] > 0.999999
            and orbit["minimumForwardDot"] > 0.999
            for orbit in metrics["orbits"]
        ),
        "no_self_intersections": all(
            not orbit["selfIntersection"] for orbit in metrics["orbits"]
        ),
        "balanced_spherical_extent": metrics["extentRatio"] < 1.15,
        "orientation_metadata": all(
            len(config["normal"]) == 3
            and len(config["quaternion"]) == 4
            and abs(
                sum(value * value for value in config["normal"]) - 1
            ) < 1e-6
            and abs(
                sum(
                    value * value
                    for value in config["quaternion"]
                ) - 1
            ) < 1e-6
            for config in configs
        ),
        "slider_updates_rigid_pose": (
            adjusted["configs"][0]["inclination"] == 61
            and abs(
                adjusted["metrics"]["minRadius"] - metrics["minRadius"]
            ) < 1e-9
            and abs(
                adjusted["metrics"]["maxRadius"] - metrics["maxRadius"]
            ) < 1e-9
        ),
        "reset_restores_angles": (
            reset["configs"][0]["inclination"]
            == original_inclination
        ),
        "export_contains_pose": all(
            field in json.loads(export_value)[0]
            for field in (
                "inclination",
                "azimuth",
                "roll",
                "normal",
                "quaternion",
            )
        ),
        "renders_geometry": initial["renderCalls"] > 0,
        "mobile_canvas_fits": (
            mobile_canvas is not None
            and mobile_canvas["width"] <= 390
            and mobile_canvas["height"] <= 390
        ),
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
    (EVIDENCE / "acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

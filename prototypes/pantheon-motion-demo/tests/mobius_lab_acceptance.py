from __future__ import annotations

import json
import math
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_motion_img2threejs" / "evidence"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?studio=1&prototype=woven-sphere&controls=1&capture=1"
)
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def attach_evidence_hooks(
    page: Page,
    console_errors: list[str],
    page_errors: list[str],
    request_failures: list[str],
) -> None:
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


def read_runtime(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STUDIO__;
          const runtime = studio.orb.userData.sculptRuntime;
          const pivots = Object.values(runtime.bandPivots);
          return {
            bandIds: Object.keys(runtime.bandPivots),
            colors: pivots.map(pivot =>
              `#${pivot.children[0].material.color.getHexString()}`
            ),
            visible: pivots.map(pivot => pivot.visible),
            metrics: runtime.metrics,
            params: runtime.params,
            guidesVisible: runtime.nodes[
              "woven-debug-guides"
            ].visible,
            referenceVisible: runtime.meshes.referenceSphere.visible,
            coreVisible: runtime.meshes.core.visible,
            materialState: pivots.map(pivot => ({
              transparent: pivot.children[0].material.transparent,
              opacity: pivot.children[0].material.opacity,
              castShadow: pivot.children[0].castShadow,
            })),
            cameraPosition: studio.camera.position.toArray(),
            rootRotation: studio.orb.rotation.toArray().slice(0, 3),
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
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME) if CHROME.exists() else None,
        )
        desktop_context = browser.new_context(
            viewport={"width": 1180, "height": 900},
            device_scale_factor=1,
        )
        desktop = desktop_context.new_page()
        attach_evidence_hooks(
            desktop,
            console_errors,
            page_errors,
            request_failures,
        )
        response = desktop.goto(BASE_URL, wait_until="networkidle")
        assert response is not None
        desktop.wait_for_function(
            "() => Boolean(window.__PANTHEON_STUDIO__?.orb)"
        )

        initial = read_runtime(desktop)
        debug_checked = desktop.get_by_role(
            "checkbox", name="Debug 幾何"
        ).is_checked()
        core_checked = desktop.get_by_role(
            "checkbox", name="顯示金色核心"
        ).is_checked()
        debug_front = EVIDENCE / "woven-sphere-debug-front.png"
        desktop.screenshot(path=str(debug_front), full_page=True)

        canvas = desktop.locator("[data-pantheon-orb-studio] canvas")
        canvas_bounds = canvas.bounding_box()
        assert canvas_bounds is not None
        start_x = canvas_bounds["x"] + canvas_bounds["width"] * 0.62
        start_y = canvas_bounds["y"] + canvas_bounds["height"] * 0.5
        desktop.mouse.move(start_x, start_y)
        desktop.mouse.down()
        desktop.mouse.move(start_x - 165, start_y + 42, steps=12)
        desktop.mouse.up()
        desktop.wait_for_timeout(200)
        orbit = read_runtime(desktop)
        debug_orbit = EVIDENCE / "woven-sphere-debug-orbit.png"
        desktop.screenshot(path=str(debug_orbit), full_page=True)

        desktop.get_by_role("checkbox", name="Debug 幾何").uncheck()
        desktop.get_by_role(
            "checkbox", name="顯示金色核心"
        ).check()
        desktop.wait_for_timeout(120)
        final_state = read_runtime(desktop)
        final_orbit = EVIDENCE / "woven-sphere-final-orbit.png"
        desktop.screenshot(path=str(final_orbit), full_page=True)

        desktop.get_by_role("button", name="1", exact=True).click()
        single_state = read_runtime(desktop)
        desktop.get_by_role("button", name="12", exact=True).click()

        camera_views = {}
        for label in ("正面", "側面", "斜角"):
            desktop.get_by_role("button", name=label, exact=True).click()
            camera_views[label] = read_runtime(desktop)["cameraPosition"]

        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
        )
        mobile = mobile_context.new_page()
        attach_evidence_hooks(
            mobile,
            console_errors,
            page_errors,
            request_failures,
        )
        mobile.goto(BASE_URL, wait_until="networkidle")
        mobile.wait_for_function(
            "() => Boolean(window.__PANTHEON_STUDIO__?.orb)"
        )
        mobile_layout = mobile.evaluate(
            """() => ({
              viewportWidth: window.innerWidth,
              scrollWidth: document.documentElement.scrollWidth,
              canvasWidth: document.querySelector(
                "[data-pantheon-orb-studio] canvas"
              )?.getBoundingClientRect().width,
            })"""
        )
        mobile_output = EVIDENCE / "woven-sphere-mobile.png"
        mobile.screenshot(path=str(mobile_output), full_page=True)

        result = {
            "httpStatus": response.status,
            "initial": initial,
            "debugChecked": debug_checked,
            "coreChecked": core_checked,
            "orbit": orbit,
            "finalState": final_state,
            "singleState": single_state,
            "cameraViews": camera_views,
            "mobileLayout": mobile_layout,
            "captures": {
                "debugFront": str(debug_front.relative_to(ROOT)),
                "debugOrbit": str(debug_orbit.relative_to(ROOT)),
                "finalOrbit": str(final_orbit.relative_to(ROOT)),
                "mobile": str(mobile_output.relative_to(ROOT)),
            },
            "consoleErrors": console_errors,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
        }
        (EVIDENCE / "woven-sphere-browser-evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        browser.close()

    assert result["httpStatus"] == 200, result
    assert initial["bandIds"] == [
        f"band-{index:02d}" for index in range(1, 13)
    ], result
    assert len(set(initial["colors"])) == 7, result
    assert initial["params"] == {
        "radius": 1,
        "bandCount": 12,
        "bandWidth": 0.15,
        "bandThickness": 0.018,
        "radialDelta": 0.028,
        "weaveFrequency": 6,
        "coreRadius": 0.21,
        "longitudinalSegments": 256,
    }, result
    assert debug_checked is True, result
    assert core_checked is False, result
    assert initial["guidesVisible"] is True, result
    assert initial["referenceVisible"] is True, result
    assert initial["coreVisible"] is False, result
    assert all(
        material["transparent"] and material["opacity"] == 0.3
        and material["castShadow"] is False
        for material in initial["materialState"]
    ), result

    band_metrics = initial["metrics"]["bandMetrics"]
    assert len(band_metrics) == 12, result
    assert all(
        0.972 - 1e-8 <= metric["minRadius"] < 0.973
        and 1.027 < metric["maxRadius"] <= 1.028 + 1e-8
        and metric["maxRadius"] - metric["minRadius"] > 0.055
        for metric in band_metrics
    ), result
    normals = [metric["normal"] for metric in band_metrics]
    assert all(
        0 < normal[1] < 1
        and abs(sum(component * component for component in normal) - 1)
        < 1e-8
        for normal in normals
    ), result
    assert all(
        abs(sum(a * b for a, b in zip(left, right))) < 0.999
        for index, left in enumerate(normals)
        for right in normals[index + 1:]
    ), result
    shell_bounds = initial["metrics"]["shellBounds"]
    assert all(value < -0.94 for value in shell_bounds["min"]), result
    assert all(value > 0.94 for value in shell_bounds["max"]), result
    assert min(metric["minRadius"] for metric in band_metrics) > 0.95, result
    assert initial["renderCalls"] > 0, result

    assert orbit["rootRotation"] == [0, 0, 0], result
    assert any(
        abs(after - before) > 0.2
        for before, after in zip(
            initial["cameraPosition"], orbit["cameraPosition"]
        )
    ), result
    assert final_state["guidesVisible"] is False, result
    assert final_state["coreVisible"] is True, result
    assert all(
        not material["transparent"] and material["opacity"] == 1
        and material["castShadow"] is True
        for material in final_state["materialState"]
    ), result
    assert single_state["visible"] == [True] + [False] * 11, result
    assert camera_views["正面"] != camera_views["側面"], result
    assert camera_views["側面"] != camera_views["斜角"], result
    assert mobile_layout["scrollWidth"] <= mobile_layout["viewportWidth"], result
    assert mobile_layout["canvasWidth"] > 300, result
    assert not console_errors, result
    assert not page_errors, result
    assert not request_failures, result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

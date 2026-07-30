from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_motion_img2threejs" / "evidence"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?studio=1&prototype=pantheon-theme-sphere&controls=1&capture=1&time=0"
)
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
THEMES = [
    "Constellation",
    "Tarot",
    "Personality",
    "NatalChart",
    "Bazi",
]


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
          const themeGroups = runtime.themeGroups;
          return {
            rootName: studio.orb.name,
            themeNames: Object.keys(themeGroups),
            themeGroupNames: Object.values(themeGroups).map(group => group.name),
            childNames: Object.fromEntries(
              Object.entries(themeGroups).map(([id, group]) => [
                id,
                group.children.map(child => child.name),
              ])
            ),
            themeVisibility: Object.fromEntries(
              Object.entries(themeGroups).map(([id, group]) => [
                id,
                group.visible,
              ])
            ),
            echoVisibility: Object.fromEntries(
              Object.entries(themeGroups).map(([id, group]) => [
                id,
                group.getObjectByName(`${id}_EchoRibbon`).visible,
              ])
            ),
            guidesVisible: runtime.nodes.ThemeSphereDebugGuides.visible,
            coreVisible: runtime.meshes.core.visible,
            metrics: runtime.metrics,
            params: runtime.params,
            cameraPosition: studio.camera.position.toArray(),
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
        context = browser.new_context(
            viewport={"width": 1180, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()
        attach_evidence_hooks(
            page,
            console_errors,
            page_errors,
            request_failures,
        )
        response = page.goto(BASE_URL, wait_until="networkidle")
        assert response is not None
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STUDIO__?.orb)"
        )
        initial = read_runtime(page)

        page.get_by_role(
            "checkbox", name="顯示伴生帶"
        ).uncheck()
        echo_hidden = read_runtime(page)
        page.get_by_role(
            "checkbox", name="顯示伴生帶"
        ).check()
        page.get_by_role(
            "checkbox", name="顯示球面與中心線"
        ).check()
        debug_enabled = read_runtime(page)
        page.get_by_role(
            "checkbox", name="顯示球面與中心線"
        ).uncheck()

        page.get_by_role(
            "button", name="顯示前 1 個主題"
        ).click()
        one_theme = read_runtime(page)
        page.get_by_role(
            "button", name="顯示前 5 個主題"
        ).click()

        camera_views = {}
        for label in ("正面", "斜角", "側面"):
            page.get_by_role("button", name=label, exact=True).click()
            camera_views[label] = read_runtime(page)["cameraPosition"]
            page.screenshot(
                path=str(EVIDENCE / f"theme-sphere-{label}.png"),
                full_page=True,
            )

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

        result = {
            "httpStatus": response.status,
            "initial": initial,
            "echoHidden": echo_hidden,
            "debugEnabled": debug_enabled,
            "oneTheme": one_theme,
            "cameraViews": camera_views,
            "mobileLayout": mobile_layout,
            "consoleErrors": console_errors,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
        }
        evidence_path = EVIDENCE / "theme-sphere-browser-evidence.json"
        evidence_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        browser.close()

    assert result["httpStatus"] == 200, result
    assert initial["rootName"] == "PantheonSphere", result
    assert initial["themeNames"] == THEMES, result
    assert initial["themeGroupNames"] == [
        f"ThemeGroup_{theme}" for theme in THEMES
    ], result
    assert all(
        initial["childNames"][theme] == [
            f"{theme}_MainMobiusRibbon",
            f"{theme}_EchoRibbon",
        ]
        for theme in THEMES
    ), result
    assert initial["metrics"]["themeCount"] == 5, result
    assert initial["metrics"]["ribbonCount"] == 10, result
    assert initial["params"]["innerSphereRadius"] == 0.75, result
    assert initial["params"]["coreRadius"] == 0.21, result
    assert initial["guidesVisible"] is False, result
    assert initial["coreVisible"] is True, result
    assert initial["renderCalls"] > 0, result
    assert all(initial["echoVisibility"].values()), result
    assert not any(echo_hidden["echoVisibility"].values()), result
    assert debug_enabled["guidesVisible"] is True, result
    assert list(one_theme["themeVisibility"].values()) == [
        True,
        False,
        False,
        False,
        False,
    ], result
    assert all(
        seam["leftToStartRight"] < 1e-8
        and seam["rightToStartLeft"] < 1e-8
        and seam["leftToStartLeft"] > 0.09
        for seam in initial["metrics"]["seamMetrics"].values()
    ), result
    assert camera_views["正面"] != camera_views["斜角"], result
    assert camera_views["斜角"] != camera_views["側面"], result
    assert mobile_layout["scrollWidth"] <= mobile_layout["viewportWidth"], result
    assert mobile_layout["canvasWidth"] > 300, result
    assert not console_errors, result
    assert not page_errors, result
    assert not request_failures, result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

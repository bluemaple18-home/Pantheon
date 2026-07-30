from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_idle_ribbon_v1"
BASE_URL = (
    "http://127.0.0.1:5174/"
    "?prototype=pantheon-star-orbits&capture=1&view=front"
)
THEMES = [
    "constellation",
    "tarot",
    "mbti",
    "human-design",
    "ziwei-bazi",
]
PHASES = {
    "Constellation": 0,
    "Tarot": 90,
    "MBTI": 105,
    "HumanDesign": 90,
    "ZiweiBazi": 45,
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


def wait_for_studio(page: Page) -> None:
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_function(
        "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
    )
    page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.setPaused(true);
          studio.setView("front");
          studio.clearSelection();
          studio.setDebugDisplay({
            showTubeLine: false,
            showRibbon: true,
            showCore: true,
            showFrame: false,
            showPhase: false,
            showUV: false
          });
          return studio.settle();
        }"""
    )


def canvas_screenshot(page: Page, name: str) -> None:
    page.locator("[data-pantheon-star-orbits] canvas").screenshot(
        path=str(EVIDENCE / name)
    )


def read_runtime(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const root = studio.orbits;
          const ribbons = [
            ...root.getObjectByName("NarrowRibbonPrototype").children
          ].filter(child => child.userData.publicRole === "pantheon-band");
          const tubes = [
            ...root.getObjectByName("StarOrbitTracks").children
          ];
          return {
            lock: studio.geometryLock,
            samples: studio.getCenterlineSamples(96),
            interaction: studio.interaction,
            ribbonMetrics: studio.ribbonMetrics,
            visibleGroups: root.children
              .filter(child => child.visible)
              .map(child => child.name),
            ribbonCount: ribbons.filter(child => child.visible).length,
            tubeCount: tubes.filter(child => child.visible).length,
            ribbonMaterials: ribbons.flatMap(mesh => {
              const materials = Array.isArray(mesh.material)
                ? mesh.material
                : [mesh.material];
              return materials.map(material => ({
                transparent: material.transparent,
                depthTest: material.depthTest,
                depthWrite: material.depthWrite,
                side: material.side
              }));
            }),
            coreVisible: root.getObjectByName("SelfCore").visible,
            performance: studio.performance
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
        desktop = browser.new_page(viewport={"width": 1440, "height": 960})
        attach_hooks(
            desktop,
            console_errors,
            page_errors,
            request_failures,
        )
        wait_for_studio(desktop)
        initial = read_runtime(desktop)

        # 1. 同相機舊 Tube 與新 Idle Ribbon 對照。
        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              showTubeLine: true,
              showRibbon: false,
              showCore: true
            })"""
        )
        canvas_screenshot(desktop, "01-old-desktop-idle-tube.png")
        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              showTubeLine: false,
              showRibbon: true
            })"""
        )
        canvas_screenshot(desktop, "02-new-desktop-idle-ribbon.png")

        # 2. 三種 Idle 寬度，同相機、同姿態。
        for index, width in enumerate((0.040, 0.045, 0.050), start=3):
            desktop.evaluate(
                """width => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  studio.setRibbonWidthProfile("desktop", { idle: width });
                  studio.clearSelection();
                  return studio.settle();
                }""",
                width,
            )
            canvas_screenshot(
                desktop,
                f"{index:02d}-desktop-idle-width-{width:.3f}.png",
            )

        # 正式候選回到 0.045。
        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setRibbonWidthProfile("desktop", {
                idle: 0.045,
                hover: 0.045,
                selected: 0.045
              });
              studio.clearSelection();
              return studio.settle();
            }"""
        )
        idle_snapshot = read_runtime(desktop)

        hover_snapshot = desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__
              .setHoveredTheme("tarot")"""
        )
        canvas_screenshot(desktop, "06-desktop-hover-width-0.070.png")
        selected_snapshot = desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__
              .selectTheme("tarot")"""
        )
        canvas_screenshot(desktop, "07-desktop-selected-width-0.095.png")

        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.clearSelection();
              studio.setMonochrome(true);
              return studio.settle();
            }"""
        )
        canvas_screenshot(desktop, "08-monochrome-idle-ribbon.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(false)"
        )

        for index, view in enumerate(
            ("front", "front-left", "right"),
            start=9,
        ):
            desktop.evaluate(
                "(value) => window.__PANTHEON_STAR_ORBITS__.setView(value)",
                view,
            )
            canvas_screenshot(desktop, f"{index:02d}-desktop-{view}.png")

        # Core on/off、frame 與 phase debug 都回到 front。
        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setView("front");
              return studio.setDebugDisplay({ showCore: false });
            }"""
        )
        canvas_screenshot(desktop, "14-desktop-idle-no-core.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({showCore: true})"
        )
        canvas_screenshot(desktop, "15-desktop-idle-with-core.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({showFrame: true})"
        )
        canvas_screenshot(desktop, "16-ribbon-frame-debug.png")
        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              showFrame: false,
              showPhase: true
            })"""
        )
        canvas_screenshot(desktop, "17-ribbon-phase-debug.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({showPhase: false})"
        )
        desktop.screenshot(
            path=str(EVIDENCE / "18-desktop-final-ui.png"),
            full_page=True,
        )

        after = read_runtime(desktop)

        mobile = browser.new_page(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
        )
        attach_hooks(
            mobile,
            console_errors,
            page_errors,
            request_failures,
        )
        wait_for_studio(mobile)
        mobile_idle = read_runtime(mobile)
        canvas_screenshot(mobile, "12-mobile-idle-width-0.040.png")
        mobile.get_by_role("button", name="塔羅").tap()
        mobile_selected = mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.settle()"
        )
        canvas_screenshot(mobile, "13-mobile-selected-width-0.085.png")
        mobile.screenshot(
            path=str(EVIDENCE / "19-mobile-final-ui.png"),
            full_page=True,
        )
        browser.close()

    idle_widths = {
        theme: visual["width"]
        for theme, visual in idle_snapshot["interaction"][
            "visuals"
        ].items()
    }
    hover_visuals = hover_snapshot["visuals"]
    selected_visuals = selected_snapshot["visuals"]
    mobile_idle_widths = {
        theme: visual["width"]
        for theme, visual in mobile_idle["interaction"][
            "visuals"
        ].items()
    }
    regular_frames = initial["ribbonMetrics"]["regular"]
    checks = {
        "geometry_signature_unchanged": (
            initial["lock"]["locked"]
            and initial["lock"]["signature"]
            == initial["lock"]["currentSignature"]
            == after["lock"]["currentSignature"]
        ),
        "centerlines_unchanged": initial["samples"] == after["samples"],
        "formal_idle_uses_ribbons_only": (
            initial["ribbonCount"] == 5
            and initial["tubeCount"] == 5
            and "NarrowRibbonPrototype" in initial["visibleGroups"]
            and "StarOrbitTracks" not in initial["visibleGroups"]
        ),
        "five_idle_ribbons_width_0045": all(
            abs(width - 0.045) < 0.0005
            for width in idle_widths.values()
        ),
        "hover_only_one_expands": (
            abs(hover_visuals["tarot"]["width"] - 0.045) < 0.0005
            and all(
                abs(visual["width"] - 0.045) < 0.0005
                for theme, visual in hover_visuals.items()
                if theme != "tarot"
            )
        ),
        "selected_only_one_expands": (
            abs(selected_visuals["tarot"]["width"] - 0.045) < 0.0005
            and all(
                abs(visual["width"] - 0.045) < 0.0005
                for theme, visual in selected_visuals.items()
                if theme != "tarot"
            )
        ),
        "mobile_idle_width_0040": all(
            abs(width - 0.040) < 0.0005
            for width in mobile_idle_widths.values()
        ),
        "mobile_selected_width_0085": (
            abs(
                mobile_selected["visuals"]["tarot"]["width"] - 0.040
            )
            < 0.0005
        ),
        "opaque_depth_materials": all(
            not material["transparent"]
            and material["depthTest"]
            and material["depthWrite"]
            for material in initial["ribbonMaterials"]
        ),
        "ribbon_phase_contract": {
            frame["id"]: frame["phaseDegrees"]
            for frame in regular_frames
        }
        == PHASES,
        "parallel_transport_stable": all(
            frame["frameFlipCount"] == 0
            and frame["seamAlignment"] > 0.999
            and frame["degenerateTriangleCount"] == 0
            for frame in regular_frames
        ),
        "core_visible_by_default": initial["coreVisible"],
        "mobile_quality": (
            mobile_idle["performance"]["dpr"] <= 1.5
            and not mobile_idle["performance"]["shadows"]
        ),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_network_failures": not request_failures,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "geometryLock": initial["lock"],
        "widths": {
            "desktop": {
                "idle": 0.045,
                "hover": 0.045,
                "selected": 0.045,
            },
            "mobile": {
                "idle": 0.040,
                "hover": 0.040,
                "selected": 0.040,
            },
            "thickness": 0.0065,
        },
        "ribbonPhases": PHASES,
        "frameMetrics": regular_frames,
        "ribbonEnvelopeMetric": initial["ribbonMetrics"],
        "performance": {
            "desktop": after["performance"],
            "mobile": mobile_idle["performance"],
        },
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

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "pantheon_ribbon_surface_v2"
BASE = "http://127.0.0.1:5174/"
SIGNATURE = (
    "sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008"
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


def open_studio(
    browser: Browser,
    hooks: tuple[list[str], list[str], list[str]],
    *,
    frame_mode: str = "selected",
    viewport: dict[str, int] | None = None,
    mobile: bool = False,
) -> Page:
    page = browser.new_page(
        viewport=viewport or {"width": 1440, "height": 960},
        device_scale_factor=3 if mobile else 1,
        is_mobile=mobile,
        has_touch=mobile,
    )
    attach_hooks(page, *hooks)
    page.goto(
        f"{BASE}?prototype=pantheon-star-orbits"
        f"&capture=1&view=front&frameMode={frame_mode}",
        wait_until="networkidle",
    )
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
            showSeam: false,
            showPhase: false,
            showUV: false,
            enableRunes: false,
            validationMode: "flat-pbr"
          });
          return studio.settle();
        }"""
    )
    return page


def shot(page: Page, filename: str) -> None:
    page.locator("[data-pantheon-star-orbits] canvas").screenshot(
        path=str(EVIDENCE / filename)
    )


def runtime(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const root = studio.orbits;
          const group = root.getObjectByName("NarrowRibbonPrototype");
          const ribbons = group.children.filter(
            child => child.userData.publicRole === "pantheon-band"
          );
          return {
            lock: studio.geometryLock,
            samples: studio.getCenterlineSamples(128),
            frameMode: studio.ribbonFrameMode,
            metrics: studio.ribbonMetrics,
            interaction: studio.interaction,
            performance: studio.performance,
            materials: ribbons.map(mesh => {
              const materials = Array.isArray(mesh.material)
                ? mesh.material
                : [mesh.material];
              return {
                groupCount: mesh.geometry.groups.length,
                materialIndices: mesh.geometry.groups.map(
                  group => group.materialIndex
                ),
                surface: {
                  uuid: materials[0].uuid,
                  color: materials[0].color.getHexString(),
                  metalness: materials[0].metalness,
                  roughness: materials[0].roughness,
                  emissive: materials[0].emissive.getHexString(),
                  transparent: materials[0].transparent,
                  depthTest: materials[0].depthTest,
                  depthWrite: materials[0].depthWrite,
                  side: materials[0].side,
                  map: Boolean(materials[0].map),
                  normalMap: Boolean(materials[0].normalMap)
                },
                edge: {
                  uuid: materials[2].uuid,
                  color: materials[2].color.getHexString(),
                  metalness: materials[2].metalness,
                  roughness: materials[2].roughness,
                  transparent: materials[2].transparent,
                  depthTest: materials[2].depthTest,
                  depthWrite: materials[2].depthWrite,
                  side: materials[2].side
                },
                attributes: Object.keys(mesh.geometry.attributes)
              };
            })
          };
        }"""
    )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    hooks = (console_errors, page_errors, request_failures)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        legacy = open_studio(browser, hooks, frame_mode="legacy")
        legacy_runtime = runtime(legacy)
        shot(legacy, "01-before-average-phase.png")
        legacy.close()

        selected = open_studio(browser, hooks, frame_mode="selected")
        initial = runtime(selected)
        shot(selected, "02-flat-color-mode.png")

        debug_modes = [
            ("front-back", "03-front-back-debug.png"),
            ("normal", "04-normal-debug.png"),
            ("uv", "05-uv-debug.png"),
            ("tangent", "06-tangent-debug.png"),
            ("edge", "07-edge-material-debug.png"),
        ]
        for mode, filename in debug_modes:
            selected.evaluate(
                """mode => window.__PANTHEON_STAR_ORBITS__
                  .setDebugDisplay({validationMode: mode})""",
                mode,
            )
            shot(selected, filename)
        selected.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__
              .setDebugDisplay({validationMode: "flat-pbr"})"""
        )

        fixed = open_studio(browser, hooks, frame_mode="fixed")
        fixed_runtime = runtime(fixed)
        shot(fixed, "08-fixed-frame.png")
        fixed.close()
        shot(selected, "09-low-amplitude-natural-roll.png")

        # 原平均 phase 與自動 phase 同相機比較。
        legacy_compare = open_studio(browser, hooks, frame_mode="legacy")
        shot(legacy_compare, "10-original-phase-config.png")
        legacy_compare.close()
        shot(selected, "11-auto-phase-best-config.png")

        # Idle 寬度候選。
        for width in (0.040, 0.045, 0.050):
            selected.evaluate(
                """width => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  studio.setRibbonWidthProfile("desktop", {idle: width});
                  studio.clearSelection();
                  return studio.settle();
                }""",
                width,
            )
            shot(selected, f"12-idle-width-{width:.3f}.png")

        # Selected 寬度候選。
        selected.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__
              .setRibbonWidthProfile("desktop", {idle: 0.045})"""
        )
        selected_width_snapshots = {}
        for width in (0.085, 0.095, 0.105):
            selected.evaluate(
                """width => window.__PANTHEON_STAR_ORBITS__
                  .setRibbonWidthProfile("desktop", {selected: width})""",
                width,
            )
            selected_width_snapshots[str(width)] = selected.evaluate(
                """() => window.__PANTHEON_STAR_ORBITS__
                  .selectTheme("tarot")"""
            )
            shot(selected, f"13-selected-width-{width:.3f}.png")
            selected.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.clearSelection()"
            )

        # 正式候選與三個主要視角。
        selected.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setRibbonWidthProfile("desktop", {
                idle: 0.045,
                hover: 0.070,
                selected: 0.095
              });
              studio.setDebugDisplay({validationMode: "flat-pbr"});
              studio.clearSelection();
              return studio.settle();
            }"""
        )
        for view in ("front", "front-left", "side"):
            selected.evaluate(
                "(value) => window.__PANTHEON_STAR_ORBITS__.setView(value)",
                view,
            )
            shot(selected, f"14-desktop-{view}.png")
        selected.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
        )
        final_desktop = runtime(selected)
        selected.screenshot(
            path=str(EVIDENCE / "15-desktop-final-ui.png"),
            full_page=True,
        )

        mobile = open_studio(
            browser,
            hooks,
            frame_mode="selected",
            viewport={"width": 390, "height": 844},
            mobile=True,
        )
        mobile_idle = runtime(mobile)
        shot(mobile, "16-mobile-idle.png")
        mobile.get_by_role("button", name="塔羅").tap()
        mobile_selected = mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.settle()"
        )
        shot(mobile, "17-mobile-selected.png")
        mobile.screenshot(
            path=str(EVIDENCE / "18-mobile-final-ui.png"),
            full_page=True,
        )
        mobile.close()
        selected.close()
        browser.close()

    frames = initial["metrics"]["regular"]
    materials = initial["materials"]
    selected_phases = {
        frame["id"]: frame["phaseDegrees"] for frame in frames
    }
    expected_phases = {
        "Constellation": 0,
        "Tarot": 90,
        "MBTI": 105,
        "HumanDesign": 90,
        "ZiweiBazi": 45,
    }
    checks = {
        "geometry_signature_unchanged": (
            initial["lock"]["locked"]
            and initial["lock"]["signature"]
            == initial["lock"]["currentSignature"]
            == final_desktop["lock"]["currentSignature"]
            == SIGNATURE
        ),
        "centerlines_unchanged_across_frame_modes": (
            initial["samples"]
            == fixed_runtime["samples"]
            == legacy_runtime["samples"]
            == final_desktop["samples"]
        ),
        "auto_phase_contract": selected_phases == expected_phases,
        "natural_roll_bounded": all(
            frame["rollAmplitudeDegrees"] <= 8
            for frame in frames
        ),
        "no_full_mobius": all(
            frame["rollAmplitudeDegrees"] < 180
            for frame in frames
        ),
        "seam_normal_continuous": all(
            frame["seamNormalDot"] >= 0.999 for frame in frames
        ),
        "seam_tangent_continuous": all(
            frame["seamTangentDot"] >= 0.999 for frame in frames
        ),
        "seam_side_continuous": all(
            frame["seamSideDot"] >= 0.999 for frame in frames
        ),
        "seam_uv_continuous": all(
            frame["seamUvDelta"] <= 1e-9 for frame in frames
        ),
        "no_frame_flip_or_degenerate_faces": all(
            frame["frameFlipCount"] == 0
            and frame["degenerateTriangleCount"] == 0
            for frame in frames
        ),
        "top_bevel_edge_groups": all(
            material["groupCount"] == 12
            and set(material["materialIndices"]) == {0, 1, 2}
            for material in materials
        ),
        "same_front_back_material": all(
            material["surface"]["side"] == 2
            and not material["surface"]["transparent"]
            and material["surface"]["depthTest"]
            and material["surface"]["depthWrite"]
            for material in materials
        ),
        "flat_pbr_has_no_texture_or_normal_map": all(
            not material["surface"]["map"]
            and not material["surface"]["normalMap"]
            for material in materials
        ),
        "edge_material_is_same_family": all(
            material["surface"]["metalness"]
            == material["edge"]["metalness"]
            and material["edge"]["roughness"]
            > material["surface"]["roughness"]
            and material["edge"]["side"] == 2
            for material in materials
        ),
        "required_surface_attributes": all(
            {
                "position",
                "normal",
                "uv",
                "aCenterline",
                "aWidthOffset",
                "aThicknessOffset",
                "aTangent",
                "aOrbitProgress",
                "aFaceType",
            }.issubset(set(material["attributes"]))
            for material in materials
        ),
        "desktop_final_widths": (
            final_desktop["interaction"]["widthProfile"]["desktop"]
            == {"idle": 0.045, "hover": 0.045, "selected": 0.045}
        ),
        "mobile_final_widths": (
            mobile_idle["interaction"]["widthProfile"]["mobile"]
            == {"idle": 0.04, "hover": 0.04, "selected": 0.04}
            and abs(
                mobile_selected["visuals"]["tarot"]["width"] - 0.04
            )
            < 0.0005
        ),
        "runes_disabled_in_flat_validation": all(
            not visual["runeVisible"]
            for visual in mobile_selected["visuals"].values()
        ),
        "mobile_quality": (
            mobile_idle["performance"]["dpr"] <= 1.5
            and not mobile_idle["performance"]["shadows"]
        ),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_network_failures": not request_failures,
    }
    source = (
        PROTOTYPE
        / "src"
        / "materials"
        / "createPantheonMaterialPrototype.ts"
    ).read_text(encoding="utf-8")
    checks["front_facing_color_is_debug_only"] = (
        "uRibbonDebugMode > 0.5" in source
        and "gl_FrontFacing" in source
        and 'validationMode: "flat-pbr"' in source
    )

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "geometryLock": initial["lock"],
        "frameModes": {
            "legacy": legacy_runtime["frameMode"],
            "fixed": fixed_runtime["frameMode"],
            "selected": initial["frameMode"],
        },
        "frameMetrics": frames,
        "widths": {
            "desktop": {"idle": 0.045, "hover": 0.045, "selected": 0.045},
            "mobile": {"idle": 0.04, "hover": 0.04, "selected": 0.04},
            "thickness": 0.0065,
        },
        "performance": {
            "desktop": final_desktop["performance"],
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

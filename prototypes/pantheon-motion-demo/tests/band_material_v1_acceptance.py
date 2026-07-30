from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_band_material_v1"
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


def open_studio(page: Page) -> None:
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_function(
        "() => Boolean(window.__PANTHEON_STAR_ORBITS__)",
        timeout=20_000,
    )
    page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.setPaused(true);
          studio.setView("front");
          studio.clearSelection();
          studio.setDebugDisplay({
            showBand: true,
            showRibbon: true,
            showTubeLine: false,
            showCore: true,
            validationMode: "flat-pbr",
            flatMaterial: false,
            showTopBottom: true,
            showBevel: true,
            showEdges: true
          });
          return studio.settle();
        }"""
    )


def canvas_shot(page: Page, name: str) -> None:
    page.locator("[data-pantheon-star-orbits] canvas").screenshot(
        path=str(EVIDENCE / name)
    )


def read_contract(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const nodes = studio.orbits.userData.starOrbitRuntime
            .getThemeNodes();
          const bands = [...nodes.ribbonMeshes.values()];
          return {
            lock: studio.geometryLock,
            samples: studio.getCenterlineSamples(96),
            metrics: studio.bandMetrics,
            interaction: studio.interaction,
            profiles: bands.map(mesh => ({
              name: mesh.name,
              publicRole: mesh.userData.publicRole,
              materials: mesh.material.map(material => ({
                type: material.type,
                metalness: material.metalness,
                roughness: material.roughness,
                clearcoat: material.clearcoat,
                clearcoatRoughness: material.clearcoatRoughness,
                anisotropy: material.anisotropy,
                envMapIntensity: material.envMapIntensity,
                transparent: material.transparent,
                depthWrite: material.depthWrite
              })),
              groups: mesh.geometry.groups.map(group => group.materialIndex),
              faceTypes: [...new Set(
                Array.from(mesh.geometry.getAttribute("aFaceType").array)
              )].sort(),
              attributes: Object.keys(mesh.geometry.attributes)
            })),
            core: {
              position: nodes.core.position.toArray(),
              radius: nodes.core.userData.radius,
              material: {
                type: nodes.core.material.type,
                metalness: nodes.core.material.metalness,
                roughness: nodes.core.material.roughness,
                clearcoat: nodes.core.material.clearcoat,
                clearcoatRoughness:
                  nodes.core.material.clearcoatRoughness
              }
            },
            performance: studio.performance
          };
        }"""
    )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    state_snapshots: dict[str, dict] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_page(
            viewport={"width": 1440, "height": 960}
        )
        attach_hooks(
            desktop,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(desktop)
        initial = read_contract(desktop)

        # 原 Flat Ribbon 使用上一輪鎖定證據，不覆寫。
        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              flatMaterial: true,
              validationMode: "flat-pbr"
            })"""
        )
        canvas_shot(desktop, "02-new-flat-metal-band.png")

        for mode, filename in [
            ("bevel", "03-bevel-debug.png"),
            ("edge", "04-edge-debug.png"),
        ]:
            desktop.evaluate(
                """mode => window.__PANTHEON_STAR_ORBITS__
                  .setDebugDisplay({validationMode: mode})""",
                mode,
            )
            canvas_shot(desktop, filename)

        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setDebugDisplay({
                flatMaterial: false,
                validationMode: "flat-pbr"
              });
              return studio.setMonochrome(true);
            }"""
        )
        canvas_shot(desktop, "05-monochrome-metal.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(false)"
        )
        canvas_shot(desktop, "06-five-theme-flat-metal.png")

        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              validationMode: "marks",
              markOpacity: 1
            })"""
        )
        canvas_shot(desktop, "07-surface-mark-placeholders.png")

        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              validationMode: "flat-pbr",
              markOpacity: 1
            })"""
        )
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.clearSelection()"
        )
        state_snapshots["idle"] = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.interaction"
        )
        canvas_shot(desktop, "08-final-idle.png")

        for index, theme in enumerate(THEMES, start=1):
            state_snapshots[f"hover-{theme}"] = desktop.evaluate(
                """theme => window.__PANTHEON_STAR_ORBITS__
                  .setHoveredTheme(theme)""",
                theme,
            )
            canvas_shot(
                desktop,
                f"09-hover-{index}-{theme}.png",
            )

        for index, theme in enumerate(THEMES, start=1):
            state_snapshots[f"selected-{theme}"] = desktop.evaluate(
                """theme => window.__PANTHEON_STAR_ORBITS__
                  .selectTheme(theme)""",
                theme,
            )
            canvas_shot(
                desktop,
                f"10-selected-{index}-{theme}.png",
            )

        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.selectTheme("tarot");
              studio.setDebugDisplay({
                validationMode: "flow",
                flowIntensity: 0.36
              });
              return studio.settle();
            }"""
        )
        canvas_shot(desktop, "11-surface-flow-debug.png")

        desktop.evaluate(
            """() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({
              validationMode: "flat-pbr",
              flowIntensity: 0.16
            })"""
        )
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.clearSelection()"
        )
        for view in ("front", "front-left", "side"):
            desktop.evaluate(
                "(view) => window.__PANTHEON_STAR_ORBITS__.setView(view)",
                view,
            )
            canvas_shot(desktop, f"12-desktop-{view}.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
        )
        canvas_shot(desktop, "13-self-core-final.png")
        desktop.screenshot(
            path=str(EVIDENCE / "14-band-material-lab.png"),
            full_page=True,
        )
        final_desktop = read_contract(desktop)
        desktop.close()

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
        open_studio(mobile)
        mobile_idle = read_contract(mobile)
        canvas_shot(mobile, "15-mobile-idle.png")
        mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.selectTheme('tarot')"
        )
        mobile_selected = read_contract(mobile)
        canvas_shot(mobile, "16-mobile-selected.png")
        mobile.screenshot(
            path=str(EVIDENCE / "17-mobile-material-lab.png"),
            full_page=True,
        )
        mobile.close()
        browser.close()

    def widths(snapshot: dict) -> list[float]:
        return [
            visual["bandWidth"]
            for visual in snapshot["visuals"].values()
        ]

    desktop_states_locked = all(
        all(abs(width - 0.045) < 0.00001 for width in widths(snapshot))
        for snapshot in state_snapshots.values()
    )
    mobile_states_locked = all(
        abs(width - 0.04) < 0.00001
        for width in widths(mobile_idle["interaction"])
        + widths(mobile_selected["interaction"])
    )
    frames = initial["metrics"]["regular"]
    checks = {
        "geometry_signature_unchanged": (
            initial["lock"]["locked"]
            and initial["lock"]["signature"] == SIGNATURE
            and initial["lock"]["currentSignature"] == SIGNATURE
            and final_desktop["lock"]["currentSignature"] == SIGNATURE
        ),
        "centerlines_byte_stable": (
            initial["samples"] == final_desktop["samples"]
        ),
        "desktop_width_locked_all_states": desktop_states_locked,
        "mobile_width_locked_all_states": mobile_states_locked,
        "band_dimensions_locked": (
            initial["interaction"]["bandDimensions"]
            == {
                "locked": True,
                "desktopWidth": 0.045,
                "mobileWidth": 0.04,
                "thickness": 0.0065,
                "bevelWidth": 0.0024,
                "bevelSegments": 2,
                "invariantAcrossStates": True,
            }
        ),
        "real_bevel_profile": (
            initial["metrics"]["profileFaceCount"] == 12
            and all(
                profile["faceTypes"] == [0, 1, 2]
                and set(profile["groups"]) == {0, 1, 2}
                and len(profile["materials"]) == 3
                for profile in initial["profiles"]
            )
        ),
        "physical_metal_materials": all(
            all(
                material["type"] == "MeshPhysicalMaterial"
                and 0.68 <= material["metalness"] <= 0.9
                and material["roughness"] >= 0.18
                and not material["transparent"]
                and material["depthWrite"]
                for material in profile["materials"]
            )
            for profile in initial["profiles"]
        ),
        "surface_bevel_edge_material_split": all(
            profile["materials"][1]["roughness"]
            < profile["materials"][0]["roughness"]
            < profile["materials"][2]["roughness"]
            for profile in initial["profiles"]
        ),
        "marks_and_flow_material_only": all(
            snapshot["visuals"][theme]["bandWidth"] == 0.045
            and snapshot["visuals"][theme]["markOpacity"] >= 0.55
            and snapshot["visuals"][theme]["flowIntensity"] > 0
            for theme, snapshot in (
                (theme, state_snapshots[f"selected-{theme}"])
                for theme in THEMES
            )
        ),
        "seam_and_normals_continuous": all(
            frame["seamNormalDot"] >= 0.999
            and frame["seamTangentDot"] >= 0.999
            and frame["seamSideDot"] >= 0.999
            and frame["seamUvDelta"] == 0
            and frame["frameFlipCount"] == 0
            and frame["degenerateTriangleCount"] == 0
            for frame in frames
        ),
        "self_core_locked_and_metal": (
            initial["core"]["position"] == [0, 0, 0]
            and initial["core"]["radius"] == 0.14
            and initial["core"]["material"]["metalness"] == 0.92
            and 0.16 <= initial["core"]["material"]["roughness"] <= 0.24
        ),
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
        "bandMetrics": initial["metrics"],
        "bandDimensions": initial["interaction"]["bandDimensions"],
        "themeMaterials": {
            theme: initial["interaction"]["visuals"][theme]
            for theme in THEMES
        },
        "core": initial["core"],
        "performance": {
            "desktop": final_desktop["performance"],
            "mobile": mobile_idle["performance"],
        },
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "evidence": sorted(
            str(path.relative_to(ROOT))
            for path in EVIDENCE.glob("*.png")
        ),
    }
    (EVIDENCE / "acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

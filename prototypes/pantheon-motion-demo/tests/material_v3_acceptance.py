from __future__ import annotations

import hashlib
import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "pantheon_material_v3"
EVIDENCE = OUTPUT / "evidence"
BASE_URL = (
    "http://127.0.0.1:5174/"
    "?prototype=pantheon-star-orbits&capture=1&geometryVersion=v1.1"
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


def open_studio(page: Page, view: str = "front") -> None:
    page.goto(f"{BASE_URL}&view={view}", wait_until="networkidle")
    page.wait_for_function("() => Boolean(window.__PANTHEON_STAR_ORBITS__)")
    page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.setPaused(true);
          studio.clearSelection();
          studio.setMonochrome(false);
          studio.setDebugDisplay({
            validationMode: "material-v3",
            flatMaterial: false,
            showBand: true,
            showCore: true
          });
          return studio.settle();
        }"""
    )


def canvas_shot(page: Page, name: str) -> None:
    page.locator("[data-pantheon-star-orbits] canvas").screenshot(
        path=str(EVIDENCE / name),
        timeout=15_000,
    )


def canonical_version_signature(data: dict) -> str:
    payload = [
        {
            key: orbit[key]
            for key in (
                "id",
                "semiMajorAxis",
                "semiMinorAxis",
                "phase",
                "scale",
                "inclination",
                "azimuth",
                "roll",
            )
        }
        for orbit in data["orbits"]
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def stable_material_fields(snapshot: dict) -> dict:
    fields = (
        "bandWidth",
        "bandThickness",
        "displayColor",
        "stateBrightness",
        "stateSaturation",
        "emissiveIntensity",
        "metalness",
        "roughness",
        "clearcoat",
        "clearcoatRoughness",
        "anisotropy",
        "envMapIntensity",
    )
    return {
        theme: {field: visual[field] for field in fields}
        for theme, visual in snapshot["visuals"].items()
    }


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    geometry = json.loads(
        (PROTOTYPE / "geometry" / "pantheon-orbits-v1.1.json").read_text()
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_page(viewport={"width": 1440, "height": 960})
        attach_hooks(
            desktop,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(desktop)
        studio = "window.__PANTHEON_STAR_ORBITS__"
        lock = desktop.evaluate(f"() => {studio}.geometryLock")
        band_metrics = desktop.evaluate(f"() => {studio}.bandMetrics")
        centerlines_idle = desktop.evaluate(
            f"() => {studio}.getCenterlineSamples(360)"
        )
        idle = desktop.evaluate(f"() => {studio}.interaction")
        effects = desktop.evaluate(f"() => {studio}.effects")
        canvas_shot(desktop, "01-luxury-idle-front.png")

        hovered = desktop.evaluate(
            f"() => {studio}.previewHoverEffect('tarot', 0.3)"
        )
        centerlines_hovered = desktop.evaluate(
            f"() => {studio}.getCenterlineSamples(360)"
        )
        canvas_shot(desktop, "02-luxury-hovered-tarot.png")
        hover_completed = desktop.evaluate(
            f"() => {studio}.previewHoverEffect('tarot', 0.3)"
        )

        desktop.evaluate(f"() => {studio}.setHoveredTheme(null)")
        desktop.evaluate(f"() => {studio}.setPaused(false)")
        desktop.wait_for_timeout(120)
        motion_active = desktop.evaluate(f"() => {studio}.interaction")
        desktop.evaluate(f"() => {studio}.setPaused(true)")

        desktop.evaluate(
            f"() => {studio}.selectTheme('tarot')"
        )
        selected = desktop.evaluate(f"() => {studio}.interaction")
        centerlines_selected = desktop.evaluate(
            f"() => {studio}.getCenterlineSamples(360)"
        )
        canvas_shot(desktop, "03-luxury-selected-tarot.png")

        for view, name in (
            ("front-left", "04-luxury-front-left.png"),
            ("right", "05-luxury-side.png"),
            ("back", "06-luxury-back.png"),
        ):
            desktop.evaluate(f"() => {studio}.setView('{view}')")
            canvas_shot(desktop, name)

        desktop.evaluate(f"() => {studio}.setView('front')")
        desktop.evaluate(
            f"() => {studio}.setDebugDisplay("
            "{validationMode: 'engraving-reveal'})"
        )
        canvas_shot(desktop, "07-engraving-reveal-debug.png")
        desktop.evaluate(
            f"() => {studio}.setDebugDisplay("
            "{validationMode: 'brushed-metal'})"
        )
        canvas_shot(desktop, "08-brushed-metal-debug.png")
        desktop.evaluate(f"() => {studio}.setMonochrome(true)")
        desktop.evaluate(
            f"() => {studio}.setDebugDisplay("
            "{validationMode: 'material-v3'})"
        )
        canvas_shot(desktop, "09-monochrome-luxury-metal.png")
        desktop.evaluate(f"() => {studio}.setMonochrome(false)")
        width_slider = (
            desktop.locator("label")
            .filter(has_text="Band Width Preview")
            .locator('input[type="range"]')
        )
        width_slider.fill("0.06")
        desktop.wait_for_timeout(240)
        width_narrow = desktop.evaluate(f"() => {studio}.interaction")
        canvas_shot(desktop, "10a-band-width-narrow.png")
        width_slider.fill("0.36")
        desktop.wait_for_timeout(240)
        width_wide = desktop.evaluate(f"() => {studio}.interaction")
        canvas_shot(desktop, "10b-band-width-wide.png")
        desktop.screenshot(
            path=str(EVIDENCE / "10-band-width-preview.png"),
            full_page=True,
        )
        desktop.get_by_role(
            "button",
            name="Reset Band Width",
        ).click()
        desktop.wait_for_timeout(240)
        width_reset = desktop.evaluate(f"() => {studio}.interaction")
        desktop.screenshot(
            path=str(EVIDENCE / "11-material-lab-ui.png"),
            full_page=True,
        )
        performance = desktop.evaluate(f"() => {studio}.performance")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        attach_hooks(
            mobile,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(mobile)
        mobile_idle = mobile.evaluate(f"() => {studio}.interaction")
        canvas_shot(mobile, "11-mobile-idle.png")
        mobile.evaluate(f"() => {studio}.selectTheme('tarot')")
        mobile_selected = mobile.evaluate(f"() => {studio}.interaction")
        canvas_shot(mobile, "12-mobile-selected.png")
        browser.close()

    invariant_idle = stable_material_fields(idle)
    invariant_hovered = stable_material_fields(hovered)
    invariant_selected = stable_material_fields(selected)
    selected_marks = selected["visuals"]["tarot"]["markOpacity"]
    hovered_marks = hovered["visuals"]["tarot"]["markOpacity"]
    idle_marks = idle["visuals"]["tarot"]["markOpacity"]

    checks = {
        "geometry_v1_1_signature_valid": (
            canonical_version_signature(geometry)
            == geometry["geometryVersionSignature"]
            == "sha256:c07bc5c75b967ca25ce74cabb0b03acaa6c7d858dc517c8f4f58079fe0c70904"
        ),
        "geometry_v1_1_locked": (
            lock["version"] == "Geometry v1.1 — LOCKED"
            and lock["locked"]
        ),
        "centerlines_unchanged_by_material_states": (
            centerlines_idle
            == centerlines_hovered
            == centerlines_selected
        ),
        "band_dimensions_locked": (
            idle["bandDimensions"]["desktopWidth"] == 0.18
            and idle["bandDimensions"]["mobileWidth"] == 0.16
            and idle["bandDimensions"]["thickness"] == 0.02
            and idle["bandDimensions"]["bevelWidth"] == 0.0024
            and band_metrics["bevelSegments"] == 2
        ),
        "band_dimensions_invariant": all(
            visual["bandWidth"] == 0.18
            and visual["bandThickness"] == 0.02
            for snapshot in (idle, hovered, selected)
            for visual in snapshot["visuals"].values()
        )
        and all(
            visual["bandWidth"] == 0.16
            and visual["bandThickness"] == 0.02
            for snapshot in (mobile_idle, mobile_selected)
            for visual in snapshot["visuals"].values()
        ),
        "band_width_preview_adjustable_and_resettable": (
            all(
                visual["bandWidth"] == 0.06
                for visual in width_narrow["visuals"].values()
            )
            and all(
                visual["bandWidth"] == 0.36
                for visual in width_wide["visuals"].values()
            )
            and all(
                visual["bandWidth"] == 0.18
                for visual in width_reset["visuals"].values()
            )
            and (
                hashlib.sha256(
                    (EVIDENCE / "10a-band-width-narrow.png").read_bytes()
                ).hexdigest()
                != hashlib.sha256(
                    (EVIDENCE / "10b-band-width-wide.png").read_bytes()
                ).hexdigest()
            )
        ),
        "material_v3_active": (
            idle["materialVersion"]
            == "Pantheon Material v3 — Luxury before Technology"
        ),
        "band_rune_vocabulary_is_unified": (
            idle["surfaceMarks"]["system"]
            == "production-band-rune-engraving"
            and not idle["surfaceMarks"]["themeSpecificGlyphs"]
            and idle["surfaceMarks"]["cellCount"] == 36
            and idle["surfaceMarks"]["minimumGlyphClusters"] >= 30
        ),
        "band_runes_have_shallow_metal_relief": (
            idle["surfaceMarks"]["strokeScale"] == 2.05
            and idle["surfaceMarks"]["reliefNormalStrength"] >= 0.89
            and idle["surfaceMarks"]["bevelHighlight"]
            and idle["surfaceMarks"]["contactShadow"]
            and not idle["surfaceMarks"]["addedGeometry"]
        ),
        "periodic_roughness_grid_removed": (
            idle["surfaceMarks"]["brushedRoughnessPattern"]
            == "anisotropy-only"
            and not idle["surfaceMarks"]["periodicRoughness"]
        ),
        "band_metal_highlights_are_subdued": (
            idle["surfaceMarks"]["metalHighlightCeiling"] == 0.48
            and all(
                visual["metalness"] <= 0.92
                and visual["roughness"] >= 0.54
                and visual["envMapIntensity"] <= 0.68
                for visual in idle["visuals"].values()
            )
        ),
        "emissive_subtracted": (
            idle["surfaceMarks"]["maximumEmissive"] == 0
            and all(
                visual["emissiveIntensity"] == 0
                for snapshot in (idle, hovered, selected)
                for visual in snapshot["visuals"].values()
            )
        ),
        "effects_v1_surface_only": (
            idle["effectsVersion"] == "Pantheon Effects v1"
            and effects["geometryAttachedOnly"]
            and not any(effects["forbiddenEffects"].values())
        ),
        "band_runes_are_fixed_to_surface": (
            idle["surfaceMarks"]["fixedToBandUv"]
            and not idle["surfaceMarks"]["independentMotion"]
            and not idle["surfaceMarks"]["wholeTextureTranslation"]
            and idle["surfaceMarks"]["metalReflectionOnly"]
            and all(
                visual["energyPulseCount"] == 0
                and visual["energyCycleSeconds"] == 0
                and visual["flowIntensity"] == 0
                and visual["hoverSweepIntensity"] == 0
                for visual in motion_active["visuals"].values()
            )
            and motion_active["geometryBuilds"] == 1
        ),
        "runes_visible_in_idle_without_sweep": (
            idle_marks == effects["hover"]["idleMarkOpacity"] == 0.72
            and hovered_marks
            == effects["hover"]["hoveredMarkOpacity"]
            == 0.82
            and selected_marks == 0.9
            and hovered["visuals"]["tarot"]["hoverSweepProgress"] == 1
            and hovered["visuals"]["tarot"]["hoverSweepIntensity"] == 0
            and hover_completed["visuals"]["tarot"]["hoverSweepProgress"] == 1
            and hover_completed["visuals"]["tarot"]["hoverSweepIntensity"] == 0
            and effects["hover"]["sweepDurationSeconds"] == 0
            and not effects["hover"]["singlePass"]
        ),
        "self_core_liquid_reflection_only": (
            0.3 <= effects["selfCore"]["reflectionFrequencyHz"] <= 0.6
            and not effects["selfCore"]["scaleAnimation"]
            and not effects["selfCore"]["emissive"]
            and not effects["selfCore"]["bloom"]
        ),
        "whole_band_visuals_invariant": (
            invariant_idle == invariant_hovered == invariant_selected
            and not any(idle["wholeBandInteraction"].values())
        ),
        "material_weight_only_rune_response": (
            idle_marks < hovered_marks < selected_marks
            and not idle["surfaceMarks"]["localEngravingRevealOnly"]
            and all(
                visual["flowIntensity"] == 0
                for snapshot in (idle, hovered, selected)
                for visual in snapshot["visuals"].values()
            )
        ),
        "frame_and_seam_stable": all(
            metric["frameFlipCount"] == 0
            and metric["seamAlignment"] > 0.999
            and metric["seamNormalDot"] > 0.999
            and metric["degenerateTriangleCount"] == 0
            for metric in band_metrics["regular"]
        ),
        "mobile_quality_active": mobile_idle["mobileQualityPreview"],
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    status = "PASS" if all(checks.values()) else "PARTIAL"
    result = {
        "status": status,
        "checks": checks,
        "geometrySignature": geometry["geometryVersionSignature"],
        "bandDimensions": idle["bandDimensions"],
        "materialVersion": idle["materialVersion"],
        "effectsVersion": idle["effectsVersion"],
        "effects": effects,
        "surfaceMarks": idle["surfaceMarks"],
        "wholeBandInteraction": idle["wholeBandInteraction"],
        "themeMaterials": {
            theme: {
                key: visual[key]
                for key in (
                    "baseColor",
                    "metalness",
                    "roughness",
                    "clearcoat",
                    "clearcoatRoughness",
                    "anisotropy",
                    "envMapIntensity",
                )
            }
            for theme, visual in idle["visuals"].items()
        },
        "markOpacity": {
            "idle": idle_marks,
            "hovered": hovered_marks,
            "selected": selected_marks,
        },
        "performance": performance,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "evidence": [
            str(path.relative_to(ROOT))
            for path in sorted(EVIDENCE.glob("*.png"))
        ],
    }
    (OUTPUT / "acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()

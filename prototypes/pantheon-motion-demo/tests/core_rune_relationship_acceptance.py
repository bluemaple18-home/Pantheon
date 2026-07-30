from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "pantheon_core_rune_relationship"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits&capture=1"
    "&geometryVersion=v1.1&freezeOrbit=1"
)
THEMES = [
    "constellation",
    "tarot",
    "mbti",
    "human-design",
    "ziwei-bazi",
]


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
        geometry_before = page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.geometryLock"
        )
        forced: dict[str, dict] = {}
        for theme in THEMES:
            page.evaluate(
                "(theme) => window.__PANTHEON_STAR_ORBITS__"
                ".forceCoreTheme(theme)",
                theme,
            )
            page.wait_for_timeout(750)
            forced[theme] = page.evaluate(
                """() => ({
                  relationship:
                    window.__PANTHEON_STAR_ORBITS__.coreRuneRelationship,
                  core:
                    window.__PANTHEON_STAR_ORBITS__.selfCoreEffect
                })"""
            )
            page.locator(
                "[data-pantheon-star-orbits] canvas"
            ).screenshot(path=str(OUTPUT / f"desktop-core-{theme}.png"))

        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.forceCoreTheme(null)"
        )
        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__"
            ".setDebugDisplay({speed: 5})"
        )
        page.wait_for_timeout(900)
        automatic = page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.coreRuneRelationship"
        )
        automatic_themes: set[str] = set()
        automatic_sequence: list[dict] = []
        for _ in range(80):
            value = page.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__"
                ".coreRuneRelationship"
            )
            theme = value["activeTheme"]
            if theme:
                automatic_themes.add(theme)
            automatic_sequence.append(
                {
                    "theme": theme,
                    "influence": (
                        value["influences"][theme]["influence"]
                        if theme
                        else 0
                    ),
                }
            )
            page.wait_for_timeout(100)
        page.locator("[data-pantheon-star-orbits] canvas").screenshot(
            path=str(OUTPUT / "desktop-auto.png")
        )

        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__"
            ".setReducedMotionPreview(true)"
        )
        page.wait_for_timeout(120)
        reduced = page.evaluate(
            """() => ({
              relationship:
                window.__PANTHEON_STAR_ORBITS__.coreRuneRelationship,
              core:
                window.__PANTHEON_STAR_ORBITS__.selfCoreEffect
            })"""
        )
        geometry_after = page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.geometryLock"
        )

        mobile_page = browser.new_page(
            viewport={"width": 390, "height": 844}
        )
        attach_hooks(
            mobile_page,
            console_errors,
            page_errors,
            request_failures,
        )
        mobile_page.goto(BASE_URL, wait_until="networkidle")
        mobile_page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        mobile_page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__"
            ".forceCoreTheme('mbti')"
        )
        mobile_page.wait_for_timeout(750)
        mobile = mobile_page.evaluate(
            """() => ({
              relationship:
                window.__PANTHEON_STAR_ORBITS__.coreRuneRelationship,
              core:
                window.__PANTHEON_STAR_ORBITS__.selfCoreEffect
            })"""
        )
        mobile_page.locator(
            "[data-pantheon-star-orbits] canvas"
        ).screenshot(path=str(OUTPUT / "mobile-mbti.png"))
        browser.close()

    forced_colors = {
        theme: value["core"]["relationship"]["displayColor"]
        for theme, value in forced.items()
    }
    forced_targets = {
        theme: value["core"]["relationship"]["targetColor"]
        for theme, value in forced.items()
    }
    influence_entries = automatic["influences"]
    checks = {
        "geometry_unchanged": geometry_before == geometry_after,
        "uses_screen_space_projection": (
            automatic["mode"] == "screen-space-relative-proximity"
        ),
        "shares_surface_energy_progress": (
            automatic["sharesSurfaceEnergyProgress"]
        ),
        "all_energy_positions_present": all(
            1 <= len(influence_entries[theme]["energyPositions"]) <= 2
            for theme in THEMES
        ),
        "five_force_themes_work": all(
            forced[theme]["relationship"]["activeTheme"] == theme
            and forced[theme]["core"]["relationship"]["targetInfluence"]
            >= 0.9
            for theme in THEMES
        ),
        "five_theme_targets_are_distinct": len(set(forced_targets.values()))
        == 5,
        "core_visibly_changes_color": len(set(forced_colors.values())) == 5,
        "single_theme_arbitration": (
            automatic["activeTheme"] is None
            or automatic["activeTheme"] in THEMES
        ),
        "automatic_uses_all_theme_colors": len(automatic_themes) == 5,
        "hysteresis_enabled": automatic["hysteresis"] > 0,
        "reduced_motion_returns_to_gold": (
            reduced["relationship"]["activeTheme"] is None
            and reduced["core"]["relationship"]["targetInfluence"] == 0
            and reduced["core"]["relationship"]["currentInfluence"] == 0
        ),
        "core_remains_metal": (
            0.68 <= reduced["core"]["metalness"] <= 0.92
            and 0.2 <= reduced["core"]["roughness"] <= 0.38
        ),
        "mobile_core_relationship_works": (
            mobile["relationship"]["activeTheme"] == "mbti"
            and mobile["core"]["relationship"]["targetInfluence"] >= 0.9
        ),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "checks": checks,
        "forcedColors": forced_colors,
        "forcedTargets": forced_targets,
        "automatic": automatic,
        "automaticThemes": sorted(automatic_themes),
        "automaticSequence": automatic_sequence,
        "reducedMotion": reduced,
        "mobile": mobile,
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

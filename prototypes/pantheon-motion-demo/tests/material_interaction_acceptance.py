from __future__ import annotations

import hashlib
import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "pantheon_material_interaction_v1"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits&capture=1&view=orbit"
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


def wait_for_studio(page: Page) -> None:
    page.goto(BASE_URL, wait_until="networkidle")
    page.wait_for_function(
        "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
    )
    page.evaluate("() => window.__PANTHEON_STAR_ORBITS__.settle()")


def canonical_signature(lock_data: dict) -> str:
    payload = [
        {
            "id": orbit["id"],
            "semiMajorAxis": orbit["semiMajorAxis"],
            "semiMinorAxis": orbit["semiMinorAxis"],
            "phase": orbit["phase"],
        }
        for orbit in lock_data["orbits"]
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    lock_data = json.loads(
        (PROTOTYPE / "geometry" / "pantheon-orbits-v1.json").read_text()
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
        wait_for_studio(desktop)
        response_ok = True
        before = desktop.evaluate(
            """() => ({
              samples: window.__PANTHEON_STAR_ORBITS__
                .getCenterlineSamples(96),
              lock: window.__PANTHEON_STAR_ORBITS__.geometryLock,
              configs: window.__PANTHEON_STAR_ORBITS__.configs,
              metrics: window.__PANTHEON_STAR_ORBITS__.metrics,
              ribbon: window.__PANTHEON_STAR_ORBITS__.ribbonMetrics,
              perf: window.__PANTHEON_STAR_ORBITS__.performance
            })"""
        )
        mutation_rejected = desktop.evaluate(
            """() => {
              try {
                window.__PANTHEON_STAR_ORBITS__.attemptGeometryMutation(
                  "Constellation",
                  { roll: -30 }
                );
                return false;
              } catch (error) {
                return String(error).includes("LOCKED");
              }
            }"""
        )
        unlock_rejected = desktop.evaluate(
            """() => {
              try {
                window.__PANTHEON_STAR_ORBITS__.unlockGeometry("unlock");
                return false;
              } catch (error) {
                return String(error).includes("Unlock rejected");
              }
            }"""
        )
        desktop.screenshot(
            path=str(EVIDENCE / "desktop-idle.png"),
            full_page=True,
        )
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.clearSelection()"
        )
        canvas_box = desktop.locator(
            "[data-pantheon-star-orbits] canvas"
        ).bounding_box()
        raycast_hover = None
        if canvas_box:
            for x_ratio in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
                for y_ratio in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
                    desktop.mouse.move(
                        canvas_box["x"] + canvas_box["width"] * x_ratio,
                        canvas_box["y"] + canvas_box["height"] * y_ratio,
                    )
                    raycast_hover = desktop.evaluate(
                        """() => window.__PANTHEON_STAR_ORBITS__
                          .interaction.state.hoveredTheme"""
                    )
                    if raycast_hover:
                        break
                if raycast_hover:
                    break

        hover_snapshots = {}
        selected_snapshots = {}
        for theme in THEMES:
            hover_snapshots[theme] = desktop.evaluate(
                """theme => {
                  window.__PANTHEON_STAR_ORBITS__.clearSelection();
                  return window.__PANTHEON_STAR_ORBITS__
                    .setHoveredTheme(theme);
                }""",
                theme,
            )
            desktop.screenshot(
                path=str(EVIDENCE / f"hover-{theme}.png"),
                full_page=True,
            )
            selected_snapshots[theme] = desktop.evaluate(
                """theme => window.__PANTHEON_STAR_ORBITS__
                  .selectTheme(theme)""",
                theme,
            )
            desktop.screenshot(
                path=str(EVIDENCE / f"selected-{theme}.png"),
                full_page=True,
            )

        desktop.evaluate(
            """() => {
              window.__PANTHEON_STAR_ORBITS__.clearSelection();
              window.__PANTHEON_STAR_ORBITS__
                .setReducedMotionPreview(true);
              window.__PANTHEON_STAR_ORBITS__
                .setHoveredTheme("human-design");
            }"""
        )
        desktop.screenshot(
            path=str(EVIDENCE / "reduced-motion.png"),
            full_page=True,
        )
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setReducedMotionPreview(false)"
        )

        # 使用正式 UI 路徑驗證鍵盤可操作的選取。
        desktop.get_by_role("button", name="塔羅").focus()
        desktop.keyboard.press("Enter")
        ui_selected = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.interaction"
        )

        after = desktop.evaluate(
            """() => ({
              samples: window.__PANTHEON_STAR_ORBITS__
                .getCenterlineSamples(96),
              lock: window.__PANTHEON_STAR_ORBITS__.geometryLock,
              perf: window.__PANTHEON_STAR_ORBITS__.performance
            })"""
        )

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
        mobile.get_by_role("button", name="人類圖").tap()
        mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.settle()"
        )
        mobile_snapshot = mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.interaction"
        )
        mobile_perf = mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.performance"
        )
        mobile.screenshot(
            path=str(EVIDENCE / "mobile-selected-human-design.png"),
            full_page=True,
        )
        browser.close()

    def one_selected(
        snapshot: dict,
        theme: str,
        expected_width: float = 0.045,
    ) -> bool:
        visuals = snapshot["visuals"]
        return (
            visuals[theme]["state"] == "Selected"
            and abs(visuals[theme]["width"] - expected_width) < 0.001
            and visuals[theme]["ribbonVisible"]
            and sum(
                1 for value in visuals.values() if value["ribbonVisible"]
            )
            == 5
            and not any(
                value["runeVisible"] for value in visuals.values()
            )
        )

    def hover_ok(snapshot: dict, theme: str) -> bool:
        visual = snapshot["visuals"][theme]
        return (
            visual["state"] == "Hovered"
            and 0.044 <= visual["width"] <= 0.046
            and not visual["runeVisible"]
        )

    regular_frames = before["ribbon"]["regular"]
    checks = {
        "http_ok": response_ok,
        "lock_file_signature_valid": (
            canonical_signature(lock_data)
            == lock_data["centerlineSignature"]
        ),
        "geometry_locked": (
            before["lock"]["locked"]
            and before["lock"]["signature"]
            == before["lock"]["currentSignature"]
            and before["lock"]["orbitCount"] == 5
        ),
        "geometry_mutation_rejected": mutation_rejected,
        "unsafe_unlock_rejected": unlock_rejected,
        "centerlines_byte_stable": before["samples"] == after["samples"],
        "common_center_and_core": (
            before["metrics"]["commonCenter"] == [0, 0, 0]
            and before["metrics"]["coreRadius"] == 0.14
        ),
        "all_hover_states": all(
            hover_ok(hover_snapshots[theme], theme) for theme in THEMES
        ),
        "all_selected_states": all(
            one_selected(selected_snapshots[theme], theme)
            for theme in THEMES
        ),
        "single_prebuilt_geometry": all(
            snapshot["geometryBuilds"] == 1
            for snapshot in selected_snapshots.values()
        ),
        "twist_reserve_bounded": all(
            max(snapshot["state"]["mobiusTwistProgress"].values())
            <= 0.2
            for snapshot in selected_snapshots.values()
        ),
        "parallel_transport_stable": all(
            frame["minimumAdjacentFrameDot"] > 0.999
            and frame["seamAlignment"] > 0.999
            and frame["frameFlipCount"] == 0
            and frame["degenerateTriangleCount"] == 0
            for frame in regular_frames
        ),
        "flat_validation_disables_runes": all(
            not any(
                visual["runeVisible"]
                for visual in snapshot["visuals"].values()
            )
            for snapshot in selected_snapshots.values()
        ),
        "no_visible_penetration_contract": (
            all(
                frame["degenerateTriangleCount"] == 0
                for frame in regular_frames
            )
            and all(
                sum(
                    1
                    for visual in snapshot["visuals"].values()
                    if visual["ribbonVisible"]
                )
                == 5
                for snapshot in selected_snapshots.values()
            )
        ),
        "desktop_raycast_hover": raycast_hover in THEMES,
        "desktop_keyboard_selection": (
            ui_selected["state"]["selectedTheme"] == "tarot"
        ),
        "mobile_tap_selection": (
            mobile_snapshot["state"]["selectedTheme"] == "human-design"
            and one_selected(
                mobile_snapshot,
                "human-design",
                expected_width=0.04,
            )
        ),
        "mobile_quality_contract": (
            mobile_perf["dpr"] <= 1.5 and not mobile_perf["shadows"]
        ),
        "render_budget_visible": (
            after["perf"]["calls"] > 0
            and after["perf"]["triangles"] > 0
            and after["perf"]["textures"] <= 2
        ),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "geometryLock": before["lock"],
        "geometryMetrics": before["metrics"],
        "ribbonMetrics": before["ribbon"],
        "interaction": {
            "hover": hover_snapshots,
            "selected": selected_snapshots,
            "mobile": mobile_snapshot,
        },
        "performance": {
            "desktopBefore": before["perf"],
            "desktopAfter": after["perf"],
            "mobile": mobile_perf,
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

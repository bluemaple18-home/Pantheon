from __future__ import annotations

import hashlib
import json
import base64
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "pantheon_material_identity_lab_v1"
BASE_URL = (
    "http://127.0.0.1:5175/"
    "?prototype=pantheon-material-identity-lab"
)


def attach_evidence_hooks(
    page: Page,
    console: list[dict[str, str]],
    page_errors: list[str],
    request_failures: list[str],
) -> None:
    page.on(
        "console",
        lambda message: console.append(
            {"type": message.type, "text": message.text}
        ),
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "requestfailed",
        lambda request: request_failures.append(
            f"{request.method} {request.url}: {request.failure}"
        ),
    )


def wait_frames(page: Page, count: int = 3) -> None:
    page.evaluate(
        """async (count) => {
          for (let index = 0; index < count; index += 1) {
            await new Promise((resolve) => requestAnimationFrame(resolve));
          }
          window.__PANTHEON_MATERIAL_IDENTITY_LAB__.render();
        }""",
        count,
    )


def configure(
    page: Page,
    *,
    phase: int = 3,
    view: str = "front",
    monochrome: bool = True,
    no_micro: bool = False,
    no_relief: bool = False,
    debug_mode: str = "beauty",
    meso_strength: float = 1,
    roughness_variation: float = 1,
) -> None:
    page.evaluate(
        """(config) => {
          const lab = window.__PANTHEON_MATERIAL_IDENTITY_LAB__;
          lab.setControls({
            phase: config.phase,
            monochrome: config.monochrome,
            noMicro: config.noMicro,
            noRelief: config.noRelief,
            debugMode: config.debugMode,
            mesoStrength: config.mesoStrength,
            roughnessVariation: config.roughnessVariation,
          });
          lab.setView(config.view);
          lab.setRotation(0);
        }""",
        {
            "phase": phase,
            "view": view,
            "monochrome": monochrome,
            "noMicro": no_micro,
            "noRelief": no_relief,
            "debugMode": debug_mode,
            "mesoStrength": meso_strength,
            "roughnessVariation": roughness_variation,
        },
    )
    wait_frames(page)


def capture(page: Page, filename: str) -> dict[str, object]:
    path = OUTPUT / filename
    page.screenshot(path=path, full_page=False)
    payload = path.read_bytes()
    return {
        "file": filename,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def contact_sheet(
    page: Page,
    filenames: list[str],
    output_name: str,
    *,
    columns: int = 3,
    target_width: int = 420,
) -> None:
    cells = []
    for filename in filenames:
        encoded = base64.b64encode((OUTPUT / filename).read_bytes()).decode()
        cells.append(
            f"<figure><figcaption>{filename}</figcaption>"
            f'<img src="data:image/png;base64,{encoded}" /></figure>'
        )
    page.set_viewport_size(
        {"width": target_width * columns, "height": 900}
    )
    page.set_content(
        f"""
        <style>
          * {{ box-sizing: border-box; }}
          body {{ margin: 0; background: #111416; color: #d6c08d;
                  font: 12px/1.3 ui-monospace, monospace; }}
          main {{ display: grid; grid-template-columns: repeat({columns}, 1fr);
                  gap: 1px; background: #2a2d2f; }}
          figure {{ margin: 0; padding: 9px; background: #111416; }}
          figcaption {{ height: 22px; }}
          img {{ display: block; width: 100%; height: auto; }}
        </style>
        <main>{''.join(cells)}</main>
        """,
        wait_until="load",
    )
    page.screenshot(path=OUTPUT / output_name, full_page=True)


def run() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    console: list[dict[str, str]] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    captures: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()
        attach_evidence_hooks(page, console, page_errors, request_failures)
        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "Boolean(window.__PANTHEON_MATERIAL_IDENTITY_LAB__)"
        )
        wait_frames(page, 5)

        configure(
            page,
            phase=1,
            meso_strength=0,
            roughness_variation=0,
            no_micro=True,
            no_relief=True,
        )
        captures.append(capture(page, "baseline-neutral.png"))

        phase_files = []
        for phase in (1, 2, 3):
            configure(page, phase=phase)
            filename = f"phase-{phase}-front.png"
            captures.append(capture(page, filename))
            phase_files.append(filename)

        view_files = []
        for view in ("front", "forty-five", "grazing"):
            configure(page, phase=3, view=view)
            filename = f"phase-3-{view}.png"
            captures.append(capture(page, filename))
            view_files.append(filename)

        comparison_modes = [
            ("no-micro", {"no_micro": True}),
            ("no-relief", {"no_relief": True}),
            ("roughness-only", {"debug_mode": "roughness"}),
            ("normal-only", {"debug_mode": "normal"}),
            ("brush-mask-only", {"debug_mode": "brush"}),
            ("formal-color-preview", {"monochrome": False}),
        ]
        mode_files = []
        for label, options in comparison_modes:
            configure(page, phase=3, **options)
            filename = f"{label}.png"
            captures.append(capture(page, filename))
            mode_files.append(filename)

        configure(page, phase=3)
        page.evaluate(
            """() => {
              const labels = document.querySelector("ol");
              if (labels) labels.style.opacity = "0";
            }"""
        )
        captures.append(capture(page, "monochrome-blind-identity.png"))

        rotation_files = []
        for index, radians in enumerate((0, 0.16, 0.32, 0.48, 0.64, 0.8)):
            page.evaluate(
                "(angle) => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.setRotation(angle)",
                radians,
            )
            wait_frames(page, 2)
            filename = f"rotation-{index:02d}.png"
            captures.append(capture(page, filename))
            rotation_files.append(filename)
        page.evaluate(
            """() => {
              const labels = document.querySelector("ol");
              if (labels) labels.style.opacity = "";
              window.__PANTHEON_MATERIAL_IDENTITY_LAB__.setRotation(0);
            }"""
        )

        closeups = []
        themes = [
            "constellation",
            "tarot",
            "mbti",
            "human-design",
            "ziwei-bazi",
        ]
        for theme in themes:
            page.evaluate(
                "(theme) => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.setTheme(theme)",
                theme,
            )
            wait_frames(page)
            filename = f"closeup-{theme}.png"
            captures.append(capture(page, filename))
            closeups.append(filename)

        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate(
            "() => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.setTheme('all')"
        )
        configure(page, phase=3, view="front")
        captures.append(capture(page, "mobile-phase-3.png"))
        mobile_performance = page.evaluate(
            "() => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.measurePerformance(90)"
        )

        page.set_viewport_size({"width": 1440, "height": 900})
        configure(page, phase=3)
        desktop_performance = page.evaluate(
            "() => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.measurePerformance(90)"
        )
        configure(
            page,
            phase=1,
            meso_strength=0,
            roughness_variation=0,
            no_micro=True,
            no_relief=True,
        )
        baseline_performance = page.evaluate(
            "() => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.measurePerformance(90)"
        )
        snapshot = page.evaluate(
            "() => window.__PANTHEON_MATERIAL_IDENTITY_LAB__.snapshot()"
        )
        status = response.status if response else None

        contact_sheet(
            page,
            ["baseline-neutral.png", *phase_files],
            "phase-comparison.png",
            columns=2,
        )
        contact_sheet(page, view_files, "view-comparison.png", columns=3)
        contact_sheet(
            page, mode_files, "debug-mode-comparison.png", columns=3
        )
        contact_sheet(
            page,
            rotation_files,
            "slow-rotation-contact-sheet.png",
            columns=3,
        )
        contact_sheet(page, closeups, "five-closeups.png", columns=3)
        context.close()
        browser.close()

    errors = [item for item in console if item["type"] == "error"]
    report = {
        "status": "PASS" if not errors and not page_errors and not request_failures else "FAIL",
        "httpStatus": status,
        "traceback": None,
        "console": console,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "captures": captures,
        "snapshot": snapshot,
        "performance": {
            "baseline": baseline_performance,
            "desktop": desktop_performance,
            "mobile": mobile_performance,
        },
        "frameTimeDelta": {
            "desktopCpuMs": desktop_performance["cpuRenderMs"]
            - baseline_performance["cpuRenderMs"],
            "mobileCpuMs": mobile_performance["cpuRenderMs"]
            - baseline_performance["cpuRenderMs"],
        },
    }
    (OUTPUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "httpStatus": status,
                "captures": len(captures),
                "consoleErrors": errors,
                "pageErrors": page_errors,
                "requestFailures": request_failures,
                "performance": report["performance"],
                "geometrySignature": snapshot["geometrySignature"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    run()

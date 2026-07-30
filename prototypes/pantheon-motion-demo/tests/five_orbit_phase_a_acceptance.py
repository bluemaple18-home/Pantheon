from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_sphere_phase_a_5"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?studio=1&prototype=pantheon-five-orbit-phase-a"
    "&capture=1&time=0&view=front"
)
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
TRACKS = [
    "Constellation",
    "Tarot",
    "MBTI",
    "HumanDesign",
    "ZiweiBazi",
]
VIEWS = [
    "front",
    "back",
    "left",
    "right",
    "top",
    "bottom",
    "front-left",
    "front-right",
]


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


def read_runtime(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STUDIO__;
          const runtime = studio.orb.userData.sculptRuntime;
          return {
            rootName: studio.orb.name,
            rootChildren: studio.orb.children.map(child => child.name),
            trackNames: Object.keys(runtime.meshes)
              .filter(name => name !== "core"),
            groupNames: Object.keys(runtime.themeGroups),
            groupChildren: Object.fromEntries(
              Object.entries(runtime.themeGroups).map(([id, group]) => [
                id,
                group.children.map(child => child.name),
              ])
            ),
            configs: studio.getOrbitConfigs(),
            metrics: studio.getOrbitMetrics(),
            debugVisible: runtime.nodes.PhaseADebugGuides.visible,
            debugChildren: runtime.nodes.PhaseADebugGuides.children.flatMap(
              child => child.children?.filter(item => item.visible)
                .map(item => item.name) ?? []
            ),
            monochromeMode: runtime.monochromeMode,
            trackColors: Object.fromEntries(
              Object.entries(runtime.meshes)
                .filter(([id]) => id !== "core")
                .map(([id, mesh]) => [id, `#${mesh.material.color.getHexString()}`])
            ),
            lineToRibbonProgress: studio.orb.userData.lineToRibbonProgress,
            cameraPosition: studio.camera.position.toArray(),
            renderCalls: studio.renderer.info.render.calls,
            triangles: studio.renderer.info.render.triangles,
          };
        }"""
    )


def main() -> None:
    preview_dir = EVIDENCE / "after"
    preview_dir.mkdir(parents=True, exist_ok=True)
    console: list[dict[str, str]] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    traceback: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME) if CHROME.exists() else None,
        )
        context = browser.new_context(
            viewport={"width": 1120, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()
        attach_evidence_hooks(
            page,
            console,
            page_errors,
            request_failures,
        )
        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STUDIO__?.orb)"
        )

        visible_traceback = page.locator(
            "text=/Traceback|Unhandled|RuntimeError/"
        )
        if visible_traceback.count():
            traceback.extend(visible_traceback.all_inner_texts())

        initial = read_runtime(page)
        camera_views: dict[str, list[float]] = {}
        canvas = page.locator("[data-pantheon-orb-studio] canvas")
        for view in VIEWS:
            page.evaluate(
                "(view) => window.__PANTHEON_STUDIO__.setView(view)",
                view,
            )
            camera_views[view] = read_runtime(page)["cameraPosition"]
            canvas.screenshot(path=str(preview_dir / f"{view}.png"))

        page.evaluate(
            """() => {
              window.__PANTHEON_STUDIO__.setPhaseAMonochromeMode(true);
              window.__PANTHEON_STUDIO__.setView("front");
            }"""
        )
        canvas.screenshot(path=str(preview_dir / "monochrome-front.png"))
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setView('left')"
        )
        canvas.screenshot(path=str(preview_dir / "monochrome-side.png"))
        monochrome = read_runtime(page)
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAMonochromeMode(false)"
        )

        page.evaluate(
            """() => {
              window.__PANTHEON_STUDIO__.setPhaseADebugVisualization("control");
              window.__PANTHEON_STUDIO__.setView("front");
            }"""
        )
        canvas.screenshot(path=str(preview_dir / "debug-control-points.png"))
        control_debug = read_runtime(page)
        page.evaluate(
            """() => {
              window.__PANTHEON_STUDIO__.setPhaseADebugVisualization("curvature");
              window.__PANTHEON_STUDIO__.setView("front");
            }"""
        )
        canvas.screenshot(path=str(preview_dir / "debug-curvature-heat.png"))
        curvature_debug = read_runtime(page)
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseADebugVisualization('off')"
        )

        hidden_track_previews: dict[str, str] = {}
        hidden_track_states: dict[str, dict] = {}
        for hidden_track_name in TRACKS:
            hidden_configs = [
                {
                    **config,
                    "visible": config["id"] != hidden_track_name,
                }
                for config in initial["configs"]
            ]
            page.evaluate(
                """(configs) => {
                  window.__PANTHEON_STUDIO__.importOrbitConfigJSON(
                    JSON.stringify(configs)
                  );
                  window.__PANTHEON_STUDIO__.setView("front");
                }""",
                hidden_configs,
            )
            hidden_output = (
                preview_dir / f"hidden-{hidden_track_name}.png"
            )
            canvas.screenshot(path=str(hidden_output))
            hidden_track_previews[hidden_track_name] = str(
                hidden_output.relative_to(ROOT)
            )
            hidden_track_states[hidden_track_name] = read_runtime(page)

        solo_track_previews: dict[str, str] = {}
        for solo_track_name in TRACKS:
            solo_configs = [
                {
                    **config,
                    "visible": config["id"] == solo_track_name,
                }
                for config in initial["configs"]
            ]
            page.evaluate(
                """(configs) => {
                  window.__PANTHEON_STUDIO__.importOrbitConfigJSON(
                    JSON.stringify(configs)
                  );
                  window.__PANTHEON_STUDIO__.setView("front");
                }""",
                solo_configs,
            )
            solo_output = preview_dir / f"solo-{solo_track_name}.png"
            canvas.screenshot(path=str(solo_output))
            solo_track_previews[solo_track_name] = str(
                solo_output.relative_to(ROOT)
            )

        page.evaluate(
            """(configs) => {
              window.__PANTHEON_STUDIO__.importOrbitConfigJSON(
                JSON.stringify(configs)
              );
            }""",
            initial["configs"],
        )
        page.get_by_role(
            "checkbox",
            name="Debug sphere／原點／控制點／tangent",
        ).check()
        debug_enabled = read_runtime(page)
        page.get_by_role(
            "checkbox",
            name="Debug sphere／原點／控制點／tangent",
        ).uncheck()

        page.get_by_role(
            "checkbox", name="Constellation visible"
        ).uncheck()
        hidden_track = read_runtime(page)
        page.get_by_role("button", name="Reset", exact=True).click()
        reset = read_runtime(page)

        page.get_by_role(
            "button", name="Export Config JSON", exact=True
        ).click()
        exported_json = page.locator("textarea").input_value()
        page.get_by_role(
            "button", name="Import Config JSON", exact=True
        ).click()
        imported = read_runtime(page)

        result = {
            "url": BASE_URL,
            "httpStatus": response.status if response else None,
            "traceback": traceback,
            "console": console,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
            "initial": initial,
            "monochrome": monochrome,
            "controlDebug": control_debug,
            "curvatureDebug": curvature_debug,
            "cameraViews": camera_views,
            "hiddenTrackPreviews": hidden_track_previews,
            "hiddenTrackStates": hidden_track_states,
            "soloTrackPreviews": solo_track_previews,
            "debugEnabled": debug_enabled,
            "hiddenTrack": hidden_track,
            "reset": reset,
            "exportedConfig": json.loads(exported_json),
            "imported": imported,
            "previews": {
                view: str(
                    (preview_dir / f"{view}.png").relative_to(ROOT)
                )
                for view in VIEWS
            },
            "themeComparisonPreviews": {
                "colorFront": str(
                    (preview_dir / "front.png").relative_to(ROOT)
                ),
                "colorSide": str(
                    (preview_dir / "left.png").relative_to(ROOT)
                ),
                "monochromeFront": str(
                    (
                        preview_dir / "monochrome-front.png"
                    ).relative_to(ROOT)
                ),
                "monochromeSide": str(
                    (
                        preview_dir / "monochrome-side.png"
                    ).relative_to(ROOT)
                ),
            },
        }
        (EVIDENCE / "browser-evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        browser.close()

    metrics = initial["metrics"]
    assert result["httpStatus"] == 200, result
    assert not traceback, result
    assert not [
        item
        for item in console
        if item["type"] in {"error", "warning"}
    ], result
    assert not page_errors, result
    assert not request_failures, result
    assert initial["rootName"] == "PantheonOrbitSphere", result
    assert initial["trackNames"] == TRACKS, result
    assert initial["groupNames"] == TRACKS, result
    assert all(
        initial["groupChildren"][track] == [f"{track}_OrbitTrack"]
        for track in TRACKS
    ), result
    assert metrics["trackCount"] == 5, result
    assert 0.32 <= metrics["minRadius"] <= 0.48, result
    assert metrics["maxRadius"] <= 1.04, result
    assert 0.7 <= metrics["averageRadius"] <= 0.96, result
    assert metrics["extentRatio"] <= 1.12, result
    assert all(
        ratio <= 1.12
        for ratio in metrics["withoutTrackExtentRatios"].values()
    ), result
    assert metrics["nearestCoreSurfaceDistance"] >= 0.12, result
    assert 2 <= sum(
        track["minRadius"] <= 0.48
        for track in metrics["tracks"].values()
    ) <= 4, result
    assert all(
        track["nonPlanarOffset"] >= 0.2
        for track in metrics["tracks"].values()
    ), result
    assert all(
        8 <= track["controlPointCount"] <= 12
        for track in metrics["tracks"].values()
    ), result
    assert all(
        track["minBendRadius"] >= 0.18
        for track in metrics["tracks"].values()
    ), result
    assert not any(
        track["hasLocalLoop"]
        for track in metrics["tracks"].values()
    ), result
    assert all(
        track["extentY"] >= 0.65
        for track in metrics["tracks"].values()
    ), result
    assert len(
        {
            (
                config["inclination"],
                config["azimuth"],
                config["latitudeAmplitude"],
                config["coreApproachRadius"],
                config["pathPhase"],
            )
            for config in initial["configs"]
        }
    ) == 5, result
    assert all(
        sum(config["visible"] for config in state["configs"]) == 4
        for state in result["hiddenTrackStates"].values()
    ), result
    assert initial["lineToRibbonProgress"] == 0, result
    assert initial["monochromeMode"] is False, result
    assert monochrome["monochromeMode"] is True, result
    assert set(monochrome["trackColors"].values()) == {"#eef2f4"}, result
    assert [config["label"] for config in initial["configs"]] == [
        "星座",
        "塔羅",
        "MBTI",
        "人類圖",
        "紫微八字",
    ], result
    assert len(
        {config["curveProfile"] for config in initial["configs"]}
    ) == 5, result
    assert initial["debugVisible"] is False, result
    assert debug_enabled["debugVisible"] is True, result
    assert all(
        name.endswith("_ControlPoints") or name.endswith("_Tangents")
        for name in control_debug["debugChildren"]
    ), result
    assert control_debug["debugChildren"], result
    assert all(
        name.endswith("_CurvatureHeat")
        for name in curvature_debug["debugChildren"]
    ), result
    assert curvature_debug["debugChildren"], result
    assert hidden_track["configs"][0]["visible"] is False, result
    assert all(config["visible"] for config in reset["configs"]), result
    assert imported["configs"] == initial["configs"], result
    assert len(set(tuple(value) for value in camera_views.values())) == 8, result
    assert initial["renderCalls"] > 0, result
    assert initial["triangles"] < 100_000, result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

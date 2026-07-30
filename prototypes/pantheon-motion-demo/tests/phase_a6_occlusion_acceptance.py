from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_sphere_phase_a_6"
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
FINAL_VIEWS = [
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
          const inner = runtime.meshes.innerOcclusionSphere;
          const core = runtime.meshes.core;
          const trackEntries = Object.entries(runtime.meshes)
            .filter(([id]) => !["core", "innerOcclusionSphere"].includes(id));
          return {
            rootName: studio.orb.name,
            rootChildren: studio.orb.children.map(child => child.name),
            trackNames: trackEntries.map(([id]) => id),
            configs: studio.getOrbitConfigs(),
            metrics: studio.getOrbitMetrics(),
            presentationMode: runtime.presentationMode,
            monochromeMode: runtime.monochromeMode,
            innerOcclusion: {
              visible: inner.visible,
              radius: runtime.params.innerOcclusionRadius,
              apertureRadius: runtime.params.apertureRadius,
              transparent: inner.material.transparent,
              opacity: inner.material.opacity,
              depthWrite: inner.material.depthWrite,
              depthTest: inner.material.depthTest,
              metalness: inner.material.metalness,
              roughness: inner.material.roughness,
            },
            coreVisible: core.visible,
            coreRadius: runtime.params.coreRadius,
            visibleCrossingsDebug:
              runtime.nodes.VisibleFinalCrossingsDebug.visible,
            trackMaterials: Object.fromEntries(
              trackEntries.map(([id, mesh]) => [id, {
                transparent: mesh.material.transparent,
                opacity: mesh.material.opacity,
                depthWrite: mesh.material.depthWrite,
                depthTest: mesh.material.depthTest,
                color: `#${mesh.material.color.getHexString()}`,
              }])
            ),
            renderCalls: studio.renderer.info.render.calls,
            triangles: studio.renderer.info.render.triangles,
          };
        }"""
    )


def set_mode(page: Page, mode: str, view: str = "front") -> None:
    page.evaluate(
        """([mode, view]) => {
          window.__PANTHEON_STUDIO__.setPhaseAPresentationMode(mode);
          window.__PANTHEON_STUDIO__.setView(view);
        }""",
        [mode, view],
    )


def main() -> None:
    xray_dir = EVIDENCE / "xray"
    final_dir = EVIDENCE / "final"
    xray_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
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

        canvas = page.locator("[data-pantheon-orb-studio] canvas")

        set_mode(page, "xray")
        xray_color = read_runtime(page)
        canvas.screenshot(path=str(xray_dir / "color-front.png"))

        set_mode(page, "monochrome-xray")
        xray_monochrome = read_runtime(page)
        canvas.screenshot(path=str(xray_dir / "monochrome-front.png"))

        final_views: dict[str, dict] = {}
        set_mode(page, "final-occluded")
        for view in FINAL_VIEWS:
            page.evaluate(
                "(view) => window.__PANTHEON_STUDIO__.setView(view)",
                view,
            )
            final_views[view] = read_runtime(page)
            canvas.screenshot(path=str(final_dir / f"{view}.png"))

        set_mode(page, "monochrome-occluded")
        monochrome_occluded = read_runtime(page)
        canvas.screenshot(
            path=str(final_dir / "monochrome-front.png")
        )

        set_mode(page, "final-occluded")
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAApertureDebugMode(true)"
        )
        aperture_debug = read_runtime(page)
        canvas.screenshot(
            path=str(final_dir / "debug-aperture.png")
        )
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAApertureDebugMode(false)"
        )

        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAOcclusionSoloMode(true)"
        )
        occlusion_solo = read_runtime(page)
        canvas.screenshot(
            path=str(final_dir / "inner-occlusion-sphere.png")
        )
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAOcclusionSoloMode(false)"
        )

        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAVisibleCrossingsDebugMode(true)"
        )
        crossings_debug = read_runtime(page)
        canvas.screenshot(
            path=str(final_dir / "debug-visible-crossings.png")
        )
        page.evaluate(
            "() => window.__PANTHEON_STUDIO__.setPhaseAVisibleCrossingsDebugMode(false)"
        )

        result = {
            "url": BASE_URL,
            "httpStatus": response.status if response else None,
            "traceback": traceback,
            "console": console,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
            "xrayColor": xray_color,
            "xrayMonochrome": xray_monochrome,
            "finalViews": final_views,
            "monochromeOccluded": monochrome_occluded,
            "apertureDebug": aperture_debug,
            "occlusionSolo": occlusion_solo,
            "crossingsDebug": crossings_debug,
            "previews": {
                "xrayColorFront": str(
                    (xray_dir / "color-front.png").relative_to(ROOT)
                ),
                "xrayMonochromeFront": str(
                    (xray_dir / "monochrome-front.png").relative_to(ROOT)
                ),
                "finalColorFront": str(
                    (final_dir / "front.png").relative_to(ROOT)
                ),
                "finalMonochromeFront": str(
                    (
                        final_dir / "monochrome-front.png"
                    ).relative_to(ROOT)
                ),
                "apertureDebug": str(
                    (final_dir / "debug-aperture.png").relative_to(ROOT)
                ),
                "occlusionSphere": str(
                    (
                        final_dir / "inner-occlusion-sphere.png"
                    ).relative_to(ROOT)
                ),
                "visibleCrossingsDebug": str(
                    (
                        final_dir / "debug-visible-crossings.png"
                    ).relative_to(ROOT)
                ),
            },
        }
        (EVIDENCE / "browser-evidence.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        browser.close()

    metrics = final_views["front"]["metrics"]
    assert result["httpStatus"] == 200, result
    assert not traceback, result
    assert not [
        item
        for item in console
        if item["type"] in {"error", "warning"}
    ], result
    assert not page_errors, result
    assert not request_failures, result
    assert xray_color["rootName"] == "PantheonOrbitSphere", result
    assert xray_color["trackNames"] == TRACKS, result
    assert xray_color["presentationMode"] == "xray", result
    assert xray_color["innerOcclusion"]["visible"] is False, result
    assert xray_monochrome["presentationMode"] == "monochrome-xray"
    assert xray_monochrome["monochromeMode"] is True, result
    assert final_views["front"]["presentationMode"] == "final-occluded"
    assert final_views["front"]["innerOcclusion"]["visible"] is True
    assert monochrome_occluded["presentationMode"] == (
        "monochrome-occluded"
    )
    assert monochrome_occluded["monochromeMode"] is True, result
    assert final_views["front"]["innerOcclusion"] == {
        "visible": True,
        "radius": 0.8,
        "apertureRadius": 0.166,
        "transparent": False,
        "opacity": 1,
        "depthWrite": True,
        "depthTest": True,
        "metalness": 0.1,
        "roughness": 0.82,
    }, result
    assert all(
        material["transparent"] is False
        and material["opacity"] == 1
        and material["depthWrite"] is True
        and material["depthTest"] is True
        for material in final_views["front"]["trackMaterials"].values()
    ), result
    assert metrics["trackCount"] == 5, result
    assert metrics["frontProjectedCrossings"] >= (
        metrics["visibleFinalCrossings"]
    ), result
    assert metrics["visibleFinalCrossings"] <= 20, result
    assert 0.55 <= metrics["coreVisibleRatioEstimate"] <= 0.9, result
    assert not any(
        track["hasLocalLoop"]
        for track in metrics["tracks"].values()
    ), result
    assert final_views["front"]["coreVisible"] is True, result
    assert aperture_debug["innerOcclusion"]["visible"] is True, result
    assert occlusion_solo["innerOcclusion"]["visible"] is True, result
    assert occlusion_solo["coreVisible"] is False, result
    assert crossings_debug["visibleCrossingsDebug"] is True, result
    assert final_views["front"]["renderCalls"] > 0, result
    assert final_views["front"]["triangles"] < 120_000, result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

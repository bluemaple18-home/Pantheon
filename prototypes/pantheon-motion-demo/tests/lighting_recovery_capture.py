from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "pantheon_lighting_recovery_v1"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits"
    "&geometryVersion=v1.1"
    "&capture=1"
    "&view=front"
)
MODES = (
    ("A-environment-only", "environment-only"),
    ("B-key-only", "key-only"),
    ("C-key-rim", "key-rim"),
    ("D-full-product-studio", "full"),
)


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


def prepare_fixed_state(page: Page) -> None:
    page.evaluate(
        """async () => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.setPaused(true);
          studio.setOrbitMotionPaused(true);
          studio.setReducedMotionPreview(true);
          studio.clearSelection();
          studio.setHoveredTheme(null);
          studio.setMonochrome(false);
          studio.setView("front");
          studio.setDebugDisplay({
            metalHighlightStrength: 1,
            validationMode: "material-v3",
            flatMaterial: false,
            showBand: true,
            showCore: true
          });
          await new Promise((resolve) => {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                requestAnimationFrame(resolve);
              });
            });
          });
          studio.render();
        }"""
    )


def set_mode_and_wait(page: Page, mode: str) -> dict:
    return page.evaluate(
        """async (mode) => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const beforeFrame = studio.frameIndex;
          studio.setProductLighting({ mode });
          await new Promise((resolve) => {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                requestAnimationFrame(resolve);
              });
            });
          });
          studio.render();
          const lighting = studio.productLighting;
          const interaction = studio.interaction;
          const firstBand = Object.values(interaction.visuals)[0];
          const bandMaterials = Object.fromEntries(
            Object.entries(interaction.visuals).map(([id, visual]) => [
              id,
              {
                roughness: visual.roughness,
                metalness: visual.metalness,
                clearcoat: visual.clearcoat,
                clearcoatRoughness: visual.clearcoatRoughness,
                envMapIntensity: visual.envMapIntensity
              }
            ])
          );
          const bandMesh = [];
          studio.orbits.traverse((node) => {
            if (node.name?.startsWith("PantheonBand.")) {
              bandMesh.push(node);
            }
          });
          const materials = bandMesh[0]?.material || [];
          return {
            captureMode: mode,
            timestamp: new Date().toISOString(),
            frameIndex: studio.frameIndex,
            framesWaited: studio.frameIndex - beforeFrame,
            keyIntensity: lighting.intensities.key,
            rimIntensity: lighting.intensities.rim,
            topIntensity: lighting.intensities.top,
            fillIntensity: lighting.intensities.fill,
            ambientIntensity: lighting.intensities.ambient,
            hemisphereIntensity: lighting.intensities.hemisphere,
            toneMapping: studio.renderer.toneMapping === 6
              ? "AgXToneMapping"
              : `unexpected:${studio.renderer.toneMapping}`,
            exposure: studio.renderer.toneMappingExposure,
            materialEnvMapIntensity: {
              topBottom:
                materials[0]?.envMapIntensity ??
                firstBand.envMapIntensity,
              bevel: materials[1]?.envMapIntensity ?? null,
              edge: materials[2]?.envMapIntensity ?? null
            },
            metalHighlightStrength:
              interaction.debug.metalHighlightStrength,
            bandMaterials,
            selfCore: studio.selfCoreEffect,
            geometrySignature:
              studio.geometryLock.signature
          };
        }""",
        mode,
    )


def measure_scene(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const renderer = studio.renderer;
          const scene = studio.scene;
          const camera = studio.camera;
          const gl = renderer.getContext();
          const width = gl.drawingBufferWidth;
          const height = gl.drawingBufferHeight;
          const bands = [];
          const runes = [];
          studio.orbits.traverse((node) => {
            if (node.name?.startsWith("PantheonBand.")) bands.push(node);
            if (node.name?.startsWith("RuneFlow.")) runes.push(node);
          });
          const core = studio.orbits.getObjectByName("SelfCore");
          const themeOrbit = Object.fromEntries(
            studio.themes.map(({ id, orbitId }) => [id, orbitId])
          );

          const toLinear = (value) =>
            value <= 0.04045
              ? value / 12.92
              : Math.pow((value + 0.055) / 1.055, 2.4);
          const readPixels = () => {
            renderer.render(scene, camera);
            const pixels = new Uint8Array(width * height * 4);
            gl.readPixels(
              0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels
            );
            return pixels;
          };
          const summarize = (pixels, predicate) => {
            const values = [];
            for (let offset = 0; offset < pixels.length; offset += 4) {
              const pixelIndex = offset / 4;
              const x = pixelIndex % width;
              const y = Math.floor(pixelIndex / width);
              const red = pixels[offset] / 255;
              const green = pixels[offset + 1] / 255;
              const blue = pixels[offset + 2] / 255;
              if (!predicate({ red, green, blue, x, y })) continue;
              values.push(
                0.2126 * toLinear(red) +
                0.7152 * toLinear(green) +
                0.0722 * toLinear(blue)
              );
            }
            values.sort((first, second) => first - second);
            const percentile = (value) =>
              values[
                Math.min(
                  values.length - 1,
                  Math.floor((values.length - 1) * value)
                )
              ] || 0;
            const average =
              values.reduce((sum, value) => sum + value, 0) /
              Math.max(1, values.length);
            return {
              pixels: values.length,
              average,
              p05: percentile(0.05),
              p50: percentile(0.5),
              p95: percentile(0.95),
              over095Ratio:
                values.filter((value) => value > 0.95).length /
                Math.max(1, values.length),
              under008Ratio:
                values.filter((value) => value < 0.08).length /
                Math.max(1, values.length)
            };
          };

          const finalPixels = readPixels();
          const fullFrame = summarize(finalPixels, () => true);
          const sphereRadius = Math.min(width, height) * 0.45;
          const sphere = summarize(
            finalPixels,
            ({ x, y }) =>
              (x - width * 0.5) ** 2 +
              (y - height * 0.5) ** 2 <= sphereRadius ** 2
          );

          const oldBackground = scene.background;
          const oldClearColor = renderer.getClearColor(
            core.material.color.clone()
          ).clone();
          const oldClearAlpha = renderer.getClearAlpha();
          const bandVisibility = bands.map((node) => node.visible);
          const runeVisibility = runes.map((node) => node.visible);
          const coreVisible = core.visible;
          scene.background = null;
          renderer.setClearColor(0x000000, 1);

          const objectPredicate = ({ red, green, blue }) =>
            Math.max(red, green, blue) > 1 / 255;
          const setVisibleTheme = (themeId) => {
            const orbitId = themeId ? themeOrbit[themeId] : null;
            bands.forEach((node) => {
              node.visible =
                !themeId || node.name === `PantheonBand.${orbitId}`;
            });
            runes.forEach((node) => {
              node.visible =
                !themeId || node.name === `RuneFlow.${orbitId}`;
            });
            core.visible = false;
          };

          setVisibleTheme(null);
          const combinedBands = summarize(
            readPixels(),
            objectPredicate
          );
          const themeMetrics = {};
          Object.keys(themeOrbit).forEach((themeId) => {
            setVisibleTheme(themeId);
            themeMetrics[themeId] = summarize(
              readPixels(),
              objectPredicate
            );
          });

          bands.forEach((node) => { node.visible = false; });
          runes.forEach((node) => { node.visible = false; });
          core.visible = true;
          const selfCore = summarize(readPixels(), objectPredicate);

          bands.forEach((node, index) => {
            node.visible = bandVisibility[index];
          });
          runes.forEach((node, index) => {
            node.visible = runeVisibility[index];
          });
          core.visible = coreVisible;
          scene.background = oldBackground;
          renderer.setClearColor(oldClearColor, oldClearAlpha);
          renderer.render(scene, camera);

          const themeAverages = Object.fromEntries(
            Object.entries(themeMetrics).map(([id, metrics]) => [
              id,
              metrics.average
            ])
          );
          const averages = Object.values(themeAverages);
          return {
            width,
            height,
            fullFrame,
            sphere,
            combinedBands,
            themes: themeMetrics,
            themeAverages,
            brightestToDarkestRatio:
              Math.max(...averages) /
              Math.max(1e-9, Math.min(...averages)),
            selfCore
          };
        }"""
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    captures: dict[str, dict] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        attach_evidence_hooks(
            page,
            console_errors,
            page_errors,
            request_failures,
        )
        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        prepare_fixed_state(page)
        canvas = page.locator("[data-pantheon-star-orbits] canvas")

        for filename, mode in MODES:
            metadata = set_mode_and_wait(page, mode)
            target = OUTPUT / f"{filename}.png"
            canvas.screenshot(path=str(target), timeout=15_000)
            metadata["sha256"] = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()
            captures[filename] = metadata

        measurements = measure_scene(page)
        browser.close()

    hashes = [capture["sha256"] for capture in captures.values()]
    distinct_captures = len(set(hashes)) == len(hashes)
    frames_valid = all(
        capture["framesWaited"] >= 3
        for capture in captures.values()
    )
    runtime_values_valid = all(
        capture["metalHighlightStrength"] == 1
        and capture["toneMapping"] == "AgXToneMapping"
        for capture in captures.values()
    )
    capture_status = (
        "PASS"
        if (
            response is not None
            and response.ok
            and not console_errors
            and not page_errors
            and not request_failures
            and distinct_captures
            and frames_valid
            and runtime_values_valid
        )
        else "FAIL"
    )
    visual_thresholds = {
        "brightestToDarkestRatioAtMost3":
            measurements["brightestToDarkestRatio"] <= 3,
        "bandUnder008AtMost035":
            measurements["combinedBands"]["under008Ratio"] <= 0.35,
        "bandOver095Below001":
            measurements["combinedBands"]["over095Ratio"] < 0.01,
        "selfCoreUnder008Below078":
            measurements["selfCore"]["under008Ratio"] < 0.78,
    }
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "captureStatus": capture_status,
        "visualStatus": (
            "PASS" if all(visual_thresholds.values()) else "NEEDS WORK"
        ),
        "capturesDistinct": distinct_captures,
        "framesValid": frames_valid,
        "runtimeValuesValid": runtime_values_valid,
        "captures": captures,
        "measurements": measurements,
        "visualThresholds": visual_thresholds,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
    }
    (OUTPUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if capture_status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

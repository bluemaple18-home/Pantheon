from __future__ import annotations

import hashlib
import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "pantheon_reflection_art_direction_v1"
EVIDENCE = OUTPUT / "evidence"
BASE_URL = (
    "http://127.0.0.1:5174/"
    "?prototype=pantheon-star-orbits&capture=1&geometryVersion=v1.1"
)
CANDIDATES = {
    "conservative": "candidate-a-conservative",
    "editorial": "candidate-b-editorial",
    "dramatic": "candidate-c-dramatic",
}
VIEWS = {
    "front": "front",
    "front-left": "front-left",
    "side": "right",
    "back": "back",
    "top": "top",
}
THEMES = (
    "constellation",
    "tarot",
    "mbti",
    "human-design",
    "ziwei-bazi",
)
EXPECTED_COLORS = {
    "constellation": "#294f87",
    "tarot": "#9b4352",
    "mbti": "#2b8178",
    "human-design": "#b9793e",
    "ziwei-bazi": "#8d472d",
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


def canvas_shot(page: Page, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.locator("[data-pantheon-star-orbits] canvas").screenshot(
        path=str(path),
        timeout=15_000,
    )


def frame_metrics(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.render();
          const gl = studio.renderer.getContext();
          const width = gl.drawingBufferWidth;
          const height = gl.drawingBufferHeight;
          const pixels = new Uint8Array(width * height * 4);
          gl.readPixels(
            0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels
          );
          const radius = Math.min(width, height) * 0.29;
          const cx = width * 0.5;
          const cy = height * 0.5;
          let centralSamples = 0;
          let centralOverexposedPixels = 0;
          let globalOverexposedPixels = 0;
          let maximumLuminance = 0;
          for (let y = 0; y < height; y += 2) {
            for (let x = 0; x < width; x += 2) {
              const index = (y * width + x) * 4;
              const r = pixels[index] / 255;
              const g = pixels[index + 1] / 255;
              const b = pixels[index + 2] / 255;
              const luminance = r * 0.2126 + g * 0.7152 + b * 0.0722;
              maximumLuminance = Math.max(maximumLuminance, luminance);
              const overexposed = luminance > 0.86 &&
                Math.max(r, g, b) > 0.94;
              if (overexposed) globalOverexposedPixels += 1;
              if ((x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2) {
                centralSamples += 1;
                if (overexposed) centralOverexposedPixels += 1;
              }
            }
          }
          return {
            width,
            height,
            maximumLuminance,
            centralSamples,
            centralOverexposedPixels,
            centralOverexposureRatio:
              centralOverexposedPixels / Math.max(1, centralSamples),
            globalOverexposedPixels,
            globalOverexposureRatio:
              globalOverexposedPixels /
              Math.max(1, Math.ceil(width / 2) * Math.ceil(height / 2))
          };
        }"""
    )


def band_metrics(page: Page, theme_id: str) -> dict:
    return page.evaluate(
        """(themeId) => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const theme = studio.themes.find((entry) => entry.id === themeId);
          const bands = [];
          studio.orbits.traverse((node) => {
            if (node.name?.startsWith("PantheonBand.")) bands.push(node);
          });
          const target = bands.find(
            (node) => node.name === `PantheonBand.${theme.orbitId}`
          );
          const visibility = bands.map((node) => node.visible);
          const core = studio.orbits.getObjectByName("SelfCore");
          const coreVisible = core.visible;
          const oldClear = target.material[0].color.clone();
          studio.renderer.getClearColor(oldClear);
          const oldClearHex = oldClear.getHex();
          const oldAlpha = studio.renderer.getClearAlpha();
          bands.forEach((node) => { node.visible = node === target; });
          core.visible = false;
          studio.renderer.setClearColor(0x000000, 1);
          studio.renderer.render(studio.scene, studio.camera);
          const gl = studio.renderer.getContext();
          const width = gl.drawingBufferWidth;
          const height = gl.drawingBufferHeight;
          const pixels = new Uint8Array(width * height * 4);
          gl.readPixels(
            0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels
          );
          const luminances = [];
          let maximumLuminance = 0;
          let readablePixels = 0;
          let objectPixels = 0;
          let overexposedPixels = 0;
          let centralOverexposedPixels = 0;
          const radius = Math.min(width, height) * 0.29;
          const cx = width * 0.5;
          const cy = height * 0.5;
          for (let index = 0; index < pixels.length; index += 16) {
            const r = pixels[index] / 255;
            const g = pixels[index + 1] / 255;
            const b = pixels[index + 2] / 255;
            if (Math.max(r, g, b) < 0.012) continue;
            const luminance = r * 0.2126 + g * 0.7152 + b * 0.0722;
            const pixelIndex = index / 4;
            const x = pixelIndex % width;
            const y = Math.floor(pixelIndex / width);
            objectPixels += 1;
            luminances.push(luminance);
            maximumLuminance = Math.max(maximumLuminance, luminance);
            if (luminance > 0.055) readablePixels += 1;
            if (luminance > 0.86 && Math.max(r, g, b) > 0.94) {
              overexposedPixels += 1;
              if ((x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2) {
                centralOverexposedPixels += 1;
              }
            }
          }
          luminances.sort((a, b) => a - b);
          const percentile = (value) =>
            luminances[Math.min(
              luminances.length - 1,
              Math.floor(luminances.length * value)
            )] || 0;

          const samples =
            studio.getCenterlineSamples(360)[theme.orbitId];
          const sampleLuminance = samples.map((point) => {
            const projected = studio.camera.position
              .clone()
              .set(point[0], point[1], point[2]);
            studio.orbits.localToWorld(projected);
            projected.project(studio.camera);
            const px = Math.round((projected.x * 0.5 + 0.5) * width);
            const py = Math.round((projected.y * 0.5 + 0.5) * height);
            let localMaximum = 0;
            for (let oy = -2; oy <= 2; oy += 1) {
              for (let ox = -2; ox <= 2; ox += 1) {
                const x = Math.max(0, Math.min(width - 1, px + ox));
                const y = Math.max(0, Math.min(height - 1, py + oy));
                const index = (y * width + x) * 4;
                const luminance =
                  (pixels[index] / 255) * 0.2126 +
                  (pixels[index + 1] / 255) * 0.7152 +
                  (pixels[index + 2] / 255) * 0.0722;
                localMaximum = Math.max(localMaximum, luminance);
              }
            }
            return localMaximum;
          });
          const longestCircularRun = (predicate) => {
            let longest = 0;
            let current = 0;
            for (let index = 0; index < sampleLuminance.length * 2; index += 1) {
              if (predicate(sampleLuminance[index % sampleLuminance.length])) {
                current += 1;
                longest = Math.max(longest, current);
              } else {
                current = 0;
              }
            }
            return Math.min(longest, sampleLuminance.length);
          };
          const medianLuminance = percentile(0.5);
          const brightThreshold =
            medianLuminance +
            (maximumLuminance - medianLuminance) * 0.34;
          const longestDarkSamples = longestCircularRun(
            (value) => value < 0.1
          );
          const longestHighlightSamples = longestCircularRun(
            (value) => value >= brightThreshold
          );

          bands.forEach((node, index) => {
            node.visible = visibility[index];
          });
          core.visible = coreVisible;
          studio.renderer.setClearColor(oldClearHex, oldAlpha);
          studio.renderer.render(studio.scene, studio.camera);
          return {
            themeId,
            maximumLuminance,
            medianLuminance,
            p95Luminance: percentile(0.95),
            objectPixels,
            readablePixelRatio: readablePixels / Math.max(1, objectPixels),
            overexposedPixels,
            centralOverexposedPixels,
            longestDarkSamples,
            longestDarkFraction: longestDarkSamples / sampleLuminance.length,
            longestHighlightSamples,
            longestHighlightFraction:
              longestHighlightSamples / sampleLuminance.length,
            brightThreshold
          };
        }""",
        theme_id,
    )


def core_metrics(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const bands = [];
          studio.orbits.traverse((node) => {
            if (node.name?.startsWith("PantheonBand.")) bands.push(node);
          });
          const visibility = bands.map((node) => node.visible);
          const core = studio.orbits.getObjectByName("SelfCore");
          bands.forEach((node) => { node.visible = false; });
          core.visible = true;
          studio.renderer.render(studio.scene, studio.camera);
          const gl = studio.renderer.getContext();
          const pixels = new Uint8Array(
            gl.drawingBufferWidth * gl.drawingBufferHeight * 4
          );
          gl.readPixels(
            0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight,
            gl.RGBA, gl.UNSIGNED_BYTE, pixels
          );
          let maximumLuminance = 0;
          for (let index = 0; index < pixels.length; index += 16) {
            const luminance =
              (pixels[index] / 255) * 0.2126 +
              (pixels[index + 1] / 255) * 0.7152 +
              (pixels[index + 2] / 255) * 0.0722;
            maximumLuminance = Math.max(maximumLuminance, luminance);
          }
          bands.forEach((node, index) => {
            node.visible = visibility[index];
          });
          studio.renderer.render(studio.scene, studio.camera);
          return { maximumLuminance };
        }"""
    )


def rotation_metrics(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const initial = studio.orbits.rotation.y;
          const gl = studio.renderer.getContext();
          const width = gl.drawingBufferWidth;
          const height = gl.drawingBufferHeight;
          const side = Math.floor(Math.min(width, height) * 0.58);
          const x = Math.floor((width - side) / 2);
          const y = Math.floor((height - side) / 2);
          const pixels = new Uint8Array(side * side * 4);
          const frames = [];
          for (let step = 0; step <= 60; step += 1) {
            studio.orbits.rotation.y =
              initial + (step / 60) * Math.PI * 2;
            studio.renderer.render(studio.scene, studio.camera);
            gl.readPixels(
              x, y, side, side, gl.RGBA, gl.UNSIGNED_BYTE, pixels
            );
            let luminanceSum = 0;
            let overexposed = 0;
            let samples = 0;
            for (let index = 0; index < pixels.length; index += 64) {
              const r = pixels[index] / 255;
              const g = pixels[index + 1] / 255;
              const b = pixels[index + 2] / 255;
              const luminance = r * 0.2126 + g * 0.7152 + b * 0.0722;
              luminanceSum += luminance;
              if (luminance > 0.86 && Math.max(r, g, b) > 0.94) {
                overexposed += 1;
              }
              samples += 1;
            }
            frames.push({
              equivalentSecond: step,
              meanLuminance: luminanceSum / Math.max(1, samples),
              overexposureRatio: overexposed / Math.max(1, samples)
            });
          }
          studio.orbits.rotation.y = initial;
          studio.renderer.render(studio.scene, studio.camera);
          const stepDeltas = frames.slice(1).map((frame, index) =>
            Math.abs(frame.meanLuminance - frames[index].meanLuminance)
          );
          return {
            frameCount: frames.length,
            equivalentDurationSeconds: 60,
            seamLuminanceDelta: Math.abs(
              frames[0].meanLuminance -
              frames[frames.length - 1].meanLuminance
            ),
            seamOverexposureDelta: Math.abs(
              frames[0].overexposureRatio -
              frames[frames.length - 1].overexposureRatio
            ),
            maximumStepLuminanceDelta: Math.max(...stepDeltas),
            frames
          };
        }"""
    )


def record_preview(page: Page, output: Path) -> bool:
    try:
        with page.expect_download(timeout=30_000) as download_info:
            page.evaluate(
                """async () => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  const canvas = studio.renderer.domElement;
                  const stream = canvas.captureStream(24);
                  const mimeType = MediaRecorder.isTypeSupported(
                    "video/webm;codecs=vp9"
                  ) ? "video/webm;codecs=vp9" : "video/webm";
                  const recorder = new MediaRecorder(stream, {
                    mimeType,
                    videoBitsPerSecond: 2_400_000
                  });
                  const chunks = [];
                  recorder.ondataavailable = (event) => {
                    if (event.data.size) chunks.push(event.data);
                  };
                  const stopped = new Promise((resolve) => {
                    recorder.onstop = resolve;
                  });
                  const initial = studio.orbits.rotation.y;
                  recorder.start(250);
                  const startedAt = performance.now();
                  await new Promise((resolve) => {
                    const animate = (now) => {
                      const progress = Math.min(1, (now - startedAt) / 8000);
                      studio.orbits.rotation.y =
                        initial + progress * Math.PI * 2;
                      studio.renderer.render(studio.scene, studio.camera);
                      if (progress < 1) requestAnimationFrame(animate);
                      else resolve();
                    };
                    requestAnimationFrame(animate);
                  });
                  recorder.stop();
                  await stopped;
                  studio.orbits.rotation.y = initial;
                  studio.renderer.render(studio.scene, studio.camera);
                  const blob = new Blob(chunks, { type: mimeType });
                  const anchor = document.createElement("a");
                  anchor.href = URL.createObjectURL(blob);
                  anchor.download = "pantheon-reflection-360.webm";
                  document.body.append(anchor);
                  anchor.click();
                  anchor.remove();
                  setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
                }"""
            )
        download_info.value.save_as(str(output))
        return output.exists() and output.stat().st_size > 0
    except Exception:
        return False


def canonical_geometry_signature(data: dict) -> str:
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
        lighting = desktop.evaluate(f"() => {studio}.lightingBaseline")
        lock = desktop.evaluate(f"() => {studio}.geometryLock")
        band_dimensions = desktop.evaluate(
            f"() => {studio}.interaction.bandDimensions"
        )
        base_colors = desktop.evaluate(
            f"""() => Object.fromEntries(
              Object.entries({studio}.interaction.visuals).map(
                ([id, visual]) => [id, visual.baseColor]
              )
            )"""
        )

        desktop.evaluate(
            f"() => {studio}.setReflectionCandidate('baseline')"
        )
        desktop.evaluate(f"() => {studio}.setView('front')")
        baseline_metrics = frame_metrics(desktop)
        canvas_shot(desktop, EVIDENCE / "baseline-front.png")

        candidate_metrics: dict[str, dict] = {}
        preview_status: dict[str, bool] = {}
        for candidate_id, directory in CANDIDATES.items():
            candidate_root = EVIDENCE / directory
            desktop.evaluate(
                f"() => {studio}.setReflectionCandidate('{candidate_id}')"
            )
            desktop.evaluate(
                f"() => {studio}.setDebugDisplay("
                "{validationMode: 'material-v3'})"
            )
            for output_name, view in VIEWS.items():
                desktop.evaluate(f"() => {studio}.setView('{view}')")
                canvas_shot(
                    desktop,
                    candidate_root / f"{output_name}.png",
                )
            desktop.evaluate(f"() => {studio}.setView('front')")
            candidate_metrics[candidate_id] = {
                "frame": frame_metrics(desktop),
                "bands": {
                    theme_id: band_metrics(desktop, theme_id)
                    for theme_id in THEMES
                },
                "core": core_metrics(desktop),
            }
            preview_status[candidate_id] = record_preview(
                desktop,
                candidate_root / "preview-360.webm",
            )

        desktop.evaluate(
            f"() => {studio}.setReflectionCandidate('editorial')"
        )
        desktop.evaluate(f"() => {studio}.setView('front')")
        debug_modes = (
            "physical-specular",
            "highlight-mask",
            "core-suppression",
            "grazing-response",
            "dark-side-lift",
            "reflection-rotation",
            "luminance-heatmap",
            "overexposure-mask",
            "reflection-profile",
            "baseline-linked-compare",
        )
        for mode in debug_modes:
            desktop.evaluate(
                f"() => {studio}.setDebugDisplay("
                f"{{validationMode: '{mode}'}})"
            )
            canvas_shot(desktop, EVIDENCE / "debug" / f"{mode}.png")
        desktop.evaluate(
            f"() => {studio}.setDebugDisplay("
            "{validationMode: 'material-v3'})"
        )
        rotation = rotation_metrics(desktop)
        editorial_snapshot = desktop.evaluate(f"() => {studio}.interaction")
        performance = desktop.evaluate(f"() => {studio}.performance")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        attach_hooks(
            mobile,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(mobile)
        for candidate_id, directory in CANDIDATES.items():
            mobile.evaluate(
                f"() => {studio}.setReflectionCandidate('{candidate_id}')"
            )
            canvas_shot(
                mobile,
                EVIDENCE / directory / "mobile.png",
            )
        mobile_snapshot = mobile.evaluate(f"() => {studio}.interaction")
        browser.close()

    editorial = candidate_metrics["editorial"]
    baseline_overexposed = baseline_metrics["centralOverexposedPixels"]
    editorial_overexposed = editorial["frame"][
        "centralOverexposedPixels"
    ]
    central_reduction = (
        1 - editorial_overexposed / baseline_overexposed
        if baseline_overexposed
        else 1
    )
    center_hot_bands = [
        theme_id
        for theme_id, metrics in editorial["bands"].items()
        if metrics["centralOverexposedPixels"] > 8
    ]
    checks = {
        "geometry_signature_unchanged": (
            canonical_geometry_signature(geometry)
            == geometry["geometryVersionSignature"]
            == lock["geometryVersionSignature"]
        ),
        "geometry_locked": lock["locked"],
        "band_dimensions_unchanged": (
            band_dimensions["desktopWidth"] == 0.18
            and band_dimensions["mobileWidth"] == 0.16
            and band_dimensions["thickness"] == 0.02
            and band_dimensions["bevelWidth"] == 0.0024
        ),
        "theme_base_colors_unchanged": base_colors == EXPECTED_COLORS,
        "global_lighting_baseline_locked": (
            lighting["exposure"]["desktop"] == 0.98
            and lighting["ambient"]["desktop"] == 0.22
            and lighting["toneMapping"] == "AgX"
            and 0.35 <= lighting["fillToKeyRatio"] <= 0.45
            and lighting["sharedPmremSoftboxCount"] == 1
        ),
        "shared_pmrem_with_material_rotation": (
            editorial_snapshot["reflectionArtDirection"]["sharedPmrem"]
            and editorial_snapshot["reflectionArtDirection"][
                "environmentCopies"
            ]
            == 1
            and editorial_snapshot["reflectionArtDirection"][
                "implementation"
            ]
            == "material-envMapRotation-plus-physical-specular-shaping"
        ),
        "central_overexposure_reduced_50_percent": central_reduction >= 0.5,
        "maximum_two_center_hot_bands": len(center_hot_bands) <= 2,
        "each_band_has_long_highlight": all(
            metrics["longestHighlightFraction"] >= 0.035
            for metrics in editorial["bands"].values()
        ),
        "outer_constellation_readable": (
            editorial["bands"]["constellation"]["readablePixelRatio"] >= 0.55
            and editorial["bands"]["constellation"]["medianLuminance"]
            >= 0.055
        ),
        "no_large_pure_white_area": (
            editorial["frame"]["globalOverexposureRatio"] <= 0.012
        ),
        "self_core_not_overexposed": (
            editorial["core"]["maximumLuminance"] < 0.9
        ),
        "rotation_is_continuous": (
            rotation["frameCount"] == 61
            and rotation["equivalentDurationSeconds"] == 60
            and rotation["seamLuminanceDelta"] < 0.002
            and rotation["seamOverexposureDelta"] < 0.002
            and rotation["maximumStepLuminanceDelta"] < 0.08
        ),
        "no_emissive_bloom_or_hard_ceiling": (
            not editorial_snapshot["reflectionArtDirection"][
                "emissiveReflection"
            ]
            and not editorial_snapshot["reflectionArtDirection"]["bloom"]
            and not editorial_snapshot["reflectionArtDirection"][
                "hardHighlightCeiling"
            ]
            and all(
                visual["emissiveIntensity"] == 0
                for visual in editorial_snapshot["visuals"].values()
            )
        ),
        "desktop_and_mobile_render": (
            mobile_snapshot["mobileQualityPreview"] is True
            and all(
                (EVIDENCE / directory / "front.png").exists()
                and (EVIDENCE / directory / "mobile.png").exists()
                for directory in CANDIDATES.values()
            )
        ),
        "candidate_previews_created": all(preview_status.values()),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    status = "PASS" if all(checks.values()) else "PARTIAL"
    result = {
        "status": status,
        "checks": checks,
        "geometrySignature": geometry["geometryVersionSignature"],
        "bandDimensions": band_dimensions,
        "baseColors": base_colors,
        "lightingBaseline": lighting,
        "reflection": editorial_snapshot["reflectionArtDirection"],
        "baselineMetrics": baseline_metrics,
        "candidateMetrics": candidate_metrics,
        "centralOverexposureReduction": central_reduction,
        "centerHotBands": center_hot_bands,
        "rotation60SecondEquivalent": rotation,
        "previewStatus": preview_status,
        "performance": performance,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "evidence": [
            str(path.relative_to(ROOT))
            for path in sorted(EVIDENCE.rglob("*"))
            if path.is_file()
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

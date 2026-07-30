from __future__ import annotations

import base64
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Browser, Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "pantheon_pmrem_reflection_field_v1"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits"
    "&geometryVersion=v1.1"
    "&freezeOrbit=1"
    "&capture=1"
)
CANDIDATES = ("current", "candidate-a", "candidate-b")
VIEWS = {
    "desktop-front": "front",
    "desktop-front-left": "front-left",
    "desktop-side": "right",
}
THEME_IDS = (
    "constellation",
    "tarot",
    "mbti",
    "human-design",
    "ziwei-bazi",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def wait_three_frames(page: Page) -> None:
    page.evaluate(
        """async () => {
          await new Promise((resolve) => {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                requestAnimationFrame(resolve);
              });
            });
          });
          window.__PANTHEON_STAR_ORBITS__.render();
        }"""
    )


def prepare_fixed_state(page: Page) -> None:
    page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.setPaused(true);
          studio.setOrbitMotionPaused(true);
          studio.setReducedMotionPreview(true);
          studio.clearSelection();
          studio.setHoveredTheme(null);
          studio.setMonochrome(false);
          studio.setProductLighting({ mode: "full" });
          studio.setDebugDisplay({
            validationMode: "material-v3",
            flatMaterial: false,
            showBand: true,
            showCore: true,
            markOpacity: 1
          });
          studio.orbits.rotation.set(
            window.THREE?.MathUtils?.degToRad?.(-8) ?? -0.13962634015954636,
            0,
            0
          );
          studio.setView("front");
          studio.render();
        }"""
    )
    wait_three_frames(page)


def runtime_metadata(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          const bands = [];
          studio.orbits.traverse((node) => {
            if (node.name?.startsWith("PantheonBand.")) bands.push(node);
          });
          const firstMaterials = Array.isArray(bands[0]?.material)
            ? bands[0].material
            : [bands[0]?.material];
          const core = studio.orbits.getObjectByName("SelfCore");
          const selfCore = studio.selfCoreEffect;
          return {
            timestamp: new Date().toISOString(),
            frameIndex: studio.frameIndex,
            geometrySignature: studio.geometryLock.signature,
            toneMapping: studio.renderer.toneMapping,
            exposure: studio.renderer.toneMappingExposure,
            reflectionField: studio.reflectionField,
            sceneEnvironmentUuid: studio.scene.environment?.uuid ?? null,
            bandEnvironment: {
              topBottom: firstMaterials[0]?.envMapIntensity ?? null,
              bevel: firstMaterials[1]?.envMapIntensity ?? null,
              edge: firstMaterials[2]?.envMapIntensity ?? null,
              allUseScenePmrem: bands.every((band) => {
                const materials = Array.isArray(band.material)
                  ? band.material
                  : [band.material];
                return materials.every(
                  (material) =>
                    material?.envMap === studio.scene.environment
                );
              })
            },
            selfCore: {
              snapshot: selfCore,
              materialEnvMapUuid: core.material.envMap?.uuid ?? null,
              matchesSceneEnvironment:
                core.material.envMap === studio.scene.environment,
              materialEnvMapIntensity: core.material.envMapIntensity,
              gpuEnvMapIntensity: selfCore.gpuEnvMapIntensity
            },
            productLighting: studio.productLighting,
            camera: {
              position: studio.camera.position.toArray(),
              fov: studio.camera.fov
            },
            renderer: {
              size: {
                width: studio.renderer.domElement.width,
                height: studio.renderer.domElement.height
              },
              dpr: studio.renderer.getPixelRatio()
            }
          };
        }"""
    )


def measure_luminance(page: Page) -> dict:
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
          const oldBackground = scene.background;
          const oldClear = renderer.getClearColor(
            core.material.color.clone()
          ).clone();
          const oldAlpha = renderer.getClearAlpha();
          const bandVisibility = bands.map((node) => node.visible);
          const runeVisibility = runes.map((node) => node.visible);
          const coreVisible = core.visible;
          const toLinear = (value) =>
            value <= 0.04045
              ? value / 12.92
              : Math.pow((value + 0.055) / 1.055, 2.4);
          const read = () => {
            renderer.render(scene, camera);
            const pixels = new Uint8Array(width * height * 4);
            gl.readPixels(
              0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels
            );
            return pixels;
          };
          const summarize = (pixels) => {
            const values = [];
            for (let offset = 0; offset < pixels.length; offset += 4) {
              const r = pixels[offset] / 255;
              const g = pixels[offset + 1] / 255;
              const b = pixels[offset + 2] / 255;
              if (Math.max(r, g, b) <= 1 / 255) continue;
              values.push(
                0.2126 * toLinear(r) +
                0.7152 * toLinear(g) +
                0.0722 * toLinear(b)
              );
            }
            values.sort((a, b) => a - b);
            const percentile = (fraction) =>
              values[
                Math.min(
                  values.length - 1,
                  Math.floor((values.length - 1) * fraction)
                )
              ] || 0;
            return {
              pixels: values.length,
              average:
                values.reduce((sum, value) => sum + value, 0) /
                Math.max(1, values.length),
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
          scene.background = null;
          renderer.setClearColor(0x000000, 1);
          runes.forEach((node) => { node.visible = false; });
          core.visible = false;
          bands.forEach((node) => { node.visible = true; });
          const combinedBands = summarize(read());
          const themes = {};
          Object.entries(themeOrbit).forEach(([themeId, orbitId]) => {
            bands.forEach((node) => {
              node.visible = node.name === `PantheonBand.${orbitId}`;
            });
            themes[themeId] = summarize(read());
          });
          bands.forEach((node) => { node.visible = false; });
          core.visible = true;
          const selfCore = summarize(read());
          bands.forEach((node, index) => {
            node.visible = bandVisibility[index];
          });
          runes.forEach((node, index) => {
            node.visible = runeVisibility[index];
          });
          core.visible = coreVisible;
          scene.background = oldBackground;
          renderer.setClearColor(oldClear, oldAlpha);
          renderer.render(scene, camera);
          const averages = Object.values(themes).map(
            (metrics) => metrics.average
          );
          return {
            width,
            height,
            combinedBands,
            themes,
            brightestToDarkestAverageRatio:
              Math.max(...averages) /
              Math.max(1e-9, Math.min(...averages)),
            selfCore
          };
        }"""
    )


def save_source_preview(page: Page, candidate_dir: Path) -> Path:
    payload = page.evaluate(
        """() => ({
          dataUrl:
            window.__PANTHEON_STAR_ORBITS__
              .getReflectionFieldSourceDataUrl(),
          field: window.__PANTHEON_STAR_ORBITS__.reflectionField
        })"""
    )
    encoded = payload["dataUrl"].split(",", 1)[1]
    image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for card in payload["field"]["cards"]:
        if card["type"] == "rect":
            box = (
                card["x"],
                card["y"],
                card["x"] + card["width"],
                card["y"] + card["height"],
            )
        else:
            box = (
                card["centerX"] - card["outerRadius"],
                card["centerY"] - card["outerRadius"],
                card["centerX"] + card["outerRadius"],
                card["centerY"] + card["outerRadius"],
            )
        draw.rectangle(box, outline="#ffcc55", width=1)
        text_box = draw.textbbox((0, 0), card["label"], font=font)
        label_width = text_box[2] - text_box[0] + 4
        label_height = text_box[3] - text_box[1] + 3
        label_y = max(0, int(box[1]) - label_height)
        draw.rectangle(
            (int(box[0]), label_y, int(box[0]) + label_width, label_y + label_height),
            fill="#101820",
        )
        draw.text(
            (int(box[0]) + 2, label_y + 1),
            card["label"],
            fill="#ffcc55",
            font=font,
        )
    draw.rectangle((0, 238, 120, 255), fill="#101820")
    draw.text(
        (4, 242),
        f"Base {payload['field']['baseColor']}",
        fill="#ffffff",
        font=font,
    )
    target = candidate_dir / "pmrem-source-preview.png"
    image.save(target)
    return target


def crop_core(source: Path, target: Path) -> None:
    image = Image.open(source).convert("RGB")
    width, height = image.size
    size = min(width, height) // 3
    left = (width - size) // 2
    top = (height - size) // 2
    image.crop((left, top, left + size, top + size)).resize(
        (640, 640), Image.Resampling.LANCZOS
    ).save(target)


def make_contact_sheet(
    paths: list[Path],
    labels: list[str],
    target: Path,
    columns: int,
) -> None:
    images = [Image.open(path).convert("RGB") for path in paths]
    thumb_width = min(image.width for image in images)
    thumb_height = min(image.height for image in images)
    rows = math.ceil(len(images) / columns)
    header = 28
    sheet = Image.new(
        "RGB",
        (thumb_width * columns, (thumb_height + header) * rows),
        "#111820",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (image, label) in enumerate(zip(images, labels)):
        column = index % columns
        row = index // columns
        image = image.resize(
            (thumb_width, thumb_height), Image.Resampling.LANCZOS
        )
        x = column * thumb_width
        y = row * (thumb_height + header)
        sheet.paste(image, (x, y + header))
        draw.text((x + 8, y + 8), label, fill="#f6d28b", font=font)
    sheet.save(target)


def capture_rotation(
    page: Page,
    canvas,
    candidate_dir: Path,
    label: str,
) -> dict:
    paths: list[Path] = []
    hashes: list[str] = []
    for index in range(12):
        page.evaluate(
            """(angle) => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.orbits.rotation.y = angle;
              studio.render();
            }""",
            index * math.tau / 12,
        )
        wait_three_frames(page)
        path = candidate_dir / f"rotation-{label}-{index:02d}.png"
        canvas.screenshot(path=str(path), timeout=20_000)
        paths.append(path)
        hashes.append(sha256(path))
    target = candidate_dir / f"rotation-{label}-contact-sheet.png"
    make_contact_sheet(
        paths,
        [f"{index * 30}°" for index in range(12)],
        target,
        4,
    )
    page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.orbits.rotation.y = 0;
          studio.render();
        }"""
    )
    wait_three_frames(page)
    return {
        "frames": len(paths),
        "distinctFrames": len(set(hashes)),
        "allFramesDistinct": len(set(hashes)) == len(paths),
        "contactSheet": str(target.relative_to(ROOT)),
        "contactSheetSha256": sha256(target),
    }


def open_candidate_page(
    browser: Browser,
    candidate: str,
    viewport: dict[str, int],
    mobile: bool,
    error_buckets: tuple[list[str], list[str], list[str]],
) -> Page:
    page = browser.new_page(
        viewport=viewport,
        device_scale_factor=1,
        is_mobile=mobile,
    )
    attach_evidence_hooks(page, *error_buckets)
    response = page.goto(
        f"{BASE_URL}&pmremCandidate={candidate}",
        wait_until="networkidle",
    )
    if response is None or not response.ok:
        raise RuntimeError(f"{candidate} 頁面載入失敗")
    page.wait_for_function(
        "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
    )
    prepare_fixed_state(page)
    return page


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    report: dict = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "NEEDS WORK",
        "candidates": {},
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
    }
    error_buckets = (console_errors, page_errors, request_failures)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=(
                "/Applications/Google Chrome.app/Contents/MacOS/"
                "Google Chrome"
            ),
        )
        for candidate in CANDIDATES:
            candidate_dir = OUTPUT / candidate
            candidate_dir.mkdir(parents=True, exist_ok=True)
            page = open_candidate_page(
                browser,
                candidate,
                {"width": 1280, "height": 720},
                False,
                error_buckets,
            )
            canvas = page.locator("[data-pantheon-star-orbits] canvas")
            captures: dict[str, dict] = {}
            for filename, view in VIEWS.items():
                page.evaluate(
                    """(view) => {
                      const studio = window.__PANTHEON_STAR_ORBITS__;
                      studio.orbits.rotation.y = 0;
                      studio.setView(view);
                      studio.render();
                    }""",
                    view,
                )
                wait_three_frames(page)
                target = candidate_dir / f"{filename}.png"
                canvas.screenshot(path=str(target), timeout=20_000)
                captures[filename] = {
                    "path": str(target.relative_to(ROOT)),
                    "sha256": sha256(target),
                    "frameIndex": page.evaluate(
                        "() => window.__PANTHEON_STAR_ORBITS__.frameIndex"
                    ),
                }
            page.evaluate(
                """() => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  studio.orbits.traverse((node) => {
                    if (
                      node.name?.startsWith("PantheonBand.") ||
                      node.name?.startsWith("RuneFlow.")
                    ) {
                      node.userData.pmremCaptureVisible = node.visible;
                      node.visible = false;
                    }
                  });
                  studio.render();
                }"""
            )
            wait_three_frames(page)
            core_isolation = candidate_dir / "self-core-isolation.png"
            canvas.screenshot(path=str(core_isolation), timeout=20_000)
            crop_core(
                core_isolation,
                candidate_dir / "self-core-close-up.png",
            )
            core_isolation.unlink()
            page.evaluate(
                """() => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  studio.orbits.traverse((node) => {
                    if (
                      node.name?.startsWith("PantheonBand.") ||
                      node.name?.startsWith("RuneFlow.")
                    ) {
                      node.visible =
                        node.userData.pmremCaptureVisible ?? true;
                      delete node.userData.pmremCaptureVisible;
                    }
                  });
                  studio.render();
                }"""
            )
            wait_three_frames(page)
            captures["self-core-close-up"] = {
                "path": str(
                    (candidate_dir / "self-core-close-up.png").relative_to(ROOT)
                ),
                "sha256": sha256(candidate_dir / "self-core-close-up.png"),
            }
            page.evaluate(
                """() => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  studio.setView("front");
                  studio.setDebugDisplay({ markOpacity: 0 });
                  studio.render();
                }"""
            )
            wait_three_frames(page)
            no_marks = candidate_dir / "no-surface-marks.png"
            canvas.screenshot(path=str(no_marks), timeout=20_000)
            captures["no-surface-marks"] = {
                "path": str(no_marks.relative_to(ROOT)),
                "sha256": sha256(no_marks),
            }
            page.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setDebugDisplay({ markOpacity: 1 })"
            )
            wait_three_frames(page)
            source_preview = save_source_preview(page, candidate_dir)
            captures["pmrem-source-preview"] = {
                "path": str(source_preview.relative_to(ROOT)),
                "sha256": sha256(source_preview),
            }
            metadata = runtime_metadata(page)
            measurements = measure_luminance(page)
            rotation_desktop = capture_rotation(
                page, canvas, candidate_dir, "desktop"
            )
            page.close()

            mobile_page = open_candidate_page(
                browser,
                candidate,
                {"width": 390, "height": 844},
                True,
                error_buckets,
            )
            mobile_canvas = mobile_page.locator(
                "[data-pantheon-star-orbits] canvas"
            )
            mobile_target = candidate_dir / "mobile-front.png"
            mobile_canvas.screenshot(
                path=str(mobile_target), timeout=20_000
            )
            captures["mobile-front"] = {
                "path": str(mobile_target.relative_to(ROOT)),
                "sha256": sha256(mobile_target),
            }
            rotation_mobile = capture_rotation(
                mobile_page, mobile_canvas, candidate_dir, "mobile"
            )
            mobile_metadata = runtime_metadata(mobile_page)
            mobile_page.close()

            report["candidates"][candidate] = {
                "captures": captures,
                "metadata": metadata,
                "mobileMetadata": mobile_metadata,
                "measurements": measurements,
                "safety": {
                    "bandOver095Below1Percent":
                        measurements["combinedBands"]["over095Ratio"] < 0.01,
                    "bandUnder008AtMost25Percent":
                        measurements["combinedBands"]["under008Ratio"] <= 0.25,
                },
                "rotation": {
                    "desktop": rotation_desktop,
                    "mobile": rotation_mobile,
                },
            }
        browser.close()

    comparison_dir = OUTPUT / "comparisons"
    comparison_dir.mkdir(exist_ok=True)
    for filename in (
        "desktop-front",
        "desktop-front-left",
        "desktop-side",
        "mobile-front",
        "self-core-close-up",
        "no-surface-marks",
    ):
        paths = [
            OUTPUT / candidate / f"{filename}.png"
            for candidate in CANDIDATES
        ]
        target = comparison_dir / f"{filename}-current-a-b.png"
        make_contact_sheet(
            paths,
            ["Current", "Candidate A", "Candidate B"],
            target,
            3,
        )
        report.setdefault("comparisons", {})[filename] = {
            "path": str(target.relative_to(ROOT)),
            "sha256": sha256(target),
        }

    front_hashes = [
        report["candidates"][candidate]["captures"]["desktop-front"][
            "sha256"
        ]
        for candidate in CANDIDATES
    ]
    report["fixedCaptureHashesDistinct"] = (
        len(set(front_hashes)) == len(front_hashes)
    )
    report["runtimeContractFix"] = {
        candidate: {
            "materialEnvMapIntensity":
                report["candidates"][candidate]["metadata"]["selfCore"][
                    "materialEnvMapIntensity"
                ],
            "gpuEnvMapIntensity":
                report["candidates"][candidate]["metadata"]["selfCore"][
                    "gpuEnvMapIntensity"
                ],
            "matchesSceneEnvironment":
                report["candidates"][candidate]["metadata"]["selfCore"][
                    "matchesSceneEnvironment"
                ],
        }
        for candidate in CANDIDATES
    }
    report["captureIntegrity"] = (
        report["fixedCaptureHashesDistinct"]
        and not console_errors
        and not page_errors
        and not request_failures
    )
    (OUTPUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["captureIntegrity"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

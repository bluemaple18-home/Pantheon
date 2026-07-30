from __future__ import annotations

import hashlib
import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "pantheon_material_v2" / "evidence"
BASE_URL = (
    "http://127.0.0.1:5174/"
    "?prototype=pantheon-star-orbits&capture=1&view=front"
)
VIEWS = ("front", "front-left", "front-right", "right", "back")
CANDIDATES = {
    "A": {"inclination": 38, "azimuth": 62, "roll": -25, "scale": 1.0},
    "B": {"inclination": 40, "azimuth": 50, "roll": -20, "scale": 1.0},
    "C": {"inclination": 39, "azimuth": 66, "roll": -39, "scale": 1.0},
    "D": {"inclination": 39, "azimuth": 66, "roll": -39, "scale": 0.98},
    "E": {"inclination": 39, "azimuth": 58, "roll": -31, "scale": 0.97},
}
DESKTOP_WIDTHS = (0.050, 0.054, 0.058, 0.062)
MOBILE_WIDTHS = (0.044, 0.048, 0.052, 0.056)

PROJECTION_ANALYSIS = """() => {
  const studio = window.__PANTHEON_STAR_ORBITS__;
  const root = studio.orbits;
  const camera = studio.camera;
  root.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);
  const samples = studio.getCenterlineSamples(360);
  const projected = Object.fromEntries(
    Object.entries(samples).map(([id, points]) => [
      id,
      points.map(([x, y, z]) => {
        const worldPoint = camera.position.clone().set(x, y, z)
          .applyMatrix4(root.matrixWorld);
        const cameraPoint = worldPoint.clone()
          .applyMatrix4(camera.matrixWorldInverse);
        const ndc = worldPoint.clone().project(camera);
        return {x: ndc.x, y: ndc.y, depth: -cameraPoint.z};
      })
    ])
  );
  const constellation = projected.Constellation;
  const sphereRadius = Math.max(
    ...Object.values(projected).flat()
      .map(point => Math.hypot(point.x, point.y))
  );
  const interiorParticipation = constellation.filter(
    point => Math.hypot(point.x, point.y) <= sphereRadius * 0.75
  ).length / constellation.length;
  const bins = 180;
  const maxima = Object.fromEntries(
    Object.keys(projected).map(id => [id, Array(bins).fill(0)])
  );
  Object.entries(projected).forEach(([id, points]) => {
    points.forEach(point => {
      const angle = Math.atan2(point.y, point.x);
      const bin = Math.min(
        bins - 1,
        Math.floor(((angle + Math.PI) / (Math.PI * 2)) * bins)
      );
      maxima[id][bin] = Math.max(
        maxima[id][bin],
        Math.hypot(point.x, point.y)
      );
    });
  });
  const globalMax = Array.from({length: bins}, (_, bin) =>
    Math.max(...Object.values(maxima).map(values => values[bin]))
  );
  const outerSilhouetteCoverage = maxima.Constellation.filter(
    (value, bin) =>
      globalMax[bin] > 0 && value >= globalMax[bin] * 0.985
  ).length / bins;
  const intersection = (a, b, c, d) => {
    const den =
      (a.x - b.x) * (c.y - d.y) -
      (a.y - b.y) * (c.x - d.x);
    if (Math.abs(den) < 1e-9) return null;
    const detA = a.x * b.y - a.y * b.x;
    const detB = c.x * d.y - c.y * d.x;
    const x =
      (detA * (c.x - d.x) - (a.x - b.x) * detB) / den;
    const y =
      (detA * (c.y - d.y) - (a.y - b.y) * detB) / den;
    const within = (value, first, second) =>
      value >= Math.min(first, second) - 1e-7 &&
      value <= Math.max(first, second) + 1e-7;
    if (
      !within(x, a.x, b.x) || !within(y, a.y, b.y) ||
      !within(x, c.x, d.x) || !within(y, c.y, d.y)
    ) return null;
    const ta = Math.abs(b.x - a.x) > Math.abs(b.y - a.y)
      ? (x - a.x) / (b.x - a.x)
      : (y - a.y) / (b.y - a.y);
    const tb = Math.abs(d.x - c.x) > Math.abs(d.y - c.y)
      ? (x - c.x) / (d.x - c.x)
      : (y - c.y) / (d.y - c.y);
    return {
      x,
      y,
      constellationDepth:
        a.depth + (b.depth - a.depth) * ta,
      otherDepth: c.depth + (d.depth - c.depth) * tb
    };
  };
  const pairs = {};
  let over = 0;
  let under = 0;
  for (const [id, points] of Object.entries(projected)) {
    if (id === "Constellation") continue;
    const hits = [];
    for (let a = 0; a < constellation.length; a += 1) {
      for (let b = 0; b < points.length; b += 1) {
        const hit = intersection(
          constellation[a],
          constellation[(a + 1) % constellation.length],
          points[b],
          points[(b + 1) % points.length]
        );
        if (!hit) continue;
        if (hits.some(
          prior => Math.hypot(prior.x - hit.x, prior.y - hit.y) < 0.003
        )) continue;
        const relation =
          hit.constellationDepth < hit.otherDepth ? "over" : "under";
        if (relation === "over") over += 1;
        else under += 1;
        hits.push({x: hit.x, y: hit.y, relation});
      }
    }
    pairs[id] = hits;
  }
  const visibleCrossingCount = Object.values(pairs)
    .reduce((sum, hits) => sum + hits.length, 0);
  const uniqueOrbitIntersections = Object.values(pairs)
    .filter(hits => hits.length > 0).length;
  const isolationScore =
    outerSilhouetteCoverage * 0.55 +
    Math.max(0, 0.3 - interiorParticipation) * 0.9 +
    0.35 / Math.max(1, visibleCrossingCount) +
    0.18 / Math.max(1, uniqueOrbitIntersections);
  return {
    visibleCrossingCount,
    uniqueOrbitIntersections,
    over,
    under,
    pairs,
    interiorParticipation,
    outerSilhouetteCoverage,
    isolationScore,
    extentRatio: studio.metrics.extentRatio
  };
}"""


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


def open_studio(page: Page, version: str = "v1.1") -> None:
    page.goto(
        f"{BASE_URL}&geometryVersion={version}",
        wait_until="networkidle",
    )
    page.wait_for_function("() => Boolean(window.__PANTHEON_STAR_ORBITS__)")
    page.evaluate(
        """() => {
          const studio = window.__PANTHEON_STAR_ORBITS__;
          studio.setPaused(true);
          studio.clearSelection();
          studio.setMonochrome(false);
          studio.setDebugDisplay({
            validationMode: "material-v2",
            flatMaterial: false,
            bandWidthPreview: null,
            showBand: true,
            showCore: true
          });
          return studio.settle();
        }"""
    )


def canvas_shot(page: Page, name: str) -> None:
    target = EVIDENCE / name
    force_refresh = name in {
        "15-mobile-idle.png",
        "16-mobile-selected.png",
    }
    if target.exists() and not force_refresh:
        return
    page.locator("[data-pantheon-star-orbits] canvas").screenshot(
        path=str(target),
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


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    v1 = json.loads(
        (PROTOTYPE / "geometry" / "pantheon-orbits-v1.json").read_text()
    )
    v1_1 = json.loads(
        (PROTOTYPE / "geometry" / "pantheon-orbits-v1.1.json").read_text()
    )
    candidate_report = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        candidates = browser.new_page(viewport={"width": 1280, "height": 900})
        attach_hooks(
            candidates,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(candidates, "v1.0")
        candidates.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setMonochrome(true);
              studio.unlockGeometry("CREATE_GEOMETRY_V1_1");
              return studio.settle();
            }"""
        )
        canvas_shot(candidates, "01-geometry-v1.0-front.png")
        for name, patch in CANDIDATES.items():
            candidates.evaluate(
                """patch => {
                  const studio = window.__PANTHEON_STAR_ORBITS__;
                  const {scale, ...angles} = patch;
                  studio.attemptGeometryMutation("Constellation", angles);
                  studio.orbits.userData.starOrbitRuntime
                    .setOrbitScale("Constellation", scale);
                  return studio.settle();
                }""",
                patch,
            )
            for view in VIEWS:
                candidates.evaluate(
                    "view => window.__PANTHEON_STAR_ORBITS__.setView(view)",
                    view,
                )
                canvas_shot(
                    candidates,
                    f"02-candidate-{name}-{view}.png",
                )
            candidates.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
            )
            candidate_report[name] = {
                "pose": patch,
            }

        desktop = browser.new_page(viewport={"width": 1440, "height": 960})
        attach_hooks(
            desktop,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(desktop)
        lock = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.geometryLock"
        )
        band_metrics = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.bandMetrics"
        )
        interaction = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.interaction"
        )
        projections = {}
        for view in ("front", "front-left", "front-right"):
            desktop.evaluate(
                "view => window.__PANTHEON_STAR_ORBITS__.setView(view)",
                view,
            )
            projections[view] = desktop.evaluate(PROJECTION_ANALYSIS)
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
        )
        core_visibility = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.measureCoreVisibility(44)"
        )

        for width in DESKTOP_WIDTHS:
            desktop.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
            )
            desktop.evaluate(
                """width => window.__PANTHEON_STAR_ORBITS__
                  .setDebugDisplay({bandWidthPreview: width})""",
                width,
            )
            desktop.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.clearSelection()"
            )
            canvas_shot(desktop, f"03-desktop-width-{width:.3f}-idle.png")
            desktop.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.selectTheme('tarot')"
            )
            canvas_shot(
                desktop,
                f"03-desktop-width-{width:.3f}-selected-tarot.png",
            )
            desktop.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(true)"
            )
            canvas_shot(
                desktop,
                f"03-desktop-width-{width:.3f}-monochrome.png",
            )
            desktop.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(false)"
            )
            for view in ("front-left", "right"):
                desktop.evaluate(
                    "view => window.__PANTHEON_STAR_ORBITS__.setView(view)",
                    view,
                )
                canvas_shot(
                    desktop,
                    f"03-desktop-width-{width:.3f}-{view}.png",
                )

        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setView("front");
              studio.setDebugDisplay({bandWidthPreview: null});
              studio.clearSelection();
              return studio.settle();
            }"""
        )
        canvas_shot(desktop, "04-desktop-idle.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.selectTheme('tarot')"
        )
        canvas_shot(desktop, "05-desktop-selected.png")
        desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front-left')"
        )
        canvas_shot(desktop, "06-desktop-front-left.png")
        for mode, name in (
            ("over-under", "07-over-under-debug.png"),
            ("outer-intersections", "08-intersections-debug.png"),
            ("engraving", "09-engraving-only.png"),
            ("emissive", "10-emissive-only.png"),
            ("background-weight", "11-background-weight.png"),
        ):
            desktop.evaluate(
                """mode => window.__PANTHEON_STAR_ORBITS__
                  .setDebugDisplay({validationMode: mode})""",
                mode,
            )
            canvas_shot(desktop, name)
        desktop.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setView("front");
              studio.clearSelection();
              studio.setDebugDisplay({validationMode: "material-v2"});
              return studio.settle();
            }"""
        )
        canvas_shot(desktop, "12-final-material-v2.png")
        desktop.screenshot(
            path=str(EVIDENCE / "13-desktop-ui.png"),
            full_page=True,
        )
        performance = desktop.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.performance"
        )

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        attach_hooks(
            mobile,
            console_errors,
            page_errors,
            request_failures,
        )
        open_studio(mobile)
        for width in MOBILE_WIDTHS:
            mobile.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
            )
            mobile.evaluate(
                """width => window.__PANTHEON_STAR_ORBITS__
                  .setDebugDisplay({bandWidthPreview: width})""",
                width,
            )
            mobile.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.clearSelection()"
            )
            canvas_shot(mobile, f"14-mobile-width-{width:.3f}-idle.png")
            mobile.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.selectTheme('tarot')"
            )
            canvas_shot(
                mobile,
                f"14-mobile-width-{width:.3f}-selected-tarot.png",
            )
            mobile.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(true)"
            )
            canvas_shot(
                mobile,
                f"14-mobile-width-{width:.3f}-monochrome.png",
            )
            mobile.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setMonochrome(false)"
            )
            for view in ("front-left", "right"):
                mobile.evaluate(
                    "view => window.__PANTHEON_STAR_ORBITS__.setView(view)",
                    view,
                )
                canvas_shot(
                    mobile,
                    f"14-mobile-width-{width:.3f}-{view}.png",
                )
        mobile.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.setView("front");
              studio.setDebugDisplay({
                bandWidthPreview: null,
                validationMode: "material-v2"
              });
              studio.clearSelection();
              return studio.settle();
            }"""
        )
        canvas_shot(mobile, "15-mobile-idle.png")
        mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.selectTheme('tarot')"
        )
        canvas_shot(mobile, "16-mobile-selected.png")
        mobile.screenshot(
            path=str(EVIDENCE / "17-mobile-ui.png"),
            full_page=True,
        )
        mobile_interaction = mobile.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.interaction"
        )
        browser.close()

    unchanged_fields = (
        "id",
        "position",
        "semiMajorAxis",
        "semiMinorAxis",
        "phase",
    )
    other_fields = unchanged_fields + (
        "scale",
        "inclination",
        "azimuth",
        "roll",
        "normal",
        "quaternion",
    )
    checks = {
        "geometry_v1_preserved": (
            v1["centerlineSignature"]
            == "sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008"
        ),
        "geometry_v1_1_signature_valid": (
            canonical_version_signature(v1_1)
            == v1_1["geometryVersionSignature"]
        ),
        "only_constellation_pose_changed": (
            all(
                v1["orbits"][0][field] == v1_1["orbits"][0][field]
                for field in unchanged_fields
            )
            and all(
                v1["orbits"][index][field]
                == v1_1["orbits"][index][field]
                for index in range(1, 5)
                for field in other_fields
            )
        ),
        "active_geometry_v1_1_locked": (
            lock["version"] == "Geometry v1.1 — LOCKED"
            and lock["locked"]
            and lock["geometryVersionSignature"]
            == v1_1["geometryVersionSignature"]
        ),
        "extent_ratio": projections["front"]["extentRatio"] <= 1.10,
        "front_crossings": (
            projections["front"]["visibleCrossingCount"] >= 3
            and projections["front"]["uniqueOrbitIntersections"] >= 2
        ),
        "front_left_crossings": (
            projections["front-left"]["visibleCrossingCount"] >= 2
        ),
        "front_right_crossings": (
            projections["front-right"]["visibleCrossingCount"] >= 2
        ),
        "over_under_alternation": (
            projections["front"]["over"] >= 1
            and projections["front"]["under"] >= 1
        ),
        "outer_silhouette_coverage": (
            0.55
            <= projections["front"]["outerSilhouetteCoverage"]
            <= 0.72
        ),
        "interior_participation": (
            0.25
            <= projections["front"]["interiorParticipation"]
            <= 0.40
        ),
        "band_dimensions": (
            interaction["bandDimensions"]["desktopWidth"] == 0.056
            and interaction["bandDimensions"]["mobileWidth"] == 0.05
            and interaction["bandDimensions"]["thickness"] == 0.0065
            and interaction["bandDimensions"]["bevelWidth"] == 0.0024
            and band_metrics["bevelSegments"] == 2
        ),
        "width_invariant": all(
            visual["bandWidth"] == 0.056
            for visual in interaction["visuals"].values()
        )
        and all(
            visual["bandWidth"] == 0.05
            for visual in mobile_interaction["visuals"].values()
        ),
        "surface_marks_subtracted": (
            interaction["surfaceMarks"]["reductionFromV1"] >= 0.70
            and interaction["surfaceMarks"]["idleCoverage"] <= 0.12
            and interaction["surfaceMarks"]["selectedCoverage"] <= 0.25
            and interaction["surfaceMarks"]["maximumEmissive"] <= 0.10
            and not interaction["surfaceMarks"]["wholeTextureTranslation"]
        ),
        "background_band_visible": (
            interaction["backgroundMinimumBrightness"] >= 0.65
        ),
        "frame_stable": all(
            metric["frameFlipCount"] == 0
            and metric["seamAlignment"] > 0.999
            and metric["seamNormalDot"] > 0.999
            and metric["degenerateTriangleCount"] == 0
            for metric in band_metrics["regular"]
        ),
        "self_core_visibility": (
            0.45 <= core_visibility["visibleRatio"] <= 0.75
        ),
        "mobile_quality": (
            mobile_interaction["mobileQualityPreview"]
            and performance["shadows"] is False
        ),
        "no_console_errors": not console_errors,
        "no_page_errors": not page_errors,
        "no_request_failures": not request_failures,
    }
    status = "PASS" if all(checks.values()) else "PARTIAL"
    result = {
        "status": status,
        "checks": checks,
        "geometry": {
            "v1Signature": v1["centerlineSignature"],
            "v1_1Signature": v1_1["geometryVersionSignature"],
            "originalConstellation": {
                key: v1["orbits"][0][key]
                for key in ("inclination", "azimuth", "roll", "scale")
            },
            "finalConstellation": {
                key: v1_1["orbits"][0][key]
                for key in ("inclination", "azimuth", "roll", "scale")
            },
            "candidates": candidate_report,
            "finalViews": projections,
        },
        "band": {
            "desktopWidth": 0.056,
            "mobileWidth": 0.05,
            "thickness": 0.0065,
            "bevelWidth": 0.0024,
            "bevelSegments": 2,
            "coreVisibility": core_visibility,
        },
        "material": interaction["surfaceMarks"],
        "performance": performance,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "evidence": [
            str(path.relative_to(ROOT))
            for path in sorted(EVIDENCE.glob("*.png"))
        ],
    }
    (ROOT / "artifacts" / "pantheon_material_v2" / "acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 2)


if __name__ == "__main__":
    main()

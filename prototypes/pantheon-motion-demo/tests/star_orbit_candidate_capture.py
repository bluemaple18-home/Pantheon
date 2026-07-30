from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "artifacts" / "pantheon_star_orbits" / "final_lock"
BASE_URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits&capture=1&view=front-left"
)

CANDIDATES = {
    "candidate-a": {
        "Constellation": {"inclination": 33},
        "MBTI": {"roll": 45.6},
        "ZiweiBazi": {"roll": 176.2},
    },
    "candidate-b": {
        "Constellation": {"inclination": 34, "azimuth": 62},
        "MBTI": {"roll": 47.6},
        "ZiweiBazi": {"roll": 174.2},
    },
    "candidate-c": {
        "Constellation": {
            "inclination": 32,
            "azimuth": 58,
            "roll": -31,
        },
        "MBTI": {"roll": 49.6, "azimuth": 335},
        "ZiweiBazi": {"roll": 172.2},
    },
}

PROJECTION_ANALYSIS = """() => {
  const studio = window.__PANTHEON_STAR_ORBITS__;
  const samples = studio.getCenterlineSamples(360);
  const camera = studio.camera;
  camera.updateMatrixWorld(true);
  const projected = Object.fromEntries(
    Object.entries(samples).map(([id, points]) => [
      id,
      points.map(([x, y, z]) => {
        const point = camera.position.clone().set(x, y, z).project(camera);
        return [point.x, point.y];
      }),
    ])
  );
  const bins = 180;
  const maxima = Object.fromEntries(
    Object.keys(projected).map(id => [id, Array(bins).fill(0)])
  );
  Object.entries(projected).forEach(([id, points]) => {
    points.forEach(([x, y]) => {
      const angle = Math.atan2(y, x);
      const bin = Math.min(
        bins - 1,
        Math.floor(((angle + Math.PI) / (Math.PI * 2)) * bins)
      );
      maxima[id][bin] = Math.max(maxima[id][bin], Math.hypot(x, y));
    });
  });
  const globalMax = Array.from({ length: bins }, (_, bin) =>
    Math.max(...Object.values(maxima).map(values => values[bin]))
  );
  const outerCoverage = Object.fromEntries(
    Object.entries(maxima).map(([id, values]) => [
      id,
      values.filter(
        (value, bin) =>
          globalMax[bin] > 0 && value >= globalMax[bin] * 0.985
      ).length / bins,
    ])
  );

  const cross = (a, b, c, d) => {
    const denominator =
      (a[0] - b[0]) * (c[1] - d[1]) -
      (a[1] - b[1]) * (c[0] - d[0]);
    if (Math.abs(denominator) < 1e-9) return null;
    const determinantA = a[0] * b[1] - a[1] * b[0];
    const determinantB = c[0] * d[1] - c[1] * d[0];
    const x =
      (determinantA * (c[0] - d[0]) -
        (a[0] - b[0]) * determinantB) / denominator;
    const y =
      (determinantA * (c[1] - d[1]) -
        (a[1] - b[1]) * determinantB) / denominator;
    const within = (value, first, second) =>
      value >= Math.min(first, second) - 1e-7 &&
      value <= Math.max(first, second) + 1e-7;
    return (
      within(x, a[0], b[0]) &&
      within(y, a[1], b[1]) &&
      within(x, c[0], d[0]) &&
      within(y, c[1], d[1])
    ) ? [x, y] : null;
  };
  const ids = Object.keys(projected);
  const pairCrossings = {};
  for (let first = 0; first < ids.length; first += 1) {
    for (let second = first + 1; second < ids.length; second += 1) {
      const firstPoints = projected[ids[first]];
      const secondPoints = projected[ids[second]];
      const intersections = [];
      for (let a = 0; a < firstPoints.length; a += 1) {
        const aNext = (a + 1) % firstPoints.length;
        for (let b = 0; b < secondPoints.length; b += 1) {
          const bNext = (b + 1) % secondPoints.length;
          const point = cross(
            firstPoints[a],
            firstPoints[aNext],
            secondPoints[b],
            secondPoints[bNext]
          );
          if (point) intersections.push(point);
        }
      }
      pairCrossings[`${ids[first]}:${ids[second]}`] = intersections.map(
        ([x, y]) => Math.hypot(x, y)
      );
    }
  }
  return { outerCoverage, pairCrossings };
}"""


def apply_candidate(page, patches: dict[str, dict[str, float]]) -> None:
    page.evaluate("() => window.__PANTHEON_STAR_ORBITS__.resetOrbitAngles()")
    for orbit_id, patch in patches.items():
        page.evaluate(
            """([id, values]) =>
              window.__PANTHEON_STAR_ORBITS__.updateOrbitAngles(id, values)
            """,
            [orbit_id, patch],
        )


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
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
        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        canvas = page.locator("[data-pantheon-star-orbits] canvas")

        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
        )
        baseline_front = page.evaluate(PROJECTION_ANALYSIS)
        canvas.screenshot(path=str(EVIDENCE / "baseline-front.png"))
        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front-left')"
        )
        baseline_front_left = page.evaluate(PROJECTION_ANALYSIS)
        canvas.screenshot(path=str(EVIDENCE / "baseline-front-left.png"))

        candidates: dict[str, dict] = {}
        for name, patches in CANDIDATES.items():
            apply_candidate(page, patches)
            page.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setView('front-left')"
            )
            front_left = page.evaluate(PROJECTION_ANALYSIS)
            canvas.screenshot(path=str(EVIDENCE / f"{name}-front-left.png"))
            page.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
            )
            front = page.evaluate(PROJECTION_ANALYSIS)
            canvas.screenshot(path=str(EVIDENCE / f"{name}-front.png"))
            candidates[name] = {
                "patches": patches,
                "front": front,
                "frontLeft": front_left,
                "configs": page.evaluate(
                    "() => window.__PANTHEON_STAR_ORBITS__.configs"
                ),
            }

        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.resetOrbitAngles()"
        )
        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.setView('front')"
        )
        core_sizes = {}
        for radius in (0.145, 0.140, 0.135):
            page.evaluate(
                "(radius) => window.__PANTHEON_STAR_ORBITS__.setCoreRadius(radius)",
                radius,
            )
            canvas.screenshot(
                path=str(EVIDENCE / f"core-{radius:.3f}.png")
            )
            core_sizes[f"{radius:.3f}"] = page.evaluate(
                "() => window.__PANTHEON_STAR_ORBITS__.metrics.coreRadius"
            )

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(BASE_URL, wait_until="networkidle")
        mobile.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        for radius in (0.145, 0.140, 0.135):
            mobile.evaluate(
                "(value) => window.__PANTHEON_STAR_ORBITS__.setCoreRadius(value)",
                radius,
            )
            mobile.locator(
                "[data-pantheon-star-orbits] canvas"
            ).screenshot(
                path=str(EVIDENCE / f"mobile-core-{radius:.3f}.png")
            )
        browser.close()

    result = {
        "status": (
            "PASS"
            if (
                response is not None
                and response.ok
                and not console_errors
                and not page_errors
                and not request_failures
            )
            else "FAIL"
        ),
        "baseline": {
            "front": baseline_front,
            "frontLeft": baseline_front_left,
        },
        "candidates": candidates,
        "coreSizes": core_sizes,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
    }
    (EVIDENCE / "candidate-analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

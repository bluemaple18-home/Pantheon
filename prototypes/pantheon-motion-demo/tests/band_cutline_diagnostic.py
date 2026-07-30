from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "pantheon_band_cutline"
URL = (
    "http://127.0.0.1:5173/"
    "?prototype=pantheon-star-orbits&geometryVersion=v1.1&capture=1"
)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
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
        page.goto(URL, wait_until="networkidle")
        page.wait_for_function(
            "() => Boolean(window.__PANTHEON_STAR_ORBITS__)"
        )
        page.evaluate(
            """() => {
              const studio = window.__PANTHEON_STAR_ORBITS__;
              studio.selectTheme("human-design");
              studio.setOrbitMotionPaused(true);
              studio.setDebugDisplay({
                flowIntensity: 0,
                validationMode: "material-v3"
              });
            }"""
        )
        page.wait_for_timeout(800)
        canvas = page.locator("[data-pantheon-star-orbits] canvas")
        canvas.screenshot(path=str(OUTPUT / "selected-flow-off.png"))
        page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__"
            ".setDebugDisplay({validationMode: 'normal'})"
        )
        page.wait_for_timeout(120)
        canvas.screenshot(path=str(OUTPUT / "normal-debug.png"))
        geometry = page.evaluate(
            "() => window.__PANTHEON_STAR_ORBITS__.geometryLock"
        )
        browser.close()

    print(
        {
            "geometrySignature": geometry["currentSignature"],
            "consoleErrors": console_errors,
            "pageErrors": page_errors,
            "requestFailures": request_failures,
        }
    )
    if console_errors or page_errors or request_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

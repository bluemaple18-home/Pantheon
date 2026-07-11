import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
URL = "http://127.0.0.1:5173"
VIDEO_ASSET = ROOT / "public" / "pantheon-orb-alpha-v2.webm"
POSTER_ASSET = ROOT / "public" / "pantheon-orb-alpha-poster.webp"
CHROME = os.environ.get(
    "BROWSER_BINARY",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def new_page(browser, viewport, reduced_motion="no-preference"):
    context = browser.new_context(
        viewport=viewport,
        device_scale_factor=1,
        reduced_motion=reduced_motion,
        locale="zh-TW",
    )
    page = context.new_page()
    events = {
        "console": [],
        "pageerror": [],
        "requestfailed": [],
        "http_errors": [],
    }

    # 驗收規範：所有監聽器必須在 goto 前完成註冊。
    page.on(
        "console",
        lambda message: events["console"].append(
            {"type": message.type, "text": message.text}
        )
        if message.type in {"error", "warning"}
        else None,
    )
    page.on("pageerror", lambda error: events["pageerror"].append(str(error)))
    page.on(
        "requestfailed",
        lambda request: events["requestfailed"].append(
            {"url": request.url, "failure": request.failure}
        ),
    )
    page.on(
        "response",
        lambda response: events["http_errors"].append(
            {"url": response.url, "status": response.status}
        )
        if response.status >= 400
        else None,
    )
    return context, page, events


def inspect_page(page):
    return page.evaluate(
        """
        () => {
          const video = document.querySelector('video');
          const poster = document.querySelector('img[src="/pantheon-orb-alpha-poster.webp"]');
          const orbitalField = document.querySelector('[data-orbital-field]');
          const orbitLayers = [...document.querySelectorAll('[data-orbit-layer]')];
          const orbitSignatures = Object.fromEntries(
            orbitLayers.map((layer) => [
              layer.dataset.orbitKind,
              [...new Set(
                [...layer.querySelectorAll('[data-glyph-type]')].map(
                  (glyph) => glyph.dataset.glyphType,
                ),
              )],
            ]),
          );
          const bodyText = document.body.innerText;
          const rects = [...document.querySelectorAll('h1, p, a, video')].map((el) => {
            const rect = el.getBoundingClientRect();
            return {
              tag: el.tagName,
              left: rect.left,
              right: rect.right,
              top: rect.top,
              bottom: rect.bottom,
            };
          });
          return {
            title: document.title,
            tracebackVisible: /Traceback|Unhandled Runtime Error|Internal Server Error/i.test(bodyText),
            viewport: { width: innerWidth, height: innerHeight },
            documentSize: {
              width: document.documentElement.scrollWidth,
              height: document.documentElement.scrollHeight,
            },
            horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
            outOfBounds: rects.filter((rect) => rect.left < -1 || rect.right > innerWidth + 1),
            video: video ? {
              currentSrc: video.currentSrc,
              readyState: video.readyState,
              paused: video.paused,
              duration: video.duration,
              display: getComputedStyle(video).display,
              opacity: getComputedStyle(video).opacity,
            } : null,
            orbitalField: orbitalField ? {
              viewBox: orbitalField.getAttribute('viewBox'),
              trackCount: orbitalField.querySelectorAll('[data-orbit-track]').length,
              radii: [...orbitalField.querySelectorAll('[data-orbit-track]')].map(
                (track) => Number(track.dataset.radius),
              ),
              glyphCount: orbitalField.querySelectorAll('[data-orbit-glyph]').length,
              signatures: orbitSignatures,
              animationNames: orbitLayers.map((layer) => getComputedStyle(layer).animationName),
            } : null,
            posterVisible: Boolean(document.querySelector('img[src="/pantheon-orb-alpha-poster.webp"]')?.offsetParent),
            posterOpacity: poster ? getComputedStyle(poster).opacity : null,
            coreOverlayPresent: Boolean(document.querySelector('[class*="coreLabel"]')),
            heroLinkVisible: Boolean(document.querySelector('.hero-link')?.offsetParent),
          };
        }
        """
    )


def run():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    result = {
        "url": URL,
        "asset_sizes": {
            "video": VIDEO_ASSET.stat().st_size,
            "poster": POSTER_ASSET.stat().st_size,
        },
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=CHROME,
            args=["--disable-background-networking"],
        )

        desktop_context, desktop, desktop_events = new_page(
            browser,
            {"width": 1440, "height": 900},
        )
        desktop.goto(URL, wait_until="networkidle")
        desktop.wait_for_function(
            "() => document.querySelector('video')?.readyState >= 2",
            timeout=15_000,
        )
        video_time_start = desktop.locator("video").evaluate("video => video.currentTime")
        desktop.wait_for_timeout(800)
        video_time_end = desktop.locator("video").evaluate("video => video.currentTime")
        desktop.screenshot(path=EVIDENCE / "desktop.png", full_page=False)
        result["desktop"] = inspect_page(desktop)
        result["desktop"]["videoProgress"] = {
            "start": video_time_start,
            "end": video_time_end,
        }
        desktop.locator(".hero-link").click()
        desktop.wait_for_timeout(500)
        result["desktop"]["architectureReached"] = desktop.evaluate(
            """
            () => {
              const rect = document.querySelector('#architecture').getBoundingClientRect();
              return location.hash === '#architecture' && rect.top < innerHeight;
            }
            """
        )
        result["desktop_events"] = desktop_events
        desktop_context.close()

        mobile_context, mobile, mobile_events = new_page(
            browser,
            {"width": 390, "height": 844},
        )
        mobile.goto(URL, wait_until="networkidle")
        mobile.wait_for_function(
            "() => document.querySelector('video')?.readyState >= 2",
            timeout=15_000,
        )
        mobile.wait_for_timeout(500)
        mobile.screenshot(path=EVIDENCE / "mobile.png", full_page=False)
        result["mobile"] = inspect_page(mobile)
        result["mobile_events"] = mobile_events
        mobile_context.close()

        reduced_context, reduced, reduced_events = new_page(
            browser,
            {"width": 1024, "height": 768},
            reduced_motion="reduce",
        )
        reduced.goto(URL, wait_until="networkidle")
        reduced.wait_for_timeout(300)
        result["reduced_motion"] = inspect_page(reduced)
        result["reduced_motion_events"] = reduced_events
        reduced_context.close()
        browser.close()

    error_groups = [
        result["desktop_events"],
        result["mobile_events"],
        result["reduced_motion_events"],
    ]
    assert all(not group[key] for group in error_groups for key in group), result
    assert not result["desktop"]["tracebackVisible"], result
    assert not result["mobile"]["tracebackVisible"], result
    assert not result["desktop"]["horizontalOverflow"], result
    assert not result["mobile"]["horizontalOverflow"], result
    assert not result["desktop"]["outOfBounds"], result
    assert not result["mobile"]["outOfBounds"], result
    assert result["desktop"]["video"]["readyState"] >= 2, result
    assert result["desktop"]["video"]["currentSrc"].endswith("pantheon-orb-alpha-v2.webm"), result
    assert result["desktop"]["video"]["paused"] is False, result
    assert result["desktop"]["posterOpacity"] == "0", result
    assert result["desktop"]["videoProgress"]["end"] > result["desktop"]["videoProgress"]["start"], result
    assert result["desktop"]["coreOverlayPresent"] is False, result
    assert result["mobile"]["coreOverlayPresent"] is False, result
    assert result["desktop"]["orbitalField"]["viewBox"] == "0 0 720 864", result
    assert result["desktop"]["orbitalField"]["trackCount"] == 3, result
    assert result["desktop"]["orbitalField"]["radii"] == [315.62496, 283.06656, 250.50816], result
    radii = result["desktop"]["orbitalField"]["radii"]
    assert [round(radii[0] - radii[1], 5), round(radii[1] - radii[2], 5)] == [
        32.5584,
        32.5584,
    ], result
    assert result["desktop"]["orbitalField"]["glyphCount"] == 39, result
    signatures = result["desktop"]["orbitalField"]["signatures"]
    assert set(signatures["outer"]).isdisjoint(signatures["middle"]), result
    assert set(signatures["outer"]).isdisjoint(signatures["inner"]), result
    assert set(signatures["middle"]).isdisjoint(signatures["inner"]), result
    assert all(
        name != "none" for name in result["desktop"]["orbitalField"]["animationNames"]
    ), result
    assert all(
        name == "none"
        for name in result["reduced_motion"]["orbitalField"]["animationNames"]
    ), result
    assert result["desktop"]["architectureReached"], result
    assert result["reduced_motion"]["video"] is None, result
    assert result["reduced_motion"]["posterVisible"], result
    assert result["reduced_motion"]["posterOpacity"] == "1", result
    assert result["desktop"]["heroLinkVisible"], result
    assert result["mobile"]["heroLinkVisible"], result
    assert result["asset_sizes"]["video"] < 1_800_000, result
    assert result["asset_sizes"]["poster"] < 100_000, result

    (EVIDENCE / "acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()

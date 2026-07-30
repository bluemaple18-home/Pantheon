from __future__ import annotations

import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "pantheon_motion_img2threejs" / "evidence"
PUBLIC = PROTOTYPE / "public"
BASE_URL = "http://127.0.0.1:5173/?studio=1&capture=1"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def decode_data_url(value: str) -> bytes:
    _, encoded = value.split(",", 1)
    return base64.b64decode(encoded)


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    console: list[dict[str, str]] = []
    page_errors: list[str] = []
    request_failures: list[dict[str, str]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME) if CHROME.exists() else None,
        )
        context = browser.new_context(
            viewport={"width": 720, "height": 864},
            device_scale_factor=1,
        )
        page = context.new_page()

        # Evidence hooks must be registered before navigation.
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
                {"url": request.url, "error": request.failure or "unknown"}
            ),
        )

        response = page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_function("Boolean(window.__PANTHEON_STUDIO__)")

        payload = page.evaluate(
            """async () => {
              const studio = window.__PANTHEON_STUDIO__;
              const canvas = studio.renderer.domElement;
              const fps = 16;
              const duration = studio.loopSeconds;
              const frameDelay = 1000 / fps;
              const mimeCandidates = [
                "video/webm;codecs=vp9",
                "video/webm;codecs=vp8",
                "video/webm",
              ];
              const mimeType = mimeCandidates.find((value) => MediaRecorder.isTypeSupported(value));
              if (!mimeType) throw new Error("No supported WebM MediaRecorder codec");

              studio.setView("front");
              studio.setTime(0);
              studio.setMaterialMode("reference");

              const posterBlob = await new Promise((resolve, reject) => {
                canvas.toBlob(
                  (blob) => blob ? resolve(blob) : reject(new Error("WebP poster encoding failed")),
                  "image/webp",
                  0.92,
                );
              });

              const stream = canvas.captureStream(fps);
              const chunks = [];
              const recorder = new MediaRecorder(stream, {
                mimeType,
                videoBitsPerSecond: 900000,
              });
              recorder.addEventListener("dataavailable", (event) => {
                if (event.data.size > 0) chunks.push(event.data);
              });
              const stopped = new Promise((resolve) => recorder.addEventListener("stop", resolve, { once: true }));
              recorder.start(1000);

              for (let frame = 0; frame <= Math.round(duration * fps); frame += 1) {
                studio.setTime(frame / fps);
                await new Promise((resolve) => setTimeout(resolve, frameDelay));
              }

              recorder.stop();
              await stopped;
              stream.getTracks().forEach((track) => track.stop());
              const videoBlob = new Blob(chunks, { type: mimeType });

              const video = document.createElement("video");
              video.muted = true;
              video.playsInline = true;
              video.src = URL.createObjectURL(videoBlob);
              await new Promise((resolve, reject) => {
                video.addEventListener("loadeddata", resolve, { once: true });
                video.addEventListener("error", reject, { once: true });
              });
              video.currentTime = Math.min(1, video.duration || 1);
              await new Promise((resolve) => video.addEventListener("seeked", resolve, { once: true }));
              const sample = document.createElement("canvas");
              sample.width = 720;
              sample.height = 864;
              const context = sample.getContext("2d", { willReadFrequently: true });
              context.clearRect(0, 0, 720, 864);
              context.drawImage(video, 0, 0, 720, 864);
              const cornerCoordinates = [[0, 0], [719, 0], [0, 863], [719, 863], [360, 20]];
              const cornerAlpha = cornerCoordinates.map(([x, y]) => context.getImageData(x, y, 1, 1).data[3]);
              URL.revokeObjectURL(video.src);

              const toDataUrl = (blob) => new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.addEventListener("load", () => resolve(reader.result), { once: true });
                reader.addEventListener("error", reject, { once: true });
                reader.readAsDataURL(blob);
              });

              return {
                mimeType,
                fps,
                duration,
                frameCount: Math.round(duration * fps),
                cornerAlpha,
                videoSize: videoBlob.size,
                posterSize: posterBlob.size,
                videoDataUrl: await toDataUrl(videoBlob),
                posterDataUrl: await toDataUrl(posterBlob),
              };
            }"""
        )
        browser.close()

    report = {
        "url": BASE_URL,
        "httpStatus": response.status if response else None,
        "mimeType": payload["mimeType"],
        "fps": payload["fps"],
        "duration": payload["duration"],
        "frameCount": payload["frameCount"],
        "cornerAlpha": payload["cornerAlpha"],
        "videoSize": payload["videoSize"],
        "posterSize": payload["posterSize"],
        "console": console,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
    }
    blocking_console = [
        item
        for item in console
        if item["type"] in {"error", "warning"}
        and not (
            item["type"] == "warning"
            and "pantheon-orb-alpha-poster" in item["text"]
            and "was preloaded using link preload" in item["text"]
        )
    ]
    blocking_request_failures = [
        item
        for item in request_failures
        if not (
            item["url"].startswith("blob:")
            and item["error"] == "net::ERR_ABORTED"
        )
    ]
    report["nonBlockingCaptureEvents"] = {
        "console": [
            item for item in console if item not in blocking_console
        ],
        "requestFailures": [
            item for item in request_failures if item not in blocking_request_failures
        ],
    }
    (EVIDENCE / "media-capture-evidence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    assert report["httpStatus"] == 200, report
    assert not page_errors, report
    assert not blocking_request_failures, report
    assert not blocking_console, report

    if any(alpha != 0 for alpha in report["cornerAlpha"]):
        raise RuntimeError(
            "Browser WebM encoder did not preserve transparent corner pixels; "
            f"alpha samples={report['cornerAlpha']}"
        )

    video_bytes = decode_data_url(payload["videoDataUrl"])
    poster_bytes = decode_data_url(payload["posterDataUrl"])
    (PUBLIC / "pantheon-orb-alpha-v3.webm").write_bytes(video_bytes)
    (PUBLIC / "pantheon-orb-alpha-poster-v3.webp").write_bytes(poster_bytes)
    (EVIDENCE / "pantheon-orb-alpha-v3.webm").write_bytes(video_bytes)
    (EVIDENCE / "pantheon-orb-alpha-poster-v3.webp").write_bytes(poster_bytes)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

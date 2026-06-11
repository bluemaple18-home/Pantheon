import { writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";

const path = process.argv[2] || "/";
const output = process.argv[3] || "TASK-002/evidence/page.png";
const width = Number(process.argv[4] || 1280);
const height = Number(process.argv[5] || 1200);
const clickSelector = process.argv[6] || "";
const port = 9342;
const chrome = spawn(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  [
    "--headless=new",
    "--disable-gpu",
    "--disable-component-update",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=/tmp/pantheon-page-shot-${Date.now()}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchJsonWithRetry(url, attempts = 12) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      return await fetch(url).then((response) => response.json());
    } catch (error) {
      lastError = error;
      await wait(500);
    }
  }
  throw lastError;
}

function send(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = send.nextId++;
    const onMessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.id === id) {
        ws.removeEventListener("message", onMessage);
        resolve(message.result);
      }
    };
    ws.addEventListener("message", onMessage);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => reject(new Error(`${method} timeout`)), 5000);
  });
}
send.nextId = 1;

try {
  await fetchJsonWithRetry(`http://127.0.0.1:${port}/json/version`);
  const target = await fetch(`http://127.0.0.1:${port}/json/new?http://127.0.0.1:8000${path}`, {
    method: "PUT",
  }).then((response) => response.json());
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));
  await send(ws, "Page.enable");
  await send(ws, "Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 700,
  });
  await send(ws, "Page.navigate", { url: `http://127.0.0.1:8000${path}?screenshot=1` });
  await wait(2200);
  if (clickSelector) {
    await send(ws, "Runtime.evaluate", {
      expression: `document.querySelector(${JSON.stringify(clickSelector)})?.click()`,
      returnByValue: true,
    });
    await wait(500);
  }
  const screenshot = await send(ws, "Page.captureScreenshot", { format: "png", fromSurface: true });
  await writeFile(output, Buffer.from(screenshot.data, "base64"));
  console.log(output);
  ws.close();
} finally {
  chrome.kill();
}

import { spawn } from "node:child_process";
import { writeFile } from "node:fs/promises";

const output = process.argv[2] || "TASK-002/evidence/fortune-reference-named-desktop.png";
const width = Number(process.argv[3] || 1365);
const height = Number(process.argv[4] || 1600);
const mobile = width < 700;
const port = 9344;
const chrome = spawn(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  [
    "--headless=new",
    "--disable-gpu",
    "--disable-component-update",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=/tmp/pantheon-fortune-reference-${Date.now()}`,
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
    setTimeout(() => reject(new Error(`${method} timeout`)), 8000);
  });
}
send.nextId = 1;

async function evaluate(ws, expression) {
  const result = await send(ws, "Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  return result.result?.value;
}

try {
  await fetchJsonWithRetry(`http://127.0.0.1:${port}/json/version`);
  const target = await fetch(`http://127.0.0.1:${port}/json/new?http://127.0.0.1:8000/`, {
    method: "PUT",
  }).then((response) => response.json());
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));

  const consoleEntries = [];
  const pageErrors = [];
  const requestFailures = [];
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.method === "Runtime.consoleAPICalled") {
      consoleEntries.push({
        type: message.params.type,
        text: message.params.args?.map((arg) => arg.value || arg.description || "").join(" "),
      });
    }
    if (message.method === "Runtime.exceptionThrown") {
      pageErrors.push(message.params.exceptionDetails?.text || "exception");
    }
    if (message.method === "Network.loadingFailed") {
      requestFailures.push(message.params.errorText || "request failed");
    }
  });

  await send(ws, "Page.enable");
  await send(ws, "Runtime.enable");
  await send(ws, "Network.enable");
  await send(ws, "Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile,
  });
  await send(ws, "Page.navigate", { url: "http://127.0.0.1:8000/?fortune-reference=1" });
  await wait(1800);

  const result = await evaluate(
    ws,
    `new Promise((resolve) => {
      const form = document.querySelector("#birth-form");
      form.querySelector("[name='name']").value = "郭家維";
      form.querySelector("[name='birth_date']").value = "1989-06-15";
      form.querySelector("[name='birth_time']").value = "04:00";
      form.querySelector("[name='gender']").value = "male";
      form.querySelector("[name='location']").value = "New Taipei";
      form.querySelector("[name='target_year']").value = "2026";
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      setTimeout(() => {
        const paper = document.querySelector("#fortune-paper");
        const text = paper?.innerText || "";
        const rect = paper?.getBoundingClientRect();
        resolve({
          hasName: text.includes("郭家維"),
          hasNameology: text.includes("姓名合參"),
          hasGrowth: text.includes("十二長生"),
          hasShensha: text.includes("神煞"),
          hasZiwei: text.includes("紫微星曜"),
          hasYearly: text.includes("今年財務、健康、人際"),
          docWidth: document.documentElement.scrollWidth,
          innerWidth,
          paperHeight: Math.round(rect?.height || 0),
        });
      }, 1800);
    })`,
  );

  const screenshot = await send(ws, "Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(output, Buffer.from(screenshot.data, "base64"));

  const evidence = {
    output,
    viewport: { width, height },
    result,
    console: consoleEntries.filter((entry) => entry.type === "error" || entry.type === "warning"),
    pageErrors,
    requestFailures,
  };
  console.log(JSON.stringify(evidence, null, 2));

  const ok =
    result.hasName &&
    result.hasNameology &&
    result.hasGrowth &&
    result.hasShensha &&
    result.hasZiwei &&
    result.hasYearly &&
    result.docWidth <= result.innerWidth + 1 &&
    pageErrors.length === 0 &&
    requestFailures.length === 0;
  if (!ok) process.exitCode = 1;
  ws.close();
} finally {
  chrome.kill();
}

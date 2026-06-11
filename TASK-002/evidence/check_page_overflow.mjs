import { spawn } from "node:child_process";

const path = process.argv[2] || "/";
const port = 9341;
const chrome = spawn(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  [
    "--headless=new",
    "--disable-gpu",
    "--disable-component-update",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=/tmp/pantheon-page-check-${Date.now()}`,
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
  const consoleErrors = [];
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.method === "Runtime.consoleAPICalled" && message.params?.type === "error") {
      consoleErrors.push(message.params.args?.map((arg) => arg.value || arg.description || "").join(" "));
    }
  });
  await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));
  await send(ws, "Runtime.enable");
  await send(ws, "Page.enable");
  await send(ws, "Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 1200,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await send(ws, "Page.navigate", { url: `http://127.0.0.1:8000${path}?overflow-check=1` });
  await wait(1800);
  const expression = `(() => {
    const viewportWidth = innerWidth;
    const offenders = [...document.querySelectorAll("*")]
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          tag: element.tagName,
          className: String(element.className || ""),
          id: element.id,
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
          text: (element.textContent || "").trim().slice(0, 48),
        };
      })
      .filter((item) => item.right > viewportWidth + 1 || item.left < -1)
      .slice(0, 20);
    return {
      innerWidth: viewportWidth,
      docWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      offenders,
    };
  })()`;
  const result = await send(ws, "Runtime.evaluate", { expression, returnByValue: true });
  console.log(JSON.stringify({ ...result.result.value, consoleErrors }, null, 2));
  ws.close();
} finally {
  chrome.kill();
}

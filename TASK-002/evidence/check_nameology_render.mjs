import { spawn } from "node:child_process";

const port = 9343;
const chrome = spawn(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  [
    "--headless=new",
    "--disable-gpu",
    "--disable-component-update",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=/tmp/pantheon-nameology-check-${Date.now()}`,
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
  const target = await fetch("http://127.0.0.1:9343/json/new?http://127.0.0.1:8000/", {
    method: "PUT",
  }).then((response) => response.json());
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));
  await send(ws, "Page.enable");
  await send(ws, "Runtime.enable");
  await send(ws, "Page.navigate", { url: "http://127.0.0.1:8000/?nameology-check=1" });
  await wait(2200);

  const result = await evaluate(
    ws,
    `new Promise((resolve) => {
      const form = document.querySelector("#birth-form");
      form.querySelector("[name='name']").value = "王小明";
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      setTimeout(() => {
        const paperText = document.querySelector("#fortune-paper")?.innerText || "";
        document.querySelector("[data-mode='dashboard']")?.click();
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        setTimeout(() => {
          const activeMode = document.querySelector(".mode-button.active")?.dataset.mode;
          resolve({
            hasObjectObject: paperText.includes("[object Object]"),
            hasFiveGrid: paperText.includes("天格") && paperText.includes("人格") && paperText.includes("三才"),
            activeMode,
          });
        }, 900);
      }, 1400);
    })`,
  );

  console.log(JSON.stringify(result, null, 2));
  if (result.hasObjectObject || !result.hasFiveGrid || result.activeMode !== "dashboard") {
    process.exitCode = 1;
  }
  ws.close();
} finally {
  chrome.kill();
}

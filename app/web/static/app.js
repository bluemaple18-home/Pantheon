import { buildPredictionPayload, fetchPrediction } from "./api.js";
import { renderDashboard } from "./dashboard.js";
import { renderFortunePaper } from "./paper.js";

const dom = {
  birthForm: document.querySelector("#birth-form"),
  apiStatus: document.querySelector("#api-status"),
  identityStrip: document.querySelector("#identity-strip"),
  pillarCards: document.querySelector("#pillar-cards"),
  destinyWheel: document.querySelector("#destiny-wheel"),
  elementBars: document.querySelector("#element-bars"),
  radarChart: document.querySelector("#radar-chart"),
  tenGodBoard: document.querySelector("#ten-god-board"),
  timingBoard: document.querySelector("#timing-board"),
  comboCards: document.querySelector("#combo-cards"),
  readingBlocks: document.querySelector("#reading-blocks"),
  signalsTable: document.querySelector("#signals-table"),
  fortunePaper: document.querySelector("#fortune-paper"),
  modeButtons: [...document.querySelectorAll(".mode-button")],
  modePanels: [...document.querySelectorAll("[data-mode-panel]")],
  chartTabs: [...document.querySelectorAll(".chart-tab")],
  chartViews: [...document.querySelectorAll("[data-chart-view]")],
};

let currentMode = "paper";
let userSelectedMode = false;

dom.modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    userSelectedMode = true;
    setMode(button.dataset.mode);
  });
});

dom.chartTabs.forEach((button) => {
  button.addEventListener("click", () => setChartView(button.dataset.chartTab));
});

function setMode(mode) {
  currentMode = mode;
  dom.modeButtons.forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  dom.modePanels.forEach((panel) => {
    panel.hidden = panel.dataset.modePanel !== mode;
  });
}

function setChartView(view) {
  dom.chartTabs.forEach((button) => {
    const active = button.dataset.chartTab === view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  dom.chartViews.forEach((panel) => {
    panel.hidden = panel.dataset.chartView !== view;
    panel.classList.toggle("active", panel.dataset.chartView === view);
  });
}

dom.birthForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = buildPredictionPayload(dom.birthForm);
  setStatus("生成中", "loading");
  try {
    const result = await fetchPrediction(data);
    renderReport(result);
    setStatus("已更新", "ready");
  } catch (error) {
    setStatus("API error", "error");
    console.error(error);
  }
});

function setStatus(text, state) {
  dom.apiStatus.textContent = text;
  dom.apiStatus.dataset.state = state;
}

function renderReport(result) {
  renderDashboard(result, dom);
  renderFortunePaper(result, dom.fortunePaper);
  setMode(userSelectedMode ? currentMode : "paper");
}

dom.birthForm.dispatchEvent(new Event("submit"));

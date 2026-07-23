import { buildPredictionPayload, fetchPrediction } from "./api.js";
import { getArticlePath, getProductThemeRecord, listArticleRecords } from "./article-registry.js?v=agy-harness-new-20260723-23";
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
  homeArticles: document.querySelector("[data-home-articles]"),
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

function renderInitialState() {
  renderHomeArticles();
  dom.fortunePaper.innerHTML = `
    <div class="empty report-empty-state">
      <div>
        <p class="eyebrow">Ready</p>
        <h2>尚未推演命盤</h2>
        <p>填好基本資料後，按下「開始推演命盤」才會產生命書。</p>
      </div>
    </div>
  `;
  setStatus("待推演", "idle");
  setMode("paper");
}

function renderHomeArticles() {
  if (!dom.homeArticles) return;
  const featuredArticles = pickFeaturedArticles(listArticleRecords());
  dom.homeArticles.replaceChildren(...featuredArticles.map((article) => {
    const productTheme = getProductThemeRecord(article.product);
    const card = document.createElement("a");
    card.className = "home-article-card";
    card.href = getArticlePath(article);
    card.dataset.productTheme = article.product;
    card.dataset.themeGlyph = productTheme.glyph;

    const meta = document.createElement("div");
    meta.className = "home-article-meta";

    const serial = document.createElement("span");
    serial.className = "home-article-serial";
    serial.textContent = article.serial;

    const product = document.createElement("span");
    product.className = "home-article-product";
    product.textContent = productTheme.label;

    const keyword = document.createElement("span");
    keyword.className = "home-article-keyword";
    keyword.textContent = article.primaryKeyword;

    const title = document.createElement("strong");
    title.textContent = article.title;

    const description = document.createElement("p");
    description.textContent = article.description;

    meta.append(serial, product, keyword);
    card.append(meta, title, description);
    return card;
  }));
}

function pickFeaturedArticles(articles) {
  const preferredSlugs = [
    "mbti-meaning",
    "tarot-card-meanings",
    "birth-chart-meaning",
    "birth-chart-astrology",
    "career-fortune",
    "life-direction",
  ];
  return preferredSlugs
    .map((slug) => articles.find((article) => article.slug === slug))
    .filter(Boolean);
}

renderInitialState();

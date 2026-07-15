const dom = {
  form: document.querySelector("[data-audit-form]"),
  submit: document.querySelector("[data-submit-button]"),
  loading: document.querySelector("[data-loading-state]"),
  loadingTitle: document.querySelector("[data-loading-title]"),
  loadingDetail: document.querySelector("[data-loading-detail]"),
  loadingTime: document.querySelector("[data-loading-time]"),
  error: document.querySelector("[data-error-state]"),
  errorMessage: document.querySelector("[data-error-message]"),
  results: document.querySelector("[data-results]"),
  resultMeta: document.querySelector("[data-result-meta]"),
  siteLink: document.querySelector("[data-site-link]"),
  scoreGrid: document.querySelector("[data-score-grid]"),
  comparisonSection: document.querySelector("[data-comparison-section]"),
  comparisonBody: document.querySelector("[data-comparison-body]"),
  findingList: document.querySelector("[data-finding-list]"),
  statGrid: document.querySelector("[data-stat-grid]"),
  endpointGrid: document.querySelector("[data-endpoint-grid]"),
  keywordSection: document.querySelector("[data-keyword-section]"),
  keywordSummary: document.querySelector("[data-keyword-summary]"),
  keywordList: document.querySelector("[data-keyword-list]"),
  pageCount: document.querySelector("[data-page-count]"),
  pageBody: document.querySelector("[data-page-body]"),
};

const SCORE_LABELS = {
  schema: ["Schema depth", "結構化資料"],
  eeat: ["E-E-A-T", "信任訊號"],
  citability: ["Citability", "引用友善度"],
  entity: ["Entity", "品牌實體"],
};

const ENDPOINT_LABELS = {
  robots: "robots.txt",
  sitemap: "sitemap.xml",
  feed: "RSS feed",
  llms_txt: "llms.txt",
  ai_txt: "ai.txt",
};

const STATUS_LABELS = {
  present: "有效",
  missing: "缺少",
  blocked: "受阻",
  fallback_html: "HTML fallback",
  invalid_content: "內容無效",
};

const LOCAL_HOSTS = new Set(["", "localhost", "127.0.0.1"]);
const API_BASE =
  window.PANTHEON_API_BASE ??
  (LOCAL_HOSTS.has(window.location.hostname) ? "" : "https://api.mysticpantheon.com");

let timerId = null;

dom.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(dom.form);
  const payload = {
    competitor_url: normalizeUrl(formData.get("competitor_url")),
    competitor_name: String(formData.get("competitor_name") || "").trim(),
    own_site_url: normalizeUrl(formData.get("own_site_url")),
    own_site_name: String(formData.get("own_site_name") || "").trim(),
    sample_limit: Number(formData.get("sample_limit")) || 6,
  };
  if (!payload.competitor_url) return;

  setLoading(true);
  dom.error.hidden = true;
  dom.results.hidden = true;
  try {
    const response = await fetch(`${API_BASE}/api/v1/seo/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(readError(data) || `HTTP ${response.status}`);
    }
    renderResults(data);
    dom.results.hidden = false;
    dom.results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    dom.errorMessage.textContent = error instanceof Error ? error.message : "請稍後再試。";
    dom.error.hidden = false;
  } finally {
    setLoading(false);
  }
});

function normalizeUrl(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return /^https?:\/\//i.test(text) ? text : `https://${text}`;
}

function readError(data) {
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg).filter(Boolean).join("；");
  return "";
}

function setLoading(active) {
  dom.loading.hidden = !active;
  dom.submit.disabled = active;
  dom.submit.querySelector("span").textContent = active ? "分析中…" : "開始分析";
  window.clearInterval(timerId);
  timerId = null;
  if (!active) return;

  const startedAt = Date.now();
  const steps = [
    [0, "正在建立網站輪廓", "檢查公開端點、頁面結構與 AI crawler 訊號…"],
    [8, "正在抽樣內容頁", "整理標題、描述、Schema、內外鏈與可引用訊號…"],
    [22, "正在比對關鍵字", "計算自家與競品的內容覆蓋差距…"],
  ];
  const update = () => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    const current = [...steps].reverse().find(([threshold]) => seconds >= threshold) || steps[0];
    dom.loadingTitle.textContent = current[1];
    dom.loadingDetail.textContent = current[2];
    dom.loadingTime.textContent = `00:${String(seconds).padStart(2, "0")}`;
  };
  update();
  timerId = window.setInterval(update, 1000);
}

function renderResults(data) {
  const competitor = data.competitor;
  const generated = new Date(data.generated_at);
  dom.resultMeta.textContent = `${competitor.site_name} · ${competitor.stats.audited_pages} 頁抽樣 · ${formatDate(generated)}`;
  dom.siteLink.href = competitor.base_url;
  renderScores(competitor.scores);
  renderComparison(data.comparison || []);
  renderFindings(competitor.findings || []);
  renderStats(competitor.stats || {});
  renderEndpoints(competitor.endpoints || {});
  renderKeywords(data, competitor);
  renderPages(competitor.pages || []);
}

function renderScores(scores) {
  dom.scoreGrid.replaceChildren(...Object.entries(SCORE_LABELS).map(([key, labels]) => {
    const value = Number(scores[key] || 0);
    const card = element("article", "score-card");
    const header = element("div", "score-card-header");
    header.append(textElement("span", labels[0]), textElement("small", labels[1]));
    const score = element("div", "score-value");
    score.append(textElement("strong", value), textElement("span", "/100"));
    const track = element("div", "score-track");
    const fill = document.createElement("i");
    fill.style.width = `${Math.max(0, Math.min(value, 100))}%`;
    track.append(fill);
    card.append(header, score, track);
    return card;
  }));
}

function renderComparison(rows) {
  dom.comparisonSection.hidden = rows.length === 0;
  dom.comparisonBody.replaceChildren(...rows.map((item) => {
    const row = document.createElement("tr");
    row.append(
      textCell(item.label),
      textCell(item.own),
      textCell(item.competitor),
      deltaCell(item.delta),
      textCell(item.verdict),
    );
    return row;
  }));
}

function renderFindings(findings) {
  const rows = findings.length ? findings : ["本次抽樣未發現明顯結構性缺口；下一步可擴大頁數並觀察內容覆蓋。"];
  dom.findingList.replaceChildren(...rows.map((finding) => textElement("li", finding)));
}

function renderStats(stats) {
  const rows = [
    ["抽樣頁面", stats.audited_pages || 0],
    ["成功頁面", stats.live_pages || 0],
    ["Feed 內容", stats.feed_items || 0],
    ["分類入口", stats.category_links || 0],
  ];
  dom.statGrid.replaceChildren(...rows.map(([label, value]) => {
    const group = document.createElement("div");
    group.append(textElement("dt", label), textElement("dd", value));
    return group;
  }));
}

function renderEndpoints(endpoints) {
  dom.endpointGrid.replaceChildren(...Object.entries(ENDPOINT_LABELS).map(([key, title]) => {
    const info = endpoints[key] || {};
    const item = element("article", "endpoint-item");
    const header = document.createElement("header");
    const dot = document.createElement("i");
    dot.className = String(info.label || "unknown");
    header.append(textElement("strong", title), dot);
    item.append(header, textElement("p", STATUS_LABELS[info.label] || "未知"));
    return item;
  }));
}

function renderKeywords(data, competitor) {
  const hasComparison = Boolean(data.own_site);
  const values = hasComparison
    ? data.content_gaps || []
    : (competitor.keyword_hits || []).map((item) => item.keyword);
  dom.keywordSummary.textContent = hasComparison
    ? "競品有命中、自家抽樣未命中的詞。"
    : "本次抽樣中有命中的關鍵字。";
  if (!values.length) {
    dom.keywordList.replaceChildren(textElement("p", "這次小樣本沒有抓到明顯內容缺口。", "keyword-empty"));
    return;
  }
  dom.keywordList.replaceChildren(...values.map((keyword) => textElement("span", keyword, "keyword-chip")));
}

function renderPages(pages) {
  dom.pageCount.textContent = `${pages.length} 個頁面`;
  dom.pageBody.replaceChildren(...pages.map((page) => {
    const row = document.createElement("tr");
    const pageCell = document.createElement("td");
    const link = textElement("a", page.title || page.url, "page-link");
    link.href = page.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.append(textElement("small", compactUrl(page.url)));
    pageCell.append(link);
    const status = textCell(page.status || "—");
    status.className = "status-code";
    row.append(
      pageCell,
      status,
      textCell((page.jsonld_types || []).join(", ") || "—"),
      textCell(page.internal_link_count || 0),
      textCell(page.description_len || 0),
    );
    return row;
  }));
}

function compactUrl(value) {
  try {
    const url = new URL(value);
    return `${url.hostname}${url.pathname}`;
  } catch {
    return value;
  }
}

function formatDate(date) {
  if (Number.isNaN(date.getTime())) return "剛剛完成";
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function element(tag, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function textElement(tag, value, className = "") {
  const node = element(tag, className);
  node.textContent = String(value);
  return node;
}

function textCell(value) {
  return textElement("td", value);
}

function deltaCell(value) {
  const number = Number(value || 0);
  const cell = textCell(number > 0 ? `+${number}` : number);
  cell.className = `delta ${number > 0 ? "positive" : number < 0 ? "negative" : ""}`;
  return cell;
}

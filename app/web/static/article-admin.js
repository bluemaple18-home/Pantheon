import {
  buildArticleGraph,
  GLOBAL_ARTICLE_POLICY,
  HUMANIZER_POLICY,
  listArticleVoiceAudits,
  listArticleRecords,
  listTopicRecords,
} from "./article-registry.js";

const dom = {
  boundary: document.querySelector("[data-policy-boundary]"),
  policyTags: document.querySelector("[data-policy-tags]"),
  topicTable: document.querySelector("[data-topic-table]"),
  graphSummary: document.querySelector("[data-graph-summary]"),
  graphLinks: document.querySelector("[data-graph-links]"),
  humanizerPurpose: document.querySelector("[data-humanizer-purpose]"),
  humanizerChecks: document.querySelector("[data-humanizer-checks]"),
  humanizerAudits: document.querySelector("[data-humanizer-audits]"),
  articleTable: document.querySelector("[data-article-table]"),
};

renderPolicy();
renderTopics();
renderGraph();
renderHumanizerGate();
renderArticles();

function renderPolicy() {
  dom.boundary.textContent = GLOBAL_ARTICLE_POLICY.publicContentBoundary;
  dom.policyTags.replaceChildren(
    ...[
      ...GLOBAL_ARTICLE_POLICY.requiredTags,
      ...GLOBAL_ARTICLE_POLICY.requiredKeywordTags,
    ].map(renderTag),
  );
}

function renderTopics() {
  dom.topicTable.replaceChildren(...listTopicRecords().map((topic) => {
    const card = document.createElement("article");
    card.className = "article-admin-topic ui-panel";
    card.innerHTML = `
      <div>
        <p>${topic.slug}</p>
        <h3>${topic.label}</h3>
      </div>
      <p>${topic.description}</p>
      <strong>${topic.primaryKeyword}</strong>
    `;
    const tags = document.createElement("div");
    tags.className = "article-tag-list ui-chip-list";
    tags.replaceChildren(...topic.requiredTags.map(renderTag));
    card.append(tags);
    return card;
  }));
}

function renderGraph() {
  const graph = buildArticleGraph();
  const counts = graph.nodes.reduce((total, node) => ({
    ...total,
    [node.kind]: (total[node.kind] || 0) + 1,
  }), {});
  dom.graphSummary.replaceChildren(
    renderMetric("Topic nodes", counts.topic || 0),
    renderMetric("Article nodes", counts.article || 0),
    renderMetric("Tag nodes", counts.tag || 0),
    renderMetric("Links", graph.links.length),
  );
  dom.graphLinks.replaceChildren(...graph.links.slice(0, 18).map((link) => {
    const item = document.createElement("p");
    item.textContent = `${link.kind}: ${link.source} -> ${link.target}`;
    return item;
  }));
}

function renderHumanizerGate() {
  dom.humanizerPurpose.textContent = HUMANIZER_POLICY.purpose;
  dom.humanizerChecks.replaceChildren(...HUMANIZER_POLICY.requiredChecks.map((check) => {
    const item = document.createElement("span");
    item.textContent = check;
    return item;
  }));
  dom.humanizerAudits.replaceChildren(...listArticleVoiceAudits().map((audit) => {
    const item = document.createElement("article");
    item.className = `article-admin-audit ui-panel ${audit.status}`;
    item.innerHTML = `
      <div>
        <strong>${audit.title}</strong>
        <span>${audit.status === "pass" ? "Pass" : "Needs review"}</span>
      </div>
      <p>${audit.issues.length ? audit.issues.join("；") : "未命中主要 AI 腔風險。"}</p>
    `;
    return item;
  }));
}

function renderArticles() {
  dom.articleTable.replaceChildren(...listArticleRecords().map((article) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>
        <a href="/articles/${article.category}/${article.slug}">${article.title}</a>
        <span>${article.description}</span>
      </td>
      <td>${article.category}</td>
      <td>${article.primaryKeyword}</td>
    `;
    const tagCell = document.createElement("td");
    const tags = document.createElement("div");
    tags.className = "article-tag-list ui-chip-list";
    tags.replaceChildren(...article.tags.map(renderTag));
    tagCell.append(tags);
    row.append(tagCell);
    return row;
  }));
}

function renderMetric(label, value) {
  const item = document.createElement("div");
  item.innerHTML = `<strong>${value}</strong><span>${label}</span>`;
  return item;
}

function renderTag(label) {
  const item = document.createElement("span");
  item.className = "ui-chip";
  item.textContent = label;
  return item;
}

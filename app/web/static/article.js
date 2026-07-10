import { buildArticleContent } from "./article-meta.js?v=article-content-20260710-6";
import { applyArticleSeo } from "./article-seo.js?v=article-content-20260710-6";

const dom = {
  productCrumb: document.querySelector("[data-product-crumb]"),
  productSeparator: document.querySelector("[data-product-separator]"),
  titleCrumb: document.querySelector("[data-title-crumb]"),
  titleSeparator: document.querySelector("[data-title-separator]"),
  articleProduct: document.querySelector("[data-article-product]"),
  articleTitle: document.querySelector("[data-article-title]"),
  articleAuthor: document.querySelector("[data-article-author]"),
  articleUpdated: document.querySelector("[data-article-updated]"),
  sectionDescription: document.querySelector("[data-section-description]"),
  productThemeLabel: document.querySelector("[data-product-theme-label]"),
  productThemeGlyph: document.querySelector("[data-product-theme-glyph]"),
  productThemeDescription: document.querySelector("[data-product-theme-description]"),
  articleTags: document.querySelector("[data-article-tags]"),
  answerText: document.querySelector("[data-answer-text]"),
  articleBody: document.querySelector("[data-article-body]"),
  articleFaq: document.querySelector("[data-article-faq]"),
  articleRelated: document.querySelector("[data-article-related]"),
  articleCta: document.querySelector("[data-article-cta]"),
  canonical: document.querySelector("link[rel='canonical']"),
  description: document.querySelector("meta[name='description']"),
  keywords: document.querySelector("meta[name='keywords']"),
  ogTitle: document.querySelector("meta[property='og:title']"),
  ogDescription: document.querySelector("meta[property='og:description']"),
  ogUrl: document.querySelector("meta[property='og:url']"),
  twitterTitle: document.querySelector("meta[name='twitter:title']"),
  twitterDescription: document.querySelector("meta[name='twitter:description']"),
  articleJsonLd: document.querySelector("#article-jsonld"),
  breadcrumbJsonLd: document.querySelector("#breadcrumb-jsonld"),
  faqJsonLd: document.querySelector("#faq-jsonld"),
};

const content = buildArticleContent(window.location.pathname, window.location.origin, {
  author: dom.articleAuthor?.textContent?.trim(),
  updated: dom.articleUpdated?.dateTime,
});

renderArticleChrome(content);
applyArticleSeo(content, dom, window.location.origin);

function renderArticleChrome(content) {
  document.body.dataset.productTheme = content.productTheme;
  document.body.dataset.intent = content.intent;
  dom.articleTitle.textContent = content.title;
  dom.titleCrumb.textContent = content.title;
  dom.articleProduct.textContent = content.productCrumbLabel;

  if (content.productCrumb) {
    dom.productCrumb.hidden = false;
    dom.productSeparator.hidden = false;
    dom.productCrumb.textContent = content.slug ? content.productCrumbLabel : content.title;
    dom.productCrumb.href = content.productHref;
  }

  if (content.slug || content.intent) {
    dom.titleSeparator.hidden = false;
    dom.titleCrumb.hidden = false;
  }

  dom.sectionDescription.textContent = content.sectionDescription;
  dom.answerText.textContent = content.answer;
  dom.productThemeLabel.textContent = content.productThemeLabel;
  dom.productThemeGlyph.textContent = content.productThemeGlyph;
  dom.productThemeDescription.textContent = content.productThemeDescription;
  dom.articleTags.replaceChildren(...(content.displayTags || content.tags || []).map((tag) => {
    const item = document.createElement("span");
    item.className = "ui-chip";
    item.textContent = tag;
    return item;
  }));
  renderArticleBody(content);
  renderArticleFaq(content);
  renderArticleRelated(content);
  renderArticleCta(content);
}

function renderArticleBody(content) {
  if (!dom.articleBody) return;
  const blocks = content.bodySections.map((section) => {
    const block = document.createElement("section");
    const heading = document.createElement("h2");
    heading.textContent = section.heading;
    block.append(heading, ...section.paragraphs.map((text) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = text;
      return paragraph;
    }));
    return block;
  });
  dom.articleBody.replaceChildren(...blocks);
}

function renderArticleFaq(content) {
  if (!dom.articleFaq) return;
  const heading = document.createElement("h2");
  heading.textContent = "常見問題";
  const questions = content.faq.map((item) => {
    const detail = document.createElement("details");
    const summary = document.createElement("summary");
    const answer = document.createElement("p");
    summary.textContent = item.question;
    answer.textContent = item.answer;
    detail.append(summary, answer);
    return detail;
  });
  dom.articleFaq.replaceChildren(heading, ...questions);
}

function renderArticleRelated(content) {
  if (!dom.articleRelated || !content.relatedLinks?.length) return;
  dom.articleRelated.hidden = false;
  const heading = document.createElement("h2");
  heading.textContent = "延伸閱讀";
  const list = document.createElement("ul");
  list.className = "article-link-list";
  content.relatedLinks.forEach((item) => {
    const link = document.createElement("a");
    const meta = document.createElement("span");
    const row = document.createElement("li");
    link.href = item.href;
    link.textContent = item.label;
    meta.textContent = item.kind;
    row.append(link, meta);
    list.append(row);
  });
  dom.articleRelated.replaceChildren(heading, list);
}

function renderArticleCta(content) {
  if (!dom.articleCta || !content.cta) return;
  dom.articleCta.hidden = false;
  const heading = document.createElement("h2");
  const body = document.createElement("p");
  const links = document.createElement("div");
  heading.textContent = content.cta.title;
  body.textContent = content.cta.body;
  links.className = "article-cta-actions";
  content.cta.links.forEach((item) => {
    const link = document.createElement("a");
    link.className = "ui-button ui-button-secondary";
    link.href = item.href;
    link.textContent = item.label;
    links.append(link);
  });
  dom.articleCta.replaceChildren(heading, body, links);
}

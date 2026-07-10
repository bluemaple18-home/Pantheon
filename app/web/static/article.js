import { buildArticleContent } from "./article-meta.js";
import { applyArticleSeo } from "./article-seo.js";

const dom = {
  categoryCrumb: document.querySelector("[data-category-crumb]"),
  categorySeparator: document.querySelector("[data-category-separator]"),
  titleCrumb: document.querySelector("[data-title-crumb]"),
  titleSeparator: document.querySelector("[data-title-separator]"),
  articleCategory: document.querySelector("[data-article-category]"),
  articleTitle: document.querySelector("[data-article-title]"),
  articleAuthor: document.querySelector("[data-article-author]"),
  articleUpdated: document.querySelector("[data-article-updated]"),
  topicDescription: document.querySelector("[data-topic-description]"),
  productThemeLabel: document.querySelector("[data-product-theme-label]"),
  productThemeGlyph: document.querySelector("[data-product-theme-glyph]"),
  productThemeDescription: document.querySelector("[data-product-theme-description]"),
  articleTags: document.querySelector("[data-article-tags]"),
  answerText: document.querySelector("[data-answer-text]"),
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
  document.body.dataset.topicIntent = content.topicIntent;

  if (content.category) {
    dom.categoryCrumb.hidden = false;
    dom.categorySeparator.hidden = false;
    dom.categoryCrumb.textContent = content.categoryLabel;
    dom.categoryCrumb.href = `/articles/${content.category}`;
    dom.articleCategory.textContent = content.categoryLabel;
  }

  if (content.slug) {
    dom.titleSeparator.hidden = false;
    dom.titleCrumb.textContent = content.title;
    dom.articleTitle.textContent = content.title;
  }

  dom.topicDescription.textContent = content.topicDescription;
  dom.productThemeLabel.textContent = content.productThemeLabel;
  dom.productThemeGlyph.textContent = content.productThemeGlyph;
  dom.productThemeDescription.textContent = content.productThemeDescription;
  dom.articleTags.replaceChildren(...content.tags.map((tag) => {
    const item = document.createElement("span");
    item.className = "ui-chip";
    item.textContent = tag;
    return item;
  }));
}

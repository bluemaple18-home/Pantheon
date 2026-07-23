import { buildArticleContent } from "./article-meta.js?v=agy-harness-new-20260723-36";
import { applyArticleSeo } from "./article-seo.js?v=article-content-20260710-10";

const INLINE_TOPIC_MAX_LINKS = 8;
const VISIBLE_RELATED_MAX_LINKS = 6;

const dom = {
  productCrumb: document.querySelector("[data-product-crumb]"),
  productSeparator: document.querySelector("[data-product-separator]"),
  titleCrumb: document.querySelector("[data-title-crumb]"),
  titleSeparator: document.querySelector("[data-title-separator]"),
  articleProduct: document.querySelector("[data-article-product]"),
  articleTitle: document.querySelector("[data-article-title]"),
  articleSerialWrapper: document.querySelector("[data-article-serial-wrapper]"),
  articleSerial: document.querySelector("[data-article-serial]"),
  articleAuthor: document.querySelector("[data-article-author]"),
  articleUpdated: document.querySelector("[data-article-updated]"),
  sectionDescription: document.querySelector("[data-section-description]"),
  productThemeLabel: document.querySelector("[data-product-theme-label]"),
  productThemeGlyph: document.querySelector("[data-product-theme-glyph]"),
  productThemeDescription: document.querySelector("[data-product-theme-description]"),
  articleTags: document.querySelector("[data-article-tags]"),
  answerText: document.querySelector("[data-answer-text]"),
  articleBody: document.querySelector("[data-article-body]"),
  hubVisibleLinks: document.querySelector("[data-hub-visible-links]"),
  topicVisibleLinks: document.querySelector("[data-topic-visible-links]"),
  articleNavigation: document.querySelector("[data-article-navigation]"),
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
});

if (content.redirectTo) {
  window.location.replace(content.redirectTo);
} else {
  renderArticleChrome(content);
  applyArticleSeo(content, dom, window.location.origin);
  initArticlePointerEffects();
}

function initArticlePointerEffects() {
  const root = document.body;
  const visual = document.querySelector(".article-theme-visual");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (!finePointer.matches || reducedMotion.matches) return;

  let pointerFrame = 0;
  let tailFadeTimer = 0;
  let previousPointer = null;
  root.dataset.pointerEffects = "enabled";

  const updateBackground = (event) => {
    const pointer = {
      clientX: event.clientX,
      clientY: event.clientY,
      pageX: event.pageX,
      pageY: event.pageY,
    };
    const deltaX = previousPointer ? pointer.clientX - previousPointer.clientX : 0;
    const deltaY = previousPointer ? pointer.clientY - previousPointer.clientY : 0;
    const distance = Math.hypot(deltaX, deltaY);
    previousPointer = pointer;
    cancelAnimationFrame(pointerFrame);
    pointerFrame = requestAnimationFrame(() => {
      root.style.setProperty("--article-pointer-x", `${pointer.pageX}px`);
      root.style.setProperty("--article-pointer-y", `${pointer.pageY}px`);
      root.style.setProperty("--article-pointer-client-x", `${pointer.clientX}px`);
      root.style.setProperty("--article-pointer-client-y", `${pointer.clientY}px`);
      if (distance > 1) {
        const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);
        const stretch = Math.min(1.2, Math.max(0.7, distance / 16));
        const opacity = Math.min(0.82, Math.max(0.36, distance / 30));
        root.style.setProperty("--article-tail-angle", `${angle.toFixed(2)}deg`);
        root.style.setProperty("--article-tail-scale", stretch.toFixed(2));
        root.style.setProperty("--article-tail-opacity", opacity.toFixed(2));
        clearTimeout(tailFadeTimer);
        tailFadeTimer = window.setTimeout(() => {
          root.style.setProperty("--article-tail-opacity", "0");
        }, 220);
      }
    });
  };

  const updateVisual = (event) => {
    if (!visual) return;
    const bounds = visual.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;
    visual.style.setProperty("--article-tilt-x", `${(-y * 3.5).toFixed(2)}deg`);
    visual.style.setProperty("--article-tilt-y", `${(x * 4.5).toFixed(2)}deg`);
    visual.style.setProperty("--article-orbit-x", `${(x * 10).toFixed(2)}px`);
    visual.style.setProperty("--article-orbit-y", `${(y * 10).toFixed(2)}px`);
  };

  const resetVisual = () => {
    visual?.style.setProperty("--article-tilt-x", "0deg");
    visual?.style.setProperty("--article-tilt-y", "0deg");
    visual?.style.setProperty("--article-orbit-x", "0px");
    visual?.style.setProperty("--article-orbit-y", "0px");
  };

  root.addEventListener("pointermove", updateBackground, { passive: true });
  visual?.addEventListener("pointermove", updateVisual, { passive: true });
  visual?.addEventListener("pointerleave", resetVisual);
  window.addEventListener("pagehide", () => {
    cancelAnimationFrame(pointerFrame);
    clearTimeout(tailFadeTimer);
  }, { once: true });
}

function renderArticleChrome(content) {
  const inlineTopicState = buildInlineTopicState(content);
  document.body.dataset.productTheme = content.productTheme;
  document.body.dataset.intent = content.intent;
  dom.articleTitle.textContent = content.title;
  dom.titleCrumb.textContent = content.title;
  dom.articleProduct.textContent = content.productCrumbLabel;
  if (content.serial && dom.articleSerial && dom.articleSerialWrapper) {
    dom.articleSerial.textContent = content.serial;
    dom.articleSerialWrapper.hidden = false;
  }

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
  if (dom.articleUpdated && content.updated) {
    dom.articleUpdated.dateTime = content.updated;
    dom.articleUpdated.textContent = content.updated;
  }
  dom.productThemeLabel.textContent = content.productThemeLabel;
  dom.productThemeGlyph.textContent = content.productThemeGlyph;
  dom.productThemeDescription.textContent = content.productThemeDescription;
  dom.articleTags.replaceChildren(...(content.displayTagLinks || (content.displayTags || content.tags || []).map((label) => ({ label }))).map((tag) => {
    const item = document.createElement(tag.href ? "a" : "span");
    item.className = "ui-chip";
    item.textContent = tag.label;
    if (tag.href) item.href = tag.href;
    return item;
  }));
  renderArticleBody(content, inlineTopicState);
  renderHubVisibleLinks(content);
  renderArticleNavigation(content);
  renderArticleFaq(content);
  renderArticleRelated(content);
  renderArticleCta(content);
}

function renderArticleBody(content, inlineTopicState) {
  if (!dom.articleBody) return;
  const blocks = content.bodySections.map((section) => {
    const block = document.createElement("section");
    const heading = document.createElement("h2");
    heading.textContent = section.heading;
    block.append(heading, ...section.paragraphs.map((text) => {
      const paragraph = document.createElement("p");
      appendInlineTopicLinks(paragraph, text, inlineTopicState);
      return paragraph;
    }));
    if (section.links?.length) {
      const list = document.createElement("ul");
      list.className = "article-link-list";
      section.links.forEach((item) => {
        const link = document.createElement("a");
        const meta = document.createElement("span");
        const row = document.createElement("li");
        link.href = item.href;
        link.textContent = item.label;
        meta.textContent = item.kind;
        row.append(link, meta);
        list.append(row);
      });
      block.append(list);
    }
    return block;
  });
  dom.articleBody.replaceChildren(...blocks);
}

function buildInlineTopicState(content) {
  const terms = (content.displayTagLinks || [])
    .filter((tag) => tag?.href?.startsWith("/topics/") && tag.label)
    .flatMap((tag) => buildInlineTermsFromTag(tag))
    .filter((term) => term.text)
    .filter((term, index, list) => list.findIndex((item) => item.text === term.text && item.href === term.href) === index)
    .sort((a, b) => b.text.length - a.text.length || a.text.localeCompare(b.text));
  return {
    terms,
    linkedTerms: new Set(),
    linkCount: 0,
  };
}

function buildInlineTermsFromTag(tag) {
  const label = String(tag.label || "").trim();
  const terms = [
    {
      text: label,
      href: tag.href,
    },
  ];
  const acronym = label.match(/^[A-Z][A-Z0-9]{1,}(?=\s|$)/)?.[0];
  if (acronym) {
    terms.push({
      text: acronym,
      href: tag.href,
    });
  }
  return terms;
}

function appendInlineTopicLinks(node, text = "", inlineTopicState) {
  const source = String(text || "");
  const state = inlineTopicState || buildInlineTopicState({});
  let cursor = 0;

  while (cursor < source.length) {
    const match = state.linkCount < INLINE_TOPIC_MAX_LINKS
      ? state.terms.find((term) => !state.linkedTerms.has(term.text) && source.startsWith(term.text, cursor))
      : null;
    if (!match) {
      const nextMatchIndex = state.linkCount < INLINE_TOPIC_MAX_LINKS
        ? findNextInlineTopicIndex(source, cursor + 1, state)
        : source.length;
      node.append(document.createTextNode(source.slice(cursor, nextMatchIndex)));
      cursor = nextMatchIndex;
      continue;
    }

    const link = document.createElement("a");
    link.className = "article-inline-topic-link";
    link.href = match.href;
    link.textContent = match.text;
    node.append(link);
    state.linkedTerms.add(match.text);
    state.linkCount += 1;
    cursor += match.text.length;
  }
}

function findNextInlineTopicIndex(source, start, state) {
  let next = source.length;
  state.terms.forEach((term) => {
    if (state.linkedTerms.has(term.text)) return;
    const index = source.indexOf(term.text, start);
    if (index !== -1 && index < next) next = index;
  });
  return next;
}

function renderArticleFaq(content) {
  if (!dom.articleFaq) return;
  if (!content.faq?.length) {
    dom.articleFaq.hidden = true;
    dom.articleFaq.replaceChildren();
    return;
  }
  dom.articleFaq.hidden = false;
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

function renderArticleNavigation(content) {
  if (!dom.articleNavigation) return;
  const navigationLinks = content.navigationLinks || [];
  if (!navigationLinks.length) {
    dom.articleNavigation.hidden = true;
    dom.articleNavigation.replaceChildren();
    return;
  }
  const previous = navigationLinks.find((item) => item.kind === "上一篇");
  const next = navigationLinks.find((item) => item.kind === "下一篇");
  const actions = document.createElement("div");
  actions.className = "article-sequence-actions";
  actions.append(
    renderSequenceButton(previous, "previous"),
    renderSequenceButton(next, "next"),
  );
  dom.articleNavigation.hidden = false;
  dom.articleNavigation.replaceChildren(actions);
}

function renderSequenceButton(item, direction) {
  if (!item) {
    const placeholder = document.createElement("span");
    placeholder.className = `article-sequence-placeholder article-sequence-placeholder-${direction}`;
    placeholder.setAttribute("aria-hidden", "true");
    return placeholder;
  }
  const link = document.createElement("a");
  const meta = document.createElement("span");
  const title = document.createElement("strong");
  link.className = `article-sequence-button article-sequence-button-${direction}`;
  link.href = item.href;
  meta.textContent = direction === "previous" ? "← 上一篇" : "下一篇 →";
  title.textContent = item.label;
  link.append(meta, title);
  return link;
}

function renderArticleRelated(content) {
  if (!dom.articleRelated) return;
  if (content.hubVisibleLinks?.links?.length) {
    dom.articleRelated.hidden = true;
    dom.articleRelated.replaceChildren();
    return;
  }
  const links = buildVisibleRelatedLinks(content);
  if (links.length) {
    const heading = document.createElement("h2");
    heading.textContent = "延伸閱讀";
    dom.articleRelated.hidden = false;
    dom.articleRelated.replaceChildren(heading, renderArticleLinkList(links, "article-link-list article-visible-link-list"));
    return;
  }
  dom.articleRelated.hidden = true;
  dom.articleRelated.replaceChildren();
}

function buildVisibleRelatedLinks(content) {
  const currentPath = content.canonicalPath || window.location.pathname;
  const links = [];
  const addLink = (item) => {
    if (!item?.href || !item?.label || item.href === currentPath) return;
    if (links.some((link) => link.href === item.href)) return;
    links.push({
      href: item.href,
      label: item.label,
      kind: item.kind || "延伸閱讀",
    });
  };

  addLink({
    href: content.productHref,
    label: `回到${content.productThemeLabel || content.productCrumbLabel || "分類"}文章`,
    kind: "分類文章",
  });
  (content.relatedLinks || []).forEach(addLink);
  return links.slice(0, VISIBLE_RELATED_MAX_LINKS);
}

function renderHubVisibleLinks(content) {
  hideHubVisibleLinks();
  const module = content.hubVisibleLinks;
  if (!module?.links?.length) return;
  const target = module.type === "topic" ? dom.topicVisibleLinks : dom.hubVisibleLinks;
  if (!target) return;
  const heading = document.createElement("h2");
  heading.textContent = module.title;
  target.hidden = false;
  target.replaceChildren(heading, renderArticleLinkList(module.links, "article-link-list article-visible-link-list"));
}

function hideHubVisibleLinks() {
  [dom.hubVisibleLinks, dom.topicVisibleLinks].forEach((section) => {
    if (!section) return;
    section.hidden = true;
    section.replaceChildren();
  });
}

function renderArticleLinkList(items, className) {
  const list = document.createElement("ul");
  list.className = className;
  items.forEach((item) => {
    const link = document.createElement("a");
    const meta = document.createElement("span");
    const row = document.createElement("li");
    link.href = item.href;
    link.textContent = item.label;
    meta.textContent = item.kind;
    row.append(link, meta);
    list.append(row);
  });
  return list;
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

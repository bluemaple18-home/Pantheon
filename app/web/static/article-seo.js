export function applyArticleSeo(content, dom, origin) {
  document.title = content.pageTitle;
  document.documentElement.lang = content.htmlLang || "zh-Hant";
  dom.canonical.href = content.canonicalUrl;
  dom.description.content = content.description;
  dom.keywords.content = content.keywords.join(", ");
  dom.ogTitle.content = content.pageTitle;
  dom.ogDescription.content = content.description;
  dom.ogUrl.content = content.canonicalUrl;
  dom.twitterTitle.content = content.pageTitle;
  dom.twitterDescription.content = content.description;
  dom.answerText.textContent = content.answer;
  syncOgLocale(content);
  syncAlternateLinks(content, origin);
  syncSiteEntityJsonLd(content);
  writeJsonLd(dom.breadcrumbJsonLd, buildBreadcrumbJsonLd(content, origin));
  writeJsonLd(dom.articleJsonLd, buildArticleJsonLd(content, origin));
  writeJsonLd(dom.faqJsonLd, buildFaqJsonLd(content));
}

export function buildBreadcrumbJsonLd(content, origin) {
  const articlesHubPath = content.articlesHubPath || "/articles";
  const latestArticlesLabel = content.uiMessages?.latestArticles || "最新文章";
  const items = [
    { name: "Pantheon", item: `${origin}${articlesHubPath}` },
    { name: latestArticlesLabel, item: `${origin}${articlesHubPath}` },
  ];
  if (content.productCrumb) {
    items.push({
      name: content.slug ? content.productCrumbLabel : content.title,
      item: content.productSchemaHref?.startsWith("http")
        ? content.productSchemaHref
        : `${origin}${content.productSchemaHref || content.productHref}`,
    });
  }
  if (content.intent && !content.slug) items.push({ name: content.title, item: content.canonicalUrl });
  if (content.slug) {
    items.push({ name: content.title, item: content.canonicalUrl });
  }
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.item,
    })),
  };
}

export function buildArticleJsonLd(content, origin) {
  const organizationRef = { "@id": `${origin}/#organization` };
  const websiteRef = { "@id": `${origin}/#website` };
  const image = `${origin}/static/pantheon-orb-alpha-poster.webp`;
  if (content.contentType === "CollectionPage") {
    return {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: content.title,
      description: content.description,
      inLanguage: content.inLanguage || "zh-Hant-TW",
      url: content.canonicalUrl,
      mainEntityOfPage: content.canonicalUrl,
      isPartOf: websiteRef,
      publisher: organizationRef,
      image,
      about: (content.displayTags || content.tags || []).map((tag) => ({
        "@type": "Thing",
        name: tag,
      })),
    };
  }
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: content.slug ? content.title : content.pageTitle.replace(" | Pantheon", ""),
    description: content.description,
    inLanguage: content.inLanguage || "zh-Hant-TW",
    url: content.canonicalUrl,
    mainEntityOfPage: content.canonicalUrl,
    image,
    datePublished: content.published,
    dateModified: content.updated,
    author: {
      "@type": "Organization",
      name: content.author,
    },
    publisher: organizationRef,
    isPartOf: websiteRef,
    articleSection: content.productThemeLabel,
    keywords: content.keywords.join(", "),
    about: (content.displayTags || content.tags || []).map((tag) => ({
      "@type": "Thing",
      name: tag,
    })),
  };
}

export function buildFaqJsonLd(content) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: content.faq.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  };
}

function writeJsonLd(node, data) {
  node.textContent = JSON.stringify(data);
}

function syncOgLocale(content) {
  const ogLocale = document.querySelector("meta[property='og:locale']");
  if (ogLocale) ogLocale.content = content.ogLocale || "zh_TW";
}

function syncAlternateLinks(content, origin) {
  document
    .querySelectorAll("link[rel='alternate'][hreflang]")
    .forEach((node) => node.remove());
  const canonicalNode = document.querySelector("link[rel='canonical']");
  const head = document.head;
  const items = [
    ...(content.languageLinks || []),
    {
      hreflang: "x-default",
      href: content.sourcePath || content.canonicalPath,
    },
  ];
  const seen = new Set();
  items.forEach((item) => {
    const hreflang = item?.hreflang;
    if (!hreflang || seen.has(hreflang)) return;
    seen.add(hreflang);
    const href = toAbsoluteUrl(item.href, origin);
    if (!href) return;
    const link = document.createElement("link");
    link.rel = "alternate";
    link.hreflang = hreflang;
    link.href = href;
    head.insertBefore(link, canonicalNode || null);
  });
}

function syncSiteEntityJsonLd(content) {
  const node = document.querySelector("#site-entity-jsonld");
  if (!node?.textContent?.trim()) return;
  try {
    const payload = JSON.parse(node.textContent);
    const website = payload?.["@graph"]?.find((item) => item?.["@type"] === "WebSite");
    if (website) website.inLanguage = content.htmlLang || "zh-Hant";
    node.textContent = JSON.stringify(payload);
  } catch {
    // Keep the static fallback JSON-LD if parsing fails.
  }
}

function toAbsoluteUrl(path, origin) {
  if (!path) return "";
  return path.startsWith("http") ? path : `${origin}${path}`;
}

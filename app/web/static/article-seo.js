export function applyArticleSeo(content, dom, origin) {
  document.title = content.pageTitle;
  dom.canonical.href = content.canonicalUrl;
  dom.description.content = content.description;
  dom.keywords.content = content.keywords.join(", ");
  dom.ogTitle.content = content.pageTitle;
  dom.ogDescription.content = content.description;
  dom.ogUrl.content = content.canonicalUrl;
  dom.twitterTitle.content = content.pageTitle;
  dom.twitterDescription.content = content.description;
  dom.answerText.textContent = content.answer;
  writeJsonLd(dom.breadcrumbJsonLd, buildBreadcrumbJsonLd(content, origin));
  writeJsonLd(dom.articleJsonLd, buildArticleJsonLd(content, origin));
  writeJsonLd(dom.faqJsonLd, buildFaqJsonLd(content));
}

export function buildBreadcrumbJsonLd(content, origin) {
  const items = [
    { name: "Pantheon", item: `${origin}/articles` },
    { name: "最新文章", item: `${origin}/articles` },
  ];
  if (content.productCrumb) {
    items.push({
      name: content.slug ? content.productCrumbLabel : content.title,
      item: content.productHref.startsWith("http") ? content.productHref : `${origin}${content.productHref}`,
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
  if (content.contentType === "CollectionPage") {
    return {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: content.title,
      description: content.description,
      inLanguage: "zh-Hant-TW",
      url: content.canonicalUrl,
      mainEntityOfPage: content.canonicalUrl,
      publisher: {
        "@type": "Organization",
        name: "Pantheon",
        url: `${origin}/`,
      },
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
    inLanguage: "zh-Hant-TW",
    url: content.canonicalUrl,
    mainEntityOfPage: content.canonicalUrl,
    datePublished: content.published,
    dateModified: content.updated,
    author: {
      "@type": "Organization",
      name: content.author,
    },
    publisher: {
      "@type": "Organization",
      name: "Pantheon",
      url: `${origin}/`,
    },
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

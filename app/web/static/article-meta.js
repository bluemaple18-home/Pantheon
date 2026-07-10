import {
  enforceArticlePolicy,
  getArticleRecord,
  getArticleSectionRecord,
  getLifeIntentRecord,
  getProductThemeRecord,
} from "./article-registry.js";

export function buildArticleContent(pathname, origin, defaults = {}) {
  const route = parseArticleRoute(pathname);
  const isLatestHub = !route.product && !route.slug && !route.intent;
  const intent = route.intent ? getLifeIntentRecord(route.intent) : null;
  const article = route.product && route.slug ? getArticleRecord(route.product, route.slug) : null;
  const section = article ? getArticleSectionRecord(article.section) : getArticleSectionRecord(route.product);
  const productThemeRecord = getProductThemeRecord(article?.product || route.product || section?.product);
  const canonicalPath = route.intent
    ? `/articles/intents/${route.intent}`
    : route.product && route.slug
      ? `/articles/${route.product}/${route.slug}`
      : route.product
        ? `/articles/${route.product}`
      : "/articles";
  const title = article?.title || route.title;
  const pageTitle = route.slug
    ? `${title} | Pantheon`
    : route.intent
      ? `${intent?.label || route.intentLabel}文章 | Pantheon`
      : route.product
      ? `${productThemeRecord.label}文章 | Pantheon`
      : "最新文章 | Pantheon";
  const description = buildDescription(route, article, section, intent, productThemeRecord);
  const updated = defaults.updated || new Date().toISOString().slice(0, 10);
  const author = defaults.author || "Pantheon 編輯部";
  const managedArticle = enforceArticlePolicy({
    section: article?.section || route.product,
    slug: route.slug,
    title,
    product: article?.product || route.product,
    primaryKeyword: article?.primaryKeyword || title,
    secondaryKeywords: article?.secondaryKeywords || [],
    tags: article?.tags || [],
  }, section);
  const productTheme = isLatestHub
    ? {
      label: "最新文章",
      glyph: "文",
      description: "Pantheon 最新文章入口，整理命盤、人格、塔羅、星座與人生方向主題。",
    }
    : getProductThemeRecord(managedArticle.productTheme);
  const displayTitle = route.slug
    ? title
    : route.intent
      ? `${intent?.label || route.intentLabel}文章`
      : route.product
        ? `${productTheme.label}文章`
        : "最新文章";
  return {
    title: displayTitle,
    pageTitle,
    description,
    canonicalPath,
    canonicalUrl: `${origin}${canonicalPath}`,
    product: managedArticle.product,
    productLabel: productTheme.label,
    productHref: route.product ? `/articles/${route.product}` : "/articles",
    section: managedArticle.section || "",
    productCrumb: route.product,
    productCrumbLabel: route.intent ? "搜尋意圖" : productTheme.label,
    slug: route.slug,
    author,
    updated,
    published: defaults.published || updated,
    sectionDescription: buildSectionDescription(route, section, intent, productTheme),
    productTheme: isLatestHub ? "latest" : managedArticle.productTheme,
    productThemeLabel: productTheme.label,
    productThemeGlyph: productTheme.glyph,
    productThemeDescription: productTheme.description,
    intent: route.intent || managedArticle.intent,
    keywords: managedArticle.keywords,
    tags: managedArticle.tags,
    answer: article?.answer || buildAnswer(route),
    bodySections: buildBodySections(route, article, section, intent, productTheme, managedArticle),
    faq: article?.faq || [
      {
        question: "這篇文章適合誰閱讀？",
        answer: "適合想先理解概念、再決定是否使用個人化工具的人。",
      },
      {
        question: "文章內容可以取代個人化解讀嗎？",
        answer: "不可以。公開文章負責解釋概念，個人化判斷仍需要回到你的資料與脈絡。",
      },
    ],
  };
}

function parseArticleRoute(pathname) {
  const segments = pathname.split("/").filter(Boolean);
  const [, productOrScope = "", slug = ""] = segments;
  const isIntentHub = productOrScope === "intents";
  const intent = isIntentHub ? slug : "";
  const legacySection = isIntentHub ? null : getArticleSectionRecord(productOrScope);
  const product = isIntentHub ? "" : legacySection?.product || productOrScope;
  return {
    product,
    productLabel: getProductThemeRecord(product).label,
    requestedSection: legacySection ? productOrScope : "",
    slug: isIntentHub ? "" : slug,
    intent,
    intentLabel: intent ? getLifeIntentRecord(intent)?.label || humanizeSlug(intent) : "",
    title: humanizeSlug(slug) || "文章",
  };
}

function buildDescription(route, article, section, intent, productTheme) {
  if (route.slug && article?.description) return article.description;
  if (route.slug) return `${route.title}：Pantheon 以繁體中文整理${productTheme.label}主題，提供清楚摘要、背景脈絡與延伸閱讀。`;
  if (route.intent) return `Pantheon ${intent?.label || route.intentLabel}文章主題入口，整理相關問題、產品脈絡與延伸閱讀。`;
  if (route.product) return section?.seoDescription || `Pantheon ${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "Pantheon 最新文章，整理命盤、人格、塔羅、星座與人生方向主題。";
}

function buildSectionDescription(route, section, intent, productTheme) {
  if (route.intent) return `${intent?.label || route.intentLabel}文章會作為搜尋意圖入口，再連回對應產品文章與工具。`;
  if (route.product && section?.description) return section.description;
  if (route.product) return `${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "最新文章入口，集中整理命盤、人格、塔羅、星座與人生方向主題。";
}

function buildAnswer(route) {
  if (route.slug) return `${route.title} 的重點會先用短摘要回答，再補充適用情境、限制與下一步閱讀。`;
  if (route.intent) return `${route.intentLabel}文章會先整理搜尋者真正想解決的問題，再連到相關產品內容。`;
  if (route.product) return `${route.productLabel}文章會先整理核心概念，再連到相關主題與個人化工具。`;
  return "最新文章會把命盤、人格、塔羅、星座與人生方向主題整理成可搜尋、可引用、可延伸的內容。";
}

function buildBodySections(route, article, section, intent, productTheme, managedArticle) {
  if (route.slug && article) {
    return buildArticleBody(article, productTheme, managedArticle);
  }
  if (route.intent) {
    const label = intent?.label || route.intentLabel;
    return [
      {
        heading: `${label}文章先看什麼？`,
        paragraphs: [
          `${label}相關搜尋通常不是只想看一個名詞，而是想知道現在遇到的問題可以從哪些角度理解。這個入口會整理人格、塔羅、命盤與星盤中和${label}有關的文章。`,
          "公開文章適合先建立概念、看常見問題與限制；如果要做個人化判斷，仍需要回到具體資料與情境。",
        ],
      },
    ];
  }
  if (route.product) {
    return [
      {
        heading: `${productTheme.label}文章怎麼讀？`,
        paragraphs: [
          section?.description || `${productTheme.label}文章會先整理常見概念，再補充使用限制與延伸閱讀。`,
          `建議先從「${section?.primaryKeyword || productTheme.label}」開始，再依照你真正想解決的問題往下閱讀。`,
        ],
      },
    ];
  }
  return [
    {
      heading: "最新文章怎麼使用？",
      paragraphs: [
        "最新文章頁整理 Pantheon 已公開的命盤、人格、塔羅、星座與人生方向內容，適合先用搜尋問題找到一篇可讀答案。",
        "公開文章只處理通用概念、適用情境與限制，不直接替任何人的人生、感情或工作下結論。",
      ],
    },
  ];
}

function buildArticleBody(article, productTheme, managedArticle) {
  const primary = article.primaryKeyword || article.title;
  const related = [primary, ...(article.secondaryKeywords || [])].slice(0, 4).join("、");
  const tagText = (article.originalTags?.length ? article.originalTags : managedArticle.tags).slice(0, 4).join("、");
  return [
    {
      heading: buildDefinitionHeading(primary),
      paragraphs: [
        article.answer,
        article.description,
      ],
    },
    {
      heading: `這篇文章會怎麼看 ${primary}？`,
      paragraphs: [
        `閱讀 ${primary} 時，先把它當成一個理解問題的入口，而不是最後答案。${productTheme.label}文章會先整理定義，再說明它通常能看什麼、不能直接代表什麼。`,
        `如果你是從「${related}」這類搜尋進來，建議先確認你要問的是概念定義、使用方式、關係判斷，還是想把它套到自己的情境。`,
      ],
    },
    {
      heading: "常見誤解",
      paragraphs: [
        buildMisunderstandingParagraph(article, productTheme),
        "公開文章可以幫你釐清語言與邏輯，但不應把單一名詞、牌義、宮位、星座或人格類型直接變成個人結論。",
      ],
    },
    {
      heading: "下一步可以讀什麼？",
      paragraphs: [
        tagText
          ? `你可以沿著 ${tagText} 這幾個主題繼續閱讀，先把相關概念串起來。`
          : `你可以沿著 ${productTheme.label} 的其他文章繼續閱讀，先把相關概念串起來。`,
        "如果你要的是個人化判斷，文章只能當作背景知識；真正套用到個人情境時，仍需要明確問題、資料與限制。",
      ],
    },
  ];
}

function buildDefinitionHeading(primary) {
  if (/[？?]$/.test(primary)) return primary;
  if (primary.includes("是什麼")) return primary;
  return `${primary}是什麼？`;
}

function buildMisunderstandingParagraph(article, productTheme) {
  if (article.product === "personality") return "人格類型適合描述偏好與互動模式，不適合拿來替一個人貼永久標籤，也不能取代心理診斷。";
  if (article.product === "tarot") return "塔羅牌義適合先理解象徵和提醒，但不能只看單張牌就斷定感情、工作或人生結果。";
  if (article.product === "astro") return "星盤與星座適合看傾向和主題，不能只用單一星座就推論一個人的完整樣貌。";
  if (article.product === "fortune") return "命盤、八字或紫微適合整理人生主題與節奏，不適合被說成固定命運或保證結果。";
  return `${productTheme.label}文章適合建立概念，但不能替代個人化判斷。`;
}

function humanizeSlug(value = "") {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

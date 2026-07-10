import {
  enforceArticlePolicy,
  getArticleRecord,
  getArticleSectionRecord,
  getLifeIntentRecord,
  getProductThemeRecord,
} from "./article-registry.js";

export function buildArticleContent(pathname, origin, defaults = {}) {
  const route = parseArticleRoute(pathname);
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
      : "文章 | Pantheon";
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
  const productTheme = getProductThemeRecord(managedArticle.productTheme);
  const displayTitle = route.slug
    ? title
    : route.intent
      ? `${intent?.label || route.intentLabel}文章`
      : route.product
        ? `${productTheme.label}文章`
        : "文章";
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
    productTheme: managedArticle.productTheme,
    productThemeLabel: productTheme.label,
    productThemeGlyph: productTheme.glyph,
    productThemeDescription: productTheme.description,
    intent: route.intent || managedArticle.intent,
    keywords: managedArticle.keywords,
    tags: managedArticle.tags,
    answer: article?.answer || buildAnswer(route),
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
  return "Pantheon 文章頁，整理命理、人格與人生決策主題。";
}

function buildSectionDescription(route, section, intent, productTheme) {
  if (route.intent) return `${intent?.label || route.intentLabel}文章會作為搜尋意圖入口，再連回對應產品文章與工具。`;
  if (route.product && section?.description) return section.description;
  if (route.product) return `${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "集中整理 Pantheon 的命理、人格、塔羅、星座與人生主題文章。";
}

function buildAnswer(route) {
  if (route.slug) return `${route.title} 的重點會先用短摘要回答，再補充適用情境、限制與下一步閱讀。`;
  if (route.intent) return `${route.intentLabel}文章會先整理搜尋者真正想解決的問題，再連到相關產品內容。`;
  if (route.product) return `${route.productLabel}文章會先整理核心概念，再連到相關主題與個人化工具。`;
  return "Pantheon 文章頁會把命理、人格與人生方向主題整理成可搜尋、可引用、可延伸的內容。";
}

function humanizeSlug(value = "") {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

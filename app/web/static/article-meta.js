import {
  enforceArticlePolicy,
  fallbackTopicLabel,
  getArticleRecord,
  getProductThemeRecord,
  getTopicRecord,
} from "./article-registry.js";

export function buildArticleContent(pathname, origin, defaults = {}) {
  const route = parseArticleRoute(pathname);
  const topic = getTopicRecord(route.category);
  const article = getArticleRecord(route.category, route.slug);
  const canonicalPath = route.category && route.slug
    ? `/articles/${route.category}/${route.slug}`
    : route.category
      ? `/articles/${route.category}`
      : "/articles";
  const title = article?.title || route.title;
  const pageTitle = route.slug
    ? `${title} | Pantheon`
    : route.category
      ? `${route.categoryLabel}文章 | Pantheon`
      : "文章 | Pantheon";
  const description = buildDescription(route, article, topic);
  const updated = defaults.updated || new Date().toISOString().slice(0, 10);
  const author = defaults.author || "Pantheon 編輯部";
  const managedArticle = enforceArticlePolicy({
    category: route.category,
    slug: route.slug,
    title,
    productTheme: article?.productTheme,
    primaryKeyword: article?.primaryKeyword || title,
    secondaryKeywords: article?.secondaryKeywords || [],
    tags: article?.tags || [],
  }, topic);
  const productTheme = getProductThemeRecord(managedArticle.productTheme);
  return {
    title: route.slug ? title : "文章",
    pageTitle,
    description,
    canonicalPath,
    canonicalUrl: `${origin}${canonicalPath}`,
    category: route.category,
    categoryLabel: route.categoryLabel,
    slug: route.slug,
    author,
    updated,
    published: defaults.published || updated,
    topicDescription: buildTopicDescription(route, topic),
    productTheme: managedArticle.productTheme,
    productThemeLabel: productTheme.label,
    productThemeGlyph: productTheme.glyph,
    productThemeDescription: productTheme.description,
    topicIntent: managedArticle.topicIntent,
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
  const [, category = "", slug = ""] = segments;
  return {
    category,
    categoryLabel: fallbackTopicLabel(category),
    slug,
    title: humanizeSlug(slug) || "文章",
  };
}

function buildDescription(route, article, topic) {
  if (route.slug && article?.description) return article.description;
  if (route.slug) return `${route.title}：Pantheon 以繁體中文整理${route.categoryLabel}主題，提供清楚摘要、背景脈絡與延伸閱讀。`;
  if (route.category) return topic?.seoDescription || `Pantheon ${route.categoryLabel}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "Pantheon 文章頁，整理命理、人格與人生決策主題。";
}

function buildTopicDescription(route, topic) {
  if (route.category && topic?.description) return topic.description;
  if (route.category) return `${route.categoryLabel}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "集中整理 Pantheon 的命理、人格、塔羅、星座與人生主題文章。";
}

function buildAnswer(route) {
  if (route.slug) return `${route.title} 的重點會先用短摘要回答，再補充適用情境、限制與下一步閱讀。`;
  if (route.category) return `${route.categoryLabel}文章會先整理核心概念，再連到相關主題與個人化工具。`;
  return "Pantheon 文章頁會把命理、人格與人生方向主題整理成可搜尋、可引用、可延伸的內容。";
}

function humanizeSlug(value = "") {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

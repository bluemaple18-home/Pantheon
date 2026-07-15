import { buildArticleContent } from "../../../../../app/web/static/article-meta.js";
import { writeFileSync } from "node:fs";
import {
  ARTICLE_SERIAL_REGISTRY,
  getArticlePath,
  listArticleRecords,
} from "../../../../../app/web/static/article-registry.js";
import { SECOND_BATCH_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-second-batch.js";
import { NEXT_30_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-next-30.js";
import { SCALE_44_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-scale-44.js";
import { buildArticleJsonLd, buildBreadcrumbJsonLd, buildFaqJsonLd } from "../../../../../app/web/static/article-seo.js";

const ORIGIN = "https://pantheon.example";

const bannedTerms = [
  "全面解析",
  "深度解析",
  "快速變化的時代",
  "不可或缺",
  "賦能",
  "不僅",
  "更是",
  "總而言之",
  "值得注意的是",
  "必看",
  "一定",
  "保證",
  "注定",
  "搜尋者通常不是",
  "站方",
  "入口",
  "標籤頁",
  "集結頁",
  "五大主題文章",
  "公開文章負責",
  "公開文章的任務",
  "小提醒",
  "獨立限制",
];

const boundaryTerms = [
  "不能",
  "不代表",
  "不是",
  "不等於",
  "不提供",
  "不能取代",
  "公開文章",
];

const scenarioTerms = [
  "感情",
  "工作",
  "人際",
  "財富",
  "人生方向",
  "關係",
  "溝通",
  "轉職",
  "創業",
  "安全感",
  "收入",
  "支出",
  "選擇",
  "等待",
  "曖昧",
  "復合",
];

const customLibraries = [
  ["second-batch", SECOND_BATCH_ARTICLE_BODY_LIBRARY],
  ["next-30", NEXT_30_ARTICLE_BODY_LIBRARY],
  ["scale-44", SCALE_44_ARTICLE_BODY_LIBRARY],
];

function classifyArticle(article) {
  if (article.id.startsWith("TAROT-")) return "tarot";
  if (article.id.startsWith("MBTI-")) return "personality";
  if (article.id.startsWith("CHART-")) return "fortune";
  if (article.id.startsWith("ASTRO-")) return "astrology";
  if (article.id.startsWith("THEME-")) return "scenario";
  return article.product || article.section || "unknown";
}

function classifyTemplate(article) {
  if (article.id.includes("-BASE-")) return "foundation";
  if (article.id.startsWith("TAROT-M")) return "single-major-card";
  if (article.id.startsWith("TAROT-")) return "single-minor-card";
  if (article.id.startsWith("MBTI-TYPE-")) return "single-personality-type";
  if (article.id.startsWith("CHART-ZIWEI-")) return "single-palace";
  if (article.id.startsWith("ASTRO-")) return "astrology-topic";
  if (article.id.startsWith("THEME-")) return "life-scenario";
  return "standard-article";
}

function libraryForSlug(slug) {
  const hit = customLibraries.find(([, library]) => Object.hasOwn(library, slug));
  return hit ? hit[0] : "fallback-runtime";
}

function normalizeKeyword(value) {
  return String(value || "")
    .replace(/是什麼/g, "")
    .replace(/怎麼看/g, "")
    .replace(/[？?：:、，,。]/g, "")
    .trim();
}

function renderedText(content) {
  return [
    content.title,
    content.answer,
    ...content.bodySections.flatMap((section) => [
      section.heading,
      ...(section.paragraphs || []),
    ]),
    ...content.faq.flatMap((item) => [item.question, item.answer]),
  ].join("\n");
}

function compact(value) {
  return String(value || "").replace(/\s+/g, "");
}

function checkArticle(article) {
  const path = getArticlePath(article);
  const content = buildArticleContent(path, ORIGIN);
  const text = renderedText(content);
  const firstParagraph = content.bodySections[0]?.paragraphs?.[0] || "";
  const first80 = firstParagraph.slice(0, 80);
  const keywordRoot = normalizeKeyword(article.primaryKeyword);
  const jsonLdTypes = [
    buildArticleJsonLd(content, ORIGIN)?.["@type"],
    buildFaqJsonLd(content)?.["@type"],
    buildBreadcrumbJsonLd(content, ORIGIN)?.["@type"],
  ];
  const blockers = [];
  const warnings = [];

  const hits = bannedTerms.filter((term) => text.includes(term));
  if (hits.length) blockers.push(`banned/template terms: ${hits.join(", ")}`);
  if (!content.title.includes(article.primaryKeyword)) blockers.push("H1/title missing primary keyword");
  if (keywordRoot && !compact(first80).includes(compact(keywordRoot))) {
    warnings.push("first 80 chars use natural wording instead of exact primary keyword");
  }
  if (!content.answer || content.answer.length > 50) blockers.push("answer missing or over 50 chars");
  if (content.faq.length < 3 || content.faq.length > 5) blockers.push(`FAQ count ${content.faq.length}`);
  if (!content.updated) blockers.push("updated date missing");
  if (content.canonicalPath !== path || content.canonicalUrl !== `${ORIGIN}${path}`) {
    blockers.push("canonical mismatch");
  }
  if (jsonLdTypes.join("|") !== "Article|FAQPage|BreadcrumbList") {
    blockers.push(`schema mismatch: ${jsonLdTypes.join("|")}`);
  }
  if (!boundaryTerms.some((term) => text.includes(term))) blockers.push("missing explicit boundary language");
  if (!scenarioTerms.some((term) => text.includes(term))) warnings.push("few concrete life-scenario markers");
  if (content.relatedLinks.length < 3) warnings.push(`related links ${content.relatedLinks.length}`);
  if (content.navigationLinks.filter(Boolean).length < 1) warnings.push("no previous/next navigation link");

  return {
    status: blockers.length ? "BLOCKER" : warnings.length ? "WARNING" : "PASS",
    id: article.id,
    serial: article.serial || ARTICLE_SERIAL_REGISTRY[article.id] || "",
    slug: content.slug,
    path,
    type: classifyArticle(article),
    template: classifyTemplate(article),
    bodyLibrary: libraryForSlug(article.slug),
    sections: content.bodySections.length,
    faq: content.faq.length,
    relatedLinks: content.relatedLinks.length,
    navigationLinks: content.navigationLinks.filter(Boolean).length,
    updated: content.updated,
    canonical: content.canonicalPath,
    blockers,
    warnings,
  };
}

const results = listArticleRecords()
  .sort((a, b) => String(a.serial).localeCompare(String(b.serial)))
  .map(checkArticle);

const summary = results.reduce((acc, row) => {
  acc[row.status] = (acc[row.status] || 0) + 1;
  return acc;
}, { PASS: 0, WARNING: 0, BLOCKER: 0 });

const payload = { generatedAt: new Date().toISOString(), summary, results };
const outputArg = process.argv.find((arg) => arg.startsWith("--output="));
if (outputArg) {
  writeFileSync(outputArg.slice("--output=".length), `${JSON.stringify(payload, null, 2)}\n`);
}
const consolePayload = outputArg
  ? {
      generatedAt: payload.generatedAt,
      summary,
      nonPass: results.filter((row) => row.status !== "PASS"),
    }
  : payload;
console.log(JSON.stringify(consolePayload, null, 2));

if (summary.BLOCKER > 0) process.exitCode = 1;

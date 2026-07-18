import fs from "node:fs";
import path from "node:path";

import { buildArticleContent } from "../../../../../app/web/static/article-meta.js";
import { getArticlePath, listArticleRecords } from "../../../../../app/web/static/article-registry.js";
import { INITIAL_31_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-initial-31.js";
import { SECOND_BATCH_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-second-batch.js";
import { NEXT_30_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-next-30.js";
import { SCALE_44_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-scale-44.js";
import { TAROT_COMPLETION_4_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-bodies-tarot-completion-4.js";
import { TAROT_CARD_FACE_50_LIBRARY } from "../../../../../app/web/static/article-card-face-50.js";
import { EXPANSION_50_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50.js";
import { EXPANSION_50C_MBTI_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50c-mbti.js";
import { EXPANSION_50C_ASTRO_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50c-astro.js";
import { EXPANSION_50C_FORTUNE_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50c-fortune.js";
import { EXPANSION_50D_MBTI_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50d-mbti.js";
import { EXPANSION_50D_ASTRO_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50d-astro.js";
import { EXPANSION_50D_FORTUNE_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-50d-fortune.js";
import { AGY_PROTOTYPE_V1_01_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-agy-prototype-v1-01.js";
import { AGY_MATRIX_BACKLOG_V1_01_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-agy-matrix-backlog-v1-01.js";
import { AGY_MATRIX_BACKLOG_V1_RETRY_01_ARTICLE_BODY_LIBRARY } from "../../../../../app/web/static/article-expansion-agy-matrix-backlog-v1-retry-01.js";

const outDir = path.dirname(new URL(import.meta.url).pathname);
const origin = "https://pantheon.local";

const bodyLibraries = [
  ["app/web/static/article-expansion-agy-matrix-backlog-v1-retry-01.js", AGY_MATRIX_BACKLOG_V1_RETRY_01_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-agy-matrix-backlog-v1-01.js", AGY_MATRIX_BACKLOG_V1_01_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-agy-prototype-v1-01.js", AGY_PROTOTYPE_V1_01_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-bodies-second-batch.js", SECOND_BATCH_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-bodies-next-30.js", NEXT_30_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-bodies-scale-44.js", SCALE_44_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-bodies-tarot-completion-4.js", TAROT_COMPLETION_4_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50.js", EXPANSION_50_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50c-mbti.js", EXPANSION_50C_MBTI_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50c-astro.js", EXPANSION_50C_ASTRO_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50c-fortune.js", EXPANSION_50C_FORTUNE_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50d-mbti.js", EXPANSION_50D_MBTI_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50d-astro.js", EXPANSION_50D_ASTRO_ARTICLE_BODY_LIBRARY],
  ["app/web/static/article-expansion-50d-fortune.js", EXPANSION_50D_FORTUNE_ARTICLE_BODY_LIBRARY],
];

const bannedPhrases = [
  "全面解析", "深度解析", "快速變化的時代", "不可或缺", "賦能", "不僅", "更是",
  "總而言之", "值得注意的是", "必看", "一定", "保證", "注定",
  "通常不是想背牌義", "不能替任何人下結論", "正位不等於好消息",
];

const templatePatterns = [
  ["GENERIC_QUESTION_OPENING", /真正要整理的是什麼？/u],
  ["GENERIC_OBSERVABLE_SECTION", /有哪些可觀察線索？/u],
  ["GENERIC_NEXT_STEP", /變成下一步/u],
  ["GENERIC_BOUNDARY_HEADING", /不能代表什麼？/u],
  ["REPEATED_CORE_NOT_INSTANT", /核心不是找一句立刻生效的答案/u],
  ["REPEATED_PUBLIC_ARTICLE_FRAME", /這篇.+公開文章能提供整理框架與常見線索/u],
  ["FALLBACK_SELF_QUESTION", /如果你想把 .+ 放回自己的狀況/u],
];

const concreteSignals = [
  "等", "問", "談", "寫", "記錄", "確認", "核對", "拒絕", "停下", "收尾", "試做",
  "回覆", "分工", "現金流", "訊息", "主管", "伴侶", "朋友", "合約", "履歷", "租約",
  "睡眠", "收入", "支出", "期限", "會議", "作品", "家庭", "同事",
];

function bodySourceFor(article) {
  const hits = [];
  for (const [file, library] of bodyLibraries) {
    if (library[article.slug]) hits.push(file);
  }
  if (TAROT_CARD_FACE_50_LIBRARY[article.slug]) hits.push("app/web/static/article-card-face-50.js");
  return hits.length ? hits.join(" + ") : "app/web/static/article-meta.js::fallback-or-inline";
}

function textFromContent(content) {
  const parts = [];
  for (const section of content.bodySections || []) {
    if (section.heading) parts.push(section.heading);
    for (const paragraph of section.paragraphs || []) parts.push(paragraph);
  }
  for (const faq of content.faq || []) {
    parts.push(faq.question || "");
    parts.push(faq.answer || "");
  }
  return parts.filter(Boolean).join("\n");
}

function countOccurrences(text, needle) {
  if (!needle) return 0;
  return text.split(needle).length - 1;
}

function issueScan(article, content, body) {
  const issues = [];
  const evidence = [];
  const headings = (content.bodySections || []).map((section) => section.heading || "");
  const paragraphs = (content.bodySections || []).flatMap((section) => section.paragraphs || []);
  const faq = content.faq || [];
  const charCount = body.length;
  const uniqueBodyRatio = new Set(body.split(/[，。；：！？\n\s]+/u).filter((x) => x.length > 1)).size / Math.max(1, body.length / 18);
  const concreteCount = concreteSignals.reduce((sum, token) => sum + countOccurrences(body, token), 0);
  const bannedHits = bannedPhrases.filter((phrase) => body.includes(phrase));
  const templateHits = templatePatterns.filter(([, pattern]) => pattern.test(body)).map(([code]) => code);

  if (!paragraphs.length || charCount < 500) {
    issues.push("BODY_MISSING_OR_TOO_THIN");
    evidence.push(`正文段落不足或過短：${paragraphs.length} 段，${charCount} 字。`);
  } else if (charCount < 900) {
    issues.push("SHORT_BODY");
    evidence.push(`正文僅 ${charCount} 字，低於基礎概念文建議長度。`);
  }

  if (bannedHits.length) {
    issues.push("BANNED_PHRASE");
    evidence.push(`「${article.primaryKeyword || article.title}」正文命中禁用或舊模板詞：${bannedHits.slice(0, 3).join("、")}。`);
  }
  if (templateHits.length >= 3) {
    issues.push("TEMPLATE_STRUCTURE");
    evidence.push(`「${article.primaryKeyword || article.title}」正文小標高度模板化，實際小標包含「${headings.slice(0, 4).join("」、「")}」。`);
  }
  if (templateHits.includes("REPEATED_CORE_NOT_INSTANT") || templateHits.includes("REPEATED_PUBLIC_ARTICLE_FRAME")) {
    issues.push("REPEATED_BATCH_COPY");
    evidence.push(`「${article.primaryKeyword || article.title}」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。`);
  }
  if (concreteCount < 7) {
    issues.push("LOW_SCENARIO_DENSITY");
    evidence.push(`具體情境/可觀察動詞密度偏低，偵測到 ${concreteCount} 個具體訊號。`);
  }
  if (!/不能|不代表|不適合|無法|不得/u.test(body)) {
    issues.push("MISSING_BOUNDARY");
    evidence.push("正文缺少清楚的公開文章邊界或不能代表什麼。");
  }
  if (faq.length < 3) {
    issues.push("FAQ_TOO_THIN");
    evidence.push(`FAQ 僅 ${faq.length} 題，未達 3 到 5 題規範。`);
  }
  if (headings.length < 3) {
    issues.push("STRUCTURE_TOO_THIN");
    evidence.push(`正文只有 ${headings.length} 個段落區塊，掃讀結構不足。`);
  }
  if (uniqueBodyRatio < 0.48 && charCount > 800) {
    issues.push("LOW_UNIQUE_LANGUAGE");
    evidence.push("詞彙重複度偏高，容易讀成同一模板替換關鍵字。");
  }
  if (article.primaryKeyword && !body.slice(0, 130).includes(article.primaryKeyword)) {
    issues.push("SEARCH_INTENT_LAG");
    evidence.push(`主關鍵字「${article.primaryKeyword}」未在正文前 130 字內自然回答。`);
  }

  return { issues: [...new Set(issues)], evidence: evidence.slice(0, 5), charCount };
}

function classify(article, content, body, scan) {
  if (scan.issues.includes("BODY_MISSING_OR_TOO_THIN")) return ["BLOCKED", "P0"];
  const severe = new Set(["TEMPLATE_STRUCTURE", "REPEATED_BATCH_COPY", "SEARCH_INTENT_LAG"]);
  const severeCount = scan.issues.filter((issue) => severe.has(issue)).length;
  if (severeCount >= 2 || (severeCount >= 1 && scan.issues.includes("SHORT_BODY"))) return ["GEMINI_REWRITE", "P0"];
  if (article.id.startsWith("THEME-") && scan.issues.includes("REPEATED_BATCH_COPY")) return ["GEMINI_REWRITE", "P1"];
  if (scan.issues.includes("TEMPLATE_STRUCTURE") && scan.issues.includes("LOW_SCENARIO_DENSITY")) return ["GEMINI_REWRITE", "P1"];
  if (scan.issues.length >= 3) return ["LIGHT_EDIT", "P1"];
  if (scan.issues.length) return ["LIGHT_EDIT", "P2"];
  return ["KEEP", "P3"];
}

function geminiBatch(verdict, priority, article) {
  if (verdict !== "GEMINI_REWRITE") return "";
  return priority;
}

function serialInfo(article) {
  const value = article.urlSlug || article.serial || article.slug || "";
  const match = String(value).match(/^(.+)-(\d{4})$/u);
  return {
    serial: match ? value : (article.serial || value),
    serialCategory: match ? match[1] : (article.articleCategory || article.product || ""),
    serialNumber: match ? Number(match[2]) : Number.MAX_SAFE_INTEGER,
  };
}

function globalSerialCompare(a, b) {
  return a.serialNumber - b.serialNumber
    || a.product.localeCompare(b.product)
    || a.articleCategory.localeCompare(b.articleCategory)
    || a.id.localeCompare(b.id)
    || a.slug.localeCompare(b.slug);
}

function queueCompare(a, b) {
  return a.priority.localeCompare(b.priority)
    || a.serialNumber - b.serialNumber
    || a.product.localeCompare(b.product)
    || a.articleCategory.localeCompare(b.articleCategory)
    || a.id.localeCompare(b.id)
    || a.slug.localeCompare(b.slug);
}

function chunk(values, size) {
  const groups = [];
  for (let index = 0; index < values.length; index += size) groups.push(values.slice(index, index + size));
  return groups;
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n]/u.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function issueSummary(rows) {
  const counts = new Map();
  rows.forEach((row) => row.issue_codes.split("|").filter(Boolean).forEach((code) => counts.set(code, (counts.get(code) || 0) + 1)));
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function briefFor(row) {
  return [
    `保留 id=${row.id}、product=${row.product}、slug=${row.slug}、title=${row.title}、primaryKeyword=${row.primaryKeyword}，不得改 URL/serial/date/metadata。`,
    `重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「${row.primaryKeyword || row.title}」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。`,
    `專屬證據：${row.reason}`,
  ];
}

const recordsRaw = listArticleRecords();
const recordsForScan = [...recordsRaw].sort((a, b) => {
  const left = { ...a, ...serialInfo(a), articleCategory: a.articleCategory || a.product || "", product: a.product || "" };
  const right = { ...b, ...serialInfo(b), articleCategory: b.articleCategory || b.product || "", product: b.product || "" };
  return globalSerialCompare(left, right);
});
const rows = [];
const seen = new Set();
const duplicates = [];
const missingBody = [];

for (const article of recordsForScan) {
  const serial = serialInfo(article);
  const key = `${article.id}|${article.product}|${article.urlSlug || article.slug}`;
  if (seen.has(key)) {
    duplicates.push(key);
    continue;
  }
  seen.add(key);
  const sourcePath = getArticlePath(article);
  const content = buildArticleContent(sourcePath, origin);
  const body = textFromContent(content);
  const scan = issueScan(article, content, body);
  if (!body.trim()) missingBody.push(key);
  const [verdict, priority] = classify(article, content, body, scan);
  rows.push({
    id: article.id,
    product: article.product || "",
    articleCategory: article.articleCategory || article.product || "",
    serial: serial.serial,
    serialCategory: serial.serialCategory,
    serialNumber: serial.serialNumber,
    slug: article.urlSlug || article.slug,
    source_file: "app/web/static/article-registry.js",
    body_source: bodySourceFor(article),
    title: article.title,
    primaryKeyword: article.primaryKeyword || "",
    char_count: scan.charCount,
    verdict,
    priority,
    issue_codes: scan.issues.join("|"),
    reason: `${bodySourceFor(article)}，正文 ${scan.charCount} 字。 ${scan.evidence.join(" ")}`,
    gemini_batch: geminiBatch(verdict, priority, article),
  });
}

rows.sort(globalSerialCompare);

const geminiRows = rows.filter((row) => row.verdict === "GEMINI_REWRITE").sort(queueCompare);
const geminiBatches = chunk(geminiRows, 5);
geminiBatches.forEach((batch, index) => {
  const label = `batch-${String(index + 1).padStart(2, "0")}`;
  batch.forEach((row) => {
    row.gemini_batch = `${row.priority}-${label}`;
  });
});

const csvHeader = ["id", "product", "slug", "serial", "title", "source_file", "body_source", "char_count", "verdict", "priority", "issue_codes", "reason", "gemini_batch"];
const csv = [
  csvHeader.join(","),
  ...rows.map((row) => csvHeader.map((key) => csvEscape(row[key])).join(",")),
].join("\n") + "\n";

const verdictCounts = rows.reduce((acc, row) => {
  acc[row.verdict] = (acc[row.verdict] || 0) + 1;
  return acc;
}, {});
const priorityCounts = rows.filter((row) => row.verdict === "GEMINI_REWRITE").reduce((acc, row) => {
  acc[row.priority] = (acc[row.priority] || 0) + 1;
  return acc;
}, {});
const issueCounts = issueSummary(rows);
const audit = `# CARD-CONTENT-GEMINI-REWRITE-AUDIT-001

## 總覽

- Runtime registry 原始列數：${recordsRaw.length}
- 以 \`id + product + slug\` 去重後 inventory：${rows.length}
- 全量掃描與 inventory 排序：全域 serial 尾碼數字升冪，再以 product/category 與 id 作為 tie-breaker。
- 後續 Gemini rewrite queue 排序：priority → serial 尾碼數字 → product/category → id。
- **後續 Gemini Rewrite Batch 1 從最小流水號且 verdict=GEMINI_REWRITE 的文章開始：${geminiRows[0]?.id || "none"} / ${geminiRows[0]?.serial || "none"}。**
- KEEP：${verdictCounts.KEEP || 0}
- LIGHT_EDIT：${verdictCounts.LIGHT_EDIT || 0}
- GEMINI_REWRITE：${verdictCounts.GEMINI_REWRITE || 0}
- BLOCKED：${verdictCounts.BLOCKED || 0}

## 判定準則

- KEEP：正文具體、能回答搜尋意圖、保留邊界，未命中明顯模板或禁用句。
- LIGHT_EDIT：局部可修，例如 FAQ、導言、主關鍵字位置或少量模板句。
- GEMINI_REWRITE：同時有模板結構、批次固定句型、正文過短、搜尋意圖延遲或情境密度不足，全文重寫比局部修補更划算。
- BLOCKED：runtime 有 registry record 但正文缺失、過薄或 body 解析失敗。

## Verdict 分布

| Verdict | Count |
|---|---:|
| KEEP | ${verdictCounts.KEEP || 0} |
| LIGHT_EDIT | ${verdictCounts.LIGHT_EDIT || 0} |
| GEMINI_REWRITE | ${verdictCounts.GEMINI_REWRITE || 0} |
| BLOCKED | ${verdictCounts.BLOCKED || 0} |

## 問題分布

| Issue code | Count |
|---|---:|
${issueCounts.map(([code, count]) => `| ${code} | ${count} |`).join("\n")}

## Gemini 優先批次

| Priority | Count |
|---|---:|
| P0 | ${priorityCounts.P0 || 0} |
| P1 | ${priorityCounts.P1 || 0} |
| P2 | ${priorityCounts.P2 || 0} |

Queue batch size：每批最多 5 篇；Batch 1 取全域排序前 5 篇，第一篇必須是所有 GEMINI_REWRITE 中流水號數字最小者。

## 代表案例

${geminiRows.slice(0, 12).map((row) => `- ${row.gemini_batch} ${row.id} / ${row.serial}：${row.reason}`).join("\n")}

## 結論

本卡只完成盤點、判定與 Gemini 改寫佇列；未改寫任何正式文章，也未呼叫 Gemini 或外部寫入服務。
`;

const queueGroups = geminiBatches.map((group, index) => {
  const first = group[0];
  const title = `## Batch ${index + 1} | ${first?.gemini_batch || "empty"}`;
  const pipelineBrief = {
    schema_version: 1,
    run_id: `gemini_rewrite_audit_001_batch_${String(index + 1).padStart(2, "0")}`,
    mode: "rewrite_existing_body",
    sort_contract: "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
    articles: group.map((row, slotIndex) => ({
      slot: `article-${String(slotIndex + 1).padStart(2, "0")}`,
      article_id: row.id,
      product: row.product,
      category: row.articleCategory,
      serial: row.serial,
      slug: row.slug,
      source_file: row.source_file,
      body_source: row.body_source,
      primaryKeyword: row.primaryKeyword,
      title: row.title,
      verdict: row.verdict,
      issue_codes: row.issue_codes.split("|").filter(Boolean),
      brief: briefFor(row),
    })),
  };
  return `${title}

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。${index === 0 ? `Batch 1 第一篇為所有 GEMINI_REWRITE 中流水號數字最小者：${first.id} / ${first.serial}。` : ""}

可供 pipeline 包裝使用的 public brief：

\`\`\`json
${JSON.stringify(pipelineBrief, null, 2)}
\`\`\`

${group.map((row) => `### ${row.id} | ${row.serial} | ${row.title}\n\n- 不可變更欄位：product=${row.product}; category=${row.articleCategory}; serial=${row.serial}; slug=${row.slug}; source_file=${row.source_file}; body_source=${row.body_source}\n- Gemini batch：${row.gemini_batch}\n- 改寫 brief：\n${briefFor(row).map((line) => `  - ${line}`).join("\n")}`).join("\n\n")}`;
}).join("\n\n");

const queue = `# Gemini Rewrite Queue

只列 \`GEMINI_REWRITE\`，不執行改寫。

排序契約：後續 Gemini 改寫必須從流水號數字最小的舊文章開始；queue 使用 \`priority -> serial 尾碼數字 -> product/category -> id\`。Batch 1 取此全域順序前 5 篇，第一篇必須是所有 \`GEMINI_REWRITE\` 中流水號數字最小者。

${queueGroups}
`;

const verdictSum = Object.values(verdictCounts).reduce((a, b) => a + b, 0);
const verification = `registry_raw_count=${recordsRaw.length}
inventory_unique_count=${rows.length}
verdict_sum=${verdictSum}
duplicates=${duplicates.length}
duplicate_keys=${duplicates.join(";") || "none"}
missing_body=${missingBody.length}
missing_body_keys=${missingBody.join(";") || "none"}
gemini_rewrite_count=${geminiRows.length}
gemini_batch_count=${geminiBatches.length}
gemini_batch_size=5
gemini_batch_1_first=${geminiRows[0]?.id || "none"}|${geminiRows[0]?.serial || "none"}
gemini_queue_sort=priority_then_serial_suffix_number_ascending_then_product_category_then_id
gemini_rewrite_with_two_reasons=${geminiRows.filter((row) => row.reason.split("。").filter(Boolean).length >= 2).length}
coverage_ok=${recordsRaw.length - duplicates.length === rows.length}
verdict_sum_ok=${verdictSum === rows.length}
gemini_reason_ok=${geminiRows.every((row) => row.reason.split("。").filter(Boolean).length >= 2)}
reproduce=node artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/audit_runtime_articles.mjs
`;

fs.writeFileSync(path.join(outDir, "inventory.csv"), csv);
fs.writeFileSync(path.join(outDir, "audit.md"), audit);
fs.writeFileSync(path.join(outDir, "gemini_queue.md"), queue);
fs.writeFileSync(path.join(outDir, "verification.txt"), verification);

console.log(verification);

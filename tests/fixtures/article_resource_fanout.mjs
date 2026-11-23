import fs from "node:fs";
import vm from "node:vm";
import { pathToFileURL } from "node:url";

const input = JSON.parse(fs.readFileSync(0, "utf8"));
if (input.mode === "registry") {
  let buildCalls = 0;
  let records;
  const context = vm.createContext({ console: { log: (value) => { records = JSON.parse(value); } } });
  const inputRecords = [
    { id: "A", product: "personality", serial: "personality-0001", title: "A" },
    { id: "B", product: "tarot", serial: "tarot-0001", title: "B" },
  ];
  const registry = new vm.SyntheticModule(["listArticleRecords", "getArticlePath", "getArticleSectionRecord"], function () {
    this.setExport("listArticleRecords", () => inputRecords);
    this.setExport("getArticlePath", (record) => `/articles/${record.product}/${record.serial}`);
    this.setExport("getArticleSectionRecord", () => ({ label: "測試", product: "personality" }));
  }, { context });
  const meta = new vm.SyntheticModule(["buildArticleContent"], function () {
    this.setExport("buildArticleContent", (path) => {
      buildCalls += 1;
      return { canonicalPath: path, title: path, answer: "答案", faq: [], bodySections: [{ heading: "段落", paragraphs: ["正文"] }] };
    });
  }, { context });
  const module = new vm.SourceTextModule(input.source, { context });
  await module.link((specifier) => specifier.includes("article-registry.js") ? registry : meta);
  await module.evaluate();
  process.stdout.write(JSON.stringify({ buildCalls, records }));
  process.exit(0);
}
if (input.locale) {
  const { listArticleLocaleRecords } = await import("../../app/web/static/article-locales.js");
  const record = listArticleLocaleRecords().find((item) => item.locale === input.locale
    && item.sourcePath && item.title && item.answer && item.bodySections?.length);
  if (!record) throw new Error(`缺少 ${input.locale} 的真實語系樣本`);
  input.path = `/${input.locale}${record.sourcePath}`;
}

const legacyImports = [];
const node = input.payload === null ? null : {
  textContent: typeof input.payload === "string" ? input.payload : JSON.stringify(input.payload),
};
const defaults = { author: "Pantheon 編輯部" };
const context = vm.createContext({
  document: {
    getElementById: () => node,
    querySelector: (selector) => selector === "[data-article-author]" ? { textContent: defaults.author } : null,
  },
  window: { location: { pathname: input.path, origin: input.origin } },
});
const importLegacy = async (specifier, referencingModule) => {
  legacyImports.push(specifier);
  return import(new URL(specifier, referencingModule.identifier));
};
const loaderUrl = pathToFileURL(`${process.cwd()}/app/web/static/article-content-loader.js`);
const loader = new vm.SourceTextModule(fs.readFileSync(loaderUrl, "utf8"), {
  context,
  identifier: loaderUrl.href,
  importModuleDynamically: importLegacy,
});
await loader.link(() => { throw new Error("輕量 loader 不應有靜態依賴"); });
await loader.evaluate();
// 執行真正入口以取得它傳入的 callback；此處只攔截 hydration，不模擬瀏覽器 DOM。
let entryArgs;
const entryUrl = pathToFileURL(`${process.cwd()}/app/web/static/article.js`);
const entry = new vm.SourceTextModule(fs.readFileSync(entryUrl, "utf8"), {
  context,
  identifier: entryUrl.href,
  importModuleDynamically: importLegacy,
});
await entry.link((specifier) => {
  if (specifier.startsWith("./article-content-loader.js?")) {
    return new vm.SyntheticModule(["loadArticleContent"], function () {
      this.setExport("loadArticleContent", (...args) => { entryArgs = args; return null; });
    }, { context });
  }
  if (specifier.startsWith("./article-seo.js?")) {
    return new vm.SyntheticModule(["applyArticleSeo"], function () {
      this.setExport("applyArticleSeo", () => {});
    }, { context });
  }
  throw new Error(`入口出現非預期靜態依賴：${specifier}`);
});
await entry.evaluate();
const actual = await loader.namespace.loadArticleContent(...entryArgs);
const result = { actual, legacyImports };
if (input.locale) result.path = input.path;
if (input.compare) {
  const { buildArticleContent } = await import("../../app/web/static/article-meta.js");
  const { buildArticleJsonLd, buildBreadcrumbJsonLd, buildFaqJsonLd } = await import("../../app/web/static/article-seo.js");
  result.expected = buildArticleContent(input.path, input.origin, defaults);
  if (actual && !actual.redirectTo) {
    const seo = (content) => ({
      article: buildArticleJsonLd(content, input.origin),
      breadcrumb: buildBreadcrumbJsonLd(content, input.origin),
      faq: buildFaqJsonLd(content),
    });
    result.actualSeo = seo(actual);
    result.expectedSeo = seo(result.expected);
  }
}
console.log(JSON.stringify(result));

import fs from "node:fs";
import vm from "node:vm";
import { pathToFileURL } from "node:url";

const input = JSON.parse(fs.readFileSync(0, "utf8"));
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

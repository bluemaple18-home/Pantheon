export async function loadArticleContent(pathname, origin, defaults = {}, loadLegacy) {
  const node = document.getElementById("article-content-payload");
  if (!node) {
    const { buildArticleContent } = await loadLegacy();
    return buildArticleContent(pathname, origin, defaults);
  }

  // 有 payload 卻無法使用時保留預渲染 HTML，不回退下載全站文章資料。
  try {
    const payload = JSON.parse(node.textContent);
    const route = pathname.replace(/\/+$/, "") || "/";
    const content = payload?.content;
    if (payload?.path !== route || content?.canonicalPath !== route
      || content.contentType !== "Article" || typeof content.title !== "string"
      || !Array.isArray(content.bodySections) || !Array.isArray(content.keywords)) {
      return null;
    }
    return { ...content, canonicalUrl: `${origin}${content.canonicalPath}` };
  } catch {
    return null;
  }
}

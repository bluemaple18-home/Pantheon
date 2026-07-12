const SITE_ORIGIN = "https://mysticpantheon.com";
const ARTICLE_PUBLISHED_DATE = "2026-07-10";
const ARTICLE_UPDATED_DATE = "2026-07-12";

const STATIC_REDIRECTS = new Map([
  ["/", "/articles"],
  ["/reading", "/articles"],
  ["/personality", "/articles"],
  ["/effects-demo", "/articles"],
  ["/strategy", "/articles"],
  ["/index.html", "/articles"],
  ["/personality.html", "/articles"],
  ["/effects-demo.html", "/articles"],
  ["/strategy.html", "/articles"],
  ["/articles/astro/12-zodiac-signs", "/articles/astro"],
]);

const PRODUCT_META = {
  fortune: ["命盤文章", "Pantheon 命盤文章，整理八字、紫微斗數、命宮、財帛宮與人生節奏主題。"],
  personality: ["人格文章", "Pantheon 人格文章，整理 MBTI、16 型人格、人際模式與自我理解主題。"],
  tarot: ["塔羅文章", "Pantheon 塔羅文章，整理塔羅牌意思、正位逆位、感情、工作與人生方向主題。"],
  astro: ["星座文章", "Pantheon 星座文章，整理星盤、太陽星座、月亮星座、上升星座與情緒安全感主題。"],
  astrology: ["星座文章", "Pantheon 星座文章，整理星盤、太陽星座、月亮星座、上升星座與情緒安全感主題。"],
  love: ["感情文章", "Pantheon 感情文章，整理曖昧、復合、安全感、關係卡住與相處模式主題。"],
  career: ["事業文章", "Pantheon 事業文章，整理轉職、工作壓力、努力未被看見與職涯方向主題。"],
  interpersonal: ["人際文章", "Pantheon 人際文章，整理人際關係、互動界線、溝通模式與社交疲憊主題。"],
  wealth: ["財富文章", "Pantheon 財富文章，整理存錢、資源分配、安全感與財富習慣主題。"],
  "life-direction": ["人生方向文章", "Pantheon 人生方向文章，整理迷惘、選擇、自我理解與長期方向主題。"],
};

const RAW_ARTICLE_META = {
  "/articles/tarot/tarot-0001": [
    "塔羅牌意思總覽：78 張牌、正位逆位與情境怎麼看",
    "整理塔羅牌意思、正位逆位、感情與工作情境，並保留公開文章不能取代個人判讀的限制。",
  ],
  "/articles/personality/personality-0001": [
    "MBTI 是什麼？16 型人格、測驗與自我理解怎麼看",
    "說明 MBTI、16 型人格與測驗使用邊界，協助讀者把人格偏好放回感情、工作與人際情境。",
  ],
  "/articles/fortune/fortune-0001": [
    "命盤是什麼？八字、紫微斗數和星盤差在哪",
    "白話整理命盤、八字、紫微斗數與星盤的差異，避免把單一工具寫成完整個人結論。",
  ],
  "/articles/interpersonal/interpersonal-0001": [
    "人際關係卡住怎麼辦？人格、塔羅與命盤可以看什麼",
    "整理人際關係、互動界線與溝通模式，先釐清情境，再連到人格、命盤與塔羅脈絡。",
  ],
  "/articles/life-direction": [
    "人生方向迷惘怎麼辦？塔羅、人格與命盤能幫你整理什麼",
    "人生方向迷惘時，先分清感情、事業、人際、財富或自我節奏哪裡最卡，再選擇適合的整理工具。",
  ],
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function productLabel(product) {
  return (PRODUCT_META[product] || ["最新文章", ""])[0];
}

function rawArticleMeta(pathname) {
  let title;
  let description;
  let product = "";
  let contentType = "Article";

  if (RAW_ARTICLE_META[pathname]) {
    [title, description] = RAW_ARTICLE_META[pathname];
    product = pathname.startsWith("/articles/") ? pathname.split("/")[2] : "";
  } else if (pathname.startsWith("/topics/")) {
    const topic = pathname.split("/").pop().replaceAll("-", " ");
    title = `${topic} 相關文章`;
    description = `Pantheon 主題頁，整理與 ${topic} 相關的公開文章、常見問題與延伸閱讀。`;
    product = "topics";
    contentType = "CollectionPage";
  } else {
    const parts = pathname.replace(/^\/+|\/+$/g, "").split("/");
    product = parts.length > 1 ? parts[1] : "";
    const [label, fallbackDescription] =
      PRODUCT_META[product] || ["最新文章", "Pantheon 最新文章，整理命盤、人格、塔羅、星座與人生方向主題。"];
    title = label;
    description = fallbackDescription;
    contentType = parts.length >= 3 ? "Article" : "CollectionPage";
  }

  return {
    title,
    pageTitle: `${title} | Pantheon`,
    description,
    canonical: `${SITE_ORIGIN}${pathname}`,
    product,
    productLabel: productLabel(product),
    contentType,
  };
}

function buildJsonLd(meta) {
  const organizationRef = { "@id": `${SITE_ORIGIN}/#organization` };
  const websiteRef = { "@id": `${SITE_ORIGIN}/#website` };
  const image = `${SITE_ORIGIN}/static/pantheon-orb-alpha-poster.webp`;
  const main =
    meta.contentType === "CollectionPage"
      ? {
          "@context": "https://schema.org",
          "@type": "CollectionPage",
          name: meta.title,
          description: meta.description,
          inLanguage: "zh-Hant-TW",
          url: meta.canonical,
          mainEntityOfPage: meta.canonical,
          isPartOf: websiteRef,
          publisher: organizationRef,
          image,
        }
      : {
          "@context": "https://schema.org",
          "@type": "Article",
          headline: meta.title,
          description: meta.description,
          inLanguage: "zh-Hant-TW",
          url: meta.canonical,
          mainEntityOfPage: meta.canonical,
          image,
          datePublished: ARTICLE_PUBLISHED_DATE,
          dateModified: ARTICLE_UPDATED_DATE,
          author: { "@type": "Organization", name: "Pantheon 編輯部" },
          publisher: organizationRef,
          isPartOf: websiteRef,
          articleSection: meta.productLabel,
        };
  const breadcrumbItems = [
    { name: "Pantheon", item: `${SITE_ORIGIN}/articles` },
    { name: "最新文章", item: `${SITE_ORIGIN}/articles` },
    { name: meta.title, item: meta.canonical },
  ];
  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: breadcrumbItems.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.item,
    })),
  };
  const faq = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "這篇文章可以取代個人判讀嗎？",
        acceptedAnswer: {
          "@type": "Answer",
          text: "不可以。公開文章只整理共通知識與使用邊界，個人判讀仍需回到你的資料、問題與當下情境。",
        },
      },
    ],
  };
  return { main, breadcrumb, faq };
}

function replaceMetaContent(markup, attrName, attrValue, contentValue) {
  const pattern = new RegExp(`(<meta\\s+${attrName}=["']${escapeRegExp(attrValue)}["'][^>]*content=["'])([^"']*)(["'])`, "i");
  return markup.replace(pattern, (_, prefix, _oldValue, suffix) => `${prefix}${escapeAttr(contentValue)}${suffix}`);
}

function renderSeoShell(markup, meta) {
  const { main, breadcrumb, faq } = buildJsonLd(meta);
  let html = markup.replace(/<title>.*?<\/title>/s, `<title>${escapeHtml(meta.pageTitle)}</title>`);
  html = replaceMetaContent(html, "name", "description", meta.description);
  html = replaceMetaContent(html, "property", "og:title", meta.pageTitle);
  html = replaceMetaContent(html, "property", "og:description", meta.description);
  html = replaceMetaContent(html, "property", "og:url", meta.canonical);
  html = replaceMetaContent(html, "name", "twitter:title", meta.pageTitle);
  html = replaceMetaContent(html, "name", "twitter:description", meta.description);
  html = html.replace(/(<link rel="canonical" href=")[^"]+(")/, (_, prefix, suffix) => `${prefix}${escapeAttr(meta.canonical)}${suffix}`);
  html = html.replace(
    /(<script type="application\/ld\+json" id="article-jsonld">).*?(<\/script>)/s,
    (_, prefix, suffix) => `${prefix}${JSON.stringify(main)}${suffix}`,
  );
  html = html.replace(
    /(<script type="application\/ld\+json" id="breadcrumb-jsonld">).*?(<\/script>)/s,
    (_, prefix, suffix) => `${prefix}${JSON.stringify(breadcrumb)}${suffix}`,
  );
  html = html.replace(
    /(<script type="application\/ld\+json" id="faq-jsonld">).*?(<\/script>)/s,
    (_, prefix, suffix) => `${prefix}${JSON.stringify(faq)}${suffix}`,
  );
  html = html.replace(/(<h1 data-article-title>).*?(<\/h1>)/s, (_, prefix, suffix) => `${prefix}${escapeHtml(meta.title)}${suffix}`);
  html = html.replace(
    /(<p class="article-section-description" data-section-description>).*?(<\/p>)/s,
    (_, prefix, suffix) => `${prefix}${escapeHtml(meta.description)}${suffix}`,
  );
  return html;
}

async function renderArticleRequest(request, env, url) {
  const assetUrl = new URL(request.url);
  assetUrl.pathname = "/article.html";
  assetUrl.search = "";
  const articleRequest = new Request(assetUrl, request);
  const response = await env.ASSETS.fetch(articleRequest);
  if (!response.ok) {
    return response;
  }
  const markup = await response.text();
  const body = renderSeoShell(markup, rawArticleMeta(url.pathname));
  const headers = new Headers(response.headers);
  headers.set("content-type", "text/html; charset=utf-8");
  headers.set("cache-control", "public, max-age=300");
  return new Response(body, { status: 200, headers });
}

function shouldRenderArticleShell(pathname) {
  return (pathname.startsWith("/articles/") && !pathname.includes(".")) || (pathname.startsWith("/topics/") && !pathname.includes("."));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const redirectTarget = STATIC_REDIRECTS.get(url.pathname);
    if (redirectTarget) {
      return Response.redirect(`${url.origin}${redirectTarget}`, 302);
    }
    if (shouldRenderArticleShell(url.pathname)) {
      return renderArticleRequest(request, env, url);
    }
    return env.ASSETS.fetch(request);
  },
};

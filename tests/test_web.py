from fastapi.testclient import TestClient
import json
from pathlib import Path
import subprocess

from main import app


INITIAL_FIRST_30_ARTICLE_PATHS = [
    "/articles/personality/personality-0001",
    "/articles/personality/personality-0002",
    "/articles/personality/personality-0003",
    "/articles/personality/personality-0004",
    "/articles/personality/personality-0005",
    "/articles/personality/personality-0006",
    "/articles/personality/personality-0007",
    "/articles/personality/personality-0008",
    "/articles/tarot/tarot-0001",
    "/articles/tarot/tarot-0002",
    "/articles/tarot/tarot-0003",
    "/articles/tarot/tarot-0004",
    "/articles/tarot/tarot-0005",
    "/articles/tarot/tarot-0006",
    "/articles/tarot/tarot-0007",
    "/articles/tarot/tarot-0008",
    "/articles/fortune/fortune-0001",
    "/articles/fortune/fortune-0002",
    "/articles/fortune/fortune-0003",
    "/articles/fortune/fortune-0004",
    "/articles/fortune/fortune-0005",
    "/articles/fortune/fortune-0006",
    "/articles/astrology/astrology-0001",
    "/articles/astrology/astrology-0002",
    "/articles/astrology/astrology-0003",
    "/articles/love/love-0001",
    "/articles/career/career-0001",
    "/articles/interpersonal/interpersonal-0001",
    "/articles/wealth/wealth-0001",
    "/articles/life-direction/life-direction-0001",
]

EXTRA_PUBLIC_ARTICLE_PATHS = [
    "/articles/astrology/astrology-0004",
]

PUBLIC_ARTICLE_PATHS = [
    *INITIAL_FIRST_30_ARTICLE_PATHS,
    *EXTRA_PUBLIC_ARTICLE_PATHS,
]


def test_home_redirects_to_latest_articles() -> None:
    client = TestClient(app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/articles"


def test_non_article_product_pages_redirect_to_articles() -> None:
    client = TestClient(app)
    for path in [
        "/reading",
        "/index.html",
        "/personality",
        "/personality.html",
        "/effects-demo",
        "/effects-demo.html",
        "/strategy",
        "/strategy.html",
    ]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/articles"


def test_articles_latest_hub_serves_collection_page() -> None:
    client = TestClient(app)
    response = client.get("/articles")
    assert response.status_code == 200
    assert "最新文章 | Pantheon" in response.text
    assert "MBTI、塔羅、命盤、星盤是什麼？先看白話答案" in response.text
    assert "從 MBTI 是什麼、16 型人格、塔羅牌意思" in response.text
    assert "class=\"destiny-screen articles-hub-screen\"" in response.text
    assert "articles-hub-breadcrumb" in response.text
    assert "data-home-articles" in response.text
    assert "content-hub-grid" in response.text
    assert "href=\"/articles/personality/personality-0001\"" in response.text
    assert "href=\"/reading\"" not in response.text
    assert "個人化解讀" not in response.text
    assert "\"@type\": \"CollectionPage\"" in response.text
    assert "/static/styles.css?v=articles-hub-20260710-4" in response.text
    assert "/static/articles.js?v=articles-hub-20260710-3" in response.text
    assert "id=\"birth-form\"" not in response.text


def test_article_urls_serve_article_template() -> None:
    client = TestClient(app)
    for path in ["/articles/astro", "/articles/astrology/astrology-0004", "/articles/intents/love", "/topics/mbti"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "data-article-header" in response.text
        assert "最新文章" in response.text
        assert "ui-topbar" in response.text
        assert "ui-topbar-inner" in response.text
        assert "ui-page-shell" in response.text
        assert "ui-chip-list" in response.text
        assert "ui-panel" in response.text
        assert "article-theme-visual" in response.text
        assert "data-product-theme-label" in response.text
        assert "data-product-theme-glyph" in response.text
        assert "href=\"/articles/fortune\"" in response.text
        assert "href=\"/articles/personality\"" in response.text
        assert "href=\"/strategy\"" not in response.text
        assert "name=\"robots\"" in response.text
        assert "name=\"keywords\"" in response.text
        assert "property=\"og:type\" content=\"article\"" in response.text
        assert "name=\"twitter:card\" content=\"summary_large_image\"" in response.text
        assert "id=\"article-jsonld\"" in response.text
        assert "id=\"breadcrumb-jsonld\"" in response.text
        assert "id=\"faq-jsonld\"" in response.text
        assert "aria-label=\"文章產品\"" in response.text
        assert "href=\"/articles/astro\"" in response.text
        assert "href=\"/reading\"" not in response.text
        assert "href=\"/personality\"" not in response.text
        assert "熱門文章" in response.text
        assert "aria-label=\"麵包屑\"" in response.text
        assert "aria-label=\"重點答案\"" in response.text
        assert "data-answer-summary" in response.text
        assert "data-section-description" in response.text
        assert "data-article-body" in response.text
        assert "data-article-tags" in response.text
        assert "aria-label=\"常見問題\"" in response.text
        assert "href=\"/articles\"" in response.text
        assert "data-product-crumb" in response.text
        assert "data-title-crumb" in response.text
        assert "data-article-footer" in response.text
        assert "aria-label=\"文章頁尾產品\"" in response.text
        assert "/static/styles.css?v=article-product-theme-20260710-4" in response.text
        assert "/static/article.js?v=article-content-20260710-9" in response.text


def test_article_breadcrumb_uses_product_and_slug_from_url() -> None:
    article_js = Path("app/web/static/article.js").read_text()
    article_meta_js = Path("app/web/static/article-meta.js").read_text()
    article_seo_js = Path("app/web/static/article-seo.js").read_text()
    article_registry_js = Path("app/web/static/article-registry.js").read_text()
    articles_js = Path("app/web/static/articles.js").read_text()
    styles_css = Path("app/web/static/styles.css").read_text()
    redirects = Path("app/web/_redirects").read_text()
    assert "buildArticleContent(window.location.pathname, window.location.origin" in article_js
    assert "if (content.redirectTo)" in article_js
    assert "window.location.replace(content.redirectTo)" in article_js
    assert "applyArticleSeo(content, dom, window.location.origin)" in article_js
    assert "getArticleSectionRecord(route.product)" in article_meta_js
    assert "getArticleRecord(route.product, route.slug)" in article_meta_js
    assert "getProductThemeRecord(managedArticle.productTheme)" in article_meta_js
    assert "productThemeGlyph" in article_meta_js
    assert "intent" in article_meta_js
    assert "canonicalPath" in article_meta_js
    assert "faq:" in article_meta_js
    assert "dom.articleTags.replaceChildren" in article_js
    assert "document.body.dataset.productTheme = content.productTheme" in article_js
    assert "document.body.dataset.intent = content.intent" in article_js
    assert "dom.productThemeGlyph.textContent = content.productThemeGlyph" in article_js
    assert "item.className = \"ui-chip\"" in article_js
    assert "dom.productCrumb.href = content.productHref" in article_js
    assert "dom.articleTitle.textContent = content.title" in article_js
    assert "dom.titleCrumb.hidden = false" in article_js
    assert "renderArticleBody(content)" in article_js
    assert "renderArticleFaq(content)" in article_js
    assert "renderArticleRelated(content)" in article_js
    assert "renderArticleCta(content)" in article_js
    assert "data-article-related" in Path("app/web/article.html").read_text()
    assert "data-article-cta" in Path("app/web/article.html").read_text()
    assert "bodySections: buildBodySections" in article_meta_js
    assert "buildArticleBody(article, productTheme, managedArticle)" in article_meta_js
    assert "ARTICLE_BODY_LIBRARY" in article_meta_js
    assert "buildRelatedLinks(article, managedArticle, productTheme, route)" in article_meta_js
    assert "buildArticleCta(article, productTheme, route)" in article_meta_js
    assert "\"mbti-meaning\"" in article_meta_js
    assert "\"magician-card-meaning\"" in article_meta_js
    assert "MBTI 是一套描述人格偏好的分類工具" in article_meta_js
    assert "魔術師牌通常代表資源、行動、創造力" in article_meta_js
    assert "buildFallbackFaq(route, article, productTheme)" in article_meta_js
    assert "buildArticleFaq(route, article, productTheme)" in article_meta_js
    assert "cleanFaqTopic(primary)" in article_meta_js
    assert "想看自己的狀況，應該從哪個入口開始？" in article_meta_js
    assert "displayTags: buildDisplayTags" in article_meta_js
    assert "INTERNAL_DISPLAY_TAGS" in article_meta_js
    assert "content.displayTags || content.tags || []" in article_js
    assert "content.displayTagLinks" in article_js
    assert "getTopicForLabel" in article_meta_js
    assert "buildTopicContent(route, topic" in article_meta_js
    assert "pickLatestArticles(listArticleRecords())" in articles_js
    assert "getArticlePath(article)" in articles_js
    assert "card.dataset.productTheme = article.product" in articles_js
    assert "SEARCH_SNIPPETS" in articles_js
    assert "MBTI 用四組偏好組成 16 型人格" in articles_js
    assert "塔羅牌意思先看 78 張牌的象徵" in articles_js
    assert ".articles-hub-breadcrumb" in styles_css
    assert "color: rgba(244, 234, 211, 0.78)" in styles_css
    assert '--article-page-bg:' in styles_css
    assert '.article-screen[data-product-theme="fortune"]' in styles_css
    assert '.article-screen[data-product-theme="personality"]' in styles_css
    assert '.article-screen[data-product-theme="fortune"] {\n  --article-accent: var(--cinnabar);' in styles_css
    assert '.article-screen[data-product-theme="personality"] {\n  --article-accent: #b98624;' in styles_css
    assert '.article-screen[data-product-theme="tarot"]' in styles_css
    assert '.article-screen[data-product-theme="astro"]' in styles_css
    assert '--article-header-bg:' in styles_css
    assert '--article-panel-bg:' in styles_css
    assert ".article-related" in styles_css
    assert ".article-cta-actions" in styles_css
    assert "document.title = content.pageTitle" in article_seo_js
    assert "dom.keywords.content = content.keywords.join" in article_seo_js
    assert "keywords: content.keywords.join" in article_seo_js
    assert "about: (content.displayTags || content.tags || []).map" in article_seo_js
    assert "\"@type\": \"Article\"" not in article_js
    assert "{ name: \"Pantheon\", item: `${origin}/articles` }" in article_seo_js
    assert "{ name: \"最新文章\", item: `${origin}/articles` }" in article_seo_js
    assert "export function applyArticleSeo" in article_seo_js
    assert "\"@type\": \"Article\"" in article_seo_js
    assert "\"@type\": \"BreadcrumbList\"" in article_seo_js
    assert "\"@type\": \"FAQPage\"" in article_seo_js
    assert "GLOBAL_ARTICLE_POLICY" in article_registry_js
    assert "HUMANIZER_POLICY" in article_registry_js
    assert "PRODUCT_THEME_REGISTRY" in article_registry_js
    assert "ARTICLE_URL_CONTRACT" in article_registry_js
    assert "articlePattern: \"/articles/{category}/{category}-{number}\"" in article_registry_js
    assert "TOPIC_REGISTRY" in article_registry_js
    assert "export function listTopicRecords" in article_registry_js
    assert "export function getArticlePath" in article_registry_js
    assert "LIFE_INTENT_REGISTRY" in article_registry_js
    assert "export function getProductThemeRecord" in article_registry_js
    assert "product: \"astro\"" in article_registry_js
    assert "product: \"personality\"" in article_registry_js
    assert "product: \"tarot\"" in article_registry_js
    assert "product: \"fortune\"" in article_registry_js
    for intent in ["感情", "事業", "人際", "財富", "人生方向"]:
        assert intent in article_registry_js
    assert "interpersonal:" in article_registry_js
    assert "intent: \"love\"" in article_registry_js
    assert "intent: \"interpersonal\"" in article_registry_js
    assert "requiredKeywordTags" in article_registry_js
    assert "bannedGenericPhrases" in article_registry_js
    assert "export function auditArticleVoice" in article_registry_js
    assert "export function listArticleVoiceAudits" in article_registry_js
    assert "ARTICLE_SECTION_REGISTRY" in article_registry_js
    assert "ARTICLE_REGISTRY" in article_registry_js
    assert "export function enforceArticlePolicy" in article_registry_js
    assert "export function buildArticleGraph" in article_registry_js
    assert "contains_article" in article_registry_js
    assert "has_tag" in article_registry_js
    assert "/ /articles 302" in redirects
    assert "/reading /articles 302" in redirects
    assert "/personality /articles 302" in redirects
    assert "/effects-demo /articles 302" in redirects
    assert "/strategy /articles 302" in redirects
    assert "/index.html /articles 302" in redirects
    assert "/personality.html /articles 302" in redirects
    assert "/effects-demo.html /articles 302" in redirects
    assert "/strategy.html /articles 302" in redirects
    assert "/articles/astro/12-zodiac-signs /articles/astro 302" in redirects
    assert "/articles /articles 200" in redirects
    assert "/articles/* /article 200" in redirects
    assert "/topics/* /article 200" in redirects
    assert "/reading /index.html 200" not in redirects
    assert "/articles /article.html 200" not in redirects
    assert "/personality /personality.html 200" not in redirects
    assert "/strategy /strategy.html 200" not in redirects
    assert "/effects-demo /effects-demo.html 200" not in redirects
    assert "/article-admin /article-admin.html 200" not in redirects


def test_public_articles_follow_latest_publication_standard() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
const paths = {json.dumps(PUBLIC_ARTICLE_PATHS)};
const summaryPaths = new Set([
  "/articles/personality/personality-0002",
  "/articles/tarot/tarot-0001",
]);
const data = paths.map((path) => {{
  const content = buildArticleContent(path, "https://mysticpantheon.com", {{
    author: "Pantheon 編輯部",
    updated: "2026-07-10",
  }});
  const bodyText = content.bodySections.flatMap((section) => section.paragraphs).join("");
  const forbidden = ["全面解析", "深度解析", "不可或缺", "賦能", "總而言之", "值得注意的是", "必看", "一定", "保證", "注定"];
  return {{
    path,
    bodySectionCount: content.bodySections.length,
    bodyLength: [...bodyText].length,
    faqCount: content.faq.length,
    relatedCount: content.relatedLinks.length,
    ctaCount: content.cta.links.length,
    hasLimit: /不能|不適合|不代表|不是/.test(bodyText),
    minBodyLength: summaryPaths.has(path) ? 2400 : 1600,
    hasForbidden: forbidden.some((word) => bodyText.includes(word) || content.title.includes(word)),
  }};
}});
console.log(JSON.stringify(data));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    records = json.loads(result.stdout)
    assert len(records) == len(PUBLIC_ARTICLE_PATHS)
    for record in records:
        assert record["bodySectionCount"] >= 8, record
        assert record["bodyLength"] >= record["minBodyLength"], record
        assert 3 <= record["faqCount"] <= 5, record
        assert record["relatedCount"] >= 6, record
        assert record["ctaCount"] >= 3, record
        assert record["hasLimit"], record
        assert not record["hasForbidden"], record


def test_unknown_article_slug_redirects_to_product_hub() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";
const content = buildArticleContent("/articles/astro/12-zodiac-signs", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
console.log(JSON.stringify(content));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {"redirectTo": "/articles/astro"}


def test_legacy_article_slug_redirects_to_serial_url() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";
const legacy = buildArticleContent("/articles/personality/relationships-stuck", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
const canonical = buildArticleContent("/articles/interpersonal/interpersonal-0001", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
const topic = buildArticleContent("/topics/mbti", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
console.log(JSON.stringify({
  legacy,
  canonical: {
    title: canonical.title,
    serial: canonical.serial,
    canonicalPath: canonical.canonicalPath,
    tagHref: canonical.displayTagLinks.find((tag) => tag.label === "人際關係")?.href,
  },
  topic: {
    title: topic.title,
    canonicalPath: topic.canonicalPath,
    relatedCount: topic.relatedLinks.length,
  },
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["legacy"] == {"redirectTo": "/articles/interpersonal/interpersonal-0001"}
    assert data["canonical"]["serial"] == "interpersonal-0001"
    assert data["canonical"]["canonicalPath"] == "/articles/interpersonal/interpersonal-0001"
    assert data["canonical"]["tagHref"] == "/topics/interpersonal"
    assert data["topic"]["canonicalPath"] == "/topics/mbti"
    assert data["topic"]["relatedCount"] >= 3


def test_article_admin_serves_management_console() -> None:
    client = TestClient(app)
    response = client.get("/article-admin")
    assert response.status_code == 200
    assert "文章管理" in response.text
    assert "強制關鍵字標籤" in response.text
    assert "文章 Section 描述" in response.text
    assert "內容圖譜" in response.text
    assert "語氣品質 Gate" in response.text
    assert "所有文章" in response.text
    assert "name=\"robots\" content=\"noindex,nofollow\"" in response.text
    assert "/static/article-admin.js" in response.text
    article_admin_js = Path("app/web/static/article-admin.js").read_text()
    assert "buildArticleGraph" in article_admin_js
    assert "renderHumanizerGate" in article_admin_js
    assert "listArticleVoiceAudits" in article_admin_js
    assert "ui-panel" in article_admin_js
    assert "ui-chip-list" in article_admin_js
    assert "ui-chip" in article_admin_js
    assert "data-graph-summary" in response.text
    assert "data-graph-links" in response.text
    assert "data-humanizer-checks" in response.text
    assert "data-humanizer-audits" in response.text


def test_article_robots_and_sitemap_are_served() -> None:
    client = TestClient(app)
    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")
    assert robots.status_code == 200
    assert "User-agent: *" in robots.text
    assert "Sitemap: https://mysticpantheon.com/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert "https://mysticpantheon.com/articles" in sitemap.text
    assert "https://mysticpantheon.com/</loc>" not in sitemap.text
    assert "https://mysticpantheon.com/articles/fortune" in sitemap.text
    assert "https://mysticpantheon.com/articles/personality" in sitemap.text
    assert "https://mysticpantheon.com/articles/astro" in sitemap.text
    assert "https://mysticpantheon.com/articles/fortune/fortune-0001" in sitemap.text
    assert "https://mysticpantheon.com/articles/interpersonal/interpersonal-0001" in sitemap.text
    assert "https://mysticpantheon.com/topics/mbti" in sitemap.text
    assert "https://mysticpantheon.com/articles/bazi" not in sitemap.text
    assert "https://mysticpantheon.com/articles/mbti" not in sitemap.text
    assert "https://mysticpantheon.com/articles/personality/relationships-stuck" not in sitemap.text


def test_first_30_article_plan_is_registered_for_site() -> None:
    article_registry_js = Path("app/web/static/article-registry.js").read_text()
    sitemap_xml = Path("app/web/sitemap.xml").read_text()
    expected_articles = [
        ("MBTI 是什麼", "/articles/personality/personality-0001"),
        ("16 型人格", "/articles/personality/personality-0002"),
        ("MBTI 測驗", "/articles/personality/personality-0003"),
        ("MBTI 準嗎", "/articles/personality/personality-0004"),
        ("INTJ 是什麼", "/articles/personality/personality-0005"),
        ("INFP 是什麼", "/articles/personality/personality-0006"),
        ("INFJ 是什麼", "/articles/personality/personality-0007"),
        ("ENFP 是什麼", "/articles/personality/personality-0008"),
        ("塔羅牌意思", "/articles/tarot/tarot-0001"),
        ("塔羅牌正位逆位", "/articles/tarot/tarot-0002"),
        ("愚者牌意思", "/articles/tarot/tarot-0003"),
        ("魔術師牌意思", "/articles/tarot/tarot-0004"),
        ("戀人牌意思", "/articles/tarot/tarot-0005"),
        ("死神牌意思", "/articles/tarot/tarot-0006"),
        ("高塔牌意思", "/articles/tarot/tarot-0007"),
        ("世界牌意思", "/articles/tarot/tarot-0008"),
        ("命盤是什麼", "/articles/fortune/fortune-0001"),
        ("八字是什麼", "/articles/fortune/fortune-0002"),
        ("紫微斗數是什麼", "/articles/fortune/fortune-0003"),
        ("命宮是什麼", "/articles/fortune/fortune-0004"),
        ("夫妻宮是什麼", "/articles/fortune/fortune-0005"),
        ("財帛宮是什麼", "/articles/fortune/fortune-0006"),
        ("星盤是什麼", "/articles/astrology/astrology-0001"),
        ("上升星座是什麼", "/articles/astrology/astrology-0002"),
        ("月亮星座是什麼", "/articles/astrology/astrology-0003"),
        ("感情塔羅", "/articles/love/love-0001"),
        ("事業運勢", "/articles/career/career-0001"),
        ("人際關係", "/articles/interpersonal/interpersonal-0001"),
        ("財富運勢", "/articles/wealth/wealth-0001"),
        ("人生方向", "/articles/life-direction/life-direction-0001"),
    ]
    for keyword, path in expected_articles:
        assert f'primaryKeyword: "{keyword}"' in article_registry_js
        assert f"https://mysticpantheon.com{path}" in sitemap_xml


def test_retired_static_product_pages_redirect_to_articles() -> None:
    retired_pages = [
        Path("app/web/index.html"),
        Path("app/web/personality.html"),
        Path("app/web/effects-demo.html"),
    ]
    styles_css = Path("app/web/static/styles.css").read_text()
    for selector in [
        ".ui-page-shell",
        ".ui-topbar",
        ".ui-topbar-row",
        ".ui-button",
        ".ui-panel",
        ".ui-chip",
    ]:
        assert selector in styles_css
    for page in retired_pages:
        html = page.read_text()
        assert 'content="0; url=/articles"' in html
        assert 'window.location.replace("/articles")' in html
        assert 'meta name="robots" content="noindex,follow"' in html
        assert "個人化解讀" not in html
        assert "人格測試" not in html
        assert "app-topbar" not in html


def test_mbti_questions_use_mixed_display_order() -> None:
    personality_js = Path("app/web/static/personality.js").read_text()
    assert "const QUESTION_ORDER" in personality_js
    assert "const QUESTIONS_PER_PAGE = 8" in personality_js
    assert "data-question-page" in personality_js
    order_start = personality_js.index("const QUESTION_ORDER")
    order_end = personality_js.index("];", order_start)
    order_block = personality_js[order_start:order_end]
    first_ids = [
        "mbti.sn.01",
        "mbti.ei.03",
        "mbti.hc.01",
        "mbti.jp.02",
        "mbti.tf.05",
        "mbti.ao.04",
    ]
    last_position = -1
    for question_id in first_ids:
        position = order_block.index(question_id)
        assert position > last_position
        last_position = position


def test_destiny_page_does_not_auto_generate_report() -> None:
    app_js = Path("app/web/static/app.js").read_text()
    assert "renderInitialState()" in app_js
    assert "尚未推演命盤" in app_js
    assert "listArticleRecords" in app_js
    assert "getProductThemeRecord" in app_js
    assert "renderHomeArticles()" in app_js
    assert "pickFeaturedArticles" in app_js
    assert "card.dataset.productTheme = article.product" in app_js
    assert "card.dataset.themeGlyph = productTheme.glyph" in app_js
    assert "home-article-product" in app_js
    assert "dispatchEvent(new Event(\"submit\"))" not in app_js
    styles_css = Path("app/web/static/styles.css").read_text()
    assert ".product-drawer:not([open]) > .destiny-workbench" in styles_css
    assert "content: attr(data-theme-glyph)" in styles_css
    assert ".home-article-product" in styles_css
    assert ".home-article-card {\n  --home-theme-accent: #ae4635;" in styles_css
    assert '.home-article-card[data-product-theme="personality"]' in styles_css
    assert '.home-article-card[data-product-theme="personality"],\n.content-hub-grid a[data-product-theme="personality"] {\n  --home-theme-accent: #b98624;' in styles_css
    assert '.home-article-card[data-product-theme="tarot"]' in styles_css
    assert '.home-article-card[data-product-theme="astro"]' in styles_css
    assert '.content-hub-grid a[data-product-theme="personality"]' in styles_css


def test_frontend_uses_public_api_base_outside_localhost() -> None:
    api_js = Path("app/web/static/api.js").read_text()
    assert "https://api.mysticpantheon.com" in api_js
    assert 'apiUrl("/api/v1/predict")' in api_js
    assert 'apiUrl("/api/v1/personality")' in api_js


def test_cors_allows_public_frontend_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://mysticpantheon.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://mysticpantheon.com"


def test_cors_rejects_unknown_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_fortune_paper_renders_nameology_nested_fields_explicitly() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    assert "function renderFiveGrid" in paper_js
    assert "function renderThreeTalents" in paper_js
    assert "renderKeyValueRows(grids)" not in paper_js
    assert "renderKeyValueRows(talents)" not in paper_js


def test_fortune_paper_uses_final_narrative_order() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    sections = [
        "姓名合參",
        "本命底色",
        "五行怎麼用",
        "十神",
        "十二長生 / 祿刃",
        "神煞",
        "紫微星曜",
        "今年工作運",
        "今年財務、健康、人際",
        "算法依據",
    ]
    positions = [paper_js.index(section) for section in sections]
    assert positions == sorted(positions)
    assert "bazi.calculated_items" in paper_js
    assert "ziwei.calculated_items" in paper_js
    assert "function deriveGrowthStates" not in paper_js
    assert "function deriveSpecialForces" not in paper_js
    assert "function deriveShensha" not in paper_js
    assert "function nameologyNarrative" in paper_js


def test_fortune_paper_does_not_promote_inferred_forces() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    assert 'label: "食祿"' not in paper_js
    assert 'label: "氣勢"' not in paper_js
    assert 'forceUseText(day.element, strongest.name)' not in paper_js


def test_fortune_paper_splits_visible_and_hidden_ten_gods() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    assert "明顯十神" in paper_js
    assert "藏干補充" in paper_js
    assert "盤裡有的十神" not in paper_js
    assert "function listProminentTenGods" in paper_js
    assert "function listHiddenTenGods" in paper_js
    assert "tenGodUseText(listProminentTenGods" in paper_js


def test_fortune_paper_limits_ziwei_auxiliary_stars() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    ziwei_py = Path("app/calculators/ziwei_items.py").read_text()
    assert 'SUPPORT_FOCUS_PALACES = {"命宮", "官祿", "財帛"}' in ziwei_py
    assert "[:4]" in ziwei_py
    assert '"天德"' not in paper_js


def test_fortune_paper_does_not_calculate_bazi_items_in_frontend() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    forbidden = [
        "const TWELVE_GROWTH",
        "const LU_BRANCH",
        "const YANGREN_BRANCH",
        "const SIX_ELEGANCE_DAYS",
        "const YUEDE_STEM",
        "const TIAN_YI_BRANCHES",
        "function pillarBranches",
        "function groupKey",
    ]
    for text in forbidden:
        assert text not in paper_js

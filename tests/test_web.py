from fastapi.testclient import TestClient
from pathlib import Path

from main import app


def test_home_serves_frontend() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Mystic Engine" in response.text
    assert "先讀懂問題，再決定要不要做個人化解讀" in response.text
    assert "data-home-articles" in response.text
    assert "精選文章" in response.text
    assert "文章入口" in response.text
    assert "熱門問題" in response.text
    assert "熱門文章主題" in response.text
    assert "每篇都先講通用概念、適用情境與限制。" in response.text
    assert "href=\"/articles/personality/mbti-meaning\"" in response.text
    assert "href=\"/articles/tarot/tarot-card-meanings\"" in response.text
    assert "href=\"/articles/fortune/birth-chart-meaning\"" in response.text
    assert "href=\"/articles/astro/birth-chart-astrology\"" in response.text
    assert "href=\"/articles\"" in response.text
    assert "href=\"/articles/fortune\"" in response.text
    assert "href=\"/articles/personality\"" in response.text
    assert "href=\"/articles/tarot\"" in response.text
    assert "href=\"/articles/astro\"" in response.text
    assert "data-product-theme=\"fortune\"" in response.text
    assert "data-product-theme=\"personality\"" in response.text
    assert "data-product-theme=\"tarot\"" in response.text
    assert "data-product-theme=\"astro\"" in response.text
    assert "<em aria-hidden=\"true\">命</em>" in response.text
    assert "<em aria-hidden=\"true\">64</em>" in response.text
    assert "<em aria-hidden=\"true\">XVII</em>" in response.text
    assert "<em aria-hidden=\"true\">星</em>" in response.text
    assert "個人化命書工具" in response.text
    assert "id=\"destiny-tool\"" in response.text
    assert "基本資料" in response.text
    assert "命書報告" in response.text
    assert "進階排盤設定" in response.text
    assert "命盤總覽" in response.text
    assert "開始推演命盤" in response.text
    assert "/strategy" not in response.text
    assert "64 分支人格測試" not in response.text
    assert "id=\"personality-form\"" not in response.text
    assert "/static/styles.css?v=home-articles-20260710-3" in response.text
    assert "/static/app.js?v=home-articles-20260710-3" in response.text


def test_personality_page_serves_standalone_frontend() -> None:
    client = TestClient(app)
    response = client.get("/personality")
    assert response.status_code == 200
    assert "64 分支人格測試" in response.text
    assert "id=\"personality-form\"" in response.text
    assert "段落 1 / 6" in response.text
    assert "返回" in response.text
    assert "繼續" in response.text
    assert "完成後產生結果" in response.text
    assert "/static/personality.js" in response.text


def test_effects_demo_page_serves_motion_lab() -> None:
    client = TestClient(app)
    response = client.get("/effects-demo")
    assert response.status_code == 200
    assert "三功能特效語言展示" in response.text
    assert "data-scene=\"fortune\"" in response.text
    assert "data-scene=\"personality\"" in response.text
    assert "data-scene=\"tarot\"" in response.text
    assert "/static/effects-demo.js" in response.text


def test_article_urls_serve_article_template() -> None:
    client = TestClient(app)
    for path in ["/articles", "/articles/astro", "/articles/astro/love-forecast", "/articles/intents/love"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "data-article-header" in response.text
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
        assert "name=\"robots\"" in response.text
        assert "name=\"keywords\"" in response.text
        assert "property=\"og:type\" content=\"article\"" in response.text
        assert "name=\"twitter:card\" content=\"summary_large_image\"" in response.text
        assert "id=\"article-jsonld\"" in response.text
        assert "id=\"breadcrumb-jsonld\"" in response.text
        assert "id=\"faq-jsonld\"" in response.text
        assert "aria-label=\"文章產品\"" in response.text
        assert "href=\"/articles/astro\"" in response.text
        assert "href=\"/personality\"" in response.text
        assert "aria-label=\"麵包屑\"" in response.text
        assert "aria-label=\"重點答案\"" in response.text
        assert "data-answer-summary" in response.text
        assert "data-section-description" in response.text
        assert "data-article-tags" in response.text
        assert "aria-label=\"常見問題\"" in response.text
        assert "href=\"/articles\"" in response.text
        assert "data-product-crumb" in response.text
        assert "data-title-crumb" in response.text
        assert "data-article-footer" in response.text
        assert "aria-label=\"文章頁尾產品\"" in response.text
        assert "/static/article.js" in response.text


def test_article_breadcrumb_uses_product_and_slug_from_url() -> None:
    article_js = Path("app/web/static/article.js").read_text()
    article_meta_js = Path("app/web/static/article-meta.js").read_text()
    article_seo_js = Path("app/web/static/article-seo.js").read_text()
    article_registry_js = Path("app/web/static/article-registry.js").read_text()
    redirects = Path("app/web/_redirects").read_text()
    assert "buildArticleContent(window.location.pathname, window.location.origin" in article_js
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
    assert "document.title = content.pageTitle" in article_seo_js
    assert "dom.keywords.content = content.keywords.join" in article_seo_js
    assert "keywords: content.keywords.join" in article_seo_js
    assert "about: content.tags.map" in article_seo_js
    assert "\"@type\": \"Article\"" not in article_js
    assert "export function applyArticleSeo" in article_seo_js
    assert "\"@type\": \"Article\"" in article_seo_js
    assert "\"@type\": \"BreadcrumbList\"" in article_seo_js
    assert "\"@type\": \"FAQPage\"" in article_seo_js
    assert "GLOBAL_ARTICLE_POLICY" in article_registry_js
    assert "HUMANIZER_POLICY" in article_registry_js
    assert "PRODUCT_THEME_REGISTRY" in article_registry_js
    assert "ARTICLE_URL_CONTRACT" in article_registry_js
    assert "articlePattern: \"/articles/{product}/{slug}\"" in article_registry_js
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
    assert "/articles /article.html 200" in redirects
    assert "/articles/* /article.html 200" in redirects
    assert "/personality /personality.html 200" not in redirects
    assert "/strategy /strategy.html 200" not in redirects
    assert "/effects-demo /effects-demo.html 200" not in redirects
    assert "/article-admin /article-admin.html 200" not in redirects


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
    assert "https://mysticpantheon.com/articles/fortune" in sitemap.text
    assert "https://mysticpantheon.com/articles/personality" in sitemap.text
    assert "https://mysticpantheon.com/articles/astro" in sitemap.text
    assert "https://mysticpantheon.com/articles/bazi" not in sitemap.text
    assert "https://mysticpantheon.com/articles/mbti" not in sitemap.text


def test_first_30_article_plan_is_registered_for_site() -> None:
    article_registry_js = Path("app/web/static/article-registry.js").read_text()
    sitemap_xml = Path("app/web/sitemap.xml").read_text()
    expected_articles = [
        ("MBTI 是什麼", "/articles/personality/mbti-meaning"),
        ("16 型人格", "/articles/personality/16-personalities"),
        ("MBTI 測驗", "/articles/personality/mbti-test"),
        ("MBTI 準嗎", "/articles/personality/mbti-accuracy"),
        ("INTJ 是什麼", "/articles/personality/intj-meaning"),
        ("INFP 是什麼", "/articles/personality/infp-meaning"),
        ("INFJ 是什麼", "/articles/personality/infj-meaning"),
        ("ENFP 是什麼", "/articles/personality/enfp-meaning"),
        ("塔羅牌意思", "/articles/tarot/tarot-card-meanings"),
        ("塔羅牌正位逆位", "/articles/tarot/upright-reversed"),
        ("愚者牌意思", "/articles/tarot/fool-card-meaning"),
        ("魔術師牌意思", "/articles/tarot/magician-card-meaning"),
        ("戀人牌意思", "/articles/tarot/lovers-card-meaning"),
        ("死神牌意思", "/articles/tarot/death-card-meaning"),
        ("高塔牌意思", "/articles/tarot/tower-card-meaning"),
        ("世界牌意思", "/articles/tarot/world-card-meaning"),
        ("命盤是什麼", "/articles/fortune/birth-chart-meaning"),
        ("八字是什麼", "/articles/fortune/bazi-meaning"),
        ("紫微斗數是什麼", "/articles/fortune/ziwei-doushu-meaning"),
        ("命宮是什麼", "/articles/fortune/ming-gong-meaning"),
        ("夫妻宮是什麼", "/articles/fortune/spouse-palace-meaning"),
        ("財帛宮是什麼", "/articles/fortune/wealth-palace-meaning"),
        ("星盤是什麼", "/articles/astro/birth-chart-astrology"),
        ("上升星座是什麼", "/articles/astro/ascendant-sign-meaning"),
        ("月亮星座是什麼", "/articles/astro/moon-sign-meaning"),
        ("感情塔羅", "/articles/tarot/love-tarot-questions"),
        ("事業運勢", "/articles/fortune/career-fortune"),
        ("人際關係", "/articles/personality/relationships-stuck"),
        ("財富運勢", "/articles/fortune/wealth-fortune"),
        ("人生方向", "/articles/fortune/life-direction"),
    ]
    for keyword, path in expected_articles:
        assert f'primaryKeyword: "{keyword}"' in article_registry_js
        assert f"https://mysticpantheon.com{path}" in sitemap_xml


def test_product_pages_use_shared_ui_primitives() -> None:
    index_html = Path("app/web/index.html").read_text()
    personality_html = Path("app/web/personality.html").read_text()
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
    assert "app-topbar destiny-topbar ui-topbar-row" in index_html
    assert "topbar-actions ui-actions" in index_html
    assert "primary-action ui-button ui-button-primary" in index_html
    assert "app-topbar personality-only-topbar ui-topbar-row" in personality_html
    assert "secondary-action ui-button ui-button-secondary" in personality_html
    assert "primary-action ui-button ui-button-primary" in personality_html


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
    assert '.home-article-card[data-product-theme="personality"]' in styles_css
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

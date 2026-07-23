from fastapi.testclient import TestClient
import json
from pathlib import Path
import re
import subprocess

from main import (
    ARTICLE_CONTENT_REFRESH_DATE,
    ARTICLE_PUBLISHED_DATE,
    ARTICLE_TAROT_COMPLETION_DATE,
    ARTICLE_UPDATED_DATE,
    ARTICLES_HUB_UPDATED_DATE,
    EXPANSION_50_PATHS,
    EXPANSION_50C_PATHS,
    EXPANSION_50D_PATHS,
    RAW_ARTICLE_META,
    TAROT_COMPLETION_PATHS,
    TAROT_CARD_FACE_REFRESH_PATHS,
    UPDATED_ARTICLE_PATHS,
    app,
    article_updated_date,
)
from scripts.competitor_seo_tool import endpoint_label
from scripts.prerender_article_shells import LEGACY_REDIRECTS, PRERENDER_ARTICLES, PRERENDER_HUBS, PRERENDER_ROUTES, PRERENDER_TOPICS, redirect_target
from scripts.update_articles_hub_dates import render_articles_hub_dates


ARTICLE_CACHE_TOKEN = "agy-daily-20260723-repair-01"

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

SECOND_BATCH_PUBLIC_ARTICLE_PATHS = [
    "/articles/tarot/tarot-0009",
    "/articles/tarot/tarot-0010",
    "/articles/tarot/tarot-0011",
    "/articles/fortune/fortune-0007",
    "/articles/fortune/fortune-0008",
    "/articles/fortune/fortune-0009",
    "/articles/personality/personality-0009",
    "/articles/personality/personality-0010",
    "/articles/personality/personality-0011",
    "/articles/astrology/astrology-0005",
    "/articles/love/love-0002",
    "/articles/love/love-0003",
    "/articles/love/love-0004",
    "/articles/career/career-0002",
    "/articles/career/career-0003",
    "/articles/career/career-0004",
    "/articles/interpersonal/interpersonal-0002",
    "/articles/wealth/wealth-0002",
    "/articles/wealth/wealth-0003",
    "/articles/life-direction/life-direction-0002",
]

NEXT_30_PUBLIC_ARTICLE_PATHS = [
    "/articles/tarot/tarot-0012",
    "/articles/tarot/tarot-0013",
    "/articles/tarot/tarot-0014",
    "/articles/tarot/tarot-0015",
    "/articles/tarot/tarot-0016",
    "/articles/tarot/tarot-0017",
    "/articles/tarot/tarot-0018",
    "/articles/tarot/tarot-0019",
    "/articles/tarot/tarot-0020",
    "/articles/tarot/tarot-0021",
    "/articles/tarot/tarot-0022",
    "/articles/tarot/tarot-0023",
    "/articles/tarot/tarot-0024",
    "/articles/tarot/tarot-0025",
    "/articles/tarot/tarot-0026",
    "/articles/tarot/tarot-0027",
    "/articles/tarot/tarot-0028",
    "/articles/tarot/tarot-0029",
    "/articles/tarot/tarot-0030",
    "/articles/tarot/tarot-0031",
    "/articles/tarot/tarot-0032",
    "/articles/personality/personality-0012",
    "/articles/personality/personality-0013",
    "/articles/personality/personality-0014",
    "/articles/personality/personality-0015",
    "/articles/personality/personality-0016",
    "/articles/personality/personality-0017",
    "/articles/personality/personality-0018",
    "/articles/personality/personality-0019",
    "/articles/personality/personality-0020",
]

SCALE_TO_125_PUBLIC_ARTICLE_PATHS = [
    "/articles/tarot/tarot-0033",
    "/articles/tarot/tarot-0034",
    "/articles/tarot/tarot-0035",
    "/articles/tarot/tarot-0036",
    "/articles/tarot/tarot-0037",
    "/articles/tarot/tarot-0038",
    "/articles/tarot/tarot-0039",
    "/articles/tarot/tarot-0040",
    "/articles/tarot/tarot-0041",
    "/articles/tarot/tarot-0042",
    "/articles/tarot/tarot-0043",
    "/articles/tarot/tarot-0044",
    "/articles/tarot/tarot-0045",
    "/articles/tarot/tarot-0046",
    "/articles/tarot/tarot-0047",
    "/articles/tarot/tarot-0048",
    "/articles/tarot/tarot-0049",
    "/articles/tarot/tarot-0050",
    "/articles/tarot/tarot-0051",
    "/articles/tarot/tarot-0052",
    "/articles/tarot/tarot-0053",
    "/articles/tarot/tarot-0054",
    "/articles/tarot/tarot-0055",
    "/articles/tarot/tarot-0056",
    "/articles/tarot/tarot-0057",
    "/articles/tarot/tarot-0058",
    "/articles/tarot/tarot-0059",
    "/articles/tarot/tarot-0060",
    "/articles/tarot/tarot-0061",
    "/articles/tarot/tarot-0062",
    "/articles/tarot/tarot-0063",
    "/articles/tarot/tarot-0064",
    "/articles/tarot/tarot-0065",
    "/articles/tarot/tarot-0066",
    "/articles/tarot/tarot-0067",
    "/articles/tarot/tarot-0068",
    "/articles/tarot/tarot-0069",
    "/articles/tarot/tarot-0070",
    "/articles/tarot/tarot-0071",
    "/articles/tarot/tarot-0072",
    "/articles/tarot/tarot-0073",
    "/articles/tarot/tarot-0074",
    "/articles/tarot/tarot-0075",
    "/articles/tarot/tarot-0076",
]

TAROT_COMPLETION_PUBLIC_ARTICLE_PATHS = [
    "/articles/tarot/tarot-0077",
    "/articles/tarot/tarot-0078",
    "/articles/tarot/tarot-0079",
    "/articles/tarot/tarot-0080",
]

EXPANSION_50_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/love/love-{serial:04d}" for serial in range(5, 13)),
    *(f"/articles/career/career-{serial:04d}" for serial in range(5, 13)),
    *(f"/articles/interpersonal/interpersonal-{serial:04d}" for serial in range(3, 13)),
    *(f"/articles/wealth/wealth-{serial:04d}" for serial in range(4, 13)),
    *(f"/articles/life-direction/life-direction-{serial:04d}" for serial in range(3, 13)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(6, 11)),
]

EXPANSION_50C_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(21, 37)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(11, 28)),
    *(f"/articles/fortune/fortune-{serial:04d}" for serial in range(10, 27)),
]

EXPANSION_50D_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(37, 53)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(28, 45)),
    *(f"/articles/fortune/fortune-{serial:04d}" for serial in range(27, 44)),
]

AGY_V1_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(53, 57)),
    "/articles/fortune/fortune-0044",
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(45, 48)),
]

AGY_ASC_BATCH_02_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(48, 53)),
]

AGY_ASC_VENUS_BATCH_03_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(53, 58)),
]

AGY_VENUS_BATCH_04_PUBLIC_ARTICLE_PATHS = [
    "/articles/astrology/astrology-0058",
    "/articles/astrology/astrology-0061",
    "/articles/astrology/astrology-0062",
    "/articles/astrology/astrology-0063",
    "/articles/astrology/astrology-0064",
]

EXPANSION_50E_PUBLIC_ARTICLE_PATHS = [
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(65, 115)),
]

DAILY_PUBLIC_ARTICLE_PATHS = [
    "/articles/astrology/astrology-0115",
]

PUBLIC_ARTICLE_PATHS = [
    *INITIAL_FIRST_30_ARTICLE_PATHS,
    *EXTRA_PUBLIC_ARTICLE_PATHS,
    *SECOND_BATCH_PUBLIC_ARTICLE_PATHS,
    *NEXT_30_PUBLIC_ARTICLE_PATHS,
    *SCALE_TO_125_PUBLIC_ARTICLE_PATHS,
    *TAROT_COMPLETION_PUBLIC_ARTICLE_PATHS,
    *EXPANSION_50_PUBLIC_ARTICLE_PATHS,
    *EXPANSION_50C_PUBLIC_ARTICLE_PATHS,
    *EXPANSION_50D_PUBLIC_ARTICLE_PATHS,
    *AGY_V1_PUBLIC_ARTICLE_PATHS,
    *AGY_ASC_BATCH_02_PUBLIC_ARTICLE_PATHS,
    *AGY_ASC_VENUS_BATCH_03_PUBLIC_ARTICLE_PATHS,
    *AGY_VENUS_BATCH_04_PUBLIC_ARTICLE_PATHS,
    *EXPANSION_50E_PUBLIC_ARTICLE_PATHS,
    *DAILY_PUBLIC_ARTICLE_PATHS,
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
    assert "感情、工作、人際卡住" in response.text
    assert "先從你的問題開始" in response.text
    assert "MBTI 是什麼、塔羅牌意思、命盤是什麼也會放回真實情境裡說清楚" in response.text
    assert "曖昧沒進展" in response.text
    assert "適合轉職嗎" in response.text
    assert "存不住錢" in response.text
    assert "class=\"destiny-screen articles-hub-screen\"" in response.text
    assert "articles-hub-breadcrumb" in response.text
    assert "data-home-articles" in response.text
    assert "content-hub-grid" in response.text
    assert "工作、財富與安全感卡住時怎麼整理" in response.text
    assert "相處很累、溝通不順與自我懷疑" in response.text
    assert "曖昧、復合、等待與下一步怎麼辦" in response.text
    assert "情緒安全感、喜歡方式與關係需求" in response.text
    assert "id=\"tarot-gap-cluster\"" not in response.text
    assert "下一批讀者常查的牌義與人際題" not in response.text
    assert "八字、紫微、命宮與財帛宮" not in response.text
    assert "MBTI、16 型人格與人際模式" not in response.text
    assert "牌義、正逆位與感情提問" not in response.text
    assert "星盤、上升星座與月亮星座" not in response.text
    assert "href=\"/articles/love/love-0002\"" in response.text
    assert "href=\"/reading\"" not in response.text
    assert "個人化解讀" not in response.text
    assert "\"@type\": \"CollectionPage\"" in response.text
    assert "name=\"author\" content=\"Pantheon 編輯部\"" in response.text
    assert f'property="article:published_time" content="{ARTICLE_PUBLISHED_DATE}"' in response.text
    assert f'property="article:modified_time" content="{ARTICLES_HUB_UPDATED_DATE}"' in response.text
    assert f'"datePublished": "{ARTICLE_PUBLISHED_DATE}"' in response.text
    assert f'"dateModified": "{ARTICLES_HUB_UPDATED_DATE}"' in response.text
    assert f'<time datetime="{ARTICLE_PUBLISHED_DATE}" data-articles-published>{ARTICLE_PUBLISHED_DATE}</time>' in response.text
    assert f'<time datetime="{ARTICLES_HUB_UPDATED_DATE}" data-articles-updated>{ARTICLES_HUB_UPDATED_DATE}</time>' in response.text
    assert render_articles_hub_dates(response.text) == response.text
    assert "\"author\": {" in response.text
    assert "\"@type\": \"Organization\"" in response.text
    assert "\"@id\": \"https://mysticpantheon.com/#organization\"" in response.text
    assert "\"@type\": \"WebSite\"" in response.text
    assert "\"@id\": \"https://mysticpantheon.com/#website\"" in response.text
    assert "\"@type\": \"FAQPage\"" in response.text
    assert "property=\"og:image\" content=\"https://mysticpantheon.com/static/pantheon-orb-alpha-poster.webp\"" in response.text
    assert "name=\"twitter:image\" content=\"https://mysticpantheon.com/static/pantheon-orb-alpha-poster.webp\"" in response.text
    assert "id=\"about-pantheon\"" in response.text
    assert "id=\"editorial-policy\"" in response.text
    assert "關於 Pantheon" in response.text
    assert "編輯政策" in response.text
    assert "聯絡 Pantheon" in response.text
    assert "公開文章不保證感情、工作、財富或人生結果" in response.text
    assert "href=\"https://schema.org/Article\"" in response.text
    assert "/static/pantheon-orb-alpha-poster.webp" in response.text
    assert "/static/pantheon-orb-alpha-v2.webm" in response.text
    assert "data-pantheon-motion-visual" in response.text
    assert "/static/styles.css?v=articles-mobile-lcp-20260723-1" in response.text
    assert f"/static/articles.js?v={ARTICLE_CACHE_TOKEN}" in response.text
    assert "id=\"birth-form\"" not in response.text


def test_articles_hub_reserves_motion_visual_space_before_javascript_mounts() -> None:
    articles_html = Path("app/web/articles.html").read_text()
    styles_css = Path("app/web/static/styles.css").read_text()
    placeholder_rule = re.search(
        r"\.content-topic-panel \[data-pantheon-motion-visual\] \{(?P<body>[^}]+)\}",
        styles_css,
    )
    mobile_visual_rule = re.search(
        r"\.content-topic-panel \[data-pantheon-motion-visual\] > \.visual \{(?P<body>[^}]+)\}",
        styles_css,
    )

    assert placeholder_rule is not None
    assert "width: min(100%, 43rem);" in placeholder_rule["body"]
    assert "aspect-ratio: 5 / 6;" in placeholder_rule["body"]
    assert '<div class="visual" role="img"' in articles_html
    assert 'class="poster"' in articles_html
    assert 'fetchpriority="high"' in articles_html
    assert mobile_visual_rule is not None
    assert "width: 100%;" in mobile_visual_rule["body"]


def test_articles_hub_uses_balanced_display_order() -> None:
    script = """
import { getArticlePath, listArticleRecords } from "./app/web/static/article-registry.js";
import { ARTICLE_HUB_DISPLAY_LIMIT, pickLatestArticles } from "./app/web/static/articles.js";

const selected = pickLatestArticles(listArticleRecords());
const records = selected.map((article) => ({
  path: getArticlePath(article),
  category: article.articleCategory,
}));
console.log(JSON.stringify({
  limit: ARTICLE_HUB_DISPLAY_LIMIT,
  records,
  adjacentSameCategory: records.some((record, index) => index > 0 && record.category === records[index - 1].category),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["limit"] == 12
    assert [record["category"] for record in data["records"]] == [
        "personality",
        "tarot",
        "fortune",
        "astrology",
        "love",
        "career",
        "interpersonal",
        "wealth",
        "life-direction",
        "personality",
        "tarot",
        "fortune",
    ]
    assert [record["path"] for record in data["records"]] == [
        "/articles/personality/personality-0056",
        "/articles/tarot/tarot-0080",
        "/articles/fortune/fortune-0044",
            "/articles/astrology/astrology-0115",
        "/articles/love/love-0012",
        "/articles/career/career-0012",
        "/articles/interpersonal/interpersonal-0012",
        "/articles/wealth/wealth-0012",
        "/articles/life-direction/life-direction-0012",
        "/articles/personality/personality-0055",
        "/articles/tarot/tarot-0079",
        "/articles/fortune/fortune-0043",
    ]
    assert data["adjacentSameCategory"] is False


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
        assert "name=\"author\" content=\"Pantheon 編輯部\"" in response.text
        assert "property=\"article:published_time\" content=\"2026-07-10\"" in response.text
        expected_modified = article_updated_date(path)
        assert f'property="article:modified_time" content="{expected_modified}"' in response.text
        assert "property=\"og:type\" content=\"article\"" in response.text
        assert "name=\"twitter:card\" content=\"summary_large_image\"" in response.text
        assert "property=\"og:image\" content=\"https://mysticpantheon.com/static/pantheon-orb-alpha-poster.webp\"" in response.text
        assert "name=\"twitter:image\" content=\"https://mysticpantheon.com/static/pantheon-orb-alpha-poster.webp\"" in response.text
        assert "id=\"site-entity-jsonld\"" in response.text
        assert "\"@id\": \"https://mysticpantheon.com/#organization\"" in response.text
        assert "\"@id\": \"https://mysticpantheon.com/#website\"" in response.text
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
        assert "href=\"/articles#about-pantheon\"" in response.text
        assert "href=\"/articles#editorial-policy\"" in response.text
        assert "href=\"mailto:hello@mysticpantheon.com\"" in response.text
        assert "href=\"https://schema.org/Article\"" in response.text
        assert "/static/pantheon-orb-alpha-poster.webp" in response.text
        assert "ui-brand-mark" in response.text
        assert 'rel="icon" href="/static/pantheon-orb-alpha-poster.webp"' in response.text
        assert "/static/styles.css?v=article-mobile-overflow-20260718-1" in response.text
        assert f"/static/article.js?v={ARTICLE_CACHE_TOKEN}" in response.text


def test_article_raw_html_has_path_specific_seo_shell() -> None:
    client = TestClient(app)
    response = client.get("/articles/tarot/tarot-0001")

    assert response.status_code == 200
    assert "<title>塔羅牌意思總覽：78 張牌、正位逆位與情境怎麼看 | Pantheon</title>" in response.text
    assert 'rel="canonical" href="https://mysticpantheon.com/articles/tarot/tarot-0001"' in response.text
    assert 'property="og:url" content="https://mysticpantheon.com/articles/tarot/tarot-0001"' in response.text
    assert "整理塔羅牌意思、正位逆位、感情與工作情境" in response.text

    article_json = re.search(r'id="article-jsonld">(.*?)</script>', response.text, re.S)
    breadcrumb_json = re.search(r'id="breadcrumb-jsonld">(.*?)</script>', response.text, re.S)
    faq_json = re.search(r'id="faq-jsonld">(.*?)</script>', response.text, re.S)
    assert article_json
    assert breadcrumb_json
    assert faq_json

    article = json.loads(article_json.group(1))
    breadcrumb = json.loads(breadcrumb_json.group(1))
    faq = json.loads(faq_json.group(1))
    assert article["@type"] == "Article"
    assert article["url"] == "https://mysticpantheon.com/articles/tarot/tarot-0001"
    assert article["dateModified"] == ARTICLE_CONTENT_REFRESH_DATE
    assert breadcrumb["@type"] == "BreadcrumbList"
    assert faq["@type"] == "FAQPage"


def test_raw_article_descriptions_meet_citability_length_gate() -> None:
    for path, (_title, description) in RAW_ARTICLE_META.items():
        assert 50 <= len(description) <= 160, path


def test_content_refresh_articles_expose_current_update_date() -> None:
    client = TestClient(app)
    assert len(UPDATED_ARTICLE_PATHS) == 125
    for path in UPDATED_ARTICLE_PATHS:
        response = client.get(path)
        expected_date = article_updated_date(path)
        assert response.status_code == 200, path
        assert f'property="article:modified_time" content="{expected_date}"' in response.text, path
        assert f'"dateModified":"{expected_date}"' in response.text, path
        assert f'<time datetime="{expected_date}" data-article-updated>{expected_date}</time>' in response.text, path

    unchanged = client.get("/articles")
    assert f'property="article:modified_time" content="{ARTICLES_HUB_UPDATED_DATE}"' in unchanged.text
    assert f'"dateModified": "{ARTICLES_HUB_UPDATED_DATE}"' in unchanged.text


def test_tarot_completion_articles_expose_publish_date() -> None:
    client = TestClient(app)
    assert TAROT_COMPLETION_PATHS == set(TAROT_COMPLETION_PUBLIC_ARTICLE_PATHS)
    for path in TAROT_COMPLETION_PUBLIC_ARTICLE_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert f'property="article:modified_time" content="{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'"dateModified":"{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'<time datetime="{ARTICLE_TAROT_COMPLETION_DATE}" data-article-updated>{ARTICLE_TAROT_COMPLETION_DATE}</time>' in response.text, path


def test_tarot_card_face_batch_exposes_current_update_date() -> None:
    client = TestClient(app)
    assert len(TAROT_CARD_FACE_REFRESH_PATHS) == 50
    for path in TAROT_CARD_FACE_REFRESH_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert f'property="article:modified_time" content="{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'"dateModified":"{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path


def test_expansion_50_articles_expose_current_publish_date() -> None:
    client = TestClient(app)
    assert EXPANSION_50_PATHS == set(EXPANSION_50_PUBLIC_ARTICLE_PATHS)
    for path in EXPANSION_50_PUBLIC_ARTICLE_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert f'property="article:modified_time" content="{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'"dateModified":"{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'<time datetime="{ARTICLE_TAROT_COMPLETION_DATE}" data-article-updated>{ARTICLE_TAROT_COMPLETION_DATE}</time>' in response.text, path


def test_expansion_50c_articles_expose_current_publish_date() -> None:
    client = TestClient(app)
    assert EXPANSION_50C_PATHS == set(EXPANSION_50C_PUBLIC_ARTICLE_PATHS)
    for path in EXPANSION_50C_PUBLIC_ARTICLE_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert f'property="article:modified_time" content="{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'"dateModified":"{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'<time datetime="{ARTICLE_TAROT_COMPLETION_DATE}" data-article-updated>{ARTICLE_TAROT_COMPLETION_DATE}</time>' in response.text, path


def test_expansion_50d_articles_expose_current_publish_date() -> None:
    client = TestClient(app)
    assert EXPANSION_50D_PATHS == set(EXPANSION_50D_PUBLIC_ARTICLE_PATHS)
    for path in EXPANSION_50D_PUBLIC_ARTICLE_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert f'property="article:modified_time" content="{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'"dateModified":"{ARTICLE_TAROT_COMPLETION_DATE}"' in response.text, path
        assert f'<time datetime="{ARTICLE_TAROT_COMPLETION_DATE}" data-article-updated>{ARTICLE_TAROT_COMPLETION_DATE}</time>' in response.text, path


def test_cloudflare_pages_exact_rewrites_use_prerendered_article_shells() -> None:
    redirects = Path("app/web/_redirects").read_text()

    assert len(PRERENDER_ARTICLES) == len(PUBLIC_ARTICLE_PATHS)
    for route, target in PRERENDER_ROUTES.items():
        assert f"{route} /{redirect_target(target)} 200" in redirects
        prerendered = Path("app/web") / target
        assert prerendered.exists()
        html = prerendered.read_text()
        assert f'rel="canonical" href="https://mysticpantheon.com{route}"' in html
        assert 'id="article-jsonld">' in html
        assert 'id="breadcrumb-jsonld">' in html
        assert 'id="faq-jsonld">' in html
        assert 'id="article-jsonld"></script>' not in html
    assert redirects.count(" /seo/articles/") == len(PRERENDER_ARTICLES) + len(PRERENDER_HUBS)
    assert redirects.count(" /seo/topics/") == len(PRERENDER_TOPICS)


def test_legacy_article_slugs_use_permanent_server_redirects() -> None:
    redirects = Path("app/web/_redirects").read_text()

    assert len(LEGACY_REDIRECTS) == 30
    assert LEGACY_REDIRECTS["/articles/personality/infp-meaning"] == "/articles/personality/personality-0006"
    assert LEGACY_REDIRECTS["/articles/astro/birth-chart-astrology"] == "/articles/astrology/astrology-0001"
    for source, target in LEGACY_REDIRECTS.items():
        assert f"{source} {target} 301" in redirects

    first_legacy = redirects.index("# BEGIN GENERATED LEGACY ARTICLE REDIRECTS")
    first_rewrite = redirects.index("/articles/personality/personality-0001 /seo/articles/personality/personality-0001/ 200")
    assert first_legacy < first_rewrite


def test_cloudflare_pages_exact_rewrites_use_prerendered_product_hubs() -> None:
    redirects = Path("app/web/_redirects").read_text()
    expected_routes = {
        "/articles/fortune",
        "/articles/personality",
        "/articles/tarot",
        "/articles/astro",
    }

    assert {hub["route"] for hub in PRERENDER_HUBS} == expected_routes
    for hub in PRERENDER_HUBS:
        route = hub["route"]
        target = PRERENDER_ROUTES[route]
        assert f"{route} /{redirect_target(target)} 200" in redirects
        html = (Path("app/web") / target).read_text()
        assert f'rel="canonical" href="https://mysticpantheon.com{route}"' in html
        assert '"@type":"CollectionPage"' in html
        assert '"hasPart":[' in html
        assert 'data-hub-visible-links>' in html
        assert '<h2>分類文章</h2>' in html
        assert 'data-prerender-internal-links' in html
        assert '<section class="article-prerender-links" aria-label="文章內鏈" hidden' in html

    tarot_html = Path("app/web/seo/articles/tarot/index.html").read_text()
    tarot_visible = re.search(r'<section class="article-hub-visible-links ui-panel" aria-label="分類文章" data-hub-visible-links>(.*?)</section>', tarot_html, re.S)
    assert tarot_visible
    assert 6 <= tarot_visible.group(1).count("<li>") <= 12
    assert 'data-topic-visible-links hidden' in tarot_html
    assert 'href="/articles/tarot/tarot-0001"' in tarot_html
    assert 'href="/articles/tarot/tarot-0080"' in tarot_html
    assert 'href="/articles/love/love-0012"' in tarot_html
    astro_html = Path("app/web/seo/articles/astro/index.html").read_text()
    assert 'href="/articles/astrology/astrology-0001"' in astro_html


def test_tarot_hub_reading_guide_is_scanable() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";

const content = buildArticleContent("/articles/tarot", "https://mysticpantheon.com", {});
const guide = content.bodySections.find((section) => section.heading === "這裡先讀哪幾篇塔羅文章？");
console.log(JSON.stringify({
  paragraphCount: guide?.paragraphs.length || 0,
  maxParagraphChars: Math.max(...(guide?.paragraphs || []).map((paragraph) => [...paragraph].length)),
  hasCount: guide?.paragraphs[0]?.includes("目前收錄 92 篇塔羅文章"),
  hasDefinitionPath: guide?.paragraphs.some((paragraph) => paragraph.includes("塔羅牌意思總覽") && paragraph.includes("塔羅牌正位逆位")),
  hasLovePath: guide?.paragraphs.some((paragraph) => paragraph.includes("感情塔羅怎麼問") && paragraph.includes("曖昧")),
  hasFullTitleDump: (guide?.paragraphs.join("") || "").length > 1400,
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["paragraphCount"] == 4
    assert data["maxParagraphChars"] < 260
    assert data["hasCount"]
    assert data["hasDefinitionPath"]
    assert data["hasLovePath"]
    assert not data["hasFullTitleDump"]


def test_cloudflare_pages_exact_rewrites_use_prerendered_topic_hubs() -> None:
    redirects = Path("app/web/_redirects").read_text()
    expected_routes = {
        "/topics/mbti",
        "/topics/personality",
        "/topics/tarot",
        "/topics/upright",
            "/topics/fortune",
            "/topics/bazi",
            "/topics/ziwei",
        "/topics/astrology",
        "/topics/love",
        "/topics/career",
        "/topics/interpersonal",
        "/topics/wealth",
        "/topics/life-direction",
        "/topics/reversed",
    }

    assert {topic["route"] for topic in PRERENDER_TOPICS} == expected_routes
    assert "/topics/fool" not in PRERENDER_ROUTES
    assert "/topics/fool /seo/topics/fool/ 200" not in redirects
    for topic in PRERENDER_TOPICS:
        route = topic["route"]
        target = PRERENDER_ROUTES[route]
        assert f"{route} /{redirect_target(target)} 200" in redirects
        html = (Path("app/web") / target).read_text()
        assert f'rel="canonical" href="https://mysticpantheon.com{route}"' in html
        assert '"@type":"CollectionPage"' in html
        assert '"hasPart":[' in html
        assert 'data-topic-visible-links>' in html
        assert '<h2>相關文章</h2>' in html
        assert 'data-prerender-internal-links' in html
        assert '<section class="article-prerender-links" aria-label="文章內鏈" hidden' in html

    tarot_topic_html = Path("app/web/seo/topics/tarot/index.html").read_text()
    tarot_topic_visible = re.search(r'<section class="article-hub-visible-links ui-panel" aria-label="相關文章" data-topic-visible-links>(.*?)</section>', tarot_topic_html, re.S)
    assert tarot_topic_visible
    assert 6 <= tarot_topic_visible.group(1).count("<li>") <= 12
    assert 'data-hub-visible-links hidden' in tarot_topic_html
    assert 'href="/articles/tarot/tarot-0001"' in tarot_topic_html
    personality_topic_html = Path("app/web/seo/topics/personality/index.html").read_text()
    assert 'href="/articles/personality/personality-0001"' in personality_topic_html


def test_prerender_article_descriptions_meet_citability_length_gate() -> None:
    for article in PRERENDER_ARTICLES:
        assert 50 <= len(article["description"]) <= 160, article["route"]


def test_prerender_articles_have_non_visible_internal_link_clusters() -> None:
    valid_article_routes = {article["route"] for article in PRERENDER_ARTICLES}
    article_counts_by_category = {}
    for article in PRERENDER_ARTICLES:
        category = article["route"].split("/")[2]
        article_counts_by_category[category] = article_counts_by_category.get(category, 0) + 1

    for article in PRERENDER_ARTICLES:
        route = article["route"]
        category = route.split("/")[2]
        links = article["internal_links"]
        article_links = [link for link in links if link["href"] in valid_article_routes]
        same_category_links = [link for link in article_links if link["href"].split("/")[2] == category]
        assert len(links) >= 6, route
        assert any(link["href"] == f"/articles/{article['product_hub']}" for link in links), route
        assert len(same_category_links) >= min(3, article_counts_by_category[category] - 1), route
        assert all(link["href"] == "/articles" or link["href"].startswith("/articles/") for link in links), route

    sample_html = Path("app/web/seo/articles/tarot/tarot-0075/index.html").read_text()
    assert 'data-prerender-internal-links' in sample_html
    assert '<section class="article-prerender-links" aria-label="文章內鏈" hidden' in sample_html
    assert 'href="/articles/tarot"' in sample_html
    assert 'href="/articles/tarot/tarot-0074"' in sample_html


def test_seo_intel_page_exposes_internal_audit_workspace() -> None:
    client = TestClient(app)
    response = client.get("/seo-intel")
    redirects = Path("app/web/_redirects").read_text()
    script = Path("app/web/static/seo-intel.js").read_text()

    assert response.status_code == 200
    assert "SEO 情蒐台" in response.text
    assert "data-audit-form" in response.text
    assert "data-score-grid" in response.text
    assert "name=\"robots\" content=\"noindex,nofollow\"" in response.text
    assert "/static/seo-intel.js?v=20260713-1" in response.text
    assert "/seo-intel /seo-intel.html 200" in redirects
    assert 'https://api.mysticpantheon.com' in script


def test_seo_audit_api_rejects_local_network_target() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/seo/audit", json={"competitor_url": "http://127.0.0.1"})

    assert response.status_code == 422
    assert "內部網路" in response.json()["detail"]


def test_seo_audit_api_uses_bounded_crawl_settings(monkeypatch) -> None:
    calls = []

    def fake_crawl_site(**kwargs):
        calls.append(kwargs)
        return {"base_url": kwargs["base_url"], "site_name": kwargs["site_name"]}

    monkeypatch.setattr("app.api.routes._public_base_url", lambda value: value.rstrip("/"))
    monkeypatch.setattr("app.api.routes.crawl_site", fake_crawl_site)
    monkeypatch.setattr(
        "app.api.routes.build_web_summary",
        lambda competitor, own: {"competitor": competitor, "own_site": own},
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/seo/audit",
        json={
            "competitor_url": "https://competitor.example/",
            "competitor_name": "Competitor",
            "own_site_url": "https://own.example/",
            "own_site_name": "Own",
            "sample_limit": 8,
        },
    )

    assert response.status_code == 200
    assert response.json()["competitor"]["site_name"] == "Competitor"
    assert len(calls) == 2
    assert calls[0]["max_feed_pages"] == 3
    assert calls[0]["max_category_pages"] == 1
    assert calls[0]["sample_limit"] == 8


def test_article_mobile_header_backdrop_stays_inside_viewport() -> None:
    styles_css = Path("app/web/static/styles.css").read_text()

    assert "@media (max-width: 760px)" in styles_css
    assert ".article-page-header::before {\n    inset-inline: 0;" in styles_css


def test_article_breadcrumb_uses_product_and_slug_from_url() -> None:
    article_js = Path("app/web/static/article.js").read_text()
    article_meta_js = Path("app/web/static/article-meta.js").read_text()
    article_seo_js = Path("app/web/static/article-seo.js").read_text()
    article_registry_js = Path("app/web/static/article-registry.js").read_text()
    article_html = Path("app/web/article.html").read_text()
    articles_js = Path("app/web/static/articles.js").read_text()
    motion_visual_js = Path("app/web/static/pantheon-motion-visual.js").read_text()
    styles_css = Path("app/web/static/styles.css").read_text()
    redirects = Path("app/web/_redirects").read_text()
    assert "buildArticleContent(window.location.pathname, window.location.origin" in article_js
    assert "if (content.redirectTo)" in article_js
    assert "window.location.replace(content.redirectTo)" in article_js
    assert "applyArticleSeo(content, dom, window.location.origin)" in article_js
    assert "getArticleSectionRecord(route.product)" in article_meta_js
    assert "getArticleRecord(route.product, route.slug)" in article_meta_js
    assert "DEFAULT_ARTICLE_PUBLISHED_DATE = \"2026-07-10\"" in article_meta_js
    assert "DEFAULT_ARTICLE_UPDATED_DATE = \"2026-07-12\"" in article_meta_js
    assert "new Date().toISOString().slice(0, 10)" not in article_meta_js
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
    assert "renderArticleBody(content, inlineTopicState)" in article_js
    assert "renderHubVisibleLinks(content)" in article_js
    assert "renderArticleNavigation(content)" in article_js
    assert "renderArticleFaq(content)" in article_js
    assert "renderArticleRelated(content)" in article_js
    assert "renderArticleCta(content)" in article_js
    assert "content.hubVisibleLinks?.links?.length" in article_js
    assert "content.navigationLinks" in article_js
    assert "VISIBLE_RELATED_MAX_LINKS = 6" in article_js
    assert "buildVisibleRelatedLinks(content)" in article_js
    assert "content.relatedLinks || []" in article_js
    assert "content.productHref" in article_js
    assert "回到${content.productThemeLabel || content.productCrumbLabel || \"分類\"}文章" in article_js
    assert "links.slice(0, VISIBLE_RELATED_MAX_LINKS)" in article_js
    assert "const navigationLinks = content.navigationLinks || [];" in article_js
    assert "(content.navigationLinks || []).forEach(addLink)" not in article_js
    assert article_js.index("href: content.productHref") < article_js.index("(content.relatedLinks || []).forEach(addLink)")
    assert "article-sequence-button-${direction}" in article_js
    assert "\"← 上一篇\"" in article_js
    assert "\"下一篇 →\"" in article_js
    assert "INLINE_TOPIC_MAX_LINKS = 8" in article_js
    assert "buildInlineTopicState(content)" in article_js
    assert "buildInlineTermsFromTag(tag)" in article_js
    assert "label.match(/^[A-Z][A-Z0-9]{1,}(?=\\s|$)/)" in article_js
    assert "content.displayTagLinks || []" in article_js
    assert "appendInlineTopicLinks(paragraph, text, inlineTopicState)" in article_js
    assert "article-inline-topic-link" in article_js
    assert "data-article-related" in article_html
    assert "data-visible-related-links" in article_html
    assert "data-hub-visible-links" in article_html
    assert "data-topic-visible-links" in article_html
    assert 'document.write(`<base href="${window.location.protocol === "file:" ? "./" : "/"}">`)' in article_html
    assert 'href="static/styles.css?v=article-mobile-overflow-20260718-1"' in article_html
    assert f'src="static/article.js?v={ARTICLE_CACHE_TOKEN}"' in article_html
    assert "data-article-navigation" in article_html
    assert "data-article-cta" in article_html
    assert "id=\"site-entity-jsonld\"" in article_html
    assert "\"@type\": \"Organization\"" in article_html
    assert "\"@type\": \"WebSite\"" in article_html
    assert "property=\"og:image\" content=\"https://mysticpantheon.com/static/pantheon-orb-alpha-poster.webp\"" in article_html
    assert "name=\"twitter:image\" content=\"https://mysticpantheon.com/static/pantheon-orb-alpha-poster.webp\"" in article_html
    assert article_html.index("data-article-navigation") < article_html.index("data-article-faq")
    assert article_html.index("data-article-faq") < article_html.index("data-article-related")
    assert "bodySections: buildBodySections" in article_meta_js
    assert "HUB_VISIBLE_MAX_LINKS = 12" in article_meta_js
    assert "hubVisibleLinks: buildHubVisibleLinks(route" in article_meta_js
    assert "function buildHubVisibleLinks" in article_meta_js
    assert "buildArticleBody(article, productTheme, managedArticle)" in article_meta_js
    assert "ARTICLE_BODY_LIBRARY" in article_meta_js
    assert "buildRelatedLinks(article, managedArticle, productTheme, route)" in article_meta_js
    assert "buildArticleRecommendationLinks(article)" in article_meta_js
    assert "sameCategoryRecommendations" in article_meta_js
    assert "crossCategoryRecommendations" in article_meta_js
    assert "getRecommendedArticleLinks(article)" in article_meta_js
    assert "getRecommendedArticleCandidates(article)" in article_meta_js
    assert "scoreRelatedArticle(article, candidate)" in article_meta_js
    assert "sharedTopicCount * 8" in article_meta_js
    assert "buildArticleCta(article, productTheme, route)" in article_meta_js
    assert "\"mbti-meaning\"" in article_meta_js
    assert "\"magician-card-meaning\"" in article_meta_js
    assert "MBTI 是一套描述人格偏好的分類工具" in article_meta_js
    assert "魔術師牌通常代表資源、行動、創造力" in article_meta_js
    assert "buildFallbackFaq(route, article, productTheme)" in article_meta_js
    assert "buildArticleFaq(route, article, productTheme)" in article_meta_js
    assert "cleanFaqTopic(primary)" in article_meta_js
    assert "想看自己的狀況，應該先整理什麼？" in article_meta_js
    assert "displayTags: buildDisplayTags" in article_meta_js
    assert "INTERNAL_DISPLAY_TAGS" in article_meta_js
    assert "content.displayTags || content.tags || []" in article_js
    assert "content.displayTagLinks" in article_js
    assert "getTopicForLabel" in article_meta_js
    assert "buildTopicContent(route, topic" in article_meta_js
    assert "pickLatestArticles(listArticleRecords())" in articles_js
    assert "pickBalancedArticles(articles, ARTICLE_HUB_DISPLAY_LIMIT)" in articles_js
    assert "getArticlePath(article)" in articles_js
    assert "card.dataset.productTheme = article.product" in articles_js
    assert "initPantheonMotionVisuals()" in articles_js
    assert "pantheon-motion-visual.js?v=articles-hub-20260711-mobile-motion-1" in articles_js
    assert "mask-image: none;" in styles_css
    assert "-webkit-mask-image: none;" in styles_css
    assert "clip-path: inset(15% 0 16% 0);" in styles_css
    assert ".playbackFallback .mediaFrame" in styles_css
    assert "@keyframes pantheonFallbackDrift" in styles_css
    assert 'video.canPlayType("video/webm")' in motion_visual_js
    assert 'document.createElement("source")' in motion_visual_js
    assert "visual.classList.toggle(\"playbackFallback\", playbackFallback)" in motion_visual_js
    assert "stroke: rgb(198 161 91 / 0.8);" in styles_css
    assert "stroke-width: 1.5;" in styles_css
    assert "stroke: rgb(178 145 83 / 0.72);" in styles_css
    assert "stroke: rgb(214 174 96 / 0.68);" in styles_css
    assert "SEARCH_SNIPPETS" in articles_js
    assert "MBTI 用四組偏好組成 16 型人格" in articles_js
    assert "塔羅牌意思先看你正在問的問題" in articles_js
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
    assert "[hidden] {\n  display: none !important;" in styles_css
    assert ".article-related" in styles_css
    assert ".article-hub-visible-links" in styles_css
    assert "grid-template-columns: minmax(0, 760px) minmax(240px, 320px)" in styles_css
    assert ".article-related {\n  grid-column: 1 / -1;" in styles_css
    assert ".article-hub-visible-links {\n  grid-column: 1 / -1;" in styles_css
    assert ".article-visible-link-list" in styles_css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in styles_css
    assert "overflow-wrap: anywhere;" in styles_css
    assert "@media (max-width: 980px)" in styles_css
    assert ".article-visible-link-list {\n    grid-template-columns: 1fr;" in styles_css
    assert ".article-sequence {\n  display: block;" in styles_css
    assert "background: transparent;" in styles_css
    assert ".article-sequence-actions" in styles_css
    assert ".article-sequence-button" in styles_css
    assert ".article-cta-actions" in styles_css
    assert ".article-inline-topic-link" in styles_css
    assert "document.title = content.pageTitle" in article_seo_js
    assert "dom.keywords.content = content.keywords.join" in article_seo_js
    assert "keywords: content.keywords.join" in article_seo_js
    assert "const organizationRef = { \"@id\": `${origin}/#organization` }" in article_seo_js
    assert "const websiteRef = { \"@id\": `${origin}/#website` }" in article_seo_js
    assert "publisher: organizationRef" in article_seo_js
    assert "isPartOf: websiteRef" in article_seo_js
    assert "image," in article_seo_js
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
    assert "TAG_TAXONOMY_POLICY" in article_registry_js
    assert "TAG_TAXONOMY_REGISTRY" in article_registry_js
    assert "export function listTagTaxonomyRecords" in article_registry_js
    assert "taxonomyStatus" in article_registry_js
    assert "indexPolicy" in article_registry_js
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
    assert "/articles/* /article 200" not in redirects
    assert "/topics/* /article 200" not in redirects
    assert "/robots.txt /robots.txt 200" in redirects
    assert "/sitemap.xml /sitemap.xml 200" in redirects
    assert "/llms.txt /llms.txt 200" in redirects
    assert "/ai.txt /ai.txt 200" in redirects
    assert "/feed/ /feed.xml 200" in redirects
    assert "/feed.xml /feed.xml 200" in redirects
    assert "/reading /index.html 200" not in redirects
    assert "/articles /article.html 200" not in redirects
    assert "/personality /personality.html 200" not in redirects
    assert "/strategy /strategy.html 200" not in redirects
    assert "/effects-demo /effects-demo.html 200" not in redirects
    assert "/article-admin /article-admin.html 200" not in redirects


def test_product_and_topic_hubs_expose_visible_article_links() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";

const defaults = {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
};

function summarize(path) {
  const content = buildArticleContent(path, "https://mysticpantheon.com", defaults);
  const module = content.hubVisibleLinks;
  const links = module?.links || [];
  return {
    path,
    type: module?.type || "",
    title: module?.title || "",
    count: links.length,
    hrefs: links.map((item) => item.href),
    labels: links.map((item) => item.label),
    kinds: links.map((item) => item.kind),
    duplicateHrefCount: links.length - new Set(links.map((item) => item.href)).size,
    hasClickHere: links.some((item) => item.label === "點這裡"),
    hasSerialInLabel: links.some((item) => /[a-z]+-\\d{4}/i.test(item.label)),
    hasSerialInKind: links.some((item) => /[a-z]+-\\d{4}/i.test(item.kind)),
  };
}

console.log(JSON.stringify({
  tarotHub: summarize("/articles/tarot"),
  astroHub: summarize("/articles/astro"),
  tarotTopic: summarize("/topics/tarot"),
  article: summarize("/articles/tarot/tarot-0001"),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)

    tarot_hub = data["tarotHub"]
    assert tarot_hub["type"] == "product"
    assert tarot_hub["title"] == "分類文章"
    assert tarot_hub["count"] == 12
    assert tarot_hub["duplicateHrefCount"] == 0
    assert all(href.startswith("/articles/") and href != "/articles/tarot" for href in tarot_hub["hrefs"])
    assert set(tarot_hub["kinds"]) == {"分類文章"}
    assert not tarot_hub["hasClickHere"]
    assert not tarot_hub["hasSerialInLabel"]
    assert not tarot_hub["hasSerialInKind"]

    astro_hub = data["astroHub"]
    assert astro_hub["type"] == "product"
    assert astro_hub["title"] == "分類文章"
    assert astro_hub["count"] == 12
    assert astro_hub["duplicateHrefCount"] == 0

    tarot_topic = data["tarotTopic"]
    assert tarot_topic["type"] == "topic"
    assert tarot_topic["title"] == "相關文章"
    assert tarot_topic["count"] == 12
    assert tarot_topic["duplicateHrefCount"] == 0
    assert all(href.startswith("/articles/") for href in tarot_topic["hrefs"])
    assert set(tarot_topic["kinds"]) == {"相關文章"}
    assert not tarot_topic["hasClickHere"]
    assert not tarot_topic["hasSerialInLabel"]
    assert not tarot_topic["hasSerialInKind"]

    assert data["article"]["type"] == ""
    assert data["article"]["count"] == 0


def test_public_articles_follow_latest_publication_standard() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
const paths = {json.dumps(PUBLIC_ARTICLE_PATHS)};
const data = paths.map((path) => {{
  const content = buildArticleContent(path, "https://mysticpantheon.com", {{
    author: "Pantheon 編輯部",
    updated: "2026-07-10",
  }});
  const headingText = content.bodySections.map((section) => section.heading).join("");
  const bodyText = content.bodySections.flatMap((section) => section.paragraphs).join("");
  const articleText = `${{headingText}}${{bodyText}}`;
  const forbidden = ["全面解析", "深度解析", "不可或缺", "賦能", "總而言之", "值得注意的是", "必看", "一定", "保證", "注定"];
  const forbiddenReaderPhrases = [
    "入口",
    "文章即可",
    "公開文章的任務",
    "公開文章負責",
    "可以先選一個入口",
    "五大主題文章",
    "人生方向入口",
    "焦慮放大器",
    "文章入口整理",
  ];
  const forbiddenTarotCoursePhrases = [
    "什麼時候需要抽牌",
    "什麼時候該從牌義進到抽牌",
    "牌義、逆位和情境要分開讀",
    "先理解 78 張牌",
    "讀塔羅文章時",
  ];
  const scaleVoicePhrases = [
    "通常不是想背牌義",
    "不能替任何人下結論",
    "正位不等於好消息",
    "公開文章只能整理通用牌義",
    "不能替你判定升遷",
    "如果你正在焦慮",
  ];
  const publicationText = `${{articleText}}${{content.title}}`;
  const positivePromiseText = publicationText.replace(/(?:不|未|並非|不是|不能|無法|沒有)(?:一定|保證|注定)/gu, "");
  return {{
    path,
    headings: headingText,
    bodySectionCount: content.bodySections.length,
    bodyLength: [...bodyText].length,
    faqCount: content.faq.length,
    relatedCount: content.relatedLinks.length,
    relatedHasEntrance: content.relatedLinks.some((item) => item.label.includes("入口") || item.kind.includes("入口")),
    relatedAllArticles: content.relatedLinks.every((item) => item.kind === "相關文章"),
    ctaCount: content.cta?.links?.length || 0,
    hasLimit: /不能|不適合|不代表|不是/.test(bodyText),
    minBodyLength: 240,
    hasForbidden: forbidden.some((word) => positivePromiseText.includes(word)),
    hasReaderHostilePhrase: forbiddenReaderPhrases.some((word) => articleText.includes(word) || content.faq.some((item) => item.question.includes(word) || item.answer.includes(word))),
    hasTarotCoursePhrase: path.includes("/tarot/") && forbiddenTarotCoursePhrases.some((word) => articleText.includes(word)),
    hasScaleVoicePhrase: /^\/articles\/tarot\/tarot-00(3[3-9]|[4-6]\d|7[0-6])$/.test(path) && scaleVoicePhrases.some((word) => articleText.includes(word)),
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
        assert record["bodySectionCount"] >= 1, record
        assert record["bodyLength"] >= record["minBodyLength"], record
        assert 3 <= record["faqCount"] <= 5, record
        assert 1 <= record["relatedCount"] <= 5, record
        assert record["relatedAllArticles"], record
        assert not record["relatedHasEntrance"], record
        assert record["ctaCount"] == 0, record
        assert record["hasLimit"], record
        assert not record["hasForbidden"], record
        assert not record["hasReaderHostilePhrase"], record
        assert not record["hasTarotCoursePhrase"], record
        if re.match(r"^/articles/tarot/tarot-00(3[3-9]|[4-6]\d|7[0-6])$", record["path"]):
            assert not record["hasScaleVoicePhrase"], record


def test_next_30_voice_does_not_reintroduce_batch_templates() -> None:
    script = """
import { NEXT_30_ARTICLE_BODY_LIBRARY } from "./app/web/static/article-bodies-next-30.js";

const paragraphs = Object.values(NEXT_30_ARTICLE_BODY_LIBRARY)
  .flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter(Boolean)) {
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }
}
const repeated = [...sentenceCounts.entries()]
  .filter(([, count]) => count > 3)
  .map(([sentence, count]) => ({ sentence, count }));
const forbiddenTemplates = [
  "這比只問",
  "尤其要回到",
  "讀這一節時，可以先把問題寫成一句生活描述",
  "先定位可觀察行為，再決定要溝通、調整或停下",
];
console.log(JSON.stringify({
  articleCount: Object.keys(NEXT_30_ARTICLE_BODY_LIBRARY).length,
  emptyParagraphs: paragraphs.filter((paragraph) => !paragraph.trim()).length,
  repeated,
  forbiddenTemplates: forbiddenTemplates.filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  minChars: Math.min(...Object.values(NEXT_30_ARTICLE_BODY_LIBRARY).map((sections) => sections.flatMap((section) => section.paragraphs).join("").length)),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["articleCount"] == 30
    assert data["emptyParagraphs"] == 0
    assert data["repeated"] == []
    assert data["forbiddenTemplates"] == []
    assert data["minChars"] >= 400


def test_scale_44_voice_does_not_share_full_sentence_templates() -> None:
    script = """
import { SCALE_44_ARTICLE_BODY_LIBRARY } from "./app/web/static/article-bodies-scale-44.js";

const paragraphs = Object.values(SCALE_44_ARTICLE_BODY_LIBRARY)
  .flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }
}
const repeated = [...sentenceCounts.entries()]
  .filter(([, count]) => count > 3)
  .map(([sentence, count]) => ({ sentence, count }));
const forbiddenTemplates = [
  "它比較像把當下狀態照亮",
  "正位不等於好消息",
  "它不只是反過來變壞",
  "如果逆位讓你覺得不安",
  "比較實際的讀法，是把牌義拆成三個問題",
  "公開文章只能整理通用牌義",
  "如果你正在焦慮，先把牌義當成整理問題的工具",
];
console.log(JSON.stringify({
  articleCount: Object.keys(SCALE_44_ARTICLE_BODY_LIBRARY).length,
  emptyParagraphs: paragraphs.filter((paragraph) => !paragraph.trim()).length,
  repeated,
  forbiddenTemplates: forbiddenTemplates.filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  minChars: Math.min(...Object.values(SCALE_44_ARTICLE_BODY_LIBRARY).map((sections) => sections.flatMap((section) => section.paragraphs).join("").length)),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["articleCount"] == 44
    assert data["emptyParagraphs"] == 0
    assert data["repeated"] == []
    assert data["forbiddenTemplates"] == []
    assert data["minChars"] >= 700


def test_tarot_completion_covers_all_78_cards_with_custom_bodies() -> None:
    script = """
import {
  auditArticleVoice,
  getArticlePath,
  listArticleRecords,
} from "./app/web/static/article-registry.js";
import { buildArticleContent } from "./app/web/static/article-meta.js";
import { TAROT_COMPLETION_4_ARTICLE_BODY_LIBRARY } from "./app/web/static/article-bodies-tarot-completion-4.js";

const tarotCards = listArticleRecords().filter((article) => article.id.startsWith("TAROT-") && !article.id.startsWith("TAROT-BASE-"));
const completionCards = tarotCards.filter((article) => [
  "TAROT-PENTACLES-10",
  "TAROT-PENTACLES-PAGE",
  "TAROT-PENTACLES-KNIGHT",
  "TAROT-PENTACLES-QUEEN",
].includes(article.id));
const paragraphs = Object.values(TAROT_COMPLETION_4_ARTICLE_BODY_LIBRARY)
  .flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }
}
const rendered = completionCards.map((article) => {
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  const bodyText = content.bodySections.flatMap((section) => section.paragraphs).join("");
  return {
    id: article.id,
    path: getArticlePath(article),
    bodyLength: [...bodyText].length,
    firstHeading: content.bodySections[0]?.heading || "",
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
    voice: auditArticleVoice(article).status,
  };
});
console.log(JSON.stringify({
  tarotCardCount: tarotCards.length,
  customBodyCount: Object.keys(TAROT_COMPLETION_4_ARTICLE_BODY_LIBRARY).length,
  repeatedSentences: [...sentenceCounts.entries()].filter(([, count]) => count > 3),
  forbiddenTemplates: ["全面解析", "深度解析", "總而言之", "值得注意的是", "通常不是想背牌義"]
    .filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  rendered,
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["tarotCardCount"] == 78
    assert data["customBodyCount"] == 4
    assert data["repeatedSentences"] == []
    assert data["forbiddenTemplates"] == []
    assert len(data["rendered"]) == 4
    for article in data["rendered"]:
        assert article["path"].startswith("/articles/tarot/tarot-00")
        assert article["bodyLength"] >= 1300, article
        assert "牌面" in article["firstHeading"], article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["updated"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["voice"] == "pass", article


def test_tarot_card_face_batch_covers_major_wands_and_cups_without_templates() -> None:
    script = """
import { TAROT_CARD_FACE_50_LIBRARY } from "./app/web/static/article-card-face-50.js";
import { buildArticleContent } from "./app/web/static/article-meta.js";
import { getArticlePath, listArticleRecords } from "./app/web/static/article-registry.js";

const targetArticles = listArticleRecords().filter((article) =>
  article.id.startsWith("TAROT-M")
  || article.id.startsWith("TAROT-WANDS-")
  || article.id.startsWith("TAROT-CUPS-")
);
const paragraphs = Object.values(TAROT_CARD_FACE_50_LIBRARY)
  .flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }
}
const records = targetArticles.map((article) => {
  const sections = TAROT_CARD_FACE_50_LIBRARY[article.slug] || [];
  const addonText = sections.flatMap((section) => section.paragraphs).join("");
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {
    id: article.id,
    slug: article.slug,
    sectionCount: sections.length,
    addonLength: [...addonText].length,
    hasCardFaceHeading: sections.some((section) => section.heading.includes("牌面")),
    renderedCardFaceHeading: content.bodySections.some((section) => section.heading.includes("牌面")),
  };
});
console.log(JSON.stringify({
  targetCount: targetArticles.length,
  libraryCount: Object.keys(TAROT_CARD_FACE_50_LIBRARY).length,
  emptyParagraphCount: paragraphs.filter((paragraph) => !paragraph.trim()).length,
  repeatedSentences: [...sentenceCounts.entries()].filter(([, count]) => count > 3),
  forbiddenTemplates: [
    "全面解析", "深度解析", "總而言之", "值得注意的是", "通常不是想背牌義",
    "牌面不是要你", "這張牌不是在說", "如果你看到這張牌",
  ].filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  records,
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["targetCount"] == 50
    assert data["libraryCount"] == 50
    assert data["emptyParagraphCount"] == 0
    assert data["repeatedSentences"] == []
    assert data["forbiddenTemplates"] == []
    for record in data["records"]:
        assert record["sectionCount"] == 2, record
        assert record["addonLength"] >= 500, record
        assert record["hasCardFaceHeading"], record
        assert record["renderedCardFaceHeading"], record


def test_expansion_50_adds_unique_publishable_articles() -> None:
    script = f"""
import {{ EXPANSION_50_ARTICLE_BODY_LIBRARY, EXPANSION_50_ARTICLE_RECORDS }} from "./app/web/static/article-expansion-50.js";
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";
import {{ REWRITE_RELEASE_001_BODY_OVERRIDES }} from "./app/web/static/article-rewrite-release-001.js";

const expectedPaths = new Set({json.dumps(EXPANSION_50_PUBLIC_ARTICLE_PATHS)});
const allArticles = listArticleRecords();
const expansion = allArticles.filter((article) => expectedPaths.has(getArticlePath(article)));
const paragraphs = Object.values(EXPANSION_50_ARTICLE_BODY_LIBRARY)
  .flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {{
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {{
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }}
}}
const rendered = expansion.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  const bodyText = content.bodySections.flatMap((section) => section.paragraphs).join("");
  const rewrite = REWRITE_RELEASE_001_BODY_OVERRIDES[article.slug];
  return {{
    path: getArticlePath(article),
    bodyLength: [...bodyText].length,
    sectionCount: content.bodySections.length,
    expectedSectionCount: rewrite?.length || 4,
    bodyMatchesRewrite: !rewrite || JSON.stringify(content.bodySections) === JSON.stringify(rewrite),
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
    voice: article.description.length >= 50 && /不|不能|無法/.test(`${{article.description}}${{article.answer}}`),
  }};
}});
console.log(JSON.stringify({{
  totalCount: allArticles.length,
  recordCount: EXPANSION_50_ARTICLE_RECORDS.length,
  bodyCount: Object.keys(EXPANSION_50_ARTICLE_BODY_LIBRARY).length,
  expansionCount: expansion.length,
  uniquePaths: new Set(expansion.map(getArticlePath)).size,
  uniqueTitles: new Set(expansion.map((article) => article.title)).size,
  missingPaths: [...expectedPaths].filter((path) => !expansion.some((article) => getArticlePath(article) === path)),
  repeatedSentences: [...sentenceCounts.entries()].filter(([, count]) => count > 3),
  forbiddenTemplates: ["全面解析", "深度解析", "總而言之", "值得注意的是", "不可或缺", "賦能", "保證", "注定"]
    .filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  rendered,
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert len(EXPANSION_50_PUBLIC_ARTICLE_PATHS) == 50
    assert data["totalCount"] >= 179
    assert data["recordCount"] == 50
    assert data["bodyCount"] == 50
    assert data["expansionCount"] == 50
    assert data["uniquePaths"] == 50
    assert data["uniqueTitles"] == 50
    assert data["missingPaths"] == []
    assert data["repeatedSentences"] == []
    assert data["forbiddenTemplates"] == []
    for article in data["rendered"]:
        assert article["bodyLength"] >= 650, article
        assert article["sectionCount"] == article["expectedSectionCount"], article
        assert article["bodyMatchesRewrite"], article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["updated"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["voice"], article


def test_expansion_50c_adds_parallel_card_articles() -> None:
    script = f"""
import {{ EXPANSION_50C_MBTI_ARTICLE_RECORDS, EXPANSION_50C_MBTI_ARTICLE_BODY_LIBRARY }} from "./app/web/static/article-expansion-50c-mbti.js";
import {{ EXPANSION_50C_ASTRO_ARTICLE_RECORDS, EXPANSION_50C_ASTRO_ARTICLE_BODY_LIBRARY }} from "./app/web/static/article-expansion-50c-astro.js";
import {{ EXPANSION_50C_FORTUNE_ARTICLE_RECORDS, EXPANSION_50C_FORTUNE_ARTICLE_BODY_LIBRARY }} from "./app/web/static/article-expansion-50c-fortune.js";
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(EXPANSION_50C_PUBLIC_ARTICLE_PATHS)});
const records = [
  ...EXPANSION_50C_MBTI_ARTICLE_RECORDS,
  ...EXPANSION_50C_ASTRO_ARTICLE_RECORDS,
  ...EXPANSION_50C_FORTUNE_ARTICLE_RECORDS,
];
const libraries = [
  EXPANSION_50C_MBTI_ARTICLE_BODY_LIBRARY,
  EXPANSION_50C_ASTRO_ARTICLE_BODY_LIBRARY,
  EXPANSION_50C_FORTUNE_ARTICLE_BODY_LIBRARY,
];
const bodies = Object.assign({{}}, ...libraries);
const paragraphs = Object.values(bodies).flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {{
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {{
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }}
}}
const allArticles = listArticleRecords();
const expansion = allArticles.filter((article) => expectedPaths.has(getArticlePath(article)));
const rendered = expansion.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  const bodyText = content.bodySections.flatMap((section) => section.paragraphs).join("");
  return {{
    path: getArticlePath(article),
    bodyLength: [...bodyText].length,
    sectionCount: content.bodySections.length,
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
    hasBoundary: /不|不能|無法/.test(`${{article.description}}${{article.answer}}${{bodyText}}`),
  }};
}});
console.log(JSON.stringify({{
  totalCount: allArticles.length,
  recordCount: records.length,
  bodyCount: Object.keys(bodies).length,
  expansionCount: expansion.length,
  uniqueSerials: new Set(records.map((record) => record.serial)).size,
  uniqueSlugs: new Set(records.map((record) => record.slug)).size,
  uniqueTitles: new Set(records.map((record) => record.title)).size,
  missingPaths: [...expectedPaths].filter((path) => !expansion.some((article) => getArticlePath(article) === path)),
  repeatedSentences: [...sentenceCounts.entries()].filter(([, count]) => count > 3),
  forbiddenTemplates: ["全面解析", "深度解析", "總而言之", "值得注意的是", "不可或缺", "賦能", "必看", "一定", "保證", "注定", "入口"]
    .filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  rendered,
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert len(EXPANSION_50C_PUBLIC_ARTICLE_PATHS) == 50
    assert data["totalCount"] == len(PUBLIC_ARTICLE_PATHS)
    assert data["recordCount"] == 50
    assert data["bodyCount"] == 50
    assert data["expansionCount"] == 50
    assert data["uniqueSerials"] == 50
    assert data["uniqueSlugs"] == 50
    assert data["uniqueTitles"] == 50
    assert data["missingPaths"] == []
    assert data["repeatedSentences"] == []
    assert data["forbiddenTemplates"] == []
    for article in data["rendered"]:
        assert article["bodyLength"] >= 650, article
        assert article["sectionCount"] == 4, article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["updated"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["hasBoundary"], article


def test_expansion_50d_adds_reviewed_articles() -> None:
    script = f"""
import {{ EXPANSION_50D_MBTI_ARTICLE_RECORDS, EXPANSION_50D_MBTI_ARTICLE_BODY_LIBRARY }} from "./app/web/static/article-expansion-50d-mbti.js";
import {{ EXPANSION_50D_ASTRO_ARTICLE_RECORDS, EXPANSION_50D_ASTRO_ARTICLE_BODY_LIBRARY }} from "./app/web/static/article-expansion-50d-astro.js";
import {{ EXPANSION_50D_FORTUNE_ARTICLE_RECORDS, EXPANSION_50D_FORTUNE_ARTICLE_BODY_LIBRARY }} from "./app/web/static/article-expansion-50d-fortune.js";
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(EXPANSION_50D_PUBLIC_ARTICLE_PATHS)});
const records = [
  ...EXPANSION_50D_MBTI_ARTICLE_RECORDS,
  ...EXPANSION_50D_ASTRO_ARTICLE_RECORDS,
  ...EXPANSION_50D_FORTUNE_ARTICLE_RECORDS,
];
const bodies = Object.assign({{}},
  EXPANSION_50D_MBTI_ARTICLE_BODY_LIBRARY,
  EXPANSION_50D_ASTRO_ARTICLE_BODY_LIBRARY,
  EXPANSION_50D_FORTUNE_ARTICLE_BODY_LIBRARY,
);
const paragraphs = Object.values(bodies).flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {{
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {{
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }}
}}
const allArticles = listArticleRecords();
const expansion = allArticles.filter((article) => expectedPaths.has(getArticlePath(article)));
const rendered = expansion.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {{
    path: getArticlePath(article),
    bodyLength: [...content.bodySections.flatMap((section) => section.paragraphs).join("")].length,
    sectionCount: content.bodySections.length,
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
  }};
}});
console.log(JSON.stringify({{
  totalCount: allArticles.length,
  recordCount: records.length,
  bodyCount: Object.keys(bodies).length,
  expansionCount: expansion.length,
  uniqueIds: new Set(records.map((record) => record.id)).size,
  uniqueSerials: new Set(records.map((record) => record.serial)).size,
  uniqueSlugs: new Set(records.map((record) => record.slug)).size,
  uniqueTitles: new Set(records.map((record) => record.title)).size,
  missingPaths: [...expectedPaths].filter((path) => !expansion.some((article) => getArticlePath(article) === path)),
  repeatedSentences: [...sentenceCounts.entries()].filter(([, count]) => count > 3),
  forbiddenTemplates: ["全面解析", "深度解析", "總而言之", "值得注意的是", "不可或缺", "賦能", "必看", "一定", "保證", "注定"]
    .filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  rendered,
}}));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    assert len(EXPANSION_50D_PUBLIC_ARTICLE_PATHS) == 50
    assert data["totalCount"] == len(PUBLIC_ARTICLE_PATHS)
    assert data["recordCount"] == data["bodyCount"] == data["expansionCount"] == 50
    assert data["uniqueIds"] == data["uniqueSerials"] == data["uniqueSlugs"] == data["uniqueTitles"] == 50
    assert data["missingPaths"] == []
    assert data["repeatedSentences"] == []
    assert data["forbiddenTemplates"] == []
    for article in data["rendered"]:
        assert article["bodyLength"] >= 650, article
        assert article["sectionCount"] == 4, article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == ARTICLE_TAROT_COMPLETION_DATE, article
        assert article["updated"] == ARTICLE_TAROT_COMPLETION_DATE, article


def test_expansion_50e_adds_fifty_unique_full_articles() -> None:
    script = f"""
import {{ EXPANSION_50E_ASTRO_ARTICLE_RECORDS as records, EXPANSION_50E_ASTRO_ARTICLE_BODY_LIBRARY as bodies }} from "./app/web/static/article-expansion-50e-astro.js";
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(EXPANSION_50E_PUBLIC_ARTICLE_PATHS)});
const allArticles = listArticleRecords();
const batch = allArticles.filter((article) => expectedPaths.has(getArticlePath(article)));
const paragraphs = Object.values(bodies).flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {{
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {{
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }}
}}
const rendered = batch.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {{
    path: getArticlePath(article),
    bodyLength: [...content.bodySections.flatMap((section) => section.paragraphs).join("")].length,
    sectionCount: content.bodySections.length,
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
  }};
}});
console.log(JSON.stringify({{
  totalCount: allArticles.length,
  recordCount: records.length,
  bodyCount: Object.keys(bodies).length,
  batchCount: batch.length,
  uniqueIds: new Set(records.map((record) => record.id)).size,
  uniqueSerials: new Set(records.map((record) => record.serial)).size,
  uniqueSlugs: new Set(records.map((record) => record.slug)).size,
  uniqueTitles: new Set(records.map((record) => record.title)).size,
  missingPaths: [...expectedPaths].filter((path) => !batch.some((article) => getArticlePath(article) === path)),
  repeatedSentences: [...sentenceCounts.entries()].filter(([, count]) => count > 3),
  forbiddenTemplates: ["全面解析", "深度解析", "總而言之", "值得注意的是", "不可或缺", "賦能", "必看", "注定"]
    .filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  rendered,
}}));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)

    assert len(EXPANSION_50E_PUBLIC_ARTICLE_PATHS) == 50
    assert data["totalCount"] == len(PUBLIC_ARTICLE_PATHS)
    assert data["recordCount"] == 50
    assert data["bodyCount"] == 50
    assert data["batchCount"] == 50
    assert data["uniqueIds"] == 50
    assert data["uniqueSerials"] == 50
    assert data["uniqueSlugs"] == 50
    assert data["uniqueTitles"] == 50
    assert data["missingPaths"] == []
    assert data["repeatedSentences"] == []
    assert data["forbiddenTemplates"] == []
    for article in data["rendered"]:
        assert 800 <= article["bodyLength"] <= 1400, article
        assert article["sectionCount"] == 4, article
        assert 4 <= article["faqCount"] <= 5, article
        assert article["published"] == "2026-07-19", article
        assert article["updated"] == "2026-07-19", article


def test_agy_v1_adds_only_approved_full_standard_articles() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(AGY_V1_PUBLIC_ARTICLE_PATHS)});
const records = listArticleRecords().filter((article) => expectedPaths.has(getArticlePath(article)));
const rendered = records.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {{
    id: article.id,
    path: getArticlePath(article),
    bodyLength: [...content.bodySections.flatMap((section) => section.paragraphs).join("")].length,
    sectionCount: content.bodySections.length,
    paragraphCounts: content.bodySections.map((section) => section.paragraphs.length),
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
  }};
}});
console.log(JSON.stringify(rendered));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    rendered = json.loads(result.stdout)

    assert len(AGY_V1_PUBLIC_ARTICLE_PATHS) == 8
    assert len(rendered) == 8
    assert {article["path"] for article in rendered} == set(AGY_V1_PUBLIC_ARTICLE_PATHS)
    assert len({article["id"] for article in rendered}) == 8
    for article in rendered:
        assert 1300 <= article["bodyLength"] <= 2000, article
        assert article["sectionCount"] == 5, article
        assert article["paragraphCounts"] == [3, 3, 3, 3, 3], article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == "2026-07-18", article
        assert article["updated"] == "2026-07-18", article


def test_agy_asc_batch_02_adds_only_approved_full_standard_articles() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(AGY_ASC_BATCH_02_PUBLIC_ARTICLE_PATHS)});
const records = listArticleRecords().filter((article) => expectedPaths.has(getArticlePath(article)));
const rendered = records.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {{
    id: article.id,
    path: getArticlePath(article),
    bodyLength: [...content.bodySections.flatMap((section) => section.paragraphs).join("")].length,
    sectionCount: content.bodySections.length,
    paragraphCounts: content.bodySections.map((section) => section.paragraphs.length),
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
  }};
}});
console.log(JSON.stringify(rendered));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    rendered = json.loads(result.stdout)

    assert len(AGY_ASC_BATCH_02_PUBLIC_ARTICLE_PATHS) == 5
    assert len(rendered) == 5
    assert {article["path"] for article in rendered} == set(AGY_ASC_BATCH_02_PUBLIC_ARTICLE_PATHS)
    assert len({article["id"] for article in rendered}) == 5
    for article in rendered:
        assert 1300 <= article["bodyLength"] <= 2000, article
        assert article["sectionCount"] == 5, article
        assert article["paragraphCounts"] == [3, 3, 3, 3, 3], article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == "2026-07-18", article
        assert article["updated"] == "2026-07-18", article


def test_agy_asc_venus_batch_03_adds_only_approved_full_standard_articles() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(AGY_ASC_VENUS_BATCH_03_PUBLIC_ARTICLE_PATHS)});
const records = listArticleRecords().filter((article) => expectedPaths.has(getArticlePath(article)));
const rendered = records.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {{
    id: article.id,
    path: getArticlePath(article),
    bodyLength: [...content.bodySections.flatMap((section) => section.paragraphs).join("")].length,
    sectionCount: content.bodySections.length,
    paragraphCounts: content.bodySections.map((section) => section.paragraphs.length),
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
  }};
}});
console.log(JSON.stringify(rendered));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    rendered = json.loads(result.stdout)

    assert len(AGY_ASC_VENUS_BATCH_03_PUBLIC_ARTICLE_PATHS) == 5
    assert len(rendered) == 5
    assert {article["path"] for article in rendered} == set(AGY_ASC_VENUS_BATCH_03_PUBLIC_ARTICLE_PATHS)
    assert len({article["id"] for article in rendered}) == 5
    for article in rendered:
        assert 1300 <= article["bodyLength"] <= 2000, article
        assert article["sectionCount"] == 5, article
        assert article["paragraphCounts"] == [3, 3, 3, 3, 3], article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == "2026-07-18", article
        assert article["updated"] == "2026-07-18", article


def test_agy_venus_batch_04_adds_only_approved_full_standard_articles() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{ getArticlePath, listArticleRecords }} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(AGY_VENUS_BATCH_04_PUBLIC_ARTICLE_PATHS)});
const records = listArticleRecords().filter((article) => expectedPaths.has(getArticlePath(article)));
const rendered = records.map((article) => {{
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com");
  return {{
    id: article.id,
    path: getArticlePath(article),
    bodyLength: [...content.bodySections.flatMap((section) => section.paragraphs).join("")].length,
    sectionCount: content.bodySections.length,
    paragraphCounts: content.bodySections.map((section) => section.paragraphs.length),
    faqCount: content.faq.length,
    published: content.published,
    updated: content.updated,
  }};
}});
console.log(JSON.stringify(rendered));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    rendered = json.loads(result.stdout)

    assert len(AGY_VENUS_BATCH_04_PUBLIC_ARTICLE_PATHS) == 5
    assert len(rendered) == 5
    assert {article["path"] for article in rendered} == set(AGY_VENUS_BATCH_04_PUBLIC_ARTICLE_PATHS)
    assert len({article["id"] for article in rendered}) == 5
    for article in rendered:
        assert 1300 <= article["bodyLength"] <= 2000, article
        assert article["sectionCount"] == 5, article
        assert article["paragraphCounts"] == [3, 3, 3, 3, 3], article
        assert 3 <= article["faqCount"] <= 5, article
        assert article["published"] == "2026-07-18", article
        assert article["updated"] == "2026-07-18", article


def test_initial_31_voice_covers_every_legacy_article_without_batch_templates() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";
import { INITIAL_31_ARTICLE_BODY_LIBRARY } from "./app/web/static/article-bodies-initial-31.js";
import { getArticlePath, listArticleRecords } from "./app/web/static/article-registry.js";
import { REWRITE_RELEASE_001_BODY_OVERRIDES } from "./app/web/static/article-rewrite-release-001.js";

const records = listArticleRecords().filter((article) =>
  /^personality-000[1-8]$/.test(article.urlSlug)
  || /^tarot-000[1-8]$/.test(article.urlSlug)
  || /^fortune-000[1-6]$/.test(article.urlSlug)
  || /^astrology-000[1-4]$/.test(article.urlSlug)
  || /^(love|career|interpersonal|wealth|life-direction)-0001$/.test(article.urlSlug)
);
const paragraphs = Object.values(INITIAL_31_ARTICLE_BODY_LIBRARY)
  .flatMap((sections) => sections.flatMap((section) => section.paragraphs));
const sentenceCounts = new Map();
for (const paragraph of paragraphs) {
  for (const sentence of paragraph.split(/[。！？]/u).map((item) => item.trim()).filter((item) => item.length >= 18)) {
    sentenceCounts.set(sentence, (sentenceCounts.get(sentence) || 0) + 1);
  }
}
const repeated = [...sentenceCounts.entries()]
  .filter(([, count]) => count > 3)
  .map(([sentence, count]) => ({ sentence, count }));
const forbiddenTemplates = [
  "通常不是想背牌義",
  "不能替任何人下結論",
  "正位不等於好消息",
  "全面解析",
  "深度解析",
];
const coverage = records.map((article) => {
  const content = buildArticleContent(getArticlePath(article), "https://mysticpantheon.com", {});
  const expectedBody = REWRITE_RELEASE_001_BODY_OVERRIDES[article.slug] || INITIAL_31_ARTICLE_BODY_LIBRARY[article.slug];
  return {
    slug: article.slug,
    hasLibrary: Boolean(INITIAL_31_ARTICLE_BODY_LIBRARY[article.slug]),
    bodyPreserved: expectedBody.every((expectedSection) =>
      content.bodySections.some((actualSection) => JSON.stringify(actualSection) === JSON.stringify(expectedSection))
    ),
  };
});
console.log(JSON.stringify({
  recordCount: records.length,
  libraryCount: Object.keys(INITIAL_31_ARTICLE_BODY_LIBRARY).length,
  emptyParagraphs: paragraphs.filter((paragraph) => !paragraph.trim()).length,
  repeated,
  forbiddenTemplates: forbiddenTemplates.filter((phrase) => paragraphs.some((paragraph) => paragraph.includes(phrase))),
  missing: coverage.filter((item) => !item.hasLibrary || !item.bodyPreserved),
  minChars: Math.min(...Object.values(INITIAL_31_ARTICLE_BODY_LIBRARY).map((sections) => sections.flatMap((section) => section.paragraphs).join("").length)),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["recordCount"] == 31
    assert data["libraryCount"] == 31
    assert data["emptyParagraphs"] == 0
    assert data["repeated"] == []
    assert data["forbiddenTemplates"] == []
    assert data["missing"] == []
    assert data["minChars"] >= 300


def test_public_generated_text_does_not_leak_internal_entry_language() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";
import { getArticlePath, listArticleRecords, listTopicRecords } from "./app/web/static/article-registry.js";

const paths = [
  "/articles",
  "/articles/personality",
  "/articles/tarot",
  "/articles/fortune",
  "/articles/astro",
  ...listArticleRecords().map(getArticlePath),
  ...listTopicRecords().map((topic) => topic.href),
];
const forbidden = [
  "入口",
  "文章即可",
  "讀文章即可",
  "哪個入口",
  "從哪個入口開始",
  "文章入口",
  "人生方向入口",
  "五大主題文章",
  "公開文章負責",
  "公開文章的任務",
  "標籤頁",
  "集結頁",
  "工具課",
];
const records = paths.map((path) => {
  const content = buildArticleContent(path, "https://mysticpantheon.com", {
    author: "Pantheon 編輯部",
    updated: "2026-07-10",
  });
  const text = [
    content.title,
    content.pageTitle,
    content.description,
    content.sectionDescription,
    content.answer,
    ...(content.bodySections || []).flatMap((section) => [
      section.heading,
      ...(section.paragraphs || []),
      ...(section.links || []).flatMap((link) => [link.label, link.kind]),
    ]),
    ...(content.faq || []).flatMap((item) => [item.question, item.answer]),
    ...(content.relatedLinks || []).flatMap((link) => [link.label, link.kind]),
    ...(content.displayTagLinks || []).map((tag) => tag.label),
  ].filter(Boolean).join("\\n");
  return {
    path,
    hits: forbidden.filter((phrase) => text.includes(phrase)),
  };
}).filter((record) => record.hits.length);
console.log(JSON.stringify(records));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == []


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
const sequenceArticle = buildArticleContent("/articles/personality/personality-0002", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
const topic = buildArticleContent("/topics/personality", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
const ineligibleTopic = buildArticleContent("/topics/fool", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
console.log(JSON.stringify({
  legacy,
  ineligibleTopic,
  canonical: {
    title: canonical.title,
    serial: canonical.serial,
    canonicalPath: canonical.canonicalPath,
    relatedLabels: canonical.relatedLinks.map((item) => item.label),
    interpersonalTagHref: canonical.displayTagLinks.find((tag) => tag.label === "人際")?.href || "",
  },
  sequenceArticle: {
    navigationLinks: sequenceArticle.navigationLinks,
    relatedLinks: sequenceArticle.relatedLinks.map((item) => ({
      label: item.label,
      kind: item.kind,
      href: item.href,
      category: item.href.split("/")[2],
    })),
  },
  topic: {
    title: topic.title,
    canonicalPath: topic.canonicalPath,
    bodyLinkCount: topic.bodySections.flatMap((section) => section.links || []).length,
    faqCount: topic.faq.length,
    relatedCount: topic.relatedLinks.length,
    bodyText: topic.bodySections.flatMap((section) => [section.heading, ...section.paragraphs]).join(" "),
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
    assert [item["kind"] for item in data["sequenceArticle"]["navigationLinks"]] == ["上一篇", "下一篇"]
    assert not any("000" in label for label in data["canonical"]["relatedLabels"])
    related_links = data["sequenceArticle"]["relatedLinks"]
    assert len(related_links) <= 5
    assert all(item["kind"] == "相關文章" for item in related_links)
    assert not any("入口" in item["label"] or "入口" in item["kind"] for item in related_links)
    assert not any("000" in item["label"] for item in related_links)
    same_category = [item for item in related_links if item["category"] == "personality"]
    cross_category = [item for item in related_links if item["category"] != "personality"]
    assert len(same_category) <= 2
    assert len(cross_category) <= 3
    assert len({item["category"] for item in cross_category}) == len(cross_category)
    assert data["canonical"]["interpersonalTagHref"] == "/topics/interpersonal"
    assert data["ineligibleTopic"] == {"redirectTo": "/articles"}
    assert data["topic"]["canonicalPath"] == "/topics/personality"
    assert data["topic"]["title"] == "人格 相關文章"
    assert data["topic"]["bodyLinkCount"] >= 3
    assert data["topic"]["faqCount"] == 0
    assert data["topic"]["relatedCount"] == 0
    assert "標籤頁" not in data["topic"]["bodyText"]
    assert "集結頁" not in data["topic"]["bodyText"]


def test_article_body_runtime_contract_keeps_custom_body_unenriched() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";
import { REWRITE_RELEASE_001_BODY_OVERRIDES } from "./app/web/static/article-rewrite-release-001.js";

const content = buildArticleContent("/articles/personality/personality-0001", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
console.log(JSON.stringify({
  headings: content.bodySections.map((section) => section.heading),
  bodyMatchesRewrite: JSON.stringify(content.bodySections) === JSON.stringify(REWRITE_RELEASE_001_BODY_OVERRIDES["mbti-meaning"]),
  text: content.bodySections.flatMap((section) => [section.heading, ...section.paragraphs]).join("\\n"),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert len(data["headings"]) == 5
    assert data["bodyMatchesRewrite"]
    assert "查「MBTI 是什麼」時" not in data["text"]
    assert "感情、工作、人際各看哪一層？" not in data["text"]
    assert "人格文章不要只讀單一類型" not in data["text"]
    assert "什麼時候需要回到自己的互動經驗？" not in data["text"]


def test_article_body_runtime_contract_fallback_is_reader_facing() -> None:
    script = """
import { buildArticleContent } from "./app/web/static/article-meta.js";

const content = buildArticleContent("/articles/astrology/astrology-0004", "https://mysticpantheon.com", {
  author: "Pantheon 編輯部",
  updated: "2026-07-10",
});
console.log(JSON.stringify({
  bodySectionCount: content.bodySections.length,
  headings: content.bodySections.map((section) => section.heading),
  text: content.bodySections.flatMap((section) => [section.heading, ...section.paragraphs]).join("\\n"),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["bodySectionCount"] == 3
    assert data["headings"] == [
        "星座感情運勢先看互動節奏，不急著問結果",
        "運勢內容要和當下事件對照",
        "星座感情運勢不是對方心意通知",
    ]
    assert "查「星座感情運勢」時" not in data["text"]
    assert "延伸閱讀" not in data["text"]
    assert "下一步可以讀什麼" not in data["text"]
    assert "公開文章負責" not in data["text"]
    assert "文章入口" not in data["text"]


def test_article_knowledge_base_serial_and_topic_contract() -> None:
    script = f"""
import {{ buildArticleContent }} from "./app/web/static/article-meta.js";
import {{
  ARTICLE_URL_CONTRACT,
  TAG_TAXONOMY_POLICY,
  TAG_TAXONOMY_REGISTRY,
  getArticlePath,
  listArticleRecords,
  listArticlesForTopic,
  listTagManagementRecords,
  listTagTaxonomyRecords,
  listTopicRecords,
  normalizePublicTagLabel,
}} from "./app/web/static/article-registry.js";

const expectedPaths = new Set({json.dumps(PUBLIC_ARTICLE_PATHS)});
const records = listArticleRecords();
const topics = listTopicRecords();
const tagManagement = listTagManagementRecords();
const taxonomy = listTagTaxonomyRecords();
const articleSummaries = records.map((article) => {{
  const path = getArticlePath(article);
  const content = buildArticleContent(path, "https://mysticpantheon.com", {{
    author: "Pantheon 編輯部",
    updated: "2026-07-10",
  }});
  return {{
    id: article.id,
    path,
    serial: article.serial,
    canonicalPath: content.canonicalPath,
    visibleTagCount: content.displayTagLinks.length,
    linkedTagCount: content.displayTagLinks.filter((tag) => tag.href?.startsWith("/topics/")).length,
    internalTagVisible: content.displayTagLinks.some((tag) => ["SEO", "AEO", "GEO", "公開文章", "通用知識"].includes(tag.label)),
  }};
}});

const topicSummaries = topics.map((topic) => {{
  const topicArticlePaths = listArticlesForTopic(topic.slug).map(getArticlePath);
  const content = buildArticleContent(topic.href, "https://mysticpantheon.com", {{
    author: "Pantheon 編輯部",
    updated: "2026-07-10",
  }});
  return {{
    id: topic.id,
    slug: topic.slug,
    href: topic.href,
    canonicalPath: content.canonicalPath,
    contentType: content.contentType,
    bodyLinkCount: content.bodySections.flatMap((section) => section.links || []).length,
    bodyText: content.bodySections.flatMap((section) => [section.heading, ...section.paragraphs]).join(" "),
    faqCount: content.faq.length,
    relatedCount: content.relatedLinks.length,
    topicArticleCount: topicArticlePaths.length,
  }};
}});

console.log(JSON.stringify({{
  articlePattern: ARTICLE_URL_CONTRACT.articlePattern,
  topicPattern: ARTICLE_URL_CONTRACT.topicPattern,
  articleSummaries,
  topicSummaries,
  personalityPaths: listArticlesForTopic("personality").map(getArticlePath),
  fortunePaths: listArticlesForTopic("fortune").map(getArticlePath),
  interpersonalPaths: listArticlesForTopic("interpersonal").map(getArticlePath),
  generatedTopicLabels: topics.map((topic) => topic.label),
  taxonomyPolicy: TAG_TAXONOMY_POLICY,
  taxonomyCount: TAG_TAXONOMY_REGISTRY.length,
  normalizedTags: {{
    career: normalizePublicTagLabel("轉職"),
    tarot: normalizePublicTagLabel("塔羅牌意思"),
    internal: normalizePublicTagLabel("SEO"),
  }},
  taxonomy: taxonomy.map((item) => ({{
    topicSlug: item.topicSlug,
    canonicalLabel: item.canonicalLabel,
    indexPolicy: item.indexPolicy,
    articleCount: item.articleCount,
    minArticles: item.minArticles,
    isGenerated: item.isGenerated,
    href: item.href,
  }})),
  tagManagement: tagManagement.map((tag) => ({{
    label: tag.label,
    slug: tag.slug,
    articleCount: tag.articleCount,
    minArticles: tag.minArticles,
    taxonomyStatus: tag.taxonomyStatus,
    canonicalLabel: tag.canonicalLabel,
    indexPolicy: tag.indexPolicy,
    isGenerated: tag.isGenerated,
    href: tag.href,
  }})),
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["articlePattern"] == "/articles/{category}/{category}-{number}"
    assert data["topicPattern"] == "/topics/{topic-slug}"

    expected_paths = set(PUBLIC_ARTICLE_PATHS)
    assert {record["path"] for record in data["articleSummaries"]} == expected_paths
    for record in data["articleSummaries"]:
        category, slug = record["path"].removeprefix("/articles/").split("/")
        assert record["path"] in expected_paths
        assert record["serial"] == slug
        assert record["serial"].startswith(f"{category}-")
        assert record["canonicalPath"] == record["path"]
        assert record["visibleTagCount"] >= 1
        assert record["linkedTagCount"] >= 0
        assert not record["internalTagVisible"]

    assert data["taxonomyPolicy"]["publicTopicMinArticles"] == 10
    assert "SEO" in data["taxonomyPolicy"]["internalOnlyTags"]
    assert data["taxonomyCount"] == 20
    assert data["normalizedTags"] == {"career": "工作", "tarot": "塔羅", "internal": "SEO"}

    assert "/articles/personality/personality-0001" in data["personalityPaths"]
    assert "/articles/fortune/fortune-0001" in data["fortunePaths"]
    assert "/articles/interpersonal/interpersonal-0001" in data["interpersonalPaths"]
    assert set(data["generatedTopicLabels"]) == {"MBTI", "人格", "塔羅", "正位", "命盤", "八字", "紫微", "星盤", "感情", "工作", "人際", "財富", "人生方向", "逆位"}
    taxonomy = {item["topicSlug"]: item for item in data["taxonomy"]}
    assert set(taxonomy) == {
        "mbti",
        "personality",
        "tarot",
        "upright",
        "fortune",
        "bazi",
        "ziwei",
        "astrology",
        "love",
        "career",
        "interpersonal",
        "wealth",
        "life-direction",
        "reversed",
        "fool",
        "magician",
        "lovers",
        "death",
        "tower",
        "world",
    }
    assert taxonomy["career"]["canonicalLabel"] == "工作"
    assert taxonomy["career"]["indexPolicy"] == "min_articles"
    assert taxonomy["career"]["href"] == "/topics/career"
    assert taxonomy["fool"]["indexPolicy"] == "min_articles"
    assert taxonomy["fool"]["isGenerated"] is False
    assert taxonomy["fool"]["href"] == ""
    tag_management = {item["slug"]: item for item in data["tagManagement"]}
    assert tag_management["fool"]["label"] == "愚者"
    assert tag_management["fool"]["taxonomyStatus"] == "managed"
    assert tag_management["fool"]["canonicalLabel"] == "愚者"
    assert tag_management["fool"]["indexPolicy"] == "min_articles"
    assert tag_management["fool"]["articleCount"] < tag_management["fool"]["minArticles"]
    assert tag_management["fool"]["isGenerated"] is False
    assert tag_management["fool"]["href"] == ""
    assert tag_management["tarot"]["articleCount"] >= tag_management["tarot"]["minArticles"]
    assert tag_management["tarot"]["isGenerated"] is True
    assert tag_management["tarot"]["href"] == "/topics/tarot"

    topic_ids = [topic["id"] for topic in data["topicSummaries"]]
    assert len(topic_ids) == len(set(topic_ids))
    for topic in data["topicSummaries"]:
        assert topic["id"].startswith("topic-")
        assert topic["id"].split("-")[1].isdigit()
        assert len(topic["id"].split("-")[1]) == 4
        assert topic["href"] == f"/topics/{topic['slug']}"
        assert topic["canonicalPath"] == topic["href"]
        assert topic["contentType"] == "CollectionPage"
        assert topic["bodyLinkCount"] == min(topic["topicArticleCount"], 24)
        assert topic["faqCount"] == 0
        assert topic["relatedCount"] == 0
        assert "標籤頁" not in topic["bodyText"]
        assert "集結頁" not in topic["bodyText"]


def test_article_admin_serves_management_console() -> None:
    client = TestClient(app)
    response = client.get("/article-admin")
    assert response.status_code == 200
    assert "文章管理" in response.text
    assert "強制關鍵字標籤" in response.text
    assert "文章 Section 描述" in response.text
    assert "內容圖譜" in response.text
    assert "標籤集結頁管理" in response.text
    assert "語氣品質 Gate" in response.text
    assert "所有文章" in response.text
    assert "name=\"robots\" content=\"noindex,nofollow\"" in response.text
    assert "/static/article-admin.js" in response.text
    assert "/static/pantheon-orb-alpha-poster.webp" in response.text
    assert "ui-brand-mark" in response.text
    article_admin_js = Path("app/web/static/article-admin.js").read_text()
    assert "buildArticleGraph" in article_admin_js
    assert "renderHumanizerGate" in article_admin_js
    assert "listArticleVoiceAudits" in article_admin_js
    assert "listTagManagementRecords" in article_admin_js
    assert "renderTagManagement" in article_admin_js
    assert "ui-panel" in article_admin_js
    assert "ui-chip-list" in article_admin_js
    assert "ui-chip" in article_admin_js
    assert "data-graph-summary" in response.text
    assert "data-graph-links" in response.text
    assert "data-tag-management-table" in response.text
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
    assert "https://mysticpantheon.com/topics/tarot" in sitemap.text
    assert "https://mysticpantheon.com/topics/personality" in sitemap.text
    assert "https://mysticpantheon.com/topics/mbti" in sitemap.text
    assert "https://mysticpantheon.com/topics/upright" in sitemap.text
    assert "https://mysticpantheon.com/topics/interpersonal" in sitemap.text
    assert "https://mysticpantheon.com/topics/reversed" in sitemap.text
    assert "https://mysticpantheon.com/topics/fool" not in sitemap.text
    assert "https://mysticpantheon.com/articles/bazi" not in sitemap.text
    assert "https://mysticpantheon.com/articles/mbti" not in sitemap.text
    assert "https://mysticpantheon.com/articles/personality/relationships-stuck" not in sitemap.text

    sitemap_lastmods = re.findall(r"<lastmod>([^<]+)</lastmod>", sitemap.text)
    assert len(sitemap_lastmods) == len(PRERENDER_ARTICLES)
    for article in PRERENDER_ARTICLES:
        entry = f"<loc>https://mysticpantheon.com{article['route']}</loc>\n    <lastmod>{article['updated']}</lastmod>"
        assert entry in sitemap.text


def test_foundation_ai_and_feed_endpoints_are_served() -> None:
    client = TestClient(app)
    llms = client.get("/llms.txt")
    ai = client.get("/ai.txt")
    feed = client.get("/feed/")
    feed_xml = client.get("/feed.xml")
    feed_file = Path("app/web/feed.xml").read_text()
    feed_links = re.findall(r"<link>(https://mysticpantheon\.com/articles/[^<]+)</link>", feed_file)
    expected_feed_links = [f"https://mysticpantheon.com{article['route']}" for article in PRERENDER_ARTICLES]

    assert llms.status_code == 200
    assert "Pantheon" in llms.text
    assert "https://mysticpantheon.com/articles" in llms.text
    assert "<!doctype html>" not in llms.text.lower()
    assert endpoint_label(
        {"status": llms.status_code, "content_type": llms.headers["content-type"], "bytes": len(llms.content), "body": llms.text},
        "llms_txt",
    ) == "present"

    assert ai.status_code == 200
    assert "AI Usage Policy" in ai.text
    assert "Allowed:" in ai.text
    assert "Attribution:" in ai.text
    assert "<!doctype html>" not in ai.text.lower()
    assert endpoint_label(
        {"status": ai.status_code, "content_type": ai.headers["content-type"], "bytes": len(ai.content), "body": ai.text},
        "ai_txt",
    ) == "present"

    assert feed.status_code == 200
    assert feed_xml.status_code == 200
    assert "<rss version=\"2.0\"" in feed.text
    assert "Pantheon 最新文章" in feed.text
    assert feed.text == feed_xml.text
    assert "https://mysticpantheon.com/articles/tarot/tarot-0001" in feed.text
    assert "https://mysticpantheon.com/articles/tarot/tarot-0080" in feed.text
    assert "https://mysticpantheon.com/articles/life-direction/life-direction-0001" in feed.text
    assert "<link>https://mysticpantheon.com/articles/life-direction</link>" not in feed.text
    assert feed_file.count("<item>") == len(PRERENDER_ARTICLES)
    assert feed_links == expected_feed_links


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

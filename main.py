from app.api.routes import router
from app.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import html
import json
import re
from pathlib import Path


WEB_DIR = Path(__file__).parent / "app" / "web"
SITE_ORIGIN = "https://mysticpantheon.com"
ARTICLE_PUBLISHED_DATE = "2026-07-10"
ARTICLE_UPDATED_DATE = "2026-07-12"
ARTICLE_CONTENT_REFRESH_DATE = "2026-07-14"
ARTICLE_TAROT_COMPLETION_DATE = "2026-07-16"
TAROT_COMPLETION_PATHS = {
    *(f"/articles/tarot/tarot-{serial:04d}" for serial in range(77, 81)),
}
TAROT_CARD_FACE_REFRESH_PATHS = {
    *(f"/articles/tarot/tarot-{serial:04d}" for serial in range(3, 25)),
    "/articles/tarot/tarot-0027",
    "/articles/tarot/tarot-0028",
    *(f"/articles/tarot/tarot-{serial:04d}" for serial in range(32, 58)),
}
EXPANSION_50_PATHS = {
    *(f"/articles/love/love-{serial:04d}" for serial in range(5, 13)),
    *(f"/articles/career/career-{serial:04d}" for serial in range(5, 13)),
    *(f"/articles/interpersonal/interpersonal-{serial:04d}" for serial in range(3, 13)),
    *(f"/articles/wealth/wealth-{serial:04d}" for serial in range(4, 13)),
    *(f"/articles/life-direction/life-direction-{serial:04d}" for serial in range(3, 13)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(6, 11)),
}
EXPANSION_50C_PATHS = {
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(21, 37)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(11, 28)),
    *(f"/articles/fortune/fortune-{serial:04d}" for serial in range(10, 27)),
}
EXPANSION_50D_PATHS = {
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(37, 53)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(28, 45)),
    *(f"/articles/fortune/fortune-{serial:04d}" for serial in range(27, 44)),
}
UPDATED_ARTICLE_PATHS = {
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(1, 9)),
    *(f"/articles/tarot/tarot-{serial:04d}" for serial in range(1, 9)),
    *(f"/articles/fortune/fortune-{serial:04d}" for serial in range(1, 7)),
    *(f"/articles/astrology/astrology-{serial:04d}" for serial in range(1, 5)),
    "/articles/love/love-0001",
    "/articles/career/career-0001",
    "/articles/interpersonal/interpersonal-0001",
    "/articles/wealth/wealth-0001",
    "/articles/life-direction/life-direction-0001",
    *(f"/articles/tarot/tarot-{serial:04d}" for serial in range(9, 77)),
    *(f"/articles/personality/personality-{serial:04d}" for serial in range(9, 21)),
    *(f"/articles/fortune/fortune-{serial:04d}" for serial in range(7, 10)),
    *(f"/articles/love/love-{serial:04d}" for serial in range(2, 5)),
    *(f"/articles/career/career-{serial:04d}" for serial in range(2, 5)),
    "/articles/astrology/astrology-0005",
    "/articles/interpersonal/interpersonal-0002",
    "/articles/wealth/wealth-0002",
    "/articles/wealth/wealth-0003",
    "/articles/life-direction/life-direction-0002",
}

PRODUCT_META = {
    "fortune": ("命盤文章", "Pantheon 命盤文章，整理八字、紫微斗數、命宮、財帛宮與人生節奏主題。"),
    "personality": ("人格文章", "Pantheon 人格文章，整理 MBTI、16 型人格、人際模式與自我理解主題。"),
    "tarot": ("塔羅文章", "Pantheon 塔羅文章，整理塔羅牌意思、正位逆位、感情、工作與人生方向主題。"),
    "astro": ("星座文章", "Pantheon 星座文章，整理星盤、太陽星座、月亮星座、上升星座與情緒安全感主題。"),
    "astrology": ("星座文章", "Pantheon 星座文章，整理星盤、太陽星座、月亮星座、上升星座與情緒安全感主題。"),
    "love": ("感情文章", "Pantheon 感情文章，整理曖昧、復合、安全感、關係卡住與相處模式主題。"),
    "career": ("事業文章", "Pantheon 事業文章，整理轉職、工作壓力、努力未被看見與職涯方向主題。"),
    "interpersonal": ("人際文章", "Pantheon 人際文章，整理人際關係、互動界線、溝通模式與社交疲憊主題。"),
    "wealth": ("財富文章", "Pantheon 財富文章，整理存錢、資源分配、安全感與財富習慣主題。"),
    "life-direction": ("人生方向文章", "Pantheon 人生方向文章，整理迷惘、選擇、自我理解與長期方向主題。"),
}

RAW_ARTICLE_META = {
    "/articles/tarot/tarot-0001": (
        "塔羅牌意思總覽：78 張牌、正位逆位與情境怎麼看",
        "整理塔羅牌意思、正位逆位、感情與工作情境，說明可以怎麼用、不能怎麼用，以及公開文章不能取代個人判讀的限制。",
    ),
    "/articles/personality/personality-0001": (
        "MBTI 是什麼？16 型人格、測驗與自我理解怎麼看",
        "說明 MBTI、16 型人格與測驗使用邊界，協助讀者把人格偏好放回感情、工作與人際情境，而不是把類型當成固定答案。",
    ),
    "/articles/fortune/fortune-0001": (
        "命盤是什麼？八字、紫微斗數和星盤差在哪",
        "白話整理命盤、八字、紫微斗數與星盤的差異，說明各自適合觀察的問題與使用邊界，避免把單一工具寫成完整個人結論。",
    ),
    "/articles/interpersonal/interpersonal-0001": (
        "人際關係卡住怎麼辦？人格、塔羅與命盤可以看什麼",
        "整理人際關係、互動界線與溝通模式，先釐清具體情境、可觀察線索與使用限制，再連到人格、命盤與塔羅脈絡。",
    ),
    "/articles/life-direction": (
        "人生方向迷惘怎麼辦？塔羅、人格與命盤能幫你整理什麼",
        "人生方向迷惘時，先分清感情、事業、人際、財富或自我節奏哪裡最卡，再選擇適合的整理工具、使用限制與下一步。",
    ),
}


def product_label(product: str) -> str:
    return PRODUCT_META.get(product, ("最新文章", ""))[0]


def article_updated_date(path: str) -> str:
    if path in TAROT_COMPLETION_PATHS or path in TAROT_CARD_FACE_REFRESH_PATHS or path in EXPANSION_50_PATHS or path in EXPANSION_50C_PATHS or path in EXPANSION_50D_PATHS:
        return ARTICLE_TAROT_COMPLETION_DATE
    return ARTICLE_CONTENT_REFRESH_DATE if path in UPDATED_ARTICLE_PATHS else ARTICLE_UPDATED_DATE


def raw_article_meta(path: str) -> dict[str, str]:
    if path in RAW_ARTICLE_META:
        title, description = RAW_ARTICLE_META[path]
        product = path.split("/")[2] if path.startswith("/articles/") else ""
        content_type = "Article"
    elif path.startswith("/topics/"):
        topic = path.rsplit("/", 1)[-1].replace("-", " ")
        title = f"{topic} 相關文章"
        description = f"Pantheon 主題頁，整理與 {topic} 相關的公開文章、常見問題與延伸閱讀。"
        product = "topics"
        content_type = "CollectionPage"
    else:
        parts = path.strip("/").split("/")
        product = parts[1] if len(parts) > 1 else ""
        label, fallback_description = PRODUCT_META.get(product, ("最新文章", "Pantheon 最新文章，整理命盤、人格、塔羅、星座與人生方向主題。"))
        title = label
        description = fallback_description
        content_type = "Article" if len(parts) >= 3 else "CollectionPage"
    return {
        "title": title,
        "page_title": f"{title} | Pantheon",
        "description": description,
        "canonical": f"{SITE_ORIGIN}{path}",
        "path": path,
        "product": product,
        "product_label": product_label(product),
        "content_type": content_type,
        "published": ARTICLE_PUBLISHED_DATE,
        "updated": article_updated_date(path),
    }


def json_script(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def build_prerender_internal_links(links: list[dict[str, str]]) -> str:
    if not links:
        return ""
    anchors = []
    for link in links:
        href = html.escape(link["href"], quote=True)
        label = html.escape(link["label"], quote=False)
        anchors.append(f'<a href="{href}">{label}</a>')
    return (
        '<section class="article-prerender-links" aria-label="文章內鏈" hidden data-prerender-internal-links>'
        "<h2>文章內鏈</h2>"
        f"<nav>{''.join(anchors)}</nav>"
        "</section>"
    )


def build_prerender_visible_links(meta: dict[str, str]) -> str:
    links = meta.get("visible_links", [])
    if not links:
        return ""
    title = html.escape(meta.get("visible_links_title", "相關文章"), quote=False)
    data_hook = "data-topic-visible-links" if meta.get("visible_links_type") == "topic" else "data-hub-visible-links"
    rows = []
    for link in links:
        href = html.escape(link["href"], quote=True)
        label = html.escape(link["label"], quote=False)
        kind = html.escape(link.get("kind", meta.get("visible_links_title", "相關文章")), quote=False)
        rows.append(f'<li><a href="{href}">{label}</a><span>{kind}</span></li>')
    return (
        f'<section class="article-hub-visible-links ui-panel" aria-label="{title}" {data_hook}>'
        f"<h2>{title}</h2>"
        f'<ul class="article-link-list article-visible-link-list">{"".join(rows)}</ul>'
        "</section>"
    )


def build_raw_jsonld(meta: dict[str, str]) -> tuple[dict, dict, dict]:
    organization_ref = {"@id": f"{SITE_ORIGIN}/#organization"}
    website_ref = {"@id": f"{SITE_ORIGIN}/#website"}
    main_type = meta["content_type"]
    if main_type == "CollectionPage":
        linked_pages = [
            {
                "@type": "WebPage",
                "name": link["label"],
                "url": f"{SITE_ORIGIN}{link['href']}",
            }
            for link in meta.get("internal_links", [])
            if link.get("href", "").startswith("/articles")
        ]
        main = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": meta["title"],
            "description": meta["description"],
            "inLanguage": "zh-Hant-TW",
            "url": meta["canonical"],
            "mainEntityOfPage": meta["canonical"],
            "isPartOf": website_ref,
            "publisher": organization_ref,
            "image": f"{SITE_ORIGIN}/static/pantheon-orb-alpha-poster.webp",
        }
        if linked_pages:
            main["hasPart"] = linked_pages
    else:
        main = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta["title"],
            "description": meta["description"],
            "inLanguage": "zh-Hant-TW",
            "url": meta["canonical"],
            "mainEntityOfPage": meta["canonical"],
            "image": f"{SITE_ORIGIN}/static/pantheon-orb-alpha-poster.webp",
            "datePublished": meta.get("published", ARTICLE_PUBLISHED_DATE),
            "dateModified": meta.get("updated", ARTICLE_UPDATED_DATE),
            "author": {"@type": "Organization", "name": "Pantheon 編輯部"},
            "publisher": organization_ref,
            "isPartOf": website_ref,
            "articleSection": meta["product_label"],
        }
    breadcrumb_items = [
        {"name": "Pantheon", "item": f"{SITE_ORIGIN}/articles"},
        {"name": "最新文章", "item": f"{SITE_ORIGIN}/articles"},
        {"name": meta["title"], "item": meta["canonical"]},
    ]
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index + 1, "name": item["name"], "item": item["item"]}
            for index, item in enumerate(breadcrumb_items)
        ],
    }
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "這篇文章可以取代個人判讀嗎？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "不可以。公開文章只整理共通知識與使用邊界，個人判讀仍需回到你的資料、問題與當下情境。",
                },
            }
        ],
    }
    return main, breadcrumb, faq


def replace_meta_content(markup: str, attr_name: str, attr_value: str, content_value: str) -> str:
    escaped = html.escape(content_value, quote=True)
    pattern = rf'(<meta\s+{attr_name}=["\']{re.escape(attr_value)}["\'][^>]*content=["\'])([^"\']*)(["\'])'
    return re.sub(pattern, rf"\g<1>{escaped}\3", markup, count=1)


def render_article_shell_from_meta(meta: dict[str, str]) -> HTMLResponse:
    markup = (WEB_DIR / "article.html").read_text(encoding="utf-8")
    # Raw shell supports file:// preview; HTTP responses keep site-root asset URLs.
    markup = markup.replace('href="static/', 'href="/static/').replace('src="static/', 'src="/static/')
    page_title = html.escape(meta["page_title"], quote=False)
    description = meta["description"]
    canonical = html.escape(meta["canonical"], quote=True)
    updated = meta.get("updated", ARTICLE_UPDATED_DATE)
    main_jsonld, breadcrumb_jsonld, faq_jsonld = build_raw_jsonld(meta)
    markup = re.sub(r"<title>.*?</title>", f"<title>{page_title}</title>", markup, count=1)
    markup = replace_meta_content(markup, "name", "description", description)
    markup = replace_meta_content(markup, "property", "og:title", meta["page_title"])
    markup = replace_meta_content(markup, "property", "og:description", description)
    markup = replace_meta_content(markup, "property", "og:url", meta["canonical"])
    markup = replace_meta_content(markup, "property", "article:modified_time", updated)
    markup = replace_meta_content(markup, "name", "twitter:title", meta["page_title"])
    markup = replace_meta_content(markup, "name", "twitter:description", description)
    markup = re.sub(r'(<link rel="canonical" href=")[^"]+(")', rf"\g<1>{canonical}\2", markup, count=1)
    markup = re.sub(
        r'(<script type="application/ld\+json" id="article-jsonld">).*?(</script>)',
        rf"\g<1>{json_script(main_jsonld)}\2",
        markup,
        count=1,
        flags=re.S,
    )
    markup = re.sub(
        r'(<script type="application/ld\+json" id="breadcrumb-jsonld">).*?(</script>)',
        rf"\g<1>{json_script(breadcrumb_jsonld)}\2",
        markup,
        count=1,
        flags=re.S,
    )
    markup = re.sub(
        r'(<script type="application/ld\+json" id="faq-jsonld">).*?(</script>)',
        rf"\g<1>{json_script(faq_jsonld)}\2",
        markup,
        count=1,
        flags=re.S,
    )
    markup = re.sub(r"(<h1 data-article-title>).*?(</h1>)", rf"\g<1>{page_title.replace(' | Pantheon', '')}\2", markup, count=1, flags=re.S)
    markup = re.sub(
        r'(<time datetime=")[^"]+(" data-article-updated>)[^<]*(</time>)',
        rf"\g<1>{html.escape(updated, quote=True)}\g<2>{html.escape(updated, quote=False)}\g<3>",
        markup,
        count=1,
    )
    markup = re.sub(
        r"(<p class=\"article-section-description\" data-section-description>).*?(</p>)",
        rf"\g<1>{html.escape(description, quote=False)}\2",
        markup,
        count=1,
        flags=re.S,
    )
    visible_links_markup = build_prerender_visible_links(meta)
    if visible_links_markup:
        visible_links_type = meta.get("visible_links_type")
        data_hook = "data-topic-visible-links" if visible_links_type == "topic" else "data-hub-visible-links"
        pattern = rf'<section class="article-hub-visible-links ui-panel" aria-label="[^"]+" {data_hook} hidden></section>'
        markup = re.sub(pattern, visible_links_markup, markup, count=1)
    markup = markup.replace("</article>", f"{build_prerender_internal_links(meta.get('internal_links', []))}</article>", 1)
    return HTMLResponse(markup)


def render_article_shell(path: str) -> HTMLResponse:
    return render_article_shell_from_meta(raw_article_meta(path))


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Pure Python modular divination engine.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https://(www\.)?mysticpantheon\.com|https://[a-z0-9-]+\.pages\.dev",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router, prefix="/api/v1")
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse(url="/articles", status_code=302)

    @app.get("/reading", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    def reading_page() -> RedirectResponse:
        return RedirectResponse(url="/articles", status_code=302)

    @app.get("/personality", include_in_schema=False)
    @app.get("/personality.html", include_in_schema=False)
    def personality_page() -> RedirectResponse:
        return RedirectResponse(url="/articles", status_code=302)

    @app.get("/effects-demo", include_in_schema=False)
    @app.get("/effects-demo.html", include_in_schema=False)
    def effects_demo_page() -> RedirectResponse:
        return RedirectResponse(url="/articles", status_code=302)

    @app.get("/strategy", include_in_schema=False)
    @app.get("/strategy.html", include_in_schema=False)
    def strategy_page() -> RedirectResponse:
        return RedirectResponse(url="/articles", status_code=302)

    @app.get("/articles", include_in_schema=False)
    def articles_page() -> FileResponse:
        return FileResponse(WEB_DIR / "articles.html")

    @app.get("/articles/intents/{intent}", include_in_schema=False)
    def article_intent_page(intent: str) -> HTMLResponse:
        return render_article_shell(f"/articles/intents/{intent}")

    @app.get("/articles/{product}", include_in_schema=False)
    def article_product_page(product: str) -> HTMLResponse:
        return render_article_shell(f"/articles/{product}")

    @app.get("/articles/{product}/{slug}", include_in_schema=False)
    def article_page(product: str, slug: str) -> HTMLResponse:
        return render_article_shell(f"/articles/{product}/{slug}")

    @app.get("/topics/{topic}", include_in_schema=False)
    def topic_page(topic: str) -> HTMLResponse:
        return render_article_shell(f"/topics/{topic}")

    @app.get("/article-admin", include_in_schema=False)
    def article_admin_page() -> FileResponse:
        return FileResponse(WEB_DIR / "article-admin.html")

    @app.get("/seo-intel", include_in_schema=False)
    @app.get("/seo-intel.html", include_in_schema=False)
    def seo_intel_page() -> FileResponse:
        return FileResponse(WEB_DIR / "seo-intel.html")

    @app.get("/robots.txt", include_in_schema=False)
    def robots_txt() -> FileResponse:
        return FileResponse(WEB_DIR / "robots.txt")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap_xml() -> FileResponse:
        return FileResponse(WEB_DIR / "sitemap.xml")

    @app.get("/llms.txt", include_in_schema=False)
    def llms_txt() -> FileResponse:
        return FileResponse(WEB_DIR / "llms.txt", media_type="text/plain; charset=utf-8")

    @app.get("/ai.txt", include_in_schema=False)
    def ai_txt() -> FileResponse:
        return FileResponse(WEB_DIR / "ai.txt", media_type="text/plain; charset=utf-8")

    @app.get("/feed/", include_in_schema=False)
    @app.get("/feed.xml", include_in_schema=False)
    def feed_xml() -> FileResponse:
        return FileResponse(WEB_DIR / "feed.xml", media_type="application/rss+xml; charset=utf-8")

    return app


app = create_app()

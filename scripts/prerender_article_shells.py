import argparse
from collections import Counter
import hashlib
import html
from pathlib import Path
import json
import re
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from main import ARTICLE_PUBLISHED_DATE, ARTICLE_UPDATED_DATE, SITE_ORIGIN, article_updated_date, render_article_shell_from_meta  # noqa: E402
from scripts import agy_seo_copy_pipeline as pipeline  # noqa: E402


WEB_DIR = Path("app/web")
REDIRECTS_PATH = WEB_DIR / "_redirects"
SITEMAP_PATH = WEB_DIR / "sitemap.xml"
PRODUCT_HUBS = {
    "fortune": {
        "title": "命盤文章",
        "description": "Pantheon 命盤文章主頁，整理命盤是什麼、八字、紫微斗數、事業、財富與人生方向主題，公開文章只提供通用知識與閱讀順序。",
    },
    "personality": {
        "title": "人格文章",
        "description": "Pantheon 人格文章主頁，整理 MBTI、16 型人格、人際互動與自我理解主題，協助讀者分清偏好、情境與使用限制。",
    },
    "tarot": {
        "title": "塔羅文章",
        "description": "Pantheon 塔羅文章主頁，整理塔羅牌意思、正位逆位、感情、工作與人生方向問題，先看牌義再回到具體情境。",
    },
    "astro": {
        "title": "星座文章",
        "description": "Pantheon 星座文章主頁，整理星盤、上升星座、月亮星座、金星星座與感情需求，避免把單一星座當成完整結論。",
    },
}
MIN_CITABILITY_DESCRIPTION_LEN = 50
MAX_CITABILITY_DESCRIPTION_LEN = 160


def registry_articles() -> list[dict[str, Any]]:
    script = """
import { listArticleRecords, getArticlePath, getArticleSectionRecord } from './app/web/static/article-registry.js';
import { buildArticleContent } from './app/web/static/article-meta.js';
const records = listArticleRecords().map((article) => {
  const path = getArticlePath(article);
  const content = buildArticleContent(path, 'https://mysticpantheon.com', {
    author: 'Pantheon 編輯部',
    updated: article.updated || '',
  });
  return {
    id: article.id || '',
    path,
    legacyPaths: [...new Set([
      `/articles/${article.articleCategory || article.product}/${article.slug}`,
      `/articles/${article.product}/${article.slug}`,
    ])],
    serial: article.serial || '',
    urlSlug: article.urlSlug || '',
    primaryKeyword: article.primaryKeyword || '',
    title: article.title || '',
    description: article.description || '',
    answer: content.answer || article.answer || '',
    faq: content.faq || article.faq || [],
    bodySections: content.bodySections || [],
    publicationPolicy: article.publicationPolicy || null,
    productLabel: getArticleSectionRecord(article.section)?.label || article.articleCategory || article.product || '文章',
    productHub: getArticleSectionRecord(article.section)?.product || article.product || article.articleCategory || 'fortune',
    articleCategory: article.articleCategory || article.product || '',
    contentType: 'Article',
    published: article.published || '',
    updated: article.updated || '',
  };
});
console.log(JSON.stringify(records));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def registry_topics() -> list[dict]:
    script = """
import { listTopicRecords, listArticlesForTopic, getArticlePath } from './app/web/static/article-registry.js';
const records = listTopicRecords().map((topic) => ({
  route: topic.href,
  title: `${topic.label} 相關文章`,
  label: topic.label,
  slug: topic.slug,
  articleCount: topic.articleCount,
  articles: listArticlesForTopic(topic.slug).map((article) => ({
    path: getArticlePath(article),
    title: article.title || '',
  })),
}));
console.log(JSON.stringify(records));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def citability_description(description: str) -> str:
    value = " ".join(str(description or "").split())
    if len(value) >= MIN_CITABILITY_DESCRIPTION_LEN:
        return value[:MAX_CITABILITY_DESCRIPTION_LEN]
    suffix = "閱讀時仍要搭配具體問題、情境脈絡與使用限制，不能直接當成個人結論。"
    return f"{value}{suffix}"[:MAX_CITABILITY_DESCRIPTION_LEN]


def target_for_route(route: str) -> str:
    return f"seo/{route.strip('/')}/index.html"


def article_category(route: str) -> str:
    parts = route.strip("/").split("/")
    return parts[1] if len(parts) >= 2 else ""


def add_unique_link(links: list[dict[str, str]], href: str, label: str, current_route: str) -> None:
    if not href or href == current_route:
        return
    if any(link["href"] == href for link in links):
        return
    links.append({"href": href, "label": label})


def build_internal_links(article: dict[str, str], articles: list[dict[str, str]]) -> list[dict[str, str]]:
    route = article["route"]
    category = article_category(route)
    product_hub = article.get("product_hub") or category
    links: list[dict[str, str]] = []
    add_unique_link(links, f"/articles/{product_hub}", f"{article['product_label']}文章", route)

    same_category = [item for item in articles if article_category(item["route"]) == category]
    current_index = next((index for index, item in enumerate(same_category) if item["route"] == route), -1)
    if current_index > 0:
        previous_article = same_category[current_index - 1]
        add_unique_link(links, previous_article["route"], f"上一篇：{previous_article['title']}", route)
    if 0 <= current_index < len(same_category) - 1:
        next_article = same_category[current_index + 1]
        add_unique_link(links, next_article["route"], f"下一篇：{next_article['title']}", route)

    for related in same_category:
        add_unique_link(links, related["route"], related["title"], route)
        if len([link for link in links if article_category(link["href"]) == category]) >= min(5, max(len(same_category) - 1, 0)):
            break

    same_product = [item for item in articles if item.get("product_hub") == product_hub]
    for related in same_product:
        add_unique_link(links, related["route"], related["title"], route)
        if len(links) >= 8:
            break

    add_unique_link(links, "/articles", "最新文章", route)
    return links[:8]


def build_hub_internal_links(hub_route: str, product: str, articles: list[dict[str, str]]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    add_unique_link(links, "/articles", "最新文章", hub_route)
    for hub_product, hub in PRODUCT_HUBS.items():
        if hub_product != product:
            add_unique_link(links, f"/articles/{hub_product}", hub["title"], hub_route)

    product_articles = [article for article in articles if article.get("product_hub") == product]
    for article in [*product_articles[:4], *product_articles[-2:]]:
        add_unique_link(links, article["route"], article["title"], hub_route)
        if len(links) >= 10:
            break
    return links[:10]


def build_topic_internal_links(topic: dict) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    add_unique_link(links, "/articles", "最新文章", topic["route"])
    for article in topic["articles"][:12]:
        add_unique_link(links, article["path"], article["title"], topic["route"])
    return links[:12]


def build_hub_visible_links(product: str, articles: list[dict[str, str]]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    product_articles = [article for article in articles if article.get("product_hub") == product]
    groups: dict[str, list[dict[str, str]]] = {}
    for article in product_articles:
        groups.setdefault(article_category(article["route"]), []).append(article)
    quota = max(1, 12 // max(len(groups), 1))
    selected: list[dict[str, str]] = []
    for items in groups.values():
        head_count = (quota + 1) // 2
        tail_items = items[-(quota // 2):] if quota // 2 else []
        for article in [*items[:head_count], *tail_items]:
            if article not in selected:
                selected.append(article)
    for article in product_articles:
        if article not in selected and len(selected) < 12:
            selected.append(article)
    for article in selected[:12]:
        add_unique_link(links, article["route"], article["title"], f"/articles/{product}")
    return [{**link, "kind": "分類文章"} for link in links]


def build_topic_visible_links(topic: dict) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for article in topic["articles"][:12]:
        add_unique_link(links, article["path"], article["title"], topic["route"])
    return [{**link, "kind": "相關文章"} for link in links]


def build_prerender_articles() -> list[dict[str, Any]]:
    articles = []
    for record in registry_articles():
        route = record["path"]
        description = citability_description(record["description"])
        articles.append(
            {
                "route": route,
                "legacy_routes": [legacy for legacy in record["legacyPaths"] if legacy != route],
                "target": target_for_route(route),
                "title": record["title"],
                "page_title": f"{record['title']} | Pantheon",
                "description": description,
                "canonical": f"{SITE_ORIGIN}{route}",
                "path": route,
                "product": route.split("/")[2],
                "product_label": record["productLabel"],
                "product_hub": record["productHub"],
                "content_type": record["contentType"],
                "id": record["id"],
                "serial": record["serial"],
                "urlSlug": record["urlSlug"],
                "primaryKeyword": record["primaryKeyword"],
                "answer": record["answer"],
                "faq": record["faq"],
                "bodySections": record["bodySections"],
                "publicationPolicy": record["publicationPolicy"],
                "published": record["published"],
                "updated": record["updated"],
            }
        )
    for article in articles:
        article["internal_links"] = build_internal_links(article, articles)
    return articles


def build_prerender_hubs(articles: list[dict[str, str]]) -> list[dict[str, str]]:
    hubs = []
    for product, hub in PRODUCT_HUBS.items():
        route = f"/articles/{product}"
        hubs.append(
            {
                "route": route,
                "target": target_for_route(route),
                "title": hub["title"],
                "page_title": f"{hub['title']} | Pantheon",
                "description": citability_description(hub["description"]),
                "canonical": f"{SITE_ORIGIN}{route}",
                "path": route,
                "product": product,
                "product_label": hub["title"].removesuffix("文章"),
                "product_hub": product,
                "content_type": "CollectionPage",
                "internal_links": build_hub_internal_links(route, product, articles),
                "visible_links_type": "product",
                "visible_links_title": "分類文章",
                "visible_links": build_hub_visible_links(product, articles),
            }
        )
    return hubs


def build_prerender_topics() -> list[dict[str, str]]:
    topics = []
    for topic in registry_topics():
        route = topic["route"]
        description = (
            f"整理 Pantheon 中提到 {topic['label']} 的公開文章，收錄 {topic['articleCount']} 篇可延伸閱讀，"
            "方便讀者直接找到相關內容與使用限制。"
        )
        topics.append(
            {
                "route": route,
                "target": target_for_route(route),
                "title": topic["title"],
                "page_title": f"{topic['title']} | Pantheon",
                "description": citability_description(description),
                "canonical": f"{SITE_ORIGIN}{route}",
                "path": route,
                "product": "topics",
                "product_label": "主題",
                "product_hub": "topics",
                "content_type": "CollectionPage",
                "internal_links": build_topic_internal_links(topic),
                "visible_links_type": "topic",
                "visible_links_title": "相關文章",
                "visible_links": build_topic_visible_links(topic),
            }
        )
    return topics


PRERENDER_ARTICLES = build_prerender_articles()
PRERENDER_HUBS = build_prerender_hubs(PRERENDER_ARTICLES)
PRERENDER_TOPICS = build_prerender_topics()
PRERENDER_PAGES = [*PRERENDER_HUBS, *PRERENDER_TOPICS, *PRERENDER_ARTICLES]
PRERENDER_ROUTES = {page["route"]: page["target"] for page in PRERENDER_PAGES}
LEGACY_REDIRECTS_START = "# BEGIN GENERATED LEGACY ARTICLE REDIRECTS"
LEGACY_REDIRECTS_END = "# END GENERATED LEGACY ARTICLE REDIRECTS"
HISTORICAL_LEGACY_ROUTES = {
    "/articles/astro/ascendant-sign-meaning",
    "/articles/astro/birth-chart-astrology",
    "/articles/astro/moon-sign-meaning",
    "/articles/fortune/bazi-meaning",
    "/articles/fortune/birth-chart-meaning",
    "/articles/fortune/career-fortune",
    "/articles/fortune/life-direction",
    "/articles/fortune/ming-gong-meaning",
    "/articles/fortune/spouse-palace-meaning",
    "/articles/fortune/wealth-fortune",
    "/articles/fortune/wealth-palace-meaning",
    "/articles/fortune/ziwei-doushu-meaning",
    "/articles/personality/16-personalities",
    "/articles/personality/enfp-meaning",
    "/articles/personality/infj-meaning",
    "/articles/personality/infp-meaning",
    "/articles/personality/intj-meaning",
    "/articles/personality/mbti-accuracy",
    "/articles/personality/mbti-meaning",
    "/articles/personality/mbti-test",
    "/articles/personality/relationships-stuck",
    "/articles/tarot/death-card-meaning",
    "/articles/tarot/fool-card-meaning",
    "/articles/tarot/love-tarot-questions",
    "/articles/tarot/lovers-card-meaning",
    "/articles/tarot/magician-card-meaning",
    "/articles/tarot/tarot-card-meanings",
    "/articles/tarot/tower-card-meaning",
    "/articles/tarot/upright-reversed",
    "/articles/tarot/world-card-meaning",
}
LEGACY_REDIRECTS = {
    legacy_route: article["route"]
    for article in PRERENDER_ARTICLES
    for legacy_route in article["legacy_routes"]
    if legacy_route in HISTORICAL_LEGACY_ROUTES
}


def redirect_target(target: str) -> str:
    return f"{target.removesuffix('/index.html')}/"


def update_redirects() -> None:
    lines = REDIRECTS_PATH.read_text(encoding="utf-8").splitlines()
    without_legacy_block: list[str] = []
    in_legacy_block = False
    for line in lines:
        if line == LEGACY_REDIRECTS_START:
            in_legacy_block = True
            continue
        if line == LEGACY_REDIRECTS_END:
            in_legacy_block = False
            continue
        if not in_legacy_block:
            without_legacy_block.append(line)

    generated_rewrites = [f"{route} /{redirect_target(target)} 200" for route, target in PRERENDER_ROUTES.items()]
    generated_legacy_redirects = [f"{source} {target} 301" for source, target in LEGACY_REDIRECTS.items()]
    filtered = [
        line
        for line in without_legacy_block
        if not (
            (line.startswith("/articles/") and " /seo/articles/" in line)
            or (line.startswith("/topics/") and " /seo/topics/" in line)
        )
    ]
    insert_at = filtered.index("/articles /articles 200")
    generated = [
        LEGACY_REDIRECTS_START,
        *generated_legacy_redirects,
        LEGACY_REDIRECTS_END,
        *generated_rewrites,
    ]
    next_lines = filtered[:insert_at] + generated + filtered[insert_at:]
    REDIRECTS_PATH.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def update_sitemap() -> None:
    routes = [
        "/articles",
        *(page["route"] for page in PRERENDER_HUBS),
        *(page["route"] for page in PRERENDER_ARTICLES),
        *(page["route"] for page in PRERENDER_TOPICS),
    ]
    unique_routes = list(dict.fromkeys(routes))
    article_lastmods = {article["route"]: article["updated"] for article in PRERENDER_ARTICLES}
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for route in unique_routes:
        lines.extend(["  <url>", f"    <loc>{SITE_ORIGIN}{route}</loc>"])
        if lastmod := article_lastmods.get(route):
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    SITEMAP_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _json_script(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _replace_section(markup: str, data_attribute: str, replacement: str) -> str:
    pattern = rf'<section\b[^>]*\b{re.escape(data_attribute)}\b[^>]*>.*?</section>'
    updated, count = re.subn(pattern, replacement, markup, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"prerender section marker missing: {data_attribute}")
    return updated


def render_article_specific_shell(article: dict[str, Any]) -> str:
    """把 answer、正文與文章專屬 FAQ 放進 initial HTML，不依賴 hydration。"""
    markup = render_article_shell_from_meta(article).body.decode("utf-8")
    policy = pipeline.load_article_publication_policy()
    identity = policy["identity"]
    author_name = html.escape(identity["author_name"], quote=False)
    author_url = html.escape(identity["author_url"], quote=True)
    author_id = identity["author_id"]
    markup = re.sub(
        r'<span data-article-author>.*?</span>',
        f'<span data-article-author><a href="{author_url}">{author_name}</a></span>',
        markup,
        count=1,
        flags=re.S,
    )

    answer_markup = (
        '<section class="article-answer-summary ui-panel" aria-label="重點答案" data-answer-summary>'
        "<h2>重點答案</h2>"
        f'<p data-answer-text>{html.escape(str(article["answer"]), quote=False)}</p>'
        "</section>"
    )
    markup = _replace_section(markup, "data-answer-summary", answer_markup)
    body_rows = []
    for section in article["bodySections"]:
        body_rows.append(f"<h2>{html.escape(str(section['heading']), quote=False)}</h2>")
        body_rows.extend(
            f"<p>{html.escape(str(paragraph), quote=False)}</p>"
            for paragraph in section["paragraphs"]
        )
    body_markup = (
        '<section class="article-body" aria-label="文章內容" data-article-body>'
        f"{''.join(body_rows)}"
        "</section>"
    )
    markup = _replace_section(markup, "data-article-body", body_markup)
    faq_rows = [
        "<details>"
        f"<summary>{html.escape(str(item['question']), quote=False)}</summary>"
        f"<p>{html.escape(str(item['answer']), quote=False)}</p>"
        "</details>"
        for item in article["faq"]
    ]
    faq_markup = (
        '<section class="article-faq ui-panel" aria-label="常見問題" data-article-faq>'
        "<h2>常見問題</h2>"
        f"{''.join(faq_rows)}"
        "</section>"
    )
    markup = _replace_section(markup, "data-article-faq", faq_markup)

    main_jsonld: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["description"],
        "inLanguage": "zh-Hant-TW",
        "url": article["canonical"],
        "mainEntityOfPage": article["canonical"],
        "image": f"{SITE_ORIGIN}/static/pantheon-orb-alpha-poster.webp",
        "author": {
            "@type": "Organization",
            "name": identity["author_name"],
            "url": identity["author_url"],
            "@id": author_id,
        },
        "publisher": {"@id": f"{SITE_ORIGIN}/#organization"},
        "isPartOf": {"@id": f"{SITE_ORIGIN}/#website"},
        "articleSection": article["product_label"],
        "articleBody": "\n".join(
            str(paragraph)
            for section in article["bodySections"]
            for paragraph in section["paragraphs"]
        ),
    }
    if article.get("published"):
        main_jsonld["datePublished"] = article["published"]
    if article.get("updated"):
        main_jsonld["dateModified"] = article["updated"]
    faq_jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
            }
            for item in article["faq"]
        ],
    }
    markup = re.sub(
        r'(<script type="application/ld\+json" id="article-jsonld">).*?(</script>)',
        lambda match: f"{match.group(1)}{_json_script(main_jsonld)}{match.group(2)}",
        markup,
        count=1,
        flags=re.S,
    )
    markup = re.sub(
        r'(<script type="application/ld\+json" id="faq-jsonld">).*?(</script>)',
        lambda match: f"{match.group(1)}{_json_script(faq_jsonld)}{match.group(2)}",
        markup,
        count=1,
        flags=re.S,
    )
    if article.get("published"):
        markup = re.sub(
            r'(<meta property="article:published_time" content=")[^"]*(" />)',
            lambda match: f"{match.group(1)}{html.escape(str(article['published']), quote=True)}{match.group(2)}",
            markup,
            count=1,
        )
    else:
        markup = re.sub(
            r'\s*<meta property="article:published_time"[^>]*>',
            "",
            markup,
            count=1,
        )
    if not article.get("updated"):
        markup = re.sub(
            r"<span>更新：<time\b[^>]*data-article-updated[^>]*>.*?</time></span>",
            '<span data-article-date-missing>更新日期待真實資料補齊</span>',
            markup,
            count=1,
            flags=re.S,
        )
        markup = re.sub(
            r'\s*<meta property="article:modified_time"[^>]*>',
            "",
            markup,
            count=1,
        )
    return markup


def prerender_artifact_findings(
    article: dict[str, Any],
    markup: str,
    *,
    mode: str | None = None,
    reference_articles: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    policy_mode = mode
    if policy_mode is None:
        change_type = (
            article.get("publicationPolicy") or {}
        ).get("changeType")
        policy_mode = (
            "rewrite_existing_body"
            if change_type == "substantive_rewrite"
            else "create"
        )
    if policy_mode not in {"create", "rewrite_existing_body"}:
        raise ValueError(f"unsupported prerender policy mode: {policy_mode}")
    findings = pipeline.article_publication_policy_findings(
        article,
        mode=policy_mode,
        reference_articles=reference_articles,
    )
    article_id = str(article["id"])

    def add(code: str, message: str) -> None:
        findings.append(pipeline._policy_finding(article_id, code, message))

    if "這篇文章會先回答核心問題" in markup or "最新文章會把命盤" in markup:
        add("initial_html_complete", "initial HTML 仍含通用 placeholder")
    if html.escape(str(article["answer"]), quote=False) not in markup:
        add("initial_html_complete", "answer 未出現在 initial HTML")
    for section in article["bodySections"]:
        for paragraph in section["paragraphs"]:
            if html.escape(str(paragraph), quote=False) not in markup:
                add("initial_html_complete", "重要正文未完整出現在 initial HTML")
                break
    article_match = re.search(
        r'<script type="application/ld\+json" id="article-jsonld">(.*?)</script>',
        markup,
        flags=re.S,
    )
    faq_match = re.search(
        r'<script type="application/ld\+json" id="faq-jsonld">(.*?)</script>',
        markup,
        flags=re.S,
    )
    if not article_match or not faq_match:
        add("structured_visible_match", "Article/FAQ JSON-LD 缺失")
        return findings
    try:
        article_jsonld = json.loads(article_match.group(1))
        faq_jsonld = json.loads(faq_match.group(1))
    except json.JSONDecodeError:
        add("structured_visible_match", "Article/FAQ JSON-LD 不是有效 JSON")
        return findings
    if article_jsonld.get("url") != article["canonical"] or article_jsonld.get("mainEntityOfPage") != article["canonical"]:
        add("canonical_jsonld_consistency", "Article JSON-LD URL 與 canonical 不一致")
    expected_author = pipeline.load_article_publication_policy()["identity"]
    author = article_jsonld.get("author") or {}
    if (
        author.get("name") != expected_author["author_name"]
        or author.get("url") != expected_author["author_url"]
        or author.get("@id") != expected_author["author_id"]
        or expected_author["author_name"] not in markup
    ):
        add("author_visible_jsonld_match", "可見署名與 Article JSON-LD author identity 不一致")
    actual_faq = [
        {
            "question": item.get("name"),
            "answer": (item.get("acceptedAnswer") or {}).get("text"),
        }
        for item in faq_jsonld.get("mainEntity") or []
    ]
    expected_faq = [
        {"question": item["question"], "answer": item["answer"]}
        for item in article["faq"]
    ]
    if actual_faq != expected_faq:
        add("faq_visible_jsonld_match", "FAQ JSON-LD 數量或內容與文章 FAQ 不一致")
    for item in expected_faq:
        if (
            html.escape(str(item["question"]), quote=False) not in markup
            or html.escape(str(item["answer"]), quote=False) not in markup
        ):
            add("faq_visible_jsonld_match", "FAQ JSON-LD 內容未全部顯示於 initial HTML")
            break
    if not article.get("published") and "datePublished" in article_jsonld:
        add("truthful_dates", "缺 published 資料時不得輸出 fallback datePublished")
    if not article.get("updated") and "dateModified" in article_jsonld:
        add("truthful_dates", "缺 updated 資料時不得輸出 fallback dateModified")
    return findings


def build_policy_v2_audit(articles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    inventory = PRERENDER_ARTICLES if articles is None else articles
    ids = [str(article["id"]) for article in inventory]
    routes = [str(article["route"]) for article in inventory]
    id_counts = Counter(ids)
    route_counts = Counter(routes)
    sitemap_text = SITEMAP_PATH.read_text(encoding="utf-8") if SITEMAP_PATH.is_file() else ""
    migration: list[dict[str, Any]] = []
    failure_counts: dict[str, int] = {}
    artifact_hashes: list[str | None] = []
    compliant = 0
    canonical_routes = set(routes)
    for inventory_index, article in enumerate(inventory):
        article_id = str(article["id"])
        artifact_path = WEB_DIR / str(article["target"])
        artifact_exists = artifact_path.is_file()
        markup = artifact_path.read_text(encoding="utf-8") if artifact_exists else ""
        artifact_hashes.append(
            hashlib.sha256(markup.encode("utf-8")).hexdigest()
            if artifact_exists
            else None
        )
        findings = pipeline.required_policy_findings(
            prerender_artifact_findings(
                article,
                markup,
                reference_articles=inventory,
            )
        )
        if not artifact_exists:
            findings.append(
                pipeline._policy_finding(
                    article_id,
                    "initial_html_artifact_missing",
                    f"initial HTML artifact 缺檔：{article['target']}",
                )
            )
        if id_counts[article_id] > 1:
            findings.append(
                pipeline._policy_finding(
                    article_id,
                    "unique_identity",
                    f"article id 在 inventory 重複 {id_counts[article_id]} 次",
                )
            )
        route = str(article["route"])
        if route_counts[route] > 1:
            findings.append(
                pipeline._policy_finding(
                    article_id,
                    "canonical_consistency",
                    f"article route 在 inventory 重複 {route_counts[route]} 次",
                )
            )
        if f"<loc>{article['canonical']}</loc>" not in sitemap_text:
            findings.append(
                pipeline._policy_finding(
                    str(article["id"]),
                    "canonical_sitemap_consistency",
                    "canonical 未出現在 sitemap",
                )
            )
        sitemap_entry = re.search(
            rf"<url>\s*<loc>{re.escape(str(article['canonical']))}</loc>(.*?)</url>",
            sitemap_text,
            flags=re.S,
        )
        sitemap_lastmod = (
            re.search(r"<lastmod>([^<]+)</lastmod>", sitemap_entry.group(1))
            if sitemap_entry
            else None
        )
        if not article.get("updated") and sitemap_lastmod:
            findings.append(
                pipeline._policy_finding(
                    str(article["id"]),
                    "truthful_dates",
                    "缺真實 updated 的舊文 sitemap 不得保留 fallback lastmod",
                )
            )
        if (
            article.get("updated")
            and sitemap_lastmod
            and sitemap_lastmod.group(1) != str(article["updated"])
        ):
            findings.append(
                pipeline._policy_finding(
                    str(article["id"]),
                    "canonical_sitemap_consistency",
                    "sitemap lastmod 與文章 updated 不一致",
                )
            )
        for link in article.get("internal_links") or []:
            href = str(link.get("href") or "")
            if href.startswith("/articles/") and href.count("/") >= 3 and href not in canonical_routes:
                findings.append(
                    pipeline._policy_finding(
                        str(article["id"]),
                        "canonical_internal_link_consistency",
                        f"站內連結不是已知 canonical route：{href}",
                    )
                )
                break
        if findings:
            codes = sorted({str(finding["code"]) for finding in findings})
            migration.append(
                {
                    "inventory_index": inventory_index,
                    "article_id": article["id"],
                    "route": article["route"],
                    "failure_codes": codes,
                }
            )
            for code in codes:
                failure_counts[code] = failure_counts.get(code, 0) + 1
        else:
            compliant += 1
    input_hash = hashlib.sha256(
        pipeline.compact_json_bytes(
            {
                "policy": pipeline.load_article_publication_policy(),
                "sitemap_sha256": hashlib.sha256(
                    sitemap_text.encode("utf-8")
                ).hexdigest(),
                "inventory": [
                    {
                        "inventory_index": index,
                        "id": article["id"],
                        "route": article["route"],
                        "published": article["published"],
                        "updated": article["updated"],
                        "publicationPolicy": article["publicationPolicy"],
                        "bodySections": article["bodySections"],
                        "artifact_sha256": artifact_hashes[index],
                    }
                    for index, article in enumerate(inventory)
                ],
            }
        )
    ).hexdigest()
    return {
        "policy_version": pipeline.publication_policy_version(),
        "validator_result": "PASS" if not migration else "MIGRATION_REQUIRED",
        "audit_mode": "read_only",
        "article_count": len(inventory),
        "compliant_count": compliant,
        "migration_count": len(migration),
        "failure_code_counts": dict(sorted(failure_counts.items())),
        "input_hash": input_hash,
        "migration_queue": migration,
        "measured_not_locally_proven": pipeline.load_article_publication_policy()["measured"],
    }


def prerender(
    *,
    required_article_modes: dict[str, str] | None = None,
    required_article_ids: set[str] | None = None,
) -> list[Path]:
    modes = dict(required_article_modes or {})
    for article_id in required_article_ids or set():
        modes.setdefault(article_id, "create")
    required_ids = set(modes)
    seen_required_ids: set[str] = set()
    written: list[Path] = []
    for page in PRERENDER_PAGES:
        target = page["target"]
        output_path = WEB_DIR / target
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if page["content_type"] == "Article":
            markup = render_article_specific_shell(page)
            if page["id"] in required_ids:
                seen_required_ids.add(str(page["id"]))
                findings = pipeline.required_policy_findings(
                    prerender_artifact_findings(
                        page,
                        markup,
                        mode=modes[str(page["id"])],
                    )
                )
                if findings:
                    codes = ",".join(sorted({str(finding["code"]) for finding in findings}))
                    raise ValueError(f"policy v2 prerender acceptance blocked {page['id']}: {codes}")
        else:
            markup = render_article_shell_from_meta(page).body.decode("utf-8")
        output_path.write_text(markup, encoding="utf-8")
        written.append(output_path)
    missing_ids = sorted(required_ids - seen_required_ids)
    if missing_ids:
        raise ValueError(
            "policy v2 prerender acceptance missing required article ids: "
            + ",".join(missing_ids)
        )
    update_redirects()
    update_sitemap()
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required-article-id", action="append", default=[])
    parser.add_argument("--required-article-mode", action="append", default=[])
    parser.add_argument("--policy-failure-output", type=Path)
    parser.add_argument("--audit-output", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.audit_output:
        audit = build_policy_v2_audit()
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        args.audit_output.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if args.audit_only:
            print(args.audit_output)
            return
    required_modes = {
        str(article_id): "create"
        for article_id in args.required_article_id
    }
    for value in args.required_article_mode:
        article_id, separator, mode = str(value).partition("=")
        if (
            not separator
            or not article_id
            or mode not in {"create", "rewrite_existing_body"}
        ):
            raise ValueError(
                "--required-article-mode must use "
                "ARTICLE_ID=create|rewrite_existing_body"
            )
        required_modes[article_id] = mode
    try:
        for output_path in prerender(required_article_modes=required_modes):
            print(output_path)
    except ValueError as error:
        match = re.search(
            r"policy v2 prerender acceptance blocked ([^:]+): ([a-z0-9_,]+)",
            str(error),
        )
        missing_match = re.search(
            r"policy v2 prerender acceptance missing required article ids: (.+)",
            str(error),
        )
        if args.policy_failure_output and (match or missing_match):
            article_ids = (
                [match.group(1)]
                if match
                else [
                    article_id
                    for article_id in missing_match.group(1).split(",")
                    if article_id
                ]
            )
            failure_codes = (
                sorted(set(match.group(2).split(",")))
                if match
                else ["initial_html_artifact_missing"]
            )
            pipeline.write_json(
                args.policy_failure_output,
                {
                    "policy_version": pipeline.publication_policy_version(),
                    "validator_result": "FAIL",
                    "article_ids": article_ids,
                    "failure_codes": failure_codes,
                },
            )
        raise


if __name__ == "__main__":
    main()

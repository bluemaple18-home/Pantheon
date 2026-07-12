from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from main import ARTICLE_PUBLISHED_DATE, ARTICLE_UPDATED_DATE, SITE_ORIGIN, render_article_shell_from_meta  # noqa: E402


WEB_DIR = Path("app/web")
REDIRECTS_PATH = WEB_DIR / "_redirects"
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


def registry_articles() -> list[dict[str, str]]:
    script = """
import { listArticleRecords, getArticlePath, getArticleSectionRecord } from './app/web/static/article-registry.js';
const records = listArticleRecords().map((article) => ({
  path: getArticlePath(article),
  title: article.title || '',
  description: article.description || '',
  productLabel: getArticleSectionRecord(article.section)?.label || article.articleCategory || article.product || '文章',
  productHub: getArticleSectionRecord(article.section)?.product || article.product || article.articleCategory || 'fortune',
  articleCategory: article.articleCategory || article.product || '',
  contentType: 'Article',
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


def build_prerender_articles() -> list[dict[str, str]]:
    articles = []
    for record in registry_articles():
        route = record["path"]
        description = citability_description(record["description"])
        articles.append(
            {
                "route": route,
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
            }
        )
    return topics


PRERENDER_ARTICLES = build_prerender_articles()
PRERENDER_HUBS = build_prerender_hubs(PRERENDER_ARTICLES)
PRERENDER_TOPICS = build_prerender_topics()
PRERENDER_PAGES = [*PRERENDER_HUBS, *PRERENDER_TOPICS, *PRERENDER_ARTICLES]
PRERENDER_ROUTES = {page["route"]: page["target"] for page in PRERENDER_PAGES}


def redirect_target(target: str) -> str:
    return f"{target.removesuffix('/index.html')}/"


def update_redirects() -> None:
    lines = REDIRECTS_PATH.read_text(encoding="utf-8").splitlines()
    generated = [f"{route} /{redirect_target(target)} 200" for route, target in PRERENDER_ROUTES.items()]
    filtered = [
        line
        for line in lines
        if not (
            (line.startswith("/articles/") and " /seo/articles/" in line)
            or (line.startswith("/topics/") and " /seo/topics/" in line)
        )
    ]
    insert_at = filtered.index("/articles /articles 200")
    next_lines = filtered[:insert_at] + generated + filtered[insert_at:]
    REDIRECTS_PATH.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def prerender() -> list[Path]:
    written: list[Path] = []
    for page in PRERENDER_PAGES:
        target = page["target"]
        output_path = WEB_DIR / target
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response = render_article_shell_from_meta(page)
        output_path.write_text(response.body.decode("utf-8"), encoding="utf-8")
        written.append(output_path)
    update_redirects()
    return written


def main() -> None:
    for output_path in prerender():
        print(output_path)


if __name__ == "__main__":
    main()

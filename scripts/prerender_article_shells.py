from pathlib import Path
import json
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from main import ARTICLE_PUBLISHED_DATE, ARTICLE_UPDATED_DATE, SITE_ORIGIN, render_article_shell_from_meta  # noqa: E402


WEB_DIR = Path("app/web")
REDIRECTS_PATH = WEB_DIR / "_redirects"
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


PRERENDER_ARTICLES = build_prerender_articles()
PRERENDER_ROUTES = {article["route"]: article["target"] for article in PRERENDER_ARTICLES}


def redirect_target(target: str) -> str:
    return f"{target.removesuffix('/index.html')}/"


def update_redirects() -> None:
    lines = REDIRECTS_PATH.read_text(encoding="utf-8").splitlines()
    generated = [f"{route} /{redirect_target(target)} 200" for route, target in PRERENDER_ROUTES.items()]
    filtered = [line for line in lines if not line.startswith("/articles/") or " /seo/articles/" not in line]
    insert_at = filtered.index("/articles /articles 200")
    next_lines = filtered[:insert_at] + generated + filtered[insert_at:]
    REDIRECTS_PATH.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def prerender() -> list[Path]:
    written: list[Path] = []
    for article in PRERENDER_ARTICLES:
        target = article["target"]
        output_path = WEB_DIR / target
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response = render_article_shell_from_meta(article)
        output_path.write_text(response.body.decode("utf-8"), encoding="utf-8")
        written.append(output_path)
    update_redirects()
    return written


def main() -> None:
    for output_path in prerender():
        print(output_path)


if __name__ == "__main__":
    main()

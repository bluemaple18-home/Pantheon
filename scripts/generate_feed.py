from pathlib import Path
import sys
from xml.sax.saxutils import escape


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.prerender_article_shells import PRERENDER_ARTICLES  # noqa: E402


WEB_DIR = Path("app/web")
FEED_PATH = WEB_DIR / "feed.xml"
SITE_ORIGIN = "https://mysticpantheon.com"
FEED_PUB_DATE = "Fri, 10 Jul 2026 00:00:00 +0800"
FEED_BUILD_DATE = "Sun, 12 Jul 2026 00:00:00 +0800"


def xml_text(value: str) -> str:
    return escape(str(value or ""), {'"': "&quot;"})


def build_item(article: dict[str, str]) -> str:
    link = f"{SITE_ORIGIN}{article['route']}"
    return "\n".join(
        [
            "    <item>",
            f"      <title>{xml_text(article['title'])}</title>",
            f"      <link>{xml_text(link)}</link>",
            f"      <guid isPermaLink=\"true\">{xml_text(link)}</guid>",
            f"      <pubDate>{FEED_PUB_DATE}</pubDate>",
            f"      <category>{xml_text(article['product_label'])}</category>",
            f"      <description>{xml_text(article['description'])}</description>",
            "    </item>",
        ]
    )


def build_feed() -> str:
    items = "\n".join(build_item(article) for article in PRERENDER_ARTICLES)
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
            "  <channel>",
            "    <title>Pantheon 最新文章</title>",
            f"    <link>{SITE_ORIGIN}/articles</link>",
            "    <description>Pantheon 以繁體中文整理塔羅、人格、命盤、星座與人生方向文章。</description>",
            "    <language>zh-TW</language>",
            f"    <lastBuildDate>{FEED_BUILD_DATE}</lastBuildDate>",
            f"    <atom:link href=\"{SITE_ORIGIN}/feed/\" rel=\"self\" type=\"application/rss+xml\" />",
            items,
            "  </channel>",
            "</rss>",
            "",
        ]
    )


def main() -> None:
    FEED_PATH.write_text(build_feed(), encoding="utf-8")
    print(FEED_PATH)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from main import ARTICLE_PUBLISHED_DATE, ARTICLES_HUB_UPDATED_DATE, WEB_DIR  # noqa: E402


ARTICLES_HTML = WEB_DIR / "articles.html"


def render_articles_hub_dates(markup: str) -> str:
    replacements = (
        (
            r'(<meta property="article:published_time" content=")[^"]+(" />)',
            rf"\g<1>{ARTICLE_PUBLISHED_DATE}\g<2>",
        ),
        (
            r'(<meta property="article:modified_time" content=")[^"]+(" />)',
            rf"\g<1>{ARTICLES_HUB_UPDATED_DATE}\g<2>",
        ),
        (
            r'("datePublished": ")[^"]+(")',
            rf"\g<1>{ARTICLE_PUBLISHED_DATE}\g<2>",
        ),
        (
            r'("dateModified": ")[^"]+(")',
            rf"\g<1>{ARTICLES_HUB_UPDATED_DATE}\g<2>",
        ),
        (
            r'(<time datetime=")[^"]+(" data-articles-published>)[^<]+(</time>)',
            rf"\g<1>{ARTICLE_PUBLISHED_DATE}\g<2>{ARTICLE_PUBLISHED_DATE}\g<3>",
        ),
        (
            r'(<time datetime=")[^"]+(" data-articles-updated>)[^<]+(</time>)',
            rf"\g<1>{ARTICLES_HUB_UPDATED_DATE}\g<2>{ARTICLES_HUB_UPDATED_DATE}\g<3>",
        ),
    )
    for pattern, replacement in replacements:
        markup, count = re.subn(pattern, replacement, markup, count=1)
        if count != 1:
            raise RuntimeError(f"找不到唯一日期欄位：{pattern}")
    return markup


def main() -> int:
    parser = argparse.ArgumentParser(description="同步最新文章頁的發布與更新日期。")
    parser.add_argument("--check", action="store_true", help="只檢查靜態頁是否與日期參數同步。")
    args = parser.parse_args()

    current = ARTICLES_HTML.read_text(encoding="utf-8")
    rendered = render_articles_hub_dates(current)
    if args.check:
        return 0 if rendered == current else 1
    ARTICLES_HTML.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

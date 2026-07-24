from __future__ import annotations

import html
import json
import re
import time
import http.client
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable

BASE = "https://news.click108.com.tw"
OUT_DIR = Path("output/click108_research")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CUTOFF_DATE = datetime(2024, 7, 10, tzinfo=timezone.utc)


@dataclass
class FeedItem:
    title: str
    link: str
    pub_date: str
    categories: list[str]
    description: str
    content_text: str
    headings: list[str]
    paragraph_count: int
    char_count: int
    promo_link_count: int


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Connection": "close",
        },
    )
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=12) as res:
                charset = res.headers.get_content_charset() or "utf-8"
                return res.read().decode(charset, errors="replace")
        except (urllib.error.URLError, http.client.RemoteDisconnected) as exc:
            last_error = exc
            time.sleep(0.4 * (attempt + 1))
    raise urllib.error.URLError(last_error)


def strip_tags(value: str) -> str:
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", value)
    value = re.sub(r"(?is)<br\s*/?>", "\n", value)
    value = re.sub(r"(?is)</p>|</h[1-6]>", "\n", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s+", "\n", value)
    return value.strip()


def text_between(tag: str, markup: str) -> list[str]:
    pat = rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>"
    return [strip_tags(m) for m in re.findall(pat, markup) if strip_tags(m)]


def parse_feed_page(page: int) -> list[FeedItem]:
    url = f"{BASE}/feed/" if page == 1 else f"{BASE}/feed/?paged={page}"
    xml_text = fetch(url)
    root = ET.fromstring(xml_text.encode("utf-8"))
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items: list[FeedItem] = []
    for node in root.findall("./channel/item"):
        title = node.findtext("title") or ""
        link = node.findtext("link") or ""
        pub_date = node.findtext("pubDate") or ""
        categories = [c.text or "" for c in node.findall("category")]
        description = strip_tags(node.findtext("description") or "")
        content_html = node.findtext("content:encoded", default="", namespaces=ns) or ""
        content_text = strip_tags(content_html)
        headings = []
        for level in range(1, 5):
            headings.extend(text_between(f"h{level}", content_html))
        items.append(
            FeedItem(
                title=title,
                link=link,
                pub_date=pub_date,
                categories=categories,
                description=description,
                content_text=content_text[:6000],
                headings=headings[:80],
                paragraph_count=len(text_between("p", content_html)),
                char_count=len(content_text),
                promo_link_count=len(re.findall(r"Vender=NEWS_promote|appdownload|click108\.com\.tw/unit", content_html)),
            )
        )
    return items


def extract_article_links(markup: str) -> list[str]:
    links = re.findall(r'https://news\.click108\.com\.tw/\d{4}/\d{2}/[a-z0-9_-]+/\d+/?', markup)
    return sorted(set(links))


def extract_category_links(markup: str) -> list[str]:
    links = re.findall(r'https://news\.click108\.com\.tw/category/[a-z0-9_-]+/?', markup)
    return sorted(set(links))


def summarize_article_page(url: str) -> dict:
    markup = fetch(url)
    title = strip_tags(re.search(r"(?is)<h1[^>]*class=\"[^\"]*entry-title[^\"]*\"[^>]*>(.*?)</h1>", markup).group(1)) if re.search(r"(?is)<h1[^>]*class=\"[^\"]*entry-title[^\"]*\"[^>]*>(.*?)</h1>", markup) else ""
    body_match = re.search(r"(?is)<div[^>]+class=\"[^\"]*td-post-content[^\"]*\"[^>]*>(.*?)</div>\s*</div>", markup)
    body_html = body_match.group(1) if body_match else markup
    headings = []
    for level in range(1, 5):
        headings.extend(text_between(f"h{level}", body_html))
    paragraphs = text_between("p", body_html)
    classes = sorted(set(re.findall(r'class="([^"]*(?:td-post-template|td-main-content|td-sidebar|td-post-content|td-ss-main)[^"]*)"', markup)))[:40]
    return {
        "url": url,
        "title": title,
        "canonical": (re.search(r'rel="canonical" href="([^"]+)"', markup) or ["", ""])[1],
        "headings": headings[:80],
        "paragraphs_sample": paragraphs[:12],
        "paragraph_count": len(paragraphs),
        "body_char_count": len(strip_tags(body_html)),
        "image_count": len(re.findall(r"<img\b", body_html)),
        "promo_link_count": len(re.findall(r"Vender=NEWS_promote|appdownload|click108\.com\.tw/unit", body_html)),
        "layout_classes": classes,
    }


def pick_samples(items: Iterable[FeedItem], links: Iterable[str]) -> list[str]:
    selected: list[str] = []
    wanted = ["zodiac", "ziwei", "astro", "tarot", "quiz", "folkcustom", "other"]
    for slug in wanted:
        for item in items:
            if f"/{slug}/" in item.link and item.link not in selected:
                selected.append(item.link)
                break
        for link in links:
            if f"/{slug}/" in link and link not in selected:
                selected.append(link)
                break
    for item in items:
        if len(selected) >= 12:
            break
        if item.link not in selected:
            selected.append(item.link)
    return selected[:12]


def item_date(item: FeedItem) -> datetime | None:
    try:
        return parsedate_to_datetime(item.pub_date).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def link_in_window(url: str) -> bool:
    match = re.search(r"/(\d{4})/(\d{2})/", url)
    if not match:
        return False
    year, month = int(match.group(1)), int(match.group(2))
    # URL 只有年月，先用該月最後一天的寬鬆判斷，避免 2024/07 窗口內文章被排除。
    if year > CUTOFF_DATE.year:
        return True
    if year < CUTOFF_DATE.year:
        return False
    return month >= CUTOFF_DATE.month


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_with_playwright(urls: list[str]) -> list[dict]:
    from scripts.browser_runtime_check import configure_playwright_browsers_path

    configure_playwright_browsers_path()
    from playwright.sync_api import sync_playwright

    captures: list[dict] = []
    viewports = {
        "desktop": {"width": 1366, "height": 900},
        "mobile": {"width": 390, "height": 844, "is_mobile": True},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in urls:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", urllib.parse.urlparse(url).path.strip("/"))[:80] or "home"
            for name, cfg in viewports.items():
                page = browser.new_page(viewport={"width": cfg["width"], "height": cfg["height"]}, is_mobile=cfg.get("is_mobile", False))
                screenshot = OUT_DIR / f"{slug}-{name}.png"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1800)
                    page.screenshot(path=str(screenshot), full_page=False)
                    metrics = page.evaluate(
                        """() => ({
                      title: document.title,
                      width: window.innerWidth,
                      height: window.innerHeight,
                      bodyWidth: document.body.scrollWidth,
                      bodyHeight: document.body.scrollHeight,
                      desktopHeaderVisible: !!document.querySelector('.td-header-desktop-wrap') && getComputedStyle(document.querySelector('.td-header-desktop-wrap')).display !== 'none',
                      mobileHeaderVisible: !!document.querySelector('.td-header-mobile-wrap') && getComputedStyle(document.querySelector('.td-header-mobile-wrap')).display !== 'none',
                      articleTitle: document.querySelector('h1.entry-title')?.innerText || document.querySelector('.entry-title')?.innerText || '',
                      contentWidth: document.querySelector('.td-post-content')?.getBoundingClientRect().width || null,
                      sidebarVisible: !!document.querySelector('.td-sidebar') && getComputedStyle(document.querySelector('.td-sidebar')).display !== 'none',
                      navText: Array.from(document.querySelectorAll('.sf-menu a, .td-mobile-main-menu a')).slice(0, 16).map(a => a.innerText.trim()).filter(Boolean)
                    })"""
                    )
                    captures.append({"url": url, "viewport": name, "screenshot": str(screenshot), "metrics": metrics})
                except Exception as exc:
                    captures.append({"url": url, "viewport": name, "error": str(exc)})
                page.close()
        browser.close()
    return captures


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        robots = fetch(f"{BASE}/robots.txt")
    except urllib.error.URLError as exc:
        robots = f"robots fetch failed: {exc}"
    home = fetch(BASE + "/")
    feed_items: list[FeedItem] = []
    seen_feed: set[str] = set()
    max_feed_pages = 80
    empty_pages = 0
    for page in range(1, max_feed_pages + 1):
        try:
            page_items = parse_feed_page(page)
        except (urllib.error.URLError, ET.ParseError) as exc:
            print(f"skip feed page {page}: {exc}")
            empty_pages += 1
            if empty_pages >= 3:
                break
            continue
        in_window = [item for item in page_items if (item_date(item) is None or item_date(item) >= CUTOFF_DATE)]
        if page_items and not in_window:
            print(f"stop feed page {page}: all items older than {CUTOFF_DATE.date()}", flush=True)
            break
        fresh = [item for item in in_window if item.link not in seen_feed]
        if not fresh:
            empty_pages += 1
            if empty_pages >= 3:
                break
            continue
        empty_pages = 0
        feed_items.extend(fresh)
        seen_feed.update(item.link for item in fresh)
        print(f"feed page {page}: +{len(fresh)} items", flush=True)
        time.sleep(0.08)

    category_links = extract_category_links(home)
    category_article_links: set[str] = set()
    for cat in category_links[:10]:
        for page in range(1, 2):
            url = cat if page == 1 else urllib.parse.urljoin(cat, f"page/{page}/")
            try:
                category_article_links.update(link for link in extract_article_links(fetch(url)) if link_in_window(link))
                print(f"category {url}: total links {len(category_article_links)}", flush=True)
            except urllib.error.URLError as exc:
                print(f"skip category {url}: {exc}", flush=True)
                continue
            time.sleep(0.25)

    samples = pick_samples(feed_items, sorted(category_article_links))
    article_summaries = []
    for url in samples:
        try:
            article_summaries.append(summarize_article_page(url))
        except urllib.error.URLError as exc:
            article_summaries.append({"url": url, "error": str(exc)})
        time.sleep(0.25)

    capture_urls = [BASE + "/"]
    capture_urls.extend(item.link for item in feed_items[:2])
    captures = capture_with_playwright(capture_urls)

    result = {
        "base": BASE,
        "robots": robots,
        "cutoff_date_utc": CUTOFF_DATE.date().isoformat(),
        "feed_pages_requested": max_feed_pages,
        "feed_items_count": len(feed_items),
        "category_count": len(category_links),
        "category_article_link_count": len(category_article_links),
        "category_links": category_links,
        "feed_items": [asdict(item) for item in feed_items],
        "article_samples": article_summaries,
        "captures": captures,
    }
    write_json(OUT_DIR / "crawl_result.json", result)

    summary = {
        "feed_items_count": len(feed_items),
        "category_count": len(category_links),
        "category_article_link_count": len(category_article_links),
        "sample_urls": samples,
        "screenshot_files": [c["screenshot"] for c in captures if "screenshot" in c],
        "screenshot_errors": [c for c in captures if "error" in c],
    }
    write_json(OUT_DIR / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

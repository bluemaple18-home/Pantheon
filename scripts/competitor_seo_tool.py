from __future__ import annotations

import argparse
import csv
import html
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
DEFAULT_KEYWORD_MATRIX = Path("artifacts/fortune_council/content_seo_matrix/keyword_seed_matrix.md")
DEFAULT_SOURCE_INTAKE = Path("artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md")
KEYWORD_STOPWORDS = {"文章", "分支文章", "主型", "牌組", "內容線", "文章型態", "標題", "內部連結", "上下篇", "跨線連結"}


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


@dataclass
class PageAudit:
    url: str
    status: int | None
    error: str
    title: str
    title_len: int
    description: str
    description_len: int
    canonical: str
    viewport: str
    meta_robots: str
    og_title: str
    og_description: str
    og_image: str
    twitter_card: str
    h1: list[str]
    h2: list[str]
    jsonld_types: list[str]
    internal_link_count: int
    unique_article_links: int
    unique_category_links: int
    asset_counts: dict[str, int]


def fetch(url: str, timeout: int = 18, retries: int = 2) -> tuple[int, dict[str, str], str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Connection": "close",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset, errors="replace")
                return response.status, dict(response.headers), text
        except (urllib.error.URLError, http.client.RemoteDisconnected) as exc:
            last_error = exc
            time.sleep(0.35 * (attempt + 1))
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


def attr(markup: str, pattern: str) -> str:
    match = re.search(pattern, markup, re.I | re.S)
    return html.unescape(match.group(1).strip()) if match else ""


def text_between(tag: str, markup: str) -> list[str]:
    return [strip_tags(match) for match in re.findall(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", markup) if strip_tags(match)]


def normalize_base(url: str) -> str:
    parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def host_pattern(base_url: str) -> str:
    host = re.escape(urllib.parse.urlparse(base_url).netloc)
    return rf"https?://{host}"


def extract_internal_links(markup: str, base_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(base_url)
    links = []
    for raw in re.findall(r"(?is)<a\b[^>]+href=[\"']([^\"']+)[\"']", markup):
        url = urllib.parse.urljoin(base_url + "/", html.unescape(raw))
        if urllib.parse.urlparse(url).netloc == parsed.netloc:
            links.append(url.split("#", 1)[0])
    return links


def extract_category_links(markup: str, base_url: str) -> list[str]:
    pattern = host_pattern(base_url)
    links = re.findall(rf"{pattern}/category/[a-z0-9_-]+/?", markup, re.I)
    return sorted(set(link.rstrip("/") + "/" for link in links))


def looks_like_article_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path
    return bool(re.search(r"/(?:20\d{2})/\d{2}/[^/]+/\d+/?$", path) or re.search(r"/articles?/[^/?#]+", path))


def extract_article_links(markup: str, base_url: str) -> list[str]:
    return sorted(set(link for link in extract_internal_links(markup, base_url) if looks_like_article_url(link)))


def parse_meta(markup: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in re.finditer(r"(?is)<meta\s+([^>]+)>", markup):
        tag = match.group(1)
        name = attr(tag, r"(?:name|property)=[\"']([^\"']+)")
        content = attr(tag, r"content=[\"']([^\"']*)")
        if name:
            values[name] = content
    return values


def parse_jsonld_types(markup: str) -> list[str]:
    types: list[str] = []
    blocks = re.findall(r"(?is)<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", markup)
    for block in blocks:
        try:
            data = json.loads(html.unescape(block.strip()))
        except json.JSONDecodeError:
            types.append("parse_error")
            continue
        nodes = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for node in nodes:
            if isinstance(node, dict) and node.get("@type"):
                value = node["@type"]
                if isinstance(value, list):
                    types.extend(str(item) for item in value)
                else:
                    types.append(str(value))
    return types


def audit_page(url: str, base_url: str) -> PageAudit:
    try:
        status, _headers, markup = fetch(url)
    except Exception as exc:
        return PageAudit(
            url=url,
            status=None,
            error=str(exc),
            title="",
            title_len=0,
            description="",
            description_len=0,
            canonical="",
            viewport="",
            meta_robots="",
            og_title="",
            og_description="",
            og_image="",
            twitter_card="",
            h1=[],
            h2=[],
            jsonld_types=[],
            internal_link_count=0,
            unique_article_links=0,
            unique_category_links=0,
            asset_counts={},
        )

    meta = parse_meta(markup)
    title = strip_tags(attr(markup, r"<title[^>]*>(.*?)</title>"))
    canonical = attr(markup, r"rel=[\"']canonical[\"']\s+href=[\"']([^\"']+)") or attr(
        markup, r"href=[\"']([^\"']+)[\"']\s+rel=[\"']canonical[\"']"
    )
    links = extract_internal_links(markup, base_url)
    return PageAudit(
        url=url,
        status=status,
        error="",
        title=title,
        title_len=len(title),
        description=meta.get("description", ""),
        description_len=len(meta.get("description", "")),
        canonical=canonical,
        viewport=meta.get("viewport", ""),
        meta_robots=meta.get("robots", ""),
        og_title=meta.get("og:title", ""),
        og_description=meta.get("og:description", ""),
        og_image=meta.get("og:image", ""),
        twitter_card=meta.get("twitter:card", ""),
        h1=text_between("h1", markup)[:8],
        h2=text_between("h2", markup)[:16],
        jsonld_types=parse_jsonld_types(markup),
        internal_link_count=len(links),
        unique_article_links=len(extract_article_links(markup, base_url)),
        unique_category_links=len(extract_category_links(markup, base_url)),
        asset_counts={
            "css": len(re.findall(r"<link[^>]+stylesheet", markup, re.I)),
            "script": len(re.findall(r"<script\b", markup, re.I)),
            "img": len(re.findall(r"<img\b", markup, re.I)),
        },
    )


def parse_feed(base_url: str, max_pages: int, since: datetime | None) -> list[FeedItem]:
    items: list[FeedItem] = []
    seen: set[str] = set()
    old_page_count = 0
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    for page in range(1, max_pages + 1):
        feed_url = f"{base_url}/feed/" if page == 1 else f"{base_url}/feed/?paged={page}"
        try:
            _status, _headers, xml_text = fetch(feed_url)
            root = ET.fromstring(xml_text.encode("utf-8"))
        except Exception:
            break
        page_items = []
        for node in root.findall("./channel/item"):
            link = node.findtext("link") or ""
            if not link or link in seen:
                continue
            content_html = node.findtext("content:encoded", default="", namespaces=ns) or ""
            title = node.findtext("title") or ""
            pub_date = node.findtext("pubDate") or ""
            dt = parse_date(pub_date)
            if since and dt and dt < since:
                continue
            headings = []
            for level in range(1, 5):
                headings.extend(text_between(f"h{level}", content_html))
            item = FeedItem(
                title=title,
                link=link,
                pub_date=pub_date,
                categories=[cat.text or "" for cat in node.findall("category")],
                description=strip_tags(node.findtext("description") or ""),
                content_text=strip_tags(content_html)[:8000],
                headings=headings[:80],
                paragraph_count=len(text_between("p", content_html)),
                char_count=len(strip_tags(content_html)),
            )
            page_items.append(item)
            seen.add(link)
        if since and not page_items:
            old_page_count += 1
            if old_page_count >= 2:
                break
        else:
            old_page_count = 0
        items.extend(page_items)
        time.sleep(0.08)
    return items


def parse_date(value: str) -> datetime | None:
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def load_seed_keywords(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    keywords: list[str] = []
    headers: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip(" `") for cell in line.strip("|").split("|")]
        if any(cell in {"主關鍵字", "核心搜尋詞"} for cell in cells):
            headers = cells
            continue
        if not headers:
            continue
        for target_header in ("主關鍵字", "核心搜尋詞"):
            if target_header not in headers:
                continue
            index = headers.index(target_header)
            if index >= len(cells):
                continue
            for keyword in re.split(r"[、,，]", cells[index]):
                keyword = keyword.strip()
                if not keyword or keyword in KEYWORD_STOPWORDS or re.search(r"^[A-Z]+-[A-Z0-9-]+$", keyword):
                    continue
                if 2 <= len(keyword) <= 24 and not re.search(r"https?://|/", keyword):
                    keywords.append(keyword)
    return sorted(set(keywords))


def load_source_intake(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    marker = "## 給競品 SEO 工具的接法"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text[:4000].strip()


def keyword_matches(keywords: Iterable[str], items: Iterable[FeedItem], audits: Iterable[PageAudit]) -> list[dict[str, object]]:
    haystacks = []
    for item in items:
        haystacks.append(("feed", item.link, " ".join([item.title, item.description, " ".join(item.categories), " ".join(item.headings)])))
    for audit in audits:
        haystacks.append(("page", audit.url, " ".join([audit.title, audit.description, audit.og_title, audit.og_description, " ".join(audit.h1), " ".join(audit.h2)])))

    rows = []
    for keyword in keywords:
        hits = []
        for source, url, text in haystacks:
            if keyword and keyword.lower() in text.lower():
                hits.append({"source": source, "url": url})
        rows.append({"keyword": keyword, "competitor_hit_count": len(hits), "sample_hits": hits[:5]})
    return rows


def title_pattern_stats(items: list[FeedItem]) -> dict[str, object]:
    titles = [item.title for item in items]
    pattern_counts = {
        "question_mark": sum("？" in title or "?" in title for title in titles),
        "exclamation": sum("！" in title or "!" in title for title in titles),
        "top": sum("TOP" in title.upper() for title in titles),
        "pipe": sum("｜" in title for title in titles),
        "colon": sum("：" in title or ":" in title for title in titles),
        "year": sum(bool(re.search(r"20\d{2}", title)) for title in titles),
        "month": sum("月" in title for title in titles),
    }
    return {
        "count": len(titles),
        "avg_title_len": round(sum(len(title) for title in titles) / len(titles), 1) if titles else 0,
        "patterns": pattern_counts,
        "common_categories": Counter(cat for item in items for cat in item.categories).most_common(30),
        "common_heading_leads": Counter(heading.split("\n", 1)[0] for item in items for heading in item.headings[:2]).most_common(20),
    }


def score_technical_gaps(audits: list[PageAudit], endpoints: dict[str, dict[str, object]]) -> list[str]:
    gaps = []
    sitemap = endpoints.get("sitemap", {})
    if sitemap.get("status") != 200:
        gaps.append("競品 sitemap 不完整或不可用；Pantheon 必須保持 sitemap 可讀並列出正式 URL。")
    if any(not audit.description for audit in audits if audit.status):
        gaps.append("競品多數頁面 meta description 為空；Pantheon 每篇都要有 70-95 字 description。")
    if any(not audit.canonical for audit in audits if audit.status):
        gaps.append("競品部分分類頁缺 canonical；Pantheon 分類頁、topic 頁、文章頁都要有 canonical。")
    if any("Article" not in audit.jsonld_types for audit in audits if looks_like_article_url(audit.url) and audit.status):
        gaps.append("競品文章頁缺 Article JSON-LD；Pantheon 文章頁固定輸出 Article + FAQPage + BreadcrumbList。")
    if any("FAQPage" not in audit.jsonld_types for audit in audits if looks_like_article_url(audit.url) and audit.status):
        gaps.append("競品文章頁缺 FAQPage；Pantheon 每篇文章保留 3-5 題 FAQ 搶 AEO/GEO 引用。")
    if any(len([h for h in audit.h1 if h]) != 1 for audit in audits if audit.status):
        gaps.append("競品 H1 有空值或多 H1 雜訊；Pantheon 每頁維持單一清楚 H1。")
    return gaps


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["keyword", "competitor_hit_count", "sample_hits"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "keyword": row["keyword"],
                    "competitor_hit_count": row["competitor_hit_count"],
                    "sample_hits": json.dumps(row["sample_hits"], ensure_ascii=False),
                }
            )


def write_reports(out_dir: Path, site_name: str, base_url: str, data: dict[str, object]) -> None:
    audits: list[PageAudit] = data["page_audits"]  # type: ignore[assignment]
    items: list[FeedItem] = data["feed_items"]  # type: ignore[assignment]
    keyword_rows: list[dict[str, object]] = data["keyword_rows"]  # type: ignore[assignment]
    stats = title_pattern_stats(items)
    endpoints: dict[str, dict[str, object]] = data["endpoints"]  # type: ignore[assignment]
    gaps = score_technical_gaps(audits, endpoints)

    raw = {
        **data,
        "page_audits": [asdict(audit) for audit in audits],
        "feed_items": [asdict(item) for item in items],
    }
    (out_dir / "competitor_audit.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(out_dir / "keyword_gap.csv", keyword_rows)

    audit_lines = [
        f"# {site_name} SEO 競品工具報告",
        "",
        f"- 網站：{base_url}",
        f"- 產出時間：{data['generated_at']}",
        f"- RSS 樣本：{len(items)} 篇",
        f"- 頁面 audit：{len(audits)} 頁",
        "",
        "## 技術 SEO 缺口",
        "",
    ]
    audit_lines.extend(f"- {gap}" for gap in gaps)
    audit_lines.extend(["", "## 端點", ""])
    for name, info in endpoints.items():
        audit_lines.append(f"- {name}: status={info.get('status', 'ERR')} bytes={info.get('bytes', 0)} {info.get('error', '')}")
    audit_lines.extend(["", "## 頁面摘要", ""])
    for audit in audits:
        audit_lines.extend(
            [
                f"### {audit.url}",
                f"- status：{audit.status or 'ERR'} {audit.error}",
                f"- title：{audit.title or '<empty>'}（{audit.title_len}）",
                f"- description：{audit.description or '<empty>'}（{audit.description_len}）",
                f"- canonical：{audit.canonical or '<missing>'}",
                f"- JSON-LD：{audit.jsonld_types or []}",
                f"- H1：{audit.h1 or []}",
                f"- 內鏈/文章/分類：{audit.internal_link_count}/{audit.unique_article_links}/{audit.unique_category_links}",
                "",
            ]
        )
    (out_dir / "seo_audit.md").write_text("\n".join(audit_lines), encoding="utf-8")

    playbook = [
        f"# {site_name} SEO 超車作戰手冊",
        "",
        "## 競品內容規律",
        "",
        f"- 文章樣本數：{stats['count']}",
        f"- 平均標題長度：{stats['avg_title_len']}",
        f"- 標題符號統計：{stats['patterns']}",
        f"- 高頻分類：{stats['common_categories'][:12]}",
        "",
        "## 我們要抄的不是文字，是結構",
        "",
        "- 用「時間/情境 + 對象 + 結果」做標題可讀性，但避免保證式承諾。",
        "- 用固定文章模板提高產量：導言、快速答案、工具分工、情境應用、限制、FAQ、CTA。",
        "- 用分類/主題內鏈做內容網，不讓文章孤立。",
        "- 每篇都補競品缺的 Article、FAQPage、Breadcrumb JSON-LD。",
        "",
    ]
    source_intake = str(data.get("source_intake") or "").strip()
    if source_intake:
        playbook.extend(
            [
                "## 已整合的 Git / 研究來源邊界",
                "",
                source_intake,
                "",
            ]
        )
    playbook.extend(
        [
        "## 30 天動作",
        "",
        "- 先補 30 篇第一批 keyword matrix 文章，每篇符合 Pantheon 公開文章展出規範。",
        "- 每篇建立 50 字 answer、70-95 字 description、3-5 題 FAQ。",
        "- sitemap 保持全量正式 URL；topic 頁與文章頁 canonical 不缺漏。",
        "- 每篇至少 5 條內鏈：產品線、五大情境、同分類 2 篇、跨分類 1 篇。",
        "",
        "## 60 天動作",
        "",
        "- 擴展塔羅 78 張牌、MBTI 16 型、紫微十二宮/十四主星。先做搜尋解釋頁，再做情境頁。",
        "- 對照 `keyword_gap.csv`：競品命中的詞，我們要有更乾淨的 answer/FAQ/schema；競品沒命中的詞，我們先卡位。",
        "",
        "## 90 天動作",
        "",
        "- 用 Search Console 驗證曝光與 CTR，重寫 title/description 低 CTR 頁。",
        "- 針對進榜頁加強內鏈和 FAQ，讓 AEO/GEO 摘要更容易被引用。",
        "",
        "## 關鍵字命中摘要",
        "",
        ]
    )
    for row in keyword_rows[:80]:
        playbook.append(f"- {row['keyword']}: competitor_hit_count={row['competitor_hit_count']}")
    (out_dir / "playbook.md").write_text("\n".join(playbook), encoding="utf-8")


def endpoint_status(url: str) -> dict[str, object]:
    try:
        status, headers, text = fetch(url)
        return {
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "bytes": len(text.encode()),
            "head": strip_tags(text[:800])[:220],
        }
    except Exception as exc:
        return {"error": str(exc)}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a competitor content site and turn findings into a Pantheon SEO playbook.",
    )
    parser.add_argument("--site-url", required=True, help="Competitor root URL, e.g. https://news.click108.com.tw")
    parser.add_argument("--name", default="", help="Human-readable competitor name. Defaults to hostname.")
    parser.add_argument("--out-dir", default="", help="Output directory. Defaults to output/competitor_seo/<hostname>.")
    parser.add_argument("--since", default="", help="Only keep RSS items after YYYY-MM-DD when feed dates are available.")
    parser.add_argument("--max-feed-pages", type=int, default=30, help="Maximum RSS pages to crawl. Default: 30.")
    parser.add_argument("--max-category-pages", type=int, default=1, help="Category pages to sample per category. Default: 1.")
    parser.add_argument("--sample-limit", type=int, default=12, help="Maximum article/category sample pages to audit. Default: 12.")
    parser.add_argument("--keyword-matrix", default=str(DEFAULT_KEYWORD_MATRIX), help="Pantheon keyword matrix markdown path.")
    parser.add_argument(
        "--source-intake",
        default=str(DEFAULT_SOURCE_INTAKE),
        help="Optional markdown source intake to include in the playbook when the file exists.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    base_url = normalize_base(args.site_url)
    hostname = urllib.parse.urlparse(base_url).netloc
    site_name = args.name or hostname
    out_dir = Path(args.out_dir) if args.out_dir else Path("output/competitor_seo") / hostname
    out_dir.mkdir(parents=True, exist_ok=True)
    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc) if args.since else None

    endpoints = {
        "robots": endpoint_status(f"{base_url}/robots.txt"),
        "sitemap": endpoint_status(f"{base_url}/sitemap.xml"),
        "feed": endpoint_status(f"{base_url}/feed/"),
    }
    _status, _headers, home_html = fetch(base_url)
    category_links = extract_category_links(home_html, base_url)
    feed_items = parse_feed(base_url, args.max_feed_pages, since)

    sample_urls = [base_url]
    for category_url in category_links[: min(4, len(category_links))]:
        sample_urls.append(category_url)
        for page in range(2, max(2, args.max_category_pages + 1)):
            sample_urls.append(urllib.parse.urljoin(category_url, f"page/{page}/"))
    for item in feed_items:
        if len(sample_urls) >= args.sample_limit:
            break
        if item.link not in sample_urls:
            sample_urls.append(item.link)
    sample_urls = list(dict.fromkeys(sample_urls))[: args.sample_limit]
    page_audits = [audit_page(url, base_url) for url in sample_urls]

    keywords = load_seed_keywords(Path(args.keyword_matrix))
    source_intake = load_source_intake(Path(args.source_intake))
    keyword_rows = keyword_matches(keywords, feed_items, page_audits)
    keyword_rows.sort(key=lambda row: (int(row["competitor_hit_count"]) == 0, -int(row["competitor_hit_count"]), str(row["keyword"])))

    data: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": base_url,
        "site_name": site_name,
        "endpoints": endpoints,
        "category_links": category_links,
        "feed_items": feed_items,
        "page_audits": page_audits,
        "keyword_rows": keyword_rows,
        "settings": {
            "since": args.since,
            "max_feed_pages": args.max_feed_pages,
            "max_category_pages": args.max_category_pages,
            "sample_limit": args.sample_limit,
            "keyword_matrix": args.keyword_matrix,
            "source_intake": args.source_intake,
        },
        "source_intake": source_intake,
    }
    write_reports(out_dir, site_name, base_url, data)
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "feed_items": len(feed_items),
                "page_audits": len(page_audits),
                "keyword_rows": len(keyword_rows),
                "reports": ["competitor_audit.json", "keyword_gap.csv", "seo_audit.md", "playbook.md"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

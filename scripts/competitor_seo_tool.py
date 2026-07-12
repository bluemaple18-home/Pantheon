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
from dataclasses import asdict, dataclass, replace
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
AI_CRAWLER_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"]
CORE_SCHEMA_TYPES = ["Article", "FAQPage", "BreadcrumbList", "Organization", "WebSite"]
TEXT_ENDPOINT_TYPES = {"text/plain", "text/markdown", "text/x-markdown", "application/markdown"}


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
    visible_text: str
    h1: list[str]
    h2: list[str]
    jsonld_types: list[str]
    internal_link_count: int
    external_link_count: int
    unique_article_links: int
    unique_category_links: int
    has_author: bool
    has_published_time: bool
    has_modified_time: bool
    has_about_or_contact_link: bool
    citability_markers: list[str]
    asset_counts: dict[str, int]


@dataclass
class GeoSignals:
    llms_txt_status: str
    ai_txt_status: str
    ai_bot_policy: dict[str, str]
    schema_depth_score: int
    eeat_score: int
    citability_score: int
    entity_score: int
    findings: list[str]


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
        except urllib.error.HTTPError as exc:
            charset = exc.headers.get_content_charset() or "utf-8"
            text = exc.read().decode(charset, errors="replace")
            return exc.code, dict(exc.headers), text
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


def is_local_netloc(netloc: str) -> bool:
    host = netloc.split(":", 1)[0].lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def remap_feed_item_links_for_audit(base_url: str, items: list[FeedItem]) -> list[FeedItem]:
    parsed_base = urllib.parse.urlparse(base_url)
    if not is_local_netloc(parsed_base.netloc):
        return items
    remapped: list[FeedItem] = []
    for item in items:
        parsed_link = urllib.parse.urlparse(item.link)
        if parsed_link.scheme in {"http", "https"} and parsed_link.netloc and not is_local_netloc(parsed_link.netloc):
            local_link = urllib.parse.urlunparse(
                (parsed_base.scheme, parsed_base.netloc, parsed_link.path, "", parsed_link.query, parsed_link.fragment)
            )
            remapped.append(replace(item, link=local_link))
        else:
            remapped.append(item)
    return remapped


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


def extract_external_links(markup: str, base_url: str) -> list[str]:
    parsed = urllib.parse.urlparse(base_url)
    links = []
    for raw in re.findall(r"(?is)<a\b[^>]+href=[\"']([^\"']+)[\"']", markup):
        url = urllib.parse.urljoin(base_url + "/", html.unescape(raw))
        target = urllib.parse.urlparse(url)
        if target.scheme in {"http", "https"} and target.netloc and target.netloc != parsed.netloc:
            links.append(url.split("#", 1)[0])
    return links


def has_about_or_contact_link(markup: str, base_url: str) -> bool:
    patterns = ("about", "contact", "privacy", "editorial", "關於", "聯絡", "隱私", "作者", "編輯")
    for raw in re.findall(r"(?is)<a\b[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", markup):
        href = urllib.parse.urljoin(base_url + "/", html.unescape(raw[0])).lower()
        label = strip_tags(raw[1]).lower()
        if any(pattern in href or pattern in label for pattern in patterns):
            return True
    return False


def extract_citability_markers(markup: str) -> list[str]:
    markers = []
    text = strip_tags(markup)
    headings = " ".join(text_between("h2", markup) + text_between("h3", markup))
    if re.search(r"是什麼|如何|怎麼|為什麼|重點|結論|總結|常見問題|FAQ", headings, re.I):
        markers.append("answer_headings")
    if re.search(r"(?is)<(ul|ol|table)\b", markup):
        markers.append("structured_blocks")
    if re.search(r"(?is)<blockquote\b|來源|參考|資料來源|研究|統計", markup):
        markers.append("source_or_evidence_language")
    if 600 <= len(text) <= 8000:
        markers.append("scannable_length")
    return markers


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
            visible_text="",
            h1=[],
            h2=[],
            jsonld_types=[],
            internal_link_count=0,
            external_link_count=0,
            unique_article_links=0,
            unique_category_links=0,
            has_author=False,
            has_published_time=False,
            has_modified_time=False,
            has_about_or_contact_link=False,
            citability_markers=[],
            asset_counts={},
        )

    meta = parse_meta(markup)
    visible_markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    visible_text = strip_tags(visible_markup)[:12000]
    title = strip_tags(attr(markup, r"<title[^>]*>(.*?)</title>"))
    canonical = attr(markup, r"rel=[\"']canonical[\"']\s+href=[\"']([^\"']+)") or attr(
        markup, r"href=[\"']([^\"']+)[\"']\s+rel=[\"']canonical[\"']"
    )
    links = extract_internal_links(markup, base_url)
    external_links = extract_external_links(markup, base_url)
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
        visible_text=visible_text,
        h1=text_between("h1", markup)[:8],
        h2=text_between("h2", markup)[:16],
        jsonld_types=parse_jsonld_types(markup),
        internal_link_count=len(links),
        external_link_count=len(external_links),
        unique_article_links=len(extract_article_links(markup, base_url)),
        unique_category_links=len(extract_category_links(markup, base_url)),
        has_author=bool(
            meta.get("author")
            or re.search(r"(?is)(rel=[\"']author[\"']|class=[\"'][^\"']*author|property=[\"']article:author[\"'])", markup)
        ),
        has_published_time=bool(meta.get("article:published_time") or re.search(r"(?is)<time\b|datePublished", markup)),
        has_modified_time=bool(meta.get("article:modified_time") or re.search(r"(?is)dateModified|更新日期|最後更新", markup)),
        has_about_or_contact_link=has_about_or_contact_link(markup, base_url),
        citability_markers=extract_citability_markers(markup),
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
    for marker in ("## 給 `competitor_seo_tool.py` 的接法", "## 給競品 SEO 工具的接法"):
        if marker in text:
            return text.split(marker, 1)[1].strip()
    return text[:8000].strip()


def keyword_matches(keywords: Iterable[str], items: Iterable[FeedItem], audits: Iterable[PageAudit]) -> list[dict[str, object]]:
    haystacks = []
    for item in items:
        haystacks.append(("feed", item.link, " ".join([item.title, item.description, " ".join(item.categories), " ".join(item.headings)])))
    for audit in audits:
        haystacks.append(
            (
                "page",
                audit.url,
                " ".join(
                    [
                        audit.title,
                        audit.description,
                        audit.og_title,
                        audit.og_description,
                        " ".join(audit.h1),
                        " ".join(audit.h2),
                        audit.visible_text,
                    ]
                ),
            )
        )

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


def looks_like_html_document(body: str) -> bool:
    snippet = body[:5000]
    return bool(
        re.search(
            r"(?is)^\s*<!doctype\s+html|^\s*<html\b|<head\b|<body\b|<title\b|<script\b|id=[\"']root[\"']",
            snippet,
        )
    )


def looks_like_xml_document(body: str) -> bool:
    return bool(re.search(r"(?is)^\s*<\?xml\b|<(rss|feed|urlset|sitemapindex)\b", body[:3000]))


def is_text_endpoint_type(content_type: str) -> bool:
    mime = content_type.split(";", 1)[0].strip().lower()
    return not mime or mime in TEXT_ENDPOINT_TYPES


def has_text_endpoint_structure(body: str) -> bool:
    return bool(
        re.search(r"https?://|www\.", body)
        or re.search(r"(?im)^\s{0,3}#{1,3}\s+\S|^\s*[-*]\s+\S", body)
        or re.search(r"(?im)^(site|title|summary|url|section|pages?|policy|usage|citation):\s*\S", body)
    )


def validate_llms_txt(info: dict[str, object]) -> tuple[str, str]:
    body = str(info.get("body", "")).strip()
    content_type = str(info.get("content_type", ""))
    if looks_like_xml_document(body):
        return "invalid_content", "body_looks_like_xml"
    if looks_like_html_document(body):
        return "fallback_html", "body_looks_like_html"
    if not is_text_endpoint_type(content_type):
        return "invalid_content", "non_text_content_type"
    if len(body) < 40:
        return "invalid_content", "body_too_short"
    has_site_context = bool(
        re.search(r"(?i)\b(llms?|ai|crawler|site|website|summary|about|section|url)\b", body)
        or re.search(r"網站|站點|摘要|引用|重要頁面|核心頁面|文章|爬蟲", body)
    )
    if has_site_context and has_text_endpoint_structure(body):
        return "present", "valid_llms_txt"
    return "invalid_content", "missing_llms_txt_context"


def validate_ai_txt(info: dict[str, object]) -> tuple[str, str]:
    body = str(info.get("body", "")).strip()
    content_type = str(info.get("content_type", ""))
    if looks_like_xml_document(body):
        return "invalid_content", "body_looks_like_xml"
    if looks_like_html_document(body):
        return "fallback_html", "body_looks_like_html"
    if not is_text_endpoint_type(content_type):
        return "invalid_content", "non_text_content_type"
    if len(body) < 40:
        return "invalid_content", "body_too_short"
    has_ai_policy = bool(
        re.search(
            r"(?i)\b(ai|llm|model|crawler|citation|cite|usage|policy|training|allowed|disallowed|attribution)\b",
            body,
        )
        or re.search(r"人工智慧|模型|爬蟲|引用|使用|政策|訓練|允許|禁止|授權|署名", body)
    )
    if has_ai_policy and has_text_endpoint_structure(body):
        return "present", "valid_ai_txt"
    return "invalid_content", "missing_ai_policy_context"


def endpoint_validation(info: dict[str, object], endpoint_name: str = "") -> tuple[str, str]:
    status = info.get("status")
    if status in {401, 403}:
        return "blocked", "http_blocked"
    if status == 404 or "404" in str(info.get("error", "")):
        return "missing", "http_404"
    if status != 200:
        return "blocked" if info.get("error") else "invalid_content", "http_not_200"
    if endpoint_name == "llms_txt":
        return validate_llms_txt(info)
    if endpoint_name == "ai_txt":
        return validate_ai_txt(info)
    return "present", "http_200"


def endpoint_label(info: dict[str, object], endpoint_name: str = "") -> str:
    return endpoint_validation(info, endpoint_name)[0]


def annotate_endpoint(endpoint_name: str, info: dict[str, object]) -> dict[str, object]:
    label, validation = endpoint_validation(info, endpoint_name)
    info["label"] = label
    info["validation"] = validation
    return info


def parse_ai_bot_policy(robots_text: str) -> dict[str, str]:
    if not robots_text:
        return {bot: "unknown" for bot in AI_CRAWLER_BOTS}
    groups: list[tuple[list[str], list[str]]] = []
    current_agents: list[str] = []
    current_rules: list[str] = []
    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            if current_agents and current_rules:
                groups.append((current_agents, current_rules))
                current_agents, current_rules = [], []
            current_agents.append(value.lower())
        elif key in {"allow", "disallow"} and current_agents:
            current_rules.append(f"{key}:{value}")
    if current_agents:
        groups.append((current_agents, current_rules))

    policies: dict[str, str] = {}
    for bot in AI_CRAWLER_BOTS:
        bot_key = bot.lower()
        matched_rules = [rules for agents, rules in groups if bot_key in agents]
        wildcard_rules = [rules for agents, rules in groups if "*" in agents]
        rules = matched_rules[0] if matched_rules else wildcard_rules[0] if wildcard_rules else []
        if any(rule == "disallow:/" for rule in rules):
            policies[bot] = "blocked"
        elif rules:
            policies[bot] = "allowed_or_partial"
        else:
            policies[bot] = "not_specified"
    return policies


def percent_score(points: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(max(0, min(points / total, 1)) * 100)


def assess_geo_signals(audits: list[PageAudit], endpoints: dict[str, dict[str, object]]) -> GeoSignals:
    live_audits = [audit for audit in audits if audit.status]
    all_schema_types = {schema_type for audit in live_audits for schema_type in audit.jsonld_types}
    schema_score = percent_score(len(all_schema_types.intersection(CORE_SCHEMA_TYPES)), len(CORE_SCHEMA_TYPES))

    eeat_points = 0
    for audit in live_audits:
        eeat_points += int(audit.has_author)
        eeat_points += int(audit.has_published_time)
        eeat_points += int(audit.has_modified_time)
        eeat_points += int(audit.has_about_or_contact_link)
        eeat_points += int(audit.external_link_count > 0)
    eeat_score = percent_score(eeat_points, max(len(live_audits) * 5, 1))

    citability_points = 0
    for audit in live_audits:
        citability_points += int(50 <= audit.description_len <= 160)
        citability_points += int(len(audit.h2) >= 2)
        citability_points += int("FAQPage" in audit.jsonld_types)
        citability_points += int(bool(audit.citability_markers))
        citability_points += int(audit.internal_link_count >= 5)
    citability_score = percent_score(citability_points, max(len(live_audits) * 5, 1))

    entity_points = 0
    for audit in live_audits:
        entity_points += int(bool(audit.og_title))
        entity_points += int(bool(audit.og_description))
        entity_points += int(bool(audit.og_image))
        entity_points += int(bool(all_schema_types.intersection({"Organization", "WebSite", "Person"})))
    entity_score = percent_score(entity_points, max(len(live_audits) * 4, 1))

    ai_policy = parse_ai_bot_policy(str(endpoints.get("robots", {}).get("body", "")))
    llms_status = endpoint_label(endpoints.get("llms_txt", {}), "llms_txt")
    ai_txt_status = endpoint_label(endpoints.get("ai_txt", {}), "ai_txt")

    findings = []
    if llms_status != "present":
        findings.append("缺 `llms.txt`；可新增 AI crawler 友善的網站摘要、重要頁面與引用規則。")
    if ai_txt_status != "present":
        findings.append("缺 `ai.txt`；可新增 AI 使用政策、品牌描述與允許引用邊界。")
    blocked_bots = [bot for bot, policy in ai_policy.items() if policy == "blocked"]
    if blocked_bots:
        findings.append(f"robots.txt 封鎖 AI crawler：{', '.join(blocked_bots)}；若目標是 GEO 曝光，需重新評估。")
    if schema_score < 70:
        findings.append("Schema depth 偏低；應補 Article、FAQPage、BreadcrumbList、Organization、WebSite 等結構化資料。")
    if eeat_score < 60:
        findings.append("E-E-A-T 訊號偏弱；應補作者、更新日期、來源引用、about/contact/editorial policy。")
    if citability_score < 60:
        findings.append("Citability 偏弱；應補短答案、FAQ、清楚小標、來源/證據段落，讓 AI 更容易引用。")
    if entity_score < 60:
        findings.append("Entity 訊號偏弱；應補品牌/網站/作者 schema 與一致的 OG metadata。")

    return GeoSignals(
        llms_txt_status=llms_status,
        ai_txt_status=ai_txt_status,
        ai_bot_policy=ai_policy,
        schema_depth_score=schema_score,
        eeat_score=eeat_score,
        citability_score=citability_score,
        entity_score=entity_score,
        findings=findings,
    )


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
    geo_signals: GeoSignals = data["geo_signals"]  # type: ignore[assignment]
    gaps = score_technical_gaps(audits, endpoints)

    raw = {
        **data,
        "page_audits": [asdict(audit) for audit in audits],
        "feed_items": [asdict(item) for item in items],
        "geo_signals": asdict(geo_signals),
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
    audit_lines.extend(
        [
            "",
            "## GEO / AEO / AI Visibility 訊號",
            "",
            f"- llms.txt：{geo_signals.llms_txt_status}",
            f"- ai.txt：{geo_signals.ai_txt_status}",
            f"- Schema depth score：{geo_signals.schema_depth_score}",
            f"- E-E-A-T score：{geo_signals.eeat_score}",
            f"- Citability score：{geo_signals.citability_score}",
            f"- Entity score：{geo_signals.entity_score}",
            f"- AI bot policy：{geo_signals.ai_bot_policy}",
            "",
            "### GEO Findings",
            "",
        ]
    )
    audit_lines.extend(f"- {finding}" for finding in geo_signals.findings)
    audit_lines.extend(["", "## 端點", ""])
    for name, info in endpoints.items():
        label = info.get("label") or endpoint_label(info, name)
        validation = info.get("validation", "")
        audit_lines.append(
            f"- {name}: {label} status={info.get('status', 'ERR')} bytes={info.get('bytes', 0)} {validation} {info.get('error', '')}"
        )
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
                f"- 內鏈/外鏈/文章/分類：{audit.internal_link_count}/{audit.external_link_count}/{audit.unique_article_links}/{audit.unique_category_links}",
                f"- E-E-A-T：author={audit.has_author} published={audit.has_published_time} modified={audit.has_modified_time} about_contact={audit.has_about_or_contact_link}",
                f"- Citability markers：{audit.citability_markers or []}",
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
        "## GEO / AEO 差距",
        "",
        f"- llms.txt：{geo_signals.llms_txt_status}",
        f"- ai.txt：{geo_signals.ai_txt_status}",
        f"- Schema depth：{geo_signals.schema_depth_score}",
        f"- E-E-A-T：{geo_signals.eeat_score}",
        f"- Citability：{geo_signals.citability_score}",
        f"- Entity：{geo_signals.entity_score}",
        "",
    ]
    playbook.extend(f"- {finding}" for finding in geo_signals.findings)
    playbook.append("")
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
            "body": text[:12000],
        }
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


def crawl_site(
    base_url: str,
    site_name: str,
    since: datetime | None,
    max_feed_pages: int,
    max_category_pages: int,
    sample_limit: int,
    keyword_matrix: Path,
    source_intake_path: Path,
) -> dict[str, object]:
    endpoints = {
        "robots": endpoint_status(f"{base_url}/robots.txt"),
        "sitemap": endpoint_status(f"{base_url}/sitemap.xml"),
        "feed": endpoint_status(f"{base_url}/feed/"),
        "llms_txt": endpoint_status(f"{base_url}/llms.txt"),
        "ai_txt": endpoint_status(f"{base_url}/ai.txt"),
    }
    for endpoint_name, info in endpoints.items():
        annotate_endpoint(endpoint_name, info)
    _status, _headers, home_html = fetch(base_url)
    category_links = extract_category_links(home_html, base_url)
    feed_items = remap_feed_item_links_for_audit(base_url, parse_feed(base_url, max_feed_pages, since))

    sample_urls = [base_url]
    for category_url in category_links[: min(4, len(category_links))]:
        sample_urls.append(category_url)
        for page in range(2, max(2, max_category_pages + 1)):
            sample_urls.append(urllib.parse.urljoin(category_url, f"page/{page}/"))
    for item in feed_items:
        if len(sample_urls) >= sample_limit:
            break
        if item.link not in sample_urls:
            sample_urls.append(item.link)
    sample_urls = list(dict.fromkeys(sample_urls))[:sample_limit]
    page_audits = [audit_page(url, base_url) for url in sample_urls]

    keywords = load_seed_keywords(keyword_matrix)
    keyword_rows = keyword_matches(keywords, feed_items, page_audits)
    keyword_rows.sort(key=lambda row: (int(row["competitor_hit_count"]) == 0, -int(row["competitor_hit_count"]), str(row["keyword"])))
    geo_signals = assess_geo_signals(page_audits, endpoints)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": base_url,
        "site_name": site_name,
        "endpoints": endpoints,
        "category_links": category_links,
        "feed_items": feed_items,
        "page_audits": page_audits,
        "keyword_rows": keyword_rows,
        "geo_signals": geo_signals,
        "settings": {
            "since": since.isoformat() if since else "",
            "max_feed_pages": max_feed_pages,
            "max_category_pages": max_category_pages,
            "sample_limit": sample_limit,
            "keyword_matrix": str(keyword_matrix),
            "source_intake": str(source_intake_path),
        },
        "source_intake": load_source_intake(source_intake_path),
    }


def keyword_hit_map(data: dict[str, object]) -> dict[str, int]:
    rows: list[dict[str, object]] = data["keyword_rows"]  # type: ignore[assignment]
    return {str(row["keyword"]): int(row["competitor_hit_count"]) for row in rows}


def write_comparison(out_dir: Path, own_data: dict[str, object], competitor_data: dict[str, object]) -> None:
    own_geo: GeoSignals = own_data["geo_signals"]  # type: ignore[assignment]
    competitor_geo: GeoSignals = competitor_data["geo_signals"]  # type: ignore[assignment]
    own_hits = keyword_hit_map(own_data)
    competitor_hits = keyword_hit_map(competitor_data)
    content_gaps = [
        keyword for keyword, count in competitor_hits.items() if count > 0 and own_hits.get(keyword, 0) == 0
    ][:60]
    content_advantages = [
        keyword for keyword, count in own_hits.items() if count > 0 and competitor_hits.get(keyword, 0) == 0
    ][:40]
    score_rows = [
        ("Schema depth", own_geo.schema_depth_score, competitor_geo.schema_depth_score),
        ("E-E-A-T", own_geo.eeat_score, competitor_geo.eeat_score),
        ("Citability", own_geo.citability_score, competitor_geo.citability_score),
        ("Entity", own_geo.entity_score, competitor_geo.entity_score),
    ]

    lines = [
        "# SEO / GEO Competitive Comparison",
        "",
        f"- 自己網站：{own_data['base_url']}",
        f"- 競品網站：{competitor_data['base_url']}",
        f"- 產出時間：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Score Delta",
        "",
        "| 指標 | 自己 | 競品 | 判讀 |",
        "|---|---:|---:|---|",
    ]
    for label, own_score, competitor_score in score_rows:
        delta = own_score - competitor_score
        if delta >= 10:
            verdict = "我們領先，維持並擴大內容覆蓋。"
        elif delta <= -10:
            verdict = "我們落後，列入優先修正。"
        else:
            verdict = "接近，靠內容量與內鏈拉開。"
        lines.append(f"| {label} | {own_score} | {competitor_score} | {verdict} |")

    lines.extend(
        [
            "",
            "## Endpoint / AI Crawler",
            "",
            "| 項目 | 自己 | 競品 | 建議 |",
            "|---|---|---|---|",
            f"| llms.txt | {own_geo.llms_txt_status} | {competitor_geo.llms_txt_status} | 自己缺就先補；競品缺代表可做 GEO 超車。 |",
            f"| ai.txt | {own_geo.ai_txt_status} | {competitor_geo.ai_txt_status} | 自己缺就補 AI 使用政策與品牌引用邊界。 |",
            f"| AI bot policy | {own_geo.ai_bot_policy} | {competitor_geo.ai_bot_policy} | 不要無意間封鎖目標 AI crawler。 |",
            "",
            "## 我們的優先修正",
            "",
        ]
    )
    if own_geo.findings:
        lines.extend(f"- {finding}" for finding in own_geo.findings)
    else:
        lines.append("- P1 GEO/AEO 檢查沒有發現 blocker，下一步看內容量、內鏈與 AI visibility 實測。")

    lines.extend(["", "## 競品弱點可超車", ""])
    if competitor_geo.findings:
        lines.extend(f"- {finding}" for finding in competitor_geo.findings)
    else:
        lines.append("- 競品 P1 GEO/AEO 訊號完整；需從內容深度、topic cluster 和品牌 citation 切入。")

    lines.extend(["", "## Content Gap", ""])
    if content_gaps:
        lines.extend(f"- 競品命中、自己未命中：{keyword}" for keyword in content_gaps)
    else:
        lines.append("- 小樣本未發現競品命中但自己缺席的 keyword。")

    lines.extend(["", "## Content Advantage", ""])
    if content_advantages:
        lines.extend(f"- 自己命中、競品未命中：{keyword}" for keyword in content_advantages)
    else:
        lines.append("- 小樣本未發現自己明顯領先的 keyword。")

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 先修自己網站仍缺或無效的 endpoint、schema、citability、entity blocker；`llms.txt` / `ai.txt` 必須是真文字檔才算完成。",
            "2. 針對 Content Gap 建文章或 FAQ，不直接複製競品正文。",
            "3. 補內鏈與 topic 頁，讓每個新頁能回到產品與情境頁。",
            "4. P3 再接 ChatGPT / Gemini / Perplexity prompt monitor 做 AI visibility 實測。",
        ]
    )
    (out_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a competitor content site and turn findings into a Pantheon SEO playbook.",
    )
    parser.add_argument("--site-url", required=True, help="Competitor root URL, e.g. https://news.click108.com.tw")
    parser.add_argument("--name", default="", help="Human-readable competitor name. Defaults to hostname.")
    parser.add_argument("--own-site-url", default="", help="Optional owned site root URL for side-by-side comparison.")
    parser.add_argument("--own-name", default="", help="Human-readable owned site name. Defaults to owned hostname.")
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
    keyword_matrix = Path(args.keyword_matrix)
    source_intake_path = Path(args.source_intake)

    data = crawl_site(
        base_url=base_url,
        site_name=site_name,
        since=since,
        max_feed_pages=args.max_feed_pages,
        max_category_pages=args.max_category_pages,
        sample_limit=args.sample_limit,
        keyword_matrix=keyword_matrix,
        source_intake_path=source_intake_path,
    )
    write_reports(out_dir, site_name, base_url, data)

    own_reports: list[str] = []
    if args.own_site_url:
        own_base_url = normalize_base(args.own_site_url)
        own_hostname = urllib.parse.urlparse(own_base_url).netloc
        own_site_name = args.own_name or own_hostname
        own_data = crawl_site(
            base_url=own_base_url,
            site_name=own_site_name,
            since=since,
            max_feed_pages=args.max_feed_pages,
            max_category_pages=args.max_category_pages,
            sample_limit=args.sample_limit,
            keyword_matrix=keyword_matrix,
            source_intake_path=source_intake_path,
        )
        own_dir = out_dir / "own_site"
        own_dir.mkdir(parents=True, exist_ok=True)
        write_reports(own_dir, own_site_name, own_base_url, own_data)
        write_comparison(out_dir, own_data, data)
        own_reports = [
            "own_site/competitor_audit.json",
            "own_site/keyword_gap.csv",
            "own_site/seo_audit.md",
            "own_site/playbook.md",
            "comparison.md",
        ]

    feed_items: list[FeedItem] = data["feed_items"]  # type: ignore[assignment]
    page_audits: list[PageAudit] = data["page_audits"]  # type: ignore[assignment]
    keyword_rows: list[dict[str, object]] = data["keyword_rows"]  # type: ignore[assignment]
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "feed_items": len(feed_items),
                "page_audits": len(page_audits),
                "keyword_rows": len(keyword_rows),
                "reports": ["competitor_audit.json", "keyword_gap.csv", "seo_audit.md", "playbook.md", *own_reports],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

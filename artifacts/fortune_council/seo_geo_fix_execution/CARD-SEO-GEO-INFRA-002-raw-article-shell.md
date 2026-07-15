# CARD-SEO-GEO-INFRA-002｜文章 raw HTML SEO shell

## 任務目的

修正單篇文章 URL 在 no-JS / raw HTML audit 下只看到共用 `article.html` fallback 的問題，讓搜尋引擎與 audit 工具不用等待前端 JS，也能讀到基本 SEO 與 JSON-LD。

## 請讀

- `main.py`
- `app/web/article.html`
- `app/web/static/article-seo.js`
- `scripts/competitor_seo_tool.py`
- `tests/test_web.py`

## 任務範圍

- `/articles/{product}/{slug}` raw HTML 要有請求路徑對應的 canonical。
- 重要 feed article raw HTML 要有對應 title / description / H1。
- raw HTML 的 `article-jsonld`、`breadcrumb-jsonld`、`faq-jsonld` 不可為空 script。
- audit 不得再出現 JSON-LD `parse_error`。
- 前端 JS 仍可在瀏覽器端接管完整內容。

## 接受標準

- 本機 audit 文章頁 JSON-LD 顯示 `Article`、`BreadcrumbList`、`FAQPage`，不含 `parse_error`。
- 本機 audit 文章頁 canonical 指向正式 article URL，不再全指 `/articles`。
- Schema depth score 達 100。
- `pytest tests/test_web.py tests/test_competitor_seo_tool.py` 通過。
- `git diff --check` 通過。

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/`

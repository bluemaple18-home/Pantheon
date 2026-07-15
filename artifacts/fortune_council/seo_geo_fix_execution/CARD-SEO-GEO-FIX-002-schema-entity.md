# CARD-SEO-GEO-FIX-002｜Schema + Entity 修復

## 任務目的

提升 Pantheon 的 Schema depth 與 Entity score，讓 Google / AI crawler 更容易理解品牌、網站、文章集合與單篇文章。

## 請讀

- `app/web/static/article-seo.js`
- `app/web/static/article-registry.js`
- `app/web/static/article-meta.js`
- `app/web/articles.html`
- `docs/pantheon_article_publication_standard.md`
- `output/competitor_seo/news.click108.com.tw/comparison.md`

## 任務範圍

- 補 `Organization` schema。
- 補 `WebSite` schema。
- 補 `SearchAction` schema，若站內搜尋尚未有正式入口，先不要宣稱不可用功能。
- 文章頁固定輸出 `Article + FAQPage + BreadcrumbList`。
- 列表頁或文章集合頁保留 `CollectionPage`，但不能取代文章 schema。
- OG title / description / image 需保持品牌與主題一致。

## 接受標準

- `own_site/seo_audit.md` 的 Schema depth score 至少 70。
- Entity score 至少 70。
- 單篇文章頁 JSON-LD 至少含 `Article`、`FAQPage`、`BreadcrumbList`。
- 首頁或文章列表頁至少含 `Organization`、`WebSite`。
- 不新增假的 SearchAction endpoint。

## 驗證

```bash
.venv/bin/python scripts/competitor_seo_tool.py \
  --own-site-url https://mysticpantheon.com \
  --own-name Pantheon \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 2 \
  --max-category-pages 1 \
  --sample-limit 5
git diff --check
```

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/`

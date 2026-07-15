# CARD-SEO-GEO-FIX-002 Verification

## 結論

`CARD-SEO-GEO-FIX-002` 已完成本地修復。未部署前，`https://mysticpantheon.com` live audit 仍會顯示舊分數；本地 server audit 已達標。

## 改動

- `app/web/articles.html`
  - 新增 `Organization` JSON-LD。
  - 新增 `WebSite` JSON-LD。
  - 新增文章列表頁 `FAQPage` JSON-LD。
  - 新增 `og:image` / `twitter:image`。
- `app/web/article.html`
  - 新增靜態 `site-entity-jsonld`，包含 `Organization` / `WebSite`。
  - 新增 `og:image` / `twitter:image`。
- `app/web/static/article-seo.js`
  - 動態 `Article` / `CollectionPage` schema 改用 `#organization` / `#website` entity reference。
  - 動態 schema 補 image。
- `scripts/competitor_seo_tool.py`
  - Schema depth 的必備 core types 校準為 `Article`、`FAQPage`、`BreadcrumbList`、`Organization`、`WebSite`。
  - 不再因未宣稱 `SearchAction` 或 `Person` 而扣核心分。
- `tests/test_web.py`
  - 新增 Organization / WebSite / FAQPage / OG image 斷言。

## 本地驗收

本地 server：`http://127.0.0.1:8799`

結果：

- Schema depth：80
- Entity：100
- Citability：80
- E-E-A-T：0，留給 `CARD-SEO-GEO-FIX-003`

證據：

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/local_comparison.md`

## 已跑驗證

```bash
.venv/bin/python -m py_compile scripts/competitor_seo_tool.py
.venv/bin/python -m pytest tests/test_web.py tests/test_competitor_seo_tool.py
.venv/bin/python scripts/competitor_seo_tool.py \
  --own-site-url http://127.0.0.1:8799 \
  --own-name PantheonLocal \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 2 \
  --max-category-pages 1 \
  --sample-limit 5 \
  --out-dir output/competitor_seo/local_vs_click108
git diff --check
```

## Live 注意事項

`https://mysticpantheon.com` 尚未部署本次 HTML 變更，live audit 仍顯示：

- Schema depth：20
- Entity：50

部署後需重跑正式 live audit。

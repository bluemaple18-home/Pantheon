# CARD-SEO-GEO-FIX-003｜E-E-A-T 信任訊號修復

## 任務目的

修復 Pantheon E-E-A-T score 目前為 0 的問題，補上作者、更新日期、about/contact/editorial policy、來源引用等 AI 與搜尋引擎可讀信任訊號。

## 請讀

- `app/web/articles.html`
- `app/web/static/article-registry.js`
- `app/web/static/article-meta.js`
- `docs/pantheon_article_publication_standard.md`
- `output/competitor_seo/news.click108.com.tw/own_site/seo_audit.md`

## 任務範圍

- 每篇公開文章顯示或輸出可讀 author。
- 每篇公開文章顯示或輸出 published / updated date。
- 補 about / contact / editorial policy 入口或至少可爬連結。
- 文章 schema 中補 `author`、`datePublished`、`dateModified`。
- 文章中的來源、參考、限制與非保證式聲明需可被 audit 讀到。

## 接受標準

- `own_site/seo_audit.md` E-E-A-T score 至少 60。
- 每篇文章至少有 author + published date。
- 重要文章有 updated date。
- 前台可爬到 about/contact/editorial policy 其中至少兩類信任入口。
- 不使用假作者或假日期。

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

`artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/`

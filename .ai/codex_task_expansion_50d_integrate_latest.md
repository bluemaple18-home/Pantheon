---
card_id: CARD-EXPANSION-50D-INTEGRATE-LATEST
card_type: mainline-integration
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 整合 50 篇、修正公開最新排序、重建 SEO artifacts 並涉及發布前完整驗收，需 strict 跑道。
ownership_matrix: .ai/ownership_expansion_50d.md
evidence_path: artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/result.md
---

# Article Expansion 50D｜主線整合與最新文章修正

## 任務目的

- 收卡並整合三個候選模組，共 50 篇全新文章。
- 將公開文章總數由 229 更新為 279。
- 修正最新文章排序，使最新發布／更新且 serial 較新的文章優先，不再固定顯示 `*-0001`。
- 重建 prerender、sitemap、feed、redirects，完成測試與 browser acceptance。

## 前置 Gate

- 三張內容卡皆有 candidate commit SHA。
- 三張內容卡皆由獨立可見 review thread 回報 `GO`，且 reviewed commit 等於 candidate commit。
- 主線重算跨卡數量、唯一性、內容品質與語法通過。

## Allowlist

- 三個 50D module 與三份 evidence JSON。
- `app/web/static/article-registry.js`
- `app/web/static/article-meta.js`
- 文章列表／首頁最新排序的最小必要 JS。
- 對應 HTML cache version。
- `main.py`
- `tests/test_web.py`
- `scripts/prerender_article_shells.py` 與 `scripts/generate_feed.py` 的生成輸出；除非 generator 本身有 bug，不修改 generator 邏輯。
- `app/web/seo/**`、`app/web/sitemap.xml`、`app/web/feed.xml`、`app/web/_redirects`
- `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/**`

## 驗收

- 279 個公開 article paths，ID／serial／slug／title 唯一。
- 最新文章清單包含 50D 新文章，排序契約有自動測試。
- 三卡合併重複完整句超過三次為 0；禁詞為 0。
- 完整 pytest、JS syntax、Python compile、generator 與 `git diff --check` 通過。
- Browser acceptance 實際驗證代表性最新文章、最新文章頁、分類頁與錯誤 listeners。

## 禁止

- 不重寫已通過 review 的候選正文。
- 不 reset、checkout 或清除既有 dirty changes。
- 未確認發布路徑前不 push／deploy。

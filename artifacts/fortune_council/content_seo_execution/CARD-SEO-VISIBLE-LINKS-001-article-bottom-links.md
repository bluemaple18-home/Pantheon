# CARD-SEO-VISIBLE-LINKS-001｜文章頁底部可見延伸閱讀

## 任務目的

在文章頁底部新增可見「延伸閱讀」模組，提升真實使用者導流、同分類閱讀深度與 SEO 內鏈權重。

## 卡片類型｜派工對象

- 類型：Frontend UX + SEO internal linking
- 派工對象：前端實作對話框

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `app/web/static/article-meta.js`
- `app/web/static/article.js`
- `app/web/static/article-registry.js`
- `app/web/article.html`
- `app/web/static/styles.css`
- `tests/test_web.py`

## 背景

目前已完成 crawler 層內鏈：

- article raw prerender hidden links
- product hub raw prerender hidden links
- topic raw prerender hidden links
- sitemap / feed / llms.txt 入口覆蓋

這能讓 crawler 和 AI reader 讀到網站結構，但對真實使用者的導流與可見 SEO 權重仍不足。下一步要在文章頁底部補一個小而穩的可見延伸閱讀區。

## 不可動範圍

- 不改首頁 hero。
- 不改 `/articles` 最新文章首頁版面。
- 不改 product hub 版面。
- 不改 topic hub 版面。
- 不改文章主內容結構。
- 不新增大型行銷區塊。
- 不改既有 header / breadcrumb / footer 架構。
- 不移除既有 hidden prerender internal links。

## 允許動的範圍

- `app/web/article.html`：文章頁底部新增延伸閱讀容器。
- `app/web/static/article.js`：把既有 `relatedLinks` / `navigationLinks` / `productHref` 渲染到新容器。
- `app/web/static/article-meta.js`：必要時調整已存在的 related link 組合，不新增另一套推薦引擎。
- `app/web/static/styles.css`：只新增文章底部模組樣式，沿用現有色彩、按鈕、卡片密度與 responsive pattern。
- `tests/test_web.py`：補行為與 DOM contract 測試。

## 模組內容

文章底部新增一個可見區塊，建議標題：

```text
延伸閱讀
```

內容最多 6 條：

1. 上一篇 / 下一篇，若存在。
2. 同分類文章 2-3 條。
3. 跨分類相關文章 1-2 條。
4. 回到 product hub 1 條。

link anchor 必須是文章標題或清楚主題，不使用「點這裡」。

## 資料來源

優先重用既有資料：

- `content.navigationLinks`
- `content.relatedLinks`
- `content.productHref`
- `content.productThemeLabel`

不要新增手寫 link map。若資料不足，先回到 `article-meta.js` 補既有 content model。

## 視覺限制

- 桌機：放在文章正文後、CTA/頁尾前；不得擠壓主文寬度。
- 手機：單欄排列，不重疊、不爆寬。
- 卡片 radius 維持既有設計系統，不做大型圓角卡片。
- 不使用新的大面積漸層或裝飾背景。
- 模組文字不超出容器，長標題可換行。
- 每個 link 必須可點、可聚焦、可鍵盤導覽。

## 切片

### Slice 1｜DOM contract

目的：在文章頁加入底部延伸閱讀容器，但先不改推薦邏輯。

依賴：無。

可能檔案：

- `app/web/article.html`
- `app/web/static/article.js`
- `tests/test_web.py`

驗收：

- article HTML 有穩定 hook，例如 `data-visible-related-links`。
- JS 會在有 link 時渲染，沒 link 時不顯示空模組。
- 既有 hidden prerender links 仍存在。

驗證：

- `pytest tests/test_web.py`

### Slice 2｜可見 link 組合

目的：用既有 `navigationLinks`、`relatedLinks`、`productHref` 組成最多 6 條可見內鏈。

依賴：Slice 1。

可能檔案：

- `app/web/static/article.js`
- `app/web/static/article-meta.js`
- `tests/test_web.py`

驗收：

- 文章頁至少有 3 條可見延伸閱讀 link。
- 同一 href 不重複。
- 不含目前文章自己的 href。
- anchor 不使用「點這裡」。

驗證：

- `pytest tests/test_web.py`

### Slice 3｜Responsive style

目的：沿用既有視覺系統，讓桌機與手機都能安全顯示。

依賴：Slice 1、Slice 2。

可能檔案：

- `app/web/static/styles.css`
- `tests/test_web.py`

驗收：

- 桌機不擠壓主文。
- 手機不重疊、不爆版。
- hover / focus 狀態清楚。
- 不修改首頁、hub、topic 版面。

驗證：

- `pytest tests/test_web.py`
- Playwright 或瀏覽器截圖檢查文章頁桌機 / 手機。

### Checkpoint｜上線前驗收

完成 Slice 1-3 後必跑：

```text
<repo-root>/.venv/bin/python -m pytest
<repo-root>/.venv/bin/python -m py_compile main.py scripts/prerender_article_shells.py scripts/generate_feed.py scripts/competitor_seo_tool.py
git diff --check
```

若有本機 browser 驗收能力，補：

```text
文章頁桌機截圖
文章頁手機截圖
```

## 驗收條件

- 文章頁底部有可見延伸閱讀模組。
- 手機與桌機都不重疊、不爆版。
- 每篇文章可見內鏈數穩定，最多 6 條。
- crawler raw hidden links 保留。
- `pytest` 通過。
- `git diff --check` 通過。
- live audit 不倒退：Schema / E-E-A-T / Citability / Entity 保持 100。

## 風險與邊界

- 這張卡會動文章頁底部畫面；實作前若要改標題、位置或視覺密度，需先確認。
- 不在本卡處理 hub / topic 可見列表。
- 不在本卡處理內文中段情境跳轉。
- 不在本卡新增內容策略或新文章。

## 證據路徑

- `artifacts/fortune_council/content_seo_execution/evidence/visible_links_001/`

## 5 行派工卡

```text
任務ID：CARD-SEO-VISIBLE-LINKS-001
卡片類型｜派工對象：Frontend UX + SEO internal linking｜前端實作對話框
請讀：artifacts/fortune_council/content_seo_execution/CARD-SEO-VISIBLE-LINKS-001-article-bottom-links.md
任務目的：在文章頁底部新增可見延伸閱讀模組，不改首頁/hub/topic 版面。
證據路徑：artifacts/fortune_council/content_seo_execution/evidence/visible_links_001/
```

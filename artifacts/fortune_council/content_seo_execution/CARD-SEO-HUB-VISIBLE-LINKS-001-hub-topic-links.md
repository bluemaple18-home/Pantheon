# CARD-SEO-HUB-VISIBLE-LINKS-001｜Hub 與 Topic 可見文章導流

## 任務目的

在 product hub 與 topic hub 補上低調、可見、可點的文章導流，提升真實使用者的文章探索、分類閱讀深度與 SEO 內鏈權重。

## 卡片類型｜派工對象

- 類型：Frontend UX + SEO internal linking
- 派工對象：前端實作對話框

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `docs/pantheon_deployment_workflow.md`
- `app/web/article.html`
- `app/web/static/article.js`
- `app/web/static/article-meta.js`
- `app/web/static/article-registry.js`
- `app/web/static/styles.css`
- `scripts/prerender_article_shells.py`
- `tests/test_web.py`

## 背景

目前已完成：

- article raw prerender hidden links
- product hub raw prerender hidden links
- topic raw prerender hidden links
- article bottom visible links
- sitemap / feed / llms.txt / ai.txt

文章頁已能把讀者導到前後篇、分類 hub 與相關文章。下一步要讓 product hub 與 topic hub 自己也有更清楚的可見文章入口，避免 crawler 有內鏈、但真實讀者只看到泛用頁面。

## 不可動範圍

- 不改首頁 hero。
- 不改 `/articles` 最新文章首頁主版面。
- 不改 product hub hero。
- 不改 topic hub hero。
- 不改文章正文結構。
- 不新增大型行銷區塊。
- 不做大卡片海或裝飾性區塊。
- 不改既有 header / breadcrumb / footer 架構。
- 不移除既有 hidden prerender internal links。

## 允許動的範圍

- `app/web/static/article.js`：在 product hub / topic hub 內容模式下渲染可見文章列表。
- `app/web/static/article-meta.js`：必要時補 hub / topic 已存在 content model 的 link 資料，不新增手寫 link map。
- `app/web/static/styles.css`：新增低調列表樣式，沿用現有文章系統色彩、間距、radius 與 responsive pattern。
- `app/web/article.html`：必要時新增穩定 hook；不得改 hero 結構。
- `scripts/prerender_article_shells.py`：若 HTML hook 變更，重新 prerender。
- `tests/test_web.py`：補 DOM contract、link 數、cache query 與 prerender 測試。

## 模組內容

### Product hub

每個 `/articles/{product}` 頁面補一組可見文章導流：

- 建議標題：`分類文章`
- 最多 12 條。
- 優先同 product 最新或代表性文章。
- anchor 使用文章標題，不顯示流水號。
- 不包含目前 hub 自己。

### Topic hub

每個 `/topics/{topic}` 頁面補一組可見文章導流：

- 建議標題：`相關文章`
- 最多 12 條。
- 優先該 topic 對應文章。
- anchor 使用文章標題，不顯示流水號。
- 不包含目前 topic 自己。

## 視覺限制

- 桌機：放在主內容區後段，不擠壓 hero 與主文欄寬。
- 手機：單欄排列，不重疊、不爆寬。
- 使用純文字或輕量列表，不做大型卡片。
- 卡片 radius 不超過既有 8px 系統。
- 不使用新的大面積漸層、裝飾背景或大圖。
- 長標題必須可換行，不可水平 overflow。
- 每個 link 必須可點、可聚焦、可鍵盤導覽。

## 切片

### Slice 1｜DOM contract

目的：建立 product hub / topic hub 可見導流容器與穩定 hook。

可能檔案：

- `app/web/article.html`
- `app/web/static/article.js`
- `tests/test_web.py`

驗收：

- product hub 有穩定 hook，例如 `data-hub-visible-links`。
- topic hub 有穩定 hook，例如 `data-topic-visible-links`。
- 沒有 link 時不顯示空模組。
- 既有 hidden prerender links 仍存在。

驗證：

```text
<repo-root>/.venv/bin/python -m pytest tests/test_web.py
```

### Slice 2｜Link 組合

目的：用既有 content model 產生最多 12 條 hub/topic 可見文章 link。

可能檔案：

- `app/web/static/article.js`
- `app/web/static/article-meta.js`
- `tests/test_web.py`

驗收：

- product hub 至少有 6 條可見文章 link。
- topic hub 至少有 6 條可見文章 link，若 topic 本身文章不足則以現有數量為準。
- 同一 href 不重複。
- anchor 不使用「點這裡」。
- 不顯示流水號。

驗證：

```text
<repo-root>/.venv/bin/python -m pytest tests/test_web.py
```

### Slice 3｜Responsive style

目的：沿用既有視覺系統，讓桌機與手機安全顯示。

可能檔案：

- `app/web/static/styles.css`
- `tests/test_web.py`

驗收：

- 桌機不擠壓 hero。
- 手機不重疊、不爆版。
- hover / focus 狀態清楚。
- 不修改首頁、文章頁正文或文章頁底部 visible links。

驗證：

```text
<repo-root>/.venv/bin/python -m pytest tests/test_web.py
```

## Checkpoint｜上線前驗收

完成 Slice 1-3 後必跑：

```text
<repo-root>/.venv/bin/python -m pytest
<repo-root>/.venv/bin/python -m py_compile main.py scripts/prerender_article_shells.py scripts/generate_feed.py scripts/competitor_seo_tool.py
git diff --check
```

若有本機 browser 驗收能力，補：

```text
product hub 桌機截圖
product hub 手機截圖
topic hub 桌機截圖
topic hub 手機截圖
```

正式站驗收：

```text
公開 product hub DOM 驗收
公開 topic hub DOM 驗收
公開頁載入新 cache query
Schema / E-E-A-T / Citability / Entity 不倒退
```

## 驗收條件

- product hub 有可見文章導流模組。
- topic hub 有可見文章導流模組。
- 手機與桌機都不重疊、不爆版。
- crawler raw hidden links 保留。
- `pytest` 通過。
- `git diff --check` 通過。
- live audit 不倒退：Schema / E-E-A-T / Citability / Entity 保持 100。

## 風險與邊界

- 這張卡會動 hub / topic 頁局部畫面；若要改 hero、主視覺、文章卡密度或大版面，要先停下來確認。
- 不在本卡處理首頁。
- 不在本卡處理文章頁底部 visible links。
- 不在本卡新增文章內容或 keyword 對標。
- 不在本卡新增新的推薦引擎。

## 證據路徑

- `artifacts/fortune_council/content_seo_execution/evidence/hub_visible_links_001/`

## 5 行派工卡

```text
任務ID：CARD-SEO-HUB-VISIBLE-LINKS-001
卡片類型｜派工對象：Frontend UX + SEO internal linking｜前端實作對話框
請讀：artifacts/fortune_council/content_seo_execution/CARD-SEO-HUB-VISIBLE-LINKS-001-hub-topic-links.md
任務目的：在 product hub / topic hub 補低調可見文章導流，不改首頁、hero 或文章正文。
證據路徑：artifacts/fortune_council/content_seo_execution/evidence/hub_visible_links_001/
```

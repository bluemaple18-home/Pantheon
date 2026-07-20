---
card_id: CARD-CONTENT-GEMINI-SCALE-PUBLISH-001
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 大量新文涉及跨批去重、內容契約、Gemini 外部生成、共享整合與上線回退成本，需 strict 跑道控管 invariant 與 release wave
ownership: 既有內容矩陣的現況去重、第一波新文候選產製與可上線證據
allowlist:
  - artifacts/fortune_council/content_seo_execution/evidence/gemini_scale_publish_001/**
  - app/web/static/article-expansion-scale-001.js
forbidden_scope:
  - 既有文章正文與 metadata
  - shared registry、article-meta、prerender、sitemap、feed、redirects
  - deploy、push、production 與遠端控制面
  - Gemini／Google 憑證、token、CLI 設定與全域 dotdir
verification:
  - cluster 與 runtime registry 語意去重
  - Gemini Writer／Reviewer SHA receipts
  - schema、內容品質、uniqueness、文章 identity 與 allowlist
  - 受影響 pytest、生成器 dry-run、git diff --check、候選頁瀏覽器驗收
evidence_path: artifacts/fortune_council/content_seo_execution/evidence/gemini_scale_publish_001/
worktree_path: pending_platform_provisioning
cwd: pending_platform_provisioning
main_cwd: <repo-root>
worktree_exists: false
source_branch: main
source_sha: ddcb4efb7da1f91714bbbdfa0875672af37b209e
source_clean: true
index_lock: absent
thread_id: pending
thread_status: CARD_DRAFTED
---

# CARD-CONTENT-GEMINI-SCALE-PUBLISH-001｜既有內容矩陣大量產文

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-SCALE-PUBLISH-001`，把既有 cluster 規劃轉成第一波可整合的新文章候選。
派工對象｜`gpt-5.6-sol`、`high`；Gemini CLI Writer／Reviewer 負責產文與獨立審稿，主線負責共享檔整合、部署與 live acceptance。
任務目的｜將既有 125 篇規劃與現行 runtime registry 語意去重，鎖定去重後最高優先的最多 30 篇，以每批 5 篇快速產出可驗收候選。
可改範圍｜只可新增本卡 evidence 與唯一專屬模組 `app/web/static/article-expansion-scale-001.js`；不得修改任何既有文章或共享整合檔。
驗收證據｜唯一 backlog、逐篇使用者情境 brief、Gemini receipts、候選 SHA、Reviewer verdict、內容與重複度 gate、測試、生成器 dry-run 與候選頁瀏覽器證據。

## 已知基線

- `CARD-SEO-WRITE-002` 已規劃 125 篇 cluster，但該清單只代表規劃，不代表仍缺文。
- 現行 runtime registry 已累積後續擴張文章；本卡必須重新做 exact 與 semantic dedupe，不得照舊清單盲寫。
- 既有 Gemini 文章 pipeline 每個模型 run 最多 5 篇，Writer 使用 Flash Low、Reviewer 使用 Pro Low。
- 必讀：
  - `docs/pantheon_article_publication_standard.md`
  - `docs/pantheon_gemini_outbox_runner.md`
  - `artifacts/fortune_council/content_seo_execution/evidence/scale_clusters/cluster_plan.md`
  - `artifacts/fortune_council/content_seo_execution/CARD-AGY-ARTICLE-PIPELINE-V1.md`
  - `artifacts/fortune_council/content_seo_execution/evidence/agy_article_pipeline_v1/acceptance.md`

## 執行契約

1. 解析既有 125 篇 cluster 規劃，與現行 runtime registry 的 id、slug、title、主題、搜尋意圖及正文語意去重。
2. 排除已上線、近義重複、只有關鍵字變體但答案相同、缺乏清楚使用者情境或會稀釋既有 canonical intent 的題目。
3. 建立唯一 backlog，排序依據為使用者需求清晰度、既有內容缺口、cluster 連結價值、風險與可驗收性；第一 wave 最多 30 篇，不足 30 篇不得硬補。
4. 每篇產文前必須建立公開 brief：使用者角色、搜尋當下情境、真正問題、期望答案、可採取下一步、差異化、不可承諾內容與可用內鏈。
5. Gemini CLI Writer 使用 Flash Low，獨立 Reviewer 使用 Pro Low；每批最多 5 篇、最多兩輪 repair／re-review。Reviewer 必須審完整文章，不可只看摘要。
6. Gemini 必須走既有 sanitized outbox runner；request／response 綁定 SHA，不傳本機絕對路徑、私密資料、token、`.work/` 狀態或未公開 metadata。
7. 每篇候選需具備 publication standard 要求的 title、description、answer、正文、FAQ、tags 與內鏈意圖；內鏈只能指向現行真實頁面，不得虛構 URL。
8. 候選只寫入 `app/web/static/article-expansion-scale-001.js`，使用唯一 ID／slug；不得修改 shared registry、article-meta、prerender、sitemap、feed 或 redirects。
9. 本卡的「可上線」只代表 `DELIVERED_CANDIDATE / READY_FOR_MAINLINE_REVIEW`。主線驗收後才可整合共享檔、執行部署與 live URL 驗收。

## 必交付

- `dedupe-inventory.csv`：125 篇規劃逐篇對照現況與 `EXCLUDE / CANDIDATE / BLOCKED` 理由。
- `backlog.md`：去重後唯一 backlog、排序依據、第一 wave 與每批邊界。
- `briefs/`：逐篇公開使用者情境與內容 brief。
- `receipts/`：Gemini Writer／Reviewer request SHA、response SHA、角色、model、status 與 schema 結果。
- `candidate-manifest.json`：候選 identity、來源 brief SHA、文章 SHA、Reviewer verdict 與 batch。
- `verification.txt`：schema、內容 gate、禁詞、字數、段落、內鏈、跨文 uniqueness、allowlist、pytest、生成器 dry-run 與 `git diff --check`。
- `browser/`：至少每個產品 cluster 一篇、總計至少 5 篇候選頁的桌面與行動版驗收摘要。
- `handoff.md`：主線整合所需 registry records、共享生成步驟、回退方式與禁止直接部署聲明。

## 禁止範圍

- 不修改既有文章正文、metadata、日期、FAQ 或 tags。
- 不修改 shared registry、article-meta、prerender、sitemap、feed、redirects、部署設定或正式環境。
- 不虛構內鏈、不保證排名、不寫保證式運勢，不提供醫療、法律或投資建議。
- 不安裝、不登入、不修改 Gemini CLI、OAuth、token store、MCP config 或全域 ai-core。
- 不 push、不 deploy、不 publish；這些外部寫入由主線另行驗收與執行。

## 驗收與交付

- 125 篇規劃必須逐篇有 dedupe verdict；`EXCLUDE + CANDIDATE + BLOCKED` 等於規劃唯一總數。
- 第一 wave 不超過 30 篇，每批不超過 5 篇；每篇均有 Writer receipt、獨立 Reviewer APPROVE 與不可變 SHA。
- schema、內容品質、禁詞、內鏈與跨文章 uniqueness findings 必須為 0；所有 ID／slug 唯一。
- 執行受影響 pytest、生成器 dry-run、`git diff --check` 與候選頁瀏覽器驗收。
- changed files 必須完全落在 allowlist；交付時建立 candidate commit 並回報完整 SHA。
- 終態只能宣稱 `DELIVERED_CANDIDATE / READY_FOR_MAINLINE_REVIEW` 或 `BLOCKED`，不得宣稱已整合、已部署或已上線。
- 同一 blocker 失敗三次立即停止，不做第四次嘗試。

## Gate 狀態

- Gate 1：實體卡已建立，等待正式 thread 與獨立 worktree receipt。
- Gate 2–5：尚未開始，禁止預填通過。

---
id: CARD-AGY-ARTICLE-PIPELINE-V1
status: awaiting_user_content_approval
type: implementation
---

# AGY 統一文章產製 Pipeline V1

## 目的

建立 Pantheon 唯一文章產製入口：既有矩陣新文走完整產文，GSC 既有頁面走 SEO copy 優化；兩者均須經獨立 Writer、Reviewer、人工核准與 deterministic gates。

## 範圍

- 新增 `scripts/gsc_opportunity_brief.py`。
- 新增 `scripts/agy_seo_copy_pipeline.py`。
- 新增 `tests/test_agy_seo_copy_pipeline.py`。
- 私密 run artifact 寫入 `.work/gsc-copy/<run-id>/`。
- 第一輪矩陣經 registry 語意去重後 backlog 為 8 篇；每個模型 run 最多 5 篇。

## 禁區

- 不接 `app/ai/agent.py` 或個人命理解讀。
- 未經使用者最終核准，不 commit、不整合 `main`、不 push、不部署。
- 不攜帶主工作區未追蹤檔。
- GSC 目前無資料；V1 只完成唯讀 client 邊界與 mock 驗證，不阻塞新文章流程。

## 核心契約

- Writer 使用 Flash Low；Reviewer 使用 Pro Low，CLI 認證可共用但每次均啟動獨立 headless process，不共用 session。
- Reviewer JSON 格式或 schema 錯誤即退件；最多 2 次 repair/re-review。
- 每篇 candidate 以原始 UTF-8 bytes 計算 SHA-256，可逐篇核准或退件。
- 人工可覆核內容 finding；schema、hash、允許欄位與測試硬閘門不可覆核。
- 新文章每篇 brief 不超過 8 KiB；GSC run brief 不超過 8 KiB、最多 5 頁。
- GSC optimize 只允許 `title`、`description`、`answer`。
- Apply 只在隔離 worktree 產生 repo diff，不 commit、不 push、不部署。

## 驗證

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py
.venv/bin/python -m pytest tests/test_web.py
git diff --check
```

## 證據

- `.work/gsc-copy/<run-id>/review.md`
- `artifacts/fortune_council/content_seo_execution/evidence/agy_article_pipeline_v1/`

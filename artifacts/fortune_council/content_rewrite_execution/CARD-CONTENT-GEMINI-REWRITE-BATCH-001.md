---
card_id: CARD-CONTENT-GEMINI-REWRITE-BATCH-001
status: REVIEW_NO_GO
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 外部 Gemini runtime、既有文章正文 schema 與 deterministic apply 邊界需同時建立，屬 strict 契約變更
source_kind: commit
source_sha: 00d13eb51c1ffbc19572f8378fac7090da93765d
source_card: CARD-CONTENT-GEMINI-REWRITE-AUDIT-001
source_thread: 019f741c-0628-7322-ae87-9c71c1ca24a7
ownership: Gemini 舊文改寫 Batch 1 的 pipeline contract、candidate 與獨立 review
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_seo_copy_pipeline.py
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_001/**
  - .work/gemini-rewrite/batch-001/**
forbidden_scope:
  - app/**
  - registry、metadata、正式正文、prerender、sitemap、feed、redirects、部署與發布狀態
evidence_path: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_001/
thread_id: 019f742c-613d-79a3-9318-c41fc59b9afd
thread_status: DELIVERED_CANDIDATE / REVIEW_NO_GO
mainline_evidence_commit: bc30655
integration_scope: pipeline_tests_and_blocked_candidate_evidence_only
---

# CARD-CONTENT-GEMINI-REWRITE-BATCH-001｜最舊流水號 Gemini 改寫候選

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REWRITE-BATCH-001`，來源固定為 audit candidate `00d13eb51c1ffbc19572f8378fac7090da93765d`。
派工對象｜`gpt-5.6-sol`、`high`；Gemini Writer 與獨立 Gemini Reviewer 透過既有 Antigravity CLI 執行。
任務目的｜為最舊流水號的 5 篇 `GEMINI_REWRITE` 建立正文改寫 schema、產出 candidate，完成 deterministic gate 與獨立 review。
可改範圍｜只可修改 pipeline、對應測試與 batch evidence/private run；本卡不得套用候選到 `app/**`。
驗收證據｜pipeline 測試、5 篇 candidate SHA、Writer/Reviewer 模型、逐篇 verdict/findings、內容品質檢查、`git diff --check` 與 candidate commit。

## Batch 1 固定文章

1. `MBTI-BASE-01`｜`personality-0001`
2. `THEME-LIFE-03`｜`life-direction-0003`
3. `THEME-INTERPERSONAL-03`｜`interpersonal-0003`
4. `THEME-LIFE-04`｜`life-direction-0004`
5. `THEME-WEALTH-04`｜`wealth-0004`

順序不得更換；不得加入 `KEEP` 或其他文章。

## Pipeline 契約

- 在 `scripts/agy_seo_copy_pipeline.py` 新增明確的 `rewrite_existing_body` mode，不得把它偽裝成現有 `optimize`。
- public brief 必須帶 article identity、current body、改寫 brief 與不可變更欄位；送模型前移除私密 path/run 資訊。
- Writer 只可輸出每篇完整 `bodySections`；不得改 id、product、slug、serial、title、description、answer、FAQ、tags、日期或 URL。
- deterministic gate 至少檢查：文章集合與順序、5 節、每節 3 段、每段 90–130 字、正文 1300–2000 字、搜尋意圖前置、兩個文章專屬場景、可觀察動詞、反例／限制、禁詞與跨篇固定句。
- Reviewer 使用獨立 Gemini Pro headless process；schema 錯誤或 deterministic finding 一律 REJECT，最多 2 次 repair/re-review。
- candidate 以逐篇 UTF-8 bytes 計算 SHA-256；candidate/review 與 attempt evidence 必須可重現。
- 本卡只產 candidate 與 review，不建立 approval.json、不執行 apply、不修改正式文章。

## 外部工具契約

- 使用 repo 既有 `GeminiClient`，transport 優先既有 Antigravity CLI；不安裝、不登入、不修改 MCP/CLI 設定。
- 不讀取、不列印、不提交 Gemini 金鑰或認證內容。
- operation level：產生外部模型候選；使用者已明確授權 Gemini 改寫這 5 篇，但正式套用仍須另行內容核准。
- 每次外部呼叫留下時間、Writer/Reviewer model、狀態與 run evidence；同一 blocker 三次即停止。

## 內容契約

- 讀者為搜尋 Pantheon 命理／人格內容的一般繁中使用者；正文白話、具體、先回答問題。
- 每篇前 80 字自然回答 primary keyword，正文 1300–2000 字。
- 至少兩個文章專屬生活場景、三個具體動詞、反例與「不能代表什麼」。
- 不把 MBTI、塔羅、命盤寫成診斷、固定人格、保證預測、投資建議或命運結論。
- 不使用批次模板小標與固定句，不得共用跨篇完整句型。

## 驗證與交付

- `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py`
- 對 candidate 跑既有與新增 deterministic quality gates。
- `git diff --check`
- changed files 必須完全落在 allowlist；交付完整 candidate commit SHA。
- 只能回報 `DELIVERED_CANDIDATE`，不得宣稱已套用、已整合、已發布或已驗收。

## Provisioning Receipt

- 正式 create receipt：thread ID `019f742c-613d-79a3-9318-c41fc59b9afd`。
- 獨立 worktree 已存在，HEAD=`00d13eb51c1ffbc19572f8378fac7090da93765d`，與主工作區不同。
- 本機進度證據：`scripts/agy_seo_copy_pipeline.py` 已出現約 312 行 diff，代表實作 turn 已產生實際檔案進度。
- Codex `list/read thread` 狀態核對連續三次逾時，依停損規則不做第四次；在正式 sidebar/list 狀態可核對前，本卡標記 `BLOCKED / THREAD_STATUS_API_TIMEOUT`，不得以本機 diff 單獨宣稱完整 `RUNNING`。
- 使用者續跑後已重新取得正式 thread read receipt：cwd 指向上述獨立 worktree、turn 為 `inProgress`、thread 狀態為 `active`；前述 API timeout blocker 已解除。
- 新增 pipeline 首輪測試：`26 passed`；Batch 1 brief 與去識別 public payload 已生成，Gemini 呼叫尚待執行線繼續。
- Candidate commit：`274cad03fb760a25f6baa10ae31f4391a073ce08`。
- Gemini 外部執行：初稿 1 次＋repair/re-review 2 次，共 6 次 Writer/Reviewer 呼叫成功；未做第 4 輪。
- 最終 deterministic findings：0；正文長度 1435–1473 字，均為 5 節 × 每節 3 段。
- Independent Gemini Pro verdict：5 篇皆 `REJECT`，finding 為跨篇句型／結構相似；未建立 approval，未 apply 正式文章。

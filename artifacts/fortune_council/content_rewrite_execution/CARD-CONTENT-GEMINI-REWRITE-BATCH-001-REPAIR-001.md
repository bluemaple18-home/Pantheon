---
card_id: CARD-CONTENT-GEMINI-REWRITE-BATCH-001-REPAIR-001
status: BLOCKED
chain_id: CONTENT-GEMINI-REWRITE-BATCH-001
repair_generation: 1
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 修復外部 Gemini 多篇生成的跨篇唯一性 finding，需維持既有 schema、candidate SHA 與獨立 review 契約
source_kind: commit
source_sha: 274cad03fb760a25f6baa10ae31f4391a073ce08
previous_card: CARD-CONTENT-GEMINI-REWRITE-BATCH-001
previous_thread: 019f742c-613d-79a3-9318-c41fc59b9afd
review_verdict: NO_GO
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_seo_copy_pipeline.py
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_001_repair_001/**
  - .work/gemini-rewrite/batch-001-repair-001/**
forbidden_scope:
  - app/**
  - 正式正文、registry、metadata、prerender、sitemap、feed、redirects、部署與發布
evidence_path: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_001_repair_001/
thread_id: 019f7458-cbdb-7ab3-a6d1-9614a982b90c
thread_status: DELIVERED_BLOCKED
mainline_evidence_commits:
  - d1c712f
  - dc9d054
integration_scope: pipeline_tests_and_blocked_repair_evidence_only
---

# CARD-CONTENT-GEMINI-REWRITE-BATCH-001-REPAIR-001｜跨篇唯一性修復

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REWRITE-BATCH-001-REPAIR-001`，只修 Batch 1 Reviewer 的跨篇句型／結構相似 finding。
來源｜固定 candidate commit `274cad03fb760a25f6baa10ae31f4391a073ce08`，不得回到 audit base 重做或換文章。
修復策略｜5 篇各自用 fresh Gemini Writer process 產生完整正文，再聚合做 deterministic uniqueness gate 與獨立 Gemini Pro 跨五篇 review。
可改範圍｜pipeline、對應測試與 repair evidence/private run；禁止修改 `app/**`、approval 或 apply。
驗收證據｜逐篇 Writer process receipt、聚合 candidate SHA、跨篇重複 n-gram／小標檢查、Reviewer verdict、測試、`git diff --check` 與 repair candidate commit。

## 固定文章與順序

1. `MBTI-BASE-01`｜`personality-0001`
2. `THEME-LIFE-03`｜`life-direction-0003`
3. `THEME-INTERPERSONAL-03`｜`interpersonal-0003`
4. `THEME-LIFE-04`｜`life-direction-0004`
5. `THEME-WEALTH-04`｜`wealth-0004`

## 唯一 Repair 範圍

- 只修 Reviewer finding：跨篇完整句、段落骨架、小標節奏或例子形狀過度相似。
- 每篇必須有不同的開場場景、H2 結構、論證順序、反例位置與結尾動作；不得只做同義詞替換。
- Writer 呼叫改為每篇一個 fresh sandboxed headless process；每次 prompt 只含單篇 public brief，不讓 Writer 看其他候選正文。
- 聚合後 deterministic gate 檢查跨篇相同完整句、共用 H2、長 n-gram 與段落開頭重複；命中即 REJECT，不交給 Reviewer 放行。
- Reviewer 使用新的獨立 Gemini Pro process，同時讀 5 篇 public candidate，專查前卡 finding 是否關閉，並維持搜尋意圖、邊界與禁詞檢查。
- 最多 1 次 repair 內部迭代；同一 blocker 三次即停。本卡是 chain 的 Repair 1，不重置 repair 額度。

## 不變契約

- identity、metadata、URL、title、FAQ、tags、日期與 current-body SHA 全部不可變。
- 每篇正文 1300–2000 字、5 節、每節 3 段、每段 90–130 字；至少兩個專屬生活場景、三個具體動詞、反例與限制。
- 不把 MBTI、塔羅、命盤寫成診斷、固定人格、保證預測、投資建議或命運結論。
- 不安裝、不登入、不改 CLI 設定、不讀取或輸出金鑰；正式文章仍不得 apply。

## 驗證

- `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py`
- repair candidate deterministic quality/uniqueness gates
- `git diff --check`
- changed files 僅 allowlist
- 建立完整 repair candidate commit SHA，只能回報 `REPAIR_READY` 或 `BLOCKED`；不得宣稱已套用、已整合或已發布。

## Provisioning Note

- 第一份 create prompt 曾使用錯誤展開的 SHA，未建立 worktree 或正式 thread；已更正為實際 commit `274cad03fb760a25f6baa10ae31f4391a073ce08`。
- 更正後 create request 仍逾時，後續唯讀 thread 查詢也逾時；本機 `git worktree list` 未出現 Repair worktree。
- 因未取得正式 thread ID、sidebar/list receipt 與獨立 worktree，本卡維持 `BLOCKED / PROVISIONING_TIMEOUT`，不得宣稱 Repair 已建立或執行中，也不得回原 implementation thread 修復。
- 使用者續跑後 provisioning 已成功：正式 thread `019f7458-cbdb-7ab3-a6d1-9614a982b90c` 可由 list 查詢，標題與 preview 含本卡 ID；cwd 為獨立 Repair worktree，thread/turn 狀態為 `active/inProgress`。前述 timeout blocker 已解除。

## Repair 1 首輪結果與續跑邊界

- Repair candidate commit：`0822be46b6e390eb1a10831aaf3ce938cc256843`。
- 跨篇 uniqueness findings 已為 0；Gemini Reviewer 為 3/5 APPROVE。
- 唯二剩餘 deterministic findings：`MBTI-BASE-01` 有一段 89 字；`THEME-LIFE-03` 命中禁詞「保證」。
- 既定 Gemini Writer internal repair 額度 1/1 已用完，不得再啟動 Writer 或重生完整正文。
- 使用者於 2026-07-18 明確要求「繼續」後，本卡只重新排隊一次 deterministic closure pass：在 repair candidate 私有 artifact 內補足該段至至少 90 字、把「保證」替換為不承諾結果的中性措辭；不得改其他段落或已通過三篇。
- closure 後必須回到同一 Reviewer 契約重跑五篇聚合審查、quality/uniqueness、pytest、allowlist 與 `git diff --check`。若仍有任一 finding，立即 `BLOCKED`，不得開第三輪或新 Repair generation。

## Deterministic Closure 結果

- closure candidate commit：`8c9dc6b97e138f278babbc3cdcc417a6d1a142ba`。
- 授權的兩處機械 finding 已關閉；其餘 73 段逐字不變，Writer process 為 0。
- deterministic quality findings：0；uniqueness findings：0；pytest：31/31；`git diff --check` 與 allowlist 通過。
- Gemini Pro 聚合重審僅 1/5 APPROVE：`THEME-LIFE-03` ↔ `THEME-LIFE-04` 命中首段抽象句型相似；`THEME-INTERPERSONAL-03` ↔ `THEME-WEALTH-04` 命中第四段抽象開場句型相似。
- 最後 closure allowance 1/1 已用完，狀態為 `BLOCKED`；未建立 approval、未 apply，正式文章未修改。

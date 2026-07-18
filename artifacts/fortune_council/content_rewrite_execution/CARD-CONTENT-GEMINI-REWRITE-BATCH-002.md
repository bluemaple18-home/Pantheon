---
card_id: CARD-CONTENT-GEMINI-REWRITE-BATCH-002
status: BLOCKED
chain_id: CONTENT-GEMINI-REWRITE-BATCH-002
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 延續外部 Gemini 多篇改寫，需隔離 Writer、聚合唯一性 gate、獨立 Reviewer 與不可套用邊界
source_kind: commit
source_sha: 8c9dc6b97e138f278babbc3cdcc417a6d1a142ba
audit_source_sha: 00d13eb51c1ffbc19572f8378fac7090da93765d
previous_card: CARD-CONTENT-GEMINI-REWRITE-BATCH-001-REPAIR-001
previous_thread: 019f7458-cbdb-7ab3-a6d1-9614a982b90c
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_seo_copy_pipeline.py
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_002/**
  - .work/gemini-rewrite/batch-002/**
forbidden_scope:
  - app/**
  - 正式正文、registry、metadata、approval、apply、prerender、sitemap、feed、redirects、部署與發布
evidence_path: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_002/
thread_id: 019f74d0-5ccd-79f0-a424-15b7eb044160
thread_status: CANDIDATE_COMMITTED_BLOCKED
worktree_path: <codex-worktree>/Pantheon
mainline_evidence_commit: a2e74da
integration_scope: pipeline_tests_and_blocked_candidate_evidence_only
---

# CARD-CONTENT-GEMINI-REWRITE-BATCH-002｜舊流水號第二批

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REWRITE-BATCH-002`，依 audit 全域順序處理下一批 5 篇 `GEMINI_REWRITE`。
來源｜固定 `8c9dc6b97e138f278babbc3cdcc417a6d1a142ba`；audit queue 固定來自 `00d13eb51c1ffbc19572f8378fac7090da93765d`。
策略｜每篇 fresh Gemini Writer、不同開場/H2/論證/反例/結尾；聚合 quality/uniqueness 後才交 fresh Gemini Pro Reviewer。
範圍｜只改 pipeline、測試、Batch 2 私有 candidate/evidence；禁止 `app/**`、approval、apply。
驗收｜5/5 Reviewer APPROVE、quality/uniqueness 0、pytest、allowlist、`git diff --check` 與完整 candidate commit。

## 固定文章與順序

1. `THEME-INTERPERSONAL-04`｜`interpersonal-0004`
2. `THEME-CAREER-05`｜`career-0005`
3. `THEME-LIFE-05`｜`life-direction-0005`
4. `THEME-WEALTH-05`｜`wealth-0005`
5. `THEME-INTERPERSONAL-05`｜`interpersonal-0005`

## 執行契約

- 逐篇 brief 必須直接取 audit evidence 的 `Batch 2 | P0-batch-02`，不得換文、跳號或混入 KEEP。
- 每篇 Writer 使用 fresh sandboxed headless process，prompt 只含該篇 public brief與專屬 variation contract；不得看到其他候選正文。
- 五篇聚合後檢查 quality、共用 H2、長 n-gram、段落開頭與抽象句型；命中即修，不得交由 Reviewer忽略。
- Reviewer 使用 fresh Gemini Pro process 同時審五篇；最多一次 internal repair，只重跑 REJECT 篇。
- 契約：1300–2000 字、5 節、每節 3 段、每段 90–130 字；前 80 字回答關鍵字，至少 2 個專屬場景、3 個具體動詞、反例與限制。
- identity、metadata、URL、title、FAQ、tags、日期、current-body SHA 不變；不得診斷、固定人格、保證預測、投資建議或命運結論。
- 不安裝、不登入、不改 CLI 設定、不讀取或輸出金鑰；正式套用未授權。

## 驗證與交付

- `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py`
- deterministic quality/uniqueness/abstract-pattern gates 全為 0
- Gemini Pro 5/5 APPROVE
- identity/current-body SHA、allowlist、`git diff --check`
- 建立 candidate commit；只能回報 `READY_FOR_REVIEW` 或 `BLOCKED`，不得宣稱已套用、整合或發布。

## Provisioning 結果

- source worktree HEAD 已確認為 `8c9dc6b97e138f278babbc3cdcc417a6d1a142ba`、working tree clean、`index.lock` 不存在。
- `codex_app` project lookup 連續 3 次逾時，未取得 project ID，因此未呼叫 create thread。
- 依停損規則不做第 4 次；目前沒有 clientThreadId、正式 thread ID 或 Batch 2 worktree，狀態固定為 `BLOCKED / PROJECT_LOOKUP_TIMEOUT`，不得宣稱已建立或執行中。
- 使用者再次要求「繼續」後，延遲建立稽核確認仍無 Batch 2 thread；project lookup 已恢復並取得 Pantheon project receipt，timeout blocker 解除，本卡回到 `QUEUED` 重新執行 provisioning gate。
- create receipt 已取得正式 thread ID `019f74d0-5ccd-79f0-a424-15b7eb044160`，且獨立 worktree 存在、HEAD 精確為來源 SHA；worktree 已出現本卡 pipeline 修改。因 read/list 詳情查詢逾時，暫標 `THREAD_CREATED_PENDING_LIST_VERIFICATION`，待正式 title/status/list receipt 可讀後才升 `RUNNING`。

## Candidate 結果

- candidate commit：`a8e7b8bb1614be7bdfa2cff28cea14e6c90d9f85`。
- Gemini：10 個 isolated Writer processes、2 個 fresh Pro Reviewer processes；internal repair 1/1 已用完。
- 最終 Reviewer：2/5 APPROVE；通過 `THEME-INTERPERSONAL-04`、`THEME-LIFE-05`。
- 剩餘 findings：`THEME-WEALTH-05` 缺少第 3 個不同具體動詞；`THEME-CAREER-05` 與 `THEME-INTERPERSONAL-05` 共用 `not_but_frame` 抽象句型。
- 主線重跑 `tests/test_agy_seo_copy_pipeline.py`：34/34 通過；`git diff --check` 與 allowlist 通過。
- 狀態為 `BLOCKED`；未建立 approval、未 apply，正式文章與共享整合檔皆未修改。

---
card_id: CARD-CONTENT-GEMINI-REWRITE-BATCH-003-010
status: CARD_DRAFTED
chain_id: CONTENT-GEMINI-REWRITE-TO-050
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 連續 8 批外部 Gemini 內容生成、逐批隔離與累計 50 篇驗收，需單一 ownership 與嚴格 evidence 契約
source_kind: commit
source_sha: 1799b2dd4edd073f581269da81b7693cb01bc15c
audit_source_commit: b71463c
ownership: Batch 3–10 pipeline、40 篇 candidate、逐批 review 與總結 evidence
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_seo_copy_pipeline.py
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_003/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_004/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_005/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_006/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_007/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_008/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_009/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_010/**
  - artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_to_050/**
  - .work/gemini-rewrite/batch-003-010/**
forbidden_scope:
  - app/**
  - 正式正文、registry、metadata、approval、apply、prerender、sitemap、feed、redirects、部署與發布
evidence_path: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_to_050/
worktree_path: pending
thread_id: pending
thread_status: CARD_DRAFTED
---

# CARD-CONTENT-GEMINI-REWRITE-BATCH-003-010｜累計改寫至 50 篇

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REWRITE-BATCH-003-010`，延續 audit 舊流水號順序產出 40 篇候選，使 Batch 1–10 累計 50 篇。
來源｜主線 commit `1799b2dd4edd073f581269da81b7693cb01bc15c`，文章 brief 只取已整合 audit queue 的 Batch 3–10。
策略｜單一 owner 依序跑 8 批；每批 5 個隔離 Writer、聚合 deterministic gates、1 個 Pro Reviewer，最多一次 repair。
範圍｜只改 pipeline、測試與 Batch 3–10 私有 evidence；禁止正式正文、approval、apply 與發布。
驗收｜40 個唯一 article ID 均有 final candidate、review、run evidence 與 SHA；累計計數為 50，測試、allowlist、`git diff --check` 通過。

## 固定批次與文章

- Batch 3：`THEME-LOVE-05/love-0005`、`ASTRO-MERCURY-01/astrology-0006`、`THEME-CAREER-06/career-0006`、`THEME-LIFE-06/life-direction-0006`、`THEME-WEALTH-06/wealth-0006`
- Batch 4：`THEME-INTERPERSONAL-06/interpersonal-0006`、`THEME-LOVE-06/love-0006`、`ASTRO-MARS-01/astrology-0007`、`THEME-CAREER-07/career-0007`、`THEME-LIFE-07/life-direction-0007`
- Batch 5：`THEME-WEALTH-07/wealth-0007`、`THEME-INTERPERSONAL-07/interpersonal-0007`、`THEME-LOVE-07/love-0007`、`ASTRO-JUPITER-01/astrology-0008`、`THEME-CAREER-08/career-0008`
- Batch 6：`THEME-LIFE-08/life-direction-0008`、`THEME-WEALTH-08/wealth-0008`、`THEME-INTERPERSONAL-08/interpersonal-0008`、`THEME-LOVE-08/love-0008`、`ASTRO-SATURN-01/astrology-0009`
- Batch 7：`THEME-CAREER-09/career-0009`、`THEME-LIFE-09/life-direction-0009`、`THEME-WEALTH-09/wealth-0009`、`THEME-INTERPERSONAL-09/interpersonal-0009`、`THEME-LOVE-09/love-0009`
- Batch 8：`ASTRO-HOUSES-01/astrology-0010`、`THEME-CAREER-10/career-0010`、`THEME-LIFE-10/life-direction-0010`、`THEME-WEALTH-10/wealth-0010`、`THEME-INTERPERSONAL-10/interpersonal-0010`
- Batch 9：`THEME-LOVE-10/love-0010`、`THEME-CAREER-11/career-0011`、`THEME-LIFE-11/life-direction-0011`、`THEME-WEALTH-11/wealth-0011`、`THEME-INTERPERSONAL-11/interpersonal-0011`
- Batch 10：`THEME-LOVE-11/love-0011`、`THEME-CAREER-12/career-0012`、`THEME-LIFE-12/life-direction-0012`、`THEME-WEALTH-12/wealth-0012`、`THEME-INTERPERSONAL-12/interpersonal-0012`

## 執行契約

- 每批 strict validate audit JSON 的 batch number、slot、ID、serial、slug、title、primaryKeyword、verdict 與 issue codes；不得換文、跳號、重複或混入 KEEP。
- 每篇使用 fresh sandboxed Gemini Writer process，prompt 只含單篇 public brief 與該篇獨特 variation contract；同批五篇開場、H2、論證順序、反例位置、結尾不得同形。
- 每篇 1300–2000 字、5 節、每節 3 段、每段 90–130 字；前 80 字回答 keyword，至少 2 個專屬場景、3 個具體動詞、反例與限制。
- 每批聚合檢查 quality、禁詞、完整句、共用 H2、24-char n-gram、段落前 10 字、抽象句型與段落骨架；再由 fresh Gemini Pro 同審五篇。
- 每批最多一次 internal repair，只重跑 REJECT 篇；額度用完後無論 `READY_FOR_REVIEW` 或 `BLOCKED`，都必須保存 final evidence，接著處理下一批，不得因單批 NO-GO 中斷 40 篇計數。
- identity、metadata、URL、title、FAQ、tags、日期與 current-body SHA 不變；不得診斷、固定人格、保證預測、投資建議或命運結論。
- 只用既有 GeminiClient/Antigravity CLI；不安裝、不登入、不改設定、不讀取或輸出金鑰；正式 apply 未授權。

## 累計與驗證

- Batch 1–2 既有 candidate article ID 必須先驗證為 10 個唯一值；Batch 3–10 再新增 40 個唯一值，不得重複，總計精確為 50。
- 每批必須有 `brief.json`、`candidate.json`、`review.json`、deterministic findings、operation receipts、`run-evidence.json` 與 `delivery-summary.md`。
- 總結 evidence 必須列 50 個 ID、每批 verdict 數、findings 數、candidate SHA、Writer/Reviewer process 數與 formal apply=false。
- 執行 `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py`、`git diff --check`、allowlist、identity/current-body SHA 與 50-ID uniqueness gate。
- 建立完整 candidate commit；只能回報 `CANDIDATES_050_READY` 或 `BLOCKED`。`CANDIDATES_050_READY` 只代表 50 篇候選/evidence 齊備，不代表內容全數 APPROVE 或已套用。

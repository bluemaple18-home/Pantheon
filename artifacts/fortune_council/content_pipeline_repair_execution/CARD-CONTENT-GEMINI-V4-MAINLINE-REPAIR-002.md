# CARD-CONTENT-GEMINI-V4-MAINLINE-REPAIR-002

## Identity

- `card_id`: `CARD-CONTENT-GEMINI-V4-MAINLINE-REPAIR-002`
- `chain_id`: `CONTENT-GEMINI-V4-MAINLINE-001`
- `repair_generation`: `2`
- `repair_limit`: `2`
- `thickness`: `strict`
- `risk`: `high`
- `model`: `gpt-5.6-sol high`
- `owner`: Gemini V4 Mainline Repair-2 owner
- `mainline_thread`: `019f8d25-e23b-7ac2-ac3f-894574bc49ec`
- `canonical_reviewer_thread`: `019f8d89-a3dd-7011-875d-22e8799cc773`

## Fixed base / review identity

- Repair-1 candidate、本輪唯一 base：
  `233ddc25032e0cac4bbc5d3144dbc383f49c0c18`
- Repair-1 candidate 唯一 parent：
  `6c4931c1da63257cd70bd0abe5776dc1758e4557`
- canonical re-review commit：
  `9279516ed98465fbec535b836e58b078c2157a0d`
- Repair-2 candidate 的唯一 parent 必須是：
  `233ddc25032e0cac4bbc5d3144dbc383f49c0c18`

## Provisioning preflight

- cwd 必須是新獨立 worktree，不得等於 main、Reviewer 或 Repair-1 cwd。
- 起始 worktree 必須 clean。
- 起始 HEAD 必須精確等於 Repair-1 candidate。
- 起始 HEAD parent 必須精確等於 Repair-1 candidate 唯一 parent。
- `index.lock` 必須不存在。
- 任一不符立即交付 `BLOCKED / PROVISIONING_PREFLIGHT`。

## 唯一 finding

`P1_TRUSTED_RESULT_SCHEMA`：Repair-1 verifier 直接信任 bundle 自帶
`result_schema`。若同步放寬 schema 並替換 execution／inbox result，verifier 會錯誤
PASS。已 resolved 的 P2 不得再處理。

## Allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-MAINLINE-REPAIR-002.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_repair_001/canary-verifier.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_repair_002/**`

## Forbidden

- `scripts/**`、`tests/**`、`docs/**`、`app/**`
- `gemini_v4_mainline_repair_001/real-canary-bundle.json`
- implementation evidence、Review evidence、文章、registry、metadata、sitemap、feed、prerender
- 任何外部 agy／Gemini 呼叫或 canary
- retry、fallback、merge、push、deploy、publish、預設 transport 切換
- recorder／broker 重寫

## RED contract

在修改 verifier 前，使用舊 verifier 保存：

1. `wrong_result_schema` 實際修改 bundle 的 `result_schema`。
2. `coherent_weakened_schema` 同步修改 `result_schema`、
   `execution.result`、`inbox.result`，現況 verifier 錯誤 PASS。
3. RED 不得修改真實 bundle。

## GREEN contract

- verifier 內建獨立、固定、closed canary schema，或驗證等價 immutable trusted
  schema digest／contract version。
- bundle `result_schema` 必須與 trusted contract 完全一致，不得自述放寬。
- execution 與 inbox result 均符合 trusted closed schema。
- canonical bytes、byte count、stdout SHA、ledger／receipt binding 維持一致。
- 新 `wrong_result_schema`、`coherent_weakened_schema` 皆 rejected。
- 原 12 controls 全部維持 rejected。
- 合法 real bundle與 synthetic bundle PASS。
- 舊 summary rejected。
- 不修改真實 bundle。

## Evidence

根目錄：
`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_repair_002/`

最低交付：

- `root-cause.md`
- `red-green.txt`
- `mutation-matrix.json`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

驗證至少包含合法 real／synthetic bundle、原 12 controls、新 wrong-schema／coherent
controls、舊 summary rejection、canonical Reviewer coherent probe、`py_compile`、privacy
scan、changed-files／allowlist、`git diff --check`。

## Delivery contract

- 交付狀態只允許 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
- 不得自稱 GO、ACCEPTED、INTEGRATED、完成、已上線或已切預設。
- 建立單一乾淨 Repair-2 candidate commit，parent 精確為 Repair-1 candidate。
- 回報完整 candidate SHA、changed files、測試／mutation數、remaining risks、
  worktree clean 與 `index.lock` absent。
- 交回同一 canonical Reviewer thread 重審；Repair owner 不得自行 re-review。
- 同一 blocker 第三次失敗後立即停止，不做第四次。

## Current state

`IN_PROGRESS / REPAIR_2`

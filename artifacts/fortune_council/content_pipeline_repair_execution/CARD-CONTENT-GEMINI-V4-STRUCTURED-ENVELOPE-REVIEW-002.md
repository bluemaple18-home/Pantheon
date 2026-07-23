# CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REVIEW-002

- card_id: `CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REVIEW-002`
- chain_id: `CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REVIEW-002`
- ownership: `independent_v4_envelope_size_review_only`
- strictness: `strict`
- risk: `high`
- status: `PENDING`
- verdict: `PENDING`

## 審查標的

- Repair-2 candidate:
  `bccd800ebf06348449d718c33036ad1c712dbef7`
- candidate parent／Repair-2 provisioning:
  `87b1cd488d12e8df2a3bb9aa4656ac22fa1d786f`
- prior Review NO_GO evidence:
  `8d0932ec37c6ca0c3a1c549f4223c23dfd21a3d5`

## 必審 Finding

先前 outbox 合法 262,144-byte task 合成 structured envelope 後超過 broker 舊
262,144-byte ceiling，造成 flag-on `ValueError` 與 ledger absent。

## 必審項目

1. Broker effective-prompt ceiling 是否精確為：
   `256 KiB task + 64 KiB schema + 64 KiB closed envelope = 384 KiB`。
2. 最大合法 task/schema 合成後是否落在 ceiling 內。
3. ceiling+1、empty prompt與 privacy pattern 是否仍在 ledger／target fork 前拒絕。
4. `384 KiB < production ARG_MAX 1 MiB` 的環境證據是否成立。
5. 是否有改動 process、ledger、anchor、replay、flag、outbox public limits 或內容
   發布邊界。
6. Structured-envelope candidate 原有 role/schema/digest/no-fallback/privacy
   contract 是否無回歸。

## Reviewer 可修改

- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_review_002/**`

## Reviewer 禁止

- 不修改 candidate code、tests、docs 或 Repair evidence。
- 不呼叫 Gemini／agy，不 retry Activation-001／002，不建立第三筆真實 payload。
- 不 merge、push、deploy、publish、default promotion 或 legacy removal。

## 驗證

- 核對 candidate SHA、parent、changed files 與 clean worktree。
- 獨立重跑最大合法 payload、ceiling+1 與 ARG_MAX probes。
- 重跑 focused structured envelope、完整 213-test affected matrix、py_compile、
  privacy scan、scope allowlist 與 `git diff --check`。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_review_002/`

至少包含：

- `review.md`
- `verification.txt`
- `decision.md`
- `changed-files.txt`

## 交付

只能：

- `DELIVERED_CANDIDATE / GO`
- `DELIVERED_CANDIDATE / NO_GO`
- `BLOCKED`

GO 不是 activation、整合、上線、預設 promotion、legacy removal 或第三次真實外呼
授權。

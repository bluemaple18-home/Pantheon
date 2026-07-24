# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REVIEW-001

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REVIEW-001`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REVIEW-001`
- ownership: `independent_review_only`
- strictness: `strict`
- risk: `high`
- status: `DELIVERED_CANDIDATE`
- verdict: `DELIVERED_CANDIDATE / NO_GO`

## 固定候選

- candidate:
  `53decc338eb750bd5556758679132c7288889778`
- source activation evidence:
  `e98d9d6f2843432fc38eb803a1ac97ac3c0f9860`
- repair card:
  `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-001`

## Review 目標

獨立確認 candidate 是否只增加安全、封閉、非內容的 V4 result diagnostics，
並維持：

- exactly-once ledger／anchor 契約
- flag-on fail-closed
- flag-on no legacy fallback
- flag-off legacy
- prompt／raw response／credential／完整環境不持久化

## 必審

1. Findings-first 審查 candidate diff 與 caller／consumer。
2. 驗 `VALID / JSON_INVALID / NOT_OBJECT / SCHEMA_MISMATCH /
   NOT_EVALUATED` 分類互斥且正確。
3. 驗 runner 只在 `V4BrokerFailure` 寫 closed `broker_diagnostic`。
4. 驗 malformed or forged diagnostic 不能造成 prompt／raw content 落盤。
5. 驗 receipt mismatch、durable/control failure 不會誤標為 schema mismatch。
6. 重跑 V4 77、legacy 57、coordinator 6、publisher 5、web 63，共 208 tests。
7. 跑 py_compile、privacy、allowlist、debug scan、`git diff --check`。

## 唯一可寫

- 本 Review 卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_review_001/**`

## 禁止

- 不 repair candidate。
- 不修改 production、tests、文章、publisher 或 automation。
- 不呼叫 Gemini／agy。
- 不 retry 前次 job、不建立第二筆真實 payload。
- 不 merge、push、deploy、publish、activation、default promotion 或 legacy removal。

## Required evidence

- `review.md`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## Verdict

只能：

- `DELIVERED_CANDIDATE / GO / READY_FOR_SECOND_ACTIVATION_PREP`
- `DELIVERED_CANDIDATE / NO_GO`
- `BLOCKED`

即使 GO，也不授權第二次真實外呼。

## Review 結果

- provisioning commit:
  `056a39afc510fc798d47f4e7565a13372e647318`
- candidate ancestry:
  `PASS`
- affected matrix:
  `208 passed`
- focused candidate diagnostics:
  `5 passed`
- focused behavioral boundaries:
  `10 passed`
- findings:
  `1 x P1 / 1 x P2`
- privacy:
  `FAIL — forged BrokerResult 可把未封閉欄位任意內容寫入 failed record`
- no-fallback:
  `PASS`
- exactly-once ledger／anchor:
  `PASS — candidate 未修改相關實作，既有 replay tests 全綠`
- decision:
  `DELIVERED_CANDIDATE / NO_GO`

本 Review 不授權 repair、第二次真實外呼、retry、activation、publish、merge、
push、deploy、default promotion 或 legacy removal。

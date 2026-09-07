# CONTENT-P0-FAST-04C — Writer Schema Failure Routing Repair

## Objective

讓 create Writer 的 `SCHEMA_INVALID_PAYLOAD` 不再用相同 prompt 消耗 transport retry，而是進入既有 bounded Writer schema-repair loop，並保留 Writer 對 title／description 的內容所有權。

## Scope

- `scripts/agy_gemini_outbox.py`
- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`

## Facts

- `OutboxGeminiClient.generate_json()` 目前將 Writer `SCHEMA_INVALID_PAYLOAD` 視為 retryable transport failure。
- `run_writer_reviewer()` 已有 `MAX_WRITER_SCHEMA_REPAIRS=2`，但接不到 `ExternalJobFailed`。
- failure receipt 已封閉驗證 `schema_diagnostics`；不需新增 registry、queue、workflow 或 schema。
- create prompt 的 title／description hard bounds 來自既有 publication policy。
- `normalize_new_output_contract()` 目前會用固定句補足過短 description；這違反 Writer 內容所有權。

## Constraints

- 不改 publication schema、四篇 identity、Writer／Reviewer ownership 或 repair budget。
- 不新增第二套 repair runtime，不做本機文字 padding。
- Reviewer 仍只接收 schema-valid candidate。
- 不碰 plist、promotion、OPEN-1、OPEN-2、production、deploy、push 或 publish。

## Minimum success condition

1. RED 能重現 Writer schema-invalid 後產生相同 prompt 的 transport retry。
2. GREEN 時下一個 Writer request 為 semantic attempt：`transport_attempt=0`、prompt 不同，並帶封閉 diagnostics 與既有 authoritative bounds。
3. description-only minLength 不得由本機固定句補足。
4. schema repair 最多兩次；有效 candidate 前 Reviewer 不得被呼叫。
5. targeted tests、相關全檔、`py_compile`、`git diff --check` 通過。

## Why not less / why not more

- why not less：只加 prompt 文案仍保留錯誤的相同-request transport retry；保留本機補字仍繞過 Writer ownership。
- why not more：既有 schema-repair loop、failure receipt 與 queue identity 已足夠，不需要新 subsystem。

## Rollback

反向套用本卡四檔 diff；不影響既有 FAST-04B candidate、runtime queue 或 production state。

## RED / GREEN evidence

- RED：`test_invalid_writer_schema_enters_semantic_repair_without_transport_retry` 失敗；舊行為仍產生相同 `request_sha256` 的 transport retry。
- GREEN：同測試通過；title／description `minLength` diagnostics 進入新 semantic prompt，`transport_attempt=0`，兩次 schema repair 後 fail closed，Reviewer 未呼叫。
- Writer ownership：production 與 broker 測試均確認 69 字 description 會 fail closed，不再由本機固定句補足。
- 相關全檔：`349 passed`。
- Coordinator failure isolation：`2 passed`。
- `py_compile`、`git diff --check`、debug marker scan：PASS。

## Scoped self-review

- Spec：沿用既有 bounded repair loop；未新增 queue、registry、workflow、schema 或模型角色。
- Correctness：只有 Writer schema-invalid 跳出 transport retry；Reviewer 與其他 transport category 行為維持原樣。
- Security：diagnostics 只來自已通過 closed failure-receipt validation 的 keyword／path。
- Residual：Reviewer schema-invalid 仍沿用既有 transport retry；本卡不建立 Reviewer repair 機制。

## Status

`LOCAL_GREEN / SELF_REVIEW_NO_P0_P1 / COMMITTED_LOCAL / PUSH_PENDING / PRODUCTION_NOT_AUTHORIZED`

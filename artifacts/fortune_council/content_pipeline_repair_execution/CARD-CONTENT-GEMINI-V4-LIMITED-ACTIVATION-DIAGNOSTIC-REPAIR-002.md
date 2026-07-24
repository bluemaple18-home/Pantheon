# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-002

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-002`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-002`
- ownership: `v4_safe_failure_diagnostics_only`
- strictness: `strict`
- risk: `high`
- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_REVIEW`

## 來源 Review

- reviewed candidate:
  `53decc338eb750bd5556758679132c7288889778`
- review evidence commit:
  `7f0a3014a2c65f155cb95510c640a80f60ae39da`
- review verdict:
  `DELIVERED_CANDIDATE / NO_GO`

## 唯一 Blockers

1. 合法 JSON `null` 被分類為 `NOT_EVALUATED`，而不是 `NOT_OBJECT`。
2. Runner 只封閉 `result_validation`；forged／malformed `BrokerResult` 可透過
   `replay_status`、`process_count`、`outcome` 把任意內容寫入 failed record。

## 目標

- 使用獨立 parse-failure 狀態，讓所有合法 JSON non-object（含 `null`）一致分類為
  `NOT_OBJECT`。
- failed record 的 `broker_diagnostic` 四個欄位全部採 closed allowlist／closed type
  sanitization。
- forged scalar、container 或不可 hash 值不得造成 exception，也不得原樣持久化。
- 維持 flag-on fail-closed／no legacy fallback、flag-off legacy 與 exactly-once
  ledger／anchor／replay 契約。

## 可修改

- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_repair_002/**`

## 禁止

- 不修改 SEO pipeline、publisher、文章、registry、metadata、sitemap、feed、
  prerender、automation、登入、憑證或全域 CLI 設定。
- 不保存或輸出 prompt、raw stdout／stderr、response body、credential 或完整環境。
- 不呼叫 Gemini／agy。
- 不 retry 前次 job、不建立第二筆真實 payload。
- 不 push、deploy、publish、activation、default promotion 或 legacy removal。
- 不重寫 broker。

## 執行

1. 先補 RED：
   - JSON `null` 必須是 `NOT_OBJECT`。
   - forged `replay_status / process_count / outcome / result_validation` 必須被封閉；
     dict／list 等不可 hash 值不得 crash。
2. 做最小 production 修正。
3. 跑 focused tests、V4、legacy、coordinator、publisher、web affected matrix、
   py_compile、privacy scan 與 `git diff --check`。
4. 建立單一 Repair-2 candidate commit，再交回原 Review thread re-review。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_repair_002/`

必須包含：

- `root-cause.md`
- `red-green.txt`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## 交付

只能：

- `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- `BLOCKED`

本卡不授權第二次真實外呼。

## 執行結果

- RED:
  `2 failed / 3 passed`
- focused GREEN:
  `8 passed`
- affected matrix:
  `211 passed`
- JSON `null`:
  `NOT_OBJECT`
- forged scalar／container diagnostics:
  closed to `INVALID / UNKNOWN / null / NOT_EVALUATED`
- prompt／raw stdout／stderr／response body retained:
  `false`
- Gemini／agy invocation during repair:
  `0`
- decision:
  `DELIVERED_CANDIDATE / READY_FOR_REVIEW`

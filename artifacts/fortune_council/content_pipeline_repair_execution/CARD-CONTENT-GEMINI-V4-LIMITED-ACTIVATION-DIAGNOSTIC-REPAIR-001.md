# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-001

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-001`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-001`
- ownership: `v4_safe_failure_diagnostics_only`
- strictness: `strict`
- risk: `high`
- status: `IN_PROGRESS`
- decision: `PENDING`

## 來源失敗

- activation evidence commit:
  `e98d9d6f2843432fc38eb803a1ac97ac3c0f9860`
- job ID:
  `1ad663e7f17477d0cee5056260427b4b360b7fab`
- durable state:
  `COMPLETE / 1 / PROCESS_TERMINAL=SUCCESS`
- caller state:
  `V4BrokerFailure`
- retry / fallback / second invocation:
  `0`

## 目標

在不保存 prompt、raw response、credential、完整環境或 CLI log 的前提下，
讓 broker／runner 的 fail-closed record 能安全區分：

- target stdout 不是 JSON object
- JSON object 不符合 strict response schema
- durable/control failure

先以 synthetic RED 測試重現目前只得到 `V4BrokerFailure`、無安全原因碼的缺口，
再做最小 production 修正。

## 可修改

- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_repair_001/**`

## 禁止

- 不修改 SEO pipeline、publisher、文章、registry、metadata、sitemap、feed、
  prerender、automation、登入、憑證或全域 CLI 設定。
- 不保存或輸出 prompt、raw stdout／stderr、response body、credential 或完整環境。
- 不呼叫 Gemini／agy。
- 不 retry 前次 job、不建立第二筆真實 payload。
- 不 push、deploy、publish、activation、default promotion 或 legacy removal。
- 不重寫 broker。

## 執行

1. 建立能重現 parse-vs-schema 診斷缺口的 focused RED tests。
2. 排序並驗證假說：
   - H1：broker 缺少安全 result-validation reason。
   - H2：runner 即使收到安全 reason，也未寫入 failed record。
   - H3：durable/control failure 必須維持獨立 reason，不能誤標成 schema failure。
3. 最小修正 broker result 與 runner failed record。
4. 驗證 invalid JSON、schema mismatch、durable failure、success 與 privacy。
5. 跑 V4 focused、legacy、coordinator、publisher、web affected gates、py_compile、
   privacy scan 與 `git diff --check`。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_diagnostic_repair_001/`

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

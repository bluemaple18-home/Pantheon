# Root Cause

## 可重現症狀

真實 limited activation 的 durable ledger 為 `COMPLETE/1`，包含恰一個
`EXEC_CONFIRMED` 與 `PROCESS_TERMINAL/SUCCESS`，但 runner 回報
`V4BrokerFailure`，且成功 inbox 不存在。

## 定位

Broker 只在 raw stdout 同時滿足下列條件時交付 result：

1. 可解析為 JSON。
2. JSON top-level 是 object。
3. object 通過 strict response schema。

任一條件失敗時，原實作都只回傳：

- `caller_contract_satisfied=false`
- `result_json=null`

沒有安全分類。Runner 隨後只把 exception class `V4BrokerFailure` 寫入 failed
record。因此 durable evidence 能證明 exactly-once process execution，卻無法區分
JSON parse failure、non-object 與 schema mismatch。

## 假說結果

- H1：broker 缺少安全 result-validation reason。`CONFIRMED`。
  三個 synthetic target 在修復前都因 `BrokerResult` 沒有分類欄位而 RED。
- H2：runner 未持久化安全 reason。`CONFIRMED`。
  修復前 failed record 沒有 `broker_diagnostic`。
- H3：durable／control failure 可能被誤標成 schema failure。`FALSIFIED /
  GUARDED`。
  nonzero、timeout 與 synthetic blocked result 維持 `NOT_EVALUATED`。

## 最小修正

Broker 新增封閉 `result_validation` 狀態：

- `VALID`
- `JSON_INVALID`
- `NOT_OBJECT`
- `SCHEMA_MISMATCH`
- `NOT_EVALUATED`

Runner 只在 `V4BrokerFailure` 時寫入四個非內容欄位：

- `replay_status`
- `process_count`
- `outcome`
- `result_validation`

沒有保存 prompt、raw stdout／stderr、response body、credential、完整環境或 CLI
log。Flag-on 仍 fail-closed，legacy fallback 契約不變。

## 尚未處理

本修正不能回溯還原前次 raw response，也不授權第二次真實外呼。下一張 Review
必須獨立確認分類正確、privacy 不回歸、exactly-once 與 no-fallback 契約不變。

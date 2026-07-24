# Limited Activation Decision

- status: `BLOCKED`
- decision: `BLOCKED`
- external invocation count: `1`

## 已通過

- final-sync candidate 已固定。
- 一筆真實、已追蹤的 daily publishing brief 已固定。
- 第一筆 writer payload 已離線建立並通過 sanitized request validation。
- job ID、request／prompt／schema digest 與 byte count 已鎖定。
- executable digest 與既有真實 V4 canary identity 相符。
- runtime 位於 repo 外，沒有 production、文章或發布檔案變更。

## 真實執行結論

使用者在看到外送目的地、主題與內容類型後明確同意。V4 runner 隨後只執行一次
`process-once`，durable ledger 證明恰一個 `EXEC_CONFIRMED` 與一個
`PROCESS_TERMINAL/SUCCESS`，replay 為 `COMPLETE/1`。

但 broker 沒有交付 caller result，runner 以 `V4BrokerFailure` fail-closed。成功
inbox 不存在，failed 與 archive record 存在。沒有 retry、fallback、第二次 process
或發布副作用。

## 唯一 blocker

Target process 成功結束，但 raw stdout 沒有成為符合 strict response schema 的 JSON
result。現有 durable ledger 只證明 process exactly-once，不保存 raw output；failed
record 也沒有保存 `JSON_PARSE_FAILED` 或 `SCHEMA_MISMATCH` 之類的安全原因碼。因此
本次結果不能安全歸因，也不能用第二次外呼試錯。

下一步必須另立 repair 卡，先以 RED 測試補上不含 prompt／raw response 的安全診斷
欄位，再做 synthetic verification 與獨立 Review。任何第二次真實外呼都需要新的
明確授權。

## 尚未授權

- Gemini／agy generation
- 第二筆 payload
- pipeline continuation
- publisher
- push
- deploy
- publish
- default promotion
- legacy removal

# Limited Activation Decision

- status: `IN_PROGRESS`
- decision: `AWAITING_EXTERNAL_CONFIRMATION`
- external invocation count: `0`

## 已通過

- final-sync candidate 已固定。
- 一筆真實、已追蹤的 daily publishing brief 已固定。
- 第一筆 writer payload 已離線建立並通過 sanitized request validation。
- job ID、request／prompt／schema digest 與 byte count 已鎖定。
- executable digest 與既有真實 V4 canary identity 相符。
- runtime 位於 repo 外，沒有 production、文章或發布檔案變更。

## 下一個動作的精確效果

若使用者確認，只執行一次 V4 runner `process-once`。它最多啟動一個 agy target，
把固定的 2555-byte sanitized writer prompt 送至 `gemini-3.5-flash`，並在 repo 外
runtime 寫 ledger、anchor 及成功或失敗結果。它不繼續文章 pipeline、不產生文章
候選、不呼叫 publisher，也不 push／deploy／publish。

成功或失敗都停止，不 retry、不 fallback、不執行第二次。

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

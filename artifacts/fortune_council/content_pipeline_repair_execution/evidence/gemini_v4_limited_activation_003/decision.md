# Gemini V4 Limited Activation-003 Decision

- status:
  `BLOCKED`
- decision:
  `BLOCKED`
- external invocation count:
  `1`

## 已通過

- Structured-envelope Repair-2 已取得獨立 Review GO。
- 全新 run identity、namespace、job ID、request digest 與 repo 外 runtime 已建立。
- 一筆 sanitized writer request 已通過 strict rebuild、digest 與 public-data
  validation。
- Effective prompt 已驗證 closed writer role、JSON-only、no-code-fence、canonical
  schema與 exact user task。
- Effective prompt 4028 bytes，低於 393216-byte ceiling。
- Executable digest 與 verified `agy 1.1.5` identity 一致。
- Runtime 尚無 ledger、anchor、inbox、archive 或 failed record。

## 真實執行結論

使用者在看到工具、模型、公開主題、effective envelope、process 上限與副作用後
明確確認。V4 runner 只執行一次，durable ledger 與 external anchor 證明：

- replay `COMPLETE / 1`
- 恰一個 `EXEC_CONFIRMED`
- 恰一個 `PROCESS_TERMINAL / SUCCESS`
- replay errors `0`

Runner 隨後以 `V4BrokerFailure` fail closed；closed diagnostic 是
`result_validation=SCHEMA_MISMATCH`。沒有 inbox，failed、archive、ledger 與
anchor 存在。沒有 retry、fallback、第二次 process、pipeline continuation、
publisher 或發布。

## 唯一 blocker

Structured envelope 已解決上一筆 canary 的 `JSON_INVALID`，真實回傳現在可進入
schema validation，但 Gemini 3.5 Flash 的輸出仍未符合指定 response schema。
Exactly-once ledger／anchor 與 CLI process 契約正常；不能以 target process
`SUCCESS` 取代 response schema 成功。

本卡不授權重送。下一步必須先在另立 Repair 卡中，以不保存 raw response 的方式
增加安全、結構化的 schema mismatch 診斷，經獨立 Review 後才可考慮新 canary。

# Gemini V4 Limited Activation-002 Decision

- status:
  `BLOCKED`
- decision:
  `BLOCKED`
- external invocation count:
  `1`

## 已通過

- Repair-2 已取得獨立 Review-2 GO。
- 全新 run identity、namespace、job ID、request digest 與 repo 外 runtime 已建立。
- 一筆 sanitized writer request 已通過 strict rebuild、digest 與 public-data
  validation。
- executable digest 與 verified `agy 1.1.5` identity 一致。
- runtime 尚無 ledger、anchor、inbox、archive 或 failed record。

## 真實執行結論

使用者在看到目標、payload、process 上限與副作用後明確確認。V4 runner 只執行
一次，durable ledger 與 external anchor 證明：

- replay `COMPLETE / 1`
- 恰一個 `EXEC_CONFIRMED`
- 恰一個 `PROCESS_TERMINAL / SUCCESS`
- replay errors `0`

Runner 隨後以 `V4BrokerFailure` fail closed；closed diagnostic 是
`result_validation=JSON_INVALID`。沒有 inbox，failed、archive、ledger 與 anchor
存在。沒有 retry、fallback、第二次 process、pipeline continuation 或發布。

## 唯一 blocker

V4 request 保存了 `role / prompt / response_schema`，但 production runner 傳給
broker target 的 `raw_request` 只有 `request["prompt"]`。相較之下，legacy
`GeminiClient._cli_transport` 會在 effective CLI prompt 中加入：

- writer／reviewer system instruction
- 單一 JSON object／禁止 Markdown code fence
- 完整 JSON schema

因此 V4 transport adapter 丟失了 structured-generation envelope。這與本次
`JSON_INVALID` 診斷一致；exactly-once ledger／anchor 本身正常。

下一步必須另立 Repair 卡，以 RED 測試鎖定 effective prompt 的 role、JSON-only、
schema、privacy 與 digest binding，再做最小 production 修正與獨立 Review。

本卡不授權第三次真實外呼。

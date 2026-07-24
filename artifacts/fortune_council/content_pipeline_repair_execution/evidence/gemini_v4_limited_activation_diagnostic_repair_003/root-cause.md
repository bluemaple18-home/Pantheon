# Gemini V4 Limited Activation Diagnostic Repair-3 Root Cause

## Preserved failure

Activation-003 的 durable ledger／anchor 證明 agy／Gemini target process 恰好一次、
以 `SUCCESS` 結束，replay 為 `COMPLETE / 1`。Broker 隨後以
`result_validation=SCHEMA_MISMATCH` fail closed；沒有 inbox、retry、fallback、
第二次 process 或發布。

## Root cause of the diagnostic blocker

現有 `_validate_json_schema` 只回傳 boolean。當真實回傳不符合 schema 時，
`BrokerResult` 與 runner failed record 只留下 `SCHEMA_MISMATCH`，沒有安全方法判斷：

- type／enum／required／additionalProperties
- minItems／maxItems／minLength／maxLength
- mismatch 所在的 schema-defined JSON path

Raw response 依 privacy 契約不保存，Activation-003 已終止且不得重送，因此目前沒有
證據能判定真實 mismatch 的特定欄位。這張 Repair 修正的是診斷盲點，不猜測模型
實際輸出。

## Falsifiable hypotheses

1. 若是局部欄位型別、必填或長度問題，下一筆經核准 canary 的 failed record 應只需
   bounded keyword／path 就能定位。
2. 若 validator 沒有安全結構可抽取，diagnostics 應保持空值，不能保存 response
   value 或任意 message。
3. 若 broker result 被 forged，runner 應丟棄未知 keyword、非 schema path、
   container token、過深 path、過長 token與超大 array index。

## Localized seam

- Broker seam:
  `_validate_json_schema`／`run_single_shot`／`BrokerResult`
- Runner seam:
  `_closed_broker_diagnostic`／`process_once` failed record
- Downstream:
  failed diagnostic only；不改 inbox、pipeline、publisher 或文章資料

CodeGraph 初始掃描涵蓋 129 files，索引 2154 nodes／4482 edges。Impact 查詢確認
production downstream 是 runner `process_once`，主要 regression surface 是
`tests/test_agy_gemini_outbox.py`；沒有 publisher 或 SEO pipeline production
symbol 需要修改。

## Minimal repair

- Boolean validator 保留原 public seam，內部改由 bounded diagnostic validator
  判定。
- 最多 3 筆、path 最深 8 層。
- Unknown additional property 只回報 parent path，不保存未知 key。
- 深層 mismatch 超過上限時只回報 bounded ancestor／`schema`。
- Runner 以 response schema 再驗 path，且只接受安全 token、bounded array index
  與固定 keyword allowlist。
- Failed record 不保存 prompt、raw stdout／stderr、response body／value、
  validator message、credential 或完整 environment。

## Remaining blocker

真實 Gemini 回傳究竟是哪個欄位不符合 schema仍未知。Repair-3 必須先經獨立
Review；Review GO 後若再建 canary，仍需新的 final payload disclosure 與使用者
確認。該 canary 即使取得 diagnostics，也可能仍是 BLOCKED，不能保證一次打通。

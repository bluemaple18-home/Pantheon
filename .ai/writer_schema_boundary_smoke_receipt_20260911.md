# Writer schema boundary 真實 smoke receipt（2026-09-11）

## 目的

驗證 `919dcd2f68` 的 provider-schema boundary repair 在真實 Writer provider 呼叫下是否成立，並區分 transport/schema failure 與 Writer 內容品質收斂問題。

## 執行邊界

- Branch：`codex/web-schema-boundary-repair-20260911`
- Repair commit：`919dcd2f6808`
- Writer：`gemini-3.5-flash-lite`
- Reviewer route：`gemini-3.1-flash-lite`
- Fixture：單篇合成 create brief，`SMOKE-SCHEMA-BOUNDARY-20260911`
- 輸出：僅 `/private/tmp`
- 未執行：publish、apply、approval、production mutation、queue mutation、服務啟停、模型 route/config 變更

## Smoke A：max_repairs=1

Run dir：`/private/tmp/pantheon-writer-schema-smoke-20260911.LL0nGW`

- 有效 Writer attempt 1 成功取得 provider response。
- `writer-schema-rejection.json` 不存在。
- `schema_repairs_used=0`。
- 初稿 deterministic findings：`description_length`、`answer_length`、`body_length`、`paragraph_length`。
- bounded repair 正常啟動；第二次 external payload 只包含 `slot + answer + bodySections + description`，已通過的 title 未被重做。
- repair 後 `body_length` 已清除，仍剩 `description_length`、`answer_length`、`paragraph_length`。
- 最終 `validator_result=FAIL`；未進正式 Reviewer approval。

這證明不合長度的真實模型輸出已能穿過 provider transport schema，進入 deterministic local gate 與 bounded repair；architecture repair 的 runtime boundary 成立。

## Smoke B：max_repairs=2

Run dir：`/private/tmp/pantheon-writer-schema-smoke-r2host-20260911.N4FNDe`

### Attempt 1

- Writer provider：success
- schema rejection：無
- title：22 字
- description：46 字
- answer：38 字
- body：1948 字
- paragraph range：131–149 字
- findings：`description_length`、`banned_phrase`

### Attempt 2

- Writer provider：success
- bounded fields：`slot + bodySections + description`
- description：43 字
- body：1948 字
- paragraph range：131–149 字
- findings：只剩 `description_length`

### Attempt 3

- Writer provider：success
- bounded fields：`slot + description`
- description：65 字
- findings：仍為 `description_length`

### Run evidence

- `attempts=3`
- `content_repairs_used=2`
- `schema_repairs_used=0`
- `failure_codes=["description_length"]`
- `validator_result=FAIL`
- `apply_executed=false`
- `approval_created=false`

## 判定

`919dcd2f68` 的 schema boundary repair 可視為 runtime evidence PASS：真實 Writer 的不合長度輸出沒有再被 provider/outbox 的 `minLength/maxLength` 提前拒絕，local deterministic gate 與 bounded repair 都有實際執行。

剩餘 blocker 已縮小為 Writer model-fit / instruction-following：`gemini-3.5-flash-lite` 在兩次 bounded repair 後仍無法把 description 收斂至 canonical 70–95 字範圍。不得再以放寬 provider schema 或 canonical validator 處理此問題。

## Spark 狀態

目前 Pantheon 沒有已接通的 Spark runner/bridge。既有換手資料也明確記錄 Spark 只曾被提出為候選，沒有 runner 支援證據。當前可用的 Codex 原生模型 override 清單亦沒有名為 Spark 的模型，因此本輪沒有宣稱 Spark A/B 已完成，也沒有新建 bridge/runner。

後續若取得正式 Spark callable route，應使用同一合成 brief、同一 canonical quality gate、同一 repair budget 做 isolated A/B；比較指標至少包含 schema rejection、初稿 findings、每輪 bounded repair 欄位、最終 deterministic findings 與 provider call 數。

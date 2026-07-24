# Gemini V4 Limited Activation Diagnostic Repair-2 Re-review

## Findings

未發現阻塞問題。沒有 P0、P1、P2 或 P3 finding。

## Spec axis

- 合法 JSON `null` 在 production broker path 分類為 `NOT_OBJECT`。
- Invalid JSON、array、schema mismatch 與 valid object 分別維持
  `JSON_INVALID / NOT_OBJECT / SCHEMA_MISMATCH / VALID`。
- `replay_status / process_count / outcome / result_validation` 全部先做 exact-type
  與 closed-value normalization。
- Forged scalar、container 與 unhashable 值不會 crash，不會原樣寫入 failed
  record。
- `V4BrokerFailure` message 只使用 sanitization 後的
  `INVALID/UNKNOWN`，不含 forged marker。

## Standards axis

- Candidate production 修改只涉及 broker 的 result classification 與 runner 的
  closed diagnostic helper。
- Failed record consumer 仍只讀 `error_type`，新增 diagnostic 維持相容。
- Flag-off legacy、flag-on fail-closed／no-fallback、receipt mismatch 與 existing
  operation no resend 均通過 regression。
- Candidate 沒有修改 ledger、anchor、replay、spawn 或 process confirmation
  implementation；相關 exactly-once tests 全綠。
- 沒有 publisher、文章、registry、automation、default transport 或 legacy
  removal 變更。

## Security / privacy

- 四個 diagnostic 欄位只可能落入 closed safe values。
- Container／unhashable inputs 在 membership 前即被 exact-type guard 擋下。
- Failed record 與 failure message 均未保留 synthetic forged marker。
- Candidate production diff 沒有新增 prompt、raw stdout／stderr、response body、
  credential 或完整環境持久化。

## Remaining risk

Runner 的 diagnostic allowlist 與 broker state domain 是兩份明確常數；未來若新增
合法 broker state 而未同步，diagnostic 會安全降級為 sentinel。這是 fail-closed
維護風險，不是目前 candidate 的阻塞問題。

## Review 結論

Verdict:
`DELIVERED_CANDIDATE / GO`

GO 只代表可交回主線評估下一階段，不授權 activation、整合、上線或第二次真實
外呼。

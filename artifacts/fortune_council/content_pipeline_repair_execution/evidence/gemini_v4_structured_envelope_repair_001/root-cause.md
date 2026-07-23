# Gemini V4 Structured Envelope Repair Root Cause

## Durable failure

Activation-002：

- replay:
  `COMPLETE / 1`
- terminal:
  `SUCCESS`
- caller:
  `V4BrokerFailure`
- result validation:
  `JSON_INVALID`

Exactly-once process accounting 正常，content caller contract 失敗。

## Localized layer

Legacy `GeminiClient.generate_json` 建立 role instruction 與 structured generation
config；`GeminiClient._cli_transport` 將 role、JSON-only、no-code-fence、schema 與
user task 組成 CLI prompt。

V4 outbox request 同樣保存 `role / prompt / response_schema`，但 production runner
過去只把 `request["prompt"]` 當成 broker `raw_request`。因此 fault 位於
runner→broker adapter seam，不在 broker、ledger、anchor 或 replay。

## Red-capable feedback loop

Runner public seam 使用 validated outbox request 與 fake broker capture。修正前：

- writer expected structured envelope，actual 只有 `公開 V4 prompt`
- reviewer expected structured envelope，actual 只有 `公開 V4 prompt`
- flag-off legacy 仍通過

結果：
`2 failed / 1 passed`

## 最小修正

Flag-on runner deterministic 渲染：

1. closed writer／reviewer role instruction
2. 禁止工具與讀取工作區
3. 單一 JSON object／禁止 Markdown code fence
4. `ensure_ascii=false / sort_keys=true / compact` schema
5. sanitized user task

完整 UTF-8 bytes 傳入既有 broker，因此 CommandFrame 的 prompt digest／byte count
自然綁定 effective prompt。External request receipt 仍綁 outbox request digest。

Flag-off 不經此 renderer。Broker、ledger、anchor 與 replay 未修改。

## 假說結果

- `H1` runner 遺失 envelope：
  supported；RED→GREEN。
- `H2` broker 改寫或截斷 payload：
  falsified；既有 target digest／byte-count tests 全綠。
- `H3` 真實 agy 仍可能不遵守完整 envelope：
  未由本 Repair 驗證，保留為未來 canary 風險。

本 Repair 沒有 Gemini／agy invocation，也沒有第三筆真實 payload。

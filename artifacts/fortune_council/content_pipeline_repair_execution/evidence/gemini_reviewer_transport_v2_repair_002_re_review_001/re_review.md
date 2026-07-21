# Transport V2 Repair 2 independent re-review

## Decision

`NO_GO / BLOCKED`

固定 candidate `fe62f1679bf248b0c55a6cea566315dca15a2e07` 未封閉 P1-01。最後一代 Repair 已用盡；禁止 Repair3、merge、push、deploy、publish 與恢復內容線。

## Spec axis findings

### P1-01｜後續 retry 只驗 base pair，會跳過最新 runtime-retry pair

- path: `scripts/agy_seo_copy_pipeline.py:2555`
- trigger: 建立合法 failed 的 attempt-01 base pair，再建立 attempt-02 runtime-retry terminal，但把其 gate 綁到另一 item；以 attempt-03 呼叫 `_generate_with_receipt`。
- evidence: production code固定讀取 caller 傳入的 base `receipt_path`，在 `2599-2605` 只以既存 retry 檔尋找下一個空檔名，未把最新 runtime-retry receipt/gate 送入共用 pair validator。獨立 probe 顯示 `client.calls == 1` 且 `terminal-receipt-runtime-retry-02.json` 已建立。
- risk: 錯綁、毀損或不完整的最新 persisted pair 無法在下一次 client call/receipt 前 fail closed；external/reviewer process 可在 evidence integrity failure 被 replay 發現前啟動。這違反固定 P1-01 retry authorization contract。
- suggested fix: 在任何新 invocation、client call或receipt前，嚴格列舉並驗證完整且連續的既有 retry chain，並以最新合法 failed pair作為唯一 retry authorization；但本鏈禁止 Repair3，因此只能維持 BLOCKED。
- validation gap: candidate test只覆蓋 base pair錯綁後的 attempt-02，未覆蓋 attempt-03 對錯綁 runtime-retry-01 的行為。
- confidence: high

## Standards axis

未發現獨立於上述 P1 的新增 standards finding。P1-02、P1-03、P2-01 的原始固定 REPRO 均已阻擋；不抵銷仍可重現的 P1-01。

## Testing gaps

- 缺少三次以上 logical attempt 的 persisted-chain probe。
- 缺少「base合法、最新 retry pair錯綁／缺漏／毀損」時，在 client call 前維持零呼叫與零新receipt的斷言。

## Residual risks

- replay最終可能拒絕整體 evidence，但拒絕發生在新 client call之後，無法滿足 transport safety invariant。
- full suite的兩個 Ziwei failure為固定 baseline，已如實分列，未宣稱全綠。

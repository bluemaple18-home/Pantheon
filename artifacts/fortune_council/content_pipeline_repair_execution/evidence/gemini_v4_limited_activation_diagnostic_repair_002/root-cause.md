# Gemini V4 Limited Activation Diagnostic Repair-2 Root Cause

## 判定

前一版安全診斷有兩個彼此獨立的實作缺口：

1. parse failure 使用 `None` 當 sentinel，與合法 JSON `null` 的 decode 結果相同。
   後續分支因此無法把 `null` 判為 JSON non-object，最後保留
   `NOT_EVALUATED`。
2. Runner 只對 `result_validation` 做集合檢查，另外三個診斷欄位直接取自
   `BrokerResult`。此外，未先驗證型別就執行 set membership，dict／list 等
   unhashable 值會觸發 `TypeError`。

## RED 證據

- 合法 JSON `null`：
  expected `NOT_OBJECT`，actual `NOT_EVALUATED`。
- forged container diagnostics：
  expected `V4BrokerFailure` 與 closed diagnostic，actual `TypeError`。

## 最小修正

- JSON decode 改成 `try / except / else`：
  decode exception 才是 `JSON_INVALID`；任何成功 decode 的非 dict 值（包含
  `null`）都是 `NOT_OBJECT`。
- Runner 在建立 failed record 與 failure message 前，先將四個欄位封閉：
  - invalid `replay_status` → `INVALID`
  - invalid `process_count` → `UNKNOWN`
  - invalid `outcome` → `null`
  - invalid `result_validation` → `NOT_EVALUATED`
- 所有 membership 前先做 exact type guard，forged scalar／container 不會原樣
  持久化，也不會造成 unhashable exception。

## 未改動

- exactly-once ledger、anchor、replay 與 process spawn 邏輯
- flag-on fail-closed／no legacy fallback
- flag-off legacy transport
- publisher、文章、registry、automation 與發布路徑

本 Repair 沒有 Gemini／agy 外呼，沒有 retry 前次 job。

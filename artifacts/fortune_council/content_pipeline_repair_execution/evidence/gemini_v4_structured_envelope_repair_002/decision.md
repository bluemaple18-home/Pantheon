# Gemini V4 Structured Envelope Size Repair-2 Decision

- status:
  `DELIVERED_CANDIDATE`
- decision:
  `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- provisioning commit:
  `87b1cd48`

## 結果

- Review 的 maximum-size regression 已以 RED 精確重現。
- Broker effective-prompt ceiling 從 raw-task `256 KiB` 修正為
  task `256 KiB` + schema `64 KiB` + closed envelope `64 KiB` =
  `384 KiB`。
- 最大合法 task/schema rendered prompt 為 `327942 bytes`，現在落在 ceiling
  內；ceiling+1 仍在 ledger 前拒絕。
- 213 個受影響 tests 全綠。
- outbox public limits、process、ledger、anchor、replay 與 flag 邊界維持。
- 沒有 Gemini／agy invocation、retry、第三筆真實 payload、push、deploy、
  publish、promotion 或 legacy removal。

## 判定

本 Repair-2 可交回原獨立 Review thread re-review。

此決策不是 activation、GO、整合或上線授權，也不授權第三次真實外呼。

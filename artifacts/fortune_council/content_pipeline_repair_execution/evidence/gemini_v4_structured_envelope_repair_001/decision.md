# Gemini V4 Structured Envelope Repair Decision

- status:
  `DELIVERED_CANDIDATE`
- decision:
  `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- provisioning commit:
  `c7d4e4dd`

## 結果

- Activation-002 的 `JSON_INVALID` 已定位到 runner adapter 遺失 structured
  generation envelope。
- RED 在 writer 與 reviewer seam 精確重現，修正後轉綠。
- effective prompt 現在 deterministic 包含 closed role、JSON-only、
  no-code-fence、canonical schema與 sanitized user task。
- 212 個受影響 tests 全綠。
- flag-off legacy、flag-on no-fallback 與 exactly-once broker 邊界維持。
- 沒有 Gemini／agy invocation、retry、第三筆真實 payload、push、deploy、
  publish、promotion 或 legacy removal。

## 判定

本 Repair 可進入獨立 Review。

此決策不是 activation、GO、整合或上線授權，也不授權第三次真實外呼。

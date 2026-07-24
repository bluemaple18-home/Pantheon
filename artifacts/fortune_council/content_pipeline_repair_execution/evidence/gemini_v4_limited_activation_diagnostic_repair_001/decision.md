# Diagnostic Repair Decision

- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_REVIEW`

## 判定

真實 activation 暴露的診斷缺口已由 synthetic RED 重現，並以最小 production
修改修復：

- broker 能安全區分 JSON invalid、non-object、schema mismatch、valid 與
  not-evaluated。
- runner 只持久化封閉、非內容的 broker diagnostic。
- raw response 與 prompt 仍不保存。
- flag-on fail-closed、no legacy fallback 與 exactly-once ledger／anchor 契約不變。
- 208 個受影響測試全綠。

候選可交獨立 Review，但不代表前次真實 article activation 已通過。

## 下一步

1. 獨立 Review 本候選的分類正確性、privacy 與 no-fallback。
2. Review GO 後，另立新的 limited activation 卡。
3. 第二次真實外呼前重新鎖 payload 並取得明確授權。

## 未授權

- Gemini／agy invocation
- retry 前次 job
- second real payload
- push
- deploy
- publish
- activation
- default promotion
- legacy removal

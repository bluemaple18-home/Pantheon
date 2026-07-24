# Final Sync Decision

- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_ACTIVATION_REVIEW`
- candidate merge:
  `dcaddc49acd812798a058b36b833fe4fe2a022ec`

## 判定

固定 v0.3.8 發布內容已與獨立 Review GO 的 V4 transport 候選在本地無衝突合併。

- V4 scope 與 reviewed lineage byte-identical。
- 發布 scope 與固定 v0.3.8 publisher commit byte-identical。
- 205 個唯一測試通過。
- compile、privacy、scope、debug 與 diff gates 通過。
- 沒有外部呼叫、發布、部署或 transport 切換。

因此候選可進入獨立 activation review，不能直接視為 production 已整合或 V4
已成為預設。

## 尚存風險

1. 自動 publisher 可能讓遠端主線在 activation 前再次前進；任何遠端整合都必須
   重新鎖定當下 SHA 並驗證 ancestry。
2. 真實文章 payload 尚未送入 V4；下一階段必須先鎖 payload、外部效果與不發布邊界，
   再取得明確確認。
3. legacy 仍保留為 flag-off 路徑；只有 limited activation 與觀察期通過後，才能另案
   決定預設化與退場。

## 未授權

- push
- deploy
- publish
- activation
- default promotion
- legacy removal

# Pantheon launchd activation recovery

## 目的

修正 production capacity guard 對 `StartInterval` 排程服務短暫無 PID 的誤判，恢復四條發文線與 Publisher，完成一篇新文發布及 sitemap +1 證據。

## 已知狀態

- Source／remote／runtime SHA：`167566d70fefdbe4f19489647569d6a891deb096`
- Promotion：`COMMITTED`
- 測試：先前 RED 1 failed，修補後 GREEN 81 passed
- 現場 blocker：capacity guard `loaded_service_pid_missing`
- 100ms bounded re-read 在 production 仍不足
- 第三次失敗後其餘六服務已安全卸載
- Publisher、tag、push、sitemap +1 尚未執行

## 工作範圍

1. 先讀現有 Recovery task 與 promotion receipt，確認現場狀態，不重做已完成整合。
2. 只修 activation/capacity guard 對 launchd 排程服務的轉態判定。
3. 判定須接受可證明正常的短命排程服務；持續異常、錯誤 identity/path、非零退出仍 fail-closed。
4. 補最小回歸測試：短暫無 PID 可恢復、持續異常仍 NO-GO。
5. 跑受影響測試、`git diff --check`、容量安全閘門。
6. 安全啟動七服務並驗證四條線：`new`、`rewrite`、`i18n-new`、`i18n-rewrite`。
7. Publisher 必須 exit 0；產生新文章 commit/tag/push；公開 sitemap 文章數 +1。

## 禁止

- 不新增架構層、第二套流程、Reviewer／Repair 卡。
- 不刪 queue、不 force push、不放寬 identity/path 驗證。
- 不用無界 retry；同一新 blocker 三次即停並回報精確證據。
- 不把舊 log 當本次執行證據。

## 交付

- 修補 commit SHA 與推送狀態。
- 測試命令與結果。
- 七服務 activation 證據、四線狀態。
- 新文章 slug、Publisher exit、commit/tag/push。
- 公開 sitemap 前後數量與 URL。
- 若 NO-GO：唯一 blocker、原始錯誤、已完成回滾／停線狀態。

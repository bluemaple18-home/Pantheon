# Pantheon 四線狀態收斂與獨立處理

## 目標

讓 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 四條線各自只領取、處理、完成自己的 queue 任務；恢復正常排程，且不混線、不重複處理、不留下假 active。

## 現場基線

- capacity guard 修補 SHA：`387d73eef8cb525efced572f5aef772ee9a135e2`，已 push。
- 已發布 `tarot-1818`：commit `9d57ebf`、tag `v0.3.366`。
- 已發布 rewrite：commit `5c0f244`、tag `v0.3.367`。
- 公開 sitemap：`624 → 625`。
- 七個 launchd 服務目前全部 unloaded。
- 未完成 transaction：`state/transaction-dr50kr8n`；內容未發布，已有 `/private/tmp/pantheon-stopped-publisher-transaction-20260817T2105` 備份。
- Queue 未刪；`097`、`098` 與數個 i18n runs 顯示 active，但目前沒有服務處理。

## 工作範圍

1. 唯讀盤點 transaction、queue、main/origin/runtime/Publisher identity；先產出單一基線。
2. 對 `transaction-dr50kr8n` 使用既有安全 rollback/recovery 入口；禁止手動刪目錄或丟內容。
3. 將沒有 live owner 的假 active runs 依既有 queue 契約恢復為可重試狀態；禁止刪 queue、禁止跨 lane 改寫 ownership。
4. 對齊 main／origin／runtime／Publisher 至同一已核准 SHA；不得繞過 descendant、identity、path preflight。
5. 通過容量安全閘門後，只啟動既有七服務，不新增服務或架構。
6. 四線各執行最多 1 筆 bounded acceptance run：
   - `new` 只處理 new 任務。
   - `rewrite` 只處理 rewrite 任務。
   - `i18n-new` 只處理 i18n-new 任務。
   - `i18n-rewrite` 只處理 i18n-rewrite 任務。
7. 驗證每筆 run 的 lane、run ID、輸入、輸出、狀態轉移與 Publisher 接收一致；不得重複或串線。
8. Publisher exit 0；需要發布的驗收輸出正常 commit/tag/push。驗收後保留正常排程啟用，不再額外 kickstart。

## 停止條件

- 任一 lane 出現 ownership 混線、重複領取、資料遺失風險：立即停止全部服務並回報。
- 同一 blocker 最多三次；禁止換錯誤名稱繼續 retry。
- 遇到新 bug：停止，不擴寫架構、不順手修第二題。

## 禁止

- 不新增卡、Reviewer、Repair、流程層或相容 adapter。
- 不刪 queue、不 force push、不手動改已發布文章。
- 不用 `max-runs > 1` 做驗收。
- 不以 log 文案取代 queue state、process ownership、git remote 與公開 sitemap 證據。

## 完成證據

- transaction 已收斂，無未完成 Publisher transaction。
- 無缺少 live owner 的假 active runs。
- main／origin／runtime／Publisher identity 對齊。
- 七服務 loaded；排程型 idle 服務可合法無 PID。
- 四線各 1 筆 bounded run 的 run ID、lane、結果與無混線證據。
- Publisher exit、commit/tag/push；公開 sitemap 變化按任務類型解釋（rewrite 不要求數量增加）。
- 受影響測試、容量 gate、`git diff --check` 通過。

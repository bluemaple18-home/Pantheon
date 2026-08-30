# CARD-PANTHEON-FOUR-LANE-ACTIVATION-ACCEPTANCE-20260829

## 任務

正式啟用並驗收 Pantheon 四線 runtime automation。本文是本次唯一 activation acceptance 契約；未完成全部條件前，不得宣稱四線已自動運行。

## 固定版本與前置條件

- accepted origin/main：`6541693e929a20cbcffe8b070085b5f1caec7a92`
- live actor expected：`bde44589f3785aae738bb7d7b1626270ba5505d0`
- fresh Rule24：`PASS`
- fresh Rule25：`READY`
- promotion plan-only：兩次執行結果一致（`plan-only ×2`）
- 四條 lane：`new`、`rewrite`、`i18n-new`、`i18n-rewrite`

以上任一版本、actor、gate 或 plan-only 結果不符，立即 `NO_GO_FOUR_LANES`。

## 唯一允許的執行順序

1. 執行正式 promotion。
2. 安裝並載入 coordinator。
3. 安裝並載入 publisher，且不得引入 future selector。
4. 將 capacity guard 置於 recovery-stage。
5. 聚合 activation 狀態。
6. 依序執行四條 lane：`new` → `rewrite` → `i18n-new` → `i18n-rewrite`。
7. 每條 lane 必須且只能跑一次 fresh scheduler canary；原 Reviewer 必須明確 `APPROVE` 後才可 publish。
8. 四條 lane 各自完成 transaction、tag、push，並以公開網址 HTTP 200 且 rendered body 可見驗收。
9. 驗證七個服務均已 loaded、持續自動運行，且 stop-loss 可觸發並 fail-closed。

## 四線 canary 驗收契約

每條 lane 的 canary 必須具備 fresh scheduler 來源、正確 lane identity/correlation、完整 Writer → Reviewer → publish 鏈路與可重現 receipt。未取得原 Reviewer `APPROVE`，不得 publish；不得以舊 canary、人工 operator 流程或其他 lane 的 candidate 代替。

每條 lane 必須留下可核對的：

- 一次且僅一次 transaction
- 對應 tag 與 push 證據
- 公開網址 HTTP 200
- 公開頁 rendered body 可見

## Runtime 與 stop-loss

- 七個服務必須全部 loaded 且自動運行。
- coordinator、四個 lane runner、publisher、capacity guard 均須可由 runtime 狀態證明。
- capacity guard 必須在 recovery-stage，並能於容量、identity、順序、重複或 drift 時自動停損。
- stop-loss 觸發時立即停止後續 lane、rollback 至安全狀態，並保留 evidence；不得自行開啟 RCA 或 Repair。

## 禁止事項

- 禁止修改 code、source、test。
- 禁止手動修改 queue、registry、plist 或 stage。
- 禁止 placeholder、preallocation 或預先占位 candidate。
- 禁止跨 lane candidate、重用舊 canary 或多跑任何 canary。
- 禁止自動開 RCA／Repair。
- 禁止在 acceptance 未閉合前宣稱 production activation 完成。

## Drift 與最終判定

任一步發生 drift、版本不一致、服務未 loaded／未自動運行、Reviewer 非 `APPROVE`、transaction/tag/push/公開網址證據缺失、HTTP 非 200、rendered body 不可見或 stop-loss 無法證明：立即 `STOP`，rollback，最終判定只能是 `NO_GO_FOUR_LANES`。

只有所有前置條件、四次單次 canary、四線 publish、四組 transaction/tag/push/public URL、七服務 runtime 與 stop-loss 證據全部閉合，最終判定才可為 `GO_FOUR_LANES`。

## Final decision

唯一合法輸出：`GO_FOUR_LANES` 或 `NO_GO_FOUR_LANES`。

# Pantheon Publisher recovery 與單筆 rewrite 驗收

## 目的

將已整合的 Publisher prerender bounded timeout 修補正式提升到 production，安全收斂 `transaction-ond6ep49`，並只執行一筆 rewrite 驗收。

## 進入條件

- Source commit 已通過 Publisher affected tests 與 `git diff --check`。
- create → run → select → publish → transaction → tag → push 的正式 capability receipt 同時具備正向與 fail-closed 負向證據。
- Source／actor／runtime manifest identity 可核對，promotion 不繞過 descendant 與 path 驗證。
- 容量安全閘門為本次執行的新鮮 `PASS`。

## 工作範圍

1. 以正式 promotion／actor recovery 入口部署 exact source SHA。
2. 以正式 Publisher recovery 入口收斂既有 transaction；禁止直接刪除。
3. 啟動七個既有 launchd service，核對 identity 與 loaded 狀態。
4. 選定一筆既有 rewrite queue 任務，先 dry-run，再以 `--exact-run-id`、`--max-runs 1` 執行一次。
5. 驗證 Publisher bounded exit、ownership、commit／tag／push、queue 與 transaction 收斂。

## 停止條件

- capability、capacity、identity 或 promotion 任一關不是 `PASS／READY`，立即 `NO-GO`。
- production 首次出現新異常即停止 acceptance，不重試試運氣。
- 不啟動 `new`、`i18n-new`、`i18n-rewrite` 的新工作；不要求 rewrite 造成 sitemap 數量增加。
- 不手動改 queue、文章、tag、transaction 或 runtime manifest。

## 完成定義

- Publisher prerender bounded run exit 0。
- 恰好一筆 rewrite complete，且 lane ownership 正確。
- 無未完成 Publisher transaction、假 active、跨 lane或重複領取。
- 七服務 loaded，Capacity Guard PASS。
- 交付 exact SHA、run ID、Publisher exit、commit／tag／push 與證據路徑。

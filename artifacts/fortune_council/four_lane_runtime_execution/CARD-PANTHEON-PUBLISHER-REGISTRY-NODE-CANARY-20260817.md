# Publisher Registry Node Canary

## 工作名稱 → 正在做什麼 → 現在狀態

Publisher Registry Node Canary → 以 `811999c1e2dcacdfed9b96b9ea95369b2da7372b` 驗證單筆 rewrite 發布鏈 → 已授權，待執行

## 唯一 selector

`legacy-auto-sweep-v1-astrology-0003-astro-base-03`

## 執行邊界

- 只允許一次 normal activation；禁止 `activate-only`。
- `PANTHEON_PUBLISH_MAX_RUNS=1` 且鎖定 exact run ID。
- 不另建平行 canary，不改文章 selector，不手動刪 transaction。
- promotion、activation 或 Publisher 任一 fail-closed 即卸載七服務並以原 plan rollback。

## 前置閘門

- capability readiness 必須為 `READY`。
- 容量證據必須為 `PASS`，主機保留空間高於 `max(20 GiB, 10%)`。
- source、actor、manifest、stage 與 runtime digest 必須 exact match。

## 驗收

- Publisher 不再停於 registry Node subprocess。
- transaction 結束，沒有殘留 active transaction。
- 指定文章完成 publish transaction，commit、tag、push 均有正式證據。
- 完成後七服務卸載；promotion transaction finalize 或依失敗路徑 rollback。

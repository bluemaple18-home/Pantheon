# Pantheon 自動產文容量 watchdog 與復工卡

- status: IN_PROGRESS
- user_hold: false
- date: 2026-08-03

## 目標

沿用既有四 Lane、Publisher transaction orphan cleanup 與 32 MiB log 界線，
補上整體寫入預算、五分鐘監控、自動停損及重開機後 allocator identity rebind，
再恢復 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 正式排程。

## 可改範圍

- `scripts/agy_gemini_allocator.py`
- `scripts/pantheon_content_capacity_guard.py`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- `ops/launchd/com.pantheon.content-capacity-guard.plist.example`
- 對應測試與本卡 evidence

## 禁止範圍

- 不刪除或重跑 queue、ledger、receipt、candidate、文章。
- 不放寬內容、Reviewer、i18n 或 Publisher 品質 gate。
- 不清理其他專案、Codex、瀏覽器或使用者資料。

## 容量契約

- 登記路徑：Gemini queue、Publisher state、Pantheon LaunchAgent logs。
- `max_bytes`: 4 GiB；`max_file_count`: 120,000。
- 正常增長：每小時不超過 256 MiB；允許單次 transaction 1 GiB／60 分鐘尖峰。
- 主機啟動線：`max(30 GiB, 15%)`；執行停損線：`max(20 GiB, 10%)`。
- log：32 MiB 時同 inode 保留末 4 MiB；queue／ledger 不做猜測性刪除。
- 超限時只 bootout 六個 Pantheon 內容服務，watchdog 保留以留下證據。

## 驗收

1. allocator 在同一 lock inode、僅 filesystem device ID 因重開機漂移時安全 rebind；
   lock inode 替換仍 fail closed。
2. watchdog 的預檢、預算、log 輪替與只停六服務有自動測試。
3. installer／plist lint、受影響 pytest、`git diff --check` 通過。
4. 上線前可用空間達 34.2 GiB；watchdog 先載入，再載入五個 Gemini 服務與 Publisher。
5. 至少觀察兩個完整週期，量測 bytes、files、free disk、RSS、swap 與增長率。
6. 實際演練停用自動重啟後恢復；不得以 `idle` 冒充文章產出。

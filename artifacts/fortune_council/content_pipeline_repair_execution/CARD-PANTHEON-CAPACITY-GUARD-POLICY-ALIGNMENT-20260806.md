# Pantheon capacity guard 規則對齊

- 狀態：`VERIFIED_READY_FOR_INTEGRATION`
- 目標：讓 production capacity preflight 與現行 `rules/24-storage-capacity-safety.md` 的 10% 啟動門檻一致，解除錯誤的固定 30 GiB／15% 阻擋。
- 根因證據：主機可用空間約 30.6 GB（12.5%）符合現行 10% 規則，但既有 guard 以 `max(30 GiB, 15%)` 判定 `NO-GO`。
- 可改：`scripts/pantheon_content_capacity_guard.py`、對應測試、本卡。
- 禁止：降低 runtime 自動停損 `max(20 GiB, 10%)`、啟用 i18n lane、enqueue／處理／發布內容、修改 production queue 或 ledger。
- 驗收：先有能重現 false-block 的 RED 測試；最小修正後相關測試與全檔測試通過；`git diff --check` 通過；production preflight 回傳 `PASS`。
- Runtime 對齊目標：後續 actor 僅對齊審核後的 `origin/main`；原有服務集合原樣恢復，i18n 服務維持未載入。
- Rollback：capacity 修正可回退本提交；actor 可回退到 `2e227232be948c24011123a07122d33f68852419`。

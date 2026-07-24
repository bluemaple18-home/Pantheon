# Repair-2 Finding Matrix

Card: `CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-02-20260725`

Chain: `pantheon-publisher-deadlock-repair-20260724`

Generation: `Repair-2`

| Finding | Repair | Regression evidence | Status |
| --- | --- | --- | --- |
| PPD-R-001 | `MutationJournal` 不再從 mutation 後的 shared worktree 讀取無歸因 post-image；publisher mutating helper 改由 before/after capture 建立 write-set，無歸因 checkpoint 一律 conflict、保存 bytes 並 fail-closed。 | `test_recovery_preserves_concurrent_owned_write_before_unattributed_checkpoint`；`test_recovery_never_overwrites_concurrent_post_image_bytes` | GREEN |
| PPD-R-002 | inconsistent atomic push 先在 `state_root` 原子寫入 durable unresolved control record；所有 publish phase 在 clean-origin、collector、mutation 前檢查。reconciliation 只有在 remote main/tag、ledger、publish evidence 全部收斂後才能清除。 | `test_unresolved_push_record_blocks_next_full_publish_before_clean_origin`；`test_atomic_push_exception_reconciles_remote_matrix` | GREEN |
| PPD-R-003 | 移除獨立 queue 預掃的 attribution authority；三個真實 collector 完成全部 filters 後，把 selected run IDs 寫入 transaction journal，recovery/retry 僅使用該 context。 | `test_recovery_retry_uses_collector_selected_run_and_leaves_third_publishable` | GREEN |
| PPD-R-004 | Repair-1 已解決，本輪未修改其契約。 | `tests/test_agy_content_publisher.py` 完整回歸 | PRESERVED |

## Lineage

- Base: `41522076fccbe0406fb4d270d138368ce5c0395f`
- Original candidate: `21dab0283f5a6690d1d4cd1631efe1354955818e`
- Parent candidate / Repair-2 start HEAD: `6ea7a7ffdfd2280555af0400baa4dc0167babdce`
- Original Reviewer thread: `019f9497-d801-7183-b4a9-9c9388aadd15`

最終 Repair-2 candidate SHA 由本 evidence 所在的單一 commit 及 executor delivery 提供；commit 無法在自身 tracked content 內自我引用其 SHA。

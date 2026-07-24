# CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724

Status: `REPAIR_READY_FOR_REVIEW`

Parent candidate: `21dab0283f5a6690d1d4cd1631efe1354955818e`

Chain: `pantheon-publisher-deadlock-repair-20260724`

Generation: `Repair-1`

## RED → GREEN

| Finding | RED（原 Reviewer 證據） | GREEN（Repair-1 regression） |
| --- | --- | --- |
| PPD-R-001 | `concurrent_owned_edit_preserved=False`；base snapshot 位於內部 lock 前，recovery 無 pre/post image。 | `test_transaction_preserves_owned_change_between_clean_check_and_mutation` 與 `test_recovery_never_overwrites_concurrent_post_image_bytes` 使用真實 Git，分別證明 mutation 前與 publisher post-image 後的 concurrent bytes 均不被覆寫；衝突時 fail-closed。 |
| PPD-R-002 | atomic push 可能已被 remote 接受，但 client raise 後直接 local rollback。 | `test_atomic_push_exception_reconciles_remote_matrix` 覆蓋 remote 未接受、main/tag 都接受、main/tag 不一致；遠端 main/tag 均以 fetch state 對帳，不一致產生 `PUSH_OUTCOME_UNKNOWN` evidence。 |
| PPD-R-003 | `failed_recovered` 沒有 run-scoped retry/defer，`max_runs=1` 可永久餓死後方 run。 | `test_failed_first_queue_run_is_deferred_and_second_run_remains_publishable` 使用雙 queue：保留 bad queue/candidate，寫入 repo-state retry metadata，collector 跳過 deferred bad run，並由 publisher 發布 healthy run。 |
| PPD-R-004 | cleanup 前沒有完整 metadata；cleanup fault 可能只留下 patch。 | `test_recovery_fault_always_has_pre_cleanup_metadata` 對 archive copy、update-ref、restore、unlink、tag delete、final evidence write 做 fault injection；每次先存在 immutable `failure-attempt.json`，且 `recovery-result.json` 標示 failed step。 |

## 實作契約

- Repo-scoped transaction lock 在 clean/base snapshot 前取得，持有至 publish、push reconciliation、recovery 結束。
- 只有 `MutationJournal.begin()` 進入 mutation phase 後才允許 recovery。
- Mutation journal 保存 owned write-set 的 pre-image 與 expected post-image hash；restore 前逐 path 比對。
- Push exception 後 fetch remote main 與隔離 tag ref；雙 ref 精確指向 candidate 才視為 committed。
- Retry metadata 寫在 publisher state root，不修改或刪除 queue、ledger、candidate payload。
- Cleanup 前原子建立 `failure-attempt.json`；每一步原子更新 `recovery-result.json`。

## 驗證摘要

- Required regression / publisher focused：32 passed，exit 0。
- 三個 AGY test files：107 passed，exit 0。
- `tests/test_web.py`：63 passed、1 個既有 dependency deprecation warning，exit 0。
- Full pytest：401 passed、1 個既有 dependency deprecation warning，exit 0。
- Full suite 初跑因缺 `node_modules/iztro` 出現卡片預列的兩項 Ziwei failure；以既有 `pnpm-lock.yaml` 執行 frozen install，manifest 與 lockfile 均未修改，重跑全綠。
- `git diff --check`：exit 0。

## Changed files

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724/finding-matrix.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-01-20260724/verification.json`

下一步：交回原 Reviewer thread `019f9497-d801-7183-b4a9-9c9388aadd15` re-review。

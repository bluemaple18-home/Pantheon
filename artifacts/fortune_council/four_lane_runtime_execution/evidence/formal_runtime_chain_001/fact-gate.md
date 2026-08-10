# Strict fact gate

- 基線：`f31ef017170c69543528708fd1314dc87ff7528a`；舊 final review `4ac00e6b18da89a911d6f9a3d51b788e8b364b2c` 的 OPEN 僅為 `PANTHEON-RECOVERY-003/005/008`。
- 受影響正式入口：`agy_gemini_coordinator.register_run/cycle_once/main`、`agy_gemini_runner.process_once/main`、`agy_content_publisher.collect_ready_runs/publish_ready_runs/main/_stage_commit_tag_push`、`pantheon_content_capacity_guard.preflight/check_once/main`、`pantheon_content_runtime_manifest` CLI、三個 installer 與四個 plist template。
- 目前缺口：adapter 只回固定 transition；七個 runtime entrypoint 不讀 manifest；barrier 沒有 service ack，且先釋放五個服務才啟動 publisher/guard；rollback 只看 label loaded，沒有比對已保存 control-plane identity。
- Runtime identity schema：`manifest_digest`、`queue_root`、`publisher_state_root`、`actor_root`、`service_label`、`identity`、`runtime_digest`、`config_version`、`generation`、共同 `runtime_identity_digest`。所有值只使用 synthetic 或本 worktree/暫存 root。
- Mutation gate：coordinator 在建立 queue/lock 前、runner 在 claim 前、publisher 在 state/lock/transaction 前、capacity guard 在 snapshot/state 前驗證；publisher transaction 前二次驗證。
- Barrier gate：七個 label 先寫帶 generation/runtime identity digest 的 private ack；activation owner 只在 7/7 完整一致後原子寫 barrier；服務執行 child 前重驗 manifest/generation/barrier。
- Rollback gate：每個 label 的 byte-exact config、loaded state、實際 `launchctl print` control identity 都要一致；任一 mismatch 固定 `ROLLBACK_FAILED`。
- 授權邊界：不碰 production queue、network、正式發布、tag、push、deploy、launchctl；所有動態證據在隔離 temp root，tag/push 只走正式 fail-closed dry-run plan。
- 驗證：FR/SC 新正負例、既有六個受影響 test files、repository full pytest、三個 shell `bash -n`、四個 plist `plutil -lint`、`git diff --check`。

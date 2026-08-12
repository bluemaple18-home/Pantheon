# Formal runtime chain evidence index

- 正向正式鏈：`capability-positive/receipt.json`。同一 correlation 依序走過 create、run（四 lane）、select、publish validation、transaction dry-run、tag plan、push plan；每一步含 production entrypoint、input/output digest、return code 與 runtime identity digest。
- Capability 負例：`capability-negative-publish/receipt.json`。publish handoff digest 漂移時固定 `BLOCKED`，後續 transaction/tag/push 未執行。
- 七服務 identity matrix：`targeted-suite.junit.xml` 的 `test_each_service_identity_mismatch_fails_before_first_io[...]` 七個 parameterized case；coordinator、四 lane、publisher、capacity guard 均在 marker/queue/state I/O 前拒絕 stale config identity。
- Barrier matrix：`targeted-suite.junit.xml` 的 `test_seven_service_barrier_requires_complete_matching_acknowledgements` 驗證 6/7 不放行與 7/7 原子放行；`test_early_service_acknowledges_but_cannot_run_before_barrier` 驗證提早啟動只可 ack，不可執行 child I/O。
- Rollback matrix：`targeted-suite.junit.xml` 的 `test_rollback_identity_requires_saved_actual_control_plane_match` 與 `test_four_lane_activation_failure_restores_previous_plists_and_loaded_state[...]`，涵蓋一致時成功及重新載入 control identity 不一致時 `ROLLBACK_FAILED`。
- Targeted receipt：`targeted-suite.junit.xml`，242 passed（含 actor recovery fail-closed unit case）。
- Repository full receipt：`full-suite-collection-failure.junit.xml` 保存未安裝 Playwright 的 collection blocker；`full-suite-with-known-dependency-exclusion.junit.xml` 排除此單一 blocker 後為 970 passed、5 unrelated failed。兩個 provider assertion failure 與三個被 `.githooks/pre-push` 缺 worktree `.venv/bin/python` 擋下的 local-temp recovery fixture push，所涉測試與 production 檔均未被本卡修改。
- 靜態 gates：三個受影響 installer `bash -n`、四個 plist `plutil -lint`、`git diff --check` 的最終結果記於 candidate 回報；本卡沒有 launchctl mutation、network、正式 queue、tag、push 或 deploy。

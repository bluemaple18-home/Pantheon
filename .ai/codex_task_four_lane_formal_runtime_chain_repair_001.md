# Codex task：修復正式 Publisher capability 呼叫鏈

- 目標：只修復 `PANTHEON-FORMAL-RUNTIME-001`，讓同一 `formal_capability_preflight()` 真正命中正式 Publisher／transaction／release boundary，並以 injected dry-run 保證零正式副作用。
- 完整契約：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-001.md`。
- 可改：`scripts/agy_content_publisher.py`、`tests/test_pantheon_content_capability_probe.py` 及本卡 task-owned evidence。
- 禁止：修改 adapter／其他 source；修 P2；merge、push、deploy、production、launchctl；子代理或外部 provider。
- 模型：`gpt-5.6-sol high`；本卡 `NOT_ELIGIBLE` 使用子代理。
- 驗收：public-interface invocation tests、targeted regression、`git diff --check`、allowlist inventory、repair-only commit、clean worktree，交回原 Reviewer re-review。

# Codex task：封住 capability sandbox 路徑信任邊界

- 目標：關閉 `PANTHEON-FORMAL-RUNTIME-001` 剩餘缺口；保留真實 production-boundary invocation，外部／symlink queue/state 在首次 I/O 前拒絕。
- 完整契約：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-002.md`。
- 可改：Publisher、capability Adapter、同一 capability test 及 task-owned evidence，共 3 個 source/test 檔。
- 禁止：其他 source/test、P2、topology/schema、merge/push/deploy/production/launchctl、子代理與外部 provider。
- 模型：`gpt-5.6-sol high`；`NOT_ELIGIBLE` 使用子代理。
- 驗收：外部 queue/state/symlink escape 零 I/O fail-closed；sandbox 內正式 calls 保持；targeted regression、allowlist、repair-only commit、clean，交回原 Reviewer。

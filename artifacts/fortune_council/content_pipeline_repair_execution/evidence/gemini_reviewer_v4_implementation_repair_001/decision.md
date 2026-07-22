# Gemini Reviewer V4 implementation Repair 1｜Decision

Status: `READY_FOR_REVIEW`

## Evidence-based decision

- 唯一 P1 `V4_IMPL_PREFORK_ABORT_EVENT_MISSING` 已由 real `run_single_shot` regression 鎖定並轉綠。
- 未修改 replacement probe 顯示 durable 三事件、target 0、result 與 fresh replay `BLOCKED / 0`、complete false、automatic resend false。
- Broker focused、implementation affected、determinism、compile 與排除兩個已知 baseline 的全套 regression 均通過。
- 完整全套只保留卡片明列、未修改的兩個 Ziwei provider baseline failure。
- 改動限制在 Repair allowlist，沒有 runner／flag／anchor boundary、retry、fallback、第二 launcher或外部 runtime 行為變更。

## Review boundary

本卡只交付 Repair candidate，不自審 `GO`。需交回 replacement Reviewer或全新 Reviewer re-review；review `GO` 前不得整合、真實 CLI canary、deploy、publish或恢復內容線。

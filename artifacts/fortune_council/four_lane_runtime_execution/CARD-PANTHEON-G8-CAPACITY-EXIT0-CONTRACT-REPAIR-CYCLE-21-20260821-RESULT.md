---
id: CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821-RESULT
card_id: CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821
status: fixed
full_suite_status: BLOCKED_BY_HOST_CAPACITY
runtime_mutation: false
---

# Capacity preactivation exit-0 契約修復結果

## 結論

`validate_preactivation_transition` 的 exit code allowlist 已由 `[]/[78]` 最小擴充為 `[]/[0]/[78]`；未知 exit code `1` 仍 fail-closed。未執行 LaunchAgent、runtime preflight、activation、canary、transaction、tag 或 push。

終局：`FIXED / READY FOR MAINLINE`

## 變更

- `scripts/pantheon_content_capacity_guard.py`：只修改一行 preactivation exit code allowlist。
- `tests/test_pantheon_content_capacity_guard.py`：測試 launchctl fixture 可指定 last exit code；新增 public Python seam regression，驗證 exit `0` 通過、exit `1` 拒絕且無 mutation。

## 驗證證據

- RED：`test_preactivation_transition_accepts_exit_zero_and_rejects_unknown` 在 source 修正前失敗於 `preactivation service mismatch`，`1 failed`。
- targeted GREEN：主線重跑為 `1 passed`。
- 完整檔：`46 passed, 5 failed`，狀態為 `BLOCKED_BY_HOST_CAPACITY`。五個失敗均在目標 transition seam 前由當前主機 `disk_free_below_start_floor` 觸發，不是本 diff regression；未修改或繞過 10% 容量安全門檻。
- `git diff --check`：PASS。

## 剩餘驗收條件

主線需在 free disk 不低於 10% 的驗收環境重跑完整 `tests/test_pantheon_content_capacity_guard.py`，確認五個既有 installer 測試恢復 GREEN。

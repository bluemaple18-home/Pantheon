---
id: CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821-RESULT
card_id: CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821
status: fixed
full_suite_status: PASS
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
- 完整檔：主機容量恢復至 free `10.0669%` 後重跑，`51 passed in 19.12s`，狀態為 `PASS`；未修改或繞過 10% 容量安全門檻。
- `git diff --check`：PASS。

## 最終驗收

targeted regression 與完整 capacity 測試皆已 GREEN；先前五個 `disk_free_below_start_floor` 環境假失敗在容量恢復後消失。

# CARD-PANTHEON-FOUR-LANE-ACTIVATION-TEMP-PLIST-CANONICAL-PATH-REPAIR-20260829

## 目標

修正 capacity guard installer 在 preactivation validator 傳遞暫存 plist 時，未使用 canonical path 的缺口。

## 允許修改

- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- `tests/test_pantheon_content_capacity_guard.py`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/RESULT.md`
- 同目錄下最小必要的唯讀驗證證據

## 禁止範圍

不得修改 capacity guard、runtime manifest、shared validator、stage/plist 手動內容、publisher/coordinator/lane/aggregate/queue/registry；不得執行 production install、activate、canary、commit、push、tag 或 deploy。

## 驗收

- `/var` → `/private/var` alias 於 public installer/preactivation seam 先 RED、修後 GREEN。
- canonical counterfactual 與 normal、`--install-recovery-stage` 回歸通過。
- owner、mode、symlink、relative、missing、canonicalization failure 均維持 fail-closed。
- 不改變 bytes、uid、gid、0600、regular、non-symlink 檢查；不留 temp residue。
- 執行指定測試、runtime manifest affected suite、`bash -n`、必要 `py_compile`、`git diff --check`。

## 交付

輸出 `pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/RESULT.md`，狀態為 `RE_REVIEW_REQUESTED`，不提交。

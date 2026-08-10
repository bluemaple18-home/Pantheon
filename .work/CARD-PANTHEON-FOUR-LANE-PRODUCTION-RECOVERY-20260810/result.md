---
id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260810
status: ready_for_re_review
type: result
repair_round: 1
parent_candidate: 995845b2c7a6abf3dc14f28fde7dd309b9812276
repair_commit: SELF
---

# Repair-1 結果

狀態：`READY_FOR_RE_REVIEW`

`repair_commit: SELF` 指含本結果檔的唯一原子修復 commit；commit 建立後以
`git rev-parse HEAD` 取得精確 SHA。其 parent 必須是
`995845b2c7a6abf3dc14f28fde7dd309b9812276`。

## P1 對照

| Finding / regression | 修復檔案 | Regression test |
| --- | --- | --- |
| `PANTHEON-RECOVERY-001` / `REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001` | `scripts/pantheon_content_actor_recovery.py` | `tests/test_pantheon_content_actor_recovery.py` |
| `PANTHEON-RECOVERY-002` / `REG-PANTHEON-CAPACITY-WRITE-CYCLES-001` | `scripts/pantheon_content_capacity_guard.py` | `tests/test_pantheon_content_capacity_guard.py::test_bounded_exercise_records_two_write_cycles_reclaims_and_stops` |
| `PANTHEON-RECOVERY-003` / `REG-PANTHEON-READINESS-CORRELATED-CHAIN-001` | `scripts/pantheon_content_capability_probe.py` | `tests/test_pantheon_content_capability_probe.py` |
| `PANTHEON-RECOVERY-004` / `REG-PANTHEON-FOUR-LANE-REJECT-NEW-ONLY-001` | `scripts/install_agy_content_publisher_launchd.sh`、`scripts/install_agy_gemini_coordinator_launchd.sh` | `tests/test_agy_content_publisher.py::test_publisher_installer_rejects_new_only_mode`、`tests/test_agy_gemini_coordinator.py::test_coordinator_installer_rejects_new_only_mode` |
| `PANTHEON-RECOVERY-005` / `REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001` | `scripts/pantheon_content_runtime_manifest.py`、三個 installer、四個 `com.pantheon.*` plist template | `tests/test_pantheon_content_runtime_manifest.py` |
| `PANTHEON-RECOVERY-006` / `REG-PANTHEON-CAPACITY-UNKNOWN-METRICS-NO-GO-001` | `scripts/pantheon_content_capacity_guard.py` | `tests/test_pantheon_content_capacity_guard.py::test_unknown_rss_or_swap_is_no_go` |
| `PANTHEON-RECOVERY-007` / `REG-PANTHEON-CAPACITY-STOP-VERIFICATION-001` | `scripts/pantheon_content_capacity_guard.py` | `tests/test_pantheon_content_capacity_guard.py::test_stop_services_requires_every_registered_label_to_be_absent` |
| `PANTHEON-RECOVERY-008` / `REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001` | `scripts/install_agy_gemini_coordinator_launchd.sh`、coordinator/lane plist template、runtime manifest barrier | `tests/test_agy_gemini_coordinator.py::test_activation_failure_rolls_back_plists_loaded_state_and_barrier` |

## 驗證

- 受影響測試：`.venv/bin/python -m pytest tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_pantheon_content_capacity_guard.py tests/test_pantheon_content_actor_recovery.py tests/test_pantheon_content_capability_probe.py tests/test_pantheon_content_runtime_manifest.py -q` → `212 passed, 1 warning in 25.65s`。
- Repository pytest：`.venv/bin/python -m pytest -q` → `950 passed, 2 warnings in 234.46s`。執行期間持續有輸出，未命中「超過 180 秒且無輸出」的中止條件。
- Shell / plist：三個 installer `bash -n` 與四個 plist template `plutil -lint` 全部通過。
- Diff gate：`git diff --check` 通過；沒有 debug marker 殘留。
- Capability 正向：`evidence/repair-1/capability-positive/receipt.json`，同一 execution/correlation 完成七步且逐步 I/O digest 連續。
- Capability 負向：`evidence/repair-1/capability-negative-{create,run,select,transaction,tag,push}/` 與 `evidence/repair-1/capability-negative/`；七個 fail step 均由同一正式入口產生並 fail closed。
- Readiness gate：`production_canary_readiness_gate.py` 對修復 receipt 回報 `READY`；此結論只代表 bounded synthetic/dry-run capability evidence 完整，`canary_created=false`，不代表 production READY。
- Capacity：`evidence/repair-1/capacity-exercise-v2.json` 記錄兩輪完整寫入、回收、逐 label stop 驗證與跨專案刪除檢查；synthetic exercise 為 `PASS`。正式 `capacity-safety-receipt.json` 保持 `NO-GO`，因未取得 production runtime 實測。

## 授權邊界與 residual risk

- 未建立或恢復 production actor；未執行 installer `--install`／`--activate`、`launchctl` mutation、真實 queue/provider 發文、production canary、transaction、tag、push、merge。
- Repair-1 關閉程式與 regression 契約，但 production 仍是 `NO-GO`：必須另經授權，在 exact commit 的 canonical clean actor 上重驗 origin、owner、runtime/dependency digest，並取得 production 容量兩週期、遙測與 stop-loss 證據。
- Synthetic capability chain 不替代 production control-plane 驗收；任何未知 RSS/swap、identity 缺失、任一 label 未證明 absent 或 bootstrap failure 都會 fail closed。

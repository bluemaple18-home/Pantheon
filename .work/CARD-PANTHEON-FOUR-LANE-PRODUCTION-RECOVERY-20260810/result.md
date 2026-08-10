---
id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260810
status: ready_for_final_re_review
type: result
repair_round: 2
parent_candidate: bf4a294da3229eba2d4bf4baf8f3c10d90267e6e
repair_commit: SELF
source_tree_digest: 14fe95fed7f3f984b230a89462136446ca0ebd1661630e538dbacef5355572e5
source_tree_digest_method: sha256(sorted("<git-blob-sha> <repo-relative-path>\\n") for the 17 changed source/template/test files)
---

# Repair-2 結果

狀態：`READY_FOR_FINAL_RE_REVIEW`

`repair_commit: SELF` 指含本檔與 Repair-2 evidence 的唯一原子 commit；final
回報提供精確 SHA。其 exact parent 是
`bf4a294da3229eba2d4bf4baf8f3c10d90267e6e`。

## 四個 OPEN 對照

| Finding / regression | 修復 | Regression evidence |
| --- | --- | --- |
| `PANTHEON-RECOVERY-001` / `REG-PANTHEON-ACTOR-RECOVERY-ENTRYPOINT-001` | Actor recovery private stage 掛接 canonical owner/digest 驗證的 Python/Node roots；在 `READY_TO_RESTORE`／`RESTORED` 前實測必要 imports、CLI 與三 installer preflight；通過後才 atomic replace | `tests/test_pantheon_content_actor_recovery.py::test_empty_target_restore_provisions_runtime_before_formal_preflights`、`::test_failed_runtime_preflight_leaves_no_half_ready_actor` |
| `PANTHEON-RECOVERY-003` / `REG-PANTHEON-READINESS-CORRELATED-CHAIN-001` | Probe 逐步以 subprocess 呼叫 `scripts.pantheon_content_capability_adapter` 正式 dry-run boundary；每步讀前一 artifact 並輸出下一 handoff；identity 綁 exact parent + source tree digest | `tests/test_pantheon_content_capability_probe.py`，含 always-fail adapter replacement |
| `PANTHEON-RECOVERY-005` / `REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001` | Runtime CLI `aggregate` 驗七份實際 stage/live plist 的 canonical realpath、owner、0600、label、manifest digest、identity 與四個 shared paths；coordinator 是唯一 activation caller；所有 runtime CLI 使用 external expected digest | `tests/test_pantheon_content_runtime_manifest.py::test_aggregate_gate_rejects_mixed_manifest_plists`、`tests/test_agy_gemini_coordinator.py::test_aggregate_activation_rejects_mixed_installer_manifest_before_mutation` |
| `PANTHEON-RECOVERY-008` / `REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001` | 三 installer stage 只寫 shared private stage；activation 才 snapshot/install live。Barrier 驗 activation digest、owner、0600、完整 JSON；rollback 逐 label 驗 control outcome、loaded/config state，任一失敗寫 `ROLLBACK_FAILED` | coordinator private-stage/rollback 動態 tests 與 `tests/test_pantheon_content_runtime_manifest.py::test_stale_or_malformed_activation_barrier_fails_closed` |

## 四個先前 CLOSED 回歸

- `REG-PANTHEON-CAPACITY-WRITE-CYCLES-001`
- `REG-PANTHEON-FOUR-LANE-REJECT-NEW-ONLY-001`
- `REG-PANTHEON-CAPACITY-UNKNOWN-METRICS-NO-GO-001`
- `REG-PANTHEON-CAPACITY-STOP-VERIFICATION-001`

上述五個具體 test node（new-only 含 publisher/coordinator 兩個）重跑：`5 passed in 0.43s`。

## 完整驗證

- Affected pytest：六個受影響 test files → `219 passed, 1 warning in 60.17s`。
- Repository pytest 首輪：`956 passed, 1 failed, 2 warnings in 263.75s`；唯一失敗為未修改的 broker timeout trace 測試。該 node 限域重跑 `1 passed in 0.57s`；修復內容穩定後的最終完整 repository 執行為 `957 passed, 2 warnings in 271.78s`。完整執行持續輸出，未命中「超過 180 秒且無輸出」中止條件。
- 三 installer `bash -n`、四 plist `plutil -lint`、`git diff --check` 與 debug marker gate 全綠。
- Readiness gate：`READY`，receipt execution line 為 `...-REPAIR-2`，`canary_created=false`；七步 artifact 均含實際 adapter command、return code 與 adapter receipt。
- Capacity gate：`evidence/repair-2/capacity-exercise.json` 為兩週期 `PASS`、回收與 stop-loss `STOPPED`；正式 `capacity-safety-receipt.json` 仍為 production `NO-GO`。

## Bounded evidence

- Positive chain：`evidence/repair-2/capability-verified-positive/receipt.json`。
- 每步 negative：`evidence/repair-2/capability-verified-negative-{create,run,select,publish,transaction,tag,push}/`。
- Identity：`parent:bf4a294da3229eba2d4bf4baf8f3c10d90267e6e;tree:14fe95fed7f3f984b230a89462136446ca0ebd1661630e538dbacef5355572e5`。
- Capacity：`evidence/repair-2/capacity-exercise.json`。

## Production 邊界與 residual risk

- 未執行 production actor restore、installer `--install`／`--activate`、launchctl mutation、真實 queue/provider、canary、transaction、tag、push 或 merge。
- `READY` 僅是 bounded production dry-run adapter readiness，不是 production `GO`。Production capacity 與 control-plane approval 仍缺，因此維持 `NO-GO`。
- 交由原 Reviewer 做 final re-review；本 Repair 實作者不宣稱 `REVIEW_GO`。

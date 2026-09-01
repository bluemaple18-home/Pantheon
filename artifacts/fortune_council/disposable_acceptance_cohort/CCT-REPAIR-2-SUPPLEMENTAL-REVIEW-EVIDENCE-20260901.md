---
id: PANTHEON-C-C-T-REPAIR-2-SUPPLEMENTAL-REVIEW-EVIDENCE
status: SUPPLEMENTAL_EVIDENCE_ONLY
date: 2026-09-01
---

# C-C/T Repair-2 supplemental review evidence

## Authority and boundary

- Code candidate：`4e68b28ed031bddafa898905880c68982944730b`
- Code parent：`b5d934dda7d32343fbf62ceff7f35869d9a20745`
- Code review range：`b5d934dda7d32343fbf62ceff7f35869d9a20745..4e68b28ed031bddafa898905880c68982944730b`
- 本文件是 `4e68b28...` 的 supplemental evidence child，不是 code candidate、Repair-3或 `C-C_T_REVIEW_GO`。
- 本文件不改 C-C/T source、tests或 candidate branch，也不增加／重置 Repair 額度；Repair budget維持 `2/2`。

## F-1：34 → 27 test migration

Repair-1 的 `34 passed` 與 Repair-2 的 `27 passed` 差異來自一個 parametrized test移除15個caller-receipt cases、改以4個raw-process cases取代，並新增4個standalone provenance regressions：`34 - 15 + 4 + 4 = 27`。不是遺漏7個獨立測試函式。

Repair-1 的 `test_runtime_receipt_regressions_cannot_pass` 允許 caller直接供應 final receipt mapping；Repair-2移除該 public callback seam後，原15個caller-receipt mutation cases不再是可呼叫介面。下表合併同類case列出替代覆蓋：

| Repair-1 retired case | 退場原因 | Repair-2 replacement coverage |
|---|---|---|
| `coordinator_cycle`: command移除 `--lane-mode` | caller不能再提供 Coordinator command／receipt | `test_formal_run_once_rejects_caller_supplied_owner_receipts_without_readback`；`test_rendered_cohort_binds_source_only_coordinator_lane_mode_and_dry_run_publisher`；private raw transport只能接收controller固定command |
| `coordinator_cycle`: terminal `active=1` | final mapping injection已不可達 | `test_runtime_receipt_regressions_cannot_pass[coordinator]`；`test_coordinator_terminal_stdout_without_run_state_readback_rejects` |
| `bootout`: 空 receipt | launch receipt callback已不可達 | `test_formal_run_once_rejects_caller_supplied_owner_receipts_without_readback`；`test_malformed_launch_receipt_still_boots_out_and_proves_final_absence` |
| `runner_once[new]`: `status=pending` | Runner final mapping injection已不可達 | `test_runtime_receipt_regressions_cannot_pass[runner]`；Runner bundle＋V4 ledger／anchor read-back仍由positive flow覆蓋 |
| `runner_once[i18n-new]`: `status=pending` | lane-specific caller mapping injection已不可達 | 同上；fixed schedule與actual bundle authority另由 `test_bundle_authority_required_entries_follow_actual_runner_schema` 覆蓋 |
| `materialize_translation`: forged `pending_digest_before` | C-B final mapping injection已不可達 | `test_runtime_receipt_regressions_cannot_pass[materialize]`；owner pending terminal read-back由positive flow覆蓋 |
| `bundle_close`: 截短 `delivered_entries` | bundle-close final mapping injection已不可達 | `test_runtime_receipt_regressions_cannot_pass[bundle-close]`；actual required entries由bundle authority test覆蓋 |
| `publisher_plan_only`: `ready_runs=[]` | caller不能再供應Publisher final mapping | `test_publisher_plan_only_rejects_wrong_owner_selector_or_extra_fields`；`test_positive_run_uses_real_publisher_owner_functions` |
| `publisher_plan_only`: selector多一筆／i18n receipt missing | caller不能再更換selector或省略owner result | lane-specific publisher schema tests；fixed single exact selector；real owner function spy |
| `drain_counts`: `pending=1` | caller drain-count callback已移除 | controller `_queue_drain_readback()`直接掃固定lane roots；positive flow要求pending／processing為0 |
| `launch`: generation drift；`print_service`: forged loaded；Publisher加入 `push`／`public_mutation` | launch／print／Publisher final mapping callbacks均移除 | formal injection TypeError；private raw process transport regressions；fixed Publisher `dry_run=True`、`push=False`與strict schema tests |

Repair-2新增的4個 provenance regressions：

1. `test_formal_run_once_rejects_caller_supplied_owner_receipts_without_readback`
2. `test_production_service_state_derives_from_plists_not_caller_env_or_self_digest`
3. `test_positive_run_uses_real_publisher_owner_functions`
4. `test_coordinator_terminal_stdout_without_run_state_readback_rejects`

因此test count下降代表受測public callback interface被刪除並以private raw transport／authoritative read-back測試取代，不是coverage靜默下降。

## F-2：launchctl authorization fuse

`scripts/pantheon_four_lane_disposable_acceptance_cohort.py::_run_process()` 對任何以 `/bin/launchctl` 開頭的command固定回傳return code `78`，不會呼叫`subprocess.run()`。

這是未授權保險絲，不是一般bug。其架構裁決如下：

- `4e68b28...` 是 launchctl-hard-disabled C-C/T review candidate。
- 即使取得 `C-C_T_REVIEW_GO`，`4e68b28...` 本身也不可直接執行真 Gate D/E。
- Gate D/E若需解除保險絲，必須另立 Owner-authorized activation-unlock card，產生新的exact actor並接受fresh review。
- activation-unlock不是Repair-3；只能改變launchctl允許條件，不得夾帶C-C/T邏輯修補。
- 後續worker不得把return code `78`短路當作bug順手刪除。
- 若治理契約改為要求`C-C_T_REVIEW_GO`的exact actor必須不改code即可執行Gate D/E，則目前狀態應回`BLOCKED_C_C_LAUNCHCTL_AUTHORIZATION_SEAM_REQUIRED`交Owner裁決，不得默示解除。

本輪未執行真實launchctl、provider、production/public mutation、Gate D/E、tag、deploy或merge。

## F-3：superseded branch lineage

`codex/pantheon-cc-t-disposable-cohort-20260901 @ aaad08e85cb18975e954c5d045141a8a7a418840` 的地位固定為：

- status：`SUPERSEDED_NONCANONICAL`
- purpose：early implementation-card branch
- not a candidate
- not a repair parent
- not a patch source
- must not be merged or cherry-picked

該branch暫不刪除；保留歷史reference不代表接受其lineage。

## Final external reviewer execution requirement

Final Independent Targeted Re-review必須由reviewer自行：

1. checkout `4e68b28ed031bddafa898905880c68982944730b` exact detached worktree；
2. 確認parent為`b5d934dda7d32343fbf62ceff7f35869d9a20745`；
3. 核對exact code diff allowlist；
4. 重跑focused Repair-2 tests；
5. 重跑affected Coordinator及runtime／Runner regressions；
6. 執行`py_compile`、`git diff --check`與`git status --short`；
7. 不得只採信committed RESULT／raw evidence。

只有真正external targeted re-review無P0/P1時，才能輸出`C-C_T_REVIEW_GO`。若再出現任何P0/P1，狀態為`BLOCKED_REVIEW_REPAIR_LIMIT`，停止且不得建立Repair-3。

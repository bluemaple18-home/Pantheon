---
id: PANTHEON-C-C-T-EXECUTABLE-COHORT-AUTHORITY-REPAIR
status: FREEZE_AUTHORIZED
type: implementation
---

# C-C/T executable cohort authority repair

## Objective

在不修改 shared runtime manifest、shared installer，且不新增 scheduler、runtime、FSM、ledger、registry 的前提下，讓 disposable seven-service cohort 依 immutable fixed schedule 完成 source、C-B materialization、translation、Publisher plan-only 與 deterministic teardown，並產生可供 Gate D/E 後續審查的 exact runtime receipts。

## Authority

- accepted parent：`836d5f0d1d62b58ad886aa37863c15ce41d233ec`
- rejected forensic input：`7821adb901d6c23059fecfd33e7b3de03fce8024`
- Owner implementation authorization：本次對話明示 `授權實作`
- Owner option：已選擇 option 2
- production activation：未授權
- commit／push：已明確授權；本 worker 未執行 commit/push
- Gate D/E：未授權
- candidate SHA／remote status：不由本 artifact 自證，須以外部 git 查詢 evidence 為準

## Allowed scope

- `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
- bounded seam：`scripts/agy_gemini_coordinator.py`
- bounded seam test：`tests/test_agy_gemini_coordinator.py`
- 本卡、同目錄 `RESULT.md` 與 exact raw test receipt

## Forbidden scope

- shared runtime manifest／schema、readiness ACK、activation barrier、installer
- Writer、Reviewer、Publisher、Runner、multilingual、C-A、C-B implementation
- production/public queue、ledger、registry、content、release、tag、deploy
- launchctl、provider、Gate D/E execution

## Acceptance

- failure／interruption 在首次 projection 前以 owner-safe `O_EXCL` consumed-generation authority 永久消耗 generation；同 generation 不可再 render 或 launch。
- externally pinned immutable plan 綁定 session、runtime、四 lane、dependency graph、C-B pins、bundle required entries、fixed schedule、Publisher exact plan-only selectors、zero-mutation budgets 與 teardown evidence contract。
- deterministic fake adapter 執行 source → materialization → translation → four bundle closes → four Publisher plan-only → drain → 7/7 absence；workload callbacks 必須吐 Coordinator/Runner/C-B/Publisher lane-specific owner-shaped native receipts，由 C-C/T validator normalize 後才可產生唯一 PASS。
- structured launchctl receipts 完整證明 initial 0/7、bootstrap、loaded identity、kickstart、bootout 與 final 7/7 absent；malformed launch receipt 若已證明 bootstrap side effect 仍必須 bootout 與 final print-not-found；callback `None` 或空 service mapping 不得作證。
- 覆蓋交接列出的 20 項 RED regression；執行 focused tests、受影響 Coordinator／runtime regressions、`py_compile` 與 `git diff --check`。
- final status 更新為 `FREEZE_AUTHORIZED`；commit/push 已獲 Owner 授權但未由本 worker 執行。不得 launchctl、provider、production/public mutation 或 Gate D/E。candidate SHA 與 remote branch/status 不由本 artifact 自證，必須以外部 git 查詢 evidence 為準。

## Context and measured gaps

- candidate worktree clean；remote candidate 與 local SHA 均為 `7821adb901d6c23059fecfd33e7b3de03fce8024`。
- candidate 初始 CodeGraph 未初始化；implementation turn 已以 bounded prepare 建立索引，`codegraph=ready`、`prepare_attempts=1`、indexed HEAD=`7821adb901d6c23059fecfd33e7b3de03fce8024`，working-tree 修補仍以 scoped source inspection 與 tests 作最終證據。
- rejected candidate 把 readiness convergence 當 workload completion，且 teardown 刪除 failure residue，使 generation 可重用。

## Verification plan

1. 先補 generation／plan／schedule／adapter RED tests，再逐一 minimal GREEN。
2. 跑完整 focused C-C/T 與 Coordinator seam tests，預期全部通過且不觸發真實 launchctl/provider。
3. 跑受影響 manifest／Runner regressions、`py_compile`、`git diff --check`，並將 exact node IDs 與輸出寫入 raw receipt。

## Evidence refs

- corrected repair result：`artifacts/fortune_council/disposable_acceptance_cohort/RESULT.md`
- raw corrected verification：`artifacts/fortune_council/disposable_acceptance_cohort/raw-test-output.txt`
- rejected external verdict：`C-C_T_REVIEW_NO_GO`
- R2 REVIEW_GO：`6897bb5d54a647b005b1422b207039f856ef232c`
- C-A REVIEW_GO：`1ea615ad4096077a2b82af86a2effb0c487c582d`
- C-B REVIEW_GO：`fa2e6cb65d5f57209fd3aebb3020246549ce2bc6`

## Corrected implementation summary

- 修復範圍停在 bounded C-C/T repair；未修改 shared runtime manifest/schema、installer、Coordinator、Publisher、Runner、multilingual、C-B、production/public/release/deploy。
- `scripts/pantheon_four_lane_disposable_acceptance_cohort.py` 現在於首次 projection 前以 `O_EXCL` 建立 durable consumed-generation marker，並在 render failure、partial readiness、teardown failure 後禁止同 generation retry。
- immutable session plan 綁定完整 session/runtime/workload/execution/budget/teardown/production fingerprint contract；run-time mutation boundary 前會重新驗證 plan digest。
- fixed schedule 明確分 source Coordinator selectors、每輪 Coordinator/Runner required-entry alternation、source terminal Coordinator receipts、C-B materialization pins、translation Coordinator selectors、translation required-entry alternation、translation terminal Coordinator receipts、Runner bundle close owner receipts、四次 lane-specific Publisher plan-only owner receipts 與 drain。
- bundle required entries 改讀 actual Runner sealed replay `entries[]` schema，僅採 `required=true` 的 `entry_id`；raw pinned bundle digest 與 sealed bundle body authority digest 分別綁定。
- C-B materialization receipt 依 existing owner schema 驗證：new `materialized` 接受 isolated queue `queue_mutation=True` / `public_mutation=False`；`already_materialized` 才接受 queue mutation false。
- Publisher plan-only receipt 依 lane 綁 owner schema：`new` 使用 `publish_ready_runs/published`、`rewrite` 使用 `publish_ready_rewrite_runs/rewritten`、`i18n-*` 使用 `publish_ready_translation_runs/translated`；不杜撰 owner receipt 中不存在的 `push/public_mutation` 欄位，zero mutation 由 dry-run command、plan budget 與 fingerprint unchanged 證明。
- launchctl evidence 改為 strict structured fake adapter receipt；callback `None`、空 service mapping、missing/extra fingerprint fields、wrong manifest/generation/plist identity、missing final print-not-found 都不能 PASS；malformed launch receipt failure path 仍納入 teardown target。

## Re-review record

- 第一個 Repair re-review：原 P1 findings 已關閉，無未解 P0/P1。
- replacement READ_ONLY re-review focused suite：`23 passed`。
- replacement re-review 後 exact-schema P1 已收斂：C-B queue mutation schema、Publisher lane-specific owner schema、malformed launch teardown、strict receipt keysets。
- 以上是主線 re-review evidence，不是 external `REVIEW_GO`。

## Corrected verification

- focused C-C/T tests：`34 passed`
- Coordinator affected seam tests：`7 passed`
- runtime manifest / sealed bundle regressions：`8 passed`
- `py_compile`：passed
- `git diff --check`：passed

## Exact test node IDs

- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_positive_fixed_schedule_reaches_one_pass_receipt`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_bundle_authority_required_entries_follow_actual_runner_schema`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_materialization_accepts_new_owner_receipt_with_isolated_queue_mutation`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_publisher_plan_only_accepts_lane_specific_owner_schema`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_publisher_plan_only_rejects_wrong_owner_selector_or_extra_fields`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_rendered_cohort_binds_source_only_coordinator_lane_mode_and_dry_run_publisher`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_failed_projection_consumes_generation_and_blocks_same_generation_retry`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_partial_readiness_consumes_generation_and_blocks_retry`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_teardown_failure_consumes_generation_and_blocks_retry`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_malformed_launch_receipt_still_boots_out_and_proves_final_absence`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_source_phase_rejects_i18n_exact_run_ids_before_launch`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_runtime_receipt_regressions_cannot_pass`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_callback_only_readiness_ack_cannot_pass`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_empty_or_extra_production_fingerprint_schema_rejects_before_bootstrap`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_plan_missing_or_drifting_fields_reject_before_projection`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_local_child_validator_rejects_missing_lane_mode_or_i18n_source_selector`

## Execution boundary record

- launchctl：`0`
- provider：`0`
- production/public/tag/push/deploy mutation：`0`
- Gate D/E：`NOT_RUN`
- commit：`FREEZE_AUTHORIZED`
- push：`FREEZE_AUTHORIZED`
- candidate SHA：`POST_FREEZE_GIT_EVIDENCE_REQUIRED`
- remote branch/status：`POST_FREEZE_GIT_EVIDENCE_REQUIRED`

## Source diff allowlist

- `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
- `artifacts/fortune_council/disposable_acceptance_cohort/CARD-PANTHEON-C-C-T-EXECUTABLE-COHORT-AUTHORITY-REPAIR-20260901.md`
- `artifacts/fortune_council/disposable_acceptance_cohort/RESULT.md`
- `artifacts/fortune_council/disposable_acceptance_cohort/raw-test-output.txt`

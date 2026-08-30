---
id: PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-ORDERING-RCA-20260829-REVIEWER-RESULT
card_id: CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-ORDERING-RCA-20260829
status: REVIEW_COMPLETE
verdict: GO
review_scope: artifact_only
---

# Publisher exact-run activation ordering RCA Reviewer RESULT

## Verdict

`GO`

無 P0/P1 finding。

本 reviewer 只讀指定 card 與同 RCA 目錄指定 artifacts，未讀 source/test，未碰 production，未 commit/push/install/activate。RCA 證據足以把唯一主因鎖為 `CAPACITY_VALIDATOR_OVERREACH`，並可開同一 bounded Repair frontier。

## Evidence reviewed

- `CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-ORDERING-RCA-20260829.md`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/RESULT.md`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/evidence-index.json`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/prerequisite-matrix.json`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/dag-and-history.json`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/verification-receipt.json`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/red-harness-run-1.json`
- `pantheon_publisher_exact_run_activation_ordering_rca_20260829/red-harness-run-2.json`

## Six-point ruling

1. Shared publisher / aggregate contract 是否允許 activation 前 exact-run selector 缺席：`YES`。
   - `RESULT.md` 指出 Publisher installer 在未指定 selector 時會刪除 stage receipt；shared `publisher_plist_preflight` 支援 `expected_exact_run_id` 與 `require_no_exact_run_id`。
   - `prerequisite-matrix.json` 的 aggregate activation 欄位明列 `publisher-exact-run-id.required=false`。

2. Capacity 是否單獨錯升為必填：`YES`。
   - `prerequisite-matrix.json` 對同一欄位標示 `required_by_shared_publisher_contract=false`、`required_by_capacity=true`。
   - `dag-and-history.json` 將 edge 4 `capacity --install-recovery-stage` 的 `run_id` 標為 `incorrectly required by private validator`。

3. Prerequisite matrix 是否證明為目前唯一缺口：`YES`。
   - matrix 中 Rule24、manifest digest/generation、barrier、model route、五份 coordinator/lane stage plist、publisher stage plist、`publisher-max-runs=1`、六份 coherent tuple、capacity candidate stage、old live cohort、stopped topology皆 PASS。
   - 唯一 RED 欄位是 `publisher-exact-run-id`。
   - counterfactual 只改一個輸入：加入合法 historical existing exact run 後，capacity 從 returncode `1` / 六份 stage 變成 returncode `0` / 七份 stage。

4. Last-good / first-bad 與 historical-run masking 是否成立：`YES`。
   - `dag-and-history.json` 鎖定 contract last-good parent `35cfdd52739f3e2896bf151ed6434a5e6d6ab95e`。
   - first bad mechanism 為 `29f758f6ad74afa412dd8ff3878efdd79074b36f`，效果是 capacity 開始無條件讀取並要求非空 `publisher-exact-run-id`。
   - last located successful production activation `g47-6477ab81-activation-only-20260826` 的後續 new run registration 發生在 activation 後，且能滿足 selector 是因為 pre-existing completed historical run `auto-i18n-en-614aa4dc3542ab2c5637`，支撐 historical-run masking 解釋。

5. RED/GREEN、雙跑與 immutable 證據是否足夠：`YES`。
   - 兩份 RED harness receipt byte-identical；verification receipt 記錄 SHA-256 `ee8a886285ee4321251e7b06fcd474c687c4f5a5ad01f56d0df4f2358dd59aa9` 與 canonical digest `bfca973b57dc5df53dfcc52560794b0a3cf609d0db2986eba27bc01e036acadb`。
   - `fresh_without_future_run`：formal order `coordinator --install → publisher --install → capacity --install-recovery-stage`，前兩步 PASS，capacity returncode `1`，edge `validate_preactivation_transition:publisher-exact-run-id`，stage 停在 6 份且 selector absent。
   - `historical_existing_run`：同 fixture 加合法 historical selector 後三步 PASS，stage 變 7 份。
   - `production_before` 與 `production_after` hashes identical；`production_bytes_unchanged=true`；verification receipt 記錄 production/live mutation `0`、external calls `0`。

6. 唯一根因能否鎖為 `CAPACITY_VALIDATOR_OVERREACH`：`YES`。
   - Evidence 同時閉合 shared contract optionality、capacity-only overrequirement、唯一 unmet prerequisite、last-good/first-bad、historical masking、fresh RED / historical GREEN、production immutable。
   - `CROSS_VERSION_STAGE_SCHEMA_GAP` 可保留為 secondary；不改變 primary root cause。

## Approved bounded Repair frontier

唯一可放行的 bounded Repair frontier：

- 只在 capacity validator 恢復 `publisher-exact-run-id` 的 optional-before-run contract。
- selector 缺席時可通過，但必須同時驗證 Publisher plist / stage 也沒有 exact selector，再繼續既有 manifest、barrier、stage/live tuple、Rule24、mode/recovery fail-closed checks。
- selector 存在時仍必須只沿用 shared publisher exact contract 精確驗證：stage receipt ↔ Publisher plist 一致，且保留既有格式／非空檢查；Capacity 不讀 run、queue 或 registry，不驗 run completion，不新增 authority。

禁止事項：

- preallocate run、placeholder run ID、猜 future run、手改 stage。
- 修改 scheduler、publisher installer、coordinator aggregate、promotion、manifest schema。
- 新增 FSM、registry、DB、authority ledger、migration。
- capacity-first bypass、per-lane/per-installer if/else 膨脹。
- production install/activate/provider/reviewer/publisher/scheduler mutation。

Required Repair tests：

- fresh/no-future-run：完整 `coordinator --install → publisher --install → capacity --install-recovery-stage` 應 GREEN，且缺席 selector 仍要求 Publisher plist / stage selector 同步缺席。
- historical existing-run：合法 selector path 維持 GREEN。
- stale selector、missing-one-side selector、mismatch selector、empty selector、malformed selector 仍 RED。
- Rule24、manifest digest/generation、barrier、model route、six/seven stage tuple、old-live cohort、stopped topology、normal/recovery mode drift 仍 fail closed。

## Mutation accounting

- source/test read by reviewer：0。
- source/test mutation：0。
- production/live mutation：0。
- install/activate/scheduler/provider/reviewer/publisher calls：0。
- commit/push/tag/deploy：0。

## Final

`GO`。可依上方 bounded Repair frontier 開同一 Repair；不得擴成 preallocation 或 control-plane 重設計。

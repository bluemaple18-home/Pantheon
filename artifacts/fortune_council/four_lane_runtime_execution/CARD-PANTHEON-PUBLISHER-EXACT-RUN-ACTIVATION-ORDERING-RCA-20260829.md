# CARD：Pantheon Publisher Exact-Run / Fresh-Run Activation Ordering RCA

- 卡號：`CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-ORDERING-RCA-20260829`
- 類型：read-only RCA
- 狀態：`RCA_COMPLETE`
- execution line：既有 `new` lane current production acceptance 的 serial control-plane failure

## Root Question

正式 service activation 為何在 fresh `new` run 建立前要求非空 `publisher-exact-run-id`，以及 durable contract 應採 optional post-activation binding 或正式 preallocation transaction？

## Locked Production Baseline

- live actor/manifest：promotion `COMMITTED` at `bde44589f3785aae738bb7d7b1626270ba5505d0`。
- Rule24 `PASS`；Rule25 `READY`。
- coordinator/publisher private stage 已寫；capacity `--install-recovery-stage` 以 `preactivation stage mismatch` fail closed。
- 七服務 `7/7 stopped`；lanes、registry、publisher ledger 與 live plists 未變。

## Required Evidence

1. 完整 activation prerequisite DAG；逐 edge 標示 owner、reads、writes、optional/required。
2. capacity 與 aggregate 的全部 stage 必填欄位矩陣，驗證 exact-run ID 是否為唯一缺口。
3. `publisher-exact-run-id` semantic owner 與合法生命週期。
4. fresh run activation ordering 與任何 provider=0 preallocation/registration seam。
5. last-good／first-bad receipt、commit、parent diff 與 blame。
6. task-owned temp roots 的 production-shaped deterministic RED，以及合法 existing exact-run historical path。
7. 唯一主因、secondary、durable invariant 與一次覆蓋完整 DAG 的 bounded Repair frontier。

## Hard Boundaries

- 不修改 source/test/live；不 install、activate、scheduler、provider、Reviewer、Publisher。
- 不 commit/push/tag/deploy，不開 Repair。
- 禁止 placeholder run ID、手改 stage、假 run、capacity-first bypass、啟動其他 lane。
- 不新增 registry、FSM、DB、ledger 或 migration。
- evidence 不足時只能 `RCA_INCOMPLETE`，不得猜測。

## Deliverable

- Evidence directory：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_ordering_rca_20260829/`
- Final receipt：上述目錄的 `RESULT.md`
- 最終必須明列唯一主裁決、last-good/first-bad、full prerequisite matrix、exact RED、minimum frontier、serial exposure 與 production mutation `0`。

## 終局

- 唯一主因：`CAPACITY_VALIDATOR_OVERREACH`。
- 結果：`RCA_COMPLETE`；未開 Repair，production mutation 與 external calls 均為 0。

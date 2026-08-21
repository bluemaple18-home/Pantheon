---
id: HANDOFF-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821
date: 2026-08-21
status: ready_for_handoff
baseline_branch: main
baseline_sha: 5887542f2cbc1c9bc3163044978aaafe6351f91c
---

# Pantheon G8 Release Transition Contract v1 換手卡

## Root Question

如何在不重寫 Publisher、coordinator、four content lanes 與內容自治邏輯的前提下，讓 G8 release control plane 只沿唯一合法 transition ordering 前進，並在碰 production 前由 read-only reconciliation 預測 phase mismatch、stale evidence 與 stage invalidation？

## Current Blocker

目前沒有新的 production blocker 被解除或驗證；本階段停在 design contract 已完成、implementation 尚未開始。

已知 production blocker仍是 Cycle 32：target 已 staged，但 orchestration 跳過正式 Publisher reset edge，直接進 Capacity preflight，造成 live Publisher `normal` 與 preactivation expected `activation-only` mismatch。

## Candidate Fork

唯一允許的下一分支是 G8 release control plane bounded implementation：read-only reconciler、現有 checks/transition effectors mapping、Capacity phase-aware no-PID semantics、orchestration ordering 與 focused/shadow tests。

若 implementation 需要重寫 content plane、新 daemon/database、第二套 state authority、放寬 fail-closed 或讓 Capacity/Rule 25 偷做 transition，立即回報 `SCOPE_VIOLATION / ARCHITECTURE_CONTRADICTION`，不得形成替代 fork。

## Goal

把已驗收的 Release State Contract v1 與 Transition Edge Map 落到最小 release control-plane implementation，先完成完全不 mutation production 的 dry reconciliation；只有所有 gates PASS 後，才回主線等待 bounded production canary 授權。

## Constraints & Preferences

- 文件、回報與自然語言使用繁中；程式碼保持既有語言。
- 不重寫 Publisher、coordinator、four lanes 或內容 business logic。
- 保留 manifest/generation/identity、private staging、receipts、rollback、Capacity resource policy、Rule 25 authorization、exact-run/canary mechanics。
- 不新增 daemon、database、scheduler 或通用 workflow engine。
- reconciler 必須純 read-only；不得 reset、install、activate、restage 或跑 canary。
- desired configuration、observed runtime、transition contract 三層 authority 不得互相覆蓋。
- reconciliation 不匹配任何唯一合法 state 時只能是 `DIVERGED`、`UNKNOWN` 或 `AMBIGUOUS`；不得猜 phase，也不得在沒有 execution artifact 時推論 `TRANSITIONING`。
- production canary 前必須停一次，回報完整 dry reconciliation 與所有 gate 狀態；不得繞過 `NO-GO`。
- 禁止 push、deploy、tag、launchctl/live plist mutation，除非後續得到明確授權並通過既有 Rule 24/25 gates。

## Completed Actions

1. 以 `49a747b77f58bb5d336aa2f43f1e192937f9bd54` 的 pre-canary diagnosis 為 evidence 起點建立實體設計卡：
   - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821.md`
2. 正式可見 thread `01a024c4-28cd-74b1-993e-54fe9bb2c025` 在獨立 worktree 完成三份 design artifact。
3. 主線驗收退回並修正兩個 P1：
   - normative matrix 原本混用自由文字，已改成 live/target-stage normalized typed rows、declared enums 與 `one_of(...)`。
   - `ST-QUIESCED-TARGET-STAGED` 原本誤把 Capacity target stage 視為已存在，已修正為 six-plist stage + Capacity absent；Capacity preflight/install 才產生第七 plist。
4. 已將 candidate 整合到 `main`：`5887542f2cbc1c9bc3163044978aaafe6351f91c`。
5. 未執行 production、canary、push、deploy、tag 或 launchctl mutation。

## Active State

- Branch：`main`
- Baseline SHA：`5887542f2cbc1c9bc3163044978aaafe6351f91c`
- Mainline tracked changes：本換手卡建立前為 clean。
- Repo 內原有若干 unrelated untracked artifacts/handoffs，屬使用者資料；不得刪除、stage 或覆寫。
- 沒有本任務啟動的 server、daemon 或 production process。
- 舊正式 design thread 保留可見、未封存；其 candidate SHA 為 `54e1d19556cb1adf154063aa775c00ace8b11479`，主線 cherry-pick 後 SHA 為上述 baseline。

## Evidence Authority

下一手必須先完整閱讀：

1. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
2. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
3. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md`
4. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821-RESULT.md`
5. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821.md`

禁止把 Cycle 31 readiness artifact 當成 current target evidence。

## Key Decisions & Resolved Questions

- 正式根因：`Runtime Transition Authority Fragmentation`。
- 採用最小 `Release Transition Contract Layer`，不是 mega state-machine engine。
- 合法主順序固定為：

```text
ST-CANARY-TERMINAL
  -> ST-TARGET-STAGED
  -> ST-QUIESCED-TARGET-STAGED
  -> ST-CAPACITY-READY
  -> ST-ACTIVATED
  -> ST-CANARY-READY
  -> ST-CANARY-RUNNING
  -> ST-CANARY-TERMINAL
```

- Publisher reset 必須在 target Publisher exact-run stage 存在後執行；`terminal -> reset -> stage` 非合法 edge。
- Activation-only loaded/no-PID 是合法 `INERT_LOADED`：`pid_required=false`、`measurement_required=false`、`expected_process_count=0`、`resource_usage=NOT_APPLICABLE`；出現 PID 才是 violation。
- Aggregate `--activate-only` 會刪除 private stage，因此 pre-activation Publisher exact-run receipt 必須失效，進 canary 前一定要 post-activation restage。
- Readiness 與 Rule 25 是 evidence/policy consumers，不是 mutation authority，也不得自行推論 phase。
- Content topology 維持 `new -> i18n-new` 與 `rewrite -> i18n-rewrite`；不得改成線性 new→rewrite→translate。
- Bounded canary success 不等於 steady autonomy committed；terminal→steady 是獨立授權 edge。

## In Progress / Remaining Work

下一手只開一張 bounded implementation 卡，依序完成：

1. 定義 read-only reconciler 的最小檔案/CLI/JSON interface，直接消費 Contract v1，不複製成第二套 enum truth。
2. 將現有 phase-sensitive checks 映射到 contract 欄位；policy-only checks 明確標示。
3. 實作 reconciler 的 `CONVERGED / DIVERGED / UNKNOWN / AMBIGUOUS` 與 divergences/next edge/evidence invalidation 輸出。
4. 修正 Capacity activation-only inert/no-PID sampler semantics；真正需要 RSS 的 phase 仍 fail closed。
5. 修正 orchestration ordering：stage → formal Publisher reset → Capacity preflight/install → activation → Publisher restage。
6. 新增 focused tests，並用 Cycle 29–32 evidence shadow replay 驗證兩個已知 blocker都能在 production 前被預測。
7. 跑 production-shaped、完全 read-only dry reconciliation。
8. 停止並回主線報告所有 gates；尚未授權 production canary。

## Waiting Conditions

開始 implementation 前必須同時確認：

- HEAD 等於或包含 baseline SHA。
- 三份 canonical design artifacts 可讀且 state/edge IDs 無漂移。
- worktree clean；unrelated untracked files不納入派工。
- CodeGraph readiness 已檢查；不可用時才限域使用 `rg`。
- 新 implementation 卡明列 ownership、可改檔案、禁止範圍、測試與停止條件。

正式 production canary 的等待條件：

- reconciler、Capacity semantics、ordering、focused tests、Cycle 29–32 replay、production-shaped dry reconciliation全部 PASS。
- Rule 24 Capacity 與 Rule 25 capability/authorization evidence current。
- 主線人工收到完整 gate matrix 後另行授權；不得自行推定。

## Blocked & Errors

- 目前無 implementation error；implementation 尚未開始。
- Cycle 32 歷史錯誤：`status=NO-GO`、`preactivation_transition=rejected`、`reason=plist activation mode mismatch`。
- 同期 raw evidence：`rss_available=false`、`rss_error=loaded_service_pid_missing:com.pantheon.agy-gemini-coordinator`；Contract v1 已判定此 phase 的 no-PID 是合法 inert semantics，但 production code 尚未修正。

## Acceptance for the Next Hand

下一手第一次回報只能確認：已讀本卡與五份 evidence、cwd/HEAD/clean/worktree/CodeGraph readiness、理解禁止事項與下一張 implementation 卡範圍。

未完成上述只讀 bootstrap 前，不得改 source、跑 mutation test、建立 production stage、啟動 canary或自行改 contract。

---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: implementation
cycle: 1
status: ready
type: bounded_contract_design
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
token_budget: 65000
model_reason: 核心 release transition contract 已收斂但影響跨 gate authority；規格固定、只做 bounded design artifacts，適用 GPT-5.5 high。
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md
  - artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md
  - artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md
forbidden_scope:
  - 修改任何 scripts、tests、config、plist、manifest、receipt schema 或 content plane code
  - 實作 reconciler、transition engine、daemon、database、scheduler 或新 workflow framework
  - production inspection、reset、install、activation、Capacity mutation、launchctl mutation、canary、deploy、tag 或 push
  - 放寬 fail-closed identity、digest、generation、Capacity 或 Rule 25 policy
  - 重寫 Publisher、coordinator、four lanes，或改新寫／改寫／翻譯 lineage
  - 建立 Reviewer、Repair、replacement thread 或其他工作卡
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/
---

# G8 Release Transition Contract Layer v1

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Release Transition Contract Layer v1 → 用既有 production failure evidence 定義 state contracts、transition edges 與 Cycle 29–32 replay → READY

## Root Question

在不改 content plane、不新增通用 engine、也不碰 production 的前提下，能否建立一份唯一且可驗證的 G8 release transition contract，使 Publisher reset、target staging、Capacity、activation、restage、readiness、Rule 25 與 canary 對同一 phase 使用相同語意，並能從既有 evidence 在 production 前預測 Cycle 32 與 activation-stage invalidation blocker？

## 基準與必讀 evidence

- source baseline：`49a747b77f58bb5d336aa2f43f1e192937f9bd54`。
- 完整閱讀：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821-RESULT.md`。
- 追讀 Cycle 29–32 cards/results、canonical TMPDIR repair、Cycle 31 readiness、Capacity Guard、preactivation transition、Rule 25、current readiness、Publisher activation-only contracts，以及 coordinator／four lanes／Publisher staged＋live plist authority。
- source confirmation 限於與上述契約直接相關的 bounded locations。先用 CodeGraph；無結果才限域 `rg`／必要片段。
- Cycle 31 readiness 只能作 historical replay evidence，不得冒充 current target evidence。

## 已確定的 architecture boundaries

正式根因名稱：`Runtime Transition Authority Fragmentation`。

本層只建立三項：

1. State contracts。
2. Transition edge contracts。
3. Evidence-bounded shadow reconciliation／replay specification。

Authority 必須分離：

- Desired configuration authority：runtime manifest、private stage、target generation、target exact-run selector。
- Observed runtime authority：live plist bytes、launchctl state、PID、barrier、actual live generation／identity。
- Transition definition authority：本卡定義的 state contract 與 allowed edge。
- Mutation authority：既有正式 scripts／installers，仍只是 effectors。
- Capacity Guard：resource policy authority，不擁有 Publisher transition。
- Rule 25：production authorization authority，不自行反推 phase。

State model 不得覆蓋 observed reality。Effector 或 receipt existence 均不得自行宣告 transition 成功。Transition 只有在以下全部成立時才可標成 `VERIFIED`：

```text
pre_snapshot matches from contract
+ allowed edge
+ effector receipt matches
+ post_snapshot matches to contract
+ required evidence present and current
+ declared invalidations verified
```

證據不足只能 `UNKNOWN` 並列出 missing fields；不得補猜。

## State Contract v1 要求

控制在約八個合法 states，預設候選：

1. `STEADY`
2. `CANARY_TERMINAL`
3. `TARGET_STAGED`
4. `QUIESCED_TARGET_STAGED`
5. `CAPACITY_READY`
6. `ACTIVATED`
7. `CANARY_READY`
8. `CANARY_RUNNING`

可依 evidence 極小幅調整，但禁止 phase explosion。Rollback 是 transition outcome，必須回到已知合法 state，不是永久 phase。

每個 state 必須同時表達兩個概念維度：

- `live_runtime_mode`
- `target_preparation_state`

v1 可保留 compound state ID，但 schema/table 必須分成 `live` 與 `target` 區段，避免 state 名稱持續膨脹。

每個 state 對 Publisher、coordinator、four lanes、Capacity Guard 至少定義：

- activation_mode
- plist_present
- loaded_expected
- pid_policy
- RunAtLoad
- StartInterval
- KeepAlive
- stage_policy
- child_policy
- generation_relation
- required_receipts

Observed reconciliation vocabulary 只允許：`CONVERGED`、`DIVERGED`、`UNKNOWN`、`AMBIGUOUS`。沒有 explicit transition execution artifact 時不得使用或推論 `TRANSITIONING`。

## Transition Edge Map v1 要求

Critical ordering 以 installer 真實 contract 為準：target stage 是 Publisher reset 的 proof context，故合法主路徑必須是：

```text
CANARY_TERMINAL
→ TARGET_STAGED
→ QUIESCED_TARGET_STAGED
→ CAPACITY_READY
→ ACTIVATED
→ CANARY_READY
→ CANARY_RUNNING
→ CANARY_TERMINAL 或經獨立授權回 STEADY
```

禁止改回 `terminal → reset → stage`。`--reset-publisher-activation-only` 必須在 target Publisher exact-run stage、manifest digest/generation、max-runs 與 exact selector proof 存在後才可執行。

每一條 edge 必須列：

- from／to state
- preconditions 與 required observed snapshot
- target intent／generation relation
- 唯一既有 effector／mutation authority
- expected mutations
- postconditions
- evidence produced
- evidence invalidated
- stage invalidated?
- restage required?
- crash／partial outcome classification
- rollback authority 與合法返回 state
- Capacity／readiness／Rule 25 在該 edge 的角色（contract field consumer 或 policy-only）

必須明確表達：`--activate-only` 替換 live plists 並刪除整個 private stage，因此所有 pre-activation private-stage evidence 與 Publisher exact-run staged receipt失效；進入 `CANARY_READY` 前必須重新 restage Publisher exact-run 並建立 current evidence。這件事不得靠 operator 記憶。

`CANARY_TERMINAL → STEADY` 是獨立 edge，需獨立 authorization；bounded canary 成功不得自動等同 steady autonomy committed。

## Content plane 不變量

控制面只能驗證既有合法 topology：

```text
new → i18n-new
rewrite → i18n-rewrite
```

不得改寫成 `new → rewrite → translate`。四 lanes 應在同一 campaign／generation／manifest 下各自完成合法 lineage；Publisher exact-run 仍只發布現行正式允許的一個 fresh `i18n-new` JA run。

## Cycle 29–32 Shadow Replay 要求

Replay 是本卡主要設計驗收，不是附錄。逐 Cycle 列出：

- evidence inventory（含來源 artifact／source contract）
- desired target
- observed live／staged facts
- 可匹配 state 與 reconciliation status
- attempted edge
- allowed／rejected／unknown
- missing／stale evidence
- exact blocker prediction
- next allowed edge

Evidence 完整才可判 `VERIFIED`／`REJECTED`；缺 evidence 固定 `UNKNOWN`。

Cycle 32 必須能在不碰 production 下指出：

- target stage 已存在；live Publisher 為 normal scheduled，其他六服務為 activation-only loaded/no-PID。
- 不得直接從 `TARGET_STAGED` 進 Capacity。
- 缺少的合法 edge 是 `TARGET_STAGED → QUIESCED_TARGET_STAGED`，由正式 `--reset-publisher-activation-only` 執行。
- Capacity 前 old-live 七服務必須匹配 activation-only inert contract。

Replay 亦必須預測 activation 會刪除 stage、讓舊 Publisher exact-run staged receipt失效，故 activation 後必須 restage 才能進 `CANARY_READY`。若模型無法預測上述兩點，本卡判定 `DESIGN_BLOCKED`。

Capacity loaded/no-PID 需在 contract 中表達為合法 inert process policy：`INERT_LOADED`、`pid_required=false`、`measurement_required=false`、`expected_process_count=0`、`resource_usage=NOT_APPLICABLE`；出現 PID 是 violation。這只是 contract mapping，本卡不得修改 Capacity code或放寬真正需 RSS 的 phase。

## 唯一交付

只新增以下三份 artifact，不新增 RESULT、測試、script 或其他檔案：

1. `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
2. `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
3. `PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md`

三份 artifact 必須互相以 stable IDs 交叉引用，並完整覆蓋以下 requirement IDs：

- `SC-01`：authority separation
- `SC-02`：state vocabulary與兩維 schema
- `SC-03`：七服務 contract fields
- `TE-01`：stage-before-reset ordering
- `TE-02`：edge authority與 verified success rule
- `TE-03`：activation invalidation與restage
- `TE-04`：bounded canary與steady autonomy分離
- `RP-01`：evidence-bounded Cycle 29–32 replay
- `RP-02`：Cycle 32 missing edge prediction
- `RP-03`：post-activation restage prediction
- `CP-01`：activation-only loaded/no-PID phase semantics
- `CT-01`：content topology不變

## 驗證與停損

- `git diff --check`。
- `git status --short` 只能出現上述三個 ownership files。
- 逐一驗證 requirement IDs 在三份 artifact 有明確 owner／cross-reference，沒有 dangling state／edge ID。
- 用 Cycle 29–32 committed evidence 回放；不得執行 production-shaped mutation或 live runtime probe。
- 不跑 release suite；本卡是 design-only，TDD 不適用。
- 發現需要重寫 content plane、新 daemon/database、大幅修改 Publisher/coordinator、放寬 fail-closed、或產生第二套 state authority時，立即停止並回 `SCOPE_VIOLATION / ARCHITECTURE_CONTRADICTION`。
- token 使用達 65,000 前必須停止；只回報已完成 artifacts、缺口與 `DESIGN_BLOCKED`，不得超額自行續跑。

## 交付契約

- 將三份 artifact 做成單一 atomic candidate commit；禁止 push。
- final 只回 `DESIGN_COMPLETE` 或 `DESIGN_BLOCKED`、完整 candidate SHA、三份檔案、驗證結果與 residual risks。
- 執行線只能交付 candidate；主線必須讀實際 artifacts、diff 與 replay evidence 後才能接受。

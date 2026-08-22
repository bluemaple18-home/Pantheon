---
id: PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821
card_id: CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821
status: candidate
version: 1
---

# G8 Release State Contract v1

## Contract Scope

本文件定義 G8 release control plane 可使用的唯一合法 state vocabulary。它只描述 state 與 evidence contract，不是 reconciler、daemon、scheduler 或 mutation engine。Transition authority 與 Cycle 29-32 replay 分別由 `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md` 與 `PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md` 擁有。

Requirement ownership：

| requirement | owner | cross-reference |
| --- | --- | --- |
| `SC-01` | 本文件：Authority Separation | `TE-02`、`RP-01` |
| `SC-02` | 本文件：State Vocabulary 與 Two-Dimensional Schema | `TE-01` |
| `SC-03` | 本文件：Service Contract Matrix | `TE-02` |
| `TE-01` | edge map | 本文件 state IDs |
| `TE-02` | edge map | 本文件 reconciliation vocabulary |
| `TE-03` | edge map | `ST-ACTIVATED`、`ST-CANARY-READY` |
| `TE-04` | edge map | `ST-CANARY-TERMINAL`、`ST-STEADY` |
| `RP-01` | replay | 本文件 state matching rules |
| `RP-02` | replay | `ST-TARGET-STAGED`、`ST-QUIESCED-TARGET-STAGED` |
| `RP-03` | replay | `ST-ACTIVATED`、`ST-CANARY-READY` |
| `CP-01` | 本文件：Activation-Only Inert Policy | edge map `TE-TARGET-STAGED-TO-QUIESCED` |
| `CT-01` | 本文件：Content Plane Invariant | replay evidence inventory |

## Authority Separation

`SC-01`：G8 release control plane 必須同時保留六種 authority，且不得互相冒充。

| authority | owns | cannot claim |
| --- | --- | --- |
| Desired configuration authority | runtime manifest、private stage、target generation、target exact-run selector | live runtime 已切換成功 |
| Observed runtime authority | live plist bytes、launchctl state、PID、barrier、actual live generation/identity | target desired state 合法 |
| Transition definition authority | 本文件 state contract 與 edge map allowed edge | production mutation 成功 |
| Mutation authority | 既有正式 installers 與 promotion primitive | 自行定義新 phase |
| Capacity Guard | resource policy 與 Capacity preactivation proof | Publisher transition 或 Rule 25 authorization |
| Rule 25 | production authorization policy | phase inference、plist transition 或 Capacity replacement |

State model 不覆蓋 observed reality。receipt 存在、effector exit 0 或 readiness 文案均不得自行宣告 state transition 成功；它們只是 transition evidence 的其中一欄。

## Reconciliation Vocabulary

`SC-02`：Observed reconciliation vocabulary 只允許：

| value | meaning |
| --- | --- |
| `CONVERGED` | required live/target evidence 與 state contract 全部一致 |
| `DIVERGED` | evidence 足以證明至少一個 required field 與 state contract 衝突 |
| `UNKNOWN` | 缺少 current evidence，不能補猜 |
| `AMBIGUOUS` | evidence 指向多個合法 state，或 current/historical evidence 混用 |

沒有 explicit transition execution artifact 時，不得使用或推論 `TRANSITIONING`。

## Two-Dimensional Schema

每個合法 state 必須拆成兩個維度，避免 state 名稱繼續膨脹：

```text
state_id
  live_runtime_mode
    publisher
    coordinator_and_four_lanes
    capacity_guard
  target_preparation_state
    private_stage
    target_generation
    publisher_exact_run
    capacity_stage
```

Service group IDs：

| service group | labels |
| --- | --- |
| `SVC-PUBLISHER` | `com.pantheon.agy-content-publisher` |
| `SVC-CORE` | `com.pantheon.agy-gemini-coordinator`、`com.pantheon.agy-gemini-new`、`com.pantheon.agy-gemini-rewrite`、`com.pantheon.agy-gemini-i18n-new`、`com.pantheon.agy-gemini-i18n-rewrite` |
| `SVC-CAPACITY` | `com.pantheon.content-capacity-guard` |

Typed predicate semantics：

| predicate | deterministic semantics |
| --- | --- |
| `one_of(a,b,...)` | evidence value must equal exactly one listed enum token; if evidence is missing, reconciliation is `UNKNOWN`; if evidence value is outside the list, reconciliation is `DIVERGED` |
| `all_labels_match` | for `SVC-CORE`, expand deterministically to the five labels listed above; every label must independently satisfy the same row, and any label mismatch makes the whole state `DIVERGED` |

`SVC-CORE` is never a lossy aggregate. A reconciler must expand it to:

```text
com.pantheon.agy-gemini-coordinator
com.pantheon.agy-gemini-new
com.pantheon.agy-gemini-rewrite
com.pantheon.agy-gemini-i18n-new
com.pantheon.agy-gemini-i18n-rewrite
```

Universal contract fields and allowed normative values：

| field | allowed values |
| --- | --- |
| `scope` | `live`、`target_stage` |
| `activation_mode` | `normal`、`activation-only`、`not_present`、`not_applicable` |
| `plist_present` | `live`、`stage`、`live_and_stage`、`absent` |
| `loaded_expected` | `loaded`、`not_loaded`、`not_required` |
| `pid_policy` | `INERT_LOADED`、`NO_PID`、`TRANSIENT_EXACT_RUN_PID`、`NOT_APPLICABLE`、`VIOLATION_IF_PID` |
| `RunAtLoad` | `true`、`false`、`not_applicable` |
| `StartInterval` | `60`、`300`、`absent`、`not_applicable` |
| `KeepAlive` | `absent`、`not_applicable` |
| `stage_policy` | `target_absent`、`target_six_plist`、`target_seven_plist`、`target_publisher_exact_run`、`target_capacity_candidate`、`target_invalidated_by_activation`、`target_consumed`、`not_applicable` |
| `child_policy` | `forbidden`、`normal_production`、`publisher_exact_run_only`、`not_applicable` |
| `generation_relation` | `old_live`、`target_same_generation`、`target_newer_than_live`、`live_equals_target`、`historical_only`、`unknown` |
| `required_receipt_set` | `RR-STEADY-LIVE`、`RR-TERMINAL-PUBLISHER`、`RR-LIVE-AO`、`RR-TARGET-STAGE`、`RR-PUBLISHER-EXACT-STAGE`、`RR-PUBLISHER-RESET`、`RR-CAPACITY-PREFLIGHT`、`RR-CAPACITY-STAGE`、`RR-ACTIVATION`、`RR-POST-ACTIVATION-RESTAGE`、`RR-CANARY-READY`、`RR-CANARY-RUNNING`、`RR-NONE` |

Any matrix cell must be either a declared enum token or a typed `one_of(...)` predicate whose members are declared enum tokens for that field. Natural-language scalar values are non-normative and invalid in the matrix.

Receipt set IDs：

| receipt set | deterministic contents |
| --- | --- |
| `RR-STEADY-LIVE` | live plist receipt, launchctl snapshot, explicit steady authorization |
| `RR-TERMINAL-PUBLISHER` | Publisher terminal receipt or bounded canary failure/recovery terminal evidence |
| `RR-LIVE-AO` | live plist receipt with `activation-only`, launchctl loaded/no-PID snapshot |
| `RR-TARGET-STAGE` | target manifest, generation, staged plist receipt for each expanded label |
| `RR-PUBLISHER-EXACT-STAGE` | staged Publisher receipt, `publisher-exact-run-id`, `publisher-max-runs=1` |
| `RR-PUBLISHER-RESET` | formal reset receipt, post-reset Publisher live receipt, unchanged other-service proof |
| `RR-CAPACITY-PREFLIGHT` | Capacity public preflight receipt and preactivation input receipts |
| `RR-CAPACITY-STAGE` | Capacity install receipt and staged Capacity plist receipt |
| `RR-ACTIVATION` | aggregate activation receipt, live aggregate receipt, barrier receipt |
| `RR-POST-ACTIVATION-RESTAGE` | post-activation Publisher restage receipt |
| `RR-CANARY-READY` | post-activation Publisher restage receipt, current readiness summary, capability receipt, Rule 25 receipt, negative fixture |
| `RR-CANARY-RUNNING` | Publisher-only activation receipt, exact-run child receipt, transaction evidence |
| `RR-NONE` | no receipt required for absent target scope; evidence absence itself must still be observed |

## Legal State Vocabulary

`SC-02`：v1 有且只有以下八個合法 state。Rollback 不是 state；rollback 是 edge outcome，必須回到其中一個合法 state。

| state_id | live_runtime_mode | target_preparation_state | reconciliation rule |
| --- | --- | --- | --- |
| `ST-STEADY` | 七服務為 normal production autonomy；Publisher 可 scheduled；core lanes 可依正式 schedule 工作 | no current canary target stage required | current production autonomy evidence 必須存在；bounded canary success 不會自動成為 steady |
| `ST-CANARY-TERMINAL` | Publisher terminal normal one-shot 或 legacy normal scheduled；其他六服務維持 activation-only loaded/no-PID | exact run 與 failure/recovery evidence 可存在；target stage 不具 current authorization | Publisher normal 與其他六 activation-only 同時存在時匹配；這是 Cycle 30 後 terminal mixed cohort |
| `ST-TARGET-STAGED` | old live 可仍為 terminal mixed cohort | target generation 已 promote/stage；coordinator、four lanes、Publisher exact-run stage 存在；Capacity stage 可缺 | stage proof 不代表 old live quiesced；不得直接進 Capacity |
| `ST-QUIESCED-TARGET-STAGED` | old live 七服務全部 activation-only、loaded/no-PID；Publisher reset receipt current | target stage 仍存在且 Publisher exact-run/max-runs proof current | stage-before-reset 已完成後匹配；Capacity 可消費此 state |
| `ST-CAPACITY-READY` | old live 七服務仍 activation-only loaded/no-PID | target seven-plist stage coherent；Capacity preflight accepted/PASS；Capacity plist 已 stage | Capacity 已成 resource policy proof，不等於 Rule 25 authorization |
| `ST-ACTIVATED` | target generation 七服務 live activation-only、loaded/no-PID；barrier current | private stage 已由 aggregate `--activate-only` 刪除，因此 pre-activation stage evidence invalid | activation success 後匹配；Publisher exact-run stage 必須視為 stale |
| `ST-CANARY-READY` | target generation live activation-only、loaded/no-PID | activation 後重建 Publisher exact-run stage；current readiness/Rule 25/capability evidence present | 可執行 Publisher-only canary 的唯一前態 |
| `ST-CANARY-RUNNING` | Publisher normal one-shot exact-run 允許 transient PID；其他六服務 activation-only loaded/no-PID | Publisher stage 已被 Publisher-only activation 消費；transaction/tag/push chain 正在 bounded window | 只有 explicit Publisher-only activation artifact 可匹配 |

## Service Contract Matrix

`SC-03`：下表是 normalized deterministic matrix。`scope=live` 描述 observed live reality；`scope=target_stage` 描述 target/private-stage reality。兩者不得混在同一 scalar 欄。缺 current evidence 固定 `UNKNOWN`；任何 label mismatch 固定 `DIVERGED`。

| state_id | service_group | scope | activation_mode | plist_present | loaded_expected | pid_policy | RunAtLoad | StartInterval | KeepAlive | stage_policy | child_policy | generation_relation | required_receipt_set |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ST-STEADY` | `SVC-PUBLISHER` | live | normal | live | one_of(loaded,not_loaded) | NO_PID | true | one_of(60,absent) | absent | not_applicable | normal_production | live_equals_target | RR-STEADY-LIVE |
| `ST-STEADY` | `SVC-CORE` | live | normal | live | loaded | NO_PID | true | 60 | absent | not_applicable | normal_production | live_equals_target | RR-STEADY-LIVE |
| `ST-STEADY` | `SVC-CAPACITY` | live | normal | live | loaded | NO_PID | true | 300 | absent | not_applicable | normal_production | live_equals_target | RR-STEADY-LIVE |
| `ST-STEADY` | `SVC-PUBLISHER` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | live_equals_target | RR-NONE |
| `ST-STEADY` | `SVC-CORE` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | live_equals_target | RR-NONE |
| `ST-STEADY` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | live_equals_target | RR-NONE |
| `ST-CANARY-TERMINAL` | `SVC-PUBLISHER` | live | normal | live | one_of(loaded,not_loaded) | NO_PID | true | one_of(60,absent) | absent | not_applicable | forbidden | old_live | RR-TERMINAL-PUBLISHER |
| `ST-CANARY-TERMINAL` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-CANARY-TERMINAL` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-CANARY-TERMINAL` | `SVC-PUBLISHER` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | unknown | RR-NONE |
| `ST-CANARY-TERMINAL` | `SVC-CORE` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | unknown | RR-NONE |
| `ST-CANARY-TERMINAL` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | unknown | RR-NONE |
| `ST-TARGET-STAGED` | `SVC-PUBLISHER` | live | normal | live | one_of(loaded,not_loaded) | NO_PID | true | one_of(60,absent) | absent | not_applicable | forbidden | old_live | RR-TERMINAL-PUBLISHER |
| `ST-TARGET-STAGED` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-TARGET-STAGED` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-TARGET-STAGED` | `SVC-PUBLISHER` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_publisher_exact_run | forbidden | target_newer_than_live | RR-PUBLISHER-EXACT-STAGE |
| `ST-TARGET-STAGED` | `SVC-CORE` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_six_plist | forbidden | target_newer_than_live | RR-TARGET-STAGE |
| `ST-TARGET-STAGED` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | target_newer_than_live | RR-NONE |
| `ST-QUIESCED-TARGET-STAGED` | `SVC-PUBLISHER` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | old_live | RR-PUBLISHER-RESET |
| `ST-QUIESCED-TARGET-STAGED` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-QUIESCED-TARGET-STAGED` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-QUIESCED-TARGET-STAGED` | `SVC-PUBLISHER` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_publisher_exact_run | forbidden | target_newer_than_live | RR-PUBLISHER-EXACT-STAGE |
| `ST-QUIESCED-TARGET-STAGED` | `SVC-CORE` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_six_plist | forbidden | target_newer_than_live | RR-TARGET-STAGE |
| `ST-QUIESCED-TARGET-STAGED` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | target_newer_than_live | RR-NONE |
| `ST-CAPACITY-READY` | `SVC-PUBLISHER` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-CAPACITY-READY` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-CAPACITY-READY` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | old_live | RR-LIVE-AO |
| `ST-CAPACITY-READY` | `SVC-PUBLISHER` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_publisher_exact_run | forbidden | target_newer_than_live | RR-PUBLISHER-EXACT-STAGE |
| `ST-CAPACITY-READY` | `SVC-CORE` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_seven_plist | forbidden | target_newer_than_live | RR-TARGET-STAGE |
| `ST-CAPACITY-READY` | `SVC-CAPACITY` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 300 | absent | target_seven_plist | forbidden | target_newer_than_live | RR-CAPACITY-STAGE |
| `ST-ACTIVATED` | `SVC-PUBLISHER` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | live_equals_target | RR-ACTIVATION |
| `ST-ACTIVATED` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | live_equals_target | RR-ACTIVATION |
| `ST-ACTIVATED` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | live_equals_target | RR-ACTIVATION |
| `ST-ACTIVATED` | `SVC-PUBLISHER` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_invalidated_by_activation | not_applicable | live_equals_target | RR-ACTIVATION |
| `ST-ACTIVATED` | `SVC-CORE` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_invalidated_by_activation | not_applicable | live_equals_target | RR-ACTIVATION |
| `ST-ACTIVATED` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_invalidated_by_activation | not_applicable | live_equals_target | RR-ACTIVATION |
| `ST-CANARY-READY` | `SVC-PUBLISHER` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | live_equals_target | RR-LIVE-AO |
| `ST-CANARY-READY` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | live_equals_target | RR-LIVE-AO |
| `ST-CANARY-READY` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | live_equals_target | RR-LIVE-AO |
| `ST-CANARY-READY` | `SVC-PUBLISHER` | target_stage | normal | stage | not_loaded | NOT_APPLICABLE | true | 60 | absent | target_publisher_exact_run | forbidden | live_equals_target | RR-CANARY-READY |
| `ST-CANARY-READY` | `SVC-CORE` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | live_equals_target | RR-CANARY-READY |
| `ST-CANARY-READY` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_absent | not_applicable | live_equals_target | RR-CANARY-READY |
| `ST-CANARY-RUNNING` | `SVC-PUBLISHER` | live | normal | live | loaded | TRANSIENT_EXACT_RUN_PID | true | one_of(absent,60) | absent | target_consumed | publisher_exact_run_only | live_equals_target | RR-CANARY-RUNNING |
| `ST-CANARY-RUNNING` | `SVC-CORE` | live | activation-only | live | loaded | INERT_LOADED | true | 60 | absent | not_applicable | forbidden | live_equals_target | RR-LIVE-AO |
| `ST-CANARY-RUNNING` | `SVC-CAPACITY` | live | activation-only | live | loaded | INERT_LOADED | true | 300 | absent | not_applicable | forbidden | live_equals_target | RR-LIVE-AO |
| `ST-CANARY-RUNNING` | `SVC-PUBLISHER` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_consumed | not_applicable | live_equals_target | RR-CANARY-RUNNING |
| `ST-CANARY-RUNNING` | `SVC-CORE` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_consumed | not_applicable | live_equals_target | RR-CANARY-RUNNING |
| `ST-CANARY-RUNNING` | `SVC-CAPACITY` | target_stage | not_present | absent | not_required | NOT_APPLICABLE | not_applicable | not_applicable | not_applicable | target_consumed | not_applicable | live_equals_target | RR-CANARY-RUNNING |

## Deterministic Matrix Validation

The normative matrix is valid only if a read-only checker can prove all of the following:

1. Every `state_id` is one of the eight legal state IDs.
2. Every `service_group` is one of `SVC-PUBLISHER`, `SVC-CORE`, or `SVC-CAPACITY`.
3. Every non-receipt cell is either a declared enum token for that column or `one_of(...)` whose members are declared enum tokens for that same column.
4. Every `required_receipt_set` is one declared receipt set ID.
5. Every legal state has at least one deterministic `live` row for each service group.
6. `SVC-CORE` rows are expanded to five labels before comparison; any single-label mismatch makes the state `DIVERGED`.

## Activation-Only Inert Policy

`CP-01`：Activation-only loaded/no-PID 是合法 inert process policy，不是 telemetry failure。

Normative mapping：

```text
topology = INERT_LOADED
pid_required = false
measurement_required = false
expected_process_count = 0
resource_usage = NOT_APPLICABLE
pid_present = violation
```

Activation-only inert terminal exit 的唯一合法集合為 `absent`、`0`、`78`。其中 `78` 只可代表 activation wrapper／barrier validation 在 production workload child 啟動前 fail-closed；它只在下列條件全部成立時合法：

1. transition 是 `TE-TARGET-STAGED-TO-QUIESCED`，live service 仍為 `old_live + activation-only`，target stage 為 current 且 generation 明確 newer than live；
2. current live plist receipt、`RR-PUBLISHER-RESET`／`RR-LIVE-AO` 與 target-stage receipts 全部存在且一致；
3. launchctl identity 為 loaded、`not running` 或 `waiting`、no-PID，且 observed plist path 精確等於該 label 的 live plist path；
4. `78` 來自 old expected digest 對 promoted shared manifest mismatch 的 wrapper validation，沒有 production workload child、child I/O 或 retry 被執行。

任一條件缺失時固定為 `UNKNOWN`；任一條件衝突、任意其他 nonzero exit、PID 存在、path drift、normal mode 或 target generation 非 newer 時固定為 `DIVERGED`。`child_policy=forbidden` 禁止的是 production workload child；activation wrapper／barrier 在 child spawn 前執行的 validation 不屬於 production workload child，因此不與合法 inert terminal `78` 矛盾。

此 mapping 只定義 contract 語意，不修改 Capacity code，也不放寬真正需要 RSS 的 phase。若 raw Capacity sampler 在 activation-only inert phase 回 `loaded_service_pid_missing:<label>`，state reconciliation 應標記為 contract split evidence，而不是把合法 no-PID 服務當成 running process 缺失。

## Content Plane Invariant

`CT-01`：Release transition contract 不改 content plane topology。控制面只能驗證既有合法 lineage：

```text
new -> i18n-new
rewrite -> i18n-rewrite
```

四 lanes 必須在同一 campaign/generation/manifest 下各自完成合法 lineage。Publisher exact-run 仍只發布現行正式允許的一個 fresh `i18n-new` JA run。任何把內容流程改寫成 `new -> rewrite -> translate` 的 state 或 edge 均為 `SCOPE_VIOLATION`。

## State Matching Rule

State 可標成 `CONVERGED` 只有在下列條件全部成立：

```text
current observed live snapshot matches live_runtime_mode
+ current target/stage snapshot matches target_preparation_state
+ required receipts are present and current
+ historical evidence is not used as current target evidence
```

缺 evidence 固定 `UNKNOWN`；evidence 足以證明 mismatch 固定 `DIVERGED`；同時符合多個 state 或混用歷史/現況 evidence 固定 `AMBIGUOUS`。

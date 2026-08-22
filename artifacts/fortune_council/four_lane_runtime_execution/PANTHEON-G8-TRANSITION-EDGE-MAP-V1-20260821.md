---
id: PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821
card_id: CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821
status: candidate
version: 1
---

# G8 Transition Edge Map v1

## Contract Scope

本文件定義 G8 release control plane 的合法 transition edges。State vocabulary 由 `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md` 擁有；Cycle 29-32 evidence replay 由 `PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md` 擁有。本文件不新增 effector、不執行 production，也不取代既有 installers。

Requirement ownership：

| requirement | owner | cross-reference |
| --- | --- | --- |
| `SC-01` | state contract | edge authority 欄位保留 authority separation |
| `SC-02` | state contract | all edges use `ST-*` IDs |
| `SC-03` | state contract | pre/post snapshots consume service fields |
| `TE-01` | 本文件：Allowed Main Path |
| `TE-02` | 本文件：Verified Success Rule 與 Edge Table |
| `TE-03` | 本文件：Activation Invalidation Edge |
| `TE-04` | 本文件：Canary Terminal vs Steady Edge |
| `RP-01` | replay | edge IDs used by Cycle 29-32 |
| `RP-02` | replay | `TE-TARGET-STAGED-TO-QUIESCED` |
| `RP-03` | replay | `TE-ACTIVATED-TO-CANARY-READY` |
| `CP-01` | state contract | consumed by Capacity edges |
| `CT-01` | state contract | preserved as all-edge invariant |

## Verified Success Rule

`TE-02`：任何 transition 只有在以下全部成立時才可標成 `VERIFIED`：

```text
pre_snapshot matches from contract
+ allowed edge
+ effector receipt matches the unique mutation authority
+ post_snapshot matches to contract
+ required evidence present and current
+ declared invalidations verified
```

任一欄缺失時只能是 `UNKNOWN`；任一欄明確衝突時是 `REJECTED`。Mutation authority 的 exit 0、stage receipt 或 Rule 25 READY 不得單獨證明 transition 成功。

## Allowed Main Path

`TE-01`：合法主路徑固定如下，不能回到 `terminal -> reset -> stage`。

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

`ST-CANARY-TERMINAL -> ST-STEADY` 是獨立、另需授權的 edge；bounded canary success 不會自動把 system 轉成 steady autonomy。

## Edge Table

| edge_id | from | to | unique mutation authority | required pre_snapshot | target intent / generation relation | expected mutations | postconditions | evidence produced | evidence invalidated | stage invalidated? | restage required? | crash / partial outcome | rollback authority / legal return | Capacity role | readiness / Rule 25 role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TE-CANARY-TERMINAL-TO-TARGET-STAGED` | `ST-CANARY-TERMINAL` | `ST-TARGET-STAGED` | runtime promotion primitive plus existing coordinator/four-lane installer and Publisher stage installer | terminal mixed live cohort; exact run still unique; actor/manifest rollback snapshot | target generation newer than old live; Publisher exact-run `max-runs=1` | promote target actor/manifest; write coordinator/four-lane staged plists; write Publisher exact-run staged plist | six target plists exist; Publisher exact-run proof current; Capacity stage may be absent | promotion plan/apply receipt, stage controls, staged aggregate receipt, Publisher exact-run receipt | old target-stage receipts for previous generation | no | no, because this edge creates stage | source promotion failure or partial stage failure yields rollback to `ST-CANARY-TERMINAL` or `UNKNOWN` if rollback evidence missing | promotion rollback bundle; installer rollback; legal return `ST-CANARY-TERMINAL` | policy-only; cannot preflight until quiesced | not authorized; historical readiness cannot fill current target |
| `TE-TARGET-STAGED-TO-QUIESCED` | `ST-TARGET-STAGED` | `ST-QUIESCED-TARGET-STAGED` | `scripts/install_agy_gemini_coordinator_launchd.sh --reset-publisher-activation-only` | matching target stage, Publisher exact-run/max-runs receipt, live Publisher normal terminal/scheduled, other six activation-only loaded/no-PID | old live stays old generation; target stage remains newer/current | replace live Publisher plist with activation-only version; bootout/bootstrap Publisher only if needed; other six unchanged | all seven old-live services activation-only loaded/no-PID at exact live plist paths; target stage still present/current; inert terminal exit is absent, `0`, or conditionally `78` | Publisher reset receipt, post-reset Publisher live receipt, launchctl post identity, other-six unchanged proof | previous live Publisher normal terminal state | no | no | running Publisher PID, identity/path drift, any nonzero exit other than conditionally legal `78`, stage mismatch or temp receipt failure rejects before mutation or rolls back to `ST-TARGET-STAGED` | reset rollback trap; legal return `ST-TARGET-STAGED` or `ST-CANARY-TERMINAL` if stage lost and terminal evidence remains | Capacity consumes this as required old-live AO/no-PID proof | readiness/Rule 25 still policy-only |
| `TE-QUIESCED-TO-CAPACITY` | `ST-QUIESCED-TARGET-STAGED` | `ST-CAPACITY-READY` | `scripts/install_pantheon_content_capacity_guard_launchd.sh --preflight` then `--install` | old live seven activation-only loaded/no-PID; target stage has coordinator/four-lane plists plus Publisher exact-run; Capacity target plist absent | target generation newer than old live | Capacity public preflight creates/validates candidate; Capacity installer writes seventh target plist | seven-plist target stage coherent; Capacity receipt PASS/current | Capacity preflight receipt, Capacity staged plist receipt, seven-stage tree digest | previous six-plist-only stage inventory | no | no | raw RSS unknown for inert AO should be classified by contract; transition reject leaves `ST-QUIESCED-TARGET-STAGED` with Capacity target absent | Capacity installer no-mutation preflight or rollback; legal return `ST-QUIESCED-TARGET-STAGED` | contract field consumer and resource policy authority | cannot authorize production alone |
| `TE-CAPACITY-TO-ACTIVATED` | `ST-CAPACITY-READY` | `ST-ACTIVATED` | `scripts/install_agy_gemini_coordinator_launchd.sh --activate-only` | seven target plists current; Capacity PASS; old live AO/no-PID; stage controls match target | target replaces live; live generation becomes target | replace seven live plists with target; add activation-only; bootout/bootstrap all seven; activate barrier; delete private stage | target seven live activation-only loaded/no-PID; barrier current; stage absent | aggregate activation receipt, live aggregate receipt, launchctl snapshots, barrier receipt | all pre-activation private-stage receipts, including Publisher exact-run staged receipt | yes | yes, before canary | partial bootstrap or validation failure must rollback to `ST-CAPACITY-READY` if stage restored; otherwise `UNKNOWN` | aggregate activation rollback; legal return `ST-CAPACITY-READY` or `UNKNOWN` | Capacity proof consumed, not owner of live transition | Rule 25 evidence before activation is stale for post-activation canary |
| `TE-ACTIVATED-TO-CANARY-READY` | `ST-ACTIVATED` | `ST-CANARY-READY` | existing Publisher stage installer | target live seven activation-only loaded/no-PID; private stage absent because activation consumed it | same target generation as live | restage Publisher exact-run only as current target evidence | post-activation Publisher exact-run stage current; Rule 25 authorization current; no child I/O | Publisher restage receipt, current readiness summary, capability receipt, Rule 25 receipt, negative fixture | pre-activation Publisher staged receipt remains invalid | no for new stage | no after this edge | stale stage reuse or missing current Rule 25 yields `UNKNOWN`/`REJECTED`; no production child permitted | Publisher stage removal only; legal return `ST-ACTIVATED` | Capacity proof is input; no new Capacity mutation | readiness and Rule 25 are evidence/policy consumers only, not mutation authority |
| `TE-CANARY-READY-TO-RUNNING` | `ST-CANARY-READY` | `ST-CANARY-RUNNING` | `scripts/install_agy_gemini_coordinator_launchd.sh --activate-publisher-only` | live seven AO/no-PID; post-activation Publisher exact-run stage; current approvals | live generation equals target; Publisher canary one-shot | replace/bootstrap Publisher only as normal exact-run; execute one bounded child | Publisher child enters exact-run bounded window; other six unchanged AO/no-PID | Publisher-only activation receipt, child run receipt, transaction evidence | Publisher stage consumed | yes for Publisher stage | no during running; yes for next cycle | second child, auto retry, regression failure or tag/push failure must fail closed | Publisher rollback/stop-loss; legal return `ST-CANARY-TERMINAL`, `ST-CANARY-READY`, or `UNKNOWN` by evidence | Capacity policy must already be current | Rule 25 authorization consumed |
| `TE-CANARY-RUNNING-TO-TERMINAL` | `ST-CANARY-RUNNING` | `ST-CANARY-TERMINAL` | Publisher transaction wrapper and stop-loss/terminal verification | Publisher exact-run child bounded; transaction evidence present | same live generation | finish child; commit/tag/push or fail/recover; stop further Publisher child | Publisher no longer running; terminal receipt present; other six AO/no-PID | transaction/tag/push receipt or failure/recovery receipt, terminal launchctl snapshot | canary-running window | yes | yes for next canary cycle | release regression failure or auto retry yields terminal blocked state, not steady | transaction rollback/stop-loss; legal return `ST-CANARY-TERMINAL` or `UNKNOWN` | no mutation authority | future authorization must start over |
| `TE-CANARY-TERMINAL-TO-STEADY` | `ST-CANARY-TERMINAL` | `ST-STEADY` | separately authorized steady-autonomy commit/activation path | terminal evidence plus explicit steady authorization | live target may be committed to steady autonomy | convert from bounded canary terminal to approved steady mode | steady autonomy receipts current | steady authorization receipt, live steady aggregate | canary-only approval | yes if canary stage existed | not by default | missing authorization keeps `ST-CANARY-TERMINAL` | independent rollback plan; legal return `ST-CANARY-TERMINAL` | policy-only unless steady plan requires new Capacity | Rule 25/canary success not sufficient without explicit steady authorization |

## Critical Edge Notes

### Stage Before Reset

`TE-01`：`--reset-publisher-activation-only` must run after target Publisher exact-run stage exists. The target stage is the proof context for resetting old live Publisher because the reset validates:

- stage manifest digest and generation;
- staged Publisher plist;
- `publisher-max-runs=1`;
- optional `publisher-exact-run-id`;
- live Publisher normal terminal/scheduled contract;
- other six live services activation-only loaded/no-PID.

Therefore `ST-CANARY-TERMINAL -> ST-TARGET-STAGED -> ST-QUIESCED-TARGET-STAGED` is the only legal ordering. `terminal -> reset -> stage` lacks target proof context and is not a v1 edge.

`78` 在此 edge 只可視為 old-live activation-only wrapper 因 old expected digest 對 promoted shared manifest mismatch 而產生的 inert validation terminal。接受它仍要求 target stage current/newer、current receipts、loaded/no-PID、`not running` 或 `waiting`，以及 launchctl observed path 精確等於該 label 的 live plist path。這不授權 production workload child；任意其他 nonzero、PID、path drift、normal mode 或 target generation mismatch 一律 `REJECTED`。

### Activation Deletes Stage

`TE-03`：`--activate-only` replaces live plists and then removes the private stage. Once `TE-CAPACITY-TO-ACTIVATED` is `VERIFIED`, every pre-activation private-stage evidence item is invalid:

- target stage tree digest;
- staged coordinator/four-lane receipts;
- staged Capacity receipt;
- staged Publisher exact-run receipt;
- `publisher-max-runs=1`;
- `publisher-exact-run-id`;
- readiness package that used those stage receipts.

`ST-ACTIVATED -> ST-CANARY-READY` must therefore restage Publisher exact-run and regenerate current readiness/Rule 25 evidence. Operator memory is not valid evidence.

### Capacity and Inert Loaded Semantics

`CP-01`：`ST-QUIESCED-TARGET-STAGED` and `ST-CAPACITY-READY` require old live services to be activation-only loaded/no-PID. In `ST-QUIESCED-TARGET-STAGED`, Capacity target stage is still absent; Capacity preflight/candidate evidence belongs to `TE-QUIESCED-TO-CAPACITY`, not to the pre-edge state. The live topology maps to `INERT_LOADED`, `pid_required=false`, `measurement_required=false`, `expected_process_count=0`, `resource_usage=NOT_APPLICABLE`. A PID is violation; lack of PID is not itself RSS telemetry failure for this phase.

### Bounded Canary vs Steady Autonomy

`TE-04`：`ST-CANARY-RUNNING -> ST-CANARY-TERMINAL` closes a bounded canary. It does not imply `ST-STEADY`. `ST-CANARY-TERMINAL -> ST-STEADY` requires an independent authorization edge and cannot be inferred from transaction/tag/push success alone.

## All-Edge Invariants

- `CT-01`：content topology remains `new -> i18n-new` and `rewrite -> i18n-rewrite`; no edge may rewrite content lineage.
- Historical Cycle 31 readiness may be replay evidence only; it cannot fill current target readiness.
- Rollback outcome must return to one of the legal state IDs in the state contract or mark reconciliation `UNKNOWN`.
- `Rule 25 READY` is production authorization evidence, not phase or transition evidence.

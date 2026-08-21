---
id: PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821
card_id: CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821
status: candidate
version: 1
---

# G8 Cycle 29-32 Shadow Replay

## Contract Scope

本文件用 `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md` 的 state IDs 與 `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md` 的 edge IDs，對 Cycle 29-32 做 evidence-bounded replay。Replay 不碰 production，不把歷史 readiness 冒充 current target evidence，不把缺 evidence 補猜成 success。

Requirement ownership：

| requirement | owner | cross-reference |
| --- | --- | --- |
| `SC-01` | state contract | replay separates desired/observed/transition/policy evidence |
| `SC-02` | state contract | replay uses only eight legal state IDs |
| `SC-03` | state contract | replay consumes service group fields |
| `TE-01` | edge map | replay validates stage-before-reset ordering |
| `TE-02` | edge map | replay applies verified success rule |
| `TE-03` | edge map | replay predicts activation invalidates stage |
| `TE-04` | edge map | replay keeps canary terminal distinct from steady |
| `RP-01` | 本文件：Cycle 29-32 Replay Matrix |
| `RP-02` | 本文件：Cycle 32 Missing Edge Prediction |
| `RP-03` | 本文件：Post-Activation Restage Prediction |
| `CP-01` | state contract | replay maps loaded/no-PID to inert policy |
| `CT-01` | state contract | replay verifies no content topology mutation |

## Evidence Inventory

Replay 使用以下 committed evidence 與 bounded source contracts：

| evidence_id | source artifact / source contract | used for |
| --- | --- | --- |
| `EV-C25-AO-LIVE` | `CARD-PANTHEON-G8-LIVE-ACTIVATION-ONLY-CONVERGENCE-CYCLE-25-20260821-RESULT.md` | G23 seven live activation-only loaded/no-PID baseline |
| `EV-C29-CAPACITY-STAGE` | `CARD-PANTHEON-G8-QUIESCENT-CAPACITY-STAGE-CYCLE-29-20260821-RESULT.md` | G23 Capacity PASS and seven-plist private stage |
| `EV-C30-PUBLISHER-TERMINAL` | `CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-30-20260821-RESULT.md` | Publisher-only canary failure, terminal normal Publisher, no production publish |
| `EV-C31-READINESS-HISTORICAL` | `CARD-PANTHEON-G8-POST-FIX-PRECANARY-READINESS-CYCLE-31-20260821-RESULT.md` | historical readiness only; source/stage mismatch blocker |
| `EV-C32-PROMOTION-STAGE` | `CARD-PANTHEON-G8-RUNTIME-PROMOTION-STAGE-CONVERGENCE-CYCLE-32-20260821-RESULT.md` | G34 promotion/stage, Capacity preflight rejection, rollback |
| `EV-PRECANARY-DIAG` | `CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821-RESULT.md` | precise Cycle 32 mismatch: live Publisher normal vs expected activation-only |
| `EV-RESET-CONTRACT` | `scripts/install_agy_gemini_coordinator_launchd.sh --reset-publisher-activation-only` and reset repair result | reset requires matching one-shot stage and other six AO/no-PID |
| `EV-ACTIVATE-CONTRACT` | `scripts/install_agy_gemini_coordinator_launchd.sh --activate-only` | activation replaces live plists and removes private stage |
| `EV-CAPACITY-CONTRACT` | `scripts/pantheon_content_capacity_guard.py` preactivation transition | staged target normal, old live AO/no-PID, loaded/no-PID topology |
| `EV-MANIFEST-CONTRACT` | `scripts/pantheon_content_runtime_manifest.py` plist receipt activation-mode parsing | normal vs activation-only mismatch semantics |

## Replay Status Values

| value | meaning |
| --- | --- |
| `VERIFIED` | evidence satisfies edge verified success rule |
| `REJECTED` | evidence proves the attempted edge is illegal or a required field conflicts |
| `UNKNOWN` | missing current evidence prevents decision |
| `HISTORICAL_ONLY` | valid artifact exists but cannot authorize current target |

## Cycle 29-32 Replay Matrix

### Cycle 29

| field | replay |
| --- | --- |
| evidence inventory | `EV-C25-AO-LIVE` plus `EV-C29-CAPACITY-STAGE` |
| desired target | G23 seven-plist private stage with Publisher exact run `auto-i18n-en-614aa4dc3542ab2c5637`, `max-runs=1` |
| observed live facts | seven services activation-only, loaded/not running, no PID; queue/state/exact run unchanged |
| observed staged facts | pre-Capacity six plists existed and Capacity target plist was absent; Capacity public preflight returned `preactivation_transition=accepted`/`PASS`; Capacity install wrote seventh staged plist |
| matched state before | `ST-QUIESCED-TARGET-STAGED` (`CONVERGED` with Capacity target absent) |
| attempted edge | `TE-QUIESCED-TO-CAPACITY` |
| allowed / rejected / unknown | `VERIFIED` |
| missing / stale evidence | no current missing field for G23 Capacity stage; later cycles cannot reuse this as current G34 evidence |
| exact blocker prediction | no blocker at Cycle 29; next edge is activation-only aggregate |
| next allowed edge | `TE-CAPACITY-TO-ACTIVATED` to `ST-ACTIVATED`, if separately authorized |

Cycle 29 proves loaded/no-PID can be a legal quiescent window and can support Capacity preactivation when all seven old-live services are activation-only. The pre-edge state has only six target plists; Capacity preflight/install is the edge that creates seventh-stage evidence. Under `CP-01`, absence of PID is expected inert state, not a child-process failure.

### Cycle 30

| field | replay |
| --- | --- |
| evidence inventory | `EV-C29-CAPACITY-STAGE` plus `EV-C30-PUBLISHER-TERMINAL` |
| desired target | Execute one bounded Publisher exact-run canary after G23 readiness/capacity gates |
| observed live facts | Publisher-only activation was invoked once; first child failed release regression; launchd started a second child due to live Publisher RunAtLoad/StartInterval; stop-loss booted out Publisher; other six services were not mutated |
| observed staged facts | Publisher stage was consumed by Publisher-only activation; exact run remained in queue; no release commit/tag/push |
| matched state before | `ST-CANARY-READY` if all current preconditions from Cycle 29/activation evidence were present; Cycle 30 result records pre-gates PASS |
| attempted edge | `TE-CANARY-READY-TO-RUNNING`, then `TE-CANARY-RUNNING-TO-TERMINAL` |
| allowed / rejected / unknown | first activation entered `ST-CANARY-RUNNING`; terminal outcome is `VERIFIED` as `ST-CANARY-TERMINAL` with failure/recovery evidence, not steady |
| missing / stale evidence | no committed publish/tag/push; no steady authorization |
| exact blocker prediction | next cycle must start from terminal mixed cohort: Publisher normal terminal/scheduled or absent, other six activation-only |
| next allowed edge | `TE-CANARY-TERMINAL-TO-TARGET-STAGED`; not `TE-CANARY-TERMINAL-TO-STEADY` without independent authorization |

`TE-04` applies here: failed or successful bounded Publisher canary terminal state is not `ST-STEADY`. The next safe path must rebuild target stage, then reset Publisher to old-live activation-only before Capacity can run.

### Cycle 31

| field | replay |
| --- | --- |
| evidence inventory | `EV-C31-READINESS-HISTORICAL`, `EV-RESET-CONTRACT` |
| desired target | Check whether canonical TMPDIR fix and current readiness can authorize a new canary |
| observed live facts | live plist cohort remained G23 activation-only for core/Capacity; Publisher terminal state from Cycle 30 was not converted by a formal reset in this cycle |
| observed staged facts | private stage control was G33, six plists only; Capacity plist absent; runtime actor did not carry canonical TMPDIR fix |
| matched state | `UNKNOWN` for current target authorization; historical readiness package is `HISTORICAL_ONLY` |
| attempted edge | no legal transition edge executed; synthetic readiness was generated only |
| allowed / rejected / unknown | `UNKNOWN` for `ST-CANARY-READY`; `REJECTED` if Cycle 31 readiness is used as current target evidence |
| missing / stale evidence | current runtime actor with canonical fix; current seven-plist stage; current Capacity receipt; current Rule 25 tied to target phase |
| exact blocker prediction | source/stage mismatch and missing Capacity stage prevent canary authorization |
| next allowed edge | promote current target and stage it: `TE-CANARY-TERMINAL-TO-TARGET-STAGED` |

Cycle 31 demonstrates why readiness artifacts are not transition evidence. Synthetic readiness `READY` can be true while current target stage is incomplete and production runtime actor lacks the required source. Replay therefore treats it as historical comparison, not authorization.

### Cycle 32

| field | replay |
| --- | --- |
| evidence inventory | `EV-C32-PROMOTION-STAGE`, `EV-PRECANARY-DIAG`, `EV-RESET-CONTRACT`, `EV-CAPACITY-CONTRACT`, `EV-MANIFEST-CONTRACT` |
| desired target | Promote canonical TMPDIR source to runtime actor, stage coordinator/four lanes plus Publisher exact-run, run Capacity preflight/install, continue to readiness/Rule 25/canary |
| observed live facts | live Publisher remained normal scheduled/terminal from previous Publisher-only canary; other six services were activation-only loaded/no-PID; no live plist mutation occurred in Cycle 32 |
| observed staged facts | target G34 coordinator/four lanes and Publisher exact-run stage existed; Capacity preflight failed before Capacity install; stage had six plists, Capacity absent; rollback restored previous stage |
| matched state before Capacity | `ST-TARGET-STAGED` (`CONVERGED` before Capacity attempt) |
| attempted edge | Cycle 32 attempted to move from staged target toward Capacity, functionally `TE-QUIESCED-TO-CAPACITY`, but skipped `TE-TARGET-STAGED-TO-QUIESCED` |
| allowed / rejected / unknown | `REJECTED`; precondition old-live seven activation-only loaded/no-PID failed because Publisher live plist was normal |
| missing / stale evidence | missing formal Publisher reset receipt; missing post-reset live Publisher activation-only receipt; missing old-live all-seven AO/no-PID snapshot; missing Capacity staged receipt because install did not run |
| exact blocker prediction | `plist activation mode mismatch` on `com.pantheon.agy-content-publisher`; Capacity expects old live Publisher activation-only, actual live Publisher normal |
| next allowed edge | `TE-TARGET-STAGED-TO-QUIESCED` via `--reset-publisher-activation-only`; after that rerun Capacity preflight/install |

`RP-02`：Cycle 32 must not go directly from `ST-TARGET-STAGED` to Capacity. The missing legal edge is `ST-TARGET-STAGED -> ST-QUIESCED-TARGET-STAGED`, implemented only by the formal Publisher activation-only reset authority. This edge requires target Publisher exact-run stage first, so the correct order is stage then reset, not terminal then reset.

## Post-Activation Restage Prediction

`RP-03`：If Cycle 32 had completed `TE-TARGET-STAGED-TO-QUIESCED` and `TE-QUIESCED-TO-CAPACITY`, the next edge would be `TE-CAPACITY-TO-ACTIVATED`. Source contract `EV-ACTIVATE-CONTRACT` shows aggregate `--activate-only` replaces seven live plists and deletes the private stage. Therefore:

| after activation fact | implication |
| --- | --- |
| live target seven services activation-only loaded/no-PID | can match `ST-ACTIVATED` |
| private stage removed | all staged Publisher exact-run evidence from pre-activation is stale |
| `publisher-exact-run-id` and `publisher-max-runs` files removed with stage | Publisher-only activation lacks current stage controls |
| readiness/Rule 25 package generated before activation consumed old stage evidence | package cannot authorize `ST-CANARY-READY` |

Next required edge is `TE-ACTIVATED-TO-CANARY-READY`: restage Publisher exact-run after activation and regenerate current readiness/capability/Rule 25 evidence. If a later flow tries `TE-CANARY-READY-TO-RUNNING` using pre-activation Publisher staged receipt, replay predicts a stale-stage blocker before canary.

## Edge Verification Summary

| cycle | observed matched state | attempted edge | replay verdict | next allowed edge |
| --- | --- | --- | --- | --- |
| 29 | `ST-QUIESCED-TARGET-STAGED` | `TE-QUIESCED-TO-CAPACITY` | `VERIFIED` | `TE-CAPACITY-TO-ACTIVATED` |
| 30 | `ST-CANARY-READY` then `ST-CANARY-RUNNING` | `TE-CANARY-READY-TO-RUNNING`; `TE-CANARY-RUNNING-TO-TERMINAL` | terminal `VERIFIED`; steady `REJECTED` without authorization | `TE-CANARY-TERMINAL-TO-TARGET-STAGED` |
| 31 | no current legal canary-ready state | none; readiness-only check | `UNKNOWN` for current target, `HISTORICAL_ONLY` for readiness | `TE-CANARY-TERMINAL-TO-TARGET-STAGED` |
| 32 | `ST-TARGET-STAGED` | skipped to Capacity path without `TE-TARGET-STAGED-TO-QUIESCED` | `REJECTED` | `TE-TARGET-STAGED-TO-QUIESCED` |

## Replay Conclusions

1. `RP-01`：Cycle 29-32 replay is evidence-bounded. Where evidence is historical or missing, verdict remains `HISTORICAL_ONLY` or `UNKNOWN`.
2. `RP-02`：Cycle 32 precise missing edge is `TE-TARGET-STAGED-TO-QUIESCED`, not another source promotion, not direct Capacity install, and not a manual plist edit.
3. `RP-03`：After any successful aggregate activation, Publisher exact-run stage must be rebuilt before `ST-CANARY-READY`; pre-activation staged receipt is invalid by contract.
4. `CP-01`：Activation-only loaded/no-PID must be represented as legal inert process policy. A PID in that phase is violation.
5. `CT-01`：No replay step requires content plane changes; legal content topology remains `new -> i18n-new` and `rewrite -> i18n-rewrite`.

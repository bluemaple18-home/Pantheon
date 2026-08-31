---
id: PANTHEON-FOUR-LANE-SEALED-COHORT-ACCEPTANCE-CAPABILITY
parent: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
type: domain-capability-repair
status: READY_FOR_INDEPENDENT_R2_REVIEW
implementation_status: READY_FOR_INDEPENDENT_R2_REVIEW
root_blocker: BLOCKED_D_E_NO_EXISTING_SEALED_PROVIDER_OUTBOX_REPLAY_SEAM
current_remote_release: main
canonical_actor_sha: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
canonical_release: v0.3.375
accepted_base_status: ACCEPTED_BASE_COMMITTED
accepted_base_sha: b13bc765e9f694b3d9eeefc65335a5410cf5d898
current_head: b13bc765e9f694b3d9eeefc65335a5410cf5d898
accepted_base_parent_sha: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
production_activation_authorized: false
acceptance_launchctl_authorized: false
shadow_execution_authorized: false
provider_calls_authorized: false
public_publish_authorized: false
commit_authorized: true
candidate_commit: THIS_COMMIT
candidate_commit_authorized: true
candidate_commit_marker: THIS_COMMIT_RESOLVES_TO_GIT_COMMIT_IDENTITY_AFTER_COMMIT
independent_review_authorized: true
independent_review_verdict: NOT_RUN
independent_review_scope: FRESH_ZERO_WRITE_REVIEW_THIS_COMMIT_VS_B13
target_after_repair: READY_FOR_INDEPENDENT_R2_REVIEW
target_not_this_card: GO_FOUR_LANE_RUNTIME_CURRENT
slice_r1_review: SLICE_R_RE_REVIEW_GO
slice_r2_status: READY_FOR_INDEPENDENT_R2_REVIEW
quarantine_ref: quarantine/slice-r2-unauthorized-3112b
---

# Pantheon Four-Lane Sealed Cohort Acceptance Capability

## Root Question

Gate A-C 已由 Owner 授權形成 exact accepted base commit：

`b13bc765e9f694b3d9eeefc65335a5410cf5d898`

其 parent 為 canonical release actor：

`0f61545f8c6b561742b27792b8fef11ae8b1ccc5`

D/E discovery 已接受：

`BLOCKED_D_E_NO_EXISTING_SEALED_PROVIDER_OUTBOX_REPLAY_SEAM`

Integration compatibility audit has since narrowed Slice R:

- Slice R1 single-job sealed replay has `SLICE_R_RE_REVIEW_GO`.
- R1 is not cohort-usable because its authority is single-job scoped.
- Slice R2 candidate code exists in the working tree and Owner has authorized creation of the exact six-file candidate commit.
- `3112b` / `3c2f` are quarantined observations, not accepted Slice R2 authority.
- Slice C must not start until the exact frozen candidate commit resolves `THIS_COMMIT`, and a fresh zero-write independent review of `THIS_COMMIT` versus `b13bc765e9f694b3d9eeefc65335a5410cf5d898` returns `R2_REVIEW_GO`.

本卡只定義 Pantheon-local 的 bounded capability repair，讓後續可以在同一 isolated 七服務 cohort 裡證明四線 runtime operability。它不是 AI Core 卡，不新增第二套 runtime，不重新定義 Writer/Reviewer/Publisher domain 邏輯，也不公開發布文章。

## Current Authority Snapshot

| 項目 | 目前事實 | 卡片含義 |
| --- | --- | --- |
| canonical actor | `0f61545f8c6b561742b27792b8fef11ae8b1ccc5` | 仍是遠端 release actor。 |
| release | `v0.3.375` | 必須保持版本線正確，不得誤寫成其他 tag。 |
| Gate A-C closeout | `ACCEPTED_BASE_COMMITTED` | Gate A-C accepted-base commit 已存在，可作為 Slice R 實作底座。 |
| accepted base SHA | `b13bc765e9f694b3d9eeefc65335a5410cf5d898` | Slice R 必須以此 exact SHA 為 base，不得隱式吸收其他 dirty diff。 |
| current HEAD | `b13bc765e9f694b3d9eeefc65335a5410cf5d898` | Current actor authority 與 accepted base 目前一致。 |
| accepted base parent | `0f61545f8c6b561742b27792b8fef11ae8b1ccc5` | 遠端 release actor 仍是 `v0.3.375`，未 push/tag/deploy。 |
| Slice R1 | `SLICE_R_RE_REVIEW_GO` | single-job sealed replay 可接受，但不足以進入 cohort Slice C。 |
| Slice R2 | `READY_FOR_INDEPENDENT_R2_REVIEW` | Owner authorized exact candidate commit creation; `THIS_COMMIT` is a non-self-referential marker resolved by git commit identity after commit。 |
| quarantine ref | `quarantine/slice-r2-unauthorized-3112b` | 保存未接受 commit；`3112b` / `3c2f` 不構成 accepted authority。 |
| umbrella blocker | `BLOCKED_D_E_NO_EXISTING_SEALED_PROVIDER_OUTBOX_REPLAY_SEAM` | 阻塞點是 acceptance execution capability 缺口，不是四線 routing 未知。 |

本卡不得把其他 dirty working tree、遠端 `0f61545f`、未提交變更、或未授權 commit 冒充為 accepted authority。Slice R/R2 frozen candidate commit 只能包含本卡列出的 exact six-file allowlist；`THIS_COMMIT` 不預填未存在 SHA，必須由實際 git commit identity 解析。

## Confirmed Existing Boundaries

| Boundary | Evidence | Required Interpretation |
| --- | --- | --- |
| Coordinator create-run entry | `scripts/agy_gemini_coordinator.py:create_campaign_run_adapter` | 這是正式建立四線 run identity/queue state 的入口；future controller 必須使用它或明確證明 equivalent official seam。 |
| Runner ownership | `scripts/agy_gemini_runner.py:process_once` | Runner 已負責 claim request、validate external request、transport、schema validation、write normal inbox、archive request；sealed replay 必須放在 transport boundary，不得讓 controller 直接寫 inbox。 |
| V4 broker substrate | `process_once()` 已有 `AGY_GEMINI_V4_BROKER == "1"` 路徑 | 可重用 V4 single-shot/ledger/anchor/strict schema 底座，但現有正式路徑不等於 acceptance sealed replay mode。 |
| Publisher exact plan-only | 既有 Publisher exact selector/dry-run/push=false path | 本卡不得修改 Publisher domain logic；D/E 只使用 existing exact plan-only selector，且 selector cardinality 必須 exactly one。 |
| Teardown helper | `scripts/pantheon_content_capacity_guard.py:_stop_services` | 目前只是 stop-loss/private helper，不是 successful teardown transaction owner。 |
| Existing synthetic E2E | `pantheon_writer_vnext_runtime_activation_e2e` | 可作參考 evidence，不是真 launchd cohort workload proof。 |

## Allowed Scope

初始 allowlist：

- `scripts/agy_gemini_runner.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- 一個新的薄 one-shot Pantheon acceptance controller
- 對應 tests
- 本卡與本卡 result receipt

只有在 deterministic discovery 證明必要時才可擴充：

- `scripts/pantheon_content_runtime_manifest.py`
- 既有 launchd template 或 ops fixture

擴充 allowlist 必須寫入 result receipt，包含 `why_needed`、`changed_contract`、`why_not_less` 與 rollback。

## Forbidden Scope

禁止修改或新增：

- `scripts/agy_multilingual_pipeline.py`
- domain Writer/Reviewer semantics
- `scripts/agy_content_publisher.py` domain logic
- outbox/inbox schema
- queue registry、FSM、database、new scheduler、new worker
- model route config
- promotion、tag、push、deploy
- production manifest、production queue、production Publisher state
- public content
- AI Core dependency 或 cross-project harness

禁止 controller 直接：

- call `cycle_once` / `process_once(generate_json=fixture)` 當作 cohort proof
- 寫 queue state / inbox / candidate / review / terminal state
- bypass Runner claim/validate/archive ownership
- bypass Coordinator official create-run identity path

## Authorization Boundary

`production launchctl` 仍為 forbidden。

`acceptance-scoped launchctl` 只在未來 Owner 另行明示授權且下列 preflight 全部可證時才允許：

- 0/7 production labels loaded，或已明確證明不會碰 production labels/plists。
- isolated fake home、isolated plist root、isolated queue/state/log/evidence roots。
- labels、manifest digest、generation、runtime identity、activation token 全部可唯一解析。
- production queue、publisher ledger、public content before fingerprint 已封存。
- teardown owner 已存在並有 negative tests。

本卡本身不授權 activation 或 shadow execution。

## Sequential Slices

### Slice R: Sealed Provider Replay Transport

Owner: `scripts/agy_gemini_runner.py`

Goal: 在 Runner 的 provider transport boundary 新增正式 acceptance sealed replay mode，讓真 lane runner 在不呼叫 live provider、不使用 production credential allocator 的情況下，仍走既有 claim、validate、schema validation、normal inbox write、archive。

Required properties:

- explicit acceptance authority digest
- exact lane
- exact run ID
- exact request SHA
- exact role
- exact model
- exact schema SHA
- sealed executable SHA
- current actor/executable SHA
- live provider disabled
- production allocator disabled
- response through existing Runner-owned inbox path
- request archived by Runner after successful processing

Acceptance gates:

- RED: sealed replay authority digest mismatch rejects before provider/allocator attempt。
- RED: wrong lane/run/request/role/model/schema/executable SHA rejects before inbox mutation。
- RED: live provider credential env present during sealed mode rejects fail-closed。
- GREEN: sealed deterministic response is accepted only when every authority field matches。
- GREEN: hydrated/validated response lands through normal inbox and archive paths。
- `git diff --check` PASS。

Stop condition:

- 若必須改 outbox/inbox schema、domain Writer/Reviewer、model routes 或 Publisher logic，立即 `BLOCKED_R_SCOPE_EXPANSION_REQUIRED`。

### Slice R2: Sealed Authority Bundle Session

Owner: `scripts/agy_gemini_runner.py` transport authority plus acceptance controller session preparation.

Goal: 將 R1 single-job sealed replay 擴為 cohort-usable 的 sealed authority bundle/session，但仍保持 Runner 每個 tick 自己 claim、validate、RAW_STDIN、schema validate、write inbox、archive。R2 不得讓 controller 監看 queue、動態換 authority、或 direct write state。

Current R2 closeout status:

`READY_FOR_INDEPENDENT_R2_REVIEW`

R2 candidate code remains unstaged until the authorized exact candidate commit is created. Repair/test evidence is GREEN and Owner has authorized exact candidate commit creation. `THIS_COMMIT` is a non-self-referential marker resolved by git commit identity after commit; no SHA is prefilled before the commit exists. This does not authorize Slice C, activation, shadow execution, provider calls, public publishing, push, tag, or deploy.

Session-level authority must bind:

- accepted base SHA: `b13bc765e9f694b3d9eeefc65335a5410cf5d898`
- actual actor SHA
- generation
- canonical queue root
- lane
- exact run ID
- provider call budget
- strict bundle digest

Bundle-level authority must contain multiple strict unique per-job entries:

- session ID
- entry ID
- job ID
- request SHA
- lane
- run ID
- role
- model
- response schema SHA
- sealed result SHA
- sealed executable path
- sealed executable SHA
- required flag

Runner behavior:

- each tick reads one immutable sealed authority bundle。
- runner finds exactly one matching bundle entry from the exact run pending outbox。
- runner then performs its normal ownership path: claim, validate, RAW_STDIN, schema validation, inbox write, archive。
- public `process_once()` contract remains unchanged outside sealed acceptance mode。
- controller must not monitor queue state to switch authority dynamically。
- controller must not write inbox、candidate、review、terminal、or queue state。

Required negative cases:

- unknown bundle rejects before claim with zero mutation。
- ambiguous bundle entry rejects before claim with zero mutation。
- lane/run/job/request mismatch rejects before claim with zero mutation。
- role/model/schema/executable digest mismatch rejects before provider or inbox mutation。
- provider call budget exceeded rejects before provider or inbox mutation。
- missing sealed executable or SHA mismatch rejects before provider or inbox mutation。

R2 closeout hard conditions:

1. Externally pinned expected bundle digest must be supplied by the launchd/session caller. Runner must verify it against the exact immutable bundle and reject bundle swap, symlink, non-canonical path, or digest mismatch before claim.
2. Bundle entries must be finite, strict, and unique. Each entry must bind `session_id`, `entry_id`, request identity, lane, run ID, role, model, schema digest, sealed result digest, sealed executable canonical path and executable digest. Ordering and required/optional semantics must be explicit wherever lane flow requires them.
3. The request being consumed must be produced by the real runtime first. The sealed bundle may authorize transport only after the pending outbox request already exists; it must not pre-author or synthesize queue work.
4. Durable exact single-use evidence must reuse V4 broker ledger/anchor plus normal Runner inbox/archive identities. R2 must not invent a new FSM, registry, usage ledger, or database unless a measured existing-seam proof shows V4 broker + inbox/archive cannot express the requirement.
5. Crash-state classification must be explicit. R2 must document and test recovery/fail-closed behavior for pre-claim reject, claim-time authority drift, post-claim transport failure, broker ledger replay, inbox written/archive missing, archive written/inbox missing, and exhausted/unused entries.
6. A session-close validator must prove every required entry was consumed exactly once, no unauthorized entry was consumed, no unknown entry remains active, and no incomplete or unused required entry is silently accepted.

R1 single-job formal CLI is not cohort authority. It must be removed or clearly deprecated as a non-cohort test/support path so that only one formal cohort-session path can authorize Slice C.

Acceptance gates:

- RED: R1 single-job authority cannot be used to authorize multi-job cohort execution。
- RED: unknown/ambiguous/budget/mismatch cases all fail pre-claim with zero mutation。
- RED: externally supplied expected bundle digest mismatch rejects before bundle read is trusted or queue mutation starts。
- RED: bundle swap/symlink/non-canonical path rejects before queue mutation。
- RED: missing `session_id` / `entry_id` / sealed result digest / explicit required semantics rejects before queue mutation。
- RED: crash-state matrix cases are classified and either recover via existing durable evidence or fail closed without widening authority。
- GREEN: multiple strict unique entries in one sealed bundle can authorize sequential real runner ticks for the same session/lane/run。
- GREEN: public `process_once()` callers without sealed acceptance env observe the original contract。
- GREEN: session-close validator proves exact required consumption and no unauthorized/unused/incomplete entries。
- GREEN: R/R2 repair and test evidence is sufficient for Owner to authorize exact frozen candidate commit creation。
- GREEN: after exact candidate commit exists, fresh read-only R2 independent review returns `R2_REVIEW_GO`。
- `git diff --check` PASS。

Stop condition:

- 若 R2 需要新增 queue registry、FSM、database、dynamic controller queue monitor、direct state writer、或改 public process_once contract，立即 `BLOCKED_R2_SCOPE_EXPANSION_REQUIRED`。

Only after the exact frozen candidate commit exists and fresh zero-write independent review of `THIS_COMMIT` versus `b13bc765e9f694b3d9eeefc65335a5410cf5d898` returns `R2_REVIEW_GO` may this card transition to `READY_FOR_SLICE_C_IMPLEMENTATION`。

### Slice C: Exact Four-Lane Cohort Shadow Consumption

Owner: existing Coordinator/lane runner/installer lifecycle seams。

Goal: 用同一 manifest、generation、runtime identity digest、activation token 與 isolated roots，讓真正的 Coordinator 與四個 lane runners 各自處理 exactly one shadow run。

Required structure:

- acceptance controller 使用 `create_campaign_run_adapter` 或正式 create-run identity seam 建立四筆 exact shadow runs。
- Coordinator 只允許四個 exact shadow run，不做 production sweep。
- lane services 綁定自己的 `--lane` 與 `--exact-run-id`。
- 四個 lane roots 分離：`new`、`rewrite`、`i18n-new`、`i18n-rewrite`。
- Publisher 僅走 existing exact plan-only selector，且每 lane selector cardinality exactly one。
- public publishing disabled。
- production queue/ledger/public content mutation zero。

Acceptance gates:

- RED: wrong lane worker receiving run rejects before mutation。
- RED: wrong manifest/generation/runtime identity/token rejects before I/O。
- RED: selector zero rejects without publish。
- RED: selector many rejects without publish。
- GREEN: four exact runs reach terminal state through real Coordinator/runner consumption。
- GREEN: each lane produces Writer receipt, Reviewer receipt or sealed equivalent accepted response, and Publisher plan-only selector=1。
- GREEN: before/after production fingerprint unchanged。

Stop condition:

- 若 controller 需要直接寫 queue/inbox/candidate/review/terminal 才能過，立即 `BLOCKED_C_CONTROLLER_BYPASS_REQUIRED`。

### Slice T: Successful Teardown Owner

Owner: acceptance controller plus existing launchd/runtime lifecycle helpers。

Goal: 建立成功路徑 teardown transaction owner。它不是新 FSM，只負責收斂一次 acceptance session。

Required teardown sequence:

1. freeze shadow injection。
2. wait until four exact runs terminal。
3. verify processing queue empty and no active acceptance run。
4. bootout 7/7 acceptance labels。
5. verify 7/7 unloaded。
6. remove activation token、barrier、readiness、lock、stage residue。
7. prove token invalid after teardown。
8. verify production queue/ledger/public content fingerprint unchanged。
9. write teardown receipt。

Acceptance gates:

- RED: teardown refuses if any run is non-terminal。
- RED: teardown refuses if processing queue is non-empty。
- RED: teardown refuses if production fingerprint changed。
- RED: stale token/readiness/lock residue after cleanup blocks closeout。
- GREEN: 7/7 labels unloaded, token invalid, isolated residue removed, production fingerprint identical。

Stop condition:

- 若需處理「恢復原本已 loaded production services」的分支，本卡第一版停止為 `BLOCKED_T_PREEXISTING_SERVICE_STATE_UNSUPPORTED`；第一版要求 acceptance 開始前 0/7 unloaded。

## Delta Acceptance After Repair

Capability repair accepted 後，不得直接沿用舊 Gate A-C receipts，也不得全量重跑歷史文章。必須重編 requirement-level delta disposition：

| Requirement | Disposition | Execution Requirement |
| --- | --- | --- |
| historical four-lane public outcomes | `CARRY_FORWARD` | `NOT_REQUIRED` |
| current actor/manifest/generation/runtime identity | `REBIND` | `REQUIRED` |
| Slice 2A baseline 38-node manifest | `REVALIDATE` | `REQUIRED` |
| Gate C 13-node negative manifest | `REVALIDATE` | `REQUIRED` |
| sealed replay negative matrix | `REVALIDATE` | `REQUIRED` |
| Rule24 capacity | `REBIND` or `REVALIDATE` based on changed installer/runtime binding | `REQUIRED if intersected` |
| seven-service static stage | `REVALIDATE` | `REQUIRED` |
| D/E cohort shadow | `REVALIDATE/NEW_EXECUTION` | `REQUIRED` |
| successful teardown | `NEW_EXECUTION` | `REQUIRED` |
| public four articles regeneration | `CARRY_FORWARD` | `NOT_REQUIRED` |

Any `IMPACT_UNKNOWN` blocks D/E; it does not authorize full rerun。

## Why Not Less / Why Not More / Do Not Absorb

`why_not_less`:

- Only reusing synthetic E2E, static stage, or activation-only cannot prove true launchd cohort workload consumption。
- Function injection through `process_once(generate_json=...)` cannot prove sealed transport in the deployed runner path。
- Manual stop commands cannot prove successful teardown or residue cleanup。
- R1 single-job authority cannot prove immutable cohort-session authority, because it does not bind finite session entries, exact-once closeout, or multi-job ordering。
- Dynamic controller switching cannot prove no queue-monitor authority or no direct state-writer bypass。
- Green runner ticks alone cannot prove externally pinned bundle digest, crash-state recovery, or required-entry closeout semantics。

`why_not_more`:

- Existing runtime, Coordinator, Runner, V4 broker, exact selector, and activation barrier are reusable。
- The measured gap is acceptance execution capability, not a need for second runtime, new scheduler, new registry/FSM, or Publisher rewrite。
- GO_FOUR_LANE_PRODUCTION_CURRENT is outside this card。
- R2 must reuse V4 broker ledger/anchor plus normal inbox/archive durable identities unless a measured seam proves they cannot express exact single-use authority。
- This card correction authorizes only exact six-file candidate commit creation. It does not authorize Slice C, launchd activation, shadow execution, provider calls, public publishing, push, tag, or deploy。

`do_not_absorb`:

- AI Core governance rules。
- Domain content quality acceptance。
- Live Writer/Reviewer model success。
- Production canary or public publish。
- Historical article regeneration。
- Cross-project generic harness。
- Controller/installer/coordinator/manifest/publisher changes。
- New queue registry、FSM、database、usage ledger、or second runtime。
- Any path where R1 single-job formal CLI remains the Slice C authority instead of being removed/deprecated behind the single cohort-session formal path。

## Authorized Candidate Creation Boundary

R/R2 repair and test evidence is GREEN in the working tree, including the Slice R2A `BASELINE_TEST_TIMING_ASSERTION_DRIFT` test-only closeout and the current 88 passed evidence. That evidence is not an independent review verdict. Owner has authorized creation of the exact frozen candidate commit; after that commit exists, independent review is authorized for exact `THIS_COMMIT` versus accepted base `b13bc765e9f694b3d9eeefc65335a5410cf5d898`.

Exact proposed R/R2 candidate commit allowlist:

- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_runner.py`
- `tests/test_agy_gemini_v4_broker.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-SEALED-COHORT-ACCEPTANCE-CAPABILITY-20260831.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-result.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt`

Explicitly excluded from that candidate commit:

- tracked Gate A-C receipt diffs
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/forensics/reviewer-overreach-20260831/`
- authority reconciliation, D/E discovery, Gate A/A1, capacity recovery, seven-service projection, and other untracked discovery artifacts outside the allowlist
- any production/public artifact, queue state, Publisher state, launchctl state, tag, push, deploy, or external provider mutation

Legal transition:

exact candidate commit resolving `THIS_COMMIT` → fresh zero-write independent review of `THIS_COMMIT` vs `b13bc765e9f694b3d9eeefc65335a5410cf5d898` → `R2_REVIEW_GO` → Slice C implementation.

## Required Result Receipt

Future implementation must write a result receipt under:

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/`

Required fields:

- exact accepted base SHA。
- changed files and allowlist disposition。
- authority digest inputs。
- Slice R/C/T test manifests and raw outputs。
- provider call count = 0。
- production mutation count = 0。
- launchctl mutation scope, if later authorized。
- before/after production fingerprints。
- teardown receipt。
- independent review verdict。
- final result: `READY_FOR_AUTHORIZED_CANDIDATE_CREATION`, `READY_FOR_INDEPENDENT_R2_REVIEW`, `READY_FOR_SLICE_C_IMPLEMENTATION`, or `BLOCKED_<exact_reason>`。

## Rollback / Removal

For this card-only change: remove this Markdown file。

For future implementation:

- rollback must be exact revert of the capability repair commit(s), not broad reset/checkout。
- removal must disable sealed acceptance mode without changing production provider path。
- one-shot controller must be removable without changing normal production runtime behavior。
- teardown implementation must leave production labels/plists untouched when acceptance launchctl is not active。

## Final Verdict Contract

This card can only produce:

- `READY_FOR_AUTHORIZED_CANDIDATE_CREATION`
- `READY_FOR_INDEPENDENT_R2_REVIEW`
- `READY_FOR_SLICE_C_IMPLEMENTATION`
- `BLOCKED_R2_IMMUTABLE_SESSION_AUTHORITY_INCOMPLETE`
- `BLOCKED_R_SINGLE_JOB_AUTHORITY_NOT_COHORT_USABLE`
- `BLOCKED_R_<exact_reason>`
- `BLOCKED_R2_<exact_reason>`
- `BLOCKED_C_<exact_reason>`
- `BLOCKED_T_<exact_reason>`
- `BLOCKED_REVIEW_<exact_reason>`

It must not produce:

- `GO_FOUR_LANE_RUNTIME_CURRENT`
- `GO_FOUR_LANE_PRODUCTION_CURRENT`
- `PARTIAL_PASS`
- `MOSTLY_PASS`
- `NEARLY_DONE`
- `LAST_STEP`

Current result:

`READY_FOR_INDEPENDENT_R2_REVIEW`

Slice R1 single-job sealed replay has `SLICE_R_RE_REVIEW_GO`, but it is not cohort authority. Slice R2 repair/test evidence is GREEN in the working tree, including Slice R2A test-only timing drift closeout. Owner has authorized exact six-file candidate commit creation; `candidate_commit` is `THIS_COMMIT` and must resolve to the actual git commit identity after commit. `3112b` / `3c2f` are not accepted authority; quarantine ref `quarantine/slice-r2-unauthorized-3112b` preserves the unauthorized candidate. No Slice C, activation, shadow execution, provider calls, public publishing, push, tag, or deploy is authorized.

---
id: RESULT-PANTHEON-SLICE-R2-IMMUTABLE-SESSION-AUTHORITY-CLOSEOUT
card: PANTHEON-FOUR-LANE-SEALED-COHORT-ACCEPTANCE-CAPABILITY
parent: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
slice: R2
status: READY_FOR_INDEPENDENT_R2_REREVIEW
accepted_base_sha: b13bc765e9f694b3d9eeefc65335a5410cf5d898
reviewed_no_go_candidate: e0d50a661af60ac03480aa54d0391af8d1387508
candidate_parent_sha: e0d50a661af60ac03480aa54d0391af8d1387508
candidate_commit: THIS_COMMIT
candidate_commit_authorized: true
final_candidate: THIS_COMMIT
independent_r2_review_verdict: NOT_RUN_REREVIEW
previous_independent_r2_review_verdict: SLICE_R_R2_REVIEW_NO_GO
independent_review_authorized: true
next_legal_status: READY_FOR_INDEPENDENT_R2_REREVIEW
production_activation_authorized: false
acceptance_launchctl_authorized: false
shadow_execution_authorized: false
provider_calls: 0
production_mutation: 0
public_publish: 0
commit_authorized: true
---

# Slice R2 Immutable Session Authority Closeout

## Scope

本次 bounded implementation 修補 fresh zero-write review 對 Runner sealed bundle/session acceptance authority 退回的兩個 finding，並更新本 receipt 與 raw output。Repair/test evidence is GREEN in the working tree, and Owner has authorized the second R2 repair candidate commit. `THIS_COMMIT` is the containing commit marker and resolves only after that commit exists. 沒有執行 Slice C、activation、shadow、provider、production 或 public mutation。

Changed files:

| Path | Disposition |
| --- | --- |
| `scripts/agy_gemini_runner.py` | allowlisted R2 implementation |
| `tests/test_agy_gemini_runner.py` | allowlisted R2 regression tests |
| `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt` | bounded raw verification output |
| `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-result.md` | bounded result receipt |

No Gate A-C receipt, V4 broker source/test, installer, controller, coordinator, publisher, manifest, model route, queue registry, production artifact, public content, push, tag, deploy, or launchctl scope was changed by this repair.

## Candidate Authority Boundary

Current status is `READY_FOR_INDEPENDENT_R2_REREVIEW`.

Reviewed candidate `e0d50a661af60ac03480aa54d0391af8d1387508` returned `SLICE_R_R2_REVIEW_NO_GO`. The 91 passed evidence below is implementation/test evidence only. It is not an independent rereview verdict. Owner has authorized the second repair candidate commit; fresh zero-write rereview is authorized only for exact `THIS_COMMIT` versus accepted base `b13bc765e9f694b3d9eeefc65335a5410cf5d898` after the containing commit identity exists.

Exact proposed repair candidate commit allowlist:

- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_runner.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-SEALED-COHORT-ACCEPTANCE-CAPABILITY-20260831.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-result.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt`

Explicitly excluded:

- tracked Gate A-C receipt diffs
- `tests/test_agy_gemini_v4_broker.py` in this repair step; any existing broker-test diff belongs to the reviewed parent candidate, not to this bounded repair allowlist
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/forensics/reviewer-overreach-20260831/`
- authority reconciliation, D/E discovery, Gate A/A1, capacity recovery, seven-service projection, and other untracked discovery artifacts outside the allowlist
- production/public artifacts, queue state, Publisher state, launchctl state, provider state, tag, push, or deploy

Legal transition:

exact repair candidate commit resolving `THIS_COMMIT` → fresh zero-write independent rereview of `THIS_COMMIT` vs `b13bc765e9f694b3d9eeefc65335a5410cf5d898` → `R2_REVIEW_GO` → Slice C implementation.

## Slice R2A Baseline Test Timing Assertion Drift

`BASELINE_TEST_TIMING_ASSERTION_DRIFT` was closed as test-only.

Evidence before the fix:

- The exact timeout node was reproducibly RED in the active candidate.
- The same exact timeout node was reproducibly RED from accepted base `b13bc765e9f694b3d9eeefc65335a5410cf5d898` via git archive.
- Broker timeout contract assertions already passed: `CLI_TIMEOUT`, `COMPLETE`, `process_count == 1`, `caller_contract_satisfied is False`, and durable ledger `EXEC_CONFIRMED == 1`.
- The only failing assertion was `target.with_suffix(".trace").exists()`.

Root cause:

- The 500 ms timeout case can terminate after broker `EXEC_CONFIRMED` but before Python user-code trace side-effect is written.
- The trace side-effect is not part of the timeout broker contract.

Minimal fix:

- Non-timeout/nonzero still requires the child trace side-effect.
- Timeout no longer requires that user-code side-effect.
- Timeout still requires durable broker contract evidence and exactly one `EXEC_CONFIRMED` ledger event.
- Production broker behavior and timeout duration were not changed.

## Durable Receipt Seam Decision

`BLOCKED_R2_DURABLE_RECEIPT_SEAM_MISSING` is not raised.

R2 uses existing V4 broker ledger/anchor plus normal Runner inbox/archive identities as the durable delivery seam:

- V4 broker ledger and anchor bind `operation_id`, `item_id`, `attempt_id`, request SHA, model, target profile, and executable digest.
- R2 derives the broker `attempt_id` from a canonical digest of the full immutable entry binding: session, entry, namespace, job, request SHA, lane, run, role, model, schema SHA, sealed result SHA, canonical executable path, executable SHA, and required flag. Rebinding any of those authorities cannot reuse a prior ledger/anchor as valid delivery.
- Normal Runner `archive/<job_id>.json` remains the durable request identity.
- Normal Runner `inbox/<job_id>.json` remains the durable response identity.
- Session close is read-only and classifies delivery from these existing artifacts; it does not create a second FSM, registry, database, usage ledger, or controller-owned state.

## Implemented R2 Contract

Formal cohort authority now requires `sealed-replay-bundle-process-once` with:

- `--bundle`
- `--expected-bundle-digest`
- `--lane`
- exactly one `--exact-run-id`

The expected bundle digest is externally supplied by the caller and is checked against the raw bundle file bytes before the bundle body is trusted. The bundle path must be absolute, canonical, non-symlink, regular, owner-owned, and not group/world-writable.

The strict bundle binds:

- `session_id`
- `bundle_digest`
- `accepted_base_sha`
- `actor_sha`
- `generation`
- canonical `queue_root`
- `lane`
- `run_id`
- `namespace`
- `provider_call_budget`
- finite `entries`

`provider_call_budget` may be lower than total entries only when the extra entries are optional. It must be greater than or equal to the number of required entries.

Each strict entry binds:

- `session_id`
- `entry_id`
- `job_id`
- `request_sha256`
- `namespace`
- `lane`
- `run_id`
- `role`
- `model`
- `schema_sha256`
- `sealed_result_sha256`
- canonical `executable_path`
- `executable_sha256`
- `required`

Runner behavior remains owner-correct:

1. The real runtime must first produce the pending outbox request.
2. Runner reads the immutable bundle and finds exactly one pending request in the exact run namespace.
3. Exactly one strict bundle entry must match that pending request.
4. Runner claims through `_process_once()`.
5. Claimed request authority is revalidated.
6. Transport uses V4 `RAW_STDIN_PROFILE`.
7. V4 ledger/anchor bind the session-derived attempt id.
8. The normalized result is checked against `sealed_result_sha256`.
9. Runner writes normal inbox and archive.

The formal single-job sealed CLI command was removed from argparse/main. The remaining single-job support function is legacy/private and cannot authorize cohort execution.

## Crash / Delivery Classification

R2 session close classifies each entry as:

| State | Evidence | Disposition |
| --- | --- | --- |
| `UNUSED` | no ledger, anchor, inbox, archive, processing, or failed state | allowed only for optional entries; required entries block close |
| `DELIVERED` | valid V4 ledger+anchor, valid archive request, valid inbox response, matching bindings, schema-valid result, matching sealed result digest | counts exactly once |
| `INCOMPLETE` | any partial, active, failed, mismatched, cross-session, missing, or malformed combination | fail closed |

Session close rejects if there is unknown/unauthorized state, incomplete evidence, or unused required entries. It is read-only and writes no pipeline state.

F1/F2 bounded repair notes:

- P1-A repair: `_sealed_bundle_attempt_id` no longer hashes only `session_id:entry_id`; restart classification and closeout reject a same-session/same-entry rebinding with changed executable/result authority.
- P1-B repair: delivery classification now treats any bundle entry still present in `outbox` as `INCOMPLETE`; closeout rejects delivered+replayed outbox and optional pending outbox states.
- Session close now also scans isolated `v4/ledger/*.jsonl` and `v4/anchors/*.json` for unknown delivery evidence. Legal bundle evidence is identified by bundle job IDs and session-derived attempt IDs; anything else blocks closeout as unauthorized state.
- Bundle loading now rejects `provider_call_budget < required_entry_count`. Optional entries may still allow `provider_call_budget < len(entries)`.

## Regression Coverage

Runner regression coverage includes:

- GREEN: real pending request followed by two bundle ticks, writer then reviewer, then successful session close.
- RED: single-job authority cannot authorize bundle CLI.
- RED: expected bundle digest mismatch.
- RED: bundle swap after external digest pin.
- RED: symlink / noncanonical bundle path.
- RED: missing `session_id`, `entry_id`, `sealed_result_sha256`, or `required`.
- RED: wrong actor, non-ancestor accepted base, wrong generation, wrong queue root, wrong lane, wrong run.
- RED: unknown, zero, many, duplicate, ambiguous, or already-used pending request.
- RED: provider budget exhausted.
- RED: provider budget lower than required entry count rejects before queue mutation.
- RED: executable SHA mismatch.
- RED: live provider / production allocator env present.
- RED: claim-time authority drift restores outbox and exits nonzero.
- RED: sealed result digest mismatch fails before inbox.
- RED: cross-session reuse is not accepted as delivery.
- RED: same-session/same-entry/job rebound authority with changed executable/result digest is not accepted as delivery.
- RED: delivered entry replayed back into outbox blocks session close.
- RED: optional entry pending in outbox blocks session close.
- RED: session close rejects unused required, unauthorized pipeline state, unknown V4 ledger/anchor evidence, and partial crash states.
- GREEN: public `process_once()` signature remains unchanged and cannot bypass formal transport block with a fixture.

## Verification

Raw output:

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt`

| Gate | Result |
| --- | --- |
| exact timeout node repeated 10 times | PASS: `10/10` |
| `for i in 1 2; do env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_gemini_v4_broker.py \|\| exit 1; done` | PASS: `42 passed in 10.77s`; `42 passed in 9.74s` |
| targeted P1-A/P1-B runner regressions | PASS: `5 passed in 2.55s` |
| `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_gemini_runner.py` | PASS: `49 passed in 8.51s` |
| `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_gemini_v4_broker.py` | PASS: `42 passed in 9.86s` |
| `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile tests/test_agy_gemini_v4_broker.py scripts/agy_gemini_runner.py tests/test_agy_gemini_runner.py` | PASS |
| `git diff --check` | PASS |
| `rg -n "DBG\|DEBUG_THIS\|console\\.log\|pdb\\.set_trace" tests/test_agy_gemini_v4_broker.py scripts/agy_gemini_runner.py tests/test_agy_gemini_runner.py` | PASS: no matches, exit `1` |
| xfail / skip / waiver | 0 |
| provider calls | 0 |
| launchctl mutation | 0 |
| production mutation | 0 |
| public mutation | 0 |

## Verdict

`READY_FOR_INDEPENDENT_R2_REREVIEW`

This is not `R2_REVIEW_GO`, not `READY_FOR_SLICE_C_IMPLEMENTATION`, and not D/E-ready. The only next legal action is exact repair candidate commit creation using the repair allowlist above, then fresh zero-write rereview of `THIS_COMMIT` versus accepted base. Only after that rereview returns `R2_REVIEW_GO` may the program move to `READY_FOR_SLICE_C_IMPLEMENTATION`.

---
id: RESULT-PANTHEON-SLICE-R2-IMMUTABLE-SESSION-AUTHORITY-CLOSEOUT
card: PANTHEON-FOUR-LANE-SEALED-COHORT-ACCEPTANCE-CAPABILITY
parent: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
slice: R2
status: READY_FOR_INDEPENDENT_R2_REVIEW
accepted_base_sha: b13bc765e9f694b3d9eeefc65335a5410cf5d898
current_head: b13bc765e9f694b3d9eeefc65335a5410cf5d898
candidate_commit: THIS_COMMIT
candidate_commit_authorized: true
candidate_commit_marker: THIS_COMMIT_RESOLVES_TO_GIT_COMMIT_IDENTITY_AFTER_COMMIT
independent_r2_review_verdict: NOT_RUN
independent_review_authorized: true
independent_review_scope: FRESH_ZERO_WRITE_REVIEW_THIS_COMMIT_VS_B13
next_legal_status: READY_FOR_INDEPENDENT_R2_REVIEW
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

本次 bounded implementation 只修補 Runner 的 sealed bundle/session acceptance authority，並更新本 receipt 與 raw output。Repair/test evidence is GREEN in the working tree, and Owner has authorized exact six-file candidate commit creation. `THIS_COMMIT` is a non-self-referential marker resolved by git commit identity after commit. 沒有執行 Slice C、activation、shadow、provider、production 或 public mutation。

Changed files:

| Path | Disposition |
| --- | --- |
| `scripts/agy_gemini_runner.py` | allowlisted R2 implementation |
| `tests/test_agy_gemini_runner.py` | allowlisted R2 regression tests |
| `tests/test_agy_gemini_v4_broker.py` | allowlisted test-only Slice R2A timing assertion drift fix |
| `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt` | bounded raw verification output |
| `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-result.md` | bounded result receipt |

No Gate A-C receipt, installer, controller, coordinator, publisher, manifest, model route, queue registry, production artifact, public content, push, tag, deploy, or launchctl scope was changed by this slice.

## Candidate Authority Boundary

Current status is `READY_FOR_INDEPENDENT_R2_REVIEW`.

The 88 passed evidence below is implementation/test evidence only. It is not an independent review verdict. Owner has authorized exact frozen candidate commit creation. A fresh zero-write independent review is authorized only for exact `THIS_COMMIT` versus accepted base `b13bc765e9f694b3d9eeefc65335a5410cf5d898` after the git commit identity exists.

Exact proposed R/R2 candidate commit allowlist:

- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_runner.py`
- `tests/test_agy_gemini_v4_broker.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-SEALED-COHORT-ACCEPTANCE-CAPABILITY-20260831.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-result.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt`

Explicitly excluded:

- tracked Gate A-C receipt diffs
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/forensics/reviewer-overreach-20260831/`
- authority reconciliation, D/E discovery, Gate A/A1, capacity recovery, seven-service projection, and other untracked discovery artifacts outside the allowlist
- production/public artifacts, queue state, Publisher state, launchctl state, provider state, tag, push, or deploy

Legal transition:

exact candidate commit resolving `THIS_COMMIT` → fresh zero-write independent review of `THIS_COMMIT` vs `b13bc765e9f694b3d9eeefc65335a5410cf5d898` → `R2_REVIEW_GO` → Slice C implementation.

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
- R2 derives the broker `attempt_id` from `session_id + entry_id`, so a different session cannot reuse a prior session's ledger as valid delivery.
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
- RED: session close rejects unused required, unauthorized pipeline state, unknown V4 ledger/anchor evidence, and partial crash states.
- GREEN: public `process_once()` signature remains unchanged and cannot bypass formal transport block with a fixture.

## Verification

Raw output:

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/slice-r-sealed-replay-test-output.txt`

| Gate | Result |
| --- | --- |
| exact timeout node repeated 10 times | PASS: `10/10` |
| `for i in 1 2; do env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_gemini_v4_broker.py \|\| exit 1; done` | PASS: `42 passed in 10.77s`; `42 passed in 9.74s` |
| `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agy_gemini_runner.py` | PASS: `46 passed in 7.43s` |
| `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile tests/test_agy_gemini_v4_broker.py scripts/agy_gemini_runner.py tests/test_agy_gemini_runner.py` | PASS |
| `git diff --check` | PASS |
| `rg -n "DBG\|DEBUG_THIS\|console\\.log\|pdb\\.set_trace" tests/test_agy_gemini_v4_broker.py scripts/agy_gemini_runner.py tests/test_agy_gemini_runner.py` | PASS: no matches, exit `1` |
| xfail / skip / waiver | 0 |
| provider calls | 0 |
| launchctl mutation | 0 |
| production mutation | 0 |
| public mutation | 0 |

## Verdict

`READY_FOR_INDEPENDENT_R2_REVIEW`

This is not `R2_REVIEW_GO`, not `READY_FOR_SLICE_C_IMPLEMENTATION`, and not D/E-ready. The only next legal action is exact candidate commit creation using the six-file allowlist. Only after `THIS_COMMIT` resolves to the actual git commit identity may the fresh zero-write R2 review run; only after that review returns `R2_REVIEW_GO` may the program move to `READY_FOR_SLICE_C_IMPLEMENTATION`.

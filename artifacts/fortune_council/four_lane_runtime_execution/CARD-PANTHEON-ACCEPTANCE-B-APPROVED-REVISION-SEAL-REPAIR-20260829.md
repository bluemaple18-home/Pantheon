# CARD: Pantheon Acceptance B approved revision seal repair

status: `RE_REVIEW_REQUESTED`
date: `2026-08-29`
owner: `Implementation Worker`
evidence_dir: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_approved_revision_seal_repair_20260829/`

## Goal

Close the missing authority edge from a terminal rejected translation run audit to a formal-approved edited revision, immutable staging seal, and publisher validated reader.

## Boundaries

- Do not mutate production content.
- Do not publish, tag, push, promote, or replay campaign/provider/coordinator flows.
- Do not create Gen07.
- Do not overwrite root or Gen06 rejected `candidate.json` / `review.json`.
- Do not mutate continuation state, queue registry, or publisher ledger during staging.
- Do not add a database, registry, FSM, universal artifact system, or second runtime.

## Allowed Files

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_content_publisher.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_content_publisher.py`
- Task evidence under the evidence dir above
- This card and final `RESULT.md`

## Required Repair

1. Add a public `stage-approved-edited-candidate` seam in `scripts/agy_multilingual_pipeline.py`.
2. Make the seam plan-only by default; execute requires exact expected plan digest.
3. Lock run/generation, terminal root and Gen06 candidate/review, continuation, queue registry, publisher ledger, source/actor, approved candidate/review/formal result, and formal job identity.
4. Write immutable payload/receipt under `editorial-staging/<operation_id>/`, then atomically replace `editorial-staging/current.json`.
5. Return `ALREADY_STAGED` for identical input and fail closed for drift or conflicting payload.
6. Provide rollback receipt semantics limited to the current operation's stage and exact prior pointer.
7. Add publisher validated reader support: root clean-review or valid approved-revision seal are the only eligible selection paths.
8. Preserve publisher release transaction, version, tag, and push semantics.

## Validation Plan

1. Run the existing RCA RED harness and confirm the missing public seam reproduces before implementation.
2. Add focused multilingual staging tests for plan-only zero write, exact positive, SHA drift, atomicity, idempotence, conflict, rollback, and Gen07 absence.
3. Add focused publisher tests for valid seal selection, tamper/missing seal rejection, ledger lifecycle, dry-run zero mutation, publish ledger receipt digest, and terminal audit bytes preservation.
4. Run the end-to-end lifecycle harness: rejected terminal fixture plus approved edited candidate/review, seal plan/apply, publisher exact select/dry-run.
5. Run affected suites, py_compile, `git diff --check`, and debug marker scan.

## Stop Condition

`RE_REVIEW_REQUESTED` only when RED to GREEN evidence, lifecycle harness evidence, and affected validation commands are captured. Otherwise stop as `BLOCKED` with the exact failing evidence.

## Why This Scope

`why_not_less`: wrapper/manual copy/direct apply cannot prove formal binding, exact current locks, atomic current seal, rollback, or publisher reader contract.

`why_not_more`: existing publisher release transaction, queue registry, and run directory authority are sufficient; Gen07, replacement runs, promotion, provider changes, and new durable subsystems are out of scope.

`do_not_absorb`: no universal staging subsystem, no provider/coordinator rewrite, no deferred-history clearing, no production publication.

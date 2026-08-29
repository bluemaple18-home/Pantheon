# CARD-PANTHEON-SERVICE-ACTIVATION-IDENTITY-CONTRACT-REVIEW-20260829

## Role

Independent Repair Reviewer for the uncommitted service activation shared identity contract Repair.

## Base

- HEAD: `779fb96434c15013d82833788a6795119730daad`
- Expected base: `origin/main`
- Review target: current uncommitted diff plus existing Repair card/artifacts.

## Write Allowlist

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-SERVICE-ACTIVATION-IDENTITY-CONTRACT-REVIEW-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_service_activation_identity_contract_review_20260829/`

## Read Scope

- Changed source/test files:
  - `scripts/pantheon_content_runtime_manifest.py`
  - `scripts/pantheon_content_capacity_guard.py`
  - `tests/test_pantheon_content_runtime_manifest.py`
  - `tests/test_pantheon_content_capacity_guard.py`
- Existing Repair artifacts:
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-SERVICE-ACTIVATION-IDENTITY-CONTRACT-REPAIR-20260829.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/pantheon_service_activation_identity_contract_repair_20260829/`
- Related producer/consumer seams needed to prove the shared manifest identity contract.

## Review Gates

- P0/P1 only block verdict.
- Verify the changed-file allowlist and source/test changed LOC budget.
- Verify a single shared validator/parser binds actor prefix exactly to `actor_head`, requires an opaque nonempty suffix, and does not encode activation mode in the suffix.
- Verify producer `build_manifest` and capacity consumer share that contract.
- Verify capacity removed the private activation-only suffix check while preserving digest, barrier, stage/live tuple, Rule 24, and recovery/normal fail-closed checks.
- Verify exact coordinator install to publisher install to capacity install-recovery-stage RED then GREEN evidence without live install/activate.
- Verify negative coverage for actor drift, malformed/missing/whitespace/stage drift/barrier drift/wrong mode remains RED.
- Verify no capacity-first bypass, per-service identity, new registry, FSM, DB, migration, lane-specific expansion, or if/else expansion.
- Independently rerun the Repair-selected targeted, promotion, affected, py_compile, and `git diff --check` gates.
- For the broad suite, require identical baseline failure node IDs or equivalent trace/import/coverage-boundary proof against parent `779fb`; otherwise verdict is NO_GO.
- Verify production/live mutation count remains zero.

## Verdict Contract

The review will write exactly one `RESULT.md` with either:

- `GO`, with explicit statement that no P0/P1 findings were found; or
- `NO_GO`, with precise P0/P1 findings and unblock conditions.

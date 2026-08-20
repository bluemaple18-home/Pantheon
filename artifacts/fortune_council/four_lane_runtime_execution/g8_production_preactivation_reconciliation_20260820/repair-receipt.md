# G8 production preactivation reconciliation repair receipt

## Candidate

- card_id: `CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REPAIR-20260820`
- status: `CANDIDATE_READY`
- production_mutation: `false`
- scope:
  - `scripts/pantheon_g8_production_preactivation.py`
  - `tests/test_pantheon_g8_production_preactivation.py`
  - `artifacts/fortune_council/four_lane_runtime_execution/g8_production_preactivation_reconciliation_20260820/repair-receipt.md`

## Repair Summary

- Added a zero-production-mutation reconciliation CLI that separates authority, runtime transition, selector, and mutation-tripwire receipts.
- Authority requires local required source, ancestry from required source to origin main, explicit allowlisted source drift, actor checkout bound to origin main, and manifest actor head bound to origin main.
- Runtime transition accepts coherent old-live receipts to coherent new-stage receipts only when staged receipts validate against the runtime manifest and the staged exact run id matches the requested selector.
- Selector creates a temporary queue/state snapshot and calls existing `collect_ready_runs` only against that isolated snapshot, never against production `state_root`.
- Selector rejects zero, multiple, wrong, drifted, or collector-blocked selections while keeping production queue/state/transaction/lock/git refs/live/staged/manifest unchanged.
- Mutation tripwire snapshots queue, state, transaction root, publisher lock, git refs, live root, staged root, and manifest before and after reconciliation; any protected change blocks with `MUTATION_DETECTED`.
- P1 repair: invalid/rejected collector side effects are now confined to the temporary snapshot. Tests assert production protected roots remain unchanged for rejected, invalid, zero, two, drift, and pre-existing ledger/retry/policy-rejection paths.
- P1 retry repair: evidence path is canonicalized before reconciliation and rejected before any snapshot or receipt write when it is equal to or inside protected production roots, publisher lock, git common dir, or the manifest. Rejected evidence paths write only stdout JSON and do not create evidence parents or files.

## Verification

- `21 passed`: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest tests/test_pantheon_g8_production_preactivation.py`
- `31 passed`: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest tests/test_pantheon_g8_production_preactivation.py tests/test_agy_content_publisher.py::test_collect_ready_runs_skips_reviewer_reject tests/test_agy_content_publisher.py::test_collect_ready_runs_exact_selector_excludes_unlisted_ready_run tests/test_agy_content_publisher.py::test_collect_ready_runs_without_exact_selector_keeps_existing_selection tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases`
- `git diff --check`: passed.

## Stop

No production activation, remote mutation, git ref mutation, queue/state/transaction mutation, LaunchAgent mutation, commit, push, tag, or replacement task was performed.

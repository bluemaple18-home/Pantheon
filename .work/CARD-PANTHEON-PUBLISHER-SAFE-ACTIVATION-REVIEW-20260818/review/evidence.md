# CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-REVIEW-20260818 Evidence

## Verdict

ACCEPT_WITH_RESIDUAL_RISK

## Review Identity

- formal_thread_id: `01a0133b-4d9f-77f0-8fe9-97710d195672`
- activation_token: received for this task; exact token intentionally omitted from committed evidence
- dispatch_key: `v1:1e39bd8f50be32db1c4dc6a02a8baee5d612f9d0685496bad9d3769b6caa4c8b`
- reviewer_head_before_evidence: `be15414ea61e5714b094846fbc743e6eb64b1a66`
- base: `0dada575ce0684e0afbaaa1ca7cc8c3a4d97e43f`
- candidate: `f1fab53310df7f89add90097c0a182509642d38b`
- source_head_extra_commit: `be15414ea61e5714b094846fbc743e6eb64b1a66`
- codegraph_status: ready, 573 indexed files, 6398 nodes, 13810 edges

## Changed-file Boundary

Command: `git diff --name-status 0dada575ce0684e0afbaaa1ca7cc8c3a4d97e43f f1fab53310df7f89add90097c0a182509642d38b`

Result:

```text
A	.work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818/evidence.md
M	scripts/install_agy_gemini_coordinator_launchd.sh
M	tests/test_agy_gemini_coordinator.py
```

This matches the review card's expected candidate boundary. The source HEAD commit only adds the review card and is excluded from the candidate diff.

## Findings

No P0/P1 blocking findings found.

## Contract Review

- Missing normal activation barrier now fails before live plist replacement, bootout, bootstrap, and Publisher child invocation. Evidence: `scripts/install_agy_gemini_coordinator_launchd.sh:698-708` validates `ACTIVATION_BARRIER` before `replace_live_plists` at `715`, `bootout_previous_services` at `729`, and `bootstrap_staged_services` at `740`.
- Barrier validation uses the existing `scripts.pantheon_content_runtime_manifest barrier-validate` authority, not a new token framework or sleep-based state machine.
- Normal `--activate` only proceeds when the existing barrier matches the current runtime manifest digest and generation. Missing, invalid, or stale identity fails through the existing failure receipt trap.
- `--activate-only` still removes and rebuilds the barrier before activating child wrappers, preserves `--activation-only` child mode, and keeps child I/O at zero in the focused test.
- Test helpers add hardened optional runtime identity fields to fixture plists so production validation is not weakened.

## Verification

Temporary environment:

- temp root: `/private/tmp/pantheon-safe-review.tJcnx1`
- venv: `/private/tmp/pantheon-safe-review.tJcnx1/.venv`
- base checkout: `/private/tmp/pantheon-safe-review.tJcnx1/base-git`
- candidate checkout: `/private/tmp/pantheon-safe-review.tJcnx1/candidate-git`
- dependencies: `fastapi`, `lunar-python`, `pydantic`, `uvicorn[standard]`, `httpx`, `pytest` installed into the temp venv

Static checks:

- `git diff --check 0dada575ce0684e0afbaaa1ca7cc8c3a4d97e43f f1fab53310df7f89add90097c0a182509642d38b`: passed
- `git show --check f1fab53310df7f89add90097c0a182509642d38b`: passed
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`: passed

Focused candidate activation tests:

Command:

```text
/private/tmp/pantheon-safe-review.tJcnx1/.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_aggregate_activation_rejects_before_mutation_with_failure_receipt
```

Result: `5 passed in 15.77s`

Candidate manifest/publisher subset:

Command:

```text
/private/tmp/pantheon-safe-review.tJcnx1/.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py tests/test_agy_content_publisher.py tests/test_agy_content_publisher_capability_receipt.py
```

Result: `192 passed, 1 warning in 49.00s`

Warning: existing `SyntaxWarning: invalid escape sequence '\/'` during `tests/test_agy_content_publisher.py` collection.

## Base/Candidate Exact Test Comparison

Command for both:

```text
/private/tmp/pantheon-safe-review.tJcnx1/.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py --tb=short
```

Base result: `41 failed, 155 passed in 200.06s`

Candidate result: `5 failed, 192 passed in 223.36s`

Candidate exact failures:

- `test_apf_004_single_create_only_adapter_plan_only_is_deterministic_and_zero_write`
- `test_apf_004_single_create_only_adapter_rejects_root_overlap_and_state_collision`
- `test_apf_004_create_run_adapter_plan_only_is_deterministic_and_zero_write`
- `test_apf_004_create_run_adapter_apply_is_idempotent_and_resume_safe`
- `test_apf_004_create_run_adapter_rejects_root_overlap_and_state_collision`

Base-only failures resolved by candidate:

- `test_four_lane_activation_failure_restores_previous_plists_and_loaded_state[0-ROLLBACK_COMPLETE]`
- `test_four_lane_activation_failure_restores_previous_plists_and_loaded_state[4-ROLLBACK_FAILED]`
- `test_four_lane_activation_success_commits_matching_private_stage`
- `test_gate2_activation_only_bootstraps_barrier_without_child_io`
- `test_activation_only_adopts_exact_legacy_capacity_guard`
- `test_activation_only_adopts_legacy_capacity_with_complete_inert_plist_set`
- `test_activation_only_inert_six_runs_real_barrier_exec_readiness`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[partial-set]`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[inert-label-loaded]`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[inert-symlink]`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[inert-owner]`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[inert-mode]`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[snapshot-hash-drift]`
- `test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation[snapshot-label-loaded]`
- `test_activation_only_inert_six_adoption_rollback_receipts[False-ROLLBACK_COMPLETE]`
- `test_activation_only_inert_six_adoption_rollback_receipts[True-ROLLBACK_FAILED]`
- `test_activation_only_inert_six_barrier_timeout_rollback_receipts[False-ROLLBACK_COMPLETE]`
- `test_activation_only_inert_six_barrier_timeout_rollback_receipts[True-ROLLBACK_FAILED]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[multi-loaded-label]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[business-plist-present]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[legacy-plist-missing]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[identity-path-drift]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[prefix-forged-path]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[duplicate-path]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[relative-path]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[noncanonical-path]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[symlink-alias]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[extra-whitespace-path]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[running-state]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[symlink-path]`
- `test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[snapshot-mode-invalid]`
- `test_activation_only_legacy_capacity_adoption_rollback_receipts[False-ROLLBACK_COMPLETE]`
- `test_activation_only_legacy_capacity_adoption_rollback_receipts[True-ROLLBACK_FAILED]`
- `test_normal_activate_rejects_legacy_capacity_adoption_authority_before_mutation`
- `test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement`
- `test_normal_activate_rejects_inert_six_adoption_authority_before_mutation`

New candidate failures relative to base: none.

## Residual Risks

- The remaining five coordinator failures are pre-existing APF create-run adapter backlog failures with shared reason `ValueError: create-run adapter new article is not in matrix backlog`; they are outside this card's safe activation boundary.
- The static review did not execute real LaunchAgent reload, production activation, production queue, publishing, tagging, or push by contract.
- The normal activation gate accepts a same-generation, same-manifest barrier as matching authority; this is consistent with the current contract and existing manifest authority, but it does not encode a separate one-time nonce.

## Review Evidence Path

`.work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-REVIEW-20260818/review/evidence.md`

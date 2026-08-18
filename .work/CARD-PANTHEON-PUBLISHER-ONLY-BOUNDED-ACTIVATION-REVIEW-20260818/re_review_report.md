# CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818 targeted re-review report

## Verdict

- Verdict: `RE-REVIEW_GO`
- Finding under review: `PANTHEON-PUBLISHER-ONLY-REVIEW-F001`
- Original candidate SHA: `482ae14d90d9b632e2cfa705e1fac00ffc3bc651`
- Original review evidence SHA: `e0cc146026e802d7415a03f41be5196afda22ea9`
- Repair candidate SHA: `1eb39f9c50a9308c742e576946d4c0c6d7930bf9`
- Production mutation count: `0`

## Scope

This re-review only checked F001, the Repair diff, and direct regressions around Publisher-only bounded activation. No general new findings were added.

CodeGraph status remained unavailable in this worktree: `CodeGraph not initialized in /Users/mattkuo/.codex/worktrees/91eb/Pantheon`; bounded `git diff`, `rg`, and targeted test execution were used.

## F001 Resolution

F001 is resolved.

Repair adds a stage receipt binding before any backup/install/bootout/bootstrap:

- `scripts/install_agy_gemini_coordinator_launchd.sh:424-435` reads `publisher-exact-run-id` when present and passes `--expected-exact-run-id`; when absent it passes `--require-no-exact-run-id`.
- `scripts/pantheon_content_runtime_manifest.py:452-495` validates the Publisher plist child args, enforces a single `--max-runs 1`, validates optional exact-run format, and fails on exact-run receipt mismatch.
- `tests/test_agy_gemini_coordinator.py:5617-5639` covers both-absent success.
- `tests/test_agy_gemini_coordinator.py:5642-5718` covers missing receipt, stale/extra receipt, value mismatch, empty receipt, max-runs, barrier, exact-run format, and plist drift fail-closed behavior with no fake launchctl mutation and unchanged live plists.

## Exact-Run State Matrix

- Matching exact receipt and plist: accepted; Publisher-only mutation limited to Publisher `bootout` and `bootstrap`; other six service plists unchanged.
- Both absent: accepted; Publisher-only mutation occurs without exact selector, as expected for non-exact bounded single-run mode.
- Missing receipt with exact plist: rejected in `publisher_only_stage_validation`; zero mutation.
- Extra/stale receipt with no exact plist: rejected with `publisher plist exact-run-id receipt mismatch`; zero mutation.
- Receipt/plist value mismatch: rejected in `publisher_only_stage_validation`; zero mutation.
- Empty receipt: rejected in `publisher_only_stage_validation`; zero mutation.

The original stale receipt repro now fails closed:

```text
returncode=1
stdout={"error": "publisher plist exact-run-id receipt mismatch", "status": "NO-GO"}
mutation_log_exists=false
mutations=[]
```

## Verification

Commands run on repair candidate `1eb39f9c50a9308c742e576946d4c0c6d7930bf9`:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k publisher_only_bounded_activation -q
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_replaces_only_publisher tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_fails_closed_before_mutation tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation -q
.venv/bin/python .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/reproduce_stale_exact_receipt.py
.venv/bin/python -m pytest tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py -q
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
git diff --check
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_four_lane_installer_separates_stage_and_activation_with_rollback tests/test_agy_gemini_coordinator.py::test_four_lane_activation_failure_restores_previous_plists_and_loaded_state tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_adoption_rollback_receipts tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_barrier_timeout_rollback_receipts tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_rollback_receipts -q
```

Results:

- Publisher-only F001 suite: `10 passed, 197 deselected`.
- Affected coordinator subset: `13 passed`.
- Original stale receipt repro: failed closed with returncode `1`, zero mutation.
- Publisher installer subset: `3 passed`.
- Runtime manifest suite: `48 passed`.
- Shell syntax: both installer scripts passed `bash -n`.
- `git diff --check`: passed.
- Full coordinator suite: `202 passed, 5 failed`. The five failures are the pre-existing APF-004 create-run adapter backlog on missing `ASTRO-SCENARIO-BIG-THREE`; no Publisher-only or repair-regression failures appeared.
- Rollback regression subset: `9 passed`.

## Residual Risks

- Full coordinator suite still has the pre-existing APF-004 backlog failures unrelated to F001 repair.
- Production canary must still independently verify real launchctl identity and no mutation of the other six services before any live activation.

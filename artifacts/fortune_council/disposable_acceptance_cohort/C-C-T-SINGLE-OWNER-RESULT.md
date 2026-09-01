# C-C/T Single Workload Owner Architecture Root Result

Status: `CANDIDATE_READY_FOR_INDEPENDENT_REVIEW`

## Scope

- Worktree: `<local-only-worktree>`; actual local execution path was `/private/tmp/pantheon-cct-single-owner-20260901.wFYyq6/worktree` (`LOCAL_ONLY_WORKTREE_PATH`, not a cross-machine command path).
- Test runner: `<repo-root>/.venv/bin/python`; actual local execution path was `/Users/mattkuo/Documents/Pantheon/.venv/bin/python` (`LOCAL_ONLY_EXECUTION_PATH`).
- Card: `CARD-PANTHEON-C-C-T-SINGLE-WORKLOAD-OWNER-ARCHITECTURE-ROOT-20260901.md`
- Allowed implementation files changed:
  - `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`
  - `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
- Evidence files changed:
  - `artifacts/fortune_council/disposable_acceptance_cohort/CARD-PANTHEON-C-C-T-SINGLE-WORKLOAD-OWNER-ARCHITECTURE-ROOT-20260901.md`
  - `artifacts/fortune_council/disposable_acceptance_cohort/C-C-T-SINGLE-OWNER-RESULT.md`
  - `artifacts/fortune_council/disposable_acceptance_cohort/c-c-t-single-owner-raw-test-output.txt`

## RED → GREEN summary

- `CCT-AR-P1-HOME-AUTHORITY`: RED proved `PRODUCTION_LAUNCH_PLIST_ROOT` followed forged `HOME`; GREEN derives production home from OS UID record via `pwd.getpwuid(os.getuid()).pw_dir`.
- `CCT-AR-P1-DUAL-WORKLOAD-OWNER`: RED proved public `run_once()` could observe launchd child execution and Controller direct owner subprocess execution for the same step; GREEN makes Controller use immutable schedule-derived acceptance-local step plists and read owner stdout plus authoritative owner artifacts.
- Mainline re-review P1: RED proved immediate stdout read-back failed under async launchd behavior; GREEN adds bounded wait and timeout fail-closed.
- Mainline re-review P1: RED proved preexisting `steps` symlink could defer failure until after unsafe path handling; GREEN creates each step root with `exist_ok=False`, validates canonical acceptance descendant, and blocks before step launchctl mutation.
- Internal read-only pre-freeze review: `GO`. This is a Mainline internal pre-freeze read-only judgment, not external `C-C_T_REVIEW_GO`.

## Verification

- Focused C-C/T:
  - Command: `<repo-root>/.venv/bin/python -m pytest tests/test_pantheon_four_lane_disposable_acceptance_cohort.py -q`
  - Result: `32 passed in 11.90s`
- Runtime/Runner affected:
  - Command: `<repo-root>/.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_agy_gemini_runner.py -q`
  - Result: `118 passed in 15.74s`
- Coordinator targeted:
  - Command: `<repo-root>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_never_advances_unlisted_active_run tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_processed_runner_keeps_unlisted_run_unchanged tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_reject_duplicates_before_advancing tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_continue_after_one_selected_run_is_terminal tests/test_agy_gemini_coordinator.py::test_lane_mode_advances_one_run_per_content_lane tests/test_agy_gemini_coordinator.py::test_lane_mode_continues_oldest_registered_run_until_terminal tests/test_agy_gemini_coordinator.py::test_lane_mode_migrates_shared_pending_jobs_by_run_namespace -q`
  - Result: `7 passed in 0.08s`
- Compile/diff:
  - Command: `<repo-root>/.venv/bin/python -m py_compile scripts/pantheon_four_lane_disposable_acceptance_cohort.py tests/test_pantheon_four_lane_disposable_acceptance_cohort.py && git diff --check && git status --short`
  - Result: exit code `0`

## Zero mutation proof

- No real `/bin/launchctl` execution was run; tests patch `_run_process`.
- No production/provider/Gate D/E/public publish/tag/deploy/commit/push was run.
- Publisher remains plan-only dry-run; tests assert real owner functions are called exactly once for new/rewrite and twice for translation lanes.

## Residual risks

- This is not `C-C_T_REVIEW_GO`; it is ready for independent review only.
- A prior broad coordinator aggregate showed two unrelated allowlist-outside failures in `test_same_generation_locale_plan_retry_rechecks_generation_boundary_inside_lock[...]`; those were not modified under this card.

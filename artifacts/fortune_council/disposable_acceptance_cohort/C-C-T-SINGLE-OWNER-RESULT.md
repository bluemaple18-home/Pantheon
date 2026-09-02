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

- Second-NO_GO Repair RCA:
  - C-C/T cohort has no known successful version.
  - Known-good seams are shared `barrier-exec` ACK → barrier → activation-only completion and `scripts/pantheon_runtime_fs_authority.py` dirfd/no-follow authority.
  - Fault origins: public callbacks from `7821adb`/`b5d` formal API lineage; immediate baseline bootout and step parent path handling from `97e` candidate lineage.
  - Durable invariant: formal Controller only owns wait primitives, must collect 7/7 post-barrier PASS completions before bootout, and must perform step filesystem operations under pinned/non-symlink acceptance authority before any mutation.
- `CCT-AR-P1-HOME-AUTHORITY`: RED proved `PRODUCTION_LAUNCH_PLIST_ROOT` followed forged `HOME`; GREEN derives production home from OS UID record via `pwd.getpwuid(os.getuid()).pw_dir`.
- `CCT-AR-P1-DUAL-WORKLOAD-OWNER`: RED proved public `run_once()` could observe launchd child execution and Controller direct owner subprocess execution for the same step; GREEN makes Controller use immutable schedule-derived acceptance-local step plists and read owner stdout plus authoritative owner artifacts.
- Mainline re-review P1: RED proved immediate stdout read-back failed under async launchd behavior; GREEN adds bounded wait and timeout fail-closed.
- Mainline re-review P1: RED proved preexisting `steps` symlink could defer failure until after unsafe path handling; GREEN creates each step root with `exist_ok=False`, validates canonical acceptance descendant, and blocks before step launchctl mutation.
- External finding `CCT-AR-P1-PREACTIVATION-TOKEN-DEADLOCK`: RED proved a baseline plist that pre-injects a nonexistent activation token causes true `barrier-exec` to return `78` before ACK; GREEN removes activation token from baseline activation-only plist env and keeps token only for post-activation step plists.
- P2-1 alternate executor: RED proved old `_execute_schedule()` could still try direct owner workload execution; GREEN makes it fail closed with `direct workload schedule is disabled; launchd step ownership required`.
- P2-2 Capacity Guard residual: non-blocking. C-C/T four-lane single workload owner scope only requires Capacity Guard readiness operability; full seven-service runtime acceptance child operability awaits Owner/Gate D/E decision.
- Second-NO_GO `CCT-AR-P1-PUBLIC-WAIT-CALLBACK-OWNER-INJECTION`: RED proved public `run_once(..., monotonic/sleep=...)` still entered formal launch path instead of TypeError; GREEN removes public wait callback parameters and routes internal waits through private `_monotonic()` / `_sleep()`.
- Second-NO_GO `CCT-AR-P1-SEVEN-SERVICE-POST-BARRIER-AUTHORITY-INCOMPLETE`: RED proved missing/wrong-label/wrong-digest/not-PASS baseline activation completion did not block PASS; GREEN adds baseline StandardOut/Error paths and requires 7/7 exact post-barrier activation-only PASS before baseline bootout.
- Second-NO_GO `CCT-AR-P1-STEP-PARENT-SYMLINK-PATH-ESCAPE`: RED proved generation parent symlink/external, inode replacement, and production symlink could escape before blocking; GREEN pins generation directory identity and uses existing `TrustedSandboxDirectoryAuthority`/`path_identity` dirfd no-follow relative creation/write.
- P2-1 safe integration: added test that executes the full step plist outer `barrier-exec` ProgramArguments with a no-side-effect child stub after barrier activation, proving token/barrier/python identity and `os.exec` handoff behavior without real launchctl.
- Internal zero-write A: RED proved preseeded and prebarrier exact baseline PASS stdout could pass baseline authority; GREEN rejects any pre-launch baseline stdout/stderr and requires post-barrier canonical owner-safe regular stdout/stderr with ctime/mtime after the barrier.
- Internal zero-write B: RED proved mutable `rendered['plist_generation_identity']` could be forged after replacing the generation root; GREEN removes rendered identity from formal authority and passes a `run_once`-captured local generation identity into schedule/step helpers.
- Internal zero-write C: RED proved step failure cleanup followed a generation symlink and deleted an external allowed filename; GREEN uses pinned identity plus `TrustedSandboxDirectoryAuthority` no-follow relative cleanup and records residue on identity drift instead of following.
- Follow-up stderr timing: RED proved a real launchd-shaped service that creates empty stderr before barrier and writes stdout after barrier was incorrectly rejected; GREEN requires only stdout ctime/mtime after barrier while keeping stderr canonical owner-safe regular and exact empty.
- Follow-up broken symlink absence: RED proved a broken baseline output symlink bypassed `Path.exists()` prelaunch absence; GREEN uses `fs_authority.path_identity()` lstat semantics so any regular/symlink/broken symlink/other prelaunch output fails closed.
- Internal read-only pre-freeze review: `GO`. This is a Mainline internal pre-freeze read-only judgment, not external `C-C_T_REVIEW_GO`.

## Minimum sufficient closeout

- why_not_less: Changing tests alone would not prove the true `barrier-exec` pre-activation invariant, and changing `_env()` alone would still leave `_execute_schedule()` as a reconnectable direct workload path.
- why_not_more: No shared runtime, owner modules, production plist/installer, Gate D/E, provider, public publish, or capacity-workload expansion was needed for this bounded finding.
- do_not_absorb: Capacity Guard child operability beyond readiness remains outside this C-C/T four-lane single-owner repair and should be decided by Owner/Gate D/E.

## Verification

- Focused C-C/T:
  - Command: `<repo-root>/.venv/bin/python -m pytest tests/test_pantheon_four_lane_disposable_acceptance_cohort.py -q`
  - Result: `50 passed in 29.81s`
- Runtime/Runner affected:
  - Command: `<repo-root>/.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_agy_gemini_runner.py -q`
  - Result: `118 passed in 16.33s`
- Coordinator targeted:
  - Command: `<repo-root>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_never_advances_unlisted_active_run tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_processed_runner_keeps_unlisted_run_unchanged tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_reject_duplicates_before_advancing tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_continue_after_one_selected_run_is_terminal tests/test_agy_gemini_coordinator.py::test_lane_mode_advances_one_run_per_content_lane tests/test_agy_gemini_coordinator.py::test_lane_mode_continues_oldest_registered_run_until_terminal tests/test_agy_gemini_coordinator.py::test_lane_mode_migrates_shared_pending_jobs_by_run_namespace -q`
  - Result: `7 passed in 0.08s`
- Compile/diff:
  - Command: `<repo-root>/.venv/bin/python -m py_compile scripts/pantheon_four_lane_disposable_acceptance_cohort.py tests/test_pantheon_four_lane_disposable_acceptance_cohort.py && git diff --check && git status --short`
  - Result: exit code `0`
- DBG scan:
  - Command: `rg -n "breakpoint\\(|pdb\\.|TODO-DBG|DEBUG|DBG|print\\(" scripts/pantheon_four_lane_disposable_acceptance_cohort.py tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
  - Result: no debugger/debug residue; hits are legitimate test child snippets and `production_fingerprint` symbol name.

## Zero mutation proof

- No real `/bin/launchctl` execution was run; tests patch `_run_process`.
- No production/provider/Gate D/E/public publish/tag/deploy/commit/push was run.
- Publisher remains plan-only dry-run; tests assert real owner functions are called exactly once for new/rewrite and twice for translation lanes.

## Residual risks

- This is not `C-C_T_REVIEW_GO`; it is ready for independent review only.
- A prior broad coordinator aggregate showed two unrelated allowlist-outside failures in `test_same_generation_locale_plan_retry_rechecks_generation_boundary_inside_lock[...]`; those were not modified under this card.

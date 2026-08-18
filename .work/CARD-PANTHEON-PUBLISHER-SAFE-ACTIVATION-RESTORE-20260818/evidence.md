# CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818 Evidence

## Scope

- Changed files:
  - `scripts/install_agy_gemini_coordinator_launchd.sh`
  - `tests/test_agy_gemini_coordinator.py`
- Production mutations: `0`
- No production activation, reload, publish, tag, push, queue, registry, sitemap, article, or transaction mutation was run.

## RED

- Command: `uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation -q`
- Pre-fix result: failed as expected.
- Failure signal: old normal `--activate` returned `0` even when the matching activation barrier did not exist before bootstrap, so the new test caught the unsafe direct normal activation path.

## GREEN

- Command: `uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation -q`
- Result: `1 passed in 2.96s`
- Acceptance mapping:
  - Missing normal transition barrier fails closed before launchctl mutation.
  - Publisher barrier-before-child marker remains absent.
  - Failure receipt phase is `normal_transition_barrier_validation`.

## Affected Tests

- Command: `uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py::test_four_lane_activation_failure_restores_previous_plists_and_loaded_state tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_runs_real_barrier_exec_readiness -q`
- Result: `6 passed in 20.93s`

- Command: `uv run --frozen python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_agy_content_publisher.py -q`
- Result: `181 passed, 1 warning in 15.68s`
- Warning: existing `SyntaxWarning: invalid escape sequence '\/'` in publisher test collection.

- Command: `uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q`
- Result: `5 failed, 192 passed in 220.56s`
- Residual failures are outside this card's permitted scope:
  - `test_apf_004_single_create_only_adapter_plan_only_is_deterministic_and_zero_write`
  - `test_apf_004_single_create_only_adapter_rejects_root_overlap_and_state_collision`
  - `test_apf_004_create_run_adapter_plan_only_is_deterministic_and_zero_write`
  - `test_apf_004_create_run_adapter_apply_is_idempotent_and_resume_safe`
  - `test_apf_004_create_run_adapter_rejects_root_overlap_and_state_collision`
- Shared failure reason: `ValueError: create-run adapter new article is not in matrix backlog`.

## Static Checks

- Command: `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`
- Result: passed.
- Command: `git diff --check`
- Result: passed.
- Command: `rg -n "\[DBG-" scripts/install_agy_gemini_coordinator_launchd.sh tests/test_agy_gemini_coordinator.py`
- Result: no debug instrumentation found.

## Implementation Note

Normal `--activate` now validates the existing matching activation barrier before live plist replacement, and only activation-only removes/rebuilds the barrier. This keeps the transition on the existing `--activate-only` plus aggregate/barrier contract and avoids adding a second activation engine.

# CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818 evidence

## Scope

- Status: DELIVERED_CANDIDATE
- Production mutations: 0
- Formal thread: 01a0139a-7a39-7f71-a8f0-49417620fad3
- Source SHA: 1db9b8a1edd689e5c8cfecc407f51d6da8351cd5
- Activation token: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818-G1

## RED

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_replaces_only_publisher tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_fails_closed_before_mutation -q
```

Result before implementation:

```text
4 failed
```

Observed failure: `scripts/install_agy_gemini_coordinator_launchd.sh` rejected `--activate-publisher-only` with usage error.

## GREEN

Commands:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_replaces_only_publisher tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_fails_closed_before_mutation -q
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_replaces_only_publisher tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_fails_closed_before_mutation tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation -q
.venv/bin/python -m pytest tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py -q
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
git diff --check
```

Results:

```text
Publisher-only contract: 5 passed
Coordinator affected subset: 9 passed
Publisher installer subset: 3 passed
Runtime manifest: 48 passed
bash -n: passed
git diff --check: passed
```

## Negative Matrix

- Missing matching activation barrier: rejected in `publisher_only_barrier_validation`; launchctl mutation log absent.
- Staged `publisher-max-runs` not equal to `1`: rejected in `publisher_only_stage_validation`; launchctl mutation log absent.
- Invalid `--exact-run-id`: rejected in `publisher_only_stage_validation`; launchctl mutation log absent.
- Staged Publisher plist manifest drift: rejected in `publisher_only_stage_validation`; launchctl mutation log absent.
- Live aggregate activation-only drift is checked by existing runtime aggregate preflight before Publisher mutation.

## Regression Note

Full command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q
```

Result:

```text
196 passed, 5 failed
```

The five failures are APF-004 create-run adapter tests failing because `ASTRO-SCENARIO-BIG-THREE` is absent from the current matrix backlog. They do not execute the modified launchd installer/runtime Publisher-only path.

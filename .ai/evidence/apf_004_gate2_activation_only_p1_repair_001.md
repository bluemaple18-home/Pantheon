# APF-004-GATE2-ACTIVATION-ONLY-P1-REPAIR-001 Evidence

## 結論

- 狀態：LOCAL REPAIR / NO LIVE MUTATION
- base：de13ef0de5d122cbe66831ede20b4a62cc6e37a1
- prior candidate：52ef3394f62d77dcec3983011bd9cf3fb07a85ab
- mutation_executed：false
- live_mutation_executed：false
- activation_executed：false

## Source decision

CodeGraph was checked first.

Result:

```text
CodeGraph not initialized in <repo-root>.
```

Fallback used bounded `rg` over:

- scripts/pantheon_content_runtime_manifest.py
- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- tests/test_pantheon_content_runtime_manifest.py

## RED

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation
```

Before fix:

```text
FAILED tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation
AssertionError: assert not True
where True = mutation_log.exists()
```

Acceptance meaning:

- normal `--activate` accepted a staged plist containing barrier-side `--activation-only`.
- aggregate preflight did not fail closed.
- fake launchctl mutation log existed, violating the reviewer edge.

## Fix

Changed only allowlist source and direct tests:

- `plist_receipt()` now accepts `expected_activation_mode`.
- `aggregate_plist_preflight()` now passes expected activation mode into plist validation.
- aggregate CLI now accepts `--activation-mode normal|activation-only`.
- normal aggregate preflight rejects barrier-side `--activation-only`.
- activation-only live post-check allows and requires the injected token.
- coordinator installer passes explicit mode for staged preflight and live post-check.

## GREEN

### P1 edge

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation
```

Result:

```text
1 passed in 3.11s
```

Evidence mapping:

- returncode non-zero.
- fake launchctl mutation log absent.
- no live fixture target plist created.
- failure receipt existed.
- receipt status：`ACTIVATION_REJECTED`
- receipt phase：`aggregate_preflight`
- receipt correlation：`apf-004-normal-rejects-ao`

### Targeted coordinator regression

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io
```

Result:

```text
2 passed in 6.19s
```

### Targeted runtime aggregate mode regression

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_hardened_aggregate_rejects_activation_only_token_in_normal_mode tests/test_pantheon_content_runtime_manifest.py::test_hardened_aggregate_accepts_activation_only_token_only_when_expected
```

Result:

```text
2 passed in 0.21s
```

### Activation-only / legacy / normal regression

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_four_lane_activation_failure_restores_previous_plists_and_loaded_state
```

Result:

```text
5 passed in 16.00s
```

### Runtime manifest targeted

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_hardened_aggregate_rejects_activation_only_token_in_normal_mode tests/test_pantheon_content_runtime_manifest.py::test_hardened_aggregate_accepts_activation_only_token_only_when_expected tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_activation_only_acknowledges_without_child_exec
```

Result:

```text
3 passed in 0.23s
```

### Runtime manifest suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
42 passed in 2.25s
```

### Affected coordinator suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or normal_activate'
```

Result:

```text
31 passed, 113 deselected in 57.86s
```

## Final gates

### bash-n

Commands:

```bash
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
```

Result：PASS

### DBG scan

Command:

```bash
rg -n '<debug-marker-pattern>' <allowlist>
```

Result：PASS, no matches.

### Added-line secret scan

Command:

```bash
git diff --unified=0 -- <allowlist> | rg -n '<secret-pattern>'
```

Result：PASS, no matches.

### Added-line path scan

Command:

```bash
git diff --unified=0 -- <allowlist> | rg -n '<absolute-path-pattern>'
```

Result：REVIEWED PASS.

Matches were limited to test fixture command paths:

- `/bin/bash`

No user live absolute path was added.

### Binary scan

Command:

```bash
file <allowlist>
```

Result：PASS. All allowlist files are text or text executable.

### Diff check

Command:

```bash
git diff --check
```

Result：PASS

# APF-004-GATE2-ACTIVATION-ONLY-REPAIR-001 Evidence

## 結論

- 狀態：REPAIR_READY_FOR_REVIEW
- branch：codex/apf-004-gate2-activation-only-repair
- base：de13ef0de5d122cbe66831ede20b4a62cc6e37a1
- mutation_executed：false
- live_mutation_executed：false
- activation_executed：false

## Scope

Allowlist changes:

- scripts/pantheon_content_runtime_manifest.py
- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- tests/test_pantheon_content_runtime_manifest.py
- .ai/codex_task_apf_004_gate2_activation_only_repair_20260814.md
- .ai/evidence/apf_004_gate2_activation_only_repair_001.md

No live install / activate / launchctl mutation was executed.

## Source decision

CodeGraph was checked before source changes. Result: CodeGraph was not initialized for this repository, so bounded `rg` fallback was used for:

- `--activate`
- `barrier-exec`
- `failure-receipt`
- direct coordinator installer tests
- runtime manifest helper tests

## RED evidence

### RED 1: activation-only public entry missing

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io
```

Observed before fix:

- returncode：1
- fixture stderr included installer usage for `[--preflight|--install|--activate]`
- cause：`--activate-only` was not a supported public action

### RED 2: legacy prior-loaded service rejected too late

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement
```

Observed before fix:

- returncode：1
- fixture live plist bytes changed before rejection
- expected behavior：reject before first live replacement when previous barrier is missing and a prior-loaded service exists

## GREEN evidence

### Activation-only child I/O stays zero

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io
```

Result:

```text
1 passed in 4.13s
```

Acceptance evidence:

- `--activate-only` returned success in private fixture.
- seven service labels were loaded in fake launchctl state.
- staged readiness acknowledgements were copied to activation ready root.
- fixture child I/O marker was absent.
- each live fixture plist had exactly one `--activation-only` before the child `--` separator.
- no child command received `--activation-only`.

### Legacy loaded without valid previous barrier rejects before mutation

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement
```

Result:

```text
1 passed in 3.14s
```

Acceptance evidence:

- activation returned non-zero.
- previous live fixture plist bytes remained unchanged.
- fake launchctl mutation log contained no `bootout` or `bootstrap`.
- `failure-receipt.json` existed in fixture stage.
- receipt status：`ACTIVATION_REJECTED`
- receipt correlation：`apf-004-legacy-barrier-red`
- receipt exit reason：`phase=previous_barrier_validation`, `exit_code=1`

### Runtime helper activation-only ack does not exec child

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_activation_only_acknowledges_without_child_exec
```

Result:

```text
1 passed in 0.06s
```

Acceptance evidence:

- `barrier-exec --activation-only` returned 0.
- stdout JSON included `activation_only=true`.
- readiness ack was written.
- child marker file was absent.

## Regression evidence

### Two RED→GREEN edge tests

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement
```

Result:

```text
2 passed in 6.12s
```

### Affected coordinator suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded'
```

Result:

```text
30 passed, 113 deselected in 61.06s (0:01:01)
```

### Normal-mode regression

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_four_lane_activation_failure_restores_previous_plists_and_loaded_state
```

Result:

```text
3 passed in 16.32s
```

### Runtime manifest suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
40 passed in 1.80s
```

## Static gates

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

### Secret scan

Command:

```bash
git diff --unified=0 -- <allowlist> | rg -n '^\+.*(SECRET|PASSWORD|TOKEN|API_KEY|PRIVATE_KEY|BEGIN [A-Z ]*PRIVATE KEY)'
```

Result：PASS, no added-line matches.

Full-file keyword scan found only existing runtime barrier token variable names:

- `PANTHEON_RUNTIME_ACTIVATION_TOKEN`

No secret values were present.

### Added-line path scan

Command:

```bash
git diff --unified=0 -- <allowlist> | rg -n '^\+.*(^|[^A-Za-z0-9_])/(Users|private|var|tmp|opt|usr|bin)(/|$)'
```

Result：REVIEWED PASS.

Matches were limited to repo-owned system binary references and private fixture scripts:

- `/usr/libexec/PlistBuddy`
- `/bin/bash`
- fixture `#!/bin/sh`

No user live absolute path was added.

### Binary scan

Command:

```bash
file <allowlist>
```

Result：PASS, all allowlist files are UTF-8 text or text executable.

### Diff check

Command:

```bash
git diff --check
```

Result：PASS

## Remaining live migration step

This commit does not execute live migration. After review/integration, live flow still requires an independent realignment stage/install confirmation gate, then a separate Gate 2 activation-only confirmation gate.

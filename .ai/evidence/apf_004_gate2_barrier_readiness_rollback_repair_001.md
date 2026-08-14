# APF-004-GATE2-BARRIER-READINESS-ROLLBACK-REPAIR-001 Evidence

## 結論

- status：REPAIR_READY
- base：a153219f919f965821dd7ee15d23a01f0469133f
- branch：codex/apf-004-gate2-barrier-readiness-rollback-repair
- mutation_executed：false
- live_mutation_executed：false
- production_mutation_executed：false
- activation_executed：false

## Pre-check

Commands:

```bash
git status --short --branch
git fetch origin main
git rev-parse origin/main
git rev-parse FETCH_HEAD
git switch -c codex/apf-004-gate2-barrier-readiness-rollback-repair a153219f919f965821dd7ee15d23a01f0469133f
```

Result:

- initial worktree：clean
- `origin/main`：a153219f919f965821dd7ee15d23a01f0469133f
- `FETCH_HEAD`：a153219f919f965821dd7ee15d23a01f0469133f
- repair branch：codex/apf-004-gate2-barrier-readiness-rollback-repair

## Source decision

CodeGraph was checked before source reads.

Result:

```text
CodeGraph not initialized in <repo-root>.
```

Fallback bounded reads:

- scripts/pantheon_content_runtime_manifest.py
- scripts/pantheon_runtime_activation.py
- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_pantheon_content_runtime_manifest.py
- tests/test_agy_gemini_coordinator.py

## RED evidence

### RED 1：activation-only barrier-exec no pre-existing token

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_activation_only_acknowledges_without_preexisting_token
```

Before fix:

```text
FAILED tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_activation_only_acknowledges_without_preexisting_token
AssertionError: assert False
```

Acceptance mapping:

- true `barrier-exec --activation-only` ran.
- no pre-existing `PANTHEON_RUNTIME_ACTIVATION_TOKEN`.
- readiness ack was not written before process returned through old 78 path.
- child marker was absent.

### RED 2：normal child token propagation

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_normal_propagates_activation_token_to_child
```

Before fix:

```text
FAILED tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_normal_propagates_activation_token_to_child
assert 78 == 0
```

Acceptance mapping:

- barrier already existed and was valid.
- no pre-existing token in env.
- child did not receive `PANTHEON_RUNTIME_ACTIVATION_TOKEN`; command returned 78 before exec.

## Fix evidence

Changed files:

- scripts/pantheon_content_runtime_manifest.py
- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_pantheon_content_runtime_manifest.py
- tests/test_agy_gemini_coordinator.py
- .ai/codex_task_apf_004_gate2_barrier_readiness_rollback_repair_20260814.md
- .ai/evidence/apf_004_gate2_barrier_readiness_rollback_repair_001.md

Implementation facts:

- `validate_runtime_tick(..., require_activation_token=True)` preserves existing token gate by default.
- `barrier-exec` pre-barrier path calls `validate_runtime_tick(..., require_activation_token=False)`.
- pre-barrier path still validates formal runtime manifest/env/path identity and child python identity before ack.
- post-barrier path validates exact barrier before setting child env token.
- activation-only returns after barrier validation and does not exec child.
- normal path sets `PANTHEON_RUNTIME_ACTIVATION_TOKEN` to the absolute barrier path before `os.execv()`.
- installer rollback receipt now includes sanitized `rollback_check_ids`.
- test-only barrier timeout env is bounded to 1..300 and production default remains 90.

## GREEN evidence

### Runtime barrier slice

Command:

```bash
.venv/bin/python -m pytest -q \
  tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_activation_only_acknowledges_without_preexisting_token \
  tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_normal_propagates_activation_token_to_child \
  tests/test_pantheon_content_runtime_manifest.py::test_early_service_acknowledges_but_cannot_run_before_barrier \
  tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_rejects_runtime_python_drift_before_ack_or_exec \
  tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_rejects_child_python_drift_before_ack_or_exec
```

Result:

```text
5 passed in 1.52s
```

### Runtime manifest suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
44 passed in 3.42s
```

### Runtime activation suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_runtime_activation.py
```

Result:

```text
6 passed in 0.04s
```

### Seven real readiness integration

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_runs_real_barrier_exec_readiness
```

Result:

```text
1 passed in 4.20s
```

Acceptance mapping:

- fake launchctl did not copy readiness files.
- each bootstrap spawned the staged plist ProgramArguments, invoking repo-owned `barrier-exec`.
- seven `barrier-exec` processes wrote readiness and activation barrier validated.
- activation-only did not exec child marker.

### Barrier timeout rollback receipts

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_barrier_timeout_rollback_receipts
```

Result:

```text
2 passed in 8.70s
```

Acceptance mapping:

- barrier timeout failure phase：`barrier_activation`
- rollback complete restored seven plist bytes and reloaded only previous capacity.
- forced rollback failure receipt included `rollback.bootstrap`.

### Targeted Gate2 matrix

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::<targeted-gate2-tests>
```

Result:

```text
37 passed in 107.82s (0:01:47)
```

Included:

- real barrier readiness integration
- timeout rollback complete / forced failed
- inert-six positive
- original capacity-only positive
- inert-six negatives
- capacity existing 13 negatives
- inert-six rollback receipts
- capacity rollback receipts
- inert-six normal isolation
- capacity normal isolation
- prior normal activation-only P1
- activation-only child I/O zero
- prior legacy negative
- normal success
- normal rollback

### Affected coordinator suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or legacy_capacity or inert_six or normal_activate or barrier_timeout or real_barrier'
```

Result:

```text
62 passed, 113 deselected in 135.63s (0:02:15)
```

## Final gates

Initial commands:

```bash
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
```

Initial results:

- coordinator installer syntax：PASS
- publisher installer syntax：PASS
- capacity guard installer syntax：PASS
- `git diff --check`：PASS

Final commands after evidence write:

```bash
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
rg -n '<debug-marker-pattern>' <allowlist>
rg -n '<secret-patterns>' <allowlist>
git diff --numstat -- <allowlist>
```

Final results:

- coordinator installer syntax：PASS
- publisher installer syntax：PASS
- capacity guard installer syntax：PASS
- `git diff --check`：PASS
- debug marker scan：PASS（no hits）
- secret pattern scan：PASS（no hits）
- binary scan：PASS（numstat shows text deltas only）

Numstat before staging:

```text
48	17	scripts/install_agy_gemini_coordinator_launchd.sh
5	0	scripts/pantheon_content_runtime_manifest.py
274	0	tests/test_agy_gemini_coordinator.py
154	3	tests/test_pantheon_content_runtime_manifest.py
```

## Remaining risk

- Barrier timeout rollback fixture uses bounded test-only timeout env; production default remains 90 seconds.
- Real-readiness integration uses fake launchctl for loaded-state simulation, but readiness is generated by actual repo-owned `barrier-exec`.
- No integration or production readiness is claimed.

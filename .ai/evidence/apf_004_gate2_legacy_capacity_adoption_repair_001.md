# APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-REPAIR-001 Evidence

## 結論

- status：REPAIR_READY
- base：e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0
- branch：codex/apf-004-gate2-legacy-capacity-adoption-repair
- mutation_executed：false
- live_mutation_executed：false
- activation_executed：false

## Source decision

Mainline CodeGraph query was reported as no relevant shell seam. This repair used bounded source reads over coordinator installer and direct tests only.

## RED evidence

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
```

Result before fix:

```text
FAILED tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
AssertionError: legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。
```

Acceptance meaning:

- fixture state had only legacy `com.pantheon.content-capacity-guard` loaded.
- six non-capacity labels were absent.
- legacy live plist existed.
- loaded identity was readable and non-running.
- current code still rejected in `previous_barrier_validation`.

## Fix evidence

Changed files:

- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- .ai/codex_task_apf_004_gate2_legacy_capacity_adoption_repair_20260814.md
- .ai/evidence/apf_004_gate2_legacy_capacity_adoption_repair_001.md

Runtime manifest helper was read and tested but not modified.

Implementation facts:

- adoption marker is generated only for `--activate-only`.
- marker requires capacity-only prior-loaded state.
- marker requires non-capacity labels absent and no non-capacity live plist backups.
- marker requires capacity target regular file, non-symlink, owner=current user, mode 0600.
- marker requires snapshot backup bytes equal live target bytes.
- marker requires loaded identity path to match capacity target.
- marker rejects `state = running`.
- rollback without previous barrier remains rejected unless adoption marker exists.

## GREEN evidence

### Positive adoption

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
```

Result:

```text
1 passed in 3.20s
```

Acceptance mapping:

- `--activate-only` returned 0.
- activation barrier validated PASS.
- stage dir removed after success.
- child I/O marker absent.
- fake mutation log showed one legacy capacity bootout and seven bootstraps.

### Zero-write negative matrix

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation
```

Result:

```text
7 passed in 19.10s
```

Covered cases:

- multi loaded label
- business plist present
- legacy plist missing
- loaded identity path drift
- running state
- symlink path
- snapshot mode invalid

Acceptance mapping:

- all cases failed closed before mutation.
- fake launchctl mutation log absent.
- receipts were `ACTIVATION_REJECTED`.
- receipt phase was `previous_barrier_validation`.

### Rollback receipts

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_rollback_receipts
```

Result:

```text
2 passed in 5.51s
```

Acceptance mapping:

- bootstrap failure after adoption triggered rollback.
- rollback success restored exact legacy capacity plist bytes and loaded state.
- rollback failure emitted `ROLLBACK_FAILED`.
- receipt phase was `bootstrap_staged_services`.

### Normal authority isolation

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_legacy_capacity_adoption_authority_before_mutation
```

Result:

```text
1 passed in 3.07s
```

Acceptance mapping:

- normal `--activate` rejected exact legacy capacity-only state.
- fake launchctl mutation log absent.
- receipt status was `ACTIVATION_REJECTED`.

### Targeted regression

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::<new-and-existing-targeted-tests>
```

Result:

```text
17 passed in 48.32s
```

Included:

- positive adoption
- zero-write negatives
- rollback receipts
- normal authority isolation
- normal staged activation-only P1
- activation-only child I/O zero
- legacy multi-loaded negative
- normal success
- normal rollback

### Runtime manifest suite

Command:

```bash
<venv-python> -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
42 passed in 2.02s
```

### Affected coordinator suite

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or legacy_capacity or normal_activate'
```

Result:

```text
42 passed, 113 deselected in 76.58s (0:01:16)
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

Matches were limited to test fixture/system binary references:

- fixture shell shebangs
- `/bin/bash`
- `/usr/libexec/PlistBuddy`

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

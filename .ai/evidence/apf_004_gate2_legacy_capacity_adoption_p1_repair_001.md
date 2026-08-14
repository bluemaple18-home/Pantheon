# APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-P1-REPAIR-001 Evidence

## 結論

- status：REPAIR_READY_FOR_REREVIEW
- parent candidate：f614bea8f22663bd40dcee0f5e921d788d679a4e
- branch：codex/apf-004-gate2-legacy-capacity-adoption-repair
- mutation_executed：false
- live_mutation_executed：false
- activation_executed：false

## Source decision

CodeGraph was checked first for this repair worktree.

Result:

```text
CodeGraph not initialized in <repair-worktree>.
```

Fallback used bounded reads over:

- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py

## RED evidence

Command:

```bash
<venv-python> -m pytest -q 'tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[prefix-forged-path]'
```

Before fix:

```text
FAILED tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[prefix-forged-path]
AssertionError: assert not True
where True = mutation_log.exists()
```

Acceptance meaning:

- fake `launchctl print` returned `path = <CAPACITY_TARGET>.forged`.
- adoption path incorrectly accepted the forged path.
- fake launchctl mutation log existed, proving first-mutation fail-closed was violated.

## Fix evidence

Changed files:

- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- .ai/codex_task_apf_004_gate2_legacy_capacity_adoption_p1_repair_20260814.md
- .ai/evidence/apf_004_gate2_legacy_capacity_adoption_p1_repair_001.md

Implementation facts:

- `launchctl print` path parsing now rejects missing path fields.
- Duplicate or ambiguous path assignments reject before adoption marker.
- The only accepted field format is strict `path = /absolute/path`.
- Extra whitespace rejects.
- Relative path rejects.
- Noncanonical path rejects.
- Symlink alias rejects.
- Prefix / suffix forged path rejects.
- Canonical loaded path must equal canonical capacity target path.
- Raw loaded path must also equal raw capacity target path.
- Checks run before adoption marker, replacement, bootout, or bootstrap.

## GREEN evidence

### Reviewer P1 exact cases

Command:

```bash
<venv-python> -m pytest -q 'tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[prefix-forged-path]' 'tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[duplicate-path]'
```

Result:

```text
2 passed in 6.49s
```

Acceptance mapping:

- forged prefix path rejected.
- duplicate path rejected.
- both cases kept fake launchctl mutation log absent.

### Full zero-write negative matrix

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation
```

Result:

```text
13 passed in 39.31s
```

Covered cases:

- multi loaded label
- business plist present
- legacy plist missing
- identity path drift
- prefix forged path
- duplicate path
- relative path
- noncanonical path
- symlink alias
- extra whitespace path
- running state
- symlink target path
- snapshot mode invalid

### Targeted regression

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py::<targeted-adoption-and-regression-tests>
```

Result:

```text
23 passed in 66.45s (0:01:06)
```

Included:

- positive adoption
- full negative matrix
- rollback success/failure receipts
- normal authority isolation
- prior normal activation-only P1
- activation-only child I/O zero
- prior legacy negative
- normal success
- normal rollback

### Runtime manifest suite

Command:

```bash
<venv-python> -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
42 passed in 2.03s
```

### Affected coordinator suite

Command:

```bash
<venv-python> -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or legacy_capacity or normal_activate'
```

Result:

```text
48 passed, 113 deselected in 96.47s (0:01:36)
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

Result：PASS, no matches.

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

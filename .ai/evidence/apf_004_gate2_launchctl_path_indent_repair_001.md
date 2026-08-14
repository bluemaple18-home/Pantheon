# APF-004-GATE2-LAUNCHCTL-PATH-INDENT-REPAIR-001 Evidence

## 結論

- status：REPAIR_READY
- base：2a073ad57e6799383236d743bcc0567f0a2d3d72
- branch：codex/apf-004-gate2-launchctl-path-indent-repair
- mutation_executed：false
- live_mutation_executed：false
- activation_executed：false

## Pre-check

Commands:

```bash
git status --short --branch
git fetch origin main
git rev-parse origin/main
git rev-parse FETCH_HEAD
```

Result:

- initial worktree：clean
- `origin/main`：`2a073ad57e6799383236d743bcc0567f0a2d3d72`
- `FETCH_HEAD`：`2a073ad57e6799383236d743bcc0567f0a2d3d72`
- repair branch：`codex/apf-004-gate2-launchctl-path-indent-repair`

## Source decision

CodeGraph was checked before source reads.

Result:

```text
CodeGraph not initialized in <repo-root>.
```

Fallback bounded reads:

- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py

## RED evidence

Positive fixture was changed first so fake `launchctl print` emitted a realistic indented path line:

```text
    path = <absolute-capacity-target>
```

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
```

Before fix:

```text
FAILED tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
AssertionError: legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。
```

Acceptance meaning:

- exact legacy capacity-only state was rejected at `previous_barrier_validation`.
- fake `launchctl` bootout/bootstrap mutation path was not reached.

## Fix evidence

Changed files:

- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- .ai/codex_task_apf_004_gate2_launchctl_path_indent_repair_20260814.md
- .ai/evidence/apf_004_gate2_launchctl_path_indent_repair_001.md

Implementation facts:

- strict path count now allows key-leading indentation.
- path extractor now allows key-leading indentation.
- `path = /absolute/path` spacing is still exact after optional indentation.
- value remains one absolute non-whitespace path.
- raw equality, canonical equality, target equality, owner/mode/hash/running checks are unchanged.

## GREEN evidence

### Exact positive

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_exact_legacy_capacity_guard
```

Result:

```text
1 passed in 2.96s
```

### 13 zero-mutation negatives

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation
```

Result:

```text
13 passed in 36.41s
```

### Rollback success/failure + normal authority isolation

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_rollback_receipts tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_legacy_capacity_adoption_authority_before_mutation
```

Result:

```text
3 passed in 9.45s
```

### Targeted regression

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::<targeted-gate2-tests>
```

Result:

```text
23 passed in 63.99s (0:01:03)
```

### Runtime manifest suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
42 passed in 2.12s
```

### Affected coordinator suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or legacy_capacity or normal_activate'
```

Result:

```text
48 passed, 113 deselected in 98.92s (0:01:38)
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

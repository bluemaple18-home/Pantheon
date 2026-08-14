# APF-004-GATE2-INERT-LIVE-PLIST-AUTHORITY-REPAIR-001 Evidence

## 結論

- status：REPAIR_READY
- base：d3f621d9849cfef1857b9765914243210ed12e79
- branch：codex/apf-004-gate2-inert-live-plist-authority-repair
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
git switch -c codex/apf-004-gate2-inert-live-plist-authority-repair d3f621d9849cfef1857b9765914243210ed12e79
```

Result:

- initial worktree：clean
- `origin/main`：d3f621d9849cfef1857b9765914243210ed12e79
- `FETCH_HEAD`：d3f621d9849cfef1857b9765914243210ed12e79
- repair branch：codex/apf-004-gate2-inert-live-plist-authority-repair

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

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_legacy_capacity_with_complete_inert_plist_set
```

Before fix:

```text
FAILED tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_legacy_capacity_with_complete_inert_plist_set
AssertionError: legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。
```

Acceptance mapping:

- exact inert-six state was rejected at `previous_barrier_validation`.
- fake launchctl mutation log was absent.
- business child I/O marker was absent.

## Fix evidence

Changed files:

- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- .ai/codex_task_apf_004_gate2_inert_live_plist_authority_repair_20260814.md
- .ai/evidence/apf_004_gate2_inert_live_plist_authority_repair_001.md

Implementation facts:

- original capacity-only authority remains.
- inert-six authority is separate and marked.
- partial inert backup set rejects.
- inert targets require regular non-symlink files, owner=current user, mode 600.
- inert target canonical path must equal expected live path.
- inert backup bytes must equal live target bytes at snapshot.
- replace-before check confirms six inert labels still unloaded.
- replace-before check confirms inert targets still exist, are not symlinks, and bytes/hash still match snapshot.
- normal `--activate` does not enter this authority.

## GREEN evidence

### Exact inert-six positive

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_adopts_legacy_capacity_with_complete_inert_plist_set
```

Result:

```text
1 passed in 3.33s
```

### Inert-six negatives

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation
```

Result:

```text
7 passed in 20.81s
```

Covered:

- partial set
- inert label loaded
- inert symlink
- inert owner mismatch via fixture stat shim
- inert mode mismatch
- snapshot-after hash drift
- snapshot-after label loaded

### Inert-six rollback receipts

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_adoption_rollback_receipts
```

Result:

```text
2 passed in 5.85s
```

Acceptance mapping:

- rollback restored seven original plist bytes.
- rollback success only reloaded snapshot-loaded capacity label.
- rollback failure emitted `ROLLBACK_FAILED`.

### Normal inert-six isolation

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_inert_six_adoption_authority_before_mutation
```

Result:

```text
1 passed in 2.68s
```

### Targeted set

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::<targeted-gate2-tests>
```

Result:

```text
34 passed in 94.38s (0:01:34)
```

Included:

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

### Runtime manifest suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py
```

Result:

```text
42 passed in 2.01s
```

### Affected coordinator suite

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or legacy_capacity or inert_six or normal_activate'
```

Result:

```text
59 passed, 113 deselected in 124.80s (0:02:04)
```

## Final gates

Commands:

```bash
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
rg -n '<debug-marker-pattern>' <allowlist>
rg -n '<secret-patterns>' <allowlist>
git diff --numstat -- <allowlist>
```

Results:

- coordinator installer syntax：PASS
- publisher installer syntax：PASS
- capacity guard installer syntax：PASS
- `git diff --check`：PASS
- debug marker scan：PASS（no hits）
- secret pattern scan：PASS（no hits）
- binary scan：PASS（numstat shows text deltas only）

Numstat:

```text
58	1	scripts/install_agy_gemini_coordinator_launchd.sh
463	3	tests/test_agy_gemini_coordinator.py
```

## Remaining risk

- Owner negative uses a fixture `stat` shim rather than privileged filesystem ownership changes.
- No integration or production readiness is claimed.

## Final gates

Pending before commit:

- three installer `bash -n`
- DBG scan
- added-line secret scan
- binary scan
- `git diff --check`
- `git show --check`

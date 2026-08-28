# Pantheon Acceptance B gen05 dangling registry guard RCA evidence

## Scope receipt

- Date: 2026-08-28
- Current HEAD: `61dfde5641`
- Handoff: `HANDOFF-PANTHEON-ACCEPTANCE-B-GEN05-DANGLING-REGISTRY-GUARD-20260828.md`
- RCA card status: `complete`; parent boundary evidence corrected the historical-good stopline.
- Production mutation: none
- Push / commit / tag / deploy / publish / resume / gen06 / planning provider: none
- CodeGraph: queried before source decision for `scripts/agy_gemini_coordinator.py` active integrity seam.

## Source localization

Current `scripts/agy_gemini_coordinator.py::_active_run_integrity_block` validates the current `identity_envelope`, then calls `_identity_envelope_from_brief(brief)`. For legacy `translate_existing` briefs with missing `lane`, `_identity_envelope_from_brief` raises `translate run lane is required for durable identity`; the active guard folds that into `active run registry is dangling`.

Focused current lines:

- `scripts/agy_gemini_coordinator.py:639` defines `_identity_envelope_from_brief(brief)`.
- `scripts/agy_gemini_coordinator.py:640-641` raises when `mode=translate_existing` and brief `lane` is missing.
- `scripts/agy_gemini_coordinator.py:2281-2284` validates state `identity_envelope` then recomputes identity from brief.
- `scripts/agy_gemini_coordinator.py:2288-2298` returns `active run registry is dangling` on `ValueError`.

Historical blame evidence:

- `git grep -n "expected_lane" ef934239c3 -- scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py`
  - `ef934239c3:scripts/agy_gemini_coordinator.py:642` had `expected_lane: str | None = None`.
  - `ef934239c3:scripts/agy_gemini_coordinator.py:2291` passed `expected_lane=str(envelope["lane"])`.
- `git blame -L 636,652 ef934239c3 -- scripts/agy_gemini_coordinator.py`
  - `ef934239c3:scripts/agy_gemini_coordinator.py:644-645` still raised `translate run lane is required for durable identity` before the `expected_lane` fallback.
- `git blame -L 2280,2295 ef934239c3 -- scripts/agy_gemini_coordinator.py`
  - `ef934239c3:scripts/agy_gemini_coordinator.py:2289-2292` passed `expected_lane=str(envelope["lane"])`.
- `git blame -L 636,645 e720f2ab41 -- scripts/agy_gemini_coordinator.py`
  - `e720f2ab41:scripts/agy_gemini_coordinator.py:639` changed `_identity_envelope_from_brief` to remove the `expected_lane` parameter.
- `git blame -L 2280,2290 e720f2ab41 -- scripts/agy_gemini_coordinator.py`
  - `e720f2ab41:scripts/agy_gemini_coordinator.py:2283` changed the active guard call to `_identity_envelope_from_brief(brief)`.

Formation correction:

- The handoff claim that `e720f2ab41` was the first failing commit is corrected.
- Executable evidence shows the last successful version is `75466a1bab5c0cd278ccbe44730bb9b058d79244` (`ef934239c3^`).
- Executable evidence shows the first failing / formation commit is `ef934239c3`, where identity-envelope active guard validation was introduced while `_identity_envelope_from_brief` still raised on missing translation `lane` before the `expected_lane` fallback could apply.
- `e720f2ab41` only removed the already-dead `expected_lane` fallback surface; it is not the first failure for this fixture.

## Current RED

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider -q
```

Result: failed as expected.

Key output:

```text
AssertionError: {'calls': {'process': 0, 'tick': 0}, 'summary': {'active': 1, ...}}
assert 'active run registry is dangling' != 'active run registry is dangling'
```

Equivalent harness command:

```bash
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/legacy_translation_guard_harness.py
```

Output:

```json
{"calls":{"process":0,"tick":0},"commit":"61dfde5641","summary":{"active":1,"complete":0,"failed":0,"legacy_sweep":null,"new_matrix_sweep":null,"reason":"active run registry is dangling","run_id":"auto-i18n-ja-1414b75a404721e95e74","runner":{"status":"idle"},"status":"blocked"}}
```

Verdict: current RED is valid. The target symptom is the dangling guard, and tick/process/provider invocation stayed zero.

## Fail-closed negative cases

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_identity_fails_closed_for_lane_authority_drift -q
```

Output:

```text
....                                                                     [100%]
4 passed in 0.05s
```

Covered cases:

- state lane missing with missing brief lane
- state lane invalid with missing brief lane
- state lane mismatch with missing brief lane
- brief lane present and mismatched against current envelope/state lane

## Historical good check

Setup:

```bash
git worktree add /private/tmp/pantheon-gen05-rca-ef934239c3-20260828-01 ef934239c3
```

Command run from the historical checkout:

```bash
/Users/mattkuo/Documents/Pantheon/.venv/bin/python /Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/legacy_translation_guard_harness.py
```

Output:

```json
{"calls":{"process":0,"tick":0},"commit":"ef934239c3","summary":{"active":1,"complete":0,"failed":0,"legacy_sweep":null,"new_matrix_sweep":null,"reason":"active run registry is dangling","run_id":"auto-i18n-ja-1414b75a404721e95e74","runner":{"status":"idle"},"status":"blocked"}}
```

Verdict: the handoff assertion that `ef934239c3` can pass the same missing-lane fixture is false for this executable fixture. `ef934239c3` contains an `expected_lane` parameter, but its helper raises on missing translation `lane` before the fallback can apply.

Parent boundary command run from `75466a1bab5c0cd278ccbe44730bb9b058d79244` / `ef934239c3^` checkout:

```bash
/Users/mattkuo/Documents/Pantheon/.venv/bin/python /Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/legacy_translation_guard_harness.py
```

Output:

```json
{"calls":{"process":0,"tick":1},"commit":"75466a1bab","summary":{"active":0,"complete":1,"failed":0,"legacy_sweep":null,"new_matrix_sweep":null,"runner":{"status":"idle"},"status":"ok"}}
```

Parent boundary command run from `ef934239c3` checkout:

```bash
/Users/mattkuo/Documents/Pantheon/.venv/bin/python /Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/legacy_translation_guard_harness.py
```

Output:

```json
{"calls":{"process":0,"tick":0},"commit":"ef934239c3","summary":{"active":1,"complete":0,"failed":0,"legacy_sweep":null,"new_matrix_sweep":null,"reason":"active run registry is dangling","run_id":"auto-i18n-ja-1414b75a404721e95e74","runner":{"status":"idle"},"status":"blocked"}}
```

Verdict: historical good is now closed. The last successful version is `75466a1bab`; the first failing / formation commit is `ef934239c3`.

## RCA status

Receipt: `GO / RCA_CLOSED_REPAIR_NOT_STARTED`; this closes RCA evidence and does not start Repair.

Closed:

- Current RED-capable command: yes.
- Target symptom: yes, `active run registry is dangling`.
- Provider/tick/process invocation zero at block: yes.
- Fail-closed negative cases: yes.
- Last successful version: yes, `75466a1bab5c0cd278ccbe44730bb9b058d79244` / `ef934239c3^` returns status `ok`, tick `1`, process `0`.
- First failing commit and mechanism: yes, `ef934239c3` introduces identity-envelope active guard validation while the helper raises before its `expected_lane` fallback.
- Durable invariant: yes, validated current envelope plus matching state lane must preserve missing-lane legacy translation identity; missing/invalid/mismatched state lane and explicit brief lane mismatch fail closed.

Repair status: not started. RCA is now eligible to hand off one bounded Repair at the coordinator active integrity seam.

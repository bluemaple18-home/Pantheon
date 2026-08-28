# Pantheon Acceptance B gen05 dangling registry guard Repair evidence

## Scope receipt

- Date: 2026-08-28
- Repair card: `CARD-PANTHEON-ACCEPTANCE-B-GEN05-DANGLING-REGISTRY-GUARD-REPAIR-20260828.md`
- RCA verdict: `GO / RCA_CLOSED_REPAIR_NOT_STARTED`
- Production mutation: none
- Push / commit / tag / deploy / publish / resume / gen06 / planning provider: none
- CodeGraph: queried before production source decision for `_active_run_integrity_block`.

## RED before Repair

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider -q
```

Output:

```text
F                                                                        [100%]
AssertionError: {'calls': {'process': 0, 'tick': 0}, 'summary': {'active': 1, ...}}
assert 'active run registry is dangling' != 'active run registry is dangling'
1 failed in 0.12s
```

Verdict: valid RED. The current guard blocks before tick/process/provider.

## Repair implementation

Changed only `scripts/agy_gemini_coordinator.py::_active_run_integrity_block`.

Implementation frontier:

- Existing explicit brief-lane path stays unchanged: `_identity_envelope_from_brief(brief)` must exactly match the current envelope.
- Missing-lane legacy translation path now runs only after `_validate_identity_envelope` succeeds.
- The fallback authority uses validated envelope mode, requires it to be `translate_existing`, validates `state.get("lane")` under that mode, requires state lane to equal envelope lane, then rebuilds the observed envelope from brief article ids.
- State `mode` is not an added authority requirement.
- Registration, global helper, publisher, promotion, registry, brief, queue, continuation, resume, planning, gen06, publish, tag, push, commit, merge, and deploy were not changed.

## Verification

Matching GREEN:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider -q
```

Output:

```text
.                                                                        [100%]
1 passed in 0.40s
```

State-mode boundary GREEN:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_guard_accepts_missing_brief_lane_with_matching_state_lane_without_state_mode -q
```

Output:

```text
.                                                                        [100%]
1 passed in 0.40s
```

Fail-closed negative cases:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_identity_fails_closed_for_lane_authority_drift -q
```

Output:

```text
....                                                                     [100%]
4 passed in 0.41s
```

Existing observed lane drift:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_translation_identity_rejects_observed_lane_drift -q
```

Output:

```text
..                                                                       [100%]
2 passed in 0.40s
```

Executable harness after Repair:

```bash
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/legacy_translation_guard_harness.py
```

Output:

```json
{"calls":{"process":0,"tick":1},"commit":"61dfde5641","summary":{"active":0,"complete":1,"failed":0,"lanes":{"i18n-new":{"active":0,"processing":0,"queued":0},"i18n-rewrite":{"active":0,"processing":0,"queued":0},"new":{"active":0,"processing":0,"queued":0},"rewrite":{"active":0,"processing":0,"queued":0}},"legacy_sweep":null,"migrated_jobs":null,"new_matrix_sweep":null,"runner":{"status":"idle"},"status":"ok"}}
```

Affected coordinator test file:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q
```

Output summary:

```text
8 failed, 313 passed in 540.68s (0:09:00)
```

Residual failures are all in the existing campaign translation / private campaign e2e path and fail with:

```text
scripts.agy_multilingual_pipeline.LocalePlanValidationError:
deterministic locale plan failure: external locale plan coverage fields are strict for article-01
```

These failures are outside the active registry guard seam and outside this Repair scope.

Debug instrumentation check:

```bash
rg -n "\[DBG-" scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py
```

Output: no matches.

Whitespace gate:

```bash
git diff --check
```

Output: no findings.

## Verdict

`GO / BOUNDED_REPAIR_DELIVERED_PRODUCTION_NOT_ACCEPTED`

The bounded Repair is delivered locally and verified at the target active-integrity seam. Production acceptance has not been run or claimed.

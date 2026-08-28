# Pantheon Acceptance B gen05 dangling registry guard RCA result

## Verdict

`GO / RCA_CLOSED_REPAIR_NOT_STARTED`

The current runtime blocker is real and reproducible:

- current HEAD `61dfde5641`
- production-shaped legacy `translate_existing` fixture
- missing brief `lane`
- valid current `identity_envelope`
- matching state `lane=i18n-new`
- exact-run coordinator path
- result: `active run registry is dangling`
- tick/process/provider invocation: `0/0/0`

The historical boundary is now corrected by parent executable evidence:

- `75466a1bab5c0cd278ccbe44730bb9b058d79244` / `ef934239c3^`: same harness returns `status=ok`, `tick=1`, `process=0`.
- `ef934239c3`: same harness returns `active run registry is dangling`, `tick=0`, `process=0`.

## Root Cause Finding

The active coordinator guard requires the legacy translation brief to carry top-level `lane` even when the current registry state already has a valid identity envelope and matching state lane. This makes the runtime active guard stricter than the intended durable identity compatibility contract.

Corrected formation: `ef934239c3` is the first failing commit. It introduced identity-envelope active guard validation with an `expected_lane` fallback call, but `_identity_envelope_from_brief` raised on missing translation `lane` before that fallback could apply. The handoff claim that `e720f2ab41` formed the failure is corrected: `e720f2ab41` only removed an already-dead fallback surface.

## Repair Gate

Repair has not started in this RCA.

RCA evidence is closed and eligible for one bounded Repair:

1. Last successful version: `75466a1bab5c0cd278ccbe44730bb9b058d79244`.
2. First failing commit/mechanism: `ef934239c3`, identity-envelope active guard validation plus helper raise before fallback.
3. Durable invariant: validated current envelope plus matching state lane must preserve legacy missing-lane translation identity; missing/invalid/mismatched state lane and explicit brief lane mismatch fail closed.
4. RED-capable command: current HEAD fixture returns dangling with provider/tick/process invocation zero.

## Files Changed

- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-DANGLING-REGISTRY-GUARD-RCA-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/legacy_translation_guard_harness.py`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/evidence.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/result.md`

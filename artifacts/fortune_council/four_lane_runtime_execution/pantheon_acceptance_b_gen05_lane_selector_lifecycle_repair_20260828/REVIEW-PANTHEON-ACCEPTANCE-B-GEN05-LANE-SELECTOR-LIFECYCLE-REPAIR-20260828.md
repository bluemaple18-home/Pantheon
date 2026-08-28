---
schema_version: 1
title: Pantheon Acceptance B gen05 lane selector lifecycle repair review
date: 2026-08-28
status: COMPLETE
verdict: GO
reviewer: independent_reviewer
scope: gen05 lane selector lifecycle bounded repair only
production_mutation: false
provider_calls: 0
push: false
promotion: false
deploy: false
publish: false
tag: false
---

# Verdict

GO for the bounded lane-selector lifecycle repair.

No P0/P1 blocking finding was found in the source/test diff. The repair correctly
aligns `_lane_for_state` with the 8a integrity guard for the narrow production
legacy translation partial state: no `routing_schema_version`, no `mode`, present
`lane`, valid `identity_envelope`, matching brief identity, matching article
digest, and no durable state migration.

Production promotion/publish remains out of scope and should stay gated by the
known full coordinator suite blocker unless mainline separately resolves or
waives that pre-existing failure.

# Findings

- [P2] Exact lane-mode skipped BLOCKED uses the dangling-registry reason for a non-dangling lane arbitration case - `scripts/agy_gemini_coordinator.py:5291`

  Trigger: `lane_mode=True` with `exact_run_ids` containing two active runs in
  the same lane. `_select_lane_states` selects one per lane, the second selected
  exact run is treated as skipped, and the cycle returns
  `reason="active run registry is dangling"` for that healthy skipped run. This
  is fail-closed, and non-selected active backlog is not affected because
  `active_states` is first filtered to `selected_run_ids` at lines 5269-5273.
  The risk is operator/runbook confusion: a healthy same-lane exact run can be
  classified as dangling, which may send the next repair toward terminalization
  or registry recovery instead of lane arbitration. Minimal fix: keep the
  BLOCKED behavior, but use a distinct summary/reason such as
  `selected exact run was not lane-runnable` or
  `exact lane selector skipped active run`, and add a regression test for two
  same-lane exact IDs.

# Review Notes

Positive authority correctness:

- `_validated_legacy_translation_lane_authority` validates the immutable
  envelope digest through `_validate_identity_envelope`, requires
  `translate_existing`, validates state lane against the envelope lane, checks
  optional brief lane drift, rebuilds the observed envelope from brief article
  IDs, and compares it back to the persisted envelope.
- The direct selector path for the partial legacy shape returns the validated
  lane without writing `routing_schema_version`, `mode`, or any other state
  field.
- The helper refactor does not materially loosen the 8a integrity guard: the
  guard still only applies this legacy authority path when the brief is
  `translate_existing` and brief `lane` is absent; otherwise it falls back to
  the durable identity envelope derived from the brief.

Fail-closed behavior:

- Unknown routing schema, mode-without-schema, invalid digest, non-translation
  envelope, missing/incorrect state lane, and brief lane drift all block the
  exact lane-mode cycle before tick/process provider work.
- The exact-run skipped BLOCKED addition closes the prior production symptom
  where a selected exact active run could pass integrity, be skipped by lane
  selection, and still report `status=ok active=1 runner=idle`.

Test adequacy:

- The new production-shaped fixture defaults to the target partial state shape.
- Positive tests cover exact-cycle tick with provider process count zero and
  direct `_lane_for_state` no-migration by byte comparison.
- Negative tests cover drift and invalid authority cases required by the RCA.
- One additional same-lane exact probe confirmed the only broadened behavior is
  explicit BLOCKED for multiple selected active runs in the same lane, not
  unrelated active backlog.

# Evidence

Inspected:

- `CARD-PANTHEON-ACCEPTANCE-B-GEN05-LANE-SELECTOR-LIFECYCLE-RCA-20260828.md`
- `pantheon_acceptance_b_gen05_lane_selector_lifecycle_rca_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-LANE-SELECTOR-LIFECYCLE-RCA-20260828.md`
- `CARD-PANTHEON-ACCEPTANCE-B-GEN05-LANE-SELECTOR-LIFECYCLE-REPAIR-20260828.md`
- `pantheon_acceptance_b_gen05_lane_selector_lifecycle_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-LANE-SELECTOR-LIFECYCLE-REPAIR-20260828.md`
- `pantheon_acceptance_b_gen05_lane_selector_lifecycle_repair_20260828/baseline-vs-repair-eight-nodeids-receipt.json`
- `pantheon_acceptance_b_gen05_production_release_8a_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-RELEASE-8A-20260828.md`
- uncommitted diff for `scripts/agy_gemini_coordinator.py`
- uncommitted diff for `tests/test_agy_gemini_coordinator.py`

Commands run:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_partial_lane_selector_uses_identity_without_migration tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_partial_selector_fails_closed_for_invalid_authority tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_identity_fails_closed_for_lane_authority_drift tests/test_agy_gemini_coordinator.py::test_active_guard_accepts_missing_brief_lane_with_matching_state_lane_without_state_mode tests/test_agy_gemini_coordinator.py::test_active_translation_identity_rejects_observed_lane_drift -q
```

Result: `13 passed in 0.07s`.

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_continue_after_one_selected_run_is_terminal tests/test_agy_gemini_coordinator.py::test_cycle_exact_run_ids_reject_duplicates_before_advancing tests/test_agy_gemini_coordinator.py::test_lane_for_state_uses_immutable_state_over_brief_and_rejects_bad_routing -q
```

Result: `3 passed in 0.07s`.

```bash
git diff --check
```

Result: PASS.

Additional same-lane exact probe:

```json
{
  "status": "blocked",
  "reason": "active run registry is dangling",
  "run_id": "same-lane-b",
  "active": 2,
  "complete": 0,
  "failed": 0,
  "runner": {"status": "idle"},
  "new_matrix_sweep": null,
  "legacy_sweep": null
}
```

Baseline-vs-repair receipt:

- classification: `PRE_EXISTING`
- same_failure_shape: `true`
- provider_calls: `0`
- production_mutation: `false`
- baseline and current both fail the same eight campaign translation tests with
  the same locale-plan strict coverage shape.

# Remaining Risk

The full `tests/test_agy_gemini_coordinator.py` file is not green in the repair
worker receipt (`318 passed, 8 failed`). The baseline-vs-repair receipt
classifies those eight failures as pre-existing against 8a, not introduced by
this bounded repair. This is acceptable for the repair verdict, but not by
itself sufficient for a later production push/promotion gate.

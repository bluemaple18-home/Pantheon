---
status: COMPLETE
verdict: FORMAL_MISSING_SEAM
date: 2026-08-28
target_run: auto-i18n-ja-1414b75a404721e95e74
production_mutation: 0
provider_mutation: 0
source_mutation: 0
---

# RESULT — gen06 same-generation planning retry missing seam RCA

## Verdict

`FORMAL_MISSING_SEAM`。

The immediate bad data is a provider-returned JA plan containing Chinese `coverage_note` values, but recovery is not `DATA_ONLY`: current formal `resume` cannot make a same-generation gen06 provider retry because it preserves the invalid cached `generations/06/external-plan.json`.

## Current facts

- target run: `auto-i18n-ja-1414b75a404721e95e74`
- failed job: `6894ba2772dca5fd9e44938951535d8e26d39467`
- provider attempt: 1 succeeded
- failed stage: planning contract validation
- registry error: `LocalePlanValidationError`
- gen06 artifacts present:
  - `external-plan.json`
  - `plan-operation.json`
  - `planning-result.json`
  - `source-ref-map.json`
- failing field: `article-01.coverage_note[3] = 財務現狀的檢視與重塑`
- reviewer queued/called: no
- gen07: absent

## 1. Last successful comparable recovery

No successful comparable same-generation invalid cached external-plan retry was found.

Closest prior seam is gen04 lifecycle repair, but it is not the same operation:

- gen04 repair handled a partial generation with persisted `external-plan.json`/`plan-operation.json` and missing `source-ref-map.json`.
- Its contract terminalizes/abandons the partial generation and authorizes a later generation; it does not retry the same generation with a new provider plan.
- It explicitly preserves partial artifacts as audit, rather than quarantining an invalid cached plan for same-generation retry.

Therefore there is no proven formal precedent for “same gen06 planning retry once” after a provider-success / deterministic plan-validation failure.

## 2. First failing mechanism / commit

The current failure is caused by the interaction of two mechanisms:

1. `scripts/agy_gemini_coordinator.py::resume_run`
   - Commit `29fa640465` (`fix: resume locale plan failure as fresh attempt`) added the special case that removes `last_job_id` for `LocalePlanValidationError`.
   - It only mutates the queue registry and does not inspect, quarantine, remove, or bind generation-local planning cache artifacts.

2. `scripts/agy_multilingual_pipeline.py::_load_or_generate_external_locale_plan`
   - If `external-plan.json` exists, it loads that payload and returns without provider generation.
   - The current gen06 has a persisted invalid `external-plan.json`, so retrying through `resume + cycle` reuses the stale bad plan.

Relevant hardening in `18c6f563f5` keeps cached plan reads strict and deterministic, which is correct for safety, but it also means registry-only resume is insufficient as a retry seam.

## 3. Authoritative owner / invariant

Ownership boundary:

- queue registry owns run selection, `status`, `last_job_id`, and terminal failed state.
- lane job queue owns provider request/archive/inbox/attempt evidence.
- generation directory owns planning artifacts and cached provider output.
- continuation state owns `next_generation`, completed/abandoned generations, and generation lifecycle authority.

Durable invariant:

When a provider attempt succeeds but deterministic planning validation fails, the cached external plan is not a successful generation artifact. Any formal same-generation retry must bind all three owners:

- registry failed identity and `last_job_id`
- provider attempt/inbox/archive identity for the failed plan
- exact generation-local cached artifact digests

Then it must either quarantine/remove the stale cached planning artifacts under receipt before reactivation, or fail closed. Clearing only registry `last_job_id` creates a false “fresh attempt” surface because generation-local cache remains authoritative for `_load_or_generate_external_locale_plan`.

## 4. RED-capable harness

Evidence:

- `red-harness-resume-cycle-stale-plan-provider0.json`

Harness method:

- copies the live target run and registry to a temp queue
- calls `resume_run(...)`
- calls `cycle_once(..., exact_run_ids=[target], lane_mode=True)` with a fail-if-called provider client
- no production state is touched

Observed:

- `provider_fail_if_called_calls = 0`
- `cycle_summary.status = failed`
- `after_error_type = LocalePlanValidationError`
- `external_plan_sha256 = b4e1b9fdd2c0fbe7235d4faffd18851c7a36dbea8e38cf7eb510aeea212b8e27`
- `gen07_exists = false`
- runner remained idle

This proves `resume + cycle` reuses the stale cached plan and does not produce a new provider attempt.

## DATA_ONLY?

No.

The bad provider payload is data, but the missing recovery capability is source/runtime contract: there is no formal, hash-bound way to perform a same-generation planning retry after a provider-success deterministic plan failure.

## Minimum-sufficient Repair frontier

Add one bounded formal seam, preferably in existing coordinator/multilingual continuation surfaces:

- command name suggestion: `retry-same-generation-locale-plan` or `quarantine-failed-locale-plan-cache`
- plan-only default; execute explicit
- only accepts:
  - exact run id/run dir
  - registry `status=failed`
  - `error_type=LocalePlanValidationError`
  - exact `last_job_id`
  - provider attempt marker `succeeded`
  - matching inbox/archive request/result digests
  - exact generation number `06`
  - exact bad `external-plan.json`, `planning-result.json`, `plan-operation.json`, `source-ref-map.json` digests
  - continuation state still `active`, `next_generation=6`
  - gen07 absent
- plan-only must be zero-write
- execute should be receipt-first and use existing atomic writer/quarantine style:
  - move or copy stale planning cache into a generation-local quarantine/receipt path
  - clear only the minimal generation-local planning artifacts that force cache reuse
  - reactivate registry for the same gen06
  - do not edit candidate/review/root result
  - do not change continuation generation number
  - idempotent crash-window replay only

Not enough:

- plain `resume`
- manual deletion of `external-plan.json`
- provider retry without artifact binding

Too much:

- new registry/FSM/database
- generic rerun/reset command
- gen07 transition
- publisher/promotion changes

Estimated implementation size if kept tight:

- source: about 120–160 LOC
- tests: about 180–260 LOC

If the repair needs more than source 160 / tests 260 LOC, stop and return to mainline for scope review rather than expanding.

---
status: COMPLETE
scope: RCA_ONLY
target_run: auto-i18n-ja-1414b75a404721e95e74
generation: 6
source_commit: 29c244744cc266df05ba687c31a35d9c63a2b9f1
production_mutation: 0
provider_mutation: 0
repair_opened: false
---

# RESULT — gen06 null `last_job_id` identity recovery RCA

## Verdict

`FORMAL_MISSING_SEAM`

Current 29c retry seam still requires registry `last_job_id == expected_job_id`. Production state now has exact gen06 stale planning artifacts and exact lane-level `archive/inbox/production-attempt` residue for job `6894ba2772dca5fd9e44938951535d8e26d39467`, but registry `last_job_id` is `null`. Therefore the formal seam cannot legally bind the job identity and fails closed before retry.

This is not `DATA_ONLY`: the data residue is recoverable, but the formal recovery seam cannot bind job identity after a same-generation retry/cycle sequence clears `last_job_id`.

## Evidence

- live provenance snapshot: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_null_last_job_identity_rca_20260828/live-provenance-snapshot.json`
- temp-copy RED harness: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_null_last_job_identity_rca_20260828/temp-copy-red-harness.json`
- prior 29c production NO-GO preflight: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_bounded_completion_29c_20260828/preflight-live-residue-29c.json`

Key live facts:

- registry status: `failed`
- registry error_type: `LocalePlanValidationError`
- registry lane: `i18n-new`
- registry `last_job_id`: `null`
- gen06 root `external-plan.json`: `b4e1b9fdd2c0fbe7235d4faffd18851c7a36dbea8e38cf7eb510aeea212b8e27`
- gen06 root `plan-operation.json`: `2a03eb2235665c70f132e7921ec3d085bd0a00552ed097c4e18cd488409172b5`
- lane archive: `640032da1b13f797e07d98d0ee94296bd8c9f821cf2d9dc6a0fa21c09af8cc2c`
- lane inbox: `de93f73901f5b4498946c1349ba9520b80570c8b19345d5e50ee13d481257226`
- lane production-attempt: `8220193ebb2b1b43b20c095a8481a58aa9d0757f94c559de38daab27fac9eee8`
- archive / inbox / attempt all bind request sha:
  `6894ba2772dca5fd9e44938951535d8e26d39467e955e51d396bea41531d878f`
- `plan-operation` prompt/schema hashes match lane archive prompt/schema hashes:
  - prompt `40729064042539a993b4c8dc6ab1eb8c4c45ded6c0425208fc98ff099ce90d03`
  - schema `9391ee846983182eb5c09433991093197e6fffe484f708d3ab8ea5ec1185a5ef`
- gen07/candidate/review/external-review/deterministic-findings: absent

Temp-copy RED harness:

- setup copied production run + lane residue into `/private/tmp`, normalized temp `run_dir`, and removed copied prior quarantine only to isolate the null-job condition.
- supplied exact expected job id and exact digests.
- result: `RED`
- error: `same-generation locale plan retry registry state differs`
- invocation zero-write: true

## Four evidence closure

1. Last successful comparable null-`last_job_id` identity recovery:
   - No successful comparable formal recovery was found.
   - Existing tests and repair artifacts cover normal `last_job_id`-bound retry, `ALREADY_ACTIVE`, crash replay, and stale-inbox quarantine; none cover failed registry with `last_job_id=null` plus exact matching lane residue.

2. First mechanism / event:
   - Commit `18b121fa335ab74621fb8da03d1a6b2a02916c88` introduced `retry_same_generation_locale_plan`.
   - Its execute path intentionally clears `last_job_id` after quarantine to let the run re-enter active queue.
   - The following exact cycle restored the stale external plan from old lane residue and raised `LocalePlanValidationError`; `_advance` handled it as a generic exception, setting `status=failed` and `error_type=LocalePlanValidationError` but not restoring `last_job_id`.
   - Commit `29c244744cc266df05ba687c31a35d9c63a2b9f1` then closed stale lane residue reuse, but still requires registry `last_job_id == expected_job_id`, so it cannot operate on the post-18b failed state.
   - Related older precedent: commit `29fa640465c` added `resume_run` behavior that clears `last_job_id` for `LocalePlanValidationError`; that is not the direct production event here, but confirms this state shape is not imaginary.

3. Authoritative owner / invariant:
   - Registry owns lifecycle status and currently owns no job id.
   - Generation root owns stale plan cache and `plan-operation` prompt/schema identity.
   - Lane outbox owner owns the durable job id through archive, inbox, and production-attempt residue.
   - A same-generation retry after provider-success deterministic validation failure must bind the job id from all available authorities when registry lacks it: expected operator job id, lane archive/inbox/attempt digests and request sha, plan-operation prompt/schema match, gen06 artifact digests, active continuation `next_generation=6`, and absence of writer/reviewer/gen07 boundary artifacts.

4. RED-capable harness:
   - `temp-copy-red-harness.json` proves current 29c seam rejects `last_job_id=null` even when exact job id and all residue digests are supplied.

## Additional live blocker to include in Repair

Production also has a prior quarantine directory from the 18b attempt while restored root gen06 planning files are present. Current 29c `validate_generation_cache` treats `source_present && quarantine_present` as cache shape drift.

So a production-sufficient repair cannot only relax `last_job_id`. It must narrowly accept this exact restored-root + prior-quarantine shape only when:

- the prior quarantine receipt belongs to the same expected job id/run/generation;
- root planning artifacts match expected current root digests;
- prior quarantine artifacts either match the same expected stale digests or are treated as already-quarantined audit for the same job;
- lane residue is still source-present and exact.

Without this, the next production attempt will fail closed on cache shape before reaching the null-job identity branch.

## Minimum Repair frontier

One bounded closure on the existing `retry_same_generation_locale_plan` seam; no new CLI.

Allow `registry.last_job_id` to be missing only when all of these are true:

- registry `status=failed`, `error_type=LocalePlanValidationError`, exact run id/run dir/lane;
- operator supplies exact `expected_job_id` and all digests;
- gen06 root planning artifacts match expected digests;
- `plan-operation` prompt/schema hashes match lane archive prompt/schema hashes;
- lane archive/inbox/attempt all bind the same `expected_job_id` and request sha;
- no outbox/processing/failed/terminalizing ambiguity;
- continuation is active with `next_generation=6`;
- gen07, candidate, review, external-review, and deterministic findings are absent;
- prior quarantine, if present with restored root cache, is same job/run/generation and exact, not an unrelated mixed cache.

Then execute may quarantine lane residue and restored root cache receipt-first exactly as 29c intended. Drift or ambiguity remains fail-closed.

Estimated closure:

- source: feasible within `<=40` LOC by adding a narrow null-job branch and a restored-root/prior-quarantine cache status to existing validators.
- tests: feasible within `<=80` LOC by adding one RED/GREEN null-`last_job_id` fixture/harness and two negatives: wrong prompt/schema or multi-job lane residue.

If implementation requires scanning for arbitrary jobs, guessing from directories, a new ledger, a new registry/FSM, or multi-job recovery, it should be `NO-GO`.

## why_not_less / why_not_more / do_not_absorb

- why_not_less: null `last_job_id` is the current formal blocker; lane residue and plan-operation already contain enough bounded identity to recover, but current seam refuses to use them.
- why_not_more: no generic retry or new runtime authority is needed; the job id is already supplied and independently verified by three lane artifacts plus plan-operation prompt/schema.
- do_not_absorb: do not scan all lane jobs, do not infer from timestamps, do not create gen07, do not hand-edit registry, do not mutate production before re-review, and do not broaden this beyond same-generation `LocalePlanValidationError` with exact digests.

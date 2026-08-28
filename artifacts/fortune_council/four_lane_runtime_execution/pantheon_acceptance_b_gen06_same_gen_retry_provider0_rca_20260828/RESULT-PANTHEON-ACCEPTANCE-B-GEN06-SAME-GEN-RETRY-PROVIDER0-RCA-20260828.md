---
status: COMPLETE
scope: RCA_ONLY
run_id: auto-i18n-ja-1414b75a404721e95e74
generation: 6
source_commit_under_review: 18b121fa335ab74621fb8da03d1a6b2a02916c88
production_mutation: 0
provider_mutation: 0
repair_opened: false
---

# RESULT — gen06 same-generation retry provider0 RCA

## Verdict

`retry-same-generation-locale-plan` 在 18b 的 execute 已正確把 run registry 從 failed 切回 active，但它只 quarantine 了 generation-local planning cache，沒有 quarantine 同一 deterministic external request 的 lane-level transport residue。

因此下一個 exact cycle 沒有建立 fresh outbox job，也沒有 provider call；pipeline 重新產生同一 prompt/schema 後，outbox 以同一 job id 直接吃到舊 `archive + inbox` response，還原出完全相同的 invalid `external-plan.json`，再次 `LocalePlanValidationError`。

這不是 `DATA_ONLY`。壞 plan 是資料，但「retry seam 沒切斷 poisoned transport owner」是 formal recovery seam gap。

## Evidence

- provenance hash chain：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_provider0_rca_20260828/provenance-hash-chain.json`
- temp-copy RED harness：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_provider0_rca_20260828/temp-copy-red-harness.json`
- production 18b attempt receipts：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_completion_18b_20260828/`

Key hashes / identities:

- job id：`6894ba2772dca5fd9e44938951535d8e26d39467`
- request sha256：`6894ba2772dca5fd9e44938951535d8e26d39467e955e51d396bea41531d878f`
- root `external-plan.json` after retry：`b4e1b9fdd2c0fbe7235d4faffd18851c7a36dbea8e38cf7eb510aeea212b8e27`
- quarantined old `external-plan.json`：`b4e1b9fdd2c0fbe7235d4faffd18851c7a36dbea8e38cf7eb510aeea212b8e27`
- lane archive request：`640032da1b13f797e07d98d0ee94296bd8c9f821cf2d9dc6a0fa21c09af8cc2c`
- lane inbox response：`de93f73901f5b4498946c1349ba9520b80570c8b19345d5e50ee13d481257226`
- lane production attempt marker：`8220193ebb2b1b43b20c095a8481a58aa9d0757f94c559de38daab27fac9eee8`

Temp-copy RED harness result:

- plan status：`READY_TO_EXECUTE`
- execute status：`RETRY_READY`
- cycle status：`failed`
- provider called：`false`
- outbox count delta：`0`
- attempt count delta：`0`
- root plan equals quarantined plan：`true`

## Source/data provenance

The replay path is:

1. 18b seam moves only gen06 local planning files into:
   `generations/06/planning-cache-quarantine/6894ba2772dca5fd9e44938951535d8e26d39467/`
2. Registry becomes active and removes `last_job_id/error_type/result`.
3. `_run_locale_generation` rebuilds the same prompt/schema for gen06.
4. `create_external_request` computes the same attempt-0 job id from canonical request sha and sees the known archive request.
5. `consume_external_response` sees `inbox/<job>.json` and returns the prior successful provider response.
6. `_load_or_generate_external_locale_plan` writes that old result back as root `external-plan.json`.
7. Deterministic locale-plan validation fails again on the same non-JA `coverage_note` content.

Relevant source points:

- `scripts/agy_gemini_coordinator.py:5484` — 18b retry seam validates lane job artifacts but only moves generation-local cache at `5603-5606`.
- `scripts/agy_gemini_outbox.py:336` — attempt-0 job id is derived from request sha.
- `scripts/agy_gemini_outbox.py:552` — known paths include archive, so archived identical request is returned.
- `scripts/agy_gemini_outbox.py:814` — inbox response is consumed when present.
- `scripts/agy_multilingual_pipeline.py:2490` — missing root `external-plan.json` causes provider transport call through the outbox client, which can resolve from old inbox without an external provider call.

## Four evidence closure

1. Last comparable success: none found for hash-bound same-generation retry after provider-success deterministic planning failure. Prior RCA already found no successful native same-generation invalid external-plan retry; 18b was the first formal seam.
2. First failing mechanism: commit `18b121fa335ab74621fb8da03d1a6b2a02916c88` added `retry_same_generation_locale_plan`, but its mutation boundary stopped at generation-local cache. The older outbox idempotency behavior is not itself failing; it became poisonous only because the new recovery seam did not bind/quarantine the lane transport residue it had validated.
3. Durable invariant: same-generation retry after deterministic validation failure must bind all authoritative owners of the poisoned attempt: generation cache, queue registry, lane archive, lane inbox, production-attempt marker, and operation receipt. If any one owner can still replay the failed provider-success payload, retry is not a retry.
4. RED-capable harness: temp-copy harness reproduces `RETRY_READY → exact cycle provider0 → identical external-plan restored → failed` without touching production or provider.

## Missing seam item

The current seam missed lane-level quarantine of:

- `queue/lanes/i18n-new/archive/<job>.json`
- `queue/lanes/i18n-new/inbox/<job>.json`
- `queue/lanes/i18n-new/production-attempts/<job>.attempt`

It did not miss gen06 root cache quarantine; that part occurred. It did not primarily miss operation receipt quarantine; root `plan-operation.json` was regenerated, but because it does not encode the external job id, it cannot prevent old inbox replay by itself.

## Minimum sufficient Repair frontier

Open one bounded closure on the existing `retry_same_generation_locale_plan` seam only:

- keep the existing exact run id / generation / job id / digest contract;
- while still inside `_run_identity_lock`, after revalidation, receipt-first move the three lane-level job artifacts above into the same run-local quarantine namespace;
- require exact digests and job identity before moving;
- fail closed on archive/inbox/attempt drift, missing artifact, ambiguous outbox/processing/failed artifact, existing active outbox for same job, gen07/candidate/reviewer boundary drift;
- then let existing outbox `create_external_request` create a fresh outbox job for the same deterministic request, so the next runner performs exactly one new provider attempt for gen06.

Estimated closure: feasible within `<=40` source LOC and `<=80` test LOC by extending the current `validate_lane_job` / execute path and adding a focused RED/GREEN regression plus drift negative. No generic retry, new ledger, new registry, FSM, or provider wrapper is needed.

## why_not_less / why_not_more / do_not_absorb

- why_not_less: only moving generation-local files is proven insufficient; leaving archive/inbox/attempt in place recreates identical stale plan with provider0.
- why_not_more: replacement lineage, new retry ledger, new generation, or second runtime is unnecessary because the authoritative stale artifacts are three concrete files under the existing lane queue owner.
- do_not_absorb: do not add generic provider retry policy, do not alter outbox idempotency globally, do not hand-edit production state, do not create gen07, and do not broaden `LocalePlanValidationError` recovery beyond this hash-bound same-generation seam.

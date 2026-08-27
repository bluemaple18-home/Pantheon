# RESULT - gen05 safety authority repair

## Scope

- 工作名稱：修復 gen05 safety authority
- RCA verdict：GEN05_SAFETY_COVERAGE_RCA_COMPLETE
- Parent SHA：e3a2bbd188a0d25f15a02cde1b2b6820df5dd583
- Allowlist diff：
  - `scripts/agy_multilingual_pipeline.py`
  - `tests/test_agy_multilingual_pipeline.py`
  - `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-SAFETY-AUTHORITY-REPAIR-20260827.md`
- Re-review repair：Reviewer `GEN05_SAFETY_AUTHORITY_REVIEW_NO_GO` P1 closed by removing the literal provider-safety token from fresh `_plan_prompt()` and fresh source fact prompt payload.

## Decision

- Fresh external locale-plan schema no longer contains `coverage_mapping.safety_boundary`.
- Fresh provider-facing prompt and source fact prompt payload no longer contain the literal `safety_boundary` token. It now lists allowed coverage fields and says schema-unlisted fields must not be output.
- Hydration always injects `safety_boundary` from current `_source_fact_package()` after source-ref/source-fact coverage is validated.
- Persisted legacy provider safety is accepted only on the read path when `plan-operation.json` is a successful writer receipt whose `schema_sha256` matches the legacy provider-safety schema digest.
- Legacy adapter ignores only the external `safety_boundary` assertion. Source ref coverage, article fields, receipt drift, missing receipt, and schema drift still fail closed.

## Why Not Less

- Only removing `safety_boundary` from schema would make fresh output safer but would not hydrate existing downstream locale-plan shape.
- Only ignoring provider safety in hydration would allow fresh provider output with the old shape to pass silently.
- Only checking source-ref-map would not bind legacy read to the provider schema receipt that actually produced the persisted plan.

## Why Not More

- Did not change production artifacts, continuation state, publisher, reviewer, model route, promotion, registry, lifecycle, semantic budget, or generation allocation.
- Did not add a new authority ledger, FSM, database, or registry.
- Did not loosen general locale-plan validation; non-safety drift remains deterministic failure.

## Do Not Absorb

- Do not absorb provider safety as authoritative input.
- Do not generalize legacy safety compatibility beyond receipt-bound persisted external locale plans.
- Do not use this repair to bless production completion; it only repairs the safety authority boundary.

## RED / GREEN

- RED authority reproduced by RCA evidence: `/private/tmp/pantheon_gen05_safety_coverage_evidence.json`
  - Current failure before repair: `locale plan safety coverage differs for article-01`
  - Legacy provider true refs: `source_ref_03`, `source_ref_08`, `source_ref_14`, `source_ref_15`, `source_ref_16`, `source_ref_22`
  - Expected deterministic true refs: none
- GREEN targeted:
  - `tests/test_agy_multilingual_pipeline.py -q -k 'continuation_schema_uses_request_local_refs_not_fact_ids or continuation_current_ref_response_hydrates_to_current_ids or continuation_fresh_response_rejects_provider_safety or legacy_provider_safety_read or exact_production_gen05_legacy_safety_hydrates_read_only or locale_plan_rejects_fresh_provider_safety_assertion or external_locale_plan_schema_locks_current_brief_coverage or planning_result_records_contract_failure_before_article or planning_result_passes_only_after_local_hydration'`
  - Result: 14 passed, 209 deselected.
- Regression added:
  - Fresh `_plan_prompt(...)` does not contain the literal `safety_boundary` token.
  - Fresh schema does not contain it.
  - Hydrated downstream locale-plan coverage still contains deterministic local safety values.
- GREEN full file:
  - `tests/test_agy_multilingual_pipeline.py -q`
  - Result: 223 passed.
- Diff gate:
  - `git diff --check`
  - Result: pass.

## Calls / Bytes

- Legacy persisted plan read does not call the planning provider. Test guard raises if the plan schema path invokes provider.
- Controlled legacy-read test advances only after planning success and stops at article generation; observed calls: `Counter({"writer": 1})` for the article stage only.
- Exact production gen05 read-only fixture:
  - Root: `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74`
  - `external-plan.json`: 4297 bytes, sha256 `bf883da733a66e4b411a466d93e2d52717846c920c0bfdae8ed9ecb72ecabb9c`
  - `source-ref-map.json`: 1576 bytes, sha256 `8c17a15d27ed776c4265757edc084a990ead2f3146422de3a845b93770970bdc`
  - `plan-operation.json`: 403 bytes, sha256 `ed10f8a4c09b688d409bcb2bb55cf537b182b967799a21a16bcbd7ab3a27aa9d`
  - Test asserted those three bytes unchanged and no `generations/06` was created.
- Schema digests:
  - Fresh schema digest: `9391ee846983182eb5c09433991093197e6fffe484f708d3ab8ea5ec1185a5ef`
  - Legacy provider-safety schema digest unchanged after re-review repair: `b2d821ad016108bb11b91dba5eefacbc1fd12bd3450603a87f2910eb33c83bf3`

## Remaining Risks

- Exact production gen05 safety hydration is read-only evidence, not a production completion claim.
- If the same production continuation is resumed, unrelated validators may still surface non-safety failures. This repair intentionally does not change those gates.

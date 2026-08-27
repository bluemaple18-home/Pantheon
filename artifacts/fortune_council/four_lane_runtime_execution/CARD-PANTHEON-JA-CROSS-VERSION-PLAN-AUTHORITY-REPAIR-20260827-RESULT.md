# Pantheon JA Cross-Version Plan Authority Repair Result

status: `DELIVERED_CANDIDATE`

card_id: `CARD-PANTHEON-JA-CROSS-VERSION-PLAN-AUTHORITY-REPAIR-20260827`

source_sha: `6a20e8d0731fb86da627dbd510d1444f20b4b283`

formal_thread_id: `01a0415c-6a0c-78f3-a13d-90a8fd930269`

## Summary

JA continuation planning now treats the current source package as the request authority. For JA continuation prompts and schemas, provider-facing coverage uses request-local `source_ref_01` through `source_ref_22`; local hydration validates exact-once ref coverage and converts legal refs back to current `source_fact_id` values for the existing internal locale-plan contract.

Legacy prior item-level mapping is invalidated when its ID set differs from the current source package and lacks stable source-span provenance. Invalidated prior coverage mappings, old coverage notes, old fact IDs, source digests, constraint IDs, and source span IDs are not included in the new JA planning prompt. Same-domain JA continuation with an exactly matching current ID set keeps only ref-based topology and is not marked invalidated.

## RED Evidence

Fixture set: `tests/fixtures/agy_multilingual_pipeline/ja_plan_authority/`

- `brief.json`: `93e09f8f637c396e35ccc28707c66734b08eb7f1c0c4cbdcb246df5b11ac8844`
- `attempt_03_locale_plan.json`: `c7c0eb857d3b87e3aa254aa1af07552205859a5f61e889ee42c4f56501771810`
- `generation_04_external_plan.json`: `063cceea4195133ab0382bf25586cb10b3240020b8a0546238830c460b943322`

Offline RED reproduction:

- current facts: `22`
- returned coverage items: `22`
- stale legacy IDs: `3`
- missing current IDs: `3`
- duplicates: `0`
- coverage: `FAIL`
- provider calls: `0`
- article calls: `0`
- Reviewer calls: `0`
- production mutation: `0`

## GREEN Evidence

Test-only fixture:

- `fixed_current_ref_external_plan.json`: `196de2cf7aaaec5ea47a8eaca78138783a73abdfd3fecf817e78bb785fbf22c2`

GREEN coverage proves:

- legacy mapping is `INVALIDATED` when stale/missing IDs exist without stable provenance;
- invalidated old IDs and old item assignments are absent from the JA continuation prompt;
- request-local refs are exactly `source_ref_01` through `source_ref_22`;
- hydration of legal refs produces current-ID coverage with stale `0`, missing `0`, duplicate `0`;
- unknown, missing, and duplicate refs fail closed;
- same-domain JA continuation is not falsely invalidated;
- non-JA schema behavior remains on `source_fact_id`;
- coverage validation remains strict.

## Call Accounting

Existing authority evidence for `auto-i18n-ja-1414b75a404721e95e74` shows:

- pre-existing attempt lineage: `3`
- post-Repair generation attempted: `04`
- planning provider calls in that saved production-shaped attempt: `1`
- article provider calls: `0`
- Reviewer provider calls: `0`
- automatic repair calls: `0`
- terminal stage: deterministic locale-plan hydration
- terminal reason: current source fact coverage mismatch before article generation

This repair run itself performed no provider, network, service, production, push, tag, deploy, publication transaction, or remote write.

## Verification

- `uv run pytest tests/test_agy_multilingual_pipeline.py -k 'ja_plan_authority or ja_continuation or ja_same_domain'`: `8 passed`
- `.venv/bin/pytest tests/test_agy_multilingual_pipeline.py`: `206 passed`
- `jq empty` on all `ja_plan_authority` fixture JSON files: passed
- `git diff --check`: passed
- changed-file allowlist: passed

## Changed Files

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/fixtures/agy_multilingual_pipeline/ja_plan_authority/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-JA-CROSS-VERSION-PLAN-AUTHORITY-REPAIR-20260827-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/ja_cross_version_plan_authority_repair_20260827/evidence.md`


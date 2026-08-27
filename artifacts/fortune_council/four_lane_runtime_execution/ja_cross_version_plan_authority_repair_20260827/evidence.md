# JA Cross-Version Plan Authority Repair Evidence

status: `DELIVERED_CANDIDATE`

## Bootstrap

- formal_thread_id: `01a0415c-6a0c-78f3-a13d-90a8fd930269`
- project_id: `local-0020d4379451d545eb08362962f1def0`
- cwd: Codex worktree for Pantheon
- HEAD at activation: `6a20e8d0731fb86da627dbd510d1444f20b4b283`
- worktree state at activation: clean
- Rule 21 digest verified: `d9cec58c149cfa7c9e3df49be5df589a0350781bc5ec19414be85c40a395ab34`
- CodeGraph: `CONTEXT_DEGRADED`; MCP status call returned unsupported, local index existed at activation HEAD

## Immutable Fixture Digests

Fixture root: `tests/fixtures/agy_multilingual_pipeline/ja_plan_authority/`

| File | Role | SHA-256 |
|---|---|---|
| `brief.json` | production brief | `93e09f8f637c396e35ccc28707c66734b08eb7f1c0c4cbdcb246df5b11ac8844` |
| `attempt_03_locale_plan.json` | historical topology input | `c7c0eb857d3b87e3aa254aa1af07552205859a5f61e889ee42c4f56501771810` |
| `generation_04_external_plan.json` | saved provider response for RED | `063cceea4195133ab0382bf25586cb10b3240020b8a0546238830c460b943322` |
| `fixed_current_ref_external_plan.json` | test-only GREEN current-ref response | `196de2cf7aaaec5ea47a8eaca78138783a73abdfd3fecf817e78bb785fbf22c2` |

No committed fixture, RESULT, or evidence file records the local runtime absolute path.

## Mandatory Offline RED

Using `brief.json` as the current source package and `generation_04_external_plan.json` as the saved provider response:

```json
{
  "current_facts": 22,
  "returned_coverage_items": 22,
  "stale_legacy_ids": 3,
  "missing_current_ids": 3,
  "duplicates": 0,
  "coverage": "FAIL",
  "stale_ids": [
    "fact-f969c002621b",
    "fact-9b6132bd3c5d",
    "fact-e9e00b456bd1"
  ],
  "missing_ids": [
    "fact-23f5088ba3c2",
    "fact-ed7ec3e401ba",
    "fact-f729514cc45f"
  ]
}
```

The RED check is fully offline: provider calls `0`, article calls `0`, Reviewer calls `0`, production mutation `0`.

## Implementation Evidence

- Added request-local ref maps for JA continuation planning.
- JA continuation external schema now asks for `source_ref`, not `source_fact_id`, and does not ask the provider to echo the source digest.
- Hydration validates ref membership, exact-once coverage, unknown refs, missing refs, duplicates, safety flags, and then converts legal refs to current source fact IDs.
- Invalidated legacy prior plans expose only status, mismatch counts, and non-authoritative section hints to the prompt.
- Same-domain prior plans with an exact current ID set are retained only as ref-based topology.
- Provider-facing JA article input uses the sanitized source package and locale plan view, so it contains request-local refs rather than local identity fields.
- Internal locale plans still keep current `source_fact_id` for existing local validation and downstream contracts.
- Same-generation `source-ref-map.json` is durably written before provider plan calls or external response persistence.
- Prompt, schema, and hydration use the same persisted source-ref map authority inside `_run_locale_generation`.
- Persisted external plans without a source-ref map fail closed.
- Persisted maps whose ref-to-current-ID coverage no longer matches the current source package fail closed before provider/article work.
- `planning-result.json` distinguishes `transport_status` from `planning_contract_status`.
- Hydration failure writes `PLANNING_CONTRACT_FAILURE`, `terminal_stage=PLANNING`, `article_provider_calls=0`, and `reviewer_provider_calls=0`.
- Planning success writes `planning_contract_status=PASS` only after local hydration and hydrated current-ID coverage validation pass.

## Verification Commands

- Focused RED/GREEN/lifecycle/planning-result: `.venv/bin/pytest tests/test_agy_multilingual_pipeline.py -k 'ja_plan_authority or ja_continuation or ja_same_domain or source_ref_map or planning_result'`
  - result: `13 passed`
- Full multilingual pipeline regression: `.venv/bin/pytest tests/test_agy_multilingual_pipeline.py`
  - result: `211 passed`
- Fixture JSON validation:
  - `brief.json`: passed
  - `attempt_03_locale_plan.json`: passed
  - `generation_04_external_plan.json`: passed
  - `fixed_current_ref_external_plan.json`: passed
  - `manifest.json`: passed
- Whitespace diff check: `git diff --check`
  - result: passed
- Base-to-candidate whitespace diff check: `git diff --check 6a20e8d0731fb86da627dbd510d1444f20b4b283`
  - result: passed
- Changed-file allowlist:
  - result: passed

## Call Accounting

From existing operation artifacts for `auto-i18n-ja-1414b75a404721e95e74`:

- generation attempts before continuation: `3`
- saved post-Repair generation: `04`
- planning provider calls in saved post-Repair attempt: `1`
- article provider calls: `0`
- Reviewer provider calls: `0`
- automatic repair calls: `0`
- terminal stage: deterministic locale-plan hydration
- terminal reason: source fact coverage mismatch before article generation

This bounded repair performed no provider call, network call, service activation, production mutation, remote write, push, tag, deploy, publication transaction, replacement task, or Reviewer task creation.

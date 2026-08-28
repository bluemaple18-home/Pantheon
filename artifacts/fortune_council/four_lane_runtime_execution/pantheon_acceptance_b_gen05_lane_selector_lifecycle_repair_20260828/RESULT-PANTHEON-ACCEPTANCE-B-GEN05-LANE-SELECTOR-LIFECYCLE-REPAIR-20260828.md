---
schema_version: 1
title: Pantheon Acceptance B gen05 lane selector lifecycle repair result
date: 2026-08-28
status: REVIEW_READY_WITH_PRE_EXISTING_FULL_SUITE_BLOCKER
verdict: TARGETED_GREEN_FULL_COORDINATOR_BLOCKER_PRE_EXISTING
target_run: auto-i18n-ja-1414b75a404721e95e74
provider_calls: 0
production_mutation: false
push: false
promotion: false
deploy: false
publish: false
tag: false
gen06: false
---

# Result

已完成唯一 bounded Repair 的 source/test 修改，未 commit，留給獨立 re-review。

本修復讓 `_lane_for_state` 接受 production-shaped legacy translation partial
state：state 無 `routing_schema_version`、無 `mode`、有 `lane`，且
`identity_envelope` 完整有效並與 durable brief identity、state lane、brief lane
相容時，selector 回傳該 lane，不修改 durable state bytes。

任何非 null unknown routing version、state mode without routing schema、invalid
digest、lane drift、non-translation envelope、brief lane drift 仍 fail closed。

# Diff

Source allowlist touched:

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- RCA / Repair card/result artifacts

Implementation summary:

- 新增 `_active_run_integrity_block_summary`，統一 active registry block 回傳形狀。
- 新增 `_validated_legacy_translation_lane_authority`，讓 integrity guard 與 selector
  共用 legacy translation lane authority 判斷。
- `_lane_for_state` 只在窄 partial shape
  (`routing_schema_version` 不存在、`mode` 不存在、`lane` 存在) 下走 envelope-based
  selector，不做 state migration。
- exact lane-mode 若 selected exact active run 被 selector skip，現在回 BLOCKED，
  不再 silent `status=ok active=1 runner=idle`。

Test summary:

- `_production_shaped_legacy_translation_active_run` 改為真實 partial state fixture。
- 新增 direct selector no-migration test。
- 新增 provider=0 exact-cycle positive。
- 新增 invalid authority fail-closed negatives。

# RED

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_partial_lane_selector_uses_identity_without_migration tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_partial_selector_fails_closed_for_invalid_authority -q
```

Result before source implementation:

- `4 failed, 2 passed`
- RED cases:
  - production partial exact-cycle did not tick (`active=1 complete=0 tick=0`)
  - direct selector raised `unknown active run routing schema`
  - unknown routing schema returned ambiguous `status=ok`
  - state mode without routing schema returned ambiguous `status=ok`

# GREEN

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_partial_lane_selector_uses_identity_without_migration tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_partial_selector_fails_closed_for_invalid_authority tests/test_agy_gemini_coordinator.py::test_active_legacy_translation_identity_fails_closed_for_lane_authority_drift tests/test_agy_gemini_coordinator.py::test_active_guard_accepts_missing_brief_lane_with_matching_state_lane_without_state_mode tests/test_agy_gemini_coordinator.py::test_active_translation_identity_rejects_observed_lane_drift -q
```

Result:

- `13 passed in 0.06s`

# Full coordinator file

Command:

```bash
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q
```

Result:

- `318 passed, 8 failed in 446.91s`

The 8 failures are in existing campaign translation / multilingual locale-plan
fixtures:

- `test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain`
- `test_private_campaign_e2e_composes_four_lanes_without_publishing`
- `test_private_campaign_e2e_resumes_seeded_partial_state_without_repeating_completed_work`
- `test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[source_sha]`
- `test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[translation_sha]`
- `test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[locale]`
- `test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[article_identity]`
- `test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[review_identity]`

Common error:

```text
LocalePlanValidationError: deterministic locale plan failure:
external locale plan coverage fields are strict for article-01
```

These failures occur in `scripts/agy_multilingual_pipeline.py` locale-plan strict
coverage handling and campaign fixtures, outside this Repair source allowlist.
They were not modified in this Repair.

## Baseline classification

Baseline-vs-repair receipt:

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_lane_selector_lifecycle_repair_20260828/baseline-vs-repair-eight-nodeids-receipt.json`

Baseline source:

- clean export path:
  `/private/tmp/pantheon-gen05-lane-selector-baseline-8a-20260828`
- commit:
  `8a50395f67d22343fec4b0a8a5f41c8f40ac360e`

Command:

```bash
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_lane_selector_lifecycle_repair_20260828/baseline_vs_repair_runner.py
```

Compared exact same 8 nodeids in baseline 8a and current Repair tree.

Classification: `PRE_EXISTING`.

Evidence:

- baseline return code: `1`
- current return code: `1`
- baseline `LocalePlanValidationError` count: `40`
- current `LocalePlanValidationError` count: `40`
- baseline strict coverage error count: `16`
- current strict coverage error count: `16`
- same failure shape: `true`

Therefore the 8 full-file failures are not introduced by this lane selector
Repair. They remain a mainline/reviewer decision before any future production
release.

# Other checks

Command:

```bash
git diff --check
```

Result: PASS.

# Risk

- Targeted selector lifecycle risk is reduced: production-shaped partial state now
  has a RED/GREEN guard and no-migration assertion.
- Remaining risk: full coordinator file is not green due 8 PRE_EXISTING campaign
  translation fixture failures outside this bounded Repair. This must be
  resolved or waived by mainline/reviewer before any future push/promotion.
- No production state has been repaired yet; publication still requires a later
  reviewed push/promotion/exact-run cycle.

---
status: COMPLETE
scope: baseline_nodeid_comparison
baseline_commit: f12f24315d
current_tree: working_tree_repair
---

# Baseline nodeid comparison

Purpose: classify the 8 long coordinator full-file failures without retaining long logs.

## Nodeids

- `tests/test_agy_gemini_coordinator.py::test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain`
- `tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_composes_four_lanes_without_publishing`
- `tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_resumes_seeded_partial_state_without_repeating_completed_work`
- `tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[source_sha]`
- `tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[translation_sha]`
- `tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[locale]`
- `tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[article_identity]`
- `tests/test_agy_gemini_coordinator.py::test_campaign_translation_drift_fails_before_queue_or_handoff_mutation[review_identity]`

## Outcomes

| Tree | Outcome | Shared failure |
| --- | --- | --- |
| clean `f12f24315d` export | 8 failed | `LocalePlanValidationError: deterministic locale plan failure: external locale plan coverage fields are strict for article-01` |
| current Repair working tree | same 8 visible failures in full-file run | `LocalePlanValidationError: deterministic locale plan failure: external locale plan coverage fields are strict for article-01` |

Classification: PRE_EXISTING, not queue reactivation Repair regression.

# JA Protected Source Constraint Traceability Repair Result

status: `DELIVERED_CANDIDATE`
card_id: `CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR`
chain_id: `PANTHEON-AUTOMATION-ACCEPTANCE-20260826`
base_commit: `d0d27cffa1a12d3029b851215f18025e97b2eb45`
root_cause: `TRANSLATION_BOUNDARY_CONTRACT_OSCILLATION`

## Summary

Implemented a replacement JA-only protected source constraint traceability seam from the card base commit.

This candidate does not cherry-pick or continue the superseded no-go commits `96a7fd4c90`, `78fe095f61`, or `f4f7c149aa`.

The repair keeps original source candidate spans immutable and traceable while letting deterministic disposition decide whether each heuristic boundary candidate becomes a protected constraint, a merged duplicate, a deterministic false positive, or a fail-closed unresolved candidate.

Review-blocked follow-up repaired three P1 issues: exact-equivalence constraint IDs, stable source clause ordinals independent of classifier hit order, and non-destructive Writer fact projection plus generic repeated target span detection.

## Behavior

- candidate 2 maps to `BOUNDARY_BOILERPLATE_REPEATED` with `repeated_locations=["body"]`
- candidate 3 maps to `BOUNDARY_MEANING_MISSING` with structured `missing_fields[]`, `missing_categories[]`, `present_categories[]`, and omission reasons
- corrected test-only fixture has no boundary omission, repetition, or unresolved finding
- unknown medical safety candidate is preserved as source span, marked `UNRESOLVED`, and fails closed as `UNRESOLVED_BOUNDARY_CANDIDATE`
- ordinary negation false positive is preserved as source span, marked `NOT_A_BOUNDARY`, and receives deterministic `reason_code`
- same-category source spans are not merged unless their exact-normalized source text matches
- `source_span_id` uses original field clause ordinal, not heuristic hit order
- Writer fact projection selects original clauses and does not substring-delete source text
- repeated boilerplate detection uses exact-normalized repeated target span evidence rather than candidate-specific phrase lists
- plan, Writer, deterministic validation, and Reviewer prompt share the same protected constraint view
- raw `source_text` is used for provenance and claim trace; boundary spans no longer become independent repeated safety requirements in Writer facts

## Evidence

See `artifacts/fortune_council/four_lane_runtime_execution/ja_protected_source_constraint_traceability_repair_20260827/verification.md`.

## Verification

- RED candidate 2/3 command: `2 failed, 3 passed, 187 deselected`
- RED full SC command: `4 failed, 3 passed, 185 deselected`
- REVIEW_BLOCKED P1 RED command: `4 failed, 192 deselected`
- GREEN protected source/boundary SC command: `11 passed, 185 deselected`
- REVIEW_BLOCKED P1 GREEN command: `4 passed, 192 deselected`
- full multilingual tests: `196 passed`
- coordinator translation regression: `24 passed, 291 deselected`
- fixture JSON and manifest digests: `json fixtures ok 7`, `manifest digests ok 6`
- absolute path scan on fixture/card artifacts: no hits
- `git diff --check`: passed

## Mutation Accounting

- provider calls: 0
- production candidate calls: 0
- production queue/state mutation: 0
- services mutation: 0
- service startup: 0
- network: 0
- publication policy mutation: 0
- Publisher / Promotion / Coordinator lifecycle mutation: 0

## Delivery Boundary

This result is only `DELIVERED_CANDIDATE`.

Mainline retains independent review, integration, and final GO. This repair does not authorize production B, publication, promotion, push, deploy, provider rerun, or fresh JA candidate generation.

# Pantheon Four-Lane EN Legacy Brief Exact Cycle RCA Review

## Task

Review whether the EN legacy brief exact-cycle RCA is sufficient to proceed to a bounded repair.

## Inputs

- RCA card: `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-EN-LEGACY-BRIEF-EXACT-CYCLE-RCA-20260830.md`
- RCA result: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_en_legacy_brief_exact_cycle_rca_20260830/RESULT.md`
- RCA isolated reproduction and evidence under the same RCA directory.
- Live actor/source history/tests/production immutable evidence: read-only.

## Required Review Questions

- Confirm the exact error is `translation brief fields are strict`.
- Confirm a five-field brief with extra `lane` reproduces RED, and removing `lane` turns GREEN with `outbox=1`.
- Confirm the producer contract is exactly four fields.
- Confirm last-good/first-bad wording is precise and does not overclaim.
- Confirm the three observed failures are same-shape.
- Confirm terminalize/retry/reseed mechanisms do not address this failure.
- Confirm repair frontier is no broader than one source file, `scripts/agy_multilingual_pipeline.py`, plus one test file.
- Define the minimum deterministic compatibility or migration contract.
- Reject any repair that relaxes unknown fields globally, hand-edits production briefs, adds a generic schema union, or introduces a registry/FSM.

## Forbidden

- Do not modify RCA, candidate source, candidate tests, production content, queues, registries, live runtime, launchctl, commits, pushes, tags, or deploys.
- Do not run production writers, reviewers, publishers, activation, or canaries.

## Output

Write only:

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_en_legacy_brief_exact_cycle_rca_review_20260830/RESULT.md`

The result must contain one `GO` or `NO-GO`, P0/P1 findings if any, exact bounded repair acceptance, and anti-expansion rules.

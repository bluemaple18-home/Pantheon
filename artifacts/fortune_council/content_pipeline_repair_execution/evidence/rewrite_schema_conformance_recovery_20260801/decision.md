---
id: CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801-decision
status: ready_for_review
type: decision
---

# Decision

DELIVERED_CANDIDATE / READY_FOR_REVIEW

## Implemented seam

- rewrite writer provider schema keeps object/array/required/additionalProperties and item-count constraints.
- only paragraph string `minLength/maxLength` are omitted at the provider boundary.
- canonical schema and deterministic local quality gates remain unchanged.
- invalid length candidates are not normalized; they enter the existing bounded, reason-bearing content repair flow.
- create/new, i18n-new, i18n-rewrite, broker, runner, coordinator, and publisher behavior were not changed.

## Acceptance

- Four synthetic cross-target minLength/maxLength paths reach the local gate unchanged.
- Canonical diagnostics and `paragraph_length` findings still fail closed.
- Repair prompt/request digests differ and exhaustion remains bounded.
- A canonical-valid fixture passes offline writer generation, local validation, reviewer approval, and publisher eligibility.
- Full affected suite: 438 passed.

## Remaining risk

No production canary was run by contract. The candidate proves the seam offline; mainline retains independent review, integration, and controlled canary responsibility.

## Candidate SHA

- Candidate：`cd3833212ad64af0a1b016c7cc7206464bb8575e`。
- Independent Review：`888bb4090d3f57af116853c2ae30b71afff678b6`，`REVIEW_GO`。
- 最新 v0.3.246 主線上的 candidate cherry-pick：`a54b4b7894`；最終 integration／deployment 狀態由主線 integration receipt 記錄。

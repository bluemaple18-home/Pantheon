# CARD-PANTHEON-PROMOTION-LEDGER-SCHEMA-CONTRACT-REVIEW-20260829

## Review Scope

- Target: independent review of the uncommitted promotion ledger schema contract repair.
- Source truth:
  - `scripts/pantheon_content_runtime_promotion.py`
  - `tests/test_pantheon_content_runtime_promotion.py`
  - formal producer schemas and measured repair evidence already present in the repair-owned artifacts.
- Reviewer-owned outputs:
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-PROMOTION-LEDGER-SCHEMA-CONTRACT-REVIEW-20260829.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/pantheon_promotion_ledger_schema_contract_review_20260829/`

## Allowlist

- Read-only inspection: current git diff, relevant source/test regions, repair card/result/evidence, formal producer schema files if present.
- Writes allowed only under reviewer-owned card/result/evidence paths listed above.
- Forbidden: modifying repair source/test, registry, FSM, DB, migrations, live ledger, production artifacts, commits, pushes, promotions, tags, deploys.

## P0/P1 Review Spec

- P0 if the repair can mutate production state during plan-only validation, rewrite live ledger/history, introduce registry/FSM/DB/migration expansion, or fail open on ambiguous preserved run identity.
- P1 if schema cardinality or canonicalization mismatches formal producer schemas, measured v0.3.374 repair evidence is missing/insufficient, preserved matching regresses, double-run idempotence is not proven, allowlist/source budget is exceeded, or tests do not cover both acceptance and fail-closed cases.

## Required Checks

- CodeGraph status and task-semantic query before source inspection.
- Declarative collection descriptor and shared exact canonicalizer; no lane-by-lane special casing or generic permissive union.
- Singular/list cardinality aligned with formal producer schemas; fail closed for both, missing, unexpected, wrong type, duplicate, and drift.
- Existing preserved matching behavior remains intact for new and rewrite flows.
- Exact v0.3.374 translation fixture and 136-live-shape census support only the measured mismatch repaired.
- Plan-only double run idempotent; transaction root, provider, publisher, and production bytes remain zero.
- Exact allowlist: one source file, one test file, repair/review cards/evidence only; source plus test changed LOC <= 200.
- No registry/FSM/DB/migration/live ledger rewrite.

## Verification Commands

- `git diff -- scripts/pantheon_content_runtime_promotion.py tests/test_pantheon_content_runtime_promotion.py`
- `git diff --check`
- `.venv/bin/python -m pytest tests/test_pantheon_content_runtime_promotion.py -q`
- `.venv/bin/python -m py_compile scripts/pantheon_content_runtime_promotion.py tests/test_pantheon_content_runtime_promotion.py`
- targeted pytest selectors for newly added promotion ledger schema contract tests.
- bounded anti-expansion scans over source/test diff and repo status.

## Verdict Contract

The review result must contain exactly one of `GO` or `NO_GO`, P0/P1 findings or an explicit statement that no blocking issue was found, spec axis, standards axis, acceptance mapping, commit allowlist, changed LOC, production immutability, missing evidence, and remaining risks.

---
id: CARD-PANTHEON-PUBLISHER-PRESERVATION-CONTRACT-REVIEW-20260826
chain_id: PANTHEON-PUBLISHER-PRESERVATION-CONTRACT-20260826
role: review
cycle: 1
model: gpt-5.5
reasoning: high
model_reason: 固定 candidate SHA 的 strict production lifecycle review
status: ready
thickness: strict
risk: high
---

# Pantheon Publisher preservation contract review

## Review Identity

- task_id: `REVIEW-PANTHEON-PUBLISHER-PRESERVATION-CONTRACT-20260826`
- review type: unique independent Reviewer successor card
- relationship: packaging follow-up for existing candidate; not a fourth A/B/C acceptance card and not a new Repair generation
- base: `5ecc8e21a9b69cc3d5bf131b9521662977d6df27`
- candidate: `92131e35522ea18063f98cf3ecd76d9675a4c299`
- review-orchestrator plan: `.work/REVIEW-PANTHEON-PUBLISHER-PRESERVATION-CONTRACT-20260826/review/review_plan.md`
- finding schema: `.work/REVIEW-PANTHEON-PUBLISHER-PRESERVATION-CONTRACT-20260826/review/finding_schema.json`

## Scope

Reviewer must inspect only the candidate diff between base `5ecc8e21a9b69cc3d5bf131b9521662977d6df27` and candidate `92131e35522ea18063f98cf3ecd76d9675a4c299` for:

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`

Reviewer must not modify code, tests, production registry, run directories, deployment state, services, git remotes, tags, or branches.

## Required Review Axes

### Spec Axis

Check whether the candidate truly enforces the Publisher preservation contract instead of only adding plan metadata:

- durable translation runs in `queue/translation-runs` must not be misclassified as actor-local or forced into `queue/gsc-copy`.
- terminal failed tombstones may preserve authoritative identity without manufacturing missing artifacts; missing identity must fail closed.
- create candidates must not be relabeled as `rewrite_existing_body` or routed back into operational selection through path or metadata tricks.
- published create runs and released rewrite runs must remain historical only.
- superseded create runs, including the 26 unpublished create runs described in the Repair card, must remain cold archive identity and must not re-enter operational Publisher selection.
- `ASTRO-BASE-02` remains the only historical rewrite candidate eligible for continuation under the prior decision.

Because this review is limited to the two changed files, any inability to prove actual Publisher operational-selection exclusion from the candidate diff must be reported as a finding or validation gap. Do not treat a new `operational_selection` metadata field alone as proof unless the changed code or tests demonstrate the Publisher selection path consumes or is constrained by it.

### Standards Axis

Check fail-closed and zero-mutation standards:

- durable roots are lane-specific and do not collapse into a single `queue/gsc-copy` allowlist.
- missing terminal failed tombstones are accepted only with a validated identity envelope.
- ledger identity checks for published/released states cannot mask article or mode drift.
- classification is consistent across `preserved_runs`, `preservation_classification`, `queue_snapshot_digest`, and postcheck behavior.
- plan generation remains zero mutation and cannot move, create, delete, rewrite, publish, apply promotion, push, deploy, or start services.

## Reviewer Routing

Use the review-orchestrator output as baseline:

- `coordinator`: dedupe findings, calibrate severity, and produce final review decision.
- `correctness`: inspect behavior, data flow, lifecycle boundaries, and fail-closed error handling.

For this strict production lifecycle review, coordinator must additionally cover standards and validation-gap checks even if the generated plan classified the local working diff as trivial.

## Findings Schema

Every finding must include these fields:

- `severity`: one of `P0`, `P1`, `P2`, `P3`
- `category`: one of `correctness`, `regression`, `security`, `performance`, `test_gap`, `maintainability`, `agents_md`, `release`
- `path`
- `line`
- `evidence`
- `risk`
- `suggested_fix`
- `validation_gap`
- `confidence`

Optional coordinator fields may include `finding_id` and `status` if writing into the generated `review_state.jsonl` format.

Only `P0` or `P1` findings may produce `NO_GO`. `P2` and `P3` findings may recommend follow-up but must not block by themselves.

## Prohibitions

- Do not modify code or tests.
- Do not run production promotion apply.
- Do not mutate production registry or run directories.
- Do not publish, push, deploy, tag, start services, or create a new Repair/new task.
- Do not broaden review scope beyond the two changed files unless the coordinator records it as an explicit validation gap rather than performing out-of-scope inspection.

## Expected Output

Reviewer should return:

- verdict: `GO`, `NO_GO`, or `NEEDS_INFO`
- reviewed base and candidate SHA
- reviewed file list
- findings array following the required schema
- explicit answer for the spec axis operational-selection question
- explicit answer for the standards axis zero-mutation question
- remaining validation gaps

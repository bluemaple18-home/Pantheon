# Pantheon Four-Lane Legacy Brief Compatibility Repair Review

## Task

Review the uncommitted bounded Repair in `<candidate-worktree>` for the legacy explicit-lane translation brief compatibility gap.

## Candidate

- Worktree: `<candidate-worktree>`
- Base: `origin/main=73180233275840b0ab0e101f246e495ee6815fc9`
- Status: uncommitted

## Scope

Review only whether the candidate:

- Changes only `scripts/agy_multilingual_pipeline.py`, `tests/test_agy_multilingual_pipeline.py`, and bounded artifacts.
- Keeps global `validate_translation_brief` strict.
- Adds compatibility only at the registered translation run read seam.
- Uses a trusted binding from registry state, checking `run_id`, `run_dir`, `lane`, and `identity_envelope`.
- Does not trust forgeable brief `lane` or path-string guesses.
- Accepts only the exact legacy explicit-lane shape for `lane=i18n-rewrite`.
- Canonicalizes to the original four-field brief before passing through the original validator.
- Keeps unknown extra fields, lane mismatch/nonstring, missing/type drift, unregistered runs, and wrong run paths RED.
- Makes all registered brief reread seams use the same narrow loader where applicable.
- Keeps the canonical producer four-field.
- Preserves idempotency and avoids duplicate outbox entries.

## Required Verification

- Inspect candidate diff and bounded artifacts.
- Independently rerun targeted multilingual tests, full multilingual tests, a coordinator slice, Python compile, and diff check when feasible.
- Confirm anti-expansion and production immutability limitations are honest.
- If useful, perform read-only production byte SHA checks for the three affected brief/registry pairs.

## Forbidden

- Do not modify candidate source, tests, artifacts, evidence, production roots, queue, registry, or launchctl.
- Do not commit, push, tag, deploy, run production retry, or call provider/publisher/reviewer.

## Output

Write only:

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_review_20260830/RESULT.md`

The result must contain a single `GO` or `NO_GO`, P0/P1 findings if any, exact evidence, and any remaining limits. `GO` only authorizes commit/integration, not production retry.

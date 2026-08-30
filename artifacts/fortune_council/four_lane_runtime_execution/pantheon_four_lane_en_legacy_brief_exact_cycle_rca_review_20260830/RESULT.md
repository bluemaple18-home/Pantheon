# Pantheon Four-Lane EN Legacy Brief Exact Cycle RCA Review

Verdict: `GO`

This `GO` authorizes only a bounded Repair design/implementation. It is not approval for production retry, activation, provider calls, publisher execution, commit, push, tag, or deploy.

## Findings

No P0/P1 findings.

## Evidence Checked

- RCA result: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_en_legacy_brief_exact_cycle_rca_20260830/RESULT.md`
- Machine evidence: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_en_legacy_brief_exact_cycle_rca_20260830/isolated-reproduction.json`
- Live actor HEAD: `6541693e929a20cbcffe8b070085b5f1caec7a92`
- Live actor source: `<production-root>/actor/scripts/agy_multilingual_pipeline.py:249-251`
- Current source: `scripts/agy_multilingual_pipeline.py:249-251`, `scripts/agy_multilingual_pipeline.py:859-891`
- History: `c1885823496270cb195308aae2d72c09c5b0712e`, `45942c29710fc58916addb8862f92c90444b29e8`, `204a8bd8b86b37f411048983730ce1efb9fa2734`
- Production immutable evidence: `resume-bde445-immutability-comparison.json`
- Additional read-only live queue shape probe: translation run states and brief field sets only; no production write.

## Acceptance Mapping

- Exact error: PASS. Isolated reproduction records `ValueError` with message `translation brief fields are strict`.
- Five-field RED: PASS. Exact immutable brief fields are `articles`, `lane`, `mode`, `run_id`, `schema_version`; `lane=i18n-rewrite`; exact fixture produces no Writer job and isolated `outbox=0`.
- Remove-lane GREEN: PASS. Single-variable control removes only top-level `lane`; result becomes `ExternalJobPending` with isolated `outbox=1` and role `writer`.
- Producer contract four fields: PASS. `prepare_translation_run` constructs only `schema_version`, `run_id`, `mode`, and `articles`, then validates before writing.
- Current executor strictness: PASS. `validate_translation_brief` still uses exact key equality and raises `translation brief fields are strict` on any extra top-level key.
- Last-good/first-bad wording: PASS. RCA does not overclaim a successful five-field executor commit. It correctly says the strict validator entered at `c1885823496`; the last proven compatible producer/consumer contract generated four-field briefs; post-seed five-field bytes later collided with the unchanged strict executor.
- Three same-shape failures: PASS by supplemental read-only live queue probe. Three failed translation runs have `error_type=ValueError` and the same five top-level brief fields including `lane`: `auto-i18n-ko-bb1bc3865ed466bac17a`, `auto-i18n-ko-85d513b289d89dd9bf75`, and `auto-i18n-en-aa637e1bf05d3ad21429`.
- Terminalize/retry/reseed applicability: PASS. RCA's seam table is consistent: these paths either leave brief bytes unchanged, require missing job/outbox/candidate/review preconditions, or re-enter the same strict validator before repair.
- Production immutability: PASS for this RCA scope. Isolated evidence reports `production_files=0`, `provider_calls=0`, `writer_jobs_production=0`, `outbox_production=0`, `publishes=0`; independent production immutability evidence shows protected queue/registry/live plist trees unchanged during the relevant blocked staging flow and external provider/publisher/reviewer calls at `0`.
- Bounded frontier: PASS. RCA's next step is limited to `scripts/agy_multilingual_pipeline.py` plus one test file.

## Required Repair Acceptance

Allowed source frontier:

- At most one source file: `scripts/agy_multilingual_pipeline.py`.
- At most one test file, preferably `tests/test_agy_multilingual_pipeline.py`.

Minimum deterministic compatibility contract:

- `validate_translation_brief` for schema v1 may accept an optional top-level `lane`.
- If `lane` is absent, existing legacy four-field brief behavior must remain unchanged.
- If `lane` is present, it must be exactly one of the existing translation identity lanes: `i18n-new` or `i18n-rewrite`.
- Any other extra top-level key must still fail with `translation brief fields are strict` or an equally strict unknown-field failure.
- Invalid lane values must fail closed before Writer outbox creation.
- Exact legacy explicit-lane fixture must move from RED to one Writer `ExternalJobPending`/`outbox=1` in isolation.
- Existing candidate/review validation, source hash validation, target field strictness, replacement validation, and locale-plan retry semantics must not be relaxed.

Required tests:

- Exact five-field legacy flat brief with `lane=i18n-rewrite` is accepted by validator and reaches one Writer outbox in isolated first tick.
- Same fixture without `lane` remains accepted.
- Same fixture with invalid `lane` fails closed with zero Writer/outbox.
- Same fixture with an unrelated extra key still fails closed with zero Writer/outbox.
- Existing multilingual pipeline tests pass.
- `git diff --check` passes.

## Anti-Expansion

Do not:

- Hand-edit production brief bytes.
- Run production coordinator/resume/reseed/replacement/provider/publisher before repair review.
- Add generic schema union logic.
- Globally allow unknown brief fields.
- Move authority to registry, status artifacts, new FSM, new ledger, or migration database.
- Modify coordinator, promotion, publisher, queue runner, registry format, production roots, or public content for this repair unless a later RCA proves a separate root cause.
- Treat `COORDINATOR_ERROR_OBSERVABILITY_GAP_ONLY` as sufficient; preserving the error message may be useful later, but it does not fix the functional contract gap.

## Limits

I did not modify RCA/source/test, did not run production, and did not commit or push. The supplemental live queue probe was read-only and used only to confirm same-shape failed brief/registry facts.

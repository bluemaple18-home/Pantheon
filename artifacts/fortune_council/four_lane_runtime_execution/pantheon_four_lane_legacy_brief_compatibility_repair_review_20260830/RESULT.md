# Pantheon Four-Lane Legacy Brief Compatibility Repair Review Result

## Verdict

GO

This GO authorizes only mainline commit/integration of the bounded Repair. It is not a production retry, activation, LaunchAgent load, provider call, publisher run, or four-lane production acceptance GO.

## P0/P1 Findings

- P0: none.
- P1: none.

## Reviewed Candidate

- Candidate worktree: `<candidate-worktree>`
- Base: `origin/main=73180233275840b0ab0e101f246e495ee6815fc9`
- Candidate status: uncommitted.
- Tracked source diff:
  - `scripts/agy_multilingual_pipeline.py`
  - `tests/test_agy_multilingual_pipeline.py`
- Bounded candidate artifacts observed:
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-LEGACY-BRIEF-COMPATIBILITY-REPAIR-20260830.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/EVIDENCE.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/RESULT.md`

## Contract Review

Accepted.

- Diff scope is bounded: tracked diff is only `scripts/agy_multilingual_pipeline.py` and `tests/test_agy_multilingual_pipeline.py`; no `uv.lock`, plist, publisher, manifest, registry, actor, or production tracked drift was present.
- Global `validate_translation_brief()` remains strict: it still rejects any key set other than canonical four fields with the same `translation brief fields are strict` error.
- Canonical producer remains four-field: `prepare_translation_run()` still writes only `schema_version`, `run_id`, `mode`, and `articles`.
- Compatibility is placed at the registered translation run read seam, not in the global validator.
- Trusted binding is narrow:
  - registry state path is derived from the canonical `translation-runs/<run_id>` parent;
  - trusted state must match `run_id`;
  - trusted state `run_dir` must match `run_dir.resolve()`;
  - trusted state `lane` must be exactly `i18n-rewrite`;
  - trusted state `identity_envelope` must match `translation_identity_envelope(source_article_id, "i18n-rewrite")`;
  - forgeable brief `lane` alone is insufficient.
- Accepted legacy shape is only canonical four fields plus exact extra key `lane` with string value `i18n-rewrite`.
- After trusted binding passes, the loader constructs an in-memory four-field brief and runs the original strict validator before downstream use.
- Registered brief reread seams were updated to use the narrow loader/normalizer for enqueue idempotency, replacement, approved-stage planning/loading, reviewer-reject authorization, fresh writer, continuation, editorial review, and apply.
- Replacement-generated briefs remain canonical four-field.
- Idempotency is preserved: replayed first-writer legacy runs create one outbox job, not duplicates.

## Independent Verification

Commands were run read-only against the candidate worktree; no candidate source/test/evidence files were modified.

- Targeted legacy/canonical slice:
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -k "legacy_rewrite_brief or canonical_translation_brief_still_reaches_first_writer_outbox or translation_brief_validator_keeps_canonical_four_field_contract" -p no:cacheprovider -q`
  - Result: `16 passed, 262 deselected`.
- Full affected multilingual test file:
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -p no:cacheprovider -q`
  - Result: `278 passed`.
- Coordinator boundary slice:
  - `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k "legacy_translation or translation_replacement or i18n_rewrite" -p no:cacheprovider -q`
  - Result: `23 passed, 364 deselected`.
- Python compile:
  - `compile()` over `scripts/agy_multilingual_pipeline.py` and `tests/test_agy_multilingual_pipeline.py`
  - Result: `compile: PASS`.
- Candidate diff check:
  - `git diff --check`
  - Result: PASS.
- Candidate status after verification:
  - unchanged: only the two modified tracked files plus bounded repair artifacts.

## Supplemental Negative Harness

Because candidate committed tests did not directly name every registry-path negative, I ran an independent ad hoc harness in temporary directories only. All cases failed closed before outbox creation:

- `unregistered_legacy_lane`: RED, `legacy translation brief lane context is invalid`, no outbox.
- `wrong_registry_run_dir`: RED, `legacy translation brief lane context is invalid`, no outbox.
- `wrong_parent_path_no_registry_authority`: RED, `legacy translation brief lane context is invalid`, no outbox.

This satisfies the review requirement that unregistered and wrong-run-path legacy briefs remain RED. For long-term regression coverage, mainline may optionally formalize these three ad hoc negatives as named tests before any production retry, but this is not a blocker for this bounded commit/integration GO.

## Production Read-Only Hash Check

I performed read-only SHA checks against the three live failed translation run brief/registry pairs before and after local verification. Hashes were unchanged.

| Run ID | Brief lane | State lane | State status | Brief SHA256 | State SHA256 |
|---|---:|---:|---:|---|---|
| `auto-i18n-ko-bb1bc3865ed466bac17a` | `i18n-new` | `i18n-new` | `failed` | `c4f91eedba60d839f95361358483c8174de4f9db6bb57d05e8b886d03856348f` | `c2b1ca693d5a38b2da2cc71384e569162dc6beb2771199be205e3483775772df` |
| `auto-i18n-ko-85d513b289d89dd9bf75` | `i18n-rewrite` | `i18n-rewrite` | `failed` | `4291007cadce2088390a55cb8a65005593f75c2a20514fcf23ee80dd26cb7365` | `1498ea53bf42d01107bb2cd268d6144d6a315af576524da14398df76e6571f4e` |
| `auto-i18n-en-aa637e1bf05d3ad21429` | `i18n-rewrite` | `i18n-rewrite` | `failed` | `bcd31d23f5d8455ea21fea205827afd267a29f4c4533b0064a80154fbd8d12f3` | `9bce7b085e306515e403d511ae7611223c88531b11e1f56f867ffb36ead02d14` |

Important limit: the candidate intentionally accepts only exact legacy `lane=i18n-rewrite`. The observed `i18n-new` legacy failed run remains outside this Repair by design and must not be used as proof that all legacy five-field briefs are now compatible.

## Repair Allowlist

Allowed for commit/integration:

- `scripts/agy_multilingual_pipeline.py`
  - constants for canonical translation brief fields and exact legacy rewrite lane;
  - registered-state path derivation;
  - legacy rewrite context validation using trusted state;
  - registered brief normalization to four fields before strict validation;
  - replacement of direct registered `brief.json` loads with the narrow loader/normalizer.
- `tests/test_agy_multilingual_pipeline.py`
  - canonical validator strictness;
  - exact legacy `i18n-rewrite` RED→GREEN;
  - canonical first-writer path still works;
  - unknown extra fields stay RED;
  - brief lane mismatch/nonstring stays RED;
  - state lane mismatch stays RED;
  - missing/type drift stays RED;
  - replay idempotency/no duplicate outbox.
- Bounded review/repair artifacts only.

Not allowed under this GO:

- loosening `validate_translation_brief()`;
- accepting arbitrary `lane` extras;
- accepting `i18n-new` legacy briefs;
- trusting brief `lane` without registry binding;
- path-string guessing without registry state;
- mutating production brief/state bytes;
- changing publisher, aggregate, lane routing, LaunchAgents, plist authority, registry format, manifest generation, provider/reviewer behavior, or creating any new authority/registry/FSM.

## Required Tests Before Production Retry

Before any production retry or activation acceptance, rerun at minimum:

- the targeted legacy/canonical slice above;
- the full `tests/test_agy_multilingual_pipeline.py`;
- the coordinator boundary slice above;
- Python compile;
- `git diff --check`;
- a production read-only pre/post hash check for the exact run(s) being retried;
- exact production retry canary on an `i18n-rewrite` legacy run only, with outbox/idempotency evidence and no mutation of the original failed brief/state except through the already-authorized runtime path.

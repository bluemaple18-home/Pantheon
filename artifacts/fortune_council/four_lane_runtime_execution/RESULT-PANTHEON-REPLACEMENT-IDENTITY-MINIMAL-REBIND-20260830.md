---
id: RESULT-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830
status: reviewed_local_candidate
card: CARD-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830
production_used: false
remote_used: false
provider_used: false
publish_used: false
promotion_used: false
service_used: false
push_used: false
---

# Replacement Identity Minimal Rebind Result

## Superseded thin-candidate evidence (non-acceptance)

This section preserves historical thin-candidate evidence only; it is not current completion evidence and must not be read as the accepted result.

- `test_translation_replacement_future_producer_writes_canonical_identity` failed as expected: replacement state lacked `routing_schema_version`.
- `test_exact_translation_replacement_plan_only_rebinds_existing_identity_without_mutation` failed as expected: plan-only receipt lacked `identity_rebind`.

### Superseded observations

- Future `enqueue_translation_replacement` now validates terminal routing identity and writes replacement `routing_schema_version`, `mode`, `lane`, and `identity_envelope`.
- Existing exact replacement plan-only reports Layer-A `identity_rebind` with `planned_mutation_count: 0` and no write set.
- Existing exact replacement execute rebinds only missing identity fields and preserves status, result absence, timestamps, attempts absence, lineage, and business outcome files.
- Wrong lane, wrong digest, and conflicting identity envelope fail closed without mutation.
- Existing exact replacement create path still creates one replacement and does not invoke runner, provider, or publisher.

## Superseded changed paths (non-current)

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830.md`
- `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830.md`

## Superseded LOC (non-current)

- source added: 83 LOC (`scripts/agy_multilingual_pipeline.py` 39, `scripts/agy_gemini_coordinator.py` 44)
- tests added: 150 LOC

## Superseded verification (non-current)

- `uv run pytest -q tests/test_agy_gemini_coordinator.py::test_translation_replacement_future_producer_writes_canonical_identity` -> RED, failed on missing `routing_schema_version`.
- `uv run pytest -q tests/test_agy_gemini_coordinator.py::test_exact_translation_replacement_plan_only_rebinds_existing_identity_without_mutation` -> RED, failed on missing `identity_rebind`.
- `.venv/bin/pytest -q <8 exact replacement selectors>` -> PASS, 36 passed.
- `.venv/bin/pytest -q <5 seed/lane-cycle replacement selectors>` -> PASS, 12 passed.
- `.venv/bin/pytest -q tests/test_agy_gemini_coordinator.py --maxfail=3` -> FAIL, 3 failed / 10 passed before stop; failures are existing campaign locale-plan coverage strictness, outside this card's replacement identity surface.

## Superseded delta evidence (non-current)

- plan-only mutation count: 0
- fail-closed cases: wrong lane, wrong digest, conflicting identity envelope
- production used: false
- remote used: false
- provider used: false
- publish used: false
- promotion used: false
- service used: false
- push used: false

## Superseded remaining risk (non-current)

- Full `tests/test_agy_gemini_coordinator.py` is not green because early campaign E2E fixtures fail with `external locale plan coverage fields are strict for article-01`. This was observed outside the touched replacement identity path and was not repaired under this card.

---

## Current candidate supersession — production-shape repair

Status: `reviewed_local_candidate`.

The earlier thin candidate above is superseded as completion evidence because it used an active/pristine replacement shape. Current candidate evidence is the production-shaped repair below.

Current exact target:

- source run: `auto-i18n-en-aa637e1bf05d3ad21429`
- target run: `auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- registry: `queue/runs/1bf0bbc61ff8d10e808f6923.json`
- article: `ASTRO-BASE-03`
- lane: `i18n-rewrite`
- reason: `LOCALE_PLAN_VALIDATION`

Delivered:

- future producer writes `routing_schema_version`, `mode`, `lane`, `identity_envelope`;
- new `reconcile-translation-replacement-identity` command requires explicit source/target IDs, registry path, current roots, and `--publisher-state-root`;
- runtime command does not read forensics branch;
- plan-only reports `missing_fields=["identity_envelope"]`, `planned_mutation_count=0`, and expected execute write set = lock coordination artifact + one-shot receipt + exact registry;
- execute writes only the lock, one-shot receipt, and exact registry `identity_envelope`;
- preserved: registry existing keys/values, result, last_job_id, timestamps, root brief/candidate/review.json, attempts/01..03 file set/bytes, empty continuation directory;
- receipt recovery covers absent+before, present+before, present+after, replay without matching receipt, external run dir, post-receipt registry clobber, and third-state fail closed;
- promotion source diff remains 0.

Verification:

- `.venv/bin/python -m py_compile scripts/agy_multilingual_pipeline.py scripts/agy_gemini_coordinator.py` -> PASS
- focused pytest selectors -> `58 passed`
- related pytest selectors -> `369 passed`
- affected pytest run -> `339 passed / 5 known unrelated failures`
- `git diff --check` -> PASS
- independent re-review -> `REVIEW_GO / no P0-P2`
- commit/push/production -> not performed

Known residual:

- Commit remains pending for Mainline.
- The 5 affected-run failures are known unrelated failures outside replacement identity.

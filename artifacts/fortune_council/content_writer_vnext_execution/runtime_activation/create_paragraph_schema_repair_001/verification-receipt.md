# Create paragraph schema repair 001 verification receipt

## Scope

- Card: `CARD-CONTENT-WRITER-VNEXT-CREATE-PARAGRAPH-SCHEMA-REPAIR-001`
- Requested card object: `6cfb3d0ed56` unavailable in local Git object DB
- Card read from: `6cfb3d0ed5`
- Mutations: allowlist only
- Explicitly not touched: replacement run, Gemini, runtime-v2 queue/state, publish, transaction, tag, push, deploy
- Existing dirty file intentionally excluded: `uv.lock`

## Repair summary

- Added a create provider bodySections schema helper that removes only paragraph string `minLength` and `maxLength`.
- `candidate_schema("create")` and `_article_json_schema()` remain unchanged, so canonical/hard local gates still retain paragraph length bounds.
- Added a focused create short-paragraph hydration test proving transport can reach local `quality_findings`, which emits `paragraph_length` and maps bounded create repair fields to `bodySections`.
- Kept rewrite provider schema behavior covered and unchanged.

## REVIEW_BLOCKED P1 repair

- Finding: `normalize_new_output_contract()` read paragraph length bounds from the relaxed create provider schema and returned `None` after transport min/max were removed.
- Fix: keep the provider response schema identity check, but read paragraph count/length bounds from `candidate_schema("create")`.
- Regression: added local coverage that provider paragraph schema lacks min/max while normalization still reflows paragraphs via canonical bounds.
- Focused Gemini regression: `test_runner_normalizes_new_description_and_paragraph_bounds_without_retry` now processes once without `V4BrokerFailure`.

## Verification

- RED: focused create provider schema test failed before repair because create paragraph item still had min/max.
- GREEN focused: `3 passed`
- SEO copy targeted: `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q` => `132 passed`
- Publisher related regression: `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q` => `112 passed, 1 warning`
- REVIEW_BLOCKED focused: `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py::test_create_normalization_reads_paragraph_bounds_from_canonical_schema tests/test_agy_gemini_outbox.py::test_runner_normalizes_new_description_and_paragraph_bounds_without_retry -q` => `2 passed`
- REVIEW_BLOCKED SEO copy targeted: `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q` => `133 passed`
- REVIEW_BLOCKED publisher regression: `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q` => `112 passed, 1 warning`
- py_compile: `.venv/bin/python -m py_compile scripts/agy_seo_copy_pipeline.py scripts/agy_content_publisher.py` => PASS
- JSON parse: `negative-matrix.json` => PASS
- `git diff --check` => PASS

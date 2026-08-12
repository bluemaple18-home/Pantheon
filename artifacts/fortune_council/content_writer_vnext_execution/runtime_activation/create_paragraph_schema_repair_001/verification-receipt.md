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

## Verification

- RED: focused create provider schema test failed before repair because create paragraph item still had min/max.
- GREEN focused: `3 passed`
- SEO copy targeted: `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q` => `132 passed`
- Publisher related regression: `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q` => `112 passed, 1 warning`
- py_compile: `.venv/bin/python -m py_compile scripts/agy_seo_copy_pipeline.py scripts/agy_content_publisher.py` => PASS
- JSON parse: `negative-matrix.json` => PASS
- `git diff --check` => PASS

# CARD-CONTENT-REWRITE-001 runtime verification

## Scope

- `app/web/static/article-meta.js`
- `tests/test_web.py`
- `artifacts/fortune_council/content_rewrite_execution/evidence/runtime/verification.md`

## Contract checked

- Custom article bodies are returned as authored and are not passed through `enrichArticleBody()`.
- Fallback article bodies are generated as a small reader-facing article body without site-management language.
- URL, layout, CSS and schema fields were not changed.

## Verification

```text
.venv/bin/python -m pytest tests/test_web.py
28 passed, 1 warning

git diff --check
PASS

node --check app/web/static/article-meta.js
PASS
```

## Notes

- The pytest warning is from `starlette.testclient` deprecating the current `httpx` integration.
- The first pytest attempt failed because the old publication-standard test still expected auto-enriched custom bodies; the test was updated to assert the new runtime contract instead.

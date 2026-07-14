# Article Update Date 2026-07-14

## Scope

- Updated article routes: 94
- Refresh date: `2026-07-14`
- Untouched article baseline: `2026-07-12`
- Layout: unchanged; only article metadata, visible update date, static shell output, and asset cache versions changed.

## Synchronized surfaces

- FastAPI article SSR: `article:modified_time`, JSON-LD `dateModified`, and visible `<time data-article-updated>`.
- Cloudflare/static prerender shells under `app/web/seo/articles/`.
- Article JavaScript cache-bust versions so refreshed body libraries are not served from an older browser cache.

## Verification

- `tests/test_web.py`: 37 passed
- `node --check app/web/static/article-meta.js`: passed
- `node --check app/web/static/article.js`: passed
- `python -m py_compile main.py scripts/prerender_article_shells.py`: passed
- `git diff --check`: passed

The full test suite still has two pre-existing Ziwei provider expectation failures (`pantheon_ziwei` vs `iztro`); they are unrelated to this date/content change.

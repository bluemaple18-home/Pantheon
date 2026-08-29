# Evidence

## RED

Command:

`uv run --frozen pytest tests/test_agy_multilingual_pipeline.py -k "legacy_rewrite_brief or canonical_translation_brief_still_reaches_first_writer_outbox or translation_brief_validator_keeps_canonical_four_field_contract" -q`

Before source repair:

- `11 failed, 5 passed, 262 deselected`
- Legacy registered `i18n-rewrite` briefs failed at `ValueError: translation brief fields are strict`.
- This reproduced the isolated five-field legacy brief gap before any source edit.

## GREEN

Target repair tests:

`16 passed, 262 deselected in 0.15s`

Full affected multilingual test file:

`278 passed in 0.90s`

Coordinator boundary slice:

Command:

`uv run --frozen pytest tests/test_agy_gemini_coordinator.py -k "legacy_translation or translation_replacement or i18n_rewrite" -q`

Result:

`23 passed, 364 deselected in 0.11s`

## Compile And Diff

Python compile:

`uv run --frozen python -m py_compile scripts/agy_multilingual_pipeline.py tests/test_agy_multilingual_pipeline.py`

Result: passed.

Whitespace:

`git diff --check`

Result: passed.

Diff budget:

- `scripts/agy_multilingual_pipeline.py`: `102` insertions, `12` deletions.
- `tests/test_agy_multilingual_pipeline.py`: `244` insertions, `0` deletions.

Source anti-expansion scan:

`git diff -- scripts/agy_multilingual_pipeline.py | rg -n "pop\\(|ignore|discard|schema union|migration registry|FSM|allowed extras|unknown extra|coordinator|publisher|manifest|LaunchAgent|promotion|deploy"`

Result: no matches.

## Production Preservation

Worktree production brief discovery:

`find .work -type f -name 'brief.json' | wc -l`

Result: `0`

Production-sensitive tracked path diff:

`git diff --name-only -- app data config .work`

Result: no output.

Scoped status:

- Modified: `scripts/agy_multilingual_pipeline.py`
- Modified: `tests/test_agy_multilingual_pipeline.py`
- Added: repair card/result/evidence artifacts only.

Provider/reviewer/publisher calls:

- No production provider, reviewer, or publisher process was run.
- New outbox tests use isolated pytest temporary roots.
- The legacy happy-path test asserts first Writer `ExternalJobPending`, exactly one outbox request after replay, no `candidate.json`, and no `review.json`.

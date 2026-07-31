# EV-CANARY-I18N-NEW-001

## Decision

```text
status: NO-GO
lane: i18n-new
run_id: manual-i18n-new-canary-v1-20260731-en-v2-mbti-pair-intp-esfj-work
locale: en
source_article_id: V2-MBTI-PAIR-INTP-ESFJ-WORK
candidate_id: null
publisher_decision: NOT_INVOKED
release_commit: null
release_tag: null
public_result: none
```

## Pre-canary replay

The newest production `en` translation run from v0.3.185 was resumed with the
repaired runtime. Its previously stored plan no longer surfaced an untyped
`ValueError`; it failed closed as `LocalePlanValidationError`. Because the old
plan remained contract-invalid, it was not treated as a canary success.

## Fresh canary evidence

- A fresh real `en` run was created from the current public article source.
- Source SHA:
  `ebc616bcd9e12d6d94048d8425478a63819bd2744fce27b585472577f7d169f6`.
- Writer `0d019484...`: production attempt succeeded and returned a schema-valid
  response envelope.
- Pipeline terminal state:
  `LocalePlanValidationError` at `2026-07-31T10:48:17+08:00`.
- Run directory contains only `brief.json`; no candidate or review exists.

## Acceptance mapping

- real provider transport: PASS
- typed post-transport failure: PASS
- locale plan contract: FAIL
- fresh candidate／Publisher／release／public result: NOT REACHED

This is evidence that the raw `ValueError` boundary was narrowed, but the
production prompt／normalization still does not reliably produce a valid locale
plan. A new repair slice is required; repeating the same canary is not
authorized.

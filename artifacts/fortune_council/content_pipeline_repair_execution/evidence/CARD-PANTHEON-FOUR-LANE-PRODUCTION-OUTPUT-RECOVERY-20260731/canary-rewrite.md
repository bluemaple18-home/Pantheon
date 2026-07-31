# EV-CANARY-REWRITE-001

## Decision

```text
status: NO-GO
lane: rewrite
run_id: legacy-manual-canary-v1-20260731-astrology-0003-astro-base-03
source_article_id: ASTRO-BASE-03
candidate_id: null
publisher_decision: NOT_INVOKED
release_commit: null
release_tag: null
public_result: none
```

## Input selection

The standard seeder first selected the real unattempted article
`ASTRO-BASE-03`, but failed closed on a historical run identity collision. The
old state points to a disappeared 2026-07-28 worktree. It was preserved.

A unique manual-canary run was then registered from the current production
article and source SHA using the same validated rewrite brief builder. No
fixture was used and no historical state was reset.

## Evidence

- Writer `99636d33...`: production attempt succeeded.
- Reviewer `0620af80...`: terminal
  `GeminiApiFailure / API_RATE_LIMITED / QUOTA`.
- Run status: `failed` at `2026-07-31T10:45:51+08:00`.
- Run directory contains `brief.json` and `public-brief.json` only.
- No candidate、approval、Publisher transaction、release commit or tag exists.

## Acceptance mapping

- real eligible source: PASS
- real Writer transport: PASS
- fresh candidate: FAIL
- bounded failure classification: PASS
- Publisher／release／public verification: NOT REACHED

The quota failure is terminal under the production pool contract. No account
fallback or manual resend was performed.

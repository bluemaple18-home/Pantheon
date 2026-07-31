# EV-CANARY-I18N-REWRITE-001

## Decision

```text
status: NO-GO
lane: i18n-rewrite
run_id: manual-i18n-rewrite-canary-v1-20260731-en-expansion-50d-fortune-0039
locale: en
source_article_id: EXPANSION-50D-FORTUNE-0039
candidate_id: null
publisher_decision: NOT_INVOKED
release_commit: null
release_tag: null
public_result: none
```

## Evidence

- Source is a real legacy article previously released through rewrite v0.3.132.
- Current source SHA:
  `df562de9df35d31fbeed3d6b9a115280f8f6fd4faa606d2dab16c3998174aa1d`.
- Initial Writer job `401ced5c...` failed with
  `GeminiApiFailure / API_HTTP_ERROR / PROVIDER_UNAVAILABLE`.
- The allowlisted transport contract produced the same logical
  `request_sha256` with `transport_attempt=1` (`57193118...`) and
  `transport_attempt=2` (`8824e476...`).
- Both bounded attempts failed with the same closed error classification.
- The run terminalized as `failed` at `2026-07-31T10:50:55+08:00`.
- No candidate、review、approval、Publisher transaction or release exists.

## Acceptance mapping

- real rewrite source and locale input: PASS
- bounded retry identity: PASS
- provider transport: FAIL after the full bounded budget
- candidate／native-quality review／Publisher／release: NOT REACHED

No fourth attempt, account fallback outside the allocator, or new canary was
performed.

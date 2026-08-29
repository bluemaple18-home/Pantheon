# CARD-PANTHEON-FOUR-LANE-LEGACY-BRIEF-COMPATIBILITY-REPAIR-20260830

## Mission

Repair the legacy translation brief compatibility gap in the multilingual pipeline at exact base `origin/main=73180233275840b0ab0e101f246e495ee6815fc9`.

RCA and independent review status: GO.

Root cause: `LEGACY_BRIEF_CROSS_VERSION_CONTRACT_GAP`.

## Scope

Allowed source file:

- `scripts/agy_multilingual_pipeline.py`

Allowed test file:

- `tests/test_agy_multilingual_pipeline.py`

Allowed artifact writes:

- This card.
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/RESULT.md`
- Minimal evidence files in the same result directory.

Any need for a second source or test file is `BLOCKED`.

## Implementation Contract

Add minimal deterministic legacy compatibility at the existing validation or hydration seam for translation briefs.

Only the exact historical extra key `lane` may be accepted, and only when all conditions hold:

- `lane` is a string.
- `lane == "i18n-rewrite"`.
- The value is bound to existing trusted caller/run/brief context that authorizes the `i18n-rewrite` lane.
- The brief is normalized to the canonical four-field shape before it flows through the existing strict validator.

Forbidden approaches:

- Blindly popping or ignoring `lane`.
- Accepting arbitrary lane values.
- Accepting unknown extras.
- Adding generic allowed-extras logic.
- Adding schema unions, migration registries, FSMs, or broader runtime machinery.
- Changing canonical producer output.
- Fixing coordinator observability where it only records `error_type`.

If no trusted lane context exists in the current function, pass the narrowest trusted context through the existing call chain in `scripts/agy_multilingual_pipeline.py`. If this cannot be done credibly within the single source allowlist, stop as `BLOCKED`.

## TDD Contract

First add RED coverage using exact three legacy shapes or representative immutable fixtures.

After repair:

- The three legacy shapes must reach legal first Writer `ExternalJobPending` with `outbox=1`, using an isolated temporary root and provider count zero.
- Unknown extra fields remain rejected.
- Lane mismatch remains rejected, including `new`, `rewrite`, `i18n-new`, and arbitrary values.
- Non-string `lane` remains rejected.
- Missing canonical fields remain rejected.
- Type drift remains rejected.
- Canonical four-field brief behavior remains unchanged.
- Same-generation rerun and idempotency do not duplicate outbox jobs.

Run affected multilingual tests and necessary coordinator boundary tests if they do not require editing outside the allowlist.

Also run:

- Python compile check for the changed source and tests.
- `git diff --check`.
- Source budget and anti-expansion inspection.

## Production Safety

Forbidden:

- Production retry.
- Rule24/Rule25 promotion or activation.
- LaunchAgent changes.
- Manual production brief, registry, or queue edits.
- Coordinator, runner, publisher, manifest, or guard changes.
- Commit, push, tag, or deploy.

Required preservation evidence:

- Production three brief bytes before and after are unchanged.
- Production registry, queue, and content bytes before and after are unchanged.
- Provider, reviewer, and publisher remain zero.

## Delivery

Deliver result to:

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/RESULT.md`

Final status: `RE_REVIEW_REQUESTED`.

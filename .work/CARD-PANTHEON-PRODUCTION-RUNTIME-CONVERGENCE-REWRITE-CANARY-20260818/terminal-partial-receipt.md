# Production runtime convergence rewrite canary terminal receipt

status: `PARTIAL`
recorded_at: `2026-08-18T11:16:00+08:00`
card_source_sha: `aab1eec46a2315a2648cc0d1495f958dcc098b9b`

## Verdict

- Rewrite canary: `PASS`
- Stale translate convergence: `PASS`, formally moved to terminal failed state
- Production Publisher scheduler: `NOT RESTORED`, `com.pantheon.agy-content-publisher` remains absent
- Overall: `PARTIAL`, not full `GO`

## Facts

- Target rewrite run: `legacy-auto-sweep-v1-astrology-0003-astro-base-03`
- Target article: `ASTRO-BASE-03`
- Publisher content commit produced by the canary: `45942c29710fc58916addb8862f92c90444b29e8`
- Release tag produced by the canary: `v0.3.368`
- Public URL check: `https://www.mysticpantheon.com/articles/astrology/astrology-0003` returned HTTP 200
- Transaction state: no `state/transaction-*` directory remained after the normal exact transaction
- Old active translate run: `auto-i18n-ja-3a39827aeb778de1957f`
- Old translate final state: `failed`, `error_type=GeminiCliFailure`, `error_code=CLI_NONZERO`, `transport_attempts=3`

## Scheduler stop reason

The task card target runtime is `aab1eec46a2315a2648cc0d1495f958dcc098b9b`. The canary correctly produced and pushed content commit `45942c29710fc58916addb8862f92c90444b29e8`, but the Publisher LaunchAgent is still absent. Restoring it safely would require a second runtime promotion/readiness/bootstrap sequence outside this card's bounded target, and RunAtLoad could trigger another non-authorized publish. Therefore the scheduler was left stopped and the terminal verdict is `PARTIAL`.

## Evidence files

- `live-recovery/exact-rewrite-deployment-preflight.json`
- `live-recovery/exact-rewrite-dry-run.json`
- `live-recovery/exact-rewrite-normal-transaction.json`
- `live-recovery/exact-rewrite-normal-transaction.stderr.log`
- `live-recovery/active-translate-status-before.json`
- `live-recovery/active-translate-cycle-exact.json`
- `live-recovery/active-translate-cycle-exact.stderr.log`
- `live-recovery/normal-scheduler-publisher-dry-run-after-canary-manifest-sha.stderr.log`

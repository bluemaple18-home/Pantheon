# G8 v0.3.370 adoption/reset authorization request

Status: `BLOCKED / DO NOT AUTHORIZE`

This document is not an authorization. It is the bounded scope that would need a fresh human approval only after the blockers in `execution-contract.json` are cleared and revalidated.

## Exact Scope That Is Not Yet Authorizable

- Adopt production runtime actor/manifest from actor `db9fb4343df212fd3b65546b017aba159620a058`, manifest `d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e`, generation `g34-db9fb434-20260822T041850Z` to release `v0.3.370` commit `b0950d4c436cc902e17ac110b579b35b84aa53e4`.
- Restage coordinator, four lanes, and Publisher exact run `auto-i18n-en-614aa4dc3542ab2c5637` through the existing installers only.
- Run exactly one Publisher activation-only reset through `scripts/install_agy_gemini_coordinator_launchd.sh --reset-publisher-activation-only`.
- Produce a fresh `publisher-reset-receipt.json` with one approved correlation id, target generation, post-reset Publisher identity, and other-six unchanged proof.

## Current Blockers

- Local `origin/main` ref is `5a9103785ebfc8d5a28fa8188def6069beb12d88`, not required base `eb2ddd8157901e8764ffcc5fd8a5c68822fa357c`; this card did not fetch because Git ref mutation is forbidden.
- CodeGraph is not initialized in this worktree.
- Formal read-only reconciler returned `BLOCKED / ALLOWLIST_REQUIRED` without `--allow-source-drift`.
- Current production has no `publisher-reset-receipt.json`; only Cycle 33 `ROLLBACK_COMPLETE` failure receipt exists.

## Forbidden Extensions

No canary, Publisher child, activation beyond Publisher reset, deploy, tag, push, schedule, steady autonomy, replacement task, or retry is requested here.

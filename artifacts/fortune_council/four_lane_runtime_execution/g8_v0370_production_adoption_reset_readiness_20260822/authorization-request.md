# G8 v0.3.370 adoption/reset authorization request

Status: `BLOCKED / DO NOT AUTHORIZE`

This document is not an authorization. It is a phase-split contract for the bounded scope that could be requested only after pre-authorization blockers are cleared and revalidated.

## Exact Scope That Is Not Yet Authorizable

- Adopt production runtime actor/manifest from actor `db9fb4343df212fd3b65546b017aba159620a058`, manifest `d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e`, generation `g34-db9fb434-20260822T041850Z` to release `v0.3.370` commit `b0950d4c436cc902e17ac110b579b35b84aa53e4`.
- Restage coordinator, four lanes, and Publisher exact run `auto-i18n-en-614aa4dc3542ab2c5637` through the existing installers only.
- Run exactly one Publisher activation-only reset through `scripts/install_agy_gemini_coordinator_launchd.sh --reset-publisher-activation-only`.
- Produce a fresh `publisher-reset-receipt.json` with one approved correlation id, target generation, post-reset Publisher identity, and other-six unchanged proof.

## Current Pre-Authorization Blockers

- Git authority is not converged. This repair observed local `main` at `58e6e0bae776fa22100b2d32d74a709e827a6ae4`, local `origin/main` at `5a9103785ebfc8d5a28fa8188def6069beb12d88`, repair HEAD at `6de8e4874d77aacce90ffee3e265ed527686a0f0`, and candidate parent `eb2ddd8157901e8764ffcc5fd8a5c68822fa357c`; no fetch or ref mutation was run.
- Formal reconciler with the locked canonical observation returned `BLOCKED / REMOTE_DIVERGED` for the repair HEAD probe. The original `BLOCKED / ALLOWLIST_REQUIRED` result was only an argv early guard and did not enter reconciliation.
- The current candidate `release-observation.json` is advisory only; the usable canonical observation is `artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json` with sha256 `839dcb7b0f9009779ccc4966ca98e0f6d5e0619de1cd5be75fdf25001c4d20a9`.
- Promotion plan readiness is not proven with exact allowlist, capacity receipt, target digest, rollback bundle, and machine-local locator binding.

## Not Pre-Authorization Blockers

- Production not yet being adopted to `v0.3.370` is expected before any authorized adoption/reset.
- The future authorized Publisher reset success receipt is expected to be absent before that reset runs.

Both facts become hard gates after adoption/reset and before any canary.

## Post-Adoption/Reset Gate Before Canary

Before any canary, a fresh formal reconciliation must return GO with actor head and manifest actor head equal to the current main authority, a fresh Publisher reset success receipt must exist for the authorized correlation id, and Rule 24 / Rule 25 production readiness must be rerun for the post-adoption target phase.

## Forbidden Extensions

No canary, Publisher child, activation beyond Publisher reset, deploy, tag, push, schedule, steady autonomy, replacement task, or retry is requested here.

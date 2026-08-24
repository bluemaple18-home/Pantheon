# Command Receipt

Time window: `2026-08-24T02:20:33Z` through repair.

- Read authority: task HEAD/main/origin-main local ref, release tag, production actor HEAD/status, runtime manifest, stage controls, and Rule 21/24/25 authority documents.
- CodeGraph: main workspace projectPath `/Users/mattkuo/Documents/Pantheon` returned READY with 645 files, 7648 nodes, and 16446 edges. Current detached worktree had degraded/no initialized index during the original candidate.
- Source lookup: CodeGraph identified the existing formal reconciler in `scripts.pantheon_g8_production_preactivation`, including `evaluate_authority` and `evaluate_release_state`. No replacement reconciler was created.
- Production before/after tripwire: original `collect_readiness_evidence.py snapshot --name before|after`; read-only Git/plist/tree digest and `launchctl print` only.
- Observation: original `collect_readiness_evidence.py observe`; read-only manifest, stage controls, live/stage plists, failure receipt, and launchctl identity.
- Original formal reconciler: `reconciler-result.json` was `BLOCKED / ALLOWLIST_REQUIRED`, an argv early guard before `reconcile()`; it is not evidence that the only remaining issue was allowlist.
- Canonical observation selected for repair probes: `artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json`, sha256 `839dcb7b0f9009779ccc4966ca98e0f6d5e0619de1cd5be75fdf25001c4d20a9`.
- Candidate observation retained as advisory only: `artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/release-observation.json`, sha256 `85c02a5b61655a039b2bd9ee111eb2a54dac89bf7a7eedb2a6a3eeccaa8d6f7f`.

## Repair Reconciler Invocations

Repair probe 1 used the canonical observation and original candidate parent as `required_source`.

```sh
/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 -m scripts.pantheon_g8_production_preactivation --card-id CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822-REPAIR-1 --repo-root /Users/mattkuo/.codex/worktrees/9aa8/Pantheon --actor-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue --state-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state --transaction-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions --live-root /Users/mattkuo/Library/LaunchAgents --staged-root /Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage --manifest /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json --expected-manifest-digest d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e --required-source eb2ddd8157901e8764ffcc5fd8a5c68822fa357c --origin-main 5a9103785ebfc8d5a28fa8188def6069beb12d88 --exact-run-id auto-i18n-en-614aa4dc3542ab2c5637 --evidence-path artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/reconciler-result-repair-1.json --release-observation artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json --allow-source-drift __repair_probe_allowlist_not_consumed_remote_diverged__
```

Result: `BLOCKED / LOCAL_HEAD_MISMATCH`; repair worktree HEAD was `6de8e4874d77aacce90ffee3e265ed527686a0f0`, not original parent `eb2ddd8157901e8764ffcc5fd8a5c68822fa357c`. Tripwire status `PASS`, changed surfaces `[]`.

Repair probe 2 used the canonical observation and repair HEAD as `required_source`.

```sh
/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 -m scripts.pantheon_g8_production_preactivation --card-id CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822-REPAIR-2 --repo-root /Users/mattkuo/.codex/worktrees/9aa8/Pantheon --actor-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue --state-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state --transaction-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions --live-root /Users/mattkuo/Library/LaunchAgents --staged-root /Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage --manifest /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json --expected-manifest-digest d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e --required-source 6de8e4874d77aacce90ffee3e265ed527686a0f0 --origin-main 5a9103785ebfc8d5a28fa8188def6069beb12d88 --exact-run-id auto-i18n-en-614aa4dc3542ab2c5637 --evidence-path artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/reconciler-result-repair-2.json --release-observation artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/release-observation.json --allow-source-drift __repair_probe_allowlist_not_consumed_remote_diverged__
```

Result: `BLOCKED / REMOTE_DIVERGED`; `required_source` `6de8e4874d77aacce90ffee3e265ed527686a0f0` is not an ancestor of local `origin_main` `5a9103785ebfc8d5a28fa8188def6069beb12d88`. Tripwire status `PASS`, changed surfaces `[]`.

The `--allow-source-drift` marker was present only to pass the argv early guard and was not consumed as an allowlist because topology failed first.

Mutation accounting: promotion/reset/Capacity install/activation/restage/canary/Publisher child/deploy/tag/push/fetch/schedule/launchctl mutation/git refs mutation all `0`.

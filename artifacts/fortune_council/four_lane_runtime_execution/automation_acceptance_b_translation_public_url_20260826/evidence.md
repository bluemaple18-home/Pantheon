# Acceptance B Translation Public URL Evidence

status: `BLOCKED`
root_cause: `ACTIVE_RUN_REGISTRY_DANGLING`
sampled_at: `2026-08-28`

## Scope

- Card: `CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826`
- Target run: `auto-i18n-ja-1414b75a404721e95e74`
- Source article: `V2-TAROT-DEATH-MONEY`
- Source path: `/articles/tarot/tarot-1884`
- Source hash: `1088d4dfae649824b9691d260e1754e528295a2b877a79a1d8e665054fe6db23`
- Locale: `ja`
- Translation article id: `V2-TAROT-DEATH-MONEY:ja`

## Read-Only Baseline

- Worktree clean before production call.
- Current worktree HEAD: `3bf38cf014781474bc0acd114dd50ad0d8ea99e1`.
- CodeGraph degraded reason: CodeGraph is not initialized in this worktree.
- Runtime manifest:
  - actor head: `2ce431ec41f5187531d88b52dfa91cef0373d8b5`
  - manifest digest: `7dbedf4e8544675f6203c2d40f96afa561d961a2c7e5a445c8d1f821f0d369f9`
  - runtime digest: `1c4bc28cda62a56fcf31bf007fd7905c4a45a5e1ca6b9fb8d0e9bfcb94498d21`
  - generation: `g55-2ce431ec-gen05-runtime-promotion-plan-20260828`
- Rule25 readiness summary for gen05 runtime promotion: `READY`, `canary_created=false`, all seven capability labels present.
- Rule24 baseline: host available space sampled at `21283012` KiB, above the 20 GiB / 10% stop line for this bounded one-shot.

## Continuation State

`continuation/state.json`:

```json
{"abandoned_generations":[4],"completed_generations":[],"next_generation":5,"operation_id":"42b2d14947072732654bb169c4aaf317f2d649631ea33fb655a104bce08f28c9","run_id":"auto-i18n-ja-1414b75a404721e95e74","schema_version":1,"semantic_budget":1,"source_sha256":["1088d4dfae649824b9691d260e1754e528295a2b877a79a1d8e665054fe6db23"],"started_after_generation":3,"starting_review_sha256":"31b5d156a987a227adccbd3c02f37f609985983d4deca7c057fcd1c27c7155cd","status":"active","terminal_candidate_sha256":null,"terminal_review_sha256":null}
```

Generation files observed after the official one-shot:

```text
generations/04/external-plan.json
generations/04/partial-generation-decision.json
generations/04/plan-operation.json
generations/04/planning-result.json
generations/05/external-plan.json
generations/05/plan-operation.json
generations/05/planning-result.json
generations/05/source-ref-map.json
```

There is no `generations/06`.

## Official Entrypoint Run

Entrypoint class: `scripts.pantheon_content_runtime_manifest barrier-exec` wrapping `scripts.agy_gemini_coordinator ... cycle --exact-run-id auto-i18n-ja-1414b75a404721e95e74`.

First attempt was rejected by argparse before runtime mutation because `--exact-run-id` was placed before the `cycle` subcommand. Corrected run output:

```json
{"status":"blocked","reason":"active run registry is dangling","run_id":"auto-i18n-ja-1414b75a404721e95e74","active":5,"complete":0,"failed":0,"runner":{"status":"idle"},"new_matrix_sweep":null,"legacy_sweep":null}
```

Interpretation: official exact-run coordinator gate blocked before runner/provider work. The runner status was `idle`.

## Queue And Ledger Evidence

- Registry file for target run remained `status=active`.
- i18n-new lane outbox count after run: `0`.
- i18n-new lane processing count after run: `0`.
- i18n-new lane inbox count after run: `16`; no new outbox/processing work was created by this run.
- Ledger path: `<runtime-root>/state/ledger.json`.
- Target run appears in source published run `translation_run_ids`, but not in `translation_published_runs`.
- Publication transaction count for `auto-i18n-ja-1414b75a404721e95e74`: `0`.

## Service State

`launchctl list` did not contain these labels after the one-shot:

- `com.pantheon.agy-content-publisher`
- `com.pantheon.agy-gemini-coordinator`
- `com.pantheon.agy-gemini-new`
- `com.pantheon.agy-gemini-rewrite`
- `com.pantheon.agy-gemini-i18n-new`
- `com.pantheon.agy-gemini-i18n-rewrite`
- `com.pantheon.content-capacity-guard`

`pgrep` could not be used as corroborating process evidence because this host returned `sysmond service not found`.

## Mutation Accounting

- Provider calls: `0`
- Reviewer calls: `0`
- Publication transaction: `0`
- Tag: `0`
- Push: `0`
- Deploy: `0`
- Gen06 creation: `0`
- Manual queue/state edits: `0`
- Code/config edits: `0`

## Acceptance Mapping

- Public URL HTTP 200: not applicable; publication was blocked before publisher.
- Browser body verification: not applicable; publication was blocked before publisher.
- Canonical/hreflang verification: not applicable; publication was blocked before publisher.
- Registry/ledger/route uniqueness: target publication count remains `0`; no duplicate publication was created.
- Seven services stopped: PASS by `launchctl list` absence for all seven labels.

Final status is `BLOCKED`, not `GO`.

# CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825 RESULT

status: BLOCKED_CLI_LITE_ENTRYPOINT_UNPROVEN
card_id: CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825
dispatch_key: v1:ecfe5970adfedcb1d0edd6154de5eb8037758bc63d37c22e7806784c722b1d11
activation_token_received: act-v1:d0125fb015f42041f17d446ea71f81d2cf12207f8fe89e647c44426616812a02
thread_id: 01a0374e-7b37-7f21-b911-984089be8509
source_thread_id: 01a034b0-a14a-7562-bc18-a014d47bb3ad

## Summary

Repair is blocked because the formal Antigravity CLI entrypoint for the two fixed Lite roles could not be proven.

Required role contract:

- Writer: `gemini-3.5-flash-lite`
- Reviewer: `gemini-3.1-flash-lite`

No source/config/test change was made, because committing a route ID to an unproven CLI label would violate the card contract.

## CodeGraph Evidence

CodeGraph was queried before source decisions.

- `codegraph_status` for this worktree returned ready: 582 indexed files, 6925 nodes, 15331 edges.
- `codegraph_search(validate_antigravity_cli_capabilities)` located `scripts/agy_seo_copy_pipeline.py:145`.
- `codegraph_search(ANTIGRAVITY_MODEL_LABELS)` located `scripts/agy_seo_copy_pipeline.py:123`, with mappings only for non-Lite `gemini-3.5-flash` and `gemini-3.1-pro`.
- `codegraph_search(agy_gemini_model_routes)` located the formal route config seam through `MODEL_ROUTE_CONFIG_PATH`.

## RED Evidence

Current tracked config violates the fixed Lite role contract:

- `config/agy_gemini_model_routes.v1.json` has Writer `gemini-3.5-flash`.
- `config/agy_gemini_model_routes.v1.json` has Reviewer `gemini-3.1-pro`.

Current CLI capability mapping also has no Lite label mapping:

- `scripts/agy_seo_copy_pipeline.py` maps `gemini-3.5-flash` to `Gemini 3.5 Flash (Low)`.
- `scripts/agy_seo_copy_pipeline.py` maps `gemini-3.1-pro` to `Gemini 3.1 Pro (Low)`.

## Formal CLI Evidence

The card allowed at most one formal `models` inventory. The first sandboxed attempt was blocked by local sandbox permissions before model inventory; the authorized formal run completed.

Formal command:

`<user-home>/.antigravity/bin/agy-1.1.3 models`

Result:

- Exit: 0
- Lite labels exposed: none
- Selectable Gemini labels exposed:
  - `Gemini 3.7 Flash (High|Medium|Low)`
  - `Gemini 3.6 Flash (High|Medium|Low)`
  - `Gemini 3.5 Flash (High|Medium|Low)`
  - `Gemini 3.1 Pro (High|Low)`

The card allowed at most one minimal sandbox/plan smoke per Lite role if the label was not exposed. Only the two user-provided Lite display names from the task card were attempted; no other names were enumerated.

Writer smoke:

- Command model label: `Gemini 3.5 Flash Lite`
- Exit: 1
- Closed result: CLI rejected the model as not recognized.

Reviewer smoke:

- Command model label: `Gemini 3.1 Flash Lite`
- Exit: 1
- Closed result: CLI rejected the model as not recognized.

## Decision

The formal callable Lite seam is unproven.

Therefore this repair must not:

- map `gemini-3.5-flash-lite` or `gemini-3.1-flash-lite` to guessed CLI labels,
- retain or introduce non-Lite, Pro, 3.6, 3.7, or fallback role routes,
- bypass capability validation,
- classify this as a retryable quota/rate-limit condition.

## Changed Files

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825-RESULT.md`

No source, config, test, installer, runtime, queue/state, actor, publisher, promotion, activation, production job, tag, or push path was modified.

## Verification

- `git diff --check`: PASS
- `rg -n "\\[DBG-" scripts tests`: PASS, no matches
- `git status --short`: only this RESULT file before commit

No targeted source tests are run for a blocked result with no source/config/test changes.

## Remaining Risk

The only blocking gap is external: Antigravity must expose or document a formal callable entrypoint for:

- `gemini-3.5-flash-lite`
- `gemini-3.1-flash-lite`

Once that entrypoint is available, a follow-up repair can safely bind the exact Lite route IDs to proven CLI labels and add GREEN regression coverage.

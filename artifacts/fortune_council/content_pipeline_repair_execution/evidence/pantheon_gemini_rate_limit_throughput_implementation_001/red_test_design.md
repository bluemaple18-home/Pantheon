# Deterministic RED test design

## Observed seams

1. `seed_new_matrix_runs()` bounds its outer loop but registers every path returned by
   one `prepare_matrix_runs()` call before checking `max_new_runs`; a five-path fixture
   can therefore register five runs in one cycle.
2. `process_once()` calls `_claim_next()` before production pool admission. The allocator
   then commits an ordinal before any rate-limit knowledge exists, and state schema v1
   has no cooldown.
3. `_claim_next()` sorts opaque filenames only; it does not prefer a queued reviewer
   request over fresh writer requests.
4. `cycle_once(lane_mode=True)` advances one state per lane and has no new-only gate;
   all four lane runner plists invoke the same unconditional `process-once`.

## Ranked, falsifiable hypotheses

1. If the new-matrix amplification is caused by the inner registration loop, a fixture
   returning five single-article brief paths will observe five registered states where
   the contract expects exactly one.
2. If admission ordering is the cause of failure churn, a state with all three anonymous
   slots cooling will still move one outbox file to processing/archive and create a
   failure unless admission is moved before claim and ordinal commit.
3. If reviewer starvation is filename-driven, one reviewer request plus multiple writer
   requests with writer filenames sorting first will call writer first.
4. If new-only needs both coordinator and runner gates, coordinator filtering alone will
   still allow non-new lane `process-once` to claim queued work.

## RED commands and expected failure

Initial focused RED command:

```text
.venv/bin/python -m pytest -q \
  tests/test_agy_gemini_coordinator.py -k 'one_run_one_article or reviewer' \
  tests/test_agy_gemini_outbox.py -k 'cooldown or reviewer_priority or new_only'
```

The first executable RED will be added one behavior at a time:

- `SC-RATE-001`: five prepared paths; assert one registered run containing one article.
- `SC-RATE-004`: reviewer and writer outbox jobs coexist; assert next provider role is reviewer.
- `SC-RATE-002/003/005`: synthetic allocator clock and three anonymous slots; assert
  cooldown, denied zero deltas, expiry, eligible-only credential read and exact ordinals.
- `SC-RATE-006`: seam on/off coordinator and lane-runner fixtures.

RED is preserved in `red_green.md` with the exact command, failing assertion and pre-fix
behavior. Expectations will not be weakened to match the current burst.

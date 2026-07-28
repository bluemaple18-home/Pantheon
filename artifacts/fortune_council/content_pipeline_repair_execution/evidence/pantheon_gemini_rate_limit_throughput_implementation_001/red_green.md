# RED / GREEN evidence

## SLICE-RATE-001 deterministic RED

### SC-RATE-001 — new-matrix burst

Command:

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_seed_new_matrix_runs_registers_only_one_run_and_article_per_cycle
```

Pre-fix result: `FAIL`

```text
assert summary["created"] == 1
E assert 5 == 1
1 failed
```

The five-path fixture reproduced five registrations in one cycle. The expected value
was not changed to accept the burst.

### SC-RATE-004 — reviewer ordering

Command:

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py::test_runner_claims_reviewer_before_fresh_writers
```

Pre-fix result: `FAIL`

```text
assert result["job_id"] == reviewer["job_id"]
E AssertionError: opaque filename ordering selected a writer job
1 failed
```

The fixture deliberately creates a writer whose opaque job filename sorts before the
reviewer. Current `_claim_next()` selected that fresh writer instead of review-pending.

### SC-RATE-002/003/005 — durable admission

Command:

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_allocator.py::test_allocator_skips_cooling_slot_and_rejoins_after_expiry
```

Pre-fix result: `FAIL`

```text
AttributeError: module 'scripts.agy_gemini_allocator' has no attribute 'production_slot_admission'
1 failed
```

The current allocator has no admission seam and no durable cooldown state.

### SC-RATE-002 — two lane roots denied before claim

Command:

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py::test_all_slots_cooling_denies_two_lanes_before_claim_or_provider
```

Pre-fix result: `FAIL`

```text
TypeError: process_once() got an unexpected keyword argument 'clock'
1 failed
```

The runner has neither an injectable admission clock nor a pre-claim cooldown path.

### SC-RATE-006 — new-only seam

Commands:

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_new_only_cycle_advances_one_new_and_skips_non_new_lanes
.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py::test_new_only_runner_gates_non_new_lane_before_claim
```

Pre-fix result: `FAIL`

```text
TypeError: cycle_once() got an unexpected keyword argument 'new_only'
TypeError: process_once() got an unexpected keyword argument 'lane'
```

Neither coordinator nor lane runner currently exposes the required reversible canary seam.

## GREEN

Final focused command:

```text
.venv/bin/python -m pytest -q \
  tests/test_agy_gemini_allocator.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_gemini_coordinator.py
```

Result:

```text
169 passed in 12.62s
```

Acceptance mapping:

- `SC-RATE-001`: five prepared paths now register exactly one run with one article.
- `SC-RATE-002`: two lane roots and 64-process contention remain closed wait with
  zero provider, credential read, ordinal, queue claim, attempt marker and failure delta.
- `SC-RATE-003`: exact clock expiry releases one new job; rewrite remains queued.
- `SC-RATE-004`: reviewer request wins over opaque writer filenames.
- `SC-RATE-005`: cooling account-1 selects only account-2 credential; expiry restores
  account-1 in deterministic rotation; stress allocations have no duplicate ordinal.
- `SC-RATE-006`: new-only advances one new state, does not seed/consume the other
  lanes, and seam-off restores rewrite processing.
- `SC-RATE-007`: cooldown schema rejects raw/extra/unbounded/duplicate fields; evidence
  privacy scan has zero matches.

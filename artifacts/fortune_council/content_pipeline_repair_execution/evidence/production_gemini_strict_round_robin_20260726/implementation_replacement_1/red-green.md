# RED → GREEN

## RED

Command:

```text
<local-only-python> -m pytest -q \
  tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py \
  -k 'production_pool or allocator_state or launchd_template or installer_rejects_relative'
```

Result: `31 failed, 5 passed, 89 deselected`.

Representative failures:

- `_allocate_production_credential_source` did not exist.
- Four-process and crash-durability probes could not allocate an ordinal.
- Provider failures did not create or advance allocator state.
- Installer did not define, validate, or inject a shared state path.

This establishes that the locked source still used deterministic job hashing
and did not satisfy the strict durable round-robin contract.

## GREEN

Focused command:

```text
<local-only-python> -m pytest -q \
  tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py \
  -k 'production_pool or allocator_state or launchd_template or installer_rejects_relative or installer_injects_one_shared'
```

Result: `38 passed, 89 deselected`.

The focused suite includes:

- exact six-allocation sequence `1,2,3,1,2,3`;
- four-process 300-allocation stress with ordinals `1..300`, no duplicate or
  gap, and exactly 100 allocations per slot;
- crash-after-commit durability;
- provider failure consumes ordinal with one request and no rotation;
- selected-credential-only access;
- missing-state initialization and the state safety matrix;
- flag-off compatibility and closed three-field public receipts;
- installer preflight ordering and one shared state path across all four lanes.

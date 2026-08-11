# RA-SLICE-002 Source Inventory

## CodeGraph query

- Query: `agy_gemini_coordinator register_run cycle_once process_once correlation_id formal runtime trusted sandbox pantheon_content_capability_receipt validate_capability_receipt create run`
- Result: found `register_run`, `cycle_once`, imported `process_once`, `_validate_formal_runtime`, `validate_capability_receipt`, and existing publisher formal capability preflight patterns.

## Source confirmation

- `scripts/agy_gemini_coordinator.py`
  - `register_run(run_dir, queue_root, correlation_id=...)` validates the private brief, stores canonical run state, and preserves caller correlation.
  - `cycle_once(queue_root, tick=..., process=..., exact_run_ids=...)` is the official run boundary and supports deterministic local injection.
  - `_validate_formal_runtime(...)` remains the shared formal runtime gate; this slice does not change it.
- `scripts/pantheon_content_capability_receipt.py`
  - `validate_capability_receipt(...)` is the only seven-step schema authority.
  - Fixed capabilities remain `create`, `run`, `select`, `publish`, `transaction`, `tag`, `push`.
- `tests/test_agy_gemini_coordinator.py`
  - Existing exact-run-id tests confirm `cycle_once` can advance only selected runs and pass `exact_run_ids` into the injected process seam.
- `tests/test_pantheon_content_capability_receipt.py`
  - Existing fixtures define required step keys, identity continuity, digest continuity, and caller-verdict rejection behavior.

## Public API selected

- Added `coordinator_create_run_receipt_preflight(...)` in `scripts/agy_gemini_coordinator.py`.
- Added stable failure type `CoordinatorReceiptBlocked`.
- The API returns a non-production envelope with exactly two `receipt_steps`; tests append fixture steps 3-7 and call the shared validator.

## Scope audit

- Modified source: `scripts/agy_gemini_coordinator.py`
- Added tests: `tests/test_agy_gemini_coordinator_capability_receipt.py`
- Added evidence under: `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_002/`
- No publisher, runner, shared validator, runtime manifest, registry, metadata, article, sitemap, feed, redirect, deployment, or production files changed.

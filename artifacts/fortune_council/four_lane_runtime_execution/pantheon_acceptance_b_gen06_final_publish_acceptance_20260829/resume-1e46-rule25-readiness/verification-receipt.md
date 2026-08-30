# RA-SLICE-006 Verification Receipt

## Positive Probe

- `package/production-canary-capability-receipt.json` is official gate compatible and keeps `canary_created=false`.
- `package/capacity-proof-normalized.json` removes local absolute cycle roots and retains two-cycle measurement, reclaim, projection, and stop-loss proof digests.
- Fourteen capability evidence files are copied into package-relative unique paths.

## Fail-closed Probe

- `package/negative-matrix.json` covers shared validator, evidence, capacity, projection, traversal, and symlink escape cases.
- `package/thin-gate-adversarial-red.json` records the official thin gate gap and the repo packager's required BLOCKED authority.
- `package/negative-fixtures/missing-step-receipt.json` is the official gate BLOCKED fixture.

## Verification Commands

- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_readiness.py -q`
- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q`
- `<ai-core-root>/scripts/production_canary_readiness_gate.py --receipt package/production-canary-capability-receipt.json`
- `git diff --check`

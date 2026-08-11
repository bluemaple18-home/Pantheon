# RA Checkpoint B Repair-1 Verification

## Source Decision

- CodeGraph status for the active detached worktree failed because `.codegraph/` is not initialized there.
- CodeGraph status for the canonical Pantheon checkout passed: 176 files, 3825 nodes, 5122 edges.
- Task-semantic query: `runtime_activation_capacity sampler host_free_bytes project-bytes-over-budget next_cycle_started`.
- CodeGraph did not return the target test symbol from the canonical checkout index, so fallback was limited to `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py` and `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`.

## Repair

- Updated only the over-budget test fixture.
- Injected a deterministic sampler with host free above reserve and zero initial project bytes.
- Preserved production guard behavior; no production source file was modified.

## Evidence

- Pre-repair local capacity pytest on this host: `4 passed in 0.14s`. This confirms the original bug is host-state dependent rather than always reproducible on every machine.
- Single over-budget regression after repair: `1 passed in 0.04s`.
- Required capacity pytest after final formatting: `4 passed in 0.05s`.
- Required readiness/e2e/capacity pytest after final formatting: `13 passed in 34.32s`.
- Deterministic probe output: `case=project-bytes-over-budget`, `len_calls=1`, `next_cycle_started=false`, `initial_project_bytes=0`.

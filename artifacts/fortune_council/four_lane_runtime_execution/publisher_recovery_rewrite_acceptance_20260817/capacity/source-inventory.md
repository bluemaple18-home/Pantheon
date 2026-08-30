# RA-SLICE-005 Source Inventory

## CodeGraph

- Status: READY.
- Task-semantic query: `RA-SLICE-005 capacity proof harness run_runtime_activation_e2e two-cycle non-production E2E measurement cleanup stop-loss policy`.
- Entry point returned: `scripts/pantheon_writer_vnext_runtime_activation_e2e.py:run_runtime_activation_e2e`.

## Bounded Source Confirmation

- `scripts/pantheon_writer_vnext_runtime_activation_e2e.py`:唯一 workload，signature 接受 caller-owned sandbox、runtime receipt、execution line、correlation、actor identity 與 brief。
- `tests/test_pantheon_writer_vnext_runtime_activation_e2e.py`:既有 RA004 regression 驗證七段 capability、dry-run tag/push 與 fail-closed matrix。
- `scripts/pantheon_content_capacity_guard.py`:現有容量守門提供本地 tree/disk/RSS/swap 量測模式參考；RA-SLICE-005 未修改或接管 production guard。

## Changed Files

- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`
- `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_005/**`

## Boundary

- No RA004 E2E, coordinator, Publisher, shared receipt validator, runtime manifest, deployment, registry, metadata, article, sitemap, feed, redirect, production, canary, network write, launchctl, service mutation, push, or tag path was modified.

# RA-SLICE-003 Source Inventory

## CodeGraph

- Status: READY
- Indexed files: 555
- Indexed nodes: 5543
- Task-semantic query:
  `agy_content_publisher formal_capability_preflight _normalize_exact_run_ids _runtime_identity_digest_for_trace TrustedSandboxDirectoryAuthority operation_trace transaction tag push pantheon_content_capability_receipt validate_capability_receipt`
- Entry points returned:
  - `scripts/agy_content_publisher.py:formal_capability_preflight`
  - `scripts/pantheon_content_capability_receipt.py:validate_capability_receipt`
  - `scripts/pantheon_runtime_fs_authority.py:TrustedSandboxDirectoryAuthority`

## Bounded Source Confirmation

- `scripts/agy_content_publisher.py`
  - Existing public Publisher boundary remains `formal_capability_preflight`.
  - Existing select/publish/transaction/tag/push branching remains in that boundary.
  - Existing injected Git dry-run path remains `_formal_capability_dry_run_git`.
  - Existing operation tracing remains `OperationTraceRecorder` plus `summarize_operation_trace`.
- `scripts/pantheon_content_capability_receipt.py`
  - Shared seven-step authority remains `validate_capability_receipt`.
  - No shared validator changes were made.
- `scripts/pantheon_runtime_fs_authority.py`
  - Evidence writes use `TrustedSandboxDirectoryAuthority.open_file`.
  - Sandbox relative path checks reject absolute paths, traversal, and symlink components.
- `tests/test_pantheon_content_capability_probe.py`
  - Existing formal probe regression still exercises Publisher capabilities through the production adapter.

## Changed Files

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher_capability_receipt.py`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_003/**`

## Forbidden Scope Check

- No changes to `scripts/pantheon_content_capability_receipt.py`.
- No changes to coordinator, runner, runtime manifest, capacity guard, deployment scripts, registry, metadata, sitemap, feed, redirects, articles, or production transport.
- No real tag, push, deploy, publication, canary, network write, launchctl, or service start/stop performed.

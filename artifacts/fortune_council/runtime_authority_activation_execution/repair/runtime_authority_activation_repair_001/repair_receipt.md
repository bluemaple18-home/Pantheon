# Runtime Authority Activation Repair-1 Receipt

## Identity

- card_id: `CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-001`
- dispatch_key: `v1:20c505d0bbb2cf35d3a9ca2d6612a2389f4dee66c7cd1cedd4ef624d83a8b8fe`
- activation_token: `act-v1:887d6dd4e4ffd08438de81c5c86b8ca640bc25f90f77acaff770018259f72201`
- source_sha: `72743258f602e7cce07463bea87849e00a7d1ee1`
- source_parent: `a0767f2071efd5593eca005e5bc7c390d416a266`
- candidate_parent: `72743258f602e7cce07463bea87849e00a7d1ee1`
- candidate_sha: reported by final delivery response after commit creation
- production_authorized: `false`

## CodeGraph

- query: `Runtime Authority Activation Repair-1: activation token must be required before formal runtime I/O, TrustedSandboxDirectoryAuthority must cover publisher filesystem/git transaction lifecycle using dir-fd/no-follow mutation-time authority, and formal capability trace identity must come only from verified runtime receipt.`
- status: `CONTEXT_READY`
- surfaced entries: `validate_service_before_io`, `TrustedSandboxDirectoryAuthority`, `formal_capability_preflight`

## RED

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_activation.py::test_formal_coordinator_requires_activation_token_before_queue_io \
  tests/test_pantheon_runtime_fs_authority.py::test_formal_transaction_blocks_late_parent_swap_before_git_lock_io \
  tests/test_pantheon_runtime_fs_authority.py::test_formal_preflight_blocks_unverified_trace_identity
```

- exit_code: `1`
- missing-token result: formal coordinator accepted missing `PANTHEON_RUNTIME_ACTIVATION_TOKEN` and reached queue I/O instead of raising `RuntimeManifestError`.
- late parent-swap result: transaction path left the live fd authority before Git lock/transaction lifecycle; the public test observed failure outside the desired `PublishBlocked` authority boundary.
- trace identity result: preflight accepted missing verified runtime identity and generated a fallback 64-hex digest.

## GREEN

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_activation.py::test_formal_coordinator_requires_activation_token_before_queue_io \
  tests/test_pantheon_runtime_fs_authority.py::test_formal_transaction_blocks_late_parent_swap_before_git_lock_io \
  tests/test_pantheon_runtime_fs_authority.py::test_formal_preflight_blocks_unverified_trace_identity
```

- exit_code: `0`
- result: `3 passed in 0.10s`
- external tree: late parent-swap test asserts external tree before/after identity and absence of external `.git` / lifecycle lock.

## Matrix

- missing token before coordinator queue I/O: `GREEN`, zero `queue/runs` writes.
- six-of-seven acknowledgements: covered by `tests/test_pantheon_runtime_activation.py::test_activation_token_requires_complete_seven_service_acknowledgements`, zero operation calls.
- stale activation token: covered by `tests/test_pantheon_runtime_activation.py::test_stale_activation_token_fails_before_queue_state_io`, zero operation calls.
- adapter missing token: covered by `tests/test_pantheon_content_capability_probe.py::test_adapter_contract_requires_activation_token_before_create_io`, zero create I/O.
- unverified trace identity: `GREEN`, `formal_capability_preflight()` blocks without `runtime_receipt`.
- late parent-swap: `GREEN`, fd authority remains live through Git common-dir mkdir, lock open, transaction create/remove, repo copy/remove.

## Targeted Suite

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py
```

- exit_code: `0`
- result: `269 passed, 1 warning in 45.84s`
- warning: existing `SyntaxWarning: invalid escape sequence '\/'` surfaced from `tests/test_agy_content_publisher.py::test_preflight_test_command_selectors_resolve_to_top_level_tests`.

## Changed Files

- `artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-001.md`
- `artifacts/fortune_council/runtime_authority_activation_execution/repair/runtime_authority_activation_repair_001/repair_receipt.md`
- `scripts/agy_content_publisher.py`
- `scripts/pantheon_content_capability_adapter.py`
- `scripts/pantheon_content_capability_probe.py`
- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/pantheon_runtime_fs_authority.py`
- `tests/test_pantheon_content_capability_probe.py`
- `tests/test_pantheon_content_runtime_manifest.py`
- `tests/test_pantheon_runtime_activation.py`
- `tests/test_pantheon_runtime_fs_authority.py`

All changed files are inside the card allowlist.

## Final Checks

- `git diff --check 72743258f602e7cce07463bea87849e00a7d1ee1..HEAD`: exit_code `0`
- `git status --short --untracked-files=all`: clean after candidate commit

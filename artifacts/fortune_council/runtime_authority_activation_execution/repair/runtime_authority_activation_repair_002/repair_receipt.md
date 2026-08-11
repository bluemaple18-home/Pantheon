# Runtime Authority Activation Repair-2 Receipt

## Status

- card_id: `CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-002`
- dispatch_key: `v1:05b1bc19ea3b6c9d90b8b2f00aff8019e6a257555785b35b5180867954a7c3fa`
- activation_token: `act-v1:db00a487856e009f6a2dc39c42737f459d7e2b330b9619fe5c2694cba00016af`
- activation_receipt: `CAPABILITY_READY/query_required`
- production_authorized: `false`
- repair_generation: `2/2`
- source_head: `bcd35b090dd37b118632d3b4153308964218f0c8`
- result: `CANDIDATE_READY_FOR_REVIEW`

## CodeGraph

- Query used projectPath for the active worktree.
- Semantic query target: `_cleanup_stale_transaction_worktrees`, `TrustedSandboxDirectoryAuthority`, post-lock stale transaction cleanup.
- Result: CodeGraph returned `_cleanup_stale_transaction_worktrees` as the stale cleanup entry point and showed ordinary `state_root.iterdir()`, `transaction_root.exists()`, and `shutil.rmtree()` usage before the repair.

## RED

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 <pantheon-canonical-checkout>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py::test_formal_transaction_post_lock_cleanup_swap_preserves_external_tree
```

Exit code: `1`

Observed failure:

- `PublishBlocked` was raised after `filesystem-lock-open`.
- External snapshot was not identical.
- Failure diff showed `publisher-state/transaction-escape`, `publisher-state/transaction-escape/repo`, and `publisher-state/transaction-escape/repo/marker.txt` disappeared from the external tree.

External tree contract:

- Before: `publisher-state/transaction-escape/repo/marker.txt` existed with body `external marker`.
- RED after: external stale tree was removed.

## GREEN

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 <pantheon-canonical-checkout>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py::test_formal_transaction_post_lock_cleanup_swap_preserves_external_tree
```

Exit code: `0`

Output:

```text
1 passed in 0.07s
```

External tree contract:

- `PublishBlocked` is still raised after the parent swap.
- External snapshot is identical before and after.
- `publisher-state/transaction-escape/repo/marker.txt` remains present with body `external marker`.

## Cleanup Matrix

- normal stale cleanup: `formal_capability_preflight("transaction")` removes sandbox-local `transaction-stale` via authority trace.
- non-transaction entry: `cache-entry` is preserved.
- symlink transaction entry: `transaction-link` is rejected with `FilesystemAuthorityError`; symlink target is preserved.
- missing repo entry: `transaction-empty` parent removal is idempotent and does not call `git worktree remove`.
- exception path: injected parent removal failure leaves the held authority usable for later `exists("publisher-state")`.

## Validation

Targeted authority file:

```bash
PYTHONDONTWRITEBYTECODE=1 <pantheon-canonical-checkout>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py
```

Exit code: `0`; output: `10 passed in 0.12s`

Targeted regression:

```bash
PYTHONDONTWRITEBYTECODE=1 <pantheon-canonical-checkout>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py tests/test_agy_content_publisher.py
```

Exit code: `0`; output: `119 passed, 1 warning in 4.34s`

Required wider regression:

```bash
PYTHONDONTWRITEBYTECODE=1 <pantheon-canonical-checkout>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py tests/test_pantheon_runtime_activation.py tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_capability_probe.py tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_runner.py tests/test_pantheon_content_capacity_guard.py
```

Exit code: `0`; output: `275 passed, 1 warning in 47.58s`

Working-tree whitespace check:

```bash
git diff --check
```

Exit code: `0`

Warning:

- Existing warning from `tests/test_agy_content_publisher.py::test_preflight_test_command_selectors_resolve_to_top_level_tests`: `DeprecationWarning: invalid escape sequence '\/'`.

## Changed Files Allowlist

- `artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-002.md`
- `artifacts/fortune_council/runtime_authority_activation_execution/repair/runtime_authority_activation_repair_002/repair_receipt.md`
- `scripts/agy_content_publisher.py`
- `scripts/pantheon_runtime_fs_authority.py`
- `tests/test_pantheon_runtime_fs_authority.py`

Allowlist result: `PASS`

## Debug Marker Scan

Command scanned allowlist source/test/card files for `TODO`, `FIXME`, `debugger`, `breakpoint`, and `print(`.

Result:

- No new debug markers in changed tests or authority code.
- Existing CLI `print(json.dumps(...))` entries remain in `scripts/agy_content_publisher.py`.

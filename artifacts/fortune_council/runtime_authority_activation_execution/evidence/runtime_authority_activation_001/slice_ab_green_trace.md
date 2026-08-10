# Slice A/B GREEN and trace checkpoint

## Slice A GREEN

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py
```

Initial Slice A result after dir-fd/no-follow authority:

- exit code: `0`
- result: `1 passed in 0.03s`
- independent mainline rerun reported: `1 passed in 0.03s`
- symptom fixed: parent-swap now raises before external queue/state I/O; external tree remains identical.

## Slice B trace checkpoint

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_runtime_fs_authority.py
```

Result after adding actual operation trace:

- exit code: `0`
- result: `2 passed in 0.06s`
- checkpoint: transaction pre/post snapshot is identical, while `operation_trace` records `filesystem-transaction-create`, `git-worktree-add`, `git-worktree-remove`, and `filesystem-transaction-remove`.
- mutation conclusion: `sandbox_mutation=true` is derived from operation trace, not from caller-provided booleans or terminal snapshot.

## Static negative regression

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_content_capability_probe.py::test_publisher_preflight_invokes_formal_publish_transaction_and_release_boundaries tests/test_pantheon_content_capability_probe.py::test_environment_roots_cannot_self_authorize_publisher_sandbox tests/test_pantheon_content_capability_probe.py::test_publisher_preflight_rejects_untrusted_roots_before_io tests/test_pantheon_content_capability_probe.py::test_dry_run_git_blocks_transaction_materialization_outside_sandbox
```

Result:

- exit code: `0`
- result: `10 passed in 0.10s`
- regression: untrusted roots still fail before boundary I/O.

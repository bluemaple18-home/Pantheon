# APF-004-MANIFEST-CREATE-IDENTITY-REPAIR-001 evidence

## Status

- status: `REPAIR_READY_FOR_REVIEW`
- mode: `REPAIR / NO_LIVE_MUTATION`
- mutation_executed: `false`
- card_commit: `de58f502e6`
- integration_commit: `8fea7a47a86a97e0dd1eb6af94df1ba6056e7a17`
- blocked_plan_commit: `6698857b9e`

## Boundary

Allowed files touched:

- `.ai/codex_task_apf_004_manifest_create_identity_repair_20260814.md`
- `.ai/evidence/apf_004_manifest_create_identity_repair_001.md`
- `scripts/pantheon_content_runtime_manifest.py`
- `tests/test_pantheon_content_runtime_manifest.py`

No live manifest, stage, runtime, plist, launchctl, install, activate, merge, push, deploy, external model, publish, transaction, tag, or schedule command was executed.

## CodeGraph

CodeGraph was queried before source decisions and returned:

```text
CodeGraph not initialized in <repo-root>. Run 'codegraph init' in that project first.
```

Fallback was limited to runtime manifest source, direct tests, installer propagation tests, the repair card, and committed evidence.

## RED

Command:

```text
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_manifest_create_cli_requires_and_validates_hardened_identity
```

Observed failure:

```text
assert missing.returncode != 0
E assert 0 != 0
```

Meaning: public `create` CLI accepted a manifest without `--actor-head` and `--python-executable`, reproducing the exact source gap from the blocked realignment plan.

## Hypotheses

1. If the root cause is only missing parser/main wiring, adding required CLI args and passing them to existing `build_manifest()` should make the RED pass without changing validation internals.
2. If validation internals are incomplete, the create test may pass but negative drift tests or installer propagation tests should fail.

Result: hypothesis 1 was supported; hypothesis 2 was falsified by the affected suite.

## Fix

Minimal source change:

- `scripts.pantheon_content_runtime_manifest create` now requires `--actor-head` and `--python-executable`;
- `main()` passes those values to existing `build_manifest()`;
- no installer shell, activation, barrier, rollback, capacity guard, publisher, coordinator, or generated shared file logic was changed.

## GREEN

Commands and results:

```text
.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_manifest_create_cli_requires_and_validates_hardened_identity
1 passed

.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_manifest_create_cli_hardened_identity_negative_matrix_fails_closed
3 passed

.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py
39 passed

.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation'
28 passed, 113 deselected

.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py -k 'installer or runtime_manifest'
5 passed, 107 deselected

.venv/bin/python -m pytest -q tests/test_pantheon_content_capacity_guard.py -k 'installer or runtime'
4 passed, 12 deselected
```

Shell `bash -n` was not required because no shell script was touched.

## Gate Notes

Locked gates run after source/evidence edits:

- debug marker scan on `scripts`, `tests`, and `.ai` allowlist;
- secret scan on allowlist;
- absolute path scan on allowlist;
- binary scan on allowlist;
- `git diff --check`;
- cached allowlist check before commit.

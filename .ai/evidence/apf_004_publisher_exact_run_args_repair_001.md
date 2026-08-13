# APF-004-PUBLISHER-EXACT-RUN-ARGS-REPAIR-001 evidence

## Status

- status: `REPAIR_READY_FOR_REVIEW`
- mode: `REPAIR / NO_LIVE_MUTATION`
- fixed_source: `7ae57fbd21bff0ffa887debf989424626734119d`
- branch: `codex/apf-004-publisher-exact-run-args-repair`
- card_commit: `b84c12f981`
- live_mutation_executed: `false`
- activation_executed: `false`

## Boundary

Allowed files touched:

- `.ai/codex_task_apf_004_publisher_exact_run_args_repair_20260814.md`
- `.ai/evidence/apf_004_publisher_exact_run_args_repair_001.md`
- `scripts/install_agy_content_publisher_launchd.sh`
- `tests/test_agy_content_publisher.py`

No Writer/Publisher business logic, runtime manifest schema, other installer, registry, shared generated file, live install/activate, launchctl mutation, Gate 1 retry, publish, transaction, tag, schedule, push, deploy, or external model command was executed.

## CodeGraph

CodeGraph was queried before source decisions and returned:

```text
CodeGraph not initialized in <repo-root>. Run 'codegraph init' in that project first.
```

Fallback was limited to Publisher installer, direct Publisher tests, the task card, and fixed-source git metadata.

## RED

Command:

```text
.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u
```

Result:

```text
2 failed
scripts/install_agy_content_publisher_launchd.sh: line 207: EXACT_RUN_ARGS[@]: unbound variable
```

The RED used `/bin/bash` `3.2.57(1)-release`, `set -u`, no `PANTHEON_PUBLISH_EXACT_RUN_ID`, and temp-only `--preflight` plus `--install` fixtures. It reproduced the exact blocker without touching live LaunchAgents.

## Hypothesis

If the failure is Bash 3.2 nounset handling of an empty local array, replacing the direct empty-array expansion with a guarded expansion should remove the unbound-variable failure while preserving exact selector argv when set.

## Fix

Minimal source change in `scripts/install_agy_content_publisher_launchd.sh`:

```text
${EXACT_RUN_ARGS[@]+"${EXACT_RUN_ARGS[@]}"}
```

This emits no argument when exact selector is unset, and emits `--exact-run-id <id>` once when set. No publisher business logic changed.

## GREEN

Commands and results:

```text
.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u
2 passed

.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath
1 passed

.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py -k 'installer or runtime_manifest'
7 passed, 107 deselected

.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u tests/test_agy_content_publisher.py::test_content_publisher_installer_rejects_python_symlink_to_non_executable tests/test_agy_content_publisher.py::test_four_lane_recovery_publisher_rejects_new_only_before_mutation
5 passed

bash -n scripts/install_agy_content_publisher_launchd.sh
pass
```

## Gate Notes

Locked gates run after evidence updates:

- debug marker scan on allowlist;
- secret scan on allowlist;
- added-line absolute path scan on allowlist;
- binary scan on allowlist;
- `git diff --check`;
- cached allowlist and cached diff check before commit.

Added-line path scan review:

- hits were limited to macOS/test fixture literals: `/usr/libexec/PlistBuddy`, `/bin/bash`, fixture shell shebangs, and fixture PATH;
- no live user home, live LaunchAgents path, live runtime root, secret path, stage path, or deployment path was added.

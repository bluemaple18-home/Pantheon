# Capacity Guard preactivation transition repair evidence

## Scope

- Changed only capacity guard installer/runtime/test ownership files plus this evidence path.
- Production mutation: `0`.
- No `launchctl bootout/bootstrap/kickstart` was run by this task.
- No publish, transaction, tag, push, production plist, production manifest, production receipt, or production barrier mutation.

## RED

Command:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition -q
```

Pre-fix result:

```text
1 failed
rss_error: loaded_service_pid_missing:com.pantheon.agy-content-publisher
reasons: ["rss_telemetry_unknown"]
```

This was a valid RED after fixture correction: the failure came from the current installer/capacity preflight path, not from missing pytest, uv cache access, or optional actor_head dirty-worktree validation.

## GREEN

Commands:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases -q
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
```

Results:

```text
7 passed
40 passed
75 passed
bash -n passed
git diff --check passed
```

## Negative Evidence

The unsafe transition matrix stayed NO-GO before staging:

- stale barrier
- wrong generation/digest
- normal live plist
- malformed live plist
- missing identity
- unknown service/control identity

## Runtime Gate Preservation

Normal capacity preflight still fails closed on unknown RSS/swap telemetry and normal loaded/no-PID services. The new transition check is only reached after an exact `rss_telemetry_unknown` / `loaded_service_pid_missing:*` preflight failure, and then requires a matching activation-only manifest, matching activation barrier, complete activation-only live plist aggregate, and launchctl loaded/no-PID identity for the registered seven-service aggregate.

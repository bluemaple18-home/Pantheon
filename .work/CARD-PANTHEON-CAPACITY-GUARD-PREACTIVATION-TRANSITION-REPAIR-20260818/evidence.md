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

Normal capacity preflight still fails closed on unknown RSS/swap telemetry and normal loaded/no-PID services. The new transition check is only reached after an exact `rss_telemetry_unknown` / `loaded_service_pid_missing:*` preflight failure, and then requires a matching activation-only manifest, matching activation barrier, staged six-service manifest/generation evidence, Publisher exact max-runs/exact-run receipt, complete activation-only live plist inert shape, and launchctl loaded/no-PID identity for the registered seven-service aggregate.

## G5 Follow-Up Root Cause

G5 actual fields from evidence commit `29f69e9e237ad94a44d3c86baac6f39e572b410e`:

- source/main/origin: `35cfdd52739f3e2896bf151ed6434a5e6d6ab95e`
- manifest_digest: `46c37d3440d5938a1022b99dec8779ecc02168ba0c00fd7c05418fc4191912ac`
- identity: `gate2-actor:35cfdd52739f3e2896bf151ed6434a5e6d6ab95e:activation-only`
- generation: `g12-35cfdd5273-20260818T120632Z`
- runtime_digest: `e8261a1dbd08dac632f11aeb03ea3fa037b012e66a874be7fdf1ab9e59f297a7`
- config_version: `formal-runtime-v3-model-route-v1`

The rejected contract surface was wrong in two places:

- The transition validator expected `config_version == formal-runtime-v2-gate2`; G5 uses the valid promoted v3 model-route runtime surface.
- The transition validator expected live plists to match the newly promoted manifest, but G5 is before aggregate activation: six new plists are staged, the seventh capacity plist is still missing, and live plists are intentionally the old activation-only loaded/no-PID set.

The fix keeps normal capacity preflight unchanged and moves preactivation acceptance to the actual G5 boundary: new manifest + new barrier + staged six current plists + Publisher exact receipt + old live activation-only inert identity.

## G5 Follow-Up RED/GREEN

RED command:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g5_promoted_manifest_with_staged_six_plists -q
```

Pre-fix result:

```text
1 failed
{"preactivation_transition": "rejected", "reasons": ["preactivation manifest mismatch"], "status": "NO-GO"}
```

GREEN commands:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g5_promoted_manifest_with_staged_six_plists tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_g5_preactivation_stage_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases -q
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
```

Results:

```text
10 passed
44 passed
75 passed
bash -n passed
git diff --check passed
```

G5 negative drift evidence:

- staged manifest digest mismatch rejected before capacity stage write
- missing Publisher exact receipt rejected before capacity stage write
- staged lane manifest digest mismatch rejected before capacity stage write

## G5 Re-Review NO-GO Repair

Reviewer thread: `01a014b5-3848-7612-a69e-99a42797d965`.

NO-GO root cause:

- Candidate `4975a189425e41f443fc3f76341362503e903cce` checked each old live activation-only plist independently.
- A single live plist could drift to a different coherent old tuple: different manifest digest, matching `--expected-digest`, different activation-only identity, and different barrier path with the same generation suffix.
- Because the validator did not bind all seven live plists as one old runtime aggregate, the transition was incorrectly accepted and the staged capacity plist was written.

Repair:

- Derived the old runtime aggregate tuple from live plists only; no old manifest load is required after promotion.
- Required equality across all seven live activation-only plists for identity, manifest digest, runtime identity digest, runtime digest, config version, generation, actor/log/queue/state roots, optional actor head, optional python/uv executable, exact barrier path, and manifest argument path.
- Preserved per-label service identity and loaded/no-PID launchctl topology checks.
- Added stage-side checks for wrong Publisher exact-run receipt and zero-child-exec staged plist I/O drift.

RED command:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_one_live_plist_coherent_old_runtime_drift -q
```

Pre-fix result:

```text
1 failed
accepted transition and wrote staged capacity plist
```

GREEN commands:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g5_promoted_manifest_with_staged_six_plists tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_g5_preactivation_stage_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_one_live_plist_coherent_old_runtime_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases -q
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
```

Results:

```text
13 passed
47 passed
75 passed
bash -n passed
git diff --check passed
```

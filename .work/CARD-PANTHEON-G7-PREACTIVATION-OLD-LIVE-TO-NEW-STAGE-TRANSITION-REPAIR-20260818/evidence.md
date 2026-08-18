# G7 preactivation old-live to new-stage transition repair evidence

## Scope

- Production mutation: `0`.
- No production runtime, LaunchAgent, queue, state, transaction, tag, or remote mutation.
- No `launchctl bootout/bootstrap/kickstart` was run by this task.
- Work remained in the existing repair thread/worktree.

## Root Cause

The preactivation validator still had a post-activation assumption in the old-live half of the contract:

- old live activation-only plists were required to use the new `gate2-actor:<sha>:activation-only` identity pattern;
- G6 live plists are a coherent old `g8` aggregate using `b74646...:four-lane-model-route-v1`, loaded/no-PID activation-only wrappers;
- before aggregate activation, old live identity may differ from the new staged target. Only post-activation checks may require live plists to equal the new target.

The second contract gap was that the new-stage half validated six already-staged service plists, but not the capacity guard plist candidate that was about to be written.

## RED

Command:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g6_old_live_model_route_identity -q
```

Pre-fix result:

```text
1 failed
{"preactivation_transition": "rejected", "reasons": ["preactivation live plist mismatch"], "status": "NO-GO"}
```

## GREEN

Commands:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g6_old_live_model_route_identity tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g5_promoted_manifest_with_staged_six_plists tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_g5_preactivation_stage_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_one_live_plist_coherent_old_runtime_drift tests/test_pantheon_content_capacity_guard.py::test_preactivation_transition_rejects_capacity_candidate_plist_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases -q
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
```

Results:

```text
15 passed
49 passed
75 passed
bash -n passed
git diff --check passed
```

## Negative Matrix

- mixed old-live identity / one-lane coherent drift rejected by old aggregate tuple equality;
- PID in loaded service remains rejected by launchctl topology check;
- stale barrier, wrong generation/digest, normal or malformed live plist, missing identity, and unknown service remain NO-GO;
- wrong Publisher exact marker, missing exact marker, stage manifest digest drift, staged lane digest drift, and capacity candidate plist drift remain NO-GO.

## Contract

Preactivation now accepts only this boundary:

- old live seven-service aggregate is complete, activation-only, loaded/no-PID, internally coherent, and inert;
- new staged aggregate is complete across six staged plists plus the capacity guard candidate plist, and matches the promoted manifest/barrier/generation;
- Publisher exact `max-runs=1` and exact-run marker are bound before capacity staging;
- normal capacity preflight behavior remains unchanged and fail-closed.

## Iteration 2 Reviewer NO-GO repair

### Reviewer finding

Candidate `5fdf66bb51e4d37aa91224264d24b1fa62120e7f` allowed this bypass:

- old G6 activation-only live seven plists exposed PID-bearing launchctl state;
- fake RSS was available, so normal capacity preflight returned `PASS`;
- installer returned success before invoking `preactivation-transition`;
- staged capacity plist was written even though G7 requires old live aggregate to be inert loaded/no-PID before staging.

### Root cause

`run_capacity_preflight` returned immediately on normal preflight `PASS`. In the installer stage path, that conflated non-transition runtime preflight with the old-live to new-stage transition gate.

### Source fix

- Preserve normal capacity preflight semantics when no stage transition context exists.
- When stage manifest/generation/Publisher markers exist, always persist the preflight receipt and invoke `preactivation-transition` before stage destination write.
- `preactivation-transition` now accepts a `PASS` preflight receipt as evidence that RSS was known, but still independently validates old live inertness and rejects any PID-bearing/non-inert live service.
- If transition validation fails after preflight `PASS`, installer returns nonzero and never writes the staged destination.

### RED

Command:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_transition_live_pid_even_when_preflight_passes -q
```

Pre-fix result:

```text
1 failed
assert 0 != 0
stdout: {"status": "PASS", ...}
staged capacity plist was written
```

### GREEN and verification

Commands:

```bash
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_transition_live_pid_even_when_preflight_passes tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g6_old_live_model_route_identity tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_accepts_g5_promoted_manifest_with_staged_six_plists tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_g5_preactivation_stage_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_one_live_plist_coherent_old_runtime_drift tests/test_pantheon_content_capacity_guard.py::test_preactivation_transition_rejects_capacity_candidate_plist_drift tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases -q
.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh
git diff --check
```

Results:

```text
16 passed
50 passed
75 passed
bash -n passed
git diff --check passed
```

### Negative evidence

- PID-bearing old live service is rejected even when normal preflight has valid RSS and returns `PASS`.
- Destination stage plist remains absent/unchanged on failure.
- Mutation log remains absent.
- Real G6 loaded/no-PID transition remains accepted.
- Original stale barrier, digest/generation drift, malformed live plist, one-lane coherent drift, wrong exact marker, and staged aggregate drift negatives remain covered.

Production mutation: `0`.

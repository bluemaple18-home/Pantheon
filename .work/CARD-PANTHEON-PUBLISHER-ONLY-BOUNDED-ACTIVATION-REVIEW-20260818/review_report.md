# CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818 review report

## Verdict

- Verdict: `REVIEW_NO_GO`
- Blocking finding IDs: `PANTHEON-PUBLISHER-ONLY-REVIEW-F001`
- Review source SHA: `359a28440835672c3e2bf020e372e9cf407d6aa4`
- Review base SHA: `1db9b8a1edd689e5c8cfecc407f51d6da8351cd5`
- Candidate SHA: `482ae14d90d9b632e2cfa705e1fac00ffc3bc651`
- Formal thread ID: `01a013b7-d985-7d70-9277-14aaa35ff780`
- Activation token: `PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818-G1`
- Production mutation count: `0`

## Bootstrap

- Cwd: `/Users/mattkuo/.codex/worktrees/91eb/Pantheon`
- HEAD at activation: `359a28440835672c3e2bf020e372e9cf407d6aa4`
- Worktree clean before evidence writes: yes
- Review card readable: yes
- Implementation card readable: yes
- Base object readable: `commit`
- Candidate object readable: `commit`
- CodeGraph readiness: unavailable; `codegraph_status` returned `CodeGraph not initialized in /Users/mattkuo/.codex/worktrees/91eb/Pantheon`, so review used bounded `rg`/`git diff`.

## Finding Matrix

### PANTHEON-PUBLISHER-ONLY-REVIEW-F001

- Severity: `P1`
- Category: production safety / selector correctness / fail-closed activation
- Path: `scripts/install_agy_gemini_coordinator_launchd.sh:409`
- Related path: `scripts/pantheon_content_runtime_manifest.py:452`
- Evidence: Publisher installer writes `publisher-exact-run-id` as a stage receipt when exact-run is provided (`scripts/install_agy_content_publisher_launchd.sh:250`). The publisher-only activation gate checks `manifest-digest`, `generation`, `publisher-max-runs`, and the staged plist, but never reads or compares `publisher-exact-run-id` (`scripts/install_agy_gemini_coordinator_launchd.sh:409-424`). The manifest `publisher-plist` preflight validates only the plist child args and returns `exact_run_id` from those args (`scripts/pantheon_content_runtime_manifest.py:452-492`), with no receipt comparison.
- Reproduction: `.venv/bin/python .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/reproduce_stale_exact_receipt.py`
- Reproduction result: command returned `0` with a stale `publisher-exact-run-id` receipt present, stdout reported `"exact_run_id": ""`, and fake launchctl mutation log contained Publisher `bootout` and `bootstrap`.
- Risk: A stale or mismatched exact-run receipt can coexist with a normal Publisher plist that omits `--exact-run-id`. The formal publisher-only activation still mutates launchd and starts Publisher with `max-runs=1` but without the intended exact selector. This violates the review card requirement that optional exact-run be bound from stage artifact to plist child args and not be bypassed by stale files.
- Suggested fix: In `--activate-publisher-only`, read `publisher-exact-run-id` if present and require exact equality with the `publisher-plist` receipt's `exact_run_id`; if absent, require the plist receipt exact_run_id to be empty. Treat mismatch or stale receipt as `publisher_only_stage_validation` failure before backups, live plist replacement, bootout, bootstrap, or child I/O. Add negative tests for stale receipt present with missing plist exact-run and receipt/plist exact-run mismatch.
- Validation gap: Existing tests cover invalid exact-run format inside the plist, but not stale or mismatched stage receipt versus plist child args.
- Confidence: high

## Verification

Commands run:

```bash
git cat-file -t 1db9b8a1edd689e5c8cfecc407f51d6da8351cd5
git cat-file -t 482ae14d90d9b632e2cfa705e1fac00ffc3bc651
git diff --name-status 1db9b8a1edd689e5c8cfecc407f51d6da8351cd5 482ae14d90d9b632e2cfa705e1fac00ffc3bc651
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_replaces_only_publisher tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_fails_closed_before_mutation -q
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_replaces_only_publisher tests/test_agy_gemini_coordinator.py::test_publisher_only_bounded_activation_fails_closed_before_mutation tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_missing_activation_barrier_before_mutation tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation -q
.venv/bin/python -m pytest tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py -q
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
bash -n scripts/install_agy_content_publisher_launchd.sh
git diff --check
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q
.venv/bin/python .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/reproduce_stale_exact_receipt.py
```

Results:

- Base/candidate objects: readable commits.
- Candidate diff files: implementation evidence plus `scripts/install_agy_content_publisher_launchd.sh`, `scripts/install_agy_gemini_coordinator_launchd.sh`, `scripts/pantheon_content_runtime_manifest.py`, `tests/test_agy_content_publisher.py`, `tests/test_agy_gemini_coordinator.py`.
- Publisher-only target tests: `5 passed`.
- Coordinator affected subset: `9 passed`.
- Publisher installer subset: `3 passed`.
- Runtime manifest suite: `48 passed`.
- Shell syntax: both launchd installer scripts passed `bash -n`.
- `git diff --check`: passed before evidence report; rerun after report is required before commit.
- Full coordinator suite: `197 passed, 5 failed`. The five failures are APF-004 create-run adapter matrix backlog failures on missing `ASTRO-SCENARIO-BIG-THREE`; they do not execute the modified Publisher-only activation path.
- Stale exact receipt repro: returned `0` and produced fake Publisher launchctl mutations, confirming finding `PANTHEON-PUBLISHER-ONLY-REVIEW-F001`.

## Residual Risks

- Rollback path restores Publisher plist and loaded state but does not compare the restored Publisher launchctl identity against the saved pre-activation identity. Because `F001` is already blocking, this remains a residual check for repair validation.
- Success path proves other six plist bytes are unchanged and no launchctl commands target them in tests; it does not capture PID/state digests for those six services.

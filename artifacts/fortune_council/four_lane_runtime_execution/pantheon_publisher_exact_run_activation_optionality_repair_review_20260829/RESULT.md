---
id: PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-OPTIONALITY-REPAIR-REVIEW-20260829-RESULT
card_id: CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-OPTIONALITY-REPAIR-20260829
status: REVIEW_COMPLETE
verdict: GO
base: bde44589f3785aae738bb7d7b1626270ba5505d0
---

# Publisher exact-run activation optionality Repair Review RESULT

## Verdict

`GO`

無 P0/P1 finding。此 bounded Repair 可進本機提交。

## Scope reviewed

固定 base：

- `bde44589f3785aae738bb7d7b1626270ba5505d0`

Artifacts / receipts reviewed:

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-OPTIONALITY-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/evidence-index.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/broad-baseline-candidate.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-red-before-run-1.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-red-before-run-2.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-green-run-1.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-green-run-2.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/red-targeted.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/green-targeted.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/targeted-capacity.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/broad-baseline.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/broad-candidate.txt`

Code/diff reviewed:

- `scripts/pantheon_content_capacity_guard.py`
- `tests/test_pantheon_content_capacity_guard.py`

## User gate review

1. Exact allowlist：PASS。
   - tracked source/test diff from base contains only:
     - `scripts/pantheon_content_capacity_guard.py`
     - `tests/test_pantheon_content_capacity_guard.py`
   - no scheduler, publisher installer, coordinator, promotion, runtime manifest, registry, DB, FSM, ledger, migration, or lane source file is modified.

2. Selector absence only when stage receipt and Publisher plist are both absent：PASS。
   - `validate_preactivation_transition` now maps missing `publisher-exact-run-id` stage receipt to `publisher_plist_preflight(..., require_no_exact_run_id=True)`.
   - The absence path continues through the existing manifest digest, generation, barrier, stage/live tuple, Rule24, topology, and mode checks.

3. Selector presence exact / empty / malformed / missing-one-side / mismatch / stale fail-closed：PASS。
   - Presence path rejects empty stage receipt before shared preflight.
   - Shared `publisher_plist_preflight(..., expected_exact_run_id=publisher_exact_run_id)` preserves format and exact stage receipt ↔ Publisher plist matching.
   - Independent negative matrix rerun covered 8 cases: stage digest drift, receipt missing, plist missing, receipt wrong/stale-vs-plist, receipt empty, both malformed, staged lane digest drift, and activation-only child I/O drift.
   - Important boundary: Capacity does not judge run completion stale; stale here is the selector/stage-plist contract drifting stale or wrong relative to Publisher plist. Run completion authority remains outside Capacity.

4. Other gates not loosened：PASS。
   - Source diff leaves subsequent staged plist loop, manifest tuple checks, live cohort comparison, Rule24/recovery topology, and mode checks in place.
   - Targeted suite and negative matrix preserve existing fail-closed coverage.

5. No run / queue / registry / new authority / per-lane expansion：PASS。
   - Source diff contains no run, queue, registry, completion, preallocation, placeholder, scheduler, publisher, coordinator, FSM, DB, ledger, or migration authority.
   - Test fixture references to `queue_root` / `publisher_state_root` are pre-existing fixture plumbing, not Capacity source authority.

6. Formal fresh + historical replay：PASS.
   - RED before-run receipts preserve original fresh/no-future-run failure at `validate_preactivation_transition:publisher-exact-run-id`.
   - Candidate green receipts show exact formal order `coordinator --install → publisher --install → capacity --install-recovery-stage`.
   - Fresh/no-selector path is GREEN with 7 staged plists and absent selector.
   - Historical valid selector path remains GREEN with 7 staged plists and exact selector.
   - Candidate green double-run files are byte-identical.

7. Broad receipt credibility：PASS.
   - Same command in receipt: `.venv/bin/python -m pytest -q tests/test_pantheon_content_capacity_guard.py tests/test_pantheon_content_runtime_manifest.py tests/test_agy_gemini_coordinator.py`.
   - parent baseline: `493 passed / 8 failed`.
   - candidate: `497 passed / 8 failed`; the delta is 4 new passing tests.
   - failure node set is exact-identical.
   - normalized error line count is 16 on both sides.
   - normalized error digest is identical: `834660a4c8ab119e7fff9e45af36ad32548b0c99e0bfd44a890269e7b2d196e2`.
   - raw stdout SHA values in the JSON match the saved raw stdout files.

8. LOC / diff hash：PASS.
   - `scripts/pantheon_content_capacity_guard.py`: `+20/-6`.
   - `tests/test_pantheon_content_capacity_guard.py`: `+93/-8`.
   - source + test changed LOC: `127`.
   - source/test diff SHA-256: `87029a93697ffcb374c39f349f48e1ce5823df0bce413c8ba454f018459fb847`.

9. Production/external 0 and compile/diff-check：PASS.
   - Receipts report production/live bytes before==after and external calls `0`.
   - This review did not run production, install, activate, provider, publisher, reviewer, scheduler, commit, or push actions.
   - Independent `py_compile` and `git diff --check` passed.

## Independent verification rerun

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/test_pantheon_content_capacity_guard.py -p no:cacheprovider`
  - `68 passed in 35.24s`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_g5_preactivation_stage_drift -p no:cacheprovider`
  - `8 passed in 8.33s`
- `PYTHONPYCACHEPREFIX=/private/tmp/pantheon-review-pycache-optionality .venv/bin/python -m py_compile scripts/pantheon_content_capacity_guard.py`
  - PASS
- `git diff --check`
  - PASS
- anti-expansion scan over the source/test diff:
  - no forbidden source authority additions found.
  - only expected selector/stage/test-fixture terms appeared.

No 501-node broad suite was rerun.

## Commit allowlist

Exact commit allowlist approved by this review:

- `scripts/pantheon_content_capacity_guard.py`
- `tests/test_pantheon_content_capacity_guard.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-PUBLISHER-EXACT-RUN-ACTIVATION-OPTIONALITY-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/.keep`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/broad-baseline-candidate.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/broad-baseline.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/broad-candidate.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/compare-broad-failures.py`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/evidence-index.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/green-targeted.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-green-harness.py`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-green-run-1.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-green-run-2.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-red-before-run-1.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/production-shaped-red-before-run-2.json`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/red-targeted.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_20260829/targeted-capacity.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_publisher_exact_run_activation_optionality_repair_review_20260829/RESULT.md`

Do not commit ignored `__pycache__/` files under the Repair artifact directory.

## Final

`GO`。無 P0/P1。可進本機提交；提交時必須限於上述 allowlist。

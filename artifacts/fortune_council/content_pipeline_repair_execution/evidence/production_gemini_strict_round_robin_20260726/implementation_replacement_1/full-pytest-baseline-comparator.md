# Full pytest baseline comparator

- candidate_full_pytest: `489 passed, 2 failed`
- candidate_isolated_retry: same two failures
- baseline_source: clean detached worktree
- baseline_head: `5ee733697727512e9c7bddb0572eedff4dd691c1`
- baseline_candidate_diff: none
- baseline_interpreter: same required local-only interpreter
- dependency_prepare_or_download: none
- baseline_result: same two failures
- classification: `PRE_EXISTING_BASELINE_MISMATCH`

The two exact failures are:

- `tests/test_api.py::test_predict_route_returns_charts_and_ai`
- `tests/test_calculators.py::test_ziwei_returns_palace_payload`

Both expected the Ziwei provider `iztro` but received the locked source fallback
provider `pantheon_ziwei`. The replacement worktree has no diff in the API,
calculator, Ziwei bridge, package manifest, lockfile, or these tests.

Per the mainline stop-loss ruling, this was the third and final execution of
the two cases. They will not be run a fourth time and are outside this card's
repair scope.

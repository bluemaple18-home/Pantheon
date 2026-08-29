# Gen06 Stale Fixture Review Evidence

Status: `GO`

## Verdict

`GO`

No P0/P1 blocking findings.

## Scope Reviewed

- Baseline HEAD: `5704fa6077aa4187619fddc08d9c29cad2f2dabf`
- Repair card: `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-STALE-FIXTURE-REPAIR-20260829.md`
- Repair evidence dir: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_repair_20260829/`
- Working-tree code diff: `tests/test_agy_multilingual_pipeline.py`
- Diff stat: `14 insertions, 1 deletion`

## Diff Review

Target node:

- `tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only`

Relevant lines:

- `tests/test_agy_multilingual_pipeline.py:2008` sets `gen06_dir`.
- `tests/test_agy_multilingual_pipeline.py:2010` defines `gen06_file_snapshot()`.
- `tests/test_agy_multilingual_pipeline.py:2020` snapshots Gen06 before hydration.
- `tests/test_agy_multilingual_pipeline.py:2037` starts Gen05 hydration.
- `tests/test_agy_multilingual_pipeline.py:2053` asserts post-hydration Gen06 snapshot equals the before snapshot.
- `tests/test_agy_multilingual_pipeline.py:2054` preserves the existing Gen05 legacy bytes assertion.
- `tests/test_agy_multilingual_pipeline.py:2055` preserves the existing continuation state assertion.

The change replaces the stale absence assertion with shape-neutral invariance:

- absent Gen06 before hydration remains absent after hydration because `None == None`;
- present Gen06 before hydration is represented by regular-file relative paths mapped to bytes;
- added, deleted, renamed, or byte-modified Gen06 regular files alter the dictionary and fail the assertion;
- Gen06 contents are read only to detect drift and are not passed into the Gen05 hydration path.

Existing Gen05 coverage/topology assertions remain strict:

- coverage length remains asserted at `22`;
- safety boundary remains `{False}`;
- hydrated outline topology still must differ from prior topology.

No source code, production code, hidden skip, xfail, or monkeypatch was added by the reviewed hunk.

## Repair Evidence Reviewed

Repair `RESULT.md` reports:

- RED command hit the same stale assertion: `assert not (run_dir / "generations/06").exists()`.
- GREEN exact test passed.
- GREEN full `tests/test_agy_multilingual_pipeline.py` passed.
- `git diff --check` passed.
- provider/coordinator/publisher/tag-push counts were `0`.

Repair production immutability receipt:

- File: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_repair_20260829/production-immutability-compare.json`
- Status: `PASS`
- Differences: `{}`
- Compared keys include runtime manifest, queue root, target run dir, Gen06 existence/tree/files, Gen07, ledger, approved-edit seal, queue state, provider/coordinator/publisher calls, and tag pushes.

Repair snapshots show the production fixture had `gen06_exists: true`, `gen07_exists: false`, and identical `gen06_tree_sha256` before and after verification:

- `8c7f2e2563db9e4fd4e3b2071a4bb8e847fbdf9743ee10e22fbd26f6d17d3216`

## Independent Commands

Exact test:

```bash
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only --tb=short -p no:cacheprovider
```

Result:

```text
collected 1 item
tests/test_agy_multilingual_pipeline.py . [100%]
1 passed in 0.04s
```

Full target file:

```bash
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py --tb=short -p no:cacheprovider
```

Result:

```text
collected 262 items
tests/test_agy_multilingual_pipeline.py ... [100%]
262 passed in 0.88s
```

Whitespace diff gate:

```bash
git diff --check
```

Result: return code `0`.

Diff scope:

```text
git diff --name-only
tests/test_agy_multilingual_pipeline.py
```

Review-created untracked artifacts:

```text
artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-STALE-FIXTURE-REVIEW-20260829.md
artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_review_20260829/RESULT.md
```

## Findings

None.

## Blocking Findings

None.

## Allowlist For Submit

- `tests/test_agy_multilingual_pipeline.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-STALE-FIXTURE-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_repair_20260829/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-STALE-FIXTURE-REVIEW-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_review_20260829/`

## Remaining Risk

The exact fixture is environment-dependent and skips if the production fixture mount is unavailable. On this review host it was mounted and the exact test ran, so this is not a blocker for this review.

## Confidence

High. The Repair is a narrow test-only change, independently re-ran the required exact and full target tests, preserves existing Gen05 assertions, and has production immutability evidence with an empty diff across the relevant runtime keys.

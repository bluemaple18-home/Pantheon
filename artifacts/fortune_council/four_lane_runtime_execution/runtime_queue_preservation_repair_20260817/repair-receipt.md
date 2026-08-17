# Runtime Queue Preservation Repair Receipt

card_id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REPAIR-20260817
dispatch_key: v1:e91fd7273749aebd0a744f48e0d2d92fb6c113f45a6aa74b7d71c97e62a238ce
activation_token: act-v1:1f0066d320680ccb49bda2d925432ad6b4dbd40f9fcbc006f97d8370f3d87e0c
base_sha: 8fad3fcbc3940bfde311eac02a5f6010e10f0b41
implementation_candidate_sha: b30cf964818e823611dec26b102d4984e01e9214
previous_delivery_tip_sha: c5cce3db0ae313d5dbd20192f8ffea33451c4039
repair_1_parent_candidate_sha: c5cce3db0ae313d5dbd20192f8ffea33451c4039
repair_1_review_card_sha: a7184dddb1caa78ba2ae988fd11f6d65afdedb2b

## Scope

- Modified `scripts/pantheon_content_runtime_promotion.py`.
- Modified `tests/test_pantheon_content_runtime_promotion.py`.
- Added this evidence receipt under the card evidence path.
- Did not touch production runtime, queue, launchd, remotes, Publisher, coordinator, runner, sitemap, or article content.

## CodeGraph

- activation receipt: CONTEXT_DEGRADED/codegraph_scope_unavailable.
- fallback scope: `scripts/pantheon_content_runtime_promotion.py`, `tests/test_pantheon_content_runtime_promotion.py`, and bounded docs search for `gsc-copy` data shape.
- Repair-1 status: CodeGraph initialized; `codegraph_context` did not surface the promotion helper, so bounded source reads were used for `_queue_snapshot_digest` and the targeted tests.

## RED

Command:

```text
uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_promotion.py -q
```

Result before implementation:

```text
5 failed, 20 passed
```

Failing contracts:

- failed run preservation was rejected as non-promotable.
- missing failed run identity did not emit the new fail-closed contract.
- gsc-copy-only residue was not rejected at plan time.
- invalid gsc-copy JSON was hidden behind failed-run rejection.
- gsc-copy plan/apply drift could not reach the new rollback assertion.

## GREEN

Commands:

```text
uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_promotion.py -q
uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
git diff --check
```

Results:

```text
25 passed in 8.77s
73 passed in 12.31s
git diff --check passed
```

## Behavior

- `active`, `complete`, and `failed` run states are preservable only when their exact run identity is listed in `preserved_run_ids`.
- Failed runs are snapshotted as preserved queue identity; promotion does not execute, publish, or mutate them.
- Non-empty `runs` or `gsc-copy` residue without explicit preserved run IDs fails during plan.
- `gsc-copy` content is part of `queue_identity_snapshot` and `queue_snapshot_digest`.
- `.json` files under `gsc-copy` must parse as JSON objects; symlinks and non-file residue fail closed.
- Postcheck compares the planned queue identity snapshot and full queue digest; drift raises `ROLLBACK_COMPLETE`.

## Remaining Risk

- No production runtime was inspected or mutated in this repair task.
- The exact production 88-run and 82-entry gsc-copy snapshot still needs mainline dry-run verification before any apply authority.
- Repair-1 did not add a synthetic in-function concurrent filesystem race harness. The deterministic coverage added here proves plan-to-apply directory-only drift fail-closed behavior; deeper TOCTOU hardening should stay separate unless mainline requires it.

## Repair-1 Reviewer NO-GO

- reviewer_thread: 01a00f1f-9be9-7370-9a67-9f6aba40627a
- reviewer_5_5_receipt: 23e340d0ad95f6d579c8c5b7e955b1451b63b718
- reviewer_5_6_sol_high_receipt: 267d26f9505b8977c554a4a346e4b87901158c6a5
- verdict: FINAL_REVIEW_NO_GO
- parent_candidate: c5cce3db0ae313d5dbd20192f8ffea33451c4039

## Repair-1 RED

Command:

```text
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_promotion.py -q
```

Result before implementation:

```text
2 failed, 25 passed
```

Failing contracts:

- plan-to-apply insertion of `queue/outbox/empty-drift/` incorrectly reached `POSTCHECK_PASSED`.
- plan-to-apply creation of empty `queue/gsc-copy/` root incorrectly reached `POSTCHECK_PASSED`.

## Repair-1 GREEN

Commands:

```text
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_promotion.py -q
.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
git diff --check
```

Results:

```text
27 passed in 9.75s
75 passed in 13.15s
git diff --check passed
```

Behavior added:

- queue snapshot digest now binds root existence.
- queue snapshot digest now includes directory entries by path and type.
- queue snapshot digest still includes file entries by path, type, and byte digest.
- directory-only queue drift during apply postcheck raises `ROLLBACK_COMPLETE` and leaves existing queue bytes unchanged.

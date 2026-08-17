# Runtime Queue Preservation Repair Receipt

card_id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REPAIR-20260817
dispatch_key: v1:e91fd7273749aebd0a744f48e0d2d92fb6c113f45a6aa74b7d71c97e62a238ce
activation_token: act-v1:1f0066d320680ccb49bda2d925432ad6b4dbd40f9fcbc006f97d8370f3d87e0c
base_sha: 8fad3fcbc3940bfde311eac02a5f6010e10f0b41
implementation_candidate_sha: b30cf964818e823611dec26b102d4984e01e9214
delivery_tip_sha: this evidence-only repair commit becomes the final delivery tip

## Scope

- Modified `scripts/pantheon_content_runtime_promotion.py`.
- Modified `tests/test_pantheon_content_runtime_promotion.py`.
- Added this evidence receipt under the card evidence path.
- Did not touch production runtime, queue, launchd, remotes, Publisher, coordinator, runner, sitemap, or article content.

## CodeGraph

- activation receipt: CONTEXT_DEGRADED/codegraph_scope_unavailable.
- fallback scope: `scripts/pantheon_content_runtime_promotion.py`, `tests/test_pantheon_content_runtime_promotion.py`, and bounded docs search for `gsc-copy` data shape.

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

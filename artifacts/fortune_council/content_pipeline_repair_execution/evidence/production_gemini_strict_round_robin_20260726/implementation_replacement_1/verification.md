# Verification

- status: `DELIVERED_CANDIDATE`
- source_head: `5ee733697727512e9c7bddb0572eedff4dd691c1`
- candidate_scope: implementation only
- prepare_or_download: none
- live_or_control_plane_write: none

## Allocator acceptance

- Focused allocator/installer tests: `38 passed, 89 deselected`.
- Runner/outbox/coordinator: `127 passed`.
- Publisher and multilingual regressions: `59 passed`.
- Four-process stress: 300 allocations; ordinals `1..300`; no duplicate or
  gap; account-1/account-2/account-3 each selected 100 times.
- Sequential allocation: exact `account-1, account-2, account-3` repetition.
- Durable state commit occurs before selected credential open and provider
  request. Crash and provider failure consume the ordinal.
- Public `credential_pool` remains exactly
  `pool_id/slot_id/manifest_sha256`.
- A single allocator helper isolates lock/state/durable-commit logic and keeps
  the runner change limited to manifest, credential, and receipt integration;
  no additional helper or test module was added.

## Full pytest

- Unfiltered candidate run: `489 passed, 2 failed`.
- The two failures reproduced identically in a clean detached source worktree
  at the locked source SHA with the same interpreter and no candidate diff.
- Classification: `PRE_EXISTING_BASELINE_MISMATCH`.
- Per stop-loss, the two Ziwei cases were not run a fourth time.
- Post-refactor suite excluding only those two exact cases:
  `490 passed, 2 deselected`.

See `full-pytest-baseline-comparator.md` for the exact cases and comparator.

## Static and boundary gates

- Python compile: pass.
- Installer `bash -n`: pass.
- Lane plist lint: pass.
- `git diff --check`: pass.
- Changed-line privacy scan: pass.
- V4 code/test/plist/docs path diff relative to source: empty.
- `scripts/agy_gemini_outbox.py` diff relative to source: empty.

## Remaining risk

- No live production job, credential value, launchd installation, restart,
  deploy, or acceptance action was performed.
- The pre-existing Ziwei baseline mismatch remains outside this card.
- Mainline retains independent Review, PR, merge, deploy, production, and
  acceptance responsibility.

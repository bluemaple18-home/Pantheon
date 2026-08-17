# Runtime Queue Preservation Review Receipt

card_id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
dispatch_key: v1:a8561b9b13d01a1400edecae2e5576850e70610ed38af6ce140661e5d9bdb21f
activation_token_received: true
formal_thread: 01a00f1f-9be9-7370-9a67-9f6aba40627a
base_sha: 8fad3fcbc3940bfde311eac02a5f6010e10f0b41
implementation_sha: b30cf964818e823611dec26b102d4984e01e9214
reviewed_candidate_sha: c5cce3db0ae313d5dbd20192f8ffea33451c4039
diff: 8fad3fcbc3940bfde311eac02a5f6010e10f0b41..c5cce3db0ae313d5dbd20192f8ffea33451c4039

## Scope

- Reviewed `scripts/pantheon_content_runtime_promotion.py`.
- Reviewed `tests/test_pantheon_content_runtime_promotion.py`.
- Reviewed `artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_repair_20260817/repair-receipt.md`.
- Did not modify source, tests, candidate commit, production runtime, queue, launchd, network, remotes, tags, or merge state.

## CodeGraph

- `codegraph_context` returned context but did not surface the target queue preservation symbols directly.
- Review used bounded fallback over the fixed candidate diff, candidate file bodies, repair card, repair receipt, and targeted tests.

## Verification

Command:

```text
uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q
```

Result:

```text
73 passed in 12.87s
```

Command:

```text
git diff --check 8fad3fcbc3940bfde311eac02a5f6010e10f0b41..c5cce3db0ae313d5dbd20192f8ffea33451c4039
```

Result:

```text
passed
```

Ad hoc scratch repro outside the repo:

```text
uv run --frozen --group dev python /private/tmp/pantheon_queue_dir_drift_repro.py
```

Result:

```json
{"apply_status": "POSTCHECK_PASSED", "empty_dir_exists": true, "receipt_state": "POSTCHECK_PASSED"}
```

## Findings

- [P1] Empty queue directory drift passes postcheck - scripts/pantheon_content_runtime_promotion.py:319
  Trigger: after `plan_promotion()` captures `queue_identity_snapshot` and `queue_snapshot_digest`, create a new empty directory under the managed queue before or during `apply_promotion()`; the scratch repro injected `queue/outbox/empty-drift` inside `_install_private_stage`.
  Risk: the review contract says any plan-to-apply queue/gsc-copy drift must rollback runtime and that directory identity must be checked. Current `_queue_snapshot_digest()` only delegates to `tree_digest()`, and `tree_digest()` hashes files only. `_queue_identity_snapshot()` enumerates `runs` and `gsc-copy`, but does not include other queue directories such as `outbox`. As a result, directory-only queue drift can survive with `POSTCHECK_PASSED`, leaving runtime actor/manifest/stage promoted against a queue state that was not the planned state.
  Fix: make the queue postcheck snapshot include directory entries for the whole managed queue, or add a full queue identity snapshot that records deterministic `path/type` for directories plus file digests, and compare that in both plan and postcheck. Ensure symlink/unexpected residue behavior remains fail closed.
  Validation gap: add a regression test that mutates the queue with a new empty directory between plan and postcheck and asserts `ROLLBACK_COMPLETE`, `state == ROLLED_BACK`, existing queue file bytes unchanged, and the drift directory is not treated as planned state.
  Confidence: high; the scratch repro produced `POSTCHECK_PASSED` with the drift directory still present.

## Residual P2/P3

- [P2] Tests do not assert queue directory identity drift. Existing tests cover gsc-copy file drift, invalid gsc-copy JSON, duplicate/unexpected/missing run identity, failed status preservation, symlink detection, and empty preserve list residue. They do not cover directory-only drift in `queue` or `gsc-copy`, which is the uncovered edge above.

## Positive Coverage Observed

- Failed runs are preserved as identity only and are not routed to execute or publish by this candidate.
- Non-empty `runs` or `gsc-copy` with an empty preserve list fails before transaction creation.
- `gsc-copy` snapshot is deterministic over sorted paths and includes `path`, `type`, and file `digest`.
- `.json` files under `gsc-copy` are parsed as JSON objects; invalid JSON fails closed before runtime mutation.
- Duplicate, unexpected, missing, and unsupported preserved run identities fail closed.
- gsc-copy file drift during apply triggers rollback in the added targeted test.

## Verdict

REVIEW_NO_GO

Reason: unresolved P1 plan-to-apply queue drift bug.

## Final Re-review

FINAL_REVIEW_NO_GO

Re-review focus:

- failed run not revived: pass.
- gsc-copy identity binding: pass for tracked file/dir entries under `gsc-copy`; residual gap is directory-only drift not covered by full queue digest.
- TOCTOU/path traversal: path traversal via run IDs is constrained by direct registry enumeration and safe IDs; TOCTOU drift check is incomplete for empty directories.
- plan-to-apply drift rollback: fails for directory-only queue drift.
- queue bytes unchanged: candidate preserves existing bytes in covered tests, but the missing directory identity rollback means the transaction can still commit with unplanned queue structure.
- test coverage: targeted suite passes, but misses the P1 directory drift regression.

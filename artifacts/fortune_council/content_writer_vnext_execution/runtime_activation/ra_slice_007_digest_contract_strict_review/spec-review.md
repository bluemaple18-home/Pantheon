# RA007 Digest Contract Strict Successor Spec Review

## Scope

- Review card: `CARD-CONTENT-WRITER-VNEXT-RA-SLICE-007-DIGEST-CONTRACT-STRICT-SUCCESSOR-001`
- Strict card source: `dd6dac202edef2bde3f060c09078295ed31691ba`
- Candidate: `def554580ced5af1399a1edfe8a9debc90a4b83b`
- Reviewed finding: `RA007-DIGEST-NOT-RECOMPUTABLE-P1`
- Review mode: fixed-SHA, read-only candidate review; no candidate code or evidence was modified.

## Source Decision

CodeGraph source decision was attempted first. The workspace index was unavailable with `CodeGraph not initialized`, so review proceeded with bounded `git show`, `git diff`, `rg`, and JSON parsing limited to the strict card and RA007 capacity preflight artifacts.

## Spec Checks

- Candidate parent is exactly `dd6dac202edef2bde3f060c09078295ed31691ba`.
- Candidate diff only changes:
  - `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/resource-snapshot.json`
  - `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/verification.txt`
- `resource-snapshot.json` now commits a versioned digest contract at lines 11-86 with domain, version, algorithm, digest format, serialization, field exclusion, input projection rule, sample field order, canonical projections, and expected digests.
- `digest_inputs[].canonical_projection` exactly matches the committed `samples[]` fields listed by `sample_field_order`, excluding only `measurement_digest`.
- Both `measurement_digest` values were recomputed from committed JSON only and exactly match:
  - sample 0: `sha256:e7b2aa52c8070fc95a7f791d8941a4dee40bb53ab0cfd4b8582a307d84d8d79f`
  - sample 1: `sha256:b7332c4dcc88b64b35634803450f9eb05513d1a955afb551792a35de33fda224`
- The original measurement values remain unchanged from the parent commit for all fields in `sample_field_order`.
- `sample_interval_seconds` remains `3`, within `1..300`.
- Four runtime indicators remain non-empty: VM allocation, swap used, memory pressure, and Codex RSS.
- Reserve, deficit, and deltas are independently recomputable from committed values.
- Verdict remains `NO-GO`.

## Spec Verdict

No P0/P1 spec finding remains. The fixed finding `RA007-DIGEST-NOT-RECOMPUTABLE-P1` is resolved by committed, portable, versioned digest inputs.

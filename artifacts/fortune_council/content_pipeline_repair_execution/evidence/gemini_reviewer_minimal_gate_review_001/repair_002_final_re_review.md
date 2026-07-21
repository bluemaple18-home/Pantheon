# Gemini Reviewer minimal gate Repair 2 final re-review

status: `RE_REVIEW_NO_GO`

## Review identity

- role: same independent Reviewer; review only, no candidate modification
- original full-range base: `4e2a9258a1e762935e01d495bf5f2b48cefee05d`
- prior candidate: `66c070f43c61d38df4a1f7944b277ca9dc05406e`
- reviewed Repair 2 candidate: `5e9b1c898d943ae59f24f9f87206c3f60b0a0ceb`
- Repair 2 parent: `66c070f43c61d38df4a1f7944b277ca9dc05406e`
- prior NO_GO evidence: `472fb0c736971d1cae7a6f5979b5c27249f2aa21`

## Findings

- [P2] `OPEN` — Error receipt can copy a stale fingerprint from the prior invocation — `scripts/agy_seo_copy_pipeline.py:2137`
  - Trigger: one client invocation succeeds and sets `last_transport_receipt`; the next invocation fails strict parsing before its transport replaces that state, such as malformed outer Gemini CLI envelope JSON.
  - Evidence: an offline two-call reproduction on the fixed candidate produced `stale_receipt_copied=true`; the second error receipt reused the first response's SHA/61-byte count and did not match the second output hash.
  - Risk: the receipt contains an apparently valid but false response fingerprint, so the failed operation cannot be truthfully bound to its request. Fail-closed verdict behavior remains intact, but audit evidence is incorrect.
  - Closure requirement: clear or scope transport receipt state at the start of every invocation and only copy a fingerprint explicitly produced by that same invocation. Cover both inner response parse failure and outer-envelope/early transport failure without storing response content, stderr, or prompt material.

- [P2] `RESOLVED` — Reviewer process accounting now counts operation receipts once — `scripts/agy_seo_copy_pipeline.py:2155`
  - Five-article success records 5; kth-call failure records the three receipts actually attempted; reviewer-only rounds record 5/10/15; closure records 5 and adds exactly 5 to the prior total.
  - Counting is derived from persisted Reviewer operation receipts, including success/error/pending and runtime-retry receipt names, instead of a batch-success increment or fixed constant.
  - Focused regressions and the complete production Reviewer suite pass. No undercount, double count, or fixed-one path was found in the reviewed scope.

- [P2] `OPEN` — Global codes still provide an equivalent cross-slot path — `scripts/agy_seo_copy_pipeline.py:1916`
  - Trigger: A and B are reviewed from the same full-batch context; B alone has the relevant problem, but A's request returns a globally allowed code such as `TEMPLATE_USAGE` with a B-only message.
  - Evidence: an offline two-article reproduction on the fixed candidate was accepted by schema/rubric and mapped `TEMPLATE_USAGE` to A, yielding A=`REJECT` and B=`APPROVE`.
  - Risk: Repair 2 correctly limits deterministic-only codes by target, but every target still receives all global codes. The mapper has no response identity field and therefore cannot reject an equivalent global-code judgment about another slot; a wrong article may be repaired.
  - Closure requirement: make the complete accepted-code contract target-bound or add a machine-verifiable target binding that rejects judgments about another slot. A regression must prove both B-only deterministic codes and equivalent global codes cannot be attached to A while B's legitimate code and candidate SHA remain valid.

## Spec axis

- Finding 1: `OPEN`. Strict-parse failure remains fail closed and does not rerun Writer, but the preserved SHA/bytes are not guaranteed to belong to the current invocation.
- Finding 2: `RESOLVED`. Multi-article, partial failure, reviewer-only, and closure accounting meet the requested one-count-per-invocation contract.
- Finding 3: `OPEN`. Target-specific deterministic allowlists work, local identity/SHA mapping is correct for compliant judgments, but the equivalent global-code cross-slot path remains.
- Repair 2 candidate and parent SHAs match the fixed contract; candidate content was not modified during review.

## Standards axis

- Repair 2 delta is exactly five files: production pipeline, its tests, and three files under the Repair 2 evidence directory.
- No docs, outbox/runner/corpus harness, app, article, registry, metadata, prerender, sitemap, feed, redirect, deployment, or publication path changed.
- Error receipts still exclude response content, raw response, stderr, and prompt fields.
- Privacy/secret/raw/path/debug scan and `git diff --check` passed.
- No Gemini CLI, HTTP, external model, environment mutation, merge, push, deploy, publish, or production operation was performed.

## Verification

- Repair 2 regression selection: `8 passed`
- complete production Reviewer focused suite: `90 passed`
- full pytest: `220 passed, 2 failed, 2 warnings`
- unrelated full-suite failures: `tests/test_api.py` and `tests/test_calculators.py` expect Ziwei provider `iztro`, while the baseline returns `pantheon_ziwei`; neither path is in the Repair 2 delta
- `py_compile`: PASS
- stored corpus offline recompute: `DELIVERED_CORPUS`, 12 rows, four cases 3/3, typed gates true, candidate SHA invariant true
- `provider_model_calls`: `unobservable/unknown`
- changed-file allowlist: PASS
- privacy/secret/raw/path/debug scan: PASS
- `git diff --check`: PASS for Repair 2 delta and necessary full-range regression scan
- an archive-only focused run was discarded because tests requiring `git rev-parse HEAD` cannot run without repository metadata; the exact clean candidate worktree rerun produced the authoritative `90 passed`

## Testing gaps

- No regression covers a prior successful transport receipt followed by a current strict-parse/early transport failure, so stale fingerprint reuse is undetected.
- The cross-slot regression covers only B's deterministic-only code. It does not attempt a globally allowlisted equivalent code for A, which the fixed candidate still accepts.

## Residual risks

- Stored corpus remains single-case and cannot exercise multi-article target confusion.
- Provider-internal calls and retries remain unobservable; only external operation receipts can be counted.
- Full suite retains the two unrelated Ziwei baseline failures.

## Verdict

`RE_REVIEW_NO_GO`

Two P2 findings remain open; therefore the entire chain is `BLOCKED`. This report does not recommend or authorize another repair, candidate modification, integration, canary, merge, push, deploy, publish, production use, or restoration of any content line.

# Gemini Reviewer minimal gate full-range re-review

status: `FULL_RANGE_NO_GO`

## Review identity

- role: same independent Reviewer; review only, no candidate repair
- implementation base SHA: `4e2a9258a1e762935e01d495bf5f2b48cefee05d`
- reviewed fixed candidate SHA: `66c070f43c61d38df4a1f7944b277ca9dc05406e`
- previous Repair 1 delta review remains scoped to `c5b33832d2c7ccb323e43fed09f502c6a3494a2d..66c070f43c61d38df4a1f7944b277ca9dc05406e`
- candidate was not modified; review used only local code, tests, and stored sanitized evidence

## Findings

- [P2] Strict-parse failures discard the response fingerprint — `scripts/agy_seo_copy_pipeline.py:2129`
  - Trigger: Reviewer transport has already received bytes and populated `last_transport_receipt`, but strict JSON parsing raises before `generate_json()` returns.
  - Risk: the error operation receipt records only status/error type and omits `output_sha256` and `output_bytes`; the failed response cannot be bound to the request or audited even though the transport had the fingerprint. This violates the request/response receipt contract specifically on the fail-closed path.
  - Evidence: an offline test double preloaded a transport receipt with SHA/77 bytes and raised `ValueError`; the written error receipt had neither output field.
  - Suggested fix: in the exception branch, copy available transport output SHA/bytes (and a typed parse position where applicable) before writing the receipt. Add a regression test for malformed Reviewer JSON after bytes were received; do not store raw output.

- [P2] Per-article Reviewer process accounting undercounts production executions — `scripts/agy_seo_copy_pipeline.py:2452`
  - Trigger: a multi-article review fails after one or more per-article calls, runs reviewer-only rounds, or executes the five-article closure path.
  - Risk: `reviewer_calls` increases only after an entire batch succeeds; partial failures are recorded as zero. `review_rewrite_release_final()` performs up to five calls per round but never updates `reviewer_processes` (`scripts/agy_seo_copy_pipeline.py:2948`). The closure always records one process even though `_generate_minimal_review()` loops over all five articles (`scripts/agy_seo_copy_pipeline.py:3501`). Evidence and cost/retry accounting therefore cannot be reconciled with the actual 2→10 or reviewer-only execution shape.
  - Suggested fix: count at the per-invocation seam or derive totals from immutable operation receipts, including partial failures and pending outbox jobs. Update reviewer-only and closure evidence, then test five-article success, kth-call failure, and multi-round totals.

- [P2] Batch-wide finding allowlist permits cross-slot findings to pass validation — `scripts/agy_seo_copy_pipeline.py:1911`
  - Trigger: one article in a multi-article batch has a deterministic-only code while another target slot is being reviewed. Every request receives the union of global codes and deterministic codes from all articles, while the base prompt also contains the full batch.
  - Risk: a judgment for target A can emit a code belonging only to B and still pass schema/rubric validation; the mapper then binds that judgment to A because identity is injected solely from invocation order. The later deterministic merge correctly adds B's local finding but cannot remove the spurious finding already attached to A, causing a wrong rejection and unnecessary Writer repair.
  - Suggested fix: build a request-specific allowlist for each target slot, keep deterministic-only codes out of model output when they are locally merged, or validate returned codes against the target article's policy set. Add a two-article regression where only B owns a unique deterministic code and prove A cannot return it.

## Spec axis

- PASS: Reviewer output is per-article `ReviewerJudgmentV1` with closed fields; strict duplicate-key parser rejects duplicates at arbitrary object depth.
- PASS: cross-field rubric only accepts `APPROVE + false + []` or `REJECT + true + non-empty HARD findings`.
- PASS: local mapper injects run/article identity and candidate SHA from local inputs; fixed candidate SHA remains unchanged.
- PASS: deterministic local findings are merged through `article_id` into the intended article and force fail-closed rejection.
- PASS: Reviewer parse/schema/rubric/map errors fail closed and do not enter the Writer content-repair loop.
- PASS: Writer schema/prompt behavior is unchanged except for the explicitly allowed shared strict duplicate-key parser.
- PASS: CLI/HTTP success receipts hash the response payload rather than stderr; stored evidence contains no response content.
- FAIL: error receipts do not retain response SHA/bytes after strict parse failure.
- FAIL: production Reviewer process evidence does not represent partial, reviewer-only, or closure executions accurately.
- FAIL: finding code validation is not target-specific in multi-article requests.

## Standards axis

- Full-range changed files are confined to task cards/evidence, Reviewer docs, two scripts, and three test files; `app/**`, articles, registry, metadata, prerender, sitemap, feed, redirects, deploy and publication paths have zero changes.
- Outbox and runner runtime files have zero diff; their existing SHA-bound request/inbox flow was inspected with the new minimal Reviewer calls.
- Evidence privacy scan found no prompt content, raw response, stderr payload, secret, PII, or machine-local absolute path.
- No Gemini CLI, HTTP, external model, environment mutation, merge, push, deploy, publish, or production operation was performed.
- `git diff --check` passed for `4e2a9258..66c070f4`.

## Verification

- production Reviewer focused tests: `84 passed`
- `py_compile`: PASS for production pipeline, outbox, runner, corpus harness, and focused test files
- stored corpus offline recompute: `DELIVERED_CORPUS`, 12 rows, four cases 3/3, typed gates true, candidate SHA invariant true
- `provider_model_calls`: `unobservable/unknown`
- full pytest: `214 passed, 2 failed, 2 warnings`
- unrelated full-suite failures: `tests/test_api.py` and `tests/test_calculators.py` expect Ziwei provider `iztro` but baseline returns `pantheon_ziwei`; those paths are absent from the candidate diff
- changed-file/forbidden-path scan: PASS
- privacy/secret/raw/local-path evidence scan: PASS
- `git diff --check`: PASS

## Testing gaps

- No regression asserts that a strict-parse error receipt preserves output SHA/bytes without storing content.
- No regression verifies partial per-article failure accounting, reviewer-only round totals, or the five-process closure total.
- No multi-article regression proves that a target slot cannot accept another article's deterministic-only code.
- Existing outbox end-to-end test covers one article; it does not prove two-to-five sequential Reviewer jobs preserve slot/SHA isolation across repeated ticks.

## Residual risks

- The sanitized corpus covers four single-case judgments, not multi-article cross-slot behavior or production prompt depth.
- Provider-internal calls/retries remain unobservable; only external process/job receipts may be counted.
- Full suite retains two unrelated Ziwei baseline failures.

## Verdict

`FULL_RANGE_NO_GO`

The previous delta-only `GO` remains valid only for the Repair 1 fixture change. It is insufficient for integration of the full production implementation. The fixed candidate must not proceed to end-to-end 4-product canary until all P2 findings are repaired and independently re-reviewed. This verdict does not authorize candidate modification, merge, push, deploy, publish, production use, or restoration of any content line.

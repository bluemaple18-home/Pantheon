# Transport V2 independent review

Verdict: `NO_GO`

Reviewed range: `22b7d44a8bdee8d64aaea6addeaa882817141bbc..96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c`

Review provisioning commit: `ee850aacce97d1f87b1df6c1e2869e753e16c574`

## Findings

### [P1] Strict gate failure leaves a non-retryable successful-process receipt

- Path: `scripts/agy_seo_copy_pipeline.py:2072`, `scripts/agy_seo_copy_pipeline.py:2289`
- Trigger: the CLI process exits zero and transport parsing succeeds, but `_validate_reviewer_judgment` later rejects schema, rubric, duplicate/unknown code, blank message, or a cross-field contradiction. The terminal receipt is already `process_succeeded`; the next resume sees that status and raises `operation receipt already exists and is not retryable` before starting a fresh invocation.
- Evidence: `adversarial_probes.py` prints `REPRO strict/schema/rubric failed item cannot resume after process_succeeded receipt`.
- Risk: a failed Reviewer identity cannot be resumed. In higher-level loops the exception is converted into an invalid review, which can discard already successful item progress and cause unrelated Writer/Reviewer work to be repeated. This violates failed-identity-only resume and the terminal/gate separation contract.
- Suggested fix: make retry eligibility derive from the bound strict gate result, never only from terminal process status; allocate an invocation-unique immutable terminal path for every retry and preserve the prior receipt/event pair.
- Validation gap: the existing resume test covers a transport exception whose legacy receipt status is `error`; it does not cover `process_succeeded` followed by strict/schema/rubric failure.
- Confidence: high.

### [P1] Receipt replay accepts malformed or contradictory records as successful

- Path: `scripts/agy_seo_copy_pipeline.py:2128`, `scripts/agy_gemini_transport_probe.py:692`
- Trigger: replay is given an unknown terminal status, wrong request/candidate SHA, wrong gate event type, gate written before terminal, an additional duplicate gate event, or a stored corpus row whose terminal candidate SHA and statuses were altered.
- Evidence: the production replay reports one success, and stored corpus replay still reports `DELIVERED_CORPUS`; `adversarial_probes.py` prints `REPRO replay accepts malformed binding/status/event and ignores duplicate gate`.
- Risk: corrupted, stale, reordered, duplicated, or cross-candidate evidence can be treated as closure. Stored corpus replay does not validate the expected request/candidate/item contract, exact terminal/event schemas, allowed statuses, one gate per invocation, or terminal-before-gate ordering.
- Suggested fix: define strict receipt/event schemas and allowed state transitions; require exactly one terminal plus one gate per invocation; validate request, candidate, item, attempt, event type, status and ordering against caller-owned expectations; reject unknown, duplicate or missing records instead of normalizing them to success/failed/pending.
- Validation gap: current tests mostly construct typed in-memory outcomes and verify duplicate invocation IDs. They do not mutate persisted candidate/request binding, event type/status, event multiplicity, or ordering.
- Confidence: high.

### [P1] Production process accounting is still control-flow-derived and undercounts failures/closure

- Path: `scripts/agy_seo_copy_pipeline.py:2665`, `scripts/agy_seo_copy_pipeline.py:3063`, `scripts/agy_seo_copy_pipeline.py:3725`
- Trigger: a per-item review fails at item k before `review_candidate_items_v2` returns, or the five-item closure path completes.
- Evidence: `reviewer_calls` is incremented only after the whole per-item function returns, so processes started before an exception add zero. The closure path runs one process per candidate item but hard-codes `closure_reviewer_processes: 1` and increments the total by one.
- Risk: run evidence can understate actual external processes, lose partial-failure counts, and mix review rounds with process invocations. This defeats the event-derived accounting requirement even though the separate `accounting.json` may contain more accurate receipt counts.
- Suggested fix: derive all externally reported Reviewer counts from validated terminal receipts at the end of each path; keep attempts, transport retries, review rounds, Writer invocations and Reviewer invocations as separate fields.
- Validation gap: closure tests assert Writer count and content changes but do not assert Reviewer process counts; partial-failure tests do not assert top-level `run-evidence.json` after a k-th item failure.
- Confidence: high.

### [P2] Global Reviewer codes and free-form messages remain cross-slot attachable

- Path: `scripts/agy_seo_copy_pipeline.py:1983`, `scripts/agy_seo_copy_pipeline.py:2043`
- Trigger: Reviewer A returns a globally accepted code such as `TEMPLATE_USAGE` with a B-only semantic message that does not literally include B's item ID.
- Evidence: `_validate_reviewer_judgment` accepts `另一篇文章使用重複模板，本篇本身沒有問題` for A because it checks only the global code set and literal forbidden identity tokens. `adversarial_probes.py` prints `REPRO cross-slot global code/message accepted for A`.
- Risk: the prior cross-article attribution finding remains open. Caller-local identity injection prevents model-controlled routing, but it does not prove that a global code/message is grounded in the current target.
- Suggested fix: make the accepted-code contract target-derived and locally verifiable. Keep deterministic-only codes out of model output, and require target-local predicates/evidence for every model-eligible code; otherwise fail closed.
- Validation gap: the existing cross-slot test includes the literal token `ITEM-B`; it does not cover semantically B-only text without B's ID, global codes, or swapped candidate fingerprints.
- Confidence: high.

## Spec axis

`NO_GO`. Per-item process fan-out, strict JSON handling, invocation-local stdout fingerprints, timeout nulls and provider-call unknownness are present. However, target-bound accepted-code semantics, strict-failure resume, persisted replay integrity, and exact process accounting are mandatory invariants and remain violated by P1/P2 findings.

## Standards axis

`NO_GO`. The fixed candidate range stays within its implementation allowlist; focused tests, py_compile, stored corpus replay, privacy scan and diff check pass. The replay implementation nevertheless fails closed-state and auditability standards because persisted evidence is only partially validated and top-level counters are still derived from control flow.

## Testing gaps

- No production test for exit-zero receipt followed by schema/rubric failure and a fresh resume invocation.
- No persisted replay matrix for unknown statuses, wrong event type, candidate/request/attempt mismatch, duplicate gate, gate-before-terminal, or missing terminal after an invocation start.
- No semantic cross-slot test where B-only prose omits B's literal identity token.
- No first/middle/last per-item failure assertion against final `run-evidence.json` counters and actual receipt count.
- No closure assertion proving five per-item Reviewer processes are recorded as five.

## Residual risks

- The stored six-process corpus is internally replayable under the current permissive verifier, but that verifier cannot establish candidate/request binding integrity after tampering.
- File-based append-only behavior is not enforced with exclusive creation or a strict one-terminal/one-gate manifest; concurrent or manual overwrite risk remains outside current tests.
- Full suite was not reclassified as green. Implementation evidence reports the two known Ziwei baseline failures; this review ran the focused affected suite only.

## Decision

Four blocking findings remain (`P1` x3, `P2` x1). Under the card contract, any P0/P1/P2 or unreproduced critical invariant requires `NO_GO`. Candidate code was not modified or repaired.

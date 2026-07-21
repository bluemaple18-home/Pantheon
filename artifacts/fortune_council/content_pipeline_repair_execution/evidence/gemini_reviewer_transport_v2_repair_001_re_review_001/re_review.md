# Transport V2 Repair generation 1 independent re-review

Verdict: `NO_GO`

Fixed Repair candidate: `1bac6ea896c14f9f6b7dc4c3097f8b17cfbfff65`

Provisioning parent: `144e757b32016bf224700661925ee751d4173d0c`

Prior Review evidence: `d8b6a235bd19d8aae72d40565841f09d35b3f83d`

Fixed V2 candidate ancestor: `96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c`

## Findings

### [P1-01] Retry eligibility still trusts an unbound failed gate

- Path: `scripts/agy_seo_copy_pipeline.py:2437`, `scripts/agy_seo_copy_pipeline.py:2454`
- Trigger: a `process_succeeded` terminal for item A/invocation X is accompanied by the expected filename, but the gate payload declares item B/invocation Y while retaining `event_type=reviewer_strict_gate` and `status=failed`.
- Evidence: `_generate_with_receipt` starts a new invocation and creates `terminal-receipt-runtime-retry-01.json`; the independent probe prints `REPRO P1-01 mismatched gate binding authorizes a fresh retry`.
- Risk: retry eligibility is not actually derived from a validated terminal/gate pair for the same invocation and binding. Persisted tampering can cause an unauthorized extra process before later replay rejects the records.
- Suggested fix: validate the full terminal and gate schemas, invocation ID, item ID, request/candidate/attempt binding and legal transition before allocating or starting a retry.
- Validation gap: Repair tests cover a legitimate failed gate, but not a failed gate whose filename matches while its payload binding differs.
- Confidence: high.

### [P1-02] Malformed terminal files can be silently ignored as pending

- Path: `scripts/agy_seo_copy_pipeline.py:2216`
- Trigger: a persisted `terminal-receipt.json` exists with schema version, invocation/item/attempt/request/candidate fields but omits `terminal_status`, and no gate is present.
- Evidence: replay returns zero invocations and one pending item instead of rejecting the malformed persisted record; the independent probe prints `REPRO P1-02 malformed persisted terminal silently normalized to pending`.
- Risk: the strict persisted-record boundary is bypassed before schema validation. Corrupt or partially overwritten terminal files can disappear from accounting instead of failing closed, violating exact pair/multiplicity and terminal completeness.
- Suggested fix: treat every file matching the terminal naming contract as a record that must pass the strict schema; never filter malformed records before validation. A matching malformed file must raise and block replay.
- Validation gap: existing tamper tests mutate fields on an otherwise selected receipt; they do not remove the discriminator used by the pre-validation filter.
- Confidence: high.

### [P1-03] A process that never started is counted as an external CLI process

- Path: `scripts/agy_seo_copy_pipeline.py:2248`, `scripts/agy_seo_copy_pipeline.py:2281`
- Trigger: replay receives a valid `process_not_started`/`CLI_NOT_FOUND` terminal and failed gate.
- Evidence: `external_cli_process_invocations` and `reviewer_invocations` both become one; the independent probe prints `REPRO P1-03 process_not_started counted as an external CLI process`.
- Risk: the externally reported process count is not the number of actually started CLI processes. This overstates process usage and still conflates logical Reviewer attempts with launched external processes.
- Suggested fix: count `reviewer_invocations` and attempted identities separately; derive `external_cli_process_invocations` only from terminal states proving a process started (`process_succeeded`, `process_nonzero`, `process_timeout`).
- Validation gap: first/middle/last tests use a test-double exception represented as `process_not_started` but assert the logical call count as the external process count; no CLI-not-found zero-process test exists.
- Confidence: high.

### [P2-01] Target-local quote existence does not bind the finding claim to the target

- Path: `scripts/agy_seo_copy_pipeline.py:2025`, `scripts/agy_seo_copy_pipeline.py:2067`
- Trigger: item A receives `TEMPLATE_USAGE` with a B-only message stating that another article is duplicated, while `evidence_quote` is an unrelated generic A span such as `article-01`.
- Evidence: validation accepts the finding. The independent probe prints `REPRO P2-01 B-only claim accepted with unrelated target-local quote`; the Repair test itself also treats a B-only message plus an A quote as valid.
- Risk: the original cross-slot attribution route remains. Exact-span existence proves only that some A text was quoted, not that the code/message is supported by that span. `TEMPLATE_USAGE` is inherently comparative and cannot be established by a single target-local quote alone.
- Suggested fix: remove comparative/deterministic codes such as `TEMPLATE_USAGE` from the model allowlist and derive them from local deterministic cross-item gates, or provide a code-specific machine-verifiable predicate that binds all compared items. For quote-eligible codes, reject structural keys/slots and require a code-specific witness predicate.
- Validation gap: tests cover blank, B-only quote and swapped candidate SHA, but not an unrelated A quote attached to a B-only semantic claim.
- Confidence: high.

## Spec axis

`NO_GO`. The Repair closes the documented happy paths, adds exclusive writes for core CLI records, improves strict replay, derives top-level counters from accounting artifacts, and adds `evidence_quote`. However all four fixed axes retain a reproducible bypass or counting error, so the original findings cannot be marked closed.

## Standards axis

`NO_GO`. Repair allowlist, focused/full regression behavior, fresh corpus integrity, privacy scan, py_compile and diff checks are acceptable. The fail-closed trust boundary and audit accounting semantics remain incomplete.

## Testing gaps

- Retry authorization with a filename-matching but payload-mismatched gate.
- Malformed terminal missing the field used by the replay pre-filter.
- `CLI_NOT_FOUND/process_not_started` separation between logical attempts and actual external processes.
- B-only message with an unrelated but target-local structural/text quote.

## Residual risks

- File mtime is used as the terminal-before-gate ordering authority; mtime is mutable metadata and is not cryptographically bound into either record.
- The six-process corpus is internally consistent and replays successfully, but it exercises valid records only and cannot close the production bypasses above.
- Full suite retains only the two known Ziwei provider baseline failures; it is not claimed green.

## Decision

`NO_GO`: P1-01, P1-02, P1-03 and P2-01 each remain independently reproducible. Candidate code was not modified, repaired, merged, pushed, deployed or published.

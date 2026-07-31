# EV-CANARY-NEW-001

## Decision

```text
status: NO-GO
lane: new
run_id: auto-new-v1-20260731-121-01
candidate_id: null
publisher_decision: NOT_INVOKED
release_commit: null
release_tag: null
public_result: none
```

## Evidence

- The fresh canary was advanced by runtime `66009a301...`.
- Production attempt markers exist for all invoked jobs.
- Writer `33832680...`: succeeded.
- Reviewer `759c3a8d...`: succeeded and requested bounded repair.
- Writer repairs `cd97d78...` and `634121c9...`: succeeded.
- Final Reviewer `95c51ce1...`: failed with
  `GeminiApiFailure / API_RATE_LIMITED / QUOTA`.
- The run terminalized as `failed` at `2026-07-31T10:41:46+08:00`.
- The run directory contains only `brief.json`; no `candidate.json`,
  `review.json` or `approval.json` exists.

## Race receipt

The new-only coordinator created
`auto-new-v1-20260731-122-01` while the first run was advancing. Its initial
Writer job was claimed before bootout completed and terminated as
`SCHEMA_INVALID_PAYLOAD`. The repaired runtime subsequently produced the
bounded repair job `2c87aa21...`.

That replacement job remains unconsumed in
`<queue-root>/lanes/new/outbox/`; authorization to run a second new canary was
not granted. A hidden ignored atomic-write temporary file also remains beside
the outbox job. Neither file was removed or rewritten.

## Acceptance mapping

- real provider path: PASS
- closed schema／failure taxonomy: PASS
- fresh candidate: FAIL
- Publisher／release／public verification: NOT REACHED
- substitute fixture or idle signal used: no

## Next authorization

Running `2c87aa21...` would be a replacement canary after a terminal provider
failure and requires explicit new authorization. Services stay stopped until
that decision.

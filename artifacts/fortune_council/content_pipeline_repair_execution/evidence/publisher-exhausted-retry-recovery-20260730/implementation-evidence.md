# Publisher exhausted retry recovery — implementation evidence

Status: `LOCAL_CANDIDATE_PENDING_FINAL_GATE`

## Why this capability was required

The four approved create runs were preserved after rollback, but their retry
records had reached `attempts: 3`, `eligibility: exhausted`. The existing
Publisher had no supported operator command to recover that state. Direct JSON
editing is forbidden because it would bypass validation and audit evidence.

## Recovery contract

The new command:

- accepts explicit create run IDs, the exact expected prior error, and an
  operator reason;
- requires a read-only dry-run digest before any mutation;
- requires the complete deployed runtime contract for a real recovery;
- validates queue state, candidate schema, clean Reviewer approval, current
  quality policy, ledger, quarantine, policy rejection, exhausted retry state,
  and `FAILED_RECOVERED` evidence;
- binds the dry-run digest to retry bytes, failure evidence bytes, candidate
  content, expected error, and recovery reason;
- rechecks the bound inputs under the Publisher lock before mutation;
- resets only the selected retry budget and writes a run-scoped audit receipt.

It does not publish, push, tag, deploy, edit the ledger, or skip any release
gate.

## RED

Before implementation:

```text
AttributeError: module 'scripts.agy_content_publisher'
has no attribute 'recover_exhausted_create_retries'
```

## Current verification

- Recovery unit cases: `8 passed`
- Publisher module: `83 passed`
- Publisher + Web combined: `155 passed`
- Publisher release gate: `348 passed`
- Python compile: passed
- `git diff --check`: passed

Production-state dry-run selected exactly:

- `auto-new-v1-20260730-082-01`
- `auto-new-v1-20260730-085-01`
- `auto-new-v1-20260730-099-01`
- `auto-new-v1-20260730-104-01`

The dry-run returned `mutation_permitted: false`. No production retry, queue,
ledger, Git ref, deployment, or live content state was changed.

The final recovery digest must be captured again after the deployed candidate
is fixed to a final SHA; stale digests are rejected.

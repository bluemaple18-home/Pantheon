# Gemini V4 Limited Activation-004 Decision

- status:
  `BLOCKED`
- decision:
  `BLOCKED`
- external invocation count:
  `1`

## Passed

- Repair-3 candidate has independent `DELIVERED_CANDIDATE / GO`.
- Fresh run identity, namespace, job ID, request digest and repo-external runtime exist.
- Exactly one sanitized writer request passed strict rebuild, digest and public-data checks.
- Effective prompt passed role, no-tool, JSON-only, no-fence, canonical schema and exact-task
  validation.
- Effective prompt is 4028 bytes, below the 393216-byte ceiling.
- Executable digest matches the previously verified agy 1.1.5 runtime.
- Executed bytes matched the previously disclosed agy digest even though the mutable
  launcher target changed after dry-run.
- Durable ledger and anchor prove one process and complete replay.

## Actual result

- job:
  `a520fbf466d750acec225d77f129151affd4e04b`
- process count:
  `1`
- process outcome:
  `SUCCESS`
- replay status:
  `COMPLETE`
- result validation:
  `JSON_INVALID`
- inbox delivery:
  `absent`
- archive／failed record:
  `present / present`
- retry／fallback／pipeline continuation／publisher:
  `0 / 0 / 0 / 0`

## Decision rationale

The exactly-once transport path reached one external process and durable terminal
state, but the returned payload was not valid JSON. Because no caller-bound inbox
delivery exists, V4 is not ready for activation. No retry is permitted on this card.
The next repair must be separately scoped and reviewed; this card does not authorize
reading or persisting the raw response.

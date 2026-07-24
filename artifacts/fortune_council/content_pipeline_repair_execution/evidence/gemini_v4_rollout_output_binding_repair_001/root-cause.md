# Gemini V4 Output Binding Repair｜Root Cause

## Failure

Rollout evidence commit
`90559641a9460c26eb7c168ebbb78ce4be2a51fa` was correctly blocked with
`REAL_SHADOW_OUTPUT_BINDING_MISMATCH`.

The production canary returned schema-valid pretty JSON. Broker control recorded the
original stdout as 64 bytes with SHA-256
`020b8cee2c58e9e4e0e2655048e07752e70f905984b36f37304819c3c757a048`,
while `BrokerResult.result_json` exposed a re-encoded 54-byte compact JSON value.

## Ranked hypotheses

1. **Production caller boundary discards byte identity — confirmed.**
   `run_single_shot` verifies `raw_result` against control byte count and digest, parses
   and validates it, then returns `canonical_json(parsed)` instead of the verified
   `raw_result`.
2. **Verifier rejects a valid binding — falsified.**
   Without the original bytes, a fresh verifier cannot prove that the recorded stdout
   digest represents the same closed-schema result. Rejecting the bundle is the correct
   fail-closed outcome.
3. **The external result is malformed or violates the schema — falsified.**
   The broker set `caller_contract_satisfied=true`, parsed the result, and the closed
   schema check passed.

## Architectural seam

`BrokerResult.result_json` is the correct seam. It is already an in-memory bytes field
whose `.result` property parses JSON for the runner. Preserving the broker-verified raw
JSON bytes restores digest binding without changing the runner inbox shape, ledger,
anchor, retry, fallback, or publishing behavior.

## Minimal fix

For schema-valid success only, return `raw_result` as `result_json`. Invalid or malformed
output still returns `None`. No verifier rule is weakened and no external canary is
executed by this repair.

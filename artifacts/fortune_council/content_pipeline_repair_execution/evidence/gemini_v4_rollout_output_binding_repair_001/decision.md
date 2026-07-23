# Gemini V4 Output Binding Repair｜Decision

## Delivery

`DELIVERED_CANDIDATE / READY_FOR_REVIEW`

## Evidence

- Root cause localized to `run_single_shot` caller boundary.
- Deterministic RED reproduced loss of pretty-JSON byte identity.
- Minimal one-expression production fix preserves verified raw stdout bytes.
- Parsed `.result` and runner-facing JSON object behavior are unchanged.
- V4, legacy publishing, and coordinator regressions: `137 passed`.
- No external canary, retry, fallback, push, deploy, publish, or default promotion.

## Review boundary

This repair is not integrated and does not make rollout ready. An independent Reviewer
must confirm:

1. preserving raw schema-valid JSON bytes in `BrokerResult.result_json` is the correct
   trust boundary;
2. malformed/schema-invalid outputs still fail closed;
3. normalized traces and runner inbox do not persist formatting or unvalidated output;
4. the changed-file allowlist and regression evidence are complete.

Only after Review GO may the mainline prepare a new rollout evidence chain. Any future
real canary requires a separate final external-call confirmation.

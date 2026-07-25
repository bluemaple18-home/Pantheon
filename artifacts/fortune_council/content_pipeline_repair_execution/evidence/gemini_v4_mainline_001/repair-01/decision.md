# Repair-1 decision

Status: `REPAIR_READY_FOR_REVIEW`

Generation: `Repair-1`

Reviewer: `019f9548-1dba-7781-9890-5dd54f669419`

## Facts

- F001–F005 each have an actually executed symptom-specific RED and focused
  GREEN.
- Required affected suite result is `192 passed`.
- Flag-off legacy behavior is unchanged.
- New flag-on operations select only `gemini_structured_api_v1`; explicit
  legacy is replay-only.
- Provider schema projection and complete local caller validation are separate.
- Durable structured replay does not open credential or fork a target.
- New structured operations still fail closed before ledger creation when no
  valid credential FD is available.
- No forbidden-scope path changed.
- No external generation, retry, fallback, integration, deployment, publish,
  activation or default promotion occurred.

## Remaining risks

- Gemini schema-complexity and model/runtime acceptance remain unverified
  without a separately authorized real canary.
- Network ambiguity and provider-internal call provenance remain unchanged.
- This executor has not performed independent Review and does not claim `GO`.

## Handoff

Create one Repair-1 candidate commit and return it to the same Reviewer thread
for re-review. Do not replace the Reviewer or reset the finding ledger.

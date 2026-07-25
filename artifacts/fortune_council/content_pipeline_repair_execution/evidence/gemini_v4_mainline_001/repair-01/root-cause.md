# Repair-1 root cause

Status: `REPAIR_READY_FOR_REVIEW`

## Identity and startup gate

- implementation base: `d5e19971614669665a7fbe0710fab7fcb1a0b883`
- parent code candidate: `748c10f13e597ad74b16ecf2914fc388ed0f07de`
- review provisioning: `b600df18868e4af75a823d17daaa387f58c64b2c`
- repair provisioning / starting HEAD:
  `c01cfba1650a7cd6d666deb6b715d3d435694972`
- ancestry is an exact single-parent chain:
  base → candidate → review provisioning → repair provisioning
- worktree was independent, detached and clean; `index.lock` was absent.
- CodeGraph was not initialized in this worktree. Per card fallback, source
  localization used narrow `rg` / `sed` and production source.
- Reviewer thread `019f9548-1dba-7781-9890-5dd54f669419` final verdict and all
  F001–F005 identities matched the physical card.

## Ranked hypotheses and results

1. F001 was a migration-default mismatch. Confirmed: the runner defaulted new
   flag-on work to `antigravity_cli_v1`.
2. F002 was a missing provider projection. Confirmed: the full caller schema,
   including unsupported string length keywords, was copied into
   `responseJsonSchema`.
3. F003 and F005 were local validator coverage and traversal-order defects.
   Confirmed: numeric bounds were not evaluated, and oversized valid arrays
   traversed every item after `maxItems` had already failed.
4. F004 was credential acquisition before durable replay judgment. Confirmed
   in both runner and broker seams.

## Minimal repairs

- New flag-on operations default to `gemini_structured_api_v1`.
  `antigravity_cli_v1` is accepted by the production runner only when the
  operation ledger already exists; flag-off legacy is unchanged.
- Provider schema projection v1 deterministically removes unsupported
  `minLength` / `maxLength` from the provider payload. The canonical target
  request still contains the complete caller schema, which the broker uses for
  independent local validation.
- Broker validation enforces inclusive `minimum` / `maximum` for number and
  integer values. Boolean values remain rejected by the numeric type gate.
- Oversized arrays return immediately after the bounded `maxItems` diagnostic;
  child traversal is zero.
- Structured credential access is lazy. Existing ledger replay does not open a
  credential or start a target. A new operation still requires a valid
  credential FD before ledger creation.

No retry, fallback, real provider request, credential mutation, publish,
activation or default promotion was performed.

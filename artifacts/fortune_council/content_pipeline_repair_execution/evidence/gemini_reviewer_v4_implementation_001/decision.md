# Gemini Reviewer V4 implementation｜Decision

Status: `READY_FOR_REVIEW`

## Evidence-based decision

- RED-first evidence exists and the final focused suite is green.
- Real synthetic subprocess tests cover process accounting, exec confirmation, timeout reap, FD privacy, replay legal table, negative schema/FSM controls, external anchor mismatch and replay-only idempotence.
- Runner canary is bounded to the original `process_once` callsite and exact flag value `1`.
- Every fail-closed result avoids inbox and legacy fallback.
- All changes are inside the card allowlist.

## Limitation

The full suite has two pre-existing Ziwei provider failures, independently reproduced from the unmodified starting commit. All other tests pass. This candidate does not claim `GO`; it must be reviewed independently before any real CLI canary or content-line recovery.

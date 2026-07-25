# Repair-2 finding matrix

| Finding | RED evidence | Production repair | GREEN evidence | Remaining risk |
|---|---|---|---|---|
| F002 P1 | Seven invalid typed schemas reached the synthetic HTTP seam | Per-type closed provider subset; typed enum; closed string format; finite numeric values and bounds; exact integer contract | 14 focused cases and 78 tests across the two affected suites passed; current article schemas still project | Provider may still reject undocumented schema complexity; no real API call was authorized |
| F003 P2 | 22 probes accepted or serialized NaN / Infinity / -Infinity | Strict parse_constant boundaries, allow_nan=False serializers and explicit finite numeric validation | 24 focused cases and 99 tests across the two affected suites passed | Strict rejection is local evidence only; provider network ambiguity remains unchanged |

Preserved Reviewer findings:

- F001: no runner change; structured-only new-operation routing regressions remain green.
- F004: no credential or replay change; credential-free durable replay regressions remain green.
- F005: maxItems early-return regression remains green.

Overall implementation status: `REPAIR_READY_FOR_REVIEW`

This is executor evidence only. It is not an independent Review verdict and does not
authorize a real canary.

# Repair-1 finding matrix

| Finding | RED evidence | Production repair | GREEN evidence | Remaining risk |
|---|---|---|---|---|
| F001 P1 | Default flag-on selected legacy; explicit legacy new job reached broker | Structured is the new-operation default; legacy profile is runner replay-only | 5 focused tests passed, including flag-off and existing legacy replay | Existing legacy replay remains dependent on its historical executable and request identity |
| F002 P1 | Full caller schema was copied into provider payload | Deterministic provider projection v1 removes unsupported string length keywords; target request retains the complete caller schema | 18 target / production-schema tests passed | Provider may still reject schemas for undocumented complexity limits; no real API call was authorized |
| F003 P2 | Four out-of-range number / integer cases were accepted | Local validator enforces inclusive minimum / maximum; bool is not numeric | 6 focused cases passed | Validator remains an intentionally bounded subset, not a general JSON Schema implementation |
| F004 P2 | Existing structured replay failed without credential in both runner and broker seams | Credential opener is lazy and owned by broker only for new operations | 3 focused cases passed; replay target trace absent; new operation without credential creates no ledger | A concurrent-create loser can still acquire credential after an initial no-ledger observation; it does not fork or resend |
| F005 P3 | Oversized valid fixture traversed 100000 children | Return immediately after maxItems diagnostic | 1 focused regression passed with 0 child iterations | Legal arrays still traverse their items as required |

Overall status: `REPAIR_READY_FOR_REVIEW`

This matrix is implementation evidence only. It is not a self-review verdict and
does not authorize a real canary.

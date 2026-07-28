# Implementation summary

status: `DELIVERED_CANDIDATE / READY_FOR_REVIEW`

## Durable provider admission

- The existing allocator state remains the single shared cross-process authority.
- State schema v1 is accepted for migration; every subsequent commit writes closed v2.
- v2 adds only `last_slot_id` and bounded anonymous cooldown records. Each record has
  `slot_id`, millisecond window and fixed `API_RATE_LIMITED` reason.
- Existing directory lock, lock-file identity, owner-only mode, atomic temp write,
  `fsync` and `os.replace` controls remain in force.
- Admission holds the allocator critical section across eligibility, queue claim,
  request validation and ordinal commit. All-slots-cooling returns before `_claim_next`.
- Ordinal commit occurs after selected credential validation and immediately before the
  single provider attempt. A denied admission has no ordinal.
- Only a sanitized closed `API_RATE_LIMITED` result writes cooldown. Timeout, transport,
  redirect, 5xx and success do not.

## Scheduling and canary

- New-matrix sweep requests and registers at most one path with one article per cycle.
- Queue claim validates role for ordering and prefers reviewer over fresh writer while
  keeping opaque filename order as the deterministic tie-breaker.
- `AGY_GEMINI_NEW_ONLY=1` makes coordinator advance one new state only, skips legacy
  rewrite seeding and shared runner consumption, and makes non-new lane runners return
  before claim. `0` preserves the four-lane behavior.
- The installer validates `AGY_GEMINI_NEW_ONLY=0|1` and a cooldown between 1 and 3600
  seconds before plist/control-plane mutation. Templates default to new-only off and a
  300-second cooldown.

## Boundaries

- No production queue, credential value/path, provider, launchd state, deployment,
  canary, publish, push, PR or merge was touched.
- No queue payload schema, Publisher, V4 lifecycle, article, registry, sitemap, feed,
  dependency or lockfile changed.
- This candidate reduces calls and failure churn after observed 429 responses. It does
  not and cannot raise provider RPD/TPM limits.

## Remaining risks

- An independent strict Review is still required; this implementation is not accepted
  or integrated.
- Fixed cooldown is an operational backoff, not a quota reset prediction.
- Concurrent attempts already admitted before the first 429 can finish independently;
  cooldown governs subsequent admissions after the closed signal is durable.
- Pristine source SHA has two existing multilingual apply fixture failures caused by
  `missing_policy_contract`; this candidate does not modify that boundary.

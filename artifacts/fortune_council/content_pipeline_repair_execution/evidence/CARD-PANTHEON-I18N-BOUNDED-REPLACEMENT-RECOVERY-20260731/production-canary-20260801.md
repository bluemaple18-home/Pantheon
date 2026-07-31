# Bounded i18n replacement production canary｜2026-08-01

## Decision

```text
status: NO_GO_PROVIDER_UNAVAILABLE
repair_deployed: true
production_output_count: 0
i18n_new_release: none
i18n_rewrite_release: none
production_canary_hold: true
services: stopped
verified_at: 2026-08-01T00:59:04+08:00
```

本次不能宣稱 canary 完成。修復已推送並部署，但兩條指定 i18n canary 都在
locale-plan provider 階段收到同一 closed failure；沒有 candidate、Publisher
release、tag 或公開文章。

## External tool gate receipt

```text
tool/service: git + GitHub origin/main; local production LaunchAgents; configured Gemini provider
operation_level: write_action
connection_status: git dry-run and pre-push hook passed
schema_checked: repository hook, Publisher deployment preflight, exact lane/run identity
confirmation_required: received from repository owner
execution_status: push/deploy complete; canary blocked by provider
remaining_risk: provider availability; i18n-rewrite has one consumed attempt
```

GitHub write payload was exactly one fast-forward commit affecting two runtime modules and
two corresponding test modules. No article source or generated page was included in that
push.

## Push and runtime alignment

- production base before repair: `2066de2c2` (`v0.3.221`)
- repair commit / final `origin/main`: `7002e135f`
- `git push --dry-run origin HEAD:main`: release-record pre-push gate PASS
- `git push origin HEAD:main`: `2066de2c2..7002e135f`
- remote reconciliation: `refs/heads/main = 7002e135f`
- production actor: detached clean HEAD at `7002e135f`
- Publisher installed expected SHA: `7002e135f`
- Publisher installed expected runtime digest:
  `b1c8c99955a7827969feb2f73275f94d316f5626af6a6b927cc6ffdf4e40cfe3`
- official Publisher deployment preflight:
  `status=ready`, actor/queue/state matched, push mode `push`

The six related LaunchAgents were stopped before synchronization and remain unloaded:
Publisher, coordinator, new, rewrite, i18n-new, and i18n-rewrite.

## Pre-deploy gates

- affected suites on v0.3.221 base: `228 passed in 13.04s`
- repository-wide suite on v0.3.221 base: exit `0`
- `git diff --check origin/main..HEAD`: PASS
- push dry-run and actual pre-push hook: PASS
- production actor worktree: clean

## Replacement selection

### i18n-new

- base: `auto-i18n-en-7f3f7bd066897cf385ac`
- replacement:
  `auto-i18n-en-7f3f7bd066897cf385ac-replacement-01`
- article: `V2-MBTI-PAIR-INTP-ESFJ-WORK:en`
- replacement reason: `LOCALE_PLAN_VALIDATION`
- source SHA: matched current source

### i18n-rewrite

The first two ASTRO-LOVE-01 terminal runs were rejected before replacement because their
saved source SHA no longer matched the rewritten source. Separate decision receipts record
`SOURCE_DRIFT`; neither original state nor brief was overwritten.

- skipped bases:
  - `auto-i18n-ja-5c2c32a5a837cd9759d4`
  - `auto-i18n-ko-a58ee1fcfd1fe3a5ffe6`
- selected base: `auto-i18n-en-3a6f3c0fe37028056913`
- replacement:
  `auto-i18n-en-3a6f3c0fe37028056913-replacement-01`
- article: `THEME-LIFE-01:en`
- replacement reason: `LOCALE_PLAN_VALIDATION`
- source SHA: matched current source

This proves the new source-identity and bounded-selection behavior executed against the real
production queue. No replacement-02 was created.

## Provider outcomes

### i18n-new

The same logical locale-plan request used the existing three-attempt transport budget:

| Attempt | Job ID | Credential slot | Closed result |
|---|---|---|---|
| 1/3 | `a74a42607303a51215a4b22b325697e72adc65ba` | `account-1` | `PROVIDER_UNAVAILABLE / API_HTTP_ERROR` |
| 2/3 | `abead906e9a27b1655c8962333fb6999456ecc25` | `account-2` | `PROVIDER_UNAVAILABLE / API_HTTP_ERROR` |
| 3/3 | `f16acb60a3f366a6e9ed0e2060c600f0508d6d0a` | `account-3` | `PROVIDER_UNAVAILABLE / API_HTTP_ERROR` |

Final canonical run state:

```text
status=failed
error_type=GeminiApiFailure
error_code=API_HTTP_ERROR
failure_category=PROVIDER_UNAVAILABLE
transport_attempts=3
```

The run stopped at the configured limit. There was no fourth attempt and no replacement-02.

### i18n-rewrite

The first locale-plan attempt also returned:

```text
job_id=702cd806201b72308ad1878e5e1d29d8402128e5
credential_slot=account-1
failure_category=PROVIDER_UNAVAILABLE
error_code=API_HTTP_ERROR
```

Because this matched the cross-account failure already seen on i18n-new, further external
calls were stopped. The run remains active with the failed receipt available for the normal
bounded attempt 2/3 when operations are explicitly resumed. Its lane has no outbox or
processing file, so no background call can occur while services remain unloaded.

## Capacity and evidence boundary

- filesystem available: `30 GiB`, usage `84%`
- Gemini queue root: `131 MiB`
- Publisher state root after failed pre-existing transaction cleanup: `51 MiB`
- temporary isolated-worktree venv used by the pre-push hook: `76 KiB`

The Publisher process that was already active before deployment ended with one real release
test failure (`371 passed, 1 failed`) and safely rolled back. It was not counted as production
output. The transaction directory was cleaned before deployment freeze.

No queue, ledger, archive, receipt, candidate, release evidence or prior production output
was deleted.

## Acceptance mapping

- repair commit pushed and actor aligned: PASS
- bounded replacement created on both i18n lanes: PASS
- source drift fail-closed and decision persisted: PASS
- retry ceiling and closed provider metadata: PASS
- real `i18n-new` published output: FAIL — provider unavailable before candidate
- real `i18n-rewrite` published output: FAIL — provider unavailable before candidate
- fixture, idle or service-green substituted for release: NO

The next allowed action is not code repair or gate relaxation. It is a later controlled
provider recheck. Until then, services must remain stopped and `production_canary_hold`
must remain true.

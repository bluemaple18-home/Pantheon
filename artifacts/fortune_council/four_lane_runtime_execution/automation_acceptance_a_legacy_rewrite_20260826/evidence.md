# Evidence: Automation Acceptance A Legacy Rewrite

status: `DELIVERED_CANDIDATE`
recorded_at_utc: `2026-08-26T12:15:46Z`

## Scope

- dispatch_key: `v2:a-legacy-rewrite-e5c0743f-20260826`
- activation_token: `act-v2:a-legacy-rewrite-e5c0743f-20260826`
- source_sha: `823ca8712e57ff4387dd2c447daf6fe329e6db9d`
- formal_thread_id: `01a03c25-41fd-7342-88f0-3b2aa1eeb56c`
- projectId: `local-0020d4379451d545eb08362962f1def0`
- old blocked candidate preserved: `943a2ab15df01986c34d25b9ccb20854ad430578`

## Preflight Evidence

- worktree clean before mutation gates and before result write.
- detached HEAD: `823ca8712e57ff4387dd2c447daf6fe329e6db9d`
- CodeGraph: `READY`, files `583`, nodes `7034`, edges `15792`, backend `native better-sqlite3`。
- Runtime manifest matched actor `e5c0743fe1e0c99a66f2c0e3355591f2a353a322` and generation `g48-e5c0743f-gsc-json-shape-20260826`。
- Rule 24 capacity preflight returned `PASS` after reading runtime telemetry with manifest-bound environment.
- Rule 25 readiness gate returned `READY` for `exec-apf-004-readiness`。
- Deployment preflight returned `status=ready`, `operation=deployment-preflight`, `mode=read-only`, `dry_run=true`, `mutation_permitted=false`, `push_mode=push`。
- Seven services checked via `launchctl print gui/501/<label>`: all returned code `113`, treated as stopped/unloaded.

## Selector Evidence

Official selector dry-run:

- ready_count: `1`
- run_id: `legacy-auto-sweep-v1-astrology-0002-astro-base-02`
- article_id: `ASTRO-BASE-02`
- mode: `rewrite_existing_body`
- status: `complete`
- review_clean_approve: `true`
- findings_count: `0`
- candidate_body_hash: `8f242bfd8838b7c2aa7eb24f0352bda32e2f0d43b8f08f0f7cd69b4f67d26c40`
- correlation_id: `ea7f99a12ce1b3d3bd9f5f11ab9aab12`
- identity_digest: `e2527737e984c94c04ac11ca3b413acb548898b89c22b249785339fd956e4e09`
- canonical: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`

Pre-public baseline:

- prerender HTML sha256: `560556a22b5ae9c12f630488a97aadb8756a81f91a3b45812faf67389cc7ee4b`
- canonical occurrences: `5`
- registry record_count: `131`
- registry `ASTRO-BASE-02` occurrences: `2`
- registry `astrology-0002` occurrences: `1`
- ledger target run occurrences before publish: `0`
- state transaction dirs before publish: `0`

## Publication Evidence

Official exact-run publication completed once:

- status: `PUBLISHED_REWRITE`
- base_sha: `823ca8712e57ff4387dd2c447daf6fe329e6db9d`
- commit_sha: `47d7b804f4dbda6491f48141535fc869000421aa`
- version: `0.3.372`
- run_ids: `["legacy-auto-sweep-v1-astrology-0002-astro-base-02"]`
- article_ids: `["ASTRO-BASE-02"]`
- pushed: `true`
- policy_version: `pantheon-article-publication-v2.0.0`
- validator_result: `PASS`
- failure_codes: `[]`
- focused tests: `3 passed, 2 warnings`
- full release gate: `427 passed, 2 warnings`
- release gate JSON: `{"version":"0.3.372","article_release":true,"status":"PASS"}`

Remote refs:

- `refs/heads/main` -> `47d7b804f4dbda6491f48141535fc869000421aa`
- `refs/tags/v0.3.372` annotated tag object -> `ff207a7d807e7c71dd2122ab58531ab8817ebce3`
- `refs/tags/v0.3.372^{}` -> `47d7b804f4dbda6491f48141535fc869000421aa`

## Public Evidence

HTTP read of canonical URL:

- status line: `HTTP/2 200`
- bytes: `23980`
- sha256: `a004cdf5f580efb1548367dad962a2fb235dd42336d2b916a1bd162f2bc6f312`
- canonical URL occurrences: `5`
- new body phrases all present:
  - `上升星座是什麼，常用來看外在呈現與第一印象`
  - `上升星座不是外貌或性格的單一答案`
  - `上升星座不能替你判斷合不合`
  - `如何觀察自己的上升星座運作`
  - `回歸現實相處的真實體驗`

Browser-visible read:

- browser URL: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- canonical link: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- H1: `上升星座是什麼？它和太陽星座差在哪`
- body chars: `2342`
- all five new body phrases present
- console warning/error logs: `[]`
- screenshot artifact: `/private/tmp/pantheon-automation-acceptance-a-browser.png`

## Post-Publication Accounting

- actor worktree HEAD remained `e5c0743fe1e0c99a66f2c0e3355591f2a353a322`; `origin/main` moved to candidate `47d7b804f4dbda6491f48141535fc869000421aa` via official flow.
- actor worktree status: clean.
- transaction directories after publication: `0`
- ledger sha256: `0fc223530e1f8af7d0b495e28e4a336471a2349ceabd93074459827cbe93d8f9`
- ledger exact run_id occurrences: `1`
- ledger exact article_id occurrences: `1`
- ledger entry:
  - section: `rewrite_released_runs`
  - run_id: `legacy-auto-sweep-v1-astrology-0002-astro-base-02`
  - article_ids: `["ASTRO-BASE-02"]`
  - commit_sha: `47d7b804f4dbda6491f48141535fc869000421aa`
  - published_at: `2026-08-26T20:08:36+08:00`
  - version: `0.3.372`
  - translation_seed_status: `seeded`
- target run absent from `published_runs`、`translation_published_runs`、`translation_deferred_runs`、`quarantined_runs`、`superseded_runs`。
- commit HTML sha256: `028a9c276e036398cafce8a5349fc6ae7497329ea69192ae8f9be8a767d80e37`
- commit HTML canonical occurrences: `5`
- registry `ASTRO-BASE-02` occurrences: `2`
- registry `astrology-0002` occurrences: `1`
- sitemap canonical occurrences: `1`
- rewrite file sha256: `5c3e0ed9b6b27441fd4c5b7ec516ac1606226f2adc0d4e811090b4c4f3662525`
- rewrite file `ASTRO-BASE-02` occurrences: `1`
- rewrite file canonical occurrences: `1`

## Final Safety

- 七服務終態仍 stopped/unloaded。
- 沒有建立 replacement thread、B/C/第四卡、Reviewer 或 Repair。
- 沒有 source edit。
- 沒有手動 tag/push/deploy；遠端 refs 的變化來自官方 publication flow。

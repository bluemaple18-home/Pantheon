# Pantheon 舊文原網址自動化驗收 Result

status: `DELIVERED_CANDIDATE`
card_id: `CARD-PANTHEON-AUTOMATION-ACCEPTANCE-A-LEGACY-REWRITE-20260826`
dispatch_key: `v2:a-legacy-rewrite-e5c0743f-20260826`
activation_token: `act-v2:a-legacy-rewrite-e5c0743f-20260826`
recorded_at_utc: `2026-08-26T12:15:46Z`

## 結論

本卡已依正式 activation 執行一次既有官方 exact-run 單篇 legacy rewrite publish flow，並交付候選 publication commit：

`47d7b804f4dbda6491f48141535fc869000421aa`

主線仍保留最終 GO 判定；本結果只標記 `DELIVERED_CANDIDATE`。

## Dispatch

- formal_thread_id: `01a03c25-41fd-7342-88f0-3b2aa1eeb56c`
- projectId: `local-0020d4379451d545eb08362962f1def0`
- cwd/worktree: `/Users/mattkuo/.codex/worktrees/da94/Pantheon`
- source_sha / detached HEAD: `823ca8712e57ff4387dd2c447daf6fe329e6db9d`
- pre-result clean state: clean
- old candidate preserved: `943a2ab15df01986c34d25b9ccb20854ad430578` is still traceable as a commit.

## Pre-Mutation Gates

- 實體卡已完整重讀。
- Rule 21 shared-resource digest 已依派工資料核對：`sha256:def530bb99caf5f40973305af0066378b92cede21ef5845714ac55b9814c7dd0`。
- CodeGraph readiness: `READY`，`583` files、`7034` nodes、`15792` edges。
- Runtime actor: `e5c0743fe1e0c99a66f2c0e3355591f2a353a322`。
- Runtime generation: `g48-e5c0743f-gsc-json-shape-20260826`。
- Runtime manifest digest: `9344898970dfa335dc5e238d3c7acc2baf634de52fc60206b441292f66261f2f`。
- Promotion transaction `v0404-gsc-json-shape-e5c0743f-20260826`: `COMMITTED`。
- Rule 24 capacity preflight: `PASS`。
- Rule 25 official readiness gate: `READY`，capabilities covered `create/run/select/publish/transaction/tag/push`，且 fail-closed fixture `BLOCKED`。
- Deployment preflight: `ready`、`mutation_permitted=false`、actor/queue/state matched。
- 七個 Pantheon launchd services mutation 前皆為 stopped/unloaded。

## Selector Lock

- selected run_id: `legacy-auto-sweep-v1-astrology-0002-astro-base-02`
- article_id: `ASTRO-BASE-02`
- mode: `rewrite_existing_body`
- canonical: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- reviewer gate: clean approve, findings count `0`
- candidate_body_hash: `8f242bfd8838b7c2aa7eb24f0352bda32e2f0d43b8f08f0f7cd69b4f67d26c40`
- correlation_id: `ea7f99a12ce1b3d3bd9f5f11ab9aab12`
- identity_digest: `e2527737e984c94c04ac11ca3b413acb548898b89c22b249785339fd956e4e09`
- dry-run selector result: exactly one ready run, article_ids exactly `["ASTRO-BASE-02"]`。

## Publication Runtime

- Official exact-run invocation count: `1`
- publication status: `PUBLISHED_REWRITE`
- base_sha: `823ca8712e57ff4387dd2c447daf6fe329e6db9d`
- commit_sha: `47d7b804f4dbda6491f48141535fc869000421aa`
- tag: `v0.3.372`
- version: `0.3.372`
- pushed: `true`
- validator_result: `PASS`
- failure_codes: `[]`
- release gate: `PASS`
- focused tests: `3 passed`
- full gate: `427 passed`
- external mutation accounting: only the authorized official publish flow performed production/remote writes; no second transaction, no manual tag/push/deploy, no replacement thread.

官方流程同時 seed 了同一篇文章的 pending translations：
`auto-i18n-en-76c60592a8db463a2225`、`auto-i18n-ja-841277b5d0a4dd537c8c`、`auto-i18n-ko-bf4f876f59cd9c7c2547`。ledger 顯示它們只掛在同一個 rewrite release entry，沒有 published translation。

## Public Verification

- HTTP URL: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- HTTP status: `HTTP/2 200`
- downloaded bytes: `23980`
- downloaded sha256: `a004cdf5f580efb1548367dad962a2fb235dd42336d2b916a1bd162f2bc6f312`
- canonical occurrences in downloaded HTML: `5`
- browser URL: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- browser canonical: `https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- browser body chars: `2342`
- browser console warnings/errors: `0`
- browser screenshot: `/private/tmp/pantheon-automation-acceptance-a-browser.png`

公開 HTTP 與 browser-visible body 皆包含新版正文關鍵語句：

- `上升星座是什麼，常用來看外在呈現與第一印象`
- `上升星座不是外貌或性格的單一答案`
- `上升星座不能替你判斷合不合`
- `如何觀察自己的上升星座運作`
- `回歸現實相處的真實體驗`

## Uniqueness / Accounting

- remote `refs/heads/main`: `47d7b804f4dbda6491f48141535fc869000421aa`
- remote annotated tag `refs/tags/v0.3.372^{}`: `47d7b804f4dbda6491f48141535fc869000421aa`
- state transaction directories after publication: `0`
- ledger target run occurrences: `1`
- ledger target article occurrences: `1`
- ledger entry: `rewrite_released_runs` only; `published_runs`、`translation_published_runs`、`translation_deferred_runs`、`quarantined_runs`、`superseded_runs` have no target run match.
- commit HTML canonical occurrences: `5`
- sitemap canonical occurrences: `1`
- registry slug occurrences: `1`
- rewrite file article_id occurrences: `1`
- rewrite file canonical occurrences: `1`

## Terminal State

- 七個 Pantheon launchd service labels 終態仍為 stopped/unloaded。
- runtime actor worktree clean。
- 本 worktree 在寫入 allowlist result/evidence 前 clean；本次提交只應包含本 RESULT 與本卡 evidence 目錄。
- 沒有建立 B/C/第四卡、Reviewer、Repair 或 replacement thread。

## Evidence

- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_a_legacy_rewrite_20260826/evidence.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_a_legacy_rewrite_20260826/machine-summary.json`

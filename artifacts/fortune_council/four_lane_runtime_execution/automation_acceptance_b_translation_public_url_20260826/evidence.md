# Evidence：Pantheon 翻譯公開網址自動化驗收 B

## Dispatch

- formal thread ID：`01a03c34-fd96-7021-9423-29879c9b5b47`
- dispatch_key：`v1:9bef6288f7b2b5684fc4563765b80db2ef33b3bf992dd2261ba8544f6a6f3c5c`
- activation_token：`act-v1:8e9e60c28a44e0b5fe1813b7b3c83438d6fb4ca066b8832c37d4e8532f3786d3`
- cwd：`/Users/mattkuo/.codex/worktrees/2cf0/Pantheon`
- source SHA / HEAD：`36c0966a68bc647a2354678a085cf412bc9b705a`
- worktree：detached/獨立 worktree；activation 前後 clean

## Card And Rule

- 實體卡：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826.md`
- Rule 21 digest：`def530bb99caf5f40973305af0066378b92cede21ef5845714ac55b9814c7dd0`
- digest matches dispatch：yes

## CodeGraph

`codegraph_status`：

- files indexed：`583`
- total nodes：`7034`
- total edges：`15792`
- database size：`18.36 MB`

第一次 source decision 前的 task-semantic CodeGraph query：

- `codegraph_files(pattern="*translation*")`：no files found
- `codegraph_files(format="flat", maxDepth=3)`：index 可用但結果過寬，顯示 publisher/runtime files 需降級定位
- degraded reason：CodeGraph readiness PASS，但 translation filename query 無命中，file index 無法精準定位 formal translation/publisher path；後續限域 `rg` 僅用於 `scripts/agy_content_publisher.py`、runtime manifest、handoff 與本卡相關 artifact。

定位到的正式入口：

- `scripts.agy_content_publisher:publish_ready_translation_runs`
- `scripts.agy_content_publisher:collect_ready_translation_runs`
- `scripts.agy_content_publisher:deployment_preflight`
- CLI：`python -m scripts.agy_content_publisher`

## Runtime Manifest

`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`：

- actor_head：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- generation：`g47-6477ab81-activation-only-20260826`
- identity：`gate2-actor:6477ab815e8aecca7d1e8e1588e6e5eba0fab001:activation-only`
- manifest_digest：`c2cd3cc7b63d7685f355a4426854b7f3d2c88b4e26b8e51468afdc7c49eadc53`
- runtime_digest：`a4dfa5e25f2e6b0f291fdf8e5e9163b70b243ea3836a1d47631e02697d1ee063`
- runtime_identity_digest：`9cfeb7d9d3b30b5759b547fca1f003d4f5a7cc1fef42297601a86b2eaa5800ce`
- actor_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor`
- queue_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue`
- publisher_state_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state`
- activation barrier：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/four-lane-activation-g47-6477ab81-activation-only-20260826.barrier`

## Service State

`launchctl list | rg 'com\.pantheon\.'` returned no rows before terminal write.

Interpretation：七個 Pantheon launchd labels are STOPPED / not loaded:

- `com.pantheon.agy-content-publisher`
- `com.pantheon.agy-gemini-coordinator`
- `com.pantheon.agy-gemini-new`
- `com.pantheon.agy-gemini-rewrite`
- `com.pantheon.agy-gemini-i18n-new`
- `com.pantheon.agy-gemini-i18n-rewrite`
- `com.pantheon.content-capacity-guard`

## Readiness And Capacity

卡 B 沿用已存在的 production-canary readiness/capacity receipts；本卡沒有重新做 capacity exercise。

- capability receipt：`artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/fresh-67f62f/rule25-readiness/capability/positive-receipt.json`
  - steps：`create`, `run`, `select`, `publish`, `transaction`, `tag`, `push`
  - every step has positive `PASS` and negative `BLOCKED` evidence
- capacity receipt：`artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/fresh-67f62f/rule25-readiness/capacity/capacity-receipt.json`
  - status：`PASS`
  - production_mutation：`false`
  - stop_loss_negative_result：`BLOCKED`

## Translation Candidate Baseline

Official exact run selected for the single-locale path:

- run_id：`auto-i18n-en-614aa4dc3542ab2c5637`
- mode：`translate_existing`
- source_article_id：`ASTRO-BASE-01`
- source path：`/articles/astrology/astrology-0001`
- target locale：`en`
- translation article_id：`ASTRO-BASE-01:en`
- source_sha256：`a375e9c17d2857881f23ebd8d2c9581caf698a59e6121e314b11892a4f464bb7`
- reviewer verdict：`APPROVE`
- reviewer findings：`[]`
- retry record：`attempts=1`, `max_attempts=3`, `candidate_preserved=true`, previous error was release test failure

Baseline hashes after blocked dry-run:

- ledger：`224d78887b4a1062702e3b920377eda8ff2abb8264b1ec48861254afe6fddabe`
- retry record：`2c50f1a7a9142bc4bedf7d7b8ea6c1217464eea7613b37b4771246217cf06602`
- brief：`9ad7ff12a79d706d90afd6ab6ff1d1858fd1116a793007b8dc3135ff18e2bac9`
- candidate：`96a84fdb310d0c07fc906e28dbcdfdb6f0bf7fe1dd7328774f4295aafe1d7912`
- review：`511a526fb26a98c96238fc011ac1241a8372db587c7c1b959740ed10510511df`

Existing translation evidence directories:

- `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/evidence/translation-0.3.369`
- `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/evidence/translation-0.3.370`（既有空目錄，mtime `Aug 21 11:59:20 2026`）

## Official Entrypoint Results

Remote confirmation with network enabled:

```text
0257bd5213eed0d0df10661a54f6215901a54997	refs/heads/main
```

Actor confirmation:

```text
6477ab815e8aecca7d1e8e1588e6e5eba0fab001
```

Actor local `origin/main` after fetch:

```text
0257bd5213eed0d0df10661a54f6215901a54997
```

Deployment preflight command used the official module entry with manifest authority, exact run and push mode:

```text
python3.12 -m scripts.agy_content_publisher --repo-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue --state-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state --max-runs 1 --exact-run-id auto-i18n-en-614aa4dc3542ab2c5637 --dry-run --push --deployment-preflight --manifest-authorized-deployment-preflight ...
```

Result:

- status：`ready`
- operation：`deployment-preflight`
- mode：`read-only`
- actor / queue / state：`matched`
- runtime_sha：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- runtime_digest：`a4dfa5e25f2e6b0f291fdf8e5e9163b70b243ea3836a1d47631e02697d1ee063`
- push_mode：`push`
- exact_run_ids：`["auto-i18n-en-614aa4dc3542ab2c5637"]`
- max_runs：`1`

Exact translation selector dry-run command used the same official module entry without `--deployment-preflight`, so it had to pass the real clean-origin gate before selecting/mutating:

```text
python3.12 -m scripts.agy_content_publisher --repo-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue --state-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state --max-runs 1 --exact-run-id auto-i18n-en-614aa4dc3542ab2c5637 --dry-run --push
```

Result:

```text
PublishBlocked: local HEAD differs from origin/main: 6477ab815e8a != 0257bd5213ee
```

## Terminal Accounting

- translation publication transaction：`0`
- tag：`0`
- push：`0`
- public locale URL：not created / not validated
- browser validation：not run because publication never occurred
- HTTP validation：not run because publication never occurred
- public content update：`0`
- ledger new translation transaction：`0`
- runtime actor worktree dirty state：none
- seven services terminal state：STOPPED / not loaded

## Blocker

root_cause：`REMOTE_MAIN_BEHIND_RUNTIME_ACTOR`

同 blocker 嘗試次數：`1` for card B（card A had already observed the same formal gate, but this card collected independent official-entry evidence）。

Interpretation：正式 publisher requires local actor HEAD to equal `origin/main` before any exact-run publish path can proceed. The active runtime actor is `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`, while the official remote `refs/heads/main` is still `0257bd5213eed0d0df10661a54f6215901a54997`. The card forbids manual push, alternate deploy, clean-origin gate edits, or Card A blocker repair, so the safe terminal state is `BLOCKED`.

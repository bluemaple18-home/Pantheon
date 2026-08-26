# Evidence：Pantheon 舊文原網址自動化驗收 A

## Dispatch

- formal thread ID：`01a03c25-41fd-7342-88f0-3b2aa1eeb56c`
- cwd：`/Users/mattkuo/.codex/worktrees/da94/Pantheon`
- source SHA：`6ccbde3a6fb036db3a548db075ec2c93ec771f66`
- worktree：detached/獨立 worktree；bootstrap 時 clean
- activation token：`act-v1:eebaa1bf3994a16ecf51c0c5ed5f86c8acb3495d262c28d7c5b92ed195408191`

## CodeGraph

`codegraph_status`：

- files indexed：`583`
- total nodes：`7034`
- total edges：`15792`
- database size：`18.36 MB`

第一次 source decision query 命中：

- `scripts/agy_content_publisher.py:3912` `publish_ready_rewrite_runs`
- `scripts/agy_content_publisher.py:3011` `summarize_legacy_rewrite_backlog`
- `scripts/agy_content_publisher.py:2927` `collect_ready_rewrite_runs`
- `scripts/agy_gemini_coordinator.py:5031` `seed_legacy_rewrite_runs`

## Runtime Manifest

`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`：

- actor_head：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- generation：`g47-6477ab81-activation-only-20260826`
- identity：`gate2-actor:6477ab815e8aecca7d1e8e1588e6e5eba0fab001:activation-only`
- runtime_digest：`a4dfa5e25f2e6b0f291fdf8e5e9163b70b243ea3836a1d47631e02697d1ee063`
- runtime_identity_digest：`9cfeb7d9d3b30b5759b547fca1f003d4f5a7cc1fef42297601a86b2eaa5800ce`
- queue_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue`
- publisher_state_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state`

## Service State

逐一查詢七個 label 均回 `Could not find service ... in domain for user gui: 501`：

- `com.pantheon.agy-content-publisher`
- `com.pantheon.agy-gemini-coordinator`
- `com.pantheon.agy-gemini-new`
- `com.pantheon.agy-gemini-rewrite`
- `com.pantheon.agy-gemini-i18n-new`
- `com.pantheon.agy-gemini-i18n-rewrite`
- `com.pantheon.content-capacity-guard`

判定：七服務保持 STOPPED / not loaded。

## Readiness And Capacity

- `artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/fresh-67f62f/rule25-readiness/official-gate-ready.json`
  - status：`READY`
  - returncode：`0`
- `artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/fresh-67f62f/rule25-readiness/official-gate-blocked.json`
  - status：`BLOCKED`
  - failure：missing `push`
- `artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/fresh-67f62f/rule25-readiness/package/production-canary-capability-receipt.json`
  - steps：`create`, `run`, `select`, `publish`, `transaction`, `tag`, `push`
  - each step has positive `PASS` and negative `BLOCKED` evidence
- `artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/fresh-67f62f/rule25-readiness/capacity/capacity-receipt.json`
  - status：`PASS`
  - stop_loss_negative_result：`BLOCKED`
  - production_mutation：`false`

## Queue And Candidate

Runtime queue summary from `queue/runs`：

- `complete + rewrite_existing_body`：`3`
- rewrite rows：
  - `legacy-auto-sweep-v1-astrology-0001-astro-base-01`：complete，已在 ledger `rewrite_released_runs`
  - `legacy-auto-sweep-v1-astrology-0002-astro-base-02`：complete，未在 ledger `rewrite_released_runs`
  - `legacy-auto-sweep-v1-astrology-0003-astro-base-03`：complete，已在 ledger `rewrite_released_runs`

Selected candidate：

- run_id：`legacy-auto-sweep-v1-astrology-0002-astro-base-02`
- article_id：`ASTRO-BASE-02`
- canonical：`https://www.mysticpantheon.com/articles/astrology/astrology-0002`
- source file：`app/web/static/article-meta.js`
- current body sha256：`0ae9b937f269a272102c1e94644e3cd613db609fd3cfb013c74a99f15b280449`
- reviewer verdict：`APPROVE`
- reviewer hard_failure：`false`
- reviewer findings：`[]`

Baseline hashes before attempted dry-run:

- ledger：`224d78887b4a1062702e3b920377eda8ff2abb8264b1ec48861254afe6fddabe`
- article prerender HTML：`97216e5578803f3a2fe1d03b82f33be04ec3fdac3e768002c9d434a19d2d6a31`
- article registry：`964cf505b5f305c0a44ca80efe7847b6e2df6fb242dbcc89c1b7991fa1d4e42e`

## Official Entrypoint Results

Deployment preflight command used official module entry:

`python3.12 -m scripts.agy_content_publisher --repo-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue --state-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state --rewrite-release --exact-run-id legacy-auto-sweep-v1-astrology-0002-astro-base-02 --max-runs 1 --dry-run --push --deployment-preflight ...`

Result:

- status：`ready`
- operation：`deployment-preflight`
- mode：`read-only`
- actor / queue / state：`matched`
- runtime_sha：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
- runtime_digest：`a4dfa5e25f2e6b0f291fdf8e5e9163b70b243ea3836a1d47631e02697d1ee063`
- push_mode：`push`
- exact_run_ids：`["legacy-auto-sweep-v1-astrology-0002-astro-base-02"]`

Exact rewrite selector dry-run command used the same official module entry without `--deployment-preflight`.

Result:

```text
PublishBlocked: local HEAD differs from origin/main: 6477ab815e8a != 0257bd5213ee
```

Remote confirmation:

```text
0257bd5213eed0d0df10661a54f6215901a54997 refs/heads/main
```

Actor local confirmation:

```text
6477ab815e8aecca7d1e8e1588e6e5eba0fab001
878db727f4c1348d36a672cb96393db17bfc4cef
fix: migrate legacy active runtime state
```

## Terminal Accounting

- publication transaction：`0`
- tag：`0`
- push：`0`
- public update：`0`
- new rewrite evidence directories after attempt：none; existing only `rewrite-0.3.367`, `rewrite-0.3.368`
- runtime actor status：clean
- current task worktree before result/evidence write：clean

No browser/public URL validation was run because publication never occurred.

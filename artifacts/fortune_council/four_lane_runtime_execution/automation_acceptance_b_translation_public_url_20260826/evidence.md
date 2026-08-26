# Evidence：Pantheon 翻譯公開網址自動化驗收 B

## Dispatch

- formal thread ID：`01a03c34-fd96-7021-9423-29879c9b5b47`
- dispatch_key：`v1:9bef6288f7b2b5684fc4563765b80db2ef33b3bf992dd2261ba8544f6a6f3c5c`
- activation_token：`act-v1:8e9e60c28a44e0b5fe1813b7b3c83438d6fb4ca066b8832c37d4e8532f3786d3`
- cwd：`/Users/mattkuo/.codex/worktrees/2cf0/Pantheon`
- continuation HEAD：`204a8bd8b86b37f411048983730ce1efb9fa2734`
- worktree：detached，clean

## Card And Rule

- 實體卡：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826.md`
- 本次續跑不建立 replacement、不重跑 A、不重跑 Writer/Reviewer、不開 C/第四卡。

## CodeGraph

本次 source decision 前執行 CodeGraph：

```text
CodeGraph not initialized in /Users/mattkuo/.codex/worktrees/2cf0/Pantheon
```

degraded reason：控制面聲明已在 source SHA 準備索引，但本 formal worktree 的 CodeGraph tool 回 `not initialized`；後續僅限域查詢 `scripts/agy_content_publisher.py`、runtime manifest、queue/state 與本卡 evidence。

定位到的正式入口：

- `scripts.agy_content_publisher:deployment_preflight`
- `scripts.agy_content_publisher:publish_ready_translation_runs`
- `scripts.agy_content_publisher:collect_ready_translation_runs`
- CLI：`python -m scripts.agy_content_publisher`

## Runtime Manifest

`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`：

- actor_head：`204a8bd8b86b37f411048983730ce1efb9fa2734`
- generation：`g49-204a8bd8-main-promotion-20260826`
- identity：`gate2-actor:204a8bd8b86b37f411048983730ce1efb9fa2734:activation-only`
- manifest_digest：`18d91a2246d5d4311b57471f116d649760003437dc482a0e1675cddf9fde0bb7`
- runtime_digest：`3528c6128abdeb76f7b2545be04795709466148a0edb15ed857a23de86cda3e0`
- runtime_identity_digest：`d19ba363be2f7eef559bab01ed093a8182ae6bd832fa6956573590ab593da18c`
- actor_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor`
- queue_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue`
- publisher_state_root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state`
- activation barrier：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/four-lane-activation-g49-204a8bd8-main-promotion-20260826.barrier`

Actor/origin：

```text
actor HEAD      204a8bd8b86b37f411048983730ce1efb9fa2734
actor origin    204a8bd8b86b37f411048983730ce1efb9fa2734
actor status    clean
```

## Service State

Terminal service checks returned `Could not find service ... in domain for port` for all seven labels:

- `com.pantheon.agy-content-publisher`
- `com.pantheon.agy-gemini-coordinator`
- `com.pantheon.agy-gemini-new`
- `com.pantheon.agy-gemini-rewrite`
- `com.pantheon.agy-gemini-i18n-new`
- `com.pantheon.agy-gemini-i18n-rewrite`
- `com.pantheon.content-capacity-guard`

Interpretation：seven Pantheon launchd labels are `STOPPED_OR_NOT_LOADED`; no service was started.

## Candidate And Queue State

Authorized exact run:

- run_id：`auto-i18n-en-614aa4dc3542ab2c5637`
- source_article_id：`ASTRO-BASE-01`
- target locale：`en`
- expected article_id：`ASTRO-BASE-01:en`

Current formal `queue/translation-runs` contains only:

```text
auto-i18n-en-aa637e1bf05d3ad21429
auto-i18n-ja-278fce6e38a85de996dd
auto-i18n-ja-3a39827aeb778de1957f
auto-i18n-ja-4a9da72316d5d368eeb5
auto-i18n-ko-85d513b289d89dd9bf75
auto-i18n-ko-bb1bc3865ed466bac17a
auto-i18n-ko-bc1ce017b4ac2657a133
```

Target queue files:

```text
rg --files queue | rg auto-i18n-en-614aa4dc3542ab2c5637
no matches
```

Retry record:

```json
{"schema_version":1,"phase":"translation","run_id":"auto-i18n-en-614aa4dc3542ab2c5637","attempts":1,"max_attempts":3,"error_type":"CalledProcessError","eligibility":"deferred","candidate_preserved":true,"recovery_count":0,"last_recovery_id":null,"next_eligible_at":"2026-08-21T12:16:10+08:00","evidence":"/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/evidence/failed-translation-08240d2029/failure.json"}
```

Ledger:

```json
{"published_count":1,"deferred_count":8,"target_published":[],"target_deferred":[]}
```

## Official Entrypoint Results

Deployment preflight with manifest authority:

```json
{"schema_version":1,"status":"ready","operation":"deployment-preflight","mode":"read-only","dry_run":true,"mutation_permitted":false,"actor":"matched","queue":"matched","state":"matched","runtime_sha":"204a8bd8b86b37f411048983730ce1efb9fa2734","runtime_manifest_schema_version":1,"runtime_digest":"3528c6128abdeb76f7b2545be04795709466148a0edb15ed857a23de86cda3e0","push_mode":"push","authority_mode":"manifest","manifest_digest":"18d91a2246d5d4311b57471f116d649760003437dc482a0e1675cddf9fde0bb7","exact_run_ids":["auto-i18n-en-614aa4dc3542ab2c5637"],"max_runs":1}
```

Exact dry-run command:

```text
python3.12 -m scripts.agy_content_publisher --repo-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue --state-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state --max-runs 1 --exact-run-id auto-i18n-en-614aa4dc3542ab2c5637 --dry-run --push --include-rewrites
```

Exact dry-run result summary:

```json
{"schema_version":1,"status":"ok","create":{"status":"idle","published":0},"rewrite":{"status":"idle","rewritten":0},"translation":{"status":"idle_rejects_only","translated":0,"base_sha":"204a8bd8b86b37f411048983730ce1efb9fa2734"}}
```

Interpretation：official dry-run was not ready for the authorized translation publication. It did not select `auto-i18n-en-614aa4dc3542ab2c5637` as publishable.

## Terminal Accounting

- translation publication transaction：`0`
- publication commit：none
- publication tag：none
- push：`0`
- public locale URL：none
- HTTP validation：not run because publication never occurred
- browser validation：not run because publication never occurred
- ledger target transaction count：`0`
- queue/run terminal state：`not ready / absent from formal translation-runs`
- runtime actor worktree dirty state：clean
- evidence-only commit push：not pushed

## Blocker

root_cause：`EXACT_TRANSLATION_RUN_NOT_READY_IN_FORMAL_QUEUE`

The blocker is single and mutation-preventing: the authorized exact run no longer exists as a ready translation run under the formal queue, and the official translation publisher dry-run reports `idle_rejects_only` with `translated=0`. The card forbids recovering queue state, rerunning Writer/Reviewer, touching other queue items, or using any alternate publication path.

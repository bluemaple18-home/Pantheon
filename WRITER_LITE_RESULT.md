# Writer Lite Repair1 結果

日期：2026-09-10
工作區：`/Users/mattkuo/Documents/Pantheon/.work/writer-lite-switch-20260910/source`
branch：`codex/writer-lite-switch-20260910`
baseline：`c217958bacb7f5403fa3a41a19b9ba2f63ba68a3`

## 結論

GO for 原 Reviewer review（RESTORE_FIRST 範圍）。Repair1 已補上同一 run 的 bounded Lite retry 入口：保留原 run、brief、舊 Flash request 證據與 correlation，只讓卡住的 writer job 產生新的 Lite request，並讓原 run 的 `last_job_id` 指到 Lite retry。最新補測已用真正 `run_pipeline_tick` 證明：Lite writer inbox 結果會被原生流程接收，並排出同一 run / namespace 的 Reviewer request。未操作 production、未呼叫 provider、未寫正式 queue。

原 Reviewer P1 已閉合：`--exact-run-id` 本身仍只會選 namespace，不會自動把舊 Flash request 變 Lite；Repair1 不是再主張 exact-run 會轉模型，而是沿既有 `replace-failed-external-job` seam 新增 `--pending-writer-lite-retry`，先在同一 run 裡建立 Lite retry request，再讓 exact-run 消費這個新 request。

## 改檔清單

1. `config/agy_gemini_model_routes.v1.json`
   - Writer primary route：`gemini-3.5-flash-lite`
   - Reviewer 維持：`gemini-3.1-flash-lite`
   - route digest：`1ed24743202ff953bf32d07d570602e61c77194df45889cabc93b13495945e0e`

2. `scripts/agy_gemini_coordinator.py`
   - 延用既有 `replace-failed-external-job` 入口、queue lock、decision path、staging request、identity receipt、state receipt、idempotent replay 與 same-run recovery seam。
   - 新增窄旗標：`--pending-writer-lite-retry`
   - 此模式只接受 source writer request 仍在 outbox、run active、`last_job_id` 精確相符、無 inbox/failed outcome、無 processing claim、無 production attempt evidence。
   - execute 時將原 Flash request 移到 archive 保存，建立新的 Lite writer request 到 outbox，更新同一 run `last_job_id` 與 replacement receipt。

3. `tests/test_writer_lite_repair1.py`
   - 覆蓋 new/rewrite 兩 lane。
   - 覆蓋 dry-run 零 mutation、execute 重入、同一 run 消費 Lite inbox complete。
   - 覆蓋 processing / existing success / production attempt evidence 拒絕。
   - RESTORE_FIRST 追加：new/rewrite 各用完整有效 brief/candidate，先由原生 tick 產生舊 Flash writer pending，再走 Repair1 建 Lite retry，只 mock provider inbox result，最後再次跑真正 `run_pipeline_tick`，確認 Lite writer success receipt、external-candidate 落盤、Reviewer operation/request 進入 pending。

4. `tests/test_writer_lite_switch_minimal.py`
   - 保留 Lite route / installer guard / exact-run no-fallback 的最小驗證。

## Why Not Less

- 只改 config 不夠：Reviewer 已重現 exact-run 仍會消費原 Flash request，不能讓同一 run 改用 Lite。
- 只用 `--exact-run-id` 不夠：它只過濾 namespace，不會改 request model，也不能改舊 immutable request。
- 不能把 pending Flash 捏造成 failed：目前卡住狀態不是可信 failed receipt；偽造 failed/quota 會破壞證據。
- 不能手改原 request：會改掉 job_id/request_sha256，違反 immutable request identity。
- 因此最小必要支援是：在既有 replacement seam 裡新增 pending writer Lite retry mode，建立新的 Lite request 並保留舊 request 證據。

## Why Not More

- 沒有新增 queue lifecycle、runtime replacement、migration framework 或新 coordinator 流程。
- 沒有重建 run、刪稿件、刪審查、清 queue、改 provider receipt。
- 沒有動 runner/outbox request schema。
- 沒有部署、push、啟停 service、寫 production、呼叫 Gemini provider。

## 既有 Seam 與新增部分

延用既有：

- `replace-failed-external-job` CLI / function 入口。
- replacement queue lock。
- `failed-external-job-replacements/<source_job_id>.json` decision。
- request staging file，再 publish 到 outbox。
- `identity-replacement-receipts/<source_job_id>.json`。
- state 上的 `failed_external_job_replacement` receipt。
- 既有 coordinator `_advance` / `cycle_once(... --exact-run-id ...)` 推進同一 run；本輪補測直接呼叫 `_advance(..., run_pipeline_tick, job_queue_root=lane_root)`，沒有 mock tick 成功。

Repair1 新增：

- `--pending-writer-lite-retry` 旗標。
- pending source guard：只允許 outbox source，拒絕 processing、terminalizing、inbox、failed、production attempt。
- 新 Lite request identity：同 namespace / role writer / same prompt / same schema / model `gemini-3.5-flash-lite`。
- pending retry decision 的 `action=pending_writer_lite_retry`、`from=outbox`、`to=archive+outbox`。

## Dry-run / Execute 指令形狀

以下是正式套用時的精確入口形狀；本 Worker 未在 production 執行。

Dry-run：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m scripts.agy_gemini_coordinator \
  --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue \
  replace-failed-external-job /ABS/RUN_DIR \
  --job-queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/lanes/NEW_OR_REWRITE \
  --lane NEW_OR_REWRITE \
  --run-id RUN_ID \
  --job-id SOURCE_FLASH_JOB_ID \
  --request-sha256 SOURCE_REQUEST_SHA256 \
  --namespace RUN_NAMESPACE \
  --correlation-id RUN_CORRELATION_ID \
  --authority-digest AUTHORITY_SHA256 \
  --pending-writer-lite-retry \
  --plan-only
```

Execute：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m scripts.agy_gemini_coordinator \
  --queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue \
  replace-failed-external-job /ABS/RUN_DIR \
  --job-queue-root /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/lanes/NEW_OR_REWRITE \
  --lane NEW_OR_REWRITE \
  --run-id RUN_ID \
  --job-id SOURCE_FLASH_JOB_ID \
  --request-sha256 SOURCE_REQUEST_SHA256 \
  --namespace RUN_NAMESPACE \
  --correlation-id RUN_CORRELATION_ID \
  --authority-digest AUTHORITY_SHA256 \
  --pending-writer-lite-retry \
  --execute
```

Execute 後再用既有 exact-run/lane runner 讓原 run 消費 Lite 結果；不要手改 staged plist 或原 request。必要參數仍是同一 run 的 `run_dir`、lane job root、`run_id`、source Flash `job_id/request_sha256/namespace`、`correlation_id`、`authority_digest`、以及目前 source config 的 Writer Lite / Reviewer Lite route env。

## 中斷副作用與恢復（RESTORE_FIRST 延後）

Owner 已把優先序改成先恢復換 Lite 發文；中斷自動恢復補強延後，本 Worker 本輪未實作、未補測、也不宣稱已驗收中斷恢復。

本輪已驗的正常路徑副作用只有：

- dry-run 零 mutation。
- execute 會把原 Flash request 移到 archive 保存，不刪除、不改 bytes。
- execute 會建立新的 Lite writer request、更新同一 run `last_job_id`。
- 原生 tick 消費 Lite inbox 後，會排出 Reviewer request 並讓 state 停在 Reviewer pending。

回退未跑 provider 前：由主線用 decision/receipt 證據人工判斷是否移回原 source outbox 並回復 state `last_job_id`；不要刪 decision 來假裝未發生。中斷恢復若要自動化，另等 Repair2/Owner 授權。

## 測試

已通過：

0. RESTORE_FIRST 原生接續補測：
   `PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -p no:cacheprovider tests/test_writer_lite_repair1.py -q`
   - `9 passed`
   - 含 new/rewrite 兩個 `run_pipeline_tick` continuation 測試；只 mock provider inbox result，沒有 mock tick 成功。

1. `PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_writer_lite_repair1.py tests/test_agy_gemini_coordinator.py -k 'writer_lite_repair1 or failed_external_job_replacement' --tb=short`
   - `35 passed, 473 deselected`

2. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/mattkuo/Documents/Pantheon/.work/writer-lite-switch-20260910/source /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider /Users/mattkuo/Documents/Pantheon/.work/writer-lite-switch-20260910/review-a/test_exact_run_contract.py --tb=short`
   - `3 passed`

3. `PYTHONDONTWRITEBYTECODE=1 /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_writer_lite_switch_minimal.py tests/test_flash_writer_route.py tests/test_agy_gemini_runner.py tests/test_agy_gemini_allocator.py -k 'writer_lite_switch_minimal or flash_writer_route or exact_run_ids or quota_block_is_per_model' --tb=short`
   - `12 passed, 17 deselected`

4. `git diff --check`
   - PASS

本輪最新 `git diff --check`：
   - PASS

未跑：

- 未呼叫 provider。
- 未啟停 service。
- 未寫正式 queue、LaunchAgents、credential、runtime manifest 或正式 actor。
- 未測中斷自動恢復補強（RESTORE_FIRST 明確延後）。

## 已知正式目標

唯讀已知兩筆舊 Flash job：

| lane | job_id | run_id |
| --- | --- | --- |
| new | `7f076dd59b7f679e4d43ecbc0f7395441d22f7f2` | `auto-new-v1-20260910-002-01` |
| rewrite | `c12acc3c703de0afaafd6129c4415a320368c62c` | `legacy-auto-sweep-v1-astrology-0010-astro-houses-01` |

正式套用前主線仍需讀正式 queue 裡的 `request_sha256`、`namespace`、`correlation_id`、`run_dir` 與 source location，並確認 source 仍在 outbox、沒有 processing/inbox/failed/production-attempt。

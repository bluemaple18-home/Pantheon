---
id: RESULT-PANTHEON-OPEN2-QUOTA-SEAM-MAPPING-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: research_result
date: 2026-09-02
status: ready_for_mainline_numeric_decision
---

# OPEN-2 quota seam 與成本上限唯讀 mapping 結果

## 結論

`READY_FOR_MAINLINE_NUMERIC_DECISION`

既有 source 足以定位兩個不同但可沿用的 durable authority：publication success
quota 應放在三個 Publisher phase 共用的 `state_root/publisher.lock` 與
`state_root/ledger.json`；daily provider-call cap 應放在四條 lane 共用的 production
credential allocator admission 與既有 allocator state。兩者都不需要新增 database、
registry、ledger、FSM 或第二套 runtime。

本 mapping 建議 Mainline 裁決 `102 provider admissions / Asia/Taipei day`。這是目前
四條 lane 各容許一個 run 完整走完既有最壞語意修復與 transport retry 預算的上限；
`75` 只能在另有 scheduler 先延後其中一條 i18n lane 時成立，不能直接套在目前會同時
推進四條 lane 的 selector。

## CodeGraph 與原始碼確認

實際執行的 task-semantic query：

```text
Map four-lane publication flow from selection through provider calls and retries to the shared publisher lock and release ledger; distinguish transport retries, per-run article attempts, and publisher retries; identify crash replay and daily quota admission seams
```

CodeGraph 在 indexed HEAD `59fe3fea21d3d10aa6190086e26645df0ba47229`
回傳 `PublishBlocked`、probe `Ledger` 與 `ReleaseContractError` 為入口。其對 production
lane／allocator 的 recall 不完整，因此依專案規則再以限域 `rg` 與下列 source symbols
確認，未以 graph 低 recall 推論產品行為。

### 四 lane selection 與 provider admission

- `scripts/agy_gemini_coordinator.py:2829-2850` 的 `_select_lane_states` 依
  `registered_at`、`run_id` 排序，每條 `new`、`rewrite`、`i18n-new`、
  `i18n-rewrite` 各選最早的一個 active run。
- `scripts/agy_gemini_coordinator.py:6051-6086` 的 `cycle_once` 在 lane mode 把這四個
  state 各交給 `_advance`；`scripts/agy_gemini_coordinator.py:2560-2619` 的
  `_advance` 以 `run_pipeline_tick` 推進 run，pending／failed／complete 寫回既有 run
  registry。這是 run lifecycle，不是 provider transport retry counter。
- `scripts/agy_gemini_outbox.py:1060-1079` 的 `run_pipeline_tick` 依 brief mode 選
  SEO 或 multilingual Writer→Reviewer pipeline，固定 `max_repairs=2`。
- `scripts/agy_gemini_outbox.py:971-1057` 的 `OutboxGeminiClient.generate_json` 對每個
  邏輯 model operation 建立外部 job；`OUTBOX_MAX_TRANSPORT_RETRIES=2`，所以
  `range(... + 1)` 最多產生 3 個不同 transport job。
- `scripts/agy_gemini_outbox.py:313-346` 的 `build_external_request` 讓同一 request 的
  transport attempt 0、1、2 各有不同 `job_id`，因此可逐一對應實際 provider
  admission，不會把三次 transport 嘗試誤當同一次。
- `scripts/agy_gemini_runner.py:1424-1465` 在 claim 後建立 production-attempt evidence，
  再由 `_credential_from_admission` commit allocator ordinal；
  `scripts/agy_gemini_runner.py:1523-1536` 才進 `_single_request_http_transport`。
  `scripts/agy_seo_copy_pipeline.py:2724-2765` 證明 production pool transport 每個 job
  只做一次 POST，不在 runner 內再重試。
- `scripts/agy_gemini_allocator.py:632-662` 的 `ProductionSlotAdmission.commit` 在共用
  allocator lock 下，於 provider call 前 durable 增加 `last_ordinal`；
  `scripts/agy_gemini_allocator.py:762-869` 的 `production_slot_admission` 對所有 lane
  使用同一 absolute state path、lock file 與 directory lock。這是現有最小、跨 lane
  且 fail-closed 的 provider-call admission seam。
- `scripts/install_agy_gemini_coordinator_launchd.sh:200,289,334` 將 coordinator 與每條
  lane 指向同一 `AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE`，確認上述 allocator 不是
  lane-local authority。

### Publisher transaction seam

- `scripts/agy_content_publisher.py:2544-2655` 的 `_recoverable_publish` 包住 create、
  rewrite、translation 三個 phase，先取得 git-common transaction lock，再執行
  phase function；同一條例外路徑才記 Publisher retry。
- `scripts/agy_content_publisher.py:4154-4214`、`:4338-4415`、`:4510-4568` 的三個
  phase 都取得同一 `state_root/publisher.lock`，並在 lock 內 selection、dry-run 判斷
  與開始 mutation。success quota admission 必須插在此 lock 內、selection 後且
  `journal.begin()`／任何 publication mutation 前。
- `scripts/agy_content_publisher.py:2698-2723` 的 `_ledger_path`／`_load_ledger` 已提供
  共用 `ledger.json`，create、rewrite、translation 分別在 `:4284-4300`、
  `:4466-4483`、`:4675-4698` 寫入 run identity、version、commit 與 published time。
  可擴充同一 ledger schema 表達 quota reservation／terminal accounting，不需第二份
  quota ledger。
- `scripts/agy_content_publisher.py:3859-3982` 顯示 create 與 rewrite 在成功 atomic push
  後才寫 ledger，且一般成功 push 前沒有 durable prepared control；只有特定 translation
  replacement 會在 `:3900-3909` 先寫 `PUSH_PREPARED`。因此目前確實存在「remote
  publication 成功、ledger 尚未寫入」crash window，不能只在現有 ledger append 前加
  計數。

最小 implementation seam 是：在 `publisher.lock` 內，以同一 ledger 先建立綁定
`run_id`、publication class、Asia/Taipei admission date 的 reservation；並把現有
`push-outcome-unresolved.json` 的 prepared/reconcile 契約一般化到 create、rewrite、
translation。replay 先用 run identity、target commit、tag 與 remote main 判定 mutation
是否已成立，再把同一 reservation 原子終結為 success 或釋放。不得只依時間或「檔案
存在」猜測結果。

## 三層 attempt／retry owner

| 層 | Authority／上限 | 是否呼叫 provider | 持久化與邊界 |
|---|---|---:|---|
| Provider transport | `OutboxGeminiClient.generate_json`；每個邏輯 operation 最多 3 個 transport job | 是；每個 job 至多一次 POST | lane `outbox/processing/archive/failed/inbox`、`production-attempts/<job_id>.attempt` 與共用 allocator ordinal |
| Run／article semantic attempt | SEO pipeline initial + 2 content repairs；translation initial + 2 generations | 是；每個 generation 含多個邏輯 operation | run dir 的 `attempts/`、`generations/`、operation receipt、candidate/review 與 coordinator run registry |
| Publisher retry | `MAX_RETRY_ATTEMPTS=3`，在 publication mutation 失敗並 recovery 後累加 | 否；內容已由 Writer/Reviewer 產出 | `state_root/retry/<phase>/<run_id>.json`；selection 以 `_retry_eligible` 排除 deferred/exhausted |

Publisher 的 `DEFAULT_MAX_RUNS=3`（`scripts/agy_content_publisher.py:38,4791-4795`）只限制
單次 Publisher invocation 收取幾個 ready run，不是 daily quota，也不是 provider-call
上限。`MAX_RETRY_ATTEMPTS=3`（`:92,1357-1418`）是 publication recovery budget，不能
拿來乘成 Gemini 成本。

## Provider-call 最壞上限推導

### 每個 run 的邏輯 operations

- `new`／`rewrite`：`scripts/agy_seo_copy_pipeline.py:4111-4323` 允許 initial 加 2 次
  content repair，正常每輪各 1 次 Writer 與 Reviewer，即 6 operations；另有全 run
  共用 `MAX_WRITER_SCHEMA_REPAIRS=2`（`:114,4195-4205`），最壞再加 2 次 Writer，
  合計 **8**。
- 每個 `i18n-*` run：`scripts/agy_multilingual_pipeline.py:3879-4020` 每 generation
  依序呼叫 locale-plan Writer、article Writer、Reviewer，共 3 operations；
  `_run_fresh_writer_reviewer` 在 `:4092-4121` 最多 3 generations，合計 **9**。
- 四 lane 各完整推進一個 run：`8 + 8 + 9 + 9 = 34` logical operations。
- 每個 operation 最多 3 個 transport jobs：`34 × 3 = 102` provider admissions。
  現行 `config/agy_gemini_model_routes.v1.json` 對 Writer／Reviewer 都只有一條 model
  route，沒有額外 route fan-out。

### 數值候選

| 候選 | 每日最壞 provider admissions | 判斷 |
|---|---:|---|
| `34` | 34 | 只容許每個 logical operation 一次 call；會提前吃掉既有 transport retry，拒絕 |
| `75` | 75 | 可完整覆蓋 new + rewrite + 一條 shared-translation success class 的最壞 3× transport 預算；但目前 selector 仍會推進兩條 i18n，須先有 scheduler 明確延後其中一條才可採 |
| `102` | 102 | 覆蓋現行四 lane 各一個 run 的完整已存在預算；建議 Mainline 採用 |

`why_not_less`：低於 34 連四條 lane 在零 transport retry 下的合法 semantic budget 都
無法容納；34 至 74 會吃掉既有 transport retry 或讓第二條 i18n lane 的結果取決於
執行先後；75 至 101 仍不能證明四條 lane 各一 run 的完整 envelope。

`why_not_more`：現行 selector 每 cycle 每 lane 只推進一個最早 run；102 已覆蓋四個
run 的完整既有 retry envelope。更高數字只允許同日再消耗下一批失敗 run，沒有來自
daily success policy 的需求證據。

`do_not_absorb`：不要新增 token-price service、provider pricing API、per-model／per-slot
第二套 budget、quota database、daily FSM 或 Publisher 內的 provider counter；不要用
filesystem mtime 當業務日期；不要把 allocator 的 provider quota block（America/Los_Angeles
reset）改名冒充本次 Asia/Taipei business cap。

最壞成本能由 repo 證明的是 **102 次實際 provider admissions／日**。source 沒有鎖定
每次 request 的 token 上限或價格表，因此不能誠實換算為每日最高 token 或金額；若
Owner 要的是貨幣硬上限而非 call-count hard cap，仍需另鎖 per-call token／price
authority。這不阻止目前 Owner 已允許的 provider-call hard cap 類型。

### Cost-cap 最小持久化變更

沿用 `production-credential-pool-state.json` 與其 lock，將 allocator schema 擴充
Asia/Taipei `cost_date`、`daily_provider_admissions` 與 configured cap。判斷與遞增要和
現有 ordinal 在一次 `_commit_state` 中完成；失敗 call 不退還，crash 在 admission 後
也不退還。這比掃 lane-local attempt marker 更可靠：marker payload 在
`scripts/agy_gemini_runner.py:858-868` 沒有日期，而且四條 lane 分散在不同 directory。

## Success quota 與 crash/replay 最小測試矩陣

| Case | 注入點／輸入 | 必要結果 |
|---|---|---|
| class quota | 同日第二個 new、第二個 rewrite、第二個 i18n（跨 i18n-new／i18n-rewrite） | 各自 fail-closed；兩條 i18n 共用 translation=1 |
| total quota | 同日已有三個不同 class success | 任一第四筆 publication admission 被拒，沒有 repo/tag/push mutation |
| concurrent phases | 兩個 process 同時看到最後一格 | 只有持有 `publisher.lock` 者 reservation；另一個 busy／cap-exhausted |
| run replay | 同一 `run_id` 重跑、ledger 已 terminal success | 回傳 already-published 等價結果；success count 不增加 |
| crash before mutation | reservation 已寫、`journal.begin()` 前 crash | replay 沿用同 admission date；可安全續跑或釋放，不能建立第二 reservation |
| crash after commit/tag、push 前 | prepared control 已綁 target commit/tag | replay 依 remote refs 判斷未發布才續推，不重計 reservation |
| crash after successful push、ledger terminal 前 | remote main/tag 已成立 | replay 辨認同一 run publication，補成一次 success；不得另放一篇 |
| cross midnight | 23:59 Asia/Taipei admission，00:01 terminal | 同一 run 永遠歸 admission date；不得移到次日再占一次 |
| failed publication | mutation recovery 完成且可證明 remote 未成立 | 釋放 success reservation；Publisher retry 照既有 3 次 authority，provider cap 不回補 |
| malformed quota state | schema/date/count/run identity 任一破損 | publication fail-closed，不可把損壞資料當零 |
| cost cap edge | 四 lane concurrent，當日第 102 與第 103 次 allocator admission | 第 102 次原子 commit；第 103 次在 claim/provider call 前拒絕 |
| cost crash | allocator 已 commit、provider call 前 crash | 當次仍計成本；同 job replay 不得再增加或再呼叫 provider |
| cost date reset | Asia/Taipei 23:59:59 與 00:00:00 | 依 allocator admission instant 分日；不能使用 host locale 或 America/Los_Angeles |

後續 RED→GREEN 至少應落在 `tests/test_agy_content_publisher.py`、
`tests/test_agy_gemini_allocator.py`、`tests/test_agy_gemini_runner.py`；若修改 allocator
state schema，舊 schema migration、未知 future schema 與 damaged-state fail-closed 都要
覆蓋。

## 執行證據

- `git diff --check`：PASS（無輸出）。
- `git status --short`：只有 Mainline 預先放入的 untracked CARD 與本 RESULT；沒有
  source、tests 或 config 變更。
- production mutation：`0`
- provider call：`NOT_RUN`
- `launchctl`：`NOT_RUN`
- source／tests／config 修改：`0`
- commit／push：`NOT_RUN`

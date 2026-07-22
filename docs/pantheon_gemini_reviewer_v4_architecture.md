# Pantheon Gemini Reviewer V4 architecture｜Repair 2 candidate

狀態：`READY_FOR_REVIEW`。本文件與 POC 只修 architecture contract；不授權 production implementation、Gemini 呼叫、retry、merge、deploy、publish 或 content recovery。

## Decision

保留方案 B：單一最小 broker 擁有唯一 ledger writer FD，並且只有 broker 能啟動 fake／future CLI target。這個選擇解決 parent crash 後的 completion ownership，但不把同 UID filesystem 當成安全邊界。方案 A 仍因 parent 同時是 writer 與 child observer而淘汰；方案 C 未建立不同 UID、sandbox 或 container，全部為 `UNSUPPORTED`。

核心 accounting 定義是「成功跨過 exec 的 target process 數」，不是 PID、broker attempt 或 provider internal call 數。每個 operation 的結果只能是 `0 / 1 / UNKNOWN`；provider internal calls 永遠是 `UNKNOWN`。

## 唯一 broker entrypoint 與 wire contract

Future production 只允許一個 entrypoint：`scripts.agy_gemini_v4_broker:run_single_shot`。CLI module mode 只作 supervisor 啟動面，不能另有第二個 spawn helper。POC 對應入口是 `scripts/agy_gemini_v4_architecture_probe.py --broker`，且只有它啟動 synthetic target。

Parent→broker command 使用 versioned、length-prefixed UTF-8 JSON frame；`additionalProperties=false`。欄位固定為：

```text
schema_version=1
operation_id, item_id, attempt_id
executable_digest, request_sha256, request_bytes_length
timeout_milliseconds
```

raw request 走 parent→broker 的獨立 stdin pipe；command 不含 raw prompt、raw output、secret、本機絕對路徑或 executable argv。Broker→parent control frame只回 `replay_status / process_count / outcome / exit_status / stdout_sha256 / stderr_sha256 / byte_count / final_anchor`。任何 unknown、missing、type 或 version 錯誤均在 fork 前 fail closed。

## FD allowlist 與 exec handshake

Parent 啟動 broker 時只允許 `0/1/2 + ledger_fd`；parent 在 `Popen` 返回後立刻關閉自己的 ledger FD。Broker 是唯一 ledger writer，先將 ledger FD 設為 non-inheritable／`FD_CLOEXEC`，再啟動 target。

Broker→target 固定 `close_fds=True`、`pass_fds=()`；target 只持 `0=validated request pipe`、`1=stdout pipe`、`2=stderr pipe`。ledger FD、ledger path、anchor、capability、operation identity 均不得放 target argv/env/stdin。POC 由 target 自己列舉 exec 後 FD table；正向值只能是 `[0,1,2]`。`close_fds=False`、傳入 ledger FD 或額外 FD 是 mandatory negative controls，任何一項可見即令對應 matrix cell 降為 `UNSUPPORTED`。

Exec confirmation 使用 POSIX close-on-exec error-pipe，或 CPython `subprocess.Popen` 內建的等價 error-pipe handshake。事件分界固定如下：

```text
preflight reject                      -> PREFLIGHT_REJECTED
broker accepted operation             -> BROKER_ATTEMPTED
即將執行唯一一次 fork                 -> FORK_ATTEMPTED
error-pipe 回傳 errno                  -> EXEC_FAILURE
error-pipe EOF / Popen 成功返回        -> EXEC_CONFIRMED
wait/kill/reap 結束                    -> PROCESS_TERMINAL
```

Broker crash 在 `FORK_ATTEMPTED` 前只有存在 durable `BROKER_ABORTED(CRASH_BEFORE_FORK)` 才可回 0。只留下 `BROKER_ATTEMPTED` 或 `FORK_ATTEMPTED` 時，一律 `AMBIGUOUS/UNKNOWN`；即使 orphan marker 證明 target 曾執行，也不得靠非 ledger 觀察把 replay 猜成 1。`EXEC_CONFIRMED` durable 後 success、nonzero、timeout 均為 1。任何 ambiguous window 都設定 `automatic_resend_allowed=false`。

## Strict event schema 與 replay FSM

每個 JSONL frame 都含 `schema_version=2`、正整數 `sequence`、前一 frame 的 `parent_sha256`、`event_type` 與完全一致的 `operation_id/item_id/attempt_id`。每種 event 有自己的 closed schema：

```text
OPERATION_CREATED()
PREFLIGHT_REJECTED(outcome=CLI_NOT_FOUND)
BROKER_ATTEMPTED(broker_attempt=1)
BROKER_ABORTED(outcome=CRASH_BEFORE_FORK)
FORK_ATTEMPTED(broker_attempt=1, process_ordinal=1)
EXEC_FAILURE(outcome=CLI_NOT_FOUND|PERMISSION_DENIED|EXEC_FORMAT|EXEC_RACE, process_ordinal=1)
EXEC_CONFIRMED(process_ordinal=1, pid=<observation only>)
PROCESS_TERMINAL(outcome=SUCCESS|CLI_NONZERO|CLI_TIMEOUT)
```

恰一個 `OPERATION_CREATED`、最多且只能一個 ordinal-1 broker/process attempt。Replay 拒絕 unknown/missing/type、wrong version/binding、非法 ordinal/outcome、duplicate/re-chained event、terminal-before-start、out-of-order、partial/truncated frame與 hash/sequence mismatch。`EXEC_CONFIRMED.pid` 是必填的 observation-only 正整數；`0`、負數、`bool`、字串與缺值全部是 schema error。PID 只供診斷，不是 identity，不參與去重或 operation binding。

Schema v2 的 event set 只包含上列八種事件；`PROCESS_NOT_STARTED`、`PROCESS_STARTED` 與其他 legacy aliases 一律是 `UNKNOWN_EVENT`，不得產生 current-schema `COMPLETE`。本 POC 不提供 legacy decoder；未來若有 migration 需要，必須另建明確 version boundary，且 legacy 結果不得轉成 schema v2 `COMPLETE`。

合法狀態／count 組合：

| Replay status | process count | 語意 |
|---|---:|---|
| `COMPLETE` | `0` | preflight reject |
| `COMPLETE` | `1` | exec confirmed 且有 terminal |
| `BLOCKED` | `0` | durable crash-before-fork 或 exec failure |
| `BLOCKED` | `1` | exec confirmed 但 terminal 缺失 |
| `AMBIGUOUS` | `UNKNOWN` | fork/exec 與 durable evidence 間的 crash window |
| `INVALID` | `UNKNOWN` | schema、binding、ordering、framing 或 chain 不合法 |

其他組合非法。Replay 只讀 ledger 與外部 anchor，永不啟動 target、補 event 或自動重送。

## External anchor owner 與一致性邊界

Future owner 固定為 coordinator control plane，而不是 broker、target 或 ledger module。介面固定為：

```python
anchor = anchor_store.load(operation_id, attempt_id)
anchor_store.compare_and_swap(operation_id, attempt_id, previous_anchor, next_anchor)
```

每次更新順序固定：broker append frame → `fsync(ledger_fd)` → 回傳 next anchor → coordinator 寫同目錄外的 temp anchor → `fsync(temp)` → atomic rename → `fsync(anchor directory)`。Broker crash 可能留下 ledger 超前 anchor；recovery 同時讀 ledger 與 anchor，超前、缺失或 mismatch 都 fail closed，交人工判讀，不得由 ledger 自己更新／證明 anchor，也不得重送。

此 owner 與 ledger 仍在同一本機帳號／trust domain。因此：application-level wrong binding、partial frame與相對既有 trusted anchor 的 mutation可標 `DETECTED`；same-UID attacker 同時替換整份 ledger／anchor，或 anchor 遺失後的自洽 full replacement，一律 `OUT_OF_SCOPE`，不得標 `DETECTED`。若未來要防止此攻擊，必須另開方案 C 的不同 UID／kernel isolation card。

## Runtime-derived matrix contract

每個 matrix cell 必須含 `observable_id` 與 executable predicate，status 只能由本次 runtime observables 推導；沒有可執行 observable 就是 `UNSUPPORTED`。正向 observables 至少包含 preflight=0、exec-failure 分帳、confirmed outcomes=1、target FD allowlist、strict replay與 anchor boundary。`strict_replay` 必須由上表所有合法 status/count/completeness/resend 組合，以及 terminal loss、legacy alias、PID domain、illegal order、partial frame、wrong binding 與 broken chain 的實際 replay controls 共同推導；其中任一結果錯誤，`illegal_or_partial_replay` cell 必須降為 `UNSUPPORTED`。每項 supported claim 都有反向 negative control；覆寫／反轉 observable 時 cell 必須降級，不能保留 literal 綠燈。方案 C 因 `kernel_isolation_executed=false` 全部 `UNSUPPORTED`。

## Exact future production cutover（仍需另卡）

首張 implementation 卡只允許 canary 接一條 caller：`scripts/agy_gemini_runner.py:process_once` 內目前呼叫 `generate_json(...)` 的位置，改由 `AGY_GEMINI_V4_BROKER=1` 選入 `scripts.agy_gemini_v4_broker:run_single_shot`。`scripts/agy_seo_copy_pipeline.py:GeminiClient._cli_transport`、HTTP transport、outbox enqueue、coordinator、其他 `_generate_with_receipt(...)` callsites全部維持原狀，不能順手切換。

Flag 關閉時走 legacy；flag 開啟時同一 operation 不得 fallback 回 legacy transport。`scripts/agy_seo_copy_pipeline.py:_generate_with_receipt` 的 `-runtime-retry-NN` 行為不得包住 V4 operation；canary 接線時必須讓 V4 ambiguous/blocked 結果直接 fail closed。舊 retry 的全面移除需另一張 migration card，不在 Repair 1 或首張 implementation 卡內。

## Implementation allowlist、tests、migration 與 rollback

下一張卡的唯一 production allowlist：

- 新增 `scripts/agy_gemini_v4_broker.py`（broker、ledger replay、anchor client 同一 module）
- 修改 `scripts/agy_gemini_runner.py` 的 `process_once` 單一 callsite與 feature flag
- 新增 `tests/test_agy_gemini_v4_broker.py`
- 修改 `tests/test_agy_gemini_outbox.py` 只補 runner canary/fail-closed contract
- 新增一個獨立 migration evidence root

明確禁止修改 `scripts/agy_seo_copy_pipeline.py`、outbox/coordinator production modules、app、articles、registry、metadata、publish、既有 evidence及任何 dependency。Implementation 順序：先 isolated module/fake tests → flag-off regression → single runner canary fake trace → independent review → 才能另議真實 CLI。不得 dual-spawn、automatic retry或 content recovery。

Rollback 只關閉 feature flag並回到切換前 code path；V4 ledger／anchor保留唯讀，不轉譯成舊 receipt、不補 terminal、不 replay target。若 flag-on operation 已留下 `BLOCKED/AMBIGUOUS/INVALID`，rollback 也不得觸發 legacy fallback。

## Repair 2 verification boundary

本 POC 只用 synthetic executable/local subprocess。Focused tests必須涵蓋 real broker crash-before-fork、fork/exec crash window、orphan target、missing/race exec、target FD table、wrong close/pass/extra FD、anchor loss/full replacement、完整合法 replay 表、terminal loss、legacy aliases、PID domain、illegal FSM與 matrix observable reversal。原 Reviewer probes必須顯示 `EXEC_CONFIRMED` 缺 terminal 為 `BLOCKED/1`，legacy aliases與非正 PID皆為 `INVALID/UNKNOWN`，同時 strict matrix仍由實際 controls維持綠燈；terminal loss、legacy alias或 PID control任一反轉時 matrix cell必須降級。POC連跑兩次 JSON byte-identical，且 privacy、allowlist、debug prefix、py_compile、focused tests與 `git diff --check`全綠後，才可交回原 Reviewer做最終 re-review；Repair author 不自審 GO。本輪是 Repair 2/2，若最終 re-review仍為 `NO_GO`，chain固定 `BLOCKED`，不得建立 Repair 3。

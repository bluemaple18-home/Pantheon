# Pantheon Gemini Reviewer V4 architecture｜Mainline candidate

狀態：`READY_FOR_REVIEW`。目前 production implementation 只存在於明確 opt-in 的 V4 broker 路徑；本文件不授權切換預設、retry、merge、deploy、publish 或 content recovery。

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

## Current production cutover boundary

目前只接一條 caller：`scripts/agy_gemini_runner.py:process_once` 由 `AGY_GEMINI_V4_BROKER=1` 選入 `scripts.agy_gemini_v4_broker:run_single_shot`。`scripts/agy_seo_copy_pipeline.py:GeminiClient._cli_transport`、HTTP transport、outbox enqueue、coordinator、其他 `_generate_with_receipt(...)` callsites全部維持原狀。

Flag-on 新 operation 固定選 `gemini_structured_api_v1`，canonical target request
保留完整 validated `role / prompt / response_schema`，CommandFrame digest／byte
count也綁定這份完整 request。顯式 `antigravity_cli_v1` 只允許讀取既有 ledger 做
replay；新 operation 在 broker process前 fail closed。舊 ledger replay仍使用原有
deterministic effective prompt重建 receipt identity。Flag-off legacy不經過任何
V4 renderer。

Effective-prompt ceiling 是 `384 KiB`：涵蓋 outbox 的 `256 KiB` task、
`64 KiB` schema與 `64 KiB` closed envelope budget，且低於目前 production
target 的 `ARG_MAX=1 MiB`。超過 ceiling 仍在 ledger／target fork 前拒絕。

Flag 關閉時走 legacy；flag 開啟時同一 operation 不得 fallback 回 legacy transport。`scripts/agy_seo_copy_pipeline.py:_generate_with_receipt` 的 `-runtime-retry-NN` 行為不得包住 V4 operation；canary 接線時必須讓 V4 ambiguous/blocked 結果直接 fail closed。舊 retry 的全面移除需另一張 migration card，不在 Repair 1 或首張 implementation 卡內。

V4 仍不得成為預設 transport。預設切換必須另有 migration commit，並在獨立 review、shadow run 與內容 schema／Reviewer 契約驗證後決定。

## Mainline verification 與 rollback

`CARD-CONTENT-GEMINI-V4-MAINLINE-001` 以 current source branch 為唯一 production truth，補上 concurrent-create loser 的 anchor provenance regression：競爭後 replay 使用哪一個 external anchor，`BrokerResult.final_anchor` 就必須回傳同一值，不得產生 `COMPLETE/1` 配上 stale `null` anchor。

本卡 synthetic acceptance 覆蓋 flag-off legacy、success、nonzero、timeout、malformed output、pre-fork abort、partial ledger、replay、digest mismatch與 concurrent duplicate。其後只執行一次真實 `agy 1.1.5` 合成公開 canary；durable ledger 為 `COMPLETE/1`、`EXEC_CONFIRMED` 恰一個、strict result schema通過，且沒有 failed record、retry或fallback。遮蔽 evidence 位於 `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/`。

後續 Activation-002 以真實文章 request 重現 `COMPLETE/1` 加
`JSON_INVALID`，證明 exactly-once 正常但 structured-generation envelope 在
runner adapter 遺失。對應 Repair 在 runner seam 補回 deterministic envelope，
不修改 broker／ledger／anchor／replay，也不授權第三次真實 canary。

Activation-004 在 envelope 與 schema diagnostics 已 Review 後仍得到
`COMPLETE/1 / SUCCESS / JSON_INVALID`。目前 production 嚴格 parser 不猜測內容；
broker 只把 parse failure 收斂成 closed、value-free 的 `EMPTY / UTF8_INVALID /
MARKDOWN_FENCE / WRAPPED_JSON / PARSE_ERROR_AT_END / PARSE_ERROR_OTHER`，
runner 再做獨立 allowlist。分類不保存 raw output、片段、offset 或 parser message，
也不代表 caller contract 已滿足。未取得下一次明確外呼確認前，狀態維持
`BLOCKED / DO_NOT_PROMOTE_DEFAULT`。

Rollback 只關閉 feature flag並回到切換前 code path；V4 ledger／anchor保留唯讀，不轉譯成舊 receipt、不補 terminal、不 replay target。若 flag-on operation 已留下 `BLOCKED/AMBIGUOUS/INVALID`，rollback 也不得觸發 legacy fallback。

## Long-form structured-output boundary

Canary-005 已把長文章失敗定位為
`COMPLETE/1 / SUCCESS / JSON_INVALID / PARSE_ERROR_AT_END`。這代表 exactly-once
process accounting完成，但 caller contract未完成。`agy 1.1.6 --print` 沒有
machine-enforced JSON Schema／structured-output interface；runner 的 canonical
schema envelope只能是 prompt instruction。

V4 不得用補括號、補引號、substring extraction、tolerant parser或同 operation
retry補足此能力缺口。若採原生 structured-output transport，必須建立新的
profile／receipt capability binding；若採 chunking，每個 chunk 必須有獨立
operation identity、ledger／anchor與 deterministic assembly contract。兩者都需
新的 architecture／acceptance boundary，不能在既有 single-shot profile內暗改。

## Provider-native target profile

`gemini_structured_api_v1` 保留相同 `run_single_shot`、ledger、anchor、replay與
receipt boundary，但把 target改成 digest-pinned獨立 adapter：

- public role／prompt／schema 以 canonical JSON走 stdin，不進 argv；
- broker先判定既有 ledger／anchor；純 replay不讀credential也不啟動target；
- 新 operation才呼叫runner提供的lazy opener，驗證owner-only file後以 inherited
  FD傳入；credential不進environment；
- 目前reviewed profile只接受單一owner-only API key檔；不解析key pool、不輪替、
  不fallback。Pantheon專用檔案使用deploy-time
  `AGY_GEMINI_V4_CREDENTIAL_FILE`指向，不把本機絕對路徑寫入共享設定；
- structured target environment不含 `HOME`；
- provider payload使用 `responseMimeType=application/json` 與
  versioned deterministic provider-schema projection v1 作
  `responseJsonSchema`；projection依 schema type限制 object／array／string／
  number／integer／boolean／null各自可用關鍵字，string `format`只接受
  `date/date-time/time`，enum值必須符合type且bool不冒充integer，numeric
  enum與bounds必須有限，integer enum與bounds固定為exact integer；
  caller-only `minLength/maxLength`保留在完整caller schema但不送provider；
  `maxOutputTokens`固定為32768；
- 一個 process只有一次 non-redirecting HTTP open，不 retry；
- 只接受 one candidate、`finishReason=STOP`與 one non-thought JSON object；
- target request、provider envelope、provider text及broker target stdout的JSON
  boundary都拒絕 `NaN/Infinity/-Infinity`，canonical serializer使用
  `allow_nan=False`；broker numeric gate也明確要求value與bounds有限，不轉
  `null`、不clamp、不容錯解析；
- adapter canonicalize後由 broker以完整 caller schema再次驗證；number／integer
  的 `minimum/maximum`由本地 gate強制，oversized array在 `maxItems` diagnostic
  後停止 child traversal。

Provider／HTTP失敗只允許 closed `target_diagnostic`。broker與runner各自持有
allowlist；unknown stderr、response body、prompt、credential與parser文字都不保存。

這個 profile不宣稱 provider internal exactly-once：network failure可能發生在
provider已接收 request之後，而 generateContent沒有 broker可驗證的 idempotency
key。此時 operation fail closed且禁止自動重送，publish count仍為 0。

## Cross-operation credential pool candidate

Quota sharding candidate新增明確opt-in
`AGY_GEMINI_V4_CREDENTIAL_POOL_FILE`，與既有
`AGY_GEMINI_V4_CREDENTIAL_FILE`互斥。Local owner-only manifest只含
`pool_id`、stable `slot_id`與各credential file path；key value仍分別存在
owner-only regular file，不進manifest、argv、environment、ledger或evidence。

選擇規則固定為：

1. 對slots依`slot_id` canonical sort；
2. 以`SHA-256(pool_id + NUL + operation_id)`選擇slot；
3. 同一operation永遠得到同一slot，不使用mutable round-robin cursor；
4. manifest與selected credential只在broker確認不是durable replay後lazy開啟；
5. new structured operation把非敏感`pool_id`、`slot_id`與manifest digest寫入
   receipt及恰一個`CREDENTIAL_SELECTED` ledger event；
6. target仍只收到一個credential FD與一次model POST。

429、timeout、transport error與nonzero都是同一operation的terminal結果；禁止
改選第二slot、retry或fallback。下一個新operation可由deterministic selection
選到不同project。舊ledger沒有`CREDENTIAL_SELECTED`仍保持replay相容。

這個pool只分攤不同Google Cloud project的quota；同project內多把key仍共享quota。
Local pool準備完成不代表activation或default promotion。

## Post-review and authentication boundary

Structured candidate `df6a33a8ce4af784ca6bfe6c2453de6eb7355f94` 已通過獨立
Review；evidence commit `3cb36a175146d217346609b2c54d59d2eed3c5fd`
記錄唯一一次 real structured canary：
`COMPLETE/1/SUCCESS/VALID`。這只證明 trusted executable snapshot 的 transport
completion、local ledger/anchor/replay accounting 與 strict caller result，
不能證明 provider internal model-call provenance。

截至 2026-07-25，Google官方文件已提供 Gemini Developer API OAuth／ADC與
Vertex AI ADC路徑；但本candidate尚未實作ADC，本機也沒有active gcloud
identity、configured project或ADC。現有API key僅能由Google control plane
判斷standard或authorization key，`AIza...`前綴不足以判定，因此型別固定記為
`UNKNOWN`，不得猜測。

Google官方API key文件並指出standard key將於2026年9月停止接受。default
promotion前必須完成下列其中一項：

1. 由正式control-plane證據確認使用authorization key；或
2. 另卡實作並Review Pantheon專用OAuth／ADC或Vertex workload identity。

ADC migration只可替換authentication header來源，不得改寫schema、provider
payload、單次HTTP、no-retry、no-redirect、ledger、receipt或fail-closed契約。
放量決策維持「不切預設」；後續shadow run或migration必須另卡、另證據、另
commit。

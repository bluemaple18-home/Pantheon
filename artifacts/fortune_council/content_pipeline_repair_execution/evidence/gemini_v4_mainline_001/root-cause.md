# Root cause

## Current production truth

- Source of truth：目前 source branch commit `ea7308bf14533c22bc83809bd72faeddcdeed6d0`。
- Production opt-in：只有 `AGY_GEMINI_V4_BROKER=1` 會讓 `scripts.agy_gemini_runner.process_once` 呼叫 `scripts.agy_gemini_v4_broker.run_single_shot`；flag off 維持 legacy `generate_json`。
- Production profile：runner 固定選 `antigravity_cli_v1`，要求 deployment-provided executable SHA-256，且只接受 profile、digest、operation、request、model 全綁定的 receipt。
- CLI identity：既有本機 binary 自報 `agy 1.1.5`；唯讀 `--help` 顯示非互動介面是 `--print <prompt>`。目前檔案 SHA-256 為 `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`。
- Baseline：`uv run --frozen pytest tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_outbox.py tests/test_agy_gemini_v4_architecture_probe.py -q` 為 `68 passed`。

## 舊 evidence 判定

可採信：

- `gemini_v4_agy_cli_compatibility_001` 已用 fake CLI 證明 closed argv、model mapping、empty stdin、environment/FD allowlist 與 privacy preflight。
- `gemini_v4_agy_cli_compatibility_repair_001` 已用 public seams 證明 production profile/digest binding、verified executable snapshot、post-fork cleanup 與 receipt provenance。
- 現行 source tests 可重現 strict replay legal table、partial/binding/hash-chain/anchor rejection、success/nonzero/timeout 與 flag-on no-fallback。

過期或不足：

- 舊 compatibility evidence 明確未執行真實 Gemini；不能證明目前 binary 的 runtime completion。
- 舊 verification 的 test count、base commit 與 isolated-worktree dependency 狀態不是目前 source branch 的驗證結果。
- 舊 canary 卡只是執行契約，不是 durable canary evidence。
- 舊 evidence 沒有 deterministic concurrent-create duplicate control，也沒有本卡要求的單一 synthetic matrix artifact。

## 排序假說

1. Concurrent-create loser 在 `FileExistsError` 分支以競爭後載入的 anchor 做 replay，卻把競爭前的 `existing_anchor` 放進 `BrokerResult.final_anchor`。若競爭前無 anchor、競爭後 ledger/anchor 已完整，結果可能是 `COMPLETE/1` 但 `final_anchor=null`。
2. 真實 `agy` snapshot 或 closed environment 仍可能與 `agy 1.1.5` runtime 不相容；version/help 只能證明 parser identity，不能證明 transport completion。
3. 若假說 1 被否證，production code 可能不需修改，剩餘缺口只在 matrix 與真實 canary evidence。

## 唯一目前 blocker

已以 public `run_single_shot` seam 建立 deterministic concurrent-create RED。重現結果是 replay 為 `COMPLETE/1`，但 `BrokerResult.final_anchor` 為 `null`；實際 durable external anchor 則是非空 SHA-256。根因是 `FileExistsError` 分支以競爭後載入值 replay，卻把競爭前的 stale `existing_anchor` 傳給 `_failure_result`。

最小修正讓 replay 與結果共用同一個 `replay_anchor`。單一測試由 RED 轉 GREEN，完整 focused suite 由 baseline `68 passed` 變為 `69 passed`；補上 malformed-output control 後 synthetic acceptance matrix 為 `21 passed`。

唯一真實 `agy 1.1.5` canary 隨後得到 durable `COMPLETE/1`、一個 `EXEC_CONFIRMED`、strict schema結果與無 failed record。技術 blocker 已解除；尚存治理邊界是獨立 Review、shadow run 與另立 migration commit，因此本卡不切預設、不放量。

## JSON_INVALID continuation（2026-07-24）

### 新 production truth

- Activation-004：`COMPLETE/1`、process outcome `SUCCESS`、replay
  `COMPLETE`，但 `result_validation=JSON_INVALID` 且沒有 inbox delivery。
- 同一 production transport 的歷史真實結果包含 `VALID`、
  `SCHEMA_MISMATCH` 與 `JSON_INVALID`；因此「agy 固定加入相同 wrapper」已被
  否證。
- durable failed record 依 privacy boundary 不保存 raw response；既有證據無法
  區分空輸出、encoding、Markdown fence／前後包裝、末端 parse failure 或其他
  syntax failure。

### 可證偽假說

1. 若是固定 Markdown fence／前後包裝，closed classifier 應回報
   `MARKDOWN_FENCE` 或 `WRAPPED_JSON`。
2. 若輸出可能被截斷，classifier 應回報客觀的 `PARSE_ERROR_AT_END`；此名稱不宣稱
   截斷原因。
3. 若是空輸出或 encoding 問題，應分別回報 `EMPTY` 或 `UTF8_INVALID`。
4. 其他不符合以上結構者只能回報 `PARSE_ERROR_OTHER`，不得保存 parser message、
   offset 或內容片段。

### Feedback loop 與最小修正

- RED：六種 broker stdout 分類加 runner persistence 共 7 cases，production
  尚無 `json_diagnostic`，結果 `7 failed`。
- GREEN：broker 只產 closed enum；runner 以另一份 allowlist 二次過濾。加入 forged
  string／object negative controls 後 `9 passed`。
- JSON 接受條件、schema、ledger、anchor、replay、process count 與 fallback 行為
  都未修改。

### 目前 blocker

本 candidate 只讓下一次失敗可被安全歸因，沒有證據可以選擇任何 tolerant parse
修正，因此狀態仍是 `BLOCKED`。下一次真實 canary 未獲本 continuation 授權。

## Output completion closure（2026-07-24）

Canary-005 得到 `COMPLETE/1 / SUCCESS / JSON_INVALID /
PARSE_ERROR_AT_END`。離線 trace 已排除 broker 2 MiB result ceiling、外層 timeout、
fence、wrapper、encoding、empty output與 legacy fallback是相容根因。

本機及官方 `agy 1.1.6` headless contract 只有文字型 `--print` 與 timeout，沒有
JSON Schema／structured-output enforcement；canonical schema 只能作為 prompt
instruction。legacy writer 以 schema retry 收斂格式錯誤，但 V4 exactly-once
禁止沿用。

因此可證明的架構根因是「transport 不提供 machine-enforced structured completion」，
而不是 broker parser defect。自動補 delimiter 會猜測並改寫 stdout；重試則違反
exactly-once，兩者都不是修復。完整判定見 `output-completion-root-cause.md`。

同一長文章 `JSON_INVALID` blocker 已達第三次，依 stop rule 不執行第四次 canary。
本卡內沒有安全 production patch；狀態維持 `BLOCKED / DO_NOT_PROMOTE_DEFAULT`。

## Provider-native repair continuation（2026-07-25）

最新授權允許在同一主卡內替換 V4 target capability。唯讀 production reference
顯示 legacy API client已使用 Gemini原生 `responseMimeType`／
`responseJsonSchema`；因此修復不是擴寫 parser，而是把這個 payload契約移入
exactly-once broker管理的獨立 adapter。

新 `gemini_structured_api_v1`：

- 不使用 `agy --print`
- 不從 prompt要求 schema enforcement
- 不把 credential放入 argv/env
- 不 retry 429/503或transport error
- 不跟 HTTP redirect
- 只有 provider `STOP`與本地 strict schema同時通過才交付

synthetic evidence已排除前次 `PARSE_ERROR_AT_END`的能力缺口；真實 structured API
尚未外呼，因此 rollout仍為 `DO_NOT_PROMOTE_DEFAULT`。

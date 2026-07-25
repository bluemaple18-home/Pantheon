# Pantheon Gemini V4：Antigravity CLI 相容契約

## 決策

`antigravity_cli_v1` 明確取代 V4 架構中「target argv 只能包含 executable、prompt 只能走 stdin」這一項假設。原因是本機 `agy 1.1.5` 的非互動介面要求 `--print <prompt>`；其餘單次 process、ledger、anchor、replay、FD 隔離與 fail-closed 契約不變。

## 封閉介面

production runner 的 flag-on新 operation固定選擇
`gemini_structured_api_v1`，不以 executable basename推論安全等級。
`antigravity_cli_v1` 只保留既有 durable ledger replay相容性；顯式指定它但沒有
既有 ledger時，runner在 broker process前 fail closed。所有 profile仍必須提供
部署時配置的 trusted executable SHA-256；未知 profile、缺少或不相符的 digest
一律在 target fork前 fail closed。`raw_stdin_v1` 只可由明確的 synthetic/test
caller使用，production設定無法抵達 synthetic profile。

```text
agy
--model <allowlisted label>
--mode plan
--sandbox
--log-file <operation-local temporary path>
--print-timeout <bounded seconds>
--print <PUBLIC_SANITIZED UTF-8 effective prompt>
```

模型映射只有：

- `gemini-3.5-flash` → `Gemini 3.5 Flash (Low)`
- `gemini-3.1-pro-preview` → `Gemini 3.1 Pro (Low)`

未知模型在 ledger 建立與 target fork 前拒絕。CommandFrame v2 綁定 profile、CLI model label、payload class、prompt SHA-256、prompt byte length、executable digest 與 timeout；production receipt 另綁定 operation、item、attempt、外部 request SHA-256、request model、`antigravity_cli_v1` profile 與 trusted executable digest，runner 只接受完全相符的 receipt。

production runner 不得直接把 outbox 的 user task 當成 effective prompt。Flag-on
路徑必須以 closed role map deterministic 渲染：

```text
<writer 或 reviewer role instruction>
禁止使用任何工具或讀取工作區。
輸出必須是單一 JSON object，不得有 Markdown code fence。
JSON Schema：<ensure_ascii=false、sort_keys=true、compact JSON>

任務：
<sanitized user task>
```

CommandFrame 的 prompt SHA-256 與 byte length 綁定上述完整 UTF-8 effective
prompt；production receipt 的 request SHA-256 仍綁定原始 outbox request。兩個
digest 各自證明 transport bytes 與 queue identity，不得互相替代。Flag-off legacy
路徑不經過 V4 renderer。

Size contract 固定為：

- sanitized user task：
  `256 KiB`
- canonical response schema：
  `64 KiB`
- closed role／instruction envelope budget：
  `64 KiB`
- broker effective-prompt ceiling：
  `384 KiB`

這個 ceiling 低於目前 production target 的 `ARG_MAX=1 MiB`；超過 384 KiB 仍在
target fork 前 fail closed。Outbox 的既有 raw task／schema public limits不縮減。

## 資料與程序邊界

- effective prompt 進入 argv 是 `agy --print` 的產品限制，因此 role instruction、
  canonical schema 與 user task 都必須是 closed／公開且已清理的資料。
- 禁止本機絕對私密路徑、`.work/`、API key、Bearer token、Google key、private key 與 GitHub token marker；驗證失敗時 target process count 為 0。
- prompt 不寫入 command frame、ledger、anchor、control frame或證據摘要；這些位置只保存 hash、byte count 與 payload classification。
- `--log-file` 使用 broker process 內的 operation-local temporary directory，target 結束後立即清理，不作為交付證據。
- target stdin 為空；除 stdin/stdout/stderr 外不繼承 file descriptor。
- target environment 只允許 `HOME`、`LANG`、`LC_ALL`、`PATH`、`TMPDIR` 與 macOS runtime 的 `__CF_USER_TEXT_ENCODING`。不繼承 `GEMINI_API_KEY`、token 或其他 parent environment。
- `HOME` 提供既有本機 CLI 設定與登入狀態；本相容層不讀取、不複製也不記錄憑證內容。

`raw_stdin_v1` synthetic/test profile 維持 fake target 的原始 stdin 行為，但其 receipt 不含 production profile binding，production runner 必須拒絕，且不得把它當成生產 Gemini transport。

## Completion provenance 限制

本相容層可證的成功範圍僅是：已雜湊並封存的 trusted executable snapshot 完成一次 transport、exit status 為 0，且 stdout 通過 JSON schema。`agy 1.1.5` 未提供可由本 broker 獨立驗證的供應商內部 model-call provenance；因此 receipt 與 `caller_contract_satisfied` 不宣稱 Gemini 供應商內部模型呼叫確實發生，只代表上述 trusted transport completion。

## Canary 邊界

`CARD-CONTENT-GEMINI-V4-MAINLINE-001` 在 fake CLI synthetic matrix 全綠後，依獨立主線授權執行了一次真實 `agy 1.1.5` canary。輸入是單一合成公開 JSON request；結果為 durable `COMPLETE/1`、一個 `EXEC_CONFIRMED`、strict schema通過，且沒有 retry、fallback、failed record、文章或發布資料讀寫。

遮蔽 evidence 位於 `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/real-canary.json`。這個結果只證明本機 trusted transport completion 與 ledger/anchor/replay binding，不提升 provider internal call provenance，也不授權把 V4 切為預設 transport。

Activation-002 以真實文章 payload 得到 durable `COMPLETE/1` 與
`PROCESS_TERMINAL/SUCCESS`，但 caller diagnostic 是 `JSON_INVALID`。根因是當時
runner 只傳 user task，遺失 legacy CLI 的 role／JSON-only／schema envelope。
Structured-envelope Repair 只以 synthetic runner seam 與既有 broker digest tests
驗證；本文件不授權第三次真實外呼。

Activation-004 在 structured envelope 與 schema diagnostic Repair 通過獨立 Review
後，仍得到 durable `COMPLETE/1`、`PROCESS_TERMINAL/SUCCESS` 與
`JSON_INVALID`。由於同一路徑也曾得到 `VALID` 與 `SCHEMA_MISMATCH`，不能假設
agy 固定加入同一種 wrapper，也不得在沒有證據時自動剝除 code fence 或前後文字。

`JSON_INVALID` 只允許 broker 產生一個 value-free closed diagnostic：

- `EMPTY`
- `UTF8_INVALID`
- `MARKDOWN_FENCE`
- `WRAPPED_JSON`
- `PARSE_ERROR_AT_END`
- `PARSE_ERROR_OTHER`

runner 以獨立 allowlist 二次過濾，且只在 `result_validation=JSON_INVALID` 時保存該
enum。不得保存 raw bytes、文字片段、parser message、offset 或未知字串。這項診斷
不放寬嚴格 `json.loads`／schema 契約、不自動修復輸出，也不授權新外呼。

## Structured-output capability boundary

Canary-005 在 `agy 1.1.6` 得到
`COMPLETE/1 / SUCCESS / JSON_INVALID / PARSE_ERROR_AT_END`。離線 trace 排除 broker
result ceiling、外層 timeout、fence與wrapper是相容根因。

`agy 1.1.6` 的 headless interface 只有文字型 `--print <prompt>` 與
`--print-timeout`；官方 help／文件沒有 JSON Schema、structured-output、
response MIME type或 output-token ceiling參數。因此 effective prompt 內的
canonical schema 是 instruction，不是 transport enforcement。

這個 profile 不得以 tolerant parser、自動補 delimiter或同 operation retry，把
不完整 stdout 轉成 caller success。長文章 V4 promotion 必須等待另一個能
machine-enforce structured output的 transport，或新的 bounded chunk operation
architecture；目前 legacy 維持預設。

## Long-form replacement profile

長文章候選改用 `gemini_structured_api_v1`，不再把 `agy --print` 當 promotion
target。此 profile重用既有 production API payload的
`responseMimeType=application/json`，並以 provider-schema projection v1產生
`responseJsonSchema`：完整 caller schema仍綁入target request與broker local
validation；projection依type只保留官方subset，string `format`封閉為
`date/date-time/time`，enum值必須符合type且bool不等於integer，number值與bounds
必須有限，integer enum／bounds必須是exact integer。caller-only
`minLength/maxLength`不送往provider，但仍留在完整caller schema由broker驗證。
target request、provider envelope／text及broker target stdout一律strict parse並
拒絕`NaN/Infinity/-Infinity`；兩端canonical serializer都使用`allow_nan=False`，
不轉null、不clamp、不tolerant parse。
此 profile移除 legacy 429/503 retry並加上：

- digest-pinned adapter
- new operation lazy credential FD（禁止 argv/env；durable replay不讀credential）
- fixed endpoint與model allowlist
- `maxOutputTokens=32768`
- redirect refusal
- `finishReason=STOP` gate
- broker-side independent schema validation
- closed target diagnostics

`antigravity_cli_v1` 保留既有 ledger／receipt replay相容性與 synthetic regression，
但在 structured real canary通過前不得再用來主張長文章可放量。

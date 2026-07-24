# Provider-native structured transport design

Date: 2026-07-25

Candidate status: READY_FOR_REVIEW

Rollout: DO_NOT_PROMOTE_DEFAULT

## Root decision

保留 `scripts.agy_gemini_v4_broker:run_single_shot` 作為唯一 V4 process owner，
把不具 structured-output 保證的 `agy --print` production target 替換成獨立
`gemini_structured_api_v1` adapter。

這不是第二條文章 pipeline。outbox、job identity、ledger、anchor、replay、
inbox與 legacy flag-off path 均不變；只有 flag-on broker 的 target capability
新增一個 provider-native profile。

## Reused production truth

唯讀 legacy reference 已有可用的 Gemini API payload：

- `systemInstruction`
- single user `contents`
- `generationConfig.responseMimeType=application/json`
- `generationConfig.responseJsonSchema=<caller schema>`
- `thinkingConfig.thinkingLevel=LOW`

新 adapter 重用這個 payload shape，不搬運 legacy retry loop。官方 structured
output 文件亦確認 REST API 可用 JSON Schema 約束輸出：

- `https://ai.google.dev/gemini-api/docs/structured-output`
- `https://ai.google.dev/api/generate-content`

## Stable module boundary

```text
outbox public request
  -> runner validates request and closed provider-schema subset
  -> runner opens owner-only credential file (value unread)
  -> run_single_shot binds request/profile/model/adapter digest
  -> broker snapshots digest-pinned adapter
  -> credential passes only as inherited FD
  -> adapter performs one non-redirecting HTTPS request
  -> adapter requires one candidate + finishReason=STOP
  -> adapter emits canonical JSON object
  -> broker independently parses and validates caller schema
  -> inbox only on durable COMPLETE/1 + VALID
```

## Credential contract

- deploy-time input：`AGY_GEMINI_V4_CREDENTIAL_FILE`
- 必須是 current UID 擁有的 regular file，禁止 symlink，group/other permission
  必須為 0，大小限制 20–512 bytes。
- runner 只 `open/fstat`，不把 value 放入 Python string、argv、environment、
  request、ledger、anchor、receipt、failed record或 evidence。
- broker 僅把 descriptor 傳給 verified adapter；structured target environment
  不含 `HOME`、API key或 unrelated variables。
- adapter 讀取後關閉 FD；HTTP header 只存在 target process memory。

本卡不建立、搬移、登入、輪替或保存真實 credential。

## HTTP and completion contract

- endpoint 固定為 Gemini Developer API `v1beta ...:generateContent`；不得由 job
  payload或 environment改寫。
- model 使用 closed allowlist。
- application request 次數固定為 1；429/503/timeout皆不 retry。
- redirect handler 固定拒絕 redirect，避免隱性第二個 HTTP request。
- `maxOutputTokens=32768`。
- 只有 `finishReason=STOP`、恰一個 candidate、恰一個非 thought text part且 text
  是 JSON object才可輸出。
- broker 再以原 caller schema驗證；provider structured output不取代本地 gate。

## Closed diagnostics

adapter stderr 只能輸出一個 closed code。broker 只有在 structured profile、
`CLI_NONZERO` 且 code 位於獨立 allowlist時，才把
`target_diagnostic` 交給 runner；runner再以相同 closed boundary過濾。

可維運分類涵蓋：

- credential/request precondition
- auth/rate-limit/provider unavailable／transport
- provider completion（`OUTPUT_TRUNCATED`、`OUTPUT_BLOCKED`、`OUTPUT_INCOMPLETE`）
- candidate／parts／JSON envelope
- response-size與 internal failure

provider body、prompt、credential、parser message與未知 stderr一律不保存。

## Exactly-once limit

ledger 可證明每個 operation 最多一個 adapter process；adapter code與 tests可證明
每個 process只有一次 application-level HTTP open，且不跟 redirect。

Gemini generateContent 未提供本 broker 可驗證的 idempotency key。若連線在
provider 可能已接收 request 後中斷，ledger只能記錄一個失敗 target process，
不得宣稱 provider internal call count。系統會 fail closed且不自動重送；文章也
不會發布。人工若建立新 operation，可能產生額外 provider cost，但不會重複 publish。

## Rollout sequence

1. local synthetic與 affected suites
2. independent read-only Review
3. 一個公開、遮蔽、明確確認後的 real structured canary
4. limited shadow：仍不 publish
5. 另行決定 V4 profile deployment與 default migration

在第 3–5 步通過前，legacy仍是預設，`agy --print` 不再作為長文章 promotion
候選。

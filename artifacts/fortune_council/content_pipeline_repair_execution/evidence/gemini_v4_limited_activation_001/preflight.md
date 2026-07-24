# V4 Limited Activation Preflight

## 固定基準

- final-sync candidate:
  `4c4211c2ff3961f24d48e75a6a7ef16c53a4da08`
- source brief:
  `artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/brief.json`
- source SHA-256:
  `209ee6b4a8c2233620b6c98b15c63c712ca96297c10b3dc85ca6160bb345582c`
- source mode / article count: `create / 1`

## 已完成的離線 staging

1. 固定 brief 已複製到 repo 外一次性 runtime。
2. `scripts.agy_gemini_outbox tick` 只建立第一筆 writer request。
3. tick 如預期回傳 `pending`（exit 75）。
4. request 已通過 strict rebuild／digest／public-data validation。
5. 沒有執行 runner、broker target 或任何 agy generation。

目前 runtime 只含：

- brief copy
- public brief
- pending writer operation receipt
- sanitized outbox request

目前不存在：

- V4 ledger
- external anchor
- processing record
- inbox response
- archive record
- failed record
- candidate article
- review output

## 若取得確認，唯一外部動作

執行一次 `scripts.agy_gemini_runner process-once`：

- `AGY_GEMINI_V4_BROKER=1`
- production entrypoint:
  `scripts.agy_gemini_v4_broker:run_single_shot`
- target profile: `antigravity_cli_v1`
- role / model: `writer / gemini-3.5-flash`
- model label: `Gemini 3.5 Flash (Low)`
- prompt transport: `--print <sanitized prompt>`
- timeout: `120000 ms`
- maximum target process count: `1`
- retry / fallback / automatic resend: `0`

Broker 會在 repo 外 runtime 寫入：

- 一份 durable ledger
- 一份 external anchor
- 成功時一份 inbox response與一份 archive request
- 失敗時一份 failed record與一份 archive request

不會執行 pipeline 的下一個 tick，因此不會產生 candidate article，也不會呼叫
publisher、修改 registry、生成頁、sitemap 或 feed。

## Executable identity

- redacted label: `local-agy-snapshot`
- current SHA-256:
  `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`
- prior verified self-reported version: `1.1.5`
- digest 與既有真實 V4 canary 證據一致。
- 未執行登入、版本查詢或設定修改。

## 邊界

- prompt 不寫入 evidence。
- credential 與完整環境不寫入 evidence。
- agy log 不保存。
- user confirmation 前 external invocation 維持 `0`。

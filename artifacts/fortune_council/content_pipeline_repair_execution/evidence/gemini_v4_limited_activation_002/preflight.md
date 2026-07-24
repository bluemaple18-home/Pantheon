# Gemini V4 Limited Activation-002 Preflight

## 固定基準

- repaired candidate:
  `a93ba6fd74223427c03aa39c98aa0705c9aaf0b6`
- independent Review-2 evidence:
  `c8246ccf609558abf35563d0f71c6b4363f75d5d`
- Review-2 verdict:
  `DELIVERED_CANDIDATE / GO`
- source brief:
  `artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/brief.json`
- source SHA-256:
  `209ee6b4a8c2233620b6c98b15c63c712ca96297c10b3dc85ca6160bb345582c`
- source mode / article count:
  `create / 1`

## Fresh dry-run

- runtime label:
  `pantheon-v4-activation-002.NhXHSf`
- fresh run identity:
  `pantheon-v4-limited-activation-002-20260724`
- namespace:
  `175f0f3eb5713c3ca65226ec`
- job ID:
  `e64cb371f426c406af15d136728b659ffe18b7d2`
- request SHA-256:
  `e64cb371f426c406af15d136728b659ffe18b7d2f95ff7060a8127f5c5d4fce0`
- prior blocked job reused:
  `false`
- prior runtime reused:
  `false`

Outbox `tick` 如預期回傳 pending（exit 75），只建立一筆 writer request。
request 已通過 strict rebuild、digest 與 public-data validation。

文章 prompt 因沿用同一份公開 brief，內容與 Activation-001 相同；完整 request
因 fresh namespace 而具有不同 job ID 與 request digest。此差異在 final payload
confirmation 時明確揭露。

## 目前 runtime 狀態

存在：

- fresh brief copy
- public brief
- pending writer operation receipt
- 一筆 sanitized outbox request

不存在：

- V4 ledger
- external anchor
- processing record
- inbox response
- archive record
- failed record
- candidate article
- review output

## 若取得 final confirmation，唯一外部動作

執行一次 `scripts.agy_gemini_runner process-once`：

- external service:
  existing local Antigravity `agy` CLI
- `AGY_GEMINI_V4_BROKER=1`
- production entrypoint:
  `scripts.agy_gemini_v4_broker:run_single_shot`
- target profile:
  `antigravity_cli_v1`
- role / model:
  `writer / gemini-3.5-flash`
- model label:
  `Gemini 3.5 Flash (Low)`
- prompt transport:
  `--print <sanitized prompt>`
- timeout:
  `120000 ms`
- maximum target process count:
  `1`
- retry / fallback / automatic resend:
  `0`

只允許在 repo 外 runtime 寫入 durable ledger、external anchor，以及單一
inbox/archive 或 failed/archive 結果。不執行下一個 pipeline tick，因此不產生
candidate article，也不呼叫 publisher。

## Executable identity

- redacted label:
  `local-agy-snapshot`
- SHA-256:
  `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`
- prior verified self-reported version:
  `1.1.5`
- current digest 與前次 verified identity 一致。
- 未執行登入、版本查詢或設定修改。

## Privacy

- prompt 不寫入 evidence。
- raw response、credential、完整環境與 executable path 不寫入 evidence。
- agy log 不保存。
- final confirmation 前 external invocation 維持 `0`。

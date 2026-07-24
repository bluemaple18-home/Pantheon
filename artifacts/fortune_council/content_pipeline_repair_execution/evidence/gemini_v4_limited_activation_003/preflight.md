# Gemini V4 Limited Activation-003 Preflight

## 固定基準

- structured-envelope Repair candidate:
  `bccd800ebf06348449d718c33036ad1c712dbef7`
- independent Review-2 evidence:
  `534b50dff98b0f836a83889d32b807211fe3377d`
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
  `pantheon-v4-activation-003.QlfanG`
- fresh run identity:
  `pantheon-v4-limited-activation-003-20260724`
- namespace:
  `da002eb9f94052331f210932`
- job ID:
  `35b808faa055a70ba92d40f5186535de6ea5590f`
- request SHA-256:
  `35b808faa055a70ba92d40f5186535de6ea5590fc3ee3d0d8b3164c00976e46b`
- prior blocked jobs reused:
  `false`
- prior runtimes reused:
  `false`

Outbox `tick` 如預期回傳 pending（exit 75），只建立一筆 writer request。
Request 已通過 strict rebuild、digest 與 public-data validation。

## Structured effective prompt

- role:
  `writer`
- model:
  `gemini-3.5-flash`
- sanitized user task SHA-256:
  `15f031649594c55a6f6fc389a00e6cf03c446004bf1453e2194e3c6a5b0063c7`
- canonical schema SHA-256:
  `fb499dbe0020b429754b769a19173dc138d08069c43a5616ebdb989f1334f6a2`
- effective prompt SHA-256:
  `1317321d6b33be04da71a547c14acb1c6e52f9e5c7fed78528777113bccd48be`
- task / schema / effective bytes:
  `2555 / 1211 / 4028`
- broker ceiling:
  `393216 bytes`

Dry-run 已驗：

- closed writer role instruction
- no-tool／no-workspace
- single JSON object／no Markdown code fence
- canonical compact response schema
- exact sanitized user task suffix

Prompt 與 schema 內容不寫入 evidence。

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
  `--print <structured sanitized effective prompt>`
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
- current digest 與 verified identity 一致。
- 未執行登入、版本查詢或設定修改。

## Privacy

- prompt／schema 不寫入 evidence。
- raw response、credential、完整 environment 與 executable path 不寫入
  evidence。
- agy log 不保存。
- final confirmation 前 external invocation 維持 `0`。

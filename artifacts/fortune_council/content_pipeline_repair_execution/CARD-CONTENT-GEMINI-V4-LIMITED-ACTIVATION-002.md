# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-002

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-002`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-002`
- ownership: `v4_limited_activation_only`
- strictness: `strict`
- risk: `high`
- status: `BLOCKED`
- decision: `BLOCKED`

## 基準

- repaired candidate:
  `a93ba6fd74223427c03aa39c98aa0705c9aaf0b6`
- independent Review-2 evidence:
  `c8246ccf609558abf35563d0f71c6b4363f75d5d`
- Review-2 verdict:
  `DELIVERED_CANDIDATE / GO`

## 目標

以全新 run identity、namespace、job ID、request digest 與 repo 外 runtime，
準備第二筆真實文章 payload 的 V4 limited canary。先完成離線 dry-run 與 final
payload disclosure；任何 Gemini／agy 外呼前，必須取得使用者對工具、對象、
payload 與影響的明確確認。

## 固定公開來源

- source:
  `artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/brief.json`
- 來源主題:
  `土星回歸`
- 只以來源的公開內容建立 sanitized writer request。
- evidence 只保存 hash、byte count、role、model、job ID、schema metadata 與
  closed diagnostic；不保存 prompt、完整 response、credential、完整環境或 CLI
  log。

## Freshness 契約

- 不重用 Activation-001 runtime。
- 不重送 job `1ad663e7f17477d0cee5056260427b4b360b7fab`。
- 使用全新 opaque run identity 產生不同 namespace、job ID 與 request digest。
- 只允許一筆 pending writer request。

## 執行模型

1. 在 repo 外建立一次性 run／queue directory。
2. 複製固定 brief，使用全新 run identity 執行一次 outbox `tick`，只建立 writer
   request；不得呼叫 Gemini。
3. 驗證 request strict schema、public-data filter、fresh identity、digest 與唯一性。
4. 鎖定 V4 executable 的 redacted label 與 SHA-256；不登入、不查詢或修改設定。
5. 對使用者展示 final payload 內容、工具、模型、最大 process count 與副作用，
   取得明確確認。
6. 確認後最多執行一次 `scripts.agy_gemini_runner process-once`，且
   `AGY_GEMINI_V4_BROKER=1`。
7. 驗證 ledger、anchor、archive／inbox 或 failed record；不得 retry、fallback、
   第二次 process 或 pipeline continuation。

## 唯一允許寫入

- 本卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_002/**`
- repo 外一次性暫存 run／queue directory。

## 禁止

- 不修改 production code、tests、文章、registry、metadata、sitemap、feed、
  prerender、publisher 或 automation。
- 不呼叫 `scripts.agy_content_publisher`。
- 不 push、deploy、publish、切換預設 transport 或移除 legacy。
- 不修改登入、憑證或全域 CLI 設定。
- flag-on 失敗不得 legacy fallback。
- final payload 確認前不得執行 Gemini／agy generation。
- 同一 blocker 第三次失敗立即停止。

## Required evidence

- `preflight.md`
- `payload-manifest.json`
- `verification.txt`
- `decision.md`
- `changed-files.txt`

## 決策

外呼前只能：

- `AWAITING_EXTERNAL_CONFIRMATION`
- `BLOCKED`

外呼後只能：

- `DELIVERED_CANDIDATE / READY_FOR_ACTIVATION_REVIEW`
- `BLOCKED`

本卡的 candidate 或 GO 都不代表整合、上線、預設 promotion 或 legacy removal。

## 離線 Gate 結果

- source brief SHA-256:
  `209ee6b4a8c2233620b6c98b15c63c712ca96297c10b3dc85ca6160bb345582c`
- staged brief SHA-256:
  `ce38b9edfedbb2de2e79558615db8a2fb48831bc397cf3f55ab182da1bd487ac`
- staged job ID:
  `e64cb371f426c406af15d136728b659ffe18b7d2`
- prior blocked job reused:
  `false`
- role / model:
  `writer / gemini-3.5-flash`
- prompt bytes / schema bytes:
  `2555 / 1211`
- sanitized request validation:
  `PASS`
- current external invocation:
  `0`
- current ledger / anchor / inbox / archive / failed record:
  `absent`
- decision:
  `BLOCKED`

## 真實執行結果

- user final confirmation:
  `received`
- external target invocation:
  `1`
- retry / fallback / automatic resend:
  `0`
- durable replay:
  `COMPLETE / 1`
- ledger terminal outcome:
  `SUCCESS`
- runner result:
  `failed / V4BrokerFailure`
- safe result validation:
  `JSON_INVALID`
- inbox:
  `absent`
- failed／archive／ledger／anchor:
  `present`
- blocker:
  V4 outbox request 雖含 role、prompt 與 response schema，但 production runner
  只把 raw prompt 傳給 agy；沒有像 legacy CLI transport 一樣把 role instruction、
  JSON-only 約束與 schema 渲染進 effective CLI prompt。
- final decision:
  `BLOCKED`

# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-003

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-003`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-003`
- ownership: `v4_limited_activation_only`
- strictness: `strict`
- risk: `high`
- status: `IN_PROGRESS`
- decision: `AWAITING_EXTERNAL_CONFIRMATION`

## 基準

- structured-envelope Repair candidate:
  `bccd800ebf06348449d718c33036ad1c712dbef7`
- independent Review-2 evidence:
  `534b50dff98b0f836a83889d32b807211fe3377d`
- Review-2 verdict:
  `DELIVERED_CANDIDATE / GO`

## 目標

以全新 run identity、namespace、job ID、request digest 與 repo 外 runtime，
準備 structured-envelope 修正後的第三筆 V4 limited canary。先完成離線
dry-run、effective prompt verification 與 final payload disclosure；任何
Gemini／agy 外呼前，必須取得使用者對工具、對象、payload 與影響的明確確認。

## 固定公開來源

- source:
  `artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/brief.json`
- topic:
  `土星回歸是什麼`
- 只以來源的公開內容建立 sanitized writer request。
- Evidence 只保存 request／effective-prompt hash、byte count、role、model、job ID、
  schema metadata 與 closed diagnostic；不保存 prompt、完整 response、credential、
  完整 environment 或 CLI log。

## Freshness 契約

- 不重用 Activation-001／002 runtime。
- 不重送 job：
  - `1ad663e7f17477d0cee5056260427b4b360b7fab`
  - `e64cb371f426c406af15d136728b659ffe18b7d2`
- 使用全新 opaque run identity 產生不同 namespace、job ID 與 request digest。
- 只允許一筆 pending writer request。

## Structured-envelope 契約

Flag-on effective prompt 必須 deterministic 包含：

- closed writer role instruction
- no-tool／no-workspace
- single JSON object／no Markdown code fence
- canonical compact response schema
- sanitized user task

CommandFrame prompt digest／byte count 綁 effective prompt；receipt request SHA 綁
原 outbox request。

## 執行模型

1. 在 repo 外建立一次性 run／queue directory。
2. 複製固定 brief，使用全新 run identity 執行一次 outbox `tick`，只建立 writer
   request；不得呼叫 Gemini。
3. 驗證 request strict schema、public-data filter、fresh identity、digest、唯一性
   與 effective prompt envelope／size。
4. 鎖定 V4 executable redacted label 與 SHA-256；不登入、不查詢或修改設定。
5. 對使用者展示 final payload、模型、effective envelope、最大 process count 與
   副作用，取得明確確認。
6. 確認後最多執行一次 `scripts.agy_gemini_runner process-once`，且
   `AGY_GEMINI_V4_BROKER=1`。
7. 驗證 ledger、anchor、archive／inbox 或 failed record；不得 retry、fallback、
   第二次 process 或 pipeline continuation。

## 唯一允許寫入

- 本卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_003/**`
- repo 外一次性暫存 run／queue directory。

## 禁止

- 不修改 production code、tests、docs、文章、registry、metadata、sitemap、feed、
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
  `765ffb7c4c3aeee1f04b7652544d9bd427484d79d735f6716b10f725f964b547`
- staged job ID:
  `35b808faa055a70ba92d40f5186535de6ea5590f`
- prior blocked jobs reused:
  `false`
- role / model:
  `writer / gemini-3.5-flash`
- user task / schema / effective prompt bytes:
  `2555 / 1211 / 4028`
- effective prompt ceiling:
  `393216`
- structured envelope validation:
  `PASS`
- sanitized request validation:
  `PASS`
- current external invocation:
  `0`
- current ledger / anchor / inbox / archive / failed record:
  `absent`
- decision:
  `AWAITING_EXTERNAL_CONFIRMATION`

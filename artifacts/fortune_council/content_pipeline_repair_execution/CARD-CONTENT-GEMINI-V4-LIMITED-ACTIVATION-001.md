# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-001

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-001`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-001`
- ownership: `v4_limited_activation_only`
- strictness: `strict`
- risk: `high`
- status: `IN_PROGRESS`
- decision: `PENDING`

## 目標

以 final-sync candidate
`4c4211c2ff3961f24d48e75a6a7ef16c53a4da08`
為唯一程式基準，準備一筆真實文章 payload 的 V4 limited activation。
先完成離線 payload／副作用 Gate；任何 Gemini／agy 外呼前必須取得使用者明確確認。

## 固定真實輸入

- source:
  `artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/brief.json`
- 使用來源的公開內容建立 sanitized outbox request。
- evidence 只保存 hash、byte count、role、model、job ID 與 schema metadata；
  不保存 prompt、完整 response、credential 或完整環境。

## 執行模型

1. 在 repo 外的暫存 run directory 複製固定 brief。
2. 以 `scripts.agy_gemini_outbox tick` 只建立第一筆 sanitized request；
   此步不得呼叫 Gemini。
3. 驗證 request schema、public-data filter、job ID 與 digest。
4. 鎖定 V4 executable 路徑的 redacted label 與 SHA-256，不執行登入或設定修改。
5. 向使用者回報精確外部效果並取得確認。
6. 確認後最多執行一次 `scripts.agy_gemini_runner process-once`，
   且 `AGY_GEMINI_V4_BROKER=1`。
7. 驗 ledger、anchor、archive／inbox 或 failed record；不得 retry、fallback 或
   第二次 process。

## 唯一允許寫入

- 本卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_001/**`
- repo 外一次性暫存 run／queue directory。

## 禁止

- 不修改 production code、文章、registry、metadata、sitemap、feed、prerender、
  publisher 或 automation。
- 不呼叫 `scripts.agy_content_publisher`。
- 不 push、deploy、publish、commit 生成文章或切換預設 transport。
- 不修改登入、憑證、全域 CLI 設定。
- flag-on 失敗不得 legacy fallback。
- 使用者確認前不得執行 Gemini／agy generation。
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

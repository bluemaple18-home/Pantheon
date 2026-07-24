# CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-004

- card_id: `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-004`
- chain_id: `CONTENT-GEMINI-V4-LIMITED-ACTIVATION-004`
- ownership: `v4_limited_activation_only`
- strictness: `strict`
- risk: `high`
- status: `IN_PROGRESS`
- decision: `AWAITING_EXTERNAL_CONFIRMATION`

## 基準

- schema diagnostic Repair-3:
  `406ec22631adde0a3c30fd753fa0be4a0baa55a9`
- independent Review-3:
  `24272917b9506630f367a252272d46ad4335a7e9`
- Review verdict:
  `DELIVERED_CANDIDATE / GO`
- source Activation-003:
  `BLOCKED / SCHEMA_MISMATCH`

## 目標

以全新 run identity、namespace、job ID、request digest 與 repo 外 runtime，準備
第四筆 V4 limited canary。若 Gemini 輸出符合 schema，驗證 caller delivery；
若仍為 schema mismatch，只保存 Repair-3 已獨立 Review 的 bounded
keyword／schema-defined path，不保存 raw response 或 instance value。

## 固定公開來源

- source:
  `artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/brief.json`
- topic:
  `土星回歸是什麼`
- 只以來源公開內容建立 sanitized writer request。
- 不保存 prompt、完整 response、instance value、validator message、credential、
  完整 environment、executable path 或 CLI log。

## Freshness

- 不重用 Activation-001／002／003 runtime 或 job。
- 使用全新 opaque run identity 產生不同 namespace、job ID 與 request digest。
- 只允許一筆 pending writer request。

## 執行

1. 在 repo 外建立一次性 run／queue directory。
2. 複製固定 brief，只改全新 run identity；執行一次 outbox `tick` 建立 writer
   request，不呼叫 Gemini。
3. 驗證 request strict schema、public-data filter、fresh identity、digest、
   structured envelope、response schema、唯一性與 effective prompt size。
4. 鎖定既有 agy executable digest；不登入、不修改任何設定。
5. 展示 final payload、模型、最大 process count、副作用與 diagnostic boundary，
   再取得使用者明確確認。
6. 確認後最多執行一次 flag-on `process-once`。
7. 驗證 ledger、anchor、archive／inbox 或 failed record；不 retry、fallback、
   第二次 process 或 pipeline continuation。

## 唯一允許寫入

- 本卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_limited_activation_004/**`
- repo 外一次性 run／queue directory。

## 禁止

- 不修改 production code、tests、docs、response schema、structured envelope、文章、
  registry、metadata、sitemap、feed、prerender、publisher 或 automation。
- 不呼叫 `scripts.agy_content_publisher`。
- 不 push、deploy、publish、切換預設 transport 或移除 legacy。
- 不修改登入、憑證或全域 CLI 設定。
- flag-on 失敗不得 legacy fallback。
- final payload 確認前不得執行 Gemini／agy generation。
- 無論成功、失敗或不確定都不得重送。

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

本卡不代表上線、預設 promotion、legacy removal 或文章發布。

## 離線 Gate 結果

- source brief SHA-256:
  `209ee6b4a8c2233620b6c98b15c63c712ca96297c10b3dc85ca6160bb345582c`
- staged brief SHA-256:
  `2c1d4dbdeaf8df739e8060c7d1ebfa8d646efe5dad5a59825949c47b2a4da0fe`
- staged job ID:
  `a520fbf466d750acec225d77f129151affd4e04b`
- namespace:
  `bbf1402b3f1a178f09e02f61`
- prior blocked jobs reused:
  `false`
- role / model:
  `writer / gemini-3.5-flash`
- user task / schema / effective prompt bytes:
  `2555 / 1211 / 4028`
- effective prompt ceiling:
  `393216`
- structured envelope／sanitized request validation:
  `PASS / PASS`
- safe schema diagnostics Review:
  `DELIVERED_CANDIDATE / GO`
- current external invocation:
  `0`
- current ledger / anchor / inbox / archive / failed record:
  `absent`
- decision:
  `AWAITING_EXTERNAL_CONFIRMATION`

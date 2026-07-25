---
card_id: CARD-CONTENT-GEMINI-V4-STRUCTURED-REPAIR-01
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: REPAIR_READY
role: repair_executor
ownership: v4_structured_repair_only
generation: Repair-1
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: credential FD、provider schema、durable replay 與 default transport selection 均為 fail-closed 跨模組契約
reviewer_thread_id: 019f9548-1dba-7781-9890-5dd54f669419
review_verdict: CHANGES_REQUESTED
implementation_base: d5e19971614669665a7fbe0710fab7fcb1a0b883
parent_code_candidate: 748c10f13e597ad74b16ecf2914fc388ed0f07de
parent_provisioning_commit: b600df18868e4af75a823d17daaa387f58c64b2c
source_branch: codex/gemini-v4-publish-main-integration-001
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/repair-01/
allowlist:
  - scripts/agy_gemini_runner.py
  - scripts/agy_gemini_v4_broker.py
  - scripts/agy_gemini_v4_structured_target.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_gemini_v4_broker.py
  - tests/test_agy_gemini_v4_structured_target.py
  - docs/pantheon_gemini_reviewer_v4_architecture.md
  - docs/pantheon_gemini_v4_agy_cli_compatibility.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/CARD-CONTENT-GEMINI-V4-STRUCTURED-REPAIR-01.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/repair-01/**
forbidden_scope:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - app/**
  - CHANGELOG.md
  - pyproject.toml
  - package.json
  - content queue, article registry and article content
  - credential content or global credential/config changes
  - real Gemini/API/agy generation
  - merge, push, deploy, publish, activation and default promotion
---

# Gemini V4 Structured Transport Repair-1

## Root question

只修 replacement Independent Review 的 F001–F005，使新 V4 operation 確實走
provider-native structured target、provider schema 與本地完整 schema 分層、numeric
constraints 被本地 gate 強制、durable replay 不依賴 credential，並限制 oversized
array 的無效 traversal。不得擴充功能或重寫 broker。

交付只能是 `REPAIR_READY_FOR_REVIEW` 或 `BLOCKED`。Repair executor 不得自審、
執行 real canary、整合或宣稱完成。

## Fixed findings

### CONTENT-GEMINI-V4-MAINLINE-001-F001 — P1

- Failure boundary：`AGY_GEMINI_V4_BROKER=1` 但未設定 profile 時仍建立
  `antigravity_cli_v1` 新 operation。
- Required behavior：flag-on 新 operation 固定使用
  `gemini_structured_api_v1`；明確指定舊 profile也不得建立新的 legacy target
  process。舊 profile只保留既有 durable replay compatibility。
- RED：runner 未設定 profile時必須走 structured；指定舊 profile的新 job必須
  fail closed且 legacy generate/process count維持 0。

### CONTENT-GEMINI-V4-MAINLINE-001-F002 — P1

- Failure boundary：完整 caller schema 的 `minLength`／`maxLength` 被直接送入
  Gemini `responseJsonSchema`，超出官方 provider subset。
- Required behavior：建立 versioned deterministic provider-schema projection；
  provider只收到官方支援 subset，本地 broker仍以完整 caller schema驗證結果。
- RED：現行文章 schema含 length constraints時，projection移除 unsupported
  keywords但保留 object/array/type/required/properties/items/enum及受支援 bounds；
  request identity仍綁完整 schema，不得弱化本地 gate。

### CONTENT-GEMINI-V4-MAINLINE-001-F003 — P2

- Failure boundary：broker接受 `minimum`／`maximum`，卻把超界 number/integer判為
  `VALID`。
- Required behavior：本地 validator強制 numeric bounds，bool不得當 number。
- RED：`minimum=1` 對 `0`、`maximum=1` 對 `2` 均為 `SCHEMA_MISMATCH`；邊界值通過。

### CONTENT-GEMINI-V4-MAINLINE-001-F004 — P2

- Failure boundary：structured credential在 durable ledger replay判定前即必填與
  開啟。
- Required behavior：既有 ledger/anchor只 replay且不開 credential、不執行
  target；新 operation仍 fail closed要求 owner-only credential FD。
- RED：credential path缺失時既有 structured ledger仍可回傳 replay result；
  target process count不增加。新 operation同條件必須失敗且不建 ledger。

### CONTENT-GEMINI-V4-MAINLINE-001-F005 — P3

- Failure boundary：array已超過 `maxItems` 後仍遍歷全部 items。
- Required behavior：`maxItems` 已失敗即停止 item traversal，或使用固定
  inspection budget；不得改變合法 array驗證。
- RED：oversized array只產生 bounded `maxItems` diagnostic，不再掃描 child
  violations；大型 fixture有 deterministic bounded-work assertion。

## Ranked, falsifiable hypotheses

1. F001源自 migration default與 replacement contract不一致；移除新 operation的
   legacy selection後，flag-off legacy仍不受影響。
2. F002不是 provider本身無法 structured output，而是 caller schema未投影；
   provider projection與完整 local validation分離後，文章 schema可送出且本地
   constraints不降級。
3. F003/F005源自 broker validator keyword coverage 與 traversal ordering；
   補齊 numeric checks並在 oversized array早停即可，不需替換 validator。
4. F004源自 credential acquisition早於 durable identity判定；lazy acquisition或
   replay seam前移後，new operation security不會降低。

## Ordered vertical slices

### V4R1-SELECTION

- traces_to：F001
- dependencies：none（current frontier）
- files：runner、outbox tests
- acceptance：flag-off legacy；flag-on只建立 structured新 operation；舊 ledger
  replay不被新 selection破壞。
- verification：focused RED→GREEN及既有 runner regression。

### V4R1-PROVIDER-SCHEMA

- traces_to：F002
- dependencies：none（current frontier）
- files：structured target、target tests、docs
- acceptance：versioned projection 具確定性；provider subset closed；完整 schema仍由
  broker驗證。
- verification：projection unit tests、current production schema fixtures、provider
  payload exact assertion。

### V4R1-LOCAL-SCHEMA

- traces_to：F003、F005
- dependencies：V4R1-PROVIDER-SCHEMA完成後核對兩層 keyword matrix
- files：broker、broker tests
- acceptance：numeric bounds 正確；oversized array bounded；既有 diagnostics不退化。
- verification：focused RED→GREEN、broker suite。

### V4R1-REPLAY-CREDENTIAL

- traces_to：F004
- dependencies：V4R1-SELECTION完成後使用固定 structured selection
- files：runner、broker、outbox/broker tests
- acceptance：durable replay不讀 credential、不 fork；new operation仍要求私密
  credential FD。
- verification：existing-ledger/no-credential及new-operation/no-credential negative
  tests。

### V4R1-CHECKPOINT

- traces_to：F001–F005
- dependencies：前四 slices
- acceptance：文件/evidence 與 source truth 一致；單一 repair candidate；無越界。
- verification：structured target、broker、outbox、architecture probe、legacy
  pipeline受影響 suites，`py_compile`、secret/debug scan、`git diff --check`。

## Evidence

在 `repair-01/` 保存：

- `root-cause.md`
- `red-green.txt`
- `finding-matrix.md`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

不得保存 prompt、credential、provider body、完整環境或本機私密絕對路徑。

## Handoff

建立單一 Repair-1 candidate commit，回報完整 SHA。主線將同一 Reviewer thread
`019f9548-1dba-7781-9890-5dd54f669419` 指向候选做 re-review；不得更换 Reviewer
来重置 finding。

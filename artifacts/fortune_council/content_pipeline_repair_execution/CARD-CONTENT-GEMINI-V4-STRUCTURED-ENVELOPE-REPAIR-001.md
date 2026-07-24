# CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REPAIR-001

- card_id: `CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REPAIR-001`
- chain_id: `CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REPAIR-001`
- ownership: `v4_effective_prompt_only`
- strictness: `strict`
- risk: `high`
- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_REVIEW`

## 來源失敗

- Activation-002 evidence commit:
  `b454dad83ff565fc6a206c80e7b939ff7c7ef3ca`
- job ID:
  `e64cb371f426c406af15d136728b659ffe18b7d2`
- durable state:
  `COMPLETE / 1 / PROCESS_TERMINAL=SUCCESS`
- caller state:
  `V4BrokerFailure / JSON_INVALID`
- retry / fallback / second invocation:
  `0`

## Root cause

V4 outbox request 含 `role / prompt / response_schema`，但 production runner 呼叫
broker 時，`raw_request` 只有 user prompt。Legacy CLI transport 會渲染 role
instruction、JSON-only／no-code-fence 約束、canonical JSON schema 與 user task；
V4 adapter 遺失這層 structured-generation envelope。

## 目標

- 在 runner→broker 的正確 seam 建立 deterministic effective CLI prompt。
- effective prompt 必須包含：
  - closed writer／reviewer role instruction
  - 禁止工具與讀取工作區
  - 單一 JSON object／禁止 Markdown code fence
  - canonical compact response schema
  - 原始 sanitized user task
- broker 的既有 CommandFrame prompt digest／byte count 必須綁定 effective prompt。
- flag-on 維持 fail-closed／no legacy fallback；flag-off 維持 legacy。

## 排序假說

1. `H1`：runner 遺失 envelope 是 `JSON_INVALID` 的主因。若在 runner seam 渲染
   envelope，synthetic broker capture 必須看到完整約束與 schema。
2. `H2`：broker 改寫或截斷 prompt。既有 digest／byte-count／target trace tests
   預期反證。
3. `H3`：真實 agy 仍可能不遵守完整 envelope。本 Repair 不以外呼驗證；只保留
   為後續 canary 風險。

## 可修改

- `scripts/agy_gemini_runner.py`
- `tests/test_agy_gemini_outbox.py`
- `docs/pantheon_gemini_reviewer_v4_architecture.md`
- `docs/pantheon_gemini_v4_agy_cli_compatibility.md`
- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_repair_001/**`

## 禁止

- 不修改 broker、SEO pipeline、publisher、文章、registry、metadata、sitemap、
  feed、prerender 或 automation。
- 不保存 effective prompt、raw stdout／stderr、response body、credential 或完整
  environment 到 evidence。
- 不呼叫 Gemini／agy。
- 不 retry Activation-001／002、不建立第三筆真實 payload。
- 不 push、deploy、publish、default promotion 或 legacy removal。

## 執行

1. 先補 RED：
   - writer effective prompt 包含 closed role、JSON-only、schema、user task。
   - reviewer 使用 reviewer role，不可混入 writer role。
   - schema 使用 canonical compact JSON。
   - flag-off 不經過 renderer。
2. 做最小 runner 修正，不重寫 broker。
3. 驗證 broker capture 的 `raw_request` digest／byte count 對應 effective prompt。
4. 跑 V4 focused、legacy、coordinator、publisher、web affected matrix、
   py_compile、privacy scan、debug-marker scan 與 `git diff --check`。
5. 建立單一 candidate commit，再送獨立 Review。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_repair_001/`

必須包含：

- `root-cause.md`
- `red-green.txt`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## 交付

只能：

- `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- `BLOCKED`

本卡不授權第三次真實外呼。

## 執行結果

- RED:
  `2 failed / 1 passed`
- focused GREEN:
  `6 passed`
- affected matrix:
  `212 passed`
- writer／reviewer role isolation:
  `PASS`
- JSON-only／no-code-fence／canonical schema／user task exact binding:
  `PASS`
- flag-off legacy bypass:
  `PASS`
- broker／ledger／anchor／replay changed:
  `false`
- Gemini／agy invocation during Repair:
  `0`
- decision:
  `DELIVERED_CANDIDATE / READY_FOR_REVIEW`

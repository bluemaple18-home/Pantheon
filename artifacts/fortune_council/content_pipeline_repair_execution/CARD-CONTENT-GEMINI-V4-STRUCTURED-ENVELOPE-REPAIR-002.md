# CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REPAIR-002

- card_id: `CARD-CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REPAIR-002`
- chain_id: `CONTENT-GEMINI-V4-STRUCTURED-ENVELOPE-REPAIR-002`
- ownership: `v4_effective_prompt_size_contract_only`
- strictness: `strict`
- risk: `high`
- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_REVIEW`

## 來源 Review

- reviewed candidate:
  `a438bf2dec16fb386b5fe23bec83583140f44ed5`
- Review evidence commit:
  `8d0932ec37c6ca0c3a1c549f4223c23dfd21a3d5`
- verdict:
  `DELIVERED_CANDIDATE / NO_GO`

## 唯一 Finding

Outbox 合法接受 262,144-byte user task 與最多 65,536-byte schema。Structured
envelope 合成後，effective prompt 可能超過 broker 現有 262,144-byte
`MAX_AGY_PROMPT_BYTES`。Review probe 實際得到：

- raw task:
  `262144 bytes`
- rendered effective prompt:
  `262509 bytes`
- runner result:
  `failed / ValueError`
- ledger:
  `absent`

## 目標

- broker effective-prompt ceiling 必須涵蓋：
  - outbox max task `256 KiB`
  - outbox max schema `64 KiB`
  - closed envelope overhead budget `64 KiB`
- ceiling 固定為 `384 KiB`，低於本 production target 的 `ARG_MAX=1 MiB`。
- 超過 ceiling 仍必須在 target fork 前 fail closed。
- CommandFrame、prompt digest／byte count、ledger、anchor、replay 契約不變。

## 可修改

- `scripts/agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- `docs/pantheon_gemini_reviewer_v4_architecture.md`
- `docs/pantheon_gemini_v4_agy_cli_compatibility.md`
- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_repair_002/**`

## 禁止

- 不修改 outbox raw task／schema public limits、SEO pipeline、publisher、文章、
  registry、metadata、sitemap、feed、prerender 或 automation。
- 不保存 effective prompt、raw stdout／stderr、response body、credential 或完整
  environment 到 evidence。
- 不呼叫 Gemini／agy。
- 不 retry Activation-001／002、不建立第三筆真實 payload。
- 不 push、deploy、publish、default promotion 或 legacy removal。

## 執行

1. 先補 RED：
   - broker ceiling 必須等於
     `MAX_PROMPT_BYTES + MAX_SCHEMA_BYTES + 64 KiB`。
   - 最大合法 task/schema 合成後必須落在 ceiling 內。
   - ceiling + 1 byte 必須 preflight fail closed。
2. 最小調整 broker constant，不改 process／ledger 實作。
3. 跑 focused、完整 affected matrix、py_compile、privacy、scope 與
   `git diff --check`。
4. 建立 Repair-2 candidate，再交回原獨立 Review thread re-review。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_structured_envelope_repair_002/`

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
  `2 failed`
- focused GREEN:
  `5 passed`
- affected matrix:
  `213 passed`
- maximum valid rendered prompt:
  `327942 bytes`
- broker effective-prompt ceiling:
  `393216 bytes / 384 KiB`
- ceiling + 1 preflight rejection:
  `PASS`
- broker process／ledger／anchor／replay logic changed:
  `false`
- Gemini／agy invocation during Repair:
  `0`
- decision:
  `DELIVERED_CANDIDATE / READY_FOR_REVIEW`

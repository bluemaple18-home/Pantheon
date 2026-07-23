---
card_id: CARD-CONTENT-GEMINI-V4-ROLLOUT-SHADOW-001
chain_id: CONTENT-GEMINI-V4-ROLLOUT-001
status: CARD_DRAFTED
role: rollout_shadow_owner
ownership: v4_shadow_evidence_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 外部 agy CLI、exactly-once ledger、shadow evidence 與 rollout decision 具有高回退成本
upstream_main_sha: c17b31247d303f485b4d64654e5196dab4fad149
upstream_candidate_sha: 8c1b935917364c820dec19304ecf6e0ac50cde5a
upstream_review_commit: 1c81e8f85229098f3c0a5a6f033eb5a126e8d015
upstream_review_verdict: GO
rollout_stage: LOCAL_SHADOW
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-ROLLOUT-SHADOW-001.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_shadow_001/**
forbidden_scope:
  - scripts/**
  - tests/**
  - docs/**
  - app/**
  - article content, registry, metadata, sitemap, feed and prerender
  - daily article automation and content queue mutation
  - login, credential and global CLI configuration
  - global environment or launchd modification
  - push, deploy, publish and default transport promotion
external_tool_gate:
  tool: agy
  cli_version: 1.1.5
  model: gemini-3.5-flash
  operation_level: one external generation
  payload_class: PUBLIC_SANITIZED_FIXED_CANARY
  effect: no content publication and no remote configuration mutation
  max_invocations: 1
  retry: forbidden
  fallback: forbidden
  authorization: USER_START_ROLLOUT_2026-07-23
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_shadow_001/
delivery_statuses:
  - DELIVERED_CANDIDATE
  - BLOCKED
decision_statuses:
  - READY_FOR_LIMITED_ROLLOUT_REVIEW
  - BLOCKED
---

# Gemini V4｜Local Shadow Rollout

## Root question

已整合但預設關閉的 V4 broker，能否在不發布文章、不修改全域設定、不 fallback／retry 的前提下，完成一次可獨立重算的本機 shadow canary，足以交給 Reviewer 判定是否具備 limited rollout 條件？

## 不可變邊界

- 初階文章產製、Writer／Reviewer、validation、apply與發布流程維持不變。
- `AGY_GEMINI_V4_BROKER=1` 只可存在於單次 shadow process 環境，不得寫入全域、launchd或 repo config。
- flag off baseline 必須維持 legacy。
- flag on 後禁止 legacy fallback。
- 不得執行文章 automation、不得修改 queue、不得發布內容。
- Provider internal model-call provenance維持 `UNKNOWN`，不得誇大。

## External tool final payload

- Tool：既有本機 `agy 1.1.5`。
- Model：`gemini-3.5-flash`。
- Invocation：production `scripts.agy_gemini_v4_broker:run_single_shot`；CLI 必須使用 `--print <prompt>`。
- Prompt：固定公開 synthetic canary，只要求回傳 closed JSON：
  - `ok: true`
  - `transport: "agy-v4-rollout-shadow-canary"`
- Schema：closed object；禁止額外欄位。
- 影響：一次外部 generation；不含文章、不含私密資料、不改遠端設定。
- 次數：最多一次；任何 timeout、nonzero、malformed、ledger／anchor／binding失敗後立即停止，不做第二次。

## 執行順序

1. Gate：獨立 clean worktree、HEAD精確等於 upstream main、card可讀、`index.lock` absent。
2. 唯讀核對 main 已包含 accepted candidate與 Review lineage，default flag仍 off。
3. 重跑 flag-off legacy regression與 V4 offline synthetic matrix；未全綠不得外呼。
4. 建立 shadow recorder/verifier；先用 synthetic bundle驗 ledger、anchor、receipt、schema、no-fallback與 privacy。
5. Offline全綠後，執行唯一一次外部 canary；不得 retry/fallback。
6. 立即用獨立 verifier重算 ledger SHA、final anchor、operation/item/attempt/request/model/profile/executable digest、result bytes/schema與 target process count。
7. 跑 focused tests、privacy/allowlist、`py_compile`、`git diff --check`。
8. 建立單一 evidence candidate commit，交獨立 Reviewer；rollout owner不得自審通過。

## Required evidence

- `preflight.md`
- `legacy-baseline.txt`
- `synthetic-shadow.json`
- `shadow-recorder.py`
- `shadow-verifier.py`
- `real-shadow-bundle.json`
- `real-shadow-verification.json`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

交付只能是 `DELIVERED_CANDIDATE` 或 `BLOCKED`。即使 evidence全綠，也只能提出 `READY_FOR_LIMITED_ROLLOUT_REVIEW`；不得自行切換預設 transport。

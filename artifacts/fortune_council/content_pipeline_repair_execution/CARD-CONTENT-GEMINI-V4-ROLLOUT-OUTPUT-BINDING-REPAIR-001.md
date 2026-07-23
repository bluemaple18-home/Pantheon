---
card_id: CARD-CONTENT-GEMINI-V4-ROLLOUT-OUTPUT-BINDING-REPAIR-001
chain_id: CONTENT-GEMINI-V4-ROLLOUT-OUTPUT-BINDING-REPAIR-001
status: DELIVERED_CANDIDATE
role: v4_output_binding_repair_owner
ownership: v4_broker_output_binding_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
source_main_sha: 4bb72adaa68436c07975725330f5eda575a67e4f
blocked_rollout_commit: 90559641a9460c26eb7c168ebbb78ce4be2a51fa
blocked_reason: REAL_SHADOW_OUTPUT_BINDING_MISMATCH
external_canary_authorization: NOT_AUTHORIZED
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_output_binding_repair_001/
---

# Gemini V4｜Rollout Output Binding Repair

## Root question

Production broker 已用原始 stdout 驗證 control 的 byte count 與 SHA-256，但
`BrokerResult.result_json` 會重新 canonicalize 已解析 JSON，使 privacy-safe rollout
recorder 無法將原始 stdout digest 與 closed-schema result 獨立綁定。本卡只修復此
production seam，不能放寬 verifier 接受條件，也不能重跑外部 canary。

## 固定 root cause

- 真實 canary stdout 為 64-byte pretty JSON 加單一換行。
- broker control 正確保存該 64-byte stdout 的 byte count 與 SHA-256。
- caller 收到的 `result_json` 被轉為 54-byte canonical JSON。
- recorder 因此只能保存語意 result，無法證明 control digest 對應同一輸出。
- verifier 的 `REAL_SHADOW_OUTPUT_BINDING_MISMATCH` 為正確 fail-closed，不得修改成
  接受任意 pretty-print 樣式。

## Repair contract

1. 先加入 deterministic RED：synthetic target 回傳 closed-schema pretty JSON，
   `result_json` 必須保留 broker 已驗證的原始 stdout bytes，且其 length／SHA-256
   必須與 `BrokerResult.byte_count`／`stdout_sha256` 完全一致。
2. 做最小 production 修正；不得重寫 broker、ledger、anchor 或 runner。
3. `.result` property 與 runner inbox 仍輸出解析後 JSON object，不得將原始格式帶入
   文章或 queue。
4. malformed／schema-invalid output 仍 `caller_contract_satisfied=false` 且
   `result_json=None`。
5. flag off 維持 legacy；flag on 失敗不得 fallback。
6. 不保存 prompt、credential、完整環境或未受 closed schema 約束的 raw output。

## Allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-ROLLOUT-OUTPUT-BINDING-REPAIR-001.md`
- `scripts/agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_output_binding_repair_001/**`

## Forbidden

- `scripts/agy_seo_copy_pipeline.py`
- `app/**`
- 其他 production scripts、docs 與 tests
- rollout blocked evidence commit 的歷史檔案
- 文章、registry、metadata、sitemap、feed、prerender、content queue與 daily automation
- login、credential、全域 CLI 設定、全域環境與 launchd
- 外部 Gemini／agy canary、retry、fallback、push、deploy、publish或預設 transport切換

## Verification

1. 保存 RED command 與失敗輸出。
2. 最小 GREEN，證明 pretty JSON raw bytes／digest／byte count一致。
3. canonical JSON、malformed output、schema-invalid與 replay／concurrent duplicate回歸。
4. V4 focused tests、legacy publishing與 coordinator受影響測試。
5. `py_compile`、privacy scan、allowlist、`[DBG-` 清除與 `git diff --check`。

## Required evidence

- `root-cause.md`
- `red-green.txt`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## Delivery

只能回報：

- `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- `BLOCKED`

本卡不得自行 Review、整合或重跑外部 canary。

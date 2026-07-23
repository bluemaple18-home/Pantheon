---
card_id: CARD-CONTENT-GEMINI-V4-ROLLOUT-SHADOW-002
chain_id: CONTENT-GEMINI-V4-ROLLOUT-002
status: CARD_DRAFTED
role: rollout_shadow_owner
ownership: v4_shadow_evidence_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
upstream_main_sha: 1dd80978dc4c6facbb588aa8869bec8362e606a3
output_binding_repair_sha: 4e04e82506c4a1c2a3846640f9504fca972ae9fd
output_binding_review_sha: 1dd80978dc4c6facbb588aa8869bec8362e606a3
output_binding_review_verdict: GO
previous_blocked_rollout_sha: 90559641a9460c26eb7c168ebbb78ce4be2a51fa
previous_blocker: REAL_SHADOW_OUTPUT_BINDING_MISMATCH
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_shadow_002/
---

# Gemini V4｜Local Shadow Rollout 002

## Root question

已 Review GO 並整合的 output-binding Repair，能否在新的獨立 chain 中，以預先鎖定、
可獨立重算且不保存 raw output 的 encoding contract，完成一次新的 production shadow
canary候選？

## Chain boundary

- 本卡是新 chain，不是對舊 `CONTENT-GEMINI-V4-ROLLOUT-001` 的 retry。
- 舊 chain 的唯一一次外呼已消耗且維持 `BLOCKED`，不得重用 ledger／operation／attempt。
- 初階發文流程、legacy default與 `AGY_GEMINI_V4_BROKER=1` 唯一 opt-in不變。
- flag on失敗不得 legacy fallback；不得發布文章或修改 content queue。

## Precommitted output encoding contract

在任何新外呼前，recorder/verifier 必須以 synthetic matrix鎖定並驗證以下唯一可接受
encodings；不得在看到 real output後新增：

1. `canonical-json-v1`
2. `canonical-json-newline-v1`
3. `sorted-indent2-json-newline-v1`

Verifier必須依 bundle中的 closed-schema parsed result與 encoding label重建完整 stdout
bytes，再核對 `byte_count`／`stdout_sha256`。未知 encoding、任意 whitespace、錯誤 key
order、額外 newline、digest／length變造均 fail closed。Evidence不得保存 prompt、
credential、完整環境、CLI log、本機路徑或 raw stdout。

## Allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-ROLLOUT-SHADOW-002.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_shadow_002/**`

## Forbidden

- 所有 production scripts、tests、docs與app
- 修改 Repair／Review／舊 rollout evidence
- article、registry、metadata、sitemap、feed、prerender、queue與 daily automation
- login、credential、全域 CLI設定、全域環境與launchd
- push、deploy、publish或預設 transport promotion

## Offline gates

1. clean獨立worktree、HEAD精確等於 upstream main、lineage與cards可讀。
2. flag-off legacy與flag-on no-fallback回歸。
3. V4 focused、legacy publishing、coordinator完整受影響測試。
4. evidence-owned recorder/verifier synthetic bundle。
5. 三種合法 encoding 全接受；mutation至少涵蓋unknown encoding、wrong whitespace、
   key order、extra newline、digest、length、schema、ledger、anchor、binding、
   process count與fallback，全部 rejected。
6. `py_compile`、privacy、allowlist、`[DBG-`與`git diff --check`。

## External canary gate

external_canary_authorization: `PENDING_FINAL_CONFIRMATION`

- Tool：既有 `agy 1.1.5`
- Model：`gemini-3.5-flash`
- Entrypoint：`scripts.agy_gemini_v4_broker:run_single_shot`
- CLI：`--print <prompt>`
- Payload：公開 sanitized fixed closed-schema canary
- Maximum：1 external invocation；no retry／fallback
- Effect：不發布、不改遠端設定、不改預設 transport

Offline全綠後必須停止於 `BLOCKED / EXTERNAL_CANARY_FINAL_CONFIRMATION`，列出實際
tool basename、version、digest、完整 prompt、schema、encoding contract、命令／測試
數與影響摘要。只有主線取得使用者對該最終包的明確確認後才能繼續。

## Required evidence

- `preflight.md`
- `legacy-baseline.txt`
- `shadow-recorder.py`
- `shadow-verifier.py`
- `synthetic-shadow.json`
- `synthetic-shadow-verification.json`
- `synthetic-mutation-matrix.json`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

授權並執行後才可新增：

- `real-shadow-bundle.json`
- `real-shadow-verification.json`

## Delivery

只能回報：

- `DELIVERED_CANDIDATE / READY_FOR_LIMITED_ROLLOUT_REVIEW`
- `BLOCKED`

即使全綠也不得自行宣稱 rollout ready、整合、放量或上線。

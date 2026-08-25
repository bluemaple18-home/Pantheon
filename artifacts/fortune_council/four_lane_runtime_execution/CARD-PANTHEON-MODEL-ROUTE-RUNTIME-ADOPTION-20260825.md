---
id: CARD-PANTHEON-MODEL-ROUTE-RUNTIME-ADOPTION-20260825
status: ready
chain_id: PANTHEON-MODEL-ROUTE-RUNTIME-ADOPTION-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，但需核對正式 runtime promotion、Rule 24/25 與既有 failed exact run 的相容邊界，屬 strict/core-bounded；不需 Sol 處理架構岔。
execution_mode: read_only_adoption_preflight
production_mutation: not_authorized_by_this_card
---

# Pantheon 模型路由 runtime adoption preflight

工作名稱：Pantheon 模型路由 runtime adoption preflight

## 任務目的

確認已通過 Review 的正式模型路由修正，如何以既有 promotion 入口進入 production actor，並證明更新後可安全回到既有 V0391 exact run；本卡只產出唯一可執行的 adoption plan 或單一 blocker，不執行 production mutation。

## Root cause 與固定事實

- 既有 V0391 exact run：`v0391-publish-canary-20260825-01`。
- 兩次 Writer job 均由舊 runtime actor `5872284828f9dd6f0a75adf407becaeadb50d61a` 執行並回 `GeminiCliFailure / CLI_NONZERO`。
- 舊 actor route 仍含不存在的 `gemini-3.5-flash-lite` 與錯誤 Reviewer route。
- 修正 candidate：`67f62f233f957bfbcaf51d65e63d58f66e35c206`。
- 獨立 Review result：`REVIEW_GO`，result commit 原始 SHA `3b0dfeb96ddd377e360d58fc6c4bb87404889839`；主線整合 commit `2bb19c5668`。
- 受影響測試：`332 passed`；`bash -n` 與 `git diff --check` PASS。
- 不得把 source Review GO 冒充 runtime 已更新；不得直接重試 V0391。

## 唯一垂直 slice

### S-RUNTIME-ADOPTION-PREFLIGHT

- traces_to：公開文章可讀成功準則；V0391 Writer blocker；模型路由 Review GO。
- blocking_edges：無；這是目前唯一 frontier。
- 目標：以 current main/source、live actor/manifest/transaction、既有 promotion CLI 與 Rule 24/25 receipts，產生 deterministic adoption verdict。
- 驗收：只能交付：
  1. `READY_FOR_EXACT_AUTHORIZATION`：列出唯一 target SHA、runtime digest、transaction root、plan digest、exact apply/finalize argv、rollback/stop-loss、預期 live identity，以及 apply 後如何回原 V0391 thread；或
  2. `BLOCKED`：單一可重現 blocker、缺少的 exact input/authorization、目前 live 與 V0391 safe state。

## 執行契約

1. 第一拍唯讀核對 source/main、live actor、manifest、promotion transaction、private stage、V0391 exact run 與兩個 failed receipts；先查 CodeGraph，無結果才限域 `rg`。
2. 必須使用既有 `scripts.pantheon_content_runtime_promotion` 與既有正式 inputs；不得建立替代 promotion、手改 actor/config/manifest/stage、重做舊 promotion 或直接操作 launchctl。
3. 僅可執行 plan/dry-run/validator/read-only capacity/readiness checks；不得 apply、finalize、rollback、activation、Gemini job、run resume、Publisher、push、tag。
4. 逐項判斷 current fix 是否需要新的 Rule 24 capacity evidence、Rule 25 receipt、remote-main equality 或其他 exact authorization；不得沿用過期 PASS。
5. source target 必須排除不屬 runtime 的 review/card artifacts；若 promotion 契約只能採整體 commit，需明列正式 runtime digest 的 allowlist/輸入如何排除 docs artifacts。
6. 不得讀寫主工作區既有未追蹤檔；只使用 Git objects、tracked files 與正式 runtime receipts。
7. 同一 blocker 最多兩次驗證；第三次前停止。不得開後續卡。

## 唯一可寫範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-RUNTIME-ADOPTION-20260825-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/model_route_runtime_adoption_20260825/`
- task-owned `/private/tmp/pantheon-model-route-adoption-20260825-*`

## 禁止範圍

- 禁止修改 source、tests、workflow、runtime actor、manifest、queue/state、V0391 run、stage、LaunchAgents 與既有 evidence。
- 禁止 production apply/finalize/rollback、activation、publish、push、tag、promotion mutation、第三次 Writer attempt。
- 禁止建立 replacement canary、Repair、Review 或其他新卡。

## 交付

- Result：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-RUNTIME-ADOPTION-20260825-RESULT.md`
- 只提交本卡 RESULT/evidence，回報完整 result commit SHA。
- `READY_FOR_EXACT_AUTHORIZATION` 不是 production 完成；主線收卡並取得必要授權後，才可在同一 thread 原地執行 apply。

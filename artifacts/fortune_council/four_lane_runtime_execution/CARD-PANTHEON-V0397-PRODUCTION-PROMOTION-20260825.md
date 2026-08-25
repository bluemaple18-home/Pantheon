---
id: CARD-PANTHEON-V0397-PRODUCTION-PROMOTION-20260825
status: ready
chain_id: PANTHEON-PUBLISH-FLOW-ACTIVATION-CANARY-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production runtime promotion 為固定 SHA、既有正式入口與高回退成本的 strict 操作。
target_sha: d8df768164
---

# Pantheon production runtime promotion

工作名稱：Pantheon production runtime promotion

任務目的：只用既有正式 promotion seam，把已 push 且通過複審的 `d8df768164` 收斂到 production runtime；完成後停止並交回原 V0391 thread 發文。

## 單一切片

- Frontier：`origin/main=d8df768164`、V0396 `REVIEW_GO`、main 整合測試通過。
- 執行：fresh read-only identity/capacity/Rule24/Rule25 gates → deterministic plan → 單次 apply → postcheck → finalize。
- 若任何 gate 非 PASS/READY、plan 非 `READY_TO_APPLY`、active run closure dangling、identity/digest drift：零 mutation 或依正式 transaction rollback，立即停止。

## 允許

- 讀 production actor、manifest、stage、queue registry/run closure、remote main。
- 使用 `scripts.pantheon_content_runtime_promotion.py` 既有 plan/apply/status/finalize/rollback。
- 建立 task-owned transaction/evidence artifacts。

## 禁止

- 禁止改產品 source/tests、另寫 promotion 腳本、重構、另開卡或 thread。
- 禁止建立新 run、呼叫 Gemini、publish、tag、push。
- 禁止清 queue、替換 dangling identity、碰使用者未追蹤檔。

## 驗收與交付

- production actor HEAD、manifest/runtime digest、stage readiness、activation barrier 全部綁定 `d8df768164`。
- transaction 最終只能 `COMMITTED`、`ROLLED_BACK` 或有單一根因的 `BLOCKED`；不得用 plan PASS 冒充完成。
- 回報 fresh gates、plan/apply/finalize 狀態、transaction root、receipt、live postcheck、active V0391 identity 是否保持。
- production promotion `COMMITTED` 後停止；主線回原 V0391 thread 執行試發與公開網址驗收。

## RESULT

狀態：pending

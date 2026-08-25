---
id: CARD-PANTHEON-MODEL-ROUTE-LITE-PRODUCTION-PROMOTION-20260825
status: ready
chain_id: PANTHEON-MODEL-ROUTE-LITE-PRODUCTION-PROMOTION-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定候選 SHA 的 production promotion；契約明確但含高影響 runtime mutation，使用 strict/core-bounded 跑道。
production_mutation: explicitly_authorized_2026-08-25
---

# 將 Gemini Lite route promotion 到 production

工作名稱：將 Gemini Lite route promotion 到 production

## 目的

把已整合、已獨立 Review GO 的 `2dd9725f72a48e31648d7a609ee53b77d403ee43`，透過既有正式 promotion 入口升為新 production generation；只在正式 stage 實際解析為 Writer `gemini-3.5-flash-lite`、Reviewer `gemini-3.1-flash-lite` 時交付 GO。

## 固定事實與授權

- Current production：generation `g37-67f62f233f-model-route-20260825`；actor `67f62f233f957bfbcaf51d65e63d58f66e35c206`。
- Promotion target：`2dd9725f72a48e31648d7a609ee53b77d403ee43`。
- `origin/main` 已由使用者明確授權並 fast-forward 到 target；本卡不得再 push。
- Target 的 Lite route 修正已通過原 Reviewer `REVIEW_GO`；禁止重做 Repair、Review 或改 source。
- 使用者已明確授權一次正式 promotion apply/finalize 與必要的 stage/readiness/barrier 更新。

## 唯一 slice：S-LITE-PRODUCTION-PROMOTION

- traces_to：V0391 公開文章可讀；Writer/Reviewer exact Lite route。
- blocking_edges：target/remote equality、Rule 24、Rule 25、promotion plan 全部 fresh GO。
- frontier：唯讀 preflight；GO 後同一 thread 直接 apply/finalize。

## 執行契約

1. 第一拍核對 card source、target object、`origin/main == target`、live actor/manifest、transaction collision 與工作區 clean；先 CodeGraph，失敗才限域 `rg`。
2. 只用既有 `scripts.pantheon_content_runtime_promotion` 與正式 Rule 24/25 入口；禁止替代腳本、手改 actor/config/manifest/stage/barrier。
3. 先 plan/dry-run；fresh capacity、readiness、negative fail-closed 與 promotion plan 全 GO 後，執行一次 apply，再一次 finalize。外部／production write 不確定時禁止重試。
4. Promotion 必須保留 queue/state 與 V0391 exact run；不得 activation、Gemini job、run resume、Publisher、文章 push 或 tag。
5. Postcheck 必須證明 transaction `COMMITTED`、rollback bundle finalized、actor clean/exact target、manifest/runtime identity 一致、七個 readiness acknowledgements、barrier 存在。
6. 必須直接讀取正式 staged model-route file，證明 Writer/Reviewer exact Lite；不得由檔名、digest 或舊 evidence 推定內容。
7. 任一 gate 不符立即停止；同一 blocker 不得第三次嘗試。

## Allowlist

- 正式 promotion transaction 明示擁有的 actor、manifest、private stage、readiness、barrier、rollback bundle。
- 本卡 RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-LITE-PRODUCTION-PROMOTION-20260825-RESULT.md`
- Evidence：`artifacts/fortune_council/four_lane_runtime_execution/model_route_lite_production_promotion_20260825/`
- Task-owned temporary files：`/private/tmp/pantheon-lite-production-promotion-20260825-*`（local-only）。

## 禁止

- 禁止 source/test/workflow 修改；禁止第二張卡、第二 promotion transaction、rollback（除非正式入口因 apply failure 自動 fail-closed）、activation、publish、push、tag。
- 禁止讀寫主工作區既有未追蹤檔。

## 驗收與交付

- GO：`COMMITTED` + exact target actor + exact Lite route + queue/V0391 preserved + production reset-safe。
- BLOCKED：單一根因、`partial_mutation`、transaction state、可安全續跑點。
- Commit 只含本卡 RESULT/evidence；回完整 SHA 與 clean status。主線負責回原 V0391 thread，不得自行發文。

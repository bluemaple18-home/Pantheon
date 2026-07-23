# Decision

Status: READY_FOR_REVIEW

Rollout decision: DO_NOT_PROMOTE_DEFAULT

## Facts

- Concurrent-create replay anchor provenance 的唯一 production defect 已由 public seam RED 重現並以最小修正轉 GREEN。
- Flag-off／flag-on synthetic acceptance matrix 為 `21 passed`。
- 唯一真實 `agy 1.1.5` canary 為 durable `COMPLETE/1`，`EXEC_CONFIRMED` 恰一個，strict result schema通過，沒有 retry、fallback或failed record。
- 受監督產文線仍固定 legacy CLI；本卡沒有修改產文、文章、registry、sitemap、feed、prerender或發布狀態。

## Interpretation

本 candidate 已具備送獨立 Review 的 exactly-once transport evidence，但真實 canary 只證明 trusted executable snapshot 的本機 transport completion 與 ledger/anchor/replay accounting，不能獨立證明 provider internal model-call provenance。

在獨立 Review、small shadow run 與另立 migration commit 之前，`AGY_GEMINI_V4_BROKER` 維持唯一 opt-in，V4 不成為預設 transport。

# Decision

Status: BLOCKED

Rollout decision: DO_NOT_PROMOTE_DEFAULT

## Facts

- Concurrent-create replay anchor provenance 的唯一 production defect 已由 public seam RED 重現並以最小修正轉 GREEN。
- Flag-off／flag-on synthetic acceptance matrix 為 `21 passed`。
- 唯一真實 `agy 1.1.5` canary 為 durable `COMPLETE/1`，`EXEC_CONFIRMED` 恰一個，strict result schema通過，沒有 retry、fallback或failed record。
- 受監督產文線仍固定 legacy CLI；本卡沒有修改產文、文章、registry、sitemap、feed、prerender或發布狀態。

## Interpretation

本 candidate 已具備送獨立 Review 的 exactly-once transport evidence，但真實 canary 只證明 trusted executable snapshot 的本機 transport completion 與 ledger/anchor/replay accounting，不能獨立證明 provider internal model-call provenance。

在獨立 Review、small shadow run 與另立 migration commit 之前，`AGY_GEMINI_V4_BROKER` 維持唯一 opt-in，V4 不成為預設 transport。

## JSON_INVALID continuation

Activation-004 證明 exactly-once transport 仍為 `COMPLETE/1`，但 caller result 是
`JSON_INVALID`。本 candidate 新增 value-free closed classifier 與 runner 二次
sanitizer，讓下一次結果能區分六種格式類別；它不自動修正 Gemini 輸出，也沒有
新增真實外呼。

因此目前決策維持：

- status：`BLOCKED`
- rollout：`DO_NOT_PROMOTE_DEFAULT`
- legacy default：維持
- next external canary：必須重新揭露 payload 並取得明確確認

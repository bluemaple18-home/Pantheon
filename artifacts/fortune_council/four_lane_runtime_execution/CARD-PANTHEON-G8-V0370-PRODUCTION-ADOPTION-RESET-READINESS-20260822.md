---
id: CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
chain_id: PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822
role: production-adoption-readiness-planner
cycle: 1
status: ready
type: production_adoption_readiness
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 規格已由 current NO-GO evidence 固定；需精確封裝 production adoption 與 Publisher reset 邊界，但本卡不執行 mutation，使用 GPT-5.5 high 控制成本。
production_read_authorized: true
production_mutation_authorized: false
canary_authorized: false
parent_candidate_sha: 2255cc504a
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/**
forbidden_scope:
  - production actor、manifest、queue、state、transaction、private stage、live plist、barrier、launchctl 或 git refs mutation
  - promotion、reset、activation、restage、canary、Publisher child、deploy、tag、push、schedule、steady autonomy
  - 修改 repo source、tests、config、registry、metadata、既有 evidence 或 handoff
verification:
  - current NO-GO evidence digests、candidate SHA 與 production identity 可重現
  - 產出唯一、bounded、可回退、fail-closed 的 adoption/reset execution contract
  - before/after protected snapshot證明 production零 mutation
  - verdict僅 READY-FOR-AUTHORIZATION、BLOCKED 或 UNKNOWN
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_production_adoption_reset_readiness_20260822/
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-PRODUCTION-ADOPTION-RESET-READINESS-20260822-RESULT.md
---

# G8 v0.3.370 production adoption／Publisher reset readiness

## 工作名稱 → 正在做什麼 → 現在狀態

G8 v0.3.370 adoption/reset readiness → 把 current `NO-GO` 轉為一份可人工授權的 bounded production mutation 契約 → `READY / READ-ONLY PLANNING`

## Root Question

在不改變 production 的前提下，是否能唯一確定把 actor／manifest從 `db9fb434…`／`0.3.369` 採用到 release `v0.3.370`，並建立 current Publisher reset success provenance所需的最小動作、前置條件、回退、停損與驗證？

## 必讀 Authority

1. `handoff_20260822_g8_exit78_release_v0370.md`
2. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822-RETRY-1-RESULT.md`
3. `artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822_retry_1/evidence-digests.sha256`
4. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
5. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
6. `<ai-core-root>/rules/24-storage-capacity-safety.md`
7. `<ai-core-root>/rules/25-production-canary-readiness.md`

## 執行契約

1. 驗 provisioning HEAD、parent candidate、`origin/main`、peeled `v0.3.370`、clean worktree與 CodeGraph readiness；CodeGraph unavailable時限域 source fallback並明列 degraded evidence。
2. 唯讀重驗 current actor／manifest／stage／launchctl與 reset provenance；做同集合 before／after snapshot。
3. 定位既有正式 entrypoint與參數，不新造第二套 production workflow；逐項確認其 I/O、identity、generation、correlation、lock、transaction、idempotency與 fail-closed seam。
4. 產出 `execution-contract.json`：精確 command template、輸入 SHA／digest、preconditions、每一步 expected receipt、stop-loss、rollback、postcondition與禁止重試條件。共享命令只用 `<repo-root>`／repo-relative path。
5. 產出 `authorization-request.md`，只列一次人工授權所需的 exact scope；不得把 readiness 結論當成授權。
6. 任何需要先改 source/config、缺正式入口、無法證明回退、identity不唯一或 current truth漂移，判定 `BLOCKED`。

## Gate

- `READY-FOR-AUTHORIZATION`：current identity唯一、正式入口存在、bounded mutation與rollback可精確重現、Rule 24／25前置條件 current，且 tripwire `PASS`。
- `BLOCKED`：存在明確缺口或矛盾。
- `UNKNOWN`：缺證據但未形成矛盾。

即使 `READY-FOR-AUTHORIZATION`，也只能停止並回主線請求人工授權；禁止執行 adoption、reset、canary或任何 production write。

## 交付

只新增本卡 evidence目錄與唯一 RESULT。RESULT 必須列 root question、current identity、精確執行契約 locator、rollback、tripwire、verdict、blocker與下一步。完成後執行 `git diff --check`、digest驗證並建立單一 candidate commit；禁止 push／tag。

## Stop-loss

- 同一 blocker第三次失敗停止。
- 任一命令需要 production write／sudo／launchctl mutation，立即停止並記 `BLOCKED`。
- production 保護面 before／after任一改變，固定 `BLOCKED / MUTATION_DETECTED`。

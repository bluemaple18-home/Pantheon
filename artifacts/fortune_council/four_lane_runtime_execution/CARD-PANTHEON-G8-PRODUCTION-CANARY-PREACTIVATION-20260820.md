---
id: CARD-PANTHEON-G8-PRODUCTION-CANARY-PREACTIVATION-20260820
chain_id: PANTHEON-G8-PRODUCTION-CANARY-PREACTIVATION-20260820
parent_card_id: CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-RETRY-1-20260820
role: verification
cycle: 1
status: ready
type: production_canary_preactivation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 已進入 production 邊界，但本卡僅做 fail-closed 唯讀 preactivation；契約固定且需核對 current source、正式 gate、容量、live identity 與唯一 selector，使用 GPT-5.5 high。
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/g8_production_canary_preactivation_20260820/**
  - .work/CARD-PANTHEON-G8-PRODUCTION-CANARY-PREACTIVATION-20260820/**
forbidden_scope:
  - 修改 source、tests、rules、config、workflow、queue、state、transaction、registry、manifest、plist、barrier 或 production artifact
  - git fetch、pull、push、tag、merge、rebase、promotion apply/finalize、installer、launchctl mutation、deploy、schedule 或發文
  - 建立 canary、鎖定或消耗 production run、啟動 Publisher、觸發任何內容 I/O
  - 用舊 receipt、狀態文案、單一 selector 命中或手改 evidence 冒充 GO
verification:
  - readiness capability 七段 PASS、official READY、missing-step BLOCKED、canary_created false
  - capacity 兩週期 PASS、回收與停損證據齊全、host reserve PASS
  - readiness source 到 current HEAD 只含卡片與 evidence lineage，production code tree無漂移
  - local main、remote main唯讀查詢、actor、manifest、staged/live identity與production基線可判定
  - canonical selector dry-run恰好一筆且零 mutation
  - evidence candidate僅限ownership、git diff --check通過、worktree clean
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_production_canary_preactivation_20260820/
---

# G8 四線 production canary preactivation

## 工作名稱 → 正在做什麼 → 現在狀態

核對 G8 production canary 預啟動條件 → 只讀驗證 current source、正式入口、容量、live identity 與唯一 selector → `READY TO DISPATCH / ZERO PRODUCTION MUTATION`

## Root Question

整合 current readiness evidence 後，是否已具備另行請求 production activation 授權所需的完整、current、可重現且 fail-closed 證據，且不存在 source／remote／runtime／capacity／selector drift？

## 當前權威事實

- readiness source：`0343bb7199b90794c10ce28cc4aff7ebbd0242b4`。
- readiness candidate：`9dcf04260d088f6d3850f6074c0e8d6e031e8a80`；已整合為 main `370736540360ad282c1c88c2f7c1ac6a15166e50`。
- summary digest：`c9a94d3646c06dc05f3e21bad5683817e38d3968fbb28b44b804918a729c7e05`。
- current evidence：七段 capability `PASS`、capacity 兩週期 `PASS`、official `READY`、missing-step `BLOCKED`、`canary_created=false`。
- 上述只代表 readiness，並不授權 production mutation。

## 唯一 frontier slice

1. 核對正式 thread、隔離 worktree、exact HEAD、clean state、卡片與 Rule 24／25。
2. CodeGraph query：`G8 production canary preactivation readiness capability capacity promotion launchagent selector transaction tag push`；失敗才限域 `rg`。
3. 驗 readiness source 到 current HEAD 的 diff；只准本 chain 卡片與 APF-004 evidence，任何 production code／config 漂移即 `NO-GO`。
4. 以正式 gate 重新驗 current capability receipt；不得重跑 readiness generator。
5. 驗 current capacity receipts、兩週期、cleanup、projection、stop-loss 與主機 reserve。
6. 只讀核對 local main、`git ls-remote origin refs/heads/main`、production actor／manifest／staged／live identity與 transaction/tag/public artifact 基線；禁止 fetch 或改 refs。
7. 只用既有正式 dry-run／plan seam 驗 canonical selector 恰好一筆；不得鎖定、消耗或寫 production queue/state。
8. 產出 `preactivation-decision.md` 與 machine-readable receipt；結論只可 `GO_FOR_USER_AUTHORIZATION` 或 `NO-GO`。

## GO 條件

- Rule 24 storage/capacity 與 Rule 25 capability gate 全部 current、完整且 PASS／READY。
- readiness source→current HEAD 只有核准 evidence/card lineage，production code tree一致。
- remote main、local main與 production authority關係明確且可由正式流程安全收斂；不得以 stale local ref 推定。
- live/staged/actor/manifest identity 無 unknown 或混合狀態。
- selector dry-run恰好一筆，所有 before mutation counts 已保存且為零新增。
- candidate 僅含本卡 evidence ownership，`git diff --check` 通過。

## 停損

- 任一 evidence 缺失、digest／identity／remote／runtime unknown、capacity 非 PASS、selector 非唯一：`NO-GO`。
- 任一步需要 production write、LaunchAgent mutation、push/tag、queue lock或 source 修補：立即停止，回報 `SCOPE_EXPANSION`。
- 本卡不得 activation production；即使 `GO_FOR_USER_AUTHORIZATION`，也必須回主線取得新的明確授權。

## 正式 task 初始 prompt 核心契約

```text
你負責 CARD-PANTHEON-G8-PRODUCTION-CANARY-PREACTIVATION-20260820，role=verification、cycle=1。只做 production canary 的唯讀 preactivation，不得建立 canary、修改 production、fetch/push/tag、執行 installer、launchctl mutation、promotion apply/finalize、鎖定或消耗 run。完整讀卡與 Rule 24/25，先做 CodeGraph query，失敗才限域 rg。驗 current readiness/capacity、source→HEAD evidence-only lineage、local/remote/actor/manifest/staged/live identity與canonical selector dry-run。不得重跑 readiness generator。產出唯一 evidence candidate，結論只可 GO_FOR_USER_AUTHORIZATION 或 NO-GO；即使 GO 也停止等待使用者另行授權 production activation。
```

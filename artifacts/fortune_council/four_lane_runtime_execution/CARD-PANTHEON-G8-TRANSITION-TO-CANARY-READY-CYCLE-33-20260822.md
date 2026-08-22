---
id: CARD-PANTHEON-G8-TRANSITION-TO-CANARY-READY-CYCLE-33-20260822
chain_id: PANTHEON-G8-TRANSITION-TO-CANARY-READY-20260822
role: production-transition-operator
cycle: 33
status: queued
type: production_transition_bootstrap
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-TRANSITION-TO-CANARY-READY-CYCLE-33-20260822-RESULT.md
forbidden_scope:
  - 未收到主線明確 ACTIVATE 前，修改 actor、manifest、queue、state、transaction、private stage、live plist、barrier 或 launchctl
  - 建立或執行 canary、Publisher child、tag、push、deploy、schedule 或 steady autonomy
  - 手改 plist／manifest／receipt、降低 fail-closed gate、沿用 historical readiness 冒充 current evidence
verification:
  - CodeGraph query 成功，失敗才限域 rg
  - local main、origin/main、actor HEAD、manifest、live/stage、launchctl、exact-run 與容量基線唯讀可判定
  - transition ordering 與 PANTHEON-G8-TRANSITION-EDGE-MAP-V1 一致
  - ACTIVATE 前 mutation accounting 全為零
  - bootstrap verdict 僅可 BOOTSTRAP_READY 或 BLOCKED
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-TRANSITION-TO-CANARY-READY-CYCLE-33-20260822-RESULT.md
---

# G8 transition to canary-ready — Cycle 33

## 工作名稱 → 正在做什麼 → 現在狀態

G8 production transition-to-canary-ready → 唯讀核對 current runtime 與唯一合法 transition 序列 → `BOOTSTRAP_ONLY / AWAITING ACTIVATE`

## Root question

在不建立 canary 的前提下，是否可用既有正式 authorities 將 current runtime 從 post-canary mixed cohort 安全收斂到 `ST-CANARY-READY`，並生成 current Rule 24／25 evidence？

## Current authoritative facts

- Pantheon `origin/main`：`db9fb4343df212fd3b65546b017aba159620a058`。
- runtime actor／manifest：`7b2f9b546bdac7c162c7ade2271eca6922020070`／generation `g33-7b2f9b54-20260821T192500Z`。
- live：coordinator＋四 lanes＋Capacity 為 activation-only loaded/no-PID；Publisher 為 normal exact-run `auto-i18n-en-614aa4dc3542ab2c5637`、max-runs 1，且目前未 loaded。
- private stage：G33 六份 normal plist，缺 Capacity；Publisher exact-run controls 存在。
- host free 約 52.7 GB，高於 20 GiB floor；此快照不替代 current two-cycle Capacity receipt。
- release-transition implementation／repair／re-review 已整合並推到 main；focused suite evidence `353 passed`，push 前 targeted regression `8 passed`。

## 第一拍：BOOTSTRAP_ONLY

1. 驗正式 thread、獨立 clean worktree、卡片可讀、HEAD 精確為 current main。
2. 先做 CodeGraph task-semantic query，再唯讀核對 actor、manifest、stage/live、launchctl、exact-run、transactions 與 disk。
3. 對照 `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md` 與 `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`，輸出唯一合法 edge sequence、每 edge authority、preconditions、invalidations、rollback 與 stop-loss。
4. 不執行 promotion、reset、Capacity、activate-only、restage、readiness、Rule 25 或 canary。
5. 回主線 verdict：`BOOTSTRAP_READY` 或 `BLOCKED`；列出 ACTIVATE 後每個 mutation invocation 的上限。

## ACTIVATE 後的固定邊界

只有主線在本 thread 明確送出 `ACTIVATE` 後，才可依序且逐 edge fail closed：

1. 以正式 promotion primitive 將 current main 收斂至 actor／manifest，保存可回復 snapshot。
2. 以正式 installers 建立 target six-service stage。
3. 以 `--reset-publisher-activation-only` 將 old-live Publisher 收回 activation-only；不得直接改 live plist。
4. 以 Capacity 正式 public gate 建立第七份 stage；Rule 24 任一 unknown 即停。
5. 以 aggregate `--activate-only` 啟用 target seven；驗七服務 activation-only loaded/no-PID。此步會消耗 private stage。
6. activation 後重新 restage Publisher exact-run；禁止沿用 activation 前 receipt。
7. 生成 current readiness、七段 capability、Rule 25 official receipt 與 fail-closed negative fixture；`canary_created=false`、`production_mutation=false`（readiness slice）。
8. 到達 `ST-CANARY-READY` 即停，回主線請求另一個 bounded canary 明確授權。

每一步最多一次正式 mutation invocation；任一 identity、digest、phase、capacity、loaded/PID、selector 或 receipt 不一致，立即 rollback 到契約允許狀態或標記 `UNKNOWN / NO CANARY`，不得跳關或重試。

## 絕對禁止

- 本卡不得執行 canary、Publisher child、release transaction、tag、push、deploy 或 steady autonomy。
- 不得修改 repo source／tests／config，不得另造 engine／supervisor／event family。
- 不得刪除既有 queue、state、failure、retry 或 transaction evidence。

## 正式 thread prompt

你負責 `CARD-PANTHEON-G8-TRANSITION-TO-CANARY-READY-CYCLE-33-20260822`，role=production-transition-operator、cycle=33。完整讀卡、Rule 24／25、release-state contract 與 transition edge map。第一拍只做 BOOTSTRAP_ONLY：驗 clean worktree/current main，先 CodeGraph，唯讀核對 current actor／manifest／live／stage／launchctl／exact-run／transactions／disk，整理唯一 edge sequence、authority、preconditions、invalidations、rollback、stop-loss與每種 mutation invocation 上限。禁止任何 production mutation、installer、promotion、reset、Capacity gate、activation、restage、readiness generator、Rule 25、canary、tag、push、deploy。只回 `BOOTSTRAP_READY` 或 `BLOCKED`；未收到主線在本 thread 明確送出的 `ACTIVATE` 不得跨線。

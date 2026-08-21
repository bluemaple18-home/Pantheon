---
id: CARD-PANTHEON-G8-RUNTIME-PROMOTION-STAGE-CONVERGENCE-CYCLE-32-20260821
execution_line_id: pantheon-g8-runtime-promotion-stage-convergence-cycle32
role: runtime-promotion-operator
status: queued
model_route: gpt-5.5-high
---

# G8 runtime source promotion 與七服務 private-stage convergence — Cycle 32

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：G8 runtime source promotion／private-stage convergence Cycle 32
- 正在做什麼：把已驗證的 canonical TMPDIR 修復正式 promote 到 runtime actor／manifest，使用既有正式入口重建 coherent seven-plist private stage，然後重跑 current non-production readiness。
- 現在狀態：`BOOTSTRAP_ONLY`；未收到主線 `ACTIVATE` 前只能唯讀 preflight。

## Root question

不重寫 Publisher、不拆 release gate；只收掉 Cycle 31 證實的兩個 blocker：

1. runtime actor／manifest 尚未承載 canonical TMPDIR 修復；
2. G33 private stage 缺 Capacity plist，只有六服務。

完成後判定是否已可回主線申請 production canary approval；本卡本身不建立 canary。

## 固定基線

- 主線 bootstrap source：`59b59c54db`（執行前回報完整 SHA）。
- canonical TMPDIR 修復：`d9e21adc9eb6439307341080f39e6d044e0492e9`。
- Cycle 31 RESULT：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-POST-FIX-PRECANARY-READINESS-CYCLE-31-20260821-RESULT.md`。
- Cycle 31 actor HEAD：`7b2f9b546bdac7c162c7ade2271eca6922020070`。
- Cycle 31 manifest generation：`g33-7b2f9b54-20260821T192500Z`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；`max-runs=1`。

## 允許範圍

收到主線 `ACTIVATE` 後才允許：

1. 以 repo 既有正式 promotion／runtime-manifest／private-stage 入口，把本卡 bootstrap source 的必要 current source promote 到既有 runtime actor。
2. 更新由正式入口管理的 actor commit、runtime manifest、private-stage control 與七份 staged plist。
3. private stage 必須精確包含 coordinator、四 lanes、Publisher、Capacity guard；identity、generation、manifest digest、actor HEAD 必須一致。
4. 執行唯讀 stage aggregate／actor-origin／manifest／queue／state／exact-run reconciliation。
5. 執行 current synthetic readiness、capacity 兩週期、official READY gate 與 fail-closed negative fixture。
6. 跑 canonical TMPDIR focused tests、Publisher terminal reset suite、相關 shell syntax 與 `git diff --check`。
7. 只新增唯一 RESULT，並以單一 commit 交付。

## 禁止範圍

- 禁止重寫 Publisher、coordinator、release gate 或另造第二套 stage validator。
- 禁止修改 repo source、tests、config、registry、shared metadata。
- 禁止操作 live plist cohort；禁止覆寫 live activation-only G23。
- 禁止 `launchctl load/bootstrap/kickstart/enable/disable/remove` 或啟動任何 production service。
- 禁止建立 canary、Publisher child、transaction、release commit、tag、push、deploy、schedule。
- 禁止刪除 queue／state／failure／retry evidence；禁止 reset exact run。
- 禁止安裝依賴、修改全域工具鏈或重試已知 `uv system-configuration` panic。
- 禁止以手寫 plist、臨時 shell 複製或直接改 manifest JSON 冒充正式入口。

## 執行順序與停損

1. `BOOTSTRAP_ONLY`：核對 formal thread、獨立 clean worktree、完整 HEAD、card blob、CodeGraph readiness。
2. 主線 `ACTIVATE` 後，先做 resource／capacity baseline與正式入口 dry preflight；任何欄未知即 `BLOCKED / NO CANARY`。
3. 鎖定唯一 promotion primitive 與唯一 stage-build primitive；若找不到正式入口，不得自行拼裝，直接 blocked。
4. promotion 前保存可回復的 actor／manifest／stage identity snapshot；不得碰 live cohort。
5. promotion 與 stage build 各最多一次正式 mutation invocation；同 blocker 不得盲重試。
6. mutation 後立即驗證 actor clean、source ancestor／blob identity、manifest digest、七 plist aggregate與 exact-run invariants。
7. 任一 invariant 失敗，使用正式 rollback 能力回復本卡前 snapshot；回報 `BLOCKED / NO CANARY`，不得進 readiness。
8. invariants 全通過才跑 current readiness；證據足夠立即停止，不跑 production/release 全套。

## 驗收契約

RESULT verdict 只能是：

- `READY_FOR_PRODUCTION_APPROVAL`：actor 已承載修復、manifest identity coherent、七 plist stage aggregate PASS、current readiness／capacity／negative fixture／focused tests 全通過，且 `canary_created=false`、production mutation（除本卡核准的 actor／manifest／private-stage promotion）為零。
- `BLOCKED / NO CANARY`：任一正式入口、identity、stage aggregate、capacity、readiness、test 或 rollback 證據不完整。

RESULT 必須列出：

- promotion 與 stage-build 正式入口；
- mutation 前後 actor HEAD、manifest digest／generation、stage plist count／names；
- source／installer blob identity；
- capacity baseline、兩週期與 cleanup／stop-loss；
- 七段 capability receipt、official READY 與 negative BLOCKED artifact digest；
- focused tests、shell syntax、diff gate；
- mutation accounting、rollback 是否觸發；
- production/canary/tag/push/deploy 均為零的證據；
- full commit SHA 與 clean status。

## 唯一交付

`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RUNTIME-PROMOTION-STAGE-CONVERGENCE-CYCLE-32-20260821-RESULT.md`

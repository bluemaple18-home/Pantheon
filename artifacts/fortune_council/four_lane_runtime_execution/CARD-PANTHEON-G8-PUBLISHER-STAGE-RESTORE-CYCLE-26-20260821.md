---
id: CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: implementation
cycle: 26
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: 規格固定；只重建一次性 private stage 並驗 Capacity，未升 Sol。
---

# 重建 G23 Publisher exact-run private stage

## 目標

Cycle25 已將 live 七服務收斂為 coherent G23 activation-only，但正式入口成功後消耗 private stage。本卡只重建同一份 G23 Publisher exact-run stage 並重驗 Capacity；保持零 activation、零 canary、零發布。

## 固定 authority

- 主線/card source：`eaf0182961`；runtime actor/source：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`。
- identity：`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`。
- generation：`g23-b1719c0d-20260821T022959Z`。
- live seven：Cycle25 `ALIGNED / NO CANARY`，coherent G23、activation-only、loaded/no-PID。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target `ASTRO-BASE-01:en`；Publisher `max-runs=1`。

## 前置閘門

1. host free disk `>=10%`、resource guard、current capability/readiness/fail-closed、Capacity proof 全 PASS。
2. 唯讀重驗 origin/main、actor、manifest、live seven、queue、state、exact run；任何 drift 即停。
3. private stage 必須為缺失／已被 Cycle25 正常消耗；若存在未知殘留或 failure receipt 不可解釋，立即停。

## 唯一順序

1. 保存 stage/live/queue/state/exact-run 前快照。
2. 從 current actor 執行 coordinator＋四 lanes 正式 `--install` 一次。
3. 執行 Publisher 正式 exact-run `--install` 一次，鎖定唯一 run、target 與 `max-runs=1`。
4. 執行 Capacity public `--preflight` 一次；必須 `preactivation_transition=accepted/PASS`。
5. PASS 後執行 Capacity 正式 `--install` 一次；重驗七服務 staged plist coherent G23，Publisher normal mode、其餘 activation-only 契約符合正式 manifest。
6. 驗證 live 七服務仍 coherent G23、loaded/no-PID；queue/state/exact run 不變。

## 可改範圍

- local-only private stage：僅既有 installers 可寫。
- `.work/CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-PUBLISHER-STAGE-RESTORE-CYCLE-26-20260821-RESULT.md`。

## 禁止

- 禁止修改 source、tests、config、workflow、manifest、live plist、queue、state、registry、sitemap、feed。
- 禁止任何 activation、launchctl mutation、barrier publish、canary、Publisher child、transaction、tag、push。
- 禁止 retry、第二次 install、換入口、手動拼 plist、另開 replacement thread。

## 驗收與停損

- coordinator/lane install=`0|1`；Publisher install=`0|1`；Capacity preflight/install=`0|1`；retry=`0`。
- activation/canary/Publisher child/transaction/tag/push=`0`；其他六服務 child I/O=`0`。
- 成功須證明 private stage coherent G23、exact run/max-runs 鎖定、Capacity PASS、live/queue/state/exact run 不變。
- 首次失敗立即停止；`git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `STAGED / CAPACITY PASS / NO CANARY`
- `BLOCKED / NO ACTIVATION`

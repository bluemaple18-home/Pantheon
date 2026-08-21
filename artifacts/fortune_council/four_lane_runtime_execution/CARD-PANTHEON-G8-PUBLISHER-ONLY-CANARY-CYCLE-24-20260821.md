---
id: CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-24-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
parent_card_id: CARD-PANTHEON-G8-RUNTIME-PROMOTION-CYCLE-23-20260821
role: implementation
cycle: 24
type: production_canary
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 固定 exact-run 的單筆 production transaction/tag/push；高回退成本但規格已鎖，不升 Sol。
---

# 發布 G8 單筆 Publisher canary

## 目標

使用既有 Publisher-only 正式入口，只發布 `auto-i18n-en-614aa4dc3542ab2c5637` 一筆，完成 transaction → annotated tag → ordinary push；其他六服務不執行 child、零第二筆內容副作用。

## 使用者授權與固定 authority

- 使用者於 2026-08-21 明確要求「繼續」，承接 Cycle 23 的下一步，授權本卡單筆 production canary、對應 transaction/tag/ordinary push 與必要 Publisher-only LaunchAgent mutation。
- source/origin/actor：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest digest：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`。
- identity digest：`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`。
- generation：`g23-b1719c0d-20260821T022959Z`。
- private stage digest：`aa801a5bd378bb4d7acd87bffb2407d31eb940d68ffabf4e2b14507cdd603c7b`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target：`ASTRO-BASE-01:en`；`max-runs=1`。

## Mutation 前硬閘門

1. 保存 queue/state/transaction/content/registry/sitemap/feed/ref/tag/remote/live/stage before snapshot。
2. 重新產生 current 七步 capability receipt：`create → run → select → publish → transaction → tag → push`；每步必須有正式入口、I/O、identity/correlation、正向 PASS 與 fail-closed 負向證據。
3. 以 current `production_canary_readiness_gate.py` 驗 `READY`、`canary_created=false`；容量與 preactivation transition 必須 PASS，host free disk `>=10%` 且 `>=20 GiB`。
4. 驗 actor clean、authority tuple 完全相符、七份 staged plist aggregate PASS、Publisher exact-run args 唯一、live 七服務 loaded/no-PID、queue 140 且 exact run 唯一完整。
5. 任一非 PASS：`BLOCKED / NO CANARY`，production mutation 0；不得改 source 或重跑。

## 唯一執行序列

1. 從正式 runtime actor呼叫一次既有 Publisher-only bounded activation入口；只接受本卡 manifest/generation/exact-run/max-runs。
2. 禁止 direct Publisher Python normal path冒充正式 canary；不得手動改 plist、queue、transaction、content、registry、tag或ref。
3. 入口呼叫後禁止 retry。立即監測 exact run ownership、selection、transaction、content、tag、push與 Publisher PID；第二筆或 unknown outcome 立即走既有 bootout/rollback並停止。
4. 成功須驗 exact run consumed恰一次、transaction committed、目標內容唯一、registry/sitemap/feed一致、annotated release tag唯一、origin push成功、actor clean。
5. 驗其他 139 runs 未變、其他六服務零 child I/O、七服務回到正式入口定義的安全 loaded/no-PID terminal topology。

## 可改範圍

- 正式 Publisher-only activation入口允許的 LaunchAgent/runtime state。
- exact run 對應的唯一 transaction、content、registry、sitemap、feed、annotated tag與 ordinary push。
- `.work/CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-24-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-24-20260821-RESULT.md`。

## 禁止與停損

- 禁止 source/tests/config/workflow/runtime manifest/queue payload/selector/plist 手動修改。
- 禁止四線批次、其他 run、第二筆 canary、force push、merge、rebase、retry、Reviewer、Repair、RCA或replacement thread。
- 正式入口前 blocker：`BLOCKED / NO CANARY`。
- 正式入口後 transaction/tag/push 或唯一性失敗：正式 rollback/bootout後 `BLOCKED / NO RETRY`。
- `git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `PUBLISHED / VERIFIED`
- `BLOCKED / NO CANARY`
- `BLOCKED / NO RETRY`

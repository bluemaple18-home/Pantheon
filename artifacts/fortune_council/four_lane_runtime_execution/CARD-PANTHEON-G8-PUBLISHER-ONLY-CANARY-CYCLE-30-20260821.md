---
id: CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-30-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: implementation
cycle: 30
thickness: strict
risk: production
model: gpt-5.5
reasoning: high
model_reason: 規格與唯一 run 已固定；單筆 production canary，未升 Sol。
---

# 發布 G8 單筆 Publisher canary（Cycle30）

## 目標

在 live 七服務與 private stage 均 coherent G23、Capacity PASS 後，只發布唯一 exact run，驗證 Publisher transaction、tag 與 ordinary push。任何失敗立即停止，不 retry、不發布第二筆。

## 固定 authority

- 主線/card source：`d787e9ebdf`；runtime actor/source：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest／identity／generation：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`／`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`／`g23-b1719c0d-20260821T022959Z`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target `ASTRO-BASE-01:en`；Publisher `max-runs=1`。
- Cycle25：live seven coherent G23、activation-only、loaded/no-PID。
- Cycle29：seven-plist private stage coherent G23、Capacity `accepted/PASS`。

## 前置閘門

1. current capability receipt 七步、official readiness、fail-closed fixture、host Capacity、actor/origin/manifest/live/stage/queue/state/exact run 全 PASS。
2. 唯讀 bounded wait 最多 300 秒；七服務連續三次 loaded/no-PID 才允許唯一 mutation；否則 `BLOCKED / NO CANARY`。
3. Publisher formal deployment preflight 必須鎖定 exact run、target、`max-runs=1`、ordinary push；任何 drift 即停。
4. 保存 transaction/tag/ref/content/queue/state/live/stage 前快照與 rollback 所需證據。

## 唯一 production mutation

1. 從 current runtime actor、固定 `TMPDIR=/private/tmp`，host-level 執行正式 `scripts/install_agy_gemini_coordinator_launchd.sh --activate-publisher-only` 一次。
2. 禁止 sandbox-first、retry、第二次 invocation、direct module、手動 launchctl、替代入口。
3. 只准 Publisher child 執行一次；其餘六服務 business child I/O 必須為 0。

## 驗收

- exact run 從待發布狀態完成正式 transaction，產生唯一可對帳內容變更、唯一 tag 與 ordinary push；remote/ref 與 transaction identity 必須互綁。
- queue/state/content/tag/origin 前後差異只能是此 exact run 的預期效果。
- activation invocation=`1`；Publisher child=`1`；transaction/tag/push=`1`；其他六服務 child I/O=`0`；retry=`0`。
- 失敗須保留 fail-closed／rollback receipt，並證明未有未對帳的 partial publish。

## 禁止

- 禁止第二筆 run、force push、修改 source/config/workflow/manifest、放寬 gate、另開 replacement thread。
- 禁止失敗後重建 stage或另一次 activation；禁止自行擴量。

## 交付與停損

- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-30-20260821-RESULT.md`。
- `git diff --check` PASS；candidate commit 只含 RESULT。
- 本卡首次正式 invocation 後不論成敗都停止。

## 終局

- `PUBLISHED / VERIFIED`
- `BLOCKED / NO CANARY`
- `BLOCKED / NO RETRY`

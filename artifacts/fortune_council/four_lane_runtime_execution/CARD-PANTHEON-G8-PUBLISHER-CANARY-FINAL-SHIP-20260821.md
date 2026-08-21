---
id: CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821
status: ready
priority: P0
task_type: production_ship
required_base_sha: 4c16a2f4ab81865ba854cff6cf79a82dfe700c71
authorized_exact_run_id: auto-i18n-en-614aa4dc3542ab2c5637
authorized_target: ASTRO-BASE-01:en
---

# G8 Publisher 單筆正式開通完整收尾

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Publisher 單筆正式開通完整收尾 → 從修復版 promotion、one-shot stage、Capacity/readiness 到 exact-run canary 一次完成 → READY

## 目的

以主線 4c16a2f4ab81865ba854cff6cf79a82dfe700c71 為唯一 source authority，完成 runtime actor promotion、one-shot Publisher stage、正式閘門與指定 exact run 一次發布。不得再拆 Cycle、Repair 或 replacement 卡。

## 已知基線

- Cycle30 因 production env 污染 fail-closed；actor 已 recovery，tag/push=0。
- Publisher 曾因 StartInterval=60 自動第二次 child；已精確 bootout，終態 service not found。
- 修復已通過 focused 14、受影響檔 373、release tests 420、shell syntax 與 diff check。
- exact run：auto-i18n-en-614aa4dc3542ab2c5637；target：ASTRO-BASE-01:en。

## 唯一執行序

1. 驗 formal thread、獨立 clean worktree、exact base、card blob、CodeGraph；CodeGraph 不可用時只做限域查詢，不另開卡。
2. 一次收齊 source/origin/actor、queue/state/exact run、七服務、live/stage/manifest/barrier、容量與磁碟現況。
3. 所有 preflight PASS 後，才以既有正式 promotion 入口把修復版帶入 runtime actor；禁止手改 actor。
4. 以正式入口建立 coherent stage；Publisher 鎖 exact run、max-runs=1、ordinary push，並驗 one-shot plist 無 StartInterval/KeepAlive、RunAtLoad=true。
5. 依 Rule24 跑 host Capacity/preactivation；依 Rule25 取得 create→run→select→publish→transaction→tag→push readiness receipt。
6. 七服務連續三次 no-PID 後，只執行一次正式 --activate-publisher-only。activation=1、Publisher child≤1、其他六服務 child I/O=0。
7. 驗 exact run transaction、release commit、annotated tag、ordinary fast-forward push、actor/origin clean coherent。
8. 成功或失敗都做終態快照；不得 retry。若 Publisher 有週期或 retry 風險，立即精確 stop-loss bootout 唯一 Publisher label，不動其他六服務。

## 允許

- 正式 promotion、stage、Capacity/readiness、Publisher-only activation，以及指定 exact run 的單筆 transaction/tag/push。
- 寫本卡專屬 .work evidence、RESULT 與必要正式 receipts。
- 必要 host execution；首次即用正確 host 路徑。

## 禁止

- 修改 source/tests/rules，或手改 plist、barrier、queue、state、actor。
- 第二次 activation、第二個 Publisher child、第二筆 run、替代 exact run。
- normal aggregate activation、其他六服務 business child I/O。
- force push、非 fast-forward push、手工 tag/push。
- 新建 Cycle、Repair、Reviewer、replacement thread。
- 任一 blocker 後繼續補洞。

## 停止條件

- 任一 current preflight、Capacity、readiness、identity、stage、barrier、queue/exact-run gate 非 PASS。
- source/origin/actor 無法用既有正式 promotion 入口收斂。
- Publisher child >1、其他六服務 I/O >0、transaction 不可對帳、push outcome unknown。
- 任何需要改 source 才能繼續的發現。

命中即 BLOCKED / NO RETRY，保留證據、必要時 stop-loss，寫 RESULT、commit、停止；禁止衍生新卡。

## 交付

- CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821-RESULT.md
- 列每階段 PASS/FAIL、mutation accounting、exact run、transaction、commit/tag/push、七服務 I/O、終態快照。
- 必須列未做、未驗、殘餘風險。

## 完成定義

只有 exact run 一筆完成 transaction、annotated tag、ordinary fast-forward push，Publisher child=1、其他六服務 child I/O=0、actor/origin clean coherent，才可回報 SHIPPED。其他一律 BLOCKED / NO RETRY。

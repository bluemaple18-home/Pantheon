---
id: APF-004-CANARY
title: 鎖定並執行 Existing Publisher 最小 production canary
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: production publish／transaction／tag／push 與容量 stop-loss 需要固定核心契約、精確 identity 與 fail-closed 執行
parent_candidate: 75dd38bd07f6d0bce4cc6657a52f1ede1eb0a4f9
traces_to:
  - US-004
  - FR-012
  - FR-014
  - SC-001
  - SC-003
  - SC-008
---

# APF-004-CANARY｜Existing Publisher 最小 production canary

## 使用者授權

使用者於 2026-08-13 在主對話明確授權 APF-004 production canary。授權只涵蓋最小批次；不含擴量、常駐排程、全面發布或 APF-005。

## 任務五行卡

- 目標：以 Existing Publisher 對 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 各一筆精確 run 依序執行 bounded production canary。
- 可做：唯讀 preflight、鎖定四筆 payload、容量基線／監控、逐筆 publisher transaction、tag、atomic push、站點／release record 驗證、停止與 rollback rehearsal。
- 禁止：不得掃描或處理未鎖定 run、不得 `max-runs > 1`、不得啟用常駐排程／LaunchAgent、不得擴量、不得刪 queue/evidence、不得修改 production code 來繞過 gate。
- 驗收：四 lane 各有唯一 publication receipt；同一 lane 的 publish→transaction→tag→push 可追溯；失敗立即停止後續 mutation，無 duplicate publish；容量與 stop-loss 持續 PASS。
- 證據：精確 payload lock、readiness／capacity 重驗、每次 mutation result、remote SHA/tag、release record、容量 before/after、rollback／stop receipt。

## 兩階段硬邊界

### Phase 1：精確 payload lock（立即執行）

1. 從 clean `75dd38b...` source 與正式 production runtime 做唯讀核對。
2. 重跑 official readiness gate；核對 committed receipt `READY`、`canary_created=false`。
3. 重新量測 host free、專案 bytes/files、RSS、swap；低於容量門檻即 `NO-GO`。
4. 確認 production actor/runtime SHA、digest、origin/main、queue/state roots、credential authority 與 publisher push mode。
5. 依 campaign identity 確定四個唯一 exact run ID、article ID、locale、預期 publication target 與執行順序。
6. 產出 final payload summary：工具／入口、四筆 target、repo/remote、預期 tag/version、外部模型資料邊界、所有 mutation 與 rollback/stop 指令摘要。
7. Phase 1 只讀；不得 create run、呼叫外部模型、publish、transaction、tag、push、deploy、schedule 或 production activation。
8. 將 payload summary 回主線；沒有主線回傳 `FINAL_PAYLOAD_CONFIRMED` 不得進 Phase 2。

### Phase 2：bounded canary（只在確認後）

1. 每個 lane 只允許一個 exact run；依序 `new → rewrite → i18n-new → i18n-rewrite`。
2. 每筆 mutation 前重驗 exact identity、capacity、origin/head、runtime digest、queue/state root、previous receipt 與 duplicate suppression。
3. 每筆只呼叫既有正式入口；`--max-runs 1`、exact selector、release gate 不得略過、push 必須符合既有 atomic transaction。
4. 每筆後核對 publication artifact、ledger transaction、tag、origin/main SHA 與 release record；任一不一致停止，不執行下一 lane。
5. 每週期後重新量測容量/RSS/swap。觸發 stop-loss 時只停止本 canary，不刪 evidence／queue、不處理其他專案。
6. 最後執行 rollback/stop rehearsal；不得回滾已合法公開的內容來冒充 rehearsal，使用既有 feature/actor stop boundary。

## 必須重驗的 authority

- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/package/production-canary-capability-receipt.json`
- ai-core `production_canary_readiness_gate.py` 回 `READY`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/capacity/capacity-receipt.json`
- host free 保留至少 `max(20 GiB, 10%)`
- runtime actor clean，SHA/digest 與正式 contract 相符
- 遠端與 credential connection active；不得輸出 secret

## 允許寫入

- `.work/APF-004-CANARY/**`
- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/**`
- Existing Publisher 正式 transaction allowlist 內的 publication／registry／release record
- Existing Publisher 建立的單次 release commit/tag 與 atomic origin push

其餘 code、config、tests、LaunchAgent、scheduler、全域設定不可修改。若既有入口不足，停止並回報 scope change，不得現場修 code。

## 交付狀態

- Phase 1：`PAYLOAD_LOCKED | NO-GO | BLOCKED`，附 exact targets 與 final payload summary。
- Phase 2：`CANARY_PASS | CANARY_STOPPED | BLOCKED`，附四 lane 狀態、remote identities、容量證據、duplicate suppression 與 rollback/stop receipt。
- 不得以單一成功 log、exit 0 或本機 commit 代替 remote publication/tag/push 證據。

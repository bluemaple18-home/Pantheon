---
id: CARD-PANTHEON-FOUR-LANE-OWNER-RESCOPE-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: mainline_control
cycle: 1
model: gpt-5.6-sol
reasoning: high
status: complete
thickness: standard
risk: medium
---

# Pantheon 四線 Owner 重切裁決

## 目標與邊界

- 從 canonical `main` 的 `0f61545f8c6b561742b27792b8fef11ae8b1ccc5` 建立 docs-only 裁決，終止 C-C/T acceptance program，並把剩餘工作縮回 resident operability 的兩個真缺口。
- 本卡只允許新增下列四份文件，不修改程式碼、測試、runtime、registry、ledger、plist 或 production 狀態：
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-OWNER-RESCOPE-20260902.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/OWNER-RESCOPE-DECISION-PANTHEON-FOUR-LANE-GO-LIVE-20260902.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-OPEN-ITEMS-20260902.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/CCT-FORENSIC-ARCHIVE-INDEX-20260902.md`
- 不 merge、rebase、squash、刪除或改寫任何 C-C/T branch；不把 C-C/T implementation 帶入本 branch。
- 本卡允許建立一個只含四份 allowlist 文件的 local docs commit；不授權 push、merge、deploy、provider call、真實 `launchctl`、Gate D/E、service start 或 public mutation。

## Owner 已鎖定的裁決

```text
TERMINATE_C_C_T_ACCEPTANCE_PROGRAM
ACCEPT_HISTORICAL_PRODUCTION_PUBLICATION_PATH_EVIDENCE
DO_NOT_CLAIM_ALWAYS_ON_OPERABILITY_YET
REMAINING_BEHAVIORAL_GAPS = OPEN-1 + OPEN-2
GO_LIVE_PREFLIGHT = REQUIRED_NON_PROGRAM_GATE
```

- 歷史 production evidence 只結案 per-run correctness；resident／unattended operability 尚未證明。
- 四條 service lane 仍是 `new`、`rewrite`、`i18n-new`、`i18n-rewrite`；產品配額把兩條 i18n lane 合併為同一個 translation publication class。
- C-C/T 持續 authority 模擬器重複證明已結案的 per-run 欄位，因此終止；其程式品質不因此被否定。

## OPEN-1 固定結案門檻

- 先唯讀映射現有 transport、run/article 與 Publisher retry authority；不得新增 retry counter。
- 只有真實觀察到同一 item 達既有正式上限、實際進入 terminal/manual、實際釋放槽位，且下一個不同 item 由既有 selector 選出並開始執行，才能結案。
- 讀 code、fixture 推論、Controller 指定下一篇，或 2026-08-26「registry 有 failed: 2 但同 cycle 仍 seed/dispatch」案例，均不得單獨宣稱 OPEN-1 已結案。

## OPEN-2 固定政策與未決輸入

- Asia/Taipei calendar date 的成功 publication quota：`new = 1`、`rewrite = 1`、`translation = 1`、`total = 3`；translation 由 `i18n-new` 與 `i18n-rewrite` 共用。
- quota 必須在 Publisher publication transaction mutation 前、既有 Publisher lock 內，以既有 ledger／release identity 持久化且原子判定；不得新增 state store。
- 同一 `run_id` crash replay 只能計數一次，也不得因「publication 已成功、ledger 尚未完成」而放出額外 publication。
- quota date 在 transaction admission 時以 Asia/Taipei 固定；跨午夜的同一 `run_id` 仍歸入該 admission date。成功只扣一次；失敗釋放 success reservation，但仍計入成本上限。
- 成功 quota 不等於成本上限。OPEN-2 必須另含 daily admitted-attempt 或 provider-call hard cap；實作前先由既有 call/retry authority 推導最小安全數值並交 Mainline 鎖定。沒有明確數值、持久化 authority 與 fail-closed 測試時，不得 activation；不得把缺口默認為已接受風險。

## 固定 go-live preflight

這不是第三項 acceptance program，且清單固定只有四項，不得擴張：

1. 七服務 install/load 乾淨。
2. cap 設定存在，且 Publisher 實際讀到。
3. 一次 dry cycle。
4. production fingerprint 無漂移。

本卡不執行 preflight 或 activation。後續即使 OPEN-2 完成，啟動仍需 Owner 另行明示授權。

## 任務切片

| Slice | 內容 | 依賴 | 完成證據 |
|---|---|---|---|
| S0 | docs-only Owner 重切 | 無 | 本卡其餘三份文件一致且 `git diff --check` 通過 |
| S1 | OPEN-2 唯讀 seam mapping、數值裁決、最小 quota 實作 | S0 | RED→GREEN、restart/manual/concurrency/crash replay 負向矩陣；production mutation 0 |
| S2 | OPEN-1 唯讀歷史證據 mapping | S0；可與 S1 mapping 平行 | 真實 evidence 若不足只回 `OPEN-1_UNPROVEN`，不得用 code inference 補足 |
| S3 | 固定四項 go-live preflight | S1；另需 Owner activation authorization | 四項逐項 evidence；不得新增第五項 |

允許的加速順序為 `S1 → S3 → bounded activation → production 中觀察 S2`，但本卡只記錄選項，不授權 activation。

## S0 驗收

- 四份 allowlist 文件存在且互相引用一致。
- `git diff --check` 通過。
- `git status --short` 只出現 allowlist 文件。
- production/public mutation、provider、真 `launchctl`、Gate D/E、push、merge、deploy：`NOT_RUN`。

---
id: CARD-PANTHEON-G8-V0394-FAILED-EXTERNAL-JOB-REPLACEMENT-REVIEW-20260825
status: ready
role: Reviewer
review_mode: full
base_commit: 998a797f3618a47a3d0493503e937a06b84e3da3
candidate_commit: a0c3ffe33e9dbbb80524fe75d0486063e02d67d7
repair_thread: 01a037e9-0ce8-7990-90d0-d4d2cc674d1b
model: gpt-5.5
thinking: high
---

# V0393 failed external job replacement 獨立審查

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：V0393 failed external job replacement 獨立審查。
- 正在做什麼：唯讀審查 candidate `a0c3ffe33e9dbbb80524fe75d0486063e02d67d7` 相對 base `998a797f3618a47a3d0493503e937a06b84e3da3` 的正確性、回歸、安全、測試與 production recovery 風險。
- 現在狀態：ready；Repair 已交付，完整兩檔測試 `450 passed`，尚未整合、push、promotion 或執行 production replacement。

## 唯一責任

只判定 V0393 candidate 是否可整合。不得修改 source、tests、production runtime、queue/state、launchctl、model route、manifest、activation、Publisher 或 publish/push。

## 必讀範圍

- V0393 Repair 卡與 evidence。
- `git diff 998a797f3618a47a3d0493503e937a06b84e3da3..a0c3ffe33e9dbbb80524fe75d0486063e02d67d7 --` 下列檔案：
  - `scripts/agy_gemini_outbox.py`
  - `scripts/agy_gemini_coordinator.py`
  - `tests/test_agy_gemini_outbox.py`
  - `tests/test_agy_gemini_coordinator.py`
  - V0393 Repair 卡與 evidence。

## Spec axis

- `CLI_NONZERO` 必須仍為 terminal；不得成為一般 retry。
- replacement 只允許明確 authority、同 run/article/correlation/namespace、active registry、exact last-job、archive+failed receipt、無 success result。
- replacement 必須保留原 model/role/prompt/schema/operation/request logical identity，只新增 replacement lineage/job identity。
- 同 source failed job 最多一個 replacement；同 authority replay idempotent；不同 authority、identity drift、第二 replacement、缺 artifact 全部 fail-closed 且 zero mutation。
- plan-only 必須 side-effect free；execute receipt 必須 machine-readable。
- formal decision 存在前，原 failed result 不得被改道；存在後只能導向指定 replacement response。

## Standards axis

- 檢查鎖、TOCTOU、部分寫入、rollback、crash consistency、symlink/path escape、未受信 JSON、authority digest 比對。
- 檢查既有 API/CLI/schema 相容性與 queue runner 行為回歸。
- 檢查測試是否真正覆蓋上述風險；不得只接受 `450 passed` 數字。
- 只審本次 diff 與必要相鄰程式；禁止全 repo 漫遊或風格重寫。

## 驗證

- 必跑 `git diff --check` 於 candidate diff。
- 允許在既有 candidate worktree 唯讀檢查；若重跑測試，只跑受影響 targeted tests，禁止建立第二套實作或改檔。
- Findings 必須含 severity、category、`path:line`、觸發條件、證據、風險、建議修法、validation gap、confidence。

## 交付

- 無 P0/P1、無 production safety blocker：`GO`。
- 有 P0/P1 或 production safety blocker：`REPAIR_REQUIRED`，列最小修復範圍；回原 V0393 Repair thread，不開第二個 Repair。
- P2/P3 分列，不得用單一 warning 阻擋。
- RESULT 只能寫本卡與專屬 evidence；不得 merge、push、deploy、archive。

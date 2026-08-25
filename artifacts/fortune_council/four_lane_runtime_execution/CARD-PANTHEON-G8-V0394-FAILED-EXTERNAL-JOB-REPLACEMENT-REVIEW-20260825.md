---
id: CARD-PANTHEON-G8-V0394-FAILED-EXTERNAL-JOB-REPLACEMENT-REVIEW-20260825
status: completed
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
- 現在狀態：completed；審查結論為 `REPAIR_REQUIRED`，尚未整合、push、promotion 或執行 production replacement。

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

## RESULT

狀態：completed

Verdict：`REPAIR_REQUIRED`

候選 commit：`a0c3ffe33e9dbbb80524fe75d0486063e02d67d7`

審查證據：

- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0394_failed_external_job_replacement_review_20260825/evidence.md`

Findings：

- [P1] replacement request 會先於 formal decision/state transition 暴露給 runner - `scripts/agy_gemini_coordinator.py:1631`
  - Category：production safety / correctness / crash consistency。
  - Trigger：`replace-failed-external-job --execute` 在寫入 `outbox/*.json` 後、decision 與 run state durable 前 crash/kill，或 runner 在這個 window 醒來。
  - Evidence：candidate 在 `scripts/agy_gemini_coordinator.py:1631` 先寫 live outbox，`1635` 才寫 formal decision，`1637-1645` 才更新 state；runner 會在 `scripts/agy_gemini_runner.py:524` 掃 `outbox/*.json`，並在 `551` 直接 claim 到 processing，不共用 replacement lock，也不要求 decision 已存在。
  - Risk：replacement provider call 可在 formal decision 前被處理，原 failed job 仍無合法 routing decision，造成 orphan replacement、exactly-once recovery 破壞，以及 mutation all-or-none 契約失效。
  - Suggested fix：先將 replacement request 寫到 runner 不可見 staging path，decision/state 具備 durable/recoverable receipt 後再原子 publish 到 `outbox`；或做可恢復 two-phase protocol，讓 replay 能完成/回滾 half-written receipt，而不是留下 `request already exists without decision`。
  - Validation gap：現有測試涵蓋 happy path、same-authority replay、identity drift、plan-only zero mutation，但未覆蓋 outbox publish 與 decision/state 之間的 crash/partial-write/runner-race。
  - Confidence：high。

Non-blocking：

- [P2] archive/failed receipt 仍有 path validation TOCTOU hardening gap - `scripts/agy_gemini_coordinator.py:1514`
  - Category：security / production hardening。
  - Trigger：local concurrent process 在 `is_file/is_symlink/stat` 與後續 `read_bytes/read_text` 之間替換 archive 或 failed receipt path。
  - Evidence：source archive 在 `1514-1524` 做 path check 後再讀；failed receipt 在 `scripts/agy_gemini_outbox.py:474-482` 做 path check/stat/read 分離，未用 `O_NOFOLLOW` descriptor + `fstat` 綁定同一 inode。
  - Risk：驗證與實際讀取可能不是同一 filesystem object；在 mutable production queue 下會削弱未受信 JSON / path escape 防線。
  - Suggested fix：用 `openat`/`O_NOFOLLOW`/`fstat` 驗證同一 descriptor，從該 descriptor 讀取並限制 size；補 concurrent replacement harness。
  - Validation gap：現有 replacement tests 未模擬 path replacement race。
  - Confidence：medium。

驗證：

- `git diff --check 998a797f3618a47a3d0493503e937a06b84e3da3..a0c3ffe33e9dbbb80524fe75d0486063e02d67d7`：passed with no output。
- Repair evidence candidate-only 讀取確認：`450 passed in 451.32s (0:07:31)`。

邊界：

- 未 checkout candidate，未修改 source/tests/runtime，未 merge/push/deploy/promotion/archive，未操作 production replacement。

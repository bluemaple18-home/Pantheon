---
card_id: CARD-PANTHEON-LOCALE-PLAN-TERMINAL-RESUME-FRESH-ATTEMPT-REPAIR-20260806
status: VERIFIED_READY_FOR_INTEGRATION
risk: production-control-plane
base_sha: fb18bdde5942137372cf0882bee4a565e4f7577c
---

# 修復 locale plan terminal resume fresh attempt

## 可重現失敗

`auto-i18n-ja-af38c7e7beacd0001ccd` 因 `LocalePlanValidationError` terminal failed。既有 `resume` 將狀態改回 active，但保留舊 `last_job_id`；下一個 exact cycle 立即重讀舊 response，再次同錯失敗，沒有建立新 provider job。

## 目標

- 僅對已 terminal 的 `LocalePlanValidationError`，`resume_run` 清除舊 `last_job_id`，使修復後 prompt 能建立 fresh request。
- 其他 failure 類型仍保留既有 `last_job_id` 與 retry／replacement 語意。
- 不改 replacement concurrency、exact selector、deterministic gate、Reviewer 或 provider transport。

## 可修改

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡

## 驗收

- RED：terminal locale-plan failure resume 後仍有 `last_job_id`。
- GREEN：該類型清除 `last_job_id`；其他 terminal failure 保留。
- `tests/test_agy_gemini_coordinator.py` 全檔通過。
- exact-run regression、Python compile、`git diff --check` 通過。
- 先交付／整合候選；另做 production actor 對齊後才可重跑 canary。

## 禁止

- 不直接編輯、刪除或搬移 production queue／inbox／archive／state。
- 不啟用 broad i18n runner，不處理其他 waiting replacement。
- 不降低 gate，不重寫 retry framework，不呼叫真實 provider。

## 驗證結果

- RED：`1 failed`，證明舊 `resume_run` 保留 terminal locale-plan job lineage。
- GREEN：新舊 failure 分流測試 `2 passed`。
- Coordinator 全檔：`80 passed`。
- Exact-run：`6 passed, 170 deselected`。
- Python compile、`git diff --check`、DBG scan：通過。
- Production：未套用此候選；broad 服務已恢復，target 仍 fail closed，沒有新 provider job／publish。

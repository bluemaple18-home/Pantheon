# Pantheon Lane Continuation Repair

## 目的

讓四條內容 lane 在同一個 run 完成 writer、reviewer 與 repair 階段前持續推進該 run，避免翻譯 backlog 採 breadth-first 輪轉而數小時沒有任何可發布成果。

## 已確認根因

1. 正式 LaunchAgent 被部署為 `AGY_GEMINI_NEW_ONLY=1`，舊文與翻譯 lane 被明確停用；已切回 `0`。
2. 完整模式恢復後，`_active_states()` 每次 pending 都更新 `updated_at`，而 `_select_lane_states()` 直接取更新時間最舊的 run，導致同一 lane 在所有 active run 間輪轉。
3. 翻譯 lane 有 36 個 active run；現行排程會先替所有 run 做 writer，再回到第一個 run 做 reviewer，單一可發布成果延遲過長。

## 可改檔案

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡

## 禁止範圍

- 不降低 writer、reviewer、deterministic gate 或發布 gate。
- 不刪除、重建或跳過現有 queue job。
- 不修改文章內容、registry、sitemap、feed 或 release ledger。
- 不改新文／舊文／翻譯的 lane 分類契約。

## 驗收

1. 新增可在修復前重現「同 lane 第二輪切到下一個 run」的測試。
2. lane mode 每輪仍只選每條 lane 一個 run。
3. 同一 lane 持續選最早註冊的 active run，直到 complete／failed 後才選下一個。
4. 受影響測試、完整 coordinator 測試與 `git diff --check` 通過。
5. 部署後觀察既有翻譯與舊文 job 產生 candidate／review，並由 publisher 實際發布至少一個成果。

## 交付

- 一個最小修復 commit。
- 測試與正式 runtime 證據。
- 完成後移除本次臨時 worktree 與 branch。

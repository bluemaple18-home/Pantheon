# CARD-PANTHEON-G8-APF004-BACKLOG-AUTHORITY-REPAIR-20260818

## 五行派工契約

- 工作：修復 APF-004 create-run adapter 對 new article 使用 filtered matrix backlog 的 authority 錯誤。
- 範圍：回原 Repair thread／原 worktree；只改 `scripts/agy_gemini_coordinator.py` 與 `tests/test_agy_gemini_coordinator.py`。
- 禁區：不動其他 candidate 檔、不重構、不改 gate、不碰 production／push／tag／publish／LaunchAgent。
- 驗收：既有 4 個失敗測試先 RED→GREEN，canonical 4 測試 GREEN，最後 16-file suite 一次全綠。
- 證據：`.work/CARD-PANTHEON-G8-APF004-BACKLOG-AUTHORITY-REPAIR-20260818/`、durable logs、candidate SHA。

## Identity

- `chain_id`: `PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818`
- `role`: `repair-continuation`
- `cycle`: `1`
- `model`: `gpt-5.6-terra`
- `reasoning`: `medium`
- `reuse_thread`: `01a0156e-2888-7b73-8498-472e6ff172f4`

## 已知 RED

- Durable receipt：`600 passed, 4 failed`。
- 四個失敗均為 `ValueError: create-run adapter new article is not in matrix backlog`：
  - `test_apf_004_single_create_only_adapter_rejects_root_overlap_and_state_collision`
  - `test_apf_004_create_run_adapter_plan_only_is_deterministic_and_zero_write`
  - `test_apf_004_create_run_adapter_apply_is_idempotent_and_resume_safe`
  - `test_apf_004_create_run_adapter_rejects_root_overlap_and_state_collision`
- 排序假說：new brief builder 以 filtered matrix backlog 當 article authority；若改用 workset item／未過濾 canonical authority，四個既有 RED 應同時轉綠。

## 執行契約

1. 先查 CodeGraph；無結果才限域讀 coordinator 的 create-run adapter／brief builder 與上述四測試。
2. 先重跑上述四測試一次確認同症狀 RED；若症狀不同即停止。
3. 只做最小 authority 修復並補一個能防止 filtered-backlog recurrence 的 observable regression assertion；不得旁改。
4. 依序驗證：四個 RED→GREEN、原 canonical 四測試 GREEN、`git diff --check`、無 `[DBG-`。
5. 以上全綠後才執行一次帶 `tee` durable log 的原 16-file suite；全綠才提交所有既有 candidate 檔與本次測試，回報 SHA 與 clean state。

## 停止條件

- 同一 authority 假說修後仍 RED，或需要超出兩檔修復 scope。
- 完整 suite 失敗或 receipt 缺終態：保存證據並停止，不重跑。
- 任何 production／外部狀態 mutation。


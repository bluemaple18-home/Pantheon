# Rewrite 第二輪：歷史 state identity collision

- 日期：2026-07-31
- lane：`rewrite`
- production Gemini calls：0（本修補與測試皆未呼叫外部模型）

## Root cause

官方 seeder 以文章 identity 產生固定 `run_id`。歷史 coordinator state 仍占用該
ID，但 `run_dir` 指向已移除的舊 worktree；backlog 無法從失效路徑讀回文章
identity，因此把文章重新分類成 `unattempted`。seeder 隨後先寫入同名 run
目錄，再於 `register_run` 撞上既有 state，拋出
`ValueError: registered run identity collision`。

## RED

測試：

`tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_preserves_orphan_state_and_uses_retry_lineage`

修補前結果：失敗於 `register_run`，錯誤為
`registered run identity collision`。

## GREEN

seeder 現在會在寫檔前，同時檢查 private run 目錄與 coordinator state ID；
若 base ID 已被任一歷史實體占用，依序選擇第一個未使用的
`retry-01` 至 `retry-100` lineage。既有 state、run 目錄與檔案均保持原樣；
若 100 個 retry lineage 全部占用則 fail closed。

驗證：

- lineage regression：2 passed
- `tests/test_agy_gemini_coordinator.py`：44 passed
- coordinator + publisher：130 passed，1 個既有 warning
- 全套：820 passed，2 個既有 warning
- `git diff --check`：通過

## 尚未冒充完成

此證據只證明 seeder root cause 已修復；`rewrite` lane 必須在 production
完成真實 Gemini 生成、Reviewer 驗證與 Publisher release 後才可驗收。

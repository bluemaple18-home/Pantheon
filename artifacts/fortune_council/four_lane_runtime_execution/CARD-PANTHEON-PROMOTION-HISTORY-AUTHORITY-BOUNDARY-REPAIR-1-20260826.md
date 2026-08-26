---
id: CARD-PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-REPAIR-1-20260826
chain_id: PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-20260826
role: repair
cycle: 1
model: gpt-5.5
reasoning: high
model_reason: bounded P1 repair of promotion evidence path containment
status: ready
thickness: strict
risk: high
parent_candidate_sha: d60a078fc204c87e3d4811a9b1ee1678123d402c
finding_ids:
  - PHAB-P1-001
---

# 修正 Promotion 證據路徑越界

## 唯一 finding

`PHAB-P1-001`：`_terminalized_dangling_active_identity()` 只拒絕 receipt 檔案本身為 symlink，未在讀取前拒絕 `dangling-active-terminalizations/` 或其他祖先為 symlink。受控 queue root 內的父目錄可因此把讀取導向 queue root 外。

## 唯一修復切片

- 允許修改：
  - `scripts/pantheon_content_runtime_promotion.py`
  - `tests/test_pantheon_content_runtime_promotion.py`
- 其他檔案只能唯讀；不得更改 implementation card 已建立的歷史／operational authority 分類。
- 在任何 receipt bytes 被讀取前，驗證 receipt 的完整路徑鏈位於 canonical queue root 內，且 receipt 與 queue root 之間的任何既有 ancestor 都不是 symlink。
- 父目錄 symlink、receipt symlink、path escape 或不可判定的路徑狀態都必須 fail closed。
- 不得以 production run ID、日期、13/6/19 或環境特例修補。

## Regression

- `PHAB-REG-P1-001`：把 `dangling-active-terminalizations/` 父目錄換成指向 queue root 外的 symlink；promotion plan 必須在讀取外部 receipt 前拒絕。
- 保留既有 receipt-file symlink、ledger/status conflict、active missing schema、unpublished candidate missing schema 與歷史正向案例。

## 驗證與交付

- 執行 `tests/test_pantheon_content_runtime_promotion.py` 全檔。
- 執行 `tests/test_pantheon_runtime_activation.py`。
- 執行 Python syntax check 與 `git diff --check`。
- 交付 candidate SHA、changed files、regression 結果、production mutation count（必須 `0`）。
- 只能回報 `DELIVERED_REPAIR_CANDIDATE`，不得宣稱 Review GO、整合或 production 可用。

## 禁止範圍

- 不清理、刪除、改寫或封存任何歷史資料、registry、run directory、ledger 或公開文章。
- 不啟動七個服務；不執行 apply、push、deploy、publish、restart 或任何 production mutation。
- 不建立第二個 Repair、Reviewer 或其他 task；卡住回主線。

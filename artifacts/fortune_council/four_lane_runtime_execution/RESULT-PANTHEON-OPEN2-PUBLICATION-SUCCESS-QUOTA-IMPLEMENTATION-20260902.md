---
id: RESULT-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902
card_id: CARD-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902
status: DELIVERED_FOR_REVIEW
production_mutation: 0
---

# OPEN-2 publication success quota 實作結果

## 交付

- 僅延伸既有 `ledger.json`，以單一 create／rewrite／translation 通用
  prepared/reconcile FSM 處理 remote 收斂、phase ledger terminal entry 與 quota
  success status 的同次 atomic write。
- quota 固定為 Asia/Taipei 的 `new=1`、`rewrite=1`、`translation=1`、`total=3`；
  同 run replay 保留首次 admission date，未發佈可證明時才 release reservation。
- dry-run 保留完整 ready 清單；non-dry 在 journal selection、reservation 與任何 mutation
  前 deterministic 僅放行各 phase 的第一筆 ready run。
- scheduler 無 `--exact-run-id` 時會先 resume `PUSH_PREPARED`；installer 固定投影
  `PANTHEON_PUBLICATION_SUCCESS_QUOTA`，Publisher 的每次 non-dry mutation 都會 strict read。
- translation-only prepared helper／reconcile FSM 已移除；保留並改接 crash、config、concurrency
  測試到通用 FSM。
- 第一個 git mutation 前會原子寫入 `COMMIT_INTENT`，保存 phase、run、base、proposed tag
  與可重建的 ledger/evidence identity；commit/tag 已生成但尚未轉換時，scheduler 會以 local
  annotated tag、peeled commit 與 parent base 驗證後原子升級為 `PUSH_PREPARED`，否則 fail-closed。
- translation 的 sealed/staged resume 會重驗 queue state、candidate/review/formal hashes，以及
  replacement manifest／supersession lineage；未發佈 terminal entry 與 reservation release 同次
  ledger atomic write。

## 驗證

- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q`：182 passed（1 個既有 SyntaxWarning）。
- installer config focused：1 passed。
- `python3 -m py_compile scripts/agy_content_publisher.py tests/test_agy_content_publisher.py`：通過。
- `bash -n scripts/install_agy_content_publisher_launchd.sh`：通過。
- `git diff --check`：通過。
- 對 base `e18c4df46d`，Publisher 為 545 additions／295 deletions，淨增 250 LOC（≤260）。

未執行 push、deploy、launchctl、provider 或 production mutation。

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

## 驗證

- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q`：179 passed。
- installer config focused：1 passed。
- `python3 -m py_compile scripts/agy_content_publisher.py tests/test_agy_content_publisher.py`：通過。
- `bash -n scripts/install_agy_content_publisher_launchd.sh`：通過。
- `git diff --check`：通過。
- 對 base `e18c4df46d`，Publisher 為 405 additions／291 deletions，淨增 114 LOC（≤260）。

未執行 commit、push、deploy、launchctl、provider 或 production mutation。

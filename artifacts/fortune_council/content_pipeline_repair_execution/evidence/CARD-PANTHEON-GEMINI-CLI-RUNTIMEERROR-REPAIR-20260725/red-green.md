# RED → GREEN

## RED

Command：

```text
.venv/bin/pytest -q \
  tests/test_agy_seo_copy_pipeline.py::test_cli_transport_exposes_only_closed_failure_code \
  tests/test_agy_gemini_outbox.py::test_runner_failure_receipt_persists_only_closed_error_code \
  tests/test_agy_gemini_outbox.py::test_outbox_failure_preserves_closed_error_code \
  tests/test_agy_gemini_coordinator.py::test_cycle_preserves_closed_code_and_failed_run_does_not_block_next
```

初次結果：`7 failed`。

- CLI nonzero、timeout、not-found、envelope error 均無 closed code。
- Timeout 直接以 `TimeoutExpired` 逸出。
- Runner receipt、outbox exception 與 coordinator state 均未保留 code。

## GREEN

相同 synthetic seams 修復後結果：`7 passed`。

補強為 public runner 實際經 `GeminiClient._cli_transport` 的四類 failure 後，targeted regression 結果：`9 passed`。

新增 operation receipt regression，驗證：

- 保存 `GeminiCliFailure` 與 closed `error_code`。
- 不保存 exception message、raw stdout/stderr、credential marker 或 private path。

沒有執行真實 Gemini 生成、retry、queue 重送或發布。

# 驗證證據

## RED

`test_run_prerender_times_out_with_observable_fail_closed_diagnostic` 在修復前實跑失敗：mock 子程序收到 `timeout=None`，而契約要求固定 `300` 秒。這是目標子程序無界等待缺陷；非 import、fixture 或環境錯誤。

## GREEN 與回歸

執行：

```text
uv run --frozen python -m pytest tests/test_agy_content_publisher.py -q
```

結果：`133 passed, 1 warning in 11.07s`。

警告為既有 `SyntaxWarning: invalid escape sequence '\/'`，位於測試中，與本修復無關。

另已執行：

```text
git diff --check
```

結果：通過。

變更檔案只包含卡片 allowlist：

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- `.work/CARD-PANTHEON-PUBLISHER-PRERENDER-BOUNDED-REPAIR-20260817/**`

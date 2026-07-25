# RED → GREEN

## RED

Command:

```text
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_ignores_non_rewrite_active_runs_for_capacity -q
```

Fixture:

- 2 個非 rewrite active runs：`create`、`translate_existing`
- 1 個 `rewrite_existing_body` active run
- `max_active_runs=2`
- 仍有 1 篇未登記、可建立的舊文 rewrite

Result:

```text
FAILED tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_ignores_non_rewrite_active_runs_for_capacity
AssertionError: assert 'active_limit' == 'seeded'
1 failed in 0.09s
```

Interpretation：舊實作使用全域 active 數量，非 rewrite backlog 錯誤占用 rewrite seeder 容量。

## GREEN

Minimal change:

```text
active_count = _active_count_by_mode(queue_root, "rewrite_existing_body")
```

同一 command 重跑結果：

```text
1 passed in 0.02s
```

結果證明 rewrite active 為 1、上限為 2 時仍可建立 1 個 rewrite run；非 rewrite active runs 不占用其 active limit 或 capacity。

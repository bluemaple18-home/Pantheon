# Reproduction

Red-capable command:

```bash
uv run pytest \
  tests/test_agy_content_publisher.py::test_sync_web_test_release_fixture_does_not_require_public_paths_to_be_adjacent \
  -q
```

Observed before the implementation change:

- Result: `1 failed`.
- Failure: `ValueError: substring not found`.
- Seam: `_sync_web_test_release_fixture`.
- Cause: the function searched for the combined sentinel
  `"]\n\nPUBLIC_ARTICLE_PATHS"` instead of the closing bracket belonging to
  `DAILY_PUBLIC_ARTICLE_PATHS`.

The reproduction fixture preserves an unrelated emergency list and date constant between the
DAILY and PUBLIC declarations.

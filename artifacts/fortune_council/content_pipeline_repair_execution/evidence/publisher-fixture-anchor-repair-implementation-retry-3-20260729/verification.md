# Verification

Green command on candidate base:

```bash
uv run pytest tests/test_agy_content_publisher.py -q
```

Result:

- `58 passed in 4.35s`.
- New path appears exactly once and inside `DAILY_PUBLIC_ARTICLE_PATHS`.
- Cache token is updated.
- The intervening emergency list/date block is unchanged.
- `PUBLIC_ARTICLE_PATHS` is unchanged.

Final static checks:

```bash
git diff --check
rg -n '\[DBG-' scripts/agy_content_publisher.py tests/test_agy_content_publisher.py
git status --short
```

Result:

- `git diff --check`: passed.
- No `[DBG-...]` marker remained in the changed source or test.
- Candidate diff contained only the publisher function, its regression test and this task's
  evidence.
- Worktree was clean after the candidate commit.

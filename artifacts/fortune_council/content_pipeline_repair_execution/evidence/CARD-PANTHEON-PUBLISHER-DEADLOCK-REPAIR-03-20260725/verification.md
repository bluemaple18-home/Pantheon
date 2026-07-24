# Repair-3 Verification

Base：`473556cc00e6a620491897ade606c72b90caac47`

## Root-cause loop

- 原 Reviewer 反例：共用 actor worktree 的 helper attribution window 可吞入
  concurrent bytes，結果為 `preserved=False`、repo clean、conflicts empty。
- Repair-3 seam：正式 CLI 只把隔離 transaction root 傳給 publisher；actor
  concurrent bytes 保留，transaction root 清除。

## Results

| Check | Result |
| --- | --- |
| Publisher focused | `38 passed` |
| Publisher + SEO + multilingual + web | `175 passed, 2 warnings` before runtime-parity guard；新增 guard test 後 focused `38 passed` |
| Full pytest | `407 passed, 2 warnings` |
| `py_compile`（cache redirected to `/tmp`） | PASS |
| `git diff --check` | PASS |
| `[DBG-` scan | clean |
| `node_modules` isolation symlink | repo `.gitignore` confirms ignored |
| V4 default promotion | no related changed file；explicit env gate remains |

Warnings are existing Starlette/httpx deprecation and sandboxed pytest-cache write warnings.

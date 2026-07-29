---
id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-1-PREFLIGHT
status: PASS
type: evidence
---

# Preflight

## Git 與 worktree

| 檢查 | Exit code | 結果 |
|---|---:|---|
| `pwd`、`git rev-parse --show-toplevel` | 0 | 目前目錄與 repo root 相同，且位於 Codex 隔離 worktree。 |
| `git rev-parse --is-inside-work-tree` | 0 | `true`。 |
| `git worktree list --porcelain` | 0 | 目前 worktree 為獨立 detached worktree。 |
| `git status --short` | 0 | 開工時無輸出，worktree clean。 |
| `git rev-parse HEAD` | 0 | `751b4db759baf3d1990795f3ea27c5e4084a6100`。 |
| `git cat-file -e '751b4db759baf3d1990795f3ea27c5e4084a6100^{commit}'` | 0 | parent candidate 存在。 |
| `git cat-file -e 'daf2642697f816f52bb68bd4143da523639c44fd^{commit}'` | 0 | reviewer evidence commit 存在。 |
| index lock 檢查 | 0 | `INDEX_LOCK_ABSENT`。 |

## Reviewer evidence

以 `git show daf2642697f816f52bb68bd4143da523639c44fd:<repo-relative-path>`
完整讀取且未 cherry-pick：

- `findings.json`
- `review.md`
- `verification.md`
- `result.md`

Review verdict 為 `REVIEW_NO_GO`；P1 是 `standalone_answer` 錯誤
fallback 至 `bodySections`，P2 是本卡不得修改的 stale tracking ref residual。

## CodeGraph

| 操作 | Exit code | 結果 |
|---|---:|---|
| CodeGraph status（目前 repo） | tool error | 此 worktree 未初始化。 |

依卡片邊界未執行 `codegraph init`，避免新增 allowlist 外索引。狀態記為
`CONTEXT_DEGRADED`，後續只讀鎖定 Reviewer evidence、
`scripts/agy_seo_copy_pipeline.py` 與 `tests/test_agy_seo_copy_pipeline.py`。

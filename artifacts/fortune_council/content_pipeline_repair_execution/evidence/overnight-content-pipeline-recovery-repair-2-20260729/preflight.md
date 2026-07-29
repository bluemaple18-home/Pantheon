---
id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-2-PREFLIGHT
status: PASS
type: evidence
---

# Preflight

## Git 與 worktree

| 檢查 | Exit code | 摘要 |
|---|---:|---|
| `pwd`、`git rev-parse --show-toplevel` | 0 | 目前目錄與 repo root 相同，位於獨立 Codex worktree。 |
| `git rev-parse --is-inside-work-tree` | 0 | `true`。 |
| `git worktree list --porcelain` | 0 | 目前為獨立 detached worktree。 |
| `git status --short` | 0 | 開工時無輸出，worktree clean。 |
| `git rev-parse HEAD` | 0 | `03acf19208383de1a992471e9d1cebc9ef1b80cb`。 |
| `git cat-file -e '03acf19208383de1a992471e9d1cebc9ef1b80cb^{commit}'` | 0 | Repair-1 parent 存在。 |
| `git cat-file -e 'ce05de3dcc4cf625fbd45e12b5cc7d92658dd923^{commit}'` | 0 | re-review evidence commit 存在。 |
| index lock 檢查 | 0 | `INDEX_LOCK_ABSENT`。 |

## Re-review evidence

以 `git show ce05de3dcc4cf625fbd45e12b5cc7d92658dd923:<repo-relative-path>`
完整讀取且未 cherry-pick：

- `re-review-findings.json`
- `re-review.md`
- `re-review-verification.md`
- `re-review-result.md`

Re-review verdict 為 `REVIEW_NO_GO`。阻斷是正式 create initial hydration
在 bounded repair 前拒絕 `standalone_answer`；第二項 finding 是
`false_social_origin` 固定正文 mapping 與 detector 掃描欄位不一致。

## CodeGraph

| 操作 | 結果 |
|---|---|
| CodeGraph status（目前 repo） | tool error：worktree 未初始化。 |

依 allowlist 未執行 `codegraph init`，避免新增交付範圍外索引。狀態記為
`CONTEXT_DEGRADED`，限域檢查 `hydrate_candidate()`、
`validate_candidate()`、`run_writer_reviewer()`、`quality_findings()`、
`_create_repair_fields()` 與相鄰 tests。

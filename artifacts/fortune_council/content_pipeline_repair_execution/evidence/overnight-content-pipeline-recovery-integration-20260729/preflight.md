# Integration v2.1 preflight

## Identity

- Card：
  `CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-INTEGRATION-20260729`
- Chain：`PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729`
- Source kind：`reviewed_candidate_commit`
- Verified remote main：
  `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`
- Reviewed candidate：
  `39a3a9f23720e158bd2cf9e630901f9debbceb15`
- Review evidence：
  `f0254a0ff701e1a11ecb8235b9198b4c4e11398b`
- Excluded local fork：
  `f432f078b2c76c7d474a2d09e0d9a68f33074573`

## v2.1 re-arbitration receipt

原 target `f432f078...` 是 local canonical-host fork；以實際共同祖先進行
`git merge-tree` 會與 505 個 mainline-only web artifacts 發生衝突。主線已把
它分類為獨立 pending fork，排除於本 pipeline recovery Integration。

本卡改以 fresh remote receipt 鎖定 `baa29d87...`；reviewed candidate 是其
三個連續後代 commit。Delivery branch 已由主線安全改指向 candidate，local
main 的 `f432f078...` ref 未遺失。

## Read-only checks

| 檢查／命令 | Exit code | 摘要 |
|---|---:|---|
| `pwd -P` / `git rev-parse --show-toplevel` | 0 | cwd 等於本 Integration 隔離 worktree；不等於主工作區或 previous worktree。 |
| `git rev-parse HEAD`（切換前） | 0 | detached HEAD 精確為 `f432f078...`。 |
| full status / tracked diff / index diff | 0 | clean。 |
| worktree index lock | 0 | absent。 |
| delivery branch ref | 0 | `codex/overnight-content-pipeline-recovery-integration-20260729` 精確指向 `39a3a9f...`，未被其他 worktree checkout。 |
| `git rev-parse refs/remotes/origin/main` | 0 | local `origin/main` 為 `baa29d87...`。 |
| `git ls-remote origin refs/heads/main` | 0 | fresh remote main 為 `baa29d87...`。 |
| candidate parents | 0 | `baa29d87... -> 751b4db7... -> 03acf192... -> 39a3a9f2...`，距離 3 commits。 |
| `git merge-base --is-ancestor baa29d87... 39a3a9f...` | 0 | verified remote main 是 candidate ancestor。 |
| review evidence object / result | 0 | `f0254a0...` 存在；`REVIEW_GO`、0 findings、P1/P2 resolved、Spec/Standards PASS。 |
| existing ignored `.venv` | 0 | symlink 已存在且由 Git ignore；未安裝依賴、未執行 uv、未改 lockfile。 |
| `.venv/bin/pytest --version` | 0 | `pytest 9.0.3`。 |
| canonical capability `--check` | 0 | `worktree_registered=true`、`provisioning=ready`、`python_tests=ready`、`node_tests=needs_prepare`、`codegraph=needs_prepare`、`code_context=not_ready`。 |

## Context boundary

CodeGraph status query回報此 worktree 未初始化。v2.1 Integration 不做 source
decision、code merge或程式修改，因此記錄 `CONTEXT_DEGRADED`，限域使用固定
SHA、Git ancestry、27-path blob equivalence、diff checks與實際 tests。未安裝
Node、未初始化下載型工具、未修改 lockfile。

## Branch binding

唯讀 preflight 全部通過後執行：

`git switch codex/overnight-content-pipeline-recovery-integration-20260729`

重驗結果：

| 檢查 | Exit code | 摘要 |
|---|---:|---|
| HEAD | 0 | `39a3a9f23720e158bd2cf9e630901f9debbceb15`。 |
| branch | 0 | `codex/overnight-content-pipeline-recovery-integration-20260729`。 |
| full status / index | 0 | clean。 |
| index lock | 0 | absent。 |
| `.venv/bin/pytest` executable | 0 | pytest 9.0.3 可執行。 |

## Preflight decision

`PROVISIONING_GO / CONTEXT_DEGRADED`。准許只新增 current Integration card 與
current Integration evidence；不准許任何 code merge或 candidate blob 修改。

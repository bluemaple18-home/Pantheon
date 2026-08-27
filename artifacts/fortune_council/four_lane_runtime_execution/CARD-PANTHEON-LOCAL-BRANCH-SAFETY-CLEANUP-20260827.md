---
id: CARD-PANTHEON-LOCAL-BRANCH-SAFETY-CLEANUP-20260827
chain_id: PANTHEON-LOCAL-BRANCH-SAFETY-CLEANUP-20260827
role: implementation
cycle: 1
model: gpt-5.6-luna
reasoning: medium
status: ready
thickness: minimal
risk: low
model_reason: bounded local Git branch inventory and deterministic safety classification
---

# 本機分支安全盤點與清理

## 目標

盤點目前未直接 merged-to-main 的本機分支，使用 `merge-base`、`patch-id`、`cherry`、`contains`、`reflog`（可得時）以及 worktree/ref evidence 進行分類，產出可重現的保留或刪除判定。

## 允許範圍

- 唯讀檢查本機 refs、commit graph、worktree 與 Git 狀態。
- 僅在證據完整符合下列條件時刪除本機分支：已證明 `main` 包含等價內容、未被任何 worktree 使用、無 unique commit、無 dirty/unsaved work，且 `git branch -d <branch>` 成功。
- 允許唯一輸出檔：`artifacts/fortune_council/four_lane_runtime_execution/evidence/local_branch_safety_cleanup_20260827/branch_cleanup_result.md`。
- 交付狀態只能使用 `DELIVERED_CANDIDATE`。

## 禁止範圍

- 禁止 `git branch -D`。
- 禁止 remote delete、`push`、`fetch`、`prune`。
- 禁止移除 worktree 或 thread。
- 禁止碰未追蹤檔案。
- 禁止修改 code、config、workflow 或既有 artifacts。
- 不得刪除任何無法由證據排除風險的分支。

## 驗收與證據

執行並記錄 `git branch --merged main`、`git worktree list --porcelain`、`git log`、`git cherry` 等唯讀證據；保存刪除前後 refs 清單、`git status` 與 `git diff --check` 結果。結果檔須列出候選 commit、deleted/retained 分支清單及每項理由，並區分證明內容與 blocker。每個刪除動作須以 `git branch -d` 的成功輸出為準。

## 停損

任何歧義一律保留並列為 blocker；同一 blocker 第三次失敗即停止，不進行第四次相同嘗試，也不得以推測取代證據。

## 交付

提供候選 commit、deleted/retained 分支清單與理由；狀態僅可標示 `DELIVERED_CANDIDATE`，由主線負責最終驗收。

# Pantheon local refs cleanup snapshot｜2026-07-21

## Root question

清除累積的本地 worktrees 與 branches，保留可追溯性；只整合已通過且不含未核准 production／content 變更的成果。

## Mainline acceptance

- 清理前 main：`5724abdeed022df7bfdfdf6437b6361341b09d18`。
- 已整合三個純 Review evidence commits：
  - `6a8f7af`：Repair 1 delta review。
  - `4de24f1`：完整 implementation range review。
  - `7d81ee2`：Repair 2 final re-review。
- 未整合任何 BLOCKED Reviewer production candidate、未核准文章候選、正式正文或發布檔。

## Archive anchor

- Annotated tag：`archive/pre-cleanup-20260721`。
- Archive commit：`ed83f9e0fa8e0c90b6978a973221605f3e7956f3`。
- Tree 與建立當下 main 相同；額外 parents 只用來保存 34 個非 main local tips，不代表接受、整合或可發布。
- 可用 `git show --no-patch archive/pre-cleanup-20260721` 與 `git log --graph archive/pre-cleanup-20260721` 回查。

## 保留但不整合的主要成果

- Gemini Reviewer V1 BLOCKED candidate：`5e9b1c898d943ae59f24f9f87206c3f60b0a0ceb`。
- Gemini Reviewer V1 final NO_GO evidence：`d7a14e66028d032354d7686f3dcd26f359ecf4bd`。
- 舊 Gemini JSON repair BLOCKED candidate：`f74d3654bfe0377c34ade128b131d42cf6bb8e41`。
- Gemini rewrite Batch 1／2、Batch 3–10 與未核准 article expansion／content rewrite candidates。
- Motion demo 與舊 pre-push backup tips。

## Cleanup boundary

- 移除 clean secondary worktrees；main worktree 保留。
- 刪除已由 archive anchor 保存的本地 task／codex／agent branches與過期 backup branches。
- `main` 保留；remote branches 不刪除、不 push。
- 正式 Codex threads 保留，不 archive、不刪除。
- 不 deploy、不 publish、不恢復內容線。

## Current blocker and next fork

- 舊 Reviewer repair chain 維持 `BLOCKED`，不得開 Repair 3。
- 下一個 candidate fork 是新的 Reviewer Transport V2 design chain；必須從 main 建立，不沿用任何已清理 worktree。

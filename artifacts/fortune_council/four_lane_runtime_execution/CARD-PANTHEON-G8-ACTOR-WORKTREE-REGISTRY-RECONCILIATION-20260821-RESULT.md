---
id: CARD-PANTHEON-G8-ACTOR-WORKTREE-REGISTRY-RECONCILIATION-20260821-RESULT
status: reconciled
source_commit: ab40e0ee6c23589cf89a14e110cca450b9f613d5
production_mutation: 0
---

# G8 actor worktree registry reconciliation result

## 結論

RECONCILED / READY TO RESUME PROMOTION

## 操作邊界

- 未修改 actor 目錄、actor `.git`、source、測試、config、runtime transaction 或 production。
- 唯一 stale admin entry 已從 Pantheon common Git dir 的 `worktrees/actor` 隔離至 common Git dir 根目錄的 `actor-worktree-admin.quarantine-20260821-g8`。
- quarantine 保留原始 `gitdir`（actor `.git`）與 stale `HEAD`（`e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0`），未刪除資料，可回退。

## 驗證證據

- 修前 RED：actor HEAD `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`，registry actor HEAD `e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0`，不一致，預期非零失敗。
- 修後 GREEN：actor HEAD 保持 `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`，`git worktree list --porcelain` 不再列 actor，檢查 exit 0。
- actor 為 standalone repo（`.git` 為目錄），`git status --porcelain` 為空，origin 維持 `git@github.com:bluemaple18-home/Pantheon.git`。
- 修前與修後的非 actor worktree path/HEAD 集合逐筆相同，共 14 筆。
- `lsof` 對 stale admin entry 與 actor `.git` 未發現開啟檔案（exit 1）。
- candidate workspace 的 `git diff --check` 通過。

## 注意事項

第一次 quarantine 落點位於 `.git/worktrees/` 下，Git 仍會枚舉該目錄，故 GREEN 未成立；同一 entry 隨即移至 common Git dir 根目錄的最終 quarantine 落點後才通過 GREEN。

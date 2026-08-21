---
id: CARD-PANTHEON-G8-ACTOR-WORKTREE-REGISTRY-RECONCILIATION-20260821
status: ready
chain_id: PANTHEON-G8-ACTOR-GIT-AUTHORITY
role: implementation
cycle: 1
thickness: standard
risk: local-git-metadata
model: gpt-5.6-terra
reasoning: medium
model_reason: 節省模式；問題已縮成單一 stale worktree admin record，修復與回退邊界固定。
---

# 對齊 G8 runtime actor 的 Git authority

## 目標

消除同一路徑的雙重 Git identity：runtime actor 自己讀到 `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`，Pantheon common Git worktree registry 卻記錄 `e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0`。

## 已知證據

- actor path：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor`（local-only）。
- actor `.git` 是獨立目錄；`git -C <actor> rev-parse HEAD` 為 `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`。
- Pantheon stale admin entry：common Git dir 下 `worktrees/actor`；其 `gitdir` 指向 actor `.git`，其 `HEAD` 為 `e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0`。
- Cycle 22 已停止，production mutation 全為 0；Capacity 已 PASS。

## 可做

1. 先建立可重跑 RED：同一指令同時讀 actor HEAD 與 `git worktree list --porcelain`，不一致即非零。
2. 唯讀確認 actor 是 standalone repo、clean、remote 正確；精確解析唯一 stale admin entry，確認沒有其他 registered worktree 或 active process 依賴它。
3. 僅在證據完整時，把唯一 stale admin entry 原子移到 common Git dir 內可回退的 quarantine 名稱；禁止刪除。不得移動或改寫 actor 目錄。
4. 重跑 RED 指令至 GREEN；再驗 actor HEAD/clean/remote 不變、Pantheon worktree list 不再把 actor 列為 linked worktree、其他 worktrees 集合不變。
5. 寫入唯一 result 與必要 evidence，提交 candidate commit。

## 可改範圍

- Pantheon common Git dir：只允許移動精確解析出的 `worktrees/actor` 到唯一 quarantine 路徑；不得修改其他 Git metadata。
- `.work/CARD-PANTHEON-G8-ACTOR-WORKTREE-REGISTRY-RECONCILIATION-20260821/**`。
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-ACTOR-WORKTREE-REGISTRY-RECONCILIATION-20260821-RESULT.md`。

## 禁止

- 禁止 `git worktree remove`、`rm`、prune、reset、checkout、clean、rebase、merge、push。
- 禁止修改 actor files、actor `.git`、source、tests、config、runtime transaction、private stage、LaunchAgents。
- 禁止 promotion、installer、activation、canary、lane run、Publisher transaction/tag/publish。
- 任一 identity 不唯一、actor dirty、process 使用中、quarantine 目的地已存在或 mutation 需擴大範圍：立即 `BLOCKED`，不得猜測或重試。

## 驗收

- RED 指令修前失敗、修後 PASS。
- actor 仍為 `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`、clean、remote 不變。
- Pantheon worktree registry 不再列 actor；其他 worktree path/HEAD 前後完全一致。
- quarantine 可回退、未刪資料；production mutation 全為 0。
- `git diff --check` PASS；candidate commit 只含 RESULT/evidence，不得把 common Git metadata 納入 commit。

## 終局

只能回報：

- `RECONCILED / READY TO RESUME PROMOTION`
- `BLOCKED / NO PRODUCTION MUTATION`

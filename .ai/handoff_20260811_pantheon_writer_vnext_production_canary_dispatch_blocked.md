# Pantheon Writer vNext：Production Canary 派工遭平台邊界阻擋

## 新任務第一拍

完整讀取本交接卡與 `<repo-root>/AGENTS.md`。第一拍只做唯讀核對：目前 branch、`main` SHA、dirty state、canary 卡片、blocked reservation 與 Codex project inventory。完成核對前不得 push、deploy、production mutation、canary、正式產文、重送 create 或建立 replacement。

## 可直接貼到新任務的啟動文字

```text
請套用 ~/ai-core/compiled_lite.md。

你現在接手 Pantheon Writer vNext Production Canary 主線。先完整讀取：
.ai/handoff_20260811_pantheon_writer_vnext_production_canary_dispatch_blocked.md
以及 <repo-root>/AGENTS.md。

若目前 checkout 看不到交接卡，從本機 Git object 讀取：
git show <handoff-source-sha>:.ai/handoff_20260811_pantheon_writer_vnext_production_canary_dispatch_blocked.md

第一拍只做唯讀核對：確認 main、dirty checkout 邊界、canary 卡 source、既有 BLOCKED reservation、list_projects/create_thread project authority 是否一致。不得重送既有 dispatch、不得建 replacement、不得 push、deploy、啟動 production、canary 或正式產文。核對後只提出同 reservation 的安全 reconciliation 路徑；若平台 project authority 仍不一致，維持 BLOCKED，平台缺口另交 ai-core-runtime，不混入 Pantheon 主線。
```

## Goal

從已通過 Checkpoint B 的 Writer vNext 主線，建立唯一正式可見 canary-executor task；再依 bounded card 執行最多一篇、一次 atomic push、無常駐服務的 production canary。

## Root Question

Codex project authority 恢復一致後，是否能把既有 canary card 安全綁定到唯一正式 thread，並在不啟用四 lane 常駐服務的前提下完成單次 `create → run → select → publish → transaction → tag → push`？

## Current Blocker

正式 `list_projects` 回傳 Pantheon remote/slingshot `projectId`，但相同 `projectId` 傳給 `create_thread` 時立即回：

```text
Unknown projectId: <Pantheon remote projectId>. Call list_projects to find available projects.
```

拒絕發生在 thread/worktree 建立前。這不是 Pantheon card、model、Git 或容量 blocker；是 Codex project inventory 與 create endpoint 的 project authority/namespace 不一致。

## Candidate Fork

- `recommended`：新主任務唯讀重查 project inventory；若 authority 一致，先對既有 blocked reservation 做官方 reconciliation／resume，不重送舊 create request、不換 identity。
- `platform-gap`：若仍不一致，只產出 ai-core-runtime 缺口卡；Pantheon 主線維持 BLOCKED。
- `forbidden`：改用另一個 projectId 猜測重試、建立同 card replacement、繞過 reservation、直接在髒主 checkout 執行 canary。

## Completed Actions

1. RA004–RA007、Repair-1 re-review 與 Checkpoint B reassessment 已整合。
2. Checkpoint B verdict：`CHECKPOINT_B_READY_FOR_CANARY_AUTHORIZATION`。
3. 使用者已授權建立並派送 bounded production canary 卡。
4. Canary card 已建立並提交：
   - `artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-PRODUCTION-CANARY-001.md`
   - source commit：`ed3913f7aa87c2a965a29f2d0a4e78c4b7afaacf`
5. 本機 `main` 已由 `7a8b927fa7f56199b31371e4ab5d6608b18dd7c9` 前進到 `ed3913f7aa87c2a965a29f2d0a4e78c4b7afaacf`。
6. Dispatch precreate resource gate 通過：active `2 → 3`（上限 4）、worktree `9 → 10`（上限 20）、projected available `26,854,801,408` bytes，高於 reserve `24,510,719,591` bytes。
7. Reservation 已原子建立後因 platform boundary 標記 `BLOCKED`；未重試、未建立 replacement。
8. 未 push、未 deploy、未啟動服務、未執行 production/canary/正式產文。

## Active State

- Canary card source：`ed3913f7aa87c2a965a29f2d0a4e78c4b7afaacf`。
- Blocked dispatch key：`v1:ffeb06e993839e4ddb420413bedfaefeb00fd2b3fd6ca76060d9dd97038101ce`。
- Reservation owner：`pantheon-writer-vnext-canary-mainline-20260811`。
- Reservation state：`BLOCKED`；formal thread ID 空；沒有 clientThreadId。
- Model contract：`gpt-5.6-sol / high`。
- 使用者既有 checkout 仍是 dirty `pantheon-visual-checkpoint-20260730`；不得修改、stash、reset 或搬運其 working tree。
- 正式服務仍 `0/4`；無新增 server。

## In Progress / Remaining Work

1. 新主任務唯讀確認 handoff source、main ref、card blob、reservation durable state。
2. 重新取得同一 host 的 `list_projects` 與 project capability；確認 Pantheon project identity 唯一且 `supportsWorktrees=true`。
3. 只查官方 reconciliation/resume 是否能把既有 BLOCKED reservation 恢復；不得先呼叫 create。
4. 若無安全原地恢復能力，維持 BLOCKED；另開 ai-core-runtime 平台缺口卡，等待外部修復。
5. 平台修復後，仍須 bootstrap-only → formal thread/worktree/head/clean 核對 → activation token，才能執行 canary 卡。

## Waiting Conditions

- Codex `list_projects` 與 `create_thread` 必須對同一 Pantheon `projectId` 有一致 authority。
- 既有 reservation 必須能原地 reconciliation/resume；若只能猜測重送或 replacement，不得前進。
- Canary 執行前仍須 fresh capacity、readiness、remote/main drift 與 exact payload preflight。

## Constraints & Preferences

- 沿用 caveman 節省 token 模式。
- 文件與回報用繁中；程式碼保留原語言。
- 正式新任務必須側邊欄可見、獨立 clean worktree。
- 同 chain Reviewer／Repair 不新增；既有唯一 Reviewer／Repair 保留。
- Platform projectId 缺口屬 ai-core-runtime；禁止偷混入 Pantheon source/card 修復。
- Canary 卡只授權一個 run、最多一篇、一次正式模型鏈、一次 atomic push；不授權 launchctl、常駐排程、四 lane 全開或第二次嘗試。

## Evidence

- Checkpoint B：`artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_checkpoint_b_reassessment/`
- Canary card：`artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-PRODUCTION-CANARY-001.md`
- Dispatch durable state：`<codex-home>/visible-thread-dispatch.sqlite`；只讀查詢，不手改 DB。

## Blocked & Errors

- `create_thread`：`Unknown projectId`。
- `formal_thread_id`：空。
- `clientThreadId`：不存在。
- 禁止把「卡片已建立」誤報為「正式任務已建立」。

## Key Decisions & Resolved Questions

- 不在本對話改用另一 projectId 重試：dispatch v5 首次 platform boundary 必須 fail closed。
- 不把控制面 bug 修進 Pantheon。
- 新對話作主線接手，不直接冒充 canary-executor；先恢復正式 dispatch authority。

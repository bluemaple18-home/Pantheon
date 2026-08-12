# Pantheon Writer vNext：主線已整合，接續 Runtime Activation

## 新任務第一拍

先完整讀取本交接卡與 `<repo-root>/AGENTS.md`，只做唯讀核對並回報：目前 branch、`main` SHA、dirty state、正式服務數量與 production authorization。完成核對前不要部署、啟動服務、產文或另開 Repair。

## 可直接貼到新任務的啟動文字

```text
請套用 ~/ai-core/compiled_lite.md。

你現在接手 Pantheon Writer vNext 主線。先完整讀取：
.ai/handoff_20260811_pantheon_writer_vnext_integrated_runtime_activation.md
以及 <repo-root>/AGENTS.md。

第一拍只做唯讀核對：確認 main、目前 dirty checkout、既有 evidence、正式服務 0/4 與 production NO-GO。核對完成後，依交接卡「下一步」用最新可見 thread 卡片流程規劃 Runtime Activation；慎選模型。未取得我的明確授權前，不得 push、deploy、啟動 production、publication、canary 或正式產文。
```

## Goal

在已整合的 Writer vNext 架構上，完成下一階段 Runtime Activation 與非 production E2E 證明，最後才判斷是否具備正式四語／四 lane 產文資格。

## Root Question

`main` 上的 Writer vNext 是否能從正式入口完成 `create → run → select → publish → transaction → tag → push` 的可追溯、fail-closed 全鏈路，並在容量與 production readiness gate 通過後安全啟用？

## Current Blocker

程式與主線整合已完成，現在的 blocker 是正式 runtime 尚未啟用、正式服務仍 `0/4`，而且尚未取得新的 production／deployment 授權與完整 capability receipt。

這不是 Writer vNext source code blocker，也不是需要 Repair-2／Repair-3 的狀態。

## Candidate Fork

- `recommended`：先做非 production Runtime Activation／E2E evidence；證明 identity、correlation、transaction、fail-closed 與容量安全後，再另行請求 production canary 授權。
- `alternative`：若只需短期限量產文，另開明確限制數量、語系、Publisher authority 與回退條件的臨時卡；不得冒充正式四 lane 服務已啟用。
- `forbidden`：直接把單篇手動成功當成正式服務完成，或在缺 capability receipt 時啟動 production canary。

## Completed Actions

1. Writer vNext architecture、contract、manifest explicit opt-in、integration 與 bounded repair 已完成。
2. Accepted Repair candidate：`6f9aa59804a97a71d96fabf32cd6829e2f84918c`。
3. 前一代 re-review：`1faf26aa18baa02ead68cf49cd8bfc17deb6685c`，`REVIEW_GO`，`WVNI3-REVIEW-001`=`RESOLVED`。
4. Mainline integration candidate：`c758f34362b1503a41c8ff48885ede896ce26335`。
5. Integration candidate 雙親順序：
   - `280884e61872f84f0186f2f1a6a6b51d4c689109`
   - `6f9aa59804a97a71d96fabf32cd6829e2f84918c`
6. Integration Reviewer commit：`1e52a551958931d34fc1faf74fc4e2b29dc7187f`，verdict=`REVIEW_GO`，無阻斷 finding。
7. 本機 `main` 已由 `fe91f3f7fd96d57791b569022fad06f7a3b3c497` 原子更新為 `c758f34362b1503a41c8ff48885ede896ce26335`。
8. 未 push、未 deploy、未啟動服務、未執行 production／publication／canary。

## Verification Evidence

- Integration receipt：`artifacts/fortune_council/content_writer_vnext_execution/integration/writer_vnext_mainline_integration_004/verification-receipt.md`
- Integration lineage：`artifacts/fortune_council/content_writer_vnext_execution/integration/writer_vnext_mainline_integration_004/lineage-receipt.json`
- Integration Reviewer report 位於 review commit `1e52a551...`：`artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_mainline_integration_004_review_001/review-report.md`
- Integration Reviewer findings 位於 review commit `1e52a551...`：`artifacts/fortune_council/content_writer_vnext_execution/review/writer_vnext_mainline_integration_004_review_001/findings.json`
- 獨立 Reviewer：`415 passed, 1 warning`。
- 主線 acceptance：manifest opt-in reproducer PASS、targeted `9 passed`、`git diff --check` PASS、cache／pyc scan `0`。
- Merge-tree：expected tree `626fe9bcfb016d46ccf1c032814f18316382dc63`；與 candidate tree 只差六個允許的 integration evidence 檔；changed paths=`1002`。

## Active State

- `main`：`c758f34362b1503a41c8ff48885ede896ce26335`。
- 使用者目前 checkout：`pantheon-visual-checkpoint-20260730`，HEAD=`e4df0fc4349568cb0a7df2de56a4865885361494`。
- 目前 checkout 原有多個 tracked／untracked 使用者變更；本次主線整合沒有改動、stash、reset 或覆蓋它們。
- 正式服務：`0/4`。
- Production verdict：`NO-GO`。
- 已啟動 server：無新增。

## In Progress / Remaining Work

1. 唯讀核對 `main == c758f343...`、handoff evidence 與 dirty checkout 邊界。
2. 依 `rules/25-production-canary-readiness.md` 做正式入口能力盤點；缺任何 create／run／select／publish／transaction／tag／push 節點就先停在 `BLOCKED`。
3. 寫一張新的 Runtime Activation 實體卡；不得重用舊 4lan Repair-3，也不得把舊 `BLOCKED` 卡改名冒充新架構。
4. 模型路由：固定規格、strict/core-bounded 的 activation／review 用 GPT-5.5 high；只有出現未解架構 fork 才升 Sol。
5. 先完成非 production E2E 與 fail-closed 負向證據；涉及外部 runtime、Publisher、tag、push、deployment 或 production 前重新取得明確授權。
6. 通過 storage capacity gate、capability receipt 與獨立 Reviewer 後，才可提出 production canary GO／NO-GO。

## Waiting Conditions

- 等待使用者在新任務明確選擇：`非 production Runtime Activation` 或 `臨時限量產文`。
- 等待任何外部服務／部署／production write 的明確授權。
- 若正式入口能力不完整，等待先完成新的架構 slice；不得用手動 shell 成功替代正式入口。

## Constraints & Preferences

- 文件、卡片、自然語言用繁中；程式碼維持原語言。
- 卡片先落實體 `.md`，正式派工必須是側邊欄可見 thread；同一 chain Reviewer／Repair 各只保留一個正式 task。
- 新任務 prompt 必須包含完整契約，不能只丟未提交卡片路徑。
- 不得使用 `startingState: working-tree` 搬運目前髒工作區。
- 不得自行 merge、push、deploy、publish、canary、tag、launchctl 或啟停 production 服務。
- 禁止 Repair-3；若新架構出現 P0/P1，依新 chain 的 bounded repair 規則處理。
- 單篇手動救援與正式服務 `0/4` 必須分開陳述。

## Key Decisions & Resolved Questions

- Writer vNext 重構與本機主線整合已完成；不再是「候選待整合」。
- `c758f343...` 是正式本機 `main` 的 integration SHA；`1e52a551...` 是獨立 Review evidence commit，不應合併成產品 source commit。
- Manifest 明示 opt-in 的 P1 已修復並複審關閉。
- 下一問題鏈是 Runtime Activation／production readiness，不是繼續修 Writer vNext contract。

## Blocked & Errors

- 無未解 source／test P0/P1。
- 唯一既有測試 warning：`tests/test_agy_content_publisher.py` 的 invalid escape sequence `\/`；非阻斷。
- Production 尚未授權且 capability receipt 未完成，因此正式產文仍不得開始。

## Cleanup Receipt

清理已完成：

- 已封存八個已完成的 Writer vNext 正式派工任務；目前側邊欄不再列出它們，本交接主對話保留。
- 已移除十四個 Writer vNext 隔離 worktree：六個 source worktree、八個正式任務 worktree。
- 已刪除六條 Writer vNext 暫存 source branches。
- 舊 Integration-001 的 staged 狀態沒有直接丟棄，已封成 detached snapshot commit `1fde0cf8a962f5d1e329259641cc1bf75750ba34`。
- 下列本機 archive refs 保存未進 `main` 但仍需追溯的候選／Review 證據；它們不會顯示成 side branches：
  - `refs/archive/writer-vnext/20260811-architecture-candidate`
  - `refs/archive/writer-vnext/20260811-architecture-review-go`
  - `refs/archive/writer-vnext/20260811-integration-001-staged-snapshot`
  - `refs/archive/writer-vnext/20260811-integration-003-rereview-go`
  - `refs/archive/writer-vnext/20260811-mainline-integration-review-go`
- `main`、目前使用者 checkout／髒分支、其他 Pantheon／JA 工作線與本卡均保留且未改動。

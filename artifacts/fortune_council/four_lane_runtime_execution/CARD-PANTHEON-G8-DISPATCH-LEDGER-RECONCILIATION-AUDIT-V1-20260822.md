---
id: CARD-PANTHEON-G8-DISPATCH-LEDGER-RECONCILIATION-AUDIT-V1-20260822
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: control_plane_reconciliation_audit
cycle: 1
status: ready
type: minimal_readonly_audit
thickness: minimal
risk: medium
model: gpt-5.6-luna
reasoning: medium
model_reason: 已固定單筆 dispatch identity 與完成 lineage，只需唯讀對帳並產出 bounded evidence；不授權控制面 mutation。
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-DISPATCH-LEDGER-RECONCILIATION-AUDIT-V1-20260822-RESULT.md
forbidden_scope:
  - 修改 <codex-home>/visible-thread-dispatch.sqlite 或任何 Codex registry、rollout、thread metadata
  - 修改 <ai-core-root>、source、tests、既有 cards/RESULT 或 main history
  - 建立 replacement、Reviewer、Repair 或下一張卡
  - push、tag、deploy、production inspection/mutation、launchctl
verification:
  - git diff --check
  - final commit 僅新增 evidence_path
  - RESULT 不含本機絕對路徑
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-DISPATCH-LEDGER-RECONCILIATION-AUDIT-V1-20260822-RESULT.md
---

# G8 dispatch ledger reconciliation audit

## 工作名稱 → 正在做什麼 → 現在狀態

G8 dispatch ledger 對帳 → 釐清舊 `BLOCKED` reservation 與已完成 main adoption 的差異，產出可執行且 fail-closed 的處置建議 → READY

## 固定事實

- main 已以 fast-forward 整合 adoption final HEAD：`7561ade2d085198ea1c755cd238516c5e839a2e7`。
- Adoption RESULT verdict：`ADOPTION_READY`。
- formal thread：`01a02569-9f7c-7a10-b25a-fa8c6c11603c`，已交付且 idle。
- dispatch key：`v1:dc5faff4873722052d681f33b44f4054fbb9efdaf10b8bc8c6fdc62f37c975c8`。
- reservation 目前為 `BLOCKED`，但保存完整 activation receipt、formal thread ID 與 token hash；`blocker_code`／`blocker_detail` 為空。
- `BLOCKED` 是 activation 訊息連續三次 RPC 逾時後由主線手動 fail-closed；之後使用者要求繼續，同一 thread 投遞成功並完成工作。

## Audit contract

1. 唯讀重跑 reservation `inspect`，核對 identity、thread、activation receipt、state、blocker 欄位。
2. 唯讀核對 formal thread 的 sidebar 可見性、idle/completed delivery、worktree final HEAD 與 clean state。
3. 唯讀核對 main HEAD 含 adoption final HEAD，且 Adoption RESULT 為 `ADOPTION_READY`。
4. 限域閱讀 `<ai-core-root>/scripts/visible_thread_dispatch_reservation.py` 與 Rule 21，判斷現有正式命令是否存在合法的 post-delivery terminal reconciliation 路徑；禁止直接改 SQLite。
5. 將差異分類為以下之一：
   - `LEDGER_CONSISTENT`
   - `HISTORICAL_BLOCKED_RECEIPT_REQUIRES_NO_MUTATION`
   - `RECONCILIATION_TOOLING_GAP`
   - `AUDIT_BLOCKED`
6. 若沒有正式、可證明安全的 mutation 命令，結論必須 fail closed：保留歷史 `BLOCKED` receipt，不得自行改表；列出最小後續卡 scope 與明確授權需求。
7. 新增唯一 RESULT，記錄查核命令、證據、分類、風險與下一步；文件只使用 `<repo-root>`、`<codex-home>`、`<ai-core-root>` 等跨機 locator。

## Delivery

- 只提交 RESULT-only candidate commit，final worktree clean。
- 回傳分類、full candidate SHA、RESULT 相對路徑、是否需要下一張 tooling card／控制面 mutation 授權。
- 本卡不修 ledger、不封存 thread、不移除 worktree、不碰 production。

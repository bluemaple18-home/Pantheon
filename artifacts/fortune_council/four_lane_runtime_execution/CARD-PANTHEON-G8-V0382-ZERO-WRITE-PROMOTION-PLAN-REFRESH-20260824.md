# PANTHEON G8 V0382 zero-write promotion plan refresh

## 工作名稱

V0382 zero-write promotion plan refresh

## 目的

在 exact target source `5872284828f9dd6f0a75adf407becaeadb50d61a` 上，沿用既有 promotion planner 產生 current actor/manifest authority 收斂的 deterministic zero-write plan 與精確授權 payload；禁止 apply 或 production mutation。

## 啟動契約

- 正式 thread 以本機 branch `codex/g8-v0381-exact-target-source` 啟動，初始 HEAD 必須等於 target，worktree 必須 clean。
- planner 執行前不得在 worktree 寫入；暫存輸出只放 task-owned `/private/tmp`。
- planner 完成後才可封裝本卡 evidence 並建立單一 commit。

## Authority 基線

- published target 與 P0 成功核對：`5872284828f9dd6f0a75adf407becaeadb50d61a`。
- V0381 formal result：`BLOCKED / ACTOR_MANIFEST_AUTHORITY_MISMATCH`。
- current actor/manifest observed：`db9fb4343df212fd3b65546b017aba159620a058`。
- manifest digest：`d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e`。
- production protected tripwire：`PASS / changed=[]`。
- V0381 remote query 已失敗且不得重試；本卡禁止 remote query。未來 apply 必須把 fresh remote equality 當成首個 fail-closed gate。

## 可讀輸入

- target checkout 內既有 promotion plan/build/read-only evidence contracts。
- main `b0e6167417` 的 V0380/V0381 evidence，可用 `git show` 唯讀讀取。
- production actor、manifest、queue、state、transactions、stage、LaunchAgents、barriers，僅限 read-only。

## 可寫輸出

- `CARD-PANTHEON-G8-V0382-ZERO-WRITE-PROMOTION-PLAN-REFRESH-20260824-RESULT.md`
- `g8_v0382_zero_write_promotion_plan_refresh_20260824/`
- task-owned `/private/tmp`。

## 禁止範圍

- 禁止任何 remote query、fetch、pull、push、tag、remote ref 或 credential write。
- 禁止修改 actor、manifest、queue、state、transactions、stage、LaunchAgents、barriers。
- 禁止 promotion apply、postcheck mutation、finalize mutation、rollback、adoption、reset、deploy、canary、launchctl mutation。
- 禁止修改 source、workflow、tests、shared metadata 或既有 artifact。
- 禁止派下一張卡。

## 必交付內容

1. exact-target clean-source receipt 與 fresh current actor/manifest identity。
2. 沿用既有正式 planner 的 machine plan、plan digest、target manifest digest、exact apply argv/argv digest；不得另造第二套 truth。
3. mutation allowlist、before identities/digests、success receipts、postcheck/finalize條件、rollback bundle與 terminal stop conditions。
4. 精確使用者授權 payload；必須把 apply 當下 fresh remote equality、capacity、Rule24/25、actor/manifest/digest no-drift 設為前置 gate。
5. verdict 只能是 `READY_FOR_PRODUCTION_PROMOTION_AUTHORIZATION`、`BLOCKED` 或 `UNKNOWN`。

## 驗證

- 所有 JSON 可解析。
- `git diff --check` 通過。
- production protected before/after `PASS` 且 `changed=[]`；否則 `BLOCKED`。
- 變更只落在本卡 ownership。
- 單一 commit，worktree 收尾乾淨。

## 交付格式

- verdict、plan digest、exact authorization payload、唯一下一拍。
- commit SHA。
- 未 remote access、未 push、未 production write、未 canary 的明確聲明。

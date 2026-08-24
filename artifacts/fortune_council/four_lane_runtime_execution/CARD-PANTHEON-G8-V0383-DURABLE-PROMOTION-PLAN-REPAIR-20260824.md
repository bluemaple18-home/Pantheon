# PANTHEON G8 V0383 durable promotion plan repair

## 工作名稱

V0383 durable promotion plan repair

## 目的

修正 V0382 exact apply payload 的 durability blocker：transaction receipt 與 rollback bundle 不得位於 `/private/tmp`；重新產生 zero-write deterministic promotion plan，禁止 apply 或任何 production mutation。

## Review finding

- V0382 `--transaction-root` 為 `/private/tmp/pantheon-g8-v0382-zero-write-promotion-plan-refresh-20260824/transaction`。
- 正式 promotion contract 會把 `promotion-receipt.json` 與完整 `rollback-bundle/` 寫入 transaction root。
- `/private/tmp` 不能作為 production rollback authority 的 durable locator。
- V0382 capacity receipt argv 亦綁定 ephemeral Codex worktree path，須改用主工作區穩定唯讀路徑。
- 因 exact argv 與 plan digest 將改變，先前使用者授權不得沿用。

## 啟動契約

- 以 `codex/g8-v0381-exact-target-source` 啟動；HEAD 必須等於 `5872284828f9dd6f0a75adf407becaeadb50d61a` 且 clean。
- planner 前不得寫 worktree；暫存 source clone 可用 task-owned `/private/tmp`。
- planner 完成後才封裝本卡 evidence 並建立單一 commit。

## 修正後 immutable locators

- transaction root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-v0383-5872284828-promotion-20260824`
- capacity receipt：`/Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/aggregate_runtime_promotion_plan_replay_raw_capacity_20260815/capacity-receipt-canonical.json`
- target source：`5872284828f9dd6f0a75adf407becaeadb50d61a`
- current actor：`db9fb4343df212fd3b65546b017aba159620a058`
- current manifest digest：`d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e`

## 可讀輸入

- target checkout 的正式 promotion planner 與 contracts。
- main `c55abd25a3` 的 V0382 plan/evidence，可用 `git show` 唯讀讀取。
- production actor、manifest、queue、state、transactions、stage、LaunchAgents、barriers，僅限 read-only。

## 可寫輸出

- `CARD-PANTHEON-G8-V0383-DURABLE-PROMOTION-PLAN-REPAIR-20260824-RESULT.md`
- `g8_v0383_durable_promotion_plan_repair_20260824/`
- task-owned `/private/tmp`。

## 禁止範圍

- 禁止 remote access、fetch、pull、push、tag、ref 或 credential write。
- 禁止建立 transaction root；planner 只能要求其 parent 已存在且 child 尚不存在。
- 禁止修改任何 production surface。
- 禁止 apply、status、postcheck mutation、finalize、rollback、adoption、reset、deploy、canary、launchctl mutation。
- 禁止修改 source、workflow、tests、shared metadata 或既有 artifact。
- 禁止派下一張卡。

## 必交付內容

1. V0382 finding 的 review receipt 與 corrected locator proof。
2. 正式 planner `READY_TO_APPLY` machine plan、plan digest、target manifest digest、exact apply argv/argv digest。
3. exact argv 必須使用上述 durable transaction root 與 stable capacity receipt；禁止其他 ephemeral production-authority locator。
4. mutation allowlist、fresh before identities/digests、success receipts、postcheck/finalize、rollback與 terminal stop conditions。
5. 新的精確使用者授權 payload；apply 前仍須 fresh remote equality、Rule24/25、capacity、no-drift、tripwire gates。
6. verdict 只能是 `READY_FOR_PRODUCTION_PROMOTION_AUTHORIZATION`、`BLOCKED` 或 `UNKNOWN`。

## 驗證

- 所有 JSON 可解析、evidence digests PASS。
- `git diff --check` 通過。
- production protected tripwire `PASS / changed=[]`。
- transaction root child 在 planner 前後皆不存在。
- 變更只落在本卡 ownership。
- 單一 commit，worktree clean。

## 交付格式

- verdict、new plan digest、new apply argv digest、精確授權 payload。
- commit SHA。
- 未 remote access、未 production write、未 canary 的明確聲明。

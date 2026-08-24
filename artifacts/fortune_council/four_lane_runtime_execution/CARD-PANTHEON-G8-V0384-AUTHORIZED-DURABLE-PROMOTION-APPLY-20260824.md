# PANTHEON G8 V0384 authorized durable promotion apply

## 工作名稱

V0384 authorized durable promotion apply

## 使用者授權

使用者已明確授權新版 V0383 exact apply payload：

- target source：`5872284828f9dd6f0a75adf407becaeadb50d61a`
- plan digest：`415eff6d83e48bc16ccb5335b77a170b750a0e8e2a45a9f6dc453fceead29840`
- exact apply argv digest：`db697635302ab6c44803cabb6aa6b9fcf16c7b36368a7d42b291a0ab0b6cc9b2`
- target manifest digest：`389cd799384af4628b9fc371d620b5e87bed52125f27d6612119158af568bfca`
- 授權包含：exact apply 一次，以及 apply 內建失敗 rollback。
- 授權不包含：finalize、手動 rollback、reset、deploy、canary、activation、launchctl mutation、push 或 tag。

## 目的

在 fresh gates 全部通過後，從 V0383 immutable argv 執行唯一一次正式 promotion apply，使 actor、runtime manifest、private-stage readiness 與 activation barrier 收斂到 target；成功後停在 `POSTCHECK_PASSED` 並保留 durable rollback bundle，等待另行處置。

## 啟動契約

- 以 `codex/g8-v0381-exact-target-source` 啟動；HEAD 必須等於 target 且 worktree clean。
- V0383 evidence 由 main `7ff35ab544` 以 `git show` 唯讀取出到 task-owned `/private/tmp`；禁止 cherry-pick。
- exact argv 必須通過 machine binding：plan digest、argv digest、target、transaction root、capacity receipt、authority artifact 全部一致。

## Mutation 前 fresh gates

任一項非 PASS，零 production mutation 停止：

1. `git ls-remote --heads origin main` 最多且只能一次，必須等於 target；失敗不得 retry。
2. durable transaction root `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-v0383-5872284828-promotion-20260824` 必須不存在。
3. source clone 存在、clean、HEAD/remote identity 與 target/expected origin 一致。
4. actor HEAD、manifest identity/digest、private-stage digest、queue/state identity 全部與 V0383 plan before tuple一致。
5. capacity receipt digest、Rule24 主機基線／預算／停損證據為 current PASS；缺證據即 `NO-GO`。
6. Rule25 capability receipt/gate 為 current READY 且 `canary_created=false`；若本次 promotion contract 明確判定不適用，必須以正式 gate contract 的 machine evidence證明，不得自行文字豁免。
7. production protected before snapshot 完整；無未授權 drift。

## 唯一允許 mutation

只可從 V0383 `exact-apply-argv.json` 讀取 argv 並執行一次，不得手動改寫或重建：

- actor：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor`
- manifest：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`
- readiness：`/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/g36-5872284828-zero-write-20260824`
- barrier：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/four-lane-activation-g36-5872284828-zero-write-20260824.barrier`
- durable transaction/rollback：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-v0383-5872284828-promotion-20260824`

## 執行與失敗契約

- apply 只可 invocation 一次；禁止 retry。
- apply exception 時，正式 command 必須完成內建 rollback；只讀核對 durable receipt 為 `ROLLED_BACK / ROLLBACK_COMPLETE` 且 protected surfaces 回到 before tuple。不得再執行手動 rollback。
- apply 成功時必須為 `POSTCHECK_PASSED`；保留 rollback bundle，不得 finalize。
- 任何結果不確定、receipt 缺失、unexpected drift 或 transaction state 非法，立即 `UNKNOWN/BLOCKED` 停止。

## 可寫本卡 evidence

- `CARD-PANTHEON-G8-V0384-AUTHORIZED-DURABLE-PROMOTION-APPLY-20260824-RESULT.md`
- `g8_v0384_authorized_durable_promotion_apply_20260824/`

## 禁止範圍

- 禁止第二次 remote query 或第二次 apply。
- 禁止 finalize、手動 rollback、reset、deploy、canary、activation、launchctl mutation、push、tag、其他 remote write。
- 禁止修改 source、workflow、tests、shared metadata 或既有 artifact。
- 禁止派下一張卡。

## 驗收

- V0383 machine bindings全部 PASS。
- fresh gates有機器可讀 receipts。
- apply 成功則 durable receipt=`POSTCHECK_PASSED`、actor/manifest/target manifest digest一致、allowlisted writes精確、unexpected changed=[]、rollback bundle存在。
- apply 失敗則 rollback receipt完整且 before tuple restored。
- 所有 JSON可解析、evidence digests PASS、`git diff --check` PASS。
- 變更只落本卡 ownership；單一 commit，worktree clean。

## Verdict

只能是 `POSTCHECK_PASSED`、`ROLLED_BACK`、`BLOCKED` 或 `UNKNOWN`。

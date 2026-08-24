# PANTHEON G8 V0385 authorized promotion apply environment retry

## 工作名稱

V0385 authorized promotion apply environment retry

## 前因

- V0384 verdict=`BLOCKED`；remote query=1、apply=0、production mutation=0。
- 唯一 remote probe 在 sandbox 內因 DNS 失敗；未 retry。
- Codex worktree 由指定 branch 建立後呈 detached target 是平台正常語意，不應以 `git branch --show-current` 空值單獨判 FAIL。
- V0383 exact apply 尚未 invocation，使用者對該 exact payload 的一次 apply 授權尚未消耗。

## 精確授權（不變）

- target：`5872284828f9dd6f0a75adf407becaeadb50d61a`
- plan digest：`415eff6d83e48bc16ccb5335b77a170b750a0e8e2a45a9f6dc453fceead29840`
- apply argv digest：`db697635302ab6c44803cabb6aa6b9fcf16c7b36368a7d42b291a0ab0b6cc9b2`
- target manifest digest：`389cd799384af4628b9fc371d620b5e87bed52125f27d6612119158af568bfca`
- 包含 exact apply 一次與 command 內建 failure rollback。
- 不含 finalize、手動 rollback、reset、deploy、canary、activation、launchctl mutation、push、tag。

## 啟動修正

- 仍以 `codex/g8-v0381-exact-target-source` 作 create-thread startingState。
- 驗證該 ref 與 HEAD 都等於 target、worktree clean；detached HEAD 本身可接受。
- V0383 evidence 唯讀取自 main `7ff35ab544` 到 task-owned `/private/tmp`；禁止 cherry-pick。
- V0384 evidence 唯讀取自 main `e61b01d46c`，確認 apply count=0。

## Fresh gate 修正

- `git ls-remote --heads origin main` 全卡只可 invocation 一次；第一次即須以核准的 host/network execution 執行，不得先在 sandbox 試跑。
- 若 host/network approval 不可用或 query 失敗，立即 `BLOCKED`，不得 retry。
- remote main 必須精確等於 target。
- transaction root `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-v0383-5872284828-promotion-20260824` 必須不存在。
- source clone、actor、manifest、private stage、queue/state、protected snapshot 必須符合 V0383 before tuple，unexpected drift=[]。
- Rule24 fresh host baseline／budget／monitor／stop-loss／capacity receipt 必須 current PASS。
- Rule25 current capability receipt/gate 必須 READY 且 `canary_created=false`；正式 machine contract 證明不適用亦可，禁止文字豁免。
- 任一 gate 非 PASS：production mutation=0，停止。

## 唯一 mutation

- 只可從 V0383 `exact-apply-argv.json` 取出已驗 digest 的 argv，使用所需 host/filesystem approval 原樣執行一次。
- actor：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/actor`
- manifest：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`
- readiness：`/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/readiness/g36-5872284828-zero-write-20260824`
- barrier：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state/four-lane-activation-g36-5872284828-zero-write-20260824.barrier`
- transaction root：上述 durable path。
- apply 禁止 retry；exception 只允許內建 rollback，禁止手動 rollback。
- success 停在 `POSTCHECK_PASSED` 且保留 rollback bundle；禁止 finalize。

## Evidence ownership

- `CARD-PANTHEON-G8-V0385-AUTHORIZED-PROMOTION-APPLY-ENVIRONMENT-RETRY-20260824-RESULT.md`
- `g8_v0385_authorized_promotion_apply_environment_retry_20260824/`

## 驗收與禁止

- remote query count=1；apply count只能 0 或 1；所有 machine bindings、JSON、digests、allowlisted writes、before/after與 durable receipt可驗。
- verdict 只能 `POSTCHECK_PASSED`、`ROLLED_BACK`、`BLOCKED`、`UNKNOWN`。
- 禁止第二次 remote query、第二次 apply、finalize、手動 rollback、reset、deploy、canary、activation、launchctl mutation、push、tag、修改既有 artifact或派下一卡。
- repo 只改本卡 ownership；`git diff --check` PASS；單一 commit；worktree clean。

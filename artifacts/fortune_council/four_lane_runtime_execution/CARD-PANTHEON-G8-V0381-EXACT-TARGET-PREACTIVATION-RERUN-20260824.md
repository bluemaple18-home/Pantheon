# PANTHEON G8 V0381 exact-target preactivation rerun

## 工作名稱

V0381 exact-target preactivation rerun

## 目的

從 published target `5872284828f9dd6f0a75adf407becaeadb50d61a` 的乾淨 source checkout 重跑正式 production preactivation，排除 V0380 的 `LOCAL_HEAD_MISMATCH`；本卡只讀 production，不執行 mutation。

## 啟動契約

- 正式 thread 必須以 `5872284828f9dd6f0a75adf407becaeadb50d61a` 作為 starting ref。
- 第一個正式 preactivation 判定完成前，不得在 worktree 產生檔案或 commit；需要暫存輸出只能使用 task-owned `/tmp` 目錄。
- 正式判定時必須證明 `HEAD == required source == remote main == 5872284828f9dd6f0a75adf407becaeadb50d61a` 且 worktree clean。
- 判定完成後才可把 task-owned temporary evidence 搬入本卡輸出目錄並建立單一 commit。

## 可讀輸入

- target checkout 內的 `scripts.pantheon_g8_production_preactivation` 與既有正式 contracts。
- main `6e0c5dd0f6` 中的 V0380 RESULT/evidence，可用 `git show` 唯讀讀取，不得 cherry-pick。
- production actor、manifest、queue、state、transactions、stage、LaunchAgents、barriers，僅限 read-only。
- `origin/main` 最多一次 `ls-remote` 唯讀核對；失敗不得 retry。

## 可寫輸出

- `CARD-PANTHEON-G8-V0381-EXACT-TARGET-PREACTIVATION-RERUN-20260824-RESULT.md`
- `g8_v0381_exact_target_preactivation_rerun_20260824/`
- 執行期間 task-owned `/tmp` 目錄。

## 禁止範圍

- 禁止 fetch、pull、push、tag、remote ref 或 credential write。
- 禁止修改任何 production surface。
- 禁止 promotion apply、adoption、reset、deploy、canary、launchctl mutation。
- 禁止修改 source、workflow、tests、shared metadata 或既有 artifact。
- 禁止派下一張卡。

## 必交付內容

1. exact-target clean-source receipt。
2. fresh protected before/after snapshots 與 tripwire。
3. 正式 preactivation machine result；不得另造第二套 truth。
4. identity matrix：source、remote、actor、manifest、target。
5. 若 READY，產生精確 production adoption/reset 授權 payload、allowlist、前置 digests/generation、成功 receipts、rollback 與 stop conditions；不得執行。
6. verdict 只能是 `READY_FOR_PRODUCTION_ADOPTION_AUTHORIZATION`、`BLOCKED` 或 `UNKNOWN`。

## 驗證

- 所有 JSON 可解析。
- `git diff --check` 通過。
- protected tripwire `PASS` 且 `changed=[]`；否則 `BLOCKED`。
- 變更只落在本卡 ownership。
- 單一 commit，worktree 收尾乾淨。

## 交付格式

- verdict、唯一下一拍與精確授權 payload。
- commit SHA。
- 未 push、未 production write、未 canary 的明確聲明。

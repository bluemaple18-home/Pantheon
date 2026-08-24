# PANTHEON G8 V0380 production adoption preactivation

## 工作名稱

V0380 production adoption preactivation

## 目的

針對已發布的 target `5872284828f9dd6f0a75adf407becaeadb50d61a`，以既有正式 contract 產生 fresh、read-only production adoption/reset 前置判定與精確授權包；本卡不執行 production mutation。

## P0 已驗證事實

- `origin/main` 由 `91095924b1fe06955f525310b62cc0cfbf7948cd` fast-forward 至 `5872284828f9dd6f0a75adf407becaeadb50d61a`。
- push pre-gate：`PASS`。
- push 後唯讀 `ls-remote`：`refs/heads/main = 5872284828f9dd6f0a75adf407becaeadb50d61a`。
- production actor / manifest 在 V0378 為 `db9fb4343df212fd3b65546b017aba159620a058`，須重新唯讀觀測，不得假設仍相同。

## 可讀輸入

- V0378 current authority evidence。
- V0379 convergence decision packet。
- `scripts.pantheon_g8_production_preactivation` 與既有 promotion/adoption/reset contracts。
- production actor、manifest、queue、state、transactions、stage、LaunchAgents 與 barriers，僅限 read-only。
- 本機 target commit 與 Git graph，僅限 read-only。

## 可寫輸出

- `CARD-PANTHEON-G8-V0380-PRODUCTION-ADOPTION-PREACTIVATION-20260824-RESULT.md`
- `g8_v0380_production_adoption_preactivation_20260824/`

## 禁止範圍

- 禁止 fetch、pull、push、tag、remote ref 或 credential write。
- 禁止修改 actor、manifest、queue、state、transactions、stage、LaunchAgents、barriers。
- 禁止 deploy、promotion apply、adoption、reset、canary、launchctl mutation。
- 禁止修改 source、workflow、tests、shared metadata 或既有 artifact。
- 禁止派下一張卡。

## 必交付內容

1. fresh production protected before/after snapshot 與 mutation tripwire。
2. target、actor、manifest、remote publication receipt 的 identity matrix。
3. 沿用正式 preactivation contract 的 machine result；不得另造第二套 truth。
4. 若可執行，列出唯一 production mutation、精確 target、allowlist、前置 digest/generation、成功 receipts、rollback 與 stop conditions。
5. 明確產生下一拍需要使用者核准的 payload；本卡本身不構成 production write 授權。
6. verdict 只能是 `READY_FOR_PRODUCTION_ADOPTION_AUTHORIZATION`、`BLOCKED` 或 `UNKNOWN`。

## 驗證

- 所有 JSON 可解析。
- `git diff --check` 通過。
- before/after protected 集合一致；任何 drift 直接 `BLOCKED`。
- 變更只落在本卡 ownership。
- 單一 commit，worktree 收尾乾淨。

## 交付格式

- verdict、唯一下一拍與精確授權 payload。
- commit SHA。
- 未 push、未 production write、未 canary 的明確聲明。

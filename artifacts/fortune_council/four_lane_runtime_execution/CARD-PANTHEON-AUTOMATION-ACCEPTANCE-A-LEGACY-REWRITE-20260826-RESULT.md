# Pantheon 舊文原網址自動化驗收 Result

status: `BLOCKED`
card_id: `CARD-PANTHEON-AUTOMATION-ACCEPTANCE-A-LEGACY-REWRITE-20260826`
dispatch_key: `v1:83918062e381307bfe86c2cfa2c992518a567f6e93e7184f0d0f14bd92cafcef`
activation_token: `act-v1:eebaa1bf3994a16ecf51c0c5ed5f86c8acb3495d262c28d7c5b92ed195408191`
recorded_at_utc: `2026-08-26T03:48:53Z`

## 結論

本卡未進入 publication mutation。正式 publisher exact-run dry-run 在 mutation 前由既有 gate 擋下：

`PublishBlocked: local HEAD differs from origin/main: 6477ab815e8a != 0257bd5213ee`

這表示 runtime actor 的 local HEAD 是 `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`，但官方 remote `refs/heads/main` 是 `0257bd5213eed0d0df10661a54f6215901a54997`。卡片要求只用既有正式單篇 Publisher 流程，且禁止手動 push、替代 deploy 或偏離正式入口；因此停止並交付 BLOCKED。

## 已完成的唯讀證據

- 實體卡已重讀，Rule 21 digest 符合 `sha256:def530bb99caf5f40973305af0066378b92cede21ef5845714ac55b9814c7dd0`。
- CodeGraph readiness：PASS，索引 `583` files、`7034` nodes、`15792` edges。
- Runtime manifest 對齊卡片指定 actor/generation：
  - actor：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`
  - generation：`g47-6477ab81-activation-only-20260826`
  - queue：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue`
  - state：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/state`
- 七個 Pantheon launchd service label 逐一查詢皆為 not found / stopped；沒有啟動常駐服務。
- Readiness/capacity gate 只讀核對：
  - `official-gate-ready.json`：`READY`
  - `official-gate-blocked.json`：缺 `push` fixture 正確 `BLOCKED`
  - `capacity-receipt.json`：`PASS`
- 候選 run 鎖定為唯一未發布 legacy rewrite：
  - run_id：`legacy-auto-sweep-v1-astrology-0002-astro-base-02`
  - article_id：`ASTRO-BASE-02`
  - canonical：`https://www.mysticpantheon.com/articles/astrology/astrology-0002`
  - reviewer：`APPROVE`，findings 空
  - 原正文 hash：`0ae9b937f269a272102c1e94644e3cd613db609fd3cfb013c74a99f15b280449`
- 正式 deployment-preflight 回 `ready`，但後續 selector dry-run 被 clean-origin gate 擋下。

## Partial Mutation

- publication transaction：無
- public content update：無
- tag：無
- push：無
- ledger 新增 rewrite transaction：無
- runtime/public content 檔案 dirty state：無

唯一非內容副作用是官方 dry-run 前置 `fetch origin main` 更新了 runtime actor 的 local Git metadata；沒有遠端寫入。

## 最後安全狀態

- runtime actor worktree clean。
- 本工作區在寫入本卡 result/evidence 前為 clean；交付只包含 allowlist 內 result/evidence。
- `state/evidence` 仍只有既有 `rewrite-0.3.367`、`rewrite-0.3.368`，沒有產生 `rewrite-0.3.372` 或其他新 rewrite evidence。
- ledger hash 保持 `224d78887b4a1062702e3b920377eda8ff2abb8264b1ec48861254afe6fddabe`。
- 原文章 prerender HTML hash 保持 `97216e5578803f3a2fe1d03b82f33be04ec3fdac3e768002c9d434a19d2d6a31`。

## Blocker

root_cause: `REMOTE_MAIN_BEHIND_RUNTIME_ACTOR`

同 blocker 嘗試次數：`1`

正式 publisher 要求 actor local HEAD 與 remote `origin/main` 相同，避免 lagging/stale runtime 發布。當前 remote main 仍在新文 canary publication commit `0257bd5213eed0d0df10661a54f6215901a54997`，而 active runtime actor 是後續修復 commit `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`。這不是舊文內容品質 blocker。

## 下一步需要的授權

主線需決定是否先讓 remote `main` 與已 activation 的 runtime actor authority 收斂。此卡沒有授權我手動 push `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`、做 promotion、改 publisher clean-origin gate，或繞過正式入口。

## Evidence

- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_a_legacy_rewrite_20260826/evidence.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_a_legacy_rewrite_20260826/machine-summary.json`

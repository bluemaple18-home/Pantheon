---
id: CARD-PANTHEON-G8-RUNTIME-PROMOTION-CYCLE-23-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: implementation
cycle: 23
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: 規格固定；含一次 remote fast-forward、runtime promotion 與 private stage mutation，未升 Sol。
---

# 收斂 G8 runtime 並驗證 Capacity

## 目標

在 actor Git authority 已對齊後，把已驗收的 Capacity exit-0 修正經正式 promotion/staging 路徑收斂到 origin、runtime actor 與 private stage；Capacity preflight 必須 PASS。保持零 activation、零 canary、零 publish。

## 固定 authority

- source commit：`b1719c0d6243c7ec6372889405a846ccd1b666ed`；source fix：`20cf1ddb1c`；capacity suite：`51 passed`。
- origin/main before 與 standalone actor before：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`，均須 clean/coherent。
- actor 不得再出現在 Pantheon `git worktree list --porcelain`；quarantine evidence 必須存在且 stale HEAD 為 `e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；Publisher `max-runs=1`。

## 前置閘門

1. host free disk `>=10%` 且 resource guard PASS；不足即 `BLOCKED / CAPACITY_SAFETY`，零 mutation。
2. 唯讀重驗 source、origin、actor、registry absence、manifest、stage、live seven、queue、exact run；任一 drift 首次即停。
3. 只接受 ordinary fast-forward；禁止 force、merge、rebase、換 target 或修改 source。
4. promotion plan、Gate A、authorization、apply argv 必須全部由既有正式入口產生並互綁；非 PASS 不重試。

## 唯一順序

1. 保存 mutation 前 authority、容量、queue、transaction、tag、content、LaunchAgent、stage 快照。
2. 跑一次受影響 release/promotion preflight；PASS 後允許一次普通 fast-forward push，使 origin/main 精確等於 source。
3. 用 `scripts/pantheon_content_runtime_promotion.py` 的 plan/apply/postcheck/finalize seam 執行一次 promotion，保留 rollback bundle。
4. 從新 actor 依序執行 coordinator＋四 lanes `--install` 一次、Publisher exact-run `--install` 一次。
5. 執行 Capacity public `--preflight` 一次；必須 `preactivation_transition=accepted/PASS`。失敗即 `BLOCKED / NO ACTIVATION`，禁止 retry/capacity install。
6. PASS 後才執行 Capacity `--install` 一次；重驗七服務 stage coherent、live 仍未啟動、queue/exact run 未變。

## 可改範圍

- origin/main：僅一次普通 fast-forward。
- 正式 runtime transaction root、actor、manifest、rollback bundle：僅既有 promotion 工具可寫。
- local-only private stage：僅既有 installers 可寫。
- `.work/CARD-PANTHEON-G8-RUNTIME-PROMOTION-CYCLE-23-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-RUNTIME-PROMOTION-CYCLE-23-20260821-RESULT.md`。

## 禁止

- 禁止修改 source、tests、config、workflow、queue、state、registry、sitemap、feed、live plist。
- 禁止 activation、canary、lane run、Publisher transaction/tag/publish；禁止 `launchctl bootstrap/bootout/kickstart`。
- 禁止重跑失敗步驟、換入口、direct module、手動拼 plist、放寬 identity/capacity gate。
- 禁止另開 Reviewer、Repair、診斷或 replacement thread。

## 驗收與停損

- push/promotion/install/preflight 各 `0|1`；retry=`0`；activation/canary/transaction/tag/publish=`0`。
- 成功須證明 origin/actor/source 收斂、七服務 stage coherent、Capacity transition PASS、live loaded/no-PID、queue/exact run 未變。
- 任一 blocker 首次 fail closed；`git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `PROMOTED / CAPACITY PASS / NO CANARY`
- `BLOCKED / NO ACTIVATION`

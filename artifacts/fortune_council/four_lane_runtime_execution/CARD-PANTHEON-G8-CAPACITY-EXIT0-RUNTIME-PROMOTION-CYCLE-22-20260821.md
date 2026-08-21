---
id: CARD-PANTHEON-G8-CAPACITY-EXIT0-RUNTIME-PROMOTION-CYCLE-22-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: implementation
cycle: 22
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，但含一次 remote fast-forward、runtime promotion 與 private stage mutation。
---

# 將 Capacity exit-0 修正帶入 G8 runtime

## Root question

能否只把已驗收的 Capacity preactivation exit-0 契約修正，透過既有正式 promotion/staging 路徑收斂到 origin、runtime actor 與 private stage，並讓唯一一次正式 Capacity preflight 回到 PASS，同時保持零 activation、零 canary、零 publish？

## 固定 authority

- source commit：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- source fix commit：`20cf1ddb1c`；完整 capacity suite：`51 passed in 19.12s`。
- origin/main before：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`；必須仍為 source ancestor。
- runtime actor before：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`，且 clean。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；Publisher `max-runs=1`。
- current private stage 已存在；不得沿用其舊 digest 冒充新 authority。

## 前置硬閘門

1. host free disk 必須 `>=10%`，且 resource guard PASS；不足立即 `BLOCKED / CAPACITY_SAFETY`，零 create／push／promotion／installer。
2. source、origin、actor、manifest、live seven、queue、exact run 全部重新唯讀量測；任一 drift 立即停止。
3. 只接受 ordinary fast-forward；禁止 force、merge、rebase、挑選另一 target 或修改 source。
4. promotion deterministic plan、Gate A、一次性 authorization、apply argv 必須全部由既有正式入口產生並互相綁定；任一非 PASS 不重試。

## 唯一執行順序

1. 保存 mutation 前 authority、容量、queue、transaction、tag、content、LaunchAgent 與 stage 快照。
2. 跑一次受影響 release／promotion preflight；PASS 後才允許一次普通 fast-forward push，使 origin/main 精確等於 source commit。
3. 用 `scripts/pantheon_content_runtime_promotion.py` 的正式 plan/apply/postcheck/finalize seam 執行一次 promotion；保留 rollback bundle。
4. 從新 actor 依序執行 coordinator＋四 lanes `--install` 一次、Publisher exact-run `--install` 一次，只重建六服務 private stage。
5. 執行 Capacity public `--preflight` 一次；必須回 `preactivation_transition=accepted/PASS`。失敗立即 `BLOCKED / NO ACTIVATION`，禁止 retry 與 capacity install。
6. preflight PASS 後才執行 Capacity `--install` 一次，完成七服務 private stage；再驗 actor/manifest/generation/digest/staged/live/queue 零漂移。

## 可改範圍

- origin/main：只允許上述一次普通 fast-forward。
- 正式 runtime transaction root、actor、manifest與rollback bundle：只能由既有 promotion 工具寫入。
- `/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage/**`：只能由既有 installers 寫入。
- 本 worktree `.work/CARD-PANTHEON-G8-CAPACITY-EXIT0-RUNTIME-PROMOTION-CYCLE-22-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-CAPACITY-EXIT0-RUNTIME-PROMOTION-CYCLE-22-20260821-RESULT.md`。

## 禁止

- 禁止修改 source、tests、config、workflow、queue、state、registry、sitemap、feed、live plist。
- 禁止 `launchctl bootstrap/bootout/kickstart`、任何 activation、lane run、canary、Publisher transaction、tag、publish。
- 禁止重跑失敗步驟、換入口、direct module、手動拼 plist、放寬容量或 identity gate。
- 禁止另開 Reviewer、Repair、診斷卡或 replacement thread。

## 驗收與停損

- push=`0|1`；promotion apply=`0|1`；coordinator install=`0|1`；Publisher install=`0|1`；Capacity preflight=`0|1`；Capacity install=`0|1`；retry=`0`。
- 終局成功必須同時證明 origin/actor/source 收斂、七服務 stage coherent、Capacity transition PASS、live 仍 activation-only loaded/no-PID、queue/exact run 未變。
- activation/canary/transaction/tag/publish=`0`。
- 任一 blocker 首次即 fail closed；不得以同卡繼續考古或修 source。
- `git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

只能回報：

- `PROMOTED / CAPACITY PASS / NO CANARY`
- `BLOCKED / NO ACTIVATION`

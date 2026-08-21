---
id: CARD-PANTHEON-G8-LIVE-ACTIVATION-ONLY-CONVERGENCE-CYCLE-25-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: implementation
cycle: 25
thickness: strict
risk: production
model: gpt-5.5
reasoning: high
model_reason: 規格固定；只執行一次既有 activation-only 正式入口，未升 Sol。
---

# 對齊 G8 live activation-only 至 G23

## 目標

解除 Cycle24 的唯一 blocker：把 live 七服務 activation-only identity 從 coherent G17 收斂到已驗證的 current G23 stage。只做 activation-only，不執行 canary、Publisher child、transaction、tag 或 push。

## 固定 authority

- 主線/card source：`dd3691cb32`；current runtime actor/source：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`。
- identity：`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`。
- generation：`g23-b1719c0d-20260821T022959Z`。
- stage digest：`aa801a5bd378bb4d7acd87bffb2407d31eb940d68ffabf4e2b14507cdd603c7b`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；Publisher `max-runs=1`。
- Cycle24 blocker：`publisher_only_live_activation_only_validation`；live coherent G17，stage/current G23。

## 前置閘門

1. host free disk `>=10%`、resource guard、current capability receipt、official readiness gate、fail-closed fixture、Capacity preflight 全部 PASS。
2. 唯讀重驗 origin/main、actor、manifest、stage、live seven、queue、exact run；除預期 G17→G23 transition 外任何 drift 即停。
3. `preactivation_transition=accepted`，且七個 staged plist 必須 coherent G23、activation mode 為 `activation-only`。
4. 保存 live plist、launchctl identity、queue/state/exact-run 與 rollback 所需快照；缺任一證據即停。

## 唯一 mutation

1. 只允許正式入口 `scripts/install_agy_gemini_coordinator_launchd.sh --activate-only` 一次。
2. 必須使用 current manifest/stage 與單一 correlation ID；禁止手動 install plist、直接 launchctl、拼接替代入口。
3. 成功後立即驗證七個 live plist 全部為 current G23 activation-only identity，七服務 loaded/no-PID，barrier 未發布。
4. queue/state/exact run 必須不變；Publisher child、其他六服務 child I/O、transaction、tag、push 全部為 `0`。

## 可改範圍

- live 七個 LaunchAgent plist 與 launchctl registration：僅由上述正式入口寫入。
- 正式入口既有 rollback/failure receipt 與 `.work/CARD-PANTHEON-G8-LIVE-ACTIVATION-ONLY-CONVERGENCE-CYCLE-25-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-LIVE-ACTIVATION-ONLY-CONVERGENCE-CYCLE-25-20260821-RESULT.md`。

## 禁止

- 禁止修改 source、tests、config、workflow、manifest、stage、queue、state、registry、sitemap、feed。
- 禁止 `--activate`、`--activate-publisher-only`、barrier publish、canary、transaction、tag、push。
- 禁止 retry、第二次 activation、換入口、放寬 identity/capacity gate、另開 replacement thread。

## 驗收與停損

- activation-only invocation=`0|1`；retry=`0`；canary/Publisher child/transaction/tag/push=`0`。
- 成功須證明 live 七服務 coherent G23、loaded/no-PID、stage/current identity 一致、queue/state/exact run 不變。
- 失敗須證明 rollback/fail-closed 狀態與 production mutation accounting；首次失敗立即停止。
- `git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `ALIGNED / NO CANARY`
- `BLOCKED / NO CANARY`

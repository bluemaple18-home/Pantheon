---
id: CARD-PANTHEON-G8-HOST-CAPACITY-STAGE-COMPLETION-CYCLE-28-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: repair
cycle: 28
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: blocker 已縮至 host telemetry 與第七份 Capacity plist；未升 Sol。
---

# 以 host telemetry 補齊 G23 Capacity stage

## 目標

承接 Cycle27 已正確建立且 byte-stable 的六服務 G23 private stage；不重跑 coordinator／lane／Publisher installers。只在 host 權限層執行一次 Capacity preflight，PASS 後執行一次 Capacity install，補齊第七份 plist。零 activation、零 canary。

## 固定 authority

- 主線/card source：`452f1da26e`；runtime actor/source：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`；identity：`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`；generation：`g23-b1719c0d-20260821T022959Z`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target `ASTRO-BASE-01:en`；Publisher `max-runs=1`。
- Cycle27 stage：六份 plist 存在且前後 byte-identical；Capacity plist 缺失；canonical TMPDIR 問題已排除。
- Cycle27 blocker：sandbox receipt 同時含 `rss_telemetry_unknown` 與 `swap_telemetry_unknown`，不符合 preactivation receipt contract。

## 前置閘門

1. capability/readiness/fail-closed/capacity proof、actor/manifest/live/queue/state/exact run 全 PASS。
2. 六服務 partial stage 必須精確符合 Cycle27 receipt；任何 drift 即停。
3. 本卡唯一 Capacity preflight 必須一開始就以 host approval／host execution 執行；禁止先跑 sandbox 版本再重試。
4. `TMPDIR=/private/tmp`；命令必須從 current runtime actor 執行。

## 唯一順序

1. 保存 stage/live/queue/state/exact-run 前快照。
2. host-level 執行 Capacity public `--preflight` 一次；必須 exit 0、`preactivation_transition=accepted/PASS`。
3. PASS 後 host-level 執行 Capacity正式 `--install` 一次，固定 canonical TMPDIR。
4. 重驗七服務 private stage coherent G23、Publisher exact-run/max-runs 鎖定、Capacity staged plist 存在；live/queue/state/exact run 不變。

## 可改範圍

- local-only private stage：僅 Capacity installer 可補第七份 plist與正式 receipt。
- `.work/CARD-PANTHEON-G8-HOST-CAPACITY-STAGE-COMPLETION-CYCLE-28-20260821/**`。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-HOST-CAPACITY-STAGE-COMPLETION-CYCLE-28-20260821-RESULT.md`。

## 禁止

- 禁止重跑前六服務 installers、修改 source/config/manifest/live plist/queue/state。
- 禁止 sandbox-first preflight、retry、第二次 preflight/install、換入口。
- 禁止 activation、launchctl mutation、barrier publish、canary、Publisher child、transaction、tag、push。

## 驗收與停損

- Capacity host preflight/install=`0|1`；其他 installers=`0`；retry=`0`。
- activation/canary/transaction/tag/push=`0`。
- 成功須證明七服務 stage coherent G23、Capacity PASS、live/queue/state/exact run 不變。
- 首次失敗立即停止；`git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `COMPLETED / CAPACITY PASS / NO CANARY`
- `BLOCKED / NO ACTIVATION`

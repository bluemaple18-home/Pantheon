---
id: CARD-PANTHEON-G8-QUIESCENT-CAPACITY-STAGE-CYCLE-29-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: repair
cycle: 29
thickness: strict
risk: production-adjacent
model: gpt-5.5
reasoning: high
model_reason: 只處理已證實的瞬時 PID 競態；bounded wait 後單次 host preflight，未升 Sol。
---

# 在 quiescent window 補齊 G23 Capacity stage

## 目標

承接 Cycle28 byte-stable 六服務 stage。以唯讀 bounded wait 找到所有 live G23 services 連續 no-PID 的 quiescent window，隨即執行唯一一次 host Capacity preflight；PASS 後補第七份 Capacity plist。零 activation、零 canary。

## 固定 authority

- 主線/card source：`d6f1b923ec`；runtime actor/source：`b1719c0d6243c7ec6372889405a846ccd1b666ed`。
- manifest／identity／generation：`d1ec853fd1b32e4a77e9ab45a19a9482bad5a5c692cfc5c8396cf365a23cccbf`／`0152d79f9901b4000c43c70966907e5001846dc7792e865d9255ada62f91ebae`／`g23-b1719c0d-20260821T022959Z`。
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`；target `ASTRO-BASE-01:en`；Publisher `max-runs=1`。
- Cycle28：raw host telemetry PASS；唯一 blocker 為 preflight 取樣瞬間六個 services 帶 PID；前後均 no-PID。

## 前置與 bounded wait

1. 六服務 stage、actor、manifest、live、queue、state、exact run 必須精確符合 Cycle28 terminal receipt。
2. 唯讀觀察 launchctl，最多 `300` 秒；每 `2` 秒一次，禁止 kickstart/bootout/bootstrap。
3. 只有七服務連續 `3` 次皆 loaded/no-PID 才算 quiescent；期限內未達成即 `BLOCKED / NO PREFLIGHT`。
4. 達成後立即從 current actor、`TMPDIR=/private/tmp`，第一次就以 host execution 執行正式 Capacity preflight。

## 唯一 mutation 順序

1. host Capacity public `--preflight` 一次；必須 exit 0、`preactivation_transition=accepted/PASS`。
2. PASS 後 host Capacity `--install` 一次。
3. 重驗七服務 private stage coherent G23；live/queue/state/exact run 不變。

## 禁止

- 禁止前六服務 installer、sandbox-first、retry、第二次 preflight/install、任何 launchctl mutation。
- 禁止 activation、barrier publish、canary、Publisher child、transaction、tag、push。
- 禁止修改 source/config/manifest/live plist/queue/state，禁止 replacement thread。

## 交付與停損

- 唯讀 samples 可多次但最長 300 秒；Capacity preflight/install=`0|1`；retry=`0`。
- 首次正式 preflight 非零立即停止；本同步 blocker 不再開下一張相同方法卡。
- 唯一 committed result：同目錄 `CARD-PANTHEON-G8-QUIESCENT-CAPACITY-STAGE-CYCLE-29-20260821-RESULT.md`。
- `git diff --check` PASS；candidate commit 只含 RESULT。

## 終局

- `COMPLETED / CAPACITY PASS / NO CANARY`
- `BLOCKED / NO PREFLIGHT`
- `BLOCKED / NO ACTIVATION`

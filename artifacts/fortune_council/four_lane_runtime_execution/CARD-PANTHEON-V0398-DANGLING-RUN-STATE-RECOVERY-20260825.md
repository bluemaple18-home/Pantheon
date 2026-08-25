---
id: CARD-PANTHEON-V0398-DANGLING-RUN-STATE-RECOVERY-20260825
status: ready
chain_id: PANTHEON-PUBLISH-FLOW-ACTIVATION-CANARY-20260825
role: repair
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production registry/data transition 與 runtime promotion 為固定根因、高回退成本的 strict Repair。
target_sha: d8df768164a289bb54039b0d65edb6de909e468a
---

# Pantheon dangling run state recovery

工作名稱：Pantheon dangling run state recovery

任務目的：修復 V0397 唯一 blocker：V0391 registry 為 active，但其 `run_dir` 已全機不存在；用既有正式狀態轉移入口 fail-closed 關閉不可恢復 identity，建立 canonical durable root，然後重跑同一 production promotion。

## 已證明事實

- `origin/main=d8df768164a289bb54039b0d65edb6de909e468a`。
- V0397 planner：`NO-GO / preserved durable run root is invalid`，production mutation=0。
- queue 有 143 registries；V0391 registry active，run_dir 指向 actor `.work/gsc-copy/v0391-publish-canary-20260825-01`。
- 該 V0391 目錄在整個 runtime root 不存在，archive/failed/processing/inbox 亦無可恢復 payload。
- canonical `<queue-root>/gsc-copy` 不存在。

## 單一切片

1. 用 repo 既有正式 recovery/registry transaction seam，把不可恢復的 V0391 active identity轉成 terminal failed/abandoned；禁止假造 run_dir、brief 或新 identity。
2. 用既有 installer/promotion seam 建立 canonical durable root；禁止手動拼第二套 workflow。
3. 重跑 V0397 fresh gates與正式 plan→apply→postcheck→finalize，target 固定 `d8df768164...`。

## 禁止

- 禁止改 source/tests、清 queue、刪 registry、複製不相干 runs、建立 replacement/new run、Gemini、publish、tag、push、另開任務。
- 禁止把 empty directory 或手寫 JSON 當成 recovery 成功。
- 任一正式 seam 不存在或狀態轉移無可驗 receipt：mutation 前停止，回報單一設計缺口。

## 驗收

- V0391 舊 identity 有正式 terminal receipt，且不再被當 active preserved run。
- canonical durable root 存在且符合 installer/promotion identity。
- promotion transaction `COMMITTED`；actor/manifest/stage/barrier 綁定 `d8df768164...`。
- 完成後停止，主線回原 V0391 thread 建立唯一新 canary 並驗公開網址。

## RESULT

狀態：pending

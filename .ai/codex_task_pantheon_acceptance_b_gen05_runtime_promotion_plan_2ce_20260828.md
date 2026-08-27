---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-PLAN-2CE-20260828
title: 核對主線執行環境升版計畫
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION
role: implementation
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production promotion 前需以正式入口重算 target、runtime authority、Rule24、Rule25 與 zero-mutation；本卡不授權 apply
parent_candidate: 2ce431ec41f5187531d88b52dfa91cef0373d8b5
---

# Pantheon Acceptance B：gen05 runtime promotion plan for 2ce431

## Root question

遠端主線 `2ce431ec41f5187531d88b52dfa91cef0373d8b5` 是否能由目前 production actor／manifest／private stage 狀態，產生 fresh、可重算、fail-closed 的正式 promotion plan，且 Rule24、Rule25 與 production protected bytes 全部保持一致、mutation 為 0？

## 已鎖定事實

- `origin/main` 已推到 `2ce431ec41f5187531d88b52dfa91cef0373d8b5`。
- readiness planner authority Repair 已由原 Reviewer 裁決 `GEN05_RUNTIME_PROMOTION_READINESS_REVIEW_GO`。
- 上一份 readiness plan 的 product target 是 `79884d8b...`，只能作歷史 baseline，不得授權本次 promotion。
- gen05 尚未執行；本卡不得做 gen04→gen05 transition，也不得消耗 semantic generation。

## 目標

1. Fresh 核對 source、origin/main、production actor、runtime manifest、private stage、queue/state 與 continuation bytes。
2. 以既有正式入口為 target `2ce431...` 產生 promotion **plan only**。
3. 重驗 Rule24 capacity 與 Rule25 `create → run → select → publish → transaction → tag → push` capability receipt。
4. 交付明確的 `PROMOTION_PLAN_GO` 或 `BLOCKED`，供 Owner 決定是否授權 production promotion mutation。

## 可寫入

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_runtime_promotion_plan_2ce_20260828/**`
- 唯一結果：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-PLAN-2CE-20260828.md`
- task-owned `/private/tmp` synthetic outputs；repo 內保存可重算 receipt 與必要 raw evidence。

## 禁止範圍

- 不得修改 code、config、tests、queue/state、continuation、runtime manifest、private stage、production actor 或 production content。
- 不得執行 promotion apply/postcheck/finalize、copy/install/reload、launchctl、service mutation、provider、gen04→gen05 transition、production gen05、publish、transaction、tag、push 或 deploy。
- 不得沿用 `79884d8b...` 的 plan digest、capacity receipt或 READY 文案冒充本次 target authority。
- 不得手寫 plan、capacity receipt、capability receipt或 mutation counters；只接受既有正式入口與可驗證 artifact bytes。
- 正式 plan入口若會建立 transaction root或寫 production state，立即停止並回 `BLOCKED / MUTATION_BOUNDARY`。

## 必查契約

1. 先作 task-semantic CodeGraph query；無結果或失敗才限域 `rg`。
2. 驗證 `HEAD`／`origin/main` 精確等於 `2ce431...`，source clean、origin一致；以實際 production bytes核對 current actor SHA、manifest digest、stage generation/digest。
3. 以修復後 planner 的 stable `plan_authority` 產生 fresh plan；runtime locator仍須 canonical 並在 plan-time fail closed，但不得進 authoritative digest。
4. Rule24：fresh host free、write-path inventory、bytes/file limits、兩個 representative synthetic cycles、RSS/swap、reclamation與stop-loss全部 PASS；planner實際讀取的 committed receipt bytes SHA 必須等於傳入 digest。
5. Rule25：七段正式入口、I/O、identity/correlation、獨立 PASS與BLOCKED evidence完整；official gate `READY`且 `canary_created=false`。
6. Continuation：`next_generation=5`、gen04 abandoned/non-resumable、gen05 source-ref-map存在、gen06不存在；只能讀取。
7. 對 production protected roots做 before／after byte digest，證明完全不變；所有 promotion/provider/publish/transaction/tag/push/deploy/service mutation counters為 0。
8. 明列 apply時的 exact target、current actor/manifest/stage、plan digest、capacity digest、target manifest digest、transaction root與 rollback boundary，但不得執行。

## 驗收

- 最終裁決只能是 `PROMOTION_PLAN_GO` 或 `BLOCKED`。
- `PROMOTION_PLAN_GO` 必須同時具備：target `2ce431...`、fresh plan `READY_TO_APPLY`、Rule24 `PASS`、Rule25 `READY`、continuation authority一致、production bytes before==after、mutation counters全部為 0。
- JSON/schema/checksum/evidence index可重算，index missing=0、digest mismatch=0、不得索引 `.git/` metadata。
- 重跑受影響 promotion／Rule24／Rule25 tests與 `git diff --check`。
- 單一 candidate commit，不 amend、不 push；回傳 full SHA、parent、verdict、exact plan authority與 residual risk。

## 停損

- 任一 authority不唯一、fresh capacity失敗、Rule25不完整、production bytes漂移、正式 plan入口欲 mutation或 target不是 `2ce431...`：立即 `BLOCKED`。
- 本卡 GO 不是 promotion授權；Owner未另行明確同意前不得做 production mutation。

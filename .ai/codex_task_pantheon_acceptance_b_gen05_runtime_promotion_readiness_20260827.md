---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260827
title: ↳ 工作｜核對 gen05 runtime promotion readiness
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production runtime promotion 前的 actor、manifest、Rule24 與 Rule25 是固定核心契約；本卡僅做唯讀與 synthetic readiness，不執行 production mutation
parent_candidate: 79884d8bff7256aa9d1adcb7133162d7ac30b86d
---

# Pantheon Acceptance B：gen05 runtime promotion readiness

## Root question

`origin/main=79884d8bff7256aa9d1adcb7133162d7ac30b86d` 是否已具備可回滾、fail-closed 的 runtime promotion 前置條件，並能在不產生 production mutation 的情況下證明 Rule24 capacity 與 Rule25 `create → run → select → publish → transaction → tag → push` readiness？

## 已鎖定前提

- gen04 → gen05 lifecycle 修復已進主線。
- gen05 topology guard RCA 主裁決是 `TOPOLOGY_GUARD_OVERREACH`；修復 `79884d8b...` 已由原 Reviewer 判定 GO。
- `main` 與 `origin/main` 已對齊 `79884d8b...`，`tests/test_agy_multilingual_pipeline.py` 為 `224 passed`。
- 本卡不重開 RCA、Repair、Reviewer、boundary、G8 或 publisher 架構。

## 目標

1. 唯讀核對 source、origin/main、production actor、runtime manifest、private stage、queue/state 與 continuation identity。
2. 以既有正式入口產生 deterministic promotion **plan only**，或明確裁決哪個前置缺口使 plan 不可建立。
3. 重驗 Rule24 容量證據與 Rule25 capability receipt；任一節點缺正式入口、I/O、identity/correlation、PASS 或 fail-closed BLOCKED 證據即回 `BLOCKED`。
4. 交付一份可由主線決定是否請求 promotion mutation 授權的 receipt；不得把 readiness 當授權。

## 允許寫入

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_runtime_promotion_readiness_20260827/**`
- 唯一結果：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260827.md`
- task-owned `/private/tmp` synthetic evidence；只可在卡內記錄可重算摘要，不得把絕對路徑寫入 repo artifact。

## 禁止範圍

- 不得修改 code、config、tests、queue/state、continuation、production artifacts、runtime manifest、private stage 或 LaunchAgent。
- 不得執行 promotion apply/finalize、copy/install/reload、launchctl、service mutation、provider call、新建 gen06、publish、transaction、tag、push 或 deploy。
- 不得用 ad-hoc shell、mock、狀態文案、HTTP 200、tag 存在或舊 receipt 單獨自證 readiness。
- 若既有 promotion `plan` 入口會寫 production transaction root，不得執行；只能由 source contract 與既有 evidence 建立授權前 payload，並標記 `BLOCKED / MUTATION_AUTHORITY_REQUIRED`。
- 不得為了通過 readiness 開 Repair；若發現 measured gap，只鎖定一個 minimum implementation frontier 交回主線。

## 必查契約

1. 先執行 CodeGraph task-semantic query，無結果或失敗才限域 `rg`；不得用 card ID 當 query。
2. 核對 `HEAD` / `origin/main` / actor SHA、actor clean state、manifest digest、stage generation/digest、queue/state roots 與 gen05 continuation authority；不得將 allocation 當 committed generation。
3. 找出 repo 內唯一正式 promotion plan/apply/postcheck/finalize 入口，列出 exact argv、inputs、outputs、mutation allowlist、rollback 與 terminal stops。
4. Rule24：重用現有正式 capacity seam，核對 write-path inventory、bytes/file limits、host free、兩個 representative synthetic cycles、RSS/swap、reclamation 與 stop-loss。證據非 fresh 或不同 actor/manifest identity 即 `NO-GO`。
5. Rule25：用官方 template/gate 核對七段同一 execution line/correlation；每段需獨立 PASS 與 BLOCKED artifact，且 `canary_created=false`。
6. 核對 gen05 下一次正式入口的計畫是否仍為：先無 provider 地完成必要 continuation transition，之後才能消耗唯一 semantic generation；不在本卡執行。
7. 對 production 目錄及受保護 artifacts 做 before/after bytes digest，證明 mutation=0。

## 驗收

- 最終單一裁決只能是 `PROMOTION_READINESS_GO` 或 `BLOCKED`。
- `PROMOTION_READINESS_GO` 必須同時具備：exact promotion plan payload、Rule24 `PASS`、Rule25 `READY`、actor/manifest/stage authority 一致、production bytes before==after、所有 mutation counters=0。
- 若 `BLOCKED`，只回傳第一個 fail-closed blocker、已通過的 gates、安全狀態與單一 bounded next frontier；不得延伸架構。
- JSON/schema/checksum 可重算，`git diff --check` 通過，changed files 精確等於 allowlist。
- 單一 candidate commit，不 amend、不 push；回傳 SHA、parent、verdict、evidence index 與 residual risk。

## 停損

- 任一讀取需要外部權限、任一正式入口會寫 production state，或 actor/manifest/queue authority 不唯一：立即停止並交回主線。
- 不得以 Owner 的 `繼續` 推導 promotion、production gen05 或 publish 授權。

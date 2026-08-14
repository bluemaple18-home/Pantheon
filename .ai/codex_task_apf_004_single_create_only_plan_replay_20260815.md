---
id: APF-004-SINGLE-CREATE-ONLY-PLAN-REPLAY
title: 重跑單筆 create-only production plan
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production runtime 的 authority-bound plan 證據需固定核心契約、真實 identity 與 fail-closed guards
parent_candidate: 2ad9af5b44a0e5d91774cbaa7d3e2463996c8203
traces_to:
  - FR-SINGLE-PLAN-001
  - SC-SINGLE-PLAN-001
  - SC-SINGLE-PLAN-002
---

# APF-004-SINGLE-CREATE-ONLY-PLAN-REPLAY｜重跑單筆 production plan

## 需求追溯

- `FR-SINGLE-PLAN-001`：以正式 `create_single_source_run_adapter` 對既有 authority-bound single payload 執行一次 plan-only。
- `SC-SINGLE-PLAN-001`：回傳恰好 1 run、3 個 expected writes、deterministic identity，且 authority digests 對上 committed artifacts。
- `SC-SINGLE-PLAN-002`：production queue/state/run-root 前後一致；apply、register、write、runner、model、publish、tag、push 全為 0。
- blocking edges：`2ad9af5b44` 已進 `origin/main`；目前 frontier 僅本卡。production apply 被本卡、獨立 Review 與後續 mutation 核准阻擋。

## 固定 authority

- `authorized-request.json`：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/create_run_only_20260814/authorized-request.json`
- `confirmed-single-payload.json`：同目錄下 `confirmed-single-payload.json`
- exact tuple：`matrix / ASTRO-SCENARIO-BIG-THREE / zh-TW / new / apf-001-v1 / apf-work-b1666341df10a14c1a586141`
- `confirmed_payload_digest` 與 `activation_authorization_digest` 必須重算上述兩檔實際 SHA-256；禁止手填 sentinel。

## 任務五行卡

- 目標：在正式 production runtime 對固定單筆 payload 呼叫新入口 `plan_only=True` 恰好一次，產出可重算 plan replay evidence。
- 可寫：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/single_create_plan_replay_20260815/**`。
- 禁止：不得 `plan_only=False`；不得 create/register/write queue/state/run；不得 runner、select、external model、publish、publisher transaction、tag、push、deploy、schedule、LaunchAgent；不得改 code/config/tests。
- 驗收：正式 actor/runtime SHA 對上 `origin/main=2ad9af5b44...`；輸入 exactly 1；輸出 1 run／3 writes；所有 mutation guards 0；before/after byte-for-byte 一致。
- 證據：authority input、invocation trace、official output、pre/post snapshot、replay verification、plan receipt；JSON/digest/sanitizer/diff-check PASS。

## 執行契約

1. 先唯讀核對 runtime manifest、actor HEAD、queue/state/run roots、activation barrier 與無 publisher/runner LaunchAgent。
2. production actor 若未包含 `2ad9af5b44` 的新入口，立即 `BLOCKED_RUNTIME_NOT_PROMOTED`；禁止自行 deploy、copy、realign 或修改 runtime。
3. 若入口可用，安裝 fail-fast monkeypatch guards：`atomic_write_json`、`register_run`、apply preflight、runner、model 與所有下游 seam 一旦觸及即拋錯。
4. 只允許一次 authority-bound `create_single_source_run_adapter(..., plan_only=True, max_runs=1)`。
5. 成功門檻：`status=planned`、`production_mutation=false`、runs 長度 1、lane=new、exact deterministic run ID、expected write set 長度 3，且 paths 只含該 run brief/state 與 create-run transaction receipt。
6. 不論成功或失敗都重拍 production trees/digests；不得以 mock filesystem 冒充 production path evidence。
7. 舊四 lane plan 與先前 blocker 只可標 historical，不得混入本次 authority-bound verdict。

## 停損與交付

- runtime 未 promotion、authority drift、任何 guard hit、snapshot drift：`BLOCKED`，不得補做第二次正式呼叫。
- 同一 blocker 第 3 次失敗即停。
- 只建立一個 evidence candidate commit，不 amend、不 push。回 candidate SHA、plan 摘要、guards、snapshot 結果與 production mutation=0。
